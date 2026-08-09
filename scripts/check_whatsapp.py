r"""Prove the WhatsApp bot still works, end to end, against the live system.

    python scripts/check_whatsapp.py

Exits non-zero on the first failure, so it can gate a deploy.

WHY THIS EXISTS

Every serious fault this bot has had was silent. Not one of them raised an
error, and not one would have been caught by reading the code:

  * the webhook was wired to output 0 of 2, so Meta's verification passed and
    every actual message was dropped with the execution ending `success`;
  * the WABA was subscribed to Meta's own dev-tools app instead of ours, so the
    callback URL showed verified and nothing was ever delivered;
  * the model was told `HM-2026-8884` and told the resident `2026-8884`;
  * every ticket for a week went to a spreadsheet while Supabase held one row;
  * a regex shipped with backspace characters where `\b` should have been — a
    valid pattern that matches nothing.

The common shape is that the happy path *looked* fine. So this file does not
check configuration, it checks CONSEQUENCES: it posts a real signed message at
the real URL and then looks in the database for the row. Anything less would
have passed on every one of the days above.

It writes to the live `requests` table and deletes what it wrote, under a
building number no real address uses.
"""

import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# A plausible street with an implausible number.
#
# The first version of this used "__selfcheck__" and the check failed — the bot
# asked WHICH BUILDING, because no building is called that. Correct behaviour,
# and a test fixture that the system under test is right to reject is a broken
# fixture. It has to look like an address to the model and like a test to a
# human, and the row is deleted either way. Matched on the number rather than
# the whole string, since the model may drop the definite article.
BUILDING = "הבדיקה 999"
BUILDING_MATCH = "requests?building=like.*999*"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def env():
    return dict(
        l.strip().split("=", 1)
        for l in open(os.path.join(ROOT, ".env"), encoding="utf-8")
        if l.strip() and not l.startswith("#") and "=" in l
    )


E = env()
FAILED = []


def check(name, ok, detail=""):
    print("  %-4s %-46s %s" % ("ok" if ok else "FAIL", name, detail))
    if not ok:
        FAILED.append(name)
    return ok


def get(url, headers=None, data=None, method="GET", timeout=60):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8")
            return r.status, (json.loads(body) if body.strip().startswith(("{", "[")) else body)
    except urllib.error.HTTPError as ex:
        body = ex.read().decode("utf-8")
        return ex.code, (json.loads(body) if body.strip().startswith(("{", "[")) else body)


def n8n(path):
    return get(E["N8N_BASE_URL"].strip().rstrip("/") + path,
               {"X-N8N-API-KEY": E["N8N_API_KEY"].strip()})[1]


def sb(path, method="GET", body=None):
    key = E["SUPABASE_SERVICE_ROLE_KEY"].strip()
    return get(E["SUPABASE_URL"].strip().rstrip("/") + "/rest/v1/" + path,
               {"apikey": key, "Authorization": "Bearer " + key,
                "Content-Type": "application/json"},
               json.dumps(body).encode() if body else None, method)


def envelope(frm, text):
    return {"object": "whatsapp_business_account", "entry": [{
        "id": E["WHATSAPP_WABA_ID"].strip(), "changes": [{"field": "messages", "value": {
            "messaging_product": "whatsapp",
            "metadata": {"phone_number_id": E["WHATSAPP_PHONE_NUMBER_ID"].strip()},
            "contacts": [{"profile": {"name": "selfcheck"}, "wa_id": frm}],
            "messages": [{"from": frm, "id": "wamid.CHK%d" % (time.time() * 1000000),
                          "timestamp": str(int(time.time())),
                          "type": "text", "text": {"body": text}}]}}]}]}


def post_message(frm, text, sign=True, bad=False):
    """Post at the live callback URL exactly as Meta would."""
    raw = json.dumps(envelope(frm, text), ensure_ascii=False,
                     separators=(",", ":")).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if sign:
        mac = hmac.new(E["APP_SECRET"].strip().encode(), raw, hashlib.sha256).hexdigest()
        headers["X-Hub-Signature-256"] = "sha256=" + ("0" * 64 if bad else mac)
    url = E["N8N_BASE_URL"].strip().rstrip("/") + "/webhook/" + "homies-whatsapp"
    return get(url, headers, raw, "POST")[0]


def main():
    print("\nWhatsApp bot self-check\n")

    # --- 1. The workflow is on, and shaped the way it is supposed to be ------
    print("n8n")
    wfs = {w["name"]: w for w in n8n("/api/v1/workflows?limit=100")["data"]}
    wf = wfs.get("Homies — WhatsApp bot")
    check("workflow exists", bool(wf))
    if not wf:
        sys.exit(1)
    full = n8n("/api/v1/workflows/%s" % wf["id"])
    check("workflow is active", full.get("active") is True)

    names = {n["name"]: n for n in full["nodes"]}
    hook = names.get("WhatsApp", {}).get("parameters", {})
    check("webhook takes GET and POST", hook.get("httpMethod") == ["GET", "POST"])
    check("webhook keeps the raw body", hook.get("options", {}).get("rawBody") is True)

    # BOTH webhook outputs must be wired. One output looks identical in the
    # editor and drops every message.
    outs = full["connections"].get("WhatsApp", {}).get("main", [])
    check("both webhook outputs wired", len(outs) == 2 and all(outs))

    # The tools must write to Supabase. This is the check that would have caught
    # a week of tickets going to a spreadsheet.
    tool_url = names.get("open_request", {}).get("parameters", {}).get("url", "")
    router = wfs.get("Homies — debt tools (Vapi)")
    writer = ""
    if router:
        writer = {n["name"]: n for n in n8n("/api/v1/workflows/%s" % router["id"])["nodes"]} \
            .get("Write, then answer", {}).get("parameters", {}).get("url", "")
    check("router writes to Supabase", "/functions/v1/debt-tools" in writer,
          writer.split("/")[2] if writer else "no router found")
    check("bot tools reach the router", "homies-debt-tools" in tool_url)

    # --- 2. Meta still points here ------------------------------------------
    print("\nmeta")
    app, secret = E["APP_ID"].strip(), E["APP_SECRET"].strip()
    app_token = "%s|%s" % (app, secret)
    subs = get("https://graph.facebook.com/v21.0/%s/subscriptions?access_token=%s"
               % (app, urllib.parse.quote(app_token)))[1].get("data", [])
    cb = next((s for s in subs if s.get("object") == "whatsapp_business_account"), {})
    check("callback registered and active", cb.get("active") is True,
          cb.get("callback_url", "")[-38:])

    token = E["WHATSAPP_ACCESS_TOKEN"].strip()
    d = get("https://graph.facebook.com/v21.0/debug_token?input_token=%s&access_token=%s"
            % (token, urllib.parse.quote(app_token)))[1].get("data", {})
    check("send token is valid", d.get("is_valid") is True)
    check("send token does not expire", not d.get("expires_at"),
          "" if not d.get("expires_at") else
          time.strftime("expires %Y-%m-%d %H:%M UTC", time.gmtime(d["expires_at"])))

    # The subscription that was silently missing: app-level registration says
    # where to deliver, this says the account is allowed to.
    waba = E["WHATSAPP_WABA_ID"].strip()
    apps = get("https://graph.facebook.com/v21.0/%s/subscribed_apps?access_token=%s"
               % (waba, urllib.parse.quote(token)))[1].get("data", [])
    ids = [a.get("whatsapp_business_api_data", {}).get("id") for a in apps]
    check("WABA is subscribed to this app", app in ids, ",".join(i for i in ids if i))

    # --- 3. A forged message is refused -------------------------------------
    print("\nsecurity")
    frm = "97250%07d" % (int(time.time()) % 10**7)
    check("unsigned message answers 200", post_message(frm, "x", sign=False) == 200,
          "200 always — Meta must never be told to retry")
    check("wrong signature answers 200", post_message(frm, "x", bad=True) == 200)

    before = sb(BUILDING_MATCH + "&select=reference")[1]
    check("forged messages wrote nothing", len(before) == 0, "%d rows" % len(before))

    # --- 4. A real message reaches the database -----------------------------
    # The only check that matters. Everything above can pass while this fails.
    print("\nend to end")
    text = "יש נזילת מים בלובי של %s, דחוף" % BUILDING
    check("signed message answers 200", post_message(frm, text) == 200)

    rows, waited = [], 0
    while waited < 45:
        time.sleep(3)
        waited += 3
        rows = sb(BUILDING_MATCH + "&select=reference,opened_via,urgency,unit")[1]
        if rows:
            break
    check("row reached Supabase", len(rows) == 1, "after %ds" % waited)
    if rows:
        check("channel recorded as whatsapp", rows[0]["opened_via"] == "whatsapp",
              rows[0]["opened_via"])
        check("common-area fault has no unit", rows[0]["unit"] in (None, ""),
              str(rows[0]["unit"]))

        # --- 5. And a second report of it does not become a second ticket ---
        post_message(frm, "הנזילה ב%s עדיין שם" % BUILDING)
        time.sleep(12)
        again = sb(BUILDING_MATCH + "&select=reference")[1]
        check("duplicate did not open a second ticket", len(again) == 1,
              "%d rows" % len(again))

    # --- Clean up after ourselves -------------------------------------------
    left = sb(BUILDING_MATCH, "DELETE")[0]
    print("\ncleanup: deleted %s rows (HTTP %s)" % (BUILDING, left))

    print()
    if FAILED:
        print("%d FAILED: %s\n" % (len(FAILED), ", ".join(FAILED)))
        sys.exit(1)
    print("all checks passed\n")


if __name__ == "__main__":
    main()
