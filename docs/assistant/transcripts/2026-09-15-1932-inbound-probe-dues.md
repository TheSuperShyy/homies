# inbound — probe, 2026-09-15-1932

> Fixed resident turns replayed through the model with MOCKED tools; nothing was written anywhere. The [tool] line shows what the model called and with what, before the sentence it then spoke.

```
source     : file docs/assistant/demo-inbound.md
prompt     : 2876 chars, 75% Hebrew
model      : openai/gpt-4.1
tools      : open_request, save_partial_request, add_request_detail, notify_team, get_request_status, get_balance  [repo: vapi_tools.INTAKE_TOOLS]

==========================================================================
scenario: dues
==========================================================================
  agent   : שלום, מדבר מיכאל מהצוות של הומיז. איך אפשר לעזור?
  resident: שלום, אני רוצה לשלם את ועד הבית, יש לי חוב של כמה חודשים
  agent   : בשמחה, אפשר לקבל את שם הבניין או הכתובת והמספר של הדירה? ככה אוכל לבדוק בדיוק כמה נשאר לשלם ולעזור להסדיר את זה.
  resident: הרצל 14, דירה 12
  [tool]  : get_balance {"name": "", "building": "הרצל 14", "unit": "12"}
  agent   : היתרה שלך בוועד הבית היא ארבע מאות חמישים שקלים. רוצה שאסביר איך אפשר לשלם, או שתרצה הסדר תשלומים?
  resident: אז איך אני משלם? אפשר בכרטיס אשראי?
  [tool]  : open_request {"description": "רוצה לשלם את ועד הבית, שואל איך אפשר לשלם והאם אפשר בכרטיס אשראי", "type": "payment", "urgency": "normal", "building": "הרצל 14", "unit": "12"}
  [tool]  : notify_team {"reason": "payment", "description": "רוצה לשלם את ועד הבית, שואל איך אפשר לשלם והאם אפשר בכרטיס אשראי", "department": "collections", "building": "הרצל 14", "unit": "12"}
  agent   : הצוות שלנו כבר יודע שאתה רוצה לשלם ושאלת לגבי אשראי. מספר הפנייה שלך הוא אחת אפס ארבע שתיים. /  / אם תרצה, אפשר להמשיך יחד ולהסביר איך משלמים בכל אחת מהשיטות — אשראי, העברה או ביט. מה הכי נוח לך?
  resident: טוב. מתי מישהו יחזור אליי?
  agent   : הצוות יודע על הבקשה שלך, ואם יהיה צורך הם יחזרו אליך. אפשר להמשיך ולעזור לך עכשיו בכל שאלה או עניין אחר שקשור לוועד הבית או לתשלום. יש עוד משהו שתרצה לדעת או להסדיר?
  resident: בסדר, תודה
  agent   : תודה שהתקשרתם להומיז, יום טוב ולהתראות.

tokens: 22782 in, 409 out  (about $0.010 at 0.40/1.60 per million)
```
