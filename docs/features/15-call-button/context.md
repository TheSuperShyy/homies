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

**Why a PIN.** The dashboard has had no login wall since 9 Aug (demo mode).
A bare button on a public page would let anyone with the URL ring a resident
about money, on Homies' number and Homies' bill. The PIN is typed every time,
lives only in Vercel, and without it configured the column is not rendered.
This was the builder's call, not the owner's; it costs four keystrokes and
should stay until a login wall returns.

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

**Still open.** The no-repeat rule beyond four attempts, calling windows and a
do-not-call UI (owner: follow-up); Homies' bank-transfer wording; and whether
the person view's `attempt` is incremented by the end-of-call writer for
button-placed calls the way it was for demo calls — verify on the first real
call.
