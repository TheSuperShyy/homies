# -*- coding: utf-8 -*-
r"""Point Vapi's Cartesia provider credential at a different Cartesia account.

    python scripts/vapi_cartesia_key.py                        # show which key is on it
    python scripts/vapi_cartesia_key.py --to CARTESIA_YARIV_API_KEY --dry
    python scripts/vapi_cartesia_key.py --to CARTESIA_YARIV_API_KEY --apply

`--to` names the .env VARIABLE, never the key itself. A key on a command line
lands in shell history, and this one decides who gets billed.

WHAT THIS DECIDES, WHICH IS MORE THAN IT LOOKS

Vapi synthesises server-side, so it holds its own copy of a Cartesia key as a
provider credential. There is exactly one, `Cartesia (Hebrew TTS)`, and BOTH
Hebrew assistants use it. The English twins run `provider: vapi` (Elliot) and
touch Cartesia not at all.

So this credential is not "the Hebrew voice's key". It is **the whole Cartesia
bill**. Repointing it moves every Hebrew utterance both voice agents ever speak
onto the account behind the new key -- not just a cloned voice, and not just the
assistant you were thinking about when you ran it.

WHY IT GETS REPOINTED AT ALL

A cloned voice is private to the account that created it: the key that made it is
the only key that can play it back. Ido's clones were made on the client's
account because ours answers `402 plan_upgrade_required` and always has. So there
are only ever two ways to put a clone on an agent -- move the credential to the
account that owns the voice, or buy cloning on the account the credential already
holds ($5/month Pro) and re-clone there. Homies chose the first on 31 Aug 2026.

THE FAILURE MODE IF YOU GET THIS WRONG IS SILENT

Point the credential at an account that does not own the voice and nothing
errors. Vapi cannot resolve the voice id, falls through the `fallbackPlan` to
`vapi/Elliot`, and the Hebrew agent answers in an American accent. No log line,
no failed call, no alert. That is why this script reads the credential back after
writing and why it refuses to run against a Cartesia key that cannot see the
voice in `CARTESIA_VOICE_ID`.

ROLLBACK is this same command with the old variable name -- `--to
CARTESIA_API_KEY` puts it back on ours. Nothing else has to be undone.
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

VAPI = "https://api.vapi.ai"
CARTESIA = "https://api.cartesia.ai"
CARTESIA_VERSION = "2026-03-01"

# Vapi 403s Python's default User-Agent behind Cloudflare (error 1010), and the
# failure reads like an auth problem rather than a header one.
UA = "curl/8.5.0"


def load_env(name):
    if not os.path.exists(ENV):
        sys.exit("No .env at %s" % ENV)
    m = re.search(r"^%s=(.*)$" % re.escape(name), io.open(ENV, encoding="utf-8").read(), re.M)
    if not m or not m.group(1).strip():
        sys.exit("%s is not set in .env" % name)
    return m.group(1).strip().strip('"').strip("'")


def vapi(method, path, key, body=None):
    req = urllib.request.Request(
        VAPI + path, method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Authorization": "Bearer " + key, "User-Agent": UA,
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s on %s %s\n%s" % (e.code, method, path,
                                           e.read().decode("utf-8", "replace")[:400]))


def owns_voice(cartesia_key, voice_id):
    """True if this Cartesia account can actually see that voice.

    The whole point of the check: a voice id that 404s here is a Hebrew agent
    that will speak English on the next call and say nothing about it.
    """
    req = urllib.request.Request(
        "%s/voices/%s" % (CARTESIA, voice_id),
        headers={"X-API-Key": cartesia_key, "Cartesia-Version": CARTESIA_VERSION,
                 "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return True, json.loads(r.read().decode("utf-8")).get("name", "?")
    except urllib.error.HTTPError as e:
        return False, "HTTP %s" % e.code


def which_var(key):
    """Report the .env variable a key matches, so the output never prints a key."""
    text = io.open(ENV, encoding="utf-8").read()
    for m in re.finditer(r"^([A-Z0-9_]*CARTESIA[A-Z0-9_]*)=(.*)$", text, re.M):
        if m.group(2).strip().strip('"').strip("'") == key:
            return m.group(1)
    return None


def main():
    args = sys.argv[1:]
    apply_it = "--apply" in args
    tovar = args[args.index("--to") + 1] if "--to" in args else None

    vapi_key = load_env("VAPI_PRIVATE_KEY")
    creds = vapi("GET", "/credential", vapi_key)
    items = creds if isinstance(creds, list) else creds.get("results", [])
    cart = [c for c in items if c.get("provider") == "cartesia"]
    if len(cart) != 1:
        sys.exit("Expected exactly one Cartesia credential, found %d. Refusing to "
                 "guess which one the assistants use." % len(cart))
    cred = cart[0]
    print("credential : %s  %r" % (cred["id"], cred.get("name")))
    print("updated    : %s" % cred.get("updatedAt", "?"))

    voice_id = os.environ.get("CARTESIA_VOICE_ID", "").strip()
    if not voice_id:
        m = re.search(r"^CARTESIA_VOICE_ID=(.*)$", io.open(ENV, encoding="utf-8").read(), re.M)
        voice_id = m.group(1).strip().strip('"') if m else ""

    if not tovar:
        print("\nNo --to given, so nothing to change. Pass the .env variable name of "
              "the\nCartesia account that should be billed, e.g. --to CARTESIA_API_KEY.")
        return 0

    new_key = load_env(tovar)
    print("target     : %s" % tovar)

    if voice_id:
        ok, detail = owns_voice(new_key, voice_id)
        print("voice check: %s -> %s (%s)" % (voice_id[:8], "visible" if ok else "NOT VISIBLE", detail))
        if not ok:
            sys.exit(
                "\nREFUSING. CARTESIA_VOICE_ID is set to a voice this account cannot see.\n"
                "Vapi would not error -- it would fall through to Elliot and the Hebrew\n"
                "agent would answer in an American accent, logging nothing. Either clear\n"
                "CARTESIA_VOICE_ID or point --to at the account that owns the voice.")
    else:
        print("voice check: skipped (CARTESIA_VOICE_ID is unset, so agents use a stock voice)")

    if not apply_it:
        print("\nDry run. Re-run with --apply to write it.")
        print("This moves the WHOLE Cartesia bill for both Hebrew agents to %s." % tovar)
        return 0

    vapi("PATCH", "/credential/" + cred["id"], vapi_key,
         {"provider": "cartesia", "apiKey": new_key})

    # READ IT BACK. A 200 means the PATCH was accepted, not that the credential
    # now holds what you think -- and Vapi masks the key on read, so the honest
    # check is that updatedAt moved plus a real synthesis on the next call.
    after = vapi("GET", "/credential/" + cred["id"], vapi_key)
    print("\nWritten. updatedAt %s -> %s" % (cred.get("updatedAt", "?"), after.get("updatedAt", "?")))
    if after.get("updatedAt") == cred.get("updatedAt"):
        sys.exit("updatedAt did not move. Treat this as NOT applied and check by hand.")
    print("The key itself is masked on read, so this proves a write happened and not\n"
          "which key landed. The real proof is a call in Hebrew that sounds right.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
