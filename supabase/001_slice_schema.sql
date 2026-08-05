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
