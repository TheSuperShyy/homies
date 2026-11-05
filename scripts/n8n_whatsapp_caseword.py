# -*- coding: utf-8 -*-
"""Each opening word sits with its own case: a fault gets care, never gladness (5 Nov 2026, epoch 94).

    python scripts/n8n_whatsapp_caseword.py              # dry run
    python scripts/n8n_whatsapp_caseword.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_caseword.py --apply      # write it
    python scripts/n8n_whatsapp_caseword.py --restore    # put the snapshot back

WHY. The owner's test on the UChat number (execution 155838): "המעלית בבניין
לא עובדת, היא תקועה בקומה 3" got "בשמחה אסף. פתחתי קריאה על המעלית …". The
owner pasted it back: "this is the reply".

WHERE IT CAME FROM. The paragraph on the word before the answer already says,
case by case, what that word is: a short caring reaction for a fault,
willingness for a request to check something. It then quotes three words in a
row, "בשמחה", "כמובן", "אוי, לא נעים", and the first is said back whatever the
case, as "אוקיי" was until 29 Oct (n8n_whatsapp_gladly.py).

WHAT CHANGES, the same words moved, nothing added:
  - the fault case gets its example, "אוי, לא נעים";
  - the check case gets the owner's "בשמחה" or "כמובן";
  - the loose list after "ומשם ישר לעניין" goes.
Plus the memory: epoch 93 -> 94, because the owner's buffer holds the reply.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py, then
n8n_uchat.py --apply carries it to the UChat copy, the bot in use.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 94
OLD_KEY = "={{ $json.to }}-93"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-05nov-before-caseword.json")

CASE_EDITS = [
    ("למי שסיפר על תקלה, תגובה קצרה ואכפתית של בן אדם לדבר עצמו,",
     'למי שסיפר על תקלה, תגובה קצרה ואכפתית של בן אדם לדבר עצמו, כמו "אוי, לא נעים",'),
    ("למי שביקש שתבדוק לו משהו, יתרה, מצב של קריאה או מה כלול בתשלום, נכונות לבדוק,",
     'למי שביקש שתבדוק לו משהו, יתרה, מצב של קריאה או מה כלול בתשלום, נכונות לבדוק, כמו "בשמחה" או "כמובן",'),
    ('ומשם ישר לעניין. "בשמחה", "כמובן", "אוי, לא נעים" — ואז השאלה, או מה שהכלי החזיר.',
     "ומשם ישר לעניין: השאלה, או מה שהכלי החזיר."),
]


def caseword(wf):
    """The workflow with the three edits; each anchor must occur exactly once. Does not touch memory."""
    import copy
    out = copy.deepcopy(wf)
    opts = {n["name"]: n for n in out["nodes"]}["Answer the resident"]["parameters"]["options"]
    sm = opts["systemMessage"]
    for old, new in CASE_EDITS:
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
    if key == NEW_KEY and CASE_EDITS[2][1] in prompt_of(live):
        print("Nothing to do. Live already has each word with its case, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 93's. Read live first." % key)

    new = caseword(live)
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
