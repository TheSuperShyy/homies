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
