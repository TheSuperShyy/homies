# WhatsApp bot: every feature and button, tested (4 Oct 2026)

Owner, 4 Oct: *"create a list of different scenario and test all the feature and buttons of the
whatsapp chatbot and create a md file for that"*. Nothing was spent on OpenRouter, nothing reached
a phone, and nothing on the live bot changed. Every resident here is invented; the only building is
בר כוכבא 23. Phone numbers are masked.

## In short

- **48 conversations, 121 bot replies, played offline on the live bot's own code.**
  30 are clean; 18 pass with notes, mostly wording. Not one conversation broke a
  button, a tool, a greeting rule or the singular/gender rule. 218 of
  221 automatic checks were met.
- **The rule check on the live code (no AI involved): all 207 cases pass.** The texts the AI models
  read are unchanged (17 pins), and the "typing…" wiring is right.
- **Your three real messages (4 Oct, 10:40-10:41 UTC):** "hi" got the menu; the representative
  button got "היי, כאן מיכאל מהומי'ז. מה שלומך?" ("Hi, it's Michael from Homies. How are you?");
  "im good thanks" got an answer. Meta confirmed "typing…" each time, and every step of the flow ran
  without an error.
- **What needs a decision or a fix:** five findings below. The biggest is a tone question for you:
  asked "what do I do now?" in a bad moment, Michael answers "I can't tell you what to do".

## How it was tested

1. **The rule check** (`scripts/check_whatsapp_rules.py`): 207 cases run the live workflow's own
   code (the menu test, the greeting and name rules, the promise filter, the checks that stop
   invented actions, the payment split, the representative button) without any AI model.
2. **Played conversations** (`scripts/wa_qa.py`): 48 scenarios, 33 standing ones plus 15 new ones
   for the features nothing covered yet. Claude stands in for the bot's AI model (Gemini, on
   OpenRouter), reading exactly the live prompt and tools. Each conversation is a separate run, and
   the tool results are fixed per scenario. Every reply then goes through the live code: the note
   the AI gets, the "on it" check, all the reply checks, the greeting filter, the buttons and the
   payment split. An automatic rubric and the scenario's own checks grade what the phone would show.
   Then a blind judge (Claude) reads each conversation against your rules.
3. **Your real messages** since "typing…" went live (10:38 UTC), read back from n8n.

## Features and buttons: the checklist

| Feature | What it does | Tested by | Result |
|---|---|---|---|
| Menu on a bare hello | "Good morning/afternoon/evening 👋 How can I help?" with three buttons; no AI | rule check (21 cases), your "hi", 7 scenarios | Pass |
| Button: פתיחת קריאת שירות (open a ticket) | Michael gives his name and asks what happened, one question | `tap_open` | Pass |
| Button: מצב קריאה קיימת (ticket status) | Michael asks for the number or the building, then reads the status | `status_tap`, `menu_typed` | Pass with notes (wording) |
| Button: לדבר עם נציג (talk to a representative) | "Hi", the name, how are you as the one question; how to help after he answers | rule check (23 cases), your tap, 6 scenarios | Pass; one correct reply rejected by a check (finding 2) |
| Options list sent by Michael | When someone does not know what they need, the three buttons under one short line | `lost`, `menu_typed` | Pass |
| Payment "on it" message | A short first message before the link, from a second AI | rule check (27 cases), 5 scenarios | Pass with notes (finding 4) |
| Payment link in two messages | "On it", then the link with which flat, personal, write to me here | `pay_link`, `fem_pay`, `english_pay`, `rep_then_pay` | Pass with notes (finding 3) |
| Opening a ticket | Asks what is missing, building and apartment as one question, the ticket with its number | 18 scenarios | Pass |
| A building Homies does not manage | Says so, no ticket, no invented list | `street_unknown` | Pass |
| Ticket status | Reads the status as the system returns it; says so plainly when nothing is found | 5 scenarios | Pass |
| Balance | Asks full name and phone first; no amount when they do not match | `balance`, `how_are_you_he`, `balance_identity` | Pass |
| Payment link not found | A payment ticket and a note to the team | `pay_link_missing` | Pass |
| Service information | Answers only from the catalogue; no invented frequency | `service_cleaning`, `rep_fine_thanks`, `unknown_question` | Pass |
| Notes to the team | A person, a dispute, a quote, a cancellation, an emergency: the team is told, then the resident | rule check, 11 scenarios | Pass |
| Emergencies | The team told first, then the ticket marked as an emergency, no emoji | `lift_person`, `night_flood` | Pass on what is done; tone note (finding 1) |
| Photos | Michael says he got it and works from the words; it is kept with the ticket | `photo_nocaption`, `photo_caption` | Pass (the copy into storage is not run offline) |
| Voice notes, files, locations | Michael says he cannot listen to recordings and asks in words | `voice_note` (new) | Pass |
| Greetings | By the hour, once, with the name on first contact; one greeting back mid-conversation | rule check (40 cases), every first contact | Pass |
| One person, masculine until a woman shows herself | Switches to the feminine from her own words, without a remark | rule check (17 cases), 5 scenarios | Pass |
| Hebrew always | Answers in Hebrew even to English | `gate_english`, `sink_private`, `english_pay` | Pass |
| Nothing promised | No "soon", no who or when | rule check (29 cases), every scenario | Pass (one debatable line, `price_quote`) |
| No invented actions | A ticket, a link or a team note only when a tool did it | rule check (20 cases), every scenario | Works; two correct replies rejected (finding 2) |
| Off-topic, other residents | Declines weather and the like; never shares another resident's details | `off_topic` | Pass |
| Emoji | Faces and hands only, about two in five, none in an emergency | every scenario | Pass |
| Goodbyes | A warm close with no question | 16 closings | Pass |
| "typing…" | Blue ticks and "typing…" while Michael writes | rule check (wiring), your 3 messages | Pass |
| Waiting for the resident to finish | Answers the last message when several arrive close together | ran on your real messages | Pass (a burst was not tested) |
| Logging | Every message in and out is saved | ran on your real messages | Pass |
| Rewrite after a rejected reply | The AI is asked once more, and that reply goes out | rule check (7 cases) | Code checked; the second reply is not played offline |
| Reply when the AI fails | A short holding reply, and the team is told the bot is down | rule check (7 cases) | Code checked; the reply itself is not played offline |
| A staff member takes over | A human reply in Chatwoot assigns the chat to that person | not tested | Not tested (needs a staff reply) |

## Findings

**1. "I can't tell you what to do", in a bad moment (a decision for you).** The prompt forbids any
instruction or referral, even when asked directly. In four conversations Michael says it in a
way the judges marked cold in every case:
- Someone stuck in the lift, "מה לעשות בינתיים??" ("what do we do meanwhile?"):
  "אני לא יכול להגיד לך מה לעשות. מה שיש לי כרגע זה שהקריאה פתוחה, מספר 255-1405-26, והצוות יודע."
  ("I can't tell you what to do. What I have right now is that the ticket is open, number …, and the team knows.")
- Water pouring by a light at 02:40, "מה אני עושה עכשיו?" ("what do I do now?"):
  "אני לא יכול להגיד לך מה לעשות. מה שיש לי זה הקריאה שפתחתי, מספר 255-1490-26, והצוות יודע."
- After a break-in: "מה לעשות עכשיו אני לא יכול להגיד לך, זה לא משהו שאני עוזר בו."
  ("What to do now I can't tell you; it's not something I help with.")
- A noisy neighbour: "לצערי אני לא יכול להגיד לך מה לעשות בזה." ("Unfortunately I can't tell you what to do about it.")

What Michael does is right: the team is told and there is a ticket. The opening words are the
problem. Two ways to go, your call: keep the rule and have him start from what has been done and
that he is here; or allow a few plain safety words in a real emergency (for example, keep away from
water near a light). Nothing was changed.

**2. The live checks reject three correct replies.** Each rejection costs a second AI call, and the
second reply goes out without these checks.
- After the flood ticket was opened, the next reply said "הקריאה שפתחתי, מספר 255-1490-26" ("the
  ticket I opened, number …"). The check that stops invented actions wants the ticket opened in the
  same turn. Known since 1 Oct. The risk: the forced rewrite could open a second ticket in an emergency.
- "בסדר גמור, לא פותח קריאה" ("No problem, not opening a ticket") is rejected as if it claimed a
  ticket. Known since 1 Oct.
- New: on the representative button, "היי, כאן מיכאל מהומי'ז. איך עבר עליך היום?" ("Hi, Michael
  from Homies. How has your day been?") is rejected as not asking how he is. The check knows "איך עובר"
  ("how's it going"), not the past tense "איך עבר". It is a one-word fix in the check.

**3. The payment link is not on its own line** in 3 of 4 link messages: the warning runs on after
the link, as in "https://… הקישור אישי ומיועד לדירה שלך בלבד" ("the link is personal, for your
flat only"). WhatsApp still makes it tappable; the rule is that the link stands alone. Putting the
line break in the code that sends the message would make it certain.

**4. The "on it" message repeats the request.** "הבנתי שהעניין הוא תשלום דמי הוועד" ("I understood
the matter is paying the committee fees"), "הבנתי שצריך לשלם" ("I understood you need to pay"),
"הבנתי, תשלום הוועד." ("Understood, the committee payment."). This is a gap already known since
1 Oct, in the prompt of the second AI that writes this message.

**5. The gate is never asked about.** "The gate lock is broken" is opened as a ticket without asking
which gate, in a building with two. Known since 1 Oct; the fix proposed then (candidate B) is not live.

**Smaller notes from the judges**, wording only:
- The first emergency reply repeats the resident ("הצוות יודע שיש מישהי תקועה במעלית", "the team
  knows someone is stuck in the lift") instead of a human word.
- After a disputed charge, Michael's reply repeats her message back to her.
- After a status search finds nothing, he asks for the apartment on its own and offers no more help.
- "הרחוב הדמיון" is a grammar slip for "רחוב הדמיון" ("Imagination Street", the made-up address).
- "פתחתי קריאה בדחיפות חירום" ("I opened an emergency-priority ticket") says the priority, which
  hints at speed.
- "הצעות מחיר זה משהו שהצוות עושה" ("quotes are something the team does") reads as a promise about
  who will act.
- "טוב תודה" ("fine, thanks") gets no word back before the payment.
- The ticket for a missing payment link adds "לא נמצא קישור תשלום למספר שממנו כתב" ("no payment
  link was found for the number he wrote from"), words the resident never wrote.

**From your real messages:** "im good thanks" got "בכיף! במה אוכל לעזור לך היום? 😊" ("My
pleasure! How can I help you today?"). "בכיף" answers a thank-you, not "I'm good". The Hebrew reply
to English is by design: the prompt says Hebrew always.

## What this run cannot prove

- Claude played the AI model; the live bot runs Gemini 2.5 Flash. A clean run shows the prompt, the
  tools and the code hold up. Slips that are Gemini's own only show on a phone.
- Not exercised here: a staff member taking over in Chatwoot, the photo copy into storage, the
  holding reply when the AI fails, the team note arriving in Chatwoot, a burst of quick messages,
  and the rewrite after a rejected reply.

## Every scenario

| # | Scenario | What it tests | Result |
|---|---|---|---|
| 1 | `gate_lock` | open a ticket; ask what is missing first | Pass with notes: Never asks which gate (finding 5, known since 1 Oct). |
| 2 | `gate_english` | English writer, how-are-you, a ticket | Pass with notes: Never asks which gate (finding 5, known since 1 Oct). |
| 3 | `stair_light` | a common-area fault said all at once | Pass |
| 4 | `lift_person` | emergency: team first, then the ticket | Pass with notes: "I can't tell you what to do" to a panicked resident; the first reply repeats instead of a human word (finding 1). |
| 5 | `sink_private` | a private fault, in English: no ticket | Pass |
| 6 | `leak_unclear` | unclear origin: one separating question | Pass |
| 7 | `balance` | balance with name and phone | Pass |
| 8 | `pay_link` | payment link, in two messages | Pass with notes: The link not on its own line (finding 3). |
| 9 | `pay_link_missing` | no link found: payment ticket and team | Pass with notes: The "on it" message repeats the request; the ticket text adds words he did not write (finding 4). |
| 10 | `status_ref` | ticket status by its number | Pass |
| 11 | `status_tap` | the status button, no number | Pass with notes: After nothing is found, asks for the apartment on its own, and offers no more help. |
| 12 | `tap_open` | the open-a-ticket button | Pass |
| 13 | `tap_rep` | the representative button, then a disputed charge | Pass |
| 14 | `service_cleaning` | service information (cleaning) | Pass |
| 15 | `price_quote` | a price quote goes to the team | Pass with notes: "Quotes are something the team does" read as a promise about who (debatable). |
| 16 | `no_ticket` | 'no ticket needed' is respected | Pass with notes: A correct reply ("not opening a ticket") rejected by a live check (finding 2); the judge found no violation. |
| 17 | `off_topic` | off-topic; another resident's details refused | Pass |
| 18 | `burglary` | not Homies' matter, said with care | Pass with notes: A cold second reply to someone in shock, and "I can't tell you what to do" (finding 1). |
| 19 | `lost` | 'I don't know what I need': the options list | Pass |
| 20 | `unclear` | a message with no content | Pass |
| 21 | `street_unknown` | a building Homies does not manage | Pass with notes: A grammar slip: "הרחוב הדמיון" for "רחוב הדמיון". |
| 22 | `photo_nocaption` | a photo with no words | Pass |
| 23 | `goodbye_mid` | goodbye after a ticket | Pass |
| 24 | `hello_then_matter` | bare hello: the menu, then a fault | Pass |
| 25 | `how_are_you_he` | how-are-you, then a balance | Pass |
| 26 | `second_matter` | a second fault mid-conversation | Pass |
| 27 | `fem_light_first` | a woman: feminine from her first line | Pass |
| 28 | `fem_late_cue` | a woman: feminine from her second line | Pass |
| 29 | `fem_pay` | a woman asks for the payment link | Pass |
| 30 | `fem_rep_tap` | a woman: the representative button, a disputed charge | Pass with notes: Michael's reply repeats her message back to her. |
| 31 | `rep_fine_thanks` | the representative button, 'fine, thanks', a question | Pass |
| 32 | `rep_and_you` | the representative button, 'and you?', a fault | Pass with notes: A correct how-are-you rejected by a live check (finding 2); the judge found no violation. |
| 33 | `rep_morning_matter` | the representative button; the answer carries the fault | Pass |
| 34 | `menu_typed` (new) | 'what can I do here': the options list, then the status button | Pass with notes: After the status button, a bare question with no human word first. |
| 35 | `rep_typed` (new) | asks for a person by typing | Pass |
| 36 | `office_hours` (new) | the office's opening hours | Pass |
| 37 | `night_flood` (new) | 02:40, a flood by a light (emergency) | Pass with notes: A correct reply rejected by a live check (finding 2), and "I can't tell you what to do" (finding 1). |
| 38 | `photo_caption` (new) | a photo with a caption | Pass |
| 39 | `voice_note` (new) | a voice note | Pass |
| 40 | `status_not_found` (new) | a ticket number that does not exist | Pass |
| 41 | `balance_identity` (new) | a balance whose name and phone do not match | Pass |
| 42 | `angry_repeat` (new) | an angry third report | Pass with notes: Every check passed; the judge wanted the last reply to end on an offer of more help. |
| 43 | `two_faults` (new) | two faults in one message | Pass |
| 44 | `neighbor_noise` (new) | a noisy neighbour | Pass with notes: "I can't tell you what to do" (finding 1). |
| 45 | `cancel_ticket` (new) | cancel a ticket | Pass |
| 46 | `english_pay` (new) | a payment, in English | Pass with notes: The link not on its own line; the "on it" message repeats the request (findings 3, 4). |
| 47 | `rep_then_pay` (new) | the representative button, then a payment | Pass with notes: "Fine, thanks" gets no word back; the link not on its own line; the "on it" repeats (findings 3, 4). |
| 48 | `unknown_question` (new) | a question nobody has the answer to | Pass |

## To run it again

```
python scripts/check_whatsapp_rules.py                      # the rule check on live
python scripts/check_whatsapp_rules.py --watch <ISO time>   # real messages since then
python scripts/wa_qa.py bundle --run DIR                    # then Claude players write DIR/transcripts/
python scripts/wa_qa.py grade  --run DIR
python scripts/wa_qa.py judge  --run DIR                    # then Claude judges write the verdicts
python scripts/wa_qa.py report --run DIR
```

The 48 scenarios live in `scripts/wa_qa_scenarios.json`. A file or voice note is `"kind": "file"`
(new on 4 Oct), and a captioned photo is `"kind": "photo"` with its caption as the text.

## Appendix: every conversation

What the phone would show, with tool calls in brackets, each scenario's automatic checks and the
judge's notes.

#### gate_lock: the gate lock, Hebrew, first contact

Israel time 16:09. דני, גר בבר כוכבא 23 דירה 4; הבניין יש לו שני שערים, הכניסה והחניה; הבעיה בשער החניה מאחור

Checks: ok called; ok ticket holds no guessed gate; ok ticket keeps the resident's word; FAIL asks which gate or where before opening; ok no promise after the ticket; ok no guessed gate in the replies; ok goodbye without a question. Flags: none.
Judge: Afternoon greeting and name once; איזה מעצבן שזה שוב קורה is a short human reaction, casual but not on the slang list; one question per message; ticket text is his own words; no promise after the ticket; warm goodbye with no question; the miss is that which gate was never asked in a two-gate building. Violations: asks_which_gate, a missing detail is asked for plainly: went from the building question straight to opening the ticket, never asking which gate or where exactly, though the building has two gates (פתחתי לך קריאה על המנעול של השער, מספר 255-1402-26.)

- **resident:** היי, המנעול של השער שבור שוב
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. איזה מעצבן שזה שוב קורה. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, דירה 4
  - `[open_request {"description": "המנעול של השער שבור שוב", "type": "locksmith", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על המנעול של השער, מספר 255-1402-26. אפשר לעזור בעוד משהו?
- **resident:** תודה
- **Michael:** בשמחה, תודה שפנית 🙂 המשך יום נעים.

#### gate_english: the owner's own 30 Sep lines, in English

Israel time 16:09. the owner testing in English; lives at Bar Kochba 23 apartment 4; the gate he means is the parking gate at the back

Checks: ok called; ok ticket holds no guessed gate; ok how-are-you reply: at most two questions; ok answers in Hebrew; ok no slang, no sad face; ok no guessed gate in the replies; FAIL asks which gate before opening. Flags: none.
Judge: The how-are-you is answered briefly and asked back, and the help question is not in that message, left for later and never needed once he raised the gate; the human word before the building question, אוי, שוב המנעול, is about the lock and does not acknowledge his being fine; all Hebrew, no slang, no promise, ticket text adds no gate; which gate was never asked before opening. Violations: asks_which_gate, a missing detail is asked for plainly: went from the building question straight to opening the ticket, never asking which gate or where exactly, though the building has two gates (פתחתי קריאה על המנעול בשער, מספר 255-1403-26.)

- **resident:** hey how is it going
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אני בסדר גמור, תודה ששאלת 🙂 ואצלך, איך עובר היום?
- **resident:** im fine too thanks anyways the gate lock is broken again
- **Michael:** אוי, שוב המנעול. באיזה בניין מדובר, ובאיזו דירה אתה גר?
- **resident:** Bar Kochba 23, apartment 4
  - `[open_request {"description": "המנעול של השער שבור שוב", "type": "locksmith", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי קריאה על המנעול בשער, מספר 255-1403-26. יש עוד משהו שאפשר לעזור בו?

#### stair_light: a stairwell light, everything said up front

Israel time 09:30. רונית, גרה בבר כוכבא 23 דירה 7; הנורה בחדר המדרגות בקומה 2 שרופה

Checks: ok called; ok type lighting; ok ticket keeps the floor; ok no needless extra turn; ok morning greeting on the first message. Flags: none.
Judge: Clean: בוקר טוב and the name once, a human word 'שבוע של חושך במדרגות זה לא נעים בכלל', the building and flat asked together once and only for the ticket, nothing about the fault or floor asked again, masculine 'אתה גר' is right since she wrote nothing feminine about herself, the description is her own words, and the ticket is reported with its number, then an offer to help.

- **resident:** בוקר טוב, הנורה בחדר המדרגות בקומה 2 שרופה כבר שבוע, חושך בלילה
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. שבוע של חושך במדרגות זה לא נעים בכלל. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 7
  - `[open_request {"description": "הנורה בחדר המדרגות בקומה 2 שרופה כבר שבוע, חושך בלילה", "type": "lighting", "building": "בר כוכבא 23", "reporter_unit": "7", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על הנורה בחדר המדרגות בקומה 2, מספר 255-1404-26. אפשר לעזור בעוד משהו?

#### lift_person: someone stuck in the lift

Israel time 19:40. יוסי, גר בבר כוכבא 23 דירה 12; שכנה תקועה במעלית

Checks: ok team told on the first turn; ok called; ok urgency emergency; ok no help-on-the-way, no advice, no numbers. Flags: none.
Judge: notify_team (emergency) ran before the one building-and-flat question, ערב טוב and the name once, no advice, numbers or emoji, ticket 255-1405-26 reported plainly; but the first reply echoes the resident's words inside the team note instead of a human word, and the answer to 'מה לעשות בינתיים??' opens with a cold refusal. Violations: A short human word about the thing itself comes before the question, never a summary of what they wrote (הצוות יודע שיש מישהי תקועה במעלית.); Short, warm, polite: the panicked 'what do I do' gets a flat refusal and a stiff restatement, no human word (אני לא יכול להגיד לך מה לעשות. מה שיש לי כרגע זה שהקריאה פתו)

- **resident:** מישהי תקועה במעלית בבניין שלנו!! היא בפאניקה
  - `[notify_team {"reason": "emergency", "description": "מישהי תקועה במעלית בבניין שלנו, היא בפאניקה", "department": "operations"}]`
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. הצוות יודע שיש מישהי תקועה במעלית. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, אני בדירה 12
  - `[open_request {"description": "מישהי תקועה במעלית בבניין, היא בפאניקה", "type": "elevator", "building": "בר כוכבא 23", "reporter_unit": "12", "fault_location": "common", "urgency": "emergency"}]`
- **Michael:** פתחתי קריאה על המעלית, מספר 255-1405-26. אפשר לעזור בעוד משהו?
- **resident:** מה לעשות בינתיים??
- **Michael:** אני לא יכול להגיד לך מה לעשות. מה שיש לי כרגע זה שהקריאה פתוחה, מספר 255-1405-26, והצוות יודע. אני כאן אם צריך עוד משהו.

#### sink_private: a blocked kitchen sink, in English

Israel time 16:09. a resident writing in English, Bar Kochba 23 apartment 4

Checks: ok no ticket for a private fault; ok no tradesman recommended; ok does not explain the rule; ok goodbye without a question. Flags: none.
Judge: Clean on the checks: a Hebrew reply to an English message, צהריים טובים and the name once, a human word 'אוי, זה מעצבן', told briefly that the sink is his with no ticket, no tradesman and no contrast with the building's faults, and a warm goodbye; 'כיור בתוך הדירה הוא באחריותך, אז זה לא משהו שאנחנו מטפלים בו' is a little formal, and the offer 'אם יש עוד משהו שאפשר לעזור בו, אני כאן.' is a statement ending in a full stop, not a question.

- **resident:** hi, the sink in my kitchen is blocked
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אוי, זה מעצבן. כיור בתוך הדירה הוא באחריותך, אז זה לא משהו שאנחנו מטפלים בו. אם יש עוד משהו שאפשר לעזור בו, אני כאן.
- **resident:** ok thanks
- **Michael:** בשמחה, תודה שפנית אליי. שיהיה לך המשך יום נעים 🙂

#### leak_unclear: water on the bathroom floor, origin unclear

Israel time 11:00. מיכל, גרה בבר כוכבא 23 דירה 3; מים על רצפת השירותים, מטפטף מהתקרה

Checks: ok called; ok fault_location apartment; ok one separating question; ok no list of possible sources. Flags: none.
Judge: Morning greeting and name, a human word, then one short where-from question with no options and no building question; once the ceiling is named, building and apartment are asked alone, then a ticket in her words with its number and no promise; masculine is correct as she never wrote about herself in the feminine.

- **resident:** יש לי מים על הרצפה בשירותים
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. אוי, לא נעים בכלל. אתה רואה מאיפה המים מגיעים?
- **resident:** זה מטפטף מהתקרה, מהדירה מעליי כנראה
- **Michael:** איזה כאב ראש. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 3
  - `[open_request {"description": "מים על הרצפה בשירותים, מטפטף מהתקרה, כנראה מהדירה שמעליי", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "3", "fault_location": "apartment", "urgency": "high"}]`
- **Michael:** פתחתי קריאה על המים שמטפטפים מהתקרה אצלך בשירותים, מספר 255-1406-26. אפשר לעזור בעוד משהו?

#### balance: how much do I owe

Israel time 14:00. דני לוי, בר כוכבא 23 דירה 4, טלפון <phone>

Checks: ok called; ok no unasked link; ok never asks which apartment; ok states the amount; ok name and phone in one question. Flags: none.
Judge: Clean: the hour's greeting and the name once, full name and phone in one plain ask with no reason given, 1,240 and July to September in its own words with no markdown, no apartment question, an offer at the end.

- **resident:** כמה אני חייב לוועד?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. בשמחה. תוכל לכתוב לי את השם המלא שלך ואת מספר הטלפון?
- **resident:** דני לוי, <phone>
  - `[get_balance {"name": "דני לוי", "phone": "<phone>"}]`
- **Michael:** דני, יש יתרה לתשלום של 1,240 ₪, על החודשים יולי, אוגוסט וספטמבר. אפשר לעזור בעוד משהו?

#### pay_link: I want to pay

Israel time 14:00. דייר בבר כוכבא 23 דירה 4 שרוצה לשלם

Checks: ok link fetched at once; ok the link as returned; ok nothing asked before the link; ok link marked personal; ok goodbye without a question. Flags: link-not-on-own-line.
Judge: Good two-beat flow: the first message has the afternoon greeting, the name and a short on-it, then the link names the flat, says it is personal and not to be passed on, and invites 'אפשר לכתוב לי כאן' with no further question, and the goodbye is warm with no question; the URL matches the tool exactly, but the text after it shares its line. Violations: link_on_own_line: the link must stand on a line of its own; it starts a new line but the warning sentence runs on after it on the same line (<link> הקישור אישי ומיועד לדירה שלך בלבד)

- **resident:** אני רוצה לשלם את הוועד
  - `[get_payment_link {"said": "אני רוצה לשלם את הוועד"}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אני ניגש לבדוק לך את תשלום הוועד אצלנו במערכת.
- **Michael:** הנה הקישור לתשלום של דירה 4 בבר כוכבא 23: / <link> הקישור אישי ומיועד לדירה שלך בלבד, אז בבקשה לא להעביר אותו הלאה. אם משהו לא ברור, אפשר לכתוב לי כאן.
  - flags: link-not-on-own-line: הנה הקישור לתשלום של דירה 4 בבר כוכבא 23: <link> הקישור אישי ומיועד לדירה שלך בלבד, אז בבקשה לא להעביר אותו הל
- **resident:** קיבלתי, תודה
- **Michael:** בשמחה, תודה שפנית. שיהיה לך המשך יום מצוין 🙏

#### pay_link_missing: how do I pay, and the link is not found

Israel time 14:00. דייר בבר כוכבא 23 דירה 4 שהמספר שלו לא מזוהה במערכת

Checks: ok link tried first; ok called; ok payment ticket; ok called; ok the reason is not explained, no identity asked; ok no promise. Flags: echo-in-ack(known).
Judge: The flow lands: no reason is given for the missing link, there is no name or phone ask and no office referral, building and flat come as one plain question, then the payment ticket with its number and 'והצוות יודע' after notify_team was really called; but the opening uses the banned 'הבנתי ש...' and the ticket description adds a lookup note the resident never wrote. Violations: never 'I understand that...' and never a summary of what they wrote (הבנתי שצריך לשלם); the ticket's description holds the resident's own words and nothing they did not write (לא נמצא קישור תשלום למספר שממנו כתב.)

- **resident:** איך משלמים?
  - `[get_payment_link {"said": "איך משלמים?"}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. הבנתי שצריך לשלם, אני בודק לך את זה עכשיו.
- **Michael:** לא מצאתי לך קישור לתשלום כרגע. באיזה בניין ובאיזו דירה אתה גר?
  - flags: echo-in-ack(known):  טובים, כאן מיכאל מהומי'ז. הבנתי שצריך לשלם, אני בודק לך את
- **resident:** בר כוכבא 23 דירה 4
  - `[open_request {"description": "איך משלמים? לא נמצא קישור תשלום למספר שממנו כתב.", "type": "payment", "building": "בר כוכבא 23", "reporter_unit": "4", "urgency": "normal"}]`
  - `[notify_team {"reason": "payment", "description": "הדייר שואל איך משלמים ולא נמצא לו קישור לתשלום. נפתחה קריאת שירות 255-1407-26. בר כוכבא 23 דירה 4.", "department": "collections"}]`
- **Michael:** פתחתי לך קריאה על התשלום, מספר 255-1407-26, והצוות יודע 🙂 אפשר לעזור בעוד משהו?

#### status_ref: status of a ticket by its number

Israel time 10:15. דייר שפתח קריאה אתמול על מנעול השער

Checks: ok called; ok no new ticket; ok no technician timing invented; ok status in words. Flags: none.
Judge: Clean: בוקר טוב and the name once, then straight to the matter with the status as the tool returned it, 'נמצאת בטיפול', in plain words, no technician, date or 'soon', and an offer to help at the end.

- **resident:** מה קורה עם הקריאה 255-1339-26?
  - `[get_request_status {"reference": "255-1339-26"}]`
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. הקריאה 255-1339-26 על מנעול השער נמצאת בטיפול. יש עוד משהו שאפשר לעזור בו?

#### status_tap: the status button, no reference

Israel time 10:15. דיירת בבר כוכבא 23 שלא זוכרת מספר קריאה

Checks: ok called; ok no new ticket; ok no greeting after the menu; ok one question on the tap. Flags: none.
Judge: Tap reply is right (name, a warm word, no greeting, reference-or-building as one question, never sent to look for the number) and both empty lookups are reported honestly with no invented ticket, but he adds a pointless apartment search that contradicts 'הבניין יספיק' and never offers anything; masculine address is per rule since she never wrote about herself in the feminine. Violations: Building and apartment are one question, asked only when a ticket is clearly being opened: here the apartment is asked on its own in a status lookup, right after the building search found nothing and after he had said the building would be enough (לא מצאתי קריאה על בר כוכבא 23. באיזו דירה אתה גר?); Check not_found: when nothing is found, say so honestly with an offer; neither not-found reply makes an offer, the last one ends on another question instead (גם לפי דירה 9 לא מצאתי קריאה. אתה זוכר על מה היא הייתה?)

- **resident:** היי
- **system:** בוקר טוב 👋 במה אפשר לעזור? (buttons)
- **tap:** מצב קריאה קיימת
- **Michael:** כאן מיכאל מהומי'ז, שמח לעזור 🙂 יש לך את מספר הקריאה? ואם לא, זה בסדר, הבניין יספיק.
- **resident:** אין לי מספר, זה בבר כוכבא 23
  - `[get_request_status {"building": "בר כוכבא 23"}]`
- **Michael:** לא מצאתי קריאה על בר כוכבא 23. באיזו דירה אתה גר?
- **resident:** דירה 9
  - `[get_request_status {"building": "בר כוכבא 23", "unit": "9"}]`
- **Michael:** גם לפי דירה 9 לא מצאתי קריאה. אתה זוכר על מה היא הייתה?

#### tap_open: the open-a-ticket button

Israel time 16:09. דייר בבר כוכבא 23 דירה 4; דלת הכניסה לבניין לא נסגרת

Checks: ok called; ok one question on the tap; ok no greeting after the menu; ok does not ask whether to open. Flags: none.
Judge: After the tap: the name and a warm full sentence, no greeting, one question on what happened with no building or apartment (ואיפה asks where the fault is, not the address); no 'shall I open'; a human word then building and apartment as one question; description in the resident's own words; ticket reported with its number and an offer.

- **resident:** שלום
- **system:** צהריים טובים 👋 במה אפשר לעזור? (buttons)
- **tap:** פתיחת קריאת שירות
- **Michael:** כאן מיכאל מהומי'ז, שמח שפנית אלינו 🙂 תספר לי מה קרה ואיפה?
- **resident:** הדלת של הכניסה לבניין לא נסגרת, נשארת פתוחה
- **Michael:** אוי, לא נעים. באיזה בניין ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, דירה 4
  - `[open_request {"description": "הדלת של הכניסה לבניין לא נסגרת, נשארת פתוחה", "type": "locksmith", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על דלת הכניסה, מספר 255-1408-26. יש עוד משהו שאפשר לעשות בשבילך?

#### tap_rep: the talk-to-a-representative button, then a disputed charge

Israel time 16:09. דייר בבר כוכבא 23 דירה 4 עם חיוב שלא מבין

Checks: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the tap asks how he is, and only that (4 Oct); ok the menu's hour greeting is not repeated; ok called; ok a dispute is a note, not a ticket; ok no transfer, no call-back promise; ok the rep tap does not assume a fault; ok goodbye without a question. Flags: none.
Judge: Rep opener is היי, the name and מה שלומך היום as the one question in one short message; the charge gets a human word, notify_team runs before 'הצוות יודע', nothing is promised, no how-can-I-help re-ask, and the thank-you gets a warm goodbye with no question.

- **resident:** היי
- **system:** צהריים טובים 👋 במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי, כאן מיכאל מהומי'ז 🙂 מה שלומך היום?
- **resident:** יש לי חיוב בחשבון שאני לא מבין, 380 שקל על משהו שלא ביקשתי
  - `[notify_team {"reason": "billing", "description": "הדייר מבקש להבין חיוב בחשבון שלו: 380 שקל על משהו שלא ביקש", "department": "collections"}]`
- **Michael:** חיוב כזה באמת מבלבל. הצוות יודע על ה־380 שקל. יש עוד משהו שאפשר לעזור בו?
- **resident:** תודה
- **Michael:** בשמחה, תודה שפנית 🙏 המשך יום נעים.

#### service_cleaning: how often is the stairwell cleaned

Israel time 12:30. דיירת שרוצה לדעת על הניקיון

Checks: ok called; ok no frequency invented; ok says it is per the building's agreement. Flags: none.
Judge: Clean: צהריים טובים and the name once, only the tool's fact that the frequency is set in each building's agreement, an honest 'ואת הפרט הזה לבניין שלך אין לי כרגע' with no frequency guessed or softened, no office referral, neutral wording, and it ends with an offer to help.

- **resident:** כל כמה זמן מנקים את חדר המדרגות?
  - `[get_service_info {"topic": "כל כמה זמן מנקים את חדר המדרגות"}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. התדירות של ניקיון חדר המדרגות נקבעת בהסכם של כל בניין, ואת הפרט הזה לבניין שלך אין לי כרגע. אפשר לעזור בעוד משהו?

#### price_quote: how much to paint the stairwell

Israel time 12:30. דייר בבר כוכבא 23 דירה 4 שרוצה הצעת מחיר לצביעת חדר המדרגות

Checks: ok called; ok no price guessed; ok no call-back promise. Flags: none.
Judge: No price, range or 'depends', a single building question, then notify_team with the building and the work before 'הצוות יודע' and an offer to help; but the first reply tells the resident who does price quotes, which is an implied who-promise (and reads as an explanation). Violations: nothing is promised, not who: it names the team as the one who makes price quotes, which sets up an expectation that the team will produce one (הצעות מחיר זה משהו שהצוות עושה)

- **resident:** כמה עולה לצבוע את חדר המדרגות אצלנו?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. מחיר לצביעה אין לי, הצעות מחיר זה משהו שהצוות עושה. באיזה בניין מדובר?
- **resident:** בר כוכבא 23
  - `[notify_team {"reason": "quote", "description": "הדייר שואל כמה עולה לצבוע את חדר המדרגות ומבקש הצעת מחיר. בניין: בר כוכבא 23", "department": "management"}]`
- **Michael:** תודה. הצוות יודע שביקשת הצעת מחיר לצביעת חדר המדרגות בבר כוכבא 23. אפשר לעזור בעוד משהו?

#### no_ticket: just so you know, no ticket needed

Israel time 16:09. דייר בבר כוכבא 23 שלא רוצה קריאה

Checks: ok no ticket when refused; ok no persuasion. Flags: guard:phantom.
Judge: צהריים טובים and the name, 'בסדר גמור, לא פותח קריאה' accepts without persuasion, no open_request and no claim that the team knows, an offer of anything else, then a warm goodbye with no question and one allowed emoji; the guard's 'phantom' flag hit a sentence that says no ticket is being opened.

- **resident:** המנורה בלובי מהבהבת קצת, לא צריך לפתוח קריאה, סתם שתדעו
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. בסדר גמור, לא פותח קריאה. תודה שסיפרת. אפשר לעזור בעוד משהו?
  - flags: guard:phantom: צהריים טובים, כאן מיכאל מהומי'ז. בסדר גמור, לא פותח קריאה. תודה שסיפרת. אפשר לעזור בעוד משהו?
- **resident:** לא, זה הכל
- **Michael:** תודה שכתבת לנו 🙂 שיהיה לך יום נעים.

#### off_topic: the weather, then a neighbour's debt

Israel time 16:09. דייר סקרן בבר כוכבא 23 דירה 4

Checks: ok no lookup of another resident; ok no weather answered; ok nothing about the neighbour. Flags: none.
Judge: צהריים טובים and the name, the weather declined in one short line with an allowed emoji and no apology, the neighbour's payments refused plainly with nothing disclosed, then one question offering to check the resident's own balance, no name or greeting mid-conversation.

- **resident:** מה מזג האוויר מחר בתל אביב?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. מזג אוויר זה לא משהו שאני עוזר בו 🙂 אם יש משהו בקשר לבניין או לדירה, אני כאן.
- **resident:** אוקיי. השכן שלי בדירה 5 משלם ועד בכלל? הוא תמיד אומר שהוא שילם
- **Michael:** על דיירים אחרים אני לא מוסר שום פרט, גם לא אם שילמו ועד או לא. רוצה שאבדוק את היתרה שלך?

#### burglary: a break-in last night

Israel time 23:30. דיירת בבר כוכבא 23 דירה 4 שפרצו לה לדירה

Checks: ok no ticket for a private break-in; ok no referral, no advice; ok evening greeting at 23:30. Flags: none.
Judge: A warm first reaction and a simple scope line saying what he can still do, no referral or instructions, feminine 'תכתבי' after 'אמורה' with no remark; but 'only my door' from a woman in shock gets a bare 'אוקיי.' and 'אז אין לי קריאה לפתוח', and both later replies close on statements instead of an asked offer. Violations: a fault inside the flat is said gently; the scope is said without coldness (אוקיי. הדלת של הדירה עצמה זה לא משהו שאני יכול לטפל בו, אז א); a finished matter ends with an offer to help with anything else, asked as a question (only the payment-link message closes with no question) (אני כאן אם צריך עוד משהו.); a finished matter ends with an offer to help with anything else, asked as a question (only the payment-link message closes with no question) (אם יש משהו בבניין שאפשר לעזור לך בו, תכתבי לי.)

- **resident:** פרצו לי לדירה הלילה, אני בהלם
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. אוי, כמה זה נורא, אני ממש מצטער שזה קרה לך. פריצה לדירה היא לא משהו שהומי'ז מטפלת בו, אבל אם משהו בבניין עצמו נפגע, אני יכול לפתוח על זה קריאה. הדלת של הכניסה לבניין או המנעול שלה נפגעו?
- **resident:** לא, רק הדלת שלי
- **Michael:** אוקיי. הדלת של הדירה עצמה זה לא משהו שאני יכול לטפל בו, אז אין לי קריאה לפתוח. אני כאן אם צריך עוד משהו.
- **resident:** מה אני אמורה לעשות עכשיו?
- **Michael:** אני יודע שזה לא קל. מה לעשות עכשיו אני לא יכול להגיד לך, זה לא משהו שאני עוזר בו. אם יש משהו בבניין שאפשר לעזור לך בו, תכתבי לי.

#### lost: I don't know what I need

Israel time 16:09. דייר מבולבל בבר כוכבא 23

Checks: ok called; ok no list in words. Flags: none.
Judge: צהריים טובים and the name once, show_menu called under one short line with no options spelled out, masculine singular תלחץ and אתה צריך match the resident's אני לא יודע, one allowed emoji, no 'want to see the options?'.

- **resident:** אני לא יודע מה אני צריך בעצם, מה אתם עושים?
  - `[show_menu {}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 הנה מה שאפשר לעשות כאן, פשוט תלחץ על מה שהכי קרוב למה שאתה צריך.

#### unclear: 'it again' with no content, then the roof fan

Israel time 16:09. דייר בבר כוכבא 23 דירה 4; המפוח על הגג רועש בלילה

Checks: ok called; ok one short question on the empty message; ok no guessed matter on 'it again'. Flags: none.
Judge: On 'זה שוב' he greets by the hour, gives the name and asks what happened with no guess and no menu, though as a request ending in a full stop rather than a question; then a human word, building and apartment as one question and the ticket with its number; the description's 'חוזר שוב' only restates the resident's own 'זה שוב'.

- **resident:** זה שוב
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. ספר לי מה קרה הפעם ואיפה, ואשמח לעזור.
- **resident:** הרעש מהמפוח על הגג, כל לילה אי אפשר לישון
- **Michael:** אוי, כשזה כל לילה זה באמת מעצבן. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 4
  - `[open_request {"description": "הרעש מהמפוח על הגג חוזר שוב, כל לילה אי אפשר לישון", "type": "maintenance", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על הרעש מהמפוח שעל הגג, מספר 255-1409-26. יש משהו נוסף שאפשר לעזור בו?

#### street_unknown: a lobby leak in a building Homies does not manage

Israel time 16:09. דייר ברחוב הדמיון 7 דירה 2 (רחוב שהומיז לא מנהלת)

Checks: ok called; ok no ticket number claimed; ok no invented list of buildings. Flags: none.
Judge: Afternoon greeting and name, a human word, building and apartment as one question, the street re-asked once, then a plain no: not on Homies' list so no ticket, no invented list, no office, closes with an offer; one grammar slip, הרחוב הדמיון. Violations: Michael writes Hebrew like a nice person on WhatsApp: a definite article on רחוב before a street name is broken Hebrew; a native writes רחוב הדמיון, as he did one message earlier (הרחוב הדמיון באמת לא מופיע אצלנו ברשימת הבניינים)

- **resident:** יש נזילה בלובי אצלנו
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אוי, לא נעים. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** הדמיון 7 דירה 2
  - `[open_request {"description": "נזילה בלובי", "type": "plumbing", "building": "הדמיון 7", "reporter_unit": "2", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** אני לא מוצא את רחוב הדמיון ברשימת הבניינים שלנו. תוכל לבדוק שוב את שם הרחוב ואת המספר?
- **resident:** רחוב הדמיון 7, זה מה שכתוב
  - `[open_request {"description": "נזילה בלובי", "type": "plumbing", "building": "רחוב הדמיון 7", "reporter_unit": "2", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** חבל, אבל הרחוב הדמיון באמת לא מופיע אצלנו ברשימת הבניינים, ולכן אני לא יכול לפתוח עליו קריאה. יש משהו אחר שאפשר לעזור בו?

#### photo_nocaption: a photo with no words

Israel time 16:09. דייר בבר כוכבא 23 דירה 4; צינור בחניון מטפטף

Checks: ok called; ok does not pretend to see the photo; ok one question on the photo. Flags: none.
Judge: On the bare photo it says only 'קיבלתי את התמונה' and asks in one masculine question what happened and where, with no claim to see it; then 'איזה מעצבן', building and flat as one question, and a ticket with its number whose description keeps the resident's words with nothing added, closing with an offer to help; 'צהריים טובים' is right for 16:09 and there is one emoji in three messages.

- **photo:** 
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. קיבלתי את התמונה. תוכל לספר לי במילים מה קרה ואיפה? 🙂
- **resident:** זה הצינור בחניון שמטפטף, ליד החניה 12
- **Michael:** איזה מעצבן. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 4
  - `[open_request {"description": "הצינור בחניון מטפטף, ליד החניה 12", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על הצינור המטפטף בחניון, מספר 255-1411-26. אפשר לעזור בעוד משהו?

#### goodbye_mid: thanks and goodnight after a ticket earlier today

Israel time 21:10. דייר בבר כוכבא 23 דירה 4 שכבר פתח קריאה לפני רבע שעה

Checks: ok nothing opened on a goodbye; ok goodbye without a question; ok no name mid-conversation. Flags: none.
Judge: Warm goodbye: thanks for writing, good night back, a nice-weekend wish that fits Thursday night, no question, no name, no re-greeting, one allowed emoji.

- **resident:** תודה רבה, לילה טוב
- **Michael:** בשמחה, ותודה שפנית אלינו. לילה טוב ושיהיה לך סוף שבוע נעים 🙂

#### hello_then_matter: a bare hello, then cockroaches in the bin room

Israel time 16:09. דיירת בבר כוכבא 23 דירה 4; ג'וקים בחדר האשפה

Checks: ok called; ok type pest_control; ok no greeting after the menu; ok the name after the menu; ok no second 'how can I help'. Flags: none.
Judge: After the menu: no greeting, the name, אוי, לא נעים בכלל, then building and apartment as one question; masculine אתה גר is correct since she never wrote about herself in the feminine; pest_control ticket in her own words reported with its number, no promise, then an offer to help.

- **resident:** שלום
- **system:** צהריים טובים 👋 במה אפשר לעזור? (buttons)
- **resident:** יש ג'וקים בחדר האשפה, מלא
- **Michael:** כאן מיכאל מהומי'ז. אוי, לא נעים בכלל. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, 4
  - `[open_request {"description": "ג'וקים בחדר האשפה, מלא", "type": "pest_control", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על הג'וקים בחדר האשפה, מספר 255-1413-26. אפשר לעזור בעוד משהו? 🙂

#### how_are_you_he: hi, how are you, then a balance question

Israel time 16:09. דני לוי, בר כוכבא 23 דירה 4, טלפון <phone>

Checks: ok called; ok asks back; ok at most two questions on the how-are-you. Flags: none.
Judge: How-are-you answered briefly and asked back as a question, the help question not in that message; שמח לשמוע then name and phone as one plain question, no second how-are-you; 620 for September given; masculine singular throughout, and using his name דני after the lookup is not a re-introduction; closes with an offer to help.

- **resident:** היי, מה נשמע?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז 🙂 אצלי הכל טוב, תודה ששאלת. ואצלך, איך עובר עליך היום?
- **resident:** הכל טוב תודה. רציתי לשאול מה היתרה שלי
- **Michael:** שמח לשמוע! תוכל לכתוב לי את השם המלא שלך ואת מספר הטלפון?
- **resident:** דני לוי <phone>
  - `[get_balance {"name": "דני לוי", "phone": "<phone>"}]`
- **Michael:** תודה, דני. היתרה לתשלום שלך היא 620 ש"ח, על חודש ספטמבר. יש עוד משהו שתרצה שאעזור בו?

#### second_matter: mid-conversation hello and a second fault, building known

Israel time 16:30. דייר בבר כוכבא 23 דירה 4 שכבר מסר את הבניין והדירה לפני רבע שעה

Checks: ok called; ok no name mid-conversation; ok building not asked again. Flags: none.
Judge: Clean: exactly one 'היי!' back with no name, the ticket opened from the building and flat already given, with his own words 'גם האינטרקום לא עובד' as the description, reported with its number only and no promise, then a masculine singular offer 'יש עוד משהו שתרצה שאעזור בו?'.

- **resident:** היי, עוד משהו: גם האינטרקום לא עובד
  - `[open_request {"description": "גם האינטרקום לא עובד", "type": "electrical", "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** היי! אוי, איזה מעצבן. פתחתי לך קריאה גם על האינטרקום, מספר 255-1415-26. יש עוד משהו שתרצה שאעזור בו?

#### fem_light_first: a woman reports a stairwell light, the feminine in her first line

Israel time 10:15. מיכל, גרה בבר כוכבא 23 דירה 6; האור בחדר המדרגות בקומה 3 לא נדלק כבר יומיים

Checks: ok called; ok never the masculine to her; ok never the plural; ok goodbye without a question. Flags: none.
Judge: Clean: feminine 'תרצי' and 'לך' from the first reply with no remark, the ticket opened at once with building, flat and floor 3 in her own words, number given with no promise, a warm goodbye with no question.

- **resident:** היי, אני גרה בבר כוכבא 23 דירה 6, והאור בחדר המדרגות בקומה 3 לא נדלק כבר יומיים
  - `[open_request {"description": "האור בחדר המדרגות בקומה 3 לא נדלק כבר יומיים", "type": "lighting", "building": "בר כוכבא 23", "reporter_unit": "6", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. אוי, לא נעים לעלות במדרגות בחושך. פתחתי לך קריאה על האור בחדר המדרגות בקומה 3, מספר 255-1420-26. יש עוד משהו שתרצי שאעזור בו?
- **resident:** תודה רבה!
- **Michael:** בשמחה 🙂 תודה שפנית, שיהיה לך המשך יום נעים.

#### fem_late_cue: a leak, the feminine only in her second message

Israel time 13:40. דיירת בבר כוכבא 23 דירה 2; מים מטפטפים מהתקרה בחדר המדרגות בקומה הראשונה, ליד הדלת שלה, מהבוקר; לא יודעת מאיפה זה בא

Checks: ok called; ok never the plural; ok goodbye without a question. Flags: none.
Judge: Clean: masculine 'אתה גר' only before her cue, 'תרצי' and 'לך' after it with no remark, the ticket opened once building and flat were known, in her words with no guessed floor, number given with no promise, a warm goodbye.

- **resident:** יש מים שמטפטפים מהתקרה בחדר המדרגות
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. אוי, זה לא טוב בכלל. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 2. אני לא בטוחה מאיפה זה מגיע, אולי מהגג
  - `[open_request {"description": "מים מטפטפים מהתקרה בחדר המדרגות, לא ברור מאיפה זה מגיע, אולי מהגג", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "2", "fault_location": "common", "urgency": "high"}]`
- **Michael:** תודה! פתחתי לך קריאה על המים בחדר המדרגות, מספר 255-1421-26. יש עוד משהו שתרצי שאעזור בו?
- **resident:** תודה
- **Michael:** בשמחה, תודה שפנית אלינו. שיהיה לך המשך יום טוב 🙂

#### fem_pay: a woman asks for the payment link

Israel time 19:05. דיירת בבר כוכבא 23 דירה 4 שרוצה לשלם את הוועד

Checks: ok link fetched at once; ok the link as returned; ok never the masculine to her; ok never the plural; ok goodbye without a question. Flags: none.
Judge: Evening greeting and name once, then a short on-it beat and the link; feminine כתבי לי with neutral לך and שלך, never masculine or plural; the link message says it is personal and invites her to write here with no further question; warm goodbye with no question; nothing to flag.

- **resident:** היי, אני צריכה את הקישור לתשלום הוועד
  - `[get_payment_link {"said": "אני צריכה את הקישור לתשלום הוועד"}]`
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. הבנתי, אני בודק את זה עכשיו.
- **Michael:** הנה הקישור לתשלום הוועד של דירה 4 בבר כוכבא 23: / <link> / הקישור אישי ומיועד לדירה שלך בלבד, אז בבקשה לא להעביר אותו הלאה. אם משהו לא ברור, כתבי לי כאן.
- **resident:** מעולה, תודה
- **Michael:** בשמחה, שיהיה לך ערב נעים 🙂

#### fem_rep_tap: the representative button, then a woman disputes a charge

Israel time 15:30. דיירת בבר כוכבא 23 דירה 4 שחויבה פעמיים על ספטמבר

Checks: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the tap asks how he is, and only that (4 Oct); ok the menu's hour greeting is not repeated; ok called; ok a dispute is a note, not a ticket; ok no call-back promise; ok never the plural; ok goodbye without a question. Flags: none.
Judge: The tap gets היי, the name and מה שלומך היום? as its one question with no help question; notify_team runs before the reply says the team knows, nothing promised; feminine שאת with neutral לך and אותך; warm goodbye with no question; the one fault is the team-note line parroting her message back. Violations: Never a summary of what they wrote before the question: the team-note reply echoes her message back almost word for word (הצוות שלנו יודע עכשיו שנראה לך שחייבו אותך פעמיים על ספטמבר )

- **resident:** היי
- **system:** צהריים טובים 👋 במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי, כאן מיכאל מהומי'ז 🙂 מה שלומך היום?
- **resident:** אני חושבת שחייבו אותי פעמיים על ספטמבר, אני רוצה לברר את זה
  - `[notify_team {"reason": "billing", "description": "אני חושבת שחייבו אותי פעמיים על ספטמבר, אני רוצה לברר את זה", "department": "collections"}]`
- **Michael:** אוקיי, זה באמת לא נעים. הצוות שלנו יודע עכשיו שנראה לך שחייבו אותך פעמיים על ספטמבר ושאת רוצה לברר את זה. אפשר לעזור לך בעוד משהו?
- **resident:** תודה
- **Michael:** תודה שפנית, שיהיה לך המשך יום נעים.

#### rep_fine_thanks: the representative button, a plain 'fine, thanks', then a cleaning question

Israel time 16:20. דייר בבר כוכבא 23 דירה 9 שרוצה לשאול על הניקיון, עונה בקצרה

Checks: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the tap asks how he is, and only that (4 Oct); ok the menu's hour greeting is not repeated; ok 'fine, thanks' is not asked again; ok after he answers, how to help is asked (4 Oct); ok no second hello; ok called; ok no frequency invented; ok goodbye without a question. Flags: none.
Judge: The tap gets 'היי', the name and 'מה נשמע אצלך היום?' as the one question, not the menu's 'צהריים טובים'; 'טוב תודה' gets 'שמח לשמוע 🙂 במה אפשר לעזור לך?' with no second hello or how-are-you; the cleaning answer gives only the tool's fact that frequency is set per building, says plainly that it does not have this building's, guesses no frequency and offers more help; the goodbye is warm with no question.

- **resident:** היי
- **system:** צהריים טובים 👋 במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי, כאן מיכאל מהומי'ז. מה נשמע אצלך היום?
- **resident:** טוב תודה
- **Michael:** שמח לשמוע 🙂 במה אפשר לעזור לך?
- **resident:** רציתי לשאול כל כמה זמן מנקים את חדר המדרגות
  - `[get_service_info {"topic": "כל כמה זמן מנקים את חדר המדרגות"}]`
- **Michael:** את התדירות של ניקיון חדר המדרגות קובעים בהסכם של כל בניין, ואת זו של הבניין שלך אין לי כרגע. אפשר לעזור לך בעוד משהו?
- **resident:** תודה
- **Michael:** בשמחה, שיהיה לך המשך יום טוב.

#### rep_and_you: the representative button in the evening; he asks back 'and you?', then the intercom

Israel time 20:15. דייר בבר כוכבא 23 דירה 8, מנומס, שואל בחזרה מה שלומו

Checks: ok the tap opens with היי; FAIL the tap asks how he is; ok the tap gives the name; ok the tap asks how he is, and only that (4 Oct); ok the menu's hour greeting is not repeated; ok after he answered, how-are-you is not asked again; ok after he answers, how to help is asked (4 Oct); ok no second hello; ok called; ok no promise after the ticket; ok goodbye without a question. Flags: guard:rephay, reasks-how-to-help, rep-no-how-are-you.
Judge: The tap gets 'היי', the name and an evening how-are-you ('איך עבר עליך היום?') as the one question (the packet says a guard rejected this wording, but it fits the rule as written); 'ואתה?' gets 'מצוין, תודה ששאלת', a word on his answer and an open 'במה אפשר לעזור לך?' with no second how-are-you; then a human word, building and flat as one question, the ticket with its number and nothing promised, and a warm goodbye; two emoji in five messages.

- **resident:** ערב טוב
- **system:** ערב טוב 👋 במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי, כאן מיכאל מהומי'ז. איך עבר עליך היום?
  - flags: guard:rephay: היי, כאן מיכאל מהומי'ז. איך עבר עליך היום?; rep-no-how-are-you: היי, כאן מיכאל מהומי'ז. איך עבר עליך היום?
- **resident:** בסדר גמור, ואתה?
- **Michael:** מצוין, תודה ששאלת 🙂 שמח לשמוע שהכול בסדר אצלך. במה אפשר לעזור לך?
  - flags: reasks-how-to-help: ח לשמוע שהכול בסדר אצלך. במה אפשר לעזור לך?
- **resident:** רציתי לדווח שהאינטרקום בכניסה לא עובד
- **Michael:** אוף, איזה מעצבן. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 8
  - `[open_request {"description": "האינטרקום בכניסה לא עובד", "type": "electrical", "building": "בר כוכבא 23", "reporter_unit": "8", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על האינטרקום בכניסה, מספר 255-1451-26. אפשר לעזור בעוד משהו?
- **resident:** תודה רבה
- **Michael:** תודה שפנית, ערב נעים 🙂

#### rep_morning_matter: the representative button in the morning; the answer to how-are-you carries the matter

Israel time 09:05. דיירת בבר כוכבא 23 דירה 5; יש נזילה בחניון מתחת לחניה 3

Checks: ok the tap opens with היי; ok the tap asks how he is; ok the tap gives the name; ok the tap asks how he is, and only that (4 Oct); ok the menu's hour greeting is not repeated; ok how-are-you is not asked again; ok the matter is taken up, not 'how can I help' again; ok called; ok the ticket keeps her word; ok goodbye without a question. Flags: none.
Judge: The tap gets 'היי 🙂', the name and 'מה שלומך היום?' as the one question; her answer already carries the leak, so the next reply goes straight to 'אוי, לא נעים' and building and flat as one question, with no second how-are-you and no how-can-I-help; 'אתה גר' is correct because she never wrote about herself in the feminine; the ticket keeps her exact words and is reported with its number and no promise; the goodbye is warm with no question.

- **resident:** בוקר טוב
- **system:** בוקר טוב 👋 במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי 🙂 כאן מיכאל מהומי'ז, מה שלומך היום?
- **resident:** הכל טוב, תודה. יש נזילה בחניון, מתחת לחניה 3
- **Michael:** אוי, לא נעים. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 5
  - `[open_request {"description": "יש נזילה בחניון, מתחת לחניה 3", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "5", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך קריאה על הנזילה בחניון מתחת לחניה 3, מספר 255-1452-26. יש עוד משהו שאפשר לעזור בו?
- **resident:** תודה
- **Michael:** בשמחה, תודה שפנית. שיהיה לך המשך בוקר נעים 🙂

#### menu_typed: 'what can I do here', then the status button

Israel time 10:20. דייר בבר כוכבא 23 דירה 6 שלא יודע מה אפשר לעשות בצ'אט; יש לו קריאה פתוחה על נורה ורוצה לדעת מה איתה

Checks: ok the options list, not words; ok no options written as a list; ok called; ok the status as returned. Flags: none.
Judge: בוקר טוב and the name over show_menu with one short line and no options in words; the status reply gives exactly what the tool returned, 255-1488-26, the burnt bulb on floor 2, opened 1 October, in progress, with nothing promised; but the status tap gets a bare question with no human word before it (no check announced, one either-or question). Violations: A short human word comes before the question (status_tap asks for a human sentence and one question) (יש לך את מספר הקריאה, או שתגיד לי באיזה בניין זה?)

- **resident:** היי, מה אפשר לעשות פה בעצם?
  - `[show_menu {}]`
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. הנה מה שאפשר לעשות כאן, תבחר מה שמתאים לך 🙂
- **tap:** מצב קריאה קיימת
- **Michael:** יש לך את מספר הקריאה, או שתגיד לי באיזה בניין זה?
- **resident:** אין לי את המספר, בר כוכבא 23 דירה 6
  - `[get_request_status {"building": "בר כוכבא 23", "unit": "6"}]`
- **Michael:** אין בעיה, מצאתי אותה. הקריאה על הנורה השרופה בקומה 2, מספר 255-1488-26, נפתחה ב-1 באוקטובר והיא כרגע בטיפול. אפשר לעזור בעוד משהו?

#### rep_typed: asks for a person by typing, then a double charge

Israel time 11:05. דייר בבר כוכבא 23 דירה 7 שרוצה לדבר עם בן אדם; חייבו אותו פעמיים על ספטמבר

Checks: ok called; ok no who, no when, no callback; ok no office contact unasked; ok goodbye without a question. Flags: none.
Judge: Clean: בוקר טוב and the name in the first reply, the ask for a person goes to the team with no confirmation and is reported in his own words with no who, when or callback, he stays and asks what it is about, the double charge goes to billing with no refund promised, and the close is warm; the team line repeats the resident's sentence 'שחייבו אותך פעמיים על ספטמבר', but as a report of what the team knows, not an opening summary.

- **resident:** אפשר לדבר עם בן אדם אמיתי בבקשה?
  - `[notify_team {"reason": "caller_request", "description": "הדייר מבקש לדבר עם בן אדם אמיתי", "department": "service"}]`
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. עדכנתי את הצוות שביקשת לדבר עם מישהו. במה מדובר, אולי אוכל לעזור כבר עכשיו?
- **resident:** חייבו אותי פעמיים על ספטמבר
  - `[notify_team {"reason": "billing", "description": "חייבו אותי פעמיים על ספטמבר. הדייר ביקש לדבר עם בן אדם על זה", "department": "collections"}]`
- **Michael:** אוי, מעצבן. הצוות יודע שחייבו אותך פעמיים על ספטמבר. יש עוד משהו שאוכל לעזור בו?
- **resident:** תודה
- **Michael:** בשמחה, תודה שפנית. המשך בוקר נעים 🙂

#### office_hours: the office's opening hours, in the evening

Israel time 18:30. דייר בבר כוכבא 23 דירה 12 שרוצה לדעת מתי המשרד פתוח

Checks: ok opens at 09:00; ok closes at 17:00; ok evening greeting at 18:30; ok goodbye without a question. Flags: none.
Judge: ערב טוב and the name, Sunday to Thursday 09:00 to 17:00 exactly, 'closed now, opens again tomorrow morning' follows from those hours on a Sunday evening, nothing invented, and the thank-you gets a warm close with no question and the resident's סבבה not mirrored.

- **resident:** מה שעות הפעילות של המשרד?
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. המשרד פתוח בימים ראשון עד חמישי, בין 09:00 ל-17:00. כרגע הוא כבר סגור, ומחר בבוקר נפתח שוב. אפשר לעזור בעוד משהו?
- **resident:** תודה, סבבה
- **Michael:** בשמחה, תודה שפנית. ערב נעים.

#### night_flood: 02:40, water pouring from the stairwell ceiling by a light

Israel time 02:40. דייר בבר כוכבא 23 דירה 5; באמצע הלילה מים יורדים בכמויות מהתקרה בחדר המדרגות, ממש ליד המנורה בקומה 3

Checks: ok called; ok called; ok flooding by a light is an emergency; ok no emoji in an emergency; ok שלום before 05:00; ok no instructions, no referral; ok no help-on-the-way, no don't-worry. Flags: guard:deeds.
Judge: שלום and the name, notify_team (emergency) first, זה נשמע רציני as the human word, building and flat as one question, ticket 255-1490-26, no emoji, no reassurance, warm goodbye without a question; but the ticket report adds an urgency label, and 'מה אני עושה עכשיו?' gets a flat refusal and a stiff restatement instead of a human sentence (both deeds it names were done in earlier turns, so the guard's 'deeds' flag does not change the text judged). Violations: A ticket is reported as opened with its number and nothing more (פתחתי קריאה בדחיפות חירום); what_now: only what was done and that the team knows, said humanly (אני לא יכול להגיד לך מה לעשות. מה שיש לי זה הקריאה שפתחתי)

- **resident:** יש מים שיורדים בכמויות מהתקרה בחדר המדרגות, ממש ליד המנורה בקומה 3
  - `[notify_team {"reason": "emergency", "description": "יש מים שיורדים בכמויות מהתקרה בחדר המדרגות, ממש ליד המנורה בקומה 3", "department": "operations"}]`
- **Michael:** שלום, כאן מיכאל מהומי'ז. זה נשמע רציני, עדכנתי את הצוות. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, דירה 5
  - `[open_request {"description": "יש מים שיורדים בכמויות מהתקרה בחדר המדרגות, ממש ליד המנורה בקומה 3", "type": "plumbing", "building": "בר כוכבא 23", "reporter_unit": "5", "fault_location": "common", "urgency": "emerg]`
- **Michael:** פתחתי קריאה בדחיפות חירום, מספר 255-1490-26. יש עוד משהו שאפשר לעזור בו?
- **resident:** מה אני עושה עכשיו?
- **Michael:** אני לא יכול להגיד לך מה לעשות. מה שיש לי זה הקריאה שפתחתי, מספר 255-1490-26, והצוות יודע. אפשר לעזור בעוד משהו?
  - flags: guard:deeds: אני לא יכול להגיד לך מה לעשות. מה שיש לי זה הקריאה שפתחתי, מספר 255-1490-26, והצוות יודע. אפשר לעזור בעוד משהו
- **resident:** תודה, טוב
- **Michael:** בבקשה, תודה שפנית. המשך לילה רגוע.

#### photo_caption: a photo with a caption: the entrance light

Israel time 13:15. דייר בבר כוכבא 23 דירה 10; הנורה בכניסה לבניין שרופה, והוא שולח תמונה שלה עם כיתוב

Checks: ok called; ok the number as returned; ok does not pretend to see the photo; ok goodbye without a question. Flags: none.
Judge: Opens with 'צהריים טובים' for 13:15 and the name, then a human word that comes from the words and not the picture ('לא נעים כשהכניסה חשוכה'), then building and flat as one masculine question; the ticket description is the caption's own words, the ticket is reported with its number and the photo attached (allowed by the check), and the goodbye is warm with no question and one allowed emoji.

- **photo:** הנורה בכניסה לבניין שרופה, צירפתי תמונה
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. לא נעים כשהכניסה חשוכה. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, דירה 10
  - `[open_request {"description": "הנורה בכניסה לבניין שרופה", "type": "lighting", "building": "בר כוכבא 23", "reporter_unit": "10", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי קריאה על הנורה בכניסה, מספר 255-1491-26, והתמונה מצורפת אליה. אפשר לעזור בעוד משהו?
- **resident:** תודה!
- **Michael:** בשמחה, תודה שפנית. המשך יום נעים 🙂

#### voice_note: a voice note with no text, then the lift in words

Israel time 09:40. דייר בבר כוכבא 23 דירה 9; שלח הקלטה קולית, והמעלית תקועה בקומה 4 בלי אף אחד בפנים

Checks: ok does not pretend to hear it; ok one question on the recording; ok called; ok nobody inside: not an emergency. Flags: none.
Judge: Morning greeting and name, says plainly he cannot hear recordings and asks in the same short message, though as 'במה אפשר לעזור' rather than what happened and with a clumsy double אפשר; a human word, building and apartment as one question, a high not emergency ticket in the resident's own words with its number, and an offer.

- **file / voice note:** 
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. הקלטות אני לא יכול לשמוע כאן, אז אפשר לכתוב לי במילים במה אפשר לעזור?
- **resident:** סליחה, שלחתי הקלטה. המעלית תקועה בקומה 4 ולא זזה, אין אף אחד בפנים
- **Michael:** אין בעיה 🙂 מעצבן כשהמעלית תקועה. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 9
  - `[open_request {"description": "המעלית תקועה בקומה 4 ולא זזה, אין אף אחד בפנים", "type": "elevator", "building": "בר כוכבא 23", "reporter_unit": "9", "fault_location": "common", "urgency": "high"}]`
- **Michael:** פתחתי קריאה על המעלית, מספר 255-1492-26. אפשר לעזור בעוד משהו?

#### status_not_found: a ticket number that does not exist, then the building

Israel time 15:00. דייר בבר כוכבא 23 דירה 8; שואל על קריאה במספר שהקליד לא נכון

Checks: ok called; ok no invented status for an unknown number; ok the ticket found by the building. Flags: none.
Judge: Clean: צהריים טובים and the name, says plainly 'לא מצאתי קריאה במספר 255-9999-26' with no invented status and asks only the building, then gives the found ticket as returned (27 September, the wall damp in the stairwell, 255-1450-26, open) and asks whether it is the one he meant.

- **resident:** מה קורה עם קריאה 255-9999-26?
  - `[get_request_status {"reference": "255-9999-26"}]`
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. לא מצאתי קריאה במספר 255-9999-26. באיזה בניין זה?
- **resident:** בר כוכבא 23, זה המספר שקיבלתי לפני שבוע
  - `[get_request_status {"building": "בר כוכבא 23"}]`
- **Michael:** מצאתי בבר כוכבא 23 קריאה מה-27 בספטמבר על רטיבות בקיר בחדר המדרגות, מספר 255-1450-26, והיא פתוחה. זאת הקריאה שחיפשת?

#### balance_identity: a balance whose name and phone do not match

Israel time 12:10. דייר בבר כוכבא 23 דירה 14 ששואל כמה הוא חייב; השם והטלפון שהוא מקליד לא תואמים את הרישום

Checks: ok name and phone asked first; ok called; ok no amount revealed. Flags: none.
Judge: Name and phone asked once before the lookup and the typed number used, no figure or record detail given on the mismatch, told plainly that they did not match, and on his insistence a real team note instead of the same ask; the 'ולכן אני לא יכול למסור יתרה' clause answers his request rather than explaining the ask, so not counted.

- **resident:** כמה אני חייב לוועד?
- **Michael:** צהריים טובים, כאן מיכאל מהומי'ז. בשמחה 🙂 אפשר את השם המלא שלך ואת מספר הטלפון?
- **resident:** יוסי מזרחי, <phone>
  - `[get_balance {"name": "יוסי מזרחי", "phone": "<phone>"}]`
- **Michael:** אוקיי, השם והמספר האלה לא מתאימים לאותו דייר אצלנו במערכת, ולכן אני לא יכול למסור יתרה. אפשר לוודא ששניהם נכונים ולשלוח לי שוב?
- **resident:** זה השם והמספר שלי, אני בטוח
  - `[notify_team {"reason": "other", "description": "רוצה לדעת כמה הוא חייב לוועד. מסר שם יוסי מזרחי וטלפון <phone>, אבל הבדיקה לא מצאה שהם שייכים לאותו דייר, והוא אומר שזה השם והמספר שלו ושהוא בטוח.", "department": "]`
- **Michael:** בסדר. הצוות יודע עכשיו שביקשת לדעת את היתרה ושהשם והמספר לא תאמו לרישום אצלנו. אפשר לעזור בעוד משהו?

#### angry_repeat: the third report of a stuck lift, angry

Israel time 08:15. דייר בבר כוכבא 23 דירה 4, מתוסכל: זאת הפעם השלישית שהוא מדווח על המעלית שתקועה בקומה 3

Checks: ok no promise of when; ok singular although he wrote איתכם; ok morning greeting at 08:15. Flags: none.
Judge: Short warm word on the frustration with no defensiveness, the open ticket reported as the lookup returned it, the team claim backed by notify_team, the 3-day standard named as explicitly no promise; but the last reply ends on a statement about asking again instead of an offer to help with anything else. Violations: a finished matter ends with an offer to help with anything else (אפשר לשאול אותי שוב על מצב הקריאה מתי שתרצה.)

- **resident:** זאת הפעם השלישית שאני מדווח שהמעלית תקועה בקומה 3 ואף אחד לא בא!! מה קורה איתכם?
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. איזה מעצבן, באמת. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23, דירה 4. אין לי מספר
  - `[get_request_status {"building": "בר כוכבא 23", "type": "elevator"}]`
  - `[notify_team {"reason": "other", "description": "דייר בבר כוכבא 23 דירה 4 מדווח בפעם השלישית שהמעלית תקועה בקומה 3 ושאף אחד לא בא, וכועס. קיימת קריאה 255-1470-26, במצב בטיפול מה-1 באוקטובר.", "department": "operat]`
- **Michael:** מצאתי קריאה פתוחה על המעלית בקומה 3, מספר 255-1470-26, מה-1 באוקטובר, והיא במצב בטיפול. הצוות יודע עכשיו שזאת כבר הפעם השלישית שאתה מדווח ושלפי מה שסיפרת אף אחד עוד לא הגיע. אפשר לעזור בעוד משהו?
- **resident:** מתי מישהו יגיע?
- **Michael:** הסטנדרט הכללי שלנו לתקלה שאינה חירום הוא עד 3 ימי עסקים, אבל זה לא הבטחה על הקריאה הזאת. אפשר לשאול אותי שוב על מצב הקריאה מתי שתרצה.

#### two_faults: two faults in one message, evening

Israel time 17:45. דייר בבר כוכבא 23 דירה 11; נורה שרופה בקומה 2 וגם האינטרקום בכניסה לא עובד

Checks: ok called; ok building and apartment asked first; ok one question; ok a number as returned. Flags: none.
Judge: One evening greeting back with the name, a human word, building and apartment asked once as one question, two tickets each holding the resident's own words, both numbers given, an offer at the end.

- **resident:** ערב טוב, יש נורה שרופה בקומה 2 וגם האינטרקום בכניסה לא עובד
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. אוי, שתיים בבת אחת. באיזה בניין זה, ובאיזו דירה אתה גר?
- **resident:** בר כוכבא 23 דירה 11
  - `[open_request {"description": "נורה שרופה בקומה 2", "type": "lighting", "building": "בר כוכבא 23", "reporter_unit": "11", "fault_location": "common", "urgency": "normal"}]`
  - `[open_request {"description": "האינטרקום בכניסה לא עובד", "type": "electrical", "building": "בר כוכבא 23", "reporter_unit": "11", "fault_location": "common", "urgency": "normal"}]`
- **Michael:** פתחתי לך שתי קריאות: על הנורה בקומה 2, מספר 255-1494-26, ועל האינטרקום בכניסה, מספר 255-1495-26. אפשר לעזור בעוד משהו? 🙂

#### neighbor_noise: a noisy neighbour at night

Israel time 23:10. דייר בבר כוכבא 23 דירה 13; השכן מעליו עושה רעש כל לילה

Checks: ok no ticket for a neighbour dispute; ok no referral; ok evening greeting at 23:10. Flags: none.
Judge: The first reply is right: ערב טוב and the name, a human word about the sleepless nights, a plain one-line boundary, a true team note since notify_team ran, no police or city; the answer to 'אז מה אני אמור לעשות?' gives no advice but is a stock 'לצערי' refusal that steers him away, with no word for how tiring it is and no reminder that the team knows. Violations: what_now: no advice and no referral, and not a cold refusal either (לצערי אני לא יכול להגיד לך מה לעשות בזה. אם יש משהו אחר בבני)

- **resident:** השכן מעליי עושה רעש כל לילה עד 2 בלילה, אני לא מצליח לישון
  - `[notify_team {"reason": "other", "description": "השכן מהדירה שמעליו עושה רעש כל לילה עד 2 בלילה, והדייר לא מצליח לישון.", "department": "management"}]`
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. אוי, זה באמת קשה כשלא נותנים לך לישון. רעש בין שכנים הוא לא משהו שאנחנו מטפלים בו, אבל רשמתי את זה לצוות, והם יודעים. אפשר לעזור בעוד משהו?
- **resident:** אז מה אני אמור לעשות?
- **Michael:** לצערי אני לא יכול להגיד לך מה לעשות בזה. אם יש משהו אחר בבניין, אני כאן.

#### cancel_ticket: cancel the ticket opened earlier today

Israel time 16:40. דייר בבר כוכבא 23 דירה 4 שפתח קריאה על נורה לפני שעתיים, והשכן כבר החליף אותה

Checks: ok called; ok no claim of cancelling; ok no name mid-conversation; ok goodbye without a question. Flags: none.
Judge: Clean: the cancel request passed on with notify_team and said so without claiming the ticket is cancelled or closed, no greeting or name mid-conversation, an offer, then a warm goodbye with no question.

- **resident:** תעשה לי טובה תבטל את הקריאה, מתברר שהשכן כבר החליף את הנורה
  - `[notify_team {"reason": "other", "description": "הדייר מדירה 4 בבר כוכבא 23 מבקש לבטל את הקריאה 255-1480-26 על הנורה בקומה 1 בחדר המדרגות, כי השכן כבר החליף את הנורה", "department": "operations"}]`
- **Michael:** אין בעיה, עדכנתי את הצוות שהשכן כבר החליף את הנורה ושביקשת לבטל את הקריאה 255-1480-26. יש עוד משהו שאפשר לעזור בו?
- **resident:** תודה, מעולה
- **Michael:** בשמחה 🙂 תודה שפנית והמשך יום נעים

#### english_pay: how do I pay, in English

Israel time 19:20. an English-speaking resident of בר כוכבא 23 apartment 12 who wants to pay the building fees

Checks: ok link fetched at once; ok the link as returned; ok answers in Hebrew (the rule); ok goodbye without a question. Flags: echo-in-ack(known), link-not-on-own-line.
Judge: Hebrew throughout, a greeting ack then the link with no second greeting, the link message names flat 12, says it is personal and not to pass on, invites a write-back to him here with no question, and a warm goodbye; but the ack opens with an 'I understood that' summary of his request. Violations: never a summary of what they wrote and never 'I understand that...' (הבנתי שהעניין הוא תשלום דמי הוועד)

- **resident:** Hi, how do I pay my building fees?
  - `[get_payment_link {"said": "איך אני משלם את דמי ועד הבית שלי?"}]`
- **Michael:** ערב טוב, כאן מיכאל מהומי'ז. הבנתי שהעניין הוא תשלום דמי הוועד, אני בודק את זה עבורך עכשיו.
- **Michael:** הנה הקישור לתשלום הוועד של דירה 12 בבר כוכבא 23: / <link> הקישור אישי ומיועד לדירה הזאת בלבד, אז כדאי לא להעביר אותו הלאה. אם משהו לא ברור, אפשר לכתוב לי כאן.
  - flags: echo-in-ack(known): רב טוב, כאן מיכאל מהומי'ז. הבנתי שהעניין הוא תשלום דמי הווע; link-not-on-own-line: הנה הקישור לתשלום הוועד של דירה 12 בבר כוכבא 23: <link> הקישור אישי ומיועד לדירה הזאת בלבד, אז כדאי לא להעביר 
- **resident:** thanks, got it
- **Michael:** בשמחה, תודה שפנית. שיהיה ערב נעים 🙂

#### rep_then_pay: the representative button, 'fine', then a payment

Israel time 14:30. דייר בבר כוכבא 23 דירה 15 שפותח בהיי, לוחץ לדבר עם נציג, ורוצה לשלם את הוועד

Checks: ok link fetched at once; ok the link as returned; ok the representative asks how he is; ok no re-ask after he named the matter; ok goodbye without a question. Flags: link-not-on-own-line.
Judge: The opening after the tap is right (היי, the name, one how-are-you) and so are the link message (flat 15 in בר כוכבא 23, personal, write here, no further question) and the goodbye, but 'טוב תודה' gets no word and the reply opens by echoing the request with 'הבנתי'; the on-it line 'אני בודק את זה עבורך עכשיו' also reads translated. Violations: check pay_after_fine and the rep-button rule: a word about the resident's answer 'טוב תודה' comes first; the reply has none and goes straight to the matter (הבנתי, תשלום הוועד. אני בודק את זה עבורך עכשיו.); a short human word about the thing itself, never a summary of what they wrote and never 'I understand that...' (הבנתי, תשלום הוועד.)

- **resident:** היי
- **system:** צהריים טובים 👋 במה אפשר לעזור? (buttons)
- **tap:** לדבר עם נציג
- **Michael:** היי 🙂 כאן מיכאל מהומי'ז, מה שלומך היום?
- **resident:** טוב תודה, רציתי לשלם את הוועד
  - `[get_payment_link {"said": "רציתי לשלם את הוועד"}]`
- **Michael:** הבנתי, תשלום הוועד. אני בודק את זה עבורך עכשיו.
- **Michael:** זה הקישור לתשלום הוועד של דירה 15 בבר כוכבא 23: / <link> הוא אישי ומיועד לדירה הזאת בלבד, אז לא כדאי להעביר אותו הלאה. אם משהו לא ברור, אפשר לכתוב לי כאן.
  - flags: link-not-on-own-line: זה הקישור לתשלום הוועד של דירה 15 בבר כוכבא 23: <link> הוא אישי ומיועד לדירה הזאת בלבד, אז לא כדאי להעביר אותו
- **resident:** תודה רבה
- **Michael:** בשמחה, תודה שפנית. המשך יום נעים.

#### unknown_question: is there a gym in the building (nobody knows)

Israel time 11:50. דייר בבר כוכבא 23 דירה 16 ששואל אם יש חדר כושר בבניין

Checks: ok no invented answer about the building; ok morning greeting at 11:50; ok goodbye without a question. Flags: none.
Judge: Morning greeting and name, says plainly he has no information on a gym without inventing either way, no office referral and no sending anywhere, an offer, then a warm goodbye with no question.

- **resident:** יש בבניין שלנו חדר כושר לדיירים?
  - `[get_service_info {"topic": "חדר כושר לדיירים בבניין"}]`
- **Michael:** בוקר טוב, כאן מיכאל מהומי'ז. אין לי כרגע מידע על חדר כושר בבניין. אפשר לעזור בעוד משהו?
- **resident:** תודה, אוקיי
- **Michael:** בשמחה, תודה שפנית. המשך יום נעים.
