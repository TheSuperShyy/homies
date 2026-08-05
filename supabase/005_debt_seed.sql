-- Homies — debt follow-up seed data
-- Extends the ten residents from 002 with the attributes the debt agent needs,
-- then gives them charges chosen to exercise every branch of the prompt.
-- Safe to re-run.
--
-- Period is July 2026 throughout, so `v_debt_call_queue` reports חודש יולי.

-- ---------------------------------------------------------------------------
-- Resident attributes
-- ---------------------------------------------------------------------------
update residents set gender = 'm', card_last4 = '4821' where phone = '+972501234567'; -- דוד
update residents set gender = 'f', card_last4 = '7355' where phone = '+972521234568'; -- שרה
update residents set gender = 'm', card_last4 = null   where phone = '+972531234569'; -- משה, no card
update residents set gender = 'f', card_last4 = '1190' where phone = '+972541234570'; -- רחל
update residents set gender = 'm', card_last4 = '6042' where phone = '+972551234571'; -- יוסי
update residents set gender = 'f', card_last4 = '8877' where phone = '+972581234572'; -- מיכל
update residents set gender = 'unknown', card_last4 = '2314' where phone = '+972501234573'; -- אבי

-- The apartment was never handed over. Two of the four real sample calls were
-- placed to residents in exactly this state and should not have been. The queue
-- view excludes them, so this row proves the exclusion rather than the branch.
update residents set handed_over = false, gender = 'f', card_last4 = null
  where phone = '+972521234574';                                            -- נועה

-- Asked not to be called again.
update residents set do_not_call = true, gender = 'm', card_last4 = '9506'
  where phone = '+972531234575';                                            -- איתי

-- ---------------------------------------------------------------------------
-- Charges
-- ---------------------------------------------------------------------------
-- Amounts vary because building committee fees vary by building, and a single
-- repeated number would hide a bug where the agent speaks a hardcoded amount.

insert into charges (resident_id, period, amount, status, attempts)
select r.id, date '2026-07-01', v.amount, v.status, v.attempts
from (values
  ('+972501234567', 450.00, 'unpaid', 0),   -- straightforward, card on file
  ('+972521234568', 450.00, 'unpaid', 1),   -- second attempt
  ('+972531234569', 380.00, 'unpaid', 0),   -- no card: office must contact
  ('+972541234570', 380.00, 'unpaid', 2),   -- third attempt
  ('+972551234571', 520.00, 'unpaid', 0),
  ('+972581234572', 520.00, 'paid',   0),   -- settled: must not appear in the queue
  ('+972501234573', 610.00, 'unpaid', 0),   -- gender unknown
  ('+972521234574', 610.00, 'unpaid', 0),   -- not handed over: excluded
  ('+972531234575', 295.00, 'unpaid', 1),   -- do not call: excluded
  ('+972541234576', 295.00, 'unpaid', 4)    -- attempts exhausted: excluded
) as v(phone, amount, status, attempts)
join residents r on r.phone = v.phone
on conflict (resident_id, period) do update set
  amount   = excluded.amount,
  status   = excluded.status,
  attempts = excluded.attempts;

-- ---------------------------------------------------------------------------
-- What the queue should now return
-- ---------------------------------------------------------------------------
-- Six rows, not ten. Excluded: מיכל (paid), נועה (not handed over),
-- איתי (do not call), טל (four attempts).
--
--   select first_name, building, month, amount, card_last4, gender, attempt
--   from v_debt_call_queue order by first_name;
--
-- If that returns ten rows, the view's filters are not being applied and no call
-- should be placed from it.
