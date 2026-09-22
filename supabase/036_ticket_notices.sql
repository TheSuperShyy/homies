-- 036: the "done" message outbox (22 Sep).
--
-- A service call opened from WhatsApp gets one message when it is resolved:
-- a Meta-approved template (docs/features/11-whatsapp-bot/templates.md,
-- `ticket_resolved_he`), because the resident has usually not written to us in
-- the last 24 hours and Meta refuses free text outside that window.
--
-- The row IS the record and the retry: the trigger below writes it the moment
-- a ticket turns resolved, and `send_ticket_notices` in the Edge Function
-- (driven every two minutes by the n8n workflow "Homies — ticket notices")
-- sends it and marks the outcome. Nothing is sent from inside the trigger --
-- a database transaction that talks to Meta is a database transaction that
-- hangs when Meta is slow.

create table if not exists ticket_notices (
  id              uuid primary key default gen_random_uuid(),
  request_id      uuid not null references requests (id) on delete cascade,
  phone           text not null,                       -- +E.164, requests.reported_by_phone
  kind            text not null check (kind in ('resolved')),
  template        text not null,                       -- the Meta template name
  params          jsonb not null default '{}'::jsonb,  -- {"1": reference, "2": short description}
  status          text not null default 'pending'
                    check (status in ('pending', 'sent', 'failed', 'skipped')),
  attempts        integer not null default 0,
  error           text,
  conversation_id integer,                             -- the Chatwoot conversation it went to
  created_at      timestamptz not null default now(),
  sent_at         timestamptz,
  unique (request_id, kind)                            -- one done message per ticket, ever
);

create index if not exists ticket_notices_pending_idx
  on ticket_notices (created_at) where status = 'pending';

comment on table ticket_notices is
  'Outbox for messages the system sends a resident about a ticket. One row per
   (ticket, kind); the trigger on requests fills it, the Edge Function drains it.';
comment on column ticket_notices.status is
  'pending: not yet sent. sent: Chatwoot accepted it and did not mark it failed.
   failed: Meta refused (error says why); retried up to 5 times by the drainer.
   skipped: a test number, never sent.';

alter table ticket_notices enable row level security;
drop policy if exists staff_read on ticket_notices;
create policy staff_read on ticket_notices for select to authenticated using (true);
grant select on ticket_notices to authenticated;

-- ---------------------------------------------------------------------------
-- The trigger: a WhatsApp ticket turning resolved queues its done message.
-- Only tickets with a reporter phone (carried since 18 Sep); a ticket with no
-- number has nobody to tell. `on conflict do nothing` keeps a ticket that is
-- reopened and resolved again from sending twice.
-- ---------------------------------------------------------------------------
create or replace function queue_ticket_resolved_notice() returns trigger as $$
begin
  if new.status = 'resolved'
     and old.status is distinct from 'resolved'
     and new.opened_via = 'whatsapp'
     and new.reported_by_phone is not null then
    insert into ticket_notices (request_id, phone, kind, template, params)
    values (
      new.id,
      new.reported_by_phone,
      'resolved',
      'ticket_resolved_he',
      jsonb_build_object(
        '1', new.reference,
        '2', left(regexp_replace(coalesce(new.description, ''), '\s+', ' ', 'g'), 80)
      )
    )
    on conflict (request_id, kind) do nothing;
  end if;
  return new;
end;
$$ language plpgsql;

drop trigger if exists requests_notice_resolved on requests;
create trigger requests_notice_resolved
  after update of status on requests
  for each row execute function queue_ticket_resolved_notice();

comment on function queue_ticket_resolved_notice is
  'Queues the WhatsApp "done" template for a WhatsApp-opened ticket the moment
   its status becomes resolved. Sending happens elsewhere, on purpose.';
