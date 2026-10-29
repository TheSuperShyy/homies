# -*- coding: utf-8 -*-
"""The n8n cron that keeps the WhatsApp test number registered: `Homies — WhatsApp number watch`.

    python scripts/n8n_number_watch.py              # dry run
    python scripts/n8n_number_watch.py --apply      # make the register credential (once), create or update the workflow
    python scripts/n8n_number_watch.py --activate   # switch it on
    python scripts/n8n_number_watch.py --drops      # the drops it has seen, from the workflow's static data

WHY
Meta has unregistered the test number (+1 555-178-1261) four times since 20 Oct: status PENDING,
platform NOT_APPLICABLE, health 141000/141001. The last time it happened under 2.5 hours after a
register. Each time the live bot went deaf until someone noticed.
- Nothing of ours unregisters it. The repo, n8n and Chatwoot 4.16.2 were checked (WORKLOG 29 Oct).
- Meta sends no notice.
- It is not idle time: the number ran from August to 20 Oct, quiet nights included.
So a keep-alive ping would not help, and registering again does. The owner, 29 Oct: "ok i think a
small checker for now is right", a standing go for this one write to Meta. The lasting fix is
Homies' own number on a verified business.

THE SHAPE
    Every 5 minutes -> Ask Meta about the number (GET status, platform_type)
      -> Unregistered? (not CONNECTED on the Cloud API)
      -> Room under Meta's limit? (Code; the register count lives in static data)
      -> Register the number (POST /register; the PIN comes from a credential)

META'S LIMIT
Register is limited to 10 calls per number in a moving 72 hours. The 11th returns 133016 and
blocks registering for 72 hours. So the Code node:
- stops at 8, counting the two registers made by hand on 29 Oct;
- never tries twice within 30 minutes;
- never retries a failed call, because each try counts as a call.
Past the cap, or on a status a register does not undo (FLAGGED, RESTRICTED, BANNED ...), it fails
the run. The red execution is the alarm. A register made by hand is invisible to that count: add its
time to BY_HAND in LIMIT_JS and re-run --apply.

THE PIN never sits in the workflow. The register node's Custom Auth credential carries the bearer
header and {"pin"} for the body. n8n's HTTP Request merges that into the JSON body (HttpRequestV3,
read on the instance 29 Oct). The credential is made once from .env (WHATSAPP_ACCESS_TOKEN,
WHATSAPP_REGISTER_PIN), and its id is kept as N8N_META_REGISTER_CRED_ID.

Every drop is written to the workflow's static data (`drops`, the last 200). The times of the drops,
the clue to what causes them, so survive execution pruning. `--drops` prints them.

Same rules as every workflow script here:
- found by NAME, so a re-run updates instead of duplicating;
- laid out on the grid (n8n_layout.py refuses otherwise);
- it only ever creates or updates THIS workflow and its one credential.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
from n8n_layout import LayoutError, check  # noqa: E402

WF_NAME = "Homies — WhatsApp number watch"
GRAPH = "https://graph.facebook.com/v23.0/"
# The bearer header the live bot's "Show typing" already uses; reading the status needs nothing more.
TYPING_CRED_NAME = "Homies WhatsApp typing (Meta)"
REGISTER_CRED_NAME = "Homies Meta register (WhatsApp number watch)"
REGISTER_CRED_VAR = "N8N_META_REGISTER_CRED_ID"

# Run once, on a drop only. Static data is the memory between runs (the live bot's Sort keeps
# its own the same way on this instance).
LIMIT_JS = r"""// Meta allows 10 registers per number in a moving 72 hours; the 11th blocks registering for 72 hours.
// So at most 8 here, counting the two made by hand on 29 Oct, and never two within 30 minutes.
const WINDOW = 72 * 3600 * 1000, CAP = 8, SPACING = 30 * 60 * 1000;
const BY_HAND = ['2026-10-29T15:51:41Z', '2026-10-29T18:37:16Z'];
const store = $getWorkflowStaticData('global');
const now = Date.now();
const { status, platform_type } = $input.first().json;
store.registers = (store.registers || []).filter(t => now - Date.parse(t) < WINDOW);
const recent = BY_HAND.concat(store.registers).filter(t => now - Date.parse(t) < WINDOW);
const last = Math.max(0, ...recent.map(t => Date.parse(t)));
// A register undoes only this drop: PENDING, off the Cloud API. FLAGGED, RESTRICTED or BANNED is Meta's call.
const undoable = status === 'PENDING' || platform_type === 'NOT_APPLICABLE';
const register = undoable && recent.length < CAP && now - last >= SPACING;
store.drops = (store.drops || []).concat([{ seen: new Date(now).toISOString(), status, platform_type, register }]).slice(-200);
if (!undoable) throw new Error(`The number is ${status} / ${platform_type}: not a drop a register undoes. Left for a person.`);
if (recent.length >= CAP) throw new Error(`${recent.length} registers in 72 hours, our cap of ${CAP} (Meta blocks at 10). Left for a person.`);
if (!register) return [];  // registered under 30 minutes ago: give Meta time
store.registers.push(new Date(now).toISOString());
return [{ json: { status, platform_type, registersIn72h: recent.length + 1 } }];
"""


def workflow(phone_id, typing_cred, register_cred):
    return {
        "name": WF_NAME,
        "settings": {"executionOrder": "v1", "timezone": "Asia/Jerusalem"},
        "nodes": [
            {
                "id": "why", "name": "Why this exists", "type": "n8n-nodes-base.stickyNote",
                "typeVersion": 1, "position": [0, -240],
                "parameters": {"height": 200, "width": 1180, "content":
                    "## Keeps the WhatsApp number registered\n"
                    "Meta has unregistered the test number four times since 20 Oct, and the bot goes deaf until "
                    "someone notices. Every 5 minutes this asks Meta for the number's status. If it is not CONNECTED "
                    "on the Cloud API, this registers it again; the PIN is in the credential. Meta allows 10 "
                    "registers in 72 hours and then blocks the number for 72, so this stops at 8 and fails the run "
                    "instead: **a red run here means a person is needed.** Owned by scripts/n8n_number_watch.py, "
                    "so edit there."},
            },
            {
                "id": "every5", "name": "Every 5 minutes", "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2, "position": [0, 0],
                "parameters": {"rule": {"interval": [{"field": "minutes", "minutesInterval": 5}]}},
            },
            {
                "id": "ask", "name": "Ask Meta about the number", "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2, "position": [240, 0],
                "parameters": {
                    "method": "GET", "url": GRAPH + phone_id + "?fields=status,platform_type",
                    "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
                    "options": {"timeout": 15000},
                },
                "credentials": {"httpHeaderAuth": typing_cred},
                "retryOnFail": True, "maxTries": 3, "waitBetweenTries": 5000,
            },
            {
                "id": "dropped", "name": "Unregistered?", "type": "n8n-nodes-base.if",
                "typeVersion": 2, "position": [480, 0],
                "parameters": {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 1},
                        "conditions": [{
                            "id": "c",
                            "leftValue": "={{ $json.status !== 'CONNECTED' || $json.platform_type !== 'CLOUD_API' }}",
                            "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                        }],
                        "combinator": "and",
                    },
                    "options": {},
                },
            },
            {
                "id": "limit", "name": "Room under Meta's limit?", "type": "n8n-nodes-base.code",
                "typeVersion": 2, "position": [720, 0],
                "parameters": {"jsCode": LIMIT_JS},
            },
            {
                "id": "register", "name": "Register the number", "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2, "position": [960, 0],
                "parameters": {
                    "method": "POST", "url": GRAPH + phone_id + "/register",
                    "authentication": "genericCredentialType", "genericAuthType": "httpCustomAuth",
                    "sendBody": True, "specifyBody": "json", "jsonBody": '{"messaging_product": "whatsapp"}',
                    "options": {"timeout": 30000},
                },
                "credentials": {"httpCustomAuth": register_cred},
                # Each try is a register call against Meta's 10 in 72 hours: never retried here.
                "retryOnFail": False,
            },
        ],
        "connections": {
            "Every 5 minutes": {"main": [[{"node": "Ask Meta about the number", "type": "main", "index": 0}]]},
            "Ask Meta about the number": {"main": [[{"node": "Unregistered?", "type": "main", "index": 0}]]},
            "Unregistered?": {"main": [[{"node": "Room under Meta's limit?", "type": "main", "index": 0}], []]},
            "Room under Meta's limit?": {"main": [[{"node": "Register the number", "type": "main", "index": 0}]]},
        },
    }


def find():
    for w in W.api("GET", "/api/v1/workflows?limit=100")["data"]:
        if w["name"] == WF_NAME:
            return w
    return None


def remember(var, value):
    """Append VAR=value to .env, in the file's own line ending."""
    path = os.path.join(W.ROOT, ".env")
    text = open(path, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in text else "\n"
    if text and not text.endswith(nl):
        text += nl
    text += "# n8n credential of the WhatsApp number watch (scripts/n8n_number_watch.py)" + nl + "%s=%s%s" % (var, value, nl)
    open(path, "w", encoding="utf-8", newline="").write(text)


def register_cred(e, apply):
    cid = e.get(REGISTER_CRED_VAR, "").strip()
    if cid:
        return {"id": cid, "name": REGISTER_CRED_NAME}, "kept"
    if not apply:
        return {"id": "<made on --apply>", "name": REGISTER_CRED_NAME}, "would make"
    secret = json.dumps({"headers": {"Authorization": "Bearer " + e["WHATSAPP_ACCESS_TOKEN"].strip()},
                         "body": {"pin": e["WHATSAPP_REGISTER_PIN"].strip()}})
    made = W.api("POST", "/api/v1/credentials", {"name": REGISTER_CRED_NAME, "type": "httpCustomAuth",
                                                 "data": {"json": secret}})
    if not made.get("id"):
        sys.exit("credential not created (its contents are not printed)")
    remember(REGISTER_CRED_VAR, made["id"])
    return {"id": made["id"], "name": REGISTER_CRED_NAME}, "made"


def main():
    e = W.env()
    if "--drops" in sys.argv:
        listed = find()
        if not listed:
            sys.exit("The workflow is not there yet -- run with --apply first.")
        wf = W.api("GET", "/api/v1/workflows/%s" % listed["id"])
        store = (wf.get("staticData") or {}).get("global") or {}
        for d in store.get("drops", []):
            print("%s  %s / %s  %s" % (d["seen"], d["status"], d["platform_type"],
                                       "registered" if d["register"] else "not registered"))
        print("registers in the last 72 h (automatic): %s" % (store.get("registers") or "none"))
        return
    apply = "--apply" in sys.argv
    for var in ("WHATSAPP_PHONE_NUMBER_ID", "N8N_WHATSAPP_TYPING_CRED_ID", "WHATSAPP_ACCESS_TOKEN", "WHATSAPP_REGISTER_PIN"):
        if not e.get(var, "").strip():
            sys.exit("%s is not in .env" % var)
    existing = find()
    reg, how = register_cred(e, apply)
    wf = workflow(e["WHATSAPP_PHONE_NUMBER_ID"].strip(),
                  {"id": e["N8N_WHATSAPP_TYPING_CRED_ID"].strip(), "name": TYPING_CRED_NAME}, reg)
    try:
        check(wf["nodes"], WF_NAME)
    except LayoutError as ex:
        sys.exit("\n%s\n" % ex)
    print("workflow   : %s" % WF_NAME)
    print("nodes      : %s" % ", ".join(n["name"] for n in wf["nodes"]))
    print("credential : %s %r (%s)" % (how, REGISTER_CRED_NAME, reg["id"]))
    print("target     : %s" % (("update %s (active=%s)" % (existing["id"], existing.get("active"))) if existing else "create new"))

    if "--activate" in sys.argv:
        if not existing:
            sys.exit("Nothing to activate -- run with --apply first.")
        W.api("POST", "/api/v1/workflows/%s/activate" % existing["id"])
        print("\nactivated: %s" % existing["id"])
        return
    if not apply:
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
