# OXS's own debt on the Dialer, and a typed number to call

**Estimate:** 1d
**Depends on:** 23-dialer (the page and the queue), 18-dialer-routing (the agent's figures), OXS API rev 1.10 (live debts)
**Status:** LIVE 25 Nov 2026. PR #26 (`main` `ec2e19f`): function deployed 16:10 UTC, Vercel production READY (redeployed with the function's `TOOL_SECRET`). Migration 044 applied about 16:08 UTC. First full pass done 16:27:37 UTC (11 runs, 0 failed): the Dialer's 490 flats all equal OXS's overdue total. The 22 overdue flats OXS gives no phone are not on it.

## Purpose

The owner, 25 Nov 2026, after the Dialer's amounts were read against OXS: *"i need it to be accurate
and has an option to manually call the input number"*. The page summed our own estimate
(`oxs_arrears.py`: every ended 2026 month with no payment record counted as owed, at the flat's usual
monthly amount), and 57 of its 201 flats matched OXS. 75 owed nothing in OXS at all. A press could
ring someone who owes nothing, and the debt agent would quote the wrong amount.

## Behaviour

1. **What is owed** is OXS's `totalDebt`: overdue, without this month (not late yet). It covers monthly
   payments of every year (a partly paid month for what is left) and open special payments (תשלומים
   מיוחדים: a renovation, a reserve fund). Special payments were 60% of the overdue debt on 25 Nov.
2. **The copy, every 10 minutes** (pg_cron `oxs-debts-sync` -> debt-tools):
   1. one `GET /debts`: every flat that owes, with its payers and totals, into `oxs_debt_flats`. A list
      under half the last one is taken for a broken answer and closes nothing;
   2. for each flat whose totals changed (the ones being dialled first, then the largest), its detail
      `GET /apartments/:id/debts?lean=true`: each month owed and what is left on it (`yearlyVector`),
      and each open special payment;
   3. `oxs_debt_apply` writes them into `charges`: one unpaid row per overdue month, one per special
      payment (`kind = 'special'`, no month, its name in `label`). A row of the flat that OXS no longer
      counts is closed (`paid`), on whichever phone it was. A row in review (disputed, pending_charge,
      waived) keeps its status; the test building's `agent` rows are never touched;
   4. at most one OXS call every 1.5 s (about 40 a minute: OXS allows 60 per key, and the payment link
      a tenant waits for uses the same key), and about 95 s a run;
   5. `oxs_debt_finish`: flats OXS no longer lists, or lists with nothing overdue, have every open row
      closed. When a run ends with no backlog for the first time, every row the old estimate wrote
      (`apartment_ref` empty, source `oxs`) is closed too.
3. **Whose phone a flat's debt is on:** the phone it is on now while OXS still lists it for the flat;
   else the phone the old estimate called (staff keep the number they know); else the first payer,
   renters (the people living there) before owners, a mobile before any other number. The phone's
   largest flat becomes its resident's building and flat (where the payment link and the balance
   lookup look). 22 overdue flats had no phone in OXS on 25 Nov; they are not on the Dialer.
4. **Just before the dialer rings someone** (the tick, after the claim), their flats are read again from
   OXS and written. If they now owe nothing overdue, the lead is skipped as `paid`; else the agent is
   given today's amount. If OXS does not answer, the last copy's figures stand.
5. **The debt agent's figures** (`v_debt_call_queue_person`, unchanged prompt): `months_phrase` names
   the months as before when all are this year's, with the year on each when any is not
   ("נובמבר 2025, דצמבר 2025 ואוקטובר 2026"), then the special payments
   ("..., וגם תשלומים מיוחדים: קרן חירום ושיפוץ לובי"). The amount and breakdown include them.
6. **Balance answers** (`get_balance`, WhatsApp and the phone line): `owed_months` has months only;
   special payments are in `owed_special` (label, amount, flat), absent when there are none.
7. **The Dialer page:**
   - the amount cell: the total, then "N months · range" (earlier years included), then
     "N special payments · ₪X" with their names in the tooltip;
   - under "מי חייב": where the amounts come from and when they were read; before the first full
     pass, how many flats are left; after 45 minutes without a run, a red note;
   - **"חיוג למספר"**: a number in any form. Its flats are found in `oxs_debt_flats` (the number as
     any payer OXS lists), read from OXS at the press and put on that number; then it is queued like
     a row's Call, with the same rules (hours, once a day, 4 tries, do-not-call). A number with nothing
     overdue in OXS is not queued ("אין חוב בפיגור ב-OXS"); an OXS error says so; a non-Israeli
     number is refused;
   - the month filter shows the 12 newest months.
8. **No more estimate:** the GitHub OXS sync runs residents and maintenance requests only, and
   `oxs_arrears.py --apply` refuses.

## Interface

- debt-tools messages (with `x-homies-secret`):
  - `{"message":{"type":"oxs-debts-sync"}}`: starts a run and answers at once; with `"wait": true`
    it answers with the run's summary (counts only).
  - `{"message":{"type":"oxs-debts-phone","phone":"+972…"}}`: the typed number's refresh; answers
    `{ok, flats, owed, name?}` or `{ok: false, error}`.
- Database (044), service role only: `oxs_debt_lease(int)`, `oxs_debt_seen(jsonb, timestamptz)`,
  `oxs_debt_apply(jsonb)`, `oxs_debt_finish(timestamptz, boolean, int, int, int, text)`.
- Dashboard: server action `callTyped` -> `lib/dialer-queue.ts` `callNumber()`, outcomes
  `r=badnumber|nodebt|oxs` (and `queued`, `hours` as before), `p` the local number.
- `scripts/oxs_debts_setup.py`: read-only state, `--apply`, `--run [N]`, `--check`, `--off`.

## Data

- `charges`: `kind` ('monthly' | 'special'), `label`, `apartment_ref` (the flat's OXS id); `period`
  may be empty for a special payment only (check constraint); unique `(apartment_ref, oxs_ref)` for
  special payments.
- `oxs_debt_flats`: one row per flat OXS listed (payers, phones, totals, fingerprint, the phone its
  debt is on, when its months were last written). `oxs_debt_state`: the last run, the backlog, the
  first full pass.
- `payment_links`: a voice row may carry no month (a tenant who owes only a special payment).

## Acceptance

1. After the first full pass, `oxs_debts_setup.py --check`: every flat on the Dialer equals OXS's
   overdue total, none is shown that is not overdue in OXS, and the only OXS flats missing are the ones
   with no phone.
2. A press on someone who paid since the last copy is skipped as `paid`, without ringing.
3. A typed number that owes in OXS is queued; one that owes nothing gets "אין חוב בפיגור ב-OXS".
4. A debt call to a tenant with a special payment names it after the months; a balance answer lists it
   by name and never as a month.
