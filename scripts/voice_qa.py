# -*- coding: utf-8 -*-
"""Claude-played calls with both Hebrew voice agents, and what they would cost on OpenRouter.

    python scripts/voice_qa.py bundle --run DIR    # live prompts, tools, the deck, PLAYER.md
    python scripts/voice_qa.py cost --run DIR      # OpenRouter price of DIR/transcripts/*.json
    python scripts/voice_qa.py play --run DIR      # SPENDS: the live models on OpenRouter, into DIR/played/
                                                   #   (VOICE_QA_ONLY=id,id to run some; stops at $1)

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


# ---------------------------------------------------------------------------
# play: the same calls with the live models on OpenRouter (SPENDS CREDIT)
# ---------------------------------------------------------------------------
# 5 Oct, the owner's go after the estimate ("ok go", ~$0.30 for 6 calls). The
# agent is the live model with the live settings (Vapi GET: inbound gpt-4.1 at
# 0.3, debt gpt-5.6-sol with nothing set); a cheap model plays the caller from
# the card. The tools are stand-ins that follow the deck's rules in code, so
# nothing is written anywhere. Vapi hangs up when the agent says one of the
# assistants' endCallPhrases, so the call ends there too.
CALLER_MODEL = "openai/gpt-4.1-mini"
TEMPERATURE = {"inbound": 0.3, "debt": None}
END_PHRASES = ("יום טוב", "ולהתראות")
SPEND_CAP = 1.00            # dollars for the whole run; stops before a call that would pass it
DIGIT_WORDS = "אפס אחת שתיים שלוש ארבע חמש שש שבע שמונה תשע".split()
MONTHS_HE = ("ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט", "ספטמבר",
             "אוקטובר", "נובמבר", "דצמבר")

CALLER_PROMPT = """You are the person on the card below, on a phone call with Homies, the company that \
manages your building. Michael from Homies is the voice on the other end.

Speak as that person, one utterance per turn, in Hebrew, written the way speech-to-text hands it to \
the agent: little or no punctuation, numbers sometimes as digits, fillers ("אה", "רגע") where a \
person would use them, now and then a garbled word. React only to what was actually said to you. \
Do not help the agent and do not trap it. The tendencies are things the person MAY do when the \
moment fits, not a script. Hang up when the person would.

Answer with JSON only: {"say": "<what you say>", "hang_up": <true if you hang up after saying it>}

The card:
%s"""


def section(md, title):
    return re.search(r"## %s.*?\n````\n(.*?)\n````" % re.escape(title), md, re.S).group(1)


def openrouter(key, body):
    body = dict(body, usage={"include": True})
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions", method="POST",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "User-Agent": "homies/1.0"})
    r = json.loads(urllib.request.urlopen(req, timeout=180).read())
    if "choices" not in r:
        sys.exit("OpenRouter returned no choices: %s" % json.dumps(r)[:300])
    return r["choices"][0]["message"], r.get("usage") or {}


def has_23(text):
    return bool(re.search(r"(?<!\d)23(?!\d)|עשרים ו?שלוש", text or ""))


def on_bar_kochba(text):
    return bool(re.search(r"כוכב|kochba|kokhba", text or "", re.I))


def fill(value, s):
    """The deck's <ticket>, <spoken>, phone and month placeholders, for this scenario."""
    if isinstance(value, dict):
        return {k: fill(v, s) for k, v in value.items() if not k.startswith("_")}
    if not isinstance(value, str):
        return value
    middle = s["ticket"].split("-")[1]
    months = sum(1 for m in MONTHS_HE if m in (s.get("vars") or {}).get("months_phrase", "")) or 1
    swap = {"<ticket>": s["ticket"], "<spoken>": " ".join(DIGIT_WORDS[int(d)] for d in middle),
            "<the phone's last four digits on the card>": s.get("phone_last4", "0000"),
            "<number of months>": months}
    return swap.get(value, value)


def stand_in(name, args, s, defaults, opened):
    """What the tool returns on this call, following the deck's rules."""
    fx = (s.get("fixtures") or {}).get(name)
    building, unit = str(args.get("building") or ""), str(args.get("unit") or "")
    ours = on_bar_kochba(building) and has_23(building)
    if name == "get_request_status" and fx:
        return fill(fx["found" if has_23(building) or args.get("reference") == "255-1478-26" else "not_found"], s)
    if name == "get_balance" and fx:
        eleven = re.search(r"(?<!\d)11(?!\d)|אחת[- ]עשרה", unit) or "לוי" in str(args.get("name") or "")
        return fill(fx["found" if ours and eleven else "not_found"], s)
    if fx:
        return fill(fx, s)
    d = defaults.get(name, {"ok": True})
    if name == "open_request":
        if s["agent"] == "inbound" and not ours:
            if not building.strip():
                return {"ok": True, "opened": False, "building_found": False, "reason": "need_building"}
            if not on_bar_kochba(building):
                return fill(d["street_unknown"], s)
            if re.search(r"\d", building):
                return {"ok": True, "opened": False, "building_found": False,
                        "reason": "number_not_on_street", "street": "בר כוכבא", "numbers_we_manage": ["23"]}
            return dict(fill(d["need_number"], s), street="בר כוכבא")
        kind = args.get("type") or "other"
        if kind in opened:
            return dict(fill(d["opened"], s), duplicate=True)
        opened.add(kind)
        return fill(d["opened"], s)
    return fill(d, s)


def play(run):
    import datetime
    import prompt_probe as P
    key = P.E.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        sys.exit("OPENROUTER_API_KEY missing from .env")
    deck = load(DECK)
    only = os.environ.get("VOICE_QA_ONLY", "").split(",") if os.environ.get("VOICE_QA_ONLY") else None
    out_dir = os.path.join(run, "played")
    os.makedirs(out_dir, exist_ok=True)
    spent = 0.0
    for s in deck["scenarios"]:
        if only and s["id"] not in only:
            continue
        md = open(os.path.join(run, "context_%s.md" % s["id"]), encoding="utf-8").read()
        prompt = section(md, "The system prompt")
        first = section(md, "The first message")
        tools = json.loads(re.search(r"## The tools\s*\n+```json\n(.*?)\n```", md, re.S).group(1))
        card = json.dumps(s["caller"], ensure_ascii=False, indent=1)
        agent_msgs = [{"role": "system", "content": prompt}, {"role": "assistant", "content": first}]
        caller_msgs = [{"role": "system", "content": CALLER_PROMPT % card}, {"role": "user", "content": first}]
        turns, usage, opened, ended = [{"agent": first}], [], set(), "caller turns ran out (8)"
        print("\n=== %s (%s, %s)" % (s["id"], s["agent"], LIVE_MODEL[s["agent"]]))
        print("  agent : %s" % first)

        def bill(who, u):
            nonlocal spent
            c = float(u.get("cost") or 0)
            spent += c
            usage.append({"who": who, "in": u.get("prompt_tokens", 0), "out": u.get("completion_tokens", 0),
                          "cached": (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
                          "reasoning": (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0),
                          "cost": c})
            if spent > SPEND_CAP:
                write(os.path.join(out_dir, "%s.json" % s["id"]), json.dumps(
                    {"scenario": s["id"], "turns": turns, "usage": usage, "ended": "spend cap"}, ensure_ascii=False, indent=1))
                sys.exit("stopped: spent $%.4f, over the $%.2f cap" % (spent, SPEND_CAP))

        for _ in range(8):
            msg, u = openrouter(key, {"model": CALLER_MODEL, "messages": caller_msgs, "temperature": 0.7,
                                      "response_format": {"type": "json_object"}})
            bill("caller", u)
            try:
                said = json.loads(msg.get("content") or "{}")
            except ValueError:
                said = {"say": msg.get("content") or "", "hang_up": False}
            text = str(said.get("say") or "").strip()
            caller_msgs.append({"role": "assistant", "content": msg.get("content") or ""})
            if text:
                turns.append({"caller": text})
                agent_msgs.append({"role": "user", "content": text})
                print("  caller: %s%s" % (text, "  [hangs up]" if said.get("hang_up") else ""))
            if said.get("hang_up"):
                ended = "the caller hung up"
                break
            rounds = []
            for _ in range(6):
                body = {"model": LIVE_MODEL[s["agent"]], "messages": agent_msgs, "tools": tools}
                if TEMPERATURE[s["agent"]] is not None:
                    body["temperature"] = TEMPERATURE[s["agent"]]
                msg, u = openrouter(key, body)
                bill("agent", u)
                calls = msg.get("tool_calls") or []
                agent_msgs.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
                if not calls:
                    break
                rnd = []
                for c in calls:
                    try:
                        a = json.loads(c["function"].get("arguments") or "{}")
                    except ValueError:
                        a = {"_raw": c["function"].get("arguments")}
                    res = stand_in(c["function"]["name"], a, s, deck["defaults"], opened)
                    rnd.append({"tool": c["function"]["name"], "arguments": a, "result": res})
                    agent_msgs.append({"role": "tool", "tool_call_id": c["id"],
                                       "content": json.dumps(res, ensure_ascii=False)})
                    print("  [tool] %s %s -> %s" % (c["function"]["name"], json.dumps(a, ensure_ascii=False),
                                                   json.dumps(res, ensure_ascii=False)))
                rounds.append(rnd)
            reply = (msg.get("content") or "").strip()
            turn = {"agent": reply}
            if rounds:
                turn = {"rounds": rounds, "agent": reply}
            turns.append(turn)
            caller_msgs.append({"role": "user", "content": reply})
            print("  agent : %s" % reply.replace("\n", " / "))
            hit = next((p for p in END_PHRASES if p in reply), None)
            if hit:
                ended = "the agent said \"%s\" (an end-call phrase), Vapi hangs up" % hit
                break
        cost_here = sum(x["cost"] for x in usage)
        print("  -- %s; $%.4f (agent $%.4f, caller $%.4f)" % (
            ended, cost_here, sum(x["cost"] for x in usage if x["who"] == "agent"),
            sum(x["cost"] for x in usage if x["who"] == "caller")))
        write(os.path.join(out_dir, "%s.json" % s["id"]), json.dumps(
            {"scenario": s["id"], "agent_model": LIVE_MODEL[s["agent"]], "caller_model": CALLER_MODEL,
             "played_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
             "turns": turns, "ended": ended, "usage": usage}, ensure_ascii=False, indent=1))
    print("\nspent $%.4f in all (OpenRouter's own per-request cost)" % spent)


def main():
    argv = sys.argv[1:]
    if len(argv) < 3 or argv[1] != "--run":
        sys.exit(__doc__)
    {"bundle": bundle, "cost": cost, "play": play}.get(argv[0], lambda run: sys.exit(__doc__))(argv[2])


if __name__ == "__main__":
    main()
