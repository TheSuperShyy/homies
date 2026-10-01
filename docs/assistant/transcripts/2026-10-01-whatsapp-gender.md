# WhatsApp bot QA, 1 Oct 2026, evening: one person, in the singular

Owner, 1 Oct: *"i notice it still uses how can i help you all which is awkward"*, and *"the bot
should adapt if the person on the other line uses feminine words or adjectives or something to
identify it should know"*. The candidate is `scripts/n8n_whatsapp_gender.py --dump`. Nothing was
spent on OpenRouter, nothing reached a phone, and the live bot did not change. Every resident here
is invented, the only building is בר כוכבא 23, and links and phone numbers are masked.

## What was tested

- **The candidate:** the prompt paragraph (singular; masculine until it is clear a woman is
  writing, then feminine, with no remark; never a slash), and the payment ack, rescue and outage
  note in words that fit both. Also the retry note without its plural clause, the singular "you"
  in the team note, the promise filter (v2) and the opener shape, and memory epoch 70.
- **30 scenarios:** the morning's 26, with the bot's earlier lines in the histories made
  singular, and 4 new ones. In the new ones a woman writes in the feminine from her first line,
  from her second message, while asking for the payment link, and after the representative
  button. One Claude player (Sonnet) per scenario plays the ack, the answering model and the
  resident. Players are blind to the rubric and, from this run on, to the judges' questions.
- **The rubric** flags a plural "you", a masculine "you" after the resident wrote about herself
  in the feminine, and a feminine "you" with no such cue.
- **The rescue and the outage note** are not in the deck, so they were replayed on their own:
  4 rescue inputs (with and without a ticket, with and without a feminine cue) and 3 outage
  samples.

## Results

| | this morning, live prompt | candidate |
|---|---|---|
| conversations / model turns | 26 / 58 | 30 / 68 |
| plural "you" in what the handset gets | 47 | 0 |
| masculine after she wrote in the feminine | 0 | 0 |
| feminine with no cue | 0 | 0 |
| slash forms | 0 | 0 |
| expectations failed | 2 (the pending which-gate checks) | 2 (the same two) |

The other flags are the same kinds as this morning:
- the payment ack's own "הבנתי ש…" (a known gap);
- the deeds guard on lift_person;
- the payment link written on the same line as the text after it, in both payment scenarios;
- the phantom guard rejecting an honest "עוד לא פתחתי קריאה" (the morning's finding 2, now in
  street_unknown, where the rubric's ticket-claim pattern trips on the same sentence).

None of them comes from this change.

**The switch, as it reads.** In burglary the resident's first lines carry no gender, and the bot
uses the default: "מקווה שאתה בסדר". Then she writes "מה אני אמורה לעשות עכשיו?", and the next
reply is "יש משהו אחר שאת צריכה?", with no remark. In fem_pay the ack is "אני בודק לך את זה
עכשיו", which fits both, and the link message ends "אם משהו לא ברור, תכתבי לי כאן". In stair_light
the persona is a woman who never shows it, and she gets "באיזה בניין זה, ובאיזו דירה אתה גר?":
the masculine default, as the owner gave it. The representative button now reads "כאן מיכאל
מהומי'ז. במה אוכל לעזור לך?". Before, it was "…במה אוכל לעזור לכם?", the line the owner saw at
11:43 UTC (execution 74380, which `--watch` now flags).

**What the run cannot say.** The model here is Claude, not Gemini 2.5 Flash. A clean run says
the new paragraph asks for the right thing; Gemini's own compliance shows only on the handset and
in `--watch`, which now flags a plural "you" and a masculine "you" after a feminine cue.

## The two writers with no history (new system texts)

- **rescue, a ticket was opened, she wrote 'אני גרה':** פתחתי לך קריאה על התאורה בחדר המדרגות, והמספר שלה הוא 255-1430-26. יש עוד משהו שאפשר לעזור לך בו?
- **rescue, a ticket was opened, a man:** פתחתי קריאה על המעלית התקועה, מספר 255-1431-26. אם יש עוד משהו שאפשר לעזור בו, אני כאן.
- **rescue, no ticket, a status question:** כרגע אין לי עדכון על מצב הקריאה שלך. אפשר לעזור לך במשהו נוסף?
- **rescue, no ticket, she wrote 'אני צריכה':** מצטער, אין לי כרגע מידע על מועדי הניקיון של חדר המדרגות. אשמח לעזור לך בכל דבר אחר.
- **outage note, sample 1:** יש אצלנו כרגע תקלה טכנית, אבל ההודעה שלך הגיעה אלינו והצוות שלנו יודע עליה.
- **outage note, sample 2:** אנחנו חווים כרגע תקלה טכנית, ואני מצטער על אי הנוחות. ההודעה שלך הגיעה אלינו והצוות שלנו מודע לזה.
- **outage note, sample 3:** כרגע יש לנו תקלה טכנית. ההודעה שלך התקבלה אצלנו, והצוות שלנו כבר יודע על כך.

All seven are singular, in words that fit both, and none promises who or when.

## Totals

| variant | conversations | model turns | guard rejections | rubric flags | expectations met | failed | judge wins |
|---|---|---|---|---|---|---|---|
| A | 30 | 68 | 2 | 6 | 118 | 2 | 0 |

## Rubric flags by rule

| rule | A |
|---|---|
| echo-in-ack(known) | 1 |
| guard:deeds | 1 |
| guard:phantom | 1 |
| link-not-on-own-line | 2 |
| ticket-claim-without-tool | 1 |

## Scenarios

### gate_lock: the gate lock, Hebrew, first contact

Israel time 16:09. דני, גר בבר כוכבא 23 דירה 4; הבניין יש לו שני שערים, הכניסה והחניה; הבעיה בשער החניה מאחור

**A.** Expectations: ok called; ok ticket holds no guessed gate; ok ticket keeps the resident's word; FAIL asks which gate or where before opening; ok no promise after the ticket; ok no guessed gate in the replies; ok goodbye without a question. Flags: none.

- **resident:** היי, המנעול של השער שבור שוב
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אוי, מעצבן שזה קורה שוב. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, דירה 4
  - `[open_request {"description": "המנעול של השער שבור שוב", "type": "locksmith", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על המנעול של השער, מספר 255-1402-26. יש עוד משהו שאפשר לעזור בו?
- **resident:** תודה
- **Michael:** בשמחה 🙂 תודה שפנית, המשך יום נעים.

### gate_english: the owner's own 30 Sep lines, in English

Israel time 16:09. the owner testing in English; lives at Bar Kochba 23 apartment 4; the gate he means is the parking gate at the back

**A.** Expectations: ok called; ok ticket holds no guessed gate; ok how-are-you reply: at most two questions; ok answers in Hebrew; ok no slang, no sad face; ok no guessed gate in the replies; FAIL asks which gate before opening. Flags: none.

- **resident:** hey how is it going
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. הכל טוב, תודה ששאלת 🙂 ואיך עובר עליך היום?
- **resident:** im fine too thanks anyways the gate lock is broken again
- **Michael:** איזה מעצבן שזה שוב קורה. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** Bar Kochba 23, apartment 4
  - `[open_request {"description": "המנעול של השער שבור שוב", "type": "locksmith", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על המנעול של השער, מספר 255-1403-26. יש עוד משהו שאפשר לעזור בו?

### stair_light: a stairwell light, everything said up front

Israel time 09:30. רונית, גרה בבר כוכבא 23 דירה 7; הנורה בחדר המדרגות בקומה 2 שרופה

**A.** Expectations: ok called; ok type lighting; ok ticket keeps the floor; ok no needless extra turn; ok morning greeting on the first message. Flags: none.

- **resident:** בוקר טוב, הנורה בחדר המדרגות בקומה 2 שרופה כבר שבוע, חושך בלילה
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. איזה מעצבן. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 7
  - `[open_request {"description": "הנורה בחדר המדרגות בקומה 2 שרופה כבר שבוע, חושך בלילה", "type": "lighting", "building": "בר כוכבא 23", "reporter_unit": "7", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** תודה 🙂 פתחתי קריאה על הנורה בחדר המדרגות בקומה 2, והמספר שלה 255-1404-26. יש עוד משהו שאפשר לעזור בו?

### lift_person: someone stuck in the lift

Israel time 19:40. יוסי, גר בבר כוכבא 23 דירה 12; שכנה תקועה במעלית

**A.** Expectations: ok team told on the first turn; ok called; ok urgency emergency; ok no help-on-the-way, no advice, no numbers. Flags: guard:deeds.

- **resident:** מישהי תקועה במעלית בבניין שלנו!! היא בפאניקה
  - `[notify_team {"reason": "emergency", "description": "מישהי תקועה במעלית בבניין של הדייר, היא בפאניקה. הבניין עוד לא ידוע.", "department": "operations"}]`
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. הצוות כבר יודע שיש מישהי תקועה במעלית. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, אני בדירה 12
  - `[open_request {"description": "מישהי תקועה במעלית, היא בפאניקה", "type": "elevator", "building": "בר כוכבא 23", "reporter_unit": "12", "fault_location": "common", "urgency": "emergency"}]`
- **Michael:** פתחתי קריאה על המעלית בבר כוכבא 23, מספר 255-1405-26. אפשר לעזור בעוד משהו?
- **resident:** מה לעשות בינתיים??
- **Michael:** אני לא יכול להגיד לך מה לעשות. פתחתי קריאה, מספר 255-1405-26, והצוות יודע.
  - flags: guard:deeds: אני לא יכול להגיד לך מה לעשות. פתחתי קריאה, מספר 255-1405-26, והצוות יודע.

### sink_private: a blocked kitchen sink, in English

Israel time 16:09. a resident writing in English, Bar Kochba 23 apartment 4

**A.** Expectations: ok no ticket for a private fault; ok no tradesman recommended; ok does not explain the rule; ok goodbye without a question. Flags: none.

- **resident:** hi, the sink in my kitchen is blocked
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 אוי, כיור סתום זה באמת לא נעים. הכיור בתוך הדירה שלך, אז זה באחריותך ולא משהו שאנחנו מטפלים בו. אפשר לעזור לך בעוד משהו?
- **resident:** ok thanks
- **Michael:** בשמחה, תודה שפנית אליי. שיהיה לך המשך יום נעים.

### leak_unclear: water on the bathroom floor, origin unclear

Israel time 11:00. מיכל, גרה בבר כוכבא 23 דירה 3; מים על רצפת השירותים, מטפטף מהתקרה

**A.** Expectations: ok called; ok fault_location apartment; ok one separating question; ok no list of possible sources. Flags: none.

- **resident:** יש לי מים על הרצפה בשירותים
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. אוי, לא נעים בכלל. זה רק אצלך בדירה או גם אצל השכנים?
- **resident:** זה מטפטף מהתקרה, מהדירה מעליי כנראה
- **Michael:** אוף, זה לא כיף. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 3
  - `[open_request {"description": "מים על הרצפה בשירותים, מטפטף מהתקרה, כנראה מהדירה שמעל", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "3", "fault_location": "apartment", "urgency": "high"}]`
- **Michael:** פתחתי לך קריאה על הנזילה מהתקרה, מספר 255-1406-26. יש עוד משהו שאפשר לעזור בו?

### balance: how much do I owe

Israel time 14:00. דני לוי, בר כוכבא 23 דירה 4, טלפון <phone>

**A.** Expectations: ok called; ok no unasked link; ok never asks which apartment; ok states the amount; ok name and phone in one question. Flags: none.

- **resident:** כמה אני חייב לוועד?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 תוכל לכתוב לי את השם המלא ומספר הטלפון שלך?
- **resident:** דני לוי, <phone>
  - `[get_balance {"name": "דני לוי", "phone": "<phone>"}]`
- **Michael:** החוב שלך לוועד עומד על 1,240 ש"ח, על יולי, אוגוסט וספטמבר. יש עוד משהו שאפשר לעזור בו?

### pay_link: I want to pay

Israel time 14:00. דייר בבר כוכבא 23 דירה 4 שרוצה לשלם

**A.** Expectations: ok link fetched at once; ok the link as returned; ok nothing asked before the link; ok link marked personal; ok goodbye without a question. Flags: link-not-on-own-line.

- **resident:** אני רוצה לשלם את הוועד
  - `[get_payment_link {"said": "אני רוצה לשלם את הוועד"}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. קיבלתי את הבקשה שלך לשלם את הוועד ואני בודק את זה עכשיו.
- **Michael:** הנה הקישור לתשלום הוועד של דירה 4 בבר כוכבא 23: / <link> הקישור אישי ומיועד לדירה הזאת בלבד, אז בבקשה לא להעביר אותו הלאה. אם משהו לא ברור, אפשר לכתוב לי כאן.
  - flags: link-not-on-own-line: הנה הקישור לתשלום הוועד של דירה 4 בבר כוכבא 23: <link> הקישור אישי ומיועד לדירה הזאת בלבד, אז בבקשה לא להעביר 
- **resident:** קיבלתי, תודה
- **Michael:** בשמחה, תודה שפנית. המשך יום נעים 🙂

### pay_link_missing: how do I pay, and the link is not found

Israel time 14:00. דייר בבר כוכבא 23 דירה 4 שהמספר שלו לא מזוהה במערכת

**A.** Expectations: ok link tried first; ok called; ok payment ticket; ok called; ok the reason is not explained, no identity asked; ok no promise. Flags: echo-in-ack(known).

- **resident:** איך משלמים?
  - `[get_payment_link {"said": "איך משלמים?"}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. הבנתי שזה בקשר לתשלום, ואני בודק את זה עכשיו אצלנו במערכת.
- **Michael:** לא הצלחתי להוציא לך קישור לתשלום. באיזה בניין ובאיזו דירה אתה גר?
  - flags: echo-in-ack(known):  טובים, כאן מיכאל מהומי'ז. הבנתי שזה בקשר לתשלום, ואני בודק
- **resident:** בר כוכבא 23 דירה 4
  - `[open_request {"description": "הדייר שאל איך משלמים. קישור התשלום לא נמצא.", "type": "payment", "building": "בר כוכבא 23", "reporter_unit": "4", "urgency": "normal"}]`
  - `[notify_team {"reason": "payment", "description": "הדייר שאל איך משלמים ולא נמצא לו קישור תשלום. נפתחה קריאה 255-1407-26, בר כוכבא 23 דירה 4.", "department": "collections"}]`
- **Michael:** תודה 🙏 פתחתי קריאה על התשלום, מספר 255-1407-26, והצוות יודע. יש עוד משהו שאפשר לעזור לך בו?

### status_ref: status of a ticket by its number

Israel time 10:15. דייר שפתח קריאה אתמול על מנעול השער

**A.** Expectations: ok called; ok no new ticket; ok no technician timing invented; ok status in words. Flags: none.

- **resident:** מה קורה עם הקריאה 255-1339-26?
  - `[get_request_status {"reference": "255-1339-26"}]`
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. הקריאה 255-1339-26 על מנעול השער נמצאת בטיפול. אפשר לעזור בעוד משהו?

### status_tap: the status button, no reference

Israel time 10:15. דיירת בבר כוכבא 23 שלא זוכרת מספר קריאה

**A.** Expectations: ok called; ok no new ticket; ok no greeting after the menu; ok one question on the tap. Flags: none.

- **resident:** היי
- **system:** בוקר טוב 👋 במה אפשר לעזור? (buttons)
- **tap:** מצב קריאה קיימת
- **Michael:** כאן מיכאל מהומי'ז. יש לך את מספר הקריאה, או שנתחיל מהבניין?
- **resident:** אין לי מספר, זה בבר כוכבא 23
  - `[get_request_status {"building": "בר כוכבא 23"}]`
- **Michael:** אין בעיה. לא מצאתי כרגע קריאה על בר כוכבא 23. אפשר לעזור בעוד משהו?

### tap_open: the open-a-ticket button

Israel time 16:09. דייר בבר כוכבא 23 דירה 4; דלת הכניסה לבניין לא נסגרת

**A.** Expectations: ok called; ok one question on the tap; ok no greeting after the menu; ok does not ask whether to open. Flags: none.

- **resident:** שלום
- **system:** צהריים טובים 👋 במה אפשר לעזור? (buttons)
- **tap:** פתיחת קריאת שירות
- **Michael:** כאן מיכאל מהומי'ז. טוב שפנית, אני איתך 🙂 ספר לי, מה קרה?
- **resident:** הדלת של הכניסה לבניין לא נסגרת, נשארת פתוחה
- **Michael:** אוי, זה לא נעים. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, דירה 4
  - `[open_request {"description": "הדלת של הכניסה לבניין לא נסגרת, נשארת פתוחה", "type": "locksmith", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על דלת הכניסה לבניין, מספר 255-1408-26. אפשר לעזור בעוד משהו?

### tap_rep: the talk-to-a-representative button, then a disputed charge

Israel time 16:09. דייר בבר כוכבא 23 דירה 4 עם חיוב שלא מבין

**A.** Expectations: ok called; ok a dispute is a note, not a ticket; ok no transfer, no call-back promise; ok the rep tap does not assume a fault; ok goodbye without a question. Flags: none.

- **resident:** היי
- **system:** צהריים טובים 👋 במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** כאן מיכאל מהומי'ז. במה אוכל לעזור לך?
- **resident:** יש לי חיוב בחשבון שאני לא מבין, 380 שקל על משהו שלא ביקשתי
  - `[notify_team {"reason": "billing", "description": "יש לי חיוב בחשבון שאני לא מבין, 380 שקל על משהו שלא ביקשתי", "department": "collections"}]`
- **Michael:** לא נעים לראות חיוב שלא מכירים. רשמתי את זה לצוות, והם יודעים על החיוב. אפשר לעזור בעוד משהו?
- **resident:** תודה
- **Michael:** בשמחה, תודה שפנית. שיהיה לך המשך יום נעים 🙂

### service_cleaning: how often is the stairwell cleaned

Israel time 12:30. דיירת שרוצה לדעת על הניקיון

**A.** Expectations: ok called; ok no frequency invented; ok says it is per the building's agreement. Flags: none.

- **resident:** כל כמה זמן מנקים את חדר המדרגות?
  - `[get_service_info {"topic": "כל כמה זמן מנקים את חדר המדרגות"}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. התדירות של ניקיון חדר המדרגות נקבעת בהסכם של כל בניין, ואין לי כרגע את מה שנקבע בבניין שלך. אפשר לעזור בעוד משהו?

### price_quote: how much to paint the stairwell

Israel time 12:30. דייר בבר כוכבא 23 דירה 4 שרוצה הצעת מחיר לצביעת חדר המדרגות

**A.** Expectations: ok called; ok no price guessed; ok no call-back promise. Flags: none.

- **resident:** כמה עולה לצבוע את חדר המדרגות אצלנו?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 באיזה בניין מדובר?
- **resident:** בר כוכבא 23
  - `[notify_team {"reason": "quote", "description": "מבקש הצעת מחיר לצביעת חדר המדרגות בבר כוכבא 23. שאל: כמה עולה לצבוע את חדר המדרגות אצלנו?", "department": "management"}]`
- **Michael:** תודה. מחיר אין לי, אבל הצוות יודע שאתה מבקש הצעת מחיר לצביעת חדר המדרגות בבר כוכבא 23. יש עוד משהו שאפשר לעזור בו?

### no_ticket: just so you know, no ticket needed

Israel time 16:09. דייר בבר כוכבא 23 שלא רוצה קריאה

**A.** Expectations: ok no ticket when refused; ok no persuasion. Flags: none.

- **resident:** המנורה בלובי מהבהבת קצת, לא צריך לפתוח קריאה, סתם שתדעו
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אין בעיה 🙂 אפשר לעזור בעוד משהו?
- **resident:** לא, זה הכל
- **Michael:** תודה שפנית, שיהיה לך המשך יום נעים.

### off_topic: the weather, then a neighbour's debt

Israel time 16:09. דייר סקרן בבר כוכבא 23 דירה 4

**A.** Expectations: ok no lookup of another resident; ok no weather answered; ok nothing about the neighbour. Flags: none.

- **resident:** מה מזג האוויר מחר בתל אביב?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. מזג אוויר זה לא משהו שאני עוזר בו 🙂 יש משהו בבניין או בדירה שאפשר לעזור בו?
- **resident:** אוקיי. השכן שלי בדירה 5 משלם ועד בכלל? הוא תמיד אומר שהוא שילם
- **Michael:** את זה אני לא יכול לספר, פרטים על דיירים אחרים אני לא מוסר, גם לא אם שילמו. תרצה שאבדוק את היתרה של הדירה שלך?

### burglary: a break-in last night

Israel time 23:30. דיירת בבר כוכבא 23 דירה 4 שפרצו לה לדירה

**A.** Expectations: ok no ticket for a private break-in; ok no referral, no advice; ok evening greeting at 23:30. Flags: none.

- **resident:** פרצו לי לדירה הלילה, אני בהלם
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. אוי, כמה קשה, מקווה שאתה בסדר. פריצה לדירה היא לא משהו שהומי'ז מטפלת בו, אבל אם נפגעה גם דלת הכניסה לבניין או המנעול שלה, אפתח על זה קריאה. יש נזק כזה?
- **resident:** לא, רק הדלת שלי
- **Michael:** טוב שהבניין עצמו נשאר שלם. הדלת של הדירה היא שלך, אז אין לי קריאה לפתוח עליה. יש עוד משהו שאפשר לעזור בו?
- **resident:** מה אני אמורה לעשות עכשיו?
- **Michael:** זה בטח מערער לגמרי. מה לעשות עכשיו אני לא יכול להגיד לך, אבל אני כאן. יש משהו אחר שאת צריכה?

### lost: I don't know what I need

Israel time 16:09. דייר מבולבל בבר כוכבא 23

**A.** Expectations: ok called; ok no list in words. Flags: none.

- **resident:** אני לא יודע מה אני צריך בעצם, מה אתם עושים?
  - `[show_menu {}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אין בעיה 🙂 אנחנו חברת ניהול של בתים משותפים. מה מהרשימה הכי קרוב למה שאתה צריך?

### unclear: 'it again' with no content, then the roof fan

Israel time 16:09. דייר בבר כוכבא 23 דירה 4; המפוח על הגג רועש בלילה

**A.** Expectations: ok called; ok one short question on the empty message; ok no guessed matter on 'it again'. Flags: none.

- **resident:** זה שוב
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. ספר לי, מה קורה שוב?
- **resident:** הרעש מהמפוח על הגג, כל לילה אי אפשר לישון
- **Michael:** אוי, זה מתיש. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 4
  - `[open_request {"description": "הרעש מהמפוח על הגג, כל לילה אי אפשר לישון", "type": "maintenance", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על הרעש מהמפוח שעל הגג, מספר 255-1409-26. אפשר לעזור בעוד משהו?

### street_unknown: a lobby leak in a building Homies does not manage

Israel time 16:09. דייר ברחוב הדמיון 7 דירה 2 (רחוב שהומיז לא מנהלת)

**A.** Expectations: ok called; ok no ticket number claimed; ok no invented list of buildings. Flags: guard:phantom, ticket-claim-without-tool.

- **resident:** יש נזילה בלובי אצלנו
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אוי, לא נעים בכלל. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** הדמיון 7 דירה 2
  - `[open_request {"description": "יש נזילה בלובי אצלנו", "type": "plumbing", "building": "הדמיון 7", "reporter_unit": "2", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** לא מצאתי את רחוב הדמיון בין הבניינים שאנחנו מנהלים, ולכן עוד לא פתחתי קריאה. תוכל לבדוק שוב איך שם הרחוב כתוב?
  - flags: guard:phantom: לא מצאתי את רחוב הדמיון בין הבניינים שאנחנו מנהלים, ולכן עוד לא פתחתי קריאה. תוכל לבדוק שוב איך שם הרחוב כתוב?; ticket-claim-without-tool: נחנו מנהלים, ולכן עוד לא פתחתי קריאה. תוכל לבדוק שוב אי
- **resident:** רחוב הדמיון 7, זה מה שכתוב
  - `[open_request {"description": "יש נזילה בלובי אצלנו", "type": "plumbing", "building": "רחוב הדמיון 7", "reporter_unit": "2", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** בדקתי שוב עם הכתובת בדיוק כמו שכתבת, ורחוב הדמיון עדיין לא מופיע אצלנו, אז אני לא יכול לפתוח קריאה על הנזילה. אני מצטער. יש משהו אחר שאפשר לעזור בו?

### photo_nocaption: a photo with no words

Israel time 16:09. דייר בבר כוכבא 23 דירה 4; צינור בחניון מטפטף

**A.** Expectations: ok called; ok does not pretend to see the photo; ok one question on the photo. Flags: none.

- **photo:** 
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. קיבלתי את התמונה, תוכל לספר לי במילים מה קרה ואיפה?
- **resident:** זה הצינור בחניון שמטפטף, ליד החניה 12
- **Michael:** אוי, לא נעים. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 4
  - `[open_request {"description": "הצינור בחניון מטפטף, ליד החניה 12", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על הצינור שמטפטף בחניון, מספר 255-1411-26, והתמונה מצורפת אליה 🙂 יש עוד משהו שאפשר לעזור בו?

### goodbye_mid: thanks and goodnight after a ticket earlier today

Israel time 21:10. דייר בבר כוכבא 23 דירה 4 שכבר פתח קריאה לפני רבע שעה

**A.** Expectations: ok nothing opened on a goodbye; ok goodbye without a question; ok no name mid-conversation. Flags: none.

- **resident:** תודה רבה, לילה טוב
- **Michael:** בשמחה, ותודה שפנית אלינו. לילה טוב ושינה נעימה 😊

### hello_then_matter: a bare hello, then cockroaches in the bin room

Israel time 16:09. דיירת בבר כוכבא 23 דירה 4; ג'וקים בחדר האשפה

**A.** Expectations: ok called; ok type pest_control; ok no greeting after the menu; ok the name after the menu; ok no second 'how can I help'. Flags: none.

- **resident:** שלום
- **system:** צהריים טובים 👋 במה אפשר לעזור? (buttons)
- **resident:** יש ג'וקים בחדר האשפה, מלא
- **Michael:** כאן מיכאל מהומי'ז. אוי, לא נעים בכלל. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, 4
  - `[open_request {"description": "יש ג'וקים בחדר האשפה, מלא", "type": "pest_control", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על הג'וקים בחדר האשפה, מספר 255-1413-26. יש עוד משהו שאפשר לעזור בו? 🙂

### how_are_you_he: hi, how are you, then a balance question

Israel time 16:09. דני לוי, בר כוכבא 23 דירה 4, טלפון <phone>

**A.** Expectations: ok called; ok asks back; ok at most two questions on the how-are-you. Flags: none.

- **resident:** היי, מה נשמע?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 אצלי הכל טוב, תודה ששאלת. ואיך עובר עליך היום?
- **resident:** הכל טוב תודה. רציתי לשאול מה היתרה שלי
- **Michael:** טוב לשמוע. אפשר לקבל את השם המלא שלך ואת מספר הטלפון?
- **resident:** דני לוי <phone>
  - `[get_balance {"name": "דני לוי", "phone": "<phone>"}]`
- **Michael:** היתרה שלך לתשלום היא 620 ₪, על חודש ספטמבר. אפשר לעזור בעוד משהו?

### second_matter: mid-conversation hello and a second fault, building known

Israel time 16:30. דייר בבר כוכבא 23 דירה 4 שכבר מסר את הבניין והדירה לפני רבע שעה

**A.** Expectations: ok called; ok no name mid-conversation; ok building not asked again. Flags: none.

- **resident:** היי, עוד משהו: גם האינטרקום לא עובד
  - `[open_request {"description": "האינטרקום לא עובד", "type": "electrical", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** היי 🙂 איזה מעצבן. פתחתי לך קריאה גם על האינטרקום, מספר 255-1415-26. יש עוד משהו שאפשר לעזור בו?

### fem_light_first: a woman reports a stairwell light, the feminine in her first line

Israel time 10:15. מיכל, גרה בבר כוכבא 23 דירה 6; האור בחדר המדרגות בקומה 3 לא נדלק כבר יומיים

**A.** Expectations: ok called; ok never the masculine to her; ok never the plural; ok goodbye without a question. Flags: none.

- **resident:** היי, אני גרה בבר כוכבא 23 דירה 6, והאור בחדר המדרגות בקומה 3 לא נדלק כבר יומיים
  - `[open_request {"description": "האור בחדר המדרגות בקומה 3 לא נדלק כבר יומיים", "type": "lighting", "building": "בר כוכבא 23", "reporter_unit": "6", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. איזה מעצבן. פתחתי לך קריאה על האור בחדר המדרגות בקומה 3, מספר 255-1420-26. אפשר לעזור בעוד משהו?
- **resident:** תודה רבה!
- **Michael:** בשמחה, תודה שפנית 🙂 שיהיה לך המשך יום נעים.

### fem_late_cue: a leak, the feminine only in her second message

Israel time 13:40. דיירת בבר כוכבא 23 דירה 2; מים מטפטפים מהתקרה בחדר המדרגות בקומה הראשונה, ליד הדלת שלה, מהבוקר; לא יודעת מאיפה זה בא

**A.** Expectations: ok called; ok never the plural; ok goodbye without a question. Flags: none.

- **resident:** יש מים שמטפטפים מהתקרה בחדר המדרגות
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אוי, לא נעים בכלל. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 2. אני לא בטוחה מאיפה זה מגיע, אולי מהגג
  - `[open_request {"description": "יש מים שמטפטפים מהתקרה בחדר המדרגות. לא בטוחה מאיפה זה מגיע, אולי מהגג", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "2", "fault_location": "common", "urgency": "h]`
- **Michael:** פתחתי לך קריאה על המים שמטפטפים בחדר המדרגות, מספר 255-1421-26. אפשר לעזור לך בעוד משהו?
- **resident:** תודה
- **Michael:** בשמחה, תודה שפנית אלינו. שיהיה לך המשך יום נעים 🙂

### fem_pay: a woman asks for the payment link

Israel time 19:05. דיירת בבר כוכבא 23 דירה 4 שרוצה לשלם את הוועד

**A.** Expectations: ok link fetched at once; ok the link as returned; ok never the masculine to her; ok never the plural; ok goodbye without a question. Flags: link-not-on-own-line.

- **resident:** היי, אני צריכה את הקישור לתשלום הוועד
  - `[get_payment_link {"said": "אני צריכה את הקישור לתשלום הוועד"}]`
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. קיבלתי את הבקשה לקישור התשלום ואני בודק לך את זה עכשיו.
- **Michael:** הנה הקישור לתשלום ועד הבית של דירה 4 בבר כוכבא 23: <link> הקישור אישי ומיועד לדירה שלך בלבד, אז בבקשה לא להעביר אותו הלאה. אם משהו לא ברור, תכתבי לי כאן.
  - flags: link-not-on-own-line: הנה הקישור לתשלום ועד הבית של דירה 4 בבר כוכבא 23: <link> הקישור אישי ומיועד לדירה שלך בלבד, אז בבקשה לא להעבי
- **resident:** מעולה, תודה
- **Michael:** בשמחה, תודה שפנית אלינו. שיהיה לך המשך ערב נעים 🙂

### fem_rep_tap: the representative button, then a woman disputes a charge

Israel time 15:30. דיירת בבר כוכבא 23 דירה 4 שחויבה פעמיים על ספטמבר

**A.** Expectations: ok called; ok a dispute is a note, not a ticket; ok no call-back promise; ok never the plural; ok goodbye without a question. Flags: none.

- **resident:** היי
- **system:** צהריים טובים 👋 במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** כאן מיכאל מהומי'ז 🙂 במה אפשר לעזור לך?
- **resident:** אני חושבת שחייבו אותי פעמיים על ספטמבר, אני רוצה לברר את זה
  - `[notify_team {"reason": "billing", "description": "הדיירת חושבת שחייבו אותה פעמיים על ספטמבר ורוצה לברר את זה", "department": "collections"}]`
- **Michael:** אוקיי, עדכנתי את הצוות על החיוב הכפול של ספטמבר. אפשר לעזור לך בעוד משהו?
- **resident:** תודה
- **Michael:** בשמחה 😊 תודה שפנית אלינו, ושיהיה לך המשך יום נעים.
