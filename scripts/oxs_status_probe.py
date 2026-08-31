#!/usr/bin/env python
"""Ask OXS what a service call's status actually is. READ ONLY.

    python scripts/oxs_status_probe.py

WHY THIS EXISTS

`oxs_requests_sync.py` has said since 12 Aug that the API cannot tell two
readings apart -- "the endpoint only serves open calls" versus "nothing is ever
closed there" -- and 36 of our 70 imported tickets sit flagged `gone from OXS`
on the dashboard because of it.

The API can tell them apart, and its own spec says so.
`OXS_External_API_v1.pdf` p.6, the parameter table for `GET /service-calls`:

    status   query   no   defaults to open

We have never sent it. `oxs_requests_sync.py` calls `oxs("/service-calls")`
bare, so every record reading `פתוחה` is the documented default filter doing
exactly what it says, not evidence about how Homies works.

This probe checks that claim against the live API before a single row is
rewritten on the strength of a PDF. It writes nothing -- to OXS, to Supabase, or
to disk -- and every request is a GET.

WHAT IT PRINTS, AND WHAT IT DOES NOT

Counts, status vocabulary, and the closure fields (`doneDate`, `closedBy`,
`lastUpdate`) of tickets we already hold. No description, no reporter name, no
phone: `docs/reference/oxs-extractable.md` records field names and not values,
and this follows it.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OXS = "https://api.oxs.co.il/api/external/v1"

# 60/min per key. A second apart is the pace oxs_buildings_sync.py already uses
# and it leaves headroom for the scheduled sync running alongside this.
PACE = 1.05

# The map in oxs_requests_sync.py was written from the spec, not from observed
# data -- only `open` has ever been seen. These are the values it claims to
# understand, plus the two catch-alls worth trying and one deliberate junk
# value. If junk is accepted silently the filter does nothing and every
# conclusion below is void, which is why it is in the list.
CANDIDATES = ["open", "close", "closed", "done", "inProgress", "in_progress",
              "cancelled", "canceled", "all", "zzzz-not-a-status"]


def env():
    return dict(
        l.strip().split("=", 1)
        for l in open(os.path.join(ROOT, ".env"), encoding="utf-8")
        if l.strip() and not l.startswith("#") and "=" in l
    )


E = env()


def http(url, headers):
    req = urllib.request.Request(url, method="GET", headers=headers)
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
    except Exception as e:  # noqa: BLE001 - a probe reports, it does not raise
        return 0, str(e)


def oxs_raw(path, **params):
    """The WHOLE envelope, unlike oxs_requests_sync.oxs() which returns `data`.

    That helper drops `total` and `pages` on the floor and never sends `page`,
    which is the second thing this probe is here to measure.
    """
    url = OXS + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return http(url, {"x-api-key": E["OXS_KEY_REQUESTS"].strip(),
                      "User-Agent": "curl/8.0",
                      "Accept": "application/json"})


def rows_of(payload):
    if not isinstance(payload, dict):
        return payload if isinstance(payload, list) else []
    d = payload.get("data", [])
    if isinstance(d, dict):
        # Sending `page` changes the shape: `data` stops being an array and
        # becomes {finalList, totalCount, totalPages}. Not what the PDF's
        # example shows (`{data: [], total, pages}`), and the reason the sync's
        # own helper -- which looks for `results` -- would have returned one
        # bogus row made of the envelope if it had ever paginated.
        d = d.get("finalList", d.get("results", [d]))
    return d if isinstance(d, list) else [d]


def statuses_in(rows):
    seen = {}
    for r in rows:
        s = r.get("status") or {}
        key = (str(s.get("status") or ""), str(s.get("label") or ""))
        seen[key] = seen.get(key, 0) + 1
    return seen


def sb(path):
    key = E["SUPABASE_SERVICE_ROLE_KEY"].strip()
    return http(E["SUPABASE_URL"].strip().rstrip("/") + "/rest/v1/" + path,
                {"apikey": key, "Authorization": "Bearer " + key,
                 "Accept": "application/json"})


def show(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main():
    # ---------------------------------------------------------------- 1 + 4
    show("1. The bare call, and what the envelope carries")
    code, payload = oxs_raw("/service-calls")
    if code != 200:
        sys.exit("bare /service-calls -> HTTP %s: %s" % (code, str(payload)[:300]))
    rows = rows_of(payload)
    envelope = {k: v for k, v in payload.items() if k != "data"} \
        if isinstance(payload, dict) else {}
    print("rows returned : %d" % len(rows))
    print("envelope keys : %s" % json.dumps(envelope, ensure_ascii=False))
    for (s, label), n in sorted(statuses_in(rows).items(), key=lambda kv: -kv[1]):
        print("   status=%-14s label=%-10s x%d" % (s or "-", label or "-", n))

    total = envelope.get("total")
    if isinstance(total, int) and total > len(rows):
        print("\n   ** TRUNCATED: total=%d, received=%d. oxs_requests_sync.py"
              % (total, len(rows)))
        print("      sends no `page` and discards `total`, so it has been")
        print("      importing the first page only.")
    elif total is not None:
        print("\n   total=%s matches what arrived -- not truncating today." % total)
    else:
        print("\n   No `total` in the envelope on this endpoint.")

    # -------------------------------------------------------------------- 2
    show("2. Does `status` do anything, and what is the vocabulary?")
    print("%-20s %-6s %-7s %s" % ("status=", "http", "rows", "distinct status.status"))
    print("-" * 70)
    results = {}
    for value in CANDIDATES:
        time.sleep(PACE)
        code, payload = oxs_raw("/service-calls", status=value)
        if code != 200:
            print("%-20s %-6s %s" % (value, code, str(payload)[:40]))
            results[value] = None
            continue
        rs = rows_of(payload)
        results[value] = len(rs)
        distinct = ", ".join(sorted({k[0] or "-" for k in statuses_in(rs)})) or "-"
        print("%-20s %-6s %-7d %s" % (value, code, len(rs), distinct))

    base = len(rows)
    junk = results.get("zzzz-not-a-status")
    print()
    if junk is not None and junk == base:
        print("** The junk value returned the same %d rows as the bare call." % base)
        print("   The filter is INOPERATIVE -- it is being ignored, not applied,")
        print("   and nothing below can be concluded from a count. STOP HERE.")
    elif junk is None:
        print("Junk value rejected, so the parameter is really being read.")

    # -------------------------------------------------------------------- 3
    show("3. Tickets that left the feed -- what does OXS say about them now?")
    code, stale = sb("requests?select=reference,building,status,oxs_last_seen_at"
                     "&opened_via=eq.oxs"
                     "&order=oxs_last_seen_at.asc&limit=8")
    if code != 200 or not isinstance(stale, list):
        print("Supabase read failed (%s); skipping." % code)
        return
    code, blds = sb("buildings?select=id,address&limit=500")
    by_addr = {b["address"]: b["id"] for b in blds} if isinstance(blds, list) else {}

    print("%-16s %-10s %-12s %-10s %s"
          % ("taskNumber", "ours", "oxs status", "doneDate", "closedBy"))
    print("-" * 70)
    for r in stale:
        ref, addr = r.get("reference"), r.get("building")
        bid = by_addr.get(addr)
        if not bid:
            print("%-16s %-10s no building id for this address" % (ref, r.get("status")))
            continue
        time.sleep(PACE)
        code, payload = oxs_raw("/service-calls/%s" % urllib.parse.quote(str(ref)),
                                buildingId=bid)
        if code != 200:
            print("%-16s %-10s HTTP %s %s"
                  % (ref, r.get("status"), code, str(payload)[:30]))
            continue
        one = rows_of(payload)
        one = one[0] if one else {}
        st = (one.get("status") or {})
        closed_by = one.get("closedBy") or {}
        print("%-16s %-10s %-12s %-10s %s"
              % (ref, r.get("status"),
                 st.get("status") or st.get("label") or "-",
                 str(one.get("doneDate") or "-")[:10],
                 closed_by.get("firstName") or "-"))

    print("\nA row whose OXS status is not `open`, or that carries a doneDate or")
    print("a closedBy, is the proof: the feed serves open calls only, and")
    print("leaving it means closed. Client question 2 answers itself.")


if __name__ == "__main__":
    main()
