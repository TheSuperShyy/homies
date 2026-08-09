# 11 — WhatsApp — the client requirement

Given by the client on 8 Aug 2026 as **PRD item 3**. This is the source of truth
for what WhatsApp has to become. [feature.md](feature.md) describes what has been
built so far, which is a fraction of it — where the two disagree, this wins.

## Verbatim

> **3. Centralized WhatsApp System with AI Bot**
>
> **Current Situation:** Multiple WhatsApp numbers/interfaces are currently used,
> partially managed through ManageChat. This setup is disorganized and does not
> meet business needs.
>
> **Objective:** Centralize all WhatsApp activities under a single platform using
> a primary business line, department routing, user access controls, call
> logging, an AI bot, and company system data integration.
>
> **Required Capabilities:**
>
> - Central business WhatsApp number with employee seat management (scalable for
>   future growth)
> - Department routing (Collections, Operations, Management, Service)
> - Chat transfer between agents, department assignment, open/closed ticket
>   status tracking
> - Ability to toggle the AI bot on/off per conversation for seamless human
>   handover
> - Complete chat logs, automatic thread summaries, and topic tagging
> - Capability to send payment links, answer FAQs, open service tickets, check
>   ticket status, and check balance/debt status
>
> **Important Emphasis:** The bot must not feel robotic or frustrating ("thrown
> to a robot"). It must communicate in a calm, respectful, clear, and
> service-oriented tone that aligns with company standards.

## What this changes about the work

**The bot is not the system.** What exists today is a single-purpose ticket
opener hanging off a webhook: a message arrives, an agent decides, a request row
is written, a reference goes back. There is no inbox, no agents, no seats, no
departments and no way to switch the bot off for one conversation.

The requirement is a **shared agent inbox** in which the AI is one participant.
That is a different shape, and it is load-bearing: the per-conversation on/off
toggle and the human handover cannot be retrofitted onto a webhook that answers
every message by definition. Meta's Cloud API delivers to exactly one callback
URL, so whatever owns the inbox owns that URL, and n8n moves behind it.

## Where each capability stands

| Required | Status | Note |
|---|---|---|
| Central business number, employee seats | **not started** | Needs the inbox product chosen first. One number, many seats, is what Meta's Cloud API is for — the current design has no seat concept at all. |
| Department routing — Collections, Operations, Management, Service | **not started** | Four departments named for the first time here. Collections maps to the debt agent's world, Service to this bot's. |
| Chat transfer between agents, department assignment | **not started** | Inbox feature. |
| Open/closed ticket status tracking | **partial** | `requests.status` exists in Supabase with `open / in_progress / resolved / cancelled / needs_review` since migration `003`. Nothing surfaces it to a person. |
| Toggle AI on/off per conversation | **not started** | **The structural one.** Today the bot answers every message that reaches the webhook; there is no per-conversation state and nowhere to put it. |
| Complete chat logs | **partial and wrong shape** | The last 12 messages live in the n8n memory node, keyed on phone. That is context for the model, not a log: it is capped, it is not queryable, and it does not survive an n8n restore. |
| Automatic thread summaries, topic tagging | **not started** | Cheap to add once conversations are stored somewhere durable. |
| Send payment links | **exists elsewhere** | `send_payment_link` is one of the debt agent's eight tools and already writes to `payment_links`. Not attached to this bot. |
| Answer FAQs | **not started** | The prompt currently answers briefly if it knows and otherwise hands off. No source of answers. |
| Open service tickets | **built** | Working end to end, real reference numbers. One of six. |
| Check ticket status | **not started** | Data is in Supabase. Needs a read tool and the identity question answered — see below. |
| Check balance / debt status | **not started** | `charges` holds it. Same identity question, and a harder one: this is money. |
| Not robotic, calm and respectful | **in progress** | The 8 Aug prompt rewrite is aimed exactly here. Untested against a native speaker. |

## Two questions this raises that were not open before

**Who is asking?** Three of the six capabilities — ticket status, balance, debt —
disclose personal financial information. The bot currently identifies nobody: it
takes the phone off the WhatsApp envelope and files a ticket against it, which is
safe precisely because it only ever *writes*. Reading somebody's debt out to
whoever holds a handset is a different risk, and PRD §13 #1 (the verification
method) has been open since the first spec. It now blocks two capabilities
rather than none.

**Where does the data come from?** Ticket status and balance both live in OXS,
and OXS is read-only by client rule of the same day — which is fine, because
reading is all this needs. They are served from the Supabase copy, so their
freshness is the freshness of the import, and the bot should say so rather than
imply live figures.
