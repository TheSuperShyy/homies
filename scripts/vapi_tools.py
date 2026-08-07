"""What each assistant is allowed to do, as Vapi function definitions.

Two lists: DEBT_TOOLS (eight, outbound) and INTAKE_TOOLS (three, inbound). They
share one webhook and one `open_request`, which is the reason they share a file.

Kept beside vapi_sync.py rather than inside it because these are a contract with
three other places at once — the TOOLS section of
docs/features/10-debt-followup/prompt.md, the tool table in feature.md, and the
handlers in supabase/functions/debt-tools/index.ts. When one changes all four
have to, and that is easier to see when this is its own file.

WHAT IS DELIBERATELY ABSENT FROM EVERY PARAMETER LIST
No tool takes an amount, a month, a charge id or a resident id. Those come from
the variableValues attached to the call, which the model can read but cannot
change. If a parameter for the amount existed, a model that misheard — or a
resident who insisted the figure was different — could write the wrong number
into a payment ticket. There is no such parameter, so it cannot.
"""


def _fn(name, description, properties=None, required=None, wait=False):
    """wait=True means the agent needs the answer before it can speak.

    Only two tools do. `open_request` hands back a real reference that gets read
    aloud, and the agent is forbidden from inventing one. `send_payment_link`
    can refuse — no amount on the call, a link already sent — and the agent must
    not tell a resident a link is coming when nothing was requested.

    Everything else is a write nobody is waiting on, and marking those `async`
    is what makes a slow tool host survivable. Measured on Apps Script: a cold
    call takes 13 SECONDS and sometimes 404s, warm about 2. A 4 Aug test call
    died exactly there — the agent said "this will just take a sec", then "sorry,
    a few more seconds", twice, then gave up and hung up on the resident. Vapi
    fires an async tool and moves on, so that silence disappears for six of the
    eight and the write still lands.
    """
    tool = {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "required": required or [],
            },
        },
    }
    if not wait:
        tool["async"] = True
    return tool


POSTURE = {
    "type": "string",
    "enum": ["open", "friction", "hot"],
    "description": "The highest posture the call reached, not the current one. Hot is a floor.",
}

TRANSFER_REASONS = ["hardship", "dispute", "distress", "language", "not_understood", "caller_request"]

# Where the request happened. Present on the inbound tool and absent from the
# outbound one, and the asymmetry is the point.
#
# On an outbound call the building and the apartment are already known — they
# ride on the call as variableValues, which the model can read and cannot
# change. Giving it parameters for them would hand it a way to overwrite a fact
# it was given, which is the same mistake as a parameter for the amount.
#
# On an inbound call nothing is known. There is no caller ID on a web call and
# no lookup behind it, so the only source for either field is what the caller
# just said. The webhook resolves this the same way round: variableValues win
# when they exist, and these fill the gap when they do not.
LOCATION = {
    "building": {
        "type": "string",
        "description": "Building name or street address, as the caller gave it.",
    },
    "unit": {
        "type": "string",
        "description": "Apartment number, digits only. Leave out rather than guess.",
    },
}


def _open_request(location):
    """The one tool both assistants carry, differing only in LOCATION.

    Written once because it writes one row into one tab. Two definitions of a
    tool the same webhook serves is how the two ends stop agreeing, and nothing
    would report it — the agent would simply read out a reference for a row with
    an empty building.
    """
    props = {
        "description": {
            "type": "string",
            "description": "What is wrong, in Hebrew, in their words where possible.",
        },
        "type": {
            "type": "string",
            "enum": ["plumbing", "electrical", "cleaning", "other"],
        },
        "urgency": {
            "type": "string",
            "enum": ["low", "normal", "high", "emergency"],
        },
    }
    if location:
        props.update(LOCATION)
    return _fn(
        "open_request",
        "Call when the resident raises a maintenance issue during the call. Wait for "
        "the reference this returns before telling them a request was opened.",
        props,
        ["description"],
        wait=True,
    )


DEBT_TOOLS = [
    _fn(
        "send_payment_link",
        "Call when the resident has agreed to settle. OXS sends them a payment link for "
        "the amount on this call; nothing is charged and no card is involved. Do not "
        "call it before they have agreed, and do not call it twice on one call.",
        # No parameters, deliberately. It had an optional `note` and on 5 Aug the
        # model SPOKE IT: the resident heard "Note," and then, as a separate
        # utterance, "resident asked how to proceed and was sent the payment link
        # after agreeing to settle." Tool arguments leaking into the voice channel
        # is a recurring failure on this stack — gpt-5.4-mini did it with harmony
        # syntax on 4 Aug — and a free-text field is the easiest thing for it to
        # leak. Everything this tool needs is on the call already, so there is
        # nothing to pass and nothing to say out loud.
        None,
        None,
        # Sync, again. It was briefly async because Apps Script took 13 seconds
        # and its 404s made the model retry three times on one call — 82,018
        # prompt tokens, three stalls. n8n answers in ~700ms with no cold start,
        # so waiting is affordable and the refusal is worth having: a call with
        # no amount gets told so, instead of the resident being promised a ticket
        # that was never valid.
        #
        # Worth being precise about what this does and does not guarantee. The
        # workflow answers from its Code node *before* touching the sheet, so a
        # sync response confirms the decision, not the row. Validation is real;
        # durability is not. Only a datastore in the request path would give that,
        # and that is a Supabase argument, not an n8n one.
        #
        # It replaced open_payment_ticket on 4 Aug. That tool took a spoken
        # authorisation to charge a card on file, which made the call recording
        # the authorisation for a payment — with a 14-day retention window and an
        # unanswered consent question sitting under it. A link moves the consent
        # to the moment the resident taps it, and Homies' own system is what
        # sends it.
        wait=True,
    ),
    _fn(
        "log_promise_to_pay",
        "Call when the resident gives a date they will pay by. Never invent or round "
        "the date. If they were vague, leave promised_date out and put what they said "
        "in `said`.",
        {
            "said": {
                "type": "string",
                "description": "Their own words for when they will pay, in Hebrew, as they said it.",
            },
            "promised_date": {
                "type": "string",
                "description": "YYYY-MM-DD, only if they named a date clearly enough to be sure.",
            },
        },
        ["said"],
    ),
    _fn(
        "request_standing_order",
        "Call once per call, only after the resident says yes to a standing order. "
        "Never after a decline. This records the request; it does not set one up.",
    ),
    _fn(
        "log_disputed_payment",
        "Call when the resident says they have already paid. Do not ask when or how. "
        "Do not send anything alongside this.",
    ),
    _open_request(location=False),
    _fn(
        "flag_not_handed_over",
        "Call when the resident says they have no keys, the apartment has not been "
        "handed over, or the handover protocol is unsigned. This stops all future "
        "calls for this apartment and cannot be undone.",
    ),
    _fn(
        "transfer_to_human",
        # 7 Aug: this used to say the call stays open, which is what the debt
        # prompt told the agent to do — say "stay on the line" and wait. There is
        # nothing to wait for. This is a function, not a transferCall, and there
        # is no destination configured anywhere; the resident got twenty seconds
        # of silence and then a dropped line. The intake twin has said the honest
        # thing since it was written and this now matches it.
        "Call after telling the resident a representative will get back to them, never "
        "before and never on its own. This hands the call to the office in writing; it "
        "does not connect anyone to anyone, so do not say you are putting them through "
        "and never ask them to hold. Close the call after calling it.",
        {
            "reason": {"type": "string", "enum": TRANSFER_REASONS},
            "posture_reached": POSTURE,
        },
        ["reason"],
    ),
    _fn(
        "log_call_outcome",
        "Call at the end of every single call without exception, including voicemail, "
        "wrong party and no answer. Include the highest posture the call reached.",
        {
            "outcome": {
                "type": "string",
                "enum": [
                    "authorized", "promised", "disputed", "refused", "transferred",
                    "voicemail", "wrong_party", "not_handed_over", "no_answer",
                    "office_to_contact",
                ],
            },
            "posture_reached": POSTURE,
            "transfer_reason": {"type": "string", "enum": TRANSFER_REASONS},
        },
        ["outcome"],
    ),
]


# The inbound agent's transfer reasons, which are not the outbound ones. Nothing
# inbound is about money, so hardship, dispute and distress have no meaning here;
# out_of_scope and emergency have no meaning outbound. `language` and
# `caller_request` are the only two that belong to both.
#
# The n8n and Apps Script routers validate against a single combined list, so an
# unknown reason silently becomes `caller_request` — which is why these strings
# have to be added there as well as here. A reason that fails validation does not
# error; it just quietly records the wrong thing forever.
INTAKE_TRANSFER_REASONS = [
    "out_of_scope", "emergency", "caller_request", "repeated_failure", "language",
]

# Three tools, all writes.
#
# WHAT IS DELIBERATELY ABSENT: `identify_resident` and `get_request_status`.
# Both are reads, and this project has no read path — the n8n handler is a stub
# that returns "lookup not implemented", and the Apps Script one matches on a
# phone number, which a web call does not have. An agent carrying a lookup tool
# that cannot look anything up is worse than one carrying none: it offers, the
# caller accepts, and the answer is invented. So the tools are absent and the
# prompt no longer offers either. Both come back with the database, not before.
INTAKE_TOOLS = [
    _open_request(location=True),
    _fn(
        "save_partial_request",
        "Call when the call is going to end without a complete request — the line is "
        "too noisy to continue, or the caller is running out of time. Send whatever you "
        "did capture, however little. A call that produces nothing is the one outcome "
        "that is not allowed.",
        {
            "description": {
                "type": "string",
                "description": "Whatever was understood, in Hebrew. Partial is fine; empty is fine.",
            },
            "reason": {
                "type": "string",
                "enum": ["audio", "time_limit", "caller_left"],
            },
            **LOCATION,
        },
        ["reason"],
        # Async, and it matters here more than anywhere. This fires at the moment
        # a call is already failing — bad line, or seconds left on the clock —
        # and making the agent wait for a write would spend the little time left
        # on silence. The row lands either way.
    ),
    _fn(
        "transfer_to_human",
        "Call after telling the caller a representative will get back to them, never "
        "before and never on its own. This hands the call to the office in writing; it "
        "does not connect anyone to anyone, so do not say you are putting them through. "
        "Close the call after calling it.",
        {"reason": {"type": "string", "enum": INTAKE_TRANSFER_REASONS}},
        ["reason"],
    ),
]


def with_server(tools, url, secret, mode="header"):
    """Point every tool at whichever host is standing up the webhooks.

    mode="header" — Supabase Edge Function. The secret is a request header,
    where it belongs.

    mode="query" — Apps Script. It cannot read custom request headers at all, so
    the secret has to ride in the URL, where it is written to logs on every
    request. That is tolerable for ten fictional residents and for nothing else:
    the moment a real Homies row exists, the secret is regenerated AND the data
    moves to Supabase. Those are the same moment, not two chores.
    """
    out = []
    for t in tools:
        t = dict(t)
        if mode == "query":
            joiner = "&" if "?" in url else "?"
            t["server"] = {"url": "%s%skey=%s" % (url, joiner, secret)}
        else:
            t["server"] = {"url": url, "headers": {"x-homies-secret": secret}}
        out.append(t)
    return out
