# -*- coding: utf-8 -*-
"""An urgent ticket is said as urgent, never as "emergency" (5 Nov 2026, epoch 93).

    python scripts/n8n_whatsapp_urgentword.py              # dry run
    python scripts/n8n_whatsapp_urgentword.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_urgentword.py --apply      # write it
    python scripts/n8n_whatsapp_urgentword.py --restore    # put the snapshot back

WHY. The owner's test on the UChat number, 10:39-10:41 UTC (execution 155798):
"המעלית בבניין לא עובדת, היא תקועה בקומה 3", then "yes" to "is someone stuck
inside?". The bot called notify_team (reason emergency) and add_request_detail,
and replied "עדכנתי מיד בדחיפות חירום שיש מישהו שתקוע במעלית. מספר הקריאה
הדחופה שלך הוא 255-1391-26, וזה הדבר היחיד שאני יכול לעשות מכאן." The owner:
"look at the reply it got broke why it will notify emergency services?" and
"so fix that i dont like the reply of that one".

WHERE IT CAME FROM. Both phrases are the prompt's own, said back:
  - "קריאת שירות בדחיפות חירום ורושם הערת חירום" gave "עדכנתי מיד בדחיפות
    חירום", which, with no one named, reads as an emergency service alerted;
  - "ושזה הדבר היחיד שאתה יכול לעשות מכאן", meant for a resident who presses
    for more, was recited on the first turn.
The tools define their own values ("emergency = a person in danger" in
notify_team), so the word is not needed for the tool choice.

WHAT CHANGES, two edits of the prompt, nothing else:
  - "בדחיפות חירום ורושם הערת חירום" becomes "דחופה ורושם הערה דחופה";
  - the pressing case says what was done and the ticket's number, without the
    quoted "only thing I can do" line.
Plus the memory: epoch 92 -> 93, because the owner's buffer holds the reply.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py, as
n8n_whatsapp_gladly.py did. Then n8n_uchat.py --apply carries it to the UChat
copy, which is the bot in use.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 93
OLD_KEY = "={{ $json.to }}-92"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-05nov-before-urgentword.json")

URGENT_EDITS = [
    ("אתה פותח מיד קריאת שירות בדחיפות חירום ורושם הערת חירום",
     "אתה פותח מיד קריאת שירות דחופה ורושם הערה דחופה"),
    ("שפתחת לו קריאה דחופה, עם המספר שלה, ושזה הדבר היחיד שאתה יכול לעשות מכאן, ולא מוסיף שאלה",
     "מה עשית ומה המספר של הקריאה, ולא מוסיף שאלה"),
]


def urgentword(wf):
    """The workflow with both edits; each anchor must occur exactly once. Does not touch memory."""
    import copy
    out = copy.deepcopy(wf)
    opts = {n["name"]: n for n in out["nodes"]}["Answer the resident"]["parameters"]["options"]
    sm = opts["systemMessage"]
    for old, new in URGENT_EDITS:
        sm = once(sm, old, new)
    opts["systemMessage"] = sm
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and URGENT_EDITS[0][1] in prompt_of(live):
        print("Nothing to do. Live already says the urgent ticket plainly, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 92's. Read live first." % key)

    new = urgentword(live)
    nb = {n["name"]: n for n in new["nodes"]}
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("tools    : %s (unchanged: %s)" % (W.epoch_hash(tools_of(new)), tools_of(new) == tools_of(live)))
    print("memory   : %s -> %s (every buffer starts fresh)" % (OLD_KEY, NEW_KEY))
    print("changed  : %s" % ", ".join(n["name"] for n in new["nodes"] if n != by[n["name"]]))

    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        NP.dump(new["nodes"], new["connections"], path)
        print("dumped   : %s (the would-be workflow, secret replaced)" % path)
    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    if snapshot(live, SNAPSHOT):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": new["nodes"], "connections": new["connections"],
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    bb = {n["name"]: n for n in back["nodes"]}
    print("\nwritten  : %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  prompt %s (want %s); memory key %s" % (W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)),
                                                     bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
