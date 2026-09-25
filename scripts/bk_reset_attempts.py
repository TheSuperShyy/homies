# -*- coding: utf-8 -*-
"""Put the test building's debtors back on the calling list after rehearsals.

    python scripts/bk_reset_attempts.py            # dry run
    python scripts/bk_reset_attempts.py --apply    # write it

WHY. The call queue gates on `charges.attempts < 4` (004, restated in 012 and
013), and every call that ends with `log_call_outcome` counts one. Four
rehearsals against the same demo resident and they vanish from the Voice Agent
list — which reads exactly like somebody deleted them, and on 25 Sep did:
*"assaf got removed?"*. Nothing was removed. The charges were still `unpaid`,
still `handed_over`, just out of attempts.

This sets `attempts` back to 0 and clears `last_call_at` for the demo arrears in
בר כוכבא 23, so the list repopulates.

בר כוכבא 23 ONLY, hard-coded, no flag to change it. A reset anywhere else would
erase a real collections history: how many times a resident has actually been
rung is the record the office works from, and four attempts is a decision to
stop calling, not a counter to tidy away.

IT DOES NOT TOUCH STATUS. A charge that is `paid` or `disputed` is out of the
queue for a reason of its own and stays out; this only returns the ones that are
still `unpaid`. See `bk_demo_as_tenant.py` for the dispute case.
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


def main():
    apply = "--apply" in sys.argv
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
            sys.exit("HTTP %s on %s: %s" % (ex.code, path.split("?")[0],
                                            ex.read().decode()[:250]))

    residents = call("GET", "residents?building=eq."
                     + urllib.parse.quote(BUILDING, safe="")
                     + "&select=id,full_name,unit,phone")
    if not residents:
        sys.exit("no residents in %s -- refusing to guess." % BUILDING)

    total = []
    for r in residents:
        ch = call("GET", "charges?resident_id=eq.%s&status=eq.unpaid"
                  "&attempts=gt.0&select=id,attempts" % r["id"])
        if not ch:
            continue
        total.extend(c["id"] for c in ch)
        print("  %-14s unit %-3s  %d unpaid charges at attempt %s"
              % (r["full_name"], r["unit"], len(ch),
                 sorted({c["attempts"] for c in ch})))

    if not total:
        print("Nothing to reset: no unpaid charge here has been tried yet.")
        return
    print("\n%d charges would go back to attempt 0." % len(total))
    if not apply:
        print("Dry run. Re-run with --apply to write it.")
        return

    call("PATCH", "charges?id=in.(%s)" % ",".join(total),
         {"attempts": 0, "last_call_at": None})
    print("reset %d charges. The Voice Agent list should show them again." % len(total))


if __name__ == "__main__":
    main()
