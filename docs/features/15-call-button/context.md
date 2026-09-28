# 15 — Why a button, and what was ruled out

**The owner's words, 25 Aug:** *"we need a button in the dashboard to make
the calls — like there is a list of tenants with open debt with a call button,
so it's a trigger, the agent won't auto call."* That replaced the PRD's
release-2 "campaign runner" with something smaller and safer, and it settled a
question the code had been carrying since 4 Aug: every resident is
`handed_over = false` so that `v_debt_call_queue` is empty and nothing can
dial. A runner would have needed someone to flip that flag in bulk. A button
flips it for one person at the moment a human chose them by name — which is
exactly what the flag was for.

**Why a PIN.** Written when the dashboard had no login wall (9-26 Aug): a
bare button on a public page would have let anyone with the URL ring a
resident about money, on Homies' number and Homies' bill. The wall came back
on 26 Aug; the PIN stays as the second, deliberate step before a phone rings.
It is typed every time, lives only in Vercel, and without it configured the
column is not rendered. This was the builder's call, not the owner's.

**Why the database composes the call.** `v_debt_call_queue_person` already
builds the Hebrew phrases (apartments, breakdown, months) and the charges
whitelist the end-of-call writer resolves every tool call against. The button
reuses it verbatim, so a real phone call carries exactly what a web-demo call
carried, and the prompt sees nothing new. `press_call` wraps it in SECURITY
DEFINER because the page runs on the anon key, which 010 opened for SELECT and
011 for one column's UPDATE; the function is the only write on `residents`
that key gains.

**Ruled out.**
- *Placing the call from the browser with the Vapi web SDK* — that is a web
  call, the resident's phone never rings.
- *A queue page with "call next"* — a runner by another name; the owner said
  no auto-calling.
- *Setting `handed_over` for everyone so the queue fills* — removes the
  interlock for no gain now that the press is the decision.
- *Recording audio for review* — owner: transcript only.

**28 Sep: if Omnitelecom will not give a SIP trunk.** Omni sent two API
documents (kept out of the public repo, in `local/omnitelecom/`): a **dialer
campaign** API (`POST https://api.tokomni.cc/api/campaign/insert/?token=…`
with `{external_id, campaign_id, number}`; their dialer rings the numbers put
in a campaign) and a **call log** API (email and password in every request;
answered / not answered, durations, recording entries). The owner was told
"for outbound we just call the api". Both routes do call an API; they differ
in who dials and whether our AI knows who picked up.

- **Route A, preferred:** the button calls Vapi, Vapi dials over Omni's SIP
  trunk. Built already; the agent knows the resident from the first second;
  Vapi reports no-answer, busy and voicemail itself.
- **Route B, only if Omni offers no trunk:** the button sends one number to
  Omni's dialer (one press = one number = one ring; "campaign" is just their
  list). When the resident answers, Omni must forward the call to our Vapi SIP
  address (`sip:<name>@sip.vapi.ai`, no login needed). Vapi then asks our server
  who it is (`assistant-request`, ~7.5 s). We identify the resident by a SIP
  header carrying our id (Vapi turns `x-resident_id` into `{{resident_id}}`), else
  by the caller number, else by the one call waiting; **if none, the agent says
  sorry and ends — it never guesses, because a wrong match tells one resident
  another's debt.** Unanswered calls reach us only through Omni's call log, read
  every few minutes. Their dialer must dial once, now, with no retries, or it
  breaks the 25 Aug rule that nothing auto-dials.
- **What decides B** — ask Omni, deal-breakers first: can an answered campaign
  call go to an outside SIP address; one attempt, no retries, calling hours;
  our id as a SIP header, or the resident's number as the caller; when a number
  leaves the campaign (there is no remove call); caller ID; answering machines;
  the number format; https, a read-only user and recordings off for the call log.
- **Testing:** the owner has an Israeli number, so no code exception — a demo
  debtor on it in בר כוכבא 23 (`scripts/debt_demo_person.py on …`), attempts
  reset after each test (`scripts/bk_reset_attempts.py`), each ring on his go.

**Still open.** The no-repeat rule beyond four attempts, calling windows and a
do-not-call UI (owner: follow-up); Homies' bank-transfer wording. **Answered
28 Sep, by reading the code:** the end-of-call writer does NOT bump attempts.
Only the agent's own `log_call_outcome` tool does (`bump_charge_attempt`), so a
call nobody answered, a busy line or a voicemail is never counted, the
four-call cap never sees it, and `call_outcomes.attempt` is never written.
That has to be fixed before the first real call, in either route.
