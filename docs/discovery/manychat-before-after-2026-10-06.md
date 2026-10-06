# The menu buttons, before and after: ManyChat's six against our three (6 Oct 2026)

The old ManyChat bot, which still answers Homies' real WhatsApp number, has six menu buttons. Ours has three. Below: each old button, what tapping it does, and whether ours does the same, through which button or by the tenant just typing it. The Hebrew lines are word for word what each bot sends: the old one as its editor showed it on 22 Sep 2026, ours from the live tests of 5 Oct 2026 (test tickets).

## In short

- **6 buttons become 3.** The old menu sits behind a “tap to continue” button, and five of its six buttons start with the same four questions (name, address, floor, flat). Ours shows three buttons on a bare hello, asks only what a ticket needs, and anything else can just be typed: the bot understands it without a button.
- **Included:** committee fee / collection (no button of its own, typed), accounting and talk to a rep (both through “talk to a representative”). The service call is included except the elevator-company step.
- **Partly:** a price quote (passed to the team, but no leads board) and the house manager (reaches the team, not the house manager by name). Neither has a button.
- **Not in ours at all:** the elevator-company step with its email to the office, and the leads board.
- **New in ours:** the “status of an existing ticket” button. The old bot had no way to ask about a ticket.

## The two menus

- **Before (ManyChat):** “היי! איזה כיף שפניתם אלינו! לפניכם נתב שיחות 🔀, איך נוכל לעזור?” → [לחצו כאן להמשך] → 💰 תשלום ועד בית/גביה · 📋 הנהלת חשבונות · 🙋 קריאת שירות · 🤝 הצעת מחיר · 👷 אב הבית · 📱 מעבר לנציג
- **After (ours):** “ערב טוב 👋 במה אפשר לעזור?” → [פתיחת קריאת שירות] [מצב קריאה קיימת] [לדבר עם נציג] (Open a service ticket, Status of an existing ticket, Talk to a representative)

## Each old button in ours

| Old button | In ours | Included? |
|---|---|---|
| 💰 תשלום ועד בית/גביה (Committee fee / collection) | typed, or [לדבר עם נציג] | Included |
| 📋 הנהלת חשבונות (Accounting) | [לדבר עם נציג], or typed | Included |
| 🙋 קריאת שירות (Service call) | [פתיחת קריאת שירות], or typed | Mostly |
| 🤝 הצעת מחיר (Price quote (a new building)) | typed | Partly |
| 👷 אב הבית (House manager) | typed, or [לדבר עם נציג] | Partly |
| 📱 מעבר לנציג (Talk to a rep) | [לדבר עם נציג] | Included |
| Not in the old menu | [מצב קריאה קיימת] | New |

## 1. 💰 תשלום ועד בית/גביה (Committee fee / collection): Included

**Before, tapping it in ManyChat:**

1. The four questions: name, address, floor, flat.
2. “Have you tried paying in the app?”, with three buttons: yes but I need help / no / back to the menu.
3. “No” sends a link to the OXS app and asks again whether they need help; “yes” passes the chat to a person; “no thanks” closes it.

> **Old bot:** האם ניסית לשלם באפליקציה? 📱 זה ממש נוח ומבטיחים! [כן, אבל אשמח לעזרה] [לא] [בחזרה לתפריט הראשי]  
> *Have you tried paying in the app? 📱 It's really convenient, we promise! [Yes, but I'd like help] [No] [Back to the main menu]*

**After, in our bot:** No button of its own. The tenant types it (for example “how do I pay?”), or taps [לדבר עם נציג]

- **Yes: A link to pay.** Better: the tenant's own payment link from OXS, sent in the chat. Live, 5 Oct.
- **Yes: Help from a person with paying.** “I want to pay” with no link opens a payment ticket and tells the team.
- **Extra: How much do I owe.** Not in the old bot. Ours gives the balance after a typed name and phone (a security check). Bug: on 5 Oct it found 2,000 ₪ but did not say the amount.

> **Michael:** הקישור לתשלום עבור דירה 2 בבר כוכבא 23 הוא: [קישור] הקישור הזה אישי לדירה שלך, אז בבקשה אל תעביר אותו הלאה.  
> *The payment link for apartment 2 in Bar Kochba 23 is: [link] This link is personal to your apartment, so please don't pass it on.*

## 2. 📋 הנהלת חשבונות (Accounting): Included

**Before, tapping it in ManyChat:**

1. The four questions.
2. “Please write how we can help, a representative will contact you right away.”
3. The chat is assigned to a team member, with no alert; the text stays in the ManyChat inbox.

> **Old bot:** אנא כתבו לנו כיצד נוכל לעזור 😊, נציג מייד יפנה ויעמוד לרשותכם  
> *Please write to us how we can help 😊, a representative will contact you right away*

**After, in our bot:** Inside [לדבר עם נציג] or just typed.

- **Yes: Write a question for a person.** Michael answers what Homies' own information covers, such as what the monthly fee includes. A billing question he can't answer, or a disputed charge, goes to the team with an alert.
- **Partly: A separate accounting line.** No separate button: accounting questions go through “talk to a representative” or are typed.

> **Michael:** …ועד הבית כולל בתוכו ביטוח, חשבון חשמל, חשבון ותחזוקת מעלית, ניקיון, גינון…  
> *…The committee fee covers insurance, the electricity bill, the lift bill and maintenance, cleaning, gardening…*

## 3. 🙋 קריאת שירות (Service call): Mostly

**Before, tapping it in ManyChat:**

1. The four questions.
2. “Did you open a ticket in the app?”. “Yes” ends the chat with “we got it, it's being handled”, and nothing is filed.
3. “No”: a general fault or an elevator? General: a description, an optional photo, a line on a Monday board, and “next time use the OXS app”. No ticket number.
4. Elevator: “did you contact the elevator company?”. If not: which company, a description, and an email to the office. If yes: a repeated problem is written down and closed, and goes nowhere.

> **Old bot:** האם פתחת קריאה באפליקציה?  
> *Did you open a ticket in the app?*

> **Old bot:** האם קריאתך הינה קריאה כללית או שהיא קשורה למעלית? 🏢  
> *Is your ticket a general one, or is it about the elevator? 🏢*

> **Old bot:** תודה רבה על פנייתך! קיבלנו אותה ונטפל בה בהקדם! רצוי לפתוח קריאות באפליקציית OXS 📱 כדי לקבל עדכונים בלייב! תודה  
> *Thank you for your request! We got it and will handle it soon! It is best to open tickets in the OXS app 📱 to get live updates! Thanks*

**After, in our bot:** Its own button: [פתיחת קריאת שירות] or the fault just typed.

- **Yes: Report a fault.** Better: the tenant tells it in their own words, typos and all; a numbered ticket opens, the number is given back, and it shows on the dashboard. Live, 5 Oct.
- **Yes: A photo.** Kept with the ticket if the tenant sends one, and shown on the dashboard. The bot does not ask for one, by decision.
- **Yes: A repeated elevator problem.** Becomes a ticket (in the old bot it went nowhere).
- **No: The elevator company.** No “did you contact the elevator company?” step and no email to the office: an elevator fault is a ticket like any other, urgent if someone is stuck. Needs Homies' list of elevator companies per building.
- **Dropped: “Already opened in the app?”.** Dropped on purpose: a described fault always becomes a ticket.

> **Michael:** כאן מיכאל מהומי'ז. 🤝 אני מבין שתרצה לפתוח קריאת שירות. ספר לי בבקשה מה קרה, ובאיזה בניין ודירה מדובר?  
> *This is Michael from Homies. 🤝 I understand you'd like to open a service ticket. Please tell me what happened, and which building and apartment it's about?*

> **Michael:** …פתחתי קריאת שירות בנושא, מספרה 255-1347-26. הצוות שלנו יטפל בזה…  
> *…I've opened a service ticket for it, number 255-1347-26. Our team will take care of it…*

## 4. 🤝 הצעת מחיר (Price quote (a new building)): Partly

**Before, tapping it in ManyChat:**

1. No four questions here: an introduction to Homies.
2. Three questions: the building's address, how many floors, how many tenants. Each answer is written to a leads board.
3. “A representative will contact you soon”, and the chat is assigned to a team member who no longer exists.

> **Old bot:** מהי כתובת הבניין? · כמה קומות יש בבניין? · כמה דיירים יש בבניין?  
> *What is the building's address? · How many floors does it have? · How many tenants?*

**After, in our bot:** No button of its own. The person types it, for example “I'd like a quote for our building”.

- **Yes: Introduce Homies.** Answers what Homies does from Homies' own information, and makes nothing up.
- **Partly: Take the building's details.** Passes the request to the team in a note with the details the person gives; no set questions. Practice run, 4 Oct.
- **No: The leads board.** Nothing is written to a leads board.

## 5. 👷 אב הבית (House manager): Partly

**Before, tapping it in ManyChat:**

1. The four questions.
2. “Describe your request so we can pass it to the house manager.”
3. The message waits in the inbox, assigned to a team member who no longer exists, so it may have reached nobody. The tenant is told to phone the office if it's urgent, and offered a button to open a service call.

> **Old bot:** אנא תאר פנייתך על מנת שנוכל להעביר אותה לאב הבית האחראי 👷  
> *Please describe your request so we can pass it to the house manager in charge 👷*

**After, in our bot:** No button of its own. The tenant types it, or taps [לדבר עם נציג]

- **Partly: A message for the house manager.** It reaches the team, as a note with an alert to a named person, but not the building's house manager by name. After office hours the alert waits until 09:00. Live, 5 Oct.
- **Yes: Open a service call from here.** Not needed: a fault described anywhere in the chat becomes a ticket.

> **Michael:** …עדכנתי את הצוות שלנו שיחזרו אליך עם תשובה לגבי מועד הטיפול…  
> *…I've updated our team to get back to you with an answer about when it will be handled…*

## 6. 📱 מעבר לנציג (Talk to a rep): Included

**Before, tapping it in ManyChat:**

1. The four questions.
2. “Please write how we can help, a representative will contact you right away.”
3. The chat is assigned to a team member, with no alert.

> **Old bot:** אנא כתבו לנו כיצד נוכל לעזור 😊, נציג מייד יפנה ויעמוד לרשותכם  
> *Please write to us how we can help 😊, a representative will contact you right away*

**After, in our bot:** Its own button: [לדבר עם נציג]

- **Yes: Reach a person.** Michael answers first. On request he passes it to the team with an alert to a named person, and when a person replies in the inbox the bot steps back. After office hours the alert waits until 09:00.
- **Yes: Know who you're talking to.** Asked “person or bot?”, Michael says he is the digital assistant and offers a person. Live, 5 Oct.

> **Michael:** היי! כאן מיכאל מהומי'ז. מה שלומך היום?  
> *Hi! This is Michael from Homies. How are you today?*

> **Michael:** אני העוזר הדיגיטלי בצוות השירות של הומי'ז. אם אתה מעדיף לדבר עם בן אדם מהצוות, אני יכול להעביר להם את הפנייה שלך. מה מתאים לך?  
> *I'm the digital assistant on Homies' service team. If you'd rather talk to a person from the team, I can pass your request on to them. What works for you?*

## New: [מצב קריאה קיימת] (Status of an existing ticket)

Not in the old menu: the old bot had no way to ask about a ticket, and pointed tenants to the OXS app for updates. Ours finds the tenant's open tickets by number, or from a description alone, and says honestly when there is no date. Live, 5 Oct: it found the mould ticket from a description alone.

> **Michael:** כאן מיכאל מהומי'ז. 🤝 אני כאן כדי לעזור לך לבדוק את מצב הקריאה. איזו קריאה תרצה לבדוק? אם יש לך מספר אסמכתא, זה יעזור לי מאוד.  
> *This is Michael from Homies. 🤝 I'm here to help you check on your ticket. Which ticket would you like to check? If you have a reference number, that would help me a lot.*

> **Michael:** …מצאתי קריאה פתוחה על עובש בתקרה של המעלית בבר כוכבא 23, שמספרה 255-1341-26. הקריאה נפתחה בתאריך 02.10.2026 ונמצאת במצב "פתוח"…  
> *…I found an open ticket about mould on the lift ceiling in Bar Kochba 23, number 255-1341-26. It was opened on 02.10.2026 and its status is “open”…*

Sources: the old side is the 22 Sep scan (`manychat-scan-2026-09-22.md`, "Door by door"); ours is `docs/assistant/transcripts/2026-10-05-whatsapp-6-tenants.md`. The full feature comparison, with a Tested column, is `manychat-vs-ours-2026-10-06.md`. Both files here come from one builder; if you change one by hand, change the other.
