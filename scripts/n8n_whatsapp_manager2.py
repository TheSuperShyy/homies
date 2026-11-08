# -*- coding: utf-8 -*-
"""Send's manager v2 (8 Nov 2026, night): a manager request is never "recorded" even when the reply does
not say "manager". Code only: no text a model reads changes, so the memory epoch stays 99.

    python scripts/n8n_whatsapp_manager2.py              # dry run
    python scripts/n8n_whatsapp_manager2.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_manager2.py --apply      # write it
    python scripts/n8n_whatsapp_manager2.py --restore    # put the snapshot back

WHAT THE RETEST SHOWED (the tester's C5/C9 retest, the UChat copy's executions 165044-165118, 14:09-14:21
UTC; both conversations passed):
  C9.4 (165118), "ומתי המנהל יחזור אליי?": the first draft said "וגם רשמתי במערכת את הבקשה שלך". The truth
  check sent it back ("רשמתי" with no tool this turn) and the retry went out clean. manager v1 would not
  have cut that sentence: it knows the request only as "לדבר עם מנהל" or "הבקשה … למנהל", and this one
  says "הבקשה שלך". On a retry, which the truth check does not see again (the fifth run's 164822), or in
  the passive ("הבקשה שלך רשומה", no deed verb), it would go out.

WHAT CHANGES (Send only): manager v1 becomes manager v2.
- When the tenant's own words this turn are about a manager or a person (מנהל, הנהלה, בן אדם, נציג,
  אחראי, manager, human, person), "הבקשה / הפנייה (שלך)", "בקשתך" and "פנייתך" count as the request too.
  "בבקשה" never does, and nor does a request for something named ("הבקשה שלך להוראת קבע", "בקשתך לדעת
  כמה …"); one "to the team" or "to a manager" still does.
- The joining word is the first one within four words of the claim, not the nearest: "וגם רשמתי …"
  goes from "וגם", where v1 would have kept "וגם" and then, as a lead-in, dropped the whole sentence.
- A lone "אבל" or "וגם" before the claim goes with it, from its comma: "אני לא יכול להבטיח מתי יחזרו
  אליך, אבל העברתי לצוות את הבקשה" keeps its honest first half.
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
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-08nov-before-manager2.json")

V1_MGR = (r"""const MGR = /(?:לדבר|לשוחח)(?: ישירות)? (?:עם|אל) (?:ה)?(?:מנהל|מנהלת|הנהלה|אחראי|נציג|נציגה|בן אדם)"""
          r"""|(?:בקשה|בקשתך|פנייה|פנייתך)(?: שלך)? (?:ל|אל )(?:ה)?(?:מנהל|מנהלת|הנהלה)/u; """)
V2_MGR = (r"""const MGR0 = /(?:לדבר|לשוחח)(?: ישירות)? (?:עם|אל) (?:ה)?(?:מנהל|מנהלת|הנהלה|אחראי|נציג|נציגה|בן אדם)"""
          r"""|(?:בקשה|בקשתך|פנייה|פנייתך)(?: שלך)? (?:ל|אל )(?:ה)?(?:מנהל|מנהלת|הנהלה)/u; """
          r"""let said = ''; try { said = String($('Carry on').first().json.text || ''); } catch (e) { said = ''; } if (!said) said = String(G.text || ''); """
          r"""const MGR = /מנהל|הנהלה|בן אדם|נציג|אחראי|manager|human|person/i.test(said) """
          r"""? /(?:לדבר|לשוחח)(?: ישירות)? (?:עם|אל) (?:ה)?(?:מנהל|מנהלת|הנהלה|אחראי|נציג|נציגה|בן אדם)"""
          r"""|(?:בקשה|בקשתך|פנייה|פנייתך)(?: שלך)? (?:ל|אל )(?:ה)?(?:מנהל|מנהלת|הנהלה)"""
          r"""|(?:^|[^א-ת])(?:ו|ש|וש)?(?:ה)?(?:בקשה|פנייה)(?!(?: שלך)?\s+(?:ל(?!צוות|מנהל|הנהלה|נציג)|על\s|בנוגע|בעניין|בקשר))(?: שלך)?(?=[\s,.!?:;)]|$)"""
          r"""|(?:בקשתך|פנייתך)(?!\s+(?:ל(?!צוות|מנהל|הנהלה|נציג)|על\s|בנוגע|בעניין|בקשר))/u : MGR0; """)
SEND_EDITS = [
    ("const mg = 'manager v1';", "const mg = 'manager v2';"),
    (V1_MGR, V2_MGR),
    ("while (m !== null && m.index <= at) { if (words(g.slice(m.index, at)) <= 4) j = m.index; m = J.exec(g); }",
     "while (m !== null && m.index <= at) { if (j === -1 && words(g.slice(m.index, at)) <= 4) j = m.index; m = J.exec(g); }"),
    # A lone "אבל" or "וגם" before the claim is the clause's own opening: the clause goes from its comma.
    ("if (j > 0 && g.slice(0, j).trim() !== '') {",
     "if (j > 0 && g.slice(0, j).trim() !== '' && !/^(?:אבל|אך|ו?גם|ואז|אז|כי|ש|ו)$/.test(g.slice(0, j).trim())) {"),
]


def manager2(wf):
    """The workflow with Send's manager v2. Nothing a model reads."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    p = by["Send"]["parameters"]
    body = p["jsonBody"]
    for _, new in SEND_EDITS:
        assert "}}" not in new and "{{" not in new, "a step would end the expression early"
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
    body = by["Send"]["parameters"]["jsonBody"]
    if "const mg = 'manager v2'" in body:
        print("Nothing to do. Live already has manager v2.")
        return
    if key != KEY or "const mg = 'manager v1'" not in body:
        sys.exit("REFUSING: live is not epoch 99 with manager v1 (key %r). Read live first." % key)

    new = manager2(live)
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
    print("  manager v2 %s; prompt %s (want %s); memory key %s" % (
        "present" if "const mg = 'manager v2'" in bb["Send"]["parameters"]["jsonBody"] else "MISSING",
        W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(live)),
        bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
