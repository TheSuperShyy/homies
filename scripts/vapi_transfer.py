#!/usr/bin/env python
"""Clone the whole Vapi setup onto another account, and repoint the repo at it.

    python scripts/vapi_transfer.py --balance
    python scripts/vapi_transfer.py --preflight
    python scripts/vapi_transfer.py --to VAPI_PRIVATE_KEY_NEW --dry
    python scripts/vapi_transfer.py --to VAPI_PRIVATE_KEY_NEW --apply
    python scripts/vapi_transfer.py --to VAPI_PRIVATE_KEY_OLD --mirror

MOVE OR MIRROR, AND THEY ARE NOT THE SAME OPERATION

`--apply` MOVES: it creates the assistants on the target and rewrites every id in
the repo to point at them. It refuses a target that already holds Homies
assistants, because creating by name again gives duplicates and no error.

`--mirror` KEEPS IN STEP: it matches by name and overwrites in place, so the ids
on the target do not change, and **it does not touch the repo at all**. That is
the whole difference — a mirror is a second copy of the agents that is not the
one being called. Account 4 is exactly this: the account we moved away from on
12 Aug, kept current so it can be picked up if the live one is lost.

A mirror creates only what is missing. Anything on the target that is not on the
source is left alone; anything with a matching name is replaced whole, tools and
server blocks included, so the two accounts really do behave the same.

`--to` names the **variable in .env** holding the target account's private key,
never the key itself. A key pasted on a command line lands in shell history, and
this repository is public.

WHAT THIS DOES THAT THE RUNBOOK DID BY HAND

`docs/handover/new-vapi.md` describes a seven-step move and has been walked three
times — 7, 11 and 12 August. Step 6, "repoint everything that hardcodes an id",
is the one that breaks things, because a wrong assistant id does not error: the
call connects to the wrong agent, or to one that no longer exists. Ten files
carry ids. Doing that by hand three times is how the demo page spent a day
calling account 3 after everything else had moved.

So: create the credential, copy the four assistants, rewrite every id in the
repo from the map that creating them produced, and print what is left.

WHY IT COPIES ALL FOUR RATHER THAN REBUILDING THE HEBREW PAIR

The runbook rebuilds the Hebrew assistants from markdown and regenerates the
English twins from the Hebrew, which is right when the point is to get a working
account. It is not right when the point is a *clone*: a rebuild produces what the
repo says should be live, and this produces what **is** live. Those differ
whenever somebody has touched the dashboard, and finding out afterwards that they
differed is the failure this exists to prevent. Rebuild deliberately, later, with
`vapi_sync.py` and `vapi_en.py` — not as a side effect of a migration.

THE THREE THINGS THAT DO NOT COME ACROSS

1. **The public key.** `GET /org` returns 401 to a private key, so there is no
   way to read it. Copy it from Dashboard → Organization → API Keys into
   `VAPI_PUBLIC_KEY` and into `web/index.html`. **This is the only manual step**,
   and without it the demo page loads and no call ever starts.
2. **Call history, transcripts and recordings.** They stay. Recordings are
   deleted after 14 days regardless, so pull anything wanted first.
3. **Riley.** Every new account arrives with its own; the id differs each time.

The Cartesia credential DOES come across, which is new — `CARTESIA_API_KEY` is
in `.env`, so the credential is created rather than left as blocker 1 of the
runbook. That blocker was the dangerous one: without it the Hebrew voice falls
back to `vapi/Elliot` and the agent talks in an American accent, silently.
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
API = "https://api.vapi.ai"

# Vapi returns these and rejects them on create. `latestVersion` is the one that
# is not obvious — the 400 names the field, which is how it was found.
READ_ONLY = {"id", "orgId", "createdAt", "updatedAt", "isServerUrlSecretSet",
             "latestVersion", "version", "credentialIds"}

# Ours. Anything else on the account is somebody else's and is not touched.
OURS = re.compile(r"^Homies", re.I)

# Every file that hardcodes an assistant id, and it is the list that matters:
# a file missing from here keeps pointing at the old account and nothing says so.
# `web/index.html` is its own git repository (see .gitignore) and still has to be
# edited here, then pushed from inside web/.
ID_FILES = [
    "web/index.html",
    "scripts/vapi_en.py",
    "scripts/vapi_call.py",
    "scripts/vapi_duel.py",
    "scripts/vapi_eval.py",
    "scripts/vapi_mock.py",
    "docs/assistant/debt-followup.md",
    "docs/assistant/demo-inbound.md",
    "docs/assistant/inbound-test-script.md",
    "docs/features/04-interruption-pacing/feature.md",
    ".env",
]


def env():
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        sys.exit("No .env")
    out = {}
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def api(method, path, key, body=None):
    req = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        # Cloudflare 403s urllib's default user-agent on this host.
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "User-Agent": "homies/1.0"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=60).read() or b"{}")


def restore(node, e):
    """Put real values back where the export wrote a placeholder.

    Only reached with --from-export. A tool server block restored with the
    literal string `<redacted>` in its header authenticates as nobody: the Edge
    Function returns 401, and nothing about the call fails — the agent talks, the
    tool silently does nothing, and the resident is told a request was opened.
    """
    if isinstance(node, dict):
        return {k: (e.get("TOOL_SECRET", "") if v == "<redacted>" else restore(v, e))
                for k, v in node.items()}
    if isinstance(node, list):
        return [restore(v, e) for v in node]
    if isinstance(node, str):
        m = re.fullmatch(r"<redacted:(\w+)>", node)
        if m:
            return e.get(m.group(1), node)
        return re.sub(r"<redacted:(\w+)>", lambda x: e.get(x.group(1), x.group(0)), node)
    return node


def source_assistants(e, from_export):
    if from_export:
        path = os.path.join(ROOT, "docs", "handover", "vapi-export.json")
        rows = json.load(open(path, encoding="utf-8"))["assistant"]
        return [restore(a, e) for a in rows if OURS.match(a.get("name", ""))]
    rows = api("GET", "/assistant?limit=100", e["VAPI_PRIVATE_KEY"])
    return [a for a in rows if OURS.match(a.get("name", ""))]


# A UUID that is correctly shaped and belongs to nobody. The point is that it can
# never name a real assistant, so this request can never create a call and can
# never bill — see `balance()`.
NO_SUCH_ASSISTANT = "11111111-2222-4333-8444-555555555555"


def balance(public_key):
    """Whether the account can start a call, and why not when it cannot.

    `GET /org` is 401 to a private key and the public key cannot read anything,
    so the balance was written off as unreadable — the runbook still says so and
    said so for a fortnight. It is readable, from an angle: **Vapi checks the
    wallet BEFORE it looks the assistant up**, so a POST to /call/web naming an
    assistant that does not exist returns the wallet message when the account is
    overdrawn and "assistant not found" when it is not. Nothing is created on
    either path, so this costs nothing and can be run as often as you like.

    WHY IT IS WORTH A FUNCTION
    19 Aug, an afternoon: the demo would not start, the page said
    "Error: [object Object]", and Vapi's call list showed nothing at all,
    because a refused call is never recorded. Every piece of evidence pointed at
    the code that had just changed. The account was eleven cents overdrawn.

    Returns (ok, message).
    """
    try:
        api("POST", "/call/web", public_key, {"assistantId": NO_SUCH_ASSISTANT})
        return True, "a call was created, which should be impossible"
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read() or b"{}")
        except Exception:
            return False, "HTTP %s, unreadable body" % exc.code
        msg = body.get("message")
        if isinstance(msg, list):
            msg = "; ".join(str(m) for m in msg)
        msg = str(msg or exc.code)
        # The wallet check fires first, so its message means the account cannot
        # place a call whatever else is right. Anything else here means it can.
        if "wallet" in msg.lower() or "credit" in msg.lower():
            return False, msg
        return True, "in credit (refused for the expected reason: %s)" % msg


def preflight(e):
    pub = e.get("VAPI_PUBLIC_KEY")
    if pub:
        ok, msg = balance(pub)
        print("BALANCE  %s" % ("OK — " if ok else "BLOCKED — ") + msg)
    else:
        print("BALANCE  VAPI_PUBLIC_KEY not in .env, cannot check")
    print()

    print("SOURCE")
    try:
        rows = api("GET", "/assistant?limit=100", e["VAPI_PRIVATE_KEY"])
    except urllib.error.HTTPError as exc:
        sys.exit("  source key rejected: HTTP %s" % exc.code)
    ours = [a for a in rows if OURS.match(a.get("name", ""))]
    for a in ours:
        m = a.get("model") or {}
        print("  %-32s %6d chars  %s/%s  %d tools" % (
            a["name"][:32], len((m.get("messages") or [{}])[0].get("content") or ""),
            a["voice"]["provider"], a["transcriber"]["provider"],
            len(m.get("tools") or [])))
    other = [a["name"] for a in rows if not OURS.match(a.get("name", ""))]
    print("  not ours, will not be copied: %s" % (", ".join(other) or "none"))

    creds = api("GET", "/credential", e["VAPI_PRIVATE_KEY"])
    print("  credentials: %s" % ", ".join("%s (%s)" % (c["provider"], c["name"])
                                          for c in creds) or "none")

    print("\nWHAT IS NEEDED TO REBUILD IT")
    need = {"CARTESIA_API_KEY": "the Hebrew voice — without it, a silent American accent",
            "TOOL_SECRET": "the tool server header",
            "N8N_WEBHOOK_SECRET": "the same value, used by the tool webhooks"}
    for k, why in need.items():
        print("  %-22s %-8s %s" % (k, "present" if e.get(k) else "MISSING", why))

    print("\nFILES THAT HARDCODE AN ID")
    ids = {a["id"]: a["name"] for a in ours}
    for f in ID_FILES:
        p = os.path.join(ROOT, f)
        if not os.path.exists(p):
            print("  %-46s MISSING FROM DISK" % f)
            continue
        text = open(p, encoding="utf-8", errors="replace").read()
        n = sum(text.count(i) for i in ids)
        print("  %-46s %d id(s)" % (f, n))

    print("\nCANNOT BE AUTOMATED")
    print("  VAPI_PUBLIC_KEY — GET /org is 401 to a private key. Copy it from")
    print("  Dashboard -> Organization -> API Keys, into .env and web/index.html.")
    print("  (The BALANCE line above IS readable, via /call/web — see balance().)")


def repoint(mapping, apply):
    """Rewrite every old id to its new one, and say what changed."""
    total = 0
    for f in ID_FILES:
        p = os.path.join(ROOT, f)
        if not os.path.exists(p):
            print("  %-46s missing, skipped" % f)
            continue
        text = open(p, encoding="utf-8", errors="replace").read()
        n = sum(text.count(old) for old in mapping)
        if not n:
            continue
        for old, new in mapping.items():
            text = text.replace(old, new)
        if apply:
            open(p, "w", encoding="utf-8", newline="\n").write(text)
        total += n
        print("  %-46s %d id(s) %s" % (f, n, "rewritten" if apply else "would change"))
    print("  %d in total" % total)


def mirror(ours, target, var):
    """Make the target's Homies assistants identical to ours, in place.

    Overwrites rather than creates, so nothing is duplicated and no id moves.
    Anything on the target that is not one of ours is not read, not written and
    not counted — a mirror is not a takeover of somebody else's account.
    """
    existing = {a["name"]: a for a in api("GET", "/assistant?limit=100", target)
                if OURS.match(a.get("name", ""))}

    print("MIRROR  current account -> %s" % var)
    print("  the repo is NOT repointed. The live account stays the live one.")
    for a in ours:
        there = existing.get(a["name"])
        m = a.get("model") or {}
        mine = len((m.get("messages") or [{}])[0].get("content") or "")
        if there:
            tm = there.get("model") or {}
            theirs = len((tm.get("messages") or [{}])[0].get("content") or "")
            print("  overwrite  %-32s %6d -> %6d chars, %d -> %d tools" % (
                a["name"][:32], theirs, mine,
                len(tm.get("tools") or []), len(m.get("tools") or [])))
        else:
            print("  create     %-32s %6d chars" % (a["name"][:32], mine))

    if "--apply" not in sys.argv:
        print("\nPlan only. Add --apply to write.")
        return

    for a in ours:
        body = {k: v for k, v in a.items() if k not in READ_ONLY}
        there = existing.get(a["name"])
        if there:
            made = api("PATCH", "/assistant/" + there["id"], target, body)
            what = "overwritten"
        else:
            made = api("POST", "/assistant", target, body)
            what = "created"
        print("  %-12s %-32s %s" % (what, made["name"][:32], made["id"]))

    print("\nSTILL TO DO BY HAND")
    print("  The public key differs per account and cannot be read through the")
    print("  API. If this mirror is ever promoted to live, take it from")
    print("  Dashboard -> Organization -> API Keys and put it in web/index.html.")


def main():
    argv = sys.argv[1:]
    e = env()

    if "--balance" in argv:
        pub = e.get("VAPI_PUBLIC_KEY")
        if not pub:
            sys.exit("VAPI_PUBLIC_KEY is not in .env")
        ok, msg = balance(pub)
        print(("OK      " if ok else "BLOCKED ") + msg)
        sys.exit(0 if ok else 1)

    if "--preflight" in argv or not argv:
        preflight(e)
        return

    if "--to" not in argv:
        sys.exit(__doc__)
    var = argv[argv.index("--to") + 1]
    target = e.get(var)
    if not target:
        sys.exit("%s is not in .env. Put the new account's private key there first."
                 % var)
    if target == e.get("VAPI_PRIVATE_KEY"):
        sys.exit("%s holds the CURRENT account's key. That would clone onto itself."
                 % var)

    apply = "--apply" in argv
    ours = source_assistants(e, "--from-export" in argv)
    if not ours:
        sys.exit("No Homies assistants found to copy.")

    # Before the collision check below, because a mirror WANTS the collision:
    # the assistants already there are the ones being brought up to date.
    if "--mirror" in argv:
        mirror(ours, target, var)
        return

    # Refuse to run into an account that already has some. Creating by name would
    # give four duplicates and no error, and the repoint below would then pick
    # whichever came back first.
    try:
        existing = [a["name"] for a in api("GET", "/assistant?limit=100", target)
                    if OURS.match(a.get("name", ""))]
    except urllib.error.HTTPError as exc:
        sys.exit("target key rejected: HTTP %s" % exc.code)
    # A dry run reports the collision and carries on: the plan is what you came
    # for, and being told only "refusing" says nothing about what the move would
    # do. --apply is where it actually stops.
    if existing:
        note = "Target already holds: %s" % ", ".join(existing)
        if apply:
            sys.exit(note + "\nRefusing: creating by name again would give "
                     "duplicates and no error, and the repoint below would then pick "
                     "whichever came back first. Delete them, or use a fresh account.")
        print("  !! %s" % note)
        print("  !! --apply would refuse. This is a plan only.")

    print("PLAN  %s -> %s" % ("current account", var))
    creds = api("GET", "/credential", target)
    have_cartesia = any(c["provider"] == "cartesia" for c in creds)
    print("  cartesia credential: %s" % ("already there" if have_cartesia
                                         else "will be created from CARTESIA_API_KEY"))
    if not have_cartesia and not e.get("CARTESIA_API_KEY"):
        sys.exit("  CARTESIA_API_KEY missing from .env. Stopping: a Hebrew assistant "
                 "without it falls back to an American voice and nothing reports it.")
    for a in ours:
        print("  create  %s" % a["name"])

    if not apply:
        print("\nRepoint that would follow:")
        repoint({a["id"]: "<new-id-for-%s>" % a["name"] for a in ours}, apply=False)
        print("\nDry run. Re-run with --apply.")
        return

    if not have_cartesia:
        c = api("POST", "/credential", target,
                {"provider": "cartesia", "apiKey": e["CARTESIA_API_KEY"],
                 "name": "Cartesia (Hebrew TTS)"})
        print("  credential created: %s" % c["id"])

    mapping = {}
    for a in ours:
        body = {k: v for k, v in a.items() if k not in READ_ONLY}
        made = api("POST", "/assistant", target, body)
        mapping[a["id"]] = made["id"]
        print("  created  %-32s %s" % (made["name"][:32], made["id"]))

    print("\nRepointing the repo:")
    repoint(mapping, apply=True)

    print("\nSTILL TO DO BY HAND")
    print("  1. VAPI_PRIVATE_KEY in .env -> the new key (this script did not")
    print("     move it, so the old account stays reachable until you say so).")
    print("  2. VAPI_PUBLIC_KEY in .env AND in web/index.html -> from the")
    print("     dashboard. Nothing can read it. Without it no web call starts.")
    print("  3. cd web && git push   (its own repo, its own Vercel deploy)")
    print("  4. python scripts/vapi_export.py --archive <label>")
    print("  5. Place one web call in each language before believing any of it.")


if __name__ == "__main__":
    main()
