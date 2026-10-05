# -*- coding: utf-8 -*-
"""What counts as a claim in a WhatsApp reply: the one source of the JavaScript
the bot's truth checks run (5 Oct 2026, n8n_whatsapp_safetynet.py).

Not a patcher (it is deliberately not named n8n_whatsapp_*: check_patchers_idle.py
runs every one of those, and NP.siblings() reads their strings as anchors). It
imports nothing from the project, so every patcher that owns a check builds it
from here without importing the others:
  outage.py      `deeds` on Reply usable?            (REPLY_DEEDS)
  paylink.py     `links` on Reply usable?            (URL_GUARD)
  retry.py       Try again: the first draft's verdict and the note (TRY_JSON)
  safetynet.py   `phantom` on Reply usable?, `Claimed a ticket?`, `Mend the reply`

WHY, 5 Oct. The live run as Assaf Clix
(docs/assistant/transcripts/2026-10-05-whatsapp-live-assaf.md): 1 of 9
conversations got everything, and the worst failures came from these checks,
not from the model's drafts.
  - "לא פתחתי קריאה חדשה" (I did NOT open a new ticket) was read as a claim to
    have opened one, twice; the last resort then told him a ticket was open.
  - "בדקתי ולא מצאתי" (I checked and found none) was blocked on the second pass,
    because the second pass cannot see the first pass's lookup.
  - "פתחנו קריאה דחופה (מספר 255-1344-26)", a ticket opened two turns earlier,
    was blocked because no tool ran THIS turn.
So a verb is a claim only when it is said: not negated (לא, טרם, אם among the
three words before it, inside its clause) and not asked (its sentence ends in
"?"). And a ticket number backs a claim only when it is real -- a tool returned
it this turn (either pass), or it is in the conversation's last twelve messages --
and it stands in the claim's own sentence or the one right after it.
When those messages cannot be read, the old rule stands: any number in the
reference's shape.

EVERY STRING HERE IS JAVASCRIPT THAT GOES INSIDE `={{ ... }}`. Three rules from
the files that came before:
  1. `}}` anywhere inside ends the expression, so braces that would touch are
     written with a space between them. Each builder below asserts it.
  2. Backslashes are built with chr(92), never typed (27 Sep: a tool in the chain
     decoded them on the way into a file).
  3. No literal quote character inside a regex class: they are unicode escapes.
"""

BS = chr(92)
NLX = BS + "n"                                     # a newline, as a regex escape
_Q = BS + "u0022" + BS + "u0027" + BS + "u05f3"   # " ' and the Hebrew geresh
# A word starts after a space or punctuation and may carry one prefix letter
# (ו and, ש that, כ as, ה the); it ends at the same set or the end of the text.
# The verb is always group 2. The verb tiers are outage.py's since 27 Sep (its
# docstring says why each verb sits where it does).
B = "(^|[" + BS + "s,.!?:;()" + _Q + "])[ושכה]?"
E = "(?=[" + BS + "s,.!?:;()" + _Q + "]|$)"
NEVER_VERBS = "החלפתי|תיקנתי|סידרתי|ניקיתי|הזמנתי"
TOOLED_VERBS = ("בדקתי|בדקנו|שלחתי|שלחנו|פתחתי|פתחנו|טיפלתי|טיפלנו|"
                "החלפנו|תיקנו|סידרנו|ניקינו|הזמנו|"
                "הוחלף|הוחלפה|הוחלפו|תוקן|תוקנה|תוקנו|טופל|טופלה|טופלו|"
                "סודר|סודרה|סודרו|נוקה|נוקו|הוזמן|הוזמנה|הוזמנו|"
                "נשלח|נשלחה|נשלחו")
NEVER = "/" + B + "(" + NEVER_VERBS + ")" + E + "/"
TOOLED = "/" + B + "(" + TOOLED_VERBS + ")" + E + "/"
# The two verbs a real ticket number makes true without a tool this turn: the
# ticket was opened earlier in the chat, and its number is the proof.
OPEN_VERBS = "['פתחתי','פתחנו']"

# The phantom claim, exactly paylink.py's PHANTOM_NEW (its anchor on the live
# condition; safetynet.py refuses if the two ever differ).
PHANTOM = "/(פתחתי|פתחנו|פותח|פותחת|נפתחה|נפתחו|נפתחת)( " + BS + "S+){0,2}? ?ה?קריא[הת]/"
# A reference as the bot writes it, and as a person may type it.
REF = "/" + BS + "b" + BS + "d{3}-" + BS + "d{3,6}-" + BS + "d{2}" + BS + "b/g"
LOOSE_REF = "/" + BS + "d{3}[" + BS + "s-]?" + BS + "d{3,6}[" + BS + "s-]?" + BS + "d{2}/g"
URL = "/https?:" + BS + "/" + BS + "/" + BS + "S+/g"
URL_TAIL = "/[.,;:!?)" + BS + "]]+$/"

# Sentences: [.!] end one only before a space or the end (so a URL, a decimal and
# a reference stay whole); ? always ends one; a newline always does. Trailing
# whitespace rides with its sentence, so joining the parts gives the text back.
SENT = ("/(?:[^.!?" + NLX + "]|[.!](?=" + BS + "S))+[.!?]*" + BS + "s*|" + BS + "s+/g")

# said(t, re): the matches of `re` in `t` that are said, not denied or asked.
# A clause runs back to the last , ; or : before the verb's word (the boundary a
# match may start with is part of the clause, so "לא, בדקתי" is a claim and "לא
# בדקתי" is not); the three words before it are read for לא / טרם / אם, each
# with up to two prefix letters (שלא, כשלא).
SAID_FN = (
    "const said = (t, re) => { const out = []; "
    "for (const s of (String(t || '').match(" + SENT + ") || [])) { "
    "if (/" + BS + "?" + BS + "s*$/.test(s)) continue; "
    "const r = new RegExp(re.source, 'g'); let m; "
    "while ((m = r.exec(s)) !== null) { "
    "const at = m.index + Math.max(0, m[0].search(/[א-ת]/)); "
    "const head = s.slice(0, at).split(/[,;:]/).pop().trim().split(/" + BS + "s+/).slice(-3).join(' '); "
    "if (/(^|" + BS + "s)[ושכ]{0,2}(לא|טרם|אם)(?=" + BS + "s|$)/.test(head)) continue; "
    "out.push(m); } } return out; }; "
)

# refsIn(s): the references in s, digits only. knownIn(s): the same for a source
# a person typed into or a tool wrote, spaces and all.
REFS_FN = (
    "const refsIn = (s) => (String(s || '').match(" + REF + ") || []).map(x => x.replace(/" + BS + "D/g, '')); "
    "const knownIn = (s) => (String(s || '').match(" + LOOSE_REF + ") || []).map(x => x.replace(/" + BS + "D/g, '')); "
)

# A turn's tool steps as the checks need them: the tool's name and its raw
# observation. `brief` is what a tool returned, for a note a model reads;
# `resultOf` is the same, parsed.
STEPS_FN = (
    "const stepsOf = (xs) => { try { return (xs || []).map(s => ({ tool: String(((s || { }).action || { }).tool || (s || { }).tool || ''), "
    "observation: String((s || { }).observation || '').slice(0, 2000) })); } catch (e) { return []; } }; "
    "const brief = (o) => { try { const x = JSON.parse(o); const y = Array.isArray(x) ? x[0] : x; "
    "const r = y.results[0].result; return (typeof r === 'string' ? r : JSON.stringify(r)).slice(0, 400); } "
    "catch (e) { return String(o || '').slice(0, 400); } }; "
    "const resultOf = (o) => { try { return JSON.parse(brief(o)) || { }; } catch (e) { return { }; } }; "
)

LIB = SAID_FN + REFS_FN + STEPS_FN

# The first pass's steps, which `Try again` carries as `first_steps`: the
# agent's second run cannot see them, and without them its "בדקתי" was a lie.
FIRST_STEPS = "(() => { try { return $('Try again').first().json.first_steps || []; } catch (e) { return []; } })()"
# Reply usable?'s view of the turn: this pass's steps, plus the first pass's on
# the second.
STEPS_BOTH = "[].concat(stepsOf($json.intermediateSteps), $runIndex > 0 ? " + FIRST_STEPS + " : [])"


def known_js(steps_js):
    """Statements that set `known` to the digits of every real reference in
    reach: the tools' observations in `steps_js` and the last twelve messages
    `Anything newer?` read. `known` stays null when those messages cannot be
    read; `backed` then falls back to the shape alone, the rule before 5 Oct."""
    return ("let known = null; { let src = ''; for (const x of (" + steps_js + ")) src += ' ' + String(x.observation || ''); "
            "let rows = null; try { rows = $('Anything newer?').all(); } catch (e) { rows = null; } "
            "if (rows !== null) { for (const r of rows) src += ' ' + String(((r || { }).json || { }).body || ''); "
            "known = knownIn(src); } } ")


# backed(t): t carries a reference in the right shape, and it is a real one.
# claimsBacked(t, re): every sentence where `re` is said carries a real reference
# itself or in the sentence right after it ("פתחתי לך קריאה. המספר: 255-…").
# Per sentence, not per reply: the offline run's "הקריאה שלך 255-1460-26
# מסומנת כמטופלת... אני פותח לך קריאת שירות חדשה" claimed a NEW ticket while
# the only number in it was the old one (5 Oct, the safetynet replay).
BACKED = ("const backed = (t) => { const mine = refsIn(t); if (!mine.length) return false; "
          "if (known === null) return true; return mine.some(x => known.indexOf(x) !== -1); }; "
          "const claimsBacked = (t, re) => { const ps = (String(t || '').match(" + SENT + ") || []).filter(p => p.trim()); "
          "for (let i = 0; i < ps.length; i++) { if (!said(ps[i], re).length) continue; "
          "if (!backed(ps[i] + ' ' + (ps[i + 1] || ''))) return false; } return true; }; ")


def _expr(body):
    """`body` is statements ending in a return. Wrapped as n8n reads it."""
    s = "={{ (() => { " + body + "})() }}"
    assert s.count("}}") == 1, "a }} inside the expression ends it early"
    return s


# --- Reply usable? ----------------------------------------------------------
def phantom_expr():
    """`phantom`: a ticket claimed as opened must carry a real reference."""
    return _expr(LIB + "const t = String($json.output || ''); "
                 "if (!said(t, " + PHANTOM + ").length) return true; "
                 "const st = " + STEPS_BOTH + "; " + known_js("st") + BACKED +
                 "return claimsBacked(t, " + PHANTOM + "); ")


def deeds_expr():
    """`deeds`: first-person physical work is always a lie; a tool-shaped deed is
    true only when a tool ran this turn (either pass), or when it is the opening
    of a ticket whose real number stands in its sentence or the next."""
    return _expr(LIB + "const t = String($json.output || ''); "
                 "if (said(t, " + NEVER + ").length) return false; "
                 "const tooled = said(t, " + TOOLED + "); if (!tooled.length) return true; "
                 "const st = " + STEPS_BOTH + "; if (st.length > 0) return true; "
                 "if (!tooled.every(m => " + OPEN_VERBS + ".indexOf(m[2]) !== -1)) return false; "
                 + known_js("st") + BACKED + "return claimsBacked(t, " + TOOLED + "); ")


def truth_js(text_js, steps_js, words_js):
    """Statements that judge `text_js` the way Reply usable?'s four truth guards
    do, given the turn's tool steps, and set `v` to { ok, words, phantom, links,
    deeds }. LIB must be in scope. Try again runs it on the first draft, so the
    last resort decides on the guards' own verdict."""
    return (
        "const v = (() => { const t = String(" + text_js + " || ''); const st = " + steps_js + "; "
        + known_js("st") + BACKED +
        "const words = " + words_js + "; "
        "const phantom = claimsBacked(t, " + PHANTOM + "); "
        "let seen = ''; for (const x of st) { if (x.tool === 'get_payment_link') seen += ' ' + x.observation; } "
        "const links = (t.match(" + URL + ") || []).every(u => seen.indexOf(u.replace(" + URL_TAIL + ", '')) !== -1); "
        "const tooled = said(t, " + TOOLED + "); "
        "const deeds = said(t, " + NEVER + ").length === 0 && (tooled.length === 0 || st.length > 0 "
        "|| (tooled.every(m => " + OPEN_VERBS + ".indexOf(m[2]) !== -1) && claimsBacked(t, " + TOOLED + "))); "
        "return { ok: words && phantom && links && deeds, words, phantom, links, deeds }; })(); "
    )


# Reply usable?'s `words`, the same rule: two words, or one on a greeting or a photo.
FIRST_WORDS = ("(() => { const w = t.trim().split(/" + BS + "s+/).filter(Boolean).length; if (w >= 2) return true; "
               "let S = { }; try { S = $('Sort').first().json; } catch (e) { S = { }; } "
               "return w === 1 && (S.greeting === true || S.photo === true); })()")


# --- The last resort --------------------------------------------------------
# The owner approved both sentences on 5 Oct. The second does not hand the
# tenant on: *"we are the team there is no one to send it to"*.
TICKET_LINE = "פתחתי על זה קריאה, מספר "
FALLBACK = "סליחה, משהו השתבש לי בתשובה. אפשר לכתוב לי את זה שוב?"
TRY_AGAIN = "$('Try again').first().json"


def claimed_expr():
    """`Claimed a ticket?`: after two rejected passes, does the reply that would
    go out claim a ticket that has no real number behind it? Only then is a
    rescue ticket opened. Not when the first draft goes out instead (its only
    fault was style), and not when a ticket really was opened this turn (its
    number is put into the reply instead)."""
    return _expr(LIB + "let T = { }; try { T = " + TRY_AGAIN + "; } catch (e) { T = { }; } "
                 "if (T.first_truth_ok === true) return false; "
                 "const t = String($json.output || ''); if (!said(t, " + PHANTOM + ").length) return false; "
                 "const st = [].concat(T.first_steps || [], stepsOf($json.intermediateSteps)); "
                 + known_js("st") + BACKED +
                 "if (claimsBacked(t, " + PHANTOM + ")) return false; "
                 "return !st.some(x => x.tool === 'open_request' && resultOf(x.observation).reference); ")


def mend_expr():
    """`Mend the reply`: what goes out after two rejected passes. No model: the
    first draft when its only fault was style; otherwise the second, with every
    sentence that claims what did not happen taken out, the ticket's real number
    put where a false ticket claim was, and, when too little is left, the one
    fixed line. Never nothing."""
    body = (LIB + "let T = { }; try { T = " + TRY_AGAIN + "; } catch (e) { T = { }; } "
            "if (T.first_truth_ok === true && String(T.first_output || '').trim()) "
            "return JSON.stringify({ output: String(T.first_output), mended: 'first draft' }); "
            "let A = { }; try { A = $('Answer the resident').first().json; } catch (e) { A = { }; } "
            "const draft = String(A.output || '').split('§§§').join(String.fromCharCode(10)); "
            "const st = [].concat(T.first_steps || [], stepsOf(A.intermediateSteps)); "
            + known_js("st") + BACKED +
            "let seen = ''; for (const x of st) { if (x.tool === 'get_payment_link') seen += ' ' + x.observation; } "
            "let ref = ''; try { const r = $json.results[0].result; ref = String((typeof r === 'string' ? JSON.parse(r) : r).reference || ''); } catch (e) { ref = ''; } "
            "if (!ref) { for (const x of st) { if (x.tool === 'open_request') { const rr = resultOf(x.observation).reference; if (rr) ref = String(rr); } } } "
            "const parts = draft.match(" + SENT + ") || []; const real = parts.filter(p => p.trim()); "
            "const out = []; const gone = []; let placed = false; let j = -1; "
            "for (const s of parts) { if (!s.trim()) { out.push(s); continue; } j++; "
            # A claim is backed by a real number in its sentence or the next.
            "const ok = backed(s + ' ' + (real[j + 1] || '')); "
            "if ((s.match(" + URL + ") || []).some(u => seen.indexOf(u.replace(" + URL_TAIL + ", '')) === -1)) { gone.push('link'); continue; } "
            "if (said(s, " + NEVER + ").length) { gone.push('deed'); continue; } "
            # A false ticket claim before a false deed: "פתחתי לך קריאה" is both,
            # and the ticket's real number belongs where it stood.
            "if (!ok && said(s, " + PHANTOM + ").length) { gone.push('ticket'); "
            "if (ref && !placed) { out.push('" + TICKET_LINE + "' + ref + '. '); placed = true; } continue; } "
            "const tooled = said(s, " + TOOLED + "); "
            "if (tooled.length && !st.length && !(ok && tooled.every(m => " + OPEN_VERBS + ".indexOf(m[2]) !== -1))) { gone.push('deed'); continue; } "
            "out.push(s); } "
            "if (ref && !placed && $json.results) { out.unshift('" + TICKET_LINE + "' + ref + '. '); placed = true; } "
            "let text = out.join('').replace(/[ " + BS + "t]+" + NLX + "/g, String.fromCharCode(10)).trim(); "
            "if (!placed && text.split(/" + BS + "s+/).filter(Boolean).length < 3) { text = '" + FALLBACK + "'; gone.push('fallback'); } "
            "return JSON.stringify({ output: text, mended: gone.join(',') || 'kept' }); ")
    s = "={{ (() => { " + body + "})() }}"
    assert s.count("}}") == 1, "a }} inside the expression ends it early"
    return s
