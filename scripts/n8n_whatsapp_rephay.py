# -*- coding: utf-8 -*-
"""The representative asks how you are, and only that: the לדבר עם נציג tap, 4 Oct.

    python scripts/n8n_whatsapp_rephay.py            # dry run
    python scripts/n8n_whatsapp_rephay.py --dump F   # dry run, plus the would-be workflow in F
                                                     # (check_whatsapp_rules.py --candidate F,
                                                     #  check_patchers_idle.py F,
                                                     #  wa_qa.py bundle --candidate F)
    python scripts/n8n_whatsapp_rephay.py --apply    # write it
    python scripts/n8n_whatsapp_rephay.py --restore  # put the 4 Oct snapshot back

WHY, 4 Oct. The owner tapped לדבר עם נציג (execution 80740) and got "היי, אני מיכאל
מהומי'ז. במה אוכל לעזור לך?". The model had written "היי, בוקר טוב! אני מיכאל מהומי'ז.
במה אוכל לעזור לך?"; Send took the second greeting out, as designed, and the
how-are-you of 1 Oct (n8n_whatsapp_rephello.py) was never written. He asked again:
*"didnt i told you to make michael to be hi this is michael from homies how are you
doing today? something like that right?"*. The 1 Oct paragraph asked for two questions
in one short message, beside the one-question rule, and the model kept one of the two.
His own shape has one question.

WHAT CHANGES, in one write. Each text is owned elsewhere; this only carries them:
  - The prompt (docs/features/11-whatsapp-bot/prompt.md): on the tap, "היי", the
    name and how he is, and that is the only question; how to help after he
    answers. MEMORY_EPOCH 71 -> 72: every buffer holds tap replies that asked how
    to help first.
  - `Reply usable?` gains `rephay` (n8n_whatsapp_retry.py): on the tap's own turn, a
    reply with no how-are-you goes back once, first pass only.
  - `Try again` (n8n_whatsapp_retry.py) names that reason when it is the one, and
    leaves the tools line off a note about the tap alone.

WHAT IT DOES NOT TOUCH. Send and its greeting filter (manners v3 already keeps the
tap's one hello and the name), the menu, Sort, the inject, the tools, the other
guards, the other two buttons, the voice agents.

A field is rewritten only when its live text is the one this replaces. Anything else
means it was changed since, and this refuses.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, `check_patchers_idle.py F`, the
Claude-played replay (`wa_qa.py bundle --candidate F`), the owner's go, `--apply`,
the check again on live, and every WhatsApp patcher's dry run idle.
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
                        "n8n-whatsapp-live-04oct-before-rephay.json")
PLACEHOLDER = NP.PLACEHOLDER
OLD_EPOCH = 71
OLD_PROMPT = "98ada1b25f27"     # EPOCH_COVERS["prompt"] at epoch 71
OLD_TRY = "323688694803"        # Try again's jsonOutput before 4 Oct (the pin)
MEMORY_KEY = "={{ $json.to }}-%d"
NL = chr(10)

# Turns the new expressions must get right before any PUT, in Node:
# (reply, $runIndex, Sort's state, usable?).
TODAY = "היי, אני מיכאל מהומי'ז. במה אוכל לעזור לך?"         # execution 80740, as sent
WANTED = "היי, כאן מיכאל מהומי'ז! מה שלומך היום?"
GUARD_SMOKE = [
    (TODAY, 0, {"tap": "other"}, False),
    (WANTED, 0, {"tap": "other"}, True),
    ("Hi, this is Michael from Homies, how are you doing today?", 0, {"tap": "other"}, True),
    ("היי, כאן מיכאל מהומי'ז! איך את היום?", 0, {"tap": "other"}, True),
    (TODAY, 1, {"tap": "other"}, True),
    ("כאן מיכאל מהומי'ז, טוב שפנית. מה קרה?", 0, {"tap": "open"}, True),
    ("איזה מעצבן. באיזה בניין ובאיזו דירה?", 0, {}, True),
]

SMOKE_JS = """
const P = JSON.parse(require('fs').readFileSync(0, 'utf8'));
let g, t;
try {
  g = new Function('$json', '$runIndex', '$', 'return (' + P.guard + ');');
  t = new Function('$json', '$', 'return (' + P.tryj + ');');
} catch (e) { console.log(JSON.stringify({ error: 'does not compile: ' + e.message })); process.exit(0); }
const mk = (S) => () => ({ first: () => ({ json: S }) });
const bad = [];
P.cases.forEach(([o, ri, S, want], i) => {
  let got; try { got = g({ output: o }, ri, mk(S)); } catch (e) { got = 'THREW ' + e.message; }
  if (got !== want) bad.push('guard ' + i + ': got ' + got + ', want ' + want);
});
const note = (o, S) => JSON.parse(t({ output: o }, mk(Object.assign({ text: 'x' }, S)))).retry_note;
try {
  const a = note(P.today, { tap: 'other' });
  if (!a.includes('לא שאלה אותו לשלומו') || a.includes('open_request')) bad.push('note: the tap is not named alone');
  const b = note('אני מבין שיש נזילה בבניין.', {});
  if (!b.includes('נפתחה בזה שהבנת') || !b.includes('open_request') || b.includes('לשלומו')) bad.push('note: the echo changed');
  const c = note('החלפתי את הנורה.', {});
  if (!c.includes('או שנתנה קישור')) bad.push('note: the full list is gone');
} catch (e) { bad.push('note threw: ' + e.message); }
console.log(JSON.stringify({ bad }));
"""


def smoke():
    import check_whatsapp_rules as C
    payload = {"guard": C.inner(R.REPHAY), "tryj": C.inner(R.TRY_JSON), "today": TODAY,
               "cases": [list(c) for c in GUARD_SMOKE]}
    r = subprocess.run(["node", "-e", SMOKE_JS], capture_output=True,
                       input=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    if r.returncode != 0:
        return ["node failed: " + r.stderr.decode("utf-8", "replace")[:300]]
    res = json.loads(r.stdout.decode("utf-8"))
    return [res["error"]] if "error" in res else res["bad"]


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
    print("MEMORY_EPOCH in n8n_whatsapp.py still says %d and retry.py carries `rephay`; "
          "the restored key is -%d. Put the repo back too (git revert)." % (W.MEMORY_EPOCH, OLD_EPOCH))


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

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in ("Sort", "Answer the resident", "Conversation so far", "Reply usable?", "Try again"):
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
        changes.append("Answer the resident: prompt %s -> %s (the representative tap asks how "
                       "he is, and only that)" % (OLD_PROMPT, W.epoch_hash(prompt)))

    # The memory: every buffer holds tap replies that asked how to help first.
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

    # Reply usable?: the `rephay` guard, by id.
    cond = by["Reply usable?"]["parameters"]["conditions"]["conditions"]
    mine = next((c for c in cond if c.get("id") == "rephay"), None)
    if mine is None:
        cond.append(json.loads(json.dumps(R.REPHAY_GUARD)))
        news.append(R.REPHAY)
        changes.append("Reply usable?: `rephay` guard added (a tap reply with no how-are-you "
                       "goes back once, first pass only)")
    elif mine.get("leftValue") != R.REPHAY:
        olds.append(mine.get("leftValue") or "")
        mine["leftValue"] = R.REPHAY
        news.append(R.REPHAY)
        changes.append("Reply usable?: `rephay` guard updated")

    # Try again: the note names the tap's missing how-are-you.
    tp = by["Try again"]["parameters"]
    if tp.get("jsonOutput") != R.TRY_JSON:
        if W.epoch_hash(tp.get("jsonOutput") or "") != OLD_TRY:
            sys.exit("REFUSING: Try again's note is %s, not the one this replaces (%s)."
                     % (W.epoch_hash(tp.get("jsonOutput") or ""), OLD_TRY))
        olds.append(tp["jsonOutput"])
        tp["jsonOutput"] = R.TRY_JSON
        news.append(R.TRY_JSON)
        changes.append("Try again: the note names a tap reply that did not ask how he is")

    bad = smoke()
    if bad:
        sys.exit("REFUSING: the new expressions failed their smoke turns:" + NL + "  "
                 + (NL + "  ").join(bad))

    sib = NP.siblings()
    sib = {k: v for k, v in sib.items()
           if not k.startswith(("n8n_whatsapp_rephay.", "n8n_whatsapp_retry."))}
    old_all, new_all = NL.join(olds), NL.join(news)
    lost = [k for k, v in sib.items() if v in old_all and v not in new_all]
    if lost:
        sys.exit("REFUSING: the edit would break other patchers' anchors: %s" % lost)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("checks   : prompt hash %s, epoch %d, %d smoke turns right, %d sibling anchors intact"
          % (W.epoch_hash(prompt), W.MEMORY_EPOCH, len(GUARD_SMOKE) + 3,
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
