# -*- coding: utf-8 -*-
"""Greet back once, never twice; and send back an echo or a clerk's preamble.

    python scripts/n8n_whatsapp_manners.py            # dry run
    python scripts/n8n_whatsapp_manners.py --apply    # write it
    python scripts/n8n_whatsapp_manners.py --restore  # put the 27 Sep snapshot back

WHY, 27 Sep. The epoch-67 fix held -- no invented repair -- and the next reply
to the owner's tester was: "צהריים טובים, מיכאל מהומי'ז. אני מבין שיש תקלה
בתאורה… כדי שאוכל לפתוח קריאת שירות ולטפל בזה, אצטרך לדעת באיזה בניין מדובר."
A second greeting and re-introduction in a conversation already greeted, the
"I understand that…" echo, and the clerk's "so that I can…, I'll need…" -- all
three already asked away by the owner. Owner: *"ok lets plan this thoroughly
before making the changes"*, then, for greetings, the rule confirmed against
examples: **"greet back once, never twice"**.

  first reply in a conversation               hour greeting + name
  resident greets mid-conversation            exactly one greeting back, no name
  resident doesn't greet, mid-conversation    none
  right after the system's menu greeting,     none (the name is kept after the menu)
    or after a first-word ack that greeted
  anywhere                                    never two greetings in one message

1. THE GREETING FILTER, IN SEND. Deterministic, because no prompt clause can
   be: the bot's memory is empty after every epoch bump and n8n restart while
   Sort's `greeted` survives, and on 27 Sep four prompt clauses said "greet"
   against one inject line that said "don't". It sits between Send's own
   clean-up and `const body`, computes `c` from `t`, and changes only
   `content: t` -> `content: c`, so the menu rules still read the unstripped
   text. It can only REMOVE: a leading greeting beyond the ones allowed, and a
   leading self-introduction where the name is not wanted. It never empties a
   message, never breaks "ערב טוב גם לכם" or "בוקר טוב ותודה", and leaves the
   text byte-identical when it removes nothing.

   "Right after the menu" is read two ways: Sort's `last_bot` (30 minutes, one
   message) and the newest OUTBOUND row in `Anything newer?` -- the messages
   table, which every execution sees, so a tap that arrives while the menu's
   own run is still saving staticData is not mistaken for a first contact.

   The ack only counts if `Say it now` actually sent it, and only as far as it
   went: an ack that greeted takes the answer's greeting, one that named takes
   the answer's name. `Worth a word?` now greets back itself when the resident
   opened with a greeting (n8n_whatsapp_firstword.py), so the greeting lands
   in the first message they read.

2. `echo` AND `clerk` ON `Reply usable?`, first pass only -- the same
   `$runIndex > 0 ||` shape as `plural` and `opener`, so a stubborn second try
   goes out rather than becoming a stub ticket. Owner: send those back.
   BOTH ARE EXEMPT WHEN THE TURN DID WORK. The second pass is rebuilt from
   `Still the last word?` and sees none of the first pass's tool results, so
   sending back a reply after open_request opened, notify_team noted or
   get_payment_link returned a link risks a second ticket, a lost note, or a
   delivered link replaced by a stub ticket (review, 27 Sep). A refused
   open_request (`opened:false`) wrote nothing and does not count -- which is
   exactly today's reply. The payment link's two-beat `§§§` is exempt too.

3. `Try again`'s note, from retry.py's RETRY_NOTE, now names the two reasons
   and the positive fix -- ask what is missing in one short question.

Not epoch-hashed: Send, the guards and the note are workflow code. The prompt,
inject and get_request_status text of the same change ship by teamnote.py.

The greeting-word test is n8n_whatsapp_untemplate.RESIDENT_HELLO, one copy for
the inject, `Worth a word?` and this filter.

Idempotent. Running it twice reports nothing to do. A later version of the
filter replaces this one by its marker.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_untemplate as U  # noqa: E402
import n8n_whatsapp_retry as R  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-27sep-before-manners.json")
PLACEHOLDER = "REPLACE_WITH_N8N_WEBHOOK_SECRET"
NEED = ("Send", "Reply usable?", "Try again", "Sort", "Carry on", "Anything newer?",
        "Say it now", "Answer the resident")

VS = chr(0xFE0F)                       # emoji variation selector, built, never typed
EMOJI = r"\p{Extended_Pictographic}" + VS

# ---------------------------------------------------------------------------
# 1. The greeting filter: one JS statement per string, joined with spaces.
#    Every closing brace that could meet another has a space before it: n8n
#    ends an expression at the first `}}`. The apostrophe of הומי'ז lives only
#    inside a regex literal, never inside a '…' string.
# ---------------------------------------------------------------------------
# A plain string, not a JS comment: nothing else in this workflow puts a comment
# inside an expression, and this is not the change to find out how n8n takes one.
MARK = "const mv = 'manners v1';"
BOT_HELLO = (r"/^(שלום רב|שלום|היי|הי|אהלן|בוקר טוב|צהריים טובים|ערב טוב|לילה טוב|"
             r"שבוע טוב|שבת שלום|חג שמח|יום טוב)( לכם| לך| לכולם)?(?=[\s,.!:;]|$)[\s,.!:;"
             + EMOJI + r"]*/u")
NAME = (r"/^((כאן|אני|זה)\s+)?מיכאל(\s+מהומי['׳’]?ז)?(\s+כאן)?(?=[\s,.!:;]|$)[\s,.!:;"
        + EMOJI + r"]*/u")
LEAD = r"/^[\s" + EMOJI + r"]+/u"

FILTER = " ".join([
    "const c = (() => { " + MARK,
    "const S = $('Sort').first().json;",
    "if (S.greeting === true) return t;",
    "const HELLO = " + BOT_HELLO + ";",
    "const NAME = " + NAME + ";",
    "let lastOut = '';",
    "try { const rows = $('Anything newer?').all(); for (const r of rows) "
    "{ if (r.json && r.json.direction === 'outbound') { lastOut = String(r.json.body || ''); break; } } "
    "} catch (e) { lastOut = ''; }",
    "const afterMenu = /במה אפשר לעזור/.test(String(S.last_bot || '')) "
    "|| lastOut.indexOf('👋 במה אפשר לעזור?') !== -1;",
    "let ackSent = false; try { ackSent = $('Say it now').all().length > 0; } catch (e) { ackSent = false; }",
    "const ack = ackSent ? String(acked || '').replace(" + LEAD + ", '') : '';",
    "const ackGreeted = ack !== '' && HELLO.test(ack);",
    "const ackNamed = ack !== '' && /מיכאל/.test(ack);",
    "const mid = S.greeted === true;",
    "let said = ''; try { said = String($('Carry on').first().json.text || ''); } catch (e) { said = ''; }",
    "if (!said) said = String(S.text || '');",
    "said = said" + U.SAID_NORM + ";",
    "const theyGreeted = " + U.RESIDENT_HELLO + ".test(said);",
    "const allowed = (afterMenu || ackGreeted) ? 0 : ((!mid || theyGreeted) ? 1 : 0);",
    "const keepName = afterMenu || (!mid && !ackNamed);",
    "let head = ''; let x = t.replace(" + LEAD + ", ''); let kept = 0; let cut = false;",
    "for (let i = 0; i < 3; i++) { const m = x.match(HELLO); if (!m) break; "
    "if (kept < allowed) { head += m[0]; kept++; } else { cut = true; } x = x.slice(m[0].length); }",
    "if (!keepName) { const n = x.match(NAME); if (n) { x = x.slice(n[0].length); cut = true; } }",
    "if (!cut) return t;",
    "const rest = x.trim();",
    "if (rest.split(/\\s+/).filter(Boolean).length < 2 || /^(גם|ו[א-ת])/.test(rest)) return t;",
    "return (head + rest).trim(); })();",
])
# The one-word test above needs a single backslash in the JS: `\\s` in this
# plain Python string is `\s` in the expression.

SEND_OLD = (".replace(/\\s{2,}/g, ' ').trim(); "
            "const body = { content: t, message_type: 'outgoing' };")
SEND_NEW = (".replace(/\\s{2,}/g, ' ').trim(); " + FILTER + " "
            "const body = { content: c, message_type: 'outgoing' };")
BLOCK_START = "const c = (() => { const mv = 'manners v"
BLOCK_END = " const body = { content: c, message_type: 'outgoing' };"

# ---------------------------------------------------------------------------
# 2. echo and clerk, first pass only, exempt when the turn did work.
# ---------------------------------------------------------------------------
WORKED = ("const t = String($json.output || ''); const steps = $json.intermediateSteps || []; "
          "const worked = t.indexOf('§§§') !== -1 || steps.some(s => { const k = ((s.action || {}).tool) || ''; "
          "return k === 'notify_team' || k === 'get_payment_link' || (k === 'open_request' "
          "&& !/opened\\W{1,6}false/.test(String(s.observation || ''))); }); if (worked) return true;")


def _cond(cid, expr):
    return {"id": cid, "leftValue": expr, "rightValue": "",
            "operator": {"type": "boolean", "operation": "true", "singleValue": True}}


ECHO_GUARD = _cond("echo", (
    "={{ $runIndex > 0 || (() => { " + WORKED + " "
    "return !/(^|[.!?,:]\\s*)(אני מבין|אני מבינה|הבנתי|שמעתי)\\s+ש/.test(t); })() }}"))
CLERK_GUARD = _cond("clerk", (
    "={{ $runIndex > 0 || (() => { " + WORKED + " "
    "return !/כדי שאוכל|אצטרך/.test(t); })() }}"))


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


def other_old_anchors():
    """Every *_OLD string any other WhatsApp patcher might replace. The filter
    must contain none of them, or that patcher's next run would rewrite part of
    it as if it were the thing it once replaced."""
    import importlib
    found = {}
    here = os.path.dirname(os.path.abspath(__file__))
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
            if k.endswith("_OLD") and isinstance(v, str) and len(v) >= 12:
                found["%s.%s" % (fn[:-3], k)] = v
    return found


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

    # 1. Send: the filter, three states
    body = by["Send"]["parameters"].get("jsonBody") or ""
    if SEND_NEW in body:
        pass
    elif BLOCK_START in body:
        a = body.index(BLOCK_START)
        z = body.index(BLOCK_END, a) + len(BLOCK_END)
        by["Send"]["parameters"]["jsonBody"] = body[:a] + FILTER + BLOCK_END + body[z:]
        changes.append("Send: greeting filter replaced with %s" % MARK)
    else:
        if body.count(SEND_OLD) != 1:
            sys.exit("REFUSING: Send.jsonBody does not carry the clean-up/body junction "
                     "this script knows (found %d). Read the live body first." % body.count(SEND_OLD))
        by["Send"]["parameters"]["jsonBody"] = body.replace(SEND_OLD, SEND_NEW, 1)
        changes.append("Send: greeting filter in (greet back once, never twice); "
                       "content: t -> content: c")
    new_body = by["Send"]["parameters"]["jsonBody"]
    if new_body.count("}}") != 1:
        sys.exit("REFUSING: the new Send body has %d '}}' -- n8n would end the expression "
                 "early." % new_body.count("}}"))
    clash = [k for k, v in other_old_anchors().items() if v in FILTER]
    if clash:
        sys.exit("REFUSING: the filter contains other patchers' OLD anchors: %s" % clash)

    # 2. echo and clerk, by id
    cond = by["Reply usable?"]["parameters"]["conditions"]["conditions"]
    for g in (ECHO_GUARD, CLERK_GUARD):
        have = next((c for c in cond if c.get("id") == g["id"]), None)
        if have is None:
            cond.append(dict(g))
            changes.append("Reply usable?: `%s` guard added (first pass, no-work turns only)" % g["id"])
        elif have.get("leftValue") != g["leftValue"]:
            have["leftValue"] = g["leftValue"]
            changes.append("Reply usable?: `%s` guard updated" % g["id"])

    # 3. Try again's note, from retry.py
    tp = by["Try again"]["parameters"]
    if tp.get("jsonOutput") != R.TRY_JSON:
        tp["jsonOutput"] = R.TRY_JSON
        changes.append("Try again: note synced from retry.RETRY_NOTE (names echo and clerk)")

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
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
    print("  Send carries %s: %s; content: c: %s" % (
        MARK, MARK in bb["Send"]["parameters"]["jsonBody"],
        "content: c, message_type" in bb["Send"]["parameters"]["jsonBody"]))
    print("  Reply usable? conditions %s" % [c.get("id") for c in bb["Reply usable?"]["parameters"]["conditions"]["conditions"]])
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
