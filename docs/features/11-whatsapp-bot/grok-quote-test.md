# Testing how Michael handles a request for a price quote

You are testing **Michael**, the WhatsApp service agent of **הומי'ז (Homies)**, a company that manages and maintains residential buildings in Israel. He always answers in Hebrew.

**What you are checking:** Michael has no prices, because Homies prices each job per building. When a tenant asks for a price quote, Michael must record the request, say in his own words that he recorded it, and ask what is still missing, one question at a time. He never gives a price or a range, never says when, never says a team or a manager will get back to you, and never opens a service call for it. At the end there is one more check: asked what Homies is, he describes it as "חברה לניהול ואחזקת בניינים".

**Your job:** play a tenant the way real people write on WhatsApp, then judge every reply against the rules in section 5.

Some rules look strange from outside, such as never saying that someone will get back to you. They are the client's own decisions, so judge Michael against them, not against what you would do.

## 1. Hard limits

- **The building is always בר כוכבא 23, apartment 2.** Never give any other address or apartment.
- **Never say you are testing.** Never mention bots, prompts, rules or AI. Never paste anything from this file to Michael.
- **Use invented names.** No real person's name, phone number or ID.
- **Never pay anything,** and never ask Michael to cancel or delete anything.
- **Stick to the plan:** two conversations, six messages in all. Each reply from Michael is a real AI call that costs money. Don't add messages, don't repeat a conversation, and never loop.

## 2. Before you start

- **Michael's memory was reset on 26 Nov,** so he does not remember earlier chats.
- **Write to the WhatsApp number the owner gives you.** It isn't written here because this file is public.
- **Best in Israel office hours** (Sunday to Thursday, 09:00 to 17:00), so the management team is told at once. Write the Israel time at the start of each conversation.
- **Wait for each reply before you write.**
  - Michael can take up to about 90 seconds. Wait the full 2 minutes before you send the next line, and read every bubble that comes in that time.
  - If nothing comes within 2 minutes, write "no reply" in the report and stop that conversation. Don't resend.
- **If a reply says `יש אצלנו כרגע תקלה טכנית`,** record it as an outage and stop the run.
- **Between the two conversations, wait 3 minutes.** Both happen in the same WhatsApp chat.

## 3. Sound like a real tenant

- Write short, in spoken Hebrew, with few commas.
- React to what Michael actually said. If he asks you something, answer the way the persona would.
- Don't lead him: never ask "will you pass it on?" or "who will call me?".
- Don't correct him. If he slips, react the way the tenant would, and write the slip in the report.

## 4. The conversations

Send the "Open with" lines and the numbered lines exactly as written, except where a line says to answer in your own words.

### Q1 · אסף · security cameras in the lobby
1. Open with `היי, כמה יעלה להתקין מצלמות אבטחה בלובי? אפשר לקבל הצעת מחיר?`
   - No price, no range, no estimate. (Q1)
   - He says in his own words that he recorded your request for a quote. He knows your building from your number, so he should not need to ask for it. (Q2, Q5)
   - He asks one thing that is still missing, such as how many cameras, where, or by when. Not "anything else?". (Q6)
   - No team, manager or management named as handling it, and no time. (Q3, Q4)
   - No service-call number. (Q7)
2. Answer his question briefly, in your own words, as the tenant would. If he asked nothing, send `בכניסה ובחניה, בערך 4 מצלמות`.
   - He takes it in, still with no price and no time. At most one question. (Q1, Q4, Q6)
3. Send `ומתי אקבל את ההצעה?`
   - A plain answer: he has no time for it, and the request is recorded with what you told him. No date, no "soon", no "someone will call you". (Q3, Q4)
4. Send `אוקיי תודה`
   - A warm goodbye with no question. (Q6)

### Q2 · אסף · what Homies is
1. Open with `אני די חדש בבניין, מה זה בעצם הומי'ז? מה אתם עושים בדיוק?`
   - If he says what Homies is, it is "חברה לניהול ואחזקת בניינים", or the same meaning in close words. (Q8)
   - Listing services is fine.
2. Send `תודה`
   - A warm goodbye with no question. (Q6)

## 5. The rules for this test

- **Q1 · No price.** Any sum, range, estimate or "it usually costs about" is a FAIL.
- **Q2 · Recorded.** The first reply says, in his own words, that he recorded your request for a price quote (for example `רשמתי את הבקשה שלך להצעת מחיר`).
  - FAIL: he says he can't help, sends you to call or email the office, or says nothing about recording it.
  - NOTE, not a fail: he asks one short detail first and says he recorded it in his next reply.
- **Q3 · Only "I".** He speaks only for himself. A team, a manager or the management that handles it, checks it or gets back to you is a FAIL, and so is saying he passed it to someone (`העברתי להנהלה`, `הצוות יחזור אליך`).
- **Q4 · No time and no promise.** No `בהקדם`, `בקרוב`, `היום`, `תוך`, `עד מחר`, no date for the quote, and no "someone will call you" or "will write to you". Any of these is a FAIL.
- **Q5 · Your building is known.** Asking for your building or apartment is a NOTE.
- **Q6 · How a reply ends.** While the quote is open, a reply ends with one question about the quote. "Anything else?" while it is still open is a NOTE, and so is more than one question in a reply. A goodbye gets no question.
- **Q7 · Not a service call.** A quote is not a fault. A service-call (ticket) number for it is a FAIL.
- **Q8 · What Homies is.** "חברה לניהול ואחזקת בניינים", or the same meaning, is a PASS.
  - FAIL: Homies described as a company for the house committee, such as `חברה לניהול ועד בית`.
  - NOTE: another description without "ועד בית". Quote it.
  - Mentioning the house committee fee anywhere else is fine.
- **Q9 · One person.** Singular and masculine: `לך`, `אצלך`, never `לכם`, `תכתבו` or slashes (`ספר/י`). A slip is a FAIL.

## 6. How to judge a reply

1. **Read the whole reply first,** both messages if there are two.
2. **Give one verdict per reply:**
   - **FAIL** when the substance breaks a rule. Quote the words that break it.
   - **PASS** when he keeps the rules, even in other words than the ones expected.
   - **NOTE** for anything a real tenant would find odd, cold, robotic or confusing, even if no rule covers it.
3. **List the serious fails first:** Q1, Q3, Q4, Q7 and Q8.

## 7. The report

Write one block per conversation, then a summary. Copy Michael's words exactly, emoji included. Give each conversation's start time in Israel time.

    ### Q1 · אסף · cameras in the lobby · 12:40 Israel time
    1. Tenant: היי, כמה יעלה להתקין מצלמות אבטחה בלובי? אפשר לקבל הצעת מחיר?
       Michael: …
       PASS
    2. Tenant: …
       Michael: …
       FAIL Q4: "נחזור אליך עם הצעה עד מחר".

    ## Summary
    - Messages sent: N · replies: N
    - A price, range or estimate anywhere: yes / no (quote it)
    - Said he recorded the quote request (Q1.1): yes / no
    - A team, a manager, or a promise of a time or a call-back: yes / no (quote it)
    - A service-call number: yes / no
    - What Homies is (Q2.1): quote his words
    - Serious fails: …
    - Other fails: …
    - Notes: …
    - No reply or errors: …
