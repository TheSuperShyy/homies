"""Deploy the read side: a webhook that hands the demo page today's call queue.

    python scripts/n8n_queue.py --dry
    python scripts/n8n_queue.py --apply

WHY THIS IS NOT JUST A FETCH FROM THE BROWSER

The Apps Script endpoint already returns the queue — filtered by the same four
conditions as v_debt_call_queue, against the live sheet. The demo page could call
it directly in one line. It does not, because Apps Script cannot read request
headers, so its secret has to travel in the URL, and a URL in a browser page is a
published URL. That secret can also *write* every tab. Putting it in a page
anyone can open turns a read into full access.

So the page calls n8n, and n8n calls Apps Script. The secret stays server-side,
and the page needs no credential at all.

WHY THE READ IS AT PAGE LOAD AND NOT DURING THE CALL

The obvious design is a `lookup_resident` tool the agent calls when someone picks
up. That is the design that already failed: Apps Script cold-starts, and a
measured request today took a 404, a retry, and 3.9 seconds. In front of a
speaking agent that is the stall that burned credits on 4 Aug. Read the whole
queue once, when the page loads and nobody is on the line, and the call itself
touches no spreadsheet.

WHAT THIS DELIBERATELY DOES NOT DO

No authentication. The queue is ten fictional residents; the endpoint is
unguarded, exactly like the tool webhook next to it, and both must grow a shared
secret before a real Homies row exists. Named here rather than in a ticket
because the sheet is the thing that will quietly stop being fictional.
"""

import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from n8n_layout import check, LayoutError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WF_NAME = "Homies — call queue (read)"
WEBHOOK_PATH = "homies-queue"


def env():
    return dict(
        l.strip().split("=", 1)
        for l in open(os.path.join(ROOT, ".env"), encoding="utf-8")
        if l.strip() and not l.startswith("#") and "=" in l
    )


def api(method, path, body=None):
    e = env()
    req = urllib.request.Request(
        e["N8N_BASE_URL"].strip() + path,
        method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={
            "X-N8N-API-KEY": e["N8N_API_KEY"].strip(),
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "homies/1.0",
        },
    )
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read() or b"{}")
    except urllib.error.HTTPError as exc:
        sys.exit("HTTP %s on %s %s\n%s" % (exc.code, method, path, exc.read().decode()[:600]))


def source_url():
    # all=1 returns everyone with a `blocked` reason on the rows being skipped,
    # rather than only the callable ones. The demo is more honest that way: the
    # four skip reasons are the eligibility rule made visible, and a list that
    # silently omits them looks like a list of every resident.
    e = env()
    return e["WEB_APP_URL"].strip() + "?key=" + e["APPS_SCRIPT_SECRET"].strip() + "&all=1"


def workflow():
    node = lambda **kw: dict({"parameters": {}, "typeVersion": 1}, **kw)
    return {
        "name": WF_NAME,
        "settings": {"executionOrder": "v1"},
        "nodes": [
            node(
                id="hook", name="Demo page asks", type="n8n-nodes-base.webhook",
                typeVersion=2, position=[0, 0],
                # Registered against this id, not the path. Omitting it is how the
                # tool workflow came up active:true with every POST 404ing.
                webhookId="homies-queue-v1",
                parameters={
                    "httpMethod": "GET",
                    "path": WEBHOOK_PATH,
                    "responseMode": "responseNode",
                    "options": {},
                },
            ),
            node(
                id="fetch", name="Read the sheet", type="n8n-nodes-base.httpRequest",
                typeVersion=4.2, position=[240, 0],
                parameters={
                    "url": source_url(),
                    "options": {"response": {"response": {"responseFormat": "json"}}},
                },
                # Apps Script 404s intermittently — twice today, once inside a live
                # call. Retrying here costs a page-load half-second and nothing
                # else, and it is the only place in the chain that can retry
                # without a person waiting on the other end.
                retryOnFail=True, maxTries=3, waitBetweenTries=1500,
            ),
            node(
                id="reply", name="Hand back the queue",
                type="n8n-nodes-base.respondToWebhook",
                typeVersion=1.1, position=[480, 0],
                parameters={
                    "respondWith": "json",
                    "responseBody": "={{ JSON.stringify($json) }}",
                    "options": {"responseHeaders": {"entries": [
                        # The page is opened from disk during testing, which makes
                        # its Origin the literal string "null" — a named origin
                        # would not match it. Nothing here is secret; the access
                        # control that matters is on the Apps Script side.
                        {"name": "Access-Control-Allow-Origin", "value": "*"},
                    ]}},
                },
            ),
        ],
        "connections": {
            "Demo page asks": {"main": [[{"node": "Read the sheet", "type": "main", "index": 0}]]},
            "Read the sheet": {"main": [[{"node": "Hand back the queue", "type": "main", "index": 0}]]},
        },
    }


def find():
    for w in api("GET", "/api/v1/workflows?limit=250").get("data", []):
        if w.get("name") == WF_NAME:
            return w
    return None


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    apply = "--apply" in sys.argv
    wf = workflow()
    existing = find()

    try:
        check(wf["nodes"], WF_NAME)
    except LayoutError as ex:
        sys.exit("\n%s\n" % ex)

    print("workflow : %s" % WF_NAME)
    print("webhook  : GET %s/webhook/%s" % (env()["N8N_BASE_URL"].strip(), WEBHOOK_PATH))
    print("reads    : %s" % source_url().split("?")[0])
    print("target   : %s" % ("update " + existing["id"] if existing else "create"))
    if not apply:
        print("\nDry run. Add --apply.")
        return

    if existing:
        body = {k: wf[k] for k in ("name", "nodes", "connections", "settings")}
        api("PUT", "/api/v1/workflows/%s" % existing["id"], body)
        wid = existing["id"]
    else:
        wid = api("POST", "/api/v1/workflows", wf)["id"]
    api("POST", "/api/v1/workflows/%s/activate" % wid)
    print("\nOK — %s active" % wid)
    print("%s/workflow/%s" % (env()["N8N_BASE_URL"].strip(), wid))


if __name__ == "__main__":
    main()
