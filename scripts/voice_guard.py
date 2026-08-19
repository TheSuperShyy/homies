"""What the agent is not allowed to say out loud, in one place.

WHY THIS IS NOT JUST A PROMPT RULE
Twice a resident has heard the machinery instead of a sentence, and neither time
was a prompt violation the model could have been talked out of:

  4 Aug — gpt-5.4-mini emitted its own tool-call syntax into the spoken channel.
          The resident heard: "Open payment ticket. two functions, open payment
          ticket ten ten i Kypiao TCN Jason. authorization captured. True."
          The underlying text was
          `to=functions.open_payment_ticket <|constrain|>json {"authorization_captured": true}`.
          Vapi logged zero tool calls: the ticket was never opened either.

  5 Aug — gpt-5.5 spoke the `note` parameter of send_payment_link. The resident
          heard "Note," and then, as a separate utterance, the whole internal
          note read back as a sentence.

A model that emits a tool call into the text stream has already failed to
distinguish the two channels, so an instruction addressed to it cannot help. The
fix has to sit somewhere the model does not control. Three places do:

  1. The tool definitions — a parameter that does not exist cannot be spoken.
     `send_payment_link` was stripped to zero parameters on 5 Aug for exactly
     this reason. See scripts/vapi_tools.py.
  2. THIS FILE — Vapi applies `voice.chunkPlan.formatPlan.replacements` to every
     chunk after the model and before the voice provider. Whatever matches here
     never reaches the speaker, whatever the model intended.
  3. The prompt — NEVER SPEAK THE MACHINERY in
     docs/features/10-debt-followup/prompt.md, which is the only layer that can
     reach a *prose* leak ("my instructions say I should..."). That one is
     best-effort by nature. The patterns below are not.

THE INVARIANT THESE PATTERNS RELY ON
Nothing a person says on a phone call — in Hebrew or in English — contains a
snake_case identifier, a `<|token|>`, a `{{variable}}` or a JSON key. So a
pattern that matches those is safe to delete unconditionally, and that is what
makes this a filter rather than a heuristic. Every tool name, every enum value
(`wrong_party`, `office_to_contact`, `not_handed_over`) and every parameter
name (`promised_date`, `posture_reached`) is snake_case, so one pattern covers
all of them and keeps covering them when a new tool is added.

The one thing to watch: if a value the agent legitimately reads aloud ever
contains an underscore, it will be eaten. Today none does — {{callback_number}}
is digits, {{verification_email}} is Office@homies-management.co.il, {{building}} is a
street. Check this before putting a real Homies email in.

TWO LAYERS, BECAUSE THE STRUCTURE IS GONE BY THE TIME ANYONE SEES IT
Vapi's own formatter de-structures a chunk before the voice provider gets it.
The 4 Aug call is stored — in both `transcript` and `artifact.messages` — as
"Open payment ticket. two functions, open payment ticket ten ten i Kypiao TCN
Jason. authorization captured. True." The underscores are already spaces, the
`<|constrain|>` has already become syllables, and `true}` has already become
"True." Nothing that reads a transcript back can match a snake_case pattern
against it, because by then there is no snake_case left.

So there are two sets of patterns and they defend different moments:

  PATTERNS — the raw shapes, matched against the chunk as the model wrote it.
  SPOKEN   — the same identifiers written the way the formatter renders them,
             as ordinary words with spaces.

Which one fires depends on whether Vapi applies replacements before or after its
own formatters, and the schema does not say. The documented examples imply
before — a phone-number replacement of `(\\d{3})(\\d{3})(\\d{4})` only makes sense
on digits that have not yet been spelled out — but "implied by an example" is not
a guarantee to put under a live call. Both sets are sent. One of them is
redundant and it costs nothing to find out which.

WHAT IT DOES NOT DO
Vapi's regex replacement uses Node's `string.replace` without the global flag,
so each pattern strips its *first* match per chunk. Chunks are short (~30 chars,
split on punctuation), so a long leak is spread over several chunks and each is
cleaned in turn — but a single chunk carrying two identifiers loses only one.
This is a floor, not a proof. It is why scripts/vapi_leak_check.py exists.
"""

# (name, regex) — the regex is written once and used twice: sent to Vapi as a
# replacement, and compiled in Python by the leak checker. They cannot drift,
# which matters because the checker's whole job is to prove the filter worked.
#
# Order is deliberate: the wide patterns run first so they take the whole span
# before a narrower one takes a piece of it. `to=functions.open_payment_ticket`
# should disappear as one match, not leave `functions.` behind.
PATTERNS = [
    # Harmony / control tokens. `<|constrain|>`, `<|channel|>`, `<|message|>`.
    ("control-token", r"<\|[^|]*\|>"),
    # The model addressing a tool. Takes the tool name with it.
    ("tool-call-syntax", r"to=[A-Za-z_.]+"),
    ("functions-prefix", r"functions\.[A-Za-z_]+"),
    # An unsubstituted variable. A dashboard test call sends no variableValues,
    # so this is reachable without any model error at all.
    ("template-variable", r"\{\{[^}]*\}\}"),
    # A JSON key. `"authorization_captured":`
    ("json-key", r'"[A-Za-z_]+"\s*:'),
    # Every tool name, every enum value, every parameter name — and every one
    # added later, without this file being touched.
    ("snake-case", r"\b[A-Za-z]+(?:_[A-Za-z]+)+\b"),
]

# The same identifiers as the formatter renders them: underscores turned into
# spaces. This is the layer that would have caught 4 Aug, because that is the
# form the resident actually heard.
#
# Every entry here had to pass one test: could a resident or the agent say this
# in the course of an ordinary collection call? Anything that could is left out
# and defended by the prompt instead, because eating a real sentence is a worse
# failure than reading one identifier. Deliberately excluded, with the sentence
# that excluded them:
#
#   "not handed over"  — "you have not handed over the keys yet"
#   "no answer"        — "there's no answer at the office right now"
#   "not understood"   — "sorry, I have not understood"
#   "first name"       — "can I take your first name?"
#   "callback number"  — a resident may ask for the callback number by name
#   open / friction / hot / dispute / hardship / language — ordinary words
#
# SIX MORE LEFT ON 19 AUG, AND THIS IS THE FAILURE THAT REMOVED THEM
# A resident reporting a parcel taken from outside their door heard:
#
#     "Would you like me to  though."
#
# The model had written "Would you like me to open request though." and this
# filter deleted the verb. Nothing errored, nothing was logged, and the sentence
# arrived at the speaker with a hole in it. `open request` even carried the
# comment "I'll open a request does not match this" — true, and beside the point:
# a model that drops an article is not a model that has leaked a tool name.
#
# The test at the top of this block was written for a COLLECTION call and never
# re-applied when the intake agent shipped, whose single commonest sentence is an
# offer to open a request. So the test is now enforced rather than remembered —
# see SAFE_SENTENCES below, checked by scripts/vapi_leak_check.py.
#
# What went, and the sentence that took it:
#
#   "open request"           — "would you like me to open request?"
#   "office to contact"      — "I'll ask the office to contact you"
#   "wrong party"            — "it sounds like I have the wrong party"
#   "caller request"         — marginal, and two ordinary words either way
#   "send payment link"      — "I'll send payment link now"
#   "request standing order" — "I can request standing order for you"
#
# All six are still caught in their raw form by the snake-case pattern above,
# which is the shape a real leak arrives in. What is given up is the second layer
# on the already-formatted spelling — and a leak read aloud once is a smaller
# failure than a sentence with a hole in it on every call.
#
# THE RULE FOR ADDING ANYTHING HERE
# Three words or more, and it must read as machinery rather than as English. A
# two-word entry is almost always an ordinary phrase in one of the two languages
# and belongs in the prompt instead.
SPOKEN = [
    "open payment ticket",      # retired tool, and the one that actually leaked
    "log promise to pay",
    "log disputed payment",
    "flag not handed over",
    "log call outcome",
    "transfer to human",
    "authorization captured",
    "posture reached",
    "promised date",
    "transfer reason",
]

# Sentences both agents actually say, which must survive the filter untouched.
#
# This exists because the rule above was correct, written down, and still broken:
# a rule nothing checks is a comment. Every one of these is taken from a live
# prompt or a real transcript, and `scripts/vapi_leak_check.py --safe` fails if
# the filter changes any of them by a single character.
#
# Add to this list whenever a prompt gains a fixed line. It costs nothing and it
# is the only thing standing between a new SPOKEN entry and a call full of holes.
SAFE_SENTENCES = [
    # Intake, 19 Aug — the three rungs, the ones that broke.
    "I can open a request for this so the office has it in writing and comes back to you.",
    "Would you like me to open request though?",
    "I will open request for the missing baggage.",
    "I'll ask the office to contact you.",
    "Would you like me to add anything else the office should know about?",
    "Your reference number is 1, 0, 6, 1.",
    # Debt.
    "I'll send you a payment link now.",
    "I can request a standing order for you.",
    "It sounds like I have the wrong party.",
    "That's something a person needs to handle.",
    # Intake, 19 Aug — the lines added when the call came back correct and cold.
    # The rung-two offer was reworded out of the system's vocabulary and into a
    # resident's, so both wordings are here: the new one because it is said, the
    # old one because a filter that breaks it would break the new one too.
    "I can open a ticket for this, or pass it to the office — but they're taking a lot of calls.",
    "I'll write the problem down, the office sees it, and they get back to you.",
    "I can't tell you how long it will take, but it's written down with them.",
    "Got it. What time did you leave it out?",
    "One moment, I'm writing this down.",
    "Thanks for calling Homies, have a good day, and goodbye.",
    # Hebrew, where the pronunciation substitutions also run.
    "אני יכול לפתוח על זה קריאה, או להעביר את זה למשרד. מה עדיף?",
    "אני לא יודע להגיד כמה זמן זה ייקח, אבל זה רשום אצלם והם חוזרים לגבי זה.",
    # A pair, because this one is meant to change: the pronunciation
    # substitution rewrites להומיז, and the second half is what it must become.
    # Getting anything else — a hole, a different rewrite — is the failure.
    ("תודה שהתקשרת להומיז, יום טוב, ולהתראות.",
     "תודה שהתקשרת לחברת הומיז, יום טוב, ולהתראות."),
    "אני יכול לפתוח על זה קריאה, ואז זה רשום במשרד וחוזרים אליך. רוצה?",
    "אפשר לפנות למשרד ב־077-6687949.",
    "מספר הקריאה שלך: 1, 0, 0, 1.",
]

# The 5 Aug shape: a note parameter announced by its own field name. "Please
# note," matches the tail of this and loses two words — acceptable, since the
# style section forbids that phrasing anyway.
NOTE_PREFIX = r"\bNote[,:]\s*"

# Braces and brackets. Never spoken by anyone; always structure that escaped.
# Exact rather than regex so replaceAllEnabled can clear the whole chunk rather
# than the first one.
BRACKETS = ["{", "}", "[", "]"]

# Case-insensitive, because the formatter capitalises: the resident heard "Open
# payment ticket", not "open payment ticket". An exact replacement would have
# missed it on the capital O, which is why these are regexes.
_ICASE = [{"type": "ignore-case", "enabled": True}]

# ---------------------------------------------------------------------------
# Pronunciation. The same mechanism, used to rewrite rather than to delete.
# ---------------------------------------------------------------------------
#
# Everything above deletes; these substitute. They share this file because they
# share one `formatPlan`, and splitting them across two modules would mean the
# second one silently overwrote the first — the same trap documented on
# chunkPlan below.
#
# WHY THIS IS NOT ONLY A PROMPT FIX
# The client heard the opening line as "מיכאל מלאומיז" on 12 Aug. The cause is
# that Hebrew glues a one-letter preposition onto the following word, so
# מ + הומיז is written מהומיז and the voice reads the pair as one unfamiliar
# word. The opening is a fixed line and was corrected there — but the model
# composes most of its sentences, and the next time it writes the company name
# after a preposition it will write it glued, because that is correct Hebrew.
# A rule cannot reach a form the language itself produces. This can.
#
# The substitutions are grammatical in any sentence: "מיכאל מהומיז" becomes
# "מיכאל מחברת הומיז", "התקשרת להומיז" becomes "התקשרת לחברת הומיז". The company
# name always ends up standing on its own, which is the whole point.
#
# ANYTHING ADDED HERE MUST BE CHECKED BY EAR, not by argument. A replacement
# that fixes one word and breaks the sentence around it is worse than the word.
PRONUNCIATION = [
    ("מהומיז", "מחברת הומיז"),
    ("להומיז", "לחברת הומיז"),
    # "בית לא נשמע כמו בעברית" — 12 Aug. The word he would have heard it in is
    # ועד בית, which is how the prompt wrote it and is not how anyone says it:
    # Israelis say ועד הבית, with the article. Without it the two nouns collide
    # into va'ad-bayit and the second one lands as a bare dictionary word rather
    # than part of a phrase. Fixed in the prompt too; this catches the sentences
    # the model composes.
    #
    # NOT PROVEN. It is the best available reading of a complaint about a sound,
    # and a sound needs an ear. If ועד הבית still lands wrong, the problem is the
    # voice rather than the phrase, and that is a different change.
    ("ועד בית", "ועד הבית"),
]


def spoken_patterns():
    """SPOKEN as bounded regexes, for the filter and the checker alike."""
    return [("spoken:" + s, r"\b" + s.replace(" ", r"\s+") + r"\b") for s in SPOKEN]


def replacements():
    """The `voice.chunkPlan.formatPlan.replacements` array Vapi wants."""
    out = [{"type": "regex", "regex": rx, "value": ""} for _, rx in PATTERNS]
    out += [{"type": "regex", "regex": rx, "value": "", "options": _ICASE}
            for _, rx in spoken_patterns()]
    out.append({"type": "regex", "regex": NOTE_PREFIX, "value": "", "options": _ICASE})
    out += [{"type": "exact", "key": b, "value": "", "replaceAllEnabled": True}
            for b in BRACKETS]
    # Last, and substituting rather than deleting. Nothing above can match a
    # Hebrew word, so the order is not load-bearing — but a deletion that ran
    # after a substitution could eat what the substitution just wrote, and this
    # way round that cannot happen.
    out += [{"type": "exact", "key": k, "value": v, "replaceAllEnabled": True}
            for k, v in PRONUNCIATION]
    return out


def voice_with_guard(voice, chunk=None):
    """A voice block with the filter attached, leaving the rest untouched.

    `chunk` is merged into the same chunkPlan. It has nothing to do with leaks —
    it is how the text is cut into audio, which is a prosody decision — but the
    two share one object in Vapi's schema and splitting them across two files
    would mean the second one silently overwrites the first.
    """
    guarded = dict(voice)
    guarded["chunkPlan"] = dict(chunk or {},
                                formatPlan={"replacements": replacements()})
    return guarded


# How the text is cut into audio, which decides how it is *heard*.
#
# The default boundary list includes the comma and the colon, so a sentence with
# a comma in it is synthesised as two separate pieces — and a TTS given a
# fragment gives it a complete intonation contour, because it has no way to know
# more is coming. A 4 Aug call came out as
#
#     "לפי מה שרשום אצלנו הוא עדיין לא הוסדר. שקלים. מצויין."
#
# where שקלים and מצויין are each their own utterance with their own falling
# ending. Nothing about the words is wrong. It sounds like a machine because it
# was spoken in pieces.
#
# Cutting only at sentence ends gives the voice a whole clause to shape, which is
# the difference between reading and speaking. The cost is latency to first
# audio: the model has to reach a full stop before anything is heard. That is
# affordable here because the style section already caps a turn at two short
# sentences — a rule written for a different reason that happens to make this
# safe.
#
# minCharacters is raised too, so a two-word acknowledgement is not flushed on
# its own while the rest of the sentence is still arriving.
# WITHDRAWN 5 Aug, the same day it went in. Kept here, unused, because the
# reasoning below is sound and the evidence against it is circumstantial —
# but circumstantial evidence from a real call beats sound reasoning.
#
# Two English calls came back mangled: "I understand. someone from the office
# get back to you about it." — words simply gone from the middle of a fixed
# line. A full config diff against the previous night, when the same agent
# was working well, found ONE functional difference on the English side: this
# block. Same model, same voice, same transcriber, same prompt, same eight
# tools, same guard, same endpointing. Only the chunk plan was new.
#
# That does not prove it caused the dropped words. It does mean it is the
# only candidate, and a change made to improve prosody is not worth a
# sentence losing words. The fragmented-Hebrew problem it was written for is
# real and still unsolved; it needs to be fixed without this, or with this
# reintroduced one field at a time against recorded calls.
_SPEECH_WITHDRAWN = {
    "minCharacters": 60,
    "punctuationBoundaries": [".", "!", "?"],
}

# Nothing sets a chunk plan now. voice_with_guard(voice) leaves chunkPlan
# carrying only formatPlan, which is what every assistant ran the night the
# calls were good.
SPEECH = {}


# ---------------------------------------------------------------------------
# Detection. Used by scripts/vapi_leak_check.py against what was actually said.
# ---------------------------------------------------------------------------

# Prose leaks — the model describing its own instructions in ordinary words.
# No filter can catch these without mangling real speech, so they are checked
# after the fact rather than blocked, and the prompt is what has to prevent
# them. Deliberately narrow: "the system" alone is a phrase the agent is *told*
# to use ("according to our system"), so only give-aways are listed.
PROSE = [
    ("says-instructions", r"(?i)\b(my|the) (instructions|prompt|system prompt|rules say)\b"),
    ("says-script", r"(?i)\b(my|the) script\b"),
    ("says-tool", r"(?i)\bI(?:'m| am| will| shall)? (?:going to |now )?(?:call|calling|invoke|log|logging|trigger)(?:ing)? (?:the )?(?:tool|function|outcome|a note)\b"),
    ("says-language-model", r"(?i)\b(language model|as an AI (model|assistant),? I (cannot|can't|am)|OpenAI|gpt-?[0-9])\b"),
    ("says-instructions-he", r"(ההוראות שלי|התסריט שלי|לפי ההנחיות שקיבלתי|הפרומפט)"),
]


def checks():
    """Everything the leak checker looks for, most serious first.

    PATTERNS almost never fire against a stored transcript — the formatter has
    already removed the structure they describe — so a hit there means raw model
    output reached the record untouched, which is worse than it sounds. The
    spoken forms are what actually catch a leak after the fact.
    """
    return (PATTERNS
            + [("spoken-note", "(?i)" + NOTE_PREFIX)]
            + [(n, "(?i)" + rx) for n, rx in spoken_patterns()]
            + PROSE)


def filtered(text):
    """The text as the speaker would receive it, with every replacement applied.

    Mirrors what Vapi does to a chunk, so a sentence can be tested against the
    filter without placing a call. Vapi strips the FIRST match per pattern per
    chunk — no global flag — so `count=1` here rather than a blanket sub; a
    stricter test than the real thing would report damage that never happens.
    """
    import re
    for rep in replacements():
        if rep["type"] == "regex":
            flags = re.I if rep.get("options") else 0
            text = re.sub(rep["regex"], rep["value"], text, count=1, flags=flags)
        else:
            text = text.replace(rep["key"], rep["value"])
    return text


def safe_sentence_failures():
    """Sentences the agents really say that this filter would damage.

    Empty is the only acceptable answer. A non-empty list means a SPOKEN entry
    is eating ordinary speech, which is what happened on 19 Aug: a resident
    reporting a stolen parcel heard "Would you like me to  though."
    """
    out = []
    for entry in SAFE_SENTENCES:
        # A bare string must survive the filter unchanged. A pair says the line
        # is expected to change and gives the exact result — that is how the
        # deliberate pronunciation rewrites are told apart from holes.
        sentence, want = entry if isinstance(entry, tuple) else (entry, entry)
        after = filtered(sentence)
        if after != want:
            out.append((sentence, after))
    return out


def leaks(text):
    """Every machinery leak in a piece of spoken text: [(name, matched), ...]."""
    import re
    found = []
    for name, rx in checks():
        for m in re.finditer(rx, text):
            found.append((name, m.group(0)))
    return found
