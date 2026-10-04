# Incoming calls, 4 Oct: talkative, friendly and service-oriented, eight simulated calls

The prompt in `docs/assistant/demo-inbound.md` after the 4 Oct change (the register sentence: a
service rep who loves the job, and service as making the caller feel looked after; the turn length:
two or three short sentences, always room for a warm word, still one question a turn), rendered at
16:20, with the 2 Oct exclamation-mark rule already in. One Claude player per call stood in for
gpt-4.1 and played a scripted caller, with fixed tool results. No model, no phone, no credits. Every
caller is invented; the only building is בר כוכבא 23.

`mold_no_address` is modelled on the owner's own test call of 2 Oct (`01a0fbb8`): an English
speaker, mould on the lift ceiling, "same building i live in", then "im not sure". It was played
on both prompts; the other six are compared with the 2 Oct run
(`2026-10-02-inbound-happy.md`), which used the prompt before this change.

**What they show.** Words per Michael turn (the fixed opener left out): the six calls 14.7 before,
16.3 after; the address call 10.7 before, 17.1 after. No turn asks two questions. Service moves the
old prompt did not make: the address helped along ("גם רק שם הרחוב, בלי המספר, יעזור לי") instead
of asked again; the ticket number offered as the way to check on it later; an open request offered
a new detail; a balance followed by an offer to open the payment request. The lift emergency stays
on full stops, gives no instructions and promises no one. ולהתראות is the last word in all eight.

**What they cannot show.** Claude already wrote about two sentences a turn on the old prompt; the
real gpt-4.1 call wrote one clipped line ("רגע, אני רושם את זה.", "הבנתי, אין פנייה."), because it
read "משפט אחד או שניים קצרים" literally. How much longer gpt-4.1 gets on "שניים או שלושה" only
the owner's call shows.

## Before: mold_no_address on the 2 Oct prompt

- **Michael:** שלום, צהריים טובים! מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** hi, how are you
- **Michael:** היי! אני מצוין, תודה! ומה שלומְךָ?
- **Caller:** im good thanks. its about the elevator again, its dirty
- **Michael:** שמח לשמוע! אוי, עוד פעם, זה באמת לא נעים. מה בדיוק מלוכלך שם?
- **Caller:** the ceiling, it has mold, its a health hazard
- **Michael:** אתה צודק, עובש זה לא משהו שמשאירים ככה. מה הכתובת של הבניין?
- **Caller:** same building i live in
- **Michael:** ברור! ומה הכתובת שלו, רחוב ומספר?
- **Caller:** im not sure of the exact address
- **Michael:** אין בעיה! אתה זוכר לפחות את שם הרחוב?
- **Caller:** oh wait, its בר כוכבא 23, תל אביב, flat 2
- `[open_request {"description": "המעלית שוב מלוכלכת: יש עובש בתקרה של המעלית, והדייר אומר שזה מפגע בריאותי.", "type": "cleaning", "urgency": "high", "building": "בר כוכבא 23, תל אביב", "unit": "2"} -> {"ok": true, "opened": true, "reference": "255-1465-26", "reference_spoken": "שתיים חמש חמש, אחת ארבע שש חמש, שתיים שש"}]`
- **Michael:** פתחתי פנייה, המספר שלה שתיים חמש חמש, אחת ארבע שש חמש, שתיים שש. יש עוד משהו שאני יכול לעזור לְךָ בו?
- **Caller:** thats it
- **Michael:** תודה רבה שהתקשרתָּ! שיהיה לְךָ המשך יום נעים, ולהתראות!

## After

### mold_no_address
- **Michael:** שלום, צהריים טובים! מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** hi, how are you
- **Michael:** הכול טוב אצלי, תודה ששאלתָּ! ומה שלומְךָ?
- **Caller:** im good thanks. its about the elevator again, its dirty
- **Michael:** שמח לשמוע! וחבל שזה שוב קורה עם המעלית, באמת לא נעים. מה בדיוק מלוכלך שם?
- **Caller:** the ceiling, it has mold, its a health hazard
- **Michael:** אתה צודק, עובש זה לא משהו שמשאירים ככה. אני פותח על זה פנייה, מה הכתובת של הבניין?
- **Caller:** same building i live in
- **Michael:** בטח! רק שאין לי מולי את הכתובת של הבניין שלְךָ, איפה הוא נמצא?
- **Caller:** im not sure of the exact address
- **Michael:** זה בסדר גמור, לא חייבים לזכור בעל פה! גם רק שם הרחוב, בלי המספר, יעזור לי. איך קוראים לרחוב שלְךָ?
- **Caller:** oh wait, its בר כוכבא 23, תל אביב, flat 2
- `[open_request {"description": "המעלית שוב מלוכלכת: יש עובש בתקרה של המעלית. לדברי הדייר זה מפגע בריאותי", "type": "cleaning", "urgency": "high", "building": "בר כוכבא 23, תל אביב", "unit": "2"} -> {"ok": true, "opened": true, "reference": "255-1465-26", "reference_spoken": "שתיים חמש חמש, אחת ארבע שש חמש, שתיים שש"}]`
- **Michael:** מעולה, תודה! פתחתי פנייה על העובש בתקרה של המעלית, והמספר שלה הוא שתיים חמש חמש, אחת ארבע שש חמש, שתיים שש, ועם המספר הזה אני יכול לבדוק לְךָ מה קורה איתה. במה עוד אני יכול לעזור לְךָ?
- **Caller:** thats it
- **Michael:** תודה רבה שהתקשרתָּ וסיפרתָּ לנו על זה! המשך יום נעים, ולהתראות!

### male_light
- **Michael:** שלום, צהריים טובים! מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** היי, יש בעיה עם האור בחדר המדרגות, הוא לא נדלק
- **Michael:** אוי, לעלות במדרגות בחושך זה ממש לא נעים! איפה בדיוק בחדר המדרגות זה?
- **Caller:** המנורה ליד המעלית בקומה שתיים, כבר יומיים חושך
- **Michael:** יומיים זה כבר באמת הרבה! בוא נפתח על זה פנייה. מה הכתובת של הבניין ומספר הדירה שלְךָ?
- **Caller:** בר כוכבא 23, דירה 4
- `[open_request {"description": "האור בחדר המדרגות לא נדלק. המנורה ליד המעלית בקומה שתיים, כבר יומיים חושך", "type": "lighting", "urgency": "normal", "building": "בר כוכבא 23", "unit": "4"} -> {"ok": true, "opened": true, "reference": "255-1460-26", "reference_spoken": "שתיים חמש חמש, אחת ארבע שש אפס, שתיים שש"}]`
- **Michael:** תודה! פתחתי על זה פנייה, והמספר שלה הוא שתיים חמש חמש, אחת ארבע שש אפס, שתיים שש. במה עוד אני יכול לעזור לְךָ?
- **Caller:** תודה רבה, זהו
- **Michael:** בשמחה, תודה שהתקשרתָּ! שיהיה לְךָ המשך אחר צהריים נעים, ולהתראות!

### hello_then_fem_late
- **Michael:** שלום, צהריים טובים! מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** שלום
- **Michael:** היי, כיף לשמוע אותְךָ! מה שלומְךָ?
- **Caller:** בסדר, תודה
- **Michael:** שמח לשמוע! במה אני יכול לעזור לְךָ היום?
- **Caller:** רציתי לשאול כמה אני צריכה לשלם לוועד, אני לא בטוחה מה היתרה שלי
- **Michael:** בשמחה, אני אבדוק לָךְ! מה הכתובת שלָךְ, כולל מספר הדירה?
- **Caller:** מיכל לוי, בר כוכבא 23 דירה 2
- `[get_balance {"name": "מיכל לוי", "building": "בר כוכבא 23", "unit": "2"} -> {"ok": true, "found": 1, "resident": "מיכל לוי", "building": "בר כוכבא 23, תל אביב - יפו", "unit": "2", "owed_total": 750, "owed_months": [{"period": "2026-07", "amount": 250}, {"period": "2026-08", "amount": 250}, {"period": "2026-09", "amount": 250}], "in_review": []}]`
- **Michael:** תודה, מיכל! היתרה הפתוחה שלָךְ היא שבע מאות וחמישים שקלים, על יולי, אוגוסט וספטמבר. אם תרצי לשלם, אני יכול לפתוח לָךְ פנייה על זה ולעדכן את הצוות.
- **Caller:** אוקיי, תודה רבה
- **Michael:** בשמחה, מיכל! תודה שהתקשרתְּ, שיהיה לָךְ המשך אחר צהריים נעים, ולהתראות!

### how_are_you_pay
- **Michael:** שלום, צהריים טובים! מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** היי מיכאל, מה שלומך?
- **Michael:** אני מצוין, תודה ששאלתָּ! ומה שלומְךָ?
- **Caller:** גם אני בסדר. אני רוצה לשלם את הוועד, איך עושים את זה?
- **Michael:** שמח לשמוע! בשביל התשלום אני אפתח לְךָ פנייה מסודרת. מה הכתובת של הבניין ומספר הדירה?
- **Caller:** יוסי כהן, בר כוכבא 23 דירה 7
- `[open_request {"description": "יוסי כהן רוצה לשלם את הוועד ושואל איך עושים את זה", "type": "payment", "urgency": "normal", "building": "בר כוכבא 23", "unit": "7"} -> {"ok": true, "opened": true, "reference": "255-1462-26", "reference_spoken": "שתיים חמש חמש, אחת ארבע שש שתיים, שתיים שש"}]`
- `[notify_team {"reason": "payment", "description": "יוסי כהן רוצה לשלם את הוועד ושואל איך עושים את זה. בר כוכבא 23 דירה 7, פנייה 255-1462-26", "department": "collections", "building": "בר כוכבא 23", "unit": "7"} -> {"ok": true, "noted": true}]`
- **Michael:** תודה, יוסי! פתחתי לְךָ פנייה על התשלום, מספר שתיים חמש חמש, אחת ארבע שש שתיים, שתיים שש, וגם הצוות שלנו כבר יודע. יש עוד משהו שאני יכול לעזור לְךָ בו?
- **Caller:** מעולה, תודה
- **Michael:** בשמחה! תודה שהתקשרתָּ, ושיהיה לְךָ המשך יום נעים, ולהתראות!

### english_status
- **Michael:** שלום, צהריים טובים! מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** Hi, I opened a request last week about the elevator, what's the status?
- **Michael:** בשמחה, אני אבדוק לְךָ את זה! יש לְךָ את מספר הפנייה, או שתגיד לי את הכתובת ומספר הדירה?
- **Caller:** I don't have the number, it's Bar Kochba 23, apartment 9
- `[get_request_status {"building": "בר כוכבא 23", "unit": "9", "type": "elevator"} -> {"ok": true, "found": 1, "requests": [{"reference": "255-1402-26", "reference_spoken": "שתיים חמש חמש, אחת ארבע אפס שתיים, שתיים שש", "type": "elevator", "status": "in_progress", "status_he": "בטיפול", "opened": "2026-09-24"}]}]`
- **Michael:** מצאתי אותה! הפנייה שלְךָ על המעלית, מספר שתיים חמש חמש, אחת ארבע אפס שתיים, שתיים שש, נפתחה בעשרים וארבעה בספטמבר והיא כרגע בטיפול. יש משהו חדש עם המעלית שתרצה שאוסיף לפנייה?
- **Caller:** ok thanks, bye
- **Michael:** בשמחה, תודה שהתקשרתָּ! שיהיה לְךָ המשך יום נעים, ולהתראות!

### stuck_elevator
- **Michael:** שלום, צהריים טובים! מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** הלו, יש ילד תקוע במעלית בין הקומות, הוא בוכה, מה עושים?
- `[notify_team {"reason": "emergency", "description": "ילד תקוע במעלית בין הקומות, הוא בוכה. המתקשר שואל מה עושים. הכתובת עוד לא ידועה.", "department": "operations"} -> {"ok": true, "noted": true}]`
- **Michael:** אוי, מסכן, זה באמת מפחיד. עדכנתי עכשיו את הצוות שלנו שיש ילד תקוע במעלית. מה הכתובת של הבניין?
- **Caller:** בר כוכבא 23
- `[open_request {"description": "ילד תקוע במעלית בין הקומות, הוא בוכה", "type": "elevator", "urgency": "emergency", "building": "בר כוכבא 23"} -> {"ok": true, "opened": true, "reference": "255-1464-26", "reference_spoken": "שתיים חמש חמש, אחת ארבע שש ארבע, שתיים שש"}]`
- `[notify_team {"reason": "emergency", "description": "ילד תקוע במעלית בין הקומות, הוא בוכה. הכתובת: בר כוכבא 23. נפתחה פנייה 255-1464-26.", "department": "operations", "building": "בר כוכבא 23"} -> {"ok": true, "noted": true}]`
- **Michael:** פתחתי פנייה בדחיפות חירום על המעלית בבר כוכבא עשרים ושלוש, מספר שתיים חמש חמש, אחת ארבע שש ארבע, שתיים שש. גם הכתובת כבר אצל הצוות, ואני כאן איתְּךָ.
- **Caller:** מה אני עושה עד שמגיעים?
- **Michael:** קשה לשמוע ילד בוכה ככה, אני יודע. מה שעשיתי זה לפתוח פנייה בדחיפות חירום, והצוות יודע על הילד במעלית. אני נשאר איתְּךָ על הקו לכל מה שצריך.
- **Caller:** טוב, תודה
- **Michael:** תודה שהתקשרתָּ ודיווחתָּ כל כך מהר. שיהיה לְךָ המשך יום רגוע יותר, ולהתראות.

### private_sink
- **Michael:** שלום, צהריים טובים! מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** היי, הכיור במטבח שלי סתום כבר מאתמול, אתם יכולים לשלוח מישהו?
- **Michael:** אוי, זה באמת מעצבן! כיור בתוך הדירה הוא באחריות שלְךָ, אז הכי טוב להזמין אינסטלטור שיפתח אותו. יש עוד משהו שאני יכול לעזור לְךָ בו?
- **Caller:** אה, אוקיי, הבנתי
- **Michael:** בהצלחה עם הכיור, מקווה שייפתח מהר! יש עוד משהו שאני יכול לעשות בשבילְךָ?
- **Caller:** לא, זהו, תודה
- **Michael:** בשמחה! תודה שהתקשרתָּ, ושיהיה לְךָ אחר צהריים נעים, ולהתראות!

