#!/usr/bin/env python
"""Deploy the debt-tools Edge Function and set the secret it reads.

Uses the Supabase Management API rather than the CLI, so nothing has to be
installed and `supabase init` does not get to restructure the repo. Reads
SUPABASE_ACCESS_TOKEN and SUPABASE_URL from .env.

Two things this gets right that are easy to get wrong:

  verify_jwt is false. Vapi and n8n are not Supabase users and cannot present a
  Supabase JWT. Leaving it on returns 401 to every caller and looks like a bad
  secret. The X-Homies-Secret header stands in front of the function instead.

  TOOL_SECRET is generated here if it is missing, written to .env, and pushed to
  the project as a function secret. The function fails closed on an empty secret
  (`|| !SECRET`), so deploying without it produces a function that 401s
  everything — which reads as a broken deploy rather than a missing value.

    python scripts/supabase_functions.py            # show what would happen
    python scripts/supabase_functions.py --apply    # do it
"""
import json
import mimetypes
import os
import secrets
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, ".env")
SLUG = "debt-tools"
SRC = os.path.join(ROOT, "supabase", "functions", SLUG, "index.ts")
API = "https://api.supabase.com"

# api.supabase.com sits behind Cloudflare, which rejects urllib's default
# User-Agent with a 403 and the body "error code: 1010" — no mention of auth,
# so it reads as a bad token. Any ordinary UA gets through.
UA = "curl/8.5.0"


def env():
    d = {}
    for line in open(ENV_PATH, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def set_env(key, value):
    """Write key=value into .env, replacing the existing line in place."""
    lines = open(ENV_PATH, encoding="utf-8").read().split("\n")
    for i, line in enumerate(lines):
        if line.split("=", 1)[0].strip() == key and not line.lstrip().startswith("#"):
            lines[i] = "%s=%s" % (key, value)
            break
    else:
        lines.append("%s=%s" % (key, value))
    open(ENV_PATH, "w", encoding="utf-8").write("\n".join(lines))


def call(token, method, path, body=None, ctype="application/json"):
    data = None
    if body is not None:
        data = json.dumps(body).encode() if ctype == "application/json" else body
    req = urllib.request.Request(
        API + path, data=data, method=method,
        headers={"Authorization": "Bearer " + token, "User-Agent": UA,
                 "Accept": "application/json", "content-type": ctype})
    try:
        r = urllib.request.urlopen(req, timeout=180)
        raw = r.read().decode("utf-8", "replace")
        return r.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:600]


def multipart(parts):
    """parts: list of (name, filename_or_None, content_bytes, content_type)."""
    b = "----homies%s" % secrets.token_hex(12)
    out = b""
    for name, filename, content, ctype in parts:
        out += ("--%s\r\n" % b).encode()
        disp = 'form-data; name="%s"' % name
        if filename:
            disp += '; filename="%s"' % filename
        out += ('Content-Disposition: %s\r\n' % disp).encode()
        out += ("Content-Type: %s\r\n\r\n" % ctype).encode()
        out += content + b"\r\n"
    out += ("--%s--\r\n" % b).encode()
    return out, "multipart/form-data; boundary=%s" % b


def main():
    apply = "--apply" in sys.argv
    e = env()

    token = e.get("SUPABASE_ACCESS_TOKEN", "").strip()
    url = e.get("SUPABASE_URL", "").strip()
    if not token:
        sys.exit("SUPABASE_ACCESS_TOKEN is empty in .env.")
    if not url:
        sys.exit("SUPABASE_URL is empty in .env.")
    ref = url.split("//")[1].split(".")[0]

    tool_secret = e.get("TOOL_SECRET", "").strip()
    generated = False
    if not tool_secret:
        tool_secret = secrets.token_urlsafe(32)
        generated = True

    src = open(SRC, encoding="utf-8").read()

    print("project        %s" % ref)
    print("function       %s  (%d lines, verify_jwt=false)" % (SLUG, src.count("\n")))
    print("TOOL_SECRET    %s" % ("generate a new one (%d chars)" % len(tool_secret)
                                 if generated else "already in .env, reuse"))
    if not apply:
        print("\nDry run. Re-run with --apply.")
        return

    if generated:
        set_env("TOOL_SECRET", tool_secret)
        print("\nwrote TOOL_SECRET to .env")

    # THE OXS MIRROR IS OFF BY DEFAULT, AND ONLY A FLAG TURNS IT ON.
    #
    # open_request can mirror tickets into OXS (oxsMirror in index.ts), gated
    # on OXS_KEY_REQUESTS being present in the FUNCTION's environment. On
    # 26 Aug the owner had that mirror switched off after it went live on a
    # consent that was not really given — "OXS is read-only" is the standing
    # rule, and reversing it is an explicit decision, not a deploy side effect.
    #
    # So a plain --apply DELETES the function-side key (a stale one must not
    # linger and quietly keep writing), and only `--oxs-mirror` pushes it. The
    # .env copy is untouched either way — the read-side importers use it.
    to_push = [{"name": "TOOL_SECRET", "value": tool_secret}]
    oxs_key = e.get("OXS_KEY_REQUESTS", "").strip()
    mirror = "--oxs-mirror" in sys.argv
    if mirror and oxs_key:
        to_push.append({"name": "OXS_KEY_REQUESTS", "value": oxs_key})
    code, out = call(token, "POST", "/v1/projects/%s/secrets" % ref, to_push)
    print("secret push    HTTP %s  (%d secrets)" % (code, len(to_push)))
    if not mirror:
        code, out = call(token, "DELETE", "/v1/projects/%s/secrets" % ref,
                         ["OXS_KEY_REQUESTS"])
        # 404 means the key is already gone, which IS the off state this
        # branch exists to enforce — found 27 Aug when the second plain
        # --apply after the shutdown aborted here and never deployed.
        if code == 404:
            print("oxs mirror     OFF — key already absent (HTTP 404)")
            code = 200
        else:
            print("oxs mirror     OFF — function-side key deleted (HTTP %s)" % code)
    else:
        print("oxs mirror     ON — pushed by explicit --oxs-mirror")
    if code >= 300:
        print(out)
        sys.exit(1)

    meta = {"name": SLUG, "entrypoint_path": "index.ts", "verify_jwt": False}
    body, ctype = multipart([
        ("metadata", None, json.dumps(meta).encode(), "application/json"),
        ("file", "index.ts", src.encode("utf-8"), "application/typescript"),
    ])
    code, out = call(token, "POST",
                     "/v1/projects/%s/functions/deploy?slug=%s" % (ref, SLUG),
                     body, ctype)
    print("deploy         HTTP %s" % code)
    if code >= 300:
        print(out)
        sys.exit(1)
    if isinstance(out, dict):
        print("               version %s, status %s, verify_jwt %s"
              % (out.get("version"), out.get("status"), out.get("verify_jwt")))
    print("\nendpoint       %s/functions/v1/%s" % (url, SLUG))


if __name__ == "__main__":
    main()
