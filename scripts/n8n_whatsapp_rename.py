# -*- coding: utf-8 -*-
"""Spell the client's name the way the client spells it: הומיז -> הומי'ז.

    python scripts/n8n_whatsapp_rename.py            # dry run
    python scripts/n8n_whatsapp_rename.py --apply    # write it
    python scripts/n8n_whatsapp_rename.py --restore  # put the snapshot back

WHY, 17 SEP
The owner read our greeting back as *"its still homiz not homies"*. He is
right, and it is not a pronunciation problem: we have written הומיז since the
first prompt, and the client writes **הומי'ז** on their own site — 188 times
against 13, counted in docs/knowledge/site/. We have been spelling our client's
brand wrong in every message they send.

WHY THIS NEEDS A PATCHER AND NOT A PROMPT EDIT
The prompt is only one of the places the name lives. The live workflow also
carries it in:

  * the MENU body, which is the greeting the resident actually reads and the
    only copy the model never writes;
  * Sort's `content:` strings, which hand the model its own greeting back as
    conversation history — leave those behind and the model reads one spelling
    in its prompt and another in its memory, and copies whichever it likes;
  * Send's echo guards, `t.indexOf('היי 👋 כאן מיכאל מהומיז...')` and
    `/מיכאל מהומיז/`, which exist to stop the bot repeating its own greeting.
    Those match by EXACT TEXT. Rename the greeting without them and the guard
    silently stops firing — the protection reads as present and is not.

That last one is why a half-done rename is worse than none, and why this is one
pass over every copy rather than an edit where the complaint happened to land.

OLD BUFFERS ARE NOT A PROBLEM, and that is deliberate: the epoch moved to 36 in
the same change, so no conversation carrying the old spelling survives to be
matched against.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
OLD, NEW = "הומיז", "הומי'ז"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-17sep-before-rename.json")
PLACEHOLDER = "REPLACE_WITH_N8N_WEBHOOK_SECRET"


def snapshot(live):
    if os.path.exists(SNAPSHOT):
        return False
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    body = dict(live, staticData="<stripped: runtime state keyed by phone numbers>")
    text = json.dumps(body, ensure_ascii=False, indent=1)
    if secret:
        if secret not in text:
            sys.exit("The live workflow does not contain N8N_WEBHOOK_SECRET from .env, "
                     "so the snapshot's redaction would miss. Refusing to write it.")
        text = text.replace(secret, PLACEHOLDER)
    with open(SNAPSHOT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return True


def restore():
    snap = json.load(open(SNAPSHOT, encoding="utf-8"))
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    if not secret:
        sys.exit("N8N_WEBHOOK_SECRET is not in .env; the snapshot's Sort node would "
                 "go live with a placeholder secret. Refusing.")
    body = json.loads(json.dumps(snap, ensure_ascii=False).replace(PLACEHOLDER, secret))
    W.api("PUT", "/api/v1/workflows/%s" % WORKFLOW_ID, {
        "name": body["name"], "nodes": body["nodes"],
        "connections": body["connections"], "settings": body.get("settings", {})})
    print("restored %s from %s (%d nodes)" % (WORKFLOW_ID, SNAPSHOT, len(body["nodes"])))


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))

    hits = []
    for node in live["nodes"]:
        blob = json.dumps(node.get("parameters", {}), ensure_ascii=False)
        # The already-renamed spelling contains the old one as a substring, so
        # count only occurrences NOT already followed by the geresh.
        n = blob.replace("הומי'ז", "\x00").count(OLD)
        if n:
            hits.append((node["name"], n))

    if not hits:
        print("\nNothing to do. Every copy already reads %s." % NEW)
        return

    print("\nnodes carrying the old spelling:")
    for name, n in hits:
        print("  %-28s %d" % (name, n))
    print("\n  total %d occurrences -> %s" % (sum(n for _, n in hits), NEW))

    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    if snapshot(live):
        print("\nsnapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))

    for node in live["nodes"]:
        params = json.dumps(node.get("parameters", {}), ensure_ascii=False)
        # Guard the already-correct spelling through the replace, so a second
        # run is a no-op rather than producing הומי''ז.
        params = params.replace("הומי'ז", "\x00").replace(OLD, NEW).replace("\x00", "הומי'ז")
        node["parameters"] = json.loads(params)

    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": live["nodes"],
        "connections": live["connections"], "settings": live.get("settings", {}),
    })
    print("\nwritten. Re-run without --apply to confirm it reports nothing to do,\n"
          "then check the greeting on a real handset — the MENU body is the one\n"
          "copy no probe exercises, because the model never writes it.")


if __name__ == "__main__":
    main()
