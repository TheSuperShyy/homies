# -*- coding: utf-8 -*-
"""The WhatsApp bot's regression gate: every rule it must keep and every bug it
has had, run against the exact code n8n runs. Read only. Spends nothing.

    python scripts/check_whatsapp_rules.py                           # the cases + pins, on live
    python scripts/check_whatsapp_rules.py --candidate F [F ...]     # on live + a patcher's --dump
    python scripts/check_whatsapp_rules.py --candidate F --replay    # + every real message, before vs after
    python scripts/check_whatsapp_rules.py --execution 65683         # on the workflow an execution ran
    python scripts/check_whatsapp_rules.py --watch 2026-09-27T13:17  # real turns since then, against the rules
    python scripts/check_whatsapp_rules.py --pins                    # print the model-text fingerprints

Exits non-zero on any failure, so it can gate a patcher's --apply.

WHY, 27 Sep. Owner: *"we need to make sure this wont open another bug we
always experiencing this issue we fix a bug it cause another one and loop
repeats"*. The loop had three causes, and each part of this file answers one.

  1. Every fix was tested once, in a temp folder, and the tests vanished; the
     next fix never re-ran them. -> THE CASES (check_whatsapp_rules.js) live
     in the repo and grow by one for every bug: the owner's greeting table,
     the 27 Sep turns, the deeds / echo / clerk guards, the payment ack's
     gate. They run the EXACT code from the workflow -- Sort's greeting test,
     Send's body, the guards, the notes -- never a copy of it.

  2. The 27 Sep regression was a change to text a MODEL reads (a note in
     `Worth a word?` told it to write a greeting back, and it started answering
     "hello" with an invented payment request). Tests of code cannot see what a
     model does with a sentence. -> THE PINS: a fingerprint of every text a
     model reads. Change one and this fails with "model-facing text changed".
     The way through is a replay of the real inputs that reach that model, with
     Claude playing it (never OpenRouter: testing spends nothing), and only then
     a new pin, printed by --pins.

  3. Nothing compared a change against everything that has really happened,
     and nothing looked at real traffic after a deploy: the owner found it. ->
     --replay runs every message ever received and every reply ever sent
     through the live code and the candidate and prints EVERY difference, so
     "only the intended ones changed" is checked, not assumed. --watch reads
     the real executions since a deploy and flags any turn that breaks the
     owner's rules.

HOW A WHATSAPP CHANGE SHIPS (CONTEXT.md, "How a WhatsApp change ships"):
  patcher --dump F  ->  this --candidate F --replay  ->  patcher --apply  ->
  this, on live  ->  the owner's handset  ->  this --watch <deploy time>, and
  again the next morning.

Real message texts are read at run time and handed to Node on stdin; they are
never written to disk. Links and phone numbers are masked in everything printed.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import n8n_whatsapp as W  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
JS = os.path.join(HERE, "check_whatsapp_rules.js")

# Every text a model reads, fingerprinted. A change fails the check until a
# replay has been done and the new value pasted here from --pins. The prompt,
# inject and tool texts are ALSO covered by MEMORY_EPOCH in n8n_whatsapp.py;
# that one decides whether memories restart, this one whether it was tested.
PINS = {
    'Answer the resident / input': '31ff6f4f297f',
    'Answer the resident / system': '8afa16824480',
    'Could not answer / input': 'd9c06797ffa6',
    'Could not answer / system': '79cd4d35fec8',
    'Say it again / input': '64f323ffcba1',
    'Say it again / system': 'e27b1450b7c0',
    'Try again / note': 'f11ade213910',
    'Worth a word? / input': '0d3156ee53a4',
    'Worth a word? / system': 'c9aaaa645060',
    'get_balance / tool': '510af1d70292',
    'get_payment_link / tool': '58ab6a539158',
    'get_request_status / tool': '76e812f28aaa',
    'get_service_info / tool': '6223a04ed17f',
    'notify_team / tool': '66859110a246',
    'open_request / tool': '8e8e45124b09',
    'show_menu / tool': '58aeda4b4677',
    'verify_address / tool': 'a2a85a3d4068',
}


# ---------------------------------------------------------------------------
# Reading workflows
# ---------------------------------------------------------------------------
def api(path):
    for attempt in range(3):
        try:
            return W.api("GET", path)
        except Exception:  # noqa: BLE001 -- a slow n8n is not a failed check
            if attempt == 2:
                raise
            time.sleep(2)


def load_live():
    return api("/api/v1/workflows/%s" % WORKFLOW_ID)


def load_candidate(files):
    """Live, with every node a patcher's --dump would change put in its place."""
    wf = load_live()
    idx = {n["name"]: i for i, n in enumerate(wf["nodes"])}
    for f in files:
        dumped = json.load(open(f, encoding="utf-8"))
        for n in dumped["nodes"]:
            i = idx.get(n["name"])
            if i is not None and wf["nodes"][i] != n:
                wf["nodes"][i] = n
                print("candidate: %s from %s" % (n["name"], os.path.basename(f)))
    return wf


def load_execution(eid):
    return api("/api/v1/executions/%s?includeData=true" % eid)["workflowData"]


def inner(expr):
    """The JavaScript between `={{` and `}}`."""
    s = (expr or "").strip()
    if s.startswith("="):
        s = s[1:].strip()
    if not (s.startswith("{{") and s.endswith("}}")):
        sys.exit("Not an n8n expression: %r" % s[:60])
    return s[2:-2].strip()


def extract(wf):
    """The code the harness runs, straight out of the workflow."""
    by = {n["name"]: n for n in wf["nodes"]}
    code = by["Sort"]["parameters"]["jsCode"]
    a = code.find("const bare = text.trim()")
    b = code.find("const isGreeting =", a)
    if a == -1 or b == -1:
        sys.exit("Sort's greeting test is not where this check expects it -- read the live code.")
    b = code.index(";", b) + 1

    def conds(name):
        return {c["id"]: inner(c["leftValue"])
                for c in by[name]["parameters"]["conditions"]["conditions"]}

    return {
        "sort_greeting": code[a:b],
        "send_body": inner(by["Send"]["parameters"]["jsonBody"]),
        "reply_usable": conds("Reply usable?"),
        "second_try": conds("Second try usable?"),
        "outage_gate": conds("Outage reply usable?"),
        "worth_text": inner(by["Worth a word?"]["parameters"]["text"]),
        "word_gate": inner(conds_raw(by, "A word first?", "word")),
        "inject": inner(by["Answer the resident"]["parameters"]["text"]),
        "try_again": inner(by["Try again"]["parameters"]["jsonOutput"]),
    }


def conds_raw(by, name, cid):
    for c in by[name]["parameters"]["conditions"]["conditions"]:
        if c.get("id") == cid:
            return c["leftValue"]
    sys.exit("No condition %r on %r." % (cid, name))


# ---------------------------------------------------------------------------
# The pins: every text a model reads
# ---------------------------------------------------------------------------
def model_texts(wf):
    by = {n["name"]: n for n in wf["nodes"]}
    out = {}
    for name in ("Answer the resident", "Worth a word?", "Say it again", "Could not answer"):
        p = by[name]["parameters"]
        out[name + " / system"] = (p.get("options") or {}).get("systemMessage") or ""
        out[name + " / input"] = p.get("text") or ""
    out["Try again / note"] = by["Try again"]["parameters"].get("jsonOutput") or ""
    for n in wf["nodes"]:
        if n["type"].endswith("Tool") or n["type"].endswith("toolCode"):
            p = n["parameters"]
            # The description and the parameter docs are what the model reads.
            out[n["name"] + " / tool"] = json.dumps(
                {k: p.get(k) or "" for k in ("toolDescription", "description", "jsonBody")},
                ensure_ascii=False, sort_keys=True)
    return out


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def check_pins(wf):
    now = {k: fingerprint(v) for k, v in model_texts(wf).items()}
    bad = sorted(k for k in set(now) | set(PINS) if now.get(k) != PINS.get(k))
    print("--- pins: every text a model reads ---")
    if not bad:
        print("all %d unchanged" % len(now))
        return 0
    for k in bad:
        print("FAIL model-facing text changed: %s  (%s -> %s)" % (k, PINS.get(k), now.get(k)))
    print("     Replay the real inputs that reach that model, with Claude playing it,")
    print("     then paste the new values from --pins. Never OpenRouter for the test.")
    return len(bad)


# ---------------------------------------------------------------------------
# The real history, read at run time, never written to disk
# ---------------------------------------------------------------------------
def rows(query):
    e = W.env()
    base = e["SUPABASE_URL"].rstrip("/") + "/rest/v1/"
    key = e["SUPABASE_SERVICE_ROLE_KEY"].strip()
    out, off = [], 0
    while True:
        req = urllib.request.Request(base + query, headers={
            "apikey": key, "Authorization": "Bearer " + key, "Range": "%d-%d" % (off, off + 999)})
        chunk = json.loads(urllib.request.urlopen(req, timeout=60).read() or b"[]")
        out += chunk
        if len(chunk) < 1000:
            return out
        off += 1000


def corpus():
    inbound = [r["body"] for r in rows("messages?direction=eq.inbound&select=body&order=created_at.asc")
               if r.get("body")]
    outbound = [r["body"] for r in rows("messages?direction=eq.outbound&sender=eq.bot&select=body"
                                        "&order=created_at.asc") if r.get("body")]
    return {"inbound": inbound, "outbound": outbound}


def node(payload):
    sys.stdout.flush()          # our lines first, then Node's
    r = subprocess.run(["node", JS], input=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    return r.returncode


# ---------------------------------------------------------------------------
# --watch: real turns since a moment, against the owner's rules
# ---------------------------------------------------------------------------
BOT_HELLO = re.compile(r"^(שלום רב|שלום|היי|הי|אהלן|בוקר טוב|צהריים טובים|ערב טוב|לילה טוב|שבוע טוב|"
                       r"שבת שלום|חג שמח|יום טוב)( לכם| לך| לכולם)?(?=[\s,.!:;]|$)")
LEAD = re.compile(r"^[\W_]+")
MENU = "👋 במה אפשר לעזור?"
PAY = re.compile(r"תשלום|לשלם|שילמ|קישור|לינק|חוב|יתרה|חשבון|pay|link|debt|balance|owe|bill|invoice",
                 re.I)
ECHO = re.compile(r"(^|[.!?,:]\s*)(אני מבין|אני מבינה|הבנתי|שמעתי)\s+ש")
CLERK = re.compile(r"כדי שאוכל|אצטרך")


def mask(s, n=110):
    s = re.sub(r"https?://\S+", "<link>", str(s))
    s = re.sub(r"\+?\d{9,15}", "<phone>", s)
    return re.sub(r"\s+", " ", s)[:n]


def watch(since):
    ids, cursor = [], None
    while True:
        page = api("/api/v1/executions?workflowId=%s&limit=100%s"
                   % (WORKFLOW_ID, "&cursor=%s" % cursor if cursor else ""))
        fresh = [x for x in page["data"] if x["startedAt"] >= since]
        ids += [x["id"] for x in fresh]
        cursor = page.get("nextCursor")
        if not cursor or len(fresh) < len(page["data"]):
            break
    flagged, turns, menus = 0, 0, []
    for eid in sorted(ids, key=int):
        ex = api("/api/v1/executions/%s?includeData=true" % eid)
        rd = ((ex.get("data") or {}).get("resultData") or {}).get("runData") or {}

        def first(name):
            try:
                return rd[name][0]["data"]["main"][0][0]["json"]
            except Exception:  # noqa: BLE001
                return None

        def items(name):
            try:
                return [i["json"] for i in rd[name][0]["data"]["main"][0]]
            except Exception:  # noqa: BLE001
                return None

        S = first("Sort") or {}
        if S.get("text") is None and S.get("greeting") is not True:
            continue                      # a delivery receipt, not a resident's message
        turns += 1
        canned = S.get("greeting") is True
        sent = []
        for name, kind in (("Say it now", "ack"), ("Send", "menu" if canned else "answer"),
                           ("Send the rest", "rest")):
            j = first(name)
            if j and j.get("content"):
                sent.append((kind, str(j["content"])))
        prev = next((str(r.get("body") or "") for r in (items("Anything newer?") or [])
                     if r.get("direction") == "outbound"), "")
        after_menu = MENU in prev or "במה אפשר לעזור" in str(S.get("last_bot") or "")
        flags = []
        hellos = [k for k, t in sent if BOT_HELLO.match(LEAD.sub("", t))]
        if len(hellos) > 1:
            flags.append("two greetings in one turn (%s)" % " + ".join(hellos))
        if not canned and after_menu and sent and BOT_HELLO.match(LEAD.sub("", sent[0][1])):
            flags.append("a greeting right after the menu (%s)" % sent[0][0])
        if not canned and S.get("greeted") is True and not after_menu:
            named = [k for k, t in sent if "מיכאל" in t]
            if named:
                flags.append("the name mid-conversation (%s)" % " + ".join(named))
        if first("Say it now"):
            said = str((first("Carry on") or {}).get("text") or S.get("text") or "")
            if not PAY.search(said):
                flags.append("a payment ack on a message with no payment words")
        for k, t in sent:
            if ECHO.search(t):
                flags.append("'I understand that...' in the %s%s"
                             % (k, " (known gap: the ack's own wording)" if k == "ack" else ""))
            if CLERK.search(t):
                flags.append("the clerk's 'so that I can / I will need' in the %s" % k)
        if "Tell the team the bot is down" in rd:
            flags.append("the outage path ran")
        if ex.get("status") != "success":
            flags.append("execution status: %s" % ex.get("status"))
        if "Still the last word?" in rd and items("Still the last word?") == []:
            newest_in = next((r for r in (items("Anything newer?") or [])
                              if r.get("direction") == "inbound"), None)
            if newest_in and newest_in.get("message_type") == "greeting":
                flags.append("a real message stood down for a greeting (it may go unanswered)")
        if canned:
            menus.append((str(S.get("to")), ex["startedAt"], eid))
        if flags:
            flagged += 1
            print("FLAG %s  %s UTC" % (eid, ex["startedAt"][:19].replace("T", " ")))
            for f in flags:
                print("     - " + f)
            print("     resident: " + mask(S.get("text") or ""))
            for k, t in sent:
                print("     %-8s: %s" % (k, mask(t)))
    menus.sort()
    for (a, ta, ia), (b, tb, ib) in zip(menus, menus[1:]):
        if a == b and _secs(ta, tb) <= 20:
            flagged += 1
            print("FLAG %s + %s  two menus to one resident within 20 s" % (ia, ib))
    print("")
    print("watched %d resident turns since %s: %s" % (
        turns, since, "%d flagged" % flagged if flagged else "nothing broke the rules"))
    return flagged


def _secs(a, b):
    from datetime import datetime
    f = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))  # noqa: E731
    return abs((f(b) - f(a)).total_seconds())


# ---------------------------------------------------------------------------
def main():
    argv = sys.argv[1:]
    if "--watch" in argv:
        since = argv[argv.index("--watch") + 1]
        sys.exit(1 if watch(since) else 0)

    if "--candidate" in argv:
        i = argv.index("--candidate") + 1
        files = []
        while i < len(argv) and not argv[i].startswith("--"):
            files.append(argv[i])
            i += 1
        wf, label = load_candidate(files), "candidate"
    elif "--execution" in argv:
        eid = argv[argv.index("--execution") + 1]
        wf, label = load_execution(eid), "the workflow execution %s ran" % eid
    else:
        wf, label = load_live(), "live"

    if "--pins" in argv:
        print("PINS = {")
        for k, v in sorted(model_texts(wf).items()):
            print("    %r: %r," % (k, fingerprint(v)))
        print("}")
        return

    print("checking %s" % label)
    print("")
    bad = check_pins(wf)
    print("")
    bad += 1 if node({"mode": "cases", "code": extract(wf)}) else 0
    if "--replay" in argv:
        print("")
        print("=== replay: every real message, live code vs %s ===" % label)
        bad += 1 if node({"mode": "replay", "live": extract(load_live()), "cand": extract(wf),
                          "corpus": corpus()}) else 0
    print("")
    print("RESULT: %s" % ("FAILED" if bad else "all green"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
