# -*- coding: utf-8 -*-
"""Which server sends Chatwoot's email, set in the live /opt/chatwoot/.env.

    python scripts/chatwoot_smtp.py                  # dry run: which settings would change
    python scripts/chatwoot_smtp.py --apply          # back up the remote .env, write the
                                                     # settings, recreate sidekiq, read back
    python scripts/chatwoot_smtp.py --test-to ADDR   # one plain test mail, sent by sidekiq
    python scripts/chatwoot_smtp.py --provider brevo --apply    # the way back

WHY GMAIL (16 Nov 2026)
Chatwoot sends through Gmail's own server (smtp.gmail.com:587) as
testclix46@gmail.com, with an app password the owner made on that account
(GMAIL_APP_PASSWORD in this repo's .env).

From 6 Sep it went through Brevo's relay with the same From address. Homies'
Google mail filed the staff invites as spam, where Gmail switches links off (the
owner: "the email invitation was sent in the spam and is not clickable"). Brevo
can sign only for a domain authenticated with it, and nobody can authenticate
gmail.com, so nothing proved the mail came from Gmail. Mail that leaves from
Gmail's own server is signed by gmail.com and passes Google's check (DMARC).

The lasting version for go-live is a sender on Homies' own domain
(homies-management.co.il authenticated in Brevo; the DNS is theirs). Add it
here as a third provider then.

WHAT IT CHANGES
The SMTP_* lines and MAILER_SENDER_EMAIL in /opt/chatwoot/.env: replaced in place,
added if missing, after a dated backup. Then it recreates sidekiq alone, because
every mail Chatwoot sends goes out from a sidekiq job (invites and resets by
deliver_later in User#send_devise_notification, notifications the same way). So
the dashboard and Meta's webhooks keep running. rails takes the values at its next
recreate; it sends no mail itself.

Gmail's own limit is about 500 recipients a day. No password is ever printed: the
read-back compares sha256 digests and shows the last 3 characters.
"""
import hashlib
import os
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "root@186.240.147.235"
KEY = os.path.expanduser("~/.ssh/homies_vps")
REMOTE_DIR = "/opt/chatwoot"
REMOTE_ENV = REMOTE_DIR + "/.env"
SENDER = "Homies <testclix46@gmail.com>"

# provider -> (the settings, the name of the password in this repo's .env)
PROVIDERS = {
    "gmail": ({
        "MAILER_SENDER_EMAIL": SENDER,
        "SMTP_ADDRESS": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "testclix46@gmail.com",
        "SMTP_AUTHENTICATION": "plain",
        "SMTP_ENABLE_STARTTLS_AUTO": "true",
    }, "GMAIL_APP_PASSWORD"),
    # 6 Sep - 16 Nov 2026; lands in spam at Homies' Google mail (see WHY).
    "brevo": ({
        "MAILER_SENDER_EMAIL": SENDER,
        "SMTP_ADDRESS": "smtp-relay.brevo.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "b8166c001@smtp-brevo.com",
        "SMTP_AUTHENTICATION": "plain",
        "SMTP_ENABLE_STARTTLS_AUTO": "true",
    }, "SMTP_KEY"),
}

# The Brevo settings by their old name: n8n_standing_order_email.py imports them,
# and n8n still sends the standing-order email through Brevo.
VALUES = PROVIDERS["brevo"][0]

# Run by `rails runner` inside sidekiq, so it uses exactly the settings Chatwoot
# sends with. A bare ActionMailer subclass: no layout, no account needed.
TEST_MAIL_RB = r'''
class HomiesSmtpProbe < ActionMailer::Base
  def probe(to)
    mail(
      from: ENV.fetch("MAILER_SENDER_EMAIL"),
      to: to,
      subject: "בדיקת מייל מהמערכת של הומיז",
      body: "זו הודעת בדיקה. היא נשלחה כדי לבדוק שהמיילים של המערכת מגיעים לתיבה הרגילה ולא לספאם.\n\n" \
            "כניסה למערכת: #{ENV.fetch('FRONTEND_URL')}/app/login\n"
    )
  end
end
s = ActionMailer::Base.smtp_settings
m = HomiesSmtpProbe.probe(ARGV[0]).deliver_now
puts "accepted by #{s[:address]}:#{s[:port]} for #{s[:user_name]}, Message-ID #{m.message_id}"
'''


def env(path=".env"):
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def ssh(cmd, input_data=None, timeout=60):
    # Bytes both ways: a text-mode pipe on Windows turns every \n into \r\n, and the
    # 16 Nov run wrote the remote .env that way (compose reads it alike; fixed by hand).
    p = subprocess.run(
        ["ssh", "-i", KEY, "-o", "BatchMode=yes", HOST, cmd],
        input=input_data.encode("utf-8") if input_data is not None else None,
        capture_output=True, timeout=timeout)
    dec = lambda b: b.decode("utf-8", errors="replace")
    return p.returncode, dec(p.stdout), dec(p.stderr)


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def merge(text, values):
    """The remote .env with `values` written in: each key's lines replaced in place,
    missing keys appended. Returns (new text, sorted names of keys that change)."""
    lines = text.splitlines()
    seen, changed = set(), set()
    for i, ln in enumerate(lines):
        if ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        k = k.strip()
        if k in values:
            seen.add(k)
            if v != values[k]:
                lines[i] = "%s=%s" % (k, values[k])
                changed.add(k)
    for k, v in values.items():
        if k not in seen:
            lines.append("%s=%s" % (k, v))
            changed.add(k)
    return "\n".join(lines) + "\n", sorted(changed)


def read_back(values):
    """What the running sidekiq holds, the password as a digest only."""
    names = ["MAILER_SENDER_EMAIL", "SMTP_ADDRESS", "SMTP_PORT", "SMTP_USERNAME",
             "SMTP_PASSWORD"]
    rc, out, err = ssh("cd %s && docker compose exec -T sidekiq printenv %s"
                       % (REMOTE_DIR, " ".join(names)))
    got = out.splitlines()
    if rc != 0 or len(got) != len(names):
        sys.exit("read-back failed: %s" % (err or out))
    ok = True
    for name, val in zip(names, got):
        want = values[name]
        if name == "SMTP_PASSWORD":
            same = sha(val) == sha(want)
            print("  %-20s %s (...%s)" % (name, "matches .env" if same else "DIFFERS", val[-3:]))
        else:
            same = val == want
            print("  %-20s %s%s" % (name, val, "" if same else "   <- expected " + want))
        ok = ok and same
    return ok


def send_test(to):
    rc, out, err = ssh("cd %s && docker compose exec -T sidekiq sh -c 'cat > /tmp/homies_smtp_probe.rb'"
                       % REMOTE_DIR, input_data=TEST_MAIL_RB)
    if rc != 0:
        sys.exit("could not place the probe: %s" % err)
    rc, out, err = ssh("cd %s && docker compose exec -T sidekiq bundle exec rails runner "
                       "/tmp/homies_smtp_probe.rb '%s'; docker compose exec -T sidekiq rm -f "
                       "/tmp/homies_smtp_probe.rb" % (REMOTE_DIR, to.replace("'", "")), timeout=240)
    lines = [ln for ln in (out + err).splitlines() if ln.strip()]
    print("\n".join(lines[-6:]))
    if rc != 0 or not any(ln.startswith("accepted by") for ln in lines):
        sys.exit("test mail NOT sent")


def main():
    args = sys.argv[1:]
    provider = args[args.index("--provider") + 1] if "--provider" in args else "gmail"
    if provider not in PROVIDERS:
        sys.exit("provider must be one of %s" % sorted(PROVIDERS))
    settings, secret_name = PROVIDERS[provider]
    values = dict(settings)
    secret = env().get(secret_name, "").replace(" ", "")
    if not secret:
        sys.exit("%s is not in this repo's .env" % secret_name)
    values["SMTP_PASSWORD"] = secret

    if "--test-to" in args:
        send_test(args[args.index("--test-to") + 1])
        return

    rc, out, err = ssh("cat %s" % REMOTE_ENV)
    if rc != 0:
        sys.exit("could not read remote .env: %s" % err)
    new, changed = merge(out, values)
    print("provider: %s" % provider)
    print("settings that change: %s" % (", ".join(changed) or "none"))
    if changed and "--apply" not in args:
        print("\n(dry run -- pass --apply to write them and recreate sidekiq)")
        return
    if changed:
        rc, _, err = ssh("cp %s %s.bak-$(date +%%Y%%m%%d%%H%%M%%S)" % (REMOTE_ENV, REMOTE_ENV))
        if rc != 0:
            sys.exit("backup failed: %s" % err)
        rc, _, err = ssh("umask 077 && cat > %s.new && mv %s.new %s"
                         % (REMOTE_ENV, REMOTE_ENV, REMOTE_ENV), input_data=new)
        if rc != 0:
            sys.exit("write failed: %s" % err)
        print("wrote %s (backup beside it)" % REMOTE_ENV)
        rc, out, err = ssh("cd %s && docker compose up -d --no-deps --force-recreate sidekiq"
                           % REMOTE_DIR, timeout=240)
        if rc != 0:
            sys.exit("recreate failed: %s" % err)
        print("recreated sidekiq")
    print("running sidekiq holds:")
    if not read_back(values):
        sys.exit("sidekiq does NOT hold the expected settings")


if __name__ == "__main__":
    main()
