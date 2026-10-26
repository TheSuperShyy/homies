"""Deploy debt-tools-sandbox (feature 19): the live debt-tools code, unchanged,
behind supabase/functions/debt-tools-sandbox/guard.ts.

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


def files():
    """(uploaded name, path). app.ts IS the live index.ts."""
    return [("index.ts", os.path.join(SBX, "index.ts")),
            ("guard_install.ts", os.path.join(SBX, "guard_install.ts")),
            ("guard.ts", os.path.join(SBX, "guard.ts")),
            ("app.ts", os.path.join(LIVE, "index.ts")),
            ("identity.ts", os.path.join(LIVE, "identity.ts")),
            ("route.ts", os.path.join(LIVE, "route.ts"))]


def deploy(e):
    token = e["SUPABASE_ACCESS_TOKEN"]
    ref = e["SUPABASE_URL"].split("//")[1].split(".")[0]
    parts = [("metadata", None, json.dumps({"name": SLUG, "entrypoint_path": "index.ts",
                                            "verify_jwt": False}).encode(), "application/json")]
    for name, path in files():
        parts.append(("file", name, open(path, "rb").read(), "application/typescript"))
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


def main():
    e = env()
    for name, path in files():
        print("%-17s %6d bytes  sha %s" % (name, os.path.getsize(path), hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]))
    assert open(os.path.join(LIVE, "index.ts"), "rb").read() == open(files()[3][1], "rb").read()
    if "--apply" in sys.argv:
        deploy(e)
    elif "--probe" in sys.argv:
        probe(e)
    else:
        print("\nDry run. --apply deploys the files (no secrets); --probe calls the deployed sandbox.")


if __name__ == "__main__":
    main()
