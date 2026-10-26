"""Create and set up the sandbox Chatwoot account (feature 19). Idempotent.

    python scripts/chatwoot_sandbox.py           # what it would create
    python scripts/chatwoot_sandbox.py --apply   # create, then read back

1. rails runner over SSH: Account "Homies — Sandbox", a sandbox admin user
   (owner of the sandbox tokens), and the owner's own login as an administrator
   of the sandbox only, so the owner can open it in the UI. Account 2 is not touched.
   Chatwoot opens whichever account was used last (active_at DESC NULLS LAST),
   so the owner's login keeps opening account 2 until the sandbox is opened.
2. API, with the sandbox admin token:
   - Hebrew name and locale;
   - an API inbox;
   - the agent bot "מיכאל — ניסוי", pointed at n8n /webhook/homies-whatsapp-sandbox?s=<secret>;
   - four Hebrew teams with both users;
   - the eight labels, with their English titles kept (the bot depends on them),
     Hebrew descriptions and colours by urgency;
   - the conversation attributes, copied by key with Hebrew display names.
The one call to account 2 is a read: GET its attribute definitions.
"""
import json, os, secrets, shlex, subprocess, sys, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from supabase_functions import env, set_env

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SSH = ["ssh", "-i", os.path.join(os.path.expanduser("~"), ".ssh", "homies_vps"), "-o", "BatchMode=yes",
       "-o", "ConnectTimeout=15", "root@186.240.147.235"]
ACCOUNT_NAME = "Homies — Sandbox"
HEBREW_NAME = "הומי'ז — סביבת ניסוי"
INBOX_NAME = "צ'אט ניסוי"
BOT_NAME = "מיכאל — ניסוי"
TEAMS = {"collections": ("גבייה", "תשלומים, חובות והסדרים"),
         "operations": ("תפעול ותקלות", "תקלות ובקשות תחזוקה בבניין"),
         "management": ("הנהלה", "ועד, חוזים והסלמות"),
         "service": ("שירות לדיירים", "פניות כלליות של דיירים")}
LABELS = [("after-hours", "#7F8C8D", "הגיע מחוץ לשעות הפעילות; ההתראה תצא ב-09:00"),
          ("bot-off", "#2563EB", "הבוט כבוי בשיחה הזו, נציג מטפל"),
          ("escalated", "#C0392B", "לא נענה בזמן, הועבר גם להנהלה"),
          ("handover", "#E67E22", "הועבר לנציג"),
          ("handover-collections", "#E67E22", "הועבר לגבייה"),
          ("handover-management", "#E67E22", "הועבר להנהלה"),
          ("handover-operations", "#E67E22", "הועבר לתפעול ותקלות"),
          ("handover-service", "#E67E22", "הועבר לשירות לדיירים")]
ATTR_HE = {"handover_at": "הועבר לנציג ב", "handover_reason": "סיבת ההעברה",
           "handover_department": "מחלקה", "handover_source": "מקור ההעברה",
           "handover_paged_at": "התראה נשלחה ב", "handover_escalation": "רמת הסלמה",
           "handover_answered_at": "נענה ב", "handover_channel": "ערוץ",
           "handover_reasons": "סיבות ההעברה"}

RUBY = r'''
require "securerandom"
acc = Account.find_by(name: "Homies — Sandbox") || Account.create!(name: "Homies — Sandbox", locale: "he")
email = "sandbox-admin@homies-sandbox.test"
u = User.find_by(email: email)
unless u
  u = User.new(name: "Sandbox Admin", email: email, password: SecureRandom.hex(12) + "Aa1!")
  u.skip_confirmation!
  u.save!
end
AccountUser.find_or_create_by!(account_id: acc.id, user_id: u.id) { |au| au.role = :administrator }
owner = User.find_by(email: ENV.fetch("OWNER_EMAIL", ""))
AccountUser.find_or_create_by!(account_id: acc.id, user_id: owner.id) { |au| au.role = :administrator } if owner
token = (u.access_token || u.create_access_token).token
puts "SANDBOX_JSON=" + { account_id: acc.id, admin_user_id: u.id, owner_user_id: owner&.id, admin_token: token }.to_json
'''


def rails(owner_email):
    remote = ("cat > /tmp/sbx.rb && docker cp /tmp/sbx.rb chatwoot-rails-1:/tmp/sbx.rb && "
              "docker exec -e OWNER_EMAIL=%s chatwoot-rails-1 bundle exec rails runner /tmp/sbx.rb; "
              "rm -f /tmp/sbx.rb; docker exec chatwoot-rails-1 rm -f /tmp/sbx.rb" % shlex.quote(owner_email))
    run = subprocess.run(SSH + [remote], input=RUBY.encode(), capture_output=True, timeout=300)
    out = run.stdout.decode("utf-8", "replace")
    line = next((l for l in out.splitlines() if l.startswith("SANDBOX_JSON=")), None)
    if not line:
        sys.exit("rails runner gave no SANDBOX_JSON line:\n" + out[-1500:] + run.stderr.decode("utf-8", "replace")[-1500:])
    return json.loads(line.split("=", 1)[1])


def api(base, token, method, path, body=None):
    req = urllib.request.Request(base + path, method=method,
                                 data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None,
                                 headers={"api_access_token": token, "Content-Type": "application/json",
                                          "User-Agent": "homies/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as x:
        sys.exit("%s %s -> HTTP %s %s" % (method, path, x.code, x.read()[:400].decode("utf-8", "replace")))


def main():
    e = env()
    apply = "--apply" in sys.argv
    cw = e["CHATWOOT_URL"].rstrip("/")
    secret = e.get("SANDBOX_WEBHOOK_SECRET", "") or secrets.token_urlsafe(24)
    hook = e["N8N_BASE_URL"].rstrip("/") + "/webhook/homies-whatsapp-sandbox?s=" + secret
    print("account %s (%s) | inbox %s | bot %s -> …/homies-whatsapp-sandbox | %d teams | %d labels"
          % (ACCOUNT_NAME, HEBREW_NAME, INBOX_NAME, BOT_NAME, len(TEAMS), len(LABELS)))
    if not apply:
        print("Dry run. --apply creates it."); return
    made = rails(e["CHATWOOT_ADMIN_EMAIL"])
    acc, tok = made["account_id"], made["admin_token"]
    assert acc != 2, "the sandbox account must not be account 2"
    base = cw + "/api/v1/accounts/%d" % acc
    users = [u for u in (made["admin_user_id"], made.get("owner_user_id")) if u]
    api(base, tok, "PATCH", "", {"name": HEBREW_NAME, "locale": "he"})
    inbox = next((i for i in api(base, tok, "GET", "/inboxes")["payload"] if i["name"] == INBOX_NAME), None) \
        or api(base, tok, "POST", "/inboxes", {"name": INBOX_NAME, "channel": {"type": "api", "webhook_url": ""}})
    bot = next((b for b in api(base, tok, "GET", "/agent_bots") if b["name"] == BOT_NAME), None)
    if bot:
        bot = api(base, tok, "PATCH", "/agent_bots/%d" % bot["id"], {"outgoing_url": hook})
    else:
        bot = api(base, tok, "POST", "/agent_bots", {"name": BOT_NAME, "description": "Feature 19 sandbox", "outgoing_url": hook})
    assert bot.get("access_token"), "the agent bot API returned no access_token"
    api(base, tok, "POST", "/inboxes/%d/set_agent_bot" % inbox["id"], {"agent_bot": bot["id"]})
    have = {t["name"]: t["id"] for t in api(base, tok, "GET", "/teams")}
    team_ids = {}
    for key, (name, desc) in TEAMS.items():
        tid = have.get(name) or api(base, tok, "POST", "/teams", {"name": name, "description": desc})["id"]
        api(base, tok, "POST", "/teams/%d/team_members" % tid, {"user_ids": users})
        team_ids[key] = tid
    have = {l["title"] for l in api(base, tok, "GET", "/labels")["payload"]}
    for title, color, desc in LABELS:
        if title not in have:
            api(base, tok, "POST", "/labels", {"title": title, "description": desc, "color": color, "show_on_sidebar": True})
    live = api(cw + "/api/v1/accounts/2", e["CHATWOOT_API_TOKEN"], "GET",
               "/custom_attribute_definitions?attribute_model=0")
    have = {a["attribute_key"] for a in api(base, tok, "GET", "/custom_attribute_definitions?attribute_model=0")}
    for a in live:
        if a["attribute_key"] not in have:
            api(base, tok, "POST", "/custom_attribute_definitions", {
                "attribute_display_name": ATTR_HE.get(a["attribute_key"], a["attribute_display_name"]),
                "attribute_display_type": a["attribute_display_type"], "attribute_description": a.get("attribute_description") or "",
                "attribute_key": a["attribute_key"], "attribute_model": 0,
                **({"attribute_values": a["attribute_values"]} if a.get("attribute_values") else {})})
    for k, v in {"SANDBOX_CW_ACCOUNT_ID": acc, "SANDBOX_CW_ADMIN_USER_ID": made["admin_user_id"],
                 "SANDBOX_CW_ADMIN_TOKEN": tok, "SANDBOX_CW_BOT_TOKEN": bot["access_token"],
                 "SANDBOX_CW_INBOX_ID": inbox["id"], "SANDBOX_CW_INBOX_IDENTIFIER": inbox["inbox_identifier"],
                 "SANDBOX_WEBHOOK_SECRET": secret, "SANDBOX_CW_TEAMS": json.dumps(team_ids)}.items():
        set_env(k, str(v))
    back = api(base, tok, "GET", "")
    print("account %d: %s, locale %s | inbox %d | bot %d | teams %s | owner added: %s"
          % (acc, back["name"], back["locale"], inbox["id"], bot["id"], team_ids, bool(made.get("owner_user_id"))))


if __name__ == "__main__":
    main()
