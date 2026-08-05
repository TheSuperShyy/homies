# 09 — Sheets mirror — context

## Why this exists

Act 2 asks call centre staff to criticise a ticket. That requires the ticket to
be in front of them, in Hebrew, in a form they can argue with. A database row is
not that. A Next.js page would be, but it costs a day and a half and needs RTL
work that the original plan had deferred to phase 6.

A spreadsheet is already the form these people argue about tickets in.

## Decisions

**Sheets instead of building a CRM page for the demo.** Three separate wins, any
one of which would probably be enough:

- RTL is free, and Hebrew RTL was mispriced in the original plan — pushed to
  phase 6 while the demo needed it in week 3.
- Ops staff read and edit spreadsheets without being taught, so criticising a
  row costs them nothing and they will actually do it.
- No tab switch. The row appears while the call is still ending, so the room
  watches intake happen rather than being shown a result afterwards.

It also takes the RTL Next.js page off the critical path entirely: ~0.5d against
~1.5d.

**Supabase stays the record; the Sheet is never a source.** The moment a
spreadsheet becomes authoritative it acquires manual edits, and reconciling them
is a permanent tax. Append-only, one direction, no exceptions.

**Their edits are wanted, and deliberately discarded upstream.** Someone
rewriting a description in the Sheet during Act 2 is the critique in its most
useful form. We keep the sheet afterwards as notes. Nothing propagates.

**Best-effort, never blocking.** A Sheets failure must not cost a ticket. The
node continues on error and the display row is simply missing — a visible,
recoverable gap.

**Only the dispatcher-facing columns.** Showing ids and confidence scores
invites a conversation about the system's internals during the five minutes
reserved for criticising its output.

## Constraints

- Google Sheets API rate limits are far above demo volume; irrelevant at eleven
  calls, worth remembering if this survives into production.
- The Sheets credential lives in the n8n credential store. Never in a file,
  never in this repository.
- Sheets RTL is per-sheet, set once in the sheet's settings, not something the
  API configures per write.
- Conditional formatting is configured in the sheet by hand, not by n8n.

## Known failure modes

- **Append latency making the row appear late,** which undercuts the "watch it
  land" effect. Three seconds is the acceptance bar; test it before the meeting
  rather than discovering it live.
- **Hebrew rendering left-to-right** because the sheet's RTL setting was not
  applied. Trivial, and highly visible if missed.
- **Someone editing the Sheet and expecting it to have done something.** Say out
  loud that edits are notes. Otherwise a helpful correction silently vanishes
  and reads as the system ignoring them.
- **The credential expiring between rehearsal and the meeting.** Check on the
  day.
- **The projector showing a stale view** because nobody scrolled. Sort newest
  first.

## Open questions

- Should the Sheet be shared with Homies after the meeting? It is their data and
  it makes a good leave-behind, but a spreadsheet that ops staff start relying
  on becomes a shadow system very quickly. Decide in the room, and if yes, share
  it as a frozen copy rather than the live mirror.
- Does the demo need a second tab showing the interaction detail — transcript,
  latency, tool calls? Adds depth if someone asks how a value was captured, and
  clutters the main view if nobody does. Build only if rehearsal wants it.

## Related

[The demo design](../../specs/2026-08-02-demo-design.md) ·
[02-intake](../02-intake/feature.md) ·
[07-partial-ticket](../07-partial-ticket/feature.md) ·
[08-instrumentation](../08-instrumentation/feature.md)
