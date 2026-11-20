# -*- coding: utf-8 -*-
"""Make the owner's test phone's next WhatsApp message count as one after a quiet gap (a test aid, 20 Nov).

    python scripts/n8n_greet_clock.py            # dry run: when the test phone last wrote, as Sort sees it
    python scripts/n8n_greet_clock.py --apply    # set that time to 9 hours ago

WHY. Since greetgap v1 (scripts/n8n_whatsapp_greetgap.py) Michael introduces himself again when a phone writes
after 8 quiet hours. Sort keeps the last time each phone wrote in the bot workflow's own store
(`staticData.global.greeted`), so testing the intro on the owner's handset otherwise means not writing to the bot
for 8 hours first. This moves that one time back, so the next message from the owner's handset is answered as
the first one after a gap, exactly as a tenant who comes back the next morning is.

ONLY OWNER_TEST_PHONE (.env), never a tenant's number, and the number is never printed. Refuses while a bot run
is in progress: n8n saves a run's copy of the store when the run ends, so a run in flight would put the old time
back. Nothing else in the store is touched; the read-back compares every other entry.
"""
import copy
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
BACK = 9 * 60 * 60 * 1000


def when(ms):
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ms / 1000.0))


def main():
    apply = "--apply" in sys.argv
    phone = "".join(ch for ch in (W.env().get("OWNER_TEST_PHONE") or "") if ch.isdigit())
    if not phone:
        sys.exit("OWNER_TEST_PHONE is not in .env.")
    masked = "…" + phone[-3:]

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    sd = live.get("staticData")
    if not isinstance(sd, dict) or not isinstance(sd.get("global"), dict):
        sys.exit("REFUSING: the workflow's store is not the shape this tool expects. Read live first.")
    greeted = sd["global"].get("greeted") or {}
    seen = greeted.get(phone)
    if not isinstance(seen, (int, float)):
        sys.exit("The test phone (%s) has no time in the store: its next message is a first one already." % masked)
    now = int(time.time() * 1000)
    print("test phone : %s" % masked)
    print("last wrote : %s (%.1f hours ago)" % (when(seen), (now - seen) / 3600000.0))
    if now - seen >= 8 * 3600000:
        print("\nNothing to do. Over 8 hours already: its next message gets Michael's intro.")
        return
    if not apply:
        print("\nDry run. --apply sets it to %s (9 hours ago)." % when(now - BACK))
        return

    runs = W.api("GET", "/api/v1/executions?workflowId=%s&limit=5" % WORKFLOW_ID).get("data") or []
    busy = [r["id"] for r in runs if r.get("status") not in ("success", "error", "canceled", "crashed")
            or not r.get("stoppedAt")]
    if busy:
        sys.exit("REFUSING: bot runs in progress (%s). Try again in a minute." % busy)

    new = copy.deepcopy(sd)
    new["global"]["greeted"][phone] = now - BACK
    W.api("PUT", "/api/v1/workflows/%s" % WORKFLOW_ID, {
        "name": live["name"], "nodes": live["nodes"], "connections": live["connections"],
        "settings": live.get("settings", {}), "staticData": new})

    back = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    bsd = back.get("staticData") or {}
    bg = (bsd.get("global") or {}).get("greeted") or {}
    print("\nwritten    : active=%s" % back.get("active"))
    print("  test phone now : %s" % (when(bg[phone]) if isinstance(bg.get(phone), (int, float)) else bg.get(phone)))
    others_same = {k: v for k, v in bg.items() if k != phone} == {k: v for k, v in greeted.items() if k != phone}
    keys_same = sorted(bsd.get("global") or {}) == sorted(sd["global"])
    print("  other phones unchanged: %s; store keys unchanged: %s" % (others_same, keys_same))
    print("  nodes unchanged: %s" % (back["nodes"] == live["nodes"]))
    if bg.get(phone) != now - BACK:
        sys.exit("NOT WRITTEN: n8n kept the old time (the API may not take the store). Wait 8 hours instead.")


if __name__ == "__main__":
    main()
