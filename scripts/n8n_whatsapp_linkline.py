# -*- coding: utf-8 -*-
"""The payment link goes out on a line of its own, as the model wrote it (18 Nov 2026; Send linkline v1).

    python scripts/n8n_whatsapp_linkline.py              # dry run
    python scripts/n8n_whatsapp_linkline.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_linkline.py --apply      # write it
    python scripts/n8n_whatsapp_linkline.py --restore    # put the snapshot back

WHY. The owner's one-conversation Grok run (18 Nov, 13:40 UTC, conversation 98, execution 190914) failed P2: the
link was not on a line of its own. The model had written it so ("...בבר כוכבא 23:\\n\\n<link>\\n\\nכשאתה נכנס
לקישור..."), as get_payment_link asks ("on a line of its own"). Send's first clean-up, `.replace(/\\s{2,}/g, ' ')`,
turns any run of two or more blanks into one space, so the blank lines around the link became spaces and the
handset got "...23: <link> כשאתה נכנס...". A single line break survives that step, which is why the question at
the end kept its own line.

WHAT CHANGES: a last step at the very end of Send, after every guard: a link is put on its own line, with a line
break before it unless one is already there and one after it when text follows; a comma, full stop, semicolon or
colon right after the link goes. The guards see the reply exactly as before (a first try that moved the link in the
clean-up step left a stray comma where the promise cutter had taken a clause after the link), and a reply with no
link comes out byte for byte as before. Not changed: the prompt, the tools, the memory key (a
code change: check_memory_epoch asks for no bump), and every other node.

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

SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-18nov-before-linkline.json")

URL = r"https?:\/\/[^\s]*[^\s.,;:!?)\]]"   # a link, never ending on punctuation
OLD_END = "})(); return JSON.stringify(body); })() }}"
NEW_END = (r"})(); body.content = ((s) => { const llv = 'linkline v1'; if (typeof s !== 'string' || s.indexOf('http') === -1) "
           r"return s; return s.replace(/(^|[^\n])[ \t]*(" + URL + r")/g, '$1\n$2')"
           r".replace(/(" + URL + r")[.,;:]?[ \t]+(?=\S)/g, '$1\n')"
           r".replace(/(" + URL + r")[.,;:]$/, '$1').replace(/^\n+/, ''); })(body.content); "
           r"return JSON.stringify(body); })() }}")


def linkline(wf):
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    p = by["Send"]["parameters"]
    if "linkline v" in p["jsonBody"]:
        sys.exit("REFUSING: Send already has linkline.")
    p["jsonBody"] = once(p["jsonBody"], OLD_END, NEW_END)
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    if "linkline v" in by["Send"]["parameters"]["jsonBody"]:
        print("Nothing to do. Send already puts the link on its own line (linkline v1).")
        return
    new = linkline(live)
    nb = {n["name"]: n for n in new["nodes"]}
    changed = [n["name"] for n in new["nodes"] if n != by[n["name"]]]
    if changed != ["Send"]:
        sys.exit("REFUSING: unexpected nodes would change: %s" % changed)
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("changed  : Send (linkline v1); memory key unchanged (%s)" % by["Conversation so far"]["parameters"]["sessionKey"])
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
    print("\nwritten  : %d nodes, active=%s; Send %s" % (
        len(back["nodes"]), back.get("active"),
        "as written" if bb["Send"]["parameters"] == nb["Send"]["parameters"] else "DIFFERS"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
