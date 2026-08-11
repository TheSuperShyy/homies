-- 013 — one call per resident (feature 14)
--
-- Since 012 a charge belongs to an apartment, so `v_debt_call_queue` is one row
-- per apartment per month. A runner iterating it calls an owner of two flats
-- behind four months eight times, about one debt. This adds the shape a call
-- actually has: one row per PERSON, carrying every apartment of theirs that owes
-- and every month still open.
--
-- SCOPE, DECIDED 11 AUG
-- Only apartments with an open balance. An earlier draft also wanted the ones
-- that owe nothing ("you have three apartments with us"), which needed a new
-- `apartments` table and a change to the OXS sweep. Cut on the client's
-- instruction: "we don't need to look for the apartments that owe nothing."
-- That removed the entire data-collection half of the feature.
--
-- THE PERSON VIEW IS BUILT FROM THE CHARGE VIEW, ON PURPOSE
-- The eligibility predicate — unpaid, has an amount, has a period, handed over,
-- not do-not-call, under four attempts — stays written down exactly once. Two
-- copies of it would drift, and the direction it drifts is calling somebody the
-- other view had excluded. sheets/Code.gs and the dashboard both mirror this
-- predicate by hand already; a third copy is not free.
--
-- Idempotent. Safe to re-run.
--
-- No `begin`/`commit` here. supabase_migrate.py already runs each file inside
-- its own transaction, so an explicit one commits the runner's out from under it
-- and the rollback savepoint it holds stops existing.

-- ---------------------------------------------------------------------------
-- Two helpers, because the phrases are composed here and not by the model
-- ---------------------------------------------------------------------------

-- An amount as it should be SPOKEN.
--
-- `to_char(amount, 'FM999999')` rounds, which was invisible while every seeded
-- charge was a round number and is not: the real OXS import carries 1,971.80 and
-- 101,519.70. An agent that says "one thousand nine hundred seventy two" about a
-- charge of 1,971.80 has stated a figure that appears nowhere, on a collection
-- call, which is the one context where being 20 agorot out is an argument.
--
-- Trailing .00 is not spoken either — "four hundred fifty point zero zero" is
-- not a sentence — so a whole number stays whole.
create or replace function money_say(v numeric) returns text
language sql immutable as $$
  select case
    when v is null           then ''
    when v = round(v, 0)     then to_char(v, 'FM999999999')
    else                          to_char(v, 'FM999999999.00')
  end
$$;

comment on function money_say(numeric) is
  'An amount formatted the way it is read aloud: no rounding, no trailing .00.';

-- A Hebrew list: one item alone, two joined with vav, three or more with commas
-- and a vav before the last.
--
-- `hyphen` is not cosmetic. The vav attaches directly to a word — אפריל, מאי
-- ויולי — and takes a maqaf before a digit — דירות 4 ו-9. Getting it the wrong
-- way round produces ו4, which the TTS reads as a word.
create or replace function hebrew_list(items text[], hyphen boolean default false)
returns text language sql immutable as $$
  select case
    when items is null or array_length(items, 1) is null then ''
    when array_length(items, 1) = 1 then items[1]
    else
      array_to_string(items[1:array_length(items, 1) - 1], ', ')
      || case when hyphen then ' ו-' else ' ו' end
      || items[array_length(items, 1)]
  end
$$;

comment on function hebrew_list(text[], boolean) is
  'Join into a spoken Hebrew list. hyphen=true before digits (ו-9), false before words (ויולי).';

-- ---------------------------------------------------------------------------
-- The charge view gains the raw amount
-- ---------------------------------------------------------------------------
-- `amount` is text because it is a template variable and the model must not see
-- a number it could reformat. The person view has to SUM it, so the numeric is
-- exposed beside it rather than parsed back out of the string. Additive: every
-- existing column keeps its name, type and meaning.
--
-- `amount` itself now goes through money_say, which is a behaviour change to a
-- view nothing reads yet — the queue is empty, and the runner that would read it
-- does not exist. Doing it now means the two views never disagree about what a
-- charge of 1,971.80 sounds like.

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
  -- APPENDED, and it has to be. `create or replace view` will not reorder or
  -- rename an existing column — a new one goes on the end or the replace fails
  -- outright. Putting it beside `amount` where it reads better costs a drop and
  -- recreate, which would take every dependent view down with it.
  c.amount                               as amount_raw
from charges c
join residents r on r.id = c.resident_id
where c.status      = 'unpaid'
  and c.amount      > 0
  and c.period     is not null
  and r.handed_over = true
  and r.do_not_call = false
  and c.attempts    < 4;

comment on view v_debt_call_queue is
  'One row per unpaid charge — an apartment for a month. The eligibility guard: '
  'a resident with no amount, no month, not handed over, on do-not-call, or past '
  'four attempts is absent, so a caller cannot dial one by mistake. '
  'v_debt_call_queue_person groups this into what a call actually is.';

-- ---------------------------------------------------------------------------
-- The call queue: one row per resident
-- ---------------------------------------------------------------------------

create or replace view v_debt_call_queue_person as

-- Everything the resident owes on one apartment, collapsed. This is the unit the
-- breakdown phrase is built from: "450 for apartment 4" is the sum of every open
-- month on 4, not one line per month — an owner four months behind on two flats
-- would otherwise hear eight figures read out and remember none of them.
with per_unit as (
  select
    q.resident_id,
    q.unit,
    sum(q.amount_raw) as unit_total
  from v_debt_call_queue q
  group by q.resident_id, q.unit
),

units as (
  select
    p.resident_id,
    array_agg(p.unit order by p.unit)                                    as unit_list,
    array_agg(money_say(p.unit_total) || ' על דירה ' || p.unit
              order by p.unit)                                           as unit_parts
  from per_unit p
  group by p.resident_id
),

-- Months are DISTINCT across apartments and ordered oldest first. Two flats both
-- behind on April owe April once as far as the sentence is concerned; "April,
-- and also April" is not something anybody should hear.
months as (
  select
    d.resident_id,
    array_agg(d.month order by d.period_month) as month_list
  from (
    select distinct
      q.resident_id,
      date_trunc('month', q.period) as period_month,
      q.month
    from v_debt_call_queue q
  ) d
  group by d.resident_id
)

select
  q.resident_id,
  q.phone,
  -- All identical within a resident; min() is how a group-by says "the one value".
  min(q.first_name)                                      as first_name,
  min(q.gender)                                          as gender,
  min(q.card_last4)                                      as card_last4,
  hebrew_list(array_agg(distinct q.building), false)     as building,

  count(*)::int                                          as open_charges,
  array_length(u.unit_list, 1)                           as apartments_owing_count,
  u.unit_list                                            as apartments_owing,

  -- The whitelist. Every write on this call resolves against it and nothing
  -- else, which is what lets the agent point at one apartment without ever being
  -- able to name a charge that is not on the call.
  jsonb_agg(jsonb_build_object(
    'charge_id', q.charge_id,
    'unit',      q.unit,
    'period',    q.period,
    'amount',    q.amount_raw
  ) order by q.unit, q.period)                           as charges,

  money_say(sum(q.amount_raw))                           as amount,

  -- The three composed phrases. Hebrew is assembled here rather than by the
  -- model for the reason the month name already is: a prompt that has to branch
  -- on "one apartment or several" gets the branch wrong under pressure, and this
  -- one would fire on every call. There is no branch, so it cannot.
  case when array_length(u.unit_list, 1) = 1
       then 'דירה '  || u.unit_list[1]
       else 'דירות ' || hebrew_list(u.unit_list, true)
  end                                                    as apartments_phrase,

  -- Never empty, even for one apartment. A model cannot branch on a variable
  -- that renders as nothing — it sees the prompt after substitution, so an empty
  -- one leaves no trace to test. That is the 4 Aug card_last4 failure exactly.
  --
  -- hyphen=true because each part OPENS with its amount: the vav lands on a
  -- digit — ו-780, not ו780. Caught on the live data 11 Aug: ו5572 renders as a
  -- word to the TTS.
  hebrew_list(u.unit_parts, true)                        as breakdown_phrase,

  hebrew_list(m.month_list, false)                       as months_phrase,

  -- The apartment, when there is exactly one it could mean. Empty when several
  -- do, which is deliberate: a maintenance ticket from a two-flat owner must not
  -- silently land on whichever flat sorted first. The agent asks, or a person
  -- reads the ticket.
  case when array_length(u.unit_list, 1) = 1 then u.unit_list[1] else '' end
                                                         as unit,

  -- The highest attempt across the charges. The queue gate is four, and taking
  -- the max means a charge already tried three times is not reset by a newer one
  -- sharing the call.
  max(q.attempt::int)::text                              as attempt,
  max(q.last_call_at)                                    as last_call_at

from v_debt_call_queue q
join units  u on u.resident_id = q.resident_id
join months m on m.resident_id = q.resident_id
group by q.resident_id, q.phone, u.unit_list, u.unit_parts, m.month_list;

comment on view v_debt_call_queue_person is
  'THE CALL QUEUE. One row per resident: every apartment of theirs that owes, '
  'every month still open, one total, and the charges whitelist every tool write '
  'resolves against. Built from v_debt_call_queue so the eligibility predicate '
  'exists once. A resident here is called once, not once per charge.';

-- security_invoker again, for the same reason 012 re-asserted it: a view without
-- it runs as its owner and hands the anon key rows RLS was meant to withhold.
alter view v_debt_call_queue        set (security_invoker = on);
alter view v_debt_call_queue_person set (security_invoker = on);
