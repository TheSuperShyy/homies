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
