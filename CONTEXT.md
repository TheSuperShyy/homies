# CONTEXT — how this project is worked

**If you were told to read the handover, read `HANDOVER.md` first, then this.**
Those two files together are the whole briefing: `HANDOVER.md` is the current
state — architecture, data, what works, what is blocked — and this file is the
rules. Neither repeats `docs/WORKLOG.md`, which is the chronology with the
reasoning behind every decision and is where to go when you need to know *why*.

Update this file when a rule changes. Update `HANDOVER.md` after every piece
of work.

---

## What Homies is

An Israeli building-management company — ~193 buildings, ~10,000 apartments,
~19 staff — getting a Hebrew AI voice agent plus chatbots. Two voice agents
(inbound intake, outbound debt collection), a WhatsApp bot, a dashboard.
Built on **Vapi + Supabase + n8n**, with **OXS** as the client's existing
management system.

The user is the builder. The client is Homies.

---

## Standing decisions. Do not relitigate these.

**OXS is read-only, forever.** Import from it, never write to it. The API
exposes write endpoints for service calls; they are forbidden. A change a
resident asks for becomes staff work, not an API call. If a design needs an
OXS write, the design is wrong.

**Supabase is the store of record.** Not Google Sheets — that was the pre-4
Aug data layer and is dormant. The old Apps Script deployment still exists as
a fallback in `vapi_sync.py`'s tool-server precedence and should eventually be
retired deliberately.

**This repository is PUBLIC.** github.com/TheSuperShyy/homies. Real resident
data must never be committed: names against phone numbers, debtor lists,
collection reports, call recordings. `.gitignore` carries the specific rules
and the reasoning for each. Check before every `git add`, and scan the staged
diff for phone numbers and key-shaped strings before committing.

**Nothing dials anybody yet.** No phone number is owned; voice is web calls
only. Every imported resident carries `handed_over = false`, which is what
keeps both queue views empty (`v_debt_call_queue_person` is the call queue —
one row per resident; `v_debt_call_queue` underneath it is per apartment per
month and a runner must never iterate it). Placing real calls needs the four
Omnitelecom SIP values and Homies' company documents, and a real outbound
campaign needs explicit approval every time — prior approval never carries
over.

**Money-spending actions need approval every time.** Buying numbers, placing
live calls, anything that bills.

**The n8n instance is shared production** carrying other clients' workflows.
Only ever create new workflows there; never modify, activate or delete
anything that is not Homies'.

**An address is verified against the real list, never taken on trust.** Homies
manages a closed set of buildings — 173 active, 4,092 apartments, mirrored from
OXS into `buildings` and `apartments` by `scripts/oxs_buildings_sync.py`. A
ticket is not filed against a street we do not manage or a flat that does not
exist; `verify_address` is called before `open_request` and the bot says what
is wrong, with the numbers we do manage, rather than "not found". Street +
number is unique across the whole portfolio, so **the city is never asked for**
— the sync re-checks that every run and refuses to write if it stops being
true. Ambiguity is returned for the bot to ask about, never resolved: below the
confidence floor, unmatched beats guessed, because a ticket on a confidently
wrong building reads correct and sends a van to the wrong street. Added
13 Aug.

**Warmth lives in the sentence, never in the fact.** The details pass through
verbatim — building, apartment, reference number, amount, months, status — and
every sentence around them is the model's to write like a person. A warm
phrasing never changes a number, never softens `not found` into *maybe*, never
adds a promise nobody made. Where warmth would cost precision the fact wins with
nothing to weigh: one half is fixed and only the other was ever available. This
is what makes "make it warmer" a safe instruction to act on, and it governs the
voice prompts too when that pass finally runs. Added 13 Aug.

**The chatbot answers building management and nothing else.** Weather, news,
sport, politics, medical or legal advice, outside suppliers, calculations,
translation, general knowledge — declined in one friendly sentence with a way
back to the building. The rule that makes it hold is **knowing the answer is not
a reason to give it**: a resident wrote to a management company, not a search
engine, and a bot that helpfully explains tomorrow's weather spends the
credibility it needs when it states what somebody owes. Three things look out of
scope and are not, and a fence without them is worse than no fence: ordinary
courtesy gets a human reply; a building question phrased generally is in scope
even when the answer is unknown; a complaint about a neighbour is common
property, which is ours. Decided 18 Aug.

**A fact we do not hold is not an escalation.** Asked something outside the
knowledge base, the bot says it does not have that detail and gives the office
phone and email — it does **not** open a staff task, and it does **not** say it
will check and come back. Nobody needs to *do* anything about a missing website,
and every such question would otherwise fill the office with empty work. The
second half matters as much: **a promise nobody recorded is a polite lie**, and
a phone number that works right now beats an undertaking no one is holding.
`transfer_to_human` stays for what it was built for — money that moves,
complaints about a person, danger, anger at us, identity that failed twice, and
a responsibility question too close to call. Decided 18 Aug, and it reverses an
instruction given the same day, deliberately.

**Ticket numbers are Homies' format, and ours are minted below theirs.**
`255-NNNN-YY` — their code for Homies, our serial, the year in two digits, the
shape every call in their system already carries. The four digits are a
constraint, not a style: `requests.reference` is unique and the OXS sync upserts
on it, so a serial that ever reached their five-digit counter would let their
call overwrite our row, and we cannot reserve a number from an API that is
twelve GETs. Mint below a counter that only climbs. **Both shapes have to keep
resolving** — tickets from before 18 Aug carry `HM-YYYY-NNNN` and residents still
hold those numbers, so `serialOf()` reads the serial out of either and nothing
matches on position alone. Decided 18 Aug.

**The resident ends the call, not the agent.** Four real calls on 18 Aug ended
with the agent deciding: that a question had been answered, that a refusal was
terminal, that a complaint was dealt with because a ticket had been filed. The
mechanism makes this unrecoverable — `endCallPhrases` carries the closing and
`endCallFunctionEnabled` is false, so **saying the phrase IS the hang-up** and
there is no turn afterwards. So: the closing question and the closing line are
each alone in their turn; a reply that is not a clean yes or no — including a
"no" with a sentence after it — puts the agent back in the call, with no limit on
the rounds; and **the reason for closing is never spoken**. *"Since you don't want
to pay this, I'll leave it there"* was said to a resident, over the top of a
complaint about a broken lift. A closing that explains itself is blaming
somebody. Decided 18 Aug.

**A refusal is never a reason for anything the agent says next**, and money set
against a service failure is not the agent's judgement to make. Withholding
payment because something is broken is the commonest reason a resident in a
managed building stops paying: it goes to a person, and the fee is **not**
explained in that moment — there it argues for paying for something that does not
work. Decided 18 Aug.

**Nobody is handed to the office without being offered a ticket first.** Three
rungs, in order: say the human thing, offer to open a request, and only then give
the office number — with what it costs, because *"there are a lot of calls at the
moment"* is true and a written request really is quicker. Going straight to the
last rung is the failure: two callers on 19 Aug, one with a parcel taken from
outside their door and one asking for a CCTV review, heard *"I cannot handle
that"* and were passed on with nothing written down while they were still on the
line. **Neither was out of scope.** A request is anything the office should have
in writing — `type: "other"` has existed since migration 014. What still skips
the ladder: money moving, receipts, disputed amounts, contract terms, legal
questions, complaints about a member of staff, and anything dangerous. Decided
19 Aug, and it is the intake half of the debt agent's ladder from 18 Aug.

**Call context is only authoritative about a call we placed.** `ctx.building` and
`ctx.unit` are facts on an outbound call — the runner attached them and a
mishearing must not move them. Inbound they are not facts about the caller at
all: they are whatever started the call. Ticket `255-1056-26` was filed against
Herzl 14, flat 12, for a caller who said *"Herzo"* and *"I don't know the
apartment number"*, because the webhook read `ctx.building || args.building` and
the demo page started **every** agent with a debt campaign's file. The test is
`dialled(ctx)` — a placed call always carries the resident or the charges, an
inbound one carries neither — and **not** "is `building` set", because the whole
point is that it was set and wrong. The caller's own words win on every inbound
path. Decided 19 Aug.

**The caller's number is taken from the call, never asked for.**
`call.customer.number` on a real call; the demo sends an invented mobile in
`caller_phone`, and the real one is read first so a variable can never override a
call. It lands on `requests.reported_by_phone` on every ticket both agents write.
On a `needs_review` row, where the audio failed and there may be no address at
all, it is often the only way back to the person. Decided 19 Aug.

**A ticket can be added to, and never corrected.** `add_request_detail` appends
one fact at a time; nothing can move a building, an apartment, or a description
already written. That is what lets the intake agent keep writing the row the
moment it has a fault and a place — the line dies at three minutes with no
warning — and ask what the office will actually need *afterwards*, once nothing
is at risk. A correction after the number is out is still `transfer_to_human`.
Decided 19 Aug.

**Money is not read out to an unproven caller, and the proof is not a prompt
rule.** On WhatsApp a balance costs a full name *and* a phone number, both
typed by the resident, both landing on the same `residents` row — the number
the message arrived from is a signal, never an identity. The refusal lives in
the Edge Function, because a prompt rule is a request and this one guards
money. Failures return one flag, never *which* half was wrong: a per-half
answer turns the check into a tool for testing guesses. Added 13 Aug from
client security feedback (PRD §13 #1). **The inbound voice line still
identifies by building+apartment or by name and is the same hole** — left
alone under standing instruction, and open.

---

## The voice prompts

`docs/features/10-debt-followup/prompt.md` and `docs/assistant/demo-inbound.md`
are the source of truth. The prompt file's own "rules for editing this file"
section governs, and the short version is:

1. **Describe what to convey. Do not write the Hebrew.** The model composes
   better Hebrew than we do, and a scripted turn is a turn it cannot adapt.
2. **A line is fixed only if it has to be** — Vapi speaks it literally, it
   carries legal weight, or a test proved the model does worse unscripted.
3. **Constrain substance, not sentences.**
4. **Say what to do, not only what to avoid.**
5. **Adding a paragraph has a cost.** The 7 Aug failures were "the model did
   not find the rule", and that gets likelier as the file grows. Every turn
   re-sends the whole prompt, so length is also money.

**Pushing a prompt: never run `vapi_sync.py` blind.** The live assistants
carry tools the script does not know about (`get_request_status`,
`get_balance` are missing from `INTAKE_TOOLS`), and a sync would strip them.
Push prompt-only: GET the assistant, swap `model.messages[system].content`,
PATCH the **whole** `model` object back. Verify tools survived.

**And never build `model.tools` from `vapi_tools.py` either.** Found 18 Aug: every
live tool carries a `server` block — the webhook URL and the shared secret — that
the repo definitions do not have. Replacing the list would have stripped all seven
on the debt agent, and nothing would report it: the agent still talks, every tool
call goes nowhere, and the resident is told a request was opened. To change a tool
description, edit the **fetched** object in place and PATCH the whole `model`.
Check `sum(1 for t in tools if t["server"]["url"])` before and after.

**Distilling a new "skill" document into a prompt means rejecting most of
it.** Anything conflicting with an earned rule loses: latency-masking fillers
lose to the silent-tool rule, de-escalation-to-keep-working loses to
hot-is-a-floor, endpointing config is not prompt text.

---

## How to work

**Log every task into `docs/WORKLOG.md` as it happens**, newest first, with
the reasoning — including what was rejected and why. That file is where a
decision gets traced back to the conversation that produced it.

**Then update `HANDOVER.md`.** Present tense only, rewritten not appended.

**Verify before claiming.** Query the database, call the endpoint, read the
file. Several times this project has been saved by checking rather than
inferring: the nine "debts" that were paid months ago, the 79% of arrears that
was buildings joining mid-year, the real phone number sitting in a docstring
about to be pushed public. When evidence contradicts the plan, say so and stop
rather than proceeding.

**Before deleting or overwriting real data, look at what is there.** Carry
what matters across a purge rather than assuming it can be rebuilt.

**Use the n8n skills before building any workflow**; never work from recall.
Workflows must be readable — no overlapping nodes, real names, sticky notes,
enforced by `scripts/n8n_layout.py`.

**A fact about Homies now lives in three files and deploys twice.**
`docs/reference/homies-faq.txt` is the source and **nothing reads it**; the
answers are written into the chatbot prompt (`מידע על הומיז`) and the debt
prompt (`WHAT YOU ACTUALLY KNOW ABOUT HOMIES`). Changing one changes nothing a
resident hears. Edit all three, then `n8n_whatsapp.py --apply` **and** the
prompt-only PATCH plus `vapi_en.py debt --update`. This is worse than it was and
is known: the alternative was a retrieval hop in front of every answer, and the
failure being fixed was a bot inventing what the fee covers — which never
triggers a lookup, because it does not know it does not know.

**Specs go in `docs/specs/`**, two files per feature in
`docs/features/NN-name/` (`feature.md` = what and acceptance, `context.md` =
why and rejected alternatives).

---

## How the user wants to be answered

- **Answer only what was asked.** One component asked, one component answered.
  No adjacent blockers volunteered.
- **"What have we done today"** gets flat bullets, past-tense verb first, one
  clause each, no explanation, no em dashes, `Will …` items last.
- Short answers to short questions. The user often asks by voice, so
  transcripts arrive garbled — read through the transcription rather than
  answering the literal words.
- Give an openable link when handing over a deliverable. A repo path alone is
  not a deliverable.

---

## The scripts

| Script | What it does |
|---|---|
| `oxs_api_import.py` | Residents from the OXS API into Supabase, real phones |
| `oxs_debt_sync.py` | Reconciles `charges` against what OXS lists as owed |
| `oxs_arrears.py` | Computes real arrears from payment records (the useful one) |
| `import_arrears.py` | Applies the onboarding correction, writes the charges |
| `oxs_purge_synthetic.py` | Removes synthetic-phone rows before a re-import |
| `oxs_probe.py` | Probes the OXS API surface |
| `vapi_sync.py` | Full assistant sync — read the warning above first |
| `vapi_tools.py` | Tool definitions; `INTAKE_TOOLS` is behind the live assistant |
| `vapi_en.py` | The English twins. `--dry` is the health check; a refusal means the table is stale |
| `vapi_export.py` | Redacted snapshot of the whole account. `--check` before committing |
| `vapi_transfer.py` | Clone onto a new account and repoint all 17 hardcoded ids |
| `n8n_deploy.py`, `n8n_layout.py` | Workflow deploy and layout enforcement |

Long sweeps: run with `python -u` so progress is visible, and in the
background. OXS rate limits are **60 requests/minute per key**, and a
per-building payments call can return ~10,000 records — a full sweep is half
an hour, not five minutes.
