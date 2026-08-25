-- ---------------------------------------------------------------------------
-- 024 — press_call: the one door a person's press goes through
-- ---------------------------------------------------------------------------
-- Decided 25 Aug: outbound debt calls are a "Call" button per resident on the
-- dashboard's Debts page. A person presses it, the agent calls that one
-- resident. Nothing dials on its own, ever.
--
-- The press IS the human decision `handed_over` was guarding. Since 4 Aug every
-- resident has carried handed_over = false so that `v_debt_call_queue` is empty
-- and nothing can dial; a runner that iterated the queue was the thing being
-- guarded against, and there is no runner. So the flag flips here, for this one
-- resident, at the moment somebody chose them by name and pressed.
--
-- WHY A FUNCTION AND NOT TWO STATEMENTS FROM THE PAGE
-- The dashboard talks to Postgres with the anon key, which migration 010 opened
-- for SELECT on everything and 011 for UPDATE on exactly one column of one
-- table. Letting the page UPDATE residents directly would hand the public anon
-- key the whole row — phone, name, do_not_call. This function is SECURITY
-- DEFINER, does one thing, and is the only write the key gains.
--
-- It returns the resident's row from `v_debt_call_queue_person` — the same
-- composed phrases and charges whitelist a demo call rides in on — or NULL when
-- the resident is not eligible: nothing unpaid, do_not_call, or four attempts
-- already. A NULL is a refusal the page can explain; it is never a call.
create or replace function press_call(p_phone text)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  r jsonb;
begin
  update residents set handed_over = true
   where phone = p_phone and handed_over = false;

  select to_jsonb(v) into r
    from v_debt_call_queue_person v
   where v.phone = p_phone;

  return r;   -- NULL when not eligible
end;
$$;

revoke all on function press_call(text) from public;
grant execute on function press_call(text) to anon, authenticated;

comment on function press_call(text) is
  'Marks one resident handed over and returns their v_debt_call_queue_person row '
  '(NULL if not eligible). The only write the anon key has on residents. Called by '
  'the dashboard''s Call button; see docs/features/15-call-button.';
