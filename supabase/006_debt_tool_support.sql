-- Homies — what the debt-tools Edge Function needs that 004 does not provide.
-- Run after 004 and 005.

-- ---------------------------------------------------------------------------
-- bump_charge_attempt
-- ---------------------------------------------------------------------------
-- log_call_outcome calls this on every call. It exists as a function rather than
-- an update because `attempts = attempts + 1` cannot be expressed through
-- PostgREST without first reading the row — and two calls to the same resident
-- overlapping would then both read 1 and both write 2, losing an attempt. The
-- queue gates on attempts < 4, so a lost attempt is a resident called five
-- times. Doing the arithmetic inside the database makes that impossible.

create or replace function bump_charge_attempt(p_charge_id uuid)
returns void
language sql
security definer
set search_path = public
as $$
  update charges
     set attempts     = attempts + 1,
         last_call_at = now()
   where id = p_charge_id;
$$;

comment on function bump_charge_attempt is
  'Increments the attempt counter atomically. Properly the campaign runner owns
   this, because it knows a call was placed even when the agent never reached
   log_call_outcome; calling it from the tool as well is the backstop.';

-- ---------------------------------------------------------------------------
-- One ticket per charge
-- ---------------------------------------------------------------------------
-- A retried tool call, or an agent that calls open_payment_ticket twice in one
-- conversation, would otherwise put two tickets in front of a member of staff
-- for the same debt — and the whole point of the ticket queue is that a person
-- charges a card exactly once.

create unique index if not exists payment_tickets_one_open_per_charge
  on payment_tickets (charge_id)
  where status in ('pending', 'approved');

-- ---------------------------------------------------------------------------
-- v_pending_payment_tickets
-- ---------------------------------------------------------------------------
-- The queue a member of staff actually works through. Ordered oldest first,
-- because the authorisation was given on a call and the resident is waiting.

create or replace view v_pending_payment_tickets as
select
  t.id,
  t.created_at,
  r.full_name,
  r.phone,
  r.building,
  r.unit,
  t.amount,
  to_char(t.period, 'MM/YYYY')  as period,
  t.card_last4,
  t.authorization_captured,
  i.audio_url,
  i.external_call_id
from payment_tickets t
join residents r on r.id = t.resident_id
left join interactions i on i.id = t.interaction_id
where t.status = 'pending'
order by t.created_at;

comment on view v_pending_payment_tickets is
  'audio_url is the authorisation itself, not evidence about it. A row with
   authorization_captured = true and no audio_url must not be charged — Vapi
   deletes recordings after 14 days and a chargeback window is far longer, so
   the recording has to be copied to our own storage at end of call.';
