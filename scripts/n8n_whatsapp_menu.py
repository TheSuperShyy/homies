# -*- coding: utf-8 -*-
"""A lost resident gets shown the options — decided by the model, not a keyword.

    python scripts/n8n_whatsapp_menu.py            # dry run
    python scripts/n8n_whatsapp_menu.py --apply    # write it

WHY — the owner's 2 Sep screenshot: "hey is this homies" was answered well,
then "idk" got a warm sign-off and a dead conversation. Not knowing what you
need was filed under needing nothing. His constraint, verbatim: "i dont want
a strict rule for keywords i want it to be general remember how we input
rules using keywords for trigger and we created a dumb bot i want to prevent
that from happening again."

So the WHEN is the model's judgment, carried by a tool description like every
other judgment in this workflow, and the menu itself stays the system's:

1. `show_menu`, a Code tool. It writes `staticData.menu_exec = <execution id>`
   and tells the model the list will appear under its next message. THE FLAG
   CANNOT LEAK: concurrent executions never see each other's staticData (a
   per-execution snapshot — measured, see the batch patcher), and a later
   execution's id differs, so the equality below fails. `isExecuted` was
   never an option; it is spuriously true and killed the promise guard for a
   day. If the sandbox lacks staticData or the execution id, the tool
   degrades to telling the model to describe the options in its own words —
   the failure mode is the feature without buttons, never an error.
2. `Send` attaches the option rows whenever `menu_exec` equals THIS run's id
   — the same one-message mechanism the echo clause uses: the model's own
   words on top, the rows underneath.
3. The attached list gains the balance row, matching the real canned menu.
   Chatwoot forwards a tap's TITLE, not its id, and 'יתרה ותשלומים' from the
   canned menu already reaches the model as plain text today (it is not in
   Sort's TAP_KIND) — so no Sort change, this is the behaviour that already
   exists.

The description's source of truth is W.tool('show_menu') in n8n_whatsapp.py,
synced here like every other tool patcher. Idempotent: run twice, the second
reports nothing to do.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"

TOOL_CODE = """\
// The flag Send reads to attach the option rows under this reply. Keyed by
// execution id: concurrent runs cannot see this write (staticData is a
// per-execution snapshot) and a later run's id differs, so it cannot leak.
try {
  const s = $getWorkflowStaticData('global');
  const id = ($execution && $execution.id) ? String($execution.id) : '';
  s.menu_exec = id;
  if (id) {
    return 'רשימת האפשרויות תוצג לדייר מתחת להודעה הבאה שלך. כתוב הודעה קצרה משלך; הרשימה כבר מציעה את האפשרויות, אז אל תמנה אותן בעצמך.';
  }
} catch (e) { }
return 'אין אפשרות להציג את הרשימה כרגע. הצג לדייר בקצרה, במילים שלך, במה אתה יכול לעזור.';
"""

# --------------------------------------------------------------------------
# Send: the flag joins the menu condition, and the balance row joins the list.
# --------------------------------------------------------------------------
COND_OLD = "if ($('Sort').first().json.greeting || t.indexOf("
COND_NEW = ("if ($('Sort').first().json.greeting || "
            "(() => { try { return $getWorkflowStaticData('global').menu_exec"
            " === String($execution.id); } catch (e) { return false; } })() || "
            "t.indexOf(")

ITEMS_OLD = ("{ title: 'מצב קריאה קיימת', value: 'status' }, "
             "{ title: 'לדבר עם נציג', value: 'human' }")
ITEMS_NEW = ("{ title: 'מצב קריאה קיימת', value: 'status' }, "
             "{ title: 'יתרה ותשלומים', value: 'balance' }, "
             "{ title: 'לדבר עם נציג', value: 'human' }")

# The net, promise-guard doctrine: decide on the reply alone. Three probes
# (22394, 22403, 22410) showed the model reliably ANSWERS a lost resident by
# reciting the four flows in words while leaving the tool unused — its
# judgment about WHEN to present options is right, its format is wrong, and a
# third prompt round is where the address-justification lesson says to stop.
# So when a reply names three or more of the four flows, it IS the options
# message, and the rows attach under it. This reads the bot's own output,
# never the resident's words — the owner's no-keyword-triggers rule is about
# resident input, and the promise guard set this exact precedent.
RECITE_OLD = ("(() => { try { return $getWorkflowStaticData('global').menu_exec"
              " === String($execution.id); } catch (e) { return false; } })() || ")
RECITE_NEW = ("(() => { try { return $getWorkflowStaticData('global').menu_exec"
              " === String($execution.id); } catch (e) { return false; } })() || "
              "['קריאת שירות', 'קריאה קיימת', 'יתרה', 'נציג']"
              ".filter(w => t.indexOf(w) !== -1).length >= 3 || ")


def clear_spot(nodes, x, y):
    """Nudge y down until the position overlaps nothing (dx<200 AND dy<100)."""
    while any(abs(n["position"][0] - x) < 200 and abs(n["position"][1] - y) < 100
              for n in nodes):
        y += 128
    return [x, y]


def main():
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    for need in ("Send", "Answer the resident", "get_request_status"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    W.check_memory_epoch(tools=W.tools_text())
    changes = []
    want_desc = W.tool("show_menu")["description"]

    # 1. The tool node.
    if "show_menu" not in by:
        anchor = by["get_request_status"]["position"]
        pos = clear_spot(live["nodes"], anchor[0], anchor[1] + 128)
        live["nodes"].append({
            "id": "showMenuJudgment1",
            "name": "show_menu",
            "type": "@n8n/n8n-nodes-langchain.toolCode",
            "typeVersion": 1.1,
            "position": pos,
            "parameters": {
                "name": "show_menu",
                "description": want_desc,
                "language": "javaScript",
                "jsCode": TOOL_CODE,
            },
        })
        changes.append("show_menu: new Code tool at %s" % pos)
    else:
        p = by["show_menu"]["parameters"]
        if p.get("description") != want_desc:
            p["description"] = want_desc
            changes.append("show_menu: description synced from n8n_whatsapp.py")
        if p.get("jsCode") != TOOL_CODE:
            p["jsCode"] = TOOL_CODE
            changes.append("show_menu: code synced")

    conns = live["connections"]
    if "show_menu" not in conns:
        conns["show_menu"] = {"ai_tool": [[
            {"node": "Answer the resident", "type": "ai_tool", "index": 0}]]}
        changes.append("show_menu: wired to the agent (ai_tool)")

    # 2 + 3. Send.
    body = by["Send"]["parameters"].get("jsonBody") or ""
# `done` marks an edit as already applied. It differs from `new` for the
    # COND edit because the recite edit rewrites part of COND_NEW's text: on an
    # up-to-date Send, COND_NEW is no longer contiguous, but the menu_exec
    # clause (RECITE_OLD, a substring of both states) still is.
    for old, new, done, label in (
            (COND_OLD, COND_NEW, RECITE_OLD,
             "Send: the menu_exec flag joins the menu condition"),
            (ITEMS_OLD, ITEMS_NEW, ITEMS_NEW,
             "Send: the balance row joins the attached list"),
            (RECITE_OLD, RECITE_NEW, RECITE_NEW,
             "Send: a reply reciting 3+ of the four flows carries the rows")):
        if done in body:
            continue
        if old not in body:
            sys.exit("Anchor missing on live Send.jsonBody -- refusing to "
                     "guess:\n  %s" % label)
        body = body.replace(old, new, 1)
        changes.append(label)
    by["Send"]["parameters"]["jsonBody"] = body

    print("workflow : %s  (%s, active=%s)"
          % (live["name"], live["id"], live.get("active")))
    if not changes:
        print("")
        print("Nothing to do. Live already matches.")
        return

    print("")
    print("changes:")
    for c in changes:
        print("  - %s" % c)

    if not apply:
        print("")
        print("Dry run. Re-run with --apply to write it.")
        return

    # PUT takes only these four keys; sending id/active/tags back is a 400.
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": live["nodes"],
        "connections": live["connections"], "settings": live.get("settings", {}),
    })
    print("")
    print("written. Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
