# 05 — Messy input

**Estimate:** 3d
**Depends on:** [01-identity](../01-identity/feature.md), [02-intake](../02-intake/feature.md)
**Status:** not started

## Purpose

Hold the ticket together when the audio does not cooperate. Residents call from
stairwells, from cars, with a television on, holding a crying child, in accented
Hebrew, at a distance from the microphone. This is the ordinary case, not the
edge case, and it is the centre of the demo.

The governing rule: **never write a confidently wrong ticket.** A missing field
is recoverable. A wrong apartment number sends a technician to the wrong door
and nobody finds out until they knock.

## Behaviour

### The Hebrew numeral normaliser

Every request contains an apartment number, which makes number transcription the
highest-frequency failure surface in the system.

Azure `he-IL` returns Hebrew numerals in inconsistent forms — `עשרים ושתיים`,
`22`, `עשרים ושניים`, `שתיים עשרה` — and gendered agreement varies with what is
being counted. This is normalised in **n8n, over the ASR output**, not in the
prompt. Prompt-level number handling is unreliable in a way that is invisible
until it is wrong, and it cannot be unit-tested.

The normaliser is a pure function with a test table of real spoken forms. It
returns a value and a confidence. Below the confidence floor, the slot is
treated as uncaptured rather than guessed.

### The ladder

**Never re-ask for a filled slot.** Capture is slot-by-slot; a caller who
already gave their building is never asked again, even after an unrelated
recovery.

**Confirm expensive slots only.** Apartment and building are read back. The
description is not — reading a paragraph back to someone who just said it is the
behaviour that makes automated calls unbearable.

**Two strikes per slot, then escalate.** Two attempts, and the second is worded
*differently* from the first. Repeating an identical question at a caller who
did not understand it the first time is the single most infuriating thing a
voice agent does.

> First: "מה מספר הדירה?"
> Second: "אפשר להגיד לי את מספר הדירה ספרה ספרה?"

Digit-by-digit on the retry sidesteps compound-numeral transcription entirely,
which is where most of the errors are.

**Below the confidence floor, do not guess.** Escalate the slot instead. Wrong
beats missing only in the sense that it is worse.

**Two failed slots ends the call gracefully** into
[07-partial-ticket](../07-partial-ticket/feature.md).

### Noise

Sustained low confidence across turns — rather than one bad turn — triggers an
acknowledgement:

> "קשה לי לשמוע אותך, יש רעש ברקע. אפשר לעבור למקום שקט יותר?"

Said once. Repeating it turns a bad connection into a bad experience.

## Interface

No new tool. Two pieces of n8n work sitting in front of the existing ones:

- **`normalise_hebrew_number(text) → { value, confidence }`** — a function node
  with a test table, called before `identify_resident`.
- **Confidence gate** on each slot, deciding capture versus re-ask versus
  escalate.

## Data

Per-slot capture status, confidence, and re-ask counts are written to
`interactions.tool_calls` by [08-instrumentation](../08-instrumentation/feature.md).
That is what turns "it handled noise well" into a number.

## Acceptance

1. The normaliser test table covers at least 30 real spoken Hebrew forms for
   numbers 1–200 and passes on all of them.
2. Apartment number is correct on ten consecutive calls with deliberate
   background noise. Correct or absent — never wrong.
3. No slot is asked for more than twice.
4. The second ask is worded differently from the first, verified across all
   slots.
5. No filled slot is ever re-asked, including after a recovery from a failure on
   a different slot.
6. Sustained noise produces the acknowledgement exactly once per call.
7. Across the whole demo: zero rows with a wrong building or apartment. This is
   the number reported in the close.

## Out of scope

Audio pre-processing or noise cancellation beyond what Vapi provides ·
speaker separation when two people talk · languages other than Hebrew ·
accent adaptation · re-transcribing the recording after the call.
