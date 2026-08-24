-- ---------------------------------------------------------------------------
-- 022 — a ticket carries what is happening to it, and when we last saw it
-- ---------------------------------------------------------------------------
-- `requests.status` has said `open` on all 69 imported tickets since the first
-- import, and that is not a bug in our importer: OXS's own `status` field reads
-- `{"label":"פתוחה","status":"open"}` on every service call it serves, verified
-- 24 Aug across all 35 live calls spanning 10 Feb to that morning. The field
-- exists and is a constant.
--
-- The progress is somewhere else. `treatmentLog` is a list of Hebrew notes —
-- "הועבר לאלון שערים", "בטיפול דוד", "ממתינים לדוד לטיפול בתקלה" — filled on 13
-- of those 35, and `lastUpdate` is a real timestamp on all 35. That is the
-- answer to "what is happening with my ticket", which is the question the bot's
-- `get_request_status` exists to answer and has been answering with the word
-- "open" and nothing else.
--
-- NEWEST FIRST. `lastUpdateNote` equals `treatmentLog[0]` on 13 of 13, never
-- `[-1]` except where the list has one entry. So element 1 in Postgres array
-- terms is the current note and the tail is history. Stored as an array rather
-- than a single note because the history is the useful part: "fittings ordered"
-- followed by "David handling it" is a ticket moving, and one string is not.
alter table requests add column if not exists oxs_last_update  timestamptz;
alter table requests add column if not exists oxs_notes        text[] not null default '{}';

-- WHEN WE LAST SAW IT, WHICH IS OURS AND NOT THEIRS.
--
-- OXS expresses closure by disappearance, not by status: 35 calls were live on
-- 24 Aug against 69 we had imported, so 35 of ours had left the feed while we
-- still displayed them open. Three left within a single hour that morning.
-- Whether leaving means resolved is a question for Homies — the endpoint cannot
-- distinguish "only open calls are served" from "nothing is ever closed here",
-- and `oxs_requests_sync.py` has refused to guess since 12 Aug.
--
-- This column stops it being a guess in either direction. Every ticket in the
-- feed gets stamped on every run, so "not seen since" is a measured fact with a
-- date on it, and the day Homies answers, one UPDATE resolves the backlog
-- instead of an archaeology exercise.
alter table requests add column if not exists oxs_last_seen_at timestamptz;

create index if not exists requests_oxs_last_seen_idx
  on requests (oxs_last_seen_at) where opened_via = 'oxs';

comment on column requests.oxs_notes is
  'OXS treatmentLog verbatim, NEWEST FIRST — element 1 is the current note.
   Their words, not ours: these are read by dispatchers and quoted to residents,
   and translating a company''s own vocabulary back at it is both rude and
   lossy.';

comment on column requests.oxs_last_seen_at is
  'The last run that saw this ticket in OXS''s service-call feed. A ticket whose
   stamp has stopped moving has left the feed — which MAY mean resolved. Do not
   convert it to resolved until Homies confirms the endpoint serves only open
   calls; see 022 and the note in oxs_requests_sync.py.';

comment on column requests.oxs_last_update is
  'OXS lastUpdate: when anything last happened to the call on their side. Equal
   to createdAt on a call nobody has touched.';
