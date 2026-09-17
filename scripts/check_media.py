"""A resident's photo lands on the ticket -- the server half, without a handset.

    python scripts/check_media.py

Posts straight to the Edge Function with the tool secret (not through the n8n
voice router: `store_media` is WhatsApp-only and has no router case, on
purpose). The image is a 1x1 PNG as a data: URL, so nothing here touches
Chatwoot. Everything it writes is on the unallocated +972599 prefix and the
בדיקת-מערכת building and is deleted at the end -- the same discipline as
check_tools.py, and the reason 032 exists.

The four claims, in order:
  1. a photo with no ticket is stored and left unlinked;
  2. a ticket opened afterwards adopts it (photos_attached: 1);
  3. a photo sent after the ticket is linked at store time;
  4. the rows and the count agree, and cleanup removes every trace.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n8n_whatsapp as W  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PHONE = "972599000001"           # bare, the WhatsApp shape
E164 = "+" + PHONE
PNG = ("data:image/png;base64,"
       "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
MSG_A, MSG_B = "9100000001", "9100000002"


def post(url, headers, body):
    req = urllib.request.Request(url, method="POST", data=json.dumps(body).encode("utf-8"),
                                 headers=dict(headers, **{"Content-Type": "application/json"}))
    try:
        return json.loads(urllib.request.urlopen(req, timeout=90).read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"__http": e.code, "__body": e.read().decode("utf-8")[:300]}


def main():
    e = W.env()
    base = e["SUPABASE_URL"].rstrip("/")
    fn = base + "/functions/v1/debt-tools"
    secret = e["TOOL_SECRET"].strip()
    key = e["SUPABASE_SERVICE_ROLE_KEY"].strip()
    rest = {"apikey": key, "Authorization": "Bearer " + key}

    def tool(name, args):
        body = {"message": {"type": "tool-calls",
                            "call": {"id": "wa:" + PHONE,
                                     "assistantOverrides": {"variableValues": {"phone": PHONE}}},
                            "toolCalls": [{"id": "probe-media", "type": "function",
                                           "function": {"name": name, "arguments": args}}]}}
        r = post(fn, {"x-homies-secret": secret}, body)
        if "__http" in r:
            return r
        return json.loads(r["results"][0]["result"])

    def rest_get(path):
        req = urllib.request.Request(base + "/rest/v1/" + path, headers=rest)
        return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8") or "[]")

    def rest_del(path):
        req = urllib.request.Request(base + "/rest/v1/" + path, method="DELETE",
                                     headers=dict(rest, Prefer="return=representation"))
        try:
            return len(json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8") or "[]"))
        except urllib.error.HTTPError as ex:
            print("   cleanup", path.split("?")[0], "-> HTTP", ex.code, ex.read()[:120])
            return 0

    fails = 0

    def check(label, cond, got):
        nonlocal fails
        print(("  ok   " if cond else "  FAIL ") + label + ("" if cond else "  got: %s" % json.dumps(got, ensure_ascii=False)[:300]))
        if not cond:
            fails += 1

    att = lambda: [{"file_type": "image", "extension": "png", "data_url": PNG, "file_size": 70}]  # noqa: E731

    try:
        r1 = tool("store_media", {"phone": PHONE, "message_id": MSG_A, "attachments": att()})
        check("1. photo before any ticket is stored, unlinked",
              r1.get("ok") and r1.get("stored") == 1 and r1.get("linked") is None and not r1.get("skipped"), r1)

        r2 = tool("open_request", {"description": "בדיקה: נזילה בלובי, תמונה מצורפת", "type": "plumbing",
                                   "building": "הרצל 112"})
        ref = r2.get("reference")
        check("2. the ticket adopts it (photos_attached 1)", bool(ref) and r2.get("photos_attached") == 1, r2)

        r3 = tool("store_media", {"phone": PHONE, "message_id": MSG_B, "attachments": att()})
        check("3. a photo after the ticket is linked at store time", r3.get("ok") and r3.get("stored") == 1
              and r3.get("linked") == ref, r3)

        rows = rest_get("request_media?phone=eq.%s&select=request_id,storage_path,mime,file_size" % PHONE)
        req = rest_get("requests?reference=eq.%s&select=image_count" % urllib.parse.quote(ref or "-", safe=""))
        check("4. two rows, both linked, image_count 2",
              len(rows) == 2 and all(r["request_id"] for r in rows) and req and req[0]["image_count"] == 2,
              {"rows": rows, "request": req})

        r5 = tool("store_media", {"phone": PHONE, "message_id": "9100000003",
                                  "attachments": [{"file_type": "image", "data_url": "https://example.com/x.jpg"}]})
        check("5. a foreign host is refused, not fetched", r5.get("ok") and r5.get("stored") == 0
              and r5.get("skipped") and "host" in r5["skipped"][0]["reason"], r5)

        r6 = tool("store_media", {"phone": PHONE, "message_id": "9100000004",
                                  "attachments": [{"file_type": "audio", "data_url": PNG}]})
        check("6. a non-image is acknowledged and not stored", r6.get("ok") and r6.get("stored") == 0, r6)
    finally:
        print("cleanup:")
        n_req = rest_del("requests?reported_by_phone=eq.%s" % urllib.parse.quote(E164, safe=""))
        n_int = rest_del("interactions?external_call_id=eq.%s" % urllib.parse.quote("wa:" + PHONE, safe=""))
        n_med = rest_del("request_media?phone=eq.%s" % PHONE)   # anything the cascade missed
        objs = ["%s/%s-0.png" % (PHONE, m) for m in (MSG_A, MSG_B)]
        req = urllib.request.Request(base + "/storage/v1/object/ticket-media", method="DELETE",
                                     data=json.dumps({"prefixes": objs}).encode(),
                                     headers=dict(rest, **{"Content-Type": "application/json"}))
        try:
            gone = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8") or "[]")
        except urllib.error.HTTPError as ex:
            gone = "HTTP %s" % ex.code
        print("   requests %d, interactions %d, stray media rows %d, storage objects %s"
              % (n_req, n_int, n_med, len(gone) if isinstance(gone, list) else gone))

    print("\n%s" % ("all 6 passed" if not fails else "%d FAILED" % fails))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
