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

**The payment and debt flows.** They need identity verification, and the
verification method is still open with Homies (PRD §13 #1). A payment flow behind
an undefined identity check is worse than no payment flow.

**Media and voice notes.** A voice note is genuinely interesting — it is the
voice agent's transcriber reachable from a text channel. It is also a second
transcription pipeline, and the Hebrew transcriber question is still open from
the latency work on 7 Aug. Not while that is unsettled.

**Outbound and templates.** Anything outside the 24-hour window needs a
Meta-approved message template, which needs the verified business account we do
not have. Sending the debt payment link over WhatsApp — which the PRD assumes —
lands here, and it is gated on the same clock as the production number.

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
