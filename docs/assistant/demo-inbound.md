# The week-3 demo assistant — inbound intake

Vapi assistant **`8894680c-03af-43f6-a75b-f828872833cc`** — *Homies — Inbound
Intake (he)*. Created 3 Aug 2026 and live. Called *(demo)* until 5 Aug, renamed
the day it gained an English twin — `vapi_sync.py` finds its target **by name**,
so that string and the live name have to move together or the next `--apply`
creates a second assistant instead of failing.

**The English twin is `8672e3b6-dfc7-40a3-af33-c572d5b4b66b`** — *Homies —
Inbound Intake (en)*. It is not edited directly and has no document of its own:
`scripts/vapi_en.py intake` reads this assistant live and applies 21
substitutions, each of which must match exactly once or it refuses to build.
Change the Hebrew here, re-sync, then re-run that script with `--update
8672e3b6-dfc7-40a3-af33-c572d5b4b66b`. If a passage in the table stops matching
it stops rather than shipping half a translation, which is the only reason the
twin can be trusted to represent the Hebrew one.

**This file is the source of truth, not the dashboard.** `scripts/vapi_sync.py`
reads the first message and the system prompt straight out of this document and
pushes them. Edit here and re-run it; edit in the dashboard and the two drift
apart with nothing to tell you.

```
python scripts/vapi_sync.py            # dry run
python scripts/vapi_sync.py --apply    # write
```

The ID `f5c758d8-9246-4f70-89a7-2eea5f1ec9df` appears throughout the feature
files as though it were this assistant. **It is not.** It is *Homies Collection
(EN test)* — English, Deepgram `nova-2`, Vapi's `Elliot` voice, with a balance of
450 shekels hardcoded into its prompt. It is an ancestor of
[10-debt-followup](../features/10-debt-followup/feature.md), not of this. It was
left untouched.

This is the executable form of [the demo design](../specs/2026-08-02-demo-design.md)
and features [01](../features/01-identity/feature.md)–[08](../features/08-instrumentation/feature.md).
Where this file and a `feature.md` disagree, the `feature.md` wins and this file
is wrong — it is downstream of them, not a second opinion.

**Every Hebrew line below is written, not transcribed.** No native speaker has
checked them. They must be read aloud by one before rehearsal, the same
condition that applies to [the debt prompt](../features/10-debt-followup/prompt.md).

---

## Platform configuration

Everything except the last two rows comes from `BASE` in `vapi_sync.py` and is
shared with the debt agent. This table is a reading of that code, not a second
place to change it — it was wrong for two days after the stack moved and nothing
reported it, because a document cannot fail a test.

| | Value | Why |
|---|---|---|
| Transcriber | `deepgram`, `nova-3`, `he`, `confidenceThreshold` 0.4 | **The client reversed this in the dashboard on 12 Aug and the table was not updated until 30 Aug.** It read `11labs`/`scribe_v2_realtime` for eighteen days. Scribe still tops the Hebrew WER benchmarks and lost anyway, on the axis nobody had weighed: 700ms against nova-3's 300ms, on every turn of every call. If Hebrew mishears audibly worsen, this is the first thing to put back — see the block in `vapi_sync.py`, which carries the whole argument. |
| Fallback transcriber | `azure`, `he-IL` | Both legs Hebrew, so no path ends with an English transcriber listening to a Hebrew resident. Fires when the provider *fails*, not when it transcribes Hebrew badly. |
| Model | `gpt-4.1-mini` | Latency. A frontier model buys nothing for slot-filling and roughly doubles the LLM line. The debt agent runs gpt-5.4 because it argues with people; this one fills four fields. |
| Voice | `cartesia`, Eyal, `sonic-3` | Male, and every line the agent speaks below is masculine first person to match. Hebrew marks the speaker's gender on the verb, so the voice and the wording are one change, never two. Was `vapi/Leah` and feminine until 7 Aug; `vapi/Elliot` is the fallback leg and is an English voice model reading Hebrew, which is a fallback and not an option. |
| Output guard | `voice.chunkPlan.formatPlan` | 27 replacements that delete tool syntax before the voice provider sees it. See `scripts/voice_guard.py`. **This lives inside `voice`, so editing the voice in the dashboard deletes it.** |
| Smart endpointing | provider `vapi`, **not** `livekit` | LiveKit's endpointing model is tuned for English. Hebrew needs Vapi's. |
| `maxDurationSeconds` | **180** | Asked for directly on 5 Aug. Read the time budget below before changing it — the number alone is not safe. |
| `silenceTimeoutSeconds` | 30 | Inbound silence is usually someone reading a number off a wall, not a dead line. |
| `endCallPhrases` | `and goodbye`, `ולהתראות` | **The only thing that ends a call.** Added 5 Aug — see below. |
| `endCallFunctionEnabled` | **false** | Explicit, not inherited. If it comes on, the model gets a way to hang up without speaking. |
| `artifactPlan.recordingEnabled` | **false** | Turned off by the client — transcript only, no audio kept. This row said `true` until 30 Aug. It is not a detail: the 30 Aug number-stutter could not be settled as voice-looping versus transcriber-looping because there was no audio to listen to. Turning it back on even once is the owner's call. |
| `server` | the `debt-tools` Edge Function | Added 8 Aug. Where the end-of-call report goes. Resolved by `report_server()` and deliberately **not** by `tool_server()` — the tools follow where the integrations live and currently pick n8n, which has no handler for a server message and would answer 200 while writing nothing. |
| `serverMessages` | `["end-of-call-report"]` | One, not eleven. `conversation-update` and `speech-update` fire several times a second into a function writing the same row; the end-of-call report carries everything in a single POST after the call has ended, where nothing it does can cost the caller a millisecond. |

### Three minutes, and why the field is not the feature

`maxDurationSeconds` does not hurry anyone along. Vapi hangs up on the second it
expires, mid-word, and **the model is never told it is coming**. On the outbound
agent that is survivable — the agent drives, and a call still running at four
minutes is one that should have been handed over. Inbound, the caller drives.

So a bare 180 would cut someone off in the middle of describing a leak and write
nothing, which is precisely the outcome the prompt calls the only one that is not
allowed. The cap therefore ships with two companions and is not safe without
them:

1. **The budget section in the prompt**, which spends the time in the order that
   survives being cut off — the row gets written the moment there is a
   description and a location, and everything else happens afterwards.
2. **`save_partial_request`**, which is what the agent reaches for when it can
   see the call is not going to finish.

Both are the model cooperating, which means both can fail. **The third companion,
built 8 Aug, is the one that cannot.** Vapi reports `endedReason:
max-duration-exceeded` in the end-of-call report; the handler in
`supabase/functions/debt-tools/index.ts` sees it, checks whether the call
produced any row at all, and if not writes a `needs_review` request with the
transcript in it. The model is not consulted and cannot decline.

The transcript goes in verbatim rather than summarised, deliberately.
Summarising means guessing the building, and a guessed building on a maintenance
ticket sends somebody to the wrong address.

### The call had no ending, in either direction

Two things were missing until 5 Aug, and they were the same omission twice.

**Nothing could end a call.** No `endCall` function, no `endCallPhrases`, and no
closing line in the prompt to trigger one with. Every inbound call on record
ended `customer-ended-call`, which reads as fine — a caller who rang in usually
does hang up. What it hides is the shape underneath: the agent reads out the
reference number, stops talking, and the line sits open in silence until the
thirty-second timeout closes it. The last thing the caller hears from Homies is
nothing at all, and they have no way to tell whether anything was written down.

The fix is the same one the debt agent got: **saying the closing line is the
only way to hang up.** `endCallFunctionEnabled` stays off, so the words are the
mechanism rather than a request the model can decline. `ולהתראות` carries the
vav, so a bare `להתראות` cannot reach it — the one-word goodbye that cut a debt
call off mid-question is unreachable here.

**And every transfer promised something that does not exist.** `transfer_to_human`
is a function that posts a row to n8n. There is no `transferPlan`, no
destination, no extension — nothing connects anyone to anyone. The prompt said
*"אני מעבירה אותך לנציג"* in five places, so the caller was told they were being
put through, and then sat listening to an open line. All five now say a
representative will get back to them, which is what actually happens, and rule 9
forbids the other phrasing outright.

When a real extension exists, both changes reverse together — the wording goes
back and a `transferPlan` goes in. Until then the honest sentence is the only
one available.

**Do not click the Model Presets in the dashboard.** *Balanced*, *High
Intelligence*, *Ultra Fast* and *Cost Saver* replace the transcriber and the
voice wholesale. Clicking one on 3 Aug swapped this assistant to Talkscriber
Whisper **English** and 11labs **Sarah**, and it answered a Hebrew caller in
English. Neither of those providers does Hebrew. There is no warning and no
undo — the recovery is `python scripts/vapi_sync.py inbound --apply`.

Vapi adds `transcriber.fallbackPlan.autoFallback: true` by itself, and it was
left on. Worth understanding before rehearsal: if Azure `he-IL` fails, Vapi
switches transcriber mid-call — and the alternatives do not do Hebrew. The
failure mode is not silence, it is a call that carries on producing confident
nonsense. If a rehearsal call goes strange for no visible reason, this is the
first thing to check.

### Turn-taking

Feature [04](../features/04-interruption-pacing/feature.md) is almost entirely
these numbers rather than prompt text.

```json
{
  "startSpeakingPlan": {
    "waitSeconds": 0.4,
    "smartEndpointingPlan": { "provider": "vapi" },
    "transcriptionEndpointingPlan": {
      "onPunctuationSeconds": 0.3,
      "onNoPunctuationSeconds": 1.0,
      "onNumberSeconds": 1.0
    }
  },
  "stopSpeakingPlan": {
    "numWords": 2,
    "voiceSeconds": 0.3,
    "backoffSeconds": 1.0
  }
}
```

These are the shared numbers, and two of them reverse what this file used to
say. Both were changed on the debt agent after a real call, and the reasoning
carries here unchanged:

- **`numWords: 2`**, up from 0. Barge-in on voice activity sounded right on
  paper — the spec wants the caller able to stop the agent mid-word — and on a
  real call it made her unusable. People say "אהה" and "כן" *while you are
  talking*; that is listening, not interrupting. At 0 every one of those stopped
  her, and she restarted the sentence from the beginning, three times in one
  opening. Two words is the line between a backchannel and an actual
  interruption.
- **`onNoPunctuationSeconds: 1.0`**, down from 1.8. The 1.8 was set for Azure,
  which punctuates Hebrew poorly enough that the no-punctuation branch carried
  every turn. Measured against that setting the median wait was 2,216ms and the
  worst turn 6,870ms, against a target of 800. Scribe v2 punctuates Hebrew
  properly, so this branch is now the fallback it was always meant to be.
- **`onNumberSeconds: 1.0`** — unchanged, and held longer than punctuation
  because every call contains an apartment number and numbers are where callers
  pause mid-utterance ("דירה… שתים עשרה").

`waitSeconds` came down to the 0.4 default with the rest of the stack.

---

## First message

```
{% assign h = "now" | date: "%H", "Asia/Jerusalem" | plus: 0 %}{% if h < 5 %}שלום{% elsif h < 12 %}בוקר טוב{% elsif h < 17 %}צהריים טובים{% else %}ערב טוב{% endif %}, מדבר מיכאל מהצוות של הומיז. איך אפשר לעזור?
```

**The greeting follows the clock since 22 Sep.** The owner asked that both
agents open with בוקר טוב / צהריים טובים / ערב טוב rather than a flat שלום.
The block in `{% %}` is a Liquid template, which Vapi renders at the moment
the call starts (the same engine that fills `{{first_name}}` on the debt
agent), so the hour is read inside the line itself, in Jerusalem time, and
nothing has to be passed in: an inbound phone call gets it as much as a web
call from the dashboard. Before 05:00 it says שלום (לילה טוב is a goodbye,
not a greeting), 05–11 בוקר טוב, 12–16 צהריים טובים, from 17:00 ערב טוב.
What the voice says is the rendered sentence, e.g. `צהריים טובים, מדבר מיכאל
מהצוות של הומיז. איך אפשר לעזור?`. Two readers do not go through Vapi and
render the block themselves with the same hours: `scripts/prompt_probe.py`,
and until 22 Sep the dashboard's no-call typed chat, which has since been
removed (typing now goes into the live call, where Vapi renders the line).
The `.strip()`-and-regex readers in `vapi_sync.py` are unaffected because the
whole line is still one line.

**The wording is the client's, 30 Aug.** `הומיז, חברת הניהול. אה, מדבר מיכאל`
→ `שלום, מדבר מיכאל מהצוות של הומיז`. The person now comes before the
company, which is how anybody answering a phone introduces themselves.
Two characters shorter, so the three seconds below still stand.

**It was written `מדברת` and is `מדבר` here, and that is not a liberty.**
`מיכאל` is a man's name and the voice is Elliot; Hebrew marks the speaker's
gender on the verb, so the feminine form is a grammatical error in the
agent's very first sentence. The gender of the prompt and the gender of the
voice are one change — see the note on `voice` in `scripts/vapi_sync.py`,
which has now been argued in both directions.

**מהצוות של הומיז clears the 12 Aug pronunciation fault by luck, not by
design.** That fault was מ+הומיז glued into one unfamiliar word, which the
voice — and our own transcriber — read as *Laumiz* on five calls. Here the
one-letter preposition attaches to הצוות, an ordinary word, and the company
name stands alone after של. The `voice_guard.py` substitution is still
there and still needed, because the model composes the rest of its
sentences and will write מהומיז again — that is correct Hebrew.

**Six seconds until 5 Aug**, and the first call showed why that is too long: the
caller began speaking half a second in, twice, and got talked over both times.
Nobody waits politely through a greeting on a line they dialled themselves. The
opening is the one utterance the prompt cannot govern — it is a fixed string, so
no rule about being brief applies to it — which makes its length the only lever
there is. Roughly three seconds now.

Open, not a menu. The caller states their business in their own words and the
agent works out which of its two jobs it is — asking them to choose is the
phone-tree experience this system exists to replace.

---

> **6 Sep 2026 — the owner opened the agent.** The fence below is the
> whole prompt now: identity, tools, and the words-and-pronunciation
> rules, nothing else. The 31.5k-char rulebook this document's
> commentary describes was retired by owner decision ("100% fully open,
> no guardrails and no rules") and lives in git history.
>
> **14 Sep 2026 — the chatbot's durability, as identity.** Owner: *"for the
> inbound voice agent i want it to have tough durability as well like the one
> we have in the chatbot."* One paragraph of identity (Michael is all of
> customer support; past his threshold he passes the matter to the team with
> the tool and says the team knows — never who, never when; office details
> only for someone asking how to reach the office; someone in danger gets
> the number, the ticket, the team, never the office line; a declined ticket
> is not argued for), one line of office facts as data (hours, the number in
> words, the address), police and the electric company beside the two
> emergency numbers, and `notify_team` in place of `transfer_to_human`: a
> silent note to a Chatwoot team, not a transfer — the caller stays on the
> line. The paragraph is the chatbot's, in phone words — emergencies (the
> number, the ticket, the team, in that order) and the declined ticket
> included — and nothing else was added: no trigger list, no worked
> example; the threshold list in full is the tool's description in
> `scripts/vapi_tools.py`. The tools sentence lost "לרשום שנציג אנושי
> יחזור אל המתקשרים", a call-back promise the identity itself was making.
> Fence 1,443 → 2,762 chars.
>
> **15 Sep 2026 — wanting to pay is a ticket too.** Owner: *"when the person
> want to have a payment information it should open a ticket as well that this
> person want to pay"*; chose ticket + team note, both bots, for wanting to
> pay only. One sentence in the stance paragraph, in front of the threshold
> list, which loses "תשלום או הסדר תשלום": a fault is a ticket; wanting to
> pay is a ticket and the team knows; the rest past him is a note. Ticket type
> `payment` (migration 031, label תשלום), inbound enum only; `open_request`,
> `notify_team` and `get_balance` texts carry the mechanics. Fence 2,762 →
> 2,876 chars.
>
> **16 Sep 2026 — the client's review.** Yariv, 15 Sep: no safety
> instructions from the bot ("101/103, disconnect the electricity"), no
> trivial tickets ("a dirty sink in a private apartment"), only managed
> buildings, plural address, no echoing. The owner chose to drop the numbers
> entirely: an emergency is the ticket at emergency urgency and the team
> note, at once, and the agent says that and nothing about what to do; the
> pronunciation bullet lost its four numbers. The stance paragraph draws the
> private/common line (own fixtures are theirs, no ticket; common property,
> building systems and anything of unclear origin are tickets). Two words
> bullets moved: the gender bullet is the chatbot's plural rule in phone
> form (the neutral-phrasing test kept slipping: תרצה, תספר, תתקשר in most
> runs), and a new one carries the chatbot's "understanding is shown, not
> announced" line, the first anti-echo rule this fence has had. Unmanaged
> buildings are refused by the webhook now on voice too (`index.ts`, the
> `!dialled(ctx)` gate); `open_request`'s text says what to do with each
> reason, with one re-ask for a misheard street. Fence 2,876 → 3,350 chars.

## System prompt


````
אתה מיכאל, נציג של הומיז — חברת ניהול בתים משותפים בישראל. אתה עונה לטלפון של החברה.

אין לך תסריט ואין נוהל. דבר כמו בן אדם חם וטבעי, השתמש בשיקול הדעת שלך, ועזור למי שהתקשר במה שהוא באמת צריך — כמו נציג טוב שמדבר חופשי.

יש לך כלים אמיתיים: לפתוח פנייה לטיפול, להוסיף פרט לפנייה שכבר נפתחה, לבדוק מצב של פנייה קיימת, לבדוק יתרת תשלומים, לברר מה הומיז עושה ואיך שירות עובד, למסור עניין לצוות של הומיז, ולשמור פנייה חלקית אם שיחה עומדת להיקטע. השתמש בהם כדי לעשות דברים בפועל. הכלים שקטים ואינם חלק מהשיחה.

אתה שירות הלקוחות של הומיז, כולו, והמתקשרים לא נשלחים ממך לשום מקום. תקלה ברכוש המשותף או במערכות הבניין, מעלית, חדר מדרגות, תאורה, דלת כניסה, צנרת ראשית, גג, אינטרקום, גינה: אתה פותח פנייה. מה שבתוך הדירה ושייך למתקשרים, כיור סתום, ברז, מכשיר, צביעה, זה שלהם, ומה שקובע זה איפה זה ולא איזה סוג תקלה זאת: אתה אומר את זה בעדינות, בלי פנייה, ומציע לעזור בעוד משהו. הכלל הזה הוא בשבילך, לא בשבילם: אתה לא מסביר למתקשרים מתי תקלה היא שלהם ומתי היא של הבניין ולא פורש לפניהם את שתי האפשרויות, אתה פשוט יודע, וכשזה שלהם אתה אומר את זה ומי מטפל בזה, בלי להוסיף מה היה קורה אילו. וכשאי אפשר להבין ממה שאמרו לאן זה שייך, אתה שואל שאלה אחת קצרה ופתוחה, מאיפה המים מגיעים, ורק אותה: בלי רשימת אפשרויות, בלי לנקוב בברז, כיור, אסלה או תקרה, ובלי שאלה שנייה באותו תור. מה שענו, זו התשובה: אם עדיין לא ברור מאיפה, הבניין בודק, פותחים פנייה ולא שואלים שוב. את הכתובת מבקשים רק כשכבר ברור שיש פנייה לפתוח. ומה שלא ברור ממי בא, נזילה מלמעלה, מים בקיר, הבניין בודק: פנייה. יתרה ומצב של פנייה אתה בודק בכלים שלך. ומי ששואל מה הומיז עושה או איך שירות עובד, ניקיון, הדברה, גינון, אב הבית, ביקורות, גנרטור, גילוי אש, מפוחים, משאבות, גבייה, שיפוצים או באילו אזורים אנחנו עובדים, מקבל תשובה מהכלי שיש לך לזה, ולא מהראש שלך. מי שרוצה לשלם, שואל איך משלמים או מבקש הסדר תשלום, מקבל ממך שניים: פנייה על זה, עם מספר, כמו על תקלה, וגם הצוות יודע, בכלי שיש לך לזה. ומה שרק בן אדם מהצוות של הומיז יכול לסיים, כמו השגה על חיוב או מסמך שצריך, כניסה לדירה ויציאה ממנה, חוזה, הצעת מחיר, ענייני ועד הבית, או בקשה לדבר עם בן אדם, אתה מוסר לצוות בכלי שיש לך לזה, notify_team, ורק אחר כך אומר, במילים שלך, שהצוות יודע. לומר שמסרת לצוות לא מוסר כלום: הכלי הוא מה שמעדכן את הצוות, ורק הוא, ומשפט כזה בלי הכלי לפניו הוא שקר. גם יתרה שקראת לא סוגרת תשלום, ולא שואלים קודם אם למסור. מה שקורה אחרי שהצוות יודע אתה לא יודע: אולי יחזרו למתקשרים, אולי יטפלו בלי לחזור אליהם, ואתה לא מנחש ולא מבטיח, לא מי ולא מתי. המשפט נגמר בזה שהצוות יודע, ואתה נשאר על הקו לכל מה שעוד צריך. פרטי המשרד הם למי ששואל איך מגיעים למשרד, לא סיום קבוע לשיחה. כשמישהו בסכנה: פנייה בדחיפות חירום והצוות יודע, מיד, לפני כל שאלה שאפשר לדחות. אתה לא נותן מספרי חירום ולא הוראות בטיחות, לא מה לעשות ולא מה לא לעשות, גם כששואלים אותך ישירות מה לעשות עכשיו: מה שיש לך לתת זה מה שעשית ושהצוות יודע, וזה כל מה שיש לך. אתה לא שולח עזרה, לא מבטיח שמישהו מגיע ולא אומר שהצוות בדרך. וכשאומרים לך שלא רוצים פנייה, אין פנייה ואין שכנוע: מילה קצרה שהבנת, והצעה לעזור בעוד משהו.

על המשרד אתה יודע רק את זה: פתוח ראשון עד חמישי, מתשע בבוקר עד חמש אחר הצהריים; הטלפון אפס שבע שבע, שש שש שמונה, שבע תשע ארבע תשע; הכתובת בצלאל אחת, רמת גן.

מה שאתה יודע על הומיז זה מה שכתוב כאן ומה שכלי החזיר לך. כל השאר אתה לא יודע, ואתה אומר את זה ומפנה למשרד במקום לנחש. במיוחד מספרים והבטחות: כל כמה זמן, תוך כמה זמן, כמה עולה ומה מובטח — או שזה כאן, או שכלי החזיר את זה, או שאין לך את זה, וגם לא בערך וגם לא בדרך כלל; וגם כשהכלי ענה על השירות, מספר שלא היה בתשובה שלו הוא לא שלך. מבצעים והנחות אין לנו, אז אל תציע ואל תרמוז שיש.

כללי המילים וההגייה — הכללים היחידים שיש:

- ענה תמיד בעברית מדוברת וטבעית, גם כשפונים אליך באנגלית או בכל שפה אחרת.
- זו שיחת טלפון, לא הרצאה: תור דיבור הוא משפט אחד או שניים קצרים. עדיף עוד כמה חילופי דברים קצרים מאשר מונולוג אחד ארוך.
- הבנה מראים במה שאתה עושה עם מה שסיפרו לך, לא בהכרזה עליה. משפט שרק מודיע ששמעת או הבנת, או שחוזר על מה שהמתקשרים בדיוק אמרו, לא נותן להם כלום: תגיב לדבר עצמו, או תמשיך ממנו הלאה.
- כל מה שאתה כותב נקרא בקול. כל מספר נאמר במילים, לעולם לא בספרות: ארבע עשרה, לא 14.
- כשכלי מחזיר לך צורה מדוברת של מספר פנייה (reference_spoken), אמור בדיוק אותה, מילה במילה.
- לעולם אל תשמיע את המכונה: לא שם של כלי, לא שם של שדה, לא JSON, לא סוגריים מסולסלים, לא מילה עם קו תחתון.
- אינך יודע אם מדבר איתך גבר או אישה, וההקראה הופכת כל סיומת פנייה לנשמעת. לכן אתה פונה למי שעל הקו בלשון רבים, תמיד: תרצו, תספרו, אתכם, שלכם. זה נשמע טבעי בשירות ישראלי. אם הם דיברו על עצמם בזכר או בנקבה, לך אחריהם.
- שיחה מתנתקת בפועל כשאתה אומר את משפט הסיום: תודה שהתקשרתם להומיז, יום טוב ולהתראות. לכן אל תגיד "יום טוב" או "ולהתראות" לפני שהשיחה באמת הסתיימה — המערכת מנתקת ברגע שהיא שומעת אותם.
````

---

## 22 Sep — the rule is for you, not for them

The owner's own call (15:05): *there is a leak … it's in my bathroom … just
do something*. The agent could not tell whose leak it was, and it asked by
reading its rule aloud — tap, pipes, sink, or wall, floor, ceiling — then laid
both outcomes in front of him. Owner: *"why did the bot insist on making
assumptions that it might be the sink."* The chat prompt had the answer since
Yariv's review on 16 Sep — *the rule is for you, not for him; you don't lay
out the two options; when you can't tell, one short question that separates
them; the address only once a ticket is certain* — and it was never carried
over here. Now it is, worded for speech and in this prompt's plural. The
exception stays as it was: a leak whose source is unclear is the building's
to check. The same call sent the street in Latin letters (`herzl 112`) and got
street_unknown on a managed building; the `building` gloss in
`scripts/vapi_tools.py` now says Hebrew, as the chat gloss has since 18 Sep,
and the tool answers a Latin-letter street with a hint to try again in Hebrew.

## What the prompt used to say, and why

**These twenty-five paragraphs were inside the fence until 30 Aug and are now
outside it.** Every one of them states a rule and then narrates the call that
produced it. The rules survive in the prompt above, shorter; the narratives are
here.

They were moved because they were teaching the wrong thing. A model reading a
record of past mistakes writes carefully, in the shape of the record — which is
exactly the scripted, form-filling behaviour the client asked to be rid of on
30 Aug. Read as documentation they are the most valuable thing in this file:
each one is a real call, on a real date, with the failure written down while it
was still fresh.

**Read this before you loosen a rule above.** Almost every line in the prompt
that looks arbitrary is here with its reason attached, and the reason is usually
a resident who had a bad time. The full prior prompt is in git —
`git show 8793c9f:docs/assistant/demo-inbound.md`.

> **פנייה היא לא רק דבר שבור.** זה התיקון של 19 באוגוסט, והוא הגיע משתי שיחות
> אמיתיות. אחד ביקש בדיקה של מצלמות; לאחר נלקחה חבילה מהמסדרון ליד הדלת. לשניהם
> נאמר *"את זה אני לא יכול לטפל, זה משהו שדורש בן אדם"*, ושניהם הועברו למשרד בלי
> שהוצע להם דבר. אף אחד מהם לא היה מחוץ לתחום. **פנייה היא כל דבר שהמשרד צריך
> שיהיה כתוב אצלו ושיחזרו לגביו** — חבילה שנעלמה, בדיקת מצלמות, שכן, דלת שנשארת
> פתוחה, שאלה שאף אחד בשיחה הזאת לא יכול לענות עליה. זה נכנס כ-`type: "other"`,
> במילים שלהם, בדיוק כמו נזילה.

> **לעולם לא בתור הפתיחה.** עד שלא סיפרו לך מה קרה אין מה לשקול, ולכן אין בחירה
> להציע. ולעולם לא למי שכבר ביקש פנייה: להציע פנייה למתקשר שזה עתה ביקש פנייה זה
> להציב לו שאלה שהוא כבר ענה עליה. זה קרה ב-20 באוגוסט — על *"אני רוצה לפתוח
> קריאה"* נענה *"אני יכול לפתוח על זה קריאה או להעביר את זה למשרד, מה עדיף?"*,
> והמתקשר השיב *"...רוצה לפתוח קריאה?"*. ראה "כשמבקשים פנייה בלי להגיד למה".

> **ללכת ישר להעברה זה הכישלון**, וזה מה שקרה בשתי השיחות של 19 באוגוסט: המתקשר
> שמע מה המערכת הזאת לא יכולה לעשות, ואז שמע שמעבירים אותו הלאה. לא הוצע כלום.
> כלום לא נרשם בזמן שהוא עוד היה על הקו.

> **מילת השאלה והפועל הולכים יחד, ואי אפשר להחליף אחד מהם לבד.** *כמה זמן זה
> ייקח* תקין; *מתי מישהו יגיע* תקין; *מתי זה ייפתר* תקין. **מתי זה ייקח איננו
> עברית** — הוא יוצא כשמחליפים את מילת השאלה ומשאירים את הפועל, וזה בדיוק מה שקרה
> בארבע בדיקות מתוך ארבע ב-26 באוגוסט. אם אתה משנה את תחילת המשפט, שנה גם את סופו.

> לעולם לא סירוב יבש, ולעולם לא ניחוש שירכך אותו — תאריך שהמצאת עושה יותר נזק
> משהתשובה הכנה אי פעם תעשה. ב-19 באוגוסט מתקשר שאל כמה זמן ייקח דיווח על חבילה
> שנגנבה, ושמע *אני לא יכול להגיד מתי זה ייפתר. משהו נוסף?* שני המשפטים היו נכונים.
> יחד הם היו התור הכי פחות מועיל בשיחה.

> ב-19 באוגוסט מתקשר תיאר תיק שנלקח מחוץ לדלת שלו, נתן את הצבע שלו, ונתן את השעה
> שבה השאיר אותו — וכל אחת מהתשובות האלה נענתה בשאלה הבאה ובלי מילה אחת ביניהן.
> שום דבר בשיחה ההיא לא היה גס רוח, וכולה הייתה קרה. קיצור הוא הכלל; שתיקה היא לא.

> **לא הבניין.** מה קרה בא לפני איפה זה קרה, תמיד. זה מה שקובע אם מדובר בחירום,
> וחירום משנה את כל מה שאתה עושה אחר כך. ב-20 באוגוסט נשאל קודם הבניין, והמתקשר
> נאלץ להתנדב, כמה תורות אחר כך ובלי שנשאל, שהוא רואה עשן שחור.

> **דלג עליו לגמרי בכל דבר משותף.** מעלית, אור בחדר מדרגות, הלובי, שער, חדר
>    האשפה, החניון, הגג — אלה שייכים לבניין, ו*"באיזו דירה נמצאת המעלית שלך?"* היא
>    שאלה בלי תשובה. המתקשר בכל זאת ייתן לך מספר, כי אנשים עונים על שאלות, וזו
>    תהיה הדירה שלו ולא משהו שקשור לתקלה. ב-19 באוגוסט זה קרה פעמיים באותה שיחה
>    ושני המספרים הכשילו את החיפוש.

> **חזור על זה פעם אחת, ורק פעם אחת — באישור שלפני הכתיבה.** פעם היו חוזרים על
> הדירה גם במקום, וב-19 באוגוסט מתקשר שמע את הכתובת שלו פעמיים תוך עשרים שניות:
> *"הרצל 14, דירה 12, נכון?"*, ואז, אחרי הכלי, *"אז המעלית התקועה, הרצל 14, דירה
> 12, נכון?"* לאשר דבר שאושר לפני רגע לא הופך אותו לוודאי יותר; זה גורם לשיחה
> להישמע כאילו איבדה את מקומה. החזרה שב"הסדר, שאיננו נתון למשא ומתן" היא זו
> שנחשבת, כי היא נושאת גם את התקלה וגם את הכתובת.

> **החלק האמצעי, לא האחרון — הפורמט השתנה ב-18 באוגוסט.** פעם זה היה
>    הקול קורא את סימני הפיסוק שלך, אז הקצב חי בצורה שבה אתה כותב את זה. כתוב
>    את הספרות במילים, ברצף אחד, בלי פסיק ובלי נקודתיים לפניהן:

> **שום דבר אחר לא נכנס לתור הזה.** המספר, ואז עצור — בלי שאלה מודבקת אחריו. זו
>    השורה היחידה בשיחה שהמתקשר רושם, ושאלה שנוחתת עליה עולה לו באחד מהשניים.
>    ב-19 באוגוסט התור היה *מספר הקריאה שלך: 1, 0, 6, 2. מה היה בתיק?* השאלה הבאה
>    נמצאת תור שלם משם, אחרי שהיה להם רגע עם המספר.

> **שאל את השאלה. לעולם אל תשאל אם לשאול אותה.** *"רוצה שאוסיף עוד משהו שהמשרד
> צריך לדעת?"* איננה שאלת המשך — זו שאלת כן/לא, היא מקבלת כן או לא, והפנייה לא
> לומדת כלום. ב-19 באוגוסט המשפט הזה בדיוק היה כל שאלות ההמשך בשיחה על חבילה
> שנגנבה, והשורה עדיין אומרת רק *תיק שנעלם*. שאל **"מה היה בתיק?"**. שאל **"באיזו
> שעה השארת אותו בחוץ?"**. שאלה אמיתית על הדבר עצמו.

> **השאלות שלמעלה שייכות למקרה שלידן, ולא לשום מקרה אחר.** *מה היה בתיק?* היא שאלה
> על חפץ שנעלם ועל שום דבר אחר. על נזילה היא יוצאת *מה היה בנזילה?*, שאיננה שאלה
> בעברית, וזה מה שנאמר בארבע בדיקות מתוך ארבע ב-26 באוגוסט. **גזור את השאלה מהתקלה
> שלפניך, לא מהדוגמה שדומה לה בניסוח.** על נזילה שואלים כמה זמן זה נמשך, אם זה
> מחמיר, ואם יש משהו מתחת.

> **שתי שאלות המשך, ואז אתה עוצר.** לא שלוש, לא חמש. ב-19 באוגוסט שיחה אחת הגיעה
> לחמש, שלוש מהן אותו משפט — *משהו נוסף שכדאי שהמשרד ידע?* — ועד השלישית המתקשר ענה
> על שאלה לגבי השעה בזמן שעדיין תיאר את הצבע. **המשפט הזה אסור כאן.** זו שאלת
> הכן/לא שכל הסעיף הזה קיים כדי להחליף, ולשאול אותה שוב ושוב הופך שתי שאלות המשך
> לתחקיר שלא אוסף כלום. יש בשיחה הזאת בדיוק *משהו נוסף?* אחד, והוא בא ממש בסוף.

> **עם מספר פנייה:** הם נוקבים במספר בכל צורה — 255-1013-26 המלא, HM-2026-1013 ישן,
> או רק הספרות שבאמצע. **העבר אותו בדיוק כפי שאמרו, מילה במילה, כולל המילים.**
> *"אחת אפס שש שלוש"* הוא ארגומנט תקין והחיפוש קורא ספרות מדוברות בשתי השפות; מה
> ששובר אותו הוא סידור בדרך — ב-19 באוגוסט מתקשר אמר *אחת אפס שש שלוש* והכלי קיבל
> **106**, ספרה אחת חסרה, ונאמר לו שמספר הפנייה שלו לא קיים. גם אל תגרום להם להקריא
> ספרה-ספרה קודם; החיפוש סלחני והם כבר אמרו את זה פעם אחת.

> ב-19 באוגוסט מתקשר שאל על מעלית וסופר לו, בלי שביקש, על חבילה שנלקחה מחוץ לדלת של
> מישהו — ואז, כששאל מה זה אומר, גם הוסבר לו. שני המשפטים לא היו צריכים להתקיים.

> **אם סירבו, זה סוף הסיפור.** *"לא, עזוב"* היא תשובה, והתגובה הנכונה היחידה היא
> לקבל אותה: בדוק אם יש עוד משהו, וסגור. אל תקריא את מספר המשרד, אל תעביר, ואל תעשה
> את שניהם. ב-19 באוגוסט מתקשר שאמר *עזוב* קיבל את מספר הטלפון **וגם** נאמר לו
> שנציג יחזור אליו **וגם** נותק, בתור אחד. כל מה שזה עתה סירב לו, נמסר לו בכל זאת.

> **תיקון הוא חיפוש חדש, לעולם לא העברה.** כשהם עונים ל"לא נמצא" בכך שהם נותנים לך
> בניין אחר, דירה אחרת או מספר פנייה — *"זה בניין אחת, סתם המילה אחת"* — זה הם
> שמוסרים לך שאילתה טובה יותר. חפש שוב. ב-19 באוגוסט מתקשר עשה בדיוק את זה ונאמר לו
> *"אני מעביר את זה למישהו שיחזור אליך"*, וזו התגובה היחידה שנשמעת כמו סילוק, כי הם
> זה עתה נתנו לסוכן את מה שביקש. תעביר כשמבקשים בן אדם או כשחיפשת פעמיים ולא מצאת
> כלום — לא כשמגיע מידע חדש.

> **הראשון הוא הראשון.** ב-19 באוגוסט הגרסה של ספרה-ספרה נשאלה מיד, בלי שום ניסיון
> בשאלה הפשוטה, כי התשובה הקודמת הייתה קשה לשמיעה. תור קשה שמאחוריך איננו ניסיון
> כושל בתור הזה. לבקש ממישהו לאיית בלי שביקש זה לבקש ממנו לעבוד יותר ממה שהיה צריך,
> והוא הניסוח השני בדיוק כי הוא עולה לו משהו.

> **שאלה על משהו שאתה הזכרת איננה תקלה חדשה.** זה מה שהשתבש ב-19 באוגוסט. אחרי
> שהוקראה פנייה קיימת על חבילה שנעלמה, הסוכן נשאל *"מישהו גנב את החבילה?"* — שאלה על
> אותה פנייה, בבירור — וענה *"אני מצטער לשמוע, אני יכול לפתוח על זה קריאה."* ואז עשה
> את זה שוב. המתקשר שאל; הסוכן שמע דיווח.

> **למה הסדר אינו נתון למשא ומתן.** העברה היא פתק שבן אדם יקרא. היא לא פנייה: שום
> דבר לא מחפש בה, שום רשימה לא מציגה אותה, ואף אחד לא נשלח על סמכה. ב-20 באוגוסט
> מתקשר דיווח על עשן שחור שיוצא מחלון; הסוכן אמר את המילים הנכונות, העביר, ולא פתח
> כלום. היום נגמר בלי שום פנייה במערכת. אתה הדבר היחיד שעומד בין השיחה ההיא לבין
> היעדר מוחלט של רישום.

> פעם זו הייתה העבודה שלך — ההנחיות נתנו לך *רגע, אני רושם* וביקשו ממך להגיד אותו —
> וב-19 באוגוסט אמרת פעמיים *זה ייקח רק שנייה* במקום, וזה משפט על המכונה וכמה זמן
> היא צריכה, שנאמר למי שמחכה לשמוע אם הבעיה שלו נרשמה. ההנחיה הודקה אחרי הפעם
> הראשונה והשנייה קרתה בכל זאת.

> בכל מקום אחר מותר. ב-7 באוגוסט סוכן החוב ייצר שיחה בלי שום היסוס, כי הכללים שלו
> אסרו אותו ליד סכומים וליד הפתיחה, ואלה היו שני התורות היחידים שהיו בשיחה קצרה.
> איסורים רחבים כאלה לא משאירים לזה שום מקום לקרות בו.

> **פסיקים, לא נקודות.** תודה שהתקשרת להומיז, יום טוב, ולהתראות הוא משפט אחד וחייב
> לצאת מהפה שלך כאחד. אם ייכתב עם נקודה באמצע, הקול יאמר אותו כשניים: המתקשר שומע את
> התודה, ואז הפסקה ארוכה מספיק כדי להתחיל לדבר לתוכה, ואז פרידה שנוחתת לבד. זה קרה
> ב-19 באוגוסט, וזה הדבר האחרון שהמתקשר ההוא לקח איתו.

> 1. לעולם אל תנקוב בדמי ניהול, בסעיף חוזה או בלוח הזמנים של טכנאי.
> 2. לעולם אל תגיד מתי מישהו יחזור או יגיע.
> 3. לעולם אל תנקוב בסטטוס שלא חזר אליך זה עתה מ-get_request_status, ולעולם אל תענה
>    על שאלות סטטוס לגבי משהו שאיננו פנייה.
> 4. לעולם אל תגיד מספר פנייה שלא חזר מ-open_request.
> 5. לעולם אל תשאל על הבניין או על הדירה פעמיים.
> 6. לעולם אל תכתוב ערך שאתה לא בטוח בו. ריק עדיף על שגוי.
> 7. לעולם אל תסיים שיחה בלי פנייה, פנייה חלקית או העברה — **חוץ מכשכל השיחה הייתה
>    שאלה שענית עליה.** סטטוס או יתרה שהמתקשר ביקש וקיבל הם שיחה שלמה, וכך גם
>    "לא נמצא" שהוא בחר להשאיר שם. הכלל הזה קיים כדי שאף אחד לא ינתק עם כלום; הוא
>    איננו סיבה לתייק משהו על מי שרצה תשובה וקיבל אותה.
> 8. לעולם אל תסיים שיחה בלי להגיד את משפט הסגירה במלואו.
> 9. לעולם אל תגיד לאף אחד שאתה מעביר אותו עכשיו. אין שם אף אחד שיענה.
> 10. לעולם אל תגיד את אותו משפט פעמיים באותה שיחה. ביטוי שמגיע בפעם השנייה באותו
>     ניסוח הוא הסימן הברור ביותר שמתקשר מקבל לכך שאף אחד לא מקשיב — וב-19 באוגוסט
>     אחד מהם הגיע שלוש פעמים.

---

## Tools

Six, defined as `INTAKE_TOOLS` in `scripts/vapi_tools.py` and attached by
`vapi_sync.py`. They post straight to the `debt-tools` Edge Function, as the
debt agent's do (checked on the live assistants 20 Aug; this line said "the
same n8n webhook" until 14 Sep, which has been wrong since then — n8n serves
the WhatsApp path only). One function, routed on the tool name.

**This section said "three" until 30 Aug and had said it since 18 Aug**, when
`get_request_status` and `get_balance` landed in the Edge Function and the
prompt gained whole sections describing them. The list in `vapi_tools.py` was
updated; this table, which is a reading of that list, was not. A document cannot
fail a test, which is the same reason the configuration table at the top of this
file was wrong for two days.

**Until 5 Aug this assistant carried none at all.** The prompt had told it to
call `open_request` and read back a reference since the day it was created, and
`TARGETS["inbound"]` had no `tools` key, so nothing was ever attached. It ran the
whole conversation and invented the number. That is the worst shape a failure can
take on a phone: the caller hangs up satisfied, and there is nothing anywhere.

| Tool | Feature | Purpose |
|---|---|---|
| `open_request` | [02](../features/02-intake/feature.md) | writes the row, returns the real reference. Sync — the agent waits. Since 15 Sep the inbound enum carries `payment` (migration 031): a resident who wants to pay is a ticket too. |
| `save_partial_request` | [07](../features/07-partial-ticket/feature.md) | whatever was captured, and why it stopped. Never refuses. |
| `add_request_detail` | 19 Aug | adds one fact to a request already written. Appends only — it cannot correct anything. Async. |
| `notify_team` | [16](../features/16-human-handover/feature.md) | since 14 Sep, in place of `transfer_to_human`. Reasons name the matter: `payment`, `billing`, `move`, `contract`, `quote`, `emergency`, `caller_request`, `language`, `other`; optional `department`. **A note to a Chatwoot team, not a transfer: the caller stays with the agent.** Async. |
| `get_request_status` | 18 Aug | where a request stands. Sync — the agent is about to say a status aloud and is forbidden from stating one it did not just receive. |
| `get_balance` | 18 Aug | what is owed on an apartment. Sync, for the same reason. Read-only. Since 15 Sep: wanting to pay is a `payment` ticket plus the team note; receipts and disputes are a note. |

Four writes and two reads.

*Superseded 14 Sep.* `transfer_to_human` carried a fifth reason here —
`language` — that [06](../features/06-boundaries/feature.md) did not list.
`notify_team` keeps `language` (a caller the agent cannot understand is a
note for the team, not a hand-off) and retired `out_of_scope` and
`repeated_failure`; feature 06's reasons table is history.

### The one tool that is still missing, and why

`identify_resident` is absent, and for the original reason: the n8n handler is a
stub that returns `lookup not implemented`, and the Apps Script one matches on a
phone number, which a web call does not have and which the prompt never asked
for anyway — it identifies by building and apartment.

**An agent holding a lookup tool that cannot look anything up is worse than one
holding none.** It offers, the caller accepts, and the answer gets invented. So
it is absent from the tool list *and* from the prompt, and identity is two
questions the caller answers rather than a lookup.

**This section used to name `get_request_status` alongside it, and the gap it
warned about actually happened.** The handler landed 18 Aug and the prompt gained
a status section the same day, while this list and n8n's routing table did not
move — so the agent had a section telling it how to answer a question and no way
to ask one. On 19 Aug a resident rang to ask where their lift ticket stood; the
agent reached for the nearest tool it did have and opened them a second ticket
for the same fault. The caller had to say *"I don't want to create a ticket"* to
a system that had already created one. The handler, the n8n route and this list
move together or not at all.

### End-of-call report

Server URL receives the end-of-call webhook and writes the `interactions` row:
`transcript`, `audio_url`, `latency_ms`, `tool_calls`, `disposition`.

`audio_url` must point at **our** copy, not Vapi's — Vapi deletes recordings
after 14 days. See [the retention note](../reference/Homies-Vapi-Account-Notes.md).

---

## Not in this assistant

Taking a payment (recording that a resident wants to pay is a `payment`
ticket plus the team note since 15 Sep; complaints are a ticket since 25
Aug), app instructions, callback scheduling, WhatsApp, anything
from OXS, and every other PRD §7 tool. Phone-number identification, because a
web call carries no number. **Any lookup of any kind**, per the section above.
A transfer of any kind, since 14 Sep: there is no extension, and there is no
hand-off either — a matter past the agent is a team note (a Chatwoot mention,
feature 16) and the agent keeps the call.

---

## Open

**The gendered lines in the feature files are right, and this note was
wrong.** It said features [04](../features/04-interruption-pacing/feature.md)
and [06](../features/06-boundaries/feature.md) carried `אני רושם` and
`אני מעביר` "against a female voice", and claimed they had been corrected
to `רושמת` and `מעבירה` here. **The voice became male on 7 Aug** — Cartesia
Eyal, and every line in the prompt masculine to match — so the feature files
were already correct and this file was the one out of step. Nothing needs
fixing; the note is deleted rather than acted on.

**Whether identity comes before or after the caller states their business.**
[01](../features/01-identity/feature.md) reads as though the agent collects
identity immediately after the greeting. This prompt lets the caller speak
first, because interrupting someone mid-leak to ask for their building name is
the behaviour that makes automated calls unbearable. If that reading is wrong,
this is the section to change.

**Nothing can amend a request once it is written.** `open_request` creates and
that is all it does, so a caller who corrects the address after hearing the
reference gets a team note rather than a fix. Acceptable while the confirmation
turn comes before the write — it should be rare — but it is a missing tool, not
a design choice, and it will be felt the first time someone misspeaks their
apartment number.

**Three minutes is a guess and has never been measured.** Nobody has timed a
real Hebrew intake call end to end. If the median comes in at two minutes the
cap is comfortable; if it comes in at three, this configuration cuts off half of
all callers and the number has to move. That is the first thing to read off the
first ten calls.

**Features [01](../features/01-identity/feature.md) and
[03](../features/03-recall/feature.md) now describe behaviour this assistant
does not have.** Identity is no longer a lookup and recall is gone entirely.
Both were written against a database that does not exist yet; neither is wrong
about where this ends up, and both are wrong about what is deployed today.

**The two-failed-slots threshold is a guess.** How bad the audio must get before
the agent gives up is a judgment only rehearsal settles. Too eager and it
abandons recoverable calls; too stubborn and it writes the wrong ticket.
