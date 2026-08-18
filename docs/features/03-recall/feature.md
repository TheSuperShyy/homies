# 03 — Recall

**Estimate:** 1d
**Depends on:** [01-identity](../01-identity/feature.md), [02-intake](../02-intake/feature.md)
**Status:** not started

## Purpose

Tell a caller the status of a request the system itself took. This is Act 3 of
the demo: a *different* person calls back minutes after Act 1 and the agent
knows what happened.

## Behaviour

Two routes in, tried in order:

1. **By reference.** The caller reads back `255-1001-26`. Exact match, cheapest
   and most reliable.
2. **By location.** No reference — most callers will not have kept it — so the
   agent identifies them via [01-identity](../01-identity/feature.md) and lists
   open requests for that `(building, unit)`.

**One open request:** state it directly.

> "כן — נזילה מהתקרה באמבטיה, נפתחה היום, הסטטוס פתוח."

**Several:** disambiguate by type or by when it was opened, never by reading a
list of references aloud.

**None:** say so plainly, and say why it might be so — this is where the
boundary gets stated:

> "אין לי פנייה פתוחה על הכתובת הזאת. אני רואה רק פניות שנפתחו דרכי — אם פתחתם
> פנייה מול המשרד, אעביר אתכם לנציג."

**The status is real, not narrated.** The agent reports `requests.status` and
`created_at` as they are. It does not estimate when a technician will arrive, it
does not say "soon," and it does not reassure. Every one of those is a promise
Homies has not made.

## Interface

**`get_request_status`**

| Field | Type | Required | Notes |
|---|---|---|---|
| `reference` | string | no | preferred when the caller has it |
| `building` | string | no | required when `reference` is absent |
| `unit` | string | no | narrows the location lookup |
| `call_id` | string | yes | Vapi call id |

Returns:

```json
{
  "found": true,
  "requests": [
    {
      "reference": "255-1001-26",
      "type": "plumbing",
      "description": "...",
      "status": "open",
      "created_at": "2026-08-21T09:14:00Z"
    }
  ]
}
```

`found: false` is a normal outcome and must not be reported as a system fault.

## Data

Reads `requests` by `reference`, or by `(building, unit)` filtered to
`status in ('open','in_progress')`, most recent first. Covered by
`requests_status_idx` and `requests_created_idx`. Writes nothing.

Rows flagged `needs_review` by
[07-partial-ticket](../07-partial-ticket/feature.md) are **excluded** — a
partial ticket has no description worth reading aloud, and reading one back
would expose the gap rather than the save.

## Acceptance

1. A request opened in Act 1 is recalled correctly in Act 3 by a different
   speaker, using location alone.
2. Recall by spoken reference works when the caller has kept the number.
3. A building and apartment with no open request produces the honest "only what
   I took myself" answer and an offer to transfer.
4. The agent never states or implies a completion date.
5. Two open requests on one apartment are disambiguated without reading
   references aloud.

## Out of scope

Requests originating in OXS (needs the nightly bridge — release 2) · closed and
resolved history · updating or cancelling a request by phone · notifying a
resident when status changes.
