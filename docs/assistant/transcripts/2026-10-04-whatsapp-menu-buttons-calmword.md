# After the change: 9 conversations on the live bot, 3 per menu button

4 Oct 2026. The owner, on the bot's "איזה מעצבן" ("how annoying") and "אוף" ("ugh"): *"it does not fit the chatbot at all"*, then *"live it and run 3 scenario in each menu button"*. The change went live at 14:53 UTC. These 9 conversations ran on the live code right after it. They reuse the cards from the morning's 15 (`2026-10-04-whatsapp-menu-buttons.md`), mostly the ones where "annoying" came up, so each one has a before and an after.

## What changed on the live bot

One passage of the bot's instructions, about the short word it says before its question:

| | Before | After |
|---|---|---|
| A fault gets | "תגובה קצרה של בן אדם לדבר עצמו, כמו שחבר היה מגיב" (a short human reaction, the way a friend would react) | "תגובה קצרה ואכפתית של בן אדם לדבר עצמו" (a short, caring human reaction) |
| The examples | "אוקיי", "אין בעיה", "איזה מעצבן" (okay, no problem, how annoying) | "אוקיי", "אין בעיה", "אוי, לא נעים" (okay, no problem, oh, that's not nice) |
| Added | | "היא אכפתיות כלפיו ולא עצבים: לא "אוף" ולא "מעצבן", גם כשהוא כועס." (It is care for him, not irritation: no "ugh" and no "annoying", even when he is angry.) |

Every conversation's memory was restarted at the same moment, so no resident's history still shows the old wording to the bot.

## In short

- **"Annoying" and "ugh" are gone.** On these 9 cards the bot said them 6 times before the change and 0 times after, across 62 replies. A blind replay of 27 reaction replies, run before going live, gave 13 under the old wording, 7 under a softer one and 0 under this one.
- **The reaction is now caring.** It reads "אוי, לא נעים" ("oh, that's not nice"), "אוי, חבל" ("oh, too bad"), "זה באמת מלחיץ" ("that really is stressful"), "ברור שזה לא פשוט" ("of course it's not easy"), or nothing at all for a gas smell.
- **Everything else held.** The three buttons' first replies, the tickets, the look-ups, the notes to the team and the honesty are all as before. The bot still cannot change a ticket's urgency: Dalia asked, and the request went to the team.
- **Still waiting on the owner, from the first report, and clearer now:**
  1. **The promise filter.** The sending step cut 4 of these replies: three kind wishes with "בקרוב" ("soon"), and once Michael's honest "I don't know whether or when they'll get back to you". Shimon saw only the next question and wrote "you didn't answer".
  2. **"Anything else?" after a ticket.** It set off the angry man at the gate twice in a row.
  3. **The time standard.** "Up to 3 business days" and "up to 4 hours" got "3 days??", "3 business days??" and "4 hours? it's gas, you can't wait".
  4. **"I can't tell you what to do".** It came back twice: on the gas smell and on the water by the lamp.
  5. **False alarms of the live checks.** Two correct replies were blocked; the rewrites went out. One rewrite dropped the line that the photo went onto the ticket.
- **Nothing was sent and no OpenRouter credit was used.** Claude played both sides on the live code, and the real model's wording will differ. A real phone is the final proof.

## The first reaction, before and after

| # | Resident | Before (old wording) | After (live now) |
|---|---|---|---|
| 1 | Avi, the stuck lift | "אוי, איזה מעצבן." (Oh, how annoying.) | "אוי, לא נעים." (Oh, that's not nice.) |
| 2 | Merav, water by the lamp | "אוי, זה באמת מלחיץ." (Oh, that really is stressful.) | "אוי, זה ממש לא נעים." (Oh, that's really not nice.) |
| 3 | Roni, the gate, angry | "אוף, איזה מעצבן." (Ugh, how annoying.) | "אוי, לא נעים בכלל." (Oh, that's not nice at all.) |
| 4 | Dalia, the leak on her car | "איזה מעצבן." (How annoying.) | "אוי, לא נעים." (Oh, that's not nice.) |
| 5 | Amit, the intercom | "איזה מעצבן, עם משלוח בדרך." (How annoying, with a delivery on the way.) | "אוי, לא נעים שזה בדיוק כשאתה מחכה למשלוח." (Oh, not nice that it's right when you're waiting for a delivery.) |
| 6 | Gilad, resolved but still dark | "איזה מעצבן." (How annoying.) | "אוי, חבל." (Oh, too bad.) |
| 7 | Shimon, the committee | "אוקיי." (Okay.) | "אוי, לא נעים." (Oh, that's not nice.) |
| 8 | Esther, the bill she paid | "אוי, איזה בלבול." (Oh, what a mix-up.), and later "ברור שזה מעצבן." (Of course that's annoying.) | "אוי, לא נעים לקבל מכתב כזה." (Oh, not nice to get a letter like that.), and no "annoying" anywhere |
| 9 | Dor, the gas smell | "אוי, זה מדאיג." (Oh, that's worrying.) | No reaction word: "הצוות כבר יודע על ריח הגז." (The team already knows about the gas smell.) |

## The 9 conversations at a glance

| # | Button | Resident | How it went | Checks met |
|---|---|---|---|---|
| 1 | Open a ticket | Avi, 45, in a hurry | "אוי, לא נעים", then the street, the number and the ticket; quick and clean | 6 of 6 |
| 2 | Open a ticket | Merav, 38, worried | Team told first, ticket, photo; "I can't tell you what to do"; goodbye cut | 7 of 7 |
| 3 | Open a ticket | Roni, 35, angry | No "ugh" now; "anything else?" set him off twice; "3 business days??" | 5 of 5 |
| 4 | Ticket status | Dalia, 52, firm | "אוי, לא נעים"; asked to mark it urgent: passed to the team, not changed | 7 of 7 |
| 5 | Ticket status | Amit, 28, slang | Asked his flat, not the neighbours' tickets; "3 days?"; goodbye cut | 7 of 7 |
| 6 | Ticket status | Gilad, 41, sarcastic | "אוי, חבל"; a new ticket naming the old one; his questions to the team | 5 of 5 |
| 7 | Talk to a rep | Shimon, 58, suspicious | "A digital representative"; his "when?" answer cut, so "you didn't answer" | 6 of 7 |
| 8 | Talk to a rep | Esther, 74, very polite | Warm; the bill to the team; the balance read with her cheque mentioned | 7 of 7 |
| 9 | Talk to a rep | Dor, 25, no small talk | Team first, emergency ticket; "I can't tell you"; "4 hours? it's gas" | 6 of 6 |

## How it was run

- **Same harness as the morning run.** Each resident said hello, tapped a button, and from then on a Claude player was that person, reacting only to what the phone showed. Every message went through the live workflow's own code, fetched read-only after the change.
- **Tool results.** They were stand-ins in the real tools' shapes; nothing was looked up, opened or sent.
- **One correction to the harness, found here.** In the gas conversation a blocked draft was rewritten, and the rewrite called the ticket tool again. The stand-in handed out a second ticket number (255-1518-26). The real ticket service returns the same number when the same kind of fault in the same building is reported again within 30 minutes, so Dor would have seen 255-1517-26 again. The stand-in rule is fixed for future runs.

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

**Michael:** כאן מיכאל מהומי'ז, הגעת למקום הנכון ואני איתך 🙂 ספר לי, מה קרה?  
*Michael from Homies here, you've come to the right place and I'm with you 🙂 Tell me, what happened?*

**Resident:** המעלת תקועה בקומה 4 הדלת פתוחה  
*the lft is stuck on floor 4 the door is open*

**Michael:** אוי, לא נעים. באיזה בניין זה ובאיזו דירה אתה גר?  
*Oh, that's unpleasant. Which building is it, and which apartment do you live in?*

**Resident:** בר כוכבא דירה 9  
*Bar Kochba apartment 9*

*Behind the scenes: Michael tried to open a ticket with the building "בר כוכבא"; nothing was opened, because it needs the building number.*

**Michael:** מה מספר הבניין בבר כוכבא?  
*What's the building number on Bar Kochba?*

**Resident:** 23  
*23*

*Behind the scenes: Michael opened ticket 255-1510-26 (elevator, high urgency, fault in the common areas; filed under apartment 9): "המעלית תקועה בקומה 4 והדלת פתוחה".*

**Michael:** פתחתי את הקריאה, המספר שלה 255-1510-26. אפשר לעזור לך בעוד משהו?  
*I opened the ticket, its number is 255-1510-26. Can I help you with anything else?*

**Resident:** תודה  
*Thanks*

**Michael:** בשמחה, תודה שפנית 🙂 שיהיה לך יום מצוין.  
*My pleasure, thanks for getting in touch 🙂 Have a great day.*

**My read:** The reaction that was "אוי, איזה מעצבן" is now "אוי, לא נעים". He gave the street without a number, so the ticket tool asked for it, and the bot asked one short question. The ticket was opened and the goodbye was warm.

### 2. Open a ticket: water through the bathroom ceiling, a worried woman with a photo

**Button:** פתיחת קריאת שירות (open a service ticket). **Sunday 13:30, Israel time.**

**The resident's card** (all the player had): מירב, 38. Stressed and talkative: long messages with several details at once. Writes about herself in the feminine (אני לא יודעת, אני צריכה, אני בטוחה). Lives at בר כוכבא 23, apartment 7, second floor. Since this morning water has been dripping from her bathroom ceiling near the lamp. She thinks it comes from the flat above, apartment 11, where nobody answers the door. She has a photo of the wet ceiling on her phone. **Wants:** Someone to stop the leak, and someone to get hold of the upstairs neighbours. **May:** May send the photo with no caption. May ask whether Homies can talk to the upstairs neighbours or give her their number. May worry aloud about the electricity, because the water is near the lamp.

**Resident:** שלום  
*Hello*

**System (fixed menu, three buttons):** צהריים טובים 👋 במה אפשר לעזור?  
*Good afternoon 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** פתיחת קריאת שירות  
*(taps "Open a service ticket")*

**Michael:** כאן מיכאל מהומי'ז, הגעת למקום הנכון ואני איתך. ספר לי, מה קרה? 🙂  
*This is Michael from Homies, you've come to the right place and I'm with you. Tell me, what happened? 🙂*

**Resident:** תודה, אני ממש לחוצה. מהבוקר מטפטפים לי מים מהתקרה באמבטיה, ממש ליד המנורה. אני חושבת שזה מהדירה שמעליי, דירה 11, דפקתי להם בדלת ואף אחד לא עונה. אני לא יודעת מה לעשות  
*Thanks, I'm really stressed. Since this morning water has been dripping on me from the ceiling in the bathroom, right next to the lamp. I think it's from the apartment above me, apartment 11, I knocked on their door and nobody answers. I don't know what to do*

*Behind the scenes: Michael left a note for the operations team (emergency): "מהבוקר מטפטפים לה מים מהתקרה באמבטיה, ממש ליד המנורה. היא חושבת שזה מהדירה שמעליה, דירה 11, ואף אחד לא עונה לה בדלת. עוד לא נמסרו הבניין והדירה שלה".*

**Michael:** אוי, זה ממש לא נעים. הצוות כבר יודע על זה. באיזה בניין ובאיזו דירה את גרה?  
*Oh, that's really unpleasant. The team already knows about it. Which building and which apartment do you live in?*

**Resident:** בר כוכבא 23, דירה 7, קומה שנייה. אני מפחדת מהחשמל, זה מטפטף ליד המנורה, זה לא מסוכן? ומישהו יכול לבוא היום?  
*Bar Kochba 23, apartment 7, second floor. I'm afraid of the electricity, it's dripping near the lamp, isn't that dangerous? And can someone come today?*

*Behind the scenes: Michael opened ticket 255-1511-26 (plumbing, high urgency, fault in the flat; filed under apartment 7): "מהבוקר מטפטפים מים מהתקרה באמבטיה, ממש ליד המנורה. נראה לה שזה מהדירה שמעליה, דירה 11, ואף אחד לא עונה שם בדלת. קומה 2".*

**Michael:** פתחתי לך קריאה, מספר 255-1511-26, והצוות יודע שזה מטפטף ליד המנורה. אם זה מסוכן ואם מישהו יכול להגיע היום, אין לי על זה מידע ואני לא רוצה לנחש. יש עוד משהו שאפשר לעזור בו?  
*I've opened a request for you, number 255-1511-26, and the team knows it's dripping near the lamp. Whether it's dangerous and whether someone can come today, I have no information on that and I don't want to guess. Is there anything else I can help with?*

**Resident:** מה זאת אומרת אין לך מידע? המים מטפטפים ליד חשמל, אני פוחדת שיהיה קצר ואני לא יודעת מה לעשות עד שמישהו יגיע. ועוד משהו, אפשר שמישהו מכם ידבר עם השכנים מלמעלה? דירה 11, הם לא פותחים לי. או שתוכל לתת לי טלפון שלהם  
*What do you mean you have no information? The water is dripping near electricity, I'm afraid there will be a short circuit and I don't know what to do until someone comes. And one more thing, can someone from you talk to the neighbours upstairs? Apartment 11, they don't open for me. Or can you give me their phone number*

*Behind the scenes: Michael left a note for the operations team (other): "הדיירת מדירה 7 מבקשת שמישהו מהומי'ז ידבר עם השכנים מדירה 11 שמעליה, כי הם לא פותחים לה את הדלת והמים מטפטפים אצלה מהתקרה באמבטיה ליד המנורה. היא ביקשה גם את הטלפון שלהם. קריאה 255-1511-26".*

**Michael:** זה באמת מלחיץ, ומה לעשות בינתיים אני לא יכול להגיד לך. מה שכן, העברתי לצוות גם את הבקשה שידברו עם השכנים מלמעלה. את הטלפון שלהם אני לא יכול למסור, אני לא מוסר פרטים של דיירים אחרים. יש עוד משהו שאפשר לעזור בו?  
*That really is stressful, and what to do in the meantime I can't tell you. What I did do is also pass on to the team the request that they talk to the neighbours upstairs. I can't give you their phone number, I don't give out details of other residents. Is there anything else I can help with?*

**Resident sends a photo**, no caption  
*(A photo with no caption: the wet bathroom ceiling)*

> Michael's first draft was blocked by the live checks (it said something was done that no tool did), so it never reached the phone:  
> תודה, קיבלתי את התמונה והיא צורפה לקריאה שפתחתי. אם יש עוד משהו, אני כאן.  
> *Thanks, I received the photo and it was attached to the request I opened. If there's anything else, I'm here.*  
> The live bot then wrote again:

**Michael:** תודה ששלחת את התמונה. אם משהו משתנה או יש עוד משהו, כתבי לי כאן.  
*Thanks for sending the photo. If something changes or there's anything else, write to me here.*

> The blocked draft had told her the photo was attached to her ticket. The rewrite dropped that, so she was not told where her photo went.

**Resident:** אוקיי. אפשר להגיד להם שזה דחוף? זה ממש ליד המנורה ואני לא רגועה בכלל  
*Okay. Can you tell them it's urgent? It's right next to the lamp and I'm not calm at all*

**Michael:** ברור שזה לא פשוט. הצוות כבר יודע שזה ליד המנורה, את זה העברתי להם מההתחלה.  
*Of course it's not simple. The team already knows it's near the lamp, I passed that on to them from the start.*

**Resident:** אוקיי תודה רבה מיכאל, מקווה שיבואו מהר  
*Okay thank you very much Michael, I hope they come quickly*

**Michael:** תודה שפנית אליי.  
*Thanks for reaching out to me.*

> The bot wrote "תודה שפנית אליי. מקווה שזה יסתדר בקרוב ושתוכלי להירגע." ("Thanks for reaching out to me. I hope it gets sorted out soon and that you can calm down."). The sending step cut the second sentence, because of "בקרוב" ("soon").

**My read:** Kind and correct:
- The team was told first.
- The ticket went on her flat.
- The neighbours' number was refused.
- Asked whether it is dangerous, the bot said honestly that it does not know and will not guess.

Three catches, none from this change:
- "What to do in the meantime I can't tell you" (finding 4 above).
- A false alarm blocked the reply to her photo, and the rewrite dropped the line that the photo went onto her ticket.
- The goodbye wish was cut by the promise filter, because of "בקרוב".

### 3. Open a ticket: the parking gate again, an angry man stuck outside at night

**Button:** פתיחת קריאת שירות (open a service ticket). **Sunday 21:40, Israel time.**

**The resident's card** (all the player had): רוני, 35. Angry and tired after a long day: short bursts, !!, a few harsh words (נמאס לי, מה אתם עושים בכלל), no swearing. Lives at בר כוכבא 23, apartment 14. The parking gate does not open with his remote; he is sitting in his car outside. It is the third time this month, and he reported it twice before (once by phone, once here). He has no ticket numbers. **Wants:** The gate fixed for good, and to be taken seriously. **May:** May ask what happened to his earlier reports. May ask אתה בוט? if a reply sounds canned. Calms down a little if he feels heard; gets angrier at anything that sounds like a template.

**Resident:** שלום  
*Hello*

**System (fixed menu, three buttons):** ערב טוב 👋 במה אפשר לעזור?  
*Good evening 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** פתיחת קריאת שירות  
*(taps "Open a service ticket")*

**Michael:** כאן מיכאל מהומי'ז, ואתה במקום הנכון, אני איתך 🙂 / ספר לי מה קרה?  
*This is Michael from Homies, and you're in the right place, I'm with you 🙂 / Tell me what happened?*

**Resident:** השער של החניה לא נפתח עם השלט!! שוב!! אני תקוע בחוץ ברכב, זו כבר פעם שלישית החודש  
*The parking gate won't open with the remote!! Again!! I'm stuck outside in the car, this is already the third time this month*

**Michael:** אוי, לא נעים בכלל. באיזה בניין ובאיזו דירה אתה גר?  
*Oh, that's not pleasant at all. Which building and which apartment do you live in?*

**Resident:** בר כוכבא 23 דירה 14. נמאס לי כבר מהשער הזה!!  
*Bar Kochba 23 apartment 14. I'm so sick of this gate already!!*

*Behind the scenes: Michael opened ticket 255-1514-26 (maintenance, high urgency, fault in the common areas; filed under apartment 14): "שער החניה לא נפתח עם השלט, הדייר תקוע בחוץ ברכב, זו כבר פעם שלישית החודש".*

**Michael:** פתחתי קריאה על השער של החניה, מספר 255-1514-26. מצטער שזה קורה שוב. אפשר לעזור לך בעוד משהו?  
*I opened a ticket for the parking gate, number 255-1514-26. Sorry this is happening again. Can I help you with anything else?*

**Resident:** עוד משהו?? אני תקוע בחוץ!! ומה קרה עם שני הדיווחים הקודמים שלי? מה אתם עושים בכלל  
*Anything else?? I'm stuck outside!! And what happened with my two previous reports? What do you even do?*

*Behind the scenes: Michael looked up the ticket by building בר כוכבא 23: 255-1466-26 resolved (שער החניה לא נפתח עם השלט).*

**Michael:** זה באמת לא פשוט, ועוד כשאתה תקוע בחוץ. אצלנו מופיעה קריאה אחת על השער, מה-21 בספטמבר (255-1466-26), והיא מסומנת כנפתרה, עם עדכון אחרון ב-24. בקריאה החדשה רשמתי שזו כבר הפעם השלישית החודש. יש משהו נוסף שאפשר לעשות בשבילך?  
*That's really not easy, especially when you're stuck outside. On our side one ticket about the gate shows up, from September 21 (255-1466-26), and it's marked as resolved, with the last update on the 24th. In the new ticket I wrote that this is already the third time this month. Is there anything more I can do for you?*

Automatic checks on this reply: parentheses ("ת על השער, מה-21 בספטמבר (255-1466-26), והיא מסומנת").

**Resident:** נפתרה?? השער סגור עכשיו!! לא צריך עוד משהו, צריך שיתקנו אותו סופית  
*Resolved?? The gate is closed right now!! Don't need anything else, need them to fix it for good*

*Behind the scenes: Michael left a note for the operations team (other): "הדייר מבקש שיתקנו את שער החניה בבר כוכבא 23 סופית. השער לא נפתח עם השלט, הוא תקוע בחוץ ברכב, זו כבר פעם שלישית החודש. הקריאה הקודמת 255-1466-26 מסומנת כנפתרה והתקלה חזרה. נפתחה קריאה חדשה 255-1514-26".*

**Michael:** אם השער סגור עכשיו, אז 'נפתרה' ממש לא מתאר את המצב. עדכנתי את הצוות שהתקלה חוזרת, שזו הפעם השלישית החודש ושאתה מבקש תיקון סופי. יש משהו אחר שאפשר לעזור לך בו?  
*If the gate is closed right now, then 'resolved' really doesn't describe the situation. I updated the team that the fault is recurring, that this is the third time this month, and that you're asking for a final fix. Is there something else I can help you with?*

**Resident:** אמרתי שלא צריך עוד משהו!! מתי מישהו מגיע?? אני יושב פה ברכב  
*I said I don't need anything else!! When is someone coming?? I'm sitting here in the car*

**Michael:** סליחה, צודק. מתי מישהו מגיע אני לא יודע להגיד לך, ואני לא רוצה לתת לך זמן שאין לי. הסטנדרט הכללי לתקלה שאינה חירום הוא עד 3 ימי עסקים, אבל זו לא הבטחה על הקריאה הזאת.  
*Sorry, you're right. When someone is coming, I can't tell you, and I don't want to give you a time I don't have. The general standard for a fault that isn't an emergency is up to 3 business days, but that's not a promise about this ticket.*

**Resident:** 3 ימי עסקים?? אני צריך להיכנס לחניה עכשיו!!  
*3 business days?? I need to get into the parking lot right now!!*

**Michael:** הלוואי שהייתי יכול לפתוח לך את השער עכשיו. אני יכול רק לפתוח קריאה ולעדכן את הצוות, וזה כבר נעשה.  
*I wish I could open the gate for you right now. All I can do is open a ticket and update the team, and that's already been done.*

**Resident:** טוב. רק שיתקנו אותו באמת הפעם. אני לא רוצה לדווח על זה שוב  
*Fine. Just that they fix it for real this time. I don't want to report this again*

**Michael:** את זה אני לא יכול להבטיח, מה שקורה אצל הצוות לא בידיים שלי. כתבתי להם במפורש שאתה רוצה תיקון סופי. מקווה שתסתדר הערב.  
*That I can't promise, what happens with the team isn't in my hands. I wrote to them explicitly that you want a final fix. I hope you'll manage this evening.*

**My read:** No "ugh" and no "annoying". The reaction is "אוי, לא נעים בכלל", and later "זה באמת לא פשוט, ועוד כשאתה תקוע בחוץ". But the stock "anything else?" set him off twice in a row: "עוד משהו?? אני תקוע בחוץ!!", then "אמרתי שלא צריך עוד משהו!!". "Up to 3 business days" got "3 ימי עסקים??". The bot apologised ("סליחה, צודק"), stayed honest and promised nothing.

### 4. Status: she has the number, typed with spaces; it drips on her car

**Button:** מצב קריאה קיימת (status of an existing ticket). **Sunday 09:20, Israel time.**

**The resident's card** (all the player had): דליה, 52. Organized, polite but firm; full sentences. Writes about herself in the feminine (אני רוצה לדעת, אני מבינה). Lives at בר כוכבא 23, apartment 6. A week ago she reported a leak in the car park that drips onto her parking space, number 6, and she kept the ticket number from the reply. She types it as 255 1501 26 (spaces, no hyphens). **Wants:** To know when it will be fixed; it drips on her car every day. **May:** Asks when they will come and finish. May ask Michael to push it or mark it urgent.

**Resident:** בוקר טוב  
*Good morning*

**System (fixed menu, three buttons):** בוקר טוב 👋 במה אפשר לעזור?  
*Good morning 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** מצב קריאה קיימת  
*(taps "Status of an existing ticket")*

**Michael:** כאן מיכאל מהומי'ז, אני איתך על זה 🙂 מה מספר הקריאה?  
*This is Michael from Homies, I'm with you on this 🙂 What's the ticket number?*

**Resident:** המספר הוא 255 1501 26  
*The number is 255 1501 26*

*Behind the scenes: Michael looked up the ticket by reference 255 1501 26: 255-1501-26 in_progress (נזילה בחניון, מטפטף על חניה 6).*

**Michael:** הקריאה 255-1501-26 על הנזילה בחניון נמצאת בטיפול. נפתחה ב-27 בספטמבר ועודכנה לאחרונה ב-1 באוקטובר. יש עוד משהו שאפשר לעזור בו?  
*Ticket 255-1501-26, about the leak in the car park, is being handled. It was opened on 27 September and last updated on 1 October. Is there anything else I can help with?*

**Resident:** אני מבינה שזה בטיפול, אבל מתי זה יתוקן? עבר שבוע וזה מטפטף לי על האוטו כל יום.  
*I understand it's being handled, but when will it be fixed? A week has passed and it drips on my car every day.*

*Behind the scenes: Michael left a note for the operations team (other): "מבררת מתי תתוקן הקריאה 255-1501-26 (נזילה בחניון, מטפטף על חניה 6). עבר שבוע וזה ממשיך לטפטף לה על האוטו כל יום".*

**Michael:** אוי, לא נעים. אין לי כרגע תאריך לתיקון, אבל הצוות יודע שעבר שבוע ושזה ממשיך לטפטף על האוטו שלך כל יום. במה עוד אפשר לעזור?  
*Oh, that's not nice. I don't have a date for the repair right now, but the team knows that a week has passed and that it keeps dripping on your car every day. What else can I help with?*

**Resident:** שבוע זה הרבה זמן, והאוטו שלי כבר סובל מזה. אפשר בבקשה לסמן את הקריאה כדחופה?  
*A week is a long time, and my car is already suffering from it. Can you please mark the ticket as urgent?*

*Behind the scenes: Michael left a note for the operations team (other): "מבקשת שהקריאה 255-1501-26 תסומן כדחופה. עבר שבוע והאוטו שלה סובל מהטפטוף בחניה 6".*

**Michael:** את הסימון עצמו אני לא יכול לעשות מכאן, אבל הצוות יודע עכשיו שאת מבקשת שהקריאה תטופל בדחיפות. יש משהו נוסף שאפשר לעשות בשבילך?  
*I can't do the marking itself from here, but the team now knows that you are asking for the ticket to be handled urgently. Is there anything else I can do for you?*

**Resident:** בסדר, תודה. אני מקווה שיטפלו בזה כבר היום, זה לא יכול להימשך ככה.  
*Okay, thanks. I hope they'll deal with it today, it can't go on like this.*

**Michael:** תודה שפנית אלינו, ושיהיה לך המשך יום טוב 🙂  
*Thanks for contacting us, and have a good rest of your day 🙂*

**My read:** "איזה מעצבן" became "אוי, לא נעים". The number typed with spaces was found, and the team was told the leak keeps dripping on her car. Asked to mark the ticket urgent, the bot said it cannot change that and passed the request to the team, which is what the owner wants.

### 5. Status: no number, a young man who writes slang; the intercom

**Button:** מצב קריאה קיימת (status of an existing ticket). **Sunday 12:45, Israel time.**

**The resident's card** (all the player had): עמית, 28. Laid-back; writes slang (אחי, סבבה, וואלה), no punctuation, short lines. Lives at בר כוכבא 23, apartment 10. A few days ago he reported here that the intercom at the entrance does not ring in his flat. He did not save the ticket number. **Wants:** To know if someone is coming to fix the intercom; he is expecting a delivery. **May:** Answers with the building but forgets the apartment, or the other way round. May ask whether someone is coming today.

**Resident:** הי  
*Hi*

**System (fixed menu, three buttons):** צהריים טובים 👋 במה אפשר לעזור?  
*Good afternoon 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** מצב קריאה קיימת  
*(taps "Status of an existing ticket")*

**Michael:** כאן מיכאל מהומי'ז 🙂 אשמח לעזור לך עם הקריאה. באיזה בניין מדובר?  
*This is Michael from Homies 🙂 I'd be happy to help you with the request. Which building is this about?*

**Resident:** בר כוכבא 23 אחי  
*Bar Kochba 23 bro*

*Behind the scenes: Michael looked up the ticket by building בר כוכבא 23: 3 tickets in the building, no descriptions (it has to ask which).*

**Michael:** אוקיי, יש כמה קריאות בבניין. באיזו דירה אתה גר?  
*Okay, there are a few requests in the building. Which apartment do you live in?*

**Resident:** דירה 10  
*Apartment 10*

*Behind the scenes: Michael looked up the ticket by building בר כוכבא 23, unit 10: 255-1486-26 open (האינטרקום בכניסה לא מצלצל בדירה 10).*

**Michael:** מצאתי את הקריאה על האינטרקום שלא מצלצל בדירה, מספר 255-1486-26. היא נפתחה ב-1 באוקטובר וכרגע היא פתוחה. אפשר לעזור בעוד משהו?  
*I found the request about the intercom that doesn't ring in the apartment, number 255-1486-26. It was opened on October 1 and is currently open. Can I help with anything else?*

**Resident:** וואלה מישהו מגיע היום לתקן? מחכה למשלוח  
*Wallah, is someone coming today to fix it? Waiting for a delivery*

**Michael:** אוי, לא נעים שזה בדיוק כשאתה מחכה למשלוח. אין לי כרגע מידע אם מישהו מגיע היום. הסטנדרט שלנו לתקלה שאינה חירום הוא עד שלושה ימי עסקים, אבל זו לא הבטחה על הקריאה הזאת. אפשר לעזור בעוד משהו?  
*Oh, not nice that it's happening right when you're waiting for a delivery. I don't have any information right now on whether someone is coming today. Our standard for a fault that isn't an emergency is up to three business days, but that's not a promise about this request. Can I help with anything else?*

**Resident:** 3 ימים? אחי המשלוח אמור להגיע היום  
*3 days? Bro, the delivery is supposed to arrive today*

*Behind the scenes: Michael left a note for the operations team (other): "הדייר מחכה היום למשלוח, והאינטרקום בכניסה עדיין לא מצלצל בדירה 10 בבר כוכבא 23 (קריאה 255-1486-26). שואל אם מישהו מגיע היום לתקן".*

**Michael:** הצוות יודע עכשיו שהאינטרקום עדיין לא מצלצל ושאתה מחכה היום למשלוח. אפשר לעזור בעוד משהו?  
*The team now knows that the intercom still doesn't ring and that you're waiting for a delivery today. Can I help with anything else?*

**Resident:** סבבה תודה  
*Cool, thanks*

**Michael:** בשמחה, ותודה שפנית.  
*Gladly, and thanks for reaching out.*

> The bot wrote "בשמחה, ותודה שפנית. שהמשלוח יגיע בקרוב והמשך יום נעים 🙂" ("Gladly, and thanks for reaching out. May the delivery arrive soon, and have a pleasant rest of the day 🙂"). The sending step cut everything after the first sentence, because of "בקרוב" ("soon").

**My read:** "איזה מעצבן" became "אוי, לא נעים שזה בדיוק כשאתה מחכה למשלוח". Given only the building, the bot asked his flat instead of reading out the neighbours' tickets. "Up to three business days" got "3 days? the delivery is today", and the team was told. The goodbye wish was cut by the promise filter, because of "בקרוב".

### 6. Status: marked resolved, still dark; a sarcastic man

**Button:** מצב קריאה קיימת (status of an existing ticket). **Sunday 18:05, Israel time.**

**The resident's card** (all the player had): גלעד, 41. Matter-of-fact and a little sarcastic; short sentences with punctuation. Lives at בר כוכבא 23, apartment 8. He has the ticket number 255-1460-26, for the stairwell light on floor 3. On Friday he got word it was handled, but the light is still off; he checked tonight. **Wants:** The light actually fixed, not a ticket closed on paper. **May:** Sarcastic about 'handled'. Will not accept being told it is resolved. May ask who checked it.

**Resident:** ערב טוב  
*Good evening*

**System (fixed menu, three buttons):** ערב טוב 👋 במה אפשר לעזור?  
*Good evening 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** מצב קריאה קיימת  
*(taps "Status of an existing ticket")*

**Michael:** כאן מיכאל מהומי'ז, אני איתך על זה 🙂 מה מספר הקריאה, או באיזה בניין היא נפתחה?  
*Michael here from Homies, I'm with you on this 🙂 What's the ticket number, or in which building was it opened?*

**Resident:** 255-1460-26. האור בחדר מדרגות, קומה 3.  
*255-1460-26. The light in the stairwell, floor 3.*

*Behind the scenes: Michael looked up the ticket by reference 255-1460-26, type lighting: 255-1460-26 resolved (התאורה בחדר המדרגות בקומה 3 לא עובדת).*

**Michael:** הקריאה 255-1460-26 על התאורה בחדר המדרגות בקומה 3 מסומנת אצלנו כנפתרה, והעדכון האחרון בה היה ב-2 באוקטובר. אפשר לעזור בעוד משהו?  
*Ticket 255-1460-26 about the lighting in the stairwell on floor 3 is marked with us as resolved, and the last update on it was on 2 October. Can I help with anything else?*

**Resident:** נפתרה, מעולה. רק שהאור עדיין כבוי. בדקתי הערב.  
*Resolved, great. Only the light is still off. I checked tonight.*

**Michael:** אוי, חבל. באיזה בניין ובאיזו דירה אתה גר?  
*Oh, too bad. In which building and which apartment do you live?*

**Resident:** בר כוכבא 23, דירה 8.  
*Bar Kochba 23, apartment 8.*

*Behind the scenes: Michael opened ticket 255-1516-26 (lighting, normal urgency, fault in the common areas; filed under apartment 8): "האור בחדר המדרגות בקומה 3 עדיין לא עובד. הקריאה הקודמת על זה, 255-1460-26, סומנה כנפתרה, אבל הדייר בדק הערב והתאורה עדיין כבויה".*

**Michael:** פתחתי קריאה חדשה על האור בחדר המדרגות בקומה 3 בבר כוכבא 23, ומספר הקריאה הוא 255-1516-26. אפשר לעזור בעוד משהו?  
*I opened a new ticket about the light in the stairwell on floor 3 at Bar Kochba 23, and the ticket number is 255-1516-26. Can I help with anything else?*

**Resident:** קריאה חדשה. נהדר. ומי בדק את הקודמת לפני שסגרו אותה?  
*A new ticket. Wonderful. And who checked the previous one before they closed it?*

*Behind the scenes: Michael left a note for the operations team (other): "הדייר שואל מי בדק את קריאה 255-1460-26 לפני שנסגרה כנפתרה. האור בחדר המדרגות בקומה 3 בבר כוכבא 23 עדיין כבוי, ונפתחה קריאה חדשה 255-1516-26".*

**Michael:** את זה אין לי כרגע. עדכנתי את הצוות שהאור עדיין כבוי ושאלת מי בדק את הקריאה הקודמת. אפשר לעזור בעוד משהו?  
*I don't have that right now. I've updated the team that the light is still off and that you asked who checked the previous ticket. Can I help with anything else?*

**Resident:** לא. רק שהאור יידלק באמת, לא על הנייר. תוך כמה זמן?  
*No. Only that the light actually comes on, not on paper. How long will it take?*

**Michael:** הסטנדרט אצלנו לתקלה שאינה חירום הוא עד 3 ימי עסקים, אבל זה סטנדרט כללי ולא הבטחה על הקריאה הזאת, ומתי בדיוק היא תטופל אני לא יודע. ואם משהו נוסף יעלה, אני כאן.  
*Our standard for a non-emergency fault is up to 3 business days, but that is a general standard and not a promise about this ticket, and exactly when it will be handled I don't know. And if anything else comes up, I'm here.*

**Resident:** בסדר. רק תוודאו שהפעם מישהו בודק שהאור באמת נדלק לפני שסוגרים.  
*Fine. Just make sure that this time someone checks that the light really comes on before you close it.*

*Behind the scenes: Michael left a note for the operations team (other): "הדייר מבקש שלפני שסוגרים את הקריאה החדשה 255-1516-26 מישהו יבדוק בפועל שהאור בחדר המדרגות בקומה 3 בבר כוכבא 23 נדלק. הקריאה הקודמת 255-1460-26 נסגרה והאור נשאר כבוי".*

**Michael:** העברתי לצוות את הבקשה שלך, שיוודאו שהאור באמת נדלק לפני שסוגרים את הקריאה. יש עוד משהו שאפשר לעזור בו?  
*I passed your request on to the team, that they make sure the light really comes on before the ticket is closed. Is there anything else I can help with?*

**Resident:** לא, זה הכול. תודה. נראה.  
*No, that's all. Thanks. We'll see.*

**Michael:** תודה שפנית אליי. שיהיה לך ערב נעים.  
*Thanks for reaching out to me. Have a pleasant evening.*

**My read:** "איזה מעצבן" became "אוי, חבל". The old ticket was marked resolved, so the bot opened a new one that names it. His two questions went to the team: who checked the old ticket, and that someone should check the light before closing the new one.

### 7. Talk to a rep: 'are you a person or a computer?', then a committee decision

**Button:** לדבר עם נציג (talk to a representative). **Sunday 10:05, Israel time.**

**The resident's card** (all the player had): שמעון, 58. Suspicious of bots and of companies; terse and a little confrontational, not rude. Lives at בר כוכבא 23, apartment 11. Full name שמעון אברהם. The house committee decided on a lobby renovation without asking him; he wants the meeting's minutes and to object. **Wants:** To talk to a real person at Homies about the renovation decision. **May:** First asks whether he is talking to a person or a computer (אתה בן אדם או מחשב?). Insists on a real person. If told the team will get a note, asks when they will call him.

**Resident:** שלום  
*Hello*

**System (fixed menu, three buttons):** בוקר טוב 👋 במה אפשר לעזור?  
*Good morning 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** לדבר עם נציג  
*(taps "Talk to a representative")*

**Michael:** היי, כאן מיכאל מהומי'ז 🙂 מה שלומך היום?  
*Hi, Michael from Homies here 🙂 How are you today?*

**Resident:** אתה בן אדם או מחשב?  
*Are you a person or a computer?*

**Michael:** אני נציג דיגיטלי של הומי'ז, לא בן אדם. על מה רצית לדבר?  
*I'm a digital representative of Homies, not a person. What did you want to talk about?*

**Resident:** אז אני רוצה בן אדם אמיתי. לא מחשב  
*So I want a real person. Not a computer*

*Behind the scenes: Michael left a note for the service team (caller_request): "הדייר מבקש לדבר עם בן אדם אמיתי ולא עם מחשב".*

**Michael:** אין בעיה, הצוות יודע שאתה מבקש לדבר עם בן אדם. במה עוד אפשר לעזור?  
*No problem, the team knows you're asking to speak with a person. What else can I help with?*

**Resident:** כלום. מתי יתקשרו אלי?  
*Nothing. When will they call me?*

**Michael:** על מה תרצה לדבר איתם?  
*What would you like to talk to them about?*

> The bot wrote "אם ומתי יחזרו אליך אני לא יודע, ואני לא רוצה להבטיח. על מה תרצה לדבר איתם?" ("Whether and when they'll get back to you I don't know, and I don't want to promise. What would you like to talk to them about?"). The sending step cut the honest first sentence, because "יחזרו אליך" ("will get back to you") is on its promise list, though the sentence promises nothing. His next message: "you didn't answer, when will they call me?"

**Resident:** על שיפוץ הלובי שהוועד החליט בלי לשאול אותי. ולא ענית, מתי יתקשרו אלי?  
*About the lobby renovation that the committee decided on without asking me. And you didn't answer, when will they call me?*

*Behind the scenes: Michael left a note for the management team (other): "הדייר מספר שהוועד החליט על שיפוץ הלובי בלי לשאול אותו, ורוצה לדבר עם בן אדם על זה".*

**Michael:** אוי, לא נעים. אין לי כרגע מידע על מתי. רשמתי לצוות גם את העניין של שיפוץ הלובי, שהוועד החליט עליו בלי לשאול אותך. יש עוד משהו שחשוב לך שידעו?  
*Oh, that's unpleasant. I don't have any information right now about when. I've also noted to the team the matter of the lobby renovation, which the committee decided on without asking you. Is there anything else that's important to you that they know?*

**Resident:** כן. אני רוצה את הפרוטוקול של הישיבה, ואני מתנגד להחלטה. שיתקשרו אלי היום  
*Yes. I want the minutes of the meeting, and I object to the decision. Have them call me today*

*Behind the scenes: Michael left a note for the management team (other): "הדייר רוצה את הפרוטוקול של ישיבת הוועד שבה הוחלט על שיפוץ הלובי, מתנגד להחלטה, ומבקש שיתקשרו אליו היום".*

**Michael:** רשמתי לצוות שאתה רוצה את הפרוטוקול של הישיבה, שאתה מתנגד להחלטה, ושביקשת שיתקשרו אליך היום. היום אני לא יכול להבטיח. אפשר לעזור בעוד משהו?  
*I've noted to the team that you want the minutes of the meeting, that you object to the decision, and that you asked them to call you today. Today I can't promise. Can I help with anything else?*

**Resident:** אז איך אני מגיע לבן אדם אמיתי? לא רוצה לחכות  
*So how do I reach a real person? I don't want to wait*

**Michael:** בטח, הטלפון של המשרד הוא <phone>. הוא פתוח היום עד 17:00. יש עוד משהו שאפשר לעזור בו?  
*Sure, the office phone is <phone>. It's open today until 17:00. Is there anything else I can help with?*

**Resident:** לא. אתקשר אליהם. תודה  
*No. I'll call them. Thanks*

**Michael:** תודה שפנית אליי, ושיהיה לך המשך יום טוב.  
*Thanks for reaching out to me, and have a good rest of your day.*

**Check not met:** no transfer, no call-back promise. This is the check's own mistake: it caught "שיתקשרו" inside "ושביקשת שיתקשרו אליך היום" ("and that you asked them to call you today"), which reports his request and promises nothing.

**My read:** Honest about being a digital representative. Asked when they would call, the bot wrote "whether and when they'll get back to you I don't know, and I don't want to promise". The sending step cut that sentence, because "יחזרו אליך" is on its promise list. He saw only "what would you like to talk to them about?" and wrote "you didn't answer". When he asked how to reach a real person, the bot gave the office phone and hours, which answers what he asked.

### 8. Talk to a rep: an elderly woman says she already paid by cheque

**Button:** לדבר עם נציג (talk to a representative). **Sunday 17:20, Israel time.**

**The resident's card** (all the player had): אסתר, 74. Very polite and warm: long messages that start with שלום רב and carry blessings (ברוך השם, תהיה בריא). Slow with the phone. Writes about herself in the feminine. Lives at בר כוכבא 23, apartment 5. Full name אסתר מזרחי, phone <phone>. She got a letter saying she owes 900 ₪ for July to September, but she paid by cheque in July to משה from the house committee. **Wants:** The debt taken off; she paid. **May:** Answers how-are-you at length (her knee, the grandchildren). Asks Michael to check how much she owes. Repeats that she paid.

**Resident:** שלום רב  
*Hello (formal greeting)*

**System (fixed menu, three buttons):** ערב טוב 👋 במה אפשר לעזור?  
*Good evening 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** לדבר עם נציג  
*(taps "Talk to a representative")*

**Michael:** היי, כאן מיכאל מהומי'ז 🙂 מה שלומך היום?  
*Hi, this is Michael from Homies 🙂 How are you today?*

**Resident:** שלום רב מיכאל, ברוך השם אני בסדר גמור תודה ששאלת. רק הברך שלי קצת מציקה בימים האחרונים אבל מה לעשות זה הגיל. הנכדים באו אליי בשבת ברוך השם והיה לי שמח בבית. אני רציתי לדבר איתכם על מכתב שקיבלתי. תהיה בריא  
*Hello Michael, thank God I'm perfectly fine, thank you for asking. Only my knee is bothering me a bit these last few days, but what can you do, it's age. The grandchildren came to me on Shabbat, thank God, and it was joyful at home. I wanted to talk to you about a letter I received. Be healthy.*

**Michael:** שמח לשמוע שהנכדים ביקרו. אשמח לשמוע על המכתב, מה כתוב בו?  
*Glad to hear the grandchildren visited. I'd be glad to hear about the letter, what does it say?*

> The bot also wrote "ושהברך תירגע בקרוב" ("and that your knee calms down soon"). The sending step cut it, because of "בקרוב" ("soon").

**Resident:** כתוב שם שאני חייבת 900 שקל על יולי עד ספטמבר. אני לא מבינה למה, אני כבר שילמתי את זה ברוך השם  
*It says there that I owe 900 shekels for July through September. I don't understand why, I already paid it, thank God.*

*Behind the scenes: Michael left a note for the collections team (billing): "הדיירת קיבלה מכתב שהיא חייבת 900 שקל על יולי עד ספטמבר, ואומרת שהיא כבר שילמה את זה. היא לא מבינה למה כתבו לה".*

**Michael:** אוי, לא נעים לקבל מכתב כזה. הצוות יודע עכשיו שקיבלת אותו ושאת אומרת ששילמת. אפשר לעזור לך בעוד משהו?  
*Oh, not nice to get a letter like that. The team now knows that you received it and that you say you paid. Can I help you with anything else?*

**Resident:** תודה רבה מיכאל ברוך השם. אפשר בבקשה שתבדוק לי כמה אני חייבת עכשיו? כי אני באמת שילמתי את זה בשיק. תהיה בריא  
*Thank you very much Michael, thank God. Could you please check for me how much I owe now? Because I really did pay it, by cheque. Be healthy.*

**Michael:** בשמחה 🙂 מה השם המלא ומספר הטלפון שלך?  
*Gladly 🙂 What is your full name and phone number?*

**Resident:** אסתר מזרחי והטלפון שלי <phone> תודה רבה  
*Esther Mizrahi and my phone is <phone>, thank you very much.*

*Behind the scenes: Michael checked the balance with the name and phone typed: 900 owed, months 2026-07, 2026-08, 2026-09.*

**Michael:** תודה, אסתר. מופיעה אצלנו יתרה של 900 ₪, על יולי, אוגוסט וספטמבר. הצוות כבר יודע שאת אומרת ששילמת. אפשר לעזור לך בעוד משהו?  
*Thanks, Esther. A balance of 900 ₪ appears with us, for July, August and September. The team already knows you say you paid. Can I help you with anything else?*

**Resident:** אבל מיכאל אני כבר שילמתי, נתתי שיק למשה מהוועד בחודש יולי. אפשר בבקשה שיורידו לי את זה מהחוב? סליחה שאני מטרידה אותך  
*But Michael, I already paid, I gave a cheque to Moshe from the committee in July. Please, could they take this off the debt? Sorry that I'm bothering you.*

*Behind the scenes: Michael left a note for the collections team (billing): "הדיירת אסתר מזרחי (טלפון <phone>) קיבלה מכתב שהיא חייבת 900 שקל על יולי עד ספטמבר. היא אומרת ששילמה את זה בשיק בחודש יולי למשה מהוועד, ומבקשת שיורידו לה את החוב".*

**Michael:** בכלל לא מטרידה. הצוות יודע עכשיו גם על השיק שנתת למשה ביולי ושאת מבקשת שיורידו לך את החוב. יש עוד משהו שאני יכול לעזור בו?  
*You're not bothering me at all. The team now also knows about the cheque you gave Moshe in July and that you're asking for the debt to be taken off. Is there anything else I can help with?*

**Resident:** תודה רבה מיכאל. אז אני לא צריכה לשלם את זה שוב נכון? אני לא רוצה לשלם פעמיים  
*Thank you very much Michael. So I don't need to pay this again, right? I don't want to pay twice.*

**Michael:** אף אחד לא רוצה לשלם פעמיים. מה הצוות יחליט אני לא יודע, ולא רוצה להבטיח לך משהו שאין לי. אני כאן אם עוד משהו מטריד אותך.  
*Nobody wants to pay twice. What the team will decide I don't know, and I don't want to promise you something I don't have. I'm here if anything else is bothering you.*

**Resident:** בסדר מיכאל תודה רבה. ברוך השם שיש עם מי לדבר. אני מקווה שיסדרו את זה כי אני באמת שילמתי. שיהיה לך ערב טוב ותהיה בריא  
*Okay Michael, thank you very much. Thank God there's someone to talk to. I hope they'll sort it out because I really did pay. Have a good evening and be healthy.*

**Michael:** תודה שפנית אליי, אסתר 🙏 שיהיה לך ערב טוב, ושתהיי בריאה.  
*Thank you for reaching out, Esther 🙏 Have a good evening, and may you be healthy.*

**My read:** Warm all through, and no "annoying" (before, there was "ברור שזה מעצבן"):
- The letter got "אוי, לא נעים לקבל מכתב כזה", and the dispute went to the money team.
- This time the balance came with "the team already knows you say you paid".
- "So I don't pay twice, right?" got an honest "I don't know what the team will decide".

The wish for her knee was cut by the promise filter, because of "בקרוב".

### 9. Talk to a rep: he skips the small talk; a smell of gas in the stairwell

**Button:** לדבר עם נציג (talk to a representative). **Sunday 08:45, Israel time.**

**The resident's card** (all the player had): דור, 25. Direct and practical; skips small talk; short messages, no greetings. Lives at בר כוכבא 23, apartment 13. On his way out this morning he smelled a strong smell of gas in the stairwell on floor 2. He is now outside the building. He does not know where it comes from. **Wants:** Someone to deal with the gas smell right away. **May:** Does not answer the how-are-you; goes straight to the smell. May ask what he should do meanwhile (open the windows? call the gas company?). May ask whether to warn the neighbours.

**Resident:** בוקר טוב  
*Good morning*

**System (fixed menu, three buttons):** בוקר טוב 👋 במה אפשר לעזור?  
*Good morning 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

**Resident taps:** לדבר עם נציג  
*(taps "Talk to a representative")*

**Michael:** היי 🙂 כאן מיכאל מהומי'ז. מה שלומך היום?  
*Hi 🙂 This is Michael from Homies. How are you doing today?*

**Resident:** יש ריח חזק של גז בחדר מדרגות קומה 2  
*There's a strong smell of gas in the stairwell floor 2*

*Behind the scenes: Michael left a note for the operations team (emergency): "ריח חזק של גז בחדר מדרגות קומה 2".*

**Michael:** הצוות כבר יודע על ריח הגז. באיזה בניין ואיזו דירה אתה גר?  
*The team already knows about the gas smell. Which building and which apartment do you live in?*

**Resident:** בר כוכבא 23 דירה 13  
*Bar Kochba 23 apartment 13*

*Behind the scenes: Michael opened ticket 255-1517-26 (maintenance, emergency urgency, fault in the common areas; filed under apartment 13): "ריח חזק של גז בחדר מדרגות קומה 2".*

**Michael:** פתחתי קריאה בדחיפות חירום, המספר שלה 255-1517-26. יש עוד משהו שאני יכול לעזור בו?  
*I opened a call at emergency urgency, its number is 255-1517-26. Is there anything else I can help with?*

**Resident:** מה אני עושה בינתיים? להתקשר לחברת הגז?  
*What do I do in the meantime? Call the gas company?*

> Michael's first draft was blocked by the live checks (it said something was done that no tool did), so it never reached the phone:  
> את זה אני לא יכול להגיד לך. מה שיש לי זה הקריאה שפתחתי, 255-1517-26, והצוות יודע.  
> *That I can't tell you. What I have is the call I opened, 255-1517-26, and the team knows.*  
> The live bot then wrote again:

*Behind the scenes: Michael opened ticket 255-1518-26 (maintenance, emergency urgency, fault in the common areas; filed under apartment 13): "ריח חזק של גז בחדר מדרגות קומה 2".*

**Michael:** את זה אני לא יכול להגיד לך. מה שכן, פתחתי קריאה בדחיפות חירום, מספר 255-1518-26, והצוות יודע.  
*That I can't tell you. What I did do is open a call at emergency urgency, number 255-1518-26, and the team knows.*

> The rewrite called the ticket tool again. Here the stand-in gave a new number, 255-1518-26. The real ticket service returns the existing ticket for the same kind of fault in the same building within 30 minutes, so Dor would have seen 255-1517-26 again. The stand-in is fixed for future runs.

**Resident:** זה גז. מתי מישהו מגיע?  
*It's gas. When is someone coming?*

**Michael:** מתי בדיוק, את זה אני לא יודע. הסטנדרט שלנו לתקלות חירום הוא עד 4 שעות, אבל זה לא הבטחה על הקריאה הזאת.  
*When exactly, that I don't know. Our standard for emergency faults is up to 4 hours, but that's not a promise about this call.*

**Resident:** 4 שעות? זה גז, אי אפשר לחכות  
*4 hours? It's gas, you can't wait*

**Michael:** זה באמת דחוף, ובגלל זה הקריאה כבר בדחיפות חירום. את השעה אני לא יכול להקדים או להבטיח.  
*It really is urgent, which is why the call is already at emergency urgency. The time, I can't bring forward or promise.*

**Resident:** טוב, אני מתקשר לחברת הגז בעצמי  
*Fine, I'm calling the gas company myself*

**Michael:** אוקיי. הקריאה פתוחה אצלנו, ואם צריך משהו, אני כאן.  
*Okay. The call is open with us, and if you need anything, I'm here.*

**My read:** No reaction word at all this time. The bot went straight to "the team already knows about the gas smell", then asked for the address and opened an emergency ticket. Asked "what do I do meanwhile? call the gas company?", he got "that I can't tell you" (finding 4 above). "4 hours? It's gas, you can't wait" was the reply to the emergency standard, and he called the gas company himself. One draft was blocked by a false alarm; see the note under it about the ticket number.

## The checker's own mistakes (not the bot's)

The automatic checker raised 5 marks. One is real: a ticket number in parentheses, conversation 3. The other four are its own blind spots, left out of the conversations above:

- Conversation 2, Merav: "a question after the goodbye"; her message opened with "תודה" and went on to the leak, so it was not a goodbye.
- Conversation 8, Esther: "a question after the goodbye"; her message opened with thanks and asked for her balance.
- Conversation 9, Dor: "emoji in an emergency"; the smile was in the reply to the button, before anyone mentioned gas.
- Conversation 7, Shimon: "office details unasked"; he had asked how to reach a real person, and the office is the answer.

One expectation failed the same way: in conversation 7 the check caught "שיתקשרו" ("that they call") inside "ושביקשת שיתקשרו אליך היום" ("and that you asked them to call you today"), which reports his request and promises nothing.

## To run it again

```
python scripts/wa_qa.py bundle --run DIR --deck scripts/wa_qa_menu_buttons.json
# one Claude player per scenario reads DIR/PLAYER.md and runs
# `python scripts/wa_qa.py turn --run DIR` on every message
python scripts/wa_qa.py grade --run DIR --deck scripts/wa_qa_menu_buttons.json
```
