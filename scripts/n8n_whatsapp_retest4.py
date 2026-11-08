# -*- coding: utf-8 -*-
"""The Grok tester's fourth run (8 Nov 2026), fixed in Send's code: Michael speaks for himself even where
the model slips into "they" or "we", and the honest "I have no time for when they'll get back to you" is
no longer cut as a promise. Code only: no text a model reads changes, so the memory epoch stays 99.

    python scripts/n8n_whatsapp_retest4.py              # dry run
    python scripts/n8n_whatsapp_retest4.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_retest4.py --apply      # write it
    python scripts/n8n_whatsapp_retest4.py --restore    # put the snapshot back

WHAT THE FOURTH RUN SHOWED (the UChat copy's executions 163758-164209, read with each draft):
  Five replies spoke as the team or as "we" (R4), and every one was the model's own wording against the
  prompt's sentence "אף אחד אחר לא מופיע בהודעות שלך כמי שבודק, רואה, מטפל, יודע או יחזור אליו":
    C1.4 (163780) "ברגע שייסגרו אותה נשלח לך עדכון מסודר לכאן" (the prompt: "נשלחת עליה הודעה לכאן");
    C1.5 (163788) "ורשמתי עכשיו לצוות שאתה מחכה לתשובה" (notify_team ran; the prompt: "רושם במערכת");
    C2 (163807) and C3 (163833) "הוספתי … לקריאה … כדי שידעו …" (add_request_detail's own text says "say
      what you added, not who will see it");
    C6.4 (163962) "כדי שנוכל לאמת את זה במערכת", written by the retry; the first draft had "כדי שאוכל".
  The same forms went out 6 times since the 29 Oct one-voice change (all 1,343 replies read): a sentence
  more in the prompt would be a rule on top of one the model already has. As with "הכל בסדר" (allclear
  v1) and the ticket number (ref v1), the code carries it.
  C9.4 (164030): the draft answered "ומתי המנהל יחזור אליי?" with "תאריך או שעה מדויקת למתי יחזרו אליך
  אין לי, אני אומר את זה בפשטות. מה שכן, …". promise v4 lets "יחזרו אליך" through after "מתי" (asking
  WHEN is not promising), but "למתי" is not "מתי", so the sentence was cut whole and the tenant got "מה
  שכן, …" with no answer to his question.

WHAT CHANGES (Send only).
- voice v1, after ref v1 and before slang v1:
    a purpose clause that has someone else knowing, seeing or handling it ("כדי שידעו …", "כדי שהצוות
      יראה …") is cut to the end of its clause (a reply that opens with one loses it up to its comma);
      never when what goes holds a ticket number or a link, or would leave fewer than two words;
    "כדי שנוכל" / "על מנת שנוכל" -> "… שאוכל";
    "רשמתי|ציינתי|כתבתי|השארתי … לצוות" -> "… במערכת";
    "נשלח לך עדכון" -> "יישלח לך עדכון", "נשלח לך הודעה" -> "תישלח לך הודעה".
- promise v5: v4 with "למתי" read as "מתי" (WHEN = /^ו?ל?מתי$/).
Not changed: the prompt, the tools' texts, the guards, the memory key, the phone agent.
The status lookup's count (C5, C10.3: "three open" while 17 and 20 were) is the function's, in
supabase/functions/debt-tools/index.ts (open_total), shipped by its own PR to main.

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
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-08nov-before-retest4.json")

# Send, after ref v1 and before slang v1. No "}}" anywhere: n8n would read it as the expression's end.
# Quotes inside the regex classes are " and ', as promise v4 writes them.
VOICE = (
    "body.content = (() => { const vv = 'voice v1'; let G = { }; try { G = $('Sort').first().json || { }; } "
    "catch (e) { G = { }; } if (G.greeting === true) return body.content; const s = String(body.content || ''); "
    "if (!s) return s; const words = (x) => x.trim().split(/\\s+/).filter(Boolean).length; "
    "const HEAD = /ו?(?:כדי|על מנת) ש(?:ידעו|יידעו|יראו|יוכלו|יבינו|יטפלו|יבדקו|יהיה להם|הצוות|המנהל|ההנהלה)"
    "(?=[\\s,.!?:;)\\u0022\\u0027]|$)/u; const KEEP = /\\d{3}-\\d{3,6}-\\d{2}|https?:\\/\\//; "
    "const cut = (p) => { const m = p.match(HEAD); if (!m) return p; const at = m.index; "
    "if (at > 0 && /[א-ת]/.test(p[at - 1])) return p; const pre = p.slice(0, at); let q = p; "
    "if (pre.trim() === '') { const k = p.indexOf(',', at); if (k === -1 || KEEP.test(p.slice(at, k))) return p; "
    "q = pre + p.slice(k + 1).replace(/^\\s+/, ''); } else { const rest = p.slice(at); const e = rest.search(/[,.!?\\n]/); "
    "const gone = e === -1 ? rest : rest.slice(0, e); if (KEEP.test(gone)) return p; "
    "q = pre.replace(/[\\s,]+$/, '') + (e === -1 ? '' : rest.slice(e)); } return words(q) >= 2 ? q : p; }; "
    "let out = /https?:\\/\\//.test(s) ? s : (s.match(/[^.!?\\n]*(?:[.!?]+|\\n+|$)/g) || [s]).map(cut).join(''); "
    "out = out.replace(/(^|[^א-ת])(ו?)(כדי|על מנת) שנוכל(?=[\\s,.!?:;)\\u0022\\u0027]|$)/gu, "
    "(m, a, v, k) => a + v + k + ' שאוכל'); "
    "out = out.replace(/(^|[^א-ת])(ו?(?:רשמתי|ציינתי|כתבתי|השארתי)(?: (?:עכשיו|כבר|גם|את זה|הערה))*) לצוות"
    "(?: שלנו)?(?=[\\s,.!?:;)\\u0022\\u0027]|$)/gu, (m, a, v) => a + v + ' במערכת'); "
    "out = out.replace(/(^|[^א-ת])(ו?)נשלח (לך|אליך|אלייך) (עדכון|הודעה)(?=[\\s,.!?:;)\\u0022\\u0027]|$)/gu, "
    "(m, a, v, to, n) => a + v + (n === 'הודעה' ? 'תישלח' : 'יישלח') + ' ' + to + ' ' + n); "
    "return words(out) >= 2 ? out : s; })(); ")
SEND_EDITS = [
    ("body.content = (() => { const sv = 'slang v1';", VOICE + "body.content = (() => { const sv = 'slang v1';"),
    ("const pv = 'promise v4';", "const pv = 'promise v5';"),
    ("const WHEN = /^ו?מתי$/;", "const WHEN = /^ו?ל?מתי$/;"),
]


def retest4(wf):
    """The workflow with Send's voice v1 and promise v5. Nothing a model reads."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    p = by["Send"]["parameters"]
    body = p["jsonBody"]
    for old, new in SEND_EDITS:
        body = once(body, old, new)
    assert "}}" not in VOICE and "{{" not in VOICE, "voice v1 would end the expression early"
    p["jsonBody"] = body
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if "const vv = 'voice v1'" in by["Send"]["parameters"]["jsonBody"]:
        print("Nothing to do. Live already has voice v1 and promise v5.")
        return
    if key != KEY or "const rv = 'ref v1'" not in by["Send"]["parameters"]["jsonBody"]:
        sys.exit("REFUSING: live is not epoch 99 with ref v1 (key %r). Read live first." % key)

    new = retest4(live)
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
    body = bb["Send"]["parameters"]["jsonBody"]
    print("\nwritten  : %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  voice v1 %s; promise v5 %s; prompt %s (want %s); memory key %s" % (
        "present" if "const vv = 'voice v1'" in body else "MISSING",
        "present" if "const WHEN = /^ו?ל?מתי$/;" in body and "'promise v5'" in body else "MISSING",
        W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(live)),
        bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
