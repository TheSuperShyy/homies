"""Deploy debt-tools-sandbox (feature 19): the live debt-tools code behind
supabase/functions/debt-tools-sandbox/guard.ts, plus the named APP_EDITS below.
Since 29 Oct app.ts is the live index.ts with those edits (the balance recognises
the sender), the way the bot copy is the live workflow plus section 6. Promoting
an edit to live means making it in debt-tools/index.ts.

    python scripts/sandbox_function.py           # dry run: the files and their hashes
    python scripts/sandbox_function.py --apply   # deploy (files only)
    python scripts/sandbox_function.py --probe   # three tool calls against the sandbox

It NEVER touches project secrets. scripts/supabase_functions.py pushes and
deletes project-wide secrets on every run (a plain run deletes OXS_KEY_REQUESTS
and so switches off the live mirror). This script only uploads files.
"""
import hashlib, json, os, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from supabase_functions import call, env, multipart  # helpers only; that script's main() is not run

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, "supabase", "functions", "debt-tools")
SBX = os.path.join(ROOT, "supabase", "functions", "debt-tools-sandbox")
SLUG = "debt-tools-sandbox"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# 29 Oct (the owner, "i thought we have auto recognition", then "go"): the owner's chat as Ido asked for
# a name and a phone for the balance, then answered "the details do not match" to Ido's own number,
# because "ido clix" is not עידו קליקס word for word. In the sandbox the balance now takes the number
# the message came from, on file for one resident, as that resident (the payment link's identity and a
# ticket's), and reads a typed number only when it is another one. A name typed in Latin letters is
# compared by its consonants (names.ts). Each anchor must occur exactly once.
RECOGNISE = '''    if (channel(ctx) === "whatsapp") {
      // SANDBOX, 29 Oct: the number the message came from, on file for one resident, is that
      // resident, as for the payment link and a ticket. A typed number is read only when it is
      // another one.
      const sender = reporterPhone(ctx);
      const typed = typedPhoneOf(args?.phone);
      if (sender && (!typed || typed === sender)) {
        const { data: own } = await db.from("residents").select(fields)
          .eq("phone", sender).maybeSingle();
        if (own) {
          resident = own;
          askedUnit = unitOf(args?.unit);
        }
      }
    }
    if (!resident && channel(ctx) === "whatsapp") {
      const given = String(args?.name ?? "").trim();'''
APP_EDITS = [
    ('import { callDirection, debtVariables, FIXED_DEFAULTS, isDialerCall, routeOf } from "./route.ts";',
     'import { callDirection, debtVariables, FIXED_DEFAULTS, isDialerCall, routeOf } from "./route.ts";\n'
     'import { sameNameAnyScript } from "./names.ts";'),
    ('    if (channel(ctx) === "whatsapp") {\n      const given = String(args?.name ?? "").trim();', RECOGNISE),
    ("if (!data || !sameName(data.full_name, given)) {", "if (!data || !sameNameAnyScript(data.full_name, given)) {"),
]


def app_source():
    """The live index.ts with APP_EDITS applied."""
    text = open(os.path.join(LIVE, "index.ts"), encoding="utf-8").read().replace("\r\n", "\n")
    for old, new in APP_EDITS:
        assert text.count(old) == 1, "APP_EDITS anchor moved in debt-tools/index.ts: %r" % old[:60]
        text = text.replace(old, new)
    return text.encode("utf-8")


def files():
    """(uploaded name, bytes). app.ts is the live index.ts plus APP_EDITS."""
    def read(*p):
        return open(os.path.join(*p), "rb").read()
    return [("index.ts", read(SBX, "index.ts")),
            ("guard_install.ts", read(SBX, "guard_install.ts")),
            ("guard.ts", read(SBX, "guard.ts")),
            ("names.ts", read(SBX, "names.ts")),
            ("app.ts", app_source()),
            ("identity.ts", read(LIVE, "identity.ts")),
            ("route.ts", read(LIVE, "route.ts"))]


def deploy(e):
    token = e["SUPABASE_ACCESS_TOKEN"]
    ref = e["SUPABASE_URL"].split("//")[1].split(".")[0]
    parts = [("metadata", None, json.dumps({"name": SLUG, "entrypoint_path": "index.ts",
                                            "verify_jwt": False}).encode(), "application/json")]
    for name, data in files():
        parts.append(("file", name, data, "application/typescript"))
    body, ctype = multipart(parts)
    code, out = call(token, "POST", "/v1/projects/%s/functions/deploy?slug=%s" % (ref, SLUG), body, ctype)
    meta = out if isinstance(out, dict) else {}
    print("deploy HTTP %s | version %s | status %s" % (code, meta.get("version"), meta.get("status")))
    if code >= 300:
        print(out); sys.exit(1)


def tool(e, phone, name, args):
    bare = phone.lstrip("+")
    envelope = {"message": {"call": {"id": "wa:" + bare, "assistantOverrides": {"variableValues": {"phone": bare}}},
                            "toolCalls": [{"id": "wa", "function": {"name": name, "arguments": args}}]}}
    req = urllib.request.Request(e["SUPABASE_URL"].rstrip("/") + "/functions/v1/" + SLUG, method="POST",
                                 data=json.dumps(envelope).encode(),
                                 headers={"x-homies-secret": e["TOOL_SECRET"],
                                          "content-type": "application/json", "User-Agent": "homies/1.0"})
    out = json.loads(urllib.request.urlopen(req, timeout=60).read())
    return json.loads(out["results"][0]["result"])


def probe(e):
    label, phone = [p.split(":", 1) for p in e["SANDBOX_PERSONAS"].split(",")][0]
    print("as", label, phone[:4] + "…" + phone[-3:])
    status = tool(e, phone, "get_request_status", {"reference": "", "building": ""})
    print("get_request_status ->", json.dumps(status, ensure_ascii=False)[:200])
    opened = tool(e, phone, "open_request", {"description": "בדיקת סביבת ניסוי: נורה שרופה בלובי", "type": "lighting",
                                             "building": "בר כוכבא 23", "reporter_unit": "1",
                                             "reporter_name": label, "fault_location": "common",
                                             "urgency": "normal"})
    print("open_request ->", json.dumps(opened, ensure_ascii=False)[:300])
    ref = str(opened.get("reference", ""))
    assert ref.startswith("999-9"), "open_request did not come back with a sandbox reference (999-9…)"
    link = tool(e, phone, "get_payment_link", {})
    print("get_payment_link ->", json.dumps({k: (v[:24] + "…" if k == "link" else v) for k, v in link.items()},
                                            ensure_ascii=False)[:200])
    # A link already on record in payment_links is READ and handed back (`reused`), as live does.
    # A new one would need OXS, which mints a link per call; the guard refuses that call.
    assert link.get("reused") or not str(link.get("link") or "").startswith("http"), "a NEW payment link came back"
    k = e["SUPABASE_SERVICE_ROLE_KEY"]
    q = e["SUPABASE_URL"].rstrip("/") + "/rest/v1/requests?select=id&reference=eq." + urllib.parse.quote(ref)
    rows = json.loads(urllib.request.urlopen(urllib.request.Request(
        q, headers={"apikey": k, "Authorization": "Bearer " + k}), timeout=60).read())
    assert rows == [], "a sandbox ticket reached the live requests table"
    print("probe ok: reads work, the ticket was faked (%s, no row), no new payment link%s"
          % (ref, " (the one on record was reused)" if link.get("reused") else ""))
    # 29 Oct, APP_EDITS: the balance recognises the sender. Reads only; no model is called.
    people = [p.split(":", 1) for p in e["SANDBOX_PERSONAS"].split(",")]
    stranger = next(ph for lb, ph in people if ph not in {p[1] for p in people[:3]})
    blank = {"name": "", "phone": "", "unit": ""}
    known = tool(e, phone, "get_balance", blank)
    print("get_balance as %s, nothing typed -> found %s%s" % (label, known.get("found"),
          "" if known.get("found") else " " + json.dumps(known)[:120]))
    assert known.get("found") == 1, "the sender on file was not recognised"
    asked = tool(e, stranger, "get_balance", blank)
    print("get_balance from a number not on file -> need_identity %s" % asked.get("need_identity"))
    assert asked.get("need_identity") and not asked.get("found"), "a number not on file was not asked who they are"
    latin = tool(e, stranger, "get_balance", {"name": "ido clix", "phone": phone, "unit": ""})
    print("get_balance, 'ido clix' with Ido's number typed from another phone -> found %s" % latin.get("found"))
    assert latin.get("found") == 1, "a name in English letters for a number on file was refused"
    wrong = tool(e, stranger, "get_balance", {"name": "dan cohen", "phone": phone, "unit": ""})
    print("get_balance, a wrong name with Ido's number -> identity_failed %s" % wrong.get("identity_failed"))
    assert wrong.get("identity_failed") and not wrong.get("found"), "a wrong name passed"
    print("balance probe ok: the sender recognised, a stranger asked, a Latin name taken, a wrong name refused")


def main():
    e = env()
    for name, data in files():
        print("%-17s %6d bytes  sha %s" % (name, len(data), hashlib.sha256(data).hexdigest()[:12]))
    print("app.ts = debt-tools/index.ts + %d APP_EDITS (the balance recognises the sender)" % len(APP_EDITS))
    if "--apply" in sys.argv:
        deploy(e)
    elif "--probe" in sys.argv:
        probe(e)
    else:
        print("\nDry run. --apply deploys the files (no secrets); --probe calls the deployed sandbox.")


if __name__ == "__main__":
    main()
