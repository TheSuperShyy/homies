# -*- coding: utf-8 -*-
"""Render the same three Hebrew lines through every candidate Ido clone, so the
difference heard is the voice and the model and nothing else.

WHY THIS FILE EXISTS RATHER THAN AN INLINE ONE-OFF
The 30 Aug comparison was rendered by hand and could not be reproduced, so the
next round could not be sure it was comparing like with like. `voice/samples/` is
gitignored on purpose (generated output, ~10 MB), which only works if there is a
committed way to regenerate it. This is that way for the Ido comparison.

WHAT IS BEING COMPARED, AND WHY THOSE FOUR
Two variables, crossed, because on 31 Aug both were suspect at once:

    clip length   9.4s (the v2 clone)   vs   55.5s (the long clone)
    model         sonic-3               vs   sonic-3.6

Cartesia's guide: "Only Sonic 3.6 uses reference audio beyond 10 seconds, so a
longer clip won't improve results on older models." That makes `long` + `sonic-3`
the control. If it sounds the same as the 9.4s clip on sonic-3, the extra audio
is genuinely being ignored by the old model and the guide is describing reality.
If `long` + `sonic-3.6` is the only one that improves, the fix is both changes
together and neither alone.

Run:
    python scripts/ido_compare.py

Eyal's three files are NOT re-rendered — he is a stock voice on our own account
and his renders from 30 Aug are the reference column. Delete
`voice/samples/final/*-eyal.mp3` if they ever need rebuilding.
"""

import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")
OUT = os.path.join(ROOT, "voice", "samples", "final")

API = "https://api.cartesia.ai/tts/bytes"
VERSION = "2026-03-01"

# The clones live on the CLIENT's Cartesia account, so the client's key is the
# only one that can play them back — a cloned voice is private to the account
# that made it. Our own key would 404 on these ids.
KEYVAR = "CARTESIA_YARIV_API_KEY"

V2 = "493006a2-0b42-46cf-a094-5cbde1ece032"    # 9.4s clip, rejected twice by ear
LONG = "ba765d50-19c6-4b3e-bc15-9de3b45f82f7"  # 55.5s clip, cut 31 Aug

# The agent's real lines, not invented test sentences. The closing line matters
# most: "יום טוב, ולהתראות" is an endCallPhrase on the live assistant, so it is a
# sentence the agent must land cleanly or the call does not end.
LINES = [
    ("greet",  u"שלום, מדבר מיכאל מהצוות של הומיז. איך אפשר לעזור?"),
    ("ticket", u"רשמתי את הפנייה, נזילה מהתקרה באמבטיה, והיא עוברת לצוות התחזוקה."),
    ("close",  u"תודה שהתקשרת להומיז, יום טוב, ולהתראות."),
]

# tag -> (voice id, model). The tag is the filename suffix and the column name on
# the listening page; keep the two in step.
# VAPI DOES NOT ACCEPT EVERY MODEL CARTESIA OFFERS, and that is the constraint
# that decides this. A PATCH with sonic-3.6 is refused: "voice.model must be one
# of the following values for he language: sonic-3.5, sonic-3.5-2026-05-04,
# sonic-3, sonic-3-2026-01-12, sonic-3-2025-10-27". So sonic-3.6 -- the only
# model that reads a reference clip past 10 seconds -- cannot be used on a live
# agent at all today, and sonic-3.5 is the best available substitute. Render it
# and listen, because Cartesia's own line implies the 55s clip buys nothing here.
VARIANTS = [
    ("v2-s36",      V2,   "sonic-3.6"),
    ("long-sonic3", LONG, "sonic-3"),
    ("long-s36",    LONG, "sonic-3.6"),
    ("long-s35",    LONG, "sonic-3.5"),      # what Vapi would actually run
    ("v2-s35",      V2,   "sonic-3.5"),      # control: does the long clip help here at all?
]


def load_env(name):
    if not os.path.exists(ENV):
        sys.exit("No .env at %s" % ENV)
    m = re.search(r"^%s=(.*)$" % re.escape(name), io.open(ENV, encoding="utf-8").read(), re.M)
    if not m or not m.group(1).strip():
        sys.exit("%s is not set in .env" % name)
    return m.group(1).strip().strip('"').strip("'")


def render(key, text, voice, model, path):
    body = json.dumps({
        "model_id": model,
        "transcript": text,
        "voice": {"mode": "id", "id": voice},
        "language": "he",
        "output_format": {"container": "mp3", "sample_rate": 44100, "bit_rate": 128000},
    }).encode("utf-8")
    req = urllib.request.Request(API, data=body, headers={
        "X-API-Key": key,
        "Cartesia-Version": VERSION,
        "Content-Type": "application/json",
        # Not decoration: Cloudflare 1010s Python's default User-Agent on these
        # vendors, and the failure looks like an auth problem rather than a UA one.
        "User-Agent": "curl/8.5.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        return "HTTP %s  %s" % (e.code, detail)
    with io.open(path, "wb") as f:
        f.write(data)
    return None


def main():
    key = load_env(KEYVAR)
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    print("key    : %s   (the .env variable — the clones are private to that account)" % KEYVAR)
    print("out    : %s\n" % os.path.relpath(OUT, ROOT))

    failed = 0
    for tag, voice, model in VARIANTS:
        print("%-14s voice %s  model %s" % (tag, voice[:8], model))
        for name, text in LINES:
            path = os.path.join(OUT, "%s-%s.mp3" % (name, tag))
            err = render(key, text, voice, model, path)
            if err:
                failed += 1
                print("    %-7s FAILED  %s" % (name, err))
            else:
                print("    %-7s %6.1f KB  %s" % (name, os.path.getsize(path) / 1024.0,
                                                 os.path.basename(path)))
        print("")

    if failed:
        print("%d render(s) failed. A `language_not_supported` here means the model "
              "does not speak Hebrew\nand that variant should come off the page rather "
              "than be shown as silence." % failed)
        return 1
    print("Done. Durations are worth reading off the page, but they cannot hear:\n"
          "every fault in this voice so far was found by a person in seconds and by\n"
          "the measurements never. Open voice/ido-vs-eyal.html and listen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
