-- 019 — row-level security on buildings and apartments
--
-- 016 created both tables and did not enable RLS, so from the moment it was
-- applied the **anon key could read the whole portfolio** — 173 addresses and
-- 4,092 apartments — and that key ships in the dashboard's browser bundle and
-- is public by design.
--
-- This is exactly the failure 009 was written to prevent. Its guard raises if
-- any table in `public` lacks RLS, and it did not fire, because a migration
-- only ever runs once: 009 ran on 9 August and 016 arrived on 13 August, four
-- days after the check had had its only chance to look. A one-shot assertion
-- cannot guard tables that do not exist yet.
--
-- So two things change. This file turns RLS on, and `scripts/supabase_migrate.py`
-- now runs the same assertion after **every** run, where it can see whatever
-- was just applied. The check in 009 stays as documentation of the rule.
--
-- NO ANON POLICY, deliberately, which is not what 010 did for the other tables.
-- 010 opened everything to anon for the no-login demo dashboard, and it says in
-- its own header that this is a trade to be reversed before real data arrives.
-- Nothing in the dashboard reads buildings or apartments today, so there is no
-- feature to weigh against it, and this is a client's commercial portfolio —
-- every building they manage, with its unit count. RLS on and no policy means
-- anon reads nothing.
--
-- The Edge Function is unaffected: `debt-tools` connects with
-- SUPABASE_SERVICE_ROLE_KEY, and the service role bypasses RLS. `verify_address`
-- keeps working.
--
-- Idempotent. Safe to re-run.

alter table buildings  enable row level security;
alter table apartments enable row level security;

-- Said out loud rather than left implicit, so the next person does not "fix"
-- the missing policy by adding one.
comment on table buildings is
  'Mirror of OXS /buildings. Import-only: OXS is read-only, forever. Refreshed
   by scripts/oxs_buildings_sync.py. RLS is ON WITH NO POLICY on purpose — only
   the service role reads this. It is the client''s whole portfolio, and no
   dashboard page needs it. If a page ever does, add a policy for the role that
   page authenticates as, not for anon.';

comment on table apartments is
  'Mirror of OXS /buildings/:id/apartments. The only source that knows a flat
   exists when nobody lives in it or nobody has a phone. RLS is ON WITH NO
   POLICY, same reasoning as buildings.';
