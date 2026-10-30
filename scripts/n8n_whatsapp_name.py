# -*- coding: utf-8 -*-
"""Every WhatsApp ticket carries the name of whoever reported it (30 Oct 2026, morning, epoch 91).

    python scripts/n8n_whatsapp_name.py              # dry run
    python scripts/n8n_whatsapp_name.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_name.py --apply      # write it
    python scripts/n8n_whatsapp_name.py --restore    # put the snapshot back

WHY. Asked whether a ticket stores who opened it, the answer was: the number and the flat, and a link
to the tenant's record when the number is on file, but no name on the ticket, so the dashboard shows a
number. The owner: "ok we need to include the name in that wtf". Feature 17 (22 Oct, the owner: "before
we can open a ticket we should include the name") made the function refuse a ticket without a name, but
only on voice: this tool could not send one. Since 22 Oct 7 of 9 call tickets carry a name and 0 of 2
WhatsApp tickets.

WHAT CHANGES, with debt-tools v138 (NAME_REQUIRED_CHANNELS voice,whatsapp):
- The function names a WhatsApp ticket from the record when the sender's number is on file, so a known
  tenant is never asked; a name they gave comes first unless it is part of the one on file. An unknown
  number gets `need_name`, and an emergency opens at once, name or not.
- open_request here gains `reporter_name` and `name_declined`, as the voice agent's tool has them, and
  its text says when to ask: only after `need_name`, once, in a sentence with whatever else is missing.
- Memory epoch 90 -> 91: the tool text changed.
Not changed: the prompt, the inject, the guards, Send.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py.
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

EPOCH = 91
OLD_KEY = "={{ $json.to }}-90"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-29oct-before-name.json")

BODY_AT = "One of low/normal/high/emergency.\", 'string')"
BODY_ADD = (
    ", reporter_name: $fromAI('reporter_name', \"The name of the person reporting, as they wrote it in this "
    "chat. Leave it empty rather than guess: a tenant on file for their number is named from the record.\", "
    "'string'), name_declined: $fromAI('name_declined', \"true only when they were asked for their name, "
    "heard once that the ticket needs the name of whoever reported it, and still would not give it.\", "
    "'boolean')")
DESC_AT = "A resident who is handed a four-point form usually answers none of it."
DESC_ADD = (
    "\nIt also needs who is reporting. A tenant on file for the number they write from is named from the "
    "record, so you send no name and never ask them for one. When it opens nothing and answers need_name, "
    "nobody is on file for that number: ask for their full name, once, in a sentence with whatever else is "
    "still missing, and call again with it as reporter_name. Someone who will not give it, after hearing "
    "once that the ticket needs the name of whoever reported it, still gets the ticket: name_declined true. "
    "An emergency never waits for a name: it opens without one.")


def name(wf):
    """The workflow with open_request's two name fields and its paragraph. Not memory."""
    out = copy.deepcopy(wf)
    p = {n["name"]: n for n in out["nodes"]}["open_request"]["parameters"]
    p["jsonBody"] = once(p["jsonBody"], BODY_AT, BODY_AT + BODY_ADD)
    p["toolDescription"] = once(p["toolDescription"], DESC_AT, DESC_AT + DESC_ADD)
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and "reporter_name" in by["open_request"]["parameters"]["jsonBody"]:
        print("Nothing to do. Live's open_request already sends the name, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 90's. Read live first." % key)

    new = name(live)
    nb = {n["name"]: n for n in new["nodes"]}
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (unchanged: %s)" % (W.epoch_hash(prompt_of(new)), prompt_of(new) == prompt_of(live)))
    print("tools    : %s -> %s" % (W.epoch_hash(tools_of(live)), W.epoch_hash(tools_of(new))))
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
    print("  tools %s (want %s); reporter_name %s; memory key %s" % (
        W.epoch_hash(tools_of(back)), W.epoch_hash(tools_of(new)),
        "sent" if "reporter_name" in bb["open_request"]["parameters"]["jsonBody"] else "MISSING",
        bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
