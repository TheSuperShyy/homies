"""Scripted conversations against the sandbox bot (feature 19). SPENDS OpenRouter
(the live credential, shared by owner decision): five of the six scenarios reach
the model, six tenant turns in all, each a few Gemini 3.1 Pro calls. Under $1.
Run only on the owner's go.

    python scripts/sandbox_drive.py              # list the scenarios (free)
    python scripts/sandbox_drive.py --run all    # or --run ido_lift,menu_two

Each scenario opens a new conversation in the sandbox inbox as one persona and
checks the bot's words (regexes) and, where it matters, the labels the sandbox
"Hand to a person" put on the conversation. A regex pass is not a quality pass:
read the transcripts, which are also written to local/sandbox/runs/.
"""
import json, os, re, sys, time, urllib.request
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox_chat import E, PERSONAS, contact, cw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = r"\b999-9\d{5}-\d{2}\b"  # the sandbox's fake ticket numbers (guard.ts)
# The AI's own reasoning sent as the reply (27 Oct, three replies to Ido): it talks about "the user",
# "the instructions", or plans "I need: 1." A reply with any of these fails, whatever the scenario.
LEAK = r"מלא מחשבות|המשתמש (?:שואל|שאל|ענה|מבקש|ביקש|כתב)|לפי ההנחיות|בהוראות|אני צריך:"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# name: (persona, what the tenant writes, bot text must match, must not match, labels must, labels must not)
SCENARIOS = {
    "menu_two":  ("לא מוכר", ["שלום"], [r"במה אפשר לעזור"], [r"לדבר עם נציג"], set(), set()),
    "unknown":   ("לא מוכר", ["נשרפה נורה בלובי"], [r"בניין|כתובת"], [], set(), set()),
    # Recognised: the ticket opens at once and the reply names where it was filed (owner, 27 Oct),
    # with no question about the building or flat and no "just to confirm" either.
    "ido_lift":  ("עידו", ["המעלית לא עובדת, אף אחד לא תקוע בה"], [r"בר כוכבא 23", r"דירה 1\b", REF],
                  [r"באיזה בניין|באיזו כתובת|באיזו דירה|מה מספר הדירה|רק לוודא"], set(), set()),
    "rep_typed": ("עידו", ["אני רוצה לדבר עם נציג"], [r"\?"], [r"מעביר אותך|אעביר אותך"], set(), {"handover"}),
    "balance":   ("עידו", ["כמה אני חייב?"], [r"שם|טלפון"], [r"\d{3,} ?₪|\d{3,} שקל"], set(), set()),
    # The owner's own sandbox chat, 27 Oct, word for word: the bot must take the committee fee on
    # itself (balance, paying, a charge) and leave the team a note because a manager was asked for.
    "manager_fee": ("עידו", ["i want to speak with to a manager", "no i need a manager right nw",
                             "its about the committee fee"],
                    [r"יתרה|לשלם|תשלום|קישור|חיוב"], [], {"handover"}, set()),
    "gas":       ("יריב", ["יש ריח חזק של גז בחדר המדרגות"], [], [], {"handover"}, set()),
    # Not in "all": a ticket opened in one turn, so the reply right after the tool call is the
    # one checked. Run on the faithful copy (no --section6) they say whether live leaks too.
    "leak_asaf":    ("אסף", ["יש נזילה בחדר המדרגות, בר כוכבא 23 דירה 2"], [REF], [], set(), set()),
    "leak_yariv":   ("יריב", ["האור בלובי לא עובד כבר יומיים. בר כוכבא 23, דירה 3"], [REF], [], set(), set()),
    "leak_unknown": ("לא מוכר", ["הדלת של הכניסה לבניין לא נסגרת. בר כוכבא 23, דירה 5"], [REF], [], set(), set()),
}


def persona(label):
    return next(k for k, (l, _) in PERSONAS.items() if l == label)


def thread(key, conv):
    return sorted(cw("GET", "/contacts/%s/conversations/%s/messages" % (contact(key), conv)) or [],
                  key=lambda m: m["id"])


def turn(key, conv, text, wait=120, settle=12):
    """Send one line and return the bot's messages to it: [(content, [button titles])]."""
    before = len(thread(key, conv))
    cw("POST", "/contacts/%s/conversations/%s/messages" % (contact(key), conv), {"content": text})
    deadline, count, quiet = time.time() + wait, before + 1, 0
    while time.time() < deadline:
        time.sleep(3)
        now = len(thread(key, conv))
        if now > count:
            count, quiet = now, 0
        elif count > before + 1:
            quiet += 3
            if quiet >= settle:
                break
    return [(m.get("content") or "", [i.get("title") for i in ((m.get("content_attributes") or {}).get("items") or [])])
            for m in thread(key, conv)[before + 1:] if m.get("message_type") == 1]


def labels(conv, wait=20):
    """The labels the sandbox handover put on the conversation (admin API, sandbox account only)."""
    url = "%s/api/v1/accounts/%s/conversations/%s" % (E["CHATWOOT_URL"].rstrip("/"), E["SANDBOX_CW_ACCOUNT_ID"], conv)
    got = set()
    for _ in range(max(1, wait // 4)):
        req = urllib.request.Request(url, headers={"api_access_token": E["SANDBOX_CW_ADMIN_TOKEN"], "User-Agent": "homies/1.0"})
        got = set(json.loads(urllib.request.urlopen(req, timeout=30).read()).get("labels") or [])
        if got:
            break
        time.sleep(4)
    return got


def spend():
    req = urllib.request.Request("https://openrouter.ai/api/v1/key",
                                 headers={"Authorization": "Bearer " + E["OPENROUTER_API_KEY"], "User-Agent": "homies/1.0"})
    return float(json.loads(urllib.request.urlopen(req, timeout=30).read())["data"].get("usage") or 0)


def run(name, log):
    label, lines, must, mustnt, lab_must, lab_not = SCENARIOS[name]
    key = persona(label)
    conv = cw("POST", "/contacts/%s/conversations" % contact(key), {})["id"]
    said = []
    log.append("## %s (as %s, conversation %s)\n" % (name, label, conv))
    print("== %s (as %s)" % (name, label))
    for line in lines:
        out = turn(key, conv, line)
        said += out
        print("  tenant:", line)
        log.append("- **tenant:** " + line)
        for c, b in out:
            shown = c.replace("\n", " / ") + (" [buttons: %s]" % " | ".join(b) if b else "")
            print("  bot:   ", shown)
            log.append("- **bot:** " + shown)
    text = "\n".join(c for c, _ in said)
    fails = [r for r in must if not re.search(r, text)] + ["NOT " + r for r in mustnt if re.search(r, text)]
    if re.search(LEAK, text):
        fails.append("the AI's reasoning is in the reply")
    if name == "menu_two" and not any(len(b) == 2 for _, b in said):
        fails.append("menu does not have exactly two buttons")
    if lab_must or lab_not:
        got = labels(conv)
        fails += ["label %s missing" % l for l in lab_must - got] + ["label %s present" % l for l in lab_not & got]
        print("  labels:", sorted(got))
        log.append("- labels: %s" % sorted(got))
    print("  ->", "PASS" if not fails else "FAIL " + str(fails))
    log.append("- **result:** %s\n" % ("PASS" if not fails else "FAIL " + str(fails)))
    return not fails


if __name__ == "__main__":
    if "--run" not in sys.argv:
        for k, v in SCENARIOS.items():
            print(k, "as", v[0], "|", " / ".join(v[1]))
        sys.exit(0)
    arg = sys.argv[sys.argv.index("--run") + 1]
    names = [n for n in SCENARIOS if not n.startswith("leak_")] if arg == "all" else arg.split(",")
    start = spend()
    log = ["# Sandbox acceptance run, %s UTC\n" % datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")]
    ok = sum(run(n, log) for n in names)
    cost = spend() - start
    print("%d/%d scenarios pass | OpenRouter spend $%.2f" % (ok, len(names), cost))
    log.append("**%d/%d pass, OpenRouter $%.2f**" % (ok, len(names), cost))
    out = os.path.join(ROOT, "local", "sandbox", "runs", datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M") + ".md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(log) + "\n")
    print("transcript:", out)
