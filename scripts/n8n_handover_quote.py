# -*- coding: utf-8 -*-
"""A WhatsApp price quote is emailed to the Management team: Yariv, Eden and Assaf Clix (26 Nov).

    python scripts/n8n_handover_quote.py                # dry run
    python scripts/n8n_handover_quote.py --dump F       # dry run, plus the would-be workflow in F
    python scripts/n8n_handover_quote.py --apply        # write it into "Homies — Hand to a person"
    python scripts/n8n_handover_quote.py --restore      # put the snapshot back
    python scripts/n8n_handover_quote.py --test         # ONE email, marked as a test, to our own address only

WHY. The owner, 26 Nov, after the Grok quote run: "... then will say the management team will get back to you i
took note of this one and forwarded it to them then the bot will send a summary of what happened in the email of
yariv, eden and assaf". Those three are the Management team in Chatwoot (team 3: yariv, עדן ממן, and our Assaf Clix
login), whom the quote's note already tags. The words Michael says are n8n_whatsapp_quote.py's (epoch 118); this is
the email.

WHERE. "Hand to a person" (oB66atFlWwtkSGgN) is the one place every team note goes through, after its own guard: a
second note of the same reason in a conversation within 24 hours is dropped there ("Anything to do?"), so a quote
noted twice is emailed once. The email goes after the Chatwoot work and before "Report back":
  Label it -> A quote to email? --yes--> Email the quote to management -> Report back
                                --no---------------------------------> Report back
"A quote to email?" is mode new, reason quote, and not the phone line (whose words are unchanged: its twin is owed).
The email cannot stop the note: it continues on error, after two tries five seconds apart.

WHAT IT SAYS. Plain text a manager can act on without opening anything: the tenant's name (Chatwoot's contact) and
phone, the request as Michael summed it up (notify_team's description: what it is for, the items, about how many,
where, the building), the link to the whole chat, and what the tenant was told (passed to the management team, who
will get back to him, no time).

WHO GETS IT. QUOTE_EMAILS in .env (comma-separated, written from Chatwoot's team 3, never in the repo), written into
the node at --apply. Change .env and re-run --apply to change it. The sender is the Brevo relay's verified one, the
same as Chatwoot's and the standing order's ("Homies Brevo SMTP", N8N_BREVO_SMTP_CRED_ID).
"""
import copy
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_handover as H  # noqa: E402
from n8n_layout import check  # noqa: E402
from chatwoot_smtp import VALUES as BREVO  # noqa: E402

WF_ID = "oB66atFlWwtkSGgN"
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-handover-live-26nov-before-quote.json")
GATE = "A quote to email?"
MAIL = "Email the quote to management"
STICKY = "Why a quote is emailed too"
LAST = "Label it"
REPORT = "Report back"
CHAT = "https://chat.srv1879140.hstgr.cloud/app/accounts/2/conversations/"

IN = "$('When handed a conversation').first().json"
GATE_EXPR = ("={{ $('Decide the routing').first().json.mode === 'new' && String(%s.reason || '').trim() === 'quote' "
             "&& String(%s.channel || '').trim() !== 'voice' }}" % (IN, IN))

WHO = ("(() => { try { return String((($('Read the conversation').first().json.meta || { }).sender || { }).name "
       "|| '').trim(); } catch (e) { return ''; } })()")
SUBJECT = ("={{ 'בקשה להצעת מחיר בוואטסאפ: ' + [%s, %s.phone].filter(Boolean).join(', ') }}" % (WHO, IN))

# Built in the node by expression, as the standing order's is: nothing here a Code node would do better.
TEXT = r"""={{ (() => {
  const inp = $('When handed a conversation').first().json;
  const who = %s;
  const conv = $('Decide the routing').first().json.conv_id;
  return [
    'דייר ביקש הצעת מחיר בוואטסאפ, ומיכאל, הבוט שלנו, רשם את הבקשה.',
    '',
    'שם: ' + (who || 'לא נמסר'),
    'טלפון: ' + (inp.phone || 'לא נמסר'),
    'הבקשה, כמו שמיכאל סיכם אותה: ' + (String(inp.description || '').trim() || '-'),
    '',
    'השיחה המלאה בצ\'אט: %s' + conv,
    '',
    'מה נאמר לדייר: שהבקשה נרשמה והועברה לצוות ההנהלה, ושהצוות יחזור אליו לגבי ההצעה. לא נאמר לו מתי.',
    '',
    "ההודעה נשלחה אוטומטית מהבוט של הומי'ז.",
  ].join('\n');
})() }}""" % (WHO, CHAT)

STICKY_TEXT = ("### A quote is emailed too (26 Nov)\n"
               "A new WhatsApp note with reason quote, past the guard above, is emailed to the Management team "
               "(Yariv, Eden, Assaf Clix: QUOTE_EMAILS in .env) with Michael's summary and a link to the chat. "
               "The phone line's quotes are not emailed yet. The email continues on error, so it never stops the "
               "note. Built by scripts/n8n_handover_quote.py.")


def new_nodes(to, smtp_id):
    if "}}" in WHO or "{{" in WHO:
        sys.exit("REFUSING: a double brace inside the expression would end it.")
    return [
        {"id": "handover-quote-sticky", "name": STICKY, "type": "n8n-nodes-base.stickyNote", "typeVersion": 1,
         "position": [2400, -480], "parameters": {"width": 720, "height": 200, "color": 4, "content": STICKY_TEXT}},
        H.if_node(GATE, (2400, 0), GATE_EXPR, "handover-quote-gate"),
        {"id": "handover-quote-mail", "name": MAIL, "type": "n8n-nodes-base.emailSend", "typeVersion": 2.1,
         "position": [2640, -180], "onError": "continueRegularOutput",
         "retryOnFail": True, "maxTries": 2, "waitBetweenTries": 5000,
         "parameters": {"fromEmail": BREVO["MAILER_SENDER_EMAIL"], "toEmail": to, "subject": SUBJECT,
                        "emailFormat": "text", "text": TEXT, "options": {"appendAttribution": False}},
         "credentials": {"smtp": {"id": smtp_id, "name": "Homies Brevo SMTP"}}},
    ]


def quote(live, to, smtp_id):
    """Live with the quote's email added after the Chatwoot work. Nothing else changes but Report back's place."""
    out = copy.deepcopy(live)
    names = {n["name"] for n in out["nodes"]}
    if GATE in names or MAIL in names:
        sys.exit("REFUSING: live already has %r." % GATE)
    by = {n["name"]: n for n in out["nodes"]}
    if out["connections"].get(LAST) != {"main": [[{"node": REPORT, "type": "main", "index": 0}]]}:
        sys.exit("REFUSING: %r does not lead straight to %r on live. Read live first." % (LAST, REPORT))
    by[REPORT]["position"] = [2880, 0]
    out["nodes"] += new_nodes(to, smtp_id)
    link = lambda name: [{"node": name, "type": "main", "index": 0}]  # noqa: E731
    out["connections"][LAST] = {"main": [link(GATE)]}
    out["connections"][GATE] = {"main": [link(MAIL), link(REPORT)]}
    out["connections"][MAIL] = {"main": [link(REPORT)]}
    return out


def recipients(e):
    to = ",".join(a.strip() for a in e.get("QUOTE_EMAILS", "").split(",") if "@" in a)
    if to.count("@") != 3:
        sys.exit("QUOTE_EMAILS in .env should hold the three Management addresses (Yariv, Eden, Assaf Clix).")
    return to


def test(e, smtp_id):
    """One test email through a temporary copy of the two new nodes, to our own address only, then deleted."""
    ours = [a for a in e["QUOTE_EMAILS"].split(",") if "@" in a and not a.strip().endswith("@homies-management.co.il")]
    if len(ours) != 1:
        sys.exit("Expected exactly one of our own addresses in QUOTE_EMAILS.")
    path = "homies-quote-mail-test-" + time.strftime("%H%M%S")
    code = lambda nid, name, x, y, js: {  # noqa: E731
        "id": nid, "name": name, "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [x, y],
        "parameters": {"jsCode": "return [{ json: %s }];" % js}}
    fake_in = json.dumps({"conv_id": 108, "phone": "+000000000", "reason": "quote", "channel": "",
                          "description": "בדיקה בלבד, לא בקשה של דייר: הצעת מחיר ל-4 מצלמות אבטחה בלובי ובחניה, "
                                         "בר כוכבא 23 דירה 2"}, ensure_ascii=False)
    nodes = [
        {"id": "qt-wh", "name": "Test call", "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [0, 0],
         "parameters": {"httpMethod": "POST", "path": path, "responseMode": "onReceived", "options": {}}},
        code("qt-in", "When handed a conversation", 240, 0, fake_in),
        code("qt-rd", "Read the conversation", 480, 0, json.dumps({"meta": {"sender": {"name": "בדיקה בלבד"}}},
                                                                    ensure_ascii=False)),
        code("qt-dr", "Decide the routing", 720, 0, json.dumps({"mode": "new", "conv_id": 108})),
    ]
    gate, mail = [copy.deepcopy(n) for n in new_nodes(ours[0].strip(), smtp_id)[1:]]
    gate["position"], mail["position"] = [960, 0], [1200, 0]
    mail["parameters"]["subject"] = mail["parameters"]["subject"].replace("={{ '", "={{ '[בדיקה] ", 1)
    nodes += [gate, mail]
    link = lambda name: [{"node": name, "type": "main", "index": 0}]  # noqa: E731
    conns = {"Test call": {"main": [link("When handed a conversation")]},
             "When handed a conversation": {"main": [link("Read the conversation")]},
             "Read the conversation": {"main": [link("Decide the routing")]},
             "Decide the routing": {"main": [link(GATE)]}, GATE: {"main": [link(MAIL), []]}}
    wf = W.api("POST", "/api/v1/workflows", {"name": "Homies — quote email test (temporary)", "nodes": nodes,
                                             "connections": conns, "settings": {"executionOrder": "v1"}})
    try:
        W.api("POST", "/api/v1/workflows/%s/activate" % wf["id"])
        url = "%s/webhook/%s" % (e["N8N_BASE_URL"].strip().rstrip("/"), path)
        req = urllib.request.Request(url, data=b"{}", method="POST",
                                     headers={"content-type": "application/json", "user-agent": "homies/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            print("webhook  : %s" % r.status)
        time.sleep(15)
        runs = W.api("GET", "/api/v1/executions?workflowId=%s&limit=1&includeData=true" % wf["id"])["data"]
        run = runs[0] if runs else {}
        ran = (((run.get("data") or {}).get("resultData") or {}).get("runData") or {})
        out = ((((ran.get(MAIL) or [{}])[-1].get("data") or {}).get("main") or [[]])[0] or [{}])[0].get("json", {})
        print("run      : %s, status %s" % (run.get("id"), run.get("status")))
        print("gate     : %s" % ("passed" if MAIL in ran else "did not pass"))
        print("mail     : %s" % (("accepted by the relay (%d)" % len(out.get("accepted", []))) if out.get("accepted")
                                 else json.dumps(out, ensure_ascii=False)[:300] or "did not run"))
    finally:
        W.api("DELETE", "/api/v1/workflows/%s" % wf["id"])
        print("harness  : deleted")


def main():
    e = W.env()
    smtp_id = e.get("N8N_BREVO_SMTP_CRED_ID", "").strip()
    if not smtp_id:
        sys.exit("N8N_BREVO_SMTP_CRED_ID is not in .env: run n8n_standing_order_email.py --apply once first.")
    if "--restore" in sys.argv:
        snap = json.load(open(SNAPSHOT, encoding="utf-8"))
        W.api("PUT", "/api/v1/workflows/%s" % WF_ID, {"name": snap["name"], "nodes": snap["nodes"],
                                                     "connections": snap["connections"],
                                                     "settings": snap.get("settings", {})})
        print("restored from %s" % os.path.relpath(SNAPSHOT, W.ROOT))
        return
    if "--test" in sys.argv:
        return test(e, smtp_id)
    to = recipients(e)
    live = W.api("GET", "/api/v1/workflows/%s" % WF_ID)
    if any(n["name"] == MAIL for n in live["nodes"]):
        print("Nothing to do. %r already has %r." % (live["name"], MAIL))
        return
    new = quote(live, to, smtp_id)
    check(new["nodes"], live["name"])
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("adds     : %s, %s, %s" % (GATE, MAIL, STICKY))
    print("wiring   : %s -> %s -> (yes) %s -> %s; (no) -> %s" % (LAST, GATE, MAIL, REPORT, REPORT))
    print("to       : %d addresses from QUOTE_EMAILS" % to.count("@"))
    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        json.dump(new, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("dumped   : %s" % path)
    if "--apply" not in sys.argv:
        print("\nDry run. Re-run with --apply to write it.")
        return
    if not os.path.exists(SNAPSHOT):
        json.dump(live, open(SNAPSHOT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    W.api("PUT", "/api/v1/workflows/%s" % WF_ID, {"name": live["name"], "nodes": new["nodes"],
                                                 "connections": new["connections"],
                                                 "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % WF_ID)
    same = (H.dumps(back["connections"]) == H.dumps(new["connections"])
            and H.dumps({n["name"]: n["parameters"] for n in back["nodes"]})
            == H.dumps({n["name"]: n["parameters"] for n in new["nodes"]}))
    print("\nwritten  : %d nodes, active=%s, %s" % (len(back["nodes"]), back.get("active"),
                                                   "read back as written" if same else "DIFFERS on read-back"))


if __name__ == "__main__":
    main()
