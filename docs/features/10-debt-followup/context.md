# Outbound debt follow-up — context

Why the prompt is shaped the way it is. If you are about to disagree with
[prompt.md](prompt.md), read this first.

## Where the evidence came from

Four recorded collection calls, supplied 3 August 2026 as
[hebrew_english_call_transcripts.pdf](../../discovery/source/hebrew_english_call_transcripts.pdf),
extracted to [call-transcripts-extracted.txt](../../discovery/call-transcripts-extracted.txt).

| # | Caller | Resident | Building | What happened |
|---|---|---|---|---|
| 1 | Meryl | Tzlil | HaZohar 6 & 8 | No keys yet. Nothing owed. Caller busy, deferred. |
| 2 | Jonathan | Michael | Weizmann | July unpaid. Card on file charged on a verbal yes. Standing order offered, declined. Policy explained. |
| 3 | Meryl | Sarah | HaZohar 6 & 8 | Apartment 6 not handed over, furniture moving in. Nothing owed. |
| 5 | Jonathan | Hadassah | Shlonsky 10 | Calling about Itamar, who is not answering. Long argument, then de-escalation. |

**Sample call 4 is missing from the PDF.** The file names jump from
`sample call 3.mp3` to `sample call 5.mp3`. Worth chasing — if it covers a
situation none of the others do, it is the most valuable of the five.

### The Hebrew is reconstructed, not quoted

The PDF's Hebrew text layer is corrupt — it extracts as repeating `אלו` /
`הגעתי לצליל` / `כן` tokens where the real sentences should be. Only fragments
survived. **Every Hebrew line in the prompt was written from the English
translation column**, not lifted from the recordings.

The meaning and register should be right. The exact phrasing may not be. Before
rehearsal, a Hebrew speaker must check the lines against the audio — register is
what gives an agent credibility with Israeli residents, and a reconstruction goes
wrong by sounding slightly too written.

## What four calls can and cannot settle

**They settle register.** Direct, informal second person, warm but not chatty, no
corporate padding, short turns. This is well evidenced across all four.

**They settle which situations are frequent.** Two of four are "nothing is owed
yet". That is the strongest number in the set — and it is not a conversation
finding at all. Those calls should never have been placed. No prompt condition
fixes it; the handover-status check before dialling does.

**They do not settle thresholds.** How many turns before handing over, what
counts as hot rather than friction — four calls cannot support that, and deriving
it anyway would be fitting to Jonathan and Meryl's habits on four particular
afternoons.

### Situations with no coverage

Asked and answered by the client on 3 August; see the decisions below. Still
worth recording real examples of:

- **The ordinary successful call** — rings, pays, hangs up in ninety seconds.
  All four samples have something going on, so we have no baseline for what
  normal sounds like or what the agent should be aiming at. **Still outstanding.**
- **Voicemail and no-answer.** Cannot appear in a set of connected calls, yet it
  will be most of real outbound volume.

Ten to fifteen more recordings would move this from informed guess to grounded,
and they should be a random fortnight rather than a curated set — hand-picking
removes exactly the boring calls that define the baseline.

## The decisions

### It is one tree, not two branches

The first draft split cooperative and resistant into separate scripts. That was
wrong, and the client corrected it: the agent reads the caller's posture at every
turn and moves with them. Call 5 goes annoyed → arguing → softening → agreeing →
annoyed again in about four minutes.

Two things follow that a branch model gets wrong:

**Movement must work in both directions.** A resistant caller who then says
"fine, send me the link" is cooperative *now*. The agent sends the link and
finishes, and specifically does not refer back to the friction — mentioning it
re-opens it.

**The one-explanation rule had to become a call-level budget.** In a branch
model, "one explanation" means one per visit to the resistant branch, so a caller
who pushes back, calms, then pushes back again gets explained at twice. Three
times. Which is precisely Jonathan's five rounds in call 5, arrived at one
reasonable step at a time. The budget never resets.

### Hot is a floor, and this is deliberate

Open and friction move freely in both directions. Once a call has been hot, it
always ends in a handover — even if the caller apologises, even if they then
offer to pay. If they offer to pay, the agent sends the link *and still
transfers*.

Judging whether someone has genuinely calmed down is exactly the read a person
can make and a bot cannot, and being wrong costs far more than an unnecessary
handover. **This does mean some calls a human would have closed get transferred.**
That is the accepted price. If the transfer rate proves unbearable in rehearsal,
this is the first knob to turn — but turn it knowing what it buys.

### What we deliberately did not copy from the transcripts

- **Charging a card on a verbal yes** (call 2). A human doing this is a business
  decision; an automated system doing it is a payment with no signature, no
  verifiable consent, and a recording as the only evidence — and the recording is
  what a disputed charge gets fought over. Replaced with a payment link, where
  the resident's own tap is the consent.
- **The five-round policy defence** (call 5): electricity, water, property tax,
  four reminders, the building's balance sheet. Jonathan recovers it because he
  can hear her tone change. A bot permitted to argue twice will argue eleven
  times, identically, across 200 buildings.
- **Discussing Itamar's debt with Hadassah** (call 5), at length. Whatever
  today's practice, an automated system doing this at scale is a different
  exposure under Israeli privacy law, and it surfaces as a complaint rather than
  a bug.
- **The warning at three months.** Jonathan raises it. The agent never mentions
  any consequence of not paying — that decision belongs to a person.

### Client decisions, 3 August 2026

**"I already paid" — hold the position, move the burden to a receipt.** The
database is checked before the call is placed, so the payment genuinely is not
recorded. The agent neither concedes nor challenges: it states what the system
shows, gives an email for the receipt, thanks them, and says it will call again.
It never asks when or how they paid — the receipt makes the question redundant,
and the question itself reads as cross-examination.

*This was not one of the three options offered. It is better than all of them,
because it uses the one asset the agent has that a human collector does not: it
already knows, before dialling, exactly what the ledger says.*

**Hardship — always transfer.** Financial hardship is a judgment call with a
relationship attached and is the worst possible thing for an automated system to
be recorded handling badly. The prompt draws the friction/hardship line sharply
because they sound alike: "later" is friction, "I don't have the money" is
hardship.

**Multi-intent — payment first, but open the ticket.** The agent acknowledges,
commits to opening a request, and returns to why it rang. It captures what they
already said rather than interviewing them, and asks at most one clarifying
question. `open_request` fires before the call ends. The failure to avoid is the
silent drop — a resident mentions a leak and nothing is opened.

**Language — Hebrew only, then hand over.** One line, then a person. No English
attempt. Multilingual is a release-2 project: every line needs a twin, and the
twins drift apart the moment one is edited.

## Open questions

**Voicemail: leave a message at all?** The prompt currently leaves a neutral one
— who is calling, which building, a number, no amount and not the word חוב. Some
collection operations avoid voicemail entirely, because a message on a shared
family phone is a disclosure you cannot control. *Would be settled by: a decision
from Homies' ops manager, ideally with whatever their current practice is.*

**Is "the 1st to the 10th" uniform?** Jonathan states it as policy in call 2. Not
known whether every house committee sets the same window. *Would be settled by:
one question to Homies.* If it varies, it becomes a per-building variable rather
than a line in the prompt.

**The reminder ladder.** Jonathan mentions four reminders in a month and a
warning at two and a half to three months. Four attempts is encoded; the warning
is left as a human decision. *Would be settled by: the actual written policy, if
one exists.*

**Resident gender.** Hebrew second-person verbs are gendered, and the agent
addresses residents directly. The prompt takes a `{{gender}}` variable with a
fallback that phrases around it. *Would be settled by: checking whether the
resident data carries gender at all.* Getting this wrong is noticed by an Israeli
listener in the first sentence.

**Which employee's name does the agent use?** It currently introduces itself as
Michal, a name belonging to no one, and discloses that it is a digital assistant.
Using a real employee's name would mean residents believe they spoke to a person.
*Would be settled by: a decision from Homies — but the recommendation is to keep
a name that is not a real employee's.*

## Scope note

Outbound is Phase 7 on the [phase chart](../../diagrams/Homies-Gantt-Simple.excalidraw)
— weeks 6–8. The week-3 demo is inbound intake, and features 01–09 are written
against that.

Building this now is fine while the transcripts are fresh, and it demos well with
the open-mic format because ops staff know exactly how these calls go wrong. But
**it is a scope change, not an addition.** If it replaces intake in the demo, the
nine existing feature specs are no longer what is being shown.
