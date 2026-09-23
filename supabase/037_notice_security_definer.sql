-- The done-message trigger runs with its own rights, not the staff member's.
--
-- WHAT WENT WRONG. Migration 036 created queue_ticket_resolved_notice() as an
-- ordinary (INVOKER) function, so its insert into ticket_notices ran as
-- whoever did the UPDATE. ticket_notices has RLS on with a read policy and no
-- insert policy (036:43-46), deliberately -- a notice is written by the system,
-- never by a person. The two together mean a staff member resolving a WhatsApp
-- ticket in the dashboard hits:
--
--   new row violates row-level security policy for table "ticket_notices"
--
-- and because the insert is inside the trigger, the UPDATE rolls back with it.
-- The ticket stays open. The owner set 255-1307-26 to Resolved on 23 Sep, saw
-- nothing happen, and got no message: the save never landed. It only ever
-- affected WhatsApp-opened tickets with a phone -- the exact rows the trigger
-- fires on -- which is why resolving OXS tickets always worked and this went
-- unnoticed from 18 Sep.
--
-- THE LESSON, for the next trigger: a trigger that writes to an RLS-protected
-- table must be SECURITY DEFINER, or it silently breaks every write to the
-- table it hangs off. The failure surfaces on the parent table, not on the
-- protected one, which is what makes it hard to read.
--
-- The alternative -- an insert policy on ticket_notices for authenticated --
-- was rejected: it would hand staff a direct write to the outbound queue to
-- fix a problem that is not theirs.
--
-- The body below is 036's, character for character. Only the rights change.
-- search_path is pinned because a SECURITY DEFINER function without one lets
-- anyone who can call it choose which `ticket_notices` it means.
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
        '2', left(regexp_replace(coalesce(new.description, ''), '\s+', ' ', 'g'), 80)
      )
    )
    on conflict (request_id, kind) do nothing;
  end if;
  return new;
end;
$$ language plpgsql;

-- The trigger already points at this function by name; replacing the function
-- is enough. Recreating it would only risk a window with no trigger at all.

comment on function queue_ticket_resolved_notice is
  'Queues the WhatsApp "done" template for a WhatsApp-opened ticket the moment
   its status becomes resolved. Sending happens elsewhere, on purpose.
   SECURITY DEFINER since 23 Sep: ticket_notices is RLS-protected with no
   insert policy, so as an INVOKER function this rolled back every staff
   attempt to resolve a WhatsApp ticket.';
