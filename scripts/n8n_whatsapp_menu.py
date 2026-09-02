# -*- coding: utf-8 -*-
"""A lost resident gets shown the options — decided by the model, not a keyword.

    python scripts/n8n_whatsapp_menu.py            # dry run
    python scripts/n8n_whatsapp_menu.py --apply    # write it

WHY — the owner's 2 Sep screenshots, in order: "idk" got a warm sign-off and
a dead thread; then, after the tool existed, "ok" got "הנה האפשרויות" with
nothing under it. His constraints, verbatim: "i dont want a strict rule for
keywords i want it to be general" and "i dont want any templated message".
His diagnosis, also verbatim: "a layer rule is lying" — and one was.

THE SIGNAL, third attempt, the one that is both live-proven and text-free:
`returnIntermediateSteps` on the agent node puts the tool calls into the
agent's own MAIN-CHAIN output item, and Send reads them through
$('Answer the resident') — the exact channel the promise guard exercises on
every run. Two earlier relays died in Send's expression sandbox and their
try/catch hid it (execs 22878, 22940, 22947: show_menu ran, success string
returned, content_type=text posted):

  1. staticData is a Code-node facility; expressions do not have it.
  2. $('show_menu') has no main output an expression can read — ai_tool
     nodes emit on the ai_tool channel.

Layers, after the audit (all pointing one direction now):
  - prompt: someone lost has not finished; show the list, don't enumerate.
  - description: judgment carrier — when to call, mid-matter tie-breaker
    (stuck after a clarify = show the choices), never announce or ask
    permission, not twice in a row.
  - tool return: truthful — the buttons appear under your next message.
  - Send: greeting || tool-called (intermediateSteps) || recital net (a
    reply naming 3+ flows in the model's OWN words gets the buttons too,
    the backstop for runs where the model recites instead of calling) ||
    verbatim-intro-echo. The model's text is 100% its own on every path.

Also owned here, from the same audit: open_request's `reporter_unit` doc
stops demanding the flat "every time" — it fought get_request_status's
DO-NOT-ASK-FOR-AN-APARTMENT rule on every lobby and lift fault.

The list is THREE rows — a WhatsApp rendering fact (3 reply buttons inline;
a 4th collapses everything into an English "Choose an item" list button; it
happened to the owner's greeting on 2 Sep and was reverted the same day).

Idempotent. This file patches the CURRENT live state to the end state and
recognizes the end state; it does not rebuild from scratch — that recovery
path is git history.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"

TOOL_CODE = """\
// This call is read by Send out of the agent's own output
// (returnIntermediateSteps) - nothing in here signals anything. Do not put
// a staticData write or an $execution read back: both died in Send's
// expression sandbox (execs 22878, 22940, 22947) and the try/catch around
// them hid it while the bot told residents the options were coming.
return 'שלושת הכפתורים יופיעו מתחת להודעה הבאה שלך. כתוב משפט קצר משלך, בלי למנות את האפשרויות ובלי להכריז שהן בדרך - הן כבר שם.';
"""

# The two dead relays, contiguous on the pre-fix live body, replaced by the
# intermediateSteps read.
DEAD = ("(() => { try { return $('show_menu').all().length > 0; }"
        " catch (e) { return false; } })() || "
        "(() => { try { return $getWorkflowStaticData('global').menu_exec"
        " === String($execution.id); } catch (e) { return false; } })() || ")
STEPS = ("(() => { try { return ($('Answer the resident').first().json"
         ".intermediateSteps || []).some(s => ((s.action || {}).tool) === "
         "'show_menu'); } catch (e) { return false; } })() || ")

# The recital-net backstop and the three-row list: asserted present, never
# rebuilt from here.
FILTER = ("['קריאת שירות', 'קריאה קיימת', 'יתרה', 'נציג']"
          ".filter(w => t.indexOf(w) !== -1).length >= 3 || ")
ITEMS_3 = ("{ title: 'מצב קריאה קיימת', value: 'status' }, "
           "{ title: 'לדבר עם נציג', value: 'human' }")
ITEMS_4 = ("{ title: 'מצב קריאה קיימת', value: 'status' }, "
           "{ title: 'יתרה ותשלומים', value: 'balance' }, "
           "{ title: 'לדבר עם נציג', value: 'human' }")

# open_request.reporter_unit: keep the send-when-known policy, kill the
# ask-pressure that fought the other two tools' unit rules (layer audit,
# 2 Sep). Lives only in the live jsonBody; param docs are not epoch-hashed.
UNIT_OLD = ("The apartment the person reporting LIVES in. Send this every "
            "time, including for a fault in the lobby or the lift.")
UNIT_NEW = ("The apartment the person reporting LIVES in. Send it whenever "
            "you know it - for a fault inside their flat the flow gives it "
            "to you. For a fault in a lobby, lift or any common area, "
            "include it only if they volunteered it, and never ask an extra "
            "question just to fill this field.")


def main():
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    for need in ("Send", "Answer the resident", "show_menu", "open_request"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    W.check_memory_epoch(tools=W.tools_text())
    changes = []

    # 1. The agent surfaces its tool calls on the main chain.
    opts = by["Answer the resident"]["parameters"].setdefault("options", {})
    if opts.get("returnIntermediateSteps") is not True:
        opts["returnIntermediateSteps"] = True
        changes.append("agent: returnIntermediateSteps on (the signal rides "
                       "the agent's own output)")

    # 2. The tool: judgment carrier, truthful return, no relay machinery.
    p = by["show_menu"]["parameters"]
    want_desc = W.tool("show_menu")["description"]
    if p.get("description") != want_desc:
        p["description"] = want_desc
        changes.append("show_menu: description synced from n8n_whatsapp.py")
    if p.get("jsCode") != TOOL_CODE:
        p["jsCode"] = TOOL_CODE
        changes.append("show_menu: relay machinery out, truthful return in")

    # 3. Other descriptions changed by the 2 Sep layer audit.
    for name in ("get_balance", "transfer_to_human"):
        want = W.tool(name)["description"]
        if by[name]["parameters"].get("toolDescription") != want:
            by[name]["parameters"]["toolDescription"] = want
            changes.append("%s: description synced (layer audit)" % name)

    # 4. Send: swap the dead relays for the intermediateSteps read.
    body = by["Send"]["parameters"].get("jsonBody") or ""
    if STEPS not in body:
        if DEAD not in body:
            sys.exit("Neither the dead relays nor the intermediateSteps read "
                     "is on live Send.jsonBody -- refusing to guess.")
        body = body.replace(DEAD, STEPS, 1)
        changes.append("Send: signal = the agent's intermediateSteps; both "
                       "dead relays removed")
    for must, label in ((FILTER, "recital net"), (ITEMS_3, "three-row list")):
        if must not in body:
            sys.exit("Live Send.jsonBody lost the %s -- refusing to guess." % label)
    if ITEMS_4 in body:
        body = body.replace(ITEMS_4, ITEMS_3, 1)
        changes.append("Send: the balance row comes back out (4 rows "
                       "collapse WhatsApp's buttons)")
    by["Send"]["parameters"]["jsonBody"] = body

    # 5. open_request's reporter_unit doc.
    ob = by["open_request"]["parameters"].get("jsonBody") or ""
    if UNIT_NEW not in ob:
        if UNIT_OLD not in ob:
            sys.exit("reporter_unit anchor missing on live open_request -- "
                     "refusing to guess.")
        by["open_request"]["parameters"]["jsonBody"] = ob.replace(UNIT_OLD, UNIT_NEW, 1)
        changes.append("open_request: reporter_unit stops demanding the flat "
                       "on common-area faults")

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
