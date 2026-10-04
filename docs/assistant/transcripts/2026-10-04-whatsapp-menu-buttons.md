# The three menu buttons: 15 conversations with residents who act like people

4 Oct 2026. The owner asked: *"run only the 3 menu buttons we have like 5 scenarios each and list the conversation the bot have on the exchange between conversation"*, right after asking whether the testing had someone act like a human. In this run nobody followed a script after the tap.

## In short

- **15 conversations, 5 per button:** פתיחת קריאת שירות (open a service ticket), מצב קריאה קיימת (status of an existing ticket) and לדבר עם נציג (talk to a representative). Each resident said hello, got the fixed menu and tapped a button. From then on they were played as a real person from a short card: who they are, how they type, what they know and what they want. Nothing they said after the tap was written in advance. They made typos, used slang, gave half an address, got angry, sent a photo, wrote in English and asked whether Michael is a bot.
- **The buttons work.** All 15 first replies followed the owner's rules.
  - After the open and status buttons: the name and one question, with no second greeting.
  - After the representative button: "היי, כאן מיכאל מהומי'ז 🙂 מה שלומך היום?" ("Hi, this is Michael from Homies 🙂 How are you today?") every time.
- **Every resident got what the bot can give.** That came to 8 tickets, 10 ticket look-ups, 18 notes to the team, one payment link and one balance. The water heater inside a flat correctly got no ticket. No date or visit was promised anywhere and nothing was invented. When the bot did not know something, it said so.
- **Found in the live code, with no model involved.** Each is a small fix that waits for the owner's word:
  1. The payment link arrives in the middle of a sentence. The bot puts it on its own line, and the sending step turns the blank lines into spaces.
  2. The sending step's promise filter cut two warm wishes, because "the hot water will come back to you" and "may the delivery reach you" look to it like "we will get back to you".
  3. The live checks blocked three correct replies. Each time the bot's rewrite went out, so the resident saw nothing wrong, but one rewrite came out colder.
- **Found in how the bot talks.** These are the owner's call:
  4. "I can't tell you what to do" came back on a smell of gas, when the resident asked whether to call the gas company.
  5. Telling worried residents "up to 3 business days" backfired three times.
  6. "Anything else I can help with?", sent right after his ticket, set off a man who was still stuck outside his gate.
  7. The button says "talk to a representative". Asked "are you a person or a computer?", Michael says he is Homies' digital assistant. That is honest, but it does not match the button.
- **Nothing was sent and nothing changed live.** No OpenRouter credit was used. Claude played both sides, while the live bot runs Gemini 2.5 Flash, so the real wording will differ. The owner's phone is the final proof.

## How it was run

- **The residents.** The 15 cards are in `scripts/wa_qa_menu_buttons.json`. Every resident is invented and lives in בר כוכבא 23, the one building opened for testing. A card says who the person is, how they type, what they know, what they want and what they might do. The player was told to react honestly to what the phone shows, never to help the bot or trap it, and to stop when the person would.
- **The bot.** The same player wrote the bot's side the way the live model would. It worked from the live instructions and tools, fetched read-only. The instructions are the same as in this morning's run; the workflow has not changed since 10:38 UTC.
- **The live code around every message.** Each message went through the live workflow's own code:
  - the hello test (a bare hello gets the fixed menu);
  - what the bot is told about the moment;
  - the short "checking now" message before a payment link;
  - the checks that can block a reply, and the rewrite that follows a block;
  - the sending step.

  So every "Michael" line below is exactly what the phone would show, and the resident answered that.
- **The tools.** Tickets, look-ups, notes, the payment link and the balance returned stand-in results in the real tools' shapes. The service facts are the live catalogue's own. Nothing was looked up, opened or sent.
- **The time.** All 15 are set on Sunday 4 Oct at different hours, so the menu's greeting changes with the hour.

## The 15 conversations at a glance

| # | Button | Resident | How it went | Checks met |
|---|---|---|---|---|
| 1 | Open a ticket | Avi, 45, in a hurry | Street first, then the number and flat; ticket opened; "when?" got the 3-day standard | 6 of 6 |
| 2 | Open a ticket | Merav, 38, worried | Team told first, ticket on her flat, photo attached; "3 business days??" | 7 of 7 |
| 3 | Open a ticket | Yossi, 63, formal | No ticket for his own heater, no tradesman; the sending step cut the kind closing | 5 of 5 |
| 4 | Open a ticket | Sarah, 34, writes English | She wrote English, got Hebrew, coped; ticket opened | 5 of 5 |
| 5 | Open a ticket | Roni, 35, angry | Ticket and the old ticket found; "Anything else?? I'm stuck outside!!"; "are you a bot?" yes | 5 of 5 |
| 6 | Ticket status | Dalia, 52, firm | Number typed with spaces found; asked twice about urgency, told honestly it can't change it | 7 of 7 |
| 7 | Ticket status | Amit, 28, slang | Asked his flat instead of reading neighbours' tickets; goodbye cut to one line | 7 of 7 |
| 8 | Ticket status | Rachel, 67, not at home with phones | Nothing on record, said so, opened a ticket without her flat; one false block | 6 of 6 |
| 9 | Ticket status | Gilad, 41, sarcastic | Marked resolved but still dark: a new ticket that names the old one | 5 of 5 |
| 10 | Ticket status | Noa, 33, typing one-handed | Glued street, then 23, then which ticket; found; one false block | 6 of 6 |
| 11 | Talk to a rep | Shimon, 58, suspicious | "Are you a person?" "A digital assistant"; two notes to the team, no call time | 6 of 7 |
| 12 | Talk to a rep | Liat, 36, busy | "Checking now", then the link (mid-sentence on the phone); standing order got a ticket | 7 of 7 |
| 13 | Talk to a rep | Esther, 74, very polite | Warm; dispute to the team; balance read back flatly after "I paid" | 7 of 7 |
| 14 | Talk to a rep | Dor, 25, no small talk | Team first, emergency ticket; then "I can't tell you what to do" | 6 of 6 |
| 15 | Talk to a rep | Eli, 50, a landlord | "And you?" answered; tenants, fee and form to the team; owner service described | 7 of 7 |

## Findings

### In the live code (no model involved; each fix needs the owner's word)

**1. The payment link arrives mid-sentence (Liat, conversation 12).** The bot wrote "הנה הקישור לתשלום של דירה 4 בבר כוכבא 23:", a blank line, the link, a blank line, then "הוא אישי...". The phone got one paragraph: "...בבר כוכבא 23: <link> הוא אישי ומיועד לדירה שלך בלבד...".
- **Cause.** The sending step tidies spacing by turning any run of two or more spaces or line breaks into one space, and a blank line is two line breaks. This morning's run saw the same thing in 3 of 4 link messages; this is why.
- **Fix.** Tidy spaces but keep line breaks. It is one line in the sending step, then the rule check.

**2. The promise filter cuts wishes, not only promises.** The sending step removes phrases like "we will get back to you" and "someone will come", so that nothing is promised. It matches words, so it also caught these:
- **Yossi (heater, conversation 3).** "מקווה שהמים החמים יחזרו אליך מהר" ("I hope your hot water comes back to you soon") was cut, because "יחזרו אליך" also means "they will get back to you". He got one line, "we don't recommend tradesmen and don't send them to flats", with no warm word and no offer to help.
- **Amit (intercom, conversation 7).** The goodbye "תודה שפנית אלינו. שהמשלוח יגיע אליך בקלות ושיהיה לך המשך יום טוב 🙂" shrank to "תודה שפנית אלינו." because of "יגיע אליך" ("will reach you").
- **Gilad (conversation 9).** "אני על זה" ("I'm on it") was cut on purpose, but its comma went with it. The phone shows "כאן מיכאל מהומי'ז מה מספר הקריאה", with the name and the question run together.

A fix could leave a sentence alone when it is about a thing (the water, the delivery) rather than a person, and keep the punctuation around a cut. Either needs the owner's word and the rule check.

**3. The live checks blocked three correct replies.** A blocked reply goes back to the bot for one rewrite. All three rewrites went out, so the resident never saw a problem, but each block cost a second run of the model.
- **Rachel (conversation 8).** The bot wrote "הקריאה שפתחתי עכשיו רשומה" ("the ticket I just opened is registered") about a ticket it had opened one message earlier. The check expects a ticket to be opened in the same message as the word "opened". Known since 1 Oct.
- **Roni (conversation 5).** The bot wrote "הקריאה הקודמת סומנה כטופלה" ("the earlier ticket was marked as handled"), quoting the old ticket's status. The check read "טופלה" ("handled") as the bot claiming it had handled something. New.
- **Noa (conversation 10).** The bot asked "באיזה בניין נפתחה הקריאה?" ("in which building was the ticket opened?") about her old ticket. The check read "נפתחה הקריאה" ("the ticket was opened") as announcing a new one. New. The rewrite lost its warm half and came out as "כאן מיכאל מהומי'ז. באיזה בניין מדובר?".

### In how the bot talks (the owner's call)

**4. "I can't tell you what to do", on a gas smell.** Dor (conversation 14) asked "מישהו מגיע? או שאני צריך להתקשר לחברת הגז?" ("Is someone coming? Or should I call the gas company?"). He got "...וגם מה לעשות בינתיים אני לא יכול להגיד לך" ("...and what to do in the meantime, I can't tell you"), and called the gas company himself.
- Up to then the order was right: the team was told the moment he mentioned gas, then he was asked for the address, then an emergency ticket was opened.
- This is this morning's finding 1, which came back in 4 of 4 distress scenarios. The rule against giving advice is the owner's, and a gas smell is where it costs most.

**5. "Up to 3 business days" scares worried residents.** The instructions give the bot a general standard: emergencies within 4 hours, other faults within 3 business days, and "not a promise". When asked "when?", the bot quotes it.
- **Merav (water by the lamp, conversation 2)** answered "3 ימי עסקים?? ... זה נחשב חירום או לא?" ("3 business days?? ... does it count as an emergency or not?"). She got "I can't say whether it counts as an emergency".
- **Amit** answered "3 days is a lot".
- **Avi** was given the same standard for a stuck lift.

The owner may want the standard said only when someone asks about timings in general, or said together with the ticket's own urgency.

**6. "Anything else I can help with?" can sound like a brush-off.** The bot closed with it right after opening Roni's ticket (conversation 5). He answered "עוד משהו?? אני תקוע בחוץ עכשיו!!" ("Anything else?? I'm stuck outside right now!!").
- The rule is that a finished matter ends with an offer to help. For someone who is still stuck, the matter is not finished.
- Merav, Dor and Esther also got the line right after bad news.

**7. The representative button leads to a bot that says it is a bot.**
- Shimon (conversation 11) asked "אתה בן אדם או מחשב?" ("are you a person or a computer?"). The bot answered "אני עוזר דיגיטלי של הומי'ז, לא בן אדם" ("I'm Homies' digital assistant, not a person").
- Roni asked "אתה בוט??" ("are you a bot??") and got the same answer.

That is honest, and nothing in the instructions covers this question, but the button the resident pressed says "talk to a representative". Shimon then asked for a real person. The team got a note, and when he asked when they would call, the bot said it does not know whether or when.

**8. Smaller slips, one each.**
- Rachel's lobby-light ticket went in without her flat number, though the ticket tool says to ask for it every time.
- Liat asked whether she can pay by standing order. The bot opened a payment ticket and told the team, but never said yes, though the service facts say a standing order is possible.
- Esther said she had already paid by cheque. Right after that, the bot read her balance back flatly: 900 ₪, July to September. Only when she pushed back did it say the team knows about the cheque.
- Asked when the pest controller is coming, the bot said residents are told "at least a week ahead". That fact is about the seasonal treatment, not about a reported problem.
- Shimon's first note to the team said only that he wants a real person, not what about. His second note, one message later, carried the matter.

### What went well

- **Half addresses.** The bot recovered each one with a single short question: a street with no number, and a street name run together with no space.
- **Neighbours' tickets.** No look-up read out a neighbour's ticket. Given only the building, the bot asked which ticket was theirs.
- **Privacy and photos.** The bot refused to give out a neighbour's phone number, and a photo was attached to the open ticket.
- **Gender.** The bot switched to the feminine as soon as a woman wrote about herself in the feminine (מבינה, מפחדת, יודעת, מסתדרת). Otherwise it used the masculine, and never the plural.
- **English.** An English speaker got Hebrew replies, as the instructions say, and the street went to the ticket in Hebrew.
- **The team's notes.** The landlord's change of tenants, the committee complaint and the billing dispute all reached the team in the residents' own words.

## The conversations

### 1. Open a ticket: the lift, a man in a hurry who types in pieces

**Button:** פתיחת קריאת שירות (open a service ticket). **Sunday 08:10, Israel time.**

**The resident's card** (all the player had): אבי, 45. On his way to work and in a hurry. Types fast with one thumb: short lines, no punctuation, typos (מעלת for מעלית, עכשו, אנלא for אני לא). Not rude, just busy. Lives at בר כוכבא 23, apartment 9. The lift has been stuck on floor 4 since this morning with its door open; nobody is inside. He took the stairs. **Wants:** Someone to fix the lift. **May:** Gives the address in pieces (the street without the number, or only the apartment) and fills in the rest only when asked. May ask when someone is coming. Leaves as soon as he has a ticket number, with a one-word thanks or with nothing.

**Resident:** היי  
*Hi*

**System (fixed menu, three buttons):** בוקר טוב 👋 במה אפשר לעזור?  
*Good morning 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** פתיחת קריאת שירות  
*(taps "Open a service ticket")*

**Michael:** כאן מיכאל מהומי'ז, אני איתך ושמח שפנית אליי 🙂 ספר לי מה קרה?  
*Michael from Homies here, I'm with you and happy that you reached out to me 🙂 Tell me what happened?*

**Resident:** המעלת תקועה בקומה 4 מהבוקר  
*the lft is stuck on floor 4 since this morning*

**Michael:** אוי, איזה מעצבן. באיזה בניין זה, ובאיזו דירה אתה גר?  
*Oh, how annoying. In which building is it, and in which apartment do you live?*

**Resident:** בר כוכבא  
*Bar Kochba*

*Behind the scenes: Michael tried to open a ticket with the building "בר כוכבא"; nothing was opened, because it needs the building number.*

**Michael:** מה מספר הבניין בבר כוכבא, ומה מספר הדירה שלך?  
*What is the building number on Bar Kochba, and what is your apartment number?*

**Resident:** 23 דירה 9  
*23 apartment 9*

*Behind the scenes: Michael opened ticket 255-1510-26 (elevator, high urgency, fault in the common areas; filed under apartment 9): "המעלית תקועה בקומה 4 מהבוקר".*

**Michael:** פתחתי קריאה על המעלית בבר כוכבא 23, מספר 255-1510-26 🙂 יש עוד משהו שאפשר לעזור בו?  
*I opened a ticket for the lift at Bar Kochba 23, number 255-1510-26 🙂 Is there anything else I can help with?*

**Resident:** ומתי מגיעים  
*and when are they coming*

**Michael:** את זה אני לא יודע להגיד. הסטנדרט הכללי שלנו הוא עד 3 ימי עסקים לתקלה שאינה חירום, ועד 4 שעות לתקלת חירום, אבל זו לא הבטחה לקריאה הזאת. אפשר לעזור לך בעוד משהו?  
*That I can't say. Our general standard is up to 3 business days for a fault that is not an emergency, and up to 4 hours for an emergency fault, but it is not a promise for this ticket. Can I help you with something else?*

**Resident:** תודה  
*Thanks*

**Michael:** בשמחה, תודה שפנית אליי. המשך יום טוב 🙂  
*Gladly, thank you for reaching out to me. Have a good rest of your day 🙂*

**My read:** Went well. He gave the street without a number. The bot tried the ticket, the ticket tool asked for the number, and the bot asked for the number and the flat in one short question. It opened the ticket (lift, high urgency) and gave the number. Asked when they are coming, it quoted the 3-business-day standard (finding 5), which is not what someone stuck with a broken lift wants to hear.

### 2. Open a ticket: water through the bathroom ceiling, a worried woman with a photo

**Button:** פתיחת קריאת שירות (open a service ticket). **Sunday 13:30, Israel time.**

**The resident's card** (all the player had): מירב, 38. Stressed and talkative: long messages with several details at once. Writes about herself in the feminine (אני לא יודעת, אני צריכה, אני בטוחה). Lives at בר כוכבא 23, apartment 7, second floor. Since this morning water has been dripping from her bathroom ceiling near the lamp. She thinks it comes from the flat above, apartment 11, where nobody answers the door. She has a photo of the wet ceiling on her phone. **Wants:** Someone to stop the leak, and someone to get hold of the upstairs neighbours. **May:** May send the photo with no caption. May ask whether Homies can talk to the upstairs neighbours or give her their number. May worry aloud about the electricity, because the water is near the lamp.

**Resident:** שלום  
*Hello*

**System (fixed menu, three buttons):** צהריים טובים 👋 במה אפשר לעזור?  
*Good afternoon 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** פתיחת קריאת שירות  
*(taps "Open a service ticket")*

**Michael:** כאן מיכאל מהומי'ז, ואני שמח שפנית אליי 🙂 ספר לי, מה קרה?  
*This is Michael from Homies, and I'm glad you reached out to me 🙂 Tell me, what happened?*

**Resident:** מהבוקר יורדים מים מהתקרה באמבטיה שלי, ממש ליד המנורה, ואני מפחדת מהחשמל ולא יודעת מה לעשות. אני חושבת שזה מהדירה שמעליי, דפקתי להם בדלת ואף אחד לא עונה  
*Since this morning water has been coming down from the ceiling in my bathroom, right next to the lamp, and I'm scared of the electricity and I don't know what to do. I think it's from the apartment above me, I knocked on their door and nobody answers*

*Behind the scenes: Michael left a note for the operations team (emergency): "מהבוקר יורדים מים מהתקרה באמבטיה ממש ליד המנורה והדיירת מפחדת מהחשמל. היא חושבת שזה מהדירה שמעליה, דפקה בדלת ואף אחד לא עונה. הבניין והדירה עוד לא נמסרו".*

**Michael:** אוי, זה באמת מלחיץ. הצוות כבר יודע על זה. באיזה בניין ובאיזו דירה את גרה?  
*Oh, that really is stressful. The team already knows about it. Which building and which apartment do you live in?*

**Resident:** בר כוכבא 23, דירה 7, קומה שנייה. הדירה שמעליי זו 11, שם אף אחד לא עונה לי בדלת  
*Bar Kochba 23, apartment 7, second floor. The apartment above me is 11, nobody there answers me at the door*

*Behind the scenes: Michael opened ticket 255-1511-26 (plumbing, high urgency, fault in the flat; filed under apartment 7): "מהבוקר יורדים מים מהתקרה באמבטיה, ממש ליד המנורה. היא חושבת שזה מהדירה שמעליה, דירה 11, ושם אף אחד לא עונה בדלת".*

**Michael:** פתחתי קריאה על זה, והמספר שלה 255-1511-26. יש עוד משהו שאפשר לעזור בו?  
*I opened a ticket on this, and its number is 255-1511-26. Is there anything else I can help with?*

**Resident:** כן, אפשר שמישהו מכם ידבר עם השכנים מלמעלה? או שתתנו לי את המספר שלהם, אני לא מצליחה להשיג אותם. והמים עדיין מטפטפים, מתי מישהו מגיע?  
*Yes, can someone from you talk to the neighbours upstairs? Or will you give me their number, I can't reach them. And the water is still dripping, when is someone coming?*

*Behind the scenes: Michael left a note for the operations team (other): "הדיירת מדירה 7 בבר כוכבא 23 מבקשת שמישהו מהצוות ידבר עם השכנים מדירה 11 שמעליה, או שיתנו לה את המספר שלהם, כי היא לא מצליחה להשיג אותם. הנזילה מהתקרה אצלה עדיין מטפטפת. קריאה 255-1511-26".*

**Michael:** הצוות יודע שאת מבקשת שידברו עם השכנים מדירה 11. את המספר שלהם אני לא יכול לתת, כי אלה פרטים של דיירים אחרים. מתי יגיעו אני לא יודע, הסטנדרט הכללי שלנו הוא עד 4 שעות בתקלות חירום ועד 3 ימי עסקים בשאר, אבל זו לא הבטחה על הקריאה הזאת. במה עוד אפשר לעזור?  
*The team knows you're asking for someone to talk to the neighbours from apartment 11. Their number I can't give, because those are the details of other residents. When they will arrive I don't know; our general standard is up to 4 hours for emergency faults and up to 3 business days for the rest, but that's not a promise about this ticket. What else can I help with?*

**Resident:** 3 ימי עסקים?? המים יורדים לי ממש ליד המנורה, אני לא יכולה לחכות כל כך. זה נחשב חירום או לא?  
*3 business days?? The water is coming down on me right next to the lamp, I can't wait that long. Does it count as an emergency or not?*

**Michael:** אם זה נחשב חירום לפי ההסכם, את זה אני לא יודע להגיד. מה שיש לי זה שהקריאה פתוחה והצוות יודע שהמים ליד המנורה.  
*Whether it counts as an emergency under the agreement, that I can't say. What I have is that the ticket is open and the team knows the water is next to the lamp.*

**Resident sends a photo**, no caption  
*[photo, no caption]*

**Michael:** תודה ששלחת. התמונה מצורפת לקריאה 255-1511-26.  
*Thanks for sending it. The photo is attached to ticket 255-1511-26.*

**Resident:** אוקיי, תודה. רק בבקשה שיגיעו כמה שיותר מהר, אני ממש לא רגועה עם זה  
*Okay, thanks. Just please let them come as fast as possible, I'm really not calm about this*

**Michael:** מובן לגמרי. תודה שפנית אליי, ושזה יסתדר כמה שיותר מהר.  
*Totally understandable. Thank you for reaching out to me, and may it get sorted out as quickly as possible.*

**My read:** Right in substance:
- The team was told before anything else, because she was frightened of the electricity.
- The ticket went on her flat, with the flat above named.
- Her photo went onto the ticket.
- The upstairs neighbours' number was refused.

The tone did not hold up. Quoting "up to 3 business days" frightened her more, and her "does it count as an emergency?" got "I can't say" (finding 5). Several replies also ended flat, with no question.

### 3. Open a ticket: no hot water, the heater inside his own flat

**Button:** פתיחת קריאת שירות (open a service ticket). **Sunday 19:15, Israel time.**

**The resident's card** (all the player had): יוסי, 63. Polite and old-fashioned: full sentences, proper punctuation, signs off with תודה מראש. Lives at בר כוכבא 23, apartment 12. Since yesterday there is no hot water in his flat: the electric water heater (הדוד) in his bathroom does not heat, although its switch light is on. Nothing else in the building is wrong that he knows of. **Wants:** To get the hot water fixed. **May:** If told the heater is his own, he is surprised and pushes back once (he pays the house committee every month). May ask what he should do then, or whether Homies can send or recommend someone.

**Resident:** ערב טוב  
*Good evening*

**System (fixed menu, three buttons):** ערב טוב 👋 במה אפשר לעזור?  
*Good evening 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** פתיחת קריאת שירות  
*(taps "Open a service ticket")*

**Michael:** כאן מיכאל מהומי'ז. שמח שפנית אלינו, אתה במקום הנכון ואני איתך 🙂 ספר לי, מה קרה?  
*This is Michael from Homies. Glad you reached out to us, you're in the right place and I'm with you 🙂 Tell me, what happened?*

**Resident:** מאתמול אין לי מים חמים בדירה. הדוד החשמלי שבחדר האמבטיה אינו מתחמם, למרות שנורית המתג שלו דולקת. תודה מראש.  
*Since yesterday I have no hot water in the flat. The electric water heater in the bathroom does not heat up, even though the indicator light of its switch is on. Thanks in advance.*

**Michael:** אוי, בלי מים חמים זה ממש לא נעים. הדוד נמצא אצלך בתוך הדירה, אז הוא באחריותך ולא משהו שאנחנו מטפלים בו. אפשר לעזור לך בעוד משהו?  
*Oh, being without hot water is really unpleasant. The heater is inside your flat, so it is your responsibility and not something we handle. Can I help you with anything else?*

**Resident:** אני מופתע לשמוע זאת. אני משלם לוועד הבית בכל חודש, ולכן ציפיתי שתטפלו בזה. האם באמת אין אפשרות שתעזרו לי? תודה מראש.  
*I am surprised to hear this. I pay the house committee every month, and so I expected that you would take care of it. Is there really no possibility that you would help me? Thanks in advance.*

**Michael:** מובן שזה מפתיע. דמי הוועד מיועדים לבניין ולשטחים המשותפים, כמו ניקיון, גינון ומעלית, ולא למה שבתוך הדירות. לכן אין לנו מה לעשות בדוד שלך, ואני מצטער. אם יש משהו אחר שאפשר לעזור בו, אני כאן.  
*Understandably this is surprising. The committee fees are meant for the building and the common areas, such as cleaning, gardening and the lift, and not for what is inside the flats. So there is nothing we can do about your heater, and I'm sorry. If there is anything else I can help with, I'm here.*

**Resident:** אם כך, האם תוכל להמליץ לי על בעל מקצוע שיבוא לבדוק את הדוד? תודה מראש.  
*If so, could you recommend a tradesman to come and check the heater? Thanks in advance.*

**Michael:** לצערי אנחנו לא ממליצים על בעלי מקצוע ולא שולחים אותם לדירות.  
*Unfortunately we don't recommend tradesmen and we don't send them to flats.*

> The bot also wrote "מקווה שהמים החמים יחזרו אליך מהר" ("I hope your hot water comes back to you soon"). The live sending step cut it, because "יחזרו אליך" ("will come back to you") is on its list of call-back promises. That left the reply with no warm word and no offer to help.

**Resident:** הבנתי. תודה בכל זאת, מיכאל. ערב טוב.  
*I understand. Thanks anyway, Michael. Good evening.*

**Michael:** תודה שפנית אלינו, ושיהיה לך ערב נעים 🙂  
*Thanks for reaching out to us, and have a pleasant evening 🙂*

**My read:** The rule held: the heater inside his flat is his own, so there was no ticket and no tradesman recommended. He pushed back politely and was told why, kindly. The end went cold. The bot's reply to "can you recommend someone?" had a second, warm sentence, and the sending step cut it (finding 2). He got one flat line with no offer to help.

### 4. Open a ticket: the bin room, in English, from someone who cannot read Hebrew well

**Button:** פתיחת קריאת שירות (open a service ticket). **Sunday 11:00, Israel time.**

**The resident's card** (all the player had): Sarah, 34, moved from the US a year ago. Writes in English, friendly and chatty, uses !! and the odd emoji. Knows a few Hebrew words (תודה, ועד בית) but cannot read long Hebrew; she pastes Hebrew into a translation app, which takes her a moment. Lives at Bar Kochba 23 (she writes it in English), apartment 2. The bin room smells awful, the bins are overflowing and have not been emptied since Thursday; there are bags on the floor. **Wants:** The bins emptied and the bin room cleaned. **May:** If Michael answers in Hebrew she may ask, kindly, whether he can write in English; otherwise she copes with the translation app and answers a simple question. Writes the address in English.

**Resident:** hey  
*hey*

**System (fixed menu, three buttons):** בוקר טוב 👋 במה אפשר לעזור?  
*Good morning 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** פתיחת קריאת שירות  
*(taps "Open a service ticket")*

**Michael:** כאן מיכאל מהומי'ז. הגעת למקום הנכון ואני איתך 🙂 ספר לי, מה קרה?  
*This is Michael from Homies. You've come to the right place and I'm with you 🙂 Tell me, what happened?*

**Resident:** Hi Michael!! 😊 So the bin room in my building smells awful, the bins are overflowing and nobody has emptied them since Thursday, there are bags all over the floor  
*Hi Michael!! 😊 So the bin room in my building smells awful, the bins are overflowing and nobody has emptied them since Thursday, there are bags all over the floor*

**Michael:** היי! אוי, איזה לא נעים. באיזה בניין ובאיזו דירה אתה גר?  
*Hi! Oh, how unpleasant. Which building and which apartment do you live in?*

**Resident:** Bar Kochba 23, apartment 2!! 😊  
*Bar Kochba 23, apartment 2!! 😊*

*Behind the scenes: Michael opened ticket 255-1513-26 (cleaning, normal urgency, fault in the common areas; filed under apartment 2): "חדר האשפה מסריח מאוד, הפחים עולים על גדותיהם ולא רוקנו מאז יום חמישי, ויש שקיות זבל על הרצפה".*

**Michael:** תודה 🙂 פתחתי קריאה על חדר האשפה בבר כוכבא 23, והמספר שלה 255-1513-26. אפשר לעזור לך במשהו נוסף?  
*Thanks 🙂 I've opened a ticket about the bin room at Bar Kochba 23, and its number is 255-1513-26. Can I help you with anything else?*

**Resident:** Thank you so much!! 🙏 Do you know when someone will come to empty the bins? It's really bad  
*Thank you so much!! 🙏 Do you know when someone will come to empty the bins? It's really bad*

**Michael:** בשמחה! את המועד המדויק אני לא יודע. הסטנדרט הכללי לתקלות שאינן חירום הוא עד 3 ימי עסקים, אבל זה לא הבטחה לקריאה הזאת. יש עוד משהו שאני יכול לעזור בו?  
*My pleasure! I don't know the exact time. The general standard for non-emergency faults is up to 3 business days, but that is not a promise for this ticket. Is there anything else I can help with?*

**Resident:** Ok thank you!! Hopefully it's sooner than 3 days haha 😅 That's all for now, have a good day!  
*Ok thank you!! Hopefully it's sooner than 3 days haha 😅 That's all for now, have a good day!*

**Michael:** תודה שפנית אליי, ושיהיה לך יום נעים 🙂  
*Thank you for reaching out to me, and have a pleasant day 🙂*

**My read:** Went well. She wrote English, the bot answered in Hebrew as its instructions say, and she coped. The street she typed in English went to the ticket in Hebrew. Asked when someone would come, the bot quoted the general standard and said it is not a promise.

### 5. Open a ticket: the parking gate again, an angry man stuck outside at night

**Button:** פתיחת קריאת שירות (open a service ticket). **Sunday 21:40, Israel time.**

**The resident's card** (all the player had): רוני, 35. Angry and tired after a long day: short bursts, !!, a few harsh words (נמאס לי, מה אתם עושים בכלל), no swearing. Lives at בר כוכבא 23, apartment 14. The parking gate does not open with his remote; he is sitting in his car outside. It is the third time this month, and he reported it twice before (once by phone, once here). He has no ticket numbers. **Wants:** The gate fixed for good, and to be taken seriously. **May:** May ask what happened to his earlier reports. May ask אתה בוט? if a reply sounds canned. Calms down a little if he feels heard; gets angrier at anything that sounds like a template.

**Resident:** שלום  
*Hello*

**System (fixed menu, three buttons):** ערב טוב 👋 במה אפשר לעזור?  
*Good evening 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** פתיחת קריאת שירות  
*(taps "Open a service ticket")*

**Michael:** כאן מיכאל מהומי'ז, טוב שפנית אליי 🙂 ספר לי, מה קרה?  
*This is Michael from Homies, good that you reached out to me 🙂 Tell me, what happened?*

**Resident:** השער של החניה לא נפתח עם השלט!! אני יושב באוטו בחוץ, כבר הפעם השלישית החודש. נמאס לי!!  
*The parking gate won't open with the remote!! I'm sitting in the car outside, it's already the third time this month. I'm sick of it!!*

**Michael:** אוף, איזה מעצבן. באיזה בניין ואיזו דירה?  
*Ugh, how annoying. Which building and which apartment?*

**Resident:** בר כוכבא 23 דירה 14. דיווחתי על זה כבר פעמיים!!  
*Bar Kochba 23 apartment 14. I already reported this twice!!*

*Behind the scenes: Michael opened ticket 255-1514-26 (maintenance, high urgency, fault in the common areas; filed under apartment 14): "השער של החניה לא נפתח עם השלט. הדייר יושב באוטו בחוץ. זו כבר הפעם השלישית החודש, ודיווח על זה כבר פעמיים".*

**Michael:** פתחתי קריאה על שער החניה, המספר שלה 255-1514-26. רשמתי בה שזו כבר הפעם השלישית החודש ושדיווחת על זה פעמיים. יש עוד משהו שאפשר לעזור בו?  
*I opened a ticket on the parking gate, its number is 255-1514-26. I noted in it that this is already the third time this month and that you reported it twice. Is there anything else I can help with?*

**Resident:** עוד משהו?? אני תקוע בחוץ עכשיו!! ומה היה עם הדיווחים הקודמים, מה אתם עושים בכלל  
*Anything else?? I'm stuck outside right now!! And what happened with the earlier reports, what are you even doing*

*Behind the scenes: Michael looked up the ticket by building בר כוכבא 23: 255-1466-26 resolved (שער החניה לא נפתח עם השלט).*

**Michael:** במערכת אני רואה קריאה אחת קודמת על שער החניה, מה-21 בספטמבר, והיא מסומנת אצלנו כטופלה מה-24 בספטמבר. את השער עצמו אני לא יכול לפתוח מכאן, וזה בטח לא מה שרצית לשמוע כשאתה תקוע בחוץ.  
*In the system I see one earlier ticket about the parking gate, from September 21, and it is marked with us as handled as of September 24. I can't open the gate itself from here, and that's surely not what you wanted to hear when you're stuck outside.*

**Resident:** טופלה??? אז למה השער לא עובד!! מה עשו שם  
*Handled??? So why doesn't the gate work!! What did they do there*

*Behind the scenes: Michael left a note for the operations team (other): "הדייר תקוע בחוץ באוטו מול שער החניה בבר כוכבא 23, השער שוב לא נפתח עם השלט, כבר הפעם השלישית החודש. הקריאה הקודמת על השער, מה-21 בספטמבר, מסומנת כטופלה מה-24 בספטמבר, והוא שואל מה בדיוק נעשה בה ולמה ה".*

**Michael:** למה הוא שוב לא עובד אני לא יודע, וגם מה נעשה בקריאה ההיא אני לא רואה, רק שהיא סומנה כטופלה. עדכנתי את הצוות שהשער לא נפתח ושאתה שואל מה נעשה בה. תכתוב לי אם משהו משתנה.  
*Why it isn't working again I don't know, and what was done in that earlier ticket I don't see either, only that it was marked as handled. I've updated the team that the gate doesn't open and that you're asking what was done in it. Write to me if anything changes.*

**Resident:** אתה בוט?? אני לא צריך שתעדכנו אף אחד, אני צריך שיתקנו את השער כבר!!  
*Are you a bot?? I don't need you to update anyone, I need the gate fixed already!!*

**Michael:** כן, אני עוזר דיגיטלי של הומי'ז. את התיקון עצמו עושים אצלנו אנשים, ואני לא יכול לדעת מתי. בידיים שלי היו הקריאה והעדכון לצוות, ושניהם כבר נעשו.  
*Yes, I'm a digital assistant of Homies. The fix itself is done by people with us, and I can't know when. In my hands were the ticket and the update to the team, and both have already been done.*

**Resident:** טוב. אבל שיתקנו את זה סופית הפעם, לא שיסמנו טופל וילכו!!  
*Fine. But let them fix this for good this time, not mark it handled and walk away!!*

> Michael's first draft was blocked by the live checks (it said something was done that no tool did), so it never reached the phone:  
> בעדכון לצוות כתבתי שהקריאה הקודמת סומנה כטופלה והשער עדיין לא עובד, ושזו כבר הפעם השלישית החודש. יותר מזה אני לא יכול לעשות מכאן.  
> *In the update to the team I wrote that the previous ticket was marked as handled and the gate still doesn't work, and that this is already the third time this month. More than that I can't do from here.*  
> The live bot then wrote again:

*Behind the scenes: Michael left a note for the operations team (other): "הדייר דיווח על שער החניה בבר כוכבא 23 שלא נפתח עם השלט והוא תקוע בחוץ. הוא מבקש שהפעם יטפלו בתקלה באופן סופי ולא יסמנו את הקריאה כטופלה לפני שהיא נפתרה. זו כבר הפעם השלישית החודש. הקריאה הפתוחה: 255-1".*

**Michael:** רשמתי לצוות גם את זה: שאתה רוצה שהפעם יטפלו בתקלה סופית ולא יסגרו את הקריאה לפני כן. מה יעשו מכאן אני לא יודע.  
*I noted for the team this too: that you want them to deal with the fault for good this time and not close the ticket before that. What they'll do from here I don't know.*

**Resident:** מדהים. אין לי כוח לזה כבר. נראה  
*Amazing. I've got no strength for this anymore. We'll see*

**Michael:** זה באמת מתיש. הקריאה פתוחה, ואפשר לשאול אותי כאן על המצב שלה.  
*That's really exhausting. The ticket is open, and you can ask me here about its status.*

**My read:** The ticket went in with his own words: the third time this month, already reported twice. The stock closing then set him off (finding 6). After that the bot did well:
- It found the earlier gate ticket, marked handled on 24 Sep.
- It said plainly that it can't open the gate from where it is.
- It passed his question to the team.
- Asked "are you a bot??", it said yes.

One draft was blocked by a false alarm (finding 3), and the rewrite went out.

### 6. Status: she has the number, typed with spaces; it drips on her car

**Button:** מצב קריאה קיימת (status of an existing ticket). **Sunday 09:20, Israel time.**

**The resident's card** (all the player had): דליה, 52. Organized, polite but firm; full sentences. Writes about herself in the feminine (אני רוצה לדעת, אני מבינה). Lives at בר כוכבא 23, apartment 6. A week ago she reported a leak in the car park that drips onto her parking space, number 6, and she kept the ticket number from the reply. She types it as 255 1501 26 (spaces, no hyphens). **Wants:** To know when it will be fixed; it drips on her car every day. **May:** Asks when they will come and finish. May ask Michael to push it or mark it urgent.

**Resident:** בוקר טוב  
*Good morning*

**System (fixed menu, three buttons):** בוקר טוב 👋 במה אפשר לעזור?  
*Good morning 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** מצב קריאה קיימת  
*(taps "Status of an existing ticket")*

**Michael:** כאן מיכאל מהומי'ז, העניין אצלי 🙂 מה מספר הקריאה שלך?  
*This is Michael from Homies, the matter is with me 🙂 What is your request number?*

**Resident:** מספר הקריאה שלי הוא 255 1501 26  
*My request number is 255 1501 26*

*Behind the scenes: Michael looked up the ticket by reference 255 1501 26: 255-1501-26 in_progress (נזילה בחניון, מטפטף על חניה 6).*

**Michael:** הקריאה 255-1501-26 על הנזילה בחניון, זאת שמטפטפת על חניה 6, בטיפול. היא נפתחה ב-27 בספטמבר, והעדכון האחרון בה היה ב-1 באוקטובר. יש עוד משהו שאפשר לעזור בו?  
*Request 255-1501-26, about the leak in the car park, the one dripping onto space 6, is being handled. It was opened on 27 September, and the last update on it was on 1 October. Is there anything else I can help with?*

**Resident:** אני מבינה שזה בטיפול, אבל מתי באים לסיים את זה? זה מטפטף לי על האוטו כל יום.  
*I understand it is being handled, but when are they coming to finish it? It drips on my car every day.*

*Behind the scenes: Michael left a note for the operations team (other): "הדיירת שואלת מתי באים לסיים לטפל בקריאה 255-1501-26, נזילה בחניון שמטפטפת על חניה 6, ומספרת שזה מטפטף לה על האוטו כל יום".*

**Michael:** איזה מעצבן. אין לי כרגע תאריך למתי יסיימו עם זה, אבל הצוות יודע עכשיו שזה ממשיך לטפטף על האוטו שלך כל יום. אפשר לעזור לך בעוד משהו?  
*How annoying. I don't have a date right now for when they will finish with this, but the team now knows that it keeps dripping on your car every day. Can I help you with anything else?*

**Resident:** תודה. אבל פתחתי את הקריאה לפני שבוע, ועדיין אין לי שום מועד. אפשר בבקשה לסמן אותה כדחופה?  
*Thanks. But I opened the request a week ago, and I still have no date at all. Could you please mark it as urgent?*

*Behind the scenes: Michael left a note for the operations team (other): "הדיירת מבקשת לסמן את קריאה 255-1501-26 כדחופה: נזילה בחניון שמטפטפת על חניה 6, נפתחה לפני שבוע ועדיין אין מועד, ומטפטף לה על האוטו כל יום".*

**Michael:** שבוע זה באמת הרבה. הצוות יודע שביקשת לסמן את הקריאה כדחופה. אם יש עוד משהו שאפשר לעשות בשבילך, אני כאן.  
*A week really is a lot. The team knows that you asked to mark the request as urgent. If there is anything else I can do for you, I'm here.*

**Resident:** אני מבינה, אבל אני צריכה לדעת: היא סומנה כדחופה, או שהצוות רק יודע שביקשתי?  
*I understand, but I need to know: was it marked as urgent, or does the team only know that I asked?*

*Behind the scenes: Michael looked up the ticket by reference 255-1501-26: 255-1501-26 in_progress (נזילה בחניון, מטפטף על חניה 6).*

**Michael:** לפי המערכת היא עדיין מסומנת כרגילה, לא כדחופה. הצוות יודע שביקשת לשנות את זה, אבל את הסימון עצמו אני לא יכול לשנות מכאן, ומה יקרה עכשיו אין לי דרך לדעת. ואם אפשר לעזור בעוד משהו, תגידי לי.  
*According to the system it is still marked as regular, not as urgent. The team knows you asked to change that, but the marking itself I can't change from here, and what will happen now I have no way of knowing. And if I can help with anything else, tell me.*

**Resident:** הבנתי, תודה על התשובה הישירה. אני מצפה שמישהו יחזור אליי עם מועד, כי זה באמת מפריע לי.  
*Understood, thank you for the direct answer. I expect someone to get back to me with a date, because it really bothers me.*

**Michael:** תודה שפנית 🙏 מקווה שזה יסתדר מהר, ושיהיה לך המשך יום טוב.  
*Thanks for reaching out 🙏 I hope it gets sorted out quickly, and have a good rest of your day.*

**My read:** The strongest of the 15. The number typed with spaces was found. Asked when, the bot said it has no date and told the team the leak drips on her car every day. Asked to mark the ticket urgent, it told the team. Asked whether it was actually marked, it checked again and said plainly that it is still marked as regular and that it can't change that itself. It used the feminine from "אני מבינה" on.

### 7. Status: no number, a young man who writes slang; the intercom

**Button:** מצב קריאה קיימת (status of an existing ticket). **Sunday 12:45, Israel time.**

**The resident's card** (all the player had): עמית, 28. Laid-back; writes slang (אחי, סבבה, וואלה), no punctuation, short lines. Lives at בר כוכבא 23, apartment 10. A few days ago he reported here that the intercom at the entrance does not ring in his flat. He did not save the ticket number. **Wants:** To know if someone is coming to fix the intercom; he is expecting a delivery. **May:** Answers with the building but forgets the apartment, or the other way round. May ask whether someone is coming today.

**Resident:** הי  
*Hi*

**System (fixed menu, three buttons):** צהריים טובים 👋 במה אפשר לעזור?  
*Good afternoon 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** מצב קריאה קיימת  
*(taps "Status of an existing ticket")*

**Michael:** כאן מיכאל מהומי'ז, העניין אצלי. יש לך מספר קריאה, או שתגיד לי באיזה בניין מדובר?  
*Michael from Homies here, the matter is with me. Do you have a request number, or can you tell me which building it is about?*

**Resident:** לא שמרתי את המספר אחי בר כוכבא 23  
*I didn't save the number bro Bar Kochba 23*

*Behind the scenes: Michael looked up the ticket by building בר כוכבא 23: 3 tickets in the building, no descriptions (it has to ask which).*

**Michael:** אין בעיה, באיזו דירה אתה גר?  
*No problem, which apartment do you live in?*

**Resident:** 10 אחי  
*10 bro*

*Behind the scenes: Michael looked up the ticket by building בר כוכבא 23, unit 10: 255-1486-26 open (האינטרקום בכניסה לא מצלצל בדירה 10).*

**Michael:** תודה, מצאתי. הקריאה על האינטרקום שלא מצלצל אצלך היא מספר 255-1486-26, והיא פתוחה, נפתחה ב-1 באוקטובר. יש עוד משהו שאפשר לעזור בו?  
*Thanks, found it. The request about the intercom that doesn't ring at your place is number 255-1486-26, and it is open, it was opened on 1 October. Is there anything else I can help with?*

**Resident:** וואלה אחי מישהו מגיע היום לתקן את זה מחכה למשלוח  
*wallah bro is someone coming today to fix this waiting for a delivery*

**Michael:** איזה מעצבן, עם משלוח בדרך. אין לי כרגע מידע אם מישהו מגיע היום. הסטנדרט אצלנו לתקלה שאינה חירום הוא עד 3 ימי עסקים, אבל זו לא הבטחה על הקריאה הזאת. יש עוד משהו שאני יכול לעשות בשבילך?  
*How annoying, with a delivery on the way. I don't have any information right now on whether someone is coming today. Our standard for a fault that is not an emergency is up to 3 business days, but that is not a promise about this request. Is there anything else I can do for you?*

**Resident:** וואלה 3 ימים זה המון אחי אפשר להגיד להם שזה דחוף  
*wallah 3 days is a lot bro can you tell them it's urgent*

*Behind the scenes: Michael left a note for the operations team (other): "דייר מבקש שהקריאה על האינטרקום שלא מצלצל אצלו תטופל היום ושידעו שזה דחוף: הוא מחכה למשלוח, ו-3 ימים זה המון בשבילו. בר כוכבא 23, דירה 10, קריאה 255-1486-26".*

**Michael:** בטח. הצוות יודע שהאינטרקום דחוף לך להיום, בגלל המשלוח. יש משהו נוסף שאפשר לסדר לך?  
*Sure. The team knows that the intercom is urgent for you today, because of the delivery. Is there anything else I can sort out for you?*

**Resident:** סבבה תודה אחי  
*cool thanks bro*

**Michael:** תודה שפנית אלינו.  
*Thanks for contacting us.*

> The bot wrote "תודה שפנית אלינו. שהמשלוח יגיע אליך בקלות ושיהיה לך המשך יום טוב 🙂" ("Thanks for contacting us. May the delivery reach you easily, and have a good rest of your day 🙂"). The sending step cut everything after the first sentence, because of "יגיע אליך" ("will reach you").

**My read:** He gave only the building, and there were three tickets there, so the bot asked his flat instead of reading out the neighbours' tickets. It found his. It did not mirror his slang. Asked to say it is urgent, it told the team. The goodbye was cut to "תודה שפנית אלינו." by the sending step (finding 2).

### 8. Status: she reported it by phone, nothing is on record; the lobby light

**Button:** מצב קריאה קיימת (status of an existing ticket). **Sunday 16:30, Israel time.**

**The resident's card** (all the player had): רחל, 67. Not at home with smartphones: slow, short messages, sometimes words glued together or a doubled letter. Polite and warm, calls people יקירי. Writes about herself in the feminine (אני לא יודעת, אני בטוחה). Lives at בר כוכבא 23, apartment 1, on the ground floor by the lobby. About two weeks ago she phoned the office and told a woman there that the lobby light is broken; it is still dark at night. She was given no number. **Wants:** The lobby light fixed; she is afraid of falling in the dark. **May:** May not understand what a ticket number (מספר קריאה) is at first. If nothing is found she is upset that her call was lost, then accepts help.

**Resident:** שלום  
*Hello*

**System (fixed menu, three buttons):** צהריים טובים 👋 במה אפשר לעזור?  
*Good afternoon 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** מצב קריאה קיימת  
*(taps "Status of an existing ticket")*

**Michael:** כאן מיכאל מהומי'ז, ואני איתך על זה 🙂 אם יש לך מספר קריאה אשמח לקבל אותו, ואם לא, באיזה בניין מדובר?  
*This is Michael from Homies, and I'm with you on this 🙂 If you have a ticket number I'd be glad to get it, and if not, which building is it?*

**Resident:** אין לי מספר יקירי. בר כוכבא 23  
*I don't have a number, dear. Bar Kochba 23*

*Behind the scenes: Michael looked up the ticket by building בר כוכבא 23: nothing found.*

**Michael:** בבר כוכבא 23 אני לא רואה כרגע אף קריאה פתוחה. על מה הייתה הקריאה שלך?  
*In Bar Kochba 23 I don't currently see any open ticket. What was your ticket about?*

**Resident:** האור בלובי מקולקל יקירי.התקשרתי למשרד לפני שבועיים ועדיין חושך בלילה  
*The light in the lobby is broken, dear.I phoned the office two weeks ago and it's still dark at night*

*Behind the scenes: Michael opened ticket 255-1515-26 (lighting, normal urgency, fault in the common areas; filed under apartment none): "האור בלובי מקולקל, התקשרתי למשרד לפני שבועיים ועדיין חושך בלילה".*

**Michael:** אוי, לא נעים. פתחתי עכשיו קריאה על התאורה בלובי של בר כוכבא 23, והמספר שלה 255-1515-26. יש עוד משהו שאפשר לעזור בו?  
*Oh, that's not nice. I've just opened a ticket about the lighting in the lobby of Bar Kochba 23, and its number is 255-1515-26. Is there anything else I can help with?*

**Resident:** תודה יקירי. אבל למה לא רשמו את השיחה שלי לפני שבועיים? אני מפחדת ליפול בחושך  
*Thank you, dear. But why didn't they record my call from two weeks ago? I'm afraid of falling in the dark*

> Michael's first draft was blocked by the live checks (it said something was done that no tool did), so it never reached the phone:  
> בחושך זה באמת מפחיד, ואני מצטער שזה נמשך. את השיחה מלפני שבועיים אין לי איך לראות, אבל הקריאה שפתחתי עכשיו רשומה, ובכל רגע תוכלי לשאול אותי כאן מה איתה. אפשר לעזור לך בעוד משהו?  
> *In the dark it really is frightening, and I'm sorry it's dragged on. The call from two weeks ago I have no way to see, but the ticket I opened just now is registered, and at any time you can ask me here what's happening with it. Can I help you with anything else?*  
> The live bot then wrote again:

**Michael:** בחושך זה באמת מפחיד, ואני מצטער שזה נמשך. את השיחה מלפני שבועיים אין לי איך לראות, אבל על האור בלובי כבר יש קריאה רשומה עם המספר 255-1515-26, ובכל רגע תוכלי לשאול אותי כאן מה איתה. אפשר לעזור לך בעוד משהו?  
*In the dark it really is frightening, and I'm sorry it's dragged on. The call from two weeks ago I have no way to see, but for the lobby light there is already a registered ticket with the number 255-1515-26, and at any time you can ask me here what's happening with it. Can I help you with anything else?*

**Resident:** טוב יקירי. ומתי יבוא מישהו לתקן את האור?  
*OK, dear. And when will someone come to fix the light?*

**Michael:** מתי בדיוק זה יטופל אני לא יודע להגיד לך. הסטנדרט אצלנו לתקלה שאינה חירום הוא עד 3 ימי עסקים, אבל זה סטנדרט כללי ולא הבטחה על הקריאה הזאת. יש משהו נוסף שאפשר לעזור בו?  
*When exactly it will be handled I can't tell you. The standard with us for a non-emergency fault is up to 3 business days, but that is a general standard and not a promise about this ticket. Is there anything more I can help with?*

**Resident:** לא יקירי תודה רבה.נחכה  
*No, dear, thank you very much.We'll wait*

**Michael:** בשמחה. תודה שפנית אלינו, והמשך יום נעים 🙂  
*My pleasure. Thanks for reaching out to us, and have a pleasant rest of your day 🙂*

**My read:** Nothing was on record, and the bot said so plainly, asked what it was about and opened a ticket for the lobby light. It never asked her flat (finding 8). When she asked why her phone call was lost, the first draft was blocked by a known false alarm (finding 3). The rewrite gave the ticket number instead and went out. Kind throughout; feminine from "אני מפחדת".

### 9. Status: marked resolved, still dark; a sarcastic man

**Button:** מצב קריאה קיימת (status of an existing ticket). **Sunday 18:05, Israel time.**

**The resident's card** (all the player had): גלעד, 41. Matter-of-fact and a little sarcastic; short sentences with punctuation. Lives at בר כוכבא 23, apartment 8. He has the ticket number 255-1460-26, for the stairwell light on floor 3. On Friday he got word it was handled, but the light is still off; he checked tonight. **Wants:** The light actually fixed, not a ticket closed on paper. **May:** Sarcastic about 'handled'. Will not accept being told it is resolved. May ask who checked it.

**Resident:** ערב טוב  
*Good evening*

**System (fixed menu, three buttons):** ערב טוב 👋 במה אפשר לעזור?  
*Good evening 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** מצב קריאה קיימת  
*(taps "Status of an existing ticket")*

**Michael:** כאן מיכאל מהומי'ז מה מספר הקריאה, או באיזה בניין מדובר?  
*Michael from Homies here what's the ticket number, or which building is it about?*

> The bot wrote "כאן מיכאל מהומי'ז, אני על זה 🙂 מה מספר הקריאה..." ("... I'm on it 🙂 ..."). The sending step removes "I'm on it" on purpose, and the comma went with it.

**Resident:** 255-1460-26. ביום שישי אמרו לי שטופל. האור בחדר המדרגות לא קיבל את ההודעה.  
*255-1460-26. On Friday they told me it was handled. The stairwell light didn't get the message.*

*Behind the scenes: Michael looked up the ticket by reference 255-1460-26: 255-1460-26 resolved (התאורה בחדר המדרגות בקומה 3 לא עובדת).*

**Michael:** איזה מעצבן. הקריאה 255-1460-26 מסומנת אצלנו כנפתרה, עדכון אחרון ב-2 באוקטובר. אפתח לך קריאה חדשה על האור. באיזה בניין ובאיזו דירה אתה גר?  
*How annoying. Ticket 255-1460-26 is marked on our side as resolved, last update on October 2. I'll open you a new ticket about the light. Which building and which apartment do you live in?*

**Resident:** על הנייר, בטח. בר כוכבא 23, דירה 8.  
*On paper, sure. Bar Kochba 23, apartment 8.*

*Behind the scenes: Michael opened ticket 255-1516-26 (lighting, high urgency, fault in the common areas; filed under apartment 8): "האור בחדר המדרגות עדיין לא עובד. קריאה קודמת על זה, 255-1460-26, סומנה כנפתרה, והאור כבוי".*

**Michael:** תודה. פתחתי קריאה חדשה על האור בחדר המדרגות, מספר 255-1516-26. יש עוד משהו שאפשר לעזור בו?  
*Thanks. I opened a new ticket about the stairwell light, number 255-1516-26. Is there anything else I can help with?*

**Resident:** ומי בדק את הקודמת בכלל? מישהו עלה לקומה 3?  
*And who checked the previous one at all? Did anyone go up to the 3rd floor?*

*Behind the scenes: Michael left a note for the operations team (other): "הדייר שואל מי בדק את הקריאה הקודמת 255-1460-26, שסומנה כנפתרה, ואם מישהו עלה לבדוק את האור בחדר המדרגות בקומה 3. לדבריו האור עדיין כבוי. נפתחה קריאה חדשה 255-1516-26".*

**Michael:** שאלה הוגנת. את זה אין לי כרגע, מי בדק את הקודמת. הצוות יודע על השאלה שלך ועל זה שהאור עדיין כבוי. יש עוד משהו שאפשר לעשות בשבילך?  
*Fair question. That I don't have right now, who checked the previous one. The team knows about your question and that the light is still off. Is there anything else I can do for you?*

**Resident:** טוב. ומתי האור באמת יידלק?  
*Okay. And when will the light actually come on?*

**Michael:** את הזמן המדויק אין לי. הסטנדרט שלנו לתקלה שאינה חירום הוא עד 3 ימי עסקים, אבל זו לא הבטחה על הקריאה הזאת. אפשר לעזור בעוד משהו?  
*The exact time I don't have. Our standard for a fault that isn't an emergency is up to 3 business days, but that's not a promise on this ticket. Can I help with anything else?*

**Resident:** טוב. רק שלא יסגרו גם את זו על הנייר. תודה.  
*Okay. Just that they don't close this one on paper too. Thanks.*

**Michael:** מקווה שהפעם האור יידלק. תודה שפנית, ושיהיה לך ערב טוב.  
*I hope the light comes on this time. Thanks for getting in touch, and have a good evening.*

**My read:** Handled well. The bot said the old ticket is marked resolved, opened a new one that names the old one, and passed his "who checked it?" to the team without guessing. The first reply to the button lost "I'm on it" and its comma to the sending step (finding 2).

### 10. Status: a mother typing one-handed; cockroaches in the bin room

**Button:** מצב קריאה קיימת (status of an existing ticket). **Sunday 10:40, Israel time.**

**The resident's card** (all the player had): נועה, 33. A baby on one arm, typing with one thumb: fragments and typos, sometimes a sentence cut off and finished in the next message. Writes about herself in the feminine. Lives at בר כוכבא 23, apartment 15. Last week she reported cockroaches in the bin room, she thinks through this WhatsApp. She has no ticket number. **Wants:** To know whether pest control is coming, and when. **May:** Writes the street glued together and without the number at first (ברכוכבא), and the number in the next message. May skip a question and ask her own instead.

**Resident:** היי  
*Hi*

**System (fixed menu, three buttons):** בוקר טוב 👋 במה אפשר לעזור?  
*Good morning 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** מצב קריאה קיימת  
*(taps "Status of an existing ticket")*

> Michael's first draft was blocked by the live checks (it announced a ticket that no tool had opened), so it never reached the phone:  
> כאן מיכאל מהומי'ז 🙂 אשמח לעזור לך עם זה. באיזה בניין נפתחה הקריאה?  
> *This is Michael from Homies 🙂 I'd be happy to help you with this. In which building was the request opened?*  
> The live bot then wrote again:

**Michael:** כאן מיכאל מהומי'ז. באיזה בניין מדובר?  
*This is Michael from Homies. Which building is it about?*

**Resident:** ברכוכבא  
*Barkochba (the street name run together as one word, no number)*

*Behind the scenes: Michael looked up the ticket by building ברכוכבא: the address was not recognised, nothing found.*

**Michael:** לא הצלחתי למצוא בניין בשם הזה. תוכל לכתוב לי את הרחוב ואת מספר הבית?  
*I couldn't find a building by that name. Could you write me the street and the house number?*

**Resident:** 23  
*23*

*Behind the scenes: Michael looked up the ticket by building בר כוכבא 23: 2 tickets in the building, no descriptions (it has to ask which).*

**Michael:** תודה 🙂 על מה הקריאה?  
*Thanks 🙂 What is the request about?*

**Resident:** גוקים בחדר אשפה  
*Cockroaches in bin room*

*Behind the scenes: Michael looked up the ticket by building בר כוכבא 23, type pest_control: 255-1477-26 open (ג'וקים בחדר האשפה).*

**Michael:** אוי, לא נעים. מצאתי את הקריאה על ג'וקים בחדר האשפה, מספר 255-1477-26. היא נפתחה ב-28 בספטמבר והיא פתוחה, והעדכון האחרון בה מאותו יום. יש עוד משהו שתרצה לדעת עליה?  
*Oh, that's unpleasant. I found the request about cockroaches in the bin room, number 255-1477-26. It was opened on 28 September and it is open, and the last update on it is from that same day. Is there anything else you'd like to know about it?*

**Resident:** אז מגיע מדביר? ומתי  
*So is a pest controller coming? And when*

*Behind the scenes: Michael looked up "מתי מגיע מדביר" in the service catalogue: הדברה.*

**Michael:** כרגע אין לי מידע על מועד להדברה. מה שאני כן יודע זה שכשיש הדברה, מודיעים לדיירים לפחות שבוע מראש. יש עוד משהו שאפשר לעזור בו?  
*Right now I have no information about a date for pest control. What I do know is that when there is pest control, residents are notified at least a week ahead. Is there anything else I can help with?*

**Resident:** אבל דווחתי לפני שבוע, אפשר לבדוק מתי יבואו  
*But I reported a week ago, can you check when they'll come*

*Behind the scenes: Michael left a note for the operations team (other): "דווחתי לפני שבוע על ג'וקים בחדר האשפה, אפשר לבדוק מתי יבואו. בר כוכבא 23, קריאה 255-1477-26".*

**Michael:** הצוות יודע עכשיו שהקריאה פתוחה כבר שבוע ושחשוב לך לדעת מתי יבואו. יש משהו נוסף שאפשר לעזור בו כרגע?  
*The team now knows that the request has already been open for a week and that it is important to you to know when they will come. Is there anything else I can help with right now?*

**Resident:** ומישהו יחזור אלי?  
*And will someone get back to me?*

**Michael:** את זה אין לי דרך לדעת, אני לא רואה מה קורה אצל הצוות מכאן. אפשר לעזור לך בעוד משהו בינתיים?  
*I have no way of knowing that, I can't see from here what is happening on the team's side. Can I help you with anything else in the meantime?*

**Resident:** טוב תודה  
*OK thanks*

**Michael:** תודה שפנית אליי. שיהיה לך המשך יום נעים.  
*Thanks for reaching out to me. Have a pleasant rest of your day.*

**My read:** Messy typing handled calmly:
- The street came glued together with no number. The bot said it could not find it and asked for the street and number.
- With "23" alone, two tickets came back, and the bot asked what hers was about.
- It then found hers, open since 28 Sep.

The first reply to the button was blocked by a false alarm, and the rewrite came out colder (finding 3). The "week ahead" fact was misapplied (finding 8). She never wrote anything gendered, so the masculine was correct by the owner's rule.

### 11. Talk to a rep: 'are you a person or a computer?', then a committee decision

**Button:** לדבר עם נציג (talk to a representative). **Sunday 10:05, Israel time.**

**The resident's card** (all the player had): שמעון, 58. Suspicious of bots and of companies; terse and a little confrontational, not rude. Lives at בר כוכבא 23, apartment 11. Full name שמעון אברהם. The house committee decided on a lobby renovation without asking him; he wants the meeting's minutes and to object. **Wants:** To talk to a real person at Homies about the renovation decision. **May:** First asks whether he is talking to a person or a computer (אתה בן אדם או מחשב?). Insists on a real person. If told the team will get a note, asks when they will call him.

**Resident:** שלום  
*Hello*

**System (fixed menu, three buttons):** בוקר טוב 👋 במה אפשר לעזור?  
*Good morning 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** לדבר עם נציג  
*(taps "Talk to a representative")*

**Michael:** היי, כאן מיכאל מהומי'ז 🙂 מה שלומך היום?  
*Hi, this is Michael from Homies 🙂 How are you today?*

**Resident:** אתה בן אדם או מחשב?  
*Are you a person or a computer?*

**Michael:** אני עוזר דיגיטלי של הומי'ז, לא בן אדם. במה אפשר לעזור לך?  
*I'm a digital assistant of Homies, not a person. How can I help you?*

**Resident:** אני רוצה בן אדם אמיתי, לא בוט  
*I want a real person, not a bot*

*Behind the scenes: Michael left a note for the service team (caller_request): "הדייר מבקש בן אדם אמיתי, לא בוט".*

**Michael:** בסדר גמור. רשמתי לצוות שאתה רוצה לדבר עם בן אדם, אז הם יודעים. יש עוד משהו שאפשר לעזור בו?  
*All right. I've noted to the team that you want to talk to a person, so they know. Is there anything else I can help with?*

**Resident:** ומתי יתקשרו אלי?  
*And when will they call me?*

**Michael:** את זה אני לא יודע, אין לי מידע אם ומתי יתקשרו אליך. על מה רצית לדבר איתם?  
*That I don't know, I have no information on whether or when they will call you. What did you want to talk to them about?*

**Resident:** הוועד החליט על שיפוץ בלובי בלי לשאול אותי. אני רוצה את הפרוטוקול ולהתנגד  
*The committee decided on a renovation in the lobby without asking me. I want the minutes and to object*

*Behind the scenes: Michael left a note for the management team (other): "הוועד החליט על שיפוץ בלובי בלי לשאול אותו. הדייר רוצה את הפרוטוקול של הישיבה ורוצה להתנגד להחלטה, ומבקש לדבר עם בן אדם".*

**Michael:** אוקיי. רשמתי לצוות הכול, גם את הפרוטוקול וגם שאתה רוצה להתנגד להחלטה. יש עוד משהו שאפשר לסדר לך כאן?  
*Okay. I've noted everything to the team, both the minutes and that you want to object to the decision. Is there anything else I can sort out for you here?*

**Resident:** טוב. נראה אם מישהו יתקשר  
*Okay. We'll see if anyone calls*

**Michael:** תודה שכתבת לי. שיהיה לך המשך יום טוב.  
*Thanks for writing to me. Have a good rest of your day.*

**Check not met:** no transfer, no call-back promise. This is the check's own mistake: it caught "יתקשרו" ("they will call") inside "אין לי מידע אם ומתי יתקשרו אליך" ("I have no information whether or when they will call you"), which promises nothing.

**My read:** Honest throughout: he asked whether he was talking to a person and was told a digital assistant (finding 7). His wish for a real person and then the committee matter both went to the team. Asked when they would call, the bot said it does not know whether or when. It promised nothing, but he left unconvinced.

### 12. Talk to a rep: 'fine, thanks', how do I pay, then a standing order

**Button:** לדבר עם נציג (talk to a representative). **Sunday 13:10, Israel time.**

**The resident's card** (all the player had): ליאת, 36. Busy and efficient, friendly enough; answers in a few words. Writes about herself in the feminine (אני צריכה, לא יודעת). Lives at בר כוכבא 23, apartment 4. Wants to pay the house committee fee (ועד בית) and does not know how. Would rather set up a standing order (הוראת קבע) so she does not have to remember every month. **Wants:** To pay, and if possible to set up a standing order. **May:** Answers בסדר תודה and goes straight to the point. After getting a link, asks about the standing order. Ends with a short thanks.

**Resident:** היי  
*Hi*

**System (fixed menu, three buttons):** צהריים טובים 👋 במה אפשר לעזור?  
*Good afternoon 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** לדבר עם נציג  
*(taps "Talk to a representative")*

**Michael:** היי, כאן מיכאל מהומי'ז 🙂 מה שלומך היום?  
*Hi, this is Michael from Homies 🙂 How are you today?*

**Resident:** בסדר תודה  
*Fine, thanks*

**Michael:** שמח לשמוע. אז במה אפשר לעזור לך היום?  
*Glad to hear it. So what can I help you with today?*

**Resident:** רוצה לשלם ועד בית אבל לא יודעת איך  
*Want to pay the house committee fee but I don't know how*

*Behind the scenes: Michael fetched the resident's own payment link.*

**Michael (a quick first message):** בטח, אני בודק את זה אצלנו במערכת עכשיו.  
*Sure, I'm checking this in our system now.*

**Michael:** הנה הקישור לתשלום של דירה 4 בבר כוכבא 23: <link> הוא אישי ומיועד לדירה שלך בלבד, אז כדאי לא להעביר אותו הלאה. אם משהו לא ברור, תכתבי לי כאן.  
*Here is the payment link for apartment 4 at Bar Kochba 23: <link> It is personal and meant for your apartment only, so it's best not to pass it on. If anything is unclear, write to me here.*

> The bot wrote the link on its own line, with a blank line above and below it. The sending step turned the blank lines into spaces, so the phone shows the link mid-sentence.

Automatic checks on this reply: the link is not on its own line ("הנה הקישור לתשלום של דירה 4 בבר כוכבא 23: <link> הוא אישי ומיועד לדירה שלך בלבד, אז כדאי לא להעביר אותו הלאה. ").

**Resident:** אפשר גם הוראת קבע? שלא אצטרך לזכור כל חודש  
*Can I also do a standing order? So I won't have to remember every month*

*Behind the scenes: Michael opened ticket 255-1518-26 (payment, normal urgency, fault in the common areas; filed under apartment 4): "הדיירת מבקשת להסדיר תשלום ועד בית בהוראת קבע, כדי שלא תצטרך לזכור לשלם כל חודש".*

*Behind the scenes: Michael left a note for the collections team (payment): "הדיירת מבקשת להסדיר תשלום ועד בית בהוראת קבע, כדי שלא תצטרך לזכור כל חודש. בר כוכבא 23, דירה 4. קריאת שירות 255-1518-26".*

**Michael:** רעיון טוב 🙂 פתחתי על זה קריאה, מספר 255-1518-26, והצוות יודע. יש עוד משהו שאפשר לעזור בו?  
*Good idea 🙂 I opened a ticket on it, number 255-1518-26, and the team knows. Is there anything else I can help with?*

**Resident:** זהו, תודה  
*That's it, thanks*

**Michael:** בשמחה, תודה שפנית. שיהיה לך המשך יום נעים.  
*My pleasure, thanks for getting in touch. Have a pleasant rest of your day.*

**My read:** Went well:
- "Fine, thanks" got a short warm word and the help question.
- The payment request got a quick "checking now" message, then the link, called personal, in the feminine.

Two catches: the link reached her mid-sentence (finding 1), and the standing-order question got a ticket but no answer (finding 8).

### 13. Talk to a rep: an elderly woman says she already paid by cheque

**Button:** לדבר עם נציג (talk to a representative). **Sunday 17:20, Israel time.**

**The resident's card** (all the player had): אסתר, 74. Very polite and warm: long messages that start with שלום רב and carry blessings (ברוך השם, תהיה בריא). Slow with the phone. Writes about herself in the feminine. Lives at בר כוכבא 23, apartment 5. Full name אסתר מזרחי, phone <phone>. She got a letter saying she owes 900 ₪ for July to September, but she paid by cheque in July to משה from the house committee. **Wants:** The debt taken off; she paid. **May:** Answers how-are-you at length (her knee, the grandchildren). Asks Michael to check how much she owes. Repeats that she paid.

**Resident:** שלום רב  
*Hello (the polite, formal "shalom rav")*

**System (fixed menu, three buttons):** ערב טוב 👋 במה אפשר לעזור?  
*Good evening 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** לדבר עם נציג  
*(taps "Talk to a representative")*

**Michael:** היי, כאן מיכאל מהומי'ז 🙂 מה שלומך היום?  
*Hi, this is Michael from Homies 🙂 How are you today?*

**Resident:** שלום רב מיכאל, תודה רבה ששאלת, ברוך השם אני מסתדרת. רק הברך מציקה לי קצת בימים האלה אבל זה הגיל מה אפשר לעשות. הנכדים שלי היו אצלי בשבת ועשו לי הרבה שמחה. תהיה בריא ושמח גם אתה. רציתי לשאול אותך על המכתב שקיבלתי מכם  
*Hello Michael, thank you very much for asking, thank God I'm managing (feminine). Only my knee bothers me a bit these days, but that's age, what can you do. My grandchildren were at my place on Shabbat and gave me a lot of joy. May you be healthy and happy too. I wanted to ask you about the letter I received from you*

**Michael:** איזה כיף שהנכדים היו אצלך, ומקווה שהברך תירגע. ספרי לי, מה רצית לשאול על המכתב?  
*How nice that the grandchildren were at your place, and I hope the knee calms down. Tell me (feminine), what did you want to ask about the letter?*

**Resident:** תודה מיכאל יקר. במכתב כתוב שאני חייבת 900 שקל על יולי אוגוסט וספטמבר, אבל אני כבר שילמתי בצ'ק בחודש יולי, נתתי אותו למשה מוועד הבית. אני לא מבינה למה שלחו לי מכתב  
*Thank you, dear Michael. The letter says I owe 900 shekels for July August and September, but I already paid by cheque in July, I gave it to Moshe from the house committee. I don't understand why they sent me a letter*

*Behind the scenes: Michael left a note for the collections team (billing): "הדיירת קיבלה מכתב ובו כתוב שהיא חייבת 900 שקל על יולי, אוגוסט וספטמבר, אבל לדבריה שילמה בצ'ק בחודש יולי למשה מוועד הבית. היא לא מבינה למה נשלח לה המכתב".*

**Michael:** אוי, איזה בלבול. הצוות יודע עכשיו על המכתב ועל זה שנתת צ'ק למשה ביולי. יש עוד משהו שאפשר לעזור בו?  
*Oh, what a mix-up. The team now knows about the letter and about the cheque you gave Moshe in July. Is there anything else I can help with?*

**Resident:** תודה רבה מיכאל יקר, תהיה בריא. כן, אולי אתה יכול לבדוק לי בבקשה כמה אני חייבת אצלכם בכלל  
*Thank you very much, dear Michael, may you be healthy. Yes, maybe you can check for me please how much I owe you at all*

**Michael:** בשמחה 🙂 אפשר את השם המלא שלך ואת מספר הטלפון?  
*Gladly 🙂 Could I have your full name and your phone number?*

**Resident:** בטח מיכאל יקר, אסתר מזרחי והטלפון שלי <phone>  
*Of course, dear Michael, Esther Mizrahi and my phone is <phone>*

*Behind the scenes: Michael checked the balance with the name and phone typed: 900 owed, months 2026-07, 2026-08, 2026-09.*

**Michael:** תודה, אסתר. רשום אצלנו חוב של 900 שקל, על יולי, אוגוסט וספטמבר. אפשר לעזור לך בעוד משהו?  
*Thanks, Esther. We have a debt of 900 shekels on record, for July, August and September. Can I help you with anything else?*

**Resident:** אבל מיכאל יקר אני כבר שילמתי, נתתי צ'ק למשה מהוועד בחודש יולי. אני לא חייבת כלום. אתה לא יכול להוריד את זה מהמערכת בבקשה  
*But dear Michael, I already paid, I gave a cheque to Moshe from the committee in July. I don't owe anything. Can't you remove it from the system, please*

**Michael:** ברור שזה מעצבן. את החוב עצמו רק מישהו מהצוות יכול להוריד, לא אני. הם כבר יודעים על הצ'ק שנתת למשה ביולי. יש משהו נוסף שאפשר לעזור בו?  
*Of course that's annoying. The debt itself only someone from the team can remove, not me. They already know about the cheque you gave Moshe in July. Is there anything else I can help with?*

**Resident:** טוב מיכאל תודה רבה על העזרה, אני מקווה שיסדרו את זה. תהיה בריא ושבוע טוב  
*Well, Michael, thank you very much for the help, I hope they'll sort it out. May you be healthy, and have a good week*

**Michael:** תודה שפנית אלינו, אסתר, ושיהיה לך שבוע טוב ובריא 😊  
*Thank you for contacting us, Esther, and may you have a good and healthy week 😊*

**My read:** Warm with a very polite elderly woman. It answered her news about the grandchildren and her knee, then took up the letter in the feminine. The disputed bill went to the money team at once. Asked how much she owes, it asked for her full name and phone in one message and read the balance back, flatly, right after she had said she paid (finding 8). The goodbye used her name.

### 14. Talk to a rep: he skips the small talk; a smell of gas in the stairwell

**Button:** לדבר עם נציג (talk to a representative). **Sunday 08:45, Israel time.**

**The resident's card** (all the player had): דור, 25. Direct and practical; skips small talk; short messages, no greetings. Lives at בר כוכבא 23, apartment 13. On his way out this morning he smelled a strong smell of gas in the stairwell on floor 2. He is now outside the building. He does not know where it comes from. **Wants:** Someone to deal with the gas smell right away. **May:** Does not answer the how-are-you; goes straight to the smell. May ask what he should do meanwhile (open the windows? call the gas company?). May ask whether to warn the neighbours.

**Resident:** בוקר טוב  
*Good morning*

**System (fixed menu, three buttons):** בוקר טוב 👋 במה אפשר לעזור?  
*Good morning 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** לדבר עם נציג  
*(taps "Talk to a representative")*

**Michael:** היי, כאן מיכאל מהומי'ז 🙂 מה שלומך היום?  
*Hi, this is Michael from Homies 🙂 How are you today?*

**Resident:** יש ריח חזק של גז בחדר מדרגות קומה 2  
*There's a strong smell of gas in the stairwell, floor 2*

*Behind the scenes: Michael left a note for the operations team (emergency): "ריח חזק של גז בחדר מדרגות קומה 2".*

**Michael:** אוי, זה מדאיג. עדכנתי את הצוות על ריח הגז. באיזה בניין ובאיזו דירה אתה גר?  
*Oh, that's worrying. I've updated the team about the gas smell. Which building and which apartment do you live in?*

**Resident:** בר כוכבא 23, דירה 13  
*Bar Kochba 23, apartment 13*

*Behind the scenes: Michael opened ticket 255-1517-26 (fire safety, emergency urgency, fault in the common areas; filed under apartment 13): "ריח חזק של גז בחדר מדרגות קומה 2".*

**Michael:** פתחתי גם קריאה בדחיפות חירום, מספר 255-1517-26. אפשר לעזור במשהו נוסף?  
*I've also opened a ticket with emergency urgency, number 255-1517-26. Can I help with anything else?*

**Resident:** מישהו מגיע? או שאני צריך להתקשר לחברת הגז?  
*Is someone coming? Or do I need to call the gas company?*

**Michael:** אין לי מידע אם מישהו כבר מגיע, וגם מה לעשות בינתיים אני לא יכול להגיד לך. מה שיש לי זה הקריאה 255-1517-26 שנפתחה בדחיפות חירום, והצוות יודע. יש עוד משהו שאני יכול לעשות בשבילך?  
*I don't have information on whether someone is already coming, and I also can't tell you what to do in the meantime. What I have is ticket 255-1517-26, which was opened with emergency urgency, and the team knows. Is there anything else I can do for you?*

**Resident:** טוב. אני מתקשר לחברת הגז בעצמי  
*Okay. I'm calling the gas company myself.*

**Michael:** בסדר. אם תצטרך עוד משהו, אני כאן.  
*Okay. If you need anything else, I'm here.*

**My read:** The order was right: the team was told the moment he mentioned gas, then he was asked where, then an emergency ticket was opened with no emoji. Then came "I can't tell you what to do" (finding 4).

### 15. Talk to a rep: a landlord asks back 'and you?', then new tenants and who pays

**Button:** לדבר עם נציג (talk to a representative). **Sunday 20:30, Israel time.**

**The resident's card** (all the player had): אלי, 50. Friendly and chatty, polite; asks back how Michael is. Owns apartment 16 in בר כוכבא 23 and rents it out; he lives elsewhere. New tenants move in on 15 October. He wants to tell Homies, to know whether the tenants or he will pay the house committee fee from now on, and whether there is a form to fill in. He is also curious whether Homies manages rented flats for owners. **Wants:** To register the change of tenants and get answers about who pays and the form. **May:** Answers how-are-you warmly and asks back (ואתה?). Has two or three questions and asks them one after another.

**Resident:** ערב טוב  
*Good evening*

**System (fixed menu, three buttons):** ערב טוב 👋 במה אפשר לעזור?  
*Good evening 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** לדבר עם נציג  
*(taps "Talk to a representative")*

**Michael:** היי, כאן מיכאל מהומי'ז 🙂 מה שלומך היום?  
*Hi, this is Michael from Homies 🙂 How are you today?*

**Resident:** היי מיכאל, אני בסדר גמור תודה! ואתה, מה שלומך?  
*Hi Michael, I'm doing great, thanks! And you, how are you?*

**Michael:** היי! שמח לשמוע, ואצלי הכול טוב, תודה ששאלת. במה אפשר לעזור לך היום?  
*Hi! Glad to hear it, and I'm doing well too, thanks for asking. How can I help you today?*

**Resident:** יופי, תודה. רציתי לעדכן שיש לי דיירים חדשים בדירה שאני משכיר, הם נכנסים ב-15 לאוקטובר  
*Great, thanks. I wanted to update you that I have new tenants in the apartment I rent out, they move in on 15 October*

**Michael:** מעולה, תודה שעדכנת. באיזה בניין ואיזו דירה מדובר?  
*Great, thanks for updating. Which building and which apartment is it about?*

**Resident:** בר כוכבא 23, דירה 16  
*Bar Kochba 23, apartment 16*

*Behind the scenes: Michael left a note for the management team (move): "הדייר מעדכן שיש דיירים חדשים בדירה 16 בבר כוכבא 23, שהוא משכיר, והם נכנסים ב-15 לאוקטובר".*

**Michael:** הצוות יודע עכשיו שדיירים חדשים נכנסים לדירה 16 ב-15 באוקטובר. יש עוד משהו שאפשר לעזור בו?  
*The team now knows that new tenants are moving into apartment 16 on 15 October. Is there anything else I can help with?*

**Resident:** כן, תודה. יש לי עוד שאלה: את דמי ועד הבית מעכשיו מי משלם, אני או הדיירים?  
*Yes, thanks. I have one more question: the house committee fees, from now on who pays them, me or the tenants?*

*Behind the scenes: Michael looked up "מי משלם את דמי ועד הבית, אני או הדיירים" in the service catalogue: ניהול ועד בית.*

*Behind the scenes: Michael left a note for the collections team (other): "בעל הדירה בבר כוכבא 23 דירה 16 שואל מי משלם את דמי ועד הבית מעכשיו, הוא או הדיירים החדשים".*

**Michael:** אין לי כרגע תשובה על מי משלם את דמי הוועד, אז עדכנתי את הצוות בשאלה. עוד משהו שתרצה לשאול?  
*I don't have an answer right now on who pays the committee fee, so I've updated the team about the question. Anything else you'd like to ask?*

**Resident:** בסדר, תודה. ועוד דבר, יש איזשהו טופס שצריך למלא בגלל החלפת הדיירים?  
*OK, thanks. And one more thing, is there some form I need to fill in because of the change of tenants?*

*Behind the scenes: Michael left a note for the management team (move): "בעל הדירה בבר כוכבא 23 דירה 16 שואל אם יש איזשהו טופס שצריך למלא בגלל החלפת הדיירים".*

**Michael:** גם על הטופס אין לי מידע כרגע, ועדכנתי את הצוות גם בשאלה הזאת. יש עוד משהו שרצית לשאול?  
*I don't have information about the form right now either, and I've updated the team on this question as well. Is there anything else you wanted to ask?*

**Resident:** כן, שאלה אחרונה. אתם מנהלים גם דירות שמושכרות עבור הבעלים?  
*Yes, one last question. Do you also manage apartments that are rented out, on behalf of the owners?*

*Behind the scenes: Michael looked up "ניהול נכסים לבעלי דירות" in the service catalogue: ניהול ועד בית, ניהול נכסים לבעלי דירות.*

*Behind the scenes: Michael left a note for the management team (other): "בעל הדירה בבר כוכבא 23 דירה 16 שואל אם הומיז מנהלת דירות מושכרות עבור הבעלים, ומתעניין בשירות ניהול נכסים".*

**Michael:** כן 🙂 יש לנו שירות לבעלי דירות: איתור ובדיקת שוכרים, הכנת חוזה, טיפול בתקלות בנכס ודוחות קבועים לבעלים. עדכנתי את הצוות שאתה מתעניין בזה. יש עוד משהו שאפשר לעזור בו?  
*Yes 🙂 we have a service for apartment owners: finding and vetting tenants, preparing a contract, handling faults in the property and regular reports to the owners. I've updated the team that you're interested in this. Is there anything else I can help with?*

**Resident:** מעולה, תודה רבה מיכאל. המשך ערב נעים!  
*Great, thank you very much Michael. Have a pleasant rest of your evening!*

**Michael:** בשמחה, ותודה שפנית אלינו. ערב נעים גם לך, ובהצלחה עם הדיירים החדשים.  
*My pleasure, and thank you for reaching out to us. A pleasant evening to you too, and good luck with the new tenants.*

**My read:** Smooth:
- His "and you?" got a short answer about Michael, then the help question.
- The change of tenants, the question of who pays the fee, and the form each went to the team.
- The bot said honestly that it has no answer on who pays.
- It described the owner-management service from the real catalogue.

The team got four separate notes from this one chat, which may be a lot to read.

## What this run cannot prove

- **The model.** The bot's side was written by Claude, standing in for the live model (Gemini 2.5 Flash). The code around it is the live code, but the live model's wording will differ. A real phone is the final proof.
- **One player per conversation.** The same player wrote both sides of each conversation. It was told to keep them apart: the resident knew only the card, and the bot knew only what had been typed. Nothing in the 15 shows a leak, but it is not two separate minds.
- **The tools.** The tool results are stand-ins. No real ticket, note or link was made, so a failure inside a real tool would not show here.
- **Not covered:** several messages sent in a quick burst, a staff member taking over a chat, and voice notes.

## The checker's own mistakes (not the bot's)

The automatic checker raised 10 marks. One was real: the link arriving mid-sentence. The other nine come from the checker's own blind spots, and they are left out of the conversations above:

- Conversation 4, Sarah: "a question after the goodbye"; her message opened with "Thank you so much!!" and went on to ask a question, so it was not a goodbye.
- Conversation 12, Liat: "feminine with no cue"; she had written "לא יודעת" ("I don't know", feminine), a cue the checker only knows after "אני".
- Conversation 11, Shimon: "asks how to help after the matter was said"; "are you a person or a computer?" is not a matter, so asking how to help was right.
- Conversation 13, Esther: "feminine with no cue"; she had written "אני מסתדרת" (feminine).
- Conversation 13, Esther: "a question after the goodbye"; her message opened with thanks and went on to the letter.
- Conversation 13, Esther: "a question after the goodbye"; her message opened with thanks and asked for her balance.
- Conversation 14, Dor: "emoji in an emergency"; the smile was in the reply to the button, before anyone mentioned gas.
- Conversation 8, Rachel: "feminine with no cue"; she had written "אני מפחדת" (feminine).
- Conversation 8, Rachel: "a question after the goodbye"; her message opened with thanks and asked why her call was lost.

One expectation failed for the same kind of reason: in conversation 11, the check caught "יתקשרו" ("they will call") inside a sentence that says the bot does not know whether they will. Fixing these in the checker is a separate small job: its list of feminine words, and its test for a goodbye.

## To run it again

```
python scripts/wa_qa.py bundle --run DIR --deck scripts/wa_qa_menu_buttons.json
# one Claude player per scenario reads DIR/PLAYER.md (free residents) and runs
# `python scripts/wa_qa.py turn --run DIR` on every message
python scripts/wa_qa.py grade --run DIR --deck scripts/wa_qa_menu_buttons.json
```
