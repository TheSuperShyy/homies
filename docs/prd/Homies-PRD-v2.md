# Homies — Voice Agent, Chatbots & CRM PRD (v2)

**Prepared by:** CLIX
**Date:** 2 August 2026
**Status:** Draft for approval
**Supersedes:** [Homies-PRD-v1.md](archive/Homies-PRD-v1.md) (30 July 2026)

> **v1 is kept unchanged as the record of what was originally proposed.** v2 exists because two decisions changed the architecture materially — see *Changes from v1* below. Do not build from v1.

---

## 0. Changes from v1

| # | Change | Effect |
|---|---|---|
| 1 | **§2.3 payment deletion is now staff-confirmed.** The bot documents and verifies; a human confirms and performs the deletion in OXS. | Removes RPA **write** access to OXS |
| 2 | **§2.2 status requests read nightly Sheets data, not live OXS.** The bot reports last-night state with an explicit freshness caveat and creates a follow-up task. | Removes RPA **read** access to OXS |
| 3 | **Playwright / RPA is out of scope entirely for release 1** (follows from 1 and 2) | No browser automation, no OXS session or MFA handling, nothing that breaks when OXS ships a redesign |
| 4 | **Scope expanded to four delivered components** — voice (inbound + outbound), team chatbot, support chatbot, CRM | Outbound moves from "later phase" into the plan; CRM is specified rather than a single line |
| 5 | **The CRM is read-only metrics, not a work queue.** Staff tasks push to Monday. | Staff already work in OXS + Monday; a third tool demanding daily attention is an adoption risk |
| 6 | **§11 success criteria revised** — "check status without a human" removed | Follows from change 2 |

**Net:** a simpler, more robust system than v1 described, at the cost of one automated flow (live status lookup).

---

## 1. Overview

A Hebrew-speaking AI **Voice Agent** (phone) and **Chatbot** (WhatsApp) that handle routine resident interactions for Homies, backed by an automation layer that reads from and reports into the OXS building-management system, plus an internal **CRM** for visibility into day-to-day work.

The agents do **not** replace staff. They handle repetitive requests, capture structured data, and escalate anything sensitive to a human.

### Delivered components

| # | Component | Direction / Users | Release |
|---|---|---|---|
| **1** | **Voice agent — inbound inquiries** | Residents calling in | R1 |
| **2** | **Customer-support chatbot** | Residents on WhatsApp | R1 |
| **3** | **Team chatbot / centralized inbox** | Homies staff | R1 |
| **4** | **CRM** — day-to-day data and metrics | Homies staff | R1 |
| **5** | **Voice agent — outbound debt follow-up** | Residents with open debts | R2 |

Components 2 and 3 are **one build on shared infrastructure** (Chatwoot + n8n) — one is bot logic, the other is inbox configuration.

**Out of scope:** ManageChat migration · two-way Monday sync · live OXS reads or writes · any browser automation.

---

## 2. Voice Agent — Inbound Inquiries

### 2.1 Open Request
Resident asks the agent to open a new service request.

- Agent identifies the resident (phone match, or asks for building/apartment)
- Captures: request type, description, building, unit, urgency
- Creates the request record and returns a reference the resident can quote later
- Confirms back to the resident in natural Hebrew

### 2.2 Status Request *(revised in v2 — no live OXS lookup)*

Resident asks about an existing request.

**Flow:**
```
1. Agent identifies the resident and locates their request in the nightly Sheets data
2. Agent reports the state as of the last export, WITH an explicit freshness caveat
3. Agent creates a staff follow-up task for the current status
4. Agent confirms someone will come back to the resident
```

**Required phrasing pattern** — the caveat is not optional:

> *"As of last night, your request from the 3rd was logged as in progress. I'll have someone confirm today's status and get back to you."*

**Requirements:**
- The bot must **never** present nightly data as current. Stale data presented confidently is worse than no answer — it is the bot misinforming a resident on the exact flow meant to reduce calls to staff, and it fails silently (surfacing as complaints, not errors).
- If no request is found, offer to open one (falls through to §2.1)
- Every status request creates a `create_staff_task` entry regardless of whether data was found

> ⚠️ **Known limitation, accepted.** This is the one inbound flow that is not fully automated. Making it live requires either an OXS API (none exists) or RPA (deliberately out of scope). Revisit if OXS ships an API.

### 2.3 Update Payment Info in OXS *(revised in v2 — staff-confirmed)*

Resident calls to **change their payment details** (e.g. new credit card, new bank account).

**Flow:**
```
1. Resident asks to change payment details
2. Bot DOCUMENTS the request                      (logged before anything else)
3. Bot VERIFIES the resident's identity           ← mandatory gate
4. Bot creates a STAFF TASK with the verification result attached
5. Bot tells the resident a team member will action it shortly
   ─────────────────────────────────────────────────────────────
6. STAFF reviews the task, confirms, and deletes the payment info in OXS manually
7. System writes the audit record and triggers send_app_instructions
8. Resident receives WhatsApp instructions to enter new details in the OXS app
```

**Requirements:**
- **Verification is a hard gate.** No staff task is created unless identity verification passes. Failed verification → no action, escalate to a human.
- The request is **documented before** verification, so there is a record even if the flow breaks mid-way.
- Every deletion writes an **audit record**: who requested, what was verified, who confirmed, timestamp, what was removed, which interaction.
- **Follow-up:** if new payment details are not entered within the agreed window (48h or 72h — **still open, §13 #2**), the system flags the resident for staff follow-up.

**Verification method — still to be defined with Homies (§13 #1).** Options: caller ID + apartment/building + ID number + a detail only the resident would know. The staff-confirmed design lowers the stakes — a human now reviews before acting — but does not remove the need for a defined method.

> ✅ **Resolved from v1:** no RPA write to OXS, and no OXS-vendor sign-off needed for automated write access.

> ⚠️ **Residual risk — no payment method gap.** Between the staff deletion (step 6) and the resident re-entering details (step 8), the resident has no active payment method. If they never complete it, billing stops silently and they become a debtor. The follow-up flag is a mitigation, not a cure. A human is now in the loop, which is the main improvement over v1.

### 2.4 Payment Link
- Payment links are **generated by the OXS system** (not by us)
- The agent/bot **sends the OXS payment link** to the resident via WhatsApp
- Link send events are logged (who, when, which balance)

### 2.5 Complaint Tickets
- Agent captures complaints and opens a **ticket**
- Records: resident, building/unit, complaint category, description, timestamp, channel
- Sends a summary to the responsible team
- Escalates to a human immediately if the resident is angry, the issue is sensitive (safety/security/legal), or they ask for a person

---

## 3. Voice Agent — Outbound Debt Follow-Up *(R2)*

The same voice agent running outbound: calls residents with open debts, explains the balance, offers to send the OXS payment link, logs the outcome, retries no-answers, escalates disputes to a human, and produces a daily report.

**Requirements:**
- **Duplicate prevention** — last-contact date and outcome per debt, enforced before any dial
- **Call windows** — legal calling hours only; DNC list respected
- Israeli caller ID via Telnyx outbound voice profile
- Tone per §9 — never pressuring. This flow carries the most reputational risk.
- Reuses `send_payment_link`, `transfer_to_human`, `identify_resident` unchanged

> ⚠️ **Gated on §13 #6** — call-recording consent and legal calling hours under Israeli law must be confirmed before the first outbound call.

---

## 4. Chatbots

| # | Chatbot | Audience | What it does |
|---|---|---|---|
| **2** | **Customer support** | Residents, on WhatsApp | Same four flows as §2, text channel. Reuses the §7 tools verbatim. |
| **3** | **Team / centralized inbox** | Homies staff, in Chatwoot | Teams = departments · routing · assignment · tags · bot on/off per conversation · SLA labels |

Both channels share the **same backend logic and data** — one brain, several front doors. This is why component 2 is inexpensive to add once the voice agent works.

---

## 5. CRM *(new in v2)*

**Read-only visibility over Supabase. Not a work queue.**

Homies staff already work in **OXS** (the spine) and **Monday** (listing). A third tool that demands daily attention would not be adopted. Actionable tasks therefore push to Monday; the CRM shows what happened.

**Views:** requests · tickets · payment-change history · escalations · interactions with transcripts

**Metrics:** daily volume · % resolved without a human · identification rate · voice latency · open tickets by department · debtor list

**Requirements:**
- Supabase auth with department scoping — staff see only their department's data (§10)
- **Hebrew RTL throughout** (`dir="rtl"`, mirrored layout) — the staff are Hebrew-speaking; this is a build requirement, not styling polish
- Every interaction is reviewable with audio + transcript + tool-call trace

> **Open (§13 #7):** whether staff genuinely live in OXS + Monday is unconfirmed. The architecture absorbs the uncertainty — see `create_staff_task` in §7.

---

## 6. Channels

| Channel | Tech | Use |
|---|---|---|
| **Voice** | Vapi (Azure Hebrew STT + TTS) + Telnyx number | Inbound service extension; outbound campaigns |
| **Chat** | WhatsApp (Meta Cloud API) + Chatwoot | Text conversations, payment links, handover |
| **Internal** | Next.js CRM + Monday | Visibility and staff tasks |

---

## 7. Human Handover (mandatory)

Every flow must offer a path to a person.

- **Voice:** warm transfer to a rep (AI whispers a summary first). If no rep is available → log a callback task and tell the resident.
- **WhatsApp:** staff takes over the conversation; the bot switches off for that thread.
- **Triggers:** explicit request for a human · anger/distress · payment disputes · safety or legal issues · agent cannot resolve

---

## 8. Capacity & Performance

**Volume target:** 50–80 residents/day expected · **system must handle 200/day**

- ~25 interactions/hour at peak load
- **Concurrent calls: at least 10 simultaneous**
- Queue/retry rather than reject when at capacity

| Metric | Target |
|---|---|
| Voice response latency (voice-to-voice) | **< 800 ms** (currently 1500 ms — tuning is Phase 1 work) |
| WhatsApp bot first response | < 3 s |
| Successful resident identification | > 90% |
| Interactions resolved without a human | **to be renegotiated** — see §12 |
| Uptime | 99% during business hours |

---

## 9. Technical Architecture

```
Resident ──phone──▶ Telnyx ──▶ Vapi (Hebrew voice agent)
                                    │
Resident ──WhatsApp──▶ Chatwoot ────┤
                                    ▼
                              n8n  (brain: logic, tools, routing)
                                    │
          ┌──────────────┬──────────┼──────────┬──────────────┐
          ▼              ▼          ▼          ▼              ▼
      Supabase      Google Sheets  Monday   Next.js CRM     Staff
    (all records)   (nightly OXS)  (tasks)   (metrics)    (handover)
```

| Layer | Tool |
|---|---|
| Voice agent | **Vapi** — Azure Hebrew STT + TTS, GPT-4.1-mini |
| Telephony / number | **Telnyx** (+972 number, SIP) |
| Chat channel | **Meta WhatsApp Cloud API** |
| Agent inbox | **Chatwoot** (departments, assignment, bot on/off) |
| Automation brain | **n8n** (tools, logic, routing, reports) |
| Database | **Supabase** (Postgres — all records) |
| OXS bridge | **Google Sheets**, nightly batch. **No RPA.** |
| Staff tasks | **Monday** (GraphQL API, one-way push) |
| CRM | **Next.js** (App Router) on Vercel |
| Hosting | **VPS** (n8n, Chatwoot) + Vercel + domain/Cloudflare |

---

## 10. Agent Tools (n8n endpoints)

| Tool | Purpose |
|---|---|
| `identify_resident` | Match caller/sender to unit + building |
| `verify_identity` | **Hard gate** before any sensitive action (§2.3) |
| `open_request` | Create a new service request |
| `get_request_status` | Look up nightly-export status — **must return the export timestamp** so the agent can state the caveat |
| `open_complaint_ticket` | Log a complaint ticket |
| `send_payment_link` | Send the OXS-generated payment link via WhatsApp |
| `log_payment_change_request` | Document the change request before verification |
| `request_payment_deletion` | ⚠️ **Replaces v1's `delete_payment_info`.** Creates a staff task — does **not** touch OXS |
| `send_app_instructions` | WhatsApp the resident how to re-enter details in the OXS app |
| `transfer_to_human` | Warm transfer / assign to agent |
| `schedule_callback` | Log a callback when no human is available |
| `create_staff_task` | **Single indirection point** for all human follow-up |

All tools are **channel-agnostic** — the same n8n webhooks serve voice and both chatbots.

**Guardrail:** `request_payment_deletion` must reject any call where `verify_identity` has not succeeded for that interaction. Verification state is held server-side in n8n/Supabase — **never trusted from the agent's own claim.**

**Why `create_staff_task` exists:** every flow needing human follow-up routes through this one step. Whether the task lands in Monday, Chatwoot, or a Supabase table is one node's configuration. If Homies' actual working habits turn out to differ from §5's assumption, it is a one-hour change rather than a redesign.

---

## 11. Data Model

- `residents` — name, phone, unit, building, language
- `requests` — type, description, status, resident, unit, opened_via, oxs_ref
- `tickets` — complaint category, description, status, assigned_to
- `payment_events` — link sent, amount, channel, timestamp, status
- `payment_change_requests` — resident, requested_at, verification_result, staff_confirmed_by, staff_confirmed_at, re_entered_at, status, follow_up_flag
- `verification_attempts` — interaction, method, fields checked, passed/failed, timestamp
- `interactions` — channel, transcript/summary, audio_url, disposition, duration
- `escalations` — reason, sensitivity flag, assigned_to, outcome
- `staff_tasks` — type, source_interaction, payload, external_ref (Monday item id), status
- `debts` / `call_attempts` — R2 outbound: balance, last_contact, outcome, retry_count
- `staff_users` / `departments` / `audit_log` — access control and traceability

`payment_change_requests` gains `staff_confirmed_by` / `staff_confirmed_at` in v2 — the human step must be attributable.

---

## 12. Language & Tone

- **Hebrew-first.** Natural, calm, respectful, concise.
- Must not feel like "being thrown to a robot."
- Never aggressive or pressuring — especially on payment and debt topics.
- ⚠️ **Constraint:** Deepgram (Vapi's default STT) does **not** support Hebrew. Hebrew transcription must use **Azure (`he-IL`)**, Gladia, ElevenLabs Scribe, or Speechmatics. Current build uses Azure `he-IL` with voice `he-IL-HilaNeural`.
- A Hebrew speaker reviews transcripts against audio during every prompt iteration. Hebrew ASR errors are invisible to a non-speaker — a mis-transcribed street name surfaces as a low identification rate with no visible cause.

---

## 13. Security & Compliance

- Role-based access; staff see only what their department needs
- Full audit log of every agent action and data access
- Resident financial data treated as sensitive
- Recording/transcript retention policy to be defined
- ⚠️ **Open:** call-recording consent under Israeli law — must be confirmed before go-live, and again before outbound
- Credentials stored in the n8n credential store / env vars — **never in code or chat**
- ⚠️ **Outstanding:** three API keys (Telnyx, Retell, Vapi) were exposed in plaintext during scoping and **have not been confirmed rotated.** Rotate before any of them is wired to production.

---

## 14. Success Criteria *(revised in v2)*

1. Residents can **open a request, log a complaint, and receive a payment link** without a human
2. Status requests return an honest, caveated answer and always produce a staff follow-up task
3. Payment-change requests are captured, verified, and actioned by staff with a complete audit trail
4. Complaint tickets are captured with complete, structured data
5. Handover to a human works reliably on both channels
6. System sustains **200 interactions/day** with < 800 ms voice latency
7. Measurable reduction in repetitive calls reaching staff

> **Changed from v1:** criterion 1 previously included *"check status … without a human."* Removed per §2.2. The **>60% resolved without a human** target must be renegotiated with Homies — still achievable, but tighter now that status requires follow-up. Set the new number once the flow mix is measured in the pilot.

---

## 15. Phasing

| Phase | Deliverable | Week |
|---|---|---|
| **1** | Vertical slice — `open_request` end to end, latency tuned | 1 |
| **2** | Complete the tool layer (§10) and data model (§11) | 2 |
| **3** | All four inbound flows; Telnyx number + IVR extension | 2–3 |
| **4** | WhatsApp + both chatbots | 3–4 |
| **5** | Sheets bridge + Monday tasks | 3–4 |
| **6** | React CRM | 4–6 |
| **7** | Outbound debt follow-up | 6–8 |
| **8** | Load test, security pass, pilot | 8–10+ |

**Estimate: ~2–3 months to the full system.** Demo-able in week 1; pilot-ready at 5–7 weeks.

---

## 16. Open Items

**Blockers:**
1. **Verification method (§2.3)** — what exactly must a resident provide before staff will delete their payment info?
2. **Re-entry window (§2.3)** — 48h or 72h before an incomplete change is flagged?

**Needed to proceed:**
3. **OXS export** — sample file + agreed nightly delivery mechanism
4. **Homies' IVR vendor** — contact and SIP details for the service extension
5. **Which department** owns payment-change follow-ups and complaint tickets
6. **Call-recording consent + legal calling hours** under Israeli law
7. **Where staff actually work** — OXS vs Monday, and which board should receive tasks *(new in v2)*
8. **Business hours** for human handover; after-hours behaviour
9. **Monday API access** — token and target board

**Resolved since v1:**
- ~~Is deleting payment info on a phone request acceptable?~~ → No. Staff-confirmed (§2.3).
- ~~OXS RPA write approval~~ → Not needed. No RPA in release 1.
- ~~How are OXS payment links obtained?~~ → Still worth confirming with OXS Fintech, but no longer blocking: links are sent, not generated by us.
