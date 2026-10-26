# WhatsApp bot QA, qa-yariv-scripted: Claude-played A/B/C on the live code

## Totals

| variant | conversations | model turns | guard rejections | rubric flags | expectations met | failed | judge wins |
|---|---|---|---|---|---|---|---|
| A | 12 | 33 | 0 | 0 | 57 | 0 | 12 |

## Scenarios

### pay_link: I want to pay

Israel time 14:00. דייר בבר כוכבא 23 דירה 4 שרוצה לשלם

Judge (blind): ranking A. Only one conversation, X.

**A.** Expectations: ok link fetched at once; ok the link as returned; ok nothing asked before the link; ok link marked personal; ok goodbye without a question. Flags: none.
Judge: Clean: an 'on it' message with צהריים טובים and the name, then the link for flat 4 in Bar Kochba 23 exactly as returned, personal and not to be passed on, write to me here, no further question; warm goodbye with no question. The packet's ' / ' on each side of the link is read as line breaks.

- **resident:** אני רוצה לשלם את הוועד
  - `[get_payment_link {"said": "אני רוצה לשלם את הוועד"}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז, רק רגע ואני בודק לך את פרטי התשלום.
- **Michael:** זה הקישור לתשלום של דירה 4 בבר כוכבא 23: / <link> / הקישור אישי לדירה שלך בלבד, אז עדיף לא להעביר אותו הלאה. אם משהו לא ברור, פשוט תכתוב לי כאן 🙂
- **resident:** קיבלתי, תודה
- **Michael:** בשמחה, ותודה שפנית! שיהיה לך סוף שבוע נעים.

### balance: how much do I owe

Israel time 14:00. דני לוי, בר כוכבא 23 דירה 4, טלפון <phone>

Judge (blind): ranking A. Only one conversation in this packet.

**A.** Expectations: ok called; ok no unasked link; ok never asks which apartment; ok states the amount; ok name and phone in one question. Flags: none.
Judge: Right greeting for 14:00 and name once, name and phone in one plain question with no why, amount and months in its own words matching the visible part of the cut-off tool result, no apartment question; the conversation closes on a payment question, not an offer to help with anything else. Violations: A finished matter ends with an offer to help with anything else (check offer_at_end): the balance answer, which is the last message, closes on a pay-now question instead (רוצה לשלם את זה עכשיו?)

- **resident:** כמה אני חייב לוועד?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 אין בעיה, תוכל לכתוב לי את השם המלא שלך ומספר טלפון?
- **resident:** דני לוי, <phone>
  - `[get_balance {"name": "דני לוי", "phone": "<phone>"}]`
- **Michael:** תודה, דני. על דירה 4 בבר כוכבא 23 יש כרגע יתרה פתוחה של 1,240 ₪, על יולי, אוגוסט וספטמבר. רוצה לשלם את זה עכשיו?

### balance_identity: a balance whose name and phone do not match

Israel time 12:10. דייר בבר כוכבא 23 דירה 14 ששואל כמה הוא חייב; השם והטלפון שהוא מקליד לא תואמים את הרישום

Judge (blind): ranking A. Only one conversation in this packet.

**A.** Expectations: ok name and phone asked first; ok called; ok no amount revealed. Flags: none.
Judge: Right greeting for 12:10 and name once; name and phone asked in one plain question before the lookup, using the typed number; the mismatch said plainly in his own words with no amount or detail revealed; when he insists, notify_team is really called and the payment link is offered instead of repeating the ask.

- **resident:** כמה אני חייב לוועד?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. בשמחה, מה השם המלא שלך ומספר הטלפון?
- **resident:** יוסי מזרחי, <phone>
  - `[get_balance {"name": "יוסי מזרחי", "phone": "<phone>"}]`
- **Michael:** תודה, יוסי. לא הצלחתי לאמת את השם והמספר מול מה שרשום אצלנו, ולכן אני לא יכול להציג את היתרה. יכול להיות שהדירה רשומה על שם אחר או עם מספר טלפון אחר?
- **resident:** זה השם והמספר שלי, אני בטוח
  - `[notify_team {"reason": "other", "department": "collections", "description": "הדייר שאל כמה הוא חייב לוועד. הוא מסר את השם יוסי מזרחי והטלפון <phone>, אבל הפרטים לא תאמו לרישום והיתרה לא הוצגה לו. הוא אומר שזה השם]`
- **Michael:** אני מאמין לך. רשמתי את זה לצוות, עם השם והמספר שכתבת, והם יודעים שביקשת לדעת את היתרה ושהפרטים לא עברו את האימות. רוצה בינתיים את הקישור לתשלום של הדירה?

### street_unknown: a lobby leak in a building Homies does not manage

Israel time 16:09. דייר ברחוב הדמיון 7 דירה 2 (רחוב שהומיז לא מנהלת)

Judge (blind): ranking A. Only one conversation, X.

**A.** Expectations: ok called; ok no ticket number claimed; ok no invented list of buildings. Flags: none.
Judge: The first re-ask after street_unknown was right, and there is no ticket claim, invented list or office referral, but after the resident confirmed the address Michael kept looking for another address instead of saying plainly that Homies does not manage it. The description's 'של הבניין' for 'אצלנו' adds no fact and is not counted. Violations: honest_refusal: after street_unknown, ask for the street once more or say plainly that Homies does not manage the building; after the second street_unknown Michael asks for an address yet again, leaving it open instead of closing plainly (יש לבניין אולי כתובת נוספת, למשל כניסה מרחוב אחר?)

- **resident:** יש נזילה בלובי אצלנו
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אוי, לא נעים. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** הדמיון 7 דירה 2
  - `[open_request {"description": "יש נזילה בלובי של הבניין", "type": "plumbing", "building": "הדמיון 7", "reporter_unit": "2", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** לא מצאתי את הדמיון 7 בין הבניינים שאנחנו מנהלים, ולכן הקריאה לא נפתחה. אולי שם הרחוב כתוב קצת אחרת, תוכל לבדוק?
- **resident:** רחוב הדמיון 7, זה מה שכתוב
  - `[open_request {"description": "יש נזילה בלובי של הבניין", "type": "plumbing", "building": "רחוב הדמיון 7", "reporter_unit": "2", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** תודה שבדקת 🙏 רחוב הדמיון 7 לא מופיע אצלנו בין הבניינים שהומי'ז מנהלת, אז אין לי איך לפתוח עליו קריאה. יש לבניין אולי כתובת נוספת, למשל כניסה מרחוב אחר?

### sink_private: a blocked kitchen sink, in English

Israel time 16:09. a resident writing in English, Bar Kochba 23 apartment 4

Judge (blind): ranking A. Only one conversation, X.

**A.** Expectations: ok no ticket for a private fault; ok no tradesman recommended; ok does not explain the rule; ok goodbye without a question. Flags: none.
Judge: Hebrew reply to English with צהריים טובים and the name once, a kind word, no ticket, no tradesman, an offer to help and a warm goodbye with no question; the one fault is that the refusal is put as the rule itself. Violations: A fault inside the flat: no explanation of the rule (no_rule_lecture); the refusal states the general rule of when a fault is the tenant's instead of only saying this one is theirs (כיור בתוך הדירה הוא באחריות הדייר, אז על זה לא נפתחת אצלנו ק)

- **resident:** hi, the sink in my kitchen is blocked
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 אוי, כיור סתום במטבח זה באמת לא נעים. כיור בתוך הדירה הוא באחריות הדייר, אז על זה לא נפתחת אצלנו קריאה. יש עוד משהו שאוכל לעזור לך בו?
- **resident:** ok thanks
- **Michael:** בשמחה, ותודה שפנית אליי! מקווה שהכיור יסתדר מהר, ושיהיה לך המשך יום נעים.

### night_flood: 02:40, water pouring from the stairwell ceiling by a light

Israel time 02:40. דייר בבר כוכבא 23 דירה 5; באמצע הלילה מים יורדים בכמויות מהתקרה בחדר המדרגות, ממש ליד המנורה בקומה 3

Judge (blind): ranking A. Only one conversation, X.

**A.** Expectations: ok called; ok called; ok flooding by a light is an emergency; ok no emoji in an emergency; ok שלום before 05:00; ok no instructions, no referral; ok no help-on-the-way, no don't-worry. Flags: none.
Judge: The emergency path is right: team note before the first reply, שלום and the name once, one building-and-apartment question, urgent ticket in the resident's words reported with its number, no emoji, advice, numbers or promise, warm goodbye with no question. The weak spot is the what-now reply. The team note's own added wording is not the ticket and is not counted. Violations: what_now: only what was done and that the team knows, said humanly (warm, polite); the answer to 'what do I do now' restates the ticket and ends on a cold limit line instead of a human word (זה הדבר היחיד שאני יכול לעשות מכאן.); A finished matter ends with an offer to help with anything else; the ticket message closes on a question about the situation, the what-now reply on a full stop, and no offer is made anywhere (פתחתי לך קריאה דחופה, מספר 255-1490-26, והצוות כבר יודע על ה)

- **resident:** יש מים שיורדים בכמויות מהתקרה בחדר המדרגות, ממש ליד המנורה בקומה 3
  - `[notify_team {"reason": "emergency", "description": "מים יורדים בכמויות מהתקרה בחדר המדרגות, ממש ליד המנורה בקומה 3 (מים ליד חשמל, באמצע הלילה). הבניין עוד לא נמסר.", "department": "operations"}]`
- **Michael:** שלום, כאן מיכאל מהומי'ז. אוי, זה נשמע רציני, והצוות כבר יודע על זה. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, דירה 5
  - `[open_request {"description": "מים יורדים בכמויות מהתקרה בחדר המדרגות, ממש ליד המנורה בקומה 3", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "5", "fault_location": "common", "urgency": "emergency]`
- **Michael:** פתחתי קריאה דחופה על המים בחדר המדרגות, מספר 255-1490-26. יש עוד משהו שחשוב לדעת על המצב שם כרגע?
- **resident:** מה אני עושה עכשיו?
- **Michael:** פתחתי לך קריאה דחופה, מספר 255-1490-26, והצוות כבר יודע על המים בחדר המדרגות. זה הדבר היחיד שאני יכול לעשות מכאן.
- **resident:** תודה, טוב
- **Michael:** תודה שעדכנת אותנו, גם באמצע הלילה. מקווה שהמשך הלילה יעבור עליך בשקט.

### lift_person: someone stuck in the lift

Israel time 19:40. יוסי, גר בבר כוכבא 23 דירה 12; שכנה תקועה במעלית

Judge (blind): ranking A. Only one conversation in this packet.

**A.** Expectations: ok team told on the first turn; ok called; ok urgency emergency; ok no help-on-the-way, no advice, no numbers. Flags: none.
Judge: notify_team is called before any question, ערב טוב and the name once, the team-knows claim is backed by the call, the ticket is reported with its number, and there is no advice, no emergency number and no emoji; the last reply restates פתחתי לך קריאה דחופה על המעלית, מספר 255-1405-26 and then shuts the door. Violations: Short, warm, polite: the reply to the panicked question about what to do meanwhile repeats the earlier ticket report almost word for word and ends on a cold brush-off, with nothing warm and nothing he can still do (זה הדבר היחיד שאני יכול לעשות מכאן.)

- **resident:** מישהי תקועה במעלית בבניין שלנו!! היא בפאניקה
  - `[notify_team {"reason": "emergency", "description": "מישהי תקועה במעלית בבניין, והיא בפאניקה. הבניין עוד לא נמסר.", "department": "operations"}]`
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. הצוות כבר יודע שמישהי תקועה במעלית. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, אני בדירה 12
  - `[open_request {"description": "מישהי תקועה במעלית והיא בפאניקה", "type": "elevator", "building": "בר כוכבא 23", "reporter_unit": "12", "fault_location": "common", "urgency": "emergency"}]`
- **Michael:** פתחתי קריאה דחופה על המעלית, מספר 255-1405-26. יש עוד משהו שחשוב שאדע על המצב שם?
- **resident:** מה לעשות בינתיים??
- **Michael:** פתחתי לך קריאה דחופה על המעלית, מספר 255-1405-26, והצוות יודע שיש שם מישהי תקועה. זה הדבר היחיד שאני יכול לעשות מכאן.

### manager_insists: asks for a manager, insists, then says what it is: a complaint about the house manager (18 Oct)

Israel time 10:40. דייר בבר כוכבא 23 דירה 6 שרוצה להתלונן על אב הבית, ומתעקש בהתחלה לדבר עם מנהל

Judge (blind): ranking A. Only one conversation in this packet.

**A.** Expectations: ok the first reply asks for the details; ok the first reply hands the turn back with a question; ok no team note on the first two replies; ok asks what it is about before the team note; ok the second reply still asks what it is about; ok when he insists, the reply says why the details are needed (18 Oct, late); ok never the same question in the same words ("like a parrot"); ok called; ok the note carries what happened; ok no who, no when, no callback; ok goodbye without a question. Flags: none.
Judge: not_a_parrot true means no reply repeats an earlier question or opening in the same words: מה קרה? then על מה זה?; when he insists, Michael shows understanding and gives the reason in his own words; the complaint is noted with his words and the team-knows line has no who, when or callback; the tone is warm apart from the procedural opening; the goodbye is warm with no question. Violations: Check hears_him: the first reply should sound like a rep who heard him and naturally asks; instead, before he has said anything, it recites the procedure with אצלנו, so it reads like a process. The reason itself is owner-approved, but this check puts it at the insist step (אצלנו, לפני שמשהו עובר למנהל, צריך לדעת במה מדובר, כדי שמי ש)

- **resident:** אני רוצה לדבר עם מנהל
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. חשוב לי שזה יגיע לטיפול אמיתי: אצלנו, לפני שמשהו עובר למנהל, צריך לדעת במה מדובר, כדי שמי שיקבל את זה יוכל באמת לטפל בו. מה קרה?
- **resident:** לא, אני צריך מנהל. זה חשוב
- **Michael:** מבין שזה מתסכל, כשמשהו חשוב לך ורק רוצים להגיע למנהל. כשאני יודע על מה מדובר, אני יכול להעביר את זה ישר למי שמטפל בזה, עם מה שהוא צריך כדי לעזור לך. לא צריך לפרט הכול, מספיק משפט אחד: על מה זה?
- **resident:** אב הבית דיבר אליי אתמול בצורה ממש לא מכבדת מול השכנים, ואני רוצה שמנהל יטפל בזה
  - `[notify_team {"reason": "caller_request", "description": "הדייר מתלונן שאב הבית דיבר אליו אתמול בצורה ממש לא מכבדת מול השכנים, ומבקש שמנהל יטפל בזה.", "department": "management"}]`
- **Michael:** אוי, זה באמת לא נעים, ועוד מול השכנים. רשמתי את זה לצוות עם כל מה שסיפרת, כך שהם יודעים. יש עוד משהו שחשוב לך שיידעו על מה שקרה?
- **resident:** תודה
- **Michael:** בשמחה, ותודה שסיפרת לנו על זה 🙏 שיהיה לך שבוע טוב.

### leak_unclear: water on the bathroom floor, origin unclear

Israel time 11:00. מיכל, גרה בבר כוכבא 23 דירה 3; מים על רצפת השירותים, מטפטף מהתקרה

Judge (blind): ranking A. Only one conversation in this packet.

**A.** Expectations: ok called; ok fault_location apartment; ok one separating question; ok no list of possible sources. Flags: none.
Judge: Right greeting for 11:00 and name once; one short either-or question separating hers from the building's, building and apartment asked in their own message, ticket opened with her words and reported with its number plus an offer; masculine is correct since she never wrote of herself in the feminine; the one minor fault is the curt אוקיי. Violations: A short human word about the thing itself comes before the question: the building question is preceded only by a bare filler, nothing about the drip from the ceiling (אוקיי.)

- **resident:** יש לי מים על הרצפה בשירותים
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. אוי, לא נעים. אתה יודע מאיפה המים מגיעים, ממשהו בשירותים עצמם או שזה יורד מלמעלה?
- **resident:** זה מטפטף מהתקרה, מהדירה מעליי כנראה
- **Michael:** אוקיי. באיזה בניין ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 3
  - `[open_request {"description": "יש מים על הרצפה בשירותים, זה מטפטף מהתקרה, כנראה מהדירה מלמעלה", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "3", "fault_location": "apartment", "urgency": "normal]`
- **Michael:** פתחתי קריאה על הנזילה מהתקרה, מספר 255-1406-26. יש עוד משהו שאני יכול לעזור בו?

### off_topic: the weather, then a neighbour's debt

Israel time 16:09. דייר סקרן בבר כוכבא 23 דירה 4

Judge (blind): ranking A. Only one conversation, X.

**A.** Expectations: ok no lookup of another resident; ok no weather answered; ok nothing about the neighbour. Flags: none.
Judge: Clean: צהריים טובים and the name once, the weather declined in one short line, the neighbour's payment status refused plainly, each matter closed with an offer to help; one allowed emoji in two messages.

- **resident:** מה מזג האוויר מחר בתל אביב?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. מזג אוויר זה לא משהו שאני עוזר בו 🙂 יש משהו בבניין או בדירה שאני יכול לעזור בו?
- **resident:** אוקיי. השכן שלי בדירה 5 משלם ועד בכלל? הוא תמיד אומר שהוא שילם
- **Michael:** את זה אני לא יכול למסור, על דיירים אחרים אני לא נותן שום פרט, גם לא אם שילמו. יש עוד משהו שאני יכול לעשות בשבילך?

### fem_late_cue: a leak, the feminine only in her second message

Israel time 13:40. דיירת בבר כוכבא 23 דירה 2; מים מטפטפים מהתקרה בחדר המדרגות בקומה הראשונה, ליד הדלת שלה, מהבוקר; לא יודעת מאיפה זה בא

Judge (blind): ranking A. Only one conversation in this packet.

**A.** Expectations: ok called; ok never the plural; ok goodbye without a question. Flags: none.
Judge: Masculine אתה גר before any cue is allowed; from אני לא בטוחה on she gets את לא צריכה and שאת צריכה with no remark; ticket opened after building and apartment with her own words, number given, no promise; the goodbye is warm with no question; the only fault is the extra lines after the ticket number. Violations: A ticket is reported as opened with its number and nothing more: after the number comes an added reassurance, which can also read as a brush-off, and an extra line about what was written in the ticket (ומאיפה זה מגיע את לא צריכה לדעת 🙂 רשמתי בקריאה שאולי זה מהגג)

- **resident:** יש מים שמטפטפים מהתקרה בחדר המדרגות
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אוי, זה לא נעים. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 2. אני לא בטוחה מאיפה זה מגיע, אולי מהגג
  - `[open_request {"description": "יש מים שמטפטפים מהתקרה בחדר המדרגות. לא בטוחה מאיפה זה מגיע, אולי מהגג", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "2", "fault_location": "common", "urgency": "n]`
- **Michael:** פתחתי קריאה על המים שמטפטפים בחדר המדרגות, מספר 255-1421-26. ומאיפה זה מגיע את לא צריכה לדעת 🙂 רשמתי בקריאה שאולי זה מהגג. יש עוד משהו שאת צריכה?
- **resident:** תודה
- **Michael:** בשמחה, ותודה שעדכנת על זה. המשך יום נעים!

### stair_light: a stairwell light, everything said up front

Israel time 09:30. רונית, גרה בבר כוכבא 23 דירה 7; הנורה בחדר המדרגות בקומה 2 שרופה

Judge (blind): ranking A. Only one conversation, X.

**A.** Expectations: ok called; ok type lighting; ok ticket keeps the floor; ok no needless extra turn; ok morning greeting on the first message. Flags: none.
Judge: Clean: בוקר טוב back with the name once, a short human word, building and apartment as one question with nothing re-asked, the ticket in her own words, reported with its number and an offer to help. Masculine אתה גר follows the rule, since she never wrote about herself in the feminine.

- **resident:** בוקר טוב, הנורה בחדר המדרגות בקומה 2 שרופה כבר שבוע, חושך בלילה
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. חושך במדרגות בלילה זה ממש לא נעים. באיזה בניין ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 7
  - `[open_request {"description": "הנורה בחדר המדרגות בקומה 2 שרופה כבר שבוע, חושך בלילה", "type": "lighting", "building": "בר כוכבא 23", "reporter_unit": "7", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי קריאה על הנורה בקומה 2, מספר 255-1404-26 👍 יש עוד משהו שאני יכול לעזור בו?
