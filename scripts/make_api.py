"""Make.com — read the client's organisation from here.

    python scripts/make_api.py            # teams, scenarios, hooks, connections
    python scripts/make_api.py blueprint <scenario_id>   # one scenario's modules
    python scripts/make_api.py runs <scenario_id>        # its recent executions

Same road as every other service in this repo: the token lives in .env (as
MAKE_API_TOKEN, or MAKE_API which is what the owner first wrote), the zone and
organisation are fixed below, and nothing here writes. A write helper, when one
is wanted, gets its own flag and its own explicit go — Make is the client's
account, and the standing rule is never to write to client systems unasked.

Zone matters: Make tokens are per-zone, and a token minted on eu2 gets a 403
from eu1 that looks exactly like a bad token.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZONE = "eu2.make.com"
ORG_ID = 1360325


def env():
    return dict(
        l.strip().split("=", 1)
        for l in open(os.path.join(ROOT, ".env"), encoding="utf-8")
        if l.strip() and not l.startswith("#") and "=" in l
    )


def token():
    e = env()
    t = (e.get("MAKE_API_TOKEN") or e.get("MAKE_API") or "").strip()
    if not t:
        sys.exit("MAKE_API_TOKEN is not set in .env")
    return t


def api(path, params=None):
    url = "https://%s/api/v2%s" % (ZONE, path)
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={
        "Authorization": "Token " + token(),
        "User-Agent": "homies/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as ex:
        body = ex.read().decode("utf-8", "replace")
        sys.exit("HTTP %d on %s\n%s" % (ex.code, path, body[:600]))


def teams():
    return api("/teams", {"organizationId": ORG_ID})["teams"]


def overview():
    org = api("/organizations/%d" % ORG_ID)["organization"]
    print("organisation :", org["name"], "(%s, zone %s)" % (ORG_ID, org.get("zone", ZONE)))
    for t in teams():
        print("\nteam :", t["name"], "(%s)" % t["id"])
        sc = api("/scenarios", {"teamId": t["id"]})["scenarios"]
        if not sc:
            print("  no scenarios")
        for s in sc:
            state = "ON " if s.get("isActive") else "off"
            sched = s.get("scheduling", {}) or {}
            print("  [%s] %-6s %-45s %s" % (
                state, s["id"], s["name"][:45],
                sched.get("type", "") + (" %s" % sched.get("interval", "") if sched.get("interval") else "")))
            if s.get("lastEdit"):
                print("        last edit %s" % s["lastEdit"][:16])
        hooks = api("/hooks", {"teamId": t["id"]})["hooks"]
        for h in hooks:
            print("  hook   %-6s %-35s %s" % (h["id"], h["name"][:35], h.get("url", "")))
        conns = api("/connections", {"teamId": t["id"]})["connections"]
        for c in conns:
            print("  conn   %-6s %-35s %s" % (c["id"], c["name"][:35], c.get("accountName", "")))


def blueprint(sid):
    bp = api("/scenarios/%s/blueprint" % sid)["response"]["blueprint"]
    print("scenario :", bp.get("name"))
    for m in bp.get("flow", []):
        print("  %-3s %-40s" % (m["id"], m["module"]))
        for k, v in (m.get("mapper") or {}).items():
            v = json.dumps(v, ensure_ascii=False)
            print("        %s = %s" % (k, v[:140]))
        for r in m.get("routes") or []:
            for mm in r.get("flow", []):
                print("      -> %-3s %-40s" % (mm["id"], mm["module"]))
                for k, v in (mm.get("mapper") or {}).items():
                    v = json.dumps(v, ensure_ascii=False)
                    print("            %s = %s" % (k, v[:140]))


def runs(sid):
    logs = api("/scenarios/%s/logs" % sid, {"pg[limit]": 15})["scenarioLogs"]
    for l in logs:
        print("  %s  %-8s ops %-4s %s" % (
            l.get("timestamp", "")[:19], l.get("status", ""), l.get("operations", ""),
            (l.get("detail") or "")[:80]))


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        overview()
    elif a[0] == "blueprint":
        blueprint(a[1])
    elif a[0] == "runs":
        runs(a[1])
    else:
        sys.exit(__doc__)
