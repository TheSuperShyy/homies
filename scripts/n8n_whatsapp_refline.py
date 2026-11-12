# -*- coding: utf-8 -*-
"""An emergency gets the owner's own reply as its model, in Michael's words (12 Nov 2026, epoch 108).

    python scripts/n8n_whatsapp_refline.py                       # dry run
    python scripts/n8n_whatsapp_refline.py --dump F              # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_refline.py --dump F --labels-only  # the labels and the key only (TDD: cases fail)
    python scripts/n8n_whatsapp_refline.py --apply               # write it
    python scripts/n8n_whatsapp_refline.py --restore             # put the snapshot back

WHY. On 12 Nov the owner sent the reply he wants for an emergency: "אני רק העוזר הדיגיטלי ואין לי אפשרות לתת
מענה מידיי,בבקשה תתקשר למוקד החירום שלנו כדי תוכל לקבל מענה בהקדם , 0776687949" and "this should be a format it
should still be dynamic but that is the reference". Since epoch 105 the prompt had asked for a caring word and then
our fixed sentence, word for word ("למקרי חירום יש לנו מוקד טלפוני ייעודי, ואפשר להתקשר אליו עכשיו").

WHAT SEND DID TO HIS REFERENCE (live, epoch 107, run through the live code before this was written):
  - "...כדי שתוכל לקבל מענה בהקדם: 077-6687949." went out as "אני רק העוזר הדיגיטלי ואין לי אפשרות לתת מענה
    מיידי." with no number at all: promise v7 read "בהקדם" as our promise and cut the sentence it was in, and
    danger v8 could not give the line back, because nothing in the turn was left to say it was an emergency;
  - "כמה שיותר מהר" and "הכי מהר" next to our line read as "on the way" to danger v8, which cut the sentence and
    put the old fixed sentence in its place; "באופן מיידי" in "I can't answer immediately" did the same;
  - line v1 turned "בבקשה תתקשר" into "אפשר להתקשר", "please" and all;
  - voice v2 cut a "כדי שיוכלו..." clause even when our number was in it;
  - mid-chat, manners v5 cut "אני מיכאל, " from "אני מיכאל, העוזר הדיגיטלי..." and left a broken opening.

WHAT CHANGES, in one write:
  The prompt   his first message about an emergency is "a message like this", the owner's reference (spelling
               and punctuation mended): the words are Michael's and fit the case, and three things are always in
               it: he is only the digital assistant and cannot answer immediately, a polite request to call our
               emergency line to get an answer soon, and the number; no question. Pressed, the same three things,
               warmly and in other words. "Not what you don't give" becomes "not this list of what you don't
               give", so it no longer reads against "I can't answer immediately".
  Send         promise v8: "בהקדם" / "במהרה" / "במהירות האפשרית" in a message that gives our line is not our
               promise where its sentence is about the line or says we can't. danger v9: the same for "בהקדם",
               "הכי מהר", "כמה שיותר מהר", "במהירות", "במיידי", "באופן מיידי"; the sentence Send adds when a cut
               takes the line is the reference's second half, and when nothing is left, the whole reference.
               line v2: a plural "you" calling ("תתקשרו", "התקשרו", "חייגו") becomes singular, and nothing else
               is touched, "בבקשה תתקשר" stays. voice v3: a clause with our number is never cut. manners v6:
               "אני מיכאל, העוזר הדיגיטלי" stays whole.
  Memory       epoch 107 -> 108.
Not changed: the tools (they say "our emergency line only", no wording), gas (its own sentence, gas company first),
no ticket and no note in an emergency, the guards, the inject. The incoming phone agent's twin is owed.

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
from n8n_whatsapp_hotline import HOTS as OLD_HOTS, expr_compiles  # noqa: E402
from n8n_whatsapp_line import STEP as LINE_V1  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 108
OLD_KEY = "={{ $json.to }}-107"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-12nov-before-refline.json")

# The owner's reference, 12 Nov, with "מידיי" spelt "מיידי", "כדי תוכל" as "כדי שתוכל", and the number as the
# prompt writes it everywhere else. Send's own sentences are its two halves.
HOT_ASK = "בבקשה תתקשר למוקד החירום שלנו כדי שתוכל לקבל מענה בהקדם: 077-6687949."
REF = "אני רק העוזר הדיגיטלי ואין לי אפשרות לתת מענה מיידי. " + HOT_ASK

PROMPT_EDITS = (
    ("מה שיש לך לתת, כבר בהודעה הראשונה שלך על המקרה, הוא מילה קצרה ואכפתית משלך על מה שהוא עובר, ואחריה "
     "המשפט הזה, מילה במילה: \"" + OLD_HOTS + "\" ושם ההודעה נגמרת, בלי שאלה.",
     "מה שיש לך לתת, כבר בהודעה הראשונה שלך על המקרה, הוא הודעה כמו זאת: \"" + REF + "\" המילים שלך ולפי "
     "המקרה, אבל שלושה דברים נמצאים בה תמיד: שאתה רק העוזר הדיגיטלי ואין לך אפשרות לתת מענה מיידי, בקשה "
     "בנימוס שיתקשר למוקד החירום שלנו כדי לקבל מענה בהקדם, והמספר. ושם ההודעה נגמרת, בלי שאלה."),
    ("מה שהוא שומע ממך זה המוקד, ולא מה שאתה לא נותן.",
     "מה שהוא שומע ממך זה המוקד, ולא הרשימה הזאת של מה שאתה לא נותן."),
    ("הוא שומע ממך שוב, בחום ובמילים אחרות, שאפשר להתקשר עכשיו למוקד החירום שלנו, עם המספר, ולא מוסיף שאלה:",
     "הוא שומע ממך שוב, בחום ובמילים אחרות, את אותם שלושה דברים, ולא מוסיף שאלה:"),
)

# The two tests every "fast" exemption below shares: the sentence is about our line, or says we can't.
LINE_RE = "/0?77[-\\s]?668[-\\s]?7949|מוקד|תתקשר|להתקשר|התקשר|לחייג|תחייג|חייג/"
CANT_RE = "/(^|[\\s,])ו?(?:אין לי|אין באפשרותי|אינני יכול|איני יכול|לא יכול|לא יכולה|לא אוכל)(?=[\\s,]|$)/"

LINE_V2 = (
    "body.content = (() => { const lv = 'line v2'; const s = String(body.content || ''); "
    "const HOT = /0?77[-\\s]?668[-\\s]?7949/; if (!HOT.test(s)) return s; "
    "const ORDER = /(^|[.!?:;,\\n]\\s*)((?:ו?(?:בבקשה|אנא|אז|עכשיו|בינתיים),?\\s+)*)(ו?)(התקשרו|חייגו)(?![א-ת])/g; "
    "const PLURAL = /(^|[^א-ת])(ו?(?:ש|כש)?)(תתקשרו|תחייגו)(?![א-ת])/g; "
    "return s.replace(ORDER, (m, a, pre, v, verb) => a + pre + v + (verb === 'התקשרו' ? 'תתקשר' : 'תחייג'))"
    ".replace(PLURAL, (m, a, p, verb) => a + p + verb.slice(0, -1)); })(); ")

# (old, new), each anchor exactly once in Send's body.
LABELS = (
    ("const pv = 'promise v7';", "const pv = 'promise v8';"),
    ("const dv = 'danger v8';", "const dv = 'danger v9';"),
    ("const lv = 'line v1';", "const lv = 'line v2';"),
    ("const vv = 'voice v2';", "const vv = 'voice v3';"),
    ("const mv = 'manners v5';", "const mv = 'manners v6';"),
)
SEND_EDITS = (
    # promise v8
    ("const pv = 'promise v7';", "const pv = 'promise v8';"),
    ("const hits = (s) => Array.from(s.matchAll(PG)).filter((h) => !exempt(s, h) && !(SO && CB.test(h[3])));",
     "const HOTC = /0?77[-\\s]?668[-\\s]?7949/.test(c); const FAST = /^(בהקדם|במהרה|במהירות האפשרית)$/; "
     "const LINEX = " + LINE_RE + "; const CANTX = " + CANT_RE + "; "
     "const hits = (s) => Array.from(s.matchAll(PG)).filter((h) => !exempt(s, h) && !(SO && CB.test(h[3])) "
     "&& !(HOTC && FAST.test(h[3]) && (LINEX.test(s) || CANTX.test(s.slice(0, h.index)))));"),
    # danger v9
    ("const dv = 'danger v8';", "const dv = 'danger v9';"),
    ("const HOTS = '" + OLD_HOTS + "';",
     "const HOTS = '" + HOT_ASK + "'; const HOTA = 'אני רק העוזר הדיגיטלי ואין לי אפשרות לתת מענה מיידי. ' + HOTS;"),
    ("const promised = (p) => { ARRIVE.lastIndex = 0; let m; while ((m = ARRIVE.exec(p)) !== null) { "
     "if (!asked(p, m.index) && !msg(p, m)) return true;",
     "const FASTD = /^(?:הכי מהר|כמה שיותר מהר|בהקדם|במהרה|במהירות|במיידי|באופן מיידי)$/; "
     "const LINED = " + LINE_RE + "; const CANTD = " + CANT_RE + "; "
     "const promised = (p) => { ARRIVE.lastIndex = 0; let m; while ((m = ARRIVE.exec(p)) !== null) { "
     "if (!asked(p, m.index) && !msg(p, m) && !(hot && FASTD.test(m[0]) && (LINED.test(p) "
     "|| CANTD.test(p.slice(0, m.index))))) return true;"),
    ("return withHot(out || (hot ? HOTS : s)); })();", "return withHot(out || (hot ? HOTA : s)); })();"),
    # line v2
    (LINE_V1, LINE_V2),
    # voice v3
    ("const vv = 'voice v2';", "const vv = 'voice v3';"),
    ("const KEEP = /\\d{3}-\\d{3,6}-\\d{2}|https?:\\/\\//; const cut = (p) =>",
     "const KEEP = /\\d{3}-\\d{3,6}-\\d{2}|https?:\\/\\/|0?77[-\\s]?668[-\\s]?7949/; const cut = (p) =>"),
    # manners v6
    ("const mv = 'manners v5';", "const mv = 'manners v6';"),
    ("if (!/^(נציג|[-־]|מ(ה)?צוות|מהומי)/.test(y))", "if (!/^(נציג|[-־]|מ(ה)?צוות|מהומי|ה?עוזר)/.test(y))"),
)
assert REF == "אני רק העוזר הדיגיטלי ואין לי אפשרות לתת מענה מיידי. " + HOT_ASK


def refline(wf, labels_only=False):
    """The workflow with the edits above; each anchor exactly once. Does not touch memory.
    labels_only: the version labels alone, no code and no prompt (so the new cases can be seen failing)."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    body = by["Send"]["parameters"]["jsonBody"]
    for old, new in (LABELS if labels_only else SEND_EDITS):
        assert "}}" not in new and "{{" not in new, "an edit would end the expression early"
        body = once(body, old, new)
    by["Send"]["parameters"]["jsonBody"] = body
    if not labels_only:
        agent = by["Answer the resident"]["parameters"]
        for old, new in PROMPT_EDITS:
            agent["options"]["systemMessage"] = once(agent["options"]["systemMessage"], old, new)
        sm = agent["options"]["systemMessage"]
        assert OLD_HOTS not in sm, "the prompt still quotes the old fixed sentence"
        assert sm.count("\"" + REF + "\"") == 1, "the prompt does not quote the owner's reference once"
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    labels_only = "--labels-only" in sys.argv
    if apply and labels_only:
        sys.exit("REFUSING: --labels-only is for a dump, never for live.")
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and "const dv = 'danger v9';" in by["Send"]["parameters"]["jsonBody"]:
        print("Nothing to do. Live already takes the owner's reference for an emergency, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 107's. Read live first." % key)

    new = refline(live, labels_only)
    nb = {n["name"]: n for n in new["nodes"]}
    if tools_of(new) != tools_of(live):
        sys.exit("REFUSING: the tools would change; this patcher edits the prompt and Send only.")
    if not labels_only:
        if W.MEMORY_EPOCH != EPOCH:
            sys.exit("REFUSING: n8n_whatsapp.MEMORY_EPOCH is %d, not %d. Move the repo first." % (W.MEMORY_EPOCH, EPOCH))
        if prompt_of(new) != W.system_prompt():
            sys.exit("REFUSING: the would-be prompt is not docs/features/11-whatsapp-bot/prompt.md's. "
                     "Edit the document first; live follows it.")
        W.check_memory_epoch(prompt=prompt_of(new), tools=tools_of(new))
    expr_compiles(nb["Send"]["parameters"]["jsonBody"], "Send")
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("Send     : promise v8, danger v9, line v2, voice v3, manners v6%s"
          % (" (LABELS ONLY: no code, no prompt)" if labels_only else ""))
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
    print("  prompt %s (want %s); memory key %s; Send %s"
          % (W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)),
             bb["Conversation so far"]["parameters"]["sessionKey"],
             "as written" if sb == nb["Send"]["parameters"]["jsonBody"] else "DIFFERS"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
