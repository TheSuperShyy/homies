# -*- coding: utf-8 -*-
"""A rejected reply gets one more pass with the tools before a stub ticket.

    python scripts/n8n_whatsapp_retry.py            # dry run
    python scripts/n8n_whatsapp_retry.py --apply    # write it
    python scripts/n8n_whatsapp_retry.py --restore  # put the 18 Sep snapshot back

WHY, 18 SEP
`Reply usable?` throws a reply away when it is empty, claims a ticket with no
reference behind it, or carries a link no tool returned. What happened next
was `Open it anyway`: a `rescue_request` with no building and no type, the
whole message log as its description, status `needs_review`. Live at 09:16:
a mould report, four turns, and on the last one the model wrote "אני פותח
קריאת שירות" and called nothing. The resident got a real reference
(255-1291-26) for a ticket that said nothing a technician could act on.
The owner, over the tickets table: "there is a bug".

The stub is the right last resort and the wrong first one. The model had
everything it needed and skipped the call; the cheapest correct thing is to
hand it the same message again with a note saying so, and let it call the
tool. Two replays of that conversation on fresh numbers opened a proper
ticket (type, building, common area) on the first try, so a second pass is
a good bet, and the stub is still there when it is not.

WHAT THIS DOES
  Reply usable? (false) -> Already retried? -> (no)  Try again -> Answer the resident
                                             -> (yes) Open it anyway -> Say it again ...

`Try again` is a Set node that re-emits the item the agent got the first time
(`Still the last word?`'s output, so `greeted`, `photo`, `text` and the rest
are all there) plus `retry_note`, which the agent's user-turn template
appends among its bracketed facts (AGENT_NEW in n8n_whatsapp_untemplate.py,
epoch 48). `Already retried?` reads its own `$runIndex`: 0 on the first
pass, 1 on the second, so the loop runs exactly once. Nothing else moves:
`Say it again`, `Second try usable?` and the send path are untouched, and on
the retry `$('Answer the resident').first()` is the latest run, which is
the draft `Say it again` should be replacing.

THE MEMORY COST, NAMED
The buffer (`Conversation so far`) records both passes: the rejected draft
as an assistant turn, then the note-plus-message and the real reply. The
1 Sep lesson is that a model copies its own last answer; the note says in
so many words that the last answer was thrown away and why, which is the
best counter this workflow has. Watched, not assumed.

HONEST LIMIT
Like `Say it again`, this cannot be fired on demand -- it needs the model to
produce an unusable reply -- so it ships wired and read back, and the
expressions proven in Node. The first live firing is the test.

Idempotent. Running it twice reports nothing to do.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-18sep-before-retry.json")
PLACEHOLDER = "REPLACE_WITH_N8N_WEBHOOK_SECRET"

# On the 240 x 60 grid, at least 200 x 100 clear of every neighbour
# (scripts/n8n_layout.py): Try again below `Still the last word?`, the If
# below `Type for a moment (menu)`.
TRY_POS, RETRIED_POS = [720, 300], [1440, 300]

# A bracketed fact for the model, in the shape of every other note in the
# user turn: what happened, and what fixes it. All three guard reasons are
# named because the Set node cannot tell which one fired.
RETRY_NOTE = (
    "[התשובה הקודמת שלך להודעה הזאת נפסלה ולא יצאה לדייר: או שהודיעה על "
    "קריאה שלא נפתחה, או שנתנה קישור שלא הגיע מכלי, או שהייתה ריקה. מה "
    "שקורה קורה רק דרך הכלים: אם יש מה לפתוח, תפתח עכשיו עם open_request "
    "ורק אז תענה, עם המספר שחזר; קישור לתשלום רק מ-get_payment_link. ואם "
    "חסר לך משהו כדי לפתוח, תשאל אותו.]"
)

# `}}` anywhere inside ends an n8n expression, so the braces are spaced.
TRY_JSON = (
    "={{ JSON.stringify(Object.assign({ }, $('Still the last word?').first().json, "
    "{ retry_note: '" + RETRY_NOTE + "' })) }}"
)

RETRIED = "={{ $runIndex > 0 }}"


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


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes = live["nodes"]
    by = {n["name"]: n for n in nodes}
    conns = live["connections"]
    for need in ("Reply usable?", "Open it anyway", "Still the last word?",
                 "Answer the resident", "Say it again"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    changes = []

    # --- The two new nodes --------------------------------------------------
    if "Try again" not in by:
        nodes.append({
            "id": "try_again", "name": "Try again",
            "type": "n8n-nodes-base.set", "typeVersion": 3.4,
            "position": TRY_POS,
            "parameters": {"mode": "raw", "jsonOutput": TRY_JSON, "options": {}},
        })
        changes.append("Try again: new node, the same message back to the agent "
                       "with a note on it")
    else:
        p = by["Try again"]["parameters"]
        if p.get("jsonOutput") != TRY_JSON:
            p["jsonOutput"] = TRY_JSON
            changes.append("Try again: note updated")

    if "Already retried?" not in by:
        nodes.append({
            "id": "already_retried", "name": "Already retried?",
            "type": "n8n-nodes-base.if", "typeVersion": 2,
            "position": RETRIED_POS,
            "parameters": {"conditions": {
                "options": {"caseSensitive": True, "leftValue": "",
                            "typeValidation": "loose"},
                "conditions": [{
                    "id": "retried", "leftValue": RETRIED, "rightValue": "",
                    "operator": {"type": "boolean", "operation": "true",
                                 "singleValue": True},
                }],
                "combinator": "and",
            }},
        })
        changes.append("Already retried?: new node, one retry and then the stub")

    # --- Wiring ------------------------------------------------------------------
    ru = conns.setdefault("Reply usable?", {}).setdefault("main", [[], []])
    while len(ru) < 2:
        ru.append([])
    want_false = [{"node": "Already retried?", "type": "main", "index": 0}]
    if ru[1] != want_false:
        ru[1] = want_false
        changes.append("Reply usable? (false) -> Already retried? (was Open it anyway)")

    want_retried = {"main": [
        [{"node": "Open it anyway", "type": "main", "index": 0}],
        [{"node": "Try again", "type": "main", "index": 0}],
    ]}
    if conns.get("Already retried?") != want_retried:
        conns["Already retried?"] = want_retried
        changes.append("Already retried? -> Open it anyway (yes) / Try again (no)")

    want_try = {"main": [[{"node": "Answer the resident", "type": "main", "index": 0}]]}
    if conns.get("Try again") != want_try:
        conns["Try again"] = want_try
        changes.append("Try again -> Answer the resident")

    if not changes:
        print("\nNothing to do. Live already matches.")
        return

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    print("\nchanges:")
    for c in changes:
        print("  - %s" % c)

    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": live["nodes"],
        "connections": live["connections"], "settings": live.get("settings", {}),
    })
    print("\nwritten. Re-run without --apply to confirm it reports nothing to do; "
          "the agent reads retry_note only once n8n_whatsapp_teamnote.py --apply "
          "has written AGENT_NEW (epoch 48).")


if __name__ == "__main__":
    main()
