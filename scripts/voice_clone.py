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
This section said for three weeks that 220s was "22x over instant cloning's
10-second limit". **There is no 10-second limit.** Cartesia's own guide says a
clone can be made "with as little as 10 seconds of audio" — a floor, which this
file had written down as a ceiling. Their guide offers up to 60 seconds, and is
explicit about who can use it: "Only Sonic 3.6 uses reference audio beyond 10
seconds, so a longer clip won't improve results on older models."

That second sentence is why nobody noticed. Feeding 40 extra seconds to `sonic-3`
would have changed nothing audible, so the wrong constant and the wrong model
would have covered for each other. The owner found it on 31 Aug by asking the
obvious question — why is a three-minute recording being used ten seconds at a
time — which no measurement in this repo had thought to ask.

**Read the vendor's number and check which direction it points.** A minimum and a
maximum look identical in a sentence and are opposites in a constant.
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

# TEN SECONDS IS THE FLOOR. SIXTY IS THE CEILING. THE MODEL DECIDES WHICH MATTERS.
#
# Cartesia asks for "as little as 10 seconds" and accepts up to 60. Until 31 Aug
# this file read that minimum as a maximum and cut every candidate to exactly ten
# seconds, throwing away 210 seconds of a 220-second recording.
#
# The catch is that the extra audio is only read by one model: "Only Sonic 3.6
# uses reference audio beyond 10 seconds, so a longer clip won't improve results
# on older models." Everything cloned here before 31 Aug was `sonic-3` on ~10s —
# the oldest model on the least audio — and was rejected twice by ear, first for
# cutting words off and then for an unsettling up-down intonation.
#
# Whatever the length, three things from their guide are baked into a clone
# permanently and cannot be undone afterwards:
#
#   - "pauses in the recording will be mimicked by the cloned voice"
#   - background noise
#   - clipping
#
# So a clip is cut from pause edge to pause edge, never at round timestamps. That
# is not a stylistic preference: `clone-candidate-a.wav` was cut at 162.0s, opened
# on a 0.146s fragment of a syllable, and the clone learned to swallow the start
# of words. Internal sentence pauses of ~0.3s are ordinary speech and are wanted
# in a long clip; it is the edges that have to land in silence.
#
#     clone-candidate-a.wav      162-172s     round cut — PRODUCED THE v1 FAULT
#     clone-candidate-b.wav      150-160s     round cut
#     clone-candidate-c.wav       31-41s      round cut
#     clone-candidate-d.wav       62-72s      round cut, 30 Aug
#     clone-candidate-e.wav      100-110s     round cut, 30 Aug
#     clone-candidate-f/g/h.wav  various      pause-bounded, 30 Aug
#     clone-candidate-i.wav      f+g joined   9.379s  -> the v2 clone
#     clone-candidate-long.wav   29.95-85.42s 55.470s -> 31 Aug, for Sonic 3.6   <- default
#
# `long` is the 30-85s run taken whole rather than sampled: speech runs from
# 30.036s to 85.321s with only ordinary 0.25-0.35s sentence pauses inside it, and
# the cut sits 86ms before the first onset and 99ms after the last, so the edges
# are silent without being padded.
#
# MEASURE THE WINDOW, NEVER THE FILE. The whole recording peaks at 0.0 dB, which
# would bake clipping into a clone forever, but no candidate contains that sample:
# they measure -0.9 to -2.2 dB, and `long` measures -0.9 dB across all 55 seconds.
# The full-scale peak lives outside every window that has been used.
#
# And none of these numbers can hear. Every fault in this voice so far was found
# by a person in seconds and by the measurements never. Pass --clip to try another
# and listen; the best clone comes from the clip that sounds most like ordinary
# speaking, not the one with the best figures.
CLIP = os.path.join(ROOT, "voice", "clone-candidate-long.wav")
# 60.0, not 10.0 — see above. The guard stays because the API's behaviour past its
# own maximum is undocumented, and a clone silently built from an arbitrary slice
# of an oversized file is exactly the failure this script exists to prevent.
MAX_SECONDS = 60.0
MIN_SECONDS = 10.0
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
    if "--name" in args:
        # Three clones now live on the client's account and are told apart by this
        # string alone. A name is not cosmetic when someone else owns the account
        # and has to recognise what is sitting on it.
        globals()["NAME"] = args[args.index("--name") + 1]
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
            "Clip is %.1fs. Cartesia accepts up to %.0f seconds.\n"
            "Sending a longer file does not use the longer file: the clone is built "
            "from whichever\nslice the API keeps, which is nobody's choice. Cut a "
            "window instead:\n"
            "  python scripts/voice_clone.py --go --clip voice/clone-candidate-long.wav"
            % (secs, MAX_SECONDS))
    if secs is not None and secs < MIN_SECONDS - 0.05:
        # Added 31 Aug. Until then this script guarded only the ceiling it had
        # invented and left the real floor unguarded, so a too-short clip would
        # have been found out by ear rather than here.
        sys.exit(
            "Clip is %.1fs. Cartesia asks for at least %.0f seconds; a shorter clip "
            "makes a thinner\nclone. Cut a longer window from the source recording."
            % (secs, MIN_SECONDS))

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
