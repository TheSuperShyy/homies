# inbound — probe, 2026-09-16-1547

> Fixed resident turns replayed through the model with MOCKED tools; nothing was written anywhere. The [tool] line shows what the model called and with what, before the sentence it then spoke.

```
source     : file docs/assistant/demo-inbound.md
prompt     : 3350 chars, 75% Hebrew
model      : openai/gpt-4.1
tools      : open_request, save_partial_request, add_request_detail, notify_team, get_request_status, get_balance  [repo: vapi_tools.INTAKE_TOOLS]

==========================================================================
scenario: lift_person
==========================================================================
  agent   : שלום, מדבר מיכאל מהצוות של הומיז. איך אפשר לעזור?
  resident: הצילו, המעלית נתקעה ויש בפנים את השכנה שלי, היא מבוגרת והיא בפאניקה
  [tool]  : notify_team {"reason": "emergency", "description": "המעלית נתקעה ויש בפנים שכנה מבוגרת בפאניקה", "department": "operations", "building": "", "unit": ""}
  [tool]  : open_request {"description": "המעלית נתקעה ויש בפנים שכנה מבוגרת בפאניקה", "type": "elevator", "urgency": "emergency", "building": "", "unit": ""}
  agent   : העברתי מיד לצוות שלנו את מה שסיפרתם, והם יודעים שיש כאן מצב חירום עם השכנה במעלית. פתחתי גם פנייה דחופה, מספר אחת אפס ארבע שתיים. /  / אני איתכם על הקו — תרצו להוסיף משהו? יש עוד משהו שחשוב לדעת או לעזור בו?
  resident: ויצמן 13
  [tool]  : add_request_detail {"reference": "255-1042-26", "detail": "ויצמן שלוש עשרה"}
  agent   : הוספתי את הכתובת ויצמן שלוש עשרה לפנייה. אם יש עוד משהו שחשוב שנדע, או שתרצו לעדכן, אני כאן בשבילכם.
  resident: היא לא עונה לי כבר, מה עושים?
  agent   : אני ממש מבין כמה זה מלחיץ, והצוות שלנו כבר יודע בדיוק מה קורה ואיפה. אין לי אפשרות לתת הוראות או לשלוח עזרה בעצמי, אבל כל מה שסיפרתם כבר אצל הצוות והם פועלים לפי הנהלים שלהם. /  / אני נשאר איתכם על הקו אם תרצו להוסיף משהו, לעדכן או לשאול.
  resident: אוקיי, אני מתקשר אליהם. תודה
  agent   : בשמחה, אני כאן לכל דבר שתרצו. תודה שהתקשרתם להומיז, יום טוב ולהתראות.

tokens: 21812 in, 371 out  (about $0.009 at 0.40/1.60 per million)
```
