# 14 — One call per resident

**Estimate:** 3d
**Depends on:** 10-debt-followup, migration 012
**Status:** BUILT and deployed, 11 Aug — freeze lifted by the client the same
day. Migration 013 applied; Edge Function v15 live; n8n router updated and
probed; Hebrew assistant synced; demo page groups Dana into one call.

**One cut from the spec below, on the client's instruction:** apartments that
owe nothing are not counted or spoken. *"We don't need to look for the
apartments that owe nothing... just the apartment that has an open balance."*
So there is no `apartments` table, no OXS sweep change, no `apartments_held`,
and the opening does not say how many flats somebody holds — only which ones owe.
Sections below that describe the counting are the original spec, kept for when
the client wants it; everything else is as built.

## Purpose

Today the call queue is one row per charge, which since migration 012 means one
row per **apartment per month**. An owner of two flats owing four months each is
eight rows, and a runner iterating the queue places eight calls to one person
about one debt. That is not a collection call, it is harassment with a schedule.

This makes the unit of a call a **person**. One call, every apartment they hold,
every month still open, one total, settled in one conversation.

What breaks if it does not exist: the first real campaign rings the two known
multi-apartment owners repeatedly, and each call names an amount without naming
which flat it is for — which the 11 Aug demo call did, leaving the resident
unable to tell which of her two July payments was being discussed.

## Behaviour

The agent opens knowing three things, and says all of them unprompted
(*"how many apartments they hold altogether" was a fourth, cut — see Status*):

1. **Which apartments have an open balance** — named, always. Never "the July
   payment" to somebody with two July payments.
2. **The total across every open apartment and month.**
3. **Which months are open**, and the per-apartment split when asked.

The call then settles all of it: a promise to pay, a payment link, a dispute, or
a refusal — for the whole balance, or for one named apartment.

### The opening, in substance

State the building, the apartments with something open, the months, and the
total. Apartments that owe nothing are not on the call at all — the agent does
not know about them and must never imply that it does.

Then the same four responses the current prompt already handles — will pay, has
paid, disputes, refuses — except each may now be about **one apartment or all of
them**, and the agent must carry which.

### "That flat was never mine"

The agent does **not** act on this. The system holds a record saying the
apartment is theirs; a verbal claim on a collection call does not outrank it,
and treating it as though it does turns "this isn't my flat" into the phrase
that ends any call about money.

So the agent says plainly that the system shows the apartment against them, once
— not an argument, and not a second attempt at the same sentence — and offers
the office:

> Shall I pass this to the office so they can check it and come back to you?

**It never says anyone is being put through.** `transfer_to_human` connects
nobody; it writes the call to the office. The existing rule stands.

On acceptance: `transfer_to_human`, and **the charges for that apartment move to
`pending_charge`**. That pauses them — `v_debt_call_queue` only emits `unpaid` —
so the resident is not rung again next week about the thing the office is still
checking, while nothing about the ownership record has been changed on their
say-so.

`flag_not_handed_over` is **not offered to the agent** under this feature. See
Out of scope.

### The apartment is always named

`{{unit}}` is currently "not spoken unless the caller asks"
(`docs/features/10-debt-followup/prompt.md`). That flips. An amount without an
apartment is unverifiable for anybody with more than one, and the resident
cannot ask their way out of it — on 11 Aug the caller asked which building and
was refused, because the model read the question as a challenge to its
legitimacy and fired the anti-scam rule.

That rule is narrowed here: **the building, apartment, month and amount of the
charge being discussed are always sayable to a confirmed account holder.** What
stays forbidden is reading details back to *prove who you are* to an unverified
caller. The prompt already accepts saying the building to an answering machine
it cannot verify at all, so refusing it to the confirmed resident was never
consistent.

## Interface

### The queue

**As built:** `v_debt_call_queue_person` (migration 013), one row per resident,
layered ON TOP of `v_debt_call_queue` rather than replacing it — the eligibility
predicate stays written once and the charge view keeps serving the dashboard.
`apartments_held` was cut with the counting; everything else in the table below
exists, plus `money_say()` (no rounding — `to_char FM999999` would have said
₪1,972 about a charge of ₪1,971.80) and `hebrew_list()` (maqaf before digits:
`ו-9`, never `ו9`).

Every spoken phrase is composed **in the view**, not by the model — the same
reason `v_debt_call_queue` already composes the Hebrew month name in SQL.

| Field | Type | Notes |
|---|---|---|
| `resident_id` | uuid | |
| `phone` | text | still the key every write lands on |
| `first_name` | text | given name only |
| `gender` | text | |
| `card_last4` | text | empty string when none |
| `building` | text | joined when the apartments span more than one |
| `apartments_held` | int | **all** apartments, settled included |
| `apartments_owing` | text[] | units with an open charge |
| `charges` | jsonb | `[{charge_id, unit, period, amount}]` — the whitelist |
| `amount` | text | total across every open charge |
| `apartments_phrase` | text | composed, e.g. `דירות 4 ו-9` |
| `breakdown_phrase` | text | composed, e.g. `450 על דירה 4 ו-780 על דירה 9` |
| `months_phrase` | text | composed, e.g. `יולי` or `אפריל עד יולי` |
| `attempt` | text | |

A row appears only when every field a call needs is present, which is the
existing view's contract and the reason it refuses to emit a row without an
amount or a month.

### The tools

`ctx` gains the `charges` array. Tools split in two:

**Call-level** — `log_promise_to_pay`, `send_payment_link`,
`request_standing_order`, `log_call_outcome`, `transfer_to_human`. These write
against **every** charge on the call. No new argument; the agent supplies
nothing it does not already supply.

**Apartment-level** — `log_disputed_payment` and, if it is ever re-offered,
`flag_not_handed_over`. These gain one optional argument:

| Field | Type | Required | Notes |
|---|---|---|---|
| `unit` | string | no | The apartment the resident named. Omitted means all of them. |

**The agent selects; it never supplies.** `unit` is resolved server-side against
the `charges` array attached to the call. A unit not on that list is refused with
`{ok: false, error: "apartment not on this call"}`. So the rule this whole file
layer exists to enforce still holds: the model cannot invent a charge, redirect
one, or be talked into collecting a different debt — it can only point at
something the runner already put in front of it.

Returns are unchanged in shape, with a `charges_written` count added.

## Data

**No new table.** The `apartments` table the original spec called for existed
only to answer `apartments_held`, and that was cut with the counting. If the
counting ever comes back, the table comes back with it — `oxs_arrears.py`
already iterates every apartment in every building's payment records and merely
declines to write down the settled ones.

`residents.unit` is display-only and **not** authoritative for anything, the
same status `charges.unit` gave it on 11 Aug.

Reads: `charges`, `residents`. Writes: unchanged tables, more rows per call.

## Acceptance

Verified 11 Aug: 1–4 against the live data (the two real multi-apartment owners,
gate flipped inside a rolled-back transaction), 8 and the refusal half of 7/12
against the live n8n webhook. 5, 6, 9, 10, 13 need the campaign runner or a
placed call, which still do not exist.

1. A resident with one apartment in arrears produces exactly one queue row, and
   the call wording differs from today's only by naming the apartment.
2. A resident with two apartments in arrears produces exactly **one** queue row.
3. For any queue row, `amount` equals the sum of `amount` across its `charges`.
4. `apartments_owing` names every apartment with an open charge and no others.
   (*`apartments_held` cut with the counting.*)
5. Placing calls for N eligible residents results in N calls, not one per charge.
   Measured against the two known multi-apartment owners: 2 calls, not 10.
6. A promise to pay on a two-apartment call writes `promises_to_pay` rows
   covering every charge on that call.
7. `log_disputed_payment` with `unit: "4"` sets only apartment 4's charge to
   `disputed`; apartment 9's stays `unpaid`.
8. `log_disputed_payment` with a unit not on the call returns `ok: false` and
   writes nothing.
9. `log_disputed_payment` with no unit sets every charge on the call to
   `disputed`.
10. Ten consecutive multi-apartment calls produce zero rows against a charge that
    was not on the call that produced them.
11. `residents.handed_over` is not written by any part of this feature, on any
    path, including a resident stating an apartment is not theirs.
12. A resident claiming an apartment is not theirs produces a
    `transfer_to_human` row and moves that apartment's charges to
    `pending_charge`; the other apartment's charges stay `unpaid`.
13. That resident does not reappear in the queue for the paused apartment, and
    **does** still appear for the apartment they did not contest.
14. No reply on that path contains a phrase promising a live transfer.

## Out of scope

- **`handed_over` becoming an apartment-level fact.** It is described in the
  schema as "false when the apartment has not been handed over" but lives on the
  resident, so setting it for one flat would stop calls about every other flat
  that owner holds — the same shape as the bug migration 012 fixed. It is also
  the interlock keeping the queue empty, so it moves on its own change, with its
  own verification and its own approval.

  **This feature no longer needs it to move.** Because the agent does not act on
  an ownership claim at all, nothing automatic writes that flag, and the
  multi-apartment blast radius never opens. `flag_not_handed_over` comes off the
  agent's toolset — the same retirement `open_payment_ticket` got on 4 Aug, and
  for the same reason: a tool the agent should not be deciding to use is a tool
  it should not be offered. The handler stays in the Edge Function so a stale
  assistant still gets an answer rather than an error.

  Whether a person should later flip that flag per apartment is a real question
  and belongs with the change that moves it.
- **Payment link delivery.** Still nothing sends them; feature 10 owns that.
- **Placing any call.** No phone number exists, every resident is
  `handed_over = false`, and a campaign needs explicit approval every time.
- **The campaign runner itself.** This defines the queue it reads and the tools
  it calls, not the thing that iterates them.
