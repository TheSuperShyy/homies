# -*- coding: utf-8 -*-
"""Score played calls against feature 17: no ticket without the reporter's name.

    python scripts/check_name_flow.py RUN_DIR      # RUN_DIR/transcripts/*.json

RUN_DIR is a voice_qa.py bundle. Its deck.json names the source deck
(`_source`), which keeps each card's `expect` and `call_has_number`; the copy
the players read has them stripped. Exit 0 when every transcript passes.

Rules (docs/features/17-name-before-ticket/feature.md, Acceptance):
  named            every ticket that opened carries reporter_name or name_declined
  asked_first      a ticket was preceded by a question about the name, unless
                   the caller said it first
  asked_once       the name was asked at most once (twice when the caller refuses),
                   never when the caller said it first
  emergency_first  in an emergency the team alert came before any name question
  phone            no number asked on a call that has one; on a call without one,
                   the ticket carries reporter_phone or phone_declined
  ticket           a ticket opened exactly when the card expects one
"""
import glob
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# "מה השם" but not "מה השם של הרחוב/הבניין": a place's name is not the person's.
# "מה השם של הדייר" IS a name question (22 Oct, nm_staff_no_number).
NAME_ASK = re.compile(r"(על איזה שם|על שם מי|מה השם(?!\s+של\s+ה?(רחוב|בניין))|מה שמך|"
                      r"איך קוראים ל|את שמך|השם שלך|השם המלא|שם מלא|עם מי (אני|יש לי))")
PHONE_WORD = re.compile(r"טלפון")
PHONE_ASK = re.compile(r"(מספר (טלפון|שאפשר|נייד|ליצירת קשר|לחזור)|לאיזה מספר|באיזה מספר)")


def asks_phone(text):
    return bool(PHONE_WORD.search(text) or PHONE_ASK.search(text))


def events(transcript):
    """The call as an ordered list: ('ask_name'|'ask_phone', i) and ('tool', name, args, result, i)."""
    out = []
    for i, turn in enumerate(transcript.get("turns", [])):
        for rnd in turn.get("rounds", []) or []:
            for call in rnd:
                out.append(("tool", call.get("tool"), call.get("arguments") or {},
                            call.get("result") or {}, i))
        text = turn.get("agent") or ""
        if text and NAME_ASK.search(text):
            out.append(("ask_name", i))
        if text and asks_phone(text):
            out.append(("ask_phone", i))
    return out


def yes(value):
    return value is True or str(value).strip().lower() == "true"


def score(card, transcript):
    """The names of the rules this transcript breaks; [] when it passes."""
    exp = card.get("expect") or {}
    ev = events(transcript)
    opened = [e for e in ev if e[0] == "tool" and e[1] == "open_request" and e[3].get("reference")]
    asks = [e for e in ev if e[0] == "ask_name"]
    fails = []
    if any(not str(e[2].get("reporter_name") or "").strip() and not yes(e[2].get("name_declined"))
           for e in opened):
        fails.append("named")
    if exp.get("ticket") and opened and not exp.get("name_given"):
        first = ev.index(opened[0])
        if not any(ev.index(a) < first for a in asks):
            fails.append("asked_first")
    if exp.get("name_given"):
        if asks:
            fails.append("asked_once")
    elif len(asks) > (2 if exp.get("refuses_name") else 1):
        fails.append("asked_once")
    if exp.get("emergency"):
        alert = [e for e in ev if e[0] == "tool" and e[1] == "notify_team"
                 and e[2].get("reason") == "emergency"]
        if not alert or (asks and ev.index(asks[0]) < ev.index(alert[0])):
            fails.append("emergency_first")
    phone_asks = [e for e in ev if e[0] == "ask_phone"]
    if card.get("call_has_number", True):
        if phone_asks:
            fails.append("phone")
    elif exp.get("ticket") and not any(str(e[2].get("reporter_phone") or "").strip()
                                       or yes(e[2].get("phone_declined")) for e in opened):
        fails.append("phone")
    if bool(exp.get("ticket")) != bool(opened):
        fails.append("ticket")
    return fails


def run(run_dir):
    bundled = json.load(open(os.path.join(run_dir, "deck.json"), encoding="utf-8"))
    src = bundled.get("_source", "")
    if src and not os.path.isabs(src):
        src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), src)
    deck = json.load(open(src, encoding="utf-8")) if src else bundled
    cards = {c["id"]: c for c in deck["scenarios"]}
    results = {}
    for path in sorted(glob.glob(os.path.join(run_dir, "transcripts", "*.json"))):
        t = json.load(open(path, encoding="utf-8"))
        sid = t.get("scenario") or os.path.splitext(os.path.basename(path))[0]
        results[sid] = score(cards[sid], t)
    return results


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    results = run(sys.argv[1])
    for sid, fails in results.items():
        print("%-4s %-24s %s" % ("ok" if not fails else "FAIL", sid, ", ".join(fails)))
    bad = sum(1 for f in results.values() if f)
    print("\n%d of %d passed" % (len(results) - bad, len(results)))
    sys.exit(1 if bad or not results else 0)


if __name__ == "__main__":
    main()
