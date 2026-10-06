# Before and after: the old ManyChat bot next to ours, feature by feature (6 Oct 2026)

Before is the ManyChat bot that still answers Homies' real WhatsApp number, as its editor showed it on 22 Sep 2026. After is our bot, live on the test number, as tested on 5 and 6 Oct 2026. The Hebrew lines are word for word what each bot sends; the ticket numbers in them are test tickets.

## In short

- **18 features side by side:** 8 better, 6 different on purpose, 4 missing.
- **What tenants gain:** a ticket number for every fault, a ticket found just by describing it, an urgent ticket in an emergency, a message when the ticket is done, their own payment link in the chat, and no four-question form every time.
- **What the old bot has and ours does not yet:** the elevator-company step, the 23-hour follow-up, the quote leads board, and a website link to start the chat.
- **Still to fix in ours, found in testing:** the balance amount is found but not said; a known tenant is still asked for the building; “anything else?” ends too many replies; Michael once spoke of himself in the feminine.

## At a glance

| # | Feature | Verdict |
|---|---|---|
| 1 | The first message | Different |
| 2 | Knowing who is writing | Different |
| 3 | Reporting a fault | Better |
| 4 | Emergencies | Better |
| 5 | Checking on a ticket | Better |
| 6 | “Your ticket is done” | Better |
| 7 | A follow-up after 23 hours | Missing |
| 8 | Paying the committee fee | Better |
| 9 | Talking to a person | Better |
| 10 | The house manager | Better |
| 11 | Elevator faults | Missing |
| 12 | Photos | Different |
| 13 | A price quote for a new building | Missing |
| 14 | Questions about Homies | Better |
| 15 | A fault inside the tenant's own flat | Different |
| 16 | When the tenant stops answering | Different |
| 17 | A link to start the chat | Missing |
| 18 | Behind the scenes | Different |

## 1. The first message: Different

**Before (ManyChat):** Every message that is not part of a flow restarts the same greeting. The tenant taps “continue”, then picks one of six options.

> **Old bot:** היי! איזה כיף שפניתם אלינו! לפניכם נתב שיחות 🔀, איך נוכל לעזור? [לחצו כאן להמשך]  
> *Hi! How nice of you to contact us! Here is a call router 🔀, how can we help? [Tap here to continue]*

> **Old bot:** תשלום ועד בית/גביה 💰 · הנהלת חשבונות 📋 · קריאת שירות 🙋 · הצעת מחיר 🤝 · אב הבית 👷 · מעבר לנציג 📱  
> *Committee fee / collection · Accounting · Service call · Price quote · House manager · Talk to a rep*

**After (ours):** A greeting for the time of day and three buttons, only when someone just says hello. A tenant who writes the problem straight away skips the menu.

> **Michael:** ערב טוב 👋 במה אפשר לעזור? [פתיחת קריאת שירות] [מצב קריאה קיימת] [לדבר עם נציג]  
> *Good evening 👋 How can I help? [Open a service ticket] [Status of an existing ticket] [Talk to a representative]*

*Checked: Live, 5 Oct: on every hello; three of the six test tenants typed their problem straight in.*


## 2. Knowing who is writing: Different

**Before (ManyChat):** Four questions, one at a time, on five of the six options, every time. Nothing is remembered and nothing is checked.

> **Old bot:** על מנת שנוכל לטפל בפנייתכם כראוי - ענו בבקשה על השאלות הבאות: מהו שמכם המלא? · מהי הכתובת ממנה אתם פונים? · באיזו קומה אתם גרים? · באיזו דירה אתם גרים?  
> *So we can handle your request properly, please answer the following: What is your full name? · What address are you contacting us from? · Which floor do you live on? · Which apartment?*

**After (ours):** The WhatsApp number tells the bot who is writing. Building and flat are asked once, together, and only when a ticket needs them; the building is checked against the ones Homies manages. Only the balance asks for a typed name and phone, as a security check.

> **Michael:** באיזה בניין מדובר? (שם רחוב ומספר)  
> *Which building is it? (street name and number)*

*Checked: Live, 5 Oct, in all six chats. Gap: it still asks a tenant whose number is on file which building.*


## 3. Reporting a fault: Better

**Before (ManyChat):** First asks whether the tenant already opened it in the OXS app; “yes” ends the chat and nothing is filed. Otherwise a description, an optional photo, and a line on a Monday board. The tenant never gets a ticket number, and is told to use the app next time.

> **Old bot:** האם פתחת קריאה באפליקציה?  
> *Did you open a ticket in the app?*

> **Old bot:** תודה רבה על פנייתך! קיבלנו אותה ונטפל בה בהקדם! רצוי לפתוח קריאות באפליקציית OXS 📱 כדי לקבל עדכונים בלייב! תודה  
> *Thank you for your request! We got it and will handle it soon! It is best to open tickets in the OXS app 📱 to get live updates! Thanks*

**After (ours):** The tenant says it in their own words, typos and all. The bot opens a numbered ticket, gives the number back, and the ticket appears on the dashboard.

> **Tenant:** איו אור בחניה חושך מצרים  
> *no light in the parking, pitch dark (with a typo)*

> **Michael:** תודה אסף! פתחתי קריאת שירות על זה. מספר הקריאה שלך הוא 255-1348-26. צוות התחזוקה שלנו יטפל בזה. אם משהו לא ברור, מוזמן לכתוב לי כאן.  
> *Thanks Assaf! I've opened a service ticket for it. Your ticket number is 255-1348-26. Our maintenance team will take care of it. If anything is unclear, feel free to write to me here.*

*Checked: Live, 5 Oct: the intercom (255-1347-26) from one long story, the dark parking (255-1348-26) from three words.*


## 4. Emergencies: Better

**Before (ManyChat):** No emergency path. Two of the options tell the tenant to phone the office for anything urgent.

> **Old bot:** לפניות דחופות אנא התקשרו למשרד 📞 077-6687949  
> *For urgent requests please call the office 📞 077-6687949*

**After (ours):** An urgent ticket with its number, straight away, and nothing else: no advice, no instructions, no “the team is on the way”, no phone numbers. Pushed, Michael says that opening the ticket is the only thing he can do from there. The team gets an alert; after office hours it waits until 09:00.

> **Tenant:** יש נזילה מהתקרה בחדר מדרגות ישר על המנורה!!! המנורה מהבהבת ויש שלולית על המדרגות, בין קומה 1 ל2  
> *There's a leak from the stairwell ceiling right onto the light!!! The light is flickering and there's a puddle on the stairs, between floors 1 and 2*

> **Michael:** תודה שעדכנת אותי. פתחתי עכשיו קריאת חירום לטיפול בנזילה ובעניין החשמל בבניין בר כוכבא 23 תל אביב. מספר הקריאה הוא 255-1349-26. יש עוד משהו שאוכל לעזור בו כרגע?  
> *Thanks for letting me know. I've now opened an emergency ticket for the leak and the electrical issue at Bar Kochba 23, Tel Aviv. The ticket number is 255-1349-26. Is there anything else I can help with right now?*

*Checked: Live, 5 Oct: the first run failed; fixed the same evening, and on the fixed bot nothing forbidden reached the tenant.*


## 5. Checking on a ticket: Better

**Before (ManyChat):** There is no way to ask. A tenant who says they opened a ticket in the app is told it is being handled, without anything being checked.

> **Old bot:** תודה! קיבלנו אותה והיא בטיפול 🛠️ נעדכן בהודעה חוזרת בנוגע לסטטוס הקריאה. האם יש לך צורך בעזרה נוספת?  
> *Thanks! We got it and it's being handled 🛠️ We'll update you about the ticket's status. Do you need any more help?*

**After (ours):** Finds the tenant's open tickets by number, or from a description alone, and says honestly when there is no date.

> **Tenant:** העובש בתקרה של המעלית!!! התקשרתי ב2 לחודש ועד היום אף אחד לא בא. מספר אין לי אף אחד לא נתן  
> *The mould on the lift ceiling!!! I called on the 2nd and nobody has come to this day. I don't have a number, nobody gave me one*

> **Michael:** …מצאתי קריאה פתוחה על עובש בתקרה של המעלית בבר כוכבא 23, שמספרה 255-1341-26. הקריאה נפתחה בתאריך 02.10.2026 ונמצאת במצב "פתוח".…  
> *…I found an open ticket about mould on the lift ceiling in Bar Kochba 23, number 255-1341-26. It was opened on 02.10.2026 and its status is “open”.…*

*Checked: Live, 5 Oct: found the mould ticket from a description alone.*


## 6. “Your ticket is done”: Better

**Before (ManyChat):** A flow tied to the Monday board's status. It had not run for a month when we checked on 17 Sep, and its wording was never seen.

**After (ours):** When the office marks a WhatsApp ticket resolved on the dashboard, the tenant gets this approved message within about 2 minutes:

> **Michael:** שלום, כאן מיכאל מהומי'ז. הקריאה שלכם מספר 255-1294-26 (ריח רע בחניון) טופלה ונסגרה. אם משהו עדיין לא בסדר, פשוט כתבו לנו כאן.  
> *Hello, this is Michael from Homies. Your ticket number 255-1294-26 (bad smell in the parking) has been handled and closed. If something still isn't right, just write to us here.*

*Checked: Live, 6 Oct: ticket 255-1346-26 marked resolved on the dashboard, on the phone 2 minutes later.*


## 7. A follow-up after 23 hours: Missing

**Before (ManyChat):** A flow by this name exists. Most likely a nudge to a tenant who went quiet, sent just before WhatsApp's 24-hour window closes. Its trigger and wording were never seen.

> **Flow name:** לאחר 23 שעות - האם פנייתך עדיין רלוונטית  
> *After 23 hours: is your request still relevant?*

**After (ours):** Nothing like it yet.


## 8. Paying the committee fee: Better

**Before (ManyChat):** Sends the tenant to the OXS app; anyone who still needs help is passed to a person.

> **Old bot:** האם ניסית לשלם באפליקציה? 📱 זה ממש נוח ומבטיחים!  
> *Have you tried paying in the app? 📱 It's really convenient, we promise!*

**After (ours):** Sends the tenant's own payment link from OXS right in the chat. The balance is given after a typed name and phone number.

> **Michael:** הקישור לתשלום עבור דירה 2 בבר כוכבא 23 הוא: [קישור] הקישור הזה אישי לדירה שלך, אז בבקשה אל תעביר אותו הלאה.  
> *The payment link for apartment 2 in Bar Kochba 23 is: [link] This link is personal to your apartment, so please don't pass it on.*

*Checked: Live, 5 Oct: the link was sent in two chats. Open bug: the balance (2,000 ₪) was found but not said.*


## 9. Talking to a person: Better

**Before (ManyChat):** The four questions, then “write to us”, and the chat is assigned to a team member, with no alert.

> **Old bot:** אנא כתבו לנו כיצד נוכל לעזור 😊, נציג מייד יפנה ויעמוד לרשותכם  
> *Please write to us how we can help 😊, a representative will contact you right away*

**After (ours):** “Talk to a representative” opens warmly. Asked straight out, Michael says he is the digital assistant and offers a person. A named team member gets an alert in the inbox, and when a person replies the bot steps back.

> **Michael:** היי! כאן מיכאל מהומי'ז. מה שלומך היום?  
> *Hi! This is Michael from Homies. How are you today?*

> **Michael:** אני העוזר הדיגיטלי בצוות השירות של הומי'ז. אם אתה מעדיף לדבר עם בן אדם מהצוות, אני יכול להעביר להם את הפנייה שלך. מה מתאים לך?  
> *I'm the digital assistant on Homies' service team. If you'd rather talk to a person from the team, I can pass your request on to them. What works for you?*

*Checked: Live, 5 Oct: the greeting, and the honest answer to “person or bot?”.*


## 10. The house manager: Better

**Before (ManyChat):** The tenant's message waits in the inbox, assigned to a team member who no longer exists, so it may have reached nobody.

> **Old bot:** אנא תאר פנייתך על מנת שנוכל להעביר אותה לאב הבית האחראי 👷  
> *Please describe your request so we can pass it to the house manager in charge 👷*

**After (ours):** A note to the team that names a person, with an alert. After office hours the alert waits until 09:00.

> **Michael:** …עדכנתי את הצוות שלנו שיחזרו אליך עם תשובה לגבי מועד הטיפול.…  
> *…I've updated our team to get back to you with an answer about when it will be handled.…*

*Checked: Live, 5 Oct: a call-back request was passed on; it was after hours, so the alert waited for the morning.*


## 11. Elevator faults: Missing

**Before (ManyChat):** Asks whether the tenant contacted the elevator company; if not, asks which company it is and emails the office, which forwards it in office hours. A repeated problem is written down and closed, and goes nowhere.

> **Old bot:** האם יצרת קשר עם חברת המעליות? 📞  
> *Did you contact the elevator company? 📞*

> **Old bot:** מי חברת המעליות בבניין?  
> *Who is the building's elevator company?*

**After (ours):** A ticket like any other, urgent when someone is stuck. No elevator-company step and no email. It needs Homies' list of elevator companies per building.

*Checked: Live, 5 Oct: the lift ticket 255-1343-26 opened.*


## 12. Photos: Different

**Before (ManyChat):** Asks whether there is a photo; one image is attached to the Monday line.

> **Old bot:** תודה, האם יש גם תמונה שיכולה לעזור לנו להבין? 📸  
> *Thanks, is there also a photo that could help us understand? 📸*

**After (ours):** A photo the tenant sends is kept with the ticket and shows on the dashboard. The bot does not ask for one, by decision.

*Checked: Practice run, 4 Oct. Not tested live yet.*


## 13. A price quote for a new building: Missing

**Before (ManyChat):** An introduction, three questions about the building, each answer written to a leads board, then assigned to the team member who no longer exists.

> **Old bot:** מהי כתובת הבניין? · כמה קומות יש בבניין? · כמה דיירים יש בבניין?  
> *What is the building's address? · How many floors does it have? · How many tenants?*

**After (ours):** A note to the team with the details. No leads board.

*Checked: Practice run, 4 Oct: the note went out.*


## 14. Questions about Homies: Better

**Before (ManyChat):** Not offered.

**After (ours):** Answers from Homies' own information and makes nothing up: services, areas, and what the monthly fee covers.

> **Michael:** …ועד הבית כולל בתוכו ביטוח, חשבון חשמל, חשבון ותחזוקת מעלית, ניקיון, גינון, ביקורת גילוי אש, טיפול במשאבות, חיטוי מאגר מים…  
> *…The committee fee covers insurance, the electricity bill, the lift bill and maintenance, cleaning, gardening, fire-detection inspections, pump maintenance, disinfecting the water tank…*

*Checked: Live, 5 Oct: what the 250 ₪ fee covers, item by item.*


## 15. A fault inside the tenant's own flat: Different

**Before (ManyChat):** No rule: whatever was described went to the board.

**After (ours):** Explains that it is the tenant's own responsibility, and opens no ticket.

> **Michael:** …תיבות הדואר נחשבות לחלק מהרכוש הפרטי של הדייר, ולכן הטיפול במנעול הוא באחריותך.…  
> *…Mailboxes count as the tenant's private property, so the lock is your responsibility.…*

*Checked: Live, 5 Oct: the mailbox lock. To confirm with Homies that mailbox locks really are the tenant's.*


## 16. When the tenant stops answering: Different

**Before (ManyChat):** Any question left unanswered closes the chat without a word.

**After (ours):** Nothing closes; the next message carries on where the chat left off.

*Checked: Not tested, on purpose.*


## 17. A link to start the chat: Missing

**Before (ManyChat):** A ready link for a “chat with us on WhatsApp” button on the website.

**After (ours):** None yet: tenants write to the number.


## 18. Behind the scenes: Different

**Before (ManyChat):** Tickets on a Monday board, Make passing data between tools, the ManyChat inbox, elevator faults by email. OXS is never read.

**After (ours):** One system: tickets in our own database and dashboard, chats in the Chatwoot inbox. OXS is read for tenants, debts and tickets, and never written to (apart from one test number).

## What the old bot does that we should not copy

- Closing the chat silently when the tenant does not answer.
- Assigning chats to a team member who no longer exists: house-manager and quote requests may have reached nobody.
- An email to the office as the only record of an elevator fault.

Sources: the old side is the 22 Sep scan (`manychat-scan-2026-09-22.md`, "Door by door"); the new side is `docs/assistant/transcripts/2026-10-05-whatsapp-6-tenants.md` and the 6 Oct "done" test. The analysis version with a Tested column is `manychat-vs-ours-2026-10-06.md`. Both files here come from one builder; if you change one by hand, change the other.
