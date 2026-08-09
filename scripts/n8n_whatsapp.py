r"""Build and push the WhatsApp bot to n8n.

    python scripts/n8n_whatsapp.py            # show what would be pushed
    python scripts/n8n_whatsapp.py --apply    # create or update the workflow
    python scripts/n8n_whatsapp.py --activate # switch it on

Same reasoning as scripts/n8n_deploy.py: the workflow is defined here rather
than clicked together in the editor, because an editor change is invisible to
everyone who did not make it and there is no diff. Re-running is safe — it
updates the workflow with the matching name instead of making a second one.

THE SHAPE, AND WHY IT IS THIS SHAPE

    Webhook -> Sort (Code) -> Respond to Meta
                          \-> Is there a message? (If) -> AI Agent -> Send
                                                              \-> (error) -> Send

Meta retries any webhook that does not answer 200 within a few seconds, and a
retry is a second copy of the same message — which, left alone, is a resident
receiving two replies to one question. So the workflow answers Meta before it
does any work at all. This is the same lesson the tool webhook learned from
Apps Script, except here the work is an entire model round-trip rather than a
one-second sheet append, so the argument is stronger rather than weaker.

Duplicates are suppressed on Meta's message id, which is stable across retries,
and never on content — a resident who sends "כן" twice means it twice.

ONE WEBHOOK, TWO METHODS

Meta verifies a callback URL with a GET carrying hub.mode / hub.verify_token /
hub.challenge and expects the challenge echoed back as **plain text**. Answer it
with JSON and the webhook silently will not save, which is the single most
common reason a Cloud API integration never starts. Hence multipleMethods on the
webhook node and respondWith: "text" on the Respond node — the POST path returns
an empty string, which Meta is equally happy with.

THE MODEL IS AN AI AGENT NODE, NOT A CODE NODE

Until 8 Aug the tool-use loop was ~150 lines of JavaScript in a Code node calling
OpenRouter over HTTP. The Agent node (@n8n/n8n-nodes-langchain.agent) replaced it
with four sub-nodes: the model, the memory, and one per tool.

What that bought, in order of how much it matters:

  1. The model key is in n8n's credential store instead of being interpolated
     into a code string, so an exported workflow carries no secret.
  2. Conversation memory is a node keyed on the phone number, rather than
     workflow static data that does not survive an n8n restore.
  3. The two tools are objects on the canvas that the agent can reach, not a URL
     buried inside a fetch call.

What it cost, and it is a real cost: the old loop sent
`reasoning: {effort: "low"}`, and the OpenRouter node has no reasoning parameter
at all — the options collection is frequency penalty, max tokens, response
format, presence penalty, temperature, timeout, max retries and top P, and
nothing else. So thinking now runs at the model's own default. That is the safe
direction (the failure this project cares about — a tool call written into
visible text instead of emitted as a tool call — happens when thinking is OFF)
but it is slower and dearer per message than the old setting.

WHAT THE MODEL IS NOT ALLOWED TO SUPPLY

The phone number. It comes off the WhatsApp envelope, never from tool arguments
and never from anything the resident typed — the same rule the voice agents
follow for the amount and the month, and for the same reason: a claim in a
message must not be able to become a fact in a row.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from n8n_layout import check, LayoutError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WF_NAME = "Homies — WhatsApp bot"
WEBHOOK_PATH = "homies-whatsapp"
SEND_CRED = "Homies WhatsApp token"
LOG_CRED = "Homies Supabase service key"

PROMPT_DOC = os.path.join(ROOT, "docs", "features", "11-whatsapp-bot", "prompt.md")

# Through OpenRouter, which is what .env.example has said the chatbot brain is
# since it was written. The voice agents are unaffected — their model is billed
# inside Vapi and does not pass through here.
#
# OpenRouter speaks the OpenAI chat-completions shape, so the tool definitions
# below are declared once in Anthropic's shape and converted on the way out. One
# canonical list, no second copy to drift.
#
# Asked for on 8 Aug, replacing anthropic/claude-opus-5. Verified against
# openrouter.ai/api/v1/models the same day: the slug exists, carries tools in
# supported_parameters, and has a 1M context. A slug that does not exist fails as
# a 404 at call time, which on a chat bot means silence, so it is checked rather
# than typed from memory.
#
# THE PRICE DIFFERENCE IS THE HEADLINE AND IT IS NOT MARGINAL
#
#                       in $/1M   out $/1M   measured cost of one real turn
#   claude-opus-5         5.00      25.00      $0.02040
#   gemini-2.5-flash      0.30       2.50      $0.00051
#
# Forty times cheaper on the same message, against the same 2,598-character
# system prompt with both tools attached. It also made the bot work today rather
# than when credits arrive: OpenRouter pre-authorises max_tokens against the
# account balance, and 4096 tokens of Opus was more than the balance could cover
# while 4096 tokens of Flash is comfortably inside it.
#
# It is also faster — 2.3s against 6.2s on the same request.
#
# Hebrew quality is the thing to watch and has NOT been signed off by a native
# speaker. Three probes on 8 Aug: a fully detailed report produced the right
# open_request call (building, unit, plumbing, high); a common-area fault
# correctly asked which BUILDING rather than which apartment, which is the gap
# the previous model failed on; and a bare "שלום" was answered with
# "היי, מה שלומך?" — chattier than a building-management line should be, and the
# first thing to put in front of a Hebrew speaker.
MODEL = "google/gemini-2.5-flash"

# NOT APPLIED ANY MORE, and kept so that is written down rather than discovered.
#
# The old Code node sent `reasoning: {effort: "low"}` on every request. The
# OpenRouter node has no reasoning parameter, so since 8 Aug thinking runs at
# whatever the model defaults to.
#
# The reasoning behind `low` was written about claude-opus-5, where thinking-off
# occasionally produced a tool call written into visible text instead of emitted
# as a structured one — the turn returns normally, the reply reads fine, and the
# tool never runs. That is a claim about that model, not about this one, and it
# has not been retested against gemini-2.5-flash. Recorded rather than deleted
# because the failure it describes is silent, and someone will be tempted to
# reach for a thinking control here eventually.
EFFORT = "low (no longer sent — the OpenRouter node has no reasoning parameter)"

# Bounds thinking AND the reply together on this model, so it is not sized for a
# WhatsApp-length answer — a reply that thought first would truncate mid-sentence.
MAX_TOKENS = 4096

# The Meta Graph API version the send call is pinned to. Meta deprecates versions
# on a schedule; pinning means the bot breaks on a date we can look up rather
# than on a morning we cannot explain.
GRAPH_VERSION = "v21.0"

# What a resident hears when the model cannot answer — an empty balance, a
# provider outage, a malformed reply. It appeared three times inside the old
# Brain's JavaScript; now it is the error branch's only content, so it is a
# constant. Masculine first person, matching the voice agents: Hebrew marks the
# speaker's gender on the verb, so this is grammar, not tone.
HANDOVER_LINE = "אני מעביר את זה לצוות, נחזור בהקדם."

# The same line for a conversation being held in English. Added 8 Aug after a
# resident tapped English from the menu, was answered in English, asked about a
# ticket, and got the Hebrew handover line back — because a "fixed line" was
# fixed in one language. The error branch below picks between the two on the
# language Sort detected, so a fallback cannot undo the language choice either.
HANDOVER_LINE_EN = "I'm passing this to the team, we'll get back to you shortly."

# The one line for a message that carries no words. It is quoted in
# docs/features/11-whatsapp-bot/prompt.md as one of the bot's two fixed lines,
# and until 8 Aug the two copies had drifted apart — the prompt documented
# "אני קורא כאן רק טקסט" while the code sent "אני יכול לקרוא רק טקסט כרגע".
# The code is the one a resident actually reads, so the code was made to match
# the document rather than the other way round.
# What a bare "speak english" gets. It is answered without the model because the
# model answered it badly: given a message whose entire content is a request to
# switch language, gemini-2.5-flash reached for the media line — "I can only read
# text here" — in reply to text. There is nothing to reason about here anyway.
# The switch is a fact Sort already established; this just confirms it and asks
# the question that gets the conversation moving.
SWITCH_LINE = {
    "he": "אין בעיה, ממשיכים בעברית. מה קרה?",
    "en": "Sure, English from here. What's up?",
}

MEDIA_LINE = {
    "he": "אני קורא כאן רק טקסט. אפשר לכתוב לי מה קרה?",
    "en": "I can only read text here. Can you write what happened?",
}

# What a tap on 'open' or 'status' gets, without a model round-trip. Before
# 9 Aug those taps went to the agent as bare row titles — "Open a service call"
# — and the model, handed four words with no verb of the resident's own,
# re-introduced itself and asked what's up, which is a menu answering a menu.
# The tap already says what they want; the only useful reply is the first
# question of that flow, and that question is the same every time — which is
# the definition of a canned line. 'human' and 'balance' still go to the
# agent, whose job on both is transfer_to_human.
#
# Same grammar rule as every other fixed line: nothing addresses the resident
# in a gendered form.
TAP_LINE = {
    "open": {
        "he": "מה התקלה, ובאיזה בניין?",
        "en": "What's the fault, and which building?",
    },
    "status": {
        "he": "מה מספר הקריאה? אפשר גם רק את הספרות האחרונות — ואם אין מספר, בניין ודירה.",
        "en": "What's the reference number? The last digits are enough — or if you don't have it, the building and apartment.",
    },
}

# The menu, sent ONLY when someone opens with a bare greeting.
#
# A list rather than reply buttons because reply buttons cap at three and the
# client asked for five options. Meta's limits, which are hard: row title 24
# characters, description 72, the button that opens the list 20, and ten rows
# across all sections.
#
# ONE OF THESE ROWS DOES NOT WORK YET. `balance` needs a resident to prove who
# they are before anything money-shaped is read out, which is PRD §13 #1 and
# still unanswered — a tap lands on the handover path and reaches a human,
# which is what happens today anyway when somebody asks in words. The row stays
# on the menu deliberately: it makes the gap visible instead of pretending the
# capability is absent. `status` worked its way off this list on 9 Aug when
# get_request_status arrived — read-only, nothing money-shaped in the answer.
#
# The Hebrew here obeys the same rule the prompt does: nothing addresses the
# resident with a gendered form. "אפשרויות" rather than "בחר", which is
# masculine imperative, and "הצוות יחזור בהקדם" rather than "יחזור אליך".
MENU = {
    "he": {
        "type": "list",
        "body": {"text": "היי, מיכאל מהומיז. מה קרה?"},
        "footer": {"text": "אפשר גם לבחור מהרשימה"},
        "action": {
            "button": "אפשרויות",
            "sections": [{"title": "אפשרויות", "rows": [
                {"id": "open", "title": "פתיחת קריאת שירות",
                 "description": "נזילה, חשמל, מעלית, לובי, שער"},
                {"id": "status", "title": "מצב קריאה קיימת",
                 "description": "מה קורה עם קריאה שכבר נפתחה"},
                {"id": "balance", "title": "יתרה ותשלומים",
                 "description": "יתרה, חוב, קבלה, אמצעי תשלום"},
                {"id": "human", "title": "לדבר עם נציג",
                 "description": "הצוות יחזור בהקדם"},
                {"id": "lang_en", "title": "English",
                 "description": "Continue in English"},
            ]}],
        },
    },
    "en": {
        "type": "list",
        "body": {"text": "Hey, Michael from Homies. What's up?"},
        "footer": {"text": "Or pick from the list"},
        "action": {
            "button": "Options",
            "sections": [{"title": "Options", "rows": [
                {"id": "open", "title": "Open a ticket",
                 "description": "Leak, power, lift, lobby, gate"},
                {"id": "status", "title": "Check an existing ticket",
                 "description": "What is happening with a ticket"},
                {"id": "balance", "title": "Balance and payments",
                 "description": "Balance, debt, receipt, payment method"},
                {"id": "human", "title": "Talk to a person",
                 "description": "The team will get back to you"},
                {"id": "lang_he", "title": "עברית",
                 "description": "להמשיך בעברית"},
            ]}],
        },
    },
}


# The menu again, after a flow completes. Asked for 9 Aug: once a ticket is
# opened, the resident should be offered the options again rather than left
# with a reference number and silence. The body changes — "עוד משהו?" is a
# follow-up, the greeting body would read like amnesia — and the rows stay
# identical. Sent by the workflow, not the model: the trigger is a reference
# number in the outgoing reply, which is exactly the marker of a completed
# flow (open or status — both end with a reference, both deserve the offer).
FOLLOWUP_BODY = {"he": "עוד משהו?", "en": "Anything else?"}
FOLLOWUP_MENU = {
    lang: dict(MENU[lang], body={"text": FOLLOWUP_BODY[lang]}) for lang in MENU
}


def env():
    return dict(
        l.strip().split("=", 1)
        for l in open(os.path.join(ROOT, ".env"), encoding="utf-8")
        if l.strip() and not l.startswith("#") and "=" in l
    )


# Collected rather than raised one at a time, so a first run prints the whole
# setup list instead of making someone discover it four runs in a row.
MISSING = []
PENDING = []


def need(e, key, why):
    v = e.get(key, "").strip()
    if not v:
        MISSING.append((key, why))
        return "<%s>" % key
    return v


def later(e, key, why):
    """Needed to SEND, and not needed to deploy. The distinction is the order.

    Meta will not save a callback URL until it has already GET-verified it, and
    that handshake needs only WHATSAPP_WEBHOOK_VERIFY_TOKEN. The phone number id
    and the access token are used on the reply, which cannot happen before the
    handshake. Requiring all three up front blocks the one step that has to come
    first, and there is no way out of that ordering — it is Meta's.

    So the workflow deploys with a placeholder here and the send fails loudly
    until the value arrives. Safe only because nothing can reach the webhook yet:
    a number that has not been connected in the Meta app receives nothing.
    """
    v = e.get(key, "").strip()
    if not v:
        PENDING.append((key, why))
        return "<%s>" % key
    return v


def set_env(key, value):
    """Write one key back into .env, in place, keeping the rest untouched."""
    path = os.path.join(ROOT, ".env")
    lines = open(path, encoding="utf-8").read().splitlines()
    for i, l in enumerate(lines):
        if l.split("=", 1)[0].strip() == key:
            lines[i] = "%s=%s" % (key, value)
            break
    else:
        lines.append("%s=%s" % (key, value))
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def ensure_send_cred(e):
    """Put the access token in n8n's credential store, not in the workflow.

    The Send node used to carry `Authorization: Bearer <token>` as a plain
    header parameter, which writes the token into the workflow JSON — visible
    to anyone with n8n access and carried into every export and backup. It is
    the same mistake the Crypto node stopped us making with APP_SECRET on
    8 Aug, except n8n refused to publish that one and nothing refuses this one.

    Deleted and recreated on every --apply rather than reused. n8n's public API
    can create and delete a credential but not update one, and the token this
    was built for is Meta's TEST token, which expires roughly every 24 hours.
    Reusing the id would mean silently sending yesterday's token; recreating
    means the value in .env is always the value in n8n.
    """
    token = e.get("WHATSAPP_ACCESS_TOKEN", "").strip()
    if not token:
        return ""
    old = e.get("N8N_WHATSAPP_CRED_ID", "").strip()
    if old:
        try:
            api("DELETE", "/api/v1/credentials/%s" % old)
        except urllib.error.HTTPError as ex:
            if ex.code != 404:
                raise
    cid = api("POST", "/api/v1/credentials", {
        "name": SEND_CRED, "type": "httpHeaderAuth",
        "data": {"name": "Authorization", "value": "Bearer " + token},
    })["id"]
    set_env("N8N_WHATSAPP_CRED_ID", cid)
    print("credential: %s -> %s (token stored in n8n, not in the workflow)"
          % (SEND_CRED, cid))
    return cid


def token_report(e):
    """Say what the send token actually is, and when it dies.

    Worth a network call on every deploy because the failure it catches is
    silent: an expired token does not break the workflow, it breaks one node,
    and the resident simply never gets an answer. The whole reason for moving
    off the API Setup token is that it expires in ~24 hours — so "never
    expires" is a claim to verify, not to take on trust.

    Read through debug_token with the app token rather than the send token
    inspecting itself, because a dead token cannot report its own death.
    """
    token = e.get("WHATSAPP_ACCESS_TOKEN", "").strip()
    app, secret = e.get("APP_ID", "").strip(), e.get("APP_SECRET", "").strip()
    if not (token and app and secret):
        return
    url = ("https://graph.facebook.com/v21.0/debug_token?input_token=%s"
           "&access_token=%s" % (token, "%s|%s" % (app, secret)))
    try:
        d = json.load(urllib.request.urlopen(url))["data"]
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError) as ex:
        print("token    : could not be checked (%s)" % ex)
        return
    exp = d.get("expires_at", 0)
    when = ("never expires" if not exp else
            time.strftime("expires %Y-%m-%d %H:%M UTC", time.gmtime(exp)))
    scopes = [s for s in d.get("scopes", []) if s.startswith("whatsapp")]
    print("token    : %s, %s%s  [%s]"
          % (d.get("type", "?").lower(), when,
             "" if d.get("is_valid") else "  ** NOT VALID **",
             ", ".join(scopes) or "no whatsapp scopes"))
    if exp and exp - time.time() < 3600:
        print("           under an hour left — replies will start failing.")


def ensure_log_cred(e):
    """The Supabase key that writes the chat log, in n8n's credential store.

    Supabase's gateway accepts `apikey` on its own — checked, 200, where
    Authorization alone is a 401 — which matters because an n8n httpHeaderAuth
    credential carries exactly one header. Two headers would have meant putting
    the second one in the workflow JSON, and this is the SERVICE ROLE key:
    full read and write over every table, including the residents' real names,
    phones and debts.

    Deleted and recreated on each --apply for the same reason as the WhatsApp
    token: the public API can create and delete a credential but not update one,
    so reuse would silently keep an old value after a rotation.
    """
    key = e.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not key:
        return ""
    old = e.get("N8N_SUPABASE_CRED_ID", "").strip()
    if old:
        try:
            api("DELETE", "/api/v1/credentials/%s" % old)
        except urllib.error.HTTPError as ex:
            if ex.code != 404:
                raise
    cid = api("POST", "/api/v1/credentials", {
        "name": LOG_CRED, "type": "httpHeaderAuth",
        "data": {"name": "apikey", "value": key},
    })["id"]
    set_env("N8N_SUPABASE_CRED_ID", cid)
    print("credential: %s -> %s" % (LOG_CRED, cid))
    return cid


def ensure_status_cred(e):
    """The Edge Function's shared secret, in n8n's credential store.

    get_request_status calls the Supabase Edge Function directly, and the
    function admits callers on an X-Homies-Secret header. Same rule as the two
    credentials above: a secret as a plain header parameter is a secret written
    into the workflow JSON, so it goes into the store instead. And the same
    delete-and-recreate dance, for the same reason — the public API cannot
    update a credential, and reuse would silently outlive a rotation.
    """
    secret = e.get("TOOL_SECRET", "").strip()
    if not secret:
        return ""
    old = e.get("N8N_TOOLSECRET_CRED_ID", "").strip()
    if old:
        try:
            api("DELETE", "/api/v1/credentials/%s" % old)
        except urllib.error.HTTPError as ex:
            if ex.code != 404:
                raise
    cid = api("POST", "/api/v1/credentials", {
        "name": "Homies tool secret", "type": "httpHeaderAuth",
        "data": {"name": "x-homies-secret", "value": secret},
    })["id"]
    set_env("N8N_TOOLSECRET_CRED_ID", cid)
    print("credential: Homies tool secret -> %s" % cid)
    return cid


def check_env():
    if MISSING:
        print("\nMissing from .env - nothing can be pushed until these exist:\n")
        for key, why in MISSING:
            print("  %-28s %s" % (key, why))
        print("\nAdd them to .env (which is gitignored) and re-run.")
        sys.exit(1)
    if PENDING:
        print("\nDeploying WITHOUT the ability to send. Still empty in .env:\n")
        for key, why in PENDING:
            print("  %-28s %s" % (key, why))
        print("\nThe webhook will verify with Meta and the bot will think, and then")
        print("the reply will fail. Fill these in and re-run --apply to finish it.")
        print("Nothing can reach the webhook until a number is connected in the")
        print("Meta app, so there is no window where a resident is left unanswered.")


def system_prompt():
    """The prompt is the document, not a copy of it.

    Same rule as the voice assistants: two copies of a prompt is how they drift.
    """
    body = open(PROMPT_DOC, encoding="utf-8").read()
    m = re.search(r"^## System prompt\s*$(.*?)(?=^## |\Z)", body, re.M | re.S)
    if not m:
        sys.exit("No '## System prompt' section in %s" % PROMPT_DOC)
    text = m.group(1).strip()
    if len(text) < 500:
        sys.exit("System prompt is %d chars — that is too short to be right." % len(text))
    return text


def api(method, path, body=None):
    e = env()
    req = urllib.request.Request(
        e["N8N_BASE_URL"].strip() + path,
        method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={
            "X-N8N-API-KEY": e["N8N_API_KEY"].strip(),
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "homies/1.0",
        },
    )
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read() or b"{}")
    except urllib.error.HTTPError as exc:
        sys.exit("HTTP %s on %s %s\n%s" % (exc.code, method, path, exc.read().decode()[:600]))


# ---------------------------------------------------------------------------
# The tools offered to the model
# ---------------------------------------------------------------------------
# Deliberately three. The tool webhook answers nine, but this slice is inbound
# support only — every payment and debt tool needs an identity check whose method
# Homies has not defined yet (PRD §13 #1), and a payment flow behind an undefined
# identity check is worse than no payment flow. get_request_status joined on
# 9 Aug: it is read-only and returns nothing money-shaped, which is why it does
# not wait for the identity decision — the same call the voice agents already
# make. It goes STRAIGHT at the Edge Function rather than through the n8n tool
# webhook, because that webhook answers locally and forwards writes async — the
# right shape for a write, and exactly wrong for a lookup that needs a real
# synchronous answer.
#
# The descriptions say WHEN to call, not just what the tool does. On this model
# that is worth real accuracy: it reaches for tools conservatively, and a
# description that only states a capability under-triggers.

TOOLS = [
    {
        "name": "open_request",
        "description": (
            "Open a maintenance or service ticket for this resident. Call this "
            "once you know what the problem is, which building and which "
            "apartment. Returns the real reference number — you must not invent "
            "one, and you must not tell the resident a ticket exists before this "
            "returns."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "What the resident said is wrong, in Hebrew, in their own words.",
                },
                "type": {
                    "type": "string",
                    "enum": ["plumbing", "electrical", "elevator", "cleaning",
                             "security", "structural", "other"],
                },
                "building": {"type": "string", "description": "Street and number."},
                "unit": {"type": "string", "description": "Apartment number."},
                "urgency": {
                    "type": "string",
                    # These four are a check constraint on requests.urgency, not
                    # a preference. Anything else is rejected by Postgres at
                    # insert time and comes back to the model as an English
                    # constraint error mid-Hebrew-conversation.
                    "enum": ["low", "normal", "high", "emergency"],
                    "description": "Infer this; never ask the resident for it. "
                                   "Use emergency only for flooding, fire, gas "
                                   "or someone trapped in a lift.",
                },
            },
            "required": ["description"],
        },
    },
    {
        "name": "get_request_status",
        "description": (
            "Call when the resident asks about an existing service call — its "
            "status, a follow-up, what happened to it. Pass the reference if "
            "they quoted one, in any form (HM-2026-1013 or just the digits). "
            "Without a reference it finds recent calls for the building and "
            "apartment. Returns up to 3 calls with reference, status "
            "(open / in_progress / resolved / cancelled), dates and "
            "description. Read-only; the answer is live from the system."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reference": {"type": "string",
                              "description": "The reference the resident quoted, as written."},
                "building": {"type": "string",
                             "description": "Street and number, if no reference was quoted."},
                "unit": {"type": "string", "description": "Apartment number, if given."},
            },
            "required": [],
        },
    },
    {
        "name": "transfer_to_human",
        "description": (
            "Hand this conversation to a person. Call this whenever money, debt, "
            "payment details or receipts come up; when the resident asks for a "
            "person or is angry; when anything sounds like a safety risk; and "
            "whenever you are simply not sure. Being unsure is a good enough "
            "reason on its own."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "enum": ["out_of_scope", "emergency", "caller_request",
                             "distress", "not_understood"],
                },
            },
            "required": ["reason"],
        },
    },
]


# ---------------------------------------------------------------------------
# Sort — decide what Meta gets back, and whether there is any work to do
# ---------------------------------------------------------------------------

SORT = r"""
// n8n hands the webhook body, query and headers on one item.
const item  = $input.first().json;
const q     = item.query   || {};
const body  = item.body    || {};
const head  = item.headers || {};

const VERIFY_TOKEN = __VERIFY_TOKEN__;
const APP_SECRET   = __APP_SECRET__;

// --- Meta's callback verification -----------------------------------------
// A GET with hub.mode=subscribe. The challenge must come back as PLAIN TEXT.
// Returning JSON here is why a Cloud API webhook silently refuses to save.
if (q['hub.mode'] === 'subscribe') {
  const ok = String(q['hub.verify_token'] || '') === VERIFY_TOKEN;
  return [{ json: { _reply: ok ? String(q['hub.challenge'] || '') : 'forbidden',
                    _work: false } }];
}

// --- Is this actually from Meta? -------------------------------------------
// Every POST Meta sends carries X-Hub-Signature-256: an HMAC-SHA256 of the raw
// body keyed on the app secret. Without checking it, this URL is a public
// endpoint that files service tickets for anybody who finds it — a forged
// envelope is indistinguishable from a resident, and the phone number in it
// decides whose ticket gets opened.
//
// The Crypto node hashes the RAW bytes. Re-serialising the parsed body does
// not reproduce them - key order, spacing and unicode escaping all differ -
// and the HMAC then fails on a payload that is otherwise perfectly valid.
// That is why the webhook node sets rawBody.
//
// Fails CLOSED. An unsigned or wrongly-signed POST is answered 200 — Meta must
// never be told to retry, and a caller who is not Meta learns nothing from the
// response — and then dropped.
//
// THE HMAC IS COMPUTED BY THE CRYPTO NODE UPSTREAM, NOT HERE.
// require('crypto') throws "Module 'crypto' is disallowed" on this instance:
// the Code node runs in a task-runner sandbox with builtins blocked, and that
// is a server setting we cannot reach. The Crypto node is native, needs no
// module, and keeps the secret in n8n's credential store rather than baked into
// this source - which is where it belonged anyway.
if (APP_SECRET) {
  const sent = String(head['x-hub-signature-256'] || '');
  const mine = 'sha256=' + String(item.signature || '');

  if (!sent.startsWith('sha256=')) {
    return [{ json: { _reply: '', _work: false, _rejected: 'unsigned' } }];
  }
  if (sent.length !== mine.length || sent !== mine) {
    return [{ json: { _reply: '', _work: false, _rejected: 'bad signature' } }];
  }
}

// --- A change notification -------------------------------------------------
const entry   = (body.entry || [])[0] || {};
const change  = (entry.changes || [])[0] || {};
const value   = change.value || {};
const msg     = (value.messages || [])[0];

// Delivery receipts and read receipts arrive on this same webhook and are not
// messages. Answer 200 and do nothing — Meta only needs the acknowledgement.
if (!msg) {
  return [{ json: { _reply: '', _work: false } }];
}

const from = String(msg.from || '');
const id   = String(msg.id || '');

// --- Duplicate suppression -------------------------------------------------
// On Meta's message id, which is stable across retries — never on content,
// because a resident who sends the same word twice means it twice.
const store = $getWorkflowStaticData('global');
store.seen = store.seen || {};
const now = Date.now();

// Evict anything older than the 24h window before testing, so the map cannot
// grow without bound.
for (const k of Object.keys(store.seen)) {
  if (now - store.seen[k] > 86400000) delete store.seen[k];
}
if (store.seen[id]) {
  return [{ json: { _reply: '', _work: false } }];
}
store.seen[id] = now;

// --- What the resident actually sent ---------------------------------------
// FOUR shapes carry words, not one. Plain text, a reply-button tap, a pick from
// a list menu, and Meta's older template-button payload.
//
// The two interactive shapes are new and they had to be handled the moment the
// menu existed: an `interactive` message carries NO `text` field, so under the
// previous parser a resident who tapped a button we ourselves had sent was told
// "I can only read text". Sending someone a menu and then not understanding
// their answer is worse than having no menu.
let text = '';
let tapped = '';
// The inbound message and the outbound reply are DIFFERENT strings, and on two
// of the three branches below `text` ends up holding the reply. Logging one as
// the other would put our own words in a resident's mouth in the transcript,
// so the inbound is carried separately from here on.
let inText = null;
if (msg.type === 'text' && msg.text) {
  text = String(msg.text.body || '');
} else if (msg.type === 'interactive' && msg.interactive) {
  const pick = msg.interactive.button_reply || msg.interactive.list_reply || {};
  tapped = String(pick.id || '');
  text   = String(pick.title || '');
} else if (msg.type === 'button' && msg.button) {
  text = String(msg.button.text || '');
}
inText = text.trim() ? text : null;
const msgType = tapped ? 'interactive' : String(msg.type || 'text');

// --- Which language to answer in -------------------------------------------
// DECIDED HERE, IN CODE, AND REMEMBERED. It was the model's job until 8 Aug and
// it did not hold: an English menu, an English row tapped, and the Hebrew
// handover line came back anyway — twice, reported from a real handset both
// times. A prompt rule was competing against a conversation history that was
// mostly Hebrew, and history won. A preference the resident set is a fact, not
// something to re-infer from context on every turn.
//
// Script detection settles the ordinary case with no guessing, because Hebrew
// has its own Unicode block and one Hebrew character is decisive. An explicit
// request — the menu row, or the word in either language — overrides it and
// STICKS, which is the whole meaning of "mode".
//
// Stored in workflow static data, the same place duplicate suppression lives,
// keyed on the phone. Same caveat as that map: it does not survive an n8n
// restore. Losing it costs one message in the wrong language, which is a real
// cost and a smaller one than the two this replaces.
store.lang = store.lang || {};
let asked = false;

if (tapped === 'lang_en' || /\benglish\b/i.test(text) || /אנגלית/.test(text)) {
  store.lang[from] = 'en';
  asked = true;
} else if (tapped === 'lang_he' || /\bhebrew\b/i.test(text) || /עברית/.test(text)) {
  store.lang[from] = 'he';
  asked = true;
} else if (text.trim()) {
  // No explicit request: the script of THIS message decides, and updates the
  // preference — someone who goes back to typing Hebrew wants Hebrew back.
  store.lang[from] = /[֐-׿]/.test(text) ? 'he' : 'en';
}
// A photo carries no words to detect, so it falls back to what was already
// chosen, and to Hebrew for someone whose first ever message is an image.
const lang = store.lang[from] || 'he';

// Media, location, stickers and reactions get the did-not-understand line
// without touching the model. A voice note is the interesting case and is
// deliberately out of this slice.
if (!text.trim()) {
  // A canned reply — flat `to`/`text`, because it goes to the same Send node
  // the agent feeds and that node reads them at the top level.
  return [{ json: {
    _reply: '', _work: false, _canned: true, _menu: false,
    to: from, lang, text: __MEDIA_LINE__[lang],
    in_text: inText, msg_type: msgType, message_id: id,
  } }];
}

// --- "speak english" and nothing else --------------------------------------
// Answered here rather than by the model. Everything the request contained has
// already been acted on above, so there is nothing left to reason about — and
// when the model was left to do it, it replied with the media line.
//
// Only when the request is the WHOLE message: "speak english, there is a leak
// in the lobby" still goes to the agent, in English, with the leak intact.
const leftover = text
  .replace(/\benglish\b|\bhebrew\b/ig, '')
  .replace(/אנגלית|עברית/g, '')
  .replace(/\b(speak|switch|to|in|please|can|you|talk|write|lets|let's)\b/ig, '')
  .replace(/אפשר|בבקשה|לדבר|לכתוב|תדבר|תכתוב|בוא/g, '')
  .replace(/[\s,.!?־-]/g, '');

if (asked && leftover.length < 3) {
  return [{ json: {
    _reply: '', _work: false, _canned: true, _menu: false,
    to: from, lang, text: __SWITCH_LINE__[lang],
    in_text: inText, msg_type: msgType, message_id: id,
  } }];
}

// --- A menu row that starts a flow ------------------------------------------
// 'open' and 'status' get the first question of their flow directly — the tap
// already said what the resident wants, and a model round-trip here produced a
// re-greeting on a real handset. 'human' and 'balance' fall through to the
// agent, which answers both by calling transfer_to_human.
if (tapped === 'open' || tapped === 'status') {
  return [{ json: {
    _reply: '', _work: false, _canned: true, _menu: false,
    to: from, lang, text: __TAP_LINE__[tapped][lang],
    in_text: inText, msg_type: msgType, message_id: id,
  } }];
}

// --- A greeting, and nothing else ------------------------------------------
// This is the only case that gets the menu. Someone who opens with "שלום" has
// told us nothing, so offering choices is genuinely useful. Someone who opens
// with "there's a leak in the lobby" has told us everything, and answering that
// with a menu would undo the rule we just spent the morning writing: do not ask
// what happened when you have already been told.
//
// Anchored and whole-string, so "שלום, יש נזילה" is NOT a greeting — it has a
// fault in it. Trailing punctuation and an emoji or two are stripped first
// because "היי!!" is the same message as "היי".
const bare = text.trim()
  .replace(/[\p{Extended_Pictographic}️]/gu, '')
  .replace(/[\s!?.,־-]+$/u, '')
  .trim().toLowerCase();
const GREETING = new RegExp(
  '^(שלום|שלום רב|היי|הי|אהלן|אהלן וסהלן|יו|מה נשמע|מה קורה|בוקר טוב|צהריים טובים|' +
  'ערב טוב|לילה טוב|hi|hii|hey|hello|yo|good morning|good afternoon|good evening|' +
  'shalom|ahlan)$', 'u');

if (!tapped && GREETING.test(bare)) {
  return [{ json: {
    _reply: '', _work: false, _canned: false, _menu: true,
    to: from, text, lang, message_id: id,
    in_text: inText, msg_type: msgType,
    menu: __MENU__[lang],
  } }];
}

// `tapped` is the row id, and it is carried through NOT for routing — the agent
// reads the title like any other message — but so an execution can be read back
// later and tell a tap from someone typing the same words.
return [{ json: { _reply: '', _work: true, _canned: false, _menu: false,
                  to: from, text, tapped, lang, message_id: id,
                  in_text: inText, msg_type: msgType } }];
"""


# ---------------------------------------------------------------------------
# Brain — the model, the tool loop, and the conversation so far
# ---------------------------------------------------------------------------

def from_ai(name, description):
    """One argument the model is allowed to fill in.

    `$fromAI` is how a tool-mode node declares a parameter to the agent: the name
    and the description become the tool's schema, so the description is prompt
    text and not a comment. Anything NOT wrapped in this is fixed by us and the
    model cannot touch it — which is how the phone number stays off the model.
    """
    return "$fromAI('%s', %s, 'string')" % (name, json.dumps(description, ensure_ascii=False))


# The envelope the tool webhook already speaks, so WhatsApp and both voice agents
# write through one router and one writer.
#
# `$('Sort').first().json.to` rather than `$json.to`: a tool runs inside the
# agent's execution, where the current item is the agent's own, and item pairing
# back to the trigger is not guaranteed. `.first()` on a named node is
# deterministic — and the phone must be deterministic, because it decides whose
# ticket this is.
TOOL_BODY = ("={{ JSON.stringify({ message: { call: {"
             " id: 'wa:' + $('Sort').first().json.to,"
             " assistantOverrides: { variableValues:"
             " { phone: $('Sort').first().json.to } } },"
             " toolCalls: [{ id: 'wa', function: { name: '%s',"
             " arguments: { %s } } }] } }) }}")


def js(src, **subs):
    for k, v in subs.items():
        src = src.replace("__%s__" % k, json.dumps(v, ensure_ascii=False))
    return src


def workflow(e):
    node = lambda **kw: dict({"parameters": {}, "typeVersion": 1}, **kw)

    verify = need(e, "WHATSAPP_WEBHOOK_VERIFY_TOKEN",
                  "any string you choose; you paste the same one into the Meta app.")
    key = need(e, "OPENROUTER_API_KEY", "the chatbot's model key. openrouter.ai -> Keys.")
    # Soft: an empty secret turns the signature check off rather than blocking a
    # deploy. That is the right default only because it is loud — the dry run
    # prints "signature: OFF" every time, so nobody can leave it off by accident.
    app_secret = e.get("APP_SECRET", "").strip()
    crypto_cred = e.get("N8N_CRYPTO_CRED_ID", "").strip()
    phone_id = later(e, "WHATSAPP_PHONE_NUMBER_ID",
                     "Meta app -> WhatsApp -> API Setup -> 'Phone number ID'.")
    later(e, "WHATSAPP_ACCESS_TOKEN",
          "Meta app -> WhatsApp -> API Setup -> temporary access token.")
    send_cred = e.get("N8N_WHATSAPP_CRED_ID", "").strip()
    log_cred = e.get("N8N_SUPABASE_CRED_ID", "").strip()
    log_url = e.get("SUPABASE_URL", "").strip().rstrip("/") + "/rest/v1/messages"
    status_cred = e.get("N8N_TOOLSECRET_CRED_ID", "").strip()
    fn_url = e.get("SUPABASE_URL", "").strip().rstrip("/") + "/functions/v1/debt-tools"
    base = e["N8N_BASE_URL"].strip().rstrip("/")

    return {
        "name": WF_NAME,
        "settings": {"executionOrder": "v1"},
        "nodes": [
            node(
                id="webhook", name="WhatsApp", type="n8n-nodes-base.webhook",
                typeVersion=2, position=[0, 0],
                # n8n registers the production webhook against this id, not the
                # path. Created without one, the workflow reports active:true and
                # every request still 404s "not registered".
                webhookId="homies-whatsapp-v1",
                parameters={
                    # Meta verifies with GET and delivers with POST, on the same
                    # URL. Both have to land here.
                    "multipleMethods": True,
                    "httpMethod": ["GET", "POST"],
                    "path": WEBHOOK_PATH,
                    "responseMode": "responseNode",
                    # rawBody keeps the exact bytes Meta signed, as binary,
                    # alongside the parsed body. Re-serialising the parsed
                    # object does not reproduce them, so without this the
                    # signature check below can only ever fail.
                    "options": {"rawBody": True},
                },
            ),
            # Between the webhook and Sort, because Sort cannot do this itself.
            # Writes the hex digest of the raw body to `signature`; Sort compares
            # it against Meta's header.
            #
            # alwaysOutputData so a GET, which carries no body to hash, still
            # produces an item and reaches Sort. Without it the verification
            # handshake dies here and the callback URL can never be saved.
            node(
                id="sign", name="Sign the raw body", type="n8n-nodes-base.crypto",
                # V2, not V1. V1 takes the secret as a plain node parameter,
                # which would write APP_SECRET into the workflow JSON — and n8n
                # itself refused the publish with "Missing or invalid required
                # parameters: secret" when this was set to 1. V2 reads it from
                # the crypto credential, which is where a secret belongs.
                typeVersion=2, position=[240, 0],
                parameters={
                    "action": "hmac",
                    "type": "SHA256",
                    "binaryData": True,
                    "binaryPropertyName": "data",
                    "dataPropertyName": "signature",
                    "encoding": "hex",
                },
                credentials={"crypto": {"id": crypto_cred, "name": "Homies Meta app secret"}},
                alwaysOutputData=True,
                onError="continueRegularOutput",
            ),
            node(
                id="sort", name="Sort", type="n8n-nodes-base.code",
                typeVersion=2, position=[480, 0],
                parameters={"jsCode": js(SORT, VERIFY_TOKEN=verify,
                                         APP_SECRET=app_secret,
                                         MEDIA_LINE=MEDIA_LINE, MENU=MENU,
                                         SWITCH_LINE=SWITCH_LINE,
                                         TAP_LINE=TAP_LINE)},
            ),
            node(
                id="respond", name="Answer Meta",
                type="n8n-nodes-base.respondToWebhook", typeVersion=1.1,
                position=[720, -180],
                parameters={
                    # text, not json — Meta's verification wants the bare
                    # challenge and rejects it wrapped in quotes.
                    "respondWith": "text",
                    "responseBody": "={{ $json._reply }}",
                    "options": {},
                },
            ),
            node(
                id="haswork", name="Is there a message?", type="n8n-nodes-base.if",
                typeVersion=2, position=[720, 60],
                parameters={"conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                    "conditions": [{
                        "id": "w",
                        "leftValue": "={{ $json._work }}",
                        "rightValue": "",
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                    }],
                    "combinator": "and",
                }},
            ),
            node(
                id="iscanned", name="Canned reply?", type="n8n-nodes-base.if",
                typeVersion=2, position=[720, 240],
                parameters={"conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                    "conditions": [{
                        "id": "c",
                        "leftValue": "={{ $json._canned }}",
                        "rightValue": "",
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                    }],
                    "combinator": "and",
                }},
            ),
            # --- The chat log -------------------------------------------
            # Two nodes, both fire-and-forget, both on the error-tolerant
            # setting: a log that can break a conversation is worse than no log.
            # If Supabase is down the resident still gets answered and the row
            # is simply missing, which the dashboard shows as a gap.
            #
            # Fed from the three If nodes rather than from Sort, because those
            # three branches are exactly the real inbound messages — a
            # verification GET, a duplicate and a rejected signature reach none
            # of them, so no extra condition is needed to exclude them.
            node(
                id="loginbound", name="Log inbound", type="n8n-nodes-base.httpRequest",
                typeVersion=4.2, position=[960, -180],
                parameters={
                    "method": "POST", "url": log_url,
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpHeaderAuth",
                    "sendBody": True, "specifyBody": "json",
                    # in_text, NOT text. On the media and menu branches `text`
                    # holds the reply we are about to send, and logging that as
                    # the resident's message would put our words in their mouth.
                    "jsonBody": "={{ JSON.stringify({"
                                " phone: $json.to, direction: 'inbound',"
                                " sender: 'resident', body: $json.in_text,"
                                " message_type: $json.msg_type,"
                                " external_id: $json.message_id,"
                                " lang: $json.lang, source: 'n8n' }) }}",
                    "options": {"timeout": 10000},
                },
                credentials=({"httpHeaderAuth": {"id": log_cred, "name": LOG_CRED}}
                             if log_cred else {}),
                onError="continueRegularOutput", alwaysOutputData=True,
            ),
            # Runs BESIDE Send, not after it, and that is the only way the text
            # is reachable: after Send, $json is Meta's response and the words we
            # sent are gone. Sharing Send's input means the same item is in hand.
            #
            # Positioned ABOVE Send on purpose. executionOrder v1 walks the
            # canvas top to bottom, and when Send failed first — a recipient off
            # the test number's allow-list — the run aborted and this node never
            # ran at all. A send failure is exactly the moment the log matters
            # most, so it cannot sit downstream of one.
            #
            # The three sources put the reply in three different fields —
            # `output` from the agent, `text` from a canned line or the
            # handover, and the menu's own body — so all three are read. The
            # menu is checked FIRST: on that branch `text` still holds the
            # resident's greeting, and testing it first logged their own words
            # back as our reply.
            node(
                id="logreply", name="Log reply", type="n8n-nodes-base.httpRequest",
                typeVersion=4.2, position=[1200, -60],
                parameters={
                    "method": "POST", "url": log_url,
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpHeaderAuth",
                    "sendBody": True, "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify({"
                                " phone: $('Sort').first().json.to,"
                                " direction: 'outbound', sender: 'bot',"
                                " body: $json.menu ? $json.menu.body.text :"
                                " ($json.output || $json.text),"
                                " message_type: $json.menu ? 'interactive' : 'text',"
                                " lang: $('Sort').first().json.lang,"
                                " source: 'n8n' }) }}",
                    "options": {"timeout": 10000},
                },
                credentials=({"httpHeaderAuth": {"id": log_cred, "name": LOG_CRED}}
                             if log_cred else {}),
                onError="continueRegularOutput", alwaysOutputData=True,
            ),
            node(
                id="ismenu", name="Menu?", type="n8n-nodes-base.if",
                typeVersion=2, position=[720, 600],
                parameters={"conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                    "conditions": [{
                        "id": "m",
                        "leftValue": "={{ $json._menu }}",
                        "rightValue": "",
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                    }],
                    "combinator": "and",
                }},
            ),
            # A SECOND send node rather than a conditional body on the first.
            #
            # A text message and an interactive one are different payloads —
            # `type: text` with `text.body` against `type: interactive` with a
            # whole `interactive` object — and folding both into one expression
            # produces a ternary spanning two payload shapes that nobody can read
            # and no execution log explains. Two nodes cost one node and are
            # obvious on the canvas.
            #
            # The payload itself is built in Sort, not here, so the menu's
            # wording lives in one place next to the language that chose it.
            node(
                id="sendmenu", name="Send menu", type="n8n-nodes-base.httpRequest",
                typeVersion=4.2, position=[960, 600],
                parameters={
                    "method": "POST",
                    "url": "https://graph.facebook.com/%s/%s/messages" % (GRAPH_VERSION, phone_id),
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpHeaderAuth",
                    "sendBody": True, "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify({ messaging_product: 'whatsapp',"
                                " to: $json.to, type: 'interactive',"
                                " interactive: $json.menu }) }}",
                    "options": {"timeout": 20000},
                },
                credentials=({"httpHeaderAuth": {"id": send_cred, "name": SEND_CRED}}
                             if send_cred else {}),
            ),
            # The agent, and its four sub-nodes. Replaced a Code node that ran
            # the tool-use loop by hand against OpenRouter's HTTP API.
            #
            # What the Code node did better: the loop was 40 readable lines with
            # its iteration cap on line one, and a 402 from OpenRouter was caught
            # in a try/catch that answered with the handover sentence.
            #
            # What this does better, and why it wins: the model key now lives in
            # n8n's credential store instead of being interpolated into a code
            # string, conversation memory is a node rather than workflow static
            # data that does not survive a restore, and the two tools are visible
            # on the canvas as things the agent can reach rather than a URL buried
            # in a fetch call. The failure path is rebuilt below as a real error
            # branch, which is the one thing that had to be replaced rather than
            # inherited.
            node(
                id="agent", name="Answer the resident",
                type="@n8n/n8n-nodes-langchain.agent",
                typeVersion=3, position=[960, 60],
                parameters={
                    "promptType": "define",
                    # The turn carries the language decision with it, rather
                    # than leaving the model to re-derive it from a history
                    # that may be mostly the other language. Sort decided it
                    # deterministically; this makes the decision impossible to
                    # miss, on every single turn, at the top of the message.
                    #
                    # A directive inside the user turn rather than in the system
                    # prompt on purpose: the system prompt is constant and this
                    # is not, and a constant instruction is exactly what the
                    # model was already failing to apply against live context.
                    "text": "={{ ($json.lang === 'en'"
                            " ? '[Answer this message in ENGLISH.]'"
                            " : '[ענה על ההודעה הזאת בעברית.]')"
                            " + '\\n' + $json.text }}",
                    "options": {"systemMessage": system_prompt()},
                },
                # A model error must not take the workflow down. OpenRouter 402s
                # on every call while the balance is empty, and a resident who
                # gets silence is worse off than one told a person will follow up.
                onError="continueErrorOutput",
            ),
            node(
                id="model", name="OpenRouter", type="@n8n/n8n-nodes-langchain.lmChatOpenRouter",
                typeVersion=1, position=[960, 420],
                parameters={"model": MODEL, "options": {"maxTokens": MAX_TOKENS}},
                credentials={"openRouterApi": {"id": e.get("N8N_OPENROUTER_CRED_ID", "").strip(),
                                               "name": "Homies OpenRouter"}},
            ),
            # Keyed on the phone number off the WhatsApp envelope, which is the
            # same rule as everywhere else here: never anything the resident
            # typed. A hardcoded key would cross every resident's conversation
            # into one thread.
            node(
                id="memory", name="Conversation so far",
                type="@n8n/n8n-nodes-langchain.memoryBufferWindow",
                typeVersion=1.3, position=[1200, 420],
                parameters={"sessionIdType": "customKey",
                            "sessionKey": "={{ $json.to }}",
                            "contextWindowLength": 30},
                # 12 until 8 Aug. Raised because the language choice now lives
                # HERE and nowhere else: a resident who asks for English is
                # remembered only for as long as that request is still inside
                # the window, and at 12 messages it scrolls out mid-conversation
                # and the bot silently reverts to Hebrew. 30 covers any service
                # conversation; at gemini-2.5-flash prices the extra context is
                # a rounding error. A hard per-phone language field belongs in
                # an n8n Data Table, which this instance supports and which is
                # the right fix when the toggle needs to survive indefinitely.
            ),
            # Both tools POST the Vapi-shaped envelope the tool webhook already
            # speaks, so WhatsApp and the voice agents write through one router
            # and one writer. The phone is interpolated from the item, NOT a
            # placeholder — a placeholder is something the model fills in, and
            # the model must never be able to choose whose ticket this is.
            node(
                id="tool_open", name="open_request",
                type="n8n-nodes-base.httpRequestTool",
                typeVersion=4.2, position=[1440, 420],
                parameters={
                    "method": "POST",
                    "url": base + "/webhook/homies-debt-tools",
                    "sendBody": True, "specifyBody": "json",
                    "jsonBody": TOOL_BODY % (
                        "open_request",
                        "description: %s, type: %s, building: %s, unit: %s, urgency: %s" % (
                            from_ai("description", TOOLS[0]["input_schema"]["properties"]["description"]["description"]),
                            from_ai("type", "One of " + "/".join(TOOLS[0]["input_schema"]["properties"]["type"]["enum"])),
                            from_ai("building", "Street and number."),
                            from_ai("unit", "Apartment number, digits only."),
                            from_ai("urgency", TOOLS[0]["input_schema"]["properties"]["urgency"]["description"]
                                    + " One of low/normal/high/emergency."),
                        )),
                    "options": {"timeout": 25000},
                    "descriptionType": "manual",
                    "toolDescription": TOOLS[0]["description"],
                },
            ),
            node(
                id="tool_transfer", name="transfer_to_human",
                type="n8n-nodes-base.httpRequestTool",
                typeVersion=4.2, position=[1680, 420],
                parameters={
                    "method": "POST",
                    "url": base + "/webhook/homies-debt-tools",
                    "sendBody": True, "specifyBody": "json",
                    "jsonBody": TOOL_BODY % (
                        "transfer_to_human",
                        "reason: %s" % from_ai(
                            "reason", "One of " + "/".join(
                                TOOLS[2]["input_schema"]["properties"]["reason"]["enum"])),
                    ),
                    "options": {"timeout": 25000},
                    "descriptionType": "manual",
                    "toolDescription": TOOLS[2]["description"],
                },
            ),
            # The one tool that skips the n8n router. The router answers Vapi
            # locally and forwards writes async — right for a write, wrong for
            # a lookup that needs a real synchronous answer. Same envelope,
            # same Edge Function the voice agents' status tool calls, secret
            # in the credential store.
            node(
                id="tool_status", name="get_request_status",
                type="n8n-nodes-base.httpRequestTool",
                typeVersion=4.2, position=[1920, 420],
                parameters={
                    "method": "POST",
                    "url": fn_url,
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpHeaderAuth",
                    "sendBody": True, "specifyBody": "json",
                    "jsonBody": TOOL_BODY % (
                        "get_request_status",
                        "reference: %s, building: %s, unit: %s" % (
                            from_ai("reference",
                                    "The reference the resident quoted, exactly as "
                                    "written — HM-2026-1013 or just the digits. "
                                    "Empty if none was quoted."),
                            from_ai("building", "Street and number, if no reference."),
                            from_ai("unit", "Apartment number, if given."),
                        )),
                    "options": {"timeout": 25000},
                    "descriptionType": "manual",
                    "toolDescription": TOOLS[1]["description"],
                },
                credentials=({"httpHeaderAuth": {"id": status_cred,
                                                 "name": "Homies tool secret"}}
                             if status_cred else {}),
            ),
            # The error branch. Not a nicety: this is the sentence the Code node
            # used to produce from its own catch block, and without it a model
            # failure is a resident who is never answered at all.
            node(
                id="handover", name="Hand over instead", type="n8n-nodes-base.set",
                typeVersion=3.4, position=[1200, 240],
                parameters={"assignments": {"assignments": [
                    {"id": "to", "name": "to", "type": "string",
                     "value": "={{ $('Sort').item.json.to }}"},
                    {"id": "text", "name": "text", "type": "string",
                     "value": "={{ $('Sort').first().json.lang === 'en' ? %s : %s }}"
                              % (json.dumps(HANDOVER_LINE_EN, ensure_ascii=False),
                                 json.dumps(HANDOVER_LINE, ensure_ascii=False))},
                ]}, "options": {}},
            ),
            node(
                id="send", name="Send", type="n8n-nodes-base.httpRequest",
                typeVersion=4.2, position=[1440, 60],
                parameters={
                    "method": "POST",
                    "url": "https://graph.facebook.com/%s/%s/messages" % (GRAPH_VERSION, phone_id),
                    # The token is a credential, not a header parameter — see
                    # ensure_send_cred(). The phone number id stays in the URL
                    # because it identifies the sender and is not a secret.
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpHeaderAuth",
                    "sendBody": True, "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify({ messaging_product: 'whatsapp',"
                                " to: $('Sort').item.json.to, type: 'text',"
                                " text: { body: $json.output || $json.text } }) }}",
                    "options": {"timeout": 20000},
                },
                credentials=({"httpHeaderAuth": {"id": send_cred, "name": SEND_CRED}}
                             if send_cred else {}),
            ),
            # --- The options, again, after a completed flow -----------------
            # Chained AFTER Send, which is the only ordering Meta respects: two
            # parallel HTTP calls can arrive swapped, and a menu that lands
            # before the reference number reads as changing the subject.
            #
            # The test is for a reference number in the outgoing reply — the
            # marker of a completed flow, and the model cannot fake it because
            # rule one of the prompt is that references come from the tool.
            # isExecuted guards the canned and menu branches, where the agent
            # never ran and referencing its output would throw.
            node(
                id="hasref", name="Ticket in the reply?", type="n8n-nodes-base.if",
                typeVersion=2, position=[1680, 60],
                parameters={"conditions": {
                    "options": {"caseSensitive": True, "leftValue": "",
                                "typeValidation": "loose"},
                    "conditions": [{
                        "id": "r",
                        "leftValue": "={{ $('Answer the resident').isExecuted"
                                     " ? ($('Answer the resident').first().json.output || '')"
                                     " : '' }}",
                        "rightValue": "HM-\\d{4}-\\d+",
                        "operator": {"type": "string", "operation": "regex"},
                    }],
                    "combinator": "and",
                }},
            ),
            # Rebuilds the flat to/menu shape the Send menu node reads, so the
            # follow-up rides the same node as the greeting menu. The body
            # differs — "עוד משהו?" — the rows are identical on purpose.
            node(
                id="followup", name="Options again", type="n8n-nodes-base.set",
                typeVersion=3.4, position=[1920, 60],
                parameters={"assignments": {"assignments": [
                    {"id": "to", "name": "to", "type": "string",
                     "value": "={{ $('Sort').first().json.to }}"},
                    {"id": "menu", "name": "menu", "type": "object",
                     "value": "={{ $('Sort').first().json.lang === 'en' ? %s : %s }}"
                              % (json.dumps(FOLLOWUP_MENU["en"], ensure_ascii=False),
                                 json.dumps(FOLLOWUP_MENU["he"], ensure_ascii=False))},
                ]}, "options": {}},
            ),
        ],
        "connections": {
            # TWO OUTPUTS, NOT ONE. `multipleMethods` gives the webhook node one
            # output per method in the order they are listed — GET on 0, POST on
            # 1 — and this connected only the first.
            #
            # The result passes every check you would think to run. Meta's
            # verification is a GET, so the callback URL saves and the dashboard
            # shows a verified webhook. Then every actual message arrives as a
            # POST on output 1, lands on nothing, and the execution ends
            # `success` having run one node. No error, no retry, no reply — the
            # resident is simply never answered.
            #
            # Caught 8 Aug by posting a real message envelope at the live URL
            # before anything was connected in Meta. It would not have been
            # caught by the verification handshake, which is the test everybody
            # runs.
            "WhatsApp": {"main": [
                [{"node": "Sign the raw body", "type": "main", "index": 0}],  # GET
                [{"node": "Sign the raw body", "type": "main", "index": 0}],  # POST
            ]},
            "Sign the raw body": {"main": [[{"node": "Sort", "type": "main", "index": 0}]]},
            # Answering is never gated on there being work. A delivery receipt,
            # a duplicate and a photo all write nothing and all still have to
            # return 200, or Meta retries them forever.
            "Sort": {"main": [[
                {"node": "Answer Meta", "type": "main", "index": 0},
                {"node": "Is there a message?", "type": "main", "index": 0},
                {"node": "Canned reply?", "type": "main", "index": 0},
                {"node": "Menu?", "type": "main", "index": 0},
            ]]},
            "Is there a message?": {"main": [[
                {"node": "Answer the resident", "type": "main", "index": 0},
                {"node": "Log inbound", "type": "main", "index": 0}]]},
            # Media with no text answers without touching the model. It reaches
            # the same Send node, which is why Sort emits flat to/text for it.
            "Canned reply?": {"main": [[
                {"node": "Send", "type": "main", "index": 0},
                {"node": "Log inbound", "type": "main", "index": 0},
                {"node": "Log reply", "type": "main", "index": 0}]]},
            # The menu is its own send node — a list payload is not a text one.
            "Menu?": {"main": [[
                {"node": "Send menu", "type": "main", "index": 0},
                {"node": "Log inbound", "type": "main", "index": 0},
                {"node": "Log reply", "type": "main", "index": 0}]]},
            # main[0] is the answer, main[1] is the error output opened by
            # onError. Both end at Send, because either way the resident gets a
            # message — that is the whole point of having a second branch.
            "Answer the resident": {"main": [
                [{"node": "Send", "type": "main", "index": 0},
                 {"node": "Log reply", "type": "main", "index": 0}],
                [{"node": "Hand over instead", "type": "main", "index": 0}],
            ]},
            "Hand over instead": {"main": [[
                {"node": "Send", "type": "main", "index": 0},
                {"node": "Log reply", "type": "main", "index": 0}]]},
            # After every text send, ask whether a flow just completed. The If
            # answers no on every branch except an agent reply carrying a
            # reference, so chaining here costs nothing on the others.
            "Send": {"main": [[
                {"node": "Ticket in the reply?", "type": "main", "index": 0}]]},
            "Ticket in the reply?": {"main": [[
                {"node": "Options again", "type": "main", "index": 0}]]},
            "Options again": {"main": [[
                {"node": "Send menu", "type": "main", "index": 0},
                {"node": "Log reply", "type": "main", "index": 0}]]},
            # Sub-nodes connect UP into the agent on their own connection types,
            # and the direction is the part that catches people out: the model,
            # the memory and each tool are the SOURCE, the agent is the target.
            "OpenRouter": {"ai_languageModel": [[
                {"node": "Answer the resident", "type": "ai_languageModel", "index": 0}]]},
            "Conversation so far": {"ai_memory": [[
                {"node": "Answer the resident", "type": "ai_memory", "index": 0}]]},
            "open_request": {"ai_tool": [[
                {"node": "Answer the resident", "type": "ai_tool", "index": 0}]]},
            "get_request_status": {"ai_tool": [[
                {"node": "Answer the resident", "type": "ai_tool", "index": 0}]]},
            "transfer_to_human": {"ai_tool": [[
                {"node": "Answer the resident", "type": "ai_tool", "index": 0}]]},
        },
    }


def find():
    for w in api("GET", "/api/v1/workflows?limit=100").get("data", []):
        if w["name"] == WF_NAME:
            return w
    return None


def main():
    e = env()
    # Before workflow(), because the Send node references the credential id, and
    # only on --apply: a dry run must not create anything in n8n.
    if "--apply" in sys.argv:
        ensure_send_cred(e)
        ensure_log_cred(e)
        ensure_status_cred(e)
        e = env()
    wf = workflow(e)
    check_env()
    existing = find()
    base = e["N8N_BASE_URL"].strip().rstrip("/")

    try:
        check(wf["nodes"], WF_NAME)
    except LayoutError as ex:
        sys.exit("\n%s\n" % ex)

    print("workflow : %s" % WF_NAME)
    print("nodes    : %s" % ", ".join(n["name"] for n in wf["nodes"]))
    print("callback : %s/webhook/%s" % (base, WEBHOOK_PATH))
    print("model    : %s via OpenRouter  effort=%s  max_tokens=%d"
          % (MODEL, EFFORT, MAX_TOKENS))
    print("tools    : %s" % ", ".join(t["name"] for t in TOOLS))
    token_report(e)
    print("signature: %s" % ("ON — X-Hub-Signature-256 checked against APP_SECRET"
                              if e.get("APP_SECRET", "").strip()
                              else "OFF — anyone with the URL can forge a resident"))
    print("prompt   : %d chars from %s"
          % (len(system_prompt()), os.path.relpath(PROMPT_DOC, ROOT)))
    print("target   : %s" % (("update " + existing["id"]) if existing else "create new"))

    if "--activate" in sys.argv:
        if not existing:
            sys.exit("Nothing to activate — run with --apply first.")
        api("POST", "/api/v1/workflows/%s/activate" % existing["id"])
        print("\nactivated. Paste this into the Meta app as the callback URL:")
        print("  %s/webhook/%s" % (base, WEBHOOK_PATH))
        return

    if "--apply" not in sys.argv:
        print("\nDry run. Re-run with --apply to push.")
        return

    if existing:
        api("PUT", "/api/v1/workflows/%s" % existing["id"], wf)
        wid = existing["id"]
        print("\nupdated %s" % wid)
    else:
        wid = api("POST", "/api/v1/workflows", wf)["id"]
        print("\ncreated %s" % wid)
    print("%s/workflow/%s" % (base, wid))
    print("\nNot active yet. Run with --activate, then add the callback URL in Meta.")


if __name__ == "__main__":
    main()
