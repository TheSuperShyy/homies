# -*- coding: utf-8 -*-
"""Remove the templating that does not live in prompt.md.

    python scripts/n8n_whatsapp_open.py            # dry run
    python scripts/n8n_whatsapp_open.py --apply     # write it

WHY
Stripping the system prompt to two restrictions on 31 Aug removed 63,800
characters of scripted behaviour and did not remove the scripts, because
`prompt.md` was never the only prompt. Three other places hold canned Hebrew,
and all three reach the resident:

1. **The agent node's own message template.** It injects a second prompt on
   every single message -- greeting choreography, and for a tap on "open a
   ticket" the whole offer script down to
   `ובאותה הודעה שאלת הבניין והדירה, והיא נגמרת בסימן השאלה שלה`. That is the
   building-and-apartment question the owner was shown as an example of
   templating, and it is not in prompt.md at all.
2. **The Sort node's canned tap replies.** Three fixed variants per menu row,
   sent without the model ever seeing the tap. The 21:25 message in the owner's
   screenshot was one of these.
3. **`transfer_to_human`'s description**, which is the opposite problem: it is
   too vague, and with the prompt's emergency protocol gone the measured
   behaviour was **0 transfers in 6 runs** for someone trapped in a lift or
   reporting gas. The owner's instruction was to put this in the tool rather
   than back in the prompt, which is also the safer place for it: tool
   descriptions are English and the bot answers in Hebrew, so there is nothing
   in them for it to recite.

WHAT STAYS, DELIBERATELY
The options list on a bare greeting, and the canned line for `לדבר עם נציג`.
That tap is routing, not conversation: `Human tap?` -> `Transfer the tap` hangs
off the *canned* branch of `Canned reply?`, so sending it to the model instead
would stop the transfer firing. Moving it is a separate job with its own
rewiring.

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
# 1. Sort: only the נציג tap is answered by the workflow now.
# --------------------------------------------------------------------------
TAP_OLD = '''  "פתיחת קריאת שירות": [
    "אפשר לספר לי מה קרה, ואני אפתח על זה קריאה לצוות?",
    "אפשר לתאר בפירוט מה מפריע, כדי שהקריאה שאפתח תגיע לצוות מדויקת?",
    "כדי שאפתח קריאה לצוות, אפשר לתאר מה בדיוק קרה?",
  ],
  "מצב קריאה קיימת": [
    "אבדוק את זה מיד. יש לך את מספר הקריאה?",
    "אפשר לבדוק לפי כתובת או לפי מספר. יש לך את מספר הקריאה?",
    "בודק בשבילך. מה מספר הקריאה?",
  ],
'''
TAP_NEW = '''  // The "open a ticket" and "status" rows had three canned variants each until
  // 31 Aug. They are gone on the owner's instruction -- a tap now reaches the
  // model, which answers it in its own words, and the tap itself is in the
  // conversation memory so the next message does not need a flag to know it
  // happened.
'''

LOOKUP_OLD = "const tapOpts = TAPPED[text.trim()];"
LOOKUP_NEW = ("const tapOpts = TAP_KIND[text.trim()] === 'human'\n"
              "  ? TAPPED[text.trim()] : null;")

# --------------------------------------------------------------------------
# 2. The agent node's injected prompt, reduced to what the model cannot know.
#
# `last_bot` is the one that genuinely matters: the workflow sometimes speaks
# for the bot, and those lines are not in its memory, so without this it
# answers a question it cannot see.
# --------------------------------------------------------------------------
AGENT_NEW = (
    "={{ ($json.greeted ? '[אתם כבר באמצע שיחה.]' "
    ": '[זו ההודעה הראשונה בשיחה.]') "
    "+ ($json.tapped_human ? ' [המערכת כבר הודיעה לדייר שהיא מעבירה לצוות "
    "ושאלה על מה הפנייה. ההודעה הזאת היא התשובה שלו, והיא נועדה לצוות "
    "שיחזור אליו.]' : '') "
    "+ ($json.last_bot ? ' [ההודעה הזאת היא תשובה למשפט ששלחה המערכת ולא "
    "אתה, ולכן אין לו זכר בזיכרון שלך: ' + $json.last_bot + ']' : '') "
    "+ String.fromCharCode(10) + $json.text }}"
)

def main():
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    for need in ("Sort", "Answer the resident", "transfer_to_human"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    changes = []

    # 1. Sort
    sort = by["Sort"]
    code = sort["parameters"]["jsCode"]
    if TAP_OLD in code:
        code = code.replace(TAP_OLD, TAP_NEW, 1)
        changes.append("Sort: drop the 6 canned tap replies for open/status")
    if LOOKUP_OLD in code:
        code = code.replace(LOOKUP_OLD, LOOKUP_NEW, 1)
        changes.append("Sort: only the נציג tap is canned; the rest reach the model")
    sort["parameters"]["jsCode"] = code

    # 2. Agent template
    agent = by["Answer the resident"]
    if agent["parameters"].get("text") != AGENT_NEW:
        before = len(agent["parameters"].get("text") or "")
        changes.append("Answer the resident: injected prompt %d -> %d chars "
                       "(drops the greeting and offer choreography)"
                       % (before, len(AGENT_NEW)))
        agent["parameters"]["text"] = AGENT_NEW

    # 3 & 4. The two tool descriptions that carry behaviour, taken from the
    #        script rather than copied here. With the prompt stripped these are
    #        most of what the model has to go on, so they are worth keeping in
    #        one place -- and n8n_whatsapp.py is that place again now that the
    #        two have been reconciled.
    for name, why in (("transfer_to_human",
                       "a person in a bad state, call it first, and only once"),
                      ("open_request",
                       "gather details in a sentence, not as a form")):
        node = by[name]
        want = W.tool(name)["description"]
        if node["parameters"].get("toolDescription") != want:
            before = len(node["parameters"].get("toolDescription") or "")
            changes.append("%s: description %d -> %d chars (%s)"
                           % (name, before, len(want), why))
            node["parameters"]["toolDescription"] = want

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
