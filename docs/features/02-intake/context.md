# 02 — Intake — context

## Why this exists

Nineteen staff take these calls today. The call itself is nearly all of the
work — the resident describes a problem, someone types it, someone else is
dispatched. If an agent can produce a row as good as the one a human types, the
call centre stops being the bottleneck at ~200 buildings. If it produces a row
that is *nearly* as good, dispatchers stop trusting any of them and phone every
caller back, and the system is worse than nothing.

## Decisions

**The description is the caller's words, not a summary.** Dispatchers read
descriptions to decide who goes and when. "Plumbing issue" tells them nothing;
"leak from the ceiling, two days now" tells them it is not an emergency but is
getting worse. Summarising is where a language model quietly destroys the
information the row exists to carry.

**Type is inferred and only confirmed when ambiguous.** Every confirmation costs
a turn, and turns are what make an automated call feel worse than a human one.
The whole point is not sounding like a phone tree. We accept occasional wrong
categorisation on genuinely ambiguous cases; we do not accept a menu.

**Urgency is inferred, never asked.** Asking a caller how urgent their problem
is has one answer, always. The signal is in how they describe it, not in what
they claim when prompted.

**Read-back happens once, at the end, in one sentence.** Field-by-field
confirmation is the single most common way voice agents become intolerable. One
sentence covers the fields where an error is expensive — location and
substance — and leaves the rest.

**A correction updates the row rather than opening a second one.** Duplicate
tickets are the failure mode that makes dispatchers distrust an automated queue
fastest, because they cannot tell which of two near-identical rows is current.

## Constraints

- `requests.description` and `requests.type` are `not null` today, which is why
  a partial call cannot use this path at all and needs
  [07-partial-ticket](../07-partial-ticket/feature.md).
- `reference` comes from a Postgres sequence with a column default. The agent
  cannot invent one, cannot predict one, and must read back exactly what the
  tool returned.
- The four types — plumbing, electrical, cleaning, other — are a guess. Homies
  has not confirmed its real categories.

## Known failure modes

- **Over-summarised description.** Watched for explicitly in Act 2. The
  correction is prompt-level, not architectural.
- **Confident wrong type.** Worse than a null type, because it routes the
  request to the wrong trade and nobody re-reads it. Acceptance criterion 6
  exists for this.
- **Duplicate rows from a mid-call correction.** Guarded by tracking the
  `request_id` returned on first write and updating it.
- **Caller describes three problems at once.** Belongs to
  [06-boundaries](../06-boundaries/feature.md); intake must not silently write
  only the first.
- **A resident expects a visit time.** The agent cannot promise one and must not
  imply it. Scheduling needs dispatcher data we do not have.

## Open questions

- What are Homies' real request categories? Ours are invented. Settled by the
  OXS export or by asking directly, and worth asking before the demo — ops staff
  will notice immediately if the categories are wrong, and it is the kind of
  detail that makes the whole thing look unresearched.
- Should `unit` be required when the request is about a common area? A lobby
  leak has no apartment. Currently nullable, which handles it; confirm in Act 2
  that a null unit reads correctly to a dispatcher.

## Related

[The demo design](../../specs/2026-08-02-demo-design.md) ·
[01-identity](../01-identity/feature.md) ·
[07-partial-ticket](../07-partial-ticket/feature.md) ·
[001_slice_schema.sql](../../../supabase/001_slice_schema.sql) lines 79–106
