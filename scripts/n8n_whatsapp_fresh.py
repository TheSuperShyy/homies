# -*- coding: utf-8 -*-
"""Every chat starts fresh after the emergency fix: the memory key only, 6 Oct.

    python scripts/n8n_whatsapp_fresh.py            # dry run
    python scripts/n8n_whatsapp_fresh.py --dump F   # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_fresh.py --apply    # write it
    python scripts/n8n_whatsapp_fresh.py --restore  # put the 6 Oct snapshot back

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
run's buffer held "the only number I can give you is ..."). Each bump has its own
snapshot, named for the epoch it replaced.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_untemplate as U  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
OLD_EPOCH = W.MEMORY_EPOCH - 1
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-before-fresh-e%d.json" % OLD_EPOCH)
PLACEHOLDER = NP.PLACEHOLDER
MEMORY_KEY = "={{ $json.to }}-%d"
NL = chr(10)


def snapshot(live):
    if os.path.exists(SNAPSHOT):
        return False
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    live = dict(live, staticData="<stripped: runtime state keyed by phone numbers>")
    text = json.dumps(live, ensure_ascii=False, indent=1)
    if secret:
        if secret not in text:
            sys.exit("The live workflow does not contain N8N_WEBHOOK_SECRET from .env, "
                     "so the snapshot's redaction would miss. Refusing to write it.")
        text = text.replace(secret, PLACEHOLDER)
    with open(SNAPSHOT, "w", encoding="utf-8", newline=NL) as f:
        f.write(text)
    return True


def restore():
    snap = json.load(open(SNAPSHOT, encoding="utf-8"))
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    if not secret:
        sys.exit("N8N_WEBHOOK_SECRET is not in .env; the snapshot's Sort node would "
                 "go live with a placeholder secret. Refusing.")
    body = json.loads(json.dumps(snap, ensure_ascii=False).replace(PLACEHOLDER, secret))
    W.api("PUT", "/api/v1/workflows/%s" % WORKFLOW_ID, {
        "name": body["name"], "nodes": body["nodes"],
        "connections": body["connections"], "settings": body.get("settings", {})})
    print("restored %s from %s (%d nodes)" % (WORKFLOW_ID, SNAPSHOT, len(body["nodes"])))
    print("MEMORY_EPOCH in n8n_whatsapp.py still says %d; the restored key is -%d. "
          "Put the repo back too (git revert)." % (W.MEMORY_EPOCH, OLD_EPOCH))


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv
    W.check_memory_epoch(prompt=W.system_prompt(), inject=U.AGENT_NEW, tools=W.tools_text())
    later = False                              # the key is always this script's to move one up

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    if "Conversation so far" not in by:
        sys.exit("No 'Conversation so far' node on the live workflow -- refusing to guess.")
    if snapshot(live):
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
