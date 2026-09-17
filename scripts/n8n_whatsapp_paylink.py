# -*- coding: utf-8 -*-
"""Add the payment link to the live WhatsApp bot.

    python scripts/n8n_whatsapp_paylink.py            # dry run
    python scripts/n8n_whatsapp_paylink.py --apply    # write it
    python scripts/n8n_whatsapp_paylink.py --restore  # put the 17 Sep snapshot back

WHY, 17 SEP

OXS External API rev 1.3 added the short payment link per apartment, and the
Edge Function fetches it for the sender of a chat (`get_payment_link` in
debt-tools/index.ts; identity is the number the message came from, by owner
decision). The bot needs the tool node to reach it, and that is all this
ships: ONE node and ONE wire, lifted from the builder by `built()` so the
repo stays the single definition.

It does not touch the prompt, the three tool texts it displaces, or the
epoch -- `n8n_whatsapp_payment.py --apply` carries the open_request and
get_balance texts, `n8n_whatsapp_teamnote.py --apply` the prompt, the
notify_team node and the epoch. Run them in that order after this, or the bot
has a tool it has not been told about.

Same shape as n8n_whatsapp_knowledge.py, for the same reason: the live
workflow is far ahead of the builder and `n8n_whatsapp.py --apply` is still
forbidden.
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
TOOL = "get_payment_link"
AGENT = "Answer the resident"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-17sep-before-paylink.json")
PLACEHOLDER = "REPLACE_WITH_N8N_WEBHOOK_SECRET"

# The phantom guard in `Reply usable?`: a reply that CLAIMS a ticket is open
# must carry a reference, or the turn goes to the rescue. The first refusal
# probes of the payment link (17 Sep) got past it twice -- "אני פותח לכם
# קריאת שירות" (present tense) and "פתחתי בשבילכם קריאת שירות" (a word the
# alternation did not list). Present-tense forms join, and any one word may
# sit between the verb and קריאה. Future "אפתח" stays out on purpose: "I'll
# open one" before the address arrives is a plan, not a claim.
# A URL in a reply must be one the tool returned in THIS execution. The sixth
# refusal probe of 17 Sep answered "here is your link" with an invented
# https://pay.homies-management.co.il/... and no tool call at all. The prompt
# already says "from the tool, not from your head"; a fabricated link is the
# one failure a sentence cannot be trusted to prevent, so the workflow
# checks: every URL in the output must appear in a get_payment_link
# observation, or the reply is unusable and takes the rescue path (a real
# needs_review ticket and an honest line), never the fake link.
URL_GUARD = {
    "id": "links",
    "leftValue": (
        "={{ (() => { const t = String($json.output || ''); "
        "const urls = t.match(/https?:\\/\\/\\S+/g) || []; if (!urls.length) return true; "
        "let seen = ''; try { for (const s of ($('Answer the resident').first().json.intermediateSteps || [])) { "
        "if (((s.action || {}).tool) === 'get_payment_link') seen += ' ' + String(s.observation || ''); } } catch (e) {} "
        "return urls.every(u => seen.indexOf(u.replace(/[.,;:!?)\\]]+$/, '')) !== -1); })() }}"
    ),
    "rightValue": "",
    "operator": {"type": "boolean", "operation": "true", "singleValue": True},
}

PHANTOM_OLD = "/(פתחתי|פתחנו|נפתחה|נפתחו)( (לך|לכם|לכן|כבר|את))* ?ה?קריא[הת]/"
PHANTOM_NEW = "/(פתחתי|פתחנו|פותח|פותחת|נפתחה|נפתחו|נפתחת)( \\S+){0,2}? ?ה?קריא[הת]/"


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
    # bot asked for a name and a flat where the link now closes the matter.
    W.check_memory_epoch(prompt=W.system_prompt(), inject=U.AGENT_NEW, tools=W.tools_text())

    want = built(TOOL)
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in (AGENT, "Reply usable?"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

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

    cond = by["Reply usable?"]["parameters"]["conditions"]["conditions"]
    phantom = next((c for c in cond if c.get("id") == "phantom"), None)
    if phantom is None:
        sys.exit("Reply usable? has no 'phantom' condition -- refusing to guess.")
    if PHANTOM_NEW not in phantom["leftValue"]:
        if PHANTOM_OLD not in phantom["leftValue"]:
            sys.exit("Anchor missing on live 'Reply usable?' phantom condition.")
        phantom["leftValue"] = phantom["leftValue"].replace(PHANTOM_OLD, PHANTOM_NEW, 1)
        changes.append("Reply usable?: the phantom guard learns the present tense")
    links = next((c for c in cond if c.get("id") == "links"), None)
    if links is None:
        cond.append(dict(URL_GUARD))
        changes.append("Reply usable?: a URL must be one the tool returned")
    elif links.get("leftValue") != URL_GUARD["leftValue"]:
        links["leftValue"] = URL_GUARD["leftValue"]
        changes.append("Reply usable?: URL guard updated")

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
          "run n8n_whatsapp_payment.py --apply (two tool texts) and then\n"
          "n8n_whatsapp_teamnote.py --apply (prompt, notify_team, epoch) -- until\n"
          "those land, the bot has the tool and has not been told it exists.")


if __name__ == "__main__":
    main()
