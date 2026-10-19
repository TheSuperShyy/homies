# -*- coding: utf-8 -*-
"""What the resident's phone gets when the bot answers "when will they call me?" honestly.

    python scripts/check_honest_answers.py                          # the built-in examples
    python scripts/check_honest_answers.py "אני לא יכול להגיד לך שיגיעו היום."   # your own sentence(s)
    python scripts/check_honest_answers.py --emergency "מי יבוא ומתי, את זה אני לא רואה מכאן."
    python scripts/check_honest_answers.py --file my_sentences.txt  # one sentence per line

Each sentence goes through the WhatsApp bot's last step, Send, twice: once as it is
live today, and once with the epoch-84 filters (promise v4 and danger v4, from
n8n_whatsapp_nopromise.py and n8n_whatsapp_danger.py) put in its place. It prints
what the phone would get from each. A normal turn gets a closing question after the
sentence; an emergency turn (--emergency) gets the urgent-ticket line, the way a reply
in a gas or flood chat looks.

Read-only and free: it reads the live workflow once (GET) and runs the code locally
in Node. No model is called, nothing is written anywhere. After the push both
columns show the same thing.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp_nopromise as NP  # noqa: E402
import n8n_whatsapp_danger as D  # noqa: E402
import check_whatsapp_rules as C  # noqa: E402

QUESTION = "יש עוד משהו שאוכל לעזור בו?"
TICKET = "פתחתי לך קריאה דחופה, מספר 255-1562-26, והצוות יודע עליה."

# (Hebrew, English) -- honest answers: the phone should get them whole.
HONEST = [
    ("אני לא יכול להגיד לך שיגיעו היום.", "I can't tell you they'll come today."),
    ("אם מישהו כבר יחזור אליך היום, את זה אני לא יודע.", "Whether someone will call you back today, I don't know."),
    ("להגיד לך שיחזרו אליך מחר, את זה אני לא יכול.", "To tell you they'll call you back tomorrow, that I can't."),
    ("להבטיח שיחזרו אליך אני לא יכול.", "Promise they'll call you back, that I can't."),
    ("אם יחזרו אליך ומתי, את זה אני לא יודע.", "Whether and when they'll call you back, I don't know."),
    ("אני לא יכול לומר לך שיחזרו אליך היום.", "I can't say they'll call you back today."),
    ("את זה שיחזרו אליך היום אני לא יכול להבטיח.", "That they'll call you back today, I can't promise."),
    ("לא אוכל להגיד לך שיחזרו אליך מחר, כי זה לא כתוב אצלי.",
     "I won't be able to tell you they'll call tomorrow, because it isn't written on my side."),
    ("אני לא יכול להתחייב שיגיעו מחר.", "I can't commit that they'll come tomorrow."),
    ("אני לא יודע אם יגיעו היום.", "I don't know whether they'll come today."),
    ("אין לי דרך לדעת אם יעדכנו אותך.", "I have no way to know whether they'll update you."),
    ("אבל להגיד לך שיגיעו היום בלי שזה כתוב אצלי יהיה לא הוגן כלפיך.",
     "But telling you they'll come today without it written on my side wouldn't be fair to you."),
    # Three that today's bot already lets through, so the count is fair.
    ("אני לא יודע מתי יחזרו אליך.", "I don't know when they'll call you back."),
    ("מתי בדיוק יחזרו אליך, את זה אני לא רואה מכאן.", "When exactly they'll call you back, I can't see from here."),
    ("רשמתי לצוות שאתה מחכה שיחזרו אליך.", "I noted for the team that you're waiting for them to call you back."),
]
# Real promises: the phone should NOT get them.
PROMISES = [
    ("יחזרו אליך מחר.", "They'll call you back tomorrow."),
    ("אני מבטיח שיחזרו אליך היום.", "I promise they'll call you back today."),
    ("אם תרצה, יחזרו אליך מחר.", "If you'd like, they'll call you back tomorrow."),
    ("אני יכול להגיד לך שיגיעו היום.", "I can tell you they'll come today."),
    ("הטכנאי יגיע מחר.", "The technician will come tomorrow."),
]
# In an emergency (gas, fire, flood): honest lines stay, "help is on the way" goes.
HONEST_EMERGENCY = [
    ("מי יבוא ומתי, את זה אני לא רואה מכאן.", "Who's coming and when, I can't see from here."),
    ("אני לא יכול לדעת אם מישהו כבר בדרך.", "I can't know whether someone is already on the way."),
    ("אני לא יכול להגיד לך שמישהו כבר בדרך.", "I can't tell you someone is already on the way."),
    ("כשהקריאה תיסגר, תגיע על זה הודעה לכאן.", "When the ticket is closed, a message about it will arrive here."),
]
PROMISES_EMERGENCY = [
    ("הצוות בדרך אלייך.", "The team is on its way to you."),
    ("אם צריך, מישהו כבר בדרך.", "If needed, someone is already on the way."),
]


def sends():
    """Live's Send, and the same Send with the epoch-84 filters swapped in."""
    live = C.load_live()
    body = {n["name"]: n for n in live["nodes"]}["Send"]["parameters"]["jsonBody"]
    new = body
    a = new.index(NP.BLOCK_START)
    z = new.index(NP.BLOCK_END, a)
    new = new[:a] + NP.FILTER + new[z:]
    a, z = new.index(D.OLD_START), new.index(D.ANCHOR)
    new = new[:a] + D.BLOCK + " " + new[z:]
    marks = lambda b: "%s, %s" % ("promise v4" if "'promise v4'" in b else "promise v3" if "'promise v3'" in b else "promise ?",
                                  "danger v4" if "'danger v4'" in b else "danger v3" if "'danger v3'" in b else "danger ?")
    return body, new, marks(body), marks(new)


def run(body, sentences, emergency):
    if emergency:
        cases = [[s + " " + TICKET, "מישהו בא??", TICKET, [], []] for s in sentences]
        js = D.SMOKE_JS
    else:
        cases = [[s + " " + QUESTION, "מתי?"] for s in sentences]
        js = NP.SMOKE_JS
    r = subprocess.run(["node", "-e", js], capture_output=True,
                       input=json.dumps({"expr": C.inner(body), "cases": cases}, ensure_ascii=False).encode("utf-8"))
    if r.returncode != 0:
        sys.exit("Node failed: " + r.stderr.decode("utf-8", "replace")[:500])
    res = json.loads(r.stdout.decode("utf-8"))
    outs = res.get("out") if isinstance(res, dict) else res
    return [o if isinstance(o, str) else json.dumps(o, ensure_ascii=False) for o in outs]


def squeeze(s):
    return " ".join(s.split())


def verdict(sentence, out, emergency):
    tail = TICKET if emergency else QUESTION
    if squeeze(out) == squeeze(sentence + " " + tail):
        return True, "kept whole"
    left = squeeze(out.replace(tail, ""))
    if not left:
        return False, "deleted; the phone gets only: " + squeeze(out)
    return False, "cut; the phone gets: " + squeeze(out)


def show(title, items, emergency, want_whole, live, new):
    print("=" * 78)
    print(title)
    print("=" * 78)
    sents = [h for h, _ in items]
    a, b = run(live, sents, emergency), run(new, sents, emergency)
    good_a = good_b = 0
    for k, ((he, en), oa, ob) in enumerate(zip(items, a, b), 1):
        wa, ta = verdict(he, oa, emergency)
        wb, tb = verdict(he, ob, emergency)
        good_a += wa == want_whole
        good_b += wb == want_whole
        print("%d. %s" % (k, en or "(your sentence)"))
        print("   bot wrote : %s" % he)
        print("   today     : %s" % ta)
        print("   new       : %s" % tb)
        print()
    return good_a, good_b, len(items)


def main():
    argv = sys.argv[1:]
    emergency = "--emergency" in argv
    argv = [x for x in argv if x != "--emergency"]
    own = []
    if "--file" in argv:
        i = argv.index("--file")
        own += [l.strip() for l in open(argv[i + 1], encoding="utf-8") if l.strip()]
        del argv[i:i + 2]
    own += [x for x in argv if x.strip()]

    live, new, mark_live, mark_new = sends()
    print("today (live) : %s" % mark_live)
    print("new          : %s" % mark_new)
    print("Normal turns end with \"%s\"; emergency turns with the urgent-ticket line." % QUESTION)
    print()
    if own:
        kind = "emergency turn" if emergency else "normal turn"
        show("Your sentences (%s)" % kind, [(s, "") for s in own], emergency, True, live, new)
        return
    rows = [
        ("Honest answers (they should arrive whole)", HONEST, False, True),
        ("Real promises (they should be taken out)", PROMISES, False, False),
        ("Emergency, honest lines (they should arrive whole)", HONEST_EMERGENCY, True, True),
        ("Emergency, help-is-coming promises (they should be taken out)", PROMISES_EMERGENCY, True, False),
    ]
    summary = []
    for title, items, em, want in rows:
        ga, gb, n = show(title, items, em, want, live, new)
        summary.append((title.split(" (")[0], ga, gb, n))
    print("=" * 78)
    print("Summary: right out of the total")
    print("%-34s %10s %10s" % ("", "today", "new"))
    for t, ga, gb, n in summary:
        print("%-34s %10s %10s" % (t, "%d of %d" % (ga, n), "%d of %d" % (gb, n)))


if __name__ == "__main__":
    main()
