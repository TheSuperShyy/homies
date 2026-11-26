# -*- coding: utf-8 -*-
"""An urgent ticket from an earlier conversation no longer puts Send's danger step into emergency mode (26 Nov; danger v11).

    python scripts/n8n_whatsapp_dangerage.py              # dry run
    python scripts/n8n_whatsapp_dangerage.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_dangerage.py --apply      # write it
    python scripts/n8n_whatsapp_dangerage.py --restore    # put the snapshot back

WHY. Run 211121 (26 Nov, 15:09 UTC, Yariv's phone, conversation 54, on Homies' own number): "יש לי בעיה יש כאן רעש
בבניין מה ניתן לעשות?". The model wrote "אוי, רעש זה באמת מפריע. מאיפה נשמע שהוא מגיע? זה משהו מהמערכות של הבניין
או ממקור אחר?", no tool. Yariv got "אוי, רעש זה באמת מפריע. זה משהו מהמערכות של הבניין או ממקור אחר? הקריאה הדחופה
שלך פתוחה, מספר 255-1445-26." The owner: "wtf is this why is there no like elaboration?".
  - Send's danger step (danger v10) counts the chat as an emergency when Sort's last_bot or the chat's last three
    outbound rows (`Anything newer?`) speak of an urgent ticket. The second of those rows was the bot's line of
    11 Nov, 16:20 UTC ("פתחתי עכשיו קריאה דחופה על הנזילה בבניין (מספר 255-1445-26)"), Yariv's leak test, 15 days
    old and still open: the rows carry no time, and his phone had written little since.
  - In emergency mode its arrival filter read "מגיע" in "מאיפה נשמע שהוא מגיע?" as a promise that someone is on the
    way, cut the question, and, since something went, added the urgent ticket's line.

WHAT CHANGES, in Send only (danger v10 -> v11):
  An urgent ticket counts only inside the current conversation. Michael introduces himself ("כאן מיכאל מהומי'ז") at
  the start of every conversation (the menu after a hello, or the first beat after 8 quiet hours, greetgap v1), so:
    - a reply that carries the introduction starts a conversation: no earlier row counts;
    - otherwise the outbound rows count newest first up to the first introduction, three at most;
    - last_bot counts unless it is the introduction (or the reply carries one).
  The ticket number for the added line is looked up in the same window. Inside a conversation nothing changes.
Not changed: the arrival filter's words (a question with "מגיע" inside a real emergency can still be cut; one cause
at a time), the prompt, the tools, memory (no epoch: Send's code is not text a model reads).

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
from n8n_whatsapp_ionly import WORKFLOW_ID, once, snapshot, restore  # noqa: E402

SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-26nov-before-dangerage.json")

EDITS = (
    ("const dv = 'danger v10';", "const dv = 'danger v11';"),
    ("const lb = [String(G.last_bot || '')].concat(outs.slice(0, 3)).join(' ');",
     "const INTRO = /כאן מיכאל מהומי/; const fresh = INTRO.test(s); const recent = []; "
     "if (!fresh) { for (const b of outs) { if (INTRO.test(b)) break; recent.push(b); if (recent.length >= 3) break; } } "
     "const lastBot = (fresh || INTRO.test(String(G.last_bot || ''))) ? '' : String(G.last_bot || ''); "
     "const lb = [lastBot].concat(recent).join(' ');"),
    ("if (!ref) { const m = s.match(REF) || String(G.last_bot || '').match(REF); if (m) ref = m[m.length - 1]; }",
     "if (!ref) { const m = s.match(REF) || lastBot.match(REF); if (m) ref = m[m.length - 1]; }"),
    ("if (!ref) { for (const b of outs) { const m = b.match(REF); if (m) { ref = m[m.length - 1]; break; } } }",
     "if (!ref) { for (const b of recent) { const m = b.match(REF); if (m) { ref = m[m.length - 1]; break; } } }"),
)
CHANGED = ["Send"]


def dangerage(wf):
    out = copy.deepcopy(wf)
    send = {n["name"]: n for n in out["nodes"]}["Send"]
    body = send["parameters"]["jsonBody"]
    for old, new in EDITS:
        body = once(body, old, new)
    send["parameters"]["jsonBody"] = body
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    body = by["Send"]["parameters"]["jsonBody"]
    if "const dv = 'danger v11';" in body:
        print("Nothing to do. Send already runs danger v11.")
        return
    if "const dv = 'danger v10';" not in body:
        sys.exit("REFUSING: Send is not on danger v10. Read live first.")
    new = dangerage(live)
    changed = [n["name"] for n in new["nodes"] if n != by[n["name"]]]
    if sorted(changed) != sorted(CHANGED):
        sys.exit("REFUSING: unexpected nodes would change: %s" % changed)
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("changed  : Send (danger v10 -> v11: an urgent ticket counts only inside the current conversation)")
    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        NP.dump(new["nodes"], new["connections"], path)
        print("dumped   : %s (the would-be workflow, secret replaced)" % path)
    if "--apply" not in sys.argv:
        print("\nDry run. Re-run with --apply to write it.")
        return
    if snapshot(live, SNAPSHOT):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": new["nodes"], "connections": new["connections"],
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    bb = {n["name"]: n for n in back["nodes"]}
    print("\nwritten  : %d nodes, active=%s; Send %s" % (
        len(back["nodes"]), back.get("active"),
        "as written" if bb["Send"]["parameters"] == {n["name"]: n for n in new["nodes"]}["Send"]["parameters"] else "DIFFERS"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
