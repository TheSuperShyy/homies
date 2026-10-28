# 19 — WhatsApp sandbox

**Estimate:** 2d
**Depends on:** 11 (WhatsApp bot), 12 (Chatwoot), 16 (human handover), 17 (name before a ticket)
**Status:** built 26 Oct 2026 (see "As built" below); the production fingerprint was unchanged after every step. The paid acceptance run waits on the owner's go.

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
| n8n | "Homies — WhatsApp bot" `u2JjrbcNPYyyh3yl`, "Hand to a person" `oB66atFlWwtkSGgN`, "debt tools (Vapi)" `lXofknAbE5wu5nwQ` | copies: "SANDBOX — WhatsApp bot", "SANDBOX — Hand to a person" and "SANDBOX — debt tools router"; webhooks `homies-whatsapp-sandbox` (its own secret) and `homies-debt-tools-sandbox`; Chatwoot credentials for the sandbox account only |
| Backend | `debt-tools` v130 | `debt-tools-sandbox`: the live `index.ts` **unchanged**, loaded behind `guard.ts`, a network guard. The guard lets Supabase reads through, answers every Supabase write itself with a fake success, and refuses every other host. A faked ticket gets a reference in the live shape, `999-9000NN-YY`. It is deployed without touching project secrets |
| Chat log | Supabase `messages` | none of its own: the sandbox Chatwoot conversation is the log, and `Anything newer?` reads it from there |
| Model | the OpenRouter credential | the same credential, unchanged (owner's decision 26 Oct). Spend comes from the live wallet, so the balance is checked around every round |
| Channel | Meta's test number +1 555-178-1261 | a chat page served from the owner's PC (`scripts/sandbox_chat.py`) on Chatwoot's public API, with a "writing as" picker |

## Isolation rules

The sandbox may not:
1. **Write to Supabase.** No `requests`, `payment_links`, `interactions`, `messages` or `call_outcomes` rows. A ticket comes back as `999-9000NN-YY` and lives only in the sandbox conversation. The serial starts at 900001, which no real ticket has, so a lookup by it finds nothing.
2. **Change anything in OXS.** OXS's payment-link GET mints a new link on every call (spec rev 1.3), so the guard refuses every OXS call. A link already on record in `payment_links` is read and handed back, exactly as live does; a tenant without one gets the function's usual "no link" path.
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
- The system menu has two buttons: פתיחת קריאת שירות and מצב קריאה קיימת. לדבר עם נציג is gone, from Sort's menu and from the copy `Send` re-attaches after a "how can I help".
- When someone types a request for a person, the bot tries to solve it.
- If it cannot, `notify_team` records the matter: in the sandbox, a private note in the sandbox conversation.
- Only an emergency is handed to the team at once.
- **The bot handles the matter itself (the owner, 27 Oct):** *"we should handle everything in our own we dont rely on anyone but we do keep a note for the team if ever there is such a conflict like this"*.
  - A tenant who insists on a manager is asked what it is about. Then the bot works the matter itself.
  - Because a manager was asked for, it also leaves the team a note and says so in one sentence, and the same message carries on with the matter. It does not end on "the team knows".
  - "You can't help me with this" does not end it (the owner's next chat, 27 Oct). The bot says what it can do with the matter and asks what is going on. Only the matter itself, once known, decides what is beyond the bot.
  - The committee **fee** (balance, paying, the link, what it covers) is the bot's. Only a matter with the committee's people stays on the staff-only list.
  - **Its reason for asking is its own, and it comes before the question** (28 Oct). It needs to know what happened to sort it out itself, faster, often right here. The insisting turn keeps that reason. It is never management's, never a relay to the team, and never "meanwhile".
  - **The matter is noted the moment the tenant names it,** under its own reason, so management never keeps a bare "wants a manager". `sandbox_drive.py` reads `handover_reasons` to check this.

**E. No claim that the team is acting** (28 Oct; live behaviour, fixed here first).
- A reply says what the tools did: the ticket and its number, that the team was told. It never says what the team is doing or will do: no "הצוות יראה את זה ויטפל", no "ועל זה עכשיו".
- The facts line that said the team sees it and handles it is gone. The emergency sentence has the bot as its subject ("אתה פותח מיד … ומעדכן את הצוות"), so "at once" is the bot's.

**B. Recognising the sender** (section 6: do not ask again for what the company's data knows reliably). Before the model runs, the sandbox workflow reads `residents` by the sender's number ("Who is writing?", a GET) and "Add who" turns the rows into a bracket fact. Then:
- **One match:** the model input carries `[הפונה מזוהה במערכת: <שם>, <בניין>, דירה <n>]`. The bot does not ask for the name, building or flat. When it opens a ticket it does not ask to confirm the place either: the same message says where the ticket was filed ("פתחתי קריאה על המעלית ב<בניין>, ורשמתי אותה על דירה <n>"), so the tenant can correct it (the owner, 27 Oct; the confirmation question it replaced was skipped by the model twice). The flat is named as the one the ticket is recorded on, apart from where the fault is: asked only for "where", the AI gave a lift ticket the building alone (28 Oct). The ticket tool's own "ask for the flat every time" gets one sentence for this case, so the rule and the tool do not compete.
- **Several flats:** it asks which one.
- **No match:** it asks as it does today.
- **The balance does not change:** it still needs a typed name and phone (open decision 2).

**D. One reply per burst** (the owner's sandbox chat, 27 Oct; a live behaviour, fixed here first).
- The bot waits about 4 s for the tenant to finish, then the AI writes for 15-20 s. A message sent in that gap had its own run, and both runs answered: two near-identical replies, half a second apart.
- Right before Send, the copy now reads the conversation again and drops its reply if the tenant has written since. The newer message's run answers everything since the last reply.
- **Exceptions:** a bare hello (it gets the menu, not the backlog) does not stop a reply, and a failed check sends, as before.

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
- It checks for new messages every 1.5 s and never stops: a failed check is tried again, and an answer for a conversation left in the meantime is dropped.
- A message typed before the conversation is open waits for it. A failed send goes back into the box.
- A line in the header says what the page is waiting for.

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
4. **Writing as Ido**, the bot never asks for his name, building or flat, opens the ticket at once, and names the building and flat in that reply. **Writing as an unknown number**, it asks as today. **A tenant with several flats** is asked which one (no persona has several flats, so this one is checked offline only: "Add who" lists the flats).
5. The balance still asks for a typed name and phone.
6. The sandbox account shows the Hebrew interface and Hebrew names, and account 2 is unchanged.
7. Deleting the sandbox (the account, the workflows, the credentials and the function) leaves the live system unchanged.

## As built (26 Oct 2026)

| Piece | Id | Made by |
|---|---|---|
| Chatwoot account | 3, "הומי'ז — סביבת ניסוי", locale `he`; the owner is an administrator | `scripts/chatwoot_sandbox.py` |
| Chatwoot inbox, bot, teams | API inbox 3 "צ'אט ניסוי"; agent bot 2 "מיכאל — ניסוי"; teams 5 גבייה, 6 תפעול ותקלות, 7 הנהלה, 8 שירות לדיירים | same |
| n8n | router `OLzT4Y7dXWYSpfXg`, handover `OnvgKPLYGGwsqY2G`, bot `SI4iUJJnLG5ghY6n` (section 6 in); credentials "SANDBOX Chatwoot admin" and "SANDBOX Chatwoot bot" | `scripts/n8n_sandbox.py --apply --section6` |
| Function | `debt-tools-sandbox` v3 (random fake serials since 27 Oct) | `scripts/sandbox_function.py --apply` |
| Memory round | `SANDBOX_MEMORY_ROUND` 36 since 09:27 UTC on 28 Oct (key `<phone>-84-sbx36`); a `sandbox_drive.py --fresh` run takes one round per persona reuse, so `.env` is the truth | `scripts/n8n_sandbox.py --apply --section6 --fresh-memory` |
| Snapshot | `local/sandbox/before.json`, taken before the build | `scripts/sandbox_fingerprint.py` |

Every id and token is in `.env` under `SANDBOX_*`. The personas are `SANDBOX_PERSONAS` (Ido, Yariv, the owner's +63 as אסף, and an unknown test number).

- **To chat:** `python scripts/sandbox_chat.py`, then open http://127.0.0.1:8765. Since 27 Oct it runs as its own process, logging to `local/sandbox/chat.log` and `chat.err.log`. After a change to the page, restart it and reload the tab. `python scripts/check_sandbox_chat.py` checks the page offline.
- **To regenerate after a live change:** `python scripts/n8n_sandbox.py --apply --section6` and `python scripts/sandbox_function.py --apply`. They re-read live and PUT the same sandbox ids. The copies are never edited by hand.
- **To check production:** `python scripts/sandbox_fingerprint.py --compare local/sandbox/before.json`.
- **Acceptance run 1 (27 Oct, $0.52): 4/6 by the checks.**
  - Section 6 behaved: two buttons; Ido was not asked where he lives; a stranger was.
  - The AI wrote its reasoning into three replies to Ido. That defect is open, with the details in WORKLOG 27 Oct.
- **Acceptance run 2 (27 Oct, $0.40):**
  - The faithful copy opened 3/3 tickets with clean replies, so the leak is a rare slip, not live behaviour.
  - With clean memory, Ido's "I want a representative" and his balance pass.
  - His lift ticket opens without the place being confirmed or named. That is the owner's call.
- **Acceptance run 3 (28 Oct, $1.02): 8/10 by the checks, every scenario on a clean memory** (`--run all --fresh`).
  - The lift ticket names the building but not the flat.
  - The manager replies slip back to "so management can handle it" when the tenant insists.
  - 7 of 18 replies end on a statement.
  - The reading is in WORKLOG 28 Oct.
- **Acceptance run 4 (28 Oct, 08:53-09:29 UTC, about $1.17): the faults fixed one cause at a time, each tested on Gemini with the scenarios it touches.**
  - Each fix's own fault is gone in its test: the flat, the borrowed reasons, "בינתיים", the read-out committee bullet, "on it now", and the missing second note.
  - Three runs still failed one check each, on a reply ending in a statement. Two were polite requests ("אשמח ש…"); one first reply asked first.
  - Manager replies ending on a question: 7 of 13 before, 17 of 20 after.
  - The text the model reads is 1,101 characters shorter.
  - Each step is in WORKLOG 28 Oct.

**Where the sandbox knowingly differs from live:**
- **Chat log.** It is the Chatwoot conversation. A two-part reply is two rows there, and the quick "word first" line counts as a bot message; live writes one `messages` row per reply.
- **Memory key.** It ends in `-sbx`, so no sandbox turn can enter a live conversation's memory.
- **Binary mode.** n8n's public API drops the `binaryMode: separate` setting. The bot carries no binary data (photos travel as Chatwoot links), so this has no effect.
- **Tickets.** A sandbox ticket cannot be found later, because the status tool reads the real table. A photo is not copied, because the guard refuses the Chatwoot host.
- **After-hours notes.** Outside Sun-Thu 09:00-17:00 Israel time, "Hand to a person" labels the conversation `after-hours` and holds the note for the live morning ticker. The ticker reads account 2 only, so a sandbox note held that way never posts. Only the labels show.
- **Canvas.** The live bot's one overlap (`Show it in Open` over `Type for a moment (menu)`) is carried over. The added nodes overlap nothing.
