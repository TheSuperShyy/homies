# -*- coding: utf-8 -*-
"""A typed request for a rep is not the tap: "how are you" nobody asked for (18 Oct, evening).

    python scripts/n8n_whatsapp_unasked.py            # dry run
    python scripts/n8n_whatsapp_unasked.py --dump F   # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_unasked.py --apply    # write it
    python scripts/n8n_whatsapp_unasked.py --restore  # put the snapshot back

WHY. The owner's handset, 14:21 UTC (executions 112521 and 112529): he typed "אני
רוצה לדבר עם מנהל" twice and got "מה שלומך היום? 😊" twice ("wth is this"). Gemini
wrote "היי, כאן מיכאל מהומי'ז. מה שלומך היום? 😊", the לדבר עם נציג tap's reply, for a
typed request; Send's greeting filter cut the hello and the name mid-conversation and
left the bare question. The Claude-played chats of epoch 80 never did this.

WHAT CHANGES, in one write. Each text is owned elsewhere; this only carries them:
  Answer the resident   the prompt (prompt.md): one sentence at the point of use -- a
                        typed request for a rep is not the tap; he already said what he
                        wants. MEMORY_EPOCH 80 -> 81: the owner's buffer holds the two
                        bad replies, ready to be copied back.
  Reply usable?         gains `unasked` (n8n_whatsapp_retry.py): off the tap, a reply
                        that asks how he is when he did not ask first goes back once,
                        first pass only. Over the 1,050 replies so far: exactly these two.
  Try again             (n8n_whatsapp_retry.py) names that reason when it is the one,
                        without the tools line.

NOT TOUCHED: Send, Sort, the inject, the tools, the other guards, the tap's own reply.

A field is rewritten only when its live text is the one this replaces (by hash);
anything else means it changed since, and this refuses. A later epoch owns the prompt
and the key: then this carries only the guard and the note.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, `check_patchers_idle.py F`, a
Claude-played replay of the inputs that reach the model (never OpenRouter), the new
pins, `--apply`, the check on live, every patcher idle, `--watch`.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_untemplate as U  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
import n8n_whatsapp_retry as R  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-18oct-before-unasked.json")
PLACEHOLDER = NP.PLACEHOLDER
OLD_EPOCH = 80
OLD_PROMPT = "ec350702a4ca"     # EPOCH_COVERS["prompt"] at epoch 80
OLD_TRY = "4f16fe9d3eb9"        # Try again's live jsonOutput before this (the pin)
MEMORY_KEY = "={{ $json.to }}-%d"
NL = chr(10)
KEPT = ("וגם כשהוא כותב שהוא רוצה נציג, זאת לא הלחיצה על הכפתור: הוא כבר אמר מה הוא רוצה, ומשם ממשיכים.",)

COMPILE_JS = ("const fs = require('fs'); const xs = JSON.parse(fs.readFileSync(0, 'utf8')); "
              "const bad = []; for (const [k, e] of xs) { try { new Function('$json', '$', "
              "'$runIndex', 'return (' + e + ');'); } catch (err) { bad.push(k + ': ' + err.message); } } "
              "console.log(JSON.stringify(bad));")


def node_of(by, name):
    if name not in by:
        sys.exit("No %r node on the live workflow -- refusing to guess." % name)
    return by[name]


def compiles(exprs):
    """Every changed expression parses as JavaScript, the way n8n will read it."""
    import check_whatsapp_rules as C
    xs = [[k, C.inner(v)] for k, v in exprs]
    r = subprocess.run(["node", "-e", COMPILE_JS], capture_output=True,
                       input=json.dumps(xs, ensure_ascii=False).encode("utf-8"))
    if r.returncode != 0:
        return ["node failed: " + r.stderr.decode("utf-8", "replace")[:300]]
    return json.loads(r.stdout.decode("utf-8"))


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
    print("MEMORY_EPOCH in n8n_whatsapp.py still says %d and retry.py carries `unasked`; "
          "put the repo back too (git revert)." % W.MEMORY_EPOCH)


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
        bad = [k for k in KEPT if k not in prompt]
        if bad:
            sys.exit("REFUSING: prompt.md does not read as this change: %s" % bad)
    if R.TRY_JSON.count("}}") != 1 or R.UNASKED.count("}}") != 1:
        sys.exit("REFUSING: a }} inside the note or the guard would end its expression early.")
    broken = compiles([("unasked", R.UNASKED), ("Try again", R.TRY_JSON)])
    if broken:
        sys.exit("REFUSING: does not parse: %s" % broken)

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in ("Answer the resident", "Conversation so far", "Reply usable?", "Try again",
                 "Sort", "Still the last word?"):
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
        changes.append("Answer the resident: prompt %s -> %s (a typed request for a rep is "
                       "not the tap)" % (OLD_PROMPT, W.epoch_hash(prompt)))

    # Reply usable?: the `unasked` guard, by id.
    cond = by["Reply usable?"]["parameters"]["conditions"]["conditions"]
    mine = next((c for c in cond if c.get("id") == "unasked"), None)
    if mine is None:
        cond.append(json.loads(json.dumps(R.UNASKED_GUARD)))
        news.append(R.UNASKED)
        changes.append("Reply usable?: `unasked` guard added (off the tap, a how-are-you he did "
                       "not ask for goes back once, first pass only)")
    elif mine.get("leftValue") != R.UNASKED:
        olds.append(mine.get("leftValue") or "")
        mine["leftValue"] = R.UNASKED
        news.append(R.UNASKED)
        changes.append("Reply usable?: `unasked` guard updated")

    # Try again: the note names it.
    tp = by["Try again"]["parameters"]
    have = tp.get("jsonOutput") or ""
    if have != R.TRY_JSON:
        if W.epoch_hash(have) != OLD_TRY:
            sys.exit("REFUSING: Try again's note is %s, neither the one this replaces (%s) nor "
                     "the new one (%s)." % (W.epoch_hash(have), OLD_TRY, W.epoch_hash(R.TRY_JSON)))
        tp["jsonOutput"] = R.TRY_JSON
        olds.append(have)
        news.append(R.TRY_JSON)
        changes.append("Try again: note %s -> %s (names a how-are-you he did not ask for)"
                       % (OLD_TRY, W.epoch_hash(R.TRY_JSON)))

    # The memory: the owner's buffer holds the two bad replies.
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
    sib = {k: v for k, v in sib.items()
           if not k.startswith(("n8n_whatsapp_unasked.", "n8n_whatsapp_retry."))}
    old_all, new_all = NL.join(olds), NL.join(news)
    lost = [k for k, v in sib.items() if v in old_all and v not in new_all]
    if lost:
        sys.exit("REFUSING: the edit would break other patchers' anchors: %s" % lost)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("checks   : prompt %s, unasked %s, Try again %s, epoch %d, %d sibling anchors intact"
          % (W.epoch_hash(prompt), W.epoch_hash(R.UNASKED), W.epoch_hash(R.TRY_JSON),
             W.MEMORY_EPOCH, sum(1 for v in sib.values() if v in old_all)))
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
    guards = [c["id"] for c in bb["Reply usable?"]["parameters"]["conditions"]["conditions"]]
    print("")
    print("written: %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  prompt %s (want %s); memory key %s" % (
        W.epoch_hash(bb["Answer the resident"]["parameters"]["options"]["systemMessage"]),
        W.epoch_hash(prompt), bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("  Reply usable? guards: %s" % ", ".join(guards))
    print("  Try again note %s (want %s)" % (W.epoch_hash(bb["Try again"]["parameters"]["jsonOutput"]),
                                             W.epoch_hash(R.TRY_JSON)))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
