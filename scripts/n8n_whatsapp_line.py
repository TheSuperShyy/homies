# -*- coding: utf-8 -*-
"""Our emergency line comes as an invitation, never an order (11 Nov 2026, evening; Send's line v1).

    python scripts/n8n_whatsapp_line.py              # dry run
    python scripts/n8n_whatsapp_line.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_line.py --apply      # write it
    python scripts/n8n_whatsapp_line.py --restore    # put the snapshot back

WHY. The owner's Grok run of the emergency line (16:02-16:16 Israel, the brief in
docs/features/11-whatsapp-bot/grok-emergency-line-test.md) found the line in every emergency, but given as an order:
three times in the plural, "(בבקשה) תתקשרו עכשיו למוקד החירום שלנו" (executions 173373, 173391, 173403), and once
bare, "תתקשר עכשיו" (173419). The owner asked for the line "in a polite way", and his address rule is one person,
never the plural. The words were Gemini's own: Send changed nothing in them, and no tool's text carries a plural.
The prompt describes the politeness ("בנימוס", "במילים שמזמינות אותו להתקשר") where the gas sentence shows it
("אפשר גם להתקשר"), and gas came out polite and singular in the same run.

WHAT CHANGES, in one write: Send gains one step, "line v1", right after the danger step. In a reply that gives
077-6687949:
  - an order to call or dial at the start of a sentence or clause, "בבקשה"/"אנא" before it dropped, becomes
    "אפשר להתקשר" / "אפשר לחייג" ("בבקשה תתקשרו עכשיו למוקד" -> "אפשר להתקשר עכשיו למוקד");
  - a plural "you" calling anywhere else is singular ("כדאי שתתקשרו" -> "כדאי שתתקשר", "אם תתקשרו" -> "אם תתקשר").
A reply without the number is not touched.
Not changed: the prompt, the tools, the inject, so the memory epoch stays 104 (EPOCH_COVERS reads those three, and
Send is not among them). The danger step, the gas sentence, and the sentence the danger step adds stay as they are.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py. The bot in use is this workflow (Chatwoot,
since 10 Nov); the UChat copy is off.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_hotline import expr_compiles  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

KEY = "={{ $json.to }}-104"
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-11nov-before-line.json")

# The step goes in right before the ref step, which follows the danger step.
ANCHOR = "body.content = (() => { const rv = 'ref v1';"
LV = "const lv = 'line v1';"
STEP = (
    "body.content = (() => { " + LV + " const s = String(body.content || ''); "
    "const HOT = /0?77[-\\s]?668[-\\s]?7949/; if (!HOT.test(s)) return s; "
    "const inf = (v) => (v.indexOf('קשר') !== -1 ? 'להתקשר' : 'לחייג'); "
    "const ORDER = /(^|[.!?:;,\\n]\\s*)((?:ו?(?:בבקשה|אנא|אז|עכשיו|בינתיים),?\\s+)*)(ו?)"
    "(תתקשרו|תתקשרי|תתקשר|התקשרו|התקשרי|התקשר|תחייגו|תחייגי|תחייג|חייגו|חייגי|חייג)(?![א-ת])/g; "
    "const PLURAL = /(^|[^א-ת])(ו?(?:ש|כש)?)(תתקשרו|תחייגו)(?![א-ת])/g; "
    "return s.replace(ORDER, (m, a, pre, v, verb) => a + pre.replace(/ו?(?:בבקשה|אנא),?\\s+/g, '') + v + 'אפשר ' "
    "+ inf(verb)).replace(PLURAL, (m, a, p, verb) => a + p + verb.slice(0, -1)); })(); ")


def line(wf):
    """The workflow with the step in place; the anchor must occur exactly once. Touches nothing else."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    body = by["Send"]["parameters"]["jsonBody"]
    if "const lv = " in body:
        sys.exit("REFUSING: Send already has a line step. Read live first.")
    if "const dv = 'danger v7';" not in body:
        sys.exit("REFUSING: Send's danger step is not v7. Read live first.")
    assert "}}" not in STEP and "{{" not in STEP, "the step would end the expression early"
    by["Send"]["parameters"]["jsonBody"] = once(body, ANCHOR, STEP + ANCHOR)
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    if LV in by["Send"]["parameters"]["jsonBody"]:
        print("Nothing to do. Live already gives our line as an invitation (Send's line v1).")
        return
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key != KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 104's. Read live first." % key)

    new = line(live)
    nb = {n["name"]: n for n in new["nodes"]}
    if prompt_of(new) != prompt_of(live) or tools_of(new) != tools_of(live):
        sys.exit("REFUSING: the prompt or the tools would change; this patcher only adds a Send step.")
    W.check_memory_epoch(prompt=prompt_of(new))
    expr_compiles(nb["Send"]["parameters"]["jsonBody"], "Send")
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (unchanged)   memory: %s (unchanged)" % (W.epoch_hash(prompt_of(new)), key))
    print("Send     : + line v1, right after danger v7: our line as an invitation, a plural 'you' calling singular")
    print("changed  : %s" % ", ".join(n["name"] for n in new["nodes"] if n != by[n["name"]]))

    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        NP.dump(new["nodes"], new["connections"], path)
        print("dumped   : %s (the would-be workflow, secret replaced)" % path)
    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    if snapshot(live, SNAPSHOT):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": new["nodes"], "connections": new["connections"],
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    bb = {n["name"]: n for n in back["nodes"]}
    sb = bb["Send"]["parameters"]["jsonBody"]
    print("\nwritten  : %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  line v1 %s; right before the ref step %s; prompt %s (want %s); memory key %s"
          % ("present" if LV in sb else "MISSING", "yes" if (STEP + ANCHOR) in sb else "NO",
             W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(live)),
             bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
