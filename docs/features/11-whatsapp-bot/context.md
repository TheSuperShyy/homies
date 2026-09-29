# 11 — WhatsApp bot — context

Why it is like this, and what was ruled out.

## The channel was a real choice, and it was made on 7 Aug

Three ways to put a bot on WhatsApp were on the table.

**Meta Cloud API test number — chosen.** Official, free, available the moment a
Meta developer app exists, and capped at five recipient numbers you register by
hand. Five is plenty to build and demo with. The important property is that
nothing gets rebuilt when Homies' real number arrives: the migration is a
phone-number id and a token, both of which are already read from `.env`.

**GreenAPI — rejected, and worth recording why.** Another client on the same n8n
instance already runs WhatsApp through it (`Inventory - 20 Availability Bot`), so
it is proven-here and would have been the fastest route to a working demo. It
drives WhatsApp Web unofficially. That breaks WhatsApp's business terms and the
number can be banned. For a company with 200 buildings whose residents' only
contact channel this would become, a foundation that can vanish overnight is the
wrong foundation. Fine to prove a bot; wrong to build a business on.

**Twilio sandbox — rejected.** `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` are
in `.env` but **empty** — placeholders, not an account. So it costs a new signup,
adds a per-message BSP markup, and still requires the identical Meta business
verification to reach production. It buys nothing the test number does not.

**Business verification is the gate on the production number, not on building.**
That distinction is what let this start today. Verification is 1–2 weeks and
depends on Homies' legal documents, which we do not have.

## Chatwoot is later, deliberately

Chatwoot is the staff shared inbox. It serves human handover and the team-comms
bot — different concerns from the resident-facing brain, and a different build.

It is also Rails plus Postgres plus Redis plus Sidekiq. When this was written the
only VPS we had was `srv1135333`, **shared production carrying four other
clients' workflows** (MOR, Shirly Inventory, CLIX, Hadas), and installing a
multi-gigabyte service beside them to unblock a demo was a bad trade.

*Revised 8 Aug:* Homies has its own n8n box, `srv1879140`, so the "beside four
other clients" objection is gone. The argument that survives is the smaller one —
Chatwoot is a Rails stack to run and maintain for a handover inbox nobody has
asked for yet, and the rewire cost of adding it later is still one field in the
Meta app config.

The rewire cost of adding it later is one field in the Meta app config. That is
the whole reason this ordering is cheap.

## Why the chat pretends to be a call

The Brain posts a Vapi-shaped envelope to the existing tool webhook. It looks
like a hack and it is a deliberate one.

The alternative is a second workflow with its own writer, its own secret and its
own row shape — precisely what `scripts/n8n_deploy.py` refuses to do for the
inbound agent, and for the same reason: two copies of a writer drift, and the
drift is invisible until a row comes out wrong. One writer, one shape, one place
to fix a bug.

The cost is that a reader of the tool webhook has to know that some of its
traffic is not a phone call. The `wa:` prefix on the session id is what makes
that legible without reading this file.

## Answer Meta first, work afterwards

Meta retries a webhook that does not return 200 quickly, and a retry is a second
copy of the same message. Left alone, that is a resident receiving two replies to
one question.

This is the same lesson the tool webhook already learned from Apps Script: the
caller never waits for storage. Here the caller is Meta and the storage is an
entire model round-trip, so the argument is stronger, not weaker.

Duplicate suppression is by Meta's message `id` rather than by content, because
content is not unique — a resident who sends "כן" twice means it twice.

## Conversation state is in n8n static data, and that is a known compromise

It is simple, it needs no new service, and it survives workflow executions.

What it is not: durable across an n8n restore, bounded in size by anything but
our own cap, or visible to anything outside n8n. It is stored with the workflow
on a **shared production instance**, so it must never hold anything a leak would
matter for. Right now it holds ten fictional residents' messages.

The 24-hour expiry is not a guess. It is WhatsApp's free-form messaging window: a
session older than that is one the bot could not legally have replied to without
an approved template, so keeping it buys nothing.

**This has to move before real resident data touches it.** Supabase is the
intended home and six migrations are already written; there is still no project
behind them.

## Thinking stays on — the counterintuitive one

Every instinct says turn thinking off for a chat bot. Latency is user-visible,
replies are short, and thinking is on by default on Claude Opus 5.

It is still wrong here. With thinking disabled, this model occasionally writes a
tool call into its visible text rather than emitting a structured tool call. The
turn returns normally, the reply reads fine, and the tool **never runs**. There is
no error and no failed call to catch — a resident is told their request is logged
and no row exists.

For an agent whose entire purpose is calling `open_request`, a silent-loss failure
mode is disqualifying in a way that a few hundred milliseconds is not.
`effort: "low"` recovers most of the latency without it.

Second-order reason: `max_tokens` bounds thinking and reply together on this
model. A `max_tokens` sized for a WhatsApp-length answer will truncate a reply
that thought first. The value in the script is sized for both.

## What is deliberately not here

**The payment flows.** Anything that *moves* money still goes to a person.

Reading a balance no longer does, and the identity method it was waiting on
(PRD §13 #1) was settled on 13 Aug: a full name and a phone number, both typed
by the resident, both landing on the same `residents` row, checked inside the
Edge Function rather than asked for by the prompt. That answers reading, not
paying — taking a payment needs more than knowing who is asking, and a payment
flow behind an identity check built for reading is worse than no payment flow.

**Media and voice notes.** A voice note is genuinely interesting — it is the
voice agent's transcriber reachable from a text channel. It is also a second
transcription pipeline, and the Hebrew transcriber question is still open from
the latency work on 7 Aug. Not while that is unsettled.

**Outbound and templates.** Anything outside the 24-hour window needs a
Meta-approved message template, which needs the verified business account we do
not have. The payment link (17 Sep) is sent INSIDE that window, as a reply to
the resident who just asked, so it needs no template; an unprompted link to a
debtor who has not written — what the outbound flow would want — still lands
here, gated on the same clock as the production number.

## Deployed 8 Aug, and what is still switched off

Workflow `fDVRNLvsALcOe3ld`, `Homies — WhatsApp bot`, active on the shared n8n
instance. Callback URL `…/webhook/homies-whatsapp`. Receiving, sorting,
deduplicating and thinking all work against real Meta payload shapes; only the
send leg is dark, waiting on `WHATSAPP_PHONE_NUMBER_ID` and
`WHATSAPP_ACCESS_TOKEN`.

**Deploying before those two exist is deliberate, not a shortcut.** Meta will
not save a callback URL until it has GET-verified it, and it cannot verify a URL
that is not live — so the workflow has to exist before the credentials that let
it reply can be obtained. The gate in `n8n_whatsapp.py` originally demanded all
three up front, which blocked the step that has to come first. It now hard-fails
on the verify token and the model key and warns on the other two.

**The bug this caught, recorded because the shape recurs.** `multipleMethods`
gives the webhook node one output per method — GET on 0, POST on 1 — and only
output 0 was connected. Verification passes, the Meta dashboard shows a healthy
webhook, and every real message ends its execution as `success` after one node.
No error and no reply. **The test that catches it is posting a message envelope
at the live URL; the test that does not is the verification handshake, which is
the one everybody runs.**

## The incumbent bot, seen live on 10 Sep

The owner reached Homies' real WhatsApp number from his own handset and found
the bot PRD item 3 calls "ManageChat" — a ManyChat router — still answering
on it. Recorded here verbatim because it is what every Homies resident has
been trained on, and because that number is already on Meta's Cloud API
through it (Meta delivers to one callback URL, so taking the number over is
a hard switch with no parallel run, and needs whoever holds the "office
homies" Meta account).

Greeting: `היי! איזה כיף שפניתם אלינו! לפניכם נתב שיחות 🔀, איך נוכל לעזור?`
with one button, `לחצו כאן להמשך`, opening six rows:
תשלום ועד בית/גביה 💰 · הנהלת חשבונות 📋 · קריאת שירות 🙋 · הצעת מחיר 🤝 ·
אב הבית 👷 · מעבר לנציג 🔀. A tap echoes the choice and runs a form:
*על מנת שנוכל לפתוח את הקריאה כראוי - ענו בבקשה על השאלות הבאות* →
*מהו שמכם המלא?* A menu tree, not a conversation, and the thing the PRD's
"must not feel robotic" line is about.

What it changed here: the prompt's facts list gained אב הבית and הצעת מחיר
(the two categories we had nothing for) and the office's own matters. What
it did not change: the menu stays at three buttons. **Chatwoot builds the
WhatsApp payload, not us** (`base_service.rb:99` on the VPS): three items
or fewer are reply buttons, four or more become a list whose wrapper button
is the account-locale string — account 2 is `en`, so it reads "Choose an
item"; Chatwoot's `he.yml` has `בחר פריט`. Descriptions are dropped on both
shapes, and the inbound tap carries only the row's **title**, which is why
the titles are the routing table (`TAP_KIND` in the live `Sort`). Whether to
flip the account to Hebrew for a seven-row list is open with the owner.

## 29 Sep — UChat evaluated: a lateral move, not a step up

The owner asked what UChat is, what it costs, and how much work it would take.
UChat (uchat.au) is a no-code chatbot builder, ManyChat's direct rival: flows
drawn as boxes, 13 channels, an "External Request" step, inbound webhooks, an
API (send-text/send-node added later per their feedback board), an AI agent
on your own key, and a live-chat inbox where a staff reply pauses the bot for
**30 minutes**. *Corrected 29 Sep, from their API spec
(`default-api-docs/api-docs.json`):* the agent's provider list is openai,
deepseek, xai, claude, **gemini**, groq and ainvented, so **Gemini is
supported** even though their training page names only three; the first
version of this section said it was not. The spec also shows what the API
cannot do: there is no endpoint that creates an AI agent or a flow (list,
info, provider/model and MCP attachment only), so both are built in their UI.
`pause-bot` takes any number of minutes. WhatsApp connects straight to Meta's Cloud API through the
business's own Meta app; UChat adds no per-message fee. Nothing in their docs
or reviews mentions Hebrew or right-to-left.

**Price:** Business is $15/mo billed yearly (~$29 monthly) for 1,000 contacts
and 5 seats; +$5 per 1,000 contacts to 5,000, +$20 per 5,000 after; seats
$5 each on Business. Contacts are everyone the bot has ever talked to, so
Homies (~7,400 residents) lands near **$80-95/month with ~10 seats, or
$125-140 with all ~19 staff seated**, plus the model bill and Meta's fees,
which exist today too.

**The work, measured against what exists:** the bot is a ~50-node n8n
workflow kept by 25 patch scripts, a 19.6k-character prompt tuned on Gemini,
8 tools on the `debt-tools` Edge Function (plain HTTP, would move unchanged),
and a regression gate that runs the exact live n8n code — which cannot run
inside UChat. Chatwoot is already the inbox (bot handoff, team paging,
handover ladder, labels, four department teams), so UChat would *replace* it.
- **Everything into UChat: ~3-5 weeks** (first estimated at 4-6 when Gemini
  seemed unavailable). The prompt ports to the same model, but UChat's agent
  wrapper still changes behaviour (it summarises after 10 messages and gets
  none of the per-turn facts n8n injects: time of day, mid-conversation,
  greeting), so some re-tuning remains; the guards are rebuilt in flows where
  possible (the reply checks can't be — UChat's AI step gives no
  check-and-retry before sending); the gate and the history are lost.
- **UChat as the inbox only, n8n stays the brain: ~1.5-2.5 weeks** of
  rewiring every Chatwoot-shaped node, for roughly what Chatwoot gives today.
  Its send API and forward-every-message behaviour are unverified.

**Recommendation: don't move.** The PRD's inbox pieces are already in
Chatwoot; what remains (filling the teams, routing) is the same work on either
platform. If Homies insists, the inbox-only route, and only after UChat's
free 14-day trial proves, on a separate test number: Hebrew in the inbox, the
send-text API, a catch-all forward, a pause that lasts the whole conversation,
group routing, and the billing currency.

**The trial, started 29 Sep.** The owner opened the account (workspace
"clix"), made a Manage-Flow API key (in `.env` as `Uchat_api_key`; read-only
calls work: `/me`, `/flow/ai-agents`, empty bot) and chose a **look-and-feel
copy first: Gemini, no tools**, so the copy reaches no data at all. Its
prompt is the live one byte for byte (sha 8afa16824480) plus a short demo
note: no tools, say plainly the action is unavailable in the demo, never
invent numbers, amounts, dates or links — because a tool-less bot invents
deeds, the exact 27 Sep bug. The paste-ready file is the gitignored
`local/uchat/agent-prompt.txt`. The agent and the menu flow are built in
UChat's UI by the owner; model and limits are then set through the API.
Channel: the web chat widget only; no WhatsApp number is connected.

## 16 Sep — the client's review: no numbers, no advice; a private fault is theirs

Yariv's review asked for three guardrails and the owner chose the sharp
form of each: no national numbers and no safety instructions at all (an
emergency is the ticket and the team, at once, and the bot says that even
when asked directly what to do now); a fault in the resident's own flat is
theirs, no ticket, said kindly; only managed buildings (chat has refused
since 23 Aug; voice joins it). The facts row with the four numbers left the
prompt, the `fault_location` gloss carries the private/common line, and
`notify_team` fires "the moment you hear it". Learned on the way: a
prohibition on instructions does not cover the direct question; naming the
question fixed it 3/3 offline. Epoch 27. Not pushed at the time of
writing.

## 15 Sep — wanting to pay is a ticket too

The owner asked for a ticket whenever a resident wants to pay, beside the
team note. The decision that mattered was the shape: ticket + note, for
wanting to pay only, not for disputes or documents. The type is ours
(`payment`, migration 031, label תשלום) and the dashboard shows the slug as
it shows every slug. The bot learns it from one sentence in the durability
paragraph and from the tool texts; the surprise was that `get_balance`'s
identity rule (name + phone) was read as the ticket's until `open_request`
said what a payment ticket needs. The live tool descriptions have their
own patcher now, `n8n_whatsapp_payment.py`, because nothing else could
ship them. Epoch 25.

## 14 Sep, evening — a word for the person first; one emoji sometimes

The owner found the menu tap answered with a bare `מה קרה?` and asked for
concern first, in the bot's own words, plus a situational emoji. Why it
was bare: the model wrote it under a prompt whose every register rule was
a cap. The decision was where to put a floor, and the answer was the block
that owns the caps, so nothing outvotes it. The price paid on the way:
pass one's floor made the model answer with words instead of the tool on a
typed complaint, inventing a reference twice; "the tool first, the words
after" is part of the floor now, not a separate rule. The emoji is placed
by moment (sorted, goodbye, a resident who writes that way), which in
practice means goodbyes. Epoch 23. See `prompt.md` and the WORKLOG.

## 14 Sep — the bot is the whole desk, and "I've let the team know" is true

The owner's refinement of the day before: cut the office's workload; the bot
is 100% of customer support; past its threshold it must not dead-end a
resident on a phone number but say it has let the right team know — with a
Chatwoot mention behind it ("like regular"). `notify_team` replaced
`transfer_to_human` (feature 16's wire, new words), the threshold cases are
noted for a team with matter-shaped reasons, office details only if asked,
emergencies never end on the office line. Epoch 20 → 22 in one day: the
second bump because the model wrote "I've told the team" without the tool
and promised call-backs, and the prompt had to say that saying is not doing.
The decline ("I don't want a ticket, just so you know") is respected since
the same edit — it was argued with on 13 Sep and 14 Sep before it.

## 13 Sep — the bot is the rep

Owner's direction: fewer office–tenant interactions; the bot handles what it
can, opens a ticket where it can, and for office matters (payment
arrangements, disputed bills, moving in or out, contracts, the committee)
says the office handles it and gives its details. Nobody is paged, not even
for an emergency — asked directly, he chose office details for those too,
with the after-hours cost in front of him. A real person replying still
silences the bot. The third button became **משהו אחר**; the paging machinery
came out (`scripts/n8n_whatsapp_nopage.py`, feature 16). Epoch 19 → 20.

## Still open

- **The model key exists and is out of credit.** `.env` had Vapi, Cartesia, n8n,
  OXS, Supabase and Telnyx keys and **no LLM key of any kind** until 8 Aug — the
  voice agents get their model inside Vapi, so nothing until then needed one.
  `OPENROUTER_API_KEY` now authenticates and a full request has been served, but
  the balance affords about 1,600 output tokens. OpenRouter pre-authorises
  `max_tokens` against the balance, so a `MAX_TOKENS` of 4096 returns **402 on
  every request** — a valid key and a bot that never calls a tool. The Brain
  catches it and hands over to a person, which makes the failure quiet rather
  than visible. Credits are the fix; shrinking `max_tokens` clears the 402 by
  reintroducing the truncation this value exists to prevent.
- **~~`OXS_KEY_REQUESTS` is empty~~ — filled 8 Aug, and then made irrelevant.**
  OXS is read-only by client rule from that same day: nothing this system builds
  writes to it, and *creating* a service request counts as writing. So this bot
  never opens a ticket in OXS regardless of what the key permits, and the key
  should be re-issued as Read-Only so the capability does not exist. Tickets live
  in Supabase and reach staff from there.
- **Our own two documents disagreed** about the chatbot brain: the build-stack
  checklist said Claude API, the credentials checklist said OpenRouter. Settled
  on **OpenRouter**, which is what `.env.example` has said since it was written
  and what the user confirmed on 7 Aug. The cost is a hop and a different
  request shape; the benefit is that swapping models for a Hebrew bake-off is a
  one-line change, which — given how much of this project has turned on Hebrew
  model behaviour — is worth more here than it would be elsewhere.
- **The Hebrew has not been reviewed by a native speaker.** Same standing gap as
  the voice prompts.
