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

It writes real rows. Everything it writes carries call_id "probe-<run>-<n>",
and since 16 Sep the run deletes them at the end (`--keep` to inspect them):
the client's review found the dashboard's counts inflated by test calls, and
a harness that leaves 44 probe interactions behind is how that happens.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Call ids have to be unique per run. The first version reused "probe-7" every
# time, so the second run had its open_payment_ticket refused by the duplicate
# guard from the first — a correct refusal reported as a failure. A test that
# passes only on a clean sheet is a test that will lie to you later.
RUN = time.strftime("%m%d-%H%M%S")
STARTED = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - 60))

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
    # A managed address, in Hebrew, since 16 Sep: the webhook verifies the
    # building on every undialled call now (this context has no resident_id,
    # so it is one), and "Herzl 14" resolves to nothing -- הרצל has 112 only.
    "building": "הרצל 112",
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
    # These two carried no building until 16 Sep, and passed: an inbound voice
    # ticket with no address at all opened anyway, with `building` empty. That
    # is the silent failure the new gate exists to stop, so they name a managed
    # address now and still test what they were written to test -- a ticket
    # opens and hands back a real reference.
    ("open_request", {"description": "leak in the lobby", "type": "plumbing",
                      "building": "הרצל 112"}, "reference"),
    # A complaint is a ticket, on voice as well as chat (25 Aug, migration 025).
    # Here because the type is constrained in Postgres: if the constraint and
    # the tool enums ever fall out of step, this fails rather than the resident
    # being told a complaint was filed that the database refused.
    ("open_request", {"description": "the guard is rude to residents",
                      "type": "complaint", "building": "הרצל 112"}, "reference"),
    # And the case those two used to be, now asserted as a refusal: no address
    # anywhere on an undialled call opens nothing and asks for the building.
    ("open_request", {"description": "נזילה בלובי", "type": "plumbing"}, "~need_building"),
    # 15 Sep, migration 031: a resident who wants to pay is a ticket too. Same
    # reason the complaint case exists -- the type is constrained in Postgres.
    ("open_request", {"description": "רוצה לשלם את ועד הבית",
                      "type": "payment", "building": "הרצל 112", "reporter_unit": "12"}, "reference"),
    # 16 Sep, the client's review: voice refuses a building Homies does not
    # manage, as chat has since 23 Aug. "~reason" = ok, opened false, that
    # reason. A street we do not have, and a number the street does not have.
    ("open_request", {"description": "נזילה בלובי", "type": "plumbing",
                      "building": "רחוב שלא קיים 5"}, "~street_unknown"),
    ("open_request", {"description": "נזילה בלובי", "type": "plumbing",
                      "building": "הרצל 14"}, "~number_not_on_street"),
    ("transfer_to_human", {"reason": "hardship", "posture_reached": "hot"}, None),
    ("open_payment_ticket", {"authorization_captured": True}, None),
    # A second ticket for the same call. On n8n this is no longer refused — the
    # sheet upserts on call_id, so the model gets ok twice and a person still
    # sees one row. The contract changed with the host; the test says so rather
    # than pretending the old guarantee survived.
    ("open_payment_ticket", {"authorization_captured": True}, "duplicate-upsert"),
    # 16 Sep, the services lookup. Two shapes: a question that is in the
    # catalogue, and one that deliberately is not -- `found: false` is a real
    # answer and the agents are told what to do with it, so it has to keep
    # working. "~~" = ok and found true; "!!" = ok and found false.
    ("get_service_info", {"topic": "כל כמה זמן מגיע אב הבית"}, "~~super"),
    ("get_service_info", {"topic": "מתי מחטאים את מאגר המים"}, "~~pumps"),
    ("get_service_info", {"topic": "כמה עולה חניה לאורחים"}, "!!not in the catalogue"),
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


# The tables a probe row can land in, children first. `messages` cascades on
# the interaction; the rest are `on delete set null`, so they are deleted by
# hand or they would survive as orphans.
CHILD_TABLES = ["call_outcomes", "payment_links", "payment_tickets",
                "promises_to_pay", "payment_disputes", "requests"]


def cleanup(run):
    """Delete every row this run wrote, by its call ids, straight from the DB."""
    e = env_all()
    base = e.get("SUPABASE_URL", "").strip().rstrip("/") + "/rest/v1/"
    key = e.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not base.startswith("http") or not key:
        print("\n(no SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY in .env: rows left in place)")
        return
    hdr = {"apikey": key, "Authorization": "Bearer " + key, "Prefer": "return=representation"}

    def call(method, path):
        req = urllib.request.Request(base + path, method=method, headers=hdr)
        try:
            return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8") or "[]")
        except urllib.error.HTTPError as ex:
            print("   cleanup %s %s -> HTTP %s %s" % (method, path.split("?")[0], ex.code, ex.read()[:120]))
            return []

    like = urllib.parse.quote("probe-%s-%%" % run, safe="")
    rows = call("GET", "interactions?select=id&external_call_id=like." + like)
    ids = [r["id"] for r in rows]
    gone = {}
    if ids:
        inlist = "in.(" + ",".join(ids) + ")"
        for t in CHILD_TABLES:
            gone[t] = len(call("DELETE", "%s?interaction_id=%s" % (t, inlist)))
        gone["interactions"] = len(call("DELETE", "interactions?id=" + inlist))
    # A request the webhook filed without an interaction still carries the
    # probe phone; the webhook's own duplicate guard is why there may be none.
    gone["requests(phone)"] = len(call(
        "DELETE", "requests?reported_by_phone=eq.%s&created_at=gte.%s"
        % (urllib.parse.quote(CONTEXT["phone"], safe=""), STARTED)))
    print("\ncleanup: " + ", ".join("%s %d" % kv for kv in gone.items()))


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
        want_found = bool(expect) and expect.startswith("~~")
        want_absent = bool(expect) and expect.startswith("!!")
        want_unmanaged = bool(expect) and expect.startswith("~") and not want_found
        ok = r.get("ok")

        if want_found:
            titles = [t.get("title", "") for t in (r.get("topics") or [])]
            good = r.get("ok") is True and r.get("found") is True and bool(titles)
            note = "topics=%s" % "/".join(titles)
        elif want_absent:
            good = r.get("ok") is True and r.get("found") is False
            note = expect[2:]
        elif want_unmanaged:
            good = (ok is True and r.get("opened") is False
                    and r.get("reason") == expect[1:])
            note = "reason=%s" % r.get("reason")
        elif want_refusal:
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
    if "--keep" not in sys.argv:
        cleanup(RUN)

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
        print("\nThe probe-* rows of this run were deleted (run with --keep to inspect them).")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
