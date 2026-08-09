#!/usr/bin/env python
"""Create the Vercel project for dashboard/ and deploy it from GitHub.

Reads VERCEL_TOKEN from .env, and the two NEXT_PUBLIC_ values from
dashboard/.env.local so the deployed app points at the same Supabase project
the local build does. Stdlib only — nothing to install, and the Vercel CLI
never gets to write .vercel/ into the repo.

Four things this gets right that are easy to get wrong:

  rootDirectory is "dashboard". The app is not at the repo root. Without this
  Vercel builds the repository, finds no package.json, and fails with a
  framework-detection error that says nothing about the real cause.

  The env vars are set BEFORE the first deployment. Next.js inlines every
  NEXT_PUBLIC_ value at build time, so a build that ran without them produces
  a bundle with `undefined` baked in — which then fails at runtime, not build
  time, and looks like a Supabase outage rather than a missing variable.

  Only the anon key goes up. It is public by design and belongs in the browser
  bundle; every table it can reach is gated by the RLS policies in
  supabase/009_dashboard_access.sql. The service role key bypasses RLS and must
  never reach Vercel — this script reads dashboard/.env.local, which does not
  contain it, and refuses if a service key somehow appears there.

  A git-linked project does not deploy itself. Creating it registers the repo;
  the first build still has to be asked for. Later pushes to main deploy on
  their own.

    python scripts/vercel_deploy.py            # show what would happen
    python scripts/vercel_deploy.py --apply    # do it
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, ".env")
LOCAL_ENV = os.path.join(ROOT, "dashboard", ".env.local")
API = "https://api.vercel.com"

PROJECT = "homies-dashboard"
ROOT_DIR = "dashboard"
REPO = "TheSuperShyy/homies"
REPO_ID = 1323863006
BRANCH = "main"

# The only two variables the dashboard reads. Anything not on this list is not
# copied to Vercel, which is the mechanism that keeps the service role key out.
WANTED = ["NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY"]
TARGETS = ["production", "preview", "development"]


def read_env(path):
    d = {}
    if not os.path.exists(path):
        return d
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def call(token, method, path, body=None, team=None):
    if team:
        path += ("&" if "?" in path else "?") + "teamId=" + team
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API + path, data=data, method=method,
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=120)
        raw = r.read().decode("utf-8", "replace")
        return r.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"error": {"message": raw[:400]}}


def err(out):
    if isinstance(out, dict):
        return (out.get("error") or {}).get("message") or json.dumps(out)[:300]
    return str(out)[:300]


def main():
    apply = "--apply" in sys.argv
    e = read_env(ENV_PATH)

    token = e.get("VERCEL_TOKEN", "").strip()
    if not token:
        sys.exit("VERCEL_TOKEN is empty in .env.\n"
                 "vercel.com -> Settings -> Tokens -> Create, then put it in .env.")

    local = read_env(LOCAL_ENV)
    missing = [k for k in WANTED if not local.get(k, "").strip()]
    if missing:
        sys.exit("dashboard/.env.local is missing: %s" % ", ".join(missing))

    # The anon and service keys are both JWTs and differ only in a claim, so a
    # paste error is invisible to the eye. Read the role out and refuse rather
    # than shipping a key that bypasses every RLS policy to a browser bundle.
    anon = local["NEXT_PUBLIC_SUPABASE_ANON_KEY"]
    if "service_role" in anon or "sb_secret" in anon:
        sys.exit("NEXT_PUBLIC_SUPABASE_ANON_KEY in dashboard/.env.local looks like a\n"
                 "SERVICE ROLE key. That bypasses RLS and would be public in the\n"
                 "browser bundle. Refusing. Use the anon/publishable key.")

    code, me = call(token, "GET", "/v2/user")
    if code != 200:
        sys.exit("token rejected — HTTP %s: %s" % (code, err(me)))
    user = me.get("user", me)
    account = user.get("username") or user.get("email")

    # A token scoped to a team creates projects under that team, and every
    # later call needs the same teamId or it 404s on a project that exists.
    code, teams = call(token, "GET", "/v2/teams")
    team_list = teams.get("teams", []) if code == 200 else []
    team = None
    if len(team_list) == 1:
        team = team_list[0]["id"]

    print("account        %s" % account)
    print("scope          %s" % (team_list[0]["slug"] if team else "personal"))
    print("project        %s" % PROJECT)
    print("root directory %s   <- the app is not at the repo root" % ROOT_DIR)
    print("git            %s @ %s" % (REPO, BRANCH))
    print("env vars       %s" % ", ".join(WANTED))
    print("               anon key, %d chars, role check passed" % len(anon))

    code, existing = call(token, "GET", "/v9/projects/%s" % PROJECT, team=team)
    found = code == 200
    print("\nproject exists %s" % ("yes, reuse it" if found else "no, create it"))

    if not apply:
        print("\nDry run. Re-run with --apply.")
        return

    if not found:
        code, out = call(token, "POST", "/v11/projects", {
            "name": PROJECT,
            "framework": "nextjs",
            "rootDirectory": ROOT_DIR,
            "gitRepository": {"type": "github", "repo": REPO},
            "environmentVariables": [
                {"key": k, "value": local[k], "type": "encrypted", "target": TARGETS}
                for k in WANTED
            ],
        }, team=team)
        if code not in (200, 201):
            # The usual cause is the Vercel GitHub App not having access to a
            # private repo. Say so, rather than printing the raw error.
            print("\ncreate failed  HTTP %s: %s" % (code, err(out)))
            if "github" in err(out).lower() or code == 403:
                print("\nThe Vercel GitHub App probably cannot see a private repo.")
                print("vercel.com/account/integrations -> GitHub -> Configure,")
                print("grant access to TheSuperShyy/homies, then re-run.")
            sys.exit(1)
        existing = out
        print("created        %s" % out.get("id"))
    else:
        # An existing project may predate the settings above. Force both.
        code, out = call(token, "PATCH", "/v9/projects/%s" % PROJECT,
                         {"framework": "nextjs", "rootDirectory": ROOT_DIR}, team=team)
        print("settings       HTTP %s (framework, rootDirectory)" % code)
        for k in WANTED:
            code, out = call(token, "POST",
                             "/v10/projects/%s/env?upsert=true" % PROJECT,
                             {"key": k, "value": local[k], "type": "encrypted",
                              "target": TARGETS}, team=team)
            print("env %-30s HTTP %s" % (k, code))

    code, dep = call(token, "POST", "/v13/deployments", {
        "name": PROJECT,
        "project": PROJECT,
        "target": "production",
        "gitSource": {"type": "github", "repoId": REPO_ID, "ref": BRANCH},
    }, team=team)
    if code not in (200, 201):
        sys.exit("\ndeploy failed  HTTP %s: %s" % (code, err(dep)))

    dep_id = dep.get("id")
    print("\ndeployment     %s" % dep_id)
    print("building       ", end="", flush=True)

    state = ""
    for _ in range(150):  # 150 * 4s = 10 minutes
        time.sleep(4)
        code, d = call(token, "GET", "/v13/deployments/%s" % dep_id, team=team)
        if code != 200:
            continue
        new = d.get("readyState") or d.get("status") or ""
        if new != state:
            print("%s " % new.lower(), end="", flush=True)
            state = new
        if new in ("READY", "ERROR", "CANCELED"):
            break

    print()
    if state != "READY":
        print("\nBuild did not succeed (%s)." % state.lower())
        print("Logs: https://vercel.com/%s/%s/%s" %
              (team_list[0]["slug"] if team else account, PROJECT, dep_id))
        sys.exit(1)

    code, proj = call(token, "GET", "/v9/projects/%s" % PROJECT, team=team)
    alias = ""
    for t in (proj.get("targets") or {}).values():
        alias = (t.get("alias") or [""])[0] or alias
    url = "https://" + (alias or d.get("url", ""))

    print("\nlive           %s" % url)
    print("\nOne thing left, and login fails without it:")
    print("  Supabase -> Authentication -> URL Configuration")
    print("  Site URL:      %s" % url)
    print("  Redirect URLs: %s/**" % url)
    print("\nAnd there is no staff user yet — signup is closed by design.")
    print("  Supabase -> Authentication -> Users -> Add user")


if __name__ == "__main__":
    main()
