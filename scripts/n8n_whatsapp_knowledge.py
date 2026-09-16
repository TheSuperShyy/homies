# -*- coding: utf-8 -*-
"""Add the services lookup to the live WhatsApp bot.

    python scripts/n8n_whatsapp_knowledge.py            # dry run
    python scripts/n8n_whatsapp_knowledge.py --apply    # write it
    python scripts/n8n_whatsapp_knowledge.py --restore  # put the 16 Sep snapshot back

WHY, 16 SEP
The owner asked for the client's website turned into a knowledge base. The
entries live in the Edge Function (`SERVICES` in
`supabase/functions/debt-tools/index.ts`) and reach the bot as one more tool,
`get_service_info`, rather than as prompt text: the catalogue is ~4k characters
against an 8.5k prompt, and both agents are open by owner decision, so a
catalogue in the fence is a rulebook under another name.

This ships ONE node and ONE wire. It does not touch the prompt or the epoch --
`n8n_whatsapp_teamnote.py --apply` owns those, and has to run after this, or
the bot is told about a tool it has not been given.

The node is not invented here. `n8n_whatsapp.py` builds it (`tool_services`,
beside the other three Edge Function tools) and `built()` lifts it out, so the
repo stays the single definition and this file is only the delivery. That is
also why `n8n_whatsapp.py --apply` is still forbidden: the live workflow is
ahead of the builder by eight nodes, and a full write would delete them.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_untemplate as U  # noqa: E402
from n8n_whatsapp_handover import built  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
TOOL = "get_service_info"
AGENT = "Answer the resident"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-16sep-before-knowledge.json")
PLACEHOLDER = "REPLACE_WITH_N8N_WEBHOOK_SECRET"


def snapshot(live):
    if os.path.exists(SNAPSHOT):
        return False
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    live = dict(live, staticData="<stripped: runtime state keyed by phone numbers>")
    text = json.dumps(live, ensure_ascii=False, indent=1)
    if secret:
        if secret not in text:
            sys.exit("The live workflow does not contain N8N_WEBHOOK_SECRET from .env, "
                     "so the snapshot's redaction would miss. Refusing to write it.")
        text = text.replace(secret, PLACEHOLDER)
    with open(SNAPSHOT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return True


def restore():
    snap = json.load(open(SNAPSHOT, encoding="utf-8"))
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    if not secret:
        sys.exit("N8N_WEBHOOK_SECRET is not in .env; the snapshot's Sort node would "
                 "go live with a placeholder secret. Refusing.")
    body = json.loads(json.dumps(snap, ensure_ascii=False).replace(PLACEHOLDER, secret))
    W.api("PUT", "/api/v1/workflows/%s" % WORKFLOW_ID, {
        "name": body["name"], "nodes": body["nodes"],
        "connections": body["connections"], "settings": body.get("settings", {})})
    print("restored %s from %s (%d nodes)" % (WORKFLOW_ID, SNAPSHOT, len(body["nodes"])))


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    # The guard first. A new tool moves the tools hash exactly as a prompt edit
    # moves the prompt hash, and a buffer minted before it holds turns where the
    # bot said it did not know something it can now answer.
    W.check_memory_epoch(prompt=W.system_prompt(), inject=U.AGENT_NEW, tools=W.tools_text())

    want = built(TOOL)
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    if AGENT not in by:
        sys.exit("No %r node on the live workflow -- refusing to guess." % AGENT)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    changes = []

    have = by.get(TOOL)
    if have is None:
        nodes.append(want)
        changes.append("add node %r (%s)" % (TOOL, want["type"]))
    else:
        for field in ("parameters", "type", "typeVersion", "credentials"):
            if field in want and have.get(field) != want[field]:
                have[field] = want[field]
                changes.append("update %r %s" % (TOOL, field))

    links = conns.setdefault(TOOL, {}).setdefault("ai_tool", [[]])
    if not any(t.get("node") == AGENT for t in links[0]):
        links[0].append({"node": AGENT, "type": "ai_tool", "index": 0})
        changes.append("wire %s -> %s (ai_tool)" % (TOOL, AGENT))

    if not changes:
        print("\nNothing to do. Live already matches.")
        return

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    print("\nchanges:")
    for c in changes:
        print("  - %s" % c)

    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": nodes,
        "connections": conns, "settings": live.get("settings", {}),
    })
    print("\nwritten. Re-run without --apply to confirm it reports nothing to do, then\n"
          "run n8n_whatsapp_teamnote.py --apply for the prompt and the epoch -- until\n"
          "that lands, the bot has the tool and has not been told it exists.")


if __name__ == "__main__":
    main()
