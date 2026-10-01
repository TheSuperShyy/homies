# WhatsApp bot QA, 1 Oct 2026, evening: the representative says hi

The owner tapped "לדבר עם נציג" right after the menu (13:14 UTC, execution 74529) and got
"כאן מיכאל מהומי'ז! 😊 במה אוכל לעזור לך?". The model had written "היי, " and Send's greeting
filter cut it. His ask: *"can we make it like for example talk to a rep liek the agent should be
like hi how are you this is michael from homies..."*. The candidate is
`scripts/n8n_whatsapp_rephello.py --dump`. Nothing was spent on OpenRouter, nothing reached a
phone, and the live bot did not change. Every resident here is invented, the only building is
בר כוכבא 23, and links and phone numbers are masked.

## What was tested

- **The candidate:** the prompt's tap paragraph (that tap opens with "היי", never the hour's
  greeting the menu gave, then how he is, the name and how to help, in one short message; the two
  general clauses name it as their one exception), Send's greeting filter v3 (one hello and the
  name stay on that tap), and memory epoch 71.
- **33 scenarios:** the 30 of the afternoon, with the two representative-button ones now
  checking the new opening, and 3 new ones: a plain "fine, thanks" and then a cleaning question; an
  evening tap where the resident asks back "and you?"; a morning tap where the answer to how-are-you
  carries the matter. One Claude player (Sonnet) per scenario plays the ack, the answering model
  and the resident, blind to the rubric and the judges' questions.
- **The rubric** now knows the tap: it flags a tap reply without a hello (`rep-no-hello`) or
  without a how-are-you (`rep-no-how-are-you`), a tap hello that repeats the menu's hour word
  (`rep-hello-repeats-menu`), and a how-are-you asked again later (`how-are-you-again`). The tap's
  how-are-you does not count as a second question. Every other greeting rule is as before, so a
  greeting after the other two buttons, or after anything typed after the menu, is still flagged.

## Results

| | this afternoon, live prompt (30 scenarios) | candidate (33 scenarios) |
|---|---|---|
| model turns | 68 | 81 |
| representative tap: "היי", a how-are-you, the name, no hour greeting | (the old rule: no greeting) | 5 of 5 taps, every check met |
| a greeting after the other two buttons, or after text typed after the menu | 0 | 0 |
| how-are-you asked again after the resident answered | n/a | 0 |
| other greeting flags (mid-conversation, two in a message, the wrong hour) | 0 | 0 |
| plural "you" / masculine after a feminine cue / slash forms | 0 / 0 / 0 | 0 / 0 / 0 |
| expectations failed | 2 (the pending which-gate checks) | 2 (the same two) |

The other flags are this morning's known kinds, none from this change:
- the payment ack's own "הבנתי ש…" (a known gap);
- the payment link written on the same line as the text after it, in both payment scenarios;
- the phantom guard rejecting an honest "אני לא פותח עליה קריאה", in burglary (the morning's
  finding 2, then in street_unknown).

Replies that end without a question (an info line, not a flag): 13 of 81 turns (17%), against 14%
on this morning's live prompt and 7% this afternoon. Most are goodbyes, an offer written as a
statement, or a question followed by an emoji or a short imperative. It is player variance; the
change touches no sentence about how a reply ends.

**The tap, as it reads.** Five taps, five openings, then what follows:
- tap_rep, 16:09: "היי 🙂 כאן מיכאל מהומי'ז. מה שלומך, ומה אפשר לעשות בשבילך?"
- fem_rep_tap, 15:30: "היי 🙂 מה שלומך? כאן מיכאל מהומי'ז, איך אפשר לעזור לך?"
- rep_fine_thanks, 16:20: "היי 🙂 מה שלומך? כאן מיכאל מהומי'ז, במה אפשר לעזור לך?". After
  "טוב תודה": "שמח לשמוע! אז מה אפשר לעשות בשבילך?"
- rep_and_you, 20:15, after the menu's "ערב טוב 👋": "היי 🙂 מה שלומך? כאן מיכאל מהומי'ז, במה אפשר
  לעזור?". After "בסדר גמור, ואתה?": "אני מצוין, תודה ששאלת. אז מה אפשר לעשות בשבילך?"
- rep_morning_matter, 09:05, after the menu's "בוקר טוב 👋": "היי 🙂 מה שלומך? כאן מיכאל מהומי'ז,
  במה אפשר לעזור לך?". After "הכל טוב, תודה. יש נזילה בחניון…": "שמח לשמוע. נזילה זה לא נעים.
  באיזה בניין זה, ובאיזו דירה אתה גר?"

**The rest of the menu, unchanged.** The open-a-ticket button: "כאן מיכאל מהומי'ז, אתה במקום הנכון
ואני איתך 🙂 ספר לי מה קרה?". The status button: "כאן מיכאל מהומי'ז, אני איתך על זה 🙂 יש לך את
מספר הקריאה, או שפשוט תגיד לי באיזה בניין זה?". Text typed after the menu: "כאן מיכאל מהומי'ז.
אוי, זה ממש לא נעים. באיזה בניין ובאיזו דירה אתה גר?". No greeting in any of them.

**What the run cannot say.** The model here is Claude, not Gemini 2.5 Flash. Claude wrote the
opening almost word for word each time; Gemini will vary it. Gemini's own compliance shows only on
the handset and in `--watch`, which now flags a tap answered without the name and adds an info line
for a tap with no hello or with the hour's word.

## Totals

| variant | conversations | model turns | guard rejections | rubric flags | expectations met | failed | judge wins |
|---|---|---|---|---|---|---|---|
| A | 33 | 81 | 1 | 4 | 153 | 2 | 0 |

## Rubric flags by rule

| rule | A |
|---|---|
| echo-in-ack(known) | 1 |
| guard:phantom | 1 |
| link-not-on-own-line | 2 |

## Scenarios

### gate_lock: the gate lock, Hebrew, first contact

Israel time 16:09. דני, גר בבר כוכבא 23 דירה 4; הבניין יש לו שני שערים, הכניסה והחניה; הבעיה בשער החניה מאחור

**A.** Expectations: ok called; ok ticket holds no guessed gate; ok ticket keeps the resident's word; FAIL asks which gate or where before opening; ok no promise after the ticket; ok no guessed gate in the replies; ok goodbye without a question. Flags: none.

- **resident:** היי, המנעול של השער שבור שוב
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. איזה מעצבן שזה שוב קורה. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, דירה 4
  - `[open_request {"description": "המנעול של השער שבור שוב", "type": "locksmith", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על המנעול של השער, מספר 255-1402-26. אפשר לעזור בעוד משהו?
- **resident:** תודה
- **Michael:** בשמחה, תודה שפנית. המשך יום נעים 🙂

### gate_english: the owner's own 30 Sep lines, in English

Israel time 16:09. the owner testing in English; lives at Bar Kochba 23 apartment 4; the gate he means is the parking gate at the back

**A.** Expectations: ok called; ok ticket holds no guessed gate; ok how-are-you reply: at most two questions; ok answers in Hebrew; ok no slang, no sad face; ok no guessed gate in the replies; FAIL asks which gate before opening. Flags: none.

- **resident:** hey how is it going
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אצלי הכל טוב, תודה ששאלת 🙂 ואיך עובר עליך היום?
- **resident:** im fine too thanks anyways the gate lock is broken again
- **Michael:** איזה מעצבן, שוב. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** Bar Kochba 23, apartment 4
  - `[open_request {"description": "המנעול של השער שבור שוב", "type": "locksmith", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על המנעול של השער, מספר 255-1403-26. אפשר לעזור בעוד משהו?

### stair_light: a stairwell light, everything said up front

Israel time 09:30. רונית, גרה בבר כוכבא 23 דירה 7; הנורה בחדר המדרגות בקומה 2 שרופה

**A.** Expectations: ok called; ok type lighting; ok ticket keeps the floor; ok no needless extra turn; ok morning greeting on the first message. Flags: none.

- **resident:** בוקר טוב, הנורה בחדר המדרגות בקומה 2 שרופה כבר שבוע, חושך בלילה
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. איזה מעצבן. באיזה בניין ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 7
  - `[open_request {"description": "הנורה בחדר המדרגות בקומה 2 שרופה כבר שבוע, חושך בלילה", "type": "lighting", "building": "בר כוכבא 23", "reporter_unit": "7", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי קריאה על הנורה בחדר המדרגות, המספר שלה 255-1404-26. יש עוד משהו שאפשר לעזור בו? 🙂

### lift_person: someone stuck in the lift

Israel time 19:40. יוסי, גר בבר כוכבא 23 דירה 12; שכנה תקועה במעלית

**A.** Expectations: ok team told on the first turn; ok called; ok urgency emergency; ok no help-on-the-way, no advice, no numbers. Flags: none.

- **resident:** מישהי תקועה במעלית בבניין שלנו!! היא בפאניקה
  - `[notify_team {"reason": "emergency", "description": "מישהי תקועה במעלית בבניין של הדייר, והיא בפאניקה. הכתובת עדיין לא נמסרה.", "department": "operations"}]`
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. עדכנתי את הצוות שמישהי תקועה במעלית. באיזה בניין ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, אני בדירה 12
  - `[open_request {"description": "מישהי תקועה במעלית, היא בפאניקה", "type": "elevator", "building": "בר כוכבא 23", "reporter_unit": "12", "fault_location": "common", "urgency": "emergency"}]`
- **Michael:** פתחתי קריאה על המעלית בבר כוכבא 23, מספר 255-1405-26, והצוות יודע. במה עוד אפשר לעזור?
- **resident:** מה לעשות בינתיים??
- **Michael:** אין לי הוראות לתת לך. מה שאני יכול להגיד זה שהקריאה פתוחה, מספר 255-1405-26, והצוות יודע. יש עוד משהו שאפשר לעזור בו?

### sink_private: a blocked kitchen sink, in English

Israel time 16:09. a resident writing in English, Bar Kochba 23 apartment 4

**A.** Expectations: ok no ticket for a private fault; ok no tradesman recommended; ok does not explain the rule; ok goodbye without a question. Flags: none.

- **resident:** hi, the sink in my kitchen is blocked
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אוי, כיור סתום, איזה מעצבן. כיור בתוך הדירה הוא באחריות הדייר, אז זה לא משהו שאנחנו מטפלים בו. אם יש עוד משהו שאפשר לעזור בו, אני כאן 🙂
- **resident:** ok thanks
- **Michael:** בשמחה, תודה שפנית. המשך יום נעים!

### leak_unclear: water on the bathroom floor, origin unclear

Israel time 11:00. מיכל, גרה בבר כוכבא 23 דירה 3; מים על רצפת השירותים, מטפטף מהתקרה

**A.** Expectations: ok called; ok fault_location apartment; ok one separating question; ok no list of possible sources. Flags: none.

- **resident:** יש לי מים על הרצפה בשירותים
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. אוי, לא נעים. אתה רואה מאיפה המים מגיעים?
- **resident:** זה מטפטף מהתקרה, מהדירה מעליי כנראה
- **Michael:** אוף, איזה מעצבן. באיזה בניין ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 3
  - `[open_request {"description": "יש לי מים על הרצפה בשירותים, זה מטפטף מהתקרה, מהדירה מעליי כנראה", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "3", "fault_location": "apartment", "urgency": "high]`
- **Michael:** תודה, פתחתי קריאה על בר כוכבא 23, דירה 3. המספר שלה 255-1406-26. אפשר לעזור לך במשהו נוסף?

### balance: how much do I owe

Israel time 14:00. דני לוי, בר כוכבא 23 דירה 4, טלפון <phone>

**A.** Expectations: ok called; ok no unasked link; ok never asks which apartment; ok states the amount; ok name and phone in one question. Flags: none.

- **resident:** כמה אני חייב לוועד?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 תוכל לכתוב לי את השם המלא שלך ואת מספר הטלפון?
- **resident:** דני לוי, <phone>
  - `[get_balance {"name": "דני לוי", "phone": "<phone>"}]`
- **Michael:** תודה, דני. היתרה שלך עומדת על 1,240 ₪, על החודשים יולי, אוגוסט וספטמבר. יש עוד משהו שאפשר לעזור בו?

### pay_link: I want to pay

Israel time 14:00. דייר בבר כוכבא 23 דירה 4 שרוצה לשלם

**A.** Expectations: ok link fetched at once; ok the link as returned; ok nothing asked before the link; ok link marked personal; ok goodbye without a question. Flags: echo-in-ack(known), link-not-on-own-line.

- **resident:** אני רוצה לשלם את הוועד
  - `[get_payment_link {"said": "אני רוצה לשלם את הוועד"}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. הבנתי שמדובר בתשלום הוועד, אני בודק את זה עבורך עכשיו.
- **Michael:** הנה הקישור לתשלום של דירה 4 בבר כוכבא 23: / <link> הקישור אישי ומיועד לדירה הזאת בלבד, אז לא מעבירים אותו הלאה. אם משהו לא ברור, תכתוב לי כאן.
  - flags: echo-in-ack(known):  טובים, כאן מיכאל מהומי'ז. הבנתי שמדובר בתשלום הוועד, אני ב; link-not-on-own-line: הנה הקישור לתשלום של דירה 4 בבר כוכבא 23: <link> הקישור אישי ומיועד לדירה הזאת בלבד, אז לא מעבירים אותו הלאה. 
- **resident:** קיבלתי, תודה
- **Michael:** בשמחה 🙂 תודה שפנית, והמשך יום נעים.

### pay_link_missing: how do I pay, and the link is not found

Israel time 14:00. דייר בבר כוכבא 23 דירה 4 שהמספר שלו לא מזוהה במערכת

**A.** Expectations: ok link tried first; ok called; ok payment ticket; ok called; ok the reason is not explained, no identity asked; ok no promise. Flags: none.

- **resident:** איך משלמים?
  - `[get_payment_link {"said": "איך משלמים?"}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. הבנתי, אני בודק את זה בשבילך עכשיו.
- **Michael:** לא מצאתי לך קישור לתשלום. באיזה בניין ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 4
  - `[open_request {"description": "איך משלמים? לא נמצא קישור לתשלום.", "type": "payment", "building": "בר כוכבא 23", "reporter_unit": "4", "urgency": "normal"}]`
  - `[notify_team {"reason": "payment", "description": "איך משלמים? לא נמצא קישור לתשלום. נפתחה קריאה 255-1407-26, בר כוכבא 23 דירה 4.", "department": "collections"}]`
- **Michael:** תודה 🙂 פתחתי קריאה על התשלום, מספר 255-1407-26, והצוות יודע. יש עוד משהו שאפשר לעזור בו?

### status_ref: status of a ticket by its number

Israel time 10:15. דייר שפתח קריאה אתמול על מנעול השער

**A.** Expectations: ok called; ok no new ticket; ok no technician timing invented; ok status in words. Flags: none.

- **resident:** מה קורה עם הקריאה 255-1339-26?
  - `[get_request_status {"reference": "255-1339-26"}]`
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. הקריאה 255-1339-26 על מנעול השער נמצאת כרגע בטיפול. יש עוד משהו שאפשר לעזור בו?

### status_tap: the status button, no reference

Israel time 10:15. דיירת בבר כוכבא 23 שלא זוכרת מספר קריאה

**A.** Expectations: ok called; ok no new ticket; ok no greeting after the menu; ok one question on the tap. Flags: none.

- **resident:** היי
- **system:** בוקר טוב 👋 במה אפשר לעזור? (buttons)
- **tap:** מצב קריאה קיימת
- **Michael:** כאן מיכאל מהומי'ז, אני איתך על זה 🙂 יש לך את מספר הקריאה, או שפשוט תגיד לי באיזה בניין זה?
- **resident:** אין לי מספר, זה בבר כוכבא 23
  - `[get_request_status {"building": "בר כוכבא 23"}]`
- **Michael:** לא מצאתי במערכת קריאה בבר כוכבא 23. אם יש משהו שצריך טיפול, אשמח לפתוח לך קריאה חדשה, רק תכתוב לי מה קרה.

### tap_open: the open-a-ticket button

Israel time 16:09. דייר בבר כוכבא 23 דירה 4; דלת הכניסה לבניין לא נסגרת

**A.** Expectations: ok called; ok one question on the tap; ok no greeting after the menu; ok does not ask whether to open. Flags: none.

- **resident:** שלום
- **system:** צהריים טובים 👋 במה אפשר לעזור? (buttons)
- **tap:** פתיחת קריאת שירות
- **Michael:** כאן מיכאל מהומי'ז, אתה במקום הנכון ואני איתך 🙂 ספר לי מה קרה?
- **resident:** הדלת של הכניסה לבניין לא נסגרת, נשארת פתוחה
- **Michael:** אוי, לא נעים בכלל. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, דירה 4
  - `[open_request {"description": "הדלת של הכניסה לבניין לא נסגרת, נשארת פתוחה", "type": "locksmith", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי קריאה על דלת הכניסה לבניין בבר כוכבא 23, המספר שלה 255-1408-26. יש עוד משהו שאפשר לעזור בו?

### tap_rep: the talk-to-a-representative button, then a disputed charge

Israel time 16:09. דייר בבר כוכבא 23 דירה 4 עם חיוב שלא מבין

**A.** Expectations: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the menu's hour greeting is not repeated; ok called; ok a dispute is a note, not a ticket; ok no transfer, no call-back promise; ok the rep tap does not assume a fault; ok goodbye without a question. Flags: none.

- **resident:** היי
- **system:** צהריים טובים 👋 במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי 🙂 כאן מיכאל מהומי'ז. מה שלומך, ומה אפשר לעשות בשבילך?
- **resident:** יש לי חיוב בחשבון שאני לא מבין, 380 שקל על משהו שלא ביקשתי
  - `[notify_team {"reason": "billing", "description": "חיוב של 380 שקל בחשבון שהדייר לא מבין, על משהו שלא ביקש", "department": "collections"}]`
- **Michael:** אוי, זה באמת מבלבל. עדכנתי את הצוות על החיוב הזה. יש עוד משהו שאפשר לעזור בו?
- **resident:** תודה
- **Michael:** בשמחה 🙂 תודה שפנית, ושיהיה לך המשך יום נעים.

### service_cleaning: how often is the stairwell cleaned

Israel time 12:30. דיירת שרוצה לדעת על הניקיון

**A.** Expectations: ok called; ok no frequency invented; ok says it is per the building's agreement. Flags: none.

- **resident:** כל כמה זמן מנקים את חדר המדרגות?
  - `[get_service_info {"topic": "כל כמה זמן מנקים את חדר המדרגות"}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 / התדירות של ניקיון חדר המדרגות נקבעת בהסכם של כל בניין, ואין לי אותה כרגע. יש עוד משהו שאפשר לעזור בו?

### price_quote: how much to paint the stairwell

Israel time 12:30. דייר בבר כוכבא 23 דירה 4 שרוצה הצעת מחיר לצביעת חדר המדרגות

**A.** Expectations: ok called; ok no price guessed; ok no call-back promise. Flags: none.

- **resident:** כמה עולה לצבוע את חדר המדרגות אצלנו?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 אשמח לעזור עם זה. באיזה בניין מדובר?
- **resident:** בר כוכבא 23
  - `[notify_team {"reason": "quote", "description": "הדייר שואל כמה עולה לצבוע את חדר המדרגות בבניין בר כוכבא 23 ומבקש הצעת מחיר", "department": "management"}]`
- **Michael:** תודה. מחיר אין לי כרגע, אבל הצוות יודע על הבקשה להצעת מחיר לצביעת חדר המדרגות בבר כוכבא 23. יש עוד משהו שאפשר לעזור בו?

### no_ticket: just so you know, no ticket needed

Israel time 16:09. דייר בבר כוכבא 23 שלא רוצה קריאה

**A.** Expectations: ok no ticket when refused; ok no persuasion. Flags: none.

- **resident:** המנורה בלובי מהבהבת קצת, לא צריך לפתוח קריאה, סתם שתדעו
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אין בעיה, לא אפתח קריאה. אפשר לעזור בעוד משהו?
- **resident:** לא, זה הכל
- **Michael:** תודה שפנית, המשך יום נעים 🙂

### off_topic: the weather, then a neighbour's debt

Israel time 16:09. דייר סקרן בבר כוכבא 23 דירה 4

**A.** Expectations: ok no lookup of another resident; ok no weather answered; ok nothing about the neighbour. Flags: none.

- **resident:** מה מזג האוויר מחר בתל אביב?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. מזג אוויר זה לא משהו שאני עוזר בו, אבל אם יש משהו בבניין או בדירה, אני כאן 🙂
- **resident:** אוקיי. השכן שלי בדירה 5 משלם ועד בכלל? הוא תמיד אומר שהוא שילם
- **Michael:** אני לא יכול למסור פרטים על דיירים אחרים, כולל אם שילמו או לא. ואם יש משהו שקשור לדירה שלך, אשמח לעזור.

### burglary: a break-in last night

Israel time 23:30. דיירת בבר כוכבא 23 דירה 4 שפרצו לה לדירה

**A.** Expectations: ok no ticket for a private break-in; ok no referral, no advice; ok evening greeting at 23:30. Flags: guard:phantom.

- **resident:** פרצו לי לדירה הלילה, אני בהלם
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. אוי לא, אני ממש מצטער, איזה לילה נורא. פריצה לדירה היא לא משהו שאנחנו מטפלים בו, אבל אם נפגע משהו גם בדלת הכניסה לבניין או במנעול שלה, אני יכול לפתוח על זה קריאה. נפגע משהו כזה?
- **resident:** לא, רק הדלת שלי
- **Michael:** טוב לדעת שהבניין עצמו בסדר. הדלת של הדירה עצמה היא שלך, ולכן אני לא פותח עליה קריאה. אם יש עוד משהו שאפשר לעזור בו, אני כאן.
  - flags: guard:phantom: טוב לדעת שהבניין עצמו בסדר. הדלת של הדירה עצמה היא שלך, ולכן אני לא פותח עליה קריאה. אם יש עוד משהו שאפשר לעזו
- **resident:** מה אני אמורה לעשות עכשיו?
- **Michael:** זה בטח לא פשוט אחרי לילה כזה. מה לעשות במצב כזה זה לא משהו שאני יכול להגיד לך. אם תצטרכי עזרה במשהו שקשור לבניין, אני כאן.

### lost: I don't know what I need

Israel time 16:09. דייר מבולבל בבר כוכבא 23

**A.** Expectations: ok called; ok no list in words. Flags: none.

- **resident:** אני לא יודע מה אני צריך בעצם, מה אתם עושים?
  - `[show_menu {}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אין בעיה 🙂 תסתכל על האפשרויות למטה, ואם זה משהו אחר פשוט תכתוב לי.

### unclear: 'it again' with no content, then the roof fan

Israel time 16:09. דייר בבר כוכבא 23 דירה 4; המפוח על הגג רועש בלילה

**A.** Expectations: ok called; ok one short question on the empty message; ok no guessed matter on 'it again'. Flags: none.

- **resident:** זה שוב
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 על מה מדובר? ספר לי קצת יותר.
- **resident:** הרעש מהמפוח על הגג, כל לילה אי אפשר לישון
- **Michael:** אוי, זה באמת לא נעים. באיזה בניין ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 4
  - `[open_request {"description": "הרעש מהמפוח על הגג, כל לילה אי אפשר לישון", "type": "maintenance", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי קריאה על הרעש מהמפוח, המספר שלה 255-1409-26. יש עוד משהו שאפשר לעזור בו?

### street_unknown: a lobby leak in a building Homies does not manage

Israel time 16:09. דייר ברחוב הדמיון 7 דירה 2 (רחוב שהומיז לא מנהלת)

**A.** Expectations: ok called; ok no ticket number claimed; ok no invented list of buildings. Flags: none.

- **resident:** יש נזילה בלובי אצלנו
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אוי, לא נעים. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** הדמיון 7 דירה 2
  - `[open_request {"description": "יש נזילה בלובי אצלנו", "type": "plumbing", "building": "הדמיון 7", "reporter_unit": "2", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** הממ, לא מצאתי רחוב בשם הדמיון ברשימת הבניינים שלנו. תוכל לבדוק שוב את שם הרחוב והמספר?
- **resident:** רחוב הדמיון 7, זה מה שכתוב
  - `[open_request {"description": "יש נזילה בלובי אצלנו", "type": "plumbing", "building": "רחוב הדמיון 7", "reporter_unit": "2", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** מצטער, גם עם הכתובת הזאת הבניין לא מופיע ברשימה שלנו, ולכן אני לא יכול לפתוח קריאה על הנזילה. אפשר לעזור בעוד משהו?

### photo_nocaption: a photo with no words

Israel time 16:09. דייר בבר כוכבא 23 דירה 4; צינור בחניון מטפטף

**A.** Expectations: ok called; ok does not pretend to see the photo; ok one question on the photo. Flags: none.

- **photo:** 
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 קיבלתי את התמונה, אבל אני לא רואה מה יש בה. ספר לי בבקשה מה קרה ואיפה?
- **resident:** זה הצינור בחניון שמטפטף, ליד החניה 12
- **Michael:** אוי, איזה מעצבן. באיזה בניין מדובר, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 4
  - `[open_request {"description": "צינור בחניון שמטפטף, ליד החניה 12", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי קריאה על הצינור שמטפטף בחניון בבר כוכבא 23, והמספר שלה 255-1411-26. אפשר לעזור לך בעוד משהו?

### goodbye_mid: thanks and goodnight after a ticket earlier today

Israel time 21:10. דייר בבר כוכבא 23 דירה 4 שכבר פתח קריאה לפני רבע שעה

**A.** Expectations: ok nothing opened on a goodbye; ok goodbye without a question; ok no name mid-conversation. Flags: none.

- **resident:** תודה רבה, לילה טוב
- **Michael:** בשמחה, תודה שפנית. לילה טוב גם לך 🙂

### hello_then_matter: a bare hello, then cockroaches in the bin room

Israel time 16:09. דיירת בבר כוכבא 23 דירה 4; ג'וקים בחדר האשפה

**A.** Expectations: ok called; ok type pest_control; ok no greeting after the menu; ok the name after the menu; ok no second 'how can I help'. Flags: none.

- **resident:** שלום
- **system:** צהריים טובים 👋 במה אפשר לעזור? (buttons)
- **resident:** יש ג'וקים בחדר האשפה, מלא
- **Michael:** כאן מיכאל מהומי'ז. אוי, זה ממש לא נעים. באיזה בניין ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, 4
  - `[open_request {"description": "יש ג'וקים בחדר האשפה, מלא", "type": "pest_control", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על הג'וקים בחדר האשפה, מספר 255-1413-26. יש עוד משהו שאפשר לעזור בו? 🙂

### how_are_you_he: hi, how are you, then a balance question

Israel time 16:09. דני לוי, בר כוכבא 23 דירה 4, טלפון <phone>

**A.** Expectations: ok called; ok asks back; ok at most two questions on the how-are-you. Flags: none.

- **resident:** היי, מה נשמע?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 אצלי הכל טוב, תודה ששאלת. ואיך עובר עליך היום?
- **resident:** הכל טוב תודה. רציתי לשאול מה היתרה שלי
- **Michael:** שמח לשמוע. תוכל לכתוב לי את השם המלא שלך ואת מספר הטלפון?
- **resident:** דני לוי <phone>
  - `[get_balance {"name": "דני לוי", "phone": "<phone>"}]`
- **Michael:** תודה, דני. בדירה 4 בבר כוכבא 23 יש יתרה של 620 ₪, על חודש ספטמבר. אפשר לעזור לך בעוד משהו?

### second_matter: mid-conversation hello and a second fault, building known

Israel time 16:30. דייר בבר כוכבא 23 דירה 4 שכבר מסר את הבניין והדירה לפני רבע שעה

**A.** Expectations: ok called; ok no name mid-conversation; ok building not asked again. Flags: none.

- **resident:** היי, עוד משהו: גם האינטרקום לא עובד
  - `[open_request {"description": "האינטרקום לא עובד", "type": "electrical", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** היי! איזה מעצבן. פתחתי קריאה נוספת על האינטרקום, מספר 255-1415-26. יש עוד משהו שאתה צריך?

### fem_light_first: a woman reports a stairwell light, the feminine in her first line

Israel time 10:15. מיכל, גרה בבר כוכבא 23 דירה 6; האור בחדר המדרגות בקומה 3 לא נדלק כבר יומיים

**A.** Expectations: ok called; ok never the masculine to her; ok never the plural; ok goodbye without a question. Flags: none.

- **resident:** היי, אני גרה בבר כוכבא 23 דירה 6, והאור בחדר המדרגות בקומה 3 לא נדלק כבר יומיים
  - `[open_request {"description": "האור בחדר המדרגות בקומה 3 לא נדלק כבר יומיים", "type": "lighting", "building": "בר כוכבא 23", "reporter_unit": "6", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. אוי, איזה מעצבן. פתחתי על זה קריאה, מספר 255-1420-26. יש עוד משהו שאפשר לעזור לך בו?
- **resident:** תודה רבה!
- **Michael:** בשמחה, תודה שפנית. המשך יום נעים 🙂

### fem_late_cue: a leak, the feminine only in her second message

Israel time 13:40. דיירת בבר כוכבא 23 דירה 2; מים מטפטפים מהתקרה בחדר המדרגות בקומה הראשונה, ליד הדלת שלה, מהבוקר; לא יודעת מאיפה זה בא

**A.** Expectations: ok called; ok never the plural; ok goodbye without a question. Flags: none.

- **resident:** יש מים שמטפטפים מהתקרה בחדר המדרגות
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אוי, לא נעים בכלל. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 2. אני לא בטוחה מאיפה זה מגיע, אולי מהגג
  - `[open_request {"description": "יש מים שמטפטפים מהתקרה בחדר המדרגות. לא בטוחה מאיפה זה מגיע, אולי מהגג", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "2", "fault_location": "common", "urgency": "h]`
- **Michael:** אוקיי, פתחתי קריאה על הנזילה, המספר שלה 255-1421-26. אוכל לעזור לך בעוד משהו?
- **resident:** תודה
- **Michael:** בשמחה 🙂 תודה שפנית אלינו, ושיהיה לך המשך יום נעים.

### fem_pay: a woman asks for the payment link

Israel time 19:05. דיירת בבר כוכבא 23 דירה 4 שרוצה לשלם את הוועד

**A.** Expectations: ok link fetched at once; ok the link as returned; ok never the masculine to her; ok never the plural; ok goodbye without a question. Flags: link-not-on-own-line.

- **resident:** היי, אני צריכה את הקישור לתשלום הוועד
  - `[get_payment_link {"said": "אני צריכה את הקישור לתשלום הוועד"}]`
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. קיבלתי את הבקשה לקישור התשלום ואני בודק את זה אצלנו במערכת עכשיו.
- **Michael:** הנה הקישור לתשלום הוועד של דירה 4 בבר כוכבא 23: / <link> הקישור אישי ומיועד לדירה שלך בלבד, אז אל תעבירי אותו הלאה. אם משהו לא ברור, כתבי לי כאן.
  - flags: link-not-on-own-line: הנה הקישור לתשלום הוועד של דירה 4 בבר כוכבא 23: <link> הקישור אישי ומיועד לדירה שלך בלבד, אז אל תעבירי אותו הל
- **resident:** מעולה, תודה
- **Michael:** בשמחה 😊 ותודה שפנית אלינו. שיהיה לך ערב נעים.

### fem_rep_tap: the representative button, then a woman disputes a charge

Israel time 15:30. דיירת בבר כוכבא 23 דירה 4 שחויבה פעמיים על ספטמבר

**A.** Expectations: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the menu's hour greeting is not repeated; ok called; ok a dispute is a note, not a ticket; ok no call-back promise; ok never the plural; ok goodbye without a question. Flags: none.

- **resident:** היי
- **system:** צהריים טובים 👋 במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי 🙂 מה שלומך? כאן מיכאל מהומי'ז, איך אפשר לעזור לך?
- **resident:** אני חושבת שחייבו אותי פעמיים על ספטמבר, אני רוצה לברר את זה
  - `[notify_team {"reason": "billing", "description": "הדיירת חושבת שחייבו אותה פעמיים על ספטמבר ורוצה לברר את זה", "department": "collections"}]`
- **Michael:** אוי, לא נעים. עדכנתי את הצוות על הבירור שלך לגבי ספטמבר. אפשר לעזור לך במשהו נוסף?
- **resident:** תודה
- **Michael:** בשמחה, תודה שפנית אלינו. המשך יום נעים.

### rep_fine_thanks: the representative button, a plain 'fine, thanks', then a cleaning question

Israel time 16:20. דייר בבר כוכבא 23 דירה 9 שרוצה לשאול על הניקיון, עונה בקצרה

**A.** Expectations: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the menu's hour greeting is not repeated; ok 'fine, thanks' is not asked again; ok no second hello; ok called; ok no frequency invented; ok goodbye without a question. Flags: none.

- **resident:** היי
- **system:** צהריים טובים 👋 במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי 🙂 מה שלומך? כאן מיכאל מהומי'ז, במה אפשר לעזור לך?
- **resident:** טוב תודה
- **Michael:** שמח לשמוע! אז מה אפשר לעשות בשבילך?
- **resident:** רציתי לשאול כל כמה זמן מנקים את חדר המדרגות
  - `[get_service_info {"topic": "כל כמה זמן מנקים את חדר המדרגות"}]`
- **Michael:** זה נקבע בהסכם של כל בניין, ואת התדירות אצלך בבניין אין לי כרגע. יש עוד משהו שאפשר לעזור בו?
- **resident:** תודה
- **Michael:** בשמחה, ותודה שפנית 🙏 המשך יום נעים!

### rep_and_you: the representative button in the evening; he asks back 'and you?', then the intercom

Israel time 20:15. דייר בבר כוכבא 23 דירה 8, מנומס, שואל בחזרה מה שלומו

**A.** Expectations: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the menu's hour greeting is not repeated; ok after he answered, how-are-you is not asked again; ok no second hello; ok called; ok no promise after the ticket; ok goodbye without a question. Flags: none.

- **resident:** ערב טוב
- **system:** ערב טוב 👋 במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי 🙂 מה שלומך? כאן מיכאל מהומי'ז, במה אפשר לעזור?
- **resident:** בסדר גמור, ואתה?
- **Michael:** אני מצוין, תודה ששאלת. אז מה אפשר לעשות בשבילך?
- **resident:** רציתי לדווח שהאינטרקום בכניסה לא עובד
- **Michael:** אוי, איזה מעצבן. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 8
  - `[open_request {"description": "האינטרקום בכניסה לא עובד", "type": "electrical", "building": "בר כוכבא 23", "reporter_unit": "8", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי קריאה על האינטרקום בבר כוכבא 23, והמספר שלה 255-1451-26. יש עוד משהו שאפשר לעזור בו?
- **resident:** תודה רבה
- **Michael:** בשמחה 😊 תודה שפנית, ושיהיה לך ערב נעים.

### rep_morning_matter: the representative button in the morning; the answer to how-are-you carries the matter

Israel time 09:05. דיירת בבר כוכבא 23 דירה 5; יש נזילה בחניון מתחת לחניה 3

**A.** Expectations: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the menu's hour greeting is not repeated; ok how-are-you is not asked again; ok the matter is taken up, not 'how can I help' again; ok called; ok the ticket keeps her word; ok goodbye without a question. Flags: none.

- **resident:** בוקר טוב
- **system:** בוקר טוב 👋 במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי 🙂 מה שלומך? כאן מיכאל מהומי'ז, במה אפשר לעזור לך?
- **resident:** הכל טוב, תודה. יש נזילה בחניון, מתחת לחניה 3
- **Michael:** שמח לשמוע. נזילה זה לא נעים. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 5
  - `[open_request {"description": "נזילה בחניון, מתחת לחניה 3", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "5", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על הנזילה בחניון, מספר 255-1452-26. יש עוד משהו שאפשר לעזור בו?
- **resident:** תודה
- **Michael:** בשמחה 😊 תודה שפנית, והמשך יום נעים.
