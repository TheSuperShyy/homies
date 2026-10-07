# -*- coding: utf-8 -*-
r"""Change ONLY the voice on the live Hebrew assistants, touching nothing else.

    python scripts/vapi_set_voice.py                  # show live vs intended, both agents
    python scripts/vapi_set_voice.py --apply
    python scripts/vapi_set_voice.py --agent inbound --apply               # one agent (AGENT_VOICE)
    python scripts/vapi_set_voice.py --agent inbound --voice ba765d50-19c6-4b3e-bc15-9de3b45f82f7 --plain --apply
                                                      # the incoming line back to the 31 Aug clone
    python scripts/vapi_set_voice.py --voice a976c076-3e31-4bf2-a178-8c3ce3d52b2a --plain --apply   # rollback to Eyal

Since 2 Oct each agent has its own voice, speed and emotion tag (AGENT_VOICE), and
this script writes all of them: the voice id, the volume, the speed and the tag
rule. Since 4 Oct a prompt push runs `vapi_sync.py <agent> --keep-voice --apply`,
which leaves the live voice alone, and then this script; without --keep-voice the
inbound sync writes the stock Eyal voice and this script must follow at once.
Flags: --apply, --plain, --agent inbound|debt, --voice <id>, --volume <n>;
anything else is refused.

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
# Refreshed 4 Oct to the account the key opens now (the tenth, copied one to one
# from the ninth the same day); the August ids 404'd.
FALLBACK_IDS = {
    "Debt Follow-up (he)": "9e0209d2-c835-4163-813f-6844f9e07651",
    "Inbound Intake (he)": "00d91473-1aaa-4a57-a380-ca5bb2b7f1af",
}


def targets(vapi_key):
    """(label, id) per Hebrew assistant, from whatever account the key opens."""
    try:
        live = vapi("GET", "/assistant?limit=100", vapi_key)
    except SystemExit as e:
        print("Listing the assistants failed (%s); using FALLBACK_IDS." % str(e)[:200])
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
#            replacement (emotion_rules). Vapi has no emotion field for sonic-3, and
#            the builder's experimentalControls "positivity:low" is the sonic-2
#            control, so it is dropped where a tag is set. The same hook carries the
#            <break/> pads since 26 Aug; sonic-3.5 obeys the tag in Hebrew rather
#            than reading it out (probe, 2 Oct).
#   dict_env the .env variable holding a Cartesia pronunciation dictionary id
#            (scripts/cartesia_dicts.py makes them: bare address words to their
#            pointed form, so לך is said lekha every time). Unset = no dictionary,
#            and the field is left as the live voice has it. 7 Oct, ready, not
#            live: docs/reference/voice/hebrew-gender-consistency-2026-10-07.md.
AGENT_VOICE = {
    "Debt Follow-up (he)": {"voice": None, "speed": None, "emotion": None,
                            "dict_env": "CARTESIA_DICT_DEBT"},
    "Inbound Intake (he)": {"voice": "4486a4a7-9ef6-44d4-88e8-10eab571b577",
                            "speed": 0.8, "emotion": "happy",
                            "dict_env": "CARTESIA_DICT_INBOUND"},
}
AGENT_FLAG = {"debt": "Debt Follow-up (he)", "inbound": "Inbound Intake (he)"}


def emotion_rules(emotion):
    """Two replacements: the tag in front of a chunk, then a chunk that is nothing
    but the tag back to empty.

    `^` is zero-width: it puts the tag in front of a chunk and removes nothing. Vapi
    runs its own formatting (angle-bracket removal included) first and custom
    replacements last, so the tag reaches Cartesia, as the <break/> pads do. Both
    rules go after the guard, so no deletion rule can reach the tag.

    The second rule keeps a chunk the guard emptied empty: a lone tag with no words
    could make Cartesia error, and Vapi would fall to Elliot for the call. It is a
    second rule and not a lookahead because Vapi checks every pattern with RE2,
    which has none: `^(?=\\s*\\S)` was refused with a 400 on 4 Oct ("invalid perl
    operator: (?="). Only `^`, literal text, `\\s*` and `$` here, all RE2.
    """
    if not re.match(r"^[a-z]+$", emotion):
        sys.exit("Emotion %r: letters only (it is written into a pattern)." % emotion)
    tag = '<emotion value="%s"/>' % emotion
    return [{"type": "regex", "regex": "^", "value": tag},
            {"type": "regex", "regex": "^" + tag + r"\s*$", "value": ""}]


def build_voice(vid, spec):
    voice = S.cartesia_voice(vid, FALLBACK)
    if spec.get("speed"):
        voice["generationConfig"]["speed"] = spec["speed"]
    if spec.get("emotion"):
        voice.pop("experimentalControls", None)
        voice["chunkPlan"]["formatPlan"]["replacements"].extend(emotion_rules(spec["emotion"]))
    did = env_value(spec["dict_env"]) if spec.get("dict_env") else ""
    if did:
        voice["pronunciationDictId"] = did
    return voice


def rep_key(r):
    """One replacement as everything that decides what it does."""
    return (r.get("type"), r.get("regex") if r.get("type") == "regex" else r.get("key"),
            r.get("value"), bool(r.get("replaceAllEnabled")),
            tuple(sorted((o.get("type"), bool(o.get("enabled"))) for o in (r.get("options") or []))))


def reps_of(v):
    return [rep_key(r) for r in
            ((((v.get("chunkPlan") or {}).get("formatPlan") or {}).get("replacements")) or [])]


def shape(v):
    """What this script owns in a voice, in a form a live read and a build share."""
    fb = ((v.get("fallbackPlan") or {}).get("voices") or [{}])[0]
    return {
        "provider": v.get("provider"),
        "voiceId": v.get("voiceId"),
        "model": v.get("model"),
        "language": v.get("language"),
        "volume": (v.get("generationConfig") or {}).get("volume"),
        "speed": (v.get("generationConfig") or {}).get("speed"),
        "experimentalControls": v.get("experimentalControls") or None,
        "pronunciationDictId": v.get("pronunciationDictId") or None,
        "replacements": reps_of(v),
        "fallback": (fb.get("provider"), fb.get("voiceId"), reps_of(fb)),
    }


def report(have, want, readback=False):
    """Every field shape() reads; a dry run shows `-> want`, a read-back OK or MISMATCH."""
    def mark(same, target):
        if readback:
            return "   OK" if same else "   MISMATCH (sent %s)" % (target,)
        return "" if same else "   -> %s" % (target,)
    for k in ("provider", "voiceId", "model", "language", "volume", "speed", "experimentalControls",
              "pronunciationDictId"):
        print("  %-21s %s%s" % (k, have[k], mark(have[k] == want[k], want[k])))
    extra = [r[2] for r in want["replacements"] if r not in have["replacements"]]
    gone = [r[2] for r in have["replacements"] if r not in want["replacements"]]
    same = have["replacements"] == want["replacements"]
    print("  %-21s %d%s" % ("replacements", len(have["replacements"]),
                            mark(same, "%d (+%s, -%s)" % (len(want["replacements"]), extra, gone))))
    hf, wf = have["fallback"], want["fallback"]
    print("  %-21s %s %s, %d replacements%s" % ("fallback", hf[0], hf[1], len(hf[2]),
                                               mark(hf == wf, "%s %s, %d" % (wf[0], wf[1], len(wf[2])))))


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


BOOL_FLAGS = ("--apply", "--plain")
VALUE_FLAGS = ("--agent", "--voice", "--volume")


def parse(argv):
    """Known flags only. A misspelled --plain in a rollback must stop, not be ignored."""
    opts, i = {}, 0
    while i < len(argv):
        a = argv[i]
        if a in BOOL_FLAGS:
            opts[a] = True
            i += 1
        elif a in VALUE_FLAGS:
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                sys.exit("%s needs a value." % a)
            opts[a] = argv[i + 1]
            i += 2
        else:
            sys.exit("Unknown argument %r. Known: %s" % (a, " ".join(BOOL_FLAGS + VALUE_FLAGS)))
    return opts


def main():
    opts = parse(sys.argv[1:])
    apply_it = opts.get("--apply", False)
    # Volume: the flag wins, then .env, then the builder's default (1.4).
    if "--volume" in opts:
        os.environ["CARTESIA_VOLUME"] = opts["--volume"]
    else:
        os.environ.setdefault("CARTESIA_VOLUME", env_value("CARTESIA_VOLUME") or "1.4")
    os.environ.setdefault("CARTESIA_MODEL", env_value("CARTESIA_MODEL") or "sonic-3.6")
    only = None
    if "--agent" in opts:
        if opts["--agent"] not in AGENT_FLAG:
            sys.exit("--agent takes %s" % " or ".join(sorted(AGENT_FLAG)))
        only = AGENT_FLAG[opts["--agent"]]
    # --voice overrides the id for the agents selected (a rollback names one);
    # --plain drops the agent's speed and emotion with it, back to the bare clone.
    override = opts.get("--voice")
    plain = opts.get("--plain", False)

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
        report(have, want)
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
        print("\n%s, read back" % label)
        report(got, want, readback=True)
        if got != want:
            sys.exit("Read-back of %s does not match what was sent (MISMATCH above). "
                     "Stop and check by hand." % label)
        print("WRITTEN %s" % label)

    print("\nWritten and read back. That proves the field is set, not that it sounds\n"
          "right -- a voice Vapi cannot resolve fails silently to Elliot at call time.\n"
          "Place one Hebrew call before calling this done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
