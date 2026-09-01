# -*- coding: utf-8 -*-
"""Answer a burst of messages once, after four seconds of quiet.

    python scripts/n8n_whatsapp_batch.py            # dry run
    python scripts/n8n_whatsapp_batch.py --apply    # write it

WHY
On 1 Sep the owner typed nine digits in a minute. Nine executions ran in
parallel, nine model replies went out, out of order, and each one invented a
meaning for its digit — a nine-option menu extrapolated from a three-row one.
One of the inventions claimed a handover and the promise backstop, doing its
job on a reply it had every reason to believe, made it real. A resident typing
"6" reached a person.

The model fixes are elsewhere (prompt.md: never guess, never volunteer). This
file fixes the shape of the conversation: real people send three messages for
one thought, and a bot that answers each one separately is having three
conversations at once with the same person.

HOW — debounce, newest message wins, and the truth lives in Postgres
1. `Log inbound` already writes every model-bound message to the Supabase
   `messages` table, and it sits ABOVE the wait on the canvas, so under
   executionOrder v1 the row is committed before this execution sleeps.
2. `Let them finish` — a Wait node, 4 seconds (owner picked 3-5), on the reply
   branch only. Same node type `Type for a moment` already uses.
3. `Anything newer?` — after the wait, one PostgREST GET: the last dozen
   `messages` rows for this phone, newest first, both directions.
4. `Still the last word?` — a Code node. If the newest inbound row is not this
   run's message, a later one arrived while we slept: return nothing, that
   run answers. Otherwise join every inbound row down to the last outbound —
   the unanswered backlog — and hand it to the agent as one text.

So nine digits become one model call and one reply, and someone who taps
"פתיחת קריאת שירות" and types the fault two seconds later gets a single answer
to both — the tap's run is silenced, but its title is a row in the backlog, so
the model reads the tap and the fault as one thought.

WHY NOT staticData, WHICH WAS BUILT FIRST AND MEASURED
n8n staticData is a PER-EXECUTION SNAPSHOT: loaded when the run starts, saved
when it ends. Concurrent executions never see each other's writes, and the
last to finish clobbers the rest. The first version of this file stashed the
burst there; three digits produced three runs with `burst_size=1` each and
three replies. The store that `greeted` and `tapped` live in works because
those are written by runs that FINISH before the next message arrives — a
burst is precisely the case where that stops being true. (Those flags carry
the same snapshot race between overlapping runs; it predates this file — two
messages 3s apart already overlapped on a 10s model call — and the batching
makes it less visible, not worse: silenced runs still save their snapshot.)

WHAT DOES NOT WAIT, ON PURPOSE
- `Answer Meta` — the 200 to Chatwoot still goes out per message, first, from
  its spot above everything on the canvas (executionOrder v1 runs branches by
  position; see CONTEXT.md).
- `Human tap?` -> `Transfer the tap` — a handover a resident asked for fires
  immediately, never behind a delay. Same reasoning that moved it above the
  reply branch on 1 Sep.
- The canned branch (greeting -> menu) — a menu is routing, not conversation.
- `Log inbound` — beside the wait, not behind it, and that is load-bearing:
  it is what makes this message visible to the sibling runs deciding whether
  they are the last word.

THE RACES, STATED
Two messages milliseconds apart can each read the other's row as not-yet-there
and both answer; the bound is two replies, the OLD behaviour, made rare. A
greeting sandwiched inside a burst logs an outbound menu row that can cut the
backlog short by one message. Both accepted: rare, bounded, and the fallback
on any query failure is one reply per message, never silence.

A SIDE EFFECT WORTH KNOWING (recorded in HANDOVER.md)
`Say it again` and the promise backstop read `$('Sort').first().json` for the
resident's text, and on a burst that is the LAST message only, not the join.
A rescue ticket's description can therefore be one line short. Accepted: the
rescue path is rare, the join lives in the agent's memory either way.

Idempotent. Running it twice reports nothing to do. Refuses to write any
layout that adds a node-overlap pair beyond the three that predate it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
from n8n_layout import overlaps  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"

QUIET_SECONDS = 4  # owner: "3-5 seconds delay only"

# --------------------------------------------------------------------------
# 1. The staticData stash from this file's first version: reverted if found.
#    See WHY NOT staticData above. Anchors kept verbatim so the revert is
#    exact.
# --------------------------------------------------------------------------
STASH_ANCHOR = """const prevBot = store.lastBot[from];
const lastBot = prevBot && (Date.now() - prevBot.at) < 30 * 60 * 1000 ? prevBot.text : '';
delete store.lastBot[from];

return [{ json: {"""

STASH_NEW = """const prevBot = store.lastBot[from];
const lastBot = prevBot && (Date.now() - prevBot.at) < 30 * 60 * 1000 ? prevBot.text : '';
delete store.lastBot[from];

// THE BURST STASH. Every model-bound message lands here; the reply branch
// waits four seconds and only the run whose id is still `latest` answers,
// with the whole stash joined (see "Still the last word?"). Canned returns
// above never reach this, so a greeting still gets the menu instantly.
// Swept like lastBot so an abandoned burst cannot sit here forever.
store.burst = store.burst || {};
for (const k in store.burst) {
  if (Date.now() - (store.burst[k].at || 0) > 10 * 60 * 1000) delete store.burst[k];
}
const burstBox = store.burst[from] = store.burst[from] || { texts: [], ids: [] };
if (!burstBox.ids.includes(id)) {
  burstBox.ids.push(id);
  if (text.trim()) burstBox.texts.push(text);
  burstBox.latest = id;
  burstBox.at = Date.now();
}

return [{ json: {"""

# --------------------------------------------------------------------------
# 2. The gate.
# --------------------------------------------------------------------------
GATE_JS = """// After `Let them finish`. The shared truth is the `messages` table: Log
// inbound wrote this message BEFORE the wait (it sits above it on the canvas,
// and executionOrder v1 runs it first), so every sibling execution can see
// it. n8n staticData cannot do this job -- it is a per-execution snapshot,
// loaded at start and saved at end, so concurrent runs never see each other.
// Measured 1 Sep: three stashed digits, three runs, burst_size=1 in each.
//
// `Anything newer?` handed us the last rows for this phone, newest first,
// both directions. If the newest inbound is not this run's message, a later
// one arrived while we slept: say nothing, its run answers the whole backlog.
// If the query failed or came back empty, fall through with this run's own
// text -- the pre-batching behaviour, one reply per message, never silence.
const j = $('Sort').first().json;
const rows = $input.all().map(i => i.json).filter(r => r && r.direction);
const newestIn = rows.find(r => r.direction === 'inbound');
if (newestIn && String(newestIn.external_id) !== String(j.message_id)) {
  return [];
}
// The unanswered backlog: inbound rows down to the last outbound. This join
// is what lets a tap followed two seconds later by the fault text read as one
// thought -- the tap's own run was silenced, but its title is a row here.
const backlog = [];
for (const r of rows) {
  if (r.direction === 'outbound') break;
  const b = String(r.body == null ? '' : r.body).trim();
  if (b) backlog.push(b);
}
backlog.reverse();
const text = backlog.length ? backlog.join('\\n') : j.text;
return [{ json: Object.assign({}, j, { text: text, burst_size: backlog.length || 1 }) }];
"""

STICKY = (
    "## One reply per thought\n"
    "People send three messages for one thought, so the reply branch waits "
    f"{QUIET_SECONDS}s, asks Postgres for anything newer, and only the run "
    "holding the NEWEST inbound answers -- with the whole unanswered backlog "
    "joined. Nine digits in a minute = one model call, one reply (1 Sep: nine "
    "essays, out of order, and a real handover fired off the digit 6).\n\n"
    "The truth is the `messages` table, written by Log inbound BEFORE the "
    "wait. n8n staticData cannot carry this: it is a per-execution snapshot, "
    "and three concurrent runs each saw only their own stash when it was "
    "tried.\n\n"
    "What never waits: the 200 to Chatwoot, the menu, and Human tap? -> "
    "Transfer the tap. Two messages ms apart can still both answer; the bound "
    "is the old behaviour, made rare."
)

WAIT_POS = [420, 64]
NEWER_POS = [620, 64]
GATE_POS = [780, 184]
STICKY_POS = [380, 250]


def main():
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes = live["nodes"]
    by = {n["name"]: n for n in nodes}
    conns = live["connections"]
    for need in ("Sort", "Is there a message?", "Answer the resident",
                 "Log inbound", "Type for a moment"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    pre_overlaps = set((a, b) for a, b, _, _ in overlaps(nodes))
    changes = []

    # --- 1. Revert the staticData stash if the first version left it -------
    code = by["Sort"]["parameters"]["jsCode"]
    if STASH_NEW in code:
        by["Sort"]["parameters"]["jsCode"] = code.replace(STASH_NEW, STASH_ANCHOR, 1)
        changes.append("Sort: drop the staticData burst stash (snapshot "
                       "semantics; measured useless across concurrent runs)")

    # --- 2. The wait -------------------------------------------------------
    wait_tv = by["Type for a moment"].get("typeVersion", 1.1)
    if "Let them finish" not in by:
        nodes.append({
            "id": "burst_wait", "name": "Let them finish",
            "type": "n8n-nodes-base.wait", "typeVersion": wait_tv,
            "position": list(WAIT_POS),
            "parameters": {"amount": QUIET_SECONDS, "unit": "seconds"},
        })
        changes.append("Let them finish: %ds of quiet before any model reply"
                       % QUIET_SECONDS)
    elif by["Let them finish"].get("position") != WAIT_POS:
        by["Let them finish"]["position"] = list(WAIT_POS)
        changes.append("Let them finish moved to %s" % WAIT_POS)

    # --- 3. The query, wearing Log inbound's own url base and credential ----
    log_in = by["Log inbound"]
    base_url = log_in["parameters"]["url"].split("/rest/v1/")[0]
    newer_url = (
        "=" + base_url + "/rest/v1/messages"
        "?phone=eq.{{ $('Sort').first().json.to }}"
        # created_at, not id: the id column is a UUID, and ordering by it is
        # ordering by nothing. Measured 1 Sep: a three-digit burst came back
        # 2,1,3 by uuid, the wrong run answered, and the join read 3-1-2.
        # Inserts are hundreds of ms apart and timestamptz keeps microseconds,
        # so created_at is arrival order for anything a human can type.
        "&order=created_at.desc&limit=12&select=external_id,body,direction"
    )
    newer_params = {
        "method": "GET", "url": newer_url,
        "authentication": log_in["parameters"].get("authentication"),
        "genericAuthType": log_in["parameters"].get("genericAuthType"),
        "options": {"timeout": 10000},
    }
    if "Anything newer?" not in by:
        node = {
            "id": "burst_query", "name": "Anything newer?",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": log_in.get("typeVersion", 4.2),
            "position": list(NEWER_POS),
            "parameters": newer_params,
            # A Supabase blip must degrade to one-reply-per-message, not to
            # silence: the gate falls through on empty input.
            "alwaysOutputData": True,
            "onError": "continueRegularOutput",
        }
        if log_in.get("credentials"):
            node["credentials"] = log_in["credentials"]
        nodes.append(node)
        changes.append("Anything newer?: the last dozen messages rows for "
                       "this phone, newest first")
    else:
        q = by["Anything newer?"]
        if q["parameters"] != newer_params:
            q["parameters"] = newer_params
            changes.append("Anything newer?: query updated")
        if q.get("position") != NEWER_POS:
            q["position"] = list(NEWER_POS)
            changes.append("Anything newer? moved to %s" % NEWER_POS)

    # --- 4. The gate -------------------------------------------------------
    if "Still the last word?" not in by:
        nodes.append({
            "id": "burst_gate", "name": "Still the last word?",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": list(GATE_POS),
            "parameters": {"jsCode": GATE_JS},
        })
        changes.append("Still the last word?: newest message answers the "
                       "joined backlog; the rest say nothing")
    else:
        g = by["Still the last word?"]
        if g["parameters"].get("jsCode") != GATE_JS:
            g["parameters"]["jsCode"] = GATE_JS
            changes.append("Still the last word?: decides from the messages "
                           "table, not from staticData")
        if g.get("position") != GATE_POS:
            g["position"] = list(GATE_POS)
            changes.append("Still the last word? moved to %s" % GATE_POS)

    # --- 5. Wiring ---------------------------------------------------------
    # Log inbound stays on the If's true branch, beside the wait: it is the
    # write the sibling runs read. Canned and menu messages log through their
    # own branches, so it must not move onto Sort -- that would double-log.
    want_if = [{"node": "Let them finish", "type": "main", "index": 0},
               {"node": "Log inbound", "type": "main", "index": 0}]
    if conns.get("Is there a message?", {}).get("main", [[]])[0] != want_if:
        conns["Is there a message?"]["main"][0] = want_if
        changes.append("Is there a message? -> Let them finish + Log inbound "
                       "(the agent moves behind the gate)")

    for src, dst in (("Let them finish", "Anything newer?"),
                     ("Anything newer?", "Still the last word?"),
                     ("Still the last word?", "Answer the resident")):
        want = {"main": [[{"node": dst, "type": "main", "index": 0}]]}
        if conns.get(src) != want:
            conns[src] = want
            changes.append("%s -> %s" % (src, dst))

    # --- 6. The note on the canvas ----------------------------------------
    if "One reply per thought" not in by:
        nodes.append({
            "id": "burst_note", "name": "One reply per thought",
            "type": "n8n-nodes-base.stickyNote", "typeVersion": 1,
            "position": list(STICKY_POS),
            "parameters": {"content": STICKY, "height": 320, "width": 360,
                           "color": 4},
        })
        changes.append("sticky: why the reply waits and what never does")
    elif by["One reply per thought"]["parameters"].get("content") != STICKY:
        by["One reply per thought"]["parameters"]["content"] = STICKY
        changes.append("sticky: note rewritten")

    # --- Layout: no NEW overlap pairs beyond the three that predate this ---
    post_overlaps = set((a, b) for a, b, _, _ in overlaps(nodes))
    new_pairs = post_overlaps - pre_overlaps
    if new_pairs:
        sys.exit("Refusing to write a layout with new overlaps: %s"
                 % ", ".join("%s/%s" % p for p in sorted(new_pairs)))

    print("workflow : %s  (%s, active=%s)"
          % (live["name"], live["id"], live.get("active")))
    if not changes:
        print("")
        print("Nothing to do. Live already matches.")
        return

    print("")
    print("changes:")
    for c in changes:
        print("  - %s" % c)

    if not apply:
        print("")
        print("Dry run. Re-run with --apply to write it.")
        return

    # PUT takes only these four keys; sending id/active/tags back is a 400.
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": live["nodes"],
        "connections": live["connections"], "settings": live.get("settings", {}),
    })
    print("")
    print("written. Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
