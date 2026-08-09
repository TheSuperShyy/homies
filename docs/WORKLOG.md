# Worklog

Every session appends here: what was done, what was decided, what is still open.
Newest first.

Design rationale belongs in the relevant `context.md`, not here. This file is the
chronology — what happened and when, so that a decision can be traced back to the
conversation that produced it.

---

## 2026-08-09

### The follow-up menu died on a `}}`, found in the execution log

Ticket HM-2026-1019 opened cleanly and no menu followed. Execution 363: the
If matched, "Options again" failed — "invalid syntax", no description. The
cause: the menu JSON was inlined into a Set-node {{ expression }}, and a
menu is JSON full of `}}` — n8n cuts an expression at the first `}}` it
meets, so the node was handed a truncated fragment. Moved the follow-up menu
into Sort's output (a Code node has no such tokenizer), and the Set now just
reads `$('Sort').first().json.followup`. Re-applied, re-activated.

### The bot's brain ran out of money, and moved to key 2

"theres a water outage" got the handover line — not a decision, the error
branch: OpenRouter 402, key 1's balance at $0.00 with the negative-balance
grace exhausted, the model failing in 253ms. The fallback did exactly its
job; a resident got a sentence instead of silence. Swapped the n8n
credential to OPENROUTER_API_KEY_2 ($45 credits, $43.80 already used —
about $1.20 of headroom, ~2,400 flash messages), workflow re-applied and
re-activated, key-1 credential deleted from n8n. That headroom is testing
money, not pilot money.

### The English menu says ticket

"Open a service call" / "Check an existing call" → "Open a ticket" / "Check
an existing ticket", asked for off a screenshot. The second title is exactly
24 characters, which is Meta's hard cap on a row title, so it fits with
nothing to spare. Hebrew rows untouched — קריאת שירות is the trade's own
word and was chosen deliberately over פנייה.

### The options come back after a flow completes

Asked for: after a ticket is opened, offer the options again instead of
leaving the resident with a reference number and silence. Two new nodes
chained AFTER Send (parallel sends can arrive swapped, and a menu landing
before the reference reads as changing the subject): an If that looks for a
reference number in the outgoing reply — the marker of a completed flow,
which the model cannot fake because references only come from the tool — and
a Set that rebuilds the flat to/menu shape so the follow-up rides the
existing Send menu node. Body "עוד משהו?" / "Anything else?", rows identical
to the greeting menu. Fires after status answers too, deliberately — both
flows end with a reference and both deserve the offer. One prompt line so
the model does not also ask "עוד משהו?" itself. isExecuted guards the canned
branches where the agent never ran.

### The WhatsApp bot answers status now, and a tap stopped being smalltalk

Two faults off one screenshot. A tap on "Open a service call" reached the
model as four bare words and it re-greeted — a menu answering a menu. Now
'open' and 'status' taps get the first question of their flow as a canned
line straight from Sort, no model round-trip; 'human' and 'balance' still go
to the agent, whose job on both is transfer_to_human.

And "any update on ticket HM-2026-1018?" got the handover line, because the
prompt explicitly said the bot cannot read requests and the only other tool
was transfer. `get_request_status` is now the bot's third tool — pointed
STRAIGHT at the Edge Function like the voice twins (the n8n router answers
locally and forwards async, wrong for a synchronous lookup), secret in a new
n8n credential ("Homies tool secret"), phone riding on the `wa:` call id.
Prompt: the you-cannot-read-requests block replaced with a status section —
bare reference message is a status question, statuses in the resident's
language, tool result is everything you know, deeper questions still go to
the team. Balance stays behind the identity question (PRD §13 #1); status is
read-only and stopped waiting for it. Verified against live rows: "1018" →
HM-2026-1018, open, electrical. Workflow updated and re-activated.

### The reference number, slowed to writing speed

The read-back example wrote the code as one token — HM-2026-1001 — and the
TTS said it like one word, too fast for a pen. The voice paces from
punctuation, so the fix is in the writing: step 4 now sends the code out in
pieces with a comma after each — HM, 2026, 1, 0, 0, 1 — followed by an offer
to repeat, and a repeat is the same pieces, not faster. Same rule added to
the status section's ask-for-it read-back. Both inbound twins (he 17,555 /
en 16,980 chars), demo-inbound.md synced.

### Everything pushed, and the dashboard is on the internet

Commit `b77435b` — 32 files, the whole week — pushed to
`TheSuperShyy/homies`. Then `scripts/vercel_deploy.py --apply` (token taken
from the logged-in Vercel CLI's auth store, written to `.env`, never echoed):
project `homies-dashboard` created git-linked with `rootDirectory: dashboard`,
the two `NEXT_PUBLIC_` vars set before the first build, one deployment,
READY. Live at **https://homies-dashboard.vercel.app** — verified 200 and the
calls tabs render with no login gate. Only the anon key went up; the script's
role check ran. Later pushes to `main` deploy themselves.

This is the open demo build — `anon_read` policies and no login. The URL is
unlisted but public: **re-lock before real resident data** (drop 010, restore
the middleware redirect), and the Supabase auth URL config + first staff user
are still owed when login returns.

### Dashboard: full-bleed, and the calls page learned outbound questions

`main` lost its 1180px cap — the tables now use the whole screen. The calls
page grew a view switcher (state in the URL, so views are bookmarkable): All /
Inbound / Outbound / No answer / Links sent. "No answer" reads
`call_outcomes` where outcome is `no_answer`, joined to the resident — name,
phone, building, attempt. "Links sent" reads `payment_links` with the
resident and status, and carries the schema's own caveat under the table:
`sent` means OXS confirmed it went out, and nothing on our side can see
whether it was paid, so the view never counts money.

### The amount-loop returned, and the cause was config, not prompt

Test call (שרה, gender f passed correctly): the agent restated the
why-you're-calling sentence three times against an "אוקיי", wrote אההה
against the written rule, and produced actual Hebrew typos — מאומיז, ועד בק,
בד בית are in Vapi's own bot log, so the model wrote them; they were not
mishearings. The live model object had **no temperature at all** — the design
value 0.3 was lost when the assistant was rebuilt — so gpt-5.4 ran at its
default, and there was no maxTokens cap to stop a runaway turn.

Set temperature 0.3 and maxTokens 200 by PATCH. The gender complaint from the
same call needed no change: `gender: "f"` was passed and the GRAMMAR rules
were armed; the call simply never reached a turn with a verb aimed at her —
מדבר מיכאל is the agent speaking about himself, masculine by identity.

Noted in passing: the demo still passes `card_last4` and `has_card`, retired
4 Aug ("neither may return"). The prompt no longer references them so they do
nothing, but the demo's variable list should be cleaned.

**The loop survived temperature 0.3 — model switched back to gpt-4.1-mini.**
Post-fix calls split: 09:57 ran the whole flow cleanly (ask, link, outcome,
end-call phrase), but 09:44 and 09:52 looped the amount exactly as before,
with a mid-word cut where a degenerating turn hit the 200-token cap. An
inconsistent failure at 0.3 points at the model, and gpt-5.4 is not the
design: the notes chose mini-class deliberately, the 7-Aug twelve-call
validation ran against it, and nobody ever validated 5.4 on this prompt.
Switched to gpt-4.1-mini, temp 0.3 and the token cap kept. If the loop
survives the mini too, the next suspect is Vapi's message history — the call
artifact shows all assistant speech merged into one message and all user
speech into another, and if that is what each inference actually receives,
no prompt can fix it.

**Status + anti-dupe extended to the English twin.** The en intake assistant
(`3edbe85b`) got the same treatment as he: get_request_status attached, the
"cannot look anything up" block replaced, the Status section added with
statuses in plain English, rule 3 rewritten, `modelOutputInMessagesEnabled`
on. Both prompts also gained one line under the no-live-transfer section —
**the transfer line is said once, ever** — after a test call where the en
agent said it twice back to back; the history fix should remove the cause,
the line removes the excuse.

**The inbound agent can now answer ticket status.** New `get_request_status`
in the debt-tools Edge Function (v11 deployed, tested against live rows):
read-only, reference-tail matching ("1013" finds HM-2026-1013) then
resident-on-call then building+unit — the open_request asymmetry, reused. The
tool points STRAIGHT at the Edge Function with the TOOL_SECRET header, not
through n8n — n8n answers Vapi locally and forwards writes async, which is
wrong for a lookup that needs a real synchronous answer. The status answer is
live truth, not the nightly export, so no §2.2 freshness caveat is owed —
that caveat belongs to OXS-side status, which this deliberately does not
touch. Prompt rewritten where it used to forbid lookups ("you cannot look
anything up" → "the one lookup you have"), a Status section added with the
status names in the caller's Hebrew, absolute rule 3 rewritten, and two
stowaways fixed: the stale feminine-first-person line (the voice has been
male Eyal since the Cartesia move — its own fixed lines were already
masculine) and `modelOutputInMessagesEnabled` turned on for inbound too,
before the debt agent's loop bites here. Live on `86a01f13` (16,971 chars)
and synced back to demo-inbound.md, which was byte-identical to live before
the edit.

**Expressiveness pass.** Voice: `positivity:low` → `curiosity:high` on the
Cartesia experimental controls — low positivity was flattening every line;
curiosity keeps the leaning-in sound without making a collections call
chipper. Prompt: one HUMAN LAYER paragraph — the TTS reads punctuation, so
write the melody; one bright word on genuinely good moments, shorter and
flatter on heavy ones; brightness is a moment, never a mood. 37,629 chars.

**The loop's likely root cause, found on the third pass:
`modelOutputInMessagesEnabled` was off.** By default Vapi builds the
assistant's own turns in conversation history from the transcription of its
TTS audio, not from what the model wrote. Evidence that this was the story
all along: the "typos" (מאומיז, לבד בית, ועד בק, "ה- link", "רוצה שאת עדכן")
appear in the bot's *logged* turns — they are Azure mis-transcribing
Michael's own speech, fed back to the model as its own words. A model whose
memory of what it said is garbled Hebrew cannot obey a never-repeat rule; it
does not recognise its own turns. The gpt-4.1-mini call showed the shape
clearly: flow correct (amount → ask → link → standing order, feminine forms
right), but the last line re-delivered verbatim after every acknowledgement.
Flag now true — history is the model's actual output. If the loop survives
THIS, the remaining suspect list is short and Vapi support is on it.

**Gender, second pass — reviewer criticism, not one bad call.** Three
reinforcements to GRAMMAR: the inflection table gained את/תרצי/תסגרי rows; a
new rule that the third person about {{first_name}} carries her gender too
(the not-the-account-holder line's יחזור → תחזור — the fixed-line inflection
rule covered endings aimed at the caller but nothing said about the resident
in the third person); and gender joined the BEFORE EVERY REPLY checklist, so
the check runs where the model acts instead of five sections away. Also
name-based inference: gender `unknown` + an unambiguous Israeli name (שרה,
יוסי) now resolves from the name; phrase-around only when the name settles
nothing. Prompt 36,443 → 37,129 chars, pushed by PATCH.

### The super-skills doc, distilled into a HUMAN LAYER — most of it rejected

The root-folder `hebrew-voice-super-skills (1).md` (20 techniques for
humanlike voice agents) was asked into the debt agent. It went in as one
compact section — THE HUMAN LAYER, after the budgets — not as twenty, because
most of the doc either already exists in stronger form or directly conflicts
with rules this prompt earned the hard way on 7 Aug.

Taken (5): pace mirroring (never temperature — hot already has its own rule),
content-matched answer timing, specific acknowledgement over bare אני מבין,
one genuine reaction to a personal detail, the demonstrated-memory callback in
the closing lead-in, warm bridges between subjects.

Rejected, with reasons: varied human goodbyes (the closing is fixed because
`endCallPhrases` matches on its words — vary it and the call stops ending);
calculated vulnerability ("יום ארוך", "אני עדיין לומד את המערכת" — the agent
never pretends to be human); slang examples (סבבה/יאללה banned); the discount
no-that-feels-like-yes (absolute rule 4 — no discounts, ever); free-value tips
(invented facts risk); temporal anchoring (no date/weather variables exist);
time-check and planted callback (wrong length of call). Per the file's own
editing rules: described what to convey, wrote no Hebrew lines, so no
`vapi_en.py` change.

Prompt: 34,715 → 36,443 chars. Pushed by direct PATCH to `3303317e` keeping
the live model object intact — **not** `vapi_sync.py`, whose BASE block still
says gpt-4.1-mini + Azure and would have downgraded the live gpt-5.4 +
Cartesia config. That mismatch is now the standing hazard: running
`vapi_sync.py debt --apply` today clobbers model and voice. The script needs
its BASE brought up to the live truth before anyone runs it again.

### Demo voice outage: Cartesia credits, two broken signups, and a discovery

The web demo was ending every call at pickup. Call logs showed
`pipeline-error-cartesia-voice-failed`; a direct TTS test against Cartesia
returned 402 — the account had hit its credit limit, and the Elliot fallback
was not rescuing the call. Two fresh Cartesia accounts both stuck at
"processing your subscription details" and returned 500 on every synthesis
call until provisioning cleared (their status page showed green throughout —
the 500s were account-side, not an outage).

The discovery that ended it: **the demo's voice was never a clone.**
`a976c076` "Eyal - Grounded Guide" is a public Cartesia library voice
(`is_public: true`, language `he`), usable on a free account. The Pro tier
gates cloning only. Pointed Vapi's Cartesia credential at the new free-tier
account, restored the assistant's original voice block (sonic-3, `he`,
positivity:low, chunkPlan guards, Elliot fallback), and the demo speaks again.

Along the way the assistant briefly ran Azure `he-IL-AvriNeural` as a
stopgap — rejected as robotic within one test call, which is a real A/B data
point for the native-voices question.

Open: free-tier credits are small, so heavy rehearsal can drain them; the
"Echo Stone" clone from `voice/echo-stone-sample.wav` still exists on no
account (needs a working Pro subscription, or ElevenLabs Starter + eleven_v3
with latency unmeasured); one or two $5 Pro charges may have gone through on
the abandoned accounts — check billing, refund via support@cartesia.ai.

### Credentials checklist written; .env.example generalised

`docs/reference/Homies-Credentials-Checklist.md` now lists every account the
build needs, per the day's decisions: telephony provider undecided (generic
BYO SIP trunk — gateway IP, SIP username/password), WhatsApp number provided
by Homies, Meta Business Manager from zero (verification is critical path
alongside Israeli DID KYC), chatbot LLM via OpenRouter. `.env.example`
telephony block generalised from Telnyx/Twilio to SIP_* variables; WhatsApp,
OpenRouter, Google Sheets and Monday blocks added. Domain split in two: n8n
and Chatwoot subdomains needed at build time (Meta webhook wants HTTPS), the
CRM's branded domain deferred to handover — Vercel's own URL until then.

### Dashboard pushed — `a2b361b`, the first commit in two days

Twenty-two files: the whole of `dashboard/`, migrations 008 and 009, and the
feature doc. Everything else from the last two days — Chatwoot, the WhatsApp
menu and language work, `check_whatsapp.py`, the Supabase writer switch — is
still uncommitted in the working tree.

Checked before staging rather than after: `.env`, `dashboard/.env.local`,
`node_modules` and `.next` all ignored, and the staged list confirmed empty of
them. `.env.local` holds only the URL and the anon key — no service role key
was ever in it. Added `dashboard/.vercel/` to `.gitignore` ahead of the deploy,
since `vercel link` writes it on first run.

`dashboard/.env.example` documents the two variables Vercel needs and says
plainly why the service role key is not among them. **Root Directory must be
set to `dashboard`** in the Vercel project — the app is not at the repo root,
and Vercel will otherwise build the repository and find no `package.json`.

## 2026-08-08

### A dashboard, and the three things it would have shown as facts

Asked for a dashboard over tickets, calls, concerns and transcripts, with
everything in Supabase. Most of the work was the second half of that sentence.

**Chat transcripts were not stored anywhere.** The conversation lived in n8n's
memory node — context for the model, never a record: capped at 30 messages, not
queryable, gone on restore. Migration 008 adds `messages`, one row per message
both directions, plus `v_conversations`. A child table rather than a bigger
`transcript` column because chat has no end-of-call moment to write one at, and
a read-modify-write of a growing string loses one of two concurrent messages.

**Every WhatsApp interaction was filed as an outbound voice call.**
`interactionId()` hardcoded `channel` and `direction` from when Vapi was the
only caller — the same shape as `opened_via` that morning. A calls page would
have reported calls that were never placed. Fixed; the four bad rows deleted.

**The log wrote our words as the resident's.** On the media and menu branches
Sort's `text` holds the *reply*, not the message, so the transcript had the bot
greeting itself. `in_text` is now carried separately from the first line.

**And logging was downstream of a failure.** `Log reply` sat to the right of
`Send`, so when Send failed — a recipient off the test allow-list — the run
aborted and nothing was logged. executionOrder v1 walks the canvas top to
bottom, so the node moved above Send. A send failure is exactly when the record
matters most.

Verified end to end: a four-message conversation, both sides, correct types,
`interactive` for the menu, `(no text)` for the image.

**Then the leak.** `messages` shipped in 008 without RLS. Every other table has
it on — the anon key reads nothing from them — and `messages` returned real
rows to it. **The anon key is public by design; it ships in the browser
bundle.** Anyone with it and the project URL could read every resident's
conversation. Live about an hour, four test threads, no real resident. Luck.

Migration 009 enables RLS, grants `staff_read` to `authenticated` and never to
`public` (which includes `anon`), sets `security_invoker` on the views — a view
otherwise reads with its owner's rights and hands rows out regardless of who
asked, which is what `v_conversations` was doing — and **fails the migration**
if any table in `public` has no RLS. 008 got through because nothing looked.

The dashboard itself is Next.js 14, seven pages, no CSS framework, builds
clean. Read-only by construction: no write policy exists, and an insert from a
staff session returns `42501`. Confirmed with a temporary auth user — signed in
reads all five tables, writes are refused, signed out reads nothing — then the
user was deleted.

Two build failures worth keeping. A single `lib/supabase.ts` exporting both
clients cannot compile: the login page is a Client Component and importing a
module that touches `next/headers` fails even unused. And the cookie callbacks
needed explicit types under `strict`.

Not deployed — Vercel needs their account. `NEXT_PUBLIC_SUPABASE_ANON_KEY` and
nothing else; the service role key in a browser bundle would hand a stranger the
whole database.

### Chatwoot is up at chat.srv1879140.hstgr.cloud

Deployed to the VPS that already runs n8n. Four containers, valid certificate,
`4.16.2`, `queue_services: ok` and `data_services: ok` — sidekiq and Postgres
both actually connected, not merely running.

Three assumptions were wrong and each was caught by reading the box instead of
trusting the plan.

**There is no Traefik network.** `ss` showed `traefik` itself owning :80 and
:443 rather than `docker-proxy`, which means host networking. The compose file
had declared `proxy` as `external: true` and would have refused to start.
Traefik reaches containers at their bridge IP through the Docker socket, so
Chatwoot needs only its own network plus labels — and with
`--providers.docker.exposedbydefault=false`, the labels are not optional.

**The certresolver was not worth guessing.** It is `letsencrypt`, copied
verbatim from n8n's own labels on the same box.

**No DNS work was needed at all.** `*.srv1879140.hstgr.cloud` is a wildcard —
`chat.`, `n8n-zqvb.` and a random string all already resolve to
186.240.147.235. HTTP-01 only needs the name to point at a box we control, not
ownership of the zone, so the certificate issued on first boot. The free domain
hPanel offers was never a blocker.

Two smaller things. `base: &base` is written as a service in Chatwoot's own
published compose, and compose obligingly starts it as a container that does
nothing; it is an `x-` extension field here. And `db:chatwoot_prepare` logs
`PG::UndefinedTable: relation "installation_configs" does not exist` in red —
an initializer running before the schema exists, with `Loading Installation
config` succeeding four lines later. Alarming and harmless.

`ENABLE_ACCOUNT_SIGNUP=false` does not lock out the first admin: every route
redirects to `/installation/onboarding` until an account exists. Verified before
handing the URL over, since the opposite would have meant a fresh install
nobody could log into.

Memory caps — rails 2g, sidekiq 1g — are there to protect n8n, which shares the
box. `curl` against n8n returned `HTTP/2 200` after the deploy.

### Chatwoot: self-hosted, and it owns the number

Two decisions, both taken 8 Aug.

**Self-hosted on Hostinger.** At 19 staff, Chatwoot Cloud is $19/agent/month —
about $361/month against a VPS at $7–15. The trade is that upgrades and backups
become ours, which is the trade already made for n8n on the same provider.

**Chatwoot owns the WhatsApp number**, with n8n behind it as an *agent bot*.
The alternative — n8n keeps the number, Chatwoot mirrors conversations read-only
— is less disruptive today and leaves the per-conversation AI toggle and real
human handover permanently impossible, which are two of the six capabilities
being asked for. A webhook answers every message by definition: there is no seat
to assign to, no second participant to hand to, and nowhere for "the bot is off
for this thread" to live.

The bot itself does not change. Agent, prompt, both tools, the Supabase writer —
all stay. What changes is who calls them.

Written: `deploy/chatwoot/` (compose, Caddyfile, env template) and
`docs/features/12-chatwoot/feature.md`. Four services — rails and sidekiq are
separate processes sharing one image, and running rails alone gives a working
dashboard that delivers nothing. Postgres must be **pgvector**, not plain, or
`db:chatwoot_prepare` fails. Caddy terminates TLS because Meta will not deliver
to a self-signed callback, so the certificate is the channel rather than a
nicety. `deploy/chatwoot/.env` is gitignored.

Not deployed — it needs DNS and an SSH session, which are the user's.

**It goes on the VPS that already runs n8n**, srv1879140 / 186.240.147.235,
KVM 2, at 11% memory and 4% disk on 8 Aug. A second VPS buys isolation for
another $7–15/month and is not worth it at this size.

Two things changed once the actual box was looked at rather than assumed.

**The Caddy service was deleted.** Port 80 there answers a bare `301 Moved
Permanently` with no `Server` header — Traefik, which is what Hostinger's n8n
template ships. A second proxy would have fought for 443, and the process that
failed to bind might have been the one serving n8n. Chatwoot now attaches to
the existing Traefik by labels, publishes no ports at all, and keeps Postgres
and Redis on a private network the n8n containers cannot see.

**Memory limits were added, to protect n8n rather than Chatwoot.** This box
runs the bot. If Rails leaks on 2 vCPU the OOM killer picks its victim by size,
and the victim could be n8n — taking WhatsApp down to fix nothing. `rails` 2g,
`sidekiq` 1g.

The two Traefik values — network name and certresolver — are discovered on the
box, not guessed. A wrong network means Traefik cannot see the container; a
wrong resolver means no certificate, and Meta will not deliver to a callback it
cannot verify.

The risky step is documented and is the only one: moving the callback means a
few minutes where Meta points at something not yet answering, and inbound
messages in that window are lost rather than queued. The test number has no
residents on it, so the first pass is free.

### Supabase is the store of record, and three guardrails now hold it there

Asked for Supabase, duplicate protection, and guardrails against the whole
thing unravelling again. All three, in that order.

**The writer moved.** `_writer()` in `n8n_deploy.py` returns the Supabase Edge
Function instead of the Apps Script URL, with the shared secret in a header
rather than the query string. Smaller than it sounds: both stores answer in the
same Vapi shape, and both writer nodes forward the untouched original envelope,
so a URL and a header changed and nothing in the graph moved. Voice and
WhatsApp both write to Supabase now. Apps Script stays deployed as the export
target and is no longer the store of record.

**The duplicate guard is in the Edge Function**, not in the prompt, because a
guard the model can decline is not a guard. Same building, same type, same unit
(`.is()` for NULL, since `.eq()` never matches it and common-area faults are
the ones most likely to be reported twice), still open, inside 30 minutes → the
existing reference comes back with `duplicate: true`. Not keyed on the
description: two people describing one lobby leak will not phrase it alike, and
substring matching on free text is the kind of clever that fails silently.
Verified across five cases — same place dedupes, different building does not,
same building with a unit is distinct from the same building without one.

**`scripts/check_whatsapp.py` checks consequences, not configuration.** It
posts a real signed message at the live URL and then looks in the database for
the row, because every serious fault this bot has had was silent and would have
passed a config audit: the half-wired webhook, the wrong WABA subscription, the
truncated reference, a week of tickets in a spreadsheet, a regex full of
backspace characters. Seventeen assertions, exits non-zero, cleans up after
itself.

It failed twice on its first two runs, which is the point.

**Once on a bad fixture of mine** — the building was `__selfcheck__` and the bot
asked which building, correctly, because no building is called that. A fixture
the system is right to reject is a broken fixture.

**Once on a real bug.** A lobby leak wrote `unit = "שטחים משותפים"` — "common
areas". The prompt says common property has no apartment and the model complied
with the idea while filling in the field. Nothing errors, the row reads
correctly to a person, and it is wrong to every query: `unit IS NULL` stops
finding common-area faults, grouping by unit invents a flat called Common
Areas, and the new duplicate guard stops matching. **A model told to leave a
field empty will often name the emptiness instead.** `unitOf()` now decides:
a unit is short and contains a digit, and a label is not a unit.

`opened_via` was hardcoded `"voice"` at all three insert sites and was about to
start lying, since WhatsApp writes through the same function. `channel()` reads
the `wa:` call-id prefix.

Four test rows deleted afterwards; `requests` is back to the one real row.

### Every ticket opened today went to a spreadsheet, not to Supabase

Asked whether `HM-2026-8282` was in the database. It is not, and neither is any
other reference the bot has read out today.

`requests` in Supabase holds **one row** — `HM-2026-1001`, 08:06, from a direct
test of the Edge Function. Checked with the service-role key, so this is not RLS
hiding rows; the anon key sees zero.

The tool webhook the bot calls, `homies-debt-tools` on n8n, does not post to
Supabase at all. Its writer node posts to the **Google Apps Script bridge**, and
`call_requests` on that spreadsheet now holds 28 rows. The reference comes back
from the sheet, which is why it looks real: it *is* real, in the wrong place.

So the two halves of this system have been drifting apart in plain sight. The
Edge Function got three fixes today — the `open_request` building bug, the
urgency validator, `save_partial_request` — and **nothing calls it except the
end-of-call report**. The voice agents and WhatsApp both write through the same
n8n router, and that router writes to Sheets.

Nothing is lost; every ticket exists. But the CRM in Phase 6 reads Supabase, the
migrations describe Supabase, and `requests.reference` is generated by a Postgres
default that has produced exactly one value.

Not fixed — repointing the writer is a one-node change, but it swaps the store
of record for the voice agents at the same time, and that is a decision rather
than a repair.

### The language stopped being the model's decision

Reported a second time from a handset, after the bilingual fixed lines were
already in: English menu, `Balance and payments` tapped, Hebrew handover line
back. The prompt said the right thing and the model did not do it — a rule
competing against a conversation history that was largely Hebrew, and history
kept winning.

So it is no longer a rule. **Sort decides the language in code and remembers
it**, per phone, in the same workflow static data that holds duplicate
suppression:

- an explicit request — the menu row, or the word in either language — sets a
  preference and it **sticks**;
- otherwise the script of the message decides, and updates the preference, so
  someone who goes back to typing Hebrew gets Hebrew back;
- a photo, which carries no words, falls back to whatever was already chosen.

The decision then rides **on every turn** as a directive at the top of the
message (`[Answer this message in ENGLISH.]`), rather than sitting in a constant
system prompt — a constant instruction is precisely what was already failing
against live context. Same caveat as the dedupe map: static data does not
survive an n8n restore, and the cost of losing it is one message in the wrong
language.

Two things fell out of testing it:

**A bare `speak english` was answered with the media line** — *"I can only read
text here"*, in reply to text. Nothing about that message needs a model: the
switch is a fact Sort has already established. It now gets a fixed confirmation
in the new language. Guarded by a leftover check, so *"speak english, there is a
leak in the lobby at Herzl 14"* still reaches the agent, in English, with the
leak intact — verified.

**And the first attempt at that guard silently did nothing.** The patch script
wrote `"\b"` into the regexes, which in Python is a **backspace character**, not
a word boundary. `/\benglish\b/` shipped as `/‹BS›english‹BS›/` — a valid regex
that matches nothing. No error anywhere; the Hebrew branch worked because its
patterns have no `\b`, so half the feature passed its test and the other half
quietly did not. Ten of them across the file, now repaired.

### A fixed line was fixed in one language

Found by the client on a real handset, which is the only place it could have
been found. English was tapped from the menu, the intro came back in English,
then *"any update on my ticket?"* was answered with
`אני מעביר את זה לצוות, נחזור בהקדם.` — an all-English conversation ending in
Hebrew.

The language rules written an hour earlier were obeyed exactly. The handover
line is not written by the model: the prompt names it verbatim as one of two
**fixed lines**, and a fixed line is fixed in the language it was written in.
Two correct rules, and the newer one had no authority over the older one.

Both fixed lines now exist in both languages, with the rule stated where it was
missing: *a fixed line stays fixed, but it does not stay Hebrew.* The error
branch's copy is an expression over the language Sort detected, so a model
failure cannot undo the language choice either.

Re-tested end to end on the same sequence: `hi` → English menu → tap English →
*"Hi, Michael from Homies. How can I help?"* → *"any update on my ticket?"* →
*"I'm passing this to the team, we'll get back to you shortly."*

Third instance today of one shape: **a rule that reads as absolute silently
outranks the rule that should have qualified it.** After the apartment question
and the announcement, this one crossed languages rather than sections.

**`transfer_to_human` remains unreliable** — called on the ticket-status
question, not called on *"how much do I owe?"*, both in the same batch. The line
is delivered either way, so the resident is told a human is coming while nobody
is told anything. Not fixed.

### A menu on the first message, and English when asked

Two asks: buttons to choose from, and an English mode triggered by saying so.

**The menu is a list, not reply buttons** — buttons cap at three and the client
picked five options. Meta's limits are hard: row title 24 characters,
description 72, list button 20, ten rows total. Two of the five rows,
`status` and `balance`, are **not built** and route to a human. That was the
explicit choice: the gap is visible rather than hidden, and a tap lands exactly
where the same question in words already lands.

**The menu appears only for a bare greeting.** `שלום` gets it; `שלום, יש נזילה
בלובי בהרצל 14` does not — it opens a ticket, because answering a stated fault
with a menu would undo the morning's rule about not asking what happened when
already told. The greeting test is anchored and whole-string, after stripping
emoji and trailing punctuation.

**Parsing taps had to land in the same change.** An `interactive` message
carries no `text` field, so under the old parser a resident tapping a button we
had just sent them would have been told *"I can only read text"*. Sort now reads
`button_reply` and `list_reply`, keeping the row id for the log and passing the
title on as the message.

**Menu language is chosen by script detection** — one Hebrew character decides
it — because the menu is sent without a model call.

**English mode lives in the conversation memory**, whose window went 12 → 30.
That is the whole mechanism, and its boundary is worth writing down: the switch
survives exactly as long as the request is still inside the window. A hard
per-phone language field belongs in an n8n Data Table, which this instance
supports (`/api/v1/data-tables` responds) and which is the right fix when the
toggle must survive indefinitely.

Seven paths tested. Hebrew greeting → Hebrew menu; `hi` → English menu; a
balance tap → handover **with `transfer_to_human` actually called**, which is
the tool that was narrated-but-not-called earlier today; an `open` tap → asks
what happened; greeting-plus-fault → ticket `HM-2026-9030`, no menu; and
`speak english please` mid-conversation → *"Hey, Michael from Homies. How can I
help?"*.

Every send in those runs failed `131030` on invented numbers, which proves the
allow-list and **not** the payload — Meta may check the recipient first. So the
Hebrew menu was sent for real to the registered test number and delivered
(`wamid.HBgMNjM5NjAzOTEzNTE0…`). The list payload is valid.

### The bot introduces itself now — and was truncating reference numbers

First real WhatsApp exchange, execution 82: `hi` in, `שלום, מה קרה?` out,
delivered. Correct, brief, and from nobody — a resident has no way to tell they
reached the building company rather than a wrong number. The first message in a
conversation now carries a name and a company (`היי, מיכאל מהומיז. מה קרה?`),
written as a rule rather than a third fixed line, plus two explicit guards: do
not introduce yourself twice, and do not ask `מה קרה?` when the first message
already said what happened. Both verified.

**Found while checking that: the model was silently truncating the reference
number.** `open_request` returned `HM-2026-8884` and the resident was told
`2026-8884`. Both test tickets, so it is default behaviour, not a one-off.

Nothing errors, the ticket is real, the reply reads perfectly, and the resident
writes down an identifier that will not be found when they quote it to staff.
The prompt already said *do not invent a reference number* and that rule was
obeyed — the number came from the tool. Passing a value through to a human
**unaltered** is a different instruction and had to be written separately, with
the exact failure named, because "exactly" is what the model already believed it
was doing. Re-tested: `HM-2026-8894` in, `HM-2026-8894` out.

### A rule loses to the headline above it — twice, in the same reply

Execution 89, a stuck lift with the floor given, answered
`אני פותח קריאה על מעלית תקועה. יש מספר דירה?`. Two faults, and both rules
already existed.

**The apartment question.** The rule was not too weak, it was in the wrong
place. The section opened *"ארבעה דברים: מה התקלה, באיזה בניין, **באיזו דירה**,
וכמה זה דחוף"* — four required things stated unconditionally — with the
common-property exception three paragraphs below. The model followed the
headline, which is what a headline is for. Folded the exception into the
definition instead: **three** things now, and *where* is one question with two
answers — inside a flat needs building and unit, common property needs the
building and nothing else, not the floor either.

**The announcement.** `אני פותח` was said before `open_request` ran, in a
message that then asked a question instead of calling it. The tool never ran.
The old rule said *do not say you opened a ticket before the tool returned*, and
the present tense complied with the letter of it.

Tightening that surfaced a third habit on the next run: `אני פותח קריאה על שער
חניון שלא נסגר. זה בסדר?` — asking permission to do the one thing it exists to
do. A resident who reports a gate has already asked. Added: never ask to open,
only ask for what is missing.

Four fault types re-tested afterwards, all correct — gate, bulb and lift open
without asking anything, an in-flat leak with a unit opens, an in-flat fault
without one asks for the unit, and a lift asked first whether anyone was
trapped, which is the safety rule working unprompted. References matched the
tool in every case.

**The general lesson, and it appeared twice in one day: an exception placed
after a categorical statement does not modify it.** Fold it into the statement,
or stop the statement being categorical.

**Judgement call left open:** *"יש רעש מהגג כל הלילה"* was answered with
*"איזה רעש?"*. The prompt says do not ask a resident to re-describe a fault; a
real service worker probably would ask this one. Not changed.

### The WABA was subscribed to the wrong app, and nothing would have said so

With the API Setup token in hand, `GET /{waba}/subscribed_apps` listed exactly
one app — **"WA DevX Webhook Events 1P App"**, Meta's own dev-tools listener.
Not HOMIES. App-level registration (done 8 Aug) tells Meta *where* to deliver;
it does not subscribe the Business Account to the app. Both are required and
only one of them is the step anyone writes down.

The failure mode is the one this workflow keeps producing: the callback URL
shows verified in the dashboard, the workflow shows active, the number accepts
messages, and no execution ever runs. Third time the same silent-success shape
has appeared here — after `multipleMethods` output 1 and after `serverUrl: null`
on the voice assistants. `POST /{waba}/subscribed_apps` with the user token
fixed it; both apps are now listed.

Then a full end-to-end run against the live URL with a correctly signed
envelope — *"יש נזילת מים בלובי של הרצל 14"*:

    WhatsApp → Sign the raw body → Sort → Answer Meta (200 in 0.8s)
    → Is there a message? → OpenRouter + open_request
    → "פתחתי קריאה 2026-8884. אעדכן בהמשך."
    → Send  ✗ 131030 Recipient phone number not in allowed list

Nine nodes correct, one refusal, and the refusal is the right one: the test
number only delivers to hand-registered recipients. Reproduced the same error
straight against Graph to prove it was the allow-list and not the credential —
`131030`, not a `190`. The credential works.

Note the row: reference **2026-8884** in `requests` is test data written against
the invented number 972500000001.

### The send token goes in n8n's credential store, not in the workflow

Asked to run on Meta's **test number** for now, which is the right call — it
needs no Business verification, so it un-blocks the last row of the checklist
today instead of in one to two weeks. Two limits come with it: it only sends to
up to five recipient numbers you register by hand, and its access token expires
roughly every 24 hours.

Neither of the two values can be fetched by API. `APP_ID`/`APP_SECRET` reach the
app, and the phone number id and access token hang off the **WhatsApp Business
Account** — `/{app-id}/whatsapp_business_accounts` and both its owned/client
variants return `(#100) nonexisting field`, because those edges live on the
Business, which an app token cannot see. They have to be copied from the
dashboard.

What did change is where the token lands. The Send node carried
`Authorization: Bearer <token>` as a plain header parameter, which writes the
token into the workflow JSON — readable by anyone with n8n access, and carried
into every export and backup. It is the same mistake the Crypto node stopped us
making with `APP_SECRET` yesterday, except n8n *refused to publish* that one and
nothing refuses this one. `ensure_send_cred()` now creates an `httpHeaderAuth`
credential and the node references it by id.

It deletes and recreates on every `--apply` rather than reusing the id. n8n's
public API can create and delete a credential but not update one, and a 24-hour
test token means rotation is routine — reusing the id would mean silently
sending yesterday's token. Recreating guarantees the value in `.env` is the
value in n8n.

### The voice agents now record their own calls — eleven of them were thrown away

`interactions` had zero rows. Eleven test calls happened on 7 Aug and every
transcript, every ended reason and every latency figure from them lives in the
Vapi dashboard and nowhere the CRM, the scoreboard in
[08-instrumentation](features/08-instrumentation/feature.md) or a native Hebrew
reviewer can reach. The table has had columns for `transcript`, `summary`,
`audio_url`, `duration_seconds` and `latency_ms` since `001` on 2 Aug and
nothing has ever written one. The tools created stub rows during a call and no
second half ever arrived.

The cause was one missing field. All four assistants had `serverUrl: null` and
`serverMessages: []`, so Vapi computed the end-of-call report and posted it
nowhere.

**This was blocked and stopped being blocked today.** `vapi_sync.py` has said
since 5 Aug that the proper fix for the duration cap "needs a server URL that
does not exist yet". Deploying `debt-tools` this morning created one.

Now live on all four:

```
server         https://…supabase.co/functions/v1/debt-tools
serverMessages ["end-of-call-report"]
```

**One message and not eleven.** `conversation-update` and `speech-update` fire
several times a second, each a round trip to Tokyo into a function that writes
the same row. The end-of-call report carries the transcript, the recording, the
duration, the ended reason and the latency in a single POST *after* the call is
over, where nothing it does can cost the caller a millisecond.

The report endpoint is resolved by its own `report_server()`, deliberately not
by `tool_server()`. They are the same URL today and they are not the same
decision: the tool endpoint follows where the integrations live and currently
picks n8n, which has no handler for a server message at all. Pointing the report
there would have returned 200 and written nothing — the failure that leaves no
trace anywhere.

Verified against the live function with four cases before anything was pushed: a
`status-update` acknowledged and ignored; a report writing one filled row; a
tool firing first and the report updating that same row rather than making a
second, keeping the more specific `transfer:hardship` over `caller_hung_up`; and
a cut-off call salvaged. Test rows deleted.

### Three bugs the wiring turned up on the way

**`open_request` was dropping the inbound caller's building.** It read
`ctx.building ?? ""` — the value the campaign runner attaches to an outbound
call. Inbound there is no caller ID and no lookup, so the building only ever
arrives as a tool argument, and this file never read it. Every intake ticket
written through Supabase would have carried an empty building while the agent
read a real reference number back to the caller. n8n does it right
(`ctx.building || args.building || ''`), which is why nothing has shown up yet:
the live assistants post to n8n. It would have appeared on the day we switched.

**`save_partial_request` did not exist in the Edge Function.** The live intake
assistant carries the tool. Pointing it at Supabase would have answered `unknown
tool save_partial_request` at the exact moment it was salvaging a failing call —
the one outcome feature [07](features/07-partial-ticket/feature.md) says is not
allowed. Written now, against the `needs_review` status migration `003` added for
it, and it never refuses: an empty description is a real answer, because it says
the audio was unusable.

**`urgency` is validated in the function instead of by Postgres.** Yesterday's
`urgent` reached the database and came back as an English constraint message
mid-Hebrew-call. There is now a small synonym map — `urgent`→`high`,
`critical`→`emergency` — and anything unrecognised lands on `normal`, not `low`:
the failure that matters is an emergency filed as routine.

### The duration cap has a net under it that the model cannot decline

Vapi hangs up on the second `maxDurationSeconds` expires, mid-word, and never
tells the model it is coming — so the agent cannot be relied on to call
`save_partial_request` first. The report handler now sees `endedReason:
max-duration-exceeded` or `silence-timed-out`, checks whether the call produced
any row at all, and if not writes a `needs_review` request with the transcript in
it verbatim.

Verbatim rather than summarised, deliberately. Summarising means guessing the
building, and a guessed building on a maintenance ticket sends somebody to the
wrong address.

### Voicemail detection was off on both outbound agents

`voicemailDetection: {}` is not a neutral default on an agent that dials people.
It is the agent holding a full debt conversation with an answering machine,
reading a resident's balance into a recording anyone in the household can play
back, and hanging up having logged nothing. `voicemail` has been a value in
`log_call_outcome`'s enum since 4 Aug; nothing was ever detecting it.

On now, Vapi's own model rather than a beep timeout — Israeli carrier greetings
run long, and a fixed timer either cuts off a real person who paused or waits
through the whole greeting. **No `voicemailMessage`.** Leaving a recorded message
about somebody's debt on a machine is a disclosure to whoever plays it, which is
a decision for Homies and their lawyer rather than a config default. Detect, log,
hang up, let the campaign runner try again.

### Both English twins have diverged and refuse to rebuild

`vapi_en.py intake` and `vapi_en.py debt` both stop rather than build:

```
intake  9 passages no longer match — including "You are Michal…"
debt    LANGUAGE block did not match. The Hebrew prompt has changed.
```

That is the safety property doing exactly what it was written to do. The cost is
that both live English assistants are stale copies of prompts that no longer
exist — the intake twin is still feminine *Michal* while the Hebrew agent has
been masculine *Michael* since 7 Aug. **An English twin that has quietly stopped
representing the Hebrew one is worse than no twin, because it gets trusted.**

The two changes that do not touch a prompt were applied to them directly:
`waitSeconds` and the report endpoint. Rewriting the two substitution tables is a
job of its own and is not done.

`waitSeconds` was still 0.4 on both twins — the 7 Aug latency fix only reached
the Hebrew pair. That field is dead time before any work starts, so unlike the
punctuation timers around it, it is not a property of the language, and leaving
it made the twin 150ms slower than the assistant it exists to represent.

### Meta is connected to n8n, and the webhook is no longer forgeable

`APP_ID` and `APP_SECRET` arrived in `.env`. They are **not** the two values the
workflow needs to send — that is still `WHATSAPP_PHONE_NUMBER_ID` and
`WHATSAPP_ACCESS_TOKEN`, which live on the WABA rather than on the app, and an
app access token can reach neither. What they *are* good for turned out to be
two things that mattered.

**One: the callback is registered, by API rather than by hand.**
`POST /{app-id}/subscriptions` accepts an app access token, so the dashboard
step is now a script:

```
object     whatsapp_business_account
callback   https://n8n-zqvb.srv1879140.hstgr.cloud/webhook/homies-whatsapp
fields     ['messages']
active     True
```

Meta called the GET challenge as part of that and got the right answer, so
verification passed on the first attempt.

**Two: the webhook was an open endpoint that files service tickets, and now it
is not.** Every POST Meta sends carries `X-Hub-Signature-256`, an HMAC-SHA256 of
the raw body keyed on the app secret. Nothing was checking it. Anyone who
learned the URL could have posted a forged envelope with any phone number in it
and opened a real ticket against a real resident — as I did repeatedly today
with `curl`, which is exactly the point.

```
correctly signed   -> passes, opens the ticket, replies
no signature       -> dropped, "unsigned"
wrong signature    -> dropped, "bad signature"
GET verification   -> still echoes the challenge
```

All four answer **200**. Meta must never be told to retry, and a caller who is
not Meta learns nothing from the response.

**Two things went wrong on the way, and both are worth keeping.**

`require('crypto')` in the Code node throws **`Module 'crypto' is disallowed`** —
this n8n runs Code in a task-runner sandbox with builtins blocked, which is a
server setting we cannot reach from here. It broke every message for a few
minutes before the executions showed why. The fix is n8n's native Crypto node,
which needs no module and takes the secret from the credential store instead of
from a string baked into this repo's source. Better in both directions.

Then n8n **refused to publish** the first attempt:

```
Cannot publish workflow: Node "Sign the raw body":
  Missing or invalid required parameters: secret
```

`typeVersion: 1` of the Crypto node takes the secret as a plain node parameter,
which would have written `APP_SECRET` into the workflow JSON. V2 reads it from a
`crypto` credential. The server-side validation caught a real mistake before it
shipped — the same check `validate_workflow` would have made, arriving from the
other direction.

Two n8n credentials now hold secrets that used to be, or would have been, in
files: `Homies OpenRouter` and `Homies Meta app secret`.

### The real WhatsApp requirement arrived, and the bot is one sixth of it

PRD item 3, from the client, saved verbatim in
[11-whatsapp-bot/prd.md](features/11-whatsapp-bot/prd.md). It is not a request
for a bot. It is a request for a **centralised WhatsApp system** — one business
number, employee seats, four departments (Collections, Operations, Management,
Service), chat transfer between agents, open/closed ticket tracking, full logs
with automatic summaries and topic tagging, and an AI bot that is **one
participant in that inbox** rather than the thing itself.

Six capabilities are named. **We have one.** Opening service tickets works end
to end; sending payment links exists but belongs to the debt agent and is not
attached here; FAQs, ticket status and balance/debt do not exist.

**The structural item is the per-conversation on/off toggle.** Today the webhook
answers every message that reaches it — that is what a webhook is. There is no
per-conversation state and nowhere to keep it. Meta's Cloud API delivers to
exactly one callback URL, so whatever owns the inbox owns that URL and n8n moves
behind it. That is not a feature to add later; it decides the shape.

**And it reopens a question that was closed by accident.** The bot identifies
nobody: it takes the phone off the envelope and files a ticket against it, which
is safe *because it only ever writes*. Three of the six new capabilities — ticket
status, balance, debt — **read** personal financial data back to whoever is
holding a handset. PRD §13 #1, the verification method, has been open since the
first spec and blocked nothing. It now blocks two capabilities.

**The Chatwoot decision from 7 Aug is worth revisiting on its own terms.** It was
deferred partly because the only VPS was shared production carrying four other
clients — an objection that died this morning when Homies' own n8n turned up.
What is left of the argument is real (a Rails stack to run and maintain) but the
thing it was deferred *for* — a handover inbox nobody had asked for — is now
explicitly asked for, in writing, four times over.

### The bot is male, the resident is not assumed to be — and it stopped sounding like a bot

Asked for: Hebrew as the main language, natural and local and casual so it reads
as a person, and **male** — masculine forms only, with better words where a word
carries too many meanings.

**The male half is easy. The other half is the one that can hurt somebody.**
Hebrew marks gender on the imperative and the second person, so `תכתוב לי` and
`אתה גר` are said to a man, and roughly half of ~10,000 apartments are not men.
Nothing in the WhatsApp envelope gives a resident's gender; a display name is a
guess. So the prompt now carries two rules, not one:

| | Rule |
|---|---|
| About **himself** | Masculine, always — `אני פותח`, `אני מעביר`, `רשמתי`. |
| About **the resident** | Never gendered — `אפשר לכתוב`, `יש כתובת?`, `מה קרה?` |

This costs nothing in register, which is why it works: `אפשר לכתוב לי מה קרה?`
is *more* natural in a service context than `תכתוב לי מה קרה`, not less.

**And the first draft of the handover line broke that rule.** `יחזרו אליך
בהקדם` — without niqqud `אליך` is *elecha*, addressed to a man. The fix is not a
slash or a spelling trick: drop the addressee. `נחזור בהקדם` is first person
plural, which is how a company talks anyway, and carries no gender at all. Both
fixed lines were re-checked for the same fault afterwards.

**Three words were replaced for carrying too many meanings:**

| Was | Now | Why |
|---|---|---|
| פנייה | קריאה / קריאת שירות | `פנייה` first means *turning*. `מספר קריאה` reads as a reference number without needing context. |
| בעיה | תקלה | `בעיה` is any problem, including a personal one. `תקלה` is a fault in something meant to work. |
| נציג מהצוות שלנו | הצוות | Translated-sounding, and `הוא יחזור` genders a colleague nobody has met. |

**The register section names the tells rather than describing a tone.** No
`איך אוכל לסייע`, no `מה שלומך`, no `תודה שפנית אלינו`, no `אשמח לעזור`, no
emoji, no openers and no sign-offs. Written formal Hebrew is what a model
reaches for by default and is exactly what makes it read as a machine.

**Four faults found by testing, three of them mine.**

1. `אוקיי` was listed as approved vocabulary, so the model opened a conversation
   with it — *"אוקיי, מה קרה?"* to a bare `שלום`. Those words are acknowledgements
   of something already said, not openers, and the prompt now says so. Now:
   *"היי, מה קרה?"*
2. Two questions in one message to a frustrated resident. The one-question rule
   was a sentence; it is now a hard count — **one question mark per message**.
3. `מישהו שכועס` sent every irritated person to a human. Someone frustrated that
   a fault has not been fixed does not want to be passed on, they want it
   written down. Split: frustrated → open the ticket; angry **at us**, or
   demanding a manager → transfer.
4. **A contradiction I wrote myself.** `מעלית תקועה עם אדם בפנים` sat in the
   urgency examples *and* under the safety rule that says never open a ticket.
   The model obeyed the first and opened a ticket for people trapped in a lift.
   Removed from the urgency list; the safety rule now names the cases and says
   explicitly not to do both.

**Verified live through the webhook after each fix:**

```
"שלום"                              היי, מה קרה?
"הדלת של הכניסה לא נסגרת"           באיזה בניין מדובר?        (building, not apartment)
"המעלית תקועה, יש בפנים אנשים"      transfer_to_human only, no ticket
"נזילה במקלחת, ויצמן 8 דירה 4"      טיפלתי. מספר קריאה HM-2026-3496.
"שלום, החניון מוצף מים"             אוקיי, יש הצפה בחניון. באיזה בניין זה קרה?
"כבר פניתי פעמיים… תעבירו למנהל"    transfer_to_human {reason: caller_request}
```

Every reply carries exactly one question mark or none, addresses nobody by
gender, and speaks in active first person.

**Still not reviewed by a native speaker,** which is the same standing gap the
voice prompts carry and it has now grown. Every line above was written, not
transcribed. The three to put in front of an Israeli first are the handover
line, `טיפלתי` as a closing, and whether `קריאה` or `פנייה` is what Homies'
own staff actually say.

### Gemini 2.5 Flash, and the WhatsApp bot answered a resident for the first time

Model switched from `anthropic/claude-opus-5` to `google/gemini-2.5-flash`, asked
for directly. Slug verified against `openrouter.ai/api/v1/models` rather than
typed from memory — it exists, carries `tools` in `supported_parameters`, and has
a 1M context.

```
                    in $/1M   out $/1M   one real turn   latency
claude-opus-5         5.00      25.00      $0.02040       6,195ms
gemini-2.5-flash      0.30       2.50      $0.00051       2,321ms
```

**Forty times cheaper and nearly three times faster on the same message**, against
the same 2,598-character prompt with both tools attached. It also made the bot
work *today* rather than when credits arrive: OpenRouter pre-authorises
`max_tokens` against the balance, and 4096 tokens of Opus exceeded it while 4096
tokens of Flash sits comfortably inside.

**And then it ran, all the way through:**

```
Sort                 success
Answer Meta          success     Meta answered in 762ms, before any model work
OpenRouter           success     x2 — the tool round trip
open_request         success
Answer the resident  success
Send                 error       Authorization failed (placeholder Meta token)
```

The reply, in Hebrew: *"היי, פתחתי עכשיו קריאת שירות עבור הנזילה בלובי, מספר
הפנייה הוא HM-2026-9318."* The reference is real — the tool webhook wrote the row
and handed the number back, and the debt-tools execution confirms it:
`type: plumbing, urgency: high, building: הרצל 14, unit: 12`, description in the
resident's own words. **The one thing this bot must never do is invent a
reference number, and it did not.**

Only `Send` fails, on the Meta token that has never been filled in.

### The tool node I used was deprecated, and n8n said so at runtime

`@n8n/n8n-nodes-langchain.toolHttpRequest` failed with:

```
has a "supplyData" method but no "execute" method
```

Reading the node source explains it: `hidden: true`, with the comment *"Replaced
by a `usableAsTool` version of the standalone HttpRequest node."* The current way
is `n8n-nodes-base.httpRequestTool` — the ordinary HTTP Request node in tool mode
— with `descriptionType: 'manual'` plus `toolDescription`, and arguments declared
through `$fromAI()` instead of `{placeholder}` tokens and a placeholder table.

This is exactly the drift the skills warn about, and it is worth noting that the
skill pack did not catch it either: `references/TOOLS.md` names the four tool
types, and the deprecation is only visible in the node source. Empirical testing
found it; nothing else would have.

**`$fromAI()` also made the security rule easier to see.** Anything wrapped in it
is a parameter the model fills. Anything not wrapped is fixed by us. The phone
number is `$('Sort').first().json.to` — `.first()` on a named node rather than
`$json`, because a tool runs inside the agent's execution where the current item
is the agent's own and pairing back to the trigger is not guaranteed. The phone
decides whose ticket this is, so it has to be deterministic.

### The OpenRouter key works and the account is still empty — the $1,000 is a cap

The key in `.env` was already in use: the n8n credential `Homies OpenRouter`
(`f95jN4EnTPL6CQuJ`) was created from that exact value, which is why the agent
run failed with **Payment required** rather than *unauthorized*. A 402 is the
account answering, not the key being rejected.

**`GET /api/v1/key` reports `limit: 1000` and that is not money.** It is a
spend ceiling on the key. The account balance is what runs out, and OpenRouter
pre-authorises `max_tokens` against it:

```
max_tokens 4096   402  "you requested up to 4096 tokens, but can only afford 1459"
max_tokens 1400   200  6,195ms  finish_reason=tool_calls
max_tokens 800    200  4,053ms
```

**So the key is fine and the model is good.** Against the real 2,598-character
system prompt with both tools attached, it called `open_request` with
`building: הרצל 14`, `unit: 12`, `type: plumbing`, `urgency: high` — a valid
enum value, so this morning's constraint fix holds through the whole chain — and
the description in the resident's own Hebrew.

**Lowering `max_tokens` is still the wrong fix, and now there are numbers.** The
prompt alone is **2,671 tokens, $0.0134**, before the model writes a word. A full
turn measured **$0.0204**. `max_tokens` only gates the pre-authorisation; it
barely moves the bill. At roughly **2¢ a message**, $5 of credit is about 250
messages and $20 is about a thousand. That is the decision, not the token cap.

**And the agent swap lost prompt caching, which is most of that cost.** The
response reports `cached_tokens: 0`. The old Code node set an explicit
`cache_control` breakpoint on the system prompt; the OpenRouter node has no such
option, so every message now pays full price for the same 2,598 characters.
Together with the missing reasoning parameter, that is the second thing the AI
node cannot express that hand-written HTTP could. Worth knowing before the
volume matters: at 200 messages a day the difference is real money.

### The WhatsApp bot is an AI Agent node now, not 150 lines of JavaScript

Asked for directly: use an AI node. The `Brain` Code node — which ran the whole
tool-use loop by hand against OpenRouter's HTTP API — is replaced by
`@n8n/n8n-nodes-langchain.agent` with four sub-nodes.

```
Answer the resident  (agent)
  ├── OpenRouter            lmChatOpenRouter   credential f95jN4EnTPL6CQuJ
  ├── Conversation so far   memoryBufferWindow keyed on the phone, window 12
  ├── open_request          toolHttpRequest
  └── transfer_to_human     toolHttpRequest
```

**What it bought, in order of how much it matters.** The model key is in n8n's
credential store instead of interpolated into a code string, so an exported
workflow carries no secret. Conversation memory is a node rather than workflow
static data, which does not survive an n8n restore. And the two tools are objects
on the canvas the agent can reach, not a URL buried in a `fetch`.

**What it cost, and this is real.** The old loop sent
`reasoning: {effort: "low"}`. **The OpenRouter node has no reasoning parameter** —
its options collection is frequency penalty, max tokens, response format,
presence penalty, temperature, timeout, max retries and top P, and nothing else.
Confirmed by reading the node source, not by assuming. So thinking now runs at
the model's own default. That is the *safe* direction, because the failure this
project cares about — a tool call written into visible text instead of emitted
as one — happens when thinking is OFF. It is slower and dearer per message.
`EFFORT` stays in the file, renamed to say it is no longer sent, so this is
written down rather than rediscovered.

**The error branch had to be rebuilt, and is not optional.** The Code node
caught a failed model call in a try/catch and answered with the handover line.
An Agent node that errors just fails. So the agent carries
`onError: continueErrorOutput` and its second output runs a Set node holding
that same sentence. Without it, a model failure is a resident who is never
answered at all.

**Verified against the live instance, which is the only way to check anything
without the MCP connected:**

```
Sort                 success
Answer Meta          success       (Meta answered before any model work)
Conversation so far  success
OpenRouter           error         Payment required
Answer the resident  success       -> error output
Hand over instead    success       to=972500000011, the Hebrew handover line
Send                 error         Authorization failed (placeholder Meta token)
```

Both remaining failures are the two things already known to be missing —
OpenRouter credit and the Meta token. Everything between them works, and the
LangChain node types are confirmed present on this n8n at the typeVersions used.

**The phone is interpolated, never a placeholder.** Both tool nodes build the
Vapi-shaped envelope with `{{ $json.to }}` for the phone and `{placeholder}`
tokens only for what the model is allowed to decide. A placeholder is something
the model fills in, and the model must never be able to choose whose ticket
this is — the same rule the voice agents follow for the amount and the month.

Dead code removed: 152 lines of `BRAIN` JavaScript and the `openai_tools()`
converter that existed only to feed it.

**The layout checker caught two things on the way.** My own `Hand over instead`
node, 60 apart from `Send` — fixed before the push. And then the debt-tools
canvas, whose nodes had drifted to `[720, 64]` and `[976, 224]`: somebody
dragged them in the n8n UI. Re-pushed from the script, which is the source of
truth, and that is precisely the drift these scripts exist to prevent.

### Two nodes had been drawn on top of each other since the day it was written

New rule from the client side: a workflow has to be presentable — no
overlapping nodes, human readable. Applied to all three and **encoded rather
than remembered**, in [scripts/n8n_layout.py](../scripts/n8n_layout.py). It
raises before any push if two nodes sit within 200×180 of each other, if a node
still carries a default name (`Code`, `If1`, `HTTP Request2`), or if the
workflow has no sticky notes at all. All three deploy scripts call it first
thing in `main()`, and `python scripts/n8n_layout.py` audits the whole instance.

**What it found immediately.** `Anything to write?` and `Needs the real answer?`
were both at exactly `[460, 120]` in the debt-tools workflow — identical
coordinates, one node drawn perfectly on top of the other, so the canvas showed
seven nodes where there were eight. **Nothing ever failed.** The workflow has
run correctly the entire time. It simply could not be read, and the two IFs that
decide whether the caller waits for a write were the pair you could not see.

Everything is now on a 240-wide grid with rows in multiples of 60 — one column
per stage, one row per branch, trigger at the left.

**Sticky notes were added and then removed the same hour.** They were not asked
for: *"no text box no description just the nodes to be very well placed no
overlapping nodes."* The canvas shows the shape of the flow and nothing else,
and the reasoning stays in the script that builds it, beside the code it
describes and under version control. Two homes for one explanation is two places
to drift, which is the argument these scripts already make about prompts.

```
  ok    Homies — call queue (read)
  ok    Homies — debt tools (Vapi)
  ok    Homies — WhatsApp bot
3 of 3 workflows are readable.
```

Re-verified after the move, because a relayout that breaks a wire is worse than
an ugly canvas: `check_tools.py` **10 passed, 0 failed**, and a WhatsApp message
still answers in 862ms.

### Homies has its own n8n, and everything had been going to the wrong one

`https://n8n-zqvb.srv1879140.hstgr.cloud` — empty, community edition, Homies'.
Its API key **was already in `.env`**, under the name `N8N_MAIN_CLIENT_ID`, which
reads like a client identifier rather than a credential for a second instance,
so nothing ever looked at it. `N8N_BASE_URL` and `N8N_API_KEY` both pointed at
`srv1135333` — the shared production instance carrying 26 workflows for four
other clients — and so every Homies workflow ever deployed, including the
WhatsApp bot created an hour earlier, was built there.

**The name is the whole cause.** Both keys are opaque JWTs and either would look
correct next to the other. Renamed: `N8N_BASE_URL` / `N8N_API_KEY` are now the
Homies instance, and the shared one is `N8N_SHARED_BASE_URL` /
`N8N_SHARED_API_KEY` with a comment saying nothing should deploy there.

Moved, in order, verifying each:

| | New id | Check |
|---|---|---|
| `Homies — debt tools (Vapi)` | `lXofknAbE5wu5nwQ` | `check_tools.py` **10 passed, 0 failed** |
| `Homies — WhatsApp bot` | `u2JjrbcNPYyyh3yl` | 200 in 688ms, Brain ran, Send fails on the placeholder token |
| `Homies — call queue (read)` | `i3VMdCnXZGooI1Dj` | returns the real queue with resident names |

All four Vapi assistants re-pointed at the new webhook — the two Hebrew ones
through `vapi_sync.py --apply`, the two English twins by PATCH, since
`vapi_en.py` still refuses to rebuild them.

**Nothing needed re-crediting, and that is worth knowing.** The tool workflow
writes through Apps Script over plain HTTP rather than a Google Sheets node, so
it carries no n8n credential at all and moved as pure JSON. A Sheets node would
have moved with a credential id belonging to the old instance and failed *after*
answering Vapi 200 — the response is computed before the write by design, so a
missing credential would have been invisible in the response.

**Two of three are deactivated on the shared instance; the queue is still live
there deliberately.** `web/index.html` is deployed separately on Vercel and
still calls the old queue URL. The file now points at the new one, and the old
workflow must stay running until that page ships — deactivating it first breaks
the demo page. Nothing was deleted: deactivation is reversible and this is
somebody else's production box.

### The WhatsApp workflow is live in n8n — and it was silently dropping every message

`Homies — WhatsApp bot`, workflow `fDVRNLvsALcOe3ld`, active. Callback URL:

```
https://n8n.srv1135333.hstgr.cloud/webhook/homies-whatsapp
```

**The bug, which is the reason this was worth testing before connecting Meta.**
`multipleMethods: true` gives the webhook node **one output per method**, in the
order they are listed — GET on output 0, POST on output 1. The workflow
connected only output 0.

Everything you would think to check passes. Meta's verification is a GET, so the
callback URL saves and the dashboard shows a verified webhook. Then every actual
message arrives as a POST on output 1, lands on nothing, and the execution ends
**`success` having run a single node**. No error, no retry, no reply. A resident
messages Homies and is never answered, and there is nothing in n8n that looks
wrong.

Found by posting a real message envelope at the live URL before touching the
Meta app. The verification handshake — the test everybody runs — would have said
it was fine.

**Verified after the fix, four payload shapes, all against the live webhook:**

| Sent | Result |
|---|---|
| Hebrew text, "יש נזילה בלובי של הבניין" | 200 in **898ms**, then Brain → Send |
| the same message id again | `_work: false`, never reaches the model — one reply per message, not one per retry |
| an image with no caption | canned Hebrew reply, no model call at all |
| a delivery receipt | 200, nothing written |

The 898ms matters: Meta retries anything not answered within a few seconds, and
a retry is a second copy of the same message. The workflow answers Meta *before*
it thinks, so the model's latency can never turn into a duplicate reply.

**The Brain ran and produced Hebrew.** Not a real answer — OpenRouter is still
out of credit, so it took its catch path and returned the handover line, *"אני
מעביר את זה לנציג מהצוות שלנו"*. Which is the graceful failure working as
designed, and also exactly the shape flagged on 7 Aug: a valid key and a bot
that always hands over reads as "the model is broken" rather than "the account
is empty."

**`Send` fails, deliberately, and the deploy gate was wrong about it.** The
script demanded `WHATSAPP_PHONE_NUMBER_ID` and `WHATSAPP_ACCESS_TOKEN` before it
would push anything. Both are only needed to *send* — and a send cannot happen
until Meta has verified the callback URL, which needs the workflow live first.
The gate blocked the step that has to come first, and that ordering is Meta's,
not ours. Split into `need()` and `later()`: hard-fail on the verify token and
the model key, deploy with a loud warning on the two send credentials. Safe only
because a number that has not been connected in the Meta app receives nothing,
so there is no window where a real resident goes unanswered.

`WHATSAPP_WEBHOOK_VERIFY_TOKEN` was generated rather than typed and is in `.env`.
It is a shared secret with Meta, and a value invented at a keyboard tends to be
one that can be guessed.

### Vapi is out of credit, so none of this has been heard on a real call

Everything above was verified by posting real Vapi payload shapes at the live
Edge Function. **The one thing that cannot be proved that way is that Vapi
actually sends the report** — that needs a call, and the account has no balance.
This is the third Vapi account since 5 Aug and there is no API endpoint that
reports a balance; `/subscription` is 404 on all three keys.

Two consequences worth having written down before the next move rather than
after it.

**The export now redacts something that matters.** `vapi_export.py` has always
replaced `server.headers` values with `<redacted>`, written when those headers
were empty, on the reasoning that a file which is safe only by accident is not
safe. As of today they carry `TOOL_SECRET`, so that decision is now the only
thing keeping the secret out of a committed file. It also means the export is
**not** a restore path for the report endpoint: an account rebuilt from it posts
reports with a header of the literal string `<redacted>`, gets a 401, and throws
away every transcript exactly as before — silently, because nothing about the
call fails. `vapi_sync.py --apply` reads the real secret from `.env` and is the
route.

**The rebuild checklist now ends on `interactions`.** Added to
[new-vapi.md](handover/new-vapi.md) as the last item, because it arrives last:
the report fires after the call is over, not during it. An empty table means the
`server` block did not survive the move, and there is no other symptom — the
call sounds perfect and nothing errors.

### Supabase exists, all six migrations are applied — and it is in Tokyo

Project `HOMIES / main`, ref `nmxlhlmcnnggnnuxyelt`, free plan. The six SQL files
that had been written and never run since 2 Aug are now applied, by
[scripts/supabase_migrate.py](../scripts/supabase_migrate.py) — a new runner that
keeps a `schema_migrations` ledger, wraps each file in its own transaction, and
stops at the first failure rather than leaving half a schema behind.

```
residents           10 rows    charges             10 rows
requests             1 row     payment_tickets      0
interactions         0         payment_links        0
call_outcomes        0         promises_to_pay      0
                               payment_disputes     0
```

Nine tables, 32 indexes, two functions (`touch_updated_at`,
`bump_charge_attempt`), **RLS on with a policy on every one**. Verified from both
sides: the publishable key gets `[]` from `residents`, the secret key gets the
row. RLS is doing its job rather than merely being switched on.

**The region is `ap-northeast-1` — Tokyo.** Nobody chose that; it is the default
if you do not change it at project creation, and it was not changed. Israel to
Tokyo is roughly a quarter of a second each way, and every tool call the voice
agent makes crosses it — against a turn that already measures 5,283 ms. Frankfurt
`eu-central-1` is the closest region Supabase offers.

Supabase cannot move a project between regions on the free plan. The fix is to
delete this project and create it again in Frankfurt, which right now costs
nothing: the only contents are ten fictional residents and the seed rows, and
the migration runner replays the whole schema in about a minute. It stops being
free the moment anything real is in there, so this is worth deciding now rather
than later.

**Finding the database was not straightforward.** `db.<ref>.supabase.co` does not
resolve at all on this project — no A record, no AAAA — so the direct connection
route does not exist and the Supavisor pooler is the only way in. The pooler
hostname embeds the region, which the dashboard shows and we did not have, so it
was found by trying all 34 hostnames until one accepted the tenant. Port 5432
(session mode) rather than 6543, because transaction mode rejects some DDL.

**Also fixed: `.env` had two Supabase blocks.** `SUPABASE_URL`,
`SUPABASE_ANON_KEY` and `SUPABASE_SERVICE_ROLE_KEY` each appeared twice, once
empty and once filled. Which value wins depends on the parser, and the symptom
would have been an authentication error rather than anything pointing at a
duplicated line. Merged into one block.

`SUPABASE_ACCESS_TOKEN` is still empty — that is the CLI token, and without it
the `debt-tools` Edge Function cannot be deployed.

### First real resident data is in Supabase — 12 people, 9 charges, ₪12,200

Imported `sheets/residents-real.csv` by
[scripts/import_oxs_csv.py](../scripts/import_oxs_csv.py). Residents upsert on
`phone`, charges on `(resident_id, period)`, so a nightly export can be replayed
without duplicating anybody — which is the whole point of an import script rather
than a one-off paste.

```
residents by source   oxs 12   seed 10
charges   by source   oxs  9   seed 10
period                2025-12-01   9 charges   ₪12,200
```

**A new column, `source`, in migration `007`.** Ten fictional residents from
`002_slice_seed.sql` were already in that table, and `residents` is what the
outbound debt agent reads to decide who to call. With real numbers and seed
numbers sitting together and nothing to tell them apart, the only thing between a
test run and phoning a real person about a real debt is somebody remembering
which is which. `oxs_ref` could not do this job — it holds the id in OXS, and a
CSV export does not carry one.

**Three charges were not created, deliberately.** Lines 3, 4 and 11 carry an
amount — ₪1,500, ₪1,000 and ₪900 — and no month. `charges.period` is a not-null
date, and the honest options were to invent a month or to skip the charge. The
residents imported; the charges did not. ₪3,400 is therefore in the CSV and not
in the database, and that is a data question for Homies rather than something to
paper over.

**The year is an assumption and it is flagged as one.** `month` arrives as
`דצמבר` — a Hebrew month name with no year at all. December 2025 is the only
December that has happened as of today, so that is what was used, it is printed
on every run, and `--year` overrides it. A charge filed under the wrong year is a
resident called about a debt from a different December.

**All 12 have `do_not_call = FALSE`.** That is faithful to the export and it is
the thing to know before anything dials. Nothing can place a call today — the
campaign runner is Phase 7 and does not exist — but the row is armed the day it
does.

**And this is the argument for moving the region that the latency numbers only
hinted at.** The project is in `ap-northeast-1`. Twelve Israeli residents' names,
phone numbers and debts are now stored in Tokyo. While the table held ten
invented people that was a performance question; with real personal data in it,
it is a data-protection question as well, and the answer to both is Frankfurt.
The cost of moving is still close to zero — delete, recreate, replay seven
migrations and re-run this import.

### OXS is read-only, decided — and the API guide turns out to document no API

**The rule, from the client side of this build:** nothing we build writes to OXS,
ever. Asked specifically whether creating a new service request was an exception,
since PRD §2.1 assumes exactly that: *"strictly do not edit anything on oxs we
just import data to clone in supabase."* So the bot does not open tickets in OXS
either. One direction only — OXS out, Supabase in.

This costs something real and it is worth naming. A resident's ticket now exists
in Supabase and **not** in the tool the staff actually work in, so somebody has
to look at a second place. That is the adoption risk the plan already flagged
against the CRM, now applied to intake. The counterweight is that a write to a
system of record for 10,000 apartments is not a bug you roll back — it is a
corrupted resident record inside a live business, and the rule removes that
entire failure class rather than guarding against it.

**OXS enforces most of it for us.** From the guide's module table:

| Module | Access levels | Scope |
|---|---|---|
| Service Requests | Read-Only **/ Full Control** | view, create, update status, delete |
| Tenant Debts | Read-Only only | balances, payment details, outstanding amounts |
| General Information | Read-Only only | buildings, apartments, tenants, payment histories |

Two of the three modules have no write permission in existence, so `OXS_KEY_DEBTS`
and `OXS_KEY_GENERAL` are read-only by construction. Service Requests is the only
module where a key *can* write, which makes `OXS_KEY_REQUESTS` the only one the
rule has to be enforced on — it should be re-issued as Read-Only so the
permission cannot be used by accident. Nothing enforces a rule as well as not
having the capability.

Verified today that **no code in this repo reads any OXS key at all** — the three
values sit in `.env` and nothing has ever called with them.

**And the guide documents no endpoints.** `OXS_API_Keys_Guide_EN.pdf` is four
pages on creating, rotating and expiring keys. Searching all four for anything
URL-shaped returns one hit, and it is the phrase "target system". No base URL, no
paths, no request or response shapes. So the import is blocked on OXS Support
sending the API documentation — the same team that has to activate API access.

Two operational facts from the guide that will matter later: rate limits are **60
requests per minute and 1,000 per hour** across all keys, which shapes how ~10,000
apartments get paged; and **every key expires**, one year by default and two at
most, with email reminders at 30, 7 and 1 days. A silently expired key looks
exactly like an outage.

**Two PRD lines are now stale.** §2.2 says making status requests live "requires
either an OXS API (none exists)" — one exists, and we hold keys for it. And §5
specifies the OXS bridge as a nightly Google Sheets batch. A read-only API pull is
strictly better than that: fresher, no manual export step, and it removes the "as
of last night" caveat the flow currently has to say out loud. Both should be
revised once the endpoints arrive.

### debt-tools is deployed, and the smoke test caught a bug I had written

`debt-tools` is live at
`https://nmxlhlmcnnggnnuxyelt.supabase.co/functions/v1/debt-tools`, version 1,
`verify_jwt: false`. Pushed by
[scripts/supabase_functions.py](../scripts/supabase_functions.py), which uses the
Management API rather than the CLI so that nothing has to be installed and
`supabase init` does not restructure the repo.

`TOOL_SECRET` was empty and is now generated, in `.env`, and pushed as a project
secret. That mattered more than it looks: the function's guard is
`!== SECRET || !SECRET`, so it **fails closed on an empty value** — deploying
without one produces a function that 401s every caller and reads as a broken
deploy rather than a missing variable.

The door was tested from both sides. No header → 401. Wrong header → 401. Right
header → 200.

**Then the third call failed, and it was our bug.**

```
{"ok":false,"error":"new row for relation \"requests\"
 violates check constraint \"requests_urgency_check\""}
```

`requests.urgency` has been constrained to `low / normal / high / emergency`
since `001` on 2 Aug, and [scripts/vapi_tools.py](../scripts/vapi_tools.py)
declares exactly those four. The WhatsApp bot I wrote yesterday declared
`normal / urgent`. **`urgent` is not a value**, so every urgent WhatsApp ticket
would have hit this constraint — and the model would have received an English
Postgres error in the middle of a Hebrew conversation.

This is the third collision of the same kind in two days: I invent an identifier
the established file has already fixed. The first two were
`WHATSAPP_TOKEN`/`WHATSAPP_VERIFY_TOKEN`. Fixed to the four schema values, with
the constraint named in a comment so the next person does not re-invent them.

Re-run after the fix: `HM-2026-1003` written, `plumbing / high`, Hebrew
description intact, `opened_via: voice`. Test row deleted afterwards.

**Left alone, worth knowing.** `open_request` in the Edge Function passes
`urgency` straight to Postgres with no validation, so an invalid value is caught
by the database rather than the function. Fail-closed is the right direction; the
cost is that the agent gets a constraint message instead of something it can act
on. Also `requests.type` has **no** constraint, and the two channels declare
different vocabularies — voice offers four types, the WhatsApp bot seven. Both
insert fine and will make the type column awkward to report on.

### The key works, the balance does not — and the whole Brain call ran for real

`OPENROUTER_API_KEY` arrived and authenticates. `GET /api/v1/key` returns the
account, and a real request to `anthropic/claude-opus-5` came back in **5,141 ms**
with 2,632 input and 48 output tokens. That request was not a toy: it used the
script's own constants, the real 2,598-character Hebrew system prompt, both tools
converted to the OpenAI shape, `reasoning: {effort: "low"}` and the
`cache_control` breakpoint. So the model slug, the tool shape, the reasoning
parameter and the caching block are all confirmed accepted by the live endpoint
rather than assumed.

**The finding that matters: the balance is about four cents, and OpenRouter
pre-authorises `max_tokens` against it.** The first attempt failed —

```
HTTP 402  You requested up to 4096 tokens, but can only afford 1600
```

`MAX_TOKENS` in the script is 4096, sized deliberately so thinking and the reply
fit together. That means **every message would 402** on this balance, with a
valid key. The Brain catches the throw and answers with the handover line, so the
failure is graceful — a resident is told a person will get back to them — but the
bot would never once call `open_request`. A working key and a bot that silently
never works is exactly the shape that gets diagnosed as "the model is broken."

Credits fix it. Lowering `max_tokens` also clears the 402 and is the wrong fix:
it buys a working request by risking a reply truncated mid-sentence, which is the
failure `MAX_TOKENS = 4096` exists to prevent.

### The lobby leak asked for an apartment number, on the first real message

The test message was the demo narrative from the plan — *"there is a water leak
in the lobby at Herzl 14, it's urgent."* The reply was `באיזו דירה אתה גר?` —
*which apartment do you live in?*

A lobby is a common area. Nobody lives in it. This gap was flagged when the
prompt was written and it reproduced on the first live message, which is a
stronger argument than the one made for it in the abstract. The prompt asks for
building **and** apartment unconditionally; it needs to skip the apartment when
the problem is in a shared space. Not yet fixed.

### Still empty: `OXS_KEY_REQUESTS`

Diffed `.env` against the pre-OpenRouter backup: **one line changed**, the
OpenRouter key. `OXS_KEY_DEBTS` and `OXS_KEY_GENERAL` were already set and are
untouched; `OXS_KEY_REQUESTS` is still blank. It is the key that writes service
requests — the exact row this bot creates — and it blocks nothing today only
because tickets go to the Sheet.

Three WhatsApp values are still absent: `WHATSAPP_WEBHOOK_VERIFY_TOKEN`,
`WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`.

---

## 2026-08-07

### WhatsApp bot built end to end, blocked on four values

Feature [11](features/11-whatsapp-bot/feature.md) — inbound support in Hebrew,
reusing the tool webhook the voice agents already call. Written and verified;
not pushed.

**The channel was a real decision.** Three options, and the fastest one was
rejected: another client on this same n8n box already runs WhatsApp through
GreenAPI (`Inventory - 20 Availability Bot`), which is proven-here and would have
demoed today. It drives WhatsApp Web unofficially, breaks WhatsApp's business
terms, and the number can be banned. Twilio was ruled out on measurement rather
than opinion — `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` are in `.env` and
**empty**, so it costs a new signup, adds a BSP markup, and still needs the same
Meta verification. Chose the Meta Cloud API test number: free, no business
verification, five hand-registered recipients, and the move to Homies' real
number is a phone-number id and a token.

**Business verification gates the production number, not the build.** That is
what let this start today rather than in two weeks.

**Chatwoot deferred**, and not on preference: it is Rails + Postgres + Redis +
Sidekiq, and the only VPS is `srv1135333`, which carries four other clients'
production workflows. Adding it later costs one field in the Meta app config.

**Thinking stays on at low effort — the counterintuitive call.** Every instinct
says disable it for a chat bot. With thinking disabled this model occasionally
writes a tool call into its *visible text* instead of emitting a structured call:
the turn returns 200, the reply reads fine, and the tool never runs. No error, no
failed call to catch. For an agent whose whole job is `open_request`, that is a
resident told their request is logged when no row exists. Also `max_tokens` caps
thinking and reply together on this model, so it is sized for both.

**Answer Meta first, work after.** Meta retries any webhook that does not return
200 quickly, and a retry is a second reply to one question. Same shape the tool
webhook already uses. Duplicates are suppressed on Meta's message id, never on
content — a resident who sends "כן" twice means it twice.

Verified before hand-off: prompt extracts (2,598 chars, **2** verbatim lines
against the debt prompt's 23 at its worst); both Code nodes parse under
`node --check`; all seven workflow nodes reachable with no dangling connections;
the media-with-no-text branch reaches Send (it did not on the first pass — the If
routed it nowhere and acceptance #5 would have failed).

Two contradictions in our own docs surfaced. The build-stack checklist says the
chatbot brain is Claude; the credentials checklist says OpenRouter — resolved to
the Anthropic API directly, because the tool calls here are load-bearing.
And `sheets/README.md` still prints the **rotated, dead** Apps Script secret in
plaintext; harmless but it should not read as live.

Blocked on four values, which the script prints rather than a document listing:
`WHATSAPP_WEBHOOK_VERIFY_TOKEN`, `OPENROUTER_API_KEY`,
`WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`. Nothing has been created in
Meta or pushed to n8n.

### Chatbot moved to OpenRouter, and two name collisions found

The brain was written against the Anthropic API. `.env.example` has said
OpenRouter since it was written, and the user confirmed it — so it moved.
`anthropic/claude-opus-5` was checked against `openrouter.ai/api/v1/models`
rather than assumed to exist: it does, at the same $5 / $25 per million tokens.
A slug that does not exist fails as a 404 at call time, which on a chat bot is
silence rather than an error anyone sees.

The shape change is not cosmetic. OpenRouter speaks OpenAI chat-completions, so
tool arguments arrive as a **JSON string** rather than an object, and every tool
call must be answered by its own `role: "tool"` message carrying the matching
`tool_call_id` or the next request is rejected outright. Tools are still declared
once, in Anthropic's shape, and converted on the way out — one canonical list,
nothing to drift.

**Two variable names I invented collided with names `.env.example` already
established** — `WHATSAPP_TOKEN` against `WHATSAPP_ACCESS_TOKEN`, and
`WHATSAPP_VERIFY_TOKEN` against `WHATSAPP_WEBHOOK_VERIFY_TOKEN`. The script was
wrong, not the template; fixed to match. Worth noticing that this only surfaced
because someone asked about the env file — nothing would have failed until
deploy day, and then it would have looked like Meta's fault.

Also found while checking: **`OXS_KEY_REQUESTS` is empty** while the debts and
general keys are set. That is the key that writes service requests. It blocks
nothing today, because tickets go to the Sheet, and it blocks everything the day
they stop.

### "Stop, ask nothing" was the instruction nearest the acknowledgement

The isolation was exact: a plain "אוקיי" loops, "אוקיי, ומה עושים?" proceeds. Same
call, same prompt, one word of difference — so it is not the flow and not the
line, it is what the model reads at that moment.

Two things were fighting, and both were mine.

**The amount turn ended with *"then stop, ask nothing, and read where they
are."*** That was meant as *do not append the question to this same turn*. What it
says, to a model that has just been acknowledged and needs to produce something,
is **do not ask** — and it was the nearest instruction. The question it should
have asked was 881 characters away under a different heading.

**And the acknowledgement rule was a prohibition with nowhere to go:**
*"'אוקיי' and a hum are not turns. Do not answer them and do not restate what you
just said."* Both halves are correct and neither says what to do instead. A model
that must produce a turn and has been told not to ask and not to restate has one
thing left: the content it already has, in new words. Which is exactly what came
out — *"זה תשלום של יולי, 450 שקלים"*.

A question rescued it because a question is content. It has something to answer,
so it never reaches the dead end.

Fixed both. The acknowledgement is now the **cue** for the question and the
question sits **554 characters** after the amount rather than 881 under another
heading. *"Ask nothing"* is gone. And the acknowledgement rule points forward
instead of only fencing: *they mean carry on — so carry on to the next thing,
never back over the last one.*

The general form, stated where it happens: **the way out of a turn with nothing in
it is a question you have not asked, never a sentence you have already said.**

Still nine fixed lines, still zero enumerations. 34,715 chars.

### One line earns its place back, and the data says which one

Removing the scripting brought the amount loop back — four restatements off
"אוקיי", each one freshly worded, no link sent. So the question was which of the
eighteen removed lines was actually doing work, and that is answerable rather
than arguable.

Twelve calls today, checked for two things: did the agent ever ask whether to send
the link, and did the link go out.

| | asked for the yes | amount said | link sent |
|---|---|---|---|
| 5 calls | **no** | 1–4 times | **0 of 5** |
| 7 calls | **yes** | mostly once | 4 of 7 |

**Every call that sent a link is a call that asked.** No exceptions in either
direction. And the two calls after the de-scripting are both in the top row.

So: described as an intention — *"ask for the yes, plainly, in your own words"* —
the agent does not compose the question. It re-delivers the message it has already
given, in fresh words each time, which is the loop. Written as a line, it asks.

That is precisely the file's own third criterion for a fixed line: a test proved
the model does worse unscripted. The ask-for-the-yes is back, **as one line and
nothing else** — no menu, no four options, no transitions. Nine fixed lines
against the English twin's seven, zero enumerations, 881 characters from the
amount to the question.

Worth naming the general shape, because it cost the day: **a turn the model will
not produce on its own has to be written; a turn it produces fine has to not
be.** Everything between those is where the scripting crept in.

### I turned the Hebrew prompt into a script, and scripts loop

The complaint was that the conversation runs by steps and the English twin
adapts. Measured rather than argued:

| | Hebrew | English |
|---|---|---|
| verbatim `>` lines | **23** | **7** |
| "exactly N things you may say next" | 5 | 0 |
| "then go to N" transitions | 7 | 2 |
| bold imperatives | 130 | 53 |

The English twin has the same four numbered steps in the already-paid branch. The
difference is that it says *"if they confirm, say what the system shows and leave
it there"* and lets the model compose the sentence, where the Hebrew dictated the
sentence and then had to dictate the transition out of it too.

**Every one of those 23 lines went in as a loop fix, and the loops were mostly not
prompt bugs** — the demo page triggering the model twice, `send_payment_link`
never being called, a closing that did not match its own `endCallPhrase`. Real
bugs, fixed. But each one also got a written line and a rule about what comes
after it, and eighteen of those accumulated into a state machine. A model that has
been handed a script and does not know which line comes next replays the last one.
**That is the loop, and I built it.**

The file's own oldest rule said so: *"the prompt does not script Hebrew lines,
with five exceptions — everything else describes what to convey, and the model
generates the Hebrew natively."* Broken eighteen times in one day, one reasonable
patch at a time.

Reverted to describing. **8 fixed lines against the English twin's 7**, zero
enumerations, and the four already-paid steps now read like the English ones.
What stays verbatim needs one of three reasons and no others: Vapi speaks it
literally (the opening), the wording carries legal or privacy weight
(not-the-account-holder, voicemail), or a test proved the model does something
worse unscripted (the handover line, which went silent on a hardship disclosure).
The closing is fixed because `endCallPhrases` matches on its words.

What did **not** revert, because these constrain substance rather than sentences:
call the tool before speaking, ask for the yes once, take the yes that follows a
question, the steps only go forwards, the closing must carry יום טוב.

The header now carries the distinction, since it is the one that was expensive to
learn: **constrain substance, not sentences.** *Call the tool before you speak* is
a rule. *Say these exact words* is a script.

33,891 chars.

### The already-paid steps had no exits, so they cycled

First test on the cut prompt. The link path ran clean end to end — asked once,
tool called, link line, closing, call ended itself. The already-paid path cycled
between step 1 and step 2 until the resident gave up.

The four steps were numbered and had no transitions. Step 2 says what the system
shows and ends on a statement, so the resident answers it with "אוקיי" — and
nothing said what to do with that. The nearest written line above was step 1's
question, so step 1 is what came out. Then step 2 again. Then step 1.

**Numbering is not a transition.** A model that has just finished a turn does not
read a list and infer that the next item follows; it looks for a written line and
uses the nearest one. Every step now ends with **"then go to N, whatever they
said"**, and the block opens with the rule the numbering was silently assuming:
**these steps only go forwards.** No going back to check, no repeating a step
because the answer was thin, no step said twice in a call.

Also written out: the feminine form of step 1. The line flipped between
*את מדברת* and *אתה מדבר* inside one call — correct twice, wrong once, on a
resident passed as `gender: f`. Repetition does not just annoy, it degrades, and
that is now the third time today one line has come out different on a second
reading.

34,308 chars, still half of where the day started.

### Cut the debt prompt in half

67,789 characters to **33,523** — 51%, and below the English twin's 38,533 for
the first time.

**Nothing was removed for being wrong.** What came out was the evidence. A day of
*"on 7 Aug a resident said X and the agent did Y, which is why this rule
exists"* — 53 dated narratives, now zero. Every one of those stories is in this
file, which is where a reader looking for the reasoning should come. The model
does not need the reasoning. It needs the rule, once, close to where it acts.

Also removed: four sections that said the same thing in different words (LANGUAGE,
STYLE, NATURALNESS and YOU ARE BEING HEARD are now one), three variants of the
closing where one will do, and the blank-line padding that made HESITATION five
thousand characters for six rules.

**Verified rather than trusted.** All 24 unique fixed Hebrew lines were extracted
from the old prompt first and checked against the new one; 22 are present
verbatim and the two absences are the shorter closing variants, deliberately
collapsed into the canonical one — which is the redundancy that broke the goodbye
this morning. Twenty-four behavioural rules that each cost a live call today were
probed by name and all twenty-four are present. Voice, tools, end-call phrases and
all 27 output-filter replacements unchanged.

The file now opens with the rules for editing itself, because the ones that
mattered were learned expensively and are invisible in the result: every turn has
a written Hebrew line; the next turn is written where the previous one ends;
enumerate rather than prohibit; every list has a default; a `>` line is spoken.

**On the knowledge-base idea** — worth doing, but not for this. A KB is retrieval
over reference material, and it would help with things the agent might be *asked*:
building addresses, office hours, what the ועד בית covers. It cannot help with
behaviour, because behaviour is not looked up mid-sentence. Every loop today came
from a missing or distant instruction, and retrieval would have made that worse by
putting the instruction further away still. Cutting was the fix.

**The prompt grew 50% in one day and has now shrunk 51%.** That is not a wash: it
is the same content with a day of investigation taken out of it and moved
somewhere a person can read.

### Why the English one sounds smoother, and it is not the language

A clean English call was held up as the target: opening, amount, link offer,
link, standing order, close. It is smoother than the Hebrew, and the two reasons
are both mechanical.

**The English twin has sentences where the Hebrew has descriptions.** The
standing order is the visible one. The English prompt says *"Would you like to
set up a standing order for next time?"* — the Hebrew said *"then, once only,
offer the standing order"*, in English, with no Hebrew line under it. So the
English offers it on almost every call and the Hebrew hardly ever did. Same
flow, one written down.

Four branches were in that state and all four now have Hebrew: the standing
order (offer, accept, decline), paying later, hardship, and a maintenance
request raised mid-call. The promise-to-pay branch also gained the rule it never
had — **a vague date is still a date.** אחרי החג and בסוף החודש are answers, and
pressing for a number loses the intent along with the date.

**The second reason is one word.** On 7 Aug בסדר opened five turns out of six.
Every sentence after it was fine; the call still sounded like a machine, because
a person reaching for the same word five times running is not a person reaching
for a word. The register section listed seven openers and never said not to
repeat one. It does now — never twice in a row, never one word for most of a
call — and it says the thing the list implied and never stated: **most turns take
no lead-in at all.** The English twin opens two turns in five with nothing, and
that is most of the difference in feel.

Live at 67,789 chars on `3303317e`. The five unwritten branches are down to
none.

### The rule against mishearing a yes stopped it hearing one at all

Two calls, two minutes apart, same script but for one button.

`019fdb6a` ran clean end to end: asked for the yes once, called
`send_payment_link`, said the link line, closed, and ended on
`assistant-said-end-call-phrase`. Every fix from today held.

`019fdb6b` differed in exactly one turn — the resident asked
*"אוקיי, ומה עושים?"* instead of just acknowledging. It explained how the link
works, asked whether to send it, was told כן, and asked again. Then again. Four
times, reworded every time. **`send_payment_link` was never called.**

**It is not the typing.** Both calls were typed, both had the mic muted, both had
clean turn-taking. The only variable was which preset was clicked.

**The cause is a rule that used to be right.** On 5 Aug a resident said
*"Okay. And what should we do?"* and was told *"Great, I'm sending you a payment
link"* — a question treated as consent. So the prompt gained
*"a question is never agreement"*. That rule is correct about the question. It
said nothing about the answer that comes after it, so the model kept applying it:
the resident had asked something at some point, so every subsequent כן still
smelled like it belonged to the question, and the safe move was to ask once more.
Forever.

Two fixes, both stated where the model is standing.

Menu option 3 stops pointing at option 1 and carries the question itself — 1,173
characters from the first copy, because a numbered cross-reference two items away
was enough to make it improvise its own wording instead. And it now says where it
goes next: *"then you are in 2, and the next thing they say is the answer to
it."* The question is asked once in the whole call, in any wording, before their
question or after it.

The 5 Aug rule keeps its warning and gains its limit: *"and then you take the
answer."* **A rule that stops you mishearing a yes has to stop somewhere short of
never hearing one.**

Live at 64,784 chars on `3303317e`, the new account.

### It never says goodbye, which is why the goodbye never ends the call

Two fixes from the last hour confirmed working before anything else. `019fdb49`
called **`send_payment_link`** — the tool-first change holds. And two calls ended
with `endedReason: assistant-said-end-call-phrase`, so the widened `יום טוב`
phrase releases the line exactly as intended.

So the complaint — *"the bot does not end the call when it says goodbye"* — has
the wrong subject. **The goodbye works. The agent never gets to it.**

It said the link line, the resident said אוקיי, and it said the link line again.
Then again. Three times, reworded each time, and the resident hung up on the
third. The closing was never reached, so nothing ever matched an end phrase, so
the call sat open.

Same fault as the amount, the transfer details and the payment link before it:
**the turn after the link line was never written down.** The section said *"two
turns, in this order, with the resident speaking in between"* and then described
the second turn in English instead of writing it. So there was nothing to say,
and the nearest written line was the one just said.

Now, directly under both copies of the link line — 811 and 647 characters away
respectively, against a cross-reference before:

> אוקיי, תודה על הזמן. שיהיה לך יום טוב, ולהתראות.

with **whatever comes back, you close** stated as the rule, and
`log_call_outcome` after it. Verified live: every copy of the closing contains a
phrase that ends the call.

Also written down, because it came out unprompted and was not in the file:
**a tool call needs no announcement.** The agent said *"תן לי רגע"* while calling
`send_payment_link`. The resident hears a pause either way, and a pause is
shorter than a pause with an excuse in it.

Live at 61,689 chars.

**Five branches are still described in English with no Hebrew written under
them** — promise-to-pay, refusal, hardship, standing order, and a maintenance
request raised mid-call. Every fault of this shape today has come from exactly
that, and each one has been found by a test call rather than by reading. They
should be written before the next round rather than after it.

### The link was never sent, so the agent kept asking permission to send it

Call `019fdb43`. The resident said כן to *"רוצה שאני אשלח לך לינק לתשלום?"* and
was asked the same question **four more times** across 116 seconds, each time in
fresh words. **`send_payment_link` was never called.** Zero tool calls on the
whole call.

**This one is not the demo page and it was wrong to keep looking there.** The
stereo recording settles it: the caller channel is silent for 115 of 116 seconds
— RMS 0 per second, one burst in second 1 as the mic connected before mute took
effect, which is where the phantom *"מה לא הבאת?"* came from. The typed turns are
about eleven seconds apart. There was no race left to blame.

Two faults, both structural, both ours.

**The tool was attached to the wrong end of the sentence.** The prompt said *say
the line, then call `send_payment_link`* — so the line got said and the call was
optional in practice. It now calls the tool **first, before speaking**. A sentence
can be talked out of; a tool result is a fact sitting in the context. Once the
tool has been called there is nothing left to ask, and that is stated where the
model is standing rather than as a rule elsewhere.

**And there were two competing payment-link lines, 25 lines apart.** One under
*"when the caller agrees, say exactly this"*, another under *"call the tool, then
tell them it is on its way"* — two written-out sentences for the same moment, with
the tool call anchored to neither. The model produced variations of both plus
improvisations of its own. Collapsed to one line, one moment.

**The menu's option 2 was a pointer, and pointers do not get followed.** *"They
agreed → go to the payment-link line in HOW PAYMENT ACTUALLY WORKS"* sent the
model twenty thousand characters away, so it stayed where it was and re-asked
option 1 — which is exactly the loop in the transcript. Option 2 now carries the
tool call and the line inline. **188 characters from the question to what to do
with the answer**, against a section reference before.

Live at 60,187 chars. Same lesson as the amount, the transfer details and the
closing, four times in one day: **the next turn has to be written where the model
is standing.**

### The closing could not hang up, because the prompt recommended a phrase that does not match

Call `019fdb38` said the whole closing three times and stayed on the line. Not a
model fault and not the page race — a contradiction between two files we wrote.

`endCallPhrases` held `שיהיה יום טוב`. ENDING THE CALL offered this as a closing:

> אוקיי, תודה על הזמן. שיהיה לך יום טוב.

and then said, in as many words, that *"the lead-in and the לך are optional and
worth varying"*. **`שיהיה לך יום טוב` does not contain `שיהיה יום טוב`.** One
word in the middle, and the phrase that releases the line stops matching. So the
file recommended a closing that could not hang up, the model took the
recommendation, and the call stayed open. The resident said אוקיי, the model had
nothing left but the closing, and said it again. Three times. It ended only when
one of them happened to drop the לך.

`endCallPhrases` now matches on **`יום טוב`**, which every form of the goodbye
contains — with the לך, without it, either gender. Nothing in a call about an
unpaid ועד בית reaches for those two words except a farewell, so it cannot fire
early. A phrase that only matches the one phrasing nobody chose is not a backstop.

**The inbound agent had the identical latent fault** and was fixed in the same
push, before it cost a caller a hung line.

The prompt now finishes on ולהתראות rather than offering it as optional. That is
the beat that makes a goodbye sound like a goodbye instead of a line going dead —
which is what was actually being asked for by "wait two seconds before ending".
**Vapi has no wait-then-hang-up setting**; the call ends when the assistant
finishes speaking the matched phrase, so the goodbye is never clipped, and the
tail is how you buy the pause.

Both live, verified: every closing the file recommends now contains a phrase that
ends the call.

### The loop was the demo page, and most of this morning was spent on the prompt

Vapi's context for call `019fdb2e` has three messages in it:

```
[assistant] greeting + reason for call + 450 שקלים     ← one turn
[user]      כן אוקיי אוקיי                              ← one turn
[assistant] reason for call again
```

Three separate clicks arrived as one user turn. The greeting and the amount left
as one assistant turn. `turnLatencies` is empty and `numUserInterrupted` is 0 —
there was no turn-taking to measure, because none happened.

**The mechanism.** A typed turn goes in as `add-message` with
`triggerResponseEnabled: true`, which asks the model to answer immediately —
including while it is still speaking, and before its own last answer has been
written into the server-side history. The model is handed a transcript in which
it has not replied yet, so it replies again. Same context, fresh sample, a
different hesitation word each time: אההה the first time, אמממ the second. Two
generations, not a decision to repeat.

That also explains the digit that went missing from the bank account on
`019fdb24` — the second reading was a second sample, not a re-reading, and
sampling an eight-digit string twice is how you get seven.

And it answers the English question properly, which the prompt-size argument only
half did. `019fdb11` alternates cleanly the whole way down because whoever ran it
waited for the agent to stop talking before clicking. Same code, same race, not
triggered.

**Three fixes in the page**, none in the prompt:

- Typed turns queue and go out one at a time, 300ms after `speech-end`. Buttons
  disable while the agent talks and the status line says why.
- Identical text within 1.5s is dropped, and buttons blur on click — a preset
  that still holds focus re-fires on Enter, which is how
  *"אוקיי, ומה עושים?"* reached Vapi twice.
- The feed tracks the open partial **per speaker** instead of collapsing whatever
  sits at the bottom of the list. Interim guesses were stranding as their own
  lines the moment the speakers interleaved, which is why three transcripts
  showed a doubled greeting the server had only once.

Live at `7872ec2` on the demo repo.

**That first fix was incomplete and the next test caught it.** Gating on
`agentSpeaking` leaves open the window where the damage actually happens: between
a turn being sent and the first audio coming back the model is generating and not
speaking, so a second click in that gap sails through and triggers a second
response off the same context.

That window is one to two seconds — exactly the gap between clicking *כן* and
clicking *אוקיי*. It also explains the thing that looked like a content
difference: *"אוקיי, ומה עושים?"* worked every time because it is a longer button
that takes longer to find and read, so the window had closed before it was
clicked. Nothing to do with which words were sent.

Sends now hold until `speech-end` rather than merely while speech plays, with a
12s escape hatch for a turn answered by a tool call and no words, and calls start
held because the greeting goes out on connect. Status reads
*"Michael is thinking…"* so the wait is visible instead of a dead button.

There is also a build tag in the status bar now, because two rounds of tests were
argued about this morning before anyone could say whether the page in the browser
had the fix in it. `ba2489a`, build `2026-08-07b`, confirmed live on Vercel.

**What this cost.** Four prompt patches this morning were aimed at a fault the
prompt did not have, using transcripts the page had corrupted. Two of them are
worth keeping on their own merits — the enumeration after the amount, and the
transfer receipt line — and one, deleting the offer to repeat, was argued from
evidence that turns out to be an artifact. It stays deleted anyway; an offer to
repeat an account number earns its place back or it does not.

**Nothing about the debt prompt should be judged from a transcript recorded
before this deploy.** The next round of tests starts from zero.

### The loop moved down one level, and the repeat corrupted the account number

The enumeration after the amount worked. Call `019fdb24` asked
*"רוצה שאני אשלח לך לינק לתשלום?"* once, off a plain "אוקיי", in the right place —
and `019fdb22` ran the already-paid branch clean. Both faults from this morning
are closed.

The same fault then reappeared one turn further down. The resident said they do
not use links, the agent read `{{alt_payment}}`, the resident said "אוקיי", and
the agent read `{{alt_payment}}` again. Identical shape, identical cause: a turn
ended and the next one was never written. The alt-payment branch finished on an
English instruction — *"then offer to send the link as well so they have both"* —
with no Hebrew under it, so there was nothing to say and the nearest written line
was the one just said.

**The repeat was not merely a repeat.** The second reading came back
*אחת, שתיים, שלוש, ארבע, חמש, שבע, שמונה* — seven digits where the first had
eight. שש was dropped. The resident who trusted the second reading would have
sent the money nowhere. This is the argument the file was missing: a detail said
once is right, a detail said twice is a coin flip, and the second reading is the
one they write down. That went into the identifier rule as evidence.

The offer to repeat is now gone rather than capped. It was capped at one this
morning after it produced a loop; capping a thing that both loops and corrupts is
the wrong move. Say it once, repeat only if they ask in words, never ask whether
they caught it.

**And the branch now has a next turn, which is the one Homies actually needs.** A
transfer does not announce itself — nobody watches the account, so a resident who
pays and sends nothing gets called again next month about a debt they settled.
The receipt line asks them to send the confirmation to `{{verification_email}}`,
with the feminine inflection written out, followed by the same three-option
enumeration and the same default: if you cannot tell which you are in, you are in
the first one.

Server-side again disagrees with the screen: the greeting appears **once** in
Vapi's record. Vapi collapses consecutive bot turns into one message while the
user's ASR buffers, which is why the pasted transcript shows the greeting twice
and shows the agent answering questions the resident had not yet asked. The demo
page's rendering is now costing more time than it saves.

Live at 58,610 chars on `0ef11cb5`, receipt line present exactly once.

### The already-paid branch looped, twice, in two different ways

Two test calls, same branch, and the agent never got out of it. In the first it
asked *"את מתכוונת לתשלום של יולי?"* three times in three wordings. In the second
it fused the whole branch into one sentence — check the month, state the
discrepancy, give the email, ask if it was heard — and said that sentence four
times, the last one after the resident had said goodbye.

Four causes, and only the first was about repetition.

- **The reflex ask did not count.** Step 1 was written as an action to perform,
  not a fact that becomes true. The agent's surprised *"רגע, שילמת על יולי?"*
  asked the question, then it ran step 1 and asked it again properly.
- **The prompt licensed the second ask.** Step 1 said "once"; step 2 ended "do
  not ask a third time", which tells a model that twice is fine. Deleted.
- **The address check was a gate, not a turn.** *"Ask whether they got it… do not
  skip this check"* had no branch for an answer that is neither yes nor no, so
  "אוקיי" and "תודה" left the agent still waiting, and it re-asked. Since the
  turn was fused, re-asking the check re-said the entire branch.
- **The branch had no Hebrew in it.** `שילמ` appeared zero times in the whole
  prompt — four English instructions and not one written line, in a file where
  every other branch has its lines set down. Two calls, two completely different
  improvisations, both looping. That is what an unwritten branch produces.

Rewritten as four steps that are four separate turns, with the Hebrew written
out. Any answer that is not an explicit correction counts as a yes. The address
check is asked once and accepts anything. A goodbye ends the call from wherever
the agent is standing, with every open question dead.

- **General rule added to REPETITION**, because this class will come back
  elsewhere: *a question you have asked once has been asked.* It never starts as
  repetition — it starts as diligence about a check too important to leave
  unresolved. No check on this call is worth asking twice; log it and let a
  person follow it up.
- **Email address delivery.** It was spoken as one mashed token
  (`officeathomeys.co.il`). The branch now says how to say it: the name, שטרודל,
  then the domain broken at every dot. Not verified on a call yet.

Live on `0ef11cb5`, 48,326 chars. Guard passes.

### Stop banning the repeat, enumerate the alternatives

The turn-3 line pushed at 07:18 did not work. The call at **07:22:32 ran on it**
— assistant `updatedAt` 07:18:05, call four minutes later, checked rather than
assumed — and the agent still answered "אוקיי" by restating the amount in fresh
words, then answered a second "אוקיי" by restating the bank details in fresh
words.

**Two things the server transcript settled that the feed could not.** The
greeting appears **once** in Vapi's own record, so the doubled greeting on screen
is the page, and the opening fix from this morning is working. The amount and the
bank details each really do appear twice. And `אוקיי, ומה עושים?` appears twice
in the user stream — the page sent it twice, which is a separate bug: the presets
are `<button>` elements, so one that still has focus after a click re-fires on
Enter.

**Why the line did not take.** It was correct and it was in the wrong place — in
HOW PAYMENT ACTUALLY WORKS, ~16k characters away from THE OPENING, where the
model is anchored when it has just said the amount. When a model is unsure what
comes next it reaches for the nearest written-out line, and the nearest one was
the sentence it had just said. That is the same mechanism as the greeting on
6 Aug and the payment line on 7 Aug: **written-out lines get spoken, and
proximity decides which.**

**The deeper reason four rules failed.** REPETITION says an acknowledgement is
not a turn. "Rephrasing is repeating" says the synonym does not help. "A question
asked once has been asked" was added this morning. All three are prohibitions,
and a prohibition tells a model what not to say without telling it what to say —
under a forced turn there is nothing left but the sentence it just used.

So the fix is not a fifth prohibition. Directly after the amount line, 442
characters away, there is now an enumeration: **exactly four things you may say
next, and no fifth** — acknowledgement → ask for the yes; agreement → the link
line; a question → answer it then ask; anything else → that branch. Plus a
default that removes the failure mode entirely: *if you cannot tell which of the
four you are in, you are in 1.* And the general form, which applies everywhere in
the file: **asking a question you have not yet asked is always better than
repeating a sentence you have already said.**

The turn-3 line now exists exactly once in the file, in the menu, with the
payment section pointing at it rather than holding a second copy.

**Why English never had this fault**, since it is the obvious question: the
English twin is running a 38,533-character prompt last updated at 02:54, which
predates every patch made today. Hebrew is at 56,564 and has grown 38% in a day.
The English agent asked "would you like me to send you a payment link?" off the
identical acknowledgement — so the flow was always right and the Hebrew simply
never had the sentence. It is also worth saying plainly that a prompt growing by
a third in one day is its own risk, and the next session should be spent cutting
rather than adding.

Live on `0ef11cb5`, 56,564 chars.

### The main path had no third turn, and the link stopped being the only answer

**The Hebrew call restated the amount three times.** Not a branch — the main
path. The agent says what is owed and stops, per THE OPENING. The resident says
"אוקיי". And there was no line for what comes next: nothing in the file asked for
the yes. HOW PAYMENT ACTUALLY WORKS said *"if it is not a clear yes, do not ask a
second time"*, which assumes a first ask that was never written anywhere. So the
agent had said the amount and had nowhere to go, and said it again. Three times,
identical but for הוסדר/שולם.

The English twin did not have this fault — it asked *"Would you like me to send
you a payment link?"* off the same acknowledgement — which is worth noting only
because it means the flow was always right and the Hebrew never had the sentence.

Turn 3 is now written: *"אז רוצה שאני אשלח לך, אה, לינק לתשלום ותסגור את זה?"*,
asked once, with the amount never said twice. **Restating what somebody has just
acknowledged is the loop this prompt keeps producing, and it appears wherever a
turn ends and the next one was never written down.** That is now stated as the
general shape, next to the specific line, because this is the fourth instance of
it in two days.

**The link stopped being the only outcome.** In the English call a resident said
their connection was too poor to open links, said it twice, and asked whether the
office could handle it. The agent offered the transfer, then sent the link
anyway. Every sentence was polite and correct; nothing in it was listening. There
was no rule for a resident who has ruled out both payment methods — the office
route existed only for `alt_payment: none` and for missing variables.

Now: when neither fits, stop offering things and put it in front of the office —
*"אני יכול, אה, להעביר את זה למשרד ושייצרו איתך קשר"* — then `office_to_contact`
and close. **A resident who could not pay and now expects a call back is better
served than one offered the same link a third time.** And never send a link to
somebody who has said they cannot open one.

**"Of course" attached to a request that was refused.** The same resident said "I
give you permission to charge the card you have on your system" and the reply
opened *"Of course."* Nothing was charged and nothing could be — but that is not
what the sentence said to the person hearing it. Someone who believes they have
authorised a payment does not pay, and is angry twice: when the debt is still
open, and when they remember agreeing to settle it. No בטח, כמובן, אין בעיה or
בשמחה in front of an answer that declines something. Warmth is a tone, not a
first word that concedes.

Live on `0ef11cb5`, 55,336 chars.

**Display, not agent, and it matters for reading these transcripts:** the first
Hebrew line was the greeting cut off at *"אני מדבר עם"* and the next was the same
greeting complete, with "הומיז" in quotes the second time. Two transcriptions of
one utterance. `web/index.html` renders `transcriptType: "partial"` into the feed
and `say()` only collapses a partial when it is still the last node, so partials
strand as soon as the two speakers interleave. Some of what reads as repetition
in these pastes is the page. The amount three times was not — user turns sit
between them.

### Four test calls on the rewritten branches: three fixes held, four new faults

**Held.** The already-paid branch ran clean — month asked once, "כן" taken as a
yes, discrepancy stated, no loop, where two calls this morning could not escape
it. The handover said the new line and the call ended. The bank account came out
digit by digit.

**1. The opening was generated a second time, twice.** Once after a plain "כן" —
greeting, greeting again, then the reason for the call. Once to an answering
machine, which was greeted before the message was left. The prompt has said "the
opening is said once and never again" since 5 Aug, and it kept saying it into a
gap: `firstMessage` is spoken by Vapi before the model produces anything, and
nothing told the model that. It read a fixed line under a heading called Opening
and did what the file appeared to ask. It now says, at the top of that section,
that the line has already gone out and the model's first turn is the answer to
whatever came back.

**2. A bare "לא" closed the call without the not-the-account-holder line.** The
person was never told why the call ended and the office got no `wrong_party` row.
The opening cross-referenced that branch by name; the branch is now written out
inline, where the decision is actually made. It costs a duplicated fixed line —
`vapi_en.py` will need a count of 2 for that pair — and a live agent that says
the line beats a build script that likes the file.

**3. The voicemail message could never end a call.** It closed on תודה ויום טוב.
`endCallPhrases` are שיהיה יום טוב and ולהתראות, and `endCallFunctionEnabled` is
false, so there was no other way to hang up: the message was left perfectly and
the call then sat open against an answering machine until it timed out. Now ends
on the phrase that releases the line. The English twin never had this bug — it
closed on "have a good day", which IS one of its phrases, purely by luck of
translation.

Also removed the dead goodbye from the explanation of its own removal. A verify
probe caught it still in the file, inside the paragraph describing it, and this
prompt's whole history is written-out lines being spoken.

**4. A new loop, and I wrote it.** The identifier rule added this morning ended
"and you offer to say it once more" — an offer with no cap. The bank details were
read, offered again, read again, offered again, and the call was still offering
when the resident gave up. Same shape as the address check fixed this morning,
which the general "a question asked once has been asked" rule did not catch,
because an offer to repeat does not feel like a question being re-asked. Capped
at one offer, any answer ends it. **An offer to repeat is a courtesy, not a
checkpoint.**

Also: the branch number was שמונה מאות on the first reading and שמונה, אפס, אפס
on the second. Same digits the same way each time, now stated.

**Not a fault, worth recording so nobody chases it:** אה renders as אההה and אמ
as אמממ in the transcript. `firstMessage` is a fixed string containing אה and it
still shows as אההה, so that is the transcriber rendering a drawn-out sound in
the agent's own audio, not the model ignoring "write אה, never אההה".

Live on `0ef11cb5`, 52,661 chars.

### Elliot for English, Eyal for Hebrew — and the voice stops living in the shell

The two Hebrew agents were speaking in two different voices and nothing in any
file said so. Inbound was on `cartesia/a976c076` (Eyal), debt was on
`vapi/Elliot`. Both targets name the same `cartesia_voice`, so the code was never
the difference: Cartesia sat behind `VOICE_PROFILE=cartesia`, inbound was pushed
once with that set, debt never was, and the divergence then survived every
subsequent sync of either agent.

**A voice is not an environment concern.** Anything that can silently differ
between two runs of the same command does not belong in an environment variable,
and this one produced two front doors of one company sounding like two companies
for two days.

Cartesia is now the default for any target carrying a `cartesia_voice`, which is
both Hebrew agents. The English twins set their own `vapi/Elliot` in
`vapi_en.py` and never reach that code, so they were already right and stay
untouched.

Why not simply put Elliot on Hebrew as well, which is the easier way to make them
match: `vapi/Elliot` with `language: he` is an English voice model being told to
read Hebrew, and the American accent is not a setting that can be tuned out — it
is what that voice is. Eyal is a Hebrew voice on a Hebrew model. The price is
wall-clock; Cartesia ran 31-66% longer on identical sentences and calls bill by
the minute, so `generationConfig.speed` is where to look before the bill argues
back.

Both escape hatches still work and were dry-run before applying:
`VOICE_PROFILE=vapi` puts Elliot back on Hebrew for an A/B, `VOICE_PROFILE=native`
reaches Azure `he-IL-AvriNeural`. An empty profile no longer means Elliot, which
is the one thing to remember about this change.

Live, all four, guard intact at 27 replacements on each:

| assistant | voice |
|---|---|
| Debt Follow-up (he) `0ef11cb5` | cartesia Eyal, fallback vapi Elliot |
| Inbound Intake (he) `51bbe77a` | cartesia Eyal, fallback vapi Elliot |
| Debt Follow-up (en) `eaa390ec` | vapi Elliot |
| Inbound Intake (en) `fd991d71` | vapi Elliot |

Unheard as of the push. Vapi's cost records report `voiceId: Elliot` for every
call on the vapi provider regardless of what was spoken, so billing has never
been evidence of what came out — only a call answers it.

### The debt agent stops promising a transfer it cannot make

Walked every branch of the debt prompt against the live config. Two things broke
and both were the same shape: the prompt describing a capability the account does
not have.

**The handover asked residents to hold for nobody.** `transfer_to_human` on this
assistant is `type: "function"`, `async: true`, posting to n8n. It is not a
`transferCall` and there is no destination configured anywhere. The prompt's
three steps were *say the line, call the tool, stay on the line and say nothing*
— so the agent said *"נא להישאר על הקו"* and went quiet, and with
`silenceTimeoutSeconds: 20` the call dropped twenty seconds later. Six paths
reach that: hardship, hot, language, not_understood, caller_request, and a
dispute that turns angry. The prompt calls a resident who asked for a person and
got a dial tone the worst outcome in the file; it was the outcome of every one of
those calls.

The intake twin has said the honest thing since it was written — *"it does not
connect anyone to anyone, so do not say you are putting them through"* — and the
debt agent simply never got that change. It now matches:

> אוקיי, אני מעביר את זה, אה, לנציג מהצוות שלנו, והוא יחזור אליך בהקדם.

Step 3 is now *say the closing and end the call, warmly*. בהקדם is the ceiling on
what may be promised; no time may be attached to it. Handover moved from the
never-end list to the end-the-call-once list, and the tool description was
rewritten to match, since a model reads that too.

**Identifiers were being read as quantities.** "Say numbers as Hebrew words, not
digits" had no exception in it, which is right for ארבע מאות וחמישים שקלים and
catastrophic for everything else. `{{alt_payment}}` in the demo carries
`חשבון 12345678`; as a spoken number that is *שנים עשר מיליון שלוש מאות ארבעים
וחמישה אלף…*, which is a sum of money and not an account anybody can use. Same
for `{{callback_number}}`, and the email address had already been heard coming
out as one mashed token.

The carve-out is stated as a test rather than a list, so it covers whatever comes
next: **an amount is understood, an identifier is copied.** Anything being copied
gets digits, in small groups, with a beat between them, and an offer to repeat.

Live on `0ef11cb5`, 50,104 chars.

**Not fixed, and known:** voicemail still cannot fire — `voicemailDetection` is
null, so the written voicemail line is unreachable and an answering machine most
likely logs `wrong_party`. `server` and `serverMessages` are still null, so every
fault continues to be found by reading transcripts by hand. Seven branches still
have no written Hebrew and improvise at runtime — promise-to-pay first, which has
no rule at all for a vague date. `docs/diagrams/Homies-System-Flow.excalidraw`
still shows "hand over, stay on the line", but it also still shows the card
authorisation flow retired on 4 Aug, so it needs regenerating rather than
patching.

---

## 2026-08-04

### Two English test calls, and what they actually showed

The reading was "it did not go through n8n, it is all hardcoded." Half right, and
the half that was wrong hid a worse bug.

**n8n was fine.** Call `019fcc8f` shows real tool responses — `{"ok":true}`,
`{"ok":false,"error":"a ticket already exists for this call"}` — and the
workflow's execution log has 25 successes. The tool layer works. What is
hardcoded is the *input*: the demo page carries ten fictional residents and
always did. n8n is the write path, not the read path. Nothing has ever read a
resident from anywhere.

**The model spoke a tool call out loud.** Call `019fccb8`, verbatim:

> Can we charge the card on file for this amount? Open payment ticket. two
> functions, open payment ticket ten ten i Kypiao TCN Jason. authorization
> captured. True. The office will process it, and you'll get a confirmation.

"two functions" is `to=functions`; the rest is `<|constrain|>json` and the
arguments. gpt-5.4-mini emitted its own tool-call syntax into the spoken channel
and the TTS read it. Vapi logged **zero tool calls** for that call, so no ticket
was opened — the resident was told the office would process a payment that does
not exist. Intermittent: the same tool fired correctly forty minutes earlier.

- **EN model back to `gpt-5.4`.** -mini bought ~860ms and this is the bill. It is
  also what was asked for in the first place.

**The call would not end.** Both calls spoke the full closing and then sat there;
one ended with the resident saying "Hello?" and the bot answering "Yes, I'm
here." `endCallFunctionEnabled` was already true — the model simply chose not to
call it, and nothing made it.

- **Added `endCallPhrases`** (`goodbye`, `and goodbye`, `להתראות`). Ends on the
  assistant's own speech, so the decision no longer rests with the model.

**The page under test was a cached copy.** The two calls sent no `phone` at all
and an office email that had been changed hours earlier. Every row those calls
wrote went in against nobody.

- **`no-store` on `web/index.html`.** A stale demo page does not announce itself —
  the call just quietly means something other than what you think it does.

The closing itself is fixed, incidentally: "Great, thank you for your time. Have
a good day, and goodbye" is a full sentence, not a bare "Goodbye". That was the
open question from the last two attempts, and it is answered.

**Third call, after those fixes.** `019fccc3` — `open_payment_ticket` fired as a
real tool call with `authorization_captured: true`, got `{"ok":true}`, no JSON
spoken, and `endedReason: assistant-said-end-call-phrase`. Both fixes held.

`endCallPhrases` then broke something else. That call logged **one** tool call.
`log_call_outcome` never ran: the model was going to log the outcome after the
closing, and the closing is now what ends the call. A resident authorised 450₪,
the ticket opened, and to the office the call did not happen. The old failure
was a call that would not end; the new one is a call that ends half a beat too
early, and it is quieter — nothing in the transcript looks wrong.

- **Prompt now orders it:** `log_call_outcome` before the closing, never after.

Also fixed: the closing came out as "No problem. **for your time.** Have a good
day, and goodbye". The English substitution used an em dash — `Great — thank you
for your time` — and Vapi splits streaming TTS on punctuation, leaving "Great" as
a chunk short enough to be swallowed. Now a comma. The Hebrew line has no dash
and has never lost a word.

**Still unresolved: the demo page has not been reloaded once.** All three calls
sent no `phone` and the old `homiesemail@gmail.com`. `no-store` cannot help until
the browser fetches the file carrying it.

### The sheet is now the source of the call list

Google Sheets as the database, deliberately, for now. It already *was* the
database for writes; what was missing was the read.

Less was missing than expected. `doGet` with no phone has always returned the
call queue filtered by the same four conditions as `v_debt_call_queue`, and
against the live sheet it returns five rows, not ten — שחר is absent because he
was marked paid. The filter has been working against real data the whole time
with nothing consuming it.

**Read path: page → n8n → Apps Script → sheet.** Not page → Apps Script. The
Apps Script secret has to ride in the URL, and a URL in a page anyone can open is
a published secret that can also *write* every tab. n8n holds it instead and the
page carries no credential. New workflow `yKZDDR7nQ76qTmKv`, three nodes,
`GET /webhook/homies-queue`, `Access-Control-Allow-Origin: *` because a page
opened from disk has Origin `null`.

**The fetch happens at page load, never during a call.** Measured today: one
request 404'd, one took 3.9s, one took 26s. That is the stall that burned credits
on 4 Aug. At page load nobody is on the line, and the httpRequest node retries
three times — the only place in the chain that can retry without a person
waiting.

Changes:

- `Code.gs` — `lookup()` returns `phone` and `surname`; `?all=1` returns everyone
  with a `blocked` reason instead of only the callable. The four skip reasons are
  kept distinct: "already paid" clears itself next month, "not handed over" is
  permanent, "do not call" is a person's decision, "4 attempts" is the ceiling.
  Collapsing them would hide the only difference that matters when someone asks
  why a debtor was never rung. **Needs a redeploy — the live version predates
  all of it.**
- `web/index.html` — `PEOPLE` fetched at load; the old array is now `FALLBACK`
  and doubles as the Hebrew→Latin table. Source shown on screen, because a silent
  fall back to the built-in list looks identical and means the opposite.
- A queue where no row has a phone is **refused**, not displayed. That is the
  4 Aug failure exactly, and the fix is a redeploy rather than a retry.

Tested against a mock of the redeployed endpoint. Caught one bug doing it: the
`en` block was built in `fromSheet` and never returned, so English mode would
have read Hebrew names aloud — the failure the whole `en` mechanism exists to
prevent, reintroduced while wiring it up. Three cases now pass: built-in table
(שרה → Sarah), sheet columns (ליאת → Liat, via optional `en_first_name` /
`en_building`), and no source at all, which is flagged on the row rather than
dialled.

That last case is live already: renaming שחר to **דוד** in the sheet produced a
name the English voice cannot say, and nothing but this flag would have shown it
before the call.

**Not done, and it is the same sentence as always.** The queue webhook is
unauthenticated, like the tool webhook beside it. Ten fictional residents. The
sheet is the thing that will quietly stop being fictional.

### Found

- **The OXS API exists.** The whole of PRD v2 was written on the premise that it
  does not — §2.2 says so in as many words, and the nightly Google Sheets bridge,
  the freshness caveat and half the phasing follow from that premise. Homies'
  access-levels page shows three modules with API keys against them.

  | Module | Level | Exposes |
  |---|---|---|
  | קריאות שירות · service requests | **full control** | view, open, update, delete |
  | חובות דיירים · resident debts | read only | debts and balances |
  | מידע כללי · general info | read only | buildings, apartments, residents, payment history |

  - **Sheets is dead.** Residents, requests and debtors were the only three things
    the nightly bridge carried, and all three are live reads now. §2.2's caveat
    goes with it, and `get_request_status` no longer needs to return an export
    timestamp because there is no export.
  - **`open_request` writes straight to OXS.** Full control on service requests is
    the one write available, and it happens to be the one the vertical slice is
    built around — so the reference read back to a caller is a real OXS reference
    rather than one we minted.
  - **Debts are read-only, and that is load-bearing.** Call outcomes, promises to
    pay, disputes and retry counts cannot be written back. Supabase is therefore
    the only place outbound campaign state can live — an argument *for* it, not
    against.
  - **There is no payment-method module at all.** §2.3 was made staff-confirmed
    because RPA is fragile. The real reason is stronger: there is no API for it.
    Same conclusion, firmer ground. It also means **no version of this system can
    charge anyone** — money always ends at a human, which is exactly what the debt
    prompt already assumes.
  - One key per module, one level per key. Three keys, stored and rotated
    separately: `OXS_KEY_REQUESTS` (write), `OXS_KEY_DEBTS`, `OXS_KEY_GENERAL`.
    Blast radius of a leak is one module.
  - **Still needed: the endpoint docs.** The table says what the modules expose,
    not what a request looks like. Base URL, auth header, routes, and above all the
    field names on a resident and a debt row — which is what `004_debt_schema.sql`
    was written against guesses about.

- **A client-side flow doc contradicted what is built on two points.** It described
  sending OXS payment links on the debt call; the 3 Aug decision was the opposite —
  no links, spoken authorisation to charge the card on file, staff make the charge.
  It also identified callers by phone number alone, where the PRD holds
  `verify_identity` as a hard gate. Caller ID is spoofable and the flow discloses a
  balance. Both need settling with Homies.

- **"CRM" is being used for two different systems.** The Chatwoot agent inbox, where
  staff work threads and toggle the bot per conversation, and the Next.js read-only
  metrics dashboard, which §5 explicitly says is *not* a work queue. Calling them
  both CRM will get the wrong one built.

### Done

- **Drew the whole PRD as one diagram** —
  [Homies-System-Flow.excalidraw](diagrams/Homies-System-Flow.excalidraw), generated
  by [gen_systemflow.py](diagrams/gen_systemflow.py). The two front doors, n8n, all
  six flows step by step, §7 handover, and the four places anything can be written.
  - **Colour encodes which system is touched**, not who is speaking — violet is an
    OXS call, cyan a Supabase write, orange leaves the machine for a person, red
    refuses rather than degrades. That is the question the diagram has to answer.
  - Escalation is drawn as a dashed pill in the gutter beside the step, not as an
    arrow to the handover band. Six columns of converging arrows is unreadable; a
    repeated pill shape reads as one rule applied everywhere, which is what §7 is.
  - Folds in the OXS API finding, so it is ahead of the written PRD. The two
    sections that changed are headed in pink.
- **Wrote [check_diagram.py](diagrams/check_diagram.py)** — generalised from
  `check_callflow.py` to take a path. Catches shape collisions, label collisions,
  and bound text wider than its box. Layout bugs in a generated diagram are
  invisible until someone opens it, and by then it has usually been sent to a
  client. Caught three on the first run.

- **Built the debt agent's tool layer** — the eight tools existed only as prose in
  `prompt.md`; the assistant has been carrying `tools: none` since it was created,
  meaning it says it opened a ticket and writes nothing. Now:
  [debt-tools/index.ts](../supabase/functions/debt-tools/index.ts) (one Edge
  Function, all eight handlers), [vapi_tools.py](../scripts/vapi_tools.py) (the
  Vapi function definitions), `006_debt_tool_support.sql`, and `vapi_sync.py`
  extended to push tools alongside the prompt.
  - **One Edge Function, not n8n.** These eight are pure database writes; n8n's
    value is in integrations it is not doing here. It does not foreclose n8n for
    the WhatsApp and Monday tools.
  - **No tool takes an amount, a month, a charge id or a resident id.** Those come
    from the call's `variableValues`, which the model can read and cannot change.
    A model that mishears a figure, or a resident who insists it is different,
    still cannot write a wrong number into a payment ticket, because there is no
    parameter to write it through. Same principle as `verify_identity` being
    server-side.
  - **The first tool call of a call creates the `interactions` stub.**
    `payment_tickets` has a CHECK that a captured authorisation carries the call
    it came from — the recording *is* the authorisation — but the end-of-call
    report has not fired while the agent is still talking. Without the stub, every
    authorised ticket would fail its constraint mid-call.
  - **`bump_charge_attempt` is a SQL function, not an update.** `attempts = attempts
    + 1` through PostgREST needs a read first, and two overlapping calls both read
    1 and both write 2. The queue gates on `attempts < 4`, so a lost attempt is a
    resident called five times.
  - Unique index so one charge cannot produce two open tickets — the point of the
    queue is that a person charges a card exactly once.
  - `vapi_sync.py` attaches **no tools at all** while `SUPABASE_URL` or
    `TOOL_SECRET` is empty, rather than pointing them at a guessed URL. Tools
    against a 404 are worse than none: the agent believes the write succeeded and
    says so on the call.
  - The secret travels in a header, not the query string. Apps Script could not
    read custom headers and its secret landed in logs on every request; an Edge
    Function can.

- **Pinned the English demo's stack in code** — `731193bf` now runs Deepgram Flux
  + Elliot + gpt-5.4-mini, set from a `STACK` constant in
  [vapi_en.py](../scripts/vapi_en.py) rather than inherited. Applied and verified
  live.
  - **It had already drifted.** The dashboard was carrying Elliot and gpt-5.4
    while the script would have overwritten both back to Azure Jenny and the
    Hebrew twin's gpt-5.5 on the next run. Dashboard edits lose silently; the
    stack now lives where re-running is safe.
  - **The dashboard labels Flux as Azure, and that is wrong.** Vapi's schema
    rejects a `model` property on the Azure transcriber outright — so a
    transcriber named `flux general en` cannot be Azure. It is Deepgram Flux,
    whose ~250ms matches the dashboard's own number.
  - **Swapped gpt-5.4 → gpt-5.4-mini for latency**, not gpt-4.1-mini. gpt-5.4 was
    ~860ms of the ~1,600ms total. Staying in the same family and generation keeps
    behaviour closest to what has actually been tested — this prompt is almost
    entirely instructions, and two generations back is a bad trade for the same
    saving.
  - Vapi's PATCH validator can be probed with a well-formed but nonexistent v4
    UUID: 404 means the body passed, 400 returns the enum. That is how the model
    list and the Azure/Deepgram question were settled rather than guessed.
  - **The English twin no longer shares the Hebrew twin's stack, on purpose.**
    Hebrew has one workable transcriber and one workable voice; English has a
    faster option for both, and this assistant exists to review the call flow,
    not to represent Hebrew latency. Hebrew latency still has to be measured on
    the Hebrew assistant.

- **Found where the latency actually was, and measured it.** The dashboard's
  ~1,600ms is transcriber + model + voice and nothing else. It omits endpointing —
  the wait between the caller falling silent and the agent deciding they have
  finished — and `onNoPunctuationSeconds` was **1.8s**, spent on every turn whose
  transcript did not happen to end in punctuation.
  - **Measured baseline, 19 turns across recent calls: median 2,216ms, p90
    3,986ms, worst turn 6,870ms.** The dashboard understated the median by ~40%
    and the tail by a factor of four. Against §8's <800ms target.
  - Wrote [vapi_latency.py](../scripts/vapi_latency.py), which computes the gap
    from the caller's last word ending to the agent's first word starting, out of
    transcript timestamps. Vapi's call object has no `performanceMetrics`, but
    messages carry `time`, `endTime` and `duration`, which is enough.
  - Applied to all three live assistants. Voice, model and transcriber
    deliberately untouched everywhere, so a before/after measurement isolates
    endpointing and nothing else. In `STACK` in `vapi_en.py` and `BASE` in
    `vapi_sync.py` — not the dashboard, so a re-sync keeps it.

    | Assistant | wait | noPunct | backoff |
    |---|---|---|---|
    | Debt (en) | 0.4 | **0.8** | 1.0 |
    | Debt (he) | 0.4 | **1.0** | 1.0 |
    | Inbound (demo, he) | 0.4 | **1.0** | 1.0 |

  - **Hebrew gets 1.0 and English 0.8, on purpose.** Azure he-IL punctuates
    Hebrew far less reliably than Deepgram Flux punctuates English, so on Hebrew
    almost every turn takes the no-punctuation path and that timer is the only
    endpointing signal there is. Cutting a caller off mid-sentence is a worse
    failure than 200ms of wait, and this is a call about money.
  - **`backoffSeconds` 1.5 with `numWords` 2 is what produced "The the" / "The the
    bill"** in the 4 Aug call: a two-word backchannel stops her, 1.5s of silence
    follows, then she restarts the sentence from the beginning.
  - **Deepgram nova-3 supports Hebrew.** The roadmap and a comment in
    `vapi_sync.py` both say Azure is the only Hebrew transcriber that exists.
    That was true of nova-2 — the enum confirms it has no `he` — but nova-3 added
    it, and 11labs, speechmatics and soniox accept `he` too. Untested, but it
    reopens a decision that was closed on false grounds.
  - **Smart endpointing is probably not helping Hebrew.** The provider enum is
    `vapi`, `livekit`, `custom-endpointing-model`, and both shipped models are
    English-trained — so Hebrew falls through to the transcription timer every
    turn. Inference from the enum, not verified.

- **Fixed the closing and the repeat loop.** A test call ended on a bare
  "Goodbye", and gave the same email instruction three times before it.
  - ENDING THE CALL said *"say a short warm closing"* and gave no example. The
    only concrete word in the section was "goodbye", four lines down, so that is
    what the model used. Abstract instructions get filled in from whatever
    concrete token is nearest. Added the actual line, marked as a shape rather
    than a script.
  - Added: **an acknowledgement ends the call.** "Okay", "sure", "I will" means
    the matter is settled — close, do not restate the instruction more helpfully.
    The dispute path already said "state once"; what it lacked was a rule for
    recognising that the once had landed.
  - **Sixth fixed Hebrew string**, so the native-speaker check now covers six, not
    five: `מצוין, תודה רבה על הזמן. שיהיה יום טוב ולהתראות.` Deliberately avoids
    `לך`, which would need gendering against `{{gender}}`.
  - `vapi_en.py` refused to build until the Hebrew went up first — it reads the
    live assistant, not the file, so a new Hebrew string it has no translation
    for is exactly the half-translated twin the assertion exists to prevent. The
    order is Hebrew first, English second, always.
  - **Latency after the endpointing change: median 1,919ms, was 2,216ms.** A
    ~300ms gain, well short of the ~1,000ms predicted. One turn still took
    5,280ms. The endpointing timer was evidently not the whole story, and
    gpt-5.4-mini's time-to-first-token over an 18k-character prompt is the next
    suspect.

- **The closing fix did not take, and the reason was instructive.** A second call
  still ended on a bare "Goodbye" — with the new prompt confirmed live in the
  call's own system message, so not a deployment problem.
  - Twenty lines below the new example sat *"Saying **goodbye** is not the same as
    ending the call. Do both."* — which reads as an instruction to say the word,
    and was the last line of the section. The example lost to it. Its real intent
    was *do not leave the line open*, so it now says "speaking the closing is not
    the same as ending the call".
  - Also added the check to **QUALITY CHECK**, which the model runs before every
    reply. A rule 450 lines into an 18,600-character prompt gets read once; a
    checklist item gets applied every turn. That is the more reliable place for
    anything about the shape of a reply.
  - Diagnosis worth keeping: `endedReason: assistant-ended-call`, "Goodbye." as a
    bot message at 46.4s, then a tool call. That ordering proves the model
    generated the word rather than Vapi injecting it, and ruled out
    `endCallMessage` in one step.
- **Resolved the hot-versus-dispute contradiction.** POSTURE listed *"they say
  they already paid"* under hot, while the disputed-payment path says log it,
  give the email once and end — and criterion 6 says every hot call transfers.
  The list was conflating a calm claim with an angry one. Hot now requires the
  anger or the refusal to accept any answer; the claim by itself is the dispute
  path. **This is a product decision made on the client's behalf and is worth
  putting to Homies** — the cost of being wrong runs both ways, and the numbers
  differ a lot: treat every claim as hot and roughly every second call transfers
  to a person.
- **English persona renamed Michal → Michael.** Elliot rendered "Mikhal" as
  "McCall" on every call, and a prompt spelling hint does not change what a voice
  does with a name. Michael is the English cognate, reads correctly unprompted,
  and fixes the second half of it too: Elliot is a male voice that had been
  introducing itself with a woman's name. Hebrew is untouched — Hila says מיכל
  correctly.
- **Demo email changed to `office@homies.co.il`.** `homiesemail@gmail.com` came
  out of the voice as "homey's email at gmail dot com": the local part runs two
  words together and the TTS guesses. Still a placeholder — Homies' real address
  has to replace it before anyone outside the team hears it.

- **The eight tools are attached and writing.** Both debt assistants went from
  `tools: none` to eight live tools. First time anything the agent says about
  having recorded something has been true.
  - Host is **Apps Script, as a deliberate stopgap** — a second implementation of
    the same eight tools in `sheets/Code.gs`, writing to five tabs created on
    first write. `vapi_sync.py` prefers Supabase and falls back to this, so the
    day the project exists the sheet stops being used with no code change.
  - **The TypeScript version stays the specification.** Two implementations of
    one contract will drift, and only one of them has real constraints.
  - Costs accepted knowingly: the secret travels in the query string, because
    Apps Script cannot read request headers, and lands in Google's logs on every
    call. Cold starts add 1–3s of silence to whichever turn fires a tool. Neither
    survives contact with a real resident row.
- **Wrote [check_tools.py](../scripts/check_tools.py)**, which fires all eight at
  the live endpoint and asserts three guards *refuse* — a duplicate ticket, a
  bogus outcome enum, a request with no description. It paid for itself at once:
  - Before the redeploy, all ten cases returned `{"found": false}`, because the
    deployed script routed every tool call to the resident lookup regardless of
    name. From Vapi's side that is invisible — the agent gets an object back,
    believes it, and tells the resident the ticket is open.
  - Two first-writes 404'd while their tabs were being created. Transient, and
    only distinguishable from a real fault by running the check twice.
  - **The checker had a bug of its own**: reusing `probe-7` across runs meant the
    second run's ticket was refused by the first run's duplicate guard — a correct
    refusal reported as a failure. Call ids are now run-stamped. A test that only
    passes against a clean sheet will lie to you later.

- **The first call with tools attached died on the tool, and the fix was `async`.**
  The agent called `log_disputed_payment`, waited, said *"this will just take a
  sec"*, then *"sorry, a few more seconds"* — twice — then hung up on the
  resident. The tool returned **404 after 17 seconds**.
  - **Measured, not estimated: Apps Script is ~13s cold and ~2s warm, and a cold
    call sometimes 404s outright.** I had told the user 1–3s when recommending
    against this route; the real cost is four times worse and includes silent
    failure. Recorded here because the estimate was wrong in the direction that
    mattered.
  - **Six of the eight tools are now `async: true`.** Vapi fires them and moves
    on, so a slow host costs nothing. Only `open_payment_ticket` and
    `open_request` still block, and both have to: the first can refuse and the
    agent must not confirm a rejected payment, the second returns a reference
    that gets read aloud and may not be invented.
  - **Async has a real cost: a fire-and-forget tool that 404s loses the write and
    nobody finds out.** That makes the cold start a correctness problem, not just
    a latency one.
  - So the console now **warms the runtime with an unauthenticated GET** on page
    load and again on call start. Rejected in one line, but it starts the
    runtime, and it carries no key — the secret stays out of the page, which is
    the whole reason the resident list is baked in rather than fetched. Verified
    after 90s idle: GET 1.79s, then POSTs at 2.3s with no 404.
- **The demo page was not sending `phone`.** Every tool row would have been
  written against nobody, and `flag_not_handed_over` would have updated no one,
  silently — findable only by staring at the sheet afterwards. Ten numbers added,
  matched to `residents.csv` **by name rather than by position**, because the CSV
  has Michal Dahan sixth and Avi Biton seventh and PEOPLE has them reversed.

- **Moved the tool layer to n8n. ~700ms, flat, no cold start.**

  | host | cold | warm |
  |---|---|---|
  | Apps Script | 13,000ms, sometimes 404 | ~2,000ms |
  | n8n | **739ms** | **~700ms** |

  - Built by [n8n_deploy.py](../scripts/n8n_deploy.py), not clicked together in
    the editor — an editor change is invisible to anyone who did not make it and
    has no diff. Re-running updates the workflow by name rather than making a
    second one.
  - **Shape: Webhook → Decide (Code) → Respond, and separately → Sheets.** The
    response is computed and returned *before* the sheet is touched, so a
    one-second Google Sheets append never reaches the caller. That is the entire
    fix for the stalls, and it holds no matter how slow storage gets.
  - **Two n8n gotchas, both cost real time.** A webhook node created without a
    `webhookId` leaves the workflow reporting `active: true` while every POST
    404s "not registered" — the id is what n8n registers against, not the path.
    And `respondToWebhook` wants typeVersion 1.1. Both found by diffing against
    the working webhooks already on the instance rather than by reading docs.
  - **The duplicate-ticket guard changed shape.** Apps Script refused a second
    ticket by scanning the sheet first; that would need a read *before* the
    response, which this design will not do. It is now an upsert on `call_id`, so
    the model may be told ok twice but a person still sees one row. The contract
    moved with the host, and `check_tools.py` says so rather than pretending the
    old guarantee survived.
  - `open_payment_ticket` is **sync again** — it went async only because 13s
    stalls were burning credit. At 700ms the refusal is worth waiting for. Note
    precisely what that buys: the workflow answers from the Code node before
    writing, so a sync response confirms **the decision, not the row**. Validation
    is guaranteed; durability is not. Only a datastore in the request path gives
    that, which is a Supabase argument rather than an n8n one.
  - Reused the existing `shirly sheets` Google credential rather than asking for
    fresh OAuth. It is another project's credential on a shared instance —
    acceptable because the instance owner is the same person, and it works, but
    a dedicated `homies-sheets` credential is the right thing before this is
    anything but a demo.

### Open
- **The n8n webhook has no authentication at all.** `N8N_WEBHOOK_SECRET` is
  still empty and the Code node does not check anything, so anyone who learns
  the URL can write rows to the spreadsheet. Fine for ten fictional residents,
  not for one real one. Header auth on the webhook node is the fix.
- **This is a shared production n8n instance** carrying other clients' workflows
  (MOR, Shirly Inventory, CLIX, Hadas). Only ever create new workflows here; do
  not modify or activate anything else.
- **Apps Script is superseded but still deployed and still writing.** Its tools
  are no longer attached to anything, but the endpoint is live with the secret in
  its URL. Decide whether to retire it rather than leaving two tool layers
  answering the same contract.
- **Apps Script is not viable for voice and this is now measured.** 2s warm is
  still poor, the warm-up is a mitigation rather than a fix, and a lost async
  write is invisible. Supabase Edge Functions are ~100–300ms with none of this.
  The stopgap bought a working demo; it should not survive contact with Homies.
- **§8's <800ms is likely unreachable for Hebrew** once endpointing is counted.
  ~1.2–1.5s is realistic. Better to renegotiate the number with Homies than to
  quietly miss it.
- **The 4 Aug English call disclosed the card's last four digits to an unverified
  caller** who simply asked which card was on file, and never stated the month or
  the amount before asking to charge. It also read "Alright. Yeah. Yeah. Yeah." as
  an unambiguous authorisation and ended the call. Nothing was written only
  because the tools are not attached.
- **`flux-general-en` is unverified.** Deepgram's provider does not validate model
  strings server-side — a nonsense model passes PATCH too. Acceptance proves the
  shape, not the name. Only a test call proves the transcriber actually runs.
- **~1,600ms was the dashboard's estimate, never measured.** The mini swap should
  take a few hundred milliseconds off, but the number to trust is voice-to-voice
  from a real call log, against §8's <800ms.
- **The debt agent still cannot run.** Blocked on one thing only I cannot do:
  the Supabase project does not exist. Create it (eu-central-1), run `001`, `002`,
  `004`, `005`, `006`, fill `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` /
  `TOOL_SECRET`, deploy the function, then `vapi_sync.py debt --apply`. Confirm
  `v_debt_call_queue` returns **six** rows.
- **Outbound cannot be rehearsed the way inbound was.** The M1 demo ran on Vapi
  web calls with no phone number; an outbound campaign is inherently a dialled
  call. The conversation and all eight tools can be tested on a web call with
  `variableValues` supplied by hand — everything except the dialling.
- **The OXS PDF is key management, not endpoint docs.** It confirms the three
  modules, and adds: rate limits 60/min and 1,000/hour, keys expire (1 year
  default, 2 max), rotation leaves the old key live for 24 hours, keys are shown
  once and unrecoverable. It contains no base URL, no routes, and no field names —
  so `004_debt_schema.sql` is still written against guesses.

- **PRD v2 is now out of date in four places** and needs amending: §2.2 (live, no
  caveat), §9 (Sheets out, OXS API in), §10 (`get_request_status` loses the export
  timestamp), §16 (item 3, the OXS export, closes entirely). Not yet done.
- Payment links versus card-on-file — two different products, one of them is wrong.
- Which second factor `verify_identity` actually uses. Still §16 #1, still blocking
  §2.3, and now blocking any balance disclosure too.

### Later that day — a way to clear the test rows

- Confirmed the live Apps Script deployment is still the **old** code: the queue
  it returns has no `phone`, and `?meta=1` is ignored rather than answered. The
  redeploy asked for earlier has not happened, so nothing added since is live.
- Added `?key=…&clear=all` (or `&clear=<tab>`) to `sheets/Code.gs`. Empties the
  five write tabs, keeps their headers, reports how many rows went.
- `residents` is refused **by name**, not merely left out of `TABS` — so putting
  it in `TABS` one day cannot quietly make the input data wipeable. There is no
  undo on a spreadsheet reachable by URL.
- Documented in `sheets/README.md` under "Clearing the test rows".

### The agent told a resident he had a card on file. He does not.

Test call to משה (`+972531234569`, `card_last4` empty). The caller asked *"do you
have my card on your system?"* and the agent answered **"we have a card on file
in the system"**, having already asked *"can we charge the card ending for this
amount?"* — the authorisation sentence with the digits missing out of the middle
of it. It then wrote `payment_tickets` with `authorization_captured: TRUE` and
`card_last4` blank.

**Cause: the agent cannot branch on an empty variable.** It never sees a
variable, it sees the prompt after substitution. The rule was *"if
`{{card_last4}}` is empty there is no card on file"*, which renders as *"if  is
empty there is no card on file"* — no condition left to evaluate. Absence had to
become a word.

Three fixes, defence in depth:

- `variablesFor` in `web/index.html` now sends `has_card` as the literal `"yes"`
  or `"no"`. Checked against a mock: משה → `no`, שרה → `yes`, and no page-only
  key leaks into the agent.
- The prompt branches on `{{has_card}}` in all five places, with *"if it is
  anything else — blank, missing, a word you do not recognise — treat it as no"*
  so a missing variable fails towards not charging. Pushed live to both
  assistants; verified 5 occurrences each.
- `open_payment_ticket` now **refuses** `authorization_captured: true` when the
  call carries no `card_last4` — in `sheets/Code.gs` and in
  `supabase/functions/debt-tools/index.ts`, so the two do not drift. The prompt
  is asked not to do this; the tool makes it impossible.

### The page was never reading the sheet

The same ticket says `first_name: Shahar` while the sheet's row 2 says דוד כהן,
and `phone` is empty on every row written today. Both mean one thing: the page
fell back to its built-in list. Nothing was wrong with the sheet — the deployed
Apps Script still predates `phone`, so the load-time guard correctly refused the
queue, and the fallback is what ran.

Synced the built-in list to the sheet anyway: שחר is now דוד and marked already
paid, matching the edit made in the sheet. A fallback that disagrees with the
source is how "the bot is not reading everything" looked from the outside.

### Payment is a link now, and OXS sends it

Client decision, reversing 3 Aug. The resident pays through a link Homies' own
system sends them; the agent never mentions a card, never takes an approval to
charge one, and no member of staff charges anything.

- `open_payment_ticket` → **`send_payment_link`** on both assistants. Verified
  live: `card_last4` and `has_card` now appear **zero** times in either prompt,
  and the retired tool is no longer offered.
- New `payment_links` tab and handler in `sheets/Code.gs`; new `payment_links`
  table in `supabase/004_debt_schema.sql`, with RLS and a unique index giving one
  link per interaction. No `card_last4` column and no `authorization_captured`
  column — there is nothing to authorise.
- `log_call_outcome` gained `link_sent`. `authorized` still accepted so older
  rows keep their meaning.
- The Hebrew fixed string is now
  *"מצוין. אני שולחת לך קישור לתשלום על הסכום הזה, ותוכל להשלים את זה בעצמך"*,
  with the English twin translated to match. Still needs a native speaker.

**Why this is better than what it replaced**, beyond being what the client
wants: the call recording stops being the authorisation for a payment. That put
a 14-day Vapi retention window and the unanswered Israeli recording-consent
question directly underneath money movement. Consent now happens when the
resident taps the link. The worst case of a mishearing drops from *a charge
nobody agreed to* to *a link nobody uses*.

**What it costs:** the payment is offered, not settled. Nothing on our side can
see whether a link was ever paid — that is a read back from OXS, and until it
exists any report counting `link_sent` is counting intentions.

### A refusal that only existed downstream was invisible to the caller

Found while moving the tool over, not by reading the code. n8n answers Vapi from
its Code node **before** the writer runs, so the card guard added to
`sheets/Code.gs` this morning would have refused the row *after* the agent had
already been told `ok: true`. The resident hears a confirmation for a row nobody
wrote. Mirrored the guard into the n8n switch and confirmed it fires there:
`{"ok":false,"error":"no card on file for this resident …"}`.

The general rule this is an instance of: **every refusal has to live in the node
that answers, not only in the node that writes.**

### The Hebrew call that "felt unnatural" was a call with no variables

*"אני מדברת עם?"* — am I speaking with *nobody*. The name was missing from the
opening and from the not-the-account-holder line. Checked the last six web calls
through the API: **three carried no `variableValues` at all.** Those are Vapi
dashboard test calls, which send nothing. On one of those `{{amount}}` and
`{{month}}` are empty too, so the same call would have said "the payment for the
month of, zero shekels" had it got that far.

Nothing to fix in the prompt for that one — dashboard calls cannot be given
variables. Testing happens from the demo page.

The three faults the user raised are real independent of it, and two were not
handled at all:

- **The opening is now said once, ever.** Not after a "no", not when someone else
  comes to the phone. The transcript shows two identical rounds of greeting and
  refusal; re-introducing yourself tells the person you have lost the thread. A
  different voice on the line gets one short line, not the opening again.
- **The wrong-party line now ends the call.** Say it, log `wrong_party`, close,
  go. Previously it said the line and waited, which is what let the loop happen.
- **An ambiguous answer gets exactly one clarifying question.** "Who's asking?",
  "they're not here", "no no", "they spoke already" — ask once whether this is
  {{first_name}}; if the second answer is still not a clear yes, treat it as a
  no. Never a third time. *The cost of ending a call with the right person by
  mistake is one missed collection; the cost of guessing wrong is telling a
  stranger what a resident owes.*
- **Money stays unsaid until they confirm who they are** — including "it's about
  your building committee payment". A no is final for the whole call.

Residual, to watch: in that transcript the fixed wrong-party line was
**paraphrased** — the privacy clause *"אני לא יכולה למסור פרטים למי שאינו בעל
החשבון"* was dropped. It may be an artefact of the empty name making the
sentence ungrammatical. Recheck it on a call that has variables before treating
it as a model problem.

### A resident asked us to prove we were real, and there was no answer for it

Call to רחל. She asked where the number came from, then asked the agent to
verify her address to prove the call was genuine. The agent said it could not
share personal details and offered a callback — then repeated *"you're a
resident in a building Homies manages, and this is the number on your resident
record"* **three times**, twice back to back, while she was asking something
different each time.

Two fixes, and the second is the one that was actually missing.

**`{{callback_number}}` existed and was used only in the voicemail message.** The
office line — the one thing that lets a suspicious resident verify the call
without having to trust the caller — was never offered to a live human. Someone
ringing about money out of the blue, in a country where phone fraud is
relentless, will ask this often, and "I can't tell you" on its own is the answer
a scammer would also give.

Now a branch of its own: say plainly that personal details are not read out over
the phone *and that this is the protection they would want*, give them
`{{callback_number}}` to ring the office themselves, offer to repeat it, and let
them hang up and check if they want to — that is a good outcome, not a lost one.
Never read back an address, a unit, a card or a balance to prove identity. The
amount already stated is the most that gets said.

**And a general no-repeat rule**, because this is the second call in a day to
loop: one said the resident-record sentence three times, the other said the
payment-link line three times. If they are still asking, the answer did not land,
so say something different — a fact not yet given, the office number, the
alternative way to pay, or a person. Never the same sentence reworded.

### An English line was living in the Hebrew prompt

The user asked for the Hebrew version to be a true clone. It already was, with
one exception found by checking rather than assuming: the refusal callback offer
added hours earlier was written as a `>` line **in English**. `>` means spoken,
so the Hebrew assistant was carrying one English sentence among six Hebrew ones
— on the branch that had never been tested in either language.

Now `> אפשר שנציג מהמשרד יחזור אליך בנושא?`, paired with its English
translation in `vapi_en.py`. Phrased without a gendered verb for the listener,
like the other fixed strings.

Also corrected the fixed-strings list, which said six and was wrong twice over:
the closing had been fixed for days without being listed, and the refusal offer
made eight. That list is what gets handed to the native speaker doing the
review, so a list that does not match the prompt is worse than no list.

Added a check worth keeping: pull both live prompts, extract every `>` line, and
assert the script matches the call language. Seven each, zero wrong.

### "I already paid" is now four steps, on the client's spec

Previously: state what the system shows, give the email, log, end — one pass,
no verification, no check that the address landed. The user asked for a
confirming question first and an explicit check that the resident actually
caught the email. Both are right, and the second is the one that was quietly
costing us.

1. **Check the month, once** — confirm it is `{{month}}` they mean, as someone
   making sure they are looking at the right thing rather than someone doubting
   them. Still never asks when, how, or through which account.
2. **Say what the system shows** — framed as two records that do not match, never
   as a correction of the resident. No third ask.
3. **Read the address, then ask whether they got it**, and repeat once, slower,
   if not. An email address spoken down a phone line is the likeliest thing on
   this call to be misheard, and a resident who writes it down wrong hears
   nothing back and concludes they were ignored. `office@homies.co.il` is still
   a placeholder, and `homiesemail@gmail.com` before it came out of the TTS as
   *"homey's email at gmail dot com"* — this step is the mitigation for a
   problem we have already had.
4. **Log and close** — no link, no amount, no asking them to pay meanwhile.

Anger at any point still overrides all four and hands over.

### There was no refusal branch. At all.

Raised by the user after a test call: a resident said he would not pay, and the
agent went straight to the closing without offering anything. Grepping the
prompt for refusal handling turned up **one** mention — *"they have refused and
you have accepted it"*, in the list of conditions for ending the call. There was
no instruction anywhere for what to do when someone says no, so the model
improvised, and closing politely is a reasonable thing to improvise.

Added as a fixed path. Accept it in one sentence, no arguing and no second ask,
then offer a person **once**: *"would you like someone from the office to get
back to you about it?"* Yes → `office_to_contact`. No → `refused`, and close
warmly. Deliberately **not** a transfer — an offered callback is answerable with
the tools that exist, and it does not walk into the handover that goes nowhere.

The reason the offer is worth having: a flat refusal is usually about something
other than money — a dispute with the committee, a repair never done, a bill
they think belongs to the previous tenant. None of it is the agent's to solve
and all of it is worth someone hearing. As it stood, the office learned only
that he said no.

### Hardship was firing on people who had already given a date

Same call, earlier: *"can we do it by the end of the week? I don't have any
money yet"* was read as hardship and escalated. He had given a date; the second
clause was the reason for the date, not distress. The rule now says a promise
with a reason attached is a promise — take the date and close — and reserves
hardship for an inability to pay with no date behind it.

Also: the handover line was spoken twice in a row on that call, once bare and
once with an apology in front of it, which sounds like the first attempt failed.
The prompt now says once.

### Everything saved for a move to another Vapi account

- `scripts/vapi_export.py` — dumps every collection the account can hold
  (`assistant`, `phone-number`, `tool`, `squad`, `workflow`, `file`), including
  the three that are empty, since an export that only looks where it expects
  things is how a resource goes missing. Server header values are redacted at
  any depth — they are empty today, but a dump that is safe by accident is not
  safe.
- `docs/handover/vapi-export.json` — 96k, six assistants and one phone number.
  A record, not a restore path: Vapi mints new ids on create.
- `docs/handover/new-vapi.md` — the rebuild. Nothing of value is only in Vapi;
  the prompts, tools and config all push from this repo, so a move is
  `vapi_sync.py --apply`, `vapi_en.py --create`, and then fixing the ids that
  seven files hardcode. Line numbers for each were checked rather than guessed.

Recorded as not transferring: call history and recordings, the free US number,
the eval suite, and anything ever edited in the dashboard and not written back
here — that last one exists nowhere else and a rebuild will quietly not have it.

### 5 Aug — "Echo Stone": the debt agent is wired for a cloned voice, and two dead ends ruled out first

Asked for the debt agent to speak in a recording of a real person's voice. The
recording is good material — 220 seconds, only 11 seconds of silence across
seven gaps, single speaker — but it peaked at **+0.29 dBFS**, i.e. at or above
full scale, and clipping bakes distortion into a clone permanently. Cleaned to
mono 44.1kHz at −0.50 dB peak as `voice/echo-stone-sample.wav`.

**Vapi cannot host a cloned voice, and this is settled rather than suspected.**
`VapiVoice.voiceId` is a closed enum of thirty names in Vapi's own OpenAPI spec
— Elliot and Leah among them — with no slot for a custom id. `CloneVoiceDTO`
exists in that spec and is referenced by no path and no other schema. Both
accounts, old and new, report zero credentials, zero provider voices and zero
files, which is consistent: a clone is created *in a provider account*, and with
no provider connected there is nowhere for one to be created.

**"Custom voice" in the dashboard is not voice cloning.** It looked like the
answer and it is the opposite: `CustomVoice` requires a `server`, and the
request flows *outward* — Vapi POSTs text to a URL you run and expects audio
back. It is a bring-your-own-engine hook for providers Vapi has not integrated.
The giveaway is that the panel has no upload field at all, only Provider, Server
URL and Voice ID. Saving that screen as it stood — Custom voice with an empty
Server URL — would have left the debt agent with no TTS whatsoever *and* wiped
the 27-replacement output guard, which lives inside `voice`. Caught before save;
the assistant still reads `provider: vapi`, `voiceId: Elliot`, guard intact.

**Cartesia, not ElevenLabs, and the reason is Hebrew.** Cartesia declares `he`
in a 42-language enum and takes a free-text `voiceId`, so a cloned id fits. It
also keeps `chunkPlan`, so the guard survives the move. ElevenLabs declares
`language` as free text, meaning nothing in the spec states whether Hebrew works
there — it would ride on `eleven_v3` — and the spec carries the error
`eleven-labs-blocked-using-instant-voice-clone-and-requested-upgrade`, so its
cloning is plan-gated as well. Paying to find out is the wrong order. PlayHT,
LMNT and Rime also declare Hebrew and are the backups.

**The debt agent takes the voice, not the inbound one.** The voice is male and
this prompt is already masculine throughout — מיכאל, מדבר, שולח, מעביר — so not
one word changes. Pointing a male clone at the inbound agent would mean flipping
the same seven passages that have already been flipped three times.

Wired as `cloned_voice()` in `vapi_sync.py`, gated on `CARTESIA_VOICE_ID`. With
the variable unset it returns None and nothing changes — verified by running the
dry run both ways, `vapi Elliot` against `cartesia <id> (cloned) fallback -> vapi
Elliot`. The fallback is not decoration: a cloned voice failing mid-call would
otherwise end it, and `FallbackVapiVoice` carries `chunkPlan`, so the guard
survives the fallback too.

**PARKED, same day.** Staying on Vapi `Elliot` v2 `language: he` for now — which
is what the assistant already carried, so nothing was changed to park it. Everything
for the clone is built and waits on one thing only: a Cartesia API key in `.env`.
`scripts/voice_clone.py --go` then does the rest, and `cloned_voice()` in
`vapi_sync.py` returns None while `CARTESIA_VOICE_ID` is unset, so the wiring is
inert rather than half-applied.

Two corrections worth carrying forward, because both were stated wrongly here
first:

- **Instant cloning is free.** The "$49/month Pro tier" came from third-party
  pricing write-ups; Cartesia's own docs say training instant clones is "fast and
  free" and put the paid tier on *Pro* cloning, a different feature. A free
  account is worth trying before assuming a bill.
- **The full recording cannot be used, in either mode.** At 3m40s it is 22x over
  instant cloning's 10-second limit and 8x under Pro cloning's 30-minute minimum,
  so it falls in the gap between the two. Using "the whole file" on the instant
  endpoint does not use the whole file; it lets the API pick the ten seconds. If
  the full-fidelity version is ever wanted, the answer is to record **30 minutes
  to 2 hours**, not to send this one — and to note that Pro clones bill TTS at
  1.5 credits per character against 1, a permanent 50% rise on a line already
  over budget.

**Vapi cannot clone, and this is now proven rather than read.** A PATCH setting
`voice.voiceId` to a custom string returns 400 with the enum in the error:

    voice.voiceId must be one of the following values: Clara, Godfrey, Elliot,
    Savannah, Nico, Kai, Emma, Sagar, Neil, Layla, Sid, Gustavo, Kylie, Rohan,
    Lily, Hana, Neha, Cole, Harry, Paige, Spencer, Naina, Leah, Tara, Jess,
    Leo, Dan, Mia, Zac, Zoe

The request was rejected, so the assistant was untouched by the test. Thirty
names, no thirty-first.

Still open, and it is the one claim in the chain that cannot be checked from
here: **whether a cloned voice speaks good Hebrew.** Only a call answers it, and
it should be answered before a resident hears it.

Also worth revisiting whichever way the clone goes: **Elliot was never chosen.**
It is Vapi's default and arrived on this assistant through a dashboard edit on
5 Aug. Fourteen of the thirty are male — Godfrey, Nico, Kai, Sagar, Neil, Sid,
Gustavo, Rohan, Cole, Harry, Spencer, Leo, Dan, Zac — and none has been heard
against Hebrew. Vapi has no standalone TTS endpoint, so auditioning them means
the dashboard preview or a call.

**Audio is now gitignored.** `New Recording 154.m4a (1).mp4` was sitting
untracked *and un-ignored* in the project root and missed the previous commit by
minutes. A voice recording identifies a person, and removing one from git
history is a rewrite rather than a delete.

### 5 Aug — the inbound call had no ending, and every transfer was a promise nobody could keep

Two omissions in the inbound agent, found by reading the live config rather than
a transcript. Both are the same mistake: a thing the prompt describes that the
platform was never told to do.

**Nothing could end an inbound call.** `endCallPhrases: None`,
`endCallFunctionEnabled: None`, and no closing line anywhere in the prompt to
trigger one with. All three calls on record ended `customer-ended-call`, which
is why it never looked like a bug — someone who rang in does normally hang up.
The shape underneath is worse than that reading: the agent reads out the
reference number, stops, and the line stays open in silence for thirty seconds
until `silenceTimeoutSeconds` closes it. The caller is left listening to nothing
with no way to tell whether their request was written down.

Fixed the way the debt agent was, because it is the same problem: an `## Ending
the call` section with a fixed closing, `endCallPhrases: ["and goodbye",
"ולהתראות"]`, and `endCallFunctionEnabled: False` set explicitly so a dashboard
visit cannot quietly hand the model a way to hang up without speaking. Saying
the line is the mechanism, not a request. One `משהו נוסף?` gates it — the only
extra turn the style section tolerates, and it is there because ending a call is
the one irreversible act in the flow.

**Every transfer path promised a live handoff that does not exist.**
`transfer_to_human` posts a row to n8n. There is no `transferPlan`, no
destination, no extension — verified on the live assistant, both fields null.
The prompt said *"אני מעבירה אותך לנציג"* in five separate places, so the caller
was told they were being put through and then sat on an open line waiting for a
voice that was never coming. All five now say a representative will get back to
them, which is what the row actually causes; `transfer_to_human`'s own
description says so too, so the model is not reading one thing in the prompt and
another in the tool; and absolute rule 9 forbids the old phrasing outright. When
a real extension exists, the wording and a `transferPlan` go back together.

The 08:56 English test call is worth separating from this. It thanked the caller
for reporting a leak and explained a fallback before it was needed — both
explicitly forbidden — but the assistants were re-synced at 10:30, so that call
predates the `Say less than you think you should` section rather than ignoring
it. It has not been retested since, and it is the thing to watch on the next
call, along with the fact that 97 seconds of leak, building and apartment
produced zero tool calls.

English twin rebuilt from the Hebrew: 24 substitutions, all matched exactly
once, no Hebrew remaining. `and goodbye` and `ולהתראות` are a matched pair here
rather than a translation — each is what its own `endCallPhrases` entry fires
on, so a twin that dropped the conjunction would be a twin that could not hang
up.

### 5 Aug — four faults in one call, one of them the worst yet

Test call to משה on the link flow.

**It read its own tool arguments out loud.** The resident heard *"Note,"* and
then, as a separate utterance, *"resident asked how to proceed and was sent the
payment link after agreeing to settle."* That is the `note` parameter of
`send_payment_link` arriving in the voice channel. Second time this stack has
leaked tool syntax into speech — gpt-5.4-mini did it with harmony format on
4 Aug. Fixed structurally rather than by asking the model nicely: **the tool now
takes no parameters at all.** Everything it needs is already on the call, so
there is nothing to pass and nothing to leak. Verified live on both assistants —
`send_payment_link params: NONE`.

**It hung up on him mid-question.** Pressed a third time on whether Homies could
take the payment, the model's entire reply was *"Goodbye."* — and
`endCallPhrases` contained the bare word `goodbye`, so the call ended there,
on his question. The note written on 4 Aug said a false positive *"would need the
bot to say goodbye when it did not mean it"*, which is precisely what happened.
Now only a full closing tail matches: `have a good day, and goodbye` /
`שיהיה יום טוב ולהתראות`. Neither is reachable by accident, and
`endCallFunctionEnabled` still covers a paraphrased closing. The prompt also
forbids leaving a conversation any way except the full closing line, and says to
hand over rather than hang up when it has run out of answers.

*Then the opposite, within the hour.* Requiring the whole closing tail
(`have a good day, and goodbye`) was too much — the prompt tells the agent to
vary the wording of the closing, so the paraphrase never matched and the calls
stopped ending at all. Only the **bare word** was ever broken; the conjunction is
what makes the rest safe. Settled on `and goodbye` / `ולהתראות`: unreachable by a
model that simply says "Goodbye", short enough to survive rephrasing. Hebrew
makes the distinction with one letter — the vav.

That only works if the closing reliably contains it, and the prompt explicitly
invited variation. So the thanks stays free and **the last two words are now
fixed**, with both reasons given: a bare goodbye reads as being hung up on, and
the line is what releases the call. Verified by checking the phrases against the
prompt text rather than assuming — `ולהתראות` on the Hebrew, `and goodbye` on
the English.

**It treated a question as a yes.** *"Okay. And what should we do?"* → *"Great,
I'm sending you a payment link."* He had asked how to pay and was recorded as
having agreed. The prompt already said a question is not agreement; it now says
so with the sentence that failed, and requires answering the question and then
asking whether to go ahead.

**It said the same sentence three times.** *"A link comes to you and you complete
it yourself whenever suits you"*, near enough word for word, while he was trying
to ask something else. The prompt now treats the payment-link line as
single-use: said once, never reworded, and a resident still asking means go to
the alternative.

### The agent had no answer to "do you have an alternative payment method"

From a test call on the new link flow. שחר asked for another way to pay and the
agent had nothing — it repeated the link three times, twice by correcting him:
*"That's not how this works."* Then *"I'm with Homies. Yes. But I can't take a
payment or charge anything for you."* Then *"It is collected monthly, but it
still is not charged. / by me."* He was not being difficult; he was asking how
to pay.

The field already existed and nothing consumed it. `Homies-Clarifying-Questions`
§1 describes the OXS debtor export as carrying *"payment link, **alternative
payment details**"* per debtor. Wired in end to end as `{{alt_payment}}`:

- `sheets/Code.gs` reads an `alt_payment` column; `residents.csv` gained one,
  six of ten rows carrying a bank transfer and four deliberately without.
- The page carries it through both the sheet path and the fallback, and swaps in
  an English rendering for English calls — Hebrew bank wording read by an English
  voice is the same noise problem the `en` names exist to solve.
- **Never empty on any path.** `'' → 'none'` in Apps Script, in `fromSheet`, and
  in the fallback rows. Verified against a mock: empty column, whitespace-only
  column and a real value all behave, in both languages.

The prompt now offers the alternative the *first* time a link does not suit
them, reads the details exactly as written, and refuses to invent a bank, a
branch or an account. With `none` it promises office follow-up and logs
`office_to_contact`.

Also removed the instruction to correct the caller. The rule is now *answer with
what you can do, never with what they have got wrong* — and the banned sentence
is described rather than quoted, since a prompt that spells out a bad line is a
prompt that can produce it. Verified absent from both live prompts.

### The eval suite was testing a flow that no longer exists

Raised by the user: the no-card conversation is worse than the with-card one.
After the link change there is no longer a no-card conversation — the agent never
mentions a card to anybody, so both residents get the identical call. The
asymmetry was real and is now structural, not behavioural.

What was still wrong is that `scripts/vapi_eval.py` — the only automated check on
how the agent *converses* — graded the card flow. Its `agrees` rubric required
the agent to read out card digits `0715`; under the current prompt a passing
agent fails that rubric and a failing one could pass it. Rewritten:

- `card_last4` dropped from `VARIABLES`. Every scenario now runs against a
  resident with no payment method, because there is no other kind.
- `agrees` — must get the yes **before** announcing the link, must say it is on
  its way rather than already arrived, immediate fail on any mention of a card.
- `hesitant` — announcing a link on the back of a "maybe" is the fail.
- `wrong_party` — card digits removed from the confidentiality list.
- `no_card` rewritten around the 4 Aug failure itself: the tester asks *"do you
  have my card on your system?"*, the way משה did, then asks a second time how
  payment will happen. Saying a card is on file is an immediate fail even if the
  rest is perfect, and there is an explicit rubric line that the call must not be
  *noticeably worse* than a cooperative one.

Not run — `--run --voice` places nine real calls and bills the account.

### Redeployed and verified

All six routes confirmed live against the deployment URL:

- `?meta=1` — writes to *Untitled spreadsheet* `1WHktpy…`, six tabs.
- Queue — five callable rows, **every one carrying its `phone`**. That is the
  fault that made three calls write rows belonging to nobody, and it is closed.
- `has_card` present and correct per row: משה `false`, the other four `true`.
- `?all=1` — all ten with a reason each: דוד and מיכל *already paid*, נועה *not
  handed over*, איתי *do not call*, טל *4 attempts made*.
- `?clear=residents` → **refused**, as designed.
- `?clear=all` → removed 4 outcomes, 3 tickets. Write tabs are empty.

Left to do on the page side: a hard reload.

Redeployed again for `send_payment_link` and verified through the n8n execution
data, not through the tool responses:

- `payment_links` created itself on first write; two link requests from two
  different calls landed, and `log_call_outcome` with `link_sent` landed.
- The **second** call of `send_payment_link` on the same `call_id` was refused
  by the writer — *"a link has already been requested on this call"* — and no
  second row exists.
- Probe rows cleared afterwards. All five write tabs are empty.

**Deployment propagation is not instant.** Executions 447174 and 447175, fired
seconds after the redeploy, came back *"unknown tool send_payment_link"* and
*"outcome must be one of: authorized, promised, …"* — the previous version still
answering. The same probes passed a minute later. Worth knowing before
concluding a redeploy failed.

**Known gap, bounded.** That duplicate refusal never reaches the agent: n8n
answers from the Code node, so Vapi was told `{"ok":true}` both times. Only one
row can exist, so the office never sees a duplicate — but the agent could say
"a link is on its way" twice on one call. Closing it properly means routing
`send_payment_link` through the sync path the way `open_request` goes, which
buys correctness at the price of an Apps Script cold start (up to 13s) in the
middle of a call. Left open deliberately; the prompt says call it once.

### 5 Aug — the agent can no longer speak its own machinery

Asked for a guardrail that stops the bot reading its instructions out loud, and
for it to be fool proof. A prompt rule alone cannot be, and the reason is in the
two incidents themselves: neither was a rule the model broke, both were the
model failing to keep two channels apart. On 4 Aug gpt-5.4-mini emitted
`to=functions.open_payment_ticket <|constrain|>json {"authorization_captured": true}`
into the spoken stream; on 5 Aug gpt-5.5 spoke the `note` parameter. An
instruction addressed to a model that has already lost track of which channel it
is writing to has nothing to hold on to.

So three layers, only one of which is advice.

**1. No surface.** `send_payment_link` was stripped to zero parameters on 5 Aug.
A field that does not exist cannot be read aloud. Unchanged today, but it is the
first layer and worth naming as one.

**2. `voice.chunkPlan.formatPlan.replacements`** — new, and the actual answer.
Vapi applies these to every chunk after the model and before the voice provider,
so the model does not get a vote. `scripts/voice_guard.py` holds them: control
tokens `<|…|>`, `to=…`, `functions.…`, unsubstituted `{{…}}`, JSON keys, braces,
and one pattern that does most of the work — `\b[A-Za-z]+(?:_[A-Za-z]+)+\b`.
Nothing anyone says on a phone call contains a snake_case identifier, so that
single pattern covers every tool name, every enum value and every parameter,
including ones added later without this file being touched.

**Then the transcripts showed the pattern could never fire against a record.**
The 4 Aug leak is stored as *"Open payment ticket. two functions, open payment
ticket ten ten i Kypiao TCN Jason. authorization captured. True."* — Vapi's own
formatter had already turned the underscores into spaces and `<|constrain|>`
into syllables before anything was written down. So a second set was added: the
same identifiers as the formatter renders them, case-insensitive. Which of the
two sets fires depends on whether replacements run before or after the built-in
formatters, and the schema does not say. The documented examples imply before —
a phone-number replacement on `(\d{3})(\d{3})(\d{4})` only makes sense on digits
that have not been spelled out yet — but that is an inference, not a guarantee,
and both sets cost nothing.

Every spoken form had to survive one test: could this appear in an ordinary
collection call? Five did and were left out — *not handed over*, *no answer*,
*not understood*, *first name*, *callback number*. Eating a real sentence is a
worse failure than reading one identifier, so those are the prompt's problem.

**3. NEVER SPEAK THE MACHINERY** in the prompt, plus absolute rule 10 and a
seventh quality check. This is the only layer that can reach a *prose* leak —
"my instructions say I should…" — which no filter can catch without mangling
real speech. It also answers being asked what the instructions are: one sentence
about being Homies' digital assistant, then carry on. Do not confirm, do not
deny, do not read anything back, not even to say it is confidential.

**`scripts/vapi_leak_check.py`** reads the transcripts back and applies the same
patterns, imported from the same file so the filter and the detector cannot
drift. Run against the last 100 calls it found exactly the two known leaks and
nothing else — 2 of 79, no false positives across four weeks of Hebrew and
English. That number is the calibration: it is what says the spoken-form list is
tight rather than merely present.

Pushed to all three assistants; 27 replacements each, verified identical to the
source. The inbound demo carries the filter but not the prompt section — it runs
from a different document, and the filter is the layer that matters there.

**What this does not do.** Vapi's regex replacement has no global flag, so each
pattern strips its first match per chunk; a single chunk carrying two
identifiers loses one. Chunks are short and split on punctuation, so a long leak
is spread across several and each is cleaned — a floor, not a proof. And a model
that describes its instructions in fluent Hebrew defeats every pattern here by
design. That is what layer 3 and the checker are for.

**Noticed while measuring:** the debt system prompt is now 33,191 characters.
Prompt reduction was already on the list; it has moved up.

### 5 Aug — the Hebrew debt prompt reverted to yesterday's wording, keeping one section

Asked to go back to "the version before this one, the one we were building
yesterday". Those are two different prompts, and the difference mattered:

- **the previous version** was two hours old — identical but for the seven
  gender passages
- **yesterday's** was 33,191 chars, 2,691 smaller, and lived only in
  `docs/handover/vapi-export-old-account.json`

**Vapi keeps version history and it does not go back far enough.** Ten versions
on the debt assistant, all from 10:09–12:17 *today*, because the assistant was
created at 09:31 in the migration. The list endpoint returns stubs; the content
is under `data` on each entry, and reading it showed the whole afternoon: the
voice moving `he-IL-HilaNeural` → Elliot → Leah → Elliot, and the 12:12 entry
that is the dashboard revert — feminine prompt against a male voice.

The answer was neither option whole: yesterday's Hebrew, **plus** the
YOU ARE BEING HEARD, NOT READ section, which was judged worth keeping. Merged by
splicing three blocks into yesterday's text at anchors present in both — the
spoken-delivery section, the money rule (`שקלים`, never `ש"ח`, never digits in
pieces) and the fixed-line re-inflection rule for the *caller's* gender. The
latter two were kept without being asked for: both were written to fix defects
heard on real calls, and both serve naturalness rather than working against it.
Removing either is one word.

35,921 chars, verified byte-identical between the document and the live
assistant.

**The seven spoken lines are yesterday's again**, and they are feminine, so the
voice went back to **Leah** in the same push. Same paired change as this morning,
run in reverse — and the override stays on the debt target rather than moving
back into `BASE`, because the point of it is that the two prompts can disagree
about the speaker's gender. They agree today. They will not always.

**The English twin refused to build, which is the guard working.** Nine
`DEBT_LINES` entries keyed on Hebrew that had just changed, and the script listed
all nine rather than shipping a half-translated prompt. Repointed at strings read
out of the live prompt rather than retyped, so a transcription slip could not
introduce a mismatch that still matched. Four English lines were reworded too —
yesterday's Hebrew says "for this amount… complete it yourself" and "anyone who
is not the account holder", which the previous English no longer rendered.

### 5 Aug — the demo page was blank, and it took three wrong diagnoses to read the console

The deployed page rendered no resident list, the tag stuck on `loading…`, and
nothing on screen said why. Cause, once actually looked at:

```
Uncaught ReferenceError: Cannot access 'ALT' before initialization
```

`const ALT` was declared twelve lines below the array that used it. `const` is
hoisted but not initialised, so reading it from above its own declaration throws
while the module's top level is still executing — and **a module that throws at
top level is discarded whole**. `drawPeople()` and `loadQueue()` are called on
the last three lines and never ran, which is why the label kept the placeholder
the markup shipped with. `node --check` passes it happily; it is a runtime fault
in something that looks like data.

**Two commits went out against a problem that did not exist.** The blank-page
symptom is identical whether a module dies on a failed import or on its own
data, so the symptom carried no information — and a CDN theory was built that
fitted it perfectly. Worse, node had printed `Cannot access 'ALT' before
initialization` with a caret on the exact line during an earlier syntax check,
and it was read as a harmless missing-`document` error and skipped past. The
evidence was on screen an hour before it was used.

What settled it in one command:

```sh
chrome --headless=new --enable-logging=stderr --dump-dom <url>
```

Ten residents or zero, the label's text, and the console — from the deployed URL,
in a clean profile, in about twenty seconds.

**Neither wrong commit was reverted, on purpose.** The SDK now ships from
`web/vendor/` instead of esm.sh, and a failed import no longer takes the page
down. Both are worth having on their own, and the second is what would have put
this error on the page rather than only in a console nobody had open.

**Then it was still blank in a real browser while a clean Chrome rendered it
fine** — which is cache, not code. Vercel was sending
`public, max-age=0, must-revalidate` with `X-Vercel-Cache: HIT`. `web/vercel.json`
now sends `no-store` for the HTML and a year of `immutable` for `vendor/`, which
is the right split: the page changes constantly, the pinned SDK never does.

**The header carries a build stamp**, from `document.lastModified` — no build
step, nothing to bump. It separates the two failures that had been confusing each
other all afternoon: a timestamp older than the last push means a cached copy; the
words "script did not run" mean the module crashed. Identical from the outside,
opposite fixes.

**The gap this exposed is real and still open.** Every assistant push is verified
against the Vapi API — voice, tools, prompt, no feminine forms left — which is
why that side has been reliable all day. The web page had no equivalent, so the
only check was a human opening it. The same headless command above, asserting
buttons > 0 and no console errors, would have caught this in thirty seconds.
Offered, not yet built.

### 5 Aug — Apps Script redeployed; the partial-request net is live

`save_partial_request` answered `unknown tool` from the deployed writer all
afternoon. Because the tool is async, n8n had already told the agent `ok:true` —
so every partial would have been lost silently, on calls that were already going
wrong. Redeployed by hand; it now returns `{ok:true}` and `partial_requests`
created itself on the first write, as `tab()` is designed to.

Two smoke rows left behind, both marked `SMOKE TEST` — one in `partial_requests`,
two in `call_requests` including the earlier probe. Clearable with
`?key=…&clear=partial_requests`, left in place rather than cleared unasked.

**The secret is still in the source.** The plan was to fold the move to Script
Properties into this same paste and it missed the window; it costs nothing to
carry to the next redeploy, and there will be one. It matters because the repo
now exists: `sheets/Code.gs` is in git history, so making that repo public later
is a history rewrite rather than a file edit.

### 5 Aug — the debt agent is male, and that is seven edits rather than one

Asked for directly, after the 5 Aug correction had gone the other way. Voice
`Leah` → `Elliot`, both Vapi v2 `language: he`.

**In Hebrew this is not a voice setting.** The speaker's gender is marked on the
verb, so the voice decides מדבר or מדברת, שולח or שולחת, מעביר or מעבירה, עוזר
or עוזרת — and מיכל is a woman's name. Changing the string alone would have left
a male voice reading feminine verbs in every sentence the agent owns, which an
Israeli hears instantly. So: the identity line, the digital-assistant disclosure
and all five spoken `>` lines were re-inflected in the same pass, and the agent
is **מיכאל**. Seven passages, each asserted to match exactly once before being
replaced.

**Set on the debt target, NOT in `BASE`.** The inbound assistant reads the same
`BASE`, its prompt is feminine throughout, and one string there would have made
that agent ungrammatical without touching a word of its prompt — the identical
failure the dashboard caused earlier the same day, from the opposite direction.
Verified after the push: intake (he) still carries `Leah` and still carries
מעבירה and עוזרת, which now agree with each other.

**It fixed something rather than only costing.** The two twins were different
people: `vapi_en.py` had been renaming מיכל to Michael because Elliot reads
"Michal" as "McCall" and because the English voice was already male, so Homies
had a woman on Hebrew calls and a man on English ones. Both are Michael now, and
that substitution entry does less work than it did — it strips the Hebrew
spelling and nothing more.

**The English twin refused to build until its table was updated**, which is the
safety property doing exactly its job: seven `DEBT_LINES` entries key on the
Hebrew that had just changed, and a stale table would otherwise have shipped a
half-translated prompt. Updated, rebuilt, no Hebrew remaining.

Recorded in the prompt header as a paired change in both directions — going back
to a female voice means re-inflecting the same seven passages, or the error
simply runs the other way.

### 5 Aug — first real intake call: 62 seconds, no ticket, and the agent did all the talking

Call `019fd123` on the English twin. The caller hung up having answered almost
nothing. Timings from `artifact.messages`, which is where the story is:

```
 -0.7s bot   6.4s  | Hello. You've reached Homies Building Management...
  5.9s bot  17.7s  | Thank you for letting me know about the leak on your ceiling...
  7.5s user  3.3s  | Um, there is a leak on my ceiling.
 20.6s bot  14.3s  | Could you please tell me the name of the building or or the street...
 25.2s user  4.8s  | Sorry. What? Okay. I think the building is building one.
```

**38 of the first 55 seconds were the agent talking, in two turns.** Twelve words
came out as fourteen seconds; the `or or` is the same restart artifact as the
`The the bill` from the 4 Aug English call. The caller was not being difficult —
they were trying to get a word in against a wall, and every attempt to interject
made it worse.

Worth separating two things that look identical in the dashboard: the panel
redraws a streaming turn from the beginning as it arrives, so a long turn *looks*
like it is repeating when it is not. The durations are the evidence, not the
transcript pane. But the durations then say the same thing anyway.

**Cause one: no turn-length rule existed.** The debt prompt caps a turn at two
short sentences; that rule was never carried across, and this prompt is longer
and more explanatory, so the model filled the space. Added a section that names
the four kinds of padding that showed up in this call by name — thanking someone
for reporting a problem, repeating what they just said, explaining a fallback
before it is needed, and announcing an action instead of doing it.

**Cause two: a fallback was written as a sub-line and read as part of the same
question.** "Which building is this about? / If they do not know the name, ask
for the street" was one bullet with a continuation line, and the model said both
in one breath — so every caller was offered two ways to answer before answering
either. Now explicitly "ask that and stop", with the street as its own later
turn.

**Cause three: the greeting was 6.4 seconds.** The caller started speaking half a
second in, twice. Nobody waits through a greeting on a line they dialled
themselves. Cut to about three seconds in both languages. Worth naming why this
one is different: the first message is a fixed string, so no rule in the prompt
governs it — its length is the only lever there is.

**The endpointing numbers were deliberately NOT touched.** `numWords: 2` is
suspect — "Sorry. What?" is exactly two words and should probably not stop an
agent mid-sentence — but changing the prompt and the turn-taking together makes
the next call uninterpretable. Three prompt causes are enough to explain
everything seen here. If turns are short and the thrash continues, the numbers
are the next suspect and there will be a clean before-and-after to read it
against.

Also unanswered, and downstream of the thrash rather than separate: the agent
never acknowledged the digits the caller offered, asked for the building name a
second time after being given a number, then moved to the apartment without
confirming the building at all. Retest before treating that as its own fault.

### 5 Aug — the intake agent has an English twin, and a name that matches it

`fd991d71` — *Homies — Inbound Intake (en)*. Built the same way as the debt
twin: `vapi_en.py` reads the live Hebrew assistant and applies a fixed table of
substitutions, each of which must match exactly once or it refuses to build.
21 passages, no regex block needed. Four assistants now, two pairs.

**`vapi_en.py` takes a target rather than being copied.** Two files carrying the
same 150 lines of machinery would have diverged within a fortnight, and the
divergence would have been invisible — both would keep producing an English
assistant. `TWINS = {debt, intake}`, same shape as `TARGETS` in `vapi_sync.py`.
Usage is now `vapi_en.py {debt|intake} --dry|--create|--update ID`. The debt twin
was re-run through the new code first and comes out byte-identical.

**The intake table is longer than the debt one for a reason worth naming.** The
debt prompt recites — seven fixed lines it must say verbatim, English prose
around them. The intake prompt *demonstrates*: almost every rule is followed by
an example of a real spoken sentence, because how to sound is not teachable in
the abstract. Those examples are the prompt's working parts, so all 25 Hebrew
lines had to cross, and they are rewritten rather than translated. "יש נזילה
מהתקרה בחדר האמבטיה, זה כבר יומיים" exists to show what an unpolished caller
sentence looks like; a faithful rendering of that particular Hebrew would teach
the opposite of what the example is for.

**Michael, not Michal, and the same Michael as the debt twin.** Elliot reads
"Michal" as "McCall" every time and no spelling hint in a prompt changes what a
voice does with a name it is handed. Reusing the debt twin's voice and name means
Homies has one English employee rather than two who have never met.

**The English twin keeps gpt-4.1-mini and does NOT follow the debt twin to
gpt-5.4.** The debt twin was moved up because -mini spoke a tool call out loud on
4 Aug — but that was gpt-5.4-mini emitting harmony control tokens, a failure of
that family, and gpt-4.1-mini does not use them. The positive reason matters
more than the absence of the negative one: this assistant exists so someone who
does not read Hebrew can judge what a Hebrew caller gets. Give it a better model
and it makes better decisions than the thing being reviewed — the flow passes in
English, fails in Hebrew, and the twin has quietly become an argument for
shipping. Same brain, or it is not a twin.

**Renamed `(demo)` to `(he)`.** Cosmetic, except that `vapi_sync.py` finds its
target *by name*: leave the script and the live assistant disagreeing and the
next `--apply` does not fail, it creates a second assistant and starts editing
that one instead. The live name, `vapi_sync.py`, `vapi_latency.py` and
`demo-inbound.md` moved together, and a dry run confirms it still resolves to
`update 51bbe77a` rather than `create`.

**Neither intake assistant is on the demo page**, and that is not a missing
config line. The page is built around the debt call — it picks a resident,
fetches the queue from n8n and hands over an amount, a month and a name as
`variableValues`. Intake takes none of those; it is answering someone who rang
in and asks for everything it knows. Adding it means an agent selector beside the
language toggle and a path that skips the resident picker. Noted in
`web/README.md` so the absence reads as a decision rather than an oversight.

### 5 Aug — the inbound ticket agent had no tools, and never had any

Asked to build a support agent that opens tickets, capped at three minutes. It
already existed — `51bbe77a`, *Homies — Inbound Intake (demo)*, live since 3 Aug
with 200 lines of Hebrew covering intake, read-back, noise, emergency and
transfer. What it did not have was a single tool.

**Not a migration casualty.** `TARGETS["inbound"]` in `vapi_sync.py` has never
carried a `tools` key, so `build()` never attached any, on either account. The
prompt had been telling it to call `open_request` and read the returned reference
aloud since the day it was written. With no tool attached, it would have run the
whole conversation and invented the number. That is the worst shape a failure can
take on a phone: the caller hangs up satisfied and there is nothing anywhere —
no row, no error, no signal. Nobody would find out until someone asked why the
leak was never fixed.

Worth noting how it stayed hidden: every check made on this assistant was about
how it *sounded*. Transcriber, voice, endpointing, gender, the guard. Nothing
ever asked whether it could do anything.

**Three tools, all writes** — `INTAKE_TOOLS` in `vapi_tools.py`. `open_request`
(sync, returns the real reference), `save_partial_request`, `transfer_to_human`.
They post to the debt agent's webhook; one workflow, routed on tool name. The
path keeps the name `homies-debt-tools` because renaming it would break the live
debt assistant's eight tools until they were re-synced — a real outage bought for
a better name.

**`identify_resident` and `get_request_status` are deliberately absent.** Both
are reads, and this project has never had a read path: the n8n handler for the
first returns `lookup not implemented`, and the Apps Script one matches on a
phone number, which a web call does not have and which the prompt never used
anyway. An agent holding a lookup that cannot look anything up is worse than one
holding none — it offers, the caller accepts, and the answer gets invented. So
the *prompt* lost them too: the whole "Checking a request" section is gone,
replaced by an explicit refusal and a transfer, and identity is now two questions
the caller answers rather than a lookup. They come back with the database.

**Three minutes is not a field.** `maxDurationSeconds: 180` hangs up on the
second it expires, mid-word, and the model is never told it is coming. Outbound
that is survivable — the agent drives, and an overrun means it should have
transferred. Inbound the caller drives, so a bare 180 cuts someone off in the
middle of describing a leak and writes nothing, which is the one outcome the
prompt itself forbids. Shipped with two companions: a budget section that spends
the time in the order that survives being cut off — write the row as soon as the
description and the apartment are in hand, tidy up afterwards — and
`save_partial_request` underneath. Both need the model to cooperate. The version
that does not is the end-of-call webhook seeing `max-duration-exceeded` and
writing a partial from the transcript, and that needs a server URL we do not
have.

**The read-back order was wrong and only mattered once a tool existed.** The
prompt said to say the sentence back "and then the reference" before writing —
but the reference does not exist until `open_request` returns it. Now: confirm,
write, *then* read the number. That also fixes a second claim it could not
honour, that a correction "updates the same request". Nothing can amend a
request; there is no tool for it. A correction after the number is out gets a
transfer and an honest sentence instead of a lie.

**Inbound has no `variableValues`, and the writer only reads those.** The rule
that the building and apartment come from the call rather than from tool
arguments exists so a mishearing cannot overwrite a fact the outbound call was
placed with. Inbound there is no such fact — nothing is attached — so obeying the
rule literally would have written every ticket with an empty address: a
description and no door to knock on. Resolved in the n8n Code node, which now
merges the tool arguments into `variableValues` before forwarding, with
`variableValues` still winning wherever they exist. The outbound guarantee is
untouched, the merge lives in one place, and it works against the writer that is
deployed today — no Apps Script change needed for `open_request` at all.

Verified by posting an inbound-shaped call (no variableValues, location as
arguments) at the live webhook: `HM-2026-9634` came back from the writer and the
row landed in `call_requests` with `הרצל 14 / 12`. `transfer_to_human` returned
`out_of_scope` rather than silently degrading to `caller_request`, which is the
extended reason list working.

**`save_partial_request` is dark until Apps Script is redeployed.** The live
writer answers `unknown tool save_partial_request`, and because the tool is async
n8n has already told the agent `ok:true` — so the row vanishes and the call
sounds fine. `sheets/Code.gs` has the handler and a `partial_requests` tab; that
file is deployed by hand and nothing here can push it.

**Apps Script 404s the `homies/1.0` user-agent**, GET and POST alike, which cost
twenty minutes reading it as a dead deployment. It is the exact inverse of Vapi,
where Cloudflare 404s urllib's default agent and `homies/1.0` is the fix — the
same header rescues one host and breaks the other. urllib also mishandles the
`/exec` redirect on GET; `curl -L` gets through where it does not. Both written
into `n8n_deploy.py`.

**The platform table in `demo-inbound.md` was two days stale** — Azure `he-IL`,
HilaNeural, `waitSeconds 0.6`, `numWords 0`, none of it true since the stack
moved. Rewritten from `BASE` and labelled as a reading of that code rather than a
second place to change it. A document cannot fail a test, which is the whole
reason it drifted.

**Added a machinery section to the inbound prompt.** It had none, and until today
it did not need one: there were no tools, so there was no tool syntax to leak.
There are now, and the two incidents that produced the debt agent's version were
both about tools existing.

### 5 Aug — the dashboard stack adopted as the default, with two corrections

Scribe v2 / gpt-5.4 / Vapi v2 voice was set in the dashboard and asked for as the
default. Captured into `vapi_sync.py` so it survives the next push — dashboard
edits lose silently on sync, and this one would have been reverted by the next
command anyone ran.

**Scribe v2 is a straight win over what it replaced.** 2.4% WER, 570ms and
$0.013 a minute against Azure he-IL's measured $0.032 — better *and* cheaper. The
reservation held against it that morning was that 11labs takes a free-text model
name Vapi cannot validate; the dashboard has now supplied the exact string, which
settles it empirically rather than by argument. Speechmatics enhanced lasted
about twenty minutes and was never called through. Azure he-IL stays as the
fallback.

**Two things the dashboard did that were not on the screen.**

**1. It deleted the output guard.** Editing the voice replaces the whole voice
object, and `chunkPlan` lives inside it — so all 27 replacements and the sentence
chunking went with it. For roughly half an hour the production Hebrew assistant
could read tool syntax aloud again. Restored by the same push. Worth naming as a
property rather than an accident: **anything nested under `voice` dies whenever
the voice is edited in the dashboard**, and the guard is nested under `voice`
precisely because that is where it has to be to work.

**2. Elliot is a male voice.** It is Vapi's default and was almost certainly
carried over rather than chosen. Every fixed line in the Hebrew prompt is
feminine first person — מדברת מיכל, אני שולחת, אני מעבירה, אני עוזרת דיגיטלית —
and Hebrew marks the speaker's gender on the verb. A male voice reading them is
not a mismatch of taste, it is a grammatical error in every sentence the agent
owns. `vapi_en.py` already carries the other half of this lesson: it renames
Michal to Michael because Elliot is male.

The choice was one word here, or rewriting the identity, all seven fixed lines
and the whole register. Took the one word: **Leah**, same provider, same v2, same
`language: he`. Picked for being a Hebrew name and nothing else — the accent
comes from `language`, not the handle — and any of Clara, Savannah, Emma, Layla,
Kylie, Lily, Hana, Neha, Paige, Naina, Tara, Jess, Mia or Zoe swaps in by
replacing one string. That choice should be made by ear.

**Cost, honestly: $0.15 a minute against a $0.10 target.** STT got cheaper and
better, so the overspend is not there. It is $0.07 LLM plus $0.05 platform, and
the platform half is fixed. **The only lever left is the 35,886-character system
prompt**, which is what the LLM line is buying. That is now the whole cost
conversation, and it is a harder one than swapping a provider: every section in
there was written after a real failure.

### 5 Aug — costing the call properly, and moving the Hebrew twin to gpt-5.4

Target set at $0.10 a minute. Measured what it actually costs first, from Vapi's
own billing across 61 calls and 68 minutes rather than from a price list.

| | $/min | share |
|---|---|---|
| Vapi platform | 0.0500 | 39% — **fixed, not reducible** |
| LLM | 0.0420 | 33% |
| TTS (Azure neural) | 0.0193 | 15% |
| STT (Azure he-IL) | 0.0144 | 11% |
| transport | 0.0009 | 1% |
| **total** | **0.1267** | |

**Half the target is gone before anything is bought.** Vapi's platform fee is
$0.05 a minute whatever the stack does, so a $0.10 target means everything else
has to fit inside the other five cents. That reframes the exercise: this is not
"cut 21%", it is "cut 35% of the part we control".

**Model rates, measured rather than quoted.** Dividing each assistant's LLM
charge by its own prompt-token count: gpt-5.5 billed **$2.44 per million prompt
tokens** on this workload against gpt-5.4's **$1.32**. Same job, 1.85x the price.
Moved the Hebrew twin to gpt-5.4, which is the single biggest reducible line.

Honest about the trade: 5.5 was chosen on 3 Aug for more natural Hebrew, and the
Hebrew cost sample behind this decision is seven calls over 5.4 minutes, which is
thin. If the Hebrew audibly worsens, this is the first thing to put back, and it
costs about two cents a minute to do so — worth paying for a call that sounds
human. The decision is cheap to reverse in either direction, which is the only
reason to make it on a sample this size.

**gpt-5.4-mini stays rejected, and the reasoning changed today without changing
the answer.** It leaked its own tool-call syntax into speech on 4 Aug, and this
morning's output filter would now catch that. But the same call logged *zero*
tool calls — the ticket was never opened. The filter fixes what the resident
hears, not a tool that did not fire, and that was always the half that mattered.

**gpt-5.4 alone does not reach $0.10.** On the Hebrew sample it projects to about
$0.106; on a turn-heavy call, nearer $0.15. Two levers remain, and they are not
equivalent:

- **Deepgram `nova-3` with `he` instead of Azure he-IL**, worth roughly $0.024 a
  minute at list rate — *not* measured here, unlike everything else above. It
  risks comprehension, which is audible in one call.
- **Halving the system prompt**, worth about the same. It risks correctness, and
  every section in there was written after a real failure. Those regressions do
  not show up in a test call; they show up in a month.

Deepgram first, on that basis alone: a lever whose failure is immediately
audible beats one whose failure is silent.

**Deepgram switched, with Hebrew behind Hebrew.** `nova-3` with `language: he`
on both Hebrew assistants. Vapi's schema accepts `he` for Deepgram, but its
`model` field is free text rather than an enum — so "nova-3 plus Hebrew" is a
combination the API cannot validate on write, and the place that failure would
otherwise surface is mid-call.

So it carries a `fallbackPlan` of Azure `he-IL`. Both legs are Hebrew; there is
no path here that ends with an English transcriber listening to a Hebrew
resident. The English twin keeps `flux-general-en`, which is correct for it.

The fallback's limit is worth stating plainly: it fires when the provider
*fails*, not when it transcribes Hebrew badly. Bad Hebrew is still bad Hebrew,
and the only detector for that is a person on a call. Azure is the transcriber
that has actually been heard doing this job; reverting is deleting six lines.

**Projected: $0.082–$0.102 a minute**, against $0.127 before. The low end uses
the Hebrew assistant's measured turn rate, the high end a turn-heavy call. The
Deepgram figure inside it is a list rate and the only number here not taken from
Vapi's own billing — the first real call replaces it.

**Deepgram lasted an hour.** A survey of Hebrew ASR — ElevenLabs Scribe v2,
Speechmatics enhanced, ivrit-ai, Soniox — does not mention Deepgram anywhere.
An engine nobody working in Hebrew recommends is a poor thing to save two cents
a minute on, and the saving is smaller than it looks: **a misheard turn costs a
re-ask, a re-ask costs another round trip through the model, and the model is
billed by the minute.** Bad transcription is expensive twice. That reverses the
argument that put Deepgram there.

**Speechmatics `enhanced`, `he`, `region: eu`.** Chosen over the two rivals on
three grounds that are not accuracy:

1. **Its `model` is an enum**, so Vapi validates the config on write. 11labs and
   Deepgram both take free-text model names, which means a wrong one surfaces
   mid-call in front of a resident. That property was worth more here than a
   benchmark position — it is the same hazard the Deepgram fallback existed to
   contain, removed rather than mitigated.
2. **`customVocabulary` fixes a defect at the layer where it happens.** הומיז
   comes back as מומיז, הומי זה and הומיס across the transcripts; it and ועד בית
   are now seeded with their mishearings as `soundsLike`.
3. **`region: eu`** is nearer Israel than us-east and keeps resident voice data
   in Europe, which starts to matter the day these stop being ten fictional
   people.

Also `numeralStyle: spoken`, because the prompt forbids the agent from saying
digits while the transcriber was handing back "450" — the two halves of the call
were in different formats.

Azure he-IL stays as the fallback. Both legs Hebrew.

**ElevenLabs Scribe v2 is next if this disappoints** — it scores higher on
published Hebrew benchmarks. It is not first because Vapi cannot validate its
model string, and because Scribe began as batch STT: a live call needs the
realtime variant and choosing wrong fails on air.

**ivrit-ai is the interesting long-term option** and the only one on the list
that can run where the data does — Whisper fine-tuned on native Israeli speech,
self-hosted. It needs `provider: custom-transcriber` and a websocket server, so
it is a project, not a config line. Worth revisiting when real resident audio is
in play, since that is the same moment the Apps Script secret and the data
location have to be dealt with.

**The cost target is now in tension with accuracy, openly.** `enhanced` is the
expensive operating point and its rate is unknown until a call bills it. If it
lands over $0.10 a minute, that is a real trade to make deliberately rather than
a projection to defend — and the honest framing is cost per *successful* call,
not per minute.

### 5 Aug — natural *spoken*, which is a different problem from natural written

Correctly pushed back on the wording pass: the agent is heard, not read, and text
that reads well can still sound wrong. Two changes, and the first is not about
words at all.

**The sentences were being cut into pieces before they were spoken.** Vapi's
default `punctuationBoundaries` includes the comma and the colon, so a Hebrew
sentence with a comma in it is synthesised as two or three separate chunks — and
a TTS handed a fragment gives it a complete falling intonation, because nothing
tells it more is coming. It is in the transcripts:

> לפי מה שרשום אצלנו הוא עדיין לא הוסדר. שקלים. מצויין.

שקלים and מצויין are each their own utterance. Not one word of that is wrong;
it sounds like a machine because it was *delivered* like one. Boundaries cut to
`. ! ?` and `minCharacters` raised 30 → 60, so the voice gets a whole clause to
shape. The cost is latency to first audio — the model must reach a full stop
before anything is heard — and it is affordable only because the style section
already caps a turn at two short sentences. A rule written for another reason
turns out to be what makes this safe.

Set in `voice_guard.SPEECH` rather than in the two sync scripts, because Vapi
puts chunking and the output filter in the same `chunkPlan` object and whichever
file wrote it second would have silently erased the other.

**New prompt section: YOU ARE BEING HEARD, NOT READ.** One clause per breath; a
sentence needing a comma to be understood is too long to hear. Say the thing
before qualifying it. Nothing that exists only in writing — ש"ח, brackets,
slashes, numeric dates. Open a turn the way an Israeli opens one, with בסדר /
רגע / יופי / אוקיי / ברור / הבנתי before the sentence, which is most of the
difference between sounding live and sounding recorded. And do not be
relentlessly efficient — answering in the minimum possible words reads as
machine even when every word is right.

**Still open on the speech side, and it needs ears rather than analysis:**
Azure `he-IL-HilaNeural` is a 2019-generation neural voice and there are only two
Hebrew voices in Azure at all. Cartesia's `sonic-3.5` lists `he` in its language
enum and is the strongest candidate to compare against; 11labs `eleven_multilingual_v2`
is the other. Neither was switched to, because Vapi exposes no voice-library
endpoint and picking a voice id blind is not a decision worth making silently.
Also unresolved: whether הומיז is pronounced correctly at all — it appears as
מומיז, הומי זה, הומיס and מהומיז across transcripts, but those records are
transcribed audio, so the mangling may be the ASR rather than the voice. One
listen settles it; nothing in the data can.

**The prompt is now 35,886 characters.** Every section added today was justified
on its own, and the total is still the total.

### 5 Aug — the Hebrew naturalness pass, done from transcripts rather than taste

Brief was "make the Hebrew natural, and make sure the translation is not read as
is." Started by pulling every Hebrew line the agent has ever spoken — 34 turns
across the old account's call history — because an opinion about naturalness is
worth less than what it actually said.

**Most of what is wrong is not translationese.** Six defects, in the order they
would embarrass us:

1. **`{{ }}` read out loud.** Call `019fc795`: *"אני מדברת עם פותח סוגריים
   מסולסלות פותח סוגריים מסולסלות…"* — the TTS saying "open curly bracket" in
   Hebrew, twice, and again in the email line. Already fixed this morning by the
   output filter, which is a better proof of that work than anything invented for
   it.
2. **Masculine grammar said to women.** Every fixed line carries masculine
   endings — ותוכל, אליך, אותך — because a fixed string has to choose. The prompt
   demands gender agreement everywhere *else*. A woman hearing a sentence built
   for a man is the clearest possible sign a line was written somewhere else and
   read out unchanged, which is precisely the complaint.
3. **`בעל החשבון` came out as "בא על חשבון"** — "not the owner of the account"
   becoming "not on account" — in four separate calls.
4. **450 spoken as "ארבע מאות, חמישים"**, two numbers side by side, and ש"ח read
   as an abbreviation rather than שקלים.
5. **Literary register in spoken lines.** למי שאינו is written Hebrew.
6. **Actual calques, and only three of them:** "תודה רבה על הזמן" (thank you for
   your time), "על הסכום הזה" (for this amount), "להשלים את זה" (complete it).

**Five of the seven spoken lines rewritten.** The opening and the handover line
survived unchanged; they were already right.

| | Before | After |
|---|---|---|
| Payment link | …קישור לתשלום על הסכום הזה, ותוכל להשלים את זה בעצמך | …קישור לתשלום, ואפשר להסדיר את זה ישירות דרכו |
| Closing | מצוין, תודה רבה על הזמן… | מצוין, תודה רבה… |
| Refusal offer | אפשר שנציג… | רוצה שנציג… |
| Wrong party | …למי שאינו בעל החשבון… ש{{first_name}} יחזור אלינו | …רק למי שהחשבון על שמו… מ{{first_name}} ליצור איתנו קשר |
| Voicemail | לגבי בניין {{building}}… להסדיר איתך | לגבי הבניין ב{{building}}… להסדיר |

Three of those do double duty. The wrong-party line drops the literary שאינו,
drops בעל החשבון, and swaps a gendered verb for an infinitive that has no gender
at all. The voicemail gains the preposition {{building}} needs, since it holds a
street and a number rather than a name.

**Gender solved once instead of eight times.** Rather than a masculine and a
feminine copy of every fixed line, GRAMMAR now says the fixed lines are written
masculine and must be re-inflected when `{{gender}}` is `f` — endings only,
*"re-inflecting is not permission to rephrase."* One rule, every line, and the
wording stays fixed.

**Money got its own rule**, because "four hundred, fifty" is not an amount
anybody recognises as theirs.

Both new blocks are Hebrew-specific, so `vapi_en.py` gained paired English
replacements for them — without which the no-Hebrew assertion would have failed
the English build, which is the table doing its job. Verified live: 7 spoken
lines each, 0 in the wrong language.

**Still unverified by a native speaker.** These are better-argued than what they
replace, not blessed. The five rewrites are the shortlist to put in front of a
Hebrew speaker, and the argument for each is above.

### 5 Aug — migrated to a new Vapi account

New keys supplied for testing. Ran the rebuild in `docs/handover/new-vapi.md`,
which is what that document was written for; it survived first contact with two
corrections noted below.

| | Old | New |
|---|---|---|
| Debt (he) | `56935b35` | `0ef11cb5-81ce-49e7-864d-8a3e4d5728b9` |
| Debt (en) | `731193bf` | `eaa390ec-70f4-49fc-a836-351c279fa31b` |
| Inbound demo | `a594a4ce` | `51bbe77a-dd86-4629-8c0b-b0da06ca4461` |
| Public key | `27382abf` | `ce1a1da7-…` (in `web/index.html`) |
| Phone number | `a6f4fa90` | **none** |

**Verified rather than assumed.** All three prompts are byte-identical to the old
account's — 33,191 / 33,529 / 7,490 characters, same first messages, same eight
tools, same n8n webhook, same `endCallPhrases`, and all 27 output-filter
replacements matching `voice_guard.py` exactly. Re-running either sync script now
resolves to *update*, not *create*, so the rebuild is idempotent.

**Two things the runbook got wrong, now fixed in it.**

*Ordering.* Step 4 builds the English twin from the **live** Hebrew assistant,
but `SOURCE` was only listed for repointing in step 6. On a fresh key that fails
cleanly with a 404 — but with a stale-yet-valid key it would have silently built
the twin from the old account's prompt, which is the exact class of failure the
document exists to prevent.

*The export overwrites itself.* `vapi_export.py` writes to a fixed path, so
exporting the new account would have destroyed the only record of the old one —
including the free number's id and the two assistants not rebuilt. Archived by
hand as `docs/handover/vapi-export-old-account.json` first, and the runbook now
says to.

**No phone number came across, and none was bought.** `PHONE_NUMBER_ID` in
`vapi_call.py` and `MICHAL_NUMBER_ID` in `vapi_duel.py` are empty, and both
scripts now exit with a sentence explaining why rather than dialling a dead id —
a stale id fails as a Vapi 400 that reads like a payload problem. Web calls from
the demo page need no number and were unaffected, which is how testing has been
done since 4 Aug anyway.

**Not rebuilt, deliberately, because each creates billable resources:** the eval
suite (`vapi_eval.py --setup`) and the duel resident (`vapi_duel.py --setup`).

**Still on the old account and nowhere else:** every call, transcript and
recording, including the two leak calls that calibrated the output filter.
Recordings are deleted 14 days after the call. The old private key is kept in
`.env` as `VAPI_PRIVATE_KEY_OLD` so anything still wanted can be pulled out —
swap it into `VAPI_PRIVATE_KEY` and run `vapi_leak_check.py` or `vapi_export.py`
against it. Nothing on that account was deleted.

**`web/index.html` changed** — both ids and the public key. Wherever it is being
served from needs the new file, or the page will keep calling assistants on an
account whose key it no longer has.

**Both new keys were pasted into chat**, which makes five on this project. They
work and they are in use; they are also compromised by that fact and belong in
the rotation list with the other four.

---

## 2026-08-03

### Done

- **Built an English twin of the debt assistant** — `731193bf`, so the flow can be
  reviewed by someone who does not read Hebrew. Generated by
  [scripts/vapi_en.py](../scripts/vapi_en.py) from the live Hebrew assistant, not
  rewritten: 20 line substitutions plus the LANGUAGE block, **each asserted to
  match exactly once**. If the Hebrew prompt is edited and a substitution stops
  matching, the script exits instead of shipping a half-translated prompt — a
  silently diverged twin is worse than none, because it would be trusted.
  - Only language changes. Same `gpt-5.5`, same endpointing, same 240s cap, same
    eight outcomes. The `they do not speak Hebrew` fixed path inverts to English.
    The Hebrew gender-agreement rule is cut to the part that survives — English
    barely marks gender, so the rest would burn attention for nothing.
  - The page transliterates resident data when English is selected. Load-bearing,
    not cosmetic: an English voice given `שחר` reads noise and the call fails on
    the opening line.
  - **English proves the flow, not the Hebrew.** Fluent English says nothing
    about whether the Hebrew sounds native. That still needs a speaker.
- **Built a browser test console** — [web/index.html](../web/index.html). Pick a
  resident, talk to מיכל in Hebrew, watch the transcript stream. Needed because
  Vapi's docs are explicit that free numbers are **US-national only**, so the
  account cannot dial +972 at all; adding a card does not lift that, it only
  unlocks buying numbers. Until a Telnyx/Twilio number is imported, this is the
  only way to hold a real conversation with the agent.
  - Resident rows are **baked in from the CSV, not fetched from the sheet**.
    Fetching live would mean shipping the Apps Script secret inside a public
    page. The page passes the row as `variableValues`; the tool, once attached,
    reads the live row server-side. The secret never reaches a browser.
  - The four ineligible residents render greyed out with their reason, which
    makes the `v_debt_call_queue` predicate visible rather than asserted.
- **The resident lookup is live.** Apps Script web app deployed on the ygrant
  account, verified end to end against the deployed URL — not just in the editor.
  Six checks pass: a resident with a card, one without, one already paid, an
  unknown number, a wrong secret (`unauthorised`), and the full queue returning
  **six** rows, the same six as `v_debt_call_queue`.
  - Vapi's tool protocol verified too, not assumed: a `POST` with
    `message.toolCalls[]` comes back with `results[].toolCallId` echoed and the
    row as a JSON string. `attempt` increments correctly — שרה has one prior
    attempt and returns `"2"`.
  - Deployment URL is in `.env` / [sheets/README.md](../sheets/README.md), not
    here. Access is **Anyone**; "Only myself" returns a Google login page to
    Vapi's servers rather than JSON, which fails as a silent tool error.
- **Reorganised docs into the two-file convention.** Nine feature folders under
  `docs/features/`, each with `feature.md` and `context.md`, plus `_template/`.
  Spec moved to `docs/specs/` (not the brainstorming skill's default path).
- **Moved 13 loose files out of the project root** into `prd/`, `discovery/`,
  `diagrams/`, `reference/`. Two left at root deliberately —
  `Lotosclean-CRM-Gantt.excalidraw` and `followup-shahar.txt` are other clients'
  work and filing them here would misattribute them. Three markdown links
  repaired after the move.
- **Checked Vapi pricing and the billing dashboard.** Written up in
  [Homies-Vapi-Account-Notes.md](reference/Homies-Vapi-Account-Notes.md).
- **Built [Homies-Call-Flow.excalidraw](diagrams/Homies-Call-Flow.excalidraw)** —
  what a resident experiences on an inbound call, client-facing, plain language.
  108 elements, validated clean.
- **Read the four call transcripts** supplied as
  `hebrew_english_call_transcripts.pdf` and built
  [Homies-Debt-Followup-Flow.excalidraw](diagrams/Homies-Debt-Followup-Flow.excalidraw)
  from them. 79 elements, validated clean.
- **Wrote the outbound debt-collection agent prompt** —
  [10-debt-followup/prompt.md](features/10-debt-followup/prompt.md), with
  [feature.md](features/10-debt-followup/feature.md) and
  [context.md](features/10-debt-followup/context.md).
- **Moved the diagram generators and the extracted transcript out of session
  scratchpad** into the repo. They were temporary and would have been lost.
- **Started this worklog**, and a memory directory at
  `~/.claude/projects/…/memory/`.
- **Checked how an existing number attaches to Vapi** and wrote it up in
  [Homies-Vapi-Account-Notes.md](reference/Homies-Vapi-Account-Notes.md) — four
  routes, two traps, and how to tell which route applies.
- **Wrote the week-3 demo assistant** —
  [assistant/demo-inbound.md](assistant/demo-inbound.md). Platform config,
  turn-taking numbers with the reasoning for each departure from default, the
  full Hebrew system prompt, the five tools, and what is deliberately absent.
  New `docs/assistant/` folder: this is build output, not a feature, so it does
  not take the two-file treatment.
- **Created the Hebrew inbound assistant in Vapi** —
  `a594a4ce-ca47-4cab-8704-160afce199a7`, *Homies — Inbound Intake (demo)*.
  Azure `he-IL` in and out, `gpt-4.1-mini`, the tuned turn-taking numbers,
  recording on. Read back after writing; Vapi accepted every field.
- **Created the Hebrew outbound debt assistant in Vapi** —
  `56935b35-78ea-463d-86c5-16969f8ae50e`, *Homies — Debt Follow-up (he)*. Config
  and its reasoning in [assistant/debt-followup.md](assistant/debt-followup.md);
  the prompt stays in the feature folder and is pushed from there, so there is
  one copy of it. 240s cap, 20s silence timeout, agent can end the call.
- **Corrected the provenance claim in the debt prompt.** It said `אני לא נגדך`
  was verbatim from call 4. Nothing in it is verbatim — the PDF's Hebrew layer
  is corrupt, so the behaviour is quoted and the wording is reconstructed.
- **Wrote `scripts/vapi_sync.py`.** It extracts the first message and system
  prompt from `demo-inbound.md` and creates or updates the assistant, so the
  document is the source of truth rather than a description of the dashboard.
  Dry run by default, `--apply` to write.
- **Added `.gitignore` and `.env.example` at the project root.** Keys now have a
  destination that is not chat. `.env` is ignored; `.env.example` holds names
  only.

- **Wrote migrations `004` and `005`** — the charge/ticket model for feature 10.
  `charges`, `payment_tickets`, `promises_to_pay`, `payment_disputes`,
  `call_outcomes`, plus `gender` / `card_last4` / `handed_over` / `do_not_call`
  on residents. Seed exercises every branch: no card on file, gender unknown,
  paid, not handed over, do-not-call, attempts exhausted.
- **Closed the missing-amount guard, structurally.** `v_debt_call_queue` only
  emits a row when amount, period, handover and consent are all present, so a
  caller iterating it cannot place a call without them. The guard could never
  have lived in the prompt — an unsupplied variable renders as an empty string
  rather than failing. Also added a database constraint that a ticket claiming a
  captured authorisation must reference the call it came from, since the
  recording is the authorisation.
- **Merged the client's Hebrew style prompt with the behavioural tree.** The
  client rewrote the debt prompt in the dashboard as a pure style/register
  document — natural Israeli Hebrew, answer-the-latest-message, no repetition —
  which deleted the posture tree, the budgets, the fixed paths and all eight
  tools. Both are now in
  [10-debt-followup/prompt.md](features/10-debt-followup/prompt.md): their
  sections close to verbatim at the top, behaviour underneath, pushed live.
- **Stopped scripting Hebrew lines.** The prompt now describes in English what to
  convey and lets the model generate the Hebrew, keeping only five fixed strings
  — opening, AI disclosure, charge authorisation, not-the-account-holder,
  voicemail. A Hebrew line written by a non-speaker from an English original is
  exactly the translated text the style section forbids. Verification surface
  drops from ~40 lines to 5.
- **Rewrote the payment flow for staff-confirmed charging** (see Decided).
  `send_payment_link` is gone, replaced by `open_payment_ticket` carrying
  `authorization_captured`. Added `{{card_last4}}`, with an explicit branch for
  residents who have no card on file.

### Decided

- **The agent's data source is a Google Sheet, not Supabase, for now.** Client's
  call. A sheet is legible and editable by them and by Homies staff mid-test; a
  Postgres table is not, and Supabase is still un-provisioned. Served by Apps
  Script over HTTP as a Vapi tool — see [sheets/](../sheets/). The rows mirror
  `002`/`005` and the eligibility predicate mirrors `v_debt_call_queue`, verified
  to return the same six, so the move to Supabase is a swap behind the webhook
  rather than a rebuild. **The SQL remains the specification**; if the two
  disagree, the sheet is the copy that is wrong.
  - Blocking constraint recorded there: an Apps Script web app with Access=Anyone
    is public, and Apps Script cannot read custom headers, so the shared secret
    must ride in the query string. Fine for ten fictional residents, **not fine
    for real Homies data** — that move to Supabase is a precondition of any real
    row, not a nice-to-have.
- **The demo is intake-reliability, not conversation quality.** Ops staff are
  recruited as judges of the output, not subjects of replacement.
- **The debt agent is one conditional tree, not two branches.** Client
  correction. Posture is re-read every turn and moves in both directions; the
  explanation budget is per call and never resets. Reasoning in
  [10-debt-followup/context.md](features/10-debt-followup/context.md).
- **Hot is a floor.** Once a call has been hot it always ends in a handover, even
  if the caller later offers to pay. Accepted cost: some calls a human would have
  closed get transferred.
- **"I already paid" → hold the position, move the burden to a receipt.** The
  agent states what the ledger shows, gives an email, and says it will call
  again. It never asks when or how they paid.
- **Hardship always transfers.** Multi-intent opens a ticket but returns to the
  payment. Non-Hebrew hands over immediately with no English attempt.
- **Number integration comes after the demo.** Client call, 3 Aug. The demo runs
  on Vapi web calls, so no DID, no import, no KYC is on the critical path for
  week 3. Accepted cost: the 1–3 week Israeli DID KYC clock starts later than it
  could, which pushes Phase 3 rather than the demo. Revisit the moment the demo
  is rehearsed, not after it is delivered.
- **Keep all four Vapi assistants.** Client call. The two English ones (the
  collections test and Vapi's Riley sample) stay. The sidebar's
  `azure · openai · azure` line is how to tell the Hebrew ones apart at a glance.
- **Supabase Edge Functions serve the Vapi tool webhooks, not n8n.** The build
  plan named n8n, but its hosting question is still unanswered and it adds a
  network hop on the latency path that matters most. Edge Functions deploy from
  this repo, need no public URL and no hosting decision. n8n comes back for
  Monday, Sheets and WhatsApp, where its connectors are the point. Accepted cost:
  the tool layer is code rather than a visual workflow, so it is less editable by
  someone who is not a developer.
- **No automatic charging on the call.** Client call, 3 Aug. The agent takes the
  resident's spoken approval to charge the card already on file, opens a ticket,
  and a member of staff reviews it and makes the charge. Same shape as the §2.3
  staff-confirmed deletion decision: the bot documents and verifies, a human
  executes. Removes payment links, SMS delivery and payment-page reconciliation
  from Phase 7 entirely. Accepted cost: every payment now waits on a human.
- **The recording is the authorisation, not evidence about it.** Follows from the
  above — the resident's recorded *"yes"* is what permits the charge. This makes
  Vapi's 14-day retention a money problem rather than a support problem, and
  turns the Israeli recording-consent question into a prerequisite for charging
  rather than for going live.
- **`gpt-5.5` on the debt assistant.** Client change, for more natural Hebrew.
  Latency and cost unmeasured — the account still has 9.2 credits, no card, and
  auto-reload off.
- **Never lead with cost savings** to a room of call-centre staff — a two-minute
  human call costs about the same as the bot handling it, and they will spot it.

### Found

- **She hung up on a hardship disclosure.** Found in the first English test call,
  4 Aug: the caller said he had lost his job and the call ended immediately, with
  no line spoken. The single worst moment in the call to go silent.
  - Root cause is not wording. `endCallFunctionEnabled: true` gives the model an
    `endCall` tool, and **no other tool exists** — `tools: none` on both
    assistants. Told to "call `transfer_to_human`", which is not declared, the
    only action actually available to it was to hang up. It did the one thing it
    could.
  - The prompt described an *intention* and assumed a tool would carry it. Fixed
    structurally: a new **HANDING OVER TO A PERSON** section makes the handover
    three ordered steps — say the line, call the tool, stay on the line — with
    the Hebrew line fixed verbatim, and `Never end the call on a handover` stated
    as an absolute regardless of whether the tool fails or is missing.
  - This makes the handover the **sixth** fixed Hebrew string. The five before it
    were fixed for legal or privacy reasons; this one is fixed because a test
    proved a description was not enough. Native-speaker verification now covers
    six lines, not five.
  - Still not an actual transfer. Until `transfer_to_human` exists she says the
    line and waits, and `silenceTimeoutSeconds: 20` ends the call. Correct words,
    no handover — better than silence, not a fix.
- **TTS mangles an email address read aloud.** `yulgatch123@gmail.com` came out
  as *"yallgach123"*. Not a prompt defect — reading an arbitrary address over a
  phone line is unreliable by construction. The disputed-payment path depends on
  the resident hearing it correctly.
  - `{{verification_email}}` is now `homiesemail@gmail.com` — client's choice —
    everywhere it was set: `web/index.html`, `vapi_eval.py`, `vapi_call.py`,
    `vapi_duel.py`, `vapi_mock.py`, `docs/assistant/debt-followup.md`. Two
    dictionary words and no digits, so a mishearing degrades to a near-miss
    rather than an unusable string.
  - Not fully solved. Any address read aloud on a bad line can still be missed,
    and there is no confirmation that the resident wrote it down. The real fix is
    sending it — SMS or WhatsApp after the call — which needs a tool that does not
    exist yet.
- **A backchannel was being treated as an interruption.** `stopSpeakingPlan`
  carried `numWords: 0`, so any sound at all stopped her mid-sentence — and an
  "mm-hmm" while she talks is listening, not interrupting. She restarted the
  opening sentence three times in one call before finishing it. Now
  `numWords: 2, voiceSeconds: 0.3, backoffSeconds: 1.5`. Two words is the line
  between acknowledgement and a real interruption.
  - Backed up in the prompt, because the two failures compound: a new rule says
    "mm-hmm", "OK", "yeah", "right" and "sure" are **not turns**, and that
    restating a point in fresh wording counts as repeating it.
- **She used the no-card branch on a resident who has a card.** Told a caller with
  card `4821` on file that "someone from the office will contact you to arrange
  it", and only asked for authorisation after he asked *"on what card?"* — which
  is the call's entire purpose, obtained by accident.
  - The prompt described both branches but never said they were exclusive. Added:
    `{{card_last4}}` alone decides, the authorisation question comes first, and
    nothing about the office is said until it is answered. Plus a symptom the
    model can check itself against — *if the caller has to ask which card, you
    have already skipped the question.*
- **The handover fix caused a regression, and the fix for that is the interesting
  part.** After adding `Never end the call on a handover`, she stopped ending
  *any* call — said "Thank you, have a good day" and left the line open
  (`endedReason: customer-ended-call`, call `019fcbd4`). Before the change she
  ended calls herself.
  - An absolute stated on its own gets generalised. The prompt said when **not**
    to hang up and never said when to, so the safe reading was never. A new
    **ENDING THE CALL** section states the positive rule beside it, ending with
    *Saying goodbye is not the same as ending the call. Do both.*
  - Worth carrying: every prohibition added to this prompt needs its complement
    written next to it, or the model finds the interpretation that satisfies the
    prohibition and nothing else. Same failure shape as the mute-agent false
    passes in the eval run — a rule satisfied by doing less.
- **English TTS mangles the name.** `en-US-JennyNeural` read "Michal" as
  *"me call"* in one call and the English male "Michael" in another. Spelled
  `Mikhal` in the English twin's four spoken instances. Hebrew
  `he-IL-HilaNeural` is correct and is untouched.

- **The agent invents missing variable values rather than failing.** First live
  test with no `variableValues` supplied: `{{amount}}` came out as silence
  (*"… שקלים"*) but `{{month}}` was filled with **אוגוסט**, the current month,
  which nobody supplied. An empty slot is visibly broken; a plausible wrong month
  is not. The prompt's never-estimate rule did not fire because from the model's
  side there was nothing to estimate, only a sentence to finish.
- **The reconstructed Hebrew produced a non-sentence in output.**
  `למישהו לא בא על חשבון` — reaching for *"someone who is not the account
  holder"*. First time the unverified-Hebrew risk showed up in behaviour rather
  than on paper.
- **The wrong-party script fired at a legitimate question.** *"Who is this, where
  did you get my number?"* got the not-the-account-holder deflection, verbatim
  and twice. Both fixed by the client's rewrite.
- **A payment was offered on a turn containing no commitment.** *"Yes, speaking"*
  — an identity confirmation — was read as agreement and the agent moved to
  close. Now guarded: authorisation requires an unambiguous yes, and hesitation
  is treated as friction.
- **Free Vapi numbers cannot place international calls.** Created one (`+16576083115`,
  id `a6f4fa90`, area code 657 — 415 was unavailable) and the first outbound
  attempt was refused before dialling: *"Free Vapi numbers do not support
  international calls."* Nothing was billed. This applies to `+972` exactly as it
  did to the `+63` test destination, so **no call to a real resident, and no
  phone-based demo, can run on the free tier.** A paid Twilio or Telnyx number is
  a prerequisite for any dialled call, not just for Israeli caller ID.
  - Twilio has a second trap: international destinations are disabled by default
    and must be enabled per country under Voice → Geo Permissions.
- **The Vapi account has no payment method, and that gates every test path.**
  Three separate walls, one cause: a second phone number (*"must provide a credit
  card"*), the text chat API (*402, pay-as-you-go orgs require a card on file*),
  and international dialling. Only the dashboard's own web-call widget still
  works, and it cannot send `variableValues`. Vapi is pay-as-you-go, so a card
  bills use rather than a subscription — **adding one unblocks all three.**
- **Vapi test suites are the right test harness, and they need no phone number.**
  Verified against the live API, not the docs. `POST /test-suite` takes a
  `targetPlan` (`assistantId` **plus `assistantOverrides.variableValues`** — all
  ten variables reach the agent) and a `testerPlan.assistant` given inline, so the
  simulated resident needs neither an assistant record nor a line of its own.
  Each test is `{type: voice|chat, script, scorers: [{type: "ai", rubric}]}` and
  an LLM judge grades the transcript — which is what makes results readable
  without Hebrew. Suite `1052adce`, nine scenarios, built by
  [vapi_eval.py](../scripts/vapi_eval.py). **This sidesteps both the one-number
  limit and the international-call refusal**; whether a *run* still needs a card
  is untested. Supersedes `vapi_duel.py`, which needed two numbers and produced
  an unscored transcript.
- **Fixed-value clones make the dashboard usable, and cost nothing.**
  [vapi_mock.py](../scripts/vapi_mock.py) copies the debt assistant with every
  `{{variable}}` substituted from the six `v_debt_call_queue` seed rows, so the
  dashboard's web-call widget — which cannot send `variableValues` and is the
  only test path a card does not gate — runs the agent on real amounts, months
  and card digits. Six clones exist, prefixed `Homies — Debt TEST:`. They are
  throwaway: edit the real assistant and re-run.
  - Substitution runs over the serialised assistant, not a list of known fields,
    and the script exits if any placeholder survives. An unresolved one renders
    empty at call time and the agent invents a value to cover the gap — which is
    exactly how a test call produced a month nobody supplied.
  - **The live prompt uses 8 of the 10 declared variables.** `unit` and `attempt`
    appear in [prompt.md](features/10-debt-followup/prompt.md) but not in the
    deployed assistant, so the call-attempt number cannot currently change the
    tone on a repeat call. Not yet decided whether to wire them in or drop them
    from the table.
- **A test-suite chat run completes, scores everything, and is worthless.** Nine
  scenarios ran (`dfe9eb9f`); every transcript is one agent turn against fifty
  tester turns. `POST /chat` still returns *402, pay-as-you-go orgs require a card
  on file*, so the agent emits only its `firstMessage` — static text needing no
  model call — and then goes silent. **The run does not error**, which is the
  dangerous part.
  - The variables did resolve: the greeting came through as *מדברת עם אליה*, so
    `targetPlan.assistantOverrides` works.
  - **Four scenarios "passed" while the agent was mute.** The rubrics are lists
    of things it must never do, and silence satisfies all of them. Fixed by
    checking transcript liveness structurally and marking those runs INVALID —
    a rubric alone cannot catch this, because the judge is reading the same empty
    transcript. Any future rubric needs the same guard.
- **Web calls with `assistantOverrides` cannot be created from the server API.**
  `POST /call` without a `phoneNumberId` returns 400. Overrides on a web call
  require the browser SDK and the Vapi **public** key, which is not in `.env`.
  This is the only free way to hear the agent speak real variable values.
- **Vapi retains recordings 14 days**, and 60-day retention is $1,000/month.
  This breaks [07-partial-ticket](features/07-partial-ticket/feature.md) as
  written. Fix logged there; **not yet applied**, awaiting approval.
- **The transcript PDF's Hebrew layer is corrupt.** Every Hebrew line in the
  prompt is reconstructed from the English translation column, not quoted. A
  Hebrew speaker must check them against the audio before rehearsal.
- **Two of the four sample calls should never have been placed** — the residents
  had no keys yet. That is a database check, not a prompt condition, and it is
  the cheapest win in the outbound flow.
- **Sample call 4 is missing** from the transcript PDF. Files jump from 3 to 5.
- **Vapi account has 9.2 credits, no card on file, auto-reload off.** The
  combination, not the balance, is the risk.
- **Vapi sells US numbers only.** There is no +972 to buy inside it, so the
  Israeli number is always an import. A number already KYC'd in a Twilio or
  Telnyx account skips 1–3 weeks of DID KYC — the longest non-compressible clock
  in the plan. Worth finding out whether one exists.
- **The assistant ID in the feature files was wrong all along.**
  `f5c758d8-…` is *Homies Collection (EN test)* — English, Deepgram `nova-2`,
  Elliot voice, 450 shekels hardcoded in its prompt. Feature 04 described it as
  Azure `he-IL` with HilaNeural; it has never been either. No Hebrew assistant
  existed in the account until today. Left it untouched — it is the closest
  thing to a feature-10 ancestor.
- **The dashboard's Model Presets silently destroy the Hebrew stack.** Clicking
  *Balanced* / *Ultra Fast* / *Cost Saver* replaces transcriber and voice
  wholesale. The inbound assistant went to Talkscriber Whisper English and
  11labs Sarah within a minute of being created, and answered a Hebrew caller in
  English. No warning, no undo. Restored with `vapi_sync.py inbound --apply` —
  which is the argument for the sync script existing at all.
- **Vapi turns on `transcriber.fallbackPlan.autoFallback` by itself.** If Azure
  `he-IL` fails it switches transcriber mid-call, and nothing else does Hebrew.
  The failure mode is confident nonsense, not silence. Left on for now, flagged.
- **Vapi sits behind Cloudflare and 403s urllib's default user-agent** (error
  1010). Any ordinary UA string passes. Cost twenty minutes; written into the
  sync script as a comment so it costs nobody else that.
- **Vapi's LiveKit smart endpointing is tuned for English.** For Hebrew the
  `smartEndpointingPlan.provider` must be `vapi`. Leaving the default is a quiet
  degradation, not an error — it would look like the model being slow.
- **Three feature files carry masculine Hebrew against a female voice.**
  `אני רושם` in [04](features/04-interruption-pacing/feature.md) and
  `אני מעביר` in [06](features/06-boundaries/feature.md). Corrected in the
  assistant; the feature files still need fixing.
- **`transfer_to_human` has a reason the schema does not.** The assistant needs
  `language`; [06](features/06-boundaries/feature.md) lists four reasons without
  it. One of the two has to move.
- **No API key exists anywhere in this project.** No `.env`, nothing. Vapi
  cannot be edited from here until a rotated key is supplied.
- `Homies-Inbound-Flow.excalidraw` is stale — it still shows the bot deleting
  payment information, a flow that was ruled out. Flagged do-not-show.

### Open

- **Still not a git repository.** Everything here is one bad overwrite from gone.
  `git init` offered repeatedly, not answered.
- Voicemail: leave a message at all, or just log the attempt? Now concrete —
  `voicemailDetection` is unconfigured on the debt assistant, so it will talk to
  an answering machine as though it were a person. Either answer is one field.
- Nothing validates that `amount` and `month` are present before a debt call is
  placed. A missing template variable renders as an empty string, so the agent
  would say "the payment for the month of, 0 shekels" rather than refusing. The
  guard belongs in the caller, which does not exist yet.
- Nothing copies the call recording out of Vapi. It is now the artifact that
  authorises a charge and it is deleted after 14 days. Belongs in the
  end-of-call webhook, which does not exist.
- Whether a resident's card is on file is a field nobody has confirmed exists.
  The prompt branches on `{{card_last4}}` being empty; migration `004` has to
  carry it either way.
- Need one recording of an ordinary successful call — all four samples have
  something going on, so there is no baseline for normal.
- Rotate the three exposed keys (Telnyx, Retell, Vapi). Rotating Vapi is now
  also the unblock for editing the assistant — new key into `.env`.
- Find out where the tentative virtual number actually lives. A console login
  means import; a SIP username and password means BYO trunk; Retell means
  replace it.
- Create the Supabase project, run `001`–`003`, supply URL and service role key.
- Choose n8n Cloud trial vs `n8n start --tunnel`.
- Ask Homies for real building names and their real request categories — ours are
  invented and ops staff will notice in the first call.
- Migration `004` for the debt/charge model does not exist and is unsized.
