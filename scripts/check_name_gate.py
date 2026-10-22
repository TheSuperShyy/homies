# -*- coding: utf-8 -*-
"""Feature 17, live: the deployed function refuses a phone-call ticket without a name.

    N8N_BASE_URL= python scripts/check_name_gate.py

One open_request, as an incoming call with no name, on בר כוכבא 23 (the test
building). The refusal opens no ticket; any row the call id left is deleted the
way check_tools.py deletes its own probes.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_tools as T  # noqa: E402
from vapi_sync import load_env, tool_server  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    load_env()
    server = tool_server()
    if not server:
        sys.exit("No tool host configured in .env")
    url, secret, mode, label = server
    headers = {}
    if mode == "query":
        url = url + ("&" if "?" in url else "?") + "key=" + secret
    else:
        headers["x-homies-secret"] = secret
    body = {"message": {
        "call": {"id": "probe-%s-1" % T.RUN},
        "toolCalls": [{"id": "tc1", "function": {"name": "open_request", "arguments": {
            "description": "בדיקת מערכת, לא תקלה אמיתית",
            "building": "בר כוכבא 23", "type": "other"}}}],
    }}
    out = T.post(url, headers, body)
    try:
        result = json.loads((out.get("results") or [{}])[0].get("result") or "{}")
    except Exception:
        result = {"raw": out}
    T.cleanup(T.RUN)
    ok = result.get("opened") is False and result.get("reason") == "need_name"
    print("host: %s" % label)
    print("%s open_request with no name -> %s"
          % ("ok  " if ok else "FAIL", json.dumps(result, ensure_ascii=False)[:200]))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
