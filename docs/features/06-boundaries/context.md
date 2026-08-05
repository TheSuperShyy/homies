# 06 — Boundaries and multi-intent — context

## Why this exists

An open mic is an adversarial test. Call centre staff know exactly which
questions break systems, and they will not spend the demo politely reporting
leaks. The agent's ability to say "that is not mine to answer" is what the room
is actually measuring, and it is what makes the answers it *does* give
believable.

It is also the framing that keeps ops staff on side: *it takes the intake call,
anything with judgment in it comes to you.* That sentence is only true if the
agent behaves this way.

## Decisions

**Emergency is folded in here, not treated as a fourth pillar.** The user chose
three hardening areas and left emergency-and-anger judgment out. The
`'emergency'` value already exists in the `urgency` check constraint, so the
branch is roughly half a day of prompt work plus a transfer path rather than a
separate workstream. The case for it as a standalone pillar was made once and
dropped.

**Transfer rather than partial answers, with no exceptions.** A confident wrong
answer about money or contracts is the failure that ends a project. There is no
category of question where guessing is better than transferring, so there is no
threshold to tune.

**Acknowledge every intent aloud, even the ones being transferred.** The silent
drop is the specific failure that destroys trust: the resident believes three
things were logged, one was, and nobody discovers it until they call back angry.
Saying "the bill question needs a person" costs one sentence.

**Multiple requests are read back together, once.** Reading back three separate
confirmations is the phone-tree experience again.

**Anger ends the flow rather than triggering de-escalation.** Scripted empathy
from a bot reads as insulting to someone already angry. One acknowledgement,
then a person. The agent's job is to notice and get out of the way.

**Transfer is logged even though there is nowhere to transfer to.** In the demo
there is no live extension. The `disposition` row is what proves the boundary
was honoured, and it is what the Sheet shows the room.

## Constraints

- No Israeli DID exists, so no real warm transfer during the demo. Telnyx KYC is
  1–3 weeks with rejection common for foreign entities.
- Homies' IVR vendor and extension structure are unknown (PRD §13 #6), so even
  with a number, the transfer target is undefined.
- The agent has no access to technician schedules, contract terms, or account
  balances. Not a policy choice — the data is not there.
- `urgency` is constrained to `low`, `normal`, `high`, `emergency`.

## Known failure modes

- **Staff deliberately probing for a hallucinated answer.** Expected, and the
  point. The prompt must make transferring the low-effort default rather than a
  reluctant fallback.
- **Multi-intent where the second item is only implied** — "and the light" —
  which is easy to miss. Rehearsal target.
- **An emergency that does not use emergency words.** "There is water everywhere
  and it is coming through the ceiling" is a flood without the word flood.
- **Over-transferring.** An agent that transfers ordinary maintenance calls is
  useless in a different way. Watch the transfer rate during the demo; it is one
  of the numbers in [08-instrumentation](../08-instrumentation/feature.md).
- **The transfer that goes nowhere.** In the demo the agent says it is bringing
  in a person and no person appears. Explain this in the opening rather than
  letting it be noticed.

## Open questions

- What is the real escalation path at Homies — an extension, a queue, a named
  duty person? Blocks real transfer (PRD §13 #6) and shapes the wording the
  agent uses.
- Should the agent attempt intake at all during an emergency, or transfer
  immediately with nothing captured? Currently: transfer immediately, capture
  whatever it already has. A dispatcher would probably rather have the building
  than a complete ticket thirty seconds later. Worth asking the ops manager
  directly in Act 2 — they know the answer and it costs one question.
- Is the four-value transfer reason enumeration the right shape, or should
  reasons be free text for the demo and enumerated once we see real ones?
  Enumerated for now, so the scoreboard can count them.

## Related

[The demo design](../../specs/2026-08-02-demo-design.md) ·
[03-recall](../03-recall/feature.md) ·
[08-instrumentation](../08-instrumentation/feature.md) · PRD v2 §7, §13 #6
