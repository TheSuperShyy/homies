# -*- coding: utf-8 -*-
r"""Change ONLY the voice on the live Hebrew assistants, touching nothing else.

    python scripts/vapi_set_voice.py                  # show live vs intended
    python scripts/vapi_set_voice.py --apply
    python scripts/vapi_set_voice.py --voice a976c076-3e31-4bf2-a178-8c3ce3d52b2a --apply   # rollback to Eyal

WHY NOT `vapi_sync.py <agent> --apply`, WHICH IS THE OBVIOUS ANSWER

Because it is all-or-nothing, and on 31 Aug both of its targets would have
carried a second change nobody asked for:

  debt     re-pushing a prompt is a decision about the prompt, not a step in
           changing a voice (on 31 Aug the repo and the live prompt differed by
           ~500 chars; on 16 Sep the prompt was rewritten open, a decision of
           its own, pushed with vapi_sync.py debt --apply).
  inbound  worse. It builds from `docs/assistant/demo-inbound.md` at 19,978
           chars while the live assistant carries ~35,600. Running it would
           replace the production prompt with a demo one. It also hardcodes
           `cartesia_voice = a976c076` (Eyal) and never consults
           CARTESIA_VOICE_ID, so it cannot install a clone even if you wanted
           the rest.

So this script does the one thing: PATCH `voice` -- the voice id and, since
15 Sep, its volume (`--volume N`, or CARTESIA_VOLUME in .env). Same surgical rule as
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
#
# RESOLVED BY NAME SINCE 16 SEP, with the ids only as a fallback. They were bare
# constants until the demo account arrived: the live wallet hit -$0.03 and
# refused every call, a fresh account's keys went into .env, `vapi_sync.py`
# created the two assistants there (it has always matched by NAME), and this
# script then 404'd on ids belonging to an account the key can no longer see.
# A hardcoded id is a fact about one account; the name is a fact about the
# agent, and this script's whole job is to run straight after that sync.
NAMES = ["Debt Follow-up (he)", "Inbound Intake (he)"]
FALLBACK_IDS = {
    "Debt Follow-up (he)": "14d502fc-95a9-4fb1-8d93-944dd7e00211",
    "Inbound Intake (he)": "8894680c-03af-43f6-a75b-f828872833cc",
}


def targets(vapi_key):
    """(label, id) per Hebrew assistant, from whatever account the key opens."""
    try:
        live = vapi("GET", "/assistant?limit=100", vapi_key)
    except SystemExit:
        live = []
    found = []
    for name in NAMES:
        hit = next((a for a in live
                    if name.lower() in str(a.get("name") or "").lower()), None)
        if hit:
            found.append((name, hit["id"]))
        elif FALLBACK_IDS.get(name):
            found.append((name, FALLBACK_IDS[name]))
    if not found:
        sys.exit("No Hebrew assistant on this account, by name or by id. "
                 "Run `vapi_sync.py inbound --apply` first.")
    return found

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
    # Volume: the flag wins, then .env, then the builder's default (1.4).
    if "--volume" in args:
        os.environ["CARTESIA_VOLUME"] = args[args.index("--volume") + 1]
    else:
        os.environ.setdefault("CARTESIA_VOLUME", env_value("CARTESIA_VOLUME") or "1.4")
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
    want_vol = voice["generationConfig"]["volume"]
    print("volume     : %s   (0.5-2.0; 1 is Cartesia's default)" % want_vol)

    def guard_count(v):
        return len((((v.get("chunkPlan") or {}).get("formatPlan") or {}).get("replacements")) or [])
    want_fb = guard_count(voice["fallbackPlan"]["voices"][0])

    # "Same" means the voice id, the model, the volume AND the fallback's guard:
    # a volume-only change has to be visible here, or this script says "nothing
    # to do" and ships it to nobody; and a fallback that lost its replacements
    # (15 Sep) has to show up as work, or Elliot reads tool names aloud.
    changed = []
    for label, aid in targets(vapi_key):
        lv = vapi("GET", "/assistant/" + aid, vapi_key).get("voice") or {}
        cur = lv.get("voiceId", "")
        cur_vol = (lv.get("generationConfig") or {}).get("volume")
        cur_fb = guard_count(((lv.get("fallbackPlan") or {}).get("voices") or [{}])[0])
        same = (cur == vid and lv.get("model") == voice["model"]
                and cur_vol == want_vol and cur_fb == want_fb)
        print("\n%-22s %s" % (label, aid))
        print("  live voice : %s%s" % (cur, "   (already correct)" if cur == vid else ""))
        print("  live model : %s%s" % (lv.get("model", "-"),
                                      "" if lv.get("model") == voice["model"] else "   -> " + voice["model"]))
        print("  live volume: %s%s" % ("none" if cur_vol is None else cur_vol,
                                      "" if cur_vol == want_vol else "   -> %s" % want_vol))
        print("  fallback   : %d replacements%s" % (cur_fb, "" if cur_fb == want_fb else "   -> %d" % want_fb))
        if not same:
            if cur != vid:
                print("  -> voice becomes %s" % vid)
            changed.append((label, aid, cur, cur_vol))

    if not changed:
        print("\nNothing to do. Both assistants already carry that voice, model and volume.")
        return 0

    if not apply_it:
        print("\nDry run. Re-run with --apply to write it.")
        print("Only the `voice` field is sent. Prompts, models and tools are untouched.")
        return 0

    for label, aid, before, before_vol in changed:
        vapi("PATCH", "/assistant/" + aid, vapi_key, {"voice": voice})
        after = (vapi("GET", "/assistant/" + aid, vapi_key).get("voice") or {})
        got = after.get("voiceId", "")
        got_vol = (after.get("generationConfig") or {}).get("volume")
        print("\n%s" % label)
        print("  voice  %s -> %s   %s" % (before, got, "OK" if got == vid else "MISMATCH"))
        print("  volume %s -> %s   %s" % ("none" if before_vol is None else before_vol, got_vol,
                                          "OK" if got_vol == want_vol else "MISMATCH"))
        fb = (after.get("fallbackPlan", {}).get("voices") or [{}])[0]
        print("  model=%s  replacements=%d  fallback=%s with %d replacements" % (
            after.get("model", "-"), guard_count(after), fb.get("voiceId", "none"), guard_count(fb)))
        if got != vid or got_vol != want_vol or guard_count(fb) != want_fb:
            sys.exit("Read-back does not match what was sent. Stop and check by hand.")

    print("\nWritten and read back. That proves the field is set, not that it sounds\n"
          "right -- a voice Vapi cannot resolve fails silently to Elliot at call time.\n"
          "Place one Hebrew call before calling this done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
