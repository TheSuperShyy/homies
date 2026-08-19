"""Scan what the agent actually said for machinery that escaped into speech.

    python scripts/vapi_leak_check.py            # last 20 calls
    python scripts/vapi_leak_check.py 50         # last 50
    python scripts/vapi_leak_check.py <call-id>  # one call, with its transcript

WHY THIS EXISTS
There are three layers stopping the agent from reading its own paperwork aloud:
the tools carry no free-text parameters to leak, voice_guard.py strips the known
shapes after the model and before the voice, and the prompt tells it not to. The
first two are structural. The third is not, and none of the three can be trusted
without looking at what came out the other end.

So this reads the transcripts back and applies the *same patterns the filter
uses*, imported from the same file, plus a short list of prose give-aways the
filter deliberately cannot touch. Two different severities:

  BLOCKED SHAPE — a filter pattern found in speech. This should be impossible.
                  It means the guard is not attached to that assistant, or the
                  call predates it, or Vapi's per-chunk single-replace let a
                  second identifier through in one chunk. Investigate.

  PROSE         — the model describing its own workings in ordinary words. The
                  filter cannot catch these by design, because the patterns that
                  would also match real speech. This is the prompt's job, and a
                  hit here is a prompt fix, not a bug.

Reads only. Writes nothing, changes nothing.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voice_guard
from voice_guard import PATTERNS, PROSE, checks

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.vapi.ai"

PROSE_NAMES = {name for name, _ in PROSE}
CHECKS = checks()


def load_key():
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        sys.exit(".env not found")
    for line in open(path, encoding="utf-8"):
        if line.strip().startswith("VAPI_PRIVATE_KEY="):
            return line.strip().split("=", 1)[1].strip()
    sys.exit("VAPI_PRIVATE_KEY missing from .env")


def get(path, key):
    req = urllib.request.Request(
        API + path,
        # Cloudflare 403s urllib's default User-Agent on this host.
        headers={"Authorization": "Bearer " + key, "User-Agent": "homies/1.0"},
    )
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read())
    except urllib.error.HTTPError as exc:
        sys.exit("HTTP %s — %s" % (exc.code, exc.read().decode()[:200]))


def spoken(call):
    """Every line the assistant said, in order. Not the resident's.

    Vapi keeps the same conversation twice: a flat `transcript` string with
    "AI:" / "User:" prefixes, and `artifact.messages` with roles. The messages
    are used because the flat string cannot be split reliably when a turn
    contains a newline, and a leak is exactly the kind of turn that does.
    """
    messages = (call.get("artifact") or {}).get("messages") or call.get("messages") or []
    out = []
    for m in messages:
        if m.get("role") in ("bot", "assistant") and m.get("message"):
            out.append(m["message"])
    if not out and call.get("transcript"):
        out = [l[3:].strip() for l in call["transcript"].splitlines()
               if l.startswith("AI:")]
    return out


def scan(text):
    hits = []
    for name, rx in CHECKS:
        for m in re.finditer(rx, text):
            hits.append((name, m.group(0)))
    return hits


def report(call, verbose=False):
    """One line per call, plus every hit. True if anything was found."""
    lines = spoken(call)
    found = [(name, hit, line) for line in lines for name, hit in scan(line)]

    when = (call.get("startedAt") or call.get("createdAt") or "")[:19].replace("T", " ")
    name = (call.get("assistant") or {}).get("name") or call.get("assistantId", "?")[:8]

    if verbose:
        print("\n%s  %s  %s" % (call["id"][:8], when, name))
        for line in lines:
            print("    AI: %s" % line[:150])

    if not found:
        if not verbose:
            print("  ok    %s  %s  %-34s %d turns" % (call["id"][:8], when, name[:34], len(lines)))
        return False

    print("\n  LEAK  %s  %s  %s" % (call["id"][:8], when, name))
    for kind, hit, line in found:
        severity = "PROSE" if kind in PROSE_NAMES else "MACHINERY"
        print("        [%s] %s: %r" % (severity, kind, hit))
        print("        in: %s" % line[:160])
    return True


def main():
    # The check that runs without a call, and the one that would have caught
    # 19 Aug. Everything else here reads transcripts and asks "did machinery
    # get out?"; this asks the opposite and equally important question — "did
    # the filter eat a real sentence?" A leak is heard once and sounds odd. A
    # filter chewing a hole in the agent's commonest sentence happens on every
    # call and reads as the model being broken.
    if "--safe" in sys.argv:
        bad = voice_guard.safe_sentence_failures()
        print("checking %d sentences the agents really say" % len(voice_guard.SAFE_SENTENCES))
        for before, after in bad:
            print("\nDAMAGED  %s" % before)
            print("  became   %s" % after)
        print("\n%d damaged." % len(bad))
        if bad:
            print("A SPOKEN entry in voice_guard.py is eating ordinary speech.")
            print("Three words or more, and it must read as machinery, not English.")
        sys.exit(1 if bad else 0)

    key = load_key()
    arg = sys.argv[1] if len(sys.argv) > 1 else "20"

    if not arg.isdigit():
        call = get("/call/" + arg, key)
        bad = report(call, verbose=True)
        sys.exit(1 if bad else 0)

    calls = get("/call?limit=" + arg, key)
    print("scanning %d calls against %d patterns\n" % (len(calls), len(CHECKS)))

    bad = sum(report(c) for c in calls)
    print("\n%d of %d calls leaked." % (bad, len(calls)))
    if bad:
        print("MACHINERY means the filter did not stop it — check that the")
        print("assistant carries voice.chunkPlan.formatPlan.replacements, and")
        print("whether the call predates them.")
        print("PROSE is a prompt fix: NEVER SPEAK THE MACHINERY.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
