"""Put a phone on the debt-call queue as a demo debtor, so the debt agent has a
real row to call and a real number to send the link to -- then take it off.

    python scripts/debt_demo_person.py on  +<country><number> --name clix
    python scripts/debt_demo_person.py off +<country><number>

`on` inserts one `residents` row (the name you give, building הרצל 112,
flat 1) and one `charges` row (July 2026, 450 shekels, unpaid), and prints the
`v_debt_call_queue_person` row the dashboard's debt tab and the Call button
read -- first name, apartments phrase, amount in words -- so you see what the
agent will say. `off` deletes the resident; the charge and every payment_links
row cascade with it.

WHY source = 'agent' ON BOTH ROWS. The twice-daily import
(`oxs_api_import.py`, 00:00 and 15:00 Israel) DELETES every resident whose
source is 'seed' -- the column default -- and the arrears sweep marks paid or
deletes only source = 'oxs' charges. 'agent' is the one value in the CHECK
constraint both leave alone, so a demo row inserted at noon is still there at
midnight. It is a small lie about provenance, named here, and `off` is how it
ends.

THE FLAT IS REAL AND OWES NOTHING. הרצל 112 flat 1 is the zero-balance flat the
18 Sep chat simulation used; OXS mints a real link for it, which opens a ₪0
balance while the agent says ₪450. Demo-only mismatch, because no real
debtor's flat is ever used for this. While the number is on file the chat bot
also serves it as that flat's resident (the payment link by chat included).

Refuses to touch a row it did not make: a number on file with any other
source, or under the paylink throwaway's name, is left alone either way.
"""
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n8n_whatsapp as W  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BUILDING = "הרצל 112, תל אביב - יפו"
UNIT = "1"
PERIOD = "2026-07-01"
AMOUNT = 450
SOURCE = "agent"


def main():
    args = sys.argv[1:]
    if len(args) < 2 or args[0] not in ("on", "off"):
        sys.exit(__doc__)
    mode, phone = args[0], args[1].strip()
    name = args[args.index("--name") + 1].strip() if "--name" in args else "clix"
    if not (phone.startswith("+") and phone[1:].isdigit() and 9 <= len(phone) <= 16):
        sys.exit("give the number in international form, +<country><number>")
    e = W.env()
    base = e["SUPABASE_URL"].rstrip("/") + "/rest/v1/"
    key = e["SUPABASE_SERVICE_ROLE_KEY"].strip()
    h = {"apikey": key, "Authorization": "Bearer " + key,
         "Content-Type": "application/json", "Prefer": "return=representation"}
    q = "residents?phone=eq." + urllib.parse.quote(phone, safe="")

    def call(method, path, body=None):
        req = urllib.request.Request(base + path, method=method, headers=h,
                                     data=json.dumps(body).encode() if body else None)
        try:
            return json.loads(urllib.request.urlopen(req, timeout=30).read() or b"[]")
        except urllib.error.HTTPError as ex:
            sys.exit("HTTP %s on %s: %s" % (ex.code, path.split("?")[0], ex.read().decode()[:300]))

    have = call("GET", q + "&select=id,full_name,building,unit,source")
    if mode == "on":
        if have and have[0]["source"] != SOURCE:
            sys.exit("…%s is on file as a real resident (%s, source %s); not touching it."
                     % (phone[-4:], have[0]["building"], have[0]["source"]))
        if have:
            rid = have[0]["id"]
            print("already on file: …%s -> %s flat %s (%s)" % (phone[-4:], have[0]["building"], have[0]["unit"], have[0]["full_name"]))
        else:
            r = call("POST", "residents", {"phone": phone, "full_name": name, "building": BUILDING,
                                           "unit": UNIT, "source": SOURCE})
            rid = r[0]["id"]
            print("resident: …%s -> %s, flat %s, named %s" % (phone[-4:], BUILDING, UNIT, name))
        ch = call("GET", "charges?resident_id=eq.%s&select=id,period,amount,status" % rid)
        if not ch:
            call("POST", "charges", {"resident_id": rid, "period": PERIOD, "amount": AMOUNT,
                                     "status": "unpaid", "unit": UNIT, "source": SOURCE})
            print("charge  : %s, %d shekels, unpaid" % (PERIOD, AMOUNT))
        else:
            print("charge  : already there (%s)" % ", ".join("%s %s %s" % (c["period"], c["amount"], c["status"]) for c in ch))
        row = call("GET", "v_debt_call_queue_person?resident_id=eq.%s&select=first_name,building,apartments_phrase,months_phrase,amount,charges" % rid)
        if not row:
            sys.exit("inserted, but the queue view does not list it -- check handed_over / do_not_call / attempts.")
        p = row[0]
        print("queue   : %s | %s | %s | %s | %s" % (p["first_name"], p["building"], p["apartments_phrase"], p["months_phrase"], p["amount"]))
        print("Now: /voice -> the debt tab shows %s -> Start call -> agree to pay." % p["first_name"])
    else:
        if not have:
            print("nothing on file for …%s" % phone[-4:])
            return
        if have[0]["source"] != SOURCE:
            sys.exit("…%s is a real resident (source %s); refusing to delete." % (phone[-4:], have[0]["source"]))
        gone = call("DELETE", q)
        print("off: removed %d resident row(s) for …%s (charges and link rows cascade)" % (len(gone), phone[-4:]))


if __name__ == "__main__":
    main()
