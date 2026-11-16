-- 041 — keep debt-tools warm in Tokyo, so a call is answered without a worker starting first
--
-- Owner, 16 Nov: "make the opening faster so there's no silence". On the 10:11 UTC dialer call the
-- tenant heard about 4.5 s of nothing before Michael's first word and hung up. 2.4 s of it was here:
-- Vapi asks debt-tools which agent answers (assistant-request) before it picks up the line, and the
-- first call after a quiet spell waits for a worker to start (1.7 s) and its first database read.
-- A warm worker answers the same question in about 0.15 s (route probes, 16 Nov).
--
-- Why every 15 seconds: on the free plan a worker stops taking requests about 75 s after it starts,
-- busy or not (function logs, 13-16 Nov). The next request starts a new one. With a ping every 15 s
-- a call finds no running worker only in the few seconds between one stopping and the next ping,
-- about one call in ten. 4 pings a minute is about 173,000 function calls a month, against the
-- free plan's 500,000 and about 22,000 used before this.
--
-- The ping is pinned to ap-northeast-1 (x-region) as Vapi's calls are; a worker in another region
-- does not help them. n8n's 2-minute caller from Frankfurt carries no pin, so its workers start in
-- eu-central-1 and never served a call.
--
-- The secret is not in this file. scripts/keep_warm.py puts TOOL_SECRET into the vault as
-- 'debt_tools_tool_secret' before it applies this, and `--off` unschedules both jobs.
-- Applied by hand through the Management API, like 036-040.
-- ---------------------------------------------------------------------------------------------------

create extension if not exists pg_net with schema extensions;
create extension if not exists pg_cron with schema pg_catalog;

-- cron.schedule with a name replaces a job of the same name, so this file can run again.
select cron.schedule(
  'keep-debt-tools-warm',
  '15 seconds',
  $job$
  select net.http_post(
    url := 'https://nmxlhlmcnnggnnuxyelt.supabase.co/functions/v1/debt-tools',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'x-region', 'ap-northeast-1',
      'x-homies-secret', (select decrypted_secret from vault.decrypted_secrets
                          where name = 'debt_tools_tool_secret' limit 1)),
    body := '{"message":{"type":"keep-warm"}}'::jsonb,
    timeout_milliseconds := 8000
  );
  $job$
);

-- pg_cron writes a row for every run, about 5,760 a day at this rate. Keep one day of them.
select cron.schedule(
  'purge-cron-run-details',
  '17 3 * * *',
  $job$ delete from cron.job_run_details where end_time < now() - interval '1 day' $job$
);
