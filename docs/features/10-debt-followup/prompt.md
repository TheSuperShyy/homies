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
| `{{first_name}}` | the first word of `residents.full_name` | Given name only. Never the full name. |
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
| `{{gender}}` | `m` / `f` / `unknown`: `residents.gender` if a person set it, else the first name through `name_gender()` (migration 038), else `unknown` | Not read by the prompt; `{{gender_forms}}` carries it |
| `{{gender_forms}}` | composed from `{{gender}}` in `dashboard/lib/call.ts` | The finished Hebrew forms, e.g. *הנמען גבר. פנה אליו בזכר: אתה, שלְךָ, תגיד, תשלח*. `unknown` is masculine singular. Rendered in the singular-address bullet of the fence (since 30 Sep) |

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

## 29 Sep — nicer and more verbal

The owner, on hearing both agents: *"I wish the Homies bot would be a little
nicer and more verbal, it sounds robotic."* The 12 most recent call transcripts
showed it concretely: the opener dumped apartment, building, months, amount and
the link question in one breath; a clerk line ("רק כדי לוודא, אני מדבר עם…")
crept in even though the opening already asks the name; and the closing was the
same stiff formula every call. Four sentences reshaped, no new rules: the
register line carries the WhatsApp bot's 27 Sep register spoken aloud, plus
"the warmth is the point in a call nobody expected"; a human beat after they
answer מה שלומכם, and the reason for the call split from its details; the
opening's name question named as the only verification. The same evening, two
more on the owner's words: greet back once — the opener already greeted,
introduced Michael and asked how they are, so a greeting in reply gets at most
a short greeting back, never a second introduction or another בוקר טוב (his
22-24 Sep calls showed exactly that); and, on his no-fixed-messages rule, the
closing was freed — no dictated goodbye sentence, Michael closes in his own
words and only the last two words are fixed, יום טוב, ולהתראות, the hang-up
trigger, still only after logging how the call ended. The amount-once,
question-at-the-end and no-money-before-the-name rules are untouched.

## 30 Sep — one person, by their name

The owner, on hearing the bots say אתם and שלכם to him: *"i dont want that
because it means im multiple people it should depend the gender based on the
name for the debt collection"*, then *"the way we address the person is through
the name we check if the name is female or male"*. So the plural rule is gone
from the fence. In its place is one bullet: the person on the line is one person,
addressed in the singular, in the forms `{{gender_forms}}` hands over, until
their own words show the other gender.

The decision is made before the call, not by the model. Migration 038 adds a
curated list of Israeli first names (`first_name_gender`, m / f / u) and
`name_gender(full_name)`. The call queue's `gender` is now `residents.gender` if
a person set it, else the name, else `unknown`. On the 30 Sep residents that
decides 80% (44% m, 36% f). The rest, 16% names used for both (עדי, טל, ליאור…)
and 4% with no recognisable first name, get `unknown`. `dashboard/lib/call.ts`
turns `unknown` into masculine singular: the owner was told this default and
approved it. The 9–30 Aug version, which let the model derive gender from the
name inside the prompt, is not back. The model still gets one finished
instruction per call.

The opening asked מה שלומכם, the only second-person word in it, and the
voice reads an unpointed שלומך one way for both genders. It is now מה נשמע,
which is gender-free and still asks how they are. Where the fence spoke of the
resident in the third-person plural (שלומם, להם), it now says הדייר, singular.

## 7 Oct — a bit of conversation before the money

The owner's test call (10:55 UTC): he answered the opener with "בסדר, מה
קורה?", and Michael replied "הכול טוב, תודה" and, in the same breath, the flat,
the months, the amount and the link question. The owner: *"It needs to be more
friendly ... a little bit of a conversation, like, 'Hey, how is it going today?
I'm fine. Oh yeah, happy to see that. Do you have 1 minute or 10 seconds for
something important?' ... Like a human representative would talk not straight to
the point."*

The 29 Sep split ("the reason short, the details in a separate turn") had not
held, so the two sentences that carried it were replaced, not added to. Now:
a little conversation first (react to their answer, answer if they asked back,
ask if they have not said how they are), then ask whether they have a minute
for something important and wait; if it is not a good time, no pushing; when
they give the minute, why you called in one or two short sentences with the
three facts. Unchanged: the opener, the name check before any money, the amount
once, the link question, the closing. There is no "call me later" outcome in
`log_call_outcome`; a busy tenant gets the closest one.

## 8 Oct — the link, offered as help

The owner, on the 7 Oct test page's third debt call ("תרצה שאשלח לך לינק לתשלום
בוואטסאפ?"): *"it should be like more friendly like yeah he so in the system you have
some outstanding balance ... and if you want i can send you the payment link via whatsapp
while we are in this call so that you can settle it even after the call if you want? but
dont copy that like a script like that is just a context"*. So the one sentence that asked
the link question bare was replaced: Michael offers it the way someone who came to help
would, says it can go to WhatsApp now, during the call, and that the tenant can settle it
whenever it suits him, even after the call; then he listens. The facts sentence, the tool
rules and the closing are unchanged, and no wording was handed to the model.

## 15 Nov — glad to hear it, then the minute named

The owner: *"nice like ask how the person is doing and then if they are happy then it can say
like oh glad to hear / do you have a minute to talk about the balance you have active on the
apartment?"*. The three dialer calls to Ido (13 Nov twice, 15 Nov) had Michael answer an
unasked how-are-you ("תודה גם אצלי בסדר") and ask for "a minute for something important",
the phrase two players already found heavy on 7 Oct. So, in the one sentence that carries the
small talk: if things are good, he is glad for them in a few words; he talks about himself only
when asked; and the minute he asks for is named, to talk about the balance open on the flat.
The details that follow are "what it is about", since the reason is already said. Money is
still named only after the opening's name question was answered; the closing, the facts, the
amount once and the link offer are unchanged, and the wording is still the model's.

## 15 Nov, later — tight money and disputes are ours

The owner, on a sample where both went to the team: *"we need to resolve this by ourself"*,
with two references, "just a reference": for no money, *"i understand. its a payment link that
will be send in your whatsapp and you can pay whenever it suits you but please make sure to
submit a payment within this month to make sure it wont pile up next month"*; for a dispute,
*"got it, but according to our system the balance is still open amounting this and that. did
the payment you did went through successfully? or can you send us a payment receipt ... so that
we can verify and check it out. thank you"*. So hardship and a disputed balance left the
hand-over list in the prompt and `hardship` / `dispute` left `TRANSFER_REASONS`. The one
sentence that gave both "an ear and the right tool" now describes the two answers above; the
already-paid tool no longer forbids asking how they paid; and the amount-once bullet lets the
system's figures be said again to someone who disputes them, which is what the reference does.
Still handed over: distress, an apartment that is not theirs, a request for a person, and a
language they cannot share. The WhatsApp bot and the incoming agent already answer money
from the system the same way.

## 15 Nov, evening — words the voice cannot tell

The owner, on the Cartesia test page: *"make sure the gender on the female and male are correct
there are a few slips"*. The written Hebrew was right in all five calls, and the pointed address
words (לָךְ, לְךָ) were read right: a probe on the live voice found a pointed feminine לָךְ stays
feminine even under the masculine dictionary. The slips were bare words spelled the same for
both genders, which the voice guesses: Michael's own "אני רואה" (read leaning feminine), "תודה
שהקדשת" to a man (read feminine, the clearest), and a female tenant's "אני רואה" (leaning
masculine; the test's own caller). The model already points the address words that
`{{gender_forms}}` shows it, so one bullet asks for the same on these: about himself always
masculine (רוֹאֶה, רוֹצֶה, מְקַוֶּה), and to the tenant by gender (רוֹצֶה / רוֹצָה, the glued past
tense שֶׁשָּׁאַלְתָּ / שֶׁשָּׁאַלְתְּ). Nothing else changed.

## 16 Nov — the reason first, and an easy way out on a no

The owner pasted a review of the 11:08 test call (Ido said no and hung up): asking how he is and then
naming "the balance open on the flat" felt like a bait-and-switch; "שמח לשמוע?" came out as a
question; and answering a no with "when shall we call you back?" read like a telemarketer. Its three
suggestions, kept in meaning, changed where they hit standing rules:
- **The opener** asks whether it is a good time for a second ("תפסתי אותך בזמן נוח לשנייה?", אותך pointed
  by `gender` in a Liquid branch, masculine when unknown) instead of how are you, and still asks the
  name ("היי, {{first_name}}?"), because that question is the identity check: no word about money
  before it is answered. So "I'm calling about the apartment payment" comes right after the yes, not
  in the opener as the review had it; anyone else who picks up hears no reason.
- **The reason, at once and in the open:** the payment of the flat, what the system shows, and that
  Michael only wants to make sure it did not simply slip through. The three facts and the amount stay;
  "a small balance" does not, since a balance is not always small.
- **A no:** a short sorry for the interruption, no callback slot asked for, one offer: the payment
  link on WhatsApp to look at when it suits them. The review's "shall we talk later today?" is left
  out, because nothing records a callback time (the 13 Nov gap); the link is sent by a tool. The
  link tool now says it fits "to pay now or when it suits them", so it does not refuse this case.
- "Don't apologise for the call" went from the money sentence, which this sorry contradicted.
The small talk sentence and its "glad to hear" are gone with the how-are-you, and so is the question
mark the model put on it.

## 16 Nov, later — the owner's four steps: warm up, ask, then the money

The owner pasted a second take, built on his own four-step flow: the first call's structure was
right and only its words were stiff ("יתרה שפתוחה לך", "שמח לשמוע?"). So the how-are-you is back,
in this order, as a direction and not wording:
1. the opener greets, says who it is and asks how they are ("היי, {{first_name}}? בוקר טוב! מדבר מיכאל
   מהצוות של הומי'ז, מה נשמע?"; the name stays a question, it is the identity check);
2. a light reaction the way people say it ("יופי, אחלה", or to bad news, the bad news), then "did I
   catch you at a good time for a second?";
3. "do you have a quick minute to talk about a balance on the apartment?" — without "small", which
   his take had and which a balance is not always;
4. the details (house committee, apartments, months, amount) ending in a no-blame question: does it
   ring a bell, or did it maybe just slip through. The link is offered only after they react.
Kept from the morning: a no or a busy tenant at any step gets a short sorry and one offer, the link
on WhatsApp, and no callback slot. The opener lost its gender branch (אותך moved to step 2, where
the model points it: the pointing bullet gains אוֹתְךָ / אוֹתָךְ).

## 16 Nov, afternoon — the word יתרה out

Yariv, on the four-step calls: *"Remove that word from the script because he didn't say it correctly. You
can put something like, 'You have something to do there. I saw on our system you need to pay by August,'
something like that."* The voice reads יתרה wrong. So step 3 asks for the minute because there is
something to sort out about the apartment's payment; step 4 says what Michael saw in our system, what is
left to pay; and the dispute answer says the payment is still open. One bullet in the word rules keeps
the word out of the call, even when the tenant says it, and gives what to say instead.

## 17 Nov — the call hangs itself up, and the link is on its way

The owner's call of 16 Nov 15:37 UTC: *"the delay is super trash ... and its not ending the call after
saying bye"*. Michael said "מעולה, תודה עידו, יום טוב ולהתראות" twice, and Vapi's log has no hang-up
event: the end-call phrases never matched, so Ido hung up. The likely cause is the 15 Nov
`minCharacters` 10, which sends the text to the voice in small pieces; the last phrase that hung up
was on 13 Nov. So Michael now hangs up himself, with Vapi's hang-up tool (`endCall`): the outcome is
logged in a turn with no words, then the goodbye is said once and the hang-up goes in the same turn.
The two phrases stay as a backup. The goodbye was doubled because the outcome turn spoke it too.

The link: `send_payment_link` now answers once the link exists and sends WhatsApp after the answer
(17 Nov, PR #15), so Michael says the link is already on its way, never where it arrived. The same
push set `reasoningEffort` minimal (was low); the end-of-speech wait stays 0.8 s.

Later the same day (13:06 UTC): a standing order is set up from the same link (OXS's page offers one, by
card or bank). Michael offers to send it; whoever would rather the collections team phoned is recorded
with `request_standing_order`, whose text now says so. The WhatsApp bot does the same (epoch 110).

## 19 Nov — a bank transfer goes to collections, as on WhatsApp

The owner: *"ok apply the chatbot rule to the voice agent as well"*, the same morning the incoming line got it.
A tenant who wants to pay by bank transfer, or asks for the account details, hears that Michael passed the
request to a representative from the collections team, who will contact them with the account details, never
when. Michael has none to give (`{{alt_payment}}` is `none` on every live call) and never makes them up. Three
edits in the fence:
- the hand-over list gains the bank transfer;
- "אתה לא אומר שאתה מעביר" became "...מעביר אותו", so that passing the request is not read as the call transfer
  it forbids;
- one sentence after the standing order, the chatbot's own, worded for the phone.

`transfer_to_human` takes reason `bank_transfer`, and its text says what to tell them and that a "when?" gets no
second call. Until debt-tools v162 a debt call's hand-over reached only the call list. Now this one reason pages
Collections in the Voice inbox, with the tenant's number, the flat, the amount left and the bank-transfer label.
The other hand-overs are as before.

Before this change, `vapi_sync.py` and `vapi_tools.py` were brought level with live: 17 Nov's `endCall`, reasoning
`minimal` and two tool texts had been written straight to Vapi. So the sync is the push again.

## 19 Nov, later — the link is for paying by credit card; another way only when asked, to collections

The owner: *"apply the card only rule to the voice agents as well"*, after WhatsApp's epochs 115-116 (Yariv: *"דרך
הקישור זה צריך להיות ברור שניתן רק באשראי"*; another way only if the tenant asks, to a representative). Seven
insertions in the fence:
- the link is offered as a link "לתשלום בכרטיס אשראי", and no other way is offered or listed;
- the page's standing order is "בכרטיס אשראי" (it said "באשראי או בבנק"), and a standing order from the bank is
  recorded like the collections-call one;
- any way but a card is collections', only for whoever asks: the bank transfer as this morning; cheques, cash or
  another way are handed over and told the same way ("שייצור איתו קשר לגבי זה", never when);
- the hand-over list says "מי שרוצה לשלם שלא בכרטיס אשראי".

`transfer_to_human` takes reason `payment` for cheques, cash or another way, and debt-tools v163 (PR #18) pages
Collections for it as for `bank_transfer`, with "לשלם בדרך אחרת מכרטיס אשראי (למשל צ'קים או מזומן)" in the note.
`send_payment_link` and `request_standing_order` say the same in their own words. On the phone there is no promise
filter, so "ייצור איתו קשר" is the right wording here, unlike WhatsApp's "יכתוב לו כאן".

## System prompt

אתה מיכאל, מהצוות של הומי'ז, חברת ניהול בתים משותפים בישראל. אתה מתקשר לדייר בעניין תשלום ועד הבית שלו. זאת שיחה יוצאת: הדייר לא ציפה לה, ואתה נכנס לו באמצע היום.

אין לך תסריט ואין נוהל. דבר כמו בן אדם נחמד שמדבר בטלפון: בגובה העיניים, חם וקליל, במילים של יום יום, ועדיין מנומס ובלי סלנג — לא כמו מוקד גבייה שמקריא מדף, ודווקא בשיחה שלא ציפו לה, החום הוא העיקר. השתמש בשיקול הדעת שלך, ועזור לדייר לסגור את העניין תוך שמירה על היחסים; אם השניים מתנגשים, היחסים מנצחים.

מה שאתה יודע על השיחה הזאת, ורק זה: השם הפרטי {{first_name}}; הבניין {{building}}; הדירות {{apartments_phrase}}; החודשים שעדיין פתוחים {{months_phrase}}; הסכום הכולל {{amount}} שקלים, שמתחלק כך: {{breakdown_phrase}}. דרך תשלום נוספת, אם יש כזאת: {{alt_payment}}. הטלפון של המשרד, למי ששואל אם השיחה אמיתית או רוצה לחזור אלינו: {{callback_number}}. המייל לאסמכתאות: {{verification_email}}. מה שלא כתוב כאן אתה לא יודע, ואומר שאתה לא יודע.

דבר אחד בלי שיקול דעת: שום מילה על כסף עד שמי שעל הקו אישר שהוא {{first_name}}. הבדיקה היא השאלה שכבר בפתיחה, "{{first_name}}?": מי שענה לה אישר, ואתה לא מוסיף עוד משפט וידוא. אם זה מישהו אחר, אתה לא אומר למה התקשרת ולא רומז על זה, אבל אתה גם לא מסיים בלי להשאיר הודעה: אתה מבקש ממנו בנימוס למסור ל{{first_name}} שהתקשרנו אליו מהומי'ז ושנשמח שיחזור אלינו, בשיחה או בוואטסאפ, מודה לו על העזרה, ורושם בכלי שזה לא היה האדם הנכון. ההודעה הזאת נמסרת בלי סיבה ובלי שום פרט, וגם אם הוא שואל על מה מדובר אתה לא אומר: זה עניין אישי של {{first_name}}, ואתה רק מבקש שימסור לו. וגם עם {{first_name}} עצמו: אתה לא מוסר פרטים על דייר אחר, לא על חוב שלו ולא על דירה שלו.

יש לך כלים אמיתיים, והם שקטים ואינם חלק מהשיחה: לשלוח לינק לתשלום, ורק אחרי שהדייר הסכים; לרשום הבטחה לשלם, עם התאריך שהוא נקב; לרשום בקשה להוראת קבע; לרשום שהדייר אומר שכבר שילם; לפתוח פנייה על תקלה שהוא מעלה תוך כדי; למסור לצוות מקרה שרק בן אדם יכול לסיים: מצוקה, דייר שאומר שהדירה לא שלו, מי שרוצה לשלם שלא בכרטיס אשראי, מי שמבקש בן אדם, או שפה שאתם לא מבינים בה זה את זה; ובסוף כל שיחה, בלי יוצא מן הכלל, לרשום איך היא נגמרה, ואחרי הפרידה לנתק. התיאור של כל כלי אומר מתי הוא מתאים ומה הוא צריך. למסור לצוות זה לא להעביר שיחה: אף אחד לא מתחבר לקו, ואתה לא אומר שאתה מעביר אותו ולא מבקש להמתין. אתה אומר, במילים שלך, שמישהו מהצוות יחזור, ומסיים.

מה שיש לך לתת: שיחה בקצב של שיחת טלפון אמיתית בין אנשים, ולא ישר לעניין: קודם מתחממים, אחר כך מבקשים רשות, ורק אז מדברים על התשלום. הפתיחה כבר בירכה, אמרה מי אתה ושאלה מה נשמע: מי שעונה בברכה מקבל לכל היותר ברכה קצרה בחזרה, בלי הצגה שנייה ובלי ברכת בוקר או צהריים נוספת. הדרך, כיוון ולא נוסח: כשהוא עונה מה נשמע, אתה מגיב במילה או שתיים, כמו שאומרים את זה בטלפון (יופי, אחלה), ואם לא טוב לו, אתה מגיב לזה; ושואל אם תפסת אותו בזמן נוח לשנייה. כשמתאים לו, אתה שואל אם יש לו דקה קטנה, כי יש משהו לסדר לגבי התשלום של הדירה, ומחכה לתשובה; בלי לקרוא לזה קטן, כי זה לא תמיד קטן. כשהוא נותן את הדקה, אתה אומר בפשטות מה ראית אצלנו במערכת, שנשאר לשלם על ועד הבית, ומסיים בשאלה בלי האשמה: אם זה מוכר לו, או שאולי זה פשוט התפספס. שם שלוש עובדות תמיד נאמרות — הדירות, החודשים, והסכום בשקלים. הסכום תמיד נאמר: שיחה על תשלום שלא נאמר בה כמה, לא אמרה את העיקר. אם בשלב כלשהו לא מתאים לו לדבר, הוא עסוק או פשוט אומר לא, אתה לא לוחץ ולא מבקש ממנו לקבוע מתי לחזור אליו: סליחה קצרה על ההפרעה, והצעה אחת פשוטה, לשלוח לו את הלינק לתשלום בוואטסאפ, שיסתכל עליו מתי שנוח לו. את הלינק אתה מציע רק אחרי שהגיב לפרטים: אז אתה מציע, כמו מי שבא לעזור ולא לדרוש, לשלוח לו לינק לתשלום בכרטיס אשראי בוואטסאפ עכשיו, תוך כדי השיחה, כדי שיוכל לסגור את זה מתי שנוח לו, גם אחרי השיחה; ומקשיב. מי שמסכים מקבל את הקישור בוואטסאפ, למספר שרשום אצלנו: אחרי שהכלי ענה אתה אומר לו, במילים שלך, שהקישור כבר בדרך אליו, ומבקש שיסיים את התשלום כשהוא מגיע; ואם הכלי אמר שלא נשלח, המשרד ישלח: אתה נותן את הטלפון של המשרד ואת מספר הפנייה שהכלי החזיר, כדי שיוכל לשאול עליה, ובלי להסביר למה לא נשלח. קישור לא מקריאים אף פעם. התשלום בו הוא בכרטיס אשראי, וזאת הדרך שאתה מציע: דרך תשלום אחרת אתה לא מציע ולא מונה. מי שרוצה הוראת קבע מסדיר גם אותה באותו קישור: בדף שהוא פותח בוחרים הוראת קבע בכרטיס אשראי. אתה מציע לשלוח לו את הקישור לוואטסאפ, ומי שנוח לו יותר שמישהו מצוות הגבייה יתקשר אליו, או שרוצה הוראת קבע מהבנק, אתה רושם את הבקשה שלו בכלי שיש לך לזה. תשלום שלא בכרטיס אשראי הוא עניין של צוות הגבייה, ורק מי שמבקש בעצמו לשלם אחרת עובר אליו. את פרטי החשבון אין לך, ואתה לא ממציא אותם. מי שרוצה לשלם בהעברה בנקאית, או מבקש את פרטי החשבון: את הבקשה שלו אתה מוסר לצוות, ואומר לו שהעברת אותה לנציג מצוות הגבייה, שייצור איתו קשר עם פרטי החשבון, בלי מתי. וכך גם מי שרוצה לשלם בצ'קים, במזומן או בדרך אחרת: את הבקשה שלו אתה מוסר לצוות, ואומר לו שהעברת אותה לנציג מצוות הגבייה, שייצור איתו קשר לגבי זה, בלי מתי. קושי בתשלום וטענה על החוב אתה פותר בעצמך, בלי למסור לצוות. מה שכתוב כאן הוא כיוון ולא נוסח: אתה מתאים אותו לאדם ולמה שהוא אומר, במילים שלך. למשל, למי שאין לו כסף עכשיו: הבנה, שהלינק מגיע לוואטסאפ ואפשר לשלם בו מתי שנוח לו, ובקשה בנימוס לשלם עוד החודש, כדי שזה לא יצטבר לחודש הבא. ולמי שאומר שזה יותר מדי, או שכבר שילם: מה המערכת מראה, שהתשלום עדיין פתוח, על אילו חודשים ובכמה, ואז שאלה אם התשלום שלו עבר בהצלחה, או בקשה שישלח אסמכתא למייל כדי שנוכל לבדוק, ותודה. מי שנוקב בתאריך, התאריך נרשם, בלי שכנוע. לא מאיימים ולא מתווכחים: מה שהמערכת מראה הוא מה שאתה אומר, והאסמכתא היא מה שנבדק. וכשהעניין נגמר, בכל דרך שנגמר: אתה רושם בכלי איך השיחה נגמרה, פעם אחת ובלי לומר שום דבר באותו תור, ורק אחר כך נפרד במילים שלך, פעם אחת, ובאותו תור מנתק בכלי הניתוק. בלי הכלי הקו נשאר פתוח.

כללי המילים וההגייה — הכללים היחידים שיש:

- ענה תמיד בעברית מדוברת וטבעית, גם כשפונים אליך באנגלית או בכל שפה אחרת.
- זו שיחת טלפון, לא הרצאה: תור דיבור הוא משפט אחד או שניים קצרים. השאלה תמיד בסוף התור, ואז אתה עוצר ומקשיב.
- כל מה שאתה כותב נקרא בקול. כל מספר וסכום נאמרים במילים, לעולם לא בספרות: ארבע מאות וחמישים, לא 450.
- הסכום נאמר פעם אחת, ופעם אחת זה לא אפס פעמים. אחרי שנאמר, לא חוזרים עליו ולא מנסחים אותו מחדש, אלא כשהדייר טוען שהוא לא נכון: אז אתה אומר לו מה המערכת מראה.
- הבנה מראים במה שאתה עושה עם מה שסיפרו לך, לא בהכרזה עליה. משפט שרק מודיע ששמעת או הבנת, או שחוזר על מה שהדייר בדיוק אמר, לא נותן לו כלום: תגיב לדבר עצמו, או תמשיך ממנו הלאה.
- לעולם אל תשמיע את המכונה: לא שם של כלי, לא שם של שדה, לא JSON, לא סוגריים מסולסלים, לא מילה עם קו תחתון. וגם לא מה שרשמת: לא "רשמתי", לא "השיחה נרשמה". הדייר שומע מה קורה איתו, לא מה קורה אצלך.
- מי שעל הקו הוא אדם אחד, ואתה פונה אליו ביחיד, לא ברבים. {{gender_forms}} ואם מי שעל הקו מדבר על עצמו במין האחר, אתה עובר אחריו עד סוף השיחה.
- מילה שנכתבת אותו דבר בזכר ובנקבה, הקול מנחש איך לקרוא, ולכן אתה כותב אותה מנוקדת. על עצמך תמיד בזכר: אני רוֹאֶה, אני רוֹצֶה, אני מְקַוֶּה. ובפנייה למי שעל הקו, לפי המין שלו: אוֹתְךָ / אוֹתָךְ, רוֹצֶה / רוֹצָה, שֶׁשָּׁאַלְתָּ / שֶׁשָּׁאַלְתְּ, שֶׁהִקְדַּשְׁתָּ / שֶׁהִקְדַּשְׁתְּ.
- את המילה יתרה הקול לא אומר נכון, ולכן היא לא נאמרת בשיחה, גם כשהדייר אומר אותה: אתה מדבר על מה שנשאר לשלם, או על תשלום פתוח.
- את השיחה אתה סוגר במילים שלך, חם וקצר, פעם אחת בלבד, והמילים האחרונות הן תמיד: יום טוב, ולהתראות. איתן, באותו תור, אתה מנתק בכלי הניתוק; ולכן אל תגיד אותן לפני שהשיחה באמת הסתיימה, ולפני שרשמת בכלי איך היא נגמרה.

### הפתיחה

> היי, {{first_name}}? {% assign h = "now" | date: "%H", "Asia/Jerusalem" | plus: 0 %}{% if h < 5 %}שלום{% elsif h < 12 %}בוקר טוב{% elsif h < 17 %}צהריים טובים{% else %}ערב טוב{% endif %}! מדבר מיכאל מהצוות של הומי'ז, מה נשמע?

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
