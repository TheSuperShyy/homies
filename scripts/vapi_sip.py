# -*- coding: utf-8 -*-
r"""The SIP address Omnitelecom's extension 208 sends calls to: Vapi's free one.

    python scripts/vapi_sip.py              # show the account's SIP addresses (read only)
    python scripts/vapi_sip.py --apply      # create it, then read it back
    python scripts/vapi_sip.py --delete     # undo: remove it from the account

WHAT IT IS

Omni put the bot on extension 208 in Tokomni (18 Oct) and asked for "the address
of the bot's server" plus a username and password (12 Oct). Vapi's answer is a
free SIP address, `provider: vapi`: a `sipUri` that answers an INVITE with the
agent attached to it, and an `authentication` login that the INVITE must pass by
digest. Without that login Vapi accepts ANY username and password, so anyone
who learns the address can ring the agent on our bill. The login is never
optional here.

It answers with the incoming agent. Menu calls ("press 5 for Michael") are then
right; dialer calls reach Michael without the tenant's figures until Omni sends
the external_id header and an `assistant-request` router picks the agent per
call (CONTEXT, 12 Oct). That router is a change to this address, not a new one.

THE LOGIN LIVES IN .env ONLY

VAPI_SIP_USERNAME and VAPI_SIP_PASSWORD (20 to 40 characters each, Vapi's own
limits). If they are missing, --apply makes them and writes them to .env before
it creates anything. Nothing here prints either value: they go to Omni in the
reply, and nowhere else. `SIP_USERNAME`/`SIP_PASSWORD` in .env.example are the
other direction (a provider's trunk login for calls WE place) and are not these.

AN ACCOUNT MOVE LOSES IT

The address belongs to the Vapi account, and `vapi_transfer.py` copies agents,
not phone numbers. After a move: `--delete` with the OLD key in VAPI_PRIVATE_KEY,
then `--apply` with the new one. The URI and the login stay the same, so Omni
changes nothing. The agent is found by NAME, so the new account's id is picked up.
"""

import io
import json
import os
import re
import secrets
import string
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")

VAPI = "https://api.vapi.ai"
# Vapi 403s Python's default User-Agent behind Cloudflare (error 1010), and the
# failure reads like an auth problem rather than a header one.
UA = "curl/8.5.0"

SIP_URI = "sip:homies-omni-208@sip.vapi.ai"
LABEL = "Omni extension 208"          # Vapi caps the name at 40 characters
AGENT = "Inbound Intake (he)"
# The tenth account's id, used only if listing the assistants fails.
FALLBACK_ID = "00d91473-1aaa-4a57-a380-ca5bb2b7f1af"

USER_VAR, PASS_VAR = "VAPI_SIP_USERNAME", "VAPI_SIP_PASSWORD"
# Letters and digits only: a PBX form that chokes on a symbol fails quietly,
# and 32 random alphanumerics are plenty for a digest password.
ALNUM = string.ascii_letters + string.digits


def env_value(name):
    m = re.search(r"^%s=(.*)$" % re.escape(name), io.open(ENV, encoding="utf-8").read(), re.M)
    return m.group(1).strip().strip('"').strip("'") if m else ""


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


def sip_numbers(key):
    got = vapi("GET", "/phone-number?limit=100", key)
    items = got if isinstance(got, list) else got.get("results", [])
    return [n for n in items if n.get("provider") == "vapi"]


def agent_id(key):
    """The incoming agent's id on whatever account the key opens, by name."""
    live = vapi("GET", "/assistant?limit=100", key)
    hit = [a for a in live if (a.get("name") or "").endswith(AGENT)]
    if len(hit) != 1:
        print("Found %d assistants named like %r; using FALLBACK_ID." % (len(hit), AGENT))
        return FALLBACK_ID, "?"
    return hit[0]["id"], hit[0]["name"]


def login():
    """The login from .env, made and written there first if it is missing."""
    user, pw = env_value(USER_VAR), env_value(PASS_VAR)
    if user and pw:
        return user, pw, False
    user = "homies208" + "".join(secrets.choice(ALNUM) for _ in range(16))
    pw = "".join(secrets.choice(ALNUM) for _ in range(32))
    text = io.open(ENV, encoding="utf-8").read()
    with io.open(ENV, "a", encoding="utf-8", newline="\n") as f:
        f.write(("" if text.endswith("\n") else "\n")
                + "\n# The login Omni's extension 208 uses to reach our Vapi SIP address (%s).\n"
                  "# Goes to Omni in the reply and nowhere else. scripts/vapi_sip.py\n"
                  "%s=%s\n%s=%s\n" % (SIP_URI, USER_VAR, user, PASS_VAR, pw))
    return user, pw, True


def show(n, names):
    auth = n.get("authentication") or {}
    print("  %s  %s  %r -> %s  login %s"
          % (n["id"], n.get("sipUri"), n.get("name"),
             names.get(n.get("assistantId"), n.get("assistantId") or "assistant-request"),
             "SET" if auth.get("username") else "NONE (any login is accepted)"))


def main():
    args = sys.argv[1:]
    unknown = [a for a in args if a not in ("--apply", "--delete")]
    if unknown or len(args) > 1:
        sys.exit("Usage: vapi_sip.py [--apply | --delete]")
    key = env_value("VAPI_PRIVATE_KEY")
    if not key:
        sys.exit("VAPI_PRIVATE_KEY is not set in .env")

    names = {a["id"]: a.get("name") for a in vapi("GET", "/assistant?limit=100", key)}
    nums = sip_numbers(key)
    print("SIP addresses on this account: %d" % len(nums))
    for n in nums:
        show(n, names)
    mine = [n for n in nums if (n.get("sipUri") or "").lower() == SIP_URI]

    if "--delete" in args:
        if not mine:
            print("\n%s is not on this account; nothing to delete." % SIP_URI)
            return 0
        vapi("DELETE", "/phone-number/" + mine[0]["id"], key)
        if any((n.get("sipUri") or "").lower() == SIP_URI for n in sip_numbers(key)):
            sys.exit("\nStill listed after the delete. Check by hand.")
        print("\nDeleted %s, and the listing no longer has it." % SIP_URI)
        return 0

    if mine:
        print("\n%s already exists; nothing to create." % SIP_URI)
        return 0

    aid, aname = agent_id(key)
    print("\nWould create %s, %r, answering with %s (%s)." % (SIP_URI, LABEL, aname, aid))
    if "--apply" not in args:
        print("Dry run. Re-run with --apply to create it.")
        return 0

    user, pw, made = login()
    print("login      : %s and %s %s" % (USER_VAR, PASS_VAR,
                                         "made and written to .env" if made else "from .env"))
    made_num = vapi("POST", "/phone-number", key, {
        "provider": "vapi", "name": LABEL, "sipUri": SIP_URI, "assistantId": aid,
        "authentication": {"username": user, "password": pw}})

    # READ IT BACK. The create's 200 says Vapi accepted the body, not that the
    # address answers with the right agent behind the right login.
    after = vapi("GET", "/phone-number/" + made_num["id"], key)
    auth = after.get("authentication") or {}
    checks = [
        ("address", (after.get("sipUri") or "").lower() == SIP_URI),
        ("agent", after.get("assistantId") == aid),
        ("login set", bool(auth.get("username"))),
        ("username matches .env", auth.get("username") == user),
    ]
    print("\nCreated %s (status %s)" % (after["id"], after.get("status", "?")))
    for label, ok in checks:
        print("  %-22s %s" % (label, "ok" if ok else "NO"))
    if not all(ok for _, ok in checks):
        sys.exit("A check failed. Treat the address as NOT ready; --delete undoes it.")
    print("The password is not returned on read, so only a real call proves it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
