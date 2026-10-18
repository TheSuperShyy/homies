# -*- coding: utf-8 -*-
"""A request for a manager: help first, then the details, then the team note (18 Oct).

    python scripts/n8n_whatsapp_askfirst.py            # dry run
    python scripts/n8n_whatsapp_askfirst.py --dump F   # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_askfirst.py --apply    # write it
    python scripts/n8n_whatsapp_askfirst.py --restore  # put the 18 Oct snapshot back

WHY, 18 Oct. The owner, passing on an instruction: when somebody asks for a
manager or for the team, the first message is "I'm here to help you"; if he
still wants a manager, the second asks what exactly he needs and what the
situation is ("I will try to help you, or I will send it to the team or the
manager"); "we need to get the information before we open a ticket with the
team". Until now a request for a person was noted at once, and the team read
"wants a person" and nothing else. prompt.md's "18 Oct" section has the rest.

WHAT CHANGES, in one write:
  Answer the resident     the prompt, by hash (prompt.md, the System prompt section).
  notify_team             its description (n8n_whatsapp.py TOOLS): a request for a
                          manager is not a reason by itself; call with the details.
  Team note this turn?    the backstop (teamnote.SAID): an offer or a condition in
                          front of the verb ("כדי שאוכל ... או להעביר", "ואם לא,
                          אדאג להעביר") is not "the team knows". Without it the
                          second message would note an empty request.
  Conversation so far     MEMORY_EPOCH 78 -> 79: buffers hold requests noted at once.

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
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_untemplate as U  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
import n8n_whatsapp_teamnote as TN  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-18oct-before-askfirst.json")
PLACEHOLDER = NP.PLACEHOLDER
OLD_EPOCH = 78
OLD_PROMPT = "c7a5ce8a699e"     # EPOCH_COVERS["prompt"] at epoch 78
OLD_NOTIFY = "07473096b3a9"     # notify_team's live toolDescription before this
OLD_NOTE = "86e8eea35e9d"       # Team note this turn?'s live leftValue before this
MEMORY_KEY = "={{ $json.to }}-%d"
NL = chr(10)

# The prompt must hold the new fragments and none of the old ones, or this refuses.
GONE = ("ענייני ועד הבית, בקשה לדבר עם בן אדם, וכל דבר אחר",
        "אתה מעביר להם את הפנייה, ושואל מה מתאים לו",
        "והבקשה נרשמת לצוות כמו כל בקשה כזאת")
KEPT = ("אתה העוזר הדיגיטלי בצוות השירות של הומי'ז",
        "וזה הולך כמו כל בקשה כזאת, שעליה כתוב בהמשך",
        "שאתה כאן כדי לעזור לו, ומזמין אותו לספר במה מדובר",
        "אתה שואל מה בדיוק הוא צריך מהם ומה המצב",
        "לצוות רושמים אחרי שיש לך את הפרטים",
        "ומי שגם אז לא רוצה לפרט לא נשאל שוב")
NOTIFY_GONE = ("a request to speak with a person",
               "first; the ask itself is the reason to call")
NOTIFY_KEPT = ("a request for a manager or a person is not one of these yet",
               "if they will not say, call it with what you have")
NOTE_KEPT = ("(אשמח|אוכל|יכול|יכולה|אפשר|כדי|נוכל|אנסה|ננסה|או)( [א-ת]+)? (להעביר|לעדכן|לרשום|למסור)",
             "אם לא[^.!?]{0,40}")

COMPILE_JS = ("const fs = require('fs'); const xs = JSON.parse(fs.readFileSync(0, 'utf8')); "
              "const bad = []; for (const [k, e] of xs) { try { new Function('$json', '$', "
              "'$runIndex', 'return (' + e + ');'); } catch (err) { bad.push(k + ': ' + err.message); } } "
              "console.log(JSON.stringify(bad));")


def node_of(by, name):
    if name not in by:
        sys.exit("No %r node on the live workflow -- refusing to guess." % name)
    return by[name]


def note_condition(by):
    conds = node_of(by, TN.IF_NODE)["parameters"]["conditions"]["conditions"]
    hits = [c for c in conds if c.get("id") == "teamnote"]
    if len(hits) != 1:
        sys.exit("REFUSING: %r has %d conditions with id 'teamnote'." % (TN.IF_NODE, len(hits)))
    return hits[0]


def compiles(expr):
    """The backstop parses as JavaScript, the way n8n will read it."""
    import check_whatsapp_rules as C
    xs = [["teamnote", C.inner(expr)]]
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
    print("MEMORY_EPOCH in n8n_whatsapp.py still says %d; the restored key is -%d and the "
          "prompt is %s. Put the repo back too (git revert)." % (W.MEMORY_EPOCH, OLD_EPOCH, OLD_PROMPT))


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    prompt = W.system_prompt()
    notify = W.tool("notify_team")["description"]
    note = TN.NOTE_THIS_TURN
    W.check_memory_epoch(prompt=prompt, inject=U.AGENT_NEW, tools=W.tools_text())
    if W.MEMORY_EPOCH < OLD_EPOCH + 1:
        sys.exit("REFUSING: MEMORY_EPOCH is %d; this change was written for %d -> %d."
                 % (W.MEMORY_EPOCH, OLD_EPOCH, OLD_EPOCH + 1))
    later = W.MEMORY_EPOCH > OLD_EPOCH + 1     # a later change owns the prompt and the key
    if not later:
        bad = [g for g in GONE if g in prompt] + [k for k in KEPT if k not in prompt]
        bad += [g for g in NOTIFY_GONE if g in notify.lower()]
        bad += [k for k in NOTIFY_KEPT if k not in notify.lower()]
        bad += [k for k in NOTE_KEPT if k not in note]
        if bad:
            sys.exit("REFUSING: prompt.md / notify_team / teamnote.SAID do not read as this "
                     "change: %s" % bad)
    broken = compiles(note)
    if broken:
        sys.exit("REFUSING: the new backstop does not parse: %s" % broken)

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in ("Answer the resident", "Conversation so far", "notify_team", TN.IF_NODE):
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
        changes.append("Answer the resident: prompt %s -> %s (a request for a manager: help "
                       "first, then what exactly and the situation, the note with the details)"
                       % (OLD_PROMPT, W.epoch_hash(prompt)))

    # notify_team: the request alone is not a reason; call it with the details.
    tp = by["notify_team"]["parameters"]
    have = tp.get("toolDescription") or ""
    if not later and have != notify:
        if W.epoch_hash(have) != OLD_NOTIFY:
            sys.exit("REFUSING: notify_team's description is %s, neither the one this replaces "
                     "(%s) nor the new one (%s)." % (W.epoch_hash(have), OLD_NOTIFY, W.epoch_hash(notify)))
        tp["toolDescription"] = notify
        olds.append(have)
        news.append(notify)
        changes.append("notify_team: description %s -> %s (a request for a manager waits for "
                       "the details)" % (OLD_NOTIFY, W.epoch_hash(notify)))

    # Team note this turn?: an offer or a condition is not "the team knows".
    cond = note_condition(by)
    have = cond.get("leftValue") or ""
    if have != note:
        if W.epoch_hash(have) != OLD_NOTE:
            sys.exit("REFUSING: the team-note backstop is %s, neither the one this replaces (%s) "
                     "nor the new one (%s)." % (W.epoch_hash(have), OLD_NOTE, W.epoch_hash(note)))
        cond["leftValue"] = note
        olds.append(have)
        news.append(note)
        changes.append("%s: backstop %s -> %s (an offer or a condition in front of the verb "
                       "is not a report)" % (TN.IF_NODE, OLD_NOTE, W.epoch_hash(note)))

    # The memory: every buffer holds requests noted at once.
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
    sib = {k: v for k, v in sib.items() if not k.startswith("n8n_whatsapp_askfirst.")}
    old_all, new_all = NL.join(olds), NL.join(news)
    lost = [k for k, v in sib.items() if v in old_all and v not in new_all]
    if lost:
        sys.exit("REFUSING: the edit would break other patchers' anchors: %s" % lost)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("checks   : prompt %s, notify_team %s, backstop %s, epoch %d, %d sibling anchors intact"
          % (W.epoch_hash(prompt), W.epoch_hash(notify), W.epoch_hash(note), W.MEMORY_EPOCH,
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
    print("  prompt %s (want %s); notify_team %s (want %s); backstop %s (want %s); memory key %s" % (
        W.epoch_hash(bb["Answer the resident"]["parameters"]["options"]["systemMessage"]),
        W.epoch_hash(prompt),
        W.epoch_hash(bb["notify_team"]["parameters"].get("toolDescription") or ""),
        W.epoch_hash(notify),
        W.epoch_hash(note_condition(bb).get("leftValue") or ""), W.epoch_hash(note),
        bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
