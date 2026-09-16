# -*- coding: utf-8 -*-
"""Drive the voice team note the way Vapi does, and read what Chatwoot got.

    python scripts/voice_note_test.py            # the nine cases
    python scripts/voice_note_test.py --clean    # remove the test contacts (cascades their conversations)

Posts Vapi-shaped envelopes to the debt-tools Edge Function (the real host,
resolved as vapi_sync.py resolves it), then reads the Voice inbox with the
Chatwoot admin token. Every call id starts `test-voice-`, the building is
`בדיקת-מערכת`, the number is an unallocated +972599 one; the DB rows stay, as
check_tools.py's `probe-` rows do. Teams hold only the owner, so each mention
pings one PC once.

CASES
  1 notify_team payment, intake assistant   -> team_notified true; a conversation in the Voice
                                               inbox, contact voice:call:<id> named after the
                                               apartment: labels handover + handover-collections,
                                               team collections, medium, one private note ending
                                               on the voice line, waiting_since > 0,
                                               handover_channel voice
  2 the same again, new call id, same phone -> same conversation (found by the number), one note
  3 end-of-call report for call 1           -> nothing new (the tool ran on that call)
  4 end-of-call, new call, bot line
    "עדכנתי את הצוות ויחזרו אליך", no tool  -> a second note, source backstop, reason other
  5 notify_team emergency, new apartment    -> urgent, operations, its own conversation
  6 debt assistant + charges, reason hardship -> a call_outcomes row and NO conversation
  7 no phone, no building                   -> contact voice:call:<id>, note says no address
  8 one call, the address arrives after the first note
                                            -> ONE thread: the second note lands on the first
                                               call's conversation and the contact is renamed
                                               to the apartment (the mid-call identity, found
                                               on the first live probe)
  9 a later call from that apartment, no phone -> found by the name; same thread; the repeat
                                               reason is skipped by the guard

Case 5 leaves an urgent emergency thread for the ticker to escalate on the
real clock (10 minutes) -- watch it or run --clean.
"""
import json
import os
import secrets
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from vapi_sync import load_env, tool_server  # noqa: E402
import n8n_whatsapp as W  # noqa: E402
import n8n_handover_test as T  # noqa: E402

# The assistant ids the Edge Function gates on. Overridable since 16 Sep: the
# demo account (wallet -$0.03 on the real one) has its own pair, and the
# whole point of this harness is to prove `isIntake()` still matches --
# which is exactly what a hardcoded id cannot test after an account move.
import os as _os
INTAKE = _os.environ.get("INTAKE_ASSISTANT_ID") or "8894680c-03af-43f6-a75b-f828872833cc"
DEBT = _os.environ.get("DEBT_ASSISTANT_ID") or "14d502fc-95a9-4fb1-8d93-944dd7e00211"
BUILDING = "בדיקת-מערכת"
RUN = secrets.token_hex(3)
ACC = "/api/v1/accounts/2"


def post(url, headers, body):
    req = urllib.request.Request(url, method="POST", data=json.dumps(body).encode("utf-8"),
                                 headers=dict(headers, **{"Content-Type": "application/json"}))
    try:
        return json.loads(urllib.request.urlopen(req, timeout=90).read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"__http": e.code, "__body": e.read().decode("utf-8")[:300]}


def envelope(call_id, assistant, tool=None, args=None, phone=None, variables=None, report=None):
    call = {"id": call_id, "type": "webCall", "assistantId": assistant}
    if phone:
        call["customer"] = {"number": phone}
    if variables:
        call["assistantOverrides"] = {"variableValues": variables}
    m = {"call": call}
    if tool:
        m["toolCalls"] = [{"id": "tc1", "function": {"name": tool, "arguments": args or {}}}]
    if report:
        m.update({"type": "end-of-call-report", "endedReason": "customer-ended-call",
                  "artifact": {"messages": report}})
    return {"message": m}


def voice_conversations():
    """Every conversation in the Voice inbox that belongs to a test contact."""
    e = W.env()
    inbox = int(e["CHATWOOT_VOICE_INBOX_ID"])
    out = []
    for q in (BUILDING, "voice:call:test-voice-", "voice:phone:+972599"):
        r = T.cw("GET", ACC + "/contacts/search?q=" + urllib.parse.quote(q))
        for c in (r.get("payload") or []) if isinstance(r, dict) else []:
            ident = str(c.get("identifier") or "")
            if not (ident.startswith("voice:" + BUILDING) or ident.startswith("voice:call:test-voice-")
                    or ident.startswith("voice:phone:+972599")):
                continue
            convs = T.cw("GET", ACC + "/contacts/%d/conversations" % c["id"])
            for cv in (convs.get("payload") or []):
                if cv.get("inbox_id") == inbox and cv["id"] not in {x[1]["id"] for x in out}:
                    out.append((c, cv))
    return sorted(out, key=lambda x: x[1]["id"])


def show(label):
    time.sleep(12)
    seen = voice_conversations()
    print("   chatwoot: %d test conversation(s)" % len(seen))
    for c, cv in seen:
        full = T.cw("GET", ACC + "/conversations/%d" % cv["id"])
        st = T.state(cv["id"])
        print("   - conv %s  contact %r named %r  waiting_since %s"
              % (cv["id"], c.get("identifier"), c.get("name"), full.get("waiting_since")))
        print("     %s" % json.dumps({k: st[k] for k in ("status", "priority", "labels", "team", "notes")}, ensure_ascii=False))
        print("     channel %s  reasons %s  source %s" % ((st["custom"] or {}).get("handover_channel"),
                                                       (st["custom"] or {}).get("handover_reasons"),
                                                       (st["custom"] or {}).get("handover_source")))
        if st["last_note"]:
            print("     last note: %s" % st["last_note"][:160])
    return seen


# The DB rows used to stay ("as check_tools.py's probe- rows do"); since 16 Sep
# both harnesses delete theirs. The client's review found the dashboard counts
# inflated by test calls, and the five "בדיקה: שכנה תקועה במעלית" emergency
# stubs he saw in the needs_review pile were this script's case 5.
CHILD_TABLES = ["call_outcomes", "payment_links", "payment_tickets",
                "promises_to_pay", "payment_disputes", "requests"]


def db_clean(prefix="test-voice-"):
    """Delete every interaction whose call id starts with `prefix`, and its rows."""
    e = W.env()
    base = e.get("SUPABASE_URL", "").strip().rstrip("/") + "/rest/v1/"
    key = e.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    hdr = {"apikey": key, "Authorization": "Bearer " + key, "Prefer": "return=representation"}

    def call(method, path):
        req = urllib.request.Request(base + path, method=method, headers=hdr)
        try:
            return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8") or "[]")
        except urllib.error.HTTPError as ex:
            print("   db %s %s -> HTTP %s %s" % (method, path.split("?")[0], ex.code, ex.read()[:120]))
            return []

    like = urllib.parse.quote(prefix + "%", safe="")
    ids = [r["id"] for r in call("GET", "interactions?select=id&external_call_id=like." + like)]
    gone = {}
    if ids:
        inlist = "in.(" + ",".join(ids) + ")"
        for t in CHILD_TABLES:
            gone[t] = len(call("DELETE", "%s?interaction_id=%s" % (t, inlist)))
        gone["interactions"] = len(call("DELETE", "interactions?id=" + inlist))
    gone["requests(building)"] = len(call("DELETE", "requests?building=eq." + urllib.parse.quote(BUILDING, safe="")))
    print("db rows removed: " + ", ".join("%s %d" % kv for kv in gone.items()))


def clean():
    n = 0
    for c, _ in voice_conversations():
        pass
    ids = set()
    for q in (BUILDING, "voice:call:test-voice-", "voice:phone:+972599"):
        r = T.cw("GET", ACC + "/contacts/search?q=" + urllib.parse.quote(q))
        for c in (r.get("payload") or []) if isinstance(r, dict) else []:
            ident = str(c.get("identifier") or "")
            if (ident.startswith("voice:" + BUILDING) or ident.startswith("voice:call:test-voice-")
                    or ident.startswith("voice:phone:+972599")):
                ids.add(c["id"])
    for cid in sorted(ids):
        r = T.cw("DELETE", ACC + "/contacts/%d" % cid)
        print("deleted contact %s %s" % (cid, "" if r is None or not (isinstance(r, dict) and r.get("_http")) else r))
        n += 1
    print("%d test contact(s) removed (their conversations cascade)" % n)
    db_clean()


def main():
    if "--clean" in sys.argv:
        clean()
        return
    load_env()
    server = tool_server()
    if not server:
        sys.exit("No tool host configured (SUPABASE_URL + TOOL_SECRET).")
    url, secret, mode, label = server
    headers = {"x-homies-secret": secret}
    print("host: %s  run: %s" % (label, RUN))
    phone = "+972599" + RUN[:3].encode().hex()[:6]

    def tool(name, call_id, assistant=INTAKE, **kw):
        out = post(url, headers, envelope(call_id, assistant, tool=name, **kw))
        res = (out.get("results") or [{}])[0].get("result") if isinstance(out, dict) else None
        try:
            res = json.loads(res) if isinstance(res, str) else res
        except ValueError:
            pass
        print("   edge: %s" % json.dumps(res if res is not None else out, ensure_ascii=False)[:200])
        return res

    c1 = "test-voice-%s-1" % RUN
    print("\n1 notify_team payment (intake, %s)" % c1)
    tool("notify_team", c1, phone=phone,
         args={"reason": "payment", "description": "בדיקה: רוצה לשלם ועד בית, אין לי קישור לתשלום",
               "building": BUILDING, "unit": "1"})
    show(1)

    c2 = "test-voice-%s-2" % RUN
    print("\n2 the same matter again, new call (%s)" % c2)
    tool("notify_team", c2, phone=phone,
         args={"reason": "payment", "description": "בדיקה: שוב על התשלום", "building": BUILDING, "unit": "1"})
    show(2)

    print("\n3 end-of-call report for call 1 (tool ran on it) -> nothing new")
    report = [
        {"role": "user", "message": "אני רוצה לשלם את ועד הבית"},
        {"role": "tool_calls", "toolCalls": [{"id": "tc1", "function": {"name": "notify_team",
                                                                          "arguments": "{\"reason\":\"payment\"}"}}]},
        {"role": "bot", "message": "מסרתי לצוות הגבייה, הצוות יודע. במה עוד אפשר לעזור?"},
    ]
    out = post(url, headers, envelope(c1, INTAKE, phone=phone, report=report))
    print("   edge: %s" % json.dumps(out, ensure_ascii=False)[:200])
    show(3)

    c4 = "test-voice-%s-4" % RUN
    print("\n4 end-of-call, bot promised, no tool (%s) -> backstop note" % c4)
    report = [
        {"role": "user", "message": "אני רוצה לדבר עם בן אדם על החוזה שלי"},
        {"role": "bot", "message": "בסדר, עדכנתי את הצוות ויחזרו אליך בהקדם. יום טוב ולהתראות."},
    ]
    out = post(url, headers, envelope(c4, INTAKE, phone=phone, report=report))
    print("   edge: %s" % json.dumps(out, ensure_ascii=False)[:200])
    show(4)

    c5 = "test-voice-%s-5" % RUN
    print("\n5 notify_team emergency, another apartment (%s)" % c5)
    tool("notify_team", c5, phone=None,
         args={"reason": "emergency", "description": "בדיקה: שכנה תקועה במעלית ובפאניקה",
               "building": BUILDING, "unit": "7"})
    show(5)

    c6 = "test-voice-%s-6" % RUN
    print("\n6 the debt assistant, reason hardship (%s) -> row only, no conversation" % c6)
    before = len(voice_conversations())
    tool("transfer_to_human", c6, assistant=DEBT,
         variables={"charges": json.dumps([{"charge_id": "00000000-0000-0000-0000-000000000000",
                                            "unit": "3", "period": "2026-07-01", "amount": 450}])},
         args={"reason": "hardship", "posture_reached": "open"})
    time.sleep(8)
    after = len(voice_conversations())
    print("   conversations before %d after %d -> %s" % (before, after, "OK, none added" if after == before else "FAIL, a conversation appeared"))

    c7 = "test-voice-%s-7" % RUN
    print("\n7 no phone, no building (%s) -> contact voice:call:<id>" % c7)
    tool("notify_team", c7, phone=None, args={"reason": "other", "description": "בדיקה: בלי כתובת ובלי מספר"})
    show(7)
    c8 = "test-voice-%s-8" % RUN
    print("\n8 one call, address after the first note (%s) -> one thread, contact renamed" % c8)
    tool("notify_team", c8, phone=None, args={"reason": "contract", "description": "בדיקה: בעיה בחוזה, בלי כתובת עדיין"})
    time.sleep(10)
    tool("notify_team", c8, phone=None, args={"reason": "contract", "description": "בדיקה: בעיה בחוזה, עכשיו עם כתובת",
                                              "building": BUILDING, "unit": "9"})
    show(8)

    c9 = "test-voice-%s-9" % RUN
    print("\n9 a later call from that apartment, no phone (%s) -> found by the name, guard skips" % c9)
    tool("notify_team", c9, phone=None, args={"reason": "contract", "description": "בדיקה: שוב על החוזה, שיחה חדשה",
                                              "building": BUILDING, "unit": "9"})
    show(9)
    if "--keep" in sys.argv:
        print("\nDone. --keep: the rows and contacts stay; `--clean` removes them.")
    else:
        print("\nDone. Removing this run's DB rows (the Chatwoot contacts stay for a look; `--clean` removes them).")
        db_clean("test-voice-%s-" % RUN)


if __name__ == "__main__":
    main()
