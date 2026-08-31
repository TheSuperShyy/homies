# -*- coding: utf-8 -*-
"""Talk to the Hebrew intake agent by typing English, and read what it says back.

    python scripts/prompt_chat.py inbound          # the live Hebrew intake agent
    python scripts/prompt_chat.py inbound --ref HEAD   # the prompt as the repo has it
    python scripts/prompt_chat.py debt

WHAT QUESTION THIS ANSWERS
"Is this agent someone I would want to reach when I call my building's office?"
That is a question you cannot answer if you cannot read Hebrew, and until now
there was no way to ask it. `prompt_probe.py` replays three fixed Hebrew
scenarios and prints Hebrew. This one lets you drive: you type English, it puts
real spoken Hebrew to the agent, and it prints the reply in Hebrew AND English.

WHY YOUR ENGLISH IS TRANSLATED INSTEAD OF SENT AS-IS
The prompt tells the agent that a caller who is not speaking Hebrew gets
`transfer_to_human` with reason "language". Type English at it directly and
every conversation ends in a hand-off on turn one, and you have tested the
language rule rather than the agent. The translation step is load-bearing.

It also means there are now TWO things that can be wrong with a bad answer:
the agent, or the Hebrew we put in its ear. So the Hebrew that is about to be
sent is printed before it is sent. Read it. If it is wrong, the turn is void.

WHY THE ENGLISH BACK-TRANSLATION IS TOLD TO KEEP THE REGISTER
You are judging tone — whether it sounds like a friendly representative or a
form being filled in. A translator that smooths a curt Hebrew sentence into
polite English destroys the only evidence you were after. See TO_EN below.

WHAT IT DOES NOT ANSWER, AND THE DIFFERENCE MATTERS
Nothing about how the agent SOUNDS. Pronunciation, pace, where it breathes,
whether it talks over you — that is TTS and endpointing, not the prompt, and
none of it is exercised here. A real call is still the only evidence about
audio. What this rules in or out is words.

NOTHING IS WRITTEN ANYWHERE. Vapi is read (GET) to fetch the live prompt and
its tools; the tools themselves are mocked from prompt_probe.TOOL_RESULTS, so
no ticket reaches Supabase and nothing touches OXS. Unlike check_tools.py,
which does write real rows, this run leaves no trace on any client system.

Costs money: OpenRouter, the same key the WhatsApp bot runs on. Every turn
re-sends the whole prompt, plus two small translation calls. Usage is printed
on exit and written into the transcript.
"""

import argparse
import datetime
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prompt_probe as pp          # the engine: .env, live prompt, tools, ask()

ROOT = pp.ROOT
# The same range prompt_probe.py counts Hebrew with, written as escapes so the
# routing rule is legible next to the regex rather than a wall of glyphs.
HEBREW = re.compile(r"[֐-׿]")
TRANSCRIPTS = os.path.join(ROOT, "docs", "assistant", "transcripts")

for stream in (sys.stdout, sys.stdin):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

TO_HE = (
    "You turn an English line into the Hebrew an Israeli resident would actually SAY "
    "on the phone to their building-management company.\n"
    "Spoken register, not written. Carry the meaning across; never translate word for word.\n"
    "Keep the tone exactly as given: annoyed stays annoyed, rambling stays rambling, "
    "curt stays curt, joking stays joking.\n"
    # CAUGHT ON THE FIRST REAL RUN. Typing the bare answer "Herzl 14" came back as
    # "the building on Herzl Street 14, there is a problem that needs handling" —
    # the translator had supplied a complaint the caller never made. A resident
    # answering an address question says the address and stops, and how the agent
    # handles a bare answer is exactly what we are here to watch.
    "ADD NOTHING. A bare fragment stays a bare fragment: \"Herzl 14\" is הרצל 14 and not "
    "a sentence about a problem; \"apartment 12\" is דירה 12; \"yes\" is כן. Never supply "
    "a reason, a greeting, a complaint or any clause the English does not contain. "
    "Roughly as many words out as in.\n"
    "Keep street names, apartment numbers and reference numbers exactly as written.\n"
    "Reply with the Hebrew line and nothing else. No quotes, no notes, no transliteration."
)

# THIS INSTRUCTION IS THE POINT OF THE SCRIPT AND IT IS EASY TO GET WRONG.
# A translator left to its own devices produces fluent, courteous English out of
# anything. The reader here is trying to decide whether the agent is too clipped
# and too cold. Politeness added in translation is politeness they will credit to
# the agent, and they would then loosen a prompt that was never tight, or fail to
# loosen one that was.
TO_EN = (
    "You turn a Hebrew line spoken by a phone agent into English.\n"
    "PRESERVE THE REGISTER EXACTLY. If the Hebrew is clipped, blunt or cold, the English "
    "must read clipped, blunt and cold. If it is warm, warm. If it is stiff or bureaucratic, "
    "keep it stiff. The reader cannot read Hebrew and is judging TONE from your output, so "
    "smoothing it into polite English tells them something false.\n"
    "Match the sentence count and roughly the length. Add no politeness, softening, "
    "hedging or filler that is not in the Hebrew.\n"
    "Keep Hebrew filler and backchannels visible rather than deleting them: render "
    "אה as 'uh', אוקיי as 'okay', רגע as 'one sec', בסדר as 'alright'.\n"
    "Reply with the English and nothing else. No quotes, no notes."
)


def translate(text, system, key, meter):
    """One small model call. `meter` accumulates [in, out] tokens across the run."""
    if not text or not text.strip():
        return ""
    msg, usage = pp.ask([{"role": "system", "content": system},
                         {"role": "user", "content": text}], key, None)
    meter[0] += usage.get("prompt_tokens", 0)
    meter[1] += usage.get("completion_tokens", 0)
    return (msg.get("content") or "").strip()


def gloss(obj, key, meter):
    """Walk a tool-argument structure and put every Hebrew string into English.

    Only the Hebrew leaves cost a call — numbers, enums and building ids pass
    through untouched, which is what you want anyway: `apartment: "12"` is
    already readable and translating it could only corrupt it.
    """
    if isinstance(obj, dict):
        return {k: gloss(v, key, meter) for k, v in obj.items()}
    if isinstance(obj, list):
        return [gloss(v, key, meter) for v in obj]
    if isinstance(obj, str) and HEBREW.search(obj):
        return translate(obj, TO_EN, key, meter)
    return obj


def turn(messages, key, tools):
    """One resident turn, run until the agent stops calling tools and speaks.

    A near-copy of prompt_probe.turn(), and deliberately not a call to it: that
    one returns tool NAMES only. The argument values are the whole point here.
    A ticket opened against the wrong apartment is the worst outcome in this
    system, and a run that prints `[tools] : open_request` cannot show it to you.
    """
    called, tin, tout = [], 0, 0
    for _ in range(6):
        msg, usage = pp.ask(messages, key, tools)
        tin += usage.get("prompt_tokens", 0)
        tout += usage.get("completion_tokens", 0)
        calls = msg.get("tool_calls") or []
        messages.append({k: v for k, v in msg.items()
                         if k in ("role", "content", "tool_calls")})
        if not calls:
            return msg.get("content") or "", called, tin, tout
        for c in calls:
            name = c["function"]["name"]
            raw = c["function"].get("arguments") or "{}"
            try:
                args = json.loads(raw)
            except ValueError:
                # Worth seeing rather than swallowing: malformed arguments are a
                # real failure mode, and one the agent is not told about.
                args = {"(unparseable)": raw}
            result = pp.TOOL_RESULTS.get(name, pp.TOOL_DEFAULT)
            called.append((name, args, result))
            messages.append({"role": "tool", "tool_call_id": c["id"],
                             "content": json.dumps(result, ensure_ascii=False)})
    return "(the agent never stopped calling tools)", called, tin, tout


def j(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


HELP = """commands
  /he <text>   send the text as-is, no translation (paste Hebrew, or force a phrase)
  /restart     hang up and call again — same prompt, empty history
  /save        write the transcript so far and keep going
  /quit        write the transcript and stop
"""


def write_transcript(rows, header, meter_main, meter_tr, target_name):
    if not rows:
        return None
    if not os.path.isdir(TRANSCRIPTS):
        os.makedirs(TRANSCRIPTS)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    path = os.path.join(TRANSCRIPTS, "%s-%s.md" % (stamp, target_name))
    out = ["# %s — typed transcript, %s" % (target_name, stamp), ""]
    out += ["> Typed in English through `scripts/prompt_chat.py`. The Hebrew under",
            "> **sent** is what the agent actually heard; if that line is wrong the",
            "> turn tested the translator, not the agent. Tools were mocked — nothing",
            "> was written to Supabase or OXS.", ""]
    out += ["```", header.rstrip(), "```", ""]
    for r in rows:
        if r["kind"] == "restart":
            out += ["---", "", "**— call restarted —**", ""]
            continue
        if r["kind"] == "agent_first":
            out += ["**agent opens**", "", "- he: %s" % r["he"],
                    "- en: %s" % r["en"], ""]
            continue
        out += ["**you** — %s" % r["typed"], "",
                "- sent (he): %s" % r["sent"]]
        for name, args, res, args_en in r["tools"]:
            out.append("- tool `%s` %s" % (name, j(args)))
            if j(args_en) != j(args):
                out.append("  - in English: %s" % j(args_en))
            out.append("  - mocked reply: %s" % j(res))
        out += ["- agent (he): %s" % r["he"],
                "- agent (en): %s" % r["en"], ""]
    total_in = meter_main[0] + meter_tr[0]
    total_out = meter_main[1] + meter_tr[1]
    out += ["---", "",
            "tokens: %d in, %d out (%d in / %d out of that was translation) — "
            "about $%.3f at 0.40/1.60 per million"
            % (total_in, total_out, meter_tr[0], meter_tr[1],
               total_in / 1e6 * 0.40 + total_out / 1e6 * 1.60), ""]
    io.open(path, "w", encoding="utf-8").write("\n".join(out))
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", choices=sorted(pp.TARGETS))
    ap.add_argument("--ref", default=None,
                    help="read the prompt from the repo at this commit instead of live")
    args = ap.parse_args()

    key = pp.E.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        sys.exit("OPENROUTER_API_KEY missing from .env")

    target = pp.TARGETS[args.target]
    prompt, first, tools = (pp.repo_prompt(target, args.ref) if args.ref
                            else pp.live_prompt(target))
    prompt = pp.resolve(prompt, target["vars"])
    first = pp.resolve(first, target["vars"])
    left = [v for v in re.findall(r"\{\{[^}]+\}\}", prompt + first) if v != "{{...}}"]
    if left:
        sys.exit("unresolved placeholders. This would test a broken script, "
                 "not the agent:\n  %s" % ", ".join(sorted(set(left))))

    heb = len(HEBREW.findall(prompt))
    header = "\n".join([
        "source     : %s" % ("repo at " + args.ref if args.ref else "live assistant"),
        "assistant  : %s  (%s)" % (target["assistant"], target["name"]
                                   if "name" in target else args.target),
        "prompt     : %d chars, %.0f%% Hebrew" % (len(prompt), 100.0 * heb / len(prompt)),
        "model      : %s" % pp.MODEL,
        "tools      : %s" % (", ".join(x["function"]["name"] for x in tools) or "none"),
    ])
    print(header)
    print("\ntools are MOCKED — nothing is written to Supabase or OXS.")
    print("type English and press enter. /quit when done, /he to send Hebrew as-is.\n")

    meter_main, meter_tr = [0, 0], [0, 0]
    rows = []

    def fresh():
        msgs = [{"role": "system", "content": prompt}]
        if first:
            msgs.append({"role": "assistant", "content": first})
            en = translate(first, TO_EN, key, meter_tr)
            print("  agent  [he] : %s" % first)
            print("  agent  [en] : %s\n" % en)
            rows.append({"kind": "agent_first", "he": first, "en": en})
        return msgs

    msgs = fresh()

    while True:
        try:
            typed = input("  you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not typed:
            continue
        if typed in ("/quit", "/q", "/exit"):
            break
        if typed == "/help":
            print(HELP)
            continue
        if typed == "/save":
            p = write_transcript(rows, header, meter_main, meter_tr, args.target)
            print("  saved: %s\n" % (p or "nothing to save yet"))
            continue
        if typed == "/restart":
            rows.append({"kind": "restart"})
            print("\n  — new call —\n")
            msgs = fresh()
            continue

        # Route by script. Anything with a Hebrew character goes verbatim, so
        # pasting a line from the test script tests that exact line; /he forces
        # it for the odd case where you want an English word said in Hebrew.
        if typed.startswith("/he "):
            sent = typed[4:].strip()
        elif HEBREW.search(typed):
            sent = typed
        else:
            sent = translate(typed, TO_HE, key, meter_tr)
        if sent != typed:
            print("  sent   [he] : %s" % sent)

        msgs.append({"role": "user", "content": sent})
        reply, called, a, b = turn(msgs, key, tools)
        meter_main[0] += a
        meter_main[1] += b

        tool_rows = []
        for name, targs, res in called:
            targs_en = gloss(targs, key, meter_tr)
            print("  [tool] %s %s" % (name, j(targs)))
            if j(targs_en) != j(targs):
                print("         in English: %s" % j(targs_en))
            print("         mocked reply: %s" % j(res))
            tool_rows.append((name, targs, res, targs_en))

        en = translate(reply, TO_EN, key, meter_tr)
        print("  agent  [he] : %s" % reply.replace("\n", " / "))
        print("  agent  [en] : %s\n" % en.replace("\n", " / "))
        rows.append({"kind": "turn", "typed": typed, "sent": sent,
                     "tools": tool_rows, "he": reply, "en": en})

    path = write_transcript(rows, header, meter_main, meter_tr, args.target)
    if path:
        print("transcript: %s" % os.path.relpath(path, ROOT).replace("\\", "/"))
    ti = meter_main[0] + meter_tr[0]
    to = meter_main[1] + meter_tr[1]
    print("tokens: %d in, %d out  (about $%.3f at 0.40/1.60 per million)"
          % (ti, to, ti / 1e6 * 0.40 + to / 1e6 * 1.60))


if __name__ == "__main__":
    main()
