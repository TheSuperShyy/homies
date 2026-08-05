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
    "voice": voice_with_guard({"provider": "vapi", "voiceId": "Elliot"}, chunk=SPEECH),
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
        "waitSeconds": 0.4,
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
    "voice": voice_with_guard({"provider": "vapi", "voiceId": "Elliot"}, chunk=SPEECH),
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
        "waitSeconds": 0.4,
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
# The debt agent's substitution table.
#
# Line-level replacements. Each must match exactly once or the script stops.
# ---------------------------------------------------------------------------

DEBT_LINES = [
    # Identity
    ("You are Michael (מיכאל), the AI voice assistant of Homies (הומיז), a building",
     "You are Michael, the AI voice assistant of Homies, a building"),
    # Both twins are Michael since 5 Aug, so this entry now only strips the
    # Hebrew spelling — מיכאל is unpronounceable to an English voice and would
    # fail the no-Hebrew check besides.
    #
    # It used to do more, and the history is worth keeping: the Hebrew agent was
    # מיכל and this table renamed her, because Elliot renders "Mikhal" as
    # "McCall" every single time and because a male voice introducing itself
    # with a woman's name is its own problem. Moving the Hebrew agent to a male
    # voice made the two the same person and retired both reasons at once.

    ("You are making an outbound phone call to a resident regarding an unpaid ועד בית\npayment.",
     "You are making an outbound phone call to a resident regarding an unpaid\nbuilding committee payment."),

    ('"אני עוזר דיגיטלי של הומיז."',
     '"I\'m a digital assistant from Homies."'),

    # Style — the register is Israeli call-centre; in English keep the register,
    # drop the nationality, which would just make the model do an accent.
    ("Imagine you have worked in an Israeli customer service call center for years.",
     "Imagine you have worked in a customer service call center for years."),

    ("Speak exactly like a real Israeli customer service representative.",
     "Speak exactly like a real customer service representative."),

    ("Say numbers as Hebrew words, not digits.",
     "Say numbers as words, not digits."),

    # Grammar
    ("• natural Israeli word order",
     "• natural English word order"),

    ("always choose the one Israelis say most often.",
     "always choose the one people say most often."),

    # English barely marks gender, so the Hebrew agreement rule would be a no-op
    # that still burns attention. Keep only the part that survives translation.
    ("If `{{gender}}` is `f`, address the caller in feminine. If `m`, masculine. If\n"
     "`unknown`, phrase around it — say that the payment has not been settled rather\n"
     "than that they did not pay.",
     "If `{{gender}}` is `unknown`, phrase around it — say that the payment has not\n"
     "been settled rather than that they did not pay. Never guess at Mr or Ms."),

    # Naturalness — same contrast, English pair.
    ('"לפי המערכת שלנו"',
     '"according to our system"'),

    ('"לפי מה שרשום אצלנו"',
     '"as per the records held on file"'),

    ("Prefer wording commonly heard in Israeli phone conversations.",
     "Prefer wording commonly heard in ordinary phone conversations."),

    # The five fixed strings.
    # Replaced the card-authorisation line on 4 Aug. "you can complete it
    # yourself" is doing real work: it is what stops the resident waiting for
    # someone at Homies to do the next thing.
    ("> מצוין. אני שולח לך עכשיו קישור לתשלום, ואפשר להסדיר את זה ישירות דרכו.",
     "> Great. I'm sending you a payment link now, and you can settle it "
     "straight through it."),

    # The refusal callback offer. It went in on 5 Aug written in English, which
    # meant the Hebrew assistant carried an English line among six Hebrew ones —
    # the only spoken line in the prompt that was not in the language of the call.
    ("> רוצה שנציג מהמשרד יחזור אליך בנושא?",
     "> Would you like someone from the office to get back to you about it?"),

    ("> שלום, מדבר מיכאל מהומיז, חברת הניהול של הבניין. אני מדבר עם {{first_name}}?",
     "> Hello, this is Michael from Homies, the building management company. "
     "Am I speaking with {{first_name}}?"),

    ("Once they confirm, say why you are calling: the ועד בית payment for",
     "Once they confirm, say why you are calling: the building committee payment for"),

    ("> סליחה על ההפרעה, אני יכול למסור פרטים רק למי שהחשבון על שמו. "
     "אפשר לבקש מ{{first_name}} ליצור איתנו קשר?",
     "> Sorry to disturb you. I can only share details with the person whose "
     "name the account is in. Could you ask {{first_name}} to get in touch?"),

    ("> שלום, מדבר מיכאל מחברת הניהול הומיז, לגבי הבניין ב{{building}}. "
     "יש נושא שנשמח להסדיר, אפשר לחזור אלינו למספר {{callback_number}}. תודה ויום טוב.",
     "> Hello, this is Michael from Homies building management, regarding "
     "{{building}}. There's something we'd like to sort out with you. Please call "
     "us back on {{callback_number}}. Thank you and have a good day."),

    ("Say nothing about money. Not the amount, not the month, not the word חוב. Use",
     "Say nothing about money. Not the amount, not the month, not the word debt. Use"),

    ("No amount. No month. Not the word חוב.",
     "No amount. No month. Not the word debt."),

    ("> רגע אחד, אני מעביר אותך לנציג מהצוות שלנו. נא להישאר על הקו.",
     "> One moment, I'm transferring you to someone from our team. "
     "Please stay on the line."),

    # The closing. Added 4 Aug after a test call ended on a bare "Goodbye" —
    # the section said "a short warm closing" and gave no example, so the model
    # took the one concrete word nearby and used that.
    # Comma, not an em dash. With the dash the closing came out of a call as
    # "No problem. for your time. Have a good day, and goodbye" — Vapi splits
    # streaming TTS on punctuation, and " — " left "Great" as a chunk of its own,
    # short enough to be swallowed while the previous sentence was still playing.
    # The Hebrew line has no dash and has never lost a word.
    ("> מצוין, תודה רבה. שיהיה יום טוב ולהתראות.",
     "> Great, thank you. Have a good day, and goodbye."),

    # The vav is what makes ולהתראות unreachable by a bare goodbye, and "and" is
    # the English equivalent — both are what the call actually ends on, so the
    # rule has to name the right two words in each language.
    ("**But the last two words are fixed: the line ends \"ולהתראות\", with the vav, and\nnothing after it.** Not \"להתראות\" on its own, not \"ביי\", not a goodbye and then\none more helpful sentence.",
     "**But the last two words are fixed: the line ends \"and goodbye\", with the\n\"and\", and nothing after it.** Not \"goodbye\" on its own, not \"bye\", not a\ngoodbye and then one more helpful sentence."),

    # The language-barrier fixed path inverts.
    ("**They do not speak Hebrew.** Apologise once and hand over with reason\n"
     "`language`. Do not attempt English, Russian or Arabic, and do not keep trying in\n"
     "Hebrew.",
     "**They do not speak English.** Apologise once and hand over with reason\n"
     "`language`. Do not attempt Hebrew, Russian or Arabic, and do not keep trying in\n"
     "English."),
    # Added 5 Aug with the naturalness pass. Both of these blocks exist only
    # because Hebrew inflects and English does not — carried across literally
    # they would be instructions about grammar the English twin has no way to
    # apply, and the Hebrew example words would trip the no-Hebrew check.
    ("""**This applies to the fixed lines too.** They are written in masculine because
Hebrew has to pick one, and a fixed line cannot carry two. When `{{gender}}` is
`f`, say the same sentence with the endings inflected feminine — אליך, אותך,
רוצה, לך and any verb addressed to the caller. **Change nothing else**: not a
word, not the order, not the length. Re-inflecting is not permission to rephrase.
When `{{gender}}` is `unknown`, leave them as written.

A woman hearing a sentence built for a man is the single clearest sign that a
line was written somewhere else and read out unchanged, which is exactly what
this prompt is trying not to sound like.""",
     """**The fixed lines are said exactly as written.** English does not inflect
them, so there is nothing to adjust and nothing to rephrase."""),

    # The spoken-delivery section, 5 Aug. Two passages name Hebrew directly —
    # the ש"ח example and the list of Israeli opening particles — and both need
    # an English counterpart or the no-Hebrew check fails the build. The rest of
    # that section is about being heard rather than read, which is true in any
    # language and carries across untouched.
    ("""**Never say anything that is only written.** No abbreviations, no ש"ח, no
brackets, no slashes, no dates as numbers, no bullet points, no headings. If you
would not say it to someone standing in front of you, it does not go down a
phone line either.""",
     """**Never say anything that is only written.** No abbreviations, no brackets,
no slashes, no dates as numbers, no bullet points, no headings. If you would not
say it to someone standing in front of you, it does not go down a phone line
either."""),

    ("""**Start a reply the way a person starts one.** Israelis do not begin a turn with
the answer — they begin with a small word that shows they were listening: בסדר,
רגע, יופי, אוקיי, ברור, הבנתי. One of those, then the sentence. It costs a
syllable and it is most of the difference between sounding live and sounding
like a recording. Do not use the same one twice in a row.""",
     """**Start a reply the way a person starts one.** People do not begin a turn with
the answer — they begin with a small word that shows they were listening: right,
okay, sure, got it, of course. One of those, then the sentence. It costs a
syllable and it is most of the difference between sounding live and sounding
like a recording. Do not use the same one twice in a row."""),

    ("""**Money is said the way a person says it.** {{amount}} arrives as a figure; say
it as one whole spoken number and follow it with שקלים — never ש"ח, which is a
thing you write and not a thing you say, and never the digits read out in pieces.
On 4 Aug 450 came out of a call as "ארבע מאות, חמישים", two numbers side by side,
which is not an amount anybody would recognise as theirs.""",
     """**Money is said the way a person says it.** {{amount}} arrives as a figure; say
it as one whole spoken number followed by the word shekels, never as digits read
out in pieces. On 4 Aug 450 came out of a call as "four hundred, fifty", two
numbers side by side, which is not an amount anybody would recognise as
theirs."""),
]

# The LANGUAGE block, replaced whole — anchored at both ends so an edit anywhere
# inside it is still caught.
DEBT_LANGUAGE = (
    re.compile(r"Speak ONLY modern Israeli Hebrew\..*?Never sound robotic\.", re.S),
    "Speak ONLY English.\n\n"
    "Use plain, everyday English — the English of a phone call, not of a letter.\n\n"
    "Every response should sound spoken, not written.\n\n"
    "Never use textbook phrasing.\n\n"
    "Never sound scripted.\n\n"
    "Never sound robotic.\n\n"
    "NOTE ON THIS VERSION\n\n"
    "This is the English twin of the Hebrew assistant, and it exists so the call\n"
    "flow can be reviewed by someone who does not read Hebrew. The behaviour,\n"
    "the outcomes and the rules are identical. Only the language differs, so do\n"
    "not soften, shorten or improve anything relative to what you are told below.",
)


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

INTAKE_LINES = [
    # Identity. "Israeli building-management company" stays — that is a fact
    # about Homies, not an instruction to perform a nationality.
    ("You are Michal, the intake agent for Homies, an Israeli building-management",
     "You are Michael, the intake agent for Homies, an Israeli building-management"),

    # The language block, replaced whole. The gender sentence goes rather than
    # inverting: English does not mark the speaker's gender on the verb, so the
    # rule has nothing to act on and would only spend attention.
    ("""## Language

Speak Hebrew, only Hebrew, for the whole call. You speak about yourself in the
feminine first person.

If the caller speaks something other than Hebrew, do not attempt it. Say
"רק רגע, אני מעבירה אותך לנציג", call transfer_to_human with reason
"language", and stop.""",
     """## Language

Speak English, only English, for the whole call.

If the caller speaks something other than English, do not attempt it. Say
"One moment, I'm putting you through to someone", call transfer_to_human with
reason "language", and stop.

NOTE ON THIS VERSION

This is the English twin of the Hebrew intake assistant, and it exists so the
call flow can be reviewed by someone who does not read Hebrew. The behaviour,
the rules and the tools are identical. Only the language differs, so do not
soften, shorten or improve anything relative to what you are told below."""),

    # The refusal that replaced the status lookup. The most important line in the
    # prompt to get right in both languages: it is the one standing between a
    # caller and an invented answer.
    ("    אין לי גישה לסטטוס של פניות קיימות. אני מעבירה אותך לנציג שיוכל לבדוק.",
     "    I don't have access to the status of existing requests. Let me put you\n"
     "    through to someone who can check."),

    ("    זה משהו שנציג צריך לטפל בו. אני מעבירה אותך.",
     "    That's something a person needs to handle. I'll put you through."),

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

    ("       מספר הפנייה שלך HM-2026-1001.",
     "       Your reference number is HM-2026-1001."),

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

    ("    זה נשמע דחוף. אני מעבירה אותך עכשיו לנציג.",
     "    That sounds urgent. I'm putting you through to someone right now."),

    # The emergency numbers do NOT translate. The caller is in Israel whichever
    # language they rang in, and 101 and 102 are the numbers that work there.
    # מד״א becomes the service rather than the acronym, which is what an English
    # speaker in Israel would be told anyway.
    ("    אם יש סכנה מיידית, תתקשרו למד״א 101 או לכבאות 102.",
     "    If anyone is in immediate danger, call an ambulance on 101 or the fire\n"
     "    service on 102."),

    ("    אני מבינה. אני מעבירה אותך לנציג שיוכל לעזור.",
     "    I understand. I'm putting you through to someone who can help."),

    ('saying "הלו?".', 'saying "Hello?".'),

    # The filler said while a tool runs. Appears twice in the prompt and the two
    # are not interchangeable — this one is the example, indented.
    ("    רגע, אני רושמת.", "    One moment, I'm writing this down."),

    # ...and this one is inside the machinery rule, quoted inline. Replaced
    # separately so a future edit to either is caught rather than absorbed.
    ('Not: "I\'m opening a request now." Just: "רגע, אני רושמת."',
     'Not: "I\'m opening a request now." Just: "One moment, I\'m writing this down."'),

    ("    אני העוזרת הדיגיטלית של הומיז, אני פותחת פניות. איך אפשר לעזור?",
     "    I'm the Homies digital assistant — I open maintenance requests. How can I help?"),
]


TWINS = {
    "debt": {
        "source": "0ef11cb5-81ce-49e7-864d-8a3e4d5728b9",   # Debt Follow-up (he)
        "name": "Homies — Debt Follow-up (en)",
        "stack": DEBT_STACK,
        "lines": DEBT_LINES,
        "block": DEBT_LANGUAGE,
        "first_message": (
            "Hello, this is Michael from Homies, the building management company. "
            "Am I speaking with {{first_name}}?"
        ),
    },
    "intake": {
        "source": "51bbe77a-dd86-4629-8c0b-b0da06ca4461",   # Inbound Intake (he)
        "name": "Homies — Inbound Intake (en)",
        "stack": INTAKE_STACK,
        "lines": INTAKE_LINES,
        # No regex block: the intake prompt's language section is replaced as an
        # ordinary exact-match entry in the table above, which gives the same
        # match-exactly-once guarantee with less machinery.
        "block": None,
        # Shortened 5 Aug from "Hello, you've reached Homies building management.
        # This is Michael. How can I help?" — 6.4 seconds of TTS, and the caller
        # started speaking 0.5s in on the first real call and was talked over.
        "first_message": "Homies Building Management, Michael speaking. How can I help?",
    },
}


def englished(prompt, twin):
    """The Hebrew prompt with every language-bound passage swapped for English."""
    out = prompt

    if twin["block"]:
        pattern, replacement = twin["block"]
        out, n = pattern.subn(lambda _: replacement, out, count=1)
        if n != 1:
            sys.exit("LANGUAGE block did not match. The Hebrew prompt has changed.")

    missed = []
    for old, new in twin["lines"]:
        if out.count(old) != 1:
            missed.append(old.splitlines()[0][:70])
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
    model.update(stack["model"])
    if "temperature" not in stack["model"]:
        model.pop("temperature", None)      # gpt-5.x rejects one
    body["model"] = model

    body["voice"] = json.loads(json.dumps(stack["voice"]))
    body["transcriber"] = dict(stack["transcriber"])
    body["startSpeakingPlan"] = json.loads(json.dumps(stack["startSpeakingPlan"]))
    body["stopSpeakingPlan"] = json.loads(json.dumps(stack["stopSpeakingPlan"]))
    body["firstMessage"] = twin["first_message"]
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
            len(twin["lines"]), " + the LANGUAGE block" if twin["block"] else ""))
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
