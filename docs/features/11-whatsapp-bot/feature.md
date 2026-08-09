# 11 — WhatsApp bot

**Estimate:** 3d
**Depends on:** the live n8n tool webhook (`homies-debt-tools`), a Meta developer app
**Status:** built, not deployed

## Purpose

The second front door. Residents already message Homies on WhatsApp — it is the
most fragmented channel the company has, and the one the client called out first
in discovery. This puts the same brain behind it that answers the phone: one
resident, one set of tools, two ways in.

It is not a new system. Every tool this bot calls already exists and already
works, because the voice agents call them. What is new is the channel adapter
and the fact that the conversation is written rather than spoken.

## Scope of this slice

**Inbound support only, in Hebrew, on the Meta test number.** Three flows:

1. **Open a request** — a resident describes a problem, the bot captures type,
   description, building, unit and urgency, and reads back a real reference.
2. **Check an existing request** — a resident quotes a reference in any form
   (or gives building + apartment) and gets the live status back. Read-only,
   straight at the Edge Function — the same `get_request_status` the voice
   agents call, added 9 Aug.
3. **Hand over** — anything outside those flows goes to a person.

Deliberately not in this slice: the debt/payment flows, outbound messages,
Chatwoot, the team inbox, and any flow that needs identity verification. Those
are named in [context.md](context.md) with the reason.

## Behaviour

**Meta must get a 200 within seconds or it retries the webhook.** A retry is a
second copy of the same message, and a second copy is a second reply. So the
workflow answers Meta before it does any work at all — the same shape the tool
webhook already uses, and for the same reason.

```
Webhook -> Sort (Code) -> Respond to Meta
                      \-> Only if there is a message (If) -> Brain (Code) -> Send
```

**Duplicate suppression is by message id, not by content.** Meta's `id` is
stable across retries. Two identical messages a resident genuinely sent twice
have different ids and both get answered; one message delivered twice has one id
and gets answered once.

**The GET and the POST are the same webhook.** Meta verifies a callback URL by
sending a `GET` with `hub.mode`, `hub.verify_token` and `hub.challenge`, and
expects the challenge echoed back as **plain text** — not JSON. Getting this
wrong is the most common reason a Cloud API webhook will not save.

**Conversation state lives in n8n's workflow static data**, keyed by phone
number, capped at the last 12 turns and expiring after 24 hours. The 24 hours is
not arbitrary: it is exactly the window in which WhatsApp lets a business send a
free-form message, so a session that has aged out is a session the bot could not
have replied to anyway.

**Only the resident's text goes to the model.** Media, location pins, reactions
and buttons are acknowledged with the did-not-understand line and not passed on.
A voice note is the interesting case and is out of this slice.

## The model

`anthropic/claude-opus-5` **through OpenRouter**, via a plain HTTPS call from the
Brain node — no SDK, because an n8n Code node has no package installer. Same
price as the direct API ($5 / $25 per million tokens), verified against
`openrouter.ai/api/v1/models` rather than assumed.

OpenRouter speaks the OpenAI chat-completions shape, so the tools are declared
once in Anthropic's shape and converted on the way out. Two consequences that
bite if you forget them: tool arguments arrive as a **JSON string**, not an
object, and every tool call must be answered by its own `role: "tool"` message
carrying the matching `tool_call_id` or the next request is rejected.

**Thinking stays on, at `effort: "low"`.** This is the one setting worth arguing
about, so the reasoning is here rather than in a comment:

- Thinking is **on by default** on this model, and `max_tokens` caps thinking and
  the reply *together*. A tight `max_tokens` truncates the reply mid-sentence.
- Turning thinking off is the obvious latency fix and is **wrong here**. With
  thinking disabled, the model occasionally writes a tool call into its visible
  text instead of emitting a structured call. The turn completes normally, the
  reply looks fine, and **the tool never runs** — no error, nothing to catch. For
  a bot whose entire job is calling `open_request`, that is a silently lost
  ticket.
- `effort: "low"` gets most of the latency and cost back without that failure
  mode.

**The system prompt is cached.** One `cache_control` breakpoint on the last
system block; cached reads cost about a tenth of a normal input token. The prompt
clears the 512-token minimum comfortably. The volatile part of every request —
the conversation so far — sits after the breakpoint, where it belongs.

**The error object is checked before the reply is read.** OpenRouter returns a
bad model slug, an exhausted balance and an upstream refusal all the same way —
HTTP 200 with an `error` object and no `choices`. Code that reads `choices[0]`
unconditionally throws on every one of them.

## Interface

No new tool. The Brain calls the existing webhook at `/webhook/homies-debt-tools`
with the same envelope the voice agents send:

```json
{ "message": { "call": { "id": "wa:<phone>:<message_id>",
                         "assistantOverrides": { "variableValues": { "phone": "…" } } },
               "toolCalls": [ { "id": "…", "function": { "name": "open_request",
                                                          "arguments": { } } } ] } }
```

The chat session impersonates a call. That is deliberate: the alternative is a
second copy of the writer, the secret and the row shape, which is exactly what
[scripts/n8n_deploy.py](../../../scripts/n8n_deploy.py) argues against in its own
docstring. The session id is prefixed `wa:` so a row's origin is readable at a
glance in the sheet.

Tools offered to the model in this slice:

| Tool | Purpose |
|---|---|
| `open_request` | Create a maintenance/service ticket. Returns the real reference. |
| `transfer_to_human` | Hand the thread to a person. |

## Data

Writes rows through the existing writer — `call_requests` and `call_outcomes` —
so a WhatsApp ticket lands in the same tab a phone ticket does. Nothing new in
the sheet, no new columns.

Reads nothing. Identity is the phone number the message arrived from, and it is
never taken from the message body.

## Acceptance

1. Meta's callback verification succeeds — the GET returns the challenge as plain
   text, and the webhook saves in the Meta app.
2. A Hebrew message describing a leak produces a `call_requests` row with the
   right type and description, and the reference the resident is shown matches
   the one in the sheet.
3. The same message delivered twice by Meta produces **one** reply and **one**
   row.
4. Asking for a person produces a `transferred` row and a handover line.
5. A photo with no text produces the did-not-understand line and no row.
6. Two residents messaging at once do not see each other's context.
7. The webhook returns 200 in under a second, measured — before the model has
   been called.
8. Breaking the OpenRouter key does not stop the webhook returning 200 to Meta.
   **Verified in a different form on 8 Aug:** an out-of-credit key returns 402,
   the Brain catches the throw, and the resident gets the handover line rather
   than silence.

## Not in this slice

Media and voice notes; the payment and debt flows; identity verification;
outbound and template messages; Chatwoot and the team inbox; the production
number. Reasons in [context.md](context.md).
