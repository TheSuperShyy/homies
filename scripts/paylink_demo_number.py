"""Put a phone on file as a throwaway resident of a zero-balance flat, so the
payment link can be seen on a real handset -- then take it off again.

    python scripts/paylink_demo_number.py on  +9725XXXXXXXX
    python scripts/paylink_demo_number.py off +9725XXXXXXXX

`on` inserts one `residents` row (name בדיקת-מערכת, building הרצל 112, flat 1,
which owed nothing on 18 Sep) and refuses if the number is already a real
resident. Write "אני רוצה לשלם את ועד הבית" to the bot from that phone: the
link arrives in WhatsApp. `off` deletes the row; its payment_links rows
cascade with it. The link OXS minted stays valid (they never expire) and
opens that flat's balance, which is zero.
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

BUILDING = "הרצל 112, תל אביב - יפו"
UNIT = "1"
NAME = "בדיקת-מערכת סימולציית קישור"


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("on", "off"):
        sys.exit(__doc__)
    mode, phone = sys.argv[1], sys.argv[2].strip()
    if not phone.startswith("+972"):
        sys.exit("give the number as +972…")
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
