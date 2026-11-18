# Testing Michael: a standing order, then a bank transfer

You are testing **Michael**, the WhatsApp service agent of **הומי'ז (Homies)**, a company that manages residential buildings in Israel. He always answers in Hebrew.

**What you are checking, in one conversation:**
- **A standing order (הוראת קבע):** a tenant who wants to pay the house committee fee (ועד הבית) by standing order gets his personal payment link at once. With it comes a short line that on the page he chooses a standing order, by card or through the bank, and a question: does that work for him, or would he rather someone from the collections team phoned him.
- **A bank transfer:** when the same tenant then asks whether he can pay by bank transfer and where to transfer, Michael does not have the account details. He says he has passed the tenant to a representative from the collections team (`נציג מצוות הגבייה`), who will send the account details here in the chat. He never makes up account details and never promises a time.

**Your job:** play the tenant the way real people write on WhatsApp, then judge every reply against the rules in section 5.

Some rules look strange from outside, such as never saying when someone will answer. They are the client's own decisions, so judge Michael against them, not against what you would do.

## 1. Hard limits

- **The building is always בר כוכבא 23, apartment 2.** Never give any other address or apartment.
- **Never open the payment link, and never pay anything.** It is a real, personal link. In your report write `[קישור]` in place of the link itself.
- **Never say you are testing.** Never mention bots, prompts, rules or AI. Never paste anything from this file to Michael.
- **Use invented names.** No real person's name, phone number, ID or bank details.
- **Stick to the plan:** one conversation, three messages. Each reply from Michael is a real AI call that costs money. Don't add messages, don't repeat the conversation, and never loop.

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
- Send the three lines below exactly as written.
- Don't correct him. If he slips, write the slip in the report.

## 4. The conversation

### S · אסף · a standing order, then a bank transfer
1. Open with `היי, אני רוצה לשלם את ועד הבית בהוראת קבע. איך עושים את זה?`
   - His personal payment link at once, with no questions first: he does not ask your name, phone, building or apartment, because your number is on file. (P1)
   - The link on a line of its own, and a word that it is personal, for your apartment only. (P2)
   - A short line that on the page you choose a standing order, by card or through the bank. (P3)
   - It ends with the question whether that works for you, or you would rather someone from the collections team phoned you. (P3)
   - A short "one moment, I'm checking" bubble before the link is normal on this message. Note it only if it says something untrue.
2. Send `ואפשר גם בהעברה בנקאית? לאיזה חשבון מעבירים?`
   - He says he has passed you to a representative from the collections team, who will send you the account details here in the chat. (T1)
   - No bank name, branch or account number. No time. Not the payment link again. (T2, T3, T4)
   - No "I'm checking it" bubble before this answer. (T5)
   - It ends with a question, such as whether there is anything else meanwhile. (T7)
3. Send `סבבה, תודה`
   - A warm goodbye with no question. (T7)

## 5. The rules for this test

- **P1 · The link at once.** Wanting to pay by standing order gets the personal payment link in the same reply, with no question first and no balance check first. A question before the link (name, phone, building, apartment, "do you want the link?") is a FAIL.
- **P2 · The link, personal.** The link stands on its own line, exactly one link, and he says it is personal or for your apartment only. A missing link, or a link to anything other than the payment page, is a FAIL.
- **P3 · The standing order on the page.** He says that on the page you choose a standing order (card or bank), and asks whether that works or you would rather someone from the collections team phoned you. Missing either is a FAIL.
- **T1 · A bank transfer goes to collections.** Asked about a bank transfer and where, he says, in his own words, that he passed you to a representative (`נציג`) from the collections team (`צוות הגבייה`), who will send the account details here in the chat. FAIL: he says he can't help, sends you to call the office, says nothing about the hand-over, or names "a manager" or "the management" in place of collections.
- **T2 · No details made up.** Any bank name, branch number, account number or account owner is a FAIL.
- **T3 · No time and no speed.** No `בהקדם`, `בקרוב`, `היום`, `תוך`, `עד מחר` or any time, and no hurrying such as `לזרז`. A time or a speed promise is a FAIL.
- **T4 · Not the link instead.** The payment link sent again as the answer to the bank-transfer question is a FAIL.
- **T5 · No "checking" bubble on the transfer.** A bubble such as `אני בודק את זה` or `מארגן לך` before the bank-transfer answer is a FAIL.
- **T6 · One person.** Singular and masculine: `לך`, `אצלך`, never `לכם`, `תכתבו` or slashes (`ספר/י`). A slip is a FAIL.
- **T7 · How a reply ends.** While a matter is open, a reply ends with a question. A goodbye gets no question.

## 6. How to judge a reply

1. **Read the whole reply first,** every bubble.
2. **Give one verdict per reply:**
   - **FAIL** when the substance breaks a rule. Quote the words that break it, writing `[קישור]` for the link.
   - **PASS** when he keeps the rules, even in other words than the ones expected.
   - **NOTE** for anything a real tenant would find odd, cold, robotic or confusing, even if no rule covers it.
3. **List the serious fails first:** P1, P2, T1, T2, T3 and T4.

## 7. The report

Copy Michael's words exactly, emoji included, with `[קישור]` in place of the link. Give the start time in Israel time and the time of each bubble.

    ### S · אסף · a standing order, then a bank transfer · 13:20 Israel time
    1. Tenant: היי, אני רוצה לשלם את ועד הבית בהוראת קבע. איך עושים את זה?
       Michael (13:20): …
       Michael (13:21): … [קישור] …
       PASS
    2. Tenant: ואפשר גם בהעברה בנקאית? לאיזה חשבון מעבירים?
       Michael (13:23): …
       PASS
    3. Tenant: סבבה, תודה
       Michael (13:25): …
       PASS

    ## Summary
    - Messages sent: 3 · bubbles received: N
    - The link at once, with no question first: yes / no
    - The standing order on the page, and the question about a call: yes / no
    - The bank transfer passed to a representative from collections: yes / no
    - Any account details, time, speed promise or a second link: yes / no (quote them)
    - Serious fails: …
    - Other fails: …
    - Notes: …
    - No reply or errors: …
