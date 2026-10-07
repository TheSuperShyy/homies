# -*- coding: utf-8 -*-
"""The two Hebrew address dictionaries for Cartesia: bare word -> pointed word, one per gender.

    python scripts/cartesia_dicts.py                                        # the entries
    python scripts/cartesia_dicts.py --key CARTESIA_YARIV_API_KEY            # what that account holds
    python scripts/cartesia_dicts.py --key CARTESIA_YARIV_API_KEY --apply    # create both there
    python scripts/cartesia_dicts.py --key CARTESIA_YARIV_API_KEY --delete   # remove ours from there

`--key` names the .env VARIABLE, never the key itself. The dictionaries have to
live on the Cartesia account whose key sits on Vapi's `Cartesia (Hebrew TTS)`
credential (scripts/vapi_cartesia_key.py says which), because Vapi hands Cartesia
only the id and Cartesia looks it up on that account. Creating them is a write to
that account: on the client's key only on the owner's word.

WHY A DICTIONARY AND NOT THE PROMPT (7 Oct; the research is in
docs/reference/voice/hebrew-gender-consistency-2026-10-07.md)
Hebrew writes "to you" the same for a man and a woman (לך) and says it two ways
(lekha / lakh). The prompt asks the model to write such words with vowel points;
measured on the 5 Oct transcripts gpt-4.1 does so for 30% of them and
gpt-5.6-sol for none. Left bare, Cartesia sonic-3.5 picks a reading per word
(לך as a man, שלומך as a woman), so one call mixes genders. A dictionary is
applied by Cartesia itself, to every whole-word match, after everything Vapi
does, and it takes a pointed Hebrew spelling as the "pronunciation". Tested
7 Oct on our own account: whole words only (the letters inside הלך untouched),
a key before "?" or "," still matched, and the pointed alias changed the reading.

TWO DICTIONARIES. The incoming agent gets the masculine one (the owner's rule:
masculine until she shows otherwise). A debt call knows the gender from the
name before it dials, so the dashboard can pick the feminine one per call
through assistantOverrides.voice.pronunciationDictId (not built; see the doc).

WHAT A DICTIONARY CANNOT DO: tell a woman from a man. When the model has
switched to the feminine and still writes a bare לך, the masculine dictionary
says lekha. That residue is the prompt's to shrink (pointed feminine forms, or
phrasings without the suffix). And את is left out on purpose: the same letters
are the object marker in almost every sentence.
"""
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
API = "https://api.cartesia.ai"
VERSION = "2026-03-01"

# bare spelling -> (masculine, feminine), standard pointing. The pronoun
# suffixes first, then the second-person past the agents use. Cartesia matches
# whole words, so the order here is for reading only.
WORDS = [
    ("לך", "לְךָ", "לָךְ"),
    ("שלך", "שֶׁלְּךָ", "שֶׁלָּךְ"),
    ("איתך", "אִתְּךָ", "אִתָּךְ"),
    ("אתך", "אִתְּךָ", "אִתָּךְ"),
    ("אליך", "אֵלֶיךָ", "אֵלַיִךְ"),
    ("עליך", "עָלֶיךָ", "עָלַיִךְ"),
    ("אותך", "אוֹתְךָ", "אוֹתָךְ"),
    ("ממך", "מִמְּךָ", "מִמֵּךְ"),
    ("אצלך", "אֶצְלְךָ", "אֶצְלֵךְ"),
    ("בשבילך", "בִּשְׁבִילְךָ", "בִּשְׁבִילֵךְ"),
    ("עבורך", "עֲבוּרְךָ", "עֲבוּרֵךְ"),
    ("בגללך", "בִּגְלָלְךָ", "בִּגְלָלֵךְ"),
    ("מולך", "מוּלְךָ", "מוּלֵךְ"),
    ("לידך", "לְיָדְךָ", "לְיָדֵךְ"),
    ("בעצמך", "בְּעַצְמְךָ", "בְּעַצְמֵךְ"),
    ("שלומך", "שְׁלוֹמְךָ", "שְׁלוֹמֵךְ"),
    ("התקשרת", "הִתְקַשַּׁרְתָּ", "הִתְקַשַּׁרְתְּ"),
    ("אמרת", "אָמַרְתָּ", "אָמַרְתְּ"),
    ("ביקשת", "בִּקַּשְׁתָּ", "בִּקַּשְׁתְּ"),
    ("שלחת", "שָׁלַחְתָּ", "שָׁלַחְתְּ"),
    ("כתבת", "כָּתַבְתָּ", "כָּתַבְתְּ"),
    ("דיווחת", "דִּוַּחְתָּ", "דִּוַּחְתְּ"),
    ("פתחת", "פָּתַחְתָּ", "פָּתַחְתְּ"),
    ("שילמת", "שִׁלַּמְתָּ", "שִׁלַּמְתְּ"),
    ("קיבלת", "קִבַּלְתָּ", "קִבַּלְתְּ"),
    ("סיפרת", "סִפַּרְתָּ", "סִפַּרְתְּ"),
    ("שאלת", "שָׁאַלְתָּ", "שָׁאַלְתְּ"),
    ("הזכרת", "הִזְכַּרְתָּ", "הִזְכַּרְתְּ"),
    ("עדכנת", "עִדְכַּנְתָּ", "עִדְכַּנְתְּ"),
    ("ציינת", "צִיַּנְתָּ", "צִיַּנְתְּ"),
    ("הסכמת", "הִסְכַּמְתָּ", "הִסְכַּמְתְּ"),
    ("פנית", "פָּנִיתָ", "פָּנִית"),
    ("ראית", "רָאִיתָ", "רָאִית"),
    ("רצית", "רָצִיתָ", "רָצִית"),
    # The glued forms (7 Oct). Cartesia matches whole words, and Hebrew writes
    # ש ("that") and ו ("and") onto the next word, so "תודה שהתקשרת" -- the
    # commonest closing there is -- never matched התקשרת above. The ones the
    # agents actually say; dagesh after שֶׁ where the letter takes it.
    ("שהתקשרת", "שֶׁהִתְקַשַּׁרְתָּ", "שֶׁהִתְקַשַּׁרְתְּ"),
    ("שאמרת", "שֶׁאָמַרְתָּ", "שֶׁאָמַרְתְּ"),
    ("שביקשת", "שֶׁבִּקַּשְׁתָּ", "שֶׁבִּקַּשְׁתְּ"),
    ("שסיפרת", "שֶׁסִּפַּרְתָּ", "שֶׁסִּפַּרְתְּ"),
    ("ששלחת", "שֶׁשָּׁלַחְתָּ", "שֶׁשָּׁלַחְתְּ"),
    ("שכתבת", "שֶׁכָּתַבְתָּ", "שֶׁכָּתַבְתְּ"),
    ("ששאלת", "שֶׁשָּׁאַלְתָּ", "שֶׁשָּׁאַלְתְּ"),
    ("שציינת", "שֶׁצִּיַּנְתָּ", "שֶׁצִּיַּנְתְּ"),
    ("שהזכרת", "שֶׁהִזְכַּרְתָּ", "שֶׁהִזְכַּרְתְּ"),
    ("ששילמת", "שֶׁשִּׁלַּמְתָּ", "שֶׁשִּׁלַּמְתְּ"),
    ("ולך", "וּלְךָ", "וְלָךְ"),
    ("ושלך", "וְשֶׁלְּךָ", "וְשֶׁלָּךְ"),
]
NAMES = {"m": "Homies Hebrew address, masculine", "f": "Homies Hebrew address, feminine"}


def env_value(name):
    m = re.search(r"^%s=(.*)$" % re.escape(name), open(ENV, encoding="utf-8").read(), re.M)
    return m.group(1).strip().strip('"').strip("'") if m else ""


def api(key, path, body=None, method=None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method or ("POST" if body is not None else "GET"),
                                 headers={"Authorization": "Bearer " + key, "Cartesia-Version": VERSION,
                                          "Content-Type": "application/json", "User-Agent": "homies/1.0"})
    try:
        raw = urllib.request.urlopen(req, timeout=60).read()
    except urllib.error.HTTPError as e:
        sys.exit("Cartesia %s %s -> %s %s" % (req.get_method(), path, e.code, e.read()[:200]))
    return json.loads(raw) if raw else {}


def items(gender):
    col = 1 if gender == "m" else 2
    return [{"text": w[0], "pronunciation": w[col]} for w in WORDS]


def ours(key):
    """Our two dictionaries on that account, by name."""
    data = api(key, "/pronunciation-dicts?limit=100").get("data", [])
    return {d["name"]: d for d in data if d.get("name") in NAMES.values()}


def main():
    argv = sys.argv[1:]
    var = argv[argv.index("--key") + 1] if "--key" in argv else ""
    apply_it, delete = "--apply" in argv, "--delete" in argv
    print("%d words, one entry each in two dictionaries:" % len(WORDS))
    for bare, m, f in WORDS:
        print("  %-10s masculine %-18s feminine %s" % (bare, m, f))
    if not var:
        print("\nDry run. --key <ENV VAR> shows what that account holds; --apply creates, --delete removes.")
        return 0
    key = env_value(var)
    if not key:
        sys.exit("%s is not set in .env" % var)
    have = ours(key)
    print("\n%s holds: %s" % (var, ", ".join("%s = %s" % (n, d["id"]) for n, d in have.items()) or "neither"))
    if delete:
        for n, d in have.items():
            api(key, "/pronunciation-dicts/" + d["id"], method="DELETE")
            print("deleted", n, d["id"])
        return 0
    if not apply_it:
        print("Dry run. Re-run with --apply to create the missing one(s) on %s." % var)
        return 0
    for g, name in NAMES.items():
        if name in have:
            print("exists", name, have[name]["id"])
            continue
        d = api(key, "/pronunciation-dicts/", {"name": name, "items": items(g)})
        back = api(key, "/pronunciation-dicts/" + d["id"])
        if len(back.get("items") or []) != len(WORDS):
            sys.exit("read-back of %s has %d items, sent %d" % (name, len(back.get("items") or []), len(WORDS)))
        print("created", name, d["id"], "(%d items read back)" % len(back["items"]))
    print("\nPut the ids in .env as CARTESIA_DICT_INBOUND (masculine) and CARTESIA_DICT_DEBT, then\n"
          "`python scripts/vapi_set_voice.py --agent inbound --apply` sends the id with the voice.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
