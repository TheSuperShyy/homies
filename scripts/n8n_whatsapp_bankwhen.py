# -*- coding: utf-8 -*-
"""A bank transfer gets no "checking" note, and "when?" gets a plain answer, not the hand-over again (18 Nov; epoch 113).

    python scripts/n8n_whatsapp_bankwhen.py              # dry run
    python scripts/n8n_whatsapp_bankwhen.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_bankwhen.py --apply      # write it
    python scripts/n8n_whatsapp_bankwhen.py --restore    # put the snapshot back

WHY. The owner's second Grok run (epoch 112, 18 Nov 11:32-11:41 UTC, conversation 96) checked against the runs:
  - Every hand-over was called with bank_transfer and every note went to Collections (190591; 190608 skipped as a
    repeat; 190640 after the label had gone).
  - The payment-ack model's note went out first on each transfer ask ("הבנתי, אני בודק את זה ממש עכשיו כדי להעביר
    לך את פרטי התשלום המדויקים", "אני כבר בודק את זה ומארגן לך את כל מה שצריך כדי לשלם"). It promises what Michael
    does not do, and B1.1's real answer then took 67 s (4,562 tokens of thinking), so Grok read the note as the reply,
    moved on, and saw the hand-over twice under B1.2.
  - "ומתי זה יגיע?" got the hand-over sentence again (190588), because epoch 112 said to call it every time they ask
    for it, and a "when" read as an ask. A "when" asked later would also ping Collections again.

WHAT CHANGES, in one write:
  A word first?   ackhold v1: the payment-ack note is held when the tenant's words name a bank transfer or the
                  account details. The hand-over is the answer; the typing indicator covers the wait.
  notify_team     a new call for every ask to pay by transfer or for the details (as epoch 112); asked only when,
                  no new call and no new hand-over sentence: no time for it, and a representative from collections
                  will send the details here.
  Memory          epoch 112 -> 113.
Not changed: the prompt, the other tools, Send, Reply usable?, Team note this turn?, Let the team know.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402
from n8n_whatsapp_bankagain import TRANSFER_WORDS  # noqa: E402

EPOCH = 113
OLD_KEY = "={{ $json.to }}-112"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-18nov-before-bankwhen.json")

NOTIFY_EDITS = (
    ("Every time they ask for it, call this again, even when you passed them on earlier in the chat or remember doing "
     "so: you cannot see whether that was closed since, and a repeat while it is still open is dropped by the system.",
     "Every time they ask to pay by transfer or for the account details, call this again, even when you passed them on "
     "earlier in the chat or remember doing so: you cannot see whether that was closed since, and a repeat while it is "
     "still open is dropped by the system. Asked only when the details will come, there is no new call and no new "
     "hand-over sentence: say plainly that you have no time for it, and that it is with a representative from "
     "collections, who will send them here."),
)

WORD_END = ".test(said); })() }}"
WORD_NEW = ".test(said) && (() => { const ahv = 'ackhold v1'; return !%s.test(said); })(); })() }}" % TRANSFER_WORDS


def bankwhen(wf):
    """The workflow with notify_team and the ack gate changed. Not memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    p = by["notify_team"]["parameters"]
    d = p["toolDescription"]
    for old, new in NOTIFY_EDITS:
        d = once(d, old, new)
    p["toolDescription"] = d
    cond = by["A word first?"]["parameters"]["conditions"]["conditions"][0]
    lv = cond["leftValue"]
    if "ackhold v" in lv or not lv.endswith(WORD_END):
        sys.exit("REFUSING: 'A word first?' does not end the way it did on 18 Nov, or already holds transfers.")
    cond["leftValue"] = lv[:-len(WORD_END)] + WORD_NEW
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and NOTIFY_EDITS[0][1] in by["notify_team"]["parameters"]["toolDescription"]:
        print("Nothing to do. Live already holds the note and answers 'when' plainly, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 112's. Read live first." % key)

    new = bankwhen(live)
    nb = {n["name"]: n for n in new["nodes"]}
    changed = [n["name"] for n in new["nodes"] if n != by[n["name"]]]
    if sorted(changed) != sorted(["notify_team", "A word first?"]):
        sys.exit("REFUSING: unexpected nodes would change: %s" % changed)
    if W.MEMORY_EPOCH != EPOCH:
        sys.exit("REFUSING: n8n_whatsapp.MEMORY_EPOCH is %d, not %d. Move the repo first." % (W.MEMORY_EPOCH, EPOCH))
    if prompt_of(new) != W.system_prompt():
        sys.exit("REFUSING: live's prompt is not docs/features/11-whatsapp-bot/prompt.md's.")
    W.check_memory_epoch(prompt=prompt_of(new), tools=tools_of(new))
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (unchanged)" % W.epoch_hash(prompt_of(new)))
    print("tools    : %s -> %s" % (W.epoch_hash(tools_of(live)), W.epoch_hash(tools_of(new))))
    print("memory   : %s -> %s (every buffer starts fresh)" % (OLD_KEY, NEW_KEY))
    print("changed  : %s" % ", ".join(changed + ["Conversation so far"]))

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
    print("  tools %s (want %s); memory key %s" % (W.epoch_hash(tools_of(back)), W.epoch_hash(tools_of(new)),
                                                  bb["Conversation so far"]["parameters"]["sessionKey"]))
    for node in ("notify_team", "A word first?"):
        print("  %s: %s" % (node, "as written" if bb[node]["parameters"] == nb[node]["parameters"] else "DIFFERS"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
