#!/usr/bin/env python
"""Delete the synthetic-phone OXS residents before a re-import with real phones.

    python scripts/oxs_purge_synthetic.py
    python scripts/oxs_purge_synthetic.py --apply

The 12 real residents imported from the OXS collection report carry synthetic
phones (+972500000001..12) because the export's phone column was one
placeholder repeated. Residents upsert on `phone`, so a re-import with real
numbers would not update these rows — it would duplicate every person. These
rows must go first.

Matching is deliberately narrow: source = 'oxs' AND phone LIKE '+9725000000%'.
The ten fictional seed residents have source = 'seed' and are untouched; a
future import with real phones can never match this pattern.

Deleting a resident cascades to charges and payment rows (FKs in
004_debt_schema.sql are `on delete cascade`); interactions, requests and
messages keep their rows with resident_id set null.
"""
import argparse
import os
import sys

import psycopg

# Resident names are Hebrew; the Windows console default (cp1252) cannot
# print them.
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PATTERN = "+9725000000%"


def env():
    d = {}
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    dsn = env().get("SUPABASE_DB_URL", "").strip()
    if not dsn:
        sys.exit("SUPABASE_DB_URL is empty in .env.")

    with psycopg.connect(dsn, connect_timeout=15) as conn:
        rows = conn.execute("""
            select r.id, r.full_name, r.phone,
                   count(c.id)                       as charges,
                   coalesce(sum(c.amount), 0)        as total
            from residents r
            left join charges c on c.resident_id = r.id
            where r.source = 'oxs' and r.phone like %s
            group by r.id, r.full_name, r.phone
            order by r.phone
        """, (PATTERN,)).fetchall()

        if not rows:
            print("Nothing matches source='oxs' AND phone LIKE %r. "
                  "Already clean." % PATTERN)
            return

        print("Synthetic OXS residents (source='oxs', phone LIKE %r):\n"
              % PATTERN)
        for _, name, phone, n, total in rows:
            print("  %-15s %-30s %2d charges  %10.2f" % (phone, name, n, total))
        print("\n  residents to delete  %d" % len(rows))
        print("  charges going with them (cascade)  %d" % sum(r[3] for r in rows))

        if not a.apply:
            print("\nDry run. Re-run with --apply.")
            return

        with conn.transaction():
            deleted = conn.execute("""
                delete from residents
                where source = 'oxs' and phone like %s
            """, (PATTERN,)).rowcount

        n_res = conn.execute(
            "select count(*) from residents where source = 'oxs'").fetchone()[0]
        n_chg = conn.execute(
            "select count(*) from charges where source = 'oxs'").fetchone()[0]

    print("\n  deleted %d residents" % deleted)
    print("  remaining residents with source='oxs'  %d" % n_res)
    print("  remaining charges   with source='oxs'  %d" % n_chg)


if __name__ == "__main__":
    main()
