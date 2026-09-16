# -*- coding: utf-8 -*-
"""Teach the minute ticker to page waiting handovers, and never to steal them.

    python scripts/n8n_handback_escalate.py              # dry run
    python scripts/n8n_handback_escalate.py --apply      # write it
    python scripts/n8n_handback_escalate.py --restore    # put the 3 Sep snapshot back

WHY
"Homies — Chatwoot handback" runs every minute and hands a quiet conversation
back to the bot after 15 minutes. That rule is right for a thread a person took
and left. It is exactly wrong for a thread a resident ASKED to have a person on
and nobody has picked up: handing that back to the bot is the PRD's "thrown to
a robot". So the ticker gains a second job, and a fence around the first.

WHAT IT CHANGES

  1. `Quiet for 15 minutes?` keeps its rule -- a waiting handover has no User
     assignee and no bot-off label, so it was never eligible -- but when it
     DOES hand a served thread back it now also strips the handover labels.
     A person replied; the wait is over.
  2. A second row: `Fetch waiting handovers` (open conversations carrying the
     `handover` label) -> `Waiting for a person?` (in office hours only: never
     paged -> page; paged 10 min ago and nobody claimed it -> escalate1; paged
     again 15 min ago at level 1 -> escalate2, and stop) -> `Hand to a person`
     with that mode. The sub-workflow re-stamps handover_paged_at on every
     page, so a tick never repeats an action, and a failed stamp re-pages a
     minute later -- loud, not silent.

The office-hours test lives in the Code node and in the sub-workflow, the same
line in both: Sunday to Thursday, 09:00-17:00 Israel time. Change one, change
both.

Idempotent. Running it twice reports nothing to do.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402
import n8n_handover as H  # noqa: E402

WORKFLOW_ID = "IVNR5iNn7bQS8JgP"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-handback-live-03sep-before-escalation.json")
ADMIN_CRED = {"httpHeaderAuth": {"id": "1qfgfvxwZ4MsUBBh",
                                 "name": "Chatwoot admin (api_access_token)"}}

KEEP_OLD = "keep_labels: labels.filter(l => l !== 'bot-off'),"
KEEP_NEW = ("// A person answered, so the handover is served: its labels go with bot-off.\n"
            "    keep_labels: labels.filter(l => l !== 'bot-off' && l !== 'after-hours' "
            "&& l !== 'escalated' && !l.startsWith('handover')),")

# A handover NOBODY has answered must survive the handback, or the labels the
# escalation ladder filters on are stripped and the thread goes quiet for good.
# Someone clicking "assign to me" without replying was enough to trigger it.
GUARD_OLD = "  if (!assignee && !labels.includes('bot-off')) continue;   // bot already on"
GUARD_NEW = (GUARD_OLD + "\n"
             "  // A name on the thread is not an answer. waiting_since is cleared only by\n"
             "  // a human agent's public reply, so while it is set the handover is still\n"
             "  // waiting and must keep its labels, its team and its place in the ladder.\n"
             "  if (labels.includes('handover') && Number(c.waiting_since ?? 0)) continue;")

WAITING = r"""
// Which handovers are still waiting for a person, and what to do about each.
// Runs in office hours only: out of hours nobody is paged, and the first tick
// after 09:00 pages everything that arrived overnight (handover_paged_at empty).
const tz = 'Asia/Jerusalem';
const now = DateTime.now().setZone(tz);
const inHours = [7, 1, 2, 3, 4].includes(now.weekday) && now.hour >= 9 && now.hour < 17;
const out = [];
if (!inHours) return out;

for (const c of ($input.first().json.data?.payload ?? [])) {
  const labels = c.labels ?? [];
  if (!labels.includes('handover') || c.status !== 'open') continue;
  // "Claimed" is a person ANSWERING the resident, never a name on the thread:
  // a rep who clicks "assign to me" and then stays silent has to keep
  // escalating. Chatwoot clears waiting_since only on a human agent's public
  // reply -- the bot's own replies never clear it (Message#human_response?
  // wants a User sender), and a private note never clears it either.
  // Answering ENDS the handover rather than merely skipping this tick: leave
  // the labels on and the resident's next message would restart the ladder on
  // a thread a rep is actively working.
  if (!Number(c.waiting_since ?? 0)) {
    out.push({ json: { conv_id: c.id, mode: 'served', phone: c.meta?.sender?.phone_number ?? '',
                       waiting_minutes: null } });
    continue;
  }

  const ca = c.custom_attributes ?? {};
  const paged = ca.handover_paged_at ? DateTime.fromISO(String(ca.handover_paged_at)) : null;
  const level = Number(ca.handover_escalation ?? 0);
  let mode = null;
  if (!paged || !paged.isValid) {
    mode = 'page';                                   // arrived out of hours, never paged
  } else if (String(ca.handover_reason ?? '') !== 'emergency') {
    // 14 Sep: only an emergency climbs the ladder. Everything else is a note
    // the bot left for the team while it kept the conversation -- paged once
    // (or at 09:00), then worked through when the team gets to it. Nobody was
    // promised a time, and paging Management ten minutes after a dues
    // question is the workload this exists to cut.
    continue;
  } else {
    const mins = now.diff(paged, 'minutes').minutes;
    if (level === 0 && mins >= 10) mode = 'escalate1';       // team again + Management
    else if (level === 1 && mins >= 15) mode = 'escalate2';  // every team; the last step
  }
  if (!mode) continue;
  out.push({ json: {
    conv_id: c.id, mode,
    phone: c.meta?.sender?.phone_number ?? '',
    waiting_minutes: paged && paged.isValid ? Math.round(now.diff(paged, 'minutes').minutes) : null,
  } });
}
return out;
"""


def wanted_nodes(sub_id):
    src = "$('Waiting for a person?').item.json"
    fetch = {
        "id": "hb-fetch-waiting", "name": "Fetch waiting handovers",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": [240, 660],
        "parameters": {
            "url": "https://chat.srv1879140.hstgr.cloud/api/v1/accounts/2/conversations",
            "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
            "sendQuery": True,
            "queryParameters": {"parameters": [{"name": "status", "value": "open"},
                                               {"name": "labels[]", "value": "handover"}]},
            "options": {"timeout": 15000},
        },
        "credentials": ADMIN_CRED,
        "retryOnFail": True, "maxTries": 3, "waitBetweenTries": 3000,
    }
    decide = {
        "id": "hb-waiting", "name": "Waiting for a person?", "type": "n8n-nodes-base.code",
        "typeVersion": 2, "position": [480, 660], "parameters": {"jsCode": WAITING.strip("\n")},
    }
    call = {
        "id": "hb-hand-to-person", "name": "Hand to a person",
        "type": "n8n-nodes-base.executeWorkflow", "typeVersion": 1.2, "position": [720, 660],
        "parameters": {
            "workflowId": {"__rl": True, "value": sub_id, "mode": "id"},
            "workflowInputs": {
                "mappingMode": "defineBelow",
                "value": {"conv_id": "={{ %s.conv_id }}" % src, "phone": "={{ %s.phone }}" % src,
                          "reason": "", "department": "", "description": "", "source": "",
                          "mode": "={{ %s.mode }}" % src, "now_override": ""},
                "matchingColumns": [],
                "schema": [{"id": n, "displayName": n, "required": False, "defaultMatch": False,
                            "display": True, "canBeUsedToMatch": True, "type": t}
                           for n, t in H.INPUTS]},
            "mode": "each",
            "options": {"waitForSubWorkflow": True},
        },
        "onError": "continueRegularOutput",
    }
    sticky = {
        "id": "hb-sticky-escalation", "name": "Waiting handovers", "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1, "position": [240, 840],
        "parameters": {"width": 700, "height": 160, "color": 4, "content":
            "### Waiting handovers\n"
            "Second job, same tick. Open conversations labelled `handover`. A person having "
            "ANSWERED (Chatwoot cleared `waiting_since`) ends it -> `served`, which strips the "
            "handover labels. Still waiting: never paged -> page (the 09:00 sweep). Then, for "
            "an EMERGENCY only (14 Sep): 10 quiet minutes -> escalate1 (team + Management); 15 "
            "more at level 1 -> escalate2 (every team). Any other reason is a note the bot left "
            "for the team and is never escalated. Office hours only. A name on the thread is "
            "NOT an answer -- someone who assigns themselves and stays silent keeps "
            "escalating, and the row above leaves an unanswered handover alone."},
    }
    return [fetch, decide, call, sticky]


def ensure_link(conns, src, dst, index=0):
    branches = conns.setdefault(src, {}).setdefault("main", [])
    while len(branches) <= index:
        branches.append([])
    if any(t.get("node") == dst for t in branches[index]):
        return False
    branches[index].append({"node": dst, "type": "main", "index": 0})
    return True


def restore():
    snap = json.load(open(SNAPSHOT, encoding="utf-8"))
    W.api("PUT", "/api/v1/workflows/%s" % WORKFLOW_ID, {
        "name": snap["name"], "nodes": snap["nodes"],
        "connections": snap["connections"], "settings": snap.get("settings", {})})
    print("restored %s from %s (%d nodes)" % (WORKFLOW_ID, SNAPSHOT, len(snap["nodes"])))


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    sub = H.find()
    if sub is None:
        sys.exit("The sub-workflow %r does not exist yet. Run "
                 "`python scripts/n8n_handover.py --apply` first." % H.WF_NAME)

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in ("Every minute", "Fetch open conversations", "Quiet for 15 minutes?",
                 "Unassign", "Strip the bot-off label"):
        if need not in by:
            sys.exit("No %r node on the live handback workflow -- refusing to guess." % need)

    before_layout = layout_complaints(nodes)
    changes = []

    # 1. served handovers lose their labels on the way back to the bot
    code = by["Quiet for 15 minutes?"]["parameters"]["jsCode"]
    if KEEP_OLD in code:
        code = code.replace(KEEP_OLD, KEEP_NEW, 1)
        changes.append("Quiet for 15 minutes?: strip handover labels on handback")
    elif "startsWith('handover')" not in code:
        sys.exit("Anchor missing in `Quiet for 15 minutes?` -- refusing to guess:\n  %s" % KEEP_OLD)

    # 1b. an UNANSWERED handover is never handed back, whoever's name is on it
    if "waiting_since" not in code:
        if GUARD_OLD not in code:
            sys.exit("Anchor missing in `Quiet for 15 minutes?` -- refusing to guess:\n  %s" % GUARD_OLD)
        code = code.replace(GUARD_OLD, GUARD_NEW, 1)
        changes.append("Quiet for 15 minutes?: keep an unanswered handover out of the handback")
    by["Quiet for 15 minutes?"]["parameters"]["jsCode"] = code

    # 2. the second row
    for want in wanted_nodes(sub["id"]):
        have = by.get(want["name"])
        if have is None:
            nodes.append(want)
            by[want["name"]] = want
            changes.append("add node %r" % want["name"])
        elif json.dumps(have.get("parameters"), sort_keys=True, ensure_ascii=False) != \
                json.dumps(want["parameters"], sort_keys=True, ensure_ascii=False):
            have["parameters"] = want["parameters"]
            changes.append("update node %r" % want["name"])
    for src, dst in (("Every minute", "Fetch waiting handovers"),
                     ("Fetch waiting handovers", "Waiting for a person?"),
                     ("Waiting for a person?", "Hand to a person")):
        if ensure_link(conns, src, dst):
            changes.append("wire %s -> %s" % (src, dst))

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    if not changes:
        print("\nNothing to do. Live already matches.")
        return
    print("\nchanges:")
    for ch in changes:
        print("  - %s" % ch)

    worse = sorted(layout_complaints(nodes) - before_layout)
    if worse:
        sys.exit("REFUSING TO PATCH. This would introduce placement problems "
                 "that are not already there:\n    " + "\n    ".join(worse))

    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": nodes, "connections": conns,
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    print("\nwritten: %d nodes. Connections now:" % len(back["nodes"]))
    for src in ("Every minute", "Fetch waiting handovers", "Waiting for a person?"):
        print("  %s -> %s" % (src, json.dumps(back["connections"].get(src), ensure_ascii=False)))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
