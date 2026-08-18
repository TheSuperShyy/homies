-- ===========================================================================
-- Homies — everything a new Supabase project needs, in one paste.
--
-- Open the new project, go to SQL Editor, paste this whole file, press Run.
-- It creates the schema and then records the migration ledger, so
-- scripts/supabase_migrate.py will not try to replay all seventeen files.
--
-- Creates tables, views, functions, triggers and RLS policies. NO DATA — the
-- rows are copied afterwards by scripts/supabase_move.py --apply.
--
-- Idempotent: running it twice is safe.
-- ===========================================================================

-- Homies — full schema for a fresh Supabase project.
--
-- GENERATED. Do not edit; edit the migrations in supabase/ and regenerate with
-- the snippet in docs/handover/supabase-migration.md.
--
-- Migrations 001..019 in order, with the two seed files left out on purpose: 002
-- and 005 create demo residents and demo charges, both purged from the live
-- database on 10 August. A fresh project should not be born holding rows
-- somebody deliberately deleted.
--
-- Creates tables, views, functions, triggers and RLS policies. No data.
-- Every migration is idempotent, so running this twice is safe.
--
-- Verified 13 Aug by running it against an empty schema on the live database
-- inside a transaction that was rolled back — which is how the missing RLS on
-- buildings/apartments was found. Re-verify the same way after regenerating.
--
-- AFTER running this, run supabase-ledger.sql in the same project, or
-- scripts/supabase_migrate.py will replay all of these against it.



-- ---------------------------------------------------------------------------
-- 001_slice_schema.sql
-- ---------------------------------------------------------------------------

-- Homies — Phase 1 vertical slice schema
-- Covers the three tables needed for `open_request` end to end.
-- Cut to the PRD v2 §11 shape so Phase 2 adds tables rather than rewriting these.
--
-- Run in the Supabase SQL editor, or: psql "$SUPABASE_DB_URL" -f 001_slice_schema.sql

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- residents
-- ---------------------------------------------------------------------------
-- `phone` is the primary lookup key for identify_resident: Vapi delivers caller
-- ID in E.164, so it is stored in E.164 and nothing else. Normalise on write,
-- never at query time — a mismatch here shows up as a low identification rate
-- with no visible error.

create table if not exists residents (
  id          uuid primary key default gen_random_uuid(),
  full_name   text not null,
  phone       text not null unique,            -- E.164, e.g. +972501234567
  building    text not null,
  unit        text not null,
  language    text not null default 'he',
  oxs_ref     text,                            -- id in OXS, from the nightly export
  created_at  timestamptz not null default now()
);

create index if not exists residents_phone_idx    on residents (phone);
create index if not exists residents_building_idx on residents (building, unit);

comment on column residents.phone is
  'E.164 only (+972...). Primary match key for identify_resident.';

-- ---------------------------------------------------------------------------
-- interactions
-- ---------------------------------------------------------------------------
-- One row per call or conversation. Created by the Vapi end-of-call webhook.
--
-- `tool_calls` and `latency_ms` are what make the demo legible: the CRM shows
-- not just that a request was created, but which tool created it and how fast
-- the agent responded. latency_ms is also the measurement for the <800ms target.

create table if not exists interactions (
  id               uuid primary key default gen_random_uuid(),
  external_call_id text unique,                -- Vapi call id
  channel          text not null default 'voice'
                     check (channel in ('voice','whatsapp','staff')),
  direction        text not null default 'inbound'
                     check (direction in ('inbound','outbound')),
  resident_id      uuid references residents (id) on delete set null,
  caller_phone     text,                       -- raw caller ID, kept even when unmatched
  transcript       text,
  summary          text,
  audio_url        text,
  disposition      text,
  duration_seconds integer,
  latency_ms       integer,                    -- voice-to-voice, vs the <800ms target
  tool_calls       jsonb not null default '[]'::jsonb,
  started_at       timestamptz,
  ended_at         timestamptz,
  created_at       timestamptz not null default now()
);

create index if not exists interactions_resident_idx on interactions (resident_id);
create index if not exists interactions_created_idx  on interactions (created_at desc);

comment on column interactions.caller_phone is
  'Raw caller ID. Retained even when identification fails — unmatched calls are the
   diagnostic signal for phone-normalisation and Hebrew ASR problems.';

-- ---------------------------------------------------------------------------
-- requests
-- ---------------------------------------------------------------------------
-- building/unit are denormalised on purpose: they record where the request was
-- about at the time it was opened, which stays correct if the resident moves.

create sequence if not exists request_reference_seq start 1001;

create table if not exists requests (
  id             uuid primary key default gen_random_uuid(),
  reference      text not null unique
                   default 'HM-' || to_char(now(), 'YYYY') || '-' ||
                           lpad(nextval('request_reference_seq')::text, 4, '0'),
  resident_id    uuid references residents (id) on delete set null,
  interaction_id uuid references interactions (id) on delete set null,
  type           text not null,                -- plumbing, electrical, cleaning, other
  description    text not null,
  building       text not null,
  unit           text,
  urgency        text not null default 'normal'
                   check (urgency in ('low','normal','high','emergency')),
  status         text not null default 'open'
                   check (status in ('open','in_progress','resolved','cancelled')),
  opened_via     text not null default 'voice'
                   check (opened_via in ('voice','whatsapp','staff')),
  oxs_ref        text,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

create index if not exists requests_resident_idx  on requests (resident_id);
create index if not exists requests_status_idx    on requests (status);
create index if not exists requests_created_idx   on requests (created_at desc);

comment on column requests.reference is
  'Human-quotable reference the agent reads back on the call, e.g. HM-2026-1001.';

-- keep updated_at honest
create or replace function touch_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists requests_touch_updated_at on requests;
create trigger requests_touch_updated_at
  before update on requests
  for each row execute function touch_updated_at();

-- ---------------------------------------------------------------------------
-- Row-level security
-- ---------------------------------------------------------------------------
-- n8n connects with the service role and bypasses RLS. The CRM connects as an
-- authenticated user and only reads. Department scoping (PRD v2 §13) lands in
-- Phase 6 — these policies are deliberately the simple version, but RLS is on
-- from day one so nothing is ever reachable with the anon key by accident.

alter table residents    enable row level security;
alter table requests     enable row level security;
alter table interactions enable row level security;

drop policy if exists residents_read    on residents;
drop policy if exists requests_read     on requests;
drop policy if exists interactions_read on interactions;

create policy residents_read    on residents    for select to authenticated using (true);
create policy requests_read     on requests     for select to authenticated using (true);
create policy interactions_read on interactions for select to authenticated using (true);


-- ---------------------------------------------------------------------------
-- 003_partial_tickets.sql
-- ---------------------------------------------------------------------------

-- Homies — migration 003: partial tickets
--
-- A call whose audio is unusable must still produce a row. Today it cannot:
-- type, description and building are all NOT NULL, so the exact call that most
-- needs a record — one where the building was inaudible — is the one the schema
-- refuses to store.
--
-- This relaxes those three columns and adds the status that marks such a row for
-- a human. See docs/features/07-partial-ticket/.
--
-- Run in the Supabase SQL editor, or:
--   psql "$SUPABASE_DB_URL" -f 003_partial_tickets.sql

-- ---------------------------------------------------------------------------
-- Relax the three NOT NULLs
-- ---------------------------------------------------------------------------
-- Complete tickets still populate all three; the constraint moves from the
-- database to open_request, which refuses to write a row missing any of them.
-- save_partial_request is the only caller allowed to omit them.

alter table requests alter column type        drop not null;
alter table requests alter column description drop not null;
alter table requests alter column building    drop not null;

comment on column requests.type is
  'Null only on needs_review rows. open_request never writes a null here.';
comment on column requests.description is
  'The caller''s own words, not a summary. Null only on needs_review rows.';
comment on column requests.building is
  'Null only on needs_review rows, where the audio was too poor to capture it.';

-- ---------------------------------------------------------------------------
-- Add the needs_review status
-- ---------------------------------------------------------------------------
-- A workflow state, not a flag: it is assigned, worked, and left. A separate
-- boolean would have to be reconciled with status on every query.

alter table requests drop constraint if exists requests_status_check;
alter table requests add constraint requests_status_check
  check (status in ('open','in_progress','resolved','cancelled','needs_review'));

comment on column requests.status is
  'needs_review = the agent could not complete intake. Captured slots are
   trustworthy; empty ones were never captured, never guessed.';

-- ---------------------------------------------------------------------------
-- Find the review queue quickly
-- ---------------------------------------------------------------------------
-- Partial rows are a small fraction of the table and are always queried on
-- their own, so a partial index stays tiny regardless of how the table grows.

create index if not exists requests_needs_review_idx
  on requests (created_at desc)
  where status = 'needs_review';

-- ---------------------------------------------------------------------------
-- Guard: a complete ticket must still be complete
-- ---------------------------------------------------------------------------
-- Dropping three NOT NULLs would otherwise let a bug in open_request write a
-- half-empty row silently. This keeps the original guarantee everywhere except
-- the one status that is allowed to be incomplete.

alter table requests drop constraint if exists requests_complete_unless_review;
alter table requests add constraint requests_complete_unless_review
  check (
    status = 'needs_review'
    or (type is not null and description is not null and building is not null)
  );


-- ---------------------------------------------------------------------------
-- 004_debt_schema.sql
-- ---------------------------------------------------------------------------

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


-- ---------------------------------------------------------------------------
-- 006_debt_tool_support.sql
-- ---------------------------------------------------------------------------

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


-- ---------------------------------------------------------------------------
-- 007_import_source.sql
-- ---------------------------------------------------------------------------

-- Homies — where a row came from
--
-- Added 8 Aug 2026, when the first real resident data was imported into a table
-- that already held ten fictional residents from 002_slice_seed.sql.
--
-- The reason this is a column and not a convention: `residents` is the table the
-- outbound debt agent reads to decide who to call. Once real phone numbers and
-- seed phone numbers sit in it together with nothing to tell them apart, the
-- only thing standing between a test run and calling a real person about a real
-- debt is somebody remembering which is which. `oxs_ref` cannot do this job —
-- it holds the id in OXS, and a CSV export does not carry one.
--
-- 'seed'   fictional, safe to call, safe to delete
-- 'oxs'    came from OXS, whether by export file or later by API. Real people.
-- 'agent'  created by a bot or by staff during normal operation.

alter table residents add column if not exists source text not null default 'seed';
alter table charges   add column if not exists source text not null default 'seed';

alter table residents drop constraint if exists residents_source_check;
alter table residents add  constraint residents_source_check
  check (source in ('seed', 'oxs', 'agent'));

alter table charges drop constraint if exists charges_source_check;
alter table charges add  constraint charges_source_check
  check (source in ('seed', 'oxs', 'agent'));

create index if not exists residents_source_idx on residents (source);
create index if not exists charges_source_idx   on charges (source);

comment on column residents.source is
  'seed = fictional test data. oxs = a real person imported from OXS. Any
   campaign, test run or destructive query must filter on this.';

-- OXS data is a copy and is never written back: the client rule of 8 Aug is that
-- nothing this system builds writes to OXS, including creating service requests.
-- So an `oxs` row is authoritative upstream and disposable here — it can always
-- be re-imported, and must never be the only place a fact lives.


-- ---------------------------------------------------------------------------
-- 008_messages.sql
-- ---------------------------------------------------------------------------

-- 008 — every message, kept.
--
-- Until now a WhatsApp conversation lived in one place: the n8n memory node.
-- That is context for the model and was never a log. It is capped at 30
-- messages, it cannot be queried, it does not survive an n8n restore, and it is
-- keyed on a phone number with no link to the ticket the conversation produced.
--
-- `interactions` already holds one row per conversation, with a `transcript`
-- column that voice fills from the end-of-call report. Chat has no equivalent
-- moment — there is no "end" of a WhatsApp thread — so the transcript has to be
-- accumulated a message at a time. Hence a child table rather than a bigger
-- text column: an append is cheap, a read-modify-write of a growing string
-- under two concurrent messages loses one of them.
--
-- Deliberately NOT modelled on Chatwoot's schema. Chatwoot takes the number
-- soon and its own Postgres becomes the operational store; this table is the
-- analytics copy the dashboard reads, and it must survive Chatwoot being
-- replaced, upgraded or restored. `source` records which system fed it so the
-- migration can be verified rather than assumed.

create table if not exists messages (
  id             uuid primary key default gen_random_uuid(),

  -- The conversation this belongs to. Nullable because a message can arrive
  -- before anything has created the interaction row — a greeting that never
  -- becomes a ticket has no tool call, and therefore no interaction.
  interaction_id uuid references interactions (id) on delete cascade,

  -- Kept alongside interaction_id, not instead of it. The phone is the only
  -- identifier present on every single inbound message, so a conversation can
  -- always be reconstructed even when the link above is null.
  phone          text not null,
  resident_id    uuid references residents (id) on delete set null,

  direction      text not null check (direction in ('inbound','outbound')),

  -- 'bot' covers anything the model or the workflow sent, including the canned
  -- lines. 'agent' is a human in Chatwoot. The distinction is the whole point
  -- of the per-conversation AI toggle, and it has to be recorded from the first
  -- message or the history is useless for measuring it.
  sender         text not null check (sender in ('resident','bot','agent')),

  body           text,

  -- 'text', 'interactive' (a menu tap), 'image', 'audio', 'location', 'sticker'.
  -- Free text rather than a check constraint: WhatsApp adds message types on
  -- Meta's schedule, and a constraint here would turn a new type into a lost
  -- message instead of an unfamiliar row.
  message_type   text not null default 'text',

  -- Meta's wamid, or Chatwoot's message id. Unique so a webhook retry cannot
  -- write the same message twice — the same reasoning as the dedupe in Sort,
  -- enforced by the database rather than by workflow static data that does not
  -- survive a restore.
  external_id    text unique,

  -- Which system wrote this row: 'n8n' today, 'chatwoot' after the number
  -- moves. Without it, a gap in the history is indistinguishable from a quiet
  -- period.
  source         text not null default 'n8n',

  -- The language the reply was sent in, for the messages we sent. Decided in
  -- code by Sort; recorded here so "the bot answered in the wrong language" is
  -- a query rather than a screenshot.
  lang           text,

  created_at     timestamptz not null default now()
);

create index if not exists messages_phone_idx       on messages (phone, created_at desc);
create index if not exists messages_interaction_idx on messages (interaction_id);
create index if not exists messages_created_idx     on messages (created_at desc);

comment on table messages is
  'One row per WhatsApp message, inbound and outbound. The durable chat log
   required by PRD item 3; the n8n memory node is context for the model and is
   not a record. Written by n8n today and by Chatwoot once it owns the number —
   see the `source` column.';

comment on column messages.external_id is
  'Meta wamid or Chatwoot message id. UNIQUE: a retried webhook must not be able
   to append the same message twice.';

-- ---------------------------------------------------------------------------
-- A conversation, as the dashboard wants to read it
-- ---------------------------------------------------------------------------
-- One row per phone: when it started, when it last moved, how many messages,
-- and the last thing said. Built as a view so the dashboard cannot drift from
-- the definition, and so "conversation" means the same thing in every query.
create or replace view v_conversations as
select
  m.phone,
  r.id                                    as resident_id,
  r.full_name,
  r.building,
  r.unit,
  min(m.created_at)                       as started_at,
  max(m.created_at)                       as last_message_at,
  count(*)                                as message_count,
  count(*) filter (where m.direction = 'inbound')  as from_resident,
  count(*) filter (where m.sender = 'agent')       as from_agent,
  -- Whether a human has ever spoken in this thread. The per-conversation AI
  -- toggle is measured from this, so it is defined once, here.
  bool_or(m.sender = 'agent')             as touched_by_human,
  max(m.lang) filter (where m.direction = 'outbound') as lang,
  (array_agg(m.body order by m.created_at desc)
     filter (where m.body is not null))[1]         as last_message
from messages m
left join residents r on r.phone = m.phone
group by m.phone, r.id, r.full_name, r.building, r.unit;

comment on view v_conversations is
  'One row per WhatsApp thread. Joined to residents on phone, which is a join
   key and never a dial target — see the no-phone-numbers rule.';


-- ---------------------------------------------------------------------------
-- 009_dashboard_access.sql
-- ---------------------------------------------------------------------------

-- 009 — row-level security for the dashboard, and a leak closed.
--
-- THE LEAK. `messages` shipped in 008 without RLS enabled. Every other table in
-- this database has it on, so the anon key reads nothing from them — checked,
-- zero rows. `messages` returned real rows to the anon key, and the anon key is
-- PUBLIC by design: it goes in the browser bundle, and anyone with it and the
-- project URL could read every resident's WhatsApp conversation.
--
-- It existed for about an hour, on a table containing four test conversations
-- and no real resident. That is luck rather than design. RLS is not something a
-- new table opts into; it is something a new table must not be able to skip,
-- which is what the check at the bottom of this file is for.
--
-- THE MODEL. The dashboard authenticates staff with Supabase Auth and talks to
-- PostgREST with the ANON key plus the user's session — never the service role
-- key, which must not reach a browser under any circumstances. So every table
-- the dashboard reads needs an explicit policy for the `authenticated` role.
--
-- Read-only, all of it. The dashboard shows what happened; nothing in it edits
-- a ticket, and a policy that does not exist cannot be exploited. Writes come
-- from the Edge Function and n8n, which use the service role key and bypass RLS
-- by design.

-- ---------------------------------------------------------------------------
-- The leak
-- ---------------------------------------------------------------------------
alter table messages enable row level security;

-- ---------------------------------------------------------------------------
-- Read access for signed-in staff
-- ---------------------------------------------------------------------------
-- `to authenticated` and not `to public`: `public` would include `anon`, which
-- is the mistake this migration exists to fix.
do $$
declare t text;
begin
  foreach t in array array[
    'residents', 'requests', 'interactions', 'messages',
    'charges', 'call_outcomes', 'payment_links', 'payment_tickets',
    'payment_disputes', 'promises_to_pay'
  ] loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists staff_read on %I', t);
    execute format(
      'create policy staff_read on %I for select to authenticated using (true)', t);
  end loop;
end $$;

comment on policy staff_read on requests is
  'Any signed-in staff member reads everything. Department scoping (PRD §10) is
   deliberately NOT here yet: there is no staff table to scope against, and a
   policy that looks like access control while enforcing nothing is worse than
   an honest one.';

-- ---------------------------------------------------------------------------
-- Views must not be a way around the policies above
-- ---------------------------------------------------------------------------
-- A view runs with its owner's rights by default, so it reads through RLS as
-- the owner and hands the rows out regardless of who asked. `v_conversations`
-- was doing exactly that — it returned rows to the anon key even while its
-- underlying tables were locked. security_invoker makes the caller's policies
-- apply, which is the only setting that makes a view safe to expose.
alter view v_conversations set (security_invoker = on);
alter view v_debt_call_queue set (security_invoker = on);
alter view v_pending_payment_tickets set (security_invoker = on);

-- ---------------------------------------------------------------------------
-- So this cannot happen again
-- ---------------------------------------------------------------------------
-- A table added without RLS is invisible until someone thinks to check with the
-- anon key, which is how 008 got through. This makes it loud: any future
-- migration that forgets `enable row level security` fails here rather than
-- shipping a readable table.
do $$
declare unguarded text;
begin
  select string_agg(c.relname, ', ')
    into unguarded
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public'
    and c.relkind = 'r'
    and not c.relrowsecurity
    and c.relname <> 'schema_migrations';

  if unguarded is not null then
    raise exception
      'These tables have no row-level security and the anon key can read them: %',
      unguarded;
  end if;
end $$;


-- ---------------------------------------------------------------------------
-- 010_open_dashboard.sql
-- ---------------------------------------------------------------------------

-- 010 — open the dashboard: anon read on everything the dashboard shows.
--
-- Demo-mode decision, 9 August 2026: no login screen. The middleware redirect
-- is gone from dashboard/middleware.ts, and this migration gives the anon role
-- the same read-only view that `authenticated` got in 009.
--
-- KNOW WHAT THIS TRADES AWAY. The anon key ships in the browser bundle and is
-- public by design. With these policies, anyone holding the project URL and
-- that key reads every table below — residents, conversations, calls — without
-- signing in. Acceptable while the data is demo/test data and the dashboard is
-- a demo. It is NOT acceptable once real residents are in these tables.
--
-- TO RE-LOCK (before pilot, or the moment real data lands):
--   drop the anon_read policies (loop below with drop instead of create),
--   restore the middleware redirect, and staff sign in again. 009's
--   authenticated policies are untouched by this file, so re-locking is a
--   deletion, not a rebuild.

do $$
declare t text;
begin
  foreach t in array array[
    'residents', 'requests', 'interactions', 'messages',
    'charges', 'call_outcomes', 'payment_links', 'payment_tickets',
    'payment_disputes', 'promises_to_pay'
  ] loop
    execute format('drop policy if exists anon_read on %I', t);
    execute format(
      'create policy anon_read on %I for select to anon using (true)', t);
  end loop;
end $$;

comment on policy anon_read on requests is
  'Demo mode: the dashboard has no login, so the anon role reads what
   authenticated reads. Drop every anon_read policy before real resident data
   arrives — see the header of this migration.';


-- ---------------------------------------------------------------------------
-- 011_status_editable.sql
-- ---------------------------------------------------------------------------

-- 011 — the dashboard can change a ticket's status. Nothing else.
--
-- Same demo-mode trade as 010, and the same expiry date. The dashboard has no
-- login, so the write goes through the anon role — which means anyone holding
-- the project URL and the anon key can change ticket statuses. Acceptable for
-- demo data. NOT acceptable once real tickets are here.
--
-- The blast radius is one column by construction, not by policy prose:
-- Postgres column-level grants mean the anon role can update `status` and
-- nothing else — not the description, not the building, not the reference.
-- A request that touches any other column fails at the grant, before RLS is
-- even consulted. The check constraint on status rejects invented values.
--
-- TO RE-LOCK (with the 010 re-lock, before pilot or real data):
--   drop policy anon_update_status on requests;
--   revoke update on requests from anon;

revoke update on requests from anon;
grant update (status) on requests to anon;

drop policy if exists anon_update_status on requests;
create policy anon_update_status on requests
  for update to anon using (true) with check (true);

comment on policy anon_update_status on requests is
  'Demo mode: the no-login dashboard edits ticket status through the anon
   role. Column-level grant restricts the write to status alone. Drop this
   policy and revoke the grant before real ticket data arrives — see the
   header of 011.';


-- ---------------------------------------------------------------------------
-- 012_charge_apartment.sql
-- ---------------------------------------------------------------------------

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


-- ---------------------------------------------------------------------------
-- 013_call_per_resident.sql
-- ---------------------------------------------------------------------------

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


-- ---------------------------------------------------------------------------
-- 014_oxs_service_calls.sql
-- ---------------------------------------------------------------------------

-- 014 — Homies' own maintenance calls, and their category vocabulary
--
-- Residents have been reporting faults through OXS's resident app since
-- February. 33 are open. Our agents could not see any of them, so "what is
-- happening with my request" got a different answer depending on which door the
-- resident came through — ours or theirs.
--
-- This makes room for their tickets in `requests` and replaces our invented
-- fault list with theirs. Asked for on 12 Aug: "import the tickets from their
-- system and their category, we want to match their format."

-- ---------------------------------------------------------------------------
-- 1. A fourth way a ticket can arrive
-- ---------------------------------------------------------------------------
-- 'oxs' is not a channel a resident chose, it is a channel we import from. It
-- matters on screen: staff must be able to see at a glance that a row came from
-- their system rather than from one of our agents, because we cannot close it.

alter table requests drop constraint if exists requests_opened_via_check;
alter table requests add constraint requests_opened_via_check
  check (opened_via in ('voice','whatsapp','staff','oxs'));

comment on column requests.opened_via is
  'oxs = imported from their resident app. Read-only on our side: OXS exposes
   no write endpoint, so nothing we do can change it there.';

-- ---------------------------------------------------------------------------
-- 2. Importing twice must not double the list
-- ---------------------------------------------------------------------------
-- The sync re-reads every open call on every run. Without this the second run
-- is 33 more rows and the dashboard count silently doubles.
--
-- Scoped to imported rows on purpose. `oxs_ref` is not exclusively an OXS id:
-- save_partial_request writes the sentinel 'partial:cut_off' into it, and every
-- abandoned call carries the same one. A plain unique index on the column fails
-- on the second partial ticket, which is how this was found.

create unique index if not exists requests_oxs_ref_unique
  on requests (oxs_ref) where oxs_ref is not null and opened_via = 'oxs';

-- ---------------------------------------------------------------------------
-- 3. Their categories, not ours
-- ---------------------------------------------------------------------------
-- Ours were invented on day one: plumbing, electrical, cleaning, other, plus
-- two more the WhatsApp bot added later. Theirs are the twelve their dispatchers
-- actually use, and they are what appears on the screen a staff member works
-- from. Where the two disagree, theirs wins.
--
-- `type` keeps a stable slug because code compares it; `category_he` holds
-- their exact wording because that is what a human reads; `oxs_category_id`
-- survives a rename on their side, which a Hebrew label would not.

alter table requests add column if not exists category_he     text;
alter table requests add column if not exists oxs_category_id text;

comment on column requests.type is
  'One slug per OXS facility category. Ours until 12 Aug; theirs from then on.';
comment on column requests.category_he is
  'The category exactly as OXS words it. What staff see. Null on rows opened
   before the vocabularies were aligned.';

-- Existing rows, mapped rather than deleted. `structural` has no equivalent on
-- their side and becomes maintenance (אחזקה), which is where their dispatchers
-- put the same kind of job.
update requests set type = 'maintenance' where type = 'structural';
update requests set type = 'other'       where type = 'security';

update requests set category_he = case type
  when 'plumbing'     then 'אינסטלציה'
  when 'electrical'   then 'חשמל'
  when 'lighting'     then 'תאורה'
  when 'elevator'     then 'מעלית'
  when 'cleaning'     then 'ניקיון'
  when 'gardening'    then 'גינון'
  when 'pest_control' then 'הדברה'
  when 'locksmith'    then 'מנעולן'
  when 'fire_safety'  then 'כיבוי אש'
  when 'maintenance'  then 'אחזקה'
  when 'other'        then 'אחר'
end
where category_he is null and type is not null;

-- The constraint goes on AFTER the mapping, so a stale value fails the
-- migration rather than being written tomorrow by a tool nobody updated.
-- Null stays legal: a needs_review row is allowed to be incomplete (003).
alter table requests drop constraint if exists requests_type_check;
alter table requests add constraint requests_type_check
  check (type is null or type in (
    'plumbing','electrical','lighting','elevator','cleaning','gardening',
    'pest_control','locksmith','fire_safety','maintenance','other'));

-- ---------------------------------------------------------------------------
-- 4. Their fields that have nowhere else to go
-- ---------------------------------------------------------------------------
-- Only what a person or an agent would use. Their internal ids, icons,
-- reminders and empty handling arrays are left where they are.

alter table requests add column if not exists reported_by_name  text;
alter table requests add column if not exists reported_by_phone text;
alter table requests add column if not exists source_platform   text;
alter table requests add column if not exists image_count       int not null default 0;
alter table requests add column if not exists oxs_created_at    timestamptz;

comment on column requests.reported_by_phone is
  'The number OXS recorded for whoever reported it. Same shape as
   residents.phone, which is how an imported ticket finds its resident.';
comment on column requests.source_platform is
  'Their wording: resident app or web. Only set on imported rows.';
comment on column requests.oxs_created_at is
  'When THEY logged it. created_at is when we imported it, and the two are
   months apart on the backlog — the dashboard must sort on this one.';

create index if not exists requests_oxs_created_idx
  on requests (oxs_created_at desc) where oxs_created_at is not null;


-- ---------------------------------------------------------------------------
-- 015_category_label.sql
-- ---------------------------------------------------------------------------

-- 015 — one Hebrew label per category, whoever opened the ticket
--
-- 014 gave imported rows `category_he`, taken verbatim from OXS. A ticket our
-- own agents open has the slug and no label, so a dashboard listing both looks
-- like two systems bolted together: their rows say תאורה and ours say nothing.
--
-- A trigger rather than a change to open_request, because the label is a fact
-- about the slug and not about the caller. Filling it in the tool would mean
-- every future writer has to remember to do the same, and one of them will not.

create or replace function fill_category_he() returns trigger as $$
begin
  -- Only when it is missing. An imported row already carries THEIR wording,
  -- and if they ever rename a category theirs must win over this table.
  if new.category_he is null and new.type is not null then
    new.category_he := case new.type
      when 'plumbing'     then 'אינסטלציה'
      when 'electrical'   then 'חשמל'
      when 'lighting'     then 'תאורה'
      when 'elevator'     then 'מעלית'
      when 'cleaning'     then 'ניקיון'
      when 'gardening'    then 'גינון'
      when 'pest_control' then 'הדברה'
      when 'locksmith'    then 'מנעולן'
      when 'fire_safety'  then 'כיבוי אש'
      when 'maintenance'  then 'אחזקה'
      when 'other'        then 'אחר'
    end;
  end if;
  return new;
end;
$$ language plpgsql;

drop trigger if exists requests_fill_category_he on requests;
create trigger requests_fill_category_he
  before insert or update of type, category_he on requests
  for each row execute function fill_category_he();

-- Rows written between 014 and this migration.
update requests set category_he = null where false;   -- no-op, forces the trigger path
update requests set type = type where category_he is null and type is not null;

comment on function fill_category_he is
  'Keeps requests.category_he in step with requests.type. OXS rows arrive with
   their own wording and are left alone; ours are filled from the slug.';


-- ---------------------------------------------------------------------------
-- 016_buildings.sql
-- ---------------------------------------------------------------------------

-- 016 — the canonical building and apartment list
--
-- Asked for 13 Aug: when a resident reports a fault the bot should ask which
-- building and which apartment, and say so when the answer does not exist.
-- Until now there was nothing to check an answer against. `residents.building`
-- is a string composed at import time and stored — good enough to file a
-- ticket, useless for verifying one. A caller who said a street we do not
-- manage, or apartment 40 in a building with 25 flats, was recorded verbatim
-- and the ticket went to a person to puzzle out.
--
-- Apartments were never fetched at all. They are also the only way to know a
-- flat exists when nobody lives in it or nobody has a phone: a flat with no
-- contact details has no `residents` row, so `residents` cannot answer the
-- question even in principle.
--
-- WHAT THE DATA IS (measured 13 Aug, all 173 active buildings)
-- Street + number is unique across the whole portfolio: no duplicate
-- addresses, and no street+number appearing in two cities. So "הרצל 14"
-- identifies a building on its own and the agent never has to ask which city
-- — worth a turn on every single call. Three street names do span two cities
-- (גולומב, החשמונאים, סוקולוב) but never at the same house number.
--
-- That uniqueness is a property of today's data and not a promise, so the
-- matcher does not assume it silently: `oxs_buildings_sync.py` re-checks it on
-- every run and refuses to write if it ever stops holding.
--
-- WHY THE OXS ID IS THE PRIMARY KEY
-- Every OXS sub-resource is keyed on it, and this table is a mirror of theirs.
-- A synthetic key would mean maintaining a mapping to the only id the source
-- system knows, for no gain — nothing here is ever created locally. OXS stays
-- read-only: this is import-only, in one direction, forever.
--
-- Idempotent. Safe to re-run.
--
-- No `begin`/`commit` here. supabase_migrate.py runs each file inside its own
-- transaction, so an explicit one commits the runner's out from under it.

create table if not exists buildings (
  id          text primary key,           -- the OXS `_id`
  street      text not null,
  -- The same street with quote marks stripped and whitespace collapsed, for
  -- matching only — never for display. ז'בוטינסקי arrives typed with U+05F3,
  -- with an ASCII apostrophe, and with nothing at all, from the same person on
  -- different days, and none of those are a different street.
  street_norm text not null,
  number      text not null,
  city        text not null,
  entrance    text,                       -- two buildings have one; see below
  -- Exactly the string `residents.building` already holds, composed the same
  -- way by the importer. A column rather than a recomposition at read time, so
  -- the two can be joined — and so drift between them shows up in one query
  -- instead of as a lookup that mysteriously stops matching.
  address     text not null,
  active      boolean not null default true,
  synced_at   timestamptz not null default now()
);

comment on table buildings is
  'Mirror of OXS /buildings. Import-only: OXS is read-only, forever. Refreshed
   by scripts/oxs_buildings_sync.py.';
comment on column buildings.street_norm is
  'Quote-stripped street, for matching what a caller says. Never displayed.';
comment on column buildings.active is
  'false = OXS `disable`. Carried rather than dropped: a building Homies
   stopped managing still appears on old tickets and old debt, and a row saying
   so explains that, where a missing row reads as an import bug. Disabled
   buildings deliberately have no apartments imported.';

create index if not exists buildings_number_idx on buildings (number);
create index if not exists buildings_street_norm_idx on buildings (street_norm);
create index if not exists buildings_address_idx on buildings (address);
-- The matcher's hot path: narrow by house number, then compare street. The
-- house number is the one token a caller always says and a transcriber rarely
-- mangles beyond recognition.
create index if not exists buildings_match_idx on buildings (number, street_norm)
  where active;

create table if not exists apartments (
  id          text primary key,           -- the OXS `_id`
  building_id text not null references buildings (id) on delete cascade,
  number      text not null,              -- usually '1' up; sometimes a label
  order_index int,
  synced_at   timestamptz not null default now(),
  -- NOTE: this constraint is WRONG and 017 drops it. Left here rather than
  -- edited out because 016 is already applied and a migration that has run is
  -- not rewritten. The assumption — no two flats share a number in one
  -- building — came from a four-building sample and died on the first full
  -- import: זבולון 17 has two units both called חנות. See 017.
  unique (building_id, number)
);

comment on table apartments is
  'Mirror of OXS /buildings/:id/apartments. The only source that knows a flat
   exists when nobody lives in it or nobody has a phone — such a flat has no
   residents row at all.';

create index if not exists apartments_building_idx on apartments (building_id);

-- ---------------------------------------------------------------------------
-- What a resident actually gets asked, in one place
-- ---------------------------------------------------------------------------
-- The bot asks for a building and an apartment and has to answer three
-- questions about the reply: is this a building we manage, does that flat
-- exist in it, and if not, what can we honestly say instead. The third is why
-- the flat range is here: "that building has apartments 1 to 25" is a useful
-- sentence and "not found" is not.
--
-- A view rather than a query in the Edge Function, because the dashboard wants
-- the same counts and two copies of a definition drift.
create or replace view v_buildings as
select
  b.id,
  b.address,
  b.street,
  b.street_norm,
  b.number,
  b.city,
  b.entrance,
  b.active,
  count(a.id)                              as apartment_count,
  min(nullif(a.order_index, 0))            as first_unit,
  max(a.order_index)                       as last_unit,
  -- Residents on file, which is NOT the apartment count: a flat with no phone
  -- has no resident row. The gap between these two columns is exactly the
  -- population the debt work keeps tripping over.
  (select count(*) from residents r where r.building = b.address) as residents_on_file
from buildings b
left join apartments a on a.building_id = b.id
group by b.id;

comment on view v_buildings is
  'One row per building with its flat range and how many residents we hold.
   apartment_count > residents_on_file is normal and expected: a flat with no
   phone number on file has no residents row.';


-- ---------------------------------------------------------------------------
-- 017_apartment_labels.sql
-- ---------------------------------------------------------------------------

-- 017 — an apartment "number" is not always a number, and is not unique
--
-- 016 put `unique (building_id, number)` on `apartments`, on the assumption —
-- taken from a four-building sample where every flat was 1..N — that a building
-- never has two flats with the same number. The full import disproved it on the
-- first run, which is the entire argument for importing before designing.
--
-- WHAT THE REAL DATA HAS, across 4,092 flats in 173 buildings:
--   * 138 numbers that are not numbers. Shops (חנות), commercial units
--     (מסחר 1..4), storage (מחסן), parking bays (חניה 43), committee flats
--     (דירת ועד, חברי וועד), a company name, and one flat called 1.5.
--   * 2 that are blank.
--   * זבולון 17, תל אביב — two separate units, both called חנות. Not a
--     duplicate row: two shops on the ground floor, neither of them numbered.
--
-- So the constraint refused a legitimate building. It was also redundant: `id`
-- is the OXS `_id` and is already the primary key, so a double import cannot
-- create a second row for one flat — which is the only thing the unique index
-- was ever protecting against.
--
-- What replaces it is the same pair as a plain index, because the lookup it
-- supports — does flat 12 exist in this building — is real and frequent. Only
-- the uniqueness was wrong.
--
-- Idempotent. Safe to re-run.

alter table apartments drop constraint if exists apartments_building_id_number_key;

create index if not exists apartments_building_number_idx
  on apartments (building_id, number);

comment on column apartments.number is
  'As OXS holds it, which is USUALLY a sequential integer and sometimes a label:
   חנות, מסחר 2, מחסן, חניה 43, דירת ועד. Not unique within a building — one
   building has two units both called חנות. Never parse it as a number; the
   spoken flat range in verify_address is computed from the numeric ones only.';


-- ---------------------------------------------------------------------------
-- 018_reporter_unit.sql
-- ---------------------------------------------------------------------------

-- 018 — who reported it, as distinct from where it broke
--
-- Asked for 13 Aug: the bot should answer a reported fault with one human
-- message — "ok, that's annoying. which building and apartment do you live in?
-- I'll open a call for you" — and ask for the apartment EVERY time, including
-- for a fault in the lobby.
--
-- That looked at first like it contradicted the rule this project spent 8 Aug
-- learning: never ask "which apartment?" about a stuck lift, because a lift
-- does not belong to one. It does not contradict it. The two questions are
-- different questions wearing the same words:
--
--     requests.unit          WHERE THE FAULT IS.  null for common property.
--     requests.reported_unit WHERE THE PERSON LIVES. always, once verified.
--
-- A lobby leak reported by flat 3 is `unit = null, reported_unit = '3'`. Every
-- query that finds common-area faults with `unit is null` keeps working, the
-- duplicate guard still groups two reports of one lobby leak together — and we
-- finally know who told us, which is the thing that was missing. Before this,
-- a WhatsApp ticket had no resident attached at all: there is no caller ID on
-- chat and nothing ever looked the sender up.
--
-- `resident_id` is filled from the same pair when a resident actually exists at
-- that flat. Often one does not — a flat with no phone number on file has no
-- `residents` row at all, which is exactly why `reported_unit` is a column of
-- its own and not a lookup. Knowing "flat 3 of יואב 14 reported this" is
-- useful even when we hold nobody there.
--
-- Idempotent. Safe to re-run.

alter table requests add column if not exists reported_unit text;

comment on column requests.unit is
  'Where the FAULT is. NULL for common property — a lift, a lobby, a stairwell
   belongs to no apartment. Do not fill this with the reporter''s flat; that is
   reported_unit.';

comment on column requests.reported_unit is
  'The apartment the person reporting LIVES in, verified against `apartments`
   before the ticket was opened. Set on every chat ticket including common-area
   ones. Distinct from `unit`, which is where the fault is.';

-- Finding every ticket a flat has ever raised is the query a person actually
-- runs — "this flat calls every week" — and it is not answerable from `unit`.
create index if not exists requests_reported_by_idx
  on requests (building, reported_unit);


-- ---------------------------------------------------------------------------
-- 019_buildings_rls.sql
-- ---------------------------------------------------------------------------

-- 019 — row-level security on buildings and apartments
--
-- 016 created both tables and did not enable RLS, so from the moment it was
-- applied the **anon key could read the whole portfolio** — 173 addresses and
-- 4,092 apartments — and that key ships in the dashboard's browser bundle and
-- is public by design.
--
-- This is exactly the failure 009 was written to prevent. Its guard raises if
-- any table in `public` lacks RLS, and it did not fire, because a migration
-- only ever runs once: 009 ran on 9 August and 016 arrived on 13 August, four
-- days after the check had had its only chance to look. A one-shot assertion
-- cannot guard tables that do not exist yet.
--
-- So two things change. This file turns RLS on, and `scripts/supabase_migrate.py`
-- now runs the same assertion after **every** run, where it can see whatever
-- was just applied. The check in 009 stays as documentation of the rule.
--
-- NO ANON POLICY, deliberately, which is not what 010 did for the other tables.
-- 010 opened everything to anon for the no-login demo dashboard, and it says in
-- its own header that this is a trade to be reversed before real data arrives.
-- Nothing in the dashboard reads buildings or apartments today, so there is no
-- feature to weigh against it, and this is a client's commercial portfolio —
-- every building they manage, with its unit count. RLS on and no policy means
-- anon reads nothing.
--
-- The Edge Function is unaffected: `debt-tools` connects with
-- SUPABASE_SERVICE_ROLE_KEY, and the service role bypasses RLS. `verify_address`
-- keeps working.
--
-- Idempotent. Safe to re-run.

alter table buildings  enable row level security;
alter table apartments enable row level security;

-- Said out loud rather than left implicit, so the next person does not "fix"
-- the missing policy by adding one.
comment on table buildings is
  'Mirror of OXS /buildings. Import-only: OXS is read-only, forever. Refreshed
   by scripts/oxs_buildings_sync.py. RLS is ON WITH NO POLICY on purpose — only
   the service role reads this. It is the client''s whole portfolio, and no
   dashboard page needs it. If a page ever does, add a policy for the role that
   page authenticates as, not for anon.';

comment on table apartments is
  'Mirror of OXS /buildings/:id/apartments. The only source that knows a flat
   exists when nobody lives in it or nobody has a phone. RLS is ON WITH NO
   POLICY, same reasoning as buildings.';


-- ---------------------------------------------------------------------------
-- The migration ledger
-- ---------------------------------------------------------------------------

create table if not exists schema_migrations (
    filename    text primary key,
    applied_at  timestamptz not null default now()
);

insert into schema_migrations (filename) values
    ('001_slice_schema.sql'),
    ('003_partial_tickets.sql'),
    ('004_debt_schema.sql'),
    ('006_debt_tool_support.sql'),
    ('007_import_source.sql'),
    ('008_messages.sql'),
    ('009_dashboard_access.sql'),
    ('010_open_dashboard.sql'),
    ('011_status_editable.sql'),
    ('012_charge_apartment.sql'),
    ('013_call_per_resident.sql'),
    ('014_oxs_service_calls.sql'),
    ('015_category_label.sql'),
    ('016_buildings.sql'),
    ('017_apartment_labels.sql'),
    ('018_reporter_unit.sql'),
    ('019_buildings_rls.sql')
on conflict do nothing;
