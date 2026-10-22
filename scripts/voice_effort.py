# -*- coding: utf-8 -*-
"""The same moments of played calls, answered again at each thinking level, and timed.

    python scripts/voice_effort.py list --run DIR      # each call's model turns, numbered (free)
    python scripts/voice_effort.py replay --run DIR --points nm_gas:1,nm_light_noname:4
                                    [--efforts default,low,none] [--cap 0.50]
                                                       # SPENDS OpenRouter credit; DIR/effort.json
    python scripts/voice_effort.py report --run DIR    # the summary again, from effort.json (free)

WHY, 22 Oct. The owner, on the incoming agent's wait between turns: *"ok lets
fix that and test it automatically"*. On 21 Oct the model took 1.5 s a turn on
average and up to 3.6 s, slowest after a tool. gpt-5.6-sol thinks before it
speaks, and the agent leaves `reasoningEffort` unset, which for this model is
`medium` (OpenRouter's model list: efforts max, xhigh, high, medium, low, none;
NOT minimal, although Vapi's enum offers it). A lower level answers sooner.
This measures how much sooner, and whether the answers stay the same.

DIR is a `voice_qa.py say` run. Its chats hold every message each model call
saw, so a moment is replayed exactly: the same system prompt, tools and
conversation, with only the thinking level changed. Each answer is timed from
the request to its first word (what a caller waits for before the voice starts)
and to its end (what a tool call waits for before it can run). Its action is
compared with what the model did in the original run: the same tool with the
same name fields, or the same question. The order of the levels rotates from
moment to moment, so each moment's cold first call is spread evenly across them.

WHAT IT DOES NOT MEASURE: Vapi's own path (the voice, the transcriber, the wait
for the caller to finish) and Vapi's route to OpenAI. OpenRouter's times
compare the levels with each other; a call through 208 and `vapi_latency.py`
give the real ones.
"""
import json
import os
import re
import statistics
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from check_name_flow import NAME_ASK, asks_phone  # noqa: E402

LEVELS = ("default", "low", "none")      # default = unset, which is what live has
CAP = 0.50                              # dollars for the whole replay, effort.json included


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write(path, obj):
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)


def model_turns(chat):
    """Each model call of a played call: (the messages it saw, what it answered).
    messages[1] is Vapi's first message, spoken before any model call."""
    msgs = chat["messages"]
    return [(msgs[:i], m) for i, m in enumerate(msgs) if m["role"] == "assistant" and i > 1]


def action(msg):
    """What a reply does, in the terms the name checks care about."""
    calls = msg.get("tool_calls") or []
    if not calls:
        text = msg.get("content") or ""
        asks = [w for w, hit in (("asks name", NAME_ASK.search(text)), ("asks phone", asks_phone(text))) if hit]
        return "says" + (" (%s)" % ", ".join(asks) if asks else "")
    out = []
    for c in calls:
        f = c["function"]
        try:
            a = json.loads(f.get("arguments") or "{}")
        except ValueError:
            a = {}
        if f["name"] == "open_request":
            fields = [k for k, on in (("name", str(a.get("reporter_name") or "").strip()),
                                      ("name_declined", str(a.get("name_declined")).lower() == "true"),
                                      ("phone", str(a.get("reporter_phone") or "").strip())) if on]
            out.append("open_request(%s)" % ",".join(fields))
        elif f["name"] == "notify_team":
            out.append("notify_team(%s)" % a.get("reason"))
        else:
            out.append(f["name"])
    return " + ".join(sorted(out))


def ask(key, body):
    """One streamed call: (seconds to the first word or tool call, seconds to the end,
    the assembled message, usage, finish reason)."""
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions", method="POST",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "User-Agent": "homies/1.0"})
    t0 = time.perf_counter()
    first, text, calls, usage, finish = None, [], {}, {}, None
    with urllib.request.urlopen(req, timeout=180) as r:
        for raw in r:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue                     # ": OPENROUTER PROCESSING" keep-alives
            data = line[5:].strip()
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            if chunk.get("error"):
                raise RuntimeError(json.dumps(chunk["error"])[:300])
            usage = chunk.get("usage") or usage
            for ch in chunk.get("choices") or []:
                d = ch.get("delta") or {}
                if first is None and (d.get("content") or d.get("tool_calls")):
                    first = time.perf_counter() - t0
                if d.get("content"):
                    text.append(d["content"])
                for tc in d.get("tool_calls") or []:
                    slot = calls.setdefault(tc.get("index", 0), {"id": "", "name": "", "arguments": ""})
                    slot["id"] = tc.get("id") or slot["id"]
                    f = tc.get("function") or {}
                    slot["name"] += f.get("name") or ""
                    slot["arguments"] += f.get("arguments") or ""
                finish = ch.get("finish_reason") or finish
    end = time.perf_counter() - t0
    msg = {"role": "assistant", "content": "".join(text)}
    if calls:
        msg["tool_calls"] = [{"id": c["id"], "type": "function",
                              "function": {"name": c["name"], "arguments": c["arguments"]}}
                             for _, c in sorted(calls.items())]
    return (end if first is None else first), end, msg, usage, finish


def list_turns(run):
    for fn in sorted(os.listdir(os.path.join(run, "chats"))):
        if not fn.endswith(".json"):
            continue
        sid = fn[:-5]
        for n, (seen, m) in enumerate(model_turns(load(os.path.join(run, "chats", fn))), 1):
            heard = next((x["content"] for x in reversed(seen) if x["role"] == "user"), "")
            print("%s:%d  after %r -> %s | %s" % (sid, n, heard[:40], action(m), (m.get("content") or "")[:70]))


def replay(run, points, levels, cap):
    import prompt_probe as P
    key = P.E.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        sys.exit("OPENROUTER_API_KEY missing from .env")
    path = os.path.join(run, "effort.json")
    rows = load(path) if os.path.exists(path) else []
    spent = sum(r["cost"] for r in rows)
    live = load(os.path.join(run, "live_inbound.json"))
    for i, point in enumerate(points):
        sid, n = point.split(":")
        chat = load(os.path.join(run, "chats", sid + ".json"))
        md = open(os.path.join(run, "context_%s.md" % sid), encoding="utf-8").read()
        tools = json.loads(re.search(r"## The tools\s*\n+```json\n(.*?)\n```", md, re.S).group(1))
        seen, original = model_turns(chat)[int(n) - 1]
        k = i % len(levels)
        for level in levels[k:] + levels[:k]:
            if any(r["point"] == point and r["level"] == level for r in rows):
                continue                     # a re-run continues where a stop left off
            if spent > cap:
                sys.exit("stopped: spent $%.4f, over the $%.2f cap" % (spent, cap))
            # As `voice_qa.py say` sends it: no token cap and no temperature on a thinking model.
            body = {"model": live["model"], "messages": seen, "tools": tools,
                    "stream": True, "usage": {"include": True}}
            if level != "default":
                body["reasoning"] = {"effort": level}
            first, end, msg, u, finish = ask(key, body)
            cost = float(u.get("cost") or 0)
            spent += cost
            rows.append({"point": point, "level": level, "first_s": round(first, 3), "end_s": round(end, 3),
                         "action": action(msg), "original": action(original),
                         "reasoning": (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0),
                         "out": u.get("completion_tokens", 0), "in": u.get("prompt_tokens", 0),
                         "cached": (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
                         "cost": cost, "finish": finish, "reply": msg,
                         "original_reply": {k2: original.get(k2) for k2 in ("content", "tool_calls")}})
            write(path, rows)                # after every call: a stop keeps what was paid for
            r = rows[-1]
            print("%-22s %-7s first %5.2fs end %5.2fs think %4d  %s%s  $%.4f" % (
                point, level, first, end, r["reasoning"], r["action"],
                "" if r["action"] == r["original"] else "  (original: %s)" % r["original"], cost))
    summary(rows, levels)


def summary(rows, levels):
    med = lambda xs: "%.2fs" % statistics.median(xs) if xs else "-"
    print("\n%-8s %5s %13s %13s %13s %9s %10s %8s" % ("level", "calls", "speech 1st", "tool done",
                                                     "all 1st", "thinking", "same act", "cost"))
    for lv in levels:
        rs = [r for r in rows if r["level"] == lv]
        if not rs:
            continue
        speech = [r["first_s"] for r in rs if not r["reply"].get("tool_calls")]
        tool = [r["end_s"] for r in rs if r["reply"].get("tool_calls")]
        print("%-8s %5d %13s %13s %13s %9.0f %7d/%-2d $%.4f" % (
            lv, len(rs), med(speech), med(tool), med([r["first_s"] for r in rs]),
            statistics.mean(r["reasoning"] for r in rs), sum(r["action"] == r["original"] for r in rs),
            len(rs), sum(r["cost"] for r in rs)))
    print("(medians; speech = time to the first word, tool = time until the tool call is complete)")
    print("spent $%.4f in all" % sum(r["cost"] for r in rows))


def main():
    a = sys.argv[1:]
    if len(a) < 3 or a[0] not in ("list", "replay", "report") or a[1] != "--run":
        sys.exit(__doc__)
    run = a[2]
    flag = lambda f, d=None: a[a.index(f) + 1] if f in a else d
    if a[0] == "list":
        return list_turns(run)
    levels = tuple((flag("--efforts") or ",".join(LEVELS)).split(","))
    if a[0] == "report":
        return summary(load(os.path.join(run, "effort.json")), levels)
    points = [p for p in (flag("--points") or "").split(",") if p]
    if not points:
        sys.exit("--points sid:n,... (numbers from `list`)")
    return replay(run, points, levels, float(flag("--cap", CAP)))


if __name__ == "__main__":
    main()
