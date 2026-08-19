# HANDOVER — Homies, everything you need to take over

**Current as of 2026-08-18.** If you have just been told "read the handover",
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
hit **n8n** at `/webhook/homies-whatsapp`, which verifies the Meta signature,
dedupes on `wamid`, detects language, and runs an AI Agent on OpenRouter with
a 30-turn memory keyed by phone.

**One writer, reached three ways.** Every write goes through the Supabase Edge
Function `debt-tools` (13 handlers, `--no-verify-jwt`, authenticated by
`TOOL_SECRET`). Voice tool calls route via n8n `/webhook/homies-debt-tools`;
the end-of-call report and the two read-only tools (`get_balance`,
`get_request_status`) go straight to the Edge Function. Every write opens an
`interactions` stub first, so nothing is orphaned.

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

**The dashboard.** Next.js 14 on Vercel at `homies-dashboard.vercel.app`.
Pages: overview, tickets, debts, conversations, calls, call detail. Anon key,
no login since 9 Aug, read-only except `requests.status`. Paging is
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
| OXS → Supabase import | works; twice-daily workflow written, not yet committed |

**Does not exist:**

- **A real phone number.** No `phoneNumberId` on the Vapi account. Needs the
  four Omnitelecom values — gateway host/IP, SIP username, SIP password, DID
  in +972 E.164 — and Homies' company registration documents, which are the
  long pole. Ask whether the trunk runs over the public internet before
  paying; a dedicated line cannot reach Vapi.
- **Payment link delivery.** `send_payment_link` writes a row and stops. OXS
  exposes no payment-link endpoint, so the link still comes from OXS itself.
- **Chatwoot in the message path.** It runs and owns the number; it is not
  wired to the bot.
- **A running scheduler.** `.github/workflows/oxs-sync.yml` exists — residents,
  arrears and requests at midnight and 15:00 Israel time — but `.github/` is
  untracked, so nothing fires until it is committed to `main` and the six
  repository secrets are set. Every other import is still run by hand.
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

| | now live | retired |
|---|---|---|
| Keys | `VAPI_PRIVATE_KEY` / `VAPI_PUBLIC_KEY` (account 6, live 19 Aug pm) | `VAPI_*_KEY_ACCOUNT7` (the old account 4), `_ACCOUNT5` |
| Debt (he) | `8f927b15-a02f-436d-a87d-acf23abecb9b` | `9e2034d1-…`, `489aa39c-…` |
| Debt (en) | `cc8e43b4-be81-46c4-9772-893ee2a0c98a` | `41d370b2-…`, `3b0e384d-…` |
| Intake (he) | `12a4c01d-85ac-4955-a195-ed4c42b09927` | `f482abc1-…`, `7813da25-…` |
| Intake (en) | `9cae6bf7-0ac6-45eb-ad66-dcca018cb710` | `8b98016b-…`, `9ed5e788-…` |

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
homies-voice-demo.vercel.app — the deployed page is build `2026-08-12a` but
carries the account-5 ids, so it reaches the rebuilt twin. **`vapi_en.py intake
--dry` is the health check**; it exits loudly whenever a Hebrew fixed line
changes, and the fix is always the table, never the check.

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
and apartment only after the yes. Warmth is now explicitly confined to the
sentence and never the fact — see the rule in `CONTEXT.md` — so refusals, the
reference-number handover and a failed identity check are all phrased like a
person while the checks behind them are unchanged. Ungendered second person
throughout: `גרים`, never `אתה גר`. Deployed and **not yet tested on a real
handset.**

**Changed 12 Aug, and worth knowing before you read a transcript:**

- **The WhatsApp bot has no name.** It is Homies' support desk, not מיכאל, and
  it will not invent a name if asked. Self-reference stays masculine — that is
  Hebrew verb grammar, not a persona. The **voice** agents are still מיכאל.
- **The bot answers in Hebrew unless English is explicitly requested** (the
  menu row, or the word). Script detection was removed: a Latin-letter
  reference number was flipping Hebrew conversations to English.
- **The voice agents read out only the tail of a reference** — `1, 0, 0, 1`,
  not `HM-2026-1001`. Lookup matches on the tail. The WhatsApp bot still quotes
  the reference in full, because there it is copied text rather than speech.

---

## The data, as it stands

- **7,391 residents** — real names, real E.164 mobiles, across 173 active
  buildings. All carry `handed_over = false`, so **`v_debt_call_queue` is
  empty and nothing can dial**. A person must flip that flag before any
  campaign. This is the safety interlock; do not remove it casually.
- **122 apartments owing ₪101,519.70, held by 120 residents** — one charge per
  apartment per unpaid month across 2026-01 → 2026-07. July is 108 apartments
  and 106 people, tapering to 4 owing January. Apartments and residents are
  different numbers and the dashboard counts both.
- The one legacy row — ₪1,500, a 2022 balance, and the only thing OXS's
  `/debts` endpoint reports for the entire company — was **deleted 17 Aug**.
  178 charges, ₪100,020 open, all of it 2026 arrears.
- Zero demo or synthetic rows; both were purged on 10 Aug. Every charge carries
  `source = 'oxs'` — until 11 Aug they all said `'seed'`, which is the flag
  every destructive query filters on.

### Known defects — six still open, sixteen fixed and kept for the record

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
6. **A common-area ticket keeps an apartment number if the resident offers
   one.** A stuck-lift ticket came out with `unit = 12`. The bot correctly
   never asked, but `check_whatsapp.py` asserts common-area faults carry no
   unit, so the contract and the row disagree and a dispatcher is misled.
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
| Vercel | `VERCEL_TOKEN` |
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
2. **Payment proof by WhatsApp or email?** The dispute path sends residents to
   `{{verification_email}}`; Israelis default to WhatsApp screenshots. An
   office-intake decision, not a prompt change.
3. **Meta/WhatsApp ownership** — if the number is to be Homies', they must
   grant Business Manager access rather than hand over a login.
4. **Chatwoot seats** — how many users, names and emails, which inboxes.

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
