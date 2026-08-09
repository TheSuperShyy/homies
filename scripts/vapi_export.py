"""Dump the whole Vapi account to a file, so it can be rebuilt somewhere else.

    python scripts/vapi_export.py            # write docs/handover/vapi-export.json
    python scripts/vapi_export.py --show     # print the inventory, write nothing

WHY THIS EXISTS ALONGSIDE vapi_sync.py
`vapi_sync.py` rebuilds the two debt assistants from the markdown, and that is
the real portable artefact — prompts, tools and config all come from files in
this repo. This script covers what the markdown does not: assistants nobody
maintains a document for, the exact config Vapi ended up storing after the
dashboard was edited by hand, and every id that other files point at.

Treat the export as a *record*, not a restore path. Vapi mints new ids on
create, so nothing here can be pushed back verbatim into a different account.
The rebuild is `docs/handover/new-vapi.md`.

WHAT IS DELIBERATELY NOT IN IT
Server header values are redacted. **That stopped being theoretical on 8 Aug**:
every assistant now carries `x-homies-secret` on its `server` block for the
end-of-call report, so the dump would otherwise put TOOL_SECRET into a committed
file. This was written when the headers were empty, on the reasoning that a file
which is safe only by accident is not safe — which is the whole return on
writing it that way.

The consequence for a rebuild: `<redacted>` is not a value. An account restored
from this export has four assistants that post their end-of-call reports with a
header of the literal string `<redacted>`, get a 401 from the Edge Function, and
throw away every transcript exactly as they did before 8 Aug — silently, because
nothing about a call fails. Re-run `vapi_sync.py --apply`, which reads the real
secret from `.env`, rather than restoring the server block from here. See
`docs/handover/new-vapi.md`.
"""

import json
import os
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "handover", "vapi-export.json")
API = "https://api.vapi.ai"

# Everything an account can hold that we might have put something in. /tool,
# /squad and /workflow are empty today and are fetched anyway — an export that
# only looks where it expects to find things is how a resource goes missing in
# a migration.
#
# 7 Aug: /credential added, and it is the most important entry in this list.
# The Hebrew voice is Cartesia, which needs a Cartesia API key registered on the
# account — the account holds exactly one credential and that is it. A new
# account has none, so the voice falls back to vapi Elliot: an English voice
# reading Hebrew with an American accent. Nothing errors, nothing logs, and
# Vapi's own cost records report `voiceId: Elliot` for that provider whatever
# was actually spoken, so billing will not catch it either. The only symptom is
# that it sounds wrong to somebody who speaks Hebrew.
#
# Values are not returned by the API and would be redacted here if they were.
# What this records is WHICH provider keys have to exist, which is the part
# that goes missing.
COLLECTIONS = ["assistant", "phone-number", "tool", "squad", "workflow", "file",
               "credential"]


def load_key():
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        sys.exit(".env not found")
    for line in open(path, encoding="utf-8"):
        if line.strip().startswith("VAPI_PRIVATE_KEY="):
            return line.strip().split("=", 1)[1]
    sys.exit("VAPI_PRIVATE_KEY missing from .env")


def get(path, key):
    req = urllib.request.Request(
        API + path,
        # Cloudflare 403s urllib's default User-Agent. Any real-looking string
        # gets through; this one says who it is.
        headers={"Authorization": "Bearer " + key, "User-Agent": "homies/1.0"},
    )
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as exc:
        return {"_error": "HTTP %s" % exc.code, "_body": exc.read().decode()[:300]}


def redact(node):
    """Blank every server header value, at any depth."""
    if isinstance(node, dict):
        return {
            k: ({kk: "<redacted>" for kk in v} if k == "headers" and isinstance(v, dict)
                else redact(v))
            for k, v in node.items()
        }
    if isinstance(node, list):
        return [redact(v) for v in node]
    return node


def label(item):
    return (item.get("name")
            or item.get("number")
            or (item.get("function") or {}).get("name")
            or item.get("id", "?"))


def main():
    key = load_key()
    show_only = "--show" in sys.argv

    export = {}
    for name in COLLECTIONS:
        data = get("/" + name, key)
        export[name] = redact(data)
        if isinstance(data, list):
            print("%-13s %d" % (name, len(data)))
            for item in data:
                print("    %s  %s" % (item.get("id", "?"), label(item)))
        else:
            print("%-13s %s" % (name, data.get("_error", "not a list")))

    if show_only:
        print("\n--show: nothing written.")
        return

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(export, fh, ensure_ascii=False, indent=2, sort_keys=True)
    print("\nwrote %s" % os.path.relpath(OUT, ROOT))
    print("Rebuild instructions: docs/handover/new-vapi.md")


if __name__ == "__main__":
    main()
