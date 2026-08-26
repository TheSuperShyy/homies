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

**Sequencing that must always happen lives in code, not in the model.**
Proven three times on 23 Aug: the model (gemini-2.5-flash) makes one tool
call per turn and never chains, whatever the prompt orders. So open_request
verifies the address itself server-side (WhatsApp only), a workflow backstop
makes promised transfers real, and the dead-end follow-up is a wired lane —
none of these rely on model discipline. Prompts persuade; workflows and
tools guarantee.

**The WhatsApp bot is מיכאל again, and the warmth is the name, not the
punctuation.** Restored 24 Aug at the builder's request (nameless since 12
Aug "sounded AI"). The brief's English example — *"Hello! Michael here from
Homies. Hope you are having a great day"* — was answered, not translated:
no `היי!`, no smiley, no `היום`, and the bot never reports its own mood
(`הכול טוב, תודה` is banned). Voice and chat now share the name.

**`charges.period` is the month owed, one row per unpaid month.** Never a
cumulative "as of" stamp: the sweep never writes the current month, and a
current-month unpaid OXS row is deleted on every run as the one shape that
can only be wrong (023, 25 Aug). The 11 Aug correction -- onboarding runs
dropped, lagging buildings excluded -- is applied on every path, and a charge
is marked paid only when OXS shows a payment for that month on an apartment
read that run. Amounts are stored as OXS gives them (agorot and all) and
**shown in whole shekels** -- ₪105,760.7 on a card reads as a typo.

**Outbound is a button, not a runner.** Decided 25 Aug: a person presses Call
next to one resident on the Debts page; the agent rings that resident, once.
Nothing auto-dials. The press is the `handed_over` decision. A PIN is typed
with it because the page has no login wall. Transcript only -- recording is
off on every assistant and the deploy scripts keep it off.

**Targets the owner has set aside, 25 Aug.** Voice latency ~1.2 s is
accepted; do not spend time chasing the PRD's 0.8 s. Ten simultaneous calls
is not a target while outbound is a button pressed by a person. Do not reopen
these without being asked.

**A complaint is a ticket, on both channels.** `type: complaint` (migration
025), opened by `open_request` like a leak — about a neighbour, the cleaning,
a contractor, or a member of staff. It goes to a person only for anger,
danger, or an explicit ask. Nothing is written to OXS: the owner wants the
foundation first, and OXS stays read-only until told otherwise.

**Acceptance is the four client flows, not the plumbing check.** Before the
client is told to test, run open-ticket, status, balance and human on
`scripts/probe_whatsapp.py` and read the replies; `check_whatsapp.py` was
green on 25 Aug while two of those flows were not. Use a name that could be a
name — "בדיקת מערכת" failed the balance flow and it was the test, not the bot.

**The per-message instruction in the agent node outranks the system prompt.
First-message rules live there, in one sentence per branch.** Proven 25 Aug:
the 23 Aug dashboard edit of that line ordered "name, offer of help, then the
body", and the 32k-character prompt saying the opposite lost 11 of 11 probes.
Change the line and the prompt together, keep the script's copy identical to
live, and test with `scripts/probe_whatsapp.py` -- `check_whatsapp.py` was
green the whole time, because plumbing is not tone.

**The live n8n workflow is ahead of `n8n_whatsapp.py`, and a PUT is a
replace.** Eight nodes (the Chatwoot handback and the promise backstop) and
the Chatwoot-shaped Sort parser exist only in production. `--apply` refuses
by name until the script catches up; edit live through the REST API
surgically, back up first to `docs/handover/`, and bring the change back to
the repo the same day. The 23 Aug prompt rewrite went three days uncommitted
and was found only because a greeting change nearly overwrote it.

**No realistic example values in prompts the model might echo.** The bot
read a resident a ticket number fabricated digit-for-digit from the prompt's
own cautionary example. Formats are taught by structure (office code,
number, year), never by a plausible concrete instance.

**In n8n If-node expressions, never reference another node bare.**
`$('Node')` on a node that did not run this execution throws, and the If
silently evaluates false — no error shown (the dead-end checker sat broken
this way). And `$('tool').all()` never sees ai_tool output — a did-the-tool-
run check must use `isExecuted`. Prefer reading `$json` from the actual
input item wherever possible.

**`hebrew-voice-gender-pronunciation-skill.md` is the source for Hebrew gender
and pronunciation rules.** Part A (gender) is integrated into both voice
prompts. Part B (general homographs) is deliberately NOT: it is real Hebrew and
almost none of it can occur in building management, and prompt length is
attention. Take from it what the domain can actually hit.

**Search a Hebrew prompt with more than one spelling.** A claim that a rule is
missing was wrong on 20 Aug because the check used pointed לְךָ and the prompt
writes *lekha*. Unpointed, pointed, and transliterated are three different
strings for one word.

**Creating a WhatsApp inbox in Chatwoot IS the cutover.** Learned the hard way
21 Aug. Chatwoot writes a per-phone-number `webhook_configuration` override on
Meta, which beats the app-level subscription, so the number moves the moment the
inbox exists -- no separate registration step, no warning. The bot was dead for
two hours while `GET /{app-id}/subscriptions` still cheerfully named n8n. **To
learn where a number really points, read
`GET /{phone-number-id}?fields=webhook_configuration`.** The app subscription is
not wrong, it is simply outranked.

**n8n changes land BEFORE the Chatwoot inbox is created.** Corrected 21 Aug
from "before the callback moves", which was the same rule aimed at the wrong
step.
The plan's stated risk -- messages lost in the switch window -- is the small
one, and on a test number it costs nothing. The real one is that the instant
Meta delivers to Chatwoot the bot goes mute: the webhook verifies an HMAC
Chatwoot never sends, `Sort` parses an envelope Chatwoot never uses, and both
send nodes post to `graph.facebook.com`, where a reply reaches the resident but
never appears in the conversation staff are watching. Rewrite all three, update
`scripts/check_whatsapp.py`, then repoint. Never the other way round.

**Read a value out of `rails runner` with a delimiter, never a position.**
It prints a RubyLLM deprecation warning and a geoip line to stdout before your
output. `tail -c 200` put 197 characters of log into `.env` as an API token on
21 Aug. Wrap the value in a marker and grep for it.

**n8n does not need the MCP to be edited.** Its REST API takes a workflow
update: `PUT /api/v1/workflows/{id}` with `N8N_API_KEY`. Two traps -- the PUT
accepts only `name`, `nodes`, `connections`, `settings` and 400s on the other
eighteen keys the GET returns; and a URL parameter needs a leading `=` or the
`{{ }}` in it is sent literally. Always save the pre-edit JSON first; that is
the rollback.

**Access to the VPS is a key, not a password.** `~/.ssh/homies_vps`, root on
186.240.147.235. Appending to `authorized_keys` there needs care: the file had
no trailing newline, so `>>` welded the new key onto the previous one and broke
both. `printf` a leading newline, or check `wc -l` afterwards.

**GitHub Actions runs the import; the dashboard watches it.** Decided 20 Aug.
The dashboard is the control surface and never the engine -- the importers are
Python, they outlive a serverless timeout, and the dashboard holds only the anon
key on purpose. Do not move execution into it.

**A green tick that did nothing is worse than a red one.** Half the scheduled
runs exit in seconds because GitHub cron is UTC and Israel has daylight saving.
Anything reporting on those runs must say SKIPPED, never success -- reading
those ticks as imports is why nobody noticed the sync had never worked.

**An import is proved by the rows it wrote, not by the runner's verdict.**
Twice now the runner has been the wrong witness: green ticks on runs that never
started (20 Aug) and a healthy-looking `/sync` while every real run was being
killed mid-write (24 Aug). Ask the database. `max(updated_at)` on the table the
import writes settles in one query what a run list cannot settle at all, which
is why every count on `/sync` now carries the age of its newest row.

**OXS's ticket `status` is a constant, and the progress is in `treatmentLog`.**
Every service call they serve reads `פתוחה`, whatever its age — so a ticket
saying `open` in our database is not evidence of anything. What moves is the
dispatcher's note list (newest first, element 0 is current) and `lastUpdate`.
Closure is expressed by the call leaving the feed, never by the field, and
whether leaving means done is still question 2 on the client list — until it is
answered, a vanished ticket is flagged and dated, never resolved by us.

**A fast import must not ride on a slow one.** The eleven-second ticket import
was the last step of the twenty-eight-minute arrears job, so when the sweep in
front of it died it died too — eleven days of it. Independent data gets an
independent schedule; shared credentials are not a reason to share a workflow.

**Pace a rate limit per request, never per loop iteration.** `oxs_arrears.py`
slept twice per building while making three calls, which makes the real request
rate depend on network latency: safe from a GitHub runner, over the limit from a
machine near OXS, where it lost 37 of 175 buildings to 429s on 24 Aug and 511 of
576 debtors with them. The gate belongs inside the fetch function, keyed on the
previous request's start time. Retry a 429; never let one become a missing row.

**A partial run must not exit 0.** Everything downstream -- the workflow gate,
`/sync`, a person glancing at a run list -- reads the exit status and nothing
else. Write what was found, because an upsert that stops early leaves yesterday
standing, but say the run was incomplete in the one channel anybody reads.

**A migration that changes a constraint owns every statement that names it.**
Migration 012 moved the apartment onto the charge and dropped
`(resident_id, period)` on 11 Aug. Two importers still named it in their
`ON CONFLICT`, so both were a guaranteed 42P10 for thirteen days, unnoticed
because a different bug was killing them earlier. When a key changes, grep for
the old one -- and run the changed statement against the real schema, inside a
transaction you roll back, rather than reasoning about whether it still fits.

**The debt agent works an objection before handing it over.** Changed 20 Aug
from the opposite. "I'll pay when the lift is fixed" is a condition, not a
refusal, and transferring on it turns the commonest objection in the business
into an automatic zero. Four moves in one turn -- say it back, open the request,
say that the committee money is what pays for the repair, ask again -- then one
smaller ask, then stop. Never argue the fee, never say the two are unrelated.

**Pressing is about specificity, not volume.** Every escalation in that ladder
gets easier for the resident to say yes to, not harder: full amount, then a
date or a standing order, then a person. An agent that repeats the same ask
louder is the one residents complain about.

**One filled control per screen.** The orange `View call` is the row action;
everything else that clicks — Newer/Older, tabs, the size pills — is outlined.
Two filled colours competing means no primary action.

**Disabled controls stay put and go grey.** Never removed: a control that
vanishes shifts its neighbours and leaves the reader unsure whether they hit
the end of the list or misclicked.

**A filled button needs two colours, not one.** A shade dark enough to carry
white text on the light theme is too dim on the dark one. Every filled control
here defines its background AND its label per theme -- see `--action` /
`--action-ink`.

**If a row has an action, it looks like one.** The dashboard's global `a {
color: inherit; text-decoration: none }` makes every link invisible as a link,
so anything clickable in a table needs `.btn-sm` or it reads as text.

**A tool that returns success must say what it did NOT do.** `verify_address`
told the model to call it before `open_request` and never said it opens nothing
itself, so a successful check read as the job being finished and the model
answered with an invented reference. Where two tools are a sequence, the first
one's description carries the handoff.

**Never let the bot's own claim be the only record.** Every path that can tell a
resident something was written must have something behind it that writes -- the
emergency backstop in `transfer_to_human`, `rescue_request` for chat. The guard
that only *suppresses* a false claim leaves the resident with nothing, which is
quieter than the lie and no better for them.

**On a detail page, the thing you came for goes first and widest.** Reference
detail goes beside it, not above it, and anything whose length is set by the
data -- a transcript, a thread -- scrolls in its own pane rather than growing
the page. The call page broke both rules on 20 Aug and was unusable within
hours of shipping.

**A rule that says what to say must also say when.** The intake prompt's
two-way offer was written with great care about its wording and nothing about
its trigger, so on 20 Aug the model opened a call with it -- apologising to
somebody who had described no misfortune and offering a ticket to somebody who
had just asked for one. Every section that scripts a sentence needs the
conditions under which it fires, and at least one explicit *never*. This is the
sibling of the rule already here: any rule banning a kind of speech gets an
example of the speech still wanted.

**Check what already exists before building it.** Asked on 20 Aug to store call
transcripts so they could be viewed: they had been stored since migration 001,
filled since 8 Aug, and rendered on a live dashboard page the whole time. The
real work was three gaps that made the existing thing unusable -- no summaries,
an unreadable layout, no search. Reading first turned a rebuild into an
afternoon.

**An emergency must leave a ticket, not just a transfer.** Write first, then
transfer — in the prompt, and enforced in `transfer_to_human` regardless of what
the prompt achieved. A transfer is a note in `call_outcomes`; nothing searches
it, no dashboard lists it, nobody is dispatched off it. On 20 Aug a caller
reported a possible fire, the agent transferred without opening a request, and
the day ended with no record of it anywhere a person would look.

**A tool's vocabulary lives in three places and they drift.** The declaration
(`vapi_tools.py`), the handler allow-list (`debt-tools/index.ts`) and the
database CHECK have to be changed together. When the intake agent shipped with
its own transfer reasons, only the first was updated: `emergency`,
`out_of_scope` and `repeated_failure` were unstorable for as long as the agent
existed, and the handler quietly rewrote them to `caller_request` rather than
letting the insert fail. **A fallback that turns an invalid value into a
plausible one is worse than a crash** — it destroys the evidence that anything
went wrong. Prefer failing loudly; where a fallback must exist, make sure no
value the system sends itself can reach it.

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

**A model asked for a required field will invent one rather than ask.** Not a
tone problem and not a hallucination in the usual sense: `open_request` needs a
description, so a resident who had said only *"I want to report something"*
produced `description: "דיווח על משהו"` and a `fault_location` nobody had
mentioned. It is the tool schema doing the asking, and the model answering it
on the resident's behalf. So every tool that takes something a resident must
supply needs the prompt to say, in words, **not knowing it is a reason to ask,
not a field to fill** — and any offer to act needs a subject, because "shall I
open a ticket about this" with no *this* is answered yes by people who assume
we understood. Found 25 Aug.

**A prompt teaches by example before it teaches by rule, and the nearest text
teaches loudest.** "Never write X" loses to two hundred lines of X, so a ban on
a habit is only real once the file stops demonstrating it. And the per-message
instruction appended to every resident message outranks the system prompt on
register exactly as it did on content in Aug: it sits closer to the words being
answered. When output has a tic, look there first, then at the examples, then at
the rules. Found 25 Aug, over the em dash.

**A canned line cannot be fixed by editing the prompt.** Menu taps are answered
by the workflow with no model round trip, so those strings drift out of step
with the prompt silently and survive every prompt pass. A reply that will not
change is the signal. Where a fixed string and the prompt say the same thing,
they are two copies and both get edited, which `check_greeting()` already
enforces for the opener and nothing enforces for the rest. **Three copies for
the status button, done by hand on 26 Aug:** `TAP_LINE` in
`scripts/n8n_whatsapp.py`, the `TAPPED` map inside the live `Sort` node, and
the sentence quoted in the prompt's own status section. Push those by patching
the live nodes in place; `--apply` overwrites a workflow that is ahead of the
repo script.

**Correct, short and cold is still a defect.** The status button used to answer
`בטח. מה מספר הקריאה?` -- accurate, two clipped fragments, and no word in it
saying anybody is going to help. The owner read it as rude. A request for
information lands on somebody who has just asked for help, so the sentence
offers before it asks. And **a resident who replies "which number?" is not being
difficult**: most call once a year and do not know a reference number exists.
Say what it is and where they saw it, and give the other route in the same
breath.

**The Hebrew assistants are instructed in Hebrew; the English twins are not.**
Decided 25 Aug, and true of both Hebrew agents since 26 Aug -- debt from
`docs/features/10-debt-followup/prompt.md`, intake from
`docs/assistant/demo-inbound.md`. Fixed lines the agent speaks are carried
through verbatim when a prompt is rewritten, never re-translated, because they
are already the output. **Which also bounds what the change can do:** the
spoken fixed lines were always Hebrew, so rewriting the instruction cannot
alter them; what it moves is every sentence the model composes for itself.
And the twins are no longer derived from each other: `vapi_en.py` used to build
the English one from the live Hebrew and refuse to ship on a mismatch, which is
what kept them saying the same thing. **Changing one prompt now requires
changing the other by hand** -- but since 26 Aug something does fail if you do
not. `parity()` runs on every `vapi_en.py` path and refuses to write a twin that
has drifted, comparing heading count and level order, snake_case identifiers,
untranslated facts, and bullet and step counts. It does not fail on tables: the
Hebrew gender tables have no English counterpart and their absence is correct.
**It is weaker than the table it replaces** -- that could not ship a twin
missing a sentence; this notices a missing section, rule, code or fact.

**A same-language prompt bleeds into speech, and that is the cost of writing
the prompt in Hebrew.** Measured 26 Aug with `prompt_probe.py`: the Hebrew
intake prompt made the agent say `מה היה בנזילה?` (the missing-parcel example
applied to a leak) 4/4, `מתי זה ייקח` (question word swapped, verb left behind)
4/4, and `בוא נראה` 2/4 — a form that appears in the prompt ONLY in the column
of things it must never say. The English prompt produced none of the three.
When the instruction is in English, the change of language is itself the
boundary between what to think and what to say; in Hebrew there is no boundary,
so **every example, every forbidden form and every fixed line is also a
candidate sentence.** Write them so they cannot be lifted: name the forbidden
column as forbidden, bind an example to its case, and say which words move
together. All three went to 0/8 that way.

**The English agents cannot have the problem the Hebrew ones had.** Their
prompts were written in English and their output is English, so nothing is
rendered between instruction and speech. An English prompt driving a Hebrew
agent is the failure mode; an English prompt driving an English agent is not,
and rewriting their prose would improve nothing.

**A required beat needs its purpose written down, not just its name.** Beat 3
of the debt call was mandatory for a week and specified only as "anything
else?", so the model produced the most literal reading of that phrase and asked
the resident what else they wanted from it. Naming a beat says when to speak;
only its purpose decides what the sentence is for. The closing question asks
what is unclear, because the one thing that beat exists to catch is a resident
who did not follow the amount and would otherwise put the phone down confused.
Decided 25 Aug.

**A voice transcript is evidence of what a recogniser heard, not of what was
said.** Bot lines are built by transcribing the assistant's own audio, so
garbled Hebrew in a transcript says nothing about the model or the voice until
it is checked against `Voice cached` and the `Model output` events in the call
log. Before concluding anything about what a voice agent said, read the log.

**And establish whether a fault was heard or seen before explaining it.** That
same question on 25 Aug was answered with a confident acoustic-echo diagnosis,
written up and committed, while the owner was on headphones and typing -- a
fact one question would have surfaced, and which made the whole explanation
impossible. A symptom reported from a demo surface can be an artefact of that
surface.

**A line reported as robotic is not always a tone defect. Pull the turn before
rewriting the sentence.** `אני מבין. על מה אפשר לעזור?` was reported that way on
26 Aug. Execution 9798 showed the resident had tapped the status button, been
asked for a reference number, and answered `אין לי` -- so the reply was not a
stiff sentence, it was the bot discarding the thread and starting over. Warming
the wording would have shipped the same failure in a friendlier voice. The
executions carry the resident's own message beside the reply and cost nothing to
read; guessing at the missing half is what produces a fix aimed at the wrong
thing. Same shape as the acoustic-echo diagnosis above, and the third time this
week that reading the evidence changed what the fix was.

**And when a prompt fix does not take, check that the model was in the
conversation at all before rewriting it again.** The same `אין לי` came back
unchanged after the prompt was fixed and deployed. The prompt was fine — live
and byte-identical to the repo. **The Sort node answers four things itself: the
menu, both tap lines and the attachment line. None of them run the agent, so
none of them are in the agent's memory**, and the model met `אין לי` as the
first thing anyone had ever said to it. No prompt rule can survive that, because
every rule about a flow is conditioned on being in the flow.

**A flag fixes the case it was written for; the sentence fixes the class.** This
hole has been patched three times, twice with a boolean — `greeted` on 12 Aug,
`tapped_open` on 25 Aug — and each patch left the next canned line uncovered,
including one whose kind the code was already storing and never read. What the
model needs is not a fact about the flow, it is **the turn the resident is
answering**, so `said()` now carries the line itself out of the one place all
four leave the node. **The rule for anything added there later: a line the
workflow speaks is a line the model must be handed**, and the way to make that
survive a forgetful afternoon is a single choke point rather than a convention.

**Brand assets are derived, and the derivation is the record.** Everything the
dashboard shows of the logo — the login lockup, `app/icon.png`, the apple
icon — is cut by script from `Homies-Logo.png` at the repo root, which is the
one file the owner supplies. Regenerate from source on any change; never
retouch a derived file, or the next regeneration silently undoes the edit.
Two judgements that took a wrong crop each to learn: **pick the crop that
survives the size** (the roof mark is the favicon because it is the only part
of the logo legible at 16px — a shrunk wordmark is not a smaller logo, it is
noise), and **look at every generated image before shipping it** — the first
roof crop carried the letter-tops of the wordmark and an edge sliver, and no
build, type-check or probe can see inside a PNG.

**And the dashboard has two themes, so an asset that carries its own colors is
two assets.** `prefers-color-scheme` splits every ground in this app; a logo
whose wordmark is dark needs a dark-theme variant with that wordmark
recolored, served by `<picture>`, or it vanishes for half the audience — the
first dark attempt shipped navy-on-navy and only a preview caught it. **The
preview that counts is composited on each theme's own ground color**, not on
a checkerboard: transparency being correct says nothing about legibility.
Same rule as the token contrast checks — measured against both themes, every
time, because an eye on one theme cannot clear the other.

**A login wall must be tested from its own public page's point of view, not
only the pages it guards.** The wall that correctly bounced every dashboard
page also bounced the login page's own logo — a subresource request carries no
special status, so /homies-logo.png was 307'd to the page displaying it and
rendered as a broken image. The probe that proved the wall up ("/ redirects,
/login answers 200") could not catch it, because it fetched pages and not
their assets. When adding any blanket intercept, enumerate what the PUBLIC
side loads — images, fonts, manifest — and verify those URLs answer 200
logged out; the exclusion belongs in the matcher by extension, and the data's
guard stays RLS, not the redirect.

**"OXS is read-only" has exactly one exception now, and its edges are sharp.**
Since 26 Aug `open_request` mirrors new tickets into OXS via
POST /service-calls — owner's decision, made knowing it reverses the standing
rule. Everything else stays import-only, and mostly not by policy: the API
itself refuses write-scope keys for every module except service_calls. The
mirror is best-effort (the resident's reference is already promised when it
runs), the created `_id` lands in `requests.oxs_ref`, and the importer treats
a feed id held by a non-imported row as its own reflection and skips it —
**that skip is what stands between the mirror and a duplicate row for every
bot ticket, so neither side of it may be "simplified" alone.** And the old
justification is a lesson in itself: the read-only rule was written when the
API truly had no writes, the API grew them, and the docstring kept asserting
the old world — a policy carried in prose outlives the facts that made it.

**A re-lock is only as complete as the list of what was opened.** Demo mode
opened three things (read policies, one column write, one RPC execute), and
only the first was written down in the migration that promised the re-lock.
When opening access "temporarily", every grant goes in the same file as the
plan to close it — later grants to the same role belong beside it, not in
their own migrations, or the re-lock closes one door of three. And the
reverse of dropping an anon write is CREATING the authenticated write, or the
feature the write served breaks silently for exactly the people who log in.

**A pronunciation instruction is testable before it ships, and the test is one
TTS request.** Whether Cartesia obeys nikkud was measured, not assumed: the
same sentence pointed masculine and feminine renders as different audio
(uncorrelated waveforms), so a prompt telling the model to point לָךְ is a real
lever and not a hope. The complement of the chat-side rule: **in writing,
unpointed לך marks nothing; in speech the engine must pick one — so chat drops
the mark and voice adds it.** The two rules come from the same fact about
Hebrew and go in opposite directions; carrying either one into the other
medium breaks it.

**An exception written far from the rule it overrides does not exist.** Proven
twice on 26 Aug: the `אין לי` fix, and then the transfer-context flow, where
"what arrives after a handover is context, not a request" sat in the transfer
section while the complaint rule 300 lines away kept opening tickets from it.
The model obeys the rule at the point of firing, so **the exception is written
inside the rule it excepts** — in both places if two rules fire — with a
cross-reference back to the full story. A precedence claim ("this beats every
other flow") helps but does not substitute.

**When the log runs out, take the sentence out of the call.** The clipped-last-
word report had nothing left in the call log — no interruption, no error, no
recording — and was settled by synthesizing the exact sentence through Cartesia
directly and measuring the waveform: speech ends 43-135ms before the audio
does, at full amplitude. **Cartesia sonic-3 pads no tail**, so any consumer
that tears the stream down early lands inside the last word; the margin is
bought in `voice_guard.py`'s PAD_RULES, which append an unspoken
`<break time="300ms"/>` after sentence-final punctuation. Two standing facts:
a complaint about a *sound* can often be reproduced outside the call for the
cost of one TTS request, and the break tag is the one way this stack can add
silence — Vapi has no tail-padding knob and formatPlan replacements are the
only hook that touches every chunk of every utterance.

**A voice call reported as "cut off" or "disconnected" is a latency report
until the log says otherwise.** Both calls behind the 26 Aug report ended
`customer-ended-call` into silence — no drop, no error; the resident hung up on
a line that was thinking. The check costs one command, `vapi_latency.py`, and
the number that matters is its caller-felt turn latency (endpointing included),
not the dashboard's panel. **A reasoning model does not belong on the speaking
end of a phone call**: gpt-5.2 spent ~4s of every ~5s turn thinking, and that
latency is variable, so the same agent passes one day's listening test and
fails the next. `customer-ended-call` in aggregate is itself a symptom — it is
what silence produces, because the caller is always the one to give up first.

**A canned line is not exempt from the prompt's style rules, and both tap lines
now follow them.** The two fixed replies in the Sort node were written before
the warmth rules and kept their clipped shape after the model's lines lost it —
the status line until the morning of 26 Aug, the open line until that evening,
each corrected only when the owner read it off a handset. The shape every fixed
line takes: **receive the person, then ask** — `בטח, אשמח לעזור. אפשר לספר לי
מה קרה?` — because the first half is what makes it service rather than a form.
A new canned line gets this shape on the day it is written, not after its own
screenshot; and it is always a three-copy change (`TAP_LINE`, the live `TAPPED`,
the prompt's worked example), moved together or not at all.

**One question mark per message is a ceiling and a floor.** The rule had been
read as a ceiling only, so replies drifted into statements: `אפשר לספר לי מה
קרה ואפתח על זה קריאה.` is correct in content and hands the resident a
description of what the bot is willing to do rather than a request to act, and
the turn stays stuck. **Every message the conversation continues after ends with
a question**, open wherever open fits and closed only when what remains really
is yes or no. Full stops belong to the messages that end things: a status
delivered, a reference number, a transfer that has happened.

**And on WhatsApp this is not only a matter of tone.** `Dead end reply?` appends
the three-button menu to any reply with no `?` in it, so a reply that does not
ask a question arrives as **two** messages. A doubled reply reported from a
handset is the backstop firing, not a duplicate send, and the fix is the missing
question rather than anything in the send path.

**A rule written for speech can be exactly wrong in writing, and the chatbot
carried one for a fortnight.** Hebrew marks the addressee's gender in `לְךָ`
against `לָךְ`, `שֶׁלְּךָ` against `שֶׁלָּךְ` — audibly. Unpointed, they are one
spelling, and a reader supplies their own gender. The WhatsApp prompt banned
them anyway, correctly observing that the letters are identical and drawing the
opposite conclusion, which cost the warmest word in the language on every turn.
**The test is not "is this word gendered", it is "can the person on the other
end see the gender in it"**, and for a text bot that means: pronouns, present,
future and imperative are visible; object and possessive suffixes and the ־ת
past are not. The owner's own voice spec is what settled it, by listing exactly
those words as the ones that *must* be pointed. **Before importing a voice rule
into the chatbot or a chat rule into the voice agents, ask which medium the rule
is about.** Most of a TTS document is inapplicable to a keyboard, and the parts
that transfer often transfer inverted.

**And gender the bot was told is not gender the bot guessed.** A resident who
writes `אני גרה` has handed over the fact; the bot follows it for the rest of
the conversation. A name in WhatsApp is still a guess and still counts for
nothing. The distinction is the whole of the policy: never infer, always use
what was actually written.

**Every instruction the model reads is in brackets, so a bracket in its output
is its own thinking.** A probe on 26 Aug returned an English deliberation
formatted like the per-turn instructions beside it, addressed to a resident.
Intermittent, so no test will hold it down. **It is stripped at the Send node,
which is the only place every outgoing message passes** — canned lines and model
replies alike — and the same place the em dash is stripped, for the same reason.
When the fix belongs to "nothing may ever leave carrying X", it belongs there and
not in the prompt.

**A retest of an unshipped fix is not evidence, and it looks exactly like one.**
The same `אין לי` was reported three times on 26 Aug, at 16:26, 16:36 and 16:50,
against a workflow that had not changed since 15:34. Only the first carried
information. **Before reading a retest, establish that the thing under test is
the thing that was changed** — for this bot that is one API read of the live
workflow, and it is the same discipline as pulling the execution before
rewriting a line. Say which build a screenshot is of, unasked, because the
person holding the handset cannot see the difference.

**State it as a fact and stop.** The per-message clause says only that this
message is an answer and quotes what was written; it does not say what to do
about it. What each of those lines means is already a section of the prompt, and
an instruction beside the turn would be a second prompt competing with the
first — the player-piano failure one paragraph down, arriving through the side
door.

**The dashboard is bilingual, and the language is the one piece of state that
is NOT in the URL.** Cookie `homies_lang`, Hebrew by default because the staff
are Hebrew speakers; `lib/i18n.ts` is the only place a user-facing string is
written. Everything else on the dashboard puts its state in the URL so a view
can be sent to a colleague, and language is the exception precisely because of
that: sending somebody a filtered list should not change their interface
language. **Add a string to the dictionary, never to a page** -- a hardcoded
one appears in the other language untranslated and nothing fails.

**Logical properties only, in every stylesheet rule.** `inline-start`, not
`left`. One hardcoded side is a corner that silently stays wrong in one of the
two languages, and it will be found by a Hebrew reader rather than by a test.

**Measure contrast, do not judge it.** Two pairs in the redesign missed AA by
0.16 and both looked fine: slate-500 muted text is 4.34:1 on the page ground.
The check is twenty lines of Python over the token list and it runs against both
themes; an eye cannot do it and a dark theme cannot be inferred from a light one.

**Fixing a defect by writing the sentence is how a prompt becomes a
player-piano, and it happened again on 26 Aug.** Three real faults were each
fixed with an exact Hebrew line, taking the WhatsApp system prompt from zero
verbatim lines to four in one afternoon. The owner caught it: *"I want the bot
to be open and not follow the script strictly."* **Count the verbatim lines
after a prompt session** -- it is one grep, and it is the only cheap signal that
this drift has happened. Keep the distinctions, which are substance, and delete
the wording. The single legitimate literal is a menu tap, because the workflow
answers it with no model call and there is nothing there to phrase.

**Do not promise routing that does not exist.** A resident is told their ticket
goes "לצות", never to a named department. The four Chatwoot teams exist and are
empty, and nothing routes to them automatically, so a sentence naming a
department describes a system we have not built. Revisit when routing is real,
not before.

**An offer that arrives WITH the question is not the offer the 25 Aug rule
bans.** That rule stops a ticket being offered to somebody who has described
nothing, because the ticket then opens empty. Asking what happened and saying in
the same breath what will be done with the answer is the opposite: the ticket
still opens only after they have told you something, and naming the outcome is
what makes the sentence sound like a person rather than a form.

**A general rule three hundred lines away does not reach the turn it governs.**
`במה אפשר לעזור?` had been restricted to the first message since 12 Aug, and the
model still produced it on message four. Naming the exact turn is what fixed it.
Distance in a prompt is real: a rule the model has to go and find is a rule it
finds sometimes.

**When two rules for the model contradict each other, one of them belongs in
code.** The opener must always carry the name; the bot must not reintroduce
itself mid-thread. Both are right, and no prompt holds both -- whichever is
written more forcefully wins that turn, which is drift dressed as behaviour.
A greeting is now answered by the workflow, so the name is a fact rather than
an instruction, and the mid-thread rule keeps its meaning for everything else.
The same reasoning already governs sequencing: what must always happen lives in
code, not in the model. Decided 25 Aug, after three attempts to fix it in the
prompt.

**A guard that fires on a shape will fire on correct output eventually.**
`Reply usable?` treated any one-word reply as a broken generation, which held
until the prompt gained a rule asking for exactly a one-word reply to a
mid-thread greeting. The guard then punished the model for obeying, and its
false branch opens a real ticket. When a rule is added on one side, the guards
that encode the old assumption have to be re-read: they do not fail loudly,
they fire on the wrong thing and look like they are working. Tie a guard to
what the message asked for, not to the length of the answer. Found 25 Aug.

**And whatever the workflow answers on its own, the model has to be told
happened.** The second half of the same rule, and the more expensive half. A
canned line is not just a string that drifts; it is a turn the agent has no
record of, so the next message reaches it stripped of what the resident had
already said. That is how a tap on *open a service call*, followed by a
description of a leak, was answered with an offer to open a service call: the
offer rule fired correctly on information that was missing a turn. Anything the
workflow handles without a round trip -- a tap, a menu, a canned first question
-- must hand its fact forward, the way `greeted` and now `tapped_open` do.
State that lives outside the conversation is invisible to the model unless
something puts it back in. Found 25 Aug.

**What happened comes before where it happened, on both channels.** An
intention — *I want to report*, *I have a problem*, *open a ticket* — is not a
description, and the address is never the next question after one. It decides
whether this is an emergency, and an emergency changes everything after it.
Voice learnt this on 20 Aug when a caller volunteered black smoke several turns
after being asked their building; chat had the same hole through a bullet that
treated a request as an account. Chat opens the door — `אפשר לספר לי מה קרה?` —
where voice asks briefly, because a live call charges for turns and a chat does
not. Sympathy waits for the description on both: being sorry about an unknown
is a formula, and it sounds like one.

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

**Every task is logged in three places, and a hook enforces it rather than
memory.** `docs/WORKLOG.md` for the chronology, `CONTEXT.md` for any standing
decision it settles, `HANDOVER.md` for anything a fresh session would act on
wrongly. Asked for three times; the first two were instructions and both were
broken, most damagingly on 19 Aug when the live Vapi account changed and both
briefing files kept naming the retired one. `scripts/check_briefing_logged.sh`
now blocks the end of a turn whose change set touches something substantive
without touching CONTEXT.md and HANDOVER.md. **If one of the three genuinely
needs nothing, open it and say why in a line** rather than skipping it — the
check is satisfied by an honest note, not only by a change.

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

**Pushing a prompt: check what a sync would strip before running it.** This
used to say never run `vapi_sync.py` blind, because the live assistants carried
tools the script did not know about. `INTAKE_TOOLS` gained
`get_request_status` and `get_balance` on 19 Aug, and the 26 Aug Hebrew push
went through `vapi_sync.py inbound --apply` with all six tools intact and
verified afterwards. The rule behind it stands: read the dry run's tool list
against the live assistant's before applying, and if the script knows fewer,
push prompt-only instead: GET the assistant, swap
`model.messages[system].content`, PATCH the **whole** `model` object back.
Either way, verify the tools survived.

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
