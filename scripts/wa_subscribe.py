# -*- coding: utf-8 -*-
"""Which apps a WhatsApp Business Account sends its webhooks to, and subscribing ours (HOMIES).

    python scripts/wa_subscribe.py                                   # read only: .env's WABA and "hadas 1"
    python scripts/wa_subscribe.py --waba 1389698653006050 --apply   # subscribe HOMIES, events to Chatwoot
    python scripts/wa_subscribe.py --waba 1389698653006050 --remove  # undo: unsubscribe HOMIES

WHY, 22 Nov. Meta's status updates (sent, delivered, read, failed) had reached no system of ours since 10 Nov.
So Chatwoot showed one tick on everything, and from 9 Nov templates from the bot's number failed in silence
(no card on the account). Meta has counted the number under "hadas 1" (1389698653006050) since 9 Nov, and no
app was subscribed to that account. A webhook goes only to apps subscribed to the account, the same silent gap
`check_whatsapp.py` has checked for since 19 Aug ("the subscription that was silently missing").

WHERE THE EVENTS GO. --apply subscribes with `override_callback_uri` set to the number's own phone-level
override (Chatwoot's /webhooks/whatsapp/<number>, read live, never typed here) and Chatwoot's verify token
(.env CHATWOOT_WA_VERIFY_TOKEN, equal to inbox 1's). So the events land where the incoming messages already
land. A doubled incoming message is dropped by Chatwoot's source_id check, and a raw Meta post to the bot's n8n
URL is refused by Sort (no shared secret), so nothing can be answered twice.

A write to Meta: only on the owner's go (22 Nov: "ok fix it"). At the move to Homies' own account the same
subscription is needed on their WABA. No token or phone number is printed.
"""
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

GRAPH = "https://graph.facebook.com/v21.0/"
HADAS = "1389698653006050"


def mask(s):
    return re.sub(r"\+?\d{11,15}", "<num>", str(s))


def call(method, path, data=None, tok=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    for attempt in range(3):
        req = urllib.request.Request(GRAPH + path, data=body, method=method,
                                     headers={"Authorization": "Bearer " + tok})
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as x:
            try:
                err = json.loads(x.read().decode()).get("error", {})
            except Exception:  # noqa: BLE001
                err = {}
            return {"HTTP": x.code, "message": err.get("message"), "code": err.get("code")}
        except (socket.timeout, TimeoutError):
            if attempt == 2:
                return {"error": "timed out three times"}


def show(waba, tok):
    d = call("GET", "%s/subscribed_apps" % waba, tok=tok)
    if "data" not in d:
        print("  WABA %s: %s" % (waba, mask(d)))
        return None
    apps = [((a.get("whatsapp_business_api_data") or {}).get("id"), (a.get("whatsapp_business_api_data") or {}).get("name"),
             mask(a.get("override_callback_uri") or "")) for a in d["data"]]
    print("  WABA %s: %s" % (waba, apps or "no app subscribed"))
    return apps


def main():
    e = W.env()
    tok = e["WHATSAPP_ACCESS_TOKEN"].strip()
    args = sys.argv[1:]
    waba = args[args.index("--waba") + 1] if "--waba" in args else None
    pid = e["WHATSAPP_PHONE_NUMBER_ID"].strip()
    wc = (call("GET", "%s?fields=webhook_configuration" % pid, tok=tok).get("webhook_configuration") or {})
    print("the number's webhook_configuration:", mask(json.dumps(wc)))
    print("subscribed apps:")
    for w in ([waba] if waba else [e["WHATSAPP_WABA_ID"].strip(), HADAS]):
        show(w, tok)
    if "--apply" not in args and "--remove" not in args:
        print("\nRead only. --waba <id> --apply subscribes HOMIES; --remove undoes it.")
        return
    if not waba:
        sys.exit("REFUSING: name the account with --waba.")
    if "--remove" in args:
        print("\nDELETE %s/subscribed_apps ->" % waba, mask(call("DELETE", "%s/subscribed_apps" % waba, tok=tok)))
    else:
        target = wc.get("phone_number")
        verify = (e.get("CHATWOOT_WA_VERIFY_TOKEN") or "").strip()
        if not target or "/webhooks/whatsapp/" not in target or not verify:
            sys.exit("REFUSING: the number has no Chatwoot phone override, or .env has no CHATWOOT_WA_VERIFY_TOKEN.")
        r = call("POST", "%s/subscribed_apps" % waba, {"override_callback_uri": target, "verify_token": verify}, tok=tok)
        print("\nPOST %s/subscribed_apps (events to Chatwoot) ->" % waba, mask(r))
    print("read back:")
    show(waba, tok)
    wc2 = (call("GET", "%s?fields=webhook_configuration" % pid, tok=tok).get("webhook_configuration") or {})
    print("the number's webhook_configuration:", mask(json.dumps(wc2)))


if __name__ == "__main__":
    main()
