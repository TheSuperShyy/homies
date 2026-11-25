-- 044 — charges carry OXS's own debt (feature 24)
--
-- The owner, 25 Nov 2026, on the Dialer page's amounts: "i need it to be accurate". They were not.
-- `charges` was our own estimate, written twice a day by oxs_arrears.py: every ended 2026 month with
-- no payment record counted as owed, at the flat's usual monthly amount. Read against OXS's live
-- debts the same day, 57 of the page's 201 flats matched; 75 owed nothing in OXS at all.
--
-- Since OXS API rev 1.10 OXS calculates each flat's debt itself, with the rules of its payments
-- screen (תשלומים): `GET /debts` lists every flat that owes, and `GET /apartments/:id/debts` gives
-- it month by month with what is left on each month, plus the open special payments. So charges
-- now hold exactly that: one row per overdue month (earlier years included), and one row per open
-- special payment (a renovation, a reserve fund), which has no month. debt-tools writes them
-- (`oxs-debts-sync`, every 10 minutes, below), and reads a tenant's flats again just before the
-- dialer rings them. Everything that already reads charges (the Dialer page, the call queue, the
-- debt agent's figures, the balance answers) is therefore OXS's figure, not ours.
--
-- WHAT IS OWED. OXS's `totalDebt`: overdue, without this month, which is not late yet. Monthly
-- payments of every year, partly paid months for what is left, and special payments.
--
-- WHAT THIS CHANGES IN THE CALL. The debt agent is told the months still open; a debt from an
-- earlier year now says its year ("נובמבר 2025"), and a special payment is named after the months
-- ("..., וגם תשלום מיוחד: קרן חירום"). The prompt is unchanged: it already reads {{months_phrase}}.
--
-- Applied by hand through the Management API, like 036-043: scripts/oxs_debts_setup.py --apply.
-- Idempotent. Safe to re-run.
-- ---------------------------------------------------------------------------------------------------

-- ---------------------------------------------------------------------------------------------------
-- charges: a special payment, and the flat in OXS
-- ---------------------------------------------------------------------------------------------------

alter table charges add column if not exists kind          text not null default 'monthly';
alter table charges add column if not exists label         text;   -- a special payment's description
alter table charges add column if not exists apartment_ref text;   -- the flat's OXS id (apartments.id)

alter table charges drop constraint if exists charges_kind_check;
alter table charges add constraint charges_kind_check check (kind in ('monthly', 'special'));

-- A special payment belongs to no month. Every month row keeps its month, as before.
alter table charges alter column period drop not null;
alter table charges drop constraint if exists charges_kind_period_check;
alter table charges add constraint charges_kind_period_check check (
  (kind = 'monthly' and period is not null) or (kind = 'special' and period is null));

-- One row per special payment per flat. (resident_id, period, unit) keeps the month rows unique.
create unique index if not exists charges_special_key on charges (apartment_ref, oxs_ref) where kind = 'special';
create index if not exists charges_apartment_idx on charges (apartment_ref) where apartment_ref is not null;

comment on column charges.kind is
  'monthly: one month of the monthly payment (period is that month). special: one open special '
  'payment (תשלום מיוחד), with no month; label is its description and oxs_ref its OXS id. See 044.';
comment on column charges.apartment_ref is
  'The flat''s OXS id. Set on every row written from OXS''s own debt (044); empty on the rows the '
  'old estimate wrote, which the first complete pass closes.';

-- ---------------------------------------------------------------------------------------------------
-- What OXS listed: one row per flat that owes, and the sync's own state
-- ---------------------------------------------------------------------------------------------------

create table if not exists oxs_debt_flats (
  apartment_ref text primary key,              -- OXS apartmentId
  building_ref  text,                          -- OXS buildingId
  address       text,                          -- buildings.address, the string residents.building holds
  number        text,                          -- the flat's number in its building
  phone         text,                          -- the payer whose phone the flat's charges are on
  phones        text[] not null default '{}',  -- every payer's phone OXS gives, for a typed number
  payers        jsonb not null default '[]',   -- [{phone, name, role}], renters first
  overdue       numeric not null default 0,    -- totalDebt
  with_month    numeric not null default 0,    -- totalDebtWithCurrentMonth
  fingerprint   text,                          -- the totals GET /debts gave, to see a change
  seen_at       timestamptz,                   -- the last run that listed it
  detail_fp     text,                          -- the fingerprint its months were last written for
  detail_at     timestamptz
);
create index if not exists oxs_debt_flats_phone_idx  on oxs_debt_flats (phone);
create index if not exists oxs_debt_flats_phones_idx on oxs_debt_flats using gin (phones);

comment on table oxs_debt_flats is
  'Feature 24: every flat OXS''s GET /debts listed, with its totals and payers. debt-tools keeps it; '
  'charges are written from each flat''s month-by-month detail.';

create table if not exists oxs_debt_state (
  id              smallint primary key default 1 check (id = 1),
  run_started_at  timestamptz,   -- a run holds the sync while this is recent
  last_run_at     timestamptz,
  last_ok_at      timestamptz,   -- the last run that read OXS's list
  last_error      text,
  owing           integer,       -- flats in OXS's list
  overdue_flats   integer,       -- of them, with something overdue
  backlog         integer,       -- overdue flats whose months are not written for their latest totals
  complete_at     timestamptz    -- the first pass with no backlog: the old estimate's rows closed then
);
insert into oxs_debt_state (id) values (1) on conflict (id) do nothing;

alter table oxs_debt_flats enable row level security;
alter table oxs_debt_state enable row level security;
drop policy if exists staff_read on oxs_debt_flats;
create policy staff_read on oxs_debt_flats for select to authenticated using (true);
drop policy if exists staff_read on oxs_debt_state;
create policy staff_read on oxs_debt_state for select to authenticated using (true);

-- ---------------------------------------------------------------------------------------------------
-- What debt-tools calls (service role)
-- ---------------------------------------------------------------------------------------------------

-- One run at a time: true when this run may go. A run that died lets the next one go after p_seconds.
create or replace function oxs_debt_lease(p_seconds integer)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
  update oxs_debt_state set run_started_at = now()
   where id = 1
     and (run_started_at is null or run_started_at < now() - make_interval(secs => greatest(p_seconds, 30)));
  return found;
end;
$$;

-- What GET /debts listed this run. Every flat is kept (seen_at = p_run); the answer is the backlog:
-- flats with something overdue whose months were not written for their latest totals, the ones a
-- person is dialling first, then the largest debts. `legacy_phone` is the phone that held the
-- flat's charges under the old estimate, so the first pass keeps the number staff already call.
create or replace function oxs_debt_seen(p_flats jsonb, p_run timestamptz)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  f   jsonb;
  out jsonb;
begin
  for f in select * from jsonb_array_elements(coalesce(p_flats, '[]'::jsonb)) loop
    insert into oxs_debt_flats (apartment_ref, building_ref, address, number, phones, payers,
                                overdue, with_month, fingerprint, seen_at)
    values (f ->> 'ref', f ->> 'building_ref', f ->> 'address', f ->> 'number',
            coalesce(array(select jsonb_array_elements_text(f -> 'phones')), '{}'),
            coalesce(f -> 'payers', '[]'::jsonb),
            coalesce((f ->> 'overdue')::numeric, 0), coalesce((f ->> 'with_month')::numeric, 0),
            f ->> 'fp', p_run)
    on conflict (apartment_ref) do update
      set building_ref = excluded.building_ref, address = excluded.address, number = excluded.number,
          phones = excluded.phones, payers = excluded.payers, overdue = excluded.overdue,
          with_month = excluded.with_month, fingerprint = excluded.fingerprint, seen_at = excluded.seen_at;
  end loop;

  select coalesce(jsonb_agg(jsonb_build_object(
           'ref', b.apartment_ref, 'phone', b.phone, 'legacy_phone', b.legacy_phone)
         order by b.dialling desc, b.overdue desc, b.apartment_ref), '[]'::jsonb)
    into out
    from (
      select fl.apartment_ref, fl.phone, fl.overdue,
             exists (select 1 from dialer_calls d
                      where d.status in ('waiting', 'sending')
                        and (d.phone = fl.phone or d.phone = any(fl.phones))) as dialling,
             (select r.phone from charges c join residents r on r.id = c.resident_id
               where c.apartment_ref is null and c.source = 'oxs' and c.status = 'unpaid'
                 and r.building = fl.address and c.unit = coalesce(fl.number, '')
               order by c.amount desc limit 1) as legacy_phone
        from oxs_debt_flats fl
       where fl.seen_at = p_run and fl.overdue > 0
         and fl.detail_fp is distinct from fl.fingerprint
    ) b;
  return out;
end;
$$;

-- One flat, from its month-by-month detail, in one transaction:
--   p = {ref, phone, name, building, unit, home, fp, overdue, with_month,
--        items: [{kind:'monthly', period, amount} | {kind:'special', ref, label, amount}]}
-- The payer's resident is found by phone, or added. Each item is written as an unpaid charge; a
-- row of this flat that OXS no longer counts is closed (status 'paid'), on whichever phone it was.
-- A row a person or the agent put in review (disputed, pending_charge, waived) keeps its status.
-- So does an 'agent' row: the test building's demo charges are never touched. `home` moves the
-- resident's building and flat to this one (the payer's largest debt), which is where the payment
-- link and the balance lookup look.
create or replace function oxs_debt_apply(p jsonb)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  rid           uuid;
  it            jsonb;
  kept_month    date[] := '{}';
  kept_special  text[] := '{}';
  apt           text := p ->> 'ref';
  unit_         text := coalesce(p ->> 'unit', '');
  written       integer := 0;
  closed        integer := 0;
  legacy        integer := 0;
  n             integer;
begin
  if coalesce(apt, '') = '' then
    return jsonb_build_object('error', 'no ref');
  end if;
  perform pg_advisory_xact_lock(hashtext('homies-oxs-debts'), hashtext(apt));

  if coalesce(p ->> 'phone', '') ~ '^\+972[0-9]{8,9}$' then
    select id into rid from residents where phone = p ->> 'phone';
    if rid is null then
      insert into residents (full_name, phone, building, unit, source, handed_over, do_not_call)
      values (coalesce(nullif(btrim(p ->> 'name'), ''), 'דייר'), p ->> 'phone', coalesce(p ->> 'building', ''),
              unit_, 'oxs', false, false)
      returning id into rid;
    elsif coalesce((p ->> 'home')::boolean, false) and coalesce(p ->> 'building', '') <> '' then
      update residents set building = p ->> 'building', unit = unit_
       where id = rid and (building is distinct from p ->> 'building' or unit is distinct from unit_);
    end if;
  end if;

  if rid is not null then
    for it in select * from jsonb_array_elements(coalesce(p -> 'items', '[]'::jsonb)) loop
      continue when coalesce((it ->> 'amount')::numeric, 0) <= 0;
      if it ->> 'kind' = 'monthly' then
        insert into charges (resident_id, period, amount, status, source, unit, kind, apartment_ref)
        values (rid, (it ->> 'period')::date, (it ->> 'amount')::numeric, 'unpaid', 'oxs', unit_, 'monthly', apt)
        on conflict (resident_id, period, unit) do update
          set amount = excluded.amount, apartment_ref = excluded.apartment_ref, kind = 'monthly',
              label = null, updated_at = now(),
              status = case when charges.status = 'paid' then 'unpaid' else charges.status end
          where charges.source = 'oxs'
            and (charges.apartment_ref is null or charges.apartment_ref = excluded.apartment_ref);
        kept_month := kept_month || (it ->> 'period')::date;
      else
        update charges
           set amount = (it ->> 'amount')::numeric, label = it ->> 'label', resident_id = rid, unit = unit_,
               updated_at = now(), status = case when status = 'paid' then 'unpaid' else status end
         where kind = 'special' and apartment_ref = apt and oxs_ref = it ->> 'ref';
        if not found then
          insert into charges (resident_id, period, amount, status, source, unit, kind, label,
                               apartment_ref, oxs_ref)
          values (rid, null, (it ->> 'amount')::numeric, 'unpaid', 'oxs', unit_, 'special',
                  it ->> 'label', apt, it ->> 'ref');
        end if;
        kept_special := kept_special || (it ->> 'ref');
      end if;
      written := written + 1;
    end loop;
  end if;

  -- What OXS no longer counts on this flat, on any phone.
  update charges c set status = 'paid', updated_at = now()
   where c.apartment_ref = apt and c.source = 'oxs' and c.status = 'unpaid'
     and not coalesce(
           (c.kind = 'monthly' and c.resident_id = rid and c.period = any(kept_month))
        or (c.kind = 'special' and c.oxs_ref = any(kept_special)), false);
  get diagnostics closed = row_count;

  -- The old estimate's rows for this flat that the writes above did not take over.
  update charges c set status = 'paid', updated_at = now()
    from residents r
   where c.resident_id = r.id and c.apartment_ref is null and c.source = 'oxs' and c.status = 'unpaid'
     and r.building = p ->> 'building' and c.unit = unit_;
  get diagnostics legacy = row_count;

  insert into oxs_debt_flats (apartment_ref, address, number, phone, overdue, with_month, detail_fp, detail_at)
  values (apt, p ->> 'building', unit_, nullif(p ->> 'phone', ''),
          coalesce((p ->> 'overdue')::numeric, 0), coalesce((p ->> 'with_month')::numeric, 0),
          p ->> 'fp', now())
  on conflict (apartment_ref) do update
    set phone = excluded.phone, detail_fp = excluded.detail_fp, detail_at = excluded.detail_at,
        overdue = case when p ? 'overdue' then excluded.overdue else oxs_debt_flats.overdue end,
        with_month = case when p ? 'with_month' then excluded.with_month else oxs_debt_flats.with_month end;

  return jsonb_build_object('resident_id', rid, 'written', written, 'closed', closed, 'legacy', legacy);
end;
$$;

-- The end of a run. With p_clear (OXS's list was read and looked whole), a flat the list no
-- longer has, or has with nothing overdue, has every open row closed; and once a pass finishes
-- with no backlog, so is every row the old estimate wrote. The state row says how it went.
create or replace function oxs_debt_finish(p_run timestamptz, p_clear boolean, p_backlog integer,
                                           p_owing integer, p_overdue integer, p_error text)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  gone    integer := 0;
  strays  integer := 0;
  legacy  integer := 0;
begin
  if p_clear then
    update charges c set status = 'paid', updated_at = now()
      from oxs_debt_flats f
     where c.apartment_ref = f.apartment_ref and c.source = 'oxs' and c.status = 'unpaid'
       and (f.seen_at is distinct from p_run or f.overdue <= 0);
    get diagnostics gone = row_count;
    update oxs_debt_flats set detail_fp = null
     where (seen_at is distinct from p_run or overdue <= 0) and detail_fp is not null;
    update charges c set status = 'paid', updated_at = now()
     where c.apartment_ref is not null and c.source = 'oxs' and c.status = 'unpaid'
       and not exists (select 1 from oxs_debt_flats f where f.apartment_ref = c.apartment_ref);
    get diagnostics strays = row_count;
    if p_backlog = 0 then
      update charges set status = 'paid', updated_at = now()
       where apartment_ref is null and source = 'oxs' and status = 'unpaid';
      get diagnostics legacy = row_count;
      update oxs_debt_state set complete_at = coalesce(complete_at, now()) where id = 1;
    end if;
  end if;
  update oxs_debt_state
     set last_run_at = now(),
         last_ok_at = case when p_clear then now() else last_ok_at end,
         last_error = p_error,
         owing = coalesce(p_owing, owing), overdue_flats = coalesce(p_overdue, overdue_flats),
         backlog = coalesce(p_backlog, backlog), run_started_at = null
   where id = 1;
  return jsonb_build_object('closed', gone, 'strays', strays, 'legacy', legacy);
end;
$$;

-- ---------------------------------------------------------------------------------------------------
-- The call queue: a special payment counts, and the months say their year when it is not this one
-- ---------------------------------------------------------------------------------------------------
-- 038's view, with a special payment allowed in and `kind` and `label` appended (create or
-- replace keeps every existing column's name, type and position).

create or replace view v_debt_call_queue as
select
  c.id                                   as charge_id,
  r.id                                   as resident_id,
  r.phone,
  split_part(r.full_name, ' ', 1)        as first_name,
  r.building,
  c.unit,
  coalesce(r.gender, name_gender(r.full_name), 'unknown') as gender,
  coalesce(r.card_last4, '')             as card_last4,
  money_say(c.amount)                    as amount,
  case extract(month from c.period)
    when  1 then 'ינואר'   when  2 then 'פברואר' when  3 then 'מרץ'
    when  4 then 'אפריל'   when  5 then 'מאי'     when  6 then 'יוני'
    when  7 then 'יולי'    when  8 then 'אוגוסט'  when  9 then 'ספטמבר'
    when 10 then 'אוקטובר' when 11 then 'נובמבר'  when 12 then 'דצמבר'
  end                                    as month,
  (c.attempts + 1)::text                 as attempt,
  c.period,
  c.last_call_at,
  c.amount                               as amount_raw,
  c.kind,
  c.label
from charges c
join residents r on r.id = c.resident_id
where c.status      = 'unpaid'
  and c.amount      > 0
  and (c.period is not null or c.kind = 'special')
  and r.handed_over = true
  and r.do_not_call = false
  and c.attempts    < 4;

-- 013's person view. Two changes, both in what the agent is told:
--   months_phrase: the months of this year as before ("אפריל, מאי ויולי"); when any open month is
--     from an earlier year, every month carries its year ("נובמבר 2025 ודצמבר 2025"). Then the
--     special payments by name: "..., וגם תשלום מיוחד: קרן חירום". Never empty: a resident here
--     owes something, a month or a special payment.
--   charges: each entry also says its kind and label.
-- A resident who owes only special payments is in it now (the months join is a left join).
create or replace view v_debt_call_queue_person as
with per_unit as (
  select q.resident_id, q.unit, sum(q.amount_raw) as unit_total
    from v_debt_call_queue q
   group by q.resident_id, q.unit
),
units as (
  select p.resident_id,
         array_agg(p.unit order by p.unit)                                       as unit_list,
         array_agg(money_say(p.unit_total) || ' על דירה ' || p.unit order by p.unit) as unit_parts
    from per_unit p
   group by p.resident_id
),
years as (
  select q.resident_id,
         bool_and(extract(year from q.period)
                  = extract(year from (now() at time zone 'Asia/Jerusalem'))) as this_year_only
    from v_debt_call_queue q
   where q.kind = 'monthly'
   group by q.resident_id
),
months as (
  select d.resident_id, array_agg(d.word order by d.period_month) as month_list
    from (
      select distinct q.resident_id,
             date_trunc('month', q.period) as period_month,
             case when y.this_year_only then q.month
                  else q.month || ' ' || extract(year from q.period)::int::text end as word
        from v_debt_call_queue q
        join years y on y.resident_id = q.resident_id
       where q.kind = 'monthly'
    ) d
   group by d.resident_id
),
specials as (
  select s.resident_id, array_agg(s.word order by s.word) as label_list
    from (
      select distinct q.resident_id, coalesce(nullif(btrim(q.label), ''), 'תשלום מיוחד') as word
        from v_debt_call_queue q
       where q.kind = 'special'
    ) s
   group by s.resident_id
)
select
  q.resident_id,
  q.phone,
  min(q.first_name)                                      as first_name,
  min(q.gender)                                          as gender,
  min(q.card_last4)                                      as card_last4,
  hebrew_list(array_agg(distinct q.building), false)     as building,
  count(*)::int                                          as open_charges,
  array_length(u.unit_list, 1)                           as apartments_owing_count,
  u.unit_list                                            as apartments_owing,
  jsonb_agg(jsonb_build_object(
    'charge_id', q.charge_id,
    'unit',      q.unit,
    'period',    q.period,
    'amount',    q.amount_raw,
    'kind',      q.kind,
    'label',     q.label
  ) order by q.unit, q.period nulls last)                as charges,
  money_say(sum(q.amount_raw))                           as amount,
  case when array_length(u.unit_list, 1) = 1
       then 'דירה '  || u.unit_list[1]
       else 'דירות ' || hebrew_list(u.unit_list, true)
  end                                                    as apartments_phrase,
  hebrew_list(u.unit_parts, true)                        as breakdown_phrase,
  -- hebrew_list(NULL) is '' rather than NULL, and concat_ws keeps an '', so the case is needed.
  concat_ws(', וגם ',
    case when m.month_list is null then null else hebrew_list(m.month_list, false) end,
    case when s.label_list is null then null
         when array_length(s.label_list, 1) = 1 then 'תשלום מיוחד: ' || s.label_list[1]
         else 'תשלומים מיוחדים: ' || hebrew_list(s.label_list, false)
    end)                                                 as months_phrase,
  case when array_length(u.unit_list, 1) = 1 then u.unit_list[1] else '' end
                                                         as unit,
  max(q.attempt::int)::text                              as attempt,
  max(q.last_call_at)                                    as last_call_at
from v_debt_call_queue q
join units         u on u.resident_id = q.resident_id
left join months   m on m.resident_id = q.resident_id
left join specials s on s.resident_id = q.resident_id
group by q.resident_id, q.phone, u.unit_list, u.unit_parts, m.month_list, s.label_list;

alter view v_debt_call_queue        set (security_invoker = on);
alter view v_debt_call_queue_person set (security_invoker = on);

-- ---------------------------------------------------------------------------------------------------
-- A try counts on a special payment too, and a voice payment link may be for one
-- ---------------------------------------------------------------------------------------------------

-- 043's, with the special payments in its predicate (the same rows v_debt_call_queue carries).
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
     and (period is not null or kind = 'special') and attempts < 4;
  if p_outcome is not null then
    select max(attempts) into a from charges where resident_id = p_resident and status = 'unpaid';
    insert into call_outcomes (resident_id, outcome, attempt) values (p_resident, p_outcome, a);
  end if;
end;
$$;

-- 034's shape, but a debt call's link row may carry no month: a tenant who owes only a special
-- payment has none to give.
alter table payment_links drop constraint if exists payment_links_shape;
alter table payment_links add constraint payment_links_shape check (
     (channel = 'voice'    and charge_id is not null and amount is not null)
  or (channel = 'whatsapp' and apartment_id is not null and link is not null)
);

-- ---------------------------------------------------------------------------------------------------
-- Who may call what
-- ---------------------------------------------------------------------------------------------------

revoke all on function oxs_debt_lease(integer)                                       from public, anon, authenticated;
revoke all on function oxs_debt_seen(jsonb, timestamptz)                             from public, anon, authenticated;
revoke all on function oxs_debt_apply(jsonb)                                         from public, anon, authenticated;
revoke all on function oxs_debt_finish(timestamptz, boolean, integer, integer, integer, text)
                                                                                    from public, anon, authenticated;
grant execute on function oxs_debt_lease(integer)                                    to service_role;
grant execute on function oxs_debt_seen(jsonb, timestamptz)                          to service_role;
grant execute on function oxs_debt_apply(jsonb)                                      to service_role;
grant execute on function oxs_debt_finish(timestamptz, boolean, integer, integer, integer, text)
                                                                                    to service_role;

-- ---------------------------------------------------------------------------------------------------
-- The sync: every 10 minutes
-- ---------------------------------------------------------------------------------------------------
-- 041's post, with the same vault secret. The function answers at once and works on in the
-- background (one GET /debts, then the month-by-month detail of flats that changed, at most about
-- 40 OXS calls a minute so the payment link keeps its share of OXS's 60), so 10 s is plenty.
select cron.schedule(
  'oxs-debts-sync',
  '*/10 * * * *',
  $job$
  select net.http_post(
    url := 'https://nmxlhlmcnnggnnuxyelt.supabase.co/functions/v1/debt-tools',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'x-homies-secret', (select decrypted_secret from vault.decrypted_secrets
                          where name = 'debt_tools_tool_secret' limit 1)),
    body := '{"message":{"type":"oxs-debts-sync"}}'::jsonb,
    timeout_milliseconds := 10000
  );
  $job$
);
