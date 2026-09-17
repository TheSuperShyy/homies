-- 033: a resident's WhatsApp photo is kept, and hung on the ticket.
--
-- The client's old bot (ManyChat -> Make -> Monday, scanned 17 Sep 2026)
-- attaches the resident's photo to the task it files. Ours dropped it: the
-- photo reaches Chatwoot, staff can see it in the conversation, and the
-- ticket never hears of it. From here the Edge Function's `store_media`
-- copies the bytes out of Chatwoot into the private bucket below and writes
-- one row per image; `open_request` then adopts whatever arrived from that
-- phone in the previous hour.
--
-- Two phone shapes live in this database and this table takes the BARE one
-- (972…, the shape of `messages.phone`), because the row is written from the
-- same n8n turn that writes `messages`. `requests.reported_by_phone` is E.164
-- (+972…); the function joins the two by prefixing a plus, never by comparing
-- them raw.

create table if not exists request_media (
  id                  uuid primary key default gen_random_uuid(),
  request_id          uuid references requests (id) on delete cascade,
  phone               text not null,
  message_external_id text,
  storage_path        text not null unique,
  mime                text not null,
  file_size           int,
  created_at          timestamptz not null default now()
);

create index if not exists request_media_request_idx on request_media (request_id);
create index if not exists request_media_phone_idx   on request_media (phone, created_at desc);

comment on table request_media is
  'One row per image a resident sent on WhatsApp, copied from Chatwoot into the
   ticket-media bucket by debt-tools store_media at webhook time. request_id is
   the newest live ticket from that phone (open / in_progress / needs_review,
   under 2 hours old) at the moment the photo arrived; null until the next
   open_request from that phone adopts it (60-minute window).';
comment on column request_media.phone is
  'Bare 972…, the shape of messages.phone. Join to requests.reported_by_phone
   as ''+'' || phone, never raw.';
comment on column request_media.message_external_id is
  'Chatwoot message id, the same value as messages.external_id, so the
   conversation page can put the thumbnail inside the right bubble.';
comment on column request_media.storage_path is
  'Object key in bucket ticket-media: <phone>/<message id>-<n>.<ext>.';

-- ---------------------------------------------------------------------------
-- Who reads it: signed-in staff, same shape as 009. Nobody but the service
-- role writes it.
-- ---------------------------------------------------------------------------
alter table request_media enable row level security;
drop policy if exists staff_read on request_media;
create policy staff_read on request_media for select to authenticated using (true);
grant select on request_media to authenticated;

-- ---------------------------------------------------------------------------
-- The bucket. PRIVATE, unlike avatars (029): a photo of somebody's flooded
-- kitchen is theirs, and the dashboard hands out one-hour signed URLs instead.
-- WhatsApp caps an image at 5 MB; 10 MB leaves room without inviting video.
-- ---------------------------------------------------------------------------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('ticket-media', 'ticket-media', false, 10485760,
        array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do update
  set public             = excluded.public,
      file_size_limit    = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- createSignedUrl runs as the signed-in user and needs SELECT on the object.
-- No insert, update or delete for staff: the function writes, nobody else.
drop policy if exists ticket_media_read on storage.objects;
create policy ticket_media_read on storage.objects
  for select to authenticated
  using (bucket_id = 'ticket-media');

comment on policy ticket_media_read on storage.objects is
  'Signed-in staff may sign a URL for any ticket photo. Writes are the Edge
   Function''s alone, on the service role.';

comment on column requests.image_count is
  'Imported rows (opened_via = oxs): OXS''s own count, from oxs_requests_sync.
   Bot rows: the number of request_media rows, maintained by debt-tools.';
