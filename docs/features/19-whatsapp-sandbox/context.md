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

So the sandbox's backend is the live code behind a network guard (`guard.ts`), which answers every Supabase write itself. Its tickets get `SBX-` references, and its chat log is the sandbox Chatwoot conversation. Reads are allowed, because they change nothing, and recognising a tenant needs the real tenant list.

**Why a guard and not a modified copy (26 Oct, found while planning).** Running the live `index.ts` unchanged means what is tested is exactly what runs live, and production code is not edited. `scripts/supabase_functions.py` pushes and deletes **project-wide** secrets on every run, so a plain run would switch off the live OXS mirror. The sandbox therefore has its own deploy (`scripts/sandbox_function.py`), which only uploads files.

## Why no payment link in the sandbox

OXS mints a new payment link on every call to `/payment-link` (spec rev 1.3, "Each call mints a NEW link"). A new link is a new object in the client's system, so the guard refuses OXS, and the bot takes the function's usual no-link path (a ticket and a team note, both sandbox-only).

## Why the labels keep their English titles

The bot and "Hand to a person" find conversations by label title: `handover`, `handover-<department>`, `after-hours`, `escalated`, `bot-off`. Renaming them would mean changing every workflow that writes or reads them. Hebrew descriptions and colours give staff the meaning, and nothing breaks.

## Open decisions

1. **The sandbox's OpenRouter key. Decided 26 Oct: share the live one.** The owner said *"lets use the openrouter we have rn"*.
   - The sandbox uses the existing n8n credential "Homies OpenRouter (OPENROUTER_API_KEY)" as it is; using a credential does not change it.
   - Its spend comes out of the live wallet. So the free offline harness carries the automated tests, live sandbox chats are the owner's own, and the balance is checked (`GET /api/v1/key`, free) before and after each round.
2. **The balance check.** Yariv asks not to re-ask what is reliably known. The 13 Aug security rule (his own feedback then) says a handset is not an identity for money: a typed name and phone are needed before a balance. The sandbox keeps the rule; it is raised with Yariv.
3. **Going live.** Each change is promoted separately, on the owner's go:
   - the menu and the prompt through `check_whatsapp_rules.py`;
   - `whoami` into `debt-tools` with `--oxs-mirror`;
   - Hebrew onto account 2.

## Ruled out

- **A separate Supabase project for the sandbox:** copying schema and data is days of work for no gain, while reads are harmless.
- **Routing a tester's number from the live workflow to the sandbox:** it would let testers use real WhatsApp, but it is an edit to the live workflow, which the owner ruled out.
