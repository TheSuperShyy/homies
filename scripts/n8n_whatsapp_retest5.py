# -*- coding: utf-8 -*-
"""The Grok tester's fifth run (8 Nov 2026, evening), its two fails fixed in Send's code: Michael says who he
is after the system's greeting, and never that a request for a manager was recorded. Code only: no text a
model reads changes, so the memory epoch stays 99.

    python scripts/n8n_whatsapp_retest5.py              # dry run
    python scripts/n8n_whatsapp_retest5.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_retest5.py --apply      # write it
    python scripts/n8n_whatsapp_retest5.py --restore    # put the snapshot back

WHAT THE FIFTH RUN SHOWED (the UChat copy's executions 164557-164977, 45 messages, read with each draft):
  C5 R2 (164670): "היי", the menu, a tap on "מצב קריאה קיימת". Sort handed the model the menu line
    (last_bot) and the tap; the draft opened "בשמחה, בוא נראה." with no name. The prompt says it twice
    ("כשהמערכת כבר בירכה אותו ... אתה אומר מי אתה" and, for a tap, "גם לחיצה היא הודעה, ואתה אומר בה מי
    אתה, גם למי שכבר דיבר איתך קודם"). Of the first replies after the menu since 25 Oct, 7 of 24 had no
    name, 3 of the 7 after the status tap (5 Nov, 6 Nov, this one).
  C9.4 R15 (164822): "ומתי המנהל יחזור אליי?". The first draft said "רשמתי את כל מה שאמרת" with no tool
    this turn and was sent back by the truth check; the retry wrote "וגם הבקשה שלך לדבר עם מנהל רשומה",
    from C9.1's notify_team. The prompt: "על הרישום הזה אתה לא מספר לו, גם לא אחר כך כשהוא שואל מתי
    יחזרו אליו". The same claim went out on 29 Oct ("רשמתי את הבקשה שלך לדבר עם מנהל אצלנו במערכת") and in
    the 5 Nov run's C9.4 ("הבקשה שלך לדבר עם מנהל רשומה אצלנו מסודר").
  Both are the model's own words against a text it has, so, as with voice v1 and v2, the code carries it.

WHAT CHANGES (Send only).
- manager v1, after voice v2 and before slang v1: a clause that says a request for a manager (or a person,
  or the management) was recorded, noted or passed on goes. The request and the recording word must be
  within five words of each other in one clause. Cut, from the smallest: the "ו" word that joins the
  clause ("וגם הבקשה שלך ... רשומה"); else the clause with the comma before it (", אבל הבקשה ... רשומה");
  else, when the sentence opens with it, the clause and its comma ("רשמתי את הבקשה ..., אבל ..." keeps
  "...", without "אבל"); else the whole sentence. Never when what goes holds a ticket number, never in a
  reply with a link, and a cut that would leave a lead-in ("מה שבטוח.") takes the sentence instead.
- intro v1, the last step: a model's reply right after the system's greeting (the menu line in Sort's
  last_bot, or as the chat's last outbound message) that has no "מיכאל" and no "העוזר הדיגיטלי" opens
  with "כאן מיכאל מהומי'ז." (after a greeting the draft kept, "היי, כאן מיכאל מהומי'ז. ..."). Not on a
  canned line, not after a short "I'm checking" message already went out this turn.
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
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-08nov-before-retest5.json")

# Both steps are JavaScript inside Send's one n8n expression: no "}}" or "{{" anywhere.
MANAGER = (
    r"""body.content = (() => { const mg = 'manager v1'; let G = { }; try { G = $('Sort').first().json || { }; } catch (e) { G = { }; } """
    r"""if (G.greeting === true || $json._canned === true) return body.content; const s = String(body.content || ''); """
    r"""const MGR = /(?:לדבר|לשוחח)(?: ישירות)? (?:עם|אל) (?:ה)?(?:מנהל|מנהלת|הנהלה|אחראי|נציג|נציגה|בן אדם)|(?:בקשה|בקשתך|פנייה|פנייתך)(?: שלך)? (?:ל|אל )(?:ה)?(?:מנהל|מנהלת|הנהלה)/u; """
    r"""const REC = /(?:^|[^א-ת])(?:ו|ש|וש|כש)?(?:רשום|רשומה|רשומים|רשומות|נרשם|נרשמה|נרשמו|רשמתי|ציינתי|העברתי|הועבר|הועברה|הועברו|עדכנתי|תיעדתי|מתועד|מתועדת|התקבל|התקבלה|השארתי|הוספתי|הכנסתי)(?=[\s,.!?:;)"']|$)/u; """
    r"""if (!s || /https?:\/\//.test(s) || !MGR.test(s) || !REC.test(s)) return s; const KEEP = /\d{3}-\d{3,6}-\d{2}/; """
    r"""const LEAD = /(?:^|\s)ו?(?:שכן|שבטוח|אבל|רק|אז|גם|כי|ש|מה|לגבי|בקיצור)$/; const words = (x) => x.trim().split(/\s+/).filter(Boolean).length; """
    r"""const near = (g) => { const a = g.match(MGR); const b = g.match(REC); if (!a || !b) return false; const a1 = a.index + a[0].length; const b1 = b.index + b[0].length; """
    r"""const gap = b.index >= a1 ? g.slice(a1, b.index) : (b1 <= a.index ? g.slice(b1, a.index) : ''); return words(gap) <= 5; }; """
    r"""const fix = (p) => { if (!MGR.test(p) || !REC.test(p)) return p; const e = p.search(/[.!?\n]+\s*$/); const head = e === -1 ? p : p.slice(0, e); const tail = e === -1 ? '' : p.slice(e); """
    r"""const segs = head.split(','); const i = segs.findIndex(near); if (i === -1) return p; const g = segs[i]; const at = Math.min(g.search(MGR), g.search(REC)); """
    r"""let j = -1; const J = /\s(?=ו(?:גם\s|בנוסף\s|כן\s|(?:ה)?(?:בקשה|בקשתך|פנייה|פנייתך)(?=[\s,.!?:;])|(?:רשום|רשומה|נרשם|נרשמה|נרשמו|רשמתי|ציינתי|העברתי|הועבר|הועברה|הועברו|עדכנתי|תיעדתי|מתועד|מתועדת|התקבל|התקבלה|השארתי|הוספתי|הכנסתי)(?=[\s,.!?:;)]))|(?:רשמתי|ציינתי|העברתי|עדכנתי|תיעדתי|השארתי|הוספתי|הכנסתי)(?=[\s,.!?:;)]))/g; """
    r"""let m = J.exec(g); while (m !== null && m.index <= at) { if (words(g.slice(m.index, at)) <= 4) j = m.index; m = J.exec(g); } """
    r"""const whole = () => (KEEP.test(p) ? p : ''); let out = null; """
    r"""if (j > 0 && g.slice(0, j).trim() !== '') { if (KEEP.test(g.slice(j))) return p; const pre = segs.slice(0, i).concat([g.slice(0, j)]).join(','); """
    r"""if (words(pre) < 2 || LEAD.test(pre.trim())) return whole(); out = segs.slice(0, i).concat([g.slice(0, j)], segs.slice(i + 1)); } """
    r"""else { if (KEEP.test(g) || words(g.slice(0, at)) > 6) return p; """
    r"""if (i > 0) { const pre = segs.slice(0, i).join(','); if (words(pre) < 2 || LEAD.test(pre.trim())) return whole(); out = segs.slice(0, i).concat(segs.slice(i + 1)); } """
    r"""else if (segs.length > 1) { const rest = segs.slice(1); rest[0] = rest[0].replace(/^(\s*)(?:אבל|אך)\s+/, '$1').replace(/^(\s*)ו(?!עד\s)(?=[א-ת])/, '$1'); if (words(rest.join(',')) < 2) return whole(); out = rest; } """
    r"""else { return whole(); } } return out.join(',').replace(/\s+,/g, ',') + tail; }; """
    r"""const pieces = s.match(/[^.!?\n]*(?:[.!?]+|\n+|$)/g) || [s]; let r = pieces.map(fix).join('').replace(/[ \t]{2,}/g, ' ').replace(/^[ \t]+/gm, '').trim(); """
    r"""if (r !== s && /^(?:גם|ו(?!עד\s)[א-ת])/.test(r) && !/^(?:גם|ו[א-ת])/.test(s)) r = r.replace(/^(?:וגם|גם)\s+/, '').replace(/^ו(?=[א-ת])/, ''); """
    r"""return words(r) >= 2 ? r : s; })(); """)
INTRO = (
    r"""body.content = (() => { const iv = 'intro v1'; let G = { }; try { G = $('Sort').first().json || { }; } catch (e) { G = { }; } """
    r"""if (G.greeting === true || $json._canned === true) return body.content; const s = String(body.content || ''); """
    r"""if (!s.trim() || /מיכאל|העוזר הדיגיטלי|העוזרת הדיגיטלית/.test(s)) return s; """
    r"""let lastOut = ''; try { for (const r of $('Anything newer?').all()) { if (r.json && r.json.direction === 'outbound') { lastOut = String(r.json.body || ''); break; } } } catch (e) { lastOut = ''; } """
    r"""const menu = /במה אפשר לעזור/.test(String(G.last_bot || '')) || lastOut.indexOf('👋 במה אפשר לעזור?') !== -1 || /👋 כאן הומי'ז[.] במה אפשר לעזור[?]/.test(lastOut); """
    r"""if (!menu) return s; let acked = false; try { acked = $('Say it now').all().length > 0; } catch (e) { acked = false; } if (acked) return s; """
    r"""const NAME = "כאן מיכאל מהומי'ז."; const H = s.match(/^(שלום רב|שלום|היי|הי|אהלן|בוקר טוב|צהריים טובים|ערב טוב|לילה טוב)(?=[\s,.!:;]|$)[\s,.!:;]*/u); """
    r"""return H ? H[1] + ', ' + NAME + ' ' + s.slice(H[0].length) : NAME + ' ' + s.replace(/^\s+/, ''); })(); """)
SEND_EDITS = [
    ("body.content = (() => { const sv = 'slang v1';", MANAGER + "body.content = (() => { const sv = 'slang v1';"),
    ("return JSON.stringify(body); })() }}", INTRO + "return JSON.stringify(body); })() }}"),
]


def retest5(wf):
    """The workflow with Send's manager v1 and intro v1. Nothing a model reads."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    p = by["Send"]["parameters"]
    body = p["jsonBody"]
    for step in (MANAGER, INTRO):
        assert "}}" not in step and "{{" not in step, "a step would end the expression early"
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
    if "const mg = 'manager v1'" in body and "const iv = 'intro v1'" in body:
        print("Nothing to do. Live already has manager v1 and intro v1.")
        return
    if key != KEY or "const vv = 'voice v2'" not in body or "const mg = 'manager v" in body \
            or "const iv = 'intro v" in body:
        sys.exit("REFUSING: live is not epoch 99 with voice v2 and neither step (key %r). Read live first." % key)

    new = retest5(live)
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
    sb = bb["Send"]["parameters"]["jsonBody"]
    print("\nwritten  : %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  manager v1 %s; intro v1 %s; prompt %s (want %s); memory key %s" % (
        "present" if "const mg = 'manager v1'" in sb else "MISSING",
        "present" if "const iv = 'intro v1'" in sb else "MISSING",
        W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(live)),
        bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
