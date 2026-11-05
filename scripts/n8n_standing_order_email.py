# -*- coding: utf-8 -*-
"""Build "Homies — Standing order email": a standing-order request reaches the collections team by email.

    python scripts/n8n_standing_order_email.py                    # dry run
    python scripts/n8n_standing_order_email.py --apply            # create, or update in place
    python scripts/n8n_standing_order_email.py --apply --publish  # ...and activate (registers the webhook)
    python scripts/n8n_standing_order_email.py --test             # SENDS ONE EMAIL, marked as a test, to COLLECTIONS_EMAIL

WHY (5 Nov 2026, Yariv's change 3 of the 4 Nov review)
OXS's API has one-time payments only, so nothing of ours can set a standing
order (הוראת קבע) up. Homies' answer at the review: the request goes to the
collections team by email, because "I don't want another system I need to
monitor every time". So debt-tools' request_standing_order records it and posts
here, and this workflow emails it with what collections need to call the tenant
back: name, phone, building, apartment, the request's number and the tenant's
own words. The owner asked OXS the same day whether the API can start one
(local/oxs/2026-11-05-standing-order-api-email.txt); if it can, this is the
fallback, not the route.

WHY n8n SENDS IT, NOT THE EDGE FUNCTION
Supabase Edge Functions cannot open outgoing connections on the mail ports (25
and 587, and 465 is reported blocked too). This box can. Brevo's relay, the
account Chatwoot's mail already uses (scripts/chatwoot_smtp.py), took our login
on 587 from the PC on 5 Nov. The function posts here the way it posts a voice
note (scripts/n8n_voice_note.py): header-authenticated and answered on receipt,
so the tenant's reply never waits on a mail server.

THE SHAPE
  Webhook (header auth, 200 on receipt)
  -> Has a request? (a body with a reference; anything else ends here, unsent)
  -> Email the collections team (SMTP, Brevo, two tries five seconds apart)

WHO GETS IT
COLLECTIONS_EMAIL in .env, written into the node at --apply. Until Homies give
their collections address it is our own team inbox; to change it, change .env
and re-run --apply. The sender is the relay's verified one, the same as
Chatwoot's.

CREDENTIALS, in n8n's store, created through the public API from .env values
that are never printed, as n8n_voice_note.py does: "Homies Brevo SMTP"
(SMTP_KEY) and "Homies standing order secret" (a fresh
N8N_STANDING_ORDER_SECRET, which reaches the function as a function secret via
supabase_functions.py).
"""
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_handover as H  # noqa: E402
from chatwoot_smtp import VALUES as BREVO  # noqa: E402

WF_NAME = "Homies — Standing order email"
WEBHOOK_PATH = "homies-standing-order"
HOOK = "Standing order from the system"
GATE = "Has a request?"
MAIL = "Email the collections team"

SUBJECT = (
    "={{ 'בקשה להוראת קבע: ' + [$json.body.name || $json.body.phone, $json.body.building, "
    "$json.body.unit ? 'דירה ' + $json.body.unit : ''].filter(Boolean).join(', ') }}")

# One plain-text message a person at collections can act on without opening
# anything else. Built in the node by expression: there is nothing here a Code
# node would do better.
TEXT = r"""={{ (() => {
  const b = $json.body || {};
  const voice = b.channel === 'voice';
  const where = [b.building, b.unit ? 'דירה ' + b.unit : ''].filter(Boolean).join(', ');
  return [
    'דייר ביקש ' + (voice ? 'בשיחת טלפון' : 'בוואטסאפ') + ' להסדיר את התשלום החודשי בהוראת קבע.',
    '',
    'שם: ' + (b.name || 'לא נמסר'),
    'טלפון: ' + (b.phone || 'לא נמסר'),
    'כתובת: ' + (where || 'לא נמסרה'),
    'מספר הבקשה: ' + b.reference,
    (voice ? 'מה הדייר אמר: ' : 'מה הדייר כתב: ') + (b.said || '-'),
    '',
    'מה לעשות: ליצור קשר עם הדייר ולהקים את הוראת הקבע. הבוט לא ביקש ממנו פרטי כרטיס אשראי או חשבון בנק.',
    '',
    "ההודעה נשלחה אוטומטית מהבוט של הומי'ז.",
  ].join('\n');
})() }}"""


def ensure_creds(e):
    """The SMTP login and the webhook's header secret, created once; their ids live in .env."""
    smtp = e.get("N8N_BREVO_SMTP_CRED_ID", "").strip()
    if not smtp:
        key = e.get("SMTP_KEY", "").strip()
        if not key:
            sys.exit("SMTP_KEY is not in .env.")
        smtp = W.api("POST", "/api/v1/credentials", {
            "name": "Homies Brevo SMTP", "type": "smtp",
            "data": {"user": BREVO["SMTP_USERNAME"], "password": key, "host": BREVO["SMTP_ADDRESS"],
                     "port": int(BREVO["SMTP_PORT"]), "secure": False, "disableStartTls": False},
        })["id"]
        W.set_env("N8N_BREVO_SMTP_CRED_ID", smtp)
        print("credential: Homies Brevo SMTP -> %s" % smtp)
    hook = e.get("N8N_STANDINGORDER_CRED_ID", "").strip()
    if not hook:
        secret = e.get("N8N_STANDING_ORDER_SECRET", "").strip() or secrets.token_urlsafe(32)
        W.set_env("N8N_STANDING_ORDER_SECRET", secret)
        hook = W.api("POST", "/api/v1/credentials", {
            "name": "Homies standing order secret", "type": "httpHeaderAuth",
            "data": {"name": "x-homies-secret", "value": secret},
        })["id"]
        W.set_env("N8N_STANDINGORDER_CRED_ID", hook)
        print("credential: Homies standing order secret -> %s  (then: python scripts/supabase_functions.py)" % hook)
    return smtp, hook


def workflow(to, smtp_id, hook_id):
    nodes = [
        {"id": "standing-sticky", "name": "Why a standing order is an email",
         "type": "n8n-nodes-base.stickyNote", "typeVersion": 1, "position": [0, -300],
         "parameters": {"width": 720, "height": 240, "color": 4, "content":
             "### Standing order email\n"
             "A tenant asked for a standing order (הוראת קבע). OXS's API cannot set one up, so the "
             "debt-tools Edge Function records the request and posts it here (header-authenticated, "
             "answered on receipt), and this emails it to the collections team, as Homies asked on 4 Nov. "
             "Supabase cannot reach the mail ports; this box can. The address is COLLECTIONS_EMAIL in "
             ".env. Built by scripts/n8n_standing_order_email.py."}},
        {"id": "standing-webhook", "name": HOOK, "type": "n8n-nodes-base.webhook",
         "typeVersion": 2, "position": [0, 0], "webhookId": "homies-standing-order-v1",
         "parameters": {"httpMethod": "POST", "path": WEBHOOK_PATH,
                        "authentication": "headerAuth", "responseMode": "onReceived", "options": {}},
         "credentials": {"httpHeaderAuth": {"id": hook_id, "name": "Homies standing order secret"}}},
        H.if_node(GATE, (240, 0), "={{ !!($json.body && $json.body.reference) }}", "standing-gate"),
        {"id": "standing-mail", "name": MAIL, "type": "n8n-nodes-base.emailSend",
         "typeVersion": 2.1, "position": [480, 0],
         "retryOnFail": True, "maxTries": 2, "waitBetweenTries": 5000,
         "parameters": {"fromEmail": BREVO["MAILER_SENDER_EMAIL"], "toEmail": to,
                        "subject": SUBJECT, "emailFormat": "text", "text": TEXT,
                        "options": {"appendAttribution": False}},
         "credentials": {"smtp": {"id": smtp_id, "name": "Homies Brevo SMTP"}}},
    ]
    link = lambda name: [{"node": name, "type": "main", "index": 0}]  # noqa: E731
    connections = {HOOK: {"main": [link(GATE)]}, GATE: {"main": [link(MAIL), []]}}
    return {"name": WF_NAME, "nodes": nodes, "connections": connections,
            "settings": {"executionOrder": "v1", "timezone": "Asia/Jerusalem"}}


def find():
    for w in W.api("GET", "/api/v1/workflows?limit=250").get("data", []):
        if w["name"] == WF_NAME:
            return w
    return None


def test(e):
    """One made-up request through the live webhook, then the run it started, read back."""
    live = find()
    if live is None or not live.get("active"):
        sys.exit("%r is not published yet: --apply --publish first." % WF_NAME)
    url = "%s/webhook/%s" % (e["N8N_BASE_URL"].strip().rstrip("/"), WEBHOOK_PATH)
    body = {"reference": "TEST-%s" % time.strftime("%H%M%S"), "name": "בדיקה בלבד",
            "phone": "+000000000", "building": "בר כוכבא 23", "unit": "2", "channel": "whatsapp",
            "said": "בדיקה של המייל להוראת קבע. זו לא בקשה של דייר, אפשר למחוק."}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={
        "content-type": "application/json", "x-homies-secret": e["N8N_STANDING_ORDER_SECRET"],
        "user-agent": "homies-debt-tools/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print("webhook  : %s" % r.status)
    except urllib.error.HTTPError as err:
        sys.exit("webhook refused: %s" % err.code)
    time.sleep(12)
    runs = W.api("GET", "/api/v1/executions?workflowId=%s&limit=1&includeData=true" % live["id"])["data"]
    if not runs:
        sys.exit("no run found")
    run = runs[0]
    data = ((run.get("data") or {}).get("resultData") or {})
    ran = data.get("runData") or {}
    mail = (ran.get(MAIL) or [{}])[-1]
    print("run      : %s, status %s, finished %s" % (run["id"], run.get("status"), run.get("finished")))
    if data.get("error"):
        print("error    : %s" % str(data["error"].get("message"))[:300])
    out = (((mail.get("data") or {}).get("main") or [[]])[0] or [{}])[0].get("json", {})
    print("mail     : %s" % ("accepted, %s" % ", ".join(out.get("accepted", [])) if out.get("accepted")
                             else json.dumps(out, ensure_ascii=False)[:300] or "did not run"))


def main():
    e = W.env()
    if "--test" in sys.argv:
        return test(e)
    apply = "--apply" in sys.argv
    to = e.get("COLLECTIONS_EMAIL", "").strip()
    if "@" not in to:
        sys.exit("COLLECTIONS_EMAIL is not in .env: the address the collections team reads.")
    smtp_id = e.get("N8N_BREVO_SMTP_CRED_ID", "").strip() or "PENDING"
    hook_id = e.get("N8N_STANDINGORDER_CRED_ID", "").strip() or "PENDING"
    if apply:
        smtp_id, hook_id = ensure_creds(e)
    elif "PENDING" in (smtp_id, hook_id):
        print("credentials: would create 'Homies Brevo SMTP' and 'Homies standing order secret'")

    wf = workflow(to, smtp_id, hook_id)
    W.check(wf["nodes"], WF_NAME)
    live = find()
    if live is None:
        print("%s: does not exist yet -> would CREATE (%d nodes)" % (WF_NAME, len(wf["nodes"])))
    else:
        same = (H.dumps(live["nodes"]) == H.dumps(wf["nodes"])
                and H.dumps(live["connections"]) == H.dumps(wf["connections"]))
        print("%s: exists as %s (%d nodes, published=%s) -> %s"
              % (WF_NAME, live["id"], len(live["nodes"]), live.get("active"),
                 "already matches" if same else "would UPDATE"))
        if same:
            if "--publish" in sys.argv and apply:
                H.publish(live["id"])
            return
    print("webhook  : %s/webhook/%s" % (e["N8N_BASE_URL"].strip().rstrip("/"), WEBHOOK_PATH))
    if not apply:
        print("Dry run. Re-run with --apply to write it.")
        return
    out = (W.api("POST", "/api/v1/workflows", wf) if live is None
           else W.api("PUT", "/api/v1/workflows/%s" % live["id"], wf))
    print("written: %s (%s)" % (out.get("name"), out.get("id")))
    back = W.api("GET", "/api/v1/workflows/%s" % out["id"])
    print("verify : %d nodes, connections from %s" % (len(back["nodes"]), sorted(back["connections"])))
    if "--publish" in sys.argv:
        H.publish(out["id"])


if __name__ == "__main__":
    main()
