# -*- coding: utf-8 -*-
"""Pressed in an emergency, the line again as a warm invitation (11 Nov 2026, night, epoch 107).

    python scripts/n8n_whatsapp_warmline.py              # dry run
    python scripts/n8n_whatsapp_warmline.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_warmline.py --apply      # write it
    python scripts/n8n_whatsapp_warmline.py --restore    # put the snapshot back

WHY. The owner's Grok run of the updated emergency-line brief (18:45-19:07 Israel, 16:45-17:07 UTC) passed every
rule. Its notes were all about tone, and both came from our own words in the prompt:
  - pressed, the reply was the prompt's description played back: "המוקד הטלפוני שלנו הוא המקום לטפל בזה עכשיו.
    המספר הוא 077-6687949." (E4.2; E3.2 opened with the same sentence). Grok: no invitation, cold, close to a
    brush-off for a panicking tenant. The prompt said "שהמוקד הוא המקום לזה עכשיו, עם המספר";
  - the caring word was only "זה באמת דחוף" / "זה בהחלט דחוף", an acknowledgement rather than care. The prompt said
    "מילה קצרה ואכפתית משלך" with nothing about whom it is for.
The owner asked for the line "in a polite way". As with the gas sentence, the words are shown, not described.

WHAT CHANGES, in one write: the prompt, two edits.
  - Pressed: "בחום ובמילים אחרות, שאפשר להתקשר עכשיו למוקד החירום שלנו, עם המספר" in place of "בפשטות ובמילים
    אחרות, שהמוקד הוא המקום לזה עכשיו, עם המספר".
  - The first message's caring word is "על מה שהוא עובר".
  Memory: epoch 106 -> 107.
Not changed: the line's sentence, no ticket, no question, the tools, Send, the guards, the inject.

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
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 107
OLD_KEY = "={{ $json.to }}-106"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-11nov-before-warmline.json")

PROMPT_EDITS = (
    ("הוא מילה קצרה ואכפתית משלך, ואחריה המשפט הזה, מילה במילה:",
     "הוא מילה קצרה ואכפתית משלך על מה שהוא עובר, ואחריה המשפט הזה, מילה במילה:"),
    ("הוא שומע ממך שוב, בפשטות ובמילים אחרות, שהמוקד הוא המקום לזה עכשיו, עם המספר, ולא מוסיף שאלה:",
     "הוא שומע ממך שוב, בחום ובמילים אחרות, שאפשר להתקשר עכשיו למוקד החירום שלנו, עם המספר, ולא מוסיף שאלה:"),
)


def warmline(wf):
    """The workflow with the edits above; each anchor exactly once. Does not touch memory."""
    out = copy.deepcopy(wf)
    agent = {n["name"]: n for n in out["nodes"]}["Answer the resident"]["parameters"]
    for old, new in PROMPT_EDITS:
        agent["options"]["systemMessage"] = once(agent["options"]["systemMessage"], old, new)
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and PROMPT_EDITS[1][1] in prompt_of(live):
        print("Nothing to do. Live already gives the pressed line as a warm invitation, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 106's. Read live first." % key)
    if W.MEMORY_EPOCH != EPOCH:
        sys.exit("REFUSING: n8n_whatsapp.MEMORY_EPOCH is %d, not %d. Move the repo first." % (W.MEMORY_EPOCH, EPOCH))

    new = warmline(live)
    if prompt_of(new) != W.system_prompt():
        sys.exit("REFUSING: the would-be prompt is not docs/features/11-whatsapp-bot/prompt.md's. "
                 "Edit the document first; live follows it.")
    if tools_of(new) != tools_of(live):
        sys.exit("REFUSING: the tools would change; this patcher only edits the prompt.")
    W.check_memory_epoch(prompt=prompt_of(new), tools=tools_of(new))
    nb = {n["name"]: n for n in new["nodes"]}
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
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
