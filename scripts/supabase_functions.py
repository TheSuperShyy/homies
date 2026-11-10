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

  The voice team note (14 Sep) needs two more: N8N_VOICE_NOTE_SECRET (minted
  by scripts/n8n_voice_note.py into .env) and N8N_VOICE_NOTE_URL (derived from
  N8N_BASE_URL unless set). Both are pushed whenever the secret exists; with
  either missing the function logs "voice note OFF" once per call and writes
  its rows as before. A rotated secret is one --apply away from the function.

  The payment link (17 Sep) needs a fourth: OXS_KEY_DEBTS, the finance
  READ-ONLY key the importers already use. Pushed whenever .env has it, on a
  plain --apply, because a read key cannot write anything into OXS -- the
  opposite of OXS_KEY_REQUESTS below, which is deleted unless --oxs-mirror
  is passed. Without it get_payment_link answers 'unavailable' and the bot
  takes the ticket route, which is what it did before the endpoint existed.

  The debt call's WhatsApp delivery (20 Sep) needs three more, all already in
  .env for other jobs: CHATWOOT_API_TOKEN (admin: finds or creates the
  contact and the conversation), CHATWOOT_BOT_TOKEN (posts the message as
  the bot, so the chat workflow neither answers it nor reads it as a human
  takeover) and OPENROUTER_API_KEY (the one model-written line above the
  link; without it the message is the link alone). Pushed on every plain
  --apply; without the two Chatwoot tokens send_payment_link answers
  'unavailable' and the agent gives the office number.

  Feature 21 (3 Nov): WHATSAPP_VIA=uchat in .env moves the debt call's link and
  the "done" notice to the UChat number, with UCHAT_API_KEY taken from .env's
  Uchat_api_key; MEDIA_HOSTS_EXTRA adds hosts a photo may come from. Each is
  pushed when .env has it. WHATSAPP_VIA=chatwoot and an --apply moves back.

  THE OXS MIRROR IS ON FOR ONE NUMBER SINCE 24 SEP: deploy with --apply
  --oxs-mirror, or the plain --apply below deletes its key and switches it off.

    python scripts/supabase_functions.py            # show what would happen
    python scripts/supabase_functions.py --apply    # do it
"""
import json
import mimetypes
import os
import secrets
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, ".env")
SLUG = "debt-tools"
SRC = os.path.join(ROOT, "supabase", "functions", SLUG, "index.ts")
# Feature 17 (22 Oct): the pure rules live beside index.ts, which imports them.
IDENTITY = os.path.join(ROOT, "supabase", "functions", SLUG, "identity.ts")
# Feature 18 (25 Oct): which agent answers a call on the 208 line, also pure.
ROUTE = os.path.join(ROOT, "supabase", "functions", SLUG, "route.ts")
# 29 Oct: the balance's name check that takes Latin letters, also pure.
NAMES = os.path.join(ROOT, "supabase", "functions", SLUG, "names.ts")
# 10 Nov: how long the caller waits for the debt call's payment link, also pure.
PAYLINK = os.path.join(ROOT, "supabase", "functions", SLUG, "paylink.ts")
API = "https://api.supabase.com"

# api.supabase.com sits behind Cloudflare, which rejects urllib's default
# User-Agent with a 403 and the body "error code: 1010" — no mention of auth,
# so it reads as a bad token. Any ordinary UA gets through.
UA = "curl/8.5.0"


def env():
    """`.env` when there is one. GitHub Actions has none: its deploy job hands
    over SUPABASE_ACCESS_TOKEN and SUPABASE_URL as environment variables, and
    `--code-only` needs nothing else (feature 22)."""
    d = {k: os.environ[k] for k in ("SUPABASE_ACCESS_TOKEN", "SUPABASE_URL")
         if os.environ.get(k)}
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH, encoding="utf-8"):
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                d[k.strip()] = v.strip()
    return d


def differs_from_main():
    """The function files that are not as `origin/main` holds them, after a fetch.

    Feature 22 (5 Nov): live code reaches the function from `main`, through a
    pull request and the pipeline. Before it, the function went live by hand
    from whatever was checked out -- v142 from `feature/chatbot`, 557 commits
    ahead of `main`. A hand deploy still uploads code with the secrets, so it
    is allowed only when that code is exactly `main`'s. Line endings are
    normalised: Windows checkouts may carry CRLF where git stores LF.
    """
    subprocess.run(["git", "-C", ROOT, "fetch", "-q", "origin", "main"], check=True)
    stale = []
    for path in (SRC, IDENTITY, ROUTE, NAMES, PAYLINK):
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        r = subprocess.run(["git", "-C", ROOT, "show", "origin/main:" + rel],
                           capture_output=True)
        here = open(path, "rb").read().replace(b"\r\n", b"\n")
        if r.returncode != 0 or r.stdout.replace(b"\r\n", b"\n") != here:
            stale.append(rel)
    return stale


def deploy_code(token, ref, url, files):
    """Upload the function's files; exit non-zero unless it comes back ACTIVE."""
    meta = {"name": SLUG, "entrypoint_path": "index.ts", "verify_jwt": False}
    body, ctype = multipart(
        [("metadata", None, json.dumps(meta).encode(), "application/json")]
        + [("file", name, text.encode("utf-8"), "application/typescript")
           for name, text in files])
    code, out = call(token, "POST",
                     "/v1/projects/%s/functions/deploy?slug=%s" % (ref, SLUG),
                     body, ctype)
    print("deploy         HTTP %s" % code)
    if code >= 300:
        print(out)
        sys.exit(1)
    status = out.get("status") if isinstance(out, dict) else None
    if isinstance(out, dict):
        print("               version %s, status %s, verify_jwt %s"
              % (out.get("version"), status, out.get("verify_jwt")))
    print("\nendpoint       %s/functions/v1/%s" % (url, SLUG))
    if status != "ACTIVE":
        sys.exit("deployed, but the function reads %s, not ACTIVE" % status)


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
    code_only = "--code-only" in sys.argv
    e = env()

    token = e.get("SUPABASE_ACCESS_TOKEN", "").strip()
    url = e.get("SUPABASE_URL", "").strip()
    if not token:
        sys.exit("SUPABASE_ACCESS_TOKEN is empty in .env.")
    if not url:
        sys.exit("SUPABASE_URL is empty in .env.")
    ref = url.split("//")[1].split(".")[0]

    # Only `main`'s function goes live (feature 22). The pipeline checks out
    # `main` itself, so the guard is for hand runs.
    if apply and not os.environ.get("GITHUB_ACTIONS"):
        stale = differs_from_main()
        if stale:
            sys.exit("REFUSED: the function here is not what main holds (%s).\n"
                     "Live code goes through a pull request to main, and the pipeline "
                     "deploys it. A hand deploy is for secrets, from a checkout of main."
                     % ", ".join(stale))

    src = open(SRC, encoding="utf-8").read()
    identity_src = open(IDENTITY, encoding="utf-8").read()
    route_src = open(ROUTE, encoding="utf-8").read()
    names_src = open(NAMES, encoding="utf-8").read()
    paylink_src = open(PAYLINK, encoding="utf-8").read()
    files = [("index.ts", src), ("identity.ts", identity_src),
             ("route.ts", route_src), ("names.ts", names_src), ("paylink.ts", paylink_src)]
    print("files          index.ts %d chars, identity.ts %d chars, route.ts %d chars, names.ts %d chars, "
          "paylink.ts %d chars"
          % (len(src), len(identity_src), len(route_src), len(names_src), len(paylink_src)))

    print("project        %s" % ref)
    print("function       %s  (%d lines, verify_jwt=false)" % (SLUG, src.count("\n")))

    # The pipeline's deploy: the code and nothing else. No secret is pushed
    # or deleted, so the OXS mirror's switches stay exactly as the last hand
    # run (--oxs-mirror) left them.
    if code_only:
        print("mode           code only: no secret is pushed or deleted")
        if not apply:
            print("\nDry run. Re-run with --apply.")
            return
        deploy_code(token, ref, url, files)
        return

    tool_secret = e.get("TOOL_SECRET", "").strip()
    generated = False
    if not tool_secret:
        tool_secret = secrets.token_urlsafe(32)
        generated = True
    print("TOOL_SECRET    %s" % ("generate a new one (%d chars)" % len(tool_secret)
                                 if generated else "already in .env, reuse"))
    voice_secret = e.get("N8N_VOICE_NOTE_SECRET", "").strip()
    voice_url = (e.get("N8N_VOICE_NOTE_URL", "").strip()
                 or (e.get("N8N_BASE_URL", "").strip().rstrip("/") + "/webhook/homies-voice-note"
                     if e.get("N8N_BASE_URL", "").strip() else ""))
    if voice_secret and voice_url:
        print("voice note     ON -> %s" % voice_url)
    elif not voice_secret:
        print("voice note     OFF — N8N_VOICE_NOTE_SECRET empty (run scripts/n8n_voice_note.py --apply)")
    else:
        print("voice note     OFF — no URL: set N8N_BASE_URL or N8N_VOICE_NOTE_URL")
    # 5 Nov, Yariv's change 3: a WhatsApp standing-order request is emailed to
    # collections by n8n (scripts/n8n_standing_order_email.py mints the secret).
    # Missing either, the request is still recorded and nothing is emailed.
    standing_secret = e.get("N8N_STANDING_ORDER_SECRET", "").strip()
    standing_url = (e.get("N8N_BASE_URL", "").strip().rstrip("/") + "/webhook/homies-standing-order"
                    if e.get("N8N_BASE_URL", "").strip() else "")
    print("standing order %s" % ("email ON -> %s" % standing_url if standing_secret and standing_url
                                  else "email OFF — run scripts/n8n_standing_order_email.py --apply"))
    finance_key = e.get("OXS_KEY_DEBTS", "").strip()
    print("payment link   %s" % ("ON  (OXS_KEY_DEBTS, finance read-only)" if finance_key
                                  else "OFF — OXS_KEY_DEBTS empty in .env"))
    cw_admin = e.get("CHATWOOT_API_TOKEN", "").strip()
    cw_bot = e.get("CHATWOOT_BOT_TOKEN", "").strip()
    or_key = e.get("OPENROUTER_API_KEY", "").strip()
    if cw_admin and cw_bot:
        print("whatsapp link  ON  (CHATWOOT_API_TOKEN + CHATWOOT_BOT_TOKEN%s)"
              % ("" if or_key else "; OPENROUTER_API_KEY empty -> the link alone"))
    else:
        print("whatsapp link  OFF — CHATWOOT_API_TOKEN / CHATWOOT_BOT_TOKEN empty in .env")
    # Feature 21 (3 Nov): WHATSAPP_VIA=uchat sends the debt call's link and the
    # "done" notice through UChat (UCHAT_API_KEY is the bot's key, Uchat_api_key
    # in .env); unset or "chatwoot" keeps Chatwoot. MEDIA_HOSTS_EXTRA adds photo
    # hosts. Each is pushed when .env has it; going back is a setting.
    wa_via = e.get("WHATSAPP_VIA", "").strip().lower()
    uchat_key = e.get("Uchat_api_key", "").strip()
    media_extra = e.get("MEDIA_HOSTS_EXTRA", "").strip()
    print("whatsapp via   %s" % ("UCHAT (UCHAT_API_KEY %s)" % ("set" if uchat_key else "MISSING")
                                  if wa_via == "uchat" else "chatwoot (WHATSAPP_VIA %s)" % (wa_via or "unset")))
    # Feature 17 (22 Oct): which channels refuse a ticket without a name.
    # Unset here leaves the project's value as it is; "off" switches it off.
    name_channels = e.get("NAME_REQUIRED_CHANNELS", "").strip()
    print("name required  %s" % (name_channels or "unchanged (not in .env)"))
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
    if voice_secret and voice_url:
        to_push.append({"name": "N8N_VOICE_NOTE_SECRET", "value": voice_secret})
        to_push.append({"name": "N8N_VOICE_NOTE_URL", "value": voice_url})
    if standing_secret and standing_url:
        to_push.append({"name": "N8N_STANDING_ORDER_SECRET", "value": standing_secret})
        to_push.append({"name": "N8N_STANDING_ORDER_URL", "value": standing_url})
    # The finance key is read-only on OXS's side (finance keys can never be
    # 'full', per the API doc), so it rides on every plain --apply and is
    # never on the delete list below.
    if finance_key:
        to_push.append({"name": "OXS_KEY_DEBTS", "value": finance_key})
    # The WhatsApp delivery (20 Sep). Both Chatwoot tokens or neither: half a
    # pair finds a contact it cannot write to.
    if cw_admin and cw_bot:
        to_push.append({"name": "CHATWOOT_API_TOKEN", "value": cw_admin})
        to_push.append({"name": "CHATWOOT_BOT_TOKEN", "value": cw_bot})
    if or_key:
        to_push.append({"name": "OPENROUTER_API_KEY", "value": or_key})
    if name_channels:
        to_push.append({"name": "NAME_REQUIRED_CHANNELS", "value": name_channels})
    if wa_via:
        to_push.append({"name": "WHATSAPP_VIA", "value": wa_via})
    if uchat_key:
        to_push.append({"name": "UCHAT_API_KEY", "value": uchat_key})
    if media_extra:
        to_push.append({"name": "MEDIA_HOSTS_EXTRA", "value": media_extra})
    oxs_key = e.get("OXS_KEY_REQUESTS", "").strip()
    # 24 Sep: the mirror came back on for ONE number, the owner's +63 tester.
    # `OXS_MIRROR_PHONES` is the second gate inside oxsMirror() and travels with
    # the key — pushed only by --oxs-mirror, deleted by a plain --apply — so the
    # off state cannot be half off, with a live allow-list waiting for a key to
    # reappear. Empty list mirrors nobody, which is what the function does when
    # the var is absent.
    oxs_phones = e.get("OXS_MIRROR_PHONES", "").strip()
    mirror = "--oxs-mirror" in sys.argv
    if mirror and oxs_key:
        to_push.append({"name": "OXS_KEY_REQUESTS", "value": oxs_key})
        to_push.append({"name": "OXS_MIRROR_PHONES", "value": oxs_phones})
    code, out = call(token, "POST", "/v1/projects/%s/secrets" % ref, to_push)
    print("secret push    HTTP %s  (%d secrets)" % (code, len(to_push)))
    if not mirror:
        code, out = call(token, "DELETE", "/v1/projects/%s/secrets" % ref,
                         ["OXS_KEY_REQUESTS", "OXS_MIRROR_PHONES"])
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
    # 5 Nov: `OXS_MIRROR_TYPES` is the third gate, the ticket types that go into
    # OXS for ANY reporter (Yariv: every elevator report). It travels with the
    # key like the phone list, but only when .env names types: otherwise it is
    # deleted, so the switch is off unless the owner has turned it on. Its own
    # DELETE, because a batch naming a secret that is absent may answer 404 and
    # leave the others standing, which would keep the mirror half on.
    oxs_types = e.get("OXS_MIRROR_TYPES", "").strip()
    if mirror and oxs_key and oxs_types:
        code, out = call(token, "POST", "/v1/projects/%s/secrets" % ref,
                         [{"name": "OXS_MIRROR_TYPES", "value": oxs_types}])
        print("oxs types      ON for any reporter: %s (HTTP %s)" % (oxs_types, code))
    else:
        code, out = call(token, "DELETE", "/v1/projects/%s/secrets" % ref, ["OXS_MIRROR_TYPES"])
        print("oxs types      OFF (HTTP %s)" % code)
        if code == 404:
            code = 200
    if code >= 300:
        print(out)
        sys.exit(1)

    deploy_code(token, ref, url, files)


if __name__ == "__main__":
    main()
