# 13 — Dashboard · context

Why the dashboard is shaped the way it is, and what was rejected. `feature.md`
is what it does; this is why. Chronology lives in `docs/WORKLOG.md`.

## The month filter on Debts — 11 Aug

Asked for as *"a filter on how much debt does each tenant have for each month,
since the current dashboard only shows a total"*, with the reason attached:
collection calling is worked month by month. The page as built answered "who
owes the most, ever", which is not the question somebody picks up the phone to
ask.

### Three shapes were on the table

**Month tabs filtering the list** — chosen. One month, one chase list; the
`Owed` column is that month's amount. It matches the unit of work, and it is
the only one of the three that makes the page smaller rather than larger.

**A month-by-month grid**, one column per month with the total at the end.
Everything visible at once and nothing to click. Rejected: seven columns today
and one more every month, so the table outgrows the screen by design, and the
number a caller actually needs is buried in a row of dashes.

**Tabs plus a per-row breakdown** — the month's amount alongside the other
months that resident owes. Rejected as the first version, not as an idea: it is
the natural next step once somebody has used the filter and says they want the
history of the person they are about to call. Better to add it on evidence than
to guess the columns now.

### Filtering in the page, not in Postgres

The existing query already pulls every open charge with its resident in one
round trip — about 400 rows — and the page groups them. The filter rides on
that same query.

Pushing the filter into Postgres with `.eq('period', …)` was rejected for
buying nothing at this size while costing two things: a second query purely to
learn which months exist for the tabs, and a second code path, since `all`
still has to group in memory. A `v_debt_by_month` view was rejected on the
reasoning already in the page — a migration is more moving parts than a page.

Both become right if the charge table stops being small. The line to watch is
PostgREST's 1,000-row default, which the current ~400 open charges sit under;
crossing it silently truncates the page, so that is the point to move the
filter into the query rather than a moment to rediscover this decision.

### The default month, and the defect that changed it

The design said the page should open on the newest month carrying debt. The
database said that month is `2026-08` — one resident, ₪1,500 — because the 2022
legacy debt is stamped with the current month by a sync that had no month to
use. The design would have shipped a landing page showing one phantom debtor
while 106 people owed for July.

The fix was not a special case for that row. Homies already holds that arrears
are months which have *ended* with nothing paid against them, and that the
current month is never chased — the same rule `oxs_arrears.py` computes on. The
default is therefore the newest completed month, which is right on its own
terms and happens to route around the defect. When the month stamp is fixed
this rule needs no revision.

The `2026-08` tab still renders and is still linkable. Hiding a row because it
is wrong would leave the dashboard disagreeing with the database, which is a
worse failure than an odd-looking tab.

### A row became an apartment — 11 Aug

Asked for straight after the month filter shipped: *"I can see that residents
have multiple apartments, so I can't really resolve that. I want to know what
apartment isn't paid yet and how much."*

The page could not answer it, and no amount of page work would have. The debt
for the second flat was not hidden by the query — it was **absent from the
database**. `residents.phone` was unique and `charges` was unique on
`(resident_id, period)`, so `import_arrears.py` hit its own `do update set
amount = excluded.amount` on the second apartment and overwrote the first
instead of adding to it. Measured before touching anything: two owners, two
invisible apartments, **₪6,665.40** missing from a reported ₪94,854.30.

### Why the apartment went on the charge

`residents.phone` unique is load-bearing in a way that is easy to underrate.
Every identity path in the system starts from a phone: `get_balance` on
WhatsApp, the n8n memory window, `v_conversations`. Keying residents on
`(phone, unit)` would have made all of them return several rows, which turns a
balance question into a disambiguation in the middle of a call — for a gain the
other option also delivers.

Putting the apartment on the charge costs one column and no lookups. What made
it cheap was checking first: every write tool keys off the `charge_id` the
campaign runner attached to the call, never off `(resident, period)`, so the
constraint beneath them could change without one of them noticing.

Rejected: patching the two rows by hand. It would have shown the right total
that afternoon and re-collapsed on the next import, which is the kind of fix
that costs more the second time it is discovered.

### Two things the pre-flight caught

Neither was part of the task, both were in the statement being rewritten.

**Nine settled charges would have been resurrected.** `import_arrears.py` ended
its upsert with `status = 'unpaid'`, so re-running it would have reopened nine
debts that `oxs_debt_sync.py` had marked paid — against real people. The import
now leaves `status` alone: the arrears file is a snapshot from one sweep, not
evidence that a settled debt is open again.

**Every real charge claimed to be fictional.** All 173 carried
`source = 'seed'` while their residents correctly said `oxs`, because the
column defaults to `'seed'` and the import never set it. Migration 007 exists
to make `source` the thing every destructive query filters on — so the entire
arrears list was one purge away from deletion *by a query written to be
careful*. Now `oxs`, scoped to charges whose resident came from OXS so a future
seeded fixture stays seed.

### What the agent says now

Identified by building+apartment, `get_balance` answers for that apartment
alone. Identified by phone or name, it answers for everything they own and
splits it under `owed_apartments`. An owner of three flats asking "how much do
I owe" means all three; the same owner asking about 601 does not.

Months are summed across apartments rather than listed twice, because "April,
and also April" is not a sentence to read back to somebody.

There is also a lookup that would have quietly broken: voice has no caller ID
and finds people by building+apartment against `residents.unit`, which now
names only one flat. The caller from the second flat had to be found through
their charge instead, or an owner would have been reachable under one of their
apartment numbers and invisible under the other.

### The owner view, and the problem the apartment split created — 11 Aug

Asked immediately after: *"How about for the people that own multiple
apartments and have debts on those apartments — how can I see that without any
issues?"*

Splitting rows per apartment answered "what does this flat owe" and quietly
broke "what does this person owe". Rows sort by amount independently, so one
owner's flats scatter — the ₪5,572 one third on page one, the ₪1,838 one on
page two — with nothing marking them as one phone call worth ₪7,409.60.

Fixed with both halves rather than either:

- `?by=owner`, one row per resident, flats merged and months deduped. This is
  the view for deciding what to say on a call.
- A marker on the apartment rows naming the owner's other flats and their
  combined total, so the apartment view cannot mislead even when nobody
  toggles.

The toggle alone was rejected because the default view would still have been
wrong-by-omission for anybody who never found the switch. The marker alone was
rejected because reading an owner's position off two rows on two pages is work
the page should have already done.

The cards are computed from the apartment grouping in both views on purpose. A
`Total open` that moved when you changed how rows were grouped would look like
a discovery rather than a rendering choice.

### Empty months are shown, not redirected

A well-formed month nobody owes for renders "Nobody owes for 2026-03" rather
than bouncing to the default. Somebody following a bookmarked or forwarded link
after that month is collected needs to see that it is clear — a silent redirect
would show them a different month's numbers under the heading they clicked.
Malformed input falls back to the default, because that is a typo rather than a
statement about a month.
