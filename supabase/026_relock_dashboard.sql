-- 026 — re-lock the dashboard: the login goes from existing to enforced.
--
-- Demo mode (9 Aug, migration 010) opened every dashboard table to the anon
-- role because the login wall was down. 010's own header says to drop those
-- policies "before pilot, or the moment real data lands"; the owner asked for
-- the login on 26 Aug, and this is the deletion that header promised. 009's
-- authenticated policies are untouched and become the dashboard's whole read
-- path again.
--
-- Three anon grants existed, not one, and this closes all of them:
--
--   * anon_read on ten tables            (010) — dropped below.
--   * anon_update_status on requests     (011) — the status dropdown wrote
--     through anon because there was no session to write through. Dropped,
--     revoked, and RE-CREATED for authenticated: the dropdown now works only
--     signed in. Without that half the re-lock silently breaks the tickets
--     page for staff.
--   * execute on press_call(text)        (024) — was granted to anon AND
--     authenticated. Anon's half is revoked; the Call button needs a session.
--
-- buildings/apartments (019) already deny anon and are not touched.
--
-- Idempotent. Safe to re-run.

do $$
declare t text;
begin
  foreach t in array array[
    'residents', 'requests', 'interactions', 'messages',
    'charges', 'call_outcomes', 'payment_links', 'payment_tickets',
    'payment_disputes', 'promises_to_pay'
  ] loop
    execute format('drop policy if exists anon_read on %I', t);
  end loop;
end $$;

-- The status dropdown, moved from anon to authenticated.
drop policy if exists anon_update_status on requests;
revoke update (status) on requests from anon;

grant update (status) on requests to authenticated;
drop policy if exists authenticated_update_status on requests;
create policy authenticated_update_status on requests
  for update to authenticated using (true) with check (true);

comment on policy authenticated_update_status on requests is
  'The tickets page''s status dropdown. Column-level grant limits the write to
   `status`; RLS row predicate is open because every staff member may move any
   ticket. Replaced anon_update_status (011) when the login was enforced on
   26 Aug 2026 — see 026.';

-- The Call button. Authenticated keeps execute from 024.
revoke execute on function press_call(text) from anon;
