# -*- coding: utf-8 -*-
"""Something new about an open ticket goes on the ticket, and the photo note says only what is true
(29 Oct 2026, night, epoch 90).

    python scripts/n8n_whatsapp_addto.py              # dry run
    python scripts/n8n_whatsapp_addto.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_addto.py --apply      # write it
    python scripts/n8n_whatsapp_addto.py --restore    # put the snapshot back

WHY. On the owner's handset (20:17-20:20 UTC) a photo of the broken stairwell light, then "its the 2nd
light near the emergency exit", then "i will just put the broken bulb ... in the side railings", got
"רשמתי במערכת … והוספתי גם את התמונה ששלחת לקריאה הקיימת" and "הוספתי את העדכון הזה לקריאה כדי שהצוות
ידע". The owner: "is this real? did it notif anyone or updated the ticket". Nothing was. Ticket
255-1365-26 was unchanged since 19 Oct and the photo was on no ticket. Both notify_team notes were
dropped by "Hand to a person" as a repeated `other` (the one of 17:06 UTC), so nobody was told either.

TWO CAUSES.
1. The bot had no way to add to a ticket. Its tools open one, read one or leave a note, and a note never
   touches a ticket, so it took the note and said the ticket had it. The function has had
   add_request_detail since August (the voice agent's; it appends, never replaces); the bot never got it.
2. The photo note told it the photo was on the resident's open ticket: "[... התמונה נשמרה במערכת ומצורפת
   לקריאה שלו: לקריאה הפתוחה אם יש כזאת, אחרת לקריאה שתיפתח עכשיו ...]". It is not. store_media files a
   photo on a ticket opened from that number in the last two hours, and an older open ticket never gets
   it. The bot said what it had been told.

WHAT CHANGES.
- A tool, add_request_detail, at the end of the tool row: the same call to the function as
  get_request_status. Its text says when (something new about a ticket that is still open: which one,
  where exactly, what they did, a photo for it), that it appends their words and attaches the photos this
  number sent in the last hour, and that only what it answers was added. It is not a message to anyone.
  The function (debt-tools v135) keeps it to the sender's own open tickets on WhatsApp.
- The photo note says only what is true: the photo is saved, it goes on a ticket when one is opened or
  when what the resident adds goes on an open ticket of theirs, and only the tool's answer says so.
- notify_team's text: something new about an open ticket is add_request_detail's; a note never changes
  a ticket.
- Memory epoch 89 -> 90: the owner's buffer holds the two false claims, ready to be copied back.
Not changed: the prompt, the guards, Send.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py, as n8n_whatsapp_ionly.py did.
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

EPOCH = 90
OLD_KEY = "={{ $json.to }}-89"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-29oct-before-addto.json")
NL = chr(10)

TOOL = "add_request_detail"
POSITION = [3120, 420]                    # the end of the tool row, on the 240 x 60 grid
TOOL_DESCRIPTION = (
    "Add something new to a ticket of the resident's that is still open: which one exactly, where, since "
    "when, what they did about it, or a photo they sent for it. It appends their words to that ticket, "
    "never replacing what is there, and attaches the photos this number sent in the last hour that are on "
    "no ticket yet. Pass the ticket's reference (get_request_status gives it; never a guessed one) and the "
    "detail in Hebrew, in their words. Returns `ok` with the reference, and `photos_attached` with how many "
    "photos went on it. Only what it answers was added: their words are on the ticket once it returns `ok`, "
    "and a photo is on it only when `photos_attached` says so. `closed`: the ticket is no longer open, and "
    "a fault that is back is a new ticket (open_request). `not found`: it is not one of theirs. A new fault "
    "is open_request's, not this. It is not a message to anyone: the ticket holds it, so say what you "
    "added, not who will see it.")
JSON_BODY = (
    "={{ JSON.stringify({ message: { call: { id: 'wa:' + $('Sort').first().json.to, assistantOverrides: "
    "{ variableValues: { phone: $('Sort').first().json.to } } }, toolCalls: [{ id: 'wa', function: { name: "
    "'add_request_detail', arguments: { reference: $fromAI('reference', \"The reference of the resident's "
    "open ticket, as get_request_status gave it.\", 'string'), detail: $fromAI('detail', \"What is new about "
    "it, in Hebrew, in the resident's own words: which one, where, what they did. Not a summary of the "
    "ticket.\", 'string') } } }] } }) }}")

PHOTO_OLD = ("הדייר צירף תמונה להודעה הזאת. התמונה נשמרה במערכת ומצורפת לקריאה שלו: לקריאה הפתוחה אם יש "
             "כזאת, אחרת לקריאה שתיפתח עכשיו.")
PHOTO_NEW = ("הדייר צירף תמונה להודעה הזאת, והיא נשמרה במערכת. היא נכנסת לקריאה כשנפתחת קריאה, או כשמה "
             "שהוא מוסיף נכנס לקריאה פתוחה שלו, ורק התשובה של הכלי אומרת אם היא נכנסה.")
NOTE_OLD = "a fault is open_request's; a ticket's status is get_request_status's. Those you do yourself."
NOTE_NEW = ("a fault is open_request's; a ticket's status is get_request_status's; and something new about a "
            "ticket that is still open (a detail, what they did, a photo) is add_request_detail's, because a "
            "note never changes a ticket. Those you do yourself.")


def addto(wf):
    """The workflow with the tool, the true photo note and notify_team's clause. Not memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    if TOOL in by:
        sys.exit("REFUSING: the workflow already has a node named %r." % TOOL)
    agent = by["Answer the resident"]["parameters"]
    agent["text"] = once(agent["text"], PHOTO_OLD, PHOTO_NEW)
    note = by["notify_team"]["parameters"]
    note["toolDescription"] = once(note["toolDescription"], NOTE_OLD, NOTE_NEW)

    tool = copy.deepcopy(by["get_request_status"])   # the same call to the function, the same credential
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
        sys.exit("REFUSING: the memory key is %r, not epoch 89's. Read live first." % key)

    new = addto(live)
    nb = {n["name"]: n for n in new["nodes"]}
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    worse = sorted(layout_complaints(new["nodes"]) - layout_complaints(live["nodes"]))
    if worse:
        sys.exit("REFUSING TO PATCH. New placement problems:" + NL + "    " + (NL + "    ").join(worse))
    inject = lambda wf: {n["name"]: n for n in wf["nodes"]}["Answer the resident"]["parameters"]["text"]
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (unchanged: %s)" % (W.epoch_hash(prompt_of(new)), prompt_of(new) == prompt_of(live)))
    print("inject   : %s -> %s" % (W.epoch_hash(inject(live)), W.epoch_hash(inject(new))))
    print("tools    : %s -> %s (notify_team's text; %s is outside the hash, pinned by the gate)"
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
    print("  %s %s; inject %s (want %s); memory key %s" % (
        TOOL, "present" if TOOL in bb else "MISSING", W.epoch_hash(inject(back)), W.epoch_hash(inject(new)),
        bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
