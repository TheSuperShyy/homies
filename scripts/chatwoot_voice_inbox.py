# -*- coding: utf-8 -*-
"""The Chatwoot inbox a voice call's team note lands in, and the probe that
settled how the note gets written there.

    python scripts/chatwoot_voice_inbox.py                 # dry run: what exists, what would be created
    python scripts/chatwoot_voice_inbox.py --apply         # create "Homies — Voice", record its id in .env
    python scripts/chatwoot_voice_inbox.py --probe         # can the agent bot write on that inbox? (throwaway, cleans up)
    python scripts/chatwoot_voice_inbox.py --clean-probe   # remove leftovers from an interrupted probe

WHY AN INBOX
A voice call has no Chatwoot conversation, and feature 16's alert is a private
note that @mentions a team ON a conversation. The owner's mechanism for "I've
let the team know" is "a mention in Chatwoot, like regular" (14 Sep), so a call
needs a place for the mention to land. An `api` channel inbox is that place:
Chatwoot lets us create contacts, conversations and INCOMING messages in it by
API, and nothing is ever sent back out of it (webhook_url empty). A rep who
picks up a voice note phones the resident and resolves the thread; nothing
typed there reaches the caller, and the note says so.

`enable_auto_assignment` is OFF at creation. On, Chatwoot would hand every new
voice conversation to an online inbox member the moment it exists -- a named
person at lunch is a black hole (the 6 Sep team decision, same reasoning).

THE PROBE (Design A or B)
The sub-workflow writes the note with the agent bot's token, and it has to be
the bot: Chatwoot skips a User's mention of a team that contains that same
User, so an admin-token note would notify nobody today (the owner is the only
member). The bot is attached to inbox 1 (WhatsApp). Whether an account-scoped
bot may write on a conversation in an inbox it is NOT attached to is what
`--probe` measures, because attaching "Homies bot" to this inbox is not an
option: its outgoing URL is the WhatsApp n8n workflow, and a bot inbox also
flips new conversations to `pending`, which the handover guard and the ticker
both refuse.

  A  every bot write answers 2xx and the mention raises a notification
     -> nothing else changes; the sub-workflow keeps its bot credential.
  B  a bot write is refused
     -> a second agent bot with an inert outgoing URL, attached here; see the
        plan in docs/features/16-human-handover/context.md.

The probe creates one throwaway contact (identifier `voice:probe:<hex>`), one
conversation, one incoming message, then tries the five bot writes the
sub-workflow makes, then one real mention of the Service team, then deletes
the contact (cascades the conversation). The owner is in Service, so the
mention pings one PC once.

Admin token: CHATWOOT_API_TOKEN. Bot token: CHATWOOT_BOT_TOKEN. Both in .env.
"""
import json
import secrets
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

CW = "https://chat.srv1879140.hstgr.cloud"
ACCOUNT = 2
INBOX_NAME = "Homies — Voice"
SERVICE_TEAM = 4

# The sidebar shows a custom attribute only when a definition exists for it.
# `handover_reasons` (14 Sep) was written without one; `handover_channel` is
# new today. Both are text.
ATTRIBUTES = [("handover_channel", "Channel"), ("handover_reasons", "Handover reasons")]


def cw(method, path, body=None, token=None):
    e = W.env()
    tok = (token or e["CHATWOOT_API_TOKEN"]).strip()
    req = urllib.request.Request(
        CW + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"api_access_token": tok, "Content-Type": "application/json",
                 "Accept": "application/json"})
    try:
        raw = urllib.request.urlopen(req, timeout=30).read()
        return json.loads(raw or b"null")
    except urllib.error.HTTPError as ex:
        return {"_http": ex.code, "_body": ex.read().decode(errors="replace")[:300]}


def ok(r):
    return not (isinstance(r, dict) and r.get("_http"))


def find_inbox():
    r = cw("GET", "/api/v1/accounts/%d/inboxes" % ACCOUNT)
    for x in (r.get("payload") or []) if isinstance(r, dict) else []:
        if x.get("name") == INBOX_NAME:
            return x
    return None


def apply():
    e = W.env()
    inbox = find_inbox()
    if inbox:
        print("inbox          %s exists: id %s (%s, auto-assign %s)"
              % (INBOX_NAME, inbox["id"], inbox.get("channel_type"), inbox.get("enable_auto_assignment")))
        if inbox.get("enable_auto_assignment"):
            r = cw("PATCH", "/api/v1/accounts/%d/inboxes/%d" % (ACCOUNT, inbox["id"]),
                   {"enable_auto_assignment": False})
            print("auto-assign    turned OFF" if ok(r) else "auto-assign    PATCH failed: %s" % r)
    else:
        r = cw("POST", "/api/v1/accounts/%d/inboxes" % ACCOUNT,
               {"name": INBOX_NAME, "enable_auto_assignment": False,
                "channel": {"type": "api", "webhook_url": ""}})
        if not ok(r):
            sys.exit("inbox create failed: %s" % r)
        inbox = r
        print("inbox          created %s: id %s" % (INBOX_NAME, inbox["id"]))
    iid = int(inbox["id"])
    if e.get("CHATWOOT_VOICE_INBOX_ID", "").strip() != str(iid):
        W.set_env("CHATWOOT_VOICE_INBOX_ID", str(iid))
        print(".env           CHATWOOT_VOICE_INBOX_ID=%d written" % iid)

    # The admin login is an administrator and therefore mentionable on every
    # inbox; membership is still recorded so the Voice inbox shows in its
    # sidebar, and so the seats step in pc-setup.md has a precedent to copy.
    me = cw("GET", "/api/v1/profile")
    members = cw("GET", "/api/v1/accounts/%d/inbox_members/%d" % (ACCOUNT, iid))
    ids = [m["id"] for m in (members.get("payload") or [])] if isinstance(members, dict) else []
    if me.get("id") and me["id"] not in ids:
        r = cw("POST", "/api/v1/accounts/%d/inbox_members" % ACCOUNT,
               {"inbox_id": iid, "user_ids": ids + [me["id"]]})
        print("members        added %s (user %s)" % (me.get("name"), me["id"]) if ok(r)
              else "members        add failed: %s" % r)
    else:
        print("members        %s" % ", ".join(str(i) for i in ids))

    defs = cw("GET", "/api/v1/accounts/%d/custom_attribute_definitions?attribute_model=conversation_attribute" % ACCOUNT)
    have = {d["attribute_key"] for d in defs} if isinstance(defs, list) else set()
    for key, label in ATTRIBUTES:
        if key in have:
            print("attribute      %s exists" % key)
            continue
        r = cw("POST", "/api/v1/accounts/%d/custom_attribute_definitions" % ACCOUNT,
               {"attribute_display_name": label, "attribute_key": key,
                "attribute_model": "conversation_attribute", "attribute_display_type": "text",
                "attribute_description": "Written by the handover sub-workflow."})
        print("attribute      %s created" % key if ok(r) else "attribute      %s failed: %s" % (key, r))

    hooks = cw("GET", "/api/v1/accounts/%d/webhooks" % ACCOUNT)
    print("webhooks       %s" % json.dumps((hooks.get("payload") or {}).get("webhooks", hooks)
                                           if isinstance(hooks, dict) else hooks)[:200])


def dry():
    inbox = find_inbox()
    e = W.env()
    print("inbox          %s" % ("exists, id %s" % inbox["id"] if inbox else "would CREATE (api channel, auto-assign off)"))
    print(".env           CHATWOOT_VOICE_INBOX_ID=%s" % (e.get("CHATWOOT_VOICE_INBOX_ID") or "(unset)"))
    defs = cw("GET", "/api/v1/accounts/%d/custom_attribute_definitions?attribute_model=conversation_attribute" % ACCOUNT)
    have = {d["attribute_key"] for d in defs} if isinstance(defs, list) else set()
    for key, _ in ATTRIBUTES:
        print("attribute      %s %s" % (key, "exists" if key in have else "would CREATE"))
    print("\nDry run. Re-run with --apply, then --probe.")


def probe():
    e = W.env()
    iid = int(e.get("CHATWOOT_VOICE_INBOX_ID") or 0)
    if not iid:
        sys.exit("CHATWOOT_VOICE_INBOX_ID is not in .env; run --apply first.")
    bot = e.get("CHATWOOT_BOT_TOKEN", "").strip()
    if not bot:
        sys.exit("CHATWOOT_BOT_TOKEN is empty in .env.")
    tag = secrets.token_hex(4)
    base = "/api/v1/accounts/%d" % ACCOUNT
    contact_id = None
    verdict = []
    try:
        r = cw("POST", base + "/contacts",
               {"inbox_id": iid, "name": "בדיקת-מערכת probe " + tag, "identifier": "voice:probe:" + tag})
        contact_id = ((r.get("payload") or {}).get("contact") or {}).get("id") if isinstance(r, dict) else None
        if not contact_id:
            sys.exit("contact create failed: %s" % r)
        print("contact        %s" % contact_id)
        r = cw("POST", base + "/conversations",
               {"inbox_id": iid, "contact_id": contact_id, "status": "open",
                "additional_attributes": {"channel": "voice", "call_id": "probe-" + tag}})
        cid = r.get("id") if isinstance(r, dict) else None
        if not cid:
            sys.exit("conversation create failed: %s" % r)
        print("conversation   %s (status %s)" % (cid, r.get("status")))
        r = cw("POST", base + "/conversations/%d/messages" % cid,
               {"content": "probe: the caller's words", "message_type": "incoming"})
        print("incoming msg   %s" % ("ok" if ok(r) else r))
        c = cw("GET", base + "/conversations/%d" % cid)
        print("waiting_since  %s" % c.get("waiting_since"))

        conv = base + "/conversations/%d" % cid
        writes = [
            ("note",       "POST", conv + "/messages", {"content": "probe note", "message_type": "outgoing", "private": True}),
            ("attributes", "POST", conv + "/custom_attributes", {"custom_attributes": {"handover_channel": "voice"}}),
            ("priority",   "POST", conv + "/toggle_priority", {"priority": "medium"}),
            ("team",       "POST", conv + "/assignments", {"team_id": SERVICE_TEAM}),
            ("labels",     "POST", conv + "/labels", {"labels": ["handover", "handover-service"]}),
        ]
        for name, m, p, b in writes:
            r = cw(m, p, b, token=bot)
            good = ok(r)
            verdict.append(good)
            print("bot %-10s %s" % (name, "2xx" if good else "HTTP %s %s" % (r.get("_http"), r.get("_body"))))
        r = cw("GET", conv, token=bot)
        print("bot read       %s" % ("2xx" if ok(r) else "HTTP %s (the known 500 once a team is on it is harmless)" % r.get("_http")))

        if all(verdict):
            before = cw("GET", base + "/notifications")
            seen = {n["id"] for n in ((before.get("data") or {}).get("payload") or [])} if isinstance(before, dict) else set()
            r = cw("POST", conv + "/messages",
                   {"content": "[@שירות](mention://team/%d/service) probe mention %s" % (SERVICE_TEAM, tag),
                    "message_type": "outgoing", "private": True}, token=bot)
            print("bot mention    %s" % ("2xx" if ok(r) else r))
            hit = None
            for _ in range(10):
                time.sleep(2)
                after = cw("GET", base + "/notifications")
                for n in ((after.get("data") or {}).get("payload") or []) if isinstance(after, dict) else []:
                    if n["id"] not in seen and n.get("notification_type") == "conversation_mention" \
                            and (n.get("primary_actor") or {}).get("id") == cid:
                        hit = n
                        break
                if hit:
                    break
            print("notification   %s" % ("conversation_mention %s at %s" % (hit["id"], hit.get("created_at")) if hit
                                         else "NOT seen within 20 s"))
            verdict.append(bool(hit))
        print("\nVERDICT        %s" % ("A -- the bot writes on the Voice inbox and the mention notifies; keep the bot credential"
                                       if all(verdict) else
                                       "B -- a bot write was refused or the mention did not notify; build the second bot"))
    finally:
        if contact_id:
            r = cw("DELETE", base + "/contacts/%d" % contact_id)
            print("cleanup        contact %s %s" % (contact_id, "deleted" if ok(r) else r))


def clean_probe():
    base = "/api/v1/accounts/%d" % ACCOUNT
    r = cw("GET", base + "/contacts/search?q=voice:probe:")
    n = 0
    for c in (r.get("payload") or []) if isinstance(r, dict) else []:
        if str(c.get("identifier") or "").startswith("voice:probe:"):
            d = cw("DELETE", base + "/contacts/%d" % c["id"])
            print("deleted contact %s %s" % (c["id"], "" if ok(d) else d))
            n += 1
    print("%d probe contact(s) removed" % n)


if __name__ == "__main__":
    if "--probe" in sys.argv:
        probe()
    elif "--clean-probe" in sys.argv:
        clean_probe()
    elif "--apply" in sys.argv:
        apply()
    else:
        dry()
