"""Measure what a caller actually waits for, from Vapi call logs.

    python scripts/vapi_latency.py                 # last 10 calls, summary
    python scripts/vapi_latency.py --turns         # every turn of the newest call
    python scripts/vapi_latency.py --assistant en  # only the English twin

WHY NOT THE DASHBOARD NUMBER
Vapi's cost/latency panel adds up transcriber + model + voice and calls that the
latency. On 4 Aug that read ~1,600ms while the agent felt like it took three
seconds to answer, and both were true: the panel does not include endpointing,
which is the wait between the caller falling silent and the agent deciding they
have finished. onNoPunctuationSeconds was 1.8, so most turns spent nearly two
seconds in a stage the panel does not show.

WHAT THIS MEASURES INSTEAD
For every bot turn: the gap between the caller's last word ending and the bot's
first word starting. Endpointing, transcription, model and speech synthesis, all
of it, as experienced. This is the number to hold against the PRD's <800ms.

It is derived from transcript timestamps rather than instrumentation, so treat
it as accurate to a few tens of milliseconds and meaningful in aggregate. The
median is the honest headline; the max is usually one turn where the caller
trailed off and the endpointing timer ran to the end.
"""

import json
import os
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAMES = {
    "en": "Homies — Debt Follow-up (en)",
    "he": "Homies — Debt Follow-up (he)",
    "inbound": "Homies — Inbound Intake (he)",
}


def api(path):
    env = dict(
        l.strip().split("=", 1)
        for l in open(os.path.join(ROOT, ".env"), encoding="utf-8")
        if l.strip() and not l.startswith("#") and "=" in l
    )
    req = urllib.request.Request(
        "https://api.vapi.ai" + path,
        headers={
            "Authorization": "Bearer " + env["VAPI_PRIVATE_KEY"].strip(),
            # Cloudflare 403s urllib's default user-agent on this host.
            "User-Agent": "homies/1.0",
        },
    )
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def who(call, index):
    """The list endpoint returns assistantId but not the assistant, so resolve
    names once up front rather than fetching each call individually."""
    a = call.get("assistant") or {}
    return a.get("name") or index.get(call.get("assistantId"), "?")


def gaps(call):
    """(seconds-from-start, wait, what the bot then said) per bot turn.

    Vapi emits a bot turn for the first message too. It is excluded: nobody was
    waiting for it, so counting it would flatter the average.
    """
    msgs = [m for m in (call.get("messages") or []) if m.get("role") in ("user", "bot")]
    out = []
    for prev, cur in zip(msgs, msgs[1:]):
        if prev["role"] != "user" or cur["role"] != "bot":
            continue
        end = prev.get("endTime") or (prev.get("time", 0) + prev.get("duration", 0))
        wait = (cur.get("time", 0) - end) / 1000.0
        # Overlaps go negative when the bot barges in; they are real but they are
        # not waiting, and averaging them in would hide the delay we are hunting.
        if wait >= 0:
            out.append((cur.get("secondsFromStart", 0), wait, cur.get("message", "")))
    return out


def pct(xs, p):
    if not xs:
        return 0.0
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round((len(xs) - 1) * p)))]


def summarise(label, waits):
    if not waits:
        print("  %-28s no measurable turns" % label)
        return
    print("  %-28s turns %2d   median %5.0fms   p90 %5.0fms   max %5.0fms" % (
        label, len(waits), pct(waits, 0.5) * 1000, pct(waits, 0.9) * 1000, max(waits) * 1000))


def main():
    want = None
    if "--assistant" in sys.argv:
        want = NAMES.get(sys.argv[sys.argv.index("--assistant") + 1])

    index = {a["id"]: a["name"] for a in api("/assistant?limit=100")}
    calls = api("/call?limit=20")
    calls = [c for c in calls if (c.get("messages") or [])]
    if want:
        calls = [c for c in calls if who(c, index) == want]
    if not calls:
        sys.exit("No calls with transcripts found.")

    if "--turns" in sys.argv:
        c = calls[0]
        print("call        :", c["id"])
        print("assistant   :", who(c, index))
        print("started     :", c.get("startedAt"))
        print("\n   at      waited   the agent then said")
        for at, wait, said in gaps(c):
            flag = "  <-- over 2s" if wait > 2 else ""
            print("  %5.1fs   %5.0fms   %s%s" % (at, wait * 1000, said[:58], flag))
        w = [g[1] for g in gaps(c)]
        print()
        summarise("this call", w)
        return

    print("Caller stops speaking -> agent starts speaking. Endpointing included.")
    print("PRD section 8 target: <800ms.\n")
    for c in calls[:10]:
        w = [g[1] for g in gaps(c)]
        label = "%s %s" % (c["id"][:8], who(c, index)[:22])
        summarise(label, w)

    everything = [g[1] for c in calls[:10] for g in gaps(c)]
    print()
    summarise("ALL CALLS", everything)


if __name__ == "__main__":
    main()
