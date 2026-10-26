"""Prove the sandbox (feature 19) leaves the live system alone. Reads only.

    python scripts/sandbox_fingerprint.py --save    local/sandbox/before.json
    python scripts/sandbox_fingerprint.py --compare local/sandbox/before.json

What is snapshotted is what the sandbox must never change:
- the 7 live n8n workflows: a hash of nodes, connections and settings, plus updatedAt and active;
- the live Edge Function `debt-tools`: its version and updated_at;
- the project's Edge Function secrets, names and a hash of each value (the sandbox deploy must
  never push or delete one; scripts/supabase_functions.py would);
- Chatwoot account 2: name, locale, inboxes, agent bots, labels, teams and attribute definitions;
- rows written since the snapshot for the sandbox personas' phones, in `requests`, `messages` and
  `interactions`. The sandbox must add none. A persona using live WhatsApp in the window also shows
  up here, so testers stay off the live number during a round.

--compare prints every difference and exits 1 if there is one.
"""
import hashlib, json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE_WORKFLOWS = ["u2JjrbcNPYyyh3yl", "oB66atFlWwtkSGgN", "lXofknAbE5wu5nwQ", "IVNR5iNn7bQS8JgP",
                  "i3VMdCnXZGooI1Dj", "pduAdXjX1EU7cA6E", "pvMuradcJOASapF0"]
LIVE_FUNCTION = "debt-tools"
LIVE_ACCOUNT = 2
# api.supabase.com sits behind Cloudflare, which rejects urllib's default User-Agent
UA = "curl/8.5.0"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def env():
    return dict((k.strip(), v.strip()) for k, v in
                (l.strip().split("=", 1) for l in open(os.path.join(ROOT, ".env"), encoding="utf-8")
                 if l.strip() and not l.startswith("#") and "=" in l))


def fetch(url, headers):
    req = urllib.request.Request(url, headers={**headers, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return dict(r.headers), r.read()


def getj(url, headers):
    return json.loads(fetch(url, headers)[1])


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def personas(e):
    """SANDBOX_PERSONAS='עידו:+972…,יריב:+972…' -> [(label, phone)]."""
    out = []
    for part in (e.get("SANDBOX_PERSONAS") or "").split(","):
        if ":" in part:
            label, phone = part.split(":", 1)
            out.append((label.strip(), phone.strip()))
    return out


def phone_forms(phone):
    """A PostgREST in-list of both stored forms: interactions.caller_phone has "+972…" since
    October and "972…" before it; messages.phone has the bare digits."""
    bare = phone.lstrip("+")
    return "(+%s,%s)" % (bare, bare)


def count(base, key, table, filters):
    q = "&".join(["select=id"] + ["%s=%s" % (k, urllib.parse.quote(v, safe=".:")) for k, v in filters])
    h, _ = fetch("%s/rest/v1/%s?%s" % (base, table, q),
                 {"apikey": key, "Authorization": "Bearer " + key, "Prefer": "count=exact", "Range": "0-0"})
    return int((h.get("Content-Range") or h.get("content-range") or "*/0").split("/")[-1])


def snapshot(since_iso):
    e = env()
    snap = {"taken_at": datetime.now(timezone.utc).isoformat(), "since": since_iso}
    n8 = e["N8N_BASE_URL"].rstrip("/")
    nh = {"X-N8N-API-KEY": e["N8N_API_KEY"], "accept": "application/json"}
    snap["n8n"] = {}
    for wid in LIVE_WORKFLOWS:
        w = getj("%s/api/v1/workflows/%s" % (n8, wid), nh)
        snap["n8n"][wid] = {"name": w["name"], "active": w.get("active"), "updatedAt": w.get("updatedAt"),
                            "hash": digest({"nodes": w["nodes"], "connections": w["connections"],
                                            "settings": w.get("settings")})}
    ref = e["SUPABASE_URL"].split("//")[1].split(".")[0]
    sh = {"Authorization": "Bearer " + e["SUPABASE_ACCESS_TOKEN"]}
    live = next(f for f in getj("https://api.supabase.com/v1/projects/%s/functions" % ref, sh)
                if f["slug"] == LIVE_FUNCTION)
    snap["function"] = {"slug": LIVE_FUNCTION, "version": live.get("version"), "updated_at": live.get("updated_at")}
    snap["secrets"] = {s["name"]: digest(s.get("value")) for s in
                       getj("https://api.supabase.com/v1/projects/%s/secrets" % ref, sh)}
    cw = e["CHATWOOT_URL"].rstrip("/") + "/api/v1/accounts/%d" % LIVE_ACCOUNT
    ch = {"api_access_token": e["CHATWOOT_API_TOKEN"]}
    acc = getj(cw, ch)
    snap["chatwoot"] = {
        "account": {"name": acc.get("name"), "locale": acc.get("locale")},
        "inboxes": sorted([i["id"], i["name"], i["channel_type"]] for i in getj(cw + "/inboxes", ch)["payload"]),
        "agent_bots": sorted([b["id"], b["name"], b.get("outgoing_url")] for b in getj(cw + "/agent_bots", ch)),
        "labels": sorted([l["title"], l.get("color"), l.get("description")] for l in getj(cw + "/labels", ch)["payload"]),
        "teams": sorted([t["id"], t["name"]] for t in getj(cw + "/teams", ch)),
        "attributes": sorted([a["attribute_key"], a["attribute_display_name"]]
                             for a in getj(cw + "/custom_attribute_definitions?attribute_model=0", ch)),
    }
    base, key = e["SUPABASE_URL"].rstrip("/"), e["SUPABASE_SERVICE_ROLE_KEY"]
    snap["persona_rows_since"] = {
        label: {
            "requests": count(base, key, "requests", [("reported_by_phone", "in." + phone_forms(phone)),
                                                      ("created_at", "gte." + since_iso)]),
            "messages": count(base, key, "messages", [("phone", "in." + phone_forms(phone)),
                                                      ("created_at", "gte." + since_iso)]),
            "interactions": count(base, key, "interactions", [("caller_phone", "in." + phone_forms(phone)),
                                                              ("started_at", "gte." + since_iso)]),
        } for label, phone in personas(e)}
    return snap


def compare(before, after):
    diffs = []
    for k in ("n8n", "function", "secrets", "chatwoot"):
        if before.get(k) != after.get(k):
            diffs.append("%s: %s -> %s" % (k, json.dumps(before.get(k), ensure_ascii=False)[:400],
                                          json.dumps(after.get(k), ensure_ascii=False)[:400]))
    for label, counts in after.get("persona_rows_since", {}).items():
        for table, n in counts.items():
            if n:
                diffs.append("%s: %d new %s row(s) since %s" % (label, n, table, before["since"]))
    return diffs


def main():
    if "--save" in sys.argv:
        path = sys.argv[sys.argv.index("--save") + 1]
        snap = snapshot(datetime.now(timezone.utc).isoformat())
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        json.dump(snap, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("saved %s | %d live workflows | debt-tools v%s | %d secrets | %d personas"
              % (path, len(snap["n8n"]), snap["function"]["version"], len(snap["secrets"]),
                 len(snap["persona_rows_since"])))
    elif "--compare" in sys.argv:
        before = json.load(open(sys.argv[sys.argv.index("--compare") + 1], encoding="utf-8"))
        diffs = compare(before, snapshot(before["since"]))
        print("live system unchanged" if not diffs else "\n".join(["CHANGED:"] + diffs))
        sys.exit(1 if diffs else 0)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
