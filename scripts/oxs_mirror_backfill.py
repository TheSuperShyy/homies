# -*- coding: utf-8 -*-
"""Push an ALREADY-OPEN ticket into OXS, the way the live mirror would have.

    python scripts/oxs_mirror_backfill.py 255-1327-26            # dry run
    python scripts/oxs_mirror_backfill.py 255-1327-26 --apply    # write it

WHY this exists. `oxsMirror()` in the Edge Function runs at the moment a ticket
is created and never again, so a ticket opened before the mirror was switched
on (24 Sep, Edge Function v100) has `oxs_ref: null` for ever. `255-1327-26` was
opened seven minutes before the deploy and the owner asked for it in OXS
anyway: *"try and make this open in oxs"*.

THIS IS A WRITE INTO A CLIENT'S PRODUCTION SYSTEM, so it carries the same two
gates as the live mirror and one more of its own:

  1. `OXS_KEY_REQUESTS` must be in `.env`. The service_calls module is the only
     one OXS will issue a write key for; finance and general keys are read-only
     at creation, so there is no way for this script to touch anything else.
  2. The ticket's `reported_by_phone` must appear in `OXS_MIRROR_PHONES`. Same
     allow-list the function reads, so a ticket this script may push is exactly
     a ticket the live mirror would have pushed. An empty list pushes nothing.
  3. `oxs_ref` must be empty. A ticket already in OXS is never sent twice --
     which is what makes re-running this safe, and what keeps
     `oxs_requests_sync.py`'s reflection-skip honest.

It writes the created call's `_id` back to `requests.oxs_ref`, exactly as the
function does, so the importer recognises the call as ours and does not mint a
duplicate row from the feed.

DELIBERATELY ONE TICKET AT A TIME. There is no `--all`: a sweep over every
unmirrored ticket would push real residents' history into OXS the moment the
allow-list grew, and the allow-list is meant to be the only thing that decides.
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

OXS_CALLS = "https://api.oxs.co.il/api/external/v1/service-calls"


def main():
    args = [a for a in sys.argv[1:] if a != "--apply"]
    apply = "--apply" in sys.argv
    if len(args) != 1:
        sys.exit(__doc__.strip().splitlines()[2].strip())
    reference = args[0].strip()

    e = W.env()
    key = e.get("OXS_KEY_REQUESTS", "").strip()
    if not key:
        sys.exit("OXS_KEY_REQUESTS is not in .env -- the mirror is off, nothing to do.")
    allowed = [p.strip() for p in e.get("OXS_MIRROR_PHONES", "").split(",") if p.strip()]
    if not allowed:
        sys.exit("OXS_MIRROR_PHONES is empty -- by design that mirrors nobody. Refusing.")

    base = e["SUPABASE_URL"].rstrip("/") + "/rest/v1/"
    srk = e["SUPABASE_SERVICE_ROLE_KEY"].strip()
    h = {"apikey": srk, "Authorization": "Bearer " + srk,
         "Content-Type": "application/json", "Prefer": "return=representation"}

    def db(method, path, body=None):
        req = urllib.request.Request(
            base + path, method=method, headers=h,
            data=json.dumps(body).encode("utf-8") if body is not None else None)
        try:
            return json.loads(urllib.request.urlopen(req, timeout=30).read() or b"[]")
        except urllib.error.HTTPError as ex:
            sys.exit("HTTP %s on %s: %s" % (ex.code, path.split("?")[0],
                                            ex.read().decode()[:300]))

    got = db("GET", "requests?reference=eq." + urllib.parse.quote(reference, safe="")
             + "&select=id,reference,description,building,unit,oxs_ref,reported_by_phone")
    if not got:
        sys.exit("No ticket with reference %s." % reference)
    r = got[0]

    if r.get("oxs_ref"):
        print("%s is already in OXS (%s). Nothing to do." % (reference, r["oxs_ref"]))
        return
    phone = (r.get("reported_by_phone") or "").strip()
    if phone not in allowed:
        sys.exit("%s was reported by a number that is NOT on OXS_MIRROR_PHONES.\n"
                 "The live mirror would have skipped it, so this does too." % reference)

    address = (r.get("building") or "").strip()
    if not address:
        sys.exit("%s has no building -- the live mirror skips an unresolved building too."
                 % reference)
    b = db("GET", "buildings?address=eq." + urllib.parse.quote(address, safe="")
           + "&select=id,address")
    if len(b) != 1:
        sys.exit("%r matched %d buildings, need exactly one." % (address, len(b)))
    building_id = str(b[0]["id"])

    # Byte for byte the description oxsMirror() builds, so a backfilled call and
    # a live-mirrored one are indistinguishable to whoever reads them in OXS.
    unit = (r.get("unit") or "").strip()
    description = (r["description"]
                   + ((u" (דירה %s)" % unit) if unit else "")
                   + (u" [בוט, סימוכין %s]" % reference))

    print("ticket      : %s" % reference)
    print("building    : %s  (OXS %s)" % (address, building_id))
    print("reporter    : …%s  (on the allow-list)" % phone[-4:])
    print("description : %s" % description)

    if not apply:
        print("\nDry run. Re-run with --apply to create it in OXS.")
        return

    req = urllib.request.Request(
        OXS_CALLS, method="POST",
        headers={"x-api-key": key, "content-type": "application/json",
                 "user-agent": "homies-debt-tools/1.0"},
        data=json.dumps({"buildingId": building_id,
                         "description": description}).encode("utf-8"))
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=20).read() or b"{}")
    except urllib.error.HTTPError as ex:
        # Status and OXS's error string only -- never the body, which on this
        # API is a list of records.
        sys.exit("OXS refused: HTTP %s %s" % (ex.code, ex.read().decode()[:200]))

    oxs_id = ((d or {}).get("data") or {}).get("_id")
    if (d or {}).get("status") != 1 or not oxs_id:
        sys.exit("OXS did not create the call: %s" % json.dumps(d)[:200])

    db("PATCH", "requests?id=eq." + str(r["id"]), {"oxs_ref": str(oxs_id)})
    print("\ncreated in OXS: %s" % oxs_id)
    print("requests.oxs_ref written -- oxs_requests_sync.py will skip its own reflection.")


if __name__ == "__main__":
    main()
