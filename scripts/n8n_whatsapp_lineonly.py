# -*- coding: utf-8 -*-
"""An emergency gets our emergency line only: no ticket, no note (11 Nov 2026, night, epoch 105; Send's danger v8).

    python scripts/n8n_whatsapp_lineonly.py              # dry run
    python scripts/n8n_whatsapp_lineonly.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_lineonly.py --apply      # write it
    python scripts/n8n_whatsapp_lineonly.py --restore    # put the snapshot back

WHY. The owner's retest of the line (15:54-16:02 UTC) opened urgent tickets 255-1443-26 and 255-1444-26, and from
his number they opened in Homies' OXS too. On seeing 255-1444-26 on his phone: "it still open a call", then "I DONT
WANT IT TO OPEN A TICKET CALL IN OXS JUST POINT THEM TO THE EMERGENCY HOTLINE WE HAVE". The hotline is a department
of its own ("a direct hotline specially built for that its a department"). Epoch 104 had read his "redirect them
here" as the line beside the urgent ticket. Gas has worked this way since 5 Nov: no ticket, no note, no building.

WHERE THE TICKET CAME FROM. Two calls on every emergency turn: open_request with urgency emergency, and
notify_team with reason emergency, whose note also makes debt-tools' backstop open a needs_review ticket, mirrored
into OXS for a mirrored number (n8n_whatsapp_gas.py found that on 5 Nov). Both were asked for by the prompt and by
the tool texts.

WHAT CHANGES, in one write:
  The prompt   an emergency (a person in danger or hurt, someone stuck in a lift, fire, smoke, flooding, water
               near electricity) opens no ticket, even on the common parts, writes no note and asks no building.
               His first message about it is a short caring word and then our line, word for word, and it ends
               there, with no question; pressed, the line again in other words. "Nobody is sent anywhere", the
               office phone and the line's own fact line say "emergency" where they said "urgent fault", and the
               rule that every message ends with a question excepts the messages about an emergency.
  The tools    open_request: never for an emergency (or gas), and urgency loses "emergency"; notify_team: never
               for an emergency (or gas), and reason loses "emergency"; verify_address: no "location during an
               emergency".
  Send         danger v8. An emergency turn now has no tool, so the step also wakes on our line in the reply
               (when no other tool ran) and still cuts advice, other numbers and "on the way". When a cut takes the
               line, the line comes back, and when nothing is left, the line alone goes. An urgent ticket found
               only in the chat's past adds no number to a reply that gives our line.
  Memory       epoch 104 -> 105.
Not changed: gas (its sentence already carries the line), a lift fault with nobody stuck (a ticket, the lift
company), line v1, the inject. The incoming phone agent's twin is owed: it still opens an urgent ticket.

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
from n8n_whatsapp_hotline import HOTS, expr_compiles  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 105
OLD_KEY = "={{ $json.to }}-104"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-11nov-before-lineonly.json")

EMERGENCY_OLD = (
    "מישהו בסכנה: אתה פותח מיד קריאת שירות דחופה ורושם הערה דחופה, לפני כל שאלה שאפשר לדחות. וזה לא רק כשמישהו "
    "בסכנה, אלא תמיד: אתה לא נותן מספרי חירום, לא הוראות בטיחות ולא הפניה לגורם אחר, לא משטרה, לא ביטוח, לא עירייה "
    "ולא עורך דין, ולא אומר מה לעשות ולא מה לא לעשות, גם כששואלים אותך ישירות מה לעשות עכשיו, וגם כשזה נשמע לך "
    "מובן מאליו: מה שיש לך לתת זה שפתחת קריאה דחופה, עם המספר שחזר, ועוד דבר אחד, וזאת החלטה של ההנהלה: על כל "
    "תקלה דחופה, בכל שעה, אתה גם מפנה אותו בנימוס למוקד החירום הטלפוני שלנו, 077-6687949, שקיים בדיוק בשביל מקרים "
    "כאלה. את זה הוא שומע כבר בהודעה הראשונה שלך על המקרה, גם אם עוד לא פתחת את הקריאה, ובמילים שמזמינות אותו "
    "להתקשר, לא כאילו אתה מעביר אותו הלאה. אתה לא שולח עזרה, לא אומר שמישהו בדרך, ולא מציע שיתקשרו אליו. גם הכלל "
    "הזה הוא בשבילך, לא בשבילו: מה שהוא שומע ממך זה מה שעשית, ולא מה שאתה לא נותן. ואם הוא לוחץ ומבקש עוד, אתה "
    "אומר לו בפשטות, במילים שלך, מה עשית ומה המספר של הקריאה, וגם את המוקד, ולא מוסיף שאלה: זה לא הרגע לשאול במה "
    "עוד אפשר לעזור.")
EMERGENCY_NEW = (
    "מקרה חירום, כמו מישהו בסכנה או שנפגע, מישהו תקוע במעלית, שריפה, עשן, הצפה או מים ליד חשמל, שייך כולו למוקד "
    "החירום הטלפוני שלנו, שקיים בדיוק בשביל מקרים כאלה, וזאת החלטה של ההנהלה: אתה לא פותח קריאה, גם כשזאת תקלה "
    "ברכוש המשותף, לא רושם הערה ולא שואל באיזה בניין או באיזו דירה. מה שיש לך לתת, כבר בהודעה הראשונה שלך על "
    "המקרה, הוא מילה קצרה ואכפתית משלך, ואחריה המשפט הזה, מילה במילה: \"" + HOTS + "\" ושם ההודעה נגמרת, בלי "
    "שאלה. וזה לא רק במקרה חירום, אלא תמיד: אתה לא נותן מספרי חירום אחרים, לא הוראות בטיחות ולא הפניה לגורם אחר, "
    "לא משטרה, לא ביטוח, לא עירייה ולא עורך דין, ולא אומר מה לעשות ולא מה לא לעשות, גם כששואלים אותך ישירות מה "
    "לעשות עכשיו, וגם כשזה נשמע לך מובן מאליו. אתה לא שולח עזרה, לא אומר שמישהו בדרך, ולא מציע שיתקשרו אליו. גם "
    "הכלל הזה הוא בשבילך, לא בשבילו: מה שהוא שומע ממך זה המוקד, ולא מה שאתה לא נותן. ואם הוא לוחץ, שואל מה לעשות "
    "או מתי מישהו יגיע, הוא שומע ממך שוב, בפשטות ובמילים אחרות, שהמוקד הוא המקום לזה עכשיו, עם המספר, ולא מוסיף "
    "שאלה: זה לא הרגע לשאול במה עוד אפשר לעזור.")

# The prompt, each edit exactly once (docs/features/11-whatsapp-bot/prompt.md carries the result).
PROMPT_EDITS = (
    ("דייר לא נשלח ממך לשום מקום, חוץ ממקרה של גז ומתקלה דחופה, שעליהם כתוב בהמשך.",
     "דייר לא נשלח ממך לשום מקום, חוץ ממקרה של גז וממקרה חירום, שעליהם כתוב בהמשך."),
    ("והטלפון גם לכל תקלה דחופה.", "והטלפון גם לכל מקרה חירום."),
    (EMERGENCY_OLD, EMERGENCY_NEW),
    ("זאת ההודעה היחידה שמותר לה להסתיים בלי שאלה, חוץ מהתשובה למי שלוחץ כשמישהו בסכנה.",
     "זאת ההודעה היחידה שמותר לה להסתיים בלי שאלה, חוץ מההודעות על מקרה חירום."),
    ("זה גם המספר של מוקד החירום הטלפוני שלנו, שעונה על תקלות דחופות גם מחוץ לשעות הפעילות.",
     "זה גם המספר של מוקד החירום הטלפוני שלנו, שעונה על מקרי חירום בכל שעה."),
)

# The tools: (node, parameter, old, new), each anchor exactly once.
TOOL_EDITS = (
    ("open_request", "toolDescription",
     "A note (notify_team) does NOT open a ticket. If you already called notify_team and the address only arrives "
     "afterwards — which is what an emergency looks like, because the person comes before the address — that is the "
     "moment to call this.\n",
     "Never for an emergency: a person in danger or hurt, someone trapped in a lift, fire, smoke, flooding or water "
     "near electricity gets our emergency line only, with no ticket and no note, even when it is a fault in the "
     "common parts. Neither is gas. A note (notify_team) does NOT open a ticket.\n"),
    ("open_request", "toolDescription", " An emergency never waits for a name: it opens without one.", ""),
    ("open_request", "jsonBody",
     "Infer this; never ask the resident for it. Use emergency only for flooding, fire or someone trapped in a lift. "
     "Gas is never a ticket. One of low/normal/high/emergency.",
     "Infer this; never ask the resident for it. An emergency is never a ticket, and neither is gas. "
     "One of low/normal/high."),
    ("notify_team", "toolDescription",
     "Call it for a PERSON in a bad state, the moment you hear it, before anything that can wait: somebody shut in a "
     "lift, on a roof, in a stairwell or a car park; somebody hurt, alone, frightened or panicking; anybody reporting "
     "fire, flooding, or water near electricity. Reason `emergency`. Never for gas: a gas report gets no note and no "
     "ticket, only the line about the gas company. It does not open the ticket and does not replace it; go on and "
     "open the ticket too.\n",
     "Never for an emergency or for gas: a person in danger or in a bad state (shut in a lift, on a roof, in a "
     "stairwell or a car park; hurt, alone, frightened or panicking), fire, smoke, flooding, water near electricity, "
     "or gas gets no note and no ticket, only our emergency line, after the gas company for gas, as the prompt "
     "says.\n"),
    ("notify_team", "jsonBody",
     "quote = a price quote; emergency = a person in danger; caller_request = they asked for a person; other = "
     "anything else past you. One of payment/billing/move/contract/quote/emergency/caller_request/other.",
     "quote = a price quote; caller_request = they asked for a person; other = anything else past you. Never an "
     "emergency or gas: those get no note. One of payment/billing/move/contract/quote/caller_request/other."),
    ("notify_team", "jsonBody",
     "Send it every time: it is what the team reads, and on an emergency it is the only account that reaches them.",
     "Send it every time: it is what the team reads."),
    ("notify_team", "jsonBody", "operations = faults, technicians, works, emergencies;",
     "operations = faults, technicians, works;"),
    ("verify_address", "toolDescription",
     "a resident asking whether we manage their building, or grounding a location during an emergency.",
     "a resident asking whether we manage their building."),
)
# Nothing left anywhere in the tools that asks for an emergency ticket or note.
TOOL_LEFTOVERS = ("Reason `emergency`", "low/normal/high/emergency", "go on and open the ticket too",
                  "emergency = a person in danger", "An emergency never waits", "during an emergency",
                  "quote/emergency/caller_request")

# Send, danger v8: wake on our line too, never add an old ticket's number to a reply that gives it, and give the
# line back when a cut takes it (`now`, `ref`, HOT and HOTS are the step's own).
SEND_EDITS = (
    ("const dv = 'danger v7';", "const dv = 'danger v8';"),
    ("if (!now && !URGENT.test(s) && (other || !URGENT.test(lb))) return s;",
     "const hot = /0?77[-\\s]?668[-\\s]?7949/.test(s); "
     "if (!now && !URGENT.test(s) && (other || (!URGENT.test(lb) && !hot))) return s;"),
    ("const withHot = (t) => { if (!now || !t || HOT.test(t)) return t;",
     "const withHot = (t) => { if (!(now || hot) || !t || HOT.test(t)) return t;"),
    ("if (ref && out.indexOf(ref) === -1) out = (out ? out + ' ' : '') + 'הקריאה הדחופה שלך פתוחה, מספר ' + ref + '.'; "
     "return withHot(out || s); })();",
     "if (ref && (now || !hot) && out.indexOf(ref) === -1) out = (out ? out + ' ' : '') + 'הקריאה הדחופה שלך פתוחה, "
     "מספר ' + ref + '.'; return withHot(out || (hot ? HOTS : s)); })();"),
)


def lineonly(wf):
    """The workflow with every edit above; each anchor must occur exactly once. Does not touch memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    body = by["Send"]["parameters"]["jsonBody"]
    if "const hot = " in body:
        sys.exit("REFUSING: Send's danger step already wakes on our line. Read live first.")
    for old, new in SEND_EDITS:
        assert "}}" not in new and "{{" not in new, "an edit would end the expression early"
        body = once(body, old, new)
    by["Send"]["parameters"]["jsonBody"] = body
    agent = by["Answer the resident"]["parameters"]
    for old, new in PROMPT_EDITS:
        agent["options"]["systemMessage"] = once(agent["options"]["systemMessage"], old, new)
    for node, key, old, new in TOOL_EDITS:
        p = by[node]["parameters"]
        p[key] = once(p[key], old, new)
    left = [(n["name"], w) for n in out["nodes"] if n["type"].endswith("Tool")
            for w in TOOL_LEFTOVERS if w in str(n.get("parameters", {}))]
    assert not left, "the tools still ask for an emergency ticket or note: %s" % left
    sm = agent["options"]["systemMessage"]
    for w in ("קריאת שירות דחופה", "רושם הערה דחופה", "שפתחת קריאה דחופה"):
        assert w not in sm, "the prompt still asks for an urgent ticket: %s" % w
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and "const dv = 'danger v8';" in by["Send"]["parameters"]["jsonBody"]:
        print("Nothing to do. Live already gives an emergency our line only, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 104's. Read live first." % key)
    if W.MEMORY_EPOCH != EPOCH:
        sys.exit("REFUSING: n8n_whatsapp.MEMORY_EPOCH is %d, not %d. Move the repo first." % (W.MEMORY_EPOCH, EPOCH))

    new = lineonly(live)
    if prompt_of(new) != W.system_prompt():
        sys.exit("REFUSING: the would-be prompt is not docs/features/11-whatsapp-bot/prompt.md's. "
                 "Edit the document first; live follows it.")
    W.check_memory_epoch(prompt=prompt_of(new), tools=tools_of(new))
    nb = {n["name"]: n for n in new["nodes"]}
    expr_compiles(nb["Send"]["parameters"]["jsonBody"], "Send")
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("tools    : %s -> %s" % (W.epoch_hash(tools_of(live)), W.epoch_hash(tools_of(new))))
    print("Send     : danger v8, an emergency turn with no tool still has its advice cut and keeps our line")
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
    print("  prompt %s (want %s); tools %s (want %s); memory key %s; danger v8 %s"
          % (W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)), W.epoch_hash(tools_of(back)),
             W.epoch_hash(tools_of(new)), bb["Conversation so far"]["parameters"]["sessionKey"],
             "present" if "const dv = 'danger v8';" in sb else "MISSING"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
