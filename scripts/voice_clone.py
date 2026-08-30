"""Clone a voice at Cartesia and print the id the assistant needs.

    python scripts/voice_clone.py --dry          show what would be sent
    python scripts/voice_clone.py --go           create the clone
    python scripts/voice_clone.py --list         voices already on the account

    --key VAR    read the key from a different .env variable

Reads CARTESIA_API_KEY from .env by default. `--key` names the VARIABLE, never
the key: a key on a command line lands in shell history, which is the one place
it is hardest to remove. Same convention as `vapi_transfer.py --to`.

WHICH ACCOUNT CAN ACTUALLY CLONE
Ours cannot. `CARTESIA_YARIV_API_KEY` can — the client's own account carries a
paid tier, found 30 Aug by sending a clone request with no file attached: a
plan-gated account answers 402 at the gate, an entitled one answers 400 about
the missing file. That probe creates nothing and is the cheap way to ask.

    python scripts/voice_clone.py --go --key CARTESIA_YARIV_API_KEY

A voice is private to the account that made it, so anything that plays it back
needs the same key — `cartesia_tts.py --key` exists for that reason.

WHY CARTESIA AND NOT ELEVENLABS
A clone cannot run on `provider: vapi`. VapiVoice.voiceId is a closed enum of
thirty names in Vapi's own OpenAPI spec, so there is no slot for a custom id, and
CloneVoiceDTO in that spec is referenced by no path and no other schema. The
clone therefore lives in a provider account with Vapi pointing at it.

Of the providers that accept a free-text voiceId, Cartesia is the one that
declares Hebrew: `he` sits in its 42-language enum. ElevenLabs declares
`language` as free text, so nothing states whether Hebrew works there at all —
it would ride on eleven_v3 — and Vapi's spec carries the error
`eleven-labs-blocked-using-instant-voice-clone-and-requested-upgrade`, so its
cloning is plan-gated too. Cartesia also keeps `chunkPlan`, which is where the
output guard lives; a provider without it would silently drop the filter that
stops the model reading its own tool calls aloud.

WHAT THIS COSTS. BOTH EARLIER ANSWERS HERE WERE WRONG.
This paragraph used to reason from documentation and get it backwards in two
directions at once. It said third-party write-ups put cloning on a "$49/month Pro
tier", and that Cartesia's own docs called instant cloning "fast and free", and
it sided with the docs. Neither held.

Run against the API, twice — 7 Aug and again 30 Aug — /voices/clone returns:

    402 plan_upgrade_required
    "This feature is not available on the free tier"

And the pricing page, read 30 Aug, explains the shape the docs obscured. There
are two cloning features on four tiers, and the $49 belongs to the other one:

    Free      $0     no cloning at all
    Pro       $5     INSTANT cloning — this script          <- what we need
    Startup   $49    adds PROFESSIONAL cloning (30+ min of audio)
    Scale     $299

So the blocker is real and the fix is **$5 a month**, not the $49 this file
implied for three weeks. That mattered: a $49 line item gets deferred and a $5
one does not, and the voice sat unbuilt partly because of a number nobody
re-checked. **Ask the API and read the seller's own price list; do not infer a
plan gate from a feature doc.**

TEN SECONDS VERSUS THE WHOLE RECORDING
Asked for, and it is not available: the source recording is 3m40s, which is 22x
over instant cloning's 10-second limit and 8x under Pro cloning's 30-minute
minimum. It falls in the gap between the two modes. Sending the whole file to the
instant endpoint does not use the whole file — it lets the API choose which ten
seconds to keep instead of choosing them deliberately. Hence the candidates below.
"""

import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")

API = "https://api.cartesia.ai"
# Required, and the only value the API accepts. It is dated rather than
# semantic, so a future version string is a deliberate migration and not a
# number to bump when something breaks.
VERSION = "2026-03-01"

# TEN SECONDS IS THE LIMIT, AND IT DECIDES THE WHOLE RESULT.
#
# Cartesia's instant cloning takes a clip of "up to 10 seconds". The source
# recording is 220 seconds, so handing it the whole thing means the clone is
# built from whichever ten seconds the API happens to keep — which could be the
# throat-clear at the start. The voice is then judged on a slice nobody chose.
#
# So the ten seconds are chosen deliberately. Their docs are specific about what
# ruins a clone: "pauses in the recording will be mimicked by the cloned voice",
# and background noise and clipping are baked in permanently. The candidates
# below were cut from the longest silence-free stretches of the recording and
# scored on mean level, steadiness of level, and the absence of any near-silent
# second inside the window:
#
#     clone-candidate-a.wav   162-172s   loudest and steady      <- default
#     clone-candidate-b.wav   150-160s   steadiest of the three
#     clone-candidate-c.wav   31-41s     early, different content
#     clone-candidate-d.wav   62-72s     cut 30 Aug, quietest
#     clone-candidate-e.wav   100-110s   cut 30 Aug
#
# d and e were added on 30 Aug from the two longest silence-free runs the first
# pass never sampled (30-85s and 93-131s). They came out 2-4 dB quieter in the
# mean than a/b/c, so they are alternates rather than contenders.
#
# **None of the five clips.** The whole recording peaks at 0.0 dB, which would be
# baked into a clone permanently, but measured one window at a time the peaks are
# -0.9 to -2.2 dB: the full-scale sample lives outside every candidate. Measure
# the window, never the file.
#
# Those are objective criteria, and objective criteria cannot hear. Listen to all
# three and pass --clip to pick a different one; the best clone comes from the
# one that sounds most like ordinary speaking, not the one with the best numbers.
CLIP = os.path.join(ROOT, "voice", "clone-candidate-a.wav")
MAX_SECONDS = 10.0
NAME = "Echo Stone"
# The subject is Ido, whose recording is `ido-voice.mp4` in the repo root, and who
# agreed to this on 30 Aug. The name below is deliberately not his: it is a label
# on a third-party vendor account, and a codename there costs nothing while a real
# person's name is one more place his identity sits. `access[type]: private` below
# is the other half of the same decision.
#
# ISO 639-1. `he` because the assistant speaks Hebrew and nothing else — see
# the Language section of docs/features/10-debt-followup/prompt.md.
#
# Set this to the language SPOKEN IN THE CLIP. Cloning from a Hebrew clip for a
# Hebrew agent is the strongest version; cloning from English and synthesising
# Hebrew works cross-lingually but is a second-best that shows up as accent.
LANGUAGE = os.environ.get("CARTESIA_CLONE_LANGUAGE", "he")

# Accepted by the API. The clip is rejected outright if it is anything else, so
# check here rather than spending a request finding out.
FORMATS = {".flac", ".mp3", ".mpeg", ".mpga", ".oga", ".ogg", ".wav", ".webm"}


def load_env(var="CARTESIA_API_KEY"):
    if not os.path.exists(ENV):
        sys.exit(".env not found. Copy .env.example to .env and fill in CARTESIA_API_KEY.")
    for line in open(ENV, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    key = os.environ.get(var, "").strip()
    if not key and var != "CARTESIA_API_KEY":
        sys.exit("%s is empty or missing in .env" % var)
    if not key:
        sys.exit(
            "CARTESIA_API_KEY is empty in .env\n"
            "  1. Create a Cartesia account at cartesia.ai — a free one may be enough.\n"
            "     Cartesia's docs say training instant clones is 'fast and free'. The\n"
            "     paid tier is for PRO cloning, which is the 30-minute one, not this.\n"
            "     If --go returns 402 or 403 anyway, the plan is the reason.\n"
            "  2. Dashboard > API Keys. The key starts sk_car_.\n"
            "  3. Put it in .env as CARTESIA_API_KEY=... — in the file, not in chat."
        )
    return key


def multipart(fields, files):
    """Encode a multipart/form-data body with the standard library only.

    Written out rather than pulled from `requests` because this project has no
    third-party dependencies and adding one to upload a single file is a poor
    trade. The parts are bytes throughout: a filename or a field value that is
    not ASCII would otherwise be silently mangled by an implicit encode.
    """
    boundary = uuid.uuid4().hex
    out = []
    for k, v in fields.items():
        out.append(("--%s\r\n" % boundary).encode())
        out.append(('Content-Disposition: form-data; name="%s"\r\n\r\n' % k).encode())
        out.append(str(v).encode("utf-8") + b"\r\n")
    for k, path in files.items():
        name = os.path.basename(path)
        ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
        out.append(("--%s\r\n" % boundary).encode())
        out.append(('Content-Disposition: form-data; name="%s"; filename="%s"\r\n'
                    % (k, name)).encode())
        out.append(("Content-Type: %s\r\n\r\n" % ctype).encode())
        out.append(open(path, "rb").read() + b"\r\n")
    out.append(("--%s--\r\n" % boundary).encode())
    return b"".join(out), "multipart/form-data; boundary=" + boundary


def call(key, method, path, body=None, ctype=None):
    headers = {
        "Authorization": "Bearer " + key,
        "Cartesia-Version": VERSION,
        "User-Agent": "homies-voice-clone/1.0",
    }
    if ctype:
        headers["Content-Type"] = ctype
    req = urllib.request.Request(API + path, method=method, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        if e.code in (402, 403):
            detail += ("\n\nA 402/403 here is almost always the plan rather than the key: "
                       "Instant Voice Cloning starts on Cartesia's Pro tier, and Free and "
                       "Starter do not include it.")
        sys.exit("HTTP %s on %s %s\n%s" % (e.code, method, path, detail))


def duration(path):
    """Seconds, read from the WAV header rather than by shelling out to ffprobe.

    The point is that this check must work on a machine that has no ffmpeg, so
    that an oversized clip is refused here rather than discovered as a clone
    built from an arbitrary ten seconds of the file.
    """
    import wave
    try:
        with wave.open(path, "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except (wave.Error, EOFError):
        return None      # not a WAV; the API is then the one that judges it


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("--dry", "--go", "--list"):
        sys.exit(__doc__)
    if "--clip" in args:
        globals()["CLIP"] = os.path.abspath(args[args.index("--clip") + 1])
    keyvar = args[args.index("--key") + 1] if "--key" in args else "CARTESIA_API_KEY"
    key = load_env(keyvar)

    if args[0] == "--list":
        voices = call(key, "GET", "/voices/")
        items = voices.get("data", voices) if isinstance(voices, dict) else voices
        if not items:
            print("No voices on this account yet.")
            return
        for v in items:
            print("%-38s %-28s %s" % (v.get("id"), v.get("name"), v.get("language")))
        return

    if not os.path.exists(CLIP):
        sys.exit("Clip not found: %s\nRegenerate it from the source recording with ffmpeg." % CLIP)
    ext = os.path.splitext(CLIP)[1].lower()
    if ext not in FORMATS:
        sys.exit("Cartesia rejects %s. Accepted: %s" % (ext, ", ".join(sorted(FORMATS))))

    secs = duration(CLIP)
    if secs is not None and secs > MAX_SECONDS + 0.05:
        sys.exit(
            "Clip is %.1fs. Cartesia's instant cloning takes up to %.0f seconds.\n"
            "Sending a longer file means the clone is built from whichever ten "
            "seconds the API keeps,\nwhich is not a choice anyone made. Use one of "
            "the prepared candidates:\n"
            "  python scripts/voice_clone.py --go --clip voice/clone-candidate-b.wav"
            % (secs, MAX_SECONDS))

    size = os.path.getsize(CLIP)
    print("clip      : %s (%.1f MB, %.1fs)" % (os.path.relpath(CLIP, ROOT), size / 1e6,
                                               secs if secs is not None else -1))
    print("name      : %s" % NAME)
    print("language  : %s   (the language spoken in the clip)" % LANGUAGE)
    print("endpoint  : POST %s/voices/clone" % API)
    print("version   : %s" % VERSION)
    print("key       : %s   (the .env variable, and so which account owns the voice)" % keyvar)

    if args[0] == "--dry":
        print("\nDry run. Nothing was uploaded. Re-run with --go.")
        return

    fields = {
        "name": NAME,
        "language": LANGUAGE,
        "description": "Cloned for the Homies debt follow-up agent. Hebrew, male.",
        # Private is the default and is restated here on purpose. This is a real
        # person's voice; a public voice on a shared library is not something to
        # arrive at by leaving a field out.
        "access[type]": "private",
    }
    body, ctype = multipart(fields, {"clip": CLIP})
    result = call(key, "POST", "/voices/clone", body, ctype)

    vid = result.get("id")
    print("\nOK — cloned.")
    print("voice id  : %s" % vid)
    print("\nNext, and it is two steps:")
    print("  1. Add CARTESIA_VOICE_ID=%s to .env" % vid)
    print("     Add the SAME Cartesia API key to Vapi as a provider credential —")
    print("     Vapi synthesises server-side, so it needs its own copy.")
    print("  2. python scripts/vapi_sync.py debt --apply")
    print("\nThen listen before anyone else does: voice/hebrew-voice-test.md")


if __name__ == "__main__":
    main()
