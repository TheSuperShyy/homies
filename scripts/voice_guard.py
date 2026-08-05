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
is digits, {{verification_email}} is office@homies.co.il, {{building}} is a
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
SPOKEN = [
    "open payment ticket",      # retired tool, and the one that actually leaked
    "send payment link",
    "log promise to pay",
    "request standing order",
    "log disputed payment",
    "flag not handed over",
    "log call outcome",
    "transfer to human",
    "open request",             # "I'll open a request" does not match this
    "authorization captured",
    "posture reached",
    "promised date",
    "transfer reason",
    "office to contact",
    "wrong party",
    "caller request",
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
SPEECH = {
    "minCharacters": 60,
    "punctuationBoundaries": [".", "!", "?"],
}


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


def leaks(text):
    """Every machinery leak in a piece of spoken text: [(name, matched), ...]."""
    import re
    found = []
    for name, rx in checks():
        for m in re.finditer(rx, text):
            found.append((name, m.group(0)))
    return found
