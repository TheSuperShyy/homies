-- 031: 'payment' joins the ticket types, and 'complaint' finally gets a label.
--
-- Owner, 15 Sep 2026: "when the person want to have a payment information it
-- should open a ticket as well that this person want to pay". Until now a
-- resident who wanted to pay was a Chatwoot team note only (notify_team,
-- reason payment, since 14 Sep); nobody is dispatched from a note, and the
-- queue staff actually work from is the tickets (the same reason
-- request_standing_order started writing a requests row on 18 Aug). So
-- wanting to pay is now a ticket AND a note, on WhatsApp and on voice.
--
-- 'payment' is OURS, like 'complaint' (025): OXS has no such category and
-- nothing is written to OXS. The row carries the resident's building, unit,
-- their words and the channel; staff read it in the dashboard.
--
-- The label trigger (015) mapped the eleven OXS categories and was never
-- taught 'complaint' when 025 added it, so every complaint ticket has had
-- category_he NULL since 25 Aug. Both labels go in here.

alter table requests drop constraint if exists requests_type_check;
alter table requests add constraint requests_type_check
  check (type is null or type in (
    'plumbing','electrical','lighting','elevator','cleaning','gardening',
    'pest_control','locksmith','fire_safety','maintenance','other',
    'complaint','payment'));

comment on constraint requests_type_check on requests is
  'The eleven OXS dispatcher categories plus complaint (25 Aug) and payment '
  '(15 Sep), both ours. A tool that sends anything else fails here rather '
  'than filing it as other.';

create or replace function fill_category_he() returns trigger as $$
begin
  -- Only when it is missing. An imported row already carries THEIR wording,
  -- and if they ever rename a category theirs must win over this table.
  if new.category_he is null and new.type is not null then
    new.category_he := case new.type
      when 'plumbing'     then 'אינסטלציה'
      when 'electrical'   then 'חשמל'
      when 'lighting'     then 'תאורה'
      when 'elevator'     then 'מעלית'
      when 'cleaning'     then 'ניקיון'
      when 'gardening'    then 'גינון'
      when 'pest_control' then 'הדברה'
      when 'locksmith'    then 'מנעולן'
      when 'fire_safety'  then 'כיבוי אש'
      when 'maintenance'  then 'אחזקה'
      when 'other'        then 'אחר'
      when 'complaint'    then 'תלונה'
      when 'payment'      then 'תשלום'
    end;
  end if;
  return new;
end;
$$ language plpgsql;

-- The complaint rows written since 25 Aug carry no label; give them one.
update requests set category_he = 'תלונה'
  where type = 'complaint' and category_he is null;
