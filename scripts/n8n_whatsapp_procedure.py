# -*- coding: utf-8 -*-
"""A request for a manager: the reason is the answer, never the same question twice (18 Oct, late).

    python scripts/n8n_whatsapp_procedure.py            # dry run
    python scripts/n8n_whatsapp_procedure.py --dump F   # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_procedure.py --apply    # write it
    python scripts/n8n_whatsapp_procedure.py --restore  # put the snapshot back

WHY. The owner's handset after epoch 81, 15:05-15:08 UTC (executions 112601-112635):
he asked for a manager five times, in Hebrew and in English, and got "what is it
about?" five times, shorter each time; "are you the manager?" got "מצוות השירות של
הומי'ז. אני כאן...". The owner: "this is like frustrating like a parrot it should be
like i understand you i order for me to do that blah blah blah its the procedure we
need to get information before we can do something".
  - The first drafts said that. `echo` and `clerk` (27 Sep) sent them back, the note
    said "just ask", and the second pass was the bare question every time.
  - The model answered "are you the manager?" with "אני מיכאל מצוות השירות של הומי'ז";
    Send's name step took "אני מיכאל" as a re-introduction and left the rest.

WHAT CHANGES, in one write. Each text is owned elsewhere; this only carries them:
  Answer the resident   the prompt (prompt.md): Michael shows he understands, says in
                        his own words that before anything goes to a manager someone
                        has to know what it is about, never asks the same question in
                        the same words twice, and notes nothing without the matter.
  notify_team           its description (n8n_whatsapp.py TOOLS), the same.
  Reply usable?         `echo` and `clerk` pass in a chat about a manager or a person
                        (retry.MGR_CTX, built into manners.py's guards).
  Try again             names neither there, and its unnamed list drops both (retry.py).
  Send                  the greeting filter, manners v4: "are you the manager?" keeps
                        the name; a cut takes "מצוות השירות של הומי'ז" with it.
  Team note this turn?  the backstop reads sentence by sentence (teamnote.SAID): the
                        procedure's conditions are not reports. 103 notes over every
                        past reply, the same 103 as before.
  Conversation so far   MEMORY_EPOCH 81 -> 82: the owner's buffer holds the question
                        four times, ready to be copied back.

A field is rewritten only when its live text is the one this replaces (by hash);
anything else means it changed since, and this refuses. A later epoch owns the prompt
and the key: then this carries only what it alone owns.

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
import n8n_whatsapp_manners as M  # noqa: E402
import n8n_whatsapp_teamnote as TN  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-18oct-before-procedure.json")
PLACEHOLDER = NP.PLACEHOLDER
OLD_EPOCH = 81
OLD_PROMPT = "961e2b20119a"     # EPOCH_COVERS["prompt"] at epoch 81
OLD_NOTIFY = "5656de378175"     # notify_team's live toolDescription before this
OLD_ECHO = "eaeeecb7074c"       # Reply usable?'s `echo` before this
OLD_CLERK = "42a36eae20e6"      # Reply usable?'s `clerk` before this
OLD_TRY = "34174ed0c761"        # Try again's live jsonOutput before this (the pin)
OLD_NOTE = "fb7af852e2cd"       # Team note this turn?'s live leftValue before this
OLD_FILTER = "4d07e28031fe"     # Send's greeting filter block, manners v3
MEMORY_KEY = "={{ $json.to }}-%d"
NL = chr(10)
KEPT = ("ההסבר הוא חלק מהתשובה", "ולא חוזר על אותה שאלה באותן מילים", "בקשה ריקה לא נרשמת")
GONE = ("ומי שגם אחרי שאלה שנייה לא רוצה לפרט לא נשאל שוב",
        "עד שיש לך את הפרטים, השיחה היא על העניין שלו")
NOTIFY_KEPT = ("never the same question in the same words",
               "a request with nothing in it is never a note")
NOTIFY_GONE = ("call it with what you have",)

COMPILE_JS = ("const fs = require('fs'); const xs = JSON.parse(fs.readFileSync(0, 'utf8')); "
              "const bad = []; for (const [k, e] of xs) { try { new Function('$json', '$', "
              "'$runIndex', 'return (' + e + ');'); } catch (err) { bad.push(k + ': ' + err.message); } } "
              "console.log(JSON.stringify(bad));")


def node_of(by, name):
    if name not in by:
        sys.exit("No %r node on the live workflow -- refusing to guess." % name)
    return by[name]


def by_id(conds, cid, where):
    hits = [c for c in conds if c.get("id") == cid]
    if len(hits) != 1:
        sys.exit("REFUSING: %r has %d conditions with id %r." % (where, len(hits), cid))
    return hits[0]


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
    print("MEMORY_EPOCH in n8n_whatsapp.py still says %d, and retry.py, manners.py and "
          "teamnote.py carry this change; put the repo back too (git revert)." % W.MEMORY_EPOCH)


def replace_field(have, want, old_hash, what, olds, news, changes, why):
    """`want` when `have` is the text this replaces, None when it is already `want`."""
    if have == want:
        return None
    if W.epoch_hash(have) != old_hash:
        sys.exit("REFUSING: %s is %s, neither the one this replaces (%s) nor the new one (%s)."
                 % (what, W.epoch_hash(have), old_hash, W.epoch_hash(want)))
    olds.append(have)
    news.append(want)
    changes.append("%s: %s -> %s (%s)" % (what, old_hash, W.epoch_hash(want), why))
    return want


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
        bad = [k for k in KEPT if k not in prompt] + [g for g in GONE if g in prompt]
        bad += [k for k in NOTIFY_KEPT if k not in notify.lower()]
        bad += [g for g in NOTIFY_GONE if g in notify.lower()]
        if bad:
            sys.exit("REFUSING: prompt.md / notify_team do not read as this change: %s" % bad)
    if M.MARK != "const mv = 'manners v4';":
        sys.exit("REFUSING: manners.py is not v4 (%r)." % M.MARK)
    send_new = M.FILTER + M.BLOCK_END
    for k, v in (("echo", M.ECHO_GUARD["leftValue"]), ("clerk", M.CLERK_GUARD["leftValue"]),
                 ("Try again", R.TRY_JSON), ("teamnote", TN.NOTE_THIS_TURN)):
        if v.count("}}") != 1:
            sys.exit("REFUSING: a }} inside %s would end its expression early." % k)
    broken = compiles([("echo", M.ECHO_GUARD["leftValue"]), ("clerk", M.CLERK_GUARD["leftValue"]),
                       ("Try again", R.TRY_JSON), ("teamnote", TN.NOTE_THIS_TURN)])
    if broken:
        sys.exit("REFUSING: does not parse: %s" % broken)

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in ("Answer the resident", "Conversation so far", "notify_team", "Reply usable?",
                 "Try again", "Send", TN.IF_NODE, "Anything newer?", "Still the last word?"):
        node_of(by, need)

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    before_layout = layout_complaints(nodes)
    changes, olds, news = [], [], []

    # The prompt and notify_team's text: by hash, the way MEMORY_EPOCH covers them.
    if not later:
        agent = by["Answer the resident"]["parameters"].setdefault("options", {})
        got = replace_field(agent.get("systemMessage") or "", prompt, OLD_PROMPT,
                            "Answer the resident: prompt", olds, news, changes,
                            "the reason is the answer, never the same question twice")
        if got is not None:
            agent["systemMessage"] = got
        tp = by["notify_team"]["parameters"]
        got = replace_field(tp.get("toolDescription") or "", notify, OLD_NOTIFY,
                            "notify_team: description", olds, news, changes,
                            "the same, and never an empty note")
        if got is not None:
            tp["toolDescription"] = got

    # Reply usable?: `echo` and `clerk` pass in a chat about a manager.
    cond = by["Reply usable?"]["parameters"]["conditions"]["conditions"]
    for g, old in ((M.ECHO_GUARD, OLD_ECHO), (M.CLERK_GUARD, OLD_CLERK)):
        mine = by_id(cond, g["id"], "Reply usable?")
        got = replace_field(mine.get("leftValue") or "", g["leftValue"], old,
                            "Reply usable?: `%s`" % g["id"], olds, news, changes,
                            "passes in a chat about a manager or a person")
        if got is not None:
            mine["leftValue"] = got

    # Try again: names neither there.
    tp = by["Try again"]["parameters"]
    got = replace_field(tp.get("jsonOutput") or "", R.TRY_JSON, OLD_TRY, "Try again: note",
                        olds, news, changes, "names neither the echo nor the clerk in a chat "
                        "about a manager")
    if got is not None:
        tp["jsonOutput"] = got

    # Send: the greeting filter, v3 -> v4, by its block.
    sp = by["Send"]["parameters"]
    body = sp.get("jsonBody") or ""
    if body.count(M.BLOCK_START) != 1:
        sys.exit("REFUSING: Send carries %d greeting filters." % body.count(M.BLOCK_START))
    a = body.index(M.BLOCK_START)
    z = body.index(M.BLOCK_END, a) + len(M.BLOCK_END)
    got = replace_field(body[a:z], send_new, OLD_FILTER, "Send: greeting filter", olds, news,
                        changes, "manners v4: \"are you the manager?\" keeps the name; no fragment")
    if got is not None:
        sp["jsonBody"] = body[:a] + got + body[z:]
        if sp["jsonBody"].count("}}") != 1:
            sys.exit("REFUSING: the new Send body has %d '}}'." % sp["jsonBody"].count("}}"))

    # Team note this turn?: sentence by sentence.
    tc = by_id(by[TN.IF_NODE]["parameters"]["conditions"]["conditions"], "teamnote", TN.IF_NODE)
    got = replace_field(tc.get("leftValue") or "", TN.NOTE_THIS_TURN, OLD_NOTE,
                        "%s: backstop" % TN.IF_NODE, olds, news, changes,
                        "sentence by sentence; the procedure's conditions are not reports")
    if got is not None:
        tc["leftValue"] = got

    # The memory: the owner's buffer holds the question four times.
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
           if not k.startswith(("n8n_whatsapp_procedure.", "n8n_whatsapp_retry.",
                                "n8n_whatsapp_manners.", "n8n_whatsapp_teamnote."))}
    old_all, new_all = NL.join(olds), NL.join(news)
    lost = [k for k, v in sib.items() if v in old_all and v not in new_all]
    if lost:
        sys.exit("REFUSING: the edit would break other patchers' anchors: %s" % lost)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("checks   : prompt %s, notify_team %s, echo %s, clerk %s, Try again %s, Send %s, "
          "backstop %s, epoch %d, %d sibling anchors intact"
          % (W.epoch_hash(prompt), W.epoch_hash(notify), W.epoch_hash(M.ECHO_GUARD["leftValue"]),
             W.epoch_hash(M.CLERK_GUARD["leftValue"]), W.epoch_hash(R.TRY_JSON),
             W.epoch_hash(send_new), W.epoch_hash(TN.NOTE_THIS_TURN), W.MEMORY_EPOCH,
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
    gb = {c["id"]: c["leftValue"] for c in bb["Reply usable?"]["parameters"]["conditions"]["conditions"]}
    print("")
    print("written: %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  prompt %s (want %s); memory key %s" % (
        W.epoch_hash(bb["Answer the resident"]["parameters"]["options"]["systemMessage"]),
        W.epoch_hash(prompt), bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("  notify_team %s (want %s)" % (W.epoch_hash(bb["notify_team"]["parameters"]["toolDescription"]),
                                         W.epoch_hash(notify)))
    print("  echo %s, clerk %s (want %s, %s)" % (W.epoch_hash(gb["echo"]), W.epoch_hash(gb["clerk"]),
                                                W.epoch_hash(M.ECHO_GUARD["leftValue"]),
                                                W.epoch_hash(M.CLERK_GUARD["leftValue"])))
    print("  Try again %s (want %s)" % (W.epoch_hash(bb["Try again"]["parameters"]["jsonOutput"]),
                                       W.epoch_hash(R.TRY_JSON)))
    print("  Send carries manners v4: %s" % (M.MARK in bb["Send"]["parameters"]["jsonBody"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
