# -*- coding: utf-8 -*-
"""The live bot's typing indicator, moved to the owner's Israeli number for the move back to Chatwoot
(10 Nov 2026).

    python scripts/n8n_whatsapp_tochatwoot.py              # dry run
    python scripts/n8n_whatsapp_tochatwoot.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_tochatwoot.py --apply      # write it
    python scripts/n8n_whatsapp_tochatwoot.py --restore    # put the snapshot back

WHY. The owner, 10 Nov, after the after-hours check passed: "move to the chatwoot now that it passed".
The number the residents write to is the owner's Israeli number, which has run through UChat since
3 Nov. Chatwoot's inbox 1 had the US test number, whose WhatsApp account is blocked for anything we
start (141006), so the move puts the Israeli number into inbox 1 the way 2 Nov moved the test number:
the channel through its own model, then Chatwoot's register_callback (WORKLOG 10 Nov). Inbound and
replies go through Chatwoot and name no number. Only the two typing nodes call Meta with the
phone-number id in the URL.

WHAT CHANGES. "Show typing" and "Show typing again" call the Israeli number's id (`UCHAT_WA_PHONE_ID`
in .env), with the credential the UChat copy's typing nodes use (`UCHAT_N8N_CRED_TYPING`), which
answered `success: true` on that number all day on 10 Nov. Nothing else: no text a model reads, so
the memory epoch stays. Both nodes continue on error, so a wrong id or key only ever costs the dots.

The snapshot is in local/ (ignored by git), with the webhook secret replaced. It goes through
scripts/check_whatsapp_rules.py like every change: `--dump F`, `check_whatsapp_rules.py --candidate F
--replay`, then `--apply` and the check on live.
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
from n8n_whatsapp_newnumber import TYPING, URL_ID, WORKFLOW_ID  # noqa: E402

SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-10nov-before-tochatwoot.json")


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


def state(wf):
    by = {n["name"]: n for n in wf["nodes"]}
    return {name: (URL_ID.search(by[name]["parameters"]["url"]).group(2),
                   ((by[name].get("credentials") or {}).get("httpHeaderAuth") or {}).get("id"))
            for name in TYPING}


def main():
    if "--restore" in sys.argv:
        return restore()
    e = W.env()
    new_id = e.get("UCHAT_WA_PHONE_ID", "").strip()
    cred_id = e.get("UCHAT_N8N_CRED_TYPING", "").strip()
    if not new_id.isdigit() or not cred_id:
        sys.exit("UCHAT_WA_PHONE_ID or UCHAT_N8N_CRED_TYPING is missing from .env.")
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    now = state(live)
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("typing   : %s" % ", ".join("%s -> ..%s (cred %s)" % (n, i[-3:], c) for n, (i, c) in now.items()))
    if all(i == new_id and c == cred_id for i, c in now.values()):
        print("Nothing to do. Both typing nodes already call the Israeli number with its credential.")
        return

    new = json.loads(json.dumps(live))
    for n in new["nodes"]:
        if n["name"] in TYPING:
            n["parameters"]["url"] = URL_ID.sub(lambda m: m.group(1) + new_id + m.group(3), n["parameters"]["url"])
            cred = n["credentials"]["httpHeaderAuth"]
            cred["id"] = cred_id
            cred.pop("name", None)
    changed = [n["name"] for n, o in zip(new["nodes"], live["nodes"]) if n != o]
    assert changed and set(changed) <= set(TYPING), changed
    print("would be : %s" % ", ".join("%s -> ..%s (cred %s)" % (n, i[-3:], c) for n, (i, c) in state(new).items()))
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
    print("\nwritten  : %d nodes, active=%s, typing %s"
          % (len(back["nodes"]), back.get("active"),
             ", ".join("..%s/%s" % (i[-3:], c) for i, c in state(back).values())))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
