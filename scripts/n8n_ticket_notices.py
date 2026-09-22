# -*- coding: utf-8 -*-
"""The n8n cron that sends the "done" messages: `Homies — ticket notices`.

    python scripts/n8n_ticket_notices.py              # dry run
    python scripts/n8n_ticket_notices.py --apply      # create or update the workflow
    python scripts/n8n_ticket_notices.py --activate   # switch it on

WHY A CRON
Migration 036 fills the `ticket_notices` outbox the moment a WhatsApp ticket
turns resolved; `send_ticket_notices` in the Edge Function sends what is
pending as the Meta template and marks each row. Something has to call it.
A database webhook would fire once and lose a Chatwoot hiccup; a cron every
two minutes is the retry as well as the trigger, and it also covers tickets
resolved by a path that does not exist yet (the OXS mirror, a bulk close).
Two minutes is the delay a resident sees between the office pressing
"resolved" and the message -- fine for a done notice.

THE SHAPE
    Every 2 minutes (scheduleTrigger) -> Send the done messages (HTTP POST to
    the Edge Function, the "Homies tool secret" header credential, the same
    envelope every n8n -> function call uses, function.name
    send_ticket_notices, arguments {limit: 20})

Same rules as every workflow script here: defined in code, found by NAME so a
re-run updates instead of duplicating, laid out on the grid (n8n_layout.py
refuses otherwise), and it only ever creates or updates THIS workflow -- the
n8n instance is shared production carrying other clients' work.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
from n8n_layout import LayoutError, check  # noqa: E402

WF_NAME = "Homies — ticket notices"
# The header credential every tool node already uses (x-homies-secret). n8n's
# public API cannot list credentials, so the id is the one written down in
# n8n_whatsapp.py when it was created.
TOOL_CRED = {"id": "OeZ0OVs0X0tyEzcI", "name": "Homies tool secret"}

ENVELOPE = ("={{ JSON.stringify({ message: { type: 'tool-calls', call: { id: 'cron:ticket-notices' }, "
            "toolCalls: [{ id: 'cron', type: 'function', function: { name: 'send_ticket_notices', "
            "arguments: { limit: 20 } } }] } }) }}")


def workflow(fn_url):
    return {
        "name": WF_NAME,
        "settings": {"executionOrder": "v1", "timezone": "Asia/Jerusalem"},
        "nodes": [
            {
                "id": "why", "name": "Why this exists", "type": "n8n-nodes-base.stickyNote",
                "typeVersion": 1, "position": [0, -240],
                "parameters": {"height": 220, "width": 720, "content":
                    "## The \"done\" message\n"
                    "When a WhatsApp ticket is set to resolved, migration 036 queues a row in `ticket_notices`. "
                    "Every two minutes this asks the Edge Function to send what is pending as the Meta template "
                    "`ticket_resolved_he` (the resident has usually not written in 24 hours, so only a template "
                    "gets through). The function marks each row sent / failed / skipped; a failure is retried "
                    "up to five times by the next ticks. Owned by scripts/n8n_ticket_notices.py -- edit there."},
            },
            {
                "id": "every2", "name": "Every 2 minutes", "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2, "position": [0, 0],
                "parameters": {"rule": {"interval": [{"field": "minutes", "minutesInterval": 2}]}},
            },
            {
                "id": "send", "name": "Send the done messages", "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2, "position": [240, 0],
                "parameters": {
                    "method": "POST", "url": fn_url,
                    "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
                    "sendBody": True, "specifyBody": "json", "jsonBody": ENVELOPE,
                    "options": {"timeout": 60000},
                },
                "credentials": {"httpHeaderAuth": TOOL_CRED},
                "retryOnFail": True, "maxTries": 3, "waitBetweenTries": 5000,
            },
        ],
        "connections": {
            "Every 2 minutes": {"main": [[{"node": "Send the done messages", "type": "main", "index": 0}]]},
        },
    }


def find():
    for w in W.api("GET", "/api/v1/workflows?limit=100")["data"]:
        if w["name"] == WF_NAME:
            return w
    return None


def main():
    e = W.env()
    fn_url = e["SUPABASE_URL"].rstrip("/") + "/functions/v1/debt-tools"
    wf = workflow(fn_url)
    try:
        check(wf["nodes"], WF_NAME)
    except LayoutError as ex:
        sys.exit("\n%s\n" % ex)
    existing = find()
    print("workflow : %s" % WF_NAME)
    print("nodes    : %s" % ", ".join(n["name"] for n in wf["nodes"]))
    print("calls    : %s  (send_ticket_notices, every 2 minutes)" % fn_url)
    print("target   : %s" % (("update %s (active=%s)" % (existing["id"], existing.get("active"))) if existing else "create new"))

    if "--activate" in sys.argv:
        if not existing:
            sys.exit("Nothing to activate -- run with --apply first.")
        W.api("POST", "/api/v1/workflows/%s/activate" % existing["id"])
        print("\nactivated: %s" % existing["id"])
        return
    if "--apply" not in sys.argv:
        print("\nDry run. Re-run with --apply to push.")
        return
    if existing:
        W.api("PUT", "/api/v1/workflows/%s" % existing["id"], wf)
        print("\nupdated %s" % existing["id"])
    else:
        wid = W.api("POST", "/api/v1/workflows", wf)["id"]
        print("\ncreated %s" % wid)
        print("Not active yet. Run with --activate.")


if __name__ == "__main__":
    main()
