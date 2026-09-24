# -*- coding: utf-8 -*-
"""Simulate the OXS ticket mirror end to end, and leave NOTHING behind.

    python scripts/check_oxs_mirror.py              # dry run: print the payload
    python scripts/check_oxs_mirror.py --apply      # create, read back, DELETE

WHY. Until now the only way to see what the mirror puts into OXS was to send a
real WhatsApp message and then go and look, which costs a model call, leaves a
ticket on both sides, and tells you nothing when it fails. The owner, 24 Sep:
*"how can we simulate the things we are doing??"* -- so this does the whole
round trip against the live API and deletes the call it made, the same
create-read-delete shape that proved the mirror on 26 Aug.

WHAT IT PROVES, which a dry run cannot: whether OXS honours `reportedBy` on
create at all. The August docstring says created records "carry no OXS user
(the spec attributes them to the API key)", and every call this script makes is
read back field by field so that claim is checked rather than repeated.

STRICTLY בר כוכבא 23. The building is hard-coded and there is no flag to change
it: every other building in OXS is a live client's, and a simulator that can be
pointed anywhere eventually is. The call is deleted at the end whatever the
result, including on a failed assertion.

THE NAME IS THE REAL OXS TENANT'S, NEVER OURS. `residents` holds two rows for
flat 2: the demo row behind the owner's +63 tester (`source='agent'`, named
a placeholder name) and the genuine imported tenant (`source='oxs'`, carrying
`oxs_ref`). Only the second may be sent back to OXS -- a name OXS gave us is
the only name it gets from us. If no `oxs`-sourced tenant is found for the
flat, no name is sent at all; a blank reporter is recoverable, a wrong one in a
client's system is not.
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

API = "https://api.oxs.co.il/api/external/v1"
BUILDING = u"בר כוכבא 23, תל אביב - יפו"   # the ONE building opened for us
UNIT = "2"                                  # the owner's +63 tester sits here
DESCRIPTION = u"בדיקת מערכת, אפשר להתעלם ולמחוק."


def main():
    apply = "--apply" in sys.argv
    e = W.env()
    key = e.get("OXS_KEY_REQUESTS", "").strip()
    if not key:
        sys.exit("OXS_KEY_REQUESTS is not in .env -- nothing to simulate.")

    base = e["SUPABASE_URL"].rstrip("/") + "/rest/v1/"
    srk = e["SUPABASE_SERVICE_ROLE_KEY"].strip()
    sh = {"apikey": srk, "Authorization": "Bearer " + srk}

    def db(path):
        req = urllib.request.Request(base + path, headers=sh)
        return json.loads(urllib.request.urlopen(req, timeout=30).read() or b"[]")

    def oxs(method, path, body=None):
        req = urllib.request.Request(
            API + path, method=method,
            headers={"x-api-key": key, "content-type": "application/json",
                     "user-agent": "homies-debt-tools/1.0"},
            data=json.dumps(body).encode("utf-8") if body is not None else None)
        # ONE urlopen per call: a POST sent twice creates two service calls,
        # and only one of them would be deleted at the end.
        try:
            res = urllib.request.urlopen(req, timeout=20)
            return res.status, json.loads(res.read() or b"{}")
        except urllib.error.HTTPError as ex:
            return ex.code, {"error": ex.read().decode()[:200]}

    # --- resolve the building and the flat, exactly as the mirror does -------
    b = db("buildings?address=eq." + urllib.parse.quote(BUILDING, safe="") + "&select=id")
    if len(b) != 1:
        sys.exit("%r matched %d buildings, need exactly one." % (BUILDING, len(b)))
    building_id = str(b[0]["id"])
    flats = db("apartments?building_id=eq." + building_id + "&select=id,number")
    hits = [f for f in flats if str(f.get("number", "")).strip() == UNIT]
    apartment_id = str(hits[0]["id"]) if len(hits) == 1 else None

    # --- the reporter: the OXS-sourced tenant of that flat, or nobody -------
    who = db("residents?building=eq." + urllib.parse.quote(BUILDING, safe="")
             + "&unit=eq." + UNIT + "&source=eq.oxs&select=full_name,oxs_ref")
    who = [r for r in who if r.get("oxs_ref")]
    reported_by = None
    if len(who) == 1:
        reported_by = {"entity": "payer", "entityId": str(who[0]["oxs_ref"]),
                       "name": who[0]["full_name"], "apartmentNumber": UNIT}
        if apartment_id:
            reported_by["apartmentId"] = apartment_id

    payload = {"buildingId": building_id, "description": DESCRIPTION}
    if reported_by:
        payload["serviceCallData"] = {"reportedBy": reported_by}
        payload["reportedBy"] = reported_by      # both shapes; OXS may take either

    print("building    : %s  (OXS %s)" % (BUILDING, building_id))
    print("flat        : %s  (apartment %s)" % (UNIT, apartment_id or "UNRESOLVED"))
    print("reporter    : %s" % (json.dumps(reported_by, ensure_ascii=False)
                                if reported_by else "NONE — no oxs-sourced tenant on this flat"))
    print("payload     : %s" % json.dumps(payload, ensure_ascii=False)[:300])
    if not apply:
        print("\nDry run. Re-run with --apply to create it, read it back and delete it.")
        return

    # --- create -------------------------------------------------------------
    code, d = oxs("POST", "/service-calls", payload)
    oxs_id = ((d or {}).get("data") or {}).get("_id")
    if (d or {}).get("status") != 1 or not oxs_id:
        sys.exit("create failed: HTTP %s %s" % (code, json.dumps(d, ensure_ascii=False)[:250]))
    print("\ncreated     : %s" % oxs_id)

    # Bound BEFORE the try: the finally block reads it, and a read-back that
    # throws must still leave a name for the cleanup to look at.
    got = None
    try:
        # --- read back ------------------------------------------------------
        code, d = oxs("GET", "/service-calls?buildingId=" + building_id)
        rows = d if isinstance(d, list) else (d.get("data") or [])
        got = next((c for c in rows if str(c.get("_id")) == oxs_id), None)
        if not got:
            print("READ BACK   : NOT FOUND in the building listing (HTTP %s)" % code)
        else:
            scd = got.get("serviceCallData") or {}
            rb = scd.get("reportedBy") or {}
            print("task number : %s" % got.get("taskNumber"))
            print("description : %s" % scd.get("description"))
            print("\n--- what OXS actually STORED for the reporter ---")
            for f in ("entity", "entityId", "name", "apartmentNumber", "apartmentId", "phone"):
                print("  %-15s: %r" % (f, rb.get(f)))
            want = (reported_by or {}).get("name")
            if want and rb.get("name") == want:
                print("\nVERDICT     : reportedBy IS honoured on create — the name is %s." % want)
            elif want:
                print("\nVERDICT     : reportedBy is IGNORED on create — OXS stored %r, not %r."
                      % (rb.get("name"), want))
    finally:
        # --- always delete, whatever happened above -------------------------
        #
        # BY TASK NUMBER AND buildingId, never by `_id`. The `_id` is returned
        # by the create and works nowhere else: GET and DELETE both answer it
        # with `403 "Resource does not belong to this company"`, which reads as
        # a permissions failure and is really a wrong-key-shaped lookup. Found
        # 24 Sep by leaving a test call behind in a client's system.
        task = (got or {}).get("taskNumber") if got else None
        if not task:
            print("\nNOT DELETED : no task number came back, so %s is still in OXS. "
                  "Delete it by hand." % oxs_id)
        else:
            code, d = oxs("DELETE", "/service-calls/%s?buildingId=%s" % (task, building_id))
            ok = (d or {}).get("status") == 1 or ((d or {}).get("data") or {}).get("deleted")
            print("\ndeleted     : %s (HTTP %s)%s"
                  % (task, code, "" if ok else "  <-- STILL THERE, delete it by hand"))


if __name__ == "__main__":
    main()
