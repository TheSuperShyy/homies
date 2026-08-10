# Homies — Accounts & Credentials Checklist

What has to exist, who provides it, and what is still missing. **Status column
verified against the live `.env` on 2026-08-10** (variable names and whether
they are populated — values were never read or printed).

Secrets live in the n8n credential store or `.env` — never in code or chat
(PRD §13). See [.env.example](../../.env.example) for the exact variable names.

Legend: **DONE** = populated and in use · **MISSING** = still to obtain ·
**N/A** = retired from the architecture.

---

## The short answer: what is actually still outstanding

Almost everything is in place. Only four groups remain:

| # | What | Blocking |
|---|---|---|
| 1 | **Omnitelecom SIP** — 4 values | Outbound/inbound phone calls. Nothing dials today. |
| 2 | **Google service account + sheet ID** | The nightly OXS sheet bridge |
| 3 | **Monday token + board ID** | Staff task hand-off (client-provided) |
| 4 | **Meta business verification** *(account state, not a key)* | Caps WhatsApp at 250 conversations/day |

Everything below that is already done.

---

## 1. Telecom — Omnitelecom *(the main gap)*

Provider **decided**: Omnitelecom (omnitelecom.com / omnitelecom.co.il, Ramat
Gan, `*9163`). No self-service and no public API — ordering is a phone call or
the contact form.

**Order exactly two products.** `OmniDID` (the +972 number) and `SIP Trunk
Solutions`. On the Hebrew site: **מספר וירטואלי** and **קו SIP**. Skip Hosted
PBX, Cloud PBX, contact centre and IVR — that is a phone platform you would be
replacing, not something Vapi needs.

**The four values Vapi needs** — the number alone does not give these:

| Env var | What it is | Status |
|---|---|---|
| `SIP_GATEWAY_IP` | Gateway host — **IP, not FQDN** (Vapi 400s on hostnames) | **MISSING** |
| `SIP_USERNAME` | SIP auth user | **MISSING** |
| `SIP_PASSWORD` | SIP auth password | **MISSING** |
| `SIP_PHONE_NUMBER` | The DID in +972 E.164 | **MISSING** |

**Ask before paying — this decides whether it works at all:** does the trunk run
over the **public internet**, or does it require a dedicated line? A dedicated
line cannot reach Vapi.

**Also specify when ordering:**

- **Digest auth, not IP-based.** Vapi's SIP servers are shared; IP auth
  misroutes between customers.
- **Outbound caller ID presenting the DID** — the debt agent is outbound.
- **G.711 (PCMU/PCMA), not G.729.**
- **DTMF RFC 2833.**
- **≥10 concurrent channels** for the pilot.

**Omni must allow, on their side:**

- SIP signalling from `44.229.228.186` and `44.238.177.138` (Vapi US)
- RTP media on UDP `40000-60000` — **media source IPs vary per call.** Vapi
  publishes static IPs for *signalling only*. Carriers who whitelist signalling
  alone produce connected calls with no audio. This is the single most common
  failure and worth stating explicitly to them.

**Israeli DIDs need company documents — Homies' registration, not yours.**
That is the long pole (1–3 weeks KYC) and it is a client task.

*Confirmed empirically against the live Vapi account (4 Aug 2026), not from
docs:* `POST /credential {"provider":"byo-sip-trunk"}` → "gateways should not be
empty", and `POST /phone-number {"provider":"byo-phone-number"}` → "Credential
Not Found". Both shapes are accepted, so BYO SIP works on this account.

**Retired:** `TELNYX_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` are
present but empty — **N/A**, not needed. Rotate and retire the old Telnyx
account (see security items).

---

## 2. Meta / Facebook — WhatsApp chatbot *(credentials DONE)*

All Meta credentials are already obtained and populated. Nothing to order here.

| Env var | What it is | Status |
|---|---|---|
| `APP_ID` | Meta developer app ID | **DONE** |
| `APP_SECRET` | App secret — signs the webhook payload | **DONE** |
| `WHATSAPP_WABA_ID` | WhatsApp Business Account ID | **DONE** |
| `WHATSAPP_PHONE_NUMBER_ID` | Phone Number ID (not the number itself) | **DONE** |
| `WHATSAPP_ACCESS_TOKEN` | Access token | **DONE** |
| `SYSTEM_USER_ACCESS_TOKEN` | Permanent system-user token — not the 24h dashboard token | **DONE** |
| `WHATSAPP_TOKEN` | Third token, longest of the three | **DONE** |
| `WHATSAPP_WEBHOOK_VERIFY_TOKEN` | Self-chosen secret, shared with n8n | **DONE** |
| `WHATSAPP_TEST_RECIPIENT` | Number the self-check messages | **DONE** |
| `N8N_WHATSAPP_CRED_ID` | The credential's ID inside n8n | **DONE** |

**Two things still to confirm — neither is a key:**

- **Business verification status.** This is account state, not an env var, so it
  cannot be checked from the repo. Unverified caps the WABA at **250
  conversations/day**, which blocks the *pilot*, not the dev work. Needs Homies'
  legal docs (company registration + matching domain). If not yet started, this
  is critical path.
- **Three overlapping tokens.** `WHATSAPP_ACCESS_TOKEN` (198 chars),
  `SYSTEM_USER_ACCESS_TOKEN` (198) and `WHATSAPP_TOKEN` (289) all coexist. Only
  the permanent system-user token should be doing real work; the others are
  likely leftovers from setup and are a rotation hazard — a temp token expiring
  looks exactly like an outage. Worth reducing to one.

**The account must be Homies-controlled, not personal** — this is the
Vapi-on-a-personal-Gmail problem, and the point was to avoid repeating it here.

**Verify the whole chain works** (posts a real signed message and checks the
database row, then cleans up):

```
python scripts/check_whatsapp.py
```

Use that rather than eyeballing config. Every serious fault this bot has had was
silent — a webhook wired to the wrong output, a WABA subscribed to Meta's own
dev-tools app — and each one *looked* fine in the dashboard.

---

## 3. Vapi (voice agent) — DONE, one warning

| Env var | Status |
|---|---|
| `VAPI_PRIVATE_KEY` | **DONE** |
| `VAPI_ASSISTANT_ID` | **DONE** |
| `VAPI_PRIVATE_KEY_ACCOUNT2`, `VAPI_PRIVATE_KEY_OLD` | **DONE** (migration leftovers) |

- ⚠️ The current key was **exposed in plaintext during scoping and is not
  confirmed rotated** — rotate before production.
- **Card on file + auto-reload.** An empty card with auto-reload off means calls
  die mid-sentence when credits hit zero.
- Account ownership (personal Gmail vs Homies) is still an open handover
  question. See [Vapi account notes](Homies-Vapi-Account-Notes.md).

## 4. Supabase — DONE

`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`,
`SUPABASE_DB_URL`, `SUPABASE_DB_PASSWORD`, `SUPABASE_ACCESS_TOKEN` — all
**DONE**. Project is live and holds the 12 real OXS residents.
Service-role key is server-side only, never shipped to a browser.

## 5. n8n — DONE

`N8N_BASE_URL`, `N8N_SHARED_BASE_URL`, `N8N_SHARED_API_KEY`, `N8N_API_KEY`,
`N8N_WEBHOOK_SECRET`, and the credential IDs (`N8N_CRYPTO_CRED_ID`,
`N8N_OPENROUTER_CRED_ID`, `N8N_WHATSAPP_CRED_ID`, `N8N_SUPABASE_CRED_ID`,
`N8N_TOOLSECRET_CRED_ID`) — all **DONE**. `N8N_MCP_TOKEN` is empty but only
needed if n8n is exposed as an MCP server.

**Back up the n8n encryption key.** Losing it loses every credential stored in
n8n — this is not recoverable and is not in `.env`.

## 6. OXS — keys DONE, endpoints unresolved

`OXS_KEY_GENERAL`, `OXS_KEY_DEBTS`, `OXS_KEY_REQUESTS` — all **DONE** (70-char
`oxs_k_` tokens). API host verified as `api.oxs.co.il`. See
[HANDOVER.md](../../HANDOVER.md) — phones are the open question; run
`python scripts/oxs_probe.py`.

Open: re-issue `OXS_KEY_REQUESTS` as Read-Only if it was created Full Control.

## 7. OpenRouter — DONE

`OPENROUTER_API_KEY`, `OPENROUTER_API_KEY_2` — **DONE**. Covers the
WhatsApp/team chatbot only; the voice agent's LLM is billed through Vapi at
pass-through, so there is no separate key on the voice path.

## 8. Cartesia (TTS) — partially done

`CARTESIA_API_KEY` **DONE**, `CARTESIA_MODEL` **DONE**,
`CARTESIA_VOICE_ID` **EMPTY** — needed only if using a cloned/custom voice.
ElevenLabs vars (`ELEVENLABS_VOICE_ID`, `ELEVENLABS_MODEL`, `VOICE_PROFILE`)
are **MISSING** and only matter if that path is revived.

## 9. Google (Sheets bridge — nightly OXS export) — MISSING

| Env var | Status |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_KEY_FILE` | **MISSING** — service-account JSON key |
| `OXS_EXPORT_SHEET_ID` | **MISSING** |

Needs a Google account/Workspace, a Cloud project with the Sheets API enabled,
and **the sheet shared with the service-account email** — easy to forget, and
reads then fail silently as 403.

## 10. Monday — MISSING (client-provided)

| Env var | Status |
|---|---|
| `MONDAY_API_TOKEN` | **MISSING** — client-provided, PRD §16 #9 |
| `MONDAY_BOARD_ID` | **MISSING** — depends where staff actually work (§16 #7) |

## 11. Vercel + GitHub (CRM dashboard) — DONE

`VERCEL_TOKEN`, `VERCEL_API` — **DONE**. Runs on the free `*.vercel.app` URL
through build and pilot.

## 12. Hostinger VPS (n8n + Chatwoot)

Not represented in `.env` (server-side). Still needed: Hostinger account +
root/SSH key, Chatwoot super-admin login, Chatwoot API access token, per-department
agent accounts, and SMTP credentials for Chatwoot notifications.

## 13. Domain

| Need | When | Why |
|---|---|---|
| Subdomains for n8n + Chatwoot | **During the build** | Meta's webhook requires a public HTTPS callback; Chatwoot needs a stable inbox address |
| Custom domain for the CRM dashboard | **At handover** | The CRM runs on `*.vercel.app` until Homies takes over |

Decide domain ownership (CLIX vs Homies) alongside the Vapi account ownership
question — same conversation.

---

## Outstanding security items

- ⚠️ Three keys exposed in plaintext during scoping, **not confirmed rotated**:
  Vapi, Telnyx, Retell (PRD §13).
- Retell and Telnyx are otherwise unused in the current architecture — rotate
  and **retire** both accounts.
- Reduce the three overlapping WhatsApp tokens to the one permanent system-user
  token.
- Back up the n8n encryption key somewhere that is not the VPS.
