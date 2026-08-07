# Paste these into the playgrounds and decide with your ears

Azure is out — accurate Hebrew, no expression, and no setting fixes it. Every
remaining option needs an API key, so the order is: **listen first, pay second.**
Both playgrounds below are free and need no code.

---

## 1. ElevenLabs — elevenlabs.io

Free tier, 10k credits/month, no card.

**You must switch the model to `Eleven v3`.** The default is
`eleven_multilingual_v2`, which has 29 languages and **no Hebrew**. Hebrew exists
only on v3. If it sounds wrong, check this first — it is the single most common
mistake.

### Plain

```
שלום, מדבר אסף מקליקס. איך אפשר לעזור?

אה, רציתי לעדכן אותך לגבי... החוב שלך, שהוא מאה שקלים. במערכת שלנו הוא עדיין לא הוסדר, ו, אה, צריך להסדיר אותו עד סוף השבוע.
```

### With v3 audio tags — this is the expressive version

v3 accepts bracketed direction. This is what Azure fundamentally cannot do.

```
[warm] שלום, מדבר אסף מקליקס. איך אפשר לעזור?

[hesitant] אה... רציתי לעדכן אותך לגבי החוב שלך, שהוא מאה שקלים. [thoughtful] במערכת שלנו הוא עדיין לא הוסדר, ו... אה, צריך להסדיר אותו עד סוף השבוע.
```

> **These tags must never go in the assistant prompt.** The output guard in
> `voice.chunkPlan.formatPlan` strips the brackets but leaves the word inside —
> verified: `[inhales] שלום` came out as `inhales שלום`. In the playground they
> are fine. On a live assistant they get read aloud. Wiring them up safely is a
> guard change, not a copy-paste.

---

## 2. Cartesia — cartesia.ai

Free tier, and **instant voice cloning is free** — the only place you can hear
your own voice today.

Set **language: Hebrew** and model **`sonic-3`**.

```
שלום, מדבר אסף מקליקס. איך אפשר לעזור?

אה, רציתי לעדכן אותך לגבי... החוב שלך, שהוא מאה שקלים. במערכת שלנו הוא עדיין לא הוסדר, ו, אה, צריך להסדיר אותו עד סוף השבוע.
```

Two things to turn on while you are there:

- **Clone your voice.** Upload `voice/clix-clone-b.wav` — already cut to 8.98s,
  the loudest of the three candidates, and under the 10-second instant limit.
- **`accentLocalization`.** Cartesia's own description: *"the voice adapts to
  match the transcript language accent while preserving vocal characteristics."*
  This is the setting that makes a voice cloned from English speak Hebrew without
  the American accent. It is the only such control on any provider Vapi supports.

---

## What to listen for

Both read the same words. Compare on:

1. **Expression.** Does the sentence rise and fall, or is it one flat line? This
   is the whole reason for the exercise.
2. **The hesitation.** Does `אה` land as a real pause, or as a spoken syllable?
3. **מאה שקלים.** One number, not two. This broke on a real call once already.
4. **Accent**, last. It only matters among voices that already sound alive.

---

## Then

Whichever wins, put its key in `.env`:

```
CARTESIA_API_KEY=sk_car_...        # or
ELEVENLABS_API_KEY=...
```

`scripts/vapi_sync.py` already resolves cloned voices ahead of native ahead of
stock, with a fallback to Elliot if the provider fails mid-call. Nothing else
needs writing — the plumbing is done and waiting on a key.

**Cost check before you commit**, at the 4,000–6,400 min/month this system is
sized for: ElevenLabs runs roughly $270–450/month, Cartesia roughly $120–240.
Voice is about 7% of the per-minute bill today, so either is affordable — but
ElevenLabs is the one worth hearing before paying for.
