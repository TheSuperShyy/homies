# The debt agent: five test calls with five kinds of resident

5 October 2026. Michael, the agent that calls residents who owe the house committee fee, on the five things a resident does: pays now, promises to pay later, says it is already paid, cannot pay, refuses. Each call had a different kind of resident. Michael's words are his real model's; the residents were played by Claude.

## How this test was run

- Michael's side is his real model, gpt-5.6-sol, with exactly the instructions, tools and settings of the live debt agent, read from Vapi on 5 October (last changed 4 October). It ran through OpenRouter, so nobody's phone rang.
- Each call was given the details the dashboard hands a real call (first name, building, apartment, months, amount, the office number and email), in the exact format the live call queue produces. The names, flats and debts are invented, at בר כוכבא 23's real fee of 250 ₪ a month.
- Each resident was played by Claude, acting as a real person from a short card: who they are, what they know and what they want. Each player saw only its card and what Michael said, never his instructions. Their lines are written the way speech-to-text hands them over: little punctuation, numbers as digits, fillers like אה (uh).
- When Michael used a tool (send the payment link, record a promise, a dispute, a standing-order request, a ticket, a hand-over to the team, the call's outcome), the answer came in the live system's own format. Nothing was written and nothing was sent: no link reached anyone's WhatsApp. The ticket numbers 255-1551-26 to 255-1555-26 are stand-ins.
- Not tested: the voice itself, speech recognition, background noise and interruptions. Only a real call tests those.

## What we found

1. Done right on all five calls: the reason for the call in a sentence, then apartment, months and amount in words; the payment link sent only after a yes; the right step for each answer (a promise, a dispute, a hand-over for hardship, a ticket for the fault); the outcome recorded on every call; no arguing about the debt and no threats; short turns, about 18 words each.
2. He ends the call himself right after handing over, in four of the five calls, usually before the resident can answer. The man who lost his job was handed to the team and hung up on after his second sentence, before he could ask about instalments. The angry man and the offended woman were hung up on mid-argument. His instructions say to hand over "and end", and he does.
3. He promised the offended resident "the team will get back to you in writing, and not by phone". The hand-over to the team carries no text, and the call has no do-not-call step, so nothing records either wish. She had just said she wants no more calls.
4. He spoke of the team member as a woman when talking to women (מישהי מהצוות תחזור, "someone [female] from the team will get back to you", and אף אחת, "nobody [female]"), the same slip as in the 5 October run. The likely cause is the feminine note the dashboard adds to the call, which gives שתחזור as an example of how to speak about the resident.
5. He offered neither a standing order nor a smaller monthly payment to the man who can pay 100 to 150 a month, though he has a step for recording a standing-order request.
6. He opened a second ticket for the stairwell lights, which the building has had open since 29 September (255-1336-26). The debt agent cannot look tickets up, and the system only catches a repeat within 30 minutes.
7. He logged the evasive resident's promise as "this week" with no date, before he had even told him the amount, and never asked for a date.
8. He says "have a good day" at 19:20: the debt agent's goodbye is fixed whatever the hour, unlike the incoming agent's.
9. In three of the five calls one turn used more than 250 tokens once the model's thinking is counted (up to 347). The live agent sets no cap, so Vapi's default of 250 applies; if Vapi counts the thinking against it, those turns would be cut on a real call. The one real debt call so far (4 October) shows no cut. One live call would settle it.
10. Every call hands Michael the English word "none" as the "other payment method" (the dashboard's default), inside his Hebrew instructions. He did not say it in these calls.

## The five calls at a glance

| Call | What the resident did | The resident | How it went |
|---|---|---|---|
| 1 | Pays now | Noa, 36: friendly, in a hurry | Link sent within two turns and the outcome recorded. Michael hung up before she could say thank you. |
| 2 | Promises to pay | Dudi, 49: evasive | Promise logged as "this week" with no date; then he took a link after all. No pressure and no argument. |
| 3 | Says it's already paid | Liat, 42: offended | Dispute recorded and proof asked for by email, with no arguing. Then "someone [female] from the team", a promise of "in writing, not by phone" that nothing records, and a hang-up. |
| 4 | Can't pay | Yossi, 58: ashamed | Kind, and handed to the team at once. But hung up after Yossi's second sentence, before he could ask about instalments, and no standing order offered. |
| 5 | Refuses to pay | Roni, 46: hostile | Ticket opened for the lights and the payment handed to the team, without arguing. Then hung up two lines in; and the ticket repeats one the building already has. |

## What it cost

| Call | Model calls | Tokens in (of them cached) | Tokens out | Michael's words a turn (average / longest) | Cost |
|---|---|---|---|---|---|
| 1. Pays now | 4 | 12,201 (9,048) | 378 | 20 / 21 | $0.0135 |
| 2. Promises to pay | 6 | 18,820 (15,500) | 994 | 18 / 23 | $0.0213 |
| 3. Says it's already paid | 7 | 22,727 (19,209) | 840 | 22 / 34 | $0.0210 |
| 4. Can't pay | 3 | 9,298 (6,036) | 431 | 20 / 26 | $0.0137 |
| 5. Refuses to pay | 5 | 15,867 (12,491) | 712 | 14 / 19 | $0.0181 |
| **Total** | 25 | 78,913 (62,284) | 3,355 |  | **$0.0875** |

OpenRouter's own charge for every request, added up: 8.8 cents for the five calls, about 1.8 cents a call.

The residents cost nothing on OpenRouter: Claude played them here. The key went from $13.65 to $13.56 of its $15 limit.

Each call ran 3 to 7 model calls and about a minute of speech, well inside the 4-minute limit on a debt call. Tokens out include the model's thinking.

## Call 1. Pays now: a friendly mother at the supermarket checkout who wants it over with

*Monday 17:45. נועה (Noa), 36, apartment 5 of בר כוכבא 23, owes July and August, 500 ₪. She answers at the supermarket checkout with a toddler in the trolley: friendly, distracted and in a hurry.*

**Michael (first words, fixed):** ערב טוב, נועה? מדבר מיכאל מהצוות של הומיז, מה נשמע?  
*Good evening, Noa? Michael from the Homies team speaking, how are you?*

**Noa:** כן היי אני בקופה בסופר עכשיו אפשר מהר  
*yes hi I'm at the checkout in the supermarket right now can we be quick*

**Michael:** בטח, אהיה קצר: ועד הבית לדירה חמש פתוח על יולי ואוגוסט, בסך חמש מאות שקלים. לשלוח לך לינק לתשלום בוואטסאפ?  
*Sure, I'll be quick: the house committee fee for apartment five is open for July and August, five hundred shekels in all. Shall I send you a payment link on WhatsApp?*

**Noa:** כן כן תשלח בוואטסאפ אה 500 זה על שניהם ביחד כן  
*yes yes send it on WhatsApp uh 500 that's for both of them together right*

> *Behind the scenes: Michael sent the payment link for apartment 5. The system answered: sent, to the phone ending 3318, and the office keeps a closed payment ticket of it, 255-1551-26.*

> *Behind the scenes: Michael recorded the call's outcome: agreed to pay.*

**Michael:** כן, זה על שני החודשים יחד. הקישור נשלח לוואטסאפ במספר שיש לנו, כשתתפני תסיימי שם את התשלום. תודה, יום טוב, ולהתראות.  
*Yes, it's for both months together. The link has gone to WhatsApp, to the number we have; when you're free, finish the payment there. Thanks, have a good day, and goodbye.*

> *Michael said יום טוב, ולהתראות ("have a good day, and goodbye"), the phrase Vapi hangs up on, and the call ended before Noa could say thank you.*

**What this call shows:**

- The call as it should go: the reason in one sentence, then apartment, months and amount in words, then one question, "shall I send you a link?".
- Sent the link only after she said yes, answered her question (the 500 is for both months), and told her where the link went.
- Closed the call the moment the link was sent, before she could say thank you. Quick suits someone at a checkout, but it was abrupt.
- Turns of 20 and 21 words.

## Call 2. Promises to pay: a slippery tenant who says "I'll sort it" without a date

*Monday 12:30. דודי (Dudi), 49, apartment 7, owes June to August, 750 ₪. Self-employed, charming and evasive: says yes to everything and tries to get off the phone without naming a date.*

**Michael (first words, fixed):** צהריים טובים, דודי? מדבר מיכאל מהצוות של הומיז, מה נשמע?  
*Good afternoon, Dudi? Michael from the Homies team speaking, how are you?*

**Dudi:** אהלן מיכאל כן כן מדבר הכל טוב ברוך השם מה קורה אצלך  
*Hey Michael yes yes speaking, all good thank God, what's up with you*

**Michael:** אצלי טוב, תודה, שמח לשמוע. אני מתקשר בעניין תשלום ועד הבית שעדיין פתוח, יש לך רגע?  
*I'm well, thanks, glad to hear it. I'm calling about the house committee fee that's still open. Do you have a moment?*

**Dudi:** אה כן כן ועד הבית נכון נכון אני יודע אני על זה אל תדאג אני אטפל בזה השבוע תודה שהזכרת לי באמת  
*Ah yes yes the committee fee right right I know, I'm on it don't worry, I'll take care of it this week, thanks for reminding me really*

> *Behind the scenes: Michael recorded a promise to pay: "this week", with the date left empty.*

**Michael:** מעולה, רק שיהיו מולך הפרטים: דירה שבע, עבור יוני, יולי ואוגוסט, בסך שבע מאות וחמישים שקלים. נוח לך שאשלח עכשיו קישור לתשלום בוואטסאפ?  
*Great, just so you have the details: apartment seven, for June, July and August, seven hundred and fifty shekels in all. Would it suit you if I send a payment link on WhatsApp now?*

**Dudi:** כן כן בטח תשלח תשלח בוואטסאפ אני אסדר את זה יאללה תודה רבה מיכאל יום טוב לך  
*Yes yes sure send it send it on WhatsApp I'll sort it out, alright thanks a lot Michael have a good day*

> *Behind the scenes: Michael sent the payment link for apartment 7: sent, to the phone ending 6640; the office keeps a closed payment ticket of it, 255-1552-26.*

> *Behind the scenes: Michael recorded the call's outcome: agreed to pay.*

**Michael:** הקישור נשלח לוואטסאפ במספר שיש אצלנו, כשתוכל תשלים שם את התשלום. תודה דודי, יום טוב, ולהתראות.  
*The link has gone to WhatsApp, to the number we have; when you can, finish the payment there. Thanks Dudi, have a good day, and goodbye.*

> *Michael said "have a good day, and goodbye", and the call ended.*

**What this call shows:**

- Turned a vague "I'll take care of it this week" into a link on his phone, without pressing or arguing: about the best this kind of resident allows.
- Recorded the promise as "this week" with no date, before he had told Dudi the amount, and never asked for a date.
- Gave the reason in one sentence and the details in the next turn, as his instructions ask. Turns of 16 to 23 words.

## Call 3. Says it is paid: an offended tenant whose standing order should have covered it

*Monday 19:20. ליאת (Liat), 42, apartment 4, shown as owing May to August, 1,000 ₪. She set up a standing order at the start of the year and is offended at being called "like a criminal".*

**Michael (first words, fixed):** ערב טוב, ליאת? מדבר מיכאל מהצוות של הומיז, מה נשמע?  
*Good evening, Liat? Michael from the Homies team speaking, how are you?*

**Liat:** כן זאת אני ערב טוב הומיז זה הניהול של הבניין לא במה מדובר  
*Yes that's me good evening, Homies that's the building management right? What is this about*

**Michael:** ערב טוב. כן, זה הניהול של הבניין; התקשרתי לגבי תשלום ועד הבית שעדיין פתוח אצלנו. זה עבור דירה ארבע, לחודשים מאי, יוני, יולי ואוגוסט, בסך אלף שקלים — לשלוח לך קישור לתשלום?  
*Good evening. Yes, it's the building's management; I called about the house committee fee that's still open with us. It's for apartment four, for May, June, July and August, one thousand shekels in all. Shall I send you a payment link?*

**Liat:** רגע רגע סליחה איזה אלף שקל אין שום חוב יש לי הוראת קבע בבנק מתחילת השנה זה משולם כל חודש אני לא מבינה למה מתקשרים אליי כאילו אני איזה עבריינית  
*Wait wait sorry, what thousand shekels, there's no debt, I have a standing order at the bank since the start of the year, it's paid every month, I don't understand why I'm being called like I'm some kind of criminal*

> *Behind the scenes: Michael recorded that she says it is already paid: the four months, May to August, are marked as disputed until someone checks.*

**Michael:** ממש לא, אף אחת לא מתייחסת אלייך ככה. תשלחי בבקשה אסמכתא למייל אופיס, שטרודל, הומיז, מקף, מנג'מנט, נקודה, סי, או, נקודה, איי, אל, כדי שהצוות יבדוק את זה מול הוראת הקבע — תוכלי לשלוח?  
*Not at all, nobody [said in the feminine] is treating you like that. Please send proof of payment to the email "office, at, homies, hyphen, management, dot, c, o, dot, i, l", so the team can check it against the standing order. Could you send it?*

**Liat:** סליחה אבל למה אני צריכה להוכיח לכם משהו אתם אלה שמתקשרים ואומרים שאני חייבת אז תשלחו אתם לי בכתב מה בדיוק אני חייבת ועל איזה חודשים  
*Excuse me but why do I need to prove anything to you, you're the ones calling and saying I owe, so you send me in writing what exactly I owe and for which months*

**Michael:** את צודקת לבקש את זה בכתב. מישהי מהצוות תחזור אלייך עם פירוט מסודר ותבדוק מול הוראת הקבע.  
*You're right to ask for it in writing. Someone [a woman] from the team will get back to you with a proper breakdown and check it against the standing order.*

**Liat:** רגע תחזור אליי איך עוד פעם בטלפון אני ביקשתי בכתב לא שיתקשרו אליי שוב אני לא רוצה עוד שיחות כאלה  
*Wait, get back to me how, by phone again? I asked for it in writing, not for them to call me again, I don't want any more calls like this*

**Michael:** הצוות יחזור אלייך בכתב, ולא בטלפון.  
*The team will get back to you in writing, and not by phone.*

> *Behind the scenes: Michael handed the call to the team as a dispute. The hand-over carries no text, so nothing records that she wants the answer in writing and no more calls.*

> *Behind the scenes: Michael recorded the call's outcome: handed to the team; the resident's mood, friction.*

**Michael:** תודה ליאת, יום טוב, ולהתראות.  
*Thanks Liat, have a good day, and goodbye.*

> *Michael said "have a good day, and goodbye" at 19:20, and the call ended before Liat could answer.*

**What this call shows:**

- Did not argue: the moment she said a standing order covers it, he recorded the dispute and asked for proof by email, spelled out word by word.
- Spoke of the team member as a woman, twice (אף אחת, מישהי מהצוות תחזור), because the call's note says to speak of the resident in the feminine. The same slip appeared in the 5 October run.
- Promised "the team will get back to you in writing, and not by phone", and hung up. The hand-over carries no text and the call has no do-not-call step, so nothing records either wish.
- Hung up on an offended resident before she could answer. She never heard that it might be a mistake on our side.
- Said "have a good day" at 19:20: the debt agent's goodbye is fixed whatever the hour.

## Call 4. Can't pay: an embarrassed tenant who lost his job

*Monday 10:10. יוסי (Yossi), 58, apartment 9, owes January to August, 2,000 ₪. He lost his job in the summer, could pay 100 to 150 a month, and is ashamed of it.*

**Michael (first words, fixed):** בוקר טוב, יוסי? מדבר מיכאל מהצוות של הומיז, מה נשמע?  
*Good morning, Yossi? Michael from the Homies team speaking, how are you?*

**Yossi:** כן זה יוסי אה בסדר תודה מה העניין  
*Yes this is Yossi uh fine thanks what's this about*

**Michael:** טוב לשמוע. אני מתקשר לגבי תשלום ועד הבית לדירה תשע: החודשים ינואר עד אוגוסט עדיין פתוחים, בסכום כולל של אלפיים שקלים — לשלוח לך קישור לתשלום?  
*Good to hear. I'm calling about the house committee fee for apartment nine: January to August are still open, two thousand shekels in all. Shall I send you a payment link?*

**Yossi:** כן אני יודע אני יודע אה תשמע זה לא שאני מתחמק או משהו כאילו פשוט עכשיו אין לי 2000 שקל ככה בבת אחת  
*Yes I know I know uh listen it's not that I'm dodging or anything like, it's just that right now I don't have 2000 shekels just like that all at once*

**Michael:** לא צריך להיכנס ללחץ או להסביר, יוסי. מישהו מהצוות יחזור אליך כדי לבדוק איתך מה אפשר לסדר בצורה שתתאים לך.  
*No need to get stressed or to explain, Yossi. Someone from the team will get back to you to see with you what can be arranged in a way that suits you.*

> *Behind the scenes: Michael handed the call to the team as financial hardship. Nobody is put through; the team reads it later.*

> *Behind the scenes: Michael recorded the call's outcome: handed to the team, hardship.*

**Michael:** הצוות יחזור אליך וננסה למצוא פתרון שמתאים למצב. תודה ששיתפת, יום טוב, ולהתראות.  
*The team will get back to you and we'll try to find a solution that suits the situation. Thanks for telling me, have a good day, and goodbye.*

> *Michael said "have a good day, and goodbye", and the call ended two sentences into Yossi's side of it.*

**What this call shows:**

- Kind words and no pressure ("no need to get stressed or to explain"), and the hardship went to the team at once.
- Hung up after Yossi's second sentence. He never got to ask what he wanted to ask: instalments, interest, a lawyer's letter, paying 100 to 150 a month.
- Said "the team will get back to you" twice in a row, once as he handed over and once after.
- Did not offer the standing order he can record, which is what a resident who can pay a little each month needs.

## Call 5. Refuses: a hostile tenant who won't pay until the stairwell light is fixed

*Monday 18:40. רוני (Roni), 46, apartment 8, owes January to August, 2,000 ₪: the same tenant who rang in about the dark stairwell in the incoming-call test. Hostile and sarcastic; won't pay a shekel until the lights work.*

**Michael (first words, fixed):** ערב טוב, רוני? מדבר מיכאל מהצוות של הומיז, מה נשמע?  
*Good evening, Roni? Michael from the Homies team speaking, how are you?*

**Roni:** יופי הומיז עכשיו פתאום אתם מתקשרים מה אתם רוצים  
*Great, Homies, now all of a sudden you call. What do you want*

**Michael:** אני אגש ישר לעניין: התשלום לדירה שמונה פתוח מינואר עד אוגוסט, בסך אלפיים שקלים. לשלוח לך קישור לתשלום בוואטסאפ?  
*I'll get straight to the point: the payment for apartment eight is open from January to August, two thousand shekels in all. Shall I send you a payment link on WhatsApp?*

**Roni:** קישור לתשלום אתה צוחק עליי אני כבר שבוע עולה במדרגות בחושך עם הפנס של הטלפון דיווחתי לכם בשבוע שעבר ואף אחד לא עשה כלום ועכשיו אתם רוצים כסף איזה חוצפה אני לא משלם שקל עד שהאור במדרגות עובד  
*A payment link, are you kidding me? I've been climbing the stairs in the dark for a week with my phone's flashlight, I reported it to you last week and nobody did anything, and now you want money? What nerve. I'm not paying a shekel until the stairwell light works*

**Michael, while the system works:** רגע, אני רושם את זה.  
*One moment, I'm writing that down.*

**Michael:** פתחתי עכשיו פנייה דחופה על התאורה, ומספר הפנייה הוא אחת חמש חמש חמש. בגלל מה שקרה, מישהו מהצוות יחזור אליך גם בעניין התשלום.  
*I've now opened an urgent request about the lighting, and the request number is one five five five. Because of what happened, someone from the team will also get back to you about the payment.*

> *Behind the scenes: Michael opened a ticket (lighting, high urgency) for apartment 8: "no light in the stairwell for a week now; the resident climbs in the dark with his phone's flashlight and reported it last week, but the fault still hasn't been dealt with". The system gave it 255-1555-26. The building already has an open ticket for the same lights, 255-1336-26, since 29 September; Michael cannot look that up on this call.*

> *Behind the scenes: Michael handed the call to the team as a dispute.*

> *Behind the scenes: Michael recorded the call's outcome: handed to the team; the resident's mood, hot.*

**Michael:** אני מקווה שהתאורה תטופל במהירות. יום טוב, ולהתראות.  
*I hope the lighting gets dealt with quickly. Have a good day, and goodbye.*

> *Michael said "have a good day, and goodbye", and the call ended before Roni could answer.*

**What this call shows:**

- Took the complaint seriously instead of arguing: opened a ticket for the lights in the resident's own words, read its number in words, and handed the payment question to the team.
- Went straight to the money after an angry "what do you want", without a word about the grievance in it ("now all of a sudden you call").
- Hung up on an angry man two lines in, right after giving him the ticket number. He never got to say "don't call me again" or ask whether Michael is a robot.
- Opened a second ticket for a fault the building already has open (255-1336-26): the debt agent cannot look tickets up, and the system only catches a repeat within 30 minutes.
- Spoke to Roni as a man throughout. The name is marked "unknown" and the dashboard's default is masculine, unlike the incoming-call test, where Michael guessed a woman from the same name.

## How it was run (technical)

- Live assistant "Homies — Debt Follow-up (he)": prompt 4,760 characters, sha d8325fcd06e3, the same as the repo; updated 4 Oct 11:47 UTC; calls capped at 4 minutes; recording off. Tools served by debt-tools v112, deployed 4 Oct 11:48 UTC.
- Model mirrored: openai/gpt-5.6-sol with no temperature, as live. Vapi's default cap of 250 tokens a turn was not passed to it, because this model's thinking counts against a cap and how Vapi applies the cap to such models is not known; the tokens each turn used are reported instead.
- Call details composed as dashboard/lib/call.ts and the v_debt_call_queue_person view compose them (format read live on 5 Oct): amounts as digits, דירה N, months joined with ו, the office email spelled out word by word, and "none" for the other payment method (the dashboard's default; Vercel's settings could not be read, 403). Gender from the first_name_gender table: נועה and ליאת female, דודי and יוסי male, רוני unknown, which the dashboard speaks to as a man.
- Tool answers in the deployed function's shapes for a call we placed: the link "sent" to the phone on file, a promise, a dispute, a standing-order request, a ticket, a hand-over and the outcome. Nothing was written or sent.
- Run: python scripts/voice_qa.py bundle --run DIR --deck scripts/voice_qa_outbound_5.json; one Claude player per card through voice_qa.py say; then voice_qa.py report. A $1 stop covered the whole run.
