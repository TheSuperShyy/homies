# -*- coding: utf-8 -*-
"""The live bot's typing indicator, moved to Homies' own number for the switch (prepared 23 Nov 2026).

    python scripts/n8n_whatsapp_tohomies.py              # dry run
    python scripts/n8n_whatsapp_tohomies.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_tohomies.py --apply      # make the credential (once), then write it
    python scripts/n8n_whatsapp_tohomies.py --restore    # put the snapshot back

WHY. The owner, 23 Nov: "so right now just prepare everything but dont disconnect everything". At the switch,
scripts/switch_to_homies.py moves Chatwoot's inbox 1 to Homies' number with Homies' token. Inbound and replies go
through Chatwoot and name no number; only the two typing nodes call Meta with a phone-number id in the URL, and
they need a key that reaches that number: Homies' token (HOMIES_WHATSAPP_TOKEN), not ours.

WHAT CHANGES. "Show typing" and "Show typing again" call their number's id (read from their WABA with their token),
with an n8n credential holding their token. --apply makes that credential once and keeps its id in .env
(HOMIES_N8N_CRED_TYPING). Nothing else: no text a model reads, so the memory epoch stays. Both nodes continue on
error, so a wrong id or key only ever costs the dots.

Like every WhatsApp change it goes through scripts/check_whatsapp_rules.py: `--dump F`,
`check_whatsapp_rules.py --candidate F --replay`, then `--apply` and the check on live. The snapshot is in local/
(ignored by git), with the webhook secret replaced.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_newnumber import TYPING, URL_ID, WORKFLOW_ID  # noqa: E402
from n8n_whatsapp_tochatwoot import state  # noqa: E402

SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-before-tohomies.json")
CRED_NAME = "WhatsApp Cloud API (Homies' own number) — typing"
CRED_ENV = "HOMIES_N8N_CRED_TYPING"


def their_phone_id(e):
    tok, waba = e.get("HOMIES_WHATSAPP_TOKEN", "").strip(), e.get("HOMIES_WHATSAPP_WABA_ID", "").strip()
    if not tok or not waba.isdigit():
        sys.exit("HOMIES_WHATSAPP_TOKEN / HOMIES_WHATSAPP_WABA_ID are not both set in .env.")
    q = urllib.parse.urlencode({"fields": "id", "access_token": tok})
    data = json.load(urllib.request.urlopen("https://graph.facebook.com/v21.0/%s/phone_numbers?%s" % (waba, q), timeout=30))
    ids = [p["id"] for p in data.get("data", [])]
    if len(ids) != 1:
        sys.exit("Their WABA lists %d numbers; expected exactly one." % len(ids))
    return ids[0]


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


def make_credential(e):
    cid = e.get(CRED_ENV, "").strip()
    if cid:
        return cid
    cid = W.api("POST", "/api/v1/credentials", {
        "name": CRED_NAME, "type": "httpHeaderAuth",
        "data": {"name": "Authorization", "value": "Bearer " + e["HOMIES_WHATSAPP_TOKEN"].strip()},
    })["id"]
    W.set_env(CRED_ENV, cid)
    print("credential: %s -> %s (their token is in n8n, not in the workflow)" % (CRED_NAME, cid))
    return cid


def main():
    if "--restore" in sys.argv:
        return restore()
    e = W.env()
    new_id = their_phone_id(e)
    cred_id = e.get(CRED_ENV, "").strip() or "<made at --apply>"
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    now = state(live)
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("typing   : %s" % ", ".join("%s -> ..%s (cred %s)" % (n, i[-3:], c) for n, (i, c) in now.items()))
    if all(i == new_id and c == cred_id for i, c in now.values()):
        print("Nothing to do. Both typing nodes already call Homies' number with their credential.")
        return

    def build(cid):
        new = json.loads(json.dumps(live))
        for n in new["nodes"]:
            if n["name"] in TYPING:
                n["parameters"]["url"] = URL_ID.sub(lambda m: m.group(1) + new_id + m.group(3), n["parameters"]["url"])
                cred = n["credentials"]["httpHeaderAuth"]
                cred["id"] = cid
                cred.pop("name", None)
        changed = [n["name"] for n, o in zip(new["nodes"], live["nodes"]) if n != o]
        assert changed and set(changed) <= set(TYPING), changed
        return new, changed

    new, changed = build(cred_id)
    print("would be : %s" % ", ".join("%s -> ..%s (cred %s)" % (n, i[-3:], c) for n, (i, c) in state(new).items()))
    print("changed  : %s" % ", ".join(changed))
    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        NP.dump(new["nodes"], new["connections"], path)
        print("dumped   : %s (the would-be workflow, secret replaced)" % path)
    if "--apply" not in sys.argv:
        print("\nDry run. Re-run with --apply to write it (at the switch, after switch_to_homies.py --apply).")
        return

    new, changed = build(make_credential(e))
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
