"""Place one outbound debt call with real variable values, then print the transcript.

This exists because the Vapi dashboard chat cannot send
`assistantOverrides.variableValues`. Unsupplied variables render as empty
strings rather than failing, which is how a test call ended up inventing a month
that nobody had supplied. Everything below is the first chance to hear the agent
speak a real amount, a real month and real card digits.

    python scripts/vapi_call.py          # print the payload, dial nothing
    python scripts/vapi_call.py --go     # actually place the call

Reads VAPI_PRIVATE_KEY from .env. Costs money when --go is passed.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")
API = "https://api.vapi.ai"

ASSISTANT_ID = "3303317e-43b6-4a84-9527-f86b905751d6"   # Homies — Debt Follow-up (he)
# Empty since the 5 Aug account migration. A phone number does not come across
# with a rebuild — the free US number (+16576083115) stayed on the old account,
# and the new one has none. Buy or import one, then put its id here.
#
# Deliberately blank rather than left pointing at the old id: a dead id does not
# fail cleanly, it fails as a Vapi 400 that reads like a payload problem. The
# check below is what turns that into a sentence.
PHONE_NUMBER_ID = ""

CUSTOMER_NUMBER = "+639910967962"

# The ten variables the prompt declares. Every one is supplied; that is the whole
# point of calling through the API instead of the dashboard.
#
# first_name and building are transliterated because the voice is Azure he-IL and
# the surrounding sentence is Hebrew — Latin characters mid-stream get spelled
# out or mangled. Swap them back to "alliah" / "BGC UPTOWN" if you specifically
# want to hear what that failure sounds like.
VARIABLES = {
    "first_name": "אליה",
    "gender": "f",
    "building": "בי ג'י סי אפטאון",
    "unit": "123",
    "month": "אוגוסט",            # "this month" — today is 3 Aug 2026
    "amount": "500",
    "card_last4": "0715",         # supplied as 715, padded: the field is four digits
    "callback_number": "03-1234567",
    "verification_email": "homiesemail@gmail.com",
    "attempt": "1",
}


def load_key():
    if not os.path.exists(ENV):
        sys.exit(".env not found.")
    for line in open(ENV, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    key = os.environ.get("VAPI_PRIVATE_KEY")
    if not key:
        sys.exit("VAPI_PRIVATE_KEY is empty in .env")
    return key


def call(key, method, path, payload=None):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            # Cloudflare 403s urllib's default user-agent.
            "User-Agent": "homies-vapi-call/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s on %s %s\n%s" % (e.code, method, path, e.read().decode("utf-8")))


def main():
    go = "--go" in sys.argv
    key = load_key()

    if not PHONE_NUMBER_ID:
        sys.exit("PHONE_NUMBER_ID is empty. The account migration on 5 Aug did not\n"
                 "bring a phone number across — buy or import one in the Vapi\n"
                 "dashboard and put its id at the top of this file. Web calls from\n"
                 "web/index.html need no number and still work.")

    payload = {
        "phoneNumberId": PHONE_NUMBER_ID,
        "assistantId": ASSISTANT_ID,
        "customer": {"number": CUSTOMER_NUMBER},
        "assistantOverrides": {"variableValues": VARIABLES},
    }

    print("calling    : %s" % CUSTOMER_NUMBER)
    print("from       : %s" % PHONE_NUMBER_ID)
    print("assistant  : %s" % ASSISTANT_ID)
    print("variables  :")
    for k, v in VARIABLES.items():
        print("  %-19s %s" % (k, v if v else "(empty)"))

    if not go:
        print("\nDry run — nothing dialled. Re-run with --go to place the call.")
        return

    result = call(key, "POST", "/call", payload)
    call_id = result["id"]
    print("\ncall %s — %s" % (call_id, result.get("status")))
    print("https://dashboard.vapi.ai/calls/%s" % call_id)

    # Poll until it ends. A four-minute maxDuration plus ringing time is the
    # ceiling, so five minutes of polling is generous.
    print("\nwaiting for the call to end", end="", flush=True)
    for _ in range(100):
        time.sleep(5)
        c = call(key, "GET", "/call/" + call_id)
        if c.get("status") == "ended":
            break
        print(".", end="", flush=True)
    else:
        print("\nStill running. Read it in the dashboard.")
        return

    print("\n\nended      : %s" % c.get("endedReason"))
    if c.get("cost") is not None:
        print("cost       : $%s" % c["cost"])

    transcript = (c.get("artifact") or {}).get("transcript") or c.get("transcript")
    print("\n---- transcript ----")
    print(transcript or "(none — the call did not get far enough to produce one)")

    rec = (c.get("artifact") or {}).get("recordingUrl")
    if rec:
        # Vapi deletes recordings after 14 days. Save anything worth keeping.
        print("\nrecording  : %s" % rec)


if __name__ == "__main__":
    main()
