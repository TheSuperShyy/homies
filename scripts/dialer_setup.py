# -*- coding: utf-8 -*-
"""The dashboard dialer (feature 23, migration 043): its database part and its Tokomni pair.

    python scripts/dialer_setup.py            # read only: the table, the tick job, the secrets, the queue
    python scripts/dialer_setup.py --apply    # TOKOMNI_TOKEN + TOKOMNI_CAMPAIGN_ID into the function, then 043
    python scripts/dialer_setup.py --off      # the kill switch: unschedule the tick and cancel everyone waiting

WHAT IT IS (owner, 25 Nov: "in the dashboard we need to have an actual dialer section there not just the
dialer test"). The dashboard's /dialer puts the tenants a person chose in `dialer_calls`; pg_cron posts
`dialer-tick` to debt-tools every 15 s while that queue has work; each tick sends at most one tenant to
Omni's dialer, only in calling hours and only when the bot's line (208) is quiet.

The function sends the leads, so it needs the same lead token and List 2 id that Vercel holds for the
dialer test page. They go from .env straight into the function's secrets and are never printed: the
read-back compares sha256 digests. Migration 043 goes through the Management API's SQL endpoint, the way
036-042 were applied. Turning the dialer back on after --off is --apply again (043 is idempotent).
"""
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, ".env")
MIGRATION = os.path.join(ROOT, "supabase", "043_dialer.sql")
API = "https://api.supabase.com"
UA = "homies-scripts/1.0"
PAIR = ("TOKOMNI_TOKEN", "TOKOMNI_CAMPAIGN_ID")
JOB = "dialer-tick"


def env():
    d = {}
    for line in open(ENV_PATH, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def call(token, method, path, body=None):
    req = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": UA})
    try:
        res = urllib.request.urlopen(req, timeout=90)
        return res.status, json.loads(res.read() or b"null")
    except urllib.error.HTTPError as ex:
        return ex.code, ex.read().decode("utf-8", "replace")[:300]


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main():
    e = env()
    token = e.get("SUPABASE_ACCESS_TOKEN", "").strip()
    ref = e.get("SUPABASE_URL", "").split("//")[-1].split(".")[0]
    if not token or not ref:
        sys.exit("SUPABASE_ACCESS_TOKEN / SUPABASE_URL missing in .env.")

    def sql(query):
        code, out = call(token, "POST", "/v1/projects/%s/database/query" % ref, {"query": query})
        if code >= 300:
            sys.exit("SQL failed: HTTP %s %s" % (code, out))
        return out

    if "--off" in sys.argv:
        sql("select cron.unschedule(jobid) from cron.job where jobname = '%s'" % JOB)
        if sql("select to_regclass('public.dialer_calls') as t")[0]["t"]:
            n = sql("update dialer_calls set status = 'cancelled', why = 'switched off', ended_at = now() "
                    "where status = 'waiting' returning id")
            print("cancelled      %d waiting" % len(n))
        print("tick           unscheduled: nothing more is sent. --apply turns it back on.")
    elif "--apply" in sys.argv:
        pair = [(name, e.get(name, "").strip()) for name in PAIR]
        if not all(v for _, v in pair):
            sys.exit("TOKOMNI_TOKEN / TOKOMNI_CAMPAIGN_ID empty in .env; nothing changed.")
        code, out = call(token, "POST", "/v1/projects/%s/secrets" % ref,
                         [{"name": n, "value": v} for n, v in pair])
        print("secrets        HTTP %s (%s)" % (code, ", ".join(PAIR)))
        if code >= 300:
            sys.exit(out)
        with open(MIGRATION, encoding="utf-8") as f:
            sql(f.read())
        print("applied        %s" % os.path.basename(MIGRATION))

    # What is there now, whichever mode ran.
    code, out = call(token, "GET", "/v1/projects/%s/secrets" % ref)
    if code != 200 or not isinstance(out, list):
        sys.exit("Could not read the function's secrets: HTTP %s" % code)
    live = {s["name"]: s.get("value") for s in out}
    for name in PAIR + ("VAPI_PRIVATE_KEY",):
        here = e.get(name, "").strip()
        state = ("absent" if name not in live else
                 "as .env" if here and live[name] == sha(here) else "present, differs from .env")
        print("secret         %-20s %s" % (name, state))
    table = sql("select to_regclass('public.dialer_calls') as t")[0]["t"]
    print("table          %s" % ("dialer_calls present" if table else "dialer_calls MISSING (run --apply)"))
    jobs = sql("select jobname, schedule, active from cron.job where jobname = '%s'" % JOB)
    print("tick           %s" % ("%s every %s, active=%s" % (JOB, jobs[0]["schedule"], jobs[0]["active"])
                                 if jobs else "not scheduled"))
    if table:
        for r in sql("select status, count(*) as n from dialer_calls group by 1 order by 1"):
            print("queue          %-10s %s" % (r["status"], r["n"]))
        st = sql("select paused_at, paused_why, resumed_at, last_tick_at, last_error from dialer_state")
        if st:
            s = st[0]
            print("state          paused=%s (%s)  last tick %s  last error %s"
                  % (s["paused_at"] or "no", s["paused_why"] or "-", s["last_tick_at"] or "never",
                     s["last_error"] or "none"))


if __name__ == "__main__":
    main()
