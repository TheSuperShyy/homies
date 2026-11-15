# -*- coding: utf-8 -*-
"""Put Chatwoot's invite email in Hebrew on the live box (15 Nov 2026).

    python scripts/chatwoot_invite_he.py            # dry run: says what would change
    python scripts/chatwoot_invite_he.py --apply    # uploads, recreates sidekiq, checks

WHY
The owner: "make it natural local hebrew". Chatwoot's invite is English text
written into its template; only Devise's subject ("הוראות אישור") followed the
account's language. Rails renders a template's .he variant over the plain one
when the mail renders in Hebrew, and Chatwoot's mailer renders in the account's
language (he). So one added file does it, and Chatwoot's own file is never edited.

WHAT IT WRITES (on the VPS, under /opt/chatwoot)
  overrides/confirmation_instructions.he.html.erb   from deploy/chatwoot/overrides/
  docker-compose.override.yml                       from deploy/chatwoot/
A file already there that differs is kept as .bak-<time> first. `docker compose
config` must pass, or the change is rolled back. Then only sidekiq is recreated
(--no-deps): invites go out with deliver_later, so the job renders them, and
rails (the dashboard, Meta's webhooks) keeps running. Jobs wait in Redis
meanwhile. Production Rails caches templates, so a changed template needs this
recreate too.

CHECKS after --apply: the file inside the sidekiq container has the repo's
sha256, and sidekiq says it is processing again. To see the email itself, render
it read-only, as on 15 Nov (WORKLOG): in the rails container, from a temporary
view path, an in-memory user, .message (renders, never delivers).

UNDO: delete both files on the box, then
`cd /opt/chatwoot && docker compose up -d --no-deps sidekiq`.
"""
import hashlib
import os
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "root@186.240.147.235"
KEY = os.path.expanduser("~/.ssh/homies_vps")
REMOTE = "/opt/chatwoot"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = [
    ("deploy/chatwoot/overrides/confirmation_instructions.he.html.erb",
     "overrides/confirmation_instructions.he.html.erb"),
    ("deploy/chatwoot/docker-compose.override.yml", "docker-compose.override.yml"),
]
CONTAINER = "chatwoot-sidekiq-1"
IN_CONTAINER = "/app/app/views/devise/mailer/confirmation_instructions.he.html.erb"


def ssh(cmd, data=None, timeout=180):
    p = subprocess.run(
        ["ssh", "-i", KEY, "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", HOST, cmd],
        input=data, capture_output=True, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def local_bytes(path):
    with open(os.path.join(ROOT, path), "rb") as f:
        return f.read().replace(b"\r\n", b"\n")  # a Windows checkout must not change the hash


def sha(data):
    return hashlib.sha256(data).hexdigest()


def remote_sha(cmd):
    rc, out, _ = ssh(cmd)
    return out.split()[0] if rc == 0 and out.strip() else None


def main():
    apply_ = "--apply" in sys.argv
    stamp = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    plan = []
    for local, remote in FILES:
        data = local_bytes(local)
        there = remote_sha("sha256sum %s/%s 2>/dev/null" % (REMOTE, remote))
        state = "same" if there == sha(data) else ("differs" if there else "missing")
        print("%-50s %s" % (remote, state))
        if state != "same":
            plan.append((remote, data, state))
    template = local_bytes(FILES[0][0])
    inside = remote_sha("docker exec %s sha256sum %s 2>/dev/null" % (CONTAINER, IN_CONTAINER))
    live = inside == sha(template)
    print("%-50s %s" % ("inside " + CONTAINER, "same" if live else ("differs" if inside else "missing")))
    if not plan and live:
        print("\nNothing to do: the Hebrew invite is live.")
        return
    if not apply_:
        print("\n(dry run -- pass --apply to upload and recreate sidekiq)")
        return

    rc, _, err = ssh("mkdir -p %s/overrides" % REMOTE)
    if rc:
        sys.exit("mkdir failed: %s" % err)
    undo = []
    for remote, data, state in plan:
        path = "%s/%s" % (REMOTE, remote)
        if state == "differs":
            rc, _, err = ssh("cp -p %s %s.bak-%s" % (path, path, stamp))
            if rc:
                sys.exit("backup of %s failed: %s" % (remote, err))
            undo.append("cp -p %s.bak-%s %s" % (path, stamp, path))
        else:
            undo.append("rm -f %s" % path)
        rc, _, err = ssh("cat > %s" % path, data=data)
        if rc:
            sys.exit("upload of %s failed: %s" % (remote, err))
        print("uploaded %s" % remote)

    rc, _, err = ssh("cd %s && docker compose config --quiet" % REMOTE)
    if rc:
        for cmd in undo:
            ssh(cmd)
        sys.exit("docker compose config refused the change, rolled back:\n%s" % err)
    rc, out, err = ssh("cd %s && docker compose config sidekiq 2>/dev/null | grep -c confirmation_instructions.he" % REMOTE)
    print("compose config: valid; the mount is in sidekiq's config (%s line)" % out.strip())

    print("recreating sidekiq (rails keeps running) ...")
    rc, out, err = ssh("cd %s && docker compose up -d --no-deps --force-recreate sidekiq" % REMOTE, timeout=300)
    if rc:
        sys.exit("recreate failed: %s\n%s" % (out, err))

    # A recreated container starts a fresh log. Sidekiq's boot line, or any job it
    # has run (a scheduled one comes every minute), shows it is processing.
    deadline = time.time() + 180
    started = False
    while time.time() < deadline:
        rc, out, _ = ssh("docker logs %s 2>&1 | grep -cE 'Starting processing|Performed '" % CONTAINER)
        if rc == 0 and out.strip() not in ("", "0"):
            started = True
            break
        time.sleep(5)
    rc, state, _ = ssh("docker inspect -f '{{.State.Status}} since {{.State.StartedAt}}' %s" % CONTAINER)
    print("sidekiq: %s; processing: %s" % (state.strip(), "yes" if started else "NOT YET SEEN"))

    inside = remote_sha("docker exec %s sha256sum %s 2>/dev/null" % (CONTAINER, IN_CONTAINER))
    print("template inside sidekiq: %s" % ("same as the repo" if inside == sha(template) else "MISSING OR DIFFERENT"))
    if inside != sha(template) or not started:
        sys.exit(1)


if __name__ == "__main__":
    main()
