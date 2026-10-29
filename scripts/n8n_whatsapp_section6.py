# -*- coding: utf-8 -*-
"""The sandbox's version of the WhatsApp bot, put on the live bot (29 Oct 2026).

    python scripts/n8n_whatsapp_section6.py              # dry run
    python scripts/n8n_whatsapp_section6.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_section6.py --apply      # write it
    python scripts/n8n_whatsapp_section6.py --restore    # put the snapshot back

WHY. The owner, 29 Oct, 15:08 UTC, after testing the sandbox by hand: "ok so right now i think we
can replace the old chatbot with the new version since i tested it out and it sounds good".

WHAT CHANGES, in one write. The live bot goes through the same section6() the sandbox runs
(scripts/n8n_sandbox_section6.py), so every text a model reads on live is the one tested there,
and the same nodes are added:
  A. no representative button (Sort, Send); a typed request for a person is the manager protocol;
  B. "Who is writing?" + "Add who": the sender recognised from `residents`; a ticket names its
     place and flat; the balance takes the sender (debt-tools v134, live since 15:2x UTC);
  C. the manager protocol: management told at once, the matter asked for warmly and then
     handled by the bot, and noted;
  (D, one reply per burst, is NOT carried: its check reads the conversation through the sandbox's
     Chatwoot fetch node, and live reads `messages` in Supabase. It needs a live version of its own.)
  E. no claim that the team is acting;
  F. money answered from the system; a claimed payment confirmed, checked against the record,
     and proof asked for "so we can verify it";
  and the team is "we" in every text (WE_EDITS).
Plus the memory: epoch 84 -> 85, because every live buffer teaches the old behaviour.

AFTER THIS, THE REPO'S SOURCES ARE BEHIND LIVE. prompt.md gets the new prompt, but the tool
descriptions in n8n_whatsapp.py's TOOLS, Sort's and Send's code there, and the two new nodes are
not folded into the builder yet. EPOCH_COVERS["tools"] holds the new live hash, so every older
patcher refuses at W.check_memory_epoch() until the fold is done. Fold them before any other
WhatsApp change.

The snapshot is in local/ (ignored by git), with the webhook secret replaced as the older ones were.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, the new pins, `--apply`, the check on live,
the owner's handset, `--watch`.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_sandbox_section6 import section6  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
EPOCH = 85
OLD_KEY = "={{ $json.to }}-84"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-29oct-before-section6.json")
ADDED = ("Who is writing?", "Add who")


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
        text = text.replace(secret, NP.PLACEHOLDER)
    os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
    with open(SNAPSHOT, "w", encoding="utf-8") as f:
        f.write(text)
    return True


def restore():
    snap = json.load(open(SNAPSHOT, encoding="utf-8"))
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    if not secret:
        sys.exit("N8N_WEBHOOK_SECRET is not in .env; the snapshot's Sort node would "
                 "go live with a placeholder secret. Refusing.")
    body = json.loads(json.dumps(snap, ensure_ascii=False).replace(NP.PLACEHOLDER, secret))
    W.api("PUT", "/api/v1/workflows/%s" % WORKFLOW_ID, {
        "name": body["name"], "nodes": body["nodes"],
        "connections": body["connections"], "settings": body.get("settings", {})})
    print("restored %s from %s (%d nodes)" % (WORKFLOW_ID, SNAPSHOT, len(body["nodes"])))
    print("Put the repo back too: git revert the section 6 commit (MEMORY_EPOCH, EPOCH_COVERS, prompt.md, pins).")


def prompt_of(wf):
    return {n["name"]: n for n in wf["nodes"]}["Answer the resident"]["parameters"]["options"]["systemMessage"]


def tools_of(wf):
    """The five descriptions in TOOLS' order, read from a workflow, the way tools_text() joins them."""
    by = {n["name"]: n for n in wf["nodes"]}
    return "\n---\n".join(t["name"] + ": " + (by[t["name"]]["parameters"].get("toolDescription") or "")
                          for t in W.TOOLS)


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    if all(name in by for name in ADDED) and by["Conversation so far"]["parameters"].get("sessionKey") == NEW_KEY:
        print("Nothing to do. Live already carries section 6 and epoch %d." % EPOCH)
        return
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 84's. Read live first." % key)
    if any(name in by for name in ADDED):
        sys.exit("REFUSING: live already has some of the new nodes: %s" % [n for n in ADDED if n in by])

    supa = by["Anything newer?"]["credentials"]["httpHeaderAuth"]
    new = section6(live, supa, burst=False)
    nb = {n["name"]: n for n in new["nodes"]}
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d -> %d (added: %s)" % (len(live["nodes"]), len(new["nodes"]),
                                               ", ".join(n for n in ADDED if n in nb)))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("tools    : %s -> %s" % (W.epoch_hash(tools_of(live)), W.epoch_hash(tools_of(new))))
    print("memory   : %s -> %s (every buffer starts fresh)" % (OLD_KEY, NEW_KEY))
    changed = [n["name"] for n in new["nodes"] if n["name"] in by and n != by[n["name"]]]
    print("changed  : %s" % ", ".join(changed))

    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        NP.dump(new["nodes"], new["connections"], path)
        print("dumped   : %s (the would-be workflow, secret replaced)" % path)
    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": new["nodes"], "connections": new["connections"],
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    bb = {n["name"]: n for n in back["nodes"]}
    print("\nwritten  : %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  prompt %s (want %s); tools %s (want %s); memory key %s; new nodes present: %s"
          % (W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)), W.epoch_hash(tools_of(back)),
             W.epoch_hash(tools_of(new)), bb["Conversation so far"]["parameters"]["sessionKey"],
             all(n in bb for n in ADDED)))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
