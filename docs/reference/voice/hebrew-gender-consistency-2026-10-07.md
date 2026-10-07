# One gender line on the Hebrew voice agents: what breaks it, and the fix that does not depend on the model

7 Oct 2026. The owner: *"we need to look for a skill for voice agent to have a consistent line of gender identification in hebrew since we are stuck on that for a long time ... the intro is like genderizing the person he is talking to a female then the next line is masculine without even identifying the gender of the person talking on the other line."*

This is the research he asked for: what the pipeline does with gender today, what was measured, the options, and the one to ship. Nothing on the live agents was changed. Two things are ready for his word (the last section).

## In short

- **The inconsistency is not in the model's grammar. It is in the words Hebrew writes the same for both genders.** "To you" is לך for a man and a woman; said, it is *lekha* or *lakh*. The same for שלך (yours), איתך (with you), שלומך (how are you), and the past tense "you called" (התקשרת: *hitkasharta* / *hitkashart*). The voice has to pick one reading for every such word, and it picks per word.
- **The prompt's answer was to make the model write vowel points on those words. The model does not.** On the 5 Oct transcripts gpt-4.1 (incoming) pointed 27 of 88 such words, 30%; gpt-5.6-sol (debt) pointed 0 of 7. The rest reach the voice bare.
- **Bare, Cartesia sonic-3.5 reads לך as a man and שלומך as a woman** (measured today by machine; samples below for the ear). So a call that opens "איך אני יכול לעזור לְךָ" (pointed, male) and continues "מה שלומך?" (bare, read female) and then "תרצה" (male) is exactly the complaint.
- **The fix is a Cartesia pronunciation dictionary, not another prompt rule.** Cartesia applies a dictionary itself, to every whole-word match, after everything Vapi does, and it accepts a pointed Hebrew spelling as the "pronunciation". Tested today on our own account: it works on sonic-3.5, matches whole words only (הלך was left alone), matches before "?" and ",", and the pointed alias changed the reading. Vapi carries the dictionary id in the voice settings (`pronunciationDictId`).
- **The line:** masculine on every ambiguous word, by the dictionary, until the caller shows she is a woman; then the model's feminine verbs plus pointed feminine pronouns, with a known residue. On debt calls the gender is known from the name before the dial, so the call can carry the feminine dictionary instead.
- **What the skill documents already say is right and is not enough.** `hebrew-voice-gender-pronunciation-skill.md` (Aug) gives the full table of forms; the published "hebrew-nikud" agent skill says the same in general terms. Both are instructions to a model, and the measurement above is what instructions get.

## 1. Where gender lives today

Three places, none of them deterministic for the ambiguous words.

| Layer | Incoming agent | Debt agent |
|---|---|---|
| Opener (fixed text) | "היי, בוקר טוב! מדבר מיכאל מהומיז, איך אני יכול לעזור **לְךָ** היום?" (pointed, masculine; the owner's own example) | "בוקר טוב, {{first_name}}? מדבר מיכאל מהצוות של הומיז, מה נשמע?" (no address word) |
| Prompt rule | One person, masculine until she shows otherwise (אני צריכה, אני גרה), then feminine to the end. Every word that ends in the address suffix "is always written pointed", with examples (לְךָ / לָךְ, שלומְךָ / שלומֵךְ, התקשרתָּ / התקשרתְּ) | `{{gender_forms}}` from the dashboard: the forms for a man, a woman, or the masculine default when the name decides nothing (`first_name_gender`, 1,484 names) |
| Voice | Cartesia sonic-3.5, voice A. Nothing in Vapi's formatting touches vowel points; custom replacements run last | Same, voice ba765d50 |

What the voice is handed: the first message as written (the tool webhook of this morning's call carries `assistant.firstMessage` with its two vowel points intact), then the model's text through Vapi's 14 formatters and our replacements. Vapi's stored transcripts show none of this: the bot's lines in `artifact.messages` are normalised (vowel points gone, "מהומיז" already replaced by "מחברת הומיז", a word dropped here and there), so a transcript can never prove what the voice heard. Vapi exposes no provider logs for the voice request either.

## 2. What was measured today

### 2a. The model does not point the words

The raw model text of the 5 Oct test calls (the `.json` records beside the transcripts), ambiguous address words only:

| Call | Bare | Pointed | Feminine verbs | Masculine verbs |
|---|---|---|---|---|
| Batya (woman, revealed herself) | 14 | 5 (לָךְ ×3, שלומֵךְ...) | תספרי, תגידי... | 0 |
| Roni (a man; the model decided "woman" from the name) | 16 | 7 | many | 5, then feminine |
| Shiran (woman) | 16 | 2 | many | 0 |
| Assaf (man) | 15 | 13 (all לְךָ) | 0 | 4 |
| **gpt-4.1, incoming, total** | **61** | **27 (30%)** | | |
| **gpt-5.6-sol, debt, 5 calls** | **7** | **0** | | |

Two things follow. The rule "write them pointed" gets 30% from the model it was written for and 0% from the other. And the model's verbs are mostly consistent (it switches when the caller reveals herself and stays), so the mixing the owner hears comes from the 70% of pronouns that reach the voice bare. The Roni call is the one real model-side fault: it took a name used by both genders as a woman's, against the rule.

### 2b. Bare, the voice chooses per word

Nine short lines rendered with Cartesia sonic-3.5 on our own key (voice "Noam", a Hebrew library voice; the live voice A sits on the client's account and was not spent), then compared by machine: each bare rendering against the pointed masculine and the pointed feminine rendering of the same line, by distance between their spectrograms (the same line rendered twice scores about 3.0; two different readings score higher).

| Line | Bare reads closer to | Margin |
|---|---|---|
| איך אני יכול לעזור **לך** היום? | masculine (*lekha*) | clear (3.08 vs 3.77) |
| מה **שלומך** היום? | feminine (*shlomekh*) | narrow (3.45 vs 3.67) |
| תודה **שהתקשרת**, יום טוב. | masculine (*hitkasharta*) | narrow (2.90 vs 3.19) |

Pointed masculine and pointed feminine renderings of one line differ from each other (3.1 to 3.5), so the voice does read the vowel points: the 26 Aug finding on sonic-3, again on sonic-3.5. The machine comparison is a signal, not an ear; the samples are listed at the end for the owner to hear.

### 2c. A Cartesia dictionary fixes it at the voice

Cartesia's pronunciation dictionary is "a simple search and replace" on the text the voice receives: `{text, pronunciation}` pairs, and the pronunciation may be a sounds-like spelling or IPA. Tested on our own account, sonic-3.5, deleted afterwards:

| Test | Result |
|---|---|
| Does it apply on sonic-3.5 at all? A control entry שלומך → בננה ("banana") | Yes: the rendering of "מה שלומך היום?" with the dictionary sits next to a direct rendering of "מה בננה היום?" (4.06) and far from the bare one (6.16) |
| Whole word or substring? The same control, line "הוא הלך לעבודה" (the letters לך inside הלך) | Whole word: unchanged (3.41 against the plain rendering, 6.03 against a "הבננה" rendering) |
| Before punctuation? "מה שלומך?" and "תודה לך, יום טוב." | Matched both (3.22 and 2.94 against the banana renderings; 6.90 and 4.90 against plain) |
| The real entry, שלומך → שְׁלוֹמְךָ (pointed masculine) | The bare line now reads closest to the pointed masculine rendering (3.12; feminine 3.47; bare 3.50): the feminine-leaning word became masculine |
| The same on sonic-3 | Same direction (3.95 masculine against 5.02 feminine) |

Vapi's side: `CartesiaVoice.pronunciationDictId` exists in the API ("only available for sonic-3 model" in the field text, "sonic-3 or newer" in the docs; the live model is sonic-3.5, so the first real call confirms it), Vapi lists and creates Cartesia dictionaries through `/provider/cartesia/pronunciation-dictionary` (the attached key holds none today), and `assistantOverrides.voice` exists, which is what lets a debt call choose a dictionary per call.

### 2d. The alternatives, checked

| Option | What it is | Verdict |
|---|---|---|
| **Cartesia pronunciation dictionary** | bare word → pointed word, applied by Cartesia to every whole-word match | **Recommended.** Deterministic, provider-level, no chunking issue, Vapi carries the id. One write to the Cartesia account on Vapi's credential |
| Vapi regex replacements (our `voice_guard.py` mechanism) | bare word → pointed word as a `formatPlan` replacement with look-arounds | Works in principle and needs no new account object, but Vapi's regex replaces the first match per chunk only (each pattern would be listed twice), `\b` does not know Hebrew letters, and RE2 refused a look-ahead on 4 Oct. The fallback if the dictionary id is not honoured on sonic-3.5 |
| The prompt alone (today) | "write every address word pointed" | Measured: 30% and 0%. Keep the rule for the feminine case; stop relying on it for the default |
| Phrasing without the suffix | "איך אפשר לעזור?" instead of "לעזור לך", "מה הכתובת?" instead of "הכתובת שלך" | Right where it fits, and section 4 of the Aug skill has the list; it shrinks exposure, it cannot remove it (שלומך, התקשרת). The owner rejected the plural, not the impersonal |
| Automatic vowelling of the model's text (Dicta Nakdan or similar) | a server between the model and the voice adds the points | Vapi has no hook between model and voice except running our own model endpoint; adds latency to every turn. Not for this |
| Another voice provider | ElevenLabs (alias dictionaries, "selective nikud" works), Azure he-IL (rule-based, reads points) | Not needed: Cartesia reads the points. Noted for the day the voice changes |
| Telling the gender from the voice | pitch, or Deepgram | Not available in the pipeline, and the owner's rule does not need it: masculine until she shows otherwise |

## 3. The line, and the word list

**The line.**
1. Every ambiguous address word is said masculine, by the dictionary, whatever the model wrote. This covers the opener, the small talk ("מה שלומך"), and every "לך / שלך / איתך" of the call.
2. A name is never evidence of gender on an incoming call. The caller shows it in her own words (אני צריכה, אני גרה, מדברת); only then the model switches, and stays switched.
3. When switched, the model uses the feminine verbs (תוכלי, תרצי, תגידי) and writes the pronouns pointed feminine (לָךְ, שֶׁלָּךְ, אִתָּךְ, שְׁלוֹמֵךְ) or avoids the suffix. A pointed feminine word is a different string, so the masculine dictionary leaves it alone.
4. On a debt call the gender is known before the dial. The call carries the feminine dictionary for a woman and the masculine one otherwise.
5. את ("you", feminine) is never bare: אַתְּ. The dictionary cannot carry it, because the same letters are the object marker in almost every sentence.

**The word list** (34 entries, both genders, in `scripts/cartesia_dicts.py`): לך, שלך, איתך, אתך, אליך, עליך, אותך, ממך, אצלך, בשבילך, עבורך, בגללך, מולך, לידך, בעצמך, שלומך, and the second-person past: התקשרת, אמרת, ביקשת, שלחת, כתבת, דיווחת, פתחת, שילמת, קיבלת, סיפרת, שאלת, הזכרת, עדכנת, ציינת, הסכמת, פנית, ראית, רצית. Standard pointing, e.g. לְךָ / לָךְ, שְׁלוֹמְךָ / שְׁלוֹמֵךְ, הִתְקַשַּׁרְתָּ / הִתְקַשַּׁרְתְּ.

**The residue, stated plainly.** For a woman caller the dictionary cannot help: when the model leaves a pronoun bare after switching (14 of 19 in Batya's call), it is said masculine. Points 2, 3 and 5 above are the prompt's share of the fix and they are best-effort, as every prompt rule is. The default path, which is the first minutes of every call and most calls entirely, becomes deterministic.

## 4. What stays in the prompt (proposed, with examples)

The owner asked to see old and new lines before any change to how the bot addresses people. Three edits to the incoming prompt's gender bullet, nothing else:

| Now | Proposed | Why |
|---|---|---|
| "כל מילה שנגמרת בפנייה אליו או אליה ... נכתבת תמיד מנוקדת" (every address word is always written pointed) | Keep, but say it for the feminine: "כשברור שמדברת איתך אישה, כל מילה כזאת נכתבת מנוקדת בנקבה, או שאתה בוחר ניסוח בלי הסיומת" (when a woman is speaking, every such word is written pointed feminine, or you choose a phrasing without the suffix) | The masculine default is now the dictionary's job; the rule is needed only where the dictionary cannot know |
| (nothing on names) | "שם פרטי אינו ראיה למין: רוני, טל, שחר, עדי יכולים להיות גבר או אישה" (a first name is not evidence of gender) | Roni, 5 Oct: the model made a man a woman from the name, and spoke of itself in the feminine |
| (את listed among the feminine forms, unpointed) | את is always written אַתְּ | Bare את is the object marker to the voice |

Example, a woman caller, as the model should write it after she says "אני גרה בדירה שש": "בטח, אני פותח על זה פנייה. **תגידי** לי רק את הרחוב ומספר הבית, ואני כבר **רושם**" (feminine verb, no pronoun suffix at all), rather than "תוכל לתת לי את הכתובת שלך".

## 5. A check so it cannot come back

`scripts/voice_qa.py` runs the agents' real model on test calls and keeps the raw text. A small gate on that text, the same regexes used for the count in 2a: for each call, (a) no feminine verb before the caller's own feminine word, (b) once switched, no masculine verb after, (c) every ambiguous pronoun after the switch pointed feminine. Reported like `check_whatsapp_rules.py`: cases, a pin, a replay. Not built; it is a few dozen lines on the counting script used today.

## 6. How it ships, and what needs the owner's go

Ready, not live:

1. `scripts/cartesia_dicts.py --key CARTESIA_YARIV_API_KEY --apply` creates the two dictionaries on the Cartesia account on Vapi's credential (the client's since 31 Aug). **A write to the client's Cartesia account: his go.** `--delete` removes them.
2. The two ids go into `.env` as `CARTESIA_DICT_INBOUND` (masculine) and `CARTESIA_DICT_DEBT`; `python scripts/vapi_set_voice.py --agent inbound --apply` then sends the id with the voice, reads it back, and changes nothing else (the field is a no-op while the variable is unset; dry run today: "Nothing to do"). The debt agent gets the masculine id the same way until the per-call choice exists.
3. One real call by the owner: the opener, "how are you", and a "thanks for calling" goodbye, listening for *lekha*, *shlomkha*, *hitkasharta*. That call also confirms Vapi passes the id for sonic-3.5. If it does not, the regex fallback in 2d is the next step.
4. The prompt edits in section 4, on his word, through `vapi_sync.py inbound --keep-voice --apply`.
5. Debt per-call choice: `dashboard/lib/call.ts` adds `voice: {provider: "cartesia", voiceId, model, pronunciationDictId}` to `assistantOverrides` by the gender it already computes. Whether Vapi merges or replaces the `voice` object on override is not documented; the first call's webhook carries the merged assistant and settles it. Not built.

Rollback at any step: unset the variable and run `vapi_set_voice.py --agent inbound --apply` (the field goes back to empty), or `cartesia_dicts.py --delete`.

## 7. Caveats

- Measured with a Hebrew library voice on our key, not voice A; the model does the reading, the voice colours it. The owner's call is the proof.
- The machine comparison distinguishes readings by distance; it does not hear. The margins on שלומך and התקשרת were narrow.
- Vapi's field text says sonic-3 only; its docs say sonic-3 or newer. Unverified on 3.5 through Vapi until a call.
- The Vapi transcripts and the dashboard's call page will keep showing bare words: they show normalised text, not what was said.
- The debt call this morning (01a11601, 10:55 UTC) shows "לשלוח לך קישור לתשלום בוואטסאפ לשלוח לך קישור" twice in one line; it may be the same normalisation. Not pursued.

## 8. The samples (`voice/samples/gender-*.mp3` on this PC; the folder is gitignored. Noam, sonic-3.5)

| File | Text | What to listen for |
|---|---|---|
| gender-g1-help-masc-pointed | איך אני יכול לעזור לְךָ היום? | *lekha* (the live opener's form) |
| gender-g2-help-fem-pointed | איך אני יכול לעזור לָךְ היום? | *lakh* |
| gender-g3-help-bare | איך אני יכול לעזור לך היום? | bare: which one the voice picks |
| gender-g4 / g5 / g6 | מה שלומְךָ / שלומֵךְ / שלומך היום? | *shlomkha* / *shlomekh* / bare |
| gender-g7 / g8 / g9 | תודה שהתקשרתָּ / שהתקשרתְּ / שהתקשרת, יום טוב. | *hitkasharta* / *hitkashart* / bare |
| gender-e7-how-bare-real | מה שלומך היום? through the masculine dictionary | should sound like g4 |
| gender-e2-how-bare-ctrl, gender-e1-banana-direct | the control: שלומך → "בננה" | proves the dictionary applies |
| gender-e4-halakh-ctrl, gender-d4-halakh-plain | הוא הלך לעבודה בבוקר, with and without the control dictionary | proves whole-word matching: both say *halakh* |

## Sources

- Cartesia: [custom pronunciations](https://docs.cartesia.ai/build-with-cartesia/sonic-3/custom-pronunciations), [pronunciation dictionary API](https://docs.cartesia.ai/2026-03-01/api-reference/pronunciation-dicts/create), [Sonic 3 to 3.5](https://docs.cartesia.ai/build-with-cartesia/tts-models/sonic-3-to-sonic-3-5), [Sonic 3.5](https://docs.cartesia.ai/build-with-cartesia/tts-models/sonic-3-5), [Hebrew](https://www.cartesia.ai/languages/hebrew)
- Vapi: [voice formatting plan](https://docs.vapi.ai/assistants/voice-formatting-plan), [pronunciation dictionaries](https://docs.vapi.ai/assistants/pronunciation-dictionaries), the API spec at api.vapi.ai/api-json (`CartesiaVoice.pronunciationDictId`, `AssistantOverrides.voice`, `RegexReplacement`)
- Prior art: the [hebrew-nikud agent skill](https://getclawkit.com/skills/official-shaharsha-hebrew-nikud) (selective points, "only when certain"), [Hebrew TTS providers compared](https://github.com/danielrosehill/Hebrew-TTS-Providers) (ElevenLabs needs `language_code: he`; MiniMax rated best), [Dicta Nakdan](https://www.openu.ac.il/en/dhsshub/tools/pages/DICTA.aspx) (automatic vowelling)
- In this repo: `docs/reference/voice/hebrew-voice-gender-pronunciation-skill.md` (the Aug table of forms), `docs/reference/voice/spell-female-male-prompt.pdf`, the 5 Oct transcripts (`docs/assistant/transcripts/2026-10-05-inbound-4-calls.json`, `...-outbound-5-calls.json`)
