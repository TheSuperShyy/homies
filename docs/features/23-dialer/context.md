# The dialer on the dashboard: context

**Asked 25 Nov 2026 by the owner:** *"ok in the dashboard we need to have an actual dialer section
there not just the dialer test"*. The design was given in chat and the owner said *"ok build it"*.

**Why a queue on our side, and not a batch into List 2.**
- Omni's lead API takes an array, so a list could go into List 2 in one request. It must not:
  List 2 dials two leads per free agent and 208 takes one call at a time, so the second tenant
  who answers is lost (the three 9 Nov leads).
- Omni's dialer has no calling hours and the API has no remove call, so a list sent at 19:50
  would ring past 20:00 and could not be taken back. Held on our side, Stop and the end of the
  hours cancel what has not gone yet.
- So one lead at a time, and the next only once the line is quiet. List 2's ratio no longer
  matters: there is never a second lead in it.

**Why the line is read from Vapi.** Our own rows know only our leads. A press-9 caller or a test
call from `/dialer/test` also holds 208, and while it does Omni holds our lead and rings it when
208 frees up. So a ringing lead is given up 2 minutes after the send and 90 s after the line went
quiet, whichever is later, and nothing is sent while any call on 208 has not ended. An unreadable
line sends nothing and gives up on nothing.

**Why the tick is pg_cron and the function, not the page.** The owner's design: the calling goes
on with the page closed. The function already holds the Vapi key and runs the router; pg_cron
already pings it every 15 s for keep-warm (041), with the same vault secret. The job's WHERE is
checked in the database, so an empty queue costs no function call; a busy one costs four a minute
(the free plan's 500,000 a month has room: keep-warm is about 173,000).

**Why "no answer" counts as a try.** The owner's design. Every placed call is one try on the
tenant's open charges, counted once: by the agent's `log_call_outcome` when it ran (as before),
else by the dialer when the call is over. `bump_charge_attempt`'s own comment (006) said the
campaign runner should own this, because it knows a call was placed when the agent never ran.

**Why five unanswered in a row pause it.** From our side "nobody picked up" and "Omni's dialer
never dialled" look the same (9-12 Nov: 208 marked disconnected, every lead waited). Five in a
row is the signal that something is down, before every tenant in the queue loses a try to it.
With real tenants many will not answer, so a session may pause on bad luck; Resume restarts the
count. A Tokomni refusal that is not the lead's own (401, 403, 404, 5xx) pauses too, rather than
refusing the whole queue one by one.

**Why one row per phone.** One ring reaches everyone on the number. The debt agent is handed every
flat the number owes on (feature 14). Two tenants who both owe on one number get the incoming
agent from the router, so the dialer skips that number rather than ring it.

**Why no PIN.** The owner's design. The dashboard has a login per person, and each row records
who pressed (from the session, not from the form). The Debts page keeps its PIN on its own button.

**Why cancel at the end of the hours instead of carrying over.** A queue left waiting overnight
would start ringing tenants at 09:00 with nobody having pressed that day.

## Constraints

- One bot extension (208), one call at a time. More extensions would allow calls in parallel;
  not ordered.
- The dialer's caller ID is the office's own number, 077-6687949 (12 Oct). Calling many tenants
  about money from it risks spam tags on the office line (CONTEXT, 12 Oct).
- **Calling hours are ours, not yet Homies' or the law's:** the PRD (§13 #6) says the legal
  calling hours must be confirmed with Homies before the first real outbound call.
- Ido, the test tenant, is on try 3 of 4 (read 25 Nov): one real call left before he leaves the
  debt call list. `bk_reset_attempts.py --apply` resets the test building.

## Known failure modes

- **Omni's dialer accepts a lead and never dials it** (208 marked unavailable on their side,
  12 Nov): the lead shows "no answer" after 2 minutes, one try is counted, and five in a row pause
  the queue. Omni's call log is the only proof; we hold no login for it.
- **The router's mark does not land:** the end-of-call report still finds the newest ringing lead
  on that number and closes it.
- **No end-of-call report:** after 20 minutes on the line the lead is closed as done, so the queue
  moves on; a late report still fills it in.
- **A tick dies between taking a lead and Tokomni's answer:** after 2 minutes the lead is failed,
  not a try. If it had in fact gone in and rang, the router still marks it answered.

## Ruled out

- Moving the Debts page's Call button to the dialer: not asked; it still goes to Vapi's phone
  number, which does not exist.
- A server-side Excel or CSV upload: the debt list is already in the database.
- Retrying a no-answer the same day: at most one call a day per tenant.

## Related

- `docs/features/18-dialer-routing/`, `docs/features/20-dialer-test/`, `docs/features/15-call-button/`
- CONTEXT.md, the Omni and dialer section; `local/omnitelecom/` for Omni's emails
