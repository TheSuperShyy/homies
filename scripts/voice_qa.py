# -*- coding: utf-8 -*-
"""Claude-played calls with both Hebrew voice agents, and what they would cost on OpenRouter.

    python scripts/voice_qa.py bundle --run DIR    # live prompts, tools, the deck, PLAYER.md
    python scripts/voice_qa.py cost --run DIR      # OpenRouter price of DIR/transcripts/*.json

WHY, 5 Oct. The owner, after the WhatsApp runs: *"test the voice agent both of
them in 3 scenarios as well like the one we did in the chatbot, i want to know if
you use openroutercredits to simulae the llm how much will it cost"*. A call costs
Vapi money and the owner places the test calls himself, so the calls here are
played offline: a Claude player is the caller on a card (scripts/voice_qa_scenarios.json)
and the agent's model, on the live system prompt and tools read from Vapi (GET
only). Unlike the WhatsApp bot there is no code around the model on a call:
what the model writes is what the voice says, so the prompt rendered for the
call's hour and the tools are the whole context.

`cost` answers the second half from the same transcripts: every model call a
real run would make (one per spoken turn, one more per round of tool calls),
each carrying the system prompt, the tools and the conversation so far, counted
with the o200k tokenizer and priced from OpenRouter's public model list. It
spends nothing; it prices what a run through prompt_probe.py would have cost.

WHAT IT DOES NOT TEST: audio. Speech recognition, the voice, pace and barge-in
live in Vapi and Cartesia; only a call tests them.
"""
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DECK = os.path.join(HERE, "voice_qa_scenarios.json")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def gender_forms():
    """The phrases dashboard/lib/call.ts hands the debt agent, by gender."""
    src = open(os.path.join(ROOT, "dashboard", "lib", "call.ts"), encoding="utf-8").read()
    block = src[src.index("const GENDER_FORMS"):]
    block = block[:block.index("};")]
    out = {}
    for key in ("f", "m", "unknown"):
        m = re.search(r"\b%s:\s*((?:'[^']*'\s*\+?\s*)+)" % key, block)
        out[key] = "".join(re.findall(r"'([^']*)'", m.group(1))) if m else ""
    return out


PLAYER = """# Playing a Homies voice call offline

You stand in for the model of one of Homies' two Hebrew voice agents, for ONE call, and you
also play the person on the other end. Nothing you write reaches anyone and nothing is dialled.

## The agent

`context_<scenario>.md` holds what the model has on this call: the system prompt exactly as
Vapi renders it at the call's time (template values filled in), the first message, and the
tools. Play that model faithfully: write what a capable model reading that prompt and those
tools would say. Do not optimise for any test, do not improve on the prompt, do not skip rules
you dislike, and do not follow rules it does not contain. Its words go straight to a voice, so
write them as the model would for speech.

The call opens with the first message (the agent's first words, fixed by Vapi; it is not a
model turn). After every caller turn the model may call tools (any number of rounds) and then
speaks. A tool returns the scenario's fixture for it, else the deck's `defaults`; follow a
fixture's `_rule` where it has one, and fill `<ticket>` and `<spoken>` from the scenario.

## The caller

You know only the card (`persona`, `knows`, `wants`, `tendencies`). Speak as that person on a
phone, one utterance per turn, and write it the way speech-to-text hands it to the agent:
little or no punctuation, numbers sometimes as digits, fillers ("אה", "רגע"), now and then a
garbled word. React only to what the agent actually said. Do not help the agent and do not trap
it. The `tendencies` are things the person MAY do when the moment fits. End the call when the
person would (a goodbye, or hanging up), at most 8 caller turns.

## Output

Write `transcripts/<scenario>.json`, valid JSON:

```json
{"scenario": "in_lift_stuck", "turns": [
  {"agent": "<the first message>", "en": "<English>"},
  {"caller": "<what the caller said, as speech-to-text gives it>", "en": "<English>"},
  {"rounds": [[{"tool": "open_request", "arguments": {}, "result": {}}]],
   "agent": "<what the model then said>", "en": "<English>"},
  {"caller": "...", "en": "..."}
]}
```

`rounds` lists the model calls that ended in tool calls before it spoke, each round the calls it
made at once, in order; leave it out when no tool ran. The English is a faithful translation for
the owner, who does not read Hebrew: keep the tone and anything awkward as it is.
"""


def bundle(run):
    import prompt_probe as P
    deck = load(DECK)
    forms = gender_forms()
    live = {}
    for target in ("inbound", "debt"):
        prompt, first, tools = P.live_prompt(P.TARGETS[target])
        live[target] = (prompt, first, tools)
        print("%-8s live prompt %d chars, first message %d chars, tools: %s"
              % (target, len(prompt), len(first), ", ".join(t["function"]["name"] for t in tools)))
    os.makedirs(os.path.join(run, "transcripts"), exist_ok=True)
    for s in deck["scenarios"]:
        prompt, first, tools = live[s["agent"]]
        values = dict(s.get("vars") or {})
        if "gender" in values:
            values["gender_forms"] = forms.get(values.pop("gender"), forms["unknown"])
        for k, v in values.items():
            prompt = prompt.replace("{{%s}}" % k, v)
            first = first.replace("{{%s}}" % k, v)
        hh, mm = (int(x) for x in s["time"].split(":"))
        import datetime
        now = datetime.datetime(2026, 10, 5, hh, mm)
        prompt = P.render_now(P.render_greeting(prompt, hh), now)
        first = P.render_now(P.render_greeting(first, hh), now)
        left = [v for v in re.findall(r"\{\{[^}]+\}\}", prompt + first) if v != "{{...}}"]
        if left:
            sys.exit("%s: unresolved placeholders %s" % (s["id"], sorted(set(left))))
        write(os.path.join(run, "context_%s.md" % s["id"]), "\n".join([
            "# %s: what the model has on this call" % s["id"], "",
            "Israel time %s, יום %s. Agent: %s." % (s["time"], s["weekday_he"], s["agent"]), "",
            "## The system prompt (verbatim, as rendered for this call)", "", "````", prompt, "````", "",
            "## The first message (spoken by Vapi before the model's first turn)", "", "````", first, "````", "",
            "## The tools", "", "```json", json.dumps(tools, ensure_ascii=False, indent=1), "```", ""]))
    player_deck = {"defaults": deck["defaults"],
                   "scenarios": [{k: v for k, v in s.items() if k != "expect"} for s in deck["scenarios"]]}
    write(os.path.join(run, "deck.json"), json.dumps(player_deck, ensure_ascii=False, indent=1))
    write(os.path.join(run, "PLAYER.md"), PLAYER)
    print("bundled %d calls into %s" % (len(deck["scenarios"]), run))


# ---------------------------------------------------------------------------
# cost: what these exact calls would have cost through OpenRouter
# ---------------------------------------------------------------------------
LIVE_MODEL = {"inbound": "openai/gpt-4.1", "debt": "openai/gpt-5.6-sol"}


def prices(ids):
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/models", headers={"User-Agent": "homies/1.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=30).read())["data"]
    except Exception as e:  # noqa: BLE001
        sys.exit("could not read OpenRouter's model list: %s" % e)
    out = {}
    for m in data:
        if m["id"] in ids:
            p = m["pricing"]
            out[m["id"]] = (float(p["prompt"]) * 1e6, float(p["completion"]) * 1e6,
                            float(p.get("input_cache_read") or 0) * 1e6)
    return out


def calls_of(context_md, transcript, enc):
    """Every model call the transcript implies: (input tokens, output tokens)."""
    sysp = re.search(r"## The system prompt.*?\n````\n(.*?)\n````", context_md, re.S).group(1)
    tools = re.search(r"## The tools\s*\n+```json\n(.*?)\n```", context_md, re.S).group(1)
    base = len(enc.encode(sysp)) + len(enc.encode(json.dumps(json.loads(tools), ensure_ascii=False)))
    hist, calls = 0, []
    for t in transcript["turns"]:
        if "caller" in t:
            hist += len(enc.encode(t["caller"])) + 4
            continue
        if "rounds" not in t and t is transcript["turns"][0]:
            hist += len(enc.encode(t.get("agent", ""))) + 4      # the first message, not a model call
            continue
        for rnd in t.get("rounds") or []:
            out = sum(len(enc.encode(json.dumps({"name": c["tool"], "arguments": c.get("arguments")},
                                                ensure_ascii=False))) for c in rnd)
            calls.append((base + hist, out))
            hist += out + sum(len(enc.encode(json.dumps(c.get("result"), ensure_ascii=False))) + 6 for c in rnd)
        said = len(enc.encode(t.get("agent", "")))
        calls.append((base + hist, said))
        hist += said + 4
    return base, calls


def cost(run):
    import tiktoken
    enc = tiktoken.get_encoding("o200k_base")
    deck = {s["id"]: s for s in load(DECK)["scenarios"]}
    sim = "openai/gpt-4.1-mini"     # a cheap caller, if a model played the resident instead of Claude
    pr = prices(set(LIVE_MODEL.values()) | {sim, "anthropic/claude-sonnet-4.5"})
    tdir = os.path.join(run, "transcripts")
    rows, tot = [], {"in": 0, "out": 0, "calls": 0, "agent": 0.0, "cached": 0.0, "caller": 0.0}
    for fn in sorted(os.listdir(tdir)):
        tr = load(os.path.join(tdir, fn))
        s = deck[tr["scenario"]]
        ctx = open(os.path.join(run, "context_%s.md" % s["id"]), encoding="utf-8").read()
        base, calls = calls_of(ctx, tr, enc)
        model = LIVE_MODEL[s["agent"]]
        pin, pout, pcache = pr[model]
        tin, tout = sum(c[0] for c in calls), sum(c[1] for c in calls)
        full = tin / 1e6 * pin + tout / 1e6 * pout
        # The system prompt and tools are the same on every call, so after the
        # first call OpenAI's automatic prompt cache bills them at the read price.
        cached = full - (len(calls) - 1) * base / 1e6 * (pin - pcache) if calls else 0.0
        # A model playing the caller: its own short prompt (the card, ~600) plus the
        # conversation, once per caller turn, at the cheap model's price.
        cturns = [t for t in tr["turns"] if "caller" in t]
        conv = sum(len(enc.encode(t.get("caller") or t.get("agent") or "")) for t in tr["turns"])
        cin = len(cturns) * (600 + conv // 2)
        cout = sum(len(enc.encode(t["caller"])) for t in cturns)
        caller = cin / 1e6 * pr[sim][0] + cout / 1e6 * pr[sim][1]
        rows.append((s["id"], model, len(calls), tin, tout, full, cached, caller))
        for k, v in (("in", tin), ("out", tout), ("calls", len(calls)), ("agent", full), ("cached", cached), ("caller", caller)):
            tot[k] += v
    print("%-18s %-20s %5s %8s %6s %9s %9s %9s" % ("call", "agent model", "calls", "tok in", "out", "$ agent", "$ cached", "$ caller"))
    for r in rows:
        print("%-18s %-20s %5d %8d %6d %9.4f %9.4f %9.4f" % r)
    print("%-18s %-20s %5d %8d %6d %9.4f %9.4f %9.4f" % ("TOTAL", "", tot["calls"], tot["in"], tot["out"],
                                                       tot["agent"], tot["cached"], tot["caller"]))
    for m, (a, b, c) in sorted(pr.items()):
        print("price %-28s in $%.2f/M  out $%.2f/M  cached in $%.2f/M" % (m, a, b, c))
    return rows, tot


def main():
    argv = sys.argv[1:]
    if len(argv) < 3 or argv[1] != "--run":
        sys.exit(__doc__)
    {"bundle": bundle, "cost": cost}.get(argv[0], lambda run: sys.exit(__doc__))(argv[2])


if __name__ == "__main__":
    main()
