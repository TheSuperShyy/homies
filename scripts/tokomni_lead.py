# -*- coding: utf-8 -*-
r"""Put one tenant on Omni's dialer list ("List 2" in Tokomni) and see what reaches Vapi.

    python scripts/tokomni_lead.py              # dry run: the lead for flat 1 (Ido Clix), as it would go
    python scripts/tokomni_lead.py --unit 3     # another flat of the test building
    python scripts/tokomni_lead.py --apply      # send it: with List 2 playing, the dialer rings at once
    python scripts/tokomni_lead.py --check      # read only: the last two hours of phone calls on Vapi,
                                                # and where the lead's external_id arrived, if anywhere

THE TEST OMNI ASKED FOR (27 Oct, local/omnitelecom/2026-10-27-token-list2.txt): one
lead through the API with an external_id, then a look on Vapi for a header carrying
that value. No dialer call has carried one so far (21 and 26 Oct), so the router
(feature 18) tells a dialer call by its caller name, `dialer-<number>`, and finds
the tenant by that number.

THE LEAD. `external_id` is the tenant's resident id from `v_debt_call_queue_person`,
the id the router would look up once the header comes through, then the moment it
is sent, as the dashboard's /dialer page does. `number` is their mobile in the
local form of Omni's own example (10 digits, no country code, digits only).

THE ADDRESS (Omni, 8 Nov, local/omnitelecom/2026-11-08-lead-api-v1.txt). The one
in their first document was wrong, so every send got a 404, and the token we had
was for their dashboard (they deleted it). The lead API:

    POST https://api.tokomni.cc/api/v1/dialer/campaign/
    Authorization: Bearer <lead token, starts eyJ, valid a year>
    {"campaign_id": "<List 2>", "external_id": "<id>-<YYYYMMDDTHHMMSS>", "number": "05..."}

200 with `inserted_count`; 207 some in, some not (`failed_items`); 502 none (a
wrong list id); 400 nothing valid (`invalid`); 401 the token. A blacklisted number
is in `blacklisted_items` and is not rung, and the same number and external_id
already waiting is not added twice. external_id: up to 64 of A-Z a-z 0-9 - _ . :.
Omni passes it to the bot as the SIP header X-External-Id.

WHAT OMNI SAID ABOUT LIST 2
- It is stopped by hand until someone presses Play on it once in Tokomni. Until
  then a lead goes in and nobody is rung.
- Never press Stop on it: it does not start again by itself.
- Never upload a sheet into it through the list's edit: that replaces every
  contact in it. Hand uploads go in a list of their own.
- No calling hours on Omni's side: a lead sent at 2 AM is rung at 2 AM. So this
  refuses outside 09:00-20:00 Israel time, on Friday afternoon and on Saturday.

בר כוכבא 23 ONLY, hard-coded, like bk_reset_attempts.py: a lead is a real phone
ringing. TOKOMNI_TOKEN and TOKOMNI_CAMPAIGN_ID live in .env only.
"""
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n8n_whatsapp as W  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

INSERT = "https://api.tokomni.cc/api/v1/dialer/campaign/"
BUILDING = u"בר כוכבא 23, תל אביב - יפו"
ISRAEL = zoneinfo.ZoneInfo("Asia/Jerusalem")
VAPI = "https://api.vapi.ai"
# Vapi 403s Python's default User-Agent behind Cloudflare; Tokomni's app does the same.
UA = "curl/8.5.0"
AGENTS = {"10ae859a-f764-4b38-9154-cd8e82eb3a27": "incoming",
          "4bc03b57-018c-41bc-9c80-1b912b55496c": "debt"}
# Every header the 208 line's INVITEs carried from 21 to 26 Oct. Anything else is new.
SEEN = {"X-Account-Sid", "X-Application-Sid", "X-Authenticated-User", "X-CID", "X-FS-Support",
        "X-Forwarded-For", "X-OMNIUF-XT", "X-accountcode", "allow", "allow-events", "call-id",
        "contact", "content-disposition", "content-length", "content-type", "cseq", "from",
        "max-forwards", "min-se", "remote-party-id", "supported", "to", "user-agent", "via"}


def mask(s):
    """Phone numbers cut to their first and last three digits."""
    return re.sub(r"\d{7,}", lambda m: m.group(0)[:3] + "…" + m.group(0)[-3:], str(s))


def local_form(phone):
    """+9725XXXXXXXX -> 05XXXXXXXX; None for a number outside Israel."""
    p = re.sub(r"\D", "", phone or "")
    if p.startswith("972"):
        return "0" + p[3:]
    return p if p.startswith("0") and len(p) == 10 else None


def calling_hours(now):
    if now.weekday() == 5 or (now.weekday() == 4 and now.hour >= 13):
        return False
    return 9 <= now.hour < 20


def lead(e, unit):
    k = e["SUPABASE_SERVICE_ROLE_KEY"].strip()
    url = (e["SUPABASE_URL"].rstrip("/") + "/rest/v1/v_debt_call_queue_person"
           "?select=resident_id,phone,first_name,unit,amount,attempt"
           "&building=eq." + urllib.parse.quote(BUILDING, safe="")
           + "&unit=eq." + urllib.parse.quote(unit, safe=""))
    req = urllib.request.Request(url, headers={"apikey": k, "Authorization": "Bearer " + k})
    rows = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if len(rows) != 1:
        sys.exit("%d rows on the call list for flat %s of %s; expected one. Refusing to guess."
                 % (len(rows), unit, BUILDING))
    return rows[0]


def send(token, body):
    # Omni, 8 Nov: the token goes in the Authorization header, never in the URL.
    req = urllib.request.Request(
        INSERT, method="POST", data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as ex:
        return ex.code, ex.read().decode("utf-8", "replace")


def check(e, resident_id):
    since = (datetime.datetime.now(datetime.timezone.utc)
             - datetime.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    req = urllib.request.Request(VAPI + "/call?limit=100&createdAtGt=" + since, headers={
        "Authorization": "Bearer " + e["VAPI_PRIVATE_KEY"].strip(), "User-Agent": UA})
    calls = [c for c in json.loads(urllib.request.urlopen(req, timeout=60).read())
             if c.get("type") == "inboundPhoneCall"]
    print("looking for external_id %s\n" % resident_id)
    if not calls:
        print("No phone call on Vapi in the last two hours.")
        return
    for c in sorted(calls, key=lambda c: c["createdAt"]):
        sip = (c.get("phoneCallProviderDetails") or {}).get("sip") or {}
        h = sip.get("headers") or {}
        print("%s  %s UTC  %-8s  %s" % (
            c["id"][:8], c["createdAt"][11:19],
            AGENTS.get(c.get("assistantId"), c.get("assistantId") or "?"),
            mask((c.get("customer") or {}).get("name", ""))))
        hits = [k for k, v in h.items() if resident_id in str(v)]
        if hits:
            print("    external_id FOUND in header %s" % ", ".join(hits))
        elif resident_id in str(sip.get("raw", "")) + str(c.get("customer")):
            print("    external_id in the INVITE, but not as a header of its own")
        else:
            print("    external_id not in this call")
        for k, v in h.items():
            if k not in SEEN:
                print("    new header %s: %s" % (k, mask(v)))


def main():
    e = W.env()
    unit = sys.argv[sys.argv.index("--unit") + 1] if "--unit" in sys.argv else "1"
    row = lead(e, unit)
    if "--check" in sys.argv:
        return check(e, row["resident_id"])

    token = e.get("TOKOMNI_TOKEN", "").strip()
    campaign = e.get("TOKOMNI_CAMPAIGN_ID", "").strip()
    if not token or not campaign:
        sys.exit("TOKOMNI_TOKEN and TOKOMNI_CAMPAIGN_ID must be set in .env")
    number = local_form(row["phone"])
    if not number:
        sys.exit("%s's number is not an Israeli one; Omni's dialer is not tried on those."
                 % row["first_name"])
    # The dashboard's form (externalIdFor): the resident id, then the moment, so a second send
    # is a new lead and not "the same number and external_id already waiting".
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
    body = {"campaign_id": campaign, "external_id": "%s-%s" % (row["resident_id"], stamp), "number": number}
    now = datetime.datetime.now(ISRAEL)
    inside = calling_hours(now)

    print("campaign     %s…  (List 2)" % campaign[:8])
    print("token        %s  (%d characters)" % ("the lead token, eyJ…" if token.startswith("eyJ")
                                               else "NOT a lead token: Omni's start with eyJ", len(token)))
    print("the lead     %s, flat %s, %s owed, attempt %s"
          % (row["first_name"], row["unit"], row["amount"], row["attempt"]))
    print("  external_id  %s  (resident id, then the moment)" % body["external_id"])
    print("  number       %s" % mask(number))
    print("Israel time  %s: %s" % (now.strftime("%a %H:%M"),
                                  "inside calling hours" if inside else "OUTSIDE calling hours"))

    if "--apply" not in sys.argv:
        print("\nList 2 must be playing (Play pressed once in Tokomni) and the phone's owner ready to "
              "pick up.\nDry run. Re-run with --apply to send it.")
        return
    if not inside:
        sys.exit("\nREFUSING: the dialer rings at once, and it is outside 09:00-20:00 Israel time.")
    status, text = send(token, body)
    print("\nsent at %s UTC: HTTP %s  %s" % (
        datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S"), status, mask(text[:300])))
    print("When the call has ended: python scripts/tokomni_lead.py --check"
          + (" --unit %s" % unit if unit != "1" else ""))


if __name__ == "__main__":
    main()
