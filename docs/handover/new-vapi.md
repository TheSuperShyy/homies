# Rebuilding on a new Vapi account

Everything the agent is lives in this repo. Vapi holds a *copy* that was pushed
from here, so moving to another account is a rebuild, not a migration — you run
the same scripts against a different key and then fix the ids that other files
point at.

Read this once before starting. The rebuild itself is about fifteen minutes; the
part that goes wrong is step 6, and it goes wrong silently.

## What is actually stored where

| | Source of truth | Vapi's copy |
|---|---|---|
| Both debt prompts | `docs/features/10-debt-followup/prompt.md` | pushed by `vapi_sync.py` / `vapi_en.py` |
| The eight tools | `scripts/vapi_tools.py` | pushed with the assistant |
| Voice, transcriber, endpointing, end-call phrases | `scripts/vapi_sync.py` (`BASE`, `TARGETS`) | pushed with the assistant |
| The spoken-output filter | `scripts/voice_guard.py` | pushed as `voice.chunkPlan.formatPlan.replacements` |
| Inbound demo prompt | `docs/assistant/demo-inbound.md` | pushed by `vapi_sync.py inbound` |
| Resident data | the Google Sheet | never stored in Vapi |
| Tool execution | n8n → Apps Script | Vapi only holds the webhook URL |

**Nothing of value is only in Vapi.** `docs/handover/vapi-export.json` is a
record of what the account held on the day it was written — regenerate it with
`python scripts/vapi_export.py`. It cannot be pushed back: Vapi mints new ids on
create, so the export is for reading, not restoring.

`docs/handover/vapi-export-old-account.json` is the same file taken from the
previous account immediately before the 5 Aug migration, kept because
`vapi_export.py` writes to a fixed path and would otherwise have overwritten the
only record of what was there — including the free number's id and the two
assistants that were not rebuilt. **Archive the old export by hand before
re-running the export on a new account.**

## What does not come across at all

- **Call history, transcripts and recordings.** They stay with the old account.
  Export anything you still need *before* you stop paying for it — recordings are
  deleted after 14 days regardless.
- **The free phone number** (`Homies test (free)`, US, used only by
  `vapi_duel.py` for assistant-to-assistant calls). A new account gets its own.
- **The eval suite.** Recreate with `python scripts/vapi_eval.py --setup`.
- **Anything edited in the dashboard and never written back here.** The model was
  set to `gpt-5.5` by hand on 3 Aug and later captured in `vapi_sync.py`; if you
  have changed anything else in the dashboard since, it exists nowhere else and
  the rebuild will quietly not have it. Diff the new assistant against
  `vapi-export.json` if you are unsure.

## The rebuild

**1. Create the account** and copy both keys from Dashboard → Organization →
API Keys. You need the **private** key for the scripts and the **public** key for
the browser page.

**2. Put the private key in `.env`.** Never on a command line, never in chat:

```
VAPI_PRIVATE_KEY=<the new private key>
```

**3. Push the Hebrew assistant.** It creates by name when nothing matches, so
this is the same command that updates it:

```
python scripts/vapi_sync.py debt          # dry run — read this before applying
python scripts/vapi_sync.py debt --apply
```

Write down the id it prints.

**4. Build the English twin.** It reads the *live* Hebrew assistant, so before
running it, put step 3's id into `SOURCE` in `scripts/vapi_en.py` — it is listed
in step 6 with the other ids, but this one cannot wait until then. On the wrong
key it fails cleanly with a 404; on a *stale but valid* key it would silently
build the twin from the old account's prompt.

```
python scripts/vapi_en.py --create
```

Write down that id too. If it stops with *"Update the table in this file before
creating anything"*, a Hebrew fixed string has changed and has no English
translation — fix the table in `vapi_en.py` rather than forcing it, because a
half-translated prompt is worse than none.

**5. Optional — the inbound demo assistant:**

```
python scripts/vapi_sync.py inbound --apply
```

**6. Repoint everything that hardcodes an id.** This is the step that breaks
things, because a wrong id does not error — it starts a call with the wrong
agent, or an agent that no longer exists.

| File | What to change |
|---|---|
| `web/index.html` | `ASSISTANTS.he`, `ASSISTANTS.en`, **and the public key** |
| `scripts/vapi_en.py` | `SOURCE`, line 29 |
| `scripts/vapi_call.py` | `ASSISTANT_ID` and `PHONE_NUMBER_ID`, lines 29–30 |
| `scripts/vapi_duel.py` | `MICHAL_ASSISTANT` and `MICHAL_NUMBER_ID`, lines 39–40 |
| `scripts/vapi_eval.py` | `MICHAL_ASSISTANT`, line 55 |
| `scripts/vapi_mock.py` | `SOURCE`, line 39 |
| `web/README.md`, `docs/assistant/*.md` | the ids quoted in prose |

Find them all with:

```
grep -rn "0ef11cb5\|eaa390ec\|51bbe77a\|ce1a1da7" --include=*.py --include=*.html --include=*.md .
```

Replace the old ids with the new ones. Those four are the current values as of
the 5 Aug migration — Hebrew, English, inbound, public key. The previous
account's were `56935b35`, `731193bf`, `a594a4ce` and `27382abf`; grep for those
if something still points at the old account.

**A phone number is not on that list because there is nothing to repoint it to.**
The free US number stayed behind, so `vapi_call.py` and `vapi_duel.py` now hold
an empty `PHONE_NUMBER_ID` and refuse to dial with a sentence explaining why.
Web calls from `web/index.html` need no number and were unaffected.

**7. Verify before trusting it.** In order, because each step assumes the last:

```
python scripts/vapi_export.py --show      # both assistants exist, right names
python scripts/check_tools.py             # eight tools answer, writes land
python scripts/vapi_leak_check.py 20      # nothing spoke its own machinery
```

Then place one web call from the page and confirm all four of:

- it identifies the resident from the sheet, not the built-in fallback
- it never mentions a card
- it never says a tool name, a field, or anything with an underscore in it —
  `vapi_leak_check.py <call-id>` prints the whole transcript with any hit
- a row appears in `payment_links`
- a row appears in `call_outcomes` — if this one is missing, the closing ended
  the call before the outcome was logged, which has regressed before

## The rest of the system, which is not Vapi's

A new Vapi account changes nothing here, but if the whole thing is being moved,
these are the other four pieces:

| Piece | Where it lives | Moving it |
|---|---|---|
| Tool routing | n8n workflow `Homies — debt tools (Vapi)` | `python scripts/n8n_deploy.py --apply --activate` against the new instance |
| Call queue read | n8n workflow `Homies — call queue (read)` | `python scripts/n8n_queue.py --apply --activate` |
| Data + tool writes | Apps Script bound to the residents sheet | paste `sheets/Code.gs`, redeploy, copy the new `/exec` URL into `.env` and both n8n scripts |
| Test console | `web/index.html` | static file; re-upload wherever it is served |

If the n8n instance changes as well, the webhook URL changes, and **that** has to
go back into `scripts/vapi_tools.py`'s server URL and be pushed to Vapi again —
otherwise the new assistants call the old instance and every tool silently writes
to the wrong place.

## Two things that are wrong today and should not be copied forward

- **The n8n webhook takes no secret.** The assistants send
  `x-homies-secret` and it is empty, so anyone who finds the URL can write rows.
  Set `N8N_WEBHOOK_SECRET` in `.env`, check it in the workflow's Code node, and
  re-push the assistants.
- **The Apps Script secret travels in the query string** and is committed in
  `sheets/Code.gs`. Acceptable only because the ten residents are fictional.
  Before a real Homies row goes in, regenerate it *and* move off Apps Script.
  Those are the same moment, not two chores.
