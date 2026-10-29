# -*- coding: utf-8 -*-
"""The word before an answer is a professional one, and money is told as what our system shows
(29 Oct 2026, evening, epoch 87).

    python scripts/n8n_whatsapp_gladly.py              # dry run
    python scripts/n8n_whatsapp_gladly.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_gladly.py --apply      # write it
    python scripts/n8n_whatsapp_gladly.py --restore    # put the snapshot back

WHY. The owner's chat on the live bot, 18:48 UTC (execution 138878): "I need to check if I have a
balance left" got "אוקיי, יש לך יתרה פתוחה של 2,000 ש"ח על החודשים ינואר עד אוגוסט 2026 …". The
owner: "so this is a bit unprofessional so its like. gladly to do so. or gotcha, based on the system
you still have ...".

WHERE IT CAME FROM. "אוקיי" is the first of the three words the prompt quotes for the short word
before an answer ("אוקיי", "אין בעיה", "אוי, לא נעים"), and a quoted word is said back: on 23 Sep a
cold "בטח" was the same list's first item. The money rule made the record the bot's evidence ("ואתה
עונה לפיו"), but nothing had it say so, so the amount came as a bare fact.

WHAT CHANGES, two edits of the prompt, nothing else:
  - the quoted "אוקיי" becomes the owner's "בשמחה"; the list stays three words, and its own rule
    ("ולא אותה מילה פעמיים בשיחה") keeps it from repeating;
  - the money rule's "ואתה עונה לפיו" goes on "ואומר לו שזה מה שרשום אצלנו במערכת".
Plus the memory: epoch 86 -> 87, because the owner's buffer holds the "אוקיי" reply.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py, as n8n_whatsapp_ionly.py did.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 87
OLD_KEY = "={{ $json.to }}-86"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-29oct-before-gladly.json")

GLADLY_EDITS = [
    ('"אוקיי", "אין בעיה", "אוי, לא נעים" — ואז השאלה', '"בשמחה", "אין בעיה", "אוי, לא נעים" — ואז השאלה'),
    ("- **חיובים:** בכל עניין של כסף, מה שרשום במערכת הוא הראיה שלך, ואתה עונה לפיו.",
     "- **חיובים:** בכל עניין של כסף, מה שרשום במערכת הוא הראיה שלך, ואתה עונה לפיו ואומר לו שזה מה שרשום "
     "אצלנו במערכת."),
]


def gladly(wf):
    """The workflow with both edits; each anchor must occur exactly once. Does not touch memory."""
    import copy
    out = copy.deepcopy(wf)
    opts = {n["name"]: n for n in out["nodes"]}["Answer the resident"]["parameters"]["options"]
    sm = opts["systemMessage"]
    for old, new in GLADLY_EDITS:
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
    if key == NEW_KEY and GLADLY_EDITS[0][1] in prompt_of(live):
        print("Nothing to do. Live already says בשמחה, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 86's. Read live first." % key)

    new = gladly(live)
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
