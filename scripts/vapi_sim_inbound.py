# -*- coding: utf-8 -*-
"""Voice calls to the live incoming agent from Vapi's simulated callers: the name flow and the wait.

    python scripts/vapi_sim_inbound.py                 # print the run it would start (free)
    python scripts/vapi_sim_inbound.py --run DIR       # SPENDS Vapi minutes: start it, wait, save DIR/
    python scripts/vapi_sim_inbound.py --report DIR    # the waits and the checks again, from DIR (free)

WHY, 22 Oct. The owner, after `reasoningEffort` low went live on the incoming agent:
*"can you test it via voice agent? but run it in background use [V]api to talk with
it like before and create an artifact for it"*. OpenRouter's replay compared the
thinking levels (`voice_effort.py`), but its times are not what a caller waits.
These are real Vapi calls: a simulated caller speaks Hebrew to the live agent
over Vapi's voice transport, so every turn carries Vapi's own figures (model,
voice, transcriber, endpointing) and the transcript gives the gap a caller hears.

Vapi's simulations API (`/eval/simulation/*`), not the old test suites
(`vapi_eval.py`), which the API spec no longer lists. One run, three inline
simulations: a scenario (the caller's situation) and a personality (the
caller's voice, model and manner). What each scenario sets:
- The caller is Assaf Clix, בר כוכבא 23, flat 2: live tests are made only there,
  as him, and their tickets are kept.
- `targetOverrides.variableValues.caller_phone` is Homies' office line, so the
  agent hears a caller whose number came through, as an outside call does, and
  a callback could only ever reach Homies.
- `notify_team` is mocked, so a test never pages the team. Every other tool
  runs for real against the deployed function.

WHAT IT DOES NOT MEASURE: the phone leg. Omni's line from Israel to Vapi's SIP
address adds its own time, and a person on a mobile is noisier than a voice
read by Azure. Compare the agent's own stages; only calls through 208 give
the caller's whole wait.
"""
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import prompt_probe as P                       # noqa: E402
from check_name_flow import NAME_ASK           # noqa: E402
from vapi_latency import gaps                  # noqa: E402

OFFICE_LINE = os.environ.get("HOMIES_CALLBACK_NUMBER", "077-6687949")
MAX_SECONDS = 150          # the caller hangs up by then: the cost ceiling of one call
# The two calls through 208 on 21 Oct that had conversations, on `medium`.
BASELINE = ("01a15ebe", "01a15ebd")

PERSONALITY = {
    "name": "Assaf, a tenant (he)",
    "assistant": {
        "name": "Simulated tenant (he)",
        "firstMessageMode": "assistant-waits-for-user",
        "maxDurationSeconds": MAX_SECONDS,
        "endCallFunctionEnabled": True,
        "model": {"provider": "openai", "model": "gpt-4.1", "temperature": 0.7, "messages": [{
            "role": "system",
            "content": (
                "You are a tenant in Israel phoning Homies, the company that manages your building. "
                "A man named Michael answers. You are NOT an assistant and you never say you are an AI.\n"
                "Speak only Hebrew, everyday spoken Hebrew, in short sentences, like a real person on "
                "the phone. Answer only what you are asked unless your situation says otherwise. React to "
                "what Michael actually says; do not help him and do not trap him. Never repeat back what "
                "he told you. When you have what you called for, say a short goodbye and end the call.")}]},
        # Male, so the two sides are told apart in a recording; Azure, so the
        # client's Cartesia account is not spent on the caller.
        "voice": {"provider": "azure", "voiceId": "he-IL-AvriNeural"},
        "transcriber": {"provider": "azure", "language": "he-IL"},
    },
}

WHO = "Your name is אסף קליקס (Assaf Clix). You live at בר כוכבא 23 in Tel Aviv, apartment 2."


def judged(name, question, expect):
    """One yes/no read of the call by Vapi's judge; our own checks come from the tool calls."""
    return {"structuredOutput": {"name": name, "type": "ai", "description": question,
                                 "schema": {"type": "boolean", "description": question}},
            "comparator": "=", "value": expect, "required": True}


SCENARIOS = [
    {
        "name": "light, name asked",
        "instructions": WHO + (
            " The light on the third-floor landing of the stairwell has been out for two days; it is "
            "dark there in the evening. Open with the problem, without a greeting and without your name. "
            "Give your name, the building and the apartment only when asked, each when it is asked. When "
            "Michael tells you a ticket is open, thank him and say goodbye."),
        "evaluations": [
            judged("asked_name_before_ticket",
                   "Did the assistant ask for the caller's name before it said that a ticket was opened?", True),
            judged("asked_phone", "Did the assistant ask the caller for a phone number?", False),
        ],
    },
    {
        "name": "leak, all given at once",
        "instructions": WHO + (
            " Open with one sentence that gives your name, the building and the apartment, and then the "
            "problem: water has been dripping from the ceiling of the ground-floor lobby, next to the "
            "mailboxes, since this morning. If Michael asks for something you already said, say a little "
            "impatiently that you already said it. When he tells you a ticket is open, thank him and say "
            "goodbye."),
        "evaluations": [
            judged("asked_again", "After the caller gave their name, building and apartment, did the "
                   "assistant ask for any of them again?", False),
            judged("gave_ticket_number", "Did the assistant tell the caller a ticket number?", True),
        ],
    },
    {
        "name": "status of the light",
        "instructions": WHO + (
            " Earlier you reported that the stairwell light on the third floor is out, and you want to "
            "know what is happening with it. You do not remember a ticket number. Answer what you are "
            "asked. Do not report anything new. Once you have an answer, thank him and say goodbye."),
        "evaluations": [
            judged("opened_new_ticket", "Did the assistant say it opened a new ticket?", False),
        ],
    },
]


def api(method, path, body=None):
    req = urllib.request.Request(
        "https://api.vapi.ai" + path, method=method,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None,
        headers={"Authorization": "Bearer " + P.E["VAPI_PRIVATE_KEY"].strip(),
                 "Content-Type": "application/json",
                 "User-Agent": "homies/1.0"})          # Cloudflare 403s urllib's own
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s on %s %s\n%s" % (e.code, method, path, e.read().decode("utf-8")[:1500]))


def run_body():
    target = P.assistant_id(P.TARGETS["inbound"])
    sims = []
    for s in SCENARIOS:
        sims.append({"type": "simulation", "name": s["name"], "personality": PERSONALITY, "scenario": {
            "name": s["name"], "instructions": s["instructions"], "evaluations": s["evaluations"],
            "targetOverrides": {"variableValues": {"caller_phone": OFFICE_LINE}},
            "toolMocks": [{"toolName": "notify_team",
                           "result": json.dumps({"ok": True, "team_notified": True})}],
            # Informational: the PRD's ceiling, reported per call by Vapi itself.
            "latencyExpectations": [{"metric": m, "aggregation": "median", "thresholdMs": 800,
                                     "required": False} for m in ("turn", "model")],
        }})
    return {"target": {"type": "assistant", "assistantId": target},
            "transport": {"provider": "vapi.websocket"}, "iterations": 1, "simulations": sims}


def find_call(prefix):
    return next((c for c in api("GET", "/call?limit=100") if c["id"].startswith(prefix)), None)


def timings_only(call):
    """A real caller's call, kept for its timings alone: what was said and the
    tools' arguments (a real address, a flat) stay out of the run folder."""
    keep = ("role", "time", "endTime", "duration", "secondsFromStart")
    return {"id": call["id"], "type": call.get("type"), "startedAt": call.get("startedAt"),
            "cost": call.get("cost"),
            "artifact": {"performanceMetrics": (call.get("artifact") or {}).get("performanceMetrics")},
            "messages": [{k: m[k] for k in keep if k in m} for m in call.get("messages") or []
                         if m.get("role") in ("user", "bot")]}


def run(out):
    os.makedirs(out, exist_ok=True)
    r = api("POST", "/eval/simulation/run", run_body())
    print("run %s queued" % r["id"], flush=True)
    for _ in range(240):                       # 20 minutes
        time.sleep(5)
        r = api("GET", "/eval/simulation/run/%s" % r["id"])
        if r.get("status") == "ended":
            break
    with open(os.path.join(out, "run.json"), "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
    items = api("GET", "/eval/simulation/run/%s/item" % r["id"])
    items = items.get("results", items) if isinstance(items, dict) else items
    with open(os.path.join(out, "items.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    calls = {}
    for it in items:
        if it.get("callId"):
            calls[it["callId"]] = api("GET", "/call/%s" % it["callId"])
    for prefix in BASELINE:
        c = find_call(prefix)
        if c:
            calls[c["id"]] = timings_only(api("GET", "/call/%s" % c["id"]))
    with open(os.path.join(out, "calls.json"), "w", encoding="utf-8") as f:
        json.dump(calls, f, ensure_ascii=False, indent=1)
    print("run %s %s (%s)" % (r["id"], r.get("status"), r.get("endedReason") or ""))
    report(out)


def stages(call):
    """Vapi's own per-turn figures for the agent: model, voice, transcriber, endpointing, turn (ms)."""
    pm = (call.get("artifact") or {}).get("performanceMetrics") or {}
    rows = pm.get("turnLatencies") or []
    pick = lambda k: [t[k] for t in rows if isinstance(t.get(k), (int, float))]
    return {k: pick(k + "Latency") for k in ("model", "voice", "transcriber", "endpointing", "turn")}


def tools_used(call):
    """(name, arguments, result) per tool call, in order, from the call's messages."""
    msgs = call.get("messages") or (call.get("artifact") or {}).get("messages") or []
    results = {m.get("toolCallId"): m.get("result") for m in msgs if m.get("role") == "tool_call_result"}
    out = []
    for m in msgs:
        for tc in m.get("toolCalls") or []:
            f = tc.get("function") or {}
            try:
                a = json.loads(f.get("arguments") or "{}") if isinstance(f.get("arguments"), str) else (f.get("arguments") or {})
            except ValueError:
                a = {}
            out.append((f.get("name"), a, results.get(tc.get("id"))))
    return out


def name_asked_first(call):
    """True when a name question came before the first open_request (None: no ticket)."""
    msgs = call.get("messages") or []
    for m in msgs:
        if m.get("role") == "bot" and NAME_ASK.search(m.get("message") or ""):
            return True
        if any((tc.get("function") or {}).get("name") == "open_request" for tc in m.get("toolCalls") or []):
            return False
    return None


def summary(call):
    w = [g[1] for g in gaps(call)]
    st = stages(call)
    med = lambda xs: round(statistics.median(xs)) if xs else None
    return {"id": call["id"], "type": call.get("type"), "started": call.get("startedAt"),
            "cost": call.get("cost"), "turns": len(w),
            "wait_median_ms": round(statistics.median(w) * 1000) if w else None,
            "wait_max_ms": round(max(w) * 1000) if w else None,
            "stage_median_ms": {k: med(v) for k, v in st.items()},
            "reasoning_effort": ((call.get("assistant") or {}).get("model") or {}).get("reasoningEffort"),
            "tools": [{"name": n, "args": a} for n, a, _ in tools_used(call)],
            "name_asked_first": name_asked_first(call)}


def report(out):
    calls = json.load(open(os.path.join(out, "calls.json"), encoding="utf-8"))
    items = json.load(open(os.path.join(out, "items.json"), encoding="utf-8"))
    by_call = {it.get("callId"): it for it in items}
    rows = []
    for cid, call in calls.items():
        s = summary(call)
        it = by_call.get(cid)
        s["scenario"] = ((it or {}).get("metadata") or {}).get("scenario", {}).get("name") if it else "21 Oct, through 208"
        s["status"] = (it or {}).get("status")
        s["evaluations"] = ((it or {}).get("results") or {}).get("evaluations") if it else None
        rows.append(s)
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print("\n%-26s %-7s %5s %9s %9s  %s" % ("call", "status", "turns", "wait med", "wait max",
                                           "agent stages, median ms (model / voice / transcriber / endpointing)"))
    for s in rows:
        m = s["stage_median_ms"]
        print("%-26s %-7s %5s %8sms %8sms  %s / %s / %s / %s" % (
            (s["scenario"] or s["id"][:8])[:26], s["status"] or "-", s["turns"], s["wait_median_ms"],
            s["wait_max_ms"], m["model"], m["voice"], m["transcriber"], m["endpointing"]))
        for t in s["tools"]:
            keep = {k: t["args"].get(k) for k in ("reporter_name", "name_declined", "reporter_phone", "building",
                                                  "unit", "type", "reason") if k in t["args"]}
            print("    tool %s %s" % (t["name"], json.dumps(keep, ensure_ascii=False)))
    print("\nsaved %s" % os.path.join(out, "summary.json"))


def main():
    a = sys.argv[1:]
    if "--run" in a:
        return run(a[a.index("--run") + 1])
    if "--report" in a:
        return report(a[a.index("--report") + 1])
    print(json.dumps(run_body(), ensure_ascii=False, indent=1)[:4000])
    print("\n%d calls, each ended by the caller by %ds. --run DIR starts them (Vapi minutes)."
          % (len(SCENARIOS), MAX_SECONDS))


if __name__ == "__main__":
    main()
