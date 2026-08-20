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
# A REAL building, resolved at run time, and a marker to find the rows by.
#
# This used to be the fictional "הבדיקה 999", chosen so the check's own rows were
# unmistakable and safe to delete. That stopped working the day `verify_address`
# became mandatory before `open_request`: the bot now checks every address
# against the portfolio and refuses one it does not manage, so a conversation
# about a building that does not exist can never produce a row. The check was
# asserting one anyway and had been red ever since — reading as a broken bot,
# and it was a broken check.
#
# So the address is real and the MARKER is what makes the row ours. It goes in
# the resident's own words, which is where the bot copies the description from,
# and every query and the cleanup match on it. Nothing is matched on the
# building any more, because the building now belongs to Homies and its real
# requests must never be in range of this file's DELETE.
MARKER = "בדיקת-מערכת-999"


def ours(frm, select=""):
    """Find this run's rows by the CONVERSATION they belong to.

    Matched on `interaction_id` — every WhatsApp write opens an interaction
    keyed `wa:<phone>`, and `frm` is minted fresh per run — rather than on the
    marker appearing in the description.

    THE MARKER STOPPED WORKING, AND THE BOT WAS RIGHT (20 Aug)
    This used to query `description like *<marker>*`, which assumed the bot
    copies the resident's message into the description verbatim. It does not,
    and it should not: the prompt tells it to write THE FAULT in the resident's
    words, so given "יש נזילת מים בלובי, דחוף. בדיקת-מערכת-999" it wrote
    "נזילת מים בלובי" and dropped the marker as the noise it is. The row was
    perfect and the query could not see it, so the check failed and read as a
    broken bot for the second time in this file's life.

    A fixture the system under test is right to reject is a broken fixture.
    That is written twice above this line already; this is the third.

    Also safer than what it replaced. The old DELETE matched free text, so a
    real resident writing the marker string would have had their ticket
    removed. This can only ever touch rows belonging to a phone number this
    process invented seconds ago.
    """
    ok, rows = sb("interactions?external_call_id=eq.wa:%s&select=id" % frm)
    if not rows:
        return []
    ids = ",".join(r["id"] for r in rows)
    return ids, "requests?interaction_id=in.(%s)%s" % (ids, select)


def our_rows(frm, select):
    got = ours(frm)
    if not got:
        return []
    return sb(got[1] + select)[1]


def our_path(frm):
    got = ours(frm)
    return got[1] if got else None


def a_real_building():
    """One address the portfolio actually contains, for the end-to-end walk.

    Read rather than hard-coded: the buildings table is imported from OXS and
    the names change when Homies takes a building on or lets one go. A constant
    here would fail silently one morning and look exactly like a bot failure,
    which is the whole problem this comment exists because of.
    """
    ok, rows = sb("buildings?select=address&active=is.true&limit=1")
    if not rows:
        sys.exit("No active buildings — import them before running this.")
    return rows[0]["address"]

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

    before = our_rows(frm, "&select=reference")
    check("forged messages wrote nothing", len(before) == 0, "%d rows" % len(before))

    # --- 4. A real conversation reaches the database ------------------------
    # The only check that matters. Everything above can pass while this fails.
    #
    # THREE MESSAGES, NOT ONE, AND THAT IS THE FIX OF 19 AUG.
    # This sent one message and asserted one row, and it had been failing for
    # some time while everything else passed — which reads as a broken bot and
    # was a broken check. The prompt is explicit that the first reply is an
    # OFFER and not an interrogation: "אתה מציע לפתוח קריאה — לא מתחיל לחקור",
    # and the address is asked for *after* they say yes. The reply the bot
    # actually gives is the prompt's own worked example, word for word.
    #
    # So one message can never produce a row, by design, and a check that
    # demanded one was testing a contract nobody agreed to. It now walks the
    # conversation the prompt promises: report, accept, address. If THAT does
    # not produce a row, something is genuinely wrong.
    print("\nend to end")
    building = a_real_building()
    print("  building:", building)
    turns = [
        "יש נזילת מים בלובי, דחוף. %s" % MARKER,   # the report, carrying the marker
        "כן, תפתח קריאה בבקשה",                     # accepting the offer
        "%s, דירה 4" % building,                    # where they live — a real address
    ]
    for i, text in enumerate(turns, 1):
        check("message %d answers 200" % i, post_message(frm, text) == 200,
              text[:38])
        # The agent has to answer before the next message means anything; a
        # burst arrives as three unanswered turns and tests nothing.
        if i < len(turns):
            time.sleep(12)

    rows, waited = [], 0
    while waited < 45:
        time.sleep(3)
        waited += 3
        rows = our_rows(frm, "&select=reference,opened_via,urgency,unit,status")
        if rows:
            break
    check("row reached Supabase", len(rows) == 1, "after %ds" % waited)
    if rows:
        check("channel recorded as whatsapp", rows[0]["opened_via"] == "whatsapp",
              rows[0]["opened_via"])
        check("common-area fault has no unit", rows[0]["unit"] in (None, ""),
              str(rows[0]["unit"]))
        # `needs_review` means the model never called open_request and the
        # rescue in transfer_to_human's neighbour wrote the row instead. The
        # resident still gets a real reference, so this is not a failure — but
        # it is the difference between the bot working and the net catching it,
        # and a green check that hides which one happened is worth nothing.
        print("       status: %s%s" % (
            rows[0]["status"],
            "   <- RESCUED, the model did not call open_request"
            if rows[0]["status"] == "needs_review" else ""))

        # --- 5. And a second report of it does not become a second ticket ---
        post_message(frm, "הנזילה עדיין שם. %s" % MARKER)
        time.sleep(12)
        again = our_rows(frm, "&select=reference")
        check("duplicate did not open a second ticket", len(again) == 1,
              "%d rows" % len(again))

    # --- Clean up after ourselves -------------------------------------------
    path = our_path(frm)
    left = sb(path, "DELETE")[0] if path else "nothing to delete"
    print("\ncleanup: deleted this run's rows (HTTP %s)" % left)

    print()
    if FAILED:
        print("%d FAILED: %s\n" % (len(FAILED), ", ".join(FAILED)))
        sys.exit(1)
    print("all checks passed\n")


if __name__ == "__main__":
    main()
