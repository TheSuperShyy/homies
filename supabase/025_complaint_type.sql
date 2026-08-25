-- ---------------------------------------------------------------------------
-- 025 — a complaint is a ticket
-- ---------------------------------------------------------------------------
-- Decided 25 Aug by the owner: a complaint opens a ticket, on the phone and on
-- WhatsApp, the same way a leak does. Until now a complaint about a person —
-- the cleaner, a contractor, the office — was a hand-over to a human with no
-- record but the conversation, and 014's type list had nowhere to file one.
--
-- 'complaint' joins the eleven OXS categories. It is OURS, not theirs: OXS has
-- no such category and nothing is written to OXS anyway (read-only, and the
-- owner wants the foundation before any POST). A complaint ticket lives in
-- `requests` with reported_by, building, unit, description and the channel it
-- came in on — which is what the PRD §2.5 asks for — and staff read it in
-- the dashboard and the inbox.
alter table requests drop constraint if exists requests_type_check;
alter table requests add constraint requests_type_check
  check (type is null or type in (
    'plumbing','electrical','lighting','elevator','cleaning','gardening',
    'pest_control','locksmith','fire_safety','maintenance','other',
    'complaint'));

comment on constraint requests_type_check on requests is
  'The eleven OXS dispatcher categories plus complaint (ours, 25 Aug). A tool '
  'that sends anything else fails here rather than filing it as other.';
