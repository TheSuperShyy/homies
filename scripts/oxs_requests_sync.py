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

STATUS, AND HOW THE QUESTION WAS SETTLED

This docstring said for three weeks that the API could not tell two readings
apart -- "the endpoint only serves open calls" versus "nothing is ever closed
there" -- and 36 of our tickets sat flagged `gone from OXS` on the dashboard,
unresolved, on that basis. It was waiting on an answer from Homies.

The answer was in OXS's own spec the whole time. `GET /service-calls` takes a
`status` parameter and, in their words (`OXS_External_API_v1.pdf` p.6), it
"defaults to open". We had never sent it -- this script called the endpoint
bare. Every record reading `פתוחה` was the documented default filter doing
exactly what it says on the tin, and none of it was evidence about how Homies
works.

Probed live on 31 Aug, `scripts/oxs_status_probe.py`:

    (bare)          42 calls     identical to status=open, which is the default
    status=open     42 calls
    status=close    26,903 calls across 1,346 pages

OXS closes calls constantly. The feed is the open ones. **A ticket that leaves
it has been closed**, and the eight oldest departures, fetched back by
taskNumber, each returned `status.status = "close"` carrying a `doneDate` and a
`closedBy` naming the staff member who closed it.

TWO THINGS THE SPEC GETS WRONG. Both measured, not read:

  * The status value is `close`, not `closed`. Sending `closed` returns zero
    rows and no error, which is exactly how a wrong guess here stays invisible.
  * A paginated response is not `{data: [], total, pages}` as the PDF's example
    shows. Passing `page` changes the shape of `data` from an array into
    `{finalList, totalCount, totalPages}`, twenty per page. The unpaginated call
    returns the whole open set (42 of 42), so this script has never truncated —
    but it would have, silently, the moment the open list outgrew one response.

WHY WE DO NOT IMPORT THE CLOSED FEED. 26,903 calls is Homies' entire history and
almost none of it is ours. Only the tickets we already hold matter, so a
departure is resolved by fetching that one call back by `taskNumber` — bounded,
because a ticket is looked up once and then carries a closed status that takes
it out of the set.

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
import urllib.parse
import urllib.request
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OXS = "https://api.oxs.co.il/api/external/v1"

# One stamp for the whole run, set in main(). See its use in build().
SEEN_AT = None

# 60 requests a minute per key. The departed-ticket lookups are the only loop
# here that can approach it; this is the pace oxs_buildings_sync.py already uses.
PACE = 1.05

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

# Their status vocabulary against ours.
#
# TWO values have been observed, 31 Aug: `open` in the feed and `close` on every
# call fetched back after it left. `close` is the one that matters and it was
# missing here until then — this table was written from the spec, which spells
# it `closed`, and `STATUS.get("close", "open")` would have quietly filed every
# closed ticket as open. The rest are kept so an unknown value is loud rather
# than silently dropped; see `unmapped` in main(), which now exits non-zero.
STATUS = {
    "open": "open",
    "close": "resolved",      # observed, and the only closed form OXS returns
    "closed": "resolved",     # spec spelling, never seen
    "inProgress": "in_progress",
    "in_progress": "in_progress",
    "done": "resolved",
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


def oxs(path, fatal=True, **params):
    # Vapi, Supabase's management API and this one all 403 or block Python's
    # default User-Agent at some point. Setting it once here costs nothing.
    url = OXS + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    code, payload = http(url, {"x-api-key": E["OXS_KEY_REQUESTS"].strip(),
                               "User-Agent": "curl/8.0",
                               "Accept": "application/json"})
    if code != 200:
        if not fatal:
            return []
        sys.exit("OXS %s -> HTTP %s" % (path, code))
    d = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(d, dict):
        # `finalList` is the real key and it is not what the spec says. The PDF
        # documents a paginated body as `{data: [], total, pages}`; what OXS
        # actually returns when `page` is sent is
        # `data: {finalList, totalCount, totalPages}`. The old code looked for
        # `results`, found nothing, and fell through to `[d]` — one bogus row
        # made of the envelope itself. It never fired only because nothing here
        # has ever sent `page`.
        d = d.get("finalList", d.get("results", d))
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


def departed_rows(gone):
    """What OXS says about the tickets that have left its open feed.

    One `GET /service-calls/:taskNumber?buildingId=` each. `buildingId` is
    required by the endpoint and is not on the ticket, so it comes from
    `buildings.id` — which IS the OXS `_id` (migration 016) — joined on the
    address string both tables are built from.

    BOUNDED ON PURPOSE. Only rows still `open` or `in_progress` on our side are
    looked up. A departed ticket therefore costs one request exactly once and
    then carries a closed status that takes it out of this set; without that
    filter every closed ticket we have ever imported would be re-fetched every
    fifteen minutes, for ever, to be told the same thing.

    `oxs_last_seen_at` is deliberately NOT in the returned rows. It means "the
    last run that saw this ticket in the open feed" and that is still true of
    the value already stored — this call did not see it there, it went and asked
    after it. Overwriting it would make a resolved ticket look freshly live.
    """
    if not gone:
        return [], []

    code, mine = sb("requests?select=reference,building,oxs_ref"
                    "&opened_via=eq.oxs&status=in.(open,in_progress)&limit=2000")
    if code != 200 or not isinstance(mine, list):
        print("  could not read our own open rows (HTTP %s); resolution skipped" % code)
        return [], []
    pending = [r for r in mine if r.get("oxs_ref") in gone]
    if not pending:
        return [], []

    # TWO KEYS PER BUILDING, because OXS writes an address two ways.
    #
    # `buildings.address` is `street number, city`, composed at import time, and
    # it is the exact string `requests.building` holds. But a service call on a
    # building with an entrance letter arrives with the letter in parentheses
    # mid-string -- `ארלוזורוב 13 (ב), רמת גן` -- which matches nothing, so the
    # by-taskNumber lookup has no buildingId and the ticket can never resolve.
    #
    # Composing their other form is exact rather than fuzzy: two of the 173
    # active buildings carry an entrance and neither sits at a duplicated
    # street+number (measured in docs/reference/oxs-extractable.md). Found by
    # `255-27001-26`, the one ticket of 292 the first live run left behind.
    code, blds = sb("buildings?select=id,address,street,number,entrance,city&limit=500")
    by_addr = {}
    if code == 200 and isinstance(blds, list):
        for b in blds:
            by_addr.setdefault(b["address"], b["id"])
            if b.get("entrance"):
                by_addr.setdefault("%s %s (%s), %s"
                                   % (b["street"], b["number"],
                                      b["entrance"], b["city"]), b["id"])

    print("  asking OXS about %d departed ticket(s), about %.0fs at %.2fs apart"
          % (len(pending), len(pending) * PACE, PACE))

    rows, unmapped, missing_bld = [], [], 0
    for r in pending:
        bid = by_addr.get(r.get("building"))
        if not bid:
            missing_bld += 1
            continue
        time.sleep(PACE)
        got = oxs("/service-calls/%s" % urllib.parse.quote(str(r["reference"])),
                  fatal=False, buildingId=bid)
        call = (got[0] if got else {}) or {}
        raw = ((call.get("status") or {}).get("status") or "").strip()
        if not raw:
            continue
        if raw not in STATUS:
            unmapped.append(raw)
            continue
        rows.append({
            "reference": r["reference"],
            "status": STATUS[raw],
            # Their closing notes are worth as much as their progress notes, and
            # a ticket often gains its most useful one on the way out.
            "oxs_notes": [n for n in (call.get("treatmentLog") or []) if str(n).strip()],
            "oxs_last_update": call.get("lastUpdate"),
        })
    if missing_bld:
        print("  no building id for %d of them — left alone" % missing_bld)
    return rows, unmapped


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

    # WHAT OXS HAS STOPPED SERVING, AND WHAT BECAME OF IT.
    #
    # Their feed is only ever the open calls; ours is every call we have ever
    # seen. The difference is the tickets that left, and until 31 Aug this
    # script could only count them and say "status unconfirmed". It can now ask:
    # each one is fetched back by taskNumber and comes home with a real status.
    # See "STATUS, AND HOW THE QUESTION WAS SETTLED" in the docstring.
    gone = known - {r["oxs_ref"] for r in rows}

    print("  new: %d   already imported: %d" % (len(new), len(rows) - len(new)))
    print("  no longer in the OXS open feed: %d of %d we hold" % (len(gone), len(known)))

    closed, unmapped_status = departed_rows(gone)
    if closed:
        print("  OXS says they are: %s"
              % dict(Counter(r["status"] for r in closed)))
    if unmapped_status:
        # Loud, and fatal. The whole point of this change is that we now trust
        # their status enough to write it; a value the table does not know is
        # the one case where trusting it would be wrong.
        sys.exit("UNMAPPED OXS STATUS -> refusing to write: %s"
                 % sorted(set(unmapped_status)))
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

    # The departed ones: PATCH each, never an upsert.
    #
    # An upsert here fails, and the failure is worth recording because the
    # reasoning that produced it looked sound. These rows all exist, so
    # `on_conflict=reference` with merge-duplicates "obviously" resolves to an
    # UPDATE — but Postgres evaluates CHECK constraints against the tuple the
    # INSERT proposes, before ON CONFLICT diverts it. The payload carries four
    # columns, so that tuple has `type`, `description` and `building` NULL with
    # status `resolved`, and `requests_complete_unless_review` (migration 003)
    # rejects the batch:
    #
    #     new row for relation "requests" violates check constraint
    #     "requests_complete_unless_review"
    #
    # Sending the whole row instead would satisfy it and would also be wrong:
    # an upsert that can INSERT is an upsert that can mint a half-built ticket
    # for a reference we mis-typed. UPDATE cannot create anything, which is the
    # correct guarantee for "this ticket already exists and has been closed".
    # One request each; the reference carries a plain unique constraint.
    if closed:
        for r in closed:
            ref = urllib.parse.quote(str(r["reference"]), safe="")
            body = {k: v for k, v in r.items() if k != "reference"}
            code, res = sb("requests?reference=eq.%s" % ref, "PATCH", body,
                           "return=minimal")
            if code >= 300:
                # Reference only, never the body: this runs every fifteen
                # minutes into a log anybody can read.
                msg = res.get("message", res) if isinstance(res, dict) else res
                sys.exit("Supabase %s resolving %s: %s"
                         % (code, r["reference"], str(msg)[:200]))
        print("resolved %d departed ticket(s) from OXS" % len(closed))

    code, after = sb("requests?select=reference&opened_via=eq.oxs&limit=2000")
    print("imported tickets now in the database: %d" % len(after))


if __name__ == "__main__":
    main()
