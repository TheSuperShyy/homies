"""Yariv's section 6 (docs/discovery/yariv-alignment-2026-10.md), applied ONLY
to the sandbox copy of the WhatsApp bot (feature 19):
  A. no representative button: the menu in Sort and the copy Send re-attaches
     after a "how can I help" both have two buttons, and the prompt passages
     about the third one are removed. A typed request for a person keeps the
     18 Oct rule already in the prompt: help first, then the matter, and the
     team only for what is beyond the bot. Every node that reacted to the tap
     keys on Sort's `tap === 'other'`, which can no longer happen, so they are
     left as they are.
  B. the sender recognised from Homies' records: "Who is writing?" reads
     `residents` by phone, "Add who" adds a bracket fact, and WHO_RULE tells
     the model not to ask. It opens the ticket and says in the same message where
     it was filed, so the tenant can correct it (the owner, 27 Oct, over a
     confirmation question the model skipped twice). "Where" alone left the flat
     out of a lift ticket (28 Oct), so the rule names the flat the ticket is
     recorded on, apart from where the fault is. The ticket tool's "ask for
     the flat every time" gets one sentence for the recognised case, so the rule
     and the tool do not compete. The balance keeps its typed name and phone.
  C. the bot solves it, the team gets a note (the owner, 27 Oct, on a sandbox chat
     where "I need a manager … it's about the committee fee" ended in "I updated
     the management team, anything else?"): *"we should handle everything in our
     own we dont rely on anyone but we do keep a note for the team if ever there
     is such a conflict like this"*. The committee FEE leaves the "only staff can
     finish" list (the people on the committee stay on it), and a manager request
     becomes: find out what it is, handle it, and leave the team a note because a
     manager was asked for, while the same message carries on with the matter.
     The owner's next chat the same day ("it still did not resolve with it self it
     should fix everything for himself"): after the note, "meanwhile, maybe I can
     help?", and to "no you cant help me for this one", "the team knows and will
     handle it". The way out was "only what is beyond you stays with the team, and
     then you tell him the team knows", which his word alone satisfied. It is gone:
     the bot is not a stop on the way to a manager, a topic still needs what is
     going on, and "you can't help" gets what the bot can do with it and a question.
     The retest (12:24 UTC) still ended "רשמתי את זה עכשיו לצוות שלנו שיבדקו. יש עוד
     משהו שאפשר לעשות מפה בינתיים?". The prompt was not what Gemini followed:
     notify_team's own description, read at the moment of the call, said "call it
     only for what is really past you" and "afterwards: that you have let the team
     know ... and what you can still do for them now". So NOTE_EDITS bring the
     tool in line, and the reason the bot gives for asking stops being "before it
     goes to a manager" / "nothing to pass on", which had it promising to forward
     the request ("I immediately write it down for the relevant team") and then
     keeping that promise.
     Then, the same evening, the owner's protocol (see MANAGER_RULE): never
     gatekeep or concede; management is told at once; the bot asks for the details
     and the concern so it can be sorted faster, warmly, and handles it itself.
  D. one reply per burst (the owner's sandbox chat, 27 Oct, "is there a way to fix
     this"): a second message sent while the AI was writing got its own answer,
     and two near-identical replies went out half a second apart. The live bot
     checks for a newer message only BEFORE the model (about 4 s after the
     message); the copy checks again right before Send. This one is not
     section 6: it is a live behaviour, fixed in the sandbox first.
Every edit asserts that its anchor occurs exactly once, so a changed live prompt
fails loudly instead of being half-edited.
"""
import copy, uuid
from n8n_sandbox import free_spot, replace_once

WHO_RULE = (
    "לפעמים כתוב לך בסוגריים שהפונה מזוהה במערכת, עם השם, הבניין והדירה שלו. זה מידע אמין מהרשומות של הומי'ז, "
    "ולכן אתה לא מבקש ממנו שם, בניין או דירה: מבחינתך הוא כבר אמר לך אותם, ואתה מעביר אותם לכלי. כשאתה פותח לו "
    "קריאה, אתה לא שואל אם זה המקום. אתה אומר לו באותה הודעה באיזה בניין פתחת אותה ועל איזו דירה רשמת אותה, כמו "
    "\"פתחתי קריאה על המעלית בהרצל 10, ורשמתי אותה על דירה 4\", כדי שיוכל לתקן אותך אם משהו לא נכון. אם כתובות לו כמה דירות, אתה שואל באיזו מהן "
    "מדובר. אם הוא מספר על בניין אחר, ממשיכים לפי מה שהוא אומר. רק היתרה נשארת כמו שהיא: הכלי של היתרה עדיין "
    "צריך שם מלא וטלפון, ואותם אתה שואל.")

PROMPT_CUTS = [
    (" וגם כשהוא כותב שהוא רוצה נציג, זאת לא הלחיצה על הכפתור: הוא כבר אמר מה הוא רוצה, ומשם ממשיכים.", ""),
    (", חוץ מהלחיצה על \"לדבר עם נציג\" שעליה תקרא בהמשך,", ","),
    ("את הדלת הזאת רק הוא פותח, חוץ מאותה לחיצה על \"לדבר עם נציג\":", "את הדלת הזאת רק הוא פותח:"),
    ("\"פתיחת קריאת שירות\", \"מצב קריאה קיימת\" או \"לדבר עם נציג\".", "\"פתיחת קריאת שירות\" או \"מצב קריאה קיימת\"."),
    ("שני הראשונים אומרים לך מה הוא רוצה", "שניהם אומרים לך מה הוא רוצה"),
    ("ולכן בלחיצה על אחד משני הראשונים הברכה כבר ניתנה", "ולכן בלחיצה על אחד מהם הברכה כבר ניתנה"),
]
# C. The bot handles it; management is told at once (the owner, 27 Oct, evening: "we dont concede we
# say the management is being informed but i would need your details and concerns so that we can
# resolve [it] faster ... the behavior and attitude is really important"). The live manager passage,
# from MANAGER_FROM to MANAGER_TO, is replaced whole by MANAGER_RULE, and notify_team's paragraph on
# it by MANAGER_TOOL, so no old sentence is left to argue with the new one. This reverses the 18 Oct
# "a request with nothing in it is never a note" for manager requests: the note goes at once, and the
# matter is added to it once the tenant gives it, so the team does not keep an empty request.
# 28 Oct: the reason for asking is the bot's own and comes before the question, the insisting turn
# included. The rule's "ask, then say why" ended 5 of 13 replies on the reason, its ready-made reason
# was pasted whole, and the insisting turn, given no reason, borrowed management's; the topic turn then
# borrowed the second note's purpose ("so management has the full picture"), which is gone too.
# MANAGER_TOOL keeps when to call and what to note; what to say is the rule's alone, so the two
# cannot drift apart. The words the rule and the tool forbade ("בינתיים", "כבר מטפלת", "in the
# meantime", "a stop on the way to a manager") are gone from both: quoted, they were said back
# (manager_fee, manager_doubt), and the last one told the model a manager is coming. What the bot does
# instead is the reason it gives for asking: it handles the matter itself.
# Not taken from the protocol the owner pasted with it: presenting the bot's own answer as "an
# automated background check" or asking for data "for the manager's screen". That misleads the
# tenant, and the prompt's honesty rule (never claim what no tool did) forbids it.
MANAGER_FROM = "בקשה לדבר עם מנהל, עם בן אדם או עם מישהו מהצוות"
MANAGER_TO = "ואתה נשאר איתו, בסבלנות, עד שהוא מספר."
MANAGER_RULE = (
    "בקשה לדבר עם מנהל, עם בן אדם או עם מישהו מהצוות היא בקשה לגיטימית, ואתה לא שומר עליה בדלת ולא מתנה אותה "
    "בכלום. אתה מקבל אותה בחום, רגוע ובטוח, כמו מי שבאמת בצד שלו: רושם מיד לצוות, עם הכלי שיש לך לזה, שהוא "
    "ביקש מנהל, עם מה שכבר סיפר, ואומר לו במשפט אחד שההנהלה מעודכנת. רק את זה, כי מה שיקרה אחר כך אתה "
    "לא יודע. ובאותה הודעה אתה אומר לו בפשטות ובכנות למה אתה צריך לדעת מה קרה: כדי "
    "שתוכל לסדר את זה בעצמך, מהר יותר, והרבה פעמים כבר כאן, ושואל אותו על מה מדובר ומה מטריד אותו. ואם הוא "
    "מתעקש, או לא רוצה לפרט, אתה לא מוותר ולא מתווכח: אתה אומר לו בנעימות שההנהלה כבר יודעת, ושמספיקה לך מילה "
    "על מה מדובר כדי להתחיל לטפל בזה בעצמך, ושואל שוב, בדרך אחרת ולא באותן מילים. כשאתה יודע במה מדובר, העניין "
    "אצלך ואתה מטפל בו עד הסוף, עם הכלים שלך ועם מה "
    "שאתה יודע: נושא עוד לא אומר מה הוא צריך, אז אתה שואל מה קורה איתו, או עושה את מה שצריך. ואת מה שהוא סיפר "
    "אתה מוסיף לצוות עם הכלי, פעם אחת. ואם הוא אומר שאתה לא יכול לעזור לו בזה, "
    "אתה לא מוותר, לא משאיר את זה לצוות ולא מתווכח: אתה מקבל את זה בחום, אומר לו שהרבה דברים כאלה אפשר לסדר "
    "לו כאן ועכשיו, ושואל בכל זאת מה קורה. מה שרק בן אדם בהומי'ז יכול לסיים נשאר אצל הצוות, עם "
    "הפרטים, ואז אתה אומר לו שהצוות יודע.")
SOLVE_EDITS = [
    ("חוזה, הצעת מחיר, ענייני ועד הבית, וכל דבר אחר שאתה לא יכול לגמור בעצמך",
     "חוזה, הצעת מחיר, עניין עם חברי ועד הבית עצמם, וכל דבר אחר שאתה לא יכול לגמור בעצמך"),
    ("- **ועד הבית:** מי שלא מכיר את ועד הבית שלו, או שיש לו עניין איתו, אתה רושם את זה לצוות.",
     "- **ועד הבית:** מי שלא מכיר את ועד הבית שלו, או שיש לו עניין עם חברי הוועד עצמם, אתה רושם את זה לצוות. "
     "דמי ועד הבית, התשלום החודשי לחברת הניהול, הם עניין שלך: כמה נשאר לשלם, איך ועד מתי משלמים, קישור לתשלום "
     "ומה כלול בתשלום."),
    (" המשפט שלך נגמר בזה שהצוות יודע.", ""),
    # After a matter only a person can finish: what the team will need to sort it out faster, not "anything
    # else" (27 Oct, the owner's "my card has been charged twice!").
    ("אתה רושם לצוות המתאים עם הכלי שיש לך לזה, ואז אומר לדייר, במילים שלך, שהצוות יודע.",
     "אתה רושם לצוות המתאים עם הכלי שיש לך לזה, ואז אומר לדייר, במילים שלך, שהצוות יודע, ושואל אותו את מה "
     "שיעזור להם לסדר את זה מהר יותר, מתי, כמה או מה בדיוק, שאלה אחת בכל פעם, ולא אם יש עוד משהו."),
    # "Are you a manager?" is a who-are-you question, not "are you a bot?" (twice, 27 Oct: "אני העוזר הדיגיטלי…").
    ("מי ששואל מי אתה שומע שאתה מיכאל מצוות השירות של הומי'ז.",
     "מי ששואל מי אתה, או אם אתה מנהל, שומע שאתה מיכאל מצוות השירות של הומי'ז."),
]
# The same in notify_team's own description, which the model reads as it calls the tool.
NOTE_FROM = "A request for a manager or a person is not one of these yet"
NOTE_TO = "A request with nothing in it is never a note, however often they ask."
MANAGER_TOOL = (
    "A request for a manager or a person is fair: never gatekeep it and never make it conditional. Call "
    "this right away (reason caller_request, with whatever they have said), and tell them in one sentence "
    "that management is being informed: only that, since what follows you do not know. Once they say what "
    "it is about, the matter is yours to the end: a topic is not yet what they need, so ask what is going "
    "on with it, or do it; and call this once more with the matter, under the matter's "
    "own reason (payment, billing, other and so on), never caller_request again: the same reason twice in "
    "a conversation is dropped as a duplicate, and management would never see it. Warm, calm and on their "
    "side throughout.")
NOTE_EDITS = [
    ("the committee's own business, or anything else",
     "the committee members' own business (the monthly committee fee itself is yours: what is owed, "
     "paying it, the link, what it covers), or anything else"),
    ("What the resident hears from you afterwards: that you have let the team know, in your own words, and "
     "what you can still do for them now.",
     "What the resident hears from you afterwards: that you have let the team know, in your own words, and "
     "then, in the same message, the matter itself while it is still yours. After a manager request it is: "
     "ask what is going on with it, or do it, as the one handling it. After a matter past you: the details "
     "the team will need to sort it out faster (when, how much, what exactly), one question at a time; only "
     "when nothing is left to ask, what else you can do now."),
    ("A different matter later in the same conversation is.",
     "A different matter later in the same conversation is, and so is the matter of a manager request, "
     "once they tell you what it is."),
]


def replace_span(text, start, end, new):
    """Replace text[start ... end] (both included) with new; each anchor must occur exactly once."""
    assert text.count(start) == 1 and text.count(end) == 1, "span anchors moved: %r / %r" % (start[:30], end[:30])
    a = text.index(start)
    b = text.index(end, a) + len(end)
    return text[:a] + new + text[b:]
REP_TAP_START = " \"לדבר עם נציג\" אומר שהוא רוצה לדבר עם מישהו"
REP_TAP_END = "וממשיכים משם."
WHO_AFTER = "אתה שירות הלקוחות של הומי'ז, כולו."
TIME_ANCHOR = "+ ' [השעה בישראל עכשיו '"
SORT_CUTS = ['    { title: "לדבר עם נציג",      value: "other" },\n', '  "לדבר עם נציג":       "other",\n']
SEND_CUT = ", { title: 'לדבר עם נציג', value: 'other' }"
FLAT_ASK = ("every time: for a fault in the lobby, the lift or the car park as much as for one inside a flat.")
FLAT_KNOWN = (FLAT_ASK + " When the message says in brackets that the sender is identified in the system, "
              "the apartment written there is the answer: send it without asking.")
ADD_WHO = (
    "// Feature 19 (Yariv's section 6): who is writing, from Homies' records, so the bot\n"
    "// does not ask again for what is known. Passes `Still the last word?` through and adds `who_text`.\n"
    "const base = $('Still the last word?').all();\n"
    "const rows = $input.all().map(i => i.json).filter(r => r && (r.full_name || r.building));\n"
    "const first = (s) => String(s || '').trim().split(/\\s+/)[0] || '';\n"
    "let who = '';\n"
    "if (rows.length === 1) {\n"
    "  const r = rows[0];\n"
    "  who = ' [הפונה מזוהה במערכת: ' + first(r.full_name) + ', ' + r.building + ', דירה ' + r.unit + '.]';\n"
    "} else if (rows.length > 1) {\n"
    "  who = ' [הפונה מזוהה במערכת: ' + first(rows[0].full_name) + ', עם כמה דירות: '\n"
    "      + rows.map(r => r.building + ' דירה ' + r.unit).join('; ') + '.]';\n"
    "}\n"
    "return base.map(b => ({ json: { ...b.json, who_text: who } }));")
# D. One reply per burst. The hello test is cut out of Sort at build time, between these two
# anchors, so the check and Sort cannot disagree about what a bare hello is.
HELLO_FROM = "const bare = text.trim()"
HELLO_TO = "const isGreeting = GREETING.test(bare) || HELLO_RUN.test(bare);"
LAST_WORD_HEAD = (
    "// One reply per burst (27 Oct, the owner's sandbox chat: a second \"faster!!\" sent while the AI\n"
    "// was writing got its own answer, and two near-identical replies went out half a second apart).\n"
    "// A tenant message newer than this run's has a run of its own, and that run answers everything\n"
    "// since the last reply, so this reply goes out only if nothing newer is there. A bare hello is\n"
    "// the exception: it gets the menu, not the backlog, so it does not stop this reply. A failed\n"
    "// check sends, as before: a double reply is better than none. Canned replies are not raced.\n"
    "const items = $('Type for a moment').all();\n"
    "const S = $('Sort').first().json;\n"
    "if (S._canned) return items;\n"
    "const payload = $input.first().json.payload;\n"
    "if (!Array.isArray(payload)) return items;\n"
    "// Sort's own hello test, copied in by scripts/n8n_sandbox_section6.py:\n"
    "const isHello = (text) => {\n")
LAST_WORD_TAIL = (
    "\n  return isGreeting;\n"
    "};\n"
    "const mine = Number(S.message_id);\n"
    "const newer = payload.some(m => m.message_type === 0 && !m.private && Number(m.id) > mine\n"
    "  && !isHello(m.content || ''));\n"
    "return newer ? [] : items;")


def last_word_before_send(out, by):
    """Type for a moment -> fetch the conversation -> drop this reply if the tenant wrote again -> Send."""
    js = by["Sort"]["parameters"]["jsCode"]
    assert js.count(HELLO_FROM) == 1 and js.count(HELLO_TO) == 1, "Sort's hello test moved"
    hello = js[js.index(HELLO_FROM): js.index(HELLO_TO) + len(HELLO_TO)]
    code = LAST_WORD_HEAD + "\n".join("  " + line for line in hello.split("\n")) + LAST_WORD_TAIL
    conns = out["connections"]
    assert conns["Type for a moment"]["main"] == [[{"node": "Send", "type": "main", "index": 0}]]
    src, send = by["Anything newer? (fetch)"], by["Send"]
    fetch_at = free_spot(out["nodes"], send["position"][0], send["position"][1] - 240)
    fetch = {"id": str(uuid.uuid4()), "name": "Anything newer before sending? (fetch)", "type": src["type"],
             "typeVersion": src["typeVersion"], "position": fetch_at, "alwaysOutputData": True,
             "onError": "continueRegularOutput", "parameters": copy.deepcopy(src["parameters"]),
             "credentials": copy.deepcopy(src["credentials"])}
    out["nodes"].append(fetch)
    check = {"id": str(uuid.uuid4()), "name": "Still the last word before sending?", "type": "n8n-nodes-base.code",
             "typeVersion": 2, "position": free_spot(out["nodes"], fetch_at[0] + 240, fetch_at[1]),
             "parameters": {"jsCode": code}}
    out["nodes"].append(check)
    conns["Type for a moment"] = {"main": [[{"node": fetch["name"], "type": "main", "index": 0}]]}
    conns[fetch["name"]] = {"main": [[{"node": check["name"], "type": "main", "index": 0}]]}
    conns[check["name"]] = {"main": [[{"node": "Send", "type": "main", "index": 0}]]}


def section6(bot, supabase_cred):
    out = copy.deepcopy(bot)
    by = {n["name"]: n for n in out["nodes"]}
    sort = by["Sort"]["parameters"]
    for cut in SORT_CUTS:
        sort["jsCode"] = replace_once(sort["jsCode"], cut, "")
    send = by["Send"]["parameters"]
    send["jsonBody"] = replace_once(send["jsonBody"], SEND_CUT, "")
    tool = by["open_request"]["parameters"]
    tool["jsonBody"] = replace_once(tool["jsonBody"], FLAT_ASK, FLAT_KNOWN)
    note = by["notify_team"]["parameters"]
    note["toolDescription"] = replace_span(note["toolDescription"], NOTE_FROM, NOTE_TO, MANAGER_TOOL)
    for old, new in NOTE_EDITS:
        note["toolDescription"] = replace_once(note["toolDescription"], old, new)
    opts = by["Answer the resident"]["parameters"]["options"]
    sm = opts["systemMessage"]
    for old, new in PROMPT_CUTS:
        sm = replace_once(sm, old, new)
    sm = replace_span(sm, MANAGER_FROM, MANAGER_TO, MANAGER_RULE)
    for old, new in SOLVE_EDITS:
        sm = replace_once(sm, old, new)
    assert sm.count(REP_TAP_START) == 1
    start = sm.index(REP_TAP_START)
    end = sm.index(REP_TAP_END, start) + len(REP_TAP_END)
    sm = sm[:start] + sm[end:]
    para_end = sm.index("\n\n", sm.index(WHO_AFTER))
    sm = sm[:para_end] + "\n\n" + WHO_RULE + sm[para_end:]
    assert "לדבר עם נציג" not in sm
    opts["systemMessage"] = sm
    ans = by["Answer the resident"]["parameters"]
    ans["text"] = replace_once(ans["text"], TIME_ANCHOR,
                               "+ ($('Add who').isExecuted ? ($('Add who').first().json.who_text || '') : '') " + TIME_ANCHOR)
    still = by["Still the last word?"]
    who_at = free_spot(out["nodes"], still["position"][0] + 240, still["position"][1] - 120)
    who = {"id": str(uuid.uuid4()), "name": "Who is writing?", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
           "position": who_at, "alwaysOutputData": True, "onError": "continueRegularOutput",
           "parameters": {"method": "GET", "options": {"timeout": 5000},
                          "url": "=https://nmxlhlmcnnggnnuxyelt.supabase.co/rest/v1/residents?phone=eq.%2B{{ $('Sort').first().json.to }}&select=full_name,building,unit",
                          "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth"},
           "credentials": {"httpHeaderAuth": dict(supabase_cred)}}
    out["nodes"].append(who)
    add = {"id": str(uuid.uuid4()), "name": "Add who", "type": "n8n-nodes-base.code", "typeVersion": 2,
           "position": free_spot(out["nodes"], who_at[0] + 240, who_at[1]), "parameters": {"jsCode": ADD_WHO}}
    out["nodes"].append(add)
    after = out["connections"]["Still the last word?"]
    out["connections"]["Still the last word?"] = {"main": [[{"node": "Who is writing?", "type": "main", "index": 0}]]}
    out["connections"]["Who is writing?"] = {"main": [[{"node": "Add who", "type": "main", "index": 0}]]}
    out["connections"]["Add who"] = after
    last_word_before_send(out, by)
    return out
