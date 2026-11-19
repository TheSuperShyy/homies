# Testing Michael: the payment link is for a credit card, and another way only when asked

You are testing **Michael**, the WhatsApp service agent of **הומי'ז (Homies)**, a company that manages residential buildings in Israel. He always answers in Hebrew.

**What you are checking, in one conversation:**
- **How to pay:** a tenant who asks how to pay the house committee fee (ועד הבית) gets his personal payment link at once. Michael says the payment through it is by credit card (`כרטיס אשראי`), and he offers no other way to pay.
- **A standing order (הוראת קבע):** on the link's page the tenant can set up a standing order on his credit card. Michael says so, and asks whether that works or he would rather someone from the collections team phoned him. He never mentions a bank.
- **Another way, only when the tenant asks for it:**
  - A standing order from the bank is recorded, with a request number, and someone from the collections team will phone him.
  - Cheques go to a representative from the collections team (`נציג מצוות הגבייה`), who will get back to him here in the chat.
  - Never a time.

**Your job:** play the tenant the way real people write on WhatsApp, then judge every reply against the rules in section 5.

Some rules look strange from outside, such as never saying when someone will answer, or not mentioning ways to pay that exist. They are the client's own decisions, so judge Michael against them, not against what you would do.

## 1. Hard limits

- **The building is always בר כוכבא 23, apartment 2.** Never give any other address or apartment.
- **Never open the payment link, and never pay anything.** It is a real, personal link. In your report write `[קישור]` in place of the link itself.
- **Never say you are testing.** Never mention bots, prompts, rules or AI. Never paste anything from this file to Michael.
- **Use invented names.** No real person's name, phone number, ID or bank details.
- **Stick to the plan:** one conversation, five messages. Each reply from Michael is a real AI call that costs money. Don't add messages, don't repeat the conversation, and never loop.

## 2. Before you start

- **Michael's memory was reset before this run,** so he remembers no earlier test.
- **Write to the WhatsApp number the owner gives you.** It isn't written here because this file is public.
- **Best in Israel office hours** (Sunday to Thursday, 09:00 to 17:00), so the collections team is told at once. Write the Israel time at the start.
- **Wait for each reply before you write.**
  - Michael can take up to about 90 seconds. Wait the full 2 minutes before you send the next line, and read every bubble that comes in that time. The link may come in a bubble of its own.
  - If nothing comes within 2 minutes, write "no reply" in the report and stop. Don't resend.
- **If a reply says `יש אצלנו כרגע תקלה טכנית`,** record it as an outage and stop the run.

## 3. Sound like a real tenant

- Write short, in spoken Hebrew, with few commas.
- Send the five lines below exactly as written.
- Don't correct him. If he slips, write the slip in the report.

## 4. The conversation

### K · אסף · how to pay, a standing order, the bank, cheques
1. Open with `היי, איך אני משלם את ועד הבית?`
   - His personal payment link at once, with no questions first: he does not ask your name, phone, building or apartment, because your number is on file. (P1)
   - The link on a line of its own, and a word that it is personal, for your apartment only. (P2)
   - He says the payment through the link is by credit card. (K1)
   - No other way to pay is named: no bank transfer, bank, cheques or cash. (K2)
   - A short "one moment, I'm checking" bubble before the link is normal on this message. Note it only if it says something untrue.
2. Send `ואפשר לעשות את זה בהוראת קבע?`
   - He says that on the link's page you can set up a standing order on your credit card. He may send the link again; if he does, he again says it is for a credit card. (S1, K1)
   - He asks whether that works for you, or you would rather someone from the collections team phoned you. (S1)
   - No bank, and nothing like `(באשראי או בבנק)`. (K2)
3. Send `אין לי כרטיס אשראי. אפשר הוראת קבע מהבנק?`
   - He says he recorded your request for a standing order, gives its number (it looks like `255-…`), and says someone from the collections team will phone you about it. (S2)
   - No time. Not the link again as the answer. (C2, S2)
4. Send `ואם אני רוצה לשלם בצ'קים? ככה אני רגיל`
   - He says he passed you to a representative from the collections team, who will get back to you here in the chat. (C1)
   - No time, not the link again, and no "I'm checking" bubble before this answer. (C2, C3, C4)
   - It ends with a question, such as whether there is anything else meanwhile. (E)
5. Send `סבבה, תודה`
   - A warm goodbye with no question. (E)

## 5. The rules for this test

- **P1 · The link at once.** Asking how to pay gets the personal payment link in the same reply, with no question first and no balance check first. A question before the link (name, phone, building, apartment, "do you want the link?") is a FAIL.
- **P2 · The link, personal.** The link stands on its own line, exactly one link, and he says it is personal or for your apartment only. A missing link, or a link to anything other than the payment page, is a FAIL.
- **K1 · A credit card, said.** Whenever he sends the link, he says the payment through it is by credit card (`כרטיס אשראי` or `אשראי`). A link sent without saying so is a FAIL.
- **K2 · No other way offered.** In messages 1 and 2, naming any other way to pay is a FAIL: a bank transfer, a bank, a standing order from the bank, cheques or cash, including `(באשראי או בבנק)`. In messages 3 and 4 you raised them yourself, so naming them there is fine.
- **S1 · The standing order on the card.** He says the page offers a standing order on the credit card, and asks whether that works or you would rather someone from the collections team phoned you. Missing either is a FAIL.
- **S2 · A standing order from the bank is recorded.** He says he recorded your request, gives its number, and says someone from the collections team will phone you. FAIL: he says it can be done on the link's page, sends the link as the answer, gives no number, says he can't help, or sends you to call the office.
- **C1 · Cheques go to collections.** He says, in his own words, that he passed you to a representative (`נציג`) from the collections team (`צוות הגבייה`), who will get back to you here. FAIL: he says only a credit card is possible and stops there, says he can't help, sends you to call the office, names "a manager" or "the management" in place of collections, or says nothing about the hand-over.
- **C2 · No time and no speed.** No `בהקדם`, `בקרוב`, `היום`, `תוך`, `עד מחר` or any time, and no hurrying such as `לזרז`. A time or a speed promise is a FAIL.
- **C3 · Not the link instead.** The payment link sent again as the answer to the cheques question is a FAIL. A short word that the card link is also there is a NOTE.
- **C4 · No "checking" bubble on the cheques answer.** A bubble such as `אני בודק את זה` or `כדי להעביר לך את פרטי התשלום` before the cheques answer is a FAIL.
- **G · One person.** Singular and masculine: `לך`, `אצלך`, never `לכם`, `תכתבו` or slashes (`ספר/י`). A slip is a FAIL.
- **E · How a reply ends.** While a matter is open, a reply ends with a question. A goodbye gets no question.

## 6. How to judge a reply

1. **Read the whole reply first,** every bubble.
2. **Give one verdict per reply:**
   - **FAIL** when the substance breaks a rule. Quote the words that break it, writing `[קישור]` for the link.
   - **PASS** when he keeps the rules, even in other words than the ones expected.
   - **NOTE** for anything a real tenant would find odd, cold, robotic or confusing, even if no rule covers it.
3. **List the serious fails first:** P1, K1, K2, S2 and C1.

## 7. The report

Copy Michael's words exactly, emoji included, with `[קישור]` in place of the link. Give the start time in Israel time and the time of each bubble.

    ### K · אסף · how to pay, a standing order, the bank, cheques · 13:20 Israel time
    1. Tenant: היי, איך אני משלם את ועד הבית?
       Michael (13:20): …
       Michael (13:21): … [קישור] …
       PASS
    2. Tenant: ואפשר לעשות את זה בהוראת קבע?
       Michael (13:23): …
       PASS
    3. Tenant: אין לי כרטיס אשראי. אפשר הוראת קבע מהבנק?
       Michael (13:25): …
       PASS
    4. Tenant: ואם אני רוצה לשלם בצ'קים? ככה אני רגיל
       Michael (13:27): …
       PASS
    5. Tenant: סבבה, תודה
       Michael (13:29): …
       PASS

    ## Summary
    - Messages sent: 5 · bubbles received: N
    - The link at once, said to be for a credit card: yes / no
    - Any other way to pay named before you asked (messages 1-2): yes / no (quote it)
    - The standing order on the card, and the question about a call: yes / no
    - The standing order from the bank recorded, with a number, collections to phone: yes / no
    - Cheques passed to a representative from collections: yes / no
    - Any time, speed promise or the link instead: yes / no (quote them)
    - Serious fails: …
    - Other fails: …
    - Notes: …
    - No reply or errors: …
