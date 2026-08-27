-- Purge every test ticket, on the owner's order (27 Aug 2026).
--
-- The requests table held two populations: 145 rows imported from OXS (real
-- faults, real residents) and 44 rows minted by three weeks of bot testing —
-- WhatsApp conversations from the test number, voice-agent rehearsals
-- (descriptions literally beginning "AI: שלום מדבר מיכאל"), rows titled
-- "בדיקה", and one staff-entered seed from 8 Aug. No real resident has ever
-- reached the bot: the only WhatsApp number wired to it is Meta's test
-- number, and the voice agents have no phone number at all. Everything not
-- imported from OXS is therefore test data by construction.
--
-- opened_via is the discriminator the code itself writes: 'oxs' rows come
-- only from the importer. Surveyed row-by-row before writing this file;
-- the full list is in docs/WORKLOG.md under 27 Aug.

delete from requests where opened_via <> 'oxs';
