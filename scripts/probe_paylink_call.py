# -*- coding: utf-8 -*-
r"""send_payment_link as a debt call makes it, with no call and no AI.

    python scripts/probe_paylink_call.py                      # dry run: who would get it, and how
    python scripts/probe_paylink_call.py --apply              # send it: a real WhatsApp message
    python scripts/probe_paylink_call.py --template --apply   # as the template, the way a debt call sends it

WHY (10 Nov). On the first real debt call (26 Oct, Vapi 01a17807) the tenant said yes, the tool
took about 12 s, Vapi stopped waiting at 10, and the model improvised "the office will send it"
with a wrong number. The debt agent can only be reached through Omni's dialer, so a fix to the
tool cannot wait for a call to prove it. This posts the same `tool-calls` message Vapi posts,
for one tenant, and times the answer.

WHO GETS THE MESSAGE. Flat 2 of the test building and nobody else: the owner's own handset
(.env's OWNER_TEST_PHONE holds that number, and the debt list's row must match it). The link in
the message is that flat's real OXS link. Do not open it.
Until 11 Nov this read OXS_MIRROR_PHONES, which then held the owner's number and nothing else.
That day flats 1 and 3, two real people at Homies, joined that list on the owner's word, so "is
on the list" stopped meaning "is the owner's handset". The owner's number has its own name now.

THE TEMPLATE. A debt call rings someone who has not written to us, so their 24 hours are shut
and the link goes as the Meta template payment_link_he. The owner's handset usually HAS written
today, so `--template` asks the function for the template anyway. The function takes that
argument only from a call id that starts with "probe-", which no real call has.

WHAT IT LEAVES. One interactions row (call id probe-paylink-<time>), one payment_links row and
one payment ticket: resolved when the link went, open when it did not. A probe's open ticket is
never mirrored into OXS. Test tickets in this building are not deleted.

COST. Free text has the bot's model write one line (about 0.03 US cents on OpenRouter). The
template has no model in it.
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDING = u"בר כוכבא 23, תל אביב - יפו"
UNIT = "2"
DEBT_AGENT = "4bc03b57-018c-41bc-9c80-1b912b55496c"
REGION = "ap-northeast-1"          # where the function's database is; the agents' tools ask for it
UCHAT = "https://www.uchat.com.au/api"


def env():
    e = {}
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            e[k.strip()] = v.strip()
    return e


def mask(s):
    """Phone numbers cut to their first and last three digits."""
    return re.sub(r"\d{7,}", lambda m: m.group(0)[:3] + "…" + m.group(0)[-3:], str(s))


def rest(e, path):
    k = e["SUPABASE_SERVICE_ROLE_KEY"].strip()
    req = urllib.request.Request(e["SUPABASE_URL"].rstrip("/") + "/rest/v1/" + path,
                                 headers={"apikey": k, "Authorization": "Bearer " + k})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def uchat(e, path):
    key = (e.get("UCHAT_API_KEY") or e.get("Uchat_api_key") or "").strip()
    if not key:
        return None
    req = urllib.request.Request(UCHAT + path, headers={
        "Authorization": "Bearer " + key, "Accept": "application/json",
        # UChat's Cloudflare refuses some default user agents (error 1010); curl's passes.
        "User-Agent": "curl/8.9.1"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=30).read())
    except urllib.error.HTTPError:
        return None


def row_for_the_owner(e):
    rows = rest(e, "v_debt_call_queue_person?building=eq." + urllib.parse.quote(BUILDING, safe="")
                + "&unit=eq." + UNIT)
    if len(rows) != 1:
        sys.exit("%d rows on the debt call list for flat %s; expected one. "
                 "(After four calls a tenant leaves the list: scripts/bk_reset_attempts.py.)"
                 % (len(rows), UNIT))
    row = rows[0]
    own = e.get("OWNER_TEST_PHONE", "").strip()
    if not own or row["phone"] != own:
        sys.exit("Flat %s's number is not the owner's handset (OWNER_TEST_PHONE in .env). Refusing: "
                 "this probe messages a real phone." % UNIT)
    return row


def newest_from_us(e, phone):
    """UChat's newest message to this tenant that WhatsApp took: (when, how many id characters)."""
    info = uchat(e, "/subscriber/get-info-by-user-id?user_id=" + re.sub(r"\D", "", phone))
    ns = ((info or {}).get("data") or {}).get("user_ns")
    if not ns:
        return None
    msgs = uchat(e, "/subscriber/chat-messages?user_ns=" + urllib.parse.quote(ns) + "&include_bot=1&limit=5")
    for m in (msgs or {}).get("data") or []:
        if m.get("type") != "in" and str(m.get("mid") or ""):
            return int(m.get("ts") or 0), str(m["mid"])
    return None


def main():
    e = env()
    template = "--template" in sys.argv
    row = row_for_the_owner(e)
    charges = row["charges"] if isinstance(row["charges"], list) else json.loads(row["charges"])
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
    call_id = "probe-paylink-" + stamp
    values = {
        "resident_id": row["resident_id"], "phone": row["phone"], "first_name": row["first_name"],
        "gender": row.get("gender") or "", "building": row["building"], "unit": row["unit"],
        "amount": str(row["amount"]), "attempt": str(row.get("attempt") or "1"),
        "apartments_phrase": row.get("apartments_phrase") or "",
        "breakdown_phrase": row.get("breakdown_phrase") or "",
        "months_phrase": row.get("months_phrase") or "",
        # A string, as it survives the trip through Vapi.
        "charges": json.dumps(charges, ensure_ascii=False),
    }
    body = {"message": {
        "type": "tool-calls",
        "call": {"id": call_id, "type": "inboundPhoneCall", "assistantId": DEBT_AGENT,
                 "assistantOverrides": {"variableValues": values}},
        "toolCalls": [{"id": "probe-1", "type": "function", "function": {
            "name": "send_payment_link", "arguments": {"force_template": True} if template else {}}}],
    }}

    print("tenant       %s, flat %s, %s (the owner's handset)" % (row["first_name"], row["unit"], mask(row["phone"])))
    print("debt         %s shekels, %d months" % (row["amount"], len(charges)))
    print("call id      %s" % call_id)
    print("as           %s" % ("the template payment_link_he (asked for)" if template
                               else "free text if they wrote to us in the last 24 hours, else the template"))
    if "--apply" not in sys.argv:
        print("\nDry run. --apply sends a real WhatsApp message to that handset.")
        return

    before = newest_from_us(e, row["phone"])
    url = e["SUPABASE_URL"].rstrip("/") + "/functions/v1/debt-tools"
    req = urllib.request.Request(url, method="POST", data=json.dumps(body).encode("utf-8"), headers={
        "x-homies-secret": e["TOOL_SECRET"].strip(), "x-region": REGION,
        "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            status, raw = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as ex:
        status, raw = ex.code, ex.read().decode("utf-8", "replace")
    took = time.time() - t0
    print("\nanswered     HTTP %s in %.1f s (Vapi waits 10 s on the 208 line until its timeout is raised)" % (status, took))
    try:
        result = json.loads(json.loads(raw)["results"][0]["result"])
    except Exception:
        sys.exit("unreadable answer: " + raw[:200])
    shown = {k: v for k, v in result.items() if k != "note"}
    print("result       %s" % json.dumps(shown, ensure_ascii=False))

    inter = rest(e, "interactions?external_call_id=eq." + call_id + "&select=id")
    if inter:
        links = rest(e, "payment_links?interaction_id=eq." + inter[0]["id"] + "&select=status,note,created_at")
        for l in links:
            print("link row     %s / %s at %s UTC" % (l["status"], l["note"], l["created_at"][11:19]))
        tickets = rest(e, "requests?interaction_id=eq." + inter[0]["id"] + "&select=reference,status,type")
        for t in tickets:
            print("ticket       %s, %s (%s)" % (t["reference"], t["status"], t["type"]))
    after = newest_from_us(e, row["phone"])
    if after and after != before and after[0] >= t0 - 5:
        when = datetime.datetime.fromtimestamp(after[0], datetime.timezone.utc).strftime("%H:%M:%S")
        print("whatsapp id  yes: a %d-character id on our message of %s UTC, so WhatsApp took it" % (len(after[1]), when))
    else:
        print("whatsapp id  NONE on a new message of ours: WhatsApp did not take it")


if __name__ == "__main__":
    main()
