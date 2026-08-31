# -*- coding: utf-8 -*-
r"""Change ONLY the voice on the live Hebrew assistants, touching nothing else.

    python scripts/vapi_set_voice.py                  # show live vs intended
    python scripts/vapi_set_voice.py --apply
    python scripts/vapi_set_voice.py --voice a976c076-3e31-4bf2-a178-8c3ce3d52b2a --apply   # rollback to Eyal

WHY NOT `vapi_sync.py <agent> --apply`, WHICH IS THE OBVIOUS ANSWER

Because it is all-or-nothing, and on 31 Aug both of its targets would have
carried a second change nobody asked for:

  debt     the repo's prompt is 54,119 chars against 53,635 live. That drift has
           been left alone on purpose since 30 Aug -- re-pushing a prompt is a
           decision about the prompt, not a step in changing a voice.
  inbound  worse. It builds from `docs/assistant/demo-inbound.md` at 19,978
           chars while the live assistant carries ~35,600. Running it would
           replace the production prompt with a demo one. It also hardcodes
           `cartesia_voice = a976c076` (Eyal) and never consults
           CARTESIA_VOICE_ID, so it cannot install a clone even if you wanted
           the rest.

So this script does the one thing: PATCH `voice`. Same surgical rule as
`n8n_whatsapp_patch.py` -- read live, change the named field, leave every other
byte as found.

IT BUILDS THE VOICE OBJECT WITH vapi_sync's OWN FUNCTION rather than a copy.
`cartesia_voice()` carries the emotion control, the `language: he` guard and the
Elliot fallbackPlan, and each of those has a paragraph of hard-won reasoning
above it. A second implementation here would drift from that within a week.

THE FAILURE MODE IS SILENT, SO THIS READS BACK
A voice id the Cartesia credential cannot see does not error. Vapi falls through
the fallbackPlan to `vapi/Elliot` and the Hebrew agent answers in an American
accent, logging nothing. So: check the voice is visible to the credential's
account BEFORE writing, and re-read the assistant after.
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
sys.path.insert(0, os.path.join(ROOT, "scripts"))
ENV = os.path.join(ROOT, ".env")

import vapi_sync as S                                          # noqa: E402

UA = "curl/8.5.0"

# The two Hebrew assistants. The English twins run `provider: vapi` (Elliot) and
# are deliberately not here: a cloned Hebrew voice reading English is not a thing
# anyone asked for, and they touch Cartesia not at all.
TARGETS = [
    ("Debt Follow-up (he)", "93c7f5e5-4024-49a3-9ab6-141f2b423649"),
    ("Inbound Intake (he)", "7752c6bb-89e9-49f3-aaf4-154ecc65cdff"),
]

FALLBACK = {"provider": "vapi", "voiceId": "Elliot", "version": "2", "language": "he"}


def env_value(name):
    m = re.search(r"^%s=(.*)$" % re.escape(name),
                  io.open(ENV, encoding="utf-8").read(), re.M)
    return m.group(1).strip().strip('"').strip("'") if m else ""


def vapi(method, path, key, body=None):
    req = urllib.request.Request(
        "https://api.vapi.ai" + path, method=method,
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


def visible_to_credential(voice_id, cartesia_key):
    req = urllib.request.Request(
        "https://api.cartesia.ai/voices/%s" % voice_id,
        headers={"X-API-Key": cartesia_key, "Cartesia-Version": "2026-03-01",
                 "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return True, json.loads(r.read().decode("utf-8")).get("name", "?")
    except urllib.error.HTTPError as e:
        return False, "HTTP %s" % e.code


def main():
    args = sys.argv[1:]
    apply_it = "--apply" in args
    vid = args[args.index("--voice") + 1] if "--voice" in args else env_value("CARTESIA_VOICE_ID")
    if not vid:
        sys.exit("No voice. Set CARTESIA_VOICE_ID in .env or pass --voice <id>.")

    vapi_key = env_value("VAPI_PRIVATE_KEY")
    if not vapi_key:
        sys.exit("VAPI_PRIVATE_KEY is not set in .env")

    # WHICH CARTESIA ACCOUNT IS VAPI ACTUALLY USING? Vapi masks the key on read,
    # so this cannot be answered from Vapi. The honest check is: the credential
    # was repointed by scripts/vapi_cartesia_key.py, and whichever .env key can
    # see this voice is the one that has to be on it.
    seen_by = [v for v in ("CARTESIA_YARIV_API_KEY", "CARTESIA_API_KEY")
               if env_value(v) and visible_to_credential(vid, env_value(v))[0]]
    ok_any = bool(seen_by)
    name = visible_to_credential(vid, env_value(seen_by[0]))[1] if ok_any else "?"

    print("voice      : %s  (%s)" % (vid, name))
    print("visible to : %s" % (", ".join(seen_by) if seen_by else "NO KEY IN .env CAN SEE IT"))
    if not ok_any:
        sys.exit("\nREFUSING. No Cartesia key in .env can resolve that voice, so Vapi's\n"
                 "credential almost certainly cannot either -- and it would not error,\n"
                 "it would answer in English. Check the id.")
    print("model      : %s" % os.environ.get("CARTESIA_MODEL", env_value("CARTESIA_MODEL") or "sonic-3.6"))

    # Build with vapi_sync's own builder so the emotion control, language guard
    # and fallbackPlan match exactly what a full sync would have produced.
    os.environ.setdefault("CARTESIA_MODEL", env_value("CARTESIA_MODEL") or "sonic-3.6")
    voice = S.cartesia_voice(vid, FALLBACK)

    changed = []
    for label, aid in TARGETS:
        live = vapi("GET", "/assistant/" + aid, vapi_key)
        cur = (live.get("voice") or {}).get("voiceId", "")
        same = cur == vid
        print("\n%-22s %s" % (label, aid))
        print("  live voice : %s%s" % (cur, "   (already correct)" if same else ""))
        if not same:
            print("  -> becomes : %s" % vid)
            changed.append((label, aid, cur))

    if not changed:
        print("\nNothing to do. Both assistants already carry that voice.")
        return 0

    if not apply_it:
        print("\nDry run. Re-run with --apply to write it.")
        print("Only the `voice` field is sent. Prompts, models and tools are untouched.")
        return 0

    for label, aid, before in changed:
        vapi("PATCH", "/assistant/" + aid, vapi_key, {"voice": voice})
        after = (vapi("GET", "/assistant/" + aid, vapi_key).get("voice") or {})
        got = after.get("voiceId", "")
        print("\n%s" % label)
        print("  %s -> %s   %s" % (before, got, "OK" if got == vid else "MISMATCH"))
        print("  model=%s  fallback=%s" % (
            after.get("model", "-"),
            (after.get("fallbackPlan", {}).get("voices") or [{}])[0].get("voiceId", "none")))
        if got != vid:
            sys.exit("Read-back does not match what was sent. Stop and check by hand.")

    print("\nWritten and read back. That proves the field is set, not that it sounds\n"
          "right -- a voice Vapi cannot resolve fails silently to Elliot at call time.\n"
          "Place one Hebrew call before calling this done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
