# -*- coding: utf-8 -*-
"""The Grok tester's third run (6 Nov 2026), fixed: a ticket the tools found is named by its number,
Michael says who he is after the system's greeting even to someone he spoke with before, a burst after
the menu reaches the model whole and knows the menu went out, "I recorded" needs a tool like "I opened"
does, and the answer to "when will the manager call?" ends on the matter (epoch 99).

    python scripts/n8n_whatsapp_retest3.py              # dry run
    python scripts/n8n_whatsapp_retest3.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_retest3.py --apply      # write it
    python scripts/n8n_whatsapp_retest3.py --restore    # put the snapshot back

WHAT THE THIRD RUN SHOWED (read against the UChat copy's executions, 158718-159074):
  C2 (158760): "שוב אני, המעלית עדיין לא עובדת" ran get_request_status (255-1403-26) and
     add_request_detail (255-1403-26), and the reply said "הוספתי לקריאה את העדכון שלך … המצב שלה כרגע
     עדיין מופיע כפתוחה" with no number. The text fix of epoch 98 (get_request_status: "name each ticket
     by its reference") held in C5 and C11.2 and not here: the reply spoke of the add, not the lookup.
  C5 (158840): the status tap right after the menu. The model was told the menu had just gone out (the
     same bracket as C1's tap, which said "כאן מיכאל") and did not say who it is. The tap paragraph says
     the name comes "if this is your first message to this person", and the buffer held C1 to C4.
  C11 (159008-159015): "שלום", "יש בעיה", "האינטרקום לא עובד כבר יומיים", seconds apart. The menu was
     logged after the other two, so `Still the last word?` stopped on it at once ("יש בעיה" never
     reached the model), and Sort's `last_bot` had been spent by "יש בעיה"'s silenced run: the model was
     never told the menu went out. Send's manners step reads the rows and would have kept the name; the
     model never wrote it.
  C6.4 (158913): "רשמתי את הפרטים שנתת לי (צ'ק של כ-500 ש"ח …)" with no tool that turn, then "כדי שנוכל
     לאמת ולסדר את זה במערכת". The deeds guard's verbs are checked/sent/opened/handled; "רשמתי" and
     "הוספתי" were never on the list, so the false claim went out. notify_team's own text already says the
     missing payment is noted once, with the details, and never mentioned to him.
  C9.4 (158988): "…יש עוד משהו שתרצה שאוסיף לקריאה בינתיים?" after "when will the manager call?". The
     manager paragraph's when-line ends "אתה נשאר בשיחה וממשיך לעזור בכל מה שעוד יש", which invites the
     anything-else; epoch 98's on-the-matter question went into the other when-line, not this one.
  C10.1 (159074): answered in 18 s ("אני העוזר הדיגיטלי בצוות השירות של הומי'ז. …"); UChat answered "ok"
     at 10:20:53 UTC. The tester saw nothing. Delivery is the phone's to prove; nothing here to change.

WHAT CHANGES.
- Send, ref v1 (code, after danger v5): when this turn's tools gave exactly one ticket (a lookup that
  found one, an add, an open) and the reply names no reference, the number goes in brackets after the
  first word for the ticket ("לקריאה (255-1403-26)"). Several tickets, none, or a reply with a number:
  untouched. Text failed once on Gemini for this exact case, so the code carries it.
- `Still the last word?`, lastword v2 (code): a menu on top of inbound rows is read past, the bare hello
  it answered is left out, and `last_bot` is the menu whenever the newest outbound row is the menu and
  Sort's own note is empty.
- The deeds guard (Reply usable?, Try again, Outage reply usable?, Mend the reply): "רשמתי", "רשמנו",
  "הוספתי", "הוספנו" and "עדכנתי" join the verbs that are true only when a tool ran this turn; Try
  again's reason names them ("…שבדקת, שלחת, רשמת, הוספת, תיקנת או טיפלת…").
- The prompt: the tap paragraph's name clause loses its first-message condition ("…גם למי שכבר דיבר
  איתך קודם"); the manager when-line's "keep helping with whatever else there is" becomes the question
  that stays on his matter.
- Memory epoch 98 -> 99.
Not changed: the tools' texts, the other guards, the phone agent.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py, then n8n_uchat.py --apply carries it to
the UChat copy, the bot in use.
"""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 99
OLD_KEY = "={{ $json.to }}-98"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-06nov-before-retest3.json")

PROMPT_EDITS = [
    ("גם לחיצה היא הודעה, ואם זאת ההודעה הראשונה שלך לאדם הזה אתה אומר בה מי אתה.",
     "גם לחיצה היא הודעה, ואתה אומר בה מי אתה, גם למי שכבר דיבר איתך קודם."),
    ('במילים שלך ובלי שעה, בלי יום ובלי "בקרוב". אתה נשאר בשיחה וממשיך לעזור בכל מה שעוד יש.',
     'במילים שלך ובלי שעה, בלי יום ובלי "בקרוב". והשאלה שבסוף ההודעה נשארת על העניין שלו, כמו אם משהו '
     'השתנה מאז.'),
]

# Send, after danger v5 and before slang v1. No "}}" anywhere: n8n would read it as the expression's end.
REF = ("body.content = (() => { const rv = 'ref v1'; const s = String(body.content || ''); "
       "if (/\\b\\d{3}-\\d{3,6}-\\d{2}\\b/.test(s)) return s; const steps = []; "
       "try { for (const x of ($('Answer the resident').first().json.intermediateSteps || [])) steps.push(x); } catch (e) { } "
       "try { for (const x of ($('Try again').first().json.first_steps || [])) steps.push(x); } catch (e) { } "
       "const res = (x) => { let o = (x || { }).observation; try { if (typeof o === 'string') o = JSON.parse(o); "
       "if (Array.isArray(o) && o[0] && o[0].results) { const r = o[0].results[0].result; o = typeof r === 'string' ? JSON.parse(r) : r; } "
       "} catch (e) { } return (o && typeof o === 'object') ? o : { }; }; const refs = []; "
       "for (const x of steps) { const tool = (x || { }).tool || ((x || { }).action || { }).tool; const r = res(x); "
       "const got = tool === 'get_request_status' ? (Array.isArray(r.requests) ? r.requests : []).map((q) => (q || { }).reference) "
       ": ((tool === 'add_request_detail' || tool === 'open_request') && r.ok !== false ? [r.reference] : []); "
       "for (const g of got) { if (g && refs.indexOf(String(g)) === -1) refs.push(String(g)); } } "
       "if (refs.length !== 1) return s; "
       "const m = s.match(/(^|[\\s,.!?:;(\"'])((?:ו|ש|וש|כש)?(?:ה|ל|ב|מה)?קריא(?:ה|ת ה?שירות)(?: ה?(?:חדשה|דחופה|נוספת))?"
       "(?: (?:שלך|שלו|שלה))?)(?=[\\s,.!?:;)\"']|$)/u); if (!m) return s; "
       "const at = m.index + m[1].length + m[2].length; return s.slice(0, at) + ' (' + refs[0] + ')' + s.slice(at); })(); ")
SEND_EDITS = [
    ("body.content = (() => { const sv = 'slang v1';", REF + "body.content = (() => { const sv = 'slang v1';"),
]

LAST_WORD_EDITS = [
    ("const backlog = [];\nlet photo = j.photo === true;\nfor (const r of rows) {\n",
     "//\n"
     "// lastword v2, 6 Nov (the tester's C11, executions 159008-159015): \"שלום\",\n"
     "// \"יש בעיה\" and the fault, seconds apart. The menu that answered \"שלום\" was\n"
     "// logged once it had gone out, after the other two, so it was the newest row:\n"
     "// the loop stopped on it at once and \"יש בעיה\" never reached the model. And\n"
     "// Sort's note that the menu had just gone out (`last_bot`) was spent by \"יש\n"
     "// בעיה\"'s silenced run, so this run was never told, and Michael did not say\n"
     "// who he is. A menu on top of inbound rows is the system's answer to a hello\n"
     "// inside this backlog: read past it, leave out the bare hello it answered, and\n"
     "// tell the model the menu was the last thing sent.\n"
     "const MENU = /👋 (?:כאן הומי'ז[.] )?במה אפשר לעזור[?]/;\n"
     "const menuTop = rows.length > 1 && rows[0].direction === 'outbound'\n"
     "  && MENU.test(String(rows[0].body || '')) && rows[1].direction === 'inbound';\n"
     "const backlog = [];\nlet photo = j.photo === true;\nfor (const r of (menuTop ? rows.slice(1) : rows)) {\n"),
    ("backlog.reverse();\nconst text = backlog.length ? backlog.join('\\n') : j.text;\n"
     "return [{ json: Object.assign({}, j, { text: text, burst_size: backlog.length || 1, photo: photo }) }];",
     "backlog.reverse();\n"
     "if (menuTop && backlog.length > 1\n"
     "    && /^(שלום רב|שלום|היי|הי|אהלן|בוקר טוב|צהריים טובים|ערב טוב|hi|hey|hello)[\\s!?.,]*$/iu.test(backlog[0])) {\n"
     "  backlog.shift();\n"
     "}\n"
     "const text = backlog.length ? backlog.join('\\n') : j.text;\n"
     "const newestOut = rows.find(r => r.direction === 'outbound');\n"
     "const lastBot = j.last_bot\n"
     "  || (newestOut && MENU.test(String(newestOut.body || '')) ? String(newestOut.body) : '');\n"
     "return [{ json: Object.assign({}, j, { text: text, burst_size: backlog.length || 1, photo: photo,\n"
     "                                        last_bot: lastBot }) }];"),
]

# The deeds guard's verbs (wa_truth.TOOLED_VERBS) as live has them, and with the five new ones.
OLD_VERBS = "טיפלתי|טיפלנו|החלפנו"
NEW_VERBS = "טיפלתי|טיפלנו|רשמתי|רשמנו|הוספתי|הוספנו|עדכנתי|החלפנו"
VERB_NODES = {"Reply usable?": 2, "Try again": 2, "Outage reply usable?": 1, "Mend the reply": 1}
OLD_WHY = "היא סיפרה שבדקת, שלחת, תיקנת או טיפלת במשהו, ושום כלי לא עשה את זה בתור הזה"
NEW_WHY = "היא סיפרה שבדקת, שלחת, רשמת, הוספת, תיקנת או טיפלת במשהו, ושום כלי לא עשה את זה בתור הזה"


def _swap(params, old, new, want, where):
    """Every `old` inside a node's parameters becomes `new`; exactly `want` of them, or refuse."""
    s = json.dumps(params, ensure_ascii=False)
    n = s.count(old)
    if n != want:
        sys.exit("REFUSING: %s has %d of %r, expected %d. Read live first." % (where, n, old[:40], want))
    return json.loads(s.replace(old, new))


def retest3(wf):
    """The workflow with the prompt's two edits, Send's ref v1, lastword v2 and the deeds verbs. Not memory."""
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
    assert "}}" not in REF and "{{" not in REF, "ref v1 would end the expression early"
    p["jsonBody"] = body
    lw = by["Still the last word?"]["parameters"]
    code = lw["jsCode"]
    for old, new in LAST_WORD_EDITS:
        code = once(code, old, new)
    lw["jsCode"] = code
    for name, want in VERB_NODES.items():
        by[name]["parameters"] = _swap(by[name]["parameters"], OLD_VERBS, NEW_VERBS, want, name)
    by["Try again"]["parameters"] = _swap(by["Try again"]["parameters"], OLD_WHY, NEW_WHY, 1, "Try again")
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and "const rv = 'ref v1'" in by["Send"]["parameters"]["jsonBody"]:
        print("Nothing to do. Live already has ref v1, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 98's. Read live first." % key)

    new = retest3(live)
    nb = {n["name"]: n for n in new["nodes"]}
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("tools    : %s -> %s (unchanged)" % (W.epoch_hash(tools_of(live)), W.epoch_hash(tools_of(new))))
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
    print("  ref v1 %s; lastword v2 %s; deeds verbs %s; prompt %s (want %s); memory key %s" % (
        "present" if "const rv = 'ref v1'" in bb["Send"]["parameters"]["jsonBody"] else "MISSING",
        "present" if "lastword v2" in bb["Still the last word?"]["parameters"]["jsCode"] else "MISSING",
        "present" if NEW_VERBS in json.dumps(bb["Reply usable?"]["parameters"], ensure_ascii=False) else "MISSING",
        W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)),
        bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
