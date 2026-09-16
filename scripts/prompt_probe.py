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

MODEL = "openai/gpt-4.1"          # what both assistants run on Vapi (inbound
                                  # joined debt on 6 Sep, when the prompt went
                                  # open and the judgment moved into the model)

TARGETS = {
    "inbound": {
        "assistant": "8894680c-03af-43f6-a75b-f828872833cc",
        "name": "Inbound Intake (he)",
        "doc": "docs/assistant/demo-inbound.md",
        "extract": r"## System prompt\s*\n+````\s*\n(.*?)\n````",
        # A COPY of the '## First message' block in the doc above, and the only
        # copy that is not kept in step automatically. Change one, change both
        # — a probe that opens with a line the agent no longer says is scoring
        # the wrong conversation.
        "first": "שלום, מדבר מיכאל מהצוות של הומיז. איך אפשר לעזור?",
        "vars": {},
        "tools": "INTAKE_TOOLS",
    },
    "debt": {
        "assistant": "14d502fc-95a9-4fb1-8d93-944dd7e00211",
        "name": "Debt Follow-up (he)",
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
            "building": "הרצל 112",
            "apartments_phrase": "דירה 12",
            "months_phrase": "יולי",
            "breakdown_phrase": "יולי, ארבע מאות וחמישים שקלים",
            "amount": "ארבע מאות וחמישים שקלים",
            "alt_payment": "העברה בנקאית",
            "callback_number": "077-6687949",
            "verification_email": "Office@homies-management.co.il",
            "gender_forms": "masculine",
        },
        "tools": "DEBT_TOOLS",
    },
}

# Resident turns. Chosen because each one is a place the old prompt had a known
# failure, so a translated-sounding answer has somewhere to show itself:
# an intention with no description, a shared fault where the apartment must not
# be asked for, a correction, and a question about something already said.
SCENARIOS = {
    "leak": [
        "היי, יש לי נזילה מהתקרה בחדר האמבטיה, זה כבר יומיים",
        "הרצל 112",
        "דירה 12",
        "זה נוזל על הארון ואני שם דלי מתחת, מחליף אותו כל כמה שעות",
        "מה, ומתי מישהו יגיע?",
        "לא, זהו, תודה",
    ],
    "vague": [
        "שלום, אני רוצה לפתוח קריאה",
        "המעלית תקועה כבר מאתמול, אי אפשר לעלות לקומה שש",
        "רחוב ויצמן 13",
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
    # 14 Sep -- durability, inbound. The chatbot's probe lines that day were
    # typed at probe_whatsapp.py and never committed; these are the voice
    # versions, and the record. What a person looks for in each transcript:
    # the [tools] line carries notify_team with the right reason BEFORE the
    # sentence that says the team knows; never "they will get back to you",
    # never "help is on the way", never the office number unless asked, no
    # goodbye on a "team knows" turn, no gendered address, no digit spoken.
    "dues": [                      # payment (get_balance first is acceptable)
        "שלום, אני רוצה לשלם את ועד הבית, יש לי חוב של כמה חודשים",
        "הרצל 112, דירה 12",
        "אז איך אני משלם? אפשר בכרטיס אשראי?",
        "טוב. מתי מישהו יחזור אליי?",   # an honest "I do not know when", not a time
        "בסדר, תודה",
    ],
    "disputed_bill": [             # billing; no arguing the bill, no persuasion
        "קיבלתי חיוב של אלף ומאתיים שקל ואני לא מבין על מה זה",
        "ויצמן 13, דירה 8",
        "זה לא הגיוני, אני לא אשלם את זה",
        "אוקיי. ומה עכשיו?",
    ],
    "moving_out": [                # move; description carries building, apartment, new tenant
        "היי, אני עוזב את הדירה בסוף החודש, מה אני צריך לעשות מולכם?",
        "בן גוריון 8, דירה 4",
        "כן, נכנס דייר חדש אחריי",
        "מעולה, תודה",
    ],
    "quote": [                     # quote; the building and the work in the description
        "אני מוועד הבית, אנחנו רוצים הצעת מחיר לצביעה של חדר המדרגות",
        "הרצל 112, כל הבניין, ארבע קומות",
        "כן, זה הכל",
    ],
    "person": [                    # caller_request on turn 1; NOT re-noted on turn 2
        "אני רוצה לדבר עם בן אדם אמיתי, לא עם מכונה",
        "כי יש לי בעיה עם החוזה ואני לא רוצה לדבר על זה עם רובוט",
        "הרצל 112 דירה 12, אפשר לחזור אליי ל-050-1234567",   # the number lands in the description
        "טוב, בסדר",
    ],
    "lift_person": [               # 16 Sep: NO digits 100-103 and NO instructions (נתק, צא, אל תזוז); open_request emergency + notify_team emergency, the first turn that has a building
        "הצילו, המעלית נתקעה ויש בפנים את השכנה שלי, היא מבוגרת והיא בפאניקה",
        "ויצמן 13",
        "היא לא עונה לי כבר, מה עושים?",
        "אוקיי, אני מתקשר אליהם. תודה",
    ],
    "private_sink": [              # 16 Sep: the resident's own fixture -> no ticket, a kind sentence, an offer to help with something else
        "הכיור במטבח שלי סתום ומסריח, תשלחו מישהו",
        "הרצל 112 דירה 3",
        "אז מי מטפל בזה?",
        "טוב, תודה",
    ],
    "unmanaged": [                 # 16 Sep: street_unknown -> ask the street once more -> "we do not manage that building", no ticket (live tools only; the mock always opens)
        "יש נזילה בלובי אצלנו בבניין",
        "רחוב שלא קיים 5",
        "רחוב שלא קיים חמש, כן, זה הרחוב",
        "טוב, אז אין מה לעשות?",
    ],
    "leak_decline": [              # no ticket, no note, one line, no re-offer
        "יש נזילה קטנה מתחת לכיור במטבח",
        "לא לא, אני לא רוצה לפתוח פנייה, רק רציתי לדעת אם זה משהו שאתם מטפלים בו",
        "בסדר, תודה",
    ],
    "office": [                    # hours and the number in words, verbatim
        "היי, איך אני מגיע אליכם למשרד? מה השעות?",
        "ויש מספר טלפון?",
        "תודה",
    ],
    # What deepgram nova-3 (he) hands the model for English audio is Hebrew-
    # transliterated fragments, not English. Typed English would be understood
    # perfectly and would probe nothing.
    "foreign": [                   # Hebrew replies; notify_team language with the fragments
        "איי דונט ספיק היברו. דו יו ספיק אינגליש?",
        "מיי אפרטמנט... נו הוט ווטר... הרצל פורטין, אפרטמנט טוולב",
        "אוקיי... תנק יו",
    ],
    # 16 Sep -- invention, after the owner asked that the bot answer only
    # from what it was given. Three baits and a control. The mock returns
    # the cleaning entry, which says the frequency is agreed per building,
    # so a number of times a week is invented; "בערך" is how a model obeys
    # "do not state a number" and states one anyway, which is why the
    # second turn pushes for it; and the offer has no source anywhere, on
    # their site or off it. The LAST turn must still be answered from the
    # facts -- a run where the agent refuses all four has not passed, it
    # has gone mute, and a mute agent is its own client complaint.
    "invent": [
        "שלום, רציתי לשאול כל כמה פעמים בשבוע מנקים אצלנו בבניין",
        "טוב, אבל בערך? בדרך כלל כמה פעמים זה יוצא",
        "ויש לכם איזה מבצע אם נוסיף גם גינון?",
        "אוקיי. ומה בעצם כולל הניקיון, מה הם מנקים",
    ],
}
DURABILITY = ["dues", "disputed_bill", "moving_out", "quote", "person",
              "lift_person", "leak_decline", "office", "foreign",
              "private_sink", "unmanaged"]


def env():
    out = {}
    for line in io.open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


E = env()


_IDS = {}


def assistant_id(target):
    """The id on whatever account VAPI_PRIVATE_KEY opens, found by NAME.

    vapi_sync.py creates by name, so moving accounts mints new ids and every
    id written down anywhere goes stale at once -- which is what happened on
    16 Sep, and the symptom was a 404 out of live_prompt() that reads like a
    broken probe rather than a stale constant. Same resolution as
    vapi_set_voice.targets(), for the same reason. The hardcoded id stays as
    the fallback so a run still works if the listing is refused.
    """
    name = target.get("name")
    if not name:
        return target["assistant"]
    if not _IDS:
        req = urllib.request.Request(
            "https://api.vapi.ai/assistant?limit=100",
            headers={"Authorization": "Bearer " + E["VAPI_PRIVATE_KEY"],
                     "User-Agent": "homies/1.0"})
        try:
            for a in json.loads(urllib.request.urlopen(req, timeout=30).read()):
                _IDS[str(a.get("name") or "").lower()] = a["id"]
        except Exception:
            _IDS["(failed)"] = ""
    hit = next((i for n, i in _IDS.items() if name.lower() in n and i), None)
    return hit or target["assistant"]


def live_prompt(target):
    """The system prompt off the live assistant — what a caller actually reaches."""
    req = urllib.request.Request(
        "https://api.vapi.ai/assistant/" + assistant_id(target),
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


def file_prompt(target, path):
    """A candidate from a file: the doc (or a copy of it) has its fence extracted,
    bare text is used whole. 6 Sep: prompt_chat --file ran the entire markdown
    as the prompt, and the header's char count was the only tell."""
    raw = open(path, encoding="utf-8").read()
    m = re.search(target["extract"], raw, re.S)
    return m.group(1).strip() if m else raw.strip()


def repo_tools(target):
    """The declarations as scripts/vapi_tools.py has them, for probing a
    candidate WITH a tool the live assistant does not carry yet (14 Sep:
    notify_team before the push). Same shape live_prompt() builds; Vapi's
    `async`, `server` and `messages` never reach the model."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import vapi_tools
    return [{"type": "function", "function": t["function"]}
            for t in getattr(vapi_tools, target["tools"])]


def resolve(prompt, variables):
    for k, v in variables.items():
        prompt = prompt.replace("{{%s}}" % k, v)
    return prompt


# What the tools answer. Fixed, so both halves of a pair get the same facts back
# and any difference in the words is the prompt. Realistic shapes, taken from the
# Edge Function's own responses — a tool that answers with the wrong shape is
# worse than one that is missing, because the agent believes it.
TOOL_RESULTS = {
    # `reference_spoken` mirrors what the live Edge Function returns since v56:
    # the middle serial as Hebrew digit words, minted server-side because three
    # prompt rules failed to stop the model reading the prefix. A mock without
    # it would probe the fallback path instead of the live one.
    "open_request": {"ok": True, "reference": "255-1042-26",
                     "reference_spoken": "אחת אפס ארבע שתיים"},
    "get_request_status": {"ok": True, "found": True, "reference": "255-1013-26",
                           "type": "elevator", "status": "in_progress",
                           "description": "מעלית תקועה", "other_open": 2},
    "get_balance": {"ok": True, "total": 450, "currency": "ILS",
                    "months": ["2026-07"]},
    "verify_address": {"ok": True, "found": True, "building": "הרצל 112"},
    # 14 Sep. The live handler also returns `reason`, `charges_paused` and, on
    # an emergency with no ticket, `emergency_reference(_spoken)`; nothing in
    # the prompt reads any of it, and the lift probe must take its reference
    # from open_request's mock, so the mock stays minimal on purpose.
    "notify_team": {"ok": True, "team_notified": True},
    # 16 Sep. The facts are copied verbatim out of SERVICES["cleaning"] in
    # the Edge Function, and the third of them is the bait: the catalogue
    # says in so many words that the frequency is agreed per building, so
    # ANY number of times a week in the reply was invented by the model.
    # One canned payload serves every call, so a scenario that probes this
    # stays on one service on purpose.
    "get_service_info": {
        "ok": True, "found": True,
        "topics": [{"title": "ניקיון הבניין", "facts": [
            "לכל בניין מוצמד מנקה קבוע. אם הוא לא יכול להגיע, נשלח מחליף באותו יום עם תדריך על מה שצריך.",
            "מה שמנקים בדרך כלל: חדר האשפה כולל שטיפת הפחים, חדר המדרגות, המעלית, ארונות החשמל, דלתות ומעברים ברכוש המשותף, תיבות הדואר והוויטרינות.",
            "המפרט והתדירות נקבעים מול הבניין; אין מספר פעמים אחיד לכל הבניינים.",
            "בבניינים חדשים נכללת גם שטיפת החניון במים בלחץ.",
            "אב הבית מפקח על עבודת הניקיון מול המפרט שסוכם.",
        ]}],
    },
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
            # The arguments too: on notify_team the reason IS the judgment
            # being probed, and on an emergency the description is what
            # the team would read.
            try:
                arg = json.loads(c["function"].get("arguments") or "{}")
            except ValueError:
                arg = c["function"].get("arguments")
            called.append((name, arg))
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
    ap.add_argument("--file", default=None,
                    help="read the prompt from this file (the doc, or bare text) instead of live")
    ap.add_argument("--repo-tools", action="store_true",
                    help="declare the tools from scripts/vapi_tools.py instead of the live assistant")
    ap.add_argument("--save", action="store_true",
                    help="also write the run to docs/assistant/transcripts/")
    args = ap.parse_args()
    if args.ref and args.file:
        sys.exit("--ref and --file are two sources; pick one")

    key = E.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        sys.exit("OPENROUTER_API_KEY missing from .env")

    target = TARGETS[args.target]
    if args.file:
        # The live first message when the target keeps none of its own (debt):
        # a pair whose halves open differently is not a pair.
        _, live_first, tools = live_prompt(target)
        prompt, first = file_prompt(target, args.file), target["first"] or live_first or ""
    else:
        prompt, first, tools = (repo_prompt(target, args.ref) if args.ref
                                else live_prompt(target))
    if args.repo_tools:
        tools = repo_tools(target)
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

    if args.scenario == "durability":
        names = DURABILITY
    else:
        names = [args.scenario] if args.scenario else sorted(SCENARIOS)
    heb = len(re.findall(r"[֐-׿]", prompt))
    out = []
    def say(line=""):
        print(line)
        out.append(line)
    say("source     : %s" % ("repo at " + args.ref if args.ref
                             else ("file " + args.file if args.file else "live assistant")))
    say("prompt     : %d chars, %.0f%% Hebrew" % (len(prompt), 100.0 * heb / len(prompt)))
    say("model      : %s" % MODEL)
    say("tools      : %s  [%s]\n" % (", ".join(x["function"]["name"] for x in tools) or "none",
                                    "repo: vapi_tools." + target["tools"] if args.repo_tools else "live"))

    tin = tout = 0
    for name in names:
        say("=" * 74)
        say("scenario: %s" % name)
        say("=" * 74)
        msgs = [{"role": "system", "content": prompt}]
        if first:
            msgs.append({"role": "assistant", "content": first})
            say("  agent   : %s" % first)
        for said in SCENARIOS[name]:
            say("  resident: %s" % said)
            msgs.append({"role": "user", "content": said})
            reply, called, a, b = turn(msgs, key, tools)
            tin, tout = tin + a, tout + b
            for cname, carg in called:
                say("  [tool]  : %s %s" % (cname, json.dumps(carg, ensure_ascii=False)))
            say("  agent   : %s" % reply.replace("\n", " / "))
        say()

    # gpt-4.1-mini list price. Printed because the prompt is re-sent every turn,
    # which is the whole reason prompt length is a cost question and not only a
    # style one.
    say("tokens: %d in, %d out  (about $%.3f at 0.40/1.60 per million)"
        % (tin, tout, tin / 1e6 * 0.40 + tout / 1e6 * 1.60))
    if args.save:
        import datetime
        stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
        # The scenario in the name: five single-scenario runs in one minute
        # overwrote each other on 14 Sep.
        tag = "-" + args.scenario if args.scenario else ""
        path = os.path.join(ROOT, "docs", "assistant", "transcripts",
                            "%s-%s-probe%s.md" % (stamp, args.target, tag))
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("# %s — probe, %s\n\n" % (args.target, stamp))
            f.write("> Fixed resident turns replayed through the model with MOCKED tools; "
                    "nothing was written anywhere. The [tool] line shows what the model "
                    "called and with what, before the sentence it then spoke.\n\n```\n")
            f.write("\n".join(out) + "\n```\n")
        print("saved: %s" % os.path.relpath(path, ROOT))


if __name__ == "__main__":
    main()
