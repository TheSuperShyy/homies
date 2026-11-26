# -*- coding: utf-8 -*-
"""A price quote: Michael asks what it is for and what is needed, records it, and says management will get back (26 Nov; epoch 118).

    python scripts/n8n_whatsapp_quote.py              # dry run
    python scripts/n8n_whatsapp_quote.py --doc        # write the prompt edits into prompt.md's fence (once)
    python scripts/n8n_whatsapp_quote.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_quote.py --apply      # write it
    python scripts/n8n_whatsapp_quote.py --restore    # put the snapshot back

WHY. The owner, 26 Nov, after the Grok quote run (conversation 108): "Price quotation should ask questions in general
like what would you like to inquire and stuff and what are the items and stuff then will say the management team will
get back to you i took note of this one and forwarded it to them then the bot will send a summary of what happened in
the email of yariv, eden and assaf". Until now a quote was noted at once, then Michael asked what was missing, one
question at a time, and named nobody ("only I", 29 Oct). That holds for every other matter; a quote is now the
exception, like a payment that is not by credit card.

WHAT CHANGES, in one write:
  The prompt     the one-voice exceptions name the quote; the quote leaves the list of matters noted at once; one
                 passage: first what the quote is for and what is needed (items, about how many, where), one short
                 question at a time; then the note with all of it; then, in the same message, that he recorded it
                 and passed it to the management team, who will get back to him about the quote, never when.
  notify_team    the same in the tool's words, with the description as the summary the email carries; "the one
                 note the resident hears about" is no longer only the payment; the quote leaves the at-once list.
  Send           promise v9: "will get back to you" (and the other call-back verbs) stays in a turn where
                 notify_team recorded a quote, the way it stays after a recorded standing order. Time words
                 ("soon") are still cut.
  Memory         epoch 117 -> 118.
The email to Yariv, Eden and Assaf Clix is "Hand to a person"'s (scripts/n8n_handover_quote.py), not this.
Not changed: Team note this turn? (a quote turn has its notify_team call), Let the team know, the other tools.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py.
"""
import copy
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 118
OLD_KEY = "={{ $json.to }}-117"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-26nov-before-quote.json")
DOC = os.path.join(W.ROOT, "docs", "features", "11-whatsapp-bot", "prompt.md")

QUOTE_HE = (
    "בקשה להצעת מחיר היא אחרת, וזאת החלטה של ההנהלה: לפני שאתה רושם אותה, אתה מבין ממנו, במילים שלך ובשאלות "
    "קצרות, שאלה אחת בכל פעם, על מה ההצעה ומה בדיוק הוא צריך: אילו פריטים או עבודות, בערך כמה ואיפה בבניין, "
    "ומה שכבר סיפר אתה לא שואל שוב. כשיש לך את התמונה, אתה רושם את הבקשה עם הכלי שיש לך לזה, עם כל מה שסיפר, "
    "ואומר לו באותה הודעה, במילים שלך, שרשמת אותה והעברת אותה לצוות ההנהלה, שיחזור אליו לגבי ההצעה, בלי מתי.")

PROMPT_EDITS = (
    ("רק במעלית, בהוראת קבע ובתשלום שלא בכרטיס אשראי זה אחרת, כמו שכתוב בהמשך.",
     "רק במעלית, בהוראת קבע, בתשלום שלא בכרטיס אשראי ובהצעת מחיר זה אחרת, כמו שכתוב בהמשך."),
    ("מסמך שצריך, כניסה לדירה ויציאה ממנה, חוזה, הצעת מחיר, עניין עם חברי ועד הבית עצמם,",
     "מסמך שצריך, כניסה לדירה ויציאה ממנה, חוזה, עניין עם חברי ועד הבית עצמם,"),
    ("אתה גם לא שואל את הדייר אם לרשום: בקשה שמעבר לך נרשמת, ואז מספרים לו.",
     "אתה גם לא שואל את הדייר אם לרשום: בקשה שמעבר לך נרשמת, ואז מספרים לו. " + QUOTE_HE),
)

QUOTE_EN = (
    "A price quote is the other note the resident hears about. Before calling, find out in your own words what the "
    "quote is for and what they need (which items or works, roughly how many, where in the building), one short "
    "question at a time, never asking again what they already told you. Then call this once: reason quote, "
    "department management, and in the description a short summary in Hebrew of the request with every detail "
    "they gave, and their building and apartment when you know them; it is what the management team reads. Then "
    "tell them in the same message, in your own words, that you have recorded their request and passed it to the "
    "management team, who will get back to them about the quote: never when, nothing more promised.\n")

NOTIFY_EDITS = (
    ("a contract, a price quote, the committee members' own business",
     "a contract, the committee members' own business"),
    ("A payment by anything but a credit card is the one note the resident hears about, and only when they ask to "
     "pay that way themselves.",
     "A payment by anything but a credit card is a note the resident hears about, and only when they ask to pay "
     "that way themselves."),
    ("\nNever for an emergency or for gas:",
     "\n" + QUOTE_EN + "Never for an emergency or for gas:"),
    ("Apart from a payment that is not by credit card, nobody else is in it:",
     "Apart from a payment that is not by credit card and a price quote, nobody else is in it:"),
    ("Never which department; `department` is your judgment and is not spoken.",
     "Never which department, apart from the collections or management team in the hand-overs above; "
     "`department` is your judgment and is not spoken."),
)

# Send's promise cutter (promise v8 -> v9). `QN` is true when this turn's notify_team, or the first pass's that
# Try again carries, recorded a quote; then a call-back verb (CB) stays, as after a recorded standing order (SO).
# Written with "{ }" and never two closing braces together: the body is an n8n expression.
QN_JS = (" QN = st.some((x) => { if (((((x || { }).action || { }).tool) || (x || { }).tool) !== 'notify_team') "
         "return false; let o = ((x || { }).action || { }).toolInput || (x || { }).toolInput || { }; if (typeof o "
         "=== 'string') { try { o = JSON.parse(o); } catch (e) { o = { }; } } if (o && o.input && typeof o.input "
         "=== 'object') o = o.input; return String((o || { }).reason || '').trim() === 'quote'; });")
SEND_EDITS = (
    ("const pv = 'promise v8';", "const pv = 'promise v9';"),
    ("let SO = false; try {", "let SO = false; let QN = false; try {"),
    ("} catch (e) { SO = false; }", QN_JS + " } catch (e) { SO = false; QN = false; }"),
    ("!(SO && CB.test(h[3]))", "!((SO || QN) && CB.test(h[3]))"),
)

CHANGED = ["Answer the resident", "notify_team", "Send"]


def edit_text(text, edits):
    for old, new in edits:
        text = once(text, old, new)
    return text


def quote(wf):
    """The workflow with the prompt, notify_team's text and Send's promise cutter changed. Not memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    opts = by["Answer the resident"]["parameters"]["options"]
    opts["systemMessage"] = edit_text(opts["systemMessage"], PROMPT_EDITS)
    p = by["notify_team"]["parameters"]
    p["toolDescription"] = edit_text(p["toolDescription"], NOTIFY_EDITS)
    s = by["Send"]["parameters"]
    s["jsonBody"] = edit_text(s["jsonBody"], SEND_EDITS)
    if "}}" in QN_JS or "{{" in QN_JS:
        sys.exit("REFUSING: the Send insertion holds a double brace, which ends n8n's expression.")
    return out


def doc():
    """Write PROMPT_EDITS into prompt.md, inside the System prompt section only."""
    raw = io.open(DOC, encoding="utf-8", newline="").read()
    head, sep, fence = raw.partition("## System prompt")
    if not sep:
        sys.exit("REFUSING: no '## System prompt' heading in prompt.md.")
    if QUOTE_HE in fence:
        print("prompt.md already carries the edit.")
        return
    io.open(DOC, "w", encoding="utf-8", newline="").write(head + sep + edit_text(fence, PROMPT_EDITS))
    print("prompt.md: %d edits written into the System prompt section." % len(PROMPT_EDITS))


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    if "--doc" in sys.argv:
        return doc()
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and QUOTE_HE in prompt_of(live):
        print("Nothing to do. Live already asks first and names the management team for a quote, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 117's. Read live first." % key)

    new = quote(live)
    nb = {n["name"]: n for n in new["nodes"]}
    changed = [n["name"] for n in new["nodes"] if n != by[n["name"]]]
    if sorted(changed) != sorted(CHANGED):
        sys.exit("REFUSING: unexpected nodes would change: %s" % changed)
    if W.MEMORY_EPOCH != EPOCH:
        sys.exit("REFUSING: n8n_whatsapp.MEMORY_EPOCH is %d, not %d. Move the repo first." % (W.MEMORY_EPOCH, EPOCH))
    if prompt_of(new) != W.system_prompt():
        sys.exit("REFUSING: the would-be prompt is not docs/features/11-whatsapp-bot/prompt.md's. "
                 "Run --doc first; live follows the document.")
    W.check_memory_epoch(prompt=prompt_of(new), tools=tools_of(new))
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s -> %s" % (W.epoch_hash(prompt_of(live)), W.epoch_hash(prompt_of(new))))
    print("tools    : %s -> %s" % (W.epoch_hash(tools_of(live)), W.epoch_hash(tools_of(new))))
    print("memory   : %s -> %s (every buffer starts fresh)" % (OLD_KEY, NEW_KEY))
    print("changed  : %s" % ", ".join(changed + ["Conversation so far"]))

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
    print("  prompt %s (want %s); tools %s (want %s); memory key %s" % (
        W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)), W.epoch_hash(tools_of(back)),
        W.epoch_hash(tools_of(new)), bb["Conversation so far"]["parameters"]["sessionKey"]))
    for node in CHANGED:
        print("  %s: %s" % (node, "as written" if bb[node]["parameters"] == nb[node]["parameters"] else "DIFFERS"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
