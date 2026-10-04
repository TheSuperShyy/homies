# -*- coding: utf-8 -*-
"""A caring word, not an irritated one: the short reaction before the question, 4 Oct.

    python scripts/n8n_whatsapp_calmword.py            # dry run
    python scripts/n8n_whatsapp_calmword.py --dump F   # dry run, plus the would-be workflow in F
                                                       # (check_whatsapp_rules.py --candidate F,
                                                       #  check_patchers_idle.py F,
                                                       #  wa_qa.py bundle --candidate F)
    python scripts/n8n_whatsapp_calmword.py --apply    # write it
    python scripts/n8n_whatsapp_calmword.py --restore  # put the 4 Oct evening snapshot back

WHY, 4 Oct evening. The owner read 15 Claude-played conversations, one per
resident, across the three menu buttons
(docs/assistant/transcripts/2026-10-04-whatsapp-menu-buttons.md) and wrote:
*"can we edit the ugh how annoying remarks it does not fit the chatbot at all"*.
The bot opened its reply with "איזה מעצבן" in 6 of the 15 and once with "אוף,
איזה מעצבן". Both came from the prompt, which listed "איזה מעצבן" among its
examples of the short word before the question and asked for a fault to get a
reaction "כמו שחבר היה מגיב" (the way a friend would react).

WHAT CHANGES, in one write. The text is owned by prompt.md; this only carries it:
  - The prompt (docs/features/11-whatsapp-bot/prompt.md): a fault gets "תגובה קצרה
    ואכפתית של בן אדם לדבר עצמו" (a short, caring human reaction to the thing
    itself), and the example list reads "אוקיי", "אין בעיה", "אוי, לא נעים". Nothing
    is banned: the 17 Sep note in HANDOVER.md says a ban on the opening word
    fought the rule that asks for one, and lost. MEMORY_EPOCH 72 -> 73: every
    buffer holds replies that open with "איזה מעצבן", and an example beats a rule.

WHAT IT DOES NOT TOUCH. Send, the guards, Try again, the menu, Sort, the inject,
the tools, the small writers (ack, rescue, outage), the voice agents.

A field is rewritten only when its live text is the one this replaces. Anything
else means it was changed since, and this refuses.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, `check_patchers_idle.py F`, the
Claude-played replay, the owner's go, `--apply`, the check again on live, and
every WhatsApp patcher's dry run idle.
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
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-04oct-before-calmword.json")
PLACEHOLDER = NP.PLACEHOLDER
OLD_EPOCH = 72
OLD_PROMPT = "c056ecfc373b"     # EPOCH_COVERS["prompt"] at epoch 72
MEMORY_KEY = "={{ $json.to }}-%d"
NL = chr(10)

# The two edits, as they read before and after. The new prompt must hold the
# new fragments and neither old one, or this refuses.
GONE = ("כמו שחבר היה מגיב", "\"איזה מעצבן\"")
KEPT = ("תגובה קצרה ואכפתית של בן אדם לדבר עצמו", "\"אוקיי\", \"אין בעיה\", \"אוי, לא נעים\"")


def node_of(by, name):
    if name not in by:
        sys.exit("No %r node on the live workflow -- refusing to guess." % name)
    return by[name]


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
    print("MEMORY_EPOCH in n8n_whatsapp.py still says %d; the restored key is -%d and the "
          "prompt is %s. Put the repo back too (git revert)." % (W.MEMORY_EPOCH, OLD_EPOCH, OLD_PROMPT))


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    prompt = W.system_prompt()
    W.check_memory_epoch(prompt=prompt, inject=U.AGENT_NEW, tools=W.tools_text())
    if W.MEMORY_EPOCH < OLD_EPOCH + 1:
        sys.exit("REFUSING: MEMORY_EPOCH is %d; this change was written for %d -> %d."
                 % (W.MEMORY_EPOCH, OLD_EPOCH, OLD_EPOCH + 1))
    later = W.MEMORY_EPOCH > OLD_EPOCH + 1     # a later change owns the prompt and the key
    if not later:
        bad = [g for g in GONE if g in prompt] + [k for k in KEPT if k not in prompt]
        if bad:
            sys.exit("REFUSING: prompt.md does not read as this change: %s" % bad)

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in ("Answer the resident", "Conversation so far"):
        node_of(by, need)

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    before_layout = layout_complaints(nodes)
    changes, olds, news = [], [], []

    # The prompt: by hash, the way MEMORY_EPOCH covers it.
    agent = by["Answer the resident"]["parameters"].setdefault("options", {})
    have = agent.get("systemMessage") or ""
    if not later and have != prompt:
        if W.epoch_hash(have) != OLD_PROMPT:
            sys.exit("REFUSING: the live prompt is %s, neither the one this replaces (%s) "
                     "nor the new one (%s)." % (W.epoch_hash(have), OLD_PROMPT, W.epoch_hash(prompt)))
        agent["systemMessage"] = prompt
        olds.append(have)
        news.append(prompt)
        changes.append("Answer the resident: prompt %s -> %s (a short, caring word before the "
                       "question; the example \"איזה מעצבן\" is now \"אוי, לא נעים\")"
                       % (OLD_PROMPT, W.epoch_hash(prompt)))

    # The memory: every buffer holds replies that open with "איזה מעצבן".
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

    sib = NP.siblings()
    sib = {k: v for k, v in sib.items() if not k.startswith("n8n_whatsapp_calmword.")}
    old_all, new_all = NL.join(olds), NL.join(news)
    lost = [k for k, v in sib.items() if v in old_all and v not in new_all]
    if lost:
        sys.exit("REFUSING: the edit would break other patchers' anchors: %s" % lost)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("checks   : prompt hash %s, epoch %d, %d sibling anchors intact"
          % (W.epoch_hash(prompt), W.MEMORY_EPOCH, sum(1 for v in sib.values() if v in old_all)))
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
        sys.exit("REFUSING TO PATCH. This would introduce placement problems "
                 "that are not already there:" + NL + "    " + (NL + "    ").join(worse))

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
    print("  prompt %s (want %s); memory key %s" % (
        W.epoch_hash(bb["Answer the resident"]["parameters"]["options"]["systemMessage"]),
        W.epoch_hash(prompt), bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
