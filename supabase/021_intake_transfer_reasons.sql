-- The intake agent's transfer reasons were never legal values.
--
-- WHAT HAPPENED, 20 Aug
-- A caller reported black smoke coming out of a window. The agent did the right
-- thing on its side: it recognised an emergency and called
-- `transfer_to_human({reason: "emergency"})`. What was recorded was
--
--     call_outcomes.transfer_reason = 'caller_request'
--     interactions.disposition      = 'transfer:caller_request'
--
-- A possible fire, filed as "the caller asked to speak to someone".
--
-- WHY THE HANDLER LIED
-- It was not a bug in the handler so much as the handler protecting itself from
-- this constraint. `transfer_reason` has been limited to the six DEBT reasons
-- since 004, because that is the agent that existed when the column was
-- written. The intake agent shipped later with its own vocabulary --
-- INTAKE_TRANSFER_REASONS in scripts/vapi_tools.py: out_of_scope, emergency,
-- caller_request, repeated_failure, language -- and three of those five have
-- never been storable. The Edge Function's allow-list mirrored the constraint
-- and silently mapped anything outside it to `caller_request`, which turned a
-- rejected insert into a wrong one. Rejected would have been better: it would
-- have shown up.
--
-- 18 of the 24 transfers on record say `caller_request`. An unknown number of
-- them were something else, and there is no way to recover which -- the word
-- was discarded before it was written. Nothing here backfills; the transcripts
-- are the only remaining evidence.
--
-- The union, not a replacement: the debt agent still uses its six.
alter table call_outcomes drop constraint if exists call_outcomes_transfer_reason_check;

alter table call_outcomes add constraint call_outcomes_transfer_reason_check
  check (transfer_reason in (
    -- Debt follow-up (004). `ownership` was added 11 Aug in the Edge Function
    -- and is included here for the same reason as the intake five: it is a
    -- value the code already sends.
    'hardship','dispute','distress','language','not_understood','caller_request',
    'ownership',
    -- Inbound intake. `language` and `caller_request` are shared with the list
    -- above and appear once.
    'out_of_scope','emergency','repeated_failure'
  ));

comment on column call_outcomes.transfer_reason is
  'Why the call was handed over. Two vocabularies share this column: the debt
   agent sends hardship/dispute/distress/language/not_understood/caller_request/
   ownership, the intake agent sends out_of_scope/emergency/caller_request/
   repeated_failure/language. Keep this constraint in step with both
   TRANSFER_REASONS and INTAKE_TRANSFER_REASONS in scripts/vapi_tools.py -- when
   they drifted apart, every intake-only reason was silently written as
   caller_request.';
