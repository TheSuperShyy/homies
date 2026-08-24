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

Read-only against OXS. Three GETs per building, paced inside `get` so the rate
stays under the 60/min limit whatever the network latency is.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
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


# THE LIMIT IS COUNTED PER REQUEST, SO THE PACING HAS TO BE TOO.
#
# This slept 1.05s twice per building while making three GETs, which makes the
# real request rate a function of how fast the network is. From a GitHub runner
# each call takes long enough that the sweep sits near 27/min and never notices.
# Run from a machine close to OXS on 24 Aug it went over 60/min and **37 of 175
# buildings came back 429** -- every one of them dropped from the arrears list
# with a printed warning nobody was reading, taking 511 of 576 debtors with
# them. The sleep now lives in `get`, so the rate is 57/min whatever the
# latency, and a 429 is retried rather than turned into a missing building.
PACE = 1.05
_last = 0.0


def get(path, tries=4):
    global _last
    for attempt in range(tries):
        gap = _last + PACE - time.monotonic()
        if gap > 0:
            time.sleep(gap)
        _last = time.monotonic()
        req = urllib.request.Request(BASE + path, headers={
            "x-api-key": KG, "User-Agent": "homies-oxs-arrears/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                body = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == tries - 1:
                raise
            # Retry-After when they send one, otherwise back off 5s, 10s, 20s.
            back = float(e.headers.get("Retry-After") or 0) or 5 * 2 ** attempt
            print(f"  · rate limited, waiting {back:.0f}s")
            time.sleep(back)
            continue
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

    behind, unknown, failed = [], [], []
    for i, b in enumerate(buildings, 1):
        addr = f"{b.get('street','').strip()} {b.get('number','').strip()}, {b.get('city','').strip()}"
        try:
            aps = {a["_id"]: str(a.get("number") or "") for a in get(f"/buildings/{b['_id']}/apartments")}
            recs = payment_records(get(f"/buildings/{b['_id']}/payments?year={YEAR}"))
        except Exception as exc:
            print(f"  ! {addr}: {exc}")
            failed.append(addr)
            continue

        # tenant contact, keyed by apartment number.
        # A failure here is NOT cosmetic and is no longer swallowed: without the
        # tenants list an apartment keeps its debt but loses its phone, and a row
        # with no phone is dropped by the writer. A building that 429s here
        # disappears from the arrears list as surely as one that fails above.
        try:
            tenants = get(f"/buildings/{b['_id']}/tenants")
        except Exception as exc:
            print(f"  ! {addr} (contacts): {exc}")
            failed.append(f"{addr} (contacts)")
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
                  f"{len(unknown)} with no {YEAR} payment at all"
                  + (f", {len(failed)} unreadable" if failed else ""))
    return behind, unknown, failed


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

    behind, unknown, failed = sweep()
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

    # A PARTIAL SWEEP MUST NOT LOOK LIKE A COMPLETE ONE.
    #
    # Whatever it found is still worth writing -- every write here is an upsert
    # and nothing is deleted, so a short run leaves yesterday's figures standing
    # rather than erasing them. What it must not do is exit 0, because that is
    # the signal the workflow gate and `/sync` both read, and "the arrears list"
    # missing 37 buildings while reporting success is the same lie this whole
    # import spent a fortnight telling.
    if failed:
        print(f"\n{'!'*78}\n{len(failed)} buildings could not be read and are "
              f"MISSING from the list above:")
        for f in failed:
            print(f"  ! {f}")
        print("This run is incomplete. It will still write what it found, and "
              f"then exit non-zero.\n{'!'*78}")

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
        sys.exit(1 if failed else 0)

    import psycopg
    dsn = E.get("SUPABASE_DB_URL", "").strip()
    if not dsn:
        sys.exit("SUPABASE_DB_URL is empty in .env.")
    period = date(YEAR, THIS_MONTH, 1)

    rows = [r for r in behind if r["phone"]]
    skipped = len(behind) - len(rows)

    # ONE DEBTOR CAN APPEAR TWICE, AND THE TABLE CANNOT HOLD BOTH.
    #
    # `charges` is unique on (resident_id, period, unit) and carries no
    # building, so the same phone owing on flat 3 of two different buildings is
    # one row whatever we do. Postgres refuses to update the same row twice
    # inside one statement, so that collision is resolved here instead of
    # raising mid-import: the larger debt wins and the count is reported.
    # Nothing is summed — a summed figure pinned to one flat is the specific,
    # confident and wrong number migration 012 was written to stop.
    best = {}
    for r in sorted(rows, key=lambda r: (r["phone"], str(r["unit"] or ""), -r["amount"])):
        best.setdefault((r["phone"], str(r["unit"] or "")), r)
    collisions = len(rows) - len(best)
    rows = list(best.values())

    names = [r["name"] for r in rows]
    phones = [r["phone"] for r in rows]
    builds = [r["building"] for r in rows]
    units = [str(r["unit"] or "") for r in rows]
    amounts = [r["amount"] for r in rows]

    # ONE STATEMENT PER TABLE, NOT TWO PER APARTMENT.
    #
    # The loop this replaces sent two round trips per debtor to a database on
    # another continent. Measured on 23 Aug in the residents importer, whose
    # identical loop spent fourteen of its nineteen minutes waiting on the
    # network — which is most of the reason the job crossed its ceiling and was
    # killed here, mid-write, twice a day. Same SQL, same conflict handling,
    # one round trip each.
    with psycopg.connect(dsn, connect_timeout=15) as conn:
        with conn.transaction():
            conn.execute("""
                insert into residents (full_name, phone, building, unit, source,
                                       handed_over, do_not_call)
                select distinct on (v.phone)
                       v.name, v.phone, v.building, v.unit, 'oxs', false, false
                  from unnest(%s::text[], %s::text[], %s::text[], %s::text[])
                       as v(name, phone, building, unit)
                 order by v.phone, v.unit
                on conflict (phone) do update set
                  building = excluded.building, unit = excluded.unit
            """, (names, phones, builds, units))

            # THE CONFLICT TARGET IS (resident_id, period, unit).
            #
            # It was (resident_id, period) until 11 Aug, when migration 012 put
            # the apartment on the charge and dropped that constraint. The
            # statement was never updated, so every arrears write since has been
            # a guaranteed 42P10, "no unique or exclusion constraint matching
            # the ON CONFLICT specification" — which nobody saw, because the job
            # was being killed in the sweep before it ever reached this line.
            #
            # `status` is deliberately absent from the update list. It used to be
            # forced back to 'unpaid' every twelve hours, which would re-chase
            # somebody who had paid the moment staff had not yet entered it in
            # OXS — the one outcome the debt agent is built to avoid. A charge
            # marked paid, disputed or waived keeps that status; only the amount
            # is refreshed. `source` is set because it defaults to 'seed', and
            # 'seed' is what every destructive query in 007 deletes.
            written = conn.execute("""
                insert into charges (resident_id, period, amount, status, source, unit)
                select r.id, %s, v.amount, 'unpaid', 'oxs', v.unit
                  from unnest(%s::text[], %s::numeric[], %s::text[])
                       as v(phone, amount, unit)
                  join residents r on r.phone = v.phone
                on conflict (resident_id, period, unit) do update set
                  amount = excluded.amount, source = 'oxs'
            """, (period, phones, amounts, units)).rowcount

        held = conn.execute("""
            select count(*) from charges
             where period = %s and status <> 'unpaid'
        """, (period,)).fetchone()[0]
        n = conn.execute("select count(*) from charges where status='unpaid'").fetchone()[0]
        owed = conn.execute("select coalesce(sum(amount),0) from charges where status='unpaid'").fetchone()[0]

    print(f"\nwrote {written} charges for {period}")
    print(f"  {skipped} skipped, no phone; {collisions} dropped, "
          f"same phone and flat number in two buildings")
    print(f"  {held} charges this period left as they were (paid, disputed or waived)")
    print(f"open balances now: {n} charges, ₪{float(owed):,.0f}")
    if failed:
        sys.exit(f"\nIncomplete: {len(failed)} buildings unread, listed above.")


if __name__ == "__main__":
    main()
