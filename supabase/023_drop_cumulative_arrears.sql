-- ---------------------------------------------------------------------------
-- 023 — remove the one cumulative arrears write, so `period` means one thing
-- ---------------------------------------------------------------------------
-- Two importers disagreed about what `charges.period` is. `import_arrears.py`
-- (11 Aug, by hand) writes ONE ROW PER UNPAID MONTH, period = that month,
-- amount = the monthly rate — which is what the dashboard's "months owed"
-- column counts and what the debt agent names on the phone. The nightly
-- `oxs_arrears.py --apply`, which first reached its write on 24 Aug, wrote ONE
-- ROW PER APARTMENT, period = the month it ran, amount = rate × months missing.
--
-- The result on 24 Aug: 534 rows stamped 2026-08-01 for ₪922,901, sitting
-- beside the per-month rows for the same debts — 68 residents holding both,
-- ₪63,614 counted twice, and a figure on a client-facing page that was not
-- the debt. On 1 September the nightly path would have added a fresh
-- cumulative row per apartment on top of August's, and compounded monthly.
--
-- Decided 25 Aug: per-month rows are the meaning; the nightly importer now
-- writes them (and applies the same onboarding / recording-lag corrections the
-- hand importer did). This migration deletes the cumulative rows, precisely:
--
--   * the sweep NEVER chases the current month ("not yet late"), so a 2026-08
--     row cannot have come from the per-month path;
--   * every one of them is source = 'oxs' and status = 'unpaid' — nobody had
--     paid, disputed or waived one (checked before writing this: 0 held);
--   * and they were all created on 24 Aug, which the guard below pins.
--
-- Derived data, re-imported twice a day. Nothing here is a record of a payment.
delete from charges
 where source = 'oxs'
   and status = 'unpaid'
   and period = date '2026-08-01'
   and created_at >= timestamptz '2026-08-24 00:00+00'
   and created_at <  timestamptz '2026-08-25 00:00+00';
