# -*- coding: utf-8 -*-
"""No promise reaches a resident: a deterministic filter in Send.

    python scripts/n8n_whatsapp_nopromise.py            # dry run
    python scripts/n8n_whatsapp_nopromise.py --dump F   # dry run, plus the would-be workflow
                                                        # in F for check_whatsapp_rules.py
    python scripts/n8n_whatsapp_nopromise.py --apply    # write it
    python scripts/n8n_whatsapp_nopromise.py --restore  # put the 1 Oct snapshot back

WHY, 1 Oct. The automated QA (docs/assistant/transcripts/2026-10-01-whatsapp-qa-abc.md)
found that the bot's replies carry promises the prompt already forbids: "הצוות שלנו
יטפל בזה בהקדם", "יחזרו אליכם בהקדם", "אל דאגה, אני מטפל בזה", "עזרה בדרך". Two of
the three real replies after the 27 Sep deploy had one; 33 of 352 in September; 72
of the 870 rows ever sent. The rule is in the prompt, so this is the model
slipping, and no wording can be proven to stop a slip offline (Claude never wrote
one in 61 test conversations; Gemini wrote three on 30 Sep). Owner: *"ok lets fix
that but make sure it wont break any other feature."*

WHY A FILTER IN SEND, NOT A GUARD THAT SENDS THE REPLY BACK. Most promises come
right after a ticket was opened ("פתחתי קריאה מספר X. הצוות יטפל בזה בהקדם"). The
second pass is rebuilt from `Still the last word?` and does not see the first
pass's tool results (manners.py, section 2, the 27 Sep review), so sending that
reply back would make the model open a second ticket, and a second refusal goes
to `Open it anyway` (a stub). A retry is also a second Gemini call. The greeting
filter already shows the safe shape: Send removes text, deterministically, and
never adds any (the owner's rule: no fixed messages but the menu).

WHAT IT DOES, after the greeting filter (`c`), before the buttons rule:
  - The canned menu and the first beat of a two-part payment reply (`two`, which
    may say "I'm on it") go out as they are.
  - No promise phrase: `c` goes out byte-identical.
  - Each sentence with a promise loses only the promise clause when what is left
    is a clean sentence: cut at the last comma, `;`, ` ו`, or the space before a
    ו/ש/כש-prefixed match, trying at most three boundaries, latest first; a
    leading "אל דאגה, " goes with its comma. What is left must have two words,
    must not start with ו/גם, must not end on a word that needs more ("כדי",
    "וביקשתי", "של"...), must not be a bare subordinate clause ("ברגע שאפתח
    קריאה"), and must keep every ticket number and link the sentence had. A cut
    at a comma never leaves a sentence that opens with "אם"/"ברגע"/"כש…": there
    the promise was the main clause ("אם מדובר ברכוש המשותף, …, נטפל בזה"), and
    what is left would be a dangling "if" (found by the 1 Oct replay).
  - Otherwise the sentence goes whole, unless it carries a ticket number or a
    link, or it is the only sentence: those stay whole, promise and all.
  - A comma inside a number is not a boundary. A dot inside a link or a decimal
    does not end a sentence (a sentence ends at .!? followed by a space, at an
    emoji followed by a space, or at a newline).
  - The result goes out only if it has two words, does not start with ו/גם where
    the original did not, and carries every ticket number and link the original
    did. Otherwise `c` goes out. The filter can only remove.

Measured on all 870 rows ever sent (check_whatsapp_rules.py --replay is the
proof): every changed reply had a promise phrase in it, none came out broken.
One known false positive in all of history: "אני ממליץ לכם לפנות למשטרה בהקדם."
(advice, dropped; that reply was a police referral the prompt bans anyway).

WHAT IT DOES NOT TOUCH. The model's text: `Log reply` stores the raw output, so
the messages table and the dashboard keep showing what the model wrote, as they
already do for the greeting filter's cuts; `--watch` reads the executions and is
the proof of what residents got. `Team note this turn?` reads the raw output, so
a cut "יחזרו אליכם" still makes its team note, and the "I passed it to the team"
that stays is true. `Send the rest`, `Say it now`, the guards, the retry note,
the prompt, the pins, MEMORY_EPOCH: unchanged (no text a model reads changes).

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, then `--apply`, then the check
again on live, then every WhatsApp patcher's dry run idle. Before the PUT this
script also compiles the new Send body in Node and runs two turns through it.

Idempotent. Running it twice reports nothing to do. A later version replaces
this one by its marker.

v2, 1 Oct: the singular "you" forms (אותך, אליך, אלייך) beside the plural ones,
because the bot now writes to one person. Applied by n8n_whatsapp_gender.py in
the same write as the prompt change; this script is idle after it.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_untemplate as U  # noqa: E402
import n8n_whatsapp_manners as M  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-01oct-before-nopromise.json")
PLACEHOLDER = "REPLACE_WITH_N8N_WEBHOOK_SECRET"
NEED = ("Send", "Sort", "Carry on", "Answer the resident", "Two parts?",
        "Anything newer?", "Say it now")

# A backslash is built, never typed: this tool chain has eaten typed ones
# (manners.py, 27 Sep). In the templates below `¤` stands for one backslash and
# is replaced once, at the end; an assertion checks none is left.
BS = chr(92)
PH = "¤"
MARK = "const pv = 'promise v2';"

# The promise phrases. One list, two wrappers: the JS filter and PROMISE_PY.
# Not here, on purpose: "עד מחר" ("אפשר לשלם עד מחר" is a fact in the link
# message), "תוך…" and "עד 3 ימי עסקים" (the facts answer), "בטיפול" (a status
# the tool returned), "אני בודק את זה עכשיו" (the ack), "עוד היום" (too often a
# plain fact), "זה יצור קשר עם…" (the pronoun is required).
# v2, 1 Oct: the bot addresses one person now (the owner: "it still uses how
# can i help you all"), so every "you" in the list also has its singular,
# masculine and feminine: אותך, אליך, אלייך. The plural forms are unchanged.
PHRASES = ("בהקדם|בקרוב|בימים הקרובים|בשעות הקרובות|בהמשך היום|"
           "אל דאגה|אל תדאגו|אל תדאגי|אל תדאג|אנחנו על זה|אני על זה|"
           "אני כבר מטפל בזה|אני מטפל בזה|מטפל בזה מיד|אני אטפל בזה|נטפל בזה|נטפל בה|"
           "יטפלו? (בזה|בו|בה|בעניין)|"
           "(יחזרו|יחזור|תחזור|נחזור|אחזור) (אליכם|אלייך|אליך)|"
           "(ייצרו|יצרו|ייצור|יצור|ניצור|תיצור) ((אתכם|איתכם|איתך|אתך) קשר|קשר (אתכם|איתכם|איתך|אתך))|"
           "(יעדכנו|יעדכן|נעדכן|אעדכן) (אתכם|אותך)|"
           "בדרך (אליכם|אליך|אלייך)|(עזרה|מישהו|הצוות|הטכנאי) בדרך|"
           "הטכנאי יגיע|מישהו יגיע|(נשלח|ישלחו) ((אליכם|אליך|אלייך) )?(מישהו|טכנאי)|"
           "יגיעו? (אליכם|אליך|אלייך|בקרוב|היום|מחר)")
# The ones that open a sentence and can be cut away with their comma.
OPENERS = ("אל דאגה|אל תדאגו|אל תדאגי|אל תדאג|אנחנו על זה|אני על זה|"
           "אני כבר מטפל בזה|אני מטפל בזה|מטפל בזה מיד|אני אטפל בזה|נטפל בזה")
PREFIX = "(וש|כש|ו|ש)?"

EP = "¤p{Extended_Pictographic}¤uFE0F"
EDGE = "[¤s,.!?:;()¤u0022¤u0027¤u05f3" + EP + "]"
P_RE = "/(^|" + EDGE + ")" + PREFIX + "(" + PHRASES + ")(?=" + EDGE + "|$)/u"
PI_RE = "/^(" + OPENERS + ")(?=" + EDGE + "|$)/u"
REF_RE = "/¤d{3}-¤d{1,6}-¤d{2}|HM-¤d{4}-¤d{3,6}|https?:¤/¤//"
REFG_RE = "/¤d{3}-¤d{1,6}-¤d{2}|HM-¤d{4}-¤d{3,6}|https?:¤/¤/¤S+/g"
SENT_RE = ("/[¤s¤S]*?(?:[.!?]+(?:[^¤S¤n]*[" + EP + "]+)*(?:¤s+|$)|[" + EP
           + "]+(?:¤s+|$)|[^¤S¤n]*¤n¤s*|$)/gu")
TAIL_RE = "/^([¤s¤S]*?)([.!?]+(?:[^¤S¤n]*[" + EP + "]+)*)?(¤s*)$/u"
FRAG_RE = "/^(גם|ו[א-ת])/"
# A word that needs more after it: a cut that ends on one is a fragment.
DANGLE_RE = ("/(^|¤s)ו?(ביקשתי|ביקשנו|לוודא|לדאוג|רוצה|רוצים|מקווה|מקווים|כדי|מנת|"
             "בשביל|אבל|או|אז|גם|רק|כי|אם|ש|אשר|כך|ככה|"
             "של|את|על|עם|אל|עבור|לגבי|בנוגע|מול|לפי|אצל|בין|כמו)$/")
# A subordinate lead-in with no main clause after it ("ברגע שאפתח קריאה").
SUB_RE = ("/^(אם|כאשר|ברגע|אחרי|לפני|למרות|בגלל|כדי|מאחר|היות|בזמן|ככל|כיוון|מכיוון)"
          "(?=[¤s,]|$)|^כש[א-ת]|^עד ש/")

# One JS statement per string, joined with spaces. No two closing braces ever
# meet: n8n ends an expression at the first `}}`.
LINES = [
    "body.content = (() => { " + MARK,
    "if (two) return c;",
    "let G = { }; try { G = $('Sort').first().json || { }; } catch (e) { G = { }; }",
    "if (G.greeting === true) return c;",
    "const P = " + P_RE + ";",
    "if (!P.test(c)) return c;",
    "const PI = " + PI_RE + ";",
    "const REF = " + REF_RE + ";",
    "const REFG = " + REFG_RE + ";",
    "const SENT = " + SENT_RE + ";",
    "const TAIL = " + TAIL_RE + ";",
    "const FRAG = " + FRAG_RE + ";",
    "const DANGLE = " + DANGLE_RE + ";",
    "const SUB = " + SUB_RE + ";",
    "const bare = (x) => x.replace(/[.,;:!?)¤]]+$/, '');",
    "const refsOf = (s) => (s.match(REFG) || []).map(bare);",
    "const words = (s) => s.trim().split(/¤s+/).filter(Boolean).length;",
    "const okCut = (s) => words(s) >= 2 && !FRAG.test(s) && !DANGLE.test(s) "
    "&& !(SUB.test(s) && s.indexOf(',') === -1);",
    "const isSep = (s, j) => (s[j] === ',' || s[j] === ';') "
    "&& !(/¤d/.test(s[j - 1] || '') && /¤d/.test(s[j + 1] || ''));",
    "const clean = (s) => { const m = s.match(TAIL); let core = m ? m[1] : s; "
    "const tail = m ? (m[2] || '') + m[3] : ''; const refs = refsOf(core);",
    "for (let i = 0; i < 4; i++) { const h = core.match(P); if (!h) break; const p = h.index + h[1].length;",
    "const bs = []; for (let j = p; j > 0 && bs.length < 3; j--) { "
    "if ((j === p - 1 && h[2] && core[j] === ' ') || isSep(core, j) || (core[j] === ' ' && core[j + 1] === 'ו')) bs.push(j); }",
    "let next = null; for (const b of bs) { const k = core.slice(0, b).replace(/[¤s,;:]+$/, '').trim(); "
    "if (okCut(k) && !(isSep(core, b) && SUB.test(k))) { next = k; break; } }",
    "if (next === null && p === 0 && PI.test(core)) { const q = core.slice(h[0].length).match(/^¤s*,¤s*/); "
    "if (q) { const k = core.slice(h[0].length + q[0].length).trim(); if (okCut(k)) next = k; } }",
    "if (next === null || refs.some((x) => next.indexOf(x) === -1)) return '';",
    "core = next; }",
    "return P.test(core) ? '' : core + tail; };",
    "const sents = (c.match(SENT) || [c]).filter((s) => s.length > 0);",
    "let changed = false; const out = [];",
    "for (const s of sents) { if (!P.test(s)) { out.push(s); continue; } const k = clean(s); "
    "if (k) { out.push(k); changed = true; continue; }",
    "if (sents.length === 1 || REF.test(s)) { out.push(s); continue; } changed = true; }",
    "if (!changed) return c;",
    "const r = out.join('').trim();",
    "if (words(r) < 2 || (FRAG.test(r) && !FRAG.test(c))) return c;",
    "if (refsOf(c).some((x) => r.indexOf(x) === -1)) return c;",
    "return r; })();",
]
FILTER = " ".join(LINES).replace(PH, BS)
assert PH not in FILTER and "}}" not in FILTER and "{{" not in FILTER

# The junction: the greeting filter's `const body` line, then twobeat's buttons rule.
SEND_OLD = "const body = { content: c, message_type: 'outgoing' }; if (!two && ("
SEND_NEW = ("const body = { content: c, message_type: 'outgoing' }; " + FILTER
            + " if (!two && (")
BLOCK_START = "body.content = (() => { const pv = 'promise v"
BLOCK_END = " if (!two && ("

# For check_whatsapp_rules.py --watch: the same phrases, Python boundaries.
PROMISE_PY = re.compile(("(?:^|¤W)(?:וש|כש|ו|ש)?(?:" + PHRASES + ")(?=¤W|$)").replace(PH, BS))

# Two turns the patcher runs through the new Send body before any PUT.
SMOKE = [
    ("פתחתי לכם קריאה מספר 255-1339-26. הצוות שלנו יטפל בזה בהקדם. במה אוכל לעזור עוד?",
     "Bar Kochba 23", "פתחתי לכם קריאה מספר 255-1339-26. במה אוכל לעזור עוד?"),
    ("איזה מעצבן. באיזה בניין ובאיזו דירה?", "the lights",
     "איזה מעצבן. באיזה בניין ובאיזו דירה?"),
]
SMOKE_JS = """
const fs = require('fs');
const P = JSON.parse(fs.readFileSync(0, 'utf8'));
let f;
try { f = new Function('$json', '$', 'return (' + P.expr + ');'); }
catch (e) { console.log(JSON.stringify({ error: 'does not compile: ' + e.message })); process.exit(0); }
const out = P.cases.map(([reply, said]) => {
  const S = { greeting: false, greeted: true, last_bot: '', text: said, tap_now: false };
  const nodes = {
    'Sort': { first: () => ({ json: S }) },
    'Carry on': { first: () => ({ json: { acked: '', text: said } }) },
    'Answer the resident': { first: () => ({ json: { intermediateSteps: [] } }) },
    'Anything newer?': { all: () => [] },
    'Say it now': { all: () => { throw new Error('unexecuted'); } },
  };
  const $ = (name) => { if (!nodes[name]) throw new Error('no node ' + name); return nodes[name]; };
  try { return JSON.parse(f({ output: reply }, $)).content; } catch (e) { return 'THREW ' + e.message; }
});
console.log(JSON.stringify({ out }));
"""


def smoke(json_body):
    """Compile the whole Send expression in Node and run SMOKE through it."""
    import check_whatsapp_rules as C
    expr = C.inner(json_body)
    payload = {"expr": expr, "cases": [[a, b] for a, b, _ in SMOKE]}
    r = subprocess.run(["node", "-e", SMOKE_JS], capture_output=True,
                       input=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    if r.returncode != 0:
        return ["node failed: " + r.stderr.decode("utf-8", "replace")[:300]]
    res = json.loads(r.stdout.decode("utf-8"))
    if "error" in res:
        return [res["error"]]
    return ["smoke %d: got %r, want %r" % (i, got, want)
            for i, (got, (_, _, want)) in enumerate(zip(res["out"], SMOKE)) if got != want]


def siblings():
    """Every module-level string of 12+ characters in every other WhatsApp patcher."""
    import importlib
    here = os.path.dirname(os.path.abspath(__file__))
    found = {}
    for fn in sorted(os.listdir(here)):
        if not (fn.startswith("n8n_whatsapp_") and fn.endswith(".py")) or fn == os.path.basename(__file__):
            continue
        try:
            mod = importlib.import_module(fn[:-3])
        except SystemExit:
            continue
        except Exception:  # noqa: BLE001 -- a dead patcher's import is not our problem
            continue
        for k, v in vars(mod).items():
            if isinstance(v, str) and len(v) >= 12 and not k.startswith("__"):
                found["%s.%s" % (fn[:-3], k)] = v
    return found


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
    with open(SNAPSHOT, "w", encoding="utf-8", newline="\n") as f:
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


def dump(nodes, conns, path):
    """The would-be workflow, for check_whatsapp_rules.py --candidate. The
    webhook secret is replaced as in the snapshot; nothing the check reads uses it."""
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    text = json.dumps({"nodes": nodes, "connections": conns}, ensure_ascii=False)
    if secret:
        text = text.replace(secret, PLACEHOLDER)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    W.check_memory_epoch(prompt=W.system_prompt(), inject=U.AGENT_NEW, tools=W.tools_text())

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in NEED:
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    before_layout = layout_complaints(nodes)

    changes = []
    body = by["Send"]["parameters"].get("jsonBody") or ""
    if SEND_NEW in body:
        pass
    elif BLOCK_START in body:
        a = body.index(BLOCK_START)
        z = body.index(BLOCK_END, a)
        by["Send"]["parameters"]["jsonBody"] = body[:a] + FILTER + body[z:]
        changes.append("Send: promise filter replaced with %s" % MARK)
    else:
        if M.MARK not in body:
            sys.exit("REFUSING: Send does not carry the greeting filter (%s); this filter "
                     "reads its `c`. Read the live body first." % M.MARK)
        if body.count(SEND_OLD) != 1:
            sys.exit("REFUSING: Send.jsonBody does not carry the body/buttons junction this "
                     "script knows exactly once (found %d). Read the live body first."
                     % body.count(SEND_OLD))
        by["Send"]["parameters"]["jsonBody"] = body.replace(SEND_OLD, SEND_NEW, 1)
        changes.append("Send: promise filter in (%s), after the greeting filter, "
                       "before the buttons rule" % MARK)

    new_body = by["Send"]["parameters"]["jsonBody"]
    if new_body.count("}}") != 1:
        sys.exit("REFUSING: the new Send body has %d '}}' -- n8n would end the expression "
                 "early." % new_body.count("}}"))
    sib = siblings()
    clash = [k for k, v in sib.items()
             if (k.endswith("_OLD") or k.endswith("_PLAIN") or k.endswith(".DEAD")) and v in FILTER]
    if clash:
        sys.exit("REFUSING: the filter contains other patchers' OLD anchors: %s" % clash)
    lost = [k for k, v in sib.items() if v in body and v not in new_body]
    if lost:
        sys.exit("REFUSING: the edit would break other patchers' anchors: %s" % lost)
    bad = smoke(new_body)
    if bad:
        sys.exit("REFUSING: the new Send body failed its smoke turns:\n  " + "\n  ".join(bad))

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("Send     : compiles in Node, %d smoke turns right, %d sibling anchors intact"
          % (len(SMOKE), sum(1 for v in sib.values() if v in body)))
    if not changes:
        print("\nNothing to do. Live already matches.")
        return
    print("\nchanges:")
    for ch in changes:
        print("  - %s" % ch)

    worse = sorted(layout_complaints(nodes) - before_layout)
    if worse:
        sys.exit("REFUSING TO PATCH. This would introduce placement problems "
                 "that are not already there:\n    " + "\n    ".join(worse))

    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        dump(nodes, conns, path)
        print("")
        print("dumped   : %s (the would-be workflow, secret replaced)" % path)

    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": nodes, "connections": conns,
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    bb = {n["name"]: n for n in back["nodes"]}
    sb = bb["Send"]["parameters"]["jsonBody"]
    print("\nwritten: %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  Send carries %s: %s; the greeting filter %s: %s; '}}' count: %d" % (
        MARK, MARK in sb, M.MARK, M.MARK in sb, sb.count("}}")))
    print("  Reply usable? conditions %s" % [
        c.get("id") for c in bb["Reply usable?"]["parameters"]["conditions"]["conditions"]])
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
