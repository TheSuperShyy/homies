"""Clone the debt assistant with its template variables already filled in.

The real assistant is a template: `{{first_name}}`, `{{amount}}`, `{{month}}` and
the rest are supplied per call as `assistantOverrides.variableValues`. The Vapi
dashboard cannot send those, so clicking "talk to assistant" there runs the agent
with every variable resolved to an empty string — which is how a test call ended
up inventing a month nobody supplied.

This makes fixed-value copies instead. Each one is a real resident from
`005_debt_seed.sql`, with the values `v_debt_call_queue` would have produced,
baked into the prompt. Then the dashboard's own web-call widget is enough to hear
the agent speak real amounts and real card digits — no phone number, no card on
the Vapi account, no cost.

    python scripts/vapi_mock.py            # list the seed rows
    python scripts/vapi_mock.py david      # create/update one clone
    python scripts/vapi_mock.py --all      # all six
    python scripts/vapi_mock.py --clean    # delete every clone

The clones are throwaway. Edit the real assistant, never these — re-run this and
they are rebuilt from it.
"""

import copy
import json
import os
import re
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")
API = "https://api.vapi.ai"

SOURCE = "93c7f5e5-4024-49a3-9ab6-141f2b423649"   # Homies — Debt Follow-up (he)
PREFIX = "Homies — Debt TEST: "

# Org-level constants. Not per-resident, so they are not in the seed.
# The office line. Same value and same override as the dashboard's Call
# button (dashboard/lib/call.ts), so .env is the one place to change it.
CALLBACK_NUMBER = os.environ.get("HOMIES_CALLBACK_NUMBER", "077-6687949")
# Spoken, not written. See web/index.html for why this is a sentence rather
# than an address: a Hebrew voice given Latin text sounds it out, and guesses
# differently every reading.
VERIFICATION_EMAIL = "אופיס, שטרודל, הומיז, נקודה, סי, או, נקודה, איי, אל"

# The three finished forms {{gender_forms}} can take. Kept in step with the copy
# in web/index.html by hand — there is no shared source between a Python script
# and a static page, and both are demo-side. When the caller becomes real these
# move into the view beside apartments_phrase and this constant goes.
GENDER_FORMS = {
    "f": "הנמענת אישה. פנה אליה בנקבה לאורך כל השיחה: את, שלָךְ, לָךְ, איתָּךְ, "
         "תגידי, תשלחי, תבדקי, תסגרי, תוכלי, תרצי.",
    "m": "הנמען גבר. פנה אליו בזכר לאורך כל השיחה: אתה, שלְךָ, לְךָ, איתְּךָ, "
         "תגיד, תשלח, תבדוק, תסגור, תוכל, תרצה.",
    "unknown": "מין הנמען לא ידוע. דבר בניסוחים נייטרליים בלבד ואל תנחש: צריך, "
               "אפשר, בואו נראה, מה תרצו, אשמח לדעת. אם הוא או היא חושפים מין "
               "בדיבור על עצמם — אני צריכה מול אני צריך — עבור מיד להטיה הזאת.",
}

# The six rows `v_debt_call_queue` returns from 002 + 005. Transcribed rather
# than queried because Supabase is not stood up yet; when it is, replace this
# with the query and the values should match exactly.
#
# The four excluded rows are deliberately absent: מיכל (paid), נועה (not handed
# over), איתי (do not call), טל (four attempts). A clone existing for any of them
# would mean the view's filters are not doing their job.
#
# month is יולי because the seed period is 2026-07-01, and attempt is
# `attempts + 1` — the view's definition, not the stored column.
ROWS = {
    "david": {
        "first_name": "דוד", "gender": "m", "building": "הרצל 14", "unit": "12",
        "month": "יולי", "amount": "450", "card_last4": "4821", "attempt": "1",
        "note": "the straightforward one — card on file, first attempt",
    },
    "sarah": {
        "first_name": "שרה", "gender": "f", "building": "הרצל 14", "unit": "7",
        "month": "יולי", "amount": "450", "card_last4": "7355", "attempt": "2",
        "note": "second attempt — she has been called about this before",
    },
    "moshe": {
        "first_name": "משה", "gender": "m", "building": "ביאליק 8", "unit": "3",
        "month": "יולי", "amount": "380", "card_last4": "", "attempt": "1",
        "note": "NO CARD ON FILE — must not ask for authorisation at all",
    },
    "rachel": {
        "first_name": "רחל", "gender": "f", "building": "ביאליק 8", "unit": "15",
        "month": "יולי", "amount": "380", "card_last4": "1190", "attempt": "3",
        "note": "third attempt — the tone should reflect that",
    },
    "yossi": {
        "first_name": "יוסי", "gender": "m", "building": "רוטשילד 22", "unit": "4",
        "month": "יולי", "amount": "520", "card_last4": "6042", "attempt": "1",
        "note": "masculine grammar throughout",
    },
    "avi": {
        "first_name": "אבי", "gender": "unknown", "building": "ז'בוטינסקי 5",
        "unit": "2", "month": "יולי", "amount": "610", "card_last4": "2314",
        "attempt": "1",
        "note": "gender unknown — the prompt must avoid gendered verbs",
    },
}

# Vapi owns these; POST /assistant rejects them.
READ_ONLY = ("id", "orgId", "createdAt", "updatedAt", "isServerUrlSecretSet")


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


def api(key, method, path, payload=None):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            # Cloudflare 403s urllib's default user-agent.
            "User-Agent": "homies-vapi-mock/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            body = r.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s on %s %s\n%s" % (e.code, method, path, e.read().decode("utf-8")))


def filled(source, row):
    """The source assistant with every {{variable}} substituted.

    Substitution runs over the serialised assistant rather than a known list of
    fields, so a placeholder added to firstMessage, a voicemail message or an
    end-call message is picked up without this script needing to know about it.
    """
    body = {k: v for k, v in copy.deepcopy(source).items() if k not in READ_ONLY}
    values = dict(row)
    values.pop("note", None)
    values["callback_number"] = CALLBACK_NUMBER
    values["verification_email"] = VERIFICATION_EMAIL
    # Composed from `gender`, not passed alongside it. The prompt stopped
    # branching on the code on 12 Aug — see web/index.html, which composes the
    # same three strings for a live call. Derived here rather than added to the
    # seed so the seed stays a transcription of the view.
    values["gender_forms"] = GENDER_FORMS[row.get("gender", "unknown")]

    text = json.dumps(body, ensure_ascii=False)
    for k, v in values.items():
        # json.dumps escapes nothing in these values except quotes, and the
        # apostrophe in ז'בוטינסקי is not escaped in JSON — but run it through
        # the encoder anyway so a value containing a quote cannot break the doc.
        text = text.replace("{{%s}}" % k, json.dumps(v, ensure_ascii=False)[1:-1])

    left = sorted(set(re.findall(r"\{\{([a-z_0-9]+)\}\}", text)))
    if left:
        # An unresolved placeholder renders as an empty string at call time and
        # the agent invents a value to cover the gap. Never ship one.
        sys.exit("Unresolved placeholders: %s\nAdd them to ROWS." % ", ".join(left))
    return json.loads(text)


def upsert(key, source, name, row, existing):
    body = filled(source, row)
    body["name"] = PREFIX + row["first_name"]
    found = existing.get(body["name"])
    if found:
        a = api(key, "PATCH", "/assistant/" + found, body)
        verb = "updated"
    else:
        a = api(key, "POST", "/assistant", body)
        verb = "created"
    print("  %-8s %s  %s" % (verb, a["id"], body["name"]))
    return a["id"]


def clones(key):
    return {a["name"]: a["id"] for a in api(key, "GET", "/assistant?limit=100")
            if (a.get("name") or "").startswith(PREFIX)}


def main():
    key = load_key()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if "--clean" in sys.argv:
        have = clones(key)
        for name, aid in have.items():
            api(key, "DELETE", "/assistant/" + aid)
            print("deleted %s" % name)
        if not have:
            print("Nothing to delete.")
        return

    if not args and "--all" not in sys.argv:
        print("Seed rows from v_debt_call_queue (002 + 005):\n")
        for k, r in ROWS.items():
            card = r["card_last4"] or "(none)"
            print("  %-8s %-5s %s₪ %-6s card %-6s attempt %s"
                  % (k, r["first_name"], r["amount"], r["month"], card, r["attempt"]))
            print("           %s" % r["note"])
        print("\n  python scripts/vapi_mock.py david   # one clone")
        print("  python scripts/vapi_mock.py --all   # all six")
        print("  python scripts/vapi_mock.py --clean # delete them")
        return

    unknown = [a for a in args if a not in ROWS]
    if unknown:
        sys.exit("Unknown row(s): %s. Options: %s"
                 % (", ".join(unknown), ", ".join(ROWS)))

    source = api(key, "GET", "/assistant/" + SOURCE)
    existing = clones(key)
    wanted = list(ROWS) if "--all" in sys.argv else args

    print("cloning %s with values resolved\n" % source["name"])
    ids = [upsert(key, source, n, ROWS[n], existing) for n in wanted]

    print("\nOpen one in the dashboard and press Talk. Web calls need no phone")
    print("number and no card, so this is the one test path that is not blocked.")
    for i in ids:
        print("  https://dashboard.vapi.ai/assistants/%s" % i)


if __name__ == "__main__":
    main()
