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
