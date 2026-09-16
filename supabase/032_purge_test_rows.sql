-- 032: the test rows leave the client's view.
--
-- Yariv's review of 15 Sep 2026: the dashboard's counts are inflated by test
-- calls, and the needs_review pile he opened was five stubs reading
-- "בדיקה: שכנה תקועה במעלית ובפאניקה" -- case 5 of scripts/voice_note_test.py,
-- run five times. Every harness here marks what it writes (call ids
-- `test-voice-*` and `probe-*`, the building בדיקת-מערכת, the sender name
-- בדיקת-מערכת, the seed phone +972501234567, descriptions that start with
-- "בדיקה:") and, until 16 Sep, none of them deleted it afterwards. Both
-- harnesses clean up after themselves now; this removes what they left.
--
-- What this does NOT match, on purpose: any phone prefix a real resident
-- could carry. `wa:97250*` was considered and rejected -- it matches the
-- owner's own number. The +972599 prefix IS matched: it is unallocated in
-- Israel and is what the harnesses invent (voice_note_test.py, the WhatsApp
-- probe), never a resident.
--
-- Children first. `messages` cascades on the interaction; the others are
-- `on delete set null` and would survive as orphans.

create temp table _test_interactions on commit drop as
  select id from interactions
   where external_call_id like 'test-voice-%'
      or external_call_id like 'probe-%'
      or external_call_id like 'wa:972599%'
      or caller_phone like '+972599%';

delete from call_outcomes    where interaction_id in (select id from _test_interactions);
delete from payment_links    where interaction_id in (select id from _test_interactions);
delete from payment_tickets  where interaction_id in (select id from _test_interactions);
delete from promises_to_pay  where interaction_id in (select id from _test_interactions);
delete from payment_disputes where interaction_id in (select id from _test_interactions);

delete from requests
 where interaction_id in (select id from _test_interactions)
    or building = 'בדיקת-מערכת'
    or reported_by_phone = '+972501234567'
    or reported_by_phone like '+972599%'
    or description like 'בדיקה:%'
    or description like '%בדיקת-מערכת%';

delete from messages where interaction_id in (select id from _test_interactions);
delete from interactions where id in (select id from _test_interactions);
