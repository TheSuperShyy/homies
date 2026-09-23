# Homies — the plan, and where the project actually went

**As of 23 September 2026. Internal, for Clix.**

The plan is `docs/prd/Homies-PRD-v2.md` (2 August). What works today is
`docs/reference/Homies-Feature-Status.md`. Every decision that moved the target
between those two dates is scattered across `CONTEXT.md`, the worklog and the
handover. This page joins them, so the question "are we building what we said
we would build?" can be answered without reading all four.

**The short answer: the software is ahead of the plan. The project is behind on
everything only Homies can supply.**

Nothing here re-opens a decision. Open questions are collected at the end as
questions, not recommendations.

---

## 1. The five components

| # | Component | Planned | Today |
|---|---|---|---|
| 1 | Voice agent, inbound | R1 | **Built.** Opens requests with a reference, answers balances, answers ticket status live, passes matters to the team. Cannot be phoned — no number. |
| 2 | Support chatbot, WhatsApp | R1 | **Built and live**, on a test number. |
| 3 | Team inbox | R1 | **Built.** Departments, routing, bot-steps-aside on takeover. One seat exists. |
| 4 | CRM | R1 | **Built.** Tickets, debts, conversations, calls, transcripts, Hebrew RTL, login. |
| 5 | Voice agent, outbound debt | R2 | **Built.** Balance, promises to pay, disputes, standing orders, payment link mid-call. Cannot dial — no number. |

All five exist. Two of them cannot reach a resident, for the same reason.

---

## 2. What feedback changed

Each row is a decision that moved the target, with its date and who made it.

| When | Who | What changed | Consequence |
|---|---|---|---|
| 30 Jul → 2 Aug | Clix | v1's browser automation dropped; payment deletion becomes staff-confirmed; status reads a nightly export | The PRD we build from. Recorded in its own §0 |
| Aug | Owner | **Chatbot first.** Voice work stops when it competes with the bot | Feature order, not scope |
| 15–16 Sep | Yariv's review | **No national emergency numbers, no safety advice.** An emergency is a ticket plus a team alert, at once | The bot no longer tells anyone what to do in a fire |
| 15–16 Sep | Yariv's review | **A fault inside the flat is the resident's.** A tap, a sink, an appliance: said kindly, no ticket. Common property and building systems still get one | Fewer tickets, and the ones opened are Homies' to fix |
| 15–16 Sep | Yariv's review | **Plural address on voice**; the agent stops guessing the caller's gender and stops echoing their words back | Tone, and it is the thing clients notice first |
| 17 Sep | Owner | **The bot never invites a photo.** One that arrives is kept and attached | Removes a question from every fault |
| 17 Sep | Owner | **No fixed messages except the menu** | Two exceptions since, both forced by Meta — see §3 |
| 26 Aug, reaffirmed 23 Sep | Owner | **Nothing is written into OXS.** The ticket mirror was built and switched off the same night; on 23 Sep: *"i dont want to edit on oxs"* | Bot tickets live only in our system. Staff close them on our dashboard |
| 22 Sep | Owner | **Tests never spend OpenRouter credit**, and **use the platform's own feature** rather than rebuilding it beside it | A dashboard chat route was deleted rather than kept |
| 23 Sep | Owner | **No WhatsApp outreach.** The flow stays call-first: ring, agree, then send the link | Templates are a rescue inside a call, never a first contact |

Two shifts are worth naming beyond the table.

**The real ask was never a standalone bot.** PRD item 3 reads as "a team
chatbot". What Homies actually wants is a centralised inbox where every channel
lands in one place and staff can take over. That is what was built, and it is
why components 2 and 3 were always one job.

**The old ManyChat bot is the real benchmark.** Not written in the PRD, but it
is what the client compares us against. Scanned on 22 Sep and documented in
`docs/discovery/manychat-scan-2026-09-22.md`: six menu doors, a four-question
form on every visit, and tickets that reach a task board with no reference for
the resident. We match or beat five of its six doors; quotes and the caretaker
route are thinner than theirs.

---

## 3. Where we landed ahead of the plan

**Live ticket status, instead of last night's file.** The biggest one. The PRD
gave up here: §2.2 had the bot read a nightly export, say *"as of last night…"*
every time, and raise a staff task on every single status question — a flow it
called, in writing, the one that is not fully automated. OXS's live API landed
instead. The bot answers from real data, and the whole class of follow-up work
that limitation implied never had to exist.

**Live residents, buildings and arrears**, refreshed automatically, rather than
a nightly hand-off.

**Photos on tickets**, with the images held privately and shown on the
dashboard. Not in the plan at all.

**A "done" message.** When a ticket is resolved the resident is told on
WhatsApp, automatically. Not in the plan; proven end to end on 23 Sep.

**The payment link reaches people outside the 24-hour window.** A second
approved template, submitted 23 Sep, so a debt call can deliver the link during
the call rather than promising the office will send it.

Both of those messages are fixed wording, which sits against the "no fixed
messages" rule. That rule is about the bot's voice; Meta permits nothing but
pre-approved text to someone who has not written to us in 24 hours. The two
templates are the only way those messages exist at all.

---

## 4. Where we landed short

| Gap | Whose move |
|---|---|
| **A real phone number.** Every call is a browser call. Residents cannot ring in; the system cannot ring out | **Homies.** The line has been on order for weeks. It blocks more than anything else here |
| **Changing payment details by phone** (PRD §2.3) | **Homies.** The PRD itself listed two blockers: what a resident must provide to prove who they are, and 48 or 72 hours before an incomplete change is flagged. Both open since day one |
| **Staff tasks pushed to a task board** | **Homies.** Needs their token and a decision on which board. The single point it would hook into was built for exactly this |
| **Staff seats in the inbox** | **Homies.** One seat exists; team alerts go to teams with no members |
| **Department-scoped access** | **Ours,** but meaningless until there are staff accounts |
| **Load test: 200 interactions/day, 10 concurrent calls** | **Ours,** and not honestly testable without the phone line |
| **The WhatsApp number switch** | **Homies.** Meta access was granted 15 Sep; it needs a date |

---

## 5. The success criteria, scored

PRD §14, verbatim, and where each one stands.

| # | Criterion | State |
|---|---|---|
| 1 | Open a request, log a complaint, receive a payment link without a human | **Met** on both channels |
| 2 | Status answers honest and caveated, always with a follow-up task | **Obsolete.** Answers are live, so there is nothing to caveat and no task to raise |
| 3 | Payment-change requests captured, verified, actioned with an audit trail | **Not built.** Blocked on Homies, see §4 |
| 4 | Complaint tickets captured with complete structured data | **Met** |
| 5 | Handover to a human works on both channels | **Met** |
| 6 | 200 interactions/day, voice under 800 ms | **Unmeasured.** Needs the phone line |
| 7 | Measurable reduction in repetitive calls reaching staff | **Unmeasurable.** Nothing is running on a real number yet |

The eighth, unnumbered: *over 60% of interactions resolved without a human.*
§14 already flags it as needing renegotiation, and it still does — there is no
traffic to measure.

**The tool layer** (§10) came out close to the plan. Twelve tools were
specified; nineteen exist. `verify_identity` became a server-side check rather
than a tool the model can claim to have run, `get_request_status` reads live
data rather than an export timestamp, and the two payment-deletion tools were
never built. Everything else is there, and every tool serves both channels from
one place, as designed.

---

## 6. What the goal is now

One centralised inbox for Homies, with a Hebrew voice agent and a WhatsApp
assistant as its front doors, everything recorded in one database, and a
dashboard the office can read. The bots handle what repeats; anything sensitive
reaches a person, in the same thread, with the bot stepping aside.

That is close to what the PRD described. What changed is the posture around it:
**we read from the client's systems and never write to them**, we do not
message residents first, and where a rule affects what a resident hears, it is
Yariv's call rather than ours.

---

## 7. Still open

**Waiting on Homies**

1. The phone line.
2. A date for the WhatsApp number switch.
3. Staff names, emails and departments for inbox seats.
4. How a resident proves identity before a payment-details change, and the
   re-entry window: 48 or 72 hours.
5. Whether bot tickets should also reach their task board, and which one.
6. Confirmation of the arrears figures, or where the office really keeps them.
7. A test apartment of our own, so demos stop borrowing a real resident's flat.
8. Screenshots or a share link for the old bot's four flows — the wording of
   each step is only in its editor.

**Ours**

9. Two tickets can never resolve: a double space in a stored building address
   breaks the lookup.
10. The dispatcher's progress notes are wiped when a ticket closes — 0 of 894
    resolved tickets kept theirs.
11. Nineteen tickets our own bots opened have sat open since August, because
    nobody works in our dashboard yet.
12. No load test, and no measured voice latency on a real line.
