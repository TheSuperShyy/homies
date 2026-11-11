# -*- coding: utf-8 -*-
"""Whose tickets are copied into OXS: read the list, and add or remove a flat of the test building.

    python scripts/oxs_mirror_list.py                          # read only: the list by flat, live against .env
    python scripts/oxs_mirror_list.py --add-flat 1 3           # dry run: what would be added
    python scripts/oxs_mirror_list.py --add-flat 1 3 --apply   # write it, then read it back
    python scripts/oxs_mirror_list.py --remove-flat 1 --apply

WHAT THE LIST IS
`open_request` copies a new ticket into Homies' OXS only when the message or the call came from a
number on `OXS_MIRROR_PHONES` (debt-tools, `oxsMirrorAllowed()`). Everybody else's ticket stays in our
system. OXS is a client's production system and is otherwise read-only for us, so every number on
this list is a decision the owner made in so many words:

  24 Sep  the owner's own +63: "from now on i want to open a ticket it should be opened in oxs as
          well, for the phone number whenever i send some report using the +63"
  11 Nov  flats 1 and 3 of the test building, Homies' own two people, after being told that their
          six tickets were not in OXS and that adding them is a write there: "so make sure when
          they open a ticket it will be opened to oxs directly"

NEVER ADD A NUMBER TO MAKE A TEST EASIER. Ask, name the numbers' owners, and wait for the word.

WHAT THIS DOES, AND DOES NOT
- A flat means every number on file for it in `residents`, in the ONE building opened for us
  (בר כוכבא 23). Flat 1 has two: the one registered in OXS and the one its tenant writes from.
  There is no flag for another building.
- `--apply` rewrites the one line in `.env` (after a copy to local/env-backups/) and sets the one
  live secret through the Management API, then reads its digest back. `.env` has to change too:
  `supabase_functions.py --apply --oxs-mirror` pushes the list from there.
- No code is deployed and nothing is written to OXS by this script. The first ticket from a newly
  added number is the first write.
- It refuses when the live list is not `.env`'s: somebody changed one without the other, and
  adding on top of that would hide it.
- NO NUMBER IS EVER PRINTED. The list is shown by flat.

The numbers are compared the way the function compares them: +E.164, exactly as `residents.phone`
holds them. A number on file in another form could never match and is not added.
"""
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, ".env")
BACKUPS = os.path.join(ROOT, "local", "env-backups")
NAME = "OXS_MIRROR_PHONES"
BUILDING = u"בר כוכבא 23, תל אביב - יפו"     # the ONE building opened for us
API = "https://api.supabase.com"
UA = "curl/8.5.0"                            # Cloudflare refuses urllib's own (supabase_functions.py)
NOT_ON_FILE = "not on file in the test building"


# --------------------------------------------------------------------------
# The rules, with no network in them (oxs_mirror_list_test.py).
# --------------------------------------------------------------------------
def entries(value):
    """The list as the function reads it: split on commas, trimmed, empties dropped."""
    return [s.strip() for s in str(value or "").split(",") if s.strip()]


def valid(number):
    """A number in the only form the function's comparison can match: +E.164."""
    return bool(re.fullmatch(r"\+\d{8,15}", str(number or "")))


def numbers_of(residents, flat):
    """Every usable number on file for one flat, each once, in the order found."""
    out = []
    for r in residents:
        if str(r.get("unit") or "").strip() == str(flat) and valid(r.get("phone")) and r["phone"] not in out:
            out.append(r["phone"])
    return out


def with_added(current, numbers):
    out = list(current)
    for n in numbers:
        if n not in out:
            out.append(n)
    return out


def without(current, numbers):
    return [n for n in current if n not in set(numbers)]


def by_flat(current, residents):
    """The list as it may be shown: (who, how many), never a number."""
    order, count = [], {}
    for n in current:
        flats = sorted({str(r.get("unit")).strip() for r in residents if r.get("phone") == n})
        who = "flat " + "/".join(flats) if flats else NOT_ON_FILE
        if who not in count:
            order.append(who)
        count[who] = count.get(who, 0) + 1
    return [(who, count[who]) for who in order]


def env_with(text, name, value):
    """`.env`'s text with the one line `name=` set to `value`; everything else byte for byte."""
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    hit = [i for i, line in enumerate(lines) if line.split("=", 1)[0].strip() == name and "=" in line]
    if hit:
        lines[hit[0]] = "%s=%s" % (name, value)
        return nl.join(lines)
    body = text if text.endswith(nl) or not text else text + nl
    return body + "%s=%s%s" % (name, value, nl)


# --------------------------------------------------------------------------
# .env, Supabase
# --------------------------------------------------------------------------
def env():
    d = {}
    for line in open(ENV_PATH, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def call(token, method, path, body=None):
    req = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": UA})
    try:
        res = urllib.request.urlopen(req, timeout=60)
        return res.status, json.loads(res.read() or b"null")
    except urllib.error.HTTPError as ex:
        return ex.code, ex.read().decode("utf-8", "replace")[:200]


def live_digest(token, ref):
    """The live secret's digest (sha256 of its value), or None when the secret is absent."""
    code, out = call(token, "GET", "/v1/projects/%s/secrets" % ref)
    if code != 200 or not isinstance(out, list):
        sys.exit("Could not read the function's secrets: HTTP %s" % code)
    names = {s["name"]: s.get("value") for s in out}
    return names.get(NAME), "OXS_KEY_REQUESTS" in names, "OXS_MIRROR_TYPES" in names


def residents(e):
    base = e["SUPABASE_URL"].rstrip("/") + "/rest/v1/"
    srk = e["SUPABASE_SERVICE_ROLE_KEY"].strip()
    req = urllib.request.Request(
        base + "residents?building=eq." + urllib.parse.quote(BUILDING, safe="") + "&select=unit,phone,source&limit=500",
        headers={"apikey": srk, "Authorization": "Bearer " + srk})
    return json.loads(urllib.request.urlopen(req, timeout=40).read() or b"[]")


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def show(current, people):
    shown = by_flat(current, people)
    print("  %d number(s): %s" % (len(current), ", ".join("%s x%d" % s for s in shown) or "nobody"))


def main():
    argv = sys.argv[1:]
    apply = "--apply" in argv
    argv = [a for a in argv if a != "--apply"]
    action, flats = None, []
    if argv:
        if argv[0] not in ("--add-flat", "--remove-flat") or len(argv) < 2:
            sys.exit("Usage: --add-flat <flat> [<flat> ...] | --remove-flat <flat> [<flat> ...]  [--apply]")
        action, flats = argv[0], argv[1:]
        if not all(re.fullmatch(r"\d{1,3}", f) for f in flats):
            sys.exit("A flat is its number, as residents.unit holds it.")

    e = env()
    token = e.get("SUPABASE_ACCESS_TOKEN", "").strip()
    ref = e["SUPABASE_URL"].strip().split("//")[1].split(".")[0]
    current = entries(e.get(NAME))
    people = residents(e)
    digest, key_on, types_on = live_digest(token, ref)
    same = digest == sha(",".join(current)) or digest == sha(e.get(NAME, ""))

    print("Copied into OXS: tickets from the numbers on %s." % NAME)
    print("  the mirror's key is %s on the live function; the every-reporter type switch is %s."
          % ("PRESENT" if key_on else "ABSENT (the mirror is off)", "ON" if types_on else "off"))
    print(".env's list:")
    show(current, people)
    print("  the live list %s" % ("is the same." if same else "IS NOT THE SAME as .env's." if digest else "is ABSENT."))

    if not action:
        if not same:
            sys.exit(1)
        return
    if not same:
        sys.exit("Refusing to change it: the live list and .env's differ. Find out which is right first.")

    picked = []
    for f in flats:
        ns = numbers_of(people, f)
        if not ns:
            sys.exit("Flat %s of the test building has no usable number on file." % f)
        picked += ns
    new = with_added(current, picked) if action == "--add-flat" else without(current, picked)
    if new == current:
        print("\nNothing to do: the list already is as asked.")
        return
    print("\n%s %s. The list would be:" % ("Adding" if action == "--add-flat" else "Removing",
                                           ", ".join("flat %s" % f for f in flats)))
    show(new, people)
    if not new:
        sys.exit("That would leave the list empty. To switch the mirror off, use supabase_functions.py --apply.")
    if not apply:
        print("Dry run. Re-run with --apply to write it. From then on these numbers' tickets open in OXS too.")
        return

    value = ",".join(new)
    os.makedirs(BACKUPS, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ")
    backup = os.path.join(BACKUPS, ".env.before-oxs-mirror-list-%s" % stamp)
    text = open(ENV_PATH, encoding="utf-8", newline="").read()
    with open(backup, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    with open(ENV_PATH, "w", encoding="utf-8", newline="") as f:
        f.write(env_with(text, NAME, value))
    print(".env          the one line rewritten (copy: %s)" % os.path.relpath(backup, ROOT))
    code, out = call(token, "POST", "/v1/projects/%s/secrets" % ref, [{"name": NAME, "value": value}])
    print("live secret   HTTP %s" % code)
    if code >= 300:
        print(out)
        sys.exit("The live list was NOT changed, and .env was. Put .env back from the copy, or run this again.")
    digest, _, _ = live_digest(token, ref)
    held = digest == sha(value)
    print("read back     the live list %s" % ("equals the new one." if held else "DOES NOT equal the new one."))
    if not held:
        sys.exit(1)


if __name__ == "__main__":
    main()
