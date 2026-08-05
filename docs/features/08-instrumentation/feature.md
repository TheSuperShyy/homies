# 08 — Instrumentation

**Estimate:** 1d
**Depends on:** every feature that writes an interaction
**Status:** not started

## Purpose

Turn the demo's closing claim from an impression into a number. Without this the
close is "I think it went well." With it:

> "That was eleven calls. Nine complete tickets, two escalated to a human, zero
> wrong tickets."

It is also how we know whether [05-messy-input](../05-messy-input/feature.md)
actually worked, rather than whether it felt like it did.

## Behaviour

Every tool call appends an entry to `interactions.tool_calls`. Each entry
records what was attempted, what came back, and what it cost in turns:

```json
{
  "tool": "identify_resident",
  "at": "2026-08-21T09:14:03Z",
  "slots": {
    "building": { "captured": true,  "confidence": 0.91, "asks": 1 },
    "unit":     { "captured": true,  "confidence": 0.62, "asks": 2 },
    "name":     { "captured": false, "confidence": null, "asks": 2 }
  },
  "outcome": "matched",
  "duration_ms": 412
}
```

Three things matter and each is used differently:

- **`captured`** — did the slot get filled. Feeds the complete-versus-partial
  count.
- **`asks`** — how many attempts. Two on a slot means the ladder was exercised;
  it is the direct measure of messy-input handling.
- **`confidence`** — what the ASR reported. Only useful in aggregate, and only
  once we know whether the numbers correlate with accuracy at all.

The end-of-call webhook also writes `duration_seconds`, `latency_ms`, the
transcript, the recording URL, and `disposition`.

## Interface

No tool. It is a shared n8n sub-workflow appended to by every other webhook, and
a single SQL query run live at the end of the meeting.

The scoreboard query:

```sql
select
  count(*)                                                as calls,
  count(*) filter (where r.status = 'open')               as complete_tickets,
  count(*) filter (where r.status = 'needs_review')       as escalated,
  count(*) filter (where i.disposition like 'transfer%')  as transfers,
  round(avg(i.latency_ms))                                as avg_latency_ms
from interactions i
left join requests r on r.interaction_id = i.id
where i.created_at > :demo_started_at;
```

**Wrong tickets are not in the query.** They cannot be — no automatic check
knows that apartment 22 should have been 2. That number comes from the room
during Act 2, which is the honest way to get it and, in front of this audience,
the more persuasive one.

## Data

Writes `interactions.tool_calls`, `latency_ms`, `duration_seconds`,
`disposition`, `transcript`, `audio_url`, `started_at`, `ended_at`. All columns
already exist; `tool_calls` is `jsonb not null default '[]'`.

## Acceptance

1. Every call produces exactly one `interactions` row.
2. Every tool call appears in `tool_calls` with slot detail.
3. Re-ask counts match what actually happened, verified by hand against three
   transcripts.
4. The scoreboard query runs in under a second and produces the closing numbers
   live.
5. `latency_ms` is populated on every call, so the pacing claim in
   [04-interruption-pacing](../04-interruption-pacing/feature.md) is evidenced.
6. Rows are attributable to a call and a time, so any disputed number in the
   room can be opened on the spot.

## Out of scope

A metrics dashboard (release 2) · alerting · retention or archival policy ·
automatic detection of wrong tickets, which is not solvable · per-user analytics.
