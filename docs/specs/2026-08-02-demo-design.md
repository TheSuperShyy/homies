# The week-3 demo — design

**Date:** 2026-08-02
**Milestone:** end of week 3 on the [phase chart](../diagrams/Homies-Gantt-Simple.excalidraw)
**Supersedes:** the Phase 1 demo narrative in the build roadmap, which assumed
caller-ID identification

---

## What this demo is

**An intake-reliability demo, not a conversation demo.**

The question in the room is not *can a bot hold a conversation in Hebrew* —
everyone already believes that. The question is *does a usable, correct row come
out the other end when a real person calls from a stairwell with a child
shouting.* That is the thing that decides whether this system is worth running,
and it is the thing the demo has to answer.

So the demo is built around inputs and their consequences: what the agent does
with degraded audio, with people who talk over it, with three requests in one
breath, with a question it is not allowed to answer — and what lands in the
database in each case.

## Who is in the room

The **operations manager and the call centre staff**. Not the owner.

This is a deliberate choice and it shapes everything. The owner asks whether the
project is worth funding. Ops staff ask whether it makes Tuesday morning better
or worse, and they are the ones who can quietly kill it by never using it. They
are also the only people who know what a good ticket looks like.

So they are recruited as **judges of the output**, not as subjects of a
replacement. The centre of the meeting is them criticising a ticket the bot
wrote. Their critique becomes the field spec, for free.

## Format: open mic

They hold the microphone. We do not touch it.

The scope is declared out loud before anyone speaks, and so is the failure:

> "This version does two things: it opens a request, and it tells you the status
> of a request it took itself. That is all it does today. It takes the intake
> call — anything with judgment in it comes to you. And it will get things wrong
> today. That is what I am here for. I want the list."

Pre-committing to failure converts every mistake from an embarrassment into data
collection, which is the only way an open mic is survivable. A scripted demo
would be safer and would prove nothing, because everyone in that room has seen a
scripted demo before.

## The two flows

1. **Open a request** — [02-intake](../features/02-intake/feature.md)
2. **Check a request the system itself took** — [03-recall](../features/03-recall/feature.md)

Recall is limited to rows the system created. Older OXS requests need the
nightly data bridge, which is release-2 work. That boundary is stated out loud
rather than hidden, because it will be discovered in the first thirty seconds
otherwise.

The limitation turns out to be the strongest beat available. Because recall only
covers rows the system took, the request it recalls in Act 3 is one the room
created minutes earlier on an open mic. Nothing about it can be pre-loaded.

## Identity: the bot asks

The agent asks for **name, building, and apartment**. It does not use caller ID.

Forced by a hard constraint: Vapi web calls carry no phone number, and the demo
runs on web calls because no Israeli DID exists yet (Telnyx KYC is 1–3 weeks and
rejection is common for foreign entities). But it is also the better design. The
laptop gets passed around an open mic, so any faked identity would apply to
everyone in the room. And asking is a real release-1 path anyway — residents
call from work phones, from a spouse's phone, from a number that was never in
OXS.

Detail in [01-identity](../features/01-identity/feature.md).

## What gets hardened

Three areas, chosen deliberately over a fourth:

- **Interruption and pacing** — [04](../features/04-interruption-pacing/feature.md).
  Judged in the first ten seconds, before anyone evaluates the output.
- **Messy input** — [05](../features/05-messy-input/feature.md). The largest single
  line item, and the centre of the demo.
- **Boundaries and multi-intent** — [06](../features/06-boundaries/feature.md).
  Knowing what not to answer is what makes the rest trustworthy.

*Not* a separate pillar: emergency and anger judgment. The `urgency` enum already
carries `'emergency'`, so the branch is roughly half a day folded into
boundaries rather than a fourth workstream.

## Where it lands, and what they watch

**Supabase is the record. A live Google Sheet is the screen.**

The n8n workflow that writes the row also appends it to a Sheet with Hebrew
headers, open on the projector for the whole meeting. The row appears while the
caller is still saying goodbye.

This beats building a CRM page for the demo on three counts: Sheets is RTL for
free, ops staff already read and edit spreadsheets natively so criticising a row
costs them nothing, and there is no tab-switch — the audience watches intake
happen rather than being shown a result afterwards. It also takes the RTL Next.js
page off the critical path entirely, ~0.5d against ~1.5d.

The Sheet is a mirror and never a source. Detail in
[09-sheets-mirror](../features/09-sheets-mirror/feature.md).

## Every call produces a row

The one rule the demo depends on: **an open mic must never produce silence.**

When the audio is unusable, the agent does not fail — it writes a partial ticket
holding whatever slots it did capture, plus the recording, flagged for a human,
and says so:

> "I am having trouble hearing you. I have saved what I have along with a
> recording, and someone will call you back."

That is better than what happens today, which is voicemail nobody transcribes.
Detail in [07-partial-ticket](../features/07-partial-ticket/feature.md).

## The scoreboard

Per-slot capture and re-ask counts are written to `interactions.tool_calls`
during the meeting, so the close is a number rather than an impression:

> "That was eleven calls. Nine complete tickets, two escalated to a human, zero
> wrong tickets."

Zero-wrong-tickets is the figure that matters and the reason
[05-messy-input](../features/05-messy-input/feature.md) forbids confident
guessing. Detail in [08-instrumentation](../features/08-instrumentation/feature.md).

---

## Running order — about 30 minutes

| | | |
|---|---|---|
| **Opening** | 3 min | Scope declared. Failure pre-committed. Sheet on the projector. |
| **Act 1 — open mic** | 10 min | They call. We do not touch it. Notes taken visibly. |
| **Act 2 — critique** | 5 min | "Is this the ticket you would have written?" Then stop talking. |
| **Act 3 — the callback** | 5 min | A *different* person rings back about a request from Act 1. |
| **Close** | 5 min | The scoreboard. Ask for the break-it list. |

Act 2 sits between the two calls on purpose. It puts several minutes and a
change of speaker between the request being created and being recalled, which is
what makes Act 3 unfakeable.

## When it goes wrong

- **Name the bad call, do not rescue it.** "That one is wrong — say what it
  should have said and I will write it down." Rescuing costs more credibility
  than the failure did.
- **"Let me try that again" once, maximum.** Twice reads as a demo held
  together with tape.
- **Two consecutive bad calls ends the open mic.** Move to Act 2 with what
  exists. A partial ticket is still a ticket, and Act 2 works on any row.

## Done means

- They leave having written a break-it list, in their words, that we keep.
- Someone volunteers a call type they would want it to take. That is adoption
  starting, unprompted.
- The Act 2 critique produces concrete field changes. If the ticket is perfect,
  either we got lucky or they are being polite; assume the latter and push.
- Nobody asks whether it replaces them. If that question comes, the framing
  failed and the rest of the meeting is spent recovering.

## Not in this demo

WhatsApp · the metrics CRM · outbound calls · the payment-change flow · live OXS
data · a real phone number · department scoping and RBAC · any browser
automation.

---

## Cost

| # | Feature | Est. |
|---|---|---|
| 01 | Identity | 1.5d |
| 02 | Intake | 1.5d |
| 03 | Recall | 1d |
| 04 | Interruption and pacing | 2d |
| 05 | Messy input | 3d |
| 06 | Boundaries and multi-intent | 2d |
| 07 | Partial ticket | 1d |
| 08 | Instrumentation | 1d |
| 09 | Sheets mirror | 0.5d |
| — | Adversarial rehearsal | 1d |
| | **Total** | **14.5d** |

Against 24 person-days budgeted for weeks 1–3. The 9.5 days of slack are not
padding: Hebrew ASR tuning is the line item that historically consumes them, and
it is now the centre of the demo rather than a side concern.

## The two soft numbers

**The Hebrew numeral normaliser** in
[05-messy-input](../features/05-messy-input/feature.md) cannot be sized honestly
until we see real Azure `he-IL` output on Israeli apartment numbers. It is the
highest-frequency failure surface in the system, because every single request
contains an apartment number. If any estimate here is wrong, it is that one.

**The partial-ticket threshold** in
[07-partial-ticket](../features/07-partial-ticket/feature.md) — how bad the audio
must get before the agent stops trying — is a judgment call that only rehearsal
settles. Too eager and it gives up on recoverable calls; too stubborn and it
produces the wrong ticket, which is the one outcome with no acceptable rate.

## The schema is not ready

The partial-ticket path cannot exist against
[001_slice_schema.sql](../../supabase/001_slice_schema.sql) as written. Four
deltas, all required before feature 07:

| Line | Now | Needs to be |
|---|---|---|
| 86 | `type text not null` | nullable |
| 87 | `description text not null` | nullable |
| 88 | `building text not null` | nullable |
| 93 | `status check (...)` | add `'needs_review'` |

Three NOT NULLs mean that a call where the building was inaudible cannot be
written at all — which is precisely the call that most needs a row. Migration
`003_partial_tickets.sql` ships with feature 07.

`interactions.audio_url` and `interactions.caller_phone` already exist, so the
recording and callback number need no change, and
`interactions.tool_calls jsonb` is where the instrumentation goes.

Separately, the comment at lines 12–15 documents a design we are not building —
it names `phone` as the primary lookup key for `identify_resident` on the
grounds that "Vapi delivers caller ID in E.164." On a web call Vapi delivers
nothing. The demo matches on name plus building plus unit, which
`residents_building_idx` already supports. The phone path stays for release 1
with real telephony; it is simply not the demo's path, and the comment should
say so.
