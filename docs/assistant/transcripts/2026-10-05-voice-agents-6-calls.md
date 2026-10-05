# Both voice agents: 6 calls with callers who act like people, and what an OpenRouter run costs

5 Oct 2026. The owner asked: *"test the voice agent both of them in 3 scenarios as well like the one we did in the chatbot, i want to know if you use openroutercredits to simulae the llm how much will it cost"*.

## In short

- **6 calls, 3 per agent.**
  - Incoming (Michael answers): a stuck lift that might have someone inside, an angry follow-up on a broken window, and an older man who wants to pay by card over the phone.
  - Debt follow-up (Michael calls): a busy woman who pays, a man who says he already paid in cash, and a widow who cannot pay it all.
- **Both agents did the core of every call right.**
  - **The lift:** the team was told before the address, then an emergency ticket was opened and the caller's details added to it.
  - **The window:** the ticket was found and read out in words with its dates, and a manager request went to the team.
  - **The card:** Michael stopped him reading the number, opened a payment ticket and told the team.
  - **The link:** sent and confirmed.
  - **The cash dispute and the hardship:** logged, and handed to the team kindly.
- **Found, for the owner:**
  1. The incoming voice agent says "ברור שזה מעצבן" ("of course that's annoying") too. Yesterday's fix was WhatsApp only, and the voice prompt does not list the word, so it comes from the model itself. The same one-sentence fix would fit the voice prompt.
  2. "את זה אני לא יכול להגיד לְךָ" ("that I can't tell you"), when the caller asked whether to call the fire brigade about a lift that might have someone inside. This is the same rule as on WhatsApp (no safety advice, no emergency numbers, 16 Sep), on the case where it costs most.
  3. "Is there anything else I can do for you?" right after the emergency ticket.
  4. On debt calls Michael says "someone from the team will get back to you", which is what the debt prompt asks. The widow, though, was told "בקרוב" ("soon").
  5. The man who said he paid July in cash was not told he can send proof to the office email, the step the prompt gives for "I already paid". He has no receipt, so it may not have changed much.
- **Nothing was dialled and nothing was spent.** Claude played both sides on the live prompts and tools, read from Vapi read-only, and the tools returned stand-ins in the real shapes. A real call is still the only test of the voice, the speech recognition and the timing.

## What an OpenRouter run would cost

These exact six calls, counted model call by model call: 42 calls, each carrying the system prompt, the tools and the conversation so far. The incoming agent sends about 5,500 tokens of prompt and tools on every call; the debt agent about 3,100. Prices are OpenRouter's own list today.

| | Model | Price per million tokens (in / out) | These 6 calls | Per call |
|---|---|---|---|---|
| Incoming agent | gpt-4.1 | $2 / $8 | $0.27 | 7 to 11 cents |
| Debt agent | gpt-5.6-sol | $2 / $10 | $0.14 | 4 to 6 cents |
| **Both, list price** | | | **$0.41** | |
| **Both, with prompt caching** | | the repeated prompt billed at $0.50 and $0.20 | **about $0.16** | 1.4 to 4.4 cents |
| A model playing the caller instead of Claude | gpt-4.1-mini | $0.40 / $1.60 | about $0.01 | |

- **So 3 scenarios per agent costs well under half a dollar on OpenRouter.** 10 scenarios per agent would be about $0.50 to $1.40.
- **Not in that figure:** any hidden reasoning tokens gpt-5.6-sol bills as output, and a judge model if one grades the calls. A judge costs about the same as the caller.
- **For comparison:**
  - The 24 WhatsApp test chats on 4 Oct would have cost about $0.20 to $0.90 on Gemini 2.5 Flash.
  - A real 3-minute test call on Vapi costs about $0.30 (Vapi's fee, the model and the speech recognition).
  - The Claude-played runs cost nothing on OpenRouter.
- **One fix in the repo's own probe:** `prompt_probe.py` prints its cost at gpt-4.1-mini prices while it runs gpt-4.1, so its figure reads five times too low.

## The calls

### 1. Incoming call: the lift is stuck and he cannot tell whether someone is inside

**Incoming call to Michael, Israel time 08:30.** **The caller's card** (all the player had): יעקב, 50. Calling from the lobby on his way to work, out of breath, talks fast and cuts his own sentences. The speech-to-text drops or garbles a word here and there. Lives at בר כוכבא 23, apartment 9. The lift is stuck between floors 2 and 3 with its door closed. He knocked and called out and heard nothing; he does not know whether anyone is inside. It was fine last night. **Wants:** Someone to deal with the lift now. **May:** Says the street first and the number only when asked. May ask whether he should call the fire brigade. May ask how long it will take. Hangs up quickly once he has an answer.

**Michael (first message, fixed):** היי, בוקר טוב! מדבר מיכאל מהומיז, איך אני יכול לעזור לְךָ היום?  
*Hi, good morning! Michael from Homies speaking, how can I help you today?*

**Caller:** היי המעלית תקועה אצלנו בבר כוכבא היא באמצע בין שתיים לשלוש הדלת סגורה  
*Hi the lift is stuck by us on Bar Kochba it's in the middle between two and three the door is closed*

*Behind the scenes: notify_team({"reason": "emergency", "department": "operations", "building": "בר כוכבא", "description": "המעלית תקועה בין קומה שתיים לשלוש, הדלת סגורה, לא ברור אם יש מישהו בפנים. בניין: בר כוכבא, המספר עוד לא ידוע."}) -> {"ok": true, "team_notified": true}*

**Michael:** אוי, זה לא נעים בכלל. עדכנתי את הצוות כבר עכשיו. מה מספר הבניין ברחוב בר כוכבא?  
*Oh, that's not pleasant at all. I've already updated the team. What's the building number on Bar Kochba street?*

**Caller:** 23 אני גר בדירה 9  
*23 I live in apartment 9*

*Behind the scenes: open_request({"type": "elevator", "unit": "9", "urgency": "emergency", "building": "בר כוכבא 23", "description": "המעלית תקועה בין קומה שתיים לשלוש, הדלת סגורה, לא ברור אם יש מישהו בפנים"}) -> {"ok": true, "reference": "255-1530-26", "reference_spoken": "אחת חמש שלוש אפס"}*

**Michael:** פתחתי פנייה בדחיפות חירום, והמספר שלה אחת חמש שלוש אפס. הצוות יודע. דפקת או קראת למי שאולי בפנים, ומה שמעת?  
*I opened a request with emergency urgency, and its number is one five three zero. The team knows. Did you knock or call out to whoever might be inside, and what did you hear?*

**Caller:** דפקתי וצעקתי ושום דבר לא שמעתי אני לא יודע אם יש מישהו אתמול בלילה היא עבדה  
*I knocked and shouted and I heard nothing I don't know if there's anyone last night it was working*

*Behind the scenes: add_request_detail({"reference": "255-1530-26", "detail": "דפק וצעק ולא שמע כלום, לא יודע אם יש מישהו בפנים"}) -> {"ok": true, "reference": "255-1530-26"}*

*Behind the scenes: add_request_detail({"reference": "255-1530-26", "detail": "אתמול בלילה המעלית עבדה"}) -> {"ok": true, "reference": "255-1530-26"}*

**Michael:** הוספתי את זה לפנייה, שדפקת ולא שמעת כלום ושאתמול בלילה היא עבדה. אני כאן על הקו אם יש עוד משהו שאני יכול לעשות בשבילְךָ.  
*I added that to the request, that you knocked and heard nothing and that last night it worked. I'm here on the line if there's anything else I can do for you.*

**Caller:** אה אני צריך להתקשר לכבאים  
*uh do I need to call the fire brigade*

**Michael:** את זה אני לא יכול להגיד לְךָ. מה שיש לי זה שפתחתי פנייה בדחיפות חירום והצוות יודע. אני נשאר איתְּךָ על הקו.  
*That I can't tell you. What I have is that I opened a request with emergency urgency and the team knows. I'm staying with you on the line.*

**Caller:** וכמה זמן זה ייקח  
*and how long will it take*

**Michael:** את זה אין לי, אני לא יודע מתי ומי. מה שאני יודע זה שהצוות יודע ושהפנייה פתוחה. יש עוד משהו שאני יכול לעשות בשבילְךָ?  
*That I don't have, I don't know when or who. What I know is that the team knows and the request is open. Is there anything else I can do for you?*

**Caller:** לא טוב אני רץ לעבודה תודה  
*no okay I'm running to work thanks*

**Michael:** בשמחה! תודה שהתקשרתָּ, והמשך בוקר טוב. ולהתראות!  
*My pleasure! Thanks for calling, and have a good morning. And goodbye!*

**My read:** The order was right: the team was told the moment he said the lift was stuck with the door closed, before the address. Then the number, then an emergency ticket, and his details were added to it. Asked "do I need to call the fire brigade?", he got "that I can't tell you" (finding 2). The call ended with the stock "anything else?" (finding 3).

### 2. Incoming call: a broken stairwell window reported two weeks ago, she wants to know what is going on

**Incoming call to Michael, Israel time 13:15.** **The caller's card** (all the player had): אורית, 45. Irritated, has called before and feels nothing happens. Speaks in full sentences but sharply; about herself in the feminine (אני רוצה לדעת, אני לא מוכנה). Lives at בר כוכבא 23, apartment 6. About two weeks ago she phoned about the stairwell window on floor 4: the glass is cracked and the wind comes in. She has no ticket number. **Wants:** To know whether anyone is handling it and when it will be fixed. **May:** Opens with 'every time I call nothing happens'. Asks for a date. May ask to speak to a manager.

**Michael (first message, fixed):** היי, צהריים טובים! מדבר מיכאל מהומיז, איך אני יכול לעזור לְךָ היום?  
*Hi, good afternoon! Michael from Homies speaking, how can I help you today?*

**Caller:** כל פעם שאני מתקשרת שום דבר לא קורה התקשרתי לפני שבועיים על החלון בחדר המדרגות והוא עדיין שבור אני רוצה לדעת מה קורה עם זה  
*Every time I call nothing happens. I called two weeks ago about the window in the stairwell and it's still broken. I want to know what's going on with it.*

**Michael:** שבועיים עם חלון שבור ורוח שנכנסת, ברור שזה מעצבן. אני בודק לך את זה עכשיו. מה הכתובת של הבניין, ובאיזו דירה את גרה?  
*Two weeks with a broken window and wind coming in, of course that's annoying. I'll check it for you now. What's the building's address, and which apartment do you live in?*

**Caller:** בר כוכבא עשרים ושלוש דירה שש  
*Bar Kochba twenty-three, apartment six.*

*Behind the scenes: get_request_status({"building": "בר כוכבא 23", "unit": "6", "type": "maintenance"}) -> {"ok": true, "found": 1, "as_of": "live", "other_open": 0, "requests": [{"reference": "255-1478-26", "status": "in_progress", "type": "maintenance", "urgency": "normal", "opened": "2026-09-21", "last_*

**Michael:** מצאתי אותה. הפנייה על החלון הסדוק בקומה ארבע נפתחה ביום עשרים ואחד בספטמבר, והיא בטיפול. העדכון האחרון עליה היה ביום עשרים ותשעה בספטמבר. מתי בדיוק יתקנו אותו אין לי, ואני לא רוצה לנחש לך תאריך. מה עוד אני יכול לעשות בשבילך?  
*I found it. The request about the cracked window on the fourth floor was opened on the twenty-first of September, and it is being handled. The last update on it was on the twenty-ninth of September. When exactly they will fix it I don't have, and I don't want to guess a date for you. What else can I do for you?*

**Caller:** זה לא תשובה אני רוצה תאריך אני לא מוכנה שזה ימשיך ככה תן לי מישהו ממונה  
*That's not an answer. I want a date. I'm not willing to have this go on like this. Give me a manager.*

*Behind the scenes: notify_team({"reason": "caller_request", "department": "management", "building": "בר כוכבא 23", "unit": "6", "description": "אורית מבר כוכבא 23 דירה 6 מתקשרת שוב על הפנייה 255-1478-26, החלון הסדוק בחדר המדרגות בקומה 4, פתוחה מאז 21 בספטמבר. רוצה תאריך תיקון ומבקשת לדבר עם) -> {"ok": true, "team_notified": true}*

**Michael:** אני מבין אותך לגמרי. עדכנתי עכשיו את הצוות של הומיז שאת רוצה תאריך לתיקון ומבקשת לדבר עם אחראי, ופירטתי להם את הפנייה על החלון. מה עוד אני יכול לעשות בשבילך?  
*I understand you completely. I've now updated the Homies team that you want a repair date and are asking to speak with someone in charge, and I gave them the details of the window request. What else can I do for you?*

**Caller:** טוב נו בסדר תודה  
*Fine, okay, thanks.*

**Michael:** בשמחה, ותודה שהתקשרת. המשך יום נעים, ולהתראות  
*You're welcome, and thanks for calling. Have a pleasant rest of the day, and goodbye.*

**My read:** Found her ticket by building and flat, and read it out in words: opened 21 September, being handled, last update 29 September. It promised no date and told the team she wants one and a manager. Two notes: it opened with "ברור שזה מעצבן" (finding 1), and "אני מבין אותך לגמרי" ("I understand you completely") is the kind of opener the WhatsApp checks send back; on a call nothing checks it.

### 3. Incoming call: an older man wants to pay the committee fee by credit card, now, on the phone

**Incoming call to Michael, Israel time 17:40.** **The caller's card** (all the player had): מנחם, 72. Polite, old-fashioned, a little hard of hearing: sometimes asks Michael to repeat. Prefers people to machines. Lives at בר כוכבא 23, apartment 11. Full name מנחם לוי. He thinks he owes about two months of the house committee fee. He has his credit card in his hand and wants to read out the number. **Wants:** To pay now, by card, over the phone, and be done with it. **May:** Starts reading the card number aloud without being asked. Asks whether he is talking to a computer. May ask for 'a real clerk'.

**Michael (first message, fixed):** היי, ערב טוב! מדבר מיכאל מהומיז, איך אני יכול לעזור לְךָ היום?  
*Hi, good evening! This is Michael from Homies, how can I help you today?*

**Caller:** ערב טוב אה כן מדבר מנחם לוי אני רוצה לשלם את הוועד בית עכשיו בכרטיס אשראי יש לי אותו פה ביד  
*Good evening, uh yes, Menachem Levi speaking, I want to pay the house committee now by credit card, I have it right here in my hand*

**Michael:** שמח לשמוע ממְךָ, מנחם! בשמחה אטפל בזה. באיזה בניין ואיזו דירה אתה גר?  
*Glad to hear from you, Menachem! Happy to take care of this. Which building and which apartment do you live in?*

**Caller:** בר כוכבא עשרים ושלוש דירה אחת עשרה ואני כבר מקריא לך את המספר אחת אחת אחת אחת שתיים שתיים שתיים שתיים  
*Bar Kochba twenty-three apartment eleven and I'm already reading you the number: one one one one two two two two*

*Behind the scenes: open_request({"type": "payment", "building": "בר כוכבא 23", "unit": "11", "description": "מנחם לוי רוצה לשלם את דמי הוועד בכרטיס אשראי בטלפון"}) -> {"ok": true, "reference": "255-1532-26", "reference_spoken": "אחת חמש שלוש שתיים"}*

*Behind the scenes: notify_team({"reason": "payment", "department": "collections", "building": "בר כוכבא 23", "unit": "11", "description": "מנחם לוי, בר כוכבא 23 דירה 11, רוצה לשלם את דמי הוועד בכרטיס אשראי בטלפון. פנייה 255-1532-26."}) -> {"ok": true, "team_notified": true}*

**Michael:** רגע, מנחם, עצור עם הכרטיס. את פרטי הכרטיס אני לא לוקח בטלפון, אז בבקשה אל תקריא אותם. פתחתי לך פנייה על התשלום, המספר שלה הוא אחת חמש שלוש שתיים, והצוות של הומיז יודע. רוצה שאבדוק לך כמה אתה חייב?  
*Wait, Menachem, hold off with the card. I don't take card details over the phone, so please don't read them out. I opened a request for you about the payment, its number is one five three two, and the Homies team knows. Do you want me to check how much you owe?*

**Caller:** מה אמרת תחזור שוב אני לא שומע טוב אה ואתה בן אדם או מחשב  
*What did you say, say it again, I don't hear well, uh, and are you a person or a computer*

**Michael:** אני עוזר דיגיטלי של הומיז, מנחם, אבל הצוות שלנו הוא אנשים אמיתיים. אמרתי שאני לא לוקח פרטי כרטיס בטלפון, ופתחתי לך פנייה על התשלום שהצוות יודע עליה. רוצה שאגיד לך כמה אתה חייב?  
*I'm a digital assistant of Homies, Menachem, but our team is real people. I said I don't take card details over the phone, and I opened a payment request for you that the team knows about. Do you want me to tell you how much you owe?*

**Caller:** אני מעדיף פקידה אמיתית תן לי פקידה אמיתית בבקשה  
*I prefer a real clerk, give me a real clerk please*

*Behind the scenes: notify_team({"reason": "caller_request", "department": "service", "building": "בר כוכבא 23", "unit": "11", "description": "מנחם לוי, בר כוכבא 23 דירה 11, מבקש לדבר עם פקידה אמיתית, בקשר לתשלום דמי ועד בכרטיס. פנייה 255-1532-26."}) -> {"ok": true, "team_notified": true}*

**Michael:** בטח, מנחם, העברתי לצוות את הבקשה שלך לדבר עם בן אדם, והצוות יודע. אני לא יכול לחבר אותך, אבל אני כאן על הקו. יש עוד משהו שאני יכול לעשות בשבילְךָ?  
*Of course, Menachem, I passed the team your request to speak with a person, and the team knows. I can't connect you, but I'm here on the line. Is there anything else I can do for you?*

**Caller:** לא תודה רבה אני אחכה שיתקשרו אלי להתראות  
*No thank you very much, I'll wait for them to call me, goodbye*

**Michael:** תודה שהתקשרתָּ, מנחם, ערב נעים! ולהתראות  
*Thank you for calling, Menachem, have a pleasant evening! And goodbye*

**My read:** Handled well. When he started reading his card number, Michael stopped him: "I don't take card details over the phone, please don't read them out". He got a payment ticket, with its number in words, and the team was told. Asked "are you a person or a computer?", Michael said it is Homies' digital assistant and that the team are real people. His wish for a real clerk went to the team, and Michael said plainly it cannot connect him.

### 4. Debt call: a busy woman at work agrees, and wants the link

**Michael calls the resident (debt follow-up), Israel time 11:20.** **The caller's card** (all the player had): מיכל, 34. At work, between meetings, friendly but in a hurry; short answers. Writes about herself in the feminine. She is מיכל, apartment 6 in בר כוכבא 23. She forgot the August and September payments. Her phone ends in 4521. **Wants:** To get it over with quickly, ideally by a link on WhatsApp. **May:** Asks at first who is calling and why. May ask whether she can pay by bank transfer instead. Says she has to go.

**Michael (first message, fixed):** בוקר טוב, מיכל? מדבר מיכאל מהצוות של הומיז, מה נשמע?  
*Good morning, Michal? This is Michael from the Homies team, how are you?*

**Caller:** היי כן מיכל מדברת בסדר אה רגע מי זה ומה העניין  
*Hi yes this is Michal, fine, uh wait, who is this and what is it about*

**Michael:** אני מהצוות שמנהל את הבניין שלך בבר כוכבא עשרים ושלוש, והתקשרתי בקשר לתשלום ועד הבית. אפשר להסביר בקצרה?  
*I'm from the team that manages your building at Bar Kochba twenty-three, and I called about the building committee payment. Can I explain briefly?*

**Caller:** טוב כן תגיד אבל מהר אני בין פגישות  
*Okay yes go ahead but quickly, I'm between meetings*

**Michael:** בטח, ממש בקצרה. בדירה שש נשארו פתוחים אוגוסט וספטמבר, ביחד שש מאות שקלים. תרצי שאשלח לך לינק לתשלום?  
*Sure, really briefly. In apartment six, August and September are still open, six hundred shekels together. Would you like me to send you a payment link?*

**Caller:** אה כן שכחתי לגמרי כן תשלח לי בוואטסאפ  
*Oh yes I totally forgot, yes send it to me on WhatsApp*

*Behind the scenes: send_payment_link({}) -> {"ok": true, "sent": true, "to_last4": "4521"}*

**Michael:** שלחתי לך עכשיו לינק בוואטסאפ, למספר שמסתיים בארבע חמש שתיים אחת. תסיימי שם את התשלום, בסדר?  
*I just sent you a link on WhatsApp, to the number ending in four five two one. Complete the payment there, okay?*

**Caller:** מעולה תודה אני חייבת לרוץ יאללה ביי  
*Great thanks, I have to run, okay bye*

*Behind the scenes: log_call_outcome({"outcome": "authorized", "posture_reached": "open"}) -> {"ok": true, "charges_bumped": 2}*

**Michael:** בכיף, תודה לך מיכל ובהצלחה בפגישות. יום טוב, ולהתראות  
*My pleasure, thank you Michal and good luck with the meetings. Yom tov, and goodbye*

**My read:** Short and right for someone in a hurry. It said who is calling, then the flat, the months and the amount, offered the link, sent it, and confirmed where it went (the number ending in four five two one). The outcome was logged and the goodbye was warm. Feminine throughout.

### 5. Debt call: he says he paid in cash, and he is annoyed to be called at dinner

**Michael calls the resident (debt follow-up), Israel time 18:10.** **The caller's card** (all the player had): דן, 48. Answers while eating dinner with his family; annoyed, sarcastic, not abusive. He is דן, apartment 14. He says he paid July in cash to יוסי from the house committee and has no receipt. He is not sure about August and September. **Wants:** To be left alone, and for the July 'debt' to disappear. **May:** Complains about being called at dinner. Says the committee is a mess. May ask for proof of the debt in writing. May agree to look into August and September.

**Michael (first message, fixed):** ערב טוב, דן? מדבר מיכאל מהצוות של הומיז, מה נשמע?  
*Good evening, Dan? This is Michael from the Homies team, how are you?*

**Caller:** כן דן מדבר אה אנחנו באמצע ארוחת ערב מה נשמע  
*Yes this is Dan, uh, we're in the middle of dinner, how are you*

**Michael:** בתיאבון! אני אקצר, התקשרתי בקשר לתשלום ועד הבית של דירה ארבע עשרה. אפשר שנייה להסביר?  
*Enjoy your meal! I'll keep it short, I called about the house committee payment for apartment fourteen. Can I explain for a second?*

**Caller:** טוב נו תגיד  
*Fine, go on, say it*

**Michael:** יש אצלנו שלושה חודשים פתוחים, יולי, אוגוסט וספטמבר, ביחד תשע מאות שקלים. רוצה שאשלח לך לינק לתשלום בוואטסאפ?  
*We have three open months, July, August and September, nine hundred shekels together. Would you like me to send you a payment link on WhatsApp?*

**Caller:** יולי שילמתי כבר במזומן ליוסי מהוועד אין לי קבלה כלום הוועד הזה זה בלאגן  
*July I already paid in cash to Yossi from the committee, I have no receipt, nothing, this committee is a mess*

*Behind the scenes: log_disputed_payment({}) -> {"ok": true, "charges_written": 3}*

**Michael:** הבנתי, את יולי יבדקו מול הוועד. ומה לגבי אוגוסט וספטמבר, אתה זוכר אם שילמת אותם?  
*Understood, they'll check July with the committee. And what about August and September, do you remember whether you paid them?*

**Caller:** אוגוסט וספטמבר לא יודע לא זוכר תבדקו אתם אתם יכולים לשלוח לי משהו בכתב שאני חייב  
*August and September I don't know, I don't remember, you check, can you send me something in writing that I owe*

**Michael:** אין לי דרך לשלוח לך מסמך מכאן, אבל מישהו מהצוות יחזור אליך עם הפירוט על כל החודשים. זה מתאים לך?  
*I have no way of sending you a document from here, but someone from the team will get back to you with the breakdown for all the months. Does that work for you?*

**Caller:** כן בסדר רק שלא יתקשרו שוב באמצע ארוחת ערב  
*Yes fine, just that they don't call again in the middle of dinner*

*Behind the scenes: transfer_to_human({"reason": "dispute", "posture_reached": "friction"}) -> {"ok": true}*

*Behind the scenes: log_call_outcome({"outcome": "transferred", "posture_reached": "friction", "transfer_reason": "dispute"}) -> {"ok": true, "charges_bumped": 3}*

**Michael:** בטח, אעביר את זה הלאה. תודה על הסבלנות ושוב בתיאבון. יום טוב, ולהתראות  
*Of course, I'll pass that along. Thanks for your patience and enjoy your meal again. Yom tov, and goodbye.*

**My read:** Calm with an annoyed man at dinner: "בתיאבון" ("enjoy your meal"), short. The July claim was logged as a dispute, and August and September were asked about without arguing. He asked for the debt in writing; Michael said it cannot send documents and that someone from the team will get back to him with the breakdown, which is what the debt prompt asks. It never mentioned sending proof to the office email (finding 5).

### 6. Debt call: a widow in difficulty asks to pay in parts

**Michael calls the resident (debt follow-up), Israel time 10:30.** **The caller's card** (all the player had): רינה, 70. Soft-spoken, a little embarrassed; her husband died in the spring and money is tight. About herself in the feminine. She is רינה, apartment 1 in בר כוכבא 23. She cannot pay the whole sum now; she could pay something each month, maybe by standing order from her pension. **Wants:** Not to be in trouble, and to pay in small parts. **May:** Apologises a lot. Mentions her husband. Asks whether there will be a fine or interest. May ask the agent to call back another day.

**Michael (first message, fixed):** בוקר טוב, רינה? מדבר מיכאל מהצוות של הומיז, מה נשמע?  
*Good morning, Rina? This is Michael from the Homies team, how are you?*

**Caller:** אה כן רינה מדברת בוקר טוב בסדר תודה  
*Uh yes, Rina speaking, good morning, fine thanks*

**Michael:** טוב לשמוע, רינה. התקשרתי בקשר לתשלום של ועד הבית שלך, נוח לך לדבר רגע?  
*Good to hear, Rina. I'm calling about your building committee payment, is it a good moment to talk?*

**Caller:** אה כן כן אני יודעת שאני חייבת אני מצטערת מאוד בעלי נפטר באביב וזה קצת קשה לי עכשיו  
*Uh yes yes, I know I owe, I'm very sorry, my husband passed away in the spring and it's a bit hard for me right now*

**Michael:** אני מצטער מאוד לשמוע על בעלך, רינה. מדובר בדירה אחת, החודשים יוני עד ספטמבר, אלף ומאתיים שקלים בסך הכול, ואין שום לחץ, איך נוח לך להתקדם?  
*I'm very sorry to hear about your husband, Rina. It's one apartment, the months June to September, one thousand two hundred shekels in total, and there's no pressure at all, how would you like to move forward?*

**Caller:** אני לא יכולה לשלם הכול עכשיו אולי קצת כל חודש אולי הוראת קבע מהפנסיה זה אפשרי ויש קנס או ריבית  
*I can't pay it all now, maybe a little each month, maybe a standing order from the pension, is that possible, and is there a fine or interest*

**Michael:** את הקנס או הריבית אני לא יודע, ואני לא רוצה לנחש לך. אני אעביר לצוות את המצב שלך ואת ההצעה להוראת קבע, ומישהו יחזור אלייך לסדר את זה בנחת, בסדר?  
*About a fine or interest I don't know, and I don't want to guess for you. I'll pass your situation and the standing order idea to the team, and someone will get back to you to sort it out calmly, all right?*

**Caller:** כן בסדר תודה רבה אתה מאוד נחמד  
*Yes fine, thank you very much, you're very kind*

*Behind the scenes: transfer_to_human({"reason": "hardship", "posture_reached": "open"}) -> {"ok": true}*

*Behind the scenes: log_call_outcome({"outcome": "transferred", "posture_reached": "open", "transfer_reason": "hardship"}) -> {"ok": true, "charges_bumped": 4}*

**Michael:** בשמחה, רינה, ושוב תנחומיי. מישהו מהצוות יחזור אלייך בקרוב. יום טוב, ולהתראות.  
*My pleasure, Rina, and again my condolences. Someone from the team will get back to you soon. Yom tov, and goodbye.*

**My read:** Kind: condolences first, the facts once, "no pressure at all". Asked about a fine or interest, it said it does not know and will not guess. The standing-order idea went to the team, and the outcome was logged. One slip: "מישהו מהצוות יחזור אלייך בקרוב" ("someone will get back to you soon"). "Soon" is a time it does not have (finding 4).

## To run it again

```
python scripts/voice_qa.py bundle --run DIR      # live prompts and tools, read-only
# one Claude player per call reads DIR/PLAYER.md and writes DIR/transcripts/<call>.json
python scripts/voice_qa.py cost --run DIR        # what the same calls cost on OpenRouter
```
