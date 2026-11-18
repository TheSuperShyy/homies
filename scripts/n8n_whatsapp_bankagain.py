# -*- coding: utf-8 -*-
"""A bank transfer is handed to collections every time it is asked, and the note finds Collections (18 Nov; epoch 112).

    python scripts/n8n_whatsapp_bankagain.py              # dry run
    python scripts/n8n_whatsapp_bankagain.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_bankagain.py --apply      # write it
    python scripts/n8n_whatsapp_bankagain.py --restore    # put the snapshot back

WHY. The owner's Grok run of epoch 111 (18 Nov, 11:00-11:11 UTC, conversation 95, a fresh chat) passed every rule
on the handset and failed where it could not look:
  - B1.1 (execution 190483): no notify_team call. The memory (keyed by the phone, not the chat) held the 10:20
    synthetic hand-over, and notify_team said "Asked about it again, it is already with collections: say so,
    without calling again". So Michael said "הבקשה שלך כבר נמצאת אצל צוות הגבייה" and nothing reached Collections.
  - B2.1 (190520): no call either. The backstop fired on "הם ייצרו איתך קשר", with reason `other`, so the note went
    to Service as "something only a person can sort out". The reply mixed in the manager-request words ("אני עושה
    כל מה שאפשר כדי לזרז את זה").

WHAT CHANGES, in one write:
  notify_team           "asked again, without calling again" becomes: every time they ask, call it again, even
                        when you passed them on earlier or remember doing so (you cannot see whether that was closed;
                        a repeat while it is still open is dropped by "Hand to a person"). A request for a person
                        about it is this same hand-over, in these words, not the manager-request words.
  Team note this turn?  banknote v1: the note also goes when the tenant's message names a transfer or the account
                        details and the reply names collections, whatever the model called.
  Let the team know     with no notify_team call (the backstop), the reason is bank_transfer when the tenant's message
                        names a transfer or the account details, else `other` as before.
  Memory                epoch 111 -> 112 (it also forgets the 10:20 synthetic hand-over on the owner's number).
Not changed: the prompt, the other tools, Send, Reply usable?, Try again, "Hand to a person".

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

EPOCH = 112
OLD_KEY = "={{ $json.to }}-111"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-18nov-before-bankagain.json")

# The tenant's own words name a bank transfer or the account details. No backslashes, so nothing to escape in n8n.
TRANSFER_WORDS = "/העברה בנקאית|בהעברה|פרטי (ה)?חשבון|מספר (ה)?חשבון|לחשבון (ה)?בנק/"
SAID = "String($('Sort').first().json.in_text || $('Sort').first().json.text || '')"

NOTIFY_EDITS = (
    ("Asked about it again, it is already with collections: say so, without calling again.",
     "Every time they ask for it, call this again, even when you passed them on earlier in the chat or remember doing "
     "so: you cannot see whether that was closed since, and a repeat while it is still open is dropped by the system. "
     "A request for a person about it is this same hand-over, told in these words, not the words for a manager request."),
)

NOTE_CLAUSE = (" || (() => { const btv = 'banknote v1'; try { return %s.test(%s) && /גבייה/.test(String($json.output || '')); }"
               " catch (e) { return false; } })() }}" % (TRANSFER_WORDS, SAID))

LET_EDIT = ("return String(o.reason || 'other');",
            "return String(o.reason || (%s.test(%s) ? 'bank_transfer' : 'other'));" % (TRANSFER_WORDS, SAID))


def bankagain(wf):
    """The workflow with notify_team, the team-note test and the note's reason changed. Not memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    p = by["notify_team"]["parameters"]
    d = p["toolDescription"]
    for old, new in NOTIFY_EDITS:
        d = once(d, old, new)
    p["toolDescription"] = d
    cond = by["Team note this turn?"]["parameters"]["conditions"]["conditions"][0]
    lv = cond["leftValue"]
    if not lv.endswith(" }}") or "banknote v" in lv:
        sys.exit("REFUSING: the team-note test does not end the way it did on 18 Nov, or already has banknote.")
    cond["leftValue"] = lv[:-3] + NOTE_CLAUSE
    v = by["Let the team know"]["parameters"]["workflowInputs"]["value"]
    v["reason"] = once(v["reason"], *LET_EDIT)
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and NOTIFY_EDITS[0][1] in by["notify_team"]["parameters"]["toolDescription"]:
        print("Nothing to do. Live already calls the hand-over every time, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 111's. Read live first." % key)

    new = bankagain(live)
    nb = {n["name"]: n for n in new["nodes"]}
    changed = [n["name"] for n in new["nodes"] if n != by[n["name"]]]
    if sorted(changed) != sorted(["notify_team", "Team note this turn?", "Let the team know"]):
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
    for node in ("notify_team", "Team note this turn?", "Let the team know"):
        print("  %s: %s" % (node, "as written" if bb[node]["parameters"] == nb[node]["parameters"] else "DIFFERS"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
