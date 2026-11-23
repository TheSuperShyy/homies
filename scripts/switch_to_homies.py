# -*- coding: utf-8 -*-
"""Move the WhatsApp bot from our test number ("hadas 1") onto Homies' own number, 077-668-7949 (prepared 23 Nov 2026).

    python scripts/switch_to_homies.py              # preflight, read only: both sides, and whether the move would validate
    python scripts/switch_to_homies.py --apply      # THE SWITCH. Refuses while ManyChat's app is still connected,
                                                    #   unless --manychat-is-off says its WhatsApp replies are off,
                                                    #   and without --app-is-published (their app must be published:
                                                    #   Meta sends an unpublished app no real messages, and that
                                                    #   can't be read from here)
    python scripts/switch_to_homies.py --restore    # back to "hadas 1", and Homies' number handed back to ManyChat

WHY. The owner, 23 Nov: "so right now just prepare everything but dont disconnect everything". Homies' token (system
user "CLIX", app HOMIES, never expires) is in .env as HOMIES_WHATSAPP_TOKEN / _WABA_ID, and the four templates were
submitted on their account that morning. Their number is already on the Cloud API, so nothing is re-registered and
no PIN is needed. Today only ManyChat's app is subscribed to their account (read 23 Nov).

HOW, the way 2 Nov and 10 Nov moved inbox 1 (WORKLOG):
  1. Chatwoot's inbox 1 takes their number through its own model (rails runner on the VPS): phone_number,
     phone_number_id, business_account_id and api_key = Homies' token. The webhook verify token is kept.
     Saving validates against Meta (a read) and runs no remote setup.
  2. Chatwoot's Whatsapp::WebhookSetupService#register_callback, with that token: POST /{their WABA}/subscribed_apps
     (messages, smb_message_echoes) for Homies' HOMIES app, then the phone-level override to
     <chatwoot>/webhooks/whatsapp/<their number>. From then on Meta sends their number's messages to Chatwoot.
  3. The channel's template sync (their WABA's templates).
  If any step fails, the channel is put back as it was, in the same run.
  4. Their app's OWN webhook: POST /{their app}/subscriptions with an app token (HOMIES_APP_SECRET), object
     whatsapp_business_account, the messages field, callback = the override register_callback just set, and inbox 1's
     verify token (CHATWOOT_WA_VERIFY_TOKEN, checked against the inbox by digest). Meta's docs subscribe webhook fields
     at the app level and subscribed_apps documents none of its own (read 23 Nov); their app had none, so without this
     step nothing may arrive. --apply refuses without the secret unless --app-webhook-by-hand says someone sets it in
     their Meta (the app's WhatsApp -> Configuration page). If it fails, the message says: by hand, or --restore.
The two typing nodes in n8n are scripts/n8n_whatsapp_tohomies.py, run after this. Inbound and replies go through
Chatwoot, and the tool server sends through inbox 1, so nothing else names the number.

--restore: the channel back to the snapshot's number and ids with our own token (WHATSAPP_ACCESS_TOKEN, checked against
the snapshot's digest), register_callback for our app, the template sync; then, with Homies' token, their override
cleared and their HOMIES app unsubscribed from their WABA, so ManyChat has the number alone again; and their app's own
webhook removed, when the snapshot says it had none before.

The snapshot (local/switch-homies-snapshot.json, ignored by git) holds numbers and ids, never a token.
"""
import base64
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.join(ROOT, "local", "switch-homies-snapshot.json")
SSH = ["ssh", "-i", os.path.join(os.path.expanduser("~"), ".ssh", "homies_vps"), "-o", "BatchMode=yes",
       "-o", "ConnectTimeout=15", "root@186.240.147.235"]
GRAPH = "https://graph.facebook.com/v21.0"
INBOX_ID = 1
TEMPLATES = ("ticket_resolved_he", "payment_link_he", "homies_hello_he", "homies_message_he")
APP_OBJECT = "whatsapp_business_account"


def env():
    out = {}
    for line in io.open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def sha(s):
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:12]


def mask(v, keep=4):
    v = str(v or "")
    return ("…" + v[-keep:]) if v else "-"


def graph(token, method, path, body=None, **q):
    q["access_token"] = token
    url = GRAPH + path + "?" + urllib.parse.urlencode(q)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, method=method, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        err = json.loads(e.read().decode("utf-8", "replace") or "{}").get("error", {})
        return {"_http": e.code, "_error": "%s %s" % (err.get("code"), (err.get("message") or "")[:160])}


RUBY = r'''
require 'json'; require 'base64'; require 'digest'
P = JSON.parse(Base64.decode64(%q(__PAYLOAD__)))
inbox = Inbox.find(P['inbox_id'])
ch = inbox.channel
raise "inbox #{inbox.id} is not a WhatsApp Cloud channel" unless ch.is_a?(Channel::Whatsapp) && ch.provider == 'whatsapp_cloud'
def state(ch)
  pc = ch.provider_config || {}
  { 'phone_number' => ch.phone_number, 'phone_number_id' => pc['phone_number_id'],
    'business_account_id' => pc['business_account_id'],
    'api_key_sha' => Digest::SHA256.hexdigest(pc['api_key'].to_s)[0, 12],
    'verify_token_set' => pc['webhook_verify_token'].present?,
    'verify_token_sha' => Digest::SHA256.hexdigest(pc['webhook_verify_token'].to_s)[0, 12],
    'templates' => (ch.message_templates || []).map { |t| [t['name'], t['status']] } }
end
out = { 'mode' => P['mode'], 'before' => state(ch) }
if %w[check apply].include?(P['mode'])
  t = P['target']
  old_phone, old_pc = ch.phone_number, ch.provider_config.dup
  ch.phone_number = t['phone_number']
  ch.provider_config = old_pc.merge('phone_number_id' => t['phone_number_id'],
                                    'business_account_id' => t['business_account_id'], 'api_key' => t['api_key'])
  if P['mode'] == 'check'
    out['valid'] = ch.valid?
    out['errors'] = ch.errors.full_messages
    ch.reload
  else
    step = 'save'
    begin
      ch.save!
      step = 'register_callback'
      Whatsapp::WebhookSetupService.new(ch).register_callback
      step = 'sync_templates'
      ch.sync_templates
      out['after'] = state(ch.reload)
    rescue StandardError => e
      out['error'] = "#{step}: #{e.message}"[0, 400]
      ch.reload
      ch.phone_number = old_phone
      ch.provider_config = old_pc
      ch.save!(validate: false)
      out['reverted'] = state(ch.reload)
    end
  end
elsif P['mode'] == 'restore'
  t = P['target']
  ch.phone_number = t['phone_number']
  ch.provider_config = ch.provider_config.merge('phone_number_id' => t['phone_number_id'],
                                                'business_account_id' => t['business_account_id'], 'api_key' => t['api_key'])
  ch.save!
  Whatsapp::WebhookSetupService.new(ch).register_callback
  ch.sync_templates
  out['after'] = state(ch.reload)
end
puts 'SWITCH_JSON=' + out.to_json
'''


def rails(payload):
    code = RUBY.replace("__PAYLOAD__", base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii"))
    remote = ("umask 077 && cat > /tmp/sw.rb && docker cp /tmp/sw.rb chatwoot-rails-1:/tmp/sw.rb && rm -f /tmp/sw.rb && "
              "docker exec chatwoot-rails-1 bundle exec rails runner /tmp/sw.rb; "
              "docker exec chatwoot-rails-1 rm -f /tmp/sw.rb")
    run = subprocess.run(SSH + [remote], input=code.encode("utf-8"), capture_output=True, timeout=300)
    out = run.stdout.decode("utf-8", "replace")
    line = next((l for l in out.splitlines() if l.startswith("SWITCH_JSON=")), None)
    if not line:
        sys.exit("rails runner gave no SWITCH_JSON line:\n" + out[-1500:] + run.stderr.decode("utf-8", "replace")[-1500:])
    return json.loads(line.split("=", 1)[1])


def show_channel(label, s):
    print("%s: %s | number id %s | account %s | key %s | verify token %s | %d templates"
          % (label, (s.get("phone_number") or "")[:6] + "…" + (s.get("phone_number") or "")[-3:],
             mask(s.get("phone_number_id")), mask(s.get("business_account_id")), s.get("api_key_sha"),
             "kept" if s.get("verify_token_set") else "MISSING", len(s.get("templates") or [])))


def homies_side(e):
    """Their token, number, templates and connected apps, read with their own token."""
    tok, waba = e.get("HOMIES_WHATSAPP_TOKEN", ""), e.get("HOMIES_WHATSAPP_WABA_ID", "")
    if not tok or not waba.isdigit():
        sys.exit("HOMIES_WHATSAPP_TOKEN / HOMIES_WHATSAPP_WABA_ID are not both set in .env.")
    d = graph(tok, "GET", "/debug_token", input_token=tok).get("data", {})
    print("their token : %s, app %s, valid %s, expires %s, %s"
          % (d.get("type"), d.get("application"), d.get("is_valid"),
             "never" if d.get("expires_at") == 0 else d.get("expires_at"),
             ", ".join(s for s in d.get("scopes", []) if s.startswith("whatsapp_business_m"))))
    phones = graph(tok, "GET", "/%s/phone_numbers" % waba,
                   fields="id,display_phone_number,verified_name,status,platform_type,quality_rating,name_status")
    if "_http" in phones or len(phones.get("data", [])) != 1:
        sys.exit("their WABA's numbers: %s" % phones)
    p = phones["data"][0]
    e164 = "+" + re.sub(r"\D", "", p["display_phone_number"])
    print("their number: %s…%s (id %s) | %s %s | quality %s | name %s"
          % (e164[:6], e164[-3:], mask(p["id"]), p.get("status"), p.get("platform_type"),
             p.get("quality_rating"), p.get("name_status")))
    tl = graph(tok, "GET", "/%s/message_templates" % waba, fields="name,status,category", limit=100)
    have = {t["name"]: t["status"] for t in tl.get("data", [])}
    print("templates   : " + ", ".join("%s %s" % (n, have.get(n, "MISSING")) for n in TEMPLATES))
    apps = graph(tok, "GET", "/%s/subscribed_apps" % waba)
    names = [a.get("whatsapp_business_api_data", {}).get("name") for a in apps.get("data", [])]
    print("connected   : %s" % (", ".join(names) or "no app"))
    return {"token": tok, "waba": waba, "phone_id": p["id"], "e164": e164, "templates": have, "apps": names,
            "app_id": str(d.get("app_id") or ""), "app_name": d.get("application")}


def describe_subs(subs):
    if not subs:
        return "none"
    return "; ".join("%s, active %s, fields %s" % (urllib.parse.urlparse(s.get("callback_url") or "").netloc or "-",
                                                   s.get("active"), ",".join(f.get("name", "?") for f in s.get("fields", [])))
                     for s in subs)


def their_app(e, h):
    """Their app's own webhook, read with an app token (app id|HOMIES_APP_SECRET). None without the secret."""
    app_id = h["app_id"]
    if e.get("HOMIES_APP_ID") and e["HOMIES_APP_ID"] != app_id:
        sys.exit("HOMIES_APP_ID in .env (%s) is not the app of their token (%s)." % (mask(e["HOMIES_APP_ID"]), mask(app_id)))
    secret = e.get("HOMIES_APP_SECRET", "")
    if not secret:
        print("their app   : %s %s | secret MISSING (HOMIES_APP_SECRET), so its own webhook can't be set from here"
              % (h["app_name"], mask(app_id)))
        return None
    app_tok = "%s|%s" % (app_id, secret)
    d = graph(app_tok, "GET", "/debug_token", input_token=h["token"])
    if not (d.get("data", {}).get("is_valid") and str(d.get("data", {}).get("app_id")) == app_id):
        sys.exit("HOMIES_APP_SECRET does not open app %s: %s" % (mask(app_id), d.get("_error") or d))
    subs = graph(app_tok, "GET", "/%s/subscriptions" % app_id)
    if "_http" in subs:
        sys.exit("their app's subscriptions: %s" % subs["_error"])
    wa = [s for s in subs.get("data", []) if s.get("object") == APP_OBJECT]
    print("their app   : %s %s | secret OK | own webhook: %s" % (h["app_name"], mask(app_id), describe_subs(wa)))
    return {"id": app_id, "token": app_tok, "before": wa}


def main():
    e = env()
    restore = "--restore" in sys.argv
    apply = "--apply" in sys.argv
    by_hand = "--app-webhook-by-hand" in sys.argv
    h = homies_side(e)
    app = their_app(e, h)

    if restore:
        if not os.path.exists(SNAPSHOT):
            sys.exit("No snapshot at %s: nothing was switched by this script." % SNAPSHOT)
        snap = json.load(open(SNAPSHOT, encoding="utf-8"))
        ours = e.get("WHATSAPP_ACCESS_TOKEN", "")
        if sha(ours) != snap["api_key_sha"]:
            sys.exit("WHATSAPP_ACCESS_TOKEN in .env is not the key inbox 1 had before the switch (digest differs). Refusing.")
        res = rails({"mode": "restore", "inbox_id": INBOX_ID, "target": {
            "phone_number": snap["phone_number"], "phone_number_id": snap["phone_number_id"],
            "business_account_id": snap["business_account_id"], "api_key": ours}})
        show_channel("inbox %d now" % INBOX_ID, res["after"])
        cleared = graph(h["token"], "POST", "/%s" % h["phone_id"],
                        {"webhook_configuration": {"override_callback_uri": ""}})
        unsub = graph(h["token"], "DELETE", "/%s/subscribed_apps" % h["waba"])
        print("their override cleared: %s | their HOMIES app unsubscribed: %s" % (cleared, unsub))
        if app and snap.get("their_app_webhook_before") == []:
            gone = graph(app["token"], "DELETE", "/%s/subscriptions" % app["id"], object=APP_OBJECT)
            print("their app's own webhook removed (it had none before): %s" % gone)
        elif "their_app_webhook_before" in snap and snap["their_app_webhook_before"]:
            print("NOTE        : their app had its own webhook before the switch (%s); left as it is now."
                  % describe_subs(snap["their_app_webhook_before"]))
        print("Restored. Turn ManyChat's WhatsApp replies back on, and send a test to each number.")
        return

    now = rails({"mode": "read", "inbox_id": INBOX_ID})["before"]
    show_channel("inbox %d now" % INBOX_ID, now)
    if now["phone_number"] == h["e164"]:
        print("Nothing to do: inbox %d already has Homies' number." % INBOX_ID)
        return
    target = {"phone_number": h["e164"], "phone_number_id": h["phone_id"], "business_account_id": h["waba"],
              "api_key": h["token"]}
    check = rails({"mode": "check", "inbox_id": INBOX_ID, "target": target})
    print("would move  : inbox %d to %s…%s, their number id and account, their token; verify token kept"
          % (INBOX_ID, h["e164"][:6], h["e164"][-3:]))
    print("validates   : %s%s" % (check.get("valid"), (" (" + "; ".join(check.get("errors") or []) + ")") if check.get("errors") else ""))
    missing = [n for n in TEMPLATES if h["templates"].get(n) != "APPROVED"]
    if missing:
        print("NOTE        : not approved yet on their account: %s (the bot's replies need none)" % ", ".join(missing))
    others = [n for n in h["apps"] if (n or "").upper() != "HOMIES"]
    if others:
        print("NOTE        : still connected to their number: %s. Both would answer, so its WhatsApp replies go off first."
              % ", ".join(others))
    vt = e.get("CHATWOOT_WA_VERIFY_TOKEN", "")
    vt_ok = bool(vt) and sha(vt) == now.get("verify_token_sha")
    print("verify token: inbox %d's %s CHATWOOT_WA_VERIFY_TOKEN in .env" % (INBOX_ID, "matches" if vt_ok else "does NOT match"))
    if app and vt_ok:
        print("would set   : their app's own webhook (%s, messages) to the address register_callback sets, right after it"
              % APP_OBJECT)
    elif not by_hand:
        print("NOTE        : --apply refuses until HOMIES_APP_SECRET (and a matching verify token) are in .env, or add"
              " --app-webhook-by-hand if someone sets the app's webhook in their Meta during the switch.")

    print("CHECK BY EYE: their app is PUBLISHED (no yellow 'unpublished' box on its WhatsApp setup page). Meta sends an"
          " unpublished app no real messages (seen 23 Nov). --apply needs --app-is-published.")

    if not apply:
        print("\nDry run: nothing written, in Chatwoot or at Meta.")
        return
    if not check.get("valid"):
        sys.exit("The move does not validate in Chatwoot. Refusing.")
    if "--app-is-published" not in sys.argv:
        sys.exit("Refusing: confirm their app is published, then add --app-is-published. Unpublished, it gets no real "
                 "messages, so the number would go silent.")
    if others and "--manychat-is-off" not in sys.argv:
        sys.exit("Refusing while %s is connected. Turn its WhatsApp replies off, then add --manychat-is-off." % ", ".join(others))
    if not (app and vt_ok) and not by_hand:
        sys.exit("Refusing: their app's own webhook can't be set from here (see the NOTE above).")

    os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
    if not os.path.exists(SNAPSHOT):
        snap = {k: now[k] for k in ("phone_number", "phone_number_id", "business_account_id", "api_key_sha")}
        if app:
            snap["their_app_webhook_before"] = [{"object": s.get("object"), "active": s.get("active"),
                                                 "callback_url": urllib.parse.urlparse(s.get("callback_url") or "").netloc,
                                                 "fields": s.get("fields", [])} for s in app["before"]]
        json.dump(snap, open(SNAPSHOT, "w", encoding="utf-8"), indent=1)
        print("snapshot    : %s" % os.path.relpath(SNAPSHOT, ROOT))
    res = rails({"mode": "apply", "inbox_id": INBOX_ID, "target": target})
    if res.get("error"):
        show_channel("put back", res.get("reverted") or {})
        sys.exit("FAILED at %s. Inbox %d is back on the test number." % (res["error"], INBOX_ID))
    show_channel("inbox %d now" % INBOX_ID, res["after"])
    apps = graph(h["token"], "GET", "/%s/subscribed_apps" % h["waba"])
    wc = graph(h["token"], "GET", "/%s" % h["phone_id"], fields="webhook_configuration").get("webhook_configuration", {})
    print("connected   : %s" % ", ".join(a.get("whatsapp_business_api_data", {}).get("name") or "?" for a in apps.get("data", [])))
    callback = wc.get("phone_number") or ""
    print("their number's messages go to: %s" % urllib.parse.urlparse(callback).netloc)
    if app and vt_ok:
        if not callback:
            sys.exit("FAILED: no phone-level override to copy, so their app's own webhook was not set. "
                     "Set it by hand, or roll back now: --restore, then ManyChat's replies on.")
        res2 = graph(app["token"], "POST", "/%s/subscriptions" % app["id"], object=APP_OBJECT,
                     callback_url=callback, verify_token=vt, fields="messages")
        if res2.get("_http") or not res2.get("success"):
            sys.exit("FAILED: their app's own webhook: %s. Messages may not reach Chatwoot. Set it by hand (their app -> "
                     "WhatsApp -> Configuration: the callback above, inbox 1's verify token, the messages field), or roll "
                     "back now: --restore, then ManyChat's replies on." % (res2.get("_error") or res2))
        subs = graph(app["token"], "GET", "/%s/subscriptions" % app["id"])
        print("their app's own webhook: %s" % describe_subs([s for s in subs.get("data", []) if s.get("object") == APP_OBJECT]))
    else:
        print("NOW BY HAND : their app -> WhatsApp -> Configuration: callback %s, inbox 1's verify token, the messages "
              "field. Nothing may arrive until it is set." % urllib.parse.urlparse(callback).netloc)
    print("Switched. Next: scripts/n8n_whatsapp_tohomies.py (typing), then a test message from a phone.")


if __name__ == "__main__":
    main()
