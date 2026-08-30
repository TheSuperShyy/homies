# -*- coding: utf-8 -*-
"""Put identical resident turns to a live assistant and print the Hebrew it writes.

    python scripts/prompt_probe.py inbound            # the live Hebrew intake agent
    python scripts/prompt_probe.py inbound --ref HEAD~2   # the same, but the prompt
                                                          # as it was at that commit
    python scripts/prompt_probe.py debt --scenario late

WHAT QUESTION THIS ANSWERS
"Does the agent sound like a person speaking Hebrew, or like an English script
being rendered into Hebrew?" That is a question about WORDS, and words are what
the prompt controls, so this is the instrument for it: same model, same
scenario, same resident turns, one variable changed.

WHAT IT DOES NOT ANSWER, AND THE DIFFERENCE MATTERS
It says nothing about how the agent SOUNDS. Pronunciation, pace, stress, where
it breathes, whether it talks over the caller — all of that lives in TTS and the
endpointing config, not in the prompt, and none of it is exercised here. A call
is still the only evidence about audio. What this rules in or out is phrasing.

WHY THE RESIDENT'S TURNS ARE FIXED AND NOT SIMULATED
`vapi_duel.py` and `vapi_eval.py` both put a second model in the caller's chair,
which is more realistic and useless for a comparison: the two runs get different
inputs, so any difference in the output has two possible causes. Here both runs
hear the same sentences in the same order, so a difference in what comes back is
the prompt and nothing else.

It reads the prompt off the LIVE assistant by default, so what is tested is what
a caller would reach — not what the repo says should be live. `--ref` reads the
repo at a commit instead, which is how the before-and-after pair is produced.

Costs money: OpenRouter, the same key the WhatsApp bot runs on. One scenario is
about six model calls carrying the whole prompt each time. Usage is printed at
the end of every run.
"""

import argparse
import io
import json
import os
import re
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODEL = "openai/gpt-4.1-mini"          # what both assistants run on Vapi

TARGETS = {
    "inbound": {
        "assistant": "7752c6bb-89e9-49f3-aaf4-154ecc65cdff",
        "doc": "docs/assistant/demo-inbound.md",
        "extract": r"## System prompt\s*\n+````\s*\n(.*?)\n````",
        # A COPY of the '## First message' block in the doc above, and the only
        # copy that is not kept in step automatically. Change one, change both
        # — a probe that opens with a line the agent no longer says is scoring
        # the wrong conversation.
        "first": "שלום, מדבר מיכאל מהצוות של הומיז. איך אפשר לעזור?",
        "vars": {},
    },
    "debt": {
        "assistant": "93c7f5e5-4024-49a3-9ab6-141f2b423649",
        "doc": "docs/features/10-debt-followup/prompt.md",
        "extract": r"\n## System prompt\s*\n(.*?)(?=\n## )",
        "first": None,
        # The debt prompt is a template. Left unresolved, every placeholder
        # renders empty and the run scores a broken script rather than the
        # agent — the failure vapi_mock.py exists to prevent on the voice side.
        # THE LIST HAS TO BE COMPLETE, and the first version of it was not.
        # It carried names the prompt does not use (`month`, `card_last4`) and
        # missed three it does, so the agent read `{{apartments_phrase}}` aloud
        # to the simulated resident. Checked against the live assistant rather
        # than written from memory: every {{name}} in the prompt AND in the
        # first message is here.
        "vars": {
            "first_name": "שחר",
            "building": "הרצל 14",
            "apartments_phrase": "דירה 12",
            "months_phrase": "יולי",
            "breakdown_phrase": "יולי, ארבע מאות וחמישים שקלים",
            "amount": "ארבע מאות וחמישים שקלים",
            "alt_payment": "העברה בנקאית",
            "callback_number": "077-6687949",
            "verification_email": "Office@homies-management.co.il",
            "gender_forms": "masculine",
        },
    },
}

# Resident turns. Chosen because each one is a place the old prompt had a known
# failure, so a translated-sounding answer has somewhere to show itself:
# an intention with no description, a shared fault where the apartment must not
# be asked for, a correction, and a question about something already said.
SCENARIOS = {
    "leak": [
        "היי, יש לי נזילה מהתקרה בחדר האמבטיה, זה כבר יומיים",
        "הרצל 14",
        "דירה 12",
        "זה נוזל על הארון ואני שם דלי מתחת, מחליף אותו כל כמה שעות",
        "מה, ומתי מישהו יגיע?",
        "לא, זהו, תודה",
    ],
    "vague": [
        "שלום, אני רוצה לפתוח קריאה",
        "המעלית תקועה כבר מאתמול, אי אפשר לעלות לקומה שש",
        "רחוב ויצמן 3",
        "רגע, לא שבע, שש",
        "אוקיי. יש עוד משהו פתוח אצלנו בבניין?",
    ],
    "parcel": [
        "מישהו לקח לי חבילה מחוץ לדלת",
        "כן, בבוקר, בערך בשמונה. שמתי אותה שם כי לא הייתי בבית",
        "בן גוריון 8, דירה 4",
        "רציתי גם שתבדקו את המצלמות בכניסה",
        "מתי אתם חוזרים אליי בקשר לזה?",
    ],
    "late": [
        "כן, מי זה?",
        "רגע, אני לא מבין, על מה החוב הזה",
        "אבל המעלית לא עובדת חודשיים ואני אמור לשלם על זה?",
        "טוב, תשלח לי את הלינק",
        "בסדר",
    ],
}


def env():
    out = {}
    for line in io.open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


E = env()


def live_prompt(target):
    """The system prompt off the live assistant — what a caller actually reaches."""
    req = urllib.request.Request(
        "https://api.vapi.ai/assistant/" + target["assistant"],
        headers={"Authorization": "Bearer " + E["VAPI_PRIVATE_KEY"],
                 # Cloudflare 403s urllib's default user-agent on this host, and
                 # the 403 reads like an auth failure. It is not.
                 "User-Agent": "homies/1.0"})
    a = json.loads(urllib.request.urlopen(req, timeout=30).read())
    prompt = "".join(m.get("content", "") for m in a["model"]["messages"]
                     if m.get("role") == "system")
    # THE TOOLS COME TOO, AND THE FIRST VERSION OF THIS SCRIPT DID NOT TAKE THEM.
    # Without them the agent cannot look anything up, and a model that is told
    # to look something up and has nothing to call INVENTS THE ANSWER: the first
    # run read out an open request on a building it had never queried. That is a
    # fault of the harness, not of the agent, and it would have been reported as
    # a fault of the agent.
    tools = [{"type": "function", "function": t["function"]}
             for t in (a["model"].get("tools") or []) if t.get("function")]
    return prompt, a.get("firstMessage") or "", tools


def repo_prompt(target, ref):
    """The prompt as the repo had it at `ref`, for the before half of a pair."""
    raw = subprocess.run(["git", "show", "%s:%s" % (ref, target["doc"])],
                         cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8")
    m = re.search(target["extract"], raw, re.S)
    if not m:
        sys.exit("Could not find the system prompt in %s at %s" % (target["doc"], ref))
    # The repo half of a before/after pair borrows the LIVE tools: the point of
    # the pair is one variable changed, and the tools are not it.
    _, _, tools = live_prompt(target)
    # AND IT NEEDS THAT COMMIT'S OWN OPENING LINE. Falling back to a hardcoded
    # one left the debt agent with no first message on the --ref half, so the
    # two halves of the pair did not start the same conversation and the
    # comparison was worthless — the English half opened by introducing itself
    # mid-call because nothing had introduced it.
    fm = re.search(r"### (?:Opening|הפתיחה)\s*\n+> (.+)", raw)
    return (m.group(1).strip(),
            fm.group(1).strip() if fm else (target["first"] or ""),
            tools)


def resolve(prompt, variables):
    for k, v in variables.items():
        prompt = prompt.replace("{{%s}}" % k, v)
    return prompt


# What the tools answer. Fixed, so both halves of a pair get the same facts back
# and any difference in the words is the prompt. Realistic shapes, taken from the
# Edge Function's own responses — a tool that answers with the wrong shape is
# worse than one that is missing, because the agent believes it.
TOOL_RESULTS = {
    "open_request": {"ok": True, "reference": "255-1042-26"},
    "get_request_status": {"ok": True, "found": True, "reference": "255-1013-26",
                           "type": "elevator", "status": "in_progress",
                           "description": "מעלית תקועה", "other_open": 2},
    "get_balance": {"ok": True, "total": 450, "currency": "ILS",
                    "months": ["2026-07"]},
    "verify_address": {"ok": True, "found": True, "building": "הרצל 14"},
}
TOOL_DEFAULT = {"ok": True}


def ask(messages, key, tools):
    body = {"model": MODEL, "messages": messages, "temperature": 0.3}
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions", method="POST",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "User-Agent": "homies/1.0"})
    r = json.loads(urllib.request.urlopen(req, timeout=120).read())
    if "choices" not in r:
        sys.exit("OpenRouter returned no choices: %s" % json.dumps(r)[:300])
    return r["choices"][0]["message"], r.get("usage") or {}


def turn(messages, key, tools):
    """One resident turn: run the model until it stops calling tools and speaks.

    Vapi runs this loop for us on a real call. Here it has to be run by hand, or
    a turn that opens a request ends with a tool call and no sentence.
    """
    called, tin, tout = [], 0, 0
    for _ in range(6):
        msg, usage = ask(messages, key, tools)
        tin += usage.get("prompt_tokens", 0)
        tout += usage.get("completion_tokens", 0)
        calls = msg.get("tool_calls") or []
        messages.append({k: v for k, v in msg.items()
                         if k in ("role", "content", "tool_calls")})
        if not calls:
            return msg.get("content") or "", called, tin, tout
        for c in calls:
            name = c["function"]["name"]
            called.append(name)
            messages.append({"role": "tool", "tool_call_id": c["id"],
                             "content": json.dumps(TOOL_RESULTS.get(name, TOOL_DEFAULT),
                                                   ensure_ascii=False)})
    return "(the agent never stopped calling tools)", called, tin, tout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", choices=sorted(TARGETS))
    ap.add_argument("--scenario", default=None,
                    help="one of: " + ", ".join(sorted(SCENARIOS)))
    ap.add_argument("--ref", default=None,
                    help="read the prompt from the repo at this commit instead of live")
    args = ap.parse_args()

    key = E.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        sys.exit("OPENROUTER_API_KEY missing from .env")

    target = TARGETS[args.target]
    prompt, first, tools = (repo_prompt(target, args.ref) if args.ref
                            else live_prompt(target))
    # The first message is a template too. Resolving only the prompt left
    # `{{first_name}}` in the agent's opening sentence, which is the one line of
    # the call that is spoken before the model does anything at all.
    prompt = resolve(prompt, target["vars"])
    first = resolve(first, target["vars"])
    # `{{...}}` with literal dots is not a placeholder: the prompt quotes it
    # as an example of what the agent must never say aloud.
    left = [v for v in re.findall(r"\{\{[^}]+\}\}", prompt) if v != "{{...}}"]
    left += [v for v in re.findall(r"\{\{[^}]+\}\}", first) if v != "{{...}}"]
    if left:
        sys.exit("unresolved placeholders. This would score a broken "
                 "script, not the agent:\n  %s"
                 % ", ".join(sorted(set(left))))

    names = [args.scenario] if args.scenario else sorted(SCENARIOS)
    heb = len(re.findall(r"[֐-׿]", prompt))
    print("source     : %s" % ("repo at " + args.ref if args.ref else "live assistant"))
    print("prompt     : %d chars, %.0f%% Hebrew" % (len(prompt), 100.0 * heb / len(prompt)))
    print("model      : %s" % MODEL)
    print("tools      : %s\n" % (", ".join(x["function"]["name"]
                                        for x in tools) or "none"))

    tin = tout = 0
    for name in names:
        print("=" * 74)
        print("scenario: %s" % name)
        print("=" * 74)
        msgs = [{"role": "system", "content": prompt}]
        if first:
            msgs.append({"role": "assistant", "content": first})
            print("  agent   : %s" % first)
        for said in SCENARIOS[name]:
            print("  resident: %s" % said)
            msgs.append({"role": "user", "content": said})
            reply, called, a, b = turn(msgs, key, tools)
            tin, tout = tin + a, tout + b
            if called:
                print("  [tools] : %s" % ", ".join(called))
            print("  agent   : %s" % reply.replace("\n", " / "))
        print()

    # gpt-4.1-mini list price. Printed because the prompt is re-sent every turn,
    # which is the whole reason prompt length is a cost question and not only a
    # style one.
    print("tokens: %d in, %d out  (about $%.3f at 0.40/1.60 per million)"
          % (tin, tout, tin / 1e6 * 0.40 + tout / 1e6 * 1.60))


if __name__ == "__main__":
    main()
