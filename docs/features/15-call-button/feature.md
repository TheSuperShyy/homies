# 15 — The Call button

**A person presses Call next to a resident on the Debts page; the debt agent
rings that one resident, once, now.** That is the whole of outbound for
release 2 as decided on 25 Aug. Nothing dials on its own.

## What it does

1. On `/debts`, every row that owes money carries a PIN field and a **call**
   button — when `CALL_PIN` is set in Vercel. Without it the column does not
   exist.
2. The press posts to a server action. The action:
   - checks the PIN;
   - calls `press_call(phone)` in Postgres (migration 024), which marks the
     resident `handed_over = true` and returns their composed call from
     `v_debt_call_queue_person` — or NULL if they owe nothing, are on
     do-not-call, or have had four attempts;
   - places the call through Vapi's `POST /call` with the same
     `variableValues` the browser demo composes (name, gender forms, building,
     apartments / breakdown / months phrases, amount, the charges whitelist,
     callback number, spoken email);
   - comes back to the same page with the result in the URL.
3. The page shows one line: *Calling +972… now — call `<id>`*, or *Did not
   call: <reason>*. The finished call appears under Calls when it ends, written
   by the existing end-of-call workflow.

## What it needs that does not exist yet

| Needed | Where | State |
|---|---|---|
| An Israeli phone number in Vapi | `VAPI_PHONE_NUMBER_ID` in Vercel | being ordered from Omnitelecom; until set the button reads "no number yet" |
| The PIN | `CALL_PIN` in Vercel | owner sets it; nothing renders without it |
| Vapi key on the server | `VAPI_PRIVATE_KEY` in Vercel | not yet added |
| Homies' bank-transfer line | `HOMIES_ALT_PAYMENT` | demo text until Homies confirms |

## What it deliberately does not do

- No queue, no runner, no schedule, no retries. One press, one call.
- No repeat protection beyond the view's four-attempt cap; no calling-window
  check; no do-not-call management UI. Deferred by the owner on 25 Aug.
- No audio recording — transcript only, switched off on all assistants 25 Aug.

## Files

- `dashboard/lib/call.ts` — the three gates and the Vapi call
- `dashboard/app/debts/page.tsx` — the column, the form, the result line
- `supabase/024_press_call.sql` — the one write the anon key gains
