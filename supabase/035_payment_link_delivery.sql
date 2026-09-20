-- 035: the debt call delivers its link to WhatsApp (20 Sep).
--
-- Comment-only. No column moves: 034 already allows `link`, `apartment_id` and
-- `payer_id` on a voice row, and its unique index on (interaction_id) for voice
-- rows is exactly the shape send_payment_link writes now -- ONE row per call,
-- carrying the targets' total and the earliest month, instead of one per
-- charge (which that index has refused on any two-flat call since 034).

comment on column payment_links.channel is
  'voice: one row per call, written by send_payment_link, which mints the link
   (oxsLinkFor, shared with the chat tool) and sends it as a WhatsApp message to
   the number on file while the call is on (20 Sep). whatsapp: a row per
   apartment, written by get_payment_link with the link the bot handed over.';

comment on column payment_links.status is
  'sent: delivered (chat: handed over in the reply; voice: the WhatsApp message
   was accepted and not marked failed). requested: minted or attempted and not
   delivered -- the `note` says why (outside_window, no_contact, apartment_unknown,
   test_number, ...). A second attempt on the same call reuses the stored link.';
