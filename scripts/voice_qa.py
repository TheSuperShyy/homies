# -*- coding: utf-8 -*-
"""Claude-played calls with both Hebrew voice agents, and what they would cost on OpenRouter.

    python scripts/voice_qa.py bundle --run DIR    # live prompts, tools, the deck, PLAYER.md
                                                   #   (--deck PATH for another card file)
    python scripts/voice_qa.py cost --run DIR      # OpenRouter price of DIR/transcripts/*.json
    python scripts/voice_qa.py play --run DIR      # SPENDS: the live models on OpenRouter, into DIR/played/
                                                   #   (VOICE_QA_ONLY=id,id to run some; stops at $1)
    python scripts/voice_qa.py say --run DIR < line.json   # SPENDS: one caller line, Claude as the caller
    python scripts/voice_qa.py tenant --run DIR ID         # the caller's protocol, for a Claude player
    python scripts/voice_qa.py report --run DIR --out PREFIX   # PREFIX.md and .html, English from DIR/en.json

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


def run_deck(run):
    """The deck a run was bundled from: bundle copies it into the run folder, so
    cost and play price and play the calls that were bundled, whichever deck."""
    here = os.path.join(run, "deck.json")
    return load(here) if os.path.exists(here) else load(DECK)


def bundle(run, deck_path=DECK):
    import prompt_probe as P
    deck = load(deck_path)
    forms = gender_forms()
    live = {}
    # Only the agents this deck calls (5 Oct: the four incoming calls read the
    # debt agent too, for nothing).
    for target in sorted({s["agent"] for s in deck["scenarios"]}):
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
    # What a call has besides the prompt and tools, for `say` (5 Oct): the
    # model and its settings, the phrases Vapi hangs up on, and the line Vapi
    # speaks while each tool runs. Read live, like everything else here.
    for target in sorted({s["agent"] for s in deck["scenarios"]}):
        a = json.loads(urllib.request.urlopen(urllib.request.Request(
            "https://api.vapi.ai/assistant/" + P.assistant_id(P.TARGETS[target]),
            headers={"Authorization": "Bearer " + P.E["VAPI_PRIVATE_KEY"], "User-Agent": "homies/1.0"}),
            timeout=30).read())
        m = a.get("model") or {}
        write(os.path.join(run, "live_%s.json" % target), json.dumps({
            "assistant": a.get("name"), "updated_at": a.get("updatedAt"),
            "model": "%s/%s" % (m.get("provider"), m.get("model")),
            "temperature": m.get("temperature"),
            # Vapi's own default when the assistant sets none.
            "max_tokens": m.get("maxTokens") or 250,
            "end_call_phrases": a.get("endCallPhrases") or [],
            "max_duration_seconds": a.get("maxDurationSeconds"),
            "waiting_lines": {t["function"]["name"]: x["content"]
                              for t in (m.get("tools") or []) if t.get("function")
                              for x in (t.get("messages") or []) if x.get("type") == "request-start"},
        }, ensure_ascii=False, indent=1))
    player_deck = {"_source": os.path.relpath(deck_path, ROOT).replace(os.sep, "/"),
                   "defaults": deck["defaults"],
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
    deck = {s["id"]: s for s in run_deck(run)["scenarios"]}
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
    deck = run_deck(run)
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


# ---------------------------------------------------------------------------
# say: Claude acts as the caller, one line at a time; the live model answers
# (SPENDS OpenRouter credit)
# ---------------------------------------------------------------------------
# 5 Oct, the owner: "go" on the four incoming calls (estimate about 25 cents).
# The same rule as that morning's WhatsApp run (wa_qa.py say): the tenant is
# Claude acting as the person on the card, one player per card, blind to the
# prompt; only the agent runs on OpenRouter. `play` above, with gpt-4.1-mini
# as the caller, is a smoke test and not the test.
#
# The agent is the live assistant as bundle read it (live_<agent>.json): its
# model, temperature and token cap, the phrases Vapi hangs up on, and the line
# Vapi speaks while a tool runs. The tools answer with the DEPLOYED function's
# own logic replayed on בר כוכבא 23's live rows, read-only, so a lookup gives
# what it would give on a real call today. Nothing is written anywhere.
FN_SRC = os.path.join(ROOT, "supabase", "functions", "debt-tools", "index.ts")
BK23 = "בר כוכבא 23, תל אביב - יפו"
SHARED = ("elevator", "lighting", "cleaning", "gardening", "fire_safety")
SAY_CAP = 1.00
SPOKEN = {"zero": "0", "oh": "0", "o": "0", "nought": "0", "one": "1", "two": "2", "three": "3",
          "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
          "אפס": "0", "אחת": "1", "אחד": "1", "שתיים": "2", "שניים": "2", "שתי": "2", "שני": "2",
          "שלוש": "3", "שלושה": "3", "ארבע": "4", "ארבעה": "4", "חמש": "5", "חמישה": "5",
          "שש": "6", "שישה": "6", "שבע": "7", "שבעה": "7", "שמונה": "8", "תשע": "9", "תשעה": "9"}
NO_BALANCE_READ = ("No single apartment matched, so no balance was read: this is NOT a zero balance. "
                   "Say you could not find it, and ask for or check the street, number and apartment with them.")
NOTE_REASONS = ("hardship", "dispute", "distress", "language", "not_understood", "caller_request", "ownership",
                "out_of_scope", "emergency", "repeated_failure", "payment", "billing", "move", "contract",
                "quote", "other")


def fn_block(start, end):
    src = open(FN_SRC, encoding="utf-8").read()
    i = src.index(start)
    return src[i:src.index(end, i)]


def type_words():
    """TYPE_WORDS, read out of the function itself so the two cannot drift."""
    return {m.group(1): json.loads(m.group(2))
            for m in re.finditer(r"^\s*(\w+):\s*(\[.*?\]),", fn_block("const TYPE_WORDS", "};"), re.M)}


def services():
    """SERVICES, the catalogue get_service_info answers from, read out of the function."""
    block = fn_block("const SERVICES: Topic[] = [", "\n];")
    block = block[block.index("= [") + 2:] + "\n]"
    block = re.sub(r"^\s*//.*$", "", block, flags=re.M)
    block = re.sub(r"(\s)(id|title|words|facts):", r'\1"\2":', block)
    return json.loads(re.sub(r",(\s*[\]}])", r"\1", block))


def key_form(v):
    return (" " + v.lower() + " ").replace(" ה", " ")


def norm_text(v):
    s = re.sub("[\"'`\u05f3\u05f4]", "", str(v or ""))
    s = re.sub(r"(^|\s)(רחוב|רח)(\s|$)", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def has_word(hay, needle):
    start = 0
    while True:
        i = hay.find(needle, start)
        if i < 0:
            return False
        nxt = hay[i + len(needle)] if i + len(needle) < len(hay) else " "
        if len(needle) > 3 or not re.match("[\u0590-\u05ff]", nxt):
            return True
        start = i + 1


def find_topics(query, limit=3):
    q = key_form(norm_text(query))
    if not q.strip():
        return []
    scored = []
    for t in services():
        best = 0
        for w in t["words"]:
            word = key_form(w).strip()
            if word and has_word(q, word) and len(word) > best:
                best = len(word)
        if best:
            scored.append((t, best))
    scored.sort(key=lambda x: -x[1])
    return [t for t, _ in scored[:limit]]


def serial_of(value):
    raw = str(value or "").strip()
    if not re.search(r"\d{4}", raw):
        spoken = "".join(SPOKEN.get(w.lower(), w) for w in re.split(r"[\s,.\-\u2013\u2014]+", raw))
        if re.search(r"\d{4}", spoken):
            raw = spoken
    m = re.search(r"(\d{3})-(\d{4,6})-(\d{2})(?!\d)", raw) or re.search(r"(\d{4})-(\d{3,6})(?!\d)()", raw)
    if m:
        return m.group(2)
    bare = re.sub(r"\D", "", raw)
    return bare if 4 <= len(bare) <= 6 else None


def unit_of(value):
    v = str(value or "").strip()
    return v if v and len(v) <= 12 and re.search(r"\d", v) else None


def spoken_ref(ref):
    m = re.match(r"^\d+-(\d+)-\d+$", str(ref or ""))
    return " ".join(DIGIT_WORDS[int(d)] for d in m.group(1)) if m else None


def with_spoken(out):
    say = spoken_ref(out.get("reference"))
    return dict(out, reference_spoken=say) if say else out


def resolves_bk23(text):
    """matchBuilding, for the one building read here: the street (any spelling
    the transcriber gives) with 23 on it."""
    return on_bar_kochba(text) and has_23(text)


class Bk23:
    """בר כוכבא 23's live rows, read once (GET only), and the deployed lookups
    replayed on them. Only this building is read: the live tools search every
    building, and every other one holds a client's real residents."""

    def __init__(self):
        import urllib.parse
        import prompt_probe as P
        url, key = P.E["SUPABASE_URL"].rstrip("/"), P.E["SUPABASE_SERVICE_ROLE_KEY"]
        h = {"apikey": key, "Authorization": "Bearer " + key, "User-Agent": "homies/1.0"}

        def get(path):
            return json.loads(urllib.request.urlopen(urllib.request.Request(url + "/rest/v1/" + path, headers=h),
                                                     timeout=30).read())
        where = urllib.parse.quote("*" + BK23 + "*")
        self.requests = get("requests?select=reference,type,status,urgency,unit,building,created_at,updated_at,"
                            "description&building=ilike.%s&order=created_at.desc" % where)
        self.residents = get("residents?select=id,full_name,building,unit&building=ilike.%s" % where)
        ids = ",".join(r["id"] for r in self.residents)
        self.charges = get("charges?select=resident_id,period,amount,status,unit&resident_id=in.(%s)"
                           "&order=period.asc" % ids) if ids else []
        self.words = type_words()

    def row(self, r):
        return {"reference": r["reference"], "status": r["status"], "type": r["type"], "urgency": r["urgency"],
                "opened": str(r["created_at"])[:10], "last_update": str(r["updated_at"])[:10],
                "description": str(r["description"])[:200] if r["description"] else None}

    def matches(self, r, kind):
        if not kind or str(r.get("type") or "") == kind:
            return True
        text = str(r.get("description") or "").lower()
        return any(w.lower() in text for w in self.words.get(kind, [kind]))

    def status(self, a):
        """get_request_status, index.ts, inbound voice (no resident on the call)."""
        rows, others, named_nothing, unknown = None, 0, False, None
        serial = serial_of(a.get("reference"))
        if serial:
            rows = [r for r in self.requests if re.search(r"-%s(-|$)" % serial, r["reference"])][:3]
        if not rows:
            short = re.sub(r"\D", "", str(a.get("reference") or ""))
            if len(short) == 3:
                near = [r for r in self.requests if re.search(r"-%s\d-" % short, r["reference"])][:10]
                if len(near) > 3:
                    return {"ok": True, "found": 0, "partial_reference": True, "too_many": len(near), "requests": []}
                if near:
                    return {"ok": True, "found": len(near), "partial_reference": True, "as_of": "live",
                            "requests": [self.row(r) for r in near]}
        if not rows:
            building, unit = str(a.get("building") or ""), unit_of(a.get("unit"))
            if unit and str(a.get("type") or "") in SHARED:
                unit = None
            if building:
                found = resolves_bk23(building)
                needle = BK23 if found else building.strip()
                unknown = not found
                pool = [r for r in self.requests if needle and needle in str(r["building"])]
                if unit:
                    pool = [r for r in pool if str(r["unit"]) == unit]
                pool = pool[:5 if unit else 12]
                kind = str(a.get("type") or "").strip()
                mine = [r for r in pool if self.matches(r, kind)] if kind else pool
                others = len(pool) - len(mine)
                named_nothing = not kind and len(pool) > 1
                rows = mine[:3 if unit else 8]
        rows = rows or []
        out = {"ok": True, "found": len(rows), "as_of": "live", "other_open": others}
        if unknown and not rows:
            out["building_unrecognized"] = True
        if named_nothing:
            out["identify_needed"] = True
        out["requests"] = [{k: v for k, v in self.row(r).items()
                            if not (named_nothing and k in ("type", "urgency", "description"))} for r in rows]
        return out

    def balance(self, a):
        """get_balance, index.ts, inbound voice: no identity gate, no resident on the call."""
        resident, asked = None, None
        building, unit = str(a.get("building") or "").strip(), str(a.get("unit") or "").strip()
        if building and unit and resolves_bk23(building):
            flat = [r for r in self.residents if str(r["unit"]) == unit]
            owing = {c["resident_id"] for c in self.charges if str(c["unit"]) == unit and c["status"] == "unpaid"}
            resident = next((r for r in flat if r["id"] in owing), flat[0] if flat else None)
            if not resident:
                via = next((c for c in self.charges if str(c["unit"]) == unit), None)
                resident = next((r for r in self.residents if via and r["id"] == via["resident_id"]), None)
            asked = unit if resident else None
        if not resident:
            name = str(a.get("name") or "").strip()
            if len(name) >= 2:
                hits = [r for r in self.residents if name.lower() in str(r["full_name"]).lower()][:2]
                if len(hits) > 1:
                    return {"ok": True, "found": 0, "ambiguous_name": True, "note": NO_BALANCE_READ}
                resident = hits[0] if hits else None
        if not resident:
            return {"ok": True, "found": 0, "note": NO_BALANCE_READ}
        mine = [c for c in self.charges if c["resident_id"] == resident["id"] and (asked is None or str(c["unit"]) == asked)]
        owed = [c for c in mine if c["status"] == "unpaid"]
        months = {}
        for c in owed:
            months[str(c["period"])[:7]] = months.get(str(c["period"])[:7], 0) + float(c["amount"])
        units = sorted({str(c["unit"]) for c in owed})
        out = {"ok": True, "found": 1, "resident": resident["full_name"], "building": resident["building"],
               "unit": asked or (units[0] if len(units) == 1 else None),
               "owed_total": int(sum(float(c["amount"]) for c in owed)),
               "owed_months": [{"period": p, "amount": int(v)} for p, v in months.items()],
               "in_review": [{"period": str(c["period"])[:7], "status": c["status"]}
                             for c in mine if c["status"] in ("disputed", "pending_charge")]}
        if len(units) > 1:
            out["owed_apartments"] = [{"unit": u, "total": int(sum(float(c["amount"]) for c in owed if str(c["unit"]) == u)),
                                       "months": [str(c["period"])[:7] for c in owed if str(c["unit"]) == u]} for u in units]
        return out

    def recent_duplicate(self, kind, unit):
        """open_request's 30-minute guard against what is really in the building."""
        import datetime
        since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=30)
        for r in self.requests:
            if (r["type"] == kind and r["status"] in ("open", "in_progress", "needs_review")
                    and str(r["unit"] or "") == str(unit or "")
                    and datetime.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")) >= since):
                return r["reference"]
        return None


def voice_tool(name, a, s, st, bk):
    """What the deployed tool would answer on this call; nothing is written."""
    def mint():
        n = len(st["minted"])
        serial = int(s["ticket"].split("-")[1]) + 10 * n
        ref = "%s-%d-%s" % (s["ticket"].split("-")[0], serial, s["ticket"].split("-")[2])
        st["minted"].append(ref)
        return ref
    if name == "open_request":
        if not a.get("description"):
            return {"ok": False, "error": "description is required"}
        said, kind = str(a.get("building") or ""), a.get("type") or "other"
        if not resolves_bk23(said):
            refuse = {"ok": True, "opened": False, "building_found": False}
            if not said.strip() or (not on_bar_kochba(said) and not re.search(r"\d", said)):
                return dict(refuse, reason="need_building")
            if not on_bar_kochba(said):
                return dict(refuse, reason="street_unknown")
            return dict(refuse, reason="number_not_on_street" if re.search(r"\d", said) else "need_number",
                        street="בר כוכבא", numbers_we_manage=["23"])
        unit = unit_of(a.get("unit"))
        key = "%s|%s" % (kind, unit or "")
        if kind != "complaint":
            held = st["opened"].get(key) or bk.recent_duplicate(kind, unit)
            if held:
                return with_spoken({"ok": True, "reference": held, "duplicate": True})
        if st.get("emergency_stub"):
            ref = st.pop("emergency_stub")
            st["opened"][key] = ref
            return with_spoken({"ok": True, "reference": ref, "completed_emergency": True})
        ref = mint()
        st["opened"][key] = ref
        return with_spoken({"ok": True, "reference": ref})
    if name == "notify_team":
        reason = a.get("reason") if a.get("reason") in NOTE_REASONS else "caller_request"
        out = {"ok": True, "reason": reason, "charges_paused": 0, "emergency_reference": None}
        if reason == "emergency" and not st["opened"] and not st.get("emergency_stub"):
            st["emergency_stub"] = out["emergency_reference"] = mint()
            out["emergency_reference_spoken"] = spoken_ref(out["emergency_reference"])
        out["team_notified"] = True
        return out
    if name == "add_request_detail":
        serial = serial_of(a.get("reference"))
        if not serial:
            return {"ok": False, "error": "no reference"}
        if not str(a.get("detail") or "").strip():
            return {"ok": False, "error": "nothing to add"}
        known = list(st["opened"].values()) + st["minted"] + [r["reference"] for r in bk.requests]
        ref = next((r for r in known if re.search(r"-%s(-|$)" % serial, r)), None)
        return with_spoken({"ok": True, "reference": ref}) if ref else {"ok": False, "error": "not found"}
    if name == "save_partial_request":
        return with_spoken({"ok": True, "reference": mint()})
    if name == "get_request_status":
        return bk.status(a)
    if name == "get_balance":
        return bk.balance(a)
    if name == "get_service_info":
        topics = find_topics(a.get("topic") or a.get("question") or "")
        if not topics:
            return {"ok": True, "found": False,
                    "note": "No topic matched. Say you do not have that detail and offer the office; do not guess."}
        return {"ok": True, "found": True, "topics": [{"title": t["title"], "facts": t["facts"]} for t in topics]}
    return {"ok": False, "error": "unknown tool %s" % name}


class VoiceCall:
    """One incoming call: the live model on OpenRouter, the caller a Claude
    player. Its whole state is DIR/chats/<scenario>.json, so the player can
    drive it one line at a time from separate processes."""

    def __init__(self, run, sid):
        import prompt_probe as P
        self.run, self.key = run, P.E.get("OPENROUTER_API_KEY", "").strip()
        if not self.key:
            sys.exit("OPENROUTER_API_KEY missing from .env")
        self.s = next((x for x in run_deck(run)["scenarios"] if x["id"] == sid), None)
        if not self.s:
            sys.exit("no scenario %r in this run" % sid)
        md = open(os.path.join(run, "context_%s.md" % sid), encoding="utf-8").read()
        self.live = load(os.path.join(run, "live_%s.json" % self.s["agent"]))
        self.tools = json.loads(re.search(r"## The tools\s*\n+```json\n(.*?)\n```", md, re.S).group(1))
        self.path = os.path.join(run, "chats", sid + ".json")
        if os.path.exists(self.path):
            self.st = load(self.path)
        else:
            first = section(md, "The first message")
            self.st = {"scenario": sid, "agent": {k: self.live[k] for k in ("assistant", "updated_at", "model",
                                                                             "temperature", "max_tokens")},
                       "caller": "Claude, acting as the tenant on the card",
                       "messages": [{"role": "system", "content": section(md, "The system prompt")},
                                    {"role": "assistant", "content": first}],
                       "turns": [{"agent": first}], "opened": {}, "minted": [], "usage": [], "ended": ""}

    def spent_run(self):
        """Every call in the run, so parallel players share one cap."""
        total, d = sum(u["cost"] for u in self.st["usage"]), os.path.dirname(self.path)
        for f in (os.listdir(d) if os.path.isdir(d) else []):
            if f.endswith(".json") and f != os.path.basename(self.path):
                try:
                    total += sum(u["cost"] for u in load(os.path.join(d, f)).get("usage", []))
                except (ValueError, OSError):
                    pass            # another player is writing it right now
        return total

    def save(self):
        import datetime
        self.st["saved_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        tr = {k: self.st[k] for k in ("scenario", "agent", "caller", "saved_at", "ended", "turns", "usage")}
        for path, body in ((self.path, self.st), (os.path.join(self.run, "transcripts", self.st["scenario"] + ".json"), tr)):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            write(path + ".tmp", json.dumps(body, ensure_ascii=False, indent=1))
            os.replace(path + ".tmp", path)

    def hear(self, text, en):
        """The caller's line in; what the caller hears back, and whether Vapi hung up."""
        if self.spent_run() > SAY_CAP:
            sys.exit("stopped: the run has spent over the $%.2f cap" % SAY_CAP)
        bk = Bk23()
        st = self.st
        st["turns"].append({"caller": text, "en": en} if en else {"caller": text})
        st["messages"].append({"role": "user", "content": text})
        rounds, heard, finish = [], [], None
        for _ in range(6):
            body = {"model": self.live["model"], "messages": st["messages"], "tools": self.tools,
                    "max_tokens": self.live["max_tokens"], "usage": {"include": True}}
            if self.live.get("temperature") is not None:
                body["temperature"] = self.live["temperature"]
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions", method="POST",
                data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json",
                         "User-Agent": "homies/1.0"})
            r = json.loads(urllib.request.urlopen(req, timeout=180).read())
            if "choices" not in r:
                self.save()
                sys.exit("OpenRouter returned no choices: %s" % json.dumps(r)[:300])
            choice, u = r["choices"][0], r.get("usage") or {}
            st["usage"].append({"in": u.get("prompt_tokens", 0), "out": u.get("completion_tokens", 0),
                                "cached": (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
                                "cost": float(u.get("cost") or 0)})
            msg, finish = choice["message"], choice.get("finish_reason")
            st["messages"].append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
            calls = msg.get("tool_calls") or []
            if not calls:
                break
            if (msg.get("content") or "").strip():
                heard.append(msg["content"].strip())     # Vapi speaks text that comes with a tool call
            rnd = []
            for c in calls:
                try:
                    a = json.loads(c["function"].get("arguments") or "{}")
                except ValueError:
                    a = {"_raw": c["function"].get("arguments")}
                fn = c["function"]["name"]
                if fn in self.live["waiting_lines"]:
                    heard.append(self.live["waiting_lines"][fn])
                res = voice_tool(fn, a, self.s, st, bk)
                rnd.append({"tool": fn, "arguments": a, "result": res})
                st["messages"].append({"role": "tool", "tool_call_id": c["id"],
                                       "content": json.dumps(res, ensure_ascii=False)})
            rounds.append(rnd)
        reply = (msg.get("content") or "").strip()
        heard.append(reply)
        turn = {"agent": reply}
        if rounds:
            turn["rounds"] = rounds
        if len(heard) > 1:
            turn["heard"] = heard
        if finish and finish != "stop":
            turn["finish"] = finish                      # "length": cut off at the token cap
        st["turns"].append(turn)
        said = " ".join(heard).lower()
        hit = next((p for p in self.live["end_call_phrases"] if p.lower() in said), None)
        if hit:
            st["ended"] = 'Michael said "%s", one of the phrases Vapi hangs up on' % hit
        return [h for h in heard if h], bool(hit)


TENANT = """# Calling Homies as a tenant

You are ONE tenant of a building Homies manages, phoning Homies. Michael answers. Michael is the real
agent: its own model answers every line you say, and each line costs a little real credit (the owner
approved this run; the script stops itself at $1). It is a test: nothing is opened, sent or written
anywhere, and no person hears you.

## Who you are

Your card (persona, knows, wants, tendencies) is in the message that started you. You know only the
card. You do not know how Homies works inside, what Michael is told, or what anyone checks. Never say
a fact the card does not give you; asked something you do not know, answer the way this person would.

## How to talk

This is a phone call. Write what this person would really SAY, one turn at a time, in Hebrew, the way
speech-to-text hands it over:
- little or no punctuation; numbers sometimes as digits (23, 8); fillers like אה, רגע, נו, כאילו where
  this person would use them; now and then a word dropped or garbled if the card says the line is bad;
- people on the phone do not answer like a form: they give the address in pieces, answer half a
  question, ask something else instead, repeat themselves, come back to what matters to them;
- the tendencies are things this person MAY do when the moment fits; do not force them and do not
  stage them one after another;
- react honestly to what Michael actually says: long, cold, confusing, repeated, evasive or wrong gets
  this person's real reaction (impatience, confusion, asking again, pushing back, giving up); a good
  answer gets a real reaction too;
- do not help Michael and do not trap him.

## How to speak

Run every command from the repo root with the Bash tool. First pick up the line (no credit is spent):

    cd "C:/Users/Acer nitro 5/Desktop/Homie" && python scripts/voice_qa.py say --run "%(run)s" <<'EOF'
    {"scenario": "%(sid)s", "start": true}
    EOF

Then each thing you say is one command of the same shape:

    cd "C:/Users/Acer nitro 5/Desktop/Homie" && python scripts/voice_qa.py say --run "%(run)s" <<'EOF'
    {"scenario": "%(sid)s", "text": "<what you say>", "en": "<a faithful English gloss of it>"}
    EOF

It prints `you_hear`: what Michael said, in order, including the short line he says while he checks
or writes something. `call` appears when the line goes dead.
- Add `"hangup": true` to the last thing you say if this person hangs up right after saying it
  (Michael does not answer it).
- `en` is for the owner, who does not read Hebrew: what you said, faithfully, garbles included.

## When to stop

End when this person would: once they have what they came for, when they give up, or when the line
goes dead. At most 10 things said. If the person simply stops talking, send
`{"scenario": "%(sid)s", "end": "the tenant stopped talking"}`.

## Rules

- Use only this command. Do not open, read or list any file in the run directory or the repo.
- When you are done, reply with one line: how many times you spoke and how the call ended.
"""


def say(run):
    """One line from a Claude player acting as the caller; prints only what the caller hears."""
    t = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    call = VoiceCall(run, str(t.get("scenario") or ""))
    show = lambda o: print(json.dumps(o, ensure_ascii=False, indent=1))
    if t.get("start"):
        call.save()
        show({"you_hear": [call.st["turns"][0]["agent"]]})
        return
    if t.get("end"):
        call.st["ended"] = call.st["ended"] or str(t["end"])
        call.save()
        show({"ended": call.st["ended"]})
        return
    if call.st["ended"]:
        sys.exit("this call has ended (%s)" % call.st["ended"])
    text = str(t.get("text") or "").strip()
    if not text:
        sys.exit("text is empty: say something, or end the call")
    if sum(1 for x in call.st["turns"] if "caller" in x) >= 10:
        sys.exit("10 lines already: end the call")
    if t.get("hangup"):
        call.st["turns"].append(dict({"caller": text, "hung_up": True}, **({"en": t["en"]} if t.get("en") else {})))
        call.st["ended"] = "the caller hung up"
        call.save()
        show({"you_hear": [], "call": "you hung up"})
        return
    heard, ended = call.hear(text, t.get("en"))
    call.save()
    out = {"you_hear": heard}
    if ended:
        out["call"] = "the line went dead: Michael hung up"
    show(out)


def tenant(run, sid):
    print(TENANT % {"run": run.replace("\\", "/"), "sid": sid})


# ---------------------------------------------------------------------------
# report: the calls of a `say` run as a document (Markdown, and HTML that
# pastes into Google Docs with the Hebrew right to left)
# ---------------------------------------------------------------------------
# 5 Oct, the owner: "extract the transcription of it and we will put it in a
# gdocs for documentation". The Hebrew is copied from the transcripts, never
# retyped; the English and the notes come from DIR/en.json, written by whoever
# read the calls. The owner does not read Hebrew, so every line has English.
WAIT_EN = {"רגע, אני רושם את זה.": "One moment, I'm writing that down.",
           "שנייה, אני בודק.": "One second, I'm checking."}


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def call_rows(tr, en, deck_s):
    """(who, hebrew, english, kind) per line, kind in say/wait/tool/end."""
    rows, name, name_en = [], deck_s["caller"]["persona"].split(",")[0].strip(), en.get("tenant_en", "Tenant")
    for i, t in enumerate(tr["turns"]):
        k = str(i)
        if "caller" in t:
            # A hang-up is said once, by the closing line below.
            rows.append((name_en, t["caller"], en.get("caller_en", {}).get(k) or t.get("en", ""), "say"))
            continue
        heard = t.get("heard") or [t.get("agent", "")]
        # In the order the caller met them: anything spoken as a tool starts
        # (the waiting line, or text the model sent with the call), what the
        # tools did, then the answer. heard_en[turn] is the English for the
        # non-waiting lines, in order.
        extra = list(en.get("heard_en", {}).get(k, []))
        for h in heard[:-1]:
            if h in WAIT_EN:
                rows.append(("Michael", h, WAIT_EN[h], "wait"))
            else:
                rows.append(("Michael", h, extra.pop(0) if extra else "", "say"))
        for line in en.get("tools_en", {}).get(k, []):
            rows.append(("", "", line, "tool"))
        label = "Michael (first words, fixed)" if i == 0 else "Michael"
        rows.append((label, heard[-1], en.get("agent_en", {}).get(k, ""), "say"))
        if t.get("finish") == "length":
            rows.append(("", "", "The reply was cut off here: it reached the live agent's limit on how long one turn can be.", "end"))
    rows.append(("", "", en.get("ended_en") or tr.get("ended", ""), "end"))
    return rows


def usage_of(tr):
    u = tr.get("usage") or []
    return {"calls": len(u), "in": sum(x["in"] for x in u), "cached": sum(x.get("cached", 0) for x in u),
            "out": sum(x["out"] for x in u), "cost": sum(x["cost"] for x in u)}


def words_of(tr):
    w = [len(t["agent"].split()) for t in tr["turns"][1:] if "agent" in t and t.get("agent")]
    return (sum(w) / len(w) if w else 0, max(w) if w else 0)


def report(run, out):
    en = load(os.path.join(run, "en.json"))
    deck = {s["id"]: s for s in run_deck(run)["scenarios"]}
    live = load(os.path.join(run, "live_inbound.json"))
    trs = {sid: load(os.path.join(run, "transcripts", sid + ".json")) for sid in en["order"]}
    md, ht = [], []
    md += ["# " + en["title"], "", en["subtitle"], ""]
    ht += ["<h1>%s</h1>" % _esc(en["title"]), "<p>%s</p>" % _esc(en["subtitle"])]
    for title, items in (("How this test was run", en["how"]), ("What we found", en["findings"])):
        md += ["## " + title, ""] + [("%d. " % (n + 1) if title == "What we found" else "- ") + x
                                      for n, x in enumerate(items)] + [""]
        tag = "ol" if title == "What we found" else "ul"
        ht += ["<h2>%s</h2>" % title, "<%s>" % tag] + ["<li>%s</li>" % _esc(x) for x in items] + ["</%s>" % tag]
    head = ["Call", "What the tenant wanted", "The tenant", "How it went"]
    md += ["## The four calls at a glance", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    ht += ["<h2>The four calls at a glance</h2>", '<table border="1" cellpadding="6" style="border-collapse:collapse">',
           "<tr>" + "".join("<th>%s</th>" % h for h in head) + "</tr>"]
    for n, sid in enumerate(en["order"]):
        c = en["calls"][sid]
        cells = [str(n + 1), c["job"], c["tenant"], c["outcome"]]
        md.append("| " + " | ".join(x.replace("|", "/") for x in cells) + " |")
        ht.append("<tr>" + "".join("<td>%s</td>" % _esc(x) for x in cells) + "</tr>")
    md.append("")
    ht.append("</table>")
    head = ["Call", "Model calls", "Tokens in (of them cached)", "Tokens out", "Michael's words a turn (average / longest)", "Cost"]
    md += ["## What it cost", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    ht += ["<h2>What it cost</h2>", '<table border="1" cellpadding="6" style="border-collapse:collapse">',
           "<tr>" + "".join("<th>%s</th>" % h for h in head) + "</tr>"]
    tot = {"calls": 0, "in": 0, "cached": 0, "out": 0, "cost": 0.0}
    for n, sid in enumerate(en["order"]):
        u, (avg, mx) = usage_of(trs[sid]), words_of(trs[sid])
        for k in tot:
            tot[k] += u[k]
        cells = ["%d. %s" % (n + 1, en["calls"][sid]["job"]), str(u["calls"]), "{:,} ({:,})".format(u["in"], u["cached"]),
                 "{:,}".format(u["out"]), "%.0f / %d" % (avg, mx), "$%.4f" % u["cost"]]
        md.append("| " + " | ".join(cells) + " |")
        ht.append("<tr>" + "".join("<td>%s</td>" % _esc(x) for x in cells) + "</tr>")
    cells = ["**Total**", str(tot["calls"]), "{:,} ({:,})".format(tot["in"], tot["cached"]), "{:,}".format(tot["out"]), "", "**$%.4f**" % tot["cost"]]
    md += ["| " + " | ".join(cells) + " |", ""]
    for x in en["cost_notes"]:
        md += [x, ""]
    ht += ["<tr>" + "".join("<td><b>%s</b></td>" % _esc(x.strip("*")) for x in cells) + "</tr>", "</table>"]
    ht += ["<p>%s</p>" % _esc(x) for x in en["cost_notes"]]
    for n, sid in enumerate(en["order"]):
        c, tr = en["calls"][sid], trs[sid]
        md += ["## Call %d. %s" % (n + 1, c["heading"]), "", "*%s*" % c["setting"], ""]
        ht += ["<h2>Call %d. %s</h2>" % (n + 1, _esc(c["heading"])), "<p><i>%s</i></p>" % _esc(c["setting"]),
               '<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">',
               "<tr><th>Who</th><th>English</th><th>Hebrew, as said</th></tr>"]
        for who, he, eng, kind in call_rows(tr, c, deck[sid]):
            if kind in ("tool", "end"):
                md += ["> *%s%s*" % ("Behind the scenes: " if kind == "tool" else "", eng), ""]
                ht.append('<tr><td colspan="3" style="background:#f2f2f2"><i>%s%s</i></td></tr>'
                          % ("Behind the scenes: " if kind == "tool" else "", _esc(eng)))
                continue
            label = who + (", while the system works" if kind == "wait" else "")
            # One spoken turn is one paragraph: the model's line breaks are
            # not pauses anybody hears, and in Markdown they split the turn
            # from its English.
            he = re.sub(r"\s*\n+\s*", " ", he)
            md += ["**%s:** %s  " % (label, he), "*%s*" % eng, ""]
            ht.append('<tr><td><b>%s</b></td><td>%s</td><td dir="rtl" style="text-align:right">%s</td></tr>'
                      % (_esc(label), _esc(eng), _esc(he)))
        md += ["**What this call shows:**", ""] + ["- " + x for x in c["shows"]] + [""]
        ht += ["</table>", "<p><b>What this call shows:</b></p>", "<ul>"] + ["<li>%s</li>" % _esc(x) for x in c["shows"]] + ["</ul>"]
    md += ["## How it was run (technical)", ""] + ["- " + x for x in en["technical"]] + [""]
    ht += ["<h2>How it was run (technical)</h2>", "<ul>"] + ["<li>%s</li>" % _esc(x) for x in en["technical"]] + ["</ul>"]
    write(out + ".md", "\n".join(md))
    write(out + ".html", "\n".join(['<!doctype html>', '<html lang="en"><head><meta charset="utf-8">',
                                    '<meta name="viewport" content="width=device-width, initial-scale=1">',
                                    "<title>%s</title>" % _esc(en.get("short_title", en["title"])),
                                    "<style>body{font-family:Arial,sans-serif;max-width:1000px;margin:24px auto;padding:0 16px;"
                                    "line-height:1.45;background:#fff;color:#111}td,th{vertical-align:top;text-align:left}"
                                    "th{background:#e8e8e8}</style></head><body>"] + ht + ["</body></html>"]))
    print("wrote %s.md and %s.html (%d calls, $%.4f)" % (out, out, len(en["order"]), tot["cost"]))


def main():
    argv = sys.argv[1:]
    if len(argv) >= 3 and argv[0] == "tenant" and argv[1] == "--run":
        return tenant(argv[2], argv[3] if len(argv) > 3 else "<id>")
    if len(argv) >= 5 and argv[0] == "report" and argv[1] == "--run" and argv[3] == "--out":
        return report(argv[2], argv[4])
    if len(argv) < 3 or argv[1] != "--run":
        sys.exit(__doc__)
    if argv[0] == "bundle":
        # --deck picks another card file (5 Oct: scripts/voice_qa_inbound_4.json);
        # cost and play then read the copy bundle leaves in the run folder.
        deck = argv[argv.index("--deck") + 1] if "--deck" in argv else DECK
        return bundle(argv[2], deck)
    {"cost": cost, "play": play, "say": say}.get(argv[0], lambda run: sys.exit(__doc__))(argv[2])


if __name__ == "__main__":
    main()
