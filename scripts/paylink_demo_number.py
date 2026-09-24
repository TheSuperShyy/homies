"""Put a phone on file as a throwaway resident of a flat in OUR test building,
so the payment link can be seen on a real handset -- then take it off again.

    python scripts/paylink_demo_number.py on  +<country><number>
    python scripts/paylink_demo_number.py off +<country><number>

`on` inserts one `residents` row (name בדיקת-מערכת, building בר כוכבא 23,
flat 4 -- Homies' own test building, the one flat with no tenant) and refuses if the number is already a
real resident. Never point this at a client's building: see the note on
BUILDING below. Write "אני רוצה לשלם את ועד הבית" to the bot from that phone: the
link arrives in WhatsApp. `off` deletes the row; its payment_links rows
cascade with it. The link OXS minted stays valid (they never expire) and
opens that flat's balance, which is a real one in a building nobody lives in.
"""
import io
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n8n_whatsapp as W  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 24 Sep: moved off הרצל 112 flat 1. That is a real client's building, and the
# owner's rule is the whole reason this line changed: *"use the information that
# is in the bar kochba building always for testing because outside of that is
# real information of the clients and we dont want to edit those."* Inserting a
# invented resident into a real building is editing a client's data, even when
# the flat owes nothing and the row is deleted afterwards. בר כוכבא 23 is the
# building Yariv opened FOR us, so a test row there is a test row in a test
# building and nothing else.
#
# FLAT 4, and the reason is the tenant list. /buildings/:id/tenants (24 Sep)
# shows בר כוכבא 23 is occupied by our own people: flat 1 עידו קליקס, flat 2
# אסף קליקס, flat 3 יריב לוי -- Yariv being the client contact himself. Flat 4
# has no tenant and no phone, so a demo resident there names nobody real. Flat 2
# is also debt_demo_person.py's, and two demo residents in one flat make the
# resident lookup ambiguous.
#
# The zero balance is gone with the move: every בר כוכבא flat carries ועד בית at
# 250 a month, unpaid. That is the better default anyway -- a link that opens a
# real balance is what a resident actually receives, and a demo showing 0 proves
# nothing.
BUILDING = "בר כוכבא 23, תל אביב - יפו"
UNIT = "4"
NAME = "בדיקת-מערכת סימולציית קישור"


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("on", "off"):
        sys.exit(__doc__)
    mode, phone = sys.argv[1], sys.argv[2].strip()
    # Any country: the owner tests from a +63 handset, and an owner abroad is
    # a real case the function handles (18 Sep).
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
        return json.loads(urllib.request.urlopen(req, timeout=30).read() or b"[]")

    have = call("GET", q + "&select=id,full_name,building,unit")
    if mode == "on":
        if have and have[0]["full_name"] != NAME:
            sys.exit("…%s is already on file as a real resident (%s); not touching it."
                     % (phone[-4:], have[0]["building"]))
        if have:
            print("already on file: …%s -> %s flat %s" % (phone[-4:], BUILDING, UNIT))
            return
        r = call("POST", "residents", {"phone": phone, "full_name": NAME, "building": BUILDING, "unit": UNIT})
        print("on file: …%s -> %s, flat %s. Now write to the bot: אני רוצה לשלם את ועד הבית"
              % (phone[-4:], r[0]["building"], r[0]["unit"]))
    else:
        if not have:
            print("nothing on file for …%s" % phone[-4:])
            return
        if have[0]["full_name"] != NAME:
            sys.exit("…%s is a real resident; refusing to delete." % phone[-4:])
        gone = call("DELETE", q)
        print("off: removed %d row(s) for …%s (link rows cascade)" % (len(gone), phone[-4:]))


if __name__ == "__main__":
    main()
