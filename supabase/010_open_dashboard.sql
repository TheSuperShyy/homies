-- 010 — open the dashboard: anon read on everything the dashboard shows.
--
-- Demo-mode decision, 9 August 2026: no login screen. The middleware redirect
-- is gone from dashboard/middleware.ts, and this migration gives the anon role
-- the same read-only view that `authenticated` got in 009.
--
-- KNOW WHAT THIS TRADES AWAY. The anon key ships in the browser bundle and is
-- public by design. With these policies, anyone holding the project URL and
-- that key reads every table below — residents, conversations, calls — without
-- signing in. Acceptable while the data is demo/test data and the dashboard is
-- a demo. It is NOT acceptable once real residents are in these tables.
--
-- TO RE-LOCK (before pilot, or the moment real data lands):
--   drop the anon_read policies (loop below with drop instead of create),
--   restore the middleware redirect, and staff sign in again. 009's
--   authenticated policies are untouched by this file, so re-locking is a
--   deletion, not a rebuild.

do $$
declare t text;
begin
  foreach t in array array[
    'residents', 'requests', 'interactions', 'messages',
    'charges', 'call_outcomes', 'payment_links', 'payment_tickets',
    'payment_disputes', 'promises_to_pay'
  ] loop
    execute format('drop policy if exists anon_read on %I', t);
    execute format(
      'create policy anon_read on %I for select to anon using (true)', t);
  end loop;
end $$;

comment on policy anon_read on requests is
  'Demo mode: the dashboard has no login, so the anon role reads what
   authenticated reads. Drop every anon_read policy before real resident data
   arrives — see the header of this migration.';
