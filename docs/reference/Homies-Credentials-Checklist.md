# Homies — Accounts & Credentials Checklist

What has to exist, who provides it, and when it's needed. Built from
[PRD v2](../prd/Homies-PRD-v2.md) §9 and the decisions of 3 August 2026:
telephony provider **undecided (generic SIP)**, WhatsApp number **provided by
Homies**, Meta presence **starting from zero**, chatbot LLM via **OpenRouter**.

Secrets live in the n8n credential store or `.env` — never in code or chat
(PRD §13). See [.env.example](../../.env.example) for the exact variable names.

---

## Critical path — start these two immediately

The only clocks that cannot be compressed. Everything else on this page is an
afternoon each.

1. **Meta business verification** — needs Homies' legal docs (company
   registration, matching domain). Unverified caps WhatsApp at 250
   conversations/day, which blocks the pilot, not the dev work.
2. **Israeli DID KYC** — 1–3 weeks elapsed at any provider. A number already
   sitting in someone's account has served that time (see
   [Vapi account notes](Homies-Vapi-Account-Notes.md)).

---

## 1. Meta / WhatsApp Cloud API *(from zero)*

| Item | Notes |
|---|---|
| Facebook account (BM admin) | Homies-controlled, **not personal** — the Vapi-on-personal-Gmail problem, avoided this time |
| Meta Business Manager | Create, then start **business verification** (critical path) |
| Meta developer app | With the WhatsApp product added |
| WABA ID + Phone Number ID | Created when the number is registered |
| Dedicated WhatsApp number | **Homies provides.** Must never have been on the WhatsApp app (or removed 30+ days). Only needs to receive one verification SMS/call |
| Permanent system-user access token | Not the 24-hour temp token from the app dashboard |
| Webhook verify token | Self-chosen secret, shared with n8n/Chatwoot |

## 2. Vapi (voice agent)

| Item | Notes |
|---|---|
| Account login | Currently a personal Gmail — ownership decision open |
| `VAPI_PRIVATE_KEY` | ⚠️ Current key compromised — **rotate before production** |
| Assistant IDs | In `.env.example` |
| Card on file + auto-reload | Empty card + auto-reload off = calls die mid-sentence at zero credits |

## 3. Telephony — virtual number *(provider undecided, kept generic)*

| Item | Notes |
|---|---|
| Provider account | Any ITSP/DID vendor that exposes SIP termination |
| +972 DID (E.164) | **KYC docs required — critical path** |
| SIP gateway IP | IP, not FQDN — Vapi returns 400 on hostnames |
| SIP username + password | Becomes a Vapi `byo-sip-trunk` credential; provider forwards inbound to `{number}@<credential_id>.sip.vapi.ai` |
| Port / outbound proxy | If the provider specifies one (usually 5060) |

If the number ends up in a Twilio-style account instead, this collapses to
Account SID + Auth Token and a dashboard import.

## 4. Hostinger — VPS (n8n + Chatwoot)

| Item | Notes |
|---|---|
| Hostinger account + VPS root/SSH key | |
| Domain + Cloudflare account | See **§11 Domain** for what's needed when |
| n8n admin login | |
| n8n **encryption key** | **Back it up** — losing it loses every credential stored in n8n |
| `N8N_WEBHOOK_SECRET` | Shared with Vapi tool calls |
| Chatwoot super-admin login | |
| Chatwoot API access token | n8n uses it for bot on/off per conversation |
| Chatwoot agent accounts | Per department (PRD §4) |
| SMTP credentials | Chatwoot email notifications |

## 5. Supabase

| Item | Notes |
|---|---|
| Org + project | Not created yet |
| `SUPABASE_URL` | |
| Anon key | Browser-safe |
| Service-role key | Server-side only, never shipped to a browser |
| Database password | |

## 6. OpenRouter (chatbot brain in n8n)

| Item | Notes |
|---|---|
| `OPENROUTER_API_KEY` | Covers the WhatsApp/team chatbot only |
| Model choice | Open — needs a Hebrew quality check |

The **voice** agent's LLM is billed through Vapi at pass-through — no separate
key on the voice path.

## 7. Google (Sheets bridge — nightly OXS export)

| Item | Notes |
|---|---|
| Google account / Workspace | |
| Cloud project + Sheets API enabled | |
| Service-account JSON key | n8n reads the sheet as this identity |
| Sheet shared with the service-account email | Easy to forget; reads fail silently as 403 |

## 8. Monday

| Item | Notes |
|---|---|
| API token | **Client-provided** — PRD open item §16 #9 |
| Target board ID | Same open item — depends on where staff actually work (§16 #7) |

## 9. OXS

**No system credentials in release 1** — v2 removed all RPA. Needed instead:

- Sample export file + agreed nightly delivery mechanism (PRD §16 #3)
- OXS Fintech confirmation on how payment links arrive
- (Optional) a read-only staff login for manual reference — staff-owned, not a
  system credential

## 10. Vercel + GitHub (CRM)

| Item | Notes |
|---|---|
| GitHub org/repo | Code home |
| Vercel account + project | Linked to the repo; env vars set in Vercel |

## 11. Domain

Two different needs, two different clocks:

| Need | When | Why |
|---|---|---|
| Subdomains for n8n + Chatwoot (e.g. `n8n.…`, `inbox.…`) | **During the build** (weeks 3–4) | Meta's webhook requires a public HTTPS callback URL; Chatwoot needs a stable inbox address |
| Custom domain for the CRM dashboard | **After the project**, at handover | The CRM runs on the free `*.vercel.app` URL through build and pilot; the branded domain is attached when Homies takes over |

Decide domain ownership (CLIX vs Homies) at the same time as the Vapi account
ownership question — same handover conversation.

---

## Outstanding security items

- ⚠️ Three keys exposed in plaintext during scoping, **not confirmed rotated**:
  Vapi, Telnyx, Retell (PRD §13). Rotate before any goes near production.
- The Retell and Telnyx accounts are otherwise unused in the current
  architecture — rotate and retire.
