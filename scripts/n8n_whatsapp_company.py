# -*- coding: utf-8 -*-
"""Homies is "a company for managing and maintaining buildings", in Michael's own line about himself (26 Nov; epoch 117).

    python scripts/n8n_whatsapp_company.py              # dry run
    python scripts/n8n_whatsapp_company.py --doc        # write the prompt edit into prompt.md's fence (once)
    python scripts/n8n_whatsapp_company.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_company.py --apply      # write it
    python scripts/n8n_whatsapp_company.py --restore    # put the snapshot back

WHY. Homies, forwarded by the owner on 26 Nov: "אפשר לבקש ממיכאל שלא יגיד 'אנחנו חברה לניהול ועד בית' אלא, 'אנחנו
חברה לניהול ואחזקת בניינים'". The bot said it on 24 Nov at 08:26 UTC, to a massage clinic's own bot that had written
to the number by mistake: "הגעת למספר של הומי'ז, אנחנו חברה לניהול ועד בית". No text says that. The prompt's first
line called Homies "חברת ניהול בתים משותפים", the only place it says what the company is, and the model put it in
its own words. So the line now carries Homies' own words, and nothing is added: no rule, and the old phrase is not
quoted anywhere (a quoted forbidden phrase gets said back).

WHAT CHANGES, in one write:
  The prompt   "אתה מיכאל מצוות השירות של הומי'ז, חברת ניהול בתים משותפים." ->
               "אתה מיכאל מצוות השירות של הומי'ז, חברה לניהול ואחזקת בניינים."
  Memory       epoch 116 -> 117.
Not changed: Worth a word? (it only decides whether a message asks for a payment link, and never says what Homies
is), the tools, Send and every guard.

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

EPOCH = 117
OLD_KEY = "={{ $json.to }}-116"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-26nov-before-company.json")
DOC = os.path.join(W.ROOT, "docs", "features", "11-whatsapp-bot", "prompt.md")

PROMPT_EDITS = (
    ("אתה מיכאל מצוות השירות של הומי'ז, חברת ניהול בתים משותפים.",
     "אתה מיכאל מצוות השירות של הומי'ז, חברה לניהול ואחזקת בניינים."),
)

CHANGED = ["Answer the resident"]


def edit_text(text, edits):
    for old, new in edits:
        text = once(text, old, new)
    return text


def company(wf):
    """The workflow with the prompt's first line changed. Not memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    opts = by["Answer the resident"]["parameters"]["options"]
    opts["systemMessage"] = edit_text(opts["systemMessage"], PROMPT_EDITS)
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
    if key == NEW_KEY and PROMPT_EDITS[0][1] in prompt_of(live):
        print("Nothing to do. Live already says 'חברה לניהול ואחזקת בניינים', epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 116's. Read live first." % key)

    new = company(live)
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
    print("tools    : %s -> %s (unchanged)" % (W.epoch_hash(tools_of(live)), W.epoch_hash(tools_of(new))))
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
