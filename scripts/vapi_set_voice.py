# -*- coding: utf-8 -*-
r"""Change ONLY the voice on the live Hebrew assistants, touching nothing else.

    python scripts/vapi_set_voice.py                  # show live vs intended, both agents
    python scripts/vapi_set_voice.py --apply
    python scripts/vapi_set_voice.py --agent inbound --apply               # one agent (AGENT_VOICE)
    python scripts/vapi_set_voice.py --agent inbound --voice ba765d50-19c6-4b3e-bc15-9de3b45f82f7 --plain --apply
                                                      # the incoming line back to the 31 Aug clone
    python scripts/vapi_set_voice.py --voice a976c076-3e31-4bf2-a178-8c3ce3d52b2a --plain --apply   # rollback to Eyal

Since 2 Oct each agent has its own voice, speed and emotion tag (AGENT_VOICE).

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

# PER AGENT SINCE 2 OCT. Until then both Hebrew agents took one voice from .env.
# The owner called that voice "tired and sad", picked a new clone cut from a
# livelier stretch of the same recording (A, "Echo Stone Lively 1"), and chose its
# happy, slowed sample for the incoming line only: "ok this is good for inbound
# 16-A-exclaim-happy-speed-0.8". The debt agent keeps the 31 Aug clone.
#
#   voice    None = CARTESIA_VOICE_ID from .env; `--voice` overrides it.
#   speed    generationConfig.speed. Weaker than its number on this clone: happy
#            speech runs ~15% quick, and 0.8 brings it back about 13%.
#   emotion  Cartesia's inline tag, put at the start of every chunk by a formatPlan
#            replacement (EMOTION_RULE). Vapi has no emotion field for sonic-3, and
#            the builder's experimentalControls "positivity:low" is the sonic-2
#            control, so it is dropped where a tag is set. The same hook carries the
#            <break/> pads since 26 Aug; sonic-3.5 obeys the tag in Hebrew rather
#            than reading it out (probe, 2 Oct).
AGENT_VOICE = {
    "Debt Follow-up (he)": {"voice": None, "speed": None, "emotion": None},
    "Inbound Intake (he)": {"voice": "4486a4a7-9ef6-44d4-88e8-10eab571b577",
                            "speed": 0.8, "emotion": "happy"},
}
AGENT_FLAG = {"debt": "Debt Follow-up (he)", "inbound": "Inbound Intake (he)"}


def emotion_rule(emotion):
    # `^` is zero-width: it puts the tag in front of each chunk and removes nothing.
    # Appended after the guard, so no deletion rule can reach it.
    return {"type": "regex", "regex": "^", "value": '<emotion value="%s"/>' % emotion}


def build_voice(vid, spec):
    voice = S.cartesia_voice(vid, FALLBACK)
    if spec.get("speed"):
        voice["generationConfig"]["speed"] = spec["speed"]
    if spec.get("emotion"):
        voice.pop("experimentalControls", None)
        voice["chunkPlan"]["formatPlan"]["replacements"].append(emotion_rule(spec["emotion"]))
    return voice


def shape(v):
    """What this script owns in a voice, in a form a live read and a build share."""
    reps = (((v.get("chunkPlan") or {}).get("formatPlan") or {}).get("replacements")) or []
    fb = ((v.get("fallbackPlan") or {}).get("voices") or [{}])[0]
    return {
        "voiceId": v.get("voiceId"),
        "model": v.get("model"),
        "volume": (v.get("generationConfig") or {}).get("volume"),
        "speed": (v.get("generationConfig") or {}).get("speed"),
        "experimentalControls": v.get("experimentalControls"),
        "replacements": [(r.get("regex"), r.get("value")) for r in reps],
        "fallback": len((((fb.get("chunkPlan") or {}).get("formatPlan") or {}).get("replacements")) or []),
    }


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
    # Volume: the flag wins, then .env, then the builder's default (1.4).
    if "--volume" in args:
        os.environ["CARTESIA_VOLUME"] = args[args.index("--volume") + 1]
    else:
        os.environ.setdefault("CARTESIA_VOLUME", env_value("CARTESIA_VOLUME") or "1.4")
    os.environ.setdefault("CARTESIA_MODEL", env_value("CARTESIA_MODEL") or "sonic-3.6")
    only = None
    if "--agent" in args:
        flag = args[args.index("--agent") + 1]
        if flag not in AGENT_FLAG:
            sys.exit("--agent takes %s" % " or ".join(sorted(AGENT_FLAG)))
        only = AGENT_FLAG[flag]
    # --voice overrides the id for the agents selected (a rollback names one);
    # --plain drops the agent's speed and emotion with it, back to the bare clone.
    override = args[args.index("--voice") + 1] if "--voice" in args else None
    plain = "--plain" in args

    vapi_key = env_value("VAPI_PRIVATE_KEY")
    if not vapi_key:
        sys.exit("VAPI_PRIVATE_KEY is not set in .env")

    plan = []
    for label, aid in targets(vapi_key):
        if only and label != only:
            continue
        spec = {} if plain else dict(AGENT_VOICE.get(label) or {})
        vid = override or spec.get("voice") or env_value("CARTESIA_VOICE_ID")
        if not vid:
            sys.exit("No voice for %s. Set CARTESIA_VOICE_ID in .env or pass --voice <id>." % label)
        plan.append((label, aid, vid, spec))

    # WHICH CARTESIA ACCOUNT IS VAPI ACTUALLY USING? Vapi masks the key on read,
    # so this cannot be answered from Vapi. The honest check is: the credential
    # was repointed by scripts/vapi_cartesia_key.py, and whichever .env key can
    # see this voice is the one that has to be on it.
    for vid in sorted({p[2] for p in plan}):
        seen_by = [v for v in ("CARTESIA_YARIV_API_KEY", "CARTESIA_API_KEY")
                   if env_value(v) and visible_to_credential(vid, env_value(v))[0]]
        name = visible_to_credential(vid, env_value(seen_by[0]))[1] if seen_by else "?"
        print("voice      : %s  (%s)" % (vid, name))
        print("visible to : %s" % (", ".join(seen_by) if seen_by else "NO KEY IN .env CAN SEE IT"))
        if not seen_by:
            sys.exit("\nREFUSING. No Cartesia key in .env can resolve that voice, so Vapi's\n"
                     "credential almost certainly cannot either -- and it would not error,\n"
                     "it would answer in English. Check the id.")
    print("model      : %s" % os.environ["CARTESIA_MODEL"])

    # Built with vapi_sync's own builder so the emotion control, language guard
    # and fallbackPlan match exactly what a full sync would have produced; the
    # agent's speed and tag go on top (build_voice).
    #
    # "Same" means everything shape() reads: id, model, volume, speed, the old
    # emotion control, every replacement (so the tag shows up as work), and the
    # fallback's guard -- a fallback that lost its replacements (15 Sep) has to
    # show up as work, or Elliot reads tool names aloud.
    changed = []
    for label, aid, vid, spec in plan:
        voice = build_voice(vid, spec)
        want = shape(voice)
        lv = vapi("GET", "/assistant/" + aid, vapi_key).get("voice") or {}
        have = shape(lv)
        print("\n%-22s %s" % (label, aid))
        for k in ("voiceId", "model", "volume", "speed", "experimentalControls"):
            print("  %-21s %s%s" % (k, have[k], "" if have[k] == want[k] else "   -> %s" % want[k]))
        extra = [r for r in want["replacements"] if r not in have["replacements"]]
        gone = [r for r in have["replacements"] if r not in want["replacements"]]
        print("  %-21s %d%s" % ("replacements", len(have["replacements"]),
                                "" if have["replacements"] == want["replacements"] else
                                "   -> %d (+%s, -%s)" % (len(want["replacements"]),
                                                         [r[1] for r in extra], [r[1] for r in gone])))
        print("  %-21s %d%s" % ("fallback replacements", have["fallback"],
                                "" if have["fallback"] == want["fallback"] else "   -> %d" % want["fallback"]))
        if have != want:
            changed.append((label, aid, voice, want))

    if not changed:
        print("\nNothing to do. Live already carries that voice, model, volume, speed and tag.")
        return 0

    if not apply_it:
        print("\nDry run. Re-run with --apply to write it.")
        print("Only the `voice` field is sent. Prompts, models and tools are untouched.")
        return 0

    for label, aid, voice, want in changed:
        vapi("PATCH", "/assistant/" + aid, vapi_key, {"voice": voice})
        got = shape(vapi("GET", "/assistant/" + aid, vapi_key).get("voice") or {})
        print("\n%s" % label)
        for k in ("voiceId", "volume", "speed"):
            print("  %-7s %s   %s" % (k, got[k], "OK" if got[k] == want[k] else "MISMATCH"))
        print("  replacements %d, fallback %d   %s" % (
            len(got["replacements"]), got["fallback"],
            "OK" if (got["replacements"], got["fallback"]) == (want["replacements"], want["fallback"]) else "MISMATCH"))
        if got != want:
            sys.exit("Read-back does not match what was sent. Stop and check by hand.")

    print("\nWritten and read back. That proves the field is set, not that it sounds\n"
          "right -- a voice Vapi cannot resolve fails silently to Elliot at call time.\n"
          "Place one Hebrew call before calling this done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
