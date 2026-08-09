# 13 — Dashboard

Read-only view of tickets, conversations and calls, over Supabase. Next.js on
Vercel, staff sign in with Supabase Auth. Asked for on 8 Aug — *"a simple
dashboard for the tickets, calls and concerns, the data and call transcription"*
— with everything stored in Supabase.

Code in [dashboard/](../../../dashboard/).

## Most of this job was not the dashboard

Three of the four things it shows were not being stored:

| | Before | After |
|---|---|---|
| Tickets | in Supabase, working | unchanged |
| Chat transcripts | **nowhere** — n8n's memory node, capped at 30, not queryable, lost on restore | `messages`, one row per message, both sides |
| Calls | schema ready, table empty | unchanged — end-of-call reports were wired 8 Aug and no call has been placed since |
| Channel of a chat | filed as `outbound voice call` | `whatsapp` / `inbound` |

That last one is the sort of bug a dashboard turns into a lie. Every WhatsApp
interaction written that morning was recorded as an outbound voice call, because
`interactionId()` hardcoded both fields from when Vapi was the only caller — the
same shape as `opened_via`. A "calls" page would have reported calls that were
never placed.

## The leak this opened, and closed

`messages` shipped in migration 008 **without RLS enabled**. Every other table
has it on, so the anon key reads nothing from them; `messages` returned real
rows. The anon key is public by design — it ships in the browser bundle — so
anyone with it and the project URL could read every resident's conversation.

It was live for about an hour, over four test conversations and no real
resident. Luck, not design. Migration 009 enables RLS, adds `staff_read` for
`authenticated` only (never `public`, which includes `anon`), sets
`security_invoker` on the views — a view otherwise reads with its owner's
rights and hands rows out regardless of who asked, which is exactly what
`v_conversations` was doing — and ends with a check that **fails the migration**
if any table in `public` lacks RLS. 008 got through because nothing was looking.

## Read-only, deliberately

There is no policy that lets a signed-in user write. Verified: an insert as a
staff session returns `42501`. Writes come from the Edge Function and n8n with
the service role key, which bypasses RLS by design.

Staff already live in OXS and Monday. A third tool that demands daily attention
is the classic adoption failure, so this one answers questions and does not ask
for work.

## Pages

- **Overview** — open tickets, urgent open, all-time, conversations, calls, and
  the last 7 days
- **Tickets** — filterable by status; the filter is in the URL so a view can be
  sent to a colleague
- **Conversations** — one row per thread, resident name where the phone matches,
  the raw number where it does not (an unmatched number means somebody outside
  the imported list is writing in, which is a signal rather than a blank)
- **Conversation** — the thread as a chat, plus that resident's recent tickets
- **Calls** — summary, outcome, length, and latency coloured against the 800ms
  target per call rather than averaged, because an average hides the bad ones
- **Call** — transcript, recording, and the tool calls, which are what the agent
  *did* as opposed to what it said it did

Hebrew is handled with `dir="auto"` per element rather than a right-to-left
layout: Hebrew flows correctly while a reference like `HM-2026-1013` inside the
same sentence stays left-to-right. A full RTL chrome is a bigger job and belongs
with the Hebrew review of the whole product.

## Deploying

```
vercel --cwd dashboard
```

Two environment variables, and only two:

```
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY
```

**Never the service role key.** It bypasses every policy above; in a browser
bundle it hands a stranger 12 real residents' names, phones and debts.

Accounts are created in **Supabase → Authentication → Users**. There is no
sign-up form, for the same reason `ENABLE_ACCOUNT_SIGNUP` is off in Chatwoot.

## Known gaps

- **No department scoping.** PRD §10 wants it; there is no staff table to scope
  against, and a policy that looks like access control while enforcing nothing
  is worse than an honest one.
- **"Concerns" is interpreted as urgency and handovers**, surfaced through the
  ticket list and the conversation view. If it means something else — a
  complaints category, or escalations as their own object — it needs its own
  type and its own page.
- **Calls will stay empty** until a call is placed. Vapi has $7.18 of credit.
- **Chat logs come from n8n today.** When Chatwoot takes the number, its webhook
  writes the same table with `source = 'chatwoot'`; the dashboard does not
  change. That column exists so a gap in the history can be told apart from a
  quiet period.
