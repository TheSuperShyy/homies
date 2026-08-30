# 04 — Interruption and pacing

**Estimate:** 2d
**Depends on:** [02-intake](../02-intake/feature.md)
**Status:** not started

## Purpose

Make the agent feel like something worth talking to in the first ten seconds.
Nobody in the room evaluates ticket quality until they have decided the call is
tolerable, and that decision is made almost entirely on turn-taking.

## Behaviour

**Barge-in.** The caller speaking stops the agent mid-word. Not at the end of
the sentence, not after a beat — immediately. Israeli phone conversation
overlaps constantly; an agent that talks through interruption reads as broken
within one turn.

**Endpointing tuned for thinking, not for silence.** A caller pausing to recall
their apartment number is not finished speaking. Too-eager endpointing produces
the interruption-of-the-caller failure, which is more irritating than latency.
The setting is tuned against real Hebrew calls, not left at the default.

**A filler before a slow tool call.** When `open_request` will take a moment,
the agent says "רגע, אני רושם" rather than going silent. Silence on a phone
call reads as a dropped connection and callers start saying "הלו?".

**Resume, do not restart.** After an interruption the agent continues from where
it was. It does not repeat its last full sentence.

**Latency budget.** Voice-to-voice under 800ms, measured on real Hebrew calls
into `interactions.latency_ms`. Currently ~1500ms. The known levers: a smaller
model, endpointing configuration, and TTS settings. Under 800ms is a target, not
a promise — Hebrew STT carries a real tax.

## Interface

None. This feature is Vapi assistant configuration plus prompt work; it exposes
no tool.

Assistant `7752c6bb-89e9-49f3-aaf4-154ecc65cdff`, Azure `he-IL` STT, voice
`he-IL-HilaNeural`. Live as of 3 Aug 2026; config and the reasoning behind each
turn-taking number are in [demo-inbound.md](../../assistant/demo-inbound.md).

This previously named `f5c758d8-…`, which is a different assistant entirely —
an English collections test that was never Hebrew and never had these settings.

## Data

Writes `interactions.latency_ms` via the end-of-call webhook. That column is the
before-and-after measurement for every change made here; a tuning pass with no
recorded number did not happen.

## Acceptance

1. Speaking over the agent stops it inside one word, on ten consecutive
   attempts.
2. A three-second mid-sentence pause does not cause the agent to take the turn.
3. Median voice-to-voice latency under 800ms across ten Hebrew calls, recorded
   in `interactions.latency_ms`. If the median lands between 800ms and 1000ms,
   ship it and say the real number — it is still a large improvement on 1500ms.
4. No silent gap longer than 1.5 seconds during a tool call.
5. After an interruption the agent resumes rather than repeating itself.

## Out of scope

Emotion or tone detection · adjusting speaking rate to the caller · multi-party
call handling · noise suppression, which belongs to
[05-messy-input](../05-messy-input/feature.md).
