# Testing the inbound agent in Hebrew — what to say, and what to watch

Four calls. Your lines are the numbered ones; read them aloud and say nothing
else, because the point is to test the agent rather than to have a conversation
with it.

**Call it from the demo page, not the Vapi dashboard.** A dashboard *Talk* test
sends `variableValues: {}`, and on 5 Aug that made the debt agent invent an
amount and a month out of two empty variables. Inbound has no variables today, so
the dashboard would work — but the habit is what matters, and the habit was worth
one wasted diagnosis already.

Assistant: **`f482abc1-db69-422b-afdd-f7b40ca9d995`** — *Homies — Inbound Intake
(he)*. The English twin is `8b98016b-…` and takes the same script translated.

> **The Hebrew below is written, not transcribed.** Same caveat as the prompt
> itself: no native speaker has read it aloud. If a line sounds wrong when you
> say it, the line is wrong, not you.

---

## Call 1 — the ordinary one, which is the one that matters

This is the whole product in ninety seconds. Everything else is an exception.

| | You say | What should happen |
|---|---|---|
| 1 | *(let it greet you first, then)* **שלום, יש לי נזילה מהתקרה בחדר האמבטיה, זה כבר יומיים** | It should **not** thank you for telling it. One short question back, and the question should be about the building — it has your description already. |
| 2 | **הרצל 14** | Asks the apartment. Nothing else. |
| 3 | **דירה 12** | Reads it back as one sentence with **no reference number in it** — the number does not exist yet. |
| 4 | **כן, נכון** | *Now* it writes. You may hear `רגע, אני רושמת`. Then it reads a reference number **digit by digit**. |
| 5 | **לא, זה הכל, תודה** | It closes: `תודה שהתקשרת להומיז, יום טוב, ולהתראות` — **and the call ends by itself.** |

**Step 5 is the new thing.** Until today this agent had no way to end a call at
all: it read out the reference, stopped talking, and the line sat open in silence
for thirty seconds. If the call does not hang up on its own here, the closing
phrase is not matching and that is the finding.

**Step 4 is the other one.** A 97-second English call on 5 Aug got a leak, a
building and an apartment and called **no tools at all**. If you get a reference
number that starts `HM-`, the write path worked.

---

## Call 2 — asking about something it cannot look up

The single easiest thing in the whole call to get wrong, because you will hand it
a reference number and it will feel like you have handed it the answer.

| | You say | What should happen |
|---|---|---|
| 1 | **שלום, רציתי לבדוק מה קורה עם הפנייה שפתחתי בשבוע שעבר** | Refuses plainly: `אין לי גישה לסטטוס של פניות קיימות`. |
| 2 | **המספר הוא HM-2026-1001** | Still refuses. It must **not** say it is checking, must not read the number back as though confirmed, and must not say the request "is open" or "is being handled". |
| 3 | **בסדר, תודה** | Says a representative will get back to you, then closes. |

**Listen for what it does not say.** It must never say `אני מעבירה אותך` — nobody
is standing by to pick up, and until today it promised exactly that in five
different places. The honest version is `אני מעבירה את זה לנציג שיחזור אליך`.

---

## Call 3 — three things at once

Tests that nothing drops silently, which is how someone leaves a call believing
something was logged when it was not.

| | You say | What should happen |
|---|---|---|
| 1 | **יש נזילה באמבטיה, וגם האור בלובי לא עובד, ובנוסף קיבלתי חשבון שאני לא מבין** | Should acknowledge all three. |
| 2 | **הרצל 14, דירה 12** | Two requests get opened — the leak and the light. The bill is named as needing a person. |
| 3 | **כן** *(to whatever it confirms)* | Reads both references back **together, once** — not one at a time. |
| 4 | **לא, תודה** | Closes. |

The bill must be handed off, not answered. A wrong answer about money costs more
than any number of transfers.

---

## Call 4 — the apartment number, which is where calls actually die

Every call contains one, and compound Hebrew numerals are where nearly all the
errors live.

| | You say | What should happen |
|---|---|---|
| 1 | **הדוד חשמל לא עובד** | Asks the building. |
| 2 | **בן גוריון 3** | Asks the apartment. |
| 3 | **מאה עשרים ושתיים** *(say it fast)* | Either it gets 122, or it asks again **differently** — `אפשר להגיד לי את מספר הדירה ספרה ספרה?`. The identical question twice is a fail. |
| 4 | **אחת, שתיים, שתיים** | Should read it back before writing. |
| 5 | **כן** | Reference number, then closes. |

If it writes an apartment you did not say, that is the worst outcome in the
system — a technician goes to a stranger's door and nobody finds out until they
knock. Empty beats wrong.

---

## After the calls

Two places to check, and they answer different questions.

**The sheet** — did the row land, with the right building and apartment? That is
the only thing that proves the tool fired rather than the agent sounding like it
did.

**The call record** — `endedReason`. For calls 1–4 you want:

    assistant-said-end-call-phrase

That is the agent closing properly. `customer-ended-call` means you hung up
first, which tells you nothing. `silence-timeout` means it stopped talking and
never closed — the failure this week's change was meant to remove.

Worth timing call 1 end to end. The cap is **180 seconds** with no warning — Vapi
hangs up mid-word — and nobody has ever measured a real Hebrew intake call. If
the median comes in near three minutes, the cap is wrong and has to move.
