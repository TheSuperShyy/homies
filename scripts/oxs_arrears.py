#!/usr/bin/env python
"""Build the real arrears list for the current year from OXS payment records.

    python scripts/oxs_arrears.py            # dry run: report, write nothing
    python scripts/oxs_arrears.py --apply

WHY THIS EXISTS
`/debts` reports one debtor for the whole company — a 2022 balance belonging to
an owner who has left. It answers "who carries old debt", not "who is behind
this year". Proved on 10 Aug: אנה פרנק 10 has zero debts per `/debts`, while
its own payment records show apartments that have not paid since June.

WHAT COUNTS AS ARREARS
Every month of the current year that has already ended and has no payment
recorded against it. The current month is never chased — it is not late yet.
The monthly figure comes from the apartment's own payment history
(`monthsPaid[].amount`), so nothing is invented; an apartment with no payment
at all this year has no figure to use and is reported separately rather than
guessed at.

Read-only against OXS. Two GETs per building, spaced for the 60/min limit.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://api.oxs.co.il/api/external/v1"
YEAR = date.today().year
THIS_MONTH = date.today().month
DUE = [f"{m:02d}" for m in range(1, THIS_MONTH)]      # ended months only


def env():
    d = {}
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


E = env()
KG = E["OXS_KEY_GENERAL"]


def get(path):
    req = urllib.request.Request(BASE + path, headers={
        "x-api-key": KG, "User-Agent": "homies-oxs-arrears/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = json.loads(r.read().decode("utf-8"))
    if body.get("status") != 1:
        raise RuntimeError(f"{path}: {body.get('error')}")
    return body["data"]


def payment_records(blob):
    """The payments endpoint nests arrays several deep; pull the leaves out."""
    out = []

    def walk(x):
        if isinstance(x, list):
            for i in x:
                walk(i)
        elif isinstance(x, dict):
            if "paymentDate" in x or "monthsPaid" in x:
                out.append(x)
            else:
                for v in x.values():
                    walk(v)
    walk(blob)
    return out


def e164(raw):
    if not raw:
        return None
    d = re.sub(r"\D", "", str(raw))
    if d.startswith("972"):
        d = d[3:]
    d = d.lstrip("0")
    return "+972" + d if len(d) >= 8 else None


def sweep():
    buildings = [b for b in get("/buildings") if not b.get("disable")]
    print(f"{len(buildings)} active buildings · chasing {YEAR}-"
          f"{DUE[0]}..{YEAR}-{DUE[-1]} ({len(DUE)} months, "
          f"{YEAR}-{THIS_MONTH:02d} excluded as not yet late)\n")

    behind, unknown = [], []
    for i, b in enumerate(buildings, 1):
        addr = f"{b.get('street','').strip()} {b.get('number','').strip()}, {b.get('city','').strip()}"
        try:
            aps = {a["_id"]: str(a.get("number") or "") for a in get(f"/buildings/{b['_id']}/apartments")}
            time.sleep(1.05)
            recs = payment_records(get(f"/buildings/{b['_id']}/payments?year={YEAR}"))
        except Exception as exc:
            print(f"  ! {addr}: {exc}")
            time.sleep(1.05)
            continue

        # tenant contact, keyed by apartment number
        try:
            tenants = get(f"/buildings/{b['_id']}/tenants")
        except Exception:
            tenants = []
        contact = {}
        for t in (tenants.get("results", tenants) if isinstance(tenants, dict) else tenants):
            if t.get("isActive") and t.get("number") is not None:
                contact[str(t["number"])] = (
                    re.sub(r"\s*-\s*דירה\s*\S+\s*$", "", t.get("name") or "").strip(),
                    e164(t.get("phone")))

        paid, rate, payer = defaultdict(set), defaultdict(Counter), {}
        for p in recs:
            ap = p.get("apartmentId")
            if not ap:
                continue
            label = p.get("paidByLabel") or (p.get("paidBy") or {}).get("firstName")
            if label:
                payer.setdefault(ap, label.strip())
            for m in (p.get("monthsPaid") or []):
                if str(m.get("year")) != str(YEAR):
                    continue
                mm = str(m.get("month") or "")[:2].zfill(2)
                paid[ap].add(mm)
                if m.get("amount"):
                    rate[ap][float(m["amount"])] += 1

        for ap_id, num in aps.items():
            missing = [m for m in DUE if m not in paid.get(ap_id, set())]
            if not missing:
                continue
            name, phone = contact.get(num, (payer.get(ap_id, ""), None))
            row = {"building": addr, "unit": num, "months": missing,
                   "name": name or payer.get(ap_id, "") or "דייר", "phone": phone}
            if rate[ap_id]:
                monthly = rate[ap_id].most_common(1)[0][0]
                row["monthly"] = monthly
                row["amount"] = monthly * len(missing)
                behind.append(row)
            else:
                unknown.append(row)     # never paid this year — no rate to trust

        if i % 20 == 0 or i == len(buildings):
            print(f"  {i}/{len(buildings)} buildings · {len(behind)} behind, "
                  f"{len(unknown)} with no {YEAR} payment at all")
        time.sleep(1.05)
    return behind, unknown


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    # --quiet EXISTS FOR CI AND IS NOT COSMETIC.
    # The block below is a debtor list: name, amount, months, building, flat and
    # phone, forty rows of it. GitHub Actions logs on a PUBLIC repository are
    # readable by anyone, so a scheduled run without this publishes exactly the
    # document the repo rules forbid committing. The workflow always passes it.
    ap.add_argument("--quiet", action="store_true",
                    help="totals only, no per-apartment lines. Required in CI.")
    a = ap.parse_args()

    behind, unknown = sweep()
    behind.sort(key=lambda r: -r["amount"])
    total = sum(r["amount"] for r in behind)

    print(f"\n{'='*78}\nBEHIND ON {YEAR}: {len(behind)} apartments, ₪{total:,.0f}\n")
    for r in ([] if a.quiet else behind[:40]):
        print(f"  {r['name'][:22]:<22} {r['amount']:>8,.0f}  "
              f"{len(r['months'])}m ({','.join(r['months'])})  "
              f"{r['building'][:26]:<26} apt {r['unit']:<4} {r['phone'] or 'NO PHONE'}")
    if len(behind) > 40:
        print(f"  ... and {len(behind)-40} more")

    print(f"\nNO {YEAR} PAYMENT ON RECORD: {len(unknown)} apartments — "
          f"not chased, no monthly figure to trust (new, vacant, or not handed over)")

    # Gitignored either way (`docs/reference/arrears-*.json`), but a scheduled
    # runner has no reader for it, and one fewer copy of a debtor list on a
    # machine we do not own is worth the two lines.
    if a.quiet:
        print("\nfull list not written (--quiet)")
    else:
        out = os.path.join(ROOT, "docs", "reference", f"arrears-{YEAR}.json")
        json.dump({"behind": behind, "unknown": unknown},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\nfull list written to {out}")

    if not a.apply:
        print("\nDry run — Supabase untouched. Re-run with --apply.")
        return

    import psycopg
    dsn = E.get("SUPABASE_DB_URL", "").strip()
    period = date(YEAR, THIS_MONTH, 1)
    with psycopg.connect(dsn, connect_timeout=15) as conn:
        with conn.transaction():
            written = skipped = 0
            for r in behind:
                if not r["phone"]:
                    skipped += 1
                    continue
                conn.execute("""
                    insert into residents (full_name, phone, building, unit, source,
                                           handed_over, do_not_call)
                    values (%s, %s, %s, %s, 'oxs', false, false)
                    on conflict (phone) do update set
                      building = excluded.building, unit = excluded.unit
                """, (r["name"], r["phone"], r["building"], r["unit"]))
                conn.execute("""
                    insert into charges (resident_id, period, amount, status)
                    select id, %s, %s, 'unpaid' from residents where phone = %s
                    on conflict (resident_id, period) do update set
                      amount = excluded.amount, status = 'unpaid'
                """, (period, r["amount"], r["phone"]))
                written += 1
        n = conn.execute("select count(*) from charges where status='unpaid'").fetchone()[0]
        owed = conn.execute("select coalesce(sum(amount),0) from charges where status='unpaid'").fetchone()[0]
    print(f"\nwrote {written} charges ({skipped} skipped, no phone)")
    print(f"open balances now: {n} charges, ₪{float(owed):,.0f}")


if __name__ == "__main__":
    main()
