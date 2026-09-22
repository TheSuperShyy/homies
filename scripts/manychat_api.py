# -*- coding: utf-8 -*-
"""ManyChat -- read the client's old WhatsApp bot from here. GET only.

    python scripts/manychat_api.py            # page, flows, tags, fields, growth tools, widgets, OTN, bot fields
    python scripts/manychat_api.py fields     # the custom fields as a table: id, name, type, English gloss
    python scripts/manychat_api.py export     # the same page-level data as JSON in docs/handover/, redacted

Same road as make_api.py: the token lives in .env as MANYCHAT_API_KEY, nothing
here writes, and a write helper -- if one is ever wanted -- gets its own flag
and its own explicit go. ManyChat is the client's account (the bot Nir built
in 2024, live on the real number), and the standing rule is never to write to
client systems unasked.

SAFETY
  Read-only by construction: the one HTTP helper below sends GET and never
  passes a body, and every path it is given is one of the 13 GET endpoints
  in ManyChat's own spec (https://api.manychat.com/swagger/compileJson?type=Page_API,
  read 22 Sep 2026). The other 21 paths -- sendFlow, sendContent, setCustomField,
  addTag, createSubscriber, ... -- do not appear in this file. One host,
  api.manychat.com. The key is never printed. No subscriber endpoint is
  called: this script reads the bot's shape (flows, fields, tags), never a
  resident's record.

WHAT THE API CAN AND CANNOT SHOW
  It lists the bot's nouns: the flows by name and namespace, the custom fields
  the bot fills, tags, growth tools (entry links), widgets, OTN topics, bot
  fields, and the page. It does NOT return a flow's content -- steps, message
  wording, buttons, conditions -- there is no such endpoint. The branches are
  read in the ManyChat editor (the owner, 22 Sep) and written up in
  docs/discovery/manychat-scan-2026-09-22.md; this script supplies the exact
  names and ids behind them.
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "api.manychat.com"
OUT = os.path.join(ROOT, "docs", "handover", "manychat-export-%s.json" % datetime.date.today().isoformat())

# The 8 page-level GET endpoints, in the order the overview prints them.
PAGE_GETS = [
    ("info", "/fb/page/getInfo"),
    ("flows", "/fb/page/getFlows"),
    ("tags", "/fb/page/getTags"),
    ("custom_fields", "/fb/page/getCustomFields"),
    ("growth_tools", "/fb/page/getGrowthTools"),
    ("widgets", "/fb/page/getWidgets"),
    ("otn_topics", "/fb/page/getOtnTopics"),
    ("bot_fields", "/fb/page/getBotFields"),
]

# English glosses for the field names the old bot uses (Hebrew verbatim).
# A name not listed here prints with an empty gloss rather than a guess.
GLOSS = {
    "כתובת": "address",
    "כמות קומות בבניין": "floors in the building",
    "כמות דיירים בבניין": "flats / residents in the building",
    "שם מלא": "full name",
    "קומת הדייר": "resident's floor",
    "דירת הדייר": "resident's flat",
    "חברת המעליות בבניין": "the building's elevator company",
    "סיכום דיווח אחרון": "summary of the last report",
    "דיווח למעלית": "elevator fault report",
    "קריאה לאב הבית": "call for the house manager (אב הבית)",
    "טלפון": "phone",
    "תמונה": "photo (URL)",
    "תמונה אריי": "photos (array)",
}


def env():
    return dict(
        l.strip().split("=", 1)
        for l in open(os.path.join(ROOT, ".env"), encoding="utf-8")
        if l.strip() and not l.startswith("#") and "=" in l
    )


def token():
    t = (env().get("MANYCHAT_API_KEY") or "").strip().strip('"')
    if not t:
        sys.exit("MANYCHAT_API_KEY is not set in .env")
    return t


def api(path, params=None):
    """GET one of ManyChat's read endpoints. There is no other HTTP call in this file."""
    url = "https://%s%s" % (HOST, path)
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token(),
        "User-Agent": "homies/1.0",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as ex:
        body = ex.read().decode("utf-8", "replace")
        sys.exit("HTTP %d on %s\n%s" % (ex.code, path, body[:600]))


def page():
    """Every page-level read, as {name: data}."""
    return {name: api(path).get("data") for name, path in PAGE_GETS}


def overview():
    p = page()
    info = p["info"] or {}
    print("page         :", info.get("name"), "| pro:", info.get("is_pro"), "| tz:", info.get("timezone"),
          "| username:", info.get("username") or "-")
    flows = (p["flows"] or {}).get("flows") or []
    folders = (p["flows"] or {}).get("folders") or []
    print("\nflows        : %d  (folders: %d)" % (len(flows), len(folders)))
    for f in flows:
        print("  %-34s %s" % (f.get("ns"), f.get("name")))
    for f in folders:
        print("  folder %-27s %s" % (f.get("id"), f.get("name")))
    for name in ("tags", "custom_fields", "growth_tools", "widgets", "otn_topics", "bot_fields"):
        rows = p[name] or []
        print("\n%-13s: %d" % (name, len(rows)))
        for r in rows:
            extra = " ".join("%s=%s" % (k, r[k]) for k in ("type",) if r.get(k))
            print("  %-10s %s  %s" % (r.get("id"), r.get("name"), extra))
    print("\nRead only. Flow CONTENT (steps, wording, buttons) is not an API endpoint;"
          " see docs/discovery/manychat-scan-2026-09-22.md.")


def fields():
    rows = api("/fb/page/getCustomFields").get("data") or []
    print("%-10s %-6s %-24s %s" % ("id", "type", "name", "gloss"))
    for r in rows:
        print("%-10s %-6s %-24s %s" % (r.get("id"), r.get("type"), r.get("name"), GLOSS.get(r.get("name"), "")))
    print("\n%d custom fields" % len(rows))


def secrets():
    """Every .env value that could open something, longest first. Mirrors vapi_export.py:
    short values (ids, flags, numbers) are not secrets and are not matched."""
    out = []
    for k, v in env().items():
        v = v.strip().strip('"')
        if len(v) >= 12 and not v.isdigit():
            out.append((k, v))
    return sorted(out, key=lambda kv: -len(kv[1]))


def export():
    data = page()
    text = json.dumps(data, ensure_ascii=False, indent=2)
    known = secrets()
    for k, v in known:
        text = text.replace(v, "<redacted:%s>" % k)
    left = [k for k, v in known if v in text]
    if left:
        sys.exit("REFUSING TO WRITE. These .env values survived redaction: %s" % ", ".join(left))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text + "\n")
    print("wrote %s (%d bytes; page-level only, no subscriber data; %d .env values checked)"
          % (os.path.relpath(OUT, ROOT), len(text.encode("utf-8")), len(known)))


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        overview()
    elif a[0] == "fields":
        fields()
    elif a[0] == "export":
        export()
    else:
        sys.exit(__doc__)
