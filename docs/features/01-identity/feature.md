# 01 — Identity

**Estimate:** 1.5d
**Depends on:** nothing
**Status:** not started

## Purpose

Establish who is calling, without caller ID. Every other feature needs a
`resident_id` or an explicit decision that we could not get one. On a Vapi web
call there is no phone number at all, so the agent asks.

## Behaviour

The agent opens, then collects three things in this order:

1. **Building** — asked first because it is the most constrained field. There are
   ~200 of them and they have known names, so it is the easiest to match and the
   easiest to confirm.
2. **Apartment** — a number, which makes it the single most ASR-fragile field in
   the system. Always read back. See [05-messy-input](../05-messy-input/feature.md).
3. **Name** — asked last, and used to confirm rather than to search. Hebrew name
   transcription is unreliable enough that matching on it produces false
   positives.

Lookup is `(building, unit)` against `residents`, which
`residents_building_idx` covers.

**On a single match** the agent confirms by name and moves on:

> "תודה — דוד, בניין הרצל 14, דירה 12. נכון?"

**On no match** the agent does not stall. It carries the building, unit and
spoken name forward as free text and opens the request anyway, with
`resident_id` null. An unregistered caller with a real leak still gets a ticket.

**On multiple matches** — two residents in one apartment — it uses the spoken
name to disambiguate, and if that fails, takes the first and notes both in the
transcript. Getting the household right matters; getting the individual right
does not, for a maintenance request.

The building and unit captured here are reused by
[02-intake](../02-intake/feature.md) and must never be asked twice.

## Interface

**`identify_resident`**

| Field | Type | Required | Notes |
|---|---|---|---|
| `building` | string | yes | as spoken; matched loosely |
| `unit` | string | yes | post-normalisation |
| `spoken_name` | string | no | confirmation only, never the search key |
| `call_id` | string | yes | Vapi call id, for the interaction row |

Returns:

```json
{
  "matched": true,
  "resident_id": "uuid",
  "full_name": "דוד כהן",
  "building": "הרצל 14",
  "unit": "12"
}
```

`matched: false` returns the echoed building and unit with a null
`resident_id`. It is a successful call, not an error — the agent must not
apologise or retry on it.

## Data

Reads `residents` on `(building, unit)`. Writes nothing; the interaction row is
created by the end-of-call webhook, and the captured slots reach it through
`tool_calls`.

## Acceptance

1. Ten calls against the ten seeded residents in
   [002_slice_seed.sql](../../../supabase/002_slice_seed.sql) return the correct
   `resident_id`.
2. A caller giving a building that exists and an apartment that does not returns
   `matched: false` and the conversation continues to intake without a stall.
3. A caller who does not know their building number is offered the street name
   and gets there.
4. Building and unit are never asked a second time later in the same call.
5. Apartment number is read back before the agent moves on.

## Out of scope

Phone-number matching (release 1, needs a real DID) · `verify_identity`, the
stronger check gating payment operations (release 1) · household relationships ·
any resident self-service registration.
