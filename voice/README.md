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

## The clone does not exist yet, and the reason is five dollars

`scripts/voice_clone.py` is finished and its clips are cut, but Cartesia's
`/voices/clone` answers `402 plan_upgrade_required` on the free tier. Tried
7 Aug, tried again 30 Aug, same response both times.

Instant voice cloning starts on Cartesia's **Pro tier, $5/month**. This file and
`voice_clone.py` both used to imply $49, which is the *Startup* tier and buys
*professional* cloning, a different feature needing thirty minutes of audio. The
voice sat unbuilt for three weeks partly because of that wrong number.

Upgrade at play.cartesia.ai/subscription, then `python scripts/voice_clone.py
--go`. Everything downstream is ready: `cartesia_tts.py --voice <id>` renders any
voice through the existing scripts, and `voice/samples/c*-a976c076.mp3` is
already Eyal saying those lines, so the comparison only needs the second column.

## The thing this directory exists to have proved

Vapi has **no synthesis endpoint** — all 48 paths were checked. Its voices can
only be heard on a live call, which costs money and takes a browser. Everything
here is the cheap way to reject a voice before paying to hear it, and it worked:
Azure was rejected as robotic, Noam was rejected as robotic, and Eyal was chosen
out of eleven, all without placing a call.
