# -*- coding: utf-8 -*-
"""The payment ack goes out only when the resident wrote about paying.

    python scripts/n8n_whatsapp_payack.py            # dry run
    python scripts/n8n_whatsapp_payack.py --dump F   # dry run, plus the would-be workflow in F
                                                     # (check_whatsapp_rules.py --candidate F,
                                                     #  check_patchers_idle.py F)
    python scripts/n8n_whatsapp_payack.py --apply    # write it
    python scripts/n8n_whatsapp_payack.py --restore  # put the 1 Oct evening snapshot back

WHY, 1 Oct evening. The owner said goodbye, "nothing so far thats about it
thanks", and got "אני רואה שאתה מחפש קישור לתשלום. אני בודק את זה עכשיו." before
the real goodbye (execution 74654). His words: *"wth is this"*. `Worth a word?`
is the small model that writes the "one moment, I'm checking" before a payment
link (n8n_whatsapp_firstword.py). Its prompt says NONE to greetings, thanks and
goodbyes, and it did not obey: every sentence it wrote in the retained history
(21 runs, 27 Sep - 1 Oct) was an invented payment request, on "hello good
afternoon" twice (65683, 65694) and on this goodbye. `A word first?` checked only
that the sentence was short and had no link.

WHAT CHANGES, in one write. Both texts are firstword.py's; this only carries them:
  - `A word first?` / word: the note goes out only when the resident's own
    message has a payment word (firstword.PAY_HE / PAY_EN: לשלם, תשלום, קישור,
    לינק, ועד, pay, link, ...). It can only hold a note back. A note held back
    costs nothing: the answer still comes, two beats and all.
  - `Carry on`: `acked` (what the inject tells the answering model was already
    sent) is set only when `Say it now` really ran. Before, a note the gate held
    back was still reported as sent, which with the new test would tell the
    model it had promised to look up a payment link nobody asked for.

WHAT IT DOES NOT TOUCH. The ack model's prompt and its note (no model-facing
text changes: pins and MEMORY_EPOCH stay), Say it now, the wiring, the inject,
Send, every other node.

A field is rewritten only when its live text is exactly the one this replaces.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, `check_patchers_idle.py F`, the
owner's go, `--apply`, the check again on live, and every WhatsApp patcher's dry
run idle.
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
import n8n_whatsapp_firstword as FW  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-01oct-before-payack.json")
PLACEHOLDER = NP.PLACEHOLDER
NL = chr(10)

# The live texts this replaces, as firstword.py had them until 1 Oct evening.
WORD_OLD = ("={{ (() => { const t = String($json.output || '').trim(); "
            "return t.length > 0 && t.length < 320 && t.toUpperCase() !== 'NONE' "
            "&& t.indexOf('http') === -1; })() }}")
CARRY_OLD = ("={{ JSON.stringify(Object.assign({ }, "
             "$('Still the last word?').first().json, { acked: "
             "String($('Worth a word?').first().json.output || '').trim().toUpperCase() "
             "=== 'NONE' ? '' : String($('Worth a word?').first().json.output || '')"
             ".trim() })) }}")

# (the ack model's output, the resident's text or None for "unreachable", goes out?)
INVENTED = "אני רואה שאתה מחפש קישור לתשלום. אני בודק את זה עכשיו."
SHORT = "רגע, אני בודק לך את זה עכשיו."
GATE_SMOKE = [
    (INVENTED, "nothing so far thats about it thanks", False),
    ("צהריים טובים, אני מבין שאתם צריכים קישור לתשלום. אני בודק את זה כרגע.", "hello good afternoon", False),
    (SHORT, "the light keeps blinking", False),
    (SHORT, "אני רוצה לשלם את הוועד", True),
    (SHORT, "send me the payment link", True),
    ("NONE", "אני רוצה לשלם", False),
    ("רגע https://x.example", "אני רוצה לשלם", False),
    (SHORT, None, False),
]
# (the ack model's output, Say it now ran?, acked)
CARRY_SMOKE = [
    (SHORT, True, SHORT),
    (SHORT, False, ""),
    ("NONE", True, ""),
]

SMOKE_JS = """
const fs = require('fs');
const P = JSON.parse(fs.readFileSync(0, 'utf8'));
let word, carry;
try { word = new Function('$json', '$', 'return (' + P.word + ');'); }
catch (e) { console.log(JSON.stringify({ error: 'the gate does not compile: ' + e.message })); process.exit(0); }
try { carry = new Function('$json', '$', 'return (' + P.carry + ');'); }
catch (e) { console.log(JSON.stringify({ error: 'Carry on does not compile: ' + e.message })); process.exit(0); }
const mk = (nodes) => (name) => { if (!nodes[name]) throw new Error('no node ' + name); return nodes[name]; };
const gate = P.gate.map(([out, said]) => {
  const nodes = {};
  if (said !== null) nodes['Still the last word?'] = { first: () => ({ json: { text: said } }) };
  try { return word({ output: out }, mk(nodes)); } catch (e) { return 'THREW ' + e.message; }
});
const carried = P.carry_cases.map(([out, sent]) => {
  const nodes = {
    'Still the last word?': { first: () => ({ json: { text: 'אני רוצה לשלם', greeted: true } }) },
    'Worth a word?': { first: () => ({ json: { output: out } }) },
    'Say it now': { all: () => { if (!sent) throw new Error('unexecuted'); return [{ json: {} }]; } },
  };
  try { const j = JSON.parse(carry({}, mk(nodes))); return [j.acked, j.text, j.greeted]; } catch (e) { return ['THREW ' + e.message]; }
});
console.log(JSON.stringify({ gate, carried }));
"""


def smoke(word_expr, carry_expr):
    import check_whatsapp_rules as C
    payload = {"word": C.inner(word_expr), "carry": C.inner(carry_expr),
               "gate": [[o, s] for o, s, _ in GATE_SMOKE],
               "carry_cases": [[o, s] for o, s, _ in CARRY_SMOKE]}
    r = subprocess.run(["node", "-e", SMOKE_JS], capture_output=True,
                       input=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    if r.returncode != 0:
        return ["node failed: " + r.stderr.decode("utf-8", "replace")[:300]]
    res = json.loads(r.stdout.decode("utf-8"))
    if "error" in res:
        return [res["error"]]
    bad = ["gate %d: got %r, want %r" % (i, got, want)
           for i, (got, (_, _, want)) in enumerate(zip(res["gate"], GATE_SMOKE)) if got is not want]
    for i, (got, (_, _, want)) in enumerate(zip(res["carried"], CARRY_SMOKE)):
        if got != [want, "אני רוצה לשלם", True]:
            bad.append("carry %d: got %r, want acked %r with the rest kept" % (i, got, want))
    return bad


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
    print("firstword.py still carries the new gate and Carry on; put the repo back too (git revert).")


def word_cond(by):
    conds = by["A word first?"]["parameters"]["conditions"]["conditions"]
    hits = [c for c in conds if c.get("id") == "word"]
    if len(hits) != 1 or len(conds) != 1:
        sys.exit("REFUSING: `A word first?` has %d conditions, %d with id 'word'. Read it first."
                 % (len(conds), len(hits)))
    return hits[0]


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    W.check_memory_epoch(prompt=W.system_prompt(), inject=U.AGENT_NEW, tools=W.tools_text())

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in ("Worth a word?", "A word first?", "Say it now", "Carry on", "Still the last word?"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    before_layout = layout_complaints(nodes)
    changes, olds, news = [], [], []

    cond = word_cond(by)
    if cond.get("leftValue") != FW.WORD_EXPR:
        if cond.get("leftValue") != WORD_OLD:
            sys.exit("REFUSING: `A word first?` / word is neither the text this replaces nor "
                     "the new one. Read the live node first.")
        olds.append(cond["leftValue"])
        cond["leftValue"] = FW.WORD_EXPR
        news.append(FW.WORD_EXPR)
        changes.append("A word first?: the note goes out only on a message with a payment word")

    carry = by["Carry on"]["parameters"]
    if carry.get("jsonOutput") != FW.CARRY:
        if carry.get("jsonOutput") != CARRY_OLD:
            sys.exit("REFUSING: `Carry on` is neither the text this replaces nor the new one. "
                     "Read the live node first.")
        olds.append(carry["jsonOutput"])
        carry["jsonOutput"] = FW.CARRY
        news.append(FW.CARRY)
        changes.append("Carry on: acked only when Say it now really sent the note")

    for label, expr in (("the gate", FW.WORD_EXPR), ("Carry on", FW.CARRY)):
        if expr.count("}}") != 1:
            sys.exit("REFUSING: %s has %d '}}'." % (label, expr.count("}}")))
    bad = smoke(FW.WORD_EXPR, FW.CARRY)
    if bad:
        sys.exit("REFUSING: the new expressions failed their smoke cases:" + NL + "  "
                 + (NL + "  ").join(bad))

    sib = NP.siblings()
    sib = {k: v for k, v in sib.items() if not k.startswith("n8n_whatsapp_payack.")}
    old_all, new_all = NL.join(olds), NL.join(news)
    lost = [k for k, v in sib.items() if v in old_all and v not in new_all
            and not k.startswith("n8n_whatsapp_firstword.")]
    if lost:
        sys.exit("REFUSING: the edit would break other patchers' anchors: %s" % lost)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("checks   : %d gate and %d Carry on smoke cases right, one '}}' each"
          % (len(GATE_SMOKE), len(CARRY_SMOKE)))
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
    print("  A word first? / word matches: %s" % (word_cond(bb)["leftValue"] == FW.WORD_EXPR))
    print("  Carry on matches: %s" % (bb["Carry on"]["parameters"]["jsonOutput"] == FW.CARRY))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
