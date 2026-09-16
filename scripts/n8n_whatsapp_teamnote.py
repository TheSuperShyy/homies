# -*- coding: utf-8 -*-
"""'I've let the team know' becomes true: the bot notes a matter for its team.

    python scripts/n8n_whatsapp_teamnote.py              # dry run
    python scripts/n8n_whatsapp_teamnote.py --apply      # write it
    python scripts/n8n_whatsapp_teamnote.py --restore    # put the 14 Sep snapshot back

WHY
The owner, 14 Sep, refining 13 Sep: the goal is to cut the office's workload;
the bot is 100% of customer support; past its threshold (no payment link, no
billing changes, no move-in/out paperwork, no contracts, no quotes) it must
stay accommodating and not dead-end the resident -- "ok, I'll let the right
team know" -- without promising what that team will do or when. Asked what
sits behind that sentence: "a mention in Chatwoot is ok, like regular."
Office phone and email only if asked. Emergencies: no office line.

What was live since 13 Sep was the opposite shape: nothing notified anyone and
the threshold cases ended with "the office handles this, here is the phone" --
the dead end. The alert half of feature 16 (a private note that @mentions the
department team; nobody rings, members see it in Chatwoot) is exactly "a
mention like regular" and still exists, dormant: the sub-workflow
oB66atFlWwtkSGgN and the ticker IVNR5iNn7bQS8JgP. This puts the call back --
the same wire, new words.

NOT A RESTORE. The 13 Sep snapshot carries the old framing (a "handover" the
bot steps back from, a נציג button, "the rep will get back to you") and the
old prompt. This builds forward from the live 31-node workflow:

  1. `notify_team`, the tool, from the builder (n8n_whatsapp.py TOOLS). Same
     httpRequestTool shape as the removed `transfer_to_human`; the body still
     calls the debt-tools handler by its old name, because that handler is the
     voice agents' too and writes the call_outcomes row and the emergency
     ticket backstop. Wired to the agent on ai_tool.
  2. `Team note this turn?`, an If off `Reply usable?[true]`, above the reply
     branch on the canvas (executionOrder v1 runs by position; a failed Send
     further down must not end the run before the note is made). True when
     the tool ran this turn (the agent's own intermediateSteps -- never
     `isExecuted`, never `.all()` on the tool node: both were live on 1 Sep and
     both were wrong) OR the reply says the team knows without a call behind
     it. That second half is the promise backstop, folded into the same node:
     a first-person "I've told the team" with no tool call still makes the
     note, so the sentence is true either way.
  3. `Let the team know`, an Execute Workflow into the sub-workflow, fire and
     forget: the reply is not delayed by six Chatwoot calls and a Chatwoot
     outage cannot stop it. Inputs from Sort and the tool's own arguments;
     reason falls back to `other`, department to the sub-workflow's default.
  4. The three texts the memory epoch hashes, synced from their owners: the
     prompt (n8n_whatsapp.system_prompt), the injected template
     (n8n_whatsapp_untemplate.AGENT_NEW, unchanged) and show_menu's
     description (unchanged). Then the memory node's sessionKey -> epoch 21.

No tap path. The third button stays משהו אחר; a request for a person reaches
the model like any message and is `notify_team(caller_request)` by judgment.

Snapshot first (docs/handover/n8n-whatsapp-live-14sep-before-teamnote.json,
secret redacted, staticData stripped); `--restore` puts it back. Placement is
checked relatively, as n8n_whatsapp_patch.py does. Idempotent: a second run
reports nothing to do.

The sub-workflow must carry the 14 Sep reasons first
(`python scripts/n8n_handover.py --apply --publish`); this refuses otherwise.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_untemplate as U  # noqa: E402
import n8n_handover as H  # noqa: E402
from n8n_whatsapp_handover import built, execute_node, tool_arg, STEPS, ensure_link  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-14sep-before-teamnote.json")
PLACEHOLDER = "REPLACE_WITH_N8N_WEBHOOK_SECRET"

TOOL = "notify_team"
IF_NODE = "Team note this turn?"
DO_NODE = "Let the team know"

# The paging machinery of 3-13 Sep must not be on the workflow: this builds
# forward from the no-page state, not on top of the old design.
STALE = ("Human tap?", "Hand to a person (tap)", "Transfer the tap", "transfer_to_human",
         "Handover this turn?", "Hand to a person", "Promised a transfer, made none?",
         "Transfer it anyway", "Carry the reply")
NEED = ("Sort", "Reply usable?", "Answer the resident", "show_menu", "Type for a moment", "Log reply")

# --------------------------------------------------------------------------
# Expressions. Every brace that would touch another has a space in it: n8n
# closes an expression on the first `}}` it meets.
# --------------------------------------------------------------------------
TOOL_RAN = ("(() => { try { return %s.some(s => ((s.action || {}).tool) === "
            "'%s'); } catch (e) { return false; } })()" % (STEPS, TOOL))

# The reply says the team knows. First person, a team as the destination, and
# not a conditional offer. The 3 Sep list was transfer verbs only
# (מעביר/העברתי); the bot's words are "I've updated / told / noted" now, so the
# verb list follows. The passive `הועברה לטיפול` is what a status reply says
# about a ticket passed on weeks ago and is deliberately NOT here (the 27 Aug
# false-positive class).
# Two shapes, measured 14 Sep (execs 40747-40755): "I told / will note this for
# the team" (a verb, incl. the infinitive of intent, plus a team), and a
# call-back promise ("they will get back to you") with no tool behind it --
# the note is what brings that promise closest to true. Only a conditional
# OFFER is excluded; a bare "אם תרצו" elsewhere in the reply is not.
SAID = ("(() => { const t = String($json.output || ''); "
        "const told = /(עדכנתי|אעדכן|הודעתי|אודיע|מסרתי|רשמתי|ארשום|לרשום|לעדכן|להעביר|העברתי|העברנו|מעביר|מעבירה|מעבירים)/.test(t) "
        "&& /(לצוות|את הצוות|למחלקה|לגבייה|להנהלה|לתפעול|לשירות|לנציג|לעמית)/.test(t); "
        "const promised = /(יחזרו אליכם|יחזור אליכם|נחזור אליכם|יצרו אתכם קשר|יצרו איתכם קשר|ייצרו אתכם קשר|ייצרו איתכם קשר|ניצור אתכם קשר|ניצור איתכם קשר|יצור אתכם קשר|יצור איתכם קשר)/.test(t); "
        "if (!told && !promised) return false; "
        "if (/(שאעביר|האם להעביר|רוצים שנעביר|רוצים שאעביר|שאעדכן|האם לעדכן|רוצים שאעדכן|שארשום|האם לרשום|רוצים שארשום)/.test(t)) return false; "
        "return true; })()")

NOTE_THIS_TURN = "={{ %s || %s }}" % (TOOL_RAN, SAID)


def wanted_nodes(sub_id):
    sort = "$('Sort').first().json"
    tool = built(TOOL)
    tool = {"id": "cw-notify-team", "name": TOOL, "type": tool["type"],
            "typeVersion": tool["typeVersion"], "position": [1680, 420],
            "parameters": tool["parameters"]}
    # tool_arg() reads the old tool name; re-point it at this one.
    def arg(field, fallback):
        return tool_arg(field, fallback).replace("'transfer_to_human'", "'%s'" % TOOL)
    do = execute_node(
        "cw-teamnote-do", DO_NODE, (1440, -600),
        {"conv_id": "={{ %s.conv_id }}" % sort,
         "phone": "={{ %s.to }}" % sort,
         "reason": arg("reason", "'other'"),
         "department": arg("department", "''"),
         "description": arg("description", "String(%s.in_text || '')" % sort),
         "source": "={{ %s ? 'tool' : 'backstop' }}" % TOOL_RAN,
         "mode": "new", "now_override": ""},
        wait=False)
    do = json.loads(json.dumps(do, ensure_ascii=False).replace("__SUB_ID__", sub_id))
    iff = {
        "id": "cw-teamnote-if", "name": IF_NODE, "type": "n8n-nodes-base.if",
        "typeVersion": 2, "position": [1200, -600],
        "parameters": {"conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 1},
            "conditions": [{"id": "teamnote", "leftValue": NOTE_THIS_TURN, "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
            "combinator": "and"}, "options": {}},
    }
    return [tool, iff, do]


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


def same(a, b):
    return json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    sub = H.find()
    if sub is None or not sub.get("active"):
        sys.exit("The sub-workflow %r must exist and be published: "
                 "python scripts/n8n_handover.py --apply --publish" % H.WF_NAME)
    live_sub = W.api("GET", "/api/v1/workflows/%s" % sub["id"])
    decide = next((n for n in live_sub["nodes"] if n["name"] == "Decide the routing"), None)
    if decide is None or "DEPT_BY_REASON" not in (decide["parameters"].get("jsCode") or ""):
        sys.exit("The live sub-workflow does not carry the 14 Sep reasons yet: "
                 "python scripts/n8n_handover.py --apply --publish first.")

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in NEED:
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)
    stale = [s for s in STALE if s in by]
    if stale:
        sys.exit("The 3-13 Sep paging nodes are still on the workflow: %s. Run "
                 "n8n_whatsapp_nopage.py --apply first; this builds forward from that." % stale)

    prompt = W.system_prompt()
    W.check_greeting(prompt)
    W.check_memory_epoch(prompt=prompt, inject=U.AGENT_NEW, tools=W.tools_text())

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))

    before_layout = layout_complaints(nodes)
    changes = []

    # 1-3. the three nodes, added or brought up to date
    for want in wanted_nodes(sub["id"]):
        have = by.get(want["name"])
        if have is None:
            nodes.append(want)
            by[want["name"]] = want
            changes.append("add node %r" % want["name"])
        elif not same(have.get("parameters"), want["parameters"]):
            have["parameters"] = want["parameters"]
            if "onError" in want:
                have["onError"] = want["onError"]
            changes.append("update node %r" % want["name"])

    # wiring
    tool_links = conns.setdefault(TOOL, {}).setdefault("ai_tool", [[]])
    if not any(t.get("node") == "Answer the resident" for t in tool_links[0]):
        tool_links[0].append({"node": "Answer the resident", "type": "ai_tool", "index": 0})
        changes.append("wire %s -> Answer the resident (ai_tool)" % TOOL)
    if ensure_link(conns, "Reply usable?", IF_NODE, 0):
        changes.append("wire Reply usable?[true] -> %s" % IF_NODE)
    if ensure_link(conns, IF_NODE, DO_NODE, 0):
        changes.append("wire %s -> %s" % (IF_NODE, DO_NODE))

    # 4. the hashed texts and the epoch
    agent = by["Answer the resident"]["parameters"]
    if agent.get("options", {}).get("systemMessage") != prompt:
        old = agent.get("options", {}).get("systemMessage") or ""
        agent.setdefault("options", {})["systemMessage"] = prompt
        changes.append("prompt: %d chars -> %d (note it for the team; office details "
                       "only if asked; never who or when)" % (len(old), len(prompt)))
    if agent.get("text") != U.AGENT_NEW:
        agent["text"] = U.AGENT_NEW
        changes.append("inject: synced from n8n_whatsapp_untemplate.AGENT_NEW")
    menu_desc = W.tool("show_menu")["description"]
    if by["show_menu"]["parameters"].get("description") != menu_desc:
        by["show_menu"]["parameters"]["description"] = menu_desc
        changes.append("show_menu: description synced")
    mem = next((n for n in nodes if n["type"].endswith("memoryBufferWindow")), None)
    if mem is None:
        sys.exit("No memory node on the live workflow -- refusing to guess.")
    want_key = "={{ $json.to }}-%d" % W.MEMORY_EPOCH
    if mem["parameters"].get("sessionKey") != want_key:
        changes.append("memory epoch: %s -> %s (every existing buffer is abandoned)"
                       % (mem["parameters"].get("sessionKey"), want_key))
        mem["parameters"]["sessionKey"] = want_key

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("sub      : %s  (%s)" % (sub["name"], sub["id"]))
    print("nodes    : %d" % len(nodes))
    if not changes:
        print("\nNothing to do. Live already matches.")
        return
    print("\nchanges:")
    for ch in changes:
        print("  - %s" % ch)

    worse = sorted(layout_complaints(nodes) - before_layout)
    if worse:
        sys.exit("REFUSING TO PATCH. This would introduce placement problems "
                 "that are not already there:\n    " + "\n    ".join(worse))

    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": nodes, "connections": conns,
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    print("\nwritten: %d nodes. Connections now:" % len(back["nodes"]))
    for src in ("Reply usable?", IF_NODE, TOOL):
        print("  %s -> %s" % (src, json.dumps(back["connections"].get(src), ensure_ascii=False)))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
