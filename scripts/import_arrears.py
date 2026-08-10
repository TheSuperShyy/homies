#!/usr/bin/env python
"""Import the 2026 arrears list into Supabase, one charge per unpaid month.

    python scripts/import_arrears.py            # dry run
    python scripts/import_arrears.py --apply

Reads `docs/reference/arrears-2026.json` (written by oxs_arrears.py). No
network calls — the OXS sweep already happened.

THE CORRECTION THIS APPLIES
The raw sweep flags every ended month of 2026 with no payment against it.
That over-counts, because a building Homies took on in June has no January
payments for an innocent reason. Where four or more flagged apartments in a
building are missing the *same leading run* of months — 01, or 01-02, or
01-05 — that run is the period before Homies managed the building, and it is
dropped from every apartment in that building. What remains is arrears.

A building where most flagged apartments miss the same *recent* month
(not a leading run) is a collection-recording lag, not debt. Those are
excluded too, and reported.

One row per unpaid month, not one lump: `charges.period` is the month itself,
so the dashboard's "months owed" column is true and the agent can name the
month it is calling about.
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YEAR = 2026


def env():
    d = {}
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def is_leading_run(months):
    """('01','02','03') -> True. ('07',) -> False. ('01','03') -> False."""
    want = [f"{i:02d}" for i in range(1, len(months) + 1)]
    return list(months) == want


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    src = os.path.join(ROOT, "docs", "reference", f"arrears-{YEAR}.json")
    behind = json.load(open(src, encoding="utf-8"))["behind"]

    by_b = defaultdict(list)
    for r in behind:
        by_b[r["building"]].append(r)

    # A leading run shared by most of a building is onboarding, and the bar for
    # believing that is lower than for other patterns: a whole building going
    # unpaid from January onwards and then resuming together does not happen,
    # whereas Homies taking the building on in May happens constantly.
    onboarded, lagging = {}, set()
    for b, rs in by_b.items():
        common, n = Counter(tuple(r["months"]) for r in rs).most_common(1)[0]
        if len(rs) < 4:
            continue
        share = n / len(rs)
        if is_leading_run(common) and share >= 0.6:
            onboarded[b] = set(common)          # months before Homies managed it
        elif share >= 0.8:
            lagging.add(b)                       # recording lag, not debt

    rows, dropped_lag, dropped_whole = [], 0, 0
    for r in behind:
        if r["building"] in lagging:
            dropped_lag += 1
            continue
        skip = onboarded.get(r["building"], set())
        months = [m for m in r["months"] if m not in skip]
        if not months:
            dropped_whole += 1
            continue
        rows.append({**r, "months": months,
                     "amount": r["monthly"] * len(months)})

    charges = sum(len(r["months"]) for r in rows)
    total = sum(r["amount"] for r in rows)
    nophone = [r for r in rows if not r["phone"]]

    print(f"source: {len(behind)} apartments flagged by the sweep")
    print(f"  {len(onboarded)} buildings started mid-year — their leading months dropped")
    print(f"  {len(lagging)} buildings show a recording lag — excluded entirely ({dropped_lag} apartments)")
    print(f"  {dropped_whole} apartments had nothing left after the correction\n")
    print(f"IMPORTING: {len(rows)} apartments, {charges} monthly charges, ₪{total:,.0f}")
    print(f"  (of these, {len(nophone)} have no phone and cannot be called)\n")

    for r in sorted(rows, key=lambda x: -x["amount"])[:15]:
        print(f"  {r['name'][:24]:<24} ₪{r['amount']:>7,.0f}  "
              f"{','.join(r['months'])}  {r['building'][:26]:<26} apt {r['unit']}")
    if len(rows) > 15:
        print(f"  ... and {len(rows)-15} more")

    if not a.apply:
        print("\nDry run — Supabase untouched. Re-run with --apply.")
        return

    import psycopg
    dsn = env().get("SUPABASE_DB_URL", "").strip()
    with psycopg.connect(dsn, connect_timeout=15) as conn:
        with conn.transaction():
            residents = written = skipped = 0
            for r in rows:
                if not r["phone"]:
                    skipped += 1
                    continue
                conn.execute("""
                    insert into residents (full_name, phone, building, unit, source,
                                           handed_over, do_not_call)
                    values (%s, %s, %s, %s, 'oxs', false, false)
                    on conflict (phone) do update set
                      building = excluded.building, unit = excluded.unit
                """, (r["name"] or "דייר", r["phone"], r["building"], r["unit"]))
                residents += 1
                for m in r["months"]:
                    conn.execute("""
                        insert into charges (resident_id, period, amount, status)
                        select id, %s, %s, 'unpaid' from residents where phone = %s
                        on conflict (resident_id, period) do update set
                          amount = excluded.amount, status = 'unpaid'
                    """, (date(YEAR, int(m), 1), r["monthly"], r["phone"]))
                    written += 1

        n = conn.execute("select count(*) from charges where status='unpaid'").fetchone()[0]
        owed = conn.execute("select coalesce(sum(amount),0) from charges where status='unpaid'").fetchone()[0]
        people = conn.execute("""
            select count(distinct resident_id) from charges where status='unpaid'
        """).fetchone()[0]

    print(f"\n{residents} residents upserted, {written} monthly charges written "
          f"({skipped} skipped for having no phone)")
    print(f"OPEN BALANCES NOW: {people} residents, {n} charges, ₪{float(owed):,.0f}")


if __name__ == "__main__":
    main()
