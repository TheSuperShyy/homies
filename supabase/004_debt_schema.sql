-- Homies — outbound debt follow-up (feature 10)
-- Adds the charge/ticket model the debt agent writes to, and the call queue it
-- reads from. Extends 001 rather than replacing anything in it.
--
-- Run in the Supabase SQL editor, or: psql "$SUPABASE_DB_URL" -f 004_debt_schema.sql
--
-- The central decision this encodes: Homies does not charge on the call. The
-- agent captures a spoken authorisation and opens a ticket; a member of staff
-- reviews the ticket and makes the charge. Nothing here moves money.

-- ---------------------------------------------------------------------------
-- residents — new columns
-- ---------------------------------------------------------------------------
-- `card_last4` is the ONLY card data that may ever exist in this database. The
-- card itself lives with the payment processor. Never add a PAN column, never
-- add an expiry, never add a CVV — the agent is instructed to refuse them and
-- there must be nowhere to put them if that instruction ever fails.

alter table residents add column if not exists gender       text;
alter table residents add column if not exists card_last4   text;
alter table residents add column if not exists handed_over  boolean not null default true;
alter table residents add column if not exists do_not_call  boolean not null default false;

alter table residents drop constraint if exists residents_gender_check;
alter table residents add  constraint residents_gender_check
  check (gender is null or gender in ('m','f','unknown'));

alter table residents drop constraint if exists residents_card_last4_check;
alter table residents add  constraint residents_card_last4_check
  check (card_last4 is null or card_last4 ~ '^[0-9]{4}$');

comment on column residents.card_last4 is
  'Last four digits only, for the agent to name on the call. Never store a full
   card number here or anywhere else in this schema.';
comment on column residents.handed_over is
  'False when the apartment has not been handed over. Two of the four sample
   calls should never have been placed for exactly this reason — it is a database
   check, not a prompt condition.';

-- ---------------------------------------------------------------------------
-- charges
-- ---------------------------------------------------------------------------
-- One row per resident per billing period. `period` is the first day of the
-- month it covers, so it sorts and compares properly; the agent speaks the
-- Hebrew month name, which is derived at query time and never stored.

create table if not exists charges (
  id           uuid primary key default gen_random_uuid(),
  resident_id  uuid not null references residents (id) on delete cascade,
  period       date not null,                   -- first of the month, e.g. 2026-07-01
  amount       numeric(10,2) not null check (amount > 0),
  status       text not null default 'unpaid'
                 check (status in ('unpaid','paid','disputed','waived','pending_charge')),
  attempts     integer not null default 0,
  last_call_at timestamptz,
  oxs_ref      text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (resident_id, period)
);

create index if not exists charges_status_idx   on charges (status);
create index if not exists charges_resident_idx on charges (resident_id);

drop trigger if exists charges_touch_updated_at on charges;
create trigger charges_touch_updated_at
  before update on charges
  for each row execute function touch_updated_at();

comment on column charges.status is
  'pending_charge means a ticket is awaiting staff review. Set it when the ticket
   is created so the same debt cannot be called about twice while it waits.';

-- ---------------------------------------------------------------------------
-- payment_tickets
-- ---------------------------------------------------------------------------
-- Written by `open_payment_ticket`. This is the queue a member of staff works
-- through, and the only path by which a card is ever charged.
--
-- `authorization_captured` records whether the resident gave an unambiguous
-- spoken yes. When it is false there was no card on file and the office has to
-- contact them — the ticket is a task, not an approval.
--
-- `interaction_id` is not decoration. The recording reached through it IS the
-- authorisation, so a ticket with authorization_captured = true and no
-- interaction is not reviewable and must not be charged.

create table if not exists payment_tickets (
  id                     uuid primary key default gen_random_uuid(),
  charge_id              uuid not null references charges (id) on delete cascade,
  resident_id            uuid not null references residents (id) on delete cascade,
  interaction_id         uuid references interactions (id) on delete set null,
  authorization_captured boolean not null default false,
  amount                 numeric(10,2) not null check (amount > 0),
  period                 date not null,
  card_last4             text,
  status                 text not null default 'pending'
                           check (status in ('pending','approved','charged','rejected')),
  reviewed_by            text,
  reviewed_at            timestamptz,
  note                   text,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);

create index if not exists payment_tickets_status_idx  on payment_tickets (status, created_at desc);
create index if not exists payment_tickets_charge_idx  on payment_tickets (charge_id);

drop trigger if exists payment_tickets_touch_updated_at on payment_tickets;
create trigger payment_tickets_touch_updated_at
  before update on payment_tickets
  for each row execute function touch_updated_at();

-- A captured authorisation without the call it came from cannot be reviewed.
alter table payment_tickets drop constraint if exists payment_tickets_auth_needs_call;
alter table payment_tickets add  constraint payment_tickets_auth_needs_call
  check (authorization_captured = false or interaction_id is not null);

-- ---------------------------------------------------------------------------
-- payment_links
-- ---------------------------------------------------------------------------
-- Written by `send_payment_link`, which replaced `open_payment_ticket` on
-- 4 Aug 2026. The resident pays a link that OXS sends them; no card is
-- discussed on the call and nobody charges anything on their behalf.
--
-- Note what is absent and why:
--
--   no card_last4              — no card is involved
--   no authorization_captured  — there is nothing to authorise; consent happens
--                                when the resident taps the link, and their
--                                payment provider holds that record, not us
--   no auth_needs_call check   — payment_tickets needs one because the recording
--                                IS the authorisation. A link request is not an
--                                approval, so a row without an interaction is
--                                merely incomplete, not dangerous
--
-- `status` tracks our side only. `requested` means we asked; `sent` means OXS
-- confirmed it went. Nothing here can observe whether it was ever *paid* —
-- that is a read back from OXS, and any report that treats `sent` as a result
-- is counting intentions.

create table if not exists payment_links (
  id             uuid primary key default gen_random_uuid(),
  charge_id      uuid not null references charges (id) on delete cascade,
  resident_id    uuid not null references residents (id) on delete cascade,
  interaction_id uuid references interactions (id) on delete set null,
  amount         numeric(10,2) not null check (amount > 0),
  period         date not null,
  status         text not null default 'requested'
                   check (status in ('requested','sent','failed')),
  note           text,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

create index if not exists payment_links_status_idx on payment_links (status, created_at desc);
create index if not exists payment_links_charge_idx on payment_links (charge_id);

-- One link per call. Two rows for one conversation means the resident is sent
-- the same link twice, which reads as a system that has lost track of them.
create unique index if not exists payment_links_one_per_interaction
  on payment_links (interaction_id) where interaction_id is not null;

drop trigger if exists payment_links_touch_updated_at on payment_links;
create trigger payment_links_touch_updated_at
  before update on payment_links
  for each row execute function touch_updated_at();

-- ---------------------------------------------------------------------------
-- promises_to_pay
-- ---------------------------------------------------------------------------
-- `said` keeps the resident's own words. The agent is told to take the date in
-- their words and read it back, so what they actually said is worth more than
-- our parse of it when a promise is later disputed.

create table if not exists promises_to_pay (
  id             uuid primary key default gen_random_uuid(),
  charge_id      uuid not null references charges (id) on delete cascade,
  interaction_id uuid references interactions (id) on delete set null,
  promised_date  date,
  said           text not null,
  created_at     timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- payment_disputes
-- ---------------------------------------------------------------------------
-- The resident says they already paid. The agent never asks when or how, so
-- there is deliberately nowhere to record either.

create table if not exists payment_disputes (
  id             uuid primary key default gen_random_uuid(),
  charge_id      uuid not null references charges (id) on delete cascade,
  interaction_id uuid references interactions (id) on delete set null,
  receipt_requested boolean not null default true,
  resolved       boolean not null default false,
  resolved_note  text,
  created_at     timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- call_outcomes
-- ---------------------------------------------------------------------------
-- Written by `log_call_outcome` on every call without exception, including
-- voicemail and wrong party.
--
-- `posture_reached` is the highest posture the call got to, and it is the number
-- worth watching: hot is a floor, so the rate of hot calls is the honest measure
-- of whether the agent is damaging relationships. Nothing else in the system
-- records that.

create table if not exists call_outcomes (
  id              uuid primary key default gen_random_uuid(),
  charge_id       uuid references charges (id) on delete set null,
  resident_id     uuid references residents (id) on delete set null,
  interaction_id  uuid references interactions (id) on delete set null,
  outcome         text not null
                    check (outcome in ('authorized','promised','disputed','refused',
                                       'transferred','voicemail','wrong_party',
                                       'not_handed_over','no_answer','office_to_contact')),
  posture_reached text check (posture_reached in ('open','friction','hot')),
  transfer_reason text check (transfer_reason in ('hardship','dispute','distress',
                                                  'language','not_understood',
                                                  'caller_request')),
  standing_order_requested boolean not null default false,
  attempt         integer,
  created_at      timestamptz not null default now()
);

create index if not exists call_outcomes_created_idx on call_outcomes (created_at desc);
create index if not exists call_outcomes_outcome_idx on call_outcomes (outcome);

-- ---------------------------------------------------------------------------
-- v_debt_call_queue
-- ---------------------------------------------------------------------------
-- The variableValues for a debt call, ready to hand to Vapi.
--
-- This view IS the guard that was missing. The agent must never invent an amount
-- or a month, but an unsupplied template variable renders as an empty string
-- rather than failing — so the fix cannot live in the prompt. A row only appears
-- here when everything the call needs is present, which means a caller iterating
-- this view is structurally unable to place a call without them.
--
-- It also excludes the calls that should never be placed: apartments not handed
-- over, residents on the do-not-call list, and debts already waiting on staff
-- review.

create or replace view v_debt_call_queue as
select
  c.id                                   as charge_id,
  r.id                                   as resident_id,
  r.phone,
  split_part(r.full_name, ' ', 1)        as first_name,
  r.building,
  r.unit,
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
   by opening a ticket for the office instead of asking for authorisation.';

-- ---------------------------------------------------------------------------
-- Row-level security
-- ---------------------------------------------------------------------------
-- Edge Functions connect with the service role and bypass RLS. Everything else
-- reads only. RLS is on from the start so nothing is reachable with the anon key
-- by accident — which matters more here than in 001, because these tables say
-- who owes money.

alter table charges          enable row level security;
alter table payment_tickets  enable row level security;
alter table payment_links    enable row level security;
alter table promises_to_pay  enable row level security;
alter table payment_disputes enable row level security;
alter table call_outcomes    enable row level security;

drop policy if exists charges_read          on charges;
drop policy if exists payment_tickets_read  on payment_tickets;
drop policy if exists payment_links_read    on payment_links;
drop policy if exists promises_to_pay_read  on promises_to_pay;
drop policy if exists payment_disputes_read on payment_disputes;
drop policy if exists call_outcomes_read    on call_outcomes;

create policy charges_read          on charges          for select to authenticated using (true);
create policy payment_tickets_read  on payment_tickets  for select to authenticated using (true);
create policy payment_links_read    on payment_links    for select to authenticated using (true);
create policy promises_to_pay_read  on promises_to_pay  for select to authenticated using (true);
create policy payment_disputes_read on payment_disputes for select to authenticated using (true);
create policy call_outcomes_read    on call_outcomes    for select to authenticated using (true);
