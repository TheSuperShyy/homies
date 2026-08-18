-- 020 — our ticket numbers take Homies' shape, not ours
--
-- Asked for on 18 Aug: "the creation of ticket it should match the homies
-- format not the HM". Same instruction as 12 Aug's categories, one field
-- further on — a resident should not be able to tell from the number which
-- door they came through, and a dispatcher should not have to learn two
-- vocabularies to read one screen.
--
-- THEIR SHAPE, MEASURED
-- All 34 imported calls read `255-NNNNN-26`:
--
--     255      their code for Homies. Constant across every record.
--     NNNNN    a running serial. 19502 on 10 Feb, 26372 on 12 Aug —
--              monotonic with date, portfolio-wide, never reset.
--     26       the year, two digits.
--
-- Ours was `HM-2026-1001`: our own prefix, four-digit year, sequence tail.
-- Nothing about it was wrong except that it was visibly not theirs.
--
-- THE COLLISION, AND WHY THE BAND IS FOUR DIGITS
-- OXS owns that serial and we cannot reserve one: their API is twelve GET
-- endpoints, so there is no number to ask for and no way to claim one. Minting
-- into their live range would eventually mean two different tickets carrying
-- one number — and worse than a clash, `requests.reference` is unique and
-- `oxs_requests_sync.py` upserts on it, so the day their counter reached one of
-- ours their call would silently overwrite our row.
--
-- So we mint BELOW them, permanently. Their counter was already five digits
-- (19502) in February and only climbs; a four-digit serial is behind them for
-- good and cannot be caught. The sequence continues from where HM- left off —
-- 1047 next — so no number is ever issued twice even across the format change.
-- The check constraint below is what stops a later hand from widening the band
-- back into their range by accident.

alter table requests
  alter column reference set default
    '255-' || lpad(nextval('request_reference_seq')::text, 4, '0')
           || '-' || to_char(now(), 'YY');

comment on column requests.reference is
  'Human-quotable ticket number, in OXS''s shape: 255-NNNN-YY. 255 is their
   code for Homies and the year is two digits, both copied from their format so
   ours and theirs read alike. Our serial stays four digits BELOW their live
   five-digit counter, because the column is unique and the OXS sync upserts on
   it — a collision would overwrite their ticket with ours. Rows before 18 Aug
   carry the old HM-YYYY-NNNN and are left as issued: a number told to a
   resident is not rewritten behind them.';

-- The sequence never goes backwards, so this only ever fails on a deliberate
-- widening. Scoped to rows we mint: imported rows carry their taskNumber
-- verbatim and legitimately sit in the five-digit range.
alter table requests drop constraint if exists requests_reference_band;
alter table requests add constraint requests_reference_band
  check (
    opened_via = 'oxs'
    or reference !~ '^255-'
    or reference ~ '^255-[0-9]{4}-[0-9]{2}$'
  );
