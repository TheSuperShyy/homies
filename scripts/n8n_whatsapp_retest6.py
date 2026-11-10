# -*- coding: utf-8 -*-
"""The tester's sixth run (10 Nov 2026, epoch 101): the one-voice sentence names its exception by the matter.

    python scripts/n8n_whatsapp_retest6.py              # dry run
    python scripts/n8n_whatsapp_retest6.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_retest6.py --apply      # write it
    python scripts/n8n_whatsapp_retest6.py --restore    # put the snapshot back

WHY. The Grok tester's sixth run (10 Nov, 07:54-09:37 UTC; the UChat copy's executions 169368-169866), the
first since epoch 100, had five replies with someone other than Michael in them, and a speed promise:
  C3.3 (169451)  "התקלה נמסרה לטיפול, וניגש לזה כמה שיותר מהר."
  C8.1 (169736)  "…, והוספתי מיד הערה דחופה לצוות."
  C8.2 (169755)  "…, והעברתי הערה דחופה לצוות."
  C10.1 (169773) "יש משהו שאוכל לעדכן את הצוות לגבי העשן בחדר המדרגות?"
  C11.3 (169714) "את התיקון עצמו עושים אנשים מהצוות של הומי'ז. … ומחכה לטיפול שלהם"
Each was the model's own draft, and Send let it through. On 8 Nov the same steps, with the same tools,
ran twice (the fourth run and the fifth) and none of them named a team. The model (Gemini 3.1 Pro,
temperature 1) is the same; between the runs only epoch 100's texts changed. Its one-voice sentence
gained ", חוץ מחברת המעליות ומצוות הגבייה, וגם עליהם רק מה שכתוב בהמשך": an exception named by WHO,
a team among them, hung on "you don't say you passed something on". C8-C11 then passed things on to
"the team", and C3.3 borrowed the lift's own hand-off ("מעבירים ... את המשך הטיפול ... לוחצים עליהם
לטפל בה בדחיפות") for a burst main pipe.

WHAT CHANGES
  - The prompt: the one-voice sentence is again what it was up to epoch 99, and its exception follows
    as its own sentence, named by the matter, the way "בגז זה אחרת" is: "רק במעלית ובהוראת קבע זה
    אחרת, כמו שכתוב בהמשך." The lift company and the collections team stay named only in their own
    lines (the lift fact, the standing order), which are unchanged. 26,021 -> 26,007 characters.
  - Memory: epoch 100 -> 101, so no buffer carries the run's "הערה דחופה לצוות" into the next turn.
Not changed: Send (its filters are not the cause), the tool texts, the inject, the phone agents.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py, then n8n_uchat.py --apply carries it to
the UChat copy, the bot in use.
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

EPOCH = 101
OLD_KEY = "={{ $json.to }}-100"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-10nov-before-retest6.json")

ONE_VOICE_OLD = ("ואתה לא מספר שהעברת משהו למישהו, חוץ מחברת המעליות ומצוות הגבייה, וגם עליהם רק מה שכתוב "
                 "בהמשך.")
ONE_VOICE_NEW = "ואתה לא מספר שהעברת משהו למישהו. רק במעלית ובהוראת קבע זה אחרת, כמו שכתוב בהמשך."


def retest6(wf):
    """The workflow with the one edit above; its anchor must occur exactly once. Does not touch memory."""
    out = copy.deepcopy(wf)
    agent = {n["name"]: n for n in out["nodes"]}["Answer the resident"]["parameters"]
    agent["options"]["systemMessage"] = once(agent["options"]["systemMessage"], ONE_VOICE_OLD, ONE_VOICE_NEW)
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and ONE_VOICE_NEW in prompt_of(live):
        print("Nothing to do. Live already names the one-voice exception by the matter, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 100's. Read live first." % key)

    new = retest6(live)
    if prompt_of(new) != W.system_prompt():
        sys.exit("REFUSING: the would-be prompt is not docs/features/11-whatsapp-bot/prompt.md's. "
                 "Edit the document first; live follows it.")
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
    print("  prompt %s (want %s); tools %s (want %s); memory key %s"
          % (W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)), W.epoch_hash(tools_of(back)),
             W.epoch_hash(tools_of(new)), bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
