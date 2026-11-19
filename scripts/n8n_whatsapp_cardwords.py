# -*- coding: utf-8 -*-
"""Epoch 115's two lines that did not reach the handset whole, and a note to Service that a standing order made (19 Nov; epoch 116).

    python scripts/n8n_whatsapp_cardwords.py              # dry run
    python scripts/n8n_whatsapp_cardwords.py --doc        # write the prompt edit into prompt.md's fence (once)
    python scripts/n8n_whatsapp_cardwords.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_cardwords.py --apply      # write it
    python scripts/n8n_whatsapp_cardwords.py --restore    # put the snapshot back

WHY. The owner's Grok run of epoch 115 (19 Nov, 10:49-10:57 UTC, conversation 101):
  - Cheques (193143): the model wrote "העברתי אותך לנציג מצוות הגבייה שיחזור אליך כאן לגבי תשלום בשיקים", as epoch 115
    told it ("שיחזור אליו כאן"), and Send's promise cutter took "שיחזור אליך כאן ..." (promise v8 cuts "יחזור אליך"
    outside a recorded standing order), so the tenant got "העברתי אותך לנציג מצוות הגבייה." with no word of what comes
    next. The Claude-played check had the same cut (co_cheques, turn 0); its expectations did not look for it.
  - A standing order from the bank (193126): request_standing_order answered already_recorded (the test number has one
    on record), and Michael said "רשמתי" with no number. The tool text tied the number to "recorded".
  - The same turn made a second note, to Service, as "something only a person can sort out": the bot said
    "מישהו מצוות הגבייה ייצור איתך קשר", which Team note this turn?'s promise test reads as an unbacked promise. Send
    already lets that sentence through after a recorded standing order (its SO test); the note did not know it, so
    every standing order recorded since 9 Nov has also paged Service.

WHAT CHANGES, in one write:
  The prompt              "שיחזור אליו כאן לגבי זה" -> "שיכתוב לו כאן לגבי זה" (cheques and the like).
  notify_team             "who will get back to them about it here" -> "who will write to them here about it".
  request_standing_order  the number every time, also when it was already recorded.
  Team note this turn?    sonote v1: no backstop note on a turn where request_standing_order recorded the request
                          (recorded or already_recorded true): its promise is the request, emailed to collections.
  Memory                  epoch 115 -> 116.
Not changed: Send, Reply usable?, Let the team know, the other tools.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py.
"""
import copy
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 116
OLD_KEY = "={{ $json.to }}-115"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-19nov-before-cardwords.json")
DOC = os.path.join(W.ROOT, "docs", "features", "11-whatsapp-bot", "prompt.md")

PROMPT_EDITS = (
    ("ואומר לו שהעברת אותו לנציג מצוות הגבייה שיחזור אליו כאן לגבי זה, בלי מתי.",
     "ואומר לו שהעברת אותו לנציג מצוות הגבייה שיכתוב לו כאן לגבי זה, בלי מתי."),
)

NOTIFY_EDITS = (
    ("tell them you have passed them to a representative from the collections team, who will get back to them about "
     "it here, never when.",
     "tell them you have passed them to a representative from the collections team, who will write to them here "
     "about it, never when."),
)

STANDING_EDITS = (
    ("What you tell them is that you recorded their request for a standing order, with its number, and that someone "
     "from the collections team will phone them about it.",
     "What you tell them, every time and also when it was already recorded, is that their request for a standing "
     "order is recorded, with its number, and that someone from the collections team will phone them about it."),
)

# The observation is n8n's string with the debt-tools result JSON inside it, so its quotes may arrive escaped: the
# same test Send's SO uses.
SOREC = r'/\\*"(?:recorded|already_recorded)\\*"\s*:\s*true/'
NOTE_OLD = "(() => { const t = String($json.output || ''); const TOLD = "
NOTE_NEW = ("(() => { const t = String($json.output || ''); const sov = 'sonote v1'; try { if (($('Answer the "
            "resident').first().json.intermediateSteps || []).some(s => ((s.action || { }).tool) === "
            "'request_standing_order' && %s.test(String(s.observation || '')))) return false; } catch (e) { } "
            "const TOLD = " % SOREC)

CHANGED = ["Answer the resident", "notify_team", "request_standing_order", "Team note this turn?"]


def edit_text(text, edits):
    for old, new in edits:
        text = once(text, old, new)
    return text


def cardwords(wf):
    """The workflow with the prompt, two tool texts and the team-note test changed. Not memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    opts = by["Answer the resident"]["parameters"]["options"]
    opts["systemMessage"] = edit_text(opts["systemMessage"], PROMPT_EDITS)
    for node, edits in (("notify_team", NOTIFY_EDITS), ("request_standing_order", STANDING_EDITS)):
        p = by[node]["parameters"]
        p["toolDescription"] = edit_text(p["toolDescription"], edits)
    note = by["Team note this turn?"]["parameters"]["conditions"]["conditions"][0]
    note["leftValue"] = once(note["leftValue"], NOTE_OLD, NOTE_NEW)
    return out


def doc():
    """Write PROMPT_EDITS into prompt.md, inside the System prompt section only."""
    raw = io.open(DOC, encoding="utf-8", newline="").read()
    head, sep, fence = raw.partition("## System prompt")
    if not sep:
        sys.exit("REFUSING: no '## System prompt' heading in prompt.md.")
    if PROMPT_EDITS[0][1] in fence:
        print("prompt.md already carries the edit.")
        return
    io.open(DOC, "w", encoding="utf-8", newline="").write(head + sep + edit_text(fence, PROMPT_EDITS))
    print("prompt.md: %d edit written into the System prompt section." % len(PROMPT_EDITS))


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    if "--doc" in sys.argv:
        return doc()
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and NOTIFY_EDITS[0][1] in by["notify_team"]["parameters"]["toolDescription"]:
        print("Nothing to do. Live already says 'write to them here', epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 115's. Read live first." % key)

    new = cardwords(live)
    nb = {n["name"]: n for n in new["nodes"]}
    changed = [n["name"] for n in new["nodes"] if n != by[n["name"]]]
    if sorted(changed) != sorted(CHANGED):
        sys.exit("REFUSING: unexpected nodes would change: %s" % changed)
    if W.MEMORY_EPOCH != EPOCH:
        sys.exit("REFUSING: n8n_whatsapp.MEMORY_EPOCH is %d, not %d. Move the repo first." % (W.MEMORY_EPOCH, EPOCH))
    if prompt_of(new) != W.system_prompt():
        sys.exit("REFUSING: the would-be prompt is not docs/features/11-whatsapp-bot/prompt.md's. "
                 "Run --doc first; live follows the document.")
    W.check_memory_epoch(prompt=prompt_of(new), tools=tools_of(new))
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s -> %s" % (W.epoch_hash(prompt_of(live)), W.epoch_hash(prompt_of(new))))
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
    print("  prompt %s (want %s); tools %s (want %s); memory key %s" % (
        W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)), W.epoch_hash(tools_of(back)),
        W.epoch_hash(tools_of(new)), bb["Conversation so far"]["parameters"]["sessionKey"]))
    for node in CHANGED:
        print("  %s: %s" % (node, "as written" if bb[node]["parameters"] == nb[node]["parameters"] else "DIFFERS"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
