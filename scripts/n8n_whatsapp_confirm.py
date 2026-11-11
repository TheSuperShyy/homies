# -*- coding: utf-8 -*-
"""A ticket only after the resident's yes; anything urgent is an emergency; our line is never a copy (11 Nov 2026,
night, epoch 106; the copy guard's repeat v2).

    python scripts/n8n_whatsapp_confirm.py              # dry run
    python scripts/n8n_whatsapp_confirm.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_confirm.py --apply      # write it
    python scripts/n8n_whatsapp_confirm.py --restore    # put the snapshot back

WHY. Minutes after epoch 105 (16:15 UTC):
  - Yariv wrote "אני חייב דחוף מישהו / כל הבניין נזילת מים / מה עושים" (173670, 16:19). Michael opened urgent ticket
    255-1445-26 with urgency high, the value left once epoch 105 took `emergency` away, and asked where the leak was.
    The owner, sending the screenshot: "i told you all types of emergency like flooding, and stuff that needs urgent
    call, also we need to make sure we dont open a service call without confirmation".
  - The owner's own lift test (173705, 16:31) got "סליחה, משהו השתבש לי בתשובה". Both drafts were a caring word and
    our line word for word, a near-copy of the smoke reply sent at 16:19, so Reply usable?'s `repeat` sent them back
    and Mend put its fixed line in their place. An emergency turn has no tool since epoch 105, and only a tool
    exempted a reply from that guard.

WHAT CHANGES, in one write:
  The prompt    an emergency is anything urgent that cannot wait, a big leak or water running in the building
                included; a lift that is down with nobody stuck is a fault, not an emergency. A service call opens
                only after he says yes: before any ticket Michael asks briefly whether to open it (with the building
                and flat in the same question when he lacks them); an explicit request is a yes. Water from the
                common parts gets the same question.
  The tools     open_request: never for anything urgent, never without the resident's yes, and a payment
                arrangement waits for the yes too; urgency names a lift that is down "high". notify_team: anything
                urgent that cannot wait gets no note.
  Try again     its "if there is something to open, open it now" waits for his yes.
  The guard     `repeats` in Reply usable?, Claimed a ticket?, Mend the reply and Try again ("repeat v2"): a text
                that gives our line, 077-6687949, is never a copy.
  Memory        epoch 105 -> 106.
Not changed: Send (danger v8, line v1), gas, the inject. The incoming phone agent's twin is owed: it still opens
an urgent ticket, and opens tickets without asking.

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
from n8n_whatsapp_hotline import expr_compiles  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 106
OLD_KEY = "={{ $json.to }}-105"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-11nov-before-confirm.json")

# The prompt, each edit exactly once (docs/features/11-whatsapp-bot/prompt.md carries the result).
PROMPT_EDITS = (
    ("תקלה ברכוש המשותף או במערכות הבניין, מעלית, חדר מדרגות, תאורה בשטחים המשותפים, דלת כניסה, צנרת ראשית, גג, "
     "אינטרקום, גינה: אתה פותח קריאת שירות עם הכלי שיש לך לזה.",
     "תקלה ברכוש המשותף או במערכות הבניין, מעלית, חדר מדרגות, תאורה בשטחים המשותפים, דלת כניסה, צנרת ראשית, גג, "
     "אינטרקום, גינה: אתה פותח עליה קריאת שירות עם הכלי שיש לך לזה, אבל רק אחרי שהוא אמר שהוא רוצה אותה, וזאת "
     "החלטה של ההנהלה. לפני כל קריאה אתה שואל אותו בקצרה אם לפתוח אותה, ואם חסרים לך הבניין והדירה, באותה שאלה. "
     "מי שכבר ביקש במפורש שתפתח קריאה כבר אמר כן."),
    ("וכשיש לך מה קרה ובאיזה בניין, הכלי בא לפני המילים.",
     "וכשיש לך מה קרה, באיזה בניין, והכן שלו, הכלי בא לפני המילים."),
    ("אם כן, זאת תקלה של הבניין, ופותחים עליה קריאה.",
     "אם כן, זאת תקלה של הבניין, ואתה שואל אותו אם לפתוח עליה קריאה."),
    ("מקרה חירום, כמו מישהו בסכנה או שנפגע, מישהו תקוע במעלית, שריפה, עשן, הצפה או מים ליד חשמל, שייך כולו למוקד "
     "החירום הטלפוני שלנו, שקיים בדיוק בשביל מקרים כאלה, וזאת החלטה של ההנהלה: אתה לא פותח קריאה, גם כשזאת תקלה "
     "ברכוש המשותף, לא רושם הערה ולא שואל באיזה בניין או באיזו דירה.",
     "מקרה חירום, כלומר כל דבר דחוף שלא יכול לחכות, כמו מישהו בסכנה או שנפגע, מישהו תקוע במעלית, שריפה, עשן, "
     "הצפה, נזילה גדולה או מים שזורמים בבניין, ומים ליד חשמל, שייך כולו למוקד החירום הטלפוני שלנו, שקיים בדיוק "
     "בשביל מקרים כאלה, וזאת החלטה של ההנהלה: אתה לא פותח קריאה, גם כשזאת תקלה ברכוש המשותף, לא רושם הערה ולא "
     "שואל באיזה בניין או באיזו דירה. מעלית שלא עובדת כשאף אחד לא תקוע בה היא לא מקרה חירום, אלא תקלה כמו כל "
     "תקלה."),
)

# The tools: (node, parameter, old, new), each anchor exactly once.
TOOL_EDITS = (
    ("open_request", "toolDescription",
     "Never for an emergency: a person in danger or hurt, someone trapped in a lift, fire, smoke, flooding or water "
     "near electricity gets our emergency line only, with no ticket and no note, even when it is a fault in the "
     "common parts. Neither is gas. A note (notify_team) does NOT open a ticket.\n",
     "Never for an emergency, which is anything urgent that cannot wait: a person in danger or hurt, someone trapped "
     "in a lift, fire, smoke, flooding, a big leak or water running in the building, water near electricity. It gets "
     "our emergency line only, with no ticket and no note, even when it is a fault in the common parts. A lift that "
     "is down with nobody inside is a fault, not an emergency. Neither is gas a ticket.\n"
     "Never without the resident's yes: before opening a ticket, ask them briefly whether to open it, and call this "
     "only once they say yes. Someone who asked you in so many words to open one has said yes. A note (notify_team) "
     "does NOT open a ticket.\n"),
    ("open_request", "toolDescription", "A payment ARRANGEMENT is a ticket straight away.",
     "A payment ARRANGEMENT is a ticket without trying the link first, once they say yes."),
    ("open_request", "toolDescription", "Call it as soon as you know WHAT is wrong and WHERE — it verifies",
     "Call it as soon as you know WHAT is wrong and WHERE and they have said yes — it verifies"),
    ("open_request", "jsonBody",
     "Infer this; never ask the resident for it. An emergency is never a ticket, and neither is gas. "
     "One of low/normal/high.",
     "Infer this; never ask the resident for it. Anything urgent that cannot wait is an emergency and never a "
     "ticket, and neither is gas; a lift that is down with nobody inside is high. One of low/normal/high."),
    ("notify_team", "toolDescription", "fire, smoke, flooding, water near electricity, or gas gets no note",
     "fire, smoke, flooding, a big leak or water running in the building, water near electricity, anything else "
     "urgent that cannot wait, or gas gets no note"),
)

# Try again's note, wherever it says it: open now only once he said yes.
TRY_OLD = "אם יש מה לפתוח, תפתח עכשיו עם open_request"
TRY_NEW = "אם יש מה לפתוח והוא כבר אמר כן, תפתח עכשיו עם open_request"

# The copy guard, the same function in four nodes: our line is never a copy.
REPEAT_OLD = ("const repeats = (t) => { const n = normRep(t); if (!n) return false; return sentRep().some(b => "
              "nearRep(n, b)); };")
REPEAT_NEW = ("const repeats = (t) => { const rpv = 'repeat v2'; const n = normRep(t); if (!n || "
              "/0?77[-\\s]?668[-\\s]?7949/.test(String(t || ''))) return false; return sentRep().some(b => "
              "nearRep(n, b)); };")
REPEAT_NODES = ("Reply usable?", "Claimed a ticket?", "Mend the reply", "Try again")


def swap_strings(obj, old, new):
    """Replace `old` in every string inside obj (a node's parameters); returns (new obj, how many replaced)."""
    if isinstance(obj, str):
        return obj.replace(old, new), obj.count(old)
    if isinstance(obj, list):
        out, n = [], 0
        for x in obj:
            y, k = swap_strings(x, old, new)
            out.append(y)
            n += k
        return out, n
    if isinstance(obj, dict):
        out, n = {}, 0
        for key, x in obj.items():
            y, k = swap_strings(x, old, new)
            out[key] = y
            n += k
        return out, n
    return obj, 0


def confirm(wf):
    """The workflow with every edit above; each anchor where it must be. Does not touch memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    for name in REPEAT_NODES:
        if "const rpv = " in str(by[name]["parameters"]):
            sys.exit("REFUSING: %s already has repeat v2. Read live first." % name)
        assert "}}" not in REPEAT_NEW and "{{" not in REPEAT_NEW, "the edit would end an expression early"
        by[name]["parameters"], k = swap_strings(by[name]["parameters"], REPEAT_OLD, REPEAT_NEW)
        assert k == 1, "the copy guard is in %s %d times, not once" % (name, k)
    by["Try again"]["parameters"], k = swap_strings(by["Try again"]["parameters"], TRY_OLD, TRY_NEW)
    assert k >= 1, "Try again no longer says %r" % TRY_OLD
    agent = by["Answer the resident"]["parameters"]
    for old, new in PROMPT_EDITS:
        agent["options"]["systemMessage"] = once(agent["options"]["systemMessage"], old, new)
    for node, key, old, new in TOOL_EDITS:
        p = by[node]["parameters"]
        p[key] = once(p[key], old, new)
    return out, k


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and "const rpv = 'repeat v2'" in str(by["Reply usable?"]["parameters"]):
        print("Nothing to do. Live already asks before a ticket and sends anything urgent to our line, epoch %d."
              % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 105's. Read live first." % key)
    if W.MEMORY_EPOCH != EPOCH:
        sys.exit("REFUSING: n8n_whatsapp.MEMORY_EPOCH is %d, not %d. Move the repo first." % (W.MEMORY_EPOCH, EPOCH))

    new, tries = confirm(live)
    if prompt_of(new) != W.system_prompt():
        sys.exit("REFUSING: the would-be prompt is not docs/features/11-whatsapp-bot/prompt.md's. "
                 "Edit the document first; live follows it.")
    W.check_memory_epoch(prompt=prompt_of(new), tools=tools_of(new))
    nb = {n["name"]: n for n in new["nodes"]}
    for name in REPEAT_NODES:
        for k2, v in nb[name]["parameters"].items():
            if isinstance(v, str) and v.strip().startswith("={{"):
                expr_compiles(v, "%s.%s" % (name, k2))
    for c in nb["Reply usable?"]["parameters"]["conditions"]["conditions"]:
        if c["id"] == "repeat":
            expr_compiles(c["leftValue"], "Reply usable?.repeat")
    for c in nb["Claimed a ticket?"]["parameters"]["conditions"]["conditions"]:
        expr_compiles(c["leftValue"], "Claimed a ticket?.%s" % c.get("id"))
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("tools    : %s -> %s" % (W.epoch_hash(tools_of(live)), W.epoch_hash(tools_of(new))))
    print("guard    : repeat v2 in %s; Try again's 'open it now' waits for the yes (%d places)"
          % (", ".join(REPEAT_NODES), tries))
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
    print("  prompt %s (want %s); tools %s (want %s); memory key %s; repeat v2 in %d of %d nodes"
          % (W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)), W.epoch_hash(tools_of(back)),
             W.epoch_hash(tools_of(new)), bb["Conversation so far"]["parameters"]["sessionKey"],
             sum("const rpv = 'repeat v2'" in str(bb[n]["parameters"]) for n in REPEAT_NODES), len(REPEAT_NODES)))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
