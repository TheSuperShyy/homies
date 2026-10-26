# 19 — WhatsApp sandbox

**Estimate:** 2d
**Depends on:** 11 (WhatsApp bot), 12 (Chatwoot), 16 (human handover), 17 (name before a ticket)
**Status:** designed 26 Oct 2026, approved by the owner; not built

## Purpose

This is a place to build and try two things without touching anything live:
- the WhatsApp changes in Yariv's accepted alignment document (`docs/discovery/yariv-alignment-2026-10.md`, section 6);
- Chatwoot in Hebrew.

The owner's condition: *"we just need to make sure the prod is not being affected the sandbox is independent"*. If the sandbox is broken or deleted, the live bot, the live inbox, the live function, the database and the WhatsApp number are exactly as before.

## What it is made of

Every piece is new and named SANDBOX. Nothing live is edited.

| Piece | Live (untouched) | Sandbox |
|---|---|---|
| Chatwoot | account 2: inbox 1 (WhatsApp), the agent bot | a new account, **"Homies — Sandbox"**, with an API inbox, its own agent bot, its own admin user and its own tokens |
| n8n | "Homies — WhatsApp bot" `u2JjrbcNPYyyh3yl`, "Hand to a person" `oB66atFlWwtkSGgN`, "debt tools (Vapi)" `lXofknAbE5wu5nwQ` | copies: "SANDBOX — WhatsApp bot" and "SANDBOX — Hand to a person"; webhook `homies-whatsapp-sandbox` with its own secret; Chatwoot credentials for the sandbox account only |
| Backend | `debt-tools` v130 | `debt-tools-sandbox`: the live `index.ts` **unchanged**, loaded behind `guard.ts`, a network guard. The guard lets Supabase reads through, answers every Supabase write itself with a fake success, and refuses every other host. It is deployed without touching project secrets |
| Chat log | Supabase `messages` | none of its own: the sandbox Chatwoot conversation is the log, and `Anything newer?` reads it from there |
| Model | the OpenRouter credential | the same credential, unchanged (owner's decision 26 Oct). Spend comes from the live wallet, so the balance is checked around every round |
| Channel | Meta's test number +1 555-178-1261 | a chat page served from the owner's PC (`scripts/sandbox_chat.py`) on Chatwoot's public API, with a "writing as" picker |

## Isolation rules

The sandbox may not:
1. **Write to Supabase.** No `requests`, `payment_links`, `interactions`, `messages` or `call_outcomes` rows. A ticket comes back as `SBX-<n>` and lives only in the sandbox conversation.
2. **Change anything in OXS.** OXS's payment-link GET mints a new link on every call (spec rev 1.3), so the guard refuses every OXS call and the bot gets the function's usual "no link" path.
3. **Call Meta.** No typing indicator, no template, no message.
4. **Call Chatwoot account 2.** The sandbox's tokens open only the sandbox account.
5. **Call the live n8n workflows or the live function.**

It may **read** Supabase: `residents`, `buildings`, `apartments`, `requests` (status) and `charges` (balance).

A check script snapshots the live system before the build and compares it after the build and after every test round:
- the n8n workflows' node hashes and `updatedAt`;
- the live function's version;
- account 2's settings, inboxes, labels and teams;
- the row counts of `requests`, `messages`, `payment_links` and `interactions`.

## Behaviour under test

**A. No representative button** (section 6).
- The system menu has two buttons: פתיחת קריאת שירות and מצב קריאה קיימת. לדבר עם נציג is gone.
- When someone types a request for a person, the bot tries to solve it.
- If it cannot, `notify_team` records the matter: in the sandbox, a private note in the sandbox conversation.
- Only an emergency is handed to the team at once.

**B. Recognising the sender** (section 6: do not ask again for what the company's data knows reliably). Before the model runs, the sandbox workflow reads `residents` by the sender's number ("Who is writing?", a GET) and "Add who" turns the rows into a bracket fact. Then:
- **One match:** the model input carries `[הפונה מזוהה במערכת: <שם>, <בניין>, דירה <n>]`. The bot does not ask for the name, building or flat. When it opens a ticket it confirms once: "זה לגבי <בניין>, דירה <n>?".
- **Several flats:** it asks which one.
- **No match:** it asks as it does today.
- **The balance does not change:** it still needs a typed name and phone (open decision 2).

**C. Chatwoot in Hebrew,** in the sandbox account only:
- account locale `he`;
- the account named "הומי'ז — סביבת ניסוי";
- the teams named גבייה, תפעול ותקלות, הנהלה, שירות לדיירים;
- the conversation attributes given Hebrew display names;
- the labels keep their English titles, which the bot and the handover depend on, and get Hebrew descriptions and colours by urgency.

## Interface

**"Who is writing?" + "Add who"** (sandbox workflow nodes, between `Still the last word?` and its successors)

- **Who is writing?** is a GET `residents?phone=eq.+<digits>&select=full_name,building,unit` with the Supabase service-key credential. It always outputs data, and an error passes on.
- **Add who** passes the items through and adds `who_text`:
  - **one row:** ` [הפונה מזוהה במערכת: <שם פרטי>, <בניין>, דירה <n>.]`;
  - **several:** ` [הפונה מזוהה במערכת: <שם פרטי>, עם כמה דירות: <בניין> דירה <n>; …]`;
  - **none:** an empty string.
- `Answer the resident` puts `who_text` in its input before the time bracket.

**The chat page** is `scripts/sandbox_chat.py`, served on `127.0.0.1:8765`. It proxies Chatwoot's public API for the sandbox API inbox, and has a "writing as" picker (Ido, Yariv, Assaf, an unknown number) taken from `SANDBOX_PERSONAS` in `.env`. Each persona is a Chatwoot contact carrying that phone, the way a WhatsApp contact carries its number.

## Data

- **Reads** (Supabase): `residents` (`phone`, `full_name`, `building`, `unit`), `buildings`, `apartments`, `requests` (`reference`, `status` and the reporter's phone), `charges`, `payment_links` (`link`, newest per resident).
- **Writes:** nothing outside the sandbox Chatwoot account (its conversations, notes and labels). Every Supabase write is answered by the guard and never sent.

## Acceptance

1. After the build, every live fingerprint equals the snapshot taken before it.
2. The acceptance run (`scripts/sandbox_drive.py`, 6 scripted conversations) and the owner's own chats leave:
   - zero new rows in `requests`, `messages`, `payment_links` and `interactions`;
   - zero calls to Meta or to an OXS write;
   - zero calls to Chatwoot account 2.
3. The menu shows two buttons. "אני רוצה לדבר עם נציג" gets help, not a transfer. An emergency still pages the sandbox team.
4. **Writing as Ido**, the bot never asks for his name, building or flat, and opens a ticket after one confirmation. **Writing as an unknown number**, it asks as today. **A tenant with several flats** is asked which one.
5. The balance still asks for a typed name and phone.
6. The sandbox account shows the Hebrew interface and Hebrew names, and account 2 is unchanged.
7. Deleting the sandbox (the account, the workflows, the credentials and the function) leaves the live system unchanged.
