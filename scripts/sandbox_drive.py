"""Scripted conversations against the sandbox bot (feature 19). SPENDS OpenRouter
(the live credential, shared by owner decision): five of the six scenarios reach
the model, six tenant turns in all, each a few Gemini 3.1 Pro calls. Under $1.
Run only on the owner's go. It refuses to start when the run could leave the key, which the live bot
answers on, under check_openrouter.py's LOW line.

    python scripts/sandbox_drive.py              # list the scenarios (free)
    python scripts/sandbox_drive.py --run quick  # 4 scenarios, $0.42 on 28 Oct: the usual check after a change
    python scripts/sandbox_drive.py --run all    # 10, $1.13, before a live promotion; or --run ido_lift,gas
    ... --run all --fresh                        # each scenario on a clean memory (a push per persona reuse)
    ... --keep 0                                 # the live bot's $2 line dropped for this one run, owner's word only

Each scenario opens a new conversation in the sandbox inbox as one persona and
checks the bot's words (regexes) and, where it matters, the labels the sandbox
"Hand to a person" put on the conversation. A regex pass is not a quality pass:
read the transcripts, which are also written to local/sandbox/runs/.

A persona's memory is its phone's, across conversations, so without --fresh a persona's later
scenarios see its earlier ones (six are Ido's). --fresh pushes a new memory round
(n8n_sandbox.py --apply --section6 --fresh-memory) before the run and before any scenario
whose persona has already spoken in it.
"""
import json, os, re, subprocess, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox_chat import E, PERSONAS, contact, cw
from check_openrouter import LOW, get as openrouter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = r"\b999-9\d{5}-\d{2}\b"  # the sandbox's fake ticket numbers (guard.ts)
# The AI's own reasoning sent as the reply (27 Oct, three replies to Ido): it talks about "the user",
# "the instructions", or plans "I need: 1." A reply with any of these fails, whatever the scenario.
LEAK = r"מלא מחשבות|המשתמש (?:שואל|שאל|ענה|מבקש|ביקש|כתב)|לפי ההנחיות|בהוראות|אני צריך:"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# name: (persona, what the tenant writes, bot text must match, must not match, labels must, labels must not)
# 29 Oct, money (the owner): the record is the evidence, so a charge question is answered with what is on
# record, and a claimed payment gets a screenshot or the payment confirmation asked for, "so we can verify
# it". "WE ARE THE TEAM": a money reply never speaks of the team as someone else who will check or handle it.
RECORD = r"250|2,?000|אלפיים|ינואר|אוגוסט|חודשים|רשום|במערכת|מופיע"
PROOF = r"צילום מסך|צילום של|אישור (?:על |מה)?(?:ה)?(?:תשלום|העברה|בנק)|קבלה|אסמכתא|הוכחה"
TEAM_ACTS = r"הצוות|לצוות|לגבייה|הם יבדקו|יבדקו|יטפלו|לעזור להם|כדי שיוכלו"
SCENARIOS = {
    "menu_two":  ("לא מוכר", ["שלום"], [r"במה אפשר לעזור"], [r"לדבר עם נציג"], set(), set()),
    "unknown":   ("לא מוכר", ["נשרפה נורה בלובי"], [r"בניין|כתובת"], [], set(), set()),
    # Recognised: the ticket opens at once and the reply names where it was filed (owner, 27 Oct),
    # with no question about the building or flat and no "just to confirm" either.
    # 28 Oct: and no word of what the team will do ("הצוות יראה את זה ויטפל"); a ticket is what was done.
    "ido_lift":  ("עידו", ["המעלית לא עובדת, אף אחד לא תקוע בה"], [r"בר כוכבא 23", r"דירה 1\b", REF],
                  [r"באיזה בניין|באיזו כתובת|באיזו דירה|מה מספר הדירה|רק לוודא",
                   r"הצוות (?:יראה|יטפל|מטפל|על זה)|ויטפל|על זה עכשיו"], set(), set()),
    # A typed request for a person is a manager request under the owner's protocol (27 Oct evening):
    # management is told at once (a real note, so the handover label) and the reply asks what it is about.
    "rep_typed": ("עידו", ["אני רוצה לדבר עם נציג"], [r"\?"], [r"מעביר אותך|אעביר אותך"], {"handover"}, set()),
    # 29 Oct: the balance recognises the sender (sandbox_function.py APP_EDITS). Ido's number is on
    # file, so the amount comes straight away and nobody is asked who they are; a number not on file
    # is still asked for a name and a phone.
    "balance":   ("עידו", ["כמה אני חייב?"], [r"\d{3,} ?₪|₪ ?\d|\d{3,} ?ש|אלפיים"],
                  [r"שם (ה)?מלא|מספר (ה)?טלפון"], set(), set()),
    "balance_unknown": ("לא מוכר", ["כמה אני חייב?"], [r"שם|טלפון"], [r"\d{3,} ?₪|₪ ?\d|\d{3,} שקל"], set(), set()),
    # The owner's own sandbox chat, 27 Oct, word for word: the bot must take the committee fee on
    # itself (balance, paying, a charge) and leave the team a note because a manager was asked for.
    "manager_fee": ("עידו", ["i want to speak with to a manager", "no i need a manager right nw",
                             "its about the committee fee"],
                    [r"יתרה|לשלם|תשלום|קישור|חיוב|דמי ה?ו?ועד"], [], {"handover"}, set()),
    # 28 Oct: "הצוות מעודכן ועל זה עכשיו", a claim no tool made (the note was even held until 09:00).
    "gas":       ("יריב", ["יש ריח חזק של גז בחדר המדרגות"], [], [r"על זה עכשיו|כבר מטפל|מטפלים בזה|קיבלו .{0,15}מיד"],
                  {"handover"}, set()),
    # Not in "all": a ticket opened in one turn, so the reply right after the tool call is the
    # one checked. Run on the faithful copy (no --section6) they say whether live leaks too.
    "leak_asaf":    ("אסף", ["יש נזילה בחדר המדרגות, בר כוכבא 23 דירה 2"], [REF], [], set(), set()),
    "leak_yariv":   ("יריב", ["האור בלובי לא עובד כבר יומיים. בר כוכבא 23, דירה 3"], [REF], [], set(), set()),
    "leak_unknown": ("לא מוכר", ["הדלת של הכניסה לבניין לא נסגרת. בר כוכבא 23, דירה 5"], [REF], [], set(), set()),
    # The owner's second chat, 27 Oct, at its own pace: the lines go out 4 s and 8 s apart without
    # waiting for the bot, so the last one lands while the AI is writing. Exactly one reply may come.
    "burst_manager": ("עידו", ["i need to speak to a manager", "faster!!", "faster!!"], [r"\?"], [], set(), set()),
    # The owner's next chat, 27 Oct: after the committee fee he says the bot can't help, and the bot
    # handed it to the team. The last reply must keep the matter: what it can do, and a question.
    # As Yariv, so it does not share Ido's memory with manager_retest in the same round.
    "manager_doubt": ("יריב", ["i need to speak to a manager", "are you a manager?",
                               "its about the monthly committee fee", "no you cant help me for this one"],
                      [], [], {"handover"}, set()),
    # The owner's retest, 27 Oct 12:24 UTC: a manager twice, then the topic, which ended in "I noted it
    # for our team, anything else in the meantime?". Then the doubt, as in manager_doubt.
    "manager_retest": ("עידו", ["I need a manager.", "I need a manager.", "it's about a payment committee",
                                "no you cant help me for this one"], [], [], {"handover"}, set()),
    # The owner's chat, 29 Oct 11:14 UTC, word for word: the charge went to collections "so they can look
    # into it", then "the team has all the details … in the meantime?", then a goodbye to the refund.
    # The owner: "when its about money base everything in the system since that is your evidence".
    "fee_dispute": ("עידו", ["hey i need a manager right now", "its the committee payment why am i charged 1k shekels?!",
                             "idk but its too much its like my monthly pay", "no but make it fast for the refund"],
                    [], [], {"handover"}, set()),
    # A payment the record does not show: what the record says, the details asked, a note to collections,
    # and no refund or correction promised.
    "paid_already": ("עידו", ["שילמתי כבר את מרץ ואפריל, למה זה עדיין מופיע אצלכם כחוב?",
                              "העברה בנקאית, 500 שקל, בתחילת אפריל",
                              "אז מתי תחזירו לי את הכסף?"], [PROOF], [], {"handover"}, set()),
    # The owner's chat at 12:51 UTC on the first F (two-message bursts sent as one message each): "הם יבדקו …
    # ויטפלו בזה … בינתיים?". The owner: "just to clarify you payed via link and yesterday right. but in our
    # system it says that the payment has not been settled yet. can you send some screenshots … WE ARE THE TEAM".
    "paid_link": ("עידו", ["i need a manager", "my payment its been doubled what HAPPEned?1",
                           "i payed 1k and its still 2k? how is that possible???\nthis is not right i dont understand",
                           "i paid it yesterday via the link you sent in whatsapp\nthis should be fix quickly"],
                  [PROOF], [], {"handover"}, set()),
}
BURST = {"burst_manager": [4, 8]}  # seconds before each line after the first
NOTED = {"manager_fee", "manager_doubt", "manager_retest", "fee_dispute", "paid_link"}  # a topic is told, so two matters are noted
# Named sets for --run (28 Oct, the owner: "can we lessen the costing of the test"; that day's seven
# runs cost about $3.30). Measured on the 09:52 run: quick $0.42 (the ticket, the emergency and the
# whole manager arc), manager $0.88, all $1.13, which is for before a live promotion.
SETS = {"quick": ["ido_lift", "gas", "rep_typed", "manager_retest"],
        "manager": ["rep_typed", "manager_fee", "burst_manager", "manager_doubt", "manager_retest"],
        "money": ["fee_dispute", "paid_already", "paid_link", "balance"]}
# Checks on one reply, by the tenant line it answers (0 is the first), where another may rightly
# mention the team's note. A hand-off is the team knowing or handling it, or "anything else
# (in the meantime)?" in place of the matter itself.
HANDOFF = (r"הצוות יודע|יטפל(?:ו)? בזה|יחזרו אליך|יחזור אליך|יש עוד משהו|עוד משהו ש|מעבר לזה"
           r"|האם יש משהו ש|יש משהו שאני יכול|יש משהו שאוכל")
# The owner's protocol, 27 Oct evening: the first reply to a manager request says management is being
# informed (no gatekeeping) and asks for the details; nothing is conceded ("I'll leave it for the
# team"); the bot never argues back; and the note promises nothing (27 Oct: "שמנהל יחזור אליך … עד שזה
# יקרה"), never "until then", and no cut-off fragment ("רק כדי שמי?", Send's promise filter).
INFORMED = r"מעדכן|עדכנתי|רשמתי|הוספתי|מעודכנ|עודכנ|יודעת|יודעים"
CONCEDE = r"אשאיר את זה|נשאיר את זה|הצוות יבדוק|שהצוות יבדוק|יבדקו את|לבדיקת הצוות"
ARGUE = r"דווקא|תתפלא|מאחד לשני|לא בשביל להעביר|לא כדי להעביר|לא סתם להעביר"
NOTE_SAYS = r"יחזור אליך|יחזרו אליך|ידבר איתך|ידברו איתך|עד שזה יקרה|עד אז|בינתיים|בלי קשר|שמי\?|כבר מטפל|על זה עכשיו"
# 28 Oct: a manager reply ends on its question (the rule said "ask, then say why", and 5 of 13 ended on
# the reason); the reason for asking is the bot's own, never management's ("ככה הם יוכלו לטפל בזה",
# "כדי שהם יוכלו לעזור לך … כשיבדקו") nor the rule's sentence pasted whole ("איתם אפשר לסדר").
ENDS_Q = r"\?[\s🙂😊🙏👍💪🤝]*$"
THEIRS = (r"כדי שהם|ככה הם|שהם יוכלו|כשיבדקו|כשיטפלו|להכין את הדברים|איתם אפשר"
          r"|להעביר לצוות|להעביר להם|להעביר להנהלה|התמונה המלאה|יעזור להם|לעזור להם|כדי שידעו|כדי שיוכלו")
# 28 Oct, the owner: "not too stiff and rude like i can fix it or like i can sort it out right here tell
# me what happened". A manager reply offers care and willingness, never its own capability.
STIFF = r"בעצמי|כאן ועכשיו|ממש כאן|התחום שלי|(?:אני יכול|אוכל) ל(?:סדר|פתור|טפל)|מספיקה לי"
# 29 Oct, the owner: "when its about money base everything in the system since that is your evidence".
# A charge question is answered with what is on record (Ido: ₪250 a month, January to August, ₪2,000),
# and a refund or a correction is never promised, since only a person can make one.
PROMISE = (r"נחזיר|נזכה|יוחזר|יזוכה|תקבל (?:את )?(?:הכסף|החזר|זיכוי)|ההחזר (?:יגיע|יבוצע|יעבור)"
           r"|נטפל בהחזר|אדאג ש|נתקן|יתקנו|יתוקן")
TURNS = {"rep_typed": {0: ([ENDS_Q, INFORMED], [NOTE_SAYS, CONCEDE, THEIRS, STIFF])},
         "burst_manager": {0: ([ENDS_Q, INFORMED], [NOTE_SAYS, CONCEDE, THEIRS, STIFF])},
         "manager_fee": {0: ([ENDS_Q, INFORMED], [NOTE_SAYS, CONCEDE, THEIRS, STIFF]),
                         1: ([ENDS_Q], [ARGUE, CONCEDE, NOTE_SAYS, THEIRS, STIFF]),
                         2: ([ENDS_Q], [HANDOFF, NOTE_SAYS, THEIRS, STIFF])},
         "manager_doubt": {0: ([ENDS_Q, INFORMED], [NOTE_SAYS, CONCEDE, THEIRS, STIFF]),
                           1: ([ENDS_Q, r"מיכאל"], [ARGUE, CONCEDE, r"דיגיטלי", THEIRS, STIFF]),
                           # the monthly fee is the bot's; the committee's people are not the topic
                           2: ([ENDS_Q], [HANDOFF, NOTE_SAYS, THEIRS, r"חברי (?:ה)?ועד|הוועד עצמם", STIFF]),
                           3: ([ENDS_Q], [HANDOFF, ARGUE, CONCEDE, THEIRS, STIFF])},
         "manager_retest": {0: ([ENDS_Q, INFORMED], [NOTE_SAYS, CONCEDE, THEIRS, STIFF]),
                            1: ([ENDS_Q], [ARGUE, CONCEDE, NOTE_SAYS, THEIRS, STIFF]),
                            2: ([ENDS_Q], [HANDOFF, NOTE_SAYS, THEIRS, STIFF]),
                            3: ([ENDS_Q], [HANDOFF, ARGUE, CONCEDE, THEIRS, STIFF])},
         "fee_dispute": {0: ([ENDS_Q, INFORMED], [NOTE_SAYS, CONCEDE, THEIRS, STIFF]),
                         1: ([ENDS_Q, RECORD], [HANDOFF, NOTE_SAYS, CONCEDE, THEIRS, STIFF, TEAM_ACTS]),
                         2: ([ENDS_Q], [HANDOFF, NOTE_SAYS, CONCEDE, THEIRS, STIFF, TEAM_ACTS]),
                         3: ([ENDS_Q, RECORD], [HANDOFF, NOTE_SAYS, CONCEDE, THEIRS, PROMISE, TEAM_ACTS])},
         "paid_already": {0: ([ENDS_Q, RECORD], [HANDOFF, NOTE_SAYS, CONCEDE, THEIRS, PROMISE, TEAM_ACTS]),
                          1: ([ENDS_Q], [NOTE_SAYS, CONCEDE, THEIRS, PROMISE, TEAM_ACTS]),
                          2: ([ENDS_Q], [HANDOFF, NOTE_SAYS, CONCEDE, THEIRS, PROMISE, TEAM_ACTS])},
         "paid_link": {0: ([ENDS_Q, INFORMED], [NOTE_SAYS, CONCEDE, THEIRS, STIFF]),
                       1: ([ENDS_Q, RECORD], [HANDOFF, NOTE_SAYS, CONCEDE, THEIRS, STIFF, TEAM_ACTS]),
                       2: ([ENDS_Q, RECORD], [HANDOFF, NOTE_SAYS, CONCEDE, THEIRS, STIFF, PROMISE, TEAM_ACTS]),
                       3: ([ENDS_Q, RECORD, PROOF], [HANDOFF, NOTE_SAYS, CONCEDE, THEIRS, STIFF, PROMISE,
                                                     TEAM_ACTS])}}


def call(method, path, body=None, tries=4):
    """cw() on a lossy line (27 Oct evening: a fifth of the packets to the server lost, TLS handshakes
    timing out). A read is tried again; a write only when it never left this PC (a URLError), so a
    tenant line is never sent twice."""
    for i in range(tries):
        try:
            return cw(method, path, body)
        except urllib.error.HTTPError:
            raise
        except OSError as x:
            if i == tries - 1 or (method != "GET" and not isinstance(x, urllib.error.URLError)):
                raise
            time.sleep(5 * (i + 1))


def fresh_memory(tries=3):
    """A new memory round for every persona, made the only way the sandbox copies are made."""
    for _ in range(tries):
        done = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "n8n_sandbox.py"),
                               "--apply", "--section6", "--fresh-memory"], capture_output=True, text=True)
        if done.returncode == 0 and "all active" in done.stdout:
            env_text = open(os.path.join(ROOT, ".env"), encoding="utf-8").read()
            print("  (fresh memory: round %s)" % re.search(r"^SANDBOX_MEMORY_ROUND=(\S+)", env_text, re.M).group(1))
            return
        print("  (fresh memory push failed, trying again)", (done.stderr or done.stdout)[-300:])
    sys.exit("could not push a fresh memory round")


def persona(label):
    return next(k for k, (l, _) in PERSONAS.items() if l == label)


def thread(key, conv):
    return sorted(call("GET", "/contacts/%s/conversations/%s/messages" % (contact(key), conv)) or [],
                  key=lambda m: m["id"])


def turn(key, conv, text, wait=120, settle=12):
    """Send one line and return the bot's messages to it: [(content, [button titles])]."""
    before = len(thread(key, conv))
    call("POST", "/contacts/%s/conversations/%s/messages" % (contact(key), conv), {"content": text})
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


def burst(key, conv, lines, gaps, wait=120, settle=20):
    """Send the lines at the given gaps without waiting for the bot, then collect every reply."""
    before = len(thread(key, conv))
    for i, line in enumerate(lines):
        if i:
            time.sleep(gaps[i - 1])
        call("POST", "/contacts/%s/conversations/%s/messages" % (contact(key), conv), {"content": line})
    deadline, count, quiet = time.time() + wait, before + len(lines), 0
    while time.time() < deadline:
        time.sleep(3)
        now = len(thread(key, conv))
        if now > count:
            count, quiet = now, 0
        elif count > before + len(lines):
            quiet += 3
            if quiet >= settle:
                break
    return [(m.get("content") or "", [i.get("title") for i in ((m.get("content_attributes") or {}).get("items") or [])])
            for m in thread(key, conv)[before:] if m.get("message_type") == 1]


def labels(conv, wait=20):
    """The labels the sandbox handover put on the conversation (admin API, sandbox account only),
    and the reasons it noted there (`handover_reasons`, comma-joined, one per matter)."""
    url = "%s/api/v1/accounts/%s/conversations/%s" % (E["CHATWOOT_URL"].rstrip("/"), E["SANDBOX_CW_ACCOUNT_ID"], conv)
    got, reasons = set(), []
    for _ in range(max(1, wait // 4)):
        req = urllib.request.Request(url, headers={"api_access_token": E["SANDBOX_CW_ADMIN_TOKEN"], "User-Agent": "homies/1.0"})
        try:
            c = json.loads(urllib.request.urlopen(req, timeout=30).read())
        except OSError:  # a lossy line: look again
            time.sleep(4)
            continue
        got = set(c.get("labels") or [])
        reasons = [r for r in str((c.get("custom_attributes") or {}).get("handover_reasons") or "").split(",") if r]
        if got:
            break
        time.sleep(4)
    return got, reasons


def spend():
    req = urllib.request.Request("https://openrouter.ai/api/v1/key",
                                 headers={"Authorization": "Bearer " + E["OPENROUTER_API_KEY"], "User-Agent": "homies/1.0"})
    return float(json.loads(urllib.request.urlopen(req, timeout=30).read())["data"].get("usage") or 0)


def headroom(keep=LOW):
    """What a run may spend and still leave the live bot `keep` dollars: check_openrouter's LOW line
    unless --keep says otherwise. The live bot answers tenants on this same key (28 Oct: a day of runs
    left the wallet at $1.57)."""
    key = E["OPENROUTER_API_KEY"]
    c, k = openrouter(key, "/credits"), openrouter(key, "/auth/key")
    left = float(c.get("total_credits") or 0) - float(c.get("total_usage") or 0)
    if k.get("limit") is not None:
        left = min(left, float(k.get("limit_remaining") or 0))
    return left - keep


def run(name, log):
    label, lines, must, mustnt, lab_must, lab_not = SCENARIOS[name]
    key = persona(label)
    conv = call("POST", "/contacts/%s/conversations" % contact(key), {})["id"]
    said, outs = [], []
    log.append("## %s (as %s, conversation %s)\n" % (name, label, conv))
    print("== %s (as %s)" % (name, label))
    for line in ([" / ".join(lines)] if name in BURST else lines):
        out = burst(key, conv, lines, BURST[name]) if name in BURST else turn(key, conv, line)
        said += out
        outs.append(out)
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
    for i, (must_i, mustnt_i) in TURNS.get(name, {}).items():
        reply = "\n".join(c for c, _ in outs[i]) if i < len(outs) else ""
        fails += ["reply to line %d lacks %s" % (i + 1, r) for r in must_i if not re.search(r, reply)]
        fails += ["reply to line %d has %s" % (i + 1, r[:30]) for r in mustnt_i if re.search(r, reply)]
    if name == "menu_two" and not any(len(b) == 2 for _, b in said):
        fails.append("menu does not have exactly two buttons")
    if name in BURST and len(said) != 1:
        fails.append("%d replies to one burst" % len(said))
    if lab_must or lab_not:
        got, reasons = labels(conv)
        fails += ["label %s missing" % l for l in lab_must - got] + ["label %s present" % l for l in lab_not & got]
        # 28 Oct: once the tenant names the topic, the matter is noted under its own reason, so management
        # does not keep a bare "wants a manager" (the committee fee went unnoted once).
        if name in NOTED and len(reasons) < 2:
            fails.append("the matter was not noted (reasons: %s)" % ",".join(reasons))
        print("  labels:", sorted(got), "| noted:", ",".join(reasons))
        log.append("- labels: %s | noted: %s" % (sorted(got), ",".join(reasons)))
    print("  ->", "PASS" if not fails else "FAIL " + str(fails))
    log.append("- **result:** %s\n" % ("PASS" if not fails else "FAIL " + str(fails)))
    return not fails


if __name__ == "__main__":
    if "--run" not in sys.argv:
        for k, v in SCENARIOS.items():
            print(k, "as", v[0], "|", " / ".join(v[1]))
        sys.exit(0)
    arg = sys.argv[sys.argv.index("--run") + 1]
    names = ([n for n in SCENARIOS if not n.startswith("leak_")] if arg == "all"
             else SETS[arg] if arg in SETS else arg.split(","))
    # --keep D lowers the live bot's line for one run, on the owner's word only (29 Oct: "can we
    # remove the 2usd limit"). The key's own cap in OpenRouter still bounds what a run can spend.
    keep = float(sys.argv[sys.argv.index("--keep") + 1]) if "--keep" in sys.argv else LOW
    room, need = headroom(keep), 0.15 * len(names)  # 28 Oct: ten scenarios cost $1.02-1.13
    if room < need:
        sys.exit("OpenRouter has $%.2f above the live bot's $%.2f line, and this run may cost $%.2f. "
                 "Top up first (python scripts/check_openrouter.py)." % (room, keep, need))
    print("%d scenarios, up to about $%.2f ($%.2f is left above the live bot's line)" % (len(names), need, room))
    start = spend()
    log = ["# Sandbox acceptance run, %s UTC\n" % datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")]
    fresh, spoke, ok = "--fresh" in sys.argv, set(), 0
    for n in names:
        if fresh and (not spoke or SCENARIOS[n][0] in spoke):
            fresh_memory()
            spoke = set()
        spoke.add(SCENARIOS[n][0])
        ok += run(n, log)
    cost = spend() - start
    print("%d/%d scenarios pass | OpenRouter spend $%.2f" % (ok, len(names), cost))
    log.append("**%d/%d pass, OpenRouter $%.2f**" % (ok, len(names), cost))
    out = os.path.join(ROOT, "local", "sandbox", "runs", datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M") + ".md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(log) + "\n")
    print("transcript:", out)
