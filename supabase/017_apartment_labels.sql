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
