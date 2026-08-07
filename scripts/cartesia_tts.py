"""Synthesize Hebrew through Cartesia, so a voice can be judged before it is wired in.

    python scripts/cartesia_tts.py --list
    python scripts/cartesia_tts.py --script clix          writes voice/samples/c-*.mp3

Reads CARTESIA_API_KEY from .env. Never takes a key on the command line — it
would land in shell history, which is the one place a key is hardest to remove.

WHY THIS EXISTS SEPARATELY FROM voice_clone.py
Cloning returned 402 `plan_upgrade_required` on 7 Aug: Instant Voice Cloning is
Pro-tier, and the free tier does not include it. That killed the "your own voice"
route for now but not the provider — Cartesia carries FOUR NATIVE HEBREW VOICES
(`language: he`), and those are free-tier TTS.

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
MODEL = os.environ.get("CARTESIA_MODEL", "sonic-3")

# The four `language: he` voices on the account. Native Hebrew, not an English
# model reading Hebrew — which is the entire distinction this file exists to test.
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

SCRIPTS = {
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


def load_key():
    if not os.path.exists(ENV):
        sys.exit(".env not found.")
    for line in open(ENV, encoding="utf-8"):
        if line.startswith("CARTESIA_API_KEY="):
            k = line.split("=", 1)[1].strip()
            if k:
                return k
    sys.exit("CARTESIA_API_KEY is empty in .env")


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
    a = ap.parse_args()
    key = load_key()

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
        audio = synth(key, vid, text, emo)
        p = os.path.join(OUT, name + ".mp3")
        open(p, "wb").write(audio)
        print("  %-18s %6.1f KB  %s%s" % (
            name, len(audio) / 1024, "[%s] " % emo if emo else "", text[:44]))
    print("\nOpen voice/clix-cartesia.html to compare against Azure.")


if __name__ == "__main__":
    main()
