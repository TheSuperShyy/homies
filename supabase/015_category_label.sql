-- 015 — one Hebrew label per category, whoever opened the ticket
--
-- 014 gave imported rows `category_he`, taken verbatim from OXS. A ticket our
-- own agents open has the slug and no label, so a dashboard listing both looks
-- like two systems bolted together: their rows say תאורה and ours say nothing.
--
-- A trigger rather than a change to open_request, because the label is a fact
-- about the slug and not about the caller. Filling it in the tool would mean
-- every future writer has to remember to do the same, and one of them will not.

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
    end;
  end if;
  return new;
end;
$$ language plpgsql;

drop trigger if exists requests_fill_category_he on requests;
create trigger requests_fill_category_he
  before insert or update of type, category_he on requests
  for each row execute function fill_category_he();

-- Rows written between 014 and this migration.
update requests set category_he = null where false;   -- no-op, forces the trigger path
update requests set type = type where category_he is null and type is not null;

comment on function fill_category_he is
  'Keeps requests.category_he in step with requests.type. OXS rows arrive with
   their own wording and are left alone; ours are filled from the slug.';
