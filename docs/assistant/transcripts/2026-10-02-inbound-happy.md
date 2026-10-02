# Incoming calls, 2 Oct: the exclamation mark, six simulated calls

The prompt in `docs/assistant/demo-inbound.md` after the 2 Oct change (the opener's greeting ends on
"!", and one words rule: "!" is read with a smile and "." flat, so warm and glad lines end on "!",
and a caller in danger stays on full stops), rendered at 16:20. One Claude player per call stood in
for gpt-4.1 and played a scripted caller, with fixed tool results. No model, no phone, no credits.
Every caller is invented; the only building is בר כוכבא 23. The words only: how the happy tag and
the new voice sound, only the owner's call shows.

**What they show.** Warm and glad lines end on "!" (a reaction to a dark stairwell, "בשמחה!", the
goodbye), questions keep "?", the balance figure is said with a full stop, and the child stuck in
the lift is full stops from start to end. "ולהתראות" stays the last word in all six. One quirk: in
`male_light` a ticket number got an "!". Singular and the feminine switch hold as on 1 Oct.

## male_light
- **Michael:** שלום, צהריים טובים! מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** היי, יש בעיה עם האור בחדר המדרגות, הוא לא נדלק
- **Michael:** אוי, לעלות במדרגות בחושך זה ממש לא נעים! איפה בדיוק בחדר המדרגות זה?
- **Caller:** המנורה ליד המעלית בקומה שתיים, כבר יומיים חושך
- **Michael:** יומיים בחושך זה באמת יותר מדי! מה הכתובת של הבניין, ובאיזו דירה אתה גר?
- **Caller:** בר כוכבא 23, דירה 4
- `[open_request {"description": "המנורה בחדר המדרגות ליד המעלית בקומה שתיים לא נדלקת, כבר יומיים חושך", "type": "lighting", "urgency": "normal", "building": "בר כוכבא 23", "unit": "4"} -> {"ok": true, "opened": true, "reference": "255-1460-26", "reference_spoken": "שתיים חמש חמש, אחת ארבע שש אפס, שתיים שש"}]`
- **Michael:** פתחתי פנייה על המנורה, המספר שלה שתיים חמש חמש, אחת ארבע שש אפס, שתיים שש! יש עוד משהו שאני יכול לעזור לְךָ בו?
- **Caller:** תודה רבה, זהו
- **Michael:** בשמחה! תודה שהתקשרתָּ, אחר צהריים נעים ולהתראות!

## hello_then_fem_late
- **Michael:** שלום, צהריים טובים! מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** שלום
- **Michael:** היי, כיף לשמוע ממְּךָ! מה שלומְךָ?
- **Caller:** בסדר, תודה
- **Michael:** שמח לשמוע! במה אני יכול לעזור לְךָ היום?
- **Caller:** רציתי לשאול כמה אני צריכה לשלם לוועד, אני לא בטוחה מה היתרה שלי
- **Michael:** בשמחה, אני בודק לָךְ! מה הכתובת ומספר הדירה שלָךְ?
- **Caller:** מיכל לוי, בר כוכבא 23 דירה 2
- `[get_balance {"name": "מיכל לוי", "building": "בר כוכבא 23", "unit": "2"} -> {"ok": true, "found": 1, "resident": "מיכל לוי", "building": "בר כוכבא 23, תל אביב - יפו", "unit": "2", "owed_total": 750, "owed_months": [{"period": "2026-07", "amount": 250}, {"period": "2026-08", "amount": 250}, {"period": "2026-09", "amount": 250}], "in_review": []}]`
- **Michael:** מיכל, היתרה שלָךְ היא שבע מאות וחמישים שקל, מאתיים וחמישים על כל אחד מהחודשים יולי, אוגוסט וספטמבר. יש עוד משהו שאני יכול לעזור לָךְ בו?
- **Caller:** אוקיי, תודה רבה
- **Michael:** בשמחה, מיכל! תודה שהתקשרתְּ, שיהיה לָךְ אחר צהריים נעים, ולהתראות!

## how_are_you_pay
- **Michael:** שלום, צהריים טובים! מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** היי מיכאל, מה שלומך?
- **Michael:** היי! אני מצוין, תודה ששאלתָּ! ומה שלומְךָ?
- **Caller:** גם אני בסדר. אני רוצה לשלם את הוועד, איך עושים את זה?
- **Michael:** יופי, שמח לשמוע! אני אפתח לְךָ פנייה על התשלום, רק תגיד לי באיזה בניין ובאיזו דירה אתה גר?
- **Caller:** יוסי כהן, בר כוכבא 23 דירה 7
- `[open_request {"description": "יוסי כהן רוצה לשלם את הוועד ושואל איך עושים את זה", "type": "payment", "urgency": "normal", "building": "בר כוכבא 23", "unit": "7"} -> {"ok": true, "opened": true, "reference": "255-1462-26", "reference_spoken": "שתיים חמש חמש, אחת ארבע שש שתיים, שתיים שש"}]`
- `[notify_team {"reason": "payment", "description": "יוסי כהן רוצה לשלם את הוועד ושואל איך עושים את זה. פנייה 255-1462-26. בר כוכבא 23 דירה 7", "department": "collections", "building": "בר כוכבא 23", "unit": "7"} -> {"ok": true, "noted": true}]`
- **Michael:** תודה יוסי! פתחתי פנייה על התשלום, המספר שלה שתיים חמש חמש, אחת ארבע שש שתיים, שתיים שש, והצוות כבר יודע שאתה רוצה לשלם. יש עוד משהו שאני יכול לעזור לְךָ בו?
- **Caller:** מעולה, תודה
- **Michael:** בשמחה, יוסי! תודה שהתקשרתָּ, שיהיה לְךָ המשך אחר צהריים נעים, ולהתראות!

## english_status
- **Michael:** שלום, צהריים טובים! מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** Hi, I opened a request last week about the elevator, what's the status?
- **Michael:** בשמחה, אני בודק לְךָ! יש לְךָ את מספר הפנייה, או שתגיד לי את הכתובת ומספר הדירה?
- **Caller:** I don't have the number, it's Bar Kochba 23, apartment 9
- `[get_request_status {"building": "בר כוכבא 23", "unit": "9", "type": "elevator"} -> {"ok": true, "found": 1, "requests": [{"reference": "255-1402-26", "reference_spoken": "שתיים חמש חמש, אחת ארבע אפס שתיים, שתיים שש", "type": "elevator", "status": "in_progress", "status_he": "בטיפול", "opened": "2026-09-24"}]}]`
- **Michael:** הפנייה על המעלית, מספר שתיים חמש חמש, אחת ארבע אפס שתיים, שתיים שש, נמצאת בטיפול. יש עוד משהו שאני יכול לעזור לְךָ בו?
- **Caller:** ok thanks, bye
- **Michael:** בשמחה! תודה שהתקשרתָּ, שיהיה לְךָ אחר צהריים נעים ולהתראות!

## stuck_elevator
- **Michael:** שלום, צהריים טובים! מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** הלו, יש ילד תקוע במעלית בין הקומות, הוא בוכה, מה עושים?
- `[notify_team {"reason": "emergency", "description": "ילד תקוע במעלית בין הקומות ובוכה. המתקשר שואל מה עושים. הכתובת עוד לא נמסרה.", "department": "operations"} -> {"ok": true, "noted": true}]`
- **Michael:** אוי, זה מפחיד, והצוות שלנו כבר יודע. באיזה בניין זה?
- **Caller:** בר כוכבא 23
- `[open_request {"description": "ילד תקוע במעלית בין הקומות, בוכה", "type": "elevator", "urgency": "emergency", "building": "בר כוכבא 23"} -> {"ok": true, "opened": true, "reference": "255-1464-26", "reference_spoken": "שתיים חמש חמש, אחת ארבע שש ארבע, שתיים שש"}]`
- `[notify_team {"reason": "emergency", "description": "עדכון: הילד תקוע במעלית בבר כוכבא 23, בין הקומות. נפתחה פנייה 255-1464-26.", "department": "operations", "building": "בר כוכבא 23"} -> {"ok": true, "noted": true}]`
- **Michael:** פתחתי פנייה דחופה, המספר שלה שתיים חמש חמש, אחת ארבע שש ארבע, שתיים שש. הצוות יודע גם איפה זה.
- **Caller:** מה אני עושה עד שמגיעים?
- **Michael:** על זה אני לא יכול לתת לְךָ הנחיות. מה שעשיתי זה לפתוח פנייה דחופה, והצוות שלנו כבר יודע.
- **Caller:** טוב, תודה
- **Michael:** תודה שהתקשרתָּ. מקווה שהילד ייצא משם מהר, ושיהיה לְךָ אחר צהריים רגוע, ולהתראות.

## private_sink
- **Michael:** שלום, צהריים טובים! מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** היי, הכיור במטבח שלי סתום כבר מאתמול, אתם יכולים לשלוח מישהו?
- **Michael:** אוי, כיור סתום מאתמול זה ממש לא נעים! זה בתוך הדירה, אז הטיפול בזה הוא שלְךָ, עם אינסטלטור פרטי. יש עוד משהו שאני יכול לעזור לְךָ בו?
- **Caller:** אה, אוקיי, הבנתי
- **Michael:** בסדר גמור! אם יש עוד משהו שאני יכול לעשות בשבילְךָ, אני כאן, יש משהו?
- **Caller:** לא, זהו, תודה
- **Michael:** תודה שהתקשרתָּ! המשך אחר צהריים נעים, ולהתראות!

