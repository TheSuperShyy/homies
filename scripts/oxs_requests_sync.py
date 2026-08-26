#!/usr/bin/env python
"""Import Homies' own maintenance calls from OXS into `requests`.

    python scripts/oxs_requests_sync.py            # show what would change
    python scripts/oxs_requests_sync.py --apply    # write it

WHY THIS EXISTS

Residents have been reporting faults through OXS's resident app since February.
Our agents could not see one of them. So a resident who reported a leak in the
app and then asked our bot what was happening with it was told, truthfully and
uselessly, that no request could be found.

Re-running is safe: rows are matched on their `_id` through `requests.oxs_ref`,
which migration 014 made unique for imported rows. An existing row is updated,
never duplicated.

WHAT THIS IS NOT

It is not two-way. **Nothing here writes to OXS.** (The claim this docstring
used to make — that nothing *could* — stopped being true with External API v1,
which has POST/PUT/DELETE for service calls, and since 26 Aug `open_request`
in the Edge Function mirrors new tickets INTO OXS. This script remains the
import half only.) A ticket imported here cannot be closed from our side,
which is why imported rows are marked `opened_via = 'oxs'` — a staff member
has to be able to see at a glance which system owns the row in front of them.

AND THE MIRROR MAKES ONE SKIP NECESSARY. A ticket our bot opened now exists in
OXS too, created by our key, and OXS serves it back in the same feed as
everything else. Its `_id` was written to `requests.oxs_ref` by the mirror at
creation time, so any feed row whose `_id` is already held by a NON-imported
request is our own ticket coming back — importing it would mint a second row
for one fault (the upsert keys on `reference`, and their taskNumber is not our
reference). Those rows are skipped, not merged: the our-side row is the
resident's record and OXS's copy is downstream of it.

STATUS, AND WHAT WE DO NOT KNOW

Every call OXS returns reads `פתוחה`. That is either because the endpoint only
serves open calls, or because nothing is ever closed there. The API cannot tell
the two apart, and the difference matters: under the first reading a call that
disappears has been resolved, under the second it has not. Until Homies answers,
a row that stops being returned is left exactly as it is rather than being
guessed into `resolved`.

Measured 24 Aug and worth the ten seconds it took: 35 calls live against 69
imported, so 35 of ours had left the feed, three of them within one hour that
morning. `oxs_last_seen_at` is stamped on every ticket in every run, so "not
seen since" is now a date rather than an inference, and the day Homies answers
the question one UPDATE clears the backlog.

WHERE THE PROGRESS ACTUALLY LIVES

`status` is a constant, but `treatmentLog` is not: a list of the dispatcher's
own notes -- "הועבר לאלון שערים", "בטיפול דוד", "ממתינים לגופים מהקבלן" -- on 13
of the 35 live calls, with `lastUpdate` carrying a real timestamp on all 35.
That is the answer to "what is happening with my ticket", and until now none of
it reached us, so the bot could only ever say "open".

NEWEST FIRST: `lastUpdateNote` equals `treatmentLog[0]` on 13 of 13 and the last
element only where the list has one. Element 0 is current, the tail is history,
and the array is stored in their order.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OXS = "https://api.oxs.co.il/api/external/v1"

# One stamp for the whole run, set in main(). See its use in build().
SEEN_AT = None

# Their twelve categories, mapped to the slugs migration 014 constrains `type`
# to. The Hebrew label is stored beside it verbatim: the slug is for code, the
# label is what a dispatcher reads, and a translation of their own vocabulary
# back at them would be both rude and lossy.
CATEGORY = {
    "אינסטלציה": "plumbing",
    "חשמל": "electrical",
    "תאורה": "lighting",
    "מעלית": "elevator",
    "ניקיון": "cleaning",
    "גינון": "gardening",
    "הדברה": "pest_control",
    "מנעולן": "locksmith",
    "כיבוי אש": "fire_safety",
    "אחזקה": "maintenance",
    "אחר": "other",
}

# Their status vocabulary against ours. Only one value has ever been observed;
# the rest are here so an unknown one is loud rather than silently dropped.
STATUS = {
    "open": "open",
    "inProgress": "in_progress",
    "in_progress": "in_progress",
    "done": "resolved",
    "closed": "resolved",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}


def env():
    return dict(
        l.strip().split("=", 1)
        for l in open(os.path.join(ROOT, ".env"), encoding="utf-8")
        if l.strip() and not l.startswith("#") and "=" in l
    )


E = env()


def http(url, headers, data=None, method="GET"):
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8")
            return r.status, (json.loads(body) if body.strip().startswith(("{", "[")) else body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body


def oxs(path):
    # Vapi, Supabase's management API and this one all 403 or block Python's
    # default User-Agent at some point. Setting it once here costs nothing.
    code, payload = http(OXS + path, {"x-api-key": E["OXS_KEY_REQUESTS"].strip(),
                                      "User-Agent": "curl/8.0",
                                      "Accept": "application/json"})
    if code != 200:
        sys.exit("OXS %s -> HTTP %s" % (path, code))
    d = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(d, dict):
        d = d.get("results", d)
    return d if isinstance(d, list) else [d]


def sb(path, method="GET", body=None, prefer=None):
    key = E["SUPABASE_SERVICE_ROLE_KEY"].strip()
    h = {"apikey": key, "Authorization": "Bearer " + key,
         "Content-Type": "application/json"}
    if prefer:
        h["Prefer"] = prefer
    return http(E["SUPABASE_URL"].strip().rstrip("/") + "/rest/v1/" + path,
                h, json.dumps(body).encode() if body is not None else None, method)


def e164(raw):
    """Their phone shapes, into the one `residents.phone` uses."""
    d = "".join(c for c in str(raw or "") if c.isdigit())
    if not d:
        return None
    if d.startswith("972"):
        return "+" + d
    if d.startswith("0"):
        return "+972" + d[1:]
    return "+972" + d if len(d) == 9 else None


def norm(s):
    """Collapse whitespace for matching only. The stored value stays verbatim.

    Their addresses are the same strings ours are built from, except when they
    are not: 'היצירה  24, רמת גן' carries a double space and misses an otherwise
    exact match. One building out of 33 is not worth a fuzzy matcher, and is
    worth a split().
    """
    return " ".join(str(s or "").split())


def build(call, residents, by_bu):
    """One OXS service call, as a `requests` row."""
    scd = call.get("serviceCallData") or {}
    rb = scd.get("reportedBy") or {}
    cat = call.get("facilityCategory") or {}

    # WHOSE TICKET IS IT: building + apartment, NOT phone.
    #
    # `reportedBy.phone` exists on every record and is empty on every record —
    # the same shape-versus-value trap the OXS phone probe was written for, and
    # it caught this on the first run. `apartmentNumber` is filled on 32 of 33,
    # their address string is the one ours is built from, and the pair matches
    # 30 of 33 residents. So the join is the address, and the phone is kept only
    # in case they start populating it.
    phone = e164(rb.get("phone"))
    addr = (call.get("buildingId") or {}).get("address")
    unit = str(rb.get("apartmentNumber") or "").strip()
    resident_id = (residents.get(phone)
                   or by_bu.get((norm(addr), unit)))

    label = (cat.get("name") or "").strip()
    slug = CATEGORY.get(label, "other")
    raw_status = ((call.get("status") or {}).get("status") or "").strip()

    return {
        # Their number, verbatim. A resident who reported it in their app knows
        # this string and no other, so storing ours instead would make the
        # ticket unfindable by the only reference they hold.
        "reference": call.get("taskNumber"),
        "oxs_ref": call.get("_id"),
        "resident_id": resident_id,
        "type": slug,
        "category_he": label or None,
        "oxs_category_id": cat.get("_id"),
        "description": (scd.get("description") or "").strip() or "(ללא תיאור)",
        "building": norm(addr) or None,
        "unit": unit or None,
        "urgency": "high" if scd.get("isPriority") else "normal",
        "status": STATUS.get(raw_status, "open"),
        "opened_via": "oxs",
        "reported_by_name": (rb.get("name") or "").strip() or None,
        "reported_by_phone": phone,
        "source_platform": ((call.get("platform") or {}).get("label") or "").strip() or None,
        "image_count": len(call.get("images") or []),
        "oxs_created_at": call.get("createdAt"),
        # Their words, in their order, newest first. See the docstring: this is
        # the only thing on the record that says a ticket is moving, because
        # `status` says `open` on every call they have ever served.
        "oxs_notes": [n for n in (call.get("treatmentLog") or []) if str(n).strip()],
        "oxs_last_update": call.get("lastUpdate"),
        # Ours, not theirs. One timestamp for the whole run, so "last seen" sorts
        # cleanly instead of smearing across the seconds the loop took.
        "oxs_last_seen_at": SEEN_AT,
    }


def main():
    global SEEN_AT
    apply = "--apply" in sys.argv
    SEEN_AT = datetime.now(timezone.utc).isoformat()

    calls = oxs("/service-calls")
    print("OXS service calls: %d" % len(calls))

    # Two indexes, because the join that was supposed to work does not. Phone
    # first if it is ever populated, address second because it actually is.
    residents, by_bu, page = {}, {}, 0
    while True:
        code, rows = sb("residents?select=id,phone,building,unit&limit=1000&offset=%d"
                        % (page * 1000))
        if code != 200 or not rows:
            break
        for r in rows:
            if r.get("phone"):
                residents.setdefault(r["phone"], r["id"])
            by_bu.setdefault((norm(r.get("building")), str(r.get("unit") or "").strip()),
                             r["id"])
        if len(rows) < 1000:
            break
        page += 1
    print("residents on file: %d" % len(residents))

    rows = [build(c, residents, by_bu) for c in calls]

    # Our own tickets, coming back. The mirror in the Edge Function stamps the
    # created OXS _id into oxs_ref on the bot's row, so a feed item whose _id a
    # non-imported row already holds is not news — it is our ticket reflected.
    # Skipped BEFORE any counting: to every number below, it does not exist.
    # See "AND THE MIRROR MAKES ONE SKIP NECESSARY" in the docstring.
    code, ours = sb("requests?select=oxs_ref&oxs_ref=not.is.null"
                    "&opened_via=neq.oxs&limit=2000")
    mirrored = {r["oxs_ref"] for r in ours} if code == 200 else set()
    skipped = [r for r in rows if r["oxs_ref"] in mirrored]
    rows = [r for r in rows if r["oxs_ref"] not in mirrored]
    if skipped:
        print("ours, reflected back by OXS and skipped: %d" % len(skipped))

    # What is already here, so the print says new or updated rather than "33".
    code, have = sb("requests?select=oxs_ref&opened_via=eq.oxs&limit=2000")
    known = {r["oxs_ref"] for r in have} if code == 200 else set()
    new = [r for r in rows if r["oxs_ref"] not in known]

    matched = sum(1 for r in rows if r["resident_id"])
    from collections import Counter
    cats = Counter(r["category_he"] or "(none)" for r in rows)
    unknown = sorted({r["category_he"] for r in rows
                      if r["category_he"] and r["category_he"] not in CATEGORY})

    # WHAT OXS HAS STOPPED SERVING.
    #
    # The one number that says something is wrong, and it is not visible from
    # either side alone: their feed is only ever the open calls, ours is every
    # call we have ever seen, and the difference is the tickets that left. Not
    # touched here — see the docstring — but printed every run, because a
    # backlog that nobody is counting is a backlog nobody notices.
    gone = known - {r["oxs_ref"] for r in rows}

    print("  new: %d   already imported: %d" % (len(new), len(rows) - len(new)))
    print("  no longer served by OXS: %d of %d we hold "
          "(may be resolved — status unconfirmed)" % (len(gone), len(known)))
    print("  matched to a resident: %d of %d" % (matched, len(rows)))
    print("  with a progress note: %d of %d" % (sum(1 for r in rows if r["oxs_notes"]), len(rows)))
    print("  no building address: %d" % sum(1 for r in rows if not r["building"]))
    print("  categories: %s" % dict(cats))
    if unknown:
        print("  UNMAPPED CATEGORIES -> filed as other: %s" % unknown)

    if not apply:
        print("\nDry run. Re-run with --apply to write.")
        return

    # Upsert on `reference`, not on `oxs_ref`.
    #
    # `oxs_ref` is unique for imported rows, but only through a PARTIAL index
    # (`where oxs_ref is not null and opened_via = 'oxs'`), and Postgres will not
    # infer a conflict target from a partial index unless the statement repeats
    # its WHERE clause — which PostgREST has no way to express. It answers
    # 42P10, "no unique or exclusion constraint matching the ON CONFLICT
    # specification", which reads like a missing index and is not one.
    #
    # `reference` carries a plain unique constraint and holds their taskNumber,
    # so one row per OXS call is exactly what it enforces. The partial index
    # stays as the second guard: it is what stops a second row appearing under a
    # different reference for the same OXS id.
    code, res = sb("requests?on_conflict=reference", "POST", rows,
                   "resolution=merge-duplicates,return=minimal")
    if code >= 300:
        # Message only, never the body. PostgREST returns the offending row in
        # `details` on a constraint failure, and this now runs every fifteen
        # minutes into a log that anybody can read — one bad row would publish a
        # resident's name, apartment and the fault they reported.
        msg = res.get("message", res) if isinstance(res, dict) else res
        sys.exit("Supabase %s: %s" % (code, str(msg)[:200]))
    print("\nwrote %d rows (HTTP %s)" % (len(rows), code))

    code, after = sb("requests?select=reference&opened_via=eq.oxs&limit=2000")
    print("imported tickets now in the database: %d" % len(after))


if __name__ == "__main__":
    main()
