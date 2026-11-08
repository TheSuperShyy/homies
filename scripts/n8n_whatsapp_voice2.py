# -*- coding: utf-8 -*-
"""Send's voice v2 (8 Nov 2026, evening): two more forms of the team in Michael's mouth, from the owner's
own test of the fourth run's fixes. Code only: no text a model reads changes, so the memory epoch stays 99.

    python scripts/n8n_whatsapp_voice2.py              # dry run
    python scripts/n8n_whatsapp_voice2.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_voice2.py --apply      # write it
    python scripts/n8n_whatsapp_voice2.py --restore    # put the snapshot back

WHAT THE OWNER'S TEST SHOWED (the UChat copy's executions 164335-164424, 10:43-10:57 UTC):
  voice v1 held on live: 164377's draft "כדי שנוכל לסדר את זה" went out as "כדי שאוכל לסדר את זה".
  Two other forms went out, each the model's own words against a text it has:
    164367, the second "when?": "הלוואי שהייתה לי שעה להגיד לך, אבל זה כרגע אצל הצוות שמטפל בזה."
      The prompt: "אף אחד אחר לא מופיע בהודעות שלך כמי שבודק, רואה, מטפל, יודע או יחזור אליו, לא צוות".
      "אצל הצוות" is the form of the owner's 29 Oct chat that started the one-voice rule ("the 3 tickets
      are still open and with the team"); 12 replies had it, 1 since that change: this one.
    164410: "פתחתי עכשיו קריאה למחלקת הניקיון על חדר המדרגות". notify_team's text: "Never which department;
      `department` is your judgment and is not spoken." 2 replies had it, 1 since the change: this one.

WHAT CHANGES (Send only): voice v1 becomes voice v2, with two more steps after its four.
- A clause that puts the matter "אצל הצוות" (or "אצל צוות", "אצל הצוותים") is cut, from where it starts to
  the end of its clause: "ואצל הצוות"; a word joined by "ו" up to six words before it ("ונמצאות אצל
  הצוות", "ובטיפול אצל הצוות"); else the comma before it (", אבל זה כרגע אצל הצוות שמטפל בזה", ", היא
  אצל הצוות"). Never when what goes holds a ticket number or a link, and never when what stays of the
  sentence is under three words or ends on a lead-in ("מה שבטוח, שתי השאלות כבר אצל הצוות." would leave
  "מה שבטוח."): then the reply goes as written. A whole sentence that is nothing else ("היא אצל צוות
  החשמל.") is left as it is too.
- "קריאה / קריאת שירות (חדשה / דחופה) למחלקת X" loses "למחלקת X".
Not changed: the prompt, the tools' texts, the guards, the memory key, the phone agent.

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

KEY = "={{ $json.to }}-99"
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-08nov-before-voice2.json")

# Inside voice v1, just before its last line. No "}}" anywhere: n8n would read it as the expression's end.
B = "(?=[\\s,.!?:;)\\u0022\\u0027]|$)"
TEAM = "אצל (?:ה)?צוות(?:ים)?" + B + "[^,.!?\\n]*"
MORE = (
    "const LEAD = /(?:^|\\s)ו?(?:שכן|שבטוח|אבל|רק|אז|גם|כי|ש|מה|לגבי|בקיצור)$/; "
    "const drop = (x, re) => { let y = x; for (let i = 0; i < 3; i++) { const m = y.match(re); "
    "if (!m || KEEP.test(m[0])) break; const head = y.slice(0, m.index); "
    "const k = Math.max(head.lastIndexOf('.'), head.lastIndexOf('!'), head.lastIndexOf('?'), head.lastIndexOf('\\n')); "
    "const pre = head.slice(k + 1).trim(); if (words(pre) < 3 || LEAD.test(pre)) break; "
    "const r = head + y.slice(m.index + m[0].length); if (words(r) < 2) break; y = r; } return y; }; "
    "out = drop(out, /\\s+ו" + TEAM + "/u); "
    "out = drop(out, /\\s+ו(?!עד\\s|ו)[א-ת]+(?:\\s+(?!ו)[^\\s,.!?]+){0,5}?\\s+" + TEAM + "/u); "
    "out = drop(out, /,\\s*(?:(?!ו)[^\\s,.!?]+\\s+){0,6}?" + TEAM + "/u); "
    "out = out.replace(/(קריא(?:ה|ת שירות)(?: (?:חדשה|דחופה))?) למחלקת (?:ה)?[א-ת]+" + B + "/gu, '$1'); ")
SEND_EDITS = [
    ("const vv = 'voice v1';", "const vv = 'voice v2';"),
    ("return words(out) >= 2 ? out : s; })(); body.content = (() => { const sv = 'slang v1';",
     MORE + "return words(out) >= 2 ? out : s; })(); body.content = (() => { const sv = 'slang v1';"),
]


def voice2(wf):
    """The workflow with Send's voice v2. Nothing a model reads."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    p = by["Send"]["parameters"]
    body = p["jsonBody"]
    for old, new in SEND_EDITS:
        body = once(body, old, new)
    assert "}}" not in MORE and "{{" not in MORE, "voice v2 would end the expression early"
    p["jsonBody"] = body
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    body = by["Send"]["parameters"]["jsonBody"]
    if "const vv = 'voice v2'" in body:
        print("Nothing to do. Live already has voice v2.")
        return
    if key != KEY or "const vv = 'voice v1'" not in body:
        sys.exit("REFUSING: live is not epoch 99 with voice v1 (key %r). Read live first." % key)

    new = voice2(live)
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s -> %s (unchanged)" % (W.epoch_hash(prompt_of(live)), W.epoch_hash(prompt_of(new))))
    print("tools    : %s -> %s (unchanged)" % (W.epoch_hash(tools_of(live)), W.epoch_hash(tools_of(new))))
    print("memory   : %s (unchanged: no text a model reads moved)" % key)
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
    print("  voice v2 %s; prompt %s (want %s); memory key %s" % (
        "present" if "const vv = 'voice v2'" in bb["Send"]["parameters"]["jsonBody"] else "MISSING",
        W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(live)),
        bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
