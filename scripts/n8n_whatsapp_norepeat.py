# -*- coding: utf-8 -*-
"""The bot stops repeating itself (19 Oct): nothing already sent is sent again, the
second pass forgets its rejected draft, a ticket is looked up by the number.

    python scripts/n8n_whatsapp_norepeat.py            # dry run
    python scripts/n8n_whatsapp_norepeat.py --dump F   # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_norepeat.py --apply    # write it
    python scripts/n8n_whatsapp_norepeat.py --restore  # put the snapshot back

WHY. The owner's handset, 11:38 and 11:39 UTC (executions 114528, 114536): "what's
happening with the ticket I opened?" twice got "send me the ticket number or the full
address" twice, word for word. On another number at 11:32 (114483) the second pass
sent back the bot's previous message entire. Measured over the messages table: 34
times since 9 Aug the bot answered within 15 minutes with what it had just sent. The
owner: "we have the same problem having going on for a long time ... lets see first
what causes it then lets fix from there". Four causes (CONTEXT, "The bot repeats
itself"), each with its fix here:
  1. The second pass was built to parrot: the rejected draft stayed in the memory as
     if sent, the message was added again with a note of don'ts, and the second
     answer skipped every style check.
  2. Nothing compared a reply with what the phone already had.
  3. One pasted "לדבר עם נציג" made the chat "about a manager" for twelve rows, and
     the echo guard stood aside twice.
  4. get_request_status could not use the sender's number, so a ticket question
     always became "send me the number or the address".

WHAT CHANGES, in one write. Each text is owned elsewhere; this only carries them:
  Reply usable?         `repeat`, NEW (retry.REPEAT): a reply that is nearly a copy of
                        one of the bot's last three sent messages goes back, on both
                        passes; a turn that did work is exempt. `echo` and `clerk`
                        read the narrowed manager test (retry.MGR_CTX: this message
                        and the one before it, a pasted tap text taken off).
  Try again             names the copy; opens "a draft you wrote was not sent"; says
                        what was sent before arrived; its tools line names the status
                        lookup (retry.TRY_JSON).
  Forget the draft      NEW (retry.forget_node): a Chat Memory Manager on the agent's
                        buffer, fed by Try again beside the agent and drawn above it,
                        so v1 runs it first: it deletes the first pass's two messages.
  Claimed a ticket?,    a first draft that copies what was sent no longer stands in
  Mend the reply        for the second, and a second draft that is a copy after the
                        mending gives way to the owner's fixed line (wa_truth).
  Team note this turn?  the backstop reads the same narrowed manager test (teamnote).
  get_request_status    its description and parameter docs (n8n_whatsapp.py TOOLS):
                        called first, with nothing; the number finds their tickets.
  Answer the resident   the prompt (prompt.md): the status tool is called before any
                        number or address is asked; a message already sent is never
                        sent again, not even in slightly different words.
  Conversation so far   MEMORY_EPOCH 82 -> 83: the owner's buffer holds the question
                        twice, ready to be copied back.
NOT HERE: the Edge Function's lookup by the sender's number (index.ts,
get_request_status) ships with `supabase_functions.py --apply --oxs-mirror`; until it
does, the tool answers `found: 0` for a resident who gave no number or address, and
the prompt then has the model ask, as before.

A field is rewritten only when its live text is the one this replaces (by hash);
anything else means it changed since, and this refuses. A later epoch owns the prompt
and the key: then this carries only what it alone owns.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, `check_patchers_idle.py F`, a
Claude-played run of wa_qa.py on the candidate (never OpenRouter), the new pins,
`--apply`, the check on live, every patcher idle, `--watch`.
"""
import copy
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_untemplate as U  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
import n8n_whatsapp_retry as R  # noqa: E402
import n8n_whatsapp_manners as M  # noqa: E402
import n8n_whatsapp_teamnote as TN  # noqa: E402
import wa_truth as T  # noqa: E402
from n8n_whatsapp_handover import built  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-19oct-before-norepeat.json")
PLACEHOLDER = NP.PLACEHOLDER
OLD_EPOCH = 82
OLD_PROMPT = "9e4b0a8f158f"       # EPOCH_COVERS["prompt"] at epoch 82
OLD_TRY = "7631ae8f7590"          # Try again's live jsonOutput before this (the pin)
OLD_ECHO = "cc071e0d0437"         # Reply usable?'s `echo` before this
OLD_CLERK = "42e8f358cf3d"        # Reply usable?'s `clerk` before this
OLD_NOTE = "601affd8b5b0"         # Team note this turn?'s live leftValue before this
OLD_CLAIMED = "93c286ed6495"      # Claimed a ticket?'s live leftValue before this
OLD_MEND = "36d26f24f13d"         # Mend the reply's live jsonOutput before this
OLD_STATUS_DESC = "0a90643fedee"  # get_request_status's live toolDescription before this
OLD_STATUS_BODY = "1705de03e6a8"  # get_request_status's live jsonBody before this
MEMORY_KEY = "={{ $json.to }}-%d"
STATUS = "get_request_status"
CLAIMED = "Claimed a ticket?"
MEND = "Mend the reply"
NL = chr(10)
KEPT = ("הכלי מוצא את הקריאות שלו לבד לפי המספר שכותבים לך ממנו",
        "הודעה שכבר שלחת לו לא נשלחת שוב")
STATUS_KEPT = ("the number they write from finds their own tickets", "`by_phone`")

COMPILE_JS = ("const fs = require('fs'); const xs = JSON.parse(fs.readFileSync(0, 'utf8')); "
              "const bad = []; for (const [k, e] of xs) { try { new Function('$json', '$', "
              "'$runIndex', 'return (' + e + ');'); } catch (err) { bad.push(k + ': ' + err.message); } } "
              "console.log(JSON.stringify(bad));")


def node_of(by, name):
    if name not in by:
        sys.exit("No %r node on the live workflow -- refusing to guess." % name)
    return by[name]


def by_id(conds, cid, where):
    hits = [c for c in conds if c.get("id") == cid]
    if len(hits) != 1:
        sys.exit("REFUSING: %r has %d conditions with id %r." % (where, len(hits), cid))
    return hits[0]


def compiles(exprs):
    """Every changed expression parses as JavaScript, the way n8n will read it."""
    import check_whatsapp_rules as C
    xs = [[k, C.inner(v)] for k, v in exprs]
    r = subprocess.run(["node", "-e", COMPILE_JS], capture_output=True,
                       input=json.dumps(xs, ensure_ascii=False).encode("utf-8"))
    if r.returncode != 0:
        return ["node failed: " + r.stderr.decode("utf-8", "replace")[:300]]
    return json.loads(r.stdout.decode("utf-8"))


def snapshot(live):
    if os.path.exists(SNAPSHOT):
        return False
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    live = dict(live, staticData="<stripped: runtime state keyed by phone numbers>")
    text = json.dumps(live, ensure_ascii=False, indent=1)
    if secret:
        if secret not in text:
            sys.exit("The live workflow does not contain N8N_WEBHOOK_SECRET from .env, "
                     "so the snapshot's redaction would miss. Refusing to write it.")
        text = text.replace(secret, PLACEHOLDER)
    with open(SNAPSHOT, "w", encoding="utf-8", newline=NL) as f:
        f.write(text)
    return True


def restore():
    snap = json.load(open(SNAPSHOT, encoding="utf-8"))
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    if not secret:
        sys.exit("N8N_WEBHOOK_SECRET is not in .env; the snapshot's Sort node would "
                 "go live with a placeholder secret. Refusing.")
    body = json.loads(json.dumps(snap, ensure_ascii=False).replace(PLACEHOLDER, secret))
    W.api("PUT", "/api/v1/workflows/%s" % WORKFLOW_ID, {
        "name": body["name"], "nodes": body["nodes"],
        "connections": body["connections"], "settings": body.get("settings", {})})
    print("restored %s from %s (%d nodes)" % (WORKFLOW_ID, SNAPSHOT, len(body["nodes"])))
    print("MEMORY_EPOCH in n8n_whatsapp.py still says %d, and retry.py, manners.py, teamnote.py "
          "and wa_truth.py carry this change; put the repo back too (git revert)." % W.MEMORY_EPOCH)


def replace_field(have, want, old_hash, what, olds, news, changes, why):
    """`want` when `have` is the text this replaces, None when it is already `want`."""
    if have == want:
        return None
    if W.epoch_hash(have) != old_hash:
        sys.exit("REFUSING: %s is %s, neither the one this replaces (%s) nor the new one (%s)."
                 % (what, W.epoch_hash(have), old_hash, W.epoch_hash(want)))
    olds.append(have)
    news.append(want)
    changes.append("%s: %s -> %s (%s)" % (what, old_hash, W.epoch_hash(want), why))
    return want


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    prompt = W.system_prompt()
    status_desc = W.tool(STATUS)["description"]
    status_body = built(STATUS)["parameters"]["jsonBody"]
    W.check_memory_epoch(prompt=prompt, inject=U.AGENT_NEW, tools=W.tools_text())
    if W.MEMORY_EPOCH < OLD_EPOCH + 1:
        sys.exit("REFUSING: MEMORY_EPOCH is %d; this change was written for %d -> %d."
                 % (W.MEMORY_EPOCH, OLD_EPOCH, OLD_EPOCH + 1))
    later = W.MEMORY_EPOCH > OLD_EPOCH + 1     # a later change owns the prompt and the key
    if not later:
        bad = [k for k in KEPT if k not in prompt]
        bad += [k for k in STATUS_KEPT if k not in status_desc]
        if bad:
            sys.exit("REFUSING: prompt.md / %s do not read as this change: %s" % (STATUS, bad))
    if M.MARK != "const mv = 'manners v4';":
        sys.exit("REFUSING: manners.py is not v4 (%r)." % M.MARK)
    claimed_want, mend_want = T.claimed_expr(), T.mend_expr()
    exprs = [("echo", M.ECHO_GUARD["leftValue"]), ("clerk", M.CLERK_GUARD["leftValue"]),
             ("repeat", R.REPEAT), ("Try again", R.TRY_JSON), ("teamnote", TN.NOTE_THIS_TURN),
             ("claimed", claimed_want), ("mend", mend_want)]
    for k, v in exprs:
        if v.count("}}") != 1:
            sys.exit("REFUSING: a }} inside %s would end its expression early." % k)
    broken = compiles(exprs)
    if broken:
        sys.exit("REFUSING: does not parse: %s" % broken)

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in ("Answer the resident", "Conversation so far", STATUS, "Reply usable?", "Try again",
                 CLAIMED, MEND, TN.IF_NODE, "Anything newer?", "Still the last word?"):
        node_of(by, need)

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    before_layout = layout_complaints(nodes)
    changes, olds, news = [], [], []

    # The prompt and the status tool's texts: by hash, the way MEMORY_EPOCH covers them.
    if not later:
        agent = by["Answer the resident"]["parameters"].setdefault("options", {})
        got = replace_field(agent.get("systemMessage") or "", prompt, OLD_PROMPT,
                            "Answer the resident: prompt", olds, news, changes,
                            "the status tool first; nothing already sent is sent again")
        if got is not None:
            agent["systemMessage"] = got
        sp = by[STATUS]["parameters"]
        got = replace_field(sp.get("toolDescription") or "", status_desc, OLD_STATUS_DESC,
                            "%s: description" % STATUS, olds, news, changes,
                            "called first, with nothing; the number finds their tickets")
        if got is not None:
            sp["toolDescription"] = got
        got = replace_field(sp.get("jsonBody") or "", status_body, OLD_STATUS_BODY,
                            "%s: parameter docs" % STATUS, olds, news, changes,
                            "the building is for when they named one")
        if got is not None:
            sp["jsonBody"] = got

    # Reply usable?: `echo` and `clerk` read the narrowed manager test; `repeat` is new.
    cond = by["Reply usable?"]["parameters"]["conditions"]["conditions"]
    for g, old in ((M.ECHO_GUARD, OLD_ECHO), (M.CLERK_GUARD, OLD_CLERK)):
        mine = by_id(cond, g["id"], "Reply usable?")
        got = replace_field(mine.get("leftValue") or "", g["leftValue"], old,
                            "Reply usable?: `%s`" % g["id"], olds, news, changes,
                            "the chat about a manager is this message and the one before it")
        if got is not None:
            mine["leftValue"] = got
    have = [c for c in cond if c.get("id") == R.REPEAT_GUARD["id"]]
    if not have:
        cond.append(dict(R.REPEAT_GUARD))
        changes.append("Reply usable?: `repeat` guard added, both passes")
    elif have[0].get("leftValue") != R.REPEAT_GUARD["leftValue"]:
        sys.exit("REFUSING: a `repeat` guard is already on live and it is not this one (%s)."
                 % W.epoch_hash(have[0].get("leftValue") or ""))

    # Try again: names the copy, speaks of a draft he never got.
    tp = by["Try again"]["parameters"]
    got = replace_field(tp.get("jsonOutput") or "", R.TRY_JSON, OLD_TRY, "Try again: note",
                        olds, news, changes, "names a copy; a draft he never got; the status lookup")
    if got is not None:
        tp["jsonOutput"] = got

    # Team note this turn?: the same narrowed manager test.
    tc = by_id(by[TN.IF_NODE]["parameters"]["conditions"]["conditions"], "teamnote", TN.IF_NODE)
    got = replace_field(tc.get("leftValue") or "", TN.NOTE_THIS_TURN, OLD_NOTE,
                        "%s: backstop" % TN.IF_NODE, olds, news, changes,
                        "the chat about a manager is this message and the one before it")
    if got is not None:
        tc["leftValue"] = got

    # The last resort: never a copy either.
    cc = by_id(by[CLAIMED]["parameters"]["conditions"]["conditions"], "claimed", CLAIMED)
    got = replace_field(cc.get("leftValue") or "", claimed_want, OLD_CLAIMED, "%s" % CLAIMED,
                        olds, news, changes, "a first draft that is a copy does not stand in")
    if got is not None:
        cc["leftValue"] = got
    mp = by[MEND]["parameters"]
    got = replace_field(mp.get("jsonOutput") or "", mend_want, OLD_MEND, "%s" % MEND,
                        olds, news, changes, "never a copy; the fixed line instead")
    if got is not None:
        mp["jsonOutput"] = got

    # Forget the draft: the node, its memory, and Try again feeding it first.
    if R.FORGET not in by:
        nodes.append(R.forget_node())
        by[R.FORGET] = nodes[-1]
        changes.append("%s: new node (Chat Memory Manager, delete the last 2)" % R.FORGET)
    mem = conns.setdefault(R.MEMORY, {}).setdefault("ai_memory", [[]])
    if not any(t.get("node") == R.FORGET for t in mem[0]):
        mem[0].append({"node": R.FORGET, "type": "ai_memory", "index": 0})
        changes.append("%s -> %s (memory)" % (R.MEMORY, R.FORGET))
    want_try = {"main": [[{"node": R.FORGET, "type": "main", "index": 0},
                          {"node": "Answer the resident", "type": "main", "index": 0}]]}
    if conns.get("Try again") != want_try:
        conns["Try again"] = copy.deepcopy(want_try)
        changes.append("Try again -> %s (first, drawn above) and Answer the resident" % R.FORGET)
    probs = R.forget_problems(nodes, conns)
    if probs:
        sys.exit("REFUSING: %s would be wrong: %s" % (R.FORGET, probs))

    # The memory: the owner's buffer holds the question twice.
    mem_p = by["Conversation so far"]["parameters"]
    want_key = MEMORY_KEY % W.MEMORY_EPOCH
    if not later and mem_p.get("sessionKey") != want_key:
        if mem_p.get("sessionKey") != MEMORY_KEY % OLD_EPOCH:
            sys.exit("REFUSING: the memory key is %r, not epoch %d." % (mem_p.get("sessionKey"), OLD_EPOCH))
        mem_p["sessionKey"] = want_key
        changes.append("Conversation so far: memory epoch %d -> %d (every buffer starts fresh)"
                       % (OLD_EPOCH, W.MEMORY_EPOCH))
    if mem_p.get("contextWindowLength") != W.MEMORY_TURNS:
        sys.exit("REFUSING: the memory window is %r, not %d." % (mem_p.get("contextWindowLength"), W.MEMORY_TURNS))

    sib = NP.siblings()
    sib = {k: v for k, v in sib.items()
           if not k.startswith(("n8n_whatsapp_norepeat.", "n8n_whatsapp_retry.",
                                "n8n_whatsapp_manners.", "n8n_whatsapp_teamnote.",
                                "n8n_whatsapp_safetynet.", "n8n_whatsapp_procedure."))}
    old_all, new_all = NL.join(olds), NL.join(news)
    lost = [k for k, v in sib.items() if v in old_all and v not in new_all]
    if lost:
        sys.exit("REFUSING: the edit would break other patchers' anchors: %s" % lost)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("checks   : prompt %s, %s %s / %s, echo %s, clerk %s, repeat %s, Try again %s, backstop %s, "
          "claimed %s, mend %s, epoch %d, %d sibling anchors intact"
          % (W.epoch_hash(prompt), STATUS, W.epoch_hash(status_desc), W.epoch_hash(status_body),
             W.epoch_hash(M.ECHO_GUARD["leftValue"]), W.epoch_hash(M.CLERK_GUARD["leftValue"]),
             W.epoch_hash(R.REPEAT), W.epoch_hash(R.TRY_JSON), W.epoch_hash(TN.NOTE_THIS_TURN),
             W.epoch_hash(claimed_want), W.epoch_hash(mend_want), W.MEMORY_EPOCH,
             sum(1 for v in sib.values() if v in old_all)))
    if not changes:
        print("")
        print("Nothing to do. Live already matches.")
        return
    print("")
    print("changes:")
    for ch in changes:
        print("  - %s" % ch)

    worse = sorted(layout_complaints(nodes) - before_layout)
    if worse:
        sys.exit("REFUSING TO PATCH. This would introduce placement problems "
                 "that are not already there:" + NL + "    " + (NL + "    ").join(worse))

    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        NP.dump(nodes, conns, path)
        print("")
        print("dumped   : %s (the would-be workflow, secret replaced)" % path)

    if not apply:
        print("")
        print("Dry run. Re-run with --apply to write it.")
        return

    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": nodes, "connections": conns,
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    bb = {n["name"]: n for n in back["nodes"]}
    gb = {c["id"]: c["leftValue"] for c in bb["Reply usable?"]["parameters"]["conditions"]["conditions"]}
    print("")
    print("written: %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  prompt %s (want %s); memory key %s" % (
        W.epoch_hash(bb["Answer the resident"]["parameters"]["options"]["systemMessage"]),
        W.epoch_hash(prompt), bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("  %s %s / %s (want %s / %s)" % (STATUS, W.epoch_hash(bb[STATUS]["parameters"]["toolDescription"]),
                                           W.epoch_hash(bb[STATUS]["parameters"]["jsonBody"]),
                                           W.epoch_hash(status_desc), W.epoch_hash(status_body)))
    print("  echo %s, clerk %s, repeat %s (want %s, %s, %s)" % (
        W.epoch_hash(gb["echo"]), W.epoch_hash(gb["clerk"]), W.epoch_hash(gb.get("repeat", "")),
        W.epoch_hash(M.ECHO_GUARD["leftValue"]), W.epoch_hash(M.CLERK_GUARD["leftValue"]), W.epoch_hash(R.REPEAT)))
    print("  Try again %s (want %s)" % (W.epoch_hash(bb["Try again"]["parameters"]["jsonOutput"]),
                                       W.epoch_hash(R.TRY_JSON)))
    print("  %s: %s" % (R.FORGET, R.forget_problems(back["nodes"], back["connections"]) or "right"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
