-- Homies — Phase 1 slice seed data
-- Ten mock residents across five buildings, Hebrew names, Israeli mobile numbers.
-- Safe to re-run: upserts on phone.
--
-- Mobile prefixes used are real Israeli ranges (050/052/053/054/055/058) so the
-- E.164 shape matches what Telnyx will actually deliver as caller ID later. The
-- numbers themselves are fictional.

insert into residents (full_name, phone, building, unit, language) values
  ('דוד כהן',      '+972501234567', 'הרצל 14',      '12', 'he'),
  ('שרה לוי',      '+972521234568', 'הרצל 14',      '7',  'he'),
  ('משה מזרחי',    '+972531234569', 'ביאליק 8',     '3',  'he'),
  ('רחל פרץ',      '+972541234570', 'ביאליק 8',     '15', 'he'),
  ('יוסי אברהם',   '+972551234571', 'רוטשילד 22',   '4',  'he'),
  ('מיכל דהן',     '+972581234572', 'רוטשילד 22',   '9',  'he'),
  ('אבי ביטון',    '+972501234573', 'ז''בוטינסקי 5', '2',  'he'),
  ('נועה שפירא',   '+972521234574', 'ז''בוטינסקי 5', '11', 'he'),
  ('איתי גולן',    '+972531234575', 'בן גוריון 30', '6',  'he'),
  ('טל אזולאי',    '+972541234576', 'בן גוריון 30', '18', 'he')
on conflict (phone) do update set
  full_name = excluded.full_name,
  building  = excluded.building,
  unit      = excluded.unit;

-- One pre-existing request so the CRM list is not empty before the first demo
-- call, and so there is something to compare the freshly-created row against.
insert into requests (resident_id, type, description, building, unit, urgency, status, opened_via)
select id, 'plumbing', 'נזילה בצנרת במטבח', building, unit, 'normal', 'in_progress', 'staff'
from residents
where phone = '+972521234568'
  and not exists (
    select 1 from requests r
    where r.description = 'נזילה בצנרת במטבח'
  );
