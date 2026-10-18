# -*- coding: utf-8 -*-
"""A request for a manager, answered like a person at a service desk (18 Oct, later).

    python scripts/n8n_whatsapp_hearyou.py            # dry run
    python scripts/n8n_whatsapp_hearyou.py --dump F   # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_hearyou.py --apply    # write it
    python scripts/n8n_whatsapp_hearyou.py --restore  # put the snapshot back

WHY. The owner, on the first version's test chat (n8n_whatsapp_askfirst.py, epoch
79: "אנסה קודם לעזור בעצמי, ואם לא אוכל, אעביר את זה למנהל"): "no not like that i
want it to be natural like a call center but human like yes i hear you can i get
some details and stuff like lowkey trying to fix everything by yourself before
following up and sending it to the team". The 79 passage told Michael what to
SAY (that he is here to help; that he will try, and if not, pass it on), and the
model said it nearly word for word. Now the passage describes the person: he
shows he heard, asks naturally for the details as someone who means to handle it,
talks about the matter and not about who will handle it, tries to close it with
his tools, and notes only what is really past him, with the details.

WHAT CHANGES, in one write:
  Answer the resident   the prompt, by hash (prompt.md, the System prompt section).
  notify_team           its description (n8n_whatsapp.py TOOLS), worded the same way.
  Conversation so far   MEMORY_EPOCH 79 -> 80: buffers hold the 79 wording.
The team-note backstop of 79 (an offer is not a report) stays as it is.

A field is rewritten only when its live text is the one this replaces (by
hash); anything else means it changed since, and this refuses. A later epoch
owns the prompt and the key: then this is idle.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, `check_patchers_idle.py F`, a
Claude-played replay of the inputs that reach the model (never OpenRouter), the
new pins, `--apply`, the check on live, every patcher idle, `--watch`.
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
                        "n8n-whatsapp-live-18oct-before-hearyou.json")
PLACEHOLDER = NP.PLACEHOLDER
OLD_EPOCH = 79
OLD_PROMPT = "1b6624a458d8"     # EPOCH_COVERS["prompt"] at epoch 79
OLD_NOTIFY = "76838431c158"     # notify_team's live toolDescription at epoch 79
MEMORY_KEY = "={{ $json.to }}-%d"
NL = chr(10)

# The prompt must hold the new fragments and none of the old ones, or this refuses.
GONE = ("שאתה כאן כדי לעזור לו, ומזמין אותו לספר במה מדובר",
        "ואומר לו שתנסה לעזור בעצמך, ואם לא תוכל, תעביר את זה לצוות או למנהל")
KEPT = ("כמו נציג טוב במוקד שירות, אנושי ולא טופס",
        "מראה לו ששמעת אותו, ומבקש בטבעיות את הפרטים",
        "עד שיש לך את הפרטים, השיחה היא על העניין שלו, לא על מי יטפל בו",
        "ומי שגם אחרי שאלה שנייה לא רוצה לפרט לא נשאל שוב",
        "וזה הולך כמו כל בקשה כזאת, שעליה כתוב בהמשך")
NOTIFY_GONE = ("first say you are here to help",)
NOTIFY_KEPT = ("show you heard them and ask for the details",
               "call it only for what is really past you")


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
    notify = W.tool("notify_team")["description"]
    W.check_memory_epoch(prompt=prompt, inject=U.AGENT_NEW, tools=W.tools_text())
    if W.MEMORY_EPOCH < OLD_EPOCH + 1:
        sys.exit("REFUSING: MEMORY_EPOCH is %d; this change was written for %d -> %d."
                 % (W.MEMORY_EPOCH, OLD_EPOCH, OLD_EPOCH + 1))
    later = W.MEMORY_EPOCH > OLD_EPOCH + 1     # a later change owns the prompt and the key
    if not later:
        bad = [g for g in GONE if g in prompt] + [k for k in KEPT if k not in prompt]
        bad += [g for g in NOTIFY_GONE if g in notify.lower()]
        bad += [k for k in NOTIFY_KEPT if k not in notify.lower()]
        if bad:
            sys.exit("REFUSING: prompt.md / notify_team do not read as this change: %s" % bad)

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in ("Answer the resident", "Conversation so far", "notify_team"):
        node_of(by, need)

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    before_layout = layout_complaints(nodes)
    changes, olds, news = [], [], []

    agent = by["Answer the resident"]["parameters"].setdefault("options", {})
    have = agent.get("systemMessage") or ""
    if not later and have != prompt:
        if W.epoch_hash(have) != OLD_PROMPT:
            sys.exit("REFUSING: the live prompt is %s, neither the one this replaces (%s) "
                     "nor the new one (%s)." % (W.epoch_hash(have), OLD_PROMPT, W.epoch_hash(prompt)))
        agent["systemMessage"] = prompt
        olds.append(have)
        news.append(prompt)
        changes.append("Answer the resident: prompt %s -> %s (a request for a manager, answered "
                       "like a person at a service desk)" % (OLD_PROMPT, W.epoch_hash(prompt)))

    tp = by["notify_team"]["parameters"]
    have = tp.get("toolDescription") or ""
    if not later and have != notify:
        if W.epoch_hash(have) != OLD_NOTIFY:
            sys.exit("REFUSING: notify_team's description is %s, neither the one this replaces "
                     "(%s) nor the new one (%s)." % (W.epoch_hash(have), OLD_NOTIFY, W.epoch_hash(notify)))
        tp["toolDescription"] = notify
        olds.append(have)
        news.append(notify)
        changes.append("notify_team: description %s -> %s (the same, worded as a service rep "
                       "would)" % (OLD_NOTIFY, W.epoch_hash(notify)))

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
    sib = {k: v for k, v in sib.items() if not k.startswith("n8n_whatsapp_hearyou.")}
    old_all, new_all = NL.join(olds), NL.join(news)
    lost = [k for k, v in sib.items() if v in old_all and v not in new_all]
    if lost:
        sys.exit("REFUSING: the edit would break other patchers' anchors: %s" % lost)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("checks   : prompt %s, notify_team %s, epoch %d, %d sibling anchors intact"
          % (W.epoch_hash(prompt), W.epoch_hash(notify), W.MEMORY_EPOCH,
             sum(1 for v in sib.values() if v in old_all)))
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
    print("  prompt %s (want %s); notify_team %s (want %s); memory key %s" % (
        W.epoch_hash(bb["Answer the resident"]["parameters"]["options"]["systemMessage"]),
        W.epoch_hash(prompt),
        W.epoch_hash(bb["notify_team"]["parameters"].get("toolDescription") or ""),
        W.epoch_hash(notify), bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
