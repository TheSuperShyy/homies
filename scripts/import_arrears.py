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

ONE ROW PER APARTMENT PER MONTH
An owner with several flats gets one charge per flat per month. Until 11 Aug
`charges` was unique on (resident_id, period) and this script did
`do update set amount = excluded.amount`, so the second apartment overwrote the
first rather than joining it: two owners, two invisible apartments, ₪6,665.40
absent. Migration 012 puts the apartment on the charge; this writes it.

WHAT THIS DELIBERATELY DOES NOT TOUCH
`status`. A charge marked `paid` by `oxs_debt_sync.py` stays paid — the arrears
file is a snapshot from one sweep and is not evidence that a settled debt is
open again. The old `do update set ... status = 'unpaid'` would have resurrected
nine settled charges on the next run.
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
YEAR = 2026


def env():
    d = {}
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


# THE CORRECTION LIVES IN oxs_arrears.py SINCE 25 AUG, and this file calls it.
# It was written here on 11 Aug and the nightly importer never applied it,
# which is how the raw ₪922,901 reached a client-facing page. One copy.
from oxs_arrears import correct  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    src = os.path.join(ROOT, "docs", "reference", f"arrears-{YEAR}.json")
    behind = json.load(open(src, encoding="utf-8"))["behind"]

    rows, onboarded, lagging, dropped_lag, dropped_whole = correct(behind)

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

    # Printed every run, because this is the case the old schema silently ate.
    # If it ever reads "0 owners", that is worth distrusting before believing.
    multi = defaultdict(list)
    for r in rows:
        if r["phone"]:
            multi[r["phone"]].append(r)
    multi = {p: rs for p, rs in multi.items() if len(rs) > 1}
    print(f"\nOWNERS WITH MORE THAN ONE APARTMENT IN ARREARS: {len(multi)}")
    for p, rs in sorted(multi.items(), key=lambda kv: -sum(x["amount"] for x in kv[1])):
        print(f"  {rs[0]['name'][:24]:<24} {len(rs)} apartments  "
              f"₪{sum(x['amount'] for x in rs):>8,.0f}  "
              f"apt {', '.join(str(x['unit']) for x in rs)}")

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
                # `unit` is set when the resident is first seen and not
                # overwritten afterwards. For an owner of several flats every
                # apartment is an equally true answer, so overwriting made
                # residents.unit depend on the order rows happen to arrive in.
                # The authoritative apartment for a debt is charges.unit.
                conn.execute("""
                    insert into residents (full_name, phone, building, unit, source,
                                           handed_over, do_not_call)
                    values (%s, %s, %s, %s, 'oxs', false, false)
                    on conflict (phone) do update set
                      building = excluded.building
                """, (r["name"] or "דייר", r["phone"], r["building"], r["unit"]))
                residents += 1
                for m in r["months"]:
                    # source='oxs': these are real people's real debts. The
                    # column defaults to 'seed', and 007 makes 'seed' the thing
                    # every destructive query filters on — so leaving the
                    # default here put the whole arrears list one purge away
                    # from deletion. Status is left alone on conflict; see the
                    # module docstring.
                    conn.execute("""
                        insert into charges (resident_id, period, unit, amount,
                                             status, source)
                        select id, %s, %s, %s, 'unpaid', 'oxs'
                          from residents where phone = %s
                        on conflict (resident_id, period, unit) do update set
                          amount = excluded.amount, source = 'oxs'
                    """, (date(YEAR, int(m), 1), str(r["unit"]), r["monthly"], r["phone"]))
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
