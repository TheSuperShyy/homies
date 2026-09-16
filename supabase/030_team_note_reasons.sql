-- The team note's reasons were never legal values either.
--
-- WHAT HAPPENED, 14 Sep
-- The WhatsApp bot stopped transferring and started NOTING: `notify_team`
-- says what the matter is -- payment, billing, move, contract, quote,
-- emergency, caller_request, other -- so the team reading the Chatwoot
-- mention knows what it is about before opening the thread. The tool still
-- posts to the same Edge Function handler as before, under the handler's old
-- name, and that handler still writes `call_outcomes.transfer_reason`.
--
-- Six of the eight words are not in this constraint, so the handler's
-- allow-list did what 021 describes: turned each of them into
-- `caller_request` and wrote that without complaint. Every dues question
-- noted on 14 Sep is on record here as "the resident asked for a person".
-- The Chatwoot note carried the right reason, because the n8n workflow reads
-- the tool's argument directly; only this table lied. Same failure, other
-- channel, one day old.
--
-- From today the inbound voice agent sends the same eight (plus `language`,
-- which is already here), so the union is widened once for both channels.
-- Three vocabularies now share the column; the comment below names them.
-- Nothing here backfills the 14 Sep rows: the word was discarded before it
-- was written.
alter table call_outcomes drop constraint if exists call_outcomes_transfer_reason_check;

alter table call_outcomes add constraint call_outcomes_transfer_reason_check
  check (transfer_reason in (
    -- Debt follow-up (004, 011 Aug).
    'hardship','dispute','distress','language','not_understood','caller_request',
    'ownership',
    -- Inbound intake's transfer reasons (021). Retired from the declaration on
    -- 14 Sep but kept storable: old rows carry them.
    'out_of_scope','emergency','repeated_failure',
    -- The team note (14 Sep): the matter, not the failure. WhatsApp and the
    -- inbound voice agent both send these through notify_team.
    'payment','billing','move','contract','quote','other'
  ));

comment on column call_outcomes.transfer_reason is
  'Why the call was handed over, or -- since 14 Sep -- what the team was told
   about. Three vocabularies share this column: the debt agent sends
   hardship/dispute/distress/language/not_understood/caller_request/ownership;
   the intake agent used to send out_of_scope/emergency/caller_request/
   repeated_failure/language; notify_team (WhatsApp and inbound voice) sends
   payment/billing/move/contract/quote/emergency/caller_request/language/other.
   Keep this constraint in step with TRANSFER_REASONS and INTAKE_NOTE_REASONS
   in scripts/vapi_tools.py and the reasons list in scripts/n8n_whatsapp.py --
   when they drift, the Edge Function silently writes caller_request.';
