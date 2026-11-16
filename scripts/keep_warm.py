# -*- coding: utf-8 -*-
"""Keep debt-tools warm in Tokyo (migration 041): pg_cron pings it every 15 seconds.

    python scripts/keep_warm.py            # read only: the jobs, their last runs, the ping's answers
    python scripts/keep_warm.py --apply    # TOOL_SECRET into the vault, then 041; reads back
    python scripts/keep_warm.py --off      # unschedule both jobs (the extensions and the secret stay)

WHY (owner, 16 Nov: "make the opening faster so there's no silence"). Vapi asks debt-tools which agent
answers before it picks up the line. The first call after a quiet spell waited 2.4 s for that, 1.7 s of
it a worker starting; a warm worker answers in about 0.15 s. Workers on this plan stop taking requests
about 75 s after they start, so the ping comes every 15 s, pinned to ap-northeast-1 as Vapi's calls are.

The secret goes from .env (TOOL_SECRET) straight into the vault as 'debt_tools_tool_secret' and is never
printed or written to a file. Runs through the Management API's SQL endpoint (SUPABASE_ACCESS_TOKEN),
the way the migrations are applied.
"""
import json
import os
import secrets
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402  (its env() reads .env)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRATION = os.path.join(ROOT, "supabase", "041_keep_debt_tools_warm.sql")
SECRET_NAME = "debt_tools_tool_secret"
JOBS = ("keep-debt-tools-warm", "purge-cron-run-details")


def sql(query):
    e = W.env()
    ref = e["SUPABASE_URL"].split("//")[1].split(".")[0]
    req = urllib.request.Request(
        "https://api.supabase.com/v1/projects/%s/database/query" % ref,
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": "Bearer " + e["SUPABASE_ACCESS_TOKEN"], "Content-Type": "application/json",
                 "User-Agent": "homies-scripts/1.0"},
        method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())


def quoted(value):
    """A dollar-quoted literal whose tag cannot occur in the value."""
    while True:
        tag = "s" + secrets.token_hex(6)
        if "$%s$" % tag not in value:
            return "$%s$%s$%s$" % (tag, value, tag)


def put_secret():
    value = W.env()["TOOL_SECRET"].strip()
    if len(value) < 20:
        sys.exit("TOOL_SECRET in .env looks wrong; nothing changed.")
    have = sql("select id from vault.secrets where name = '%s'" % SECRET_NAME)
    if have:
        sql("select vault.update_secret('%s'::uuid, %s)" % (have[0]["id"], quoted(value)))
        print("vault: %s updated" % SECRET_NAME)
    else:
        sql("select vault.create_secret(%s, '%s', 'x-homies-secret for the keep-warm ping (041)')"
            % (quoted(value), SECRET_NAME))
        print("vault: %s created" % SECRET_NAME)


def show():
    ext = sql("select extname from pg_extension where extname in ('pg_cron', 'pg_net') order by 1")
    print("extensions:", ", ".join(r["extname"] for r in ext) or "none")
    print("vault secret:", "present" if sql("select 1 from vault.secrets where name = '%s'" % SECRET_NAME)
          else "missing")
    if not any(r["extname"] == "pg_cron" for r in ext):
        return
    for j in sql("select jobid, jobname, schedule, active from cron.job order by jobid"):
        print("job %s %-24s %-12s active=%s" % (j["jobid"], j["jobname"], j["schedule"], j["active"]))
    runs = sql("select d.status, count(*) as n, max(d.start_time) as last from cron.job_run_details d "
               "join cron.job j using (jobid) where j.jobname = 'keep-debt-tools-warm' "
               "and d.start_time > now() - interval '10 minutes' group by 1 order by 1")
    for r in runs:
        print("runs, last 10 min: %-10s %s (last %s)" % (r["status"], r["n"], str(r["last"])[:19]))
    if any(r["extname"] == "pg_net" for r in ext):
        answers = sql("select status_code, left(coalesce(content, error_msg, ''), 120) as body, created "
                      "from net._http_response order by id desc limit 3")
        for a in answers:
            print("ping answer %s %s | %s" % (str(a["created"])[:19], a["status_code"], a["body"]))


def main():
    if "--off" in sys.argv:
        for name in JOBS:
            sql("select cron.unschedule(jobid) from cron.job where jobname = '%s'" % name)
        print("unscheduled:", ", ".join(JOBS))
    elif "--apply" in sys.argv:
        put_secret()
        with open(MIGRATION, encoding="utf-8") as f:
            sql(f.read())
        print("applied", os.path.basename(MIGRATION))
    show()


if __name__ == "__main__":
    main()
