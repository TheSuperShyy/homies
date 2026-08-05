# 09 — Sheets mirror

**Estimate:** 0.5d
**Depends on:** [02-intake](../02-intake/feature.md), [07-partial-ticket](../07-partial-ticket/feature.md)
**Status:** not started

## Purpose

Put the row on a screen the moment it is written. Supabase is the record; the
Sheet is what the room watches. It is open on the projector for the whole
meeting, and a row appears while the caller is still saying goodbye.

## Behaviour

The same n8n workflow that writes to Supabase appends to a Google Sheet. One
extra node, fired after a successful insert.

**Columns, in Hebrew, right-to-left:**

| מספר פנייה | שעה | בניין | דירה | סוג | תיאור | דחיפות | סטטוס |
|---|---|---|---|---|---|---|---|

Reference, time, building, apartment, type, description, urgency, status.
Nothing else — no ids, no confidence scores, no internal fields. This is the
ticket as a dispatcher would see it, which is what Act 2 asks them to criticise.

**`needs_review` rows are visibly distinct.** Conditional formatting on the
status column. A partial ticket must be identifiable at a glance from the back
of the room, because pointing at one is how the partial-ticket path gets
explained.

**Append only.** The mirror never reads from the Sheet and never writes back to
Supabase. If someone edits a cell during the meeting — and they should, that is
the critique made concrete — the edit stays in the Sheet and changes nothing
upstream. Their edits are notes, and notes are exactly what we want out of Act 2.

**A failed append never fails the call.** The Sheets node is best-effort. If
Google is slow, the request is still written, the caller still hears their
reference, and the row is missing from the screen. Losing a display row is
recoverable; losing a ticket is not.

## Interface

No tool. An n8n Google Sheets node on the success branch of `open_request` and
`save_partial_request`, with an `onError: continue` policy.

## Data

Reads the row just written. Writes nothing to Supabase.

## Acceptance

1. A row appears in the Sheet within three seconds of the call completing.
2. Hebrew headers render right-to-left correctly.
3. A `needs_review` row is visually distinct without anyone needing to read the
   status text.
4. Editing a cell has no effect on Supabase — confirmed by re-querying.
5. Deliberately breaking the Sheets credential does not break `open_request`;
   the ticket is still created and the reference still read back.
6. The reference in the Sheet matches the one spoken on the call.

## Out of scope

Two-way sync · reading anything from Sheets · the nightly OXS import, which is a
different Sheets integration entirely (release 2) · formatting beyond the status
highlight · sharing the Sheet with Homies after the meeting, which is a decision
for the room, not a build task.
