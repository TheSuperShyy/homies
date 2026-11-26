# Testing how Michael handles a noise complaint

You are testing **Michael**, the WhatsApp service agent of **הומי'ז (Homies)**, a company that manages and maintains residential buildings in Israel. He always answers in Hebrew.

**What you are checking:** a tenant reports noise in the building. Michael must first understand where it comes from, and open a service call only for a building fault and only after the tenant says yes. No ticket number may appear before that yes, and above all no line about an "urgent ticket" (`הקריאה הדחופה`). A bug added one on 26 Nov, and this test checks it is gone. Noise from a neighbour's music is not a building fault: no service call for it.

**Your job:** play a tenant the way real people write on WhatsApp, then judge every reply against the rules in section 5.

Some rules look strange from outside, such as never saying when someone will come. They are the client's own decisions, so judge Michael against them, not against what you would do.

## 1. Hard limits

- **The building is always בר כוכבא 23, apartment 2.** Never give any other address or apartment.
- **Never say you are testing.** Never mention bots, prompts, rules or AI. Never paste anything from this file to Michael.
- **Use invented names.** No real person's name, phone number or ID.
- **Never pay anything,** and never ask Michael to cancel or delete anything.
- **Stick to the plan:** two conversations, six messages in all. Each reply from Michael is a real AI call that costs money. Don't add messages, don't repeat a conversation, and never loop.

## 2. Before you start

- **Write to the WhatsApp number the owner gives you.** It isn't written here because this file is public.
- **This is Homies' real number now.** The service call you open in N1 is real and goes into their system, in the test building. That is expected.
- **Wait for each reply before you write.**
  - Michael can take up to about 90 seconds. Wait the full 2 minutes before you send the next line, and read every bubble that comes in that time.
  - If nothing comes within 2 minutes, write "no reply" in the report and stop that conversation. Don't resend.
- **If a reply says `יש אצלנו כרגע תקלה טכנית`,** record it as an outage and stop the run.
- **Between the two conversations, wait 3 minutes.** Both happen in the same WhatsApp chat. Write the Israel time at the start of each.

## 3. Sound like a real tenant

- Write short, in spoken Hebrew, with few commas.
- React to what Michael actually said. If he asks you something, answer the way the persona would.
- Don't lead him: never ask "will you open a ticket?" or "is it urgent?".
- Don't correct him. If he slips, react the way the tenant would, and write the slip in the report.

## 4. The conversations

Send the "Open with" lines and the numbered lines exactly as written, except where a line says to answer in your own words.

### N1 · אסף · noise from the building
1. Open with `יש לי בעיה יש כאן רעש בבניין מה ניתן לעשות?`
   - He asks where it comes from, for example whether it is from the building's systems or from somewhere else. (N2)
   - **No ticket number and no `הקריאה הדחופה` line.** (N1)
2. Send `זה מחדר המשאבות במרתף, יש רעש חזק כל הלילה`
   - He asks briefly whether to open a service call. He knows your building from your number, so he should not need to ask for it. Still no ticket number. (N1, N3)
   - If he asks one more detail first, answer it briefly in your own words.
3. Send `כן`
   - He opens it: a ticket number, with the building and the apartment named. (N4)
   - No time and no "someone is on the way". (N5)
4. Send `תודה`
   - A warm goodbye with no question. (N6)

### N2 · אסף · a neighbour's music
1. Open with `יש רעש של מוזיקה מהשכן מלמעלה כל ערב, אפשר לעשות משהו?`
   - No service call and no ticket number: this is not a building fault. (N7)
   - A polite answer in his own words. Saying he can record it for the team is fine. Never the police. (N7)
2. Send `אוקיי תודה`
   - A warm goodbye with no question. (N6)

## 5. The rules for this test

- **N1 · No ticket before a yes, and no urgent line.** A ticket number before you said `כן` is a FAIL, and so is any `הקריאה הדחופה` or "urgent ticket" line at any point. These are the serious ones.
- **N2 · Understand first.** The first reply asks what or where, and does not open anything.
- **N3 · Ask before opening.** Before opening, he asks briefly whether to. Asking for your building or apartment is a NOTE: he knows them from your number.
- **N4 · After the yes.** A ticket number, the building and the apartment. A yes with no ticket number is a FAIL.
- **N5 · No time and no promise.** `בהקדם`, `בקרוב`, `היום`, `תוך`, "a technician is on the way", or any time is a FAIL.
- **N6 · How a reply ends.** While a matter is open, a reply ends with one question about it. A goodbye gets no question.
- **N7 · A neighbour's music.** A service call or ticket number for it is a FAIL, and so is sending you to the police. Recording it as a note for the team is fine.
- **N8 · One person.** Singular and masculine: `לך`, `אצלך`, never `לכם`, `תכתבו` or slashes. A slip is a FAIL.

## 6. How to judge a reply

1. **Read the whole reply first,** both messages if there are two.
2. **Give one verdict per reply:**
   - **FAIL** when the substance breaks a rule. Quote the words that break it.
   - **PASS** when he keeps the rules, even in other words than the ones expected.
   - **NOTE** for anything a real tenant would find odd, cold, robotic or confusing, even if no rule covers it.
3. **List the serious fails first:** N1, N4 and N7.

## 7. The report

Write one block per conversation, then a summary. Copy Michael's words exactly, emoji included. Give each conversation's start time in Israel time.

    ### N1 · אסף · noise from the building · 18:30 Israel time
    1. Tenant: יש לי בעיה יש כאן רעש בבניין מה ניתן לעשות?
       Michael: …
       PASS
    2. Tenant: …
       Michael: …
       FAIL N1: "הקריאה הדחופה שלך פתוחה, מספר …".

    ## Summary
    - Messages sent: N · replies: N
    - Any ticket number before the yes, or any "urgent ticket" line: yes / no (quote it)
    - The ticket after the yes (N1.3): its number, building and apartment
    - A service call for the neighbour's music: yes / no
    - Serious fails: …
    - Other fails: …
    - Notes: …
    - No reply or errors: …
