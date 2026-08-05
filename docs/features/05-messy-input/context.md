# 05 — Messy input — context

## Why this exists

The user's framing, and the reason the demo was rebuilt around it: *how the AI
handles messy audio and inaudible chats, and the limitations on what the bot can
provide.*

A demo that only proves an agent can talk proves nothing anyone doubted. What
the room actually wants to know is what happens when the call is bad — because
in their experience most calls are bad. Answering that question honestly is
worth more than ten clean conversations.

## Decisions

**Number normalisation is n8n post-processing, not prompt engineering.** The
decisive argument is testability. A function node with a table of real spoken
forms can be run a hundred times in a second and will fail loudly on a
regression. A prompt instruction cannot be tested at all, degrades silently when
the model changes, and fails on exactly the inputs nobody thought to try. Given
that every request contains an apartment number, this is the highest-leverage
half-day in the project.

**Two strikes, and the second is worded differently.** One attempt gives up too
early on a recoverable call. Three is where callers start swearing. The
different wording matters more than the count: repeating a question verbatim
signals that nothing was understood and nothing will change.

**Digit-by-digit on the retry.** Compound Hebrew numerals are where the
transcription errors concentrate. Asking for digits sidesteps the failure rather
than retrying into it.

**Confirm location, never confirm the description.** Confirmation cost is not
uniform. A wrong apartment wastes a technician's morning; a slightly clipped
description still routes correctly and a dispatcher can read the rest. Spend
confirmation turns only where an error is expensive.

**Never guess below the confidence floor.** The single rule everything else
serves. It is what makes "zero wrong tickets" claimable in the close, and it is
the claim the room will actually care about. A guessed field is undetectable
until a technician is standing at the wrong door.

**Never re-ask a filled slot.** The most common way voice agents feel stupid.
State is tracked per slot, so a failure on the apartment number never restarts
the building question.

## Constraints

- Azure `he-IL` is the only viable Hebrew STT. There is no better provider to
  switch to and no fallback.
- Hebrew numerals are gendered and agree with the noun being counted, so the
  same apartment number is spoken several legitimate ways.
- Israeli residents call from stairwells, cars, and streets. Ambient noise is
  the normal condition.
- Accented Hebrew is common — Russian, Amharic, Arabic, French first languages
  are all well represented in Israeli buildings.
- Vapi's ASR confidence, where exposed, is a proxy rather than a calibrated
  probability. The floor is empirical.

## Known failure modes

- **Numerals transcribed as words rather than digits.** The primary target of the
  normaliser.
- **`22` heard as `2`, or the reverse.** The classic and most expensive error.
  Read-back plus the confidence floor.
- **Background speech captured as caller speech.** Interacts with barge-in in
  [04-interruption-pacing](../04-interruption-pacing/context.md); tune the two
  together or each will appear to fix and re-break the other.
- **Confidence scores that do not correlate with accuracy.** If the floor turns
  out to be meaningless, fall back to always reading back the number and
  treating a failed read-back as an escalation. Slower, and it always works.
- **The normaliser being wrong is worse than absent,** because it is confident.
  The test table is the guard, and it should include forms we expect to fail so
  the failure is deliberate.

## Open questions

- What confidence value should the floor be? Empirical. Set it from the first
  batch of real Hebrew calls, not from a guess. Too high produces needless
  escalations; too low produces wrong tickets, which is the unacceptable
  direction.
- Does Azure expose per-word confidence through Vapi, or only per-utterance?
  Determines whether the gate can be per-slot or must be per-turn. Per-utterance
  would make the gate blunter and push more calls toward
  [07-partial-ticket](../07-partial-ticket/feature.md).
- How much of the 3-day estimate is the normaliser? Unknown until we see real
  ASR output. This is the softest number in the whole plan and the one most
  likely to move.

## Related

[The demo design](../../specs/2026-08-02-demo-design.md) ·
[01-identity](../01-identity/feature.md) ·
[04-interruption-pacing](../04-interruption-pacing/feature.md) ·
[07-partial-ticket](../07-partial-ticket/feature.md) ·
[08-instrumentation](../08-instrumentation/feature.md)
