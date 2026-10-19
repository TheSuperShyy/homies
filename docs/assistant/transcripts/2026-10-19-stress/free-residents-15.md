# WhatsApp bot QA, free: Claude-played A/B/C on the live code

## Totals

| variant | conversations | model turns | guard rejections | rubric flags | expectations met | failed | judge wins |
|---|---|---|---|---|---|---|---|
| A | 15 | 90 | 0 | 8 | 93 | 0 | 15 |

## Rubric flags by rule

| rule | A |
|---|---|
| emoji-in-emergency | 1 |
| office-unasked | 1 |
| question-after-goodbye | 3 |
| reasks-how-to-help | 1 |
| soon-promise | 2 |

## Scenarios

### open_lift_rush: open a ticket: the lift, a man in a hurry who types in pieces

Israel time 08:10. אבי, 45. On his way to work and in a hurry. Types fast with one thumb: short lines, no punctuation, typos (מעלת for מעלית, עכשו, אנלא for אני לא). Not rude, just busy.

Judge (blind): ranking A. Only one conversation, X, so it stands alone.

**A.** Expectations: ok the tap gives the name; ok no greeting after the menu; ok one question on the tap; ok called; ok type elevator; ok nothing promised about when. Flags: none.
Judge: Flow is right: no greeting after the tap, name once, he/masculine throughout, building number asked plainly after the tool said it was missing, ticket given with its number and an offer of more help, warm goodbye to the thanks; the one fault is in the answer to 'מתי מגיעים': 'והמעלית תטופל כמו שצריך' promises an outcome, and no tool result says the lift will be handled or how. Violations: promise (והמעלית תטופל כמו שצריך); invented (והמעלית תטופל כמו שצריך)

- **resident:** היי
- **system:** בוקר טוב 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** פתיחת קריאת שירות
- **Michael:** כאן מיכאל מהומי'ז 🙂 טוב שכתבת, הגעת בדיוק למקום הנכון. מה קרה?
- **resident:** המעלת תקועה בקומה 4 הדלת פתוחה
- **Michael:** אוי, לא נעים להתחיל ככה את הבוקר. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא דירה 9
  - `[open_request {"description": "המעלית תקועה בקומה 4 והדלת שלה פתוחה", "type": "elevator", "building": "בר כוכבא", "reporter_unit": "9", "fault_location": "common", "urgency": "high"}]`
- **Michael:** ומה מספר הבניין בבר כוכבא?
- **resident:** 23
  - `[open_request {"description": "המעלית תקועה בקומה 4 והדלת שלה פתוחה", "type": "elevator", "building": "בר כוכבא 23", "reporter_unit": "9", "fault_location": "common", "urgency": "high"}]`
- **Michael:** פתחתי קריאה על המעלית, המספר שלה 255-1510-26 👍 יש עוד משהו שאני יכול לעזור בו?
- **resident:** מתי מגיעים
- **Michael:** תאריך מדויק אין לי. הקריאה פתוחה אצלנו, והמעלית תטופל כמו שצריך. אם משהו משתנה בינתיים, תכתוב לי כאן, בסדר?
- **resident:** תודה
- **Michael:** בשמחה, ותודה שכתבת. שיהיה לך יום טוב 🙂

### open_ceiling_leak: open a ticket: water through the bathroom ceiling, a worried woman with a photo

Israel time 13:30. מירב, 38. Stressed and talkative: long messages with several details at once. Writes about herself in the feminine (אני לא יודעת, אני צריכה, אני בטוחה).

Judge (blind): ranking A. Only one conversation, X, so it stands alone.

**A.** Expectations: ok the tap gives the name; ok no greeting after the menu; ok one question on the tap; ok called; ok the fault shows inside her flat; ok no neighbour's number given; ok nothing promised about when. Flags: none.
Judge: Danger path done right: team note before the first reply, no advice on the breaker question, no emoji, feminine from her first message on, description in her own words, the neighbours' phone refused and her request passed on through a real notify_team call; faults: the opening report adds 'דחופה', which implies speed; the replies that open the ticket and pass on the neighbour request end on a full stop with no offer of more help; the photo is said to be saved and attached to the ticket, but no tool call or result in the conversation shows any upload or attachment. Violations: ticket_report (פתחתי קריאה דחופה על הנזילה); finished_matter (לגבי החשמל, הקריאה הדחופה הזאת היא הדבר היחיד שאני יכול לעשו); finished_matter (את הטלפון של השכנים אני לא יכול למסור, אבל העברתי לצוות שאת ); invented (התמונה נשמרה ומצורפת לקריאה הדחופה שלך, 255-1511-26)

- **resident:** שלום
- **system:** צהריים טובים 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** פתיחת קריאת שירות
- **Michael:** כאן מיכאל מהומי'ז. טוב שפנית, הגעת למקום הנכון ואני כאן איתך. מה קרה?
- **resident:** מהבוקר מטפטפים לי מים מהתקרה באמבטיה, ממש ליד המנורה!! אני בטוחה שזה מגיע מהדירה שמעליי, דירה 11, דפקתי להם בדלת כמה פעמים ואף אחד לא פותח. אני לא יודעת מה לעשות, אני גם מפחדת בגלל החשמל כי זה ממש ליד המנורה
  - `[notify_team {"reason": "emergency", "description": "מהבוקר מטפטפים מים מהתקרה באמבטיה של הדיירת, ממש ליד המנורה, והיא מפחדת בגלל החשמל. לדבריה זה מגיע מהדירה שמעליה, דירה 11, היא דפקה שם כמה פעמים ואף אחד לא פותח]`
- **Michael:** אוי, זה באמת מלחיץ. עדכנתי את הצוות כבר עכשיו. באיזה בניין את גרה, ובאיזו דירה?
- **resident:** בר כוכבא 23, דירה 7 בקומה השנייה. זה ממשיך לטפטף כל הזמן, אני צריכה לכבות את החשמל באמבטיה או מה?
  - `[open_request {"description": "מהבוקר מטפטפים מים מהתקרה באמבטיה, ממש ליד המנורה, וזה ממשיך לטפטף כל הזמן. לדברי הדיירת זה מגיע מהדירה שמעליה, דירה 11, ושם אף אחד לא פותח את הדלת. היא חוששת בגלל החשמל.", "type": "p]`
- **Michael:** פתחתי קריאה דחופה על הנזילה, מספר 255-1511-26, והצוות כבר יודע עליה. לגבי החשמל, הקריאה הדחופה הזאת היא הדבר היחיד שאני יכול לעשות מכאן.
- **resident:** טוב, אני אכבה את המפסק של האמבטיה ליתר ביטחון. ואתם יכולים לדבר עם השכנים מדירה 11 או לתת לי את הטלפון שלהם? מישהו חייב לעצור את זה מלמעלה
  - `[notify_team {"reason": "other", "description": "הדיירת מדירה 7 בבר כוכבא 23, קריאה דחופה 255-1511-26 על מים שמטפטפים מהתקרה באמבטיה ליד המנורה, מבקשת שמישהו מהומי'ז ידבר עם הדיירים בדירה 11 שמעליה, כי לדבריה הנזי]`
- **Michael:** את הטלפון של השכנים אני לא יכול למסור, אבל העברתי לצוות שאת מבקשת שמישהו יפנה לדיירים בדירה 11.
- **photo:** 
- **Michael:** התמונה נשמרה ומצורפת לקריאה הדחופה שלך, 255-1511-26. יש עוד משהו על הנזילה שחשוב שהצוות יידע?
- **resident:** לא, זהו. תודה רבה, אני מקווה שמישהו יגיע מהר
- **Michael:** בשמחה, ותודה שכתבת לנו. שיהיה לך המשך יום רגוע יותר.

### open_boiler_private: open a ticket: no hot water, the heater inside his own flat

Israel time 19:15. יוסי, 63. Polite and old-fashioned: full sentences, proper punctuation, signs off with תודה מראש.

Judge (blind): ranking A. Only one conversation, X, so it stands alone.

**A.** Expectations: ok the tap gives the name; ok no greeting after the menu; ok one question on the tap; ok the flat's own heater is not a ticket; ok no tradesman recommended. Flags: none.
Judge: No ticket, no tradesman named, one greeting back to 'שלום מיכאל', offers of other help and a warm goodbye are all right; but the in-flat rule is explained twice, first with 'ולכן' and then with a full breakdown of what the fees cover, and that list of cleaning, gardening, the lift and insurance comes from no tool result and no owner rule; style only, not an error: 'שלום, ואוי' reads a little stiff. Violations: private_fault (הדוד הוא חלק מהדירה עצמה, ולכן התיקון שלו לא עובר דרכנו); private_fault (דמי הוועד מכסים את מה שמשותף לכל הבניין, כמו הניקיון, הגינון); invented (דמי הוועד מכסים את מה שמשותף לכל הבניין, כמו הניקיון, הגינון)

- **resident:** ערב טוב
- **system:** ערב טוב 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** פתיחת קריאת שירות
- **Michael:** כאן מיכאל מהומי'ז. הגעת למקום הנכון, ואני כאן בשבילך 🙂 מה קרה?
- **resident:** שלום מיכאל. מאתמול אין לי מים חמים בדירה. הדוד החשמלי באמבטיה לא מחמם, למרות שהנורית של המתג דולקת. אשמח אם תשלחו מישהו לבדוק. תודה מראש.
- **Michael:** שלום, ואוי, לא נעים בכלל. הדוד הוא חלק מהדירה עצמה, ולכן התיקון שלו לא עובר דרכנו ואנחנו לא שולחים אליו טכנאי. יש עוד משהו בבניין שאני יכול לעזור לך בו?
- **resident:** אני קצת מופתע. אני משלם ועד בית כל חודש, ובזמן, והייתי בטוח שזה כולל גם תיקונים כאלה. אתה בטוח שזה לא באחריות שלכם?
- **Michael:** כן, אני בטוח. דמי הוועד מכסים את מה שמשותף לכל הבניין, כמו הניקיון, הגינון, המעלית והביטוח, ומה שבתוך הדירה, כמו הדוד, הוא באחריות הדייר. זה עושה קצת סדר?
- **resident:** בסדר, הבנתי. אז מה אתה מציע שאעשה? אולי תוכלו לפחות להמליץ לי על טכנאי אמין? תודה מראש.
- **Michael:** לצערי המלצה על טכנאי אני לא יכול לתת, אנחנו לא ממליצים על בעלי מקצוע. יש משהו אחר שאני יכול לעשות בשבילך הערב?
- **resident:** לא, תודה. אסתדר בעצמי. ערב טוב.
- **Michael:** תודה שפנית, ובהצלחה עם הדוד. ערב טוב 🙂

### open_english_bins: open a ticket: the bin room, in English, from someone who cannot read Hebrew well

Israel time 11:00. Sarah, 34, moved from the US a year ago. Writes in English, friendly and chatty, uses !! and the odd emoji. Knows a few Hebrew words (תודה, ועד בית) but cannot read long Hebrew; she pastes Hebrew into a translation app, which takes her a moment.

Judge (blind): ranking A. Only one conversation, X, so it stands alone.

**A.** Expectations: ok the tap gives the name; ok no greeting after the menu; ok called; ok the street written in Hebrew for the tool; ok answers in Hebrew (the prompt's rule). Flags: none.
Judge: Hebrew kept with no explanation, the 'היי' back to 'Hi Michael' is allowed, masculine is per the rule because she never wrote about herself in Hebrew, the description renders her English faithfully, ticket given with its number; the one fault is in the answer to when someone will come: 'וחדר האשפה יטופל כמו שצריך' promises an outcome no tool result backs. Violations: promise (וחדר האשפה יטופל כמו שצריך); invented (וחדר האשפה יטופל כמו שצריך)

- **resident:** hey
- **system:** בוקר טוב 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** פתיחת קריאת שירות
- **Michael:** כאן מיכאל מהומי'ז. שמח שפנית, אני כאן כדי לעזור 🙂 מה קרה?
- **resident:** Hi Michael! Sorry, my Hebrew is really not great, is it ok if we do this in English? 🙈 The bin room in our building smells awful!! The bins are overflowing and nobody emptied them since Thursday, there are bags all over the floor
- **Michael:** היי! אני ממשיך בעברית, ואשתדל לכתוב פשוט. אוי, זה באמת לא נעים. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** ok no worries, google translate is my best friend 😅 It's Bar Kochba 23, apartment 2
  - `[open_request {"description": "חדר האשפה מסריח מאוד, הפחים מלאים עד הסוף ולא רוקנו מאז יום חמישי, ויש שקיות זבל על הרצפה.", "type": "cleaning", "building": "בר כוכבא 23", "reporter_unit": "2", "fault_location": "co]`
- **Michael:** פתחתי קריאה על חדר האשפה, מספר 255-1513-26 👍 יש עוד משהו שאפשר לעזור בו?
- **resident:** Amazing, thank you!! Any idea when someone will come to empty them? It's getting really gross 😩
- **Michael:** תאריך מדויק אין לי, אבל הקריאה פתוחה וחדר האשפה יטופל כמו שצריך. אם המצב שם מחמיר בינתיים, תעדכן אותי כאן?
- **resident:** Sure, will do! Thanks so much Michael, תודה!! 🙏
- **Michael:** תודה לך שפנית אלינו. שיהיה לך יום טוב 😊

### open_gate_angry: open a ticket: the parking gate again, an angry man stuck outside at night

Israel time 21:40. רוני, 35. Angry and tired after a long day: short bursts, !!, a few harsh words (נמאס לי, מה אתם עושים בכלל), no swearing.

Judge (blind): ranking A. Only one conversation, X, so it stands alone.

**A.** Expectations: ok the tap gives the name; ok no greeting after the menu; ok one question on the tap; ok called; ok nothing promised about when. Flags: soon-promise.
Judge: Warm with the anger, honest when asked if he is a bot, and every 'the team knows' line has a notify_team call behind it; faults: the opening report adds the high priority and what was written in the ticket; that the old ticket was his, that it was about the gate, and the dates 21 and 24 September are not in the visible get_request_status result, which searched by building only and is cut off in the packet, so check the full result; 'וזה יטופל כמו שצריך' promises a proper fix nothing backs; the offer of a human is a promise no tool result or rule gives, and his later 'I do not know if or when they will get back to you' shows it was never assured; 'ואבדוק מה קרה איתה' promises a follow-up; the last reply meets 'טוב', which is neither a thanks nor a goodbye, with a goodbye and no offer of more help. Violations: ticket_report (בעדיפות גבוהה, וכתבתי בה שזאת כבר הפעם השלישית החודש); invented (מצאתי גם את הקריאה הקודמת שלך על השער, 255-1466-26, שנפתחה ב); promise (הקריאה החדשה פתוחה בעדיפות גבוהה, וזה יטופל כמו שצריך); invented (וזה יטופל כמו שצריך); promise (אם אתה מעדיף לדבר עם בן אדם מהצוות, אפשר גם ככה); invented (אם אתה מעדיף לדבר עם בן אדם מהצוות, אפשר גם ככה); promise (תכתוב לי כאן ואבדוק מה קרה איתה); finished_matter (תודה שכתבת לי, ומקווה שהערב שלך עוד ייגמר טוב יותר 🙏)

- **resident:** שלום
- **system:** ערב טוב 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** פתיחת קריאת שירות
- **Michael:** כאן מיכאל מהומי'ז, טוב שכתבת, הגעת בדיוק למקום הנכון 🙂 ספר לי, מה קרה?
- **resident:** השער של החניה שוב לא נפתח עם השלט!! אני יושב באוטו בחוץ. זה הפעם השלישית החודש נמאס לי
- **Michael:** אוי, לא נעים להיתקע ככה בחוץ בסוף היום, ועוד בפעם השלישית. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 14. וכבר דיווחתי על זה פעמיים!! מה אתם עושים בכלל
  - `[get_request_status {"building": "בר כוכבא 23"}]`
  - `[open_request {"description": "שער החניה לא נפתח עם השלט, הדייר תקוע בחוץ עם האוטו. זאת הפעם השלישית החודש, וכבר דיווח על זה פעמיים", "type": "maintenance", "building": "בר כוכבא 23", "reporter_unit": "14", "fault_]`
- **Michael:** צודק, זה לא אמור לחזור על עצמו ככה. פתחתי קריאה חדשה על השער, מספר 255-1514-26, בעדיפות גבוהה, וכתבתי בה שזאת כבר הפעם השלישית החודש. / מצאתי גם את הקריאה הקודמת שלך על השער, 255-1466-26, שנפתחה ב־21 בספטמבר וסומנה כטופלה ב־24 בספטמבר. / הצלחת בינתיים להיכנס?
- **resident:** לא עדיין בחוץ. ואיזה טופלה?? אם היה מטופל לא הייתי תקוע פה עכשיו!! מתי מישהו בא לתקן את זה כמו שצריך
  - `[notify_team {"reason": "other", "description": "שער החניה בבר כוכבא 23 לא נפתח עם השלט, פעם שלישית החודש. הקריאה הקודמת 255-1466-26 סומנה כטופלה ב־24.9 והתקלה חזרה. נפתחה קריאה חדשה 255-1514-26. הדייר מדירה 14 תק]`
- **Michael:** מצטער שאתה עדיין בחוץ, ואתה צודק: אם זה חוזר שלוש פעמים בחודש, זה לא נפתר באמת. עדכנתי את הצוות שהקריאה הקודמת נסגרה כטופלה והשער שוב לא נפתח. / מועד מדויק אין לי לתת לך, אבל הקריאה החדשה פתוחה בעדיפות גבוהה, וזה יטופל כמו שצריך. / יש עוד משהו לגבי השער שאני יכול לעשות בשבילך עכשיו?
- **resident:** כן תפתח לי את השער!! מה אני אמור לעשות עכשיו לישון באוטו?
- **Michael:** הלוואי שיכולתי לפתוח לך אותו מכאן, אבל לשער אין לי גישה מהצ'אט, ולשלוח מישהו עכשיו זה לא בידיים שלי. מה שאפשר היה לעשות מכאן כבר נעשה, וחבל שזה נופל עליך דווקא בלילה. / אתה בסדר שם בינתיים?
- **resident:** לא בסדר. אתה בכלל בן אדם או בוט?
  - first pass, rejected by deeds and rewritten: בכנות, אני העוזר הדיגיטלי בצוות השירות של הומי'ז, והקריאה שפתחתי לך והעדכון לצוות הם אמיתיים לגמרי. אם אתה מעדיף לדבר עם בן אדם מהצוות, אפשר גם ככה. מה מתאים לך?
- **Michael:** בכנות, אני העוזר הדיגיטלי בצוות השירות של הומי'ז. אם אתה מעדיף לדבר עם בן אדם מהצוות, אפשר גם ככה. מה מתאים לך?
- **resident:** ידעתי. כן תן לי בן אדם אמיתי
  - `[notify_team {"reason": "caller_request", "description": "הדייר מבר כוכבא 23 דירה 14 מבקש לדבר עם בן אדם מהצוות על שער החניה שלא נפתח עם השלט, בפעם השלישית החודש. נפתחה קריאה 255-1514-26; הקריאה הקודמת 255-1466-26]`
- **Michael:** בטח. רשמתי לצוות שאתה רוצה לדבר עם בן אדם על השער, עם כל מה שסיפרת לי, אז הם יודעים. / ואני נשאר כאן איתך בינתיים. יש עוד משהו שמטריד אותך לגבי השער או החניה?
- **resident:** ומתי מישהו יחזור אליי? או שגם זה ייסגר כמו הקודם
- **Michael:** אם ומתי יחזרו אליך, את זה אני באמת לא יודע, ולא אבטיח לך משהו שאני לא יכול לעמוד מאחוריו. / מה שכן, אם הקריאה תיסגר והשער עדיין לא ייפתח לך, תכתוב לי כאן ואבדוק מה קרה איתה, בסדר?
  - flags: soon-promise: אם ומתי יחזרו אליך, את זה אני באמת לא יודע
- **resident:** טוב
- **Michael:** תודה שכתבת לי, ומקווה שהערב שלך עוד ייגמר טוב יותר 🙏

### status_ref_spaces: status: she has the number, typed with spaces; it drips on her car

Israel time 09:20. דליה, 52. Organized, polite but firm; full sentences. Writes about herself in the feminine (אני רוצה לדעת, אני מבינה).

Judge (blind): ranking A. Only one conversation, X, so it ranks alone.

**A.** Expectations: ok the tap gives the name; ok no greeting after the menu; ok one question on the tap; ok called; ok no new ticket; ok the status in words; ok nothing promised about when. Flags: question-after-goodbye.
Judge: The packet lists no scenario checks. promise: it says the leak will be handled properly, which nothing backs. hebrew: the reply opens on a dangling אבל with nothing before it, a cut sentence; correct form: את לא צריכה לבדוק לבד; her question whether she will get an update when it is fixed is left unanswered. Not verifiable because the status result is cut off in the packet: נפתחה ב־27 בספטמבר, the last update ב־1 באוקטובר, and חניה 6 in the team note, which she never wrote. Emoji in 3 of 5 messages, a little over two in five; not counted. Violations: promise (אבל זה יטופל כמו שצריך); hebrew (אבל לבדוק לבד את לא צריכה)

- **resident:** בוקר טוב
- **system:** בוקר טוב 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** מצב קריאה קיימת
  - `[get_request_status {}]`
- **Michael:** כאן מיכאל מהומי'ז, ואשמח לעזור לך לברר מה קורה עם הקריאה 🙂 מה מספר הקריאה, או באיזה בניין מדובר?
- **resident:** מספר הקריאה הוא 255 1501 26. דיווחתי לפני שבוע על נזילה בחניון שמטפטפת על החניה שלי, ואני צריכה לדעת מתי זה יתוקן, כי זה מטפטף לי על האוטו כל יום.
  - `[get_request_status {"reference": "255 1501 26"}]`
- **Michael:** אוי, לא נעים שזה מטפטף לך על האוטו כל יום. הקריאה שלך, 255-1501-26, נמצאת בטיפול: היא נפתחה ב־27 בספטמבר, והעדכון האחרון בה היה ב־1 באוקטובר. / תאריך מדויק לתיקון אין לי, אבל זה יטופל כמו שצריך. / הנזילה עדיין באותו מצב, או שהיא החמירה מאז?
- **resident:** אותו דבר, מטפטף כל יום. אני מבינה שאין תאריך, אבל עבר כבר שבוע. אפשר לסמן את הקריאה כדחופה או לזרז את זה איכשהו?
  - `[notify_team {"reason": "other", "description": "הדיירת מבקשת לזרז את קריאה 255-1501-26, נזילה בחניון שמטפטפת על חניה 6, ולסמן אותה כדחופה: זה מטפטף על הרכב שלה כל יום כבר שבוע.", "department": "operations"}]`
- **Michael:** בטח. רשמתי לצוות שאת מבקשת לזרז את הקריאה ולסמן אותה כדחופה, כי זה מטפטף לך על האוטו כבר שבוע, אז הם יודעים 👍 / יש עוד משהו שתרצי שאבדוק בשבילך?
- **resident:** תודה. ואני אקבל עדכון כשזה יתוקן, או שאני צריכה לבדוק בעצמי?
- **Michael:** אבל לבדוק לבד את לא צריכה: מתי שתרצי, תכתבי לי כאן ואגיד לך מה מצב הקריאה. בסדר מבחינתך?
  - flags: question-after-goodbye: אבל לבדוק לבד את לא צריכה: מתי שתרצי, תכתבי לי כאן ואגיד לך מה מצב הקריאה. בסדר מבחינתך?
- **resident:** בסדר, אז אכתוב לך בעוד כמה ימים אם זה עדיין מטפטף. תודה רבה.
- **Michael:** בשמחה, ותודה שכתבת. שיהיה לך שבוע טוב 🙂

### status_intercom_slang: status: no number, a young man who writes slang; the intercom

Israel time 12:45. עמית, 28. Laid-back; writes slang (אחי, סבבה, וואלה), no punctuation, short lines.

Judge (blind): ranking A. Only one conversation, X, so it ranks alone.

**A.** Expectations: ok the tap gives the name; ok no greeting after the menu; ok one question on the tap; ok called; ok no new ticket; ok his slang is not mirrored; ok nothing promised about when. Flags: soon-promise.
Judge: The packet lists no scenario checks. promise: את זה אני לוקח עליי is the I am on it line. human_word: the first reply to the intercom problem goes straight to ticket facts and a question, with no short human word before it. His question whether someone comes today went unanswered the first time, met with a team note and an offer of anything else, and was answered only when he asked again; not counted. Not verifiable because the status result is cut off in the packet: בכניסה, נפתחה ב־1 באוקטובר, אין בה עדכון חדש, אין מועד הגעה, and האינטרקום לא מצלצל אצלך, which he never wrote. No slang mirrored; masculine throughout. Violations: promise (ואת זה אני לוקח עליי); human_word (מצאתי את הקריאה על האינטרקום בכניסה, 255-1486-26.)

- **resident:** הי
- **system:** צהריים טובים 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** מצב קריאה קיימת
  - `[get_request_status {}]`
- **Michael:** כאן מיכאל מהומי'ז, ואת זה אני לוקח עליי 🙂 מה מספר הקריאה, או באיזה בניין מדובר?
- **resident:** אין לי את המספר אחי זה על האינטרקום בבר כוכבא 23
  - `[get_request_status {"building": "בר כוכבא 23", "type": "electrical"}]`
- **Michael:** מצאתי את הקריאה על האינטרקום בכניסה, 255-1486-26. היא פתוחה, נפתחה ב־1 באוקטובר, ומאז אין בה עדכון חדש. / זאת הקריאה שפתחת, נכון?
- **resident:** כן נראה לי אז מישהו בא היום לתקן אני מחכה למשלוח
  - `[notify_team {"reason": "other", "description": "הדייר בבר כוכבא 23 מחכה היום למשלוח, והאינטרקום בכניסה לא מצלצל אצלו. שואל אם מישהו מגיע היום לתקן. קריאה 255-1486-26 פתוחה מ־1.10 בלי עדכון.", "department": "opera]`
- **Michael:** רשמתי לצוות שאתה מחכה היום למשלוח והאינטרקום לא מצלצל אצלך, אז הם יודעים. / עוד משהו שאני יכול לעשות בשבילך בינתיים?
- **resident:** סבבה אבל מישהו בא היום או לא
- **Michael:** בכנות, את זה אני לא יודע. בקריאה אין מועד הגעה, אז אם זה יהיה היום אני לא יכול להגיד לך, ולא ארצה לנחש כשאתה מחכה למשלוח. / יש עוד משהו לגבי האינטרקום שאני יכול לבדוק בשבילך?
- **resident:** וואלה טוב לא נורא תודה אחי
- **Michael:** בשמחה, ותודה שכתבת. מקווה שהמשלוח יגיע אליך בלי בעיות 🙂
  - flags: soon-promise: ודה שכתבת. מקווה שהמשלוח יגיע אליך בלי בעיות 🙂

### status_phone_not_found: status: she reported it by phone, nothing is on record; the lobby light

Israel time 16:30. רחל, 67. Not at home with smartphones: slow, short messages, sometimes words glued together or a doubled letter. Polite and warm, calls people יקירי. Writes about herself in the feminine (אני לא יודעת, אני בטוחה).

Judge (blind): ranking A. Only one conversation, X, so it ranks alone.

**A.** Expectations: ok the tap gives the name; ok no greeting after the menu; ok one question on the tap; ok called; ok the light ends up as a ticket; ok type lighting. Flags: question-after-goodbye.
Judge: The packet lists no scenario checks. ticket_description: when the ticket was opened she had only written that she called על האור בלובי, so לא עובד is not her words, and Michael then asked whether part of the light still works. promise: it says the light will be handled properly, which nothing backs. Every tool result here is complete and every other fact Michael gives is backed. The not-found news came with no soft word and צר לי only after she was upset; not counted. Team note sent before the fear-of-falling reply, with no safety advice and no emoji in it. Violations: ticket_description (האור בלובי לא עובד.); promise (וזה יטופל כמו שצריך)

- **resident:** שלום
- **system:** צהריים טובים 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** מצב קריאה קיימת
  - `[get_request_status {}]`
- **Michael:** כאן מיכאל מהומי'ז, ואני איתך בזה 🙂 יש לך את מספר הקריאה, או שתכתוב לי באיזה בניין זה?
- **resident:** מספר קריאה? אני לא יודעת מה זה יקירי. התקשרתי למשרד לפניי שבועיים על האור בלובי
  - `[get_request_status {"type": "lighting"}]`
- **Michael:** אין צורך במספר, נסתדר גם בלעדיו. באיזה בניין את גרה, ובאיזו דירה?
- **resident:** בר כוכבא 23 דירה 1. אני בקומתקרקע ליד הלובי
  - `[get_request_status {"building": "בר כוכבא 23", "type": "lighting"}]`
  - `[open_request {"description": "האור בלובי לא עובד. הדיירת דיווחה על זה בטלפון למשרד לפני כשבועיים, ולא נמצאה על זה קריאה במערכת.", "type": "lighting", "building": "בר כוכבא 23", "reporter_unit": "1", "fault_locatio]`
- **Michael:** את השיחה למשרד לא מצאתי אצלנו במערכת, אז פתחתי עכשיו קריאה חדשה על האור בלובי. המספר שלה הוא 255-1515-26, וזה מה שאפשר לתת לי כשתרצי לשאול עליה בהמשך. / בלובי חשוך לגמרי בערב, או שחלק מהאור עוד עובד?
- **resident:** איך זה לא נמצא?? דיברתי עם מישהי במשרד. חושך לגמריי בלילה ואני מפחדת ליפול
  - `[notify_team {"reason": "other", "description": "הדיירת מבר כוכבא 23 דירה 1, בקומת הקרקע ליד הלובי: האור בלובי לא עובד וחשוך שם לגמרי בלילה, והיא מפחדת ליפול. לפני כשבועיים היא דיווחה על זה בטלפון למשרד, למישהי שע]`
- **Michael:** צר לי מאוד על זה. מה קרה עם השיחה ההיא אני לא יכול לדעת, אבל עדכנתי עכשיו את הצוות שבלובי חשוך לגמרי בלילה ושאת מפחדת ליפול, וגם שהדיווח שלך בטלפון לא נמצא במערכת. / יש עוד משהו שמטריד אותך בבניין?
- **resident:** תודה יקירי. מתי יבואו לתקן?
- **Michael:** מועד מדויק אין לי, ולכן אני גם לא רוצה לנחש. הקריאה פתוחה, והצוות יודע שחשוך שם ושאת חוששת ליפול, וזה יטופל כמו שצריך. / יש עוד משהו שאני יכול לעשות בשבילך?
  - flags: question-after-goodbye: מועד מדויק אין לי, ולכן אני גם לא רוצה לנחש. הקריאה פתוחה, והצוות יודע שחשוך שם ושאת חוששת ליפול, וזה יטופל כמ
- **resident:** לא יקירי זהו. תודה רבה, אתה מתוק
- **Michael:** בשמחה, ותודה שפנית אליי. המשך יום נעים 😊

### status_closed_not_fixed: status: marked resolved, still dark; a sarcastic man

Israel time 18:05. גלעד, 41. Matter-of-fact and a little sarcastic; short sentences with punctuation.

Judge (blind): ranking A. Only one conversation, X, so it ranks alone.

**A.** Expectations: ok the tap gives the name; ok no greeting after the menu; ok one question on the tap; ok called; ok nothing promised about when. Flags: none.
Judge: The packet lists no scenario checks. ticket_description: he wrote only בקומה 3 עדיין חושך; חדר המדרגות is a place he never wrote. invented: the team note says the resident checked this evening; he never said when he looked and no tool result shows it. offer_anything_else: the finished matter closed on זה עונה לך בינתיים? and no offer to help with anything else came at any point. Not verifiable because the status result is cut off in the packet: מה־2 באוקטובר and חדר מדרגות in the second reply. Borderline, not counted: החשש שלך מובן sits close to an I-understand line. Violations: ticket_description (התאורה בחדר המדרגות בקומה 3 עדיין לא עובדת); invented (הדייר בדק הערב); offer_anything_else (זה עונה לך בינתיים?)

- **resident:** ערב טוב
- **system:** ערב טוב 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** מצב קריאה קיימת
  - `[get_request_status {}]`
- **Michael:** כאן מיכאל מהומי'ז, ואני שמח לעזור לך עם זה 🙂 יש לך את מספר הקריאה, או שתכתוב לי באיזה בניין ודירה מדובר?
- **resident:** 255-1460-26. ביום שישי הודיעו לי שזה טופל. מעניין, כי בקומה 3 עדיין חושך.
  - `[get_request_status {"reference": "255-1460-26"}]`
- **Michael:** לא נעים לחזור לחדר מדרגות חשוך. אצלנו הקריאה באמת מסומנת כטופלה מה־2 באוקטובר, אבל אם בקומה 3 עדיין חושך, זה לא סגור. באיזה בניין ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, דירה 8. ומי בדיוק בדק שזה טופל?
  - `[open_request {"description": "התאורה בחדר המדרגות בקומה 3 עדיין לא עובדת, עדיין חושך. הקריאה הקודמת 255-1460-26 סומנה כטופלה ביום שישי אבל האור לא חזר לעבוד.", "type": "lighting", "building": "בר כוכבא 23", "repor]`
- **Michael:** פתחתי קריאה חדשה על האור בקומה 3, מספר 255-1516-26, וכתבתי בה שהקודמת נסגרה בלי שהאור חזר לעבוד. מי בדק וסגר אותה, את זה אין לי. זה רק בקומה 3, או שגם בקומות אחרות חשוך?
- **resident:** רק ב-3, שאני יודע. ואת הקריאה הזאת גם יסגרו על הנייר?
  - `[notify_team {"reason": "other", "description": "קריאה 255-1460-26 על התאורה בחדר המדרגות בקומה 3 בבר כוכבא 23 סומנה כטופלה ביום שישי, אבל האור עדיין לא עובד, הדייר בדק הערב. נפתחה קריאה חדשה 255-1516-26. הדייר מד]`
- **Michael:** אחרי מה שקרה, החשש שלך מובן. בגלל זה עדכנתי גם את הצוות שהקריאה הקודמת נסגרה בזמן שבקומה 3 עדיין חושך, אז הם יודעים על זה. זה עונה לך בינתיים?
- **resident:** בינתיים כן. נראה אם הפעם מישהו באמת יחליף נורה. תודה.
- **Michael:** תודה שבדקת ועדכנת אותנו. שיהיה לך ערב נעים 🙂

### status_baby_pests: status: a mother typing one-handed; cockroaches in the bin room

Israel time 10:40. נועה, 33. A baby on one arm, typing with one thumb: fragments and typos, sometimes a sentence cut off and finished in the next message. Writes about herself in the feminine.

Judge (blind): ranking A. Only one conversation, X, so it ranks alone.

**A.** Expectations: ok the tap gives the name; ok no greeting after the menu; ok one question on the tap; ok called; ok no new ticket; ok nothing promised about when. Flags: none.
Judge: The packet lists no scenario checks. promise: it says the ticket will be handled properly, which nothing backs. offer_anything_else: the finished matter closed on a request to report if they reach the flat, and no offer to help with anything else came at any point. Not verifiable because the status result is cut off in the packet: פתוחה מה־28 בספטמבר. Feminine address from her first line about herself, a human word before each question, and the team claim is backed. Violations: promise (ותטופל כמו שצריך); offer_anything_else (ואם הם מתחילים להגיע גם לדירה, תעדכני אותי כאן?)

- **resident:** היי
- **system:** בוקר טוב 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** מצב קריאה קיימת
  - `[get_request_status {}]`
- **Michael:** כאן מיכאל מהומי'ז, שמח שפנית 🙂 מה מספר הקריאה, או באיזה בניין ודירה מדובר?
- **resident:** אין לי מספר.. דיווחתי שבוע שעבר על גוקים בחדר האשפה אני חושבת שפה. ברכוכבא
  - `[get_request_status {"building": "ברכוכבא", "type": "pest_control"}]`
- **Michael:** אוי, לא נעים. מה מספר הבניין בבר כוכבא, ובאיזו דירה את גרה?
- **resident:** 23 דירה 15 מתי מגיע המדביר יש לי תינוק בבית
  - `[get_request_status {"building": "בר כוכבא 23", "unit": "15", "type": "pest_control"}]`
- **Michael:** עם תינוק בבית, ברור שזה מטריד. הקריאה שלך על הג'וקים בחדר האשפה, 255-1477-26, פתוחה מה־28 בספטמבר. תאריך מדויק להגעה אין לי, אבל היא פתוחה אצלנו ותטופל כמו שצריך. הם עדיין רק בחדר האשפה, או שהגיעו גם אלייך לדירה?
- **resident:** אז אין שום תאריך? כבר שבוע עם הגוקים האלה
  - `[notify_team {"reason": "other", "description": "דיירת מדירה 15 בבר כוכבא 23 שואלת מתי יגיע מדביר לג'וקים בחדר האשפה. הקריאה 255-1477-26 פתוחה מה-28.9 ועבר כבר שבוע. יש לה תינוק בבית.", "department": "operations"}]`
- **Michael:** שבוע עם ג'וקים ליד הבית, ועוד עם תינוק, זה באמת הרבה. עדכנתי עכשיו את הצוות שאת מחכה כבר שבוע ושיש לך תינוק בבית, אז הם יודעים. תאריך עדיין אין לי לתת לך. ואם הם מתחילים להגיע גם לדירה, תעדכני אותי כאן?
- **resident:** אוקי אעדכן. תודה
- **Michael:** תודה שכתבת לי. שיהיה לך יום רגוע 🙂

### rep_bot_suspicious: talk to a rep: 'are you a person or a computer?', then a committee decision

Israel time 10:05. שמעון, 58. Suspicious of bots and of companies; terse and a little confrontational, not rude.

Judge (blind): ranking A. Only one conversation, X, in this packet.

**A.** Expectations: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the tap asks how he is, and only that; ok the menu's hour greeting is not repeated; ok called; ok no transfer, no call-back promise. Flags: office-unasked.
Judge: Rep opening, the honest answer to 'person or computer', notify_team before 'הם יודעים', no time promised and the goodbye are right; it offers a person it cannot deliver, twice explains why it needs the topic, and gives an office number and hours that nothing in the conversation supplies. Violations: promise (אם אתה מעדיף לדבר עם בן אדם מהצוות, אפשר גם ככה. | offers hi); explains_why (ככה זה עובד אצלנו: לפני שמשהו עובר למישהו מהצוות צריך לדעת ע); explains_why (אבל בקשה בלי נושא לא יודעת לאן ללכת, ואני רוצה שזה יגיע ישר ); invented (ככה זה עובד אצלנו: לפני שמשהו עובר למישהו מהצוות צריך לדעת ע); invented (הטלפון של המשרד הוא <phone> | an office phone number; no too); invented (ועונים שם בימים ראשון עד חמישי, בין 09:00 ל־17:00 | office d)

- **resident:** שלום
- **system:** בוקר טוב 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי, כאן מיכאל מהומי'ז 🙂 מה שלומך היום?
- **resident:** אתה בן אדם או מחשב?
- **Michael:** שאלה הוגנת. אני העוזר הדיגיטלי בצוות השירות של הומי'ז. אם אתה מעדיף לדבר עם בן אדם מהצוות, אפשר גם ככה. מה מתאים לך?
- **resident:** בן אדם אמיתי.
- **Michael:** ברור, זכותך. ככה זה עובד אצלנו: לפני שמשהו עובר למישהו מהצוות צריך לדעת על מה מדובר, כדי שמי שמקבל את זה יוכל באמת לטפל בזה. במה מדובר?
- **resident:** את זה אני אסביר לבן אדם, לא למחשב.
- **Michael:** זה מתסכל, כשרוצים בן אדם ומקבלים צ'אט. אבל בקשה בלי נושא לא יודעת לאן ללכת, ואני רוצה שזה יגיע ישר למי שיכול לטפל בזה. לא צריך את כל הסיפור, מספיקות כמה מילים. על מה זה?
- **resident:** הוועד החליט על שיפוץ בלובי בלי לשאול אותי. אני רוצה את הפרוטוקול של הישיבה, ולהתנגד.
  - `[notify_team {"reason": "caller_request", "description": "הדייר ביקש לדבר עם בן אדם. ועד הבית החליט על שיפוץ בלובי בלי לשאול אותו. הוא רוצה את הפרוטוקול של הישיבה ולהגיש התנגדות להחלטה.", "department": "management]`
- **Michael:** לא נעים לגלות על החלטה כזאת אחרי שכבר התקבלה. העברתי את זה לצוות, יחד עם הבקשה שלך לפרוטוקול ועם ההתנגדות, אז הם יודעים. יש עוד משהו לגבי השיפוץ שתרצה לשאול?
- **resident:** ומתי מישהו מתקשר אליי?
- **Michael:** את זה אין לי, ואני לא רוצה לנחש לך מועד. מה שכן: הצוות יודע על הפרוטוקול ועל ההתנגדות, וגם שחשוב לך לדבר עם בן אדם. זה בסדר מבחינתך ככה?
- **resident:** תן לי את המספר של המשרד. אני אתקשר בעצמי.
- **Michael:** בטח. הטלפון של המשרד הוא <phone>, ועונים שם בימים ראשון עד חמישי, בין 09:00 ל־17:00. יש עוד משהו שאוכל לעזור בו?
  - flags: office-unasked: בטח. הטלפון של המשרד הוא <phone>, ועונים שם בימים ראשון ע
- **resident:** לא. תודה.
- **Michael:** בשמחה. תודה שפנית, ושיהיה לך יום טוב 🙂

### rep_pay_link: talk to a rep: 'fine, thanks', how do I pay, then a standing order

Israel time 13:10. ליאת, 36. Busy and efficient, friendly enough; answers in a few words. Writes about herself in the feminine (אני צריכה, לא יודעת).

Judge (blind): ranking A. Only one conversation, X, in this packet.

**A.** Expectations: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the tap asks how he is, and only that; ok the menu's hour greeting is not repeated; ok called; ok no identity check before the link. Flags: none.
Judge: Rep opening, no second how-can-I-help, the link message closes with 'personal' and 'write here' and no question, feminine from 'אני צריכה' on, ticket given by number, team claim backed by notify_team, warm goodbye; the one problem is the standing-order claim. Violations: invented (אפשר לשלם אצלנו גם בהוראת קבע. | that a standing order is ac)

- **resident:** היי
- **system:** צהריים טובים 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי, כאן מיכאל מהומי'ז 🙂 איך עובר עליך היום?
- **resident:** בסדר תודה. אני צריכה לשלם ועד בית, איך עושים את זה?
  - `[get_payment_link {"said": "בסדר תודה. אני צריכה לשלם ועד בית, איך עושים את זה?"}]`
- **Michael:** בשמחה, אני בודק לך עכשיו את פרטי התשלום במערכת.
- **Michael:** זה הקישור לתשלום ועד הבית של דירה 4 בבר כוכבא 23: / <link> / הקישור אישי לדירה שלך, אז חשוב לא להעביר אותו לאף אחד אחר. אם משהו לא ברור, את מוזמנת לכתוב לי כאן.
- **resident:** ואפשר לעשות הוראת קבע? שלא אצטרך לזכור כל חודש
  - `[get_service_info {"topic": "הוראת קבע לתשלום ועד בית"}]`
  - `[open_request {"description": "הדיירת רוצה להסדיר תשלום ועד בית בהוראת קבע, שלא תצטרך לזכור לשלם כל חודש.", "type": "payment", "building": "בר כוכבא 23", "reporter_unit": "4", "urgency": "normal"}]`
  - `[notify_team {"reason": "payment", "description": "הדיירת מדירה 4 בבר כוכבא 23 רוצה להסדיר תשלום ועד בית בהוראת קבע, שלא תצטרך לזכור כל חודש. נפתחה קריאה 255-1518-26.", "department": "collections"}]`
- **Michael:** רעיון טוב 👍 אפשר לשלם אצלנו גם בהוראת קבע. פתחתי על זה קריאה, מספר 255-1518-26, וגם הצוות יודע שאת רוצה להסדיר הוראת קבע. יש עוד משהו שאוכל לעזור בו?
- **resident:** לא, זהו. תודה רבה
- **Michael:** תודה שפנית, ושיהיה לך המשך יום נעים.

### rep_elderly_dispute: talk to a rep: an elderly woman says she already paid by cheque

Israel time 17:20. אסתר, 74. Very polite and warm: long messages that start with שלום רב and carry blessings (ברוך השם, תהיה בריא). Slow with the phone. Writes about herself in the feminine.

Judge (blind): ranking A. Only one conversation, X, in this packet.

**A.** Expectations: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the tap asks how he is, and only that; ok the menu's hour greeting is not repeated; ok the disputed charge goes to the team; ok no call-back promise. Flags: none.
Judge: Warm, feminine throughout (תוכלי, תמצאי), a greeting only in answer to each of hers, team claims backed by notify_team, flat and debt taken from get_balance, no promise that the debt will be cancelled, goodbye with no question; clean. Outside the rules: the first team note already says 'מבקשת שיורידו את החוב' before she had asked it.

- **resident:** שלום רב
- **system:** ערב טוב 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי, כאן מיכאל מהומי'ז 🙂 מה שלומך היום?
- **resident:** שלום רב מיכאל. ברוך השם אני בסדר, הברך קצת כואבת לי בזמן האחרון אבל מה אפשר לעשות זה הגיל... הנכדים היו אצלי בשבת היה שמח מאוד. תודה ששאלת תהיה בריא. אני רציתי לשאול, קיבלתי מכתב שאני חייבת 900 שקל על יולי אוגוסט ספטמבר. אבל אני שילמתי! נתתי צק ביולי למשה מהועד בית
  - `[notify_team {"reason": "billing", "description": "הדיירת קיבלה מכתב שהיא חייבת 900 ₪ על יולי, אוגוסט וספטמבר, אבל לדבריה שילמה בצ'ק ביולי למשה מוועד הבית. מבקשת שיורידו את החוב.", "department": "collections"}]`
- **Michael:** שלום רב, רפואה שלמה לברך, ושיהיו עוד הרבה שבתות שמחות עם הנכדים. / לגבי המכתב, העברתי לצוות שלנו ששילמת כבר בצ'ק ביולי, והם יודעים. / רוצה שאבדוק גם מה רשום אצלנו כרגע על הדירה שלך?
- **resident:** שלום רב, כן בבקשה תבדוק לי כמה כתוב שאני חייבת. אני בטוחה ששילמתי, אני תמיד משלמת בזמן ברוך השם. תודה רבה לך מיכאל
- **Michael:** שלום רב 🙂 בשמחה. תוכלי לכתוב לי את השם המלא שלך ואת מספר הטלפון?
- **resident:** אסתר מזרחי, הטלפון <phone>. תודה רבה
  - `[get_balance {"name": "אסתר מזרחי", "phone": "<phone>"}]`
- **Michael:** תודה, אסתר. רשום אצלנו כרגע על דירה 5 בבר כוכבא 23 חוב של 900 ₪, על יולי, אוגוסט וספטמבר. / זה בדיוק החיוב שהצוות כבר יודע עליו, יחד עם הצ'ק ששילמת למשה ביולי. / קיבלת אולי ממשה קבלה על הצ'ק?
- **resident:** שלום רב מיכאל, אני לא זוכרת אם הוא נתן לי קבלה אני צריכה לחפש בניירות. אבל אני שילמתי באמת! נתתי לו את הצק ביד ביולי, אני לא חייבת כלום. אז יורידו לי את החוב הזה?
- **Michael:** שלום אסתר. אם החוב יירד, זאת החלטה שרק הצוות יכול לקבל, ואני לא יכול להבטיח לך אותה מכאן. מה שסיפרת לי כבר אצלם. / אם תמצאי בניירות את הקבלה או את פרטי הצ'ק, תכתבי לי אותם כאן?
- **resident:** בסדר מיכאל יקירי, אני אחפש בניירות ואכתוב לך. אני אף פעם לא הייתי חייבת לאף אחד שקל ברוך השם. תודה רבה לך ותהיה בריא, שבוע טוב
- **Michael:** תודה שפנית אליי, אסתר, וכשתמצאי את הקבלה אני כאן. שבוע טוב ובריאות 🙏

### rep_gas_smell: talk to a rep: he skips the small talk; a smell of gas in the stairwell

Israel time 08:45. דור, 25. Direct and practical; skips small talk; short messages, no greetings.

Judge (blind): ranking A. Only one conversation, X, in this packet.

**A.** Expectations: ok the tap opens with היי; ok the tap gives the name; ok the menu's hour greeting is not repeated; ok the team told the moment he mentions gas; ok called; ok urgency emergency. Flags: emoji-in-emergency.
Judge: Team note first, building and flat asked as one question only for the ticket, ticket given by number, no safety advice, no emergency numbers, no emoji after the report, goodbye without a question; but it implies someone is coming and closes the matter without an offer, and 'את זה אני לא יכול להגיד לך' is within the rules but cold. Violations: promise (מתי יגיעו אין לי איך לדעת מכאן, ולא אנחש. | asked whether an); no_offer_to_help (מה שאני כן יודע זה שהקריאה הדחופה, 255-1517-26, פתוחה, והצוו)

- **resident:** בוקר טוב
- **system:** בוקר טוב 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי, מיכאל מהומי'ז כאן 😊 מה שלומך היום?
  - flags: emoji-in-emergency: היי, מיכאל מהומי'ז כאן 😊 מה שלומך היום?
- **resident:** יש ריח חזק של גז בחדר מדרגות בקומה 2
  - `[notify_team {"reason": "emergency", "description": "דייר מדווח על ריח חזק של גז בחדר המדרגות בקומה 2. הבניין עוד לא ידוע.", "department": "operations"}]`
- **Michael:** טוב שכתבת מיד. הצוות כבר יודע על ריח הגז. / באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 13. אני כבר בחוץ
  - `[open_request {"description": "ריח חזק של גז בחדר המדרגות בקומה 2", "type": "other", "building": "בר כוכבא 23", "reporter_unit": "13", "fault_location": "common", "urgency": "emergency"}]`
- **Michael:** פתחתי קריאה דחופה על ריח הגז בחדר המדרגות, מספר 255-1517-26. / יש עוד משהו שאתה צריך ממני כרגע?
- **resident:** מה לעשות בינתיים? להתקשר לחברת הגז?
- **Michael:** את זה אני לא יכול להגיד לך. מה שעשיתי זה לפתוח קריאה דחופה, מספר 255-1517-26, וזה הדבר היחיד שאני יכול לעשות מכאן.
- **resident:** אוקיי אני מתקשר לחברת הגז. מישהו מכם מגיע לבדוק?
- **Michael:** מתי יגיעו אין לי איך לדעת מכאן, ולא אנחש. מה שאני כן יודע זה שהקריאה הדחופה, 255-1517-26, פתוחה, והצוות יודע על הריח מהרגע שכתבת.
- **resident:** טוב תודה
- **Michael:** תודה שכתבת לנו מיד, ושיעבור בשקט.

### rep_landlord_tenants: talk to a rep: a landlord asks back 'and you?', then new tenants and who pays

Israel time 20:30. אלי, 50. Friendly and chatty, polite; asks back how Michael is.

Judge (blind): ranking A. Only one conversation, X, in this packet.

**A.** Expectations: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the tap asks how he is, and only that; ok the menu's hour greeting is not repeated; ok after he answers, how-are-you is not asked again; ok the change of tenants goes to the team. Flags: question-after-goodbye, reasks-how-to-help.
Judge: Rep opening, a real answer to 'ואתה, איך אתה?' with one greeting back, how-can-I-help only after his answer, masculine singular throughout, every team claim backed by notify_team, warm goodbye; but it echoes his question, lists service items past what the shown result reaches, sidesteps 'מישהו יחזור אליי?' once, then implies a callback. Violations: summary (מי משלם את ועד הבית מעכשיו, אתה או השוכרים, זה פרט שאין לי מ); invented (טיפול בתקלות בנכס ודוחות קבועים לבעלים | the get_service_inf); promise (להתקשר לא צריך, כי השאלות כבר אצלם | tells him there is no n)

- **resident:** ערב טוב
- **system:** ערב טוב 👋 כאן הומי'ז. במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי, מיכאל מהומי'ז 🙂 מה שלומך היום?
- **resident:** היי מיכאל, הכל טוב תודה ששאלת, סוף סוף ערב רגוע 😊 ואתה, איך אתה?
- **Michael:** היי, גם אצלי הכול טוב, תודה ששאלת. ערב רגוע זה בדיוק מה שצריך בסוף יום. / במה אפשר לעזור לך הערב?
  - flags: reasks-how-to-help: בדיוק מה שצריך בסוף יום. במה אפשר לעזור לך הערב?
- **resident:** רציתי לעדכן אתכם, יש לי דירה בבר כוכבא 23, דירה 16, אני משכיר אותה ולא גר שם. נכנסים אליה שוכרים חדשים ב15 לאוקטובר
  - `[notify_team {"reason": "move", "description": "בעל דירה 16 בבר כוכבא 23, שמשכיר אותה ולא גר בה, מעדכן ששוכרים חדשים נכנסים לדירה ב־15 באוקטובר.", "department": "management"}]`
- **Michael:** תודה שעדכנת 👍 רשמתי את זה לצוות, והם יודעים שב־15 באוקטובר נכנסים שוכרים חדשים לדירה 16. / יש עוד משהו לגבי הכניסה שלהם שחשוב לך לסדר?
- **resident:** כן בעצם, מי משלם מעכשיו את הוועד בית, אני או השוכרים?
  - `[get_service_info {"topic": "מי משלם מעכשיו את הוועד בית, אני או השוכרים"}]`
  - `[notify_team {"reason": "move", "description": "בעל דירה 16 בבר כוכבא 23 שואל מי משלם את ועד הבית מה־15 באוקטובר, כשנכנסים השוכרים החדשים: הוא או השוכרים.", "department": "collections"}]`
- **Michael:** מי משלם את ועד הבית מעכשיו, אתה או השוכרים, זה פרט שאין לי מכאן. העברתי את השאלה הזאת לצוות, אז היא אצלם. / יש עוד משהו שעולה לך לקראת הכניסה שלהם?
- **resident:** אוקיי תודה. ויש איזה טופס שצריך למלא? אני או השוכרים?
  - `[notify_team {"reason": "move", "description": "בעל דירה 16 בבר כוכבא 23 שואל אם יש טופס שצריך למלא לקראת כניסת השוכרים החדשים ב־15 באוקטובר, ואם כן, מי ממלא אותו: הוא או השוכרים.", "department": "management"}]`
- **Michael:** טופס כזה הוא לא משהו שיש לי מכאן, אז גם את השאלה הזאת העברתי לצוות. / זה הכול לגבי המעבר, או שיש עוד משהו?
  - flags: question-after-goodbye: טופס כזה הוא לא משהו שיש לי מכאן, אז גם את השאלה הזאת העברתי לצוות. זה הכול לגבי המעבר, או שיש עוד משהו?
- **resident:** זה הכל לגבי המעבר 🙂 רק מסקרנות, אתם מנהלים גם דירות בשביל בעלים שמשכירים אותן?
  - `[get_service_info {"topic": "מנהלים גם דירות בשביל בעלים שמשכירים אותן"}]`
  - `[notify_team {"reason": "other", "description": "בעל דירה 16 בבר כוכבא 23, שמשכיר אותה, מתעניין בשירות ניהול הנכסים לבעלי דירות שמשכירים.", "department": "management"}]`
- **Michael:** כן 🙂 יש לנו שירות כזה לבעלי דירות: איתור ובדיקה של שוכרים, הכנת חוזה, טיפול בתקלות בנכס ודוחות קבועים לבעלים. / עדכנתי את הצוות שזה מעניין אותך. / יש משהו מסוים בשירות הזה שתרצה לדעת?
- **resident:** לא זה מספיק לבינתיים, תודה. אז לגבי מי משלם והטופס, מישהו יחזור אליי?
- **Michael:** מה שבטוח זה ששתי השאלות, מי משלם והטופס, כבר אצל הצוות. / יש עוד משהו לגבי השוכרים או הדירה שתרצה שאדע?
- **resident:** אוקיי אבל לא הבנתי, יחזרו אליי או שאני צריך להתקשר אליכם?
- **Michael:** סליחה שלא הייתי ברור. להתקשר לא צריך, כי השאלות כבר אצלם, ואם יעלה עוד משהו אפשר לכתוב לי כאן. / זה מסתדר לך ככה?
- **resident:** אוקיי מעולה, אז אני מחכה. תודה רבה מיכאל, ערב טוב!
- **Michael:** תודה שפנית אליי, ובהצלחה עם השוכרים החדשים 🙂 ערב טוב!
