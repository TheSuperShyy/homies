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

- **Route A:** the button calls Vapi, Vapi dials over Omni's SIP
  trunk. Built already; the agent knows the resident from the first second;
  Vapi reports no-answer, busy and voicemail itself. Was the preferred ask
  until 28 Sep evening — see the order flip below.
- **28 Sep evening, the owner flipped the order:** *"lets try that first
  instead of escalating on our preferred setup"* — the message to Omni asks to
  use their dialer API (Route B), not for a trunk. The trunk is no longer
  requested; it comes back only if Omni offers it themselves. Route B's
  technical shape and deal-breakers are unchanged.
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
- **The list to Omni — FINAL, 28 Sep evening** (checked once more against both
  PDFs: nothing asked is answered in them, and nothing they raise is missed;
  the one oddity deliberately left out is that their log request takes epoch
  milliseconds while their response sample shows seconds — trivially detected
  empirically once we have access):
  1. A live token and campaign id — the documents hold example values only.
  2. **Deal-breaker:** can an answered campaign call be forwarded to an
     outside SIP address? We provide the address once confirmed.
  3. One call per number, immediately, no automatic retries, only within
     hours we define.
  4. Our `external_id` as a custom SIP header on the forwarded call; if not,
     the resident's number as the calling party on that leg.
  5. When does a number leave the campaign so it can be called again; is
     there a way to remove one (their doc has none, and 200 = added "if not
     already present").
  6. Which number the resident sees — it should be Homies' own.
  7. Answering machines: detected and dropped, or forwarded as answered.
  8. Number format for the insert: `05…` or `972…` (their log sample mixes
     both).
  9. Billing: how the dialer call and the forwarded leg are charged.
  10. Call log: a read-only user, https, recordings off for our line, and can
      a log row carry the `external_id` we sent (today it has neither the
      campaign nor our id, so rows are matched by number and time only).
- **Testing:** the owner has an Israeli number, so no code exception — a demo
  debtor on it in בר כוכבא 23 (`scripts/debt_demo_person.py on …`), attempts
  reset after each test (`scripts/bk_reset_attempts.py`), each ring on the
  owner's go.
- **The two documents alone cannot make a debt call** (owner, 28 Sep: *"can we
  do a debt call using just the docs"*). The insert starts a call and the log
  reports on it afterwards; neither says what happens when the resident picks
  up (an agent, a queue, a recorded message), and nothing in them sends a call
  to an outside system, so our agent is not on the line unless Omni sets that
  up. The call log's one sample is an *inbound* call to an agent on an
  extension; it says nothing about dialer calls. Both documents hold only
  placeholders (`YOUR_CLIENT_TOKEN_HERE`, the textbook example uuid as the
  campaign id, a sample number and login); even the ringing needs a real token
  and campaign from Omni.
- **Not to be put to Omni yet: an agent login instead of forwarding.** Vapi can
  send a SIP REGISTER (`outboundAuthenticationPlan.sipRegisterPlan`: domain,
  username, realm), but its API describes that only for authenticating outbound
  calls over a trunk, and its inbound instructions all have the provider send
  the call to a Vapi address. Whether our agent would receive calls sent to such
  a login is undocumented: ask Vapi, or test, before offering it.
- **Checked 28 Sep against Vapi's docs and API definitions:** a plain SIP
  address takes calls with "no authentication or SIP registration"; `x-` headers
  fill template variables, case-insensitive; `assistant-request` is answered
  within 7.5 s end to end, and its reply type carries `assistantOverrides`
  beside `assistantId`, so "the live debt agent plus this resident's figures" is
  a supported reply. US signalling `sip.vapi.ai` (44.229.228.186,
  44.238.177.138), UDP/TCP 5060, TLS 5061; media UDP 40000-60000 from changing
  IPs. Omni lists SIP trunking (OmniSIP) among its products, so Route A asks
  for something they sell.

**7 Oct: Omni asked us for sample payloads. They have sent no API key** (the
owner, correcting an earlier "they sent us some api keys" the same day). Their
current setup cannot connect to an AI agent platform; that matches the 5 Oct
call ("your current system can't run the AI services"), where the free move to
Tokomni comes first. Nothing to connect with yet: none in `.env`, and the PDFs
still hold `YOUR_CLIENT_TOKEN_HERE`, so the email asks for a token and a
campaign id. The samples drafted for Omni, all values invented:

1. **Us → them, adding a number** (their own insert, one request per press of
   Call, never a bulk sync): `POST …/campaign/insert/?token=<theirs>` with
   `{"external_id": "<our residents.id uuid>", "campaign_id": "<theirs>",
   "number": "05…"}`.
2. **Them → us, the answered call:** not JSON. A SIP INVITE to our Vapi
   address (placeholder `sip:homies-debt@sip.vapi.ai`; extension 3 gets its own,
   e.g. `homies-service`), the tenant's number as `From`, and
   `x-resident_id: <the external_id>`. The addresses are created only after Omni
   confirms forwarding.
3. **Them → us, optional call result:** a JSON POST to a web address of ours,
   in their call log's own field names: `event`, `call_uuid`, `campaign_id`,
   `external_id`, `number`, `status` (answered / not_answered / busy / failed),
   `start_epoch`, `total_duration`. No such endpoint exists yet; without it we
   read their call log.

If their AI connection is not a SIP forward (for example, streaming audio to a
web address), their document for it changes the build: ask for it before
building anything.

**Still open.** The no-repeat rule beyond four attempts, calling windows and a
do-not-call UI (owner: follow-up); Homies' bank-transfer wording. **Answered
28 Sep, by reading the code:** the end-of-call writer does NOT bump attempts.
Only the agent's own `log_call_outcome` tool does (`bump_charge_attempt`), so a
call nobody answered, a busy line or a voicemail is never counted, the
four-call cap never sees it, and `call_outcomes.attempt` is never written.
That has to be fixed before the first real call, in either route.
