# -*- coding: utf-8 -*-
"""WhatsApp message templates on the WhatsApp Business Account, from the repo.

    python scripts/wa_templates.py                          # list: name, status, category, language
    python scripts/wa_templates.py create <name>            # dry: show what would be submitted
    python scripts/wa_templates.py create <name> --apply    # submit it to Meta for approval
    python scripts/wa_templates.py chatwoot                 # which templates Chatwoot's inbox 1 has synced

The source of truth is docs/features/11-whatsapp-bot/templates.md: one
section per template, parsed here by its bullet fields and the fenced body.
Meta is the copy. Approval is Meta's decision (UTILITY templates usually
clear in minutes to hours); `list` prints PENDING / APPROVED / REJECTED and,
for a rejection, the reason.

The token is WHATSAPP_ACCESS_TOKEN -- the system-user token that never
expires and carries whatsapp_business_management. WHATSAPP_TOKEN in the same
file expired on 8 Aug 2026 and is not read. Nothing here prints either.

Templates belong to the WABA, not to the number: everything created on the
test account has to be created again on Homies' own WABA at cutover, with the
same command against the new ids in .env.
"""
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs", "features", "11-whatsapp-bot", "templates.md")
GRAPH = "https://graph.facebook.com/v21.0"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def env():
    return dict(
        l.strip().split("=", 1)
        for l in io.open(os.path.join(ROOT, ".env"), encoding="utf-8")
        if l.strip() and not l.startswith("#") and "=" in l
    )


def graph(method, path, token, body=None):
    req = urllib.request.Request(
        GRAPH + path, method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                 "User-Agent": "homies/1.0"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read() or b"{}")
    except urllib.error.HTTPError as ex:
        err = json.loads(ex.read().decode("utf-8", "replace") or "{}").get("error", {})
        return {"__http": ex.code, "__error": err.get("message", ""), "__sub": err.get("error_user_msg", "")}


def templates_from_doc():
    """Every `## name` section of templates.md with its fields and fenced body."""
    text = io.open(DOC, encoding="utf-8").read()
    out = {}
    for sec in re.split(r"^## ", text, flags=re.M)[1:]:
        name = sec.split("\n", 1)[0].strip()
        if not re.fullmatch(r"[a-z0-9_]+", name):
            continue
        field = lambda k: (re.search(r"^- \*\*%s:\*\*\s*(.+)$" % k, sec, re.M) or [None, ""])[1].strip()
        body = (re.search(r"```\n(.*?)\n```", sec, re.S) or [None, ""])[1].strip()
        ex = [e.strip(" `") for e in field("examples").split("·")] if field("examples") else []
        out[name] = {"name": name, "category": field("category"), "language": field("language"),
                     "body": body, "examples": ex}
    return out


def main():
    e = env()
    token = e.get("WHATSAPP_ACCESS_TOKEN", "").strip()
    waba = e.get("WHATSAPP_WABA_ID", "").strip()
    if not token or not waba:
        sys.exit("WHATSAPP_ACCESS_TOKEN / WHATSAPP_WABA_ID missing from .env")
    args = sys.argv[1:]

    if args[:1] == ["chatwoot"]:
        cw = e["CHATWOOT_URL"].rstrip("/") + "/api/v1/accounts/%s/inboxes/1" % e.get("CHATWOOT_ACCOUNT_ID", "2")
        req = urllib.request.Request(cw, headers={"api_access_token": e["CHATWOOT_API_TOKEN"].strip()})
        ib = json.loads(urllib.request.urlopen(req, timeout=30).read())
        for t in ib.get("message_templates") or []:
            print("  %-36s %-10s %-8s %s  ns=%s" % (t.get("name"), t.get("status"), t.get("language"),
                                                    t.get("category"), (t.get("namespace") or "")[:12]))
        print("%d template(s) synced into Chatwoot inbox 1" % len(ib.get("message_templates") or []))
        return

    if not args or args[0] == "list":
        r = graph("GET", "/%s/message_templates?fields=name,status,category,language,rejected_reason&limit=50" % waba, token)
        if "__http" in r:
            sys.exit("HTTP %s: %s" % (r["__http"], r["__error"]))
        for t in r.get("data", []):
            line = "  %-36s %-10s %-8s %s" % (t["name"], t["status"], t["language"], t["category"])
            if t.get("rejected_reason") and t["rejected_reason"] != "NONE":
                line += "  rejected: " + t["rejected_reason"]
            print(line)
        print("%d template(s) on WABA %s" % (len(r.get("data", [])), waba))
        return

    if args[0] == "create" and len(args) >= 2:
        name = args[1]
        apply = "--apply" in args
        t = templates_from_doc().get(name)
        if not t:
            sys.exit("no section `## %s` in %s" % (name, os.path.relpath(DOC, ROOT)))
        nvars = len(set(re.findall(r"\{\{(\d+)\}\}", t["body"])))
        if len(t["examples"]) != nvars:
            sys.exit("%s: %d variables in the body but %d examples" % (name, nvars, len(t["examples"])))
        if not t["category"] or not t["language"] or not t["body"]:
            sys.exit("%s: category, language and a fenced body are all required" % name)
        existing = graph("GET", "/%s/message_templates?fields=name,status,language&limit=50" % waba, token)
        for x in existing.get("data", []):
            if x["name"] == name and x["language"] == t["language"]:
                sys.exit("%s (%s) already exists on the WABA with status %s -- a change is a new name (e.g. %s_v2)."
                         % (name, t["language"], x["status"], name))
        body = {"name": name, "language": t["language"], "category": t["category"],
                "components": [{"type": "BODY", "text": t["body"],
                                **({"example": {"body_text": [t["examples"]]}} if nvars else {})}]}
        print("template : %s  (%s, %s)" % (name, t["category"], t["language"]))
        print("body     : %s" % t["body"])
        print("examples : %s" % " · ".join(t["examples"]))
        if not apply:
            print("\nDry run. Re-run with --apply to submit it to Meta.")
            return
        r = graph("POST", "/%s/message_templates" % waba, token, body)
        if "__http" in r:
            sys.exit("HTTP %s: %s %s" % (r["__http"], r["__error"], r["__sub"]))
        print("\nsubmitted: id %s, status %s, category %s" % (r.get("id"), r.get("status"), r.get("category")))
        print("Meta reviews it; `python scripts/wa_templates.py` shows the verdict, `chatwoot` shows when inbox 1 has it.")
        return

    sys.exit(__doc__)


if __name__ == "__main__":
    main()
