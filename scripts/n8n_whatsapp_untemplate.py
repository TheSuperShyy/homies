# -*- coding: utf-8 -*-
"""Take the last fixed sentences out, and leave the intro and its menu in.

    python scripts/n8n_whatsapp_untemplate.py            # dry run
    python scripts/n8n_whatsapp_untemplate.py --apply    # write it

WHY
The owner, for the third time and flatly: *"i dont want a templated message,
only the intro one which is the menu."*

The model's replies were already free — 20 live replies on 1 Sep, zero exact
repeats, and the single word `elevator` answered four different ways. It is the
WORKFLOW that still spoke in fixed sentences, in three places that are not the
menu:

1. **The `לדבר עם נציג` tap** — one of three canned Hebrew lines, chosen at
   random, sent without the model ever seeing the tap.
2. **A photo or sticker with no caption** — one fixed line.
3. **`Hand over instead`** — two fixed lines, used when a guard throws away a
   reply. Handled by `scripts/n8n_whatsapp_sayagain.py`, not here.

WHAT STAYS, BECAUSE THE OWNER NAMED IT
`MENU.content` — `היי, כאן מיכאל מהומיז. במה אפשר לעזור?` — and the three menu
rows, sent for a bare greeting. That text is also the opener in prompt.md and
`check_greeting()` refuses to deploy if the two drift apart, so it is fixed in
two files on purpose.

THE TRAP, AND IT IS THE REASON THIS ONE WAS LEFT ALONE ON 31 AUG
`Human tap?` -> `Transfer the tap` hangs off the CANNED branch of
`Canned reply?`. Send the tap to the model and that branch stops running for it,
so the transfer silently stops firing and a resident who asked for a person
never reaches one. `Human tap?` is therefore reconnected to `Sort` itself, where
it sees every message and tests only `$json.tap === 'human'` — so the routing no
longer depends on who writes the words.

THE OTHER HALF OF THE TAP, WHICH IS EASY TO GET WRONG
`store.tapped[from]` is written on the tap and CONSUMED at the bottom of the
node, one message later, to tell the model that the message it is reading is the
answer to the tap. With the tap falling through to the same return, the flag
would be set and consumed in the same run, so the next message would see
nothing. `tapNow` guards the consume.

Idempotent. Running it twice reports nothing to do.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"

# --------------------------------------------------------------------------
# 1. The attachment reply.
# --------------------------------------------------------------------------
ATTACH_OLD = """if (!text.trim()) {
  return [{ json: {
    _reply: '', _work: false, _canned: true, _menu: false,
    to: from, conv_id: convId, lang,
    text: said("אני קורא כאן רק טקסט. אפשר לכתוב לי מה קרה?"),
    in_text: inText, msg_type: 'attachment', message_id: id,
  } }];
}"""

ATTACH_NEW = """// Answered with a fixed sentence until 1 Sep. It falls through to the model
// now, carrying a flag the agent template turns into a note that something
// arrived which the model cannot see. That note goes workflow-to-model and is
// never sent to anybody, so it is not a template.
//
// Nothing below trips on an empty string: the greeting regex is anchored and
// whole-string so '' is not a greeting, and TAP_KIND[''] is undefined.
const attachment = !text.trim();"""

# --------------------------------------------------------------------------
# 2. The three canned lines for the נציג tap.
# --------------------------------------------------------------------------
TAPPED_OLD = """const TAPPED = {
  // NO COURTESY OPENER on a tap (owner, 27 Aug evening): the greeting was
  // already said by the menu, so "בטח, אשמח לעזור" reads as starting over.
  // Straight to the substance: invite the details, say what happens with
  // them, end on the question.
  // The "open a ticket" and "status" rows had three canned variants each until
  // 31 Aug. They are gone on the owner's instruction -- a tap now reaches the
  // model, which answers it in its own words, and the tap itself is in the
  // conversation memory so the next message does not need a flag to know it
  // happened.
  // The נציג tap was the model's until 26 Aug and it fumbled it twice in one
  // evening: first a re-greeting with the menu glued on, then the bare fixed
  // line with no question. A tap is routing, and routing is the workflow's;
  // Human tap? below fires the actual transfer; the model only ever sees the
  // resident's ANSWER, flagged tapped_human.
  "לדבר עם נציג": [
    "אני מעביר אותך לצוות. כדי שמי שחוזר יגיע כבר עם ההקשר, אפשר לכתוב בכמה מילים על מה הפנייה?",
    "מעביר אותך לצוות שלנו. כדי שיחזרו מוכנים, אפשר לכתוב בכמה מילים במה מדובר?",
    "אני מעביר את זה לצוות. רק כדי שמי שחוזר ידע במה מדובר, על מה הפנייה?",
  ],
};
"""

TAPPED_NEW = """// The נציג tap held three canned Hebrew lines, picked at random, until 1 Sep.
// The owner's instruction is that the intro and its menu are the only fixed
// text in the system, so they are gone and the tap reaches the model like any
// other message. The reason it survived the 31 Aug cut was the transfer, not
// the wording: see the note on tapNow below, and Human tap? now hanging off
// Sort rather than off the canned branch.
"""

TAPOPTS_OLD = """const tapOpts = TAP_KIND[text.trim()] === 'human'
  ? TAPPED[text.trim()] : null;
// Never the same phrasing twice in a row. Pure random repeated the same
// variant three taps running in the 27 Aug test, which reads as one script;
// remembering the last pick per handset+button and stepping past it makes
// consecutive taps always differ while staying random.
let canned;
if (tapOpts) {
  store.lastVar = store.lastVar || {};
  const vkey = from + ':' + (TAP_KIND[text.trim()] || 'human');
  let pick = Math.floor(Math.random() * tapOpts.length);
  if (tapOpts.length > 1 && tapOpts[pick] === store.lastVar[vkey]) {
    pick = (pick + 1) % tapOpts.length;
  }
  canned = tapOpts[pick];
  store.lastVar[vkey] = canned;
}
if (canned) {
  // A CANNED LINE NEVER REACHES THE MODEL, so without this the agent answers
  // the fault description as though it arrived out of nowhere and offers to
  // open a call the resident has already asked for by tapping. Seen live on
  // 25 Aug: tap "פתיחת קריאת שירות", describe a leak, and get back "shall I
  // open a ticket?" — the exact re-ask the prompt exists to prevent.
  store.tapped = store.tapped || {};
  store.tapped[from] = { kind: TAP_KIND[text.trim()], at: Date.now() };
  return [{ json: {
    _reply: '', _work: false, _canned: true, _menu: false,
    to: from, conv_id: convId, lang, text: said(canned),
    tap: TAP_KIND[text.trim()] || '',
    in_text: inText, msg_type: 'interactive', message_id: id,
  } }];
}

// "לדבר עם נציג" is canned above since 26 Aug -- see the comment on TAPPED.
"""

TAPOPTS_NEW = """// A tap is still routing, and routing is still the workflow's: `tap` is carried
// out of this node on the ordinary return, and Human tap? -> Transfer the tap
// hangs off Sort itself, so the handover fires whether the words come from here
// or from the model. Sending the tap to the model WITHOUT moving Human tap?
// would have stopped requests for a person transferring, silently.
//
// store.tapped is written for the NEXT message: it is what stops the model
// answering a fault description with "shall I open a ticket?" after the
// resident already asked for one by tapping (live, 25 Aug). It is consumed at
// the bottom of this node, so on the tap's own run the consume has to be
// skipped or the flag would be spent before the answer arrives -- hence tapNow
// being read there too.
const tapNow = TAP_KIND[text.trim()] || '';
if (tapNow) {
  store.tapped = store.tapped || {};
  store.tapped[from] = { kind: tapNow, at: Date.now() };
}
"""

# --------------------------------------------------------------------------
# 3. Do not spend the tap flag on the tap's own run.
# --------------------------------------------------------------------------
CONSUME_OLD = "const lastTap = store.tapped[from];"
CONSUME_NEW = ("const lastTap = tapNow ? null : store.tapped[from];")

# --------------------------------------------------------------------------
# 4. Carry the tap and the attachment out on the ordinary return.
# --------------------------------------------------------------------------
RETURN_OLD = """  greeting: isGreeting, last_bot: lastBot,
  message_id: id,
  in_text: inText, msg_type: 'text',"""

RETURN_NEW = """  greeting: isGreeting, last_bot: lastBot,
  message_id: id,
  // `tap` is what Human tap? reads, and it now leaves the node on this return
  // rather than on a canned one. `tap_now` separates the tap itself from the
  // message that answers it, which tapped_human used to mean on its own.
  tap: tapNow, tap_now: !!tapNow, attachment,
  in_text: inText, msg_type: attachment ? 'attachment' : 'text',"""

# --------------------------------------------------------------------------
# 5. The agent template. Kept in step with n8n_whatsapp_open.py, which is where
#    it is defined; this file only pushes it.
# --------------------------------------------------------------------------
AGENT_NEW = (
    "={{ ($json.greeted ? '[אתם כבר באמצע שיחה.]' "
    ": '[זו ההודעה הראשונה בשיחה.]') "
    "+ ($json.tap_now ? ' [ההודעה הזאת היא לחיצה על כפתור, לא משהו שהדייר "
    "הקליד. הפנייה כבר הועברה לנציג על ידי המערכת, אז אל תשאל אם להעביר — "
    "תגיד לו בניסוח שלך מה קרה, ותשאל על מה הפנייה כדי שמי שחוזר אליו יגיע "
    "עם ההקשר.]' : '') "
    "+ ($json.tapped_human && !$json.tap_now ? ' [ההודעה הזאת היא התשובה של "
    "הדייר על מה הפנייה, אחרי שהיא כבר הועברה לנציג. היא נועדה לצוות שיחזור "
    "אליו.]' : '') "
    "+ ($json.attachment ? ' [הדייר שלח קובץ, תמונה או מיקום בלי טקסט. אתה "
    "לא רואה קבצים, ולכן אין לך מה לקרוא כאן.]' : '') "
    "+ ($json.last_bot ? ' [ההודעה הזאת היא תשובה למשפט ששלחה המערכת ולא "
    "אתה, ולכן אין לו זכר בזיכרון שלך: ' + $json.last_bot + ']' : '') "
    "+ String.fromCharCode(10) + $json.text }}"
)


def edit(code, old, new, label, changes):
    if new in code and old not in code:
        return code
    if old not in code:
        sys.exit("Anchor missing in the live Sort node -- refusing to guess:\n  %s"
                 % label)
    changes.append(label)
    return code.replace(old, new, 1)


def main():
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    for need in ("Sort", "Human tap?", "Transfer the tap", "Answer the resident",
                 "Canned reply?"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    changes = []
    code = by["Sort"]["parameters"]["jsCode"]
    code = edit(code, ATTACH_OLD, ATTACH_NEW,
                "Sort: a photo with no caption reaches the model instead of a "
                "fixed line", changes)
    code = edit(code, TAPPED_OLD, TAPPED_NEW,
                "Sort: drop the three canned replies for the נציג tap", changes)
    code = edit(code, TAPOPTS_OLD, TAPOPTS_NEW,
                "Sort: the נציג tap reaches the model; the handover still fires "
                "from the workflow", changes)
    code = edit(code, CONSUME_OLD, CONSUME_NEW,
                "Sort: do not spend the tap flag on the tap's own run", changes)
    code = edit(code, RETURN_OLD, RETURN_NEW,
                "Sort: carry tap / tap_now / attachment out on the model return",
                changes)
    by["Sort"]["parameters"]["jsCode"] = code

    agent = by["Answer the resident"]
    if agent["parameters"].get("text") != AGENT_NEW:
        changes.append("Answer the resident: tell the model when a message IS "
                       "the tap, when it answers one, and when a file arrived")
        agent["parameters"]["text"] = AGENT_NEW

    # --- The rewiring -------------------------------------------------------
    # Off the canned branch, onto Sort. Everything else about both nodes is
    # untouched; only who feeds Human tap? changes.
    #
    # AND IT GOES SECOND, DIRECTLY AFTER Answer Meta. n8n walks a node's
    # connections in array order, and `Send` throws when Chatwoot cannot find
    # the conversation — which aborts the run, so anything ordered after it
    # never happens. Human tap? was last under the canned branch, behind that
    # Send, and a transfer a resident asked for is not something to leave
    # downstream of a delivery that can fail. It was also unverifiable there:
    # probe_whatsapp.py talks to an invented conversation id, so every probe
    # 404s at Send and the node was never reached.
    conns = live["connections"]
    canned_out = conns["Canned reply?"]["main"][0]
    if any(d["node"] == "Human tap?" for d in canned_out):
        conns["Canned reply?"]["main"][0] = [d for d in canned_out
                                             if d["node"] != "Human tap?"]
        changes.append("Canned reply? no longer feeds Human tap?")
    sort_out = [d for d in conns["Sort"]["main"][0] if d["node"] != "Human tap?"]
    sort_out.insert(1, {"node": "Human tap?", "type": "main", "index": 0})
    if sort_out != conns["Sort"]["main"][0]:
        changes.append("Sort feeds Human tap? directly and SECOND, so the "
                       "handover fires before anything downstream can throw")
        conns["Sort"]["main"][0] = sort_out

    # AND THE CANVAS IS THE ORDER. `executionOrder: v1` walks a node's branches
    # by POSITION, top to bottom, not by the order of the connections array --
    # so putting Human tap? second in that array changed nothing while it sat at
    # y=336, below `Is there a message?` at y=-16. The agent branch ran first,
    # `Send` failed on a conversation Chatwoot could not find, the run ended
    # there, and the tap never transferred. Measured twice before the cause was
    # found, which is the second time this workflow has been diagnosed through
    # an instrument rather than the code.
    #
    # Moved into the band between `Answer Meta` (y=-256) and `Is there a
    # message?` (y=-16): the 200 still goes out first, and the handover a
    # resident asked for no longer sits downstream of a delivery that can throw.
    for name, want in (("Human tap?", [440, -176]),
                       ("Transfer the tap", [680, -176]),
                       ("The tap transfer", [500, -420])):
        if name in by and by[name].get("position") != want:
            changes.append("%s moved to %s, so v1 runs the handover before the "
                           "reply branch" % (name, want))
            by[name]["position"] = want

    sticky = by.get("The tap transfer")
    STICKY = (
        "## The tap transfer\n"
        "\"לדבר עם נציג\" reaches the MODEL, which answers it in its own words -- "
        "the three canned variants went on 1 Sep, on the owner's instruction that "
        "the intro and its menu are the only fixed text in the system.\n\n"
        "A tap is still routing, and routing is still the workflow's: this fires "
        "the real handover, same webhook call the promise backstop uses. It hangs "
        "off **Sort**, not off the canned branch, because the tap no longer takes "
        "that branch -- and it sits ABOVE the reply branch on the canvas because "
        "executionOrder v1 goes by position, and a failed Send further down would "
        "otherwise end the run before the transfer happened.\n\n"
        "`tap_now` tells the model the message IS the tap; `tapped_human` tells it "
        "the next message is the answer to it."
    )
    if sticky is not None and sticky["parameters"].get("content") != STICKY:
        changes.append("The tap transfer: note rewritten -- it still said the tap "
                       "was answered by Sort, canned")
        sticky["parameters"]["content"] = STICKY

    print("workflow : %s  (%s, active=%s)"
          % (live["name"], live["id"], live.get("active")))
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

    # PUT takes only these four keys; sending id/active/tags back is a 400.
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": live["nodes"],
        "connections": live["connections"], "settings": live.get("settings", {}),
    })
    print("")
    print("written. Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
