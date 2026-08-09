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
