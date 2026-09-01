# -*- coding: utf-8 -*-
"""The menu learns English small talk, an echo becomes the intro, and
get_balance stops interrogating.

    python scripts/n8n_whatsapp_greet.py            # dry run
    python scripts/n8n_whatsapp_greet.py --apply    # write it

WHY — the owner's 20:21 transcript, in his words: "it did not even trigger the
menu also it sound robotic."

1. `wassap` and `whats up` never got the menu. The GREETING list in `Sort`
   holds Hebrew plus textbook English (hi, hello, good morning); no slang. All
   three of his openers fell through to the model, which clarified the same
   way three times, in the singular. A greeting the workflow recognises never
   reaches the model at all, which is also the cheapest fix for the register.
2. `hi is this homies support?` got the verbatim intro sentence back — the
   model reciting the opener check_greeting pins into the prompt — WITHOUT the
   menu, because Send attaches it only on `greeted !== true` and his handset
   has been greeted-true since August. So: when a reply contains the canonical
   sentence verbatim, it IS the intro, and the menu rides along regardless of
   `greeted`. The ownership clause (epoch 7) makes echoes rarer; this makes a
   surviving one indistinguishable from the intended thing.
3. Three rounds of "עבור דירה מסוימת, או באופן כללי?", capped with
   "המערכת דורשת שאציין" — an invented requirement, blamed on a system, before
   any tool had run. The cause is the `unit` parameter doc in get_balance's
   live jsonBody: "Apartment number, only if they asked about one specific
   apartment. Empty otherwise." — an OPTIONAL field documented as a condition,
   which the model resolved by interrogating. THE SCHEMA IS A PROMPT TOO: an
   optional field must say what to do in the normal case, or the model will
   ask the resident to fill it.

The description text comes from W.tool('get_balance') — n8n_whatsapp.py is the
source of truth, this file only syncs, same as the other tool patchers. The
`unit` doc exists only in the live jsonBody (the builder's is the pre-Chatwoot
shape, stale by design since the Sort divergence), so that one is a surgical
string edit here.

Idempotent. Running it twice reports nothing to do.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"

# --------------------------------------------------------------------------
# 1. The greeting list. Anchored ^...$ on `bare` (emoji and trailing
#    punctuation stripped, lowercased), so a greeting WITH content still goes
#    to the model — "hi is this homies support?" is a question, not a hello.
# --------------------------------------------------------------------------
GREET_OLD = (
    "'ערב טוב|לילה טוב|hi|hii|hey|hello|yo|good morning|good afternoon|good evening|' +\n"
    "  'shalom|ahlan)$', 'u');"
)
GREET_NEW = (
    "'ערב טוב|לילה טוב|hi|hii|hey|hello|yo|good morning|good afternoon|good evening|' +\n"
    "  // English small talk, 1 Sep: wassap and whats up reached the model and\n"
    "  // were clarified at, three times, in the singular. A hello is a hello.\n"
    "  'whats up|what\\u0027s up|whatsup|wassup|wassap|wazzup|sup|' +\n"
    "  'hi there|hey there|hello there|howdy|' +\n"
    "  'shalom|ahlan)$', 'u');"
)

# --------------------------------------------------------------------------
# 2. Send: a verbatim intro echo carries the menu, greeted or not.
# --------------------------------------------------------------------------
SEND_OLD = ("if ($('Sort').first().json.greeting || "
            "(/מיכאל מהומיז/.test(t) && $('Sort').first().json.greeted !== true))")
SEND_NEW = ("if ($('Sort').first().json.greeting || "
            "t.indexOf('היי, כאן מיכאל מהומיז. במה אפשר לעזור?') !== -1 || "
            "(/מיכאל מהומיז/.test(t) && $('Sort').first().json.greeted !== true))")

# --------------------------------------------------------------------------
# 3. get_balance's unit doc: the normal case first, and never a question.
# --------------------------------------------------------------------------
UNIT_OLD = ("$fromAI('unit', \"Apartment number, only if they asked about one "
            "specific apartment. Empty otherwise.\", 'string')")
UNIT_NEW = ("$fromAI('unit', \"Almost always empty: the lookup finds the "
            "resident's own apartment by itself. Fill it only when the "
            "resident has already named a specific apartment on their own. "
            "NEVER ask which apartment or whether they mean a specific one — "
            "call without it.\", 'string')")


def main():
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    for need in ("Sort", "Send", "get_balance"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    W.check_memory_epoch(tools=W.tools_text())
    changes = []

    def edit(node, field, old, new, label):
        val = by[node]["parameters"].get(field) or ""
        if new in val and old not in val:
            return
        if old not in val:
            sys.exit("Anchor missing on live %r.%s -- refusing to guess:\n  %s"
                     % (node, field, label))
        by[node]["parameters"][field] = val.replace(old, new, 1)
        changes.append(label)

    edit("Sort", "jsCode", GREET_OLD, GREET_NEW,
         "Sort: the greeting list learns English small talk")
    edit("Send", "jsonBody", SEND_OLD, SEND_NEW,
         "Send: a verbatim intro echo carries the menu, greeted or not")
    edit("get_balance", "jsonBody", UNIT_OLD, UNIT_NEW,
         "get_balance: the unit doc states the normal case and bans the question")

    want = W.tool("get_balance")["description"]
    if by["get_balance"]["parameters"].get("toolDescription") != want:
        before = len(by["get_balance"]["parameters"].get("toolDescription") or "")
        by["get_balance"]["parameters"]["toolDescription"] = want
        changes.append("get_balance: description %d -> %d chars (the lookup "
                       "finds the apartment itself; ask in your own words)"
                       % (before, len(want)))

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
