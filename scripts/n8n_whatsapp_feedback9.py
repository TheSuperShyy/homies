# -*- coding: utf-8 -*-
"""Yariv's written review of the simulated run (9 Nov 2026, epoch 100).

    python scripts/n8n_whatsapp_feedback9.py              # dry run
    python scripts/n8n_whatsapp_feedback9.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_feedback9.py --apply      # write it
    python scripts/n8n_whatsapp_feedback9.py --restore    # put the snapshot back

WHY. Yariv marked the "Michael Simulated Run" page (the 3 Nov run, local/artifacts/michael-simulation) and
wrote a comment under most checks; the owner passed them on as screenshots on 9 Nov ("Feedbacks"). The run
is from 3 Nov, so gas (5 Nov) and the manager sentence of 7.2 (manager v2, 8 Nov) had already changed.
What is still to do, in his words:
  2.1 (correct, plus): for a lift, also the fault, the lift's number if there is more than one, the floor
      it is stuck on.
  2.2 (wrong): "…מספר הקריאה בהומיז הוא 255-1600-26. אנחנו מעבירים את המידע והמשך הטיפול לחברת
      המעליות, ועוקבים אחריה."
  2.3 / 2.4 (wrong / same tone): "אני מצטער, אבל זה לא תלוי בנו, זה תלוי בחברת המעליות האחראית על
      השירות והתחזוקה למעלית, אנחנו עושים את מירב המאמצים מולם."
  4.1 (wrong): the lift is in the lift company's hands; we pass the request on and press them.
  3.2 (wrong): water from the ceiling is an event in the private flat: first a professional on the
      tenant's behalf, unless it is known to come from a failure in the common property.
  5.2 (wrong): a standing order is no OXS call: an email to collections (the address is now his, in
      .env), and the tenant hears that someone from the team will call him.
  6.2 / 6.3: before or after office hours, an urgent call that needs an answer now goes to "our
      telephone emergency centre", 077-6687949.

WHAT CHANGES
  (A blind Claude-played run of scripts/wa_qa_feedback9.json passed 21/21, but its second "when??" dropped
  the lift company: the prompt's general "not the same reason twice" won over "גם כשהוא שואל שוב". The lift
  line now says it outright: on a second "when" the lift company stays, beside what Michael does now.)
  - The prompt: the lift (a fact: the lift company repairs, we pass it on and follow it, when depends on
    them; said when a lift call opens, when he asks when, and on its status) and its intake details; the
    leak; the standing order's callback; the emergency line after hours. The one-voice sentence names its
    two exceptions (the lift company, the collections team), and "nobody is sent anywhere" its second
    (an urgent fault while the office is closed).
  - The inject: the clock line says when it is outside office hours (Sun-Thu 09:00-17:00, Israel).
  - request_standing_order: what he hears includes the collections team's call.
  - open_request: a leak from "the flat above" is no longer named a building fault.
  - Send: danger v6 keeps a sentence whose only "advice" is our own emergency line, after hours only;
    promise v6 keeps "someone will call you" on a turn that recorded a standing order.
  - Memory: epoch 99 -> 100.
Not changed: gas (the gas company's line, at any hour: Yariv's change 2), the menu (1.1 is a question
for Yariv), the manager reply (7.2's sentence is gone since manager v2), the phone agents.

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

EPOCH = 100
OLD_KEY = "={{ $json.to }}-99"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-09nov-before-feedback9.json")

LIFT_FACT = (
    "- **מעלית:** את התיקון עושה חברת המעליות שאחראית על השירות והתחזוקה של המעלית בבניין, ולא אנחנו. "
    "קריאה על מעלית נפתחת אצלנו, ואנחנו מעבירים לחברת המעליות את המידע ואת המשך הטיפול, עוקבים אחרי "
    "הקריאה ולוחצים עליהם לטפל בה בדחיפות. מתי יבואו לתקן תלוי בהם, לא בנו. את זה הדייר שומע ממך, "
    "במילים שלך, כשאתה פותח קריאה על מעלית, יחד עם מספר הקריאה בהומי'ז, וכשהוא שואל מתי יתקנו אותה "
    "או מה המצב שלה. וגם כשהוא שואל שוב מתי, חברת המעליות נשארת בתשובה, לצד מה שאתה עושה עכשיו בשבילו.")

PROMPT_EDITS = [
    # The one voice, and nobody sent anywhere: each names its exceptions, written further on.
    ("אף אחד אחר לא מופיע בהודעות שלך כמי שבודק, רואה, מטפל, יודע או יחזור אליו, לא צוות, לא מנהל ולא "
     "הנהלה, ואתה לא מספר שהעברת משהו למישהו. דייר לא נשלח ממך לשום מקום, חוץ ממקרה של גז.",
     "אף אחד אחר לא מופיע בהודעות שלך כמי שבודק, רואה, מטפל, יודע או יחזור אליו, לא צוות, לא מנהל ולא "
     "הנהלה, ואתה לא מספר שהעברת משהו למישהו, חוץ מחברת המעליות ומצוות הגבייה, וגם עליהם רק מה שכתוב "
     "בהמשך. דייר לא נשלח ממך לשום מקום, חוץ ממקרה של גז ומתקלה דחופה מחוץ לשעות הפעילות, שעליהם כתוב "
     "בהמשך."),
    # 2.1: what the lift company needs.
    ("וכשיש לך מה קרה ובאיזה בניין, הכלי בא לפני המילים.",
     "וכשיש לך מה קרה ובאיזה בניין, הכלי בא לפני המילים. על מעלית, חברת המעליות צריכה לדעת גם מה קורה "
     "איתה, באיזו מעלית מדובר כשיש בבניין יותר מאחת, ובאיזו קומה היא תקועה: מה שהוא עוד לא אמר לך מזה "
     "אתה שואל באותה שאלה שבה אתה מבקש בניין ודירה, או מיד אחרי שפתחת את הקריאה, ומוסיף לקריאה את מה "
     "שיענה."),
    # 3.2: a leak in the flat starts as the flat's.
    ("ומה שלא ברור ממי בא, נזילה מלמעלה, מים בקיר, הבניין בודק: קריאה.",
     "נזילה או רטיבות בתוך הדירה, גם כשהמים יורדים מהתקרה או יוצאים מהקיר, היא אחרת, וזאת החלטה של "
     "ההנהלה: זה אירוע בדירה הפרטית, ולכן קודם כל צריך בעל מקצוע מטעם הדייר שיבדוק מאיפה זה בא. את זה "
     "אתה כן אומר לו, בעדינות ובמילים שלך, ושואל אם כבר התברר שזה בא מתקלה ברכוש המשותף, כמו הצנרת "
     "הראשית או הגג; אם כן, זאת תקלה של הבניין, ופותחים עליה קריאה."),
    # 5.2: the collections team calls.
    ("אתה רושם את הבקשה שלו בכלי שיש לך לזה, ורק בו, בלי קריאת שירות ובלי הערה.",
     "אתה רושם את הבקשה שלו בכלי שיש לך לזה, ורק בו, בלי קריאת שירות ובלי הערה, ואומר לו שרשמת אותה "
     "ושמישהו מצוות הגבייה ייצור איתו קשר בטלפון, בלי מתי."),
    # 6.2 / 6.3: the emergency line, only while the office is closed.
    ("הטלפון והמייל של המשרד הם רק למי שמבקש אותם במפורש או ששואל איך מגיעים למשרד.",
     "הטלפון והמייל של המשרד הם רק למי שמבקש אותם במפורש, למי ששואל איך מגיעים למשרד, ולתקלה דחופה "
     "מחוץ לשעות הפעילות."),
    ("מה שיש לך לתת זה שפתחת קריאה דחופה, עם המספר שחזר, וזה כל מה שיש לך.",
     "מה שיש לך לתת זה שפתחת קריאה דחופה, עם המספר שחזר, וזה כל מה שיש לך. רק כשכתוב לך שעכשיו מחוץ "
     "לשעות הפעילות של המשרד, יש לזה תוספת אחת, וזאת החלטה של ההנהלה: על תקלה דחופה שצריכה מענה מיידי "
     "אתה גם מפנה אותו למוקד החירום הטלפוני שלנו, 077-6687949, שעונה גם כשהמשרד סגור."),
    ("אתה אומר לו בפשטות, במילים שלך, מה עשית ומה המספר של הקריאה, ולא מוסיף שאלה",
     "אתה אומר לו בפשטות, במילים שלך, מה עשית ומה המספר של הקריאה, ומחוץ לשעות הפעילות גם את המוקד, ולא "
     "מוסיף שאלה"),
    ("- **טלפון:** 077-6687949. זה גם המספר לתקלות דחופות; אין קו חירום נפרד.",
     "- **טלפון:** 077-6687949. זה גם המספר של מוקד החירום הטלפוני שלנו, שעונה על תקלות דחופות גם מחוץ "
     "לשעות הפעילות."),
    # 2.2, 2.3, 2.4, 4.1: the lift company, as a fact, with when he hears it.
    ("- **אחריות:** רכוש משותף על ועד הבית וחברת הניהול יחד; רכוש פרטי על הדייר.",
     "- **אחריות:** רכוש משותף על ועד הבית וחברת הניהול יחד; רכוש פרטי על הדייר.\n" + LIFT_FACT),
]

TOOL_EDITS = {
    "request_standing_order": [
        ("toolDescription",
         "What you tell them is that you recorded their request for a standing order, with its number. It is "
         "not a message to anyone, so never who will handle it, contact them or when.",
         "What you tell them is that you recorded their request for a standing order, with its number, and "
         "that someone from the collections team will phone them about it. Never when, and nothing about how "
         "it is set up."),
    ],
    "open_request": [
        ("jsonBody",
         "'apartment' for a building-caused fault that shows inside a flat: a leak from the riser or the flat "
         "above, a blocked main stack;",
         "'apartment' for a building-caused fault that shows inside a flat, once it is known to come from the "
         "common property: a leak from the riser or the roof, a blocked main stack;"),
    ],
}

# The clock line every message ends with: outside office hours it says so. toFormat, not .hour, so the
# test stubs (which have toFormat and weekday only) read it too. No "}}" may appear: one expression.
INJECT_OLD = ("['ראשון','שני','שלישי','רביעי','חמישי','שישי','שבת'][$now.setZone('Asia/Jerusalem').weekday % 7] "
              "+ '.]'")
INJECT_NEW = ("['ראשון','שני','שלישי','רביעי','חמישי','שישי','שבת'][$now.setZone('Asia/Jerusalem').weekday % 7] "
              "+ ((() => { const z = $now.setZone('Asia/Jerusalem'); const h = parseInt(z.toFormat('HH:mm'), 10); "
              "return (z.weekday === 5 || z.weekday === 6 || h < 9 || h >= 17) ? ', מחוץ לשעות הפעילות של המשרד' "
              ": ''; })()) + '.]'")

# Send, danger v6: after hours a sentence whose only "advice" is our own line and a verb of calling stays.
# The same hours as the inject; $now is n8n's, and a missing one (a test without it) reads as open.
DANGER_DEFS = (
    "let closed = false; try { const z = $now.setZone('Asia/Jerusalem'); const h = parseInt(z.toFormat('HH:mm'), 10); "
    "closed = z.weekday === 5 || z.weekday === 6 || h < 9 || h >= 17; } catch (e) { closed = false; } "
    "const HOT = /0?77[-\\s]?668[-\\s]?7949/; "
    "const CALLV = /(^|[\\s,])(?:ו|ש|וש)?(?:תתקשר|תתקשרי|תתקשרו|להתקשר|התקשר|התקשרי|התקשרו|לחייג|חייג|חייגי|חייגו|תחייג|תחייגי)(?=[\\s,.!?:;]|$)/g; "
    "const hotline = (p) => closed && HOT.test(p) && !ADVICE.test(p.split(HOT).join(' ').replace(CALLV, (m, a) => a)); ")
# Send, promise v6: on a turn whose tools recorded a standing order, "someone will call you" is the truth.
PROMISE_DEFS = (
    "let SO = false; try { const st = []; for (const x of ($('Answer the resident').first().json.intermediateSteps || [])) st.push(x); "
    "try { for (const x of ($('Try again').first().json.first_steps || [])) st.push(x); } catch (e) { } "
    "SO = st.some((x) => ((((x || { }).action || { }).tool) || (x || { }).tool) === 'request_standing_order' "
    "&& /\\\\*\"(?:recorded|already_recorded)\\\\*\"\\s*:\\s*true/.test(String((x || { }).observation || ''))); } "
    "catch (e) { SO = false; } const CB = /^(?:ייצרו|יצרו|ייצור|יצור|יחזרו|יחזור|תחזור) /; ")
SEND_EDITS = [
    ("const dv = 'danger v5';", "const dv = 'danger v6';"),
    ("const promised = (p) => {", DANGER_DEFS + "const promised = (p) => {"),
    ("const bad = ADVICE.test(p) || promised(p);", "const bad = (ADVICE.test(p) && !hotline(p)) || promised(p);"),
    ("const pv = 'promise v5';", "const pv = 'promise v6';"),
    ("const hits = (s) => Array.from(s.matchAll(PG)).filter((h) => !exempt(s, h));",
     PROMISE_DEFS + "const hits = (s) => Array.from(s.matchAll(PG)).filter((h) => !exempt(s, h) && !(SO && CB.test(h[3])));"),
]


def feedback9(wf):
    """The workflow with every edit above; each anchor must occur exactly once. Does not touch memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    agent = by["Answer the resident"]["parameters"]
    sm = agent["options"]["systemMessage"]
    for old, new in PROMPT_EDITS:
        sm = once(sm, old, new)
    agent["options"]["systemMessage"] = sm
    agent["text"] = once(agent["text"], INJECT_OLD, INJECT_NEW)
    for tool, edits in TOOL_EDITS.items():
        p = by[tool]["parameters"]
        for key, old, new in edits:
            p[key] = once(p[key], old, new)
    p = by["Send"]["parameters"]
    body = p["jsonBody"]
    for _, new in SEND_EDITS + [(None, INJECT_NEW)]:
        assert "}}" not in new and "{{" not in new, "an edit would end the expression early"
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
    if key == NEW_KEY and LIFT_FACT in prompt_of(live):
        print("Nothing to do. Live already has Yariv's 9 Nov review, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 99's. Read live first." % key)

    new = feedback9(live)
    nb = {n["name"]: n for n in new["nodes"]}
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("inject   : %s -> %s" % (W.epoch_hash(by["Answer the resident"]["parameters"]["text"]),
                                    W.epoch_hash(nb["Answer the resident"]["parameters"]["text"])))
    print("tools    : %s -> %s" % (W.epoch_hash(tools_of(live)), W.epoch_hash(tools_of(new))))
    print("memory   : %s -> %s (every buffer starts fresh)" % (OLD_KEY, NEW_KEY))
    print("changed  : %s" % ", ".join(n["name"] for n in new["nodes"] if n != by[n["name"]]))

    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        NP.dump(new["nodes"], new["connections"], path)
        print("dumped   : %s (the would-be workflow, secret replaced)" % path)
    if "--prompt" in sys.argv:
        path = sys.argv[sys.argv.index("--prompt") + 1]
        with open(path, "w", encoding="utf-8") as f:
            f.write(prompt_of(new))
        print("prompt   : written to %s" % path)
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
    print("  prompt %s (want %s); tools %s (want %s); memory key %s; danger v6 %s; promise v6 %s"
          % (W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)), W.epoch_hash(tools_of(back)),
             W.epoch_hash(tools_of(new)), bb["Conversation so far"]["parameters"]["sessionKey"],
             "present" if "const dv = 'danger v6'" in bb["Send"]["parameters"]["jsonBody"] else "MISSING",
             "present" if "const pv = 'promise v6'" in bb["Send"]["parameters"]["jsonBody"] else "MISSING"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
