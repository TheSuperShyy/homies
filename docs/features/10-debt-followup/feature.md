# 10 — Outbound debt follow-up

The agent calls a resident about an unpaid building committee fee, reads the
caller's posture turn by turn, and either settles the payment or hands over
cleanly. It never takes money on the line and never argues twice.

The spoken behaviour is defined in [prompt.md](prompt.md). The reasoning behind
it is in [context.md](context.md). This file is the contract around it.

## Behaviour

1. **Nothing is called blind.** The queue is built from the database before any
   dialling: apartments with an unpaid month, minus standing orders, minus
   anyone whose handover protocol is unsigned, minus anyone called in the last
   few days, minus anything outside legal calling hours.
2. **The agent identifies itself as a digital assistant**, by a name belonging to
   no real employee, and names the building.
3. **It states the month and the amount, once**, then stops and listens.
4. **It re-reads the caller's posture before every turn** — open, friction, hot —
   and moves with them in both directions, except that hot is a floor.
5. **Budgets are per call and never reset:** one explanation, one standing-order
   offer, two clarification attempts.
6. **Fixed paths override posture entirely:** not handed over, not the account
   holder, hardship, no Hebrew, voicemail.
7. **Every call writes a row**, including voicemail, wrong party and no answer.

## Tool contract

| Tool | When | Must not |
|---|---|---|
| `send_payment_link` | they agree to pay, or while transferring a hot call | fire on a hardship transfer, or on a disputed payment |
| `log_promise_to_pay` | they give a date | invent or round the date |
| `request_standing_order` | they say yes, once per call | fire after a decline |
| `log_disputed_payment` | they claim to have paid | be accompanied by a payment link |
| `open_request` | they raise a maintenance issue | be claimed in speech before the call actually runs |
| `flag_not_handed_over` | keys not received / protocol unsigned | be reversible by the agent |
| `transfer_to_human` | reasons: `hardship`, `dispute`, `distress`, `language`, `not_understood`, `caller_request` | — |
| `log_call_outcome` | every call, always | omit the highest posture reached |

## Data

**The schema for this does not exist yet.** [001_slice_schema.sql](../../../supabase/001_slice_schema.sql)
has `residents`, `requests` and `interactions` — there is no debt, payment, or
call-attempt table anywhere. Migration `004` must add, at minimum:

- a per-apartment, per-month charge with an amount and a settled flag
- a handover status on `residents`, since it gates every call
- an attempt log — timestamp, outcome, posture reached — keyed to the charge
- a promise-to-pay record with the date the resident gave

`interactions` already carries `audio_url`, `latency_ms`, `tool_calls` and
`disposition`, so the recording and the instrumentation need no change. Write the
transfer disposition as `transfer:<reason>` to match the scoreboard query in
[08-instrumentation](../08-instrumentation/feature.md).

## Acceptance criteria

1. No call is placed for an apartment whose handover protocol is unsigned. Two of
   the four sample calls would have been prevented by this alone.
2. No call is placed without both a month and an amount.
3. The amount is never spoken to anyone who is not the account holder — not to a
   spouse, not to voicemail, not to whoever picked up.
4. Card details are never requested, accepted, repeated, or acted on.
5. The agent explains the monthly-collection policy at most once per call,
   measured across the whole call and not per posture.
6. Every call that reaches `hot` ends in a transfer, with no exceptions, even
   where the caller later offers to pay.
7. A maintenance issue raised mid-call produces a `requests` row. Zero silent
   drops.
8. Hardship always transfers. The agent never offers a plan, a delay, or a
   waiver.
9. Every call writes an outcome row, including voicemail, wrong party and no
   answer.
10. Zero calls in which the agent mentions a warning, legal action, the apartment
    owner, or any consequence of not paying.

Criterion 5 is the one that needs deliberate testing, because it only fails on a
call where the caller cools down and heats up again — which is the shape of
sample call 5 and will not appear in a scripted rehearsal.

## Out of scope

Taking payment on the call · agreeing a payment plan · any language but Hebrew ·
deciding that a warning is due · two-way sync with OXS · SMS-only dunning
campaigns · anything that decides *who* to call beyond the queue rules above.

## Estimate

**4d**, and it is a soft number — it assumes the payment link already exists as a
service. If `send_payment_link` has to be built against a provider, add 2–3d, and
the provider choice is not made.

Excludes migration `004`, which is unsized until the charge model is agreed with
Homies.
