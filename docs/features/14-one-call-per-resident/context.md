# 14 — One call per resident · context

Why this shape, and what was rejected. `feature.md` is what it does.

## Where the requirement came from

Asked on 11 Aug, after watching a demo call to a two-apartment owner:

> *"Calling multiple times to a single person is not the best way. The best way
> is to determine how many apartments this person has, what specific apartments
> have the balance not yet settled, how much is the total and what month still
> has an open balance, so we can complete all transactions in a single short
> call."*

That is a stronger requirement than the one it replaced. The earlier proposal
was "one call covering the total, with per-apartment arguments deferred to a
second version". It does not survive the phrase **complete all transactions**: a
resident who says "I already paid for number 4" in a call that can only record a
dispute against everything has not completed anything, and the office receives a
ticket saying both flats are contested when one of them is not.

## The counting was cut, later the same day

Everything below about counting apartments that owe nothing is the original
spec. Reading the plan back, the client cut it: *"we don't need to look for the
apartments that owe nothing... just the apartment that has an open balance."*
That removed the `apartments` table, the sweep change and `apartments_held` —
the whole data-collection half — and the feature shipped the same day. The
section is kept because the cheap path it describes is still the right one if
the counting ever comes back.

## The counting requirement is the expensive-sounding part, and it is not

"How many apartments this person has" needs apartments that owe **nothing**,
which Supabase does not hold. Both import paths upsert `on conflict (phone)`, so
`residents` is one row per person carrying one apartment, and only apartments
that earned a charge exist per-apartment at all.

Checked before estimating it: `oxs_arrears.py` sweeps every active building's
payment records and already iterates every apartment in them. It keeps the ones
behind, sets aside the ones with no payments at all, and silently drops the
settled. The half-hour sweep and the rate-limit budget are already spent; what
is missing is a list it chooses not to write down. That turned a "needs another
OXS project" into a change to one loop.

Worth stating because the requirement sounded like the costly half and is the
cheap half. The costly half is the tool layer.

## Compose in the queue, not in the prompt

The obvious implementation teaches the prompt two shapes: one apartment, and
several. Rejected.

Every turn re-sends the whole system prompt, so length is latency and money, and
`CONTEXT.md` already records the failure mode this invites — the 7 Aug failures
were "the model did not find the rule", which gets likelier as the file grows.
A branch is also the kind of rule a model applies inconsistently under pressure,
and this one would fire on every single call.

So the view hands over finished Hebrew: `דירות 4 ו-9`, `450 על דירה 4 ו-780 על
דירה 9`. The prompt keeps **one** sentence form and cannot get the branch wrong,
because there is no branch. This is not a new idea in this codebase —
`v_debt_call_queue` already composes the Hebrew month name in SQL rather than
letting the model derive it from a date.

## The agent selects, it never supplies

The hard part is that `log_promise_to_pay`, `send_payment_link` and
`log_disputed_payment` each write against a single `ctx.chargeId`, and a call
covering eight charges has nowhere to record a promise against eight.

The tempting fix is to let the agent pass `charge_id`. That is precisely what
`debt-tools/index.ts` exists to prevent: the agent never supplies `charge_id`,
`resident_id`, `amount` or `period`, so a model that hallucinates an amount, or
is talked into collecting a different debt, still writes the right row.

The resolution keeps the rule intact. The call carries a whitelist — the
`charges` array — and the agent passes a **unit**, which is a thing the resident
said out loud, not an identifier it could invent. The Edge Function maps unit to
charge id against that whitelist and refuses anything absent from it. The model
gains the ability to point at one of the debts already in front of it, and no
ability to reach a debt that is not.

Rejected alternatives for the same problem:

- **A parent "call" record every write hangs off.** Cleaner on paper, and a
  migration touching five tables to express something the whitelist already
  expresses. Revisit if a third thing ever needs the grouping.
- **One call per apartment, months collapsed.** Halves the calls and does not
  solve the requirement: Dana still gets two.
- **Leave it per charge.** Today's behaviour. Eight calls.

## Why the apartment is now always spoken

`{{unit}}` was "not spoken unless the caller asks", which was right when a
resident meant an apartment. The 11 Aug demo call showed the cost: the agent
quoted ₪780 for July to a woman with two July payments and never said which flat,
and when she asked which building, it refused.

The refusal was the anti-scam rule misfiring. That rule — never read out an
address or a unit **to prove who you are** — is correct and stays. What it is
not is a reason to withhold what the charge is for from somebody who has already
confirmed they are the account holder.

The prompt contradicted itself on this, which is the strongest argument that it
is a defect rather than a judgement call: the voicemail line says
`לגבי בניין {{building}}` to an answering machine belonging to nobody in
particular, while the agent refused the same fact to the confirmed resident.

## The ownership claim: the agent insists, and does not act

Decided 11 Aug, reading the "left broken" note above:

> *"The agent should insist, since the system says otherwise, and would say
> would you like me to forward you to the office regarding this concern?"*

This is the right call for a reason beyond this feature. `flag_not_handed_over`
sets `handed_over = false` and waives the charge **on an unverified verbal
claim**, made to an automated caller, by someone with an obvious incentive. That
makes "this flat was never mine" the phrase that ends any call about money, and
it is not a phrase anybody has to prove.

It also runs against a standing decision already in `CONTEXT.md`: OXS is
read-only and **a change a resident asks for becomes staff work, not an API
call.** Who owns an apartment is precisely that kind of change. The agent
recording it unilaterally is the same mistake as writing it back to OXS, one
layer down.

So the posture is: say once, plainly, that the system shows the apartment
against them; offer the office; do not argue and do not repeat the sentence.
That fits the prompt's existing temperament — hot is a floor, and de-escalating
into further persuasion loses.

**One wording correction to the instruction as given.** "Forward you to the
office" promises a live transfer, and `transfer_to_human` connects nobody — it
writes the call to the office for a person to pick up. `HANDOVER.md` states the
rule outright: never say anyone is being put through. The line is *"shall I pass
this to the office so they can check it and come back to you?"*

**Pause, do not waive.** On acceptance the apartment's charges move to
`pending_charge`, which `v_debt_call_queue` already excludes because it only
emits `unpaid`. That machinery exists for disputes and fits exactly: the
resident is not rung again next week about something the office is still
checking, and the ownership record is untouched. Waiving would have decided the
question the transfer exists to ask.

The side effect worth naming: this **removed** the blocker rather than deferring
it. Nothing automatic writes `handed_over` any more, so the multi-apartment
blast radius on that flag never opens, and this feature stops depending on a
change to the interlock.

The cost is real and belongs on the record: a resident who genuinely is not
responsible keeps receiving calls until a person acts. `pending_charge` bounds
that to the apartment they contested rather than all of them, but it is a
promise that the office follow-up actually happens.

## What this deliberately leaves broken

`residents.handed_over` is documented as "false when the apartment has not been
handed over" and lives on the resident. For a multi-apartment owner that is the
same category error migration 012 fixed for charges: flagging one flat stops
calls about all of them.

It is not fixed here, for one reason. That flag is the interlock keeping
`v_debt_call_queue` empty and keeping the system unable to dial anybody. Moving
it is a change whose failure mode is placing calls that should not happen, and
it deserves its own change, its own verification, and its own approval — not a
paragraph inside a feature about call grouping.

Until then `flag_not_handed_over` on an owner with several apartments is a blunt
instrument, and the honest handling is to route those to a person.
