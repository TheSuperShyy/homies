# -*- coding: utf-8 -*-
"""Michael introduces himself again after 8 quiet hours, not 24 (20 Nov; Sort only, no new epoch).

    python scripts/n8n_whatsapp_greetgap.py              # dry run
    python scripts/n8n_whatsapp_greetgap.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_greetgap.py --apply      # write it
    python scripts/n8n_whatsapp_greetgap.py --restore    # put the snapshot back

WHY. The owner, 20 Nov, with a screenshot of run 195345 (07:52 UTC): "i noticed michael did not introduced
himself". He had asked "היי, איך אני משלם את ועד הבית?" 20.5 hours after his last message (the Grok rerun,
19 Nov 11:24 UTC). Sort counts a phone as mid-conversation while it wrote in the last 24 hours, so the turn
carried "[אתם כבר באמצע שיחה. לא מציגים את עצמך שוב ...]" and the answer greeted back without the name, as
the owner's greeting table says for mid-conversation. He was shown examples and chose 8 hours: "ok go ahead
with 8 hours and push it live".

WHAT CHANGES: Sort's `greeted` window, 24 hours -> 8 (greetgap v1). Everything that reads `greeted` is as it
was: on a first message Worth a word?'s note has the ack greet by the clock and name Michael, and Send then
takes the greeting and the name out of the answer; with no ack, the inject has the answer open with the name.
A bare hello still gets Sort's canned intro whatever the window.

NOT CHANGED: the prompt, the tools, the memory key (no model-facing text moves, so no epoch), every other node.

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
from n8n_whatsapp_ionly import WORKFLOW_ID, once, snapshot, restore  # noqa: E402

SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-20nov-before-greetgap.json")
MARK = "greetgap v1"

OLD = (
    "// A person greets again after a day of silence — and so does Michael. The\n"
    "// value is the last time this phone wrote; anything that is not a number is\n"
    "// the old boolean format and counts as stale, so every existing contact gets\n"
    "// the new introduction once.\n"
    "const lastSeen = store.greeted[from];\n"
    "const greeted = typeof lastSeen === 'number' && (Date.now() - lastSeen) < 24 * 60 * 60 * 1000;\n"
)
NEW = (
    "// A person greets again after a quiet gap, and so does Michael. The value is\n"
    "// the last time this phone wrote; anything that is not a number is the old\n"
    "// boolean format and counts as stale. " + MARK + " (the owner, 20 Nov: \"ok go\n"
    "// ahead with 8 hours\"): the gap is 8 hours, it was a day. Someone who wrote\n"
    "// yesterday afternoon and writes again this morning meets Michael again.\n"
    "const GREET_GAP = 8 * 60 * 60 * 1000;\n"
    "const lastSeen = store.greeted[from];\n"
    "const greeted = typeof lastSeen === 'number' && (Date.now() - lastSeen) < GREET_GAP;\n"
)


def greetgap(wf):
    """The workflow with Sort's window at 8 hours. Nothing else."""
    out = copy.deepcopy(wf)
    sort = next(n for n in out["nodes"] if n["name"] == "Sort")
    sort["parameters"]["jsCode"] = once(sort["parameters"]["jsCode"], OLD, NEW)
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    code = by["Sort"]["parameters"]["jsCode"]
    if MARK in code:
        print("Nothing to do. Live Sort already carries %s (8 hours)." % MARK)
        return
    if code.count(OLD) != 1:
        sys.exit("REFUSING: Sort's 24-hour window is not where this patcher expects it. Read live first.")

    new = greetgap(live)
    nb = {n["name"]: n for n in new["nodes"]}
    changed = [n["name"] for n in new["nodes"] if n != by[n["name"]]]
    if changed != ["Sort"]:
        sys.exit("REFUSING: unexpected nodes would change: %s" % changed)
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("Sort     : greeted window 24 h -> 8 h (%s)" % MARK)
    print("memory   : %s (unchanged)" % by["Conversation so far"]["parameters"].get("sessionKey"))

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
    print("  Sort: %s" % ("as written" if bb["Sort"]["parameters"] == nb["Sort"]["parameters"] else "DIFFERS"))
    others = [k for k in by if k != "Sort" and bb.get(k) != by[k]]
    print("  other nodes changed: %s" % (others or "none"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
