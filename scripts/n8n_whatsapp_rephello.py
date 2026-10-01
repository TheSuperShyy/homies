# -*- coding: utf-8 -*-
"""The representative says hi: the לדבר עם נציג tap opens like a person joining.

    python scripts/n8n_whatsapp_rephello.py            # dry run
    python scripts/n8n_whatsapp_rephello.py --dump F   # dry run, plus the would-be workflow in F
                                                       # (check_whatsapp_rules.py --candidate F,
                                                       #  check_patchers_idle.py F,
                                                       #  wa_qa.py bundle --candidate F)
    python scripts/n8n_whatsapp_rephello.py --apply    # write it
    python scripts/n8n_whatsapp_rephello.py --restore  # put the 1 Oct evening snapshot back

WHY, 1 Oct evening. The owner tapped לדבר עם נציג right after the menu (execution
74529) and got "כאן מיכאל מהומי'ז! 😊 במה אוכל לעזור לך?". The model had written
"היי, " in front of it and Send's greeting filter cut it, as the owner's 27 Sep
table says: no greeting right after the system's menu. On that one tap he asked
for the opposite: *"can we make it like for example talk to a rep liek the agent
should be like hi how are you this is michael from homies..."*. Someone who asks
for a representative is waiting for a person, and a person joining says hi.

WHAT CHANGES, in one write. Each text is owned elsewhere; this only carries them:
  - The prompt (docs/features/11-whatsapp-bot/prompt.md). On that tap: open with
    "היי" (not the hour's greeting, which the menu already gave), ask how he is,
    say who you are, ask how you can help, in one short message. The two general
    clauses it would contradict (no greeting after the system's; only the
    resident opens how-are-you) name it as their one exception, and "no greeting
    on a tap" now speaks of the other two buttons. MEMORY_EPOCH 70 -> 71: every
    buffer holds tap replies without the hello.
  - Send's greeting filter, manners v3 (n8n_whatsapp_manners.py): on that tap
    one hello stays, and so does the name. Every other row is v2.

WHAT IT DOES NOT TOUCH. The menu and its buttons, Sort, the inject, the tools,
the guards (the `opener` guard already exempts this tap; Send's third menu rule
needs an ungreeted handset, which a tap never is), the other two buttons,
anything typed after the menu, the small writers, the voice agents.

A field is rewritten only when its live text is the one this replaces. Anything
else means it was changed since, and this refuses.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, `check_patchers_idle.py F`, the
Claude-played replay (`wa_qa.py bundle --candidate F`), the owner's go,
`--apply`, the check again on live, and every WhatsApp patcher's dry run idle.
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
import n8n_whatsapp_manners as M  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
import n8n_whatsapp_retry as R  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-01oct-before-rephello.json")
PLACEHOLDER = NP.PLACEHOLDER
OLD_EPOCH = 70
OLD_PROMPT = "c6956ac921cf"     # EPOCH_COVERS["prompt"] at epoch 70
OLD_MARK = "const mv = 'manners v2';"
MEMORY_KEY = "={{ $json.to }}-%d"
NL = chr(10)
MENU = "צהריים טובים 👋 במה אפשר לעזור?"

# Turns the new Send body must get right before any PUT: (reply, Sort's state, want).
REP = "היי, מה שלומך? כאן מיכאל מהומי'ז. במה אוכל לעזור לך?"
TAP = {"last_bot": MENU, "tap": "other", "tap_now": True, "text": "לדבר עם נציג"}
SMOKE = [
    (REP, TAP, REP),
    ("היי! צהריים טובים, מה שלומך? כאן מיכאל מהומי'ז. במה אוכל לעזור לך?", TAP,
     "היי! מה שלומך? כאן מיכאל מהומי'ז. במה אוכל לעזור לך?"),
    ("היי! כאן מיכאל מהומי'ז, טוב שפנית. מה קרה?",
     {"last_bot": MENU, "tap": "open", "tap_now": True, "text": "פתיחת קריאת שירות"},
     "כאן מיכאל מהומי'ז, טוב שפנית. מה קרה?"),
    ("צהריים טובים! מיכאל מהומי'ז כאן. איך אפשר לעזור בתשלום?",
     {"last_bot": MENU, "text": "I want to pay"},
     "מיכאל מהומי'ז כאן. איך אפשר לעזור בתשלום?"),
    ("היי, שמח לשמוע! במה אוכל לעזור?", {"text": "טוב תודה"}, "שמח לשמוע! במה אוכל לעזור?"),
]

SMOKE_JS = """
const fs = require('fs');
const P = JSON.parse(fs.readFileSync(0, 'utf8'));
let f;
try { f = new Function('$json', '$', 'return (' + P.expr + ');'); }
catch (e) { console.log(JSON.stringify({ error: 'does not compile: ' + e.message })); process.exit(0); }
const out = P.cases.map(([reply, st]) => {
  const S = Object.assign({ greeting: false, greeted: true, last_bot: '', text: '', tap_now: false }, st);
  const nodes = {
    'Sort': { first: () => ({ json: S }) },
    'Carry on': { first: () => ({ json: { acked: '', text: S.text } }) },
    'Answer the resident': { first: () => ({ json: { intermediateSteps: [] } }) },
    'Anything newer?': { all: () => [] },
    'Say it now': { all: () => { throw new Error('unexecuted'); } },
  };
  const $ = (name) => { if (!nodes[name]) throw new Error('no node ' + name); return nodes[name]; };
  try { return JSON.parse(f({ output: reply }, $)).content; } catch (e) { return 'THREW ' + e.message; }
});
console.log(JSON.stringify({ out }));
"""


def smoke(json_body):
    """Compile the whole Send expression in Node and run SMOKE through it."""
    import check_whatsapp_rules as C
    payload = {"expr": C.inner(json_body), "cases": [[a, b] for a, b, _ in SMOKE]}
    r = subprocess.run(["node", "-e", SMOKE_JS], capture_output=True,
                       input=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    if r.returncode != 0:
        return ["node failed: " + r.stderr.decode("utf-8", "replace")[:300]]
    res = json.loads(r.stdout.decode("utf-8"))
    if "error" in res:
        return [res["error"]]
    return ["smoke %d: got %r, want %r" % (i, got, want)
            for i, (got, (_, _, want)) in enumerate(zip(res["out"], SMOKE)) if got != want]


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
    print("MEMORY_EPOCH in n8n_whatsapp.py still says %d and manners.py says v3; the "
          "restored key is -%d and Send runs v2. Put the repo back too (git revert)."
          % (W.MEMORY_EPOCH, OLD_EPOCH))


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
    for need in ("Send", "Sort", "Answer the resident", "Conversation so far"):
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
        changes.append("Answer the resident: prompt %s -> %s (the representative tap opens "
                       "with hi, how are you, the name)" % (OLD_PROMPT, W.epoch_hash(prompt)))

    # The memory: every buffer holds tap replies without the hello.
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

    # Send: the greeting filter, v2 -> v3, by its own block markers.
    body = by["Send"]["parameters"].get("jsonBody") or ""
    new = body
    if M.SEND_NEW not in body:
        if body.count(OLD_MARK) != 1 or body.count(M.BLOCK_START) != 1:
            sys.exit("REFUSING: Send does not carry %s exactly once. Read the live body first." % OLD_MARK)
        a = body.index(M.BLOCK_START)
        z = body.index(M.BLOCK_END, a) + len(M.BLOCK_END)
        new = body[:a] + M.FILTER + M.BLOCK_END + body[z:]
        if M.SEND_NEW not in new:
            sys.exit("REFUSING: the replaced block does not read as manners.SEND_NEW.")
        changes.append("Send: greeting filter manners v2 -> v3 (the representative tap keeps "
                       "one hello and the name)")
    if new != body:
        if new.count("}}") != 1:
            sys.exit("REFUSING: the new Send body has %d '}}'." % new.count("}}"))
        for k, v in (("the promise filter", NP.SEND_NEW), ("the opener menu rule", R.SEND_TAIL_NEW)):
            if v not in new:
                sys.exit("REFUSING: the new Send body lost %s." % k)
        bad = smoke(new)
        if bad:
            sys.exit("REFUSING: the new Send body failed its smoke turns:" + NL + "  "
                     + (NL + "  ").join(bad))
        by["Send"]["parameters"]["jsonBody"] = new
        olds.append(body)
        news.append(new)

    sib = NP.siblings()
    sib = {k: v for k, v in sib.items() if not k.startswith("n8n_whatsapp_rephello.")}
    old_all, new_all = NL.join(olds), NL.join(news)
    lost = [k for k, v in sib.items() if v in old_all and v not in new_all]
    if lost:
        sys.exit("REFUSING: the edit would break other patchers' anchors: %s" % lost)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("checks   : prompt hash %s, epoch %d, %d smoke turns right, %d sibling anchors intact"
          % (W.epoch_hash(prompt), W.MEMORY_EPOCH, len(SMOKE),
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
    sb = bb["Send"]["parameters"]["jsonBody"]
    print("")
    print("written: %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  prompt %s (want %s); memory key %s" % (
        W.epoch_hash(bb["Answer the resident"]["parameters"]["options"]["systemMessage"]),
        W.epoch_hash(prompt), bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("  Send carries %s: %s; %s: %s; the opener rule: %s; '}}' count: %d" % (
        M.MARK, M.SEND_NEW in sb, NP.MARK, NP.SEND_NEW in sb, R.SEND_TAIL_NEW in sb, sb.count("}}")))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
