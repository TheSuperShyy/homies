#!/usr/bin/env python
"""Reconcile Supabase `charges` against what OXS says is owed, right now.

    python scripts/oxs_debt_sync.py            # dry run: report only
    python scripts/oxs_debt_sync.py --apply

`GET /debts` returns one row for the whole company, which is not the whole
truth — debts are also readable per building. This sweeps every active
building (`/buildings/:id/debts`), which is the complete current picture, and
makes Supabase match it:

  in OXS, not in Supabase   -> insert a charge (and the resident if missing)
  in Supabase, not in OXS   -> mark the charge `paid`
  in both                   -> update the amount to the OXS figure

The second rule is the important one. A charge nobody has cleared is a call
to somebody who paid months ago, which the debt prompt calls the worst call
this agent makes. OXS is the record; if OXS does not list it, it is settled.

Read-only against OXS. GETs only, one per building, ~1.05s apart for the
60/min per-key limit.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://api.oxs.co.il/api/external/v1"


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
        "x-api-key": key, "User-Agent": "homies-oxs-debt-sync/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.loads(r.read().decode("utf-8"))
    if body.get("status") != 1:
        raise RuntimeError(f"{path}: {body.get('error')}")
    return body["data"]


def e164(raw):
    if not raw:
        return None
    d = re.sub(r"\D", "", str(raw))
    if d.startswith("972"):
        d = d[3:]
    d = d.lstrip("0")
    return "+972" + d if len(d) >= 8 else None


def rows(data):
    return data.get("results", data) if isinstance(data, dict) else (data or [])


def sweep():
    kg, kf = E["OXS_KEY_GENERAL"], E["OXS_KEY_DEBTS"]
    buildings = [b for b in get("/buildings", kg) if not b.get("disable")]
    print(f"sweeping {len(buildings)} active buildings for current debts")

    found = []
    for i, b in enumerate(buildings, 1):
        addr = f"{b.get('street','').strip()} {b.get('number','').strip()}, {b.get('city','').strip()}"
        for rec in rows(get(f"/buildings/{b['_id']}/debts", kf)):
            total = rec.get("totalDebt") or 0
            if total <= 0:
                continue
            owner = (rec.get("owners") or [{}])[0]
            cd = owner.get("contactDetails") or {}
            found.append({
                "phone": e164(cd.get("mobilePhone") or cd.get("phone")),
                "name": (owner.get("firstName") or "").strip() or "דייר",
                "amount": float(total),
                "address": rec.get("address") or addr,
                "unit": str((rec.get("apartment") or {}).get("number") or ""),
                "oxs_ref": rec.get("_id"),
            })
        if i % 25 == 0 or i == len(buildings):
            print(f"  {i}/{len(buildings)} buildings, {len(found)} debts found")
        time.sleep(1.05)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    found = sweep()
    total = sum(f["amount"] for f in found)
    print(f"\nOXS says {len(found)} apartments owe money, ₪{total:,.0f} in total")
    for f in sorted(found, key=lambda x: -x["amount"]):
        print(f"  {f['name'][:24]:<24} {f['amount']:>9,.0f}  {f['address']:<28} "
              f"apt {f['unit']:<4} {f['phone'] or 'NO PHONE'}")

    import psycopg
    dsn = E.get("SUPABASE_DB_URL", "").strip()
    if not dsn:
        sys.exit("SUPABASE_DB_URL is empty in .env.")
    period = date.today().replace(day=1)
    live_phones = {f["phone"] for f in found if f["phone"]}

    with psycopg.connect(dsn, connect_timeout=15) as conn:
        current = conn.execute("""
            select r.phone, r.full_name, c.amount, c.period
            from charges c join residents r on r.id = c.resident_id
            where c.status = 'unpaid'
        """).fetchall()
        stale = [c for c in current if c[0] not in live_phones]

        print(f"\nin Supabase now: {len(current)} unpaid charges")
        print(f"OXS does not list {len(stale)} of them — these are settled:")
        for phone, name, amount, per in stale:
            print(f"  {name[:24]:<24} {float(amount):>9,.0f}  {per}  {phone}")

        if not a.apply:
            print("\nDry run — nothing written. Re-run with --apply.")
            return

        with conn.transaction():
            paid = conn.execute("""
                update charges c set status = 'paid'
                from residents r
                where r.id = c.resident_id
                  and c.status = 'unpaid'
                  and not (r.phone = any(%s))
            """, (list(live_phones),)).rowcount

            added = updated = nophone = 0
            for f in found:
                if not f["phone"]:
                    nophone += 1
                    continue
                conn.execute("""
                    insert into residents (full_name, phone, building, unit, oxs_ref,
                                           source, handed_over, do_not_call)
                    values (%s, %s, %s, %s, %s, 'oxs', false, false)
                    on conflict (phone) do update set
                      building = excluded.building, unit = excluded.unit
                """, (f["name"], f["phone"], f["address"], f["unit"], f["oxs_ref"]))
                n = conn.execute("""
                    insert into charges (resident_id, period, amount, status, oxs_ref)
                    select id, %s, %s, 'unpaid', %s from residents where phone = %s
                    on conflict (resident_id, period) do update set
                      amount = excluded.amount, status = 'unpaid',
                      oxs_ref = excluded.oxs_ref
                """, (period, f["amount"], f["oxs_ref"], f["phone"])).rowcount
                added += n
                updated += (1 - n)

        n_unpaid = conn.execute(
            "select count(*) from charges where status = 'unpaid'").fetchone()[0]
        owed = conn.execute(
            "select coalesce(sum(amount),0) from charges where status='unpaid'").fetchone()[0]

    print(f"\nmarked {paid} charges paid")
    print(f"wrote {added + updated} charges from OXS ({nophone} skipped, no phone)")
    print(f"open balances now: {n_unpaid} charges, ₪{float(owed):,.0f}")


if __name__ == "__main__":
    main()
