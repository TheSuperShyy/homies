# -*- coding: utf-8 -*-
"""A hello gets Michael's intro, with no buttons (11 Nov 2026, epoch 103).

    python scripts/n8n_whatsapp_hiintro.py              # dry run
    python scripts/n8n_whatsapp_hiintro.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_hiintro.py --apply      # write it
    python scripts/n8n_whatsapp_hiintro.py --restore    # put the snapshot back

WHY. The owner, 11 Nov: "lets remove the button each hi so every opening message will receive the intro only
the michael from homies how can i help you". Shown examples (the 27 Sep table says to show them before a
greeting changes), he gave the exact shape: "Hi good morning or good afternoon. this is michael from homies
how can i help you today". So a bare hello now gets

    "היי, צהריים טובים 👋 כאן מיכאל מהומי'ז. במה אוכל לעזור לך היום?"      ("היי" alone before 05:00)

and no buttons. It replaces the 8 Oct menu ("<clock> 👋 כאן הומי'ז. במה אפשר לעזור?" with two buttons,
n8n_whatsapp_menuline.py, now superseded) and the 27 Sep table's "a bare hi gets the canned menu". The rest
of the table stands: the next reply does not greet again, and since the system has now said his name, it
does not say who he is either.

WHAT CHANGES, in one write:
  Sort                  MENU.content: "היי, " + the clock's word + the new tail. MENU.items stay (Sort's
                        follow-up reads them).
  Send menu             posts plain text: no input_select, no items.
  Send (manners v5)     afterMenu also knows the new intro (introNamed). Right after it, a name the draft
                        opens with is cut like a second greeting: keepName is false after the intro, and
                        still true after the old menu. The echo clause no longer gives buttons to a reply
                        that is only "<hello>, כאן מיכאל מהומי'ז. במה אוכל לעזור…?" (the 25 Aug canned opener),
                        because the intro carries none now. intro v1 is unchanged: it adds the name only
                        after the OLD menu, and the new intro is not that.
  Still the last word?  MENU also matches the new intro, so a burst after it is read past it, and the model
                        is told what the system sent.
  The prompt            the greeting paragraph quotes the new sentence and says it gave his name, so the next
                        reply neither greets nor says who he is; the tap paragraph no longer says the buttons
                        came with the greeting. 25,991 -> 25,850 characters.
  Memory                epoch 102 -> 103, so no buffer carries "the system did not introduce you".
Not changed: the options list (show_menu, "what can I do here?") keeps its buttons; a first message that is
not a bare hello still opens with the clock's greeting and the name, written by the model; the rep-tap
hello. The phone has no buttons, and its opener already names Michael: nothing owed there.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py. The bot in use is this workflow (Chatwoot,
since 10 Nov); the UChat copy is off and n8n_uchat.py refuses to switch it on.
"""
import copy
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 103
OLD_KEY = "={{ $json.to }}-102"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-11nov-before-hiintro.json")
VS = "️"   # the emoji variation selector inside Send's character classes

# Sort: the sentence, and "היי, " before the clock's word.
SORT_OLD = 'const MENU = {\n  content: HELLO + " ' + W.GREETING_TAIL_OCT + '",'
SORT_NEW = ("// 11 Nov (n8n_whatsapp_hiintro.py): the greeting introduces Michael, with no buttons. \"היי, \" and the\n"
            "// clock's word go first (\"היי\" alone before 05:00). `items` stay for the follow-up below.\n"
            "const HI = HH < 5 ? 'היי' : 'היי, ' + HELLO;\n"
            'const MENU = {\n  content: HI + " ' + W.GREETING_TAIL + '",')

# Send menu: plain text.
MENU_SEND_OLD = ("={{ JSON.stringify({ content: $json.menu.content, message_type: 'outgoing', content_type: "
                 "'input_select', content_attributes: { items: $json.menu.items } }) }}")
MENU_SEND_NEW = "={{ JSON.stringify({ content: $json.menu.content, message_type: 'outgoing' }) }}"

# Send: manners v5.
INTRO_RE = "/👋 כאן מיכאל מהומי'ז[.] במה אוכל לעזור לך היום[?]/"
MV_OLD = "const mv = 'manners v4';"
MV_NEW = "const mv = 'manners v5';"
AFTER_TAIL = ("/במה אפשר לעזור/.test(String(S.last_bot || '')) || lastOut.indexOf('👋 במה אפשר לעזור?') !== -1 || "
              "/👋 כאן הומי'ז[.] במה אפשר לעזור[?]/.test(lastOut);")
AFTER_OLD = "const afterMenu = " + AFTER_TAIL
AFTER_NEW = ("const introNamed = " + INTRO_RE + ".test(String(S.last_bot || '') + ' ' + lastOut); "
             "const afterMenu = introNamed || " + AFTER_TAIL)
KEEP_OLD = "const keepName = askedWho || afterMenu || repTap || (!mid && !ackNamed);"
KEEP_NEW = "const keepName = askedWho || (afterMenu && !introNamed) || repTap || (!mid && !ackNamed);"
# 11 Nov, 12:05 UTC: the first write left Send's own `greeting ||` branch. The canned greeting goes out Canned
# reply? -> Type for a moment -> Send (execution 173085: Sort greeting true, _menu false), not through Send menu,
# and that branch gave the owner's hello the intro WITH the two buttons. A greeting gets no buttons now; the old
# tails' echo alternatives still give a menu sentence of before 11 Nov its buttons.
GREET_BTN_OLD = "if (!two && ($('Sort').first().json.greeting || "
GREET_BTN_NEW = "if (!two && ("
ECHO_ALT = (" || (/מיכאל מהומי'ז/.test(t) && $('Sort').first().json.greeted !== true && "
            "/^(היי|הי|שלום|שלום רב|אהלן|בוקר טוב|צהריים טובים|ערב טוב)[,!.]?( (כאן |אני )?מיכאל מהומי'ז( כאן)?"
            "[.,!]?)? ?במה (אפשר|אוכל|נוכל) לעזור( לכם| לך| לכם היום| לך היום)?\\??$/.test(t.replace("
            "/[\\p{Extended_Pictographic}" + VS + "]/gu, '').replace(/\\s+/g, ' ').trim()))")

# Still the last word?: the new intro is the system's answer too.
LW_OLD = "const MENU = /👋 (?:כאן הומי'ז[.] )?במה אפשר לעזור[?]/;"
LW_NEW = ("// 11 Nov (n8n_whatsapp_hiintro.py): the greeting that introduces Michael is the system's answer too.\n"
          "const MENU = /👋 (?:כאן הומי'ז[.] )?במה אפשר לעזור[?]|" + INTRO_RE[1:-1] + "/;")

# The prompt, each edit exactly once (docs/features/11-whatsapp-bot/prompt.md carries the result).
PROMPT_EDITS = (
    ('כשמישהו רק מברך, המערכת עונה לו לבד, ולא אתה: ברכה לפי השעה בישראל ואחריה "' + W.GREETING_TAIL_OCT
     + '" — בוקר טוב בבוקר, צהריים טובים בצהריים, ערב טוב בערב.',
     'כשמישהו רק מברך, המערכת עונה לו לבד, ולא אתה: "היי", ברכה לפי השעה בישראל ואחריהן "' + W.GREETING_TAIL
     + '" — בוקר טוב בבוקר, צהריים טובים בצהריים, ערב טוב בערב.'),
    ('הוא עשה דבר אחד: שאל במה לעזור.', 'הוא עשה שני דברים: הציג אותך בשמך ושאל במה לעזור.'),
    ('את עצמך הוא לא הציג, וזה נשאר שלך: כשכתוב לך שזאת ההודעה הראשונה בשיחה,',
     'כשכתוב לך שזאת ההודעה הראשונה בשיחה,'),
    ('הברכה כבר ניתנה והשיחה כבר נפתחה. אז אתה לא מברך שוב: אתה אומר מי אתה, באותה קלילות, וממשיך ישר לעניין.',
     'הברכה כבר ניתנה, השם שלך כבר נאמר והשיחה כבר נפתחה. אז אתה לא מברך שוב ולא אומר שוב מי אתה: אתה ממשיך ישר '
     'לעניין.'),
    ('השם, רק בהודעה הראשונה בשיחה או אחרי הברכה של המערכת; הכפתורים לא שייכים לכאן,',
     'השם, רק בהודעה הראשונה בשיחה; הכפתורים לא שייכים לכאן,'),
    ('הלחיצה הזאת היא הרגע שבו הוא פוגש אותך בפעם הראשונה, והתשובה שלך עליה היא מה שהוא ירגיש לגבי כל השירות:',
     'התשובה שלך על הלחיצה הזאת היא מה שהוא ירגיש לגבי כל השירות:'),
    ('גם לחיצה היא הודעה, ואתה אומר בה מי אתה, גם למי שכבר דיבר איתך קודם. את הכפתורים הוא קיבל יחד עם הברכה של '
     'המערכת, ולכן בלחיצה על אחד מהם הברכה כבר ניתנה ואתה לא חוזר עליה: השם שלך, ומשם ישר לעניין.',
     'את הכפתורים הוא קיבל אחרי שכבר הוצגת לו, ולכן בלחיצה על אחד מהם לא מברכים ולא אומרים שוב מי אתה: ישר לעניין.'),
)


def node_compiles(code, what):
    """A Code node's body must parse: n8n runs it inside an async function, so top-level return is fine."""
    js = ("const src = require('fs').readFileSync(0, 'utf8');"
          "const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;"
          "try { new AsyncFunction('$input', '$', '$json', '$node', '$workflow', '$execution', '$getWorkflowStaticData',"
          " 'items', src); } catch (e) { console.log(e.message); process.exit(1); }")
    r = subprocess.run(["node", "-e", js], input=code, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        sys.exit("REFUSING: %s would not compile: %s" % (what, (r.stdout or r.stderr).strip()[:200]))


def hiintro(wf):
    """The workflow with the edits above; each anchor must occur exactly once. Does not touch memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    sort = by["Sort"]["parameters"]
    if "const HI " in sort["jsCode"]:
        sys.exit("REFUSING: Sort already has a `const HI`. Read live first.")
    sort["jsCode"] = once(sort["jsCode"], SORT_OLD, SORT_NEW)
    by["Send menu"]["parameters"]["jsonBody"] = once(by["Send menu"]["parameters"]["jsonBody"], MENU_SEND_OLD,
                                                     MENU_SEND_NEW)
    body = by["Send"]["parameters"]["jsonBody"]
    for old, new in ((MV_OLD, MV_NEW), (AFTER_OLD, AFTER_NEW), (KEEP_OLD, KEEP_NEW), (ECHO_ALT, ""),
                     (GREET_BTN_OLD, GREET_BTN_NEW)):
        body = once(body, old, new)
    by["Send"]["parameters"]["jsonBody"] = body
    lw = by["Still the last word?"]["parameters"]
    lw["jsCode"] = once(lw["jsCode"], LW_OLD, LW_NEW)
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
    at_103 = key == NEW_KEY and W.GREETING_TAIL in by["Sort"]["parameters"]["jsCode"] \
        and MV_NEW in by["Send"]["parameters"]["jsonBody"]
    if at_103 and GREET_BTN_OLD not in by["Send"]["parameters"]["jsonBody"]:
        print("Nothing to do. Live already greets with Michael's intro and no buttons, epoch %d." % EPOCH)
        return
    if at_103:
        # The 12:02 write is live; only Send's greeting branch is left (code only, the epoch stays).
        new = copy.deepcopy(live)
        snd = {n["name"]: n for n in new["nodes"]}["Send"]["parameters"]
        snd["jsonBody"] = once(snd["jsonBody"], GREET_BTN_OLD, GREET_BTN_NEW)
    elif key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 102's. Read live first." % key)
    else:
        new = hiintro(live)
    if prompt_of(new) != W.system_prompt():
        sys.exit("REFUSING: the would-be prompt is not docs/features/11-whatsapp-bot/prompt.md's. "
                 "Edit the document first; live follows it.")
    nb = {n["name"]: n for n in new["nodes"]}
    node_compiles(nb["Sort"]["parameters"]["jsCode"], "Sort")
    node_compiles(nb["Still the last word?"]["parameters"]["jsCode"], "Still the last word?")
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("greeting : \"%s\" -> \"%s\", no buttons" % (W.GREETING_TAIL_OCT, W.GREETING_TAIL))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("tools    : %s (unchanged: %s)" % (W.epoch_hash(tools_of(new)), tools_of(new) == tools_of(live)))
    print("Send     : manners v5; the intro-only echo and Send's own greeting branch give no buttons")
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
    print("  Send's greeting branch: %s" % ("gone" if GREET_BTN_OLD not in bb["Send"]["parameters"]["jsonBody"]
                                          else "STILL THERE"))
    print("  prompt %s (want %s); memory key %s; Sort's tail %s; Send menu %s; manners v5 %s; last word %s"
          % (W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)),
             bb["Conversation so far"]["parameters"]["sessionKey"],
             "present" if W.GREETING_TAIL in bb["Sort"]["parameters"]["jsCode"] else "MISSING",
             "plain text" if "input_select" not in bb["Send menu"]["parameters"]["jsonBody"] else "STILL BUTTONS",
             "present" if MV_NEW in bb["Send"]["parameters"]["jsonBody"] else "MISSING",
             "knows the intro" if INTRO_RE[1:-1] in bb["Still the last word?"]["parameters"]["jsCode"] else "MISSING"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
