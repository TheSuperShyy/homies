# The client's old ManyChat bot — scan of 22 Sep 2026

Read through the ManyChat API with the key the owner put in `.env` on 22 Sep
(`MANYCHAT_API_KEY`, `scripts/manychat_api.py`, read-only: eight GET calls,
no subscriber lookups, nothing written). Page **הומי'ז ניהול ואחזקת מבנים**
(Pro, `Asia/Jerusalem`), four flows, thirteen custom fields, one tag, one
entry link. The raw page-level answer is in
`docs/handover/manychat-export-2026-09-22.json`. This is the same account the
Make scan of 17 Sep saw from the other side: field `10802746` = `טלפון` and
the "done" flow `content20240325164237_508609` are both on the list.

## The short version

**The API lists the bot's nouns, not its steps.** ManyChat's own spec has
thirteen read endpoints — the page, its flows *by name*, tags, custom fields,
growth tools, widgets, OTN topics, bot fields, and five subscriber lookups —
and none returns a flow's content. Message wording, buttons, the order of
the questions and the conditions between them are visible only in the
ManyChat editor, which the owner opened on 22 Sep. The other twenty-one
endpoints are writes and were not called.

So the branch-by-branch section below is a **reconstruction**, and each
branch says what it rests on: what a handset saw on 10 Sep
(`docs/features/11-whatsapp-bot/context.md`, "The incumbent bot, seen live"),
which custom field the step fills, and which Make hook the finished intake
is posted to (`docs/discovery/make-scan-2026-09-17.md`). Where the three
sources say nothing, the row says *unknown — confirm in the editor* rather
than guessing. The last section lists exactly what the editor still has to
supply.

## What the API shows

### The four flows

| ns | name | what it is | evidence |
|---|---|---|---|
| `wa_default` | WhatsApp Default Reply | The bot. ManyChat runs the default reply for any WhatsApp message that no keyword or open flow claims, so every conversation starts here: the greeting, the router and the forms. | 10 Sep handset; the Make hooks |
| `content20240325164237_508609` | קריאתך טופלה בהצלחה (מהמאנדיי) | The "done" message. Make scenario 898283 sends it when a Monday item's status turns בוצע: find the subscriber by the phone field, `sendFlow` this ns. No run in Make's log window as of 17 Sep. | Make 898283 |
| `content20240331074346_968302` | לאחר 23 שעות - האם פנייתך עדיין רלוונטית | A follow-up at 23 hours — "is your request still relevant?" Twenty-three, not twenty-four, because Meta allows free text only inside 24 hours of the resident's last message; the nudge is timed to need no template. Trigger and whether it is live: unknown. | name only |
| `content20260730113317_363910` | Untitled | Created 30 Jul 2026, two years after the rest. A draft, a test, or something live — unknown. | name only |

No folders, no widgets, no OTN topics, no bot fields.

### The thirteen custom fields — the questionnaire

Every field is either a question the form asked or a value the bot wrote.
Ids are ManyChat's; names are verbatim.

| id | field | meaning | branch |
|---|---|---|---|
| 10790949 | שם מלא | full name | identification |
| 10802746 | טלפון | phone (also ManyChat's own `whatsapp_phone`) | identification; the key Make and the "done" scenario match on |
| 10772897 | כתובת | address | identification |
| 10790958 | קומת הדייר | resident's floor | identification |
| 10790961 | דירת הדייר | resident's flat | identification |
| 10772906 | כמות קומות בבניין | floors in the building | building profile |
| 10772912 | כמות דיירים בבניין | flats / residents in the building | building profile |
| 10791312 | חברת המעליות בבניין | the building's elevator company | building profile; used by the elevator email |
| 10802484 | סיכום דיווח אחרון | summary of the last report | the fault as described — kept on the subscriber, so the bot remembers the last report |
| 10802488 | דיווח למעלית | elevator fault report | elevator branch |
| 10802513 | קריאה לאב הבית | call for the house manager | אב הבית branch |
| 10813193 | תמונה | photo URL | service call, optional |
| 10813846 | תמונה אריי | photos, array | service call, several photos |

Tag: `טסטים` (43703507) — a marker for test subscribers; whether any flow
or Make scenario checks it: unknown. Growth tool: `WhatsApp URL #1`
(23663000, `messenger_ref_url`) — a link that opens WhatsApp to the number
with a reference, the kind of thing a website button uses.

### What the API cannot show, and what was not touched

Steps, wording, buttons, delays, conditions, and which flow is active. Nothing
in the account was created, changed, tagged or sent; `manychat_api.py` has no
write path and no subscriber call.

## The old bot, reconstructed

**Entry.** A resident writes to the number (or taps the website link →
`WhatsApp URL #1`). Any message that no open flow claims runs
`wa_default`. What the handset saw on 10 Sep, verbatim:

> `היי! איזה כיף שפניתם אלינו! לפניכם נתב שיחות 🔀, איך נוכל לעזור?`
> one button `לחצו כאן להמשך`, opening six rows:
> תשלום ועד בית/גביה 💰 · הנהלת חשבונות 📋 · קריאת שירות 🙋 · הצעת מחיר 🤝 · אב הבית 👷 · מעבר לנציג 🔀

A tap echoes the choice, then (for the rows with a form):
`על מנת שנוכל לפתוח את הקריאה כראוי - ענו בבקשה על השאלות הבאות` →
`מהו שמכם המלא?` — a menu tree with forms, not a conversation.

**1. קריאת שירות 🙋 — service call → Monday.** Form: full name → (phone)
→ address → floor → flat → the building profile (floors, number of flats,
elevator company) → the fault (`סיכום דיווח אחרון`) → photo, optional
(`תמונה` / `תמונה אריי`). Then an External Request to Make hook 432824
("קריאה כללית התקבלה במאני צ'אט") → scenario 887568 creates an item
"קריאת שירות מהווצאפ" on board **1270620891** (משימות שטח), assigned to a
team and a person, with the phone and address in columns, posts the whole
intake as an update, and attaches the photo if there is one. Evidence: the
10 Sep form opening, the field list Make receives (all thirteen), Make's
run log (~3/week, last 17 Sep 06:09). *Confirm in the editor:* the question
order, whether the building profile is asked every time or only once
(fields persist on the subscriber, so a returning resident may skip them),
the exact wording of the closing message.

**1a. Elevator — the same call, plus an email.** If the fault is the
elevator, the description goes into `דיווח למעלית` and a second hook fires:
430282 ("התקבלה קריאת שירות למעלית") → scenario 881814 → Gmail to
`Office@homies-management.co.il`, subject "נפתחה קריאת שירות על מעלית
בווצאפ", body: address, name, floor and flat, **the elevator company**, the
fault. The email goes to the office, not to the elevator company. Evidence:
Make 881814 (runs 17 Sep 07:02, 6 Sep, 19 Aug). *Confirm:* how the bot
decides it is an elevator fault — a menu row inside the service-call form, a
yes/no question, or a keyword.

**2. אב הבית 👷 — house-manager call → Monday.** A form ending in
`קריאה לאב הבית` (what the house manager is needed for). Make has no
separate hook for it, and the general-call scenario 887568 receives that
field, so the likeliest route is the same Monday item as a service call.
Evidence: the field, the 887568 field list. *Confirm:* the questions, and
whether it really posts to 432824.

**3. הצעת מחיר 🤝 — price quote → leads.** A form for a prospective
customer rather than a resident: name, phone, email, address, floors,
number of flats, floor, flat → hook 432788 ("בקשה להצעת מחיר") → scenario
887490 looks the phone up on the leads board **1270706127**, updates the
existing lead or creates "פנייה חדשה מהווצאפ". Evidence: Make 887490's
field list (last used 1 Sep). *Confirm:* wording; whether email is asked.

**4. תשלום ועד בית/גביה 💰 and 5. הנהלת חשבונות 📋 — unknown.** No custom
field belongs to either and no Make hook receives them, so they are either a
text answer (how to pay, whom to call, a link) or a hand-off inside ManyChat.
*Confirm in the editor — these two rows are the ones nothing else records.*

**6. מעבר לנציג 🔀 — a human.** No hook. In ManyChat this is normally
"open the conversation in Live Chat and stop the bot", sometimes with a
"someone will get back to you" line. *Confirm.*

**After the call: two timed flows.** (a) The "done" message: a Monday
status change to בוצע → Make 898283 → `sendFlow`
`content20240325164237_508609` to the subscriber found by phone. Make logged
no run for it in the window read on 17 Sep, so either nobody moves the
status or the Monday webhook is stale; the resident may not have received a
"done" in a month. (b) The 23-hour nudge `לאחר 23 שעות - האם פנייתך עדיין
רלוונטית`: name only. The natural shape is a Smart Delay of 23 h after the
form, a condition, then the question; whether it is wired and live is
*unknown*.

**Memory.** Because fields live on the subscriber, the old bot "remembers"
a resident: their address, flat, building and last report persist between
conversations. That is a feature of ManyChat's data model, not of the
flow — and the reason a second report may skip questions (unconfirmed).

## Feature list — everything the old bot has, one line each

1. **Entry link** — a `messenger_ref_url` growth tool for a website button.
2. **Default-reply router** — every unclaimed message restarts the greeting and menu.
3. **Fixed greeting + one "continue" button + a six-row list** (payments, accounting, service call, quote, house manager, human).
4. **Identification form** — full name, phone, address, floor, flat, asked as separate questions.
5. **Building profile** — floors, number of flats, elevator company, asked of the resident.
6. **Service call** → Monday item on משימות שטח, with the whole intake as an update.
7. **Photo upload** — single or several, attached to the Monday update.
8. **Elevator fault** — separate description field + an email to the office naming the elevator company.
9. **House-manager call** — its own row and field, filed with the service calls.
10. **Price quote** → leads board, deduplicated by phone.
11. **Payments row** — content unknown.
12. **Accounting row** — content unknown.
13. **Human hand-off row** — mechanism unknown.
14. **Last-report memory** — the fault description kept on the subscriber.
15. **"Done" message** — driven by a Monday status change (silent for a month).
16. **23-hour follow-up** — "is your request still relevant?", timed inside Meta's free-text window.
17. **Test tag** (`טסטים`).
18. **The stack** — Monday is the ticket system, Make the router, ManyChat the resident record; nothing writes to OXS.
19. **A flow created 30 Jul 2026 ("Untitled")** — contents unknown.

## Old vs ours — where each feature stands in our bot today

"Ours" is the n8n bot at epoch 50 with the tools in
`supabase/functions/debt-tools/index.ts`; the *adapt?* column is left for the
owner — nothing here decides.

| feature | old bot | ours today | adapt? |
|---|---|---|---|
| Entry link | `WhatsApp URL #1` ref link | none; residents write to the number | |
| Greeting + router | fixed greeting, "continue" button, six rows, every time | fixed greeting + three reply buttons (פתיחת קריאת שירות · מצב קריאה קיימת · משהו אחר) on a bare hello only; `show_menu` on model judgment; a hello *with* a matter gets no buttons (20 Sep); three rows by decision — WhatsApp renders four+ as a list | |
| Identification | five separate questions | conversation: building and flat asked together, the sender's number is the phone (18 Sep); full name + phone only where money is read (`get_balance`); `verify_address` checks the building is ours | |
| Building profile | floors, flats, elevator company asked of the resident | not asked — OXS holds building data; the elevator company per building is an open item (needs Yariv's list, see HANDOVER) | |
| Service call | → Monday 1270620891 | `open_request` → `requests` with a `255-NNNN-YY` reference read back to the resident; dashboard `/tickets`; OXS mirror built but OFF; Monday not written | |
| Photo | field → Monday attachment | `store_media` → `request_media` + private bucket, thumbnails on the dashboard (17 Sep); the bot never invites a photo | |
| Elevator | own description field + email to the office with the elevator company | a service call like any other; no email; no elevator-company field | |
| House manager | own row + field → Monday | `notify_team` ("אב הבית: … רושם לצוות", prompt facts block) | |
| Price quote | → leads board 1270706127 | `notify_team` ("הצעת מחיר … נרשמת לצוות"); no leads board | |
| Payments row | unknown | `get_balance` (name + phone gate), `get_payment_link` (the resident's own OXS link, to the number on file), "I want to pay" → ticket + team note; the debt voice agent sends the link mid-call | |
| Accounting row | unknown | `notify_team` for billing disputes and documents; office facts (hours, phone, address) in the prompt | |
| Human hand-off | unknown | `notify_team`, and a human replying in Chatwoot pauses the bot for that conversation (`_claim`) | |
| Last-report memory | subscriber field | `get_request_status` by reference or by building + flat, from the database, not from memory | |
| "Done" message | Monday status → ManyChat flow; silent a month | `ticket_resolved_he` Meta template from the `ticket_notices` outbox on a 2-minute cron (22 Sep; PENDING at Meta) | |
| 23-hour follow-up | a flow, trigger unknown | none | |
| Test tag | `טסטים` | test prefixes skipped in code (`TEST_PREFIXES` in the Edge Function) | |
| General info / FAQ | not seen in the menu | `get_service_info` (services, regions, fee, SLA) | |
| Ticket status | only the "done" push | `get_request_status`, on request | |
| Ticket system / router | Monday / Make | Supabase + dashboard / n8n | |

Four rows are the ones I would look at first, as suggestions only: the
**23-hour nudge** (cheap for us — a cron on open tickets, and at 23 h it
needs no template); the **elevator company per building** (already open,
this is a second reason); an **entry link** for the website once the number
moves; and whether a bot ticket should also land on **Monday 1270620891**
before cutover (the open question from the Make scan, unchanged).

## Still to fill in from the editor

The owner can see the flows (22 Sep). What the API cannot supply and this
doc still needs, per flow — a screenshot with every branch expanded, or
Flow → Share link:

- `WhatsApp Default Reply`: the exact wording of every step; the button
  labels; the order of the form questions; how the elevator sub-branch is
  chosen; what the **payments**, **accounting** and **human** rows do;
  whether the building profile is asked every time; the closing message
  after a call is filed; whether `טסטים` gates anything.
- `לאחר 23 שעות`: what triggers it, what it says, and whether it is live.
- `קריאתך טופלה בהצלחה (מהמאנדיי)`: the wording (ours is now a Meta
  template; theirs may be free text, which would explain the silence if
  residents were outside the 24-hour window).
- `Untitled` (30 Jul 2026): what it is.

When those arrive, the reconstructed rows above get replaced by the real
thing and the "confirm" notes go.
