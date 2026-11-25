# OXS's own debt on the Dialer — context

## Why this exists

On 25 Nov 2026 the owner asked whether the Dialer's debt balances were accurate. Read against OXS's
live debts: 57 of the page's 201 flats matched. 75 flats (₪183k on the page) owed nothing in OXS. 18
owed only the current month. 50 differed either way. 749 flats OXS says owe were not on the page. The
owner: *"fym mostly no i need it to be accurate"*.

## Decisions

**OXS's calculation, not ours.** Until OXS API rev 1.10 (read 17 Nov) the debt endpoints read a summary
OXS no longer kept, nearly always empty, so arrears were estimated from payment records. Since rev
1.10 OXS works debt out per flat with its payments screen's rules, which is what the office sees. An
estimate can only drift from that. One traced flat had payment records for 2024, 2025 and November
2026: ten months owed for the estimate, nothing for OXS.

**Overdue (`totalDebt`), not "owed today".** This month is not late yet, and the old estimate never
chased it either. The owner was told this was the recommendation and did not object. `with_month` is
kept in `oxs_debt_flats` should that change.

**Special payments and earlier years count.** OXS counts them, and they were 60% of the overdue total.
Leaving them out would make the page "accurate" only for the monthly payment.

**charges stays the one table every reader uses.** The page, the queue, press_call, the router's
figures, the try counter and get_balance all read charges. Writing OXS's figure there made all of them
right at once. A separate table read by the page alone would have left the agent quoting another
number.

**A special payment is a charge with no month.** OXS gives it no date. A month stamped on it would be
read out as that month by the agent and the balance tool. The views, the try counter and get_balance
were taught the kind, and the payment link's record may carry no month.

**Changed flats only, every 10 minutes, at 40 calls a minute.** One `GET /debts` (about 5 s) sees
every change in totals. Only flats whose totals changed are read month by month. OXS allows 60 calls a
minute per key, and the payment link a tenant is waiting for on the phone uses the same finance key.
The first pass is about 513 flats, roughly six runs.

**Read again before ringing.** A copy up to 10 minutes old is enough for the page, but not for a call:
someone who paid an hour ago must not be rung about it.

**The phone stays the one staff know.** The first pass keeps the number the old estimate called while
OXS still lists it as a payer of the flat. Otherwise renters (the people living there) come before
owners, and a mobile before a landline, because the payment link goes to WhatsApp.

**A typed number moves the flat's debt onto it.** The person being called is the one the call is about.
The agent never guesses whose debt it is; the flat is found only through OXS's own payer list.

**Closed rows are `paid`.** No new status was added. Every reader already treats anything but
`unpaid` as not owed, and `paid` is what the old sync wrote on positive evidence. A row in review is
never touched.

## Constraints

- OXS: 60 calls a minute per key. GET /debts is computed once a minute for paging. A malformed id
  answers 403. `?lean=true` has no monthly total, so the check is months + specials = `totalDebt`.
- Supabase Edge Functions stop a worker at 150 s on the free plan, so a run budgets about 95 s, and
  pg_cron does not wait for it (EdgeRuntime.waitUntil).
- `charges` is unique on (resident, month, flat number) with no building, so an owner with the same
  flat number in two buildings keeps one month row. The write refuses to overwrite a row of another
  flat, so the second flat's month is left out rather than mixed in. Rare.

## Known failure modes

- **OXS down or answering 429:** the run stops, closes nothing, and says so in `oxs_debt_state`. The
  page shows a red note after 45 minutes. The dialer sends on the last copy's figures.
- **GET /debts much shorter than last time:** taken as a broken answer, so nothing is closed.
- **The first of the month:** every flat that did not pay last month changes, so the backlog is a few
  hundred flats for an hour or two. The page says nothing (the copy is complete), and the dialer reads
  each tenant again before ringing.
- **A flat whose detail keeps failing** stays in the backlog. Before the first full pass, that would
  hold back the old estimate's rows. `--run` prints `failed`.

## Open questions

- Whether "owed today" (with this month) should be shown beside the overdue figure. Settled by the
  owner or Yariv looking at the page.
- Whether the bot should read special payments' names aloud as OXS writes them ("הפרש לאחר עליית דמי
  וועד 11/26"). Settled by the first real debt call with one.
