# 16 — Human handover on WhatsApp and voice

**Estimate:** 1d
**Depends on:** [11-whatsapp-bot](../11-whatsapp-bot/feature.md), [12-chatwoot](../12-chatwoot/feature.md)
**Status:** built and wired live 3 Sep, alert proven on the owner's PC the same day (Windows toast). Switched off for WhatsApp on 13 Sep, **back on 14 Sep as a *team note*** — the same mention, new words; see the two notes below. **The inbound voice agent joined the same afternoon** (the Voice section below). The toggle half (a person's reply silences the bot; the 15-minute handback) has been live throughout.

> **14 Sep, afternoon — voice joined.** Owner: *"for the inbound voice agent
> i want it to have tough durability as well like the one we have in the
> chatbot."* The voice `transfer_to_human` had told the model to promise a
> call-back and hang up, and its handler wrote a row nobody read. Now the
> voice tool is `notify_team` too, and behind it the Edge Function posts to
> a new n8n workflow, "Homies — Voice team note", which gives the call a
> Chatwoot conversation in a new **Homies — Voice** inbox (API channel, no
> way back out) and hands it to this sub-workflow with `channel: voice`.
> Same mention, same teams, same ladder; the note's last line says phone the
> resident and resolve. An end-of-call backstop makes the note when the bot
> said the team knows and never called. Verified: nine harness cases
> (`scripts/voice_note_test.py`), the emergency thread escalated by the
> ticker on the real clock, the WhatsApp harness still 12/12.

> **14 Sep — back on, as "I've let the team know".** The owner's refinement:
> the goal is to cut the office's workload, the bot is 100% of customer
> support, and past its threshold (paying dues, a disputed bill or a
> document, moving in or out, a contract, a quote, a request for a person)
> it must not dead-end a resident on a phone number. It says it has let the
> right team know — and asked what sits behind that sentence, he chose *"a
> mention in Chatwoot, like regular"*. So `scripts/n8n_whatsapp_teamnote.py`
> put the call to this sub-workflow back on the WhatsApp workflow, framed as
> the bot noting a matter for its own team while it keeps the conversation:
> the tool is `notify_team` (the name is a prompt; the debt-tools handler
> behind it keeps its old name for the voice agents), reasons name the
> matter (`payment` / `billing` / `move` / `contract` / `quote` /
> `emergency` / `caller_request` / `other`) and pick the team by default,
> priority is **medium** except emergencies, the 24-hour guard is **per
> reason** (a second matter the same day gets its own note; `handover_reasons`
> on the conversation holds the window's list), and **only an emergency
> climbs the escalation ladder** — everything else is paged once (or at
> 09:00) and worked through. Office details only when asked. Emergencies:
> emergency-urgency ticket and the team notified, at once — **no office
> line**; *since 16 Sep, and no national number and no safety advice
> either, by owner decision after the client's review.* No נציג button, no tap path; a request for a person is
> `caller_request` by the model's judgment. The promise backstop is folded
> into `Team note this turn?`: a first-person "I've told the team" or a
> call-back promise with no tool call still makes the note. Epoch 22.
> Snapshot `docs/handover/n8n-whatsapp-live-14sep-before-teamnote.json`.

> **13 Sep — the alert half is off.** The owner's direction: *"lessen the
> interaction with office and tenants … if the chatbot cannot handle the
> conversation anymore it should try its best to handle everything like
> opening a ticket … the bot won't turn off but would mention the office."*
> Asked directly, he chose the same for emergencies: office details, no page.
> So `scripts/n8n_whatsapp_nopage.py` removed all three paging paths from the
> WhatsApp workflow — the נציג tap chain, the `transfer_to_human` tool and
> the promise backstop, eleven nodes — and the third button now reads
> **משהו אחר** and reaches the model like any message. The bot resolves what
> it can, says office matters (payment arrangements, disputed bills, moving
> in or out, contracts, the committee) are the office's and gives its
> details, and promises nobody a call. An emergency is an `emergency`-urgency
> ticket, the national number and the office line; **nobody at Homies hears
> about a 22:00 lift call until someone opens Chatwoot** — the cost, stated
> to the owner and accepted. The sub-workflow, the ticker, the teams and the
> inbox membership all stay in place; the escalation ladder is dormant because
> nothing sets a `handover` label. To turn paging back on:
> `python scripts/n8n_whatsapp_nopage.py --restore` (the 13 Sep snapshot, 42
> nodes, epoch 19 prompt), then re-run the three superseded patchers' epoch
> bookkeeping by hand. Everything below this line describes the 3–6 Sep
> build as it was, and is kept because the sub-workflow still exists.

## Purpose

When a resident asks for a person, or the bot decides one is needed, somebody
at Homies has to *find out*. All staff share one WhatsApp number through
Chatwoot, so a handover can never ring a representative's phone: it has to mark
the conversation, route it to a department, and notify people inside Chatwoot.
Until 3 Sep `transfer_to_human` wrote a Supabase row nobody read and changed
nothing in the inbox; the bot kept answering, and its line "the message reached
a Homies representative and is marked urgent" was untrue.

## Behaviour

**Three paths, one step.** The model's `transfer_to_human` call, the
`לדבר עם נציג` tap, and the promise backstop (a reply that says "I'm passing
this on" with no tool behind it) all invoke the n8n sub-workflow
**"Homies — Hand to a person"**, which does, in order:

1. Reads the conversation. A probe's invented conversation 404s here and the
   workflow exits without writing.
2. Guards: a conversation already handed over in the last 24 hours, still open
   and with no person on it, is left alone — unless the new reason is
   `emergency` and the stored one was not, which is an upgrade.
3. Decides the department: the tool's `department` argument (the model's
   judgment, no keyword table) or, when missing, `emergency` → Operations and
   everything else → Service. Priority `urgent` for an emergency, `high`
   otherwise.
4. **In office hours (Sun–Thu 09:00–17:00 Israel), posts a private note that
   @mentions the department's team.** Since 14 Sep evening the note is in
   plain words for a rep: the mention, *דייר צריך מישהו מכם*, *סיבה*, the
   resident's phone, *מה הדייר רוצה*, the last messages, and one *מה
   לעשות* line (answer here and the bot stops; the 10-minute sentence only
   on an emergency). No "source", "escalation" or "handover" words; only
   the backstop adds a sentence saying why the note exists. That mention is the alert: every member
   gets a Chatwoot notification (bell, a Windows toast from the browser on
   their PC, email since 6 Sep for any seat that turns it on). Out of hours nothing is posted; the thread is labelled
   `after-hours` and the first tick after 09:00 pages it.
5. Stamps the state on the conversation (`handover_at`, `handover_reason`,
   `handover_department`, `handover_source`, `handover_paged_at`,
   `handover_escalation`), sets the priority, assigns the team, and writes the
   labels `handover` + `handover-<department>` as a union with what was there.

**The escalation ladder** runs on the minute ticker ("Homies — Chatwoot
handback"), office hours only: paged 10 minutes ago and still nobody on it →
the team again plus Management, priority urgent, label `escalated`; 15 more
minutes at level 1 → every team; then it stops. Each step re-stamps
`handover_paged_at`, so a tick never repeats an action, and a failed stamp
simply re-pages a minute later.

**Taking it.** A paged conversation lands in every team member's **Mentions**
and **Participating** views at once (Chatwoot adds a mentioned user as a
conversation participant), so it is visible before anyone owns it. The first
representative who replies to the resident claims the thread (the existing
reply-claim node) and the bot goes quiet on it.

**Answering is what ends a handover, not a name on the thread.** The ticker
reads Chatwoot's `waiting_since`, which only a human agent's public reply
clears -- the bot's own replies never do. On the first tick after a reply the
handover is `served`: its `handover`, `handover-*`, `after-hours` and
`escalated` labels come off and `handover_answered_at` is stamped. Until then
it keeps escalating, even if somebody has clicked "assign to me" and gone
quiet. A served thread that later goes quiet for 15 minutes is handed back to
the bot as before; an unanswered handover is never handed back, because that
would strip the labels the ladder needs to find it again.

**While it waits, the bot keeps answering** (owner's decision, 3 Sep), so a
22:00 follow-up is never met with silence. The resident is told, in the bot's
own words, that the team has it and that someone will get back; never which
department. The injected context now carries the time of day, so the bot can
say the office is closed when it is.

## Interface

**Sub-workflow "Homies — Hand to a person"** (Execute Workflow trigger)

| Input | Type | Notes |
|---|---|---|
| `conv_id` | number | Chatwoot display id |
| `phone` | string | E.164, for the note |
| `reason` | string | `caller_request`, `emergency`, `out_of_scope`, `not_understood` |
| `department` | string | `collections` / `operations` / `management` / `service`, or empty |
| `description` | string | what the model recorded, Hebrew |
| `source` | string | `tap`, `tool`, `backstop` |
| `mode` | string | `new` (bot), `page` / `escalate1` / `escalate2` / `served` (ticker) |
| `now_override` | string | ISO, tests only |
| `channel` | string | `whatsapp` (default) or `voice` (14 Sep); stamped as `handover_channel` |

Returns `{ ok, conv_id, mode, department, paged, in_hours }`, or the trigger
item with an `error` when the conversation does not exist.

**`transfer_to_human`** gained an optional `department` argument (enum above).
The Edge Function ignores it; only the sub-workflow reads it.

### Voice (14 Sep)

The inbound voice agent's `notify_team` (`scripts/vapi_tools.py`, reasons
`payment billing move contract quote emergency caller_request language other`)
posts to the Edge Function, which writes its rows as before and then, for the
intake assistant only, POSTs `{call_id, phone, building, unit, identifier,
label, reason, department, description, source}` to the n8n webhook
`/webhook/homies-voice-note` (header `x-homies-secret`, its own fresh secret;
3 s, two attempts, never blocks the tool). **"Homies — Voice team note"**
(`scripts/n8n_voice_note.py`) answers on receipt, then: the contact is the
**call** (`identifier: voice:call:<id>`; the apartment, canonical, is its
name and the number its phone, which is how a later call finds it again —
three searches, one pick: call, phone, label); its open conversation in the
Voice inbox from the last 24 h, else a new one carrying `additional_attributes`
`{channel, call_id, building, unit, phone}`; the caller's words as an
**incoming** message (what sets `waiting_since`, so the ticker's `served`
sweep leaves it alone); then this sub-workflow, `mode: new, channel: voice`,
no wait. The note ends (words of 14 Sep evening): *"מה לעשות: זאת הייתה
שיחת טלפון עם הבוט והיא כבר נגמרה, אז מה שכותבים כאן הדייר לא רואה.
מתקשרים לדייר למספר שלמעלה / אין מספר, אז מתקשרים לדייר לפי הכתובת
שלמעלה. כשסיימתם, סוגרים את השיחה הזאת כאן (Resolve)."* Emergencies
escalate on the same ladder; a
resolve or a public reply ends it. **The backstop:** the end-of-call report
carries every spoken line and every tool call; when the bot's lines say the
team knows or promise a call-back and no `notify_team` ran, the Edge Function
posts the same note with `source: backstop` from the caller's own turns.

## Data

Chatwoot, account 2: labels `handover`, `handover-collections`,
`handover-operations`, `handover-management`, `handover-service`,
`after-hours`, `escalated`; conversation custom-attribute definitions for the
nine `handover_*` keys (`handover_channel` and `handover_reasons` added
14 Sep); `priority`; the team. Inbox 2 **Homies — Voice** (API channel,
auto-assign off, created by `scripts/chatwoot_voice_inbox.py`; id in `.env`
as `CHATWOOT_VOICE_INBOX_ID`). Supabase is unchanged:
`call_outcomes` and `interactions.disposition` are still written by the Edge
Function exactly as before.

## Acceptance

1. `python scripts/n8n_handover_test.py` passes its eight cases on the test
   conversations: new in hours (one note, high, team, labels, stamp); duplicate
   (skipped); emergency upgrade (urgent, second note, department label
   replaced); escalate1 (Management mentioned, level 1); escalate2 (every team,
   level 2, attributes intact); new after hours (no note, `after-hours`,
   `handover_paged_at` empty); page at 09:00 (note, label gone, stamp set);
   missing conversation (no writes). Passed 3 Sep.
2. Every patch script reports "Nothing to do" on a second run:
   `n8n_handover.py`, `n8n_whatsapp_handover.py`, `n8n_handback_escalate.py`.
3. `scripts/check_whatsapp.py` and `scripts/probe_whatsapp.py` stay green after
   the wiring (a probe's handover exits on the 404 and the reply still goes
   out).
4. On the owner's handset, tapping `לדבר עם נציג`: the conversation shows
   `handover`, `handover-service`, priority high, team Service, the stamp, and
   one private note mentioning the team — and the bot still answers the next
   message.
5. A seat in the Service team gets the alert. **Proven 3 Sep, server and
   screen:** with the owner's own login in the Service team and team
   auto-assign OFF, one page produced a `conversation_mention` notification
   on that account in the same second as the note (09:42:23 UTC), with no
   assignee. The toast needed one more step: the push toggle showed ON while
   the server held no push subscription (the browser had never finished
   registering). After the owner re-enabled push in the browser the
   subscription registered (10:19 UTC); the next page (10:20:06) and a direct
   mention (10:21:26) each ran a real push job, and the owner confirmed the
   Windows toast on the PC. The delay was not timed. **Email proven 6 Sep**,
   once SMTP existed: the same mention path sent
   "You have been mentioned in conversation [ID - 53]" to the seat's mailbox
   in 386 ms, confirmed received.
6. Left unclaimed in office hours, on the real clock, 3 Sep: Management paged
   at +10:17 (09:52:40), every team at +26:18 (10:08:41), priority urgent,
   `escalated`, level 2, and nothing after that. The bot stayed unassigned
   throughout. Repeated on the 10:20:06 page: Management at 10:30:40, every
   team at 10:46:40, same result.
7. A reply from a seat claims the thread; 15 quiet minutes later it is
   unassigned, the handover labels are gone, and the bot resumes.

## Out of scope

Side channels (email on every handover, WhatsApp templates to staff, Telegram,
SMS) — Chatwoot only, by decision. The outbound debt agent's transfers (same
handler, unchanged; a follow-up if wanted). The English twin. An on-call path at night. Round-robin to one
named person. A dashboard queue. Creating the 19 seats, populating the teams,
enabling browser push on each representative's PC and setting each seat's
notification preferences — those are the owner's, and nothing here notifies
anyone until they exist. The representatives work on PCs; the Chatwoot mobile
app plays no part.
