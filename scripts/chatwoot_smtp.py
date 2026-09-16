# -*- coding: utf-8 -*-
"""Add Brevo SMTP settings to the live Chatwoot .env and restart the app.

    python scripts/chatwoot_smtp.py            # dry run: prints what would change
    python scripts/chatwoot_smtp.py --apply    # backs up the remote .env, appends
                                                # the SMTP_* + MAILER_SENDER_EMAIL
                                                # lines (skips ones already there),
                                                # and restarts rails + sidekiq

WHY
Chatwoot has never had outbound mail: SMTP_* is absent from
/opt/chatwoot/.env, so invites, password resets and the mention/assignment
email channel (docs/features/16-human-handover) have never worked. Feature
16's escalation ladder and every seat's notification preferences already
assume email exists once SMTP is set.

WHAT IT WRITES
Six lines appended to /opt/chatwoot/.env on the VPS (never overwritten if a
key is already present -- rerun is a no-op then), and a restart of the two
containers that read it. The value source is this repo's own .env
(SMTP_KEY, the Brevo SMTP key) plus the fixed values from the Brevo SMTP page
and the verified sender.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "root@186.240.147.235"
KEY = os.path.expanduser("~/.ssh/homies_vps")
REMOTE_ENV = "/opt/chatwoot/.env"

VALUES = {
    "MAILER_SENDER_EMAIL": "Homies <testclix46@gmail.com>",
    "SMTP_ADDRESS": "smtp-relay.brevo.com",
    "SMTP_PORT": "587",
    "SMTP_USERNAME": "b8166c001@smtp-brevo.com",
    "SMTP_AUTHENTICATION": "plain",
    "SMTP_ENABLE_STARTTLS_AUTO": "true",
}


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


def ssh(cmd, input_data=None):
    p = subprocess.run(
        ["ssh", "-i", KEY, "-o", "BatchMode=yes", HOST, cmd],
        input=input_data, capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout, p.stderr


def main():
    apply_ = "--apply" in sys.argv
    smtp_key = env()["SMTP_KEY"]
    values = dict(VALUES)
    values["SMTP_PASSWORD"] = smtp_key

    rc, out, err = ssh("cat %s" % REMOTE_ENV)
    if rc != 0:
        sys.exit("could not read remote .env: %s" % err)
    existing_keys = {ln.split("=", 1)[0] for ln in out.splitlines()
                     if ln.strip() and not ln.startswith("#") and "=" in ln}

    missing = {k: v for k, v in values.items() if k not in existing_keys}
    print("already present: %s" % sorted(set(values) - set(missing)))
    print("to add: %s" % sorted(missing))
    if not missing:
        print("nothing to do")
        return
    if not apply_:
        print("\n(dry run -- pass --apply to write and restart)")
        return

    block = "\n" + "\n".join("%s=%s" % (k, v) for k, v in missing.items()) + "\n"
    backup_cmd = "cp %s %s.bak-$(date +%%Y%%m%%d%%H%%M%%S)" % (REMOTE_ENV, REMOTE_ENV)
    rc, out, err = ssh(backup_cmd)
    if rc != 0:
        sys.exit("backup failed: %s" % err)
    rc, out, err = ssh("cat >> %s" % REMOTE_ENV, input_data=block)
    if rc != 0:
        sys.exit("append failed: %s" % err)
    print("appended %d line(s) to %s" % (len(missing), REMOTE_ENV))

    rc, out, err = ssh("cd /opt/chatwoot && docker compose up -d rails sidekiq")
    print(out)
    if rc != 0:
        sys.exit("restart failed: %s" % err)
    print("restarted rails + sidekiq")


if __name__ == "__main__":
    main()
