# -*- coding: utf-8 -*-
"""Every chat starts fresh: the memory key only, one epoch up (6 Oct; again 29 Oct, night).

    python scripts/n8n_whatsapp_fresh.py            # dry run
    python scripts/n8n_whatsapp_fresh.py --dump F   # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_fresh.py --apply    # write it
    python scripts/n8n_whatsapp_fresh.py --restore  # put the snapshot of the epoch before back

WHY. The emergency fix (n8n_whatsapp_danger.py, debt-tools v118) is code, so
check_memory_epoch() asks for no bump. But a buffer holds the model's raw
drafts, and the owner's held chat 6 of the 5 Oct evening test: "our team is
already on its way", the safety advice, and the intercom's number read out as
the emergency ticket. The owner asked for that chat to be run again (6 Oct: *"run
the new test for the whole chatbot again for the emergency only"*), and a model
copies its own earlier lines (n8n_whatsapp.py, MEMORY_EPOCH, 1 Sep).

WHAT CHANGES: `Conversation so far`'s key, one epoch up (MEMORY_EPOCH - 1 ->
MEMORY_EPOCH). Nothing else. Used twice on 6 Oct: 75 -> 76 before the emergency
was run again, 76 -> 77 before it was run a third time on danger v2 (the second
run's buffer held "the only number I can give you is ..."). Used again on 29 Oct (night),
88 -> 89, after the owner had tested epoch 88 on the handset: *"ok its kidna good
now so lets reset the memory again"*. Each bump has its own snapshot, named for the
epoch it replaced; the two of 6 Oct are in docs/handover/, later ones in local/
like the other patchers'.

THE CHECK READS LIVE (29 Oct, night). It was W.check_memory_epoch() on the repo's own
texts. The 29 Oct patchers (section6, ionly, gladly, checkword) write live
directly and wait for the fold, so that night the repo built inject 31ff6f4f297f
and tools ba0d94da4e6d against live's 680da3fc96bc and 72cac34efc1c, and that
check refused a bump that changes no text. What it guards is the same: live's
prompt, inject and tool texts must be the ones EPOCH_COVERS records, or the new
epoch would be minted over text it does not cover.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_ionly import prompt_of, tools_of, snapshot, restore  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
OLD_EPOCH = W.MEMORY_EPOCH - 1
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-before-fresh-e%d.json" % OLD_EPOCH)
MEMORY_KEY = "={{ $json.to }}-%d"
NL = chr(10)


def covered(live):
    """Refuse unless live's prompt, inject and tool texts are the ones the epoch covers."""
    inject = {n["name"]: n for n in live["nodes"]}["Answer the resident"]["parameters"]["text"]
    for name, text in (("prompt", prompt_of(live)), ("inject", inject), ("tools", tools_of(live))):
        if W.epoch_hash(text) != W.EPOCH_COVERS.get(name):
            sys.exit("REFUSING: live's %s is %s and the epoch covers %s. A text change goes out with its "
                     "own patcher, which moves the epoch itself." % (name, W.epoch_hash(text), W.EPOCH_COVERS.get(name)))


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    later = False                              # the key is always this script's to move one up

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    if "Conversation so far" not in by:
        sys.exit("No 'Conversation so far' node on the live workflow -- refusing to guess.")
    covered(live)
    if snapshot(live, SNAPSHOT):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    before_layout = layout_complaints(nodes)

    changes = []
    mem = by["Conversation so far"]["parameters"]
    want_key = MEMORY_KEY % W.MEMORY_EPOCH
    if not later and mem.get("sessionKey") != want_key:
        if mem.get("sessionKey") != MEMORY_KEY % OLD_EPOCH:
            sys.exit("REFUSING: the memory key is %r, not epoch %d." % (mem.get("sessionKey"), OLD_EPOCH))
        mem["sessionKey"] = want_key
        changes.append("Conversation so far: memory epoch %d -> %d (every buffer starts fresh)"
                       % (OLD_EPOCH, W.MEMORY_EPOCH))
    if mem.get("contextWindowLength") != W.MEMORY_TURNS:
        sys.exit("REFUSING: the memory window is %r, not %d." % (mem.get("contextWindowLength"), W.MEMORY_TURNS))

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    if not changes:
        print("")
        print("Nothing to do. Live already matches.")
        return
    print("")
    print("changes:")
    for ch in changes:
        print("  - %s" % ch)
    worse = sorted(layout_complaints(nodes) - before_layout)
    if worse:
        sys.exit("REFUSING TO PATCH. New placement problems:" + NL + "    " + (NL + "    ").join(worse))
    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        NP.dump(nodes, conns, path)
        print("")
        print("dumped   : %s (the would-be workflow, secret replaced)" % path)
    if not apply:
        print("")
        print("Dry run. Re-run with --apply to write it.")
        return
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": nodes, "connections": conns,
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    bb = {n["name"]: n for n in back["nodes"]}
    print("")
    print("written: %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  memory key %s" % bb["Conversation so far"]["parameters"]["sessionKey"])
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
