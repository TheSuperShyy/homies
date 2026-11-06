# -*- coding: utf-8 -*-
"""The Grok tester's run of 5-6 Nov, fixed: Send's danger step lets an unrelated reply go, the bot stops
reciting its limits, speaks for itself and in the singular, and opens a balance with "כמובן"
(6 Nov 2026, epoch 97). The owner: "lets fix and give me the instructions to test again".

    python scripts/n8n_whatsapp_retest.py              # dry run
    python scripts/n8n_whatsapp_retest.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_retest.py --apply      # write it
    python scripts/n8n_whatsapp_retest.py --restore    # put the snapshot back

WHAT THE RUN SHOWED (WORKLOG 6 Nov, read against the executions):
  C9 (156623, 156642, 156650): the model wrote the right replies to a manager request and a cleaning
     complaint, and Send's danger step broke them. It wakes while any of the last three outbound messages
     names an urgent ticket, cut "…לטפל בזה הכי מהר שאפשר, תוכל לספר לי עוד מה קורה?" for "הכי מהר" and
     "רציתי לשאול בזהירות…" for "זהירות", and appended "הקריאה הדחופה שלך פתוחה, מספר …" to each, which
     kept it awake for the next turn.
  C7.2, C8.2: in a gas and a danger follow-up the bot recited what it cannot do ("אין לי אפשרות לתת
     הוראות בטיחות", "…להגיד לך מה לעשות עכשיו או לשלוח מישהו").
  C5.3: "כדי שהצוות יראה את זה"; C9.4: "הבקשה שלך לדבר עם מנהל רשומה", from the when-line's "או
     שרשמת את זה".
  C6.1: the link's close in the plural ("שלכם", "מוזמנים"), copied from the prompt's own "שלהם",
     "שיכתבו".
  C6.3: "בשמחה" before a ₪2,000 debt; the owner took the recommendation to keep "כמובן" for a balance.

WHAT CHANGES.
- Send, danger v5 (code):
  - a turn whose tools handled another matter (a note that is not an emergency, a ticket that is not
    urgent, a balance, a link, a service answer, a standing order) is not an emergency turn: the step
    sleeps, unless this reply itself names the urgent ticket;
  - it appends one line only, "הקריאה הדחופה שלך פתוחה, מספר …". "…וזה הדבר היחיד שאני יכול לעשות
    מכאן", the line the owner disliked on 5 Nov (out of the prompt since epoch 93), goes from the code.
- The prompt:
  - after "you send no help": the prompt's own "הכלל הזה הוא בשבילך, לא בשבילו" for that rule, said
    as what he did, not what he does not give;
  - after the gas line: a follow-up hears again, in other words, that gas goes straight to the company;
  - "רואה" joins those who never appear as checking or handling;
  - the when-line reassures with the matter he told, not with "recorded" in general;
  - the link's close in the singular;
  - a balance opens with "כמובן", its own case.
- Memory epoch 96 -> 97.
Not changed: the tools, the guards, the gas line itself, the closing-message sentence (the owner kept it:
true, and the gate holds it).

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

EPOCH = 97
OLD_KEY = "={{ $json.to }}-96"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-06nov-before-retest.json")

PROMPT_EDITS = [
    ("אתה לא שולח עזרה, לא אומר שמישהו בדרך, ולא מציע שיתקשרו אליו.",
     "אתה לא שולח עזרה, לא אומר שמישהו בדרך, ולא מציע שיתקשרו אליו. גם הכלל הזה הוא בשבילך, לא בשבילו: "
     "מה שהוא שומע ממך זה מה שעשית, ולא מה שאתה לא נותן."),
    ('יש עוד משהו בבניין שאני יכול לבדוק בשבילך?"',
     'יש עוד משהו בבניין שאני יכול לבדוק בשבילך?" ומי ששואל אחרי זה מה לעשות שומע ממך שוב, במילים אחרות, '
     "שעל גז מדווחים ישר לחברת הגז."),
    ("כמי שבודק, מטפל, יודע או יחזור אליו", "כמי שבודק, רואה, מטפל, יודע או יחזור אליו"),
    ("ומרגיע אותו במה שנכון עכשיו, שהקריאה נפתחה או שרשמת את זה, במילים שלך",
     "ומרגיע אותו במה שנכון עכשיו על העניין שהוא סיפר לך, שהקריאה עליו נפתחה או שרשמת אותו, במילים שלך"),
    ("הקישור אישי לדירה שלהם ולא מעבירים אותו הלאה, ואם משהו לא ברור שיכתבו לך כאן",
     "הקישור אישי לדירה שלו ולא מעבירים אותו הלאה, ואם משהו לא ברור שיכתוב לך כאן"),
    ('למי שביקש שתבדוק לו משהו, יתרה, מצב של קריאה או מה כלול בתשלום, נכונות לבדוק, כמו "בשמחה" או '
     '"כמובן", ולא מילה שנשמעת כמו התשובה עצמה, ומשם ישר למה שהמערכת מראה;',
     'למי שביקש שתבדוק לו מצב של קריאה או מה כלול בתשלום, נכונות לבדוק, כמו "בשמחה", ולא מילה שנשמעת '
     'כמו התשובה עצמה, ומשם ישר למה שהמערכת מראה; למי ששאל כמה הוא חייב, "כמובן", ומשם ישר למה שהמערכת '
     'מראה;'),
]

# Send's danger step, v4 -> v5. Exact JavaScript, matched once each.
SEND_EDITS = [
    ("const dv = 'danger v4'", "const dv = 'danger v5'"),
    ("if (!now && !URGENT.test(lb) && !URGENT.test(s)) return s;",
     "const other = steps.some((x) => { const tool = ((x || { }).action || { }).tool; const a = arg(x); "
     "return (tool === 'open_request' && !/^(emergency|critical|immediate)$/i.test(String(a.urgency || '').trim())) "
     "|| (tool === 'notify_team' && String(a.reason || '').trim() !== 'emergency') "
     "|| ['get_balance', 'get_payment_link', 'get_service_info', 'request_standing_order'].indexOf(tool) !== -1; }); "
     "if (!now && !URGENT.test(s) && (other || !URGENT.test(lb))) return s;"),
    (r"const said = String(G.text || '').trim(); const ask = /[?]/.test(said) || "
     r"/^(?:מה|מתי|איך|למה|האם|יש|אז|כמה|מי|איפה)(?:[\s,]|$)/.test(said); if (ref && out.indexOf(ref) === -1) "
     r"out = (out ? out + ' ' : '') + (ask ? 'פתחתי לך קריאה דחופה, מספר ' + ref + ', וזה הדבר היחיד שאני "
     r"יכול לעשות מכאן.' : 'הקריאה הדחופה שלך פתוחה, מספר ' + ref + '.');",
     "if (ref && out.indexOf(ref) === -1) out = (out ? out + ' ' : '') + 'הקריאה הדחופה שלך פתוחה, מספר ' + ref + '.';"),
]


def retest(wf):
    """The workflow with Send's danger v5 and the six prompt edits. Not memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    opts = by["Answer the resident"]["parameters"]["options"]
    sm = opts["systemMessage"]
    for old, new in PROMPT_EDITS:
        sm = once(sm, old, new)
    opts["systemMessage"] = sm
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
    if key == NEW_KEY and "danger v5" in by["Send"]["parameters"]["jsonBody"]:
        print("Nothing to do. Live already has danger v5, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 96's. Read live first." % key)

    new = retest(live)
    nb = {n["name"]: n for n in new["nodes"]}
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("tools    : %s (unchanged: %s)" % (W.epoch_hash(tools_of(new)), tools_of(new) == tools_of(live)))
    print("memory   : %s -> %s (every buffer starts fresh)" % (OLD_KEY, NEW_KEY))
    print("changed  : %s" % ", ".join(n["name"] for n in new["nodes"] if n != by[n["name"]]))
    left = [n["name"] for n in new["nodes"] if "', וזה הדבר היחיד שאני יכול לעשות מכאן." in str(n.get("parameters", {}))]
    assert not left, "the disliked line is still appended in: %s" % left

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
    print("  danger v5 %s; prompt %s (want %s); memory key %s" % (
        "present" if "danger v5" in bb["Send"]["parameters"]["jsonBody"] else "MISSING",
        W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)), bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
