# -*- coding: utf-8 -*-
"""Make an emergency handover leave a record.

    python scripts/n8n_whatsapp_transfer.py            # dry run
    python scripts/n8n_whatsapp_transfer.py --apply    # write it

WHY
On 1 Sep a resident reported somebody fallen on the stairs and wrote "send
help". Four turns, one handover, and `requests` ended the conversation empty.
The owner asked why no ticket was opened; this is the answer, and it is a
one-word answer.

`transfer_to_human` offered the model five reasons, one of them `distress`. It
picked `distress`, which is the correct English word for a frightened person and
a perfectly valid value -- the Edge Function stores it without complaint, so
nothing anywhere reported a problem. But the emergency backstop in
`supabase/functions/debt-tools/index.ts` -- the net that writes a `needs_review`
ticket when a handover happens and no request was opened, added on 20 Aug after
a caller reported a fire and the day ended with an empty table -- is scoped to
`reason === "emergency"` alone.

So the reason that best describes a person in trouble was the one reason that
routed them around the net built for exactly them. A transfer is a note: nothing
searches `call_outcomes`, no dashboard lists it, nobody is dispatched off it.

TWO CHANGES, BOTH ON THE WHATSAPP TOOL ONLY
1. `distress` is no longer offered. On WhatsApp a person in distress IS the
   emergency case. The Edge Function is deliberately NOT widened instead: the
   voice debt agent sends `distress` for someone upset about money, and minting
   an emergency ticket for every distressed debtor is worse than the bug.
   `scripts/vapi_tools.py` is untouched.
2. The tool now sends a `description`. The backstop writes `args.description`
   and falls back to a sentence saying the call recording is the only account of
   what happened -- which on WhatsApp is false twice over, because there is no
   call and no recording. Without this the ticket a resident's emergency
   produces says nothing about the emergency.

Idempotent. Running it twice reports nothing to do.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"


def built(name):
    """The node as n8n_whatsapp.py builds it, so this file duplicates no text.

    The jsonBody is assembled from TOOL_BODY, from_ai() and the tool spec; a
    copy pasted in here would be a second source of truth and would drift the
    first time either side is edited, which is the whole reason the tool
    descriptions were reconciled on 31 Aug.
    """
    for n in W.workflow(W.env())["nodes"]:
        if n["name"] == name:
            return n
    sys.exit("n8n_whatsapp.py no longer builds a %r node." % name)


def main():
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    if "transfer_to_human" not in by:
        sys.exit("No transfer_to_human node on the live workflow -- refusing to guess.")

    node = by["transfer_to_human"]
    want = built("transfer_to_human")["parameters"]["jsonBody"]
    have = node["parameters"].get("jsonBody") or ""

    changes = []
    if have != want:
        if "distress" in have and "distress" not in want:
            changes.append("transfer_to_human: stop offering `distress`, so a person "
                           "in a bad state reaches the emergency backstop")
        if "description" in want and "'description'" not in have:
            changes.append("transfer_to_human: send a description, so the ticket the "
                           "backstop writes says what was reported")
        if not changes:
            changes.append("transfer_to_human: jsonBody %d -> %d chars"
                           % (len(have), len(want)))
        node["parameters"]["jsonBody"] = want

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
    print("")
    print("  live wants: %s" % want)

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
