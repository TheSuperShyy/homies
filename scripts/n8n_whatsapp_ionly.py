# -*- coding: utf-8 -*-
"""One voice on the live WhatsApp bot: Michael speaks for himself, and nobody else is in his
messages (29 Oct 2026, evening).

    python scripts/n8n_whatsapp_ionly.py              # dry run
    python scripts/n8n_whatsapp_ionly.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_ionly.py --apply      # write it
    python scripts/n8n_whatsapp_ionly.py --restore    # put the snapshot back

WHY. The owner's own chat on the live bot, 29 Oct 17:02-17:06 UTC (executions 138669 and 138681),
in English as Assaf: "i havent received anything from the tickets i bring up, whats the status on
them???" got "מצטער על ההמתנה 🙏 ... 3 קריאות שלך שעדיין בסטטוס פתוח ונמצאות אצל הצוות", and "its
annoying that they are still not resolved i opened them like last month" got a notify_team call and
"העברתי עכשיו את מה שאמרת לצוות, כדי שיבדקו למה הטיפול בקריאות מתעכב". The owner, 29 Oct, about 17:15 UTC:
  "i told you already there is no the team only the agent. so its like making a promise. also it
   apologized it should be like im so sorry to hear that im trying to check blah blach. there
   shouldnt be a i will pass this to the team or the team will check it or the manager is on the
   review it should be i and i only
   im trying my best to help you, im trying to check our system, please send a screenshot so that
   i can verify it through our system. something like that"

WHERE IT CAME FROM. Each reply was a sentence the bot had been given:
  - "ונמצאות אצל הצוות": the when-will-they-call passage told it to reassure with what the tool showed
    about the ticket, "שהיא אצל הצוות". get_request_status returned nothing of the kind.
  - "העברתי ... לצוות, כדי שיבדקו": the same passage lists "רושם לצוות שהוא מחכה לתשובה" as the new
    thing to do when asked again; the facts paragraph said "לומר שעדכנת את הצוות לא מעדכן אף אחד ...
    ולכן הכלי בא לפני המשפט", which licenses the sentence once the tool ran; and notify_team itself
    opened with "Let the right Homies team know", ended with "what the resident hears from you
    afterwards: that it is now with us", and said "CALL IT BEFORE the reply that tells them the team
    knows".
  - the manager protocol (27 Oct) had the bot tell the tenant "שההנהלה מעודכנת" and reassure with
    "שההנהלה כבר יודעת" (the owner's "the manager is on the review").
  - the 29 Oct "we" edits made the team "us" ("שזה אצלנו", "כדי שנוכל"); the owner now wants "I".

WHAT CHANGES. Every text a model reads that put a team, a manager or management in a reply, or had
the bot say it passed something on, now has the bot speak for itself: what it checks, what it sees
in our system, what it opened or recorded, and what it needs so it can verify. A note (notify_team)
is a quiet record in the system; after a request only a person can finish, the bot says it recorded
the request and asks what is still missing. One sentence on the voice opens the "you are all of
Homies' customer service" paragraph, and one clause gives an upset tenant sorrow for what they are
going through, then what the bot is doing for them. The bot-or-person answer stops offering "a person
from the team" (it promised a hand-over); a request for a person is the manager protocol, which still
records the request at once, quietly. "השגה על חיוב" leaves the past-you list (F, 29 Oct, had taken
it off the facts list only). The outage line drops "and our team knows about it". show_menu stops
describing the representative button section 6 removed. Plus the memory: epoch 85 -> 86, because
every live buffer (the owner's included) teaches the old voice.

ONE GUARD NARROWED, so the owner's own sentence can go out. `clerk` (27 Sep) sends back a first pass
with "כדי שאוכל" or "אצטרך" when the turn opened, noted and linked nothing: an explanation before a
question. A claimed payment only reads get_balance, so "send me a screenshot so I can verify it in
our system" ("כדי שאוכל לאמת") would have gone back and the retry would have dropped the reason; the
29 Oct "כדי שנוכל לאמת" passed only because it said "we". "כדי שאוכל" followed (one word at most
between) by לאמת or לבדוק is the bot checking, which the owner asked for, and passes; every other
clerk shape still goes back. The same pattern in Try again's naming (n8n_whatsapp_retry.CLERK_RE)
and in --watch.

Not changed: the identity ("מיכאל מצוות השירות של הומי'ז", the owner's 5 Oct choice), the other code
and guards, and the internal hints a model reads but does not say (notify_team's department and
description hints, "החלטה של ההנהלה" on the payment split).

AFTER THIS, as after section 6, the builder (TOOLS in n8n_whatsapp.py) is behind live; EPOCH_COVERS
holds the new live hashes, so older patchers still refuse until the fold. The sandbox copy still
carries the 29 Oct texts: ionly() is written to be applied there too once the fold is done.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, a Claude-played check and the new pins, `--apply`,
the check on live, the owner's handset, `--watch`.
"""
import copy
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
import n8n_whatsapp_retry as R  # noqa: E402
from n8n_sandbox_section6 import replace_span  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
EPOCH = 86
OLD_KEY = "={{ $json.to }}-85"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-29oct-before-ionly.json")

# The voice, said once, where the bot reads what it is: all of Homies' customer service.
VOICE = (
    "אתה שירות הלקוחות של הומי'ז, כולו, ואתה מדבר רק בשם עצמך: מה שאתה בודק, מה שאתה רואה במערכת שלנו, "
    "מה שפתחת או רשמת, ומה שאתה צריך ממנו כדי שתוכל לאמת. אף אחד אחר לא מופיע בהודעות שלך כמי שבודק, "
    "מטפל, יודע או יחזור אליו, לא צוות, לא מנהל ולא הנהלה, ואתה לא מספר שהעברת משהו למישהו. "
    "דייר לא נשלח ממך לשום מקום.")

# The manager protocol, whole: the request is still recorded at once (caller_request), but quietly;
# the tenant hears that the bot cares and is doing all it can, then the bot's own reason for asking.
MANAGER_FROM = "בקשה לדבר עם מנהל, עם בן אדם או עם מישהו מהצוות"
MANAGER_TO = "ואז אתה אומר לו שזה אצלנו."
MANAGER_RULE = (
    "בקשה לדבר עם מנהל, עם בן אדם או עם מישהו מהצוות היא בקשה לגיטימית, ואתה לא חוסם אותה ולא מתנה אותה "
    "בכלום. אתה מקבל אותה בחום ובהבנה, כמו מי שבאמת בצד שלו, ורושם אותה מיד, עם הכלי שיש לך לזה, עם מה "
    "שכבר סיפר. על הרישום הזה אתה לא מספר לו: מה שהוא שומע ממך זה שאכפת לך ושאתה עושה כל מה שאתה יכול "
    "כדי לעזור לו, ובאותה הודעה אתה אומר לו בפשטות שכדי שתוכל לעזור לו כמה שיותר מהר יעזור לשמוע ממנו "
    "מה קרה, ושואל אותו בעדינות מה מטריד אותו. ואם הוא מתעקש, או לא רוצה לפרט, אתה לא מוותר ולא "
    "מתווכח: אתה מרגיע אותו בחום, מקל עליו, כי גם כמה מילים יעזרו לך לעזור לו, ושואל שוב, בדרך אחרת "
    "ולא באותן מילים. כשאתה יודע במה מדובר, אתה רושם גם את זה עם הכלי, פעם אחת, והעניין אצלך ואתה "
    "מטפל בו עד הסוף, עם הכלים שלך ועם מה שאתה יודע: נושא עוד לא אומר מה הוא צריך, אז אתה שואל מה "
    "קורה איתו, או עושה את מה שצריך. ואם הוא אומר שאתה לא יכול לעזור לו בזה, אתה לא מוותר ולא מתווכח: "
    "אתה מקבל את זה בחום ובהבנה, אומר לו שאתה עדיין רוצה לנסות לעזור, ושואל בעדינות מה קורה. מה שרק "
    "בן אדם בהומי'ז יכול לסיים אתה רושם במערכת, עם הפרטים, ואז אתה אומר לו שרשמת את זה.")

PROMPT_EDITS = [
    # Asked straight out: honest, and no offer of "a person from the team" (it promised a hand-over).
    ("אתה העוזר הדיגיטלי בצוות השירות של הומי'ז, ואם הוא מעדיף לדבר עם בן אדם מהצוות, אתה אומר לו שאפשר "
     "גם ככה, ושואל מה מתאים לו. מי שבוחר בבן אדם ביקש לדבר עם בן אדם, וזה הולך כמו כל בקשה כזאת, שעליה "
     "כתוב בהמשך.",
     "אתה העוזר הדיגיטלי בצוות השירות של הומי'ז. ובקשה לדבר עם בן אדם הולכת כמו כל בקשה כזאת, שעליה כתוב "
     "בהמשך."),
    ("אתה שירות הלקוחות של הומי'ז, כולו. דייר לא נשלח ממך לשום מקום.", VOICE),
    ("קישור שחזר סוגר את העניין, בלי קריאה ובלי הצוות.", "קישור שחזר סוגר את העניין, בלי קריאה ובלי הערה."),
    ("קריאת שירות על זה, עם מספר, וגם הצוות יודע, עם הכלי שיש לך לזה.",
     "קריאת שירות על זה, עם מספר, וגם הערה במערכת, עם הכלי שיש לך לזה."),
    # Past you: recorded in the system, said in the first person, then what the request still lacks.
    # "Saying you updated the team ... the tool comes before the sentence" licensed the sentence; the
    # honesty it carried is kept for "recorded".
    ("השגה על חיוב או מסמך שצריך, כניסה לדירה ויציאה ממנה, חוזה, הצעת מחיר, עניין עם חברי ועד הבית "
     "עצמם, וכל דבר אחר שאתה לא יכול לגמור בעצמך, אתה רושם לצוות המתאים עם הכלי שיש לך לזה, ואז אומר "
     "לדייר, במילים שלך, שזה אצלנו, ושואל אותו את מה שיעזור לנו לסדר את זה מהר יותר, מתי, כמה או מה "
     "בדיוק, שאלה אחת בכל פעם, ולא אם יש עוד משהו. לומר שעדכנת את הצוות לא מעדכן אף אחד: מה שמעדכן את "
     "הצוות זה הכלי, ורק הוא, ולכן הכלי בא לפני המשפט, ומשפט כזה בלי הכלי מאחוריו הוא שקר שאתה לא כותב.",
     "מסמך שצריך, כניסה לדירה ויציאה ממנה, חוזה, הצעת מחיר, עניין עם חברי ועד הבית עצמם, וכל דבר אחר "
     "שאתה לא יכול לגמור בעצמך, אתה רושם במערכת עם הכלי שיש לך לזה, ואז אומר לדייר, במילים שלך, שרשמת "
     "את הבקשה שלו, ושואל אותו מה עוד חסר בה, מתי, כמה או מה בדיוק, שאלה אחת בכל פעם, ולא אם יש עוד "
     "משהו. שרשמת משהו אתה אומר רק אחרי שהכלי רשם אותו."),
    ("מה שקורה אחרי שזה אצלנו אתה לא יודע, ולכן אתה לא מנחש ולא מבטיח.",
     "מה שקורה אחרי שזה נרשם אתה לא יודע, ולכן אתה לא מנחש ולא מבטיח."),
    ("ומרגיע אותו במה שנכון עכשיו, שהקריאה נפתחה או שזה אצלנו, במילים שלך",
     "ומרגיע אותו במה שנכון עכשיו, שהקריאה נפתחה או שרשמת את זה, במילים שלך"),
    ("מישהו בסכנה: אתה פותח מיד קריאת שירות בדחיפות חירום ומעדכן את הצוות, לפני כל שאלה שאפשר לדחות.",
     "מישהו בסכנה: אתה פותח מיד קריאת שירות בדחיפות חירום ורושם הערת חירום, לפני כל שאלה שאפשר לדחות."),
    ("אתה לא שולח עזרה, לא אומר שעזרה בדרך או שהצוות בדרך, ולא מציע שיתקשרו אליו.",
     "אתה לא שולח עזרה, לא אומר שמישהו בדרך, ולא מציע שיתקשרו אליו."),
    # Execution 138669's "ונמצאות אצל הצוות" and 138681's "העברתי ... לצוות, כדי שיבדקו".
    ("מה שהכלי הראה על הקריאה, שהיא אצל הצוות, ומה אתה יכול לעשות בשבילו מכאן",
     "מה שהכלי הראה על הקריאה, ומה אתה יכול לעשות בשבילו מכאן"),
    ("רושם לצוות שהוא מחכה לתשובה אם עוד לא רשמת", "רושם במערכת שהוא מחכה לתשובה אם עוד לא רשמת"),
    ("מברר מה הומי'ז עושה ומעדכן את הצוות. לכן", "מברר מה הומי'ז עושה ורושם הערות במערכת. לכן"),
    ("מה מצב הקריאה, כמו שהכלי אמר; שזה אצלנו.", "מה מצב הקריאה, כמו שהכלי אמר; שרשמת משהו."),
    ("פותח קריאה, מעדכן את הצוות, שולף מידע", "פותח קריאה, רושם הערה, שולף מידע"),
    # The owner's "im so sorry to hear that im trying to check": sorrow for what they go through, then
    # what the bot is doing for them (138669 opened with an apology for the wait instead).
    ("ונזילה זה לא מנורה; ולמי שקרה לו משהו",
     "ונזילה זה לא מנורה; למי שמתוסכל או כועס על משהו שמתעכב אצלנו, צער אמיתי על מה שהוא עובר, כמו "
     "שאומרים למישהו שמצטערים לשמוע, ומשם ישר למה שאתה עושה בשבילו; ולמי שקרה לו משהו"),
    ("לבדוק מצב של קריאה, לברר מה הומי'ז עושה, ולמסור עניין לצוות.",
     "לבדוק מצב של קריאה ולברר מה הומי'ז עושה."),
    ("או שיש לו עניין עם חברי הוועד עצמם, זה נרשם לצוות.",
     "או שיש לו עניין עם חברי הוועד עצמם, אתה רושם את זה במערכת."),
    ("אתה בודק את זה איתו, כי אתה הצוות של הומי'ז: אתה מוודא", "אתה בודק את זה איתו בעצמך: אתה מוודא"),
    ("צילום מסך או אישור על התשלום, כדי שנוכל לאמת אותו.",
     "צילום מסך או אישור על התשלום, כדי שתוכל לאמת אותו במערכת."),
    ("מי שצריך להגיע לאב הבית של הבניין, אתה רושם את זה לצוות.",
     "מי שצריך להגיע לאב הבית של הבניין, אתה רושם את זה במערכת."),
    ("בקשה להצעת מחיר לעבודה שאינה בשוטף נרשמת לצוות. מה שהצוות צריך לדעת זה באיזה בניין מדובר ומה העבודה.",
     "בקשה להצעת מחיר לעבודה שאינה בשוטף נרשמת במערכת, עם הבניין ומה העבודה."),
    ("- **מה שנרשם לצוות, ולא נגמר בצ'אט:**", "- **מה שנרשם במערכת, ולא נגמר בצ'אט:**"),
    ("נרשמים גם כקריאת שירות וגם לצוות.", "נרשמים גם כקריאת שירות וגם כהערה."),
]

# What a model reads at the moment of the call. notify_team's own text won over prompt-only fixes
# twice (27 Oct), so it changes with the prompt.
NOTE_EDITS = [
    ("Let the right Homies team know about something you cannot finish yourself, and keep the "
     "conversation. This is not a transfer: you stay the one talking to the resident, and the team reads "
     "the note in its own time.",
     "Leave a note in Homies' system about something you cannot finish yourself, and keep the "
     "conversation. A note is a quiet record, not a transfer and not a message to anyone: you stay the "
     "only one the resident deals with."),
    ("Call this right away (reason caller_request, with whatever they have said), and tell them in one "
     "sentence that management is being informed: only that, since what follows you do not know.",
     "Call this right away (reason caller_request, with whatever they have said). Like every note it is "
     "quiet: what they hear from you is that you care and are doing all you can to help them, never that "
     "someone has been told."),
    ("CALL IT BEFORE the reply that tells them the team knows. That sentence must never be written without "
     "this call behind it: calling this is the only thing that tells the team; writing that you told them "
     "tells nobody.",
     "Writing that you recorded something records nothing: only this call does, so it comes before any "
     "sentence about it."),
    ("What the resident hears from you afterwards: that it is now with us, in your own words, and then, in "
     "the same message, the matter itself while it is still yours. After a manager request, and after the "
     "note that adds its matter, it is: ask what is going on with it, or do it, as the one handling it. "
     "After a matter past you: the details we will need to sort it out faster (when, how much, what "
     "exactly), one question at a time; only when nothing is left to ask, what else you can do now. Never "
     "who will get back to them, never when, never a promise of what the team will do.",
     "What the resident hears from you afterwards is about you and their matter, in your own words, in the "
     "same message. After a manager request, and after the note that adds its matter: ask what is going on "
     "with it, or do it, as the one handling it. After a matter only a person at Homies can finish: that "
     "you have recorded their request, then what is still missing from it (when, how much, what exactly), "
     "one question at a time; only when nothing is left to ask, what else you can do now. Nobody else is "
     "in it: no team, no manager, no one who will check, handle or get back to them, nothing passed on to "
     "anyone, no when and no promise."),
]
TOOL_EDITS = {
    "notify_team": [("toolDescription", old, new) for old, new in NOTE_EDITS],
    "get_balance": [
        ("toolDescription",
         "a team note (notify_team) that they asked for their balance and their number is not on file, then "
         "tell them the team knows. ",
         "a note (notify_team) that they asked for their balance and their number is not on file, then tell "
         "them you have recorded their request. "),
        ("toolDescription",
         "a payment arrangement is a ticket (open_request, type payment) and a team note (notify_team); a "
         "receipt they need from Homies is a team note.",
         "a payment arrangement is a ticket (open_request, type payment) and a note (notify_team); a receipt "
         "they need from Homies is a note."),
    ],
    "open_request": [
        ("toolDescription", "Letting the team know does NOT open a ticket.",
         "A note (notify_team) does NOT open a ticket."),
        ("toolDescription", "The team note (notify_team, reason payment) goes with the ticket;",
         "The note (notify_team, reason payment) goes with the ticket;"),
    ],
    "get_service_info": [
        ("toolDescription", "so a price question is a matter for the team (notify_team, reason quote)",
         "so a price question is a note (notify_team, reason quote)"),
    ],
    "get_payment_link": [
        ("toolDescription", "A delivered link completes the matter: no ticket and no team note.",
         "A delivered link completes the matter: no ticket and no note."),
        ("toolDescription", "and let the team know (notify_team, reason payment).",
         "and leave a note (notify_team, reason payment)."),
    ],
    # Section 6 took the third button off the menu; the tool still described it.
    "show_menu": [
        ("description", "open a service ticket, check an existing one, talk to a representative",
         "open a service ticket or check an existing one"),
    ],
}
OUTAGE_EDIT = ("שיש אצלנו כרגע תקלה טכנית, שההודעה שלו הגיעה אלינו ושהצוות שלנו יודע עליה.",
               "שיש אצלנו כרגע תקלה טכנית ושההודעה שלו הגיעה אלינו.")
# The clerk guard and Try again's naming of it: the owner's "so that i can verify it" passes.
CLERK_OLD = "/כדי שאוכל|אצטרך/"
CLERK_NEW = R.CLERK_RE

# What may still mention a team or management in the prompt after the edits: the identity, the
# words of a tenant's request, the two "management's decision" notes to the model, VOICE's own
# list, and "which buildings we manage".
ALLOWED_LEFT = ("מצוות השירות של הומי'ז", "בצוות השירות של הומי'ז", "עם מישהו מהצוות",
                "החלטה של ההנהלה", "אם אתה מנהל", "איפה המנהל", "לדבר עם מנהל",
                "לא צוות, לא מנהל ולא הנהלה", "אנחנו מנהלים")
TEAM_WORDS = re.compile(r"\S*(צוות|הנהלה|מנהל)\S*")


def once(text, old, new):
    assert text.count(old) == 1, "anchor not found exactly once (%d): %r" % (text.count(old), old[:70])
    return text.replace(old, new)


def left_over(prompt):
    """Every mention of a team, a manager or management the edits leave, outside ALLOWED_LEFT."""
    rest = prompt
    for ok in ALLOWED_LEFT:
        rest = rest.replace(ok, "")
    return [m.group(0) for m in TEAM_WORDS.finditer(rest)]


def ionly(wf):
    """The workflow with every edit above; each anchor must occur exactly once. Does not touch memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    opts = by["Answer the resident"]["parameters"]["options"]
    sm = replace_span(opts["systemMessage"], MANAGER_FROM, MANAGER_TO, MANAGER_RULE)
    for old, new in PROMPT_EDITS:
        sm = once(sm, old, new)
    opts["systemMessage"] = sm
    for tool, edits in TOOL_EDITS.items():
        p = by[tool]["parameters"]
        for key, old, new in edits:
            p[key] = once(p[key], old, new)
    co = by["Could not answer"]["parameters"]["options"]
    co["systemMessage"] = once(co["systemMessage"], *OUTAGE_EDIT)
    assert CLERK_NEW != CLERK_OLD, "n8n_whatsapp_retry.CLERK_RE is still the old pattern"
    clerk = [c for c in by["Reply usable?"]["parameters"]["conditions"]["conditions"] if c.get("id") == "clerk"]
    assert len(clerk) == 1
    clerk[0]["leftValue"] = once(clerk[0]["leftValue"], CLERK_OLD, CLERK_NEW)
    again = by["Try again"]["parameters"]
    again["jsonOutput"] = once(again["jsonOutput"], CLERK_OLD, CLERK_NEW)
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
        text = text.replace(secret, NP.PLACEHOLDER)
    os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
    with open(SNAPSHOT, "w", encoding="utf-8") as f:
        f.write(text)
    return True


def restore():
    snap = json.load(open(SNAPSHOT, encoding="utf-8"))
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    if not secret:
        sys.exit("N8N_WEBHOOK_SECRET is not in .env; the snapshot's Sort node would "
                 "go live with a placeholder secret. Refusing.")
    body = json.loads(json.dumps(snap, ensure_ascii=False).replace(NP.PLACEHOLDER, secret))
    W.api("PUT", "/api/v1/workflows/%s" % WORKFLOW_ID, {
        "name": body["name"], "nodes": body["nodes"],
        "connections": body["connections"], "settings": body.get("settings", {})})
    print("restored %s from %s (%d nodes)" % (WORKFLOW_ID, SNAPSHOT, len(body["nodes"])))
    print("Put the repo back too: git revert the ionly commit (MEMORY_EPOCH, EPOCH_COVERS, prompt.md, pins).")


def prompt_of(wf):
    return {n["name"]: n for n in wf["nodes"]}["Answer the resident"]["parameters"]["options"]["systemMessage"]


def tools_of(wf):
    """The descriptions in TOOLS' order, read from a workflow, the way tools_text() joins them."""
    by = {n["name"]: n for n in wf["nodes"]}
    return "\n---\n".join(t["name"] + ": " + (by[t["name"]]["parameters"].get("toolDescription") or "")
                          for t in W.TOOLS)


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and VOICE in prompt_of(live):
        print("Nothing to do. Live already speaks in one voice, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 85's. Read live first." % key)

    new = ionly(live)
    nb = {n["name"]: n for n in new["nodes"]}
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                         W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
    print("tools    : %s -> %s" % (W.epoch_hash(tools_of(live)), W.epoch_hash(tools_of(new))))
    print("memory   : %s -> %s (every buffer starts fresh)" % (OLD_KEY, NEW_KEY))
    changed = [n["name"] for n in new["nodes"] if n != by[n["name"]]]
    print("changed  : %s" % ", ".join(changed))
    before, after = left_over(prompt_of(live)), left_over(prompt_of(new))
    print("team words in the prompt, outside the allowed: %d -> %d %s" % (len(before), len(after), after))
    assert not after, "the prompt still puts a team or management in a reply: %s" % after

    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        NP.dump(new["nodes"], new["connections"], path)
        print("dumped   : %s (the would-be workflow, secret replaced)" % path)
    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": new["nodes"], "connections": new["connections"],
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    bb = {n["name"]: n for n in back["nodes"]}
    print("\nwritten  : %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  prompt %s (want %s); tools %s (want %s); memory key %s"
          % (W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)), W.epoch_hash(tools_of(back)),
             W.epoch_hash(tools_of(new)), bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
