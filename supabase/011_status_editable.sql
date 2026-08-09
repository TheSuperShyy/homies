-- 011 — the dashboard can change a ticket's status. Nothing else.
--
-- Same demo-mode trade as 010, and the same expiry date. The dashboard has no
-- login, so the write goes through the anon role — which means anyone holding
-- the project URL and the anon key can change ticket statuses. Acceptable for
-- demo data. NOT acceptable once real tickets are here.
--
-- The blast radius is one column by construction, not by policy prose:
-- Postgres column-level grants mean the anon role can update `status` and
-- nothing else — not the description, not the building, not the reference.
-- A request that touches any other column fails at the grant, before RLS is
-- even consulted. The check constraint on status rejects invented values.
--
-- TO RE-LOCK (with the 010 re-lock, before pilot or real data):
--   drop policy anon_update_status on requests;
--   revoke update on requests from anon;

revoke update on requests from anon;
grant update (status) on requests to anon;

drop policy if exists anon_update_status on requests;
create policy anon_update_status on requests
  for update to anon using (true) with check (true);

comment on policy anon_update_status on requests is
  'Demo mode: the no-login dashboard edits ticket status through the anon
   role. Column-level grant restricts the write to status alone. Drop this
   policy and revoke the grant before real ticket data arrives — see the
   header of 011.';
