# -*- coding: utf-8 -*-
"""The owner's standard emergency reply is the base of Michael's answer (12 Nov 2026, later; epoch 109, danger v10).

    python scripts/n8n_whatsapp_standard.py                         # dry run
    python scripts/n8n_whatsapp_standard.py --dump F                # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_standard.py --dump F --labels-only  # the label and the key only (TDD: cases fail)
    python scripts/n8n_whatsapp_standard.py --apply                 # write it
    python scripts/n8n_whatsapp_standard.py --restore               # put the snapshot back

WHY. The owner, after epoch 108 had made his morning's reference the model ("אני רק העוזר הדיגיטלי ואין לי
אפשרות לתת מענה מיידי. בבקשה תתקשר למוקד החירום שלנו כדי שתוכל לקבל מענה בהקדם"): "אני רק העוזר הדיגיטלי,
לקריאות דחופות ואירועי חירום בבקשה תתקשר בדחיפות למוקד הטלפוני שלנו - 077-6687949" and "add this on the context
like the basis of what the bot should answer make this the main standard". This text takes the morning's place.

WHAT LIVE SEND DOES WITH IT (epoch 108, run through the live code before this was written): it goes out whole, the
caring-word and pressed variants too, and right after the menu no "כאן מיכאל" is put in front of it. An en dash
before the number becomes a comma, as every dash does. The guards pass it. So Send needs only its own two
sentences changed: the one it adds when a cut takes the line, and the one it sends when nothing is left.

WHAT CHANGES, in one write:
  The prompt   his first message about an emergency is "this message, the basis of your answer", the standard as
               the owner wrote it with a full stop added. He may fit it to the case and to who writes (a woman
               hears "תתקשרי"), and three things are always in it: he is only the digital assistant, a polite
               request to call our phone line urgently, and the number; no question. Pressed: unchanged, the same
               three things warmly, in other words.
  Send         danger v10: HOTS is the standard's second half, HOTA the whole standard.
  Memory       epoch 108 -> 109.
Not changed: promise v8, line v2, voice v3, manners v6 (they keep any wording of it whole), the tools, gas, no
ticket and no note in an emergency. The incoming phone agent's twin is owed.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py. The bot in use is this workflow (Chatwoot,
since 10 Nov); the UChat copy is off.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_hotline import expr_compiles  # noqa: E402
from n8n_whatsapp_refline import PROMPT_EDITS as REFLINE_EDITS, REF as REF108, HOT_ASK as ASK108  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 109
OLD_KEY = "={{ $json.to }}-108"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-12nov-before-standard.json")

# The owner's standard, word for word, with a full stop at the end. Send's sentences are its two halves.
STD_ASK = "לקריאות דחופות ואירועי חירום בבקשה תתקשר בדחיפות למוקד הטלפוני שלנו - 077-6687949."
STD = "אני רק העוזר הדיגיטלי, " + STD_ASK

PROMPT_EDITS = (
    (REFLINE_EDITS[0][1],
     "מה שיש לך לתת, כבר בהודעה הראשונה שלך על המקרה, הוא ההודעה הזאת, שהיא הבסיס לתשובה שלך: \"" + STD + "\" "
     "אפשר להתאים אותה למקרה ולמי שכותב, אבל שלושה דברים נמצאים בה תמיד: שאתה רק העוזר הדיגיטלי, בקשה בנימוס "
     "שיתקשר בדחיפות למוקד הטלפוני שלנו, והמספר. ושם ההודעה נגמרת, בלי שאלה."),
)

LABELS = (("const dv = 'danger v9';", "const dv = 'danger v10';"),)
SEND_EDITS = LABELS + (
    ("const HOTS = '" + ASK108 + "'; const HOTA = 'אני רק העוזר הדיגיטלי ואין לי אפשרות לתת מענה מיידי. ' + HOTS;",
     "const HOTS = '" + STD_ASK + "'; const HOTA = 'אני רק העוזר הדיגיטלי, ' + HOTS;"),
)


def standard(wf, labels_only=False):
    """The workflow with the edits above; each anchor exactly once. Does not touch memory.
    labels_only: the version label alone, no code and no prompt (so the new cases can be seen failing)."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    body = by["Send"]["parameters"]["jsonBody"]
    for old, new in (LABELS if labels_only else SEND_EDITS):
        assert "}}" not in new and "{{" not in new, "an edit would end the expression early"
        body = once(body, old, new)
    by["Send"]["parameters"]["jsonBody"] = body
    if not labels_only:
        agent = by["Answer the resident"]["parameters"]
        for old, new in PROMPT_EDITS:
            agent["options"]["systemMessage"] = once(agent["options"]["systemMessage"], old, new)
        sm = agent["options"]["systemMessage"]
        assert REF108 not in sm, "the prompt still quotes the morning's reference"
        assert sm.count("\"" + STD + "\"") == 1, "the prompt does not quote the owner's standard once"
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    labels_only = "--labels-only" in sys.argv
    if apply and labels_only:
        sys.exit("REFUSING: --labels-only is for a dump, never for live.")
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and "const dv = 'danger v10';" in by["Send"]["parameters"]["jsonBody"]:
        print("Nothing to do. Live already takes the owner's standard for an emergency, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 108's. Read live first." % key)

    new = standard(live, labels_only)
    nb = {n["name"]: n for n in new["nodes"]}
    if tools_of(new) != tools_of(live):
        sys.exit("REFUSING: the tools would change; this patcher edits the prompt and Send only.")
    if not labels_only:
        if W.MEMORY_EPOCH != EPOCH:
            sys.exit("REFUSING: n8n_whatsapp.MEMORY_EPOCH is %d, not %d. Move the repo first." % (W.MEMORY_EPOCH, EPOCH))
        if prompt_of(new) != W.system_prompt():
            sys.exit("REFUSING: the would-be prompt is not docs/features/11-whatsapp-bot/prompt.md's. "
                     "Edit the document first; live follows it.")
        W.check_memory_epoch(prompt=prompt_of(new), tools=tools_of(new))
    expr_compiles(nb["Send"]["parameters"]["jsonBody"], "Send")
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("Send     : danger v10%s" % (" (LABEL ONLY: no code, no prompt)" if labels_only else ""))
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
    sb = bb["Send"]["parameters"]["jsonBody"]
    print("\nwritten  : %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  prompt %s (want %s); memory key %s; Send %s"
          % (W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)),
             bb["Conversation so far"]["parameters"]["sessionKey"],
             "as written" if sb == nb["Send"]["parameters"]["jsonBody"] else "DIFFERS"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
