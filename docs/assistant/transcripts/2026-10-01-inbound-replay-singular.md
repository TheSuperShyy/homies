# Incoming-call agent, 1 Oct evening: one person, in the singular (Claude replay)

Offline. Claude (Sonnet) played the model (gpt-4.1 on the phone) and the caller, one call each, on
the prompt and opening line of `docs/assistant/demo-inbound.md` as committed (round 1: `f4b35eb`;
round 2: `bc9ce79`, after the pointing clause was widened). The tools were the live definitions and
returned fixed results. No model, phone or credit was used. This checks the rules, not gpt-4.1's
exact wording or how the voice sounds. Every caller is invented and the only building is
בר כוכבא 23. The owner's decision and the design are in that file, "1 Oct — one person, in the
singular".

## Read

- **No plural and no slash in any of the seven calls.** Every call ends on ולהתראות.
- **Masculine until she shows otherwise.** The men got the masculine throughout. The women got it
  until "אני צריכה" / "אני לא בטוחה", and from then on the feminine, with no remark: "את גרה",
  "שלָךְ", "לָךְ", "תודה שהתקשרתְּ".
- **Pointed where the voice needs it.** Round 1 pointed לְךָ, לָךְ and התקשרתָּ, but left the small
  talk's "מה שלומך?" bare, which the voice can read either way. The clause now covers every word
  ending in the address suffix. Round 2 has "מה שלומְךָ?", "מִמְּךָ" and "ששאלתָּ".
- **What only a call can show:** gpt-4.1's own compliance, and how the voice reads the pointing.


## male_light: a man reports the stairwell light (round 1)

- **Michael:** שלום, צהריים טובים, מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** היי, יש בעיה עם האור בחדר המדרגות, הוא לא נדלק
- **Michael:** אוי, לא נעים בכלל לעלות במדרגות בחושך. איפה בדיוק זה בבניין?
- **Caller:** המנורה ליד המעלית בקומה שתיים, כבר יומיים חושך
- **Michael:** כבר יומיים, זה באמת מציק. מה הכתובת של הבניין, ובאיזו דירה אתה גר?
- **Caller:** בר כוכבא 23, דירה 4
- `[open_request {"description": "האור בחדר המדרגות לא נדלק, המנורה ליד המעלית בקומה שתיים, חושך כבר יומיים", "type": "lighting", "urgency": "normal", "building": "בר כוכבא 23", "unit": "4"} -> {"ok": true, "opened": true, "reference": "255-1460-26", "reference_spoken": "שתיים חמש חמש, אחת ארבע שש אפס, שתיים שש"}]`
- **Michael:** פתחתי על זה פנייה, והמספר שלה הוא שתיים חמש חמש, אחת ארבע שש אפס, שתיים שש. יש עוד משהו שאני יכול לעזור לְךָ בו?
- **Caller:** תודה רבה, זהו
- **Michael:** בשמחה, תודה שהתקשרתָּ, והמשך אחר צהריים נעים, ולהתראות.

## fem_leak_first: a woman reports a leak, "אני צריכה" in her first line (round 1)

- **Michael:** שלום, צהריים טובים, מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** שלום, אני צריכה לדווח על נזילה בחדר המדרגות, יש מים על הרצפה ליד הכניסה
- **Michael:** אוי, לא נעים בכלל. מאיפה המים מגיעים?
- **Caller:** נראה לי שזה מטפטף מהתקרה, מעל תיבות הדואר
- **Michael:** בסדר, אני פותח על זה פנייה. מה הכתובת של הבניין?
- **Caller:** בר כוכבא 23, אני גרה בדירה 6
- `[open_request {"description": "נזילה בחדר המדרגות, מים על הרצפה ליד הכניסה, נראה שמטפטף מהתקרה מעל תיבות הדואר", "type": "plumbing", "urgency": "normal", "building": "בר כוכבא 23", "unit": "6"} -> {"ok": true, "opened": true, "reference": "255-1461-26", "reference_spoken": "שתיים חמש חמש, אחת ארבע שש אחת, שתיים שש"}]`
- **Michael:** פתחתי פנייה על הנזילה, המספר שלה הוא שתיים חמש חמש, אחת ארבע שש אחת, שתיים שש. אני יכול לעזור לָךְ במשהו נוסף?
- **Caller:** תודה, זה הכל
- **Michael:** בשמחה, תודה שהתקשרתְּ. המשך אחר צהריים נעים, ולהתראות.

## hello_then_fem_late: a bare hello, small talk, the feminine only in her third line (round 1)

- **Michael:** שלום, צהריים טובים, מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** שלום
- **Michael:** היי, שמח לשמוע אותך! מה שלומך?
- **Caller:** בסדר, תודה
- **Michael:** יופי, טוב לשמוע. אז במה אני יכול לעזור לְךָ?
- **Caller:** רציתי לשאול כמה אני צריכה לשלם לוועד, אני לא בטוחה מה היתרה שלי
- **Michael:** בטח, אני בודק את זה. באיזה בניין ובאיזו דירה את גרה?
- **Caller:** מיכל לוי, בר כוכבא 23 דירה 2
- `[get_balance {"name": "מיכל לוי", "building": "בר כוכבא 23", "unit": "2"} -> {"ok": true, "found": 1, "resident": "מיכל לוי", "building": "בר כוכבא 23, תל אביב - יפו", "unit": "2", "owed_total": 750, "owed_months": [{"period": "2026-07", "amount": 250}, {"period": "2026-08", "amount": 250}, {"period": "2026-09", "amount": 250}], "in_review": []}]`
- **Michael:** היתרה שלָךְ היא שבע מאות וחמישים שקלים, על יולי, אוגוסט וספטמבר. עוד משהו שאני יכול לעזור לָךְ בו?
- **Caller:** אוקיי, תודה רבה
- **Michael:** בשמחה, תודה שהתקשרתְּ. המשך אחר צהריים נעים, ולהתראות.

## english_status: an English speaker asks about his request (round 1)

- **Michael:** שלום, צהריים טובים, מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** Hi, I opened a request last week about the elevator, what's the status?
- **Michael:** בטח, בוא נראה איפה זה עומד. מה הכתובת של הבניין ומספר הדירה?
- **Caller:** I don't have the number, it's Bar Kochba 23, apartment 9
- `[get_request_status {"building": "בר כוכבא 23", "unit": "9", "type": "elevator"} -> {"ok": true, "found": 1, "requests": [{"reference": "255-1402-26", "reference_spoken": "שתיים חמש חמש, אחת ארבע אפס שתיים, שתיים שש", "type": "elevator", "status": "in_progress", "status_he": "בטיפול", "opened": "2026-09-24"}]}]`
- **Michael:** מצאתי את הפנייה על המעלית, מספר שתיים חמש חמש, אחת ארבע אפס שתיים, שתיים שש, והיא כרגע בטיפול. אני יכול לעזור לְךָ במשהו נוסף?
- **Caller:** ok thanks, bye
- **Michael:** תודה שהתקשרתָּ, אחר צהריים נעים ולהתראות.

## how_are_you_pay: a how-are-you, then he wants to pay (round 1)

- **Michael:** שלום, צהריים טובים, מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** היי מיכאל, מה שלומך?
- **Michael:** אני מצוין, תודה! ואיך אתה?
- **Caller:** גם אני בסדר. אני רוצה לשלם את הוועד, איך עושים את זה?
- **Michael:** שמח לשמוע! אפתח על זה פנייה, באיזה בניין ובאיזו דירה אתה?
- **Caller:** יוסי כהן, בר כוכבא 23 דירה 7
- `[open_request {"description": "רוצה לשלם את הוועד, שואל איך עושים את זה", "type": "payment", "urgency": "normal", "building": "בר כוכבא 23", "unit": "7"} -> {"ok": true, "opened": true, "reference": "255-1462-26", "reference_spoken": "שתיים חמש חמש, אחת ארבע שש שתיים, שתיים שש"}]`
- `[notify_team {"reason": "payment", "description": "יוסי כהן, בר כוכבא 23 דירה 7, רוצה לשלם את הוועד ושואל איך עושים את זה. נפתחה פנייה 255-1462-26", "department": "collections", "building": "בר כוכבא 23", "unit": "7"} -> {"ok": true, "noted": true}]`
- **Michael:** פתחתי לְךָ על זה פנייה, מספר שתיים חמש חמש, אחת ארבע שש שתיים, שתיים שש, והצוות יודע. עוד משהו שאני יכול לעזור בו?
- **Caller:** מעולה, תודה
- **Michael:** בשמחה, תודה שהתקשרתָּ, והמשך אחר צהריים נעים. ולהתראות.

## hello_then_fem_late_v2: the same small-talk call on the widened pointing clause (round 2)

- **Michael:** שלום, צהריים טובים, מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** שלום
- **Michael:** היי, שמח לשמוע מִמְּךָ! מה שלומְךָ?
- **Caller:** בסדר, תודה
- **Michael:** יופי, טוב לשמוע. במה אני יכול לעזור לְךָ?
- **Caller:** רציתי לשאול כמה אני צריכה לשלם לוועד, אני לא בטוחה מה היתרה שלי
- **Michael:** בטח, אני יכול לבדוק את זה לָךְ. באיזה בניין ובאיזו דירה את גרה?
- **Caller:** מיכל לוי, בר כוכבא 23 דירה 2
- `[get_balance {"name": "מיכל לוי", "building": "בר כוכבא 23", "unit": "2"} -> {"ok": true, "found": 1, "resident": "מיכל לוי", "building": "בר כוכבא 23, תל אביב - יפו", "unit": "2", "owed_total": 750, "owed_months": [{"period": "2026-07", "amount": 250}, {"period": "2026-08", "amount": 250}, {"period": "2026-09", "amount": 250}], "in_review": []}]`
- **Michael:** היתרה שלָךְ היא שבע מאות וחמישים שקלים, מאתיים וחמישים על כל אחד מהחודשים יולי, אוגוסט וספטמבר. אני יכול לעזור לָךְ בעוד משהו?
- **Caller:** אוקיי, תודה רבה
- **Michael:** בשמחה. תודה שהתקשרתְּ, והמשך אחר צהריים נעים, ולהתראות.

## hello_male: a man's small talk, asked back, then the intercom (round 2)

- **Michael:** שלום, צהריים טובים, מדבר מיכאל מהומיז. איך אני יכול לעזור לְךָ?
- **Caller:** שלום
- **Michael:** היי, איזה כיף לשמוע ממְּךָ! מה שלומְךָ?
- **Caller:** בסדר, תודה, ומה איתך?
- **Michael:** יופי, גם אצלי הכל טוב, תודה ששאלתָּ. במה אני יכול לעזור לְךָ?
- **Caller:** רציתי לדווח שהאינטרקום בכניסה לא עובד
- **Michael:** אוי, זה באמת לא נעים. מה בדיוק קורה כשמנסים להשתמש בו?
- **Caller:** לוחצים על הכפתור ושום דבר לא קורה, אין צלצול בדירות
- **Michael:** אני פותח על זה פנייה. מה הכתובת של הבניין, ובאיזו דירה אתה?
- **Caller:** בר כוכבא 23, דירה 5
- `[open_request {"description": "האינטרקום בכניסה לא עובד. לוחצים על הכפתור ושום דבר לא קורה, אין צלצול בדירות", "type": "electrical", "urgency": "normal", "building": "בר כוכבא 23", "unit": "5"} -> {"ok": true, "opened": true, "reference": "255-1463-26", "reference_spoken": "שתיים חמש חמש, אחת ארבע שש שלוש, שתיים שש"}]`
- **Michael:** פתחתי על זה פנייה, והמספר שלה הוא שתיים חמש חמש, אחת ארבע שש שלוש, שתיים שש. אני יכול לעזור לְךָ במשהו נוסף?
- **Caller:** תודה, יום טוב
- **Michael:** תודה רבה שהתקשרתָּ, שיהיה לְךָ המשך אחר צהריים נעים, ולהתראות.
