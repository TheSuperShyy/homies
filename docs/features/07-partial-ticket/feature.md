# 07 — Partial ticket

**Estimate:** 1d (including the schema migration)
**Depends on:** [02-intake](../02-intake/feature.md), [05-messy-input](../05-messy-input/feature.md)
**Status:** not started — **blocked on migration 003**

## Purpose

Guarantee that every call produces a visible row. When the audio is unusable and
the ladder in [05-messy-input](../05-messy-input/feature.md) has run out, the
agent does not fail — it saves what it has and hands the call to a human with
enough to work from.

Without this, an open mic can produce silence, and silence in front of the room
that has to adopt this system is the worst available outcome.

## Behaviour

Triggered when two slots have exhausted their attempts, or when confidence stays
below the floor across several consecutive turns.

The agent says what it is doing — it does not simply hang up:

> "קשה לי לשמוע אותך. שמרתי את מה שהצלחתי לקלוט וגם הקלטה, ונציג יחזור אליך."

Then it writes a `requests` row containing:

- every slot that *was* captured, and nothing invented for the rest
- `status = 'needs_review'`
- `urgency` left at its default unless something clearly signalled otherwise
- a link to the recording, through the interaction

The row appears in the Sheet like any other, visibly flagged. That visibility is
the point: a human sees it within a working day rather than discovering a
voicemail nobody transcribed.

**A partial ticket never guesses.** An uncaptured field is empty. The whole
value of the row is that a human can trust the parts that are filled in.

## Interface

**`save_partial_request`**

| Field | Type | Required | Notes |
|---|---|---|---|
| `building` | string | no | whatever was captured |
| `unit` | string | no | whatever was captured |
| `type` | string | no | only if genuinely inferred |
| `description` | string | no | partial transcript is acceptable here |
| `resident_id` | uuid | no | usually null |
| `call_id` | string | yes | links the recording and transcript |
| `captured_slots` | array | yes | which slots succeeded, for the scoreboard |

Returns:

```json
{ "reference": "255-1042-26", "request_id": "uuid", "status": "needs_review" }
```

The reference is still generated and still read aloud if the caller can hear it.
There is no reason a partial ticket should be un-quotable.

## Data

Requires **migration `003_partial_tickets.sql`**, which must run before this
feature can exist at all:

| Column | Now | After |
|---|---|---|
| `requests.type` | `not null` | nullable |
| `requests.description` | `not null` | nullable |
| `requests.building` | `not null` | nullable |
| `requests.status` | 4 values | adds `'needs_review'` |

Three NOT NULLs mean a call where the building was inaudible cannot be written
at all today — precisely the call that most needs a row.

`interactions.audio_url` and `interactions.caller_phone` already exist, so the
recording and callback number need no schema change.

### The recording must be re-hosted — pending change

**Vapi retains call recordings for 14 days on the Build plan**, and extending to
60 days is a $1,000/month add-on, so buying out is not an option. See
[the Vapi account notes](../../reference/Homies-Vapi-Account-Notes.md).

If `audio_url` points at Vapi's storage, every partial ticket older than two
weeks becomes a row nobody can act on — and the tickets that most need a human to
listen are exactly the ones that sit longest. That defeats the entire feature.

**Required:** n8n copies the recording into Supabase Storage on the same branch
that writes the row, and `audio_url` points at our copy. This changes the tool
contract — `save_partial_request` fetches and re-hosts rather than storing
whatever Vapi handed it. Roughly an hour of work.

*Not yet applied to the interface table above.* Do this before building the tool,
not after.

## Acceptance

1. Migration 003 applies cleanly and existing rows are unaffected.
2. A deliberately unintelligible call produces a row with `needs_review` and no
   invented values.
3. The recording is reachable from the row, **and is hosted by us, not by Vapi**
   — verify by checking the URL's host, not by clicking it. A Vapi link works
   fine on the day it is created and dies fourteen days later.
4. The row appears in the Sheet, visibly distinct from complete tickets.
5. The agent explains what it is doing before ending the call; it never hangs up
   silently.
6. Every call in the demo produces exactly one row — complete or partial. Zero
   silent calls.
7. Partial rows are excluded from [03-recall](../03-recall/feature.md).

## Out of scope

Re-transcribing the recording afterwards to recover fields · automatic callback ·
a review queue UI (the Sheet is the queue) · merging a partial ticket with a
later complete one.
