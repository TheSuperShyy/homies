# Moving the WhatsApp line and the staff inbox to UChat

**Estimate:** 13-19d (one developer), plus 1d for the dry run that can happen first
**Depends on:** 11-whatsapp-bot, 12-chatwoot, 16-human-handover; a WhatsApp number UChat can connect (in practice Homies' own)
**Status:** prepared 3 Nov 2026, not started. Nothing moves until the owner says so.

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
- A paid UChat plan, the staff as team members, and the four agent groups.
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

These are 29 Sep prices, not checked again:
- **UChat Business:** about $80-95 a month with 10 seats, or $125-140 with all 19 staff.
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
