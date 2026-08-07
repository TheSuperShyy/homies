# The debt follow-up assistant — outbound

Vapi assistant **`3303317e-43b6-4a84-9527-f86b905751d6`** — *Homies — Debt
Follow-up (he)*. Created 3 Aug 2026 and live.

**The prompt is not in this file.** It lives in
[10-debt-followup/prompt.md](../features/10-debt-followup/prompt.md) and is
pushed straight from there, so there is exactly one copy of it. This file holds
the platform configuration and the reasoning behind it.

```
python scripts/vapi_sync.py debt            # dry run
python scripts/vapi_sync.py debt --apply    # write
```

The script lifts the whole `## System prompt` section as the system message and
the blockquote under `### Opening` as the first message. Adding a `## ` heading
inside that section would silently truncate the prompt — the extraction stops at
the next level-2 heading.

---

## Platform configuration

| | Value | Why |
|---|---|---|
| Transcriber | `azure`, `he-IL` | The only Hebrew option in Vapi. |
| Model | `gpt-5.5`, no temperature | Changed from `gpt-4.1-mini` on 3 Aug for more natural Hebrew. The deliberate 0.3 came off with it and has not been restored — posture reading wants consistency, so this is worth revisiting once latency and cost are measured. |
| Voice | `azure`, `he-IL-HilaNeural` | Female. Every line in the prompt is feminine first person because of this. |
| `firstMessageMode` | `assistant-speaks-first` | It is an outbound call; the agent opens. |
| `maxDurationSeconds` | **240** | Target is a two-minute call. Past four minutes it is a call that should have been handed over. |
| `silenceTimeoutSeconds` | **20** | Outbound: a silent line is an answering machine or a hang-up, not someone thinking. Inbound uses 30. |
| `endCallFunctionEnabled` | true | The agent must be able to end the call itself after a voicemail or a wrong party. |
| `artifactPlan.recordingEnabled` | true | Quality review and dispute evidence. It stopped being the *authorisation* on 4 Aug — see below. |

## The recording stopped being load-bearing on 4 Aug

**Superseded.** For one day this said the recording *was* the authorisation for a
payment: the agent took a spoken approval to charge a card Homies holds, and a
staff member made the charge against it. Client decision, 3 Aug.

Reversed 4 Aug, also by the client. **The resident pays a link that OXS sends
them.** No card is discussed, no approval is taken, nobody charges anything on
their behalf, and consent now happens when they tap the link — recorded by their
payment provider, not by us.

Keep the recording on for quality review and for disputes. What changes is that
losing one is no longer losing the authorisation for money that moved.

That makes the recorded *"yes"* the artifact that authorises money to move. Two
consequences, neither of them handled:

- **Vapi deletes recordings after 14 days.** A chargeback window is months. The
  recording has to be copied to storage we control in the end-of-call webhook.
  Same defect as [07-partial-ticket](../features/07-partial-ticket/feature.md),
  now with money attached.
- **Israeli call-recording consent** (PRD §13 #8) stops being a go-live question
  and becomes a prerequisite for charging anyone.

The agent must never say a charge has happened. It says a person will handle it.

Turn-taking numbers are shared with the inbound assistant — the reasoning for
each is in [demo-inbound.md](demo-inbound.md) and is not repeated here.

Vapi switches on `transcriber.fallbackPlan.autoFallback` by itself and it was
left on. If Azure `he-IL` fails, Vapi swaps transcriber mid-call and the
alternatives do not do Hebrew — the failure mode is confident nonsense, not
silence. **This matters more on a collection call than on an intake call**,
because the resident cannot tell it has happened and the recording is what
someone will later be judged against.

---

## Variables

The prompt uses ten, listed in
[prompt.md](../features/10-debt-followup/prompt.md). They are supplied per call
through `assistantOverrides.variableValues`, not stored on the assistant:

```json
{
  "assistantId": "3303317e-43b6-4a84-9527-f86b905751d6",
  "assistantOverrides": {
    "variableValues": {
      "first_name": "צליל",
      "building": "הזוהר 6",
      "month": "יולי",
      "amount": "450",
      "card_last4": "4821",
      "verification_email": "homiesemail@gmail.com",
      "callback_number": "03-1234567",
      "gender": "f",
      "attempt": "1"
    }
  }
}
```

**A call with `amount` or `month` missing must not be placed.** The prompt says
the agent has no fallback and must never estimate — but a template variable that
is never supplied renders as an empty string, so the agent would cheerfully say
*"the payment for the month of, 0 shekels"*. The guard belongs in whatever
places the call, not in the prompt. It does not exist yet.

---

## Not wired up

**No tools are attached.** The prompt names eight —
`open_payment_ticket`, `log_promise_to_pay`, `request_standing_order`,
`log_disputed_payment`, `open_request`, `flag_not_handed_over`,
`transfer_to_human`, `log_call_outcome` — and none exist as webhooks, because
n8n and Supabase are not up. The agent will currently *say* it has opened a
ticket and logged an outcome, and nothing will have happened. It is testable as
a conversation and nothing more.

`open_payment_ticket` is the same shape as `create_staff_task` in the build plan
— the indirection that absorbs the OXS-versus-Monday question. Where the ticket
lands is one n8n node's configuration.

**No phone number.** The account has none, by decision — number integration
comes after the demo. It can be exercised through the dashboard's web call.

**No campaign layer.** Call windows, retry logic, duplicate prevention and the
DNC list are Phase 7 and unbuilt. Nothing currently stops the same person being
called twice in an hour.

---

## Open

**Whether to leave a voicemail at all.** The prompt has a voicemail message
written, and `voicemailDetection` is deliberately *not* configured, so today the
agent will talk to an answering machine as though it were a person. Both
alternatives — leave the written message, or log the attempt and hang up — are
one field. The question has been asked twice and not answered, and it cannot be
settled by us: leaving a message about a debt where a family member may hear it
is a privacy judgment the client has to make.

**The Hebrew is unverified.** Every line is reconstructed from the English
translation column of the transcript PDF, whose Hebrew layer is corrupt. A native
speaker must read them against the audio before anyone dials a resident.

**`gender: unknown` is untested.** The prompt handles it by phrasing around
gendered verbs. Whether resident records even carry gender is one of the
outstanding questions for Homies.
