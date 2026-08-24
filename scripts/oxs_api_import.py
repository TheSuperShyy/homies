#!/usr/bin/env python
"""Import real residents and debts from the OXS External API v1 into Supabase.

    python scripts/oxs_api_import.py            # dry run: fetch + report, write nothing
    python scripts/oxs_api_import.py --apply    # purge fake rows, import real ones

Replaces the CSV-export path (`oxs_import.py`, `import_oxs_csv.py`) — the
endpoint reference arrived 10 Aug (`OXS_External_API_v1.pdf`, repo root) and
all three keys are live. Read-only against OXS, always: GETs only.

What it does, in order:
  1. GET /buildings (general key), keep the active ones.
  2. GET /buildings/:id/tenants for each — active tenants with a phone become
     `residents` rows. Name arrives as "שם משפחה - דירה 3"; the suffix is
     stripped. Phones normalise to E.164 (+972...). No phone, no row — the
     phone is the lookup key the whole system identifies callers by.
  3. GET /debts (finance key) — each open debt becomes a `charges` row against
     the resident with the same phone (or a new resident from the owner record
     if the tenants list somehow missed them). period = first of the current
     month; amount = totalDebt (the overdue sum, excluding the current month,
     which is not yet late).
  4. With --apply: delete the fake rows first — source='seed' (the ten demo
     residents) and the synthetic-phone OXS rows (+9725000000xx) — then upsert
     on phone.

gender stays NULL (OXS does not carry it; the agents infer from name/speech).
handed_over stays false — nobody imported here is callable until a person
flips it, same policy as the CSV importer. do_not_call stays false.

Rate limits are per key, 60/min — tenant fetches are spaced ~1.05s apart, so
~170 active buildings take ~3-4 minutes.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://api.oxs.co.il/api/external/v1"

# Set by --quiet. Suppresses every line that carries a name, a phone or an
# amount. See the flag's note in main().
QUIET = False


def env():
    d = {}
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


E = env()


def get(path, key):
    req = urllib.request.Request(BASE + path, headers={
        "x-api-key": key, "User-Agent": "homies-oxs-import/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.loads(r.read().decode("utf-8"))
    if body.get("status") != 1:
        raise RuntimeError(f"{path}: {body.get('error')}")
    return body["data"]


def e164(raw):
    """'050-123 4567' -> '+972501234567'; None when nothing usable."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if digits.startswith("972"):
        digits = digits[3:]
    digits = digits.lstrip("0")
    if len(digits) < 8:          # too short to be an Israeli number
        return None
    return "+972" + digits


def clean_name(name):
    """'יעקב דיין - דירה 1' -> 'יעקב דיין'."""
    return re.sub(r"\s*-\s*דירה\s*\S+\s*$", "", name or "").strip()


def fetch_all():
    kg, kf = E["OXS_KEY_GENERAL"], E["OXS_KEY_DEBTS"]

    buildings = [b for b in get("/buildings", kg) if not b.get("disable")]
    print(f"buildings: {len(buildings)} active")

    residents = {}          # phone -> row
    skipped_nophone = 0
    dupes = 0
    for i, b in enumerate(buildings, 1):
        addr = f"{b.get('street','').strip()} {b.get('number','').strip()}, {b.get('city','').strip()}"
        data = get(f"/buildings/{b['_id']}/tenants", kg)
        rows = data.get("results", data) if isinstance(data, dict) else data
        for t in rows:
            if not t.get("isActive"):
                continue
            phone = e164(t.get("phone"))
            if not phone:
                skipped_nophone += 1
                continue
            if phone in residents:
                dupes += 1
                continue
            residents[phone] = {
                "full_name": clean_name(t.get("name")) or "דייר",
                "phone": phone,
                "building": addr,
                "unit": str(t.get("number") or ""),
                "oxs_ref": t.get("_id"),
            }
        if i % 20 == 0 or i == len(buildings):
            print(f"  ...{i}/{len(buildings)} buildings, {len(residents)} residents so far")
        time.sleep(1.05)

    d = get("/debts", kf)
    debts = d.get("results", d) if isinstance(d, dict) else d
    charges = []
    for rec in debts:
        total = rec.get("totalDebt") or 0
        if total <= 0:
            continue
        owner = (rec.get("owners") or [{}])[0]
        phone = e164((owner.get("contactDetails") or {}).get("mobilePhone"))
        if phone and phone not in residents:
            residents[phone] = {
                "full_name": clean_name(owner.get("firstName")) or "דייר",
                "phone": phone,
                "building": rec.get("address") or "",
                "unit": str((rec.get("apartment") or {}).get("number") or ""),
                "oxs_ref": owner.get("_id"),
            }
        charges.append({
            "phone": phone,
            "amount": total,
            "oxs_ref": rec.get("_id"),
            "address": rec.get("address"),
            "owner": clean_name(owner.get("firstName")),
            # Since 012 the apartment is part of the charge's identity, so an
            # owner of three flats owes three rows rather than overwriting
            # themselves twice. Empty string, never None: the unique constraint
            # treats NULLs as distinct and would let the duplicate back in.
            "unit": str((rec.get("apartment") or {}).get("number") or ""),
        })

    print(f"\nresidents with a phone: {len(residents)}   "
          f"(skipped, no phone: {skipped_nophone}; duplicate phones: {dupes})")
    print(f"open debts: {len(charges)}")
    if not QUIET:
        for c in charges:
            print(f"  {c['owner']:<25} {c['address']:<28} {c['amount']:>9.2f}  {c['phone']}")
    return list(residents.values()), charges


def apply(residents, charges):
    import psycopg
    from datetime import date

    dsn = E.get("SUPABASE_DB_URL", "").strip()
    if not dsn:
        sys.exit("SUPABASE_DB_URL is empty in .env.")
    period = date.today().replace(day=1)

    with psycopg.connect(dsn, connect_timeout=15) as conn:
        # The debts imported from the collection report do not come back from
        # /debts — the finance module returns one row for the whole company.
        # Those are real money owed by real people, so they are carried across
        # the purge and re-attached by name to the resident's real phone.
        carried = conn.execute("""
            select r.full_name, c.period, c.amount, c.status, c.unit, c.source
            from charges c join residents r on r.id = c.resident_id
            where r.phone like '+9725000000%'
        """).fetchall()
        print(f"\ncarrying {len(carried)} report debts across the purge")

        with conn.transaction():
            purged = conn.execute("""
                delete from residents
                where source = 'seed' or phone like '+9725000000%'
            """).rowcount

            # ONE STATEMENT FOR ALL SEVEN THOUSAND, NOT SEVEN THOUSAND
            # STATEMENTS.
            #
            # The loop this replaces was measured on 23 Aug: 4m22s to fetch the
            # residents from OXS, then 14m24s to write them, because every row
            # was its own round trip to a database in another region. That is
            # what pushed the job past its 45-minute ceiling and got it killed
            # in the step after this one. Identical SQL and identical conflict
            # handling, arrays instead of a loop, seconds instead of minutes.
            conn.execute("""
                insert into residents
                  (full_name, phone, building, unit, oxs_ref, source,
                   handed_over, do_not_call)
                select v.full_name, v.phone, v.building, v.unit, v.oxs_ref,
                       'oxs', false, false
                  from unnest(%s::text[], %s::text[], %s::text[], %s::text[],
                              %s::text[])
                       as v(full_name, phone, building, unit, oxs_ref)
                on conflict (phone) do update set
                  full_name = excluded.full_name,
                  building  = excluded.building,
                  unit      = excluded.unit,
                  oxs_ref   = excluded.oxs_ref,
                  source    = 'oxs'
            """, ([r["full_name"] for r in residents],
                  [r["phone"] for r in residents],
                  [r["building"] for r in residents],
                  [r["unit"] for r in residents],
                  [r["oxs_ref"] for r in residents]))

            n_charges = 0
            for c in charges:
                if not c["phone"]:
                    print(f"  ! debt without phone, skipped: {c['owner']} {c['address']}")
                    continue
                # (resident_id, period, unit) since 012 dropped the two-column
                # constraint; `source` because it defaults to 'seed', which is
                # what 007's purge queries delete. This path is not exercised by
                # the scheduled run — the workflow passes --skip-charges — but a
                # statement that can only raise 42P10 is not worth leaving in.
                conn.execute("""
                    insert into charges
                      (resident_id, period, amount, status, oxs_ref, source, unit)
                    select id, %s, %s, 'unpaid', %s, 'oxs', %s
                      from residents where phone = %s
                    on conflict (resident_id, period, unit) do update set
                      amount = excluded.amount, oxs_ref = excluded.oxs_ref,
                      source = 'oxs'
                """, (period, c["amount"], c["oxs_ref"], c["unit"], c["phone"]))
                n_charges += 1

            n_carried, lost = 0, []
            for name, per, amount, status, unit, src in carried:
                n = conn.execute("""
                    insert into charges
                      (resident_id, period, amount, status, unit, source)
                    select id, %s, %s, %s, %s, %s
                      from residents where full_name = %s
                    on conflict (resident_id, period, unit) do nothing
                """, (per, amount, status, unit, src, name)).rowcount
                if n:
                    n_carried += 1
                else:
                    lost.append((name, amount))

        n_res = conn.execute("select count(*) from residents").fetchone()[0]
        n_chg = conn.execute("select count(*) from charges").fetchone()[0]

    print(f"\npurged {purged} fake residents (charges cascaded)")
    print(f"re-attached {n_carried}/{len(carried)} report debts to real phones")
    for name, amount in lost:
        print(f"  ! could not re-attach: {name} {amount}")
    print(f"now in Supabase: {n_res} residents, {n_chg} charges ({n_charges} from OXS API)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    # --quiet EXISTS FOR CI AND IS NOT COSMETIC.
    # The per-debt line below prints an owner's name, address, amount and phone
    # number. GitHub Actions logs on a PUBLIC repository are readable by anyone,
    # so an unfiltered scheduled run publishes a debtor list to the internet —
    # the precise thing .gitignore and the repo rules exist to prevent. The
    # scheduled workflow always passes this; a human at a terminal never needs
    # to.
    ap.add_argument("--quiet", action="store_true",
                    help="counts only, no per-resident lines. Required in CI.")
    # /debts is a collections ledger, not an arrears list: it returns a single
    # company-wide record, a 2022 balance against a departed owner. Importing it
    # twice a day re-creates that phantom charge for ever. Real arrears come
    # from oxs_arrears.py, which runs straight after this one.
    ap.add_argument("--skip-charges", action="store_true",
                    help="residents only; leave `charges` to oxs_arrears.py.")
    a = ap.parse_args()

    global QUIET
    QUIET = a.quiet
    residents, charges = fetch_all()
    if a.skip_charges:
        charges = []
    if not a.apply:
        print("\nDry run — nothing written. Re-run with --apply.")
        return
    if len(residents) < 50:
        sys.exit(f"Only {len(residents)} residents fetched — refusing to purge "
                 "and import a suspiciously small set. Investigate first.")
    apply(residents, charges)


if __name__ == "__main__":
    main()
