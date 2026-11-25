# The dialer on the dashboard

**Estimate:** 1d
**Depends on:** 18-dialer-routing (who answers), 20-dialer-test (Omni's lead API), 15-call-button (`press_call`)
**Status:** BUILT 25 Nov 2026, PR #23 (`feature/real-dialer`); migration 043 applied and the function's Tokomni pair set on 25 Nov; the first real press is owed

## Purpose

The dashboard could ring testers only (feature 20). This is the dialer itself: staff pick tenants
who owe and the system calls them through Omni's dialer, one after another, with Michael (the
debt agent) on the line. The owner, 25 Nov: *"in the dashboard we need to have an actual dialer
section there not just the dialer test"*.

## Behaviour

1. **The page** (`/dialer`, "חייגן", in the main menu next to Debts; on a phone, the icon in the
   top bar) has two tabs: "חיוג לדיירים" (this) and "שיחות בדיקה" (feature 20, now at
   `/dialer/test`, unchanged).
2. **The line, now:** ringing someone, Michael talking to someone, or free; how many are waiting;
   a Stop button while anyone waits. Four counts for today: waiting, called, answered, no answer.
   The page refreshes itself every 10 s while anything is waiting or on the line.
3. **Today's calls:** each press of today, with its status, its result (the agent's outcome, or
   why it did not ring), when, who pressed, and a link to the call's page once it has one.
4. **Who owes:** one row per phone number (a couple on one phone is one ring; an owner of two flats
   is one call about both): name, buildings and flats, amount, months, tries so far (of 4), the
   last call's result, and today's state. Filter by month, search by name, phone or building, 10,
   25 or 50 rows a page. Every unpaid charge counts; the month filter only picks who is shown.
5. **A press:** tick rows (or the whole page) and press "חייג למסומנים", or press "חייג" on one
   row. Each becomes a waiting row in `dialer_calls` (`dialer_queue`), or a reason it did not:
   not an Israeli number, already queued, already called today, no tenant on the number,
   do-not-call, owes nothing, or four tries on every open month. A press outside calling hours
   adds nobody. The button is the only thing that puts anyone in the queue.
6. **The tick** (debt-tools, `dialer-tick`): pg_cron posts it every 15 s, and only while the queue
   has a row waiting, sending, ringing or talking. One tick:
   1. reads the bot's line on Vapi (`GET /call?phoneNumberId=<208>&limit=5`): busy while a call
      has not ended, else quiet since the newest ended;
   2. expires what is over (`dialer_expire`): a lead ringing for 2 minutes, and 90 s after the
      line went quiet, is **no answer** (one try counted, and a `no_answer` row in
      `call_outcomes`, so the Calls page's "ללא מענה" tab shows it); a send that never finished
      after 2 minutes is failed (no try); a call on the line for 20 minutes with no report is done;
   3. outside calling hours (Sun-Thu 09:00-20:00, Fri until 13:00, never Saturday, Israel time):
      cancels everyone waiting, and stops;
   4. without `TOKOMNI_TOKEN` / `TOKOMNI_CAMPAIGN_ID` in the function: cancels everyone waiting;
   5. with the line busy or unreadable: waits for the next tick;
   6. takes the next tenant (`dialer_claim_next`, under one lock): nothing while paused, while a
      lead is still sending, ringing or talking, or when the last five sent leads since the last
      Resume all reached nobody (that pauses the queue). A tenant already called today, no longer
      eligible (`press_call()`: paid, do-not-call, 4 tries), or sharing the number with another
      tenant who owes, is skipped with the reason. `press_call()` also puts the tenant on the debt
      call list, which is what makes the router hand the call to the debt agent;
   7. sends one lead to Tokomni (the same request as the dialer test page, `external_id` =
      resident id + the moment): 200 that took it is **ringing**; no answer at all is ringing too
      (on 16 Nov such a lead rang anyway); anything else is **failed**, and a refusal that is
      Tokomni's own (401, 403, 404, 5xx) pauses the queue.
7. **Picked up:** the router (feature 18) marks the newest ringing lead on that number answered
   (`dialer_answered`, in the background, after the answer to Vapi), and gives the debt agent the
   tenant's figures as before.
8. **Hung up:** the end-of-call report marks the lead done (`dialer_ended`) with the agent's
   `log_call_outcome` and the call's page. A call the agent never logged still counts as one try,
   once.
9. **Stop** cancels everyone waiting; a call already ringing or talking runs to its end.
   **Resume** clears a pause, and the five-in-a-row count starts again from then.

## Interface

- Page: `dashboard/app/(app)/dialer/page.tsx`, server actions `call` (one phone from the row's
  button, `one`, or the ticked `phone` boxes), `stop`, `resume`; each comes back to the page with
  the outcome in the URL (`r=queued|none|hours|stopped|resumed|db`, `n`, `k`, `w`, `b`).
- Database (043): `dialer_queue(text[])`, `dialer_stop()`, `dialer_resume()` for signed-in staff
  (the email is read from the session, never sent); `dialer_expire(timestamptz)`,
  `dialer_cancel_waiting(text)`, `dialer_claim_next()`, `dialer_answered(text, text)`,
  `dialer_ended(text, text, uuid)` and `dialer_count_try(uuid, text)` for the function only.
- Function: `{"message":{"type":"dialer-tick"}}` with `x-homies-secret`, from pg_cron's
  `dialer-tick` job.

## Data

- `dialer_calls`: one row per press per tenant. `status` waiting, sending, ringing, answered, done,
  no_answer, skipped, failed, cancelled; `why`; `pressed_by` (email), `pressed_at`, `sent_at`,
  `answered_at`, `ended_at`; `external_id`, `tokomni_status`, `vapi_call_id`, `interaction_id`,
  `outcome`, `attempt`, `amount`, `name`, `phone`, `resident_id`. Staff read it; only the
  functions write it.
- `dialer_state`: one row, the pause (`paused_at`, `paused_why` streak or tokomni, `resumed_at`)
  and the last tick (`last_tick_at`, `last_error`).
- Writes elsewhere: `residents.handed_over` (through `press_call`), `charges.attempts` and
  `last_call_at` (one try per placed call), `call_outcomes` (a `no_answer` row).

## Files

- `supabase/043_dialer.sql`; `scripts/dialer_setup.py` (read only; `--apply` sets the function's
  Tokomni pair from `.env` and applies 043; `--off` unschedules the tick and cancels everyone
  waiting, the kill switch).
- `supabase/functions/debt-tools/dialer.ts` (pure), `index.ts` (`dialerTick`, `dialerLine`,
  `dialerAnswered`, the end-of-call hook). `scripts/supabase_functions.py` uploads `dialer.ts` and
  pushes the Tokomni pair on a hand `--apply`.
- `dashboard/app/(app)/dialer/page.tsx`, `loading.tsx`, `tabs.tsx`; `dialer/test/` (feature 20,
  moved); `dashboard/lib/dialer-queue.ts` (server), `dialer-board.ts` (pure);
  `components/select-all.tsx`, `auto-refresh.tsx`, `pending-button.tsx` (name and value).
- `scripts/check_dialer_queue.test.ts`: the tick's rules beside the test page's, and the list.

## Acceptance

1. A press on one tester (Ido, in calling hours) puts one waiting row in, a lead goes to Tokomni
   within 15 s, and his phone rings once. Picked up: the debt agent with his figures; the row goes
   answered, then done with the outcome, and links to the call.
2. Two tenants pressed together: the second lead is sent only after the first call ended (or two
   minutes of no answer), never both in List 2 at once.
3. An unanswered call is "no answer" after about 2 minutes, counts one try, and shows in the Calls
   page's no-answer tab.
4. The same tenant pressed again the same day is refused "already called today".
5. Stop with three waiting: all three cancelled, nothing more sent.
6. At 20:00 (Friday 13:00) everyone still waiting is cancelled.
