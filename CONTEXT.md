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

**The dashboard's look comes from the supplied design system, not from taste.**
`Re-Design/` is the delivered source and `dashboard/design-system/` is the
vendored copy. Its token files stay byte-identical to the source; corrections
go in `tokens/app.css` with the measurement that forced them, so the diff
against the source stays empty and every deviation is visible in one file.
Dark is the default, light is `data-theme="light"`. Component values -- control
heights, radii, paddings -- are copied from the system's components, not
re-invented; where a number is copied the CSS comment names the component it
came from.

**Ornament is the one place the supplied design system gets overruled.** Its
values — colour, type, radii, control heights — are copied exactly. Its
decoration is not, where the decoration carries a meaning borrowed from the
dashboard it was recreated from: the hero's concentric rings belong to a stock
portfolio and say nothing about buildings. Ornament either says whose product
this is or it says nothing, so it gets replaced rather than inherited. Nothing
else in the system does.

**PostgREST's `or=()` is a parser, so user text never goes into it raw.** The
filter is a comma-separated list inside parentheses: a comma or a bracket in a
typed phrase does not error, it silently reinterprets the rest of the query as
more clauses, and `%` and `_` are `ilike` wildcards on top of that. Strip them to
whitespace before building the string. The same care applies to any filter built
by concatenating user input — the failure mode is a query that succeeds and
returns the wrong rows, which no test catches unless somebody types a comma.

**A list that truncates has to say so.** Every capped result set prints its real
total and how many are shown. A panel that quietly stops at eight is a panel
that says there are eight, and the cost is somebody acting on "there are only
two of these" when there are forty.

**Adding a property to a base rule changes every component that did not opt
out.** `justify-content: center` went onto the base `button` to fix an icon
button, and silently moved the theme switch's knob to the middle of its track —
a component that sets `display: inline-flex` but never had an opinion about
justification, because it did not need one until the base grew one. Before
widening a shared rule, list what already matches it; the ones that will change
are the ones that were relying on the default you are replacing.

**"I checked every variant" is a claim to verify, not to make.** The same
commit rendered nine button variants on one page and called it every button in
the app. The tenth was the theme switch, and the tenth was the one that broke.
Enumerate from the stylesheet or the markup, not from memory.

**When the same one-off rule has been written five times, the sixth case is
already broken.** Five components each carried their own `svg { width: … }`
because an SVG with a viewBox and no width renders at 300x150; the bare `button`
element had no such rule, so the one button in the app without a component class
rendered a 300px magnifier from the day it was written. A repeated workaround is
a missing default, and the cost of not noticing is paid by whatever comes next
and does not have a class. Put it on the element.

**A small screen sometimes needs a different component, not the same one
rearranged.** The sidebar was made responsive the usual way — same markup, a
media query, a column becomes a row — and it passed every check I ran: it fit,
it did not overflow, nothing was clipped by the layout engine. It was still
unusable, because seven labels in a 390px row means a horizontal scroller, and a
scroller nobody can see is a bar showing three destinations with two cut off
mid-word. The owner found it in a photograph of their own phone. Reflowing a
desktop component is the cheap answer and it is right most of the time; when the
content does not fit at all, the honest answer is a second component that does.

**Rendering it is not the same as using it.** The harness renders the markup as
written, so it answers "does this lay out" and never "can somebody work this".
Everything it can prove — no overflow, nothing clipped, contrast, both
directions — was green on a navigation bar that did not work. Ask what a reader
has to already know to operate what is on the screen; here it was "this strip
scrolls sideways", which nothing said.

**A breakpoint value measured on one screen is a guess on every other one.**
Three of the mobile defects were numbers that were correct where they were
chosen and wrong 600px away: a 176px tile minimum picked so a label would not
wrap, a 68% bubble width that is a comfortable line at 1000px and five words at
358, a 22px page padding that is 4% of a laptop and 11% of a phone. When a
number is set to make one thing fit, write down which width it was fitted at.

**A new field does not automatically want a new table.** Ask what reads it and
how often first. Two fields that the shell renders on every single page went
into auth metadata rather than a `profiles` table, because the request already
carries that metadata and a table would have cost a database round trip per page
render. The rule is not "avoid tables" — it is that storage follows the read
path, and the read path here was already decided.

**A control that does nothing is worse than no control.** Placeholders earn
their place only while they are honest about being one and only while something
is coming. The notification bell sat disabled and labelled "soon" for four days
with nothing behind it and nothing planned, which stopped being honesty and
became furniture. Draw the empty seat when the meal is ordered; otherwise leave
the chair out.

**When something is missing from the page, probe the DOM before theorising.**
Twice in one day an element that was simply absent had a cause no amount of
reading the source would have found — a stylesheet 404, and a flex item with a
computed height of zero. A ten-line script that prints `getBoundingClientRect`
and `naturalWidth` into a fixed overlay settles it in one screenshot, and every
guess made before running it was wrong.

**Do not disturb the owner's running dev server.** Verification builds go to
their own `distDir` (`NEXT_DIST_DIR=.next-verify npx next build`), and the
owner's processes are not killed or their `.next` deleted without saying so
first — a build sharing `.next` with a live dev server pulls the stylesheet out
from under it and the app appears to explode with nothing in any log. The wider
rule: when checking your own work costs the user their working copy, isolate
the check.

**Filters scope the whole panel, live in the URL, and put presets before a
calendar.** One row above the charts, never a picker per chart — three ranges
on one screen produce three numbers nobody can compare, and the first question
asked of a dashboard is whether one thing moved while another did. The range
belongs in the URL for the same reason every other filter here does: a view
should be a link you can send a colleague. And a percentage against a zero
baseline is not shown at all; dividing by zero is "nothing to compare with",
not "up 100%".

**A chart's numbers are checked against the database before it is drawn, and
its colours are computed rather than chosen.** Both rules were earned on the
same afternoon: one of the three metrics asked for had never had a row in its
table, and the design system turned out to ship no categorical palette at all.
So — query the table first and say plainly when the answer is zero rather than
quietly dropping the series; and run any categorical palette through the
validator against the real surface in both themes before it ships. A chart is
the one part of a dashboard that can be confidently, legibly wrong.

**Navigation in the dashboard is client-side, and the shell is a route group.**
Use `next/link` for anything inside the app; a bare `<a>` reloads the document,
throws away the shell and the skeleton, and spins the browser tab. The routes
live in `app/(app)/` with the shell as that group's layout, so `/login` cannot
render the sidebar by structure rather than by a condition. The rule that
follows from both: **a layout shared by two routes is not re-rendered when you
move between them**, so anything in the shell that depends on which page is
showing reads `usePathname()` on the client. A path computed on the server
freezes on first load and the interface starts lying — that is what
`x-pathname` was doing, and it is why it was removed.

**A verification build never shares a directory with a running dev server.**
Both `next dev` and `next build` write `.next`, so building while the server
runs rewrites the tree underneath it: the server keeps serving the manifest it
booted with, the hashed chunks it names are gone, and the browser 404s on its
own stylesheet. The page then renders with no CSS, which does not look like a
missing stylesheet, it looks like the app exploded, and nothing errors
anywhere. `next.config.mjs` therefore honours `NEXT_DIST_DIR`; verification
builds run as `NEXT_DIST_DIR=.next-verify npx next build`. Dev and the real
deploy keep `.next`.

**Colour is measured, never eyeballed.** `python scripts/contrast_check.py`
after any token change. The supplied system shipped four pairs under WCAG AA
and its own readme says the colours were taken off screenshots, which is
exactly why this is a script and not a judgement.

**A design change is not done until it has been looked at.** Build passing and
tokens measured are necessary and not sufficient — render it in a headless
browser at desktop and phone width, in both themes and both directions, and
look. Two defects in the 30 Aug pass were invisible in the source and obvious
in the image. Note that Chrome headless clamps its window to ~500px, so a
"390px" screenshot is really a 500px layout cropped; render inside a 390px
iframe to see a phone.

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

**Read the vendor's spec before calling a question unanswerable.** For three
weeks this file said OXS's ticket `status` was a constant and that closure could
only be inferred from a call leaving the feed — with whether leaving meant done
sitting as question 2 on the client list, and 36 tickets flagged and waiting on
it. `GET /service-calls` takes a `status` parameter that "defaults to open",
documented on page 6 of `OXS_External_API_v1.pdf`, and we had never sent it.
Every call reading `פתוחה` was our own filter reflected back. Measured 31 Aug:
`status=open` 42, `status=close` 26,903. **The constant was ours, not theirs.**
The general rule is the one that cost the three weeks: a field that never varies
is a claim about the query as much as about the data, and the cheapest test is
the parameter table, not the client's inbox.

**A ticket that leaves the OXS feed has been closed**, and the sync now asks
rather than guesses — each departure is fetched back by `taskNumber` and carries
a real status, a `doneDate` and a `closedBy`. What still holds from before: the
dispatcher's `treatmentLog` (newest first, element 0 is current) is where a
ticket's *progress* lives, because the feed's own status really is `open` on
everything in it — that part was never wrong, it just was not the whole story.

**Their vocabulary is `close`, not `closed`, and their paginated body is
`data: {finalList, totalCount, totalPages}`, not the `{data, total, pages}` the
PDF's example shows.** Both were found by probing and both are places where
trusting the document would have failed silently — a wrong status value returns
zero rows and no error, and the wrong envelope key returns one bogus row.

**Two screens reading one table must share the PREDICATE, not just the
formatter.** `shekels` and `month` were extracted so `/debts` and `/search`
could not round a resident's total differently — and the same bug was already
sitting one layer down, in the `WHERE`: search filtered charges to `unpaid`
while debts read `unpaid, disputed, pending_charge`. Nothing looked wrong,
because no row carries the other two today; it would have surfaced months later
as two pages quoting different money for one person, with no error anywhere. A
subset of an enum, hand-written at two call sites, is a divergence waiting for
the first row that exercises it. The list lives in `dashboard/lib/money.ts` as
`OUTSTANDING` and both pages import it. Extract the filter with the formatter,
or do not bother extracting.

**A panel that answers a question about a person must not inherit another
panel's cap.** Search's debt section was first built from the ids of the
residents panel above it, so the two could never disagree about who matched —
which sounded like a virtue and was a bug. That panel is capped at 8 and ordered
by name, so `גולן` listed eight Golans who owed nothing and reported no debt,
while דניאלה גולן, ninth alphabetically, owed ₪14,976. Join from the table that
holds the answer and cap that independently. Consistency between two lists is
worth less than either list being right.

**A per-row flag must measure something about the row.** This was got wrong
twice in one day on the same badge. "gone from OXS" fired on any ticket not seen
for 45 minutes — but if the importer has not run, every open ticket is stale at
once and none of them has gone anywhere, so it lit all 54 while 0 were missing.
The test: if the flag would turn on for every row at the same instant because of
something outside the row, it is a system fact wearing a row's clothes, and it
belongs wherever that system is reported. Here the fix was to compare each
ticket against the newest stamp in the table — which IS the last run — instead of
against the clock. Importer lag has one value for the whole system and lives on
/sync.

**A status list may hide rows; the state it derives may not.** Half of `/sync`
was `skipped — wrong hour` — real runs, permanent by design, and pure noise to
anyone looking for the last real import. Filtering them out is right, and the
way to do it safely is fixed: the table reads the filtered list, everything that
decides a banner reads the UNFILTERED one, and the filter is written so it can
never match a failure (here it requires conclusion `success`). Plus the count of
what was dropped, per the truncation rule above. Get this backwards — derive
"nothing has failed" from a list you filtered — and the page reports health by
hiding the evidence.

**A scheduled workflow runs from the DEFAULT branch, so a fix on a feature
branch is not running.** Two commits' worth of importer fix sat on
`feature/chatbot` while every scheduled run kept executing `main`'s old copy,
and the symptom looked exactly like the fix not working. If the change is to a
`.github/workflows` job or anything one calls, it is not live until it is on
`main` — and where a branch carries another session's in-flight work, cherry-pick
the commits rather than merging the branch to get there.

**GitHub's cron is best-effort, and at `*/15` that means about 5 runs a day.**
Measured 1 Sep over 30 consecutive runs of `oxs-requests.yml`: median gap 237
minutes, worst 746. It asks for 96 and delivers 5. Do not read a `*/n` schedule
in this repo as a frequency — it is a ceiling nobody enforces. Anything whose
correctness depends on a real interval needs a real scheduler; anything that
merely wants freshness must record when it actually ran, which is what
`oxs_last_seen_at` is for.

**An upsert is not a safe way to update rows that already exist.** PostgREST's
`on_conflict=...` with merge-duplicates reads like "UPDATE if present", and it
is not: Postgres evaluates CHECK constraints against the tuple the INSERT
proposes, *before* ON CONFLICT diverts it. A four-column payload aimed at 216
existing tickets was rejected by `requests_complete_unless_review` because the
proposed insert had `type`, `description` and `building` null. Sending the whole
row silences it and buys a worse problem — an upsert that can insert can mint a
half-built row under a mistyped key. **When the row must already exist, PATCH.**
UPDATE cannot create anything, and that is the guarantee you actually want.

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

**Warm is not casual: the register is polite and professional, and slang is
banned (27 Aug, owner).** The "sound human" work had put "מבאס" into the
prompt's approved empathy words, and the owner rejected it the first time a
resident-facing turn used that register ("make the response polite and
professional"). Empathy stays — "זה באמת מתסכל", "מצטער לשמוע" — but the bot
sounds like someone at an office desk, not a friend on the couch, even when
the resident is angry or slangy themselves. This bounds every future "make it
human" pass, chat and voice both.

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

**And the corollary, which cost six pushes on 31 Aug: a sentence present in a
prompt is a sentence the model will send.** Marking it wrong does not disarm
it — `זה לא משהו שאני יכול לעזור בו` came back verbatim one push after it was
written into the file as a ✗ example of what not to say. Nor does writing the
negative as a described shape rather than a sentence. If a phrasing must not
reach a resident, the only reliable move is that no version of it appears in
the file.

**An example in a prompt is a template, whatever the sentence next to it
says.** This file told the model `אלה דוגמאות ולא נוסח קבוע` three separate
times and the examples came back to residents word for word anyway. A rule
banning repetition **word for word** was satisfied by moving a comma. There is
no wording that makes a complete, sendable sentence safe to show a model: if
it is in the prompt it will be sent, so the only way to stop the reciting is
to leave nothing to recite.

**The intro and its menu are the only fixed text in the system.** Everything else a resident reads is written by the model, including the answer to a menu tap, the answer to a photo with no caption, and the rescue when a guard throws a reply away. Stated by the owner three times; the last four canned sentences went on 1 Sep. **Adding a stock line back — even as a fallback, even on a path that never runs — is reintroducing the thing.**

**A completed matter ends with an offer; a finished conversation ends with a parting; both are described in the prompt as ACTS — offer, thank, wish — never as sentences.** Owner decision of 1 Sep night, replacing the function of the canned follow-up menu two days after its form was removed. The closing paragraph's last clause is load-bearing: after the goodbye, no more questions, or the offer rule re-asks into a parted conversation. Two live outros differed in everything but warmth, which is what "not fixed" looks like when it works.

**The tool schema is a prompt too.** An optional parameter documented as a condition ("only if they asked about one specific apartment") became a three-round interrogation of a resident, invented before any tool had run, and was rationalised as `המערכת דורשת`. An optional field's doc states the normal case first ("almost always empty: the lookup finds it itself") and bans the question it would otherwise invite. Tool descriptions are covered by the memory epoch now (`EPOCH_COVERS['tools']`, via `tools_text()`); parameter docs that live only in live jsonBodies are not — bump by hand when one changes.

**The greeting list in `Sort`'s GREETING regex is the routing table for small talk.** A greeting it recognises gets the menu from the workflow and never reaches the model; one it misses gets clarified at by the model, in whatever register the model picks. English slang joined on 1 Sep after `wassap` was interrogated three times. A reply that contains the canonical intro sentence verbatim carries the menu regardless of `greeted` — an echo is indistinguishable from the intended intro, so it became one.

**n8n staticData is a per-execution snapshot and cannot coordinate concurrent runs.** Loaded when the execution starts, saved when it ends: two overlapping executions never see each other's writes and the last to finish clobbers the rest. `greeted`/`tapped`/`lastBot` work only because their writers finish before the next message arrives. Anything that must be shared across a burst lives in Postgres — the `messages` table, written by `Log inbound` before the wait, is the coordination point for batching. And `messages.id` is a UUID: order by `created_at`, never by id.

**A burst answers once.** The reply branch waits 4 seconds (owner: "3-5"), asks Postgres for anything newer, and only the run holding the newest inbound answers, with the whole unanswered backlog joined. The 200 to Chatwoot, the menu, and the tap handover never wait.

**Not-understanding is admitted, never repaired by a guess; nothing unasked enters a reply; a tool's silence is a fact the model does not fill.** Owner decisions of 1 Sep evening, after nine digits produced nine invented menu options, one real handover, and a recital of the facts list. The emergency numbers are scoped on their own facts line: for someone in immediate danger, and no one else.

**"Nothing is templated" has a precise meaning here, and a boundary.** No stored sentence exists that can reach a resident except the intro and its three menu rows — checkable, because only `Send` and `Send menu` put words on the wire, so a fixed string ships only via an assignment to `text` or `menu`, and the only one left is `said(MENU.content)`. What the guarantee does NOT promise: a model at temperature 0.6 given an identical short input will occasionally converge on identical wording (measured 1 Sep: 27 replies, one such repeat, across two numbers with no shared memory). That is not a template and the fix for it, if the owner ever wants one, is temperature — not a rule asking for variety, which is how the 66k prompt happened.

**The agent's memory is a second source of instructions, and it outranks the prompt, because an example beats a rule.** A live buffer holds the resident's turns, the bot's replies AND the bracketed context injected at the time, all presented as how this conversation goes. So a behaviour fix does not reach anyone who has talked to the bot before: on 1 Sep a tap answered **byte-identically to a reply from 58 minutes earlier**, nineteen minutes after the fix went live, out of a 36-message buffer holding three verbatim demonstrations of the bug. **A change that does not bump `MEMORY_EPOCH` has shipped to new numbers only.** Simple Memory lives in the n8n process, so bumping the session key is the only way to discard a buffer; `check_memory_epoch()` now refuses the deploy when the prompt or the injected template has moved and the epoch has not, the same way `check_greeting()` refuses when the menu and the opener drift.

**`probe_whatsapp.py` cannot see any of that**, because a fresh number has no buffer. Twelve clean probes and one broken live conversation were both true at the same moment. To test behaviour a resident would actually get, build history on one number first.

**The context injected into the agent node carries STATE AND FACTS. The prompt carries judgement.** A clause there that says what to write becomes the sentence the model writes: on 1 Sep one telling it to report the handover "in your own wording" produced the same two opening sentences on three different menu taps, which the owner read as a template and was right to. **A template written as an instruction is still a template.** The node was built on this rule and its own comment states it: an instruction there is a second prompt nobody reads beside the first. Facts also fail safely, because a wrong fact is caught by a probe and a wrong instruction is obeyed.

**Anything the injected context asserts must be gated on the same field the routing reads.** The handover claim is gated on `tap === 'human'`, which is what `Human tap?` tests, so the claim and the transfer cannot disagree. It was gated on `tap_now` for a day, which is true for all three menu rows, and the bot announced a handover on two rows that never had one.

**On this n8n, `executionOrder: v1` schedules a node's branches by their POSITION on the canvas, not by the connections array.** A branch placed lower runs later, and an earlier branch that throws ends the run before it. So the canvas is not a diagram of the flow, it IS the flow's order: **anything that must happen — a handover, a write — belongs physically above anything that can fail.** Cost two probes and a wrong diagnosis to find.

**A prohibition that quotes the phrase it forbids supplies the phrase.** The bullet saying `אין צוות שנמצא בדרך` used `בדרך` twice and the bot answered `עזרה בדרך`. Second time this exact mechanism has cost a day — the gendering line that named `את/ה` made slash-forms explode. **State the positive fact, put it where behaviour lives rather than in the lookup list, and let the absence do the work.** What replaced it is one frame, `אתה מדווח מה כבר נעשה, לא מה עומד לקרות`, which covers a whole family of invented promises without naming a single one of them.

**A tool description is read at the moment that tool is chosen, and nowhere else.** Telling `transfer_to_human` to go back and open a ticket afterwards did nothing, because the address arrives two turns later and by then the model is not reading that text. Moved into `open_request` it worked immediately. **An instruction about what to do LATER belongs on the tool that acts later, or in the prompt — never on the tool being called now.**

**An enum is prompt text, and one wrong-but-valid word can disable a safety net silently.** `transfer_to_human` offered `distress` beside `emergency`; the emergency backstop that writes a ticket when a handover leaves no record fires only on `emergency`, so the word that best described a hurt resident was the word that skipped the net — stored without complaint, reported by nothing. **When a guard keys on one value, no sibling value may describe the same situation better.** Fixed by removing the word from the channel that misused it, not by widening the guard, because the voice agent means something else by it.

**If the bot can claim it, the facts block has to deny it.** It told a resident the team was on the way. Nothing said otherwise — there is no dispatch, and no sentence anywhere said so — so the model supplied the most reassuring thing that fitted. A capability the product does not have needs a stated fact, not a rule; it sits with office hours and the emergency numbers, and it is one line.

**Never ask an n8n tool node whether it ran; ask the reply.** `isExecuted` is spuriously true and `.all()` throws from inside a downstream If — one makes a guard useless, the other makes it fire on everything, and both shipped on 1 Sep. The honest signal is in the output itself: a reference number exists only because the tool returned one, and ours have a fixed shape, so a claim without one is a phantom. **Guard on evidence the model could not have fabricated, not on workflow introspection.**

**An instrument that reads the wrong node will hide a working guard and invent a broken one.** `probe_whatsapp.py` read the agent's raw output, but three nodes can replace a reply before it is sent. Any tool that reports what the bot said must read the LAST writer, and the last run of it.

**A fix that makes the output worse gets rolled back, not supplemented.** On 1 Sep three changes were made to stop the bot repeating itself; the third made messages longer, switched the tic from singular to plural and brought markdown back. It was measured offline, reverted, and never reached live, and the prompt finished the pass the same size it started. **Adding a fourth clause to correct the third is how the 66k version happened.**

**One default beats a menu of options.** Told the neutral forms available in Hebrew — plural, infinitive, or rephrasing around the event — the model got it right once in three. Told simply to address the resident in the plural, always, it got it right four times in four. **Every option is a decision to get wrong once per sentence**, and a prompt that offers choices is asking for that decision every time. Pick the default and say only that.

**Naming a failure mode teaches it, and this survives the rewrite.** The stripped prompt's one gendering line said not to solve the problem with a slash mid-word; the replies came back full of slashes, including on the bot's own verbs. Removing the mention was necessary and not sufficient — the positive default was what fixed it.

**Where a fact goes decides whether it works.** The owner's correction that
handovers go to *department representatives* was written into the prompt's
facts list and changed nothing; moved verbatim into `transfer_to_human`'s
description it took on the first probe. A reference bullet at the bottom of a
prompt is background the model reads once; a tool description is read at the
moment it decides to act. **Ask which moment the model needs the fact, and put
it there.** Same for length: a channel fact about WhatsApp did nothing, a line
in `open_request` fixed mid-conversation replies but not the opening one, and
only extending the tap fact — *the tap already tells you what they want, so
what is missing is what happened* — removed the four-point form.

**Behaviour belongs in the tool descriptions, not the prompt, and the reason is
mechanical.** Tool descriptions are English; the bot answers in Hebrew. There
is nothing in them it can copy into a reply. When the emergency protocol was
deleted the bot stopped transferring anybody — zero in six runs for somebody
shut in a lift — and moving the same requirement into `transfer_to_human`'s
description fixed it without putting a single Hebrew sentence back in front of
the model.

**The prompt was never the only prompt.** The agent node injects its own
instructions on every message — 1,473 characters of them until 31 Aug,
including the whole offer script — and the `Sort` node answers greetings, menu
taps and media with canned Hebrew the model never sees. **Anyone auditing what
the bot says has to read all three**, and reading `prompt.md` alone will
mislead them.

**When a model behaves erratically on one path, check whether its tool
definitions contradict themselves before blaming the prompt.** On 31 Aug the
live prompt opened an ordinary ticket correctly **1 time in 3**, and the two
failure modes were stalling: re-asking an address just given, or writing
`אני פותח קריאה` and calling nothing. It read as prompt bloat. It was
`open_request` arguing with itself — its description said there is no step
before it, two of its own `$fromAI` parameter docs said to verify the address
first. Deleting those two strings took it to **8 in 9**. **A model given an
instruction it cannot satisfy does not error, it stalls**, and a stall looks
exactly like a badly written prompt.

**Prompt size is still measurable, and the measurement is worth redoing.** The
same run showed the live prompt reciting its worked examples near-verbatim
across three runs of the lift, gas and hesitancy arcs — it is a lookup table on
the paths it has entries for. And the balance section, ~45 lines, tied exactly
with a one-line rule and with nothing at all, because `get_balance`'s own
description already carries the identity check. But the headline finding of
that comparison was contaminated by the tool bug and should not be quoted.
**What did hold: constraints without craft are useless** — told not to gender
the resident and given no idea how, the 1,564-char prompt invented `את/ה`
slash-forms and sounded like a government form.

**A short prompt leans on tool descriptions far harder than a long one.** With
the rules gone, the tool text is most of what the model has. So a harness that
sends stale tool definitions measures the wrong prompt — and `wa_prompt_chat.py`
was doing exactly that until it was pointed at live. **Anything that reads the
bot's configuration should read it from live, not from the script that built
it**, because the script is behind in at least three places and nobody notices
until something is measured against it.

**A live probe cannot show you which tools were called, and that hid a real
defect for two days.** `probe_whatsapp.py` reads replies off the executions; it
says nothing about whether `transfer_to_human` actually fired. The first
offline run found the gas path announcing a transfer it never made, with the
`Promised a transfer, made none?` node silently covering for it. **When a guard
node exists, assume it is load-bearing until proven otherwise** — its whole job
is to make a failure invisible.

**A list of banned phrasings teaches the phrasings, not the boundary.** The
emergency block forbade three ways of rating severity; the model avoided all
three and wrote a fourth. Bans that enumerate need a **test** the model can
apply to a sentence it has not seen — here, "if your sentence rates how bad the
situation is, it is out". This is the same failure as the ✓/✗ lists, one level
up: enumeration cannot cover a space, and the file keeps trying.

**Naming what they feel is not rating the danger, and a prompt that forbids
both forbids warmth.** Written carelessly, a severity ban and the concern rungs
cancel each other out. "This sounds frightening" is about the person and is
always true. "This is dangerous" is a verdict on the hazard, which belongs to
the resident and the emergency services. **Only the clinical verdict is worth
banning** — life-threatening, all-clear, or a named cause. Banning ordinary
concern was an over-tightening, and it is recorded here because it looked
principled while being wrong.

**The proposed prompt rewrite failed twice, by two methods, on two agents.**
It arrived with a diagnosis of constraint overload and model paralysis. This
session probed the WhatsApp bot live and found the four claimed contradictions
wrong on the mechanism; the voice session drove the candidate text itself with
`prompt_chat.py --file` and watched it reproduce the original complaint almost
word for word, asking a trapped caller which apartment they live in. **Treat it
as settled** unless new evidence arrives — and note what settled it was running
the text, not arguing about it.

**Every worked example in this prompt was a single message, and the failures
are multi-turn.** That asymmetry explains a week of results: first replies read
well and second replies repeat the question, forget the transfer, or answer a
frightened person with a form. A resident trapped in a lift went three turns
with no `transfer_to_human` while every single-turn probe of the same words
passed. **The fix was the file's first two-turn example** — specifically one
where the resident does *not* answer the question, which nothing here had ever
shown. Probe arcs, not messages.

**And a tone rule must never decide whether somebody gets a human.** The
concern rungs are about how warm the sentence is; when one of them also said
what to ask next, it silently pre-empted the emergency protocol, because the
protocol never mentions the words that rung used. Keep the decision and the
register in separate blocks, and have the register hand off explicitly.

**One send per case measures the best case and nothing else.** The owner
caught a cold reply ten minutes after a push whose three verification probes
had all passed. Model output at temperature 0.6 has a spread, the resident
meets a random draw from it, and **what matters is the floor**. A behaviour
change is not verified until the same message has been sent at least three
times.

**An example that contradicts the rule beside it is the one that wins.**
Twice in one day: a generic concern line among four specific ones, and a
question that dropped the resident's word while the rule above it required
carrying it. Both were recited three runs of three. **Every example in a block
must demonstrate the rule**; an exception cannot sit loose among them, it has
to be labelled as the exception.

**And examples must show the language crossing.** Residents write English and
are answered in Hebrew by design, so a block whose example headers are all
Hebrew silently excludes every English message — `im stuck!!!` matched nothing
and fell through to the file's defaults.

**Every path in the WhatsApp prompt assumes the resident describes the
problem, and somebody in trouble cannot.** `im stuck!!!!` has no fault, no
place and no detail, so every rule keyed on what they said had nothing to work
with and produced the shortest sentence available. **A message can be urgent
and thin at the same time, and thin is not the same as uncooperative**: the
exclamation marks are the content. Asking such a person to describe what
happened is the worst available reply.

**And `where do you live` is a records question while `where are you now` is a
rescue question.** They sound alike and read completely differently: one says a
file is being opened, the other says somebody is coming. The prompt only had
the first, which is why every trapped resident got asked for their flat number.

**A prompt full of rules that cap a behaviour has no way to ask for more of
it.** Every warmth rule in the WhatsApp prompt was a ceiling — one containment
word per conversation, none is fine, not sorry yet, don't be shocked by a dead
bulb — all correct, all written against a bot that over-apologised, and
together they meant a resident who wrote that they were trapped got the cheapest
word in the language. **When a dial only turns one way, the answer is a floor
that scales, not another cap.** The scale now has a rung for when it happened
to the *person* rather than to a thing of theirs, and it is the rung the other
rules defer to.

**And raising helpfulness produces fabrication as a side effect, reliably.**
Told to care about the person and given a step reading "basic agreed
precautions", the bot invented a distress button and a guard post for a
resident stuck in a car park. Nothing in the file was false; the gap was
filled with something plausible. **Any instruction that widens what the bot
may offer needs a matching sentence about what it does not know** — here, that
it knows nothing about the physical building, and that caution is about the
resident's body, never about equipment.

**One block owns one decision, and a local exception cannot outvote a general
rule that is stated three times with examples.** On 31 Aug a hesitant resident
got a reply assembled entirely from approved text — the openers list, the
register table's good column, and the headline invitation example — while the
exception telling the bot to do the opposite sat once, fifty lines away, in
another section. Two rounds of adding rules changed nothing. The fix was to
move the exception **into** the block that owns the decision and delete the
rival, so there is one place to read and nothing to outvote. When a rule keeps
losing, look for the block that is beating it before writing it a third time.

**And a word approved in the general register cannot be un-approved from a
distance.** `אין בעיה` is blessed twice as ordinary spoken Hebrew; banning it
inside one branch did nothing. Scoping it where it is approved — it answers a
fact received, not a person who has just said something is hard — is what held.

**A ✓ example silently repeals a ✗ list.** The invitation block's first worked
example opened `בטח, אשמח לעזור` while `אשמח לעזור` sat on this file's own
list of things only a bot writes — and examples outrank rules at any distance,
so the ban lost on the most-travelled path in the file. When a ban keeps
leaking, grep the approved examples for it before writing the rule again.

**A contrast pair is not a sendable phrase; a written-out phrase is.** The
do-not-say rule has an exploitable middle: `"תוכל" מול "תוכלי"` never leaks,
because neither half is a message, while `תוכל לכתוב` sitting in the prose as
an example of the leak was sent to a resident verbatim. Teach the shape with
pairs or with a test the model can apply; never with the finished phrase.

**But strip examples only where the reply has to be tailored to the person,
and only where a single message is the whole conversation.** Ingredients — a
table of what to convey instead of a sentence — held for a first message and
dissolved three turns deep, where the model reverted to its defaults. Worked
examples survive context; tables do not. Where the two conflict, the reciting
is the smaller defect: similar reassurance to two residents beats a brush-off
to one.
This is the distinction, and getting it backwards makes things worse. Where two
residents would notice they got identical words — a hesitation whose *worry*
differs, an acknowledgement of what someone just told you — a fixed sentence is
actively wrong, and the fix is to replace the example with what the message must
**convey**: a table of content per case, and question *directions* rather than
question texts. Where the reply is generic by nature — declining an off-topic
question, which nobody receives twice — the single example is the only thing
carrying the register, and removing it leaves the model's own default, which is
corporate mush. Three pushes made that branch worse before it was put back.
**Recitation is a defect only where somebody would notice the repeat.**

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

**Nothing compiles the scripts, so run `python -m py_compile scripts/*.py`
before committing one.** `vapi_mock.py` was a `SyntaxError` for twelve days
from 18 Aug -- two comment lines lost their `#` -- and two later commits touched
the file without noticing. There is no test suite here and no CI step that would
have caught it; the only reason it surfaced is that a patch to the file failed.
A script in this repo is usually run by hand, months apart, which is exactly the
condition under which a broken one stays broken.

**One real value, one env var, everywhere.** The office line is 077-6687949 and
it is read from `HOMIES_CALLBACK_NUMBER` with that as the fallback -- in
`dashboard/lib/call.ts` and now in the four Python scripts that used to hardcode
`03-1234567`. A placeholder is safe in a simulation and dangerous in
`vapi_call.py`, which dials for real, and the two look identical in a diff.

**Hebrew is the product; the English twins are not.** Owner's direction,
30 Aug: work the Hebrew and leave English alone — the two operate differently,
so a change reasoned out for Hebrew prosody or Hebrew grammar does not become
an English change by translation. This overrides the older instinct to keep the
pair in step sentence for sentence. The twins are frozen comparison instruments
that nobody outside this project hears; `parity()` still runs on them and still
passes structurally, which is all it was ever asked to do. Related:
[[hebrew-is-not-a-translation]] — carry the meaning, then pick the words that
language really uses.

**A fact the agent reads aloud is stored in its spoken form, not its written
one.** A phone number goes in the prompt as `אפס שבע שבע, שש שש שמונה, ...`,
never as `077-6687949`; an email as `אופיס, שטרודל, ...`, never as an address.
The model is told to hand these over verbatim, so whatever form the prompt uses
is the form that reaches the voice — and a numeral does not reach it intact.
Vapi's formatter cuts any number above `numberToDigitsCutoff` (default 2025)
into single digits separated by full stops before the voice sees it, and our own
tail pad then adds 300ms after each one. That is what broke the office number on
30 Aug. `vapi_mock.py` had used the spoken form for the verification email since
long before, with the reason written next to it; nobody had carried it across.

**The pad is not the bug, but it doubles one.** `PAD_RULES` in `voice_guard.py`
appends 300ms to every chunk ending in a full stop, and it earns its place —
Cartesia leaves 43-135ms of tail and the teardown lands inside the last word
without it. It also amplifies anything that produces many small
sentence-ending chunks. When a turn sounds slow, find what is generating the
full stops before touching the pad.

**Punctuation in a voice prompt is performed, not read.** Every comma is a
pause the voice takes and every full stop is a falling ending, so what looks
like a formatting choice in the text is a timing instruction in the audio. This
has now bitten twice: prose in Aug (a sentence synthesised in pieces, each with
its own ending) and digits on 30 Aug (`1, 0, 0, 1` heard as four separate
words with gaps, reported as "very slowly and bugging"). **Write the punctuation
you want to hear.** Digits run together inside a group, one comma between
groups, never a full stop inside a number. A rule that says "say it clearly"
and a rule that says "put a comma after each digit" are not the same rule, and
the second one is the only one the voice can obey.

**A number that is a quantity is a word; a number that is an identifier is
digits.** Apartment 12 is דירה שתים עשרה and 450 is ארבע מאות וחמישים
שקלים; a reference or a phone number is digits. The intake prompt had the
apartment on the wrong side of that line until 30 Aug.

**The same is true of the voice agents' opening, and only grep keeps the
copies together.** The spoken first line is a fixed string Vapi plays before the
model is invoked, so no prompt rule reaches it. On the Hebrew side there are
three: the `## First message` fence in `docs/assistant/demo-inbound.md`, the
`### הפתיחה` blockquote in `docs/features/10-debt-followup/prompt.md`, and the
`"first"` string in `scripts/prompt_probe.py`, which opens every probe run and,
left stale, scores a conversation the agent no longer has. All three are silent
when wrong. Grep the old line before declaring the change done.

**Nothing on the English side forces a touch, and believing otherwise cost an
edit on 30 Aug.** `vapi_en.py` carries a substitution table that used to refuse
to ship a twin whose Hebrew had moved. `englished()` has short-circuited to the
frozen files under `docs/assistant/en/` since 25 Aug, so that table has not run
since and guards nothing.

**The voice's gender and the prompt's gender are one change, and it has now
been argued in both directions.** Hebrew marks the speaker's gender on the
verb, so a male voice reading `מדברת` is a grammatical error in every sentence
the agent has, not a stylistic mismatch. Feminine until 7 Aug (voice Leah,
מיכל), masculine since (Cartesia "Eyal", מיכאל) at the client's request. A line
arriving in the wrong gender is a slip to raise, not a decision to infer — the
cost of guessing wrong is nine passages and a voice swap.

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
none of them are in the agent's memory** — and that list is the *entire* extent
of word-matching in this system. There is no intent classifier and no keyword
routing on anything a resident says; every other decision is the model weighing
prose against prose, which is why a behaviour only changes when its rule beats
the text around it rather than merely existing, and the model met `אין לי` as the
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

**"OXS is read-only" stands, and the night it was briefly breached is the
reason it now has teeth.** A ticket mirror (open_request → POST
/service-calls) was built, tested against the live API, and deployed on the
strength of a capability question — which is not consent, as the owner made
plain within the hour: *"i told you not to do any shit to oxs."* The mirror is
OFF and stays off: a plain function deploy deletes its key, and only the
explicit `--oxs-mirror` flag enables it. **A standing rule is reversed by an
answer that could not mean anything else, never by momentum** — and when a
promised safeguard turns out not to exist (the "dummy building" — there are
none), the work stops and the question goes back, rather than the safeguard
being quietly downgraded. The dormant machinery is documented in HANDOVER; its
mirror and the importer's reflection-skip are one mechanism and may only be
enabled or removed together. What remains true either way: the API refuses
write-scope keys for every module except service_calls, and the old docstring
asserting "no writes exist" outlived the API that made it true — a policy
carried in prose outlives its facts.

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
answers it with no model call and there is nothing there to phrase. As of late
26 Aug all three taps are answered that way: "לדבר עם נציג" was the model's,
and after the third prompt round failed on the same turn in one evening, the
turn moved into the workflow instead of getting a fourth rule — a routing turn
the model keeps fumbling is evidence the turn was never the model's to phrase.

**A worked example that matches the input verbatim beats every instruction
around it.** The tap "לדבר עם נציג" was answered with the greeting glued to
the fixed transfer line — the exact shape of a first-message example in the
prompt that listed "רוצה נציג", against a mid-thread note in the same message
and a transfer rule 600 lines down that forbade both halves. The model did not
misread the rules; it found a closer match. So examples are held to every rule
in the file, including the rules of other sections: an example that a section
elsewhere would reject is a defect *now*, not when it fires. Same family as
"the exception lives inside the rule it overrides", one step earlier — the
example IS the rule the model reads first.

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

## Moving Vapi accounts

`docs/handover/new-vapi.md` is the procedure and `scripts/vapi_transfer.py` runs
most of it. Two rules survive every move:

**The script's file list is always one move behind the repo.** `ID_FILES` is a
hand-maintained list, and a file that hardcodes an assistant id but is missing
from it keeps pointing at the old account while the run reports success. The
30 Aug move found three such files after the fact. So the last step is never the
script: **grep the outgoing ids across the repo yourself**, and add whatever you
find to `ID_FILES` before you forget. A wrong assistant id does not error — it
starts a call with the wrong agent, on an account nobody is watching.

**Environment variables in a hosting dashboard do not travel, and guessing at
them is not the same as reading them.** A move that changes `.env` and the code
leaves a host's own variables untouched, and an env var *wins* over the constant
beside it, so a stale hardcoded fallback stays invisible until the day somebody
unsets the variable — which is why `dashboard/lib/call.ts` is worth keeping
right even when nothing reads it.

But read the host before warning about it. On 30 Aug this warning was issued
about the dashboard's Call button and was wrong: `VERCEL_API` in `.env` lists
both projects, and `homies-dashboard` holds no Vapi variables at all — no
`CALL_PIN`, so the button does not even render. `VERCEL_TOKEN` beside it is dead
(403 `invalidToken`); `VERCEL_API` is the working one.

**A copy is not a rebuild, and the difference is the point.**
`vapi_transfer.py` reproduces what **is** live; `vapi_sync.py` pushes what the
repo says should be live. Those differ whenever a prompt has been edited without
a push — both Hebrew prompts were a few hundred chars behind on 30 Aug — and a
migration is the wrong moment to discover it. Copy to move, sync deliberately
afterwards, never as a side effect.

## Somebody else's voice

`ido-voice.mp4` is a real person speaking for three and a half minutes, and the
clone built from it will answer residents under a different name. Three
decisions stand around that, and none of them is about audio quality.

**Consent gets written into the repo, not remembered.** Ido agreed on 30 Aug and
that sentence is in `voice/README.md`. Permission for something like this
otherwise lives in one person's head and leaves when they do, and the next person
to find a stranger's voice in a repository should find the answer beside it
rather than have to go asking. The clone is named **Echo Stone** on Cartesia
rather than "Ido", and `access[type]` is set to `private` explicitly: a codename
on a vendor account costs nothing and is one fewer place his name sits.

**Recordings are ignored by extension, including containers — never by
filename.** This was learned twice. On 5 Aug `New Recording 154.m4a (1).mp4`
turned up untracked and unignored and missed a commit by minutes; the fix written
that day added `New Recording*` and `*.m4a*`, patterns that match *that file*.
The same day `ido-voice.mp4` arrived, matched neither, and sat one `git add -A`
from GitHub for 25 days until a `git status` run for an unrelated reason caught
it. The comment above those patterns even said "the extension alone does not
catch it" and then omitted the extension. **A rule written against the last
accident catches the last accident.** `.gitignore` now covers the audio
extensions plus `*.mp4 *.m4v *.mov`, because a voice recording arrives in
whatever wrapper the sender's phone chose.

Once a recording is in a repo's history, removing it is a rewrite rather than a
delete. That asymmetry is the whole reason these rules are strict.

## A measurement you wrote yourself is a hypothesis, not evidence

Chasing the clone's intonation, I wrote a pitch tracker and it reported a p10-p90
spread of 177 Hz around a 126 Hz median, which would mean Ido swings across an
octave and a half while speaking. That is a striking number and it was my bug.
The upper hump sat against the tracker's own 320 Hz ceiling, which is what a
railing autocorrelation looks like, and the test that settled it was contiguity:
a person who raises their voice does it for a whole word, so real high pitch
arrives in runs of 20+ frames. **99% of mine were 1 to 19 frame flickers** —
octave errors, not speech.

The rule: before believing a number your own code produced, find the check that
would expose it as an artefact and run that. A histogram that looks bimodal, a
distribution pressed against a search boundary, an effect that appears in every
sample equally — each has a cheap test. Skipping it turns a bug into a finding
and sends the next hour somewhere useless.

**And know when measurement is spent.** Three theories for that intonation fault,
three refuted, and the client heard the problem in seconds each time. Duration
tells you a clip came out short, never that a word was clipped or that a
contour is unsettling. When the instrument cannot see the fault, stop building
instruments and ship the comparison to the person who can hear it.

## Cut a cloning clip on pauses, never on round numbers

The first clone of Ido truncated words, and the client heard it immediately. The
cause was not the model. `clone-candidate-a.wav` was cut 162s to 172s because
those were the loudest ten seconds, and a window chosen that way opens and closes
wherever it happens to land: that one opens on a 0.15-second fragment of a
syllable and runs off the end mid-phrase. **An instant clone learns the clip it
is given, including how the clip begins and ends.** Feed it clipped speech and it
produces clipped speech.

So the selection rule is a boundary rule first and a level rule second: map every
pause in the recording, keep only windows that **start and end inside a pause**,
and score those on level. On this recording, 55 pauses left exactly three usable
windows. Where one window is too short, join two pause-bounded ones rather than
extending a single one to a target length; the seam is silence to silence, which
is a breath, while a trim to fit puts the mid-word cut straight back.

**And do not judge the result by duration.** Duration told us v1 came out short,
which is a hint, and it cannot tell a clipped word from a brisk one. The client
heard the fault in seconds and no measurement here had flagged it. Ship a
listening page and ask a person; the numbers are for narrowing down which clip to
try next, not for deciding.

## Whoever owns the key owns the voice

Ido's clone (`61e911a7-…`, "Echo Stone") was made on **the client's own Cartesia
account**, because ours cannot clone and theirs can. Three consequences, and they
are the kind that are obvious in hindsight and expensive in advance:

**A cloned voice is private to the account that created it.** It cannot be listed,
played or synthesised with any other key, which is why `voice_clone.py` and
`cartesia_tts.py` both take `--key VAR` now. `--key` names the **variable**, never
the key, the same convention as `vapi_transfer.py --to`.

**Vapi needs its own copy of that key, so the clone is unreachable until someone
moves the credential.** Vapi synthesises server-side and currently holds *our*
key. Pointing it at the client's key would make the clone work and would also move
**every** Hebrew utterance, both agents, onto the client's bill — not just the
cloned one. That is a commercial decision, not a configuration step, and it has
not been made.

**Ask before touching a client's account, every time.** Homies approved this clone
explicitly on 30 Aug. The rule that a capability question is not consent is why
the finding "their key can clone" and the act of cloning on it were two separate
turns.

## Ask the API and read the price list

A vendor's feature documentation is not a statement about your account. Cloning
sat unbuilt for three weeks on a $49/month figure that came from third-party
write-ups, next to a note reasoning from Cartesia's docs that it might be free —
two guesses in opposite directions, neither checked against anything.

`/voices/clone` answers the question in one request: `402
plan_upgrade_required`, on 7 Aug and again on 30 Aug. The seller's own price page
answers the rest: instant cloning is the **$5/month Pro** tier, and the $49
Startup tier buys *professional* cloning, a different feature needing thirty
minutes of audio. **A $49 line item gets deferred; a $5 one does not**, so the
wrong number did not just sit there being wrong, it decided something.

**And there is a way to ask that creates nothing.** Send the request deliberately
malformed — a clone with no file attached. A plan-gated account rejects it at the
gate (`402 plan_upgrade_required`); an entitled one gets far enough to complain
about the missing file (`400 No file was provided`). That one distinction is what
found the client's account could clone when ours could not, and it cost nothing
and left no trace. Prefer it to "try it and see", which on a write endpoint means
creating something on somebody's account to find out whether you could.

The general form: when a capability might be plan-gated, spend the one request
that returns the real error, and read the price list rather than a feature page.
The same rule caught the opposite error on 30 Aug, when "Cartesia publishes no
balance" turned out to be false — a synthesis call answers "is there credit"
even though nothing answers "how much".

## A minimum and a maximum look identical in a sentence

Cartesia's guide says a voice clone can be made "with as little as 10 seconds of
audio". On 5 Aug that became `MAX_SECONDS = 10.0` in `scripts/voice_clone.py`,
and a docstring calling the 220-second source recording "22x over instant
cloning's 10-second limit". It is a **floor**. They accept up to sixty seconds.
For three weeks every clip was cut to exactly ten seconds and 210 seconds of a
220-second recording were thrown away on each attempt.

Nothing caught it because nothing could. The number was in our own repository, in
a comment block explaining at length why it mattered, and every later reader
(me included) treated it as settled fact and reasoned forward from it. **A
constant you wrote yourself reads like evidence and is only ever a claim.** The
owner found it by asking why a three-minute recording was being used ten seconds
at a time — a question about the shape of the thing, which no measurement in the
repo was capable of asking.

**It had an accomplice.** `sonic-3.6` — Cartesia's current model, which speaks
Hebrew — appeared in no file here before 31 Aug, because a 30 Aug probe guessed
six model ids and missed it, then reported "only sonic-3 and sonic-preview accept
Hebrew". That conclusion was about the guess list, not about Cartesia. **A probe
over a list you invented measures your list.** And the two errors protected each
other, because "only Sonic 3.6 uses reference audio beyond 10 seconds": a longer
clip on the old model changes nothing audible, so testing either fix alone would
have looked like a dead end and confirmed both mistakes.

So: when a number decides an approach, re-read it at the source before building
the third attempt on it, and when a probe comes back negative, ask whether it
tested the world or your own list. Related: [[Ask the API and read the price
list]] and [[A measurement you wrote yourself is a hypothesis, not evidence]].

## A dry run tells you what the repo wants, not what is live

`python scripts/vapi_sync.py debt` printed a cloned voice id on 31 Aug while the
live debt assistant was on Eyal and had been all along. Both statements were
true: the dry run reports what `--apply` *would* push. Reading it as the live
state is how you verify a claim about production against a file on disk.

Verify "nothing was changed" against the provider's API. `GET /assistant/<id>`
and read `voice.voiceId`. It is one request and it is the only thing that
actually answers the question.

**The same read found a live hazard.** `vapi_sync.py`'s `cloned_voice()` prefers
`CARTESIA_VOICE_ID` over the stock voice, so setting that variable "ready for
later" armed `--apply` to put a twice-rejected clone onto the production debt
agent — and it would have failed silently rather than loudly, because the clone
is on the client's Cartesia account while Vapi's credential holds our key, so
Vapi falls through to Elliot and a Hebrew agent speaks with an American accent
while logging nothing. The variable's own docstring had said the safe state is
*unset*: "with the variable absent this function changes nothing at all, so
--apply stays safe to run". **Do not pre-load a variable that overrides
production; leave it unset until the thing it names has been accepted.**

## The WhatsApp builder can no longer push, and that is the safe answer

`scripts/n8n_whatsapp.py` builds the workflow and ships it with a PUT, and a PUT
is a replace. Since the Chatwoot cutover on 21 Aug the live workflow has carried
nodes that script does not build — the human handback, the promise backstop, the
tap transfer, the two typing-indicator Waits — all applied through the REST API
and never brought back into the builder. On 31 Aug that was **35 live against 21
built**, and the script's own guard refuses the push rather than silently delete
fourteen nodes that are serving residents.

**The guard is not a bug to work around.** The correct long-term fix is bringing
the builder back up to date so it is the source of truth again. Until then,
changes to the live bot are surgical: read the live workflow, change only the
named things, leave every other byte as found, write it back. That is what
`scripts/n8n_whatsapp_patch.py` is, and it is idempotent on purpose — the thing
it edits is live, so the obvious way to check whether it worked is to run it
again.

**A consequence worth stating plainly: the repo is not the bot.** After a
surgical patch, `n8n_whatsapp.py` describes something that is not live and the
live workflow contains things no file describes. Anything asserting "the bot
does X" has to be read off the live workflow, not off the repo.

## State moves while you are describing it — re-read live before you assert

On 31 Aug the WhatsApp bot's status was written into the briefing files twice and
was wrong both times, from evidence that was minutes old.

A dry run showed 35 live nodes and the follow-up menu still present, so HANDOVER
got a table headed **UNAPPLIED**. That table was already false when it was
committed: the live workflow had moved to 33 nodes, prompt 47,219, temperature
0.3. Nobody in this session ran `--apply`. Separately, the patch script itself
was being rewritten on disk while the session ran — a 126-line copy that parses
but has an empty `main()` got committed in `a5c4983`, in place of the 184-line
copy that had dry-run correctly minutes earlier.

**So a repository under a live session is not a still photograph, and neither is
the production system it talks to.** Three rules follow:

1. **Re-read the live system immediately before writing a claim about it**, not
   at the start of the work. A node count, a prompt length or an "unapplied" is
   a reading, not a fact, and it decays.
2. **Stamp readings with their timestamp** and never carry one forward. Every
   table in HANDOVER describing live state should say when it was read.
3. **Verify what you committed, not what you edited.** `git show <sha>:<path>`
   costs one command. A file that parses is not a file that works, and "I
   repaired it" is a claim about a version that may no longer be the one on disk.

**And do not explain away an anomaly with the nearest available theory.** The
mangled string literal in that script was blamed on my own heredoc escaping,
because I had genuinely hit that bug twice the same hour. The likelier cause was
that something else was writing the file. A familiar explanation that fits is not
the same as the right one — the same error as the octave-error pitch tracker,
one day apart. Related: [[A measurement you wrote yourself is a hypothesis, not
evidence]] and [[A dry run tells you what the repo wants, not what is live]].

## The platform's allow-list is narrower than the vendor's catalogue

Cartesia offers `sonic-3.6`. Vapi will not run it. A PATCH setting it on a Hebrew
assistant is refused: *"voice.model must be one of the following values for he
language: sonic-3.5, sonic-3.5-2026-05-04, sonic-3, sonic-3-2026-01-12,
sonic-3-2025-10-27."*

This mattered more than a version number usually does. `sonic-3.6` is the only
Cartesia model that reads a reference clip past ten seconds, so the whole point
of cutting a 55-second clone — the fix for two rejected voices — **cannot be used
on a live agent at all**. The repo had been tuned end to end for a model the
runtime does not accept, and nothing said so until the write was attempted.

**So when a vendor capability has to travel through a platform, ask the platform
what it accepts before building on the vendor's answer.** The vendor's docs
describe the vendor. And note what saved this: the PATCH was refused cleanly, so
both assistants were left untouched. A silent partial apply here would have left
one agent on a new voice and one on the old with no error to read.

**The consolation was also something never tried.** `sonic-3.5` is on the
allow-list and had been rendered nowhere in this repo, because the model probe
that missed 3.6 missed it too. It does not rush the way `sonic-3` does. A probe
over a list you invented measures your list — recorded twice now, one day apart.

## A provider credential is a billing decision wearing a config field's clothes

Vapi synthesises server-side, so it holds its own copy of a Cartesia key. There is
one, `Cartesia (Hebrew TTS)` (`448aa856`), and **both** Hebrew assistants use it
while the English twins use `provider: vapi` and touch Cartesia not at all. So
that credential is not "the Hebrew voice's key". It is the entire Cartesia bill.

Repointing it to the client's account on 31 Aug was the only way to put Ido's
voice on an agent — a cloned voice is private to the account that created it, and
ours answers `402 plan_upgrade_required`. But it moved every Hebrew utterance
both agents will ever speak onto the client's bill, not just the cloned one, and
the client had approved their key for *cloning*, not for carrying production
traffic. That is a decision for the owner, and it was put to them with the
alternative priced ($5/month Pro on our account, then re-clone there) rather than
taken as a step inside a voice change.

**The general form: before editing a shared credential, work out everything that
authenticates through it, and say who pays afterwards.** Then check the rollback
is one command before you make the change, not after.

## When someone is stuck, narrow the question rather than widen it

Added to the WhatsApp prompt on 31 Aug and live the same day. A resident who says
"I'm not sure it's worth bothering you" has already told you the hard part is
starting. Answering that with "share whatever you're comfortable with" sounds
generous and is the opposite: it is an open question handed to the one person who
has just said open questions are what they cannot answer. "אין בעיה" is in the
same family — it reassures nothing and moves nothing.

What works is three moves in one message: **the worry he actually voiced is
heard**, **its cost is lowered** in one sentence, and then **one question
answerable in two words** — in the flat or the common area, did it break or is it
just bothering you, was it today. Two words is enough to work from, and asking
for them is the agent taking the step instead of waiting.

**Answer the worry he said, not the set of worries people have.** There are three
common ones — it is too small to bother anyone, it involves a neighbour, it is
embarrassing and who will read it — and they need different sentences. Reassuring
someone worried about a neighbour that "even small things matter" answers a
concern he never raised, and reads precisely like not having been read. **If it
is unclear which one it is, ask the narrow question on its own: guessing the
wrong worry is worse than not guessing.**

The door-left-open line ("if you feel like sharing later, I'm here") is correct
*after* those, never instead of them. On its own it closes the conversation while
sounding like it is keeping it open, and someone who already hesitated does not
come back.

**And the worked example in the prompt is marked as an example on purpose.** A
fixed phrase is one the model will say back word for word, which the same prompt
forbids elsewhere — the rule that a sentence already sent is never sent again
exists because repetition is how a person works out they are talking to a
recording. This is the same trap that put a feminine-inflected `אֵלַיִךְ` in front
of a male caller on the voice agent: the model reproduced the prompt's own worked
example, gender and all.

## The voice prompts

**Verify a push by reading the assistant back, never by trusting the write.**
`vapi_sync.py --apply` printing OK means the PATCH returned 200, not that the
assistant carries what you meant. GET it afterwards and compare the system
prompt against the repo, count the tools, and check the guard replacement count
— the 3 Aug Model Presets incident and the 12 Aug dashboard reversal both
changed live assistants behind the repo's back, and neither showed up in a
push's own output.

**And normalise whitespace when grepping Hebrew prose for a rule.** These
prompts are hard-wrapped at 80 columns, so a phrase that reads as one string on
the page is split by a newline in the file. A contiguous-string check reported a
live rule as missing on 30 Aug. The same error in the other direction would
report a missing rule as present, which is the dangerous half.


**A whole-object `--apply` pushes everything the tool believes, not the change
you made. Learned 31 Aug by breaking it.** Pushing the inbound prompt with
`vapi_sync.py --apply` silently reverted Ido's cloned voice to the Eyal id
hardcoded in that script, an hour after another session had put the clone live.
The prompt half was verified and correct; nothing checked the fields that were
not meant to change. **With two sessions on one account, every whole-object
write is a clobber risk** — prefer a surgical patcher that touches one field and
reads back (`vapi_set_voice.py`, `n8n_whatsapp_patch.py`), and after any
whole-object write verify the fields you did NOT intend to touch.

**And do not trust a tool's own label for a fact it is asserting.** The dry run
printed `voice: cartesia a976c076… (cloned)` and that voice is stock Eyal. The
word "cloned" was a hardcoded string next to a hardcoded id, agreeing with
nothing.

**An indented example is an instruction to say the line inside it. Decided
31 Aug.** No disclaimer above it changes that — WhatsApp proved it there first
(*"saying 'not a fixed formula' next to a complete sentence does not stop the
sentence being sent"*) and the voice prompt reproduced it. **To stop a sentence
being said, delete the sentence; to keep a behaviour, state it as required
content and let the words be free** — `זה תוכן ולא נוסח`. **Negative examples are
free** and should stay: a banned wrong sentence has no right line beside it to
copy, so it costs nothing in variety.

**And openness is paid for in safety, on this agent, every time.** Freeing the
phrasing on 31 Aug immediately produced a misgendered caller (`איפה את גרה`) and
silently stopped `transfer_to_human` firing on a trapped person, while a
templated agent had done both correctly for weeks. **The fixed phrasings were
holding the rules.** Neither was recoverable by adding a ban: what worked was
removing the need for the risky construction at all — asking where the *fault*
is rather than where *they* live has no second-person verb to get wrong. **Prefer
a structural fix that makes the error unsayable over a rule that forbids it.**

**Measure a proposed prompt, do not argue with it. Decided 31 Aug.** A rewrite
arrived with a confident diagnosis — constraint overload, the model freezing —
and `prompt_chat.py --file` settled it in ten minutes and about thirty cents: it
failed both emergency cases, one of them reproducing the exact complaint that
started the work. **The claim was plausible and the evidence was cheap**, which
is the whole argument for owning an instrument.

What it showed is worth more than the verdict. The candidate stated the
tool-first rule in *clearer* prose than ours, with none of the surrounding
constraints, and still did not fire. **Prompt length and negative phrasing were
not the variable.** The behaviour comes from the worked example and from saying
that a hedged report counts; strip those and a shorter, friendlier, better-organised
prompt does the wrong thing on a gas leak.

**Never add a worked example to a section that already has one — change the one
that is there. Learned 31 Aug, the hard way.** Four separate failures in one
session came from examples competing: an emergency section ended up carrying
three, and the model produced the nearest two spliced together, dropping the
emergency phone number that lived only in the furthest. Each attempted fix added
another example and made it worse. Collapsing them to one complete example fixed
it and left the section shorter than before. **Count the examples in a section
before writing a rule for it.**

**And a hedge defeats a trigger list.** *"I think there is a gas leak"* produced
no written request while *"I am stuck in the lift"* was handled perfectly, from
the same list, in the same run. A list of emergencies reads as a list of
confirmed facts unless it says otherwise. Any classifier written as a list of
nouns needs a line saying that a suspicion counts.

**A rule lands where the example lands. Learned 31 Aug.** An anti-parroting rule
written as a paragraph after the politeness list changed the output by nothing at
all — the echo came back word for word. Moved directly under the worked example
that produces the behaviour, and written in that example's own `לא:` / `אלא:`
shape, it took immediately. **The model copies the nearest example, not the
furthest rule**, so a rule that contradicts an example must be placed against that
example or it loses. The same session showed the other half: a care rule in its
own section never reached the emergency path, because that section carries its own
complete procedure and a caller in a lift is handled entirely inside it. **A
cross-cutting rule has to be repeated inside every branch that has its own
procedure**, or it governs only the calls that fall through to the default.

**A guard that cannot be satisfied is not a guard, it is a wall, and the model
works around walls. Decided 31 Aug.** `check_briefing_logged.sh` spent four
turns blocking a session that had already committed its briefing files, because
it reads the uncommitted set and committing is what empties it — and the only
uncommitted work belonged to a second session sharing the checkout, so the sole
way to clear the block was to commit somebody else's unfinished work. The cost
of a guard being too lax is one late reminder. The cost of it being
unsatisfiable is that the next session learns to route around it, and then it
protects nothing. **Every blocking check needs an escape that a compliant
session can actually reach**, and "the last commit already did it" is usually
that escape.

**And a check that assumes it is the only writer will eventually be wrong.**
Two sessions in one checkout is now normal here, so anything fingerprinting the
working tree is fingerprinting other people's typing too.

**Probe a large prompt change before pushing it. Decided 30 Aug, after it paid
for itself the first time it was used.** `scripts/prompt_probe.py` costs cents —
about $0.22 for a three-scenario before/after pair — and caught three
regressions in the refactor that all three static checks passed clean. Static
checks prove the prompt still extracts, still contains its facts and still
survives the voice filter. **None of them can tell you the agent stopped
confirming the address.** **And a probe is only as good as what it prints:
`prompt_probe.py` shows tool NAMES, so a hand-off that goes out with an empty
`description` is invisible to it. `scripts/prompt_chat.py` prints the arguments,
and found exactly that on 31 Aug.** Money-spending still needs the owner's word each time;
the recommendation is to ask for it on anything over about 20% of the prompt.

**A rule stated as an abstraction fails where a wrong-answer-beside-the-right-one
succeeds.** Both regressions I was most confident about were abstractions I had
written to replace a concrete pairing. *"The tool returns a number in three
parts, say the middle"* produced an agent that read all three; the old
`כן: … / לא: …` pair did not. This does not contradict the rule above it —
worked *examples of a question* leak into unrelated questions and must go; a
worked example of a **format** is the only thing that reliably pins a format.
The distinction is whether the example is something to imitate or something to
match.

**And "write it and move on" is heard as permission to skip.** Any instruction
to be faster needs the thing it must not drop named in the same breath, or the
model drops the most skippable-looking step — which was the address
confirmation, the one turn standing between a technician and a stranger's door.


**A prompt is not its own changelog. Decided 30 Aug, and it is rule 5 with
teeth.** The inbound prompt had grown twenty-five paragraphs that state a rule
and then narrate the call that produced it. That reads as institutional memory
and behaves as a script: a model given a record of past mistakes writes
carefully, in the shape of the record. `vapi_sync.py` ships only the
four-backtick fence, so the narratives moved *below* it and lost nothing. **When
a rule needs its story to be followed, write the rule better — do not put the
story back.**

**Worked examples are a liability in a prompt that must generalise.** The prompt
listed *"מה היה בתיק?"* as a follow-up example and the agent asked *"מה היה
בנזילה?"* — not Hebrew, and four times out of four on 26 Aug. It was reaching
for the nearest-shaped sentence rather than deriving a question from the fault
in front of it. Name the *kind* of thing to ask and let it compose.

**A line stays verbatim only when something mechanical depends on the exact
characters.** In the inbound prompt that is three: the closing sentence, because
`endCallPhrases` matches on it and `endCallFunctionEnabled` is false, so the
words *are* the hang-up; the emergency-services numbers; and the tool waiting
lines, which live in config rather than in the model. Everything else is content
the agent phrases itself.

### The facts about Homies live in one file

`docs/knowledge/homies.md` is the master for the thirteen facts both channels
state — hours, contacts, what the ועד fee covers, payment, response times, the
common-versus-private property line. **Edit there first, then the two prompts,
then run `python scripts/facts_check.py`,** which fails when they drift.

The copies are deliberate and cannot be collapsed: the WhatsApp bot ships
through n8n and the voice agent through `vapi_sync.py`, and they do not want the
same characters. `077-6687949` is correct in a chat window a resident copies
from and is the exact input that broke the voice on 30 Aug. Seven of the
thirteen therefore carry a written and a spoken rendering; six are ordinary
Hebrew and carry one.

**Policy may be stated; a promise may not.** This is the line that lets the
agent answer at all. *"תקלות חירום עד ארבע שעות, השאר עד שלושה ימי עסקים"* is
the standard and is sayable. *"יטפלו בזה עד מחר"* is a commitment somebody else
has to keep, and a question about a specific request is answered from
`get_request_status` and nowhere else.

**Vapi's built-in knowledge base is not used, and the trigger for changing that
is a corpus rather than a preference.** It exists — hosted v2, custom, and the
legacy model field — and for thirteen facts it buys nothing: it is a round trip,
Hebrew retrieval is unmeasured and fails quietly as *"אין לי את הפרט הזה"* about
a fact we hold, a Vapi-hosted base cannot serve the WhatsApp bot, and the four
rules governing the facts stay in the prompt regardless. Revisit when there are
contracts, house rules or per-building documents.

**The configuration table in `demo-inbound.md` is a reading of the code and goes
stale silently.** Three rows were wrong on 30 Aug — the transcriber by eighteen
days, the recording flag, and the tool count. A document cannot fail a test.
Read the dry run against the code, not against the table.


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

**A guard must key on the claim, not the artifact.** The phantom-ticket
guard fired on the SHAPE of a reference, and every honest status reply quotes
one — so the guard replaced correct answers with rescue tickets for three
days before anyone saw it. The claim it exists to catch is "I opened a
ticket"; the artifact is the number. Any backstop written against a pattern
that legitimate output also produces will eat legitimate output, and it will
do it silently, because the backstop's own success looks like the system
working. Key the trigger on the act being claimed, and keep a probe in the
suite that runs the GOOD case through the guard.

**A duplicate is a merge, not a discard.** The 30-minute ticket guard was
designed so one leak gets one van, and for months its answer to a second
report was to hand back the old reference and drop everything else in the
message. That is half a design: deciding two reports are one event without
deciding where the second report's NEW FACTS go. A resident who elaborated
twenty minutes later left no trace (27 Aug, the elevator ticket), so now the
duplicate path appends what is new and skips what is already held. The rule
generalizes: any dedup that survives a row must route the loser's information
into the winner, or the system trains people that elaborating is pointless.

**Enforcement must count already-enforced as success.** The plain-deploy step
that deletes the OXS key aborted on 404 once the key was already gone — and
took the entire function deploy down with it, silently, from the second run
onward. A guard that fails when the state it wants already holds is a guard
that breaks the pipeline it protects. Idempotence first, then loudness.

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

**Destructive database changes go through the migration ledger, not raw
REST.** Migration 027 (the 27 Aug test-ticket purge) set the pattern: survey
row-by-row first, write the delete as a numbered migration whose comment says
what the populations were and why one goes, apply via `supabase_migrate.py`.
The repo then carries a permanent, reviewable record of every destructive op
— which is also what makes such an op approvable at all. Same date, same
principle: `requests` is real-data-only now (`opened_via <> 'oxs'` means a
real resident or a new test), and test rows are cleaned up when a test round
ends rather than left to fossilize.

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

**When a provider hides the metric, probe the capability.** Cartesia
publishes no balance anywhere an API key can reach, and "dashboard only" was
the wrong answer to "is there credit left" — the cheapest real call answers
it: a two-word synthesis returns 200 while the account can pay and 402 when
it cannot, which is how the credit outage was diagnosed in the first place.
Prefer the smallest genuine operation over a status page; it tests the thing
that will actually run.

**Send a plain non-browser User-Agent to every provider API, or set none.**
Two providers now refuse Python's default: the Supabase Management API
("Forbidden use of secret API key in browser") and Vapi, which answers 403
`error code: 1010` — a Cloudflare browser-signature block, not an auth
failure, and it reads exactly like a dead key. `User-Agent: curl/8.5.0`
clears both. Before concluding a key is revoked, retry with that header; a
wrongly reported dead key sends somebody rotating credentials that work.

Long sweeps: run with `python -u` so progress is visible, and in the
background. OXS rate limits are **60 requests/minute per key**, and a
per-building payments call can return ~10,000 records — a full sweep is half
an hour, not five minutes.
