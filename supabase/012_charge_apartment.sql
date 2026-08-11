-- ---------------------------------------------------------------------------
-- 012 — a charge belongs to an apartment, not to a phone
-- ---------------------------------------------------------------------------
-- `charges` was unique on (resident_id, period) and `residents.phone` is unique,
-- so an owner with three flats in one building survived the import as one
-- resident and one charge per month. `import_arrears.py` ran
-- `on conflict (resident_id, period) do update set amount = excluded.amount`,
-- which means the second apartment did not merge with the first — it overwrote
-- it. Measured 11 Aug against the arrears source: two owners, two apartments
-- invisible, ₪6,665.40 of real money absent from the dashboard.
--
-- The apartment moves onto the charge rather than onto the resident key. The
-- alternative — keying residents on (phone, unit) — would make `residents.phone`
-- non-unique, and every identity path in the system starts from a phone:
-- `get_balance` on WhatsApp, the n8n memory window, `v_conversations`. A lookup
-- that can return three rows turns a balance question into a disambiguation
-- mid-call. Keeping one person per phone and letting their charges name the
-- apartment costs one column.
--
-- No write tool needs changing. Every one of them keys off the `charge_id` the
-- campaign runner attached to the call, never off (resident, period), so the
-- constraint underneath them can change without their touching it.

alter table charges add column if not exists unit text;

-- Backfill from the resident. `residents.unit` is NOT NULL and, verified on
-- 11 Aug, for all 119 residents in arrears it already names an apartment that
-- genuinely owes — the collapse hid the *second* flat, it did not mislabel the
-- first. So this is correct for every existing row, and the two missing
-- apartments come back with the re-import rather than from here.
update charges c
   set unit = r.unit
  from residents r
 where r.id = c.resident_id
   and c.unit is null;

-- Empty string, not NULL, for an unknown apartment. In a unique constraint
-- Postgres treats NULLs as distinct from each other, so a nullable column would
-- let (resident, period, NULL) be inserted twice and quietly reopen the exact
-- duplicate this migration exists to prevent.
alter table charges alter column unit set default '';
update charges set unit = '' where unit is null;
alter table charges alter column unit set not null;

comment on column charges.unit is
  'The apartment this charge is for. An owner with several flats has one charge
   per flat per month; residents.unit names only one of them and is not
   authoritative for debt. Empty string, never NULL, so the unique constraint
   below cannot be bypassed by two unknown apartments.';

alter table charges drop constraint if exists charges_resident_id_period_key;
alter table charges drop constraint if exists charges_resident_period_unit_key;
alter table charges add constraint charges_resident_period_unit_key
  unique (resident_id, period, unit);

-- ---------------------------------------------------------------------------
-- Every real charge says it is real
-- ---------------------------------------------------------------------------
-- `charges.source` defaults to 'seed' and `import_arrears.py` never set it, so
-- all 173 real charges claimed to be fictional while their residents correctly
-- said 'oxs'. 007 makes this column the thing every destructive query filters
-- on — which put the entire arrears list one purge away from deletion, by a
-- query written to be careful.
--
-- Scoped to charges whose resident came from OXS rather than blanket-updating:
-- if fictional residents are ever seeded again, their charges must stay 'seed'.
-- There are none today, which is why this is safe to run now.
update charges c set source = 'oxs'
  from residents r
 where r.id = c.resident_id and r.source = 'oxs' and c.source = 'seed';

create index if not exists charges_unit_idx on charges (resident_id, unit);

-- ---------------------------------------------------------------------------
-- The call queue names the apartment the debt is for
-- ---------------------------------------------------------------------------
-- `r.unit` becomes `c.unit`. Without this an owner of two flats would be told
-- the amount for one and the apartment number of the other, which is the worst
-- possible combination: specific, confident, and wrong.
--
-- One row per apartment per month means a two-flat owner owing four months
-- yields eight rows. That is not new — four months already yielded four rows —
-- and collapsing a person's calls is the campaign runner's job, not this view's.
-- The view's contract is that every row carries everything one call needs.

create or replace view v_debt_call_queue as
select
  c.id                                   as charge_id,
  r.id                                   as resident_id,
  r.phone,
  split_part(r.full_name, ' ', 1)        as first_name,
  r.building,
  c.unit,
  coalesce(r.gender, 'unknown')          as gender,
  coalesce(r.card_last4, '')             as card_last4,
  to_char(c.amount, 'FM999999')          as amount,
  case extract(month from c.period)
    when  1 then 'ינואר'   when  2 then 'פברואר' when  3 then 'מרץ'
    when  4 then 'אפריל'   when  5 then 'מאי'     when  6 then 'יוני'
    when  7 then 'יולי'    when  8 then 'אוגוסט'  when  9 then 'ספטמבר'
    when 10 then 'אוקטובר' when 11 then 'נובמבר'  when 12 then 'דצמבר'
  end                                    as month,
  (c.attempts + 1)::text                 as attempt,
  c.period,
  c.last_call_at
from charges c
join residents r on r.id = c.resident_id
where c.status      = 'unpaid'
  and c.amount      > 0
  and c.period     is not null
  and r.handed_over = true
  and r.do_not_call = false
  and c.attempts    < 4;

comment on view v_debt_call_queue is
  'Every column is a template variable the debt prompt uses. A resident with no
   card on file appears with card_last4 = empty string, which the prompt handles
   by not mentioning a card. `unit` comes from the charge, not the resident, so
   an owner of several flats is told about the right one.';

-- Re-asserted rather than assumed. 009 turned this on because a view otherwise
-- reads with its owner's rights and hands rows to whoever asks — which is what
-- this view was doing. Restating it after a replace costs nothing and removes
-- the question of whether the option survived.
alter view v_debt_call_queue set (security_invoker = on);
