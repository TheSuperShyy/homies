# The client's old ManyChat bot — scan of 22 Sep 2026

Two sources, both read on 22 Sep and both read-only. **The API**, with the
key the owner put in `.env` (`MANYCHAT_API_KEY`, `scripts/manychat_api.py`:
eight GET calls, no subscriber lookups, nothing written): page
**הומי'ז ניהול ואחזקת מבנים** (Pro, `Asia/Jerusalem`), four flows, thirteen
custom fields, one tag, one entry link; raw answer in
`docs/handover/manychat-export-2026-09-22.json`. **The editor**: the owner
opened the `WhatsApp Default Reply` flow and sent a screenshot of the whole
canvas; every step, question, button and hook below is read from it. This is
the same account the Make scan of 17 Sep saw from the other side — field
`10802746` = `טלפון` and the "done" flow `content20240325164237_508609` are
on both lists.

## The short version

**The API lists the bot's nouns, not its steps.** ManyChat's own spec has
thirteen read endpoints — page, flows *by name*, tags, custom fields, growth
tools, widgets, OTN topics, bot fields, five subscriber lookups — and none
returns a flow's content. The other twenty-one are writes and were not
called. The steps came from the editor instead, the same day.

**The bot in one paragraph.** One menu with six doors. Five of the six start
with the same four questions (full name, address, floor, flat). Then each
door does one thing: *payments* pushes the resident to the OXS app and
otherwise hands to a person; *accounting* and *talk to a rep* take a free-text
message and hand to a person; *service call* asks whether the call was
already opened in the app, then whether it is general or an elevator fault,
takes a description and an optional photo, and posts it to Make (→ Monday) or,
for an elevator, asks for the elevator company and posts to Make (→ an email
to the office); *quote* skips the four questions, asks address, floors and
number of flats and posts each answer to Make (→ the leads board); *house
manager* takes a description and leaves it for a person. Every question the
resident does not answer closes the conversation — that is what all the red
lines on the canvas are. "Back to the main menu" returns to the menu.

It never reads or writes OXS. It sends people to the OXS app three times
(pay there, open calls there, get updates there). Two doors assign the
conversation to **"Unknown user"** — a team member ManyChat no longer has —
so the house-manager and quote chats may be landing on nobody's desk.

## What the API shows

### The four flows

| ns | name | what it is |
|---|---|---|
| `wa_default` | WhatsApp Default Reply | The bot. ManyChat runs the default reply for any WhatsApp message no keyword or open flow claims, so every conversation starts here. Read in full below. |
| `content20240325164237_508609` | קריאתך טופלה בהצלחה (מהמאנדיי) | The "done" message. Make scenario 898283 sends it when a Monday item's status turns בוצע: find the subscriber by the phone field, `sendFlow` this ns. No run in Make's log window as of 17 Sep. Wording not seen. |
| `content20240331074346_968302` | לאחר 23 שעות - האם פנייתך עדיין רלוונטית | A follow-up at 23 hours — "is your request still relevant?" Twenty-three, not twenty-four: Meta allows free text only inside 24 hours of the resident's last message, so the nudge is timed to need no template. Trigger, wording and whether it is live: not seen. |
| `content20260730113317_363910` | Untitled | Created 30 Jul 2026, two years after the rest. Not seen. |

No folders, widgets, OTN topics or bot fields.

### The thirteen custom fields, matched to the steps that set them

| id | field | meaning | set where |
|---|---|---|---|
| 10802746 | טלפון | phone | the first action of the flow copies ManyChat's `phone` into it; the key Make and the "done" scenario match on |
| 10790949 | שם מלא | full name | the four-question form |
| 10772897 | כתובת | address | the four-question form; also the quote's first question |
| 10790958 | קומת הדייר | resident's floor | the four-question form |
| 10790961 | דירת הדייר | resident's flat | the four-question form |
| 10772906 | כמות קומות בבניין | floors in the building | **the quote flow only** — not asked of residents |
| 10772912 | כמות דיירים בבניין | flats in the building | **the quote flow only** |
| 10802484 | סיכום דיווח אחרון | summary of the last report | the general service call's "what would you like to report?" |
| 10802488 | דיווח למעלית | elevator fault report | the elevator branch's description |
| 10791312 | חברת המעליות בבניין | elevator company | the elevator branch's "which elevator company?" |
| 10802513 | קריאה לאב הבית | call for the house manager | the house-manager door's description |
| 10813193 | תמונה | photo URL | the general service call's photo step |
| 10813846 | תמונה אריי | photos, array | same step, several photos |

Fields live on the subscriber, so a returning resident's address and last
report are still there next time — ManyChat's data model, not a step in
the flow; the flow asks the four questions again regardless.

Tag: `טסטים` (43703507) — a marker for test contacts; nothing in `wa_default`
checks it. Growth tool: `WhatsApp URL #1` (23663000, `messenger_ref_url`) —
a link that opens WhatsApp to the number with a reference, for a website
button.

## `WhatsApp Default Reply`, as the editor shows it

### The map

```
message arrives (no open flow)
  → save phone into טלפון, assign a team member
  → MENU  "היי! איזה כיף שפניתם אלינו! לפניכם נתב שיחות 🔀, איך נוכל לעזור?"
          [לחצו כאן להמשך] → six rows

  💰 תשלום ועד בית/גביה ─ FORM ─ "paid in the app?" ─┬─ yes but help → "passed to a rep" → OPEN, team member
                                                     ├─ no → app link, "still need help?" ─┬─ yes → same
                                                     │                                     └─ no → "closed 🔒" → CLOSED
                                                     └─ back to menu → MENU
  📋 הנהלת חשבונות ──── FORM ─ "write what you need, a rep will attend" → OPEN, team member
  🙋 קריאת שירות ────── FORM ─ "opened in the app?" ─┬─ yes → "it's being handled; more help?" → no: CLOSED / yes: MENU
                                                     ├─ no → "general or elevator?"
                                                     │     ├─ general → describe → photo? → (photo) → MAKE hook khz… → CLOSED
                                                     │     │                                → "thanks, use the OXS app for live updates"
                                                     │     └─ elevator → "contacted the elevator company?"
                                                     │           ├─ yes → "if it repeats, write the details" → CLOSED
                                                     │           └─ no → which company? → describe → MAKE hook ve6… → "we'll pass it on in office hours"
                                                     └─ back to menu → MENU
  🤝 הצעת מחיר ───────── (no form) MAKE hook mgv… → intro + address / floors / flats (hook after each) → "a rep will call" → Unknown user
  👷 אב הבית ─────────── FORM ─ describe → OPEN, Unknown user → "the house manager will contact you; urgent: call the office" [open a service call]
  📱 מעבר לנציג ──────── FORM ─ "write what you need, a rep will attend" → OPEN, team member

  any question left unanswered ──────────────────────────────────────────────→ CLOSED   (every red line)
```

FORM = the same four questions on five of the six doors (five copies of one
block): *"על מנת שנוכל לטפל בפנייתכם כראוי - ענו בבקשה על השאלות הבאות"* →
`מהו שמכם המלא?` → `מהי הכתובת ממנה אתם פונים?` → `באיזו קומה אתם גרים?` →
`באיזו דירה אתם גרים?`. (The service-call copy opens with *"…לפתוח את
הקריאה כראוי"*.) OPEN / CLOSED are ManyChat inbox states; "team member" is
a live assignee, "Unknown user" is not.

Which of the two free-text doors (accounting, rep) is which copy of the form
is the one thing the canvas does not settle — they end at the same step, so
it does not matter to the resident.

### The doors, verbatim

**Start.** Trigger "When…" → `Set User Field טלפון to {phone}`, `Assign
conversation: Choose a team member` → the menu:
`היי! איזה כיף שפניתם אלינו! לפניכם נתב שיחות 🔀, איך נוכל לעזור?`, button
`לחצו כאן להמשך`, rows `תשלום ועד בית/גביה 💰` · `הנהלת חשבונות 📋` ·
`קריאת שירות 🙋` · `הצעת מחיר 🤝` · `אב הבית 👷` · `מעבר לנציג 📱`.

**💰 Payments.** FORM → `האם ניסית לשלם באפליקציה? 📱 זה ממש נוח ומבטיחים!`
[`כן, אבל אשמח לעזרה` / `לא` / `בחזרה לתפריט הראשי`].
*Yes-but-help* → `תודה, פנייתך הועברה לנציג ותטופל בהקדם ✅` → mark Open,
assign a team member. *No* → `ממליצים לכם בחום לנסות את אפליקציית שירות
הלקוחות שלנו בכתובת: https://mc.ht/s/XXXXXX ולשלם דרכה בכרטיס אשראי. האם
בכל זאת תצטרכו עזרה?` [`כן, אשמח לעזרה` → the same "passed to a rep" /
`לא תודה` → `תודה, פנייתך נסגרה 🔒` → Closed]. The link is a ManyChat short
link (the OXS app, by context).

**📋 Accounting and 📱 Talk to a rep.** FORM → `אנא כתבו לנו כיצד נוכל
לעזור 😊, נציג מייד יפנה ויעמוד לרשותכם` (waits for text) → on reply: assign
a team member, mark Open. No hook — the text stays in the ManyChat inbox.

**🙋 Service call.** FORM → `האם פתחת קריאה באפליקציה?` [`כן` / `לא` /
`בחזרה לתפריט הראשי`].
*Yes* → `תודה! קיבלנו אותה והיא בטיפול 🛠️ נעדכן בהודעה חוזרת בנוגע לסטטוס
הקריאה. האם יש לך צורך בעזרה נוספת?` [`לא` → Closed / `כן` → menu]. Nothing
is filed; the bot takes the resident's word that the app has it.
*No* → `האם קריאתך הינה קריאה כללית או שהיא קשורה למעלית? 🏢`
[`קריאה כללית` / `הקריאה קשורה למעלית`].
- *General* → `על מה תרצו לדווח? ✍️` (text → `סיכום דיווח אחרון`) → `תודה,
  האם יש גם תמונה שיכולה לעזור לנו להבין? 📸` [`יש לי תמונה לצרף!` /
  `אין לי תמונה לצרף`] → with a photo: `אנא צרפו מטה את התמונה לתיאור
  הבעיה 👇` (waits for an image → `תמונה`) → **External Request
  `hook.eu2.make.com/khz…`** (Make hook 432824, scenario 887568 → Monday
  board 1270620891, photo attached) + mark Closed → `תודה רבה על פנייתך!
  קיבלנו אותה ונטפל בה בהקדם! רצוי לפתוח קריאות באפליקציית OXS 📱 כדי לקבל
  עדכונים בלייב! תודה`. Without a photo: the same hook and the same closing
  line. **The resident gets no reference number.**
- *Elevator* → `האם יצרת קשר עם חברת המעליות? 📞` [`כן` / `לא`].
  *Yes* → `אם כך, רק במידה ויש בעיה חוזרת שלא מקבלת מענה ראוי 🔁, אנא כתבו
  לנו במפורט ואנו ניצור עימם קשר` (waits for text) → mark Closed. **No
  hook** — a repeated elevator problem is written and closed. *No* → `מי
  חברת המעליות בבניין?` (text → `חברת המעליות בבניין`) → `אוקי, אנחנו נעשה
  זאת עבורך באהבה ❤️. על מנת שנוכל להעביר את פנייתך אנו זקוקים לתיאור
  התקלה ובמידה וידוע לך - מי חברת המעליות בבניין? במידה והמדובר בתקלה דחופה
  אנא התקשרו אלינו בטלפון 📞 077-6687949` (text → `דיווח למעלית`) →
  **External Request `hook.eu2.make.com/ve6…`** (Make hook 430282,
  scenario 881814 → Gmail to `Office@homies-management.co.il` naming the
  elevator company) → `תודה, פנייתך התקבלה ✅ אנו נעביר אותה לחברת המעליות
  בשעות פעילות המשרד`. The office forwards; the bot does not reach the
  elevator company itself.

**🤝 Quote.** No FORM. **External Request `hook.eu2.make.com/mgv…`** first
(Make hook 432788, scenario 887490: find the lead on board 1270706127 by
phone, create `פנייה חדשה מהווצאפ` if none) → `היי! תודה שפניתם אלינו, אנחנו
הומיז ניהול ואחזקת מבנים, משרדינו ממוקמים ברחוב בצלאל 1 ברמת גן. נשמח לדבר
איתכם על מנת להבין את צרכי הבניין ולפעול בהתאם :) בינתיים ענו לנו בבקשה על
השאלות הבאות ⏰` → `מהי כתובת הבניין?` → `כמה קומות יש בבניין?` → `כמה
דיירים יש בבניין?` — **the same hook fires again after each answer**, which
is why the Make scenario is written as update-or-create → `מעולה! תודה, נציג
יצור אתכם קשר בהקדם ונשמח לעזור גם לרשותכם 📞 ניתן להתקשר אלינו בטלפון:
077-6687949` → assign conversation: **Unknown user**.

**👷 House manager.** FORM → `אנא תאר פנייתך על מנת שנוכל להעביר אותה לאב
הבית האחראי 👷` (text → `קריאה לאב הבית`) → mark Open, assign **Unknown
user** → `מעולה! תודה, אב הבית האחראי ייצור קשר בהקדם. לפניות דחופות אנא
התקשרו למשרד 📞 077-6687949 ניתן גם לפתוח קריאת שירות באפליקציית OKS או דרך
הכפתור מטה` [`לפתיחת קריאת שירות` → the service-call door] → mark Open,
assign Unknown user again. **No hook** — nothing reaches Make or Monday; the
message waits in the ManyChat inbox for a person who is not there.

**Timeouts.** Every "Waiting for…" step has *If contact has not responded* →
one node, `Mark conversation as Closed`. The wait length is not visible on
the canvas. A resident who pauses mid-form is closed without a word.

## Feature list — everything the old bot has, one line each

1. **Entry link** — a `messenger_ref_url` growth tool for a website button.
2. **Default-reply router** — every unclaimed message restarts the greeting and menu; the phone is copied into a field first.
3. **Fixed greeting + one "continue" button + a six-row list** (payments, accounting, service call, quote, house manager, rep).
4. **Identification form** — full name, address, floor, flat as four separate questions, on five of the six doors, every time.
5. **"Did you already do it in the app?" gates** — on payments and on service calls; "yes" ends the conversation with a reassurance and nothing filed.
6. **Push to the OXS app** — three times: pay there, open calls there, get live updates there.
7. **General service call** → Make → Monday item on משימות שטח, the whole intake as an update; no reference number to the resident.
8. **Photo, optional** — yes/no question, then one image, attached to the Monday update.
9. **Elevator fault** — "did you contact the elevator company?"; if not, company + description → Make → email to the office, which forwards in office hours.
10. **Quote for a prospect** — intro, three building questions, Make → leads board, updated after every answer.
11. **House-manager call** — description, left in the inbox for a person.
12. **Accounting / rep** — free text, handed to a team member.
13. **Back to the main menu** on the two three-button questions.
14. **Silent close on any unanswered question.**
15. **Last-report memory** — the description kept on the subscriber (a ManyChat property, not a step).
16. **"Done" message** — Monday status → Make → a ManyChat flow (silent a month).
17. **23-hour follow-up flow** — exists; not seen wired.
18. **Test tag** (`טסטים`), unused by this flow.
19. **The stack** — Monday is the ticket system for service calls, Make the router, ManyChat the inbox and resident record, OXS untouched.
20. **A flow created 30 Jul 2026 ("Untitled")** — not seen.

## Old vs ours — where each feature stands in our bot today

"Ours" is the n8n bot at epoch 50 with the tools in
`supabase/functions/debt-tools/index.ts`; the *adapt?* column is left for the
owner — nothing here decides.

| feature | old bot | ours today | adapt? |
|---|---|---|---|
| Entry link | `WhatsApp URL #1` ref link | none; residents write to the number | |
| Greeting + router | fixed greeting, "continue" button, six rows, every time | fixed greeting + three reply buttons (פתיחת קריאת שירות · מצב קריאה קיימת · משהו אחר) on a bare hello only; `show_menu` on model judgment; a hello *with* a matter gets no buttons (20 Sep); three by decision — WhatsApp renders four+ as a list | |
| Identification | four questions, five doors, every time | conversation: building and flat asked together (18 Sep), the sender's number is the phone; full name + phone only where money is read (`get_balance`); `verify_address` checks the building is ours | |
| "Already in the app?" gate | yes → reassurance, nothing filed | none — a described fault becomes a ticket; a status question reads the database (`get_request_status`) | |
| Push to the OXS app | three times | none in chat; the payment link *is* the resident's own OXS link (`get_payment_link`) | |
| Service call | → Monday 1270620891, no reference to the resident | `open_request` → `requests` with a `255-NNNN-YY` reference read back; dashboard `/tickets`; OXS mirror built but OFF; Monday not written | |
| Photo | yes/no question, one image → Monday attachment | `store_media` → `request_media` + private bucket, thumbnails on the dashboard; the bot never invites a photo, it keeps one that arrives | |
| Elevator | "contacted the company?" gate; company + description → email to the office; "repeated problem" → closed with no hook | a service call like any other; no elevator-company field (open item, needs Yariv's list); no email — the desk sees it on the dashboard | |
| House manager | description → inbox, assigned to a user who no longer exists | `notify_team` ("אב הבית: … רושם לצוות") | |
| Quote | three building questions → leads board, no form | `notify_team` ("הצעת מחיר … נרשמת לצוות"); no leads board | |
| Payments | app gate → app link → rep or close | `get_balance` (name + phone gate), `get_payment_link`, "I want to pay" → ticket + team note; the debt voice agent sends the link mid-call | |
| Accounting / rep | free text → team member | `notify_team`; a human replying in Chatwoot pauses the bot (`_claim`) | |
| Back to menu | on two questions | the menu returns on a bare hello or `show_menu` | |
| Unanswered question | silent close | nothing closes; the next message continues the conversation (memory epoch) | |
| Last-report memory | subscriber field | `get_request_status` by reference or building + flat | |
| "Done" message | Monday status → ManyChat flow; silent a month | `ticket_resolved_he` Meta template from the `ticket_notices` outbox on a 2-minute cron (22 Sep; PENDING at Meta) | |
| 23-hour follow-up | a flow, not seen wired | none | |
| Test tag | `טסטים` | test prefixes skipped in code (`TEST_PREFIXES`) | |
| General info / FAQ | not in the menu | `get_service_info` (services, regions, fee, SLA) | |
| Ticket status | only the "done" push | `get_request_status`, on request | |
| Ticket system / router | Monday / Make | Supabase + dashboard / n8n | |

Four rows I would look at first, as suggestions only: the **23-hour nudge**
(cheap for us — a cron on open tickets, and at 23 h it needs no template);
the **elevator company per building** (already open; this is a second
reason); an **entry link** for the website once the number moves; and
whether a bot ticket should also land on **Monday 1270620891** before
cutover (the open question from the Make scan, unchanged). And one thing to
tell Yariv regardless: **two doors of the live bot assign to "Unknown
user"** — house-manager and quote chats may be reaching nobody.

## Still not seen

The other three flows' content — the "done" message's wording (if it is
free text, residents outside the 24-hour window never got it, which would
explain the silence Make shows), what triggers the 23-hour nudge and whether
it is live, and what `Untitled` (30 Jul 2026) is. The timeout length on the
"waiting" steps. A screenshot of each of those three flows closes this.
