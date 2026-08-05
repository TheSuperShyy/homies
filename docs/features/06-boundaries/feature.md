# 06 — Boundaries and multi-intent

**Estimate:** 2d
**Depends on:** [02-intake](../02-intake/feature.md), [03-recall](../03-recall/feature.md)
**Status:** not started

## Purpose

Know what not to answer, and handle a caller who says three things in one
breath. Knowing its own limits is what makes everything else the agent says
trustworthy — and on an open mic, the room will spend most of its effort probing
exactly this.

## Behaviour

### Out of scope

The agent does two things: opens a request, and reports the status of one it
took. Everything else — payments, debts, contracts, complaints about staff,
legal questions, "when is the technician coming" — gets the same shape of
answer:

> "זה משהו שנציג צריך לטפל בו. אני מעביר אותך."

**No hedging, no partial answers, no guessing.** The agent never says "I think"
about a policy question. A wrong answer about money is worse than any number of
transfers.

**No invented facts.** It does not know service charges, contract terms,
technician schedules, or who is on duty. When it does not know, it says so and
transfers.

### Multi-intent

A caller who says *"there's a leak in the bathroom, and also the lobby light is
out, and by the way I got a bill I don't understand"* gets all three
acknowledged:

1. Open a request for the leak.
2. Open a second request for the light.
3. Name the third as needing a person, and transfer.

**Acknowledge everything, act on what is in scope, transfer the rest.** The
failure to avoid is silently dropping items two and three — that is how a
resident ends up believing something was logged when it was not.

Requests are read back together, once, not one at a time.

### Emergency

Folded in here rather than being a separate workstream, because `urgency`
already carries `'emergency'`.

Gas, flooding, fire, no water to the building, anything involving injury:

- `urgency` is set to `emergency` on the row.
- The agent says a human is being brought in and transfers immediately.
- It does not complete the normal intake script first.
- For life safety it names the emergency services rather than implying Homies is
  the right call.

An emergency that produces a tidy ticket and no human is a failure regardless of
how good the ticket is.

### Anger

A caller who is furious is not argued with, not de-escalated with scripted
sympathy, and not kept in the flow. One acknowledgement, then a transfer offer.
Repeated frustration means the agent stops trying to complete the ticket.

## Interface

**`transfer_to_human`**

| Field | Type | Required | Notes |
|---|---|---|---|
| `reason` | string | yes | out_of_scope, emergency, caller_request, repeated_failure |
| `context` | string | yes | what was captured before the transfer |
| `call_id` | string | yes | Vapi call id |

In the demo, transfer means a spoken handoff plus a logged row — there is no
phone number to warm-transfer to. The row is what proves the boundary was
honoured.

## Data

Writes `interactions.disposition` as `transfer:<reason>` — for example
`transfer:emergency`. The prefix is what lets the scoreboard in
[08-instrumentation](../08-instrumentation/feature.md) count transfers with a
single predicate; the suffix is what makes the count explainable when someone
asks which ones.

Any request created before the transfer is written normally, with
`urgency = 'emergency'` where it applies.

## Acceptance

1. Ten out-of-scope questions produce ten transfers and zero attempted answers.
2. A three-intent call produces two requests, one transfer, and acknowledges all
   three items aloud.
3. An emergency transfers before completing intake, and the row carries
   `urgency = 'emergency'`.
4. The agent never states a service charge, contract term, or technician
   schedule.
5. An angry caller is offered a person within two turns.
6. Every transfer writes a `disposition` of the form `transfer:<reason>`, and
   the scoreboard's transfer count matches the number of transfers the room
   witnessed.

## Out of scope

Actual warm transfer to a live extension (needs Telnyx and Homies' IVR —
release 1) · callback scheduling · complaint tickets as a distinct type
(release 1, PRD §7) · sentiment scoring beyond obvious anger cues.
