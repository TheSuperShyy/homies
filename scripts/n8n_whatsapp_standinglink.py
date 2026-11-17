# -*- coding: utf-8 -*-
"""A standing order is answered with the payment link first (17 Nov 2026; epoch 110).

    python scripts/n8n_whatsapp_standinglink.py              # dry run
    python scripts/n8n_whatsapp_standinglink.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_standinglink.py --apply      # write it
    python scripts/n8n_whatsapp_standinglink.py --restore    # put the snapshot back

WHY. On 4 Nov Homies decided that a request for a standing order (הוראת קבע) goes to the collections team
by email, because "OXS's payment API has one-time payments only" (n8n_whatsapp_standing.py, epoch 96; Yariv's
9 Nov review added that a team member phones the tenant). On 17 Nov the page our payment link opens
(OXS's tenant page, "OXS: תשלום וועד בית באשראי") turned out to offer "הוראת קבע בכרטיס אשראי" and "הוראת
קבע בנקאית דיגיטלית" itself (CONTEXT, "The payment link is also the way to a standing order"). The owner
saw three examples and said "ok thats better", then "ok go ahead and make the change".

WHAT CHANGES, in one write:
  The prompt              a standing order is set up on the page the payment link opens. Whoever asks for
                          one gets their personal link, a short line that on the page they choose a standing
                          order, and the question whether that works or they would rather someone from the
                          collections team phoned them. Whoever prefers the call, or gets no link, is recorded
                          with request_standing_order exactly as before (recorded, the number, collections
                          will phone, never when).
  get_payment_link        its "a standing order is not this ... gets no link" becomes the first answer to one.
  request_standing_order  called for the phone call or when no link came back, no longer at the first ask.
  Memory                  epoch 109 -> 110.
Not changed: the tool row, open_request, notify_team, get_balance, the guards, Send, the email to collections.
The incoming phone agent's twin is owed, and the debt agent follows separately (the owner: WhatsApp first).

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py. The bot in use is this workflow (Chatwoot,
since 10 Nov); the UChat copy is off.
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

EPOCH = 110
OLD_KEY = "={{ $json.to }}-109"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-17nov-before-standinglink.json")

PROMPT_EDITS = (
    ("הוראת קבע היא לא הסדר תשלום ולא קישור: מי שמבקש אותה, או שואל אם אפשר לשלם כך, אתה רושם את הבקשה שלו "
     "בכלי שיש לך לזה, ורק בו, בלי קריאת שירות ובלי הערה, ואומר לו שרשמת אותה ושמישהו מצוות הגבייה ייצור איתו "
     "קשר בטלפון, בלי מתי.",
     "הוראת קבע היא לא הסדר תשלום: מסדירים אותה בדף שהקישור לתשלום פותח, ושם בוחרים הוראת קבע, באשראי או "
     "בבנק. מי שמבקש אותה, או שואל אם אפשר לשלם כך, מקבל ממך את הקישור האישי שלו, עם הסבר קצר שבדף בוחרים "
     "הוראת קבע, ושאלה אם זה מסתדר לו או שנוח לו יותר שמישהו מצוות הגבייה יתקשר אליו. מי שמעדיף שיתקשרו, וגם "
     "מי שלא חזר לו קישור, אתה רושם את הבקשה שלו בכלי שיש לך לזה, ורק בו, בלי קריאת שירות ובלי הערה, ואומר "
     "לו שרשמת אותה ושמישהו מצוות הגבייה ייצור איתו קשר בטלפון, בלי מתי."),
)

LINK_EDITS = (
    ("A standing order (הוראת קבע) is not this: asking for one, or whether they can pay by one, is "
     "request_standing_order's, and gets no link.",
     "It is also the first answer to a standing order (הוראת קבע): the page the link opens offers one, by card "
     "or through the bank. Asking for one, or whether they can pay by one, gets this link with a short line that "
     "on the page they choose a standing order, and, instead of the usual close, the question whether that works "
     "for them or they would rather someone from the collections team phoned them; that phone call is "
     "request_standing_order's."),
)

STANDING_EDITS = (
    ("Call it the moment a resident asks for one, asks whether they can pay by one, wants to move their payment "
     "to one, or says yes to one: the ask itself is the reason to call, so never ask whether they want it "
     "recorded.",
     "The first answer to a standing-order ask is get_payment_link, whose page offers one. Call this when a "
     "resident who asked for one would rather someone from the collections team phoned them, or when "
     "get_payment_link found no link for them: then never ask whether they want it recorded."),
    ("A standing order is not a payment link, a ticket or a note: this one call is all of it.",
     "It is not a ticket or a note: this one call is all of it."),
)


def standinglink(wf):
    """The workflow with the prompt's sentence and the two tool texts changed. Not memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    opts = by["Answer the resident"]["parameters"]["options"]
    sm = opts["systemMessage"]
    for old, new in PROMPT_EDITS:
        sm = once(sm, old, new)
    opts["systemMessage"] = sm
    for node, edits in (("get_payment_link", LINK_EDITS), ("request_standing_order", STANDING_EDITS)):
        p = by[node]["parameters"]
        d = p["toolDescription"]
        for old, new in edits:
            d = once(d, old, new)
        p["toolDescription"] = d
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and LINK_EDITS[0][1] in by["get_payment_link"]["parameters"]["toolDescription"]:
        print("Nothing to do. Live already answers a standing order with the link, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 109's. Read live first." % key)

    new = standinglink(live)
    nb = {n["name"]: n for n in new["nodes"]}
    changed = [n["name"] for n in new["nodes"] if n != by[n["name"]]]
    if sorted(changed) != sorted(["Answer the resident", "get_payment_link", "request_standing_order"]):
        sys.exit("REFUSING: unexpected nodes would change: %s" % changed)
    if W.MEMORY_EPOCH != EPOCH:
        sys.exit("REFUSING: n8n_whatsapp.MEMORY_EPOCH is %d, not %d. Move the repo first." % (W.MEMORY_EPOCH, EPOCH))
    if prompt_of(new) != W.system_prompt():
        sys.exit("REFUSING: the would-be prompt is not docs/features/11-whatsapp-bot/prompt.md's. "
                 "Edit the document first; live follows it.")
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
        W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)),
        W.epoch_hash(tools_of(back)), W.epoch_hash(tools_of(new)),
        bb["Conversation so far"]["parameters"]["sessionKey"]))
    for node in ("get_payment_link", "request_standing_order"):
        print("  %s: %s" % (node, "as written" if bb[node]["parameters"]["toolDescription"]
                            == nb[node]["parameters"]["toolDescription"] else "DIFFERS"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
