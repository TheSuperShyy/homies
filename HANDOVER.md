# HANDOVER — Homies, everything you need to take over

**Current as of 2026-08-23.** If you have just been told "read the handover",
this file plus `CONTEXT.md` is the whole briefing. Read both, then start
working. Go to `docs/WORKLOG.md` only when you need to know *why* something
was decided — it is the chronology with full reasoning, newest first.

Rewrite this file after every piece of work. Present tense only, never
appended to.

---

## The project in a paragraph

Homies is an Israeli building-management company — ~193 buildings, ~10,000
apartments, ~19 staff — getting a Hebrew AI voice agent plus chatbots. Two
voice agents (inbound intake, outbound debt collection) and a WhatsApp bot,
all writing to one database, with a dashboard over the top. The client's
existing management system is **OXS**, which we read from and never write to.
The user is the builder; Homies is the client.

---

## The system, one page

**Two front doors, and no third.** A resident either opens `web/index.html`
and starts a **web call** (there is no phone number — nothing dials, nothing
can be dialled), or sends a **WhatsApp message** to one Meta test number.

**The runtime.** Web calls hit **Vapi**, which runs four assistants — Hebrew
inbound + debt, and English twins used for comparison. Hebrew stack is
ElevenLabs Scribe v2 for speech-to-text and Cartesia Sonic 3 for the voice,
attached with our own Cartesia key so Vapi bills ₪0 for TTS. WhatsApp messages
go **Meta -> Chatwoot -> n8n** since 21 Aug. Chatwoot owns the number and the
inbox; n8n is its *agent bot*, still at `/webhook/homies-whatsapp`, which checks
a shared secret in the query string, ignores everything that is not an inbound
`message_created`, dedupes on Chatwoot's message id, and runs an AI Agent on
OpenRouter with a 30-turn memory keyed by phone. Replies post back to Chatwoot,
never to Meta, so the inbox holds both halves of every conversation.

**Chatwoot assigns new conversations to the agent bot itself** (`assignee_type
"AgentBot"`), and only a **User** assignee counts as a takeover -- both the
WhatsApp gate and the handback filter check the type since 23 Aug, after the
bot spent two days silencing itself on every conversation newer than
conversation 1.

**The WhatsApp bot was field-tested 23 Aug and the findings are unfixed on
purpose.** 19 live Hebrew scenarios (33 exchanges), 10 judges, 85 findings
("Homies Bot Field Test" artifact, which now also prints every conversation
word for word as chat bubbles; verdicts in docs/WORKLOG.md). The short
version: attitude, refusals and privacy held; the promises were hollow --
zero open_request calls against three "went to the team" claims, one
fabricated ticket number (255-1048-26 -- the exact example the prompt's own
war story quotes), one turn of pure silence, and post-tool amnesia. The
missing transfer_to_human records behind three of four handover lines are a
**warning, not a failure -- the owner's call, 23 Aug**: with Chatwoot in the
path every chat stays answerable in the inbox within WhatsApp's 24-hour
window; it becomes a real failure again only if nobody watches the inbox or
the window passes. Worst three by harm: ghost tickets, the silent reply,
dead-end endings. The owner asked for findings, not fixes: change nothing in
the prompt or workflow without walking that report first.

**Except the emergency flow — rebuilt later on 23 Aug at the owner's
request, then re-tuned the same evening from commanding to calming.**
Emergencies no longer end at the one-line transfer cutoff, and the bot does
NOT open by ordering a call to emergency services. The prompt's protocol now
runs: confirm first whether it's really serious (one answerable question —
the resident assesses; the bot never declares severity in either direction,
"ייתכן שיש סכנת חיים" is quoted as the banned move); recognize panic from
the writing (caps, !!!, "הצילו") and be the calm one — acknowledge first,
short sentences, one thing per message; the hotlines 100/101/102/103 are
ADVICE for serious situations matched to the hazard ("אם המצב חמור, 102 הם
הכתובת הכי נכונה"), never a command; "we're not experts"; universally-
accepted safety precautions only, strictly no diagnosis; transfer to the
right department "takes a moment" (tool before text); ask them not to act on
their own or take rash steps; stay in the conversation one question at a
time, hotline availability said once, gently; cheerful words banned. Two
structural changes rode along, workflow now 30 nodes: **the promise
backstop** ("Promised a transfer, made none?" → "Transfer it anyway" →
"Carry the reply") makes any spoken handover real when the model skipped the
tool — every transfer writes interactions + call_outcomes + a needs_review
row in requests, so promises are staff-visible now; and **the silent reply is
plugged** — its mechanism was "Hand over instead" evaluating its text to
null (now String()-wrapped with a fallback), plus "Send" substitutes the
fixed line for empty content, so a blank outgoing message is impossible.
Also fixed on the way: `$('tool').all()` in main-flow expressions never sees
ai_tool output — tool-ran checks must use `isExecuted` (the phantom-ticket
check in "Reply usable?" had this latent bug too; fixed). Verified over four
live rounds, test data cleaned. Rollback snapshots in the session scratchpad:
wa-current-emergency.json / wa-before-backstop.json / wa-before-fixups.json,
each patch script takes --restore.

**Dead-end endings are fixed too (23 Aug, owner's direction).** The
follow-up lane ("Dead end reply?" → "Options again" → "Send menu") was an
orphan — no incoming edge since the cutover rewrite — and its checker's
conditions referenced unexecuted nodes bare, silently evaluating false. Now:
Send feeds the checker; every reply that ends without a question is followed
by "אפשר לעזור בעוד משהו?" (owner's phrasing) with the three menu buttons;
a reply announcing a handover ("אני מעביר...") stays quiet on purpose. Both
checker conditions read $json.content (Send's own response) — no cross-node
expression references in If nodes; bare `$('node')` on an unexecuted node
silently fails the condition. Rollbacks: wa-before-deadend.json /
wa-before-deadend2.json.

**The bot is Michael (23 Aug evening, owner's direction).** Every FIRST
message of a conversation opens with a polite personal hello — «היי, כאן
מיכאל מהומיז. איך אפשר לעזור היום?» — whatever the resident wrote; there is
no greeting matcher anymore (the exact-match regex is deleted from Sort).
Smalltalk gets a human answer. The media fixed line was removed from the
prompt entirely — the workflow answers real media itself before the model
runs, and the model is banned from ever claiming it "only reads text" (it
had said that to plain text on the owner's handset). Greeting memory is
time-based: greet again after 24 quiet hours; legacy boolean flags count as
stale, so every pre-existing contact gets the new intro once.

**Ghost tickets are fixed at the root (23 Aug, owner's direction).** The
model provably never chains verify_address → open_request (one tool call per
turn is what gemini-2.5-flash does), so the sequencing moved into the edge
function: on the WhatsApp channel open_request verifies the address itself
and refuses with verify_address's own reason codes instead of filing —
voice keeps normalise-never-refuse on purpose (function v37; the gate is
`channel(ctx)` on the wa: call-id prefix). The bot prompt teaches one call,
verify_address is demoted to address questions and emergency grounding, and
the prompt contains no example ticket numbers anymore — the bot had
fabricated one digit for digit. Verified live: real references in replies
matching real rows, refusals for unmanaged addresses with the street's real
numbers offered, no junk rows. Rollback: wa-before-ghost.json
(patch_wa_ghost.py --restore) + redeploy the previous index.ts. Still open
by design: the Chatwoot assign/label flag on transfers.

**The bot's on/off switch is the natural gesture: replying.** A public human
reply auto-assigns the conversation to the replier (the workflow does this;
Chatwoot itself does not), and an assigned conversation is one the bot stays
out of. The other switches work too: assign by hand, the **`bot-off` label**,
or **resolve**. The bot's own replies (`sender.type: agent_bot`) and private
notes never claim. After every bot reply the thread flips to `open`, so
everything shows on the default screen.

**Quiet hands it back.** "Homies — Chatwoot handback" (IVNR5iNn7bQS8JgP) runs
every minute: a handed-over conversation silent for **15 minutes** is
unassigned and stripped of `bot-off`, so the resident's next message gets the
bot instead of an agent who went home. Taking over resets the clock, and so
does every reply -- the bot never interrupts mid-conversation. Resolved
conversations are never handed back.

Held up by: **auto-assignment OFF** on inbox 1 (on, every conversation is
assigned on arrival and the bot never speaks), the `bot-off` label at account
level, and two n8n credentials -- bot token for replies, admin token
("Chatwoot admin", `N8N_CHATWOOT_ADMIN_CRED_ID`) for assignment changes.
Six-state switch test and reply-claim test passed 21 Aug.

**One writer, reached three ways.** Every write goes through the Supabase Edge
Function `debt-tools` (13 handlers, `--no-verify-jwt`, authenticated by
`TOOL_SECRET`). **Both voice assistants call the Edge Function directly** —
every tool, reads and writes alike — as does the end-of-call report. Checked on
the live assistants 20 Aug; the earlier claim that voice tools route via n8n
`/webhook/homies-debt-tools` was wrong. n8n serves the WhatsApp path only.

That matters when you run `vapi_sync.py`: `tool_server()` prefers n8n whenever
`N8N_BASE_URL` is set in `.env`, so a plain sync would silently move the voice
agents behind n8n and put every tool through the Decide node. Until that is a
decision somebody has made on purpose, sync with it cleared:

    N8N_BASE_URL= python scripts/vapi_sync.py inbound --apply

Every write opens an `interactions` stub first, so nothing is orphaned.

**The store.** Supabase Postgres (Tokyo region), the only store of record.
Tables: `residents`, `charges`, `interactions`, `requests`, `messages`,
`call_outcomes`, `payment_links`, `promises_to_pay`, `payment_disputes`,
`payment_tickets`, and since 13 Aug `buildings` + `apartments` (the OXS
address list, 173 active buildings and 4,092 flats — import-only).
Views: `v_buildings` (address, flat range, residents on file),
`v_debt_call_queue` (the eligibility guard —
unpaid, handed over, not do-not-call, attempts < 4, one row per apartment per
month), `v_debt_call_queue_person` (**the call queue since 11 Aug** — one row
per resident, every apartment they owe on, composed Hebrew phrases and the
`charges` whitelist; built on the charge view so the predicate exists once),
`v_conversations`, `v_pending_payment_tickets`.

**Never `npx next build` against a running dev server.** `next.config.mjs`
reads `NEXT_DIST_DIR`; a verification build is
`NEXT_DIST_DIR=.next-verify npx next build`. Sharing `.next` with `next dev`
serves a page with no CSS and no error in any log. Related: a corrupted
`.next` cache crashed the dev server on 28 Aug (`ENOENT` on
`webpack/server-development/*.pack.gz`, root then 404ing) — the fix is to stop
the process, delete `.next`, and start again. And a backgrounded `npm run dev`
in this harness reports `exited with code 127` while the server keeps
serving: check `netstat` and an actual HTTP probe before believing it died.

**The dashboard.** Next.js 14 on Vercel at `homies-dashboard.vercel.app`.
Pages: overview, tickets, debts, conversations, calls, call detail. Anon key,
no login since 9 Aug, read-only except `requests.status`.

**Where the call recordings and transcripts are.** `/calls` lists every voice
call; the `transcript` link on a row opens `/calls/<id>`, which carries the
facts, the summary, an audio player for the recording, the transcript laid out
as a conversation, and the tool calls the agent actually made. Both come from
`interactions` -- `transcript`, `audio_url` -- written by the end-of-call
report. **Vapi deletes its own recordings after 14 days** and nothing copies
them to our storage yet, so `audio_url` on an older call is a dead link while
the transcript beside it stays good. The search box on `/calls` matches
transcript and summary, works in Hebrew, and puts the term in the URL so a
search can be sent to somebody.

**Both Hebrew voice agents carry the gender rules**, from
`hebrew-voice-gender-pronunciation-skill.md`. Intake has had them since it was
written; the debt agent got the homograph traps (לך, שלך, איתך and four more --
spelled the same for both genders, said differently) and the neutral-phrasing
repertoire on 20 Aug. Both sit inside the span `DEBT_BLOCKS`/`INTAKE_BLOCKS`
replace, so the English twins carry an English grammar note instead and no
Hebrew table leaks to an English caller.

**The OXS import completed its first full pass on 24 Aug**, four days after the
secrets landed and thirteen days after it last wrote a charge. Until then every
real run was killed at the 45-minute ceiling partway through arrears, and the
write it was heading for would have raised 42P10 when it got there -- migration
012 dropped `(resident_id, period)` on 11 Aug and both importers still named it.
Also fixed that day: row-at-a-time writes (14m24s of the 18m46s residents step,
now seconds), `charges.source`/`charges.unit` never being set, block-buffered
stdout that made the killed step log nothing at all, a guard that read the clock
while the scheduler ran 51 minutes late, and a `/sync` page that counted queue
time as run time and treated only `failure` as failure. **A full pass is ~28
minutes**, almost all of it OXS rate limiting; the ceiling is 90. Watch it at
`/sync`, where every count now carries the age of its newest row. **A run
finishing in under a minute imported nothing** -- that is the daylight-saving
guard, not a success, and the page says so by name. The Run now button needs
`GITHUB_DISPATCH_TOKEN` (fine-grained PAT, Actions write) in Vercel; everything
else on that page works without it.

**The debt agent no longer transfers on "the lift isn't fixed".** It works
the objection first -- log the fault, say that the committee money funds the
repair, ask again -- then one smaller ask, then hands over. Changed 20 Aug,
both twins live, **not yet heard out loud.**

**Pagination sits above every table**, not below, on calls, tickets,
conversations and debts. It hides itself when the whole list fits on one page.

**Every row in `/calls` has a filled orange `View call` button**, including rows with no
transcript -- the detail page still shows the recording, outcome and tool calls.

**The call page is two columns** -- conversation left, summary / recording /
details / tools right -- collapsing to one column under 900px with the sidebar
first. The transcript scrolls inside its own pane; do not remove that cap
without replacing it, or the page length goes back to being whatever the call
length was. Speaker names are deliberately absent from the bubbles and stated
once in the panel header.

**Summaries start from 20 Aug, not before.** `analysisPlan.summaryPlan` was
added to the assistants that day; the 163 calls recorded before it have a null
summary permanently, because a summary is generated at end of call and cannot be
backfilled. A row reading "no summary" is an old call, not a fault. Paging is
`dashboard/components/pager.tsx` and lives entirely in the URL: `?page=` plus
`?per=` at 10, 25 or 50, ten being the default and the fallback for anything
off that list. Every filter on every list carries the size, and every size
change resets to page one. Debts is one row per
**apartment**, with `?by=owner` for one row per person and a marker on
apartment rows whose owner holds another flat. It filters by month —
`/debts?month=2026-07`, tabs derived from the data, `?month=all` for the
lifetime view — and opens on the newest **completed** month, because the
current month is never chased and the newest month carrying a charge is
defect 1 below.

**The 13 tools:** `open_request`, `save_partial_request`, `send_payment_link`,
`log_promise_to_pay`, `request_standing_order`, `log_disputed_payment`,
`transfer_to_human`, `log_call_outcome`, `get_balance` (read),
`get_request_status` (read), `verify_address` (read, 13 Aug — is this a
building we manage, does that flat exist in it), and two retired-but-answered:
`open_payment_ticket` (4 Aug) and `flag_not_handed_over` (11 Aug — **defanged**:
it no longer touches `handed_over` or waives anything; it pauses the apartment
and routes to a person). Since 11 Aug the three debt writes take an optional
`unit` — the agent **selects** an apartment already on the call, resolved
server-side against the `charges` whitelist; an off-call unit is refused, never
widened. `transfer_to_human` gained reason `ownership` ("that flat is not
mine"): pauses the named apartment to `pending_charge`, changes no ownership
record. It still **connects nobody** — it writes the call to the office. Never
say anyone is being put through.

---

**DEFECT CLOSED 30 Aug: the inbound agent broke when asked for the office
number.** Call `01a05232` produced `ב0.7`, `7`, then `6.` thirty-eight times.
The prompt held the number as the numeral `077-6687949`; Vapi's formatter cut it
into single digits (`numberToDigitsCutoff` default 2025, nothing sets it) and
`voice_guard.py`'s tail pad added 300ms after each. Both Hebrew prompts now
carry the number in words. **Do not put a numeral phone number back into a voice
prompt.**

**DEFECT OPEN: `{{callback_number}}` is still a numeral** and will break the
same way in the debt agent's voicemail line. The value comes from
`dashboard/lib/call.ts` and four scripts under `scripts/`. Not urgent — there is
no phone number on the account, so no voicemail is reachable — but the fix is
the same: store it spoken, as `vapi_mock.py` already does for the verification
email.

**The office line is 077-6687949**, confirmed by the owner 30 Aug. Read from
`HOMIES_CALLBACK_NUMBER` where it is used, with that as the fallback, so it is
set in one place. It was already right in the live path; four scripts carried
`03-1234567` and were fixed, including `vapi_call.py`, which dials for real with
`--go`.

**`scripts/vapi_mock.py` did not compile between 18 and 30 Aug** and anyone who
tried to run it in that window got a `SyntaxError`, not a result. Fixed. Nothing
here compiles the scripts, so run `python -m py_compile scripts/*.py` before
committing one -- see CONTEXT.md.

**A prompt change is three files, all Hebrew.** `docs/assistant/demo-inbound.md`
(inbound), `docs/features/10-debt-followup/prompt.md` (debt), and the `"first"`
string in `scripts/prompt_probe.py`, which opens every probe run and is silent
when stale. Nothing under `docs/assistant/en/` is part of the job.

**Numbers are read one digit at a time on the live agents, and the fix is in
the repo but not applied.** Reported 30 Aug as "1 2 3 4 5 6, very slowly and
bugging". Both prompts told it to — a comma after every digit, which the voice
performs as a pause. Rewritten so digits run together in groups; the apartment
number, which was being spelled out as אחת שתיים, is a word again. Goes live
with the same two `--apply` commands below.

**Do not "fix" this by raising `formatPlan.numberToDigitsCutoff`.** It is unset
on all four assistants, so they run Vapi's default of 2025, and yes that means
Vapi splits any bare number above 2025 into digits itself. Raising it makes
Vapi speak the number as **English words** inside a Hebrew sentence, which is
worse. The reasoning is written beside the field in `scripts/voice_guard.py`.

**The repo is one line ahead of live Vapi, and nothing has been applied.**
All four assistants introduce themselves the client's way as of 30 Aug —
Hebrew `שלום, מדבר מיכאל מהצוות של הומיז`, English "this is Michael from
the Homies team" — **in the files only**. The live assistants still say the old
line. Both dry runs are clean (inbound 35,622 chars, debt 53,617, first messages
extracting, both English twins passing parity). To push:

    python scripts/vapi_sync.py inbound --apply
    python scripts/vapi_sync.py debt --apply

Read the `vapi_sync.py` warnings in `CONTEXT.md` before running either —
`tool_server()` prefers n8n whenever `N8N_BASE_URL` is set. The English twins go
with `vapi_en.py <twin> --update <id>`; they are comparison instruments and
nobody outside this project hears them.

**The debt opening lost `שמנהלת את הבניין` with the rewording** — the clause
that told a cold-called resident why we have their number. Deliberate, the
client's phrasing. If attempts start ending in `מי זה?` or hang-ups inside two
turns, look here first; `docs/features/10-debt-followup/prompt.md` carries the
way back.

---

## What works, and what does not exist

| Works today | |
|---|---|
| Outbound debt collection, voice (Hebrew) | web calls only |
| Inbound intake → ticket, voice (Hebrew + English twin) | web calls only |
| Debt call → ticket on request, and a disputed payment routed | since 18 Aug; both twins |
| Balance check | voice + WhatsApp; on WhatsApp it costs a full name **and** a phone number |
| WhatsApp bot: open a ticket, check a ticket | one Meta test number, Hebrew only; go-live runbook in `docs/handover/meta-anydesk-session.md` |
| Address verification | the bot refuses a building Homies does not manage, and a flat that does not exist in it |
| General questions (hours, phone, address, what ועד בית covers, payment, response times) | answered from the prompt since 18 Aug; source in `docs/reference/homies-faq.txt` |
| Off-topic questions | politely declined, never escalated, since 18 Aug |
| Ticket numbers in Homies' own format | `255-NNNN-YY` since 18 Aug; the old `HM-YYYY-NNNN` still resolves |
| Dashboard | live; 10/25/50 rows a page, chosen in the URL |
| OXS → Supabase import | works; twice daily on GitHub Actions, first complete pass 24 Aug (~28 min), watched at `/sync` |

**Does not exist:**

- **A real phone number.** No `phoneNumberId` on the Vapi account. Needs the
  four Omnitelecom values — gateway host/IP, SIP username, SIP password, DID
  in +972 E.164 — and Homies' company registration documents, which are the
  long pole. Ask whether the trunk runs over the public internet before
  paying; a dedicated line cannot reach Vapi.
- **Payment link delivery.** `send_payment_link` writes a row and stops. OXS
  exposes no payment-link endpoint, so the link still comes from OXS itself.
- **Chatwoot hardening, and the seats.** Chatwoot is live in the path (see
  above) but three things are unfinished. **SMTP is unset** --
  `MAILER_SENDER_EMAIL` and `SMTP_ADDRESS` are absent, not blank -- so nobody
  can be invited and nobody can recover an account; the Rails console is the
  only door, which means losing root on the VPS means losing Chatwoot. **The 19
  seats and the routing rules** do not exist: teams 1-4 (Collections,
  Operations, Management, Service) are created and empty, and nothing routes to
  them automatically. **The webhook secret is a query-string shared secret**,
  not a verified signature: Chatwoot does send `X-Chatwoot-Signature`
  (HMAC-SHA256 over `${timestamp}.${body}`) but n8n cannot check it --
  `require('crypto')` is blocked in the task-runner sandbox. The account is
  named `CLIX`, not Homies.

  **The number is Meta's test number and is meant to be replaced.** A swap
  changes the inbox's `phone_number` and `provider_config` and the callback URL
  (Chatwoot puts the number *in* the path), and touches n8n not at all -- the
  cutover removed the last place n8n named the number. **Creating or editing a
  WhatsApp inbox in Chatwoot repoints the number by itself**, via a
  per-phone-number `webhook_configuration` override that beats the app-level
  subscription. Do the n8n side first. Check with
  `GET /{phone-number-id}?fields=webhook_configuration`, never
  `GET /{app-id}/subscriptions`, which lies.

- **A completed run on the schedule itself.** The full pass on 24 Aug was
  dispatched by hand and finished in 27m41s; the `decide` job that decides
  whether a cron is the live one or its daylight-saving twin has been exercised
  only on the manual path, where it always says go. The first scheduled proof is
  15:00 Israel that day. Every import other than these three is still run by
  hand.
- **A campaign runner.** Nothing has ever iterated the queue. **A runner reads
  `v_debt_call_queue_person`, never `v_debt_call_queue`.** The person view is
  one row per resident and IS the grouping decision, made 11 Aug: one call
  covers every apartment they owe on. The charge view underneath is one row per
  apartment per month — an owner with two flats owing four months is eight rows
  there, and a runner iterating it places eight calls. Pass the whole person
  row as `variableValues`, `charges` included: the tools resolve apartment
  writes against that whitelist.

**Changed 18 Aug — the call no longer hangs up on people, and the verification
email is real.**

- **The resident ends the call, not the agent.** Four rules, all from real calls
  on 18 Aug: a **"no" with a sentence after it is not a no** (wait for a turn
  that stops); **never say why you are ending** (absolute rule 14 — *"since you
  don't want to pay this, I'll leave it there"* was said to a resident); a
  refusal is never a reason for anything you say next; and the closing is the
  same words whatever happened in the call.
- **Withholding payment because something is broken has its own path.** The
  commonest reason a resident in a managed building stops paying, and the prompt
  had nothing for it. Say the broken thing back in their words, then
  `transfer_to_human` reason `dispute`. **Do not explain what the fee covers
  here** — in that position it argues for paying for something that does not work.
- **Already reported → do not file a second ticket.** The debt agent has
  `open_request` but not `get_request_status`, so it cannot see an existing one.
  Two rows for one broken lift tells the office nothing.
- **The closing is a handshake, not a decision.** business → their answer →
  *"anything else?"* **alone in its turn** → their answer → the closing **alone in
  its turn**. Absolute rules **12 and 13**, in the section the fixed paths do not
  override. `endCallPhrases` carries "have a good day" and
  `endCallFunctionEnabled` is **false**, so the phrase **is** the only way a call
  ends — there is no turn after it and a premature close cannot be recovered
  from. A reply that is not a yes or no to the question is not an answer to it:
  handle it, ask again, wait again, **no limit on the rounds**. Handovers are four
  steps. The failure it comes from: the question was bolted onto the turn that
  read out the phone number, and *"can you make it slower"* got counted as an
  answer.
- **`idleTimeoutSeconds` 8 → 12 on all four assistants**, and in `vapi_en.py` and
  `vapi_sync.py`, which both hardcode it and would have reverted it on the next
  rebuild. At 8 it interrupted a resident's thinking pause — the same pause the
  handshake now depends on.
- **`Office@homies-management.co.il`** — confirmed from the client's FAQ. The
  demo page had been reading out `office@homies.co.il`, which does not exist, and
  a test call asked a resident to send payment proof to it. Fixed in
  `web/index.html` (Hebrew spoken form **with the hyphen**, and English),
  `debt-followup.md` and `voice_guard.py`. **`web/` is unpushed** — the deployed
  page still reads the wrong address until `cd web && git push`.
- **An apartment that is not on this call** is handled separately now. "Apartment
  twelve, not seven" is not a dispute, it is the call having the wrong flat — ask
  once whether the call's apartment is theirs, and if not, `transfer_to_human`
  with reason `ownership`.

**Open, from the same calls:** the agent said *"Reason. Dispute. Friction."*
aloud — a tool argument spoken as a sentence. Absolute rule 10 now names it, but
it is a prompt rule against a generation habit, so watch for it. And the TTS says
**"HOMEies"** for Homies, on the first word of every call.

**THE LIVE VAPI ACCOUNT CHANGED TWICE ON 19 AUG. Read this before touching
anything that dials.** The second move, in the afternoon, was to a fresh account
— the one below. **A new account starts with no provider credentials**, so the
Cartesia key had to be created on it by hand before the Hebrew agents had a
voice; `--mirror` does not carry credentials, only assistants. Check
`GET /credential` on any new target before believing a migration is complete.

**The first move, that morning:** The account live since 12 Aug — "account 5" — went **$0.11
overdrawn**, and Vapi refuses a web call *before* it creates one, so every
attempt failed with no call record on either side and nothing in the history to
find. **Account 4 is now the live one.** Its four assistants had been mirrored an
hour earlier and were byte-identical, so nothing was copied: 19 ids across 11
files plus the public key were repointed, and `.env` swapped.

**Superseded 30 Aug — the August account is live.** The table below is kept
because the ids in its *retired* column are what you grep for when something
still misbehaves. Current ids, and the full account of the move, are in
`docs/handover/new-vapi.md` under **30 Aug**.

| | now live (30 Aug) | retired |
|---|---|---|
| Keys | `VAPI_PRIVATE_KEY` / `VAPI_PUBLIC_KEY` (the August account, live 30 Aug) | `VAPI_*_KEY_ACCOUNT6` (live 19–30 Aug), `_ACCOUNT7` (the old account 4), `_ACCOUNT5` |
| Debt (he) | `93c7f5e5-4024-49a3-9ab6-141f2b423649` | `8f927b15-…`, `9e2034d1-…`, `489aa39c-…` |
| Debt (en) | `72de8d5c-12c7-4e6c-a2db-27b16d41066a` | `cc8e43b4-…`, `41d370b2-…`, `3b0e384d-…` |
| Intake (he) | `7752c6bb-89e9-49f3-aaf4-154ecc65cdff` | `12a4c01d-…`, `f482abc1-…`, `7813da25-…` |
| Intake (en) | `713874a1-5e3c-4c47-b0e8-7e4e75c1e83b` | `9cae6bf7-…`, `8b98016b-…`, `9ed5e788-…` |
| Cartesia credential | `448aa856-75ef-4209-9f0c-b795be6529dc` | `6b3954f6-…`, `52e0bca2-…` |
| Org | `c9c2b782-6419-4d2f-ad74-cc72ba4ff65c` | `4cedeed3-…` |

**The demo is deployed and the dashboard has nothing to deploy.** Both Vercel
projects were read on 30 Aug with `VERCEL_API`:

| Project | Domain | Vapi vars |
|---|---|---|
| `homies-voice-demo` | `homies-voice-demo.vercel.app` | none — the keys are in the page |
| `homies-dashboard` | `homies-dashboard.vercel.app` | **none**, and `hiddenProductionEnvCount` is 0 |

`homies-voice-demo` auto-deploys from `TheSuperShyy/homies-voice-demo` and is
serving the August account: public key `36afb64b`, all four new ids, no trace of
the old ones.

**Correction to what this file said earlier: the dashboard's Call button was
never going to bill the old account, because it is switched off in production.**
`callingEnabled()` needs `CALL_PIN` and the call itself needs `VAPI_PRIVATE_KEY`
and `VAPI_PHONE_NUMBER_ID`; the project holds none of the three, so the column
does not render. Outbound cannot work from Vercel until there is a phone number
anyway ([[homies-no-phone-numbers]]). The constant in `dashboard/lib/call.ts`
was still worth fixing — it is the fallback that takes over the day
`VAPI_DEBT_ASSISTANT_ID` is set and is wrong.

**Still open: nobody has placed a call** on the August account in either
language, so the Cartesia voice is verified by its id and not yet by ear.

**Two Vercel tokens are in `.env` and only one works.** `VERCEL_TOKEN` returns
403 `invalidToken`; `VERCEL_API` authenticates as `thesupershyy`. Use
`VERCEL_API`, and treat `VERCEL_TOKEN` as dead rather than as a second try.

Account 5's balance is **unknown**, and the earlier claim here that it was back
in credit was wrong. `VAPI_PUBLIC_KEY_ACCOUNT5` in `.env` does not hold account
5's public key — a promote overwrote it (see below) — so that check was reading
the live account twice and reporting its balance under another name. The private
key is correct; the public one has to come from account 5's own dashboard before
its balance can be read at all.

**Retired public keys in `.env` are not trustworthy.** `repoint()` rewrote every
occurrence of the outgoing public key across every file, `.env` included, so each
`VAPI_PUBLIC_KEY_ACCOUNT<n>` was overwritten with the incoming key by the very
step meant to preserve it — and `.env` is gitignored, so there is nothing to
recover them from. **Fixed 19 Aug** (`skip_in_env`: keys are `swap_env()`'s
territory, ids still move), but the values already lost stay lost. Every retired
**private** key is intact. Take a retired public key from that account's
dashboard, Organization → API Keys. **Call history, transcripts and recordings did not
move and cannot**; everything before 19 Aug 12:00 lives on account 5, and Vapi
deletes recordings after 14 days.

**THE CARTESIA KEY LIVES IN VAPI, NOT IN `.env`.** Changed 19 Aug. It is a Vapi
provider credential — "Cartesia (Hebrew TTS)", `4c9be89b-f62e-42e7-bd2d-35faf51e0969`
— and that is the copy that pays for Hebrew speech. `.env` feeds only the three
local scripts (`cartesia_tts.py`, `voice_clone.py`, `vapi_transfer.py`); no n8n
workflow touches it. **Editing `.env` alone leaves the old account billing while
everything looks migrated.** Update both:
`PATCH /credential/{id}` with `{provider, apiKey, name}`. Vapi never reads the
value back, so the only proof is a Hebrew call. Superseded keys are kept as
`CARTESIA_API_KEY_ACCOUNT<n>`.

**The Hebrew voice cannot be lost in a move.** `a976c076-3e31-4bf2-a178-8c3ce3d52b2a`
— *Eyal - Grounded Guide* — is a **public** Cartesia voice, so it belongs to no
account. And a voice listing's `owner_id` is the **voice's** owner, never the
caller's: all three of our keys report `org_3AOx…` because that is who published
the first public voice in the list. It looks like an account identifier and is
not one.

**Cartesia has no balance endpoint, and it is in the live Hebrew path.**
`/usage`, `/balance`, `/account`, `/credits` are all 404 and a successful call
returns no quota headers — checked 19 Aug. Both keys in `.env`
(`CARTESIA_API_KEY`, `CARTESIA_MAIN_API_KEY`) are valid and belong to the **same
org**, so they are two keys on one balance rather than two accounts. **Vapi holds
this key as a provider credential** ("Cartesia (Hebrew TTS)", added 11 Aug), which
means Hebrew speech bills to *our* Cartesia org and not through Vapi — a Vapi
balance in credit says nothing about whether the Hebrew agent can speak. The only
way to read what is left is the Cartesia dashboard. The English twins use Vapi's
own Elliot voice and are unaffected.

**Do not spend another hour looking for it.** Swept 19 Aug against both keys and
both API versions: `/usage`, `/balance`, `/account`, `/credits`, `/billing`,
`/subscription`, `/quota`, `/org`, `/v1/*` and a dozen more are all 404, and a
successful call carries no quota, credit or rate headers. Two endpoints answer at
all — `/status`, which is a public health check, and **`/api-keys`, which returns
401 "you must be logged in"**. That is the shape of the whole thing: Cartesia's
account surface is behind a dashboard *session*, and an API key is not one.

**And the Vapi wallet trick does not port.** It works there because Vapi checks
the wallet *before* it validates the request. Cartesia validates first — an empty
transcript and a nonexistent voice id both come back as plain 400s — so a
deliberately unsynthesisable request tells you nothing about credit. The only
signal an API key can give is *"this key still authenticates"*, which catches a
revoked key and never an empty balance. Anything stronger is a real synthesis,
which bills.

**Check the balance before a test session, not after.**
`python scripts/vapi_transfer.py --balance` — exit 0 in credit, exit 1 blocked.
It was thought impossible until 19 Aug: `GET /org` is 401 to a private key and
the public key reads nothing. But **Vapi checks the wallet before it looks the
assistant up**, so a POST to `/call/web` naming a correctly-shaped uuid that
belongs to nobody returns the wallet message when overdrawn and *assistant not
found* when not. Nothing is created either way, so it is free.

**New 18 Aug — moving Vapi accounts is one script.**
`scripts/vapi_transfer.py --preflight` shows what is here and what a move needs;
`--to <ENV_VAR> --dry` shows the plan; `--apply` does it. It creates the Cartesia
credential, copies all four assistants verbatim, and rewrites **17 hardcoded ids
across 10 files** — the step that has broken every previous move, because a wrong
assistant id does not error, it just calls the wrong agent.

- **Blocker 1 of `new-vapi.md` is solved.** Cartesia was said not to travel, and
  its absence is silent — the Hebrew voice falls back to `vapi/Elliot` and only a
  Hebrew speaker notices. `CARTESIA_API_KEY` is in `.env`, so the credential is
  created; the script stops if it is missing.
- **It copies, it does not rebuild.** A rebuild gives what the repo says should
  be live; a copy gives what **is** live. Rebuild deliberately afterwards.
- **`--to` names the variable in `.env`, never the key** — shell history, public
  repo. It refuses a target that already holds Homies assistants, and refuses to
  clone onto itself.
- **The public key is the one manual step.** `GET /org` is 401 to a private key.
  It goes in `.env` and `web/index.html` by hand, and without it the demo page
  loads and no call ever starts.

**Two more verbs, added 19 Aug, and they are not the same as `--apply`.**

- **`--mirror`** keeps a second account in step: matches by name, overwrites in
  place so no id moves, creates only what is missing, and **does not touch the
  repo**. Anything on the target that is not ours is not read, not written and
  not counted. This is what made the promotion below cost nothing.
- **`--promote`** makes a mirror the live one. Creates nothing, copies nothing —
  repoints every id in the repo at the twin already there, carries the **public
  key** along in the same rewrite (it is not an assistant id, and with the wrong
  one the page loads, looks perfect, and every call is rejected), and swaps the
  `.env` pair while keeping the outgoing one under its account number. It
  **refuses a target that cannot place a call**, because promoting onto a second
  overdrawn account leaves everything repointed and the same invisible symptom.

`--apply` still refuses a target that already holds Homies assistants; that
refusal is right, and `--mirror` / `--promote` are what to reach for instead.

**Refreshed 18 Aug — the Vapi export.** `scripts/vapi_export.py` is the backup,
and it now redacts by **value** rather than by field name: every
credential-shaped entry in `.env` is replaced wherever it appears, and the write
is refused if one survives. `--check` re-scans every export on disk, `--archive
<label>` writes the dated copy in the same run. Plain URLs and bare uuids are
deliberately left alone — `SUPABASE_URL` is public and ships in the dashboard
bundle, and a check that flags harmless things is a check nobody reads. The
`@`-free URL test is what keeps `SUPABASE_DB_URL`, which carries the database
password, on the secret side. Current: `docs/handover/vapi-export.json` plus
`vapi-export-account5-18aug.json`, 5 assistants, 1 credential, all clean.

**It is a record, not a restore path.** Vapi mints new ids on create, and pushing
a whole assistant object back is how tools get replaced by a stale list. The
rebuild is `docs/handover/new-vapi.md`.

**Changed 18 Aug — a standing order opens a ticket.** `request_standing_order`
used to write one `call_outcomes` row and nothing else; the Calls page has five
tabs and none of them filters on `standing_order_requested` or
`office_to_contact`, so the request reached nobody. It now writes the flag **and**
a `requests` row, marked `oxs_ref = 'standing_order'`, type `other`. One open
ticket per resident with **no** time window — asked again next month is the same
unmet request, not a new one — and a repeat hands back the existing reference.
The prompt says the one tool does all of it and must never be paired with
`open_request`, or one arrangement becomes two people to ring. Edge Function v21.

**Changed 18 Aug — the debt agent answers questions instead of handing them
over, and it now has facts to answer from.** From a real English call in which it
reached for the office twice on questions it could have answered, never returned
to the payment, closed on the resident's "no", and **invented what the fee
covers** — "lighting" and "plumbing", neither of which is on Homies' list.

- **Three rungs, and it never jumps to the third.** Answer it → if you cannot,
  offer to open a request → only then the office. `transfer_to_human` is for what
  a request cannot carry, or when they ask for a person.
- **The voice agents now carry the facts.** Until today neither had the FAQ or
  even the office number, so every general question was answered from nothing.
  `WHAT YOU ACTUALLY KNOW ABOUT HOMIES` is in the debt prompt, with the same four
  rules as the chatbot: quote contacts exactly, answer rather than recite, service
  levels are policy never a promise, never adjudicate responsibility.
  **`docs/reference/homies-faq.txt` is now the source for three deployments** —
  the chatbot prompt, the debt prompt, and nothing reads the file itself.
- **The answer and the ask are one turn**, because there is no later turn.
- **The close asks whether there is anything else**, and an unsettled payment
  goes back on the table once — except on a handover, where the rule against
  offering the link on the way out still holds.
- Hebrew 53,569 chars, English twin 52,121, 57 passages + 4 blocks, 7 tools each.

**Still missing on the intake agent:** it has no facts either. Same gap, not yet
closed.

**Changed 18 Aug — the debt agent opens tickets, and a disputed payment has
somewhere to go.** Both were asked for and both are live on the Hebrew and
English twins.

- **A request opened on request.** `open_request` was taught for one case, a
  maintenance issue raised mid-call. It now also covers a resident asking
  outright and a resident accepting the offer of one. The tool *description* was
  widened too, not only the prompt — that string is what the model reads when it
  decides whether the tool applies.
- **"I already paid" is now six steps, not four.** Offer the link once, as an
  option. If they refuse: understand it, say once that our side still shows it
  open, and give them the two real choices — a request with a number they can
  quote, or the office. **This reverses "do not offer the link"** on instruction;
  what survives is no arguing, no repeating the amount, and never a second offer.
- **The dispute is logged whichever they pick, including neither.**
  `log_disputed_payment` sets the charge to `disputed`, which is what the debts
  dashboard shows and what stops them being chased next month. A ticket is
  something the resident holds; it never replaces the log.
- **Never push these with `vapi_sync.py`.** The live tool objects carry a
  `server` block (webhook + secret) that `vapi_tools.py` does not, so replacing
  `model.tools` from the repo strips all seven and every tool call goes nowhere.
  Edit the fetched objects in place and PATCH the whole `model`.

**Changed 18 Aug — the voice agents speak the new reference, and the English
intake twin is current.** The Hebrew intake prompt was pushed prompt-only (23,583
chars, three tools verified intact) and the English twin rebuilt from it
(`vapi_en.py intake --update`). Testable now on
homies-voice-demo.vercel.app — the deployed page carries the **live account-6
ids** (all four, verified against the served HTML on 25 Aug), so a web call
there reaches the assistants the repo syncs. **`vapi_en.py intake
--dry` is the health check**; it exits loudly whenever a Hebrew fixed line
changes, and the fix is always the table, never the check.

**Changed 20 Aug — the opening turn.** A caller who asks for a request without
saying why now gets one question, *בטח. מה קרה?* / "Of course. What's happened?",
and nothing else in that turn: not the building, not sympathy, not the choice
between a request and the office. The two-way offer and the "I'm sorry to hear
that" line each carry an explicit gate now, because neither had one and both
fired on the first sentence of a call. Both twins verified live against the API
after the push.

**Changed 18 Aug — ticket numbers are Homies' format.** New tickets are minted
`255-NNNN-YY` (migration 020), the shape every call in OXS already carries: their
code for Homies, our serial, the year in two digits. First one was `255-1047-26`.

- **Our serial is four digits and theirs is five, deliberately.**
  `requests.reference` is unique and `oxs_requests_sync.py` upserts on it, so a
  number of ours that ever collided with their counter would let their call
  overwrite our row. We cannot reserve one — their API is twelve GETs — so we
  mint below a counter that only climbs. A check constraint enforces the band.
- **Both shapes resolve.** Tickets before 18 Aug keep `HM-YYYY-NNNN` and
  residents still hold those numbers. `serialOf()` in the Edge Function reads the
  serial out of either — middle of a three-number reference, tail of a lettered
  one — and looks up on that. Verified live against both, plus bare digits and an
  imported `255-26277-26`.
- **The read-back rule is about the middle now, not the end.** Quoting the last
  part of `255-1047-26` gives a resident the year. The chat prompt names the new
  truncations (`1047`, `255-1047`, `1047-26`) rather than saying "exactly".
- **The voice prompt is fixed on disk and NOT pushed.** `demo-inbound.md` said
  read out only the last part; under the new shape that is *2, 6*. Corrected in
  the file, left unpushed under the chatbot-first instruction — voice takes no
  real calls, so it is a demo break, not a resident-facing one. Push it with the
  prompt-only PATCH described in `CONTEXT.md`, never `vapi_sync.py`.

**Changed 18 Aug — the chatbot has facts, a register and a fence.** The system
prompt is **26,718 chars**; `scripts/n8n_whatsapp.py --apply` is the only way it
reaches n8n, and every deploy should be read back from the running workflow
rather than assumed.

- **It answers general questions.** Hours, phone, address, email, what ועד בית
  covers and excludes, payment terms and methods, how to reach the committee,
  service levels, and where responsibility sits. Source recorded verbatim in
  `docs/reference/homies-faq.txt` — **that file is not read by anything**; the
  facts live in the prompt, and changing one without the other changes nothing
  a resident hears. Since 18 Aug it is the source for **two** prompts — here and
  the debt agent — so a fact that changes has to be edited in three places and
  deployed twice.
- **Service levels are policy, never a promise.** "Emergencies within 4 hours,
  otherwise 3 business days" may be quoted. "Yours will be done tomorrow" is
  still forbidden, and is *more* likely now that numbers exist to reach for.
- **A missing fact is answered, not escalated** — see `CONTEXT.md`. It says it
  does not have the detail and gives the office phone and email.
- **Off-topic is declined politely and never escalated** — see `CONTEXT.md`.
- **The register has a floor as well as a ceiling.** Not clerical, not street; a
  three-column band with `וואלה`/`סבבה`/`תכל'ס` borderline under one rule —
  never lead with slang, match a resident down at most one step. Flash's
  translationese tells are named (`בנוסף`, `כמו כן`, `לפיכך`, `על מנת`) because
  a bare prohibition leaves it reaching for its own last message.
- **Never gender the resident, and `לך` is the word that breaks it** — written
  identically for both, said two ways. Delete it rather than choose.

Tested from a handset on 18 Aug: the register held, and the two bugs it found
(`לך`, and claiming Homies has no website) are fixed. Test sheet:
https://claude.ai/code/artifact/78182277-486e-4b23-8b28-59ee5e616619

**Changed 13 Aug — the bot offers to open a ticket instead of interrogating.**
A reported fault gets *acknowledge → offer, saying where it goes → then, after
yes, building and apartment*. This **reverses the 8 Aug "never ask permission"
rule**, deliberately: that rule came from voice, where a turn costs seconds of
a live call, and on chat turns are cheap while tone is not. Two cases still
skip the offer — a resident who asked outright ("open a ticket", "send
someone"), and anyone in danger, who is transferred immediately with no ticket.
The `open` menu row now asks only *"ok. what's the fault?"*, since tapping it
is itself the request.

**Changed 13 Aug — a ticket now records who reported it, not just where the
fault is.** The bot asks for building **and** apartment on every report,
including a lobby leak, because it is asking *who is this* — chat has no caller
ID and nothing ever looked the sender up, so a WhatsApp ticket carried no
resident at all. This is **not** a reversal of the lift rule: `requests.unit`
still means where the fault is and stays NULL for common property;
`requests.reported_unit` (migration 018) is where the person lives.
`resident_id` is filled from the same verified pair, best-effort — a flat with
no phone on file has no `residents` row.

The model sends `reporter_unit` + `fault_location` (`apartment`/`common`) and
the server derives `unit`; `unit` is no longer offered to the model. Anything
not literally `"apartment"` counts as common, because a fault wrongly filed as
common gets read by a person and one wrongly pinned to a flat sends a
technician to a stranger's door. Voice is untouched — no `reporter_unit` on a
voice call means no change to `unit`.

**Changed 13 Aug — an address is checked against a real list before a ticket
is filed.** `buildings` and `apartments` are new (migration 016), mirrors of
OXS's own: **173 active buildings and 4,092 apartments**, refreshed by
`scripts/oxs_buildings_sync.py`. Before this there was nothing to verify an
answer against, so a resident naming a street Homies does not manage got a real
reference number and believed a technician was coming.

**Street + number is unique across the whole portfolio** — no duplicate
addresses, no street+number in two cities. `הרצל 14` identifies a building on
its own, so **the agent never asks which city.** The sync re-checks that every
run and refuses to write if it stops holding, because the matcher leans on it.

`verify_address` is the new read-only tool; the bot calls it before
`open_request`. It answers found / street unknown / street real but not that
number / no number given / ambiguous, and returns the flat range so a refusal
can be useful — "that building has apartments 1 to 25" rather than "not found".
Matching compares the resident's whole sentence against the list instead of
parsing it into street and number; 173/173 addresses resolve in three phrasings.
Ambiguity is returned for the bot to ask about, never resolved.

**An apartment "number" is often not a number.** 138 of the 4,092 are labels —
חנות, מסחר 2, מחסן, חניה 43, דירת ועד — and they are **not unique within a
building**: זבולון 17 has two units both called חנות. Migration 016 assumed
otherwise, its unique constraint rejected that building on the first real
import, and 017 drops it (`id` is the OXS id and already the primary key, so
nothing was lost). The flat range the bot reads out is computed from the
numeric flats only, or it says "apartments 1 to חנות".

`open_request` **normalises but does not refuse**: it files against the
canonical address when one resolves, and files anyway when none does. It is
shared with both voice agents and only the chat bot verifies first, so
rejecting would silently drop inbound voice tickets. It also fixes the
duplicate guard, which matches `building` as a string — `יואב 14` and
`רחוב יואב 14 רמת גן` were two buildings to it and one to everyone else.

**Changed 13 Aug — a balance on WhatsApp now needs proof of who is asking.**
Client security feedback. `get_balance` used to identify a chat caller by the
WhatsApp number the message arrived from, then by building+apartment, then by a
name — and the bottom two are things a neighbour knows, so anyone who found the
number could type a name and be read a stranger's debt. On chat it is now one
rule with no fallbacks: **a full name and a phone number, both typed by the
resident, both landing on the same `residents` row.** The envelope number is
not a shortcut past the question.

The refusal is in the **Edge Function**, not the prompt — a prompt rule is a
request and this one guards money. Missing either half returns `need_identity`;
a mismatched pair returns `identity_failed`, which deliberately does not say
*which* half was wrong (a per-half answer is an oracle). Two failures, or a
refusal to identify, go to `transfer_to_human`.

**Voice is untouched and carries the same hole.** The inbound agent calls the
same `get_balance` and still identifies by building+apartment or by name; the
gate is scoped to `channel(ctx) === "whatsapp"` because the standing
instruction is to leave those fallbacks alone. Inbound voice identity is open.

**Not deployed.** The Edge Function needs pushing and the n8n workflow needs
re-syncing before any of this is live.

**Changed 13 Aug, and the first thing to look for in a transcript.** The first
message names the desk and makes an open offer — `היי, כאן שירות הלקוחות של
הומיז. במה אפשר לעזור?` — rather than asking what broke, because plenty of
people write in about a balance or a ticket status. It is first-message-only.
**That greeting exists twice** — in the prompt, and hardcoded as the `MENU` body
in `scripts/n8n_whatsapp.py`, because a bare `היי` short-circuits before the
model and is answered by the workflow. They drifted on 13 Aug and a real handset
found it. `check_greeting()` now fails the deploy if they stop matching. Any
reply carrying the `אפשרויות` list button came from the workflow, not the model.
The bot then **offers** to open a ticket before asking anything, and asks for the building
and apartment only after the yes.

**The order is fixed and it is what → whether → where (25 Aug).** An intention
is not a description: `אני רוצה לדווח`, `יש לי בעיה`, `אני רוצה להתלונן` say
what somebody wants done and nothing about what happened, so there is nothing
to offer on and nothing to open. The bot asks first, and asks by opening a door
rather than demanding a datum — `בטח. אפשר לספר לי מה קרה?`, echoing whatever
word they used, never a bare `מה הבעיה?`. Sympathy still waits for the
description (being sorry about an unknown is the most machine-like line
available); before it, the bot receives the person — `בטח`, `אני מבין`,
`אני מקשיב`. A description is never invented and neither is `fault_location`.
Voice keeps its own shorter form of the same order and was not touched. Warmth is now explicitly confined to the
sentence and never the fact — see the rule in `CONTEXT.md` — so refusals, the
reference-number handover and a failed identity check are all phrased like a
person while the checks behind them are unchanged. Ungendered second person
throughout: `גרים`, never `אתה גר`. Deployed and **not yet tested on a real
handset.**

**Changed 12 Aug, and worth knowing before you read a transcript:**

- **The WhatsApp bot is מיכאל again, since 24 Aug** — nameless from 12 to 24
  Aug, and the builder's verdict on that was "sounds AI". Opener:
  `היי, כאן מיכאל מהומיז. במה אפשר לעזור?`, in both the prompt and the menu the
  workflow sends to a bare `היי`, and `check_greeting()` asserts they match.
  No `היי!`, no smiley, no `היום`, never reports its own mood. Voice and chat
  share the name now.
- **Tickets about nothing were possible until 25 Aug.** `אני רוצה לדווח על
  משהו` → `רוצה שאפתח על זה קריאה?` → yes → address wrote a real ticket with
  `description: "דיווח על משהו"` and an invented `fault_location: apartment`.
  Cause was one prompt bullet listing `אני רוצה לדווח` among "they already
  asked outright, go straight to building and apartment". Fixed, live, and
  re-probed; the bullet now needs a request **and** an account.
- **No em dash reaches a resident, and it is enforced in three places
  (25 Aug).** The prompt forbids it and no longer contains one outside the rule
  that names it; the per-message instruction, which the model sees beside every
  turn, was rewritten to colons and full stops; and the `Send` node strips
  `—` and `–` to a comma on the way out, so a canned line or a model slip
  cannot carry one. Reference numbers use ASCII hyphens and are untouched by
  the strip, which was tested rather than assumed.
- **Voice: a bot line in `artifact.messages` is a TRANSCRIPTION, not what was
  said (25 Aug).** Vapi transcribes the assistant's own audio to build the
  transcript, so the stored bot text is a recognition of Hebrew speech and
  drops or mangles words. Proof: the model emitted `דירה שתים עשרה` and
  `ארבע מאות וחמישים שקלים`; the transcript stores `דירה 12` and `450` -- only
  a recogniser turns words into digits. So `מחבר` for `מחברת הומיז`, and
  `תם יוף ובפקל של מיוף`, are recogniser output, **not** the model, and not
  necessarily what a caller heard. The honest record is `Voice cached` and the
  `Model output` events in the call log. Do not diagnose voice behaviour from
  the dashboard transcript. (An earlier note here blamed an acoustic echo from
  laptop speakers; wrong -- testing was on headphones and by typing, and this
  is normal Vapi behaviour.)
- **Voice: the Hebrew debt prompt is written in Hebrew (25 Aug).** 52,586
  chars, 68% Hebrew; the rest is tool names, codes and variables. Source is
  still `docs/features/10-debt-followup/prompt.md`, and `vapi_sync.py debt
  --apply` still pushes it. **The English twin no longer derives from it** --
  `vapi_en.py` reads `docs/assistant/en/debt.en.md`, frozen from the last
  substitution build. **Do not keep them in step.** Owner's direction,
  30 Aug: work the Hebrew, leave the English alone -- the two operate
  differently, so a change reasoned out for Hebrew is not an English
  change waiting to be translated. Nothing forces it either: `englished()`
  short-circuits to the frozen file, so the substitution table in
  `vapi_en.py` has not run since 25 Aug and refuses nothing, whatever its
  comments claim. `parity()` checks structure, not wording, and keeps
  passing while the two drift in words. Updating a twin is its own
  request.
  **Intake (he) followed on 26 Aug** -- 33,948 chars, 70% Hebrew, source
  `docs/assistant/demo-inbound.md`, pushed with `vapi_sync.py inbound --apply`,
  and its English twin frozen at `docs/assistant/en/intake.en.md` the same way.
  Both Hebrew agents are now instructed in Hebrew. The debt agent has since been
  heard by the owner and reported clean -- no cut-off, and it holds a turn like
  a person; **the intake agent has not been called since its rewrite**.
  `vapi_en.py <twin> --dry` now prints a parity report against the Hebrew twin
  and refuses to write a drifted one; both pairs pass.
- **WhatsApp: the status button answers warmly and explains itself (26 Aug).**
  `בטח, אשמח לבדוק בשבילך. יש לך את מספר הקריאה?` replaces `בטח. מה מספר
  הקריאה?`, and a resident who answers "which number?" is now told what it is
  and offered building-and-apartment instead. Three copies edited together:
  `TAP_LINE`, the live `Sort` node's `TAPPED`, and the prompt's status section.
  The other button, `בטח. אפשר לספר לי מה קרה?`, has the same clipped shape and
  was left.
- **WhatsApp: "אין לי" no longer resets the conversation (26 Aug).** A resident
  who tapped the status button, was asked for a number and answered `אין לי` got
  `אני מבין. על מה אפשר לעזור?` back (execution 9798). They had answered; the
  bot started over. The prompt already routed a numberless resident to building
  and apartment but never said that `אין לי` IS that case. Now it does:
  `אין בעיה, נמצא את זה גם ככה. באיזה בניין ואיזו דירה?` An open question after
  an answer is named as losing the thread, and `על מה אפשר לעזור?` is named as
  not Hebrew.
- **The OXS ticket mirror is BUILT, VERIFIED, and OFF — owner's order, 26 Aug
  night (function v46).** It went live without real consent (a capability
  question was read as a go-ahead, against the standing read-only rule) and
  the owner had it switched off within the hour: *"i told you not to do any
  shit to oxs."* **Off is enforced, not just configured**: a plain
  `supabase_functions.py --apply` DELETES the function-side `OXS_KEY_REQUESTS`
  on every deploy, and only an explicit `--oxs-mirror` flag pushes it. Do NOT
  pass that flag without the owner saying so in terms that cannot mean
  anything else. Verified off: ticket `255-1124-26` opened with `oxs_ref:
  None` and no OXS call. The dormant machinery (oxsMirror in the Edge
  Function, the importer's reflection-skip, `requests.oxs_ref`) is correct
  and tested — one round trip ran clean in production before the shutdown —
  and MUST be re-enabled or removed together, never half. **No OXS write of
  any kind, probe included, without the owner's explicit go.**
- **Dashboard: /login renders WITHOUT the app shell** (26 Aug night, after a
  screenshot showed the sidebar wrapped around the sign-in card). The branch
  is a path test in `app/layout.tsx`; the login page carries its own brand
  (the real logo, floating with no plate, served per theme by a `<picture>`:
  `homies-logo-dark.png` — wordmark recolored white — under
  `prefers-color-scheme: dark`, transparent-original `homies-logo.png`
  otherwise) and language switch. If a new public page is ever added, it needs
  the same treatment — the layout's shell assumes a signed-in reader. **The
  favicon is the roof mark** (`dashboard/app/icon.png` 512 transparent +
  `apple-icon.png` 180 white, auto-served by Next); the source of all four
  images is `Homies-Logo.png` at the repo root — regenerate from there (the
  wordmark is dark NAVY, not black, and the source hides a faint frame line
  in its outer 8px; the recolor and crop in the worklog entry handle both),
  never edit the derived files.
- **Dashboard: image extensions are EXCLUDED from the middleware matcher, on
  purpose (26 Aug night).** The wall 307'd `/homies-logo.png` to `/login` and
  the login page showed a broken image of its own brand. The matcher now skips
  `png|jpg|jpeg|svg|webp|ico` — do not "harden" that exclusion away: public/
  assets are what pages need before a session exists, RLS guards the data, and
  anything secret does not belong in public/. Verified: logo 200, /tickets
  still 307.
- **VERCEL_TOKEN in `.env` is dead — 403 on every API call (26 Aug night).**
  Deploys are unaffected (the project is git-linked; push to main builds), and
  the login wall was verified by probing https://homies-dashboard.vercel.app
  directly: every page 307s to /login, /login answers 200. Rotate the token
  before the next scripted `vercel_deploy.py` run; until then do not trust any
  script that polls the Vercel API — it fails with 403, not with a clear
  "token expired".
- **Dashboard: the login is ENFORCED as of 26 Aug night.** Migration 026
  dropped every anon grant (the ten anon_read policies, the status dropdown's
  anon write, press_call's anon execute) and moved the status write to
  authenticated; the middleware redirect is back. Verified: anon key reads 0
  rows; the staff account signs in and reads. **One account exists:
  clixteam579@gmail.com** (password given to the owner in chat, 26 Aug); more
  are made in Supabase dashboard → Authentication → Add user — there is no
  sign-up form on purpose. Demo mode is OVER: anyone showing the dashboard
  now needs those credentials. **A second account exists for the Homies side:
  office@homies-management.co.il** (created 26 Aug night, password handed to
  the owner in chat, verified signing in). If a demo without login is ever
  wanted again,
  that is 010's pattern; do not just delete the middleware redirect — RLS is
  the boundary and the pages would show empty tables, not data. NOTE: the
  Supabase secret key refuses requests carrying a browser User-Agent
  ("Forbidden use of secret API key in browser") — send no UA from scripts.
- **Money and keys, measured 28 Aug.** OpenRouter (the WhatsApp bot's brain)
  reads **$29.13 left of $115** — `GET https://openrouter.ai/api/v1/credits`
  with the `OPENROUTER_API_KEY`, the one balance in this project an API will
  tell you as a NUMBER. **Cartesia publishes no balance** (no usage endpoint;
  `/api-keys` wants a dashboard session, not a key) — but the question that
  matters is answerable: **a two-word `/tts/bytes` synthesis returns 200 when
  the account can pay and 402 when it cannot**, which is exactly how the
  8 Aug demo outage was diagnosed. Checked 28 Aug: `CARTESIA_API_KEY`,
  `CARTESIA_MAIN_API_KEY` **and the supposedly retired `..._ACCOUNT1` all
  returned 200** — so all three keys are live and billable, and ACCOUNT1 is
  not as dead as this file said; treat it as a live key until somebody
  revokes it in the dashboard. **Vapi exposes no credit to the private key**
  either (`/subscription` 404, `/org` 401 — that one wants the public key).
- **Vapi's API 403s on Python's default User-Agent** (`error code: 1010`,
  Cloudflare, not auth). Send `User-Agent: curl/8.5.0` and the same key works
  — this is why `vapi_export.py` succeeds where a hand-rolled urllib call
  "fails". Do not report the Vapi key as dead without retrying with that
  header.
- **Voice stack, confirmed live 28 Aug:** both Hebrew assistants speak
  through **Cartesia `sonic-3`, stock voice `a976c076-3e31-4bf2-a178-8c3ce3d52b2a`**,
  credential held Vapi-side as "Cartesia (Hebrew TTS)"; both English twins are
  on Vapi's built-in Elliot. `CARTESIA_VOICE_ID` is still EMPTY — there is no
  clone, and `CARTESIA_API_KEY` is still the value exposed in chat on 7 Aug,
  still unrotated.
- **Voice: both Hebrew prompts now instruct POINTED address words at a known
  gender (26 Aug night, owner's explicit ask, NOT yet heard in a call).**
  Debt 53,635 chars / intake 35,622, live and verified. The rule: gender
  undecided → drop the ambiguous word (unchanged); gender decided → write it
  pointed (לָךְ / לְךָ, and תָּ/תְּ past in direct address); point only what
  saves a pronunciation, plus אֶת/אַתְּ, עִם/עַם, שָׁם/שֵׁם. Cartesia sonic-3
  honours nikkud — measured, two pointings of one sentence give uncorrelated
  audio; confirmation WAVs are with the owner. **Both frozen English twins are
  now officially behind their Hebrew sources** (`vapi_en.py <twin> --dry` shows
  it); updating them is by hand and still owed. Source of the requirement:
  `Spell female male prompt.pdf` at the repo root — its agent_gender, sales
  and slang sections were deliberately not taken.
- **Voice: every sentence now ends in a 300ms unspoken pause, on both Hebrew
  agents and their fallbacks (26 Aug evening, NOT yet heard).** Fix for the
  clipped-last-word report: Cartesia sonic-3 leaves 43-135ms of tail (measured
  from its own WAV output), so `voice_guard.py` PAD_RULES append
  `<break time="300ms"/>` after sentence-final punctuation, last in the shared
  formatPlan. The safe-sentence gate knows to strip the pad; both assistants
  read back 3 pad rules live. **If the clip survives, raise the constant in
  PAD (one string) before suspecting the widget's player.** The two isolation
  WAVs are in the session scratchpad; the owner has copies to judge whether
  Cartesia's own rendering also swallows the syllable — if it does, the fix is
  a different voice, not more padding.
- **Voice: the debt agent runs gpt-4.1 since 26 Aug ~18:52, owner's choice, NOT
  yet heard.** The "cut off / losing connection" report was measured as model
  latency, not network: gpt-5.2 (reasoning) spent ~3.9s of a ~5.3s turn
  thinking; `vapi_latency.py` put the two reported calls at 5,390/5,850ms
  median caller wait vs the PRD's <800ms. Swapped via one line in
  `vapi_sync.py` + `--apply`; prompt, voice, transcriber, tools unchanged.
  **First 4.1 call should be listened to for Hebrew and negotiation quality**;
  if worse, the untried cheaper move is keeping 5.2 with reasoning effort
  turned down (option offered, not taken). The English twin still runs gpt-5.4;
  intake (he) still gpt-4.1-mini and still unheard since its Hebrew rewrite.
- **WhatsApp: shipped, probed, and the prompt now treats gender as a question
  about what a reader can SEE (26 Aug, latest).** The `last_bot` fix below is
  live and verified; the entry below it is history, not a pending item. Since
  then, four more prompt pushes, **live prompt 39,968 chars**, all probed:
  - **Consecutive taps never repeat a phrasing (27 Aug, later).** The picker
    keeps the last variant per handset+button in workflow static data
    (store.lastVar) and steps past a repeat draw. Bulk replay tests flood the
    owner's real chat — keep future variant tests to code-level checks or a
    handful of taps.
  - **Every tap answers with one of THREE random phrasings since 27 Aug**,
    and since the evening they are DIRECT — no courtesy opener ("בטח, אשמח
    לעזור"), because the menu greeting already said hello; a tap answers with
    the substance. All nine live in the live `Sort`'s `TAPPED`, all end with
    the question; variants rephrase, never redirect (status always names מספר
    הקריאה, human always announces the transfer + asks the topic). `said()`
    carries the picked sentence into `last_bot`.
  - **The "לדבר עם נציג" TAP is canned since late 26 Aug — the model no
    longer sees it.** Three prompt rounds could not hold gemini-2.5-flash on
    this turn (a re-greeting with the menu glued on, then the bare fixed line
    with no question — execs 10593, 10655), so the tap joined the other two in
    the live `Sort`'s `TAPPED` with the owner's wording: `קיבלתי, אני מעביר
    אותך לצוות. כדי שמי שחוזר יגיע כבר עם ההקשר, אפשר לכתוב בכמה מילים על מה
    הפנייה?`. A `Human tap?` → `Transfer the tap` branch off the canned path
    fires the real transfer (same debt-tools webhook as the promise backstop,
    reason caller_request) so the line never promises what didn't happen.
    The resident's answer reaches the model flagged `tapped_human` (one-line
    no-question closer, context for the team, nothing else); `Dead end reply?`
    skips replies naming הצוות so that closer doesn't get the menu. Verified
    by replaying the real tap webhook: exec 10672, plain text, transfer
    `{"ok":true}`. A TYPED bare "רוצה נציג" still goes to the model and the
    transfer-section rule (confirm + handover + on-what-subject) still governs
    it. The team reads the context in the Chatwoot thread —
    `transfer_to_human` does not assign the conversation, so the bot stays on
    until a human replies. Known open rate-slip: the model writes `אליך` in
    the closer.
  - **Both tap lines are warm now.** The open button says `בטח, אשמח לעזור.
    אפשר לספר לי מה קרה?` since the evening of 26 Aug (same three-copy change
    as the status button: `TAP_LINE`, live `TAPPED`, prompt). Probed: the turn
    after the tap still routes without a re-offer.
  - **The balance opener was the last flow still ending in a full stop** —
    3/3 systematic, `אז צריך שם מלא ומספר טלפון.` with the menu appended as a
    second message. Fixed 26 Aug (the balance section now says "ואז שואל" means
    a question mark, why in the first half, what in the second); 5/5 probes end
    in the question since. Live prompt 41,454 chars. `check_whatsapp.py` all
    green the same day.
  - **Status answers open with the checking (27 Aug).** "בדקתי במערכת: הקריאה
    על המעלית פתוחה ובטיפול" — checked-first, topic in the resident's words,
    status in human Hebrew, same order for not-found. Owner's framing ask;
    examples live in the status section of prompt.md.
  - **The phantom guard keys on opening LANGUAGE, not reference shape (27
    Aug).** A reply quoting a reference (every status answer does) is no
    longer a "claim"; only פתחתי/נפתחה/פתחנו קריאה phrasing, or
    פתחתי/פתחנו beside a reference, triggers the open_request check. Before
    this, correct status replies were being replaced by rescue tickets whose
    description is the transcript (255-1130-26, purged by migration 028).
  - **get_request_status canonicalizes the building via matchBuilding (27
    Aug, debt-tools v52)** — "אבטליון 4 הרצליה" without the comma now finds
    the row — and returns `building_unrecognized: true` when the address
    resolves to nothing, so the agent says "לא זיהיתי את הכתובת" instead of
    the false "אין קריאות פתוחות".
  - **Replies pause like typing (27 Aug).** Wait nodes "Type for a moment" /
    "(menu)" hold canned lines and menus 0.5-1.7s before sending (felt ~2-3s
    with run overhead, measured); agent replies get zero added. Amounts are
    expressions on the Wait nodes, live workflow only.
  - **The requests table holds ONLY real OXS imports since migration 027** —
    every test ticket (whatsapp/voice/staff, 44 rows) is purged. A non-oxs
    row now means a real resident used the bot, or a new test began.
  - **A duplicate report's new facts land on the existing ticket (27 Aug,
    debt-tools v50).** open_request's 30-minute duplicate guard no longer
    discards the second description: it appends with " | " unless the words
    are already there. Plain `supabase_functions.py --apply` no longer aborts
    when the OXS key is already absent (404 = off, the state it enforces).
  - **A thing's name is not a fault description (27 Aug).** "תקנו את המעלית"
    no longer counts as a description: the bot asks what is happening with the
    thing before the address and before any open_request, and builds the
    description from everything told along the way (duration, prior reports).
    Curses are never echoed back. Ticket 255-1125-26 ("תקלה במעלית", no
    context) is the failure that forced it.
  - **Every reply ends with a question, and this is a standing rule the owner
    asked to be kept.** Open wherever open fits; closed only when what remains
    really is yes or no. Full stops only where the conversation ends: status
    delivered, reference number given, transfer done. **A reply with no `?` is
    sent as TWO messages** — `Dead end reply?` appends the button menu to it —
    so a doubled reply on a handset is that backstop firing, not a duplicate
    send. Probed 6 times, 5 ended in a question; flash, so it is a rate.
    **Narrowed 27 Aug: `Dead end reply?` now has THREE conditions.** A reply
    that asks for something without a question mark (contains
    באיזה/איזו/איזה/איפה/מתי/"צריך לדעת"/"אפשר ל") is mid-flow and gets NO
    menu — live 15:24 an address request phrased as a statement got the menu
    glued on mid-complaint. It also skips replies naming הצוות (the
    transfer-context closer). The `tapped_open` note now demands a short
    respectful reaction to the thing itself, acknowledgment of a repeat
    complaint, no slang, and ending on the question mark — written WITHOUT
    naming any phrase to avoid, because the first draft named "אני מבין" and
    thereby planted it.
  - **`Spell female male prompt.pdf` at the repo root is a VOICE spec** (nikkud
    for TTS, `agent_gender`/`customer_gender`, ends at Text To Speech). Only a
    subset applies to a keyboard. **The voice agents were not touched** — the
    pointed half is theirs and is an unstarted pass.
  - **The ban on `לך`/`שלך` is reversed** and this is deliberate, not a
    regression: unpointed they are one spelling and mark nothing to a reader.
    Allowed now: `לך`, `שלך`, `אותך`, `איתך`, `ממך`, `בשבילך`, `אצלך`, and the
    ־ת past. Still avoided: `אתה`/`את`, present, future, imperative,
    `אליך`/`אלייך`, `עליך`/`עלייך`. **Do not "fix" this back** — the reasoning
    is in `CONTEXT.md`.
  - **The bot follows a gender the resident wrote** (`אני גרה`) for the rest of
    the conversation. A name is still worth nothing.
  - **`באפשרותך`, `ברצונך`, `הנך`, `הינך`, `עבורך`, `לרשותך`, `להלן` are
    forbidden**, and `תוכל` was removed from the list of words the prompt
    recommends.
  - **The `אין לי` branch is decided by what the resident negated**: the ticket
    (`קריאה`, `פתחתי`, `דיווחתי`) means open the door and say the answer becomes
    a ticket for the team; only the number (`זוכר`, `שמרתי`) means ask building
    and apartment, and **ask**, not observe that it is possible.
  - **The Send node now strips any `[...]` span** as well as the dash. A probe
    caught the model emitting its own English reasoning, bracketed like the
    per-turn instructions, on its way to a resident. Intermittent; two clean
    reruns. If a legitimate bracket is ever needed in a reply, this is why it
    vanishes.
  - **Probing is `scripts/probe_whatsapp.py "מצב קריאה קיימת" ">>אין לי"`** and
    it costs one real model call per phrase. The model is
    `google/gemini-2.5-flash`, so a branch that is right three times can still
    be wrong the fourth; judge a prompt change on several runs, not one.
  - **The live workflow still cannot be deployed by `scripts/n8n_whatsapp.py`**
    (it refuses, correctly — eight nodes it does not build). The prompt is
    pushed on its own by a scratchpad script that reuses that file's
    `system_prompt()`, so `check_greeting()` still gates it. **That script dies
    with the session; the next person needs to write it again or teach
    `n8n_whatsapp.py` a prompt-only mode.** The Sort, agent and Send edits are
    mirrored in `n8n_whatsapp.py` but have only ever reached n8n by hand.
- **WhatsApp: the two `אין לי` prompt fixes below never ran, and there was a
  patch waiting to be pushed (26 Aug, now shipped — see above).** Retested at 16:26 and 16:36 and the
  reply was unchanged. The prompt was not the problem: the live system message
  is 37,856 chars and byte-identical to `prompt.md`. **Execution 9939** shows
  the agent's whole input was `אין לי`, and the memory for that phone held
  nothing but `אין לי` → `אני מבין. על מה אפשר לעזור?`, three times. The turn
  before it, execution 9932, was a canned reply with `_work: false`: the Sort
  node answered the button tap and the agent never ran. **A canned line never
  reaches the agent and is never written to its memory**, so no rule about the
  status flow could apply — the model did not know it was in one. Third time
  for this hole (`greeted` 12 Aug, `tapped_open` 25 Aug), and `TAP_KIND` has
  stored `status` all along with nothing reading it. Fixed by carrying the
  sentence instead of a fourth flag: `said()` records every canned line as it
  leaves Sort, the next turn gets it as `last_bot`, and the agent template
  states it as a fact and leaves the meaning to the prompt. Memory `sessionKey`
  bumped to `={{ $json.to }}-4` because Simple Memory cannot be cleared per
  conversation and that handset's window is four demonstrations of the fault.
  **`scripts/n8n_whatsapp.py` has the change; the live workflow does not** —
  every command that would push it, and the script's own dry run, were refused
  by the permission classifier. The patcher and a pre-change backup of the live
  workflow are in this session's scratchpad. **Nothing pushed, nothing tested.**
  **The live workflow has not changed since 15:34** (`updatedAt`
  `2026-08-26T07:34:49Z`), so the 16:26, 16:36 and 16:50 reports are three runs
  of one build and only the first is evidence. Check that field before reading
  the next screenshot. To ship it, run the scratchpad patcher — it PUTs Sort,
  the agent template and the memory key in one call and prints four assertions
  back; there is a pre-change copy of the live workflow beside it. Then probe
  with `scripts/probe_whatsapp.py "מצב קריאה קיימת" ">>אין לי"` before a real
  handset touches it.
- **WhatsApp: "אין לי" now splits in two (26 Aug).** "לא זוכר / לא שמרתי" keeps
  the lookup and asks building and apartment. "אין לי קריאה / לא פתחתי" has
  nothing to look up and gets the door opened instead:
  `אה, אין בעיה. אפשר לספר לי מה קרה? אני אפתח על זה קריאה ואעביר לצוות.`
  Ambiguous, ask the building; its answer settles it. **The bot says "לצוות" and
  never names a department** -- routing to the four Chatwoot teams does not
  exist, so naming one would promise a system we have not built.
- **Dashboard: redesigned and bilingual (26 Aug).** Hebrew by default with an
  English switch in the sidebar, `dir` and `lang` following it. Sidebar nav at
  >=1024px, SVG icon set, status pills with a dot as well as a colour, semantic
  stripes on the stat tiles, sticky table headers, Noto Sans Hebrew via
  `next/font`. **Every user-facing string lives in `dashboard/lib/i18n.ts`**
  (185 entries); a string written into a page shows untranslated in the other
  language and nothing fails. The middleware now sets `x-pathname` on the
  request headers because a server layout cannot otherwise know which page it
  is rendering. `tsc` and `next build` clean; all pages 200 in both languages.
  **Superseded by the 30 Aug pass below**, and the "never seen in a browser"
  note with it -- it has now been looked at. **This closes two of the three
  CRM gaps the owner listed on 25 Aug** (Hebrew RTL, and the login page now has
  real labels); **daily metrics and department scoping are still owed**, and the
  login page still is not enforced.
- **Dashboard: rebuilt on the Stovest design system (30 Aug).** The system the
  owner supplied lives in `Re-Design/` and is vendored under
  `dashboard/design-system/`. The four token files there are BYTE-IDENTICAL to
  the delivered ones on purpose -- every deviation is in one extension file,
  `tokens/app.css`, each with the measurement that forced it. **Do not edit
  `tokens/colors.css` and friends;** put the change in `app.css` so the diff
  against the source stays empty.
  - **Dark is the default and light is `data-theme="light"`**, which is the
    system's contract, not a preference. It is read from the `homies_theme`
    cookie on the SERVER, so the attribute is in the first byte of HTML and
    there is no flash. The switch is in the topbar, a server action like the
    language one.
  - **Four of the system's own colour pairs miss WCAG AA** -- its readme admits
    the colours were eyeballed from screenshots. White on `--accent` is 3.81:1
    behind a 13px nav label, so `--accent-fill` exists as a darker step of the
    same hue for anywhere the accent carries text; `--text-2` and `--text-3`
    were both raised. `python scripts/contrast_check.py` measures all 34 pairs
    the interface renders, composites translucent pill grounds the way CSS
    does, and exits 1 on a failure. **Run it after any token change.**
  - **Fonts: Poppins plus Noto Sans Hebrew, both through `next/font`.** Poppins
    is the system's face and has NO Hebrew -- not one glyph -- so Noto sits
    behind it and the browser resolves per glyph. The system's own
    `@import url(fonts.googleapis.com)` is deliberately not used: it is a
    render-blocking third-party request on every cold load.
  - **Three placeholders, drawn and labelled as such:** the topbar search, the
    notifications bell and the settings gear. Nothing in this app searches
    across four tables in one query and building it would be new data logic.
  - **Only the overview has had its own layout pass.** Tickets, debts,
    conversations, calls, sync, the two detail pages and login inherit the new
    shell and tokens but still need their own pass. Waiting on the owner's
    review of the overview.
- **The dashboard was slow because it asked the auth server twice.** The root
  layout called `auth.getUser()` -- a full network round trip, ~0.29s measured
  -- for a question the middleware had answered a millisecond earlier for the
  same request, and it blocked the shell from streaming while it waited. The
  middleware now sets `x-user-email` on the request headers alongside
  `x-pathname` and the layout reads that. **Do not reintroduce `getUser()` in a
  layout or page**; the middleware is the only place that should call it.
- **The hero card's ornament is ours, not the design system's.** The system
  ships concentric rings; `components/motif.tsx` draws rooftops instead,
  because the rings came from a stock-portfolio recreation and meant nothing on
  a maintenance dashboard. It is the only deliberate departure from the
  reference in the restyle — do not "restore" it.
- **Every `<td>` in every table carries a `data-label`, and it must keep doing
  so.** Below 720px the tables become stacked cards and that attribute is the
  only thing naming each line. Set it from the same `t('col.x')` call as the
  matching `<th>`; a new column without one renders as a value with no label.
- **`/search` is live and the header pill posts to it.** It covers `requests`,
  `residents`, `messages` and `interactions` (voice only), eight rows each,
  newest first, with a two-character floor. Nothing in the interface says
  "soon" any more; `chrome.soon` is deleted.
- **`term()` in `app/(app)/search/page.tsx` strips `, ( ) " ' \ % _ *` before
  the phrase reaches PostgREST's `or=()`.** Do not remove it and do not build
  another `or` filter from user input without it.
- **Every icon in `components/icons.tsx` now carries `width="16" height="16"`
  as an attribute.** That is the default for an icon nobody has styled — an
  unsized `<svg>` is 300x150 in normal flow and 0x0 inside a shrinkable flex
  item, and both have shipped. CSS still beats presentation attributes, so every
  per-component `svg` rule keeps working. Do not remove it.
- **`button svg` has a 15px default now.** An SVG with a viewBox and no width
  is 300x150, not viewBox-sized. Do not add another per-component rule for it
  unless that component genuinely wants a different size.
- **The phone has two bars and no sidebar.** `.mtop` (brand + Import + Settings)
  at the top, `.tabbar` (Overview, Tickets, Debts, Chats, Calls) fixed at the
  bottom; `.rail` is `display: none` below 1024px. Do not fold the sidebar back
  into a horizontal strip — seven labels across 390 points is what produced
  "Co" and "Impor" on the owner's phone.
- **A new destination does not automatically get a tab.** Five is what fits at a
  legible size. A sixth view goes in the top bar beside Import and Settings, or
  it displaces one.
- **Tab labels come from `tab.*`, not `nav.*`.** A tab is 78px wide and the
  sidebar names do not fit in it.
- **Language and sign out are not in any phone bar** — both are on /settings,
  which is one tap from the top bar.
- **Mobile is verified inside an iframe, never by resizing the window.**
  Headless Chrome clamps its window to about 489px, hands you 489 while you
  asked for 390, and crops the screenshot — which reads exactly like a layout
  bug. `scratchpad/mk_mobile.py` builds the iframe harness and `probe.js`
  reports real overflow from the layout engine.
- **The display name and profile photo live in `auth.users.raw_user_meta_data`
  (`display_name`, `avatar_url`, `avatar_path`), NOT in a profiles table.** The
  middleware reads them off the `getUser()` call it already makes and passes
  them to the shell as `x-user-name` (percent-encoded — headers are latin-1 and
  Hebrew is not) and `x-user-avatar`. Do not add a profiles table for these: it
  puts a second database round trip in front of every page render.
- **Nothing that grants access may ever go in user metadata.** The account can
  write its own metadata through the auth API. A role belongs in a table with
  its own policies, read by RLS from there.
- **Migration 029 created the `avatars` storage bucket** — public, 256 KB,
  webp/jpeg/png, write/replace/delete restricted to a folder named for the
  owner's user id. The path scheme `<uid>/<timestamp>.<ext>` is load-bearing:
  the policies compare `storage.foldername(name)[1]` against `auth.uid()`.
- **The photo is resized to a 256px square in the browser before upload**
  (`components/avatar-picker.tsx`). It is the only client component outside the
  login form.
- **`main` is pushed and level with `origin/main` as of 30 Aug.** The redesign,
  the charts, the logo and the settings page are all live on Vercel.
- **`/settings` is the account page, and it is the only page in the app that
  writes to anything.** Password change, theme, language, sign out. It verifies
  the current password before changing it — Supabase does not require that, and
  without it the session cookie alone is enough to lock the owner out.
- **There is no role model and the settings page says so.** One policy,
  `staff_read`, grants every signed-in account the same read of every table.
  Do not add a "Role: Admin" row until there is a column behind it.
- **The notification bell was removed on 30 Aug, deliberately.** Nothing raises
  a notification and there is no store for one. Do not re-add it as a dim
  placeholder; add it when there is something to announce.
- **Four logo files, and which one to use is decided on the server.**
  `public/homies-logo{,-dark}.png` are the full lockup (login page);
  `public/homies-mark{,-dark}.png` are the roof mark alone (sidebar), cut from
  the same sources. The `-dark` variants draw the ladder and figure in WHITE
  and are for dark grounds. **Do not pick between them with
  `prefers-color-scheme`** — the theme is a cookie and a switch in the topbar,
  so a media query answers the wrong question; read `getTheme()` and set the
  `src`. That bug shipped once already on the login page.
- **`.rail > * { flex: none }` is load-bearing.** The sidebar is a column flex
  container at `100dvh`; without it, a viewport under ~620px tall makes flex
  shrink the items instead of scrolling, and the brand collapses to height 0
  and is clipped away by its own `overflow: hidden` — invisible, with no error.
- **NEVER run `next build` while a dev server is up on the same directory.**
  Both write to `.next`; the build rewrites it under the running server, whose
  manifest then points at chunks that no longer exist, and the browser 404s on
  its own stylesheet. The page renders with no CSS, which does not look like a
  missing stylesheet — it looks like the app exploded (inline SVGs fill the
  viewport in visited-link purple) and nothing appears in any log, because
  nothing errored. Use `NEXT_DIST_DIR=.next-verify npx next build`;
  `next.config.mjs` reads that env var for exactly this. If a server is already
  in that state: stop it, delete `.next`, restart. A hard reload will not fix
  it.
- **The overview's date filter is `?from=&to=` in the URL**, defaulting to the
  last seven days, and it scopes every chart on the panel. Presets are plain
  links; the custom range is the one client component
  (`components/date-range.tsx`, `<input type="date">` — the browser's own
  picker). Both dates are validated in the page: reversed pairs are swapped, a
  future `to` is clamped, and a span over 366 days is cut back, because those
  queries pull rows rather than counts.
- **Bucket size is chosen by span, and the thresholds are set by CARD width.**
  <=14 days daily, <=98 weekly, beyond that monthly — never more than 14 columns
  in a ~240px card. If you widen those cards, `grainFor` in
  `components/charts.tsx` is the one place to change.
- **A `to` date is inclusive, so the query bound is the start of the NEXT day
  and exclusive.** Using `lte` on the date drops everything logged after
  midnight on the last day of the range. Same reasoning as the Jerusalem
  bucketing note below — both bit once already.
- **The overview's charts read three tables, and one of them is empty.**
  `requests` and `interactions` (channel `voice`) have real data;
  **`payment_links` has never had a single row.** `send_payment_link` writes one
  and stops — nothing delivers it, and OXS exposes no payment-link endpoint — so
  the third segment is a true zero, not a bug, and a line under the chart says
  so. It will start plotting itself the day delivery exists; RLS `staff_read`
  already covers the table. **Do not "fix" that zero by removing the series.**
- **Chart colour is validated, not picked.** `--cat-1..3` in
  `design-system/tokens/app.css` are slots 1-3 of the documented categorical
  order, checked against the real card surface in both themes. In LIGHT mode the
  aqua is 2.82:1 on white — a WARN, legal only with visible labels, which is why
  every segment is direct-labelled and repeated in the legend with its value.
  **Never use those fills without labels, and never add a fourth series without
  re-running the validator.**
- **No chart library, and the overview is still 189 B of client JS.** Both
  charts are inline SVG/CSS in `components/charts.tsx`. Hover is `<title>`
  rather than a floating tooltip, deliberately — a cursor-following tooltip
  needs a client component, and every value is printed anyway.
- **Anything bucketed by day must use `Asia/Jerusalem`, not `slice(0, 10)`.**
  Supabase returns UTC; Israel is 2-3 hours ahead, so slicing the ISO string
  files everything logged before 03:00 local under the previous day. `byDay`
  gets this right — copy it rather than re-deriving it.
- **Navigation is client-side. Use `next/link`, never a bare `<a>`, for
  anything inside the app.** A plain anchor reloads the document, which throws
  away the shell and the skeleton and spins the browser tab. The only `<a>`
  that belong are the ones leaving for GitHub on the import page.
- **The routes live in an `app/(app)/` route group and the shell is that
  group's layout.** The parentheses are invisible in URLs. `/login` is outside
  the group, which is what guarantees it never renders the sidebar — it used to
  be a path test in the root layout, and a path test goes stale as soon as the
  layout stops re-rendering between routes.
- **Anything in the shell that depends on WHICH page is showing must read
  `usePathname()`**, not a request header. A shared layout is not re-rendered
  when the page under it changes, so a server-computed path freezes on first
  load. This is why `components/nav.tsx` is the one client component in the
  shell, and why `x-pathname` was removed from the middleware.
- **Every route has a `loading.tsx`** backed by `components/skeleton.tsx`,
  sized to the real column counts and row heights so nothing shifts when the
  data lands. If you add a page, add its skeleton with the right `cols`, or the
  layout will jump.
- **Seen in a browser, finally.** Headless Chrome at 1440 and at a true 390
  viewport, dark and light, right-to-left and left-to-right. Two things the
  screenshots caught that reading the CSS did not: the hero ring motif was on
  the wrong corner in LTR (now a sized disc on `inset-inline-end`, which
  mirrors itself), and reference numbers were breaking across two lines in a
  narrow column. **Chrome headless clamps its window to ~500px** -- a
  screenshot requested at 390 is a 500px layout cropped to 390, which in a
  right-to-left page looks like a blank screen. Render inside a 390px iframe
  instead.
- **WhatsApp: the prompt holds no verbatim lines again (26 Aug).** The three
  fixes above were each written as an exact Hebrew sentence, taking the system
  prompt from 0 scripted lines to 4 in an afternoon; the owner asked for the bot
  to be open rather than scripted, which is rule 1 of the file's own editing
  rules. Rewritten as intent, distinctions kept, **back to 0**. Check with a
  grep for four-space-indented Hebrew inside the `## System prompt` section
  after any prompt session. The menu tap stays literal because the workflow
  answers it with no model call. Live prompt 37,856 chars. **Not tested through
  the bot.**
- **Voice: the Hebrew intake prompt was tested and had three Hebrew errors the
  English one did not (26 Aug).** `scripts/prompt_probe.py` puts fixed resident
  turns to the live assistant and prints what it writes; `--ref <commit>` runs
  the same turns against an older prompt, which is how a before/after pair is
  made. It tests WORDS, never audio. The three — `מה היה בנזילה?`,
  `מתי זה ייקח`, `בוא נראה` — were all the model lifting fragments of its own
  Hebrew instructions into its speech, which an English prompt cannot do.
  Fixed and re-tested at 0/8; live prompt is now 34,877 chars. **Open, 1/8:**
  one run said the closing line mid-call, which on a real call hangs up. What the change can and cannot do: the fixed lines the
  agents speak were always Hebrew and are carried through verbatim, so nothing
  about those changed; what should read less translated is every sentence the
  model composes between them.
- **Voice: the debt call's closing question changed (25 Aug).** Beat 3 was
  "anything else?", which the model rendered as `יש עוד משהו שתרצה ממני?`. It
  now asks whether anything is unclear or they want to ask something --
  `יש שאלות או משהו שלא ברור?` / `Any questions, or anything that isn't clear?`
  Live on both debt twins. The intake agent's own "anything else" beat was left
  alone: there it means another fault to report.
- **Voice: the "agent gets cut off" report is a transcript artefact (25 Aug,
  confirmed).** The 13:19 call log holds no record of the assistant's text at
  all -- every "Michael" line in the dashboard is a Deepgram transcript, and
  segments close mid-word when the pipeline clears, which happens whenever the
  caller speaks or types. Tells to recognise it by: `הומיס` corrected to
  `הומיז` between frames, `חכה 2º` for `חכה שנייה`, `דירה 12 12` doubled at a
  segment boundary. **Unproven:** that the audio matched the text; recording is
  off, so nobody has ground truth. Offer a single recorded call before
  promising the client the audio is clean.
- **Voice: no call in the account shows the agent cut mid-sentence (25 Aug).**
  Across all six real calls every `Pipeline cleared` follows a
  `Bot stopped speaking`, never interrupts one; delivery runs ~14 chars/sec,
  ordinary for Hebrew. **Unexplained:** in the 12:43:06 call the audio runs ~2s
  past the end of the model's text. Recording is off, so it cannot be settled
  without one recorded call.
- **A bare greeting never reaches the model (25 Aug).** `Sort` answers it with
  `MENU.content` -- `היי, כאן מיכאל מהומיז. במה אפשר לעזור?` -- every time,
  not once per 24 hours. Asked for three times; the model cannot deliver it
  because the mid-thread rule forbids reintroducing itself, and both rules
  cannot be true at once. So the name is now the workflow's job. Only a bare
  one: `שלום, יש נזילה` still goes to the model. Side effect: a greeting typed
  mid-flow restarts the opener.
- **The three buttons are attached by `Send`, on two signals (25 Aug, narrowed
  26 Aug).** `Sort` reporting `greeting: true`, or the reply containing
  `מיכאל מהומיז` **on a handset `Sort` has not greeted in 24 hours**
  (`greeted !== true`). Until 25 Aug it was the name alone, so a second `היי`
  inside 24 hours lost the buttons. On 26 Aug the name-alone half misfired the
  other way: the model re-introduced itself mid-thread on a "לדבר עם נציג" tap
  (a prompt example matched the input verbatim and beat the mid-thread note —
  fixed in prompt.md the same night) and a resident asking for a person got the
  menu glued to the transfer reply. The `greeted` guard makes mid-thread menu
  attachment impossible whatever the model writes. The live Chatwoot `Sort`
  had no greeting test at all between the 21 Aug cutover and 25 Aug.
- **`Reply usable?` exempts a one-word reply to a greeting (25 Aug).** Its
  false branch is the rescue: `rescue_request`, a real ticket, and a handover
  line. `היי.` is one word and correct, so a resident who said hello twice was
  given a service call. Empty output and one-word answers to anything else
  still take the rescue. **Residual, flagged not fixed:** a one-word reply to a
  non-greeting (`תודה` → one word) still opens a `needs_review` ticket.
- **A tap is remembered for one message (`tapped_open`, 25 Aug).** Tapping
  `פתיחת קריאת שירות` is an explicit request, but the canned reply never
  reaches the model, so the agent used to offer to open a call the resident had
  already asked for. `Sort` now records the tap in workflow static data and the
  next message carries a flag that tells the agent to skip the offer and ask
  the building and apartment. Deleted after that one message; typing a fault
  without tapping still gets the offer.
- **The canned tap lines are not the model, and they can contradict the
  prompt.** `TAP_LINE` in `scripts/n8n_whatsapp.py` answers a tap on the menu
  with no model round trip. The `status` line spent a day asking three things
  at once while the prompt required one question, and it is where the owner
  first saw the dash. If a reply looks wrong and prompt changes do not move it,
  check whether it is canned before rewriting the prompt again.
- **The live n8n workflow is ahead of `scripts/n8n_whatsapp.py`.** Eight nodes
  and the Chatwoot-shaped Sort parser exist only in production. **`--apply`
  now refuses** while that is true; patch live through the REST API, back up
  to `docs/handover/` first (24 Aug backup is there, secret redacted), and
  bring the change back to the repo. `check_whatsapp.py` speaks Chatwoot's
  envelope since 24 Aug and is green; it had been red against a working bot
  since the 21 Aug cutover.
- **The bot answers in Hebrew unless English is explicitly requested** (the
  menu row, or the word). Script detection was removed: a Latin-letter
  reference number was flipping Hebrew conversations to English.
- **The voice agents read out only the tail of a reference** — `1, 0, 0, 1`,
  not `HM-2026-1001`. Lookup matches on the tail. The WhatsApp bot still quotes
  the reference in full, because there it is copied text rather than speech.

---

## The data, as it stands

- **7,532 residents** — real names, real E.164 mobiles, across 174 buildings
  (175 are active in OXS; one has no resident with a usable phone). All carry
  `handed_over = false`, so **`v_debt_call_queue` is empty and nothing can
  dial**. A person must flip that flag before any campaign. This is the safety
  interlock; do not remove it casually.
- **65 apartments owing ₪60,175, held by 64 residents — 105 monthly charges,
  Jan–Jul 2026** (written 25 Aug from that morning's sweep). One row per
  apartment per unpaid month, `period` = the month owed. The raw sweep said
  576 apartments and ₪977,850; the correction (22 buildings that joined
  mid-year lose their leading months, 2 buildings with a recording lag are
  excluded) brings it to 79 apartments / ₪67,225, and 15 of those have no
  phone and are not written. **89 charges are marked paid** — 80 of them on
  25 Aug, months the 11 Aug import listed that OXS now shows a payment for.
  Apartments and residents are different numbers and the dashboard counts both.
- **342 apartments are behind and not chased**, because they have no 2026
  payment at all and therefore no monthly rate that can be trusted — new,
  vacant, or never handed over. They are reported by the sweep and deliberately
  not written.
- The one legacy row — ₪1,500, a 2022 balance, and the only thing OXS's
  `/debts` endpoint reports for the entire company — was **deleted 17 Aug**.
  194 charges now, 89 of them paid, none dated later than July.
- **70 imported maintenance tickets of 104**, and the other 34 are ours from
  testing (21 voice, 12 WhatsApp, 1 staff) — the Tickets, Calls and
  Conversations pages all show test traffic mixed with the real import. **No
  real resident has ever spoken to the system**: all 167 interactions and 460
  messages are our own.
- Tickets refresh **every 15 minutes** on their own workflow since 24 Aug
  (`oxs-requests.yml`), not twice a day. Each carries `oxs_notes` — the OXS
  dispatcher's own progress notes, newest first — and `oxs_last_seen_at`.
  **36 of the 70 have left the OXS feed** and are flagged on the dashboard as
  gone, not resolved; see client question 2.
- Zero demo or synthetic rows; both were purged on 10 Aug. Every charge carries
  `source = 'oxs'` — until 11 Aug they all said `'seed'`, which is the flag
  every destructive query filters on.

**Finishing a task means updating three files, and a hook says so.**
`scripts/check_briefing_logged.sh` runs on Stop and refuses to end a turn whose
change set touches anything substantive without touching **CONTEXT.md and
HANDOVER.md**. It blocks each change set once, records the fingerprint in
`.git/briefing-nagged`, and cannot loop. Enforcement is switched on in
`.claude/settings.local.json` (gitignored — this repo is public and a cloner
should not inherit a hook); the check itself is committed and runs by hand:
`bash scripts/check_briefing_logged.sh`. **If it fires and one of the three
really needs nothing, write the line saying so** rather than bypassing it.

### Known defects — eight still open, eighteen fixed and kept for the record

1. ~~**The 2022 debt is stamped `2026-08`.**~~ **Fixed 17 Aug.** The row —
   ₪1,500, ארז לויים, הרכסים 17 apt 8, `handed_over=false` — was deleted, and
   `--skip-charges` on the scheduled import stops `/debts` being read at all, so
   it cannot return. `charges` now holds 178 rows, all real arrears across
   2026-01 → 2026-07, ₪100,020 open, and no row carries an `oxs_ref`. The
   dashboard's "open on the newest *completed* month" rule stays — the current
   month is never chased, which was always the better half of that reasoning.
2. ~~People owning several apartments collapse into one row.~~ **Fixed 11 Aug**
   by migration 012: the apartment lives on the charge, unique on
   `(resident_id, period, unit)`. Recovered ₪6,665.40 across two owners.
   `residents.unit` still exists but names only one of an owner's flats and is
   **not authoritative for debt** — read `charges.unit`.
3. **A handover reaches nobody.** Narrowed 18 Aug — standing orders now open a
   ticket, so this is `transfer_to_human` alone, 16 rows.
   `transfer_to_human` writes a row to
   `call_outcomes`, stamps `interactions.disposition`, and stops. No email, no
   Slack, no notification of any kind — and the dashboard has no transfers view,
   which a grep over `dashboard/` confirms. So `אני מעביר את זה לצוות, נחזור
   בהקדם` is a promise that depends on somebody opening a table that does not
   display it. **This is worse than declining**, because a resident who is told
   help is coming stops chasing. Found 16 Aug; every handover since the bot went
   up is sitting unread. Smallest of the open items and the only one that is a
   live correctness fault rather than a missing feature.
4. **18 apartments have no phone in OXS** and were skipped. Not callable.
5. **CONTAINED, NOT FIXED — the WhatsApp bot claims work it did not do.** Two
   faces of one fault. The handover line without `transfer_to_human`, seen
   12 Aug; and on 19 Aug, with the execution in hand, *"פתחתי קריאה … מספר
   255-1048-26"* having called only `verify_address`. No row, and that reference
   belongs to somebody else's ticket, so a resident quoting it later quotes a
   stranger's fault.

   **The guard is live at "Reply usable?"** — a reply carrying a reference, or
   claiming a request was opened, with no `open_request` output behind it takes
   the false branch into "Hand over instead". Proven on a real run: the phantom
   was replaced with *אני מעביר את זה לצוות* and the resident got a person
   instead of a fabricated number. **The cause is untouched and intermittent** —
   one run in the same session called the tool correctly.

   Two n8n traps found building it, both worth knowing before editing any
   expression here: **`}}` anywhere inside an expression ends it** — n8n closes
   on the first one, so an arrow function's natural `}})()` truncates everything
   and the node reports "invalid syntax" at run time rather than at deploy; and
   **`isExecuted` is useless on a tool node** — it returned true on a run whose
   execution shows the tool was never called. Use the node's output instead.
17. **CLOSED 25 Aug.** The correction now lives in `oxs_arrears.py` as
   `correct()`, applied on every path (`import_arrears.py` imports it), and the
   nightly write is per-month. Kept for the history. ~~The nightly arrears
   import writes the UNFILTERED sweep, and the ₪922,901 on the dashboard is not
   a debt figure anybody has stood behind.~~ Opened
   24 Aug, the hour the import first completed. `import_arrears.py` — which
   produced the ₪101,519 figure on 11 Aug — drops two patterns before writing:
   months forming a **leading run** shared by ≥60% of a building's flagged
   apartments (the period before Homies managed the building, not debt), and
   whole buildings where ≥80% miss the same pattern (recording lag, not debt).
   It reads `docs/reference/arrears-2026.json`, which `oxs_arrears.py` writes
   **only when `--quiet` is off** — and the workflow passes `--quiet`. So the
   automated path skips the filter entirely. Raw: 576 apartments, ₪975,991.
   Filtered, by hand, on 11 Aug: 122 and ₪101,519. **Do not quote the dashboard
   arrears total to the client until this is settled.** Nothing dials — every
   resident is `handed_over = false`.

18. **CLOSED 25 Aug.** Migration 023 deleted the 540 cumulative rows
   (₪934,061); `period` is the month owed everywhere; a current-month unpaid
   OXS row is deleted on every run as the one shape that can only be wrong; and
   a charge is marked paid only on positive evidence from OXS. ~~Two importers
   disagree about what `charges.period` means, and ₪63,614 is counted
   twice.~~ `import_arrears.py` writes one row per unpaid month stamped
   with the month owed; `oxs_arrears.py` writes one cumulative row per apartment
   stamped with the month it ran. 68 residents hold both — ₪683 for July and
   ₪683 again inside the August row. Re-running within the same month is safe
   (it upserts the same period). **1 September is not**: it writes a fresh
   Jan–Aug row beside the untouched Jan–Jul ones and compounds monthly from
   there. Decide before then whether the nightly import retires its own earlier
   rows, or is re-keyed so a year's arrears is one row.

19. **The WhatsApp bot can answer in the resident's voice.** Real transcript,
   24 Aug 14:28, under the 23 Aug prompt: to `אין לי לא פתחתי` it wrote
   *"אוקיי. אם ארצה לפתוח, אשאל על הפרטים"* — first person as the one deciding
   whether to open a ticket — and to `לא אחי`, *"אוקיי, תודה בכל אופן"*. Not
   the intro; the model losing which side of the conversation it is on, which
   the WORKLOG has seen before as "does not recognise its own turns". Suspect
   the `Conversation so far` memory shape. Found while fixing the intro, not
   fixed. Reproduce with a short refusal after the status-menu tap. **Not
   reproduced on 25 Aug** after the per-message rule was rewritten (`אין לי,
   לא פתחתי` → `אוקיי. אז אפשר לפתוח קריאה, לבדוק מצב...`); may have been the
   same cause. Keep open until seen clean on a real handset.

21. **The model is inconsistent about complaint vs the service type.** "The
   cleaner has not come for two weeks and the lobby is dirty" filed as
   `complaint` on one run and `cleaning` on the next, same words. Both are
   defensible — the second even routes to the cleaning team — but it means
   "every complaint has `type = complaint`" is not a promise anyone can rely
   on for a report. Decide whether service-not-delivered is a complaint or a
   task, then say so in one line in both prompts.

20. **Asked `אתה בוט?`, the bot said `אני לא בוט.`** Live, 25 Aug, fresh
   number; on an earlier run the same question got `אני נציג שירות`. There is
   no rule about it in the prompt, so the model improvises, and one of its
   improvisations is a lie to a resident. **This needs a decision, not a
   prompt tweak**: whether מיכאל admits to being automated when asked directly.
   Recommendation: yes, in one line, and carry on -- `אני העוזר האוטומטי של
   הומיז. במה אפשר לעזור?` -- because the persona is a name and a tone, not a
   claim to be a person, and the first resident who finds out otherwise tells
   the whole building. Reproduce: `python scripts/probe_whatsapp.py "אתה בוט?"`.

6. **A common-area ticket keeps an apartment number if the resident offers
   one.** A stuck-lift ticket came out with `unit = 12`. The bot correctly
   never asked, but `check_whatsapp.py` asserts common-area faults carry no
   unit, so the contract and the row disagree and a dispatcher is misled.
20. ~~**The arrears sweep loses buildings to the rate limit and reports a total
   anyway.**~~ **Fixed 24 Aug.** It slept 1.05s twice per building while making
   three GETs, so the request rate depended on latency — ~27/min from a GitHub
   runner, over 60/min from a machine near OXS, where **37 of 175 buildings
   answered 429** and were skipped with a printed warning, taking 511 of 576
   debtors with them. The gate moved inside `get()` and keys on the previous
   request's start, so the rate is 57/min whatever the link; a 429 is retried
   three times honouring `Retry-After`; a tenants failure counts as a failure
   too (it costs the phone, and a row with no phone is dropped by the writer);
   and an incomplete sweep writes what it found and then **exits non-zero**, so
   the workflow gate and `/sync` both go red.

19. ~~**The scheduled import had never completed a single pass.**~~ **Fixed
   24 Aug**, and verified by a 27m41s run that wrote 534 charges. Five faults:
   the 45-minute job ceiling (a full pass is ~28 min, ceiling now 90), 14m24s of
   row-at-a-time writes now one statement per table, an `ON CONFLICT
   (resident_id, period)` that migration 012 dropped on 11 Aug and which
   answers 42P10 every time, `charges.source`/`charges.unit` never being set,
   and block-buffered stdout that made the killed step log nothing at all.
   `charges.status` also stopped being forced back to `'unpaid'` nightly, which
   would re-chase somebody who paid before staff entered it in OXS.

16. ~~**A caller was told about another resident's request, and the call had no
    memory of itself.**~~ **Fixed 19 Aug.** The category is matched against the
    description as well as the `type`, so a lift enquiry finds the caller's
    ticket without widening to the building; everything else comes back as
    `other_open`, **a count, which is the most the agent may say**. A building
    with no fault named returns `identify_needed` and withheld descriptions. The
    prompt gained a within-call memory section — a question about something the
    agent mentioned is not a new fault, a declined offer is not re-offered.
    **Client decisions, both explicit:** how many but never what; memory within
    the call only.
15. ~~**The model poisons its own lookup — an apartment for a lift, a reference
    a digit short.**~~ **Fixed 19 Aug, in the function rather than the prompt.**
    Five common-area categories drop the apartment whatever the agent passes; a
    three-digit reference becomes a wildcard search returning `partial_reference`
    — one or two candidates get read back, more than three asks for the number
    again. **Read the tool-call arguments in Vapi before believing a transcript**
    — twice the transcript blamed the database and the arguments blamed the
    model.
14. ~~**The type filter hid the ticket it was meant to find, and "never mind"
    got a transfer.**~~ **Fixed 19 Aug.** The `type` filter on
    `get_request_status` is soft now — it narrows, and falls back when that
    empties the answer, because a ticket's category is an inference and the
    caller's question is not. And rule 7 carves out the case it was never meant
    to cover: a question asked and answered is a complete call, so a declined
    offer is no longer answered with the office number, a transfer and a goodbye
    all at once.
13. ~~**A reference quoted by a caller is not found, and a correction gets a
    transfer.**~~ **Fixed 19 Aug.** `serialOf` now reads spoken digits — "one
    zero six three" and `אחת אפס שש שלוש` both resolve. The apartment question
    moved its condition into the capture section, because two sections disagreed
    and the model followed the general one. A correction after a not-found is a
    new search, never a transfer.
12. ~~**The status lookup only matches an exact building name, and demands an
    apartment for a shared fault.**~~ **Fixed 19 Aug.** `ilike` not `.eq`;
    apartment optional; optional `type` filter; `ambiguous_building` when the
    loose match spans more than one. **This surfaced a live data defect** —
    `Herzl fourteen` and `Herzl 14` are one building stored twice, because the
    agent writes what the caller said and `verify_address` is still not attached.
11. ~~**The agent improvises the waiting line, and reads the address back
    twice.**~~ **Fixed 19 Aug.** The waiting line is a request-start message on
    the three sync tools now, not an instruction — the model ignored the
    instruction twice. **The prompt tells the agent to stay silent there; do not
    put the line back in the prompt, or it is heard twice.** New tool messages
    need an entry in `TOOL_MESSAGES` in `vapi_en.py` or the twin build exits.
10. ~~**The agent cannot read a request status, and opens a second ticket
    instead.**~~ **Fixed 19 Aug.** `get_request_status` and `get_balance` are now
    declared in `INTAKE_TOOLS` and routed in the n8n Decide node; the handlers
    were already complete in the Edge Function. Both verified through the live
    webhook. **Any new tool needs all three** — handler, route, declaration — and
    the prompt describing it counts for nothing.
9. ~~**The intake call is correct and cold**, and the offer sounded like a
   script.~~ **Fixed 19 Aug**, in two passes — the second because the first kept
   a three-rung structure that was never asked for. The offer is now one turn
   carrying both options and the honest wait on the slower one; the English says
   "ticket", not "request". Every field
   captured, every answer met with the next question and no acknowledgement;
   the same filler question three times; a follow-up jammed onto the reference
   number; a bare "I cannot say"; the goodbye split off into its own utterance.
   All six were the prompt's, not the model's — the pacing rules banned enough
   speech that the model removed the rest. **When editing those rules, add an
   example of what is still wanted**, not only what is banned.
8. ~~**The agent's sentences arrive with holes in them.**~~ **Fixed 19 Aug.** A
   resident heard *"Would you like me to  though."* — two spaces, no verb.
   Nothing was interrupted; `voice_guard.py` strips phrases so a tool name can
   never be read aloud, and `open request` was on the list. Six two-word entries
   removed, all of them ordinary English. The rule that should have caught it was
   already written in that file and unenforced, so it now is: `SAFE_SENTENCES`,
   checked by `python scripts/vapi_leak_check.py --safe`. **Run that after any
   change to the spoken filter.** `SAFE_SENTENCES` entries may be a bare string
   (must survive untouched) or a **pair** (must come out as the second half) —
   the pair form is for the deliberate pronunciation rewrites, such as להומיז
   becoming לחברת הומיז, which are the filter working rather than damage.
7. ~~**An inbound ticket carries an address the caller never gave.**~~ **Fixed
   19 Aug.** `255-1056-26` was filed against Herzl 14, flat 12, for a caller who
   said *"Herzo"* and did not know their apartment. The agent captured it
   correctly; the webhook overwrote it, because `ctx.building || args.building`
   put call context ahead of the caller on **every** path, and the demo page was
   attaching a debt campaign's file to inbound calls. Now gated on `dialled(ctx)`
   — see CONTEXT.md — so context counts only on a call we placed. Verified live
   against the exact shape of the failing call.

### Five more, from the client's own calls on 12 Aug — four now fixed

Traced to Yariv's ten calls on the debt agent, not reasoned about. Feedback
verbatim in `feedback-yariv-voice-2026-08-12.txt`; the full reading, and what
was done about each, is in the WORKLOG entry for 12 Aug.

7. ~~The debt agent's opening is heard as "לאומיז".~~ **Fixed.** `מהומיז` was
   one token — a one-letter preposition glued to the company name — and the
   voice read the pair as one unfamiliar word. Now `מחברת הומיז`, plus a
   substitution in `voice_guard.py` because the model composes most sentences
   and will write the glued form again, correctly.
8. ~~Nothing speaks into silence.~~ **Fixed.** `messagePlan` was null on both
   Hebrew agents, which is why no prompt change could have helped — the model
   is not invoked while nobody is talking. Two genderless lines, first at 8s,
   twice per stretch of silence, plus a `silenceTimeoutMessage` so a dying line
   ends on a goodbye.
9. ~~`{{verification_email}}` is Latin text read by a Hebrew voice.~~ **Fixed.**
   Stored the way it is said — `אופיס, שטרודל, הומיז, נקודה, סי, או, נקודה,
   איי, אל` — since nothing parses it. **The address itself is still
   **CONFIRMED 18 Aug and corrected everywhere**:
   `Office@homies-management.co.il`, from the client's own FAQ. Until then the
   demo page said `office@homies.co.il` and the test scripts said
   `homiesemail@gmail.com`, both invented, and an English test call read the
   invented one to a resident. Respell it
   in the same shape when Homies answers.
10. **The gender fault was bookkeeping, not Hebrew, and the branch is gone.**
   `gender = "m"`, `first_name = יוסי`, and the agent said **תשלחי** one turn
   after the masculine form. `{{gender}}` no longer appears in the prompt at
   all: `{{gender_forms}}` arrives finished, in Hebrew, at the top — the same
   pattern as `apartments_phrase`, and for the same reason. Inbound also got
   the full language skill, which it had never had. **Neither has been
   re-tested on a live call, and free sentences can still slip.**
   **`gender_forms` is composed in `web/index.html`** — a call from an
   undeployed build sends nothing for it and the agent runs with no gender
   instruction at all. Deploy before testing.
11. ~~A tool call can be the last thing the agent does.~~ **Fixed** in the debt
    prompt: after any tool the next thing is speech, and "you send it to me"
    now splits — the payment link can be sent, nothing else can.
    *Correction to the first reading:* the `log_disputed_payment{}` in that
    call was **not** a defect. The tool takes one optional field and its
    description says to omit it unless one apartment was named. The empty call
    was correct; only the silence after it was wrong.
12. **`vapi_en.py intake` has been unbuildable since 7 Aug.** Its substitution
    table still expects `You are Michal` and `אני מעבירה`, from before the
    agent was made male; every passage must match exactly or it refuses. The
    Hebrew assistant is the deployed one and the twin is for review only, so
    nothing live is affected — but the English intake assistant on the account
    is stale and cannot be regenerated until the table is brought forward.

---

## OXS — the part that took longest to learn

**The API works.** `https://api.oxs.co.il/api/external/v1`, header
`x-api-key`, envelope `{status, data}`. Three module-scoped keys in `.env`
(`OXS_KEY_GENERAL`, `OXS_KEY_DEBTS`, `OXS_KEY_REQUESTS`), all live; external
API access was already enabled, so no support ticket is needed. Reference is
`OXS_External_API_v1.pdf` in the repo root — gitignored, it is OXS's document.
Rate limits are **60/min and 1,000/hr per key**, not shared across keys.

**`/debts` does not report who is behind.** It returns one record
company-wide — a 2022 balance belonging to an owner marked inactive, with
collection notes attached. It answers "who carries old debt". Proven by
counter-example: one building shows zero debts via `/debts` while its own
payment records show apartments that have not paid since June.

**So arrears are computed, not fetched.** `/buildings/:id/payments` carries
`apartmentId`, `totalAmount`, and `monthsPaid[{year, month, amount, isKeva}]`.
Arrears = months of the year that have ended with nothing paid against them,
at the apartment's own monthly rate, never a guessed one. The current month is
never chased.

**The correction that makes it honest:** where four or more flagged apartments
in a building miss the same *leading run* of months (01, 01–02, 01–05), Homies
took that building on mid-year and the run is not debt. Thresholds are
asymmetric on purpose — 0.6 for leading runs, 0.8 otherwise — because a whole
building going unpaid from January and resuming in unison does not happen,
while a building being taken on in May happens constantly. Raw sweep flagged
610 apartments and ₪962,405; after correction, 139 and ₪108,770.

`docs/reference/arrears-2026.json` holds the full list and is **gitignored —
740 real mobile numbers, and this repo is public.**

---

## Credentials — names only, values live in `.env`

| System | Env vars |
|---|---|
| Vapi | `VAPI_PRIVATE_KEY`, `VAPI_PUBLIC_KEY` — **account 4 since 19 Aug**, promoted when account 5 went overdrawn (+ `_OLD`, `_ACCOUNT2`, `_ACCOUNT3`, `_ACCOUNT5`). Every superseded pair is kept: the one time a key was dropped it took a day to work out which account a stale assistant id belonged to |
| Supabase | `SUPABASE_URL`, `_ANON_KEY`, `_SERVICE_ROLE_KEY`, `_DB_URL`, `_DB_PASSWORD` |
| n8n | `N8N_BASE_URL`, `N8N_API_KEY`, `N8N_WEBHOOK_SECRET` |
| OXS | `OXS_KEY_GENERAL`, `OXS_KEY_DEBTS`, `OXS_KEY_REQUESTS` |
| Cartesia | `CARTESIA_API_KEY` (attached inside Vapi as a credential) |
| OpenRouter | `OPENROUTER_API_KEY` — **key 2 since 12 Aug**, uncapped, on the $19.80 account. `_CAPPED15` is the 12-Aug key (same account, $15 cap); `_EMPTY` is a different, unfunded account. n8n credential `92ZNHDhByavmNP5T` (`N8N_OPENROUTER_CRED_ID`) — the API cannot PATCH a credential, so a key change means a **new credential and a re-push**, and every superseded one is left in place |
| Meta/WhatsApp | `APP_ID`, `APP_SECRET`, `WHATSAPP_TOKEN`, `WHATSAPP_WABA_ID`, `WHATSAPP_PHONE_NUMBER_ID` |
| Vercel | `VERCEL_TOKEN` — **the one in .env answers "invalidToken" (checked 24 Aug)**; deploys still go out on push |
| Dashboard, in Vercel's env (none set yet) | `CALL_PIN` (no PIN, no Call column), `VAPI_PRIVATE_KEY`, `VAPI_PHONE_NUMBER_ID` (no number, no call), `VAPI_DEBT_ASSISTANT_ID` (defaults to Debt he), `HOMIES_CALLBACK_NUMBER` / `HOMIES_VERIFICATION_EMAIL_SAY` / `HOMIES_ALT_PAYMENT` (defaults in `dashboard/lib/call.ts`), `GITHUB_DISPATCH_TOKEN` (Run now on `/sync`) |
| Internal | `TOOL_SECRET` (Vapi → n8n → Edge Function) |

Empty and expected to stay empty: Twilio, Telnyx (no phone numbers yet).
Missing if wanted: `ELEVENLABS_API_KEY` — the custom voice
`WKRPx9n3dUHKk1SZhnwv` errors in Vapi because only a Cartesia credential
exists. Never print a value, never commit one, never paste one into chat.

---

## Open questions for the client

1. **Why does OXS report one debtor across 193 buildings?** Either their
   finance module tracks only legacy carried debt, or Homies records arrears
   somewhere the API does not aggregate. Until answered, the computed arrears
   list is ours, not OXS-blessed.
2. **When a service call stops appearing in OXS, has it been done?** The single
   most valuable question on this list, and the cheapest to answer. Their
   `status` field reads `פתוחה` on every call they serve — verified 24 Aug
   across all 35 live, dating back to 10 February — so closure is expressed only
   by the call leaving the feed. 34 were live against 70 we hold; three left
   within one hour that morning. If leaving means done, one UPDATE resolves 36
   stale tickets and the bot stops telling residents that a finished job is
   still open. If it does not, we have a real backlog nobody is counting.
   `requests.oxs_last_seen_at` has been stamped on every run since 24 Aug, so
   whichever the answer is, the data to act on it already exists.
3. **Payment proof by WhatsApp or email?** The dispute path sends residents to
   `{{verification_email}}`; Israelis default to WhatsApp screenshots. An
   office-intake decision, not a prompt change.
4. **Meta/WhatsApp ownership** — if the number is to be Homies', they must
   grant Business Manager access rather than hand over a login.
5. **Chatwoot seats** — how many users, names and emails, which inboxes.

## The freeze was lifted 11 Aug, and feature 14 shipped through it

The voice-agent freeze (11 Aug, morning) was lifted the same day by the client
— *"implement the handling"* — and both of its deferred consequences are
resolved:

1. **`debt-tools` is deployed (v15).** The multi-apartment `get_balance`, and
   the whole feature-14 tool layer: `ctx.charges` whitelist, per-apartment
   writes via an optional `unit` the server resolves, `flag_not_handed_over`
   defanged, `ownership` transfers pausing the named apartment.
2. **Call grouping is decided and built: one call per resident.**
   `v_debt_call_queue_person` is the queue; the phrases are composed in SQL;
   the live Hebrew assistant carries the person-call prompt and tool schemas.
   One scope cut, by the client: apartments that owe nothing are not counted
   or spoken — only what owes is on the call.

**The English debt twin is CURRENT again** (rebuilt 11 Aug, evening): its
substitution table was rebuilt against the post-cut prompt — four whole-section
blocks plus 52 line pairs, feature 14 included — and pushed to account 4. Both
demo languages now show the same call. `vapi_en.py debt --dry` is the health
check; it exits loudly whenever a Hebrew fixed line changes, and the fix is the
table, never the check. **The intake twin was rebuilt 18 Aug** — 25 passages plus
two regex blocks against the masculine prompt, 21,734 chars, no Hebrew left, and
pushed. Its table had refused since 7 Aug, which is the check working: the agent
turned masculine, five fixed lines stopped matching, and it stopped rather than
shipping half a translation. Both English demos can be trusted again. The demo page still
sends `month` (singular) alongside the phrases; harmless, and the intake twin
relies on nothing else.

Nothing dials: no phone number exists, all 7,391 residents are
`handed_over = false`, and both queue views return 0 rows.

## Next moves, in order

**THE REFACTORED PROMPT IS LIVE AS OF 30 AUG, AND THE PATCHES IN IT WERE
NEVER PROBED.** State as of the push, in order of what would bite first:

1. **Live on assistant `7752c6bb-89e9-49f3-aaf4-154ecc65cdff`**, 19,978 chars,
   down from 35,622. Verified against the Vapi API after the write, not assumed:
   prompt matches the repo byte for byte, six tools attached, 27 guard
   replacements, `recordingEnabled` false, transcriber `deepgram nova-3`. This
   also finally ships `8793c9f`, so the office-number stutter is gone from live.
2. **The three regression patches went live unprobed.** They were written
   against failures `prompt_probe.py` found and were never re-tested — the owner
   chose to push rather than spend the $0.08, with the office-number bug live
   and breaking calls as the reason. **So the first real calls are the test.**
   Watch for: the reference number read in full (all three parts instead of the
   middle), and the address read-back before the write going missing. Both
   regressed once already. Rollback is `git revert` plus one `--apply`.
3. **`prompt_probe.py` bare reads the LIVE assistant, not the repo.** While
   nothing is applied, that is the *old* prompt. Use `--ref HEAD` for the new
   one and `--ref 8793c9f` for the old. Getting this wrong scores the same
   prompt twice and reads as "no change".
4. Skip the `late` scenario on inbound — it is a debt call and only adds noise
   and cost.

**What the probe established about the refactor**, so nobody re-litigates it:
the example-contamination failure (`מה היה בתיק?` on a parcel) is fixed, the
re-asking of already-given facts is fixed, the ungrammatical `מתי זה ייקח` is
gone, and per-call token cost halved. Against that, the reference number and the
address confirmation both regressed and were patched. The fence is 19,978 chars,
down from 36,668.


**TWO THINGS ARE COMMITTED AND NOT LIVE, AND A CALLER TODAY GETS NEITHER.**
`8793c9f` (the office number written as speech, which fixed the 30 Aug
digit-stutter) and the 30 Aug prompt refactor are both in the repo and neither
has been pushed to Vapi. One command covers both:

    python scripts/vapi_sync.py inbound --apply

Until that runs, the inbound assistant is still serving the 36,668-character
prompt with `077-6687949` in it, and still breaks on any call that asks for the
office number. **Read the dry run's tool list before applying** — it must show
six.

**The inbound prompt was cut 49% on 30 Aug and it is a real behavioural
change.** The fence is 18,824 characters, down from 36,668. Reverting is one
`git revert` plus one `--apply`. Two behaviours to watch on the first calls
after the push, because their explanatory stories were moved out of the prompt
and the bare rules may not carry the same weight: **opening a second request for
a fault that already has one**, and **the count-not-contents line on other
residents' requests**. The `parcel` scenario in `prompt_probe.py` exercises the
first.

**`prompt_probe.py` is the measurement and it has not been run.** It costs
money — OpenRouter, the same key the WhatsApp bot runs on, roughly six model
calls per scenario carrying the whole prompt each time — so it needs the owner's
word each time, like every spend here:

    python scripts/prompt_probe.py inbound --ref 8793c9f    # before
    python scripts/prompt_probe.py inbound                  # after

Same tools and same fixed tool results on both halves, so the only variable is
the wording. Worth running **before** the live push, not after.

**`docs/knowledge/homies.md` is new and is the master for the thirteen facts
both channels state.** Change a fact there, then in both prompts, then run
`python scripts/facts_check.py`. It exits non-zero and names what drifted. The
WhatsApp prompt was deliberately not edited — doing so means a redeploy through
shared production n8n.

**Three rows of `demo-inbound.md`'s configuration table were wrong and are now
right.** If you read that file before 30 Aug, re-read it: the transcriber is
`deepgram nova-3` and has been since 12 Aug (the table said `11labs` for
eighteen days); `recordingEnabled` is **false** by client instruction (the table
said true); and `INTAKE_TOOLS` has **six** tools, not three. The recording one
matters most — there is no audio for any call, which is why the 30 Aug stutter
could not be settled as voice-looping versus transcriber-looping.

**Still open, unchanged:** `{{callback_number}}` is a numeral and will break the
debt agent's voicemail line the same way the office number broke inbound. It
comes from `dashboard/lib/call.ts` and four scripts. Not urgent — there is no
phone number on the account, so no voicemail is reachable — and the fix is the
same one: store it spoken.


**The owner's read of the PRD checklist, 25 Aug — what is accepted as-is and
what is still owed.** WhatsApp bot: done; next is moving it to Homies' own
number and sending the OXS payment link through WhatsApp (template message).
Status lookups: done, from our copy of OXS, on both channels. Complaints:
**a ticket, `type: complaint`, on voice and WhatsApp** (corrected by the owner
the same hour; migration 025) — opened like any request, read by staff in the
dashboard and the inbox, never written to OXS for now. Voice
latency: **~1.2 s accepted**; the PRD's 0.8 s is not a target. Ten concurrent
calls: **not a target** while outbound is a manual button; note inbound would
still need it once a number exists. Chatwoot: **two inboxes** planned — one
for resident ticketing, one for staff tasks on ticket resolution; needs
Homies' seats. CRM: no RTL, no login, no daily metrics — acknowledged, still
owed. Monday: **confirmed in the main PRD** (§0 change 5, §5, §6, §10, §11
`staff_tasks`, phase 5, open items 7 and 9) — tasks push to Monday one-way;
still needs their token and board. Outbound: not functional until the number.

**Decided 25 Aug, and the order it happens in.** Outbound is a **Call button
per resident on `/debts`** — a person presses, the agent rings that one
resident, nothing auto-dials (feature 15, built). **Transcript only**: recording
is off on all four assistants and the deploy scripts keep it off. The
no-repeat / do-not-call / calling-hours rules are a later follow-up. To make
the button live: (1) the owner orders the Israeli number from Omnitelecom —
the list is in memory and in `docs/`; (2) create the BYO SIP credential and
phone number in Vapi, copy its id; (3) set `CALL_PIN`, `VAPI_PRIVATE_KEY` and
`VAPI_PHONE_NUMBER_ID` in Vercel. Until (3) the column reads "no number yet".
The first real press is also the first real test of the end-of-call writer on
a phone call: check that `attempts` moves and the call lands under Calls.

0. **Place one web call in each language, on the new account.** Nothing has been
   called since the promotion — the assistants are verified identical and the
   balance is verified in credit, and neither of those is a call. The intake
   agent is the one to try: it gained a ladder, follow-up questions and a fourth
   tool today, and none of it has been heard out loud.
1. **Test the chatbot on a real handset.** Both 13 Aug changes are **deployed**
   — `debt-tools` v17 ACTIVE, WhatsApp workflow updated and still active — and
   smoke-tested against the live function. What has *not* happened is a real
   WhatsApp conversation through them: a balance with nothing given / a name
   only / a mismatched pair / a correct pair, and a report from a real address,
   a real street at a wrong number, an invented street, and a flat past the end
   of a building.
2. ~~Deploy the demo page.~~ **Done 18 Aug** — build `2026-08-12b` is live, with
   `gender_forms` and the spelled-out email, which also closed the English debt
   twin's unresolved `{{gender_forms}}`. **Redeployed 19 Aug**: the page used to
   start *every* agent with the picked person's full debt file, so the intake
   agent was answering the phone holding a debtor's building and apartment. It
   now sends the intake agent one variable — `caller_phone` — and nothing else.
3. **Attach `get_request_status` and `get_balance` to the intake agent, or cut
   the prompt sections that call them.** The prompt has taught both since the
   Edge Function shipped; the assistant carries three tools and neither is one of
   them, so the agent is told to call something that is not there. `vapi_tools.py`
   still justifies their absence with "this project has no read path", which
   stopped being true in early August. This is the 5 Aug failure shape — the
   caller asks, the agent has nothing to call, and the answer is invented. Both
   twins, Hebrew and English. **The intake agent now carries six tools** —
   `add_request_detail`, then `get_request_status` and `get_balance`, all
   19 Aug — so `verify_address` is the only gap left in that list.
4. Fix the remaining data defect (the 2022 debt stamped `2026-08`).
5. Schedule the sync — `oxs_debt_sync.py` nightly, plus a pre-flight debt
   check immediately before any call, so nobody is chased for something they
   paid yesterday.
6. Send Omnitelecom the SIP routing request; they already carry the line, so
   this is a routing change rather than a purchase.
7. Wire Chatwoot into the message path.

## Pending on other people

- `OXS_KEY_REQUESTS` to be re-issued Read-Only on the OXS side.
- ElevenLabs key in Vapi, if that voice is wanted.
- ~~`scripts/vapi_tools.py` — add `get_request_status` and `get_balance` to
  `INTAKE_TOOLS`.~~ **Done 19 Aug**, along with the missing n8n routes. Both
  verified through the live webhook.
