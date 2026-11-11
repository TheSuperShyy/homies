# -*- coding: utf-8 -*-
"""Every emergency gets Homies' emergency line, at any hour, said politely (11 Nov 2026, epoch 104).

    python scripts/n8n_whatsapp_hotline.py              # dry run
    python scripts/n8n_whatsapp_hotline.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_hotline.py --apply      # write it
    python scripts/n8n_whatsapp_hotline.py --restore    # put the snapshot back

WHY. The owner, 11 Nov: "ok so when we have like an emergency any type of emergency we have a direct hotline
specially built for that its a department the number is not given to us yet", then "0776687949 this is the
hotline so all the emergency service redirect them here in a polite way". It is the line Yariv gave on 9 Nov as
"our telephone emergency centre". Since epoch 100 Michael gave it only outside Sun-Thu 09:00-17:00 Israel: in
office hours Send's danger v6 cut it, and gas got the gas company only. Asked whether gas gets it too, the owner
was told "you said any type of emergency, so I'll add the hotline next to the gas company unless you say
otherwise", and answered with the number and "all the emergency service".

WHAT CHANGES, in one write:
  The prompt   every urgent fault gets the line, at any hour, politely, from his first message about it, even
               before the ticket is open; the pressed reply names it at any hour; "nobody is sent anywhere" and
               "the office phone is only for ..." lose "outside office hours"; the gas sentence, word for word,
               gains the line after the gas company, and so does its "what do I do?" answer.
  Send         danger v7. A sentence whose only advice is our line, a verb of calling or a word of recommending
               ("אני ממליץ", "כדאי") stays at any hour (v6: after hours only, and no word of recommending). On
               the turn whose tools opened the urgent ticket or the emergency note, a reply without the line
               gets one sentence, right after the ticket's sentence or else before the closing question:
                   "למקרי חירום יש לנו מוקד טלפוני ייעודי, ואפשר להתקשר אליו עכשיו: 077-6687949."
               A later turn adds nothing: the line came with the ticket.
  Memory       epoch 103 -> 104.
Not changed: the inject (its "outside office hours" mark stays, a true fact); the urgent ticket and the
emergency note, still opened first; gas still opens no ticket; the phone agents. The incoming phone agent's twin
is owed: it still gives the line after hours only (docs/assistant/demo-inbound.md).

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py. The bot in use is this workflow (Chatwoot,
since 10 Nov); the UChat copy is off.
"""
import copy
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 104
OLD_KEY = "={{ $json.to }}-103"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-11nov-before-hotline.json")

# The one sentence Send adds. Neither gender nor an order: "אפשר להתקשר", and why the line is the place.
HOTS = "למקרי חירום יש לנו מוקד טלפוני ייעודי, ואפשר להתקשר אליו עכשיו: 077-6687949."

# The prompt, each edit exactly once (docs/features/11-whatsapp-bot/prompt.md carries the result).
PROMPT_EDITS = (
    # Nobody is sent anywhere: gas, and now every urgent fault.
    ("דייר לא נשלח ממך לשום מקום, חוץ ממקרה של גז ומתקלה דחופה מחוץ לשעות הפעילות, שעליהם כתוב בהמשך.",
     "דייר לא נשלח ממך לשום מקום, חוץ ממקרה של גז ומתקלה דחופה, שעליהם כתוב בהמשך."),
    # The office phone: on request, how to reach the office, and every urgent fault.
    ("הטלפון והמייל של המשרד הם רק למי שמבקש אותם במפורש, למי ששואל איך מגיעים למשרד, ולתקלה דחופה מחוץ לשעות "
     "הפעילות.",
     "הטלפון והמייל של המשרד הם רק למי שמבקש אותם במפורש ולמי ששואל איך מגיעים למשרד, והטלפון גם לכל תקלה דחופה."),
    # The emergency: the urgent ticket and its number, and the line at any hour, politely, from the first message.
    ("מה שיש לך לתת זה שפתחת קריאה דחופה, עם המספר שחזר, וזה כל מה שיש לך. רק כשכתוב לך שעכשיו מחוץ לשעות הפעילות "
     "של המשרד, יש לזה תוספת אחת, וזאת החלטה של ההנהלה: על תקלה דחופה שצריכה מענה מיידי אתה גם מפנה אותו למוקד "
     "החירום הטלפוני שלנו, 077-6687949, שעונה גם כשהמשרד סגור.",
     "מה שיש לך לתת זה שפתחת קריאה דחופה, עם המספר שחזר, ועוד דבר אחד, וזאת החלטה של ההנהלה: על כל תקלה דחופה, "
     "בכל שעה, אתה גם מפנה אותו בנימוס למוקד החירום הטלפוני שלנו, 077-6687949, שקיים בדיוק בשביל מקרים כאלה. את "
     "זה הוא שומע כבר בהודעה הראשונה שלך על המקרה, גם אם עוד לא פתחת את הקריאה, ובמילים שמזמינות אותו להתקשר, "
     "לא כאילו אתה מעביר אותו הלאה."),
    # Pressed for more: the line at any hour.
    ("מה עשית ומה המספר של הקריאה, ומחוץ לשעות הפעילות גם את המוקד, ולא מוסיף שאלה",
     "מה עשית ומה המספר של הקריאה, וגם את המוקד, ולא מוסיף שאלה"),
    # Gas: the gas company first, then the line; the same in the "what do I do?" answer.
    ("ולדווח לה ישירות. יש עוד משהו בבניין שאני יכול לבדוק בשבילך?\" ומי ששואל אחרי זה מה לעשות שומע ממך שוב, "
     "במילים אחרות, שעל גז מדווחים ישר לחברת הגז.",
     "ולדווח לה ישירות. אפשר גם להתקשר למוקד החירום הטלפוני שלנו, 077-6687949. יש עוד משהו בבניין שאני יכול "
     "לבדוק בשבילך?\" ומי ששואל אחרי זה מה לעשות שומע ממך שוב, במילים אחרות, שעל גז מדווחים ישר לחברת הגז, "
     "ושאפשר להתקשר גם למוקד החירום שלנו."),
)

# Send, danger v7. The office-hours test goes; a word of recommending is no advice next to our line; the turn
# that opened the urgent ticket or the emergency note always carries the line (`now` and `ref` are the step's).
DV_OLD = "const dv = 'danger v6';"
DV_NEW = "const dv = 'danger v7';"
CLOSED_OLD = ("let closed = false; try { const z = $now.setZone('Asia/Jerusalem'); const h = parseInt(z.toFormat('HH:mm'), "
              "10); closed = z.weekday === 5 || z.weekday === 6 || h < 9 || h >= 17; } catch (e) { closed = false; } ")
HOTLINE_OLD = ("const hotline = (p) => closed && HOT.test(p) && !ADVICE.test(p.split(HOT).join(' ').replace(CALLV, "
               "(m, a) => a)); ")
HOTLINE_NEW = (
    "const RECV = /(^|[\\s,])(?:ו|ש|וש)?(?:ממליץ|ממליצה|מומלץ|כדאי|עדיף|רצוי)(?=[\\s,.!?:;]|$)/g; "
    "const hotline = (p) => HOT.test(p) && !ADVICE.test(p.split(HOT).join(' ').replace(CALLV, (m, a) => a)"
    ".replace(RECV, (m, a) => a)); "
    "const HOTS = '" + HOTS + "'; "
    "const withHot = (t) => { if (!now || !t || HOT.test(t)) return t; "
    "const ps = t.match(/(?:[^.!?\\n]|[.!](?=\\S))+[.!?]*\\s*|\\s+/g) || [t]; "
    "let i = ref ? ps.findIndex((p) => p.indexOf(ref) !== -1) : -1; "
    "if (i === -1) { let k = ps.length - 1; while (k > 0 && !ps[k].trim()) k--; i = /[?]\\s*$/.test(ps[k]) ? k - 1 : k; } "
    "const head = ps.slice(0, i + 1).join('').replace(/\\s+$/, ''); "
    "const tail = ps.slice(i + 1).join('').replace(/^\\s+/, ''); "
    "return (head ? head + ' ' : '') + HOTS + (tail ? ' ' + tail : ''); }; ")
NOCUT_OLD = "if (!cut) return s;"
NOCUT_NEW = "if (!cut) return withHot(s);"
END_OLD = "return out || s; })();"
END_NEW = "return withHot(out || s); })();"
SEND_EDITS = ((DV_OLD, DV_NEW), (CLOSED_OLD, ""), (HOTLINE_OLD, HOTLINE_NEW), (NOCUT_OLD, NOCUT_NEW), (END_OLD, END_NEW))


def expr_compiles(expr, what):
    """An n8n expression's JavaScript must parse, the way the gate compiles Send."""
    s = expr.strip()
    s = s[1:].strip() if s.startswith("=") else s
    if not (s.startswith("{{") and s.endswith("}}")):
        sys.exit("REFUSING: %s is not one n8n expression." % what)
    js = ("const src = require('fs').readFileSync(0, 'utf8');"
          "try { new Function('$json', '$', '$now', 'return (' + src + ');'); }"
          " catch (e) { console.log(e.message); process.exit(1); }")
    r = subprocess.run(["node", "-e", js], input=s[2:-2].strip(), capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        sys.exit("REFUSING: %s would not compile: %s" % (what, (r.stdout or r.stderr).strip()[:200]))


def hotline(wf):
    """The workflow with the edits above; each anchor must occur exactly once. Does not touch memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    body = by["Send"]["parameters"]["jsonBody"]
    for name in ("HOTS", "withHot", "RECV"):
        if name in body:
            sys.exit("REFUSING: Send already names %s. Read live first." % name)
    for old, new in SEND_EDITS:
        assert "}}" not in new and "{{" not in new, "an edit would end the expression early"
        body = once(body, old, new)
    if "closed" in body:   # on 11 Nov all four were the danger step's office-hours test
        sys.exit("REFUSING: Send still reads `closed`.")
    by["Send"]["parameters"]["jsonBody"] = body
    agent = by["Answer the resident"]["parameters"]
    for old, new in PROMPT_EDITS:
        agent["options"]["systemMessage"] = once(agent["options"]["systemMessage"], old, new)
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and DV_NEW in by["Send"]["parameters"]["jsonBody"]:
        print("Nothing to do. Live already gives our emergency line at any hour, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 103's. Read live first." % key)
    if W.MEMORY_EPOCH != EPOCH:
        sys.exit("REFUSING: n8n_whatsapp.MEMORY_EPOCH is %d, not %d. Move the repo first." % (W.MEMORY_EPOCH, EPOCH))

    new = hotline(live)
    if prompt_of(new) != W.system_prompt():
        sys.exit("REFUSING: the would-be prompt is not docs/features/11-whatsapp-bot/prompt.md's. "
                 "Edit the document first; live follows it.")
    W.check_memory_epoch(prompt=prompt_of(new))
    nb = {n["name"]: n for n in new["nodes"]}
    expr_compiles(nb["Send"]["parameters"]["jsonBody"], "Send")
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("tools    : %s (unchanged: %s)" % (W.epoch_hash(tools_of(new)), tools_of(new) == tools_of(live)))
    print("Send     : danger v7, our line at any hour; the emergency turn always carries it")
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
    sb = bb["Send"]["parameters"]["jsonBody"]
    print("\nwritten  : %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  prompt %s (want %s); memory key %s; danger v7 %s; the office-hours test %s; the added sentence %s"
          % (W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)),
             bb["Conversation so far"]["parameters"]["sessionKey"],
             "present" if DV_NEW in sb else "MISSING",
             "gone" if CLOSED_OLD not in sb else "STILL THERE",
             "present" if HOTS in sb else "MISSING"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
