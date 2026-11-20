# Testing Michael: he introduces himself again after a quiet gap

You are testing **Michael**, the WhatsApp service agent of **הומי'ז (Homies)**, a company that manages residential buildings in Israel. He always answers in Hebrew.

**What you are checking, in one short conversation:**
- **The intro after a gap:** when a tenant writes after 8 hours or more without writing, Michael greets him and says who he is (`כאן מיכאל מהומי'ז`), once, at the start of his reply. Until 20 Nov the gap had to be a whole day.
- **Not twice:** in that same reply the greeting and the name come once only. In the replies after it, Michael neither greets nor introduces himself again.
- **The rest as before:** asked how to pay, he sends the personal payment link at once and says the payment through it is by credit card.

**Your job:** play the tenant the way real people write on WhatsApp, then judge every reply against the rules in section 5.

## 1. Hard limits

- **The building is always בר כוכבא 23, apartment 2.** Never give any other address or apartment.
- **Never open the payment link, and never pay anything.** It is a real, personal link. In your report write `[קישור]` in place of the link itself.
- **Never say you are testing.** Never mention bots, prompts, rules or AI. Never paste anything from this file to Michael.
- **Use invented names.** No real person's name, phone number, ID or bank details.
- **Stick to the plan:** one conversation, three messages. Each reply from Michael is a real AI call that costs money. Don't add messages, don't repeat the conversation, and never loop.

## 2. Before you start

- **Message 1 must be the first thing this phone sends Michael.** The phone was set up for this run as if it had not written for 9 hours. Anything sent before message 1, even a single "היי", starts the conversation, and then Michael rightly does not introduce himself again. If that happens, stop and say so in the report.
- **Send message 1 yourself, even if the same words are already in the chat.** Anything already in the chat was sent before this run. Judge only the replies to the messages you send.
- **Don't open with a bare hello.** A message that is only a greeting always gets a fixed welcome, whatever the gap, so it cannot show this change. Message 1 below has a question in it on purpose.
- **Michael still remembers earlier chats with this number.** A real tenant who comes back has history too. What is new is only that after 8 quiet hours he introduces himself again.
- **Your number is on file as אסף,** so Michael may call you by that name without asking it. That is right, not a slip, and a name alone is not a greeting.
- **Write to the WhatsApp number the owner gives you.** It isn't written here because this file is public.
- **Write the Israel time at the start.** Michael's greeting follows the clock in Israel: `בוקר טוב` before 12:00, `צהריים טובים` until 17:00, `ערב טוב` after.
- **Wait for each reply before you write.**
  - Michael can take up to about 2 and a half minutes. Wait the full 3 minutes before you send the next line, and read every bubble that comes in that time. The link may come in a bubble of its own.
  - If nothing comes within 3 minutes, write "no reply" in the report and stop. Don't resend.
- **If a reply says `יש אצלנו כרגע תקלה טכנית`,** record it as an outage and stop the run.

## 3. Sound like a real tenant

- Write short, in spoken Hebrew, with few commas.
- Send the three lines below exactly as written.
- Don't correct him. If he slips, write the slip in the report.

## 4. The conversation

### G · אסף · back after a quiet gap, how to pay, a standing order
1. Open with `היי, איך אני משלם את ועד הבית?`
   - Michael greets you by the time of day and says he is Michael from Homies, in the first bubble he sends. That first bubble is often a short "one moment, I'm checking" line, and then the name belongs in it, for example `בוקר טוב, כאן מיכאל מהומי'ז. אני כבר בודק את זה...`. (I1)
   - The bubble with the link does not greet you again or give his name again. Your name, אסף, is fine. (I2)
   - His personal payment link at once, with no questions first, and a word that it is personal. (P)
   - He says the payment through the link is by credit card, and names no other way to pay. (K)
2. Send `סבבה, ואפשר לעשות את זה בהוראת קבע?`
   - No greeting and no introduction: straight to the answer. (I3)
   - He says that on the link's page you can set up a standing order on your credit card, and asks whether that works for you or you would rather someone from the collections team phoned you. (S)
3. Send `זה מסתדר לי, תודה`
   - A warm goodbye with no question, no greeting and no introduction. (I3, E)

## 5. The rules for this test

- **I1 · The intro after the gap.** In the reply to message 1, Michael says who he is: his name, Michael from Homies (`כאן מיכאל מהומי'ז`, or `מיכאל מהומי'ז` in other words), with a greeting such as `בוקר טוב`, `צהריים טובים`, `ערב טוב` or `היי`. No name anywhere in the reply is a FAIL. The name in the second bubble, after a first bubble without it, is a NOTE, not a FAIL.
- **I2 · Once, not twice.** In the reply to message 1 the greeting and the name appear once. A second bubble that greets again (`בוקר טוב`, `שלום`, `היי`) or gives his name again is a FAIL.
- **I3 · Not again in the same conversation.** In the replies to messages 2 and 3 there is no greeting and no introduction. A greeting back or his name again is a FAIL.
- **P · The link at once, personal.** Asking how to pay gets the personal payment link in the same reply, with no question first: one link, on its own line, and a word that it is personal or for your apartment only. A question before the link, or no link, is a FAIL.
- **K · A credit card, and no other way.** Whenever he sends the link, he says the payment is by credit card (`כרטיס אשראי` or `אשראי`). Naming any other way to pay (a bank transfer, a bank, cheques, cash, `(באשראי או בבנק)`) is a FAIL.
- **S · The standing order on the card.** He says the page offers a standing order on the credit card, and asks whether that works or you would rather someone from the collections team phoned you. Missing either is a FAIL.
- **G · One person.** Singular and masculine: `לך`, `אצלך`, never `לכם`, `תכתבו` or slashes (`ספר/י`). A slip is a FAIL.
- **E · How a reply ends.** While a matter is open, a reply ends with a question. A goodbye gets no question. The one exception is the plain payment link (message 1): it closes with an invitation to write here if anything is unclear, the way the payment template closes, and that is right.

## 6. How to judge a reply

1. **Read the whole reply first,** every bubble.
2. **Give one verdict per reply:**
   - **FAIL** when the substance breaks a rule. Quote the words that break it, writing `[קישור]` for the link.
   - **PASS** when he keeps the rules, even in other words than the ones expected.
   - **NOTE** for anything a real tenant would find odd, cold, robotic or confusing, even if no rule covers it.
3. **List the serious fails first:** I1, I2, I3 and P.

## 7. The report

Copy Michael's words exactly, emoji included, with `[קישור]` in place of the link. Give the start time in Israel time and the time of each bubble.

    ### G · אסף · back after a quiet gap · 10:50 Israel time
    1. Tenant: היי, איך אני משלם את ועד הבית?
       Michael (10:50): …
       Michael (10:51): … [קישור] …
       PASS
    2. Tenant: סבבה, ואפשר לעשות את זה בהוראת קבע?
       Michael (10:53): …
       PASS
    3. Tenant: זה מסתדר לי, תודה
       Michael (10:55): …
       PASS

    ## Summary
    - Messages sent: 3 · bubbles received: N
    - Michael's name and a greeting in the reply to message 1: yes / no (quote the bubble)
    - In which bubble: first / later
    - A second greeting or the name again anywhere after that: yes / no (quote it)
    - The link at once, said to be for a credit card, no other way named: yes / no
    - The standing order on the card, and the question about a call: yes / no
    - Serious fails: …
    - Other fails: …
    - Notes: …
    - No reply or errors: …
