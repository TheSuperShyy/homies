# -*- coding: utf-8 -*-
"""In an emergency Michael says the urgent ticket and its number, nothing else: a step in Send, 6 Oct.

    python scripts/n8n_whatsapp_danger.py            # dry run
    python scripts/n8n_whatsapp_danger.py --dump F   # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_danger.py --apply    # write it
    python scripts/n8n_whatsapp_danger.py --restore  # put the 6 Oct snapshot back

WHY. The live test of 5 Oct evening (docs/assistant/transcripts/
2026-10-05-whatsapp-6-tenants.md, chat 6): water dripping onto a stairwell
light. The prompt already says, in so many words, no safety instructions, no
"what to do" even when asked, never "help / the team is on the way", only the
urgent ticket and its number, and "that is the only thing I can do from here"
when pushed. The model wrote "our team is already on its way", "don't touch
anything electrical, keep away", "they'll come as fast as they can" and "no need
to call an electrician" anyway. The owner, 6 Oct: *"we dont order them around we
just open a ticket that is the best thing we can do for them and dont advise
anything and dont tell them that the team is on the way"*. A rule the model has
and breaks belongs in code (CONTEXT: a necessary condition goes in code).

WHAT IT DOES, in Send, after the promise filter and before the emoji step, only
in an emergency: this turn's tools opened an emergency ticket or told the team of
an emergency, or the last bot message spoke of the urgent ticket.
- A sentence that advises or instructs (don't touch, keep away, switch off, call,
  an electrician, safety, 100-102...) goes.
- A sentence that promises arrival or action (on the way, will come, as fast as
  possible, right away, is handling it) goes, unless the word is asked about or
  denied ("I don't know when they'll come" stays).
- If anything went and the reply no longer names the ticket, the ticket line is
  added with the real number: "פתחתי לך קריאה דחופה, מספר X, וזה הדבר היחיד שאני
  יכול לעשות מכאן." when he asked something, "הקריאה הדחופה שלך פתוחה, מספר X."
  when he did not. The number comes from this turn's open_request, else the
  reply, else the last bot message. Nothing is ever invented.
- Outside an emergency it changes nothing. It never returns an empty reply.

V2, THE SAME EVENING, after the owner's "ok go" run of the emergency again
(live6_leak_panic_fixed, runs 84781-84801). v118 opened its own urgent ticket
(255-1349-26) and v1 cleaned the turn that opened it, then missed three things:
- the model calls it "קריאת שירות דחופה", which v1's test for the last bot
  message did not read as the urgent ticket, so the next turns went unfiltered
  ("only a licensed electrician can decide", "keep away from the leak");
- it gave the office number "for urgent faults", from the prompt's facts ("זה גם
  המספר לתקלות דחופות"). The facts stay for other questions; in an emergency a
  phone number is an instruction to call, and goes;
- "אני מיד מטפל בזה" before the ticket existed: the reply itself naming the
  urgent ticket now counts as an emergency.
And "it will be handled" (יטופל) stays: it is the owner's own line for "when?".

V3, the third run (live6_leak_panic_v2, runs 84817-84853): no advice, no "on
the way" and no phone number reached him, but one turn lost everything except
"I understand your worry" without naming the ticket: Sort's last_bot was empty
there, so the number was not found. The chat's own recent outbound rows
(`Anything newer?`) are read as well.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, `check_patchers_idle.py F`,
`--apply`, the check again on live, every WhatsApp patcher's dry run idle.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_untemplate as U  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-06oct-before-danger-v3.json")
PLACEHOLDER = NP.PLACEHOLDER
NL = chr(10)
# A backslash is built, never typed (manners.py, 27 Sep): `¤` stands for one.
BS = chr(92)
PH = "¤"

MARK = "const dv = 'danger v3';"
OLD_START = "body.content = (() => { const dv = 'danger v"
ANCHOR = "body.content = (() => { const ev = 'emoji v1';"
PUSHED = "פתחתי לך קריאה דחופה, מספר ' + ref + ', וזה הדבר היחיד שאני יכול לעשות מכאן."
OPEN = "הקריאה הדחופה שלך פתוחה, מספר ' + ref + '."
LINES = [
    "body.content = (() => { " + MARK,
    "let G = { }; try { G = $('Sort').first().json || { }; } catch (e) { G = { }; }",
    "if (G.greeting === true) return body.content;",
    "const s = String(body.content || '');",
    # This turn's tools, both passes.
    "const steps = [];",
    "try { for (const x of ($('Answer the resident').first().json.intermediateSteps || [])) steps.push(x); } catch (e) { }",
    "try { for (const x of ($('Try again').first().json.first_steps || [])) steps.push(x); } catch (e) { }",
    "const arg = (x) => { let o = ((x || { }).action || { }).toolInput || { }; if (typeof o === 'string') { try { o = JSON.parse(o); } catch (e) { o = { }; } }"
    " if (o && o.input && typeof o.input === 'object') o = o.input; return o || { }; };",
    "const res = (x) => { let o = (x || { }).observation; try { if (typeof o === 'string') o = JSON.parse(o);"
    " if (Array.isArray(o) && o[0] && o[0].results) { const r = o[0].results[0].result; o = typeof r === 'string' ? JSON.parse(r) : r; } } catch (e) { }"
    " return (o && typeof o === 'object') ? o : { }; };",
    "let now = false; let ref = '';",
    "for (const x of steps) { const tool = ((x || { }).action || { }).tool; const a = arg(x);"
    " if (tool === 'open_request' && /^(emergency|critical|immediate)$/i.test(String(a.urgency || '').trim())) { now = true; const r = res(x); if (r.reference) ref = String(r.reference); }"
    " if (tool === 'notify_team' && String(a.reason || '').trim() === 'emergency') now = true; }",
    # v3: Sort's last_bot was empty on a live turn (84827), so the chat's own
    # recent outbound rows, newest first, are read too.
    "let outs = []; try { outs = $('Anything newer?').all().map((r) => r.json || { }).filter((r) => r.direction === 'outbound').map((r) => String(r.body || '')); } catch (e) { outs = []; }",
    "const lb = [String(G.last_bot || '')].concat(outs.slice(0, 3)).join(' ');",
    "const URGENT = /קריא(?:ה|ת)(?: ה?שירות)? (?:ה)?(?:דחופה|חירום)|קריא(?:ה|ת)(?: ה?שירות)? בדחיפות|הקריאה הדחופה|קריאת החירום|דחופת חירום|דחיפות חירום/;",
    "if (!now && !URGENT.test(lb) && !URGENT.test(s)) return s;",
    "const REF = /¤b¤d{3}-¤d{3,6}-¤d{2}¤b/g;",
    "if (!ref) { const m = s.match(REF) || String(G.last_bot || '').match(REF); if (m) ref = m[m.length - 1]; }",
    "if (!ref) { for (const b of outs) { const m = b.match(REF); if (m) { ref = m[m.length - 1]; break; } } }",
    # Advice or an instruction: always out, in an emergency.
    # Not "לוודא": "אני רוצה לוודא שאני מבין" is his own question; not "אל תהסס" (v2, the replay).
    "const ADVICE = /(?:^|[¤s,])אל (?!דאגה|תדאג|תהסס)ת[א-ת]+|תתרחק|התרחק|להתרחק|תרחיק|להרחיק|רחוק מ|תכבה|לכבות|כבה את|תנתק|לנתק|נתק את|מפסק"
    "|תתקשר|להתקשר|התקשר|חייג|לחייג|תזמין|להזמין|חשמלאי|אינסטלטור|כיבוי אש|מד.א|משטרה|חברת החשמל|בטיחות|זהירות|היזהר|תיזהר|להיזהר"
    "|שים לב|תשים לב|תוודא|(?:^|[¤s,])וודא ש|תישאר|להישאר|הישאר|תצא |לצאת מ|מומלץ|ממליץ|כדאי|עדיף|אין צורך|לא צריך ל|(?:^|¤D)10[0-2](?:¤D|$)"
    "|(?:^|[¤s,])(?:ת?שמור|ת?שמרו|לשמור) על"
    # A phone number is an instruction to call (v2).
    "|(?:^|[^¤d-])0¤d{1,2}[-¤s]?¤d{3}[-¤s]?¤d{4}(?!¤d)|¤+¤d[¤d¤s-]{7,}|¤*¤d{3,5}|1-?[78]00-?¤d{2,3}-?¤d{3}/;",
    # A promise of arrival or of action: out, unless asked about or denied.
    "const ARRIVE = /בדרך(?! כלל)|(?:^|[¤s,])(?:ו|ש|וש)?(?:יגיע|יגיעו|תגיע|מגיע|מגיעה|מגיעים|יבוא|יבואו|יצאו|יוצא|יוצאים|ישלחו|שולחים)(?=[¤s,.!?]|$)"
    "|הכי מהר|כמה שיותר מהר|בהקדם|במהרה|במהירות|במיידי|באופן מיידי"
    # Handling NOW is a promise; "it will be handled" is the owner's own "when?" line (v2).
    "|(?:^|[¤s,])(?:ו|ש|וש|ה)?(?:מטפל|מטפלת|מטפלים|מטופל|מטופלת)(?=[¤s,.!?]|$)/g;",
    "const asked = (p, i) => p.slice(0, i).split(/¤s+/).slice(-4).some((w) => /^(?:מתי|לא|אין|אינני|אינו)$/.test(w.replace(/[^א-ת]/g, '')));",
    "const promised = (p) => { ARRIVE.lastIndex = 0; let m; while ((m = ARRIVE.exec(p)) !== null) { if (!asked(p, m.index)) return true;"
    " if (m[0] === '') ARRIVE.lastIndex++; } return false; };",
    "const parts = s.match(/(?:[^.!?¤n]|[.!](?=¤S))+[.!?]*¤s*|¤s+/g) || [s];",
    "let cut = false;",
    "const kept = parts.filter((p) => { if (!p.trim()) return true; const bad = ADVICE.test(p) || promised(p); if (bad) cut = true; return !bad; });",
    "if (!cut) return s;",
    "let out = kept.join('').replace(/[ ¤t]{2,}/g, ' ').trim();",
    "const said = String(G.text || '').trim();",
    "const ask = /[?]/.test(said) || /^(?:מה|מתי|איך|למה|האם|יש|אז|כמה|מי|איפה)(?:[¤s,]|$)/.test(said);",
    "if (ref && out.indexOf(ref) === -1) out = (out ? out + ' ' : '') + (ask ? '" + PUSHED + "' : '" + OPEN + "');",
    "return out || s; })();",
]
BLOCK = " ".join(LINES).replace(PH, BS)
assert PH not in BLOCK and "}}" not in BLOCK and "{{" not in BLOCK

# Chat 6 of the 5 Oct evening test, as the fixed system would see it: the
# emergency got its own ticket (255-1349-26 stands in for the new number).
NEW = "255-1349-26"
LEAK = [
    {"tool": "notify_team", "toolInput": {"reason": "emergency", "description": "נזילה על מנורה בחדר מדרגות"},
     "observation": '[{"results":[{"toolCallId":"wa","result":"{\\"ok\\":true,\\"reason\\":\\"emergency\\"}"}]}]'},
]
OPENED = [
    {"tool": "open_request", "toolInput": {"urgency": "emergency", "building": "בר כוכבא 23", "fault_location": "common"},
     "observation": '[{"results":[{"toolCallId":"wa","result":"{\\"ok\\":true,\\"reference\\":\\"' + NEW + '\\"}"}]}]'},
]
T1 = "הבנתי, תודה! פתחתי קריאת חירום עבורך, מספר הקריאה הוא " + NEW + ". אני כאן לכל עדכון."
T2 = "כל הכבוד שאתה נשאר להזהיר את השכנים! 👍 פתחתי לך קריאה דחופה, מספר " + NEW + ", וזה הדבר היחיד שאני יכול לעשות מכאן."
T3 = "פתחתי לך קריאה דחופה, מספר " + NEW + ", וזה הדבר היחיד שאני יכול לעשות מכאן."
T4 = "אני מבין את התסכול שלך, אסף. " + T3
SMOKE = [
    # (reply, the tenant's words, the last bot message, this turn's tools, want)
    ("אוי ואבוי! זה נשמע מסוכן מאוד! אני מעביר את זה לצוות החירום שלנו באופן מיידי. באיזה בניין מדובר?",
     "יש מים שנוזלים מהתקרה בחדר מדרגות בין קומה 1 ל2, ישר על המנורה והיא מהבהבת!!! יש שלולית על המדרגות מה עושים??",
     "", LEAK, "אוי ואבוי! זה נשמע מסוכן מאוד! באיזה בניין מדובר?"),
    ("הבנתי, תודה! פתחתי קריאת חירום עבורך, מספר הקריאה הוא " + NEW + ". הצוות שלנו כבר בדרך לטפל בזה. לגבי כיבוי חשמל - אל תנסה "
     "לגעת בשום דבר שקשור לחשמל או למים בעצמך. בבקשה תתרחק מהאזור הרטוב ואל תאפשר לאף אחד להתקרב לשם. הבטיחות שלך היא הכי חשובה "
     "עכשיו. אני כאן לכל עדכון.",
     "בר כוכבא 23 תל אביב. מה אני עושה בינתיים, לכבות חשמל??", "אוי ואבוי! זה נשמע מסוכן מאוד! באיזה בניין מדובר?", OPENED, T1),
    ("אין לי תאריך מדויק לגבי מתי יגיעו, אבל הקריאה שלך הוגדרה כדחופת חירום, והצוות מטפל בה במיידי. הם יגיעו הכי מהר שאפשר. כל הכבוד "
     "שאתה נשאר להזהיר את השכנים! 👍",
     "אוקיי. תוך כמה זמן הם מגיעים? אני נשאר פה למטה להזהיר את השכנים", T1, [], T2),
    ("אין לי מספר לתת לך להתקשר אליו ישירות, אבל אני יכול להבטיח לך שהצוות עודכן בקריאת החירום שלך (" + NEW + ") ומטפל בזה. בבקשה "
     "תמשיך להישאר רחוק מהאזור המסוכן.",
     "יש מיספר של מישהו שאני יכול להתקשר אליו עכשיו? זה ממשיך לטפטף על המנורה!!", T2, [], T3),
    ("אני מבין את התסכול שלך, אסף. הצוות שלנו בדרך. אין צורך להזמין חשמלאי בעצמך, הומי'ז מטפלת בזה. הדבר היחיד שאני יכול לעשות "
     "מכאן זה לוודא שהקריאה הדחופה שלך מטופלת, וזה מה שקורה.",
     "אז מה, סתם לחכות פה? להזמין חשמלאי לבד או שאתם שולחים מישהו?", T3, [], T4),
    ("בכיף, אסף. תודה רבה על הסבלנות שלך ועל שאתה דואג לשכנים. 🙏 אני מקווה שהצוות יגיע במהרה.",
     "טוב, תודה. אני מחכה להם פה למטה", T4, [],
     # The 🙏 opens the cut sentence, so it goes with it.
     "בכיף, אסף. תודה רבה על הסבלנות שלך ועל שאתה דואג לשכנים. הקריאה הדחופה שלך פתוחה, מספר " + NEW + "."),
    # An honest "no date" in an emergency stays whole.
    ("אין לי תאריך מדויק מתי יגיעו, אבל הקריאה הדחופה שלך פתוחה, מספר " + NEW + ".", "מתי הם מגיעים?", T3, [],
     "אין לי תאריך מדויק מתי יגיעו, אבל הקריאה הדחופה שלך פתוחה, מספר " + NEW + "."),
    # v2, from the run again (live6_leak_panic_fixed): the reply naming the
    # urgent ticket is an emergency before any tool ran.
    ("אוי, זה ממש לא נעים לשמוע! אני מיד מטפל בזה. כדי שאוכל לפתוח קריאת שירות דחופה, אני צריך לדעת באיזה בניין זה קרה ובאיזו דירה אתה גר?",
     "דחוף!!! יש מים שנוטפים מהתקרה בחדר מדרגות ישר על המנורה", "", [],
     "אוי, זה ממש לא נעים לשמוע! כדי שאוכל לפתוח קריאת שירות דחופה, אני צריך לדעת באיזה בניין זה קרה ובאיזו דירה אתה גר?"),
    # "קריאת שירות דחופה" in the last message is the urgent ticket; an honest
    # "no time, it will be handled" stays, the electrician and the safety go.
    ("אני מבין את הדאגה שלך לגבי המנורה והחשמל. אני לא יכול לתת לך הנחיות לגבי ניתוק חשמל, כי זה משהו שרק חשמלאי מוסמך יכול להחליט עליו. "
     "פתחתי קריאת שירות דחופה (מספר " + NEW + ") והצוות שלנו כבר מעודכן. אין לי תאריך מדויק או שעה לומר לך מתי מישהו יגיע, אבל אני יכול "
     "להבטיח לך שזה יטופל כמו שצריך ובמהירות האפשרית. שוב, הכי חשוב עכשיו זה לשמור על הבטיחות שלך ולא להתקרב לאזור הנזילה והמנורה המהבהבת.",
     "כן אבל מה עם החשמל?? לנתק או לא? המנורה עוד מהבהבת. ומתי מישהו מגיע?",
     "הבנתי! פתחתי עכשיו קריאת שירות דחופה לטיפול בזה, מספר הקריאה שלך הוא " + NEW + ". יש עוד משהו שאוכל לעזור בו כרגע?", [],
     "אני מבין את הדאגה שלך לגבי המנורה והחשמל. פתחתי קריאת שירות דחופה (מספר " + NEW + ") והצוות שלנו כבר מעודכן. אין לי תאריך "
     "מדויק או שעה לומר לך מתי מישהו יגיע, אבל אני יכול להבטיח לך שזה יטופל כמו שצריך."),
    # A phone number in an emergency is an instruction to call (a made-up one here).
    ("אני מבין שזה דחוף. המספר היחיד שאני יכול לתת לך הוא 03-1234567, שהוא מספר הטלפון של המשרד שלנו לתקלות דחופות. פתחתי כבר "
     "קריאת שירות דחופה (" + NEW + ") והצוות מעודכן. זה הדבר היחיד שאני יכול לעשות מכאן.",
     "אין מספר שאפשר להתקשר אליו עכשיו?? זה לא יכול לחכות", "פתחתי קריאת שירות דחופה (מספר " + NEW + ").", [],
     "אני מבין שזה דחוף. פתחתי כבר קריאת שירות דחופה (" + NEW + ") והצוות מעודכן. זה הדבר היחיד שאני יכול לעשות מכאן."),
    # From the replay of every past reply (v2): his own "make sure I understand"
    # question stays, "keep calm" and "they'll come asap" go; "don't hesitate to
    # ask" is not advice.
    ("אני מבין שאין מענה מכפתור החירום. זה מתסכל, אבל אל דאגה, אנחנו כאן כדי לעזור. אני רוצה לוודא שאני מבין נכון: האם אתם במעלית בבניין "
     "שבו אתם גרים? אם כן, אנא מסרו לי את כתובת הבניין המלאה (רחוב ומספר), ואת מספר הדירה שלכם. ברגע שאקבל את הפרטים, אוכל לפתוח "
     "קריאת שירות דחופה ולדאוג שיגיעו אליכם מהר ככל האפשר. בינתיים, שמרו על קור רוח. אנחנו איתכם.",
     "נתקעתי במעלית ואין מענה מכפתור החירום", "", [],
     "אני מבין שאין מענה מכפתור החירום. זה מתסכל, אבל אל דאגה, אנחנו כאן כדי לעזור. אני רוצה לוודא שאני מבין נכון: האם אתם במעלית בבניין "
     "שבו אתם גרים? אם כן, אנא מסרו לי את כתובת הבניין המלאה (רחוב ומספר), ואת מספר הדירה שלכם. ברגע שאקבל את הפרטים, אוכל לפתוח "
     "קריאת שירות דחופה. אנחנו איתכם."),
    ("פתחתי קריאת שירות דחופה, מספר 255-1202-26. אם יש לכם שאלות נוספות, אל תהססו לשאול.", "יש נזילה בלובי", "", [],
     "פתחתי קריאת שירות דחופה, מספר 255-1202-26. אם יש לכם שאלות נוספות, אל תהססו לשאול."),
    # v3, the third run (84827): last_bot empty, the urgent ticket in the chat's
    # own last row; everything was cut but the worry, so the ticket line comes.
    ("אני מבינה את הדאגה שלך. במקרים כאלה של מים וחשמל, הכי בטוח זה לא לגעת בכלום ולהתרחק מהאזור. הצוות שלנו קיבל את הקריאה הדחופה "
     "ומטפל בזה. אין לי מידע מדויק מתי יגיעו, אבל הם בדרך לטפל בזה כמה שיותר מהר. אני כאן אם יש לך שאלות נוספות.",
     "אבל מה אני עושה עכשיו?? לכבות את החשמל או לא? ומתי מישהו מגיע", "", [],
     "אני מבינה את הדאגה שלך. אני כאן אם יש לך שאלות נוספות. " + T3,
     ["תודה שעדכנת אותי. פתחתי עכשיו קריאת חירום לטיפול בנזילה. מספר הקריאה הוא " + NEW + "."]),
    # Outside an emergency nothing changes, promise-like words included.
    ("אין לי תאריך מדויק מתי יגיעו לתקן, אבל הקריאה שלך נפתחה והצוות יטפל בזה כמו שצריך. יש משהו נוסף שאוכל לעזור לך בו?",
     "יש מושג בערך מתי יבואו לתקן?", "פתחתי קריאת שירות בנושא, מספרה 255-1347-26.", [],
     "אין לי תאריך מדויק מתי יגיעו לתקן, אבל הקריאה שלך נפתחה והצוות יטפל בזה כמו שצריך. יש משהו נוסף שאוכל לעזור לך בו?"),
    ("אני לא יכול להבטיח מתי בדיוק יחזרו אליך, אבל העברתי לצוות את הבקשה הדחופה שלך. יש משהו נוסף שאוכל לעזור לך בו?",
     "היום?? מתי יחזרו אליי.", "עדכנתי את הצוות שלנו שיחזרו אליך עם תשובה לגבי מועד הטיפול.", [],
     "אני לא יכול להבטיח מתי בדיוק יחזרו אליך, אבל העברתי לצוות את הבקשה הדחופה שלך. יש משהו נוסף שאוכל לעזור לך בו?"),
]

SMOKE_JS = r"""
const fs = require('fs');
const P = JSON.parse(fs.readFileSync(0, 'utf8'));
let f;
try { f = new Function('$json', '$', 'return (' + P.expr + ');'); }
catch (e) { console.log(JSON.stringify({ error: 'does not compile: ' + e.message })); process.exit(0); }
const out = P.cases.map(([reply, said, lastBot, steps, rows]) => {
  const S = { greeting: false, greeted: true, last_bot: lastBot, text: said, tap_now: false };
  const st = steps.map((x) => ({ action: { tool: x.tool, toolInput: x.toolInput }, observation: x.observation }));
  const nodes = {
    'Sort': { first: () => ({ json: S }) },
    'Carry on': { first: () => ({ json: { acked: '', text: said } }) },
    'Answer the resident': { first: () => ({ json: { intermediateSteps: st } }) },
    'Anything newer?': { all: () => (rows || []).map((b) => ({ json: { direction: 'outbound', body: b } })) },
    'Say it now': { all: () => { throw new Error('unexecuted'); } },
    'Try again': { first: () => { throw new Error('unexecuted'); } },
  };
  const $ = (name) => { if (!nodes[name]) throw new Error('no node ' + name); return nodes[name]; };
  try { return JSON.parse(f({ output: reply }, $)).content; } catch (e) { return 'THREW ' + e.message; }
});
console.log(JSON.stringify({ out }));
"""


def smoke(json_body):
    import check_whatsapp_rules as C
    payload = {"expr": C.inner(json_body), "cases": [[c[0], c[1], c[2], c[3], c[5] if len(c) > 5 else []] for c in SMOKE]}
    r = subprocess.run(["node", "-e", SMOKE_JS], capture_output=True,
                       input=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    if r.returncode != 0:
        return ["node failed: " + r.stderr.decode("utf-8", "replace")[:300]]
    res = json.loads(r.stdout.decode("utf-8"))
    if "error" in res:
        return [res["error"]]
    return ["smoke %d:%s  got  %s%s  want %s" % (i, NL, got, NL, want)
            for i, (got, c) in enumerate(zip(res["out"], SMOKE)) if got != c[4]
            for want in [c[4]]]


def snapshot(live):
    if os.path.exists(SNAPSHOT):
        return False
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    live = dict(live, staticData="<stripped: runtime state keyed by phone numbers>")
    text = json.dumps(live, ensure_ascii=False, indent=1)
    if secret:
        if secret not in text:
            sys.exit("The live workflow does not contain N8N_WEBHOOK_SECRET from .env, "
                     "so the snapshot's redaction would miss. Refusing to write it.")
        text = text.replace(secret, PLACEHOLDER)
    with open(SNAPSHOT, "w", encoding="utf-8", newline=NL) as f:
        f.write(text)
    return True


def restore():
    snap = json.load(open(SNAPSHOT, encoding="utf-8"))
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    if not secret:
        sys.exit("N8N_WEBHOOK_SECRET is not in .env; the snapshot's Sort node would "
                 "go live with a placeholder secret. Refusing.")
    body = json.loads(json.dumps(snap, ensure_ascii=False).replace(PLACEHOLDER, secret))
    W.api("PUT", "/api/v1/workflows/%s" % WORKFLOW_ID, {
        "name": body["name"], "nodes": body["nodes"],
        "connections": body["connections"], "settings": body.get("settings", {})})
    print("restored %s from %s (%d nodes)" % (WORKFLOW_ID, SNAPSHOT, len(body["nodes"])))


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv
    W.check_memory_epoch(prompt=W.system_prompt(), inject=U.AGENT_NEW, tools=W.tools_text())

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    if "Send" not in by or "Sort" not in by:
        sys.exit("No Send / Sort node on the live workflow -- refusing to guess.")
    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    before_layout = layout_complaints(nodes)

    changes = []
    body = by["Send"]["parameters"].get("jsonBody") or ""
    if MARK not in body:
        if body.count(ANCHOR) != 1:
            sys.exit("REFUSING: Send does not carry the emoji step this script inserts before. Read the live body first.")
        if NP.MARK not in body:
            sys.exit("REFUSING: Send does not carry the promise filter (%s)." % NP.MARK)
        if OLD_START in body:
            i, j = body.index(OLD_START), body.index(ANCHOR)
            if not i < j:
                sys.exit("REFUSING: the older danger step is not right before the emoji step.")
            by["Send"]["parameters"]["jsonBody"] = body[:i] + BLOCK + " " + body[j:]
            changes.append("Send: danger step -> %s (v3: the chat's own recent rows count as the last "
                           "message when last_bot is empty)" % MARK)
        else:
            by["Send"]["parameters"]["jsonBody"] = body.replace(ANCHOR, BLOCK + " " + ANCHOR)
            changes.append("Send: in an emergency, the urgent ticket and its number only (%s), before the emoji step" % MARK)
    new_body = by["Send"]["parameters"]["jsonBody"]
    if new_body.count("}}") != 1:
        sys.exit("REFUSING: the new Send body has %d '}}'." % new_body.count("}}"))
    sib = NP.siblings()
    # emoji.py's TAIL_NEW is the text it once inserted, with nothing between the
    # menu rule and its step. It decides on MARK, never on TAIL_NEW, so its dry
    # run stays idle with this block in between.
    sib = {k: v for k, v in sib.items()
           if not k.startswith("n8n_whatsapp_danger.") and k != "n8n_whatsapp_emoji.TAIL_NEW"}
    lost = [k for k, v in sib.items() if v in body and v not in new_body]
    if lost:
        sys.exit("REFUSING: the edit would break other patchers' anchors: %s" % lost)
    bad = smoke(new_body)
    if bad:
        sys.exit("REFUSING: the new Send body failed its smoke turns:" + NL + "  " + (NL + "  ").join(bad))

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("Send     : compiles in Node, %d smoke turns right, %d sibling anchors intact"
          % (len(SMOKE), sum(1 for v in sib.values() if v in body)))
    if not changes:
        print("")
        print("Nothing to do. Live already matches.")
        return
    print("")
    print("changes:")
    for ch in changes:
        print("  - %s" % ch)
    worse = sorted(layout_complaints(nodes) - before_layout)
    if worse:
        sys.exit("REFUSING TO PATCH. New placement problems:" + NL + "    " + (NL + "    ").join(worse))
    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        NP.dump(nodes, conns, path)
        print("")
        print("dumped   : %s (the would-be workflow, secret replaced)" % path)
    if not apply:
        print("")
        print("Dry run. Re-run with --apply to write it.")
        return
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": nodes, "connections": conns,
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    sb = {n["name"]: n for n in back["nodes"]}["Send"]["parameters"]["jsonBody"]
    print("")
    print("written: %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  Send carries %s: %s; %s: %s; '}}' count: %d"
          % (MARK, MARK in sb, NP.MARK, NP.MARK in sb, sb.count("}}")))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
