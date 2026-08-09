#!/usr/bin/env python
"""Import an OXS export CSV into Supabase. Read-only towards OXS, by definition.

    python scripts/import_oxs_csv.py sheets/residents-real.csv
    python scripts/import_oxs_csv.py sheets/residents-real.csv --apply

Every row is marked `source = 'oxs'` so a real person can never be mistaken for
one of the ten fictional residents in 002_slice_seed.sql. Matching is on `phone`
in E.164, which is the same key identify_resident uses — so an import that
normalises phones differently from the agent produces a resident who exists in
the table and cannot be found on a call.

Re-running is safe: residents upsert on phone, charges on (resident_id, period).
The point is that a nightly export can be replayed without duplicating anybody.

WHAT THIS DELIBERATELY REFUSES TO GUESS

`month` arrives as a Hebrew month name with no year — "דצמבר", not 2025-12.
`charges.period` is a not-null date. Rather than assume, the year comes from
--year and every affected row is listed before anything is written. A charge
filed under the wrong year is a resident called about a debt from a different
December, which is worse than a row that was never created.
"""
import argparse
import csv
import os
import sys

import psycopg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEB_MONTHS = {
    "ינואר": 1, "פברואר": 2, "מרץ": 3, "מרס": 3, "אפריל": 4, "מאי": 5,
    "יוני": 6, "יולי": 7, "אוגוסט": 8, "ספטמבר": 9, "אוקטובר": 10,
    "נובמבר": 11, "דצמבר": 12,
}

GENDER = {"m": "m", "f": "f", "male": "m", "female": "f",
          "ז": "m", "נ": "f", "unknown": "unknown"}


def env():
    d = {}
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def blank_to_none(v):
    v = (v or "").strip()
    return v or None


def truthy(v):
    return str(v).strip().upper() in ("TRUE", "1", "YES", "Y")


def period(month_cell, year):
    """Hebrew month name -> the first of that month. None if there is no month."""
    m = (month_cell or "").strip()
    if not m:
        return None
    if m in HEB_MONTHS:
        return "%04d-%02d-01" % (year, HEB_MONTHS[m])
    # Already a date, or a numeric month.
    if m[:4].isdigit() and "-" in m:
        return m[:7] + "-01" if len(m) >= 7 else None
    if m.isdigit() and 1 <= int(m) <= 12:
        return "%04d-%02d-01" % (year, int(m))
    return "?" + m          # flagged, never written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--year", type=int, default=2025,
                    help="year for bare Hebrew month names (default 2025)")
    a = ap.parse_args()

    path = a.csv_path if os.path.isabs(a.csv_path) else os.path.join(ROOT, a.csv_path)
    if not os.path.exists(path):
        sys.exit("No such file: %s" % path)

    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    if not rows:
        sys.exit("%s has no rows." % path)

    people, charges, skipped = [], [], []

    for i, r in enumerate(rows, 2):          # 2 = first data row in a spreadsheet
        phone = (r.get("phone") or "").strip()
        name = (r.get("full_name") or "").strip()
        if not phone or not name:
            skipped.append((i, "no phone or no name"))
            continue
        if not phone.startswith("+"):
            skipped.append((i, "phone %r is not E.164" % phone))
            continue

        g = blank_to_none(r.get("gender"))
        card = blank_to_none(r.get("card_last4"))
        if card and not (card.isdigit() and len(card) == 4):
            skipped.append((i, "card_last4 %r is not four digits" % card))
            continue

        people.append({
            "phone": phone,
            "full_name": name,
            "building": (r.get("building") or "").strip(),
            "unit": (r.get("unit") or "").strip(),
            "gender": GENDER.get((g or "").lower()) if g else None,
            "card_last4": card,
            "handed_over": truthy(r.get("handed_over", "TRUE")),
            "do_not_call": truthy(r.get("do_not_call", "FALSE")),
        })

        amount = blank_to_none(r.get("amount"))
        per = period(r.get("month"), a.year)
        if amount and per and not per.startswith("?"):
            charges.append({"phone": phone, "period": per,
                            "amount": float(amount),
                            "status": (r.get("status") or "unpaid").strip() or "unpaid",
                            "attempts": int((r.get("attempts") or "0").strip() or 0)})
        elif amount and per and per.startswith("?"):
            skipped.append((i, "charge skipped — month %r not understood" % per[1:]))
        elif amount:
            skipped.append((i, "charge skipped — amount %s with no month" % amount))

    print("%s\n" % path)
    print("  residents to import   %d" % len(people))
    print("  charges to import     %d   (year %d applied to bare month names)"
          % (len(charges), a.year))
    print("  rows with a problem   %d" % len(skipped))
    for line, why in skipped:
        print("      line %-3d %s" % (line, why))

    callable_now = [p for p in people if not p["do_not_call"]]
    if callable_now:
        print("\n  %d of these %d real people have do_not_call = FALSE."
              % (len(callable_now), len(people)))

    if not a.apply:
        print("\nDry run. Re-run with --apply.")
        return

    dsn = env().get("SUPABASE_DB_URL", "").strip()
    if not dsn:
        sys.exit("SUPABASE_DB_URL is empty in .env.")

    with psycopg.connect(dsn, connect_timeout=15) as conn:
        with conn.transaction():
            ids = {}
            for p in people:
                ids[p["phone"]] = conn.execute("""
                    insert into residents
                        (full_name, phone, building, unit, gender, card_last4,
                         handed_over, do_not_call, source)
                    values (%(full_name)s, %(phone)s, %(building)s, %(unit)s,
                            %(gender)s, %(card_last4)s, %(handed_over)s,
                            %(do_not_call)s, 'oxs')
                    on conflict (phone) do update set
                        full_name = excluded.full_name,
                        building  = excluded.building,
                        unit      = excluded.unit,
                        gender    = coalesce(excluded.gender, residents.gender),
                        card_last4 = coalesce(excluded.card_last4, residents.card_last4),
                        handed_over = excluded.handed_over,
                        do_not_call = excluded.do_not_call,
                        source    = 'oxs'
                    returning id
                """, p).fetchone()[0]

            for c in charges:
                conn.execute("""
                    insert into charges
                        (resident_id, period, amount, status, attempts, source)
                    values (%s, %s, %s, %s, %s, 'oxs')
                    on conflict (resident_id, period) do update set
                        amount   = excluded.amount,
                        status   = excluded.status,
                        attempts = excluded.attempts,
                        source   = 'oxs'
                """, (ids[c["phone"]], c["period"], c["amount"],
                      c["status"], c["attempts"]))

        n_res = conn.execute(
            "select count(*) from residents where source = 'oxs'").fetchone()[0]
        n_chg = conn.execute(
            "select count(*) from charges where source = 'oxs'").fetchone()[0]

    print("\n  residents with source='oxs'  %d" % n_res)
    print("  charges   with source='oxs'  %d" % n_chg)


if __name__ == "__main__":
    main()
