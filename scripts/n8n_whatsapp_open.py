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
# 1b. The phantom-ticket guard, which was missing by one letter.
#
# `Reply usable?` is supposed to catch the bot claiming a ticket it never
# opened, and send the resident to a person instead of to a number that does
# not exist. On 1 Sep it wrote `פתחתי קריאת שירות` -- the construct form
# קריאת, not קריאה -- called no tool at all, and the guard let it through. The
# resident was told their fault was logged and nothing was.
#
# Still verb-first only: a status reply says `הקריאה נפתחה ב־26.8`, noun then
# verb, and matching that order would kill correct status answers.
# --------------------------------------------------------------------------
CLAIMS_OLD = "/פתחתי קריאה|נפתחה קריאה|פתחנו קריאה/"
CLAIMS_NEW = "/(פתחתי|פתחנו|נפתחה|נפתחו)( (לך|לכם|לכן|כבר|את))* ?ה?קריא[הת]/"

# And the check itself, which live still does with `isExecuted`. n8n_whatsapp.py
# stopped trusting that on 19 Aug -- it reports true for a tool node that was
# never invoked, describing reachability rather than execution -- and moved to
# asking for the node's OUTPUT, which a tool the agent never called does not
# have. The script was fixed; live never received it, so the guard has been
# passing every phantom claim through since.
# Both ways of asking the tool node whether it ran are wrong, and each was live
# for part of 1 Sep. `isExecuted` is spuriously true, so the guard never fired.
# `.all()` throws from inside this If, so it fired on EVERY ticket confirmation
# and replaced correct answers with the canned line in `Hand over instead`.
# The reply carries the honest signal: a reference exists only because
# open_request returned one, and ours have a fixed shape.
EXEC_OLDS = [
    "try { return $('open_request').isExecuted === true; } catch (e) { return false; }",
    ("try { const r = $('open_request').all();"
     " return Array.isArray(r) && r.length > 0;"
     " } catch (e) { return false; }"),
]
EXEC_NEW = r" return /\b\d{3}-\d{3,6}-\d{2}\b/.test(t);"

# The old second clause treated "a reference plus פתחתי" as a claim, which the
# shape test now decides on its own -- and it accepted the HM form, which is
# exactly the shape the model invented on 1 Sep.
SECOND_OLD = (r" || ((/\b\d{3}-\d{3,6}-\d{2}\b|\bHM-\d{4}-\d{3,6}\b/.test(t))"
              " && /פתחתי|פתחנו/.test(t))")

# --------------------------------------------------------------------------
# 2. The agent node's injected prompt.
#
# THIS FILE NO LONGER OWNS IT. It reduced the template from 1,473 characters to
# 406 on 31 Aug, and that is the change recorded here; on 1 Sep
# `n8n_whatsapp_untemplate.py` grew it again to carry `tap_now` and
# `attachment`, because the canned tap reply and the canned attachment reply
# both became the model's job and it has to be told which is which.
#
# Keeping a second copy here meant this script silently REVERTED that one the
# next time it ran -- caught on the same day, by running both. One field, one
# owner: the same rule that settled the tool descriptions on 31 Aug.
AGENT_NEW = None

def main():
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    for need in ("Sort", "Answer the resident", "transfer_to_human"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    # This file syncs three of the five tool descriptions, so it asserts the
    # tools epoch: a description change poisons buffers the way a prompt change
    # does, and on 1 Sep the get_balance interrogation proved it.
    W.check_memory_epoch(tools=W.tools_text())

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

    # 1b. The phantom-ticket guard
    guard = by.get("Reply usable?")
    if guard is not None:
        conds = guard["parameters"]["conditions"]["conditions"]
        for c in conds:
            if c.get("id") != "phantom":
                continue
            lv = str(c.get("leftValue", ""))
            if CLAIMS_OLD in lv:
                lv = lv.replace(CLAIMS_OLD, CLAIMS_NEW, 1)
                changes.append("Reply usable?: widen the phantom-ticket regex "
                               "(it missed קריאת and let a fake ticket through)")
            if SECOND_OLD in lv:
                lv = lv.replace(SECOND_OLD, "", 1)
                changes.append("Reply usable?: drop the second claims clause, "
                               "which accepted the invented HM reference shape")
            for old in EXEC_OLDS:
                if old in lv:
                    lv = lv.replace(old, EXEC_NEW.strip(), 1)
                    changes.append("Reply usable?: decide on the reference shape "
                                   "in the reply, not on asking the tool node")
                    break
            c["leftValue"] = lv

    # 2. Agent template -- owned by n8n_whatsapp_untemplate.py since 1 Sep.
    #    See the note on AGENT_NEW above: writing it from here as well reverted
    #    that script's version every time this one ran.

    # 3 & 4. The two tool descriptions that carry behaviour, taken from the
    #        script rather than copied here. With the prompt stripped these are
    #        most of what the model has to go on, so they are worth keeping in
    #        one place -- and n8n_whatsapp.py is that place again now that the
    #        two have been reconciled.
    # No example reference number anywhere the model can read one. The prompt
    # has had none since 20 Aug, when the bot minted one digit by digit out of
    # an example written in the file; two survived in this tool's text, and on
    # 1 Sep a probe quoted 255-1013-26 -- the example -- for a brand-new ticket.
    ref = by.get("get_request_status")
    if ref is not None:
        jb = ref["parameters"].get("jsonBody") or ""
        old_ref = ("exactly as written — 255-1013-26, an old HM-2026-1013, or "
                   "just the serial.")
        new_ref = ("exactly as written, whether that is the whole reference, an "
                   "older HM-prefixed one, or just the serial.")
        if old_ref in jb:
            ref["parameters"]["jsonBody"] = jb.replace(old_ref, new_ref, 1)
            changes.append("get_request_status: drop the example reference "
                           "number from the parameter doc")

    for name, why in (("transfer_to_human",
                       "a person in a bad state, call it first, and only once"),
                      ("open_request",
                       "gather details in a sentence, not as a form"),
                      ("get_request_status",
                       "no example reference number to copy")):
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
