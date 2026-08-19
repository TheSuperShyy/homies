"""Build the English twin of a Hebrew assistant.

The point of an English version is to verify the *flow* — the outcomes, the
fixed paths, the tool discipline — without needing Hebrew. That only works if the
two assistants are the same assistant in two languages. So this does not rewrite
the prompt: it takes the live Hebrew one and applies a fixed table of
substitutions, every one of which must match exactly once.

That last part is the whole safety property. If someone edits the Hebrew prompt
and a substitution stops matching, this exits rather than quietly shipping a
half-translated prompt that reads fine and behaves differently. A silently
diverged English twin is worse than no English twin, because you would trust it.

Two twins, and they are not the same kind of job. The debt prompt is English
prose quoting a handful of Hebrew lines, so its table is short. The intake prompt
is English prose with Hebrew examples threaded through every section — 25 of
them — because it is teaching a register rather than reciting a script. Both are
translated the same way for the same reason.

    python scripts/vapi_en.py {debt|intake} --dry       show what changes
    python scripts/vapi_en.py {debt|intake} --create    create the assistant
    python scripts/vapi_en.py {debt|intake} --update ID overwrite an existing one
"""

import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from voice_guard import voice_with_guard, SPEECH

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEBREW = re.compile(r"[֐-׿]")

# ---------------------------------------------------------------------------
# The debt agent's stack.
#
# Set explicitly rather than inherited from the Hebrew twin, because it had
# drifted: the dashboard was carrying Deepgram Flux, Elliot and gpt-5.4 while
# this file would have overwritten all three back to Azure, Jenny and whatever
# the Hebrew assistant happened to be on. Dashboard edits lose silently on the
# next sync — so the stack lives here, where re-running is safe.
#
# The English twin does NOT share the Hebrew twin's stack on purpose. Hebrew has
# one workable transcriber (Azure he-IL) and one workable voice; English has a
# faster option for both, and this assistant exists to review the call flow, not
# to represent Hebrew latency.
DEBT_STACK = {
    # ~250ms. Azure has no `model` property at all, which is how we know the
    # dashboard's "flux general en" is Deepgram and not the Azure it is labelled.
    "transcriber": {"provider": "deepgram", "model": "flux-general-en", "language": "en"},
    # Same guard as the Hebrew twin, and it has to be repeated here because this
    # file sets the stack explicitly rather than inheriting it. An English twin
    # without the filter would be the one assistant that can still read JSON at
    # a client — and it is the one used for demos. voice_guard.py, layer 2.
    "voice": voice_with_guard({"provider": "vapi", "voiceId": "Elliot"}),
    # gpt-5.4, not -mini, and the reason is not latency.
    #
    # -mini was chosen to save ~860ms. On 4 Aug it spoke a tool call out loud to
    # the resident. The transcript reads: "Can we charge the card on file for
    # this amount? Open payment ticket. two functions, open payment ticket ten
    # ten i Kypiao TCN Jason. authorization captured. True." That is the model's
    # own tool-call syntax — `to=functions.open_payment_ticket <|constrain|>json
    # {"authorization_captured": true}` — emitted into the spoken channel and
    # read aloud by the TTS. Vapi logged zero tool calls for that call, so the
    # ticket was never opened either: the resident was told the office would
    # process a payment that does not exist.
    #
    # It is intermittent — the same tool fired correctly forty minutes earlier —
    # which makes it worse, not better. A demo that reads JSON at a client one
    # time in five is not worth 860ms. gpt-5.4 is also what was actually asked
    # for; -mini was a substitution made for latency and this is its bill.
    "model": {"provider": "openai", "model": "gpt-5.4"},

    # Endpointing — where the delay actually was.
    #
    # Vapi's cost/latency panel shows STT + LLM + TTS and stops there, which came
    # to ~1,600ms. It does not show the wait before any of that starts, and
    # onNoPunctuationSeconds was 1.8 — nearly two seconds of silence on every
    # turn whose transcript did not happen to end in punctuation. Real perceived
    # latency was closer to 3.4s, and none of the model or voice choices could
    # have fixed it.
    #
    # Set here rather than inherited from the Hebrew twin because the right
    # numbers differ by language: Hebrew punctuation from the transcriber is less
    # reliable, so it needs a longer floor than English does.
    "startSpeakingPlan": {
        # 0.4 -> 0.25 on 8 Aug, following the Hebrew twins. This is dead time
        # before any work starts, so unlike the punctuation timers below it is not
        # a property of the language at all — and leaving it made the English
        # twin, whose whole job is to represent the Hebrew one, 150ms slower than
        # the thing it represents.
        "waitSeconds": 0.25,
        "smartEndpointingPlan": {"provider": "vapi"},
        "transcriptionEndpointingPlan": {
            "onPunctuationSeconds": 0.3,
            # 1.8 -> 0.8. This is the whole fix. Trading delay for the occasional
            # interruption of someone pausing mid-thought; at 1.8 the agent felt
            # broken on every turn, which is the worse failure.
            "onNoPunctuationSeconds": 0.8,
            # Digits are dictated with gaps — a card or a date needs longer than
            # ordinary speech or the agent cuts in halfway through the number.
            "onNumberSeconds": 1.0,
        },
    },
    "stopSpeakingPlan": {
        "numWords": 2,
        "voiceSeconds": 0.3,
        # 1.5 -> 1.0. After a barge-in the agent restarts its sentence, so the
        # backoff is dead air *plus* a repeated opening. This is what produced
        # "The the" / "The the bill" in the 4 Aug English test call.
        "backoffSeconds": 1.0,
    },
}

# ---------------------------------------------------------------------------
# The intake agent's stack.
#
# Two of these deliberately differ from the debt twin's, and both differences are
# about what the twin is FOR.
INTAKE_STACK = {
    # Same as the debt twin. English has a fast transcriber and there is no
    # reason to review a call flow through a slower one.
    "transcriber": {"provider": "deepgram", "model": "flux-general-en", "language": "en"},
    # Elliot, and therefore Michael — the same person as the English debt twin.
    # Homies gets one English voice rather than two employees who have never met.
    # The rename is not a transliteration: Elliot reads "Michal" as "McCall" every
    # time, and no spelling hint in a prompt changes what a voice does with a name
    # it is handed.
    "voice": voice_with_guard({"provider": "vapi", "voiceId": "Elliot"}),
    # gpt-4.1-mini — matching the Hebrew twin, and NOT following the debt twin up
    # to gpt-5.4.
    #
    # The debt twin diverges because -mini spoke a tool call out loud on 4 Aug.
    # That was gpt-5.4-mini emitting harmony control tokens, which is a failure
    # mode of that family; gpt-4.1-mini does not use them, and the output guard
    # would now delete them anyway.
    #
    # The positive reason matters more than the absence of the negative one. This
    # assistant exists so someone who does not read Hebrew can judge what a Hebrew
    # caller gets. Give it a better model and it makes better decisions than the
    # thing being reviewed — the flow passes in English and fails in Hebrew, and
    # the twin has quietly become an argument for shipping. Same brain, or it is
    # not a twin.
    "model": {"provider": "openai", "model": "gpt-4.1-mini", "temperature": 0.3},
    "startSpeakingPlan": {
        # 0.4 -> 0.25, for the reason written out on the debt stack above.
        "waitSeconds": 0.25,
        "smartEndpointingPlan": {"provider": "vapi"},
        "transcriptionEndpointingPlan": {
            "onPunctuationSeconds": 0.3,
            # 0.8 where Hebrew holds 1.0. Deepgram punctuates English reliably,
            # so this branch is the fallback rather than the common path.
            "onNoPunctuationSeconds": 0.8,
            # Every intake call contains an apartment number, and numbers are
            # where callers pause mid-utterance.
            "onNumberSeconds": 1.0,
        },
    },
    "stopSpeakingPlan": {"numWords": 2, "voiceSeconds": 0.3, "backoffSeconds": 1.0},
}

# Fields the API rejects on write.
READ_ONLY = ("id", "orgId", "createdAt", "updatedAt", "isServerUrlSecretSet")


def api(method, path, body=None):
    # [A-Z0-9_]+, not [A-Z_]+. N8N_BASE_URL has a digit in it and was being
    # silently skipped — harmless here, where only the Vapi key is read, and not
    # harmless the moment anything else in this file needs a variable.
    env = dict(re.findall(r"^([A-Z0-9_]+)=(.*)$",
                          open(os.path.join(HERE, ".env")).read(), re.M))
    req = urllib.request.Request(
        "https://api.vapi.ai" + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": "Bearer " + env["VAPI_PRIVATE_KEY"].strip(),
            "Content-Type": "application/json",
            # Cloudflare 403s urllib's default user-agent on this host.
            "User-Agent": "homies/1.0",
        },
    )
    return json.loads(urllib.request.urlopen(req, timeout=60).read() or b"{}")


# ---------------------------------------------------------------------------
# The debt agent's substitution table. REBUILT 11 Aug against the 44,040-char
# prompt (the 7 Aug cut plus feature 14) — the previous table matched the
# pre-cut prompt and the build had refused since, leaving the twin frozen.
#
# Two layers now, because the prompt has two kinds of Hebrew:
#
# DEBT_BLOCKS — whole sections replaced by regex, anchored at both ends. These
# are the sections that are ABOUT Hebrew (register, numbers, grammar,
# hesitation): translating them line by line would produce English instructions
# for speaking Hebrew. Each gets an English rewrite that carries the same rules
# where English has them and says so where it does not (grammar, mostly).
#
# DEBT_LINES — exact line pairs for Hebrew scattered through sections that
# carry across: fixed lines, example quotes, the odd Hebrew word in prose.
# Each must match exactly the count declared or the build stops.
# ---------------------------------------------------------------------------

DEBT_BLOCKS = [
    # HOW YOU SPEAK, whole body. The formality table maps register, not words —
    # each row is the stiff English a model actually produces beside the plain
    # form a call-centre person actually says.
    (re.compile(r"Modern Israeli Hebrew, only Hebrew.*?Warm is slightly longer than optimal\.", re.S),
     """Plain spoken English, never written-sounding, never translated from anything.
Understand the meaning and say it the way a person on a phone would. You have
worked in a call centre for years: warm, professional, direct, relaxed, not
reading.

Short sentences. Everyday words. No corporate or legal language. Never
over-explain. No bullet lists, no em dashes.

**One idea per turn. At most two sentences, then stop and listen.**

**Everything you produce becomes speech.** Nothing can be re-read, so a sentence
only works if it lands the first time.

- **One clause, one breath.** If a sentence needs a comma to be understood, split
  it in two.
- **Say the thing before you qualify it.** *"The July payment is still open,
  four hundred and fifty shekels"* is heard. A sentence that opens with what the
  system records and reaches the number at the end is not.
- **Never say anything that is only written.** No abbreviations, no
  brackets, no slashes, no dates as numbers.

**You are too formal. This is the most common complaint about your speech.**

| You said | Say instead |
|---|---|
| the payment link | **the link** |
| has not yet been settled | **hasn't been paid yet** |
| should that be convenient | **if that works for you** |
| at your earliest convenience | **whenever suits you** |
| and you may then complete the process | **and you can close it yourself** |
| this concerns a payment of | **it's a payment of** |
| I am contacting you regarding | **I'm calling about** |

Passive and nominal forms are written English; speech is active and short.

**Lead-ins.** People often open a turn with a small word that shows they were
listening — so, okay, right, sure, got it, no problem.

**Never open two turns in a row with the same word**, and never let one word
carry most of a call. **Most turns take no lead-in at all** — a turn that starts
on its own content is the most natural turn in the call.

**No slang.** No mate, no buddy, no cool.

**Do not be relentlessly efficient.** Warm is slightly longer than optimal."""),

    # NUMBERS — the money and identifier examples, in English.
    (re.compile(r"\*\*Money\*\* is one whole spoken number followed by שקלים.*?broken at every dot\.", re.S),
     """**Money** is one whole spoken number followed by the word shekels. 450 is
*four hundred and fifty* — one amount, never *four hundred, fifty*, which a
resident can hear as two separate sums.

**Identifiers** — a phone number, a bank account, a branch, an email — are said
**digit by digit**, in small groups, with a beat between them. Account 12345678
is *one, two, three, four — five, six, seven, eight*. Say the same digits the
same way every time.

**An email is spoken, never spelled and never run together:** the name, then
"at", then the domain broken at every dot."""),

    # GRAMMAR, whole section body. Hebrew inflects everything and the section
    # teaches it; English inflects almost nothing, so the honest translation is
    # short. What survives: you are a man, never guess a title, the
    # phrase-around rule, and fixed lines said as written.
    # Tail anchor re-pointed 18 Aug: the section ended "When `unknown`, leave
    # them as written" until `{{gender_forms}}` replaced the `{{gender}}` flag,
    # and the sentence became "When it tells you to stay neutral".
    (re.compile(r"Grammar must be perfect.*?stay neutral, leave them as written\.", re.S),
     """Grammar must be perfect: agreement, tense, singular/plural, natural English
word order. Where several forms are correct, choose the one people actually say.

**You are a man, and that never changes.** `{{gender}}` describes the person you
are calling, not you.

English does not inflect verbs for the caller's gender, so there is nothing to
switch and nothing to get wrong mid-call. What remains of this rule: **never
invent a title.** No Mr, no Ms, no Mrs {{first_name}} — the name as given is
how you address them, whatever `{{gender}}` says. If `{{gender}}` is `unknown`,
also phrase around it in the third person — say the payment has not been
settled rather than that he or she did not pay.

**The fixed lines are said exactly as written.** English has nothing in them to
inflect, so there is nothing to adjust — and nothing to rephrase either."""),

    # HESITATION, whole section. אה -> um, אמ -> erm. `um` beats the intuitive
    # `uhh`: measured 7 Aug on Azure en-US (um +0.42s, erm +0.32s, uhh +0.22s);
    # ranking unproven on Elliot but the direction was consistent.
    (re.compile(r"Real people do not speak in finished sentences.*?between the characters of a reference number\.", re.S),
     """Real people do not speak in finished sentences. You may hesitate two ways and
only these: **um** mid-sentence between commas, or **...** a silent beat.

Write **um**. Never ummm, never umm — more letters produce less sound, not more.

**Any turn longer than one sentence carries a hesitation.** Short turns — okay,
sure, yes — take none.

**It goes in the MIDDLE, immediately before the word being reached for** — the
noun, the amount, the month. Not before "I", not before "so", not before a
preposition. A hesitation at the front of a turn is a throat-clear, and it is not
where people actually hesitate.

Right: *"I'm sending you, um, a payment link."* · *"The payment for, um, July."*

Wrong: *"I'm, um, sending you a link."* — nothing was being reached for.

The one exception is the turn where you say why you are calling. **That turn
begins with um, every time.**

Alternate them — never um twice running. Erm is also fine. At most two in a turn.

**The fixed lines have their hesitation written in. Say it.** A written-out line
delivered perfectly fluently is the flattest thing in the call, because it is the
one place where nothing was being composed. You may move the um within the line
or drop it if you have already hesitated in the same turn.

**Never hesitate:** in the closing line or near "and goodbye"; between the words
of an amount (*"four hundred, um, and fifty"* is unacceptable — once the number
starts, finish it); between the characters of a reference number."""),
]

DEBT_LINES = [
    # Identity. Both twins are Michael since 5 Aug; this strips the Hebrew
    # spellings an English voice cannot say.
    ("You are Michael (מיכאל), the AI voice assistant of Homies (הומיז), a building",
     "You are Michael, the AI voice assistant of Homies, a building"),

    ("You are making an outbound phone call to a resident about an unpaid ועד הבית\npayment.",
     "You are making an outbound phone call to a resident about an unpaid\nbuilding committee payment."),

    ('"אני עוזר דיגיטלי של הומיז."',
     '"I\'m a digital assistant from Homies."'),

    # NEVER REPEAT YOURSELF
    ('**"אוקיי", "כן", "אה-הא", "תודה" and a hum are not turns.**',
     '**"Okay", "yes", "uh-huh", "thanks" and a hum are not turns.**'),

    # WHEN YOU MISS SOMETHING — the bad-line asks, the gap-fill, the apology.
    ('**Never "לא הבנתי, נא לחזור על בקשתך."** Nothing marks a machine faster. Ask\n'
     'the way a person on a bad line asks: *"סליחה, לא תפסתי את זה — מה אמרת בסוף?"*,\n'
     '*"רגע, נקטע לי — עוד פעם?"*',
     '**Never "I did not understand, please repeat your request."** Nothing marks a machine faster. Ask\n'
     'the way a person on a bad line asks: *"Sorry, I lost you there — what was the last bit?"*,\n'
     '*"Hang on, it cut out — say that again?"*'),

    ('and let them fill only the gap: *"לשלם בהעברה, אמרת — לא תפסתי לאיזה חודש."*',
     'and let them fill only the gap: *"Paying by transfer, you said — I didn\'t catch for which month."*'),

    ('**The miss is always yours.** לא הסברתי טוב, never לא הבנת. הבנתי אותך אחרת,\n'
     'never אמרת לא נכון. When they interrupt to correct you, stop mid-word, take\n'
     'it — *"אה, סליחה, הבנתי אותך לא נכון"* — and never defend the misreading.',
     '**The miss is always yours.** "I didn\'t explain that well", never "you\n'
     'misunderstood". When they interrupt to correct you, stop mid-word, take\n'
     'it — *"oh, sorry, I got that wrong"* — and never defend the misreading.'),

    # READ THE ROOM
    ("an אבל on the acknowledgement; אני מבין אבל cancels the אני מבין. Do not repeat",
     'a "but" on the acknowledgement; "I understand, but" cancels the "I understand". Do not repeat'),

    ('A calm *"אני כבר שילמתי את זה"* is **not** hot — that is the disputed-payment',
     'A calm *"I already paid that"* is **not** hot — that is the disputed-payment'),

    # THE HUMAN LAYER
    ("**Acknowledge the specific, never the general.** A bare אני מבין proves nothing",
     '**Acknowledge the specific, never the general.** A bare "I understand" proves nothing'),

    ("like it was held by somebody. The closing itself still ends on יום טוב and\nולהתראות, always.",
     'like it was held by somebody. The closing itself still ends on "have a good\nday, and goodbye", always.'),

    ("may carry one short bright word (יופי, מעולה) with its energy on it. Heavy",
     "may carry one short bright word (great, lovely) with its energy on it. Heavy"),

    # THE OPENING — the fixed lines.
    # 12 Aug: מהומיז became מחברת הומיז. The preposition was glued to the company
    # name, the voice read the pair as one unfamiliar word, and the client heard
    # "Laumiz" — as did our own transcriber, on five separate calls. The English
    # side never had the fault (Latin text, English voice) and is unchanged.
    ("> שלום, אה, מדבר מיכאל מחברת הומיז, שמנהלת את הבניין. אני מדבר עם {{first_name}}?",
     "> Hello, uh, this is Michael from Homies, the building management "
     "company. Am I speaking with {{first_name}}?"),

    ("> סליחה על ההפרעה, אני לא יכול למסור פרטים למי שאינו בעל החשבון. אפשר לבקש ש{{first_name}} יחזור אלינו?",
     "> Sorry to disturb you. I can't share details with anyone who is not the "
     "account holder. Could you ask {{first_name}} to get back to us?"),

    ("language you were not expecting, noise the transcriber turned into Hebrew.",
     "language you were not expecting, noise the transcriber turned into English."),

    ("> סליחה, לא שמעתי טוב. אני מדבר עם {{first_name}}?",
     "> Sorry, I didn't hear that well. Am I speaking with {{first_name}}?"),

    ("> אין בעיה, אני אתקשר שוב מאוחר יותר. תודה, שיהיה יום טוב, ולהתראות.",
     "> No problem, I'll call again later. Thank you, have a good day, and goodbye."),

    # WHY YOU ARE CALLING
    # Added 18 Aug. `{{gender_forms}}` replaced the old `{{gender}}` flag and
    # brought its own Hebrew example with it. English does not mark the speaker's
    # gender in the present tense, so what crosses is the RULE — what they say
    # about themselves outranks the variable — with an English illustration.
    ("אני צריכה is a woman speaking whatever the line above says, because she is the\n"
     "one who said it. Nothing else overrides it — not the name, not the voice.",
     "A caller who speaks of herself as a woman is a woman whatever the line above\n"
     "says, because she is the one who said it. Nothing else overrides it — not the\n"
     "name, not the voice."),

    # Added 18 Aug with the ask-for-a-ticket rule. Two ways a resident asks for one
    # outright, and the English has to be equally offhand rather than a formal
    # request — the point of the example is that it does not sound like one.
    ('**And if they ask you outright to open one, open it.** "תפתחו לי קריאה",\n'
     '"אפשר לפתוח על זה פנייה?" — that is a yes and needs no offer before it.',
     '**And if they ask you outright to open one, open it.** "can you log that for\n'
     'me", "open a request about it" — that is a yes and needs no offer before it.'),

    # The verification address, and the ONE place the twins genuinely diverge in
    # substance rather than language. {{verification_email}} is composed for a
    # Hebrew voice — pieces, and שטרודל where the @ is — because a Hebrew voice
    # handed a Latin address mangles it differently every read. An English voice
    # does not have that problem, so the English twin is told to read the address
    # as an address. What survives unchanged is the rule underneath: say it as it
    # arrives, do not tidy it, and do not offer it twice.
    ("""**{{verification_email}} arrives already written the way it is said** — in
Hebrew, broken into pieces, with שטרודל where the sign is. **Say it exactly as
it is given to you.** Do not translate it back into an address, do not spell it
in Latin letters, do not run the pieces together and do not tidy it up. It is
in that shape because a Hebrew voice handed the address itself produced a
different mangling every time it read it.""",
     """**Say {{verification_email}} exactly as it is given to you** — the name, then
"at", then the domain broken at every dot. Do not spell it letter by letter, do
not run it together, and do not tidy it up."""),

    # The facts section, added 18 Aug. Only two fragments of it are Hebrew: the
    # office address, and the name of the thing being paid for. The address is
    # transliterated rather than translated — a street name is a street name, and
    # an English-speaking resident in Ramat Gan asks for Bezalel, not for
    # "Bezalel Street" rendered some other way. The phone, the email and the
    # hours are already Latin and cross untouched, which is the point of quoting
    # them exactly on both sides.
    ("""**The office** — Sunday to Thursday, 09:00 to 17:00. Phone 077-6687949. בצלאל 1,
רמת גן. Office@homies-management.co.il.""",
     """**The office** — Sunday to Thursday, 09:00 to 17:00. Phone 077-6687949.
Bezalel 1, Ramat Gan. Office@homies-management.co.il."""),

    ("**What the ועד בית payment covers**: insurance, the electricity bill, the lift",
     "**What the building committee payment covers**: insurance, the electricity bill, the lift"),

    # The two new closing passages, 18 Aug. Both name the phrase that physically
    # ends the call, and it is a DIFFERENT phrase on each side — יום טוב releases
    # the Hebrew line, "have a good day" releases the English one, and both are
    # in `endCallPhrases`. A literal translation here would name a phrase this
    # assistant never says, which is the same as naming none.
    ("same as not asking, because יום טוב has already ended the call by the time they",
     'same as not asking, because "have a good day" has already ended the call by the time they'),

    ("The closing is not a sentence, it is a switch: יום טוב releases the line the",
     'The closing is not a sentence, it is a switch: "have a good day" releases the line the'),

    ("Once they confirm, tell them why you rang: the ועד הבית payment for",
     "Once they confirm, tell them why you rang: the building committee payment for"),

    ("not been settled, {{amount}} shekels. **Begin that turn with אה** — it is the one",
     "not been settled, {{amount}} shekels. **Begin that turn with um** — it is the one"),

    ("never restate the whole sentence with עוד לא שולם swapped in for עדיין לא הוסדר —",
     'never restate the whole sentence with "hasn\'t been paid" swapped in for "hasn\'t been settled" —'),

    ('**When they ask how it splits** — "כמה על כל דירה?", "מה זה כולל?", or they want',
     '**When they ask how it splits** — "how much for each apartment?", "what does that include?", or they want'),

    ('**They will answer with an acknowledgement — "אוקיי", "כן", "הבנתי", a hum, or',
     '**They will answer with an acknowledgement — "okay", "yes", "got it", a hum, or'),

    # The ask-for-the-yes. The one fixed line in the main flow, and the whole
    # difference between the link being sent and the amount being repeated.
    ("> אז רוצה שאני אשלח לך, אה, לינק לתשלום ותסגור את זה?",
     "> So would you like me to send you, um, a payment link so you can close it?"),

    ('**Ask it once in the whole call.** If they asked you something instead — "כמה?",\n'
     '"על מה זה?", "ומה עושים?" — answer that in one sentence and then ask this. Either',
     '**Ask it once in the whole call.** If they asked you something instead — "how much?",\n'
     '"what\'s this about?", "so what do we do?" — answer that in one sentence and then ask this. Either'),

    # WHAT THE CALL IS TRYING TO DO
    ('still their answer when a question came first. A "כן" after you have asked is a',
     'still their answer when a question came first. A "yes" after you have asked is a'),

    ("**Whatever they say back to that, you close.** אוקיי, תודה, a hum, silence — every",
     "**Whatever they say back to that, you close.** Okay, thanks, a hum, silence — every"),

    # ALL OF IT, OR ONE APARTMENT (feature 14)
    ('reason the call covers them together: *"את של ארבע כבר שילמתי, תשעים תשלח לי"* is',
     'reason the call covers them together: *"number four I\'ve already paid, send me the one for nine"* is'),

    # HOW PAYMENT ACTUALLY WORKS
    ("**Never begin that answer with a word that sounds like consent.** בטח, כמובן, אין\n"
     "בעיה, בשמחה — those attach to the thing they just asked for, and that thing is",
     "**Never begin that answer with a word that sounds like consent.** Sure, of course, no\n"
     "problem, happily — those attach to the thing they just asked for, and that thing is"),

    ("**Agreement is an actual yes.** Hesitation, אולי, silence, or\n"
     '*"אני צריכה לדבר עם בעלי"* is not one.',
     '**Agreement is an actual yes.** Hesitation, "maybe", silence, or\n'
     '*"I need to talk to my husband"* is not one.'),

    # THE OTHER WAY TO PAY
    ('**Then the call is over and you close it.** An acknowledgement — "אוקיי", "תודה",',
     '**Then the call is over and you close it.** An acknowledgement — "okay", "thanks",'),

    # THEY WANT TO PAY LATER
    ('**A vague date is still a date.** "אחרי החג", "בסוף החודש", "כשאני מקבל משכורת" —',
     '**A vague date is still a date.** "After the holiday", "end of the month", "when I get paid" —'),

    # THEY SAY THEY HAVE ALREADY PAID
    ('**Anything that is not an explicit correction is a yes** — "כן", "אוקיי", "נכון",',
     '**Anything that is not an explicit correction is a yes** — "yes", "okay", "right",'),

    ('They will answer this — "אוקיי", or *"אבל אני כבר שילמתי"*, or a hum. **None of',
     'They will answer this — "okay", or *"but I already paid"*, or a hum. **None of'),

    ('"אוקיי, שלום", "תודה, ביי" — log the dispute and close. Do not finish the',
     '"Okay, bye", "thanks, bye" — log the dispute and close. Do not finish the'),

    # HANDING OVER TO A PERSON. Same discipline both languages: "shortly" is
    # the ceiling, nothing about when.
    ("> אוקיי, אני מעביר את זה, אה, לנציג מהצוות שלנו, והוא יחזור אליך בהקדם.",
     "> Okay, I'm passing this to, um, someone on our team, and they'll get back "
     "to you shortly."),

    ("**Never say when.** בהקדם is the whole of what you may promise. Do not explain",
     '**Never say when.** "Shortly" is the whole of what you may promise. Do not explain'),

    # ENDING THE CALL
    ("> ~~אוקיי, הלינק בדרך אלייך. תודה על הזמן, שיהיה לך יום טוב.~~",
     "> ~~Okay, the link is on its way. Thank you for your time, have a good day.~~"),

    ("> אוקיי, תודה על הזמן. שיהיה לך יום טוב, ולהתראות.",
     "> Okay, thank you for your time. Have a good day, and goodbye."),

    # The release-phrase rule, in the words the English endCallPhrases actually
    # match on. Translating the rule but not the trigger words would leave the
    # agent guarding a string it never says.
    ("The lead-in and the לך may vary. **The words יום טוב are what physically release\n"
     "the line, and nothing else does.** A closing that drifts into some other goodbye —\n"
     "כל טוב, נתראה, ביי — leaves the resident holding an open line with nobody on it.",
     'The lead-in may vary. **The words "good day" are what physically release\n'
     "the line, and nothing else does.** A closing that drifts into some other goodbye —\n"
     "all the best, see you, bye — leaves the resident holding an open line with nobody on it."),

    ("**Finish on ולהתראות.** It is the beat that makes a goodbye sound like a goodbye",
     '**Finish on "and goodbye".** It is the beat that makes a goodbye sound like a goodbye'),

    ('"אוקיי", "בסדר", "אני אעשה את זה" — the matter is settled. Close and end. Do not',
     '"Okay", "fine", "I\'ll do that" — the matter is settled. Close and end. Do not'),

    # FIXED PATHS
    ('**They refuse outright.** *"אני לא משלם את זה."* A decision, not a delay and not a',
     '**They refuse outright.** *"I\'m not paying this."* A decision, not a delay and not a'),

    ('who gave you a date has not told you about hardship** — *"אני אשלם בסוף השבוע, אין\n'
     'לי כסף עד אז"* is a promise with a reason attached. Take the date and close warmly.',
     'who gave you a date has not told you about hardship** — *"I\'ll pay at the weekend, I\n'
     'don\'t have the money till then"* is a promise with a reason attached. Take the date and close warmly.'),

    # The language barrier inverts with the language.
    ("**They do not speak Hebrew.** Apologise once and hand over with reason `language`.\n"
     "Do not attempt English, Russian or Arabic.",
     "**They do not speak English.** Apologise once and hand over with reason `language`.\n"
     "Do not attempt Hebrew, Russian or Arabic."),

    # The ownership offer (feature 14). A question, because it has to survive a
    # no — and "pass this to the team", never "put you through".
    ("> רוצה שאני אעביר את זה לצוות שיבדקו ויחזרו אליך?",
     "> Would you like me to pass this to the team, so they can check it and get "
     "back to you?"),

    # Voicemail. Ends on the phrase that releases the line, in its own language.
    ("> שלום, מדבר מיכאל מחברת הניהול הומיז לגבי בניין {{building}}. יש נושא שנשמח להסדיר איתך, אפשר לחזור אלינו למספר {{callback_number}}. תודה. שיהיה יום טוב.",
     "> Hello, this is Michael from Homies building management, regarding "
     "building {{building}}. There's a matter we'd be glad to settle with you. "
     "Please call us back on {{callback_number}}. Thank you and have a good day."),

    ("No amount. No month. Not the word חוב. **It ends on שיהיה יום טוב.** Read",
     'No amount. No month. Not the word debt. **It ends on "have a good day."** Read'),

    # NEVER SPEAK THE MACHINERY
    ('- **A tool name**, or an announcement that you are about to use one. *"אני רושם את\n'
     '  התוצאה"* is this. **A tool call needs no announcement at all** — not רגע, not\n'
     '  תן לי רגע, not אני בודק. Do it silently, then speak.',
     '- **A tool name**, or an announcement that you are about to use one. *"I\'m logging\n'
     '  the result"* is this. **A tool call needs no announcement at all** — not "one moment", not\n'
     '  "give me a sec", not "let me check". Do it silently, then speak.'),

    # ABSOLUTE RULES
    ("11. Never hesitate in the closing line or near ולהתראות. A hesitation inside it",
     '11. Never hesitate in the closing line or near "and goodbye". A hesitation inside it'),

    # BEFORE EVERY REPLY
    ("- Would a native Israeli actually say this? Does it sound translated?",
     "- Would a person on a phone actually say this? Does it sound written?"),

    ("- Is every verb and pronoun aimed at the caller — and every verb about\n"
     "  {{first_name}} — inflected for their gender? Every word in the turn, not just\n"
     "  the first one.",
     "- Am I addressing the caller by the name I was given, with no invented title?"),

    ("- If this is my last turn, does it carry יום טוב?",
     '- If this is my last turn, does it carry "good day"?'),
]


# ---------------------------------------------------------------------------
# The intake agent's substitution table.
#
# Longer than the debt one because the two prompts teach differently. The debt
# prompt recites: seven fixed lines the agent must say verbatim, and English
# prose around them. The intake prompt demonstrates — nearly every rule is
# followed by an example of a real sentence, in Hebrew, because a rule about how
# to sound is not teachable in the abstract. Those examples are the prompt's
# working parts, so all 25 have to cross.
#
# The examples are rewritten, not translated. "יש נזילה מהתקרה בחדר האמבטיה, זה
# כבר יומיים" is there to show what an unpolished caller sentence looks like, so
# the English has to be an unpolished English sentence rather than a faithful
# rendering of that particular Hebrew one. A stiff literal translation would
# teach the opposite of what the example is for.
# ---------------------------------------------------------------------------

# The Language section, replaced whole by regex. Anchored on `## Language` and on
# the last line of `### Saying it so it can be heard`, so an edit to either end
# stops the build instead of shipping a half-translated section.
INTAKE_BLOCKS = [(
    re.compile(r"## Language\n.*?\"language\", then close the call\.\n", re.S),
    """## Language

Speak English, only English, for the whole call.

If the caller speaks something other than English, do not attempt it. Say
"One moment - I'm passing this to someone who'll get back to you", call
transfer_to_human with reason "language", then close the call.

### Saying it so it can be heard

**An amount is understood; an identifier is copied**, and the two are said
differently. 450 is *four hundred and fifty shekels*, one whole number, **with
the "and"** - without it a caller can hear two separate sums. A reference
number, a phone number or an apartment number is digits, one at a time, with a
comma between them. Never say a digit sequence as a word.

NOTE ON THIS VERSION

This is the English twin of the Hebrew intake assistant, and it exists so the
call flow can be reviewed by someone who does not read Hebrew. The behaviour,
the rules and the tools are identical. Only the language differs, so do not
soften, shorten or improve anything relative to what you are told below.
""")
,(
    # Turn-openers and hesitation. Both sections are lists of Hebrew particles -
    # אז/אוקיי/בסדר, and אה as the hesitation sound - so they cross as their
    # English equivalents rather than as translations. Anchored on the next
    # heading, which is English and stable.
    #
    # One line in here is load-bearing rather than cosmetic: the ban on
    # hesitating near the closing phrase. `ולהתראות` is what `endCallPhrases`
    # matches on in Hebrew and "and goodbye" is what it matches on here, so a
    # sloppy rendering leaves the English twin unable to hang up.
    re.compile(r"## Opening a turn like a person\n.*?(?=## Never speak the machinery)", re.S),
    """## Opening a turn like a person

People start a lot of turns with one small word that shows they were listening:
so, okay, right, sure, got it, of course, no problem, one second.

**Never open two turns in a row with the same one**, and never let one of them
carry the whole call - a call where every turn starts with okay sounds like one
sentence played repeatedly. **Most turns take none at all**; a turn that starts
on its own content is the most natural turn there is.

No mate, no buddy. This is a company answering a phone, not a friend.

## Hesitation

Real people do not speak in finished sentences. You may hesitate, two ways only:

    uh     a hesitation sound, mid-sentence, between commas
    ...    a silent beat, no word at all

**Begin your first reply after the greeting with uh.** That is the turn where
the caller has just told you their problem and you are taking it in, and it is
the most natural hesitation in the whole call.

    Uh, okay. Water coming through the ceiling - which apartment?

After that, roughly one turn in three. Alternate the two; never use uh twice in
a row. At most one per turn. Write uh, never uhhh - more letters produce less
sound, not more, and that was measured rather than assumed.

**Never hesitate in these three places**, which are about specific words rather
than whole subjects:

- between the characters of a reference number
- between the words of a number or an address
- in the closing line, and never near "and goodbye"

"and goodbye" is what ends the call and nothing else does, so a hesitation
inside it stops the phrase matching and the call does not end.

Everywhere else is allowed. On 7 Aug the debt agent produced a call with no
hesitation at all, because its rules banned it near amounts and near the opening
and those were the only two turns a short call had. Bans that broad leave
nowhere for it to happen.

""")]


INTAKE_LINES = [
    # No identity entry any more. The Hebrew prompt turned masculine on 7 Aug and
    # now opens "You are Michael" in English — the same words the twin wants — so
    # a substitution here would be a rule with nothing to do. The block below
    # still carries the gender rules away, which is where the real difference is.

    # The language block, replaced whole — rebuilt 18 Aug against the masculine
    # prompt. Everything from `## Language` to the end of `### Saying it so it
    # can be heard` is about producing Hebrew: which verbs mark the speaker's
    # gender, how to address a caller whose gender is unknown, foreign words in
    # Hebrew letters, number-noun agreement, Hebrew abbreviations. English marks
    # none of it, so the whole section goes rather than being translated into
    # rules that would only spend attention.
    #
    # Two things in it are NOT about Hebrew and are kept: an amount is said as
    # words and an identifier is said digit by digit, and the non-native-speaker
    # transfer. The first is the rule the reference read-back depends on, which
    # is exactly what this twin exists to test.

    # The status-refusal line is gone from both sides. It was what stood between
    # a caller and an invented answer while the agent had no lookup; it has one
    # now (`get_request_status`), and a twin still carrying the refusal would be
    # testing a flow that no longer exists.

    # 19 Aug. The single out-of-scope line that used to sit here is gone from
    # both sides, and what replaced it is the reason: the agent said it to a
    # caller whose parcel had been taken and to another asking for a CCTV
    # review, and in both calls it was the whole response. Three rungs now, and
    # all three are translated together because a twin holding one of them is a
    # twin testing a flow that does not exist.
    ("אני מצטער לשמוע.", "I'm sorry to hear that."),

    # One sentence carrying both ways out, since 19 Aug. The two used to be
    # separate rungs and the caller had to refuse the first before hearing the
    # second, which read as a script advancing rather than as a person saying
    # what they can do.
    #
    # THE WORD IS NOT THE SAME ON BOTH SIDES, AND THAT IS THE POINT.
    # לפתוח קריאה is ordinary Hebrew — it is what an Israeli building-management
    # office says and what a resident says back. Its literal English, "open a
    # request", is not ordinary English: a caller on 19 Aug heard it and said
    # they did not follow it. English has its own everyday word for the same
    # thing and it is "ticket". A translation that matched word for word here
    # would be faithful to the Hebrew and wrong in the room.
    ("""    אני יכול לפתוח על זה קריאה, או להעביר את זה למשרד — אבל יש שם המון פניות
    כרגע, אז זה ייקח זמן. מה עדיף?""",
     """    I can open a ticket for this, or pass it to the office — but they're taking
    a lot of calls at the moment, so that would be a wait. Which would you
    prefer?"""),

    ("do not push — the sentence ends on *מה עדיף?*, which is a question, not a",
     "do not push — the sentence ends on *which would you prefer?*, which is a\n"
     "question, not a"),

    # The plainer second attempt, for a caller who did not follow the first.
    # Both sides have to be equally small words; a tidy English sentence here
    # would be testing a flow the Hebrew twin does not have.
    ("    אני רושם את הבעיה, במשרד רואים את זה וחוזרים אליך. בסדר?",
     "    I'll write the problem down, the office sees it, and they get back to\n"
     "    you. Alright?"),

    # The phone number is a fact and stays exactly as it is. Only the sentence
    # around it is translated - same rule as every other contact detail in this
    # table.
    ("    אין בעיה. אפשר לפנות למשרד ב־077-6687949.",
     "    That's no problem. You can reach the office on 077-6687949."),

    # Added 18 Aug. The status vocabulary arrived with `get_request_status` and
    # was never in this table, so the twin has been unbuildable since. The last
    # paragraph inverts on purpose: in Hebrew the rule is "never say the English
    # word", and here the system's word IS English, so what carries across is
    # *do not read the system's label out as written*.
    ("""    open         הפנייה פתוחה, הטיפול עוד לא התחיל
    in_progress  בטיפול
    resolved     טופלה ונסגרה
    cancelled    בוטלה

Never say the English word.""",
     """    open         it's open, nobody has started on it yet
    in_progress  someone is working on it
    resolved     it's been done and closed
    cancelled    it was cancelled

Never read the system's label out as it is written."""),

    # The amount example, from the balance section.
    ("are spoken as words — ארבע מאות חמישים שקלים — never as a digit sequence.",
     "are spoken as words — four hundred and fifty shekels — never as a digit sequence."),

    # Keeping what you caught rather than asking for the sentence again. The
    # English has to be an equally half-finished sentence, not a tidy one.
    ("and ask only for the gap — יש נזילה בחדר האמבטיה, הבנתי; לא תפסתי באיזו דירה.",
     "and ask only for the gap — got it, a leak in the bathroom; I didn't catch\n"
     "which apartment."),

    # Taking a correction. "The miss is always yours" is the rule; the two Hebrew
    # half-sentences are what it sounds like, so both have to cross.
    ("""אה, סליחה, הבנתי אותך לא נכון. Never defend the misreading. The miss is always
yours: לא הסברתי טוב, never לא הבנת.""",
     """uh, sorry — I had that wrong. Never defend the misreading. The miss is always
yours: I didn't explain that well, never you didn't understand."""),

    # The two questions the whole call depends on.
    ("""1. **Building.** באיזה בניין מדובר?
   Ask that and stop. Only if they say they do not know the name, ask for the
   street — as its own turn, later: באיזה רחוב זה?
2. **Apartment.** ומה מספר הדירה?""",
     """1. **Building.** Which building is this about?
   Ask that and stop. Only if they say they do not know the name, ask for the
   street — as its own turn, later: Which street is it on?
2. **Apartment.** And the apartment number?"""),

    # The description example, which is the difference between a ticket a
    # dispatcher can act on and one they have to phone back about.
    ("""  "יש נזילה מהתקרה בחדר האמבטיה, זה כבר יומיים" is the description.
  "בעיית אינסטלציה" is not — it throws away the two days, which is what decides""",
     """  "there's water coming through the bathroom ceiling, it's been two days" is the
  description. "plumbing issue" is not — it throws away the two days, which decides"""),

    ('  it is genuinely ambiguous — "אין מים חמים" could be plumbing or electrical.',
     '  it is genuinely ambiguous — "there\'s no hot water" could be plumbing or electrical.'),

    ("""- **Urgency** — you infer it from how they speak. "זה מציף לי את הבית" is high.
  "מתי שמישהו עובר" is low. When nothing points either way, it is normal and you""",
     """- **Urgency** — you infer it from how they speak. "it's flooding the flat" is high.
  "whenever someone's passing" is low. When nothing points either way, it is normal and you"""),

    # The confirmation turn, said before the row is written.
    ("       רשמתי: נזילה מהתקרה באמבטיה, הרצל 14 דירה 12. נכון?",
     "       So — water through the bathroom ceiling, Herzl 14, apartment 12. Is that right?"),

    # The tail only since 12 Aug — HM and the year are the same on every
    # reference, so they are four extra things to mishear on the one line the
    # caller has to write down. Both sides say the digits and nothing else.
    ("       מספר הקריאה שלך: 1, 0, 0, 1.",
     "       Your reference number is 1, 0, 0, 1."),

    ("    שמרתי את הפרטים שכן הספקתי, ונציג יחזור אליכם.",
     "    I've saved the details I got, and someone will call you back."),

    # Two attempts per slot, the second worded differently. The point is that the
    # second is not a repeat, so the English pair has to differ from each other
    # the same way the Hebrew pair does.
    ("""    First:  מה מספר הדירה?
    Second: אפשר להגיד לי את מספר הדירה ספרה ספרה?""",
     """    First:  What's the apartment number?
    Second: Could you give me the apartment number one digit at a time?"""),

    ("    קשה לי לשמוע אותך, יש רעש ברקע. אפשר לעבור למקום שקט יותר?",
     "    I'm having trouble hearing you, there's a lot of background noise.\n"
     "    Could you move somewhere quieter?"),

    ("    קשה לי לשמוע. שמרתי את מה שכן הצלחתי לקלוט יחד עם הקלטה, ונציג יחזור אליכם.",
     "    I'm struggling to hear you. I've saved what I could make out along with\n"
     "    the recording, and someone will call you back."),

    ("    זה נשמע דחוף. אני מסמן את זה כדחוף ומעביר לנציג עכשיו.",
     "    That sounds urgent. I'm marking it urgent and passing it to someone now."),

    # The emergency numbers do NOT translate. The caller is in Israel whichever
    # language they rang in, and 101 and 102 are the numbers that work there.
    # מד״א becomes the service rather than the acronym, which is what an English
    # speaker in Israel would be told anyway.
    ("    אם יש סכנה מיידית, תתקשרו למד״א 101 או לכבאות 102.",
     "    If anyone is in immediate danger, call an ambulance on 101 or the fire\n"
     "    service on 102."),

    ("    אני מבין. אני מעביר את זה לנציג שיחזור אליך.",
     "    I understand. I'm passing this to someone who'll get back to you."),

    # The closing, added 5 Aug. Both halves matter: "and goodbye" is what the
    # endCallPhrases entry matches on, exactly as ולהתראות is on the Hebrew side,
    # so this pair is load-bearing rather than cosmetic. A translation that
    # dropped the conjunction would leave the English twin unable to hang up.
    ("    משהו נוסף?", "    Anything else?"),

    ("    תודה שהתקשרת להומיז, יום טוב, ולהתראות.",
     "    Thanks for calling Homies, have a good day, and goodbye."),

    ("**Say the whole line.** Not להתראות on its own, not a shortened version, not",
     "**Say the whole line.** Not \"goodbye\" on its own, not a shortened version, not"),

    # The waiting line stopped being the agent's to say on 19 Aug — it is a
    # request-start message on the tool now, translated in TOOL_MESSAGES above,
    # and the prompt tells the agent to stay quiet rather than what to say. The
    # entries for the indented example and for the "hello?" silence rule went
    # with the section that held them; what is left is the two places the line
    # is still QUOTED, once as history and once inside the machinery rule.
    ("say it — and on 19 Aug you twice said *זה ייקח רק שנייה* instead, which is a",
     "say it — and on 19 Aug you twice said *this will just take a sec* instead,\n"
     "which is a"),

    ("This used to be your job — the prompt gave you *רגע, אני רושם* and asked you to",
     "This used to be your job — the prompt gave you *one moment, I'm writing this\n"
     "down* and asked you to"),

    # Inside the machinery rule, quoted inline. Replaced separately so a future
    # edit to either is caught rather than absorbed.
    ('Not: "I\'m opening a request now." Just: "רגע, אני רושם."',
     'Not: "I\'m opening a request now." Just: "One moment, I\'m writing this down."'),

    ("    אני העוזר הדיגיטלי של הומיז, אני פותח פניות. איך אפשר לעזור?",
     "    I'm the Homies digital assistant — I open maintenance requests. How can I help?"),

    # ---- 19 Aug: the call was correct and cold ----------------------------
    # A real English call answered every one of the caller's answers with the
    # next question and nothing else. These six pairs are the repair, and they
    # are all quoted speech, which is why they are all in this table.

    # The two words that go in front of the next question.
    ("""Two words. הבנתי. טוב. אוקיי, רשמתי. Not a sentence, not a thank-you, and not
a repeat of what they said — the rule above bans repeating an answer back, and
it does not ban hearing one.

    Not:  באיזו שעה השארת את זה בחוץ?
    But:  הבנתי. באיזו שעה השארת את זה בחוץ?""",
     """Two words. Got it. Okay. Right, I have that. Not a sentence, not a thank-you,
and not a repeat of what they said — the rule above bans repeating an answer
back, and it does not ban hearing one.

    Not:  What time did you leave it out?
    But:  Got it. What time did you leave it out?"""),

    # The filler question that got asked three times, and the one place it is
    # still allowed. Both quotes are the SAME English sentence in the real call,
    # which is exactly why the ban and the exception have to be separate entries.
    ("""ran to five, three of which were the same sentence — *משהו נוסף שכדאי
שהמשרד ידע?* — and by the third the caller was answering a question about the""",
     """ran to five, three of which were the same sentence — *anything else the office
should know?* — and by the third the caller was answering a question about the"""),

    ("nothing. There is exactly one *משהו נוסף?* in this call and it comes at the very",
     "nothing. There is exactly one *anything else?* in this call and it comes at the very"),

    # The turn that put a question on top of the reference number.
    ("*מספר הקריאה שלך: 1, 0, 6, 2. מה היה בתיק?*",
     "*your reference number is 1, 0, 6, 2. What was in the bag?*"),

    # Not knowing, said as a person rather than as a wall.
    ("""with it. You do not know, and rules 1 and 2 hold — but a bare *אני לא יכול
להגיד* is a door closing in someone's face""",
     """with it. You do not know, and rules 1 and 2 hold — but a bare *I cannot
say* is a door closing in someone's face"""),

    ("    אני לא יודע להגיד כמה זמן זה ייקח, אבל זה רשום אצלם והם חוזרים לגבי זה.",
     "    I can't tell you how long it will take, but it's written down with them\n"
     "    and they do come back about it."),

    ("""a report about a stolen parcel would take and heard *אני לא יכול להגיד מתי
זה ייפתר. משהו נוסף?* Both sentences were true.""",
     """a report about a stolen parcel would take and heard *I cannot say when it will
be resolved. Anything else?* Both sentences were true."""),

    # The closing, which split in two on the wire. Load-bearing on this side as
    # well: "and goodbye" is what endCallPhrases matches, and a full stop before
    # it is what stopped it arriving attached to the rest.
    ("**Commas, not full stops.** תודה שהתקשרת להומיז, יום טוב, ולהתראות is one",
     "**Commas, not full stops.** Thanks for calling Homies, have a good day, and\n"
     "goodbye is one"),

    # The improvised waiting line. The Hebrew quotes what the English twin
    # actually said, translated back, so both twins are warned off the same
    # sentence.
]


TWINS = {
    "debt": {
        "source": "9e2034d1-7a4f-4e3b-89ee-6a6155091ed7",   # Debt Follow-up (he)
        "name": "Homies — Debt Follow-up (en)",
        "stack": DEBT_STACK,
        "lines": DEBT_LINES,
        "block": DEBT_BLOCKS,
        "first_message": (
            "Hello, this is Michael from Homies, the building management company. "
            "Am I speaking with {{first_name}}?"
        ),
    },
    "intake": {
        "source": "f482abc1-db69-422b-afdd-f7b40ca9d995",   # Inbound Intake (he)
        "name": "Homies — Inbound Intake (en)",
        "stack": INTAKE_STACK,
        "lines": INTAKE_LINES,
        # A regex block since 18 Aug. The language section used to be one exact
        # entry in the table; it grew from 8 lines to 69 when the caller-gender
        # rules went in, and an exact match that long breaks on every unrelated
        # edit inside it. Anchored at both ends instead, which keeps the
        # match-exactly-once guarantee where it is load-bearing.
        "block": INTAKE_BLOCKS,
        # Shortened 5 Aug from "Hello, you've reached Homies building management.
        # This is Michael. How can I help?" — 6.4 seconds of TTS, and the caller
        # started speaking 0.5s in on the first real call and was talked over.
        "first_message": "Homies Building Management, Michael speaking. How can I help?",
    },
}


def englished(prompt, twin):
    """The Hebrew prompt with every language-bound passage swapped for English."""
    out = prompt

    blocks = twin["block"] or []
    if blocks and not isinstance(blocks, list):
        blocks = [blocks]
    for pattern, replacement in blocks:
        out, n = pattern.subn(lambda _: replacement, out, count=1)
        if n != 1:
            sys.exit("Section block did not match (found %d, want 1) — the Hebrew "
                     "prompt has changed:\n  %s" % (n, pattern.pattern[:80]))

    missed = []
    for pair in twin["lines"]:
        # A third element is how many times the passage is expected to appear.
        # Default 1, and that default is the safety property: a Hebrew line that
        # quietly gains a second home is a Hebrew line somebody duplicated
        # without deciding to. Where the duplication IS the decision — a fixed
        # line written out both where it is catalogued and where it is actually
        # said — the count says so out loud, in this file, next to the line.
        old, new = pair[0], pair[1]
        want = pair[2] if len(pair) > 2 else 1
        if out.count(old) != want:
            missed.append("[x%d, found %d] %s"
                          % (want, out.count(old), old.splitlines()[0][:70]))
            continue
        out = out.replace(old, new)

    if missed:
        sys.exit("These passages no longer match the live Hebrew prompt:\n  " +
                 "\n  ".join(missed) +
                 "\n\nUpdate the table in this file before creating anything. A "
                 "partly translated prompt is worse than none.")

    left = sorted(set(HEBREW.findall(out)))
    if left:
        for i, line in enumerate(out.splitlines(), 1):
            if HEBREW.search(line):
                print("  %4d| %s" % (i, line.strip()[:110]))
        sys.exit("Hebrew still present in the English prompt — see above.")

    return out


# What Vapi says while a sync tool runs, in both languages. Short, and about the
# caller rather than about the machine: the model's own improvisation on 19 Aug
# was "this will just take a sec", which is a sentence about how long a computer
# needs said to somebody waiting to hear whether their problem was written down.
TOOL_MESSAGES = {
    "רגע, אני רושם.": "One moment, I'm writing this down.",
    "רגע, אני בודק.": "One moment, let me check.",
}


def _englished_tool(tool):
    """A tool with its spoken messages translated and nothing else touched."""
    msgs = tool.get("messages")
    if not msgs:
        return tool
    out = []
    for m in msgs:
        content = m.get("content")
        if content is not None and HEBREW.search(content):
            if content not in TOOL_MESSAGES:
                sys.exit("A tool message has no English: %r\n"
                         "Add it to TOOL_MESSAGES in this file. A tool message is "
                         "spoken, and the twins share their tools verbatim." % content)
            m = dict(m, content=TOOL_MESSAGES[content])
        out.append(m)
    return dict(tool, messages=out)


def build(source, twin):
    """The English assistant body, everything but language held constant."""
    stack = twin["stack"]
    body = {k: v for k, v in source.items() if k not in READ_ONLY}
    body["name"] = twin["name"]

    model = dict(body["model"])
    model["messages"] = [
        {**m, "content": englished(m["content"], twin)} if m.get("role") == "system" else m
        for m in model["messages"]
    ]
    # Take the model from the stack, keeping everything else the Hebrew twin
    # carries — tools above all — so only the stack diverges. The tools are the
    # reason this is a copy rather than a second assistant: both twins post to
    # the same webhook, so a flow proved in English is the same flow in Hebrew.
    # Tool request-start messages are SPOKEN, and the twins share their tools
    # verbatim — so an untranslated one is the single place a Hebrew sentence
    # reaches an English caller's ear. Added 19 Aug with the messages themselves.
    # Anything unlisted stops the build rather than shipping in Hebrew, the same
    # rule the prompt table follows.
    model["tools"] = [_englished_tool(t) for t in (model.get("tools") or [])]
    model.update(stack["model"])
    if "temperature" not in stack["model"]:
        model.pop("temperature", None)      # gpt-5.x rejects one
    body["model"] = model

    body["voice"] = json.loads(json.dumps(stack["voice"]))
    body["transcriber"] = dict(stack["transcriber"])
    body["startSpeakingPlan"] = json.loads(json.dumps(stack["startSpeakingPlan"]))
    body["stopSpeakingPlan"] = json.loads(json.dumps(stack["stopSpeakingPlan"]))
    body["firstMessage"] = twin["first_message"]
    # The idle prompts went into the shared BASE on 12 Aug, so the copy above
    # brings the HEBREW ones across. Nothing else in this file would catch that:
    # englished() rewrites the system prompt and nothing else, and these live in
    # a config field. An English caller hearing "הלו? שומעים אותי?" is the exact
    # failure the twins exist to make visible.
    body["messagePlan"] = {
        "idleMessages": ["Hello? Are you still there?", "Still with me?"],
        # 12, not 8, since 18 Aug. At 8 the prompt fired "Still with me?" while a
        # resident was thinking mid-answer, twice on real calls, and it reads as
        # impatience. It also fights the closing handshake: that ends on a beat
        # where the agent asks and then waits, and a prod at 8 seconds lands in
        # exactly the pause the handshake exists to create.
        "idleTimeoutSeconds": 12,
        "idleMessageMaxSpokenCount": 2,
        "idleMessageResetCountOnUserSpeechEnabled": True,
        "silenceTimeoutMessage":
            "It sounds like we've lost the line. Thanks for calling Homies, "
            "have a good day, and goodbye.",
    }
    return body


def main():
    args = sys.argv[1:]
    if len(args) < 2 or args[0] not in TWINS or args[1] not in ("--dry", "--create", "--update"):
        sys.exit(__doc__)

    twin = TWINS[args[0]]
    source = api("GET", "/assistant/" + twin["source"])
    body = build(source, twin)

    if args[1] == "--dry":
        prompt = body["model"]["messages"][0]["content"]
        print("name:        ", body["name"])
        print("source:      ", source["name"])
        print("voice:       ", "%s / %s" % (body["voice"]["provider"], body["voice"]["voiceId"]))
        print("transcriber: ", "%s / %s" % (body["transcriber"]["provider"],
                                            body["transcriber"].get("model", "-")))
        print("model:       ", body["model"]["model"],
              "(%s on the Hebrew twin)" % source["model"]["model"])
        print("tools:       ", ", ".join(t["function"]["name"]
                                         for t in body["model"].get("tools") or []) or "none")
        print("maxDuration: ", body.get("maxDurationSeconds"), "seconds (from the Hebrew twin)")
        sp, st = body["startSpeakingPlan"], body["stopSpeakingPlan"]
        print("endpointing: ", "wait %ss, noPunct %ss, number %ss, backoff %ss" % (
            sp["waitSeconds"], sp["transcriptionEndpointingPlan"]["onNoPunctuationSeconds"],
            sp["transcriptionEndpointingPlan"]["onNumberSeconds"], st["backoffSeconds"]))
        print("prompt:       %d chars, no Hebrew remaining" % len(prompt))
        print("firstMessage:", body["firstMessage"])
        print("\nsubstitutions applied: %d passages%s" % (
            len(twin["lines"]),
            " + %d section blocks" % len(twin["block"]) if twin["block"] else ""))
        print("\nNothing was created. Re-run with --create.")
        return

    if args[1] == "--create":
        made = api("POST", "/assistant", body)
        print("created", made["id"], "-", made["name"])
        print("\nAdd this to web/index.html as the English option.")
    else:
        if len(args) < 3:
            sys.exit("--update needs an assistant id")
        made = api("PATCH", "/assistant/" + args[2], body)
        print("updated", made["id"], "-", made["name"])


if __name__ == "__main__":
    main()
