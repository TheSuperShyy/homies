# -*- coding: utf-8 -*-
"""Exercise "Homies — Hand to a person" end to end, on the test conversations.

    python scripts/n8n_handover_test.py              # run the eight cases, print Chatwoot state after each
    python scripts/n8n_handover_test.py --one        # case 1 only: one real page of the Service team, for a live alert test
    python scripts/n8n_handover_test.py --clean      # strip what the run left on the test conversations

WHY A HARNESS
The public n8n API cannot run a workflow directly, and the sub-workflow has
no webhook of its own. So this creates a throwaway caller -- Webhook ->
Execute Workflow (waiting) -> Respond -- publishes it, posts each case at it,
and deletes it in a `finally`. Chatwoot is read back with the admin token
after every case, because the sub-workflow's own report says what it decided
and Chatwoot says what actually happened.

WHAT IT WRITES
Private notes, labels, a priority, a team and custom attributes on two TEST
conversations (53 and 44: the Meta test number, no residents). Teams are
empty, so the mentions notify nobody. `--clean` takes the labels, priority,
team and attributes off again; the notes stay, as private notes on a test
thread. `now_override` is what makes office hours testable at any hour.
`notes` counts private notes on the last page of the messages endpoint; the
clean-up's activity lines can push the oldest note off that page, so the count
may drop by one after `--clean` without any note being deleted.

THE TICKER RACES THIS HARNESS, in office hours. The test conversations have
no pending resident message, so their `waiting_since` is 0, and the minute
ticker reads that as "a person answered" -> `served`, which strips the
`handover` label the duplicate guard keys on. When a tick lands between two
cases on the same conversation, the second is not seen as a duplicate (case
2 or 11 reports `ok` instead of `skip`; `handover_answered_at` on the
conversation is the tell). Re-run, or run outside 09:00-17:00. A real
WhatsApp thread keeps `waiting_since` set until a human replies, so this
cannot happen there.

CASES
  1 new, in hours        -> one note, high, team service, labels handover + handover-service
  2 the same again       -> skipped by the guard, still one note
  3 emergency on top     -> upgrade: urgent, a second note
  4 escalate1            -> Management mentioned, escalated label, level 1
  5 escalate2            -> every team mentioned, level 2
  6 new, at 22:15        -> no note, after-hours label, handover_paged_at empty
  7 page at 09:00        -> the note arrives, after-hours label gone, paged_at set
  8 a conversation id that does not exist -> the workflow exits without writing
  9 payment on 53     -> its own note (different reason), team collections, medium
 10 billing on 53     -> its own note again
 11 payment again     -> skipped by the per-reason guard
 12 quote, channel voice -> its own note whose last line tells the rep to phone and resolve;
                        handover_channel stamped `voice`
"""
import json
import os
import secrets
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_handover as H  # noqa: E402

CW = "https://chat.srv1879140.hstgr.cloud"
ACCOUNT = 2
TEST_CONVERSATIONS = (53, 44)


def cw(method, path, body=None):
    e = W.env()
    req = urllib.request.Request(
        CW + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"api_access_token": e["CHATWOOT_API_TOKEN"].strip(),
                 "Content-Type": "application/json", "Accept": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=30).read() or b"null")
    except urllib.error.HTTPError as ex:
        return {"_http": ex.code, "_body": ex.read().decode()[:300]}


def state(cid):
    c = cw("GET", "/api/v1/accounts/%d/conversations/%d" % (ACCOUNT, cid))
    m = c.get("meta", {}) or {}
    # The show payload's `messages` omits private notes; the messages endpoint
    # carries them (message_type 1, private true).
    msgs = cw("GET", "/api/v1/accounts/%d/conversations/%d/messages" % (ACCOUNT, cid))
    notes = [x for x in (msgs.get("payload", []) if isinstance(msgs, dict) else [])
             if x.get("private") and x.get("message_type") == 1]
    return {"status": c.get("status"), "priority": c.get("priority"), "labels": c.get("labels"),
            "team": (m.get("team") or {}).get("name"), "assignee": (m.get("assignee") or {}).get("name"),
            "custom": c.get("custom_attributes"), "notes": len(notes),
            "last_note": (notes[-1]["content"][:170].replace("\n", " | ") if notes else None)}


def clean():
    for cid in TEST_CONVERSATIONS:
        base = "/api/v1/accounts/%d/conversations/%d" % (ACCOUNT, cid)
        # The duplicate guard only counts an OPEN conversation, so a test thread
        # somebody resolved in Chatwoot makes every duplicate case report `ok`
        # (14 Sep: 53 was resolved, cases 2 and 11 both "passed" as new notes).
        cw("POST", base + "/toggle_status", {"status": "open"})
        cw("POST", base + "/labels", {"labels": []})
        cw("POST", base + "/toggle_priority", {"priority": None})
        cw("POST", base + "/assignments", {"team_id": 0})
        # A team with auto-assign ON hands the thread to a member (seen 3 Sep:
        # "Assigned to Assaf Clix via service by Homies bot"); the flag is off
        # on all four teams now, but a leftover assignee must not survive a run.
        cw("POST", base + "/assignments", {"assignee_id": None})
        cw("POST", base + "/custom_attributes", {"custom_attributes": {
            k: None for k in ("handover_at", "handover_reason", "handover_reasons",
                              "handover_department", "handover_channel",
                              "handover_source", "handover_paged_at", "handover_escalation",
                              "handover_answered_at")}})
        print("cleaned %d:" % cid, state(cid))


def harness(sub_id):
    path = "homies-handover-test-" + secrets.token_hex(6)
    schema = [{"id": n, "displayName": n, "required": False, "defaultMatch": False,
               "display": True, "canBeUsedToMatch": True, "type": t} for n, t in H.INPUTS]
    values = {n: "={{ $('Test call').first().json.body.%s }}" % n for n, _ in H.INPUTS}
    wf = {
        "name": "Homies — handover test harness (temporary)",
        "settings": {"executionOrder": "v1"},
        "nodes": [
            {"id": "t-wh", "name": "Test call", "type": "n8n-nodes-base.webhook",
             "typeVersion": 2, "position": [0, 0],
             "parameters": {"httpMethod": "POST", "path": path,
                            "responseMode": "responseNode", "options": {}}},
            {"id": "t-ex", "name": "Hand to a person", "type": "n8n-nodes-base.executeWorkflow",
             "typeVersion": 1.2, "position": [240, 0],
             "parameters": {"workflowId": {"__rl": True, "value": sub_id, "mode": "id"},
                            "workflowInputs": {"mappingMode": "defineBelow", "value": values,
                                               "matchingColumns": [], "schema": schema},
                            "mode": "once", "options": {"waitForSubWorkflow": True}},
             "onError": "continueRegularOutput"},
            {"id": "t-rs", "name": "Answer", "type": "n8n-nodes-base.respondToWebhook",
             "typeVersion": 1.1, "position": [480, 0],
             "parameters": {"respondWith": "json",
                            "responseBody": "={{ JSON.stringify($json) }}", "options": {}}},
        ],
        "connections": {
            "Test call": {"main": [[{"node": "Hand to a person", "type": "main", "index": 0}]]},
            "Hand to a person": {"main": [[{"node": "Answer", "type": "main", "index": 0}]]}},
    }
    return wf, path


def main():
    if "--clean" in sys.argv:
        return clean()
    sub = H.find()
    if sub is None or not sub.get("active"):
        sys.exit("The sub-workflow must exist and be published: "
                 "python scripts/n8n_handover.py --apply --publish")
    base = W.env()["N8N_BASE_URL"].strip().rstrip("/")
    wf, path = harness(sub["id"])
    created = W.api("POST", "/api/v1/workflows", wf)
    hid = created["id"]
    try:
        W.api("POST", "/api/v1/workflows/%s/activate" % hid)
        time.sleep(2)
        url = base + "/webhook/" + path
        print("harness %s ready" % hid)

        def call(body):
            req = urllib.request.Request(
                url, method="POST", data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            try:
                return json.loads(urllib.request.urlopen(req, timeout=120).read() or b"null")
            except urllib.error.HTTPError as ex:
                return {"_http": ex.code, "_body": ex.read().decode()[:300]}

        def case(label, body, cid=None):
            r = call(body)
            print("\n%s -> %s" % (label, json.dumps(r, ensure_ascii=False)))
            if cid:
                print("   %d: %s" % (cid, json.dumps(state(cid), ensure_ascii=False)))

        print("\nbefore 53:", json.dumps(state(53), ensure_ascii=False))
        # `--one`: a single real page, with the real clock, so a person in the
        # Service team can watch the notification arrive on their PC.
        if "--one" in sys.argv:
            case("1 new, real clock", {"conv_id": 53, "phone": "+972500000000", "reason": "caller_request",
                                       "department": "service", "description": "בדיקת התראה: הדייר ביקש נציג",
                                       "source": "tool", "mode": "new", "now_override": ""}, 53)
            return
        case("1 new, in hours", {"conv_id": 53, "phone": "+972500000000", "reason": "caller_request",
                                 "department": "service", "description": "בדיקת מערכת: הדייר ביקש נציג",
                                 "source": "tool", "mode": "new", "now_override": "2026-09-02T10:30:00"}, 53)
        case("2 duplicate", {"conv_id": 53, "phone": "+972500000000", "reason": "caller_request",
                             "department": "service", "description": "כפילות", "source": "backstop",
                             "mode": "new", "now_override": "2026-09-02T10:31:00"}, 53)
        case("3 emergency upgrade", {"conv_id": 53, "phone": "+972500000000", "reason": "emergency",
                                     "department": "operations", "description": "בדיקה: ריח גז",
                                     "source": "tool", "mode": "new", "now_override": "2026-09-02T10:32:00"}, 53)
        case("4 escalate1", {"conv_id": 53, "mode": "escalate1", "now_override": "2026-09-02T10:45:00"}, 53)
        case("5 escalate2", {"conv_id": 53, "mode": "escalate2", "now_override": "2026-09-02T11:00:00"}, 53)
        print("\nbefore 44:", json.dumps(state(44), ensure_ascii=False))
        case("6 new, after hours", {"conv_id": 44, "phone": "+972500000001", "reason": "not_understood",
                                    "department": "", "description": "בדיקה בלילה", "source": "tap",
                                    "mode": "new", "now_override": "2026-09-02T22:15:00"}, 44)
        case("7 page at 09:00", {"conv_id": 44, "mode": "page", "now_override": "2026-09-03T09:00:30"}, 44)
        case("8 missing conversation", {"conv_id": 999999, "mode": "new", "reason": "caller_request",
                                        "source": "tool"})
        # 14 Sep: the reasons name the matter, the guard is per reason, and a
        # dues question is medium, not high. Three cases on 53, after the
        # emergency stamp from case 3 is still on it: a payment note lands as
        # its own matter (different reason), a billing note lands too, and a
        # second payment note is the duplicate the guard exists for.
        case("9 payment, own matter", {"conv_id": 53, "phone": "+972500000000", "reason": "payment",
                                      "department": "", "description": "בדיקה: הדייר רוצה לשלם ועד בית",
                                      "source": "tool", "mode": "new", "now_override": "2026-09-02T11:05:00"}, 53)
        case("10 billing, own matter", {"conv_id": 53, "phone": "+972500000000", "reason": "billing",
                                       "department": "", "description": "בדיקה: השגה על חיוב",
                                       "source": "tool", "mode": "new", "now_override": "2026-09-02T11:06:00"}, 53)
        case("11 payment again, duplicate", {"conv_id": 53, "phone": "+972500000000", "reason": "payment",
                                            "department": "", "description": "כפילות",
                                            "source": "backstop", "mode": "new", "now_override": "2026-09-02T11:07:00"}, 53)
        # 14 Sep, voice joined: the same sub-workflow with `channel: voice`. The
        # note's last line changes (phone the resident, then resolve here) and
        # the channel is stamped so later modes read it back. A new reason so
        # the guard lets it through on 53.
        case("12 quote, channel voice", {"conv_id": 53, "phone": "+972500000000", "reason": "quote",
                                       "department": "", "description": "בדיקה: הצעת מחיר לצביעה",
                                       "source": "tool", "mode": "new", "channel": "voice",
                                       "now_override": "2026-09-02T11:08:00"}, 53)
    finally:
        try:
            W.api("POST", "/api/v1/workflows/%s/deactivate" % hid)
        except SystemExit as ex:
            print("deactivate:", ex)
        try:
            W.api("DELETE", "/api/v1/workflows/%s" % hid)
            print("\nharness deleted")
        except SystemExit as ex:
            print("delete:", ex)


if __name__ == "__main__":
    main()
