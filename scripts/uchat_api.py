# -*- coding: utf-8 -*-
"""UChat -- read the owner's UChat workspace from here. GET only.

    python scripts/uchat_api.py                  # the workspace at a glance: channels, agents, flows, people
    python scripts/uchat_api.py get team/labels  # any other GET path in UChat's spec, printed as JSON

(Write the path without its leading slash: Git Bash rewrites an argument that
starts with "/" into a Windows path before Python sees it.)

Kept for the move described in docs/features/21-uchat-migration/feature.md:
before any step of it, this shows what the workspace already holds. The key
lives in .env as Uchat_api_key (the owner's own workspace "clix", made 29 Sep
with the "Manage Flow" ability only, so it cannot add or remove people).

SAFETY
  Read-only by construction: the one HTTP helper below sends GET and never
  passes a body. Every write the move needs (send-text, pause-bot,
  assign-agent-group, ...) is a POST, and none of them appears in this file;
  a write helper, if one is ever wanted, gets its own flag and its own
  explicit go. One host, www.uchat.com.au. The key is never printed, and
  phone numbers and email addresses in any answer are masked.

TWO THINGS LEARNED THE HARD WAY
  - UChat sits behind Cloudflare, which refuses Python's default user agent
    with "Error 1010: browser_signature_banned" (a 403 that looks like a bad
    key). curl's user agent passes, so this file sends it (3 Nov 2026).
  - The API cannot create an AI agent, a flow or an integration (the Webhook
    integration included). Those are made in UChat's dashboard by a person;
    after that, everything is reachable here.

The spec: https://www.uchat.com.au/default-api-docs/api-docs.json (257 paths on
3 Nov 2026; a copy is kept in local/uchat-prep/).
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://www.uchat.com.au/api"
MAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\+?\d[\d\s-]{8,}\d")

# What the overview reads, in the order it prints.
OVERVIEW = [
    ("me", "/me"),
    ("workspace", "/team-info"),
    ("channels", "/workspace-settings/channels"),
    ("ai_provider", "/flow/settings/get-default-ai-provider"),
    ("ai_agents", "/flow/ai-agents"),
    ("subflows", "/flow/subflows"),
    ("inbound_webhooks", "/flow/inbound-webhooks"),
    ("team_members", "/team-members"),
    ("agent_groups", "/team/agent-groups"),
    ("labels", "/team/labels"),
    ("ticket_lists", "/team/ticket-lists"),
    ("bot_users", "/flow/bot-users-count"),
]


def env():
    return dict(
        l.strip().split("=", 1)
        for l in open(os.path.join(ROOT, ".env"), encoding="utf-8")
        if l.strip() and not l.startswith("#") and "=" in l
    )


def token():
    t = (env().get("Uchat_api_key") or "").strip().strip('"')
    if not t:
        sys.exit("Uchat_api_key is not set in .env")
    return t


def mask(text):
    return PHONE.sub("<phone>", MAIL.sub("<email>", text))


def api(path):
    """GET one UChat path. There is no other HTTP call in this file."""
    if not path.startswith("/") or "://" in path:
        sys.exit("a path, like /team/labels")
    req = urllib.request.Request(BASE + path, headers={
        "Authorization": "Bearer " + token(),
        "User-Agent": "curl/8.9.1",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r)
    except urllib.error.HTTPError as ex:
        body = ex.read().decode("utf-8", "replace")
        if "1010" in body:
            sys.exit("HTTP %d on %s: Cloudflare refused the user agent (error 1010), not the key" % (ex.code, path))
        return {"_http": ex.code, "_body": mask(body[:300])}


def rows(answer):
    data = answer.get("data") if isinstance(answer, dict) else answer
    return data if isinstance(data, list) else []


def overview():
    got = {name: api(path) for name, path in OVERVIEW}
    me = got["me"] if isinstance(got["me"], dict) else {}
    ws = (got["workspace"] or {}).get("data") or {}
    print("signed in as :", me.get("name"), "| workspace:", ws.get("name"), "(%s)" % ws.get("id"))
    ch = (got["channels"] or {}).get("data") or {}
    print("channels on  :", ", ".join(k for k, v in ch.items() if v) or "-")
    ai = (got["ai_provider"] or {}).get("data") or {}
    print("default AI   :", (ai.get("ai_provider") or "-"), (ai.get("ai_model") or ""))
    for name in ("ai_agents", "subflows", "inbound_webhooks", "team_members", "agent_groups", "labels", "ticket_lists"):
        r = rows(got[name])
        if isinstance(got[name], dict) and "_http" in got[name]:
            print("%-13s: HTTP %s" % (name, got[name]["_http"]))
            continue
        names = [str(x.get("name") or x.get("title") or x.get("id")) for x in r if isinstance(x, dict)]
        print("%-13s: %d  %s" % (name, len(r), mask(", ".join(names[:12]))))
    print("bot users    :", mask(json.dumps((got["bot_users"] or {}).get("data"), ensure_ascii=False)))
    print("\nRead only. The move's plan: docs/features/21-uchat-migration/feature.md.")


def main():
    args = sys.argv[1:]
    if not args:
        return overview()
    if args[0] == "get" and len(args) == 2:
        path = args[1] if args[1].startswith("/") else "/" + args[1]
        if ":" in path:
            sys.exit("that path was rewritten by the shell; write it without the leading slash, like team/labels")
        return print(mask(json.dumps(api(path), ensure_ascii=False, indent=1)))
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
