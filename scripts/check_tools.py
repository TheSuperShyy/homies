"""Exercise all eight debt tools against whichever host is configured.

    python scripts/check_tools.py

Resolves the host exactly the way vapi_sync.py does — Supabase if it is set,
Apps Script otherwise — so this tests the endpoint the agent will really call,
not a different one.

WHY THIS EXISTS
A tool that answers with the wrong shape is worse than one that is missing. The
agent reads the result, believes it, and tells the resident their ticket is open.
The first time the Apps Script endpoint was probed it returned
{"found": false, "reason": "no phone supplied"} for log_call_outcome — because
the deployed version routed every tool call to the resident lookup regardless of
name. Nothing about that is visible from the Vapi side.

It writes real rows. Everything it writes carries call_id "probe-<n>", so it is
easy to find and delete afterwards.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

# Call ids have to be unique per run. The first version reused "probe-7" every
# time, so the second run had its open_payment_ticket refused by the duplicate
# guard from the first — a correct refusal reported as a failure. A test that
# passes only on a clean sheet is a test that will lie to you later.
RUN = time.strftime("%m%d-%H%M%S")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vapi_sync import load_env, tool_server  # noqa: E402


def env_all():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return dict(
        l.strip().split('=', 1)
        for l in open(os.path.join(root, '.env'), encoding='utf-8')
        if l.strip() and not l.startswith('#') and '=' in l
    )

# A resident from the seed, with everything a call needs. Mirrors what the queue
# would attach; the tools must take their facts from here and not from arguments.
CONTEXT = {
    "phone": "+972501234567",
    "first_name": "Shahar",
    "building": "Herzl 14",
    "unit": "12",
    "amount": "450",
    "month": "July",
    "card_last4": "4821",
}

# (tool, arguments, what a pass looks like)
CASES = [
    ("log_call_outcome", {"outcome": "no_answer", "posture_reached": "open"}, None),
    ("log_promise_to_pay", {"said": "next Sunday", "promised_date": "2026-08-09"}, None),
    ("request_standing_order", {}, None),
    ("log_disputed_payment", {}, None),
    ("open_request", {"description": "leak in the lobby", "type": "plumbing"}, "reference"),
    ("transfer_to_human", {"reason": "hardship", "posture_reached": "hot"}, None),
    ("open_payment_ticket", {"authorization_captured": True}, None),
    # A second ticket for the same call. On n8n this is no longer refused — the
    # sheet upserts on call_id, so the model gets ok twice and a person still
    # sees one row. The contract changed with the host; the test says so rather
    # than pretending the old guarantee survived.
    ("open_payment_ticket", {"authorization_captured": True}, "duplicate-upsert"),
    # Must be refused: the enum is checked server-side, not trusted from the model.
    ("log_call_outcome", {"outcome": "totally-made-up"}, "!bad enum"),
    # Must be refused: the model cannot open a request with no description.
    ("open_request", {}, "!missing description"),
]


def post(url, headers, body):
    req = urllib.request.Request(
        url, method="POST", data=json.dumps(body).encode("utf-8"),
        headers=dict(headers, **{"Content-Type": "application/json"}),
    )
    try:
        return json.loads(urllib.request.urlopen(req, timeout=90).read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"__http": e.code, "__body": e.read().decode("utf-8")[:300]}


def main():
    load_env()
    server = tool_server()
    if not server:
        sys.exit("No tool host configured. Set SUPABASE_URL + TOOL_SECRET, "
                 "or WEB_APP_URL + APPS_SCRIPT_SECRET, in .env")

    url, secret, mode, label = server
    headers = {}
    if mode == "query":
        url = url + ("&" if "?" in url else "?") + "key=" + secret
    else:
        headers["x-homies-secret"] = secret

    print("host: %s" % label)
    print("url : %s\n" % url.split("?")[0])

    passed = failed = 0
    for i, (tool, args, expect) in enumerate(CASES, 1):
        body = {"message": {
            "call": {"id": "probe-%s-%d" % (RUN, i),
                     "assistantOverrides": {"variableValues": CONTEXT}},
            "toolCalls": [{"id": "tc%d" % i,
                           "function": {"name": tool, "arguments": args}}],
        }}
        # The duplicate-ticket case has to reuse the previous call id, or it is
        # not a duplicate and proves nothing.
        if expect == "!duplicate":
            body["message"]["call"]["id"] = "probe-%s-%d" % (RUN, i - 1)

        out = post(url, headers, body)
        if "__http" in out:
            print("  FAIL  %-24s HTTP %s %s" % (tool, out["__http"], out["__body"][:80]))
            failed += 1
            continue

        results = out.get("results") or []
        if not results or "toolCallId" not in results[0]:
            print("  FAIL  %-24s wrong envelope: %s" % (tool, json.dumps(out)[:90]))
            failed += 1
            continue

        try:
            r = json.loads(results[0]["result"])
        except Exception:
            r = {"raw": results[0]["result"]}

        if expect == "duplicate-upsert":
            expect, note_only = None, True
        want_refusal = bool(expect) and expect.startswith("!")
        ok = r.get("ok")

        if want_refusal:
            good = ok is False
            note = expect[1:]
        elif expect:
            good = ok is True and bool(r.get(expect))
            note = "%s=%s" % (expect, r.get(expect))
        else:
            good = ok is True
            note = ""

        print("  %s  %-24s %s %s" % ("pass" if good else "FAIL", tool,
                                     json.dumps(r)[:70], note))
        passed, failed = (passed + 1, failed) if good else (passed, failed + 1)

    print("\n%d passed, %d failed" % (passed, failed))

    # A passing response does not mean a row was written.
    #
    # The n8n workflow answers Vapi from its Code node and writes afterwards, so
    # everything above can pass while every write fails silently — which is
    # exactly what happened on 4 Aug: 10/10 here, and every execution erroring on
    # a dead Google OAuth credential. Checking the responses alone was a test
    # that agreed with itself.
    if label == "n8n":
        import time as _t
        _t.sleep(6)   # executions are recorded after the response goes out
        e = env_all()
        req = urllib.request.Request(
            e["N8N_BASE_URL"].strip() + "/api/v1/executions?limit=%d" % (len(CASES) + 2),
            headers={"X-N8N-API-KEY": e["N8N_API_KEY"].strip(), "User-Agent": "homies/1.0"},
        )
        try:
            runs = json.loads(urllib.request.urlopen(req, timeout=30).read()).get("data", [])
        except Exception as exc:
            print("could not read n8n executions: %s" % exc)
            runs = []
        bad = [r for r in runs if r.get("status") not in ("success", "running", "new", "waiting")]
        print("n8n executions: %d checked, %d failed" % (len(runs), len(bad)))
        for r in bad[:5]:
            print("   %s  %s  workflow=%s" % (r.get("startedAt", "")[11:19],
                                              r.get("status"), r.get("workflowId")))
        if bad:
            failed += len(bad)
            print("\nResponses were fine and the writes were not. Open the execution in\n"
                  "n8n and read the failing node — the last time this happened it was\n"
                  "a Google credential returning 'unknown client'.")
    if failed:
        print("\nIf every tool returned {\"found\": false}, the deployed Apps Script is\n"
              "still the old version — paste sheets/Code.gs in and redeploy.")
    else:
        print("\nAll eight answer correctly and the three guards refuse. Safe to attach:")
        print("  python scripts/vapi_sync.py debt --apply")
        print("\nDelete the probe-* rows from the sheet when you are done.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
