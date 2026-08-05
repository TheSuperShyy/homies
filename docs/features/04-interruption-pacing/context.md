# 04 — Interruption and pacing — context

## Why this exists

Call centre staff have heard bad IVR their whole careers and can identify one in
a single turn. If the agent talks over people or leaves dead air, the room stops
listening to what it produces and starts listening to how it behaves — and the
ticket-critique half of the meeting never happens.

This is the only feature in the demo whose entire value is a first impression.

## Decisions

**Barge-in is immediate, not sentence-boundary.** Waiting for a clause to finish
is technically gentler and feels, to a caller, exactly like being ignored.
Hebrew conversation overlaps more than English does; the tolerance is lower.

**Endpointing errs toward waiting.** Two failure modes are available and they
are not symmetric. If we wait too long, latency looks bad. If we cut people off,
the agent looks rude, and callers repeat themselves, which corrupts the
transcript and lengthens the call anyway. Waiting is the cheaper error.

**Fillers before slow tool calls rather than faster tool calls.** Getting the
webhook under 300ms is real work; saying "רגע, אני רושם" costs a prompt line and
removes the perceived gap entirely. Do the cheap thing first and only optimise
the webhook if it is still audible.

**Latency is measured, not estimated.** `interactions.latency_ms` exists for
this. The 1500ms figure came from a live call; every claimed improvement must
come from the same place. This is also why latency tuning was pulled into week 1
of the original plan rather than left to hardening — it is the one technical
risk that could force rework, and it gets answered on the first real call.

## Constraints

- Hebrew STT is slower than English. Azure `he-IL` is the only solid option;
  Deepgram has no Hebrew at all, so there is no faster provider to switch to.
- Voice `he-IL-HilaNeural`. The alternatives are worse.
- Vapi's endpointing controls are what they are; we tune within them rather than
  building our own VAD.
- Under 800ms may not be reachable in Hebrew. The demo does not depend on
  hitting it — it depends on the number being real and stated.

## Known failure modes

- **Endpointing cuts off a caller hunting for their apartment number.** The
  exact moment where a cut-off is most damaging, because it corrupts the
  highest-value field. Worth over-tuning for specifically.
- **Barge-in triggered by background noise** — a TV, another conversation — so
  the agent stops speaking for nothing. Interacts directly with
  [05-messy-input](../05-messy-input/context.md); the two must be tuned
  together, not separately.
- **Latency spikes on the first call after idle.** Cold start. Place a throwaway
  call before the meeting begins.
- **Filler phrases become a verbal tic** if the agent uses one before every
  turn. Only before genuinely slow operations.

## Open questions

- Is 800ms reachable in Hebrew at all, or is the realistic floor closer to
  1000ms? Settled by the first tuning pass. Whatever it turns out to be is what
  we say in the room.
- Does the Vapi assistant need distinct endpointing settings for the
  number-heavy identity phase versus the free-text description phase? Plausible
  — the pause patterns are genuinely different — but not worth building before
  rehearsal shows it matters.

## Related

[The demo design](../../specs/2026-08-02-demo-design.md) ·
[05-messy-input](../05-messy-input/feature.md) ·
[08-instrumentation](../08-instrumentation/feature.md) ·
Vapi assistant `f5c758d8-9246-4f70-89a7-2eea5f1ec9df`
