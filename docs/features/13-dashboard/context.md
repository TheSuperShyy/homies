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

### Empty months are shown, not redirected

A well-formed month nobody owes for renders "Nobody owes for 2026-03" rather
than bouncing to the default. Somebody following a bookmarked or forwarded link
after that month is collected needs to see that it is clear — a silent redirect
would show them a different month's numbers under the heading they clicked.
Malformed input falls back to the default, because that is a typo rather than a
statement about a month.
