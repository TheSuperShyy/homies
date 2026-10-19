# -*- coding: utf-8 -*-
"""A rejected reply gets one more pass with the tools before a stub ticket.

    python scripts/n8n_whatsapp_retry.py            # dry run
    python scripts/n8n_whatsapp_retry.py --apply    # write it
    python scripts/n8n_whatsapp_retry.py --restore  # put the 18 Sep snapshot back

WHY, 18 SEP
`Reply usable?` throws a reply away when it is empty, claims a ticket with no
reference behind it, or carries a link no tool returned. What happened next
was `Open it anyway`: a `rescue_request` with no building and no type, the
whole message log as its description, status `needs_review`. Live at 09:16:
a mould report, four turns, and on the last one the model wrote "אני פותח
קריאת שירות" and called nothing. The resident got a real reference
(255-1291-26) for a ticket that said nothing a technician could act on.
The owner, over the tickets table: "there is a bug".

The stub is the right last resort and the wrong first one. The model had
everything it needed and skipped the call; the cheapest correct thing is to
hand it the same message again with a note saying so, and let it call the
tool. Two replays of that conversation on fresh numbers opened a proper
ticket (type, building, common area) on the first try, so a second pass is
a good bet, and the stub is still there when it is not.

WHAT THIS DOES
  Reply usable? (false) -> Already retried? -> (no)  Try again -> Answer the resident
                                             -> (yes) Open it anyway -> Say it again ...

`Try again` is a Set node that re-emits the item the agent got the first time
(`Still the last word?`'s output, so `greeted`, `photo`, `text` and the rest
are all there) plus `retry_note`, which the agent's user-turn template
appends among its bracketed facts (AGENT_NEW in n8n_whatsapp_untemplate.py,
epoch 48). `Already retried?` reads its own `$runIndex`: 0 on the first
pass, 1 on the second, so the loop runs exactly once. Nothing else moves:
`Say it again`, `Second try usable?` and the send path are untouched, and on
the retry `$('Answer the resident').first()` is the latest run, which is
the draft `Say it again` should be replacing.

THE MEMORY COST, NAMED
The buffer (`Conversation so far`) records both passes: the rejected draft
as an assistant turn, then the note-plus-message and the real reply. The
1 Sep lesson is that a model copies its own last answer; the note says in
so many words that the last answer was thrown away and why, which is the
best counter this workflow has. Watched, not assumed.

HONEST LIMIT
Like `Say it again`, this cannot be fired on demand -- it needs the model to
produce an unusable reply -- so it ships wired and read back, and the
expressions proven in Node. The first live firing is the test.

TWO MORE REASONS, 20 SEP
Live, the owner's handset: "hey wassup, i would like to report something"
got the system's opener recited word for word and, because Send's text net
saw the opener, the three buttons (50815); "hey how is it going? i want to
report something" got "ספר/י" (50885), the slash form the prompt bans. Both
are style faults, not lies, so a stub ticket is the wrong fallback for them.
Two conditions join `Reply usable?` here (same by-id mechanism as paylink's
`links`): `plural` rejects a gendered slash or bracket form, `opener`
rejects a bare "how can I help" on a message that was not a bare hello.
Both are FIRST-PASS ONLY (`$runIndex > 0 ||`): on the retry the reply goes
out as the model wrote it rather than minting a stub. The retry note names
both reasons without quoting the opener -- naming a phrase is how the model
is handed it (1 Sep). Nothing here adds a word a resident could read: the
owner's rule is no fixed message except the menu, and this keeps it.

A THIRD, 4 OCT: `rephay`. The owner's לדבר עם נציג tap got "היי, אני מיכאל
מהומי'ז. במה אוכל לעזור לך?" (execution 80740) and he asked again for "hi this is
michael from homies how are you doing today?". The prompt now asks for that and
for nothing else on the tap (epoch 72, n8n_whatsapp_rephay.py), and this guard
backs it: on the tap's own turn (Sort's `tap` is 'other'), a reply that does not
ask how he is goes back once, first pass only like the other two. `Try again`
reads the same thing off the rejected text and names it; that note alone does
not carry the tools line, because there is nothing to open. HAY_ALT is the one
copy of "the bot asked how he is": wa_qa.py's rubric and the --watch flag in
check_whatsapp_rules.py read it from here.

A FOURTH, 18 OCT: `unasked`, the mirror of `rephay`. Typed "אני רוצה לדבר עם
מנהל" got "מה שלומך היום? 😊" twice (executions 112521, 112529): the model took
the typed request for the tap. Off the tap, a reply that asks how he is when he
did not ask first goes back once, first pass only, and `Try again` names it. It
reads HAY_STRICT, not HAY_ALT, because "מה המצב" and "מה קורה" also ask about the
matter. n8n_whatsapp_unasked.py carries it to live.

18 OCT, LATE: A CHAT ABOUT A MANAGER. The owner insisted on a manager five times
and got "what is it about?" five times, shorter each time ("like a parrot"). The
first drafts had explained why the details are needed, which is what he wants;
`echo` and `clerk` sent them back and the note said "just ask". MGR_CTX reads the
chat (a request for a manager or a person among the resident's recent messages);
there the two guards pass, `Try again` names neither, and the unnamed list drops
both and the "no reason" tail (RETRY_NOTE_MGR). n8n_whatsapp_procedure.py carries it.

19 OCT: THE BOT REPEATS ITSELF (n8n_whatsapp_norepeat.py carries it). "מה קורה עם
הקריאה שפתחתי?" twice got the same message twice, word for word (114528, 114536); on
another number the second pass sent back the bot's previous message entire (114483).
Four changes here:
  - `repeat`, a guard on BOTH passes (no `$runIndex > 0` way out): a reply that is,
    nearly letter for letter, one of the bot's last three sent messages goes back,
    unless the turn did work (wa_truth.REPEAT_FN says how it reads).
  - The second pass no longer sees the rejected draft. `Forget the draft` (a Chat
    Memory Manager on the same buffer, drawn above the agent so v1 runs it first)
    deletes the first pass's two messages before it runs, so the model is not shown
    a draft the resident never got, nor his message twice, and the turns after it
    remember only what went out. The note says so: a draft was not sent, and what
    was sent before did arrive (FORGET, TRY_WIRE).
  - The tools line names get_request_status beside open_request: the note had sent a
    question about an existing ticket toward opening a new one.
  - MGR_CTX reads the resident's last two messages, not the twelve rows, and a
    pasted לדבר עם נציג glued to other words counts as the tap: one "נציג" no longer
    switches `echo` and `clerk` off for the rest of the chat (114528).

5 OCT, THE SECOND PASS KEEPS WHAT THE FIRST ONE KNEW (n8n_whatsapp_safetynet.py,
which carries this to live). The live run as Assaf: the first pass looked the
mould up, found nothing and said so; its draft was sent back for its opening
("אני מבין ש..."); the second pass could not see the lookup, so its "בדקתי"
failed `deeds`, and the last resort told him a ticket was open. `Try again`
now carries three things besides the note:
  - `first_steps`: the first pass's tools and what they returned. The truth
    guards count them on the second pass, and the note tells the model what
    they returned, so it neither repeats the lookup nor opens a ticket twice.
  - `first_output` and `first_truth_ok`: the first draft and the four truth
    guards' verdict on it (wa_truth.truth_js, the guards' own code). When its
    only fault was style and the second pass fails a truth guard, the first
    draft goes out (`Mend the reply`): a retry for style can never end worse
    than the draft it replaced.
And a truth failure is named like the echo and the clerk: an empty reply, a
ticket claimed with no real number, a link no tool returned, a deed no tool
did. The full list stays for a reason the node cannot see (plural, opener).
`Already retried?`'s yes branch goes to `Claimed a ticket?` now, not straight
to the rescue ticket.

Idempotent. Running it twice reports nothing to do.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import wa_truth as T  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-18sep-before-retry.json")
# 5 Oct: where a second rejection goes (n8n_whatsapp_safetynet.py adds it).
CLAIMED = "Claimed a ticket?"
PLACEHOLDER = "REPLACE_WITH_N8N_WEBHOOK_SECRET"

# On the 240 x 60 grid, at least 200 x 100 clear of every neighbour
# (scripts/n8n_layout.py): Try again below `Still the last word?`, the If
# below `Type for a moment (menu)`.
TRY_POS, RETRIED_POS = [720, 300], [1440, 300]

# A bracketed fact for the model, in the shape of every other note in the
# user turn: what happened, and what fixes it. All five guard reasons are
# named because the Set node cannot tell which one fired. The opener is
# described, not quoted (20 Sep). 1 Oct: the slash reason no longer says
# "singular instead of plural" -- the bot speaks to one person now.
# 19 Oct (n8n_whatsapp_norepeat.py): the rejected draft is no longer in the memory
# the second pass reads (`Forget the draft`), so the note speaks of a draft he never
# got and says that what was sent before did arrive: a model told "your previous
# answer did not go out" while its last visible answer DID go out is a model
# invited to send that one again (114483 sent the bot's previous message back).
# The tools line names the status lookup beside opening a ticket.
NOTE_OPEN = "[טיוטה שכתבת להודעה הזאת לא יצאה לדייר"
TOOLS_LINE = ("מה שקורה קורה רק דרך הכלים: אם יש מה לפתוח, תפתח עכשיו עם open_request "
              "ורק אז תענה, עם המספר שחזר; מצב של קריאה קיימת רק מ-get_request_status; "
              "קישור לתשלום רק מ-get_payment_link.")
SEEN = " ההודעות שכן שלחת לו קודם בשיחה הגיעו אליו, ואין צורך לשלוח אותן שוב."
RETRY_NOTE = (
    NOTE_OPEN + ": או שהודיעה על "
    "קריאה שלא נפתחה, או שנתנה קישור שלא הגיע מכלי, או שהייתה ריקה, או "
    "שפנתה לדייר בלוכסן או בסוגריים, או שחזרה על משפט "
    "הפתיחה של המערכת במקום לענות על מה שכתב, או שסיפרה שבדקת, תיקנת, "
    "החלפת או שלחת משהו בלי שכלי עשה את זה, או שפתחה בהודעה שהבנת אותו "
    "או בסיכום של מה שכתב, או שהסבירה לו למה אתה צריך פרט לפני ששאלה "
    "עליו. " + TOOLS_LINE + " ואם "
    "חסר לך משהו, תשאל עליו בשאלה אחת קצרה, בלי הקדמה ובלי הסבר." + SEEN + "]"
)

BS = chr(92)   # a backslash, built rather than typed (27 Sep)

# The echo and the clerk, as the guards on `Reply usable?` test them. One copy:
# n8n_whatsapp_manners.py builds its `echo` and `clerk` conditions from these.
ECHO_RE = "/(^|[.!?,:]" + BS + "s*)(אני מבין|אני מבינה|הבנתי|שמעתי)" + BS + "s+ש/"
CLERK_RE = "/כדי שאוכל|אצטרך/"

# 27 Sep evening: THE REWRITE NAMES WHAT IT CAN SEE. The note above lists eight
# possible reasons because the Set node cannot tell which guard fired -- and in
# execution 65856 the model, told "one of these eight", deleted a promise and
# sent "אני מבין שיש לכם בעיה עם התאורה..." again on the second pass. But two of
# the eight are READ OFF THE REJECTED TEXT, which is `$json.output` right here.
# When the echo or the clerk is in it, the note says so, and says what to write
# instead; anything else keeps the full list. Described, never quoted. Wrapped:
# a throw here would cost the resident the reply, so it falls back to the list.
WHY_ECHO = ("היא נפתחה בזה שהבנת אותו או בסיכום של מה שכתב, ובמקום זה תגיב לדבר "
            "עצמו במילה או שתיים ומשם ישר לעניין")
WHY_CLERK = "היא הסבירה לו למה אתה צריך פרט לפני ששאלה עליו, ובמקום זה פשוט תשאל"
# 19 Oct: the draft was, nearly word for word, a message he already has (`repeat`).
WHY_REPEAT = ("היא חזרה כמעט מילה במילה על הודעה ששלחת לו כבר והוא כבר קרא, ובמקום זה "
              "תענה על מה שהוא כתב עכשיו, במילים אחרות, ואם אין לך מה להוסיף, תגיד פחות")
NOTE_HEAD = NOTE_OPEN + ", כי "
NOTE_TAIL = ". " + TOOLS_LINE

# 4 Oct: "the bot asked how he is", one copy. Hebrew and English, the forms a
# person uses; no apostrophes (`.` stands in), so it sits in an n8n expression
# as safely as in Python. The `rephay` guard and `Try again` use HAY_JS;
# wa_qa.py's rubric and the --watch flag use HAY_PY.
# 5 Oct evening: "איך עבר עליך היום?" (how has your day been) -- the evening form
# of the "today" the owner asked for -- was missing, and the guard sent a right
# reply back (the Claude-played check of n8n_whatsapp_hayday.py).
HAY_ALT = (r"מה שלומ|מה נשמע|מה קורה|מה העניינים|מה המצב|מה איתך|איך הולך|איך עובר|איך עבר|איך היום"
           r"|איך אתה|איך את(?=[\s,.!?]|$)"
           r"|how are you|how is it going|how.s it going|how is your day|how.s your day"
           r"|how was your day|how has your day"
           r"|how are things|what.?s up|wassup")
HAY_JS = "/" + HAY_ALT + "/i"
HAY_PY = __import__("re").compile(HAY_ALT, __import__("re").I)
WHY_REPHAY = ("היא לא שאלה אותו לשלומו, ובלחיצה על לדבר עם נציג הנציג שנכנס לשיחה אומר היי, "
              "אומר מי הוא ושואל מה שלומו, וזאת השאלה היחידה בהודעה")

# 18 Oct: "how are you" nobody asked for (n8n_whatsapp_unasked.py). The owner typed
# "אני רוצה לדבר עם מנהל" and got "מה שלומך היום? 😊" twice (executions 112521 and
# 112529): the model answered the typed request as the לדבר עם נציג tap, and Send's
# greeting filter left only the question. The prompt says only the resident opens
# that door, the tap aside; `unasked` backs it. HAY_STRICT is narrower than HAY_ALT
# on purpose: "מה קורה", "מה המצב" and "מה העניינים" also ask about the matter ("ספר
# לי מה המצב"), and "איך אתה" also starts "איך אתה מעדיף לשלם". Over the 1,050 bot
# replies so far it would have sent back exactly those two.
HAY_STRICT = (r"מה שלומ|מה נשמע|מה איתך|איך עובר עלי|איך עבר עלי|איך היום|איך הולך לך"
              r"|איך הולך(?=[?!.,]|$)|איך אתה(?=[?!.,]|$)|איך את(?=[?!.,]|$)"
              r"|how are you|how.s it going|how is it going|how.s your day|how is your day"
              r"|how was your day|how has your day")
HAY_STRICT_JS = "/" + HAY_STRICT + "/i"
HAY_STRICT_PY = __import__("re").compile(HAY_STRICT, __import__("re").I)
WHY_UNASKED = ("היא שאלה אותו לשלומו, והוא לא שאל אותך לשלומך ולא לחץ על לדבר עם נציג, "
               "ובמקום זה תמשיך ממה שהוא כתב לך")

# 18 Oct, late (n8n_whatsapp_procedure.py): THE CHAT IS ABOUT A MANAGER. The owner's
# handset, 15:05-15:08 UTC (executions 112601-112635): five turns of "what is it
# about?", each shorter than the last -- "this is like frustrating like a parrot it
# should be like i understand you i order for me to do that blah blah blah its the
# procedure we need to get information before we can do something". The first
# drafts said exactly that ("אני מבין שחשוב לך לדבר עם מנהל. כדי שאוכל לוודא שהפנייה
# שלך מגיעה לאדם הנכון..., אני צריך להבין מה המצב"); `echo` and `clerk` sent them
# back, and the rewrite was the bare question every time. So while the chat is
# about a request for a manager or a person, "I understand you" and the reason for
# asking are the answer, not a fault, and the note does not ask for a bare question.
# Read off the resident's own messages among the last twelve rows (`Anything
# newer?`, both directions, this message among them), the לדבר עם נציג tap's own
# row aside (it opens "hi, how are you today"); off this turn's text when the rows
# cannot be read. No lookbehind and no backslash: it sits in n8n expressions.
# Over the 1,055 bot replies so far it covers the two of 18 Oct 15:05 and 15:06,
# the 18 Oct 13:25 and 5 Oct 12:29 / 12:34 person requests, and nothing else.
MGR_ALT = (r"מנהל|אחראי|נציג|בן אדם|בנאדם|אדם אמיתי|מישהו מהצוות|מישהו אמיתי"
           r"|manager|supervisor|representative|human(?![a-z])|person(?![a-z])|(^|[^a-z])agent(?![a-z])")
MGR_JS = "/" + MGR_ALT + "/i"
MGR_PY = __import__("re").compile(MGR_ALT, __import__("re").I)
TAP_REP = "לדבר עם נציג"
# 19 Oct (n8n_whatsapp_norepeat.py): THE RESIDENT'S LAST TWO MESSAGES, NOT TWELVE
# ROWS. At 11:38 a pasted "לדבר עם נציג" glued to a question about a ticket made the
# chat "about a manager" (114528), and the row stayed among the twelve for the next
# turn (114536): "אני מבין שאתה רוצה לברר..." went out twice with the echo guard
# standing aside. Now: this message and the one before it (the first two inbound
# rows, newest first), each with a leading tap text taken off, so the exemption
# lasts while he is asking for a person and ends when the chat moves on. A
# follow-up with no manager word ("למה שאספר לך?") still counts: the message before
# it asked.
MGR_CTX = ("let mgrAsk = false; const mgrSaid = (s) => { const b = String(s || '').trim()"
           ".replace(/^" + TAP_REP + "/, '').trim(); return b !== '' && " + MGR_JS + ".test(b); }; "
           "try { const rows = $('Anything newer?').all().map(r => (r || { }).json || { })"
           ".filter(x => x.direction === 'inbound').slice(0, 2); "
           "mgrAsk = rows.some(x => mgrSaid(x.body)); } catch (e) { mgrAsk = false; } "
           "if (!mgrAsk) { try { mgrAsk = mgrSaid($('Still the last word?').first().json.text); } "
           "catch (e) { mgrAsk = false; } } ")
assert "}}" not in MGR_CTX, "a }} inside the manager test ends an expression early"


def mgr_py(texts):
    """MGR_CTX in Python, for --watch and wa_qa: `texts` are the resident's
    messages, newest first; the first two decide, a leading tap text taken off."""
    import re
    for s in list(texts)[:2]:
        b = re.sub("^" + re.escape(TAP_REP), "", str(s or "").strip()).strip()
        if b and MGR_PY.search(b):
            return True
    return False
# ...except when the same reply makes a promise. The replay of 112626's first draft
# ("כדי שאוכל לעדכן את הצוות ולדאוג שיחזרו אליך, מה הנושא...?") found it: let through, Send
# cuts the promise's sentence and leaves "I understand you want a manager." with no
# question, and the backstop notes an empty request. `echo` and `clerk` caught it
# before; with a promise they still do, and the note names the promise. The phrases
# are Send's (n8n_whatsapp_nopromise.PHRASES, which asserts this copy is the same:
# nopromise imports manners, which imports this, so it cannot be imported here).
PROMISE_PHRASES = ("בהקדם|בקרוב|בימים הקרובים|בשעות הקרובות|בהמשך היום|במהרה|במהירות האפשרית|"
                   "אנחנו על זה|אני על זה|"
                   "אני כבר מטפל בזה|אני מטפל בזה|מטפל בזה מיד|אני אטפל בזה|"
                   "(יחזרו|יחזור|תחזור|נחזור|אחזור) (אליכם|אלייך|אליך)|"
                   "(ייצרו|יצרו|ייצור|יצור|ניצור|תיצור) ((אתכם|איתכם|איתך|אתך) קשר|קשר (אתכם|איתכם|איתך|אתך))|"
                   "(יעדכנו|יעדכן|נעדכן|אעדכן) (אתכם|אותך)|"
                   "בדרך (אליכם|אליך|אלייך)|(עזרה|מישהו|הצוות|הטכנאי) בדרך|"
                   "הטכנאי יגיע|מישהו יגיע|(נשלח|ישלחו) ((אליכם|אליך|אלייך) )?(מישהו|טכנאי)|"
                   "יגיעו? (אליכם|אליך|אלייך|בקרוב|היום|מחר)")
PROMISE_JS = "/" + PROMISE_PHRASES + "/"
WHY_PROMISE = ("היא הבטיחה לו שיחזרו אליו, שיטפלו בזה או מתי, ואת זה אתה לא יודע, "
               "ובמקום זה תגיד רק מה שאתה כן יודע")
# The full list, when nothing can be named, without the two reasons the chat about
# a manager does not have, and without "ask it in one short question, no reason".
RETRY_NOTE_MGR = (
    NOTE_OPEN + ": או שהודיעה על "
    "קריאה שלא נפתחה, או שנתנה קישור שלא הגיע מכלי, או שהייתה ריקה, או "
    "שפנתה לדייר בלוכסן או בסוגריים, או שחזרה על משפט "
    "הפתיחה של המערכת במקום לענות על מה שכתב, או שסיפרה שבדקת, תיקנת, "
    "החלפת או שלחת משהו בלי שכלי עשה את זה. " + TOOLS_LINE + SEEN + "]"
)

# 5 Oct: the four truth guards, named when they are the reason. Read off the
# first draft with the guards' own code (wa_truth.truth_js), not guessed.
WHY_WORDS = "היא הייתה ריקה"
WHY_PHANTOM = "היא אמרה שנפתחה קריאה, ובתור הזה לא נפתחה שום קריאה ולא חזר מספר"
WHY_LINKS = "היא נתנה קישור שלא הגיע מכלי"
WHY_DEEDS = "היא סיפרה שבדקת, שלחת, תיקנת או טיפלת במשהו, ושום כלי לא עשה את זה בתור הזה"
# 5 Oct: what the first pass's tools returned, as a fact in the same brackets.
# Without it the second pass lost the lookup it was answering from.
FACTS_HEAD = "[מה שהכלים כבר החזירו לך בתור הזה, לפני הטיוטה שנפסלה: "
FACTS_TAIL = ". זה כבר קרה, ואפשר לענות לפיו; קריאה שכבר נפתחה לא פותחים שוב.]"

# `}}` anywhere inside ends an n8n expression, so the braces are spaced.
# 4 Oct: the representative tap's missing how-are-you is named too. The tools
# line rides on the echo, the clerk and (5 Oct) any truth reason; a note that
# names the tap alone ends there, because a tap opens nothing.
# 5 Oct: besides the note, `first_steps`, `first_output` and `first_truth_ok`
# (the docstring says why). A throw leaves the full list and a verdict of "not
# true", so the last resort mends the second draft rather than trusting the first.
TRY_JSON = (
    "={{ JSON.stringify(Object.assign({ }, $('Still the last word?').first().json, (() => { "
    "const o = String($json.output || ''); try { " + T.LIB + T.REPEAT_FN +
    "const first_steps = stepsOf($json.intermediateSteps); "
    + T.truth_js("o", "first_steps", T.FIRST_WORDS) +
    "const why = []; "
    "if (!v.words) why.push('" + WHY_WORDS + "'); "
    "if (!v.phantom) why.push('" + WHY_PHANTOM + "'); "
    "if (!v.links) why.push('" + WHY_LINKS + "'); "
    "if (!v.deeds) why.push('" + WHY_DEEDS + "'); "
    # 19 Oct: a copy of a message he already got is named, as the `repeat` guard
    # reads it (not when the turn did work: the guard stood aside there).
    "const workedRep = o.indexOf('§§§') !== -1 || first_steps.some(s => s.tool === 'notify_team' "
    "|| s.tool === 'get_payment_link' || (s.tool === 'open_request' && !/opened" + BS + "W{1,6}false/"
    ".test(String(s.observation || '')))); "
    "if (!workedRep && repeats(o)) why.push('" + WHY_REPEAT + "'); "
    # 18 Oct, late: in a chat about a manager, the echo and the clerk are the answer.
    + MGR_CTX +
    "if (!mgrAsk && " + ECHO_RE + ".test(o)) why.push('" + WHY_ECHO + "'); "
    "if (!mgrAsk && " + CLERK_RE + ".test(o)) why.push('" + WHY_CLERK + "'); "
    "const tools = why.length > 0; let rep = false; "
    "try { rep = $('Still the last word?').first().json.tap === 'other'; } catch (e) { rep = false; } "
    "if (rep && !" + HAY_JS + ".test(o)) why.push('" + WHY_REPHAY + "'); "
    # 18 Oct: a how-are-you he did not ask for, off the tap, is named too.
    # `wrote`, not `said`: the truth library above already declares `said`.
    "let wrote = ''; try { wrote = String($('Still the last word?').first().json.text || ''); } catch (e) { wrote = ''; } "
    "if (!rep && " + HAY_STRICT_JS + ".test(o) && !" + HAY_JS + ".test(wrote)) why.push('" + WHY_UNASKED + "'); "
    # 18 Oct, late: in a chat about a manager a promise is what sent it back.
    "if (mgrAsk && " + PROMISE_JS + ".test(o)) why.push('" + WHY_PROMISE + "'); "
    "let note = why.length ? '" + NOTE_HEAD + "' + why.join('. וגם ') + (tools ? '" + NOTE_TAIL + "' : '.') + '" + SEEN + "]' "
    ": (mgrAsk ? '" + RETRY_NOTE_MGR + "' : '" + RETRY_NOTE + "'); "
    "if (first_steps.length) note += ' " + FACTS_HEAD + "' + first_steps.map(s => s.tool + ': ' + brief(s.observation)).join('; ') + '" + FACTS_TAIL + "'; "
    "return { retry_note: note, first_output: o, first_steps, first_truth_ok: v.ok }; "
    "} catch (e) { return { retry_note: '" + RETRY_NOTE + "', first_output: o, first_steps: [], first_truth_ok: false }; } "
    "})())) }}"
)
assert TRY_JSON.count("}}") == 1, "a }} inside Try again ends its expression early"

RETRIED = "={{ $runIndex > 0 }}"

# The two style guards (20 Sep), as conditions on `Reply usable?`. Each is
# true (usable) on the retry pass whatever the text says: a style fault on
# the second attempt goes out rather than becoming a stub ticket.
#
# `plural`: a gendered slash or bracket form -- ספר/י, תרצה/י, ספר(י),
# מוזמן/ת, and the full-word kind the third live probe produced, ספר/ספרי,
# where the second word is the first word's stem plus a suffix (the
# backreference). Two Hebrew letters before the slash keep ו/או and 20/9
# out; the stem and the boundary after keep בניין/דירה and קריאה/תקלה out.
# The letter after the backreference is for final forms: מוזמן/מוזמנת has ן
# on one side and נ on the other.
PLURAL = (r"={{ $runIndex > 0 || !/([א-ת]{2,})[א-ת]?(\/|\()(\1[א-ת]?)?(י|ה|ת|נה|ו|ות)\)?(?=[\s,.!?:;)]|$)/"
          r".test(String($json.output || '')) }}")
# The shape of a bare "how can I help" turn: a hello, the name or not, "how
# can I help", nothing else. One source, two uses: the `opener` guard below
# and Send's third menu rule.
# 23 Sep: the workflow's own opener greets by the hour, so בוקר טוב /
# צהריים טובים / ערב טוב are openers too. Without them the clock greeting
# stops being recognised as the turn the resident has already had, and the
# guard quietly protects nothing -- the same failure n8n_whatsapp_rename.py
# records for Send's echo tests.
# 1 Oct: "לך היום" beside "לכם היום" -- the bot addresses one person now,
# and the singular shape has to count as the opener the plural one did.
OPENER_RE = (r"/^(היי|הי|שלום|שלום רב|אהלן|בוקר טוב|צהריים טובים|ערב טוב)[,!.]?"
             r"( (כאן |אני )?מיכאל מהומי'ז( כאן)?[.,!]?)?"
             r" ?במה (אפשר|אוכל|נוכל) לעזור( לכם| לך| לכם היום| לך היום)?\??$/")
STRIP = r".replace(/[\p{Extended_Pictographic}️]/gu, '').replace(/\s+/g, ' ').trim()"
# `opener`: the whole reply is that shape -- the turn the resident has
# already had -- on a message that was not a bare hello (a bare hello never
# reaches this node; the canned menu answers it). Emoji and the variation
# selector come off first, as in Sort.
# 23 Sep, epoch 54: `tap === 'other'` is exempt, and that is the owner's
# instruction turned into a guard. He read the נציג reply -- "ספרו לי בבקשה מה
# העניין" -- and said *"it already assume there is a problem. i want it to ask
# how can he help."* So the prompt now asks for exactly the sentence this guard
# was built to catch: a greeting, the name, and "במה אוכל לעזור?", nothing else.
# On any other message that shape is still the failure it always was -- the
# resident said something concrete and got the opener recited back. On the נציג
# tap it is the CORRECT reply, because the resident said nothing to continue
# from: the tap carries no content beyond "I want a person". Narrow on purpose,
# `tap` and not `tapped_human`: `tap` is this message's own row (Sort's
# "carried for readback"), so the exemption lasts exactly one turn and the
# guard is live again on the next.
OPENER = (r"={{ $runIndex > 0 || $('Sort').first().json.greeting === true"
          r" || $('Sort').first().json.tap === 'other' || (() => {"
          r" const t = String($json.output || '')" + STRIP + ";"
          r" return !" + OPENER_RE + ".test(t); })() }}")

# Send's third menu rule said: the name on an ungreeted handset means the
# intro, so attach the buttons. Written 2 Sep, when the model's first-contact
# reply was the opener and nothing else. Now the prompt asks for the name
# AND a question about the matter on first contact, and the owner's rule is
# buttons only when nothing concrete was said -- so the rule fired on a good
# reply ("היי, בוקר טוב! אני מיכאל מהומי'ז. ספרו לי מה קרה ואיפה", probe
# 50915) and contradicted the decision. Narrowed: the name on an ungreeted
# handset attaches the buttons only when the reply is the bare opener shape,
# which after the `opener` guard means a second-pass recital -- the last
# resort. The verbatim-echo test and the show_menu call before it are
# untouched, and n8n_whatsapp_greet.py stays idle: its anchor is the echo.
# Send's second menu rule -- the options written out in words -- matched four
# exact strings, and the model writes "קריאות שירות", "יתרות", "תשלומים"
# (probes 50930, 50932: the options listed in a paragraph, show_menu not
# called, no buttons). Categories instead of strings: three of the five in
# one reply is a list. A ticket confirmation, a balance, a payment link and
# a status answer each touch one category, two at most.
FILTER_OLD = ("['קריאת שירות', 'קריאה קיימת', 'יתרה', 'נציג']"
              ".filter(w => t.indexOf(w) !== -1).length >= 3 || ")
FILTER_NEW = ("[/קריא(ת|ות) שירות|תקל/, /קריא(ה|ות) קיימ|מצב (ה)?קריא/, /יתר(ה|ות)|תשלומ/, "
              "/נציג|בן אדם/, /מידע כללי|השירותים ש/]"
              ".filter(r => r.test(t)).length >= 3 || ")
SEND_TAIL_OLD = "(/מיכאל מהומי'ז/.test(t) && $('Sort').first().json.greeted !== true))"
SEND_TAIL_NEW = ("(/מיכאל מהומי'ז/.test(t) && $('Sort').first().json.greeted !== true && "
                 + OPENER_RE + ".test(t" + STRIP + ")))")


def guard(gid, expr):
    return {"id": gid, "leftValue": expr, "rightValue": "",
            "operator": {"type": "boolean", "operation": "true", "singleValue": True}}


# `rephay` (4 Oct): on the לדבר עם נציג tap's own turn, the reply asks how he is,
# or it goes back once. First pass only, like the two above.
REPHAY = (r"={{ $runIndex > 0 || $('Sort').first().json.tap !== 'other' || "
          + HAY_JS + r".test(String($json.output || '')) }}")

# `unasked` (18 Oct, n8n_whatsapp_unasked.py): a reply that asks how he is, when he
# did not ask first and this is not the לדבר עם נציג tap, goes back once. First
# pass only, like the three above. The resident's words are read where Try again
# reads them; a throw counts as "he did not ask".
UNASKED = (r"={{ $runIndex > 0 || $('Sort').first().json.tap === 'other' || (() => { "
           r"let said = ''; try { said = String($('Still the last word?').first().json.text || ''); } "
           r"catch (e) { said = ''; } return " + HAY_JS + r".test(said) || !" + HAY_STRICT_JS
           + r".test(String($json.output || '')); })() }}")
assert UNASKED.count("}}") == 1, "a }} inside `unasked` ends its expression early"

# A turn that did work (a ticket opened, a note, a link, the two-beat): the style
# guards stand aside, because the second pass sees none of it (CONTEXT, "Sending a
# reply back is only safe when the turn did no work"). One copy: manners.py's
# `echo` and `clerk` are built from this string, byte for byte as before 19 Oct.
WORKED = ("const t = String($json.output || ''); const steps = $json.intermediateSteps || []; "
          "const worked = t.indexOf('§§§') !== -1 || steps.some(s => { const k = ((s.action || {}).tool) || ''; "
          "return k === 'notify_team' || k === 'get_payment_link' || (k === 'open_request' "
          "&& !/opened" + BS + "W{1,6}false/.test(String(s.observation || ''))); }); if (worked) return true;")

# `repeat` (19 Oct, n8n_whatsapp_norepeat.py): a reply that is, nearly letter for
# letter, one of the bot's last three sent messages goes back, on EITHER pass: no
# `$runIndex > 0` way out, because the second pass is where 114483 sent the previous
# message back. A turn that did work is exempt like the other style guards. After
# two rejections `Mend the reply` never sends a copy either (wa_truth.mend_expr).
REPEAT = "={{ (() => { " + WORKED + " " + T.REPEAT_FN + "return !repeats(t); })() }}"
assert REPEAT.count("}}") == 1, "a }} inside `repeat` ends its expression early"

PLURAL_GUARD = guard("plural", PLURAL)
OPENER_GUARD = guard("opener", OPENER)
REPHAY_GUARD = guard("rephay", REPHAY)
UNASKED_GUARD = guard("unasked", UNASKED)
REPEAT_GUARD = guard("repeat", REPEAT)

# `Forget the draft` (19 Oct): a Chat Memory Manager on the same buffer as the
# agent, fed by `Try again` beside `Answer the resident` and drawn above it, so
# executionOrder v1 runs it first. It deletes the last two messages of the buffer:
# the first pass's human turn and the draft the resident never got. Without it the
# second pass read its own rejected draft as the last exchange and the turns after
# it remembered a reply that was never sent (112609's memory held one; 114483 copied
# one back). The memory sub-node's key reads `$json.to`, which Try again's item
# carries. `continueRegularOutput`: a failure here must not cost the resident the
# reply; it only means the draft stays in memory, as it did before.
FORGET = "Forget the draft"
# On the 240 x 60 grid (n8n_layout.py), above `Answer the resident` [960, 64]
# and clear of `Anything newer?` [620, 64] and `Show typing` [720, -360].
FORGET_POS = [720, -120]
MEMORY = "Conversation so far"


def forget_node():
    return {
        "id": "forget_draft", "name": FORGET,
        "type": "@n8n/n8n-nodes-langchain.memoryManager", "typeVersion": 1.1,
        "position": list(FORGET_POS), "onError": "continueRegularOutput",
        "parameters": {"mode": "delete", "deleteMode": "lastN", "lastMessagesCount": 2},
    }


def forget_problems(nodes, conns):
    """What is wrong with `Forget the draft` on a workflow; empty when right. The
    carrier runs it before any write and check_whatsapp_rules.py on live."""
    by = {n["name"]: n for n in nodes}
    out = []
    n = by.get(FORGET)
    if n is None:
        return ["%s is missing" % FORGET]
    want = forget_node()
    for k in ("type", "typeVersion", "parameters", "onError"):
        if n.get(k) != want[k]:
            out.append("%s: %s is %r, not %r" % (FORGET, k, n.get(k), want[k]))
    if any(t for b in (conns.get(FORGET) or {}).get("main") or [] for t in b or []):
        out.append("%s feeds other nodes; it has to be a side branch" % FORGET)
    kids = [t["node"] for t in ((conns.get("Try again") or {}).get("main") or [[]])[0] or []]
    if FORGET not in kids:
        out.append("%s is not fed by Try again" % FORGET)
    if "Answer the resident" not in kids:
        out.append("Try again no longer feeds Answer the resident")
    mine = n.get("position") or [0, 0]
    for k in kids:
        pos = (by.get(k) or {}).get("position")
        if k != FORGET and pos and (pos[1], pos[0]) <= (mine[1], mine[0]):
            out.append("%s is drawn below %s under Try again, so it would run after it" % (FORGET, k))
    mem = [t["node"] for b in ((conns.get(MEMORY) or {}).get("ai_memory") or []) for t in b or []]
    if FORGET not in mem:
        out.append("%s is not on %s's memory" % (FORGET, MEMORY))
    if "Answer the resident" not in mem:
        out.append("Answer the resident is no longer on %s's memory" % MEMORY)
    return out


def snapshot(live):
    if os.path.exists(SNAPSHOT):
        return False
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    live = dict(live, staticData="<stripped: runtime state keyed by phone numbers>")
    text = json.dumps(live, ensure_ascii=False, indent=1)
    if secret:
        if secret not in text:
            sys.exit("The live workflow does not contain N8N_WEBHOOK_SECRET from .env, "
                     "so the snapshot's redaction would miss. Refusing to write it.")
        text = text.replace(secret, PLACEHOLDER)
    with open(SNAPSHOT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return True


def restore():
    snap = json.load(open(SNAPSHOT, encoding="utf-8"))
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    if not secret:
        sys.exit("N8N_WEBHOOK_SECRET is not in .env; the snapshot's Sort node would "
                 "go live with a placeholder secret. Refusing.")
    body = json.loads(json.dumps(snap, ensure_ascii=False).replace(PLACEHOLDER, secret))
    W.api("PUT", "/api/v1/workflows/%s" % WORKFLOW_ID, {
        "name": body["name"], "nodes": body["nodes"],
        "connections": body["connections"], "settings": body.get("settings", {})})
    print("restored %s from %s (%d nodes)" % (WORKFLOW_ID, SNAPSHOT, len(body["nodes"])))


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes = live["nodes"]
    by = {n["name"]: n for n in nodes}
    conns = live["connections"]
    # 5 Oct: `Say it again` is gone; a second rejection goes to `Claimed a
    # ticket?`, which n8n_whatsapp_safetynet.py adds. Until it has, this script's
    # wiring would point at nothing, so it refuses rather than write it.
    for need in ("Reply usable?", "Open it anyway", "Still the last word?",
                 "Answer the resident", "Send", CLAIMED):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess%s." % (
                need, " (python scripts/n8n_whatsapp_safetynet.py --apply adds it)" if need == CLAIMED else ""))

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    changes = []

    # --- The two new nodes --------------------------------------------------
    if "Try again" not in by:
        nodes.append({
            "id": "try_again", "name": "Try again",
            "type": "n8n-nodes-base.set", "typeVersion": 3.4,
            "position": TRY_POS,
            "parameters": {"mode": "raw", "jsonOutput": TRY_JSON, "options": {}},
        })
        changes.append("Try again: new node, the same message back to the agent "
                       "with a note on it")
    else:
        p = by["Try again"]["parameters"]
        if p.get("jsonOutput") != TRY_JSON:
            p["jsonOutput"] = TRY_JSON
            changes.append("Try again: note updated")

    if "Already retried?" not in by:
        nodes.append({
            "id": "already_retried", "name": "Already retried?",
            "type": "n8n-nodes-base.if", "typeVersion": 2,
            "position": RETRIED_POS,
            "parameters": {"conditions": {
                "options": {"caseSensitive": True, "leftValue": "",
                            "typeValidation": "loose"},
                "conditions": [{
                    "id": "retried", "leftValue": RETRIED, "rightValue": "",
                    "operator": {"type": "boolean", "operation": "true",
                                 "singleValue": True},
                }],
                "combinator": "and",
            }},
        })
        changes.append("Already retried?: new node, one retry and then the stub")

    # --- Forget the draft (19 Oct) --------------------------------------------------
    if FORGET not in by:
        nodes.append(forget_node())
        by[FORGET] = nodes[-1]
        changes.append("%s: new node, the first pass's two messages out of the buffer "
                       "before the second pass" % FORGET)
    else:
        want = forget_node()
        for k in ("parameters", "onError", "type", "typeVersion"):
            if by[FORGET].get(k) != want[k]:
                by[FORGET][k] = want[k]
                changes.append("%s: %s updated" % (FORGET, k))
    mem = conns.setdefault(MEMORY, {}).setdefault("ai_memory", [[]])
    if not any(t.get("node") == FORGET for t in mem[0]):
        mem[0].append({"node": FORGET, "type": "ai_memory", "index": 0})
        changes.append("%s -> %s (memory)" % (MEMORY, FORGET))

    # --- The style guards, by id (20 Sep; `repeat` 19 Oct) --------------------------
    cond = by["Reply usable?"]["parameters"]["conditions"]["conditions"]
    for g in (PLURAL_GUARD, OPENER_GUARD, REPHAY_GUARD, UNASKED_GUARD, REPEAT_GUARD):
        have = next((c for c in cond if c.get("id") == g["id"]), None)
        if have is None:
            cond.append(dict(g))
            changes.append("Reply usable?: `%s` guard added, first pass only" % g["id"])
        elif have.get("leftValue") != g["leftValue"]:
            have["leftValue"] = g["leftValue"]
            changes.append("Reply usable?: `%s` guard updated" % g["id"])

    # --- Send's third menu rule, narrowed to the bare opener shape (20 Sep) ------
    sbody = by["Send"]["parameters"].get("jsonBody") or ""
    if SEND_TAIL_NEW not in sbody:
        if sbody.count(SEND_TAIL_OLD) != 1:
            sys.exit("REFUSING: Send.jsonBody does not carry the menu rule this script "
                     "knows (found %d). Read the live body before touching it."
                     % sbody.count(SEND_TAIL_OLD))
        by["Send"]["parameters"]["jsonBody"] = sbody.replace(SEND_TAIL_OLD, SEND_TAIL_NEW, 1)
        changes.append("Send: the name-on-first-contact menu rule fires only on the "
                       "bare opener shape")
    sbody = by["Send"]["parameters"].get("jsonBody") or ""
    if FILTER_NEW not in sbody:
        if sbody.count(FILTER_OLD) != 1:
            sys.exit("REFUSING: Send.jsonBody does not carry the option-words net this "
                     "script knows (found %d). Read the live body before touching it."
                     % sbody.count(FILTER_OLD))
        by["Send"]["parameters"]["jsonBody"] = sbody.replace(FILTER_OLD, FILTER_NEW, 1)
        changes.append("Send: the options-written-out net reads categories, not four "
                       "exact strings")

    # --- Wiring ------------------------------------------------------------------
    ru = conns.setdefault("Reply usable?", {}).setdefault("main", [[], []])
    while len(ru) < 2:
        ru.append([])
    want_false = [{"node": "Already retried?", "type": "main", "index": 0}]
    if ru[1] != want_false:
        ru[1] = want_false
        changes.append("Reply usable? (false) -> Already retried? (was Open it anyway)")

    want_retried = {"main": [
        [{"node": CLAIMED, "type": "main", "index": 0}],
        [{"node": "Try again", "type": "main", "index": 0}],
    ]}
    if conns.get("Already retried?") != want_retried:
        conns["Already retried?"] = want_retried
        changes.append("Already retried? -> %s (yes) / Try again (no)" % CLAIMED)

    want_try = {"main": [[{"node": FORGET, "type": "main", "index": 0},
                          {"node": "Answer the resident", "type": "main", "index": 0}]]}
    if conns.get("Try again") != want_try:
        conns["Try again"] = want_try
        changes.append("Try again -> %s (first, drawn above) and Answer the resident" % FORGET)

    if not changes:
        print("\nNothing to do. Live already matches.")
        return

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    print("\nchanges:")
    for c in changes:
        print("  - %s" % c)

    # 5 Oct evening: the would-be workflow for the gate, as the other patchers do.
    if "--dump" in sys.argv:
        import n8n_whatsapp_nopromise as NP
        path = sys.argv[sys.argv.index("--dump") + 1]
        NP.dump(live["nodes"], live["connections"], path)
        print("\ndumped   : %s (the would-be workflow, secret replaced)" % path)

    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": live["nodes"],
        "connections": live["connections"], "settings": live.get("settings", {}),
    })
    print("\nwritten. Re-run without --apply to confirm it reports nothing to do; "
          "the agent reads retry_note only once n8n_whatsapp_teamnote.py --apply "
          "has written AGENT_NEW (epoch 48).")


if __name__ == "__main__":
    main()
