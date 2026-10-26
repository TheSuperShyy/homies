# 19 — WhatsApp sandbox: why it is built this way

## Why a sandbox at all

Yariv's accepted alignment document (26 Oct) asks for two changes to the WhatsApp bot:
- no representative button, so the bot is the representative;
- no asking again for what the company's data already knows reliably.

The owner chose to build them and Chatwoot in Hebrew away from production: *"lets create a sandbox for this so we dont touch the prod"*, then *"we just need to make sure the prod is not being affected the sandbox is independent"*.

## Why a live sandbox and not the offline harness alone

Three options were put to the owner:
- **A, offline only:** `wa_qa.py` with Claude playing the bot. It is free, but nobody can chat with it.
- **B, a live copy reached through a web chat.**
- **C, a second Meta app with its own test number:** more Meta setup, and the same 5-recipient limit.

The owner picked B. The offline harness still runs before anything is promoted: it tests the rules for free, while B lets the owner feel the conversation on Gemini.

## Why a separate Chatwoot account, not just a new inbox

The interface language, team names and labels are **account-wide** in Chatwoot. A sandbox inbox inside account 2 would make Hebrew a change to the live inbox. A second account on the same server isolates all of it.

## Why the sandbox writes nothing to the database

"Independent" rules out test rows in the live tables, even on the test building:
- `requests` feeds the dashboard and, for listed numbers, the OXS mirror;
- `messages` feeds the live bot's own guards (`Anything newer?`).

So the sandbox writes its log and its tickets to n8n Data Tables, and its tickets get `SBX-` references. Reads are allowed, because they change nothing. And recognising a tenant needs the real tenant list.

## Why the stored payment link

OXS mints a new payment link on every call to `/payment-link` (spec rev 1.3, "Each call mints a NEW link"). A new link is a new object in the client's system, so the sandbox reuses the newest link already stored in `payment_links`, or shows a placeholder.

## Why the labels keep their English titles

The bot and "Hand to a person" find conversations by label title: `handover`, `handover-<department>`, `after-hours`, `escalated`, `bot-off`. Renaming them would mean changing every workflow that writes or reads them. Hebrew descriptions and colours give staff the meaning, and nothing breaks.

## Open decisions

1. **The sandbox's OpenRouter key.**
   - **A separate key with a small cap,** created by the owner in OpenRouter, means sandbox chats can never empty the live bot's wallet. This is the recommendation.
   - **Sharing the live key** is simpler, but its spend comes out of the live wallet.
2. **The balance check.** Yariv asks not to re-ask what is reliably known. The 13 Aug security rule (his own feedback then) says a handset is not an identity for money: a typed name and phone are needed before a balance. The sandbox keeps the rule; it is raised with Yariv.
3. **Going live.** Each change is promoted separately, on the owner's go:
   - the menu and the prompt through `check_whatsapp_rules.py`;
   - `whoami` into `debt-tools` with `--oxs-mirror`;
   - Hebrew onto account 2.

## Ruled out

- **A separate Supabase project for the sandbox:** copying schema and data is days of work for no gain, while reads are harmless.
- **Routing a tester's number from the live workflow to the sandbox:** it would let testers use real WhatsApp, but it is an edit to the live workflow, which the owner ruled out.
