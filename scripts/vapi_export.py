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

    python scripts/vapi_export.py --check    # re-scan what is on disk, write nothing
    python scripts/vapi_export.py --archive account5-18aug   # keep a dated copy too

WHAT IS DELIBERATELY NOT IN IT
Server header values are redacted, and since 18 Aug so is **every value in
`.env`, wherever it appears**. Blanking a field called `headers` is a list of
names, and a list of names misses the field somebody adds next month; matching
on the values themselves cannot. The write is then refused outright if any
`.env` value survived, because a backup that leaks the secret is worse than no
backup — it looks like diligence. `--check` re-runs that scan over every export
already on disk.

**That stopped being theoretical on 8 Aug**:
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
import re
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


# A value shorter than this is not matched. Without the floor a short .env entry
# — a port, a region, a two-letter flag — matches inside every id in the file and
# shreds the export into placeholder confetti.
MIN_SECRET = 12

# Two things in .env are NOT secrets, and treating them as such is not the safe
# direction — it is the useless one. `SUPABASE_URL` is public by design: it is
# compiled into the dashboard's browser bundle on every build. Flagging it as a
# leak means the next person reads six warnings, finds all six harmless, and
# stops reading the warnings. A check nobody believes protects nothing.
#
# So: a plain http(s) URL with no credentials in it, and a bare uuid, are
# identifiers. Everything else in .env is presumed to open something.
#
# The URL test deliberately requires no `@`. A postgres DSN is also a URL, and
# `SUPABASE_DB_URL` carries the database password in its userinfo — that one is
# a secret wearing a URL's clothes, and it is the single most dangerous value in
# the file.
PLAIN_URL = re.compile(r"^https?://[^@\s]+$")
BARE_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def is_secret(value):
    return not (PLAIN_URL.match(value) or BARE_UUID.match(value))


def secrets():
    """Every value in .env that opens something, longest first so the longest wins."""
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        sys.exit(".env not found — cannot redact without knowing what is secret.")
    found = {}
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            v = v.strip().strip('"').strip("'")
            if len(v) >= MIN_SECRET and is_secret(v):
                found[k.strip()] = v
    return dict(sorted(found.items(), key=lambda kv: -len(kv[1])))


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


def scrub(text, known):
    """The second pass, and the one that does not depend on guessing field names.

    Named placeholders rather than a bare <redacted>: `<redacted:VAPI_PUBLIC_KEY>`
    tells a reader which value to put back, which a row of identical blanks does
    not. It also surfaces things worth knowing — this is how the tool secret and
    N8N_WEBHOOK_SECRET turned out to be the same string.
    """
    for name, value in known.items():
        text = text.replace(value, "<redacted:%s>" % name)
    return text


def leaks(text, known):
    return sorted(name for name, value in known.items() if value in text)


def label(item):
    return (item.get("name")
            or item.get("number")
            or (item.get("function") or {}).get("name")
            or item.get("id", "?"))


def main():
    argv = sys.argv[1:]
    known = secrets()

    if "--check" in argv:
        folder = os.path.dirname(OUT)
        bad = 0
        for name in sorted(os.listdir(folder)):
            if not name.startswith("vapi-export") or not name.endswith(".json"):
                continue
            found = leaks(open(os.path.join(folder, name), encoding="utf-8").read(), known)
            print("  %-46s %s" % (name, "LEAKS " + ", ".join(found) if found else "clean"))
            bad += len(found)
        sys.exit(bad and "\n%d leak(s) on disk. Do not commit." % bad or 0)

    key = load_key()
    show_only = "--show" in argv

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

    text = scrub(json.dumps(export, ensure_ascii=False, indent=2, sort_keys=True), known)
    survived = leaks(text, known)
    if survived:
        sys.exit("REFUSING TO WRITE. These .env values survived redaction: %s"
                 % ", ".join(survived))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    targets = [OUT]
    # The dated copies (vapi-export-account3-11aug.json and friends) were made by
    # hand each time, which means they were made when somebody remembered. This
    # writes both in one run.
    if "--archive" in argv:
        i = argv.index("--archive")
        if i + 1 >= len(argv):
            sys.exit("--archive needs a label, e.g. --archive account5-18aug")
        targets.append(OUT.replace(".json", "-%s.json" % argv[i + 1]))

    for path in targets:
        open(path, "w", encoding="utf-8", newline="\n").write(text + "\n")
        print("\nwrote %s" % os.path.relpath(path, ROOT))
    print("Redacted %d .env values. `--check` re-scans before you commit." % len(known))
    print("Rebuild instructions: docs/handover/new-vapi.md")


if __name__ == "__main__":
    main()
