-- 029 — somewhere to put a staff photo.
--
-- WHY THIS IS THE ONLY THING THE FEATURE NEEDS. The settings page grew two
-- fields on 30 Aug: a display name and a profile photo. Neither gets a table.
--
-- The obvious design is a `profiles` table keyed on auth.users(id), and it is
-- the wrong one here. The shell renders the reader's name and picture in the
-- sidebar and the topbar on EVERY page, and the whole reason that shell streams
-- quickly is that it does not ask the database who is signed in — the
-- middleware already calls `auth.getUser()` to decide whether to let the
-- request through, and hands the answer down as a request header. A profiles
-- table would put a second round trip back in front of every page render, which
-- is precisely the cost that was removed on 30 Aug.
--
-- `auth.users.raw_user_meta_data` comes back with `getUser()` at no cost, so
-- the name and the photo's URL live there. The trade-off is honest and worth
-- stating: user metadata is writable by the user themselves through the auth
-- API. That is correct for a name and a picture, which are theirs to choose,
-- and it would be COMPLETELY WRONG for anything that grants access. If a role
-- column is ever added, it does NOT go here — it goes in a table with its own
-- policies, and RLS reads it from there, never from the JWT's metadata.
--
-- So all that is left is a bucket for the image itself.

-- ---------------------------------------------------------------------------
-- The bucket
-- ---------------------------------------------------------------------------
-- PUBLIC, deliberately. The alternative is a private bucket plus a signed URL
-- minted on every render, which expires, needs a round trip, and cannot be
-- cached by the browser. What is in here is a handful of staff headshots — not
-- resident data, and nothing that RLS anywhere else depends on. A public bucket
-- for those is the ordinary answer and the one every dashboard uses.
--
-- The limits are enforced HERE and not only in the upload code, because the
-- upload code is a thing anybody with a session can bypass by calling the
-- storage API directly. 256 KB is generous for a 256px square: the browser
-- resizes to that before it uploads, which lands around 20 KB.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('avatars', 'avatars', true, 262144,
        array['image/webp', 'image/jpeg', 'image/png'])
on conflict (id) do update
  set public             = excluded.public,
      file_size_limit    = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- ---------------------------------------------------------------------------
-- Who may do what
-- ---------------------------------------------------------------------------
-- Every object lives under a folder named for its owner's user id, and the
-- write policies check that folder against `auth.uid()`. Without that, any
-- signed-in account could overwrite anybody else's photo — a small thing to do
-- to a colleague and an unpleasant one.
drop policy if exists avatars_read on storage.objects;
create policy avatars_read on storage.objects
  for select to public
  using (bucket_id = 'avatars');

drop policy if exists avatars_insert_own on storage.objects;
create policy avatars_insert_own on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'avatars'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists avatars_update_own on storage.objects;
create policy avatars_update_own on storage.objects
  for update to authenticated
  using (
    bucket_id = 'avatars'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists avatars_delete_own on storage.objects;
create policy avatars_delete_own on storage.objects
  for delete to authenticated
  using (
    bucket_id = 'avatars'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

comment on policy avatars_read on storage.objects is
  'Staff headshots, public by design — see 029. Nothing resident-identifying goes in this bucket.';
