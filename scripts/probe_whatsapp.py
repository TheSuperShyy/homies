# -*- coding: utf-8 -*-
"""Talk to the live WhatsApp bot from invented numbers and print what it said.

    python scripts/probe_whatsapp.py "היי" "בוקר טוב, מה נשמע?" ">>עוד שאלה"

WHY THIS EXISTS BESIDE check_whatsapp.py
The self-check proves the plumbing: three messages, one row. It cannot tell you
whether the bot SOUNDS right, and on 25 Aug it was green while the bot pasted
"במה אפשר לעזור?" above every balance question and reintroduced itself to a
resident mid-thread. This prints the actual replies so a person -- or a fan-out
of judges -- can read them against prompt.md. It found both faults in one run.

HOW IT WORKS
Each phrase goes from a FRESH test number, so the first-message introduction is
exercised. A phrase starting with '>>' is sent from the SAME number as the
previous one -- a second turn in the same conversation (memory is keyed by
phone). Posts Chatwoot's `message_created` envelope with the `?s=` secret, the
way the agent bot does, then reads the replies out of the n8n executions rather
than off a phone. The Send node 404s against the invented conversation id; that
is expected, harmless, and keeps test replies out of the real inbox.

Rows written under the test numbers are deleted at the end. Never run it
against a real resident's number, and never at more than a handful of phrases at
a time -- every message is a real model call on the production key.
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(ROOT)
import n8n_whatsapp as W  # noqa: E402  (env(), api())

E = W.env()
SECRET = (E.get("N8N_WEBHOOK_SECRET") or "").strip()
if not SECRET:
    sys.exit("N8N_WEBHOOK_SECRET missing from .env")
HOOK = (E["N8N_BASE_URL"].strip().rstrip("/") + "/webhook/homies-whatsapp?s="
        + urllib.parse.quote(SECRET))
WF = "u2JjrbcNPYyyh3yl"

phrases = [a for a in sys.argv[1:] if a.strip()]
if not phrases:
    sys.exit(__doc__)

# 5990xxxxxx is not a live Israeli mobile range; still unique per run.
seed = int(time.time() * 1000) % 10**7
phones, cur = [], None
for i, p in enumerate(phrases):
    if p.startswith(">>") and cur:
        phones.append(cur)
    else:
        cur = "+9725990%06d" % ((seed + i * 7919) % 10**6)
        phones.append(cur)
texts = [p[2:] if p.startswith(">>") else p for p in phrases]


def envelope(i, phone, text):
    n = (seed * 10 + i) % 10**9
    return {"event": "message_created", "id": 9000000000 + n, "content": text,
            "message_type": "incoming", "private": False, "content_type": "text",
            "sender": {"id": 800000 + i, "type": "contact", "name": "בדיקת-מערכת",
                       "phone_number": phone},
            "conversation": {"id": 950000000 + n % 10**7, "status": "pending", "labels": [],
                             "meta": {"assignee": None, "assignee_type": None}},
            "inbox": {"id": 1, "name": "Homies WhatsApp"}}


def mask(s):
    return re.sub(r"\+?\d{9,15}", lambda m: m.group(0)[:5] + "…" + m.group(0)[-2:], str(s))


before = int(W.api("GET", "/api/v1/executions?workflowId=%s&limit=1" % WF)["data"][0]["id"])
for i, (phone, text) in enumerate(zip(phones, texts)):
    req = urllib.request.Request(
        HOOK, data=json.dumps(envelope(i, phone, text), ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "homies-probe/1.0"},
        method="POST")
    with urllib.request.urlopen(req, timeout=60):
        pass
    # A second turn on the same number has to wait for the first reply, or it
    # arrives as two unanswered messages and tests nothing.
    time.sleep(14 if i + 1 < len(texts) and phones[i + 1] == phone else 3)

time.sleep(22)
ex = [e for e in W.api("GET", "/api/v1/executions?workflowId=%s&limit=40" % WF)["data"]
      if int(e["id"]) > before]
ex.sort(key=lambda e: int(e["id"]))

own = {p.lstrip("+") for p in phones}
results = []
for e in ex:
    d = W.api("GET", "/api/v1/executions/%s?includeData=true" % e["id"])
    run = (d.get("data") or {}).get("resultData", {}).get("runData", {})
    if "Sort" not in run:
        continue
    try:
        s = run["Sort"][0]["data"]["main"][0][0]["json"]
    except Exception:
        continue
    if not (s.get("_work") or s.get("_canned") or s.get("_menu")):
        continue  # Chatwoot's echo of an outgoing message, filtered by Sort
    # The self-check or another probe may be talking to the bot at the same
    # time. Only conversations on THIS run's numbers are ours to report.
    to = str(s.get("to") or "").lstrip("+")
    if to and to not in own:
        continue
    row = {"exec": e["id"], "in": s.get("in_text"), "phone": mask(s.get("to", "")),
           "by": "model" if "Answer the resident" in run else "workflow"}
    if row["by"] == "model":
        try:
            row["reply"] = run["Answer the resident"][0]["data"]["main"][0][0]["json"].get("output", "")
        except Exception as x:
            row["reply"] = "(unreadable: %s)" % x
    else:
        row["reply"] = s.get("text") or (s.get("menu") or {}).get("content") or json.dumps(
            {k: v for k, v in s.items() if k in ("text", "menu", "_canned", "_menu")},
            ensure_ascii=False)
    row["tools"] = [t for t in ("open_request", "verify_address", "get_request_status",
                                "get_balance", "transfer_to_human") if t in run]
    results.append(row)

for r in results:
    print("=" * 76)
    print("exec %s  from %s  [%s]" % (r["exec"], r["phone"], r["by"]))
    print("  IN   : %s" % r["in"])
    print("  OUT  : %s" % str(r["reply"]).replace("\n", " / "))
    if r["tools"]:
        print("  TOOLS: %s" % ", ".join(r["tools"]))
print("=" * 76)
print("sent %d, captured %d" % (len(texts), len(results)))

# --- Clean up after ourselves ---------------------------------------------
key = E["SUPABASE_SERVICE_ROLE_KEY"].strip()
base = E["SUPABASE_URL"].strip().rstrip("/") + "/rest/v1/"
h = {"apikey": key, "Authorization": "Bearer " + key, "Prefer": "return=representation"}
bare = sorted(own)
plus = sorted(set(phones))
for table, col, vals in (("messages", "phone", bare + plus),
                         ("requests", "reported_by_phone", bare + plus),
                         ("interactions", "external_call_id", ["wa:" + b for b in bare])):
    try:
        q = "%s?%s=in.(%s)" % (table, col, ",".join(vals))
        req = urllib.request.Request(base + q, headers=h, method="DELETE")
        n = len(json.loads(urllib.request.urlopen(req, timeout=30).read() or b"[]"))
        print("cleanup %-13s %d" % (table, n))
    except Exception as x:
        print("cleanup %-13s %s" % (table, str(x)[:60]))
