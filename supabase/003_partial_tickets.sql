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
