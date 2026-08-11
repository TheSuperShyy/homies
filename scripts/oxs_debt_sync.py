#!/usr/bin/env python
"""Report what OXS's debts endpoints say. **Reports only — it cannot write.**

    python scripts/oxs_debt_sync.py

WHY THIS NO LONGER WRITES — 11 Aug 2026
It was built to reconcile: sweep `/buildings/:id/debts` across every active
building, and mark `paid` any Supabase charge that OXS does not list, on the
premise that "OXS is the record; if OXS does not list it, it is settled."

That premise is false, and the cost of it was measured rather than guessed. A
full sweep of all 173 active buildings on 11 Aug returned **one apartment
owing ₪1,500** — a 2022 balance against an owner marked inactive. Supabase at
that moment held 170 unpaid charges, all of them real. Running `--apply` would
have marked **169 real debts as paid** and destroyed the arrears list.

The debts endpoints are a **collections ledger**, not an arrears tracker: a
place a case is filed once it escalates past normal chasing, which is why the
only entry is four years old and belongs to somebody who left. Month-to-month
arrears are never entered there. They are computed from payment records, which
is what `oxs_arrears.py` and `import_arrears.py` do, and that is the only path
that may write charges.

It also stamped every debt it found with `date.today()`, because these records
carry no month — which is how a 2022 balance came to be labelled 2026-08 and
sat on the dashboard as a phantom current debt until it was retired.

What survives is the useful half: seeing what OXS's collections ledger holds.
Read-only against OXS, GETs only, ~1.05s apart for the 60/min per-key limit.
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
    ap = argparse.ArgumentParser(description=__doc__)
    # Kept, so anybody reaching for the old flag gets the reason rather than a
    # usage error and a workaround.
    ap.add_argument("--apply", action="store_true",
                    help="removed 11 Aug 2026 — see the module docstring")
    a = ap.parse_args()

    if a.apply:
        sys.exit(
            "--apply was removed on 11 Aug 2026.\n\n"
            "This script used to mark a charge 'paid' whenever OXS did not list\n"
            "it. A full sweep of all 173 buildings that day returned ONE debt,\n"
            "against 170 real unpaid charges in Supabase — so applying it would\n"
            "have marked 169 real debts as settled.\n\n"
            "The debts endpoints are a collections ledger, not an arrears\n"
            "tracker. Arrears are computed from payment records:\n"
            "  scripts/oxs_arrears.py    -> compute\n"
            "  scripts/import_arrears.py -> write\n")

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

    # Read-only, and stated as a comparison rather than a reconciliation. The
    # gap between the two numbers below is the finding — it is what showed that
    # these endpoints do not describe monthly arrears at all.
    live_phones = {f["phone"] for f in found if f["phone"]}
    with psycopg.connect(dsn, connect_timeout=15) as conn:
        current = conn.execute("""
            select r.phone, r.full_name, c.amount, c.period
            from charges c join residents r on r.id = c.resident_id
            where c.status = 'unpaid'
        """).fetchall()
        absent = [c for c in current if c[0] not in live_phones]

    print(f"\nin Supabase now: {len(current)} unpaid charges")
    print(f"OXS's debts endpoints do not mention {len(absent)} of them.")
    print("That is expected, and is NOT evidence they are settled — arrears")
    print("live in payment records, not in the debts endpoints. This script")
    print("used to mark exactly these as 'paid'.\n")
    print("To refresh arrears: scripts/oxs_arrears.py then import_arrears.py.")


if __name__ == "__main__":
    main()
