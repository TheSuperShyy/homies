# -*- coding: utf-8 -*-
"""The WhatsApp bot's regression gate: every rule it must keep and every bug it
has had, run against the exact code n8n runs. Read only. Spends nothing.

    python scripts/check_whatsapp_rules.py                           # the cases + pins, on live
    python scripts/check_whatsapp_rules.py --candidate F [F ...]     # on live + a patcher's --dump
    python scripts/check_whatsapp_rules.py --candidate F --replay    # + every real message, before vs after
    python scripts/check_whatsapp_rules.py --execution 65683         # on the workflow an execution ran
    python scripts/check_whatsapp_rules.py --watch 2026-09-27T13:17  # real turns since then, against the rules
    python scripts/check_whatsapp_rules.py --pins                    # print the model-text fingerprints

Exits non-zero on any failure, so it can gate a patcher's --apply.

WHY, 27 Sep. Owner: *"we need to make sure this wont open another bug we
always experiencing this issue we fix a bug it cause another one and loop
repeats"*. The loop had three causes, and each part of this file answers one.

  1. Every fix was tested once, in a temp folder, and the tests vanished; the
     next fix never re-ran them. -> THE CASES (check_whatsapp_rules.js) live
     in the repo and grow by one for every bug: the owner's greeting table,
     the 27 Sep turns, the deeds / echo / clerk guards, the payment ack's
     gate. They run the EXACT code from the workflow -- Sort's greeting test,
     Send's body, the guards, the notes -- never a copy of it.

  2. The 27 Sep regression was a change to text a MODEL reads (a note in
     `Worth a word?` told it to write a greeting back, and it started answering
     "hello" with an invented payment request). Tests of code cannot see what a
     model does with a sentence. -> THE PINS: a fingerprint of every text a
     model reads. Change one and this fails with "model-facing text changed".
     The way through is a replay of the real inputs that reach that model, with
     Claude playing it (never OpenRouter: testing spends nothing), and only then
     a new pin, printed by --pins.

  3. Nothing compared a change against everything that has really happened,
     and nothing looked at real traffic after a deploy: the owner found it. ->
     --replay runs every message ever received and every reply ever sent
     through the live code and the candidate and prints EVERY difference, so
     "only the intended ones changed" is checked, not assumed. --watch reads
     the real executions since a deploy and flags any turn that breaks the
     owner's rules.

HOW A WHATSAPP CHANGE SHIPS (CONTEXT.md, "How a WhatsApp change ships"):
  patcher --dump F  ->  this --candidate F --replay  ->  patcher --apply  ->
  this, on live  ->  the owner's handset  ->  this --watch <deploy time>, and
  again the next morning.

Real message texts are read at run time and handed to Node on stdin; they are
never written to disk. Links and phone numbers are masked in everything printed.

This file tests the CODE. The model's own behaviour is tested, still without a
model call, by scripts/wa_qa.py: Claude plays the model, this code runs around
every turn, blind judges rank the variants (CONTEXT.md, "How the WhatsApp bot
is tested without a model call").
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import n8n_whatsapp as W  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
JS = os.path.join(HERE, "check_whatsapp_rules.js")

# Every text a model reads, fingerprinted. A change fails the check until a
# replay has been done and the new value pasted here from --pins. The prompt,
# inject and tool texts are ALSO covered by MEMORY_EPOCH in n8n_whatsapp.py;
# that one decides whether memories restart, this one whether it was tested.
# 1 Oct evening: five moved together (n8n_whatsapp_gender.py: one person, in
# the singular), after 30 Claude-played conversations and the rescue and
# outage writers replayed on the new texts (scratchpad run wa_qa_gender).
# 1 Oct, later: the prompt alone (n8n_whatsapp_rephello.py: the representative
# tap opens with hi, how are you, the name), after the Claude-played deck.
# 4 Oct: the prompt and Try again's note (n8n_whatsapp_rephay.py: the tap asks
# how he is and only that; the note names a tap reply that did not), after the
# Claude-played deck (33 conversations, scratchpad run wa_qa_rephay).
# 4 Oct evening: the prompt alone (n8n_whatsapp_calmword.py: the word before the
# question is caring, no "אוף", no "מעצבן"), after a blind replay of 27 reaction
# turns from that day's runs: irritated openings 13 (old), 7 (softer), 0 (this).
# 5 Oct: Try again's note (n8n_whatsapp_safetynet.py: a truth failure is named,
# and what the first pass's tools returned is handed to the second), and `Say it
# again` gone with its two pins. Replay: the five retries of 5 Oct whose first
# pass used tools (live 83668's mould lookup; offline, a duplicate ticket, two
# status lookups and a refused ticket), the second pass played by Claude on the
# new input: 5 of 5 went out, none said anything untrue (two of them had ended
# in Say it again's false claims before). Scratchpad run safetynet/retry_play.py.
PINS = {
    # 29 Oct, evening (n8n_whatsapp_ionly.py, epoch 86): one voice, Michael's (the owner: "there is no the
    # team only the agent ... it should be i and i only"). Nine texts moved together: the prompt, the
    # outage line, six tool descriptions and Try again's note (its clerk pattern now lets "so I can
    # verify / check it" through). Claude-played on the candidate (scripts/wa_qa_ionly.json: the owner's
    # 17:02 chat word for word, a manager request, a claimed payment, a document, bot-or-person, the
    # stuck lift): 6 conversations, 28 turns, no reply with a team, a manager or "we will", no guard
    # rejection on the new code; 26/28 expectations, the two misses being "sorry" said on the first
    # complaint rather than the second, and the payment turn graded on the retry the OLD clerk forced
    # (its first pass, the owner's own sentence, goes out whole on the new code).
    # 29 Oct (n8n_whatsapp_section6.py, epoch 85): the sandbox's version put on live, owner's "replace
    # the old chatbot with the new version". The five texts below are section6()'s, tested in the sandbox
    # that day (three blind Claude rounds, two Gemini runs, the owner's own chats) rather than by a fresh
    # replay of the real inputs; the cases are 416/416 and the replay of every message changes nothing.
    # 29 Oct, night (n8n_whatsapp_addto.py, epoch 90): the photo note no longer says the photo is on the open
    # ticket, a new tool adds to an open ticket, and notify_team says a note never changes a ticket (the
    # owner, on 139178/139189: "is this real? did it notif anyone or updated the ticket"). Claude-played on
    # the candidate (scripts/wa_qa_addto.json): the owner's chat went on 255-1365-26 by the new tool, every
    # "I added" backed by its answer, no note, no team; the same chat on the old text reproduced the claims.
    # 2 Nov (n8n_whatsapp_photo.py, epoch 92): the photo note says the photo is seen when Show the photos put it
    # on the item, and keeps "you do not see its content" when none could be fetched. Checked by the five new
    # inject cases and by Node runs of Show the photos (a photo before the words, one before the last reply,
    # Sort's own, a failed download, five photos with a PDF among them). What Gemini makes of a real photo is
    # the owner's handset test, not a Claude play: Claude cannot stand in for the model's eyes.
    # 9 Nov (n8n_whatsapp_feedback9.py, epoch 100): the clock line says when the office is closed.
    'Answer the resident / input': 'fd710a52a21b',
    'add_request_detail / tool': 'b2fc05691540',
    # 5 Oct (n8n_whatsapp_straight.py, epoch 74): the prompt and get_balance's
    # text, after a Claude-played check of 11 situations through the would-be
    # bot's guards and Send (the pushed danger line now carries its number).
    # 5 Oct evening (n8n_whatsapp_hayday.py, epoch 75): the rep tap asks how he is
    # TODAY. Claude-played: 5 replies through the would-be guards and Send.
    # 8 Oct (n8n_whatsapp_menuline.py, epoch 78): the ownership clause quotes the
    # menu's new tail, "👋 כאן הומי'ז. במה אפשר לעזור?". Claude-played on the
    # candidate: tap_open, status_tap, tap_rep, hello_then_matter, rep_fine_thanks;
    # 17 turns, 34/34 expectations, no guard rejection, no rubric flag.
    # 18 Oct (n8n_whatsapp_askfirst.py, epoch 79): a request for a manager gets help
    # first, then the questions, and the team note only with the details; with it
    # notify_team's text. Claude-played on the candidate: manager_insists,
    # manager_wont_say, rep_typed, tap_rep, fem_rep_tap, price_quote,
    # pay_link_missing, neighbor_noise, cancel_ticket, angry_repeat; 28 turns,
    # 59/59 expectations, no guard rejection, no rubric flag.
    # 18 Oct, later (n8n_whatsapp_hearyou.py, epoch 80): the same request answered
    # like a person at a service desk, not a process; notify_team's text with it.
    # Claude-played on the candidate: manager_insists, manager_wont_say, rep_typed,
    # tap_rep, price_quote; 18 turns, 37/37 expectations, no guard rejection.
    # 18 Oct, evening (n8n_whatsapp_unasked.py, epoch 81): a typed request for a rep
    # is not the tap; with it Try again names a how-are-you he did not ask for.
    # Claude-played on the candidate: manager_typed_mid, manager_insists,
    # manager_wont_say, rep_typed, tap_rep, rep_fine_thanks, how_are_you_he,
    # rep_and_you (29 turns, 65/65, no flag), and 112521's own draft through the
    # retry (variant R: sent back by `unasked`, the note named it, the second pass
    # asked what it is about; 6/6).
    # 18 Oct, late (n8n_whatsapp_procedure.py, epoch 82): a request for a manager is
    # answered with the reason, never the same question twice, and nothing goes on
    # without the matter; notify_team's text and Try again's note with it.
    # Claude-played on the candidate: manager_parrot (the owner's chat word for word),
    # manager_insists, manager_wont_say, manager_typed_mid, rep_typed, angry_repeat,
    # stair_light, tap_rep; 29 turns, 58/58, no guard rejection, no flag, and no
    # backstop note without the tool. Tonight's six first drafts replayed through the
    # candidate: the five that explained go out, 112618 keeps its name, and 112626's
    # (a promise inside the reason) goes back with the promise named.
    # 19 Oct (n8n_whatsapp_norepeat.py, epoch 83): a ticket's status is looked up by
    # the number first (two sentences), nothing already sent is sent again, and
    # Try again's note speaks of a draft he never got; get_request_status's text
    # with them. Claude-played on the candidate: see the WORKLOG entry of the day.
    # 20 Oct (n8n_whatsapp_lowkey.py, epoch 84): asked when someone will call, come or
    # update, a true reason from what the tools returned and what is not in them, never
    # a stated reason (one stated was sent in a third of the answers); asked again,
    # something new. Claude-played in three rounds, the last half size and clean
    # (WORKLOG 19 Oct, the epoch-84 entry).
    # 29 Oct, late (n8n_whatsapp_gladly.py, epoch 87): the prompt alone. The quoted word before an answer
    # is "בשמחה", not "אוקיי", and money is told as what our system shows. Claude-played on the
    # candidate (scripts/wa_qa_gladly.json: the owner's 138868/138878 chat with its two earlier exchanges
    # in memory, and a stair-light fault): 6 turns, 7/7 expectations, no guard rejection; the balance
    # came as "לפי מה שרשום אצלנו במערכת …" and the fault opened with care, not gladness.
    # 29 Oct, later (n8n_whatsapp_checkword.py, epoch 88): a request to check something gets willingness to
    # check, never a word that sounds like the answer (138931: "הכל בסדר 🙂" before a ₪2,000 debt), and the
    # quoted "אין בעיה" is "כמובן". Claude-played on the candidate (scripts/wa_qa_checkword.json: 138931's
    # exact input with an empty memory, the same with the chat in memory, a status check): 7/7 and 8/9 then
    # 7/7 on the final text, no guard rejection. The OLD text played the same input well too: a Claude
    # pass cannot see this Gemini slip, so Send's allclear v1 carries the guarantee.
    # 5 Nov (n8n_whatsapp_urgentword.py, epoch 93): an urgent ticket is said as urgent, never "emergency"
    # (155798: "עדכנתי מיד בדחיפות חירום …", read as an emergency service alerted), and the pressing case
    # says what was done and the number, without the recited "only thing I can do". Claude-played on the
    # four real danger turns (155798's "yes", 19 Oct "זה דחוף" and "אין לכם מוקד חירום??", 5 Oct's water
    # on the stairwell light and "שמישהו יתקשר אליי דחוף"): no "חירום" in what is said, no recited line.
    # 5 Nov, later (n8n_whatsapp_caseword.py, epoch 94): each opening word sits with its own case (155838:
    # "בשמחה אסף. פתחתי קריאה על המעלית"). Claude-played: the elevator fault gets "אוי, לא נעים", a balance
    # check keeps "בשמחה"/"כמובן", a frustrated resident keeps "מצטער לשמוע", a bare request to open a
    # ticket keeps its warm sentence.
    # 5 Nov, later still (n8n_whatsapp_gas.py, epoch 95, Yariv's change 2): gas gets no ticket and no note,
    # only the gas company line, word for word. Claude-played on the one real gas report (23 Aug, "יש ריח
    # חזק של גז בכניסה לבניין!!"), gas in the flat, a hedged smell and "what should I do, open the
    # windows?": the line, no tool, no advice; a stuck lift with someone inside and smoke still get the
    # urgent ticket. notify_team and open_request moved with it (gas left their emergency lists).
    # 5 Nov, last (n8n_whatsapp_standing.py, epoch 96, Yariv's change 3): a standing order is recorded with
    # request_standing_order alone and emailed to collections; the prompt says it is neither an arrangement
    # nor a link, and get_payment_link says it is not a link. Claude-played on the candidate
    # (scripts/wa_qa_standing.json): "אפשר לעשות הוראת קבע?" on file, a number not on file moving to one,
    # and a plain "איך משלמים?": 3 conversations, 7 turns, 16/16, no guard rejection. The standing order got
    # the tool alone and its number, "how do I pay" still got the link, and the unknown number was asked its
    # name, building and flat once, with no reason given; no team, no card or bank details.
    # 6 Nov (n8n_whatsapp_retest.py, epoch 97, the Grok tester's run): no recited limits in a danger or gas
    # follow-up, the gas follow-up repeats the gas company, "רואה" joins one voice, the when-line reassures with
    # the matter he told, the link's close is singular, a balance opens with "כמובן". Send's danger v5 rides
    # with it (code, its own cases). Claude-played on the candidate (scripts/wa_qa_retest.json): gas then
    # what to do, smoke then pressing, a manager then cleaning then when, a link then a balance then a week's
    # wait: 4 conversations, 12 turns, 18/18, no guard rejection.
    # 6 Nov, later (n8n_whatsapp_retest2.py, epoch 98, the tester's second run): the when-line's closing
    # question stays on the matter, and a manager request is not "recorded" later either. Claude-played
    # (scripts/wa_qa_retest2.json): the lift's when and re-ask ended on the lift and named 255-1398-26; the
    # manager's when gave the cleaning ticket and no "recorded". The one deck miss was a turn-index slip.
    # 6 Nov, evening (n8n_whatsapp_retest3.py, epoch 99, the tester's third run): the name after the system's
    # greeting even to someone in memory, and the manager's "when" ends on the matter. Claude-played on the
    # candidate (scripts/wa_qa_retest3.json): the status tap and a burst after the menu, each with an earlier
    # chat in memory, both opened "כאן מיכאל מהומי'ז"; the manager's when named 255-1405-26 with no
    # "recorded", its question on the stairwell ("יש עוד משהו על חדר המדרגות שחשוב לך שאוסיף לקריאה?", the
    # deck's one miss, on its words); 11/12.
    # 9 Nov (n8n_whatsapp_feedback9.py, epoch 100, Yariv's written review of the simulated run): the lift
    # company, the lift details, water in a flat, the standing order's call from collections, the emergency
    # line after hours. Claude-played blind on the candidate (scripts/wa_qa_feedback9.json): 5 conversations,
    # 13 turns, 21/21, no guard rejection; its one miss (a second "when" without the lift company) was fixed
    # in the lift line and a blind re-run of the lift went 4/4 with no flag.
    # 10 Nov (n8n_whatsapp_retest6.py, epoch 101, the tester's sixth run): the one-voice exception is named by
    # the matter ("רק במעלית ובהוראת קבע זה אחרת"), not by who. Claude-played blind on the candidate
    # (scripts/wa_qa_retest6.json): the lift and the standing order, 7 turns, 11/11, no guard rejection; the
    # lift company on opening, on both "when"s and on the status, the collections call, and no team anywhere.
    # 10 Nov, later (n8n_whatsapp_retest7.py, epoch 102, the tester's seventh run): the lift line's press loses
    # "לטפל בה בדחיפות", which every lift ticket since epoch 100 gave back as "כמה שיותר מהר". Claude-played
    # blind on the candidate (scripts/wa_qa_retest7.json): the lift arc, 5 turns, 5/5, no guard rejection, no
    # flag; the lift company on opening ("עוקבים אחרי הקריאה ולוחצים עליהם. מתי הם מגיעים לתקן תלוי בהם"), on
    # both "when"s and on the status, with no time and no speed.
    # 11 Nov (n8n_whatsapp_hiintro.py, epoch 103): a bare hello gets "היי, <clock> 👋 כאן מיכאל מהומי'ז. במה אוכל
    # לעזור לך היום?" with no buttons. The greeting paragraph quotes it and says it gave his name, so the next reply
    # neither greets nor says who he is; the tap paragraph no longer says the buttons came with the greeting. Cases
    # and the replay on the candidate; no model run (the owner's rule; his own phone is the test).
    # 11 Nov, later (n8n_whatsapp_hotline.py, epoch 104): every urgent fault gets our emergency line, 077-6687949, at
    # any hour and politely, from his first message about it, even before the ticket; the gas sentence gains it after
    # the gas company. The owner: "0776687949 this is the hotline so all the emergency service redirect them here in
    # a polite way". Cases (13 new, danger v7) and the replay on the candidate; no model run, as for epoch 103.
    # 11 Nov, night (n8n_whatsapp_lineonly.py, epoch 105): an emergency gets our line only, word for word, with no
    # ticket, no note, no building question and no question at the end. The owner: "I DONT WANT IT TO OPEN A TICKET
    # CALL IN OXS JUST POINT THEM TO THE EMERGENCY HOTLINE WE HAVE". Cases (12 new, danger v8) and the replay on the
    # candidate; no model run, as for epochs 103 and 104.
    # 11 Nov, later that night (n8n_whatsapp_confirm.py, epoch 106): a ticket only after the resident's yes; an
    # emergency is anything urgent that cannot wait (Yariv's "כל הבניין נזילת מים" had got urgent ticket 255-1445-26).
    # The owner: "we need to make sure we dont open a service call without confirmation". No model run.
    # 11 Nov, night (n8n_whatsapp_warmline.py, epoch 107): pressed in an emergency, "בחום ... שאפשר להתקשר עכשיו
    # למוקד החירום שלנו" in place of "המוקד הוא המקום לזה עכשיו", which came back word for word as a cold reply; the
    # caring word is "על מה שהוא עובר". From the owner's Grok run of 18:45-19:07 Israel. No model run.
    # 12 Nov (n8n_whatsapp_refline.py, epoch 108): an emergency's first message is "a message like this", the owner's
    # own reference ("אני רק העוזר הדיגיטלי ואין לי אפשרות לתת מענה מיידי. בבקשה תתקשר למוקד החירום שלנו כדי שתוכל
    # לקבל מענה בהקדם: 077-6687949."), in his words and fitting the case, the three things always in it and no
    # question; pressed, the same three things. The owner: "this should be a format it should still be dynamic but
    # that is the reference". Cases and the replay on the candidate; no model run.
    'Answer the resident / system': '504d924d3419',
    'Could not answer / input': 'd9c06797ffa6',
    'Could not answer / system': '88ff96885ec3',
    # 5 Oct evening: the note's words are unchanged; HAY_ALT inside it gained
    # "איך עבר" (retry.py), which only decides whether the rephay reason is added.
    # 18 Oct, evening: names a how-are-you he did not ask for (`unasked`); see above.
    # 18 Oct, late: in a chat about a manager, names neither the echo nor the clerk,
    # names a promise instead, and its unnamed list asks for no bare question.
    # 19 Oct: names a copy of a sent message, opens with "a draft you wrote was not
    # sent", says what was sent arrived, and its tools line names the status lookup.
    # 6 Nov, evening (n8n_whatsapp_retest3.py): the deeds guard's verbs gained recorded, added and updated,
    # and the note's reason names them. Claude-played the retry on C6.4's real first draft (158913, "רשמתי
    # את הפרטים…" with no tool): sent back by `deeds`, the second pass noted the details with notify_team,
    # never mentioned it, and asked for the cheque's photo, with no "we" and nothing fixed.
    # 10 Nov, later (n8n_whatsapp_retest7.py, promise v7): the note's copy of the promise phrases gains
    # "נשלח / ישלחו" + "איש מקצוע / בעל מקצוע", as Send's and Reply usable?'s do; nothing else in it moves.
    # It is n8n_whatsapp_retry.py's own note (check_patchers_idle: retry no longer updates it).
    # 11 Nov, later that night (n8n_whatsapp_confirm.py, epoch 106): "if there is something to open, open it now"
    # waits for his yes, in all four places; and its copy reason never names a draft that gives our line.
    'Try again / note': '89a706c8f03b',
    'Worth a word? / input': '0d3156ee53a4',
    'Worth a word? / system': 'f5f04e9b3f08',
    'get_balance / tool': '1753e9c90dba',
    'get_payment_link / tool': '2dd75e741bfc',   # 5 Nov, epoch 96: a standing order is not a link
    'request_standing_order / tool': '9d18f612c2fd',   # 5 Nov, epoch 96: new; 9 Nov, epoch 100: collections will phone
    # 19 Oct: called first, with nothing; the number they write from finds their
    # tickets; a reference or a building only when it found nothing (norepeat.py).
    'get_request_status / tool': 'd9a90bd9c2c0',   # 6 Nov, epoch 98: names each ticket by its reference
    'get_service_info / tool': '18ca3d507731',
    'notify_team / tool': '82a6b8569159',     # 18 Oct, late: the reason, never an empty note; 29 Oct, night: and
    # something new about an open ticket is add_request_detail's; 5 Nov (gas.py): never for gas; 11 Nov, night
    # (lineonly.py, epoch 105): never for an emergency either, and reason has no `emergency`; later that night
    # (confirm.py, epoch 106): nor for anything else urgent, like a big leak
    # 30 Oct, morning (n8n_whatsapp_name.py, epoch 91): reporter_name and name_declined, and when to ask: only
    # after need_name, once (the owner: "ok we need to include the name in that wtf"); debt-tools v138
    # names a tenant on file from the record and asks the rest (NAME_REQUIRED_CHANNELS voice,whatsapp).
    # 5 Nov (n8n_whatsapp_gas.py, epoch 95): urgency's emergency no longer lists gas; gas is never a ticket.
    # 9 Nov (n8n_whatsapp_feedback9.py, epoch 100): fault_location no longer names "the flat above" a building fault.
    # 11 Nov, night (n8n_whatsapp_lineonly.py, epoch 105): never for an emergency, and urgency has no `emergency`.
    # 11 Nov, later that night (n8n_whatsapp_confirm.py, epoch 106): never without the resident's yes, and never for
    # anything urgent; a lift that is down with nobody inside is a fault, urgency high.
    'open_request / tool': '6bf840fa6406',
    'show_menu / tool': '427d364be55d',
    'verify_address / tool': '1d0288dbbe17',   # 11 Nov, night (lineonly.py): no "location during an emergency"
}


# ---------------------------------------------------------------------------
# Reading workflows
# ---------------------------------------------------------------------------
def api(path):
    for attempt in range(3):
        try:
            return W.api("GET", path)
        except Exception:  # noqa: BLE001 -- a slow n8n is not a failed check
            if attempt == 2:
                raise
            time.sleep(2)


def load_live():
    return api("/api/v1/workflows/%s" % WORKFLOW_ID)


def load_candidate(files):
    """Live, with every node a patcher's --dump would change put in its place.

    5 Oct (n8n_whatsapp_safetynet.py): a dump that ADDS or REMOVES nodes is the
    would-be workflow whole -- its nodes and its wires -- because laying it over
    live only where a name already exists (the rule until then) kept the removed
    nodes, dropped the new ones, and so tested code that would never run. A dump
    with the same node names as live is laid over it exactly as before."""
    wf = load_live()
    idx = {n["name"]: i for i, n in enumerate(wf["nodes"])}
    for f in files:
        dumped = json.load(open(f, encoding="utf-8"))
        names = {n["name"] for n in dumped["nodes"]}
        if names != set(idx) and "connections" in dumped:
            for name in sorted(names - set(idx)):
                print("candidate: + %s from %s" % (name, os.path.basename(f)))
            for name in sorted(set(idx) - names):
                print("candidate: - %s (not in %s)" % (name, os.path.basename(f)))
            wf = dict(wf, nodes=dumped["nodes"], connections=dumped["connections"])
            idx = {n["name"]: i for i, n in enumerate(wf["nodes"])}
            continue
        for n in dumped["nodes"]:
            i = idx.get(n["name"])
            if i is not None and wf["nodes"][i] != n:
                wf["nodes"][i] = n
                print("candidate: %s from %s" % (n["name"], os.path.basename(f)))
    return wf


def load_execution(eid):
    return api("/api/v1/executions/%s?includeData=true" % eid)["workflowData"]


def inner(expr):
    """The JavaScript between `={{` and `}}`."""
    s = (expr or "").strip()
    if s.startswith("="):
        s = s[1:].strip()
    if not (s.startswith("{{") and s.endswith("}}")):
        sys.exit("Not an n8n expression: %r" % s[:60])
    return s[2:-2].strip()


def extract(wf):
    """The code the harness runs, straight out of the workflow."""
    by = {n["name"]: n for n in wf["nodes"]}
    code = by["Sort"]["parameters"]["jsCode"]
    a = code.find("const bare = text.trim()")
    b = code.find("const isGreeting =", a)
    if a == -1 or b == -1:
        sys.exit("Sort's greeting test is not where this check expects it -- read the live code.")
    b = code.index(";", b) + 1

    def conds(name):
        # 5 Oct: `Second try usable?` is gone and `Claimed a ticket?` is new
        # (n8n_whatsapp_safetynet.py); a node that is not there has no conditions.
        if name not in by:
            return {}
        return {c["id"]: inner(c["leftValue"])
                for c in by[name]["parameters"]["conditions"]["conditions"]}

    mend = by.get("Mend the reply")
    return {
        "sort_greeting": code[a:b],
        "send_body": inner(by["Send"]["parameters"]["jsonBody"]),
        "reply_usable": conds("Reply usable?"),
        "second_try": conds("Second try usable?"),
        # 5 Oct: the last resort, no model (n8n_whatsapp_safetynet.py).
        "claimed": conds("Claimed a ticket?"),
        "mend": inner(mend["parameters"]["jsonOutput"]) if mend else "",
        "outage_gate": conds("Outage reply usable?"),
        "worth_text": inner(by["Worth a word?"]["parameters"]["text"]),
        "word_gate": inner(conds_raw(by, "A word first?", "word")),
        # 1 Oct evening: it decides what the answering model is told was sent.
        "carry_on": inner(by["Carry on"]["parameters"]["jsonOutput"]),
        "inject": inner(by["Answer the resident"]["parameters"]["text"]),
        "try_again": inner(by["Try again"]["parameters"]["jsonOutput"]),
        # 1 Oct: it reads "you", and the bot's "you" went singular.
        "team_note": inner(conds_raw(by, "Team note this turn?", "teamnote")),
        # 6 Nov (n8n_whatsapp_retest3.py): which run answers a burst, the text it hands the model,
        # and whether it tells the model the menu went out.
        "last_word": (by.get("Still the last word?") or {}).get("parameters", {}).get("jsCode", ""),
        # 11 Nov (n8n_whatsapp_hiintro.py): the greeting's sentence in Sort, and what posts it.
        "sort_menu": (code[max(0, code.find("const MENU = {") - 400):code.find("};", code.find("const MENU = {")) + 2]
                      if "const MENU = {" in code else ""),
        "send_menu_body": (by.get("Send menu") or {}).get("parameters", {}).get("jsonBody", ""),
        # 11 Nov (n8n_whatsapp_hotline.py): the prompt, so a case can hold what it says about our emergency line.
        "prompt": ((by["Answer the resident"]["parameters"].get("options") or {}).get("systemMessage") or ""),
        # 11 Nov, night (n8n_whatsapp_warmline.py): the memory key, so a prompt-only epoch's cases can be keyed to it
        # and go back with it on a restore.
        "memory_key": ((by.get("Conversation so far") or {}).get("parameters") or {}).get("sessionKey") or "",
    }


def conds_raw(by, name, cid):
    for c in by[name]["parameters"]["conditions"]["conditions"]:
        if c.get("id") == cid:
            return c["leftValue"]
    sys.exit("No condition %r on %r." % (cid, name))


# ---------------------------------------------------------------------------
# The pins: every text a model reads
# ---------------------------------------------------------------------------
def model_texts(wf):
    by = {n["name"]: n for n in wf["nodes"]}
    out = {}
    for name in ("Answer the resident", "Worth a word?", "Say it again", "Could not answer"):
        if name not in by:          # 5 Oct: `Say it again` is gone (safetynet.py)
            continue
        p = by[name]["parameters"]
        out[name + " / system"] = (p.get("options") or {}).get("systemMessage") or ""
        out[name + " / input"] = p.get("text") or ""
    out["Try again / note"] = by["Try again"]["parameters"].get("jsonOutput") or ""
    for n in wf["nodes"]:
        if n["type"].endswith("Tool") or n["type"].endswith("toolCode"):
            p = n["parameters"]
            # The description and the parameter docs are what the model reads.
            out[n["name"] + " / tool"] = json.dumps(
                {k: p.get(k) or "" for k in ("toolDescription", "description", "jsonBody")},
                ensure_ascii=False, sort_keys=True)
    return out


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


# 4 Oct: "typing…" (n8n_whatsapp_typing.py). Two side-branch calls to Meta whose
# whole correctness is where they hang and where they are drawn: executionOrder
# v1 runs a node's children top to bottom, so one drawn below a sibling would
# show "typing…" after the reply. The patcher's own problems() is the check.
def check_typing(wf):
    import n8n_whatsapp_typing as TY
    print("--- typing indicator (n8n_whatsapp_typing.py) ---")
    names = {n["name"] for n in wf["nodes"]}
    if not any(name in names for name in TY.PARENTS):
        print("not on this workflow")
        return 0
    probs = TY.problems(wf)
    if not probs:
        print("both nodes right: Meta's typing call, side branches, each above its siblings")
        return 0
    for p in probs:
        print("FAIL " + p)
    return len(probs)


# 19 Oct: `Forget the draft` (n8n_whatsapp_norepeat.py). A Chat Memory Manager on
# the agent's buffer whose whole correctness is where it hangs and where it is
# drawn: executionOrder v1 runs it before the agent only when it is drawn above.
# retry.forget_problems() is the check, run by the carrier before any write too.
def check_forget(wf):
    import n8n_whatsapp_retry as R
    print("--- Forget the draft (n8n_whatsapp_retry.py) ---")
    if R.FORGET not in {n["name"] for n in wf["nodes"]}:
        print("not on this workflow")
        return 0
    probs = R.forget_problems(wf["nodes"], wf.get("connections") or {})
    if not probs:
        print("right: a side branch off Try again, drawn above the agent, on its memory, "
              "deleting the first pass's two messages")
        return 0
    for p in probs:
        print("FAIL " + p)
    return len(probs)


def check_pins(wf):
    now = {k: fingerprint(v) for k, v in model_texts(wf).items()}
    bad = sorted(k for k in set(now) | set(PINS) if now.get(k) != PINS.get(k))
    print("--- pins: every text a model reads ---")
    if not bad:
        print("all %d unchanged" % len(now))
        return 0
    for k in bad:
        print("FAIL model-facing text changed: %s  (%s -> %s)" % (k, PINS.get(k), now.get(k)))
    print("     Replay the real inputs that reach that model, with Claude playing it,")
    print("     then paste the new values from --pins. Never OpenRouter for the test.")
    return len(bad)


# ---------------------------------------------------------------------------
# The real history, read at run time, never written to disk
# ---------------------------------------------------------------------------
def rows(query):
    e = W.env()
    base = e["SUPABASE_URL"].rstrip("/") + "/rest/v1/"
    key = e["SUPABASE_SERVICE_ROLE_KEY"].strip()
    out, off = [], 0
    while True:
        req = urllib.request.Request(base + query, headers={
            "apikey": key, "Authorization": "Bearer " + key, "Range": "%d-%d" % (off, off + 999)})
        chunk = json.loads(urllib.request.urlopen(req, timeout=60).read() or b"[]")
        out += chunk
        if len(chunk) < 1000:
            return out
        off += 1000


def corpus():
    inbound = [r["body"] for r in rows("messages?direction=eq.inbound&select=body&order=created_at.asc")
               if r.get("body")]
    outbound = [r["body"] for r in rows("messages?direction=eq.outbound&sender=eq.bot&select=body"
                                        "&order=created_at.asc") if r.get("body")]
    return {"inbound": inbound, "outbound": outbound}


def node(payload):
    sys.stdout.flush()          # our lines first, then Node's
    r = subprocess.run(["node", JS], input=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    return r.returncode


# ---------------------------------------------------------------------------
# --watch: real turns since a moment, against the owner's rules
# ---------------------------------------------------------------------------
BOT_HELLO = re.compile(r"^(שלום רב|שלום|היי|הי|אהלן|בוקר טוב|צהריים טובים|ערב טוב|לילה טוב|שבוע טוב|"
                       r"שבת שלום|חג שמח|יום טוב)( לכם| לך| לכולם)?(?=[\s,.!:;]|$)")
LEAD = re.compile(r"^[\W_]+")
# 8 Oct: the menu says "כאן הומי'ז" (n8n_whatsapp_menuline.py); real rows from before
# carry the old tail, so --watch and the replay know both.
MENUS = ("👋 כאן הומי'ז. במה אפשר לעזור?", "👋 במה אפשר לעזור?")
PAY = re.compile(r"תשלום|לשלם|שילמ|קישור|לינק|חוב|יתרה|חשבון|pay|link|debt|balance|owe|bill|invoice",
                 re.I)
ECHO = re.compile(r"(^|[.!?,:]\s*)(אני מבין|אני מבינה|הבנתי|שמעתי)\s+ש")
# 29 Oct, evening: "so I can verify / check it" is not the clerk (n8n_whatsapp_retry.CLERK_RE).
CLERK = re.compile(r"כדי שאוכל(?!(\s+\S+)?\s+(לאמת|לבדוק))|אצטרך")
# 29 Oct, evening (n8n_whatsapp_ionly.py): one voice, Michael's. The owner: "there is no the team only
# the agent ... there shouldnt be a i will pass this to the team or the team will check it or the
# manager is on the review it should be i and i only". A team or management in a reply (his own
# "מצוות השירות" aside), the manager by article, something passed on, or "they / we will" do it.
# 29 Oct, late (n8n_whatsapp_checkword.py): an all-clear in a turn that looked something up. Send cuts the
# interjection and the joined form ("allclear v1"); this flags any form left, the "שהכל בסדר" kind included.
ALL_CLEAR = re.compile(r"(?<![א-ת])[ושכ]?(הכל|הכול)\s+(בסדר|טוב|תקין)(?![א-ת])")
# 29 Oct, night (n8n_whatsapp_addto.py): "I added it / the photo to the ticket" in a turn where no tool
# added anything. 139178 and 139189 said so after a note that never touches a ticket (and was dropped as
# a duplicate besides). Backed only by add_request_detail or open_request answering ok in that turn.
ADDED_CLAIM = re.compile(r"(?<![א-ת])ו?(הוספתי|צירפתי|עדכנתי)(?![א-ת])[^.!?\n]{0,40}?(?<![א-ת])[לבה]?קריא[הת]")
ADDED_OK = re.compile(r'\\*"ok\\*"\s*:\s*true')


def opened_this_turn(rd):
    """Whether open_request answered ok on any pass of this run."""
    for run in rd.get("Answer the resident") or []:
        for out in ((run.get("data") or {}).get("main") or []):
            for it in out or []:
                for s in ((it or {}).get("json") or {}).get("intermediateSteps") or []:
                    if ((s or {}).get("action") or {}).get("tool") == "open_request" \
                            and ADDED_OK.search(str(s.get("observation"))):
                        return True
    return False
# 11 Nov, later that night (n8n_whatsapp_confirm.py): a ticket opens only after the resident's yes. Michael's last
# message offered one (a question about opening a ticket), or the resident asked for one in so many words.
OFFERED = re.compile(r"(?:לפתוח|שאפתח|אפתח)[^.!?\n]{0,60}קריא[^.!?\n]{0,40}\?|קריא[^.!?\n]{0,60}(?:לפתוח|שאפתח|אפתח)"
                     r"[^.!?\n]{0,40}\?")
ASKED_TICKET = re.compile(r"(?<![א-ת])ו?(?:תפתח|תפתחי|תפתחו|פתח|לפתוח|אפשר לפתוח)(?![א-ת])[^.!?\n]{0,30}קריא"
                          r"|קריא[^.!?\n]{0,30}(?<![א-ת])(?:תפתח|לפתוח)(?![א-ת])")


def added_this_turn(rd):
    """Whether add_request_detail or open_request answered ok on any pass of this run."""
    for run in rd.get("Answer the resident") or []:
        for out in ((run.get("data") or {}).get("main") or []):
            for it in out or []:
                for s in ((it or {}).get("json") or {}).get("intermediateSteps") or []:
                    tool = ((s or {}).get("action") or {}).get("tool")
                    if tool in ("add_request_detail", "open_request") and ADDED_OK.search(str(s.get("observation"))):
                        return True
    return False
# 9 Nov (n8n_whatsapp_feedback9.py): "someone from the collections team will phone you" is said on a
# standing order, at the client's word, so "צוות הגבייה" is not someone acting in Michael's place.
TEAM_VOICE = re.compile(r"(?<![א-ת])(?!(?:מ|ב)צוות השירות)(?!(?:מ|ב|ל)?צוות הגבייה)[א-ת]{0,3}צוות|(?<![א-ת])[א-ת]{0,3}הנהלה"
                        r"|(?<![א-ת])ו?[הל]מנהל(?![א-ת])"
                        r"|(?<![א-ת])[ושכ]?(העברתי|העברנו|אעביר|נעביר|יבדקו|יטפלו|יחזרו|יעדכנו|ידאגו"
                        r"|נבדוק|נטפל|נחזור|נעדכן|שנוכל)(?![א-ת])")
# 5 Oct: a ticket claim and a ticket number, the shapes wa_truth.py's PHANTOM and
# REF read (there as JS for n8n, here for the watch).
TICKET_CLAIM = re.compile(r"(פתחתי|פתחנו|פותח|פותחת|נפתחה|נפתחו|נפתחת)( \S+){0,2}? ?ה?קריא[הת]")
REF = re.compile(r"\b\d{3}-\d{3,6}-\d{2}\b")
# 1 Oct: the bot writes to one person, masculine until she writes about herself
# in the feminine (n8n_whatsapp_gender.py). One copy, read by --watch here and by
# wa_qa.py's rubric. "you" in the plural, as a pronoun or a verb:
# 11 Nov, evening: "תתקשרו" and "תחייגו" too. The owner's Grok run had "תתקשרו עכשיו למוקד החירום שלנו" three
# times, and this watch said "nothing broke the rules" (Send's line v1 now makes it "אפשר להתקשר").
PLURAL_YOU = re.compile(r"(?:^|\W)(?:ו|ש|כש)?(אתם|לכם|אתכם|אליכם|שלכם|איתכם|עבורכם|בשבילכם|אצלכם|"
                        r"מכם|ממכם|עליכם|תרצו|תוכלו|תצטרכו|תשלחו|תכתבו|תגידו|תספרו|תבדקו|תעדכנו|"
                        r"תפנו|תבחרו|תקבלו|תראו|תשלמו|ספרו|תתקשרו|תחייגו)(?=\W|$)")
# "you", masculine only and feminine only. Future 2nd person masculine is also
# 3rd person feminine ("היא תוכל"), so a hit is read, not trusted.
MASC_YOU = re.compile(r"(?:^|\W)(?:ו|ש|כש)?(אתה|תוכל|תרצה|תצטרך|תשלח|תכתוב|תגיד|תספר|תבדוק|תעדכן|"
                      r"תפנה|תבחר|תשלם|תודיע|ספר לי|שלח לי|כתוב לי|מוזמן)(?=\W|$)")
FEM_YOU = re.compile(r"(?:^|\W)(?:ו|ש|כש)?(תוכלי|תרצי|תצטרכי|תשלחי|תכתבי|תגידי|תספרי|תבדקי|תעדכני|"
                     r"תפני|תבחרי|תשלמי|תודיעי|ספרי לי|שלחי לי|כתבי לי|מוזמנת|את בטוחה)(?=\W|$)")
# A woman writing about herself: "אני" and a feminine present form. "אני" is
# required -- "המעלית צריכה" is the lift, not the resident.
FEM_CUE = re.compile(r"(?:^|\W)(?:ו|ש|כש|כי )?אני\s+(?:לא\s+|כבר\s+|עדיין\s+|ממש\s+|גם\s+|פשוט\s+)?"
                     r"(צריכה|יכולה|גרה|יודעת|מבקשת|מעוניינת|בטוחה|חושבת|שואלת|כותבת|מחפשת|מתקשרת|"
                     r"עובדת|נמצאת|זקוקה|מוכנה|מצטערת|מרגישה|משלמת|מגיעה|יוצאת|חוזרת|שומעת|מבינה|"
                     r"זוכרת|אמורה|מודאגת|לחוצה)(?=\W|$)")


def mask(s, n=110):
    s = re.sub(r"https?://\S+", "<link>", str(s))
    s = re.sub(r"\+?\d{9,15}", "<phone>", s)
    # Israeli numbers the way people type them, with a hyphen or spaces
    # (052-7654321, 050 123 4567, +972-52-765-4321): the line above only took
    # unbroken digits (4 Oct). A ticket reference (255-1490-26) starts with no 0.
    s = re.sub(r"(?:\+972[\s\-]?|\b0)(?:[23489]|[57]\d)[\s\-]?\d{3}[\s\-]?\d{4}\b", "<phone>", s)
    return re.sub(r"\s+", " ", s)[:n]


def watch(since):
    ids, cursor = [], None
    while True:
        page = api("/api/v1/executions?workflowId=%s&limit=100%s"
                   % (WORKFLOW_ID, "&cursor=%s" % cursor if cursor else ""))
        fresh = [x for x in page["data"] if x["startedAt"] >= since]
        ids += [x["id"] for x in fresh]
        cursor = page.get("nextCursor")
        if not cursor or len(fresh) < len(page["data"]):
            break
    flagged, turns, menus, cut = 0, 0, [], 0
    she = set()                           # residents seen writing in the feminine
    try:                                  # the promise phrases, one list (1 Oct)
        from n8n_whatsapp_nopromise import PROMISE_PY, hits as promise_hits
    except Exception:  # noqa: BLE001 -- the watch still runs without it
        PROMISE_PY = promise_hits = None
    for eid in sorted(ids, key=int):
        ex = api("/api/v1/executions/%s?includeData=true" % eid)
        rd = ((ex.get("data") or {}).get("resultData") or {}).get("runData") or {}

        def first(name):
            try:
                return rd[name][0]["data"]["main"][0][0]["json"]
            except Exception:  # noqa: BLE001
                return None

        def items(name):
            try:
                return [i["json"] for i in rd[name][0]["data"]["main"][0]]
            except Exception:  # noqa: BLE001
                return None

        S = first("Sort") or {}
        if S.get("text") is None and S.get("greeting") is not True:
            continue                      # a delivery receipt, not a resident's message
        turns += 1
        canned = S.get("greeting") is True
        sent = []
        for name, kind in (("Say it now", "ack"), ("Send", "menu" if canned else "answer"),
                           ("Send the rest", "rest")):
            j = first(name)
            if j and j.get("content"):
                sent.append((kind, str(j["content"])))
        prev = next((str(r.get("body") or "") for r in (items("Anything newer?") or [])
                     if r.get("direction") == "outbound"), "")
        after_menu = any(m in prev for m in MENUS) or "במה אפשר לעזור" in str(S.get("last_bot") or "")
        flags, infos = [], []
        hellos = [k for k, t in sent if BOT_HELLO.match(LEAD.sub("", t))]
        if len(hellos) > 1:
            flags.append("two greetings in one turn (%s)" % " + ".join(hellos))
        rep_tap = S.get("tap") == "other"
        if not canned and after_menu and not rep_tap and sent and BOT_HELLO.match(LEAD.sub("", sent[0][1])):
            flags.append("a greeting right after the menu (%s)" % sent[0][0])
        # 11 Nov, later that night (n8n_whatsapp_confirm.py): no ticket without the resident's yes. 173670 opened
        # 255-1445-26 straight after the hello, on "כל הבניין נזילת מים".
        if not canned and opened_this_turn(rd) and S.get("tapped_open") is not True \
                and not OFFERED.search(prev + " " + str(S.get("last_bot") or "")) \
                and not ASKED_TICKET.search(str(S.get("text") or "")):
            flags.append("a ticket opened with no yes from the resident")
        # 1 Oct evening: the לדבר עם נציג tap opens "hi, how are you, this is
        # Michael" (n8n_whatsapp_rephello.py). The name is the one thing the
        # filter cannot add, so its absence is a flag; the hello's form is read.
        # 4 Oct (n8n_whatsapp_rephay.py): and it asks how he is, the one question
        # (execution 80740 asked how to help instead). `rephay` sends such a reply
        # back once, so a flag here means the second pass went out without it too.
        if not canned and rep_tap:
            answers = [t for k, t in sent if k == "answer"]
            if answers and "מיכאל" not in answers[0]:
                flags.append("the representative tap answered without the name")
            from n8n_whatsapp_retry import HAY_PY as hay
            if answers and not hay.search(answers[0]):
                flags.append("the representative tap answered without asking how he is")
            if answers and re.search(r"במה (אפשר|אוכל|אני יכול) לעזור|איך (אפשר|אני יכול) לעזור|how can i help",
                                     answers[0], re.I):
                infos.append("the representative's hello also asked how to help")
            if answers:
                h = BOT_HELLO.match(LEAD.sub("", answers[0]))
                if not h:
                    infos.append("the representative tap answered without a hello")
                elif h.group(1) in ("בוקר טוב", "צהריים טובים", "ערב טוב", "שלום"):
                    infos.append("the representative's hello is the hour's word the menu used: %s" % h.group(1))
        if not canned and S.get("greeted") is True and not after_menu:
            named = [k for k, t in sent if "מיכאל" in t]
            if named:
                flags.append("the name mid-conversation (%s)" % " + ".join(named))
        # 1 Oct evening: the gate's own payment words (n8n_whatsapp_payack.py), so a
        # flag here means the gate let through what it should have held.
        try:
            from n8n_whatsapp_firstword import PAY_PY as pay
        except Exception:  # noqa: BLE001 -- the watch still runs without it
            pay = PAY
        said = str((first("Carry on") or {}).get("text") or S.get("text") or "")
        if first("Say it now"):
            if not pay.search(said):
                flags.append("a payment ack on a message with no payment words")
        else:
            wrote = str((first("Worth a word?") or {}).get("output") or "").strip()
            if wrote and wrote.upper() != "NONE":
                infos.append("the ack model wrote a note and the gate held it: %s" % mask(wrote, 60))
        # 18 Oct, late (n8n_whatsapp_procedure.py): in a chat about a manager or a
        # person, "I understand you" and the reason for asking are what the owner
        # asked for, so they are an info line there, not a flag. The same test as
        # the guards (retry.MGR_CTX): the resident's own rows, the tap's row aside.
        # 19 Oct: this message and the one before it, a pasted tap text taken off
        # (retry.mgr_py, the guards' own test in Python).
        from n8n_whatsapp_retry import mgr_py
        newer = items("Anything newer?") or []
        mgr = mgr_py([str(r.get("body") or "") for r in newer if r.get("direction") == "inbound"])
        # 19 Oct (n8n_whatsapp_norepeat.py): what went out is not what the phone
        # already had. The `repeat` guard's own test (wa_truth.repeats_py) on the
        # bot's last three rows; a flag here means the guard let a copy through.
        from wa_truth import repeats_py
        had = [str(r.get("body") or "") for r in newer if r.get("direction") == "outbound"]
        for k, t in sent:
            if k == "answer" and not canned and repeats_py(t, had):
                flags.append("the answer repeats what the phone already had: %s" % mask(t, 60))
        for k, t in sent:
            if ECHO.search(t):
                (infos if mgr else flags).append(
                    "'I understand that...' in the %s%s"
                    % (k, " (known gap: the ack's own wording)" if k == "ack"
                       else " (a chat about a manager: wanted)" if mgr else ""))
            if CLERK.search(t):
                (infos if mgr else flags).append("the clerk's 'so that I can / I will need' in the %s%s"
                                                 % (k, " (a chat about a manager: wanted)" if mgr else ""))
            m = TEAM_VOICE.search(t)
            if m and not canned:
                flags.append("someone other than Michael in the %s: %s" % (k, m.group(0)))
            looked = any((((run.get("data") or {}).get("main") or [[{}]])[0][0].get("json") or {}).get("intermediateSteps")
                         for run in (rd.get("Answer the resident") or []))
            m = ALL_CLEAR.search(t)
            if m and looked and not canned and k != "ack":
                flags.append("an all-clear in a turn that looked something up, in the %s: %s" % (k, m.group(0)))
            m = ADDED_CLAIM.search(t)
            if m and not canned and k != "ack" and not added_this_turn(rd):
                flags.append("a ticket said to be added to, with nothing added this turn, in the %s: %s"
                             % (k, m.group(0)))
        # 1 Oct: Send removes promises (n8n_whatsapp_nopromise.py). A promise in
        # what went out is a flag; the ack and the first beat of a two-part
        # payment reply may say "I'm on it". One the filter cut is an info line.
        # 5 Oct (promise v3): a phrase is a promise only as Send reads it -- not
        # in a reported request, a wish or "I can't say when". hits() runs Send's
        # own definitions in Node; without Node, the bare phrase list as before.
        if PROMISE_PY is not None and not canned:
            two_beat = any(k == "rest" for k, _ in sent)
            raw = str((first("Type for a moment") or {}).get("output") or "")
            texts = [t for _, t in sent] + [raw]
            left = None
            if promise_hits is not None and any(PROMISE_PY.search(t) for t in texts):
                left = promise_hits(texts)
            if left is None:
                left = [[m.group(0).strip() for m in PROMISE_PY.finditer(t)] for t in texts]
            for (k, t), hs in zip(sent, left):
                if hs and (k == "rest" or (k == "answer" and not two_beat)):
                    flags.append("a promise in the %s: %s" % (k, hs[0]))
            answers = [hs for (k, _), hs in zip(sent, left) if k == "answer"]   # none when Send failed
            if raw and answers and not two_beat and not any(answers) and left[-1]:
                cut += 1
                infos.append("the model wrote a promise and the filter cut it: %s" % mask(left[-1][0], 40))
        # 1 Oct: one person, in the singular; feminine once she has written in
        # the feminine (in this window: an earlier cue is not seen, so a
        # feminine reply with no cue here is an info line, not a flag).
        if not canned:
            who = str(S.get("to") or "")
            if FEM_CUE.search(str(S.get("text") or "")):
                she.add(who)
            for k, t in sent:
                m = PLURAL_YOU.search(t)
                if m:
                    flags.append("plural 'you' in the %s: %s" % (k, m.group(1)))
                m = MASC_YOU.search(t)
                if m and who in she:
                    flags.append("masculine to a resident who wrote in the feminine, in the %s: %s"
                                 % (k, m.group(1)))
                m = FEM_YOU.search(t)
                if m and who not in she:
                    infos.append("feminine with no feminine cue in this window, in the %s: %s"
                                 % (k, m.group(1)))
        # 4 Oct: "typing…" is Meta's answer to a side call that continues on
        # error, so a failure shows nowhere but here.
        for name in ("Show typing", "Show typing again"):
            for run in rd.get(name) or []:
                try:
                    j = run["data"]["main"][0][0]["json"]
                except Exception:  # noqa: BLE001
                    continue
                if j.get("success") is not True:
                    infos.append("%s did not show: %s" % (name, mask(json.dumps(j.get("error") or j,
                                                                             ensure_ascii=False), 90)))
        # 5 Oct (n8n_whatsapp_safetynet.py): the last resort is no model now.
        # `Mend the reply` ran = both passes were rejected; what it did is an info
        # line, and a turn where it ran and nothing went out is a flag (the old
        # `Second try usable?` sent nothing on a failure).
        rescued = ""
        rescue = first("Open it anyway")
        if rescue:
            try:
                r = rescue["results"][0]["result"]
                rescued = str((json.loads(r) if isinstance(r, str) else r).get("reference") or "")
            except Exception:  # noqa: BLE001
                rescued = "?"
        mend = first("Mend the reply")
        if mend is not None:
            infos.append("the last resort ran (%s)%s" % (mend.get("mended") or "?",
                                                         ", rescue ticket %s" % rescued if rescue else ""))
            if not any(k == "answer" for k, _ in sent):
                flags.append("the last resort ran and nothing went out")
        # A ticket claim is backed by any real number in the chat, so a NEW claim
        # quoting an OLD ticket's number passes the checks (5 Oct, a known gap).
        # Shown here, to be read: the same matter, or another one?
        given = rescued
        for run in rd.get("Answer the resident") or []:
            try:
                for st in run["data"]["main"][0][0]["json"].get("intermediateSteps") or []:
                    given += " " + str(st.get("observation") or "")
            except Exception:  # noqa: BLE001
                continue
        for k, t in sent:
            if k == "answer" and TICKET_CLAIM.search(t):
                old = [x for x in REF.findall(t) if x not in given]
                if old:
                    infos.append("a ticket claim with a number no tool gave this turn: %s (the same matter?)"
                                 % ", ".join(old))
        if "Tell the team the bot is down" in rd:
            flags.append("the outage path ran")
        if ex.get("status") != "success":
            flags.append("execution status: %s" % ex.get("status"))
        if "Still the last word?" in rd and items("Still the last word?") == []:
            newest_in = next((r for r in (items("Anything newer?") or [])
                              if r.get("direction") == "inbound"), None)
            if newest_in and newest_in.get("message_type") == "greeting":
                flags.append("a real message stood down for a greeting (it may go unanswered)")
        if canned:
            menus.append((str(S.get("to")), ex["startedAt"], eid))
        if flags or infos:
            flagged += 1 if flags else 0
            print("%s %s  %s UTC" % ("FLAG" if flags else "INFO", eid, ex["startedAt"][:19].replace("T", " ")))
            for f in flags:
                print("     - " + f)
            for f in infos:
                print("     info: " + f)
            print("     resident: " + mask(S.get("text") or ""))
            for k, t in sent:
                print("     %-8s: %s" % (k, mask(t)))
    menus.sort()
    for (a, ta, ia), (b, tb, ib) in zip(menus, menus[1:]):
        if a == b and _secs(ta, tb) <= 20:
            flagged += 1
            print("FLAG %s + %s  two menus to one resident within 20 s" % (ia, ib))
    print("")
    print("watched %d resident turns since %s: %s%s" % (
        turns, since, "%d flagged" % flagged if flagged else "nothing broke the rules",
        "; the filter cut a promise from %d" % cut if cut else ""))
    return flagged


def _secs(a, b):
    from datetime import datetime
    f = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))  # noqa: E731
    return abs((f(b) - f(a)).total_seconds())


# ---------------------------------------------------------------------------
def main():
    argv = sys.argv[1:]
    if "--watch" in argv:
        since = argv[argv.index("--watch") + 1]
        sys.exit(1 if watch(since) else 0)

    if "--candidate" in argv:
        i = argv.index("--candidate") + 1
        files = []
        while i < len(argv) and not argv[i].startswith("--"):
            files.append(argv[i])
            i += 1
        wf, label = load_candidate(files), "candidate"
    elif "--execution" in argv:
        eid = argv[argv.index("--execution") + 1]
        wf, label = load_execution(eid), "the workflow execution %s ran" % eid
    else:
        wf, label = load_live(), "live"

    if "--pins" in argv:
        print("PINS = {")
        for k, v in sorted(model_texts(wf).items()):
            print("    %r: %r," % (k, fingerprint(v)))
        print("}")
        return

    print("checking %s" % label)
    print("")
    bad = check_pins(wf)
    print("")
    bad += check_typing(wf)
    print("")
    bad += check_forget(wf)
    print("")
    # 5 Oct: the live run's 37 promise cuts, each a case (promise v3).
    fixture = json.load(open(os.path.join(HERE, "wa_promise_live_05oct.json"), encoding="utf-8"))
    bad += 1 if node({"mode": "cases", "code": extract(wf), "promise_live": fixture["cases"]}) else 0
    if "--replay" in argv:
        print("")
        print("=== replay: every real message, live code vs %s ===" % label)
        bad += 1 if node({"mode": "replay", "live": extract(load_live()), "cand": extract(wf),
                          "corpus": corpus()}) else 0
    print("")
    print("RESULT: %s" % ("FAILED" if bad else "all green"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
