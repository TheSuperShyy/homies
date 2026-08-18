#!/usr/bin/env python
"""Import the canonical building and apartment list from OXS into Supabase.

    python scripts/oxs_buildings_sync.py            # dry run: fetch + report, write nothing
    python scripts/oxs_buildings_sync.py --apply    # upsert buildings and apartments
    python scripts/oxs_buildings_sync.py --json PATH  # also dump the raw fetch

Read-only against OXS, always: GETs only. Two endpoints, both on the general
key — `/buildings` (one call) and `/buildings/:id/apartments` (one call per
active building, ~173 of them, spaced for the 60/min limit, so about three
minutes).

WHY THIS EXISTS
Until now `residents.building` was the only place a building name lived: a
string composed at import time from the OXS record and then never checked
against anything. That is enough to file a ticket and not enough to *verify*
one. A resident who says a street we do not manage, or an apartment number
that does not exist in their building, was recorded verbatim and the ticket
went to a person to puzzle over.

Apartments are the half that was never fetched at all. They are also the only
way to know an apartment exists when nobody lives in it or nobody has a phone
on file — `residents` cannot answer that, because a flat with no contact
details has no row there.

WHAT THE DATA LOOKS LIKE, AND WHY MATCHING IS EASIER THAN EXPECTED
Checked 13 Aug against all 173 active buildings:

  - Street + number is unique across the whole portfolio. Zero duplicate
    addresses, and zero cases of one street+number appearing in two cities.
    So a caller who says "הרצל 14" has identified the building, and the agent
    never has to ask which city. Three street names do appear in more than one
    city — גולומב, החשמונאים, סוקולוב — but never at the same house number.
  - Apartment numbers are plain sequential integers, "1" upward.
  - Two buildings carry an entrance letter. Neither address is otherwise
    duplicated, so the letter is stored and is not needed to disambiguate.

The uniqueness is a property of today's data, not a guarantee. `--apply`
re-checks it on every run and says so loudly if it ever stops being true,
because the matcher in the Edge Function leans on it.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OXS = "https://api.oxs.co.il/api/external/v1"
PACE = 1.05          # seconds between calls; the limit is 60/min per key


def env():
    d = {}
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


E = env()


def oxs(path, key):
    req = urllib.request.Request(OXS + path, headers={
        "x-api-key": key, "User-Agent": "homies-buildings-sync/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.loads(r.read().decode("utf-8"))
    if body.get("status") != 1:
        raise RuntimeError("%s: %s" % (path, body.get("error")))
    return body["data"]


def rows_of(data):
    """OXS returns either a bare list or {results: [...]}, depending on endpoint."""
    return data.get("results", data) if isinstance(data, dict) else data


def sb(method, path, payload=None, prefer=None):
    url = E["SUPABASE_URL"] + "/rest/v1/" + path
    key = E.get("SUPABASE_SERVICE_ROLE_KEY") or E["SUPABASE_ANON_KEY"]
    headers = {
        "apikey": key, "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "User-Agent": "homies-buildings-sync/1.0",
    }
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(
        url, method=method,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None,
        headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8")
            return json.loads(body) if body.strip() else []
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s on %s %s\n%s" % (e.code, method, path, e.read().decode("utf-8")))


def s(rec, field):
    return str(rec.get(field, "") or "").strip()


# Normalised for matching, not for display. The geresh and gershayim are the
# point: ז'בוטינסקי is typed with U+05F3, with an ASCII apostrophe, and with
# nothing at all, by the same person on different days. Latin quotes appear in
# OXS's own data. None of them are a different street.
def norm(street):
    t = re.sub(r"[׳״'\"`׳״]", "", street or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def fetch(verbose=True):
    kg = E["OXS_KEY_GENERAL"]
    every = oxs("/buildings", kg)
    active = [b for b in every if not b.get("disable")]
    if verbose:
        print("buildings : %d total, %d active, %d disabled"
              % (len(every), len(active), len(every) - len(active)))
        print("apartments: fetching %d buildings at %.2fs apart (~%d min)\n"
              % (len(active), PACE, round(len(active) * PACE / 60) or 1))

    buildings, apartments = [], []
    for i, b in enumerate(active, 1):
        street, number, city = s(b, "street"), s(b, "number"), s(b, "city")
        buildings.append({
            "id": b["_id"],
            "street": street,
            "street_norm": norm(street),
            "number": number,
            "city": city,
            "entrance": s(b, "enterance") or None,
            # Exactly the string `residents.building` already holds, composed
            # the same way by oxs_api_import.py. Kept as a column rather than
            # recomposed at read time so the two can be joined and, more to the
            # point, so a drift between them is visible in one query.
            "address": "%s %s, %s" % (street, number, city),
            "active": True,
        })
        flats = rows_of(oxs("/buildings/%s/apartments" % b["_id"], kg))
        for a in flats:
            apartments.append({
                "id": a["_id"],
                "building_id": b["_id"],
                "number": s(a, "number"),
                "order_index": a.get("orderIndex"),
            })
        if verbose and (i % 25 == 0 or i == len(active)):
            print("  %3d/%d  %-34s %2d flats  (%d so far)"
                  % (i, len(active), buildings[-1]["address"], len(flats), len(apartments)))
        if i < len(active):
            time.sleep(PACE)

    # The disabled ones are carried too, without their apartments. A building
    # Homies stopped managing still appears on old tickets and in old debt, and
    # a row that says `active = false` explains that; a missing row reads as an
    # import bug. Not worth 20 more API calls to list flats nobody will report.
    for b in every:
        if b.get("disable"):
            street, number, city = s(b, "street"), s(b, "number"), s(b, "city")
            buildings.append({
                "id": b["_id"], "street": street, "street_norm": norm(street),
                "number": number, "city": city,
                "entrance": s(b, "enterance") or None,
                "address": "%s %s, %s" % (street, number, city),
                "active": False,
            })
    return buildings, apartments


def check(buildings, apartments):
    """The assumptions the address matcher is built on. Re-checked every run.

    If any of these stops holding, the matcher in `debt-tools` starts returning
    one confident answer where there are two — which is worse than returning
    nothing, because the ticket goes to the wrong building and reads correct.
    """
    live = [b for b in buildings if b["active"]]
    problems = []

    seen = {}
    for b in live:
        seen.setdefault(b["address"], []).append(b)
    dup_addr = {a: v for a, v in seen.items() if len(v) > 1}
    if dup_addr:
        problems.append("%d duplicate addresses: %s"
                        % (len(dup_addr), ", ".join(list(dup_addr)[:3])))

    bynum = {}
    for b in live:
        bynum.setdefault((b["street_norm"], b["number"]), []).append(b)
    dup_sn = {k: v for k, v in bynum.items() if len(v) > 1}
    if dup_sn:
        problems.append(
            "%d street+number pairs are NOT unique — the matcher assumes they "
            "are: %s" % (len(dup_sn), ", ".join("%s %s" % k for k in list(dup_sn)[:3])))

    per = {}
    for a in apartments:
        per.setdefault(a["building_id"], []).append(a["number"])
    empty = [b["address"] for b in live if not per.get(b["id"])]
    if empty:
        problems.append("%d active buildings returned no apartments: %s"
                        % (len(empty), ", ".join(empty[:3])))

    # NOT a problem, and reported anyway. An apartment "number" is a label as
    # often as OXS feels like it — חנות, מסחר 2, מחסן, חניה 43, דירת ועד — and
    # one building has two units both called חנות. Migration 016 assumed
    # otherwise and its unique constraint rejected that building on the first
    # real import; 017 drops it. Printed every run so the next person meets
    # this in the output rather than in a 409.
    labels = [a for a in apartments if not str(a["number"]).strip().isdigit()]
    seen = {}
    for a in apartments:
        seen.setdefault((a["building_id"], str(a["number"]).strip()), 0)
        seen[(a["building_id"], str(a["number"]).strip())] += 1
    shared = [k for k, n in seen.items() if n > 1]

    print("\nchecks")
    print("  active buildings      : %d" % len(live))
    print("  disabled, carried     : %d" % (len(buildings) - len(live)))
    print("  apartments            : %d" % len(apartments))
    print("  distinct streets      : %d" % len({b["street_norm"] for b in live}))
    print("  cities                : %d" % len({b["city"] for b in live}))
    print("  street+number unique  : %s" % ("yes" if not dup_sn else "NO"))
    if per:
        sizes = sorted(len(v) for v in per.values())
        print("  flats per building    : min %d, median %d, max %d"
              % (sizes[0], sizes[len(sizes) // 2], sizes[-1]))
    print("  flats named, not numbered: %d  %s"
          % (len(labels),
             ", ".join(sorted({str(a["number"]).strip() for a in labels})[:6])))
    print("  same number twice in one building: %d" % len(shared))
    for p in problems:
        print("  !! " + p)
    return problems


def apply(buildings, apartments):
    print("\nwriting")
    # Buildings first — apartments carry a foreign key to them.
    sb("POST", "buildings?on_conflict=id", buildings,
       prefer="resolution=merge-duplicates,return=minimal")
    print("  buildings  upserted %d" % len(buildings))
    # Chunked because a 4,000-row body times out the gateway well before it
    # troubles Postgres.
    n = 0
    for i in range(0, len(apartments), 500):
        chunk = apartments[i:i + 500]
        sb("POST", "apartments?on_conflict=id", chunk,
           prefer="resolution=merge-duplicates,return=minimal")
        n += len(chunk)
        print("  apartments upserted %d/%d" % (n, len(apartments)))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="write to Supabase")
    p.add_argument("--json", metavar="PATH", help="dump the raw fetch here too")
    args = p.parse_args()

    buildings, apartments = fetch()
    problems = check(buildings, apartments)

    if args.json:
        json.dump({"buildings": buildings, "apartments": apartments},
                  open(args.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("\nwrote %s" % args.json)

    if not args.apply:
        print("\nDry run. Re-run with --apply to write.")
        return

    if problems:
        # Refusing rather than warning. Every one of these breaks the matcher in
        # a way that produces a confident wrong answer, and a confident wrong
        # building on a ticket is the failure this whole feature exists to stop.
        sys.exit("\nRefusing to write: the checks above failed.")
    apply(buildings, apartments)
    print("\nDone.")


if __name__ == "__main__":
    main()
