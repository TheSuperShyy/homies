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

# NO TEMPERATURE WAS SENT AT ALL UNTIL 31 AUG, and that is worth a paragraph
# because the same omission has already cost this project once.
#
# The node only ever carried maxTokens, so the model ran at whatever OpenRouter
# and Google default to — for Gemini that is 1.0, which is high for a service
# desk. On 26 Aug the voice agent was found in exactly this state ("the live
# model object had no temperature at all — the design value 0.3 was lost when
# the assistant was rebuilt"), on a call that produced real Hebrew typos in the
# bot's own logged output. That one turned out to have a second cause as well,
# but the missing temperature was real and was fixed with 0.3.
#
# Set here after feedback that the bot misspells simple Hebrew words. No
# examples came with the feedback, so this is the likeliest cause addressed
# rather than a reproduced fault fixed — read the probe output before believing
# it worked. 0.3 is the value the rest of the project already uses.
#
# If it does not hold, the next suspect is the model, not the prompt: this bot
# runs google/gemini-2.5-flash, chosen on 8 Aug for cost, and the comment above
# MODEL says its Hebrew was never signed off by a native speaker. A spelling
# rule in the prompt is NOT the next thing to try — twice recorded here that a
# prompt hint does not change what a model emits at token level.
# RAISED 0.3 -> 0.6 on 31 Aug, deliberately reversing the same day's change.
#
# 0.3 was set that morning against a Hebrew-spelling complaint. It is also
# what makes the model reach for the nearest finished sentence in the prompt
# every time: three different hesitations came back with the SAME Hebrew
# sentence, word for word. The prompt now offers ✓/✗ pairs with two and three
# variants each, and variants cannot vary at 0.3.
#
# The evidence for 0.3 was always thin: the spelling complaint arrived with no
# examples, was never reproduced, and six probe replies at 0.3 had no typos --
# which is what 0.6 would also produce. If Hebrew degrades, step to 0.45 and
# re-probe; that is one constant and one push.
TEMPERATURE = 0.6

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

# HEBREW ONLY, ASKED FOR 12 AUG: *"i want the english to be removed 100% for
# now"*. The English half of every line, the English menu, the English row and
# the whole language-switch path are gone — not disabled behind a flag, removed,
# because a switch that nobody can reach is a thing the next person has to read
# and rule out. What is left is `lang`, pinned to 'he': it is written on every
# `messages` row and the dashboard reads it, so the field stays even though it
# now has one value.
#
# What went with it: HANDOVER_LINE_EN, SWITCH_LINE and MEDIA_LINE's English
# twin (both added 8 Aug, when a fixed line fixed in one language came back in
# the other), the lang_en / lang_he menu rows, and Sort's switch detection.
# `git log` has them if English is ever wanted back — and the prompt section
# that goes with them is in the same commit.

# The one line for a message that carries no words. It is quoted in
# docs/features/11-whatsapp-bot/prompt.md as one of the bot's two fixed lines,
# and until 8 Aug the two copies had drifted apart — the prompt documented
# "אני קורא כאן רק טקסט" while the code sent "אני יכול לקרוא רק טקסט כרגע".
# The code is the one a resident actually reads, so the code was made to match
# the document rather than the other way round.
MEDIA_LINE = {
    "he": "אני קורא כאן רק טקסט. אפשר לכתוב לי מה קרה?",
}

# What a tap on 'open' or 'status' gets, without a model round-trip. Before
# 9 Aug those taps went to the agent as bare row titles — "Open a service call"
# — and the model, handed four words with no verb of the resident's own,
# re-introduced itself and asked what's up, which is a menu answering a menu.
# The tap already says what they want; the only useful reply is the first
# question of that flow, and that question is the same every time — which is
# the definition of a canned line. 'human' and 'balance' still go to the
# agent: 'human' becomes transfer_to_human, and 'balance' now opens with the
# identity question (13 Aug).
#
# Balance is the one flow whose first question is fixed and still is NOT canned,
# which is worth the sentence. A canned line never reaches the model, so the
# agent has no record of having asked it — and the answer to *this* question is
# a name and a number, which on their own could belong to any flow. So the model
# asks this one itself, and remembers it.
#
# THIS COMMENT USED TO GO ON to say 'open' and 'status' get away with it because
# their answers say what they are, a fault description or a reference number.
# Wrong, and it cost 26 Aug: a resident asked for a reference number answered
# "אין לי", which says what it is not. The reasoning held for the answers that
# were imagined and not for the one that arrived. `said()` in the Sort node now
# carries every canned line forward regardless, so the argument no longer has to
# be right — which is the point of not making it.
#
# Same grammar rule as every other fixed line: nothing addresses the resident
# in a gendered form.
# DEAD SINCE 31 AUG, AND KEPT ONLY AS A RECORD. The owner asked for nothing
# templated, so the 'open' and 'status' taps stopped being answered by the
# workflow and now reach the model like any other message. Nothing reads this
# any more — the SORT template's tap branch went with it. Do not wire it back
# in without saying so: these sentences are the ones the owner pointed at.
TAP_LINE = {
    # The fault only, and not the building with it. Tapping this row IS the
    # explicit request, so the offer the prompt now opens with ("shall I open a
    # ticket?") would re-ask a question already answered — which is the one case
    # the offer is skipped. What follows is the model asking building and
    # apartment together, so asking for the building here would split that pair
    # across two messages and leave the apartment dangling on its own.
    #
    # WARMED 27 AUG, asked for off a handset screenshot, and it is the same
    # change as `status` below a day later: "בטח. אפשר לספר לי מה קרה?" was two
    # clipped fragments, correct and cold, with nothing saying anyone intends
    # to help. The first worked example in the prompt's "וככה שואלים" list is
    # this sentence and moved with it — THE TWO ARE ONE CHANGE, same as status.
    "open": {
        "he": "בטח, אשמח לעזור. אפשר לספר לי מה קרה?",
    },
    # WARMED 26 AUG, on the owner's reading of the live reply: "בטח. מה מספר
    # הקריאה?" is correct, short and cold. Two clipped fragments land on someone
    # who has just asked for help without one word saying anybody is going to
    # help them. The first half of the sentence is what makes it service rather
    # than a form, and it is not redundant just because helping is obvious.
    # The same sentence is in the prompt, under "מצב של קריאה קיימת", because
    # the model produces it on the typed path and this canned copy produces it
    # on the tap path. THE TWO ARE ONE CHANGE.
    "status": {
        "he": "בטח, אשמח לבדוק בשבילך. יש לך את מספר הקריאה?",
    },
}

# BOTH LINES WERE REWRITTEN ON 25 AUG, off a screenshot from a real handset.
#
# `status` read "מה מספר הקריאה? אפשר גם רק את הספרות האחרונות — ואם אין מספר,
# בניין ודירה." Three options in one breath, and the prompt has forbidden
# exactly that since 24 Aug: the status opener is one question, and a resident
# with no number will say so. Worse, it is where the owner first saw the em
# dash, and it was never the model writing it -- this line is canned, so no
# amount of prompt work could have reached it.
#
# `open` read "בסדר. מה התקלה?" -- the flat "what is the problem" the 25 Aug
# prompt pass replaced everywhere else. A tap is still an explicit request, so
# the offer is still skipped; only the wording changed, to the same open
# invitation the prompt now uses.

# The menu, sent ONLY when someone opens with a bare greeting.
#
# A list rather than reply buttons because reply buttons cap at three and the
# client asked for five options. Meta's limits, which are hard: row title 24
# characters, description 72, the button that opens the list 20, and ten rows
# across all sections.
#
# Every row works now. `balance` was the last holdout — it handed over to a
# human until 9 Aug, when get_balance arrived. The identity question that kept
# it there (PRD §13 #1) is answered as of 13 Aug: a balance needs a full name
# and a phone number, typed by the resident, landing on the same record. The
# WhatsApp envelope, a name alone and building+apartment alone were all enough
# before, and all three are things somebody else knows. Reading amounts is all
# it does; paying, receipts and disputes still reach the team. `status` came
# off the handover path the same day get_request_status arrived.
#
# The Hebrew here obeys the same rule the prompt does: nothing addresses the
# resident with a gendered form. "אפשרויות" rather than "בחר", which is
# masculine imperative, and "הצוות יחזור בהקדם" rather than "יחזור אליך".
# THE BODY IS THE GREETING, AND IT IS THE SECOND COPY OF IT.
# A bare "היי" never reaches the model — the GREETING regex in the Sort node
# short-circuits and this list message is sent by the workflow. So the opener
# lives in two places that cannot share a value: the system prompt in
# docs/features/11-whatsapp-bot/prompt.md, and here. They must say the same
# thing, and on 13 Aug they did not: the prompt was rewritten to
# "היי, כאן שירות הלקוחות של הומיז. במה אפשר לעזור?" and this line was left at
# the old "היי, כאן הומיז. מה קרה?", so every resident who opened with a plain
# hello got the old greeting from a prompt that no longer contained it. Verified
# live on 14 Aug from a real handset. Change both or neither.
MENU = {
    "he": {
        "type": "list",
        # Must stay character-for-character identical to the opener in
        # prompt.md — check_greeting() below fails the deploy if they drift, and
        # they did drift once, on 13 Aug. Name restored 24 Aug.
        "body": {"text": "היי, כאן מיכאל מהומיז. במה אפשר לעזור?"},
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
            ]}],
        },
    },
}


# THE FOLLOW-UP MENU IS GONE, AND THAT IS THE POINT OF THIS COMMENT.
#
# Until 31 Aug the options list was sent a second time after every completed
# flow — body "עוד משהו?", same four rows — fired by an If that asked
# whether the outgoing reply contained a question mark. Asked for on 9 Aug, on
# the reasoning that a resident should not be left with a reference number and
# silence.
#
# What it actually did was end every conversation with a dropdown. A ticket
# opened, the reply carried a reference and no question mark, and the last thing
# the resident saw was a widget. Someone who declined a ticket got the same
# widget after the closing line. It was also byte-identical every time, which is
# the one thing the prompt forbids the model from doing — the rule that a
# sentence already sent is never sent again exists because a repeat is how you
# know you are talking to a recording, and the workflow was breaking it on the
# model's behalf.
#
# The prompt had been bent around it, too: it used to tell the model NOT to say
# "עוד משהו?" itself, because the workflow would. That paragraph is now
# inverted — the bot closes its own conversations, warmly and in its own words.
#
# The GREETING menu stays. It is a guide for someone who opens with a bare
# "היי" and does not know what the number is for, and it is sent once.


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
    check_greeting(text)
    return text


def check_greeting(prompt):
    """The menu body and the prompt's opener must be the same sentence.

    A bare "היי" never reaches the model: the GREETING regex in the Sort node
    short-circuits and MENU is sent by the workflow. That makes the opener the
    one line living in two places, and on 13 Aug they drifted — the prompt was
    rewritten and MENU was not, so anyone starting with a plain hello got an
    opener the prompt no longer contained, from a workflow that had just been
    deployed and verified. Verifying the system prompt could not have caught it,
    because the system prompt was correct.

    So it is asserted rather than remembered. The prompt carries the opener as a
    worked example, verbatim, which is exactly what makes this checkable: if the
    two stop matching, the deploy stops.
    """
    body = MENU["he"]["body"]["text"]
    if body not in prompt:
        sys.exit(
            "The menu greeting and the prompt's opener have drifted.\n"
            "  MENU  : %s\n"
            "  ...is not in %s\n"
            "A bare greeting is answered by MENU, not by the model, so these two\n"
            "have to be the same sentence. Fix whichever is stale, then re-run."
            % (body, os.path.relpath(PROMPT_DOC, ROOT)))


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
# Deliberately five. The tool webhook answers more, but this slice is inbound
# support only — every tool that MOVES money still goes to a person. Reading a
# balance stopped waiting on PRD §13 #1 on 13 Aug, when the identity method was
# settled (a full name and a phone number, checked in the Edge Function); paying
# has not, and a payment flow behind an identity check built for reading is
# worse than no payment flow. `verify_address` joined 13 Aug: it is read-only,
# returns nothing about any person, and is what lets the bot refuse a building
# we do not manage instead of filing a ticket against it. get_request_status
# joined on
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

def tool(name):
    """One tool definition, by name.

    By name and not by index. These were `TOOLS[0]`, `TOOLS[1]`, `TOOLS[3]`
    until 13 Aug, and inserting `verify_address` into the middle of the list
    silently repointed two nodes at the wrong descriptions — a bug that
    deploys cleanly and shows up as a model that calls the wrong tool.
    """
    for t in TOOLS:
        if t["name"] == name:
            return t
    raise KeyError("no tool named %r" % name)


TOOLS = [
    {
        "name": "open_request",
        "description": (
            "Open a maintenance or service ticket. Call it as soon as you "
            "know WHAT is wrong and WHERE — it verifies the address itself, "
            "inside the same call: a building Homies does not manage opens "
            "nothing, and the response says why (building_found false, with "
            "reason street_unknown / number_not_on_street plus "
            "numbers_we_manage / need_number / need_building / ambiguous plus "
            "candidates) so you can tell the resident and ask again. You do "
            "NOT need verify_address before this — there is no step before "
            "this. When it opens, the response carries the real reference "
            "number, the only source of one: never invent a number, and never "
            "say a ticket exists before this returns a reference."
            # Added 31 Aug: with the prompt stripped, the model answered a
            # menu tap with a four-point numbered form. This is the lever
            # that works -- a tool description, in English, with no Hebrew
            # sentence in it to recite.
            " Collect what is missing the way a person would, in a "
            "sentence, taking the most useful thing first — not as a "
            "numbered list of requirements. A resident who is handed a "
            "four-point form usually answers none of it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "What the resident said is wrong, in Hebrew, in their own words.",
                },
                # The same eleven the voice agents use, and the same eleven
                # migration 014 allows: Homies' own categories, taken off their
                # live service calls. `security` and `structural` were ours and
                # are gone; existing rows carrying them were mapped to `other`
                # and `maintenance` by that migration.
                "type": {
                    "type": "string",
                    "enum": ["plumbing", "electrical", "lighting", "elevator",
                             "cleaning", "gardening", "pest_control",
                             "locksmith", "fire_safety", "maintenance",
                             "other", "complaint"],
                },
                "building": {"type": "string", "description": "Street and number."},
                # Two apartment fields, because there are two facts and they are
                # not the same one. `unit` is where the fault is; a lift and a
                # lobby belong to nobody, so it is empty for them. `reporter_unit`
                # is where the person lives, and is always sent — it is who
                # reported this, and on chat there is no caller ID to tell us.
                #
                # The model does not have to keep both straight: it sends
                # `reporter_unit` plus `fault_location`, and the server decides
                # what `unit` becomes. That is deliberate — the old design had
                # the model express "this is a common-area fault" by OMITTING a
                # field, and an implicit branch is the kind this file has been
                # burned by before.
                "reporter_unit": {
                    "type": "string",
                    "description": "The apartment the person reporting LIVES in. "
                                   "Send this every time, including for a fault "
                                   "in the lobby or the lift.",
                },
                "fault_location": {
                    "type": "string",
                    "enum": ["apartment", "common"],
                    "description": "Where the FAULT is, not where they live. "
                                   "'apartment' for a leak in their kitchen; "
                                   "'common' for a lift, lobby, stairwell, "
                                   "roof, car park, gate or yard.",
                },
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
        "name": "verify_address",
        "description": (
            "Check a building — and an apartment, if there is one — against the "
            "list of buildings Homies actually manages, WITHOUT opening "
            "anything. Use it only when the address itself is the question: a "
            "resident asking whether we manage their building, or grounding a "
            "location during an emergency. It is NOT a step before "
            "open_request — open_request verifies on its own; for tickets call "
            "open_request directly. Pass building exactly as they wrote it; "
            "the whole sentence is fine. Pass unit only for a fault inside a "
            "flat. Returns building_found, the canonical address when the "
            "building is real, and when it is not — why, with the numbers we "
            "do manage on that street so you can offer them."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "building": {"type": "string",
                             "description": "The building as the resident wrote "
                                            "it — street and number, in any "
                                            "phrasing. Required."},
                "unit": {"type": "string",
                         "description": "Apartment number. Only for a fault "
                                        "inside a flat. Omit for common areas."},
            },
            "required": ["building"],
        },
    },
    {
        "name": "get_request_status",
        "description": (
            "Call when the resident asks about an existing service call — its "
            "status, a follow-up, what happened to it. Pass the reference if "
            "they quoted one, in any form (255-1013-26 whole, the old HM-2026-1013, "
            "or just the serial). "
            "Without a reference the building finds them; the apartment only "
            "narrows it. DO NOT ASK FOR AN APARTMENT when the fault is not in "
            "one — a lift, a lobby light, a gate and the bin store belong to the "
            "building, and asking which flat somebody's elevator is in is a "
            "question with no answer. Name the type when they named it. Returns "
            "reference, status (open / in_progress / resolved / cancelled), "
            "dates and description; or `ambiguous_building` with the names when "
            "what they typed fits more than one, and then you ask which rather "
            "than choosing. Read-only; the answer is live from the system."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reference": {"type": "string",
                              "description": "The reference the resident quoted, as written."},
                "building": {"type": "string",
                             "description": "Street and number, if no reference was quoted. "
                                            "A partial name is fine — the match is loose."},
                "unit": {"type": "string",
                         "description": "Apartment number. Leave out for a fault that is "
                                        "not inside a flat."},
                "type": {"type": "string",
                         "enum": ["plumbing", "electrical", "lighting", "elevator",
                                  "cleaning", "gardening", "pest_control", "locksmith",
                                  "fire_safety", "maintenance", "other", "complaint"],
                         "description": "What they named, if they named it — "
                                        "'the elevator' is elevator."},
            },
            "required": [],
        },
    },
    {
        "name": "transfer_to_human",
        "description": (
            # Widened 31 Aug, when the prompt's emergency protocol was deleted
            # with the rest of the scripting. Measured before the change: zero
            # transfers in six runs for somebody shut in a lift or reporting
            # gas. The owner's call was to put it here rather than back in the
            # prompt, which is also the safer home for it — tool descriptions
            # are English and the bot writes Hebrew, so there is no sentence in
            # here for it to recite.
            "Hand this conversation to a person. CALL THIS BEFORE the reply "
            "that tells them their message is going to somebody — that "
            "sentence must never be written without this call behind it, "
            "because it is a promise made to somebody who may be in danger.\n"
            # Rewritten 1 Sep. The old wording said "before your reply, never
            # after", which the model read as "on every reply", so a four-turn
            # fire conversation called it four times and announced the same
            # handover four times, once saying it was transferring them again.
            "You only hand a conversation over once. After that call the "
            "handover exists and stays true: do not call this again in the "
            "same conversation, and do not tell them a second time. Later "
            "messages are for what is actually new.\n"
            "Call it whenever money, debt, payment details or receipts come "
            "up; when the resident asks for a person, or is angry; and "
            "whenever you are simply not sure — being unsure is reason enough "
            "on its own.\n"
            "And call it for a PERSON in a bad state, as opposed to a thing "
            "that broke: somebody shut in a lift, on a roof, in a stairwell "
            "or a car park; somebody hurt, alone, frightened or panicking; "
            "anybody reporting gas, fire, flooding, or water near "
            "electricity. A burst pipe is a ticket. A person who cannot get "
            "out is this, and it happens first — before you ask where they "
            "live, before anything else. If a message contains both, this one "
            "wins.\n"
            # The owner's correction, 31 Aug: they are department
            # representatives, not "a human representative". Put here rather
            # than in the prompt because a bullet in the prompt's facts list
            # did not displace the model's default — the tool description is
            # what it reads at the moment it decides to hand over. The Hebrew
            # term is given because that is the word it has to produce.
            "Whoever picks it up is one of Homies' department "
            "representatives. In Hebrew that is נציג מחלקה, or simply הצוות — "
            "use one of those when you tell the resident where their message "
            "went. Routing to a particular department does not exist yet, so "
            "never say which department it went to.\n"
            # Added 1 Sep: on a four-turn gas-then-fire conversation this was
            # called on every turn, and the bot announced the same handover
            # four times -- once even saying it was transferring them "again".
            "Call it again only if something genuinely new appears that the "
            "first handover did not cover."
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
    {
        "name": "get_balance",
        "description": (
            "Call when the resident asks about their balance, their debt, or "
            "how much they owe — including a tap on the balance row of the "
            "options list. IDENTITY FIRST: this needs the resident's full name "
            "AND their phone number, both typed by them in this conversation. "
            "Do not call it without both, do not use the number they are "
            "messaging from, and never fill either from a guess. If they have "
            "not given both yet, ask — one message, both facts. Returns the "
            "resident's name, apartment, total owed and the unpaid months, or "
            "`identity_failed` when the name and the number do not belong to "
            "the same resident. Read-only — it cannot take a payment; anyone "
            "who wants to actually pay, needs a receipt or disputes an amount "
            "goes to the team."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string",
                         "description": "The resident's full name, as they typed "
                                        "it. First name and surname, both."},
                "phone": {"type": "string",
                          "description": "The phone number as they typed it, "
                                         "digits and all. Not the number the "
                                         "message arrived from."},
                "unit": {"type": "string",
                         "description": "Apartment number, only when they asked "
                                        "about one specific apartment."},
            },
            "required": ["name", "phone"],
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
// There is one. Hebrew.
//
// The history, because this field looks vestigial and is not: language was the
// model's job until 8 Aug and it did not hold (an English row tapped, the Hebrew
// handover line back anyway, twice, from a real handset), so it moved into code
// as a per-phone preference with script detection. Script detection then kept
// firing on things that are not a language — a resident quoting HM-2026-1013 at
// a Hebrew conversation got answered in English — so on 12 Aug it was removed
// and Hebrew became the default with an explicit request as the only way out.
// Later the same day the request was to remove English entirely, so the way out
// went too.
//
// `lang` stays as a constant because it is written on every `messages` row and
// the dashboard reads it. One value today; the column does not have to change
// if a second language ever comes back.
const lang = 'he';

// --- Has this handset already been spoken to? ------------------------------
// The menu, the two tap lines and the switch line are all sent WITHOUT the
// model, so none of them are in the agent's memory. On 12 Aug that produced
// exactly the fault the prompt forbids: "היי" was answered with the menu, the
// resident wrote what broke, and the agent — looking at what it had every
// reason to read as the first message of the conversation — introduced itself
// a second time. No prompt rule can fix that, because from where the model
// sits it IS the first message. So the fact is carried in on the turn, the
// same way the language is.
store.greeted = store.greeted || {};
const greeted = store.greeted[from] === true;
store.greeted[from] = true;

// --- And WHAT it said, not just that it spoke -------------------------------
// `greeted` above is a flag, and a flag only fixes the case it was written for.
// The same hole was patched again on 25 Aug with `tapped_open`, and found a
// THIRD time on 26 Aug: a resident tapped "מצב קריאה קיימת", was asked for a
// reference number by the canned line below, answered "אין לי", and got
// "אני מבין. על מה אפשר לעזור?" back. The model had no question in front of
// it, so an answer read as an opening, and it opened. TAP_LINE's own comment
// argued this could not happen -- that a reference number says what it is --
// and it is right about the number and wrong about "I don't have one".
//
// So carry the SENTENCE. Every canned line leaves this node through said(),
// which means a line added later is covered by having been said, with nobody
// remembering to add a flag for it.
//
// Half an hour, and spent on the next message: it describes the turn the
// resident is answering, not a standing state. After that the agent's own
// memory holds the thread, because from there on the bot's turns are its own.
store.lastBot = store.lastBot || {};
for (const k in store.lastBot) {
  if (Date.now() - (store.lastBot[k].at || 0) > 60 * 60 * 1000) delete store.lastBot[k];
}
const said = (t) => { store.lastBot[from] = { text: t, at: Date.now() }; return t; };

// Media, location, stickers and reactions get the did-not-understand line
// without touching the model. A voice note is the interesting case and is
// deliberately out of this slice.
if (!text.trim()) {
  // A canned reply — flat `to`/`text`, because it goes to the same Send node
  // the agent feeds and that node reads them at the top level.
  return [{ json: {
    _reply: '', _work: false, _canned: true, _menu: false,
    to: from, lang, text: said(__MEDIA_LINE__[lang]),
    in_text: inText, msg_type: msgType, message_id: id,
  } }];
}

// --- A menu row that starts a flow ------------------------------------------
// 'open' and 'status' get the first question of their flow directly — the tap
// already said what the resident wants, and a model round-trip here produced a
// re-greeting on a real handset. 'human' and 'balance' fall through to the
// agent: 'human' becomes transfer_to_human, 'balance' becomes get_balance.
// The 'open' and 'status' taps were answered here with a canned line until
// 31 Aug, when the owner asked for nothing templated. They fall through to the
// model now, which answers the tap in its own words. The tap is then in the
// conversation memory, so store.tapped is no longer needed to stop the 25 Aug
// re-ask: the model can see for itself that a ticket was already asked for.

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
  // The menu body is what the resident reads, so that is what is remembered.
  // The Send menu node puts it on the wire; this node is where it is chosen.
  said(__MENU__[lang].body.text);
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
//
// Spent on the first message after the tap and then forgotten: it says what
// the resident just did, not a standing state. Half an hour, because somebody
// who taps and answers tomorrow is starting again. Stale entries are swept so
// the map cannot grow without limit.
store.tapped = store.tapped || {};
for (const k in store.tapped) {
  if (Date.now() - (store.tapped[k].at || 0) > 60 * 60 * 1000) delete store.tapped[k];
}
const lastTap = store.tapped[from];
const tappedOpen = !!lastTap && lastTap.kind === 'open'
  && (Date.now() - lastTap.at) < 30 * 60 * 1000;
if (lastTap) delete store.tapped[from];

// The line the resident is answering, when the workflow is what said it.
// Same half hour as the tap, and spent the same way.
const prevBot = store.lastBot[from];
const lastBot = prevBot && (Date.now() - prevBot.at) < 30 * 60 * 1000 ? prevBot.text : '';
delete store.lastBot[from];

// Always false on this branch -- a bare greeting returned the menu above and
// never reaches the model here -- but the field has to exist, because the
// "Reply usable?" guard reads it and an undefined there would make a one-word
// reply unjudgeable rather than merely wrong.
return [{ json: { _reply: '', _work: true, _canned: false, _menu: false,
                  to: from, text, tapped, lang, greeted, message_id: id,
                  tapped_open: tappedOpen, greeting: GREETING.test(bare),
                  last_bot: lastBot,
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

    `get_balance` has a `phone` argument, and it is not that phone. The one this
    docstring means is the sender's, minted into the call id from the envelope
    and untouchable. The argument is a number the resident *typed*, which is
    half of proving who they are — and it is only worth anything because the
    model cannot substitute the envelope one for it.
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
                    # The turn opens with the language directive even now that
                    # there is only one language, because the failure it guards
                    # against is not a choice between two — it is a model
                    # answering an English-looking message in English out of
                    # habit. A resident who writes "ok" gets Hebrew back.
                    #
                    # A directive inside the user turn rather than in the system
                    # prompt on purpose: the system prompt is constant and this
                    # is not, and a constant instruction is exactly what the
                    # model was already failing to apply against live context.
                    #
                    # `greeted` rides beside it and is a fact the agent cannot
                    # see for itself: Sort knows a menu or a tap line went out
                    # without a model round-trip, and without being told, the
                    # agent introduces itself again on what it reads as message
                    # one.
                    #
                    # THIS LINE OUTRANKS THE SYSTEM PROMPT, and that cut both
                    # ways on 25 Aug. A dashboard edit of 23 Aug had made the
                    # first-message branch say "name, then a polite offer of
                    # help, and THEN address the body" -- so a balance question
                    # got the whole opener pasted above it, and a mid-thread
                    # "היי" got a full reintroduction, while the system prompt
                    # said the opposite in both places and lost 11 times out of
                    # 11 in the probe fan-out. Whatever the first message must
                    # do, it is said HERE, in one sentence per branch, and the
                    # prompt agrees with it rather than the other way round.
                    # Mirrors the live node exactly; see prompt.md.
                    #
                    # NO DASH IN HERE EITHER (25 Aug). This string is
                    # appended to EVERY resident message, so six em
                    # dashes sat beside every turn the model ever saw
                    # -- a stronger example than any rule in the system
                    # prompt, and the reason the prompt cleanup alone
                    # would not have held. Colons and full stops carry
                    # the same meaning; the branches are unchanged.
                    "text": "={{ '[ענה על ההודעה הזאת בעברית, תמיד, גם אם"
                            " ההודעה באנגלית.]'"
                            " + ($json.greeted"
                            " ? ' [אתם כבר באמצע שיחה. לא מציגים את עצמך שוב"
                            " ולא כותבים \"במה אפשר לעזור\". אם ההודעה היא רק"
                            " ברכה: ברכה קצרה בחזרה וממשיכים מאיפה שהפסקתם."
                            " אם יש בה תוכן: בלי פתיח בכלל, ישר לעניין.]'"
                            " : ' [זו ההודעה הראשונה בשיחה. פתח בשם: היי, כאן"
                            " מיכאל מהומיז. אם ההודעה היא רק ברכה (גם \"מה נשמע\""
                            " ו\"מה המצב\" הן ברכה, לא שאלה. לא עונים עליהן ולא"
                            " מחזירים אותן), הוסף הצעת עזרה אחת: במה אפשר לעזור?"
                            " אם יש בהודעה תוכן, בלי \"במה אפשר לעזור\" בכלל:"
                            " השם, ואז ישר מטפלים במה שנכתב, באותה הודעה.]')"
                            # A tap on "פתיחת קריאת שירות" IS the request, so
                            # the offer would re-ask an answered question. The
                            # model cannot know the tap happened -- the line it
                            # was answered with was canned -- so Sort tells it.
                            " + ($json.tapped_open ? ' [הדייר כבר ביקש לפתוח"
                            " קריאה, וכבר אמרנו לו לספר מה קרה. אל תציע לפתוח"
                            " קריאה, הוא כבר ביקש. אחרי שסיפר, שאל באיזה בניין"
                            " ואיזו דירה גרים.]' : '')"
                            # The turn the resident is answering, when the
                            # workflow said it rather than the model. Stated as
                            # a fact and nothing more: what the sentence means
                            # and what to do about it is the prompt's job, and
                            # the prompt already has a section on every one of
                            # these lines. An instruction here would be a second
                            # prompt nobody reads beside the first.
                            " + ($json.last_bot ? ' [ההודעה הזאת היא תשובה. מה"
                            " שנכתב לדייר לפני כן נשלח על ידי המערכת ולא על ידך,"
                            " ולכן אין לו זכר בזיכרון שלך: ' + $json.last_bot"
                            " + ']' : '')"
                            " + String.fromCharCode(10) + $json.text }}",
                    "options": {"systemMessage": system_prompt()},
                },
                # A model error must not take the workflow down. OpenRouter 402s
                # on every call while the balance is empty, and a resident who
                # gets silence is worse off than one told a person will follow up.
                onError="continueErrorOutput",
                # Absorbs a transient provider blip before it reaches a resident.
                # It does NOT cover the 11 Aug failure — see "Reply usable?",
                # where the generation errored and the node still reported
                # success — but it covers the failures that do throw.
                retryOnFail=True, maxTries=3, waitBetweenTries=5000,
            ),
            node(
                id="model", name="OpenRouter", type="@n8n/n8n-nodes-langchain.lmChatOpenRouter",
                typeVersion=1, position=[960, 420],
                parameters={"model": MODEL, "options": {"maxTokens": MAX_TOKENS,
                                                        "temperature": TEMPERATURE}},
                credentials={"openRouterApi": {"id": e.get("N8N_OPENROUTER_CRED_ID", "").strip(),
                                               "name": "Homies OpenRouter"}},
                retryOnFail=True, maxTries=3, waitBetweenTries=5000,
            ),
            # Keyed on the phone number off the WhatsApp envelope, which is the
            # same rule as everywhere else here: never anything the resident
            # typed. A hardcoded key would cross every resident's conversation
            # into one thread.
            node(
                id="memory", name="Conversation so far",
                type="@n8n/n8n-nodes-langchain.memoryBufferWindow",
                typeVersion=1.3, position=[1200, 420],
                # THE `-2` IS A MEMORY EPOCH, and it is deliberate. Simple
                # Memory lives in the n8n process, not in a table, so there is
                # no way to delete one poisoned conversation: a workflow save
                # does not clear it and neither does a reactivate. On 26 Aug one
                # test handset had four identical
                # "אין לי" → "אני מבין. על מה אפשר לעזור?" pairs sitting in its
                # window, which is a three-shot demonstration of the exact fault
                # being fixed, and it would have argued with the fix. Bumping
                # the suffix abandons every old buffer at once. Bump it again
                # the next time a bad turn has to be forgotten; the cost is that
                # everyone mid-conversation starts fresh, which is cheap.
                # Bumped to -3 on 27 Aug: the test handset's buffer held a full
                # day of elevator test runs, so the model imitated its own old
                # turns (skipping the new ask-what-happened rule) and imported
                # one building's fault details into another building's ticket.
                parameters={"sessionIdType": "customKey",
                            "sessionKey": "={{ $json.to }}-4",
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
                        "description: %s, type: %s, building: %s, reporter_unit: %s,"
                        " fault_location: %s, urgency: %s" % (
                            from_ai("description", tool("open_request")["input_schema"]["properties"]["description"]["description"]),
                            from_ai("type", "One of " + "/".join(tool("open_request")["input_schema"]["properties"]["type"]["enum"])),
                            from_ai("building", "Street and number, as the resident wrote it. The whole sentence is fine; this tool checks it."),
                            # `unit` is deliberately NOT offered to the model.
                            # The server derives it from these two, so there is
                            # no way for the model to pin a lobby leak to a flat
                            # by filling the wrong field.
                            from_ai("reporter_unit",
                                    tool("open_request")["input_schema"]["properties"]["reporter_unit"]["description"]),
                            from_ai("fault_location",
                                    tool("open_request")["input_schema"]["properties"]["fault_location"]["description"]
                                    + " One of apartment/common."),
                            from_ai("urgency", tool("open_request")["input_schema"]["properties"]["urgency"]["description"]
                                    + " One of low/normal/high/emergency."),
                        )),
                    "options": {"timeout": 25000},
                    "descriptionType": "manual",
                    "toolDescription": tool("open_request")["description"],
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
                                tool("transfer_to_human")["input_schema"]["properties"]["reason"]["enum"])),
                    ),
                    "options": {"timeout": 25000},
                    "descriptionType": "manual",
                    "toolDescription": tool("transfer_to_human")["description"],
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
                        "reference: %s, building: %s, unit: %s, type: %s" % (
                            from_ai("reference",
                                    "The reference the resident quoted, exactly as "
                                    "written — 255-1013-26, an old HM-2026-1013, or just the "
                                    "serial. "
                                    "Empty if none was quoted."),
                            from_ai("building", "Street and number, if no reference. "
                                                "A partial name is fine."),
                            # Empty for anything shared. Since 19 Aug the handler
                            # no longer requires it, and requiring it here would
                            # put the unanswerable question back one layer down.
                            from_ai("unit", "Apartment number. Empty for a lift, a lobby "
                                            "light, a gate — anything not inside a flat."),
                            from_ai("type", "One of plumbing/electrical/lighting/elevator/"
                                            "cleaning/gardening/pest_control/locksmith/"
                                            "fire_safety/maintenance/other/complaint, if they named "
                                            "the thing. Empty otherwise."),
                        )),
                    "options": {"timeout": 25000},
                    "descriptionType": "manual",
                    "toolDescription": tool("get_request_status")["description"],
                },
                credentials=({"httpHeaderAuth": {"id": status_cred,
                                                 "name": "Homies tool secret"}}
                             if status_cred else {}),
            ),
            # Same direct-to-Edge-Function route as the status lookup, for the
            # same reason: a balance answer has to be synchronous and live.
            #
            # Both identity fields come from the model, which means they come
            # from what the resident typed — that is the point. The envelope
            # number stopped being an identity on 13 Aug: the function no
            # longer looks at it for a balance, so there is nothing here to
            # take off the Sort item. The check is the function's, not this
            # node's; a model that calls the tool with a blank name gets
            # `need_identity` back and has to go and ask.
            node(
                id="tool_balance", name="get_balance",
                type="n8n-nodes-base.httpRequestTool",
                typeVersion=4.2, position=[2160, 420],
                parameters={
                    "method": "POST",
                    "url": fn_url,
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpHeaderAuth",
                    "sendBody": True, "specifyBody": "json",
                    "jsonBody": TOOL_BODY % (
                        "get_balance",
                        "name: %s, phone: %s, unit: %s" % (
                            from_ai("name",
                                    "The resident's full name exactly as they "
                                    "typed it in this conversation — first name "
                                    "and surname. Required."),
                            from_ai("phone",
                                    "The phone number exactly as they typed it "
                                    "in this conversation. NOT the number the "
                                    "message arrived from. Required."),
                            from_ai("unit",
                                    "Apartment number, only if they asked about "
                                    "one specific apartment. Empty otherwise."),
                        )),
                    "options": {"timeout": 25000},
                    "descriptionType": "manual",
                    "toolDescription": tool("get_balance")["description"],
                },
                credentials=({"httpHeaderAuth": {"id": status_cred,
                                                 "name": "Homies tool secret"}}
                             if status_cred else {}),
            ),
            # Straight at the Edge Function for the third time, and for the
            # same reason as the other two: this is a lookup a resident is
            # waiting on, not a write that can be forwarded async.
            #
            # It reads nothing about any person — buildings and apartment
            # numbers only — so unlike the balance tool it has no identity
            # question to answer. What it does have is a job to do BEFORE
            # open_request, which is the one ordering the prompt has to enforce
            # and this node cannot.
            node(
                id="tool_address", name="verify_address",
                type="n8n-nodes-base.httpRequestTool",
                typeVersion=4.2, position=[2400, 420],
                parameters={
                    "method": "POST",
                    "url": fn_url,
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpHeaderAuth",
                    "sendBody": True, "specifyBody": "json",
                    "jsonBody": TOOL_BODY % (
                        "verify_address",
                        "building: %s, unit: %s" % (
                            from_ai("building",
                                    "The building as the resident wrote it — "
                                    "street and number, any phrasing. The whole "
                                    "sentence is fine. Required."),
                            from_ai("unit",
                                    "Apartment number, only for a fault inside "
                                    "a flat. Empty for a lift, lobby, stairwell "
                                    "or anything in the common areas."),
                        )),
                    "options": {"timeout": 25000},
                    "descriptionType": "manual",
                    "toolDescription": tool("verify_address")["description"],
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
                    # A literal, not an expression: one language, one line. It
                    # picked between two on `lang` until 12 Aug.
                    {"id": "text", "name": "text", "type": "string",
                     "value": HANDOVER_LINE},
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
                    # NO DASH LEAVES THIS WORKFLOW, whoever wrote the sentence.
                    #
                    # The prompt forbids "—" and 220 instances of it were taken
                    # out of the prompt on 25 Aug, because a rule that argues
                    # with its own examples loses. That makes the model unlikely
                    # to type one; this makes it impossible. Every outgoing
                    # message passes through here, canned lines and model
                    # replies alike, so one expression covers all of them. A
                    # comma is the substitution because that is what the dash
                    # was standing in for in every line we had.
                    # AND NEITHER DOES A BRACKET.
                    #
                    # Every instruction the model reads on a turn arrives inside
                    # square brackets: the language line, the mid-conversation
                    # line, the tap line, and since 26 Aug the last_bot line. On
                    # 26 Aug a probe came back
                    # "אוקיי, תודה. [The user said they live in building 12...]"
                    # -- the model's own reasoning, in English, formatted like
                    # the instructions beside it, addressed to nobody and about
                    # to be sent to a resident. Intermittent, so it cannot be
                    # tested away; two more runs of the same turn were clean.
                    # A bracketed span is never something a service agent types,
                    # so it comes off here for the same reason the dash does.
                    "jsonBody": "={{ JSON.stringify({ messaging_product: 'whatsapp',"
                                " to: $('Sort').item.json.to, type: 'text',"
                                " text: { body: String($json.output || $json.text || '')"
                                r".replace(/\[[^\]]*\]/g, ' ')"
                                r".replace(/\s*[—–]\s*/g, ', ')"
                                r".replace(/,\s*,/g, ',').replace(/\s+,/g, ',')"
                                r".replace(/,\s*\./g, '.')"
                                r".replace(/\s{2,}/g, ' ').trim() } }) }}",
                    "options": {"timeout": 20000},
                },
                credentials=({"httpHeaderAuth": {"id": send_cred, "name": SEND_CRED}}
                             if send_cred else {}),
            ),
            # --- The options, again, after a dead-end reply -----------------
            # Chained AFTER Send, which is the only ordering Meta respects: two
            # parallel HTTP calls can arrive swapped, and a menu that lands
            # before the reply reads as changing the subject.
            #
            # The test was a reference number in the reply, and it was too
            # narrow: "אוקיי." to a pasted sentence, and the handover line,
            # are both dead ends and both left the resident staring at a wall
            # — on a real handset, twice, with a prompt rule against it that
            # history outvoted. The deterministic version: a reply that asks a
            # question is mid-flow and gets no menu; a reply that asks nothing
            # has nowhere to go, so the options follow it. This covers the
            # reference replies the old test caught, the bare acknowledgements
            # it missed, and the handover line.
            #
            # Reads the text from whichever node produced it — Hand over
            # instead on the error branch FIRST, because on that branch the
            # agent's main output is empty and .first() on it throws. Canned
            # branches produce neither, evaluate to '', and fail notEmpty —
            # correctly, since every canned line ends with a question anyway.
            # --- Is what the model produced actually a reply? ---------------
            # On 11 Aug a resident asked for their balance, gave their name,
            # and was sent the single word "אני". The tool had worked:
            # get_balance returned ₪9,984 across two months. What failed was the
            # generation *after* it — OpenRouter returned
            # finish_reason "error" with one completion token, and the agent
            # node reported success carrying that one word as its answer.
            #
            # This is why onError and retryOnFail are not enough on their own.
            # Neither fires, because nothing threw. The node succeeded; it
            # succeeded with a fragment.
            #
            # The test is word count, not length. Every reply this agent has any
            # business sending is a sentence — it answers a question or asks
            # one — and the canned one-liners are on other branches entirely. A
            # single word is a broken generation whatever the word is, and
            # "אני" is exactly as long as a legitimate Hebrew word, so length
            # cannot tell them apart.
            #
            # THAT LAST CLAIM WAS FALSE, and cost a resident a service call on
            # 25 Aug. Write הי twice inside a day and the mid-thread rule is to
            # answer with a short greeting and nothing else -- "היי." -- one
            # word, correct, and read here as a broken generation. The rescue
            # fired, opened a ticket, and told them it was with the team. One
            # word is only evidence of failure when the message being answered
            # asked for more than one, so a greeting is exempt. Empty still
            # fails, and a one-word answer to anything else still fails.
            #
            # Failing this sends the handover line instead, which is the honest
            # answer: we could not produce one, and a person will follow up.
            node(
                id="usable", name="Reply usable?", type="n8n-nodes-base.if",
                typeVersion=2, position=[1200, 60],
                parameters={"conditions": {
                    "options": {"caseSensitive": True, "leftValue": "",
                                "typeValidation": "loose"},
                    "conditions": [{
                        "id": "words",
                        "leftValue": "={{ (() => { const w = String($json.output"
                                     r" || '').trim().split(/\s+/).filter(Boolean).length;"
                                     " if (w >= 2) return true;"
                                     " return w === 1 && $('Sort').first().json.greeting === true;"
                                     " })() }}",
                        "rightValue": "",
                        "operator": {"type": "boolean", "operation": "true",
                                     "singleValue": True},
                    }, {
                        # THE PHANTOM TICKET, caught 19 Aug with the run in front
                        # of me. The agent answered an address with "\u05e4\u05ea\u05d7\u05ea\u05d9 \u05e7\u05e8\u05d9\u05d0\u05d4
                        # \u05e2\u05dc \u05e0\u05d6\u05d9\u05dc\u05ea \u05de\u05d9\u05dd \u05d1\u05dc\u05d5\u05d1\u05d9, \u05de\u05e1\u05e4\u05e8 255-1048-26" and the
                        # execution shows one tool call, verify_address. No row
                        # was written, and the number it read out belongs to
                        # somebody else's ticket. The resident is left believing
                        # a request exists, holding a reference that will resolve
                        # to a stranger's fault if they ever quote it.
                        #
                        # Known since 12 Aug as defect 5 and left to the prompt,
                        # which already forbids it and was obeyed on every other
                        # run. A rule the model follows most of the time is not a
                        # guard; this is, because it reads the execution rather
                        # than the intention.
                        #
                        # False sends the reply to "Hand over instead" — the same
                        # branch a degenerate answer takes — so the resident gets
                        # a person instead of a number that is not real.
                        "id": "phantom",
                        "leftValue":
                            # TWO THINGS THIS EXPRESSION HAS TO SURVIVE, both of
                            # which bit on 19 Aug and neither of which is about
                            # the logic:
                            #
                            # 1. `}}` ANYWHERE INSIDE ENDS THE EXPRESSION. n8n
                            #    closes on the first `}}` it meets, so an arrow
                            #    function's `}` next to the closing brace \u2014 the
                            #    natural `}})()` \u2014 truncates the whole thing and
                            #    the node reports "invalid syntax". Every brace
                            #    that would touch another has a space in it.
                            #
                            # 2. The backslashes are SINGLE. Written `\\b` in
                            #    Python source they reach n8n as `\\b`, which in
                            #    a JS regex is a literal backslash followed by b
                            #    \u2014 a valid pattern that matches nothing here. A
                            #    raw string keeps them as the word boundaries
                            #    they are meant to be.
                            r"={{ (() => {"
                            r" const t = String($json.output || '');"
                            # A REFERENCE ALONE IS NOT A CLAIM \u2014 learned live
                            # on 27 Aug. Every status reply quotes a reference
                            # (including OXS's five-digit serials, hence
                            # \d{3,6}), so testing for the number alone made
                            # the guard kill correct status answers and let
                            # the rescue mint junk tickets whose description
                            # is the transcript (255-1130-26, plus two purged
                            # rows from 24 Aug). A claim is the OPENING
                            # language: the exact "X \u05e7\u05e8\u05d9\u05d0\u05d4" phrases, or a
                            # first-person \u05e4\u05ea\u05d7\u05ea\u05d9/\u05e4\u05ea\u05d7\u05e0\u05d5 anywhere near a
                            # reference. "\u05e0\u05e4\u05ea\u05d7\u05d4 \u05d1\u05be26.8" in a status reply
                            # matches neither.
                            " const claims = /\u05e4\u05ea\u05d7\u05ea\u05d9 \u05e7\u05e8\u05d9\u05d0\u05d4|\u05e0\u05e4\u05ea\u05d7\u05d4 \u05e7\u05e8\u05d9\u05d0\u05d4|\u05e4\u05ea\u05d7\u05e0\u05d5 \u05e7\u05e8\u05d9\u05d0\u05d4/.test(t)"
                            r" || ((/\b\d{3}-\d{3,6}-\d{2}\b|\bHM-\d{4}-\d{3,6}\b/.test(t))"
                            " && /\u05e4\u05ea\u05d7\u05ea\u05d9|\u05e4\u05ea\u05d7\u05e0\u05d5/.test(t));"
                            " if (!claims) return true;"
                            # `isExecuted` is useless on a tool node: it reported
                            # true on the 19 Aug run where the execution shows
                            # verify_address as the only tool called. It appears
                            # to describe the node being reachable rather than
                            # having been invoked. The node's OUTPUT is the
                            # honest signal - a tool the agent never called has
                            # produced no items, and asking for them throws.
                            " try {"
                            "  const r = $('open_request').all();"
                            "  return Array.isArray(r) && r.length > 0;"
                            " } catch (e) { return false; }"
                            " } )() }}",
                        "rightValue": "",
                        "operator": {"type": "boolean", "operation": "true",
                                     "singleValue": True},
                    }],
                    "combinator": "and",
                }},
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
            #
            # main[0] no longer goes straight to Send: a generation can fail
            # without throwing, so the answer is checked before it is sent.
            "Answer the resident": {"main": [
                [{"node": "Reply usable?", "type": "main", "index": 0}],
                [{"node": "Hand over instead", "type": "main", "index": 0}],
            ]},
            # true — a real sentence, send it. false — a fragment, so join the
            # error branch and send the handover line. Both ends already exist;
            # this only decides which one a degenerate reply takes.
            "Reply usable?": {"main": [
                [{"node": "Send", "type": "main", "index": 0},
                 {"node": "Log reply", "type": "main", "index": 0}],
                [{"node": "Hand over instead", "type": "main", "index": 0}],
            ]},
            "Hand over instead": {"main": [[
                {"node": "Send", "type": "main", "index": 0},
                {"node": "Log reply", "type": "main", "index": 0}]]},
            # `Send` is a leaf. It used to feed "Dead end reply?", which asked
            # whether the outgoing reply contained a question mark and sent the
            # options list after every reply that did not — so a ticket number
            # was always followed by a dropdown. Removed 31 Aug; the bot closes
            # its own conversations now. See the FOLLOW-UP MENU note at the top.
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
            "get_balance": {"ai_tool": [[
                {"node": "Answer the resident", "type": "ai_tool", "index": 0}]]},
            "verify_address": {"ai_tool": [[
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
    # temperature is printed because the last time it went missing nobody saw.
    print("model    : %s via OpenRouter  effort=%s  max_tokens=%d  temp=%s"
          % (MODEL, EFFORT, MAX_TOKENS, TEMPERATURE))
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
        # A PUT IS A REPLACE, AND THIS SCRIPT IS BEHIND THE LIVE WORKFLOW.
        #
        # Since the Chatwoot cutover on 21 Aug the live workflow has carried
        # eight nodes this file does not build -- the human handback (Human
        # replied?, Assign to the replier, Carry the reply, Show it in Open,
        # Open it anyway) and the promise backstop (Promised a transfer, made
        # none?, Transfer it anyway, The promise backstop) -- plus a Sort node
        # that parses Chatwoot's envelope rather than Meta's, all applied
        # through the REST API and never brought back here. On 24 Aug an
        # --apply to change one greeting would have deleted all of it, and was
        # caught only because the dry run prints the node list. So it is
        # refused here, by name, until either the script catches up or the
        # caller says --force and means it.
        live = api("GET", "/api/v1/workflows/%s" % existing["id"])
        ours = {n["name"] for n in wf["nodes"]}
        extra = [n["name"] for n in live["nodes"] if n["name"] not in ours]
        if extra and "--force" not in sys.argv:
            sys.exit(
                "\nREFUSING TO PUSH. The live workflow has %d node(s) this script "
                "does not build, and a PUT would delete them:\n%s\n\n"
                "Bring the script up to date first, or pass --force to replace "
                "the live workflow anyway. A backup of the live one as of 24 Aug "
                "is in docs/handover/n8n-whatsapp-live-24aug-before-intro.json."
                % (len(extra), "".join("  - %s\n" % n for n in extra)))
        api("PUT", "/api/v1/workflows/%s" % existing["id"], wf)
        wid = existing["id"]
        print("\nupdated %s" % wid)
    else:
        wid = api("POST", "/api/v1/workflows", wf)["id"]
        print("\ncreated %s" % wid)
    print("%s/workflow/%s" % (base, wid))

    # Read the state back rather than asserting one. This printed "Not active
    # yet. Run with --activate" unconditionally, including after updating a
    # workflow that was already live and stayed live — which on 13 Aug read as
    # "the deploy just took the bot down" and cost a scare and a round of
    # checking. A PUT does not deactivate anything; the line was simply never
    # true on the update path.
    state = api("GET", "/api/v1/workflows/%s" % wid)
    if state.get("active"):
        print("\nActive. The change is live now — n8n reloads the workflow on save.")
    else:
        print("\nNot active. Run with --activate, then add the callback URL in Meta.")


if __name__ == "__main__":
    main()
