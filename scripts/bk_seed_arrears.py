# -*- coding: utf-8 -*-
"""Give בר כוכבא 23's residents the charges OXS already shows against them.

    python scripts/bk_seed_arrears.py            # dry run
    python scripts/bk_seed_arrears.py --apply

WHY THIS EXISTS AND `oxs_arrears.py` DOES NOT DO IT. That importer derives each
apartment's monthly figure from its own PAYMENT history (`monthsPaid[].amount`)
precisely so nothing is invented -- and every flat in this building has paid
nothing, ever. With no payment to read a rate from, the importer files the flat
under "unknown" and writes no charge, which is the correct conservative answer
for a client's building and the wrong one here.

So the figure comes from the month rows themselves
(`/apartments/:aid/payments?year=`, `payments[year]['ועד בית'].months[].amount`),
which is what OXS has actually charged rather than anything guessed. Only months
that have already ENDED are seeded -- the same rule oxs_arrears.py uses, since
the current month is not late yet.

SCOPED TO THE TEST BUILDING BY CONSTRUCTION. The building id is hard-coded and
there is no flag to change it, because of the owner's rule of 24 Sep: *"use the
information that is in the bar kochba building always for testing because
outside of that is real information of the clients and we dont want to edit
those in a way."* A file that cannot be pointed at a client's building cannot
be pointed at one by accident.

Residents that already carry charges are left alone, so this never doubles a
balance and is safe to re-run. `--off` removes what it wrote.
"""
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n8n_whatsapp as W  # noqa: E402
import oxs_debt_sync as O  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BUILDING_ID = "6266589524cc8a004c24ece1"          # בר כוכבא 23, תל אביב - יפו
BUILDING = "בר כוכבא 23, תל אביב - יפו"
CATEGORY = "ועד בית"
# `oxs` and not `agent`: OXS really does show these unpaid, so that is the
# honest provenance, and it means the arrears sweep will keep them correct --
# marking them paid if somebody ever pays. An `agent` charge would go stale.
SOURCE = "oxs"


def ended_months(year):
    """Months of `year` that have already finished, as period strings."""
    today = datetime.date.today()
    last = 12 if year < today.year else today.month - 1
    return ["%d-%02d-01" % (year, m) for m in range(1, last + 1)]


def main():
    apply = "--apply" in sys.argv
    off = "--off" in sys.argv
    year = datetime.date.today().year
    want_periods = set(ended_months(year))

    e = W.env()
    base = e["SUPABASE_URL"].rstrip("/") + "/rest/v1/"
    key = e["SUPABASE_SERVICE_ROLE_KEY"].strip()
    h = {"apikey": key, "Authorization": "Bearer " + key,
         "Content-Type": "application/json", "Prefer": "return=representation"}

    def rest(method, path, body=None):
        req = urllib.request.Request(base + path, method=method, headers=h,
                                     data=json.dumps(body).encode() if body is not None else None)
        try:
            return json.loads(urllib.request.urlopen(req, timeout=40).read() or b"[]")
        except urllib.error.HTTPError as ex:
            sys.exit("HTTP %s on %s: %s" % (ex.code, path.split("?")[0], ex.read().decode()[:300]))

    q = "residents?building=ilike." + urllib.parse.quote("*בר כוכבא 23*", safe="")
    residents = rest("GET", q + "&select=id,full_name,unit,phone,source")
    if not residents:
        sys.exit("no residents on %s -- nothing to seed." % BUILDING)

    if off:
        n = 0
        for r in residents:
            gone = rest("DELETE", "charges?resident_id=eq.%s&source=eq.%s" % (r["id"], SOURCE))
            n += len(gone)
        print("removed %d seeded charge(s) from %s" % (n, BUILDING))
        return

    # --- what OXS charges each flat, per month --------------------------------
    kg = O.E["OXS_KEY_GENERAL"]
    aps = O.rows(O.get("/buildings/%s/apartments" % BUILDING_ID, kg))
    per_unit = {}
    for a in aps:
        d = O.get("/buildings/%s/apartments/%s/payments?year=%d" % (BUILDING_ID, a["_id"], year), kg)
        blk = ((d.get("payments") or {}).get(str(year)) or {}).get(CATEGORY) or {}
        for i, m in enumerate(blk.get("months") or []):
            amt = float(m.get("amount") or 0)
            if amt <= 0 or m.get("wasPaid"):
                continue
            period = "%d-%02d-01" % (year, i + 1)
            if period in want_periods:
                per_unit.setdefault(str(a.get("number")), []).append((period, amt))

    print("building : %s" % BUILDING)
    print("months   : %d ended in %d" % (len(want_periods), year))

    # THE SAME PERSON CAN SIT ON A FLAT TWICE. The OXS import writes a row per
    # tenant, and the demo scripts add their own with a different phone, so
    # flat 1 carries עידו קליקס from both. Charging both would put one person
    # on the debt-call queue twice and double the flat's arrears. Matching on
    # name-and-unit is enough here: a flat with two DIFFERENT names on it is a
    # real pair of residents and both should be charged.
    charged_names = set()
    for r in residents:
        if rest("GET", "charges?resident_id=eq.%s&select=id&limit=1" % r["id"]):
            charged_names.add((str(r.get("unit") or ""), (r.get("full_name") or "").strip()))

    planned = []
    for r in sorted(residents, key=lambda x: str(x.get("unit"))):
        have = rest("GET", "charges?resident_id=eq.%s&select=id" % r["id"])
        unit = str(r.get("unit") or "")
        owed = per_unit.get(unit, [])
        key_nm = (unit, (r.get("full_name") or "").strip())
        if not have and key_nm in charged_names:
            print("  flat %-3s %-16s skip, the same person already carries charges here"
                  % (unit, (r.get("full_name") or "")[:16]))
            continue
        if have:
            print("  flat %-3s %-16s skip, already has %d charge(s)" % (unit, (r.get("full_name") or "")[:16], len(have)))
            continue
        if not owed:
            print("  flat %-3s %-16s skip, OXS shows nothing unpaid and ended" % (unit, (r.get("full_name") or "")[:16]))
            continue
        total = sum(a for _, a in owed)
        print("  flat %-3s %-16s + %d month(s), %d total" % (unit, (r.get("full_name") or "")[:16], len(owed), total))
        planned.append((r, unit, owed))

    if not planned:
        print("")
        print("Nothing to do.")
        return
    if not apply:
        print("")
        print("Dry run. Re-run with --apply to write it.")
        return

    for r, unit, owed in planned:
        rest("POST", "charges", [{"resident_id": r["id"], "period": p, "amount": a,
                                  "status": "unpaid", "unit": unit, "source": SOURCE}
                                 for p, a in owed])
    print("")
    print("written for %d resident(s)." % len(planned))


if __name__ == "__main__":
    main()
