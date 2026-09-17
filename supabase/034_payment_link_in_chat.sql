-- 034: a payment link handed over in chat (17 Sep 2026).
--
-- OXS External API rev 1.3 added GET /apartments/:id/payment-link on the
-- finance module, read-only key: one short payment link per active payer of
-- the apartment, the same link OXS itself sends from "דרישת תשלום". It
-- notifies nobody; delivery is ours. The WhatsApp bot's `get_payment_link`
-- (debt-tools/index.ts) fetches the SENDER's own link and returns it in the
-- tool result, and this row records that it did.
--
-- 004 shaped this table for the voice flow: a row per CHARGE, one row per
-- call. A chat link is per APARTMENT (it opens the whole balance), and on
-- chat every message from one number shares one interactions row
-- (`wa:<phone>`), so "one per interaction" would refuse a second link for
-- that number for life. The voice guarantees stay exactly as they were, on
-- voice rows; chat rows get their own shape.
--
-- The link itself is stored, because OXS mints a NEW link on every call and
-- says to keep the one you got: a resident who asks twice gets the same link
-- back with no second call. Whoever holds a link can see and pay that
-- apartment's balance and it never expires, so the dashboard never selects
-- this column and no log path prints it.

alter table payment_links alter column charge_id drop not null;
alter table payment_links alter column amount    drop not null;   -- check (amount > 0) passes on NULL
alter table payment_links alter column period    drop not null;

alter table payment_links add column if not exists channel text not null default 'voice';
alter table payment_links drop constraint if exists payment_links_channel_check;
alter table payment_links add constraint payment_links_channel_check
  check (channel in ('voice', 'whatsapp'));

-- apartments.id, the OXS _id. No foreign key on purpose: the shape check
-- below requires it non-null on a chat row, and an apartment re-import must
-- not be able to null it out from under one.
alter table payment_links add column if not exists apartment_id text;
alter table payment_links add column if not exists payer_id     text;
alter table payment_links add column if not exists link         text;

alter table payment_links drop constraint if exists payment_links_shape;
alter table payment_links add constraint payment_links_shape check (
     (channel = 'voice'    and charge_id is not null and amount is not null and period is not null)
  or (channel = 'whatsapp' and apartment_id is not null and link is not null)
);

-- "One link per call" stays true on voice. On chat the reuse index is what
-- makes "asked again, same link" one cheap read.
drop index if exists payment_links_one_per_interaction;
create unique index if not exists payment_links_one_per_interaction
  on payment_links (interaction_id)
  where interaction_id is not null and channel = 'voice';
create index if not exists payment_links_reuse_idx
  on payment_links (resident_id, apartment_id, created_at desc)
  where channel = 'whatsapp';

comment on column payment_links.channel is
  'voice: a row per charge, written by send_payment_link (nothing delivers it
   yet). whatsapp: a row per apartment, written by get_payment_link with the
   link the bot handed over.';
comment on column payment_links.apartment_id is
  'apartments.id, the OXS apartment _id the link was minted for. Chat rows only.';
comment on column payment_links.payer_id is
  'The OXS payerId of the link chosen (our record for the phone, else the
   main payer). Stored so the match rate against residents.oxs_ref can be
   measured; never shown.';
comment on column payment_links.link is
  'The OXS payment link, exactly as returned. Whoever holds it can see and
   pay the apartment balance and it never expires. Never selected by the
   dashboard; never logged.';
comment on column payment_links.status is
  'voice: requested = we asked, nothing delivers it yet. whatsapp: sent =
   minted by OXS and handed to the bot in the tool result. Nothing here can
   observe whether it was paid; that is a read back from OXS.';
