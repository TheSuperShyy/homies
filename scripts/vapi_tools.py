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

`unit` IS THE ONE EXCEPTION, AND IT IS NOT ONE (added 11 Aug, feature 14)
A call now covers every apartment a resident owes on, so a write has to be able
to mean one of them. The agent passes an apartment NUMBER — a thing the resident
said out loud — and the webhook maps it to a charge id against the list attached
to the call, refusing anything absent from it. So the agent still supplies no
identifier and can still reach no debt it was not handed. It selects; it does
not supply.
"""


def _fn(name, description, properties=None, required=None, wait=False, waiting=None):
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

    # `waiting` is what Vapi SAYS when the call starts, in place of whatever the
    # model would have improvised.
    #
    # Only sync tools get one, because only a sync tool has a gap to fill. The
    # prompt used to carry this job — "while a tool runs, say רגע, אני רושם" —
    # and the model ignored it twice on 19 Aug in favour of "this will just take
    # a sec", a sentence about the machine and how long it needs said to somebody
    # waiting to hear whether their problem was written down. The instruction was
    # tightened after the first time and the second happened anyway.
    #
    # A line the model is told to say is a suggestion; a request-start message is
    # spoken by Vapi and the model never gets the turn. That is the difference,
    # and it is why the prompt now tells the agent to stay QUIET here rather than
    # what to say — two sources for one line would be heard as a stutter.
    #
    # The string is Hebrew because the Hebrew assistant is the source. The
    # English twin translates it in vapi_en.py, alongside every other spoken
    # line; a tool message left untranslated is the one place Hebrew could reach
    # an English caller's ear, since the twins share their tools verbatim.
    if waiting:
        tool["messages"] = [{"type": "request-start", "content": waiting}]
    return tool


POSTURE = {
    "type": "string",
    "enum": ["open", "friction", "hot"],
    "description": "The highest posture the call reached, not the current one. Hot is a floor.",
}

TRANSFER_REASONS = [
    "hardship", "dispute", "distress", "language", "not_understood", "caller_request",
    # 11 Aug. "That flat is not mine", "I have no keys", "the protocol was never
    # signed" — one shape, and the one that replaced flag_not_handed_over. The
    # agent does not act on the claim; the apartment is paused and a person
    # checks it. It is the only reason that changes anything besides the record,
    # which is why it is a reason and not a separate tool.
    "ownership",
]

# The apartment a write is about, on a call that covers more than one.
#
# Left out means the whole call, which is the common case — 117 of the 119
# residents with arrears hold one flat — so the agent reaches the right
# behaviour by saying nothing. It is never required and never guessed: an
# apartment that is not on the call is refused by the webhook rather than
# widened back to everything, because a mishearing on "I paid for four" must not
# dispute a flat the resident never mentioned.
UNIT_ON_CALL = {
    "unit": {
        "type": "string",
        "description": (
            "Apartment number, digits only, only if the resident named ONE apartment "
            "for this. Leave it out for the whole balance. Never guess it."
        ),
    },
}

# Where the request happened. The inbound tool takes both; the outbound one takes
# the apartment only and never the building, and the asymmetry is the point.
#
# On an outbound call the BUILDING is always known — it rides on the call as a
# variableValue, which the model can read and cannot change. Giving it a
# parameter would hand it a way to overwrite a fact it was given, which is the
# same mistake as a parameter for the amount. That has not changed.
#
# The apartment stopped being always-known on 11 Aug. A call covering several
# flats sends `unit` empty because no single value is true, so the outbound tool
# takes one — checked against the apartments on the call, ctx winning wherever it
# is present, so the single-apartment call behaves exactly as it did.
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
        # HOMIES' OWN CATEGORIES, not ours. Until 12 Aug this was four invented
        # values and the WhatsApp bot declared a different seven, so the same
        # fault was filed under two vocabularies depending on the channel.
        # These eleven are what their dispatchers actually use, read off their
        # live service calls, and migration 014 constrains the column to them.
        "type": {
            "type": "string",
            "enum": ["plumbing", "electrical", "lighting", "elevator",
                     "cleaning", "gardening", "pest_control", "locksmith",
                     "fire_safety", "maintenance", "other", "complaint"],
        },
        "urgency": {
            "type": "string",
            "enum": ["low", "normal", "high", "emergency"],
        },
    }
    if location == "full":
        props.update(LOCATION)
    elif location == "unit":
        # Outbound, since feature 14. The building is still a fact on the call
        # and stays absent, but a call covering several apartments sends `unit`
        # empty on purpose — no single value is true — so a leak reported by a
        # two-flat owner has no apartment on it unless the agent can pass what
        # they said. The webhook only accepts an apartment already on the call,
        # and drops anything else to empty rather than sending a technician to a
        # guessed address.
        props["unit"] = LOCATION["unit"]
    return _fn(
        "open_request",
        "Call when the resident raises a maintenance issue during the call, asks "
        "outright for a request to be opened, or accepts the offer of one. Wait for "
        "the reference this returns before telling them a request was opened. Say "
        "nothing while it runs — the waiting line is spoken for you.",
        props,
        ["description"],
        wait=True,
        waiting="רגע, אני רושם.",
    )


DEBT_TOOLS = [
    _fn(
        "send_payment_link",
        "Call when the resident has agreed to settle. OXS sends them a payment link for "
        "the amount on this call; nothing is charged and no card is involved. Do not "
        "call it before they have agreed, and do not call it twice on one call.",
        # `unit` and nothing else. It had an optional `note` and on 5 Aug the
        # model SPOKE IT: the resident heard "Note," and then, as a separate
        # utterance, "resident asked how to proceed and was sent the payment link
        # after agreeing to settle." Tool arguments leaking into the voice channel
        # is a recurring failure on this stack — gpt-5.4-mini did it with harmony
        # syntax on 4 Aug — and a FREE-TEXT field is the easiest thing for it to
        # leak. That is the specific risk, and it is why `note` is still gone.
        #
        # An apartment number is the opposite kind of field: a digit or two, from
        # a fixed list, which the agent has already said out loud in this call.
        # Leaked, it costs one stray "four" in a sentence. Absent, a resident who
        # agrees to clear one flat and not the other gets a link for both, which
        # is a link they did not ask for about money they are disputing.
        dict(UNIT_ON_CALL),
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
            **UNIT_ON_CALL,
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
        "Do not send anything alongside this. If they named one apartment, pass it as "
        "`unit` so only that apartment is disputed.",
        dict(UNIT_ON_CALL),
    ),
    _open_request(location="unit"),
    # `flag_not_handed_over` was here until 11 Aug and is retired, the same way
    # open_payment_ticket was on 4 Aug and for the same reason: a tool the agent
    # should not be deciding to use is a tool it should not be offered.
    #
    # It set residents.handed_over = false and waived the charge on an unverified
    # verbal claim made to an automated caller. That made "this flat was never
    # mine" the sentence that ends any call about money. It was also on the
    # RESIDENT, so flagging one flat stopped calls about every other flat that
    # owner holds — the bug migration 012 fixed for charges, one table over.
    #
    # The path now is `transfer_to_human` with reason `ownership`: the apartment
    # is paused, a person checks it, and nothing about who holds it moves on a
    # phone call. The handler survives in the Edge Function, defanged, so a stale
    # assistant gets an answer rather than an error.
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
        "and never ask them to hold. Close the call after calling it. Use reason "
        "`ownership` when they say an apartment is not theirs or was never handed over "
        "to them, and pass that apartment as `unit`.",
        {
            "reason": {"type": "string", "enum": TRANSFER_REASONS},
            "posture_reached": POSTURE,
            **UNIT_ON_CALL,
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

# Six tools: four writes and two reads.
#
# THE READS ARRIVED LATE, AND THE GAP WAS VISIBLE FROM THE OUTSIDE.
# This list said "three tools, all writes" and explained that `get_request_status`
# was absent because there was no read path — true when it was written. The
# handler landed in the Edge Function on 18 Aug and the prompt gained a whole
# "Status of an existing request" section the same day. This list was not
# touched, and n8n had no route for the name either, so the agent had a section
# telling it how to answer a question and no way to ask one.
#
# What that looks like on a call, 19 Aug: a resident rang to ask where their
# elevator ticket stood. The agent had nothing to look it up with, so it did the
# only thing it could — took the building, took the apartment, and opened them a
# second ticket for the same fault. The caller had to say "I don't want to create
# a ticket" to a system that had already created one.
#
# A prompt that describes a tool the assistant does not carry is worse than a
# missing section: the model will not say "I cannot", it will find the nearest
# tool it does have. So the rule is that these three move together or not at all
# — the handler, the route in n8n, and this list.
#
# `identify_resident` is still absent, and still for the original reason: the
# n8n handler is a stub that returns "lookup not implemented".
INTAKE_TOOLS = [
    _open_request(location="full"),
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
        "add_request_detail",
        "Call after open_request, to add something the caller told you afterwards. One "
        "fact per call, in their words. Use it for the answers to your follow-up "
        "questions — what the item was, where they left it, when they noticed. It adds "
        "to the ticket and never replaces anything already on it.",
        {
            "reference": {
                "type": "string",
                "description": "The reference open_request returned.",
            },
            "detail": {
                "type": "string",
                "description": "The one thing to add, in the caller's own words.",
            },
        },
        ["reference", "detail"],
        # Async, deliberately. The ticket already exists and already has its
        # number read out; the agent is enriching a row, not waiting on one, and
        # a caller who has just answered a question should hear the next one
        # rather than a pause. A failed append costs a line of detail. A pause
        # here costs the same three minutes every other async tool exists to
        # protect.
    ),
    _fn(
        "transfer_to_human",
        "Call after telling the caller a representative will get back to them, never "
        "before and never on its own. This hands the call to the office in writing; it "
        "does not connect anyone to anyone, so do not say you are putting them through. "
        "Close the call after calling it.",
        {
            "reason": {"type": "string", "enum": INTAKE_TRANSFER_REASONS},
            # 20 Aug. These two exist for one case: `reason: emergency` where no
            # request was opened first. The server writes the ticket the agent
            # skipped, and without these it has nothing to write into it — a row
            # saying only "an emergency happened somewhere" is barely better
            # than the nothing it replaces.
            #
            # Optional in the schema and mandatory in the prompt, on purpose. A
            # required field the model cannot fill is a tool call that never
            # happens, and a transfer that does not happen is worse than a
            # transfer with a thin description.
            "description": {
                "type": "string",
                "description": (
                    "What was reported, in the caller's own words. Required when "
                    "reason is `emergency`; leave out otherwise."
                ),
            },
            "building": {
                "type": "string",
                "description": (
                    "The building, if one was given. Only read when reason is "
                    "`emergency` and no request was opened."
                ),
            },
        },
        ["reason"],
    ),
    _fn(
        "get_request_status",
        "Call when the caller asks what is happening with a request they already made. "
        "Never open a new one to answer this. Pass the reference exactly as they said "
        "it — whole, or just the digits — and the lookup is forgiving. With no "
        "reference, the building and apartment find their recent requests. What comes "
        "back is everything you know: it does not say when a technician will come or "
        "who is handling it.",
        {
            "reference": {
                "type": "string",
                "description": "As the caller said it. Any form. Leave out if they have none.",
            },
            # The apartment is OPTIONAL here and that is the point: a lift, a
            # lobby light or a gate is not in a flat. Building alone is a
            # complete question when the fault is a shared one.
            **LOCATION,
            "type": {
                "type": "string",
                "enum": ["plumbing", "electrical", "lighting", "elevator",
                         "cleaning", "gardening", "pest_control", "locksmith",
                         "fire_safety", "maintenance", "other", "complaint"],
                "description": "What the caller named, if they named it — 'the elevator' is elevator.",
            },
        },
        [],
        # Sync. The agent is about to say a status out loud and is forbidden from
        # stating one it did not just get back, so there is nothing for it to do
        # while this runs. Same reason open_request waits.
        wait=True,
        # Checking, not writing — the caller asked a question and nothing is
        # being recorded, so a line about writing would be a small lie.
        waiting="רגע, אני בודק.",
    ),
    _fn(
        "get_balance",
        "Call when the caller asks how much is owed on an apartment, or whether the "
        "building fee is paid. Building and apartment identify them; a full name works "
        "if they offer one. Read the amount as words. You can read a balance and you "
        "cannot touch one — paying, receipts and disputes are a person's job.",
        {
            "name": {
                "type": "string",
                "description": "Full name, only if the caller offered one.",
            },
            **LOCATION,
        },
        [],
        wait=True,
        waiting="רגע, אני בודק.",
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
