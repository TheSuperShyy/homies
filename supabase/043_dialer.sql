-- 043 — the dialer (feature 23): staff put tenants who owe on Omni's dialer, one call at a time
--
-- The owner, 25 Nov 2026: "in the dashboard we need to have an actual dialer section there not
-- just the dialer test". The dashboard's /dialer lists everyone who owes. A signed-in person ticks
-- tenants and presses Call; each becomes a 'waiting' row here. debt-tools sends them to Omni's
-- dialer one at a time (`dialer-tick`, below), and the tenant who picks up gets the debt agent with
-- their figures (feature 18's router, unchanged).
--
-- WHY ONE AT A TIME. The bot's extension 208 takes one call at a time, and List 2 dials two leads
-- per free agent, so a second lead waiting in List 2 is a call lost (the three 9 Nov leads). So no
-- lead goes to Omni while another is still ringing or talking, and the next goes only when the line
-- is quiet.
--
-- WHY OUR OWN RECORD. A call nobody answers never reaches Vapi: without a row per lead there is no
-- "no answer", no try counted, and no way to know the line is free. Every lead sent is one try on
-- the tenant's open charges (bump_charge_attempt's own comment said the campaign runner should own
-- this), counted once: by the agent's log_call_outcome when it ran, else here.
--
-- NOTHING RINGS BY ITSELF. Every row is a tenant a signed-in person chose and pressed. Outside
-- calling hours the waiting rows are cancelled rather than carried to the morning, and five sent
-- leads in a row that reached nobody pause the queue until a person presses Resume: that pattern
-- means Omni's dialer or 208 is down, not five tenants ignoring us.
--
-- The eligibility for the call itself is still press_call() and v_debt_call_queue_person (024,
-- 013), checked when the lead is sent, not when it was pressed: a tenant who paid in between is
-- skipped. dialer_queue's own checks are only there to say why a press did not go in.
--
-- Applied by hand through the Management API, like 036-042: scripts/dialer_setup.py --apply.
-- Idempotent. Safe to re-run.
-- ---------------------------------------------------------------------------------------------------

create table if not exists dialer_calls (
  id              uuid primary key default gen_random_uuid(),
  resident_id     uuid references residents (id) on delete set null,
  phone           text not null,                -- '+972…', residents.phone's form
  name            text,                         -- the tenant's name when pressed, for the page
  amount          numeric,                      -- owed when pressed; when sent, what the agent was given
  status          text not null default 'waiting'
                    check (status in ('waiting', 'sending', 'ringing', 'answered', 'done',
                                      'no_answer', 'skipped', 'failed', 'cancelled')),
  why             text,                         -- a skip, failure or cancel reason, or Tokomni's answer
  pressed_by      text,                         -- the signed-in email that pressed
  pressed_at      timestamptz not null default now(),
  sent_at         timestamptz,
  answered_at     timestamptz,
  ended_at        timestamptz,
  external_id     text,
  tokomni_status  integer,
  vapi_call_id    text,
  interaction_id  uuid references interactions (id) on delete set null,
  outcome         text,                         -- the agent's log_call_outcome, copied at the end
  attempt         integer                       -- which try this call was
);

create index if not exists dialer_calls_status_idx  on dialer_calls (status, pressed_at);
create index if not exists dialer_calls_phone_idx   on dialer_calls (phone, sent_at desc);
create index if not exists dialer_calls_pressed_idx on dialer_calls (pressed_at desc);
create index if not exists dialer_calls_call_idx    on dialer_calls (vapi_call_id);

comment on table dialer_calls is
  'Feature 23: one row per tenant put on Omni''s dialer from the dashboard. waiting -> sending -> '
  'ringing -> answered -> done, or no_answer / skipped / failed / cancelled. Written by the '
  'dialer_* functions only.';

-- One row: the pause, and what the last tick said.
create table if not exists dialer_state (
  id            smallint primary key default 1 check (id = 1),
  paused_at     timestamptz,
  paused_why    text,
  resumed_at    timestamptz,
  last_tick_at  timestamptz,
  last_error    text
);
insert into dialer_state (id) values (1) on conflict (id) do nothing;

-- Staff read both; nobody writes them except through the functions below.
alter table dialer_calls enable row level security;
alter table dialer_state enable row level security;
drop policy if exists staff_read on dialer_calls;
create policy staff_read on dialer_calls for select to authenticated using (true);
drop policy if exists staff_read on dialer_state;
create policy staff_read on dialer_state for select to authenticated using (true);

-- ---------------------------------------------------------------------------------------------------
-- Helpers
-- ---------------------------------------------------------------------------------------------------

-- The day in Israel, which is the day "already called today" means.
create or replace function dialer_israel_day(at timestamptz)
returns date language sql stable as $$
  select (at at time zone 'Asia/Jerusalem')::date
$$;

-- One try on the tenant's open charges: the same charges a debt call carries
-- (v_debt_call_queue's predicate) and the same arithmetic as bump_charge_attempt (006).
-- With p_outcome, also the call_outcomes row the Calls page's "no answer" tab reads.
create or replace function dialer_count_try(p_resident uuid, p_outcome text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  a integer;
begin
  if p_resident is null then
    return;
  end if;
  update charges
     set attempts = attempts + 1, last_call_at = now()
   where resident_id = p_resident and status = 'unpaid' and amount > 0
     and period is not null and attempts < 4;
  if p_outcome is not null then
    select max(attempts) into a from charges where resident_id = p_resident and status = 'unpaid';
    insert into call_outcomes (resident_id, outcome, attempt) values (p_resident, p_outcome, a);
  end if;
end;
$$;

-- ---------------------------------------------------------------------------------------------------
-- What the dashboard calls (signed in)
-- ---------------------------------------------------------------------------------------------------

-- A press: each phone becomes a waiting row, or a reason it did not.
--   number   not an Israeli '+972' number        queued  already waiting or on the line
--   today    already rang today                  unknown no tenant has this number
--   dnc      on do-not-call                      paid    owes nothing now
--   tries    every open month has had 4 tries
create or replace function dialer_queue(p_phones text[])
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  who      text := nullif(auth.jwt() ->> 'email', '');
  p        text;
  queued   integer := 0;
  skipped  jsonb := '[]'::jsonb;
  t        record;
begin
  if who is null then
    return jsonb_build_object('error', 'not signed in');
  end if;
  perform pg_advisory_xact_lock(hashtext('homies-dialer'));

  for p in select distinct x from unnest(coalesce(p_phones, '{}'::text[])) x where x is not null limit 300 loop
    if p !~ '^\+972[0-9]{8,9}$' then
      skipped := skipped || jsonb_build_object('phone', p, 'why', 'number');
      continue;
    end if;
    if exists (select 1 from dialer_calls
                where phone = p and status in ('waiting', 'sending', 'ringing', 'answered')) then
      skipped := skipped || jsonb_build_object('phone', p, 'why', 'queued');
      continue;
    end if;
    if exists (select 1 from dialer_calls
                where phone = p and status in ('ringing', 'answered', 'done', 'no_answer')
                  and dialer_israel_day(sent_at) = dialer_israel_day(now())) then
      skipped := skipped || jsonb_build_object('phone', p, 'why', 'today');
      continue;
    end if;

    -- Everyone on this number, as one call: a couple on one phone is one ring, shown under the
    -- one who owes the most, and a do-not-call from either keeps the number off the dialer.
    with per as (
      select r.id, r.full_name, r.do_not_call,
             coalesce(sum(c.amount) filter (where c.status = 'unpaid' and c.amount > 0), 0) as owed,
             coalesce(sum(c.amount) filter (where c.status = 'unpaid' and c.amount > 0
                                              and c.attempts < 4), 0)    as callable,
             coalesce(max(c.attempts) filter (where c.status = 'unpaid' and c.amount > 0), 0) as tries
        from residents r
        left join charges c on c.resident_id = r.id
       where r.phone = p
       group by r.id, r.full_name, r.do_not_call
    )
    select (array_agg(id order by owed desc, id))[1]        as resident_id,
           (array_agg(full_name order by owed desc, id))[1] as name,
           coalesce(bool_or(do_not_call), false)            as dnc,
           coalesce(sum(owed), 0)                           as owed,
           coalesce(sum(callable), 0)                       as callable,
           coalesce(max(tries), 0)                          as tries,
           count(*)                                         as people
      into t
      from per;

    if t.people = 0 or t.resident_id is null then
      skipped := skipped || jsonb_build_object('phone', p, 'why', 'unknown');
    elsif t.dnc then
      skipped := skipped || jsonb_build_object('phone', p, 'why', 'dnc');
    elsif t.owed <= 0 then
      skipped := skipped || jsonb_build_object('phone', p, 'why', 'paid');
    elsif t.callable <= 0 then
      skipped := skipped || jsonb_build_object('phone', p, 'why', 'tries');
    else
      insert into dialer_calls (resident_id, phone, name, amount, pressed_by, attempt)
      values (t.resident_id, p, t.name, t.owed, who, t.tries + 1);
      queued := queued + 1;
    end if;
  end loop;

  return jsonb_build_object('queued', queued, 'skipped', skipped);
end;
$$;

-- Stop: everyone still waiting is cancelled. A call already ringing or talking runs to its end.
create or replace function dialer_stop()
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  n   integer;
  who text := nullif(auth.jwt() ->> 'email', '');
begin
  if who is null then
    return 0;
  end if;
  perform pg_advisory_xact_lock(hashtext('homies-dialer'));
  update dialer_calls set status = 'cancelled', why = 'stopped:' || who, ended_at = now()
   where status = 'waiting';
  get diagnostics n = row_count;
  return n;
end;
$$;

-- Resume after the five-in-a-row pause. The streak is counted again from now.
create or replace function dialer_resume()
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if nullif(auth.jwt() ->> 'email', '') is null then
    return;
  end if;
  update dialer_state set paused_at = null, paused_why = null, resumed_at = now() where id = 1;
end;
$$;

-- ---------------------------------------------------------------------------------------------------
-- What debt-tools calls (service role)
-- ---------------------------------------------------------------------------------------------------

-- What is over. p_line_quiet_since is when the bot's line last went quiet (the newest call on 208
-- ended), or NULL when the line is busy or could not be read: then nothing ringing is expired,
-- because the lead may be waiting in Omni's queue for 208 and will still ring.
create or replace function dialer_expire(p_line_quiet_since timestamptz default null)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  r          dialer_calls;
  lost       integer := 0;
  unanswered integer := 0;
  capped     integer := 0;
begin
  perform pg_advisory_xact_lock(hashtext('homies-dialer'));

  -- The worker died between taking the lead and Tokomni's answer. Not a try: it may never have gone.
  update dialer_calls set status = 'failed', why = 'lost', ended_at = now()
   where status = 'sending' and sent_at < now() - interval '2 minutes';
  get diagnostics lost = row_count;

  -- Rang, and nobody picked up: 2 minutes after the send, and 90 seconds after the line went quiet.
  if p_line_quiet_since is not null then
    for r in select * from dialer_calls
              where status = 'ringing'
                and now() > greatest(sent_at + interval '2 minutes',
                                     p_line_quiet_since + interval '90 seconds')
              for update loop
      update dialer_calls set status = 'no_answer', ended_at = now() where id = r.id;
      perform dialer_count_try(r.resident_id, 'no_answer');
      unanswered := unanswered + 1;
    end loop;
  end if;

  -- On the line far longer than a debt call runs, and no end-of-call report came: the line is
  -- free again. If the report comes later, dialer_ended still fills the row in.
  update dialer_calls set status = 'done', why = 'no_report', ended_at = now()
   where status = 'answered' and answered_at < now() - interval '20 minutes';
  get diagnostics capped = row_count;

  return jsonb_build_object('lost', lost, 'no_answer', unanswered, 'capped', capped);
end;
$$;

-- Outside calling hours, or with the dialer not connected: nobody waits for the morning.
create or replace function dialer_cancel_waiting(p_why text)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  n integer;
begin
  perform pg_advisory_xact_lock(hashtext('homies-dialer'));
  update dialer_calls set status = 'cancelled', why = p_why, ended_at = now() where status = 'waiting';
  get diagnostics n = row_count;
  return n;
end;
$$;

-- The next tenant to send, or why there is none: paused, busy (a lead still ringing or talking),
-- or idle. Under one lock with the other writers, so two ticks can never send two leads.
create or replace function dialer_claim_next()
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  st      dialer_state;
  r       dialer_calls;
  q       jsonb;
  n       integer;
  last5   integer;
  nobody  integer;
  i       integer := 0;
begin
  perform pg_advisory_xact_lock(hashtext('homies-dialer'));

  select * into st from dialer_state where id = 1;
  if st.paused_at is not null then
    return jsonb_build_object('state', 'paused');
  end if;
  if exists (select 1 from dialer_calls where status in ('sending', 'ringing', 'answered')) then
    return jsonb_build_object('state', 'busy');
  end if;
  if not exists (select 1 from dialer_calls where status = 'waiting') then
    return jsonb_build_object('state', 'idle');
  end if;

  -- Five sent leads in a row that reached nobody, since the last Resume.
  select count(*), count(*) filter (where status = 'no_answer')
    into last5, nobody
    from (select status from dialer_calls
           where sent_at is not null and status in ('no_answer', 'done')
             and sent_at > coalesce(st.resumed_at, '-infinity'::timestamptz)
           order by sent_at desc limit 5) s;
  if last5 = 5 and nobody = 5 then
    update dialer_state set paused_at = now(), paused_why = 'streak' where id = 1;
    return jsonb_build_object('state', 'paused');
  end if;

  loop
    i := i + 1;
    exit when i > 50;
    select * into r from dialer_calls where status = 'waiting'
     order by pressed_at, id limit 1 for update skip locked;
    if not found then
      return jsonb_build_object('state', 'idle');
    end if;

    if exists (select 1 from dialer_calls
                where phone = r.phone and id <> r.id
                  and status in ('ringing', 'answered', 'done', 'no_answer')
                  and dialer_israel_day(sent_at) = dialer_israel_day(now())) then
      update dialer_calls set status = 'skipped', why = 'today', ended_at = now() where id = r.id;
      continue;
    end if;

    -- The call's own gate (024): puts the tenant on the debt call list, so the router gives the
    -- debt agent, and answers NULL when they owe nothing, are on do-not-call or have had 4 tries.
    q := press_call(r.phone);
    if q is null then
      update dialer_calls set status = 'skipped', why = 'eligible', ended_at = now() where id = r.id;
      continue;
    end if;
    -- Two tenants owing on one number get the incoming agent from the router: the agent never
    -- guesses whose debt it is. So the dialer does not ring that number at all.
    select count(*) into n from v_debt_call_queue_person where phone = r.phone;
    if n > 1 then
      update dialer_calls set status = 'skipped', why = 'shared', ended_at = now() where id = r.id;
      continue;
    end if;

    update dialer_calls
       set status = 'sending', sent_at = now(),
           resident_id = coalesce((q ->> 'resident_id')::uuid, resident_id),
           amount = coalesce(nullif(q ->> 'amount', '')::numeric, amount),
           attempt = coalesce(nullif(q ->> 'attempt', '')::integer, attempt)
     where id = r.id;
    return jsonb_build_object(
      'state', 'send', 'id', r.id, 'phone', r.phone, 'resident_id', q ->> 'resident_id');
  end loop;

  return jsonb_build_object('state', 'idle');
end;
$$;

-- The router saw the dialer's call to this number arrive: the tenant picked up.
create or replace function dialer_answered(p_phone text, p_call_id text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  hit uuid;
begin
  update dialer_calls
     set status = 'answered', answered_at = now(), vapi_call_id = p_call_id
   where id = (select id from dialer_calls
                where phone = p_phone and status in ('sending', 'ringing')
                  and sent_at > now() - interval '15 minutes'
                order by sent_at desc limit 1)
  returning id into hit;
  return hit;
end;
$$;

-- The call's end-of-call report: the lead is done, with the agent's outcome. A call the agent
-- never logged still counts as one try, here, once.
create or replace function dialer_ended(p_call_id text, p_phone text, p_interaction uuid)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  r dialer_calls;
  o text;
begin
  perform pg_advisory_xact_lock(hashtext('homies-dialer'));
  select * into r from dialer_calls where vapi_call_id = p_call_id order by sent_at desc limit 1;
  if not found and p_phone is not null then
    -- The router's mark did not land: the newest lead on this number still ringing.
    select * into r from dialer_calls
     where phone = p_phone and status in ('sending', 'ringing', 'answered')
       and sent_at > now() - interval '30 minutes'
     order by sent_at desc limit 1;
  end if;
  if r.id is null then
    return null;
  end if;
  if p_interaction is not null then
    select outcome into o from call_outcomes
     where interaction_id = p_interaction order by created_at desc limit 1;
  end if;
  update dialer_calls
     set status = 'done', ended_at = now(), answered_at = coalesce(answered_at, now()),
         vapi_call_id = coalesce(vapi_call_id, p_call_id),
         interaction_id = coalesce(p_interaction, interaction_id),
         outcome = coalesce(o, outcome),
         why = case when why = 'no_report' then null else why end
   where id = r.id;
  -- Once: the first report for this lead (a lead capped as no_report had not been counted yet).
  if o is null and r.interaction_id is null and (r.status <> 'done' or r.why = 'no_report') then
    perform dialer_count_try(r.resident_id, null);
  end if;
  return r.id;
end;
$$;

-- ---------------------------------------------------------------------------------------------------
-- Who may call what
-- ---------------------------------------------------------------------------------------------------

revoke all on function dialer_israel_day(timestamptz)               from public;
revoke all on function dialer_count_try(uuid, text)                 from public, anon, authenticated;
revoke all on function dialer_queue(text[])                         from public, anon;
revoke all on function dialer_stop()                                from public, anon;
revoke all on function dialer_resume()                              from public, anon;
revoke all on function dialer_expire(timestamptz)                   from public, anon, authenticated;
revoke all on function dialer_cancel_waiting(text)                  from public, anon, authenticated;
revoke all on function dialer_claim_next()                          from public, anon, authenticated;
revoke all on function dialer_answered(text, text)                  from public, anon, authenticated;
revoke all on function dialer_ended(text, text, uuid)               from public, anon, authenticated;

grant execute on function dialer_israel_day(timestamptz)            to authenticated, service_role;
grant execute on function dialer_queue(text[])                      to authenticated;
grant execute on function dialer_stop()                             to authenticated;
grant execute on function dialer_resume()                           to authenticated;
grant execute on function dialer_count_try(uuid, text)              to service_role;
grant execute on function dialer_expire(timestamptz)                to service_role;
grant execute on function dialer_cancel_waiting(text)               to service_role;
grant execute on function dialer_claim_next()                       to service_role;
grant execute on function dialer_answered(text, text)               to service_role;
grant execute on function dialer_ended(text, text, uuid)            to service_role;

-- ---------------------------------------------------------------------------------------------------
-- The tick: every 15 seconds, and only while the queue has work
-- ---------------------------------------------------------------------------------------------------
-- The same post as 041's keep-warm, with the same vault secret. The WHERE is checked in the
-- database, so an empty queue costs no function call at all; a busy one costs four a minute.
-- 30 s, because a tick may wait up to 20 s for Tokomni. Ticks that overlap are safe: the second
-- finds the first's lead 'sending' and does nothing.
select cron.schedule(
  'dialer-tick',
  '15 seconds',
  $job$
  select net.http_post(
    url := 'https://nmxlhlmcnnggnnuxyelt.supabase.co/functions/v1/debt-tools',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'x-homies-secret', (select decrypted_secret from vault.decrypted_secrets
                          where name = 'debt_tools_tool_secret' limit 1)),
    body := '{"message":{"type":"dialer-tick"}}'::jsonb,
    timeout_milliseconds := 30000
  )
  where exists (select 1 from public.dialer_calls
                 where status in ('waiting', 'sending', 'ringing', 'answered'));
  $job$
);
