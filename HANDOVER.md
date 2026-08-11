# HANDOVER — Homies, everything you need to take over

**Current as of 2026-08-11.** If you have just been told "read the handover",
this file plus `CONTEXT.md` is the whole briefing. Read both, then start
working. Go to `docs/WORKLOG.md` only when you need to know *why* something
was decided — it is the chronology with full reasoning, newest first.

Rewrite this file after every piece of work. Present tense only, never
appended to.

---

## The project in a paragraph

Homies is an Israeli building-management company — ~193 buildings, ~10,000
apartments, ~19 staff — getting a Hebrew AI voice agent plus chatbots. Two
voice agents (inbound intake, outbound debt collection) and a WhatsApp bot,
all writing to one database, with a dashboard over the top. The client's
existing management system is **OXS**, which we read from and never write to.
The user is the builder; Homies is the client.

---

## The system, one page

**Two front doors, and no third.** A resident either opens `web/index.html`
and starts a **web call** (there is no phone number — nothing dials, nothing
can be dialled), or sends a **WhatsApp message** to one Meta test number.

**The runtime.** Web calls hit **Vapi**, which runs four assistants — Hebrew
inbound + debt, and English twins used for comparison. Hebrew stack is
ElevenLabs Scribe v2 for speech-to-text and Cartesia Sonic 3 for the voice,
attached with our own Cartesia key so Vapi bills ₪0 for TTS. WhatsApp messages
hit **n8n** at `/webhook/homies-whatsapp`, which verifies the Meta signature,
dedupes on `wamid`, detects language, and runs an AI Agent on OpenRouter with
a 30-turn memory keyed by phone.

**One writer, reached three ways.** Every write goes through the Supabase Edge
Function `debt-tools` (12 handlers, `--no-verify-jwt`, authenticated by
`TOOL_SECRET`). Voice tool calls route via n8n `/webhook/homies-debt-tools`;
the end-of-call report and the two read-only tools (`get_balance`,
`get_request_status`) go straight to the Edge Function. Every write opens an
`interactions` stub first, so nothing is orphaned.

**The store.** Supabase Postgres (Tokyo region), the only store of record.
Tables: `residents`, `charges`, `interactions`, `requests`, `messages`,
`call_outcomes`, `payment_links`, `promises_to_pay`, `payment_disputes`,
`payment_tickets`. Views: `v_debt_call_queue` (the eligibility guard —
unpaid, handed over, not do-not-call, attempts < 4), `v_conversations`,
`v_pending_payment_tickets`.

**The dashboard.** Next.js 14 on Vercel at `homies-dashboard.vercel.app`.
Pages: overview, tickets, debts, conversations, calls, call detail. Anon key,
no login since 9 Aug, read-only except `requests.status`. Ten rows a page
everywhere, via `dashboard/components/pager.tsx`. Debts is one row per
**apartment**, with `?by=owner` for one row per person and a marker on
apartment rows whose owner holds another flat. It filters by month —
`/debts?month=2026-07`, tabs derived from the data, `?month=all` for the
lifetime view — and opens on the newest **completed** month, because the
current month is never chased and the newest month carrying a charge is
defect 1 below.

**The 12 tools:** `open_request`, `save_partial_request`, `send_payment_link`,
`log_promise_to_pay`, `request_standing_order`, `log_disputed_payment`,
`flag_not_handed_over`, `transfer_to_human`, `log_call_outcome`,
`get_balance` (read), `get_request_status` (read), and `open_payment_ticket`
(retired 4 Aug, not offered). `transfer_to_human` **connects nobody** — it
writes the call to the office. Never say anyone is being put through.

---

## What works, and what does not exist

| Works today | |
|---|---|
| Outbound debt collection, voice (Hebrew) | web calls only |
| Inbound intake → ticket, voice (Hebrew) | web calls only |
| Balance check | voice + WhatsApp |
| WhatsApp bot: open a ticket, check a ticket | one Meta test number |
| Dashboard | live, ten rows a page |
| OXS → Supabase import | works, run by hand |

**Does not exist:**

- **A real phone number.** No `phoneNumberId` on the Vapi account. Needs the
  four Omnitelecom values — gateway host/IP, SIP username, SIP password, DID
  in +972 E.164 — and Homies' company registration documents, which are the
  long pole. Ask whether the trunk runs over the public internet before
  paying; a dedicated line cannot reach Vapi.
- **Payment link delivery.** `send_payment_link` writes a row and stops. OXS
  exposes no payment-link endpoint, so the link still comes from OXS itself.
- **Chatwoot in the message path.** It runs and owns the number; it is not
  wired to the bot.
- **Any scheduler.** Every import and sync is run by hand.
- **A campaign runner.** Nothing has ever iterated `v_debt_call_queue`.
  **Read this before writing one:** the view is one row per charge, which since
  11 Aug means one row per *apartment per month*. An owner with two flats owing
  four months each is **eight rows, and a naive runner places eight calls**.
  Collapsing is the runner's job — the view's contract is only that a row
  carries everything one call needs. How a call should be grouped (per
  resident, per apartment, per charge) is **deliberately undecided as of
  11 Aug**; see "Deferred by decision" below.

---

## The data, as it stands

- **7,391 residents** — real names, real E.164 mobiles, across 173 active
  buildings. All carry `handed_over = false`, so **`v_debt_call_queue` is
  empty and nothing can dial**. A person must flip that flag before any
  campaign. This is the safety interlock; do not remove it casually.
- **122 apartments owing ₪101,519.70, held by 120 residents** — one charge per
  apartment per unpaid month across 2026-01 → 2026-07. July is 108 apartments
  and 106 people, tapering to 4 owing January. Apartments and residents are
  different numbers and the dashboard counts both.
- Plus one legacy row, ₪1,500 — a 2022 balance, and the only thing OXS's
  `/debts` endpoint reports for the entire company.
- Zero demo or synthetic rows; both were purged on 10 Aug. Every charge carries
  `source = 'oxs'` — until 11 Aug they all said `'seed'`, which is the flag
  every destructive query filters on.

### Three known defects

1. **The 2022 debt is stamped `2026-08`** because the sync had no month to
   use. The agent would name August, which that resident would dispute. The
   dashboard routes around it — Debts opens on the newest *completed* month —
   but the row itself is still wrong and the voice agent still reads it.
2. ~~People owning several apartments collapse into one row.~~ **Fixed 11 Aug**
   by migration 012: the apartment lives on the charge, unique on
   `(resident_id, period, unit)`. Recovered ₪6,665.40 across two owners.
   `residents.unit` still exists but names only one of an owner's flats and is
   **not authoritative for debt** — read `charges.unit`.
3. **18 apartments have no phone in OXS** and were skipped. Not callable.

---

## OXS — the part that took longest to learn

**The API works.** `https://api.oxs.co.il/api/external/v1`, header
`x-api-key`, envelope `{status, data}`. Three module-scoped keys in `.env`
(`OXS_KEY_GENERAL`, `OXS_KEY_DEBTS`, `OXS_KEY_REQUESTS`), all live; external
API access was already enabled, so no support ticket is needed. Reference is
`OXS_External_API_v1.pdf` in the repo root — gitignored, it is OXS's document.
Rate limits are **60/min and 1,000/hr per key**, not shared across keys.

**`/debts` does not report who is behind.** It returns one record
company-wide — a 2022 balance belonging to an owner marked inactive, with
collection notes attached. It answers "who carries old debt". Proven by
counter-example: one building shows zero debts via `/debts` while its own
payment records show apartments that have not paid since June.

**So arrears are computed, not fetched.** `/buildings/:id/payments` carries
`apartmentId`, `totalAmount`, and `monthsPaid[{year, month, amount, isKeva}]`.
Arrears = months of the year that have ended with nothing paid against them,
at the apartment's own monthly rate, never a guessed one. The current month is
never chased.

**The correction that makes it honest:** where four or more flagged apartments
in a building miss the same *leading run* of months (01, 01–02, 01–05), Homies
took that building on mid-year and the run is not debt. Thresholds are
asymmetric on purpose — 0.6 for leading runs, 0.8 otherwise — because a whole
building going unpaid from January and resuming in unison does not happen,
while a building being taken on in May happens constantly. Raw sweep flagged
610 apartments and ₪962,405; after correction, 139 and ₪108,770.

`docs/reference/arrears-2026.json` holds the full list and is **gitignored —
740 real mobile numbers, and this repo is public.**

---

## Credentials — names only, values live in `.env`

| System | Env vars |
|---|---|
| Vapi | `VAPI_PRIVATE_KEY` (+ `_OLD`, `_ACCOUNT2`) |
| Supabase | `SUPABASE_URL`, `_ANON_KEY`, `_SERVICE_ROLE_KEY`, `_DB_URL`, `_DB_PASSWORD` |
| n8n | `N8N_BASE_URL`, `N8N_API_KEY`, `N8N_WEBHOOK_SECRET` |
| OXS | `OXS_KEY_GENERAL`, `OXS_KEY_DEBTS`, `OXS_KEY_REQUESTS` |
| Cartesia | `CARTESIA_API_KEY` (attached inside Vapi as a credential) |
| OpenRouter | `OPENROUTER_API_KEY`, `_2` |
| Meta/WhatsApp | `APP_ID`, `APP_SECRET`, `WHATSAPP_TOKEN`, `WHATSAPP_WABA_ID`, `WHATSAPP_PHONE_NUMBER_ID` |
| Vercel | `VERCEL_TOKEN` |
| Internal | `TOOL_SECRET` (Vapi → n8n → Edge Function) |

Empty and expected to stay empty: Twilio, Telnyx (no phone numbers yet).
Missing if wanted: `ELEVENLABS_API_KEY` — the custom voice
`WKRPx9n3dUHKk1SZhnwv` errors in Vapi because only a Cartesia credential
exists. Never print a value, never commit one, never paste one into chat.

---

## Open questions for the client

1. **Why does OXS report one debtor across 193 buildings?** Either their
   finance module tracks only legacy carried debt, or Homies records arrears
   somewhere the API does not aggregate. Until answered, the computed arrears
   list is ours, not OXS-blessed.
2. **Payment proof by WhatsApp or email?** The dispute path sends residents to
   `{{verification_email}}`; Israelis default to WhatsApp screenshots. An
   office-intake decision, not a prompt change.
3. **Meta/WhatsApp ownership** — if the number is to be Homies', they must
   grant Business Manager access rather than hand over a login.
4. **Chatwoot seats** — how many users, names and emails, which inboxes.

## Deferred by decision — do not restart these unasked

**The voice agent is frozen as of 11 Aug.** Not blocked, chosen. Do not edit the
prompt, the queue grouping, or the assistants.

Two consequences to state plainly rather than quietly work around:

1. **`debt-tools` in the repo is ahead of what is deployed.** `get_balance`
   gained a per-apartment answer and the ability to find a caller through their
   second flat; neither is live. On a call today, the two multi-apartment
   owners get one combined balance, and their second apartment cannot be found
   by building+apartment. No write tool changed, so nothing else waits on it.
   **Deploying it is a decision, not a chore.**
2. **How a call is grouped is undecided.** One call per resident (everything
   they owe), per apartment, or per charge as today. It is not only a queue
   change: `{{month}}` and `{{amount}}` are single values and the prompt
   refuses a call without them, and `log_promise_to_pay`, `send_payment_link`
   and `log_disputed_payment` each write against one `charge_id`. A call
   covering eight charges has nowhere to record a promise against eight. The
   tool layer is the real work.

Nothing is urgent: no phone number exists, all 7,391 residents are
`handed_over = false`, and the queue returns 0 rows.

## Next moves, in order

1. Fix the remaining data defect (the 2022 debt stamped `2026-08`).
2. Schedule the sync — `oxs_debt_sync.py` nightly, plus a pre-flight debt
   check immediately before any call, so nobody is chased for something they
   paid yesterday.
3. Order the Omnitelecom line; company documents are the long pole.
4. Wire Chatwoot into the message path.

## Pending on other people

- `OXS_KEY_REQUESTS` to be re-issued Read-Only on the OXS side.
- ElevenLabs key in Vapi, if that voice is wanted.
- `scripts/vapi_tools.py` — add `get_request_status` and `get_balance` to
  `INTAKE_TOOLS` before anyone runs a full inbound sync, or the sync will
  strip them from the live assistant.
