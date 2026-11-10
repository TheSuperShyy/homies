-- 039 — the "ticket closed" message names the report as the tenant gave it
--
-- Owner, 10 Nov: "fix it", on the closed-ticket test of 255-1433-26. The message
-- (ticket_resolved_he) carries a short description as {{2}}. 036/037 took the
-- first 80 characters of requests.description, and since 29 Oct the WhatsApp
-- bot's add_request_detail appends what it adds to a ticket after " | ". So the
-- test's message would have read:
--
--   "הקריאה שלכם מספר 255-1433-26 (המעלית תקועה בקומה 3 מהבוקר | יש רק מעלית
--    אחת | הדייר שוב שואל מתי מגיעים ומחכה ) טופלה ונסגרה"
--
-- The bot's own notes about the tenant ("הדייר שוב שואל...") reached the
-- tenant's message. The first part, before the first " | ", is the report as
-- opened: "(המעלית תקועה בקומה 3 מהבוקר)".
--
-- The body below is 037's, character for character, with one change: {{2}} is
-- split_part(..., ' | ', 1), trimmed. The rights stay SECURITY DEFINER with
-- search_path pinned (037 says why). The trigger points at the function by
-- name, so replacing the function is enough.
-- ---------------------------------------------------------------------------
create or replace function queue_ticket_resolved_notice() returns trigger
security definer
set search_path = public, pg_temp
as $$
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
        '2', left(btrim(regexp_replace(split_part(coalesce(new.description, ''), ' | ', 1), '\s+', ' ', 'g')), 80)
      )
    )
    on conflict (request_id, kind) do nothing;
  end if;
  return new;
end;
$$ language plpgsql;

comment on function queue_ticket_resolved_notice is
  'Queues the WhatsApp "done" template for a WhatsApp-opened ticket the moment
   its status becomes resolved. Sending happens elsewhere, on purpose.
   SECURITY DEFINER since 23 Sep: ticket_notices is RLS-protected with no
   insert policy, so as an INVOKER function this rolled back every staff
   attempt to resolve a WhatsApp ticket. Since 10 Nov (039) {{2}} is the
   report before the first " | ", so notes added later never reach the tenant.';
