# -*- coding: utf-8 -*-
"""The live bot's typing indicator, moved to the new WhatsApp test number (2 Nov 2026).

    python scripts/n8n_whatsapp_newnumber.py              # dry run
    python scripts/n8n_whatsapp_newnumber.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_newnumber.py --apply      # write it
    python scripts/n8n_whatsapp_newnumber.py --restore    # put the snapshot back

WHY. Since 31 Oct, ~14:43 UTC, our Meta system user cannot see the old test account
(1004244565865434) or its number at all (100/33, "does not exist ... missing permissions"). The
owner made a new test number in the HOMIES app: +1 555-045-9005, in "Test Messaging Account".
The owner, 2 Nov: "ok go". Chatwoot's inbox, the Meta routing and the PIN were moved first (WORKLOG
2 Nov). Inbound reaches the bot through Chatwoot, and replies go out through Chatwoot, so neither
names the number. Only the two typing nodes call Meta with the phone-number id in the URL.

WHAT CHANGES. "Show typing" and "Show typing again" get the new id from .env
(WHATSAPP_PHONE_NUMBER_ID). Nothing else: no text a model reads, so the memory epoch stays.
Both nodes continue on error, so a stale id only ever cost the indicator, never a reply.

The snapshot is in local/ (ignored by git), with the webhook secret replaced as the older ones were.
It goes through scripts/check_whatsapp_rules.py like every change: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, then `--apply` and the check on live.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
TYPING = ("Show typing", "Show typing again")
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-02nov-before-newnumber.json")
URL_ID = re.compile(r"(graph\.facebook\.com/v[\d.]+/)(\d+)(/messages)")


def snapshot(live):
    if os.path.exists(SNAPSHOT):
        return False
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    live = dict(live, staticData="<stripped: runtime state keyed by phone numbers>")
    text = json.dumps(live, ensure_ascii=False, indent=1)
    if secret:
        if secret not in text:
            sys.exit("The live workflow does not contain N8N_WEBHOOK_SECRET from .env, "
                     "so the snapshot's redaction would miss. Refusing to write it.")
        text = text.replace(secret, NP.PLACEHOLDER)
    os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
    with open(SNAPSHOT, "w", encoding="utf-8") as f:
        f.write(text)
    return True


def restore():
    snap = json.load(open(SNAPSHOT, encoding="utf-8"))
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    if not secret:
        sys.exit("N8N_WEBHOOK_SECRET is not in .env; the snapshot's Sort node would "
                 "go live with a placeholder secret. Refusing.")
    body = json.loads(json.dumps(snap, ensure_ascii=False).replace(NP.PLACEHOLDER, secret))
    W.api("PUT", "/api/v1/workflows/%s" % WORKFLOW_ID, {
        "name": body["name"], "nodes": body["nodes"],
        "connections": body["connections"], "settings": body.get("settings", {})})
    print("restored %s from %s (%d nodes)" % (WORKFLOW_ID, SNAPSHOT, len(body["nodes"])))


def ids(wf):
    by = {n["name"]: n for n in wf["nodes"]}
    return {name: URL_ID.search(by[name]["parameters"]["url"]).group(2) for name in TYPING}


def main():
    if "--restore" in sys.argv:
        return restore()
    new_id = W.env().get("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    if not new_id.isdigit():
        sys.exit("WHATSAPP_PHONE_NUMBER_ID in .env is not a phone-number id.")
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    now = ids(live)
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("typing   : %s" % ", ".join("%s -> %s" % (n, i) for n, i in now.items()))
    if all(i == new_id for i in now.values()):
        print("Nothing to do. Both typing nodes already call %s." % new_id)
        return

    new = json.loads(json.dumps(live))
    for n in new["nodes"]:
        if n["name"] in TYPING:
            n["parameters"]["url"] = URL_ID.sub(lambda m: m.group(1) + new_id + m.group(3), n["parameters"]["url"])
    changed = [n["name"] for n, o in zip(new["nodes"], live["nodes"]) if n != o]
    assert changed and set(changed) <= set(TYPING), changed
    print("would be : %s" % ", ".join("%s -> %s" % (n, i) for n, i in ids(new).items()))
    print("changed  : %s" % ", ".join(changed))

    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        NP.dump(new["nodes"], new["connections"], path)
        print("dumped   : %s (the would-be workflow, secret replaced)" % path)
    if "--apply" not in sys.argv:
        print("\nDry run. Re-run with --apply to write it.")
        return

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": new["nodes"], "connections": new["connections"],
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    print("\nwritten  : %d nodes, active=%s, typing %s" % (len(back["nodes"]), back.get("active"), ids(back)))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
