-- 009 — row-level security for the dashboard, and a leak closed.
--
-- THE LEAK. `messages` shipped in 008 without RLS enabled. Every other table in
-- this database has it on, so the anon key reads nothing from them — checked,
-- zero rows. `messages` returned real rows to the anon key, and the anon key is
-- PUBLIC by design: it goes in the browser bundle, and anyone with it and the
-- project URL could read every resident's WhatsApp conversation.
--
-- It existed for about an hour, on a table containing four test conversations
-- and no real resident. That is luck rather than design. RLS is not something a
-- new table opts into; it is something a new table must not be able to skip,
-- which is what the check at the bottom of this file is for.
--
-- THE MODEL. The dashboard authenticates staff with Supabase Auth and talks to
-- PostgREST with the ANON key plus the user's session — never the service role
-- key, which must not reach a browser under any circumstances. So every table
-- the dashboard reads needs an explicit policy for the `authenticated` role.
--
-- Read-only, all of it. The dashboard shows what happened; nothing in it edits
-- a ticket, and a policy that does not exist cannot be exploited. Writes come
-- from the Edge Function and n8n, which use the service role key and bypass RLS
-- by design.

-- ---------------------------------------------------------------------------
-- The leak
-- ---------------------------------------------------------------------------
alter table messages enable row level security;

-- ---------------------------------------------------------------------------
-- Read access for signed-in staff
-- ---------------------------------------------------------------------------
-- `to authenticated` and not `to public`: `public` would include `anon`, which
-- is the mistake this migration exists to fix.
do $$
declare t text;
begin
  foreach t in array array[
    'residents', 'requests', 'interactions', 'messages',
    'charges', 'call_outcomes', 'payment_links', 'payment_tickets',
    'payment_disputes', 'promises_to_pay'
  ] loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists staff_read on %I', t);
    execute format(
      'create policy staff_read on %I for select to authenticated using (true)', t);
  end loop;
end $$;

comment on policy staff_read on requests is
  'Any signed-in staff member reads everything. Department scoping (PRD §10) is
   deliberately NOT here yet: there is no staff table to scope against, and a
   policy that looks like access control while enforcing nothing is worse than
   an honest one.';

-- ---------------------------------------------------------------------------
-- Views must not be a way around the policies above
-- ---------------------------------------------------------------------------
-- A view runs with its owner's rights by default, so it reads through RLS as
-- the owner and hands the rows out regardless of who asked. `v_conversations`
-- was doing exactly that — it returned rows to the anon key even while its
-- underlying tables were locked. security_invoker makes the caller's policies
-- apply, which is the only setting that makes a view safe to expose.
alter view v_conversations set (security_invoker = on);
alter view v_debt_call_queue set (security_invoker = on);
alter view v_pending_payment_tickets set (security_invoker = on);

-- ---------------------------------------------------------------------------
-- So this cannot happen again
-- ---------------------------------------------------------------------------
-- A table added without RLS is invisible until someone thinks to check with the
-- anon key, which is how 008 got through. This makes it loud: any future
-- migration that forgets `enable row level security` fails here rather than
-- shipping a readable table.
do $$
declare unguarded text;
begin
  select string_agg(c.relname, ', ')
    into unguarded
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public'
    and c.relkind = 'r'
    and not c.relrowsecurity
    and c.relname <> 'schema_migrations';

  if unguarded is not null then
    raise exception
      'These tables have no row-level security and the anon key can read them: %',
      unguarded;
  end if;
end $$;
