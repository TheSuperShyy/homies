# -*- coding: utf-8 -*-
"""Run the services matcher against realistic resident questions, offline.

    python scripts/check_knowledge.py

WHY IT PARSES index.ts INSTEAD OF IMPORTING ANYTHING
`SERVICES` and `findTopics` live in the Edge Function, which is TypeScript on
Deno, and deploying in order to find out whether a keyword list works is a slow
way to learn that it does not. This lifts the data straight out of the file that
ships and re-implements the matcher's two rules in Python, so the thing under
test is the thing that runs. When the TypeScript matcher changes, change this
one too; until they agree again this file fails, which is the point of it.

THE TWO RULES, AND WHY THEY EXIST
Both came out of this test failing on its first run, 23 of 29:

  * **The definite article is dropped at every word start, on both sides.**
    Hebrew puts it INSIDE a phrase -- אב בית is said אב הבית, מאגר מים is said
    מאגר המים -- so keywords written the dictionary way matched neither. Applied
    to the query and the keyword alike, so it is a comparison form and not a
    guess about meaning.
  * **A keyword of three characters or fewer must not be followed by a Hebrew
    letter.** אש is a word and it is also the first two letters of אשפה, which
    put fire detection on every question about the bin room. Longer keywords
    keep plain containment, because Hebrew glues prefixes and בהדברה must still
    find הדברה.

THE EXPECTATION IS PRESENCE, NOT RANK. The tool returns up to three topics and
the model picks between them; a question about cockroaches in the bin room
legitimately matches both cleaning and pest control. A `None` expectation is the
stricter case: it asserts NOTHING matched, because a balance question, a leak
and the opening hours each belong to something else, and a services answer
volunteered over them is a wrong answer.
"""
import io
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "supabase", "functions", "debt-tools", "index.ts")
HEB = re.compile(r"[֐-׿]")


def topics():
    s = io.open(SRC, encoding="utf-8").read()
    if "const SERVICES: Topic[] = [" not in s:
        sys.exit("No SERVICES table in %s -- has the knowledge base moved?" % SRC)
    block = s.split("const SERVICES: Topic[] = [", 1)[1].split("\n];", 1)[0]
    out = []
    for m in re.finditer(r"\{\s*id:\s*\"(.*?)\".*?title:\s*\"(.*?)\".*?words:\s*\[(.*?)\]",
                         block, re.S):
        out.append((m.group(1), m.group(2), re.findall(r'"(.*?)"', m.group(3))))
    return out


def norm(v):
    """index.ts norm(): quotes out, the word 'street' out, whitespace collapsed."""
    v = re.sub(r"[\"'`׳״]", "", str(v or ""))
    v = re.sub(r"(^|\s)(רחוב|רח)(\s|$)", " ", v)
    return re.sub(r"\s+", " ", v).strip()


def key_form(v):
    """index.ts keyForm(): the definite article dropped at every word start."""
    return (" " + v.lower() + " ").replace(" ה", " ")


def has_word(hay, needle):
    """index.ts hasWord(): short keywords may not run into a Hebrew letter."""
    frm = 0
    while True:
        i = hay.find(needle, frm)
        if i < 0:
            return False
        nxt = hay[i + len(needle)] if i + len(needle) < len(hay) else " "
        if len(needle) > 3 or not HEB.match(nxt):
            return True
        frm = i + 1


def find(table, q, limit=3):
    qq = key_form(norm(q))
    if not qq.strip():
        return []
    scored = []
    for tid, _title, words in table:
        best = 0
        for w in words:
            word = key_form(w).strip()
            if word and has_word(qq, word) and len(word) > best:
                best = len(word)
        if best:
            scored.append((best, tid))
    scored.sort(key=lambda x: -x[0])
    return [t for _, t in scored[:limit]]


# (what a resident types, the topic that must be among the answers)
CASES = [
    ("כל כמה זמן מנקים את חדר המדרגות?", "cleaning"),
    ("מי מנקה את הבניין", "cleaning"),
    ("כמה עולה הניקיון", "cleaning"),
    ("אתם עושים הדברה?", "pest"),
    ("יש לי ג'וקים בחדר אשפה", "pest"),
    ("מתי ההדברה הבאה", "pest"),
    ("מי אחראי על הגינה", "garden"),
    ("יש לכם גנן?", "garden"),
    ("כל כמה זמן בודקים את הגנרטור", "generator"),
    ("הגנרטור עובד?", "generator"),
    ("מתי הביקורת של גילוי אש", "fire"),
    ("הגלאי עשן מצפצף", "fire"),
    ("מה זה המפוחים בחניון", "fans"),
    ("מתי מחטאים את מאגר המים", "pumps"),
    ("אין לחץ מים בקומה שמונה", "pumps"),
    ("יש הצפה בחניון", "pumps"),
    ("מי זה אב הבית שלנו", "super"),
    ("אב בית מגיע מתי", "super"),
    ("איך עובדת הגבייה של ועד הבית", "management"),
    ("אפשר לקבל קבלה על התשלום", "management"),
    ("אתם שוטפים את החניון?", "parking"),
    ("אתם עושים שיפוצים בדירה", "renovation"),
    ("אני בעל דירה ורוצה להשכיר אותה", "property"),
    ("אתם מנהלים דירות Airbnb", "shortterm"),
    ("אתם עובדים בהרצליה?", "areas"),
    ("באילו ערים אתם", "areas"),
    # Must match NOTHING: each belongs to another tool or to the facts, and a
    # services answer offered instead of the real one is a wrong answer.
    ("כמה אני חייב", None),
    ("יש נזילה מהתקרה", None),
    ("מה שעות הפעילות שלכם", None),
]


def main():
    table = topics()
    print("%d topics, %d keywords, from %s\n"
          % (len(table), sum(len(w) for _, _, w in table),
             os.path.relpath(SRC, ROOT)))
    bad = 0
    for q, want in CASES:
        got = find(table, q)
        ok = (not got) if want is None else (want in got)
        bad += 0 if ok else 1
        print("  %s %-40s -> %s" % ("ok  " if ok else "MISS", q[:40],
                                    ", ".join(got) or "(nothing)"))
    print("\n%d/%d as expected" % (len(CASES) - bad, len(CASES)))
    if bad:
        print("\nA MISS is either a keyword the catalogue is missing or a rule that\n"
              "stopped matching. Fix SERVICES in index.ts, not this file, unless the\n"
              "matcher itself changed.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
