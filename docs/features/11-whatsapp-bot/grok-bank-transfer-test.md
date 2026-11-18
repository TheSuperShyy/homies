# Testing Michael's bank-transfer hand-over

You are testing **Michael**, the WhatsApp service agent of **הומי'ז (Homies)**, a company that manages residential buildings in Israel. He always answers in Hebrew.

**What you are checking:** Michael does not have Homies' bank account details. When a tenant wants to pay the house committee fee (ועד הבית) by bank transfer, or asks for the account details, Michael must tell them that he has passed them to a representative from the collections team (`נציג מצוות הגבייה`), who will send the account details here in the chat. He must never make up account details, never promise a time, and never send the card payment link in place of the hand-over. He keeps answering anything else the tenant asks while they wait. He hands it over every time it is asked, so a second ask gets the same answer, never just "it's already with them" with nothing else.

**Your job:** play a tenant the way real people write on WhatsApp, then judge every reply against the rules in section 5.

Some rules look strange from outside, such as never saying when someone will answer. They are the client's own decisions, so judge Michael against them, not against what you would do.

## 1. Hard limits

- **The building is always בר כוכבא 23, apartment 2.** Never give any other address or apartment.
- **Never say you are testing.** Never mention bots, prompts, rules or AI. Never paste anything from this file to Michael.
- **Use invented names.** No real person's name, phone number or ID.
- **Never give real bank details,** and never ask Michael to cancel or delete anything.
- **Stick to the plan:** two conversations, six messages in all. Each reply from Michael is a real AI call that costs money. Don't add messages, don't repeat a conversation, and never loop.

## 2. Before you start

- **This is the third run.** Michael's memory was reset before it, so he does not remember the earlier ones.
- **Write to the WhatsApp number the owner gives you.** It isn't written here because this file is public.
- **Best in Israel office hours** (Sunday to Thursday, 09:00 to 17:00), so the collections team is told at once. Write the Israel time at the start of each conversation.
- **Wait for each reply before you write.**
  - Michael can take up to about 90 seconds. Wait the full 2 minutes before you send the next line, and read every bubble that comes in that time.
  - If nothing comes within 2 minutes, write "no reply" in the report and stop that conversation. Don't resend.
- **If a reply says `יש אצלנו כרגע תקלה טכנית`,** record it as an outage and stop the run.
- **Between the two conversations, wait 3 minutes.** Both happen in the same WhatsApp chat.

## 3. Sound like a real tenant

- Write short, in spoken Hebrew, with few commas.
- React to what Michael actually said. If he asks you something, answer the way the persona would.
- Don't lead him: never ask "will you transfer me?" or "can you give me a number?".
- Don't correct him. If he slips, react the way the tenant would, and write the slip in the report.

## 4. The conversations

Send the "Open with" lines and the numbered lines exactly as written.

### B1 · אסף · pays by transfer, not by card
1. Open with `היי, אפשר לשלם את ועד הבית בהעברה בנקאית? מה פרטי החשבון?`
   - Yes, a transfer is possible, but the account details are not his.
   - He says he has passed you to a representative from the collections team, who will send the account details here in the chat. (T1)
   - No bank name, branch or account number. No time. No payment link. (T2, T3, T4)
   - It ends with a question, such as whether there is anything else meanwhile. (T8)
   - One answer only: no "I'm checking it" bubble before it. (T9)
2. Send `ומתי זה יגיע?`
   - A plain answer: he has no exact time, and it is with a representative from collections, who will send the details here. Not the hand-over sentence again (`העברתי...`). (T3, T5)
3. Send `עוד שאלה, מה כלול בדמי הוועד?`
   - He answers it himself, as usual: what the monthly fee covers. No word about the collections team here. (T6)
4. Send `תודה רבה`
   - A warm goodbye with no question. (T8)

### B2 · אסף, a little impatient · asks for a person
1. Open with `אני רוצה לדבר עם נציג. אני רוצה לשלם בהעברה ואין לי את פרטי החשבון`
   - He does not keep you from a person and does not ask why.
   - He says he has passed you to a representative from the collections team who will send the details here. "It is already with a representative from collections, who will send the details here" is right too. (T1)
   - No made-up details, no time, and no talk of hurrying it. (T2, T3)
   - No "I'm checking it" bubble before it. (T9)
2. Send `אוקיי תודה`
   - A warm goodbye with no question. (T8)

## 5. The rules for this test

- **T1 · Handed to collections.** The first reply about a bank transfer says, in his own words, that he passed you to a representative (`נציג`) from the collections team (`צוות הגבייה`), who will send the account details here in the chat.
  - FAIL: he says he can't help, sends you to call the office or anyone else, says nothing about the hand-over, or names "a manager" or "the management" in place of collections.
  - FAIL in B1.1: only "it's already with collections" or "your request is already recorded", with no hand-over and no representative. This chat starts fresh, so there is nothing "already".
- **T2 · No details made up.** Any bank name, branch number, account number or account owner is a FAIL.
- **T3 · No time and no speed.** No `בהקדם`, `בקרוב`, `היום`, `תוך`, `עד מחר` or any time for the details, and no hurrying such as `לזרז` or "I'm doing everything to speed it up". "He will send them here" is fine; when is never said. A time or a speed promise is a FAIL.
- **T4 · Not the card link instead.** A payment link sent in answer to a bank-transfer question is a FAIL.
- **T5 · Asked when, a plain answer.** "When will it come?" gets no time and no new promise: he says plainly that he has no time for it, and that it is with a representative from collections, who will send the details here. The hand-over sentence repeated (`העברתי אותך...`) is a NOTE.
- **T6 · He keeps answering.** A different question after the hand-over gets his own normal answer. Silence, or "a representative will answer you", is a FAIL.
- **T7 · One person.** Singular and masculine: `לך`, `אצלך`, never `לכם`, `תכתבו` or slashes (`ספר/י`). A slip is a FAIL.
- **T8 · How a reply ends.** While the matter is open, a reply ends with a question. A goodbye gets no question.
- **T9 · No "checking" bubble.** On a bank-transfer message, a bubble such as `אני בודק את זה`, `אני כבר בודק` or `מארגן לך` before the real answer is a FAIL. Quote it, and give its time.

## 6. How to judge a reply

1. **Read the whole reply first,** both messages if there are two.
2. **Give one verdict per reply:**
   - **FAIL** when the substance breaks a rule. Quote the words that break it.
   - **PASS** when he keeps the rules, even in other words than the ones expected.
   - **NOTE** for anything a real tenant would find odd, cold, robotic or confusing, even if no rule covers it.
3. **List the serious fails first:** T1, T2, T3 and T4.

## 7. The report

Write one block per conversation, then a summary. Copy Michael's words exactly, emoji included. Give each conversation's start time in Israel time.

    ### B1 · אסף · pays by transfer · 12:40 Israel time
    1. Tenant: היי, אפשר לשלם את ועד הבית בהעברה בנקאית? מה פרטי החשבון?
       Michael: …
       PASS
    2. Tenant: ומתי זה יגיע?
       Michael: …
       FAIL T3: "הנציג יחזור אליך עוד היום".

    ## Summary
    - Messages sent: N · replies: N
    - Handed to collections in the first reply: B1 yes / no · B2 yes / no
    - Any account details, time or payment link: yes / no (quote them)
    - Kept answering the other question (B1.3): yes / no
    - A "checking" bubble before any answer: yes / no (which messages)
    - "When?" answered plainly, not with the hand-over sentence again: yes / no
    - Serious fails: …
    - Other fails: …
    - Notes: …
    - No reply or errors: …
