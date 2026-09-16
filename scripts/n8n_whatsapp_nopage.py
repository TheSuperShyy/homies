# -*- coding: utf-8 -*-
"""ONE-DAY STATE, 13 Sep. Superseded 14 Sep by n8n_whatsapp_teamnote.py, which
builds on top of what this left (the mention came back as a team note).
Its dry run is still the right check that the 3-13 Sep paging nodes are
gone. DO NOT run `--restore`: the 13 Sep snapshot predates the team-note
nodes and would take them off with it.

Nothing pages a person from WhatsApp any more: the bot is the rep.

    python scripts/n8n_whatsapp_nopage.py              # dry run
    python scripts/n8n_whatsapp_nopage.py --apply      # write it
    python scripts/n8n_whatsapp_nopage.py --restore    # put the 13 Sep snapshot back

WHY
The owner, 13 Sep: "lessen the interaction with office and tenants ... if the
chatbot cannot handle the conversation anymore it should try its best to
handle everything like opening a ticket ... the bot won't turn off but would
mention the office." Asked twice more, in so many words: the third button
becomes משהו אחר, and emergencies get the office details like everything else.

So the alert half of feature 16 comes out of this workflow. Three paths paged a
department inside Chatwoot -- the נציג tap (`Human tap?` -> `Hand to a person
(tap)` -> `Transfer the tap`), the model's `transfer_to_human` tool (whose
description said to call it for money disputes, anger, a request for a person,
or whenever unsure), and the promise backstop (`Promised a transfer, made
none?` -> `Transfer it anyway`). All three go. The toggle half stays exactly as
it is: a real person replying in the thread (`Human replied?` -> `bot-off`) is
still the one thing that silences the bot, and the 15-minute handback still
hands the thread back.

THE COST, STATED ONCE. A 22:00 "I'm stuck in the lift" is now an
emergency-urgency ticket, the national number and the office line. Nobody at
Homies hears about it until somebody opens Chatwoot. The owner chose this with
that consequence in front of him.

WHAT IT CHANGES, AND NOTHING ELSE

  0. Snapshot. Before touching anything it writes the live workflow to
     docs/handover/n8n-whatsapp-live-13sep-before-nopage.json with the webhook
     secret replaced by a placeholder (public repo). `--restore` puts it back,
     secret re-inserted from .env. Written once; a later run leaves it alone.
  1. Deletes the eleven nodes that made up the paging: the three of the tap
     path and its sticky, the tool, the two of the tool path, and the four of
     the backstop (the If, `Transfer it anyway`, `Carry the reply`, its
     sticky). Every connection into or out of them goes with them.
  2. Rewires `Reply usable?[true]` -> `Type for a moment` and `Log reply`
     directly. That is the backstop's false branch with the If taken out; an
     If passes items through unchanged, and `Canned reply?` and `Second try
     usable?` already feed those two nodes in the same shape.
  3. The third button. Chatwoot forwards a tap as its TITLE, so the title is
     the routing key and every copy moves together: `Sort`'s MENU item and
     TAP_KIND line, `Send`'s input_select items. "לדבר עם נציג"/`human`
     becomes "משהו אחר"/`other`. A kind of `other` is tested by nothing; the
     tap reaches the model like any other message, which is the point.
  4. Syncs the three texts the memory epoch hashes, from their owners: the
     system prompt (n8n_whatsapp.system_prompt), the injected template
     (n8n_whatsapp_untemplate.AGENT_NEW, minus its two "already handed to a
     rep" clauses), and show_menu's description (n8n_whatsapp.tool). Then the
     memory node's sessionKey, so epoch 20 actually starts.
  5. One sticky, `One reply per thought`, loses the clause naming the tap
     transfer as something that never waits.

Placement is checked relatively, as n8n_whatsapp_patch.py does: the live
canvas already has complaints, and this must not add any.

Idempotent. Running it twice reports nothing to do.

Left alone, on purpose: the `Hand to a person` sub-workflow and the ticker
(the handback is the toggle's other half; the ladder acts only on `handover`
labels nothing sets now), the four Chatwoot teams and inbox membership, and the
`transfer_to_human` handler inside debt-tools, which the voice agents still
use. n8n_whatsapp_handover.py, n8n_whatsapp_promise.py and
n8n_whatsapp_transfer.py are superseded by this: their dry runs will exit on a
node that is absent on purpose.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_untemplate as U  # noqa: E402
from n8n_whatsapp_patch import layout_complaints, strip_connections  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-13sep-before-nopage.json")
PLACEHOLDER = "REPLACE_WITH_N8N_WEBHOOK_SECRET"

# Named, not matched by shape, for the reason n8n_whatsapp_patch.py gives: a
# rule that says "any If feeding an Execute Workflow" would one day match
# something else on a workflow this repo cannot see in source.
DROP = [
    "Human tap?", "Hand to a person (tap)", "Transfer the tap", "The tap transfer",
    "transfer_to_human",
    "Handover this turn?", "Hand to a person",
    "Promised a transfer, made none?", "Transfer it anyway", "Carry the reply",
    "The promise backstop",
]

# The nodes this edits by anchor. Missing = refuse, never guess.
NEED = ("Sort", "Send", "show_menu", "Reply usable?", "Type for a moment",
        "Log reply", "Answer the resident", "One reply per thought")

# --------------------------------------------------------------------------
# Sort. Whitespace inside the two lines is the editor's column alignment, so
# the anchors are regexes on the meaning and the replacements keep the shape.
# --------------------------------------------------------------------------
SORT_MENU_OLD = re.compile(r'\{ title: "לדבר עם נציג",\s*value: "human" \}')
SORT_MENU_NEW = '{ title: "משהו אחר",         value: "other" }'
SORT_KIND_OLD = re.compile(r'"לדבר עם נציג":\s*"human",')
SORT_KIND_NEW = '"משהו אחר":          "other",'
# A comment, and only a comment: true once, false now, and a person reading
# the live script next month deserves the current sentence.
SORT_NOTE_OLD = "// `tap` is what Human tap? reads, and it now leaves the node on this return"
SORT_NOTE_NEW = ("// `tap` is the row's kind, carried for readback. Since 13 Sep nothing routes\n"
                 "  // on it (Human tap? is gone); it leaves the node on this return")

# Send's input_select items, exact.
SEND_OLD = "{ title: 'לדבר עם נציג', value: 'human' }"
SEND_NEW = "{ title: 'משהו אחר', value: 'other' }"

# The sticky.
STICKY_OLD = "the 200 to Chatwoot, the menu, and Human tap? -> Transfer the tap."
STICKY_NEW = "the 200 to Chatwoot and the menu."


def ensure_link(conns, src, dst, index=0):
    branches = conns.setdefault(src, {}).setdefault("main", [])
    while len(branches) <= index:
        branches.append([])
    if any(t.get("node") == dst for t in branches[index]):
        return False
    branches[index].append({"node": dst, "type": "main", "index": 0})
    return True


def snapshot(live):
    """The live workflow as found, secret redacted. Once."""
    if os.path.exists(SNAPSHOT):
        return False
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    # staticData is runtime state -- per-phone language, last canned line,
    # last tap -- keyed by resident phone numbers. `--restore` never sends it
    # (PUT takes name/nodes/connections/settings), and this file lives in a
    # public repo, so it is not kept. The 3 Sep snapshots still carry it.
    live = dict(live, staticData="<stripped: runtime state keyed by phone numbers>")
    text = json.dumps(live, ensure_ascii=False, indent=1)
    if secret:
        if secret not in text:
            sys.exit("The live workflow does not contain N8N_WEBHOOK_SECRET from .env, "
                     "so the snapshot's redaction would miss. Refusing to write it.")
        text = text.replace(secret, PLACEHOLDER)
    with open(SNAPSHOT, "w", encoding="utf-8", newline="\n") as f:
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


def edit(text, old, new, label, changes):
    """Present-new = done; present-old = replace once; neither = refuse."""
    if isinstance(old, re.Pattern):
        if old.search(text) is None:
            if new in text:
                return text
            sys.exit("Anchor missing -- refusing to guess:\n  %s" % label)
        changes.append(label)
        return old.sub(new, text, count=1)
    if new in text and old not in text:
        return text
    if old not in text:
        sys.exit("Anchor missing -- refusing to guess:\n  %s" % label)
    changes.append(label)
    return text.replace(old, new, 1)


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes = live["nodes"]
    conns = live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in NEED:
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    prompt = W.system_prompt()
    W.check_greeting(prompt)
    W.check_memory_epoch(prompt=prompt, inject=U.AGENT_NEW, tools=W.tools_text())

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))

    before_layout = layout_complaints(nodes)
    changes = []

    # 1. the paging nodes
    present = [n["name"] for n in nodes if n["name"] in DROP]
    if present:
        changes.append("remove nodes: %s" % ", ".join(present))
    kept = [n for n in nodes if n["name"] not in DROP]
    before = json.dumps(conns, sort_keys=True, ensure_ascii=False)
    conns = strip_connections(conns, set(DROP))
    if json.dumps(conns, sort_keys=True, ensure_ascii=False) != before:
        changes.append("rewire: drop every connection touching those nodes")

    # 2. the reply branch, with the backstop taken out of the middle
    for dst in ("Type for a moment", "Log reply"):
        if ensure_link(conns, "Reply usable?", dst, 0):
            changes.append("wire Reply usable?[true] -> %s" % dst)

    # 3. the third button, every copy
    sort = by["Sort"]["parameters"]
    code = sort.get("jsCode") or ""
    code = edit(code, SORT_MENU_OLD, SORT_MENU_NEW, "Sort: MENU row 3 reads משהו אחר / other", changes)
    code = edit(code, SORT_KIND_OLD, SORT_KIND_NEW, "Sort: TAP_KIND maps משהו אחר -> other", changes)
    if SORT_NOTE_OLD in code:
        code = code.replace(SORT_NOTE_OLD, SORT_NOTE_NEW, 1)
        changes.append("Sort: the tap comment stops naming Human tap?")
    sort["jsCode"] = code

    send = by["Send"]["parameters"]
    send["jsonBody"] = edit(send.get("jsonBody") or "", SEND_OLD, SEND_NEW,
                            "Send: show_menu's third row reads משהו אחר / other", changes)

    # 4. the three hashed texts, from their owners, then the epoch itself
    agent = by["Answer the resident"]["parameters"]
    if agent.get("options", {}).get("systemMessage") != prompt:
        old = agent.get("options", {}).get("systemMessage") or ""
        agent.setdefault("options", {})["systemMessage"] = prompt
        changes.append("prompt: %d chars -> %d (you handle it; the office for office "
                       "matters; nobody is promised a call)" % (len(old), len(prompt)))
    if agent.get("text") != U.AGENT_NEW:
        agent["text"] = U.AGENT_NEW
        changes.append("inject: the two 'already handed to a rep' clauses are gone")
    menu_desc = W.tool("show_menu")["description"]
    if by["show_menu"]["parameters"].get("description") != menu_desc:
        by["show_menu"]["parameters"]["description"] = menu_desc
        changes.append("show_menu: description stops offering a person")
    mem = next((n for n in kept if n["type"].endswith("memoryBufferWindow")), None)
    if mem is None:
        sys.exit("No memory node on the live workflow -- refusing to guess.")
    want_key = "={{ $json.to }}-%d" % W.MEMORY_EPOCH
    if mem["parameters"].get("sessionKey") != want_key:
        changes.append("memory epoch: %s -> %s (every existing buffer is abandoned)"
                       % (mem["parameters"].get("sessionKey"), want_key))
        mem["parameters"]["sessionKey"] = want_key

    # 5. the sticky
    st = by["One reply per thought"]["parameters"]
    st["content"] = edit(st.get("content") or "", STICKY_OLD, STICKY_NEW,
                         "sticky One reply per thought: no tap transfer to name", changes)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d live -> %d after" % (len(nodes), len(kept)))
    if not changes:
        print("\nNothing to do. Live already matches.")
        return
    print("\nchanges:")
    for ch in changes:
        print("  - %s" % ch)

    worse = sorted(layout_complaints(kept) - before_layout)
    if worse:
        sys.exit("REFUSING TO PATCH. This would introduce placement problems "
                 "that are not already there:\n    " + "\n    ".join(worse))

    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    # PUT takes only these four keys; sending id/active/tags back is a 400.
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": kept, "connections": conns,
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    names = {n["name"] for n in back["nodes"]}
    left = [d for d in DROP if d in names]
    print("\nwritten: %d nodes.%s" % (len(back["nodes"]),
                                      " STILL PRESENT: %s" % left if left else ""))
    for src in ("Sort", "Reply usable?"):
        print("  %s -> %s" % (src, json.dumps(back["connections"].get(src), ensure_ascii=False)))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
