"""Synthesize Hebrew through Cartesia, so a voice can be judged before it is wired in.

    python scripts/cartesia_tts.py --list
    python scripts/cartesia_tts.py --script clix          writes voice/samples/c-*.mp3

Reads CARTESIA_API_KEY from .env. Never takes a key on the command line — it
would land in shell history, which is the one place a key is hardest to remove.

WHY THIS EXISTS SEPARATELY FROM voice_clone.py
Cloning returned 402 `plan_upgrade_required` on 7 Aug: Instant Voice Cloning is
Pro-tier, and the free tier does not include it. **Re-tested 30 Aug: byte-for-byte
the same 402.** That killed the "your own voice" route for now but not the
provider — Cartesia carries native Hebrew voices (`language: he`), and those are
free-tier TTS.

The count in this paragraph used to say four. A full walk of the account on
30 Aug found 934 voices, about thirty of them `he`, so the library grew and the
number here was three weeks stale. `--list` is the answer, not this comment.

That matters because it is the first option that is native Hebrew *and* modern.
Azure's he-IL voices are accurate and flat; vapi/Elliot is expressive with an
American accent. `sonic-3` + a `he` voice is the first thing that is neither.

WHAT THIS DOES NOT REPRODUCE
Same caveats as scripts/voice_samples.py: no latency figure, no output guard, and
no chunking. Vapi splits text before the provider sees it, so a call is many
short requests where this is one long one.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")
OUT = os.path.join(ROOT, "voice", "samples")

API = "https://api.cartesia.ai"
VERSION = "2026-03-01"
# sonic-3.6 since 31 Aug, not sonic-3. Two reasons, and the second is the one that
# cost time: it is Cartesia's current GA model, and it is the ONLY model that reads
# reference audio past 10 seconds ("a longer clip won't improve results on older
# models"). A 30 Aug probe here concluded that only sonic-3 and sonic-preview speak
# Hebrew; that probe guessed six model ids and sonic-3.6 was not among them, so the
# conclusion was about the guess list rather than about Cartesia. sonic-3.6 renders
# Hebrew fine — verified 31 Aug on all three of the agent's real lines.
MODEL = os.environ.get("CARTESIA_MODEL", "sonic-3.6")

# Three of the `language: he` voices on the account, the ones these scripts use.
# Native Hebrew, not an English model reading Hebrew — which is the entire
# distinction this file exists to test. There are about thirty; run `--list`.
NOAM = "3e32f3c5-9ac0-4192-9994-87fdb277120f"      # masculine, "Broadcaster"
YARDEN = "ff857c8e-e7f9-4afd-af42-dce9f3c5ab02"    # feminine, "Trusted Advisor"
AYALA = "ebc02c0d-61fd-48f2-a6c9-0d6683b7d466"     # feminine, "Expert Narrator"

GREET = "שלום, מדבר אסף מקליקס. איך אפשר לעזור?"
# The same debt line at four hesitation strengths. Identical words otherwise, so
# any difference heard is the filler and nothing else.
D_NONE = ("רציתי לעדכן אותך לגבי החוב שלך, שהוא מאה שקלים. "
          "במערכת שלנו הוא עדיין לא הוסדר, וצריך להסדיר אותו עד סוף השבוע.")
D_EH = ("אה, רציתי לעדכן אותך לגבי, אה, החוב שלך, שהוא מאה שקלים. "
        "במערכת שלנו הוא עדיין לא הוסדר, ו, אה, צריך להסדיר אותו עד סוף השבוע.")
D_ELL = ("רציתי לעדכן אותך לגבי... החוב שלך, שהוא מאה שקלים. "
         "במערכת שלנו הוא עדיין לא הוסדר, ו... צריך להסדיר אותו עד סוף השבוע.")
D_MIX = ("אה, רציתי לעדכן אותך לגבי... החוב שלך, שהוא מאה שקלים. "
         "במערכת שלנו הוא עדיין לא הוסדר, ו, אה, צריך להסדיר אותו עד סוף השבוע.")

# 16 Sep, the client's review: "the company name comes out as Homz/Himz". Nobody
# has ever listened to how the clone says הומיז -- recording is off on the
# assistants and every transcript record of a mangled name is Deepgram's, not
# the voice's. So: the two live first messages and the closing line, the name
# spelled five ways, rendered through the CLIENT's clone on the model Vapi
# actually runs. Render with
#
#   CARTESIA_MODEL=sonic-3.5 python scripts/cartesia_tts.py --script homiez --key CARTESIA_YARIV_API_KEY
#
# and the owner listens (voice/samples/name-*.mp3). The spelling that lands
# goes into voice_guard.PRONUNCIATION and the fixed lines; the transcripts
# cannot settle this, only an ear can. `ido_compare.py` has the ids.
CLONE = "ba765d50-19c6-4b3e-bc15-9de3b45f82f7"
NAME_FORMS = [
    ("plain",   "הומיז"),        # as written everywhere today
    ("niqqud",  "הוֹמִיז"),       # holam + hiriq: ho-MIZ spelled out
    ("hyphen",  "הומי-ז"),       # the client's own spelling in the 12 Aug note
    ("geresh",  "הומי'ז"),       # the same idea with a geresh
    ("yodyod",  "הומייז"),       # doubled yod, the long-i convention
]


def _homiez():
    out = []
    for tag, form in NAME_FORMS:
        out.append(("name-%s-1-greet" % tag, CLONE,
                    "שלום, מדבר מיכאל מהצוות של %s. איך אפשר לעזור?" % form, None))
        out.append(("name-%s-2-close" % tag, CLONE,
                    "תודה שהתקשרתם ל%s, יום טוב ולהתראות." % form, None))
        # The glued forms the model composes: מ+, ל+, ש+. voice_guard rewrites
        # the first two today; the third it does not, and this is where to hear
        # whether it must.
        out.append(("name-%s-3-glued" % tag, CLONE,
                    "אני מתקשר מ%s, בקשר לבניין ש%s מנהלת." % (form, form), None))
    return out


SCRIPTS = {
    "homiez": _homiez(),
    "clix": [
        ("c0-greeting",     NOAM,   GREET,  None),
        ("c1-debt-none",    NOAM,   D_NONE, None),
        ("c2-debt-eh",      NOAM,   D_EH,   None),
        ("c3-debt-ellipsis", NOAM,  D_ELL,  None),
        ("c4-debt-mixed",   NOAM,   D_MIX,  None),
        # Emotion is a Cartesia-only control and has no Azure equivalent. The
        # debt call is the one place warmth is load-bearing: the same sentence
        # read flatly reads as a threat.
        ("c5-debt-warm",    NOAM,   D_MIX,  "positivity:low"),
        ("c6-debt-curious", NOAM,   D_MIX,  "curiosity:low"),
        # The support agent is female — this is the inbound greeting.
        ("c7-support-fem",  YARDEN, "שלום, הגעת לקליקס. איך אפשר לעזור?", None),
    ],
}


def load_key(var="CARTESIA_API_KEY"):
    """The VARIABLE name is the argument, never the key. See voice_clone.py.

    A cloned voice is private to the account that created it, so playing one back
    needs that account's key — which is not necessarily the one the rest of this
    project uses.
    """
    if not os.path.exists(ENV):
        sys.exit(".env not found.")
    for line in open(ENV, encoding="utf-8"):
        if line.startswith(var + "="):
            k = line.split("=", 1)[1].strip()
            if k:
                return k
    sys.exit("%s is empty or missing in .env" % var)


def call(path, key, body=None, method="GET"):
    req = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(body).encode("utf-8") if body else None,
        headers={"X-API-Key": key, "Cartesia-Version": VERSION,
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %d on %s %s\n%s" % (e.code, method, path, e.read().decode("utf-8", "replace")))


def synth(key, voice_id, text, emotion=None):
    body = {
        "model_id": MODEL,
        "transcript": text,
        "voice": {"mode": "id", "id": voice_id},
        "language": "he",
        "output_format": {"container": "mp3", "sample_rate": 44100, "bit_rate": 128000},
    }
    if emotion:
        # experimental controls are Cartesia's own; they are not part of the
        # Vapi voice object, so anything tuned here must be re-expressed as
        # CartesiaVoice.experimentalControls in vapi_sync.py before it ships.
        body["_experimental_controls"] = {"emotion": [emotion]}
    return call("/tts/bytes", key, body, "POST")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="Hebrew voices on the account")
    ap.add_argument("--script", choices=sorted(SCRIPTS), help="render a named script")
    # Render a script through ONE voice instead of the per-line voices, which is
    # how a cloned voice gets judged against a stock one on identical words. The
    # id goes in the filename because the whole point is hearing two of these
    # side by side, and a second run must not overwrite the first.
    ap.add_argument("--voice", metavar="ID",
                    help="override every voice in the script with this id")
    ap.add_argument("--key", metavar="VAR", default="CARTESIA_API_KEY",
                    help="read the key from this .env variable (not the key itself)")
    a = ap.parse_args()
    key = load_key(a.key)

    if a.list:
        d = json.loads(call("/voices/?limit=100", key))
        rows = d.get("data", d if isinstance(d, list) else [])
        heb = [r for r in rows if r.get("language") == "he"]
        print("%d Hebrew voices (of %d returned)" % (len(heb), len(rows)))
        for r in heb:
            print("  %s  %-28s %s" % (r["id"], r.get("name"), r.get("gender")))
        return

    if not a.script:
        sys.exit("pass --script or --list")

    os.makedirs(OUT, exist_ok=True)
    print("model %s\n" % MODEL)
    for name, vid, text, emo in SCRIPTS[a.script]:
        if a.voice:
            vid = a.voice
            name = "%s-%s" % (name, a.voice[:8])
        audio = synth(key, vid, text, emo)
        p = os.path.join(OUT, name + ".mp3")
        open(p, "wb").write(audio)
        print("  %-18s %6.1f KB  %s%s" % (
            name, len(audio) / 1024, "[%s] " % emo if emo else "", text[:44]))
    print("\nOpen voice/clix-cartesia.html to compare against Azure.")


if __name__ == "__main__":
    main()
