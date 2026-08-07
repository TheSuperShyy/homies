# voice/ — the listening pages, and why they are silent in a fresh clone

The `.html` files here are committed. **The audio they play is not**, and that is
deliberate rather than an oversight. Open any of them after cloning and every
player will be empty until you regenerate the samples.

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

## The thing this directory exists to have proved

Vapi has **no synthesis endpoint** — all 48 paths were checked. Its voices can
only be heard on a live call, which costs money and takes a browser. Everything
here is the cheap way to reject a voice before paying to hear it, and it worked:
Azure was rejected as robotic, Noam was rejected as robotic, and Eyal was chosen
out of eleven, all without placing a call.
