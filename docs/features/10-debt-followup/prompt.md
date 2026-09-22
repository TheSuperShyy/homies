# Outbound debt follow-up — agent prompt

Push with `python scripts/vapi_sync.py debt --apply`. Everything outside the
**System prompt** section is for us, not the model.

> **16 Sep 2026: the agent is open.** The system prompt is a ~3.5k fence in the
> inbound agent's shape (see the 16 Sep section below). Everything from here
> to that section describes the scripted agent that ran until 16 Sep and is
> kept as its record; the variables table is still the contract.

**Cut on 7 Aug from 67,789 characters to roughly a third of that.** Nothing was
deleted because it was wrong. What came out was the *evidence* — a day of
"on 7 Aug a resident said X and the agent did Y, which is why this rule exists".
Every one of those stories is in `docs/WORKLOG.md`, which is where a reader
looking for the reasoning should go. The model does not need the reasoning; it
needs the rule, once, close to where it acts.

The failures of 7 Aug were almost all *"the model did not find the rule"* rather
than *"the rule was wrong"*, and that failure gets likelier as the file grows.
**Adding a paragraph to this prompt now has a cost. Weigh it.**

## The rules for editing this file

**1. Describe what to convey. Do not write the Hebrew.** The model composes better
Hebrew than we can, and a scripted turn is a turn it cannot adapt. This is the
oldest rule in the file and it was broken eighteen times on 7 Aug — every loop got
patched with another verbatim line, the count went from 5 to 23, and the agent
became a player-piano that replayed the last roll whenever it was unsure. The
English twin has 7 fixed lines and adapts; that is the whole difference between
them.

**2. A line is fixed only if it has to be.** Three reasons qualify and no others:
Vapi speaks it literally (the opening), the wording carries legal or privacy
weight (not-the-account-holder, voicemail), or a test proved the model does
something worse when left to phrase it (the handover line — told only to call the
tool, it went silent on a hardship disclosure). The closing is fixed because
`endCallPhrases` matches on its words and nothing else hangs up the call.

**The ask-for-the-yes qualifies under the third reason and the evidence is
unusually clean.** Across twelve calls on 7 Aug: five where the agent never asked
whether to send the link — the amount came out between one and four times and
**the link was never sent, not once.** Seven where it did ask — the amount came
out once and four of them ended with the link on its way. Described as an
intention, the agent does not compose the question; it re-delivers the message it
already gave. Written as a line, it asks. That is what a fixed line is for, and
it is the only turn in the main flow that needs to be one.

**3. Constrain substance, not sentences.** *Call the tool before you speak* is a
rule. *Say these exact words* is a script. The first survives a conversation
going somewhere unexpected; the second is what produces the loops.

**4. Say what to do, not only what to avoid.** A prohibition leaves a model with
nothing to say when a turn is forced, and the nearest written line is what comes
out. Give it the next move.

**5. Anything written as a `>` line is spoken**, so it must be Hebrew here and
have a translation in `scripts/vapi_en.py`.

## The fixed lines a native speaker has to check

Ten: the opening, the ask-for-the-yes, the not-the-account-holder line, the
did-not-hear question, the could-not-identify closing, the handover line, the
ownership offer, the closing, and the voicemail message. Not forty.

The ownership offer is fixed under reason two — it carries privacy and legal
weight. It is the turn where a resident denies owing anything at all, and the
difference between *"shall I pass this to the team"* and *"I'm putting you
through"* is a promise the system cannot keep.

### The opening changed on 30 Aug, and it gave something up

`שלום, אה, מדבר מיכאל מחברת הומיז, שמנהלת את הבניין`
→ `שלום, מדבר מיכאל מהצוות של הומיז`, the client's wording, so both
agents introduce themselves the same way.

**What went with it: שמנהלת את הבניין.** This is a cold outbound call about
money, to someone with no caller ID, and that clause was the answer to the
question every such call raises — *why do you have my number?* It is gone,
which is a deliberate trade and not an oversight: the name Homies is
expected to carry it. If attempts start ending in *מי זה?* or hang-ups in the
first two turns, this line is the first place to look, and
`מהצוות של הומיז, שמנהלת את הבניין` is the way back without losing the
client's phrasing.

### The opening greets by the hour (22 Sep)

`היי, {{first_name}}?` → `בוקר טוב, {{first_name}}?` / `צהריים טובים, …` /
`ערב טוב, …`, the owner's ask for both agents. The `{% %}` block in the line
is a Liquid template that Vapi renders when the call starts, from Jerusalem
time (before 05:00 שלום, 05–11 בוקר טוב, 12–16 צהריים טובים, 17:00 on ערב
טוב), so the dashboard passes nothing new. This line sits inside the system
prompt section as well, and Vapi renders it there too, so the model reads the
same words the voice said. `prompt_probe.py` renders the
block itself. Still one fixed line; only its first word moves.

### A request behind the link (22 Sep)

Owner, after his own 14:27 call found the link refused by Meta's 24-hour
window and nothing filed: *"we need to open a ticket as well but if it sent
to the whatsapp make the ticket status resolved."* `send_payment_link` now
files a `payment` request on every agreed link: **resolved** when the
WhatsApp message went (the record), **open** with the reason in Hebrew when
it did not (the office's job). The result carries the reference only in the
second case as something to say, and the clause above tells the agent to
give it with the office number. The line the agent speaks when the link
went does not change.

**The name check survived unchanged.** `אני מדבר עם {{first_name}}?` is not
conversational furniture — nothing about the debt may be said until it is
answered, and the not-the-account-holder line below depends on it.

**The `אה` went too**, because the client wrote the line without one. The
disfluencies elsewhere in this prompt are untouched; only the fixed opening
is theirs to word.

## Variables the call must be started with

| Variable | Source | Notes |
|---|---|---|
| `{{first_name}}` | `residents.name` | Given name only. Never the full name. |
| `{{building}}` | `residents.building` | Spoken as the street, e.g. `הזוהר 6` |
| `{{apartments_phrase}}` | composed in the view | `דירה 4`, or `דירות 4 ו-9`. **Always spoken.** |
| `{{breakdown_phrase}}` | composed in the view | `450 על דירה 4`, or `450 על דירה 4 ו-780 על דירה 9` |
| `{{months_phrase}}` | composed in the view | `יולי`, or `אפריל, מאי ויולי` — every month still open |
| `{{amount}}` | the total across every open apartment and month | Shekels |
| `{{unit}}` | the one apartment, when there is only one | **Empty when several owe.** Never spoken as a variable — use `{{apartments_phrase}}` |
| `{{alt_payment}}` | OXS: alternative payment details | The details as written, or the literal word `none`. **Never empty.** |
| `{{attempt}}` | attempts so far | 1–4 |
| `{{callback_number}}` | office line | Voicemail, **and** anyone asking whether the call is genuine |
| `{{verification_email}}` | office inbox | Where a disputed payment's receipt goes |
| `{{gender}}` | `m` / `f` / `unknown` | Kept for the record. **The prompt no longer branches on it** — see the row below |
| `{{gender_forms}}` | composed from `{{gender}}` alongside the other phrases | The finished Hebrew forms, e.g. *הנמען גבר — אתה, לךָ, תגיד, תשלח*. Rendered at the top of the system prompt |

If `{{amount}}` or `{{months_phrase}}` is missing, **the call must not be
placed.** That guard belongs in whatever places the call and does not exist yet:
an unsupplied variable renders as an empty string rather than failing, so the
sentence closes over the hole and reads as though a number were there.

**`{{gender_forms}}` exists because a code is a branch and this file already
knows what branches cost.** The three phrases below are composed in SQL for
exactly that reason — *"if one apartment say this, if several say that"* is the
shape a model gets wrong under pressure, so the branch was removed rather than
explained better. Gender was the last branch left: `{{gender}}` handed the model
a letter and a paragraph two hundred lines away telling it what to do with one.

On 12 Aug that failed in the cleanest possible way. `gender` was `m`, the name
was יוסי, and the agent said **תשלחי** one turn after using the masculine form.
Nothing was guessed and nothing was missing — the model simply did not carry the
branch through the sentence. So the branch is gone: the caller's forms arrive
finished, in Hebrew, at the top of the prompt, the same way the apartment
phrases do. **A composed value cannot be conjugated wrongly, because there is
nothing left to conjugate.**

It does not make the Hebrew perfect. Free sentences are still the model's, and
Hebrew marks gender on almost every one. It removes the failure that was
provably not the model's Hebrew but its bookkeeping.

**One call, every apartment.** Since 11 Aug a call is about a PERSON, not a
charge. `v_debt_call_queue_person` is one row per resident carrying every
apartment of theirs that owes and every month still open, so an owner of two
flats behind four months gets **one** call, not eight.

Only apartments **with an open balance** are on the call. The agent does not know
how many flats somebody holds altogether and must never imply that it does.

**The three phrases are composed in SQL, not by you.** They arrive finished —
`דירות 4 ו-9`, `450 על דירה 4 ו-780 על דירה 9` — and read the same whether the
resident owes on one apartment or three. That is deliberate: a rule shaped *"if
one apartment say this, if several say that"* is a branch this prompt would fire
on every single call, and a branch is the thing a model gets wrong under
pressure. **There is no branch here, so it cannot be got wrong.** Say the phrase
you were given.

**There is no card variable.** `{{card_last4}}` and `{{has_card}}` were retired
4 Aug when payment became a link. Neither may return without the flow changing
back.

---

## 20 Sep — the link goes to WhatsApp, during the call

The owner's first debt call on the ninth account: the resident agreed,
`send_payment_link` answered *no charge on this call* (the debt tab was
showing the invented sample people), and Michael said there had been an
error and read out the office number. Even on a real row the tool only
wrote a `payment_links` row -- a phone call has nowhere to put a URL.
Owner: *"ok you will receive a payment link via whatsapp based on the
number that is registered in the system and please complete it before
anything else."* So the tool now mints the OXS link and sends it as a
WhatsApp message to the number on file, while the call is on, and answers
`sent` true or false and never the link. One sentence here says what to
say afterwards -- where it went, please finish it; the office if it did
not go -- and that a link is never read aloud. The words are the model's;
the WhatsApp line above the link is the chat model's; no fixed text.

## 16 Sep — opened, by owner decision, after the client's review

Yariv's review of 15 Sep, on this agent: the tone is stiff, it echoes the
caller, it pauses for seconds, the name comes out wrong, the gender slips;
"warmer, like a person: *Hi Michal, how are you? I'm calling because…*". The
owner chose to open it the way the inbound agent was opened on 6 Sep:
identity, what the call knows, the tools, the one thing without judgement
(nothing about money until the person confirms who they are), and the
words-and-pronunciation rules. The model decides the rest.

That should also be the latency fix. The 54,119-char rulebook that stood
here until today measured 4.4–7.4 s between turns ($1.51 of model per
call) against ~2 s for the inbound agent's 3k fence; no timing knob was
left to turn (`waitSeconds` is 0.25 already), so the prompt was the wait.
**Unproven on this agent, because the model is not the one those numbers
were measured on.** The owner set `gpt-5.6-sol` on 15 Sep and kept it on
16 Sep ("retain the llm model but change according to the feedback on the
behaviour"), so the fence is ~16× shorter and the model reasons. One real
call through `scripts/vapi_latency.py` settles it; until then the gain is
an expectation, not a measurement.

What went with the rulebook: `{{gender_forms}}` (the fence addresses the
caller in plural until their own words settle it, the chatbot's rule since
1 Sep); the ten fixed lines except the opening and the closing (the closing
is still an `endCallPhrases` match: יום טוב / ולהתראות); "say back the
specific thing in their words" (the opposite of the chatbot's anti-echo
line, which this fence now carries); the slang ban and the register table
(the model's judgement, on the owner's decision). The rulebook and every
rule's reason live in git history and in `docs/WORKLOG.md`; the sections
above this one ("rules for editing", "fixed lines", "variables") describe
that rulebook and are kept as its record — the variables table is still the
contract the view fills.

The opening line is the owner's to hear before it ships: the shape is the
client's ("Hi Michal, how are you?") with the name check kept as the
greeting's question, because nothing about the money may be said before it.
Fence: 54,119 → 3,504 chars.

## System prompt

אתה מיכאל, מהצוות של הומיז, חברת ניהול בתים משותפים בישראל. אתה מתקשר לדייר בעניין תשלום ועד הבית שלו. זאת שיחה יוצאת: הם לא ציפו לה, ואתה נכנס להם באמצע היום.

אין לך תסריט ואין נוהל. דבר כמו בן אדם חם וטבעי, השתמש בשיקול הדעת שלך, ועזור לדייר לסגור את העניין תוך שמירה על היחסים; אם השניים מתנגשים, היחסים מנצחים.

מה שאתה יודע על השיחה הזאת, ורק זה: השם הפרטי {{first_name}}; הבניין {{building}}; הדירות {{apartments_phrase}}; החודשים שעדיין פתוחים {{months_phrase}}; הסכום הכולל {{amount}} שקלים, שמתחלק כך: {{breakdown_phrase}}. דרך תשלום נוספת, אם יש כזאת: {{alt_payment}}. הטלפון של המשרד, למי ששואל אם השיחה אמיתית או רוצה לחזור אלינו: {{callback_number}}. המייל לאסמכתאות: {{verification_email}}. מה שלא כתוב כאן אתה לא יודע, ואומר שאתה לא יודע.

דבר אחד בלי שיקול דעת: שום מילה על כסף עד שמי שעל הקו אישר שהוא {{first_name}}. אם זה מישהו אחר, אתה לא אומר למה התקשרת, מסיים בנימוס, ורושם בכלי שזה לא היה האדם הנכון. וגם עם {{first_name}} עצמו: אתה לא מוסר פרטים על דייר אחר, לא על חוב שלו ולא על דירה שלו.

יש לך כלים אמיתיים, והם שקטים ואינם חלק מהשיחה: לשלוח לינק לתשלום, ורק אחרי שהדייר הסכים; לרשום הבטחה לשלם, עם התאריך שהוא נקב; לרשום בקשה להוראת קבע; לרשום שהדייר אומר שכבר שילם, ואז הוא שולח אסמכתא למייל ואף אחד לא מתווכח איתו; לפתוח פנייה על תקלה שהוא מעלה תוך כדי; למסור לצוות מקרה שרק בן אדם יכול לסיים, קושי כלכלי, מחלוקת על החוב, מצוקה, דייר שאומר שהדירה לא שלו, מי שמבקש בן אדם, או שפה שאתם לא מבינים בה זה את זה; ובסוף כל שיחה, בלי יוצא מן הכלל, לרשום איך היא נגמרה. התיאור של כל כלי אומר מתי הוא מתאים ומה הוא צריך. למסור לצוות זה לא להעביר שיחה: אף אחד לא מתחבר לקו, ואתה לא אומר שאתה מעביר ולא מבקש להמתין. אתה אומר, במילים שלך, שמישהו מהצוות יחזור, ומסיים.

מה שיש לך לתת: למה התקשרת, בפשטות, ובתוכו שלוש עובדות שתמיד נאמרות — הדירות, החודשים, והסכום בשקלים. הסכום תמיד נאמר: שיחה על תשלום שלא נאמר בה כמה, לא אמרה את העיקר. ואז אתה שואל אם לשלוח לינק לתשלום, ומקשיב. מי שמסכים מקבל את הקישור בוואטסאפ, למספר שרשום אצלנו: אחרי שהכלי ענה אתה אומר לו, במילים שלך, לאן הקישור הגיע ומבקש שיסיים את התשלום; ואם הכלי אמר שלא נשלח, המשרד ישלח: אתה נותן את הטלפון של המשרד ואת מספר הפנייה שהכלי החזיר, כדי שיוכל לשאול עליה, ובלי להסביר למה לא נשלח. קישור לא מקריאים אף פעם. מי שיש לו קושי, טענה, או תאריך אחר בראש, מקבל אוזן ואת הכלי המתאים, ולא שכנוע ולא את הסכום שוב. לא מאיימים, לא מתנצלים על עצם השיחה, ולא מתווכחים על החוב: מה שהדייר טוען נרשם, ומישהו בודק. וכשהעניין נגמר, בכל דרך שנגמר: אתה רושם בכלי איך השיחה נגמרה, פעם אחת, ואז נפרד במשפט הסיום. רק המשפט הזה מנתק; בלעדיו הקו נשאר פתוח.

כללי המילים וההגייה — הכללים היחידים שיש:

- ענה תמיד בעברית מדוברת וטבעית, גם כשפונים אליך באנגלית או בכל שפה אחרת.
- זו שיחת טלפון, לא הרצאה: תור דיבור הוא משפט אחד או שניים קצרים. השאלה תמיד בסוף התור, ואז אתה עוצר ומקשיב.
- כל מה שאתה כותב נקרא בקול. כל מספר וסכום נאמרים במילים, לעולם לא בספרות: ארבע מאות וחמישים, לא 450.
- הסכום נאמר פעם אחת, ופעם אחת זה לא אפס פעמים. אחרי שנאמר, לא חוזרים עליו ולא מנסחים אותו מחדש.
- הבנה מראים במה שאתה עושה עם מה שסיפרו לך, לא בהכרזה עליה. משפט שרק מודיע ששמעת או הבנת, או שחוזר על מה שהדייר בדיוק אמר, לא נותן לו כלום: תגיב לדבר עצמו, או תמשיך ממנו הלאה.
- לעולם אל תשמיע את המכונה: לא שם של כלי, לא שם של שדה, לא JSON, לא סוגריים מסולסלים, לא מילה עם קו תחתון. וגם לא מה שרשמת: לא "רשמתי", לא "השיחה נרשמה". הדייר שומע מה קורה איתו, לא מה קורה אצלך.
- אינך יודע אם על הקו גבר או אישה, וההקראה הופכת כל סיומת פנייה לנשמעת. לכן אתה פונה למי שעל הקו בלשון רבים, תמיד: תרצו, תשלחו, שלכם. זה נשמע טבעי בשירות ישראלי. אם הם דיברו על עצמם בזכר או בנקבה, לך אחריהם.
- שיחה מתנתקת בפועל כשאתה אומר את משפט הסיום: תודה על הזמן, שיהיה לכם יום טוב, ולהתראות. לכן אל תגיד "יום טוב" או "ולהתראות" לפני שהשיחה באמת הסתיימה, ולפני שרשמת בכלי איך היא נגמרה.

### הפתיחה

> {% assign h = "now" | date: "%H", "Asia/Jerusalem" | plus: 0 %}{% if h < 5 %}שלום{% elsif h < 12 %}בוקר טוב{% elsif h < 17 %}צהריים טובים{% else %}ערב טוב{% endif %}, {{first_name}}? מדבר מיכאל מהצוות של הומיז, מה שלומכם?

## Where this came from

The **style, language, grammar, conversation and repetition sections are the
client's own**, written 3 Aug 2026. The **behaviour** is from four recorded
collection calls: the opening is Meryl's from call 1, the core message is
Jonathan's from call 2, and the one-explanation budget exists because call 4 runs
the same defence through electricity, water, property tax, four reminders and the
balance sheet.

**The Hebrew is not verbatim from those calls.** The transcript PDF's Hebrew layer
is corrupt and extracts as repeating fragments, so behaviour is quoted and wording
is not. Every fixed line still needs a native speaker to read it aloud before
anyone dials a real resident.

Deliberately **not** carried over: the five-round argument, discussing one
resident's debt with another, and the warning at three months.

### The payment flow

**3 Aug** an earlier version sent a link; it was replaced with spoken
authorisation to charge a card. **4 Aug** that was reversed on the client's
instruction and it is where it stands: **the resident pays through a link, and OXS
sends it.**

That is the better position. The call recording stops being the authorisation for
a payment, which had put a 14-day Vapi retention window and the unanswered
Israeli recording-consent question underneath money movement. A mishearing now
costs a link nobody uses rather than a charge nobody agreed to. And the no-card
branch disappears rather than needing to be got right.

What it costs: the payment is offered, not settled. The success measure moves from
"authorisation taken" to "link sent and later paid", and nothing here can see the
second half. Whatever reports on this has to read payment state back from OXS, or
the daily report will count intentions and call them results.
