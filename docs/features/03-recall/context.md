# 03 — Recall — context

## Why this exists

"What is happening with my request" is one of the highest-volume calls the
centre takes and one of the lowest-value: a human looks something up and reads
it aloud. It is also, in the demo, the beat that proves the row was real. Act 1
shows a row appearing on a screen, which anyone can fake. Act 3 shows a
different person retrieving it by voice.

## Decisions

**Only requests the system itself took.** This looked like a limitation forced
by the missing OXS bridge, and it is — but scoping to our own rows turns
`get_request_status` from a data-integration problem into one webhook against a
table we already own. That is the difference between one day and a fortnight.

**Say the boundary out loud on the call.** "I only see requests opened through
me" is a sentence the agent says to real residents, not just a demo caveat. Ops
staff will test it within the first two calls; discovering it themselves after
we hid it is much worse than hearing it from the agent.

**Location lookup, not reference lookup, is the primary path.** People do not
keep reference numbers. Designing around the reference would produce a flow that
works in rehearsal and fails in the field. The reference stays as the fast path
for the minority who have it.

**No estimated completion times, ever.** The agent has no dispatcher data, no
technician calendar, and no authority to commit Homies to anything. "Soon" is a
promise. This is the same restraint as the nightly-status freshness caveat in
PRD v2 §2.2, applied to a case where the data happens to be live.

**Partial tickets are excluded from recall.** A `needs_review` row has no
usable description. Reading one back would say "we have a record that we could
not hear you," which converts a save into an embarrassment.

## Constraints

- Requests created in OXS by staff are invisible until the nightly Sheets import
  exists. Release 2.
- Status values are `open`, `in_progress`, `resolved`, `cancelled`, plus
  `needs_review` once migration 003 lands.
- Nothing writes `in_progress` yet — no dispatcher workflow exists — so every
  request in the demo is `open`. Honest, and slightly dull.

## Known failure modes

- **Caller asks about a request opened with a human.** The most likely real
  question and the one we cannot answer. Handled by the boundary sentence plus a
  transfer.
- **Caller misreads the reference.** Falls back to location lookup rather than
  looping on the number.
- **Every demo request shows `open`,** which can read as "nothing happened."
  Worth pre-empting verbally rather than faking an `in_progress` row. Faking it
  would be the one dishonest thing in the demo.
- **A resident treats the recall as a complaint channel** — "it has been two
  days and nobody came." Out of scope here; belongs to
  [06-boundaries](../06-boundaries/feature.md) and ends in a transfer.

## Open questions

- Should recall include `resolved` requests from the last few days? A resident
  chasing something marked resolved that plainly is not resolved is a real and
  common case. Excluded for the demo to keep the surface small; revisit for
  release 1.
- Is there a privacy problem in reporting a request by apartment to whoever
  calls from that apartment? Probably not for maintenance, plainly yes for
  anything payment-related. Needs an answer before `verify_identity` flows ship.

## Related

[The demo design](../../specs/2026-08-02-demo-design.md) ·
[02-intake](../02-intake/feature.md) ·
[07-partial-ticket](../07-partial-ticket/feature.md) · PRD v2 §2.2
