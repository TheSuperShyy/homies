# -*- coding: utf-8 -*-
"""Make the owner's demo number BE a real tenant of בר כוכבא 23, not a fourth person.

    python scripts/bk_demo_as_tenant.py +<country><number>            # dry run
    python scripts/bk_demo_as_tenant.py +<country><number> --apply    # write it

WHY, the owner on 25 Sep: *"i told you link clix to assaf for demo only"*. The
demo row for his +63 tester was its own person called `clix`, sitting on flat 2
beside the flat's actual tenant. So the debt list showed FOUR entries for a
three-tenant building, and a payment link or a balance pulled from that number
belonged to nobody real.

WHAT THIS DOES, and the shape is deliberate:

  1. Renames the demo row to the flat's real tenant, read from the
     `source='oxs'` row for that same flat. The name is never typed in here --
     it comes from OXS, so it cannot drift from what their system says.
  2. Puts that row's charges back to `unpaid` and clears the payment disputes
     against them. They went `disputed` on 24 Sep when a test voice call said
     "I already paid", which is the dispute flow working correctly and is also
     why the number fell off the calling list and read a zero balance.
  3. Clears the charges hanging off the OXS-sourced row for the same flat, so
     the tenant appears ONCE on the list -- through the demo row, which is the
     one the +63 reaches.

WHAT IT DOES NOT DO. The OXS row itself stays, with the tenant's real phone and
`oxs_ref` intact: that row is how `oxsReportedBy()` names a ticket's reporter,
and deleting it would make mirrored tickets anonymous again. Only its charges
go, and those are seeded arrears from `bk_seed_arrears.py`, not client history.

THE DEMO ROW KEEPS `source='agent'`, which is what protects it from the
twice-daily OXS import (that upserts on PHONE and would otherwise not know it).
`debt_demo_person.py off <phone>` still tears it down.

בר כוכבא 23 ONLY, hard-coded, no flag. Every other building is a live client's.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n8n_whatsapp as W  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BUILDING = u"בר כוכבא 23, תל אביב - יפו"
UNIT = "2"


def main():
    apply = "--apply" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    # Taken as an argument, never hard-coded: this is a public repo and a
    # resident's number has no business being committed to it.
    if len(args) != 1 or not args[0].startswith("+"):
        sys.exit("give the demo number in international form, +<country><number>")
    demo_phone = args[0].strip()
    e = W.env()
    base = e["SUPABASE_URL"].rstrip("/") + "/rest/v1/"
    k = e["SUPABASE_SERVICE_ROLE_KEY"].strip()
    h = {"apikey": k, "Authorization": "Bearer " + k,
         "Content-Type": "application/json", "Prefer": "return=representation"}

    def call(method, path, body=None):
        req = urllib.request.Request(
            base + path, method=method, headers=h,
            data=json.dumps(body).encode("utf-8") if body is not None else None)
        try:
            return json.loads(urllib.request.urlopen(req, timeout=30).read() or b"[]")
        except urllib.error.HTTPError as ex:
            sys.exit("HTTP %s on %s %s: %s" % (ex.code, method, path.split("?")[0],
                                               ex.read().decode()[:250]))

    q = "building=eq." + urllib.parse.quote(BUILDING, safe="") + "&unit=eq." + UNIT
    demo = [r for r in call("GET", "residents?%s&select=id,full_name,phone,source" % q)
            if (r.get("phone") or "").strip() == demo_phone]
    real = [r for r in call("GET", "residents?%s&source=eq.oxs&select=id,full_name,phone,oxs_ref" % q)
            if r.get("oxs_ref")]
    if len(demo) != 1:
        sys.exit("expected exactly one demo row on flat %s, found %d" % (UNIT, len(demo)))
    if len(real) != 1:
        sys.exit("expected exactly one OXS tenant on flat %s, found %d" % (UNIT, len(real)))
    demo, real = demo[0], real[0]
    name = str(real["full_name"]).strip()

    demo_ch = call("GET", "charges?resident_id=eq.%s&select=id,status,period" % demo["id"])
    real_ch = call("GET", "charges?resident_id=eq.%s&select=id,status,period" % real["id"])
    bad = [c for c in demo_ch if c.get("status") != "unpaid"]

    print("flat %s of %s" % (UNIT, BUILDING))
    print("  demo row   : %r  -> rename to %r" % (demo["full_name"], name))
    print("  its charges: %d, of which not unpaid: %d" % (len(demo_ch), len(bad)))
    print("  OXS tenant : %r keeps its row; %d charges to clear" % (name, len(real_ch)))
    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    if demo["full_name"] != name:
        call("PATCH", "residents?id=eq.%s" % demo["id"], {"full_name": name})
        print("renamed the demo row to %r" % name)
    if bad:
        ids = ",".join(c["id"] for c in bad)
        call("DELETE", "payment_disputes?charge_id=in.(%s)" % ids)
        call("PATCH", "charges?id=in.(%s)" % ids, {"status": "unpaid"})
        print("restored %d charges to unpaid and cleared their disputes" % len(bad))
    if real_ch:
        ids = ",".join(c["id"] for c in real_ch)
        call("DELETE", "payment_disputes?charge_id=in.(%s)" % ids)
        call("DELETE", "charges?id=in.(%s)" % ids)
        print("cleared %d charges off the OXS row so the tenant appears once" % len(real_ch))
    print("\nDone. The +63 now answers as %r on flat %s." % (name, UNIT))


if __name__ == "__main__":
    main()
