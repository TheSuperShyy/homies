"""Generate Hebrew voice samples locally, so a voice can be judged before it is bought.

    pip install edge-tts
    python scripts/voice_samples.py

Writes .mp3 files into voice/samples/ and nothing else. No Vapi call, no
assistant is modified, no provider key is needed, nothing is billed.

WHY THIS IS A FAIR TEST OF AZURE-ON-VAPI
`he-IL-AvriNeural` and `he-IL-HilaNeural` are Microsoft neural voice models.
Vapi's `provider: azure` reaches the same models through the paid Speech API;
Edge read-aloud reaches them through the free one. Same model, same weights, so
the *accent and prosody* you hear here are what a call would sound like.

What this does NOT reproduce, and do not conclude anything about:
  - latency          — different endpoint, different region, no streaming
  - the output guard — lives in voice.chunkPlan.formatPlan, applied by Vapi
  - chunking         — Vapi splits text before the provider ever sees it, so a
                       call is many short requests where this is one long one

WHY THERE IS NO vapi/Elliot SAMPLE HERE, AND NO STAND-IN FOR ONE
Vapi has no synthesis endpoint — all 48 paths were checked. Its voices can only
be heard on a live call.

Substituting an English-trained Azure voice reading Hebrew was tried and does
not work: `en-US-AndrewNeural` given the line from test 1 returned 0.3 seconds
of near-silence against Avri's 3.2, because Azure's English voices decline
out-of-locale text outright. Vapi's voices *do* read Hebrew, badly — a silent
file misrepresents that as total failure, so the comparison was dropped rather
than dressed up. The American accent has to be heard on a real call.

The lines are the agent's real fixed lines, from voice/hebrew-voice-test.md.
Invented sample text proves nothing — see that file's own header for why.
"""

import asyncio
import os
import sys

try:
    import edge_tts
except ImportError:
    sys.exit("pip install edge-tts")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "voice", "samples")

AVRI = "he-IL-AvriNeural"       # male   — debt agent, matches מיכאל
HILA = "he-IL-HilaNeural"       # female — inbound support agent

# Each line is the shortest one that breaks a different thing. Numbered to match
# voice/hebrew-voice-test.md, so a failure here points straight at the diagnosis
# written there rather than needing a fresh judgement.
LINES = [
    ("1-gutturals", AVRI,
     "שלום, מדבר מיכאל מהומיז, חברת הניהול של הבניין. אני מדבר עם דוד?"),
    ("3-number", AVRI,
     "מדובר בתשלום ועד בית של ארבע מאות וחמישים שקלים עבור חודש יולי."),
    ("4-reference", AVRI,
     "מספר הפנייה שלך HM-2026-9634."),
    ("5-closing", AVRI,
     "מצוין, תודה רבה על הזמן. שיהיה יום טוב ולהתראות."),
    ("9-voicemail", AVRI,
     "שלום, מדבר מיכאל מחברת הניהול הומיז לגבי בניין הרצל 14. "
     "יש נושא שנשמח להסדיר איתך, אפשר לחזור אלינו למספר 03-1234567. תודה ויום טוב."),
    # The inbound agent is female, and its greeting is the first thing any
    # resident ever hears from this system.
    ("inbound-greeting", HILA,
     "שלום, הגעת להומיז, חברת ניהול הבניינים. איך אפשר לעזור?"),
]

# PAUSE CONTROL.
# Azure on Vapi exposes `speed` and `chunkPlan` and nothing else — no SSML, no
# break tags. So the only pause lever that survives the trip to Vapi is
# punctuation plus rate. Both variants below are reproducible on a real call;
# anything using <break> would not be, so it is deliberately not tested here.
PAUSE = [
    ("pause-a-plain", AVRI, "+0%",
     "שלום, מדבר מיכאל מהומיז. מדובר בתשלום ועד בית של ארבע מאות וחמישים שקלים."),
    ("pause-b-punctuated", AVRI, "-8%",
     "שלום... מדבר מיכאל, מהומיז. מדובר בתשלום ועד בית, של ארבע מאות וחמישים שקלים."),
]


async def say(name, voice, text, rate="+0%"):
    path = os.path.join(OUT, name + ".mp3")
    await edge_tts.Communicate(text, voice, rate=rate).save(path)
    print("  %-32s %-20s %5.1f KB" % (name, voice, os.path.getsize(path) / 1024))


async def main():
    os.makedirs(OUT, exist_ok=True)
    print("writing to voice/samples/  (gitignored — *.mp3 is not committed)\n")
    for name, voice, text in LINES:
        await say(name, voice, text)
    for name, voice, rate, text in PAUSE:
        await say(name, voice, text, rate)
    print("\nOpen voice/listen.html to compare them.")
    print("Judge in this order: accent first, then the number in 3, then the")
    print("vav on ולהתראות in 5. Stop at the first failure — a voice that gets")
    print("the accent wrong cannot be rescued by the later lines.")


if __name__ == "__main__":
    asyncio.run(main())
