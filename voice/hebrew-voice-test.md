# Judging a cloned voice on Hebrew — nine lines, in order

Paste these into the provider's playground once the clone exists, before the
voice goes near an assistant and long before it goes near a resident.

**These are not sample sentences. They are the agent's actual fixed lines**,
lifted from `docs/features/10-debt-followup/prompt.md` with the template
variables filled in. A voice that handles invented test text and then fumbles
`ולהתראות` has taught you nothing, because `ולהתראות` is the line the call
cannot end without.

The order is deliberate: each line is the shortest one that can break a
different thing. Stop at the first failure — they compound, and diagnosing the
ninth is pointless if the first was already wrong.

---

### 1 — Gutturals, and the whole point of the exercise

```
שלום, מדבר מיכאל מהומיז, חברת הניהול של הבניין. אני מדבר עם דוד?
```

**Listen for:** the ח in חברת and the ה in הומיז. This is where a voice cloned
by a model with no Hebrew in it gives itself away — ח becomes an English *h* or
disappears, and the word turns into "everat". Also the stress: Hebrew stresses
the **last** syllable, so it is mi-kha-**EL**, not mi-**KHA**-el. An
English-trained voice reaches for the penultimate and the name comes out
American.

If this line is wrong, nothing below matters. Try another provider.

### 2 — Does it still sound like the person?

```
אני עוזר דיגיטלי של הומיז.
```

**Listen for:** whether that is recognisably the voice from the recording. A
clone stretched to a language it was not trained on often stays intelligible
while losing the timbre that made it worth cloning. If it is fluent Hebrew in a
stranger's voice, the clone has failed at the only job it had.

### 3 — A number spoken as a number

```
מדובר בתשלום ועד בית של ארבע מאות וחמישים שקלים עבור חודש יולי.
```

**Listen for:** *one* number. On 4 Aug, 450 came out of a real call as
"ארבע מאות, חמישים" — two numbers side by side, with a falling ending on each,
as though the resident owed two separate sums. Also ועד בית, which is the term
the whole product is about, and שקלים, which must never come out as ש״ח.

### 4 — Digits inside Hebrew, and Latin characters mid-sentence

```
מספר הפנייה שלך HM-2026-9634.
```

**Listen for:** whether it reads the letters at all, and whether it switches
accent to do it. A reference number read in a sudden American accent mid-Hebrew
sentence is the single most artificial thing a caller can hear. Also whether the
digits arrive one at a time, which is what the prompt requires.

### 5 — The closing, which is load-bearing

```
מצוין, תודה רבה על הזמן. שיהיה יום טוב ולהתראות.
```

**Listen for:** the vav on ולהתראות. `endCallPhrases` matches this string, and
it is the **only** thing that ends a debt call — `endCallFunctionEnabled` is off
precisely so the model cannot hang up without saying it. If the voice elides the
vav into להתראות, the phrase stops matching and calls stop ending. This is the
one line where a pronunciation problem becomes a functional one.

### 6 — Speaking to a woman while being a man

```
בסדר, אני מבין. אפשר שנציג מהמשרד יחזור אלייך בנושא?
```

**Listen for:** אלייך, addressed to a woman, in the same breath as מבין, spoken
by a man. Both at once is the normal case and it is what the agent got wrong on
a real call — it said אני מבינה, feminising its own verb because the caller was
female. The prompt now has a rule for it; this checks the voice does not blur
the two endings into each other.

### 7 — A long sentence that must not fragment

```
סליחה על ההפרעה, אני לא יכול למסור פרטים למי שאינו בעל החשבון. אפשר לבקש שדוד יחזור אלינו?
```

**Listen for:** whether it stays one utterance. The chunk plan was withdrawn on
5 Aug after words went missing from the middle of fixed lines, so the voice
provider now receives longer spans than it used to. This is the longest fixed
line the agent has, and it is the one that would show the problem coming back.

### 8 — Handing over

```
רגע אחד, אני מעביר אותך לנציג מהצוות שלנו. נא להישאר על הקו.
```

**Listen for:** the ע in מעביר and the guttural cluster in רגע. Same failure
mode as line 1, but buried mid-sentence where it is easier to miss and easier
for a caller to mishear as a different word.

### 9 — The one nobody is there to interrupt

```
שלום, מדבר מיכאל מחברת הניהול הומיז לגבי בניין הרצל 14. יש נושא שנשמח להסדיר איתך, אפשר לחזור אלינו למספר 03-1234567. תודה ויום טוב.
```

**Listen for:** pace over a long uninterrupted stretch. This is the voicemail
message — the only time the agent speaks for more than two sentences with no
turn-taking to break it up. Clones tend to drift flat, fast or both once there
is nothing to respond to, and a voicemail that sounds like a robot is the one
artefact of this system a resident can replay.

---

## Then, and only then

A playground is not a phone call. Once these nine pass, the remaining risks are
ones only a real call reaches:

- **Latency.** Vapi's target here is under 800ms voice-to-voice and the current
  build measures worse than that. A cloned voice on a third-party provider adds
  a hop. Measure with `scripts/vapi_latency.py`, not by ear.
- **The output guard.** It lives in `voice.chunkPlan.formatPlan`, so it moves
  with the provider. `vapi_sync.py` carries it across automatically — confirm 27
  replacements are on the assistant after the switch, and never re-edit the
  voice in the dashboard, which deletes it.
- **The fallback firing silently.** If Cartesia fails, the call continues on
  Elliot. That is the correct behaviour and it means a broken clone can look
  like a working system. Check `voiceId` in the call record, and note that Vapi
  reports the *provider's* label rather than what was actually spoken — only
  listening settles it.
