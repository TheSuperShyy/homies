"""Put a phone on the debt-call queue as a demo debtor, so the debt agent has a
real row to call and a real number to send the link to -- then take it off.

    python scripts/debt_demo_person.py on  +<country><number> --name clix [--unit 1]
    python scripts/debt_demo_person.py off +<country><number>

`on` inserts one `residents` row (the name you give, building בר כוכבא 23,
flat 2) and one `charges` row per unpaid month, and prints the
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

THE FLAT IS HOMIES' OWN TEST FLAT (23 Sep). Yariv opened בר כוכבא 23 for us
with ten flats and ועד בית at 250 a month, unpaid. Flat 2 is Asaf's, chosen by
the owner: the payment page names Asaf while the message arrives on the owner's
own handset, because OXS tenants are read-only and their phone cannot be changed
from here. So the link opens a real balance on a flat nobody lives in, and the
amount the agent says comes from the same charges OXS shows. Until
this, the demo borrowed a real resident's flat and said 450 over a 0 balance.
While the number is on file the chat bot also serves it as that flat's
resident (the payment link by chat included).

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

# 23 Sep: moved off הרצל 112 flat 1, a real resident's flat that owes nothing,
# onto Homies' own test building. Yariv opened בר כוכבא 23 for us that day with
# ten flats and ועד בית charged at 250 a month, none of it paid -- so for the
# first time the amount the agent says and the balance the link opens come from
# the same place. Flat 2 by the owner's choice (23 Sep): it is Asaf's flat in
# OXS, so the payment page names him while the message comes to the owner's own
# handset -- which is the point, since OXS tenants are read-only and a phone
# there cannot be changed from here. Flat 4 is the unnamed one if a blank payer
# is ever wanted instead.
BUILDING = "בר כוכבא 23, תל אביב - יפו"
UNIT = "2"
# The months OXS shows as charged and unpaid, up to the last one that has ended
# -- the same rule oxs_arrears.py uses, so the demo says what a real debtor's
# row would say. September is left out until its due date passes.
CHARGES = [("2026-%02d-01" % m, 250) for m in range(1, 9)]
SOURCE = "agent"


def main():
    args = sys.argv[1:]
    if len(args) < 2 or args[0] not in ("on", "off"):
        sys.exit(__doc__)
    mode, phone = args[0], args[1].strip()
    name = args[args.index("--name") + 1].strip() if "--name" in args else "clix"
    # --unit, 24 Sep: בר כוכבא 23 has a tenant per flat (1 עידו קליקס,
    # 2 אסף קליקס, 3 יריב לוי, 4 empty), so which flat the demo sits on decides
    # whose name the OXS payment page shows. Sending to Ido means flat 1, his
    # own, or the page names somebody else. Default stays 2.
    unit = args[args.index("--unit") + 1].strip() if "--unit" in args else UNIT
    if unit not in [str(n) for n in range(1, 11)]:
        sys.exit("--unit must be a flat in בר כוכבא 23, 1 to 10 (got %r)" % unit)
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
                                           "unit": unit, "source": SOURCE})
            rid = r[0]["id"]
            print("resident: …%s -> %s, flat %s, named %s" % (phone[-4:], BUILDING, unit, name))
        ch = call("GET", "charges?resident_id=eq.%s&select=id,period,amount,status" % rid)
        if not ch:
            call("POST", "charges", [{"resident_id": rid, "period": p, "amount": a,
                                      "status": "unpaid", "unit": unit, "source": SOURCE}
                                     for p, a in CHARGES])
            print("charges : %d months, %d shekels each, %d total, unpaid"
                  % (len(CHARGES), CHARGES[0][1], sum(a for _, a in CHARGES)))
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
