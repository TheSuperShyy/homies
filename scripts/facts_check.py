# -*- coding: utf-8 -*-
"""Prove the two channels still say the same thing about Homies.

Fourteen facts — hours, contacts, what the fee covers, response times, the
common-versus-private property line — are stated by both the WhatsApp bot and
the inbound voice agent. `docs/knowledge/homies.md` is the master; the two
prompts each carry their own copy because neither runtime can read a third file
at answer time.

    python scripts/facts_check.py

Exit 0 when every fact is present in both, non-zero with a list when it is not.

WHY A CHECKER AND NOT ONE SHARED STRING. The prompts cannot share text: the
WhatsApp bot ships through n8n and the voice agent through vapi_sync.py, and
they do not even want the same characters — `077-6687949` is right in a chat
window a resident copies from, and is the exact input that broke the voice on
30 Aug. So the copies are deliberate and the drift is what gets caught.

WHAT THIS DOES NOT CHECK: that the facts are true. Nobody in this repo can
verify the office hours. It checks that the two channels agree, which is the
failure that would otherwise reach a resident as two different answers.
"""

import io
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MASTER = "docs/knowledge/homies.md"
WHATSAPP = "docs/features/11-whatsapp-bot/prompt.md"
VOICE = "docs/assistant/demo-inbound.md"

# Only the fenced block ships to Vapi — everything else in that file is
# documentation the model never sees, so a fact sitting outside it is a fact the
# agent does not have. Same regex as vapi_sync.py:624.
VOICE_FENCE = r"## System prompt\s*\n+````\s*\n(.*?)\n````"

# The email is the one fact deliberately absent from the voice prompt: a Hebrew
# voice mangles Latin characters and nobody can reconstruct a mangled address.
# Checked in the negative — its presence would be the bug.
NEVER_SPOKEN = "Office@homies-management.co.il"


def read(path):
    return io.open(os.path.join(ROOT, path), encoding="utf-8").read()


def flat(s):
    """Whitespace-insensitive, because both prompts wrap their prose."""
    return re.sub(r"\s+", " ", s).strip()


def facts():
    """The master table: [(key, written, spoken)]."""
    block = re.search(r"```facts\s*\n(.*?)\n```", read(MASTER), re.S)
    if not block:
        sys.exit("No ```facts block in " + MASTER)
    out = []
    for line in block.group(1).split("\n"):
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split("::")]
        if len(parts) != 3:
            sys.exit("Malformed row (needs two '::'): " + line)
        key, written, spoken = parts
        # `=` is the common case: the fact is ordinary Hebrew and needs no
        # second rendering. `-` means it is never said aloud at all.
        out.append((key, written, written if spoken == "=" else spoken))
    return out


def main():
    rows = facts()
    whatsapp = flat(read(WHATSAPP))

    voice_doc = read(VOICE)
    fence = re.search(VOICE_FENCE, voice_doc, re.S)
    if not fence:
        sys.exit("Could not find the system prompt fence in " + VOICE)
    voice = flat(fence.group(1))

    bad = []
    for key, written, spoken in rows:
        if flat(written) not in whatsapp:
            bad.append((key, "whatsapp", written))
        if spoken == "-":
            continue
        if flat(spoken) not in voice:
            bad.append((key, "voice", spoken))

    if NEVER_SPOKEN in voice:
        bad.append(("office_email", "voice", "present, and must not be — see " + MASTER))

    print("%d facts, %s" % (len(rows), MASTER))
    for key, where, value in bad:
        print("  MISSING  %-18s %-9s %s" % (key, where, value[:70]))
    if bad:
        print("\n%d missing. Edit the prompt, not the master, unless the fact "
              "itself changed." % len(bad))
        return 1
    print("  both channels agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
