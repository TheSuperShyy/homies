# -*- coding: utf-8 -*-
"""Gas gets no ticket, only "report it to the gas company" (5 Nov 2026, epoch 95). Yariv's change 2.

    python scripts/n8n_whatsapp_gas.py              # dry run
    python scripts/n8n_whatsapp_gas.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_gas.py --apply      # write it
    python scripts/n8n_whatsapp_gas.py --restore    # put the snapshot back

WHY. The client review of 4 Nov (local/meetings/2026-11-04-homies-agent-review.md,
36:11-37:10): when a resident reports gas, the bot must not open a call. It tells
the resident to report it to the gas company, and Yariv wants the wording fixed.
The owner was offered two lines on 5 Nov and did not pick; line 2 is the one
taken, because Send's danger step cuts line 1's "מטפלת" ("handles it") as a
promise of action whenever the chat had an urgent ticket shortly before, as the
owner's own test chat does. Line 2 passes that step in every case (a case in
check_whatsapp_rules.js holds it).

WHERE GAS WAS, before this. The prompt never named it; the tools did:
  - notify_team: "anybody reporting gas, fire, flooding, or water near
    electricity. Reason `emergency`." An emergency note also makes debt-tools'
    backstop open a needs_review ticket, mirrored into OXS for a mirrored number;
  - open_request's urgency gloss: "Use emergency only for flooding, fire, gas or
    someone trapped in a lift."
And the prompt's "דייר לא נשלח ממך לשום מקום" forbids sending anyone elsewhere.

WHAT CHANGES:
  - the prompt: "except gas" on the no-sending-elsewhere sentence, and one
    sentence at the end of the danger paragraph, where "what you have to give"
    is the urgent ticket: with gas, what he has to give is the line, word for
    word, with no ticket, no note and no address question. Everything else in
    that paragraph stands for gas too: no safety advice, no what to do;
  - notify_team: gas leaves the emergency list, with "never for gas";
  - open_request's urgency: gas leaves it, with "gas is never a ticket".
Plus the memory: epoch 94 -> 95. The tools hash moves too (notify_team).
A person in danger, a stuck lift, fire and flooding are unchanged. The phone
agent is unchanged (the owner, 5 Nov: chatbot first). n8n_whatsapp.py's TOOLS
is not folded (EPOCH_COVERS says so), so it still lists gas; live is the source.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py, then
n8n_uchat.py --apply carries it to the UChat copy, the bot in use.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 95
OLD_KEY = "={{ $json.to }}-94"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-05nov-before-gas.json")

# Line 2 of the two offered on 5 Nov, from the meeting's own wording.
GAS_LINE = ("במקרה של גז, צריך לפנות לחברת הגז שמספקת את הגז לבניין ולדווח לה ישירות. "
            "יש עוד משהו בבניין שאני יכול לבדוק בשבילך?")

PROMPT_EDITS = [
    ("דייר לא נשלח ממך לשום מקום.",
     "דייר לא נשלח ממך לשום מקום, חוץ ממקרה של גז."),
    ("דייר שאומר שהוא לא רוצה קריאה לא מקבל קריאה ולא מקבל שכנוע: מילה קצרה שמקבלת את זה.",
     "דייר שאומר שהוא לא רוצה קריאה לא מקבל קריאה ולא מקבל שכנוע: מילה קצרה שמקבלת את זה. "
     "בגז זה אחרת, וזאת החלטה של ההנהלה: על ריח גז, דליפת גז או כל תקלה בגז אתה לא פותח קריאה, "
     "לא רושם הערה ולא שואל באיזה בניין, ומה שיש לך לתת הוא רק זה, מילה במילה: \"" + GAS_LINE + "\""),
]
TOOL_EDITS = {
    "notify_team": [
        ("toolDescription",
         "anybody reporting gas, fire, flooding, or water near electricity. Reason `emergency`.",
         "anybody reporting fire, flooding, or water near electricity. Reason `emergency`. Never for gas: "
         "a gas report gets no note and no ticket, only the line about the gas company."),
    ],
    "open_request": [
        ("jsonBody",
         "Use emergency only for flooding, fire, gas or someone trapped in a lift.",
         "Use emergency only for flooding, fire or someone trapped in a lift. Gas is never a ticket."),
    ],
}


def gas(wf):
    """The workflow with every edit above; each anchor must occur exactly once. Does not touch memory."""
    import copy
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    opts = by["Answer the resident"]["parameters"]["options"]
    sm = opts["systemMessage"]
    for old, new in PROMPT_EDITS:
        sm = once(sm, old, new)
    opts["systemMessage"] = sm
    for tool, edits in TOOL_EDITS.items():
        p = by[tool]["parameters"]
        for key, old, new in edits:
            p[key] = once(p[key], old, new)
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and GAS_LINE in prompt_of(live):
        print("Nothing to do. Live already sends gas to the gas company, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 94's. Read live first." % key)

    new = gas(live)
    nb = {n["name"]: n for n in new["nodes"]}
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("tools    : %s -> %s" % (W.epoch_hash(tools_of(live)), W.epoch_hash(tools_of(new))))
    print("memory   : %s -> %s (every buffer starts fresh)" % (OLD_KEY, NEW_KEY))
    print("changed  : %s" % ", ".join(n["name"] for n in new["nodes"] if n != by[n["name"]]))
    left = [n["name"] for n in new["nodes"]
            if any(w in str(n.get("parameters", {})) for w in ("reporting gas", "fire, gas"))]
    assert not left, "gas is still an emergency in: %s" % left

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
    print("  prompt %s (want %s); tools %s (want %s); memory key %s"
          % (W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)), W.epoch_hash(tools_of(back)),
             W.epoch_hash(tools_of(new)), bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
