# Moving the WhatsApp line and the staff inbox to UChat

**Estimate:** 13-19d (one developer), plus 1d for the dry run that can happen first
**Depends on:** 11-whatsapp-bot, 12-chatwoot, 16-human-handover; a WhatsApp number UChat can connect (in practice Homies' own)
**Status:** prepared 3 Nov 2026. **The UChat version of the bot is built and running on our side (3 Nov, owner: *"lets create a uchat version as well of the chatbot"*)**, beside the live bot. **It answers in UChat's web chat since 3 Nov, 08:19 UTC**, on a new UChat account the owner opened (workspace "homies-uchat", bot `f315405`). That account is on UChat's free Pro trial, which ends about 16 Nov; after that it needs the Business plan, $15 a month, or it stops answering.

## Purpose

The plan for leaving Chatwoot if we ever have to, written before it is needed
(the owner, 3 Nov: *"we need to prep for migration to uchat just in case"*).
UChat takes the number and becomes the staff inbox. **The bot is not rebuilt:**
it stays in n8n with its reply checks, its tests and its memory. The tool
server, the data, the dashboard and the phone agents stay where they are.
Without this plan, a move would start from a blank page under time pressure.

## The route

| | |
|---|---|
| **Moves to UChat** | The number's connection; the staff inbox (seats, departments, labels, hand-over, the bot's pause); the bot's way in and out (n8n talks to UChat's API instead of Chatwoot's); the tool server's WhatsApp sends |
| **Stays** | The n8n bot (prompt, reply checks, memory keyed by the tenant's number, OpenRouter); Supabase (residents, tickets, the message log, photos); the dashboard; the OXS sync; the voice agents; the Meta templates, which belong to the WhatsApp account, not to the platform |
| **Not chosen** | Rebuilding the bot as a UChat AI agent: 21-34 days, and it loses the before-sending checks and the replay tests. Kept in [uchat-comparison.md](../11-whatsapp-bot/uchat-comparison.md), Option A |

## The UChat version (built 3 Nov 2026)

`scripts/n8n_uchat.py` builds it from live, the way `n8n_sandbox.py` builds
the sandbox. Re-run it after a change on live; never edit the copies by hand.

| Piece | What it is |
|---|---|
| "UCHAT — WhatsApp bot" (`mKheBsTxtcMhPxu7`) | The live bot regenerated from live. Its prompt, reply checks, memory rules and tools are live's, unchanged. Webhook `homies-whatsapp-uchat`, with its own secret |
| "UCHAT — Chatwoot-compatible API" (`FIVPZiM5udeXFacS`) | The translator. It takes the bot's Chatwoot calls, does them through UChat's API, and answers in Chatwoot's shape. Door: the `api_access_token` header |
| "UCHAT — Hand to a person" (`EYePE3S0E6t1kojj`) | The live hand-over, paging through the translator |
| UChat workspace "clix", bot "homies-chatbot" | 9 tags (`bot-off`, the handover labels, `urgent`) and 10 contact fields (`team_note`, the `handover_*` stamps), made by `--uchat` |

**How a message travels:**
1. UChat's default reply runs the sub flow "Michael". Its one step, an External Request, posts `{"user_ns": …}`.
2. `Who is this? (UChat)` and `Which message? (UChat)` read the contact and their newest message back from UChat.
3. `From UChat` hands Sort the Chatwoot event it has always read. From there on, the bot is the live bot.
4. Replies go out through the translator, all as the bot (`send-content`, `send_as_agent: 0`). The menu's buttons each run their own step, "Michael", "Michael 2" or "Michael 3", which hold the same External Request.

**Differences from live, all on purpose:**
- **Everyone gets through since 3 Nov** (`UCHAT_TEST_PHONES=all` in `.env`; a list of numbers brings the filter back). The copy uses the live tools, so a ticket it opens is real, as on the live WhatsApp bot.
- **The memory key gets `-uchat`,** so the two bots never share a memory.
- **Nothing is written to the live `messages` log.** The burst check reads the UChat conversation instead.
- **The typing dots are live's call for the UChat number** (3 Nov). UChat keeps WhatsApp's message id (`mid`); the translator passes it on as `source_id`.
- **A private note becomes the contact's `team_note` field,** because UChat's API has no internal note. A label goes on twice: as a tag, which the copies read back, and as a UChat label, which staff see. A team becomes its agent group through `UCHAT_GROUPS` (see "Set up like our Chatwoot" below).
- **No 15-minute hand-back copy.** UChat's own pause after a staff reply does that job (30 minutes, staff can extend).
- **`Worth a word?` runs only on a message with a payment word** (`A payment word?`, 3 Nov). Its note could go out only then anyway, so the replies are the same, and every other AI reply comes about 6 s sooner.
- **`Let them finish` waits 2 s, and none after a button tap** (live: 4 s), and the way in reads the contact and its messages at once (3 Nov, for speed). The model stays live's: 3.7 Flash was tested and not taken (WORKLOG 3 Nov).

**Proven on 3 Nov, with a contact that does not exist (no AI was called):**
- the translator refuses a call without the door (401);
- it gets UChat's "not found" and answers it in Chatwoot's shape;
- the copy's whole way in runs without an error, to `Sort` and `Answer Meta`.

**Done in UChat's builder (3 Nov),** driven from a local Chrome window that the owner logged in to:
- the sub flow **Michael** (`f306703s5045787`), a draft;
- its Start step leads to an empty Action step, "Action #1".

**Blocked on the free plan, in the first account ("clix"):**
- Adding **External Request** to that step was refused: *"Upgrade to Pro account to use this feature."*
- The other ways out of UChat are Pro too: Integrations (the Webhook integration), Notification and AI Actions.

**Finished on a new account (3 Nov), owner: *"i open a new account"*:**
- **The account:** "CLIX", workspace **homies-uchat**, on the Pro trial (13 days left on 3 Nov).
- **The bot:** "homies-chatbot", an Omni bot, flow `f315405`.
- **The sub flow Michael** (`f315405s5045807`):
  - Start → the step **Michael**, which holds the External Request;
  - it posts `{"user_ns": <User Ns>}` (raw JSON, the field put in with UChat's picker) to the copy's webhook;
  - published.
- **Its API key** ("homies-n8n"):
  - Manage Flow only, so the team endpoints answer 403.
  - It is in `.env` as `Uchat_api_key`; the first account's key is kept as `UCHAT_API_KEY_CLIX`.
- **Our side, pointed at it:**
  - `UCHAT_FLOW_NS=f315405`;
  - the translator's UChat credential made again with the new key (the old one deleted);
  - `--uchat` (9 tags, 10 fields) and `--apply`.
- **`--wire`:** the default reply and the web chat's start flow are both "Michael" (read back: active, `f315405s5045807`).
- **The web chat** is at `https://www.uchat.com.au/p/web/<bot code>`; the builder's Preview → "Open in Web Browser" gives it.
- **`--tester`:** the first chat contact carries the test phone.
- **Contact ids are `f315405u<digits>`,** the shape the translator rebuilds.

**Proven, 3 Nov 08:19 UTC, no AI called:**
- In UChat's web chat, "היי" got the live bot's own greeting, "בוקר טוב 👋 כאן הומי'ז. במה אפשר לעזור?", with the two buttons פתיחת קריאת שירות and מצב קריאה קיימת.
- **The copy's run** (execution 150459, green): `From UChat` → Sort → `Canned reply?` → `Send` → `Show it in Open`.
- **The translator's runs:** all green.
- **The run before it** (150455, the chat opening) skipped with "nothing from the contact yet", as it should.

**On WhatsApp since 3 Nov,** on the owner's own Israeli number (never in this public repo; HANDOVER says where it is), through UChat's WhatsApp Cloud:
- **Proven 09:50 UTC on the owner's phone:** "היי" got the greeting with both buttons, and a tap on פתיחת קריאת שירות went to the AI, whose answer arrived.
- **Each button needs its own step:** UChat makes a button's WhatsApp id from its step, and WhatsApp refuses a message whose buttons share an id (#131009). The web chat does not show this.

**Not yet tried** (each one calls the AI, so it is a paid test):
- a real question through to a ticket;
- the hand-over from a real message. Its UChat end is proven without the AI (below).

### Set up like our Chatwoot (3 Nov)

The owner: *"ok just make uchat like the settings we have on the chatwoot"*. Read from Chatwoot account 2 first: 4 teams, 2 users, 8 labels, 9 conversation attributes. It has no saved replies, automations, macros, webhooks or integrations. Greeting, working hours, auto-assignment and the satisfaction survey are all off.

| Chatwoot | UChat now |
|---|---|
| Teams `collections`, `operations`, `management`, `service` (ids 1-4) | Agent groups with the same names: `20217`, `20219`, `20221`, `20223`. `UCHAT_GROUPS` in `.env` maps team id to group id |
| Assaf Clix in `service`, the other three empty | The owner ("CLIX", UChat user `357951`) in `service`, the other three empty |
| 8 labels | The same 8 as UChat labels; the Live Chat sidebar's "show labels" and "show department" are on |
| 9 conversation attributes | Contact fields, made earlier by `--uchat`, plus `team_note` |
| Account language Hebrew | The owner's UChat profile in Hebrew. UChat has no workspace language: each member picks their own. The dashboard turns right-to-left |
| Working hours off | Business hours "open all day" every day, which only a flow that checks them reads |
| A team assignment picks nobody | **UChat always gives the chat to a member of the group:** Random, Least Assigned or Round Robin, no "nobody". All four groups use Least Assigned, and members see every conversation |
| Users Assaf Clix (administrator, clixteam579@gmail.com) and "seat2 test" (agent) | CLIX (the owner's login, owner) and, since 3 Nov, "Assaf Clix" (clixteam579@gmail.com, admin, Hebrew profile, in no group). Invites are made in Workspace Settings → Users, since the API has none. The trial holds 2 users |
| The test seat "seat2 test" | Not invited: an invite emails a person, so it waits for the owner's word. The trial is full; a third member needs Business |

**The key:** team calls need UChat's "Manage Team" ability, which the bot's key (`Uchat_api_key`, Manage Flow) lacks. A second key, "homies-team-setup", has Manage Team only. It is in `.env` as `UCHAT_API_KEY_TEAM`, and was read off the page by a script without being shown.

**The translator:** written again with the groups and the labels' second call (`Map a write`, labels → `add-tags-by-name` and `add-labels-by-name`). Only it was written; the bot and hand-over copies did not change. Rollback snapshot: `local/uchat-prep/n8n-uchat-translator-before-groups-2026-11-03.json`.

**Proven 3 Nov, with no AI:** the translator was called as the hand-over calls it (team 4, then the labels `handover` and `handover-service`) on the web chat's contact.
- The contact went to group `20223`, and UChat gave it to the owner, the group's one member.
- Both labels arrived as tags and as UChat labels.
- **The bot was not paused** (`paused_diff_seconds` 0). In UChat only a staff reply pauses it, as in Chatwoot, where the bot keeps answering after a hand-over.
- Everything was removed afterwards (tags, labels, the assignee), and the contact read back as it was.

**Then from here:**
- `--wire` makes "Michael" the default reply and the web chat's start flow.
- `--tester <user_ns>` puts the test phone on that contact.
- A first "היי" gets the menu without touching the AI.

**Connected on 3 Nov evening** (owner: *"lets connect everything in the uchat?"*, after counting the bot as moved):
- **The dashboard's log.** The copy's `Log inbound` / `Log reply` write the live `messages` table again, as `source` 'uchat' with ids `uchat:<n>`. UChat numbers our messages from 1, Chatwoot's range, and `external_id` is unique. Live at 17:25 UTC. No UChat row yet: nobody had written since.
- **Photos on tickets.** The tool server (v140) lets UChat's domain through its photo fence and keeps the `uchat:` prefix, which it used to strip. A bare id would have overwritten a Chatwoot photo with the same number. `MEDIA_HOSTS_EXTRA` adds another host as a setting. Not proven with a real photo: none had come through UChat to show its host.
- **The debt call's link and the "done" notice** leave from the UChat number when `WHATSAPP_VIA=uchat` (set). Free text goes inside 24 hours, judged by the contact's `last_interaction` (UTC, checked). Outside them a template goes by phone with `create_if_not_found`. Delivery is read back as WhatsApp's id (`mid`). `WHATSAPP_VIA=chatwoot` and an `--apply` move back.
- **Probed with no AI and nothing stored:** `send_ticket_notices` answers `via: uchat`. `store_media` lets a UChat address through (404 on a made-up file) and refuses another host.

**Not connected yet, and why:**
- **Templates.** `ticket_resolved_he` and `payment_link_he` are approved on the Chatwoot test number's WhatsApp account ("Test Messaging Account"), not on the UChat number's ("hadas 1"). That account has none, so UChat's sync finds nothing and a notice waits as `template_not_synced`. They have to be created there; that is a write in Meta, which waits for the owner's go.
- **Meta blocks the UChat number from starting conversations:** WABA 141006, no payment method; also business 141010, not verified. So even a template cannot go until a payment method is added in WhatsApp Manager. Replies inside 24 hours are not affected.
- **The phone agents' notes** still open a conversation in Chatwoot's Voice inbox. UChat has no inbox for calls. Its place for them is a ticket list, which only UChat's dashboard can create (the API adds items, not lists), and the workspace has none.
- **Residents' voice notes:** unchanged. The live bot cannot hear them either; it says the file arrived and cannot be read.
- **The live number** stays on Chatwoot: moving it is the cutover below.

## What has to change

Read from the live system on 3 Nov 2026: all 8 Homies workflows on n8n, the
tool server's code, the dashboard. Every UChat call below needs only the
"Manage Flow" ability, which our key has.

### The bot, n8n "Homies — WhatsApp bot" (`u2JjrbcNPYyyh3yl`)

| Step | Today, through Chatwoot | In UChat |
|---|---|---|
| `WhatsApp` + `Sort` | Chatwoot's agent bot posts every event to the webhook. `Sort` checks the secret, keeps new messages, treats a staff reply as a takeover, and reads the on/off switch (assigned to a person, `bot-off` label, resolved) | UChat's **Webhook integration** forwards every incoming message. A new `Sort` reads UChat's payload. The switch becomes UChat's own pause plus a tag. **The payload's format is not published:** the dry run captures it |
| `Send`, `Send the rest`, `Say it now` | A message on the conversation | `POST /subscriber/send-text` |
| `Send menu` | Chatwoot's three-button list | The menu built once as a UChat flow node; `POST /subscriber/send-node` |
| `Show it in Open` | `toggle_status` | `POST /subscriber/move-chat-to` (`open`) |
| `Assign to the replier` | Assigns the staff member who replied, so the bot stops | UChat pauses the bot by itself when staff reply (30 minutes, staff can extend). `POST /subscriber/assign-agent` only where an owner is needed |
| `Read the photos` | Reads the conversation's messages for the photos | The media link in the webhook payload, or `GET /subscriber/chat-messages` |
| `Show typing`, `Show typing again` | Meta's typing call, with Meta's message id that Chatwoot passes on (`source_id`) | Kept only if UChat's payload carries Meta's message id; otherwise dropped |
| Everything else | Supabase log, who is writing, memory, the tools, the checks | Unchanged |

### The other workflows

| Workflow | Today | In UChat |
|---|---|---|
| "Hand to a person" (`oB66atFlWwtkSGgN`) | Reads the conversation; a private note pages the department; team, priority, labels, a stamp | `POST /subscriber/assign-agent-group` (four groups: Collections, Operations, Management, Service); `POST /subscriber/add-labels-by-name`; the stamp as a user field (`PUT /subscriber/set-user-field-by-name`); priority as a label. **UChat's API has no internal-note call.** The matter goes on a ticket-list item (`POST /team/ticket-lists/{listId}/create`) or through a flow node with a staff notification. The dry run decides |
| "Chatwoot handback" (`IVNR5iNn7bQS8JgP`) | Every few minutes: a taken conversation quiet for 15 minutes is unassigned and loses `bot-off` | `POST /subscriber/pause-bot` with `minutes`, and `resume-bot`. The 15-minute rule becomes the pause length |
| "Voice team note" (`pduAdXjX1EU7cA6E`) | The phone agents' note opens a conversation in Chatwoot's Voice inbox | UChat has no inbox for a non-chat channel: a ticket-list item per call, or Chatwoot kept running for the Voice inbox only |
| "ticket notices" (`pvMuradcJOASapF0`) | Calls the tool server | Unchanged |
| "number watch", "call queue", "debt tools (Vapi)" | No Chatwoot | Unchanged |

### The tool server (`supabase/functions/debt-tools`)

| Action | Today | In UChat |
|---|---|---|
| `send_ticket_notices` (the "done" message) | Reads the approved templates from Chatwoot's inbox 1, sends `ticket_resolved_he` through Chatwoot | `POST /subscriber/send-whatsapp-template-by-user-id` (`create_if_not_found`) |
| `send_payment_link` on a debt call | Finds or makes the Chatwoot contact and conversation, sends the link as the bot | `POST /subscriber/send-text` inside 24 hours; `payment_link_he` by template outside them |
| `store_media`, `add_request_detail` | Copies photos only from Chatwoot's host (`MEDIA_HOSTS`) | UChat's media host added to the list |

All three go behind one switch, so the move and its rollback are a setting,
not a deploy.

### The tests

`check_whatsapp_rules.py` runs the exact live code on Chatwoot-shaped
messages. Its cases and the replay need UChat-shaped ones, built from the
payload the dry run captures.

## Order of work

**0. Ready now (done 3 Nov).**
- The inventory above.
- Backups in `local/uchat-prep/` (not in git: they hold phone numbers):
  - all 8 Homies workflows (`n8n-2026-11-03/`);
  - all of Chatwoot account 2: settings with secrets blanked, 10 contacts, 9 conversations, 2,037 messages (`chatwoot-2026-11-03/`);
  - UChat's API spec.
- `scripts/uchat_api.py`, a read-only look at the workspace.

**1. Dry run on the owner's UChat workspace "clix", web chat only (about 1 day; free; no WhatsApp number).**
- The owner, in UChat's dashboard (its API cannot do these):
  - turn on the web chat widget;
  - turn on the Webhook integration with a capture address we give.
- We:
  - send one Hebrew message and one photo from the widget, and keep the payload;
  - try send-text, send-node, pause-bot / resume-bot, move-chat-to, assign-agent-group and labels on that one widget contact;
  - look at Hebrew right-to-left in Live Chat and the mobile app;
  - write the answers into [context.md](context.md), "Open questions".

**2. Build beside the live bot (8-11 days).**
- A copy of the bot workflow for UChat, the way the sandbox was copied on 26 Oct. The live bot stays on Chatwoot until step 4.
- The UChat versions of "Hand to a person" and the handback.
- The switch in the tool server, and the tests on UChat-shaped messages.

**3. The number and the seats (needs the client).**
- A paid UChat plan, and the staff as team members, each put in their group (`POST /team/update-agent-group-users/{id}` with `UCHAT_API_KEY_TEAM`). The four agent groups exist since 3 Nov.
- The number connected through UChat's **WhatsApp Cloud** (Facebook login).
  - In practice Homies' own number, which also needs the "office homies" Meta account.
  - Our Meta test number most likely cannot go through that screen (see context.md).

**4. Cutover (about an hour, then two or three days of watching).** Below.

## Cutover

**Connecting the number in UChat IS the cutover.** UChat connects through its
own Meta app, and Meta then delivers each message to every app on the account.
Whatever answers the number today, ManyChat on Homies' number or Chatwoot on
ours, keeps getting the messages, so two bots would answer. Every step happens
in one sitting.

1. **Before:**
   - both templates approved;
   - the UChat copy of the bot passes its tests on the widget;
   - staff are logged in to UChat.
2. **Connect the number** in UChat (WhatsApp Cloud).
3. **The same minute, switch the old path off:**
   - ManyChat disconnected (Homies' number), or Chatwoot's agent bot unlinked from inbox 1 (ours);
   - the UChat copy of the bot switched on.
4. **One "hi" from a tester.** It shows in UChat's Live Chat, the n8n run is green, and a row lands in Supabase `messages`.
5. **Flip the tool server's switch to UChat.** Then one ticket notice and one payment link.
6. **Watch:** `check_whatsapp_rules.py --watch` from the cutover minute, again the next morning.

## Rollback (minutes)

1. Switch the UChat copy of the bot off and the tool server's switch back to Chatwoot.
2. Disconnect the number in UChat.
3. Give the number back to what had it:
   - for ours, re-link Chatwoot's agent bot to inbox 1;
   - if our app was taken off the account, re-subscribe it and run Chatwoot's `Whatsapp::WebhookSetupService#register_callback` for inbox 1 in `rails runner` (the 2 Nov recipe, WORKLOG 2 Nov).
4. One "hi" proves it.

Chatwoot is not switched off at the move, so the rollback needs no rebuild.

## Data

| Store | At the move |
|---|---|
| Supabase | Unchanged. The dashboard's Conversations page keeps the whole history |
| Chatwoot | Stays running, read-only in practice: the archive, and the Voice inbox if that stays |
| UChat | Contacts appear as people write (or are created ahead with `POST /subscriber/create-many`). **Past messages do not import:** UChat's API has no call that writes them |
| Meta | The number and the templates stay on the WhatsApp account; UChat reads the templates with `POST /whatsapp-template/sync` |
| n8n | Unchanged, apart from the UChat copies |

## Running cost

- **UChat's own page, 3 Nov:**
  - Business is **$15 a month** (shown down from $29): 1 bot, 1,000 contacts, 5 members.
  - Extras: 1,000 contacts $5, a member $10, a bot $10, each a month.
  - Partner is $199 a month.
- **For the whole staff, at those prices:** about $105 a month with 10 seats, or about $195 with all 19 staff, both on the 10,000-contact tier. That is $15, plus $10 for each member over 5, plus $40 for contacts ($5 per 1,000 up to 5,000, then $20 per 5,000, on UChat's public pricing page). The 29 Sep estimate was $80-95 and $125-140, when a member was $5. (Corrected 3 Nov evening: the first version read $60 and $105, which do not follow from these prices.) The Hebrew comparison sheet works this out from its inputs (HANDOVER).
  - Contacts count everyone who has ever written. About 7,500 residents puts it on the 10,000 tier.
- **No AI key is needed in UChat,** because the bot stays on OpenRouter.
- **Inbound webhooks (500 a day per bot) are not used.** Replies go through the REST API, whose rate limit UChat does not publish.

## Acceptance (for the move itself)

1. A tester's "hi" gets the menu through UChat within 10 seconds, with a green n8n run and a Supabase `messages` row.
2. A fault report opens a ticket carrying the reporter's name, and a photo sent with it lands on the ticket.
3. A staff reply in UChat stops the bot in that chat, and the bot answers again after the pause.
4. A hand-over puts the chat in the right agent group, with its label, and staff can read the matter.
5. A ticket resolved on the dashboard sends `ticket_resolved_he` through UChat.
6. A debt call's payment link arrives on WhatsApp.
7. The gate is green on the UChat copy, and `--watch` after the cutover flags nothing new.
8. The rollback is rehearsed once before the cutover: the old path answers within 10 minutes.
