# -*- coding: utf-8 -*-
"""The Grok tester's second run (6 Nov 2026), fixed: a status answer names its ticket, the question after
"when?" stays on the matter, a manager request is never "recorded" later either, and "מבאס" becomes
"לא נעים" (epoch 98).

    python scripts/n8n_whatsapp_retest2.py              # dry run
    python scripts/n8n_whatsapp_retest2.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_retest2.py --apply      # write it
    python scripts/n8n_whatsapp_retest2.py --restore    # put the snapshot back

WHAT THE SECOND RUN SHOWED (read against the UChat copy's executions):
  C2 (158324): "שוב אני, המעלית עדיין לא עובדת" went to get_request_status, which returned 255-1398-26,
     and the reply said only "היא עדיין פתוחה במערכת". Nothing in that tool's text asks for the number;
     C10.3 listed three tickets without theirs the same way.
  C1.4, C2, C9.4 (158295, 158324, 158538): the answer to "when?" ended "יש עוד משהו שאוכל לעזור בו
     בינתיים?". The rule against it lives in the question paragraph, far from the when-line the model is
     following at that moment.
  C9.4 (158538): "גם הבקשה שלך וגם קריאת השירות על הניקיון כבר פתוחות ורשומות". The manager paragraph's
     "על הרישום הזה אתה לא מספר לו" covers the first reply; the later "when will the manager call?" is
     answered from the when-line.
  C4.1 in the first run and C11.1 in this one: "מבאס", under a prompt that already says "בלי סלנג".

WHAT CHANGES.
- get_request_status's text: name each ticket by its reference when saying what it shows.
- The prompt: the when-line's closing question stays on his matter (point of use, positive, no quoted
  phrase); the manager paragraph's "not telling" reaches the later question too.
- Send, slang v1 (code, beside emoji v1): "מבאס" and "באסה" -> "לא נעים". The prompt already forbids slang and the model
  said it twice in two runs; the code makes the owner's register hold the way emoji v1 does for emoji.
- Memory epoch 97 -> 98.
Not changed: the guards, the other tools, the phone agent (its played manager call was clean).

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py, then n8n_uchat.py --apply carries it to
the UChat copy, the bot in use.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 98
OLD_KEY = "={{ $json.to }}-97"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-06nov-before-retest2.json")

PROMPT_EDITS = [
    ("ומיד אחריה מה שכן נכון עכשיו: מה שהכלי הראה על הקריאה, ומה אתה יכול לעשות בשבילו מכאן, כמו לבדוק "
     "אותה שוב כשיכתוב לך.",
     "ומיד אחריה מה שכן נכון עכשיו: מה שהכלי הראה על הקריאה, ומה אתה יכול לעשות בשבילו מכאן, כמו לבדוק "
     "אותה שוב כשיכתוב לך. והשאלה שבסוף ההודעה הזאת נשארת על העניין שלו, כמו אם משהו השתנה או החמיר."),
    ("על הרישום הזה אתה לא מספר לו:",
     "על הרישום הזה אתה לא מספר לו, גם לא אחר כך כשהוא שואל מתי יחזרו אליו:"),
]
TOOL_EDITS = {
    "get_request_status": [
        ("toolDescription", "Read-only; the answer is live from the system.",
         "Read-only; the answer is live from the system. When you tell them what it shows, name each ticket by "
         "its reference."),
    ],
}
SLANG = ("body.content = (() => { const sv = 'slang v1'; const s = String(body.content || ''); "
         "return s.replace(/(^|[\\s,.!?:;\"'(])(?:מבאס|באסה)(?=[\\s,.!?:;\"')]|$)/g, (m, a) => a + 'לא נעים'); })(); ")
SEND_EDITS = [
    ("body.content = (() => { const ev = 'emoji v1';", SLANG + "body.content = (() => { const ev = 'emoji v1';"),
]


def retest2(wf):
    """The workflow with the two prompt edits, get_request_status's clause and Send's slang v1. Not memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    opts = by["Answer the resident"]["parameters"]["options"]
    sm = opts["systemMessage"]
    for old, new in PROMPT_EDITS:
        sm = once(sm, old, new)
    opts["systemMessage"] = sm
    for tool, edits in TOOL_EDITS.items():
        p = by[tool]["parameters"]
        for key, old, new in edits:
            p[key] = once(p[key], old, new)
    p = by["Send"]["parameters"]
    body = p["jsonBody"]
    for old, new in SEND_EDITS:
        body = once(body, old, new)
    p["jsonBody"] = body
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and "slang v1" in by["Send"]["parameters"]["jsonBody"]:
        print("Nothing to do. Live already has slang v1, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 97's. Read live first." % key)

    new = retest2(live)
    nb = {n["name"]: n for n in new["nodes"]}
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("tools    : %s -> %s (get_request_status's text)" % (W.epoch_hash(tools_of(live)), W.epoch_hash(tools_of(new))))
    print("memory   : %s -> %s (every buffer starts fresh)" % (OLD_KEY, NEW_KEY))
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
    print("\nwritten  : %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  slang v1 %s; prompt %s (want %s); tools %s (want %s); memory key %s" % (
        "present" if "slang v1" in bb["Send"]["parameters"]["jsonBody"] else "MISSING",
        W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)), W.epoch_hash(tools_of(back)),
        W.epoch_hash(tools_of(new)), bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
