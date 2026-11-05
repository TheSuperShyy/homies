# -*- coding: utf-8 -*-
"""A standing order is recorded with one tool and reaches collections by email (5 Nov 2026, epoch 96).
Yariv's change 3 of the 4 Nov review.

    python scripts/n8n_whatsapp_standing.py              # dry run
    python scripts/n8n_whatsapp_standing.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_standing.py --apply      # write it
    python scripts/n8n_whatsapp_standing.py --restore    # put the snapshot back

WHY. At the review (local/meetings/2026-11-04-homies-agent-review.md, 7:32-15:06) Homies decided that,
while OXS's payment API has one-time payments only, a resident's request for a standing order (הוראת
קבע) goes to the collections team by email: "I don't want another system I need to monitor every
time". The bot had no way to do that. Nobody has asked it on WhatsApp yet (0 inbound messages with
"קבע" by 5 Nov), and what the texts pointed it to was wrong for it: "wants to pay or asks how" is
get_payment_link, a one-time link, and "a payment arrangement" is a ticket plus a team note, which lands
in the inbox, the other system.

WHAT CHANGES.
- A tool, request_standing_order, at the end of the tool row: the same call to the function as
  add_request_detail. debt-tools v148 (PR #5) records the request once per number, from the record
  for a tenant on file (or asks: need_name, and open_request's building answers), never into OXS, and
  hands it to "Homies — Standing order email" (scripts/n8n_standing_order_email.py), which emails
  collections. Its text says when (the ask itself, or a yes), that it is the whole of it (no link, no
  ticket, no note), that no card or bank detail goes through the chat, and what to say: recorded, with
  the number, nobody else in it.
- The prompt: one sentence after the payment arrangement's, that a standing order is neither an
  arrangement nor a link and is recorded with the tool alone; and the list of what he does names it.
- get_payment_link's text: a standing order is not a link.
- Memory epoch 95 -> 96.
Not changed: open_request, notify_team, get_balance, the guards, Send. The guards need nothing: "רשמתי"
is not a deed they police, and the number comes back in the tool's own answer, so it is a known one.
The phone agent is unchanged (the owner, 5 Nov: chatbot first).

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py, then n8n_uchat.py --apply carries it to
the UChat copy, the bot in use.
"""
import copy
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

EPOCH = 96
OLD_KEY = "={{ $json.to }}-95"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-05nov-before-standing.json")
NL = chr(10)

TOOL = "request_standing_order"
POSITION = [3360, 420]                    # the end of the tool row, on the 240 x 60 grid
TOOL_DESCRIPTION = (
    "Record a request for a standing order (הוראת קבע) for the monthly payment, so the people at Homies "
    "who set one up have it. Call it the moment a resident asks for one, asks whether they can pay by "
    "one, wants to move their payment to one, or says yes to one: the ask itself is the reason to call, "
    "so never ask whether they want it recorded. For a tenant on file for the number they write from it "
    "needs nothing more, because it finds their name, building and apartment itself: send only `said`. "
    "Returns `recorded` true with the request's `reference`; with `already_recorded` true it was recorded "
    "before, it is the same request with the same number, and nothing new was recorded. `need_name`: "
    "nobody is on file for that number, so ask, once, for their full name, in the same sentence as the "
    "building and apartment if you do not have them, then call again with them. `need_building`, and "
    "`building_found` false with its reasons, mean what they mean for open_request. A standing order is "
    "not a payment link, a ticket or a note: this one call is all of it. Never ask for a card number, a "
    "bank account or how they will pay: none of that goes through this chat. What you tell them is that "
    "you recorded their request for a standing order, with its number. It is not a message to anyone, "
    "so never who will handle it, contact them or when.")
JSON_BODY = (
    "={{ JSON.stringify({ message: { call: { id: 'wa:' + $('Sort').first().json.to, assistantOverrides: "
    "{ variableValues: { phone: $('Sort').first().json.to } } }, toolCalls: [{ id: 'wa', function: { name: "
    "'request_standing_order', arguments: { said: $fromAI('said', \"What they asked for, in Hebrew, in "
    "their own words.\", 'string'), reporter_name: $fromAI('reporter_name', \"Their full name, only after "
    "this tool answered need_name and they told you it. Leave it empty otherwise: a tenant on file for "
    "their number is named from the record.\", 'string'), building: $fromAI('building', \"Street and "
    "number in Hebrew, only after this tool asked for the building. Leave it empty otherwise.\", "
    "'string'), unit: $fromAI('unit', \"The apartment they live in, only after this tool asked for the "
    "building. Leave it empty otherwise.\", 'string') } } }] } }) }}")

PROMPT_EDITS = [
    ("כשלא חזר קישור, וכן כשמבקשים הסדר תשלום, זה הולך כמו תקלה: קריאת שירות על זה, עם מספר, וגם הערה "
     "במערכת, עם הכלי שיש לך לזה.",
     "כשלא חזר קישור, וכן כשמבקשים הסדר תשלום, זה הולך כמו תקלה: קריאת שירות על זה, עם מספר, וגם הערה "
     "במערכת, עם הכלי שיש לך לזה. הוראת קבע היא לא הסדר תשלום ולא קישור: מי שמבקש אותה, או שואל אם אפשר "
     "לשלם כך, אתה רושם את הבקשה שלו בכלי שיש לך לזה, ורק בו, בלי קריאת שירות ובלי הערה."),
    ("נותן קישור לתשלום, מברר מה הומי'ז עושה ורושם הערות במערכת.",
     "נותן קישור לתשלום, רושם בקשה להוראת קבע, מברר מה הומי'ז עושה ורושם הערות במערכת."),
]
LINK_OLD = ("Call the moment a resident wants to pay, asks how or where to pay, asks for their payment link, "
            "or says after a balance that they will settle it.")
LINK_NEW = LINK_OLD + (" A standing order (הוראת קבע) is not this: asking for one, or whether they can pay by "
                       "one, is request_standing_order's, and gets no link.")


def standing(wf):
    """The workflow with the tool, the prompt's two edits and get_payment_link's clause. Not memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    if TOOL in by:
        sys.exit("REFUSING: the workflow already has a node named %r." % TOOL)
    opts = by["Answer the resident"]["parameters"]["options"]
    sm = opts["systemMessage"]
    for old, new in PROMPT_EDITS:
        sm = once(sm, old, new)
    opts["systemMessage"] = sm
    link = by["get_payment_link"]["parameters"]
    link["toolDescription"] = once(link["toolDescription"], LINK_OLD, LINK_NEW)

    tool = copy.deepcopy(by["add_request_detail"])   # the same call to the function, the same credential
    tool.update({"id": str(uuid.uuid4()), "name": TOOL, "position": list(POSITION)})
    tool["parameters"]["jsonBody"] = JSON_BODY
    tool["parameters"]["toolDescription"] = TOOL_DESCRIPTION
    out["nodes"].append(tool)
    out["connections"][TOOL] = {"ai_tool": [[{"node": "Answer the resident", "type": "ai_tool", "index": 0}]]}
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and TOOL in by:
        print("Nothing to do. Live already has %s, epoch %d." % (TOOL, EPOCH))
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 95's. Read live first." % key)

    new = standing(live)
    nb = {n["name"]: n for n in new["nodes"]}
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    worse = sorted(layout_complaints(new["nodes"]) - layout_complaints(live["nodes"]))
    if worse:
        sys.exit("REFUSING TO PATCH. New placement problems:" + NL + "    " + (NL + "    ").join(worse))
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("tools    : %s -> %s (get_payment_link's text; %s is outside the hash, pinned by the gate)"
          % (W.epoch_hash(tools_of(live)), W.epoch_hash(tools_of(new)), TOOL))
    print("memory   : %s -> %s (every buffer starts fresh)" % (OLD_KEY, NEW_KEY))
    print("changed  : %s" % ", ".join(n["name"] for n in new["nodes"] if n["name"] not in by or n != by[n["name"]]))

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
    print("  %s %s; prompt %s (want %s); tools %s (want %s); memory key %s" % (
        TOOL, "present" if TOOL in bb else "MISSING", W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)),
        W.epoch_hash(tools_of(back)), W.epoch_hash(tools_of(new)), bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
