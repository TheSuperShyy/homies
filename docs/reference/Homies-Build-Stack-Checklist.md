# Homies — Build Stack & Tools Checklist

What we need to build the three pillars (Collection voice agent, Service voice agent, Centralized WhatsApp), including **both voice options A and B**. Grouped by layer. Costs are approximate for planning; free tiers noted for testing.

---

## 1. Core Platform (shared — build first)

| Tool | Role | Plan / cost | Notes |
|---|---|---|---|
| **Supabase** | Database (all tables) + auth + storage (recordings/transcripts) | Free tier for dev; Pro ~$25/mo | Postgres. Holds every table + RBAC. |
| **n8n** | Automation brain — orchestrates everything | Self-hosted (free, Docker) or Cloud ~$20–50/mo | Call queue, retries, reports, bot logic, OXS jobs. |
| **Chatwoot** | WhatsApp shared inbox (Pillar 3) | Self-hosted (free) or Cloud from ~$20/agent/mo | Teams = departments, agents, assignment, tags, bot on/off. |
| **Hosting** | Run n8n / Chatwoot / services | VPS ~$20–40/mo (Hetzner/DO) or AWS/GCP | ⚠️ Check data residency (EU/Israel) for resident data. |
| **Claude API** (Anthropic) | LLM brain for bot + voice agents | Usage-based | Handles Hebrew reasoning. |

---

## 2. OXS Data Integration (interim, no API until ~Q2 2027)

| Tool | Role | Plan / cost | Notes |
|---|---|---|---|
| **Google Sheets** | Interim bridge — debtor imports, summary exports | Free / Workspace | The Excel layer. Start here. |
| **Playwright** | RPA — live OXS reads/writes (browser automation) | Free (open source) | Only if you need *live* lookups, not just batch. Runs as a small service n8n calls. |
| **OXS Fintech** | Payment-link generation | TBD — ask vendor | Confirm if they expose an API for links. |

**Also confirm with OXS directly:** what the "Metric API" actually exposes (analytics-only vs. real data), and whether any export/webhook exists on your plan.

---

## 3. Voice Call Center — Telephony Layer (needed for BOTH A and B)

| Item | Role | Cost | Notes |
|---|---|---|---|
| **Telnyx account** | Telephony: SIP trunk + numbers + inbound/outbound | Pay-as-you-go | Account exists but **$0 balance — must fund**. Rotate the exposed key. |
| **Israeli phone number (DID)** | Local caller ID | ~$3/mo + $3 upfront each | ✅ Available on Telnyx (+972 landline). ⚠️ Requires KYC/regulatory docs — start early. |
| **SIP Connection** | Bridge Telnyx ↔ voice AI ↔ existing IVR | included | Create Credential or FQDN connection. |
| **Outbound Voice Profile** | Enables outbound collection calls | included | Required before any outbound call. |
| **Existing IVR access** | Add the service extension (Pillar 2) | via Homies' phone vendor | Need vendor + SIP details to route the extension. |

---

## 4. Voice AI — CHOOSE OPTION A **or** B

### OPTION A — Hebrew-native all-in-one (fastest to good Hebrew, less control)

| Tool | Role | Cost | Notes |
|---|---|---|---|
| **Yappr** *or* **Voca.ai** | Speech-to-speech Hebrew agent (STT+LLM+TTS in one) | Per-minute + number fees | Native Israeli Hebrew, lower latency. ⚠️ Verify: does it expose **SIP** (to hook existing IVR) + **API/webhooks** (so n8n stays the brain)? |
| *(Telnyx from §3)* | Only if the platform doesn't bundle Israeli numbers/SIP | — | Some platforms bring their own numbers. |

**Pros:** fast, natural Hebrew, minimal engineering. **Cons:** vendor lock-in, per-minute cost, less control over logic.

### OPTION B — Build-your-own pipeline (most control, most work)

| Tool | Role | Cost | Notes |
|---|---|---|---|
| **Pipecat** *or* **LiveKit Agents** | Orchestrator — plug in any STT/LLM/TTS | Free (open source) + hosting | Lets you use the *best* Hebrew components (Vapi won't). |
| **STT (pick one):** ivrit.ai / ElevenLabs Scribe / Amazon Transcribe | Hebrew speech → text | ivrit.ai free (self-host); others usage-based | ivrit.ai = leading Hebrew ASR; Scribe ~3.1% WER. |
| **LLM:** Claude API | Agent brain | usage-based | Shared with §1. |
| **TTS (pick one):** ElevenLabs / Azure Speech | Text → Hebrew speech | usage-based | ElevenLabs = most natural Hebrew voices. |
| **Telnyx (from §3)** | Telephony/SIP | see §3 | Required — Option B has no telephony of its own. |

**Pros:** full control, swap vendors freely, own the data. **Cons:** more engineering, you manage latency + the STT→LLM→TTS chain.

> **Recommendation:** run a **Hebrew bake-off** (free) across A and B before committing — record real Hebrew calls, compare STT accuracy, TTS naturalness, latency. Decide from evidence.

---

## 5. WhatsApp (Pillar 3)

| Item | Role | Cost | Notes |
|---|---|---|---|
| **Meta WhatsApp Business (Cloud API)** | The WhatsApp channel | Per-conversation pricing | Needs **verified Meta Business account + 1 official number**. |
| **Meta test number (sandbox)** | Free testing before verification | Free | Build + test bot/handoff first. |
| **Chatwoot** (from §1) | Inbox UI | see §1 | Connects to Cloud API. |
| **BSP (optional):** 360dialog / Twilio | Simplifies WhatsApp API onboarding | markup on messages | 360dialog strong in EU/Israel. |

---

## 6. Accounts / Credentials to Set Up (secrets → store in n8n creds or env vars, never in chat/code)

- [ ] Supabase project + service key
- [ ] n8n instance (self-host or cloud)
- [ ] Chatwoot instance
- [ ] Telnyx — **rotate exposed key**, fund account, new API key
- [ ] Anthropic (Claude) API key
- [ ] ElevenLabs account (STT/TTS)
- [ ] Voice platform key — Yappr/Voca (A) *or* ivrit.ai + Pipecat/LiveKit (B)
- [ ] Meta Business Manager + WhatsApp number
- [ ] Google account (Sheets) + service account
- [ ] OXS: test account + sample Excel export + vendor contact for API/Fintech

---

## 7. Free-Tier Testing Kit (validate before spending)

| Layer | Test with | Cost |
|---|---|---|
| Hebrew voice quality | ElevenLabs free tier, ivrit.ai on HF, Retell/Vapi trial minutes, Yappr/Voca demo | Free |
| SIP call flow | Telnyx trial credit + **Zoiper/Linphone** softphone (no DID needed) | ~Free |
| Backend/logic | Supabase free + n8n self-hosted | Free |
| WhatsApp | Meta Cloud API test number + Chatwoot self-host | Free |

**Test order:** (1) Hebrew bake-off → (2) SIP plumbing → (3) n8n+Supabase data/report flow → (4) WhatsApp sandbox → (5) fund Telnyx + start IL number KYC for pilot.

---

## 8. Rough Monthly Cost (pilot scale, excluding usage)

- Supabase Pro: ~$25 · n8n cloud: ~$20 (or $0 self-host) · Chatwoot: $0–20 · VPS: ~$30
- Telnyx IL number: ~$3/number + call/minute usage
- Voice: Option A per-minute, or Option B = ElevenLabs + Claude usage + hosting
- WhatsApp: per-conversation (Meta)
- **Baseline infra: ~$75–120/mo + usage.** Voice + telephony + WhatsApp scale with volume.

---

## Immediate blockers to clear first
1. 🔑 **Rotate the Telnyx key** (exposed in chat) + fund the account.
2. 🗣️ **Run the Hebrew bake-off** → decide Option A vs B. Everything downstream depends on it.
3. 🏢 **Get OXS vendor answers** (Metric API scope, Fintech link API, test account) + Homies' IVR vendor details.
4. 📞 **Start Israeli-number KYC** on Telnyx (long lead time).
