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
