"""OXS's own debt in charges (feature 24, migration 044): set it up, run it, check it.

    python scripts/oxs_debts_setup.py              # read only: is 044 in, the sync's state, the open charges
    python scripts/oxs_debts_setup.py --apply      # migration 044 (idempotent), then the read-back
    python scripts/oxs_debts_setup.py --run [N]    # up to N sync runs now (default 30), until no backlog
    python scripts/oxs_debts_setup.py --check      # the Dialer's flats against OXS's live GET /debts
    python scripts/oxs_debts_setup.py --off        # the kill switch: unschedule the 10-minute sync

WHY (the owner, 25 Nov 2026, on the Dialer page's amounts: "i need it to be accurate"). charges were
our estimate from payment records (oxs_arrears.py): 57 of the page's 201 flats matched OXS. Since OXS
API rev 1.10 OXS works each flat's debt out itself, so debt-tools copies it: pg_cron posts
`oxs-debts-sync` every 10 minutes, a run reads GET /debts and then the month-by-month detail of the
flats whose totals changed (at most about 40 OXS calls a minute), and oxs_debt_apply writes them. The
old estimate's rows are closed once a first run finishes with no backlog.

Prints counts and sums only: no names, phones or flats (this repository is public, and so are its
Actions logs). OXS is only read. The migration goes through the Management API's SQL endpoint, the
way 036-043 were applied.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, ".env")
MIGRATION = os.path.join(ROOT, "supabase", "044_oxs_live_debts.sql")
API = "https://api.supabase.com"
UA = "homies-scripts/1.0"
JOB = "oxs-debts-sync"


def env():
    d = {}
    for line in open(ENV_PATH, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def http(method, url, headers, body=None, timeout=90):
    req = urllib.request.Request(url, method=method, headers={**headers, "User-Agent": UA},
                                 data=json.dumps(body).encode("utf-8") if body is not None else None)
    try:
        res = urllib.request.urlopen(req, timeout=timeout)
        return res.status, json.loads(res.read() or b"null")
    except urllib.error.HTTPError as ex:
        return ex.code, ex.read().decode("utf-8", "replace")[:300]


def main():
    e = env()
    token = e.get("SUPABASE_ACCESS_TOKEN", "").strip()
    base = e.get("SUPABASE_URL", "").strip().rstrip("/")
    ref = base.split("//")[-1].split(".")[0]
    if not token or not ref:
        sys.exit("SUPABASE_ACCESS_TOKEN / SUPABASE_URL missing in .env.")

    def sql(query):
        code, out = http("POST", "%s/v1/projects/%s/database/query" % (API, ref),
                         {"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                         {"query": query}, timeout=120)
        if code >= 300:
            sys.exit("SQL failed: HTTP %s %s" % (code, out))
        return out

    def applied():
        return bool(sql("select to_regclass('public.oxs_debt_flats') as t")[0]["t"])

    if "--off" in sys.argv:
        sql("select cron.unschedule(jobid) from cron.job where jobname = '%s'" % JOB)
        print("unscheduled %s. charges keep what the last run wrote; --apply schedules it again." % JOB)
        return

    if "--apply" in sys.argv:
        sql(open(MIGRATION, encoding="utf-8").read())
        print("applied        044_oxs_live_debts.sql")

    if "--run" in sys.argv:
        if not applied():
            sys.exit("044 is not applied: --apply first.")
        i = sys.argv.index("--run")
        runs = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 and sys.argv[i + 1].isdigit() else 30
        secret = e.get("TOOL_SECRET", "").strip()
        for n in range(1, runs + 1):
            code, out = http("POST", base + "/functions/v1/debt-tools",
                             {"Content-Type": "application/json", "x-homies-secret": secret},
                             {"message": {"type": "oxs-debts-sync", "wait": True}}, timeout=170)
            if code != 200 or not isinstance(out, dict):
                print("run %d: HTTP %s %s" % (n, code, str(out)[:160]))
                if code in (401, 404):
                    return
                time.sleep(20)
                continue
            keep = {k: out.get(k) for k in ("ok", "state", "owing", "overdue", "detailed", "failed",
                                            "mismatched", "backlog", "written", "closed", "ms", "error")
                    if k in out}
            print("run %d: %s %s" % (n, json.dumps(keep), json.dumps(out.get("finish") or {})))
            if out.get("state") == "another run is going":
                time.sleep(30)
                continue
            if out.get("error") and "429" in str(out.get("error")):
                time.sleep(65)
            if out.get("ok") and out.get("backlog") == 0:
                break

    if "--check" in sys.argv:
        check(e, sql)
        return

    # The read-back, always.
    if not applied():
        print("044            NOT applied (python scripts/oxs_debts_setup.py --apply)")
        return
    st = sql("select last_ok_at, last_run_at, last_error, owing, overdue_flats, backlog, complete_at "
             "from oxs_debt_state where id = 1")[0]
    job = sql("select schedule, active from cron.job where jobname = '%s'" % JOB)
    open_ = sql("""select kind, source, count(*) as n, round(sum(amount)) as total,
                          count(*) filter (where apartment_ref is null) as old_estimate
                     from charges where status = 'unpaid' group by kind, source order by kind, source""")
    print("044            applied")
    print("job            %s" % (("%s, %s" % (job[0]["schedule"], "active" if job[0]["active"] else "INACTIVE"))
                                 if job else "NOT scheduled"))
    print("last run       %s (ok %s)%s" % (st["last_run_at"], st["last_ok_at"],
                                          ("  error: " + st["last_error"]) if st["last_error"] else ""))
    print("OXS lists      %s flats, %s with something overdue; backlog %s; first full pass %s"
          % (st["owing"], st["overdue_flats"], st["backlog"], st["complete_at"] or "not yet"))
    for r in open_:
        print("open charges   %-8s %-6s %5s rows  %10s  (old estimate: %s)"
              % (r["kind"], r["source"], r["n"], r["total"], r["old_estimate"]))


def check(e, sql):
    """The Dialer's open charges per flat, against OXS's live overdue total per flat."""
    req = urllib.request.Request("https://api.oxs.co.il/api/external/v1/debts",
                                 headers={"x-api-key": e["OXS_KEY_DEBTS"], "User-Agent": UA})
    data = json.loads(urllib.request.urlopen(req, timeout=90).read().decode("utf-8"))["data"]
    rows = data.get("results", data) if isinstance(data, dict) else data
    oxs = {str(r.get("apartmentId")): round(float(r.get("totalDebt") or 0), 2) for r in rows}
    overdue = {k: v for k, v in oxs.items() if v > 0}
    ours = {r["apartment_ref"]: round(float(r["owed"]), 2) for r in sql(
        """select c.apartment_ref, sum(c.amount) as owed from charges c
            where c.status = 'unpaid' and c.amount > 0 and c.source = 'oxs' and c.apartment_ref is not null
            group by c.apartment_ref""")}
    phone = {r["apartment_ref"] for r in sql(
        "select apartment_ref from oxs_debt_flats where coalesce(array_length(phones, 1), 0) > 0")}
    old = sql("select count(*) as n from charges where status = 'unpaid' and source = 'oxs' "
              "and apartment_ref is null")[0]["n"]
    same = sum(1 for k, v in ours.items() if abs(overdue.get(k, 0) - v) <= 1)
    differ = sum(1 for k, v in ours.items() if k in overdue and abs(overdue[k] - v) > 1)
    not_owing = sum(1 for k in ours if k not in overdue)
    missing = [k for k in overdue if k not in ours]
    print("OXS overdue    %d flats, %.0f in total" % (len(overdue), sum(overdue.values())))
    print("on the Dialer  %d flats, %.0f in total" % (len(ours), sum(ours.values())))
    print("  equal to OXS           %d" % same)
    print("  different              %d" % differ)
    print("  not overdue in OXS     %d" % not_owing)
    print("OXS flats not on it      %d (%d of them with no phone in OXS)"
          % (len(missing), sum(1 for k in missing if k not in phone)))
    print("old-estimate rows open   %d" % old)


if __name__ == "__main__":
    main()
