# -*- coding: utf-8 -*-
"""The word before a check is willingness to check, never a word that sounds like the answer
(29 Oct 2026, late, epoch 88).

    python scripts/n8n_whatsapp_checkword.py              # dry run
    python scripts/n8n_whatsapp_checkword.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_checkword.py --apply      # write it
    python scripts/n8n_whatsapp_checkword.py --restore    # put the snapshot back

WHY. Three minutes after n8n_whatsapp_gladly.py went live (19:13 UTC), the owner sent his balance
question again (execution 138931, 19:16). The epoch bump had emptied the bot's memory, so "אה, חשבתי
שזה בחינם. בכל מקרה, אני צריך לבדוק אם נשארה לי יתרה" came with no "it" to refer to, and the bot
answered the first half: "הכל בסדר 🙂 בדקתי במערכת, ורשומה לך יתרה של 2,000 ש"ח …". The owner: "what is
this?????? why did it say everything is fine".

WHERE IT CAME FROM. The paragraph on the word before an answer sizes it to the situation (a ticket
asked for: warm willingness; a fault: care; a delay: sorrow; something not Homies': a human word) and
has no line for a request to check something, a balance, a ticket's status, what the fee covers. With
nothing there, the model reached for the quoted "אין בעיה" kind of word, which in front of a debt
reads as the verdict. gladly's blind check kept the earlier chat in memory, so "it" had a meaning and
this case never came up.

WHAT CHANGES, one clause in that list: a request to check something gets willingness to check, not a
word that sounds like the answer itself, and then straight to what the system shows. And the quoted
list's "אין בעיה" becomes "כמובן": it is the word taken once "בשמחה" has been said in a chat, and a
blind player wrote "אין בעיה. לפי המערכת שלנו נשארה לך יתרה של 2,000 ₪". Plus the
memory: epoch 87 -> 88, because the owner's buffer holds the "הכל בסדר" reply.

AND A GUARANTEE IN CODE (the owner: "i dont want that to happen again ever"). A prompt clause lowers the
odds; it cannot promise. A blind Claude player given the OLD text on 138931's exact input wrote
"בשמחה. לפי מה שרשום אצלנו במערכת …", so a Claude-played pass cannot even see this slip of Gemini's.
So Send gets "allclear v1", after its manners step: in a turn where a tool ran, an all-clear
("הכל בסדר", "הכל טוב", "הכל תקין", with or without "גמור", spelt הכל or הכול) is cut where it is an
interjection, at the start of a sentence followed by punctuation, an emoji or a line break, or joined
on with ו ("…והכל בסדר."). What the tool found stays and says it. A question ("הכל בסדר עם זה?") is not
touched, and neither is a reply the cut would leave under two words. A turn with no tool ("how are
you?" -> "הכל טוב, ואצלך?") is not touched either. --watch flags any all-clear left in a tool turn.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py, as n8n_whatsapp_ionly.py did.
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

EPOCH = 88
OLD_KEY = "={{ $json.to }}-87"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-29oct-before-checkword.json")

CHECK_WORD = ("למי שביקש שתבדוק לו משהו, יתרה, מצב של קריאה או מה כלול בתשלום, נכונות לבדוק, ולא מילה שנשמעת "
              "כמו התשובה עצמה, ומשם ישר למה שהמערכת מראה; ")
EDITS = [
    ("ומשם ישר למה שאתה עושה בשבילו; ולמי שקרה לו משהו",
     "ומשם ישר למה שאתה עושה בשבילו; " + CHECK_WORD + "ולמי שקרה לו משהו"),
    # The quoted list's second word is the one taken once "בשמחה" has been said in a chat (the list's own
    # "not the same word twice"): the blind player then wrote "אין בעיה. לפי המערכת שלנו נשארה לך יתרה של
    # 2,000 ₪", the same ambiguity in a milder form. "כמובן" is willingness and nothing else.
    ('"בשמחה", "אין בעיה", "אוי, לא נעים"', '"בשמחה", "כמובן", "אוי, לא נעים"'),
]
# Send: the manners step's result becomes c0, and "allclear v1" makes c from it, so everything after
# (the promise filter, the emoji rule, the body) reads the cut text.
SEND_FROM = "const c = (() => { const mv = 'manners v4';"
SEND_TO = "const c0 = (() => { const mv = 'manners v4';"
ALLCLEAR_AT = "return (head + rest).trim(); })(); const body = { content: c,"
ALLCLEAR_JS = (
    r"const c = (() => { const av = 'allclear v1'; let worked = false; "
    r"try { worked = ($('Answer the resident').first().json.intermediateSteps || []).length > 0; } "
    r"catch (e) { worked = false; } if (!worked) return c0; "
    r"const AC1 = /(^|[.!?\n]\s*|[\p{Extended_Pictographic}\uFE0F]\s*)(הכל|הכול)\s+(בסדר|טוב|תקין)(\s+גמור)?"
    r"(?=[^\S\n]*(?:[,.!:;\n\p{Extended_Pictographic}\uFE0F]|$))[\s,.!:;\p{Extended_Pictographic}\uFE0F]*/gu; "
    r"const AC2 = /\s+ו(הכל|הכול)\s+(בסדר|טוב|תקין)(\s+גמור)?"
    r"(?=[^\S\n]*(?:[,.!:;\n\p{Extended_Pictographic}\uFE0F]|$))/gu; "
    r"const out = c0.replace(AC1, (m, lead) => lead).replace(AC2, '').replace(/ {2,}/g, ' ').trim(); "
    r"return out.split(/\s+/).filter(Boolean).length >= 2 ? out : c0; })(); ")


def checkword(wf):
    """The workflow with the clause and allclear v1; each anchor must occur exactly once. Not memory."""
    out = copy.deepcopy(wf)
    opts = {n["name"]: n for n in out["nodes"]}["Answer the resident"]["parameters"]["options"]
    sm = opts["systemMessage"]
    for old, new in EDITS:
        sm = once(sm, old, new)
    opts["systemMessage"] = sm
    send = {n["name"]: n for n in out["nodes"]}["Send"]["parameters"]
    body = once(send["jsonBody"], SEND_FROM, SEND_TO)
    send["jsonBody"] = once(body, ALLCLEAR_AT, ALLCLEAR_AT.replace(" const body = ", " " + ALLCLEAR_JS + "const body = ", 1))
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and CHECK_WORD in prompt_of(live):
        print("Nothing to do. Live already has the check word, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 87's. Read live first." % key)

    new = checkword(live)
    nb = {n["name"]: n for n in new["nodes"]}
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("tools    : %s (unchanged: %s)" % (W.epoch_hash(tools_of(new)), tools_of(new) == tools_of(live)))
    print("memory   : %s -> %s (every buffer starts fresh)" % (OLD_KEY, NEW_KEY))
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
    print("\nwritten  : %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  prompt %s (want %s); memory key %s" % (W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)),
                                                     bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
