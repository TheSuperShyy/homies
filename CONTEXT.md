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

**Every way out of a turn is offered in the same breath, and the honest cost
comes with it.** A resident who cannot be helped by the agent hears both options
at once — a ticket, or the office with a wait — and picks. Offering them one at a
time, so the second only appears after the first is refused, turns an offer into
a funnel and reads as a script advancing rather than a person talking. The caveat
on the slower option is said because it is true, once, and the turn ends on a
question rather than a recommendation. Once they have chosen, that is the answer:
no second attempt at persuading them. Decided 19 Aug, having been asked for twice.

**A caller hears about their own request and a count of everything else.**
Somebody who names a street is not entitled to their neighbours' business. A
status lookup may return how many other requests are open in the building — a
number, nothing more — and never a description, a reference or a category for one
the caller did not ask about. Where nothing was named to match on, the
descriptions are withheld and the agent asks what the request was about rather
than reading the list. Decided with the client 19 Aug, after a caller asking about
a lift was told about a stolen parcel and then had it explained.

**A fix that removes a false negative must not create a disclosure.** The soft
fallback that stopped a lift enquiry returning nothing did it by widening to the
whole building, which is how the parcel leaked. Matching the caller's words
against the description finds their request without widening. When a broadening
is the fix, ask what else it lets through.

**Memory is within the call, and it is not storage.** The transcript is already
in context; what was missing was the instruction to use it. A question about
something the agent mentioned is not a new fault, an offer turned down stays
turned down, and "it" means the last thing named. Anything across calls waits on
the identity question, which nothing today answers. Decided with the client
19 Aug.

**When a caller says something is broken, read the tool calls, not the
transcript.** Vapi records the arguments the agent passed and what came back, and
that is the difference between "the lookup is broken" and "the model sent 106
instead of 1063". Twice on 19 Aug the transcript pointed at the database and the
arguments pointed at the model.

**An instruction the model can ignore is not a constraint.** Where a rule can be
enforced in the function, enforce it there and leave the prompt to explain why:
the agent kept passing an apartment for a lift after being told not to, so five
common-area categories now drop the apartment server-side. The prompt persuades;
the function decides.

**A recovery that guesses confidently is worse than the failure it replaces.**
The near-miss reference lookup first offered four candidates and had silently cut
off the right one. If a recovery cannot be complete, it has to say so and ask —
never present a partial list as the answer. Decided 19 Aug.

**A filter narrows an answer; it never causes there to be none.** Where a query
is narrowed by something the system inferred — a category, a label, a guess made
at write time — and the question comes from a person, the person is the one who
knows. Narrow, and if that empties the result, ask again without the narrowing.
Added as a hard filter on 19 Aug and wrong within the hour: a lift enquiry
returned nothing because the matching ticket had been filed as `other`.

**A rule written to guarantee an outcome will manufacture one.** *Never end a
call without a request, a partial or a transfer* made the agent transfer a caller
who had just declined a transfer. Any rule of that shape needs the case it was
never meant to cover written into it — a question asked and answered is a
complete call. Decided 19 Aug.

**A rule the model follows most of the time is not a guard.** Where the cost of
disobedience is a resident being told something untrue, the check goes where it
can read what actually happened — the workflow, the tool output, the execution —
not into another line of prompt. The bot claimed to have opened a ticket and
quoted a reference while calling only `verify_address`; the prompt had forbidden
exactly that since 12 Aug and was obeyed on every other run. Decided 19 Aug.

**A test fixture the system under test is right to reject is a broken fixture.**
Learned twice on the same file: `__selfcheck__` as a building name, then the
invented `הבדיקה 999` once `verify_address` began refusing addresses outside the
portfolio. Isolation has to come from something the system does not validate — a
marker in the text — not from making the input wrong. Decided 19 Aug.

**Anything spoken arrives as words.** A reference read aloud digit by digit
comes back from the transcriber as "one zero six three", and a lookup that only
parses digits fails on the one form the design itself produces. Spoken digits are
normalised before matching, in both languages. The general rule: **whatever the
agent reads out, it must be able to read back in.** Decided 19 Aug, after a
caller quoted a real reference and was told it did not exist.

**When two parts of a prompt disagree, the model follows the general one.** Not
the more specific, not the more recent. A condition that matters has to live in
the section that states the rule, not in a section three screens away that
qualifies it — the status section said not to ask for an apartment for a shared
fault, the capture section said to ask always, and the agent asked twice.
Decided 19 Aug.

**A lookup takes what a caller says, not what the database stores.** Exact
matching on anything a person speaks aloud is a lookup that fails silently and
looks like "no records" — a building matched with `.eq` wanted its punctuation
and its city. Match loosely, then **guard the looseness**: a filter for what they
named, and an explicit ambiguous answer when the loose match spans more than one
record, so the agent asks rather than picks. Guessing which building somebody
meant sends the answer to the wrong address.

**And do not ask for an apartment for something that is not in one.** A lift, a
lobby light, a gate, the bin store belong to the building. Requiring the flat
number made the commonest inbound question unanswerable. Decided 19 Aug.

**A line the model must say every time is not the model's line.** Where the
wording is fixed and non-negotiable, it goes somewhere the model cannot reach:
`voice.chunkPlan.formatPlan.replacements` for what must never be said, a tool's
**request-start message** for what must always be said while that tool runs. An
instruction is a suggestion — the waiting line was instructed, then instructed
more firmly after it was ignored, and it was ignored again the same afternoon.
When the line moves out of the prompt, the prompt has to be changed to say
*nothing* rather than left saying the same thing, or the caller hears it twice.
Tool messages are spoken and the twins share tools verbatim, so each one needs a
translation in `TOOL_MESSAGES`. Decided 19 Aug.

**A tool exists in three places, and it is not usable until all three have it.**
The handler (Supabase Edge Function), the route (the n8n Decide node, which
answers Vapi *before* the writer runs and returns `unknown tool` for a name it
does not know), and the declaration (`INTAKE_TOOLS` / `DEBT_TOOLS`, which is what
the assistant actually carries). A prompt section describing the tool is a
fourth thing and is not one of the three.

**And a prompt that describes a tool the assistant does not carry is worse than
a missing section.** The model will not say "I cannot" — it reaches for the
nearest tool it does have. On 19 Aug a resident asked for the status of their
elevator ticket, the agent had no lookup, and it opened them a second ticket for
the same elevator and read out its number. The handler had been complete for a
day and the prompt had described it for a day; the declaration and the route
were never added. Move all three together, or none. Decided 19 Aug.

**Hebrew is the source, English is derived, and the derivation is not word for
word.** The prompt is written with every spoken line in Hebrew and pushed to the
Hebrew assistant; `vapi_en.py` reads *that live assistant* and swaps each Hebrew
line for an English one. The English twin is never hand-edited — it is rebuilt,
which is why editing it in the dashboard loses silently.

So the translation in the pipeline runs **Hebrew → English**: carry the meaning
across, then pick the English a person actually says. The twins are the same
*flow*, not the same words. The reverse direction still matters, earlier and
invisibly — a Hebrew line composed in English first and rendered across comes out
grammatical and unsaid, and nothing here catches that, because by then Hebrew is
the source of truth.

The case that settled it: לפתוח קריאה is completely ordinary Hebrew, what a
building-management office says and what a resident says back. Its literal
English, "open a request", is not ordinary English — a caller heard it on 19 Aug
and said they did not follow. English has its own everyday word and it is
**ticket**. A faithful translation was wrong in the room.

The substitution table in `vapi_en.py` defaults to word-for-word and that default
is usually right, so **every deliberate divergence carries a comment next to its
entry** naming the register it follows. The test, in either direction, is whether
a person speaking that language would say it that way — never whether it matches
the other side. Applies to the WhatsApp bot's Hebrew as much as to the voice
agents. Decided 19 Aug.

**Short is not the same as cold — an answer gets two words before the next
question.** The pacing rules were written against a seventeen-second turn and
they worked; what they also did was strip out every acknowledgement, because
*do not repeat what they said* reads to a model as *say nothing*. The call of
19 Aug captured every field the office needed and met three consecutive answers
with three consecutive questions. הבנתי, טוב, אוקיי — two words, not a sentence,
not a thank-you, and not a repeat. **Any rule in a prompt that bans a kind of
speech gets an example of the speech that is still wanted**, or the model
resolves the ambiguity by removing more than was asked. Decided 19 Aug.

**A yes/no question is not a follow-up, and asking it twice is worse than not
asking it.** *"Anything else the office should know?"* collects nothing and
sounds like a form; the ticket learns something only from a question about the
actual thing — what was in the bag, what time it was left. Two follow-ups per
call and then stop, and never the same sentence twice in one call. Decided
19 Aug, after a call asked five and repeated one of them three times.

**A filter that deletes words is checked against real sentences, every time.**
`voice_guard.py` strips phrases from the spoken channel so a tool name can never
be read aloud, and on 19 Aug it deleted the verb out of the intake agent's
commonest sentence: a resident heard *"Would you like me to  though."* Six
two-word entries were ordinary English — `open request`, `office to contact`,
`wrong party`, `caller request`, `send payment link`, `request standing order` —
and every one produced a hole, silently, on every call. **An entry must be three
words or more and must read as machinery rather than as English**; two words is
nearly always an ordinary phrase in one of the two languages and belongs in the
prompt. The rule existed before this and was unenforced, which is the actual
lesson: `SAFE_SENTENCES` now holds the lines both agents really say, and
`vapi_leak_check.py --safe` fails if the filter changes one by a character. A
leak heard once is a smaller failure than a hole in every call. Decided 19 Aug.

**Check the Vapi balance before a test session, not after.**
`vapi_transfer.py --balance`, exit 1 when blocked. An overdrawn account refuses
every web call **before Vapi creates one**, so there is no call record, no error
in the history, and no trace anywhere except a rejection in the browser — an
afternoon on 19 Aug went to a false lead because the break coincided with a
deploy. The balance was thought unreadable (`GET /org` is 401 to a private key);
it is readable because **Vapi checks the wallet before it looks the assistant
up**, so asking for a uuid that belongs to nobody returns the wallet message when
overdrawn. Nothing is created, so it is free. Decided 19 Aug.

**A second account is kept mirrored, and promoting it is bookkeeping, not a
migration.** `--mirror` overwrites in place so no id moves and the repo is not
touched; `--promote` then repoints 19 ids across 11 files, carries the **public
key** with them, and swaps the `.env` pair. The public key is the half that is
easy to forget and impossible to diagnose: with the wrong one the page loads,
looks perfect, and every call is rejected by an account that does not own the
assistant. Promotion **refuses a target that cannot place a call**. Superseded
key pairs are kept under their account number, never deleted. Live account since
19 Aug: **account 4**. Decided 19 Aug.

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
| `vapi_transfer.py` | `--balance` first. Then `--apply` to move, `--mirror` to keep a spare in step, `--promote` to make that spare live |
| `n8n_deploy.py`, `n8n_layout.py` | Workflow deploy and layout enforcement |

Long sweeps: run with `python -u` so progress is visible, and in the
background. OXS rate limits are **60 requests/minute per key**, and a
per-building payments call can return ~10,000 records — a full sweep is half
an hour, not five minutes.
