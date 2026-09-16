# -*- coding: utf-8 -*-
"""SUPERSEDED 13 Sep by n8n_whatsapp_nopage.py: nothing pages a person from
WhatsApp any more, and the nodes this wires are gone. Its dry run exits on a
missing node, which is correct. `--restore` still works from the 3 Sep snapshot.

Make a WhatsApp handover reach a person: wire the bot to "Hand to a person".

    python scripts/n8n_whatsapp_handover.py              # dry run
    python scripts/n8n_whatsapp_handover.py --apply      # write it
    python scripts/n8n_whatsapp_handover.py --restore    # put the 3 Sep snapshot back

WHY
Three paths hand a conversation over -- the model's `transfer_to_human` tool,
the "לדבר עם נציג" tap, and the promise backstop -- and all three ended in a
Supabase row nobody reads. Nothing changed in Chatwoot, nobody was notified,
and the bot kept answering. This wires each path to the sub-workflow built by
`n8n_handover.py`, which pages the department's team inside Chatwoot.

WHAT IT CHANGES, AND NOTHING ELSE

  1. A new If, `Handover this turn?`, off the usable-reply branch, ABOVE the
     promise backstop on the canvas. It decides on evidence the model could
     not fake: the agent's own `intermediateSteps` (did `transfer_to_human`
     run this turn) and the reply's first-person handover sentence -- the
     same channel `Send` reads for `show_menu`, and the same regex the
     backstop uses. Never `isExecuted` or `.all()` on the tool node; both
     were live on 1 Sep and both were wrong.
  2. `Hand to a person`: an Execute Workflow node that fires the sub-workflow
     and does not wait. The reply to the resident is not delayed by six
     Chatwoot calls, and a Chatwoot outage cannot stop the reply.
  3. The promise backstop no longer fires when the tool already ran. Since
     the 1 Sep rewrite it decided on the sentence alone, so a turn with a
     tool call AND "אני מעביר" transferred twice. It still rescues a promise
     made without a call.
  4. The tap path: `Human tap?` -> `Hand to a person (tap)` -> `Transfer the
     tap`. The page happens before the Supabase write; the sub-workflow's
     own guard absorbs the model's tool call on the answer turn.
  5. `transfer_to_human` gains the `department` argument, regenerated from
     the builder so the live body and n8n_whatsapp.py cannot drift, and its
     description stops saying that routing does not exist.

The sub-workflow must exist first (`n8n_handover.py --apply`); this refuses
otherwise. Placement is checked relatively, as n8n_whatsapp_patch.py does:
the live canvas already has complaints, and this must not add any.

Idempotent. Running it twice reports nothing to do.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402
import n8n_handover as H  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-03sep-before-handover.json")
PLACEHOLDER = "REPLACE_WITH_N8N_WEBHOOK_SECRET"

# --------------------------------------------------------------------------
# Expressions. Every brace that would touch another has a space in it: n8n
# closes an expression on the first `}}` it meets.
# --------------------------------------------------------------------------
STEPS = "($('Answer the resident').first().json.intermediateSteps || [])"
TOOL_RAN = ("(() => { try { return %s.some(s => ((s.action || {}).tool) === "
            "'transfer_to_human'); } catch (e) { return false; } })()" % STEPS)

# The sentence test is the backstop's own, so the two nodes cannot disagree
# about what a promise looks like.
SAID = ("(() => { const t = String($json.output || ''); "
        "if (!/(אני |אנחנו )?(מעביר|מעבירה|מעבירים|העברתי|העברנו)/.test(t)) return false; "
        "if (!/(לצוות|לנציג|לטיפול|לעמית)/.test(t)) return false; "
        "if (/(שאעביר|האם להעביר|רוצים שנעביר|אם תרצו)/.test(t)) return false; "
        "return true; })()")

HANDOVER_THIS_TURN = ("={{ (() => { let tap = ''; try { tap = $('Sort').first().json.tap; } "
                      "catch (e) { } if (tap === 'human') return false; "
                      "return %s || %s; })() }}" % (TOOL_RAN, SAID))


def tool_arg(field, fallback):
    """One argument of the model's transfer_to_human call, read off the agent's
    intermediateSteps. toolInput arrives as an object, occasionally as a JSON
    string, occasionally wrapped in {input: ...}; all three are handled."""
    return ("={{ (() => { try { const s = %s.find(x => ((x.action || {}).tool) === "
            "'transfer_to_human'); let o = s ? s.action.toolInput : null; "
            "if (typeof o === 'string') o = JSON.parse(o); "
            "if (o && o.input && typeof o.input === 'object') o = o.input; "
            "o = o || {}; return String(o.%s || %s); } catch (e) { return %s; } })() }}"
            % (STEPS, field, fallback, fallback))


SOURCE = ("={{ %s ? 'tool' : 'backstop' }}" % TOOL_RAN)

# The clause that stops the backstop double-firing. Inserted after the
# sentence test, before the tap test, in the same try/catch style.
PROMISE_ANCHOR = "if (!said) return false;"
PROMISE_CLAUSE = (" try { if (%s.some(s => ((s.action || {}).tool) === 'transfer_to_human')) "
                  "return false; } catch (e) { }" % STEPS)


def schema():
    return [{"id": n, "displayName": n, "required": False, "defaultMatch": False,
             "display": True, "canBeUsedToMatch": True, "type": t}
            for n, t in H.INPUTS]


def execute_node(nid, name, pos, values, wait):
    return {
        "id": nid, "name": name, "type": "n8n-nodes-base.executeWorkflow",
        "typeVersion": 1.2, "position": list(pos),
        "parameters": {
            "workflowId": {"__rl": True, "value": "__SUB_ID__", "mode": "id"},
            "workflowInputs": {"mappingMode": "defineBelow", "value": values,
                               "matchingColumns": [], "schema": schema()},
            "mode": "once",
            "options": {"waitForSubWorkflow": wait},
        },
        "onError": "continueRegularOutput",
    }


def wanted_nodes(sub_id):
    sort = "$('Sort').first().json"
    tool_path = execute_node(
        "cw-handover-do", "Hand to a person", (1440, -600),
        {"conv_id": "={{ %s.conv_id }}" % sort,
         "phone": "={{ %s.to }}" % sort,
         "reason": tool_arg("reason", "'caller_request'"),
         "department": tool_arg("department", "''"),
         "description": tool_arg("description", "String(%s.in_text || '')" % sort),
         "source": SOURCE, "mode": "new", "now_override": ""},
        wait=False)
    tap_path = execute_node(
        "cw-handover-tap", "Hand to a person (tap)", (720, -360),
        {"conv_id": "={{ %s.conv_id }}" % sort,
         "phone": "={{ %s.to }}" % sort,
         "reason": "caller_request", "department": "", "description": "",
         "source": "tap", "mode": "new", "now_override": ""},
        wait=False)
    gate = {
        "id": "cw-handover-if", "name": "Handover this turn?",
        "type": "n8n-nodes-base.if", "typeVersion": 2, "position": [1200, -600],
        "parameters": {"conditions": {
            "options": {"caseSensitive": True, "leftValue": "",
                        "typeValidation": "loose", "version": 1},
            "conditions": [{"id": "handover", "leftValue": HANDOVER_THIS_TURN,
                            "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true",
                                         "singleValue": True}}],
            "combinator": "and"}, "options": {}},
    }
    out = [gate, tool_path, tap_path]
    return json.loads(json.dumps(out, ensure_ascii=False).replace("__SUB_ID__", sub_id))


def built(name):
    for n in W.workflow(W.env())["nodes"]:
        if n["name"] == name:
            return n
    sys.exit("n8n_whatsapp.py no longer builds a %r node." % name)


def ensure_link(conns, src, dst, index=0):
    """Add src -> dst on output `index` if it is not already there."""
    branches = conns.setdefault(src, {}).setdefault("main", [])
    while len(branches) <= index:
        branches.append([])
    if any(t.get("node") == dst for t in branches[index]):
        return False
    branches[index].append({"node": dst, "type": "main", "index": 0})
    return True


def drop_link(conns, src, dst):
    changed = False
    for branch in conns.get(src, {}).get("main", []):
        before = len(branch)
        branch[:] = [t for t in branch if t.get("node") != dst]
        changed = changed or len(branch) != before
    return changed


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

    sub = H.find()
    if sub is None:
        sys.exit("The sub-workflow %r does not exist yet. Run "
                 "`python scripts/n8n_handover.py --apply` first." % H.WF_NAME)

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes = live["nodes"]
    conns = live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in ("Sort", "Reply usable?", "Promised a transfer, made none?",
                 "Human tap?", "Transfer the tap", "transfer_to_human",
                 "Answer the resident"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    # The tool text this pushes is covered by the memory epoch.
    W.check_memory_epoch(tools=W.tools_text())

    before_layout = layout_complaints(nodes)
    changes = []

    # 1, 2, 4: the three new nodes, added or brought up to date.
    for want in wanted_nodes(sub["id"]):
        have = by.get(want["name"])
        if have is None:
            nodes.append(want)
            by[want["name"]] = want
            changes.append("add node %r" % want["name"])
        elif json.dumps(have.get("parameters"), sort_keys=True, ensure_ascii=False) != \
                json.dumps(want["parameters"], sort_keys=True, ensure_ascii=False):
            have["parameters"] = want["parameters"]
            have["onError"] = want.get("onError")
            changes.append("update node %r" % want["name"])

    if ensure_link(conns, "Reply usable?", "Handover this turn?", 0):
        changes.append("wire Reply usable?[true] -> Handover this turn?")
    if ensure_link(conns, "Handover this turn?", "Hand to a person", 0):
        changes.append("wire Handover this turn? -> Hand to a person")
    if drop_link(conns, "Human tap?", "Transfer the tap"):
        changes.append("unwire Human tap? -> Transfer the tap")
    if ensure_link(conns, "Human tap?", "Hand to a person (tap)", 0):
        changes.append("wire Human tap? -> Hand to a person (tap)")
    if ensure_link(conns, "Hand to a person (tap)", "Transfer the tap", 0):
        changes.append("wire Hand to a person (tap) -> Transfer the tap")

    # 3: the backstop stands down when the tool ran.
    guard = by["Promised a transfer, made none?"]
    for c in guard["parameters"]["conditions"]["conditions"]:
        lv = str(c.get("leftValue", ""))
        if "intermediateSteps" in lv:
            continue
        if PROMISE_ANCHOR not in lv:
            sys.exit("Anchor missing in the promise guard -- refusing to guess:\n  %s"
                     % PROMISE_ANCHOR)
        c["leftValue"] = lv.replace(PROMISE_ANCHOR, PROMISE_ANCHOR + PROMISE_CLAUSE, 1)
        changes.append("Promised a transfer, made none?: stand down when the tool ran")

    # 5: the tool, regenerated from the builder.
    node = by["transfer_to_human"]
    want = built("transfer_to_human")["parameters"]
    for key, label in (("jsonBody", "body (department argument)"),
                       ("toolDescription", "description (routing exists now)")):
        if node["parameters"].get(key) != want[key]:
            node["parameters"][key] = want[key]
            changes.append("transfer_to_human: %s" % label)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("sub      : %s  (%s)" % (sub["name"], sub["id"]))
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
    for src in ("Reply usable?", "Handover this turn?", "Human tap?", "Hand to a person (tap)"):
        print("  %s -> %s" % (src, json.dumps(back["connections"].get(src), ensure_ascii=False)))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
