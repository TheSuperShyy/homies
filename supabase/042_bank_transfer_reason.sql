-- 042 — a bank transfer is a note reason of its own
--
-- 18 Nov 2026 (Yariv; the owner: "ok give the phone line the same transfer as whatsapp"). A tenant who wants to pay
-- by bank transfer, or asks for the account details, is passed to a representative from the collections team, and
-- the note that does it carries the reason `bank_transfer` ("Hand to a person" routes it to Collections, labels it
-- `bank-transfer`, and tells staff to send the account details). The WhatsApp bot has sent it since epoch 111; the
-- inbound phone agent sends it from 19 Nov.
--
-- The Edge Function's transfer_to_human keeps an allow-list and stores anything else as `caller_request`, the quiet
-- lie 021 and 030 were written against: on the phone that would also send the team's note to Management as "asked
-- for a person", because the function posts the voice note with the reason it stored. So the word goes into the
-- function's list, and first into this CHECK, or the insert of the row would fail.
--
-- Additive: every value 030 allowed is still allowed.
-- ---------------------------------------------------------------------------
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
    'payment','billing','move','contract','quote','other',
    -- 18 Nov (042): a bank transfer, handed to collections and told to the tenant.
    'bank_transfer'
  ));
