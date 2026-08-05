# 08 — Instrumentation — context

## Why this exists

The demo closes on a claim. If the claim is "it handled the messy calls well,"
the room has to take our word for it, and they have no reason to. If the claim
is "eleven calls, nine complete, two escalated, zero wrong," they can check it
against their own memory of the last thirty minutes — and they will, which is
what makes it land.

It is also the only way to know whether the three days spent on
[05-messy-input](../05-messy-input/feature.md) bought anything.

## Decisions

**`interactions.tool_calls` rather than new tables.** The column exists, it is
`jsonb`, and the demo does not need queryable slot-level history. Adding tables
for a measurement we will redesign after the first real week is premature.

**Per-slot, not per-call.** "The call failed" is not actionable. "The apartment
number needed two asks on six of eleven calls" points directly at the
normaliser. The slot is the unit of failure in this system, so it is the unit of
measurement.

**Re-ask count is the headline metric, not confidence.** Asks are ground truth —
they happened, they cost the caller time, and they are countable. Confidence is
a vendor number of unknown calibration. If they disagree, believe the asks.

**Wrong tickets are counted by humans, in the room.** No automatic check can
know a transcribed apartment number was wrong. Asking the ops staff to supply
that number in Act 2 is honest, and it is more persuasive than a self-reported
figure would be — they trust their own count.

**One live query, not a dashboard.** Running SQL in front of the room and
reading the result is faster to build and more credible than a chart, because a
chart could show anything.

## Constraints

- `tool_calls` is `jsonb not null default '[]'::jsonb`. Appending from n8n means
  a read-modify-write; concurrent calls on the same interaction would race,
  though within one call the tools are sequential so it is not a practical
  problem at demo scale.
- `interaction_id` on `requests` is backfilled by the end-of-call webhook, so
  the scoreboard join only works after the call ends. Fine for a close, wrong
  for anything live.
- Vapi's end-of-call payload is the source for latency, duration, transcript and
  recording. If it does not fire, the row is thin.

## Known failure modes

- **The end-of-call webhook not firing,** leaving an interaction with no latency
  or transcript. Check after the first rehearsal call, not on the day.
- **Ambiguous re-ask counting.** Does a clarification count as a re-ask? Define
  it once — an ask is any question targeting a slot that is not yet captured —
  and apply it consistently, or the headline number means nothing.
- **The scoreboard contradicting the room's impression.** If the numbers look
  better than the meeting felt, believe the room. The instrumentation is
  measuring what we thought to measure, and the gap between that and what
  mattered is exactly what Act 2 exists to find.
- **Rehearsal calls polluting the demo count.** The query filters on
  `demo_started_at`; set it deliberately.

## Open questions

- Is per-slot confidence available from Azure through Vapi, or only per
  utterance? Determines whether the confidence field is meaningful or
  decorative. Same question as
  [05-messy-input](../05-messy-input/context.md) — answered once, used twice.
- Does `tool_calls` need a defined schema, or is loose JSON enough until the
  metrics CRM is built? Loose for now. It becomes a real problem the moment
  anything queries it, which is release 2.

## Related

[The demo design](../../specs/2026-08-02-demo-design.md) ·
[04-interruption-pacing](../04-interruption-pacing/feature.md) ·
[05-messy-input](../05-messy-input/feature.md) ·
[001_slice_schema.sql](../../../supabase/001_slice_schema.sql) lines 43–69
