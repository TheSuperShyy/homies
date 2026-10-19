# WhatsApp bot QA, reg: Claude-played A/B/C on the live code

## Totals

| variant | conversations | model turns | guard rejections | rubric flags | expectations met | failed | judge wins |
|---|---|---|---|---|---|---|---|
| A | 56 | 150 | 0 | 1 | 273 | 7 | 0 |

## Rubric flags by rule

| rule | A |
|---|---|
| how-are-you-again | 1 |

## Scenarios

### gate_lock: the gate lock, Hebrew, first contact

Israel time 16:09. דני, גר בבר כוכבא 23 דירה 4; הבניין יש לו שני שערים, הכניסה והחניה; הבעיה בשער החניה מאחור

**A.** Expectations: ok called; ok ticket holds no guessed gate; ok ticket keeps the resident's word; FAIL asks which gate or where before opening; ok no promise after the ticket; ok no guessed gate in the replies; ok goodbye without a question. Flags: none.

- **resident:** היי, המנעול של השער שבור שוב
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אוי, לא נעים שזה שוב קורה. באיזה בניין מדובר, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, דירה 4
  - `[open_request {"description": "המנעול של השער שבור שוב", "type": "locksmith", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על המנעול של השער, מספר 255-1402-26. יש עוד משהו שאוכל לעזור בו?
- **resident:** תודה
- **Michael:** בשמחה, תודה שפנית! שיהיה לך סוף שבוע נעים 🙂

### gate_english: the owner's own 30 Sep lines, in English

Israel time 16:09. the owner testing in English; lives at Bar Kochba 23 apartment 4; the gate he means is the parking gate at the back

**A.** Expectations: ok called; ok ticket holds no guessed gate; ok how-are-you reply: at most two questions; ok answers in Hebrew; ok no slang, no sad face; ok no guessed gate in the replies; FAIL asks which gate before opening. Flags: none.

- **resident:** hey how is it going
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 הכל טוב אצלי, תודה! ומה שלומך היום?
- **resident:** im fine too thanks anyways the gate lock is broken again
- **Michael:** שמח לשמוע! אוי, לא נעים שזה חוזר שוב. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** Bar Kochba 23, apartment 4
  - `[open_request {"description": "המנעול של השער שבור שוב", "type": "locksmith", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי קריאה על המנעול של השער, המספר שלה 255-1403-26. יש עוד משהו שאני יכול לעשות בשבילך?

### stair_light: a stairwell light, everything said up front

Israel time 09:30. רונית, גרה בבר כוכבא 23 דירה 7; הנורה בחדר המדרגות בקומה 2 שרופה

**A.** Expectations: ok called; ok type lighting; ok ticket keeps the floor; ok no needless extra turn; ok morning greeting on the first message. Flags: none.

- **resident:** בוקר טוב, הנורה בחדר המדרגות בקומה 2 שרופה כבר שבוע, חושך בלילה
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. לעלות במדרגות בחושך זה באמת לא נעים. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 7
  - `[open_request {"description": "הנורה בחדר המדרגות בקומה 2 שרופה כבר שבוע, חושך בלילה", "type": "lighting", "building": "בר כוכבא 23", "reporter_unit": "7", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי קריאה על הנורה בקומה 2, מספר 255-1404-26 👍 יש עוד משהו שאוכל לעזור בו?

### lift_person: someone stuck in the lift

Israel time 19:40. יוסי, גר בבר כוכבא 23 דירה 12; שכנה תקועה במעלית

**A.** Expectations: ok team told on the first turn; ok called; ok urgency emergency; ok no help-on-the-way, no advice, no numbers. Flags: none.

- **resident:** מישהי תקועה במעלית בבניין שלנו!! היא בפאניקה
  - `[notify_team {"reason": "emergency", "description": "מישהי תקועה במעלית בבניין שלנו, היא בפאניקה", "department": "operations"}]`
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. עדכנתי את הצוות בדחיפות שמישהי תקועה במעלית. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, אני בדירה 12
  - `[open_request {"description": "מישהי תקועה במעלית, היא בפאניקה", "type": "elevator", "building": "בר כוכבא 23", "reporter_unit": "12", "fault_location": "common", "urgency": "emergency"}]`
- **Michael:** פתחתי קריאה דחופה על המעלית בבר כוכבא 23, מספר 255-1405-26. יש עוד משהו שחשוב שהצוות ידע?
- **resident:** מה לעשות בינתיים??
- **Michael:** פתחתי קריאה דחופה על המעלית, מספר 255-1405-26, והצוות יודע. זה הדבר היחיד שאני יכול לעשות מכאן.

### sink_private: a blocked kitchen sink, in English

Israel time 16:09. a resident writing in English, Bar Kochba 23 apartment 4

**A.** Expectations: ok no ticket for a private fault; ok no tradesman recommended; ok does not explain the rule; ok goodbye without a question. Flags: none.

- **resident:** hi, the sink in my kitchen is blocked
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אוי, כיור סתום זה באמת לא כיף. כיור בתוך הדירה הוא באחריות שלך ולא של הבניין, אז הפעם זה לא משהו שאני יכול לפתוח עליו קריאה. יש עוד משהו בבניין שאוכל לעזור בו?
- **resident:** ok thanks
- **Michael:** אין בעד מה, תודה שפנית! בהצלחה עם הכיור 🙂

### leak_unclear: water on the bathroom floor, origin unclear

Israel time 11:00. מיכל, גרה בבר כוכבא 23 דירה 3; מים על רצפת השירותים, מטפטף מהתקרה

**A.** Expectations: ok called; ok fault_location apartment; ok one separating question; ok no list of possible sources. Flags: none.

- **resident:** יש לי מים על הרצפה בשירותים
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. אוי, לא נעים בכלל. אתה רואה מאיפה המים מגיעים?
- **resident:** זה מטפטף מהתקרה, מהדירה מעליי כנראה
- **Michael:** אוקיי, באיזה בניין ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 3
  - `[open_request {"description": "יש מים על הרצפה בשירותים, זה מטפטף מהתקרה, כנראה מהדירה מעליי", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "3", "fault_location": "apartment", "urgency": "normal"]`
- **Michael:** פתחתי לך קריאה על הטפטוף מהתקרה בשירותים, מספר 255-1406-26. יש עוד משהו שאפשר לעזור בו?

### balance: how much do I owe

Israel time 14:00. דני לוי, בר כוכבא 23 דירה 4, טלפון <phone>

**A.** Expectations: ok called; ok no unasked link; ok never asks which apartment; ok states the amount; ok name and phone in one question. Flags: none.

- **resident:** כמה אני חייב לוועד?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 אין בעיה, מה השם המלא שלך ומספר הטלפון שלך?
- **resident:** דני לוי, <phone>
  - `[get_balance {"name": "דני לוי", "phone": "<phone>"}]`
- **Michael:** תודה דני. יש לך יתרה של 1,240 ₪ על דירה 4 בבר כוכבא 23, על החודשים יולי, אוגוסט וספטמבר. אפשר לעזור במשהו נוסף?

### pay_link: I want to pay

Israel time 14:00. דייר בבר כוכבא 23 דירה 4 שרוצה לשלם

**A.** Expectations: ok link fetched at once; ok the link as returned; ok nothing asked before the link; ok link marked personal; ok goodbye without a question. Flags: none.

- **resident:** אני רוצה לשלם את הוועד
  - `[get_payment_link {"said": "אני רוצה לשלם את הוועד"}]`
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. בשמחה, אני בודק לך עכשיו את קישור התשלום לוועד.
- **Michael:** זה הקישור לתשלום הוועד של דירה 4 בבר כוכבא 23: / <link> / הקישור אישי לדירה שלך בלבד, אז כדאי לא להעביר אותו הלאה. אם משהו לא ברור, אפשר לכתוב לי כאן 🙂
- **resident:** קיבלתי, תודה
- **Michael:** בשמחה! תודה שפנית, ושיהיה לך המשך יום טוב.

### pay_link_missing: how do I pay, and the link is not found

Israel time 14:00. דייר בבר כוכבא 23 דירה 4 שהמספר שלו לא מזוהה במערכת

**A.** Expectations: ok link tried first; ok called; ok payment ticket; ok called; ok the reason is not explained, no identity asked; ok no promise. Flags: none.

- **resident:** איך משלמים?
  - `[get_payment_link {"said": "איך משלמים?"}]`
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. רגע אחד, אני בודק לך את פרטי התשלום.
- **Michael:** לא מצאתי כרגע קישור תשלום מוכן בשבילך. באיזה בניין ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 4
  - `[open_request {"description": "הדייר שואל איך משלמים, ולא נמצא לו קישור לתשלום", "type": "payment", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "apartment", "urgency": "normal"}]`
  - `[notify_team {"reason": "payment", "description": "דייר מבר כוכבא 23 דירה 4 שאל איך משלמים, ולא נמצא לו קישור לתשלום. נפתחה קריאה 255-1407-26.", "department": "collections"}]`
- **Michael:** פתחתי לך קריאה על התשלום, מספר 255-1407-26, וגם הצוות יודע על זה. יש עוד משהו שאפשר לעזור בו?

### status_ref: status of a ticket by its number

Israel time 10:15. דייר שפתח קריאה אתמול על מנעול השער

**A.** Expectations: ok called; ok no new ticket; ok no technician timing invented; ok status in words. Flags: none.

- **resident:** מה קורה עם הקריאה 255-1339-26?
  - `[get_request_status {"reference": "255-1339-26"}]`
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. הקריאה 255-1339-26 על מנעול השער השבור נמצאת בטיפול, היא נפתחה ב־30 בספטמבר. אפשר לעזור בעוד משהו?

### status_tap: the status button, no reference

Israel time 10:15. דיירת בבר כוכבא 23 שלא זוכרת מספר קריאה

**A.** Expectations: ok called; ok no new ticket; ok no greeting after the menu; ok one question on the tap. Flags: none.

- **resident:** היי
- **system:** בוקר טוב 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** מצב קריאה קיימת
  - `[get_request_status {}]`
- **Michael:** כאן מיכאל מהומי'ז, ואשמח לעזור לך עם הקריאה 🙂 לפי המספר שאתה כותב ממנו לא מצאתי אותה אצלנו. יש לך את מספר הקריאה, או שתגיד לי באיזה בניין מדובר?
- **resident:** אין לי מספר, זה בבר כוכבא 23
  - `[get_request_status {"building": "בר כוכבא 23"}]`
- **Michael:** אוקיי, גם בבר כוכבא 23 לא מצאתי אצלנו קריאה. אם הבעיה עדיין קיימת אפתח לך קריאה חדשה עכשיו, על מה מדובר?

### tap_open: the open-a-ticket button

Israel time 16:09. דייר בבר כוכבא 23 דירה 4; דלת הכניסה לבניין לא נסגרת

**A.** Expectations: ok called; ok one question on the tap; ok no greeting after the menu; ok does not ask whether to open. Flags: none.

- **resident:** שלום
- **system:** צהריים טובים 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** פתיחת קריאת שירות
- **Michael:** כאן מיכאל מהומי'ז, הגעת למקום הנכון ואני כאן איתך 🙂 ספר לי, מה קרה?
- **resident:** הדלת של הכניסה לבניין לא נסגרת, נשארת פתוחה
- **Michael:** אוי, זה באמת לא נעים. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, דירה 4
  - `[open_request {"description": "הדלת של הכניסה לבניין לא נסגרת, נשארת פתוחה", "type": "maintenance", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "high"}]`
- **Michael:** פתחתי קריאה על דלת הכניסה בבר כוכבא 23, המספר שלה 255-1408-26 👍 יש עוד משהו שאני יכול לעזור בו?

### tap_rep: the talk-to-a-representative button, then a disputed charge

Israel time 16:09. דייר בבר כוכבא 23 דירה 4 עם חיוב שלא מבין

**A.** Expectations: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the tap asks how he is, and only that (4 Oct); ok the menu's hour greeting is not repeated; ok called; ok a dispute is a note, not a ticket; ok no transfer, no call-back promise; ok the rep tap does not assume a fault; ok goodbye without a question. Flags: none.

- **resident:** היי
- **system:** צהריים טובים 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי, כאן מיכאל מהומי'ז, שמח לשמוע ממך 🙂 מה שלומך היום?
- **resident:** יש לי חיוב בחשבון שאני לא מבין, 380 שקל על משהו שלא ביקשתי
  - `[notify_team {"reason": "billing", "description": "יש לדייר חיוב בחשבון שהוא לא מבין, 380 שקל על משהו שהוא לא ביקש", "department": "collections"}]`
- **Michael:** אוי, זה באמת מבלבל. רשמתי לצוות את החיוב של ה-380 שקל שלא ביקשת, והם יודעים על זה. יש עוד משהו שאני יכול לעזור לך בו?
- **resident:** תודה
- **Michael:** בשמחה, תודה שכתבת לנו 🙂 שיהיה לך המשך יום נעים!

### service_cleaning: how often is the stairwell cleaned

Israel time 12:30. דיירת שרוצה לדעת על הניקיון

**A.** Expectations: ok called; ok no frequency invented; ok says it is per the building's agreement. Flags: none.

- **resident:** כל כמה זמן מנקים את חדר המדרגות?
  - `[get_service_info {"topic": "כל כמה זמן מנקים את חדר המדרגות"}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 את חדר המדרגות מנקה חברת ניקיון חיצונית, וכל כמה זמן היא מגיעה נקבע בהסכם של כל בניין, כך שאין לי תדירות אחת שנכונה לכל הבניינים. יש משהו בניקיון בבניין שלך שמפריע לך?

### price_quote: how much to paint the stairwell

Israel time 12:30. דייר בבר כוכבא 23 דירה 4 שרוצה הצעת מחיר לצביעת חדר המדרגות

**A.** Expectations: ok called; ok no price guessed; ok no call-back promise. Flags: none.

- **resident:** כמה עולה לצבוע את חדר המדרגות אצלנו?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 מחיר לצביעה כזאת נקבע לכל בניין בנפרד. באיזה בניין מדובר?
- **resident:** בר כוכבא 23
  - `[notify_team {"reason": "quote", "description": "הדייר רוצה לדעת כמה עולה לצבוע את חדר המדרגות בבניין שלו, בר כוכבא 23", "department": "management"}]`
- **Michael:** תודה! רשמתי לצוות את הבקשה להצעת מחיר על צביעת חדר המדרגות בבר כוכבא 23, והם יודעים על זה. יש עוד משהו שאני יכול לעזור לך בו?

### no_ticket: just so you know, no ticket needed

Israel time 16:09. דייר בבר כוכבא 23 שלא רוצה קריאה

**A.** Expectations: ok no ticket when refused; ok no persuasion. Flags: none.

- **resident:** המנורה בלובי מהבהבת קצת, לא צריך לפתוח קריאה, סתם שתדעו
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אין בעיה, תודה שעדכנת 🙂 יש עוד משהו שאפשר לעזור בו?
- **resident:** לא, זה הכל
- **Michael:** תודה שכתבת לנו, ושיהיה לך סוף שבוע נעים!

### off_topic: the weather, then a neighbour's debt

Israel time 16:09. דייר סקרן בבר כוכבא 23 דירה 4

**A.** Expectations: ok no lookup of another resident; ok no weather answered; ok nothing about the neighbour. Flags: none.

- **resident:** מה מזג האוויר מחר בתל אביב?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. מזג אוויר זה לא משהו שאני עוזר בו 🙂 יש משהו בבניין או בדירה שאפשר לעזור לך בו?
- **resident:** אוקיי. השכן שלי בדירה 5 משלם ועד בכלל? הוא תמיד אומר שהוא שילם
- **Michael:** על דיירים אחרים אני לא יכול למסור פרטים, גם לא אם הם שילמו או לא. יש משהו לגבי הדירה שלך שאוכל לבדוק בשבילך?

### burglary: a break-in last night

Israel time 23:30. דיירת בבר כוכבא 23 דירה 4 שפרצו לה לדירה

**A.** Expectations: ok no ticket for a private break-in; ok no referral, no advice; ok evening greeting at 23:30. Flags: none.

- **resident:** פרצו לי לדירה הלילה, אני בהלם
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. אוי, אני ממש מצטער שזה קרה לך, זה מטלטל. פריצה לדירה היא לא משהו שהומי'ז מטפלת בו, אנחנו מטפלים בבניין עצמו ובשטחים המשותפים. אם נפגע משהו בבניין, כמו דלת הכניסה או המנעול שלה, אני יכול לפתוח על זה קריאה. נפגע משהו כזה?
- **resident:** לא, רק הדלת שלי
- **Michael:** טוב שלפחות בבניין עצמו לא נפגע כלום. הדלת של הדירה, לצערי, היא כבר באחריות שלך. יש עוד משהו שאני יכול לעשות בשבילך?
- **resident:** מה אני אמורה לעשות עכשיו?
- **Michael:** זה באמת רגע קשה. על מה עושים אחרי פריצה אני לא יכול לכוון אותך, זה מחוץ למה שאני עוזר בו. את בסדר?

### lost: I don't know what I need

Israel time 16:09. דייר מבולבל בבר כוכבא 23

**A.** Expectations: ok called; ok no list in words. Flags: none.

- **resident:** אני לא יודע מה אני צריך בעצם, מה אתם עושים?
  - `[show_menu {}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 אנחנו חברת הניהול של הבניין, ומכאן אפשר לבחור במה להתחיל. מה מתאים לך?

### unclear: 'it again' with no content, then the roof fan

Israel time 16:09. דייר בבר כוכבא 23 דירה 4; המפוח על הגג רועש בלילה

**A.** Expectations: ok called; ok one short question on the empty message; ok no guessed matter on 'it again'. Flags: none.

- **resident:** זה שוב
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. מה בדיוק קורה שוב, ואיפה?
- **resident:** הרעש מהמפוח על הגג, כל לילה אי אפשר לישון
- **Michael:** אוי, רעש כזה כל לילה זה ממש מתיש. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 4
  - `[open_request {"description": "הרעש מהמפוח על הגג שוב, כל לילה אי אפשר לישון", "type": "maintenance", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על הרעש מהמפוח בגג, מספר 255-1409-26. יש עוד משהו שאפשר לעזור בו?

### street_unknown: a lobby leak in a building Homies does not manage

Israel time 16:09. דייר ברחוב הדמיון 7 דירה 2 (רחוב שהומיז לא מנהלת)

**A.** Expectations: ok called; ok no ticket number claimed; ok no invented list of buildings. Flags: none.

- **resident:** יש נזילה בלובי אצלנו
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אוי, לא נעים בכלל. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** הדמיון 7 דירה 2
  - `[open_request {"description": "יש נזילה בלובי של הבניין", "type": "plumbing", "building": "הדמיון 7", "reporter_unit": "2", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** לא מצאתי את רחוב הדמיון ברשימת הבניינים שאנחנו מנהלים, אז הקריאה עוד לא נפתחה. תוכל לבדוק אם שם הרחוב כתוב נכון ולשלוח לי אותו שוב?
- **resident:** רחוב הדמיון 7, זה מה שכתוב
  - `[open_request {"description": "יש נזילה בלובי של הבניין", "type": "plumbing", "building": "רחוב הדמיון 7", "reporter_unit": "2", "fault_location": "common", "urgency": "normal"}]`
  - `[notify_team {"reason": "other", "description": "דייר מדווח על נזילה בלובי של הבניין ברחוב הדמיון 7, הוא גר בדירה 2. הכתובת לא נמצאה ברשימת הבניינים שאנחנו מנהלים, והדייר מאשר שזאת הכתובת, ולכן לא נפתחה קריאה.", "]`
- **Michael:** בדקתי שוב, ורחוב הדמיון 7 עדיין לא מופיע אצלי ברשימת הבניינים שאנחנו מנהלים, אז קריאה לא יכולתי לפתוח. העברתי לצוות את הנזילה בלובי יחד עם הכתובת והדירה שלך, כך שהם יודעים על זה. יש עוד משהו שאוכל לעזור בו?

### photo_nocaption: a photo with no words

Israel time 16:09. דייר בבר כוכבא 23 דירה 4; צינור בחניון מטפטף

**A.** Expectations: ok called; ok does not pretend to see the photo; ok one question on the photo. Flags: none.

- **photo:** 
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 התמונה הגיעה ונשמרה אצלנו, אבל אני לא רואה מה יש בה. תוכל לכתוב לי בכמה מילים מה קרה ואיפה?
- **resident:** זה הצינור בחניון שמטפטף, ליד החניה 12
- **Michael:** אוקיי, טוב שסיפרת. באיזה בניין החניון הזה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 4
  - `[open_request {"description": "הצינור בחניון מטפטף, ליד חניה 12", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי קריאה על הצינור שמטפטף בחניון ליד חניה 12, מספר 255-1411-26, והתמונה ששלחת מצורפת אליה. יש עוד משהו שאפשר לעזור בו?

### goodbye_mid: thanks and goodnight after a ticket earlier today

Israel time 21:10. דייר בבר כוכבא 23 דירה 4 שכבר פתח קריאה לפני רבע שעה

**A.** Expectations: ok nothing opened on a goodbye; ok goodbye without a question; ok no name mid-conversation. Flags: none.

- **resident:** תודה רבה, לילה טוב
- **Michael:** בשמחה, ותודה שפנית אלינו. לילה טוב ושקט 🙂

### hello_then_matter: a bare hello, then cockroaches in the bin room

Israel time 16:09. דיירת בבר כוכבא 23 דירה 4; ג'וקים בחדר האשפה

**A.** Expectations: ok called; ok type pest_control; ok no greeting after the menu; ok the name after the menu; ok no second 'how can I help'. Flags: none.

- **resident:** שלום
- **system:** צהריים טובים 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **resident:** יש ג'וקים בחדר האשפה, מלא
- **Michael:** כאן מיכאל מהומי'ז. אוי, זה ממש לא נעים. באיזה בניין מדובר, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, 4
  - `[open_request {"description": "יש הרבה ג'וקים בחדר האשפה", "type": "pest_control", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי קריאה על הג'וקים בחדר האשפה, מספר 255-1413-26 👍 יש עוד משהו שאוכל לעזור בו?

### how_are_you_he: hi, how are you, then a balance question

Israel time 16:09. דני לוי, בר כוכבא 23 דירה 4, טלפון <phone>

**A.** Expectations: ok called; ok asks back; ok at most two questions on the how-are-you. Flags: none.

- **resident:** היי, מה נשמע?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 אצלי הכול טוב, תודה ששאלת. ואיך עובר עליך היום?
- **resident:** הכל טוב תודה. רציתי לשאול מה היתרה שלי
- **Michael:** שמח לשמוע! תוכל לכתוב לי את השם המלא שלך ומספר טלפון?
- **resident:** דני לוי <phone>
  - `[get_balance {"name": "דני לוי", "phone": "<phone>", "unit": ""}]`
- **Michael:** תודה, דני. על דירה 4 בבר כוכבא 23 רשומה אצלנו יתרה של 620 ₪, על חודש ספטמבר. תרצה לשלם אותה עכשיו?

### second_matter: mid-conversation hello and a second fault, building known

Israel time 16:30. דייר בבר כוכבא 23 דירה 4 שכבר מסר את הבניין והדירה לפני רבע שעה

**A.** Expectations: ok called; ok no name mid-conversation; ok building not asked again. Flags: none.

- **resident:** היי, עוד משהו: גם האינטרקום לא עובד
  - `[open_request {"description": "גם האינטרקום לא עובד", "type": "electrical", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** היי שוב. אינטרקום שלא עובד זה באמת לא נוח. פתחתי קריאה גם עליו, מספר 255-1415-26. יש עוד משהו בבניין שצריך טיפול?

### fem_light_first: a woman reports a stairwell light, the feminine in her first line

Israel time 10:15. מיכל, גרה בבר כוכבא 23 דירה 6; האור בחדר המדרגות בקומה 3 לא נדלק כבר יומיים

**A.** Expectations: ok called; ok never the masculine to her; ok never the plural; ok goodbye without a question. Flags: none.

- **resident:** היי, אני גרה בבר כוכבא 23 דירה 6, והאור בחדר המדרגות בקומה 3 לא נדלק כבר יומיים
  - `[open_request {"description": "האור בחדר המדרגות בקומה 3 לא נדלק כבר יומיים", "type": "lighting", "building": "בר כוכבא 23", "reporter_unit": "6", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. יומיים של חושך במדרגות זה ממש לא נעים. פתחתי קריאה על האור בקומה 3, מספר 255-1420-26. יש עוד משהו שאוכל לעזור לך בו?
- **resident:** תודה רבה!
- **Michael:** בשמחה! תודה שפנית, שיהיה לך יום נעים 🙂

### fem_late_cue: a leak, the feminine only in her second message

Israel time 13:40. דיירת בבר כוכבא 23 דירה 2; מים מטפטפים מהתקרה בחדר המדרגות בקומה הראשונה, ליד הדלת שלה, מהבוקר; לא יודעת מאיפה זה בא

**A.** Expectations: ok called; ok never the plural; ok goodbye without a question. Flags: none.

- **resident:** יש מים שמטפטפים מהתקרה בחדר המדרגות
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אוי, מים מהתקרה זה ממש לא נעים. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 2. אני לא בטוחה מאיפה זה מגיע, אולי מהגג
  - `[open_request {"description": "מים מטפטפים מהתקרה בחדר המדרגות. לא בטוחה מאיפה זה מגיע, אולי מהגג", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "2", "fault_location": "common", "urgency": "high"]`
- **Michael:** אוקיי, פתחתי קריאה על הטפטוף בחדר המדרגות, מספר 255-1421-26, וציינתי בה שאולי זה מגיע מהגג. יש עוד משהו שאת צריכה?
- **resident:** תודה
- **Michael:** בשמחה, תודה שפנית אלינו. שיהיה לך המשך יום נעים 🙂

### fem_pay: a woman asks for the payment link

Israel time 19:05. דיירת בבר כוכבא 23 דירה 4 שרוצה לשלם את הוועד

**A.** Expectations: ok link fetched at once; ok the link as returned; ok never the masculine to her; ok never the plural; ok goodbye without a question. Flags: none.

- **resident:** היי, אני צריכה את הקישור לתשלום הוועד
  - `[get_payment_link {"said": "אני צריכה את הקישור לתשלום הוועד"}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז, אני בודק לך עכשיו את הקישור לתשלום הוועד.
- **Michael:** הנה הקישור לתשלום הוועד של דירה 4 בבר כוכבא 23: / <link> / הקישור אישי לדירה שלך בלבד, אז חשוב לא להעביר אותו הלאה. אם משהו לא ברור, תכתבי לי כאן 🙂
- **resident:** מעולה, תודה
- **Michael:** בשמחה, תודה שפנית. שיהיה לך ערב נעים!

### fem_rep_tap: the representative button, then a woman disputes a charge

Israel time 15:30. דיירת בבר כוכבא 23 דירה 4 שחויבה פעמיים על ספטמבר

**A.** Expectations: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the tap asks how he is, and only that (4 Oct); ok the menu's hour greeting is not repeated; ok called; ok a dispute is a note, not a ticket; ok no call-back promise; ok never the plural; ok goodbye without a question. Flags: none.

- **resident:** היי
- **system:** צהריים טובים 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי, כאן מיכאל מהומי'ז 🙂 מה שלומך היום?
- **resident:** אני חושבת שחייבו אותי פעמיים על ספטמבר, אני רוצה לברר את זה
  - `[notify_team {"reason": "billing", "description": "הדיירת חושבת שחויבה פעמיים על ספטמבר ורוצה לברר את זה", "department": "collections"}]`
- **Michael:** אוי, חיוב כפול זה באמת לא נעים. רשמתי את זה לצוות, והם כבר יודעים. יש עוד משהו שאוכל לעזור לך בו?
- **resident:** תודה
- **Michael:** אין בעד מה, תודה שפנית. שיהיה לך המשך יום נעים 🙏

### rep_fine_thanks: the representative button, a plain 'fine, thanks', then a cleaning question

Israel time 16:20. דייר בבר כוכבא 23 דירה 9 שרוצה לשאול על הניקיון, עונה בקצרה

**A.** Expectations: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the tap asks how he is, and only that (4 Oct); ok the menu's hour greeting is not repeated; ok 'fine, thanks' is not asked again; ok after he answers, how to help is asked (4 Oct); ok no second hello; ok called; ok no frequency invented; ok goodbye without a question. Flags: none.

- **resident:** היי
- **system:** צהריים טובים 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי, כאן מיכאל מהומי'ז 🙂 מה שלומך היום?
- **resident:** טוב תודה
- **Michael:** שמח לשמוע. מה אפשר לעשות בשבילך?
- **resident:** רציתי לשאול כל כמה זמן מנקים את חדר המדרגות
  - `[get_service_info {"topic": "כל כמה זמן מנקים את חדר המדרגות"}]`
- **Michael:** התדירות של הניקיון נקבעת בהסכם של כל בניין, ולכן אין לי מספר קבוע לתת לך. יש משהו בניקיון אצלך בבניין שמפריע לך?
- **resident:** תודה
- **Michael:** בשמחה, תודה שפנית! סוף שבוע נעים 😊

### rep_and_you: the representative button in the evening; he asks back 'and you?', then the intercom

Israel time 20:15. דייר בבר כוכבא 23 דירה 8, מנומס, שואל בחזרה מה שלומו

**A.** Expectations: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the tap asks how he is, and only that (4 Oct); ok the menu's hour greeting is not repeated; ok after he answered, how-are-you is not asked again; ok after he answers, how to help is asked (4 Oct); ok no second hello; ok called; ok no promise after the ticket; ok goodbye without a question. Flags: none.

- **resident:** ערב טוב
- **system:** ערב טוב 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי, מיכאל מהומי'ז כאן 🙂 איך עובר עליך היום?
- **resident:** בסדר גמור, ואתה?
- **Michael:** שמח לשמוע, וגם אצלי הכול טוב, תודה ששאלת. במה אוכל לעזור לך הערב?
- **resident:** רציתי לדווח שהאינטרקום בכניסה לא עובד
- **Michael:** אוי, בלי אינטרקום זה באמת לא נוח. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 8
  - `[open_request {"description": "האינטרקום בכניסה לא עובד", "type": "electrical", "building": "בר כוכבא 23", "reporter_unit": "8", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** תודה. פתחתי קריאה על האינטרקום בכניסה, מספר 255-1451-26 👍 יש עוד משהו שאוכל לעזור בו?
- **resident:** תודה רבה
- **Michael:** בשמחה, ותודה שעדכנת אותנו. ערב נעים וסוף שבוע טוב!

### rep_morning_matter: the representative button in the morning; the answer to how-are-you carries the matter

Israel time 09:05. דיירת בבר כוכבא 23 דירה 5; יש נזילה בחניון מתחת לחניה 3

**A.** Expectations: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the tap asks how he is, and only that (4 Oct); ok the menu's hour greeting is not repeated; ok how-are-you is not asked again; ok the matter is taken up, not 'how can I help' again; ok called; ok the ticket keeps her word; ok goodbye without a question. Flags: none.

- **resident:** בוקר טוב
- **system:** בוקר טוב 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי 🙂 כאן מיכאל מהומי'ז, מה שלומך היום?
- **resident:** הכל טוב, תודה. יש נזילה בחניון, מתחת לחניה 3
- **Michael:** טוב לשמוע. אוי, נזילה בחניון זה לא נעים. באיזה בניין זה, ומה מספר הדירה שלך?
- **resident:** בר כוכבא 23 דירה 5
  - `[open_request {"description": "יש נזילה בחניון, מתחת לחניה 3", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "5", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי קריאה על הנזילה בחניון, מתחת לחניה 3, מספר הקריאה 255-1452-26. יש עוד משהו שאוכל לעזור בו?
- **resident:** תודה
- **Michael:** בשמחה, תודה שעדכנת! יום נעים 🙂

### menu_typed: 'what can I do here', then the status button

Israel time 10:20. דייר בבר כוכבא 23 דירה 6 שלא יודע מה אפשר לעשות בצ'אט; יש לו קריאה פתוחה על נורה ורוצה לדעת מה איתה

**A.** Expectations: ok the options list, not words; ok no options written as a list; ok called; ok the status as returned. Flags: none.

- **resident:** היי, מה אפשר לעשות פה בעצם?
  - `[show_menu {}]`
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז 🙂 הנה מה שאפשר לעשות כאן, מה מתאים לך?
- **tap:** מצב קריאה קיימת
  - `[get_request_status {"reference": "", "building": "", "unit": "", "type": ""}]`
- **Michael:** מצאתי את הקריאה שלך על הנורה השרופה בקומה 2, מספר 255-1488-26. היא נפתחה ב-1 באוקטובר, וכרגע היא בטיפול. יש עוד משהו שתרצה לדעת עליה?

### rep_typed: asks for a person by typing, then a double charge

Israel time 11:05. דייר בבר כוכבא 23 דירה 7 שרוצה לדבר עם בן אדם; חייבו אותו פעמיים על ספטמבר

**A.** Expectations: ok called; ok no who, no when, no callback; ok no office contact unasked; ok goodbye without a question. Flags: none.

- **resident:** אפשר לדבר עם בן אדם אמיתי בבקשה?
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז, ואני איתך. אצלנו, לפני שמשהו עובר למישהו בצוות, צריך קודם לדעת במה מדובר, כדי שמי שיקבל את זה יוכל באמת לטפל בזה. מה קרה?
- **resident:** חייבו אותי פעמיים על ספטמבר
  - `[notify_team {"reason": "billing", "description": "הדייר אומר שחייבו אותו פעמיים על ספטמבר, וביקש לדבר עם בן אדם.", "department": "collections"}]`
- **Michael:** אוי, חיוב כפול זה באמת לא נעים. רשמתי את זה לצוות, והם יודעים על זה. יש עוד משהו שאוכל לעזור לך בו?
- **resident:** תודה
- **Michael:** בשמחה, תודה שפנית! שיהיה לך שבוע טוב 🙂

### office_hours: the office's opening hours, in the evening

Israel time 18:30. דייר בבר כוכבא 23 דירה 12 שרוצה לדעת מתי המשרד פתוח

**A.** Expectations: ok opens at 09:00; ok closes at 17:00; ok evening greeting at 18:30; ok goodbye without a question. Flags: none.

- **resident:** מה שעות הפעילות של המשרד?
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז 🙂 המשרד פתוח בימים ראשון עד חמישי, בין 09:00 ל-17:00, כך שהיום הוא כבר סגור. יש משהו שאני יכול לעזור לך בו כבר עכשיו?
- **resident:** תודה, סבבה
- **Michael:** בשמחה! תודה שפנית, ושיהיה לך ערב נעים.

### night_flood: 02:40, water pouring from the stairwell ceiling by a light

Israel time 02:40. דייר בבר כוכבא 23 דירה 5; באמצע הלילה מים יורדים בכמויות מהתקרה בחדר המדרגות, ממש ליד המנורה בקומה 3

**A.** Expectations: ok called; ok called; ok flooding by a light is an emergency; ok no emoji in an emergency; ok שלום before 05:00; ok no instructions, no referral; ok no help-on-the-way, no don't-worry. Flags: none.

- **resident:** יש מים שיורדים בכמויות מהתקרה בחדר המדרגות, ממש ליד המנורה בקומה 3
  - `[notify_team {"reason": "emergency", "description": "יש מים שיורדים בכמויות מהתקרה בחדר המדרגות, ממש ליד המנורה בקומה 3. הבניין עוד לא ידוע", "department": "operations"}]`
- **Michael:** שלום, כאן מיכאל מהומי'ז. זה נשמע רציני, והצוות שלנו כבר יודע. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, דירה 5
  - `[open_request {"description": "יש מים שיורדים בכמויות מהתקרה בחדר המדרגות, ממש ליד המנורה בקומה 3", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "5", "fault_location": "common", "urgency": "emerg]`
- **Michael:** פתחתי קריאה דחופה על המים בחדר המדרגות, מספר 255-1490-26. יש עוד משהו שראית שם שחשוב שאדע?
- **resident:** מה אני עושה עכשיו?
- **Michael:** פתחתי לך קריאה דחופה, מספר 255-1490-26, והצוות יודע עליה. זה הדבר היחיד שאני יכול לעשות מכאן.
- **resident:** תודה, טוב
- **Michael:** תודה שעדכנת אותנו, ומקווה שתצליח לנוח קצת הלילה.

### photo_caption: a photo with a caption: the entrance light

Israel time 13:15. דייר בבר כוכבא 23 דירה 10; הנורה בכניסה לבניין שרופה, והוא שולח תמונה שלה עם כיתוב

**A.** Expectations: ok called; ok the number as returned; ok does not pretend to see the photo; ok goodbye without a question. Flags: none.

- **photo:** הנורה בכניסה לבניין שרופה, צירפתי תמונה
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. נורה שרופה בכניסה זה באמת לא נעים. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, דירה 10
  - `[open_request {"description": "הנורה בכניסה לבניין שרופה", "type": "lighting", "building": "בר כוכבא 23", "reporter_unit": "10", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי קריאה על הנורה בכניסה לבניין, מספר 255-1491-26 👍 יש עוד משהו שאפשר לעזור בו?
- **resident:** תודה!
- **Michael:** בשמחה, ותודה שעדכנת אותנו! שיהיה לך המשך יום נעים.

### voice_note: a voice note with no text, then the lift in words

Israel time 09:40. דייר בבר כוכבא 23 דירה 9; שלח הקלטה קולית, והמעלית תקועה בקומה 4 בלי אף אחד בפנים

**A.** Expectations: ok does not pretend to hear it; ok one question on the recording; ok called; ok nobody inside: not an emergency. Flags: none.

- **file / voice note:** 
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז 🙂 הקלטות וקבצים אני לא יכול לפתוח מכאן. תוכל לכתוב לי בכמה מילים במה מדובר?
- **resident:** סליחה, שלחתי הקלטה. המעלית תקועה בקומה 4 ולא זזה, אין אף אחד בפנים
- **Michael:** אין בעיה בכלל. מעלית שלא זזה זה ממש לא נוח. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 9
  - `[open_request {"description": "המעלית תקועה בקומה 4 ולא זזה, אין אף אחד בפנים", "type": "elevator", "building": "בר כוכבא 23", "reporter_unit": "9", "fault_location": "common", "urgency": "high"}]`
- **Michael:** פתחתי קריאה על המעלית התקועה, מספר 255-1492-26 👍 אפשר לעזור במשהו נוסף?

### status_not_found: a ticket number that does not exist, then the building

Israel time 15:00. דייר בבר כוכבא 23 דירה 8; שואל על קריאה במספר שהקליד לא נכון

**A.** Expectations: ok called; ok no invented status for an unknown number; ok the ticket found by the building. Flags: none.

- **resident:** מה קורה עם קריאה 255-9999-26?
  - `[get_request_status {"reference": "255-9999-26"}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. לא מצאתי קריאה עם המספר 255-9999-26. באיזה בניין מדובר?
- **resident:** בר כוכבא 23, זה המספר שקיבלתי לפני שבוע
  - `[get_request_status {"building": "בר כוכבא 23"}]`
- **Michael:** מצאתי בבר כוכבא 23 קריאה על רטיבות בקיר בחדר המדרגות, מספר 255-1450-26. היא נפתחה ב-27 בספטמבר ועדיין פתוחה. זאת הקריאה שהתכוונת אליה?

### balance_identity: a balance whose name and phone do not match

Israel time 12:10. דייר בבר כוכבא 23 דירה 14 ששואל כמה הוא חייב; השם והטלפון שהוא מקליד לא תואמים את הרישום

**A.** Expectations: ok name and phone asked first; ok called; ok no amount revealed. Flags: none.

- **resident:** כמה אני חייב לוועד?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 אין בעיה, מה השם המלא שלך ומספר הטלפון?
- **resident:** יוסי מזרחי, <phone>
  - `[get_balance {"name": "יוסי מזרחי", "phone": "<phone>"}]`
- **Michael:** השם והמספר האלה לא תואמים למה שרשום אצלנו, ולכן את היתרה אני לא יכול להציג. אולי הדירה רשומה על שם אחר או עם מספר טלפון אחר, למשל של בן משפחה?
- **resident:** זה השם והמספר שלי, אני בטוח
  - `[notify_team {"reason": "other", "description": "הדייר שאל כמה הוא חייב לוועד. הוא מסר שם מלא יוסי מזרחי וטלפון <phone>, אבל הם לא תואמים לרישום אצלנו, והוא בטוח שאלה השם והמספר שלו. לא הצלחתי לאמת את הזהות ולכן ל]`
- **Michael:** אם אלה הפרטים שלך, כנראה משהו ברישום אצלנו לא מסתדר, ואת זה רק מישהו מהצוות יכול לברר. רשמתי להם את הבקשה שלך לדעת את היתרה, יחד עם השם והמספר שכתבת, אז הם יודעים. יש עוד משהו בינתיים שאני יכול לעזור בו?

### angry_repeat: the third report of a stuck lift, angry

Israel time 08:15. דייר בבר כוכבא 23 דירה 4, מתוסכל: זאת הפעם השלישית שהוא מדווח על המעלית שתקועה בקומה 3

**A.** Expectations: ok no promise of when; ok singular although he wrote איתכם; ok morning greeting at 08:15. Flags: none.

- **resident:** זאת הפעם השלישית שאני מדווח שהמעלית תקועה בקומה 3 ואף אחד לא בא!! מה קורה איתכם?
  - `[get_request_status {"type": "elevator"}]`
  - `[notify_team {"reason": "other", "description": "הדייר מדווח בפעם השלישית שהמעלית תקועה בקומה 3 ושאף אחד לא הגיע. יש קריאה פתוחה 255-1470-26 מה-1.10, בסטטוס בטיפול. הוא מתוסכל מאוד ושואל מה קורה.", "department": "]`
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. מצטער שזה נמשך ככה. הקריאה שלך על המעלית שתקועה בקומה 3, מספר 255-1470-26, נפתחה ב-1 באוקטובר והיא בטיפול. עדכנתי עכשיו את הצוות שזאת כבר הפעם השלישית שאתה מדווח ושעדיין אף אחד לא הגיע. יש עוד משהו על המעלית שחשוב שהם יידעו?
- **resident:** מתי מישהו יגיע?
- **Michael:** שעה או יום מדויקים אין לי, ואני לא רוצה לנחש לך. הקריאה בטיפול, והצוות יודע שזאת כבר הפעם השלישית, אז זה יטופל כמו שצריך. אתה מסתדר בינתיים עם המדרגות?

### two_faults: two faults in one message, evening

Israel time 17:45. דייר בבר כוכבא 23 דירה 11; נורה שרופה בקומה 2 וגם האינטרקום בכניסה לא עובד

**A.** Expectations: ok called; ok building and apartment asked first; ok one question; ok a number as returned. Flags: none.

- **resident:** ערב טוב, יש נורה שרופה בקומה 2 וגם האינטרקום בכניסה לא עובד
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. אוי, שתיים בבת אחת, לא נעים. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 11
  - `[open_request {"description": "יש נורה שרופה בקומה 2", "type": "lighting", "building": "בר כוכבא 23", "reporter_unit": "11", "fault_location": "common", "urgency": "normal"}]`
  - `[open_request {"description": "האינטרקום בכניסה לא עובד", "type": "electrical", "building": "בר כוכבא 23", "reporter_unit": "11", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי שתי קריאות: על הנורה בקומה 2, מספר 255-1494-26, ועל האינטרקום בכניסה, מספר 255-1495-26 👍 יש עוד משהו שאפשר לעזור בו?

### neighbor_noise: a noisy neighbour at night

Israel time 23:10. דייר בבר כוכבא 23 דירה 13; השכן מעליו עושה רעש כל לילה

**A.** Expectations: ok no ticket for a neighbour dispute; ok no referral; ok evening greeting at 23:10. Flags: none.

- **resident:** השכן מעליי עושה רעש כל לילה עד 2 בלילה, אני לא מצליח לישון
  - `[notify_team {"reason": "other", "description": "הדייר מתלונן שהשכן שגר מעליו עושה רעש כל לילה עד 2 בלילה, והוא לא מצליח לישון.", "department": "management"}]`
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. לילות בלי שינה זה ממש מתיש, מצטער שאתה עובר את זה. רעש מדירה של שכן זה לא משהו שהומי'ז מטפלת בו, אנחנו אחראים על הרכוש המשותף ועל המערכות של הבניין, אבל רשמתי את זה לצוות, אז הם יודעים על זה. יש משהו בבניין עצמו שאני יכול לעזור לך בו?
- **resident:** אז מה אני אמור לעשות?
- **Michael:** על זה אני לא יכול לייעץ לך, ואני יודע שזה לא מה שקיווית לשמוע. מה שיכולתי לעשות מכאן זה לרשום את זה לצוות, וזה כבר אצלם. יש עוד משהו על הרעש שחשוב שהם יידעו?

### cancel_ticket: cancel the ticket opened earlier today

Israel time 16:40. דייר בבר כוכבא 23 דירה 4 שפתח קריאה על נורה לפני שעתיים, והשכן כבר החליף אותה

**A.** Expectations: ok called; ok no claim of cancelling; ok no name mid-conversation; ok goodbye without a question. Flags: none.

- **resident:** תעשה לי טובה תבטל את הקריאה, מתברר שהשכן כבר החליף את הנורה
  - `[get_request_status {"reference": "255-1480-26", "building": "בר כוכבא 23", "type": "lighting"}]`
  - `[notify_team {"reason": "other", "description": "הדייר מבר כוכבא 23 דירה 4 מבקש לבטל את הקריאה 255-1480-26 על הנורה בקומה 1 בחדר המדרגות: מתברר שהשכן כבר החליף את הנורה.", "department": "operations"}]`
- **Michael:** יופי, טוב שזה הסתדר 👍 הצוות כבר יודע שאתה מבקש לבטל את הקריאה על הנורה, 255-1480-26. יש עוד משהו שאני יכול לעשות בשבילך?
- **resident:** תודה, מעולה
- **Michael:** בשמחה, ותודה שעדכנת! שיהיה לך המשך יום נעים.

### english_pay: how do I pay, in English

Israel time 19:20. an English-speaking resident of בר כוכבא 23 apartment 12 who wants to pay the building fees

**A.** Expectations: ok link fetched at once; ok the link as returned; ok answers in Hebrew (the rule); ok goodbye without a question. Flags: none.

- **resident:** Hi, how do I pay my building fees?
  - `[get_payment_link {"said": "איך משלמים את דמי הוועד שלי?"}]`
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז, אני בודק לך עכשיו את פרטי התשלום במערכת.
- **Michael:** זה הקישור לתשלום דמי הוועד של בר כוכבא 23, דירה 12: / <link> / הוא אישי לדירה שלך בלבד, אז עדיף לא להעביר אותו הלאה. ואם משהו לא ברור, אפשר לכתוב לי כאן.
- **resident:** thanks, got it
- **Michael:** בשמחה, תודה שפנית! ערב נעים 🙂

### rep_then_pay: the representative button, 'fine', then a payment

Israel time 14:30. דייר בבר כוכבא 23 דירה 15 שפותח בהיי, לוחץ לדבר עם נציג, ורוצה לשלם את הוועד

**A.** Expectations: ok link fetched at once; ok the link as returned; ok the representative asks how he is; ok no re-ask after he named the matter; ok goodbye without a question. Flags: none.

- **resident:** היי
- **system:** צהריים טובים 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי, כאן מיכאל מהומי'ז, שמח לשמוע ממך 🙂 מה שלומך היום?
- **resident:** טוב תודה, רציתי לשלם את הוועד
  - `[get_payment_link {"said": "רציתי לשלם את הוועד"}]`
- **Michael:** שמח לשמוע! אני בודק לך עכשיו את פרטי התשלום, רק רגע.
- **Michael:** הנה הקישור לתשלום הוועד של דירה 15 בבר כוכבא 23: / <link> / הקישור אישי לדירה שלך ולא כדאי להעביר אותו לאחרים. ואם משהו לא ברור, אני כאן, פשוט תכתוב לי.
- **resident:** תודה רבה
- **Michael:** בשמחה, תודה שפנית אליי! שיהיה לך המשך יום נעים 😊

### unknown_question: is there a gym in the building (nobody knows)

Israel time 11:50. דייר בבר כוכבא 23 דירה 16 ששואל אם יש חדר כושר בבניין

**A.** Expectations: ok no invented answer about the building; ok morning greeting at 11:50; ok goodbye without a question. Flags: none.

- **resident:** יש בבניין שלנו חדר כושר לדיירים?
  - `[get_service_info {"topic": "חדר כושר לדיירים בבניין"}]`
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. על חדר כושר לדיירים בבניין אין לי כרגע מידע. יש משהו אחר שאני יכול לעזור לך בו?
- **resident:** תודה, אוקיי
- **Michael:** בשמחה, תודה שכתבת! שיהיה לך יום טוב 🙂

### manager_insists: asks for a manager, insists, then says what it is: a complaint about the house manager (18 Oct)

Israel time 10:40. דייר בבר כוכבא 23 דירה 6 שרוצה להתלונן על אב הבית, ומתעקש בהתחלה לדבר עם מנהל

**A.** Expectations: ok the first reply asks for the details; ok the first reply hands the turn back with a question; ok no team note on the first two replies; ok asks what it is about before the team note; ok the second reply still asks what it is about; ok when he insists, the reply says why the details are needed (18 Oct, late); ok never the same question in the same words ("like a parrot"); ok called; ok the note carries what happened; ok no who, no when, no callback; ok goodbye without a question. Flags: none.

- **resident:** אני רוצה לדבר עם מנהל
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. בטח, אני איתך. אצלנו, לפני שמשהו עובר למנהל צריך לדעת במה מדובר, כדי שמי שיקבל את זה יוכל באמת לטפל בו. מה קרה?
- **resident:** לא, אני צריך מנהל. זה חשוב
- **Michael:** זה באמת מתסכל כשמשהו חשוב לך ורק רוצים להגיע למנהל. אבל בלי לדעת על מה מדובר, מי שיקבל את הפנייה לא יוכל לעשות איתה כלום. לא צריך לפרט הכול, משפט אחד מספיק 🙏 מה הנושא?
- **resident:** אב הבית דיבר אליי אתמול בצורה ממש לא מכבדת מול השכנים, ואני רוצה שמנהל יטפל בזה
  - `[notify_team {"reason": "caller_request", "description": "הדייר ביקש לדבר עם מנהל. לדבריו, אב הבית דיבר אליו אתמול בצורה ממש לא מכבדת מול השכנים, והוא רוצה שמנהל יטפל בזה.", "department": "management"}]`
- **Michael:** אוי, זה באמת לא נעים, במיוחד מול השכנים. רשמתי את זה לצוות עם כל מה שסיפרת, והם יודעים. יש עוד משהו שאני יכול לעשות בשבילך?
- **resident:** תודה
- **Michael:** בשמחה, ותודה שפנית. שיהיה לך המשך יום נעים 🙂

### manager_wont_say: asks for a manager, insists, and will not say why (18 Oct; late: nothing goes on without the matter)

Israel time 12:15. דייר בבר כוכבא 23 דירה 11 שרוצה רק מנהל ולא מוכן להסביר לבוט על מה

**A.** Expectations: ok the first reply asks for the details; ok when he insists, the reply says why (turn 1); ok when he will not say, the reply says why (turn 2); ok no empty note, however often he asks (18 Oct, late); ok never the same question in the same words; ok no who, no when, no callback, even when he asks for one; ok goodbye without a question. Flags: none.

- **resident:** תעביר אותי למנהל בבקשה
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 בטח, אני כאן. אצלנו, לפני שמשהו עובר למנהל, חשוב לדעת על מה מדובר, כדי שמי שיקבל את זה יוכל באמת לטפל בו. מה קרה?
- **resident:** לא צריך עזרה ממך, אני רוצה מנהל
- **Michael:** אני לא מנסה לעכב אותך, ואני יודע שזה מתסכל כשרוצים פשוט להגיע למנהל. רק שבלי לדעת מה הנושא, אין לי מה להעביר הלאה. לא צריך לפרט, מילה או שתיים מספיקות. על מה מדובר, בגדול?
- **resident:** זה עניין אישי, אני לא רוצה לפרט. רק שהמנהל ידע שחיפשתי אותו
- **Michael:** את הפרטים האישיים אתה ממש לא צריך לספר לי. מה שחסר לי זה רק הנושא, אפילו בכותרת כללית, כי בקשה בלי שום נושא אני לא יכול לרשום, ומי שיקבל אותה לא יידע מאיפה להתחיל 🙏 לאיזה נושא זה קשור?
- **resident:** תודה
- **Michael:** בשמחה, ותודה שפנית. אם תרצה לחזור לזה, מספיק לכתוב לי כאן את הנושא, גם בכמה מילים. שיהיה לך המשך יום טוב!

### manager_typed_mid: types a request for a manager in the middle of a chat (18 Oct, the owner's handset: executions 112521, 112529)

Israel time 17:20. דייר בבר כוכבא 23 דירה 5 שכבר שאל על הניקיון, ועכשיו רוצה מנהל כי הוועד החליט על שיפוץ בלובי בלי לשאול אף אחד

**A.** Expectations: ok no how-are-you he did not ask for (112521); ok the reply asks for the details; ok no team note before the details; ok called; ok the note carries what he wants; ok goodbye without a question. Flags: none.

- **resident:** אני רוצה לדבר עם מנהל
- **Michael:** ברור, יש דברים שצריך בשבילם מישהו עם סמכות. אצלנו, לפני שמשהו עובר למנהל, צריך לדעת במה מדובר, כדי שמי שיקבל את זה יוכל באמת לטפל בו. מה קרה?
- **resident:** הוועד החליט על שיפוץ בלובי בלי לשאול אף אחד, ואני רוצה להתנגד
  - `[notify_team {"reason": "caller_request", "description": "הדייר ביקש לדבר עם מנהל. לדבריו הוועד החליט על שיפוץ בלובי בלי לשאול אף אחד מהדיירים, והוא רוצה להתנגד להחלטה.", "department": "management"}]`
- **Michael:** מובן לגמרי, על דבר כזה רוצים שישאלו. רשמתי את ההתנגדות שלך לצוות, והם יודעים 👍 יש עוד משהו שאוכל לעשות בשבילך?
- **resident:** תודה
- **Michael:** על לא דבר, ותודה שפנית. שיהיה לך ערב נעים!

### manager_parrot: asks for a manager five times, in Hebrew and English, and asks if Michael is the manager (18 Oct, late: the owner's handset, executions 112601-112635)

Israel time 18:05. דייר בבר כוכבא 23 דירה 2 שכותב גם באנגלית, רוצה מנהל ולא מבין למה צריך להסביר לבוט; רק אחרי שמסבירים לו למה, הוא מספר שחייבו אותו פעמיים על ועד הבית של ספטמבר

**A.** Expectations: ok no how-are-you he did not ask for (112521); FAIL turn 1 says why the details are needed; ok "are you the manager?" is answered with who he is (112618); ok no fragment where the name was (112618); FAIL turn 3 says why; FAIL turn 4 says why; ok never the same question in the same words ("like a parrot"); ok no team note before the matter; ok called; ok the note carries the double charge; ok no who, no when, no callback; ok goodbye without a question. Flags: none.

- **resident:** אני רוצה לדבר עם מנהל
- **Michael:** אני כאן איתך. אצלנו, לפני שמשהו עובר למנהל, צריך לדעת על מה מדובר, כדי שמי שיקבל את זה יוכל באמת לטפל בו. מה קרה?
- **resident:** no i just need a manager
- **Michael:** זה מתסכל כשרוצים פשוט מנהל, ואני לא מנסה להתחמק ממך. אבל בקשה בלי נושא אין לי איך להעביר, היא פשוט לא אומרת למנהל כלום. מספיקות כמה מילים, בלי פרטים 🙏 במה מדובר?
- **resident:** why would i tell you are you the manager?
- **Michael:** שאלה הוגנת. אני לא המנהל, אני מיכאל מצוות השירות של הומי'ז, והפניות לצוות עוברות דרכי. בשביל זה מספיקה לי מילה אחת על מה זה, בלי שום פרט. אז מה הנושא?
- **resident:** i want to talk with the manager
- **Michael:** רואה שאתה כבר כמה פעמים מבקש את זה, ואני מצטער שזה לוקח יותר ממה שרצית. לחבר אותך ישירות למנהל מכאן אני לא יכול, אבל לרשום לצוות את מה שחשוב לך אני כן, וזה מתחיל ממילה אחת על מה זה. זה קשור לתשלום, לתקלה בבניין או למשהו אחר?
- **resident:** i told you i want a manager just get me one are you not listening
- **Michael:** אני מקשיב, ואני לא מנסה לסנן אותך, באמת. כל מה שחסר לי זה הנושא, וגם חצי משפט מספיק. על מה תרצה לדבר עם המנהל?
- **resident:** fine. i was charged twice for the september committee fee
  - `[notify_team {"reason": "billing", "description": "הדייר ביקש לדבר עם מנהל. לדבריו חויב פעמיים על דמי ועד הבית של ספטמבר.", "department": "collections"}]`
- **Michael:** אוי, זה באמת לא נעים לגלות. רשמתי לצוות את החיוב הכפול של ספטמבר, והם יודעים. יש עוד משהו שרצית להעלות?
- **resident:** ok thanks
- **Michael:** בשמחה, ותודה על הסבלנות 🙏 שיהיה לך ערב נעים!

### status_repeat: asks what is happening with his ticket, and asks again (19 Oct: the owner's chat on a second number, executions 114483 and 114536)

Israel time 14:30. דייר בבר כוכבא 23 דירה 2 שפתח לפני שבוע קריאה על התאורה בחדר המדרגות ולא שמע כלום. לא זוכר מספר קריאה ולא מבין למה שואלים אותו. אם מבקשים ממנו מספר או כתובת, הוא כותב שוב את אותה שאלה בדיוק

**A.** Expectations: ok called; ok no new ticket; ok the status is given on the first ask; ok no number or address asked before looking (114528); ok no question asked twice in the same words (114536); ok answered without a second ask. Flags: none.

- **resident:** היי מה קורה?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 הכול טוב אצלי, תודה ששאלת! ומה איתך, איך עובר עליך היום?
- **resident:** הכל טוב תודה. מה קורה עם הקריאה שפתחתי אני לא מבין
  - `[get_request_status {}]`
- **Michael:** שמח לשמוע! הקריאה שלך על התאורה בחדר המדרגות בקומה 3, מספר 255-1402-26, נמצאת בטיפול. היא נפתחה ב-12.10, והעדכון האחרון בה היה ב-18.10. זאת הקריאה שהתכוונת אליה?
- **resident:** כן זאת
- **Michael:** מעולה 👍 יש עוד משהו שאוכל לעזור לך בו?
- **resident:** אוקיי תודה
- **Michael:** בשמחה! תודה שפנית, ושיהיה לך המשך יום נעים

### status_none_by_phone: asks about his ticket, but nothing is on record for his number (19 Oct)

Israel time 14:30. דייר בסוקולוב 86 שכותב מטלפון חדש; פתח קריאה בטלפון למשרד על הדלת של החניון ואין לו מספר

**A.** Expectations: ok the lookup first, with nothing; ok then the number or the building is asked for; ok one question; FAIL no new ticket; FAIL no ticket claimed; ok questions_distinct. Flags: none.

- **resident:** מה קורה עם הקריאה שפתחתי?
  - `[get_request_status {}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. לא מצאתי קריאה שרשומה על המספר שממנו אתה כותב. יש לך את מספר הקריאה, או לפחות באיזה בניין מדובר?
- **resident:** אין לי מספר. סוקולוב 86
  - `[get_request_status {"building": "סוקולוב 86"}]`
- **Michael:** אין בעיה. גם לפי סוקולוב 86 לא מופיעה אצלי קריאה במערכת, אבל אפשר לפתוח אותה מחדש. על מה היא הייתה?
- **resident:** על הדלת של החניון
  - `[open_request {"description": "הדלת של החניון. הדייר אומר שכבר פתח על זה קריאה בעבר, והיא לא נמצאה במערכת לא לפי הטלפון ולא לפי הבניין", "type": "maintenance", "building": "סוקולוב 86", "fault_location": "common", ]`
- **Michael:** פתחתי לך קריאה חדשה על הדלת של החניון בסוקולוב 86, מספר 255-1496-26. יש עוד משהו שאוכל לעזור בו?
- **resident:** תודה
- **Michael:** בשמחה, תודה שפנית! שיהיה לך המשך יום טוב 🙂

### status_tap_found: the status button, and his number finds the ticket (19 Oct)

Israel time 10:15. דיירת בבר כוכבא 23 שלא זוכרת מספר קריאה

**A.** Expectations: ok the lookup on the tap itself; ok the status on the tap; ok one question on the tap; ok no greeting after the menu; ok no new ticket. Flags: none.

- **resident:** היי
- **system:** בוקר טוב 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** מצב קריאה קיימת
  - `[get_request_status {}]`
- **Michael:** כאן מיכאל מהומי'ז, נעים להכיר 🙂 הקריאה שלך על התאורה בחדר המדרגות בקומה 3, מספר 255-1402-26, נמצאת בטיפול. היא נפתחה ב-12.10, והעדכון האחרון בה היה ב-18.10. יש עוד משהו שתרצה לדעת עליה?
- **resident:** תודה רבה
- **Michael:** בכיף, תודה שפנית! שיהיה לך יום נעים

### manager_glued_tap: a pasted "talk to a representative" glued to a ticket question, then the question again (19 Oct: the owner's handset, executions 114528 and 114536)

Israel time 14:37. דייר בבר כוכבא 23 דירה 2 שבודק את הבוט מהטלפון: לוחץ על נציג, עונה על מה שלומו, ואז מדביק בטעות את טקסט הכפתור לפני השאלה שלו על הקריאה. אם מבקשים ממנו מספר או כתובת, הוא כותב את השאלה שוב בלי הטקסט המודבק

**A.** Expectations: ok called; ok a pasted button text is not a request for a person; ok no new ticket; ok the status on the glued message; ok no echo (the chat is not about a manager); ok no question asked twice in the same words. Flags: how-are-you-again.

- **resident:** hello
- **system:** צהריים טובים 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי, כאן מיכאל מהומי'ז 🙂 מה שלומך היום?
- **resident:** היי מה שלומך
- **Michael:** הכול טוב אצלי, תודה ששאלת! ואצלך, איך עובר היום?
  - flags: how-are-you-again: הכול טוב אצלי, תודה ששאלת! ואצלך, איך עובר היום?
- **resident:** לדבר עם נציגהכל טוב תודה. מה קורה עם הקריאה שפתחתי אני לא מבין PNG
  - `[get_request_status {}]`
- **Michael:** טוב לשמוע 🙂 הקריאה שפתחת היא על התאורה בחדר המדרגות בקומה 3, מספר 255-1402-26, והיא בטיפול. היא נפתחה ב-12.10, והעדכון האחרון בה היה ב-18.10. יש משהו לגביה שעדיין לא ברור לך?
- **resident:** תודה
- **Michael:** בשמחה! תודה שכתבת, ושיהיה לך המשך יום טוב
