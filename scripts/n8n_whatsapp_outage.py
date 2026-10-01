# -*- coding: utf-8 -*-
"""When the bot's model cannot run, say so honestly -- and never claim work.

    python scripts/n8n_whatsapp_outage.py            # dry run
    python scripts/n8n_whatsapp_outage.py --apply    # write it
    python scripts/n8n_whatsapp_outage.py --restore  # put the 27 Sep snapshot back

WHY, 27 Sep. The owner's tester reported flickering stairwell lights and got
back: "בדקתי את התאורה... החלפתי את הנורות שהבהבו ועכשיו הכל תקין" -- I checked
the lighting, I replaced the flickering bulbs, all fine now. No ticket. Owner:
*"wtf is this why is it inventing"*.

Execution 65271 says exactly what happened, and it was not the main prompt:

  1. The real agent never answered. OpenRouter refused its call three times,
     `Prompt tokens limit exceeded: 20377 > 18331` -- the ACCOUNT was at
     -$0.17. The key's "$14.98 left" is a spending cap, not money. Small calls
     still fit; the agent's 20k-token prompt did not.
  2. The agent's error output went to `Say it again`, the rescue node built on
     18 Sep. It has no tools, and its system message said "אתה מדווח מה כבר
     נעשה" -- report what has already been done -- and "don't say a ticket was
     opened without a number". Told to report a finished deed, forbidden the
     only honest one, and unable to do anything, it reported a repair.
  3. Its only gate, `Second try usable?`, counted two words.

sayagain.py wired the error output there believing "if the model is what
failed, the retry fails too and nothing is sent". On 27 Sep the model had NOT
failed -- the wallet had, and the rescue's 325-token prompt was small enough to
be paid for when the agent's was not. The assumption broke silently, and the
same shape had already answered five turns on 25 Sep.

ONE NODE WAS SERVING TWO OPPOSITE SITUATIONS UNDER ONE INSTRUCTION. On the
rescue path a ticket WAS just opened, and "report what was done, with the
number" is right. On the error path nothing was done, and the same sentence
generates the lie. Two meanings get two nodes:

  Answer the resident (error) --> Tell the team the bot is down   (runs first)
                              \\-> Could not answer --> Outage reply usable? --> send

`Could not answer` is an agent with no tools, no memory, and -- deliberately --
NOT the resident's words: it is told only that a message could not be
handled. With nothing to answer, there is nothing to invent specifics about.
It writes, in its own words (the owner's no-fixed-message rule), that there is
a technical problem on our side and the message is with the team, promising
nobody and nothing. `Tell the team the bot is down` is what makes that true:
the same sub-workflow as `Let the team know`, reason `system_error` (labelled
in Hebrew in n8n_handover.py; the 24-hour per-reason guard means one note per
conversation per outage, not one per message). It sits ABOVE the writer on the
canvas because executionOrder v1 runs the higher branch first, and the writer
continues on error, so a model that is fully down still leaves the note.

`Say it again` keeps its job, the rescue, fed only by `Open it anyway`, and its
sentence is scoped in sayagain.py: it reports the stub ticket and nothing else.

THE DEEDS GUARD. No gate anywhere looked for claimed WORK -- `phantom` is a
phantom-ticket check (verb פתח + noun קריאה, reference required) and today's
reply never mentioned a ticket. Two tiers, tested on all 863 replies the bot
had ever sent (9 Aug - 27 Sep):

  NEVER   first-person-singular physical work. The bot is one person and does
          none; no tool does any. Always a lie. Hits: 1 of 863 -- today's.
  TOOLED  tool-shaped deeds and passives (checked, sent, opened, handled,
          was fixed / replaced / sent...). True only when a tool ran THIS turn.
          62 of 863 match, and the ones read by eye all had a tool behind them.
          `טיפלתי` lives here, not in NEVER: five real replies say "טיפלתי
          בפתיחת קריאת שירות", which is honest. Plural and passive forms live
          here too, because "they fixed it" can be a status the tool returned.

Deliberately NOT in either tier: העברתי / העברנו / עדכנתי. "I told the team"
without the tool is what `Team note this turn?` exists to catch -- it sends the
note after the fact (14 Sep, "the note is what brings that promise closest to
true"). Rejecting it here would take that job away from the node designed for
it.

Where each tier applies:

  Reply usable?        NEVER always; TOOLED unless the agent's own
                       intermediateSteps has a step. Both passes: a false deed
                       on the retry goes to the rescue, never to the resident.
  Second try usable?   NEVER always; TOOLED unless the verb is open/handle AND
                       a reference is in the text -- the rescue's one real deed.
  Outage reply usable? both tiers always, plus no link, no reference, >= 2 words.
                       No false branch: a bad outage line is dropped; the team
                       note has already gone.

`Try again`'s note gains the deeds reason, from retry.py's RETRY_NOTE, and
`Say it again`'s system message comes from sayagain.py's SAY_SYSTEM -- both
imported, so those patchers' own dry runs stay the judges of their nodes.

Known limit, stated: in the TOOLED tier any tool this turn licenses any
tool-shaped verb. Matching verb to tool is a later refinement if it is ever
needed.

HONEST LIMIT. The outage path cannot be fired on demand while the wallet has
money -- the same limit sayagain.py records for the rescue. It ships wired,
read back, and with its expressions unit-tested in Node against the corpus.
The next empty-wallet morning is its first live run, and the team note is the
tell.

Idempotent. Running it twice reports nothing to do.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_untemplate as U  # noqa: E402
import n8n_handover as H  # noqa: E402
import n8n_whatsapp_retry as R  # noqa: E402
import n8n_whatsapp_sayagain as S  # noqa: E402
from n8n_whatsapp_handover import execute_node  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-27sep-before-outage.json")
PLACEHOLDER = "REPLACE_WITH_N8N_WEBHOOK_SECRET"

AGENT = "Answer the resident"
WRITER = "Could not answer"
GATE = "Outage reply usable?"
NOTE = "Tell the team the bot is down"
RESCUE = "Say it again"
RESCUE_GATE = "Second try usable?"

NEED = (AGENT, RESCUE, RESCUE_GATE, "Reply usable?", "Try again", "Open it anyway",
        "OpenRouter", "Type for a moment", "Log reply", "Sort")

# Grid cells (240 x 60) on the empty rows under the whole flow. The note is the
# HIGHER of the two branches off the error output: executionOrder v1 runs the
# top branch first, so the team hears even if the writer then fails.
NOTE_POS, WRITER_POS, GATE_POS = [1200, 900], [1200, 1020], [1440, 1020]

# --------------------------------------------------------------------------
# The deed verbs. Hebrew has no \w, so no \b: a word starts after a space or
# punctuation (quotes written as \u escapes, so no literal quote character can
# end an expression early), may carry one prefix letter -- ו and, ש that,
# כ as, ה the -- and ends at the same set or the end of the text. The group
# holding the verb is always group 2.
# --------------------------------------------------------------------------
# The three quote marks go into the JS as unicode escapes, built with
# chr(92), so no literal quote can end an n8n expression early and no tool
# in the chain can decode them on the way into this file (27 Sep: one did).
_BS = chr(92)
_Q = _BS + "u0022" + _BS + "u0027" + _BS + "u05f3"
_B = "(^|[" + _BS + "s,.!?:;()" + _Q + "])[ושכה]?"
_E = "(?=[" + _BS + "s,.!?:;()" + _Q + "]|$)"
NEVER_VERBS = "החלפתי|תיקנתי|סידרתי|ניקיתי|הזמנתי"
TOOLED_VERBS = ("בדקתי|בדקנו|שלחתי|שלחנו|פתחתי|פתחנו|טיפלתי|טיפלנו|"
                "החלפנו|תיקנו|סידרנו|ניקינו|הזמנו|"
                "הוחלף|הוחלפה|הוחלפו|תוקן|תוקנה|תוקנו|טופל|טופלה|טופלו|"
                "סודר|סודרה|סודרו|נוקה|נוקו|הוזמן|הוזמנה|הוזמנו|"
                "נשלח|נשלחה|נשלחו")
NEVER = "/" + _B + "(" + NEVER_VERBS + ")" + _E + "/"
TOOLED = "/" + _B + "(" + TOOLED_VERBS + ")" + _E + "/"
TOOLED_ALL = TOOLED + "g"          # a fresh literal per evaluation: lastIndex starts at 0
REF = r"/\d{3}-\d{3,6}-\d{2}/"
# The rescue's one real deed: the stub ticket, said with its number.
RESCUE_OK = "['פתחתי','פתחנו','טיפלתי','טיפלנו']"


def _cond(cid, expr):
    return {"id": cid, "leftValue": expr, "rightValue": "",
            "operator": {"type": "boolean", "operation": "true", "singleValue": True}}


# `}}` anywhere inside ends an n8n expression, so braces never touch.
REPLY_DEEDS = _cond("deeds", (
    "={{ (() => { const t = String($json.output || ''); "
    "if (" + NEVER + ".test(t)) return false; "
    "if (!" + TOOLED + ".test(t)) return true; "
    "let n = 0; try { n = ($json.intermediateSteps || []).length; } catch (e) { n = 0; } "
    "return n > 0; })() }}"))

RESCUE_DEEDS = _cond("deeds", (
    "={{ (() => { const t = String($json.output || ''); "
    "if (" + NEVER + ".test(t)) return false; "
    "const ref = " + REF + ".test(t); const ok = " + RESCUE_OK + "; "
    "const re = " + TOOLED_ALL + "; let m; "
    "while ((m = re.exec(t)) !== null) { if (!(ref && ok.indexOf(m[2]) !== -1)) return false; } "
    "return true; })() }}"))

GATE_CONDS = [
    _cond("words", r"={{ String($json.output || '').trim().split(/\s+/).filter(Boolean).length >= 2 }}"),
    _cond("nolink", r"={{ !/https?:\/\//.test(String($json.output || '')) }}"),
    _cond("noref", "={{ !" + REF + ".test(String($json.output || '')) }}"),
    _cond("deeds", ("={{ (() => { const t = String($json.output || ''); "
                    "return !" + NEVER + ".test(t) && !" + TOOLED + ".test(t); })() }}")),
]

# --------------------------------------------------------------------------
# The writer. It is told a message could not be handled and nothing else: the
# resident's words are withheld on purpose, and so is the error text -- an
# English "Payment required" in front of a model is one sentence away from
# telling a resident there is a problem with THEIR payment.
# --------------------------------------------------------------------------
WRITER_SYSTEM = (
    "אתה מיכאל מהומי'ז, ואתה כותב לדייר בוואטסאפ בעברית. על עצמך אתה מדבר בלשון זכר, "
    # 1 Oct: singular, in words that fit both; it sees no message at all
    # (firstword.py's SYSTEM says why).
    "ואל הדייר אתה פונה ביחיד, במילים שמתאימות לגבר ולאישה כאחד, כמו \"לך\" ו\"שלך\".\n"
    "המערכת שמטפלת בפניות לא זמינה כרגע, ולכן ההודעה האחרונה שלו לא טופלה. אתה לא רואה "
    "אותה, לא יודע מה כתוב בה ולא עונה עליה.\n"
    "אתה לא בודק, לא פותח, לא מתקן, לא מחליף ולא שולח כלום, ולא אומר שעשית משהו כזה. "
    "אין מספר קריאה ואין קישור, ואתה לא מזכיר אותם.\n"
    "מה שאתה כותב, במשפט אחד או שניים ובמילים שלך: שיש אצלנו כרגע תקלה טכנית, שההודעה "
    "שלו הגיעה אלינו ושהצוות שלנו יודע עליה. בלי להבטיח מי יחזור אליו ומתי, ובלי לשאול "
    "במה עוד אפשר לעזור, כי כרגע אי אפשר.\n"
    "בלי שלום, בלי היי ובלי להציג את עצמך. בלי markdown, בלי כוכביות ובלי סוגריים. "
    "אין נוסח קבוע: תכתוב את זה במילים שלך."
)
WRITER_TEXT = "[המערכת לא הצליחה לטפל בהודעה האחרונה של הדייר. תכתוב לו עכשיו את ההודעה על התקלה.]"

SORT = "$('Sort').first().json"
# The staff DO get the resident's words and the error: they are the ones who act.
NOTE_VALUES = {
    "conv_id": "={{ %s.conv_id }}" % SORT,
    "phone": "={{ %s.to }}" % SORT,
    "reason": "system_error",
    "department": "",
    "description": (
        "={{ 'הבוט לא הצליח לענות לדייר בגלל תקלה טכנית אצלנו (מהמערכת: ' + "
        "String(($json.error && $json.error.message) || $json.error || 'לא ידוע').slice(0, 160) + "
        "'). הדייר כתב: ' + String($json.text || $json.in_text || '').slice(0, 400) }}"),
    "source": "outage",
    "mode": "new",
    "now_override": "",
}


def wanted_nodes(sub_id):
    writer = {
        "id": "cw-outage-writer", "name": WRITER,
        "type": "@n8n/n8n-nodes-langchain.agent", "typeVersion": 3,
        "position": list(WRITER_POS),
        "parameters": {"promptType": "define", "text": WRITER_TEXT,
                       "options": {"systemMessage": WRITER_SYSTEM}},
        # A fully dead model must not stop the execution: the item goes on
        # with no `output`, the gate counts no words, nothing is sent.
        "onError": "continueRegularOutput",
    }
    gate = {
        "id": "cw-outage-gate", "name": GATE,
        "type": "n8n-nodes-base.if", "typeVersion": 2,
        "position": list(GATE_POS),
        "parameters": {"conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
            "conditions": [dict(c) for c in GATE_CONDS],
            "combinator": "and"}, "options": {}},
    }
    note = execute_node("cw-outage-note", NOTE, NOTE_POS, dict(NOTE_VALUES), wait=False)
    note = json.loads(json.dumps(note, ensure_ascii=False).replace("__SUB_ID__", sub_id))
    return [note, writer, gate]


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


def same(a, b):
    return (json.dumps(a, sort_keys=True, ensure_ascii=False)
            == json.dumps(b, sort_keys=True, ensure_ascii=False))


def link(node):
    return {"node": node, "type": "main", "index": 0}


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    # The guard first, like every sibling: this ships no hashed text, but it
    # ships alongside a prompt change, and a live edit made while the repo's
    # prompt has moved without its epoch is how the 1 Sep buffers happened.
    W.check_memory_epoch(prompt=W.system_prompt(), inject=U.AGENT_NEW, tools=W.tools_text())

    sub = H.find()
    if sub is None or not sub.get("active"):
        sys.exit("The sub-workflow %r must exist and be published." % H.WF_NAME)
    live_sub = W.api("GET", "/api/v1/workflows/%s" % sub["id"])
    decide = next((n for n in live_sub["nodes"] if n["name"] == "Decide the routing"), None)
    if decide is None or "system_error:" not in (decide["parameters"].get("jsCode") or ""):
        sys.exit("The live sub-workflow has no Hebrew label for system_error yet, so the "
                 "staff note would print the English key: "
                 "python scripts/n8n_handover.py --apply --publish first.")

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in NEED:
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    # The error output must be what this script expects: the rescue alone (as
    # sayagain.py left it), or already this script's two nodes. Anything else
    # is a change nobody here has read.
    err = ((conns.get(AGENT) or {}).get("main") or [[], []])
    err_now = sorted(t.get("node") for t in (err[1] if len(err) > 1 else []))
    if err_now not in ([RESCUE], sorted([NOTE, WRITER])):
        sys.exit("REFUSING: %s's error output goes to %s, which this script does not know."
                 % (AGENT, err_now))

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))

    before_layout = layout_complaints(nodes)
    changes = []

    # 1. the three outage nodes
    for want in wanted_nodes(sub["id"]):
        have = by.get(want["name"])
        if have is None:
            nodes.append(want)
            by[want["name"]] = want
            changes.append("add node %r" % want["name"])
            continue
        for field in ("parameters", "onError", "position"):
            if field in want and not same(have.get(field), want[field]):
                have[field] = want[field]
                changes.append("update %r %s" % (want["name"], field))

    # 2. wiring: the error output to the note and the writer, never the rescue
    want_err = [link(NOTE), link(WRITER)]
    main_out = conns.setdefault(AGENT, {}).setdefault("main", [])
    while len(main_out) < 2:
        main_out.append([])
    if sorted(t["node"] for t in main_out[1]) != sorted([NOTE, WRITER]):
        main_out[1] = want_err
        changes.append("%s (error) -> %s + %s (was %s)" % (AGENT, NOTE, WRITER, RESCUE))
    if conns.get(WRITER) != {"main": [[link(GATE)]]}:
        conns[WRITER] = {"main": [[link(GATE)]]}
        changes.append("%s -> %s" % (WRITER, GATE))
    want_gate = {"main": [[link("Type for a moment"), link("Log reply")]]}
    if conns.get(GATE) != want_gate:
        conns[GATE] = want_gate
        changes.append("%s -> the send path, true branch only" % GATE)
    lm = conns.setdefault("OpenRouter", {}).setdefault("ai_languageModel", [[]])
    if not any(d.get("node") == WRITER for d in lm[0]):
        lm[0].append({"node": WRITER, "type": "ai_languageModel", "index": 0})
        changes.append("OpenRouter also drives %s" % WRITER)

    # 3. the deeds guard, by id, on both existing gates
    for node, guard in (("Reply usable?", REPLY_DEEDS), (RESCUE_GATE, RESCUE_DEEDS)):
        cond = by[node]["parameters"]["conditions"]["conditions"]
        have = next((c for c in cond if c.get("id") == "deeds"), None)
        if have is None:
            cond.append(dict(guard))
            changes.append("%s: `deeds` guard added" % node)
        elif have.get("leftValue") != guard["leftValue"]:
            have["leftValue"] = guard["leftValue"]
            changes.append("%s: `deeds` guard updated" % node)

    # 4. the two texts whose source of truth is another script
    opts = by[RESCUE]["parameters"].setdefault("options", {})
    if opts.get("systemMessage") != S.SAY_SYSTEM:
        opts["systemMessage"] = S.SAY_SYSTEM
        changes.append("%s: system message synced from sayagain.SAY_SYSTEM "
                       "(reports the stub ticket, nothing else)" % RESCUE)
    tp = by["Try again"]["parameters"]
    if tp.get("jsonOutput") != R.TRY_JSON:
        tp["jsonOutput"] = R.TRY_JSON
        changes.append("Try again: note synced from retry.RETRY_NOTE (names the deeds guard)")

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("sub      : %s  (%s)" % (sub["name"], sub["id"]))
    print("nodes    : %d" % len(nodes))
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

    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": nodes, "connections": conns,
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    bb = {n["name"]: n for n in back["nodes"]}
    print("\nwritten: %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  %s error -> %s" % (AGENT, [t["node"] for t in back["connections"][AGENT]["main"][1]]))
    for node in ("Reply usable?", RESCUE_GATE, GATE):
        ids = [c.get("id") for c in bb[node]["parameters"]["conditions"]["conditions"]]
        print("  %-22s conditions %s" % (node, ids))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
