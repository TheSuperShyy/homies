# voice/ — the listening pages, and why they are silent in a fresh clone

The `.html` files here are committed. **The audio they play is not**, and that is
deliberate rather than an oversight. Open any of them after cloning and every
player will be empty until you regenerate the samples.

## Whose voice this is, and that he said yes

`ido-voice.mp4` in the repo root is **Ido**, 3m40s of him speaking. Every
`clone-candidate-*.wav` here is a ten-second window cut from it, and
`echo-stone-sample.wav` is the whole thing as WAV.

**Ido agreed to his voice being cloned for the Homies agent, confirmed 30 Aug
2026.** That sentence is in this file because consent for something like this is
the kind of fact that lives in one person's memory and then leaves with them, and
because the next person to find a stranger's voice in a repository deserves to
find the answer beside it rather than have to go asking.

The clone is named **Echo Stone** on Cartesia, not "Ido". A codename on a vendor
account costs nothing, and it is one fewer place his name sits. `access[type]`
is set to `private` explicitly in `scripts/voice_clone.py` for the same reason.

`clix-clone-*.wav` are a different person and a different project.

## Why the audio is gitignored

Two different reasons, and both matter:

- `Voice-record-sample-to-clone.ogg` and `clix-clone-*.wav` are **a real
  person's voice**. A voice recording identifies someone the way a photograph
  does, and once it is in a repository's history removing it is a rewrite rather
  than a delete. It stays local.
- `samples/*.mp3` are **generated**, so committing them would put ~10 MB of
  reproducible output in the history to save one command.

`.gitignore` covers `*.mp3 *.wav *.ogg *.m4a *.opus *.flac *.aac *.webm`.
Nothing in this directory should ever be force-added past that.

## Regenerating

```bash
pip install edge-tts                       # for the Azure comparisons

python scripts/voice_samples.py            # Azure he-IL, the agent's real lines
python scripts/cartesia_tts.py --script clix   # Cartesia sonic-3.5, needs CARTESIA_API_KEY
```

The two auditions — eleven masculine and eighteen feminine Hebrew voices — were
rendered inline rather than from a committed script. `cartesia_tts.py --list`
prints all 29 voices with their ids if they need rebuilding.

## What each page is for

| Page | Question it answers |
|---|---|
| `hebrew-samples.html` | Does Azure's Hebrew get the accent right? (Yes, and it is flat.) |
| `fillers.html` | Which filler spelling actually renders? (`אה`, and `אההה` backfires.) |
| `clix-script.html` | The CLIX script in English, filler variants |
| `clix-hebrew.html` | The same script in Hebrew |
| `clix-cartesia.html` | Cartesia vs Azure, identical text |
| `hebrew-audition.html` | Eleven masculine Hebrew voices — **Eyal was chosen** |
| `hebrew-audition-women.html` | Eighteen feminine voices, from before both agents went male |
| `listen.html` | The original clone-candidate picker |
| `ido-vs-eyal.html` | **The live question**: does any Ido clone beat Eyal? Five rows per line — Eyal, both rejected clones, the control, the candidate |

## Three clones exist, two are rejected, and the reason was two of my own numbers

The clone lives on **the client's Cartesia account** (`CARTESIA_YARIV_API_KEY`),
approved by Yariv on 30 Aug, because ours has never had the cloning entitlement:
`/voices/clone` answers `402 plan_upgrade_required` on it. A cloned voice is
private to the account that made it, so the client's key is also the only key
that can play these back.

| | clip | model | verdict |
|---|---|---|---|
| `61e911a7…` v1 | 10s, cut at round timestamps | `sonic-3` | rejected — cut words off |
| `493006a2…` v2 | 9.4s, pause-bounded | `sonic-3` | rejected — "sudden high tone and low tone, unsettling" |
| `ba765d50…` long | 55.5s, pause-bounded | `sonic-3.6` | cut 31 Aug, awaiting a listen |

**v1's fault was mine.** `clone-candidate-a.wav` was cut at 162.0s and opened on
a 0.146s fragment of a syllable, so the clone learned to swallow the starts of
words. Clips are cut pause-edge to pause-edge now, at any length.

**v2's fault was two numbers I had written down myself and never re-read.**

1. **Ten seconds is Cartesia's minimum, not its maximum.** Their guide says a
   clone can be made "with as little as 10 seconds of audio". This repo recorded
   that as a ceiling on 5 Aug and spent three weeks choosing which ten seconds of
   a 220-second recording to keep. They accept up to 60. The v2 clip was 9.4s —
   *below* their floor, which nothing here was checking either.
2. **`sonic-3.6` was never tried.** It is Cartesia's current model, it speaks
   Hebrew, and before 31 Aug it appeared in no file in this repo. A probe on
   30 Aug concluded "only sonic-3 and sonic-preview do Hebrew"; it guessed six
   model ids and that was not one of them, so the finding described the guess
   list, not Cartesia.

Those two mistakes protected each other: *"Only Sonic 3.6 uses reference audio
beyond 10 seconds, so a longer clip won't improve results on older models."* A
longer clip on `sonic-3` changes nothing audible, so fixing either one alone
looks like a dead end. `ido-vs-eyal.html` therefore carries the control — the
55s clip on `sonic-3` — beside the candidate.

The owner found all of this by asking why a three-minute recording was being used
ten seconds at a time. No measurement in this repo had thought to ask.

### LIVE since 31 Aug: `ba765d50` on both Hebrew agents

Debt (he) `93c7f5e5` and Intake (he) `7752c6bb` both run `ba765d50`
(Echo Stone Long) on **`sonic-3.5`**, with an Elliot fallback. Read back from the
Vapi API at 06:54Z, not from a dry run.

**It runs 3.5 and not 3.6, and that is a Vapi limit rather than a choice.** Vapi
refuses `sonic-3.6` for Hebrew outright, and 3.6 is the only model that reads a
reference clip past ten seconds — so the 55-second clone's advantage is real in
`ido_compare.py` and unavailable in production. What is live is *not* the row
that was picked on the listening page.

**The Cartesia credential now holds the client's key** (`448aa856`, repointed
06:47:43Z), because a cloned voice is private to the account that made it. That
credential is the whole Cartesia bill for both Hebrew agents, not just the clone.

**Not yet heard on a call.** If Vapi could not resolve the voice it would fall
through to Elliot and answer in an American accent, logging nothing — so one
Hebrew web call is the only real proof. Rollback to Eyal:

```bash
python scripts/vapi_set_voice.py --voice a976c076-3e31-4bf2-a178-8c3ce3d52b2a --apply
python scripts/vapi_cartesia_key.py --to CARTESIA_API_KEY --apply   # billing too
```

### Regenerating the comparison

```bash
python scripts/ido_compare.py     # 9 renders, needs CARTESIA_YARIV_API_KEY
```

Eyal's three files are not re-rendered; delete `samples/final/*-eyal.mp3` if they
ever need rebuilding.

## The thing this directory exists to have proved

Vapi has **no synthesis endpoint** — all 48 paths were checked. Its voices can
only be heard on a live call, which costs money and takes a browser. Everything
here is the cheap way to reject a voice before paying to hear it, and it worked:
Azure was rejected as robotic, Noam was rejected as robotic, and Eyal was chosen
out of eleven, all without placing a call.
