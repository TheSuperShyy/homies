# -*- coding: utf-8 -*-
"""A bank transfer from a phone call: the team's note says to send the account details (19 Nov 2026).

    python scripts/n8n_handover_bankvoice.py             # dry run
    python scripts/n8n_handover_bankvoice.py --apply     # write it
    python scripts/n8n_handover_bankvoice.py --restore   # put the snapshot back

WHY. The owner: "ok give the phone line the same transfer as whatsapp". On a phone call the inbound agent's note is
a voice note: the call is over, so the note's last line tells staff how to reach the caller ("מתקשרים לדייר למספר
שלמעלה"). For a bank transfer what they owe the caller is the account details, so with a number the line says to
send the building's account details to that number, on WhatsApp or by phone. With no number it is the same line as
any voice note (the address, or nothing left). WhatsApp notes are untouched: they already say "send the details
here".

WHAT CHANGES: "Homies — Hand to a person" (oB66atFlWwtkSGgN), node "Decide the routing", one line. The same edit is
in n8n_handover.py's DECIDE, the source; the patcher refuses unless live's edited code equals it.
"""
import copy
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

HANDOVER_ID = "oB66atFlWwtkSGgN"
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-handover-live-19nov-before-bankvoice.json")

EDITS = (
    ("    const reach = phone ? 'מתקשרים לדייר' + now_ + ' למספר שלמעלה.'\n",
     "    // 19 Nov (n8n_handover_bankvoice.py): a bank transfer owes the caller the account details.\n"
     "    const reach = (phone && reason === 'bank_transfer')\n"
     "                ? 'שולחים לדייר את פרטי החשבון של הבניין שלו, בוואטסאפ או בטלפון, למספר שלמעלה.'\n"
     "                : phone ? 'מתקשרים לדייר' + now_ + ' למספר שלמעלה.'\n"),
)


def edit(code):
    for old, new in EDITS:
        assert code.count(old) == 1, "anchor not found exactly once: %r" % old[:60]
        code = code.replace(old, new, 1)
    return code


def main():
    import n8n_handover as H
    if "--restore" in sys.argv:
        snap = json.load(open(SNAPSHOT, encoding="utf-8"))
        W.api("PUT", "/api/v1/workflows/%s" % HANDOVER_ID, {"name": snap["name"], "nodes": snap["nodes"],
              "connections": snap["connections"], "settings": snap.get("settings", {})})
        print("restored %s from %s" % (HANDOVER_ID, os.path.relpath(SNAPSHOT, W.ROOT)))
        return
    live = W.api("GET", "/api/v1/workflows/%s" % HANDOVER_ID)
    code = {n["name"]: n for n in live["nodes"]}["Decide the routing"]["parameters"]["jsCode"]
    if "n8n_handover_bankvoice.py" in code:
        print("Nothing to do. The voice note already says to send the account details.")
        return
    new = edit(code)
    if new.strip() != H.DECIDE.strip():
        sys.exit("REFUSING: the would-be routing code is not n8n_handover.py's DECIDE. Edit the script first.")
    print("handover : %s (%s) 'Decide the routing' %d -> %d chars" % (live["name"], HANDOVER_ID, len(code), len(new)))
    if "--apply" not in sys.argv:
        print("\nDry run. Re-run with --apply to write it.")
        return
    if not os.path.exists(SNAPSHOT):
        io.open(SNAPSHOT, "w", encoding="utf-8").write(json.dumps(live, ensure_ascii=False, indent=1))
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    nodes = copy.deepcopy(live["nodes"])
    for n in nodes:
        if n["name"] == "Decide the routing":
            n["parameters"]["jsCode"] = new
    W.api("PUT", "/api/v1/workflows/%s" % HANDOVER_ID, {"name": live["name"], "nodes": nodes,
          "connections": live["connections"], "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % HANDOVER_ID)
    bc = {n["name"]: n for n in back["nodes"]}["Decide the routing"]["parameters"]["jsCode"]
    print("written  : active=%s, routing %s" % (back.get("active"), "as written" if bc == new else "DIFFERS"))


if __name__ == "__main__":
    main()
