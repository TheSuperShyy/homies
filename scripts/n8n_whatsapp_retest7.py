# -*- coding: utf-8 -*-
"""The tester's seventh run (10 Nov 2026, epoch 102): the lift line loses its "urgently", and Send knows
"a professional will be sent".

    python scripts/n8n_whatsapp_retest7.py              # dry run
    python scripts/n8n_whatsapp_retest7.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_retest7.py --apply      # write it
    python scripts/n8n_whatsapp_retest7.py --restore    # put the snapshot back

WHY. The Grok tester's seventh run (10 Nov, 10:26-11:52 UTC; the UChat copy's executions 169956-170367,
one per message, all on epoch 101) had no team anywhere (five in the sixth run), and two promises:
  C1.3 (169970)  "אנחנו נעקוב אחרי זה ונוודא שהם מגיעים לטפל כמה שיותר מהר."  (the lift ticket's opening)
  C3.3 (170031)  "נשלח איש מקצוע מטעמנו לבדוק ולטפל בזה."                   (a main-pipe ticket)
Both were the model's own drafts. C1.5's draft also had "ואנחנו ממשיכים ללחוץ עליהם כדי שיגיעו בהקדם",
which Send cut ("בהקדם" is in its list).

The lift. Every lift ticket opened since epoch 100 promised speed: the sixth run's "ולוחצים עליהם להגיע
כמה שיותר מהר" and this run's "ונוודא שהם מגיעים לטפל כמה שיותר מהר". The five lift turns of the two
8 Nov runs, before the lift line existed, promised nothing (their every "כמה שיותר מהר" is the manager
line's "so I can help you as fast as possible"). The lift line says "ולוחצים עליהם לטפל בה בדחיפות".
Yariv's own words (9 Nov: 2.2, 2.3/2.4, 4.1) are "we pass it on and follow it", "it depends on the lift
company, we make every effort with them" and "we press them": "urgently" was ours, and it comes back as
"as fast as possible". The sixth run's C3.3 borrowed it for a main pipe ("וניגש לזה כמה שיותר מהר").

The professional. Send's promise list cuts "נשלח מישהו / טכנאי" and did not know "איש מקצוע". The
prompt already says Michael sends nobody ("ולא שולח אף אחד"), so a new form joins the list with a gate
case, as a slang word does (CONTEXT), rather than a sentence on top.

WHAT CHANGES
  - The prompt: "עוקבים אחרי הקריאה ולוחצים עליהם לטפל בה בדחיפות." -> "עוקבים אחרי הקריאה ולוחצים
    עליהם." Nothing else; the lift company, "when depends on them" and when he hears it are unchanged.
    26,007 -> 25,991 characters.
  - The promise phrases (n8n_whatsapp_nopromise.PHRASES = n8n_whatsapp_retry.PROMISE_PHRASES), in the four
    places live carries them: Send, Reply usable? (twice) and Try again. "(מישהו|טכנאי)" after "נשלח /
    ישלחו" becomes "(מישהו|טכנאי|איש מקצוע|בעל מקצוע)". Send's mark: promise v6 -> v7.
  - Memory: epoch 101 -> 102, so no buffer carries "ונוודא שהם מגיעים" into the next turn.
Not changed: the "anything else" endings (R5) and the plural "you" (R3): both were in the 8 Nov runs at
the same steps, and no text causes them. The inject, the tool texts, the phone agents (the incoming
agent's own lift line, docs/assistant/demo-inbound.md, carries the same "בדחיפות": owed, chatbot first).

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py, then n8n_uchat.py --apply carries it to
the UChat copy, the bot in use.
"""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 102
OLD_KEY = "={{ $json.to }}-101"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-10nov-before-retest7.json")

LIFT_OLD = "עוקבים אחרי הקריאה ולוחצים עליהם לטפל בה בדחיפות."
LIFT_NEW = "עוקבים אחרי הקריאה ולוחצים עליהם."

SENT_OLD = "(נשלח|ישלחו) ((אליכם|אליך|אלייך) )?(מישהו|טכנאי)|"
SENT_NEW = "(נשלח|ישלחו) ((אליכם|אליך|אלייך) )?(מישהו|טכנאי|איש מקצוע|בעל מקצוע)|"
PHRASES_OLD = NP.PHRASES.replace(SENT_NEW, SENT_OLD)
assert SENT_NEW in NP.PHRASES and PHRASES_OLD != NP.PHRASES, "nopromise.PHRASES does not have v7's words yet"
PV_OLD = "const pv = 'promise v6';"
PV_NEW = "const pv = 'promise v7';"

# Where live carries the phrase list, and how many times.
PLACES = (("Send", 1), ("Reply usable?", 2), ("Try again", 1))


def swap(params, old, new, count, where):
    """params with old -> new, which must occur exactly `count` times in it (read as JSON text)."""
    text = json.dumps(params, ensure_ascii=False)
    found = text.count(old)
    if found != count:
        sys.exit("REFUSING: %s has %r %d times, not %d. Read live first." % (where, old[:40], found, count))
    return json.loads(text.replace(old, new))


def retest7(wf):
    """The workflow with the edits above; each anchor must occur as often as stated. Does not touch memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    agent = by["Answer the resident"]["parameters"]
    agent["options"]["systemMessage"] = once(agent["options"]["systemMessage"], LIFT_OLD, LIFT_NEW)
    for name, count in PLACES:
        # The whole list, not only its piece: live and the repo must agree before anything moves.
        swap(by[name]["parameters"], PHRASES_OLD, PHRASES_OLD, count, name)
        by[name]["parameters"] = swap(by[name]["parameters"], SENT_OLD, SENT_NEW, count, name)
    by["Send"]["parameters"] = swap(by["Send"]["parameters"], PV_OLD, PV_NEW, 1, "Send's mark")
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    # A later epoch owns the memory key (11 Nov: hiintro, 103); the fix is still this carrier's to check.
    later = W.MEMORY_EPOCH > EPOCH and key == "={{ $json.to }}-%d" % W.MEMORY_EPOCH
    if (key == NEW_KEY or later) and LIFT_NEW in prompt_of(live) and PV_NEW in by["Send"]["parameters"]["jsonBody"]:
        print("Nothing to do. Live already has the seventh run's fix, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 101's. Read live first." % key)

    new = retest7(live)
    if prompt_of(new) != W.system_prompt():
        sys.exit("REFUSING: the would-be prompt is not docs/features/11-whatsapp-bot/prompt.md's. "
                 "Edit the document first; live follows it.")
    nb = {n["name"]: n for n in new["nodes"]}
    for name, count in PLACES:
        have = json.dumps(nb[name]["parameters"], ensure_ascii=False).count(NP.PHRASES)
        if have != count:
            sys.exit("REFUSING: %s would carry the repo's phrase list %d times, not %d." % (name, have, count))
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("tools    : %s (unchanged: %s)" % (W.epoch_hash(tools_of(new)), tools_of(new) == tools_of(live)))
    print("promise  : v6 -> v7 in Send; the list's new words in %s"
          % ", ".join("%s (%d)" % (n, c) for n, c in PLACES))
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
    print("  prompt %s (want %s); tools %s (want %s); memory key %s; promise v7 %s; the list's new words %s"
          % (W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)), W.epoch_hash(tools_of(back)),
             W.epoch_hash(tools_of(new)), bb["Conversation so far"]["parameters"]["sessionKey"],
             "present" if PV_NEW in bb["Send"]["parameters"]["jsonBody"] else "MISSING",
             ", ".join("%s %d" % (n, json.dumps(bb[n]["parameters"], ensure_ascii=False).count(NP.PHRASES))
                       for n, _ in PLACES)))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
