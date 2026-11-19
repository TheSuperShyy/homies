# -*- coding: utf-8 -*-
"""The payment link is offered as credit card only; another way only when asked, to collections (19 Nov 2026; epoch 115).

    python scripts/n8n_whatsapp_cardonly.py              # dry run
    python scripts/n8n_whatsapp_cardonly.py --doc        # write the prompt edits into prompt.md's fence (once)
    python scripts/n8n_whatsapp_cardonly.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_cardonly.py --apply      # write it
    python scripts/n8n_whatsapp_cardonly.py --restore    # put the snapshot back

WHY. Yariv, 19 Nov, on the one-conversation run (execution 190914, "אתה יכול לבחור לשלם בהוראת קבע (באשראי או
בבנק)"): "דרך הקישור זה צריך להיות ברור שניתן רק באשראי. ואז אם הדייר יגיד (רק אם יגיד) שהוא רוצה באפשרות אחרת
נניח של צקים או בנק, אז שהבוט יעביר לנציגים שלנו (המטרה שלנו לעודד את כולם או יותר נכון לדחוף אותם לתשלום
באשראי)". Forwarded by the owner. The 17 Nov sentence (epoch 110) said the link's page offers a standing order "by
card or bank", and the prompt's facts listed every way to pay.

WHAT CHANGES, in one write:
  The prompt              the link is for paying by credit card, said when it is sent, and the one way offered;
                          its page's standing order is by credit card; a standing order from the bank is
                          request_standing_order's (collections phone); any way but a card is collections', and only
                          for whoever asks: a bank transfer as before (the account details), cheques, cash or another
                          way to a representative from collections who will get back to them here, never when. The
                          one-voice sentence and the tool list name "a payment not by credit card"; the facts line no
                          longer lists the ways.
  get_payment_link        card only, never another way offered; another way, asked, goes to notify_team
                          (bank_transfer, or payment) or request_standing_order (from the bank).
  request_standing_order  also for a standing order from their bank account.
  notify_team             a payment by anything but a card is the one note the tenant hears about; cheques, cash or
                          another way: reason payment, department collections, told in the same way.
  A word first?           ackhold v2: cheques or cash in the tenant's words hold the payment-ack note too.
  Team note this turn?    banknote v2: cheques or cash asked and collections in the reply send the note too.
  Let the team know       otherpay v1: with no notify_team call, cheques or cash in the tenant's words make the
                          backstop's reason `payment` (Collections), not `other` (Service).
  Memory                  epoch 114 -> 115.
Not changed: Send, Reply usable?, Try again, the other tools, "Hand to a person" (payment already goes to
Collections there), the templates (neither names a way to pay).
The incoming phone agent's twin is owed, and so is the debt agent's ("בדף שהוא פותח בוחרים הוראת קבע, באשראי או
בבנק"): both on the owner's word.

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
from n8n_whatsapp_bankagain import TRANSFER_WORDS  # noqa: E402

EPOCH = 115
OLD_KEY = "={{ $json.to }}-114"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-19nov-before-cardonly.json")
DOC = os.path.join(W.ROOT, "docs", "features", "11-whatsapp-bot", "prompt.md")

# Cheques (צ'ק, צ׳ק, Yariv's צקים, שיק, שיקים, with a prefix ב/ו/ה/ל/ש) and cash, as whole words where it matters:
# "שיקום" (a renovation) is not a cheque. No quantifier braces, so nothing in it can read as an expression's end.
OTHERPAY_WORDS = "/(^|[^א-ת])[ובהלש]?[ובהלש]?(צ['׳]?ק|שיק)(ים)?(?![א-ת])|המחא|מזומן/"

PROMPT_EDITS = (
    ("רק במעלית, בהוראת קבע ובהעברה בנקאית זה אחרת, כמו שכתוב בהמשך.",
     "רק במעלית, בהוראת קבע ובתשלום שלא בכרטיס אשראי זה אחרת, כמו שכתוב בהמשך."),
    ("קישור שחזר סוגר את העניין, בלי קריאה ובלי הערה.",
     "קישור שחזר סוגר את העניין, בלי קריאה ובלי הערה. התשלום בקישור הוא בכרטיס אשראי, וזאת הדרך שאתה מציע: כשאתה "
     "שולח אותו אתה אומר שהוא לתשלום בכרטיס אשראי, ודרך תשלום אחרת אתה לא מציע ולא מונה."),
    ("מסדירים אותה בדף שהקישור לתשלום פותח, ושם בוחרים הוראת קבע, באשראי או בבנק.",
     "מסדירים אותה בדף שהקישור לתשלום פותח, ושם בוחרים הוראת קבע בכרטיס אשראי."),
    ("עם הסבר קצר שבדף בוחרים הוראת קבע, ושאלה אם זה מסתדר לו",
     "עם הסבר קצר שבדף בוחרים הוראת קבע בכרטיס אשראי, ושאלה אם זה מסתדר לו"),
    ("מי שמעדיף שיתקשרו, וגם מי שלא חזר לו קישור,",
     "מי שמעדיף שיתקשרו, מי שרוצה הוראת קבע מחשבון הבנק, וגם מי שלא חזר לו קישור,"),
    ("העברה בנקאית היא עניין של צוות הגבייה: את פרטי החשבון אין לך, ואתה לא ממציא אותם.",
     "תשלום שלא בכרטיס אשראי הוא עניין של צוות הגבייה, ורק מי שמבקש בעצמו לשלם אחרת עובר אליו. את פרטי החשבון אין "
     "לך, ואתה לא ממציא אותם."),
    ("ואומר לו שהעברת אותו לנציג מצוות הגבייה שישלח לו כאן את פרטי החשבון, בלי מתי.",
     "ואומר לו שהעברת אותו לנציג מצוות הגבייה שישלח לו כאן את פרטי החשבון, בלי מתי. וכך גם מי שרוצה לשלם בשיקים, "
     "במזומן או בכל דרך אחרת שהיא לא כרטיס אשראי: אתה מעביר אותו לנציג מצוות הגבייה עם אותו כלי, ואומר לו שהעברת "
     "אותו לנציג מצוות הגבייה שיחזור אליו כאן לגבי זה, בלי מתי."),
    ("מעביר לנציג מצוות הגבייה מי שרוצה לשלם בהעברה בנקאית,",
     "מעביר לנציג מצוות הגבייה מי שרוצה לשלם שלא בכרטיס אשראי,"),
    ("- **תשלום:** עד ה־10 בכל חודש, בהעברה בנקאית, הוראת קבע, כרטיס אשראי או שיקים.",
     "- **תשלום:** עד ה־10 בכל חודש, בכרטיס אשראי, בקישור האישי. העברה בנקאית, הוראת קבע מהבנק או שיקים מסדירים רק "
     "עם נציג מצוות הגבייה, ורק למי שמבקש."),
)

LINK_EDITS = (
    ("A bank transfer is not this: a resident who wants to pay by bank transfer, or asks for the account details, is "
     "handed to collections with notify_team (reason bank_transfer) instead.",
     "The link is paid by credit card only, and it is the one way to pay you offer: when you send it, say it is for "
     "paying by credit card, and never offer or list another way. Another way is not this, and only when the resident "
     "asks for it himself: a bank transfer or the account details go to collections with notify_team (reason "
     "bank_transfer); cheques, cash or any other way but a card go to collections with notify_team (reason payment); "
     "a standing order from their bank account is request_standing_order's."),
    ("the page the link opens offers one, by card or through the bank.",
     "the page the link opens offers one on a credit card."),
)

STANDING_EDITS = (
    ("Call this when a resident who asked for one would rather someone from the collections team phoned them, or "
     "when get_payment_link found no link for them:",
     "Call this when a resident who asked for one would rather someone from the collections team phoned them, wants "
     "it from their bank account rather than on a credit card, or when get_payment_link found no link for them:"),
)

NOTIFY_EDITS = (
    ("A bank transfer is the one note the resident hears about.",
     "A payment by anything but a credit card is the one note the resident hears about, and only when they ask to pay "
     "that way themselves."),
    ("then whether there is anything else you can help with meanwhile. Every time they ask to pay by transfer or for "
     "the account details, call this again,",
     "then whether there is anything else you can help with meanwhile. The same for a resident who wants to pay by "
     "cheques, in cash or any other way but a credit card: reason payment, department collections, with the way they "
     "named; tell them you have passed them to a representative from the collections team, who will get back to them "
     "about it here, never when. Every time they ask to pay by transfer, for the account details or another way but a "
     "card, call this again,"),
    ("Apart from a bank transfer, nobody else is in it:",
     "Apart from a payment that is not by credit card, nobody else is in it:"),
)

# The three code pieces that read the tenant's words for a transfer (bankagain.py, bankwhen.py) read cheques and cash too.
WORD_OLD = "(() => { const ahv = 'ackhold v1'; return !%s.test(said); })()" % TRANSFER_WORDS
WORD_NEW = "(() => { const ahv = 'ackhold v2'; return !%s.test(said) && !%s.test(said); })()" % (TRANSFER_WORDS,
                                                                                                   OTHERPAY_WORDS)
NOTE_OLD = ("(() => { const btv = 'banknote v1'; try { return %s.test(String($('Sort').first().json.in_text || "
            "$('Sort').first().json.text || '')) && /גבייה/.test(String($json.output || '')); } catch (e) { return "
            "false; } })()" % TRANSFER_WORDS)
NOTE_NEW = ("(() => { const btv = 'banknote v2'; try { const said = String($('Sort').first().json.in_text || "
            "$('Sort').first().json.text || ''); return (%s.test(said) || %s.test(said)) && "
            "/גבייה/.test(String($json.output || '')); } catch (e) { return false; } })()" % (TRANSFER_WORDS,
                                                                                            OTHERPAY_WORDS))
WHY_OLD = ("return String(o.reason || (%s.test(String($('Sort').first().json.in_text || $('Sort').first().json.text "
           "|| '')) ? 'bank_transfer' : 'other'));" % TRANSFER_WORDS)
WHY_NEW = ("return String(o.reason || (() => { const opv = 'otherpay v1'; const said = String($('Sort').first().json"
           ".in_text || $('Sort').first().json.text || ''); return %s.test(said) ? 'bank_transfer' : %s.test(said) ? "
           "'payment' : 'other'; })());" % (TRANSFER_WORDS, OTHERPAY_WORDS))


def edit_text(text, edits):
    for old, new in edits:
        text = once(text, old, new)
    return text


def cardonly(wf):
    """The workflow with the prompt, three tool texts and three code pieces changed. Not memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    opts = by["Answer the resident"]["parameters"]["options"]
    opts["systemMessage"] = edit_text(opts["systemMessage"], PROMPT_EDITS)
    for node, edits in (("get_payment_link", LINK_EDITS), ("request_standing_order", STANDING_EDITS),
                        ("notify_team", NOTIFY_EDITS)):
        p = by[node]["parameters"]
        p["toolDescription"] = edit_text(p["toolDescription"], edits)
    word = by["A word first?"]["parameters"]["conditions"]["conditions"][0]
    word["leftValue"] = once(word["leftValue"], WORD_OLD, WORD_NEW)
    note = by["Team note this turn?"]["parameters"]["conditions"]["conditions"][0]
    note["leftValue"] = once(note["leftValue"], NOTE_OLD, NOTE_NEW)
    wi = by["Let the team know"]["parameters"]["workflowInputs"]["value"]
    wi["reason"] = once(wi["reason"], WHY_OLD, WHY_NEW)
    return out


def doc():
    """Write PROMPT_EDITS into prompt.md, inside the System prompt section only (the dated notes quote old lines)."""
    raw = io.open(DOC, encoding="utf-8", newline="").read()
    head, sep, fence = raw.partition("## System prompt")
    if not sep:
        sys.exit("REFUSING: no '## System prompt' heading in prompt.md.")
    if PROMPT_EDITS[0][1] in fence:
        print("prompt.md already carries the edits.")
        return
    io.open(DOC, "w", encoding="utf-8", newline="").write(head + sep + edit_text(fence, PROMPT_EDITS))
    print("prompt.md: %d edits written into the System prompt section." % len(PROMPT_EDITS))


CHANGED = ["Answer the resident", "get_payment_link", "request_standing_order", "notify_team", "A word first?",
           "Team note this turn?", "Let the team know"]


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    if "--doc" in sys.argv:
        return doc()
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and LINK_EDITS[0][1] in by["get_payment_link"]["parameters"]["toolDescription"]:
        print("Nothing to do. Live already offers the link as card only, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 114's. Read live first." % key)

    new = cardonly(live)
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
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
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
