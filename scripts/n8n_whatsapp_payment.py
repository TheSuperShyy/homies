# -*- coding: utf-8 -*-
"""Bring the live open_request and get_balance tool texts up to the repo's.

    python scripts/n8n_whatsapp_payment.py            # dry run
    python scripts/n8n_whatsapp_payment.py --apply    # write it
    python scripts/n8n_whatsapp_payment.py --restore  # put the 15 Sep snapshot back

WHY, 15 SEP
Owner: "when the person want to have a payment information it should open a
ticket as well that this person want to pay". Wanting to pay is a ticket now
(migration 031, type `payment`) beside the team note, and the model learns it
from three tool texts: open_request (the lead paragraph and the gloss on
`type`), notify_team (its payment clause) and get_balance (its last sentence).

`n8n_whatsapp_teamnote.py` carries the prompt, the memory epoch and the
notify_team node, but not the other two tools' descriptions, and the script
that used to sync those (`n8n_whatsapp_open.py`) exits on the transfer node it
expects and the 13 Sep build removed. So this does exactly two nodes:

  open_request   toolDescription <- TOOLS; the `type` and (since 16 Sep) the
                 `fault_location` $fromAI docs in jsonBody replaced by anchor,
                 so the rest of that body -- reporter_unit, urgency, the verify
                 fixes of earlier patchers -- is untouched.
  get_balance    toolDescription <- TOOLS.

Same rules as every layered patcher here: read live, change the named fields,
leave every other byte, snapshot before the first write, idempotent, --restore.
The epoch guard runs first: a tool-text change poisons buffers exactly the way
a prompt change does, and teamnote's --apply is what actually bumps the live
session key -- run that after this.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_untemplate as U  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-15sep-before-payment.json")
PLACEHOLDER = "REPLACE_WITH_N8N_WEBHOOK_SECRET"

# The live `type` doc as every earlier build wrote it: a bare enum list. The
# anchor is the whole $fromAI doc string, so a body that already carries the
# gloss is left alone (idempotent), and one with an unknown shape is refused.
TYPE_OLD = ('$fromAI(\'type\', "One of plumbing/electrical/lighting/elevator/cleaning/'
            'gardening/pest_control/locksmith/fire_safety/maintenance/other/complaint", '
            "'string')")

# 16 Sep, the client's review: the `fault_location` gloss moved (a resident's
# own fixtures are not a ticket). Same mechanism, second anchor: the doc as
# every build before 16 Sep wrote it, replaced whole by what TOOLS says now.
FAULT_OLD = ('$fromAI(\'fault_location\', "Where the FAULT is, not where they live. '
             "'apartment' for a leak in their kitchen; 'common' for a lift, lobby, "
             'stairwell, roof, car park, gate or yard. One of apartment/common.", '
             "'string')")


# 18 Sep, the owner over the tickets table: every ticket carries the
# reporter's flat, asked for with the building, and the building reaches
# the tool in Hebrew. Two more anchors, same mechanism: the live docs as
# the 2 Sep menu patcher and the 26 Aug build wrote them, replaced whole
# by what TOOLS says now.
REPORTER_OLD = ('$fromAI(\'reporter_unit\', "The apartment the person reporting LIVES in. '
                "Send it whenever you know it - for a fault inside their flat the flow "
                "gives it to you. For a fault in a lobby, lift or any common area, "
                "include it only if they volunteered it, and never ask an extra "
                'question just to fill this field.", \'string\')')
BUILDING_OLD = ('$fromAI(\'building\', "Street and number, as the resident wrote it. '
                'The whole sentence is fine; this tool checks it.", \'string\')')


def type_new():
    t = W.tool("open_request")["input_schema"]["properties"]["type"]
    return W.from_ai("type", (t.get("description", "") + " ").lstrip()
                     + "One of " + "/".join(t["enum"]))


def reporter_new():
    return W.from_ai("reporter_unit",
                     W.tool("open_request")["input_schema"]["properties"]["reporter_unit"]["description"])


def building_new():
    return W.from_ai("building",
                     W.tool("open_request")["input_schema"]["properties"]["building"]["description"])


def fault_new():
    f = W.tool("open_request")["input_schema"]["properties"]["fault_location"]
    return W.from_ai("fault_location", f["description"] + " One of apartment/common.")


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

    # The guard first: if TOOLS moved and the epoch did not, stop here.
    W.check_memory_epoch(prompt=W.system_prompt(), inject=U.AGENT_NEW, tools=W.tools_text())

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    for need in ("open_request", "get_balance", "notify_team", "Answer the resident"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(live["nodes"]))
    changes = []

    for name in ("open_request", "get_balance"):
        want = W.tool(name)["description"]
        have = by[name]["parameters"].get("toolDescription") or ""
        if have != want:
            changes.append("%s: description %d -> %d chars" % (name, len(have), len(want)))
            by[name]["parameters"]["toolDescription"] = want

    body = by["open_request"]["parameters"].get("jsonBody") or ""
    for arg, old, new in (("type", TYPE_OLD, type_new()),
                          ("fault_location", FAULT_OLD, fault_new()),
                          ("reporter_unit", REPORTER_OLD, reporter_new()),
                          ("building", BUILDING_OLD, building_new())):
        if new in body:
            continue
        if body.count(old) != 1:
            sys.exit("REFUSING: the open_request jsonBody does not carry the `%s` doc this "
                     "script knows (found %d). Read the live body before touching it."
                     % (arg, body.count(old)))
        body = body.replace(old, new, 1)
        by["open_request"]["parameters"]["jsonBody"] = body
        changes.append("open_request: jsonBody `%s` doc %d -> %d chars" % (arg, len(old), len(new)))

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
    print("\nwritten. Re-run without --apply to confirm it reports nothing to do, then "
          "run n8n_whatsapp_teamnote.py --apply for the prompt and the epoch.")


if __name__ == "__main__":
    main()
