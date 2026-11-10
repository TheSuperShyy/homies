-- 040 — the reviewers' page: Michael's real replies, each marked right or wrong, with a comment
--
-- Owner, 10 Nov: "push it live to vercel make sure the data can be saved on a database so we can
-- retrieve it add a send button". The page is the dashboard's /review. It opens without a login,
-- reached only through a link that carries a key (?k=...). Before it, the reviews lived in each
-- reviewer's browser (the 3 Nov "Michael Simulated Run") and could not be read back.
--
-- review_sets    one row per set of replies to review: `data` holds the chats, found by `key`.
--                The replies live here, not in the public repo: they quote a real flat's balance
--                and its payment link.
-- reply_reviews  one row per press of "send": marks = {"<step id>": {"m": "pass"|"fail"|null, "n": comment}}.
--
-- Both tables are RLS-locked with no anon policy. A visitor without a login reaches them only through the
-- two SECURITY DEFINER functions below, and both need the set's key. Staff (authenticated) read both.
-- Applied by hand through the Management API, like 036-039.
-- ---------------------------------------------------------------------------------------------------

create table if not exists review_sets (
  id         text primary key,
  key        text not null unique check (char_length(key) >= 20),
  title      text not null,
  data       jsonb not null check (jsonb_typeof(data) = 'object'),
  created_at timestamptz not null default now()
);

create table if not exists reply_reviews (
  id         uuid primary key default gen_random_uuid(),
  set_id     text not null references review_sets (id) on delete cascade,
  marks      jsonb not null check (jsonb_typeof(marks) = 'object' and pg_column_size(marks) < 200000),
  passed     integer not null,
  failed     integer not null,
  total      integer not null,
  created_at timestamptz not null default now()
);

create index if not exists reply_reviews_set_idx on reply_reviews (set_id, created_at desc);

alter table review_sets   enable row level security;
alter table reply_reviews enable row level security;
revoke all on review_sets, reply_reviews from anon;
drop policy if exists staff_read on review_sets;
create policy staff_read on review_sets for select to authenticated using (true);
drop policy if exists staff_read on reply_reviews;
create policy staff_read on reply_reviews for select to authenticated using (true);
grant select on review_sets, reply_reviews to authenticated;

-- The set behind a link, or null. Never lists sets: a wrong key learns nothing.
create or replace function review_set(p_key text) returns jsonb
language sql stable security definer set search_path = public, pg_temp as $$
  select jsonb_build_object('id', id, 'title', title, 'data', data)
  from review_sets where key = p_key
$$;

-- One press of "send". Keeps only the set's own steps, a mark of pass / fail / none and a note up to
-- 4,000 characters; refuses an unknown key and an empty review. Returns the counts it stored.
create or replace function submit_reply_review(p_key text, p_marks jsonb) returns jsonb
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  s      review_sets;
  steps  text[];
  clean  jsonb := '{}'::jsonb;
  k      text;
  v      jsonb;
  m      text;
  n      text;
  n_pass integer := 0;
  n_fail integer := 0;
  new_id uuid;
begin
  select * into s from review_sets where key = p_key;
  if s.id is null then
    raise exception 'unknown link' using errcode = '28000';
  end if;
  if jsonb_typeof(p_marks) is distinct from 'object' then
    raise exception 'marks must be an object' using errcode = '22023';
  end if;
  select array_agg(st->>'id') into steps
    from jsonb_array_elements(s.data->'chats') c, jsonb_array_elements(c->'steps') st;
  for k, v in select key, value from jsonb_each(p_marks) loop
    continue when not (k = any (steps)) or jsonb_typeof(v) is distinct from 'object';
    m := case when v->>'m' in ('pass', 'fail') then v->>'m' end;
    n := left(coalesce(v->>'n', ''), 4000);
    continue when m is null and btrim(n) = '';
    clean := clean || jsonb_build_object(k, jsonb_build_object('m', m, 'n', n));
    if m = 'pass' then n_pass := n_pass + 1; elsif m = 'fail' then n_fail := n_fail + 1; end if;
  end loop;
  if clean = '{}'::jsonb then
    raise exception 'nothing marked' using errcode = '22023';
  end if;
  insert into reply_reviews (set_id, marks, passed, failed, total)
    values (s.id, clean, n_pass, n_fail, coalesce(array_length(steps, 1), 0))
    returning id into new_id;
  return jsonb_build_object('id', new_id, 'passed', n_pass, 'failed', n_fail,
                            'total', coalesce(array_length(steps, 1), 0));
end
$$;

revoke all on function review_set(text) from public;
revoke all on function submit_reply_review(text, jsonb) from public;
grant execute on function review_set(text) to anon, authenticated;
grant execute on function submit_reply_review(text, jsonb) to anon, authenticated;

comment on table review_sets is
  'Sets of Michael''s real replies for reviewers (the dashboard''s /review?k=<key>). The data stays out of the public repo.';
comment on table reply_reviews is
  'One row per "send" on /review: marks {step: {m: pass|fail|null, n: comment}}, with the counts.';
