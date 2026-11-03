# -*- coding: utf-8 -*-
"""One simulated call to the live incoming agent about a manager, the tenant voiced by Cartesia.

    python scripts/vapi_sim_manager.py              # print the run it would start (free)
    python scripts/vapi_sim_manager.py --run DIR    # SPENDS: one call, about $0.40-0.60 of Vapi
                                                    # minutes, plus the tenant's Cartesia characters
    python scripts/vapi_sim_manager.py --recordings DIR   # the saved call's recordings again (free)

WHY, 3 Nov. The incoming agent took the chatbot's way with a manager request at 14:23 UTC
(docs/assistant/demo-inbound.md, "3 Nov"). The owner: "can i hear it like do a simulated test in
the bg with cartesia as the tenant". vapi_sim_inbound.py's caller speaks with Azure, so the
client's Cartesia account is not spent on the caller. Here the owner asked for Cartesia: the tenant
is Cartesia's stock Hebrew voice "Asaf" (HEBREW_MEN in vapi_sync.py), on the Vapi account's Cartesia
credential, which is the client's key. Michael keeps his own clone, so the two voices differ.

THE CALL: a cold "I want a manager", one refusal to explain to a bot, then the problem (the lobby
ceiling dripping), then "when will the manager call me?", then goodbye. notify_team is mocked with
"Success.", which is what the live tool answers (it is async), so the team is never paged.
open_request runs for real, as Assaf Clix at בר כוכבא 23 flat 2, and its ticket is kept: test
tickets are never deleted. caller_phone is Homies' office line, as in vapi_sim_inbound.py.

DIR gets run.json, items.json, call.json, transcript.txt and the recording, which Vapi makes because
the agent records (artifactPlan.recordingEnabled, on since 26 Oct).
"""
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import vapi_sim_inbound as V                  # noqa: E402
from vapi_sync import HEBREW_MEN              # noqa: E402

MAX_SECONDS = 210         # the tenant hangs up by then: the cost ceiling of the call

PERSONALITY = json.loads(json.dumps(V.PERSONALITY))
PERSONALITY["name"] = "Assaf, a tenant who wants a manager (he, Cartesia)"
PERSONALITY["assistant"]["maxDurationSeconds"] = MAX_SECONDS
PERSONALITY["assistant"]["voice"] = {"provider": "cartesia", "voiceId": HEBREW_MEN["asaf"][0],
                                     "model": "sonic-3.5", "language": "he"}

SCENARIO = {
    "name": "manager, the chatbot's way",
    "instructions": V.WHO + (
        " You are annoyed and you want a manager, not a bot. Open with exactly 'אני רוצה לדבר עם מנהל.' and "
        "nothing else. To Michael's first answer, refuse once to explain, with exactly 'לא רוצה להסביר לבוט, "
        "תביא לי בן אדם.' If he then asks again, give in and tell him the problem in one sentence: water has "
        "been dripping from the ceiling of the ground-floor lobby, next to the mailboxes, since this morning. "
        "Give your name, the building and the apartment only when asked, each when it is asked. Once he tells "
        "you a request was opened, ask 'ומתי המנהל יחזור אליי?'. After his answer to that, thank him, say "
        "goodbye and end the call."),
    "evaluations": [
        V.judged("someone_else",
                 "Did the assistant say that a team, a manager or management was told, notified or updated, or "
                 "that someone will call the caller back or get back to them?", False),
        V.judged("argued",
                 "Did the assistant refuse the request for a manager, argue with the caller about it, or say "
                 "it cannot help?", False),
        V.judged("ticket_number", "Did the assistant tell the caller the number of a request it opened?", True),
    ],
}


def body():
    target = V.P.assistant_id(V.P.TARGETS["inbound"])
    sim = {"type": "simulation", "name": SCENARIO["name"], "personality": PERSONALITY, "scenario": {
        "name": SCENARIO["name"], "instructions": SCENARIO["instructions"],
        "evaluations": SCENARIO["evaluations"],
        "targetOverrides": {"variableValues": {"caller_phone": V.OFFICE_LINE}},
        "toolMocks": [{"toolName": "notify_team", "result": "Success."}]}}
    return {"target": {"type": "assistant", "assistantId": target},
            "transport": {"provider": "vapi.websocket"}, "iterations": 1, "simulations": [sim]}


def transcript(call):
    """Who said what, and the agent's tool calls, in order."""
    lines = []
    for m in (call.get("artifact") or {}).get("messages") or call.get("messages") or []:
        role = m.get("role")
        if role == "bot":
            lines.append("מיכאל: " + (m.get("message") or ""))
        elif role == "user":
            lines.append("הדייר: " + (m.get("message") or ""))
        elif role == "tool_calls":
            for t in m.get("toolCalls") or []:
                lines.append("  [%s] %s" % (t["function"]["name"], t["function"]["arguments"].replace("\n", " ")))
        elif role == "tool_call_result":
            lines.append("  [-> %s] %s" % (m.get("name"), str(m.get("result"))[:200]))
    return "\n".join(lines)


def save_recordings(call, out):
    """The call's recordings, downloaded beside the transcript.

    The plain recordingUrl is a private bucket path on this account (a 400 without auth, seen on the
    first run); the artifact also carries short-lived presigned copies, which download as they are.
    """
    art = call.get("artifact") or {}
    urls = {
        "recording": art.get("presignedMonoUrl"),
        "recording-stereo": art.get("presignedStereoUrl"),
        "michael-only": art.get("presignedAssistantUrl"),
    }
    saved = []
    for name, url in urls.items():
        if not url:
            continue
        ext = os.path.splitext(url.split("?")[0])[1] or ".wav"
        path = os.path.join(out, name + ext)
        req = urllib.request.Request(url, headers={"User-Agent": "homies/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
            f.write(r.read())
        saved.append(path)
    return saved


def run(out):
    os.makedirs(out, exist_ok=True)
    r = V.api("POST", "/eval/simulation/run", body())
    print("run %s queued" % r["id"], flush=True)
    for _ in range(120):                       # 10 minutes
        time.sleep(5)
        r = V.api("GET", "/eval/simulation/run/%s" % r["id"])
        if r.get("status") == "ended":
            break
    with open(os.path.join(out, "run.json"), "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
    items = V.api("GET", "/eval/simulation/run/%s/item" % r["id"])
    items = items.get("results", items) if isinstance(items, dict) else items
    with open(os.path.join(out, "items.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    print("run %s %s (%s)" % (r["id"], r.get("status"), r.get("endedReason") or ""))
    for it in items:
        if not it.get("callId"):
            print("no call on item %s: %s" % (it.get("id"), it.get("status")))
            continue
        call = None
        for _ in range(24):                    # the recording lands a little after the call ends
            call = V.api("GET", "/call/%s" % it["callId"])
            art = call.get("artifact") or {}
            if art.get("recordingUrl") or call.get("recordingUrl") or art.get("recording"):
                break
            time.sleep(5)
        with open(os.path.join(out, "call.json"), "w", encoding="utf-8") as f:
            json.dump(call, f, ensure_ascii=False, indent=1)
        text = transcript(call)
        with open(os.path.join(out, "transcript.txt"), "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print("call %s, %s, cost $%s" % (call["id"], call.get("endedReason"), call.get("cost")))
        print("item status: %s" % it.get("status"))
        for ev in (it.get("evaluations") or it.get("results") or []):
            print("  judge: %s" % json.dumps(ev, ensure_ascii=False)[:300])
        print(text)
        for p in save_recordings(call, out):
            print("saved %s" % p)


def recordings_again(out):
    """Fresh presigned links for the call saved in DIR, and the recordings downloaded again (free)."""
    saved = json.load(open(os.path.join(out, "call.json"), encoding="utf-8"))
    call = V.api("GET", "/call/%s" % saved["id"])
    for p in save_recordings(call, out):
        print("saved %s" % p)


def main():
    a = sys.argv[1:]
    if "--run" in a:
        run(a[a.index("--run") + 1])
        return
    if "--recordings" in a:
        recordings_again(a[a.index("--recordings") + 1])
        return
    b = body()
    s = b["simulations"][0]
    print("would start: 1 call to %s over %s, the tenant on %s %s, up to %ds"
          % (b["target"]["assistantId"], b["transport"]["provider"], s["personality"]["assistant"]["voice"]["provider"],
             s["personality"]["assistant"]["voice"]["voiceId"], MAX_SECONDS))
    print("scenario: %s\n%s" % (s["scenario"]["name"], s["scenario"]["instructions"]))
    print("mocks: %s" % s["scenario"]["toolMocks"])
    print("\nFree so far. --run DIR spends.")


if __name__ == "__main__":
    main()
