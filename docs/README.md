# Homies — documentation

Everything that describes what we are building and why. Code lives elsewhere;
this directory is the argument for the code.

## Layout

```
docs/
├── README.md                      you are here
├── WORKLOG.md                     what was done, decided and found, by date
├── assistant/                     what is actually live in Vapi
│   ├── demo-inbound.md            week-3 intake assistant: config, prompt, tools
│   └── debt-followup.md           outbound collection assistant: config only
├── features/                      one folder per shippable unit
│   ├── _template/                 copy this to start a new feature
│   ├── 01-identity/
│   ├── 02-intake/
│   ├── 03-recall/
│   ├── 04-interruption-pacing/
│   ├── 05-messy-input/
│   ├── 06-boundaries/
│   ├── 07-partial-ticket/
│   ├── 08-instrumentation/
│   ├── 09-sheets-mirror/
│   └── 10-debt-followup/          outbound — release 2, not the week-3 demo
├── specs/                         designs, one per milestone
│   └── 2026-08-02-demo-design.md  the week-3 demo
├── prd/                           what we told the client we would build
│   ├── Homies-PRD-v2.md           current
│   └── archive/Homies-PRD-v1.md   superseded, kept for the diff
├── discovery/                     what the client told us
│   ├── Homies-Clarifying-Questions.md
│   ├── Homies-Clarifying-Questions-GDocs.txt
│   ├── Homies-Feature-Clarification.txt
│   ├── homies.txt                 the original scoping note
│   ├── call-transcripts-extracted.txt   4 real collection calls, English column
│   └── source/                    originals, untranslated and translated
├── diagrams/
│   ├── Homies-Call-Flow.excalidraw       what a resident experiences — show this one
│   ├── Homies-Debt-Followup-Flow.excalidraw  outbound collection (release 2)
│   ├── Homies-Gantt-Simple.excalidraw    the 6-week phase chart
│   ├── Homies-Inbound-Flow.excalidraw    inbound voice flow (stale — see below)
│   └── gen_*.py, check_*.py              regenerate and validate the two flows
└── reference/
    ├── Homies-Build-Stack-Checklist.md
    └── Homies-Vapi-Account-Notes.md   cost, retention, account state
```

Schema and seed data are not here — they are executable and live in
[supabase/](../supabase/). The assistant is pushed to Vapi by
[scripts/vapi_sync.py](../scripts/vapi_sync.py), which reads
[assistant/demo-inbound.md](assistant/demo-inbound.md) directly — so that
document is the assistant, not a description of it.

`Homies-Inbound-Flow.excalidraw` still shows the bot deleting payment information,
which is a flow we decided against. Do not show it to anyone until it is
regenerated.

The direction of the top three folders is worth noticing: **discovery** is what
the client said, **prd** is what we committed to, **specs** and **features** are
what we are building. A disagreement between any two of them is a real problem,
and having them adjacent is what makes it findable.

## The two-file rule

Every feature folder holds exactly two documents, and they answer different
questions for different readers.

**`feature.md` — what to build.** Behaviour, tool contract, data written,
acceptance criteria, what is deliberately excluded, estimate. Written so that
someone who has never seen this project can implement it and know when they are
finished. If you are coding, this is the file.

**`context.md` — why it is like this.** The decisions behind the behaviour, the
constraints that forced them, the failure modes we already know about, and the
questions still open. Written so that someone changing this feature in three
months does not re-litigate a settled argument or repeat a solved mistake. If
you are about to disagree with `feature.md`, read this first.

Keeping them apart matters. Mixed together, the rationale swamps the
instructions and the instructions get stale because nobody wants to edit a wall
of prose. Apart, `feature.md` stays short enough to keep current.

Anything else a feature needs — SQL, prompt text, sample transcripts — goes in
its own folder alongside those two files.

## Where the feature list comes from

The nine features are the week-3 demo backlog from
[the demo design](specs/2026-08-02-demo-design.md). They are numbered in build
order, not priority order: identity before intake because you cannot open a
request for nobody, intake before recall because you cannot look up a request
that was never created.

Release-2 work — WhatsApp, the metrics CRM, outbound debt calls, the live OXS
bridge — has no folder yet. It gets one when it gets a design.

## Status

| # | Feature | Est. | State |
|---|---|---|---|
| 01 | [Identity](features/01-identity/feature.md) | 1.5d | not started |
| 02 | [Intake](features/02-intake/feature.md) | 1.5d | not started |
| 03 | [Recall](features/03-recall/feature.md) | 1d | not started |
| 04 | [Interruption & pacing](features/04-interruption-pacing/feature.md) | 2d | not started |
| 05 | [Messy input](features/05-messy-input/feature.md) | 3d | not started |
| 06 | [Boundaries](features/06-boundaries/feature.md) | 2d | not started |
| 07 | [Partial ticket](features/07-partial-ticket/feature.md) | 1d | not started |
| 08 | [Instrumentation](features/08-instrumentation/feature.md) | 1d | not started |
| 09 | [Sheets mirror](features/09-sheets-mirror/feature.md) | 0.5d | not started |

13.5 person-days, plus 1 day of adversarial rehearsal, against the 24 the
[phase chart](diagrams/Homies-Gantt-Simple.excalidraw) budgets for weeks 1–3.

### Beyond the demo

| # | Feature | Est. | State |
|---|---|---|---|
| 10 | [Outbound debt follow-up](features/10-debt-followup/feature.md) | 4d | prompt drafted |

Feature 10 is **Phase 7 work, weeks 6–8** — it is not part of the week-3 demo,
and features 01–09 are written against inbound intake. It was drafted early
because four real collection recordings arrived and the reasoning was worth
capturing while they were fresh. Its prompt is the only spoken-behaviour document
in the repo, and it needs a schema (`004`) that does not exist yet.

## Credentials

None, ever, in this directory or any other tracked file. Keys live in the n8n
credential store, in environment variables, or in a password manager. Three keys
were pasted in plaintext during design and must be treated as compromised until
rotated: Telnyx, Retell, Vapi.
