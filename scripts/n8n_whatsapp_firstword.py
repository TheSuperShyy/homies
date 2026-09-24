# -*- coding: utf-8 -*-
"""The "one moment, I'm checking" goes out BEFORE the checking, not after it.

    python scripts/n8n_whatsapp_firstword.py            # dry run
    python scripts/n8n_whatsapp_firstword.py --apply    # write it

WHY, and it is a timing bug rather than a wording one. Epoch 57 gave a reply
that did real work two messages, split by §§§ and posted ~2s apart. The owner
kept reporting *"it sends at the same time"*, and execution 58640 says why:

    resident writes            09:37:18
    Send (first message)       09:37:30   <- 12 seconds of silence
    Send the rest              09:37:32   <- the 2s gap, working exactly

Both halves are written by the same completion, so neither can leave until the
model has finished thinking AND the tool has returned. The acknowledgement
therefore lands at the moment the answer is already in hand, and a resident
sees twelve seconds of nothing followed by two messages at once. The gap was
never the problem; its position was.

So the acknowledgement moves in front of the work. `Worth a word?` is a small
agent that runs on the inbound message and does one thing: decides whether the
resident wants a PAYMENT LINK, and if so writes ONE short sentence in Michael's
voice. Anything else returns NONE and nothing is sent.

NARROWED TO THE PAYMENT LINK ON 24 SEP, and the owner's own screenshot is the
argument. "the lights are out in the hallway" came back as "I understand you,
I'm checking it now" followed by a request for the building and flat -- it was
not checking anything, it was about to ask a question, so the sentence was
simply untrue. The payment link is the one case where the bot really does go
away and look something up (OXS, ~2.7s of the 12), which is what makes the wait
worth narrating. Owner: *"can we make that type of feature specific only for the
getting of payment link only."*

WHY AN AGENT AND NOT A CHAIN: `Say it again` is already an agent v3 with a
model and no tools, so that shape is proven on this instance. A node type n8n
has never run here is not something to discover in production.

IT FAILS OPEN, and that is the whole reason it is safe to put in the main path.
`onError: continueRegularOutput` means a model outage, a rate limit or a
timeout costs the acknowledgement and nothing else: `A word first?` sees no
output, takes the false branch, and the resident gets their answer exactly as
before. A node that can silence the bot has no business on this path.

`Carry on` rebuilds the item the agent needs. `Answer the resident` reads
$json.text, .photo, .attachment, .greeted, .tap_now, .retry_note, .last_bot,
and an agent node in between replaces $json with its own output -- so the
original is restored from `Still the last word?` and carries one new field,
`acked`, which the inject turns into a line telling the model what the resident
has already been told. Without it the model writes its own acknowledgement too
and the resident gets three messages.

THE RETRY PATH IS DELIBERATELY UNTOUCHED. `Try again` feeds the agent directly,
so a second attempt never acknowledges twice.

Idempotent. Surgical. `n8n_whatsapp.py --apply` remains the wrong way to ship.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n8n_whatsapp as W  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"

# A clear band. The first placement put all four on top of existing nodes
# (Menu?, OpenRouter, Conversation so far, Open it anyway) and n8n_layout.py
# named every collision; this row is empty from x=1200 to x=1920 at y=700.
POS = {"Worth a word?": [1200, 700], "A word first?": [1440, 700],
       "Say it now": [1680, 700], "Carry on": [1920, 700]}

# --------------------------------------------------------------------------
# 1. Worth a word? -- decide, and write the sentence or NONE.
# --------------------------------------------------------------------------
SYSTEM = (
    "אתה מיכאל, נציג השירות של הומי'ז, חברת ניהול בתים משותפים, בצ'אט וואטסאפ "
    "עם דייר. על עצמך אתה מדבר בלשון זכר, ואל הדייר אתה פונה בלשון רבים.\n"
    "\n"
    "לפניך ההודעה האחרונה שהדייר שלח. יש לך תפקיד אחד ויחיד, וצר מאוד: להחליט "
    "אם הדייר רוצה עכשיו קישור לתשלום. רק זה ושום דבר אחר.\n"
    "\n"
    "זה כן: מי שמבקש קישור לתשלום, מי שאומר שהוא רוצה לשלם או שואל איך ואיפה "
    "משלמים, ומי שאומר שלא קיבל קישור או שלא קיבל כלום בנוגע לתשלום.\n"
    "\n"
    "אם כן: כתוב הודעה אחת קצרה בעברית, במילים שלך, שאומרת לו שהבנת מה הוא צריך "
    "ושאתה בודק את זה עכשיו. משפט אחד או שניים, חם וטבעי. אין בה שום תוצאה: לא "
    "סכום, לא מספר, לא קישור, לא מה מצאת, ולא הבטחה תוך כמה זמן. היא יוצאת לפני "
    "הבדיקה ולא אחריה, אז היא לא יכולה לדעת כלום.\n"
    "\n"
    "זה לא, ועל כל אלה מחזירים NONE: תקלה מכל סוג — נזילה, תאורה, מעלית, חדר "
    "מדרגות — בקשה לפתוח קריאת שירות, שאלה על מצב של קריאה קיימת, שאלה על "
    "היתרה או על החוב, שאלה על השירותים של הומי'ז, בקשה לדבר עם נציג, ברכה, "
    "תודה, פרידה, שיחת חולין, או בקשה לפרט שחסר. גם כשברור לך שהמענה יצריך "
    "עבודה או בדיקה, זה עדיין NONE: זה לא התפקיד שלך כאן.\n"
    "\n"
    "כשמחזירים NONE מחזירים בדיוק את המילה NONE, באנגלית, ותו לא. לא משפט, "
    "לא הסבר, לא סימן פיסוק.\n"
    "\n"
    "אתה לא עונה כאן לדייר ולא פותר לו כלום. מישהו אחר עושה את זה מיד אחריך."
)

# `first` decides whether this sentence also carries the greeting and the name:
# it is the resident's first message of the conversation, so the system's own
# greeting has not run and nobody has introduced themselves yet.
TEXT = (
    "={{ (() => { const HH = Number(new Intl.DateTimeFormat('en-GB', "
    "{ hour: '2-digit', hourCycle: 'h23', timeZone: 'Asia/Jerusalem' })"
    ".format(new Date())); const hello = HH < 5 ? 'שלום' : HH < 12 ? 'בוקר טוב' "
    ": HH < 17 ? 'צהריים טובים' : 'ערב טוב'; const first = $json.greeted !== true; "
    "const note = first ? ('[זאת הפנייה הראשונה שלו אליך. אם אתה כותב הודעה, "
    "פתח אותה ב\"' + hello + '\" והצג את עצמך כמיכאל מהומי\\'ז, במשפט אחד.]') : "
    "'[אתם כבר באמצע שיחה. בלי ברכה ובלי להציג את עצמך שוב.]'; "
    "return note + String.fromCharCode(10) + String($json.text || ''); })() }}"
)

# --------------------------------------------------------------------------
# 2. A word first? -- did it write one, and is it sane.
# --------------------------------------------------------------------------
# The length cap is the runaway guard: this node is allowed to send WITHOUT the
# model having seen the prompt's rules about what the bot may say, so anything
# that is not a short sentence is treated as a malfunction and dropped.
WORD_EXPR = (
    "={{ (() => { const t = String($json.output || '').trim(); "
    "return t.length > 0 && t.length < 320 && t.toUpperCase() !== 'NONE' "
    "&& t.indexOf('http') === -1; })() }}"
)

SAY_BODY = (
    "={{ JSON.stringify({ content: String($json.output || '')"
    ".replace(/\\[[^\\]]*\\]/g, ' ').replace(/\\s{2,}/g, ' ').trim(), "
    "message_type: 'outgoing' }) }}"
)

# --------------------------------------------------------------------------
# 3. Carry on -- the agent's item back, plus what the resident was just told.
# --------------------------------------------------------------------------
CARRY = (
    "={{ JSON.stringify(Object.assign({ }, "
    "$('Still the last word?').first().json, { acked: "
    "String($('Worth a word?').first().json.output || '').trim().toUpperCase() "
    "=== 'NONE' ? '' : String($('Worth a word?').first().json.output || '')"
    ".trim() })) }}"
)

# --------------------------------------------------------------------------
# 4. The inject gains one line, so the model does not acknowledge twice.
# --------------------------------------------------------------------------
INJECT_ANCHOR = "+ ($json.retry_note ? ' ' + $json.retry_note : '') "
INJECT_NEW = (
    INJECT_ANCHOR
    + "+ ($json.acked ? ' [הודעה קצרה כבר יצאה אליו ממך ברגע זה: \"' + "
      "$json.acked + '\". היא כבר אצלו. אל תחזור עליה, אל תפתח שוב בזה שאתה "
      "בודק, ואם היא כבר בירכה והציגה אותך אל תעשה את זה שוב. ההודעה שאתה כותב "
      "עכשיו היא התשובה עצמה, הודעה אחת, בלי §§§.]' : '') "
)


def guard(gid, expr):
    return {"id": gid, "leftValue": expr, "rightValue": "",
            "operator": {"type": "boolean", "operation": "true", "singleValue": True}}


def main():
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in ("Still the last word?", "Answer the resident", "Send", "OpenRouter"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    changes = []
    send = by["Send"]

    def want_node(name, spec):
        have = by.get(name)
        if have is None:
            spec["position"] = POS[name]
            nodes.append(spec)
            changes.append("%s: new node" % name)
            return
        for k, v in spec.items():
            if k in ("id", "name", "position"):
                continue
            if have.get(k) != v:
                have[k] = v
                changes.append("%s: %s updated" % (name, k))
        if have.get("position") != POS[name]:
            have["position"] = POS[name]
            changes.append("%s: moved to %s" % (name, POS[name]))

    want_node("Worth a word?", {
        "id": "worth_a_word", "name": "Worth a word?",
        "type": "@n8n/n8n-nodes-langchain.agent", "typeVersion": 3,
        # A model outage must cost the nicety, never the reply.
        "onError": "continueRegularOutput",
        "parameters": {"promptType": "define", "text": TEXT,
                       "options": {"systemMessage": SYSTEM}},
    })
    want_node("A word first?", {
        "id": "a_word_first", "name": "A word first?",
        "type": "n8n-nodes-base.if", "typeVersion": 2,
        "parameters": {"conditions": {
            "options": {"caseSensitive": True, "leftValue": "",
                        "typeValidation": "loose"},
            "conditions": [guard("word", WORD_EXPR)], "combinator": "and"}},
    })
    want_node("Say it now", {
        "id": "say_it_now", "name": "Say it now",
        "type": send["type"], "typeVersion": send["typeVersion"],
        "onError": "continueRegularOutput",
        "parameters": {
            "method": "POST", "url": send["parameters"]["url"],
            "authentication": send["parameters"].get("authentication"),
            "genericAuthType": send["parameters"].get("genericAuthType"),
            "sendBody": True, "specifyBody": "json", "jsonBody": SAY_BODY,
            "options": send["parameters"].get("options", {"timeout": 20000}),
        },
        "credentials": send.get("credentials", {}),
    })
    want_node("Carry on", {
        "id": "carry_on", "name": "Carry on",
        "type": "n8n-nodes-base.set", "typeVersion": 3.4,
        "parameters": {"mode": "raw", "jsonOutput": CARRY, "options": {}},
    })

    # --- the inject ---------------------------------------------------------
    agent = by["Answer the resident"]
    txt = agent["parameters"].get("text") or ""
    if "$json.acked" not in txt:
        if INJECT_ANCHOR not in txt:
            sys.exit("Anchor missing in the live inject -- refusing to guess:\n"
                     "  %s" % INJECT_ANCHOR)
        agent["parameters"]["text"] = txt.replace(INJECT_ANCHOR, INJECT_NEW, 1)
        changes.append("Answer the resident: the inject names what was already said")

    # --- wiring -------------------------------------------------------------
    want_conns = {
        "Still the last word?": {"main": [[{"node": "Worth a word?", "type": "main", "index": 0}]]},
        "Worth a word?": {"main": [[{"node": "A word first?", "type": "main", "index": 0}]]},
        "A word first?": {"main": [
            [{"node": "Say it now", "type": "main", "index": 0}],
            [{"node": "Carry on", "type": "main", "index": 0}],
        ]},
        "Say it now": {"main": [[{"node": "Carry on", "type": "main", "index": 0}]]},
        "Carry on": {"main": [[{"node": "Answer the resident", "type": "main", "index": 0}]]},
    }
    for name, spec in want_conns.items():
        if conns.get(name) != spec:
            conns[name] = spec
            changes.append("wiring: %s" % name)

    # The model sub-node feeds a third parent. It already feeds two, so this is
    # the shape this workflow already runs, not a new idea.
    lm = conns.get("OpenRouter", {}).get("ai_languageModel", [[]])
    row = lm[0] if lm else []
    if not any(x.get("node") == "Worth a word?" for x in row):
        row.append({"node": "Worth a word?", "type": "ai_languageModel", "index": 0})
        conns["OpenRouter"] = {"ai_languageModel": [row]}
        changes.append("wiring: OpenRouter also drives Worth a word?")

    print("workflow : %s  (%s, active=%s)"
          % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    if not changes:
        print("")
        print("Nothing to do. Live already matches.")
        return

    print("")
    print("changes:")
    for c in changes:
        print("  - %s" % c)

    if not apply:
        print("")
        print("Dry run. Re-run with --apply to write it.")
        return

    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": nodes,
        "connections": conns, "settings": live.get("settings", {}),
    })
    print("")
    print("written. Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
