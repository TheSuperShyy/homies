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
     confirmation question the model skipped twice). The ticket tool's "ask for
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
    "קריאה, אתה לא שואל אם זה המקום. אתה אומר לו באותה הודעה איפה פתחת אותה, הבניין והדירה, כמו \"פתחתי קריאה על "
    "המעלית בהרצל 10, דירה 4\", כדי שיוכל לתקן אותך אם זה לא נכון. אם כתובות לו כמה דירות, אתה שואל באיזו מהן "
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
# C. Handle it ourselves; a note for the team when a manager was asked for.
SOLVE_EDITS = [
    ("חוזה, הצעת מחיר, ענייני ועד הבית, וכל דבר אחר שאתה לא יכול לגמור בעצמך",
     "חוזה, הצעת מחיר, עניין עם חברי ועד הבית עצמם, וכל דבר אחר שאתה לא יכול לגמור בעצמך"),
    ("- **ועד הבית:** מי שלא מכיר את ועד הבית שלו, או שיש לו עניין איתו, אתה רושם את זה לצוות.",
     "- **ועד הבית:** מי שלא מכיר את ועד הבית שלו, או שיש לו עניין עם חברי הוועד עצמם, אתה רושם את זה לצוות. "
     "דמי ועד הבית, התשלום החודשי לחברת הניהול, הם עניין שלך: כמה נשאר לשלם, איך ועד מתי משלמים, קישור לתשלום "
     "ומה כלול בתשלום."),
    ("כשיש לך את הפרטים, אתה מנסה לסגור את העניין בעצמך עם הכלים שלך, ורק מה שבאמת מעבר לך אתה רושם לצוות, "
     "עם מה שהוא סיפר לך, ואז אומר לו שהצוות יודע.",
     "כשאתה יודע במה מדובר, העניין אצלך ואתה מטפל בו עד הסוף: אתה לא תחנת ביניים בדרך למנהל, ולא מעביר אותו "
     "לאף אחד. נושא עוד לא אומר מה הוא צריך, אז אתה שואל מה קורה, וסוגר את זה בעצמך, עם הכלים שלך ועם מה שאתה "
     "יודע. ומכיוון שהוא ביקש מנהל, אתה גם רושם על זה הערה לצוות עם הכלי שיש לך לזה, עם מה שהוא סיפר לך, ואומר "
     "לו את זה במשפט אחד. ההערה היא לא הטיפול: באותה הודעה אתה כבר ממשיך איתו בעניין עצמו. ואם הוא אומר שאתה לא "
     "יכול לעזור לו בזה, הוא עוד לא יודע מה אתה יכול: אתה לא מוותר ולא מעביר אותו לצוות, אלא אומר לו בפשטות מה "
     "אתה כן יכול לעשות בעניין הזה, ושואל מה קורה. מה שמעבר לך נקבע לפי העניין עצמו, כשאתה כבר יודע מה הוא, ולא "
     "לפי מה שהוא אומר עליך."),
    (" המשפט שלך נגמר בזה שהצוות יודע.", ""),
]
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
    opts = by["Answer the resident"]["parameters"]["options"]
    sm = opts["systemMessage"]
    for old, new in PROMPT_CUTS + SOLVE_EDITS:
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
