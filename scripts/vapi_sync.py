"""Push the written prompts to Vapi.

The markdown is the source of truth. This script extracts the system prompt and
the first message from it, builds the assistant payload, and creates or updates
the assistant by name. Editing in the Vapi dashboard puts the two out of sync
silently — edit the markdown and re-run this instead.

    python scripts/vapi_sync.py debt              # show what would change
    python scripts/vapi_sync.py debt --apply      # write it
    python scripts/vapi_sync.py inbound --apply

Reads VAPI_PRIVATE_KEY from .env. Never takes a key on the command line.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vapi_tools import DEBT_TOOLS, INTAKE_TOOLS, with_server
from voice_guard import voice_with_guard, SPEECH

# The Windows console defaults to cp1252 and cannot print Hebrew.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")
API = "https://api.vapi.ai"

# Shared by both assistants. HilaNeural is female, which is why every written
# line is feminine first person.
#
# On the Hebrew transcriber: this used to say Azure was the only one that exists.
# That was true of Deepgram nova-2, which has no `he` at all, but nova-3 added
# it — and 11labs, speechmatics and soniox accept `he` too. Azure is no longer
# the default; it is the fallback. See the transcriber block below for what
# replaced it and on what evidence. Measure any swap with scripts/vapi_latency.py.
BASE = {
    # The stack chosen in the dashboard on 5 Aug, captured here so it survives.
    #
    # Scribe v2 tops the published Hebrew ASR benchmarks and the dashboard puts
    # it at 2.4% WER, 570ms and $0.013 a minute — better *and* cheaper than the
    # Azure he-IL it replaces, which measured $0.032. The reservation held
    # against it earlier was that 11labs takes a free-text model name Vapi
    # cannot validate; the dashboard has now supplied the exact string, which
    # settles that empirically rather than by argument.
    #
    # Deepgram nova-3 held this slot for about an hour on price alone and went
    # out on evidence: it appears nowhere in any survey of Hebrew ASR. The
    # saving was illusory anyway — a misheard turn costs a re-ask, a re-ask
    # costs another round trip through the model, and the model is billed by the
    # minute. Bad transcription is expensive twice.
    #
    # Azure he-IL stays as the fallback. Both legs Hebrew, so no path ends with
    # an English transcriber listening to a Hebrew resident. It fires when the
    # provider *fails*, not when it transcribes Hebrew badly.
    #
    # ivrit-ai, the open-source Whisper fine-tuned on native Israeli speech, is
    # the long-term option and the only one that can run where the data does. It
    # needs `provider: custom-transcriber` and a websocket server, so it is a
    # project rather than a config line.
    #
    # 7 Aug: scribe_v2 -> scribe_v2_realtime. Same family, and the enum offers
    # three — scribe_v1, scribe_v2, scribe_v2_realtime. The first two are batch
    # models; only the third is built to stream, and this is a live phone call.
    # Published numbers put Scribe at 3.1% WER on FLEURS Hebrew and 5.5% on
    # Common Voice Hebrew, and the realtime variant leads multilingual realtime
    # accuracy at 93.5% on FLEURS. Nothing else tested close in Hebrew: Soniox
    # measured 7.5% WER, Speechmatics claims ~90% at sub-second latency.
    #
    # CHECKED BEFORE SWITCHING, because a realtime model can carry a narrower
    # language set than its batch sibling: scribe_v2_realtime covers 90+
    # languages and Hebrew is one of them.
    #
    # Vapi's own language enum is NOT what settled this. 11labs, cartesia,
    # soniox and vapi all publish the identical 185-entry list, and it contains
    # Volapük, Church Slavonic and Avestan — it is a copy of ISO 639-1, not a
    # support matrix. `he` appearing there is evidence of nothing. The curated
    # lists, where an entry means something, are azure 143, deepgram 89,
    # speechmatics 62 and openai 57.
    #
    # NOVA-3, NOT SCRIBE, SINCE 12 AUG — the client reversed this in the
    # dashboard, and on the axis the paragraphs above never weighed: latency.
    # Scribe measured 700ms in Vapi's panel against nova-3's 300ms, and the
    # 12 Aug diagnosis of "why is Hebrew slower than English" put the
    # transcriber as the largest single contributor. The WER argument stands
    # unrefuted (scribe still tops the Hebrew benchmarks) — it lost to 400ms
    # on every turn of every call. If the Hebrew mishears audibly worsen,
    # this block is the first thing to put back. confidenceThreshold and the
    # autoFallback flag are part of the dashboard change, captured verbatim.
    "transcriber": {
        "provider": "deepgram",
        "model": "nova-3",
        "language": "he",
        "confidenceThreshold": 0.4,
        "fallbackPlan": {
            "autoFallback": {"enabled": True},
            "transcribers": [{"provider": "azure", "language": "he-IL"}],
        },
    },
    # Vapi's own v2 voices, which the dashboard rates at 93 for humanness against
    # Azure HilaNeural's 2019-generation neural output — and 440ms against
    # Azure's slower. `language: he` is what makes an English-named voice speak
    # Hebrew, and it is not optional: without it the voice reads Hebrew text as
    # if it were English.
    #
    # LEAH, NOT ELLIOT, AND THIS IS NOT A PREFERENCE.
    # The dashboard edit set Elliot, which is Vapi's default and a MALE voice.
    # Every fixed line in this prompt is feminine first person — מדברת מיכל,
    # אני שולחת, אני מעבירה, אני עוזרת דיגיטלית — and Hebrew marks the speaker's
    # gender on the verb, so a male voice saying them is not a stylistic mismatch
    # but a grammatical error in every sentence the agent has. vapi_en.py already
    # carries the other half of this lesson: it renames Michal to Michael because
    # Elliot is male.
    #
    # The choice was between changing one word here and rewriting the identity,
    # the seven fixed lines and the whole feminine register. This is the one word.
    #
    # Leah was picked for being a Hebrew name and nothing else — the accent comes
    # from `language`, not the handle. Any of these swap in by replacing the one
    # string, and the choice should be made by ear, not by argument:
    # Clara, Savannah, Emma, Layla, Kylie, Lily, Hana, Neha, Paige, Naina, Tara,
    # Jess, Mia, Zoe.
    #
    # The guard sits on the voice, not the model, so nothing the model decides
    # can switch it off — but note that it therefore dies whenever the voice is
    # edited in the dashboard, which is exactly what happened on 5 Aug. See
    # scripts/voice_guard.py.
    # ELLIOT, NOT LEAH, SINCE 7 AUG — and this is the second time this one line
    # has been the whole argument, in the opposite direction.
    #
    # It was Leah because the intake prompt was feminine first person and a male
    # voice reading מדברת is a grammatical error in every sentence, not a
    # stylistic mismatch. The client has since asked for a male voice on both
    # agents, so the prompt was flipped to masculine — nine passages in
    # demo-inbound.md — and this line follows it rather than leading.
    #
    # The rule survives the reversal: THE VOICE AND THE PROMPT'S GENDER ARE ONE
    # CHANGE. Whoever edits this next must check demo-inbound.md in the same
    # commit, in whichever direction they are going.
    "voice": voice_with_guard(
        {"provider": "vapi", "voiceId": "Elliot", "version": "2", "language": "he"}),
    "model": {"provider": "openai", "model": "gpt-4.1-mini", "temperature": 0.3},
    "firstMessageMode": "assistant-speaks-first",
    "artifactPlan": {"recordingEnabled": True},
    # See the assistant docs for why each of these departs from the default.
    "startSpeakingPlan": {
        # 0.6 -> 0.4, matching the English twin. Then 0.4 -> 0.25 on 7 Aug when
        # a turn was measured end to end at 5,283ms: this is dead time added to
        # every single turn before any work starts, and at that total it is the
        # cheapest 150ms in the stack.
        "waitSeconds": 0.25,
        # Both shipped endpointing models are English-trained, so on Hebrew this
        # is unlikely to fire and the transcription timer below carries every
        # turn. Left on because it costs nothing when it does not fire.
        "smartEndpointingPlan": {"provider": "vapi"},
        "transcriptionEndpointingPlan": {
            "onPunctuationSeconds": 0.3,
            # 1.8 -> 1.0. Measured baseline before this change was a median wait
            # of 2,216ms and a worst turn of 6,870ms, against a <800ms target;
            # Vapi's own panel reported ~1,600ms because it excludes this stage
            # entirely.
            #
            # 1.0 -> 0.8 on 7 Aug, matching the English twin after all. The 1.0
            # was set for Azure he-IL, which punctuates Hebrew poorly, so the
            # timer carried every turn. The transcriber is 11labs scribe now and
            # Vapi reports endpointing at 301ms average, which means punctuation
            # IS arriving and this timer is not the path most turns take. The
            # reasoning for 1.0 outlived the transcriber it was written about.
            "onNoPunctuationSeconds": 0.8,
            # Digits are dictated with gaps. A card or a date needs longer than
            # ordinary speech, or the agent cuts in halfway through the number.
            "onNumberSeconds": 1.0,
        },
    },
    # numWords was 0, meaning any sound at all stopped her mid-sentence. On a
    # real call people say "mm-hmm" and "yeah" while you talk — that is
    # listening, not interrupting — and she restarted the sentence from the
    # beginning every time, three times in one opening. Two words is the
    # threshold between a backchannel and an actual interruption.
    # backoffSeconds was 1.5. After a barge-in she restarts the sentence from the
    # beginning, so the backoff is dead air *followed by* a repeated opening —
    # which is what produced "The the" / "The the bill" on the 4 Aug English call,
    # three times in one exchange.
    "stopSpeakingPlan": {"numWords": 2, "voiceSeconds": 0.3, "backoffSeconds": 1.0},
    # Both asked for on 12 Aug. The office ambience covers the tool-call
    # pauses that pure silence turns into "הלו?"; the denoising filters the
    # resident's side before the transcriber hears it, which matters more now
    # that the transcriber was chosen for speed rather than accuracy.
    "backgroundSound": "office",
    "backgroundDenoisingEnabled": True,
    # NOTHING SPOKE INTO SILENCE UNTIL 12 AUG, on either agent.
    #
    # The client's note was that when he stopped answering, the agent never
    # asked "הלו? אתה כאן?" — and he was exactly right, because there was no
    # mechanism for it. The agent finished its turn, heard nothing, and waited
    # for silenceTimeoutSeconds to close the line. Four of his ten calls ended
    # that way, one of them with a question still hanging.
    #
    # This is not a prompt rule and could never have been one: the model is not
    # invoked while nobody is talking, so it has no turn in which to notice. It
    # is a platform feature that was simply never switched on.
    #
    # THE LINES CARRY NO GENDER. אתה כאן? would be wrong for half of callers on
    # a line with no caller ID, and this is the worst possible turn to guess in
    # — the caller has already gone quiet once.
    "messagePlan": {
        "idleMessages": ["הלו? שומעים אותי?", "עדיין על הקו?"],
        # Eight seconds. Long enough that someone reading an apartment number
        # off a door is not interrupted, short enough that it lands before the
        # caller concludes the call has dropped.
        # 12, not 8, since 18 Aug. At 8 the prompt fired "Still with me?" while a
        # resident was thinking mid-answer, twice on real calls, and it reads as
        # impatience. It also fights the closing handshake: that ends on a beat
        # where the agent asks and then waits, and a prod at 8 seconds lands in
        # exactly the pause the handshake exists to create.
        "idleTimeoutSeconds": 12,
        # Twice, then stop. A third is nagging, and the silence timeout is the
        # thing that should end a genuinely dead line.
        "idleMessageMaxSpokenCount": 2,
        # The two are per stretch of silence, not per call — otherwise a caller
        # who pauses twice early has spent them, and the one that matters, later
        # on, never comes.
        "idleMessageResetCountOnUserSpeechEnabled": True,
        # The last thing they hear is now a goodbye rather than nothing. This is
        # the other half of the same complaint: a line that closes on a timeout
        # closes in silence, and the caller cannot tell a hangup from a fault.
        "silenceTimeoutMessage": "נראה שאין קליטה. תודה שהתקשרת להומיז, יום טוב, ולהתראות.",
    },
}

TARGETS = {
    "inbound": {
        # "(demo)" until 5 Aug, renamed the day it gained an English twin.
        # vapi_sync.py finds its target BY NAME, so this string and the live
        # assistant's name have to move together — leave them disagreeing and the
        # next --apply does not fail, it creates a second assistant and starts
        # editing that one instead.
        "name": "Homies — Inbound Intake (he)",
        "doc": "docs/assistant/demo-inbound.md",
        "extract": "fence",
        "extra": {
            # 300 -> 180 on 5 Aug, asked for directly.
            #
            # This field does not hurry anyone along: Vapi hangs up on the second
            # it expires, mid-word, and the model is never told it is coming.
            # Outbound that is survivable because the agent drives the call and an
            # overrun means it should have transferred. Inbound the CALLER drives,
            # so on its own a 180 would cut someone off in the middle of
            # describing a leak and write nothing — which is the one outcome the
            # prompt says is not allowed.
            #
            # So the cap ships with two companions, and it is not safe without
            # them. The prompt now carries a budget section that spends the time
            # in the order that survives being cut off — write the row as soon as
            # the description and the location are in hand, tidy up afterwards —
            # and `save_partial_request` is the net under it.
            #
            # The proper fix is the end-of-call webhook: Vapi reports
            # endedReason `max-duration-exceeded`, and a server seeing that can
            # write a partial from the transcript with no cooperation from the
            # model at all. That is the only version that cannot be talked out
            # of, and it needs a server URL that does not exist yet.
            "maxDurationSeconds": 180,
            # Untouched. Inbound silence is usually someone reading a meter number
            # off a wall, not a dead line.
            "silenceTimeoutSeconds": 30,
            # Added 5 Aug. Until now this assistant had NO WAY TO END A CALL —
            # no endCall function, no phrases, and no closing line in the prompt
            # to trigger one with. Every call it has ever handled ended
            # `customer-ended-call`, which looked fine because a caller who rang
            # in usually does hang up. What it hides is the shape underneath: the
            # agent reads out a reference number, stops talking, and the line
            # sits open for thirty seconds of silence before Vapi closes it. The
            # caller is left listening to nothing, wondering whether it worked.
            #
            # Same mechanism as the debt agent and for the same reason: the model
            # can decline to call a function, so the words are made the mechanism
            # rather than a request. With no endCall available, SAYING the closing
            # line is the only way to hang up.
            #
            # ולהתראות carries the vav, so a bare להתראות does not match it — the
            # one-word goodbye that ended a debt call mid-question on 5 Aug cannot
            # reach this. "and goodbye" does the same job for the English twin,
            # which shares this file's reasoning through vapi_en.py.
            #
            # 7 Aug: widened to יום טוב for the reason written out on the debt
            # target below. שיהיה לך יום טוב is ordinary Hebrew and does not
            # contain שיהיה יום טוב, so the narrow phrase left a call unable to
            # end. This one has the same latent fault and gets the same fix
            # before it costs an inbound caller a hung line.
            "endCallPhrases": ["יום טוב", "ולהתראות",
                               "have a good day", "and goodbye"],
            # Explicit rather than inherited. It is already Vapi's default, but
            # a dashboard visit can flip it without saying so, and if it comes on
            # the model gets a way to hang up WITHOUT speaking — which is the
            # failure this whole change exists to remove.
            "endCallFunctionEnabled": False,
        },
        # MALE since 7 Aug. This agent was מיכל and feminine throughout until the
        # client asked for a male voice on both agents.
        #
        # The prompt moved with it, because in Hebrew it has to: מדבר not מדברת,
        # מעביר not מעבירה, רושם not רושמת, מסמן not מסמנת, מבין not מבינה,
        # העוזר הדיגיטלי not העוזרת הדיגיטלית, and מיכאל not מיכל. Nine passages
        # in docs/assistant/demo-inbound.md, verified with a count-checked
        # replacement rather than by eye. Changing the voice without those would
        # leave a male voice reading feminine verbs in every sentence it has.
        "native_voice": "he-IL-AvriNeural",
        # "Eyal — Grounded Guide", the same voice chosen by ear for the debt
        # agent. One person across both front doors is a product decision, not an
        # oversight — a resident who hears the same voice for a leak and for a
        # payment is hearing one company.
        "cartesia_voice": "a976c076-3e31-4bf2-a178-8c3ce3d52b2a",
        "tools": INTAKE_TOOLS,
    },
    "debt": {
        "name": "Homies — Debt Follow-up (he)",
        # Extracted from the feature folder directly, so the prompt lives in one
        # place. docs/assistant/debt-followup.md holds the config reasoning only.
        "doc": "docs/features/10-debt-followup/prompt.md",
        "extract": "headings",
        "extra": {
            # Male, asked for on 5 Aug. Overrides BASE's Leah for this assistant
            # ONLY — the inbound assistant reads the same BASE and its prompt is
            # still feminine throughout, so setting this one string there instead
            # would have made that agent ungrammatical without touching a word of
            # its prompt. That is exactly the failure this override exists to
            # prevent, and it is the same one the dashboard caused on 5 Aug.
            #
            # Not separable from the prompt. Hebrew marks the speaker's gender on
            # the verb, so this string and the seven fixed lines in
            # docs/features/10-debt-followup/prompt.md are one change: מדבר not
            # מדברת, שולח not שולחת, מעביר not מעבירה, עוזר not עוזרת, and מיכאל
            # not מיכל. Reverting the voice without reverting those leaves a
            # female voice reading masculine verbs, which is the same error in
            # the other direction.
            # Unverified by ear as of the push. Vapi accepts the combination and
            # the dashboard set it earlier the same day, but nothing here proves
            # a male voice comes out: Vapi's own cost records report
            # `voiceId: Elliot` for EVERY call on this provider, including ones
            # that demonstrably ran on Leah, so billing is a provider label
            # rather than evidence of what was spoken. Only a call answers it.
            #
            # If it comes out female or with an English accent, Vapi is
            # substituting because its provider has no male Hebrew voice, and the
            # fallback is Azure, which does — `he-IL-AvriNeural`, the male
            # counterpart of the `he-IL-HilaNeural` this assistant used until
            # 5 Aug:
            #
            #     {"provider": "azure", "voiceId": "he-IL-AvriNeural"}
            #
            # It costs latency (Azure was the slower of the two) and it is a
            # purpose-built Hebrew voice rather than a multilingual one, which
            # for a Hebrew-only assistant is a fair trade.
            # Elliot, on yesterday's wording. That combination had never existed
            # before 5 Aug: yesterday's text was written feminine, and the only
            # masculine version was of today's rewritten lines. The wording that
            # was asked to be kept is kept — same sentences, same register, same
            # length — with seven gender markers moved so the verbs agree with
            # the voice saying them.
            #
            # The voice and those seven passages are one change and have been
            # three times now: Leah+feminine, Elliot+masculine, Leah+feminine,
            # and now Elliot+masculine again. Whichever way it goes, they move
            # together or every sentence the agent owns is ungrammatical. The
            # in-between state is not hypothetical — the dashboard produced it
            # at 12:12 by saving a stale editor over a fresh push.
            #
            # Still on the debt target rather than in BASE. BASE is shared with
            # the inbound assistant, whose prompt is feminine throughout, and one
            # string in the wrong file would break it silently.
            "voice": voice_with_guard(
                {"provider": "vapi", "voiceId": "Elliot", "version": "2", "language": "he"}),
            # Target is a two-minute call. Anything past four is a call that
            # should have been handed over.
            "maxDurationSeconds": 240,
            # Outbound: a silent line is an answering machine or a hang-up, not
            # someone thinking.
            "silenceTimeoutSeconds": 20,
            # Added 8 Aug. This was `{}` on the live assistant, which is not a
            # neutral default on an outbound agent — it is the agent conducting a
            # full debt conversation with an answering machine, reading a real
            # resident's balance into a recording anyone in the household can
            # play back, and hanging up having logged nothing.
            #
            # `voicemail` is already a value in log_call_outcome's enum, so the
            # outcome this produces has had somewhere to go since 4 Aug; nothing
            # was detecting it. Vapi's own model rather than the beep timeout —
            # Israeli carrier greetings run long, and a fixed timer either cuts
            # off a real person who paused or waits through the whole greeting.
            #
            # No voicemailMessage. Leaving a recorded message about somebody's
            # debt on a machine is a disclosure to whoever plays it, which is a
            # decision for Homies and their lawyer, not a config default. Detect,
            # log, hang up, let the campaign runner try again inside call hours.
            "voicemailDetection": {
                "provider": "vapi",
                "backoffPlan": {"maxRetries": 2, "startAtSeconds": 5, "frequencySeconds": 5},
            },
            # OFF since 5 Aug, reversing the 4 Aug decision, because the failure
            # it was protecting against has swapped ends.
            #
            # It went on when two calls spoke the whole closing and then sat
            # there — endCallPhrases had not matched, so nothing ended the call.
            # Giving the model `endCall` fixed that. What it also did was let the
            # model end a call WITHOUT saying anything it was told to say, and
            # that is now the failure actually happening:
            #
            #   wrong party  -> log_call_outcome{wrong_party} -> endCall
            #                   spoken, in full: "Goodbye."
            #   refusal      -> log_call_outcome{refused}     -> endCall
            #                   spoken, in full: "Goodbye."
            #
            # Both outcomes were logged correctly, so the model understood the
            # situation perfectly and simply skipped the words. The prompt
            # already says "Close with a full sentence, not a single word" two
            # lines above the closing line, and says "Say exactly this" above the
            # not-the-account-holder line. Both were read and ignored, which is
            # what makes this a structural problem rather than a wording one: a
            # rule the model can decline is not a rule.
            #
            # With this off the only way to end a call is to SAY the closing
            # line, because endCallPhrases matches on speech. Saying the line
            # becomes a precondition of hanging up rather than a request.
            #
            # The 4 Aug risk is real and is now bounded on both sides:
            # maxDurationSeconds caps a stuck call at four minutes, and
            # silenceTimeoutSeconds closes a dead line in twenty seconds. A call
            # that overstays costs a few cents. A resident told "Goodbye." and
            # cut off — or a wrong number never given the privacy line — costs
            # the relationship, and it is the one they will describe to the
            # building.
            #
            # WATCH THIS. If calls start failing to end, the phrase is not
            # matching and this goes back to True while that is fixed.
            "endCallFunctionEnabled": False,
            # A backstop, because endCallFunctionEnabled alone is not reliable.
            # On 4 Aug two consecutive English calls spoke the whole closing —
            # "thank you for your time, have a good day, and goodbye" — and then
            # simply sat there. One ended with the resident saying "Hello?" and
            # the bot answering "Yes, I'm here." The model chose not to call
            # endCall, and nothing made it. These phrases end the call on the
            # assistant's own speech, so the decision no longer rests with the
            # model.
            #
            # "a false positive would need the bot to say goodbye when it did not
            # mean it" — which is exactly what happened on 5 Aug. Pressed a third
            # time on whether Homies could take the payment, the model answered
            # the single word "Goodbye." and the call ended on it, mid-question,
            # with the resident still asking. The bare word was doing the work.
            #
            # The first fix for that was the whole closing tail — "have a good
            # day, and goodbye" — and it was too much: the model paraphrases the
            # sentence around it, so nothing matched and the calls stopped ending
            # at all. The bare word was the only broken entry; the conjunction is
            # what makes the rest safe.
            #
            # "and goodbye" cannot be reached by a model that simply says
            # "Goodbye." Hebrew makes the same distinction with one letter:
            # ולהתראות carries the vav, so a bare להתראות does not match it.
            # Short enough to survive rephrasing, specific enough not to fire
            # mid-conversation. endCallFunctionEnabled above is still the backstop.
            #
            # 7 Aug: שיהיה יום טוב was too narrow, and the prompt itself was what
            # broke it. ENDING THE CALL offers שיהיה לך יום טוב as a closing and
            # says in as many words that the לך is optional and worth varying —
            # so the model varied it, the phrase stopped matching, and the call
            # would not hang up. The resident said אוקיי, the model had nothing
            # left but the closing, and said it again. Three times. The call ended
            # only when a later closing happened to drop the לך.
            #
            # So this matches on יום טוב, which every form of the goodbye
            # contains — with the לך, without it, feminine or masculine. It cannot
            # fire mid-conversation: nothing in a call about an unpaid ועד בית
            # reaches for those two words except a farewell. A phrase that only
            # matches the one phrasing nobody chose is not a backstop.
            "endCallPhrases": ["יום טוב", "ולהתראות",
                               "have a good day", "and goodbye"],
            # Overrides BASE. Was gpt-5.5, set in the dashboard on 3 Aug for more
            # natural Hebrew. Moved to gpt-5.4 on 5 Aug on cost.
            #
            # Measured from Vapi's own billing across 61 calls, not from a price
            # list: gpt-5.5 charged $2.44 per million prompt tokens on this
            # workload against gpt-5.4's $1.32 — 1.85x for the same job. The LLM
            # is the largest reducible line on the bill, and the target is $0.10
            # a minute against $0.127 today.
            #
            # This is a real trade, not a free win: 5.5 was chosen for Hebrew
            # quality and the Hebrew sample behind that decision was seven calls.
            # If the Hebrew audibly worsens, this line is the first thing to put
            # back — and the cost of doing so is about two cents a minute, which
            # is worth paying for a call that sounds human.
            #
            # gpt-5.4-mini is cheaper again and stays rejected. It spoke its own
            # tool-call syntax aloud on 4 Aug; the output filter added 5 Aug would
            # now catch that, but the same call logged ZERO tool calls — the
            # ticket was never opened. The filter fixes what the resident hears,
            # not a tool that did not fire, and that is the half that mattered.
            #
            # No temperature: the dashboard change dropped it and the gpt-5.x
            # models may not accept one. The 0.3 on the inbound assistant was
            # deliberate, so it stays there.
            #
            # 5.4 -> 5.2, set in the dashboard on 12 Aug in the same edit that
            # swapped the transcriber; captured here so a sync does not revert
            # it. Note the English twin still runs gpt-5.4 — vapi_en.py copies
            # the prompt, not this block.
            "model": {"provider": "openai", "model": "gpt-5.2"},
        },
        # "Echo Stone" — this agent takes a cloned voice when one exists. See
        # cloned_voice() below. The debt agent and not the inbound one because
        # the voice being cloned is male and this prompt is already masculine
        # throughout: מיכאל, מדבר, שולח, מעביר. Pointing a male clone at the
        # inbound agent instead would mean rewriting the same seven passages that
        # have already been flipped three times. Nothing in the prompt changes
        # here — only the voice block.
        "cloneable": True,
        # Male, matching מיכאל and the masculine prompt. See native_voice().
        "native_voice": "he-IL-AvriNeural",
        # "Eyal — Grounded Guide", masculine. Chosen by ear on 7 Aug from all
        # eleven of Cartesia's masculine Hebrew voices, auditioned on one
        # identical sentence — see HEBREW_MEN.
        #
        # Noam held this slot for a few hours and was rejected as robotic. It
        # was also the only Hebrew voice I had found at that point, because the
        # first voice-list fetch read one page of nine and I reported 4 Hebrew
        # voices when there are 29. Paginate before concluding a catalogue is
        # small.
        #
        # Eyal at 9.48s is near the fast end of the eleven, which is worth
        # noting against the theory that slower simply meant more expressive:
        # the two slowest, Yonatan at 11.55s and Ido at 11.15s, were not chosen.
        # Duration was a useful sort order and a bad judge.
        "cartesia_voice": "a976c076-3e31-4bf2-a178-8c3ce3d52b2a",
        "tools": DEBT_TOOLS,
    },
}


def load_env():
    if not os.path.exists(ENV):
        sys.exit(".env not found. Copy .env.example to .env and fill in VAPI_PRIVATE_KEY.")
    for line in open(ENV, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    key = os.environ.get("VAPI_PRIVATE_KEY")
    if not key:
        sys.exit("VAPI_PRIVATE_KEY is empty in .env")
    return key


def extract_fence(text):
    """demo-inbound.md: the prompt is a four-backtick block, because it contains
    indented Hebrew examples that a three-backtick fence would end early."""
    fm = re.search(r"## First message\s*\n+```+\s*\n(.*?)\n```+", text, re.S)
    sp = re.search(r"## System prompt\s*\n+````\s*\n(.*?)\n````", text, re.S)
    if not (fm and sp):
        sys.exit("Could not find the first message or system prompt block")
    return fm.group(1).strip(), sp.group(1).strip()


def extract_headings(text):
    """prompt.md: the system prompt is everything between its '## System prompt'
    heading and the next level-2 heading. The first message is the opening line,
    which is the first blockquote under '### Opening'."""
    sp = re.search(r"\n## System prompt\s*\n(.*?)(?=\n## )", text, re.S)
    if not sp:
        sys.exit("Could not find the '## System prompt' section")
    body = sp.group(1).strip().strip("-").strip()
    fm = re.search(r"### Opening\s*\n+> (.+)", body)
    if not fm:
        sys.exit("Could not find the opening line under '### Opening'")
    return fm.group(1).strip(), body


def tool_server():
    """Where the tool webhooks live: (url, secret, mode, label), or None.

    Supabase is preferred and Apps Script is the fallback, in that order, because
    the Apps Script implementation is a stopgap with weaker guarantees — no
    constraints, a secret in the query string, and a cold start that costs the
    call one to three seconds of silence. The moment Supabase is configured it
    wins automatically and the sheet stops being used.

    None rather than a guess when neither is set. An assistant carrying tools
    that point at a URL which 404s is worse than one carrying none: the agent
    believes it opened a ticket, says so out loud, and nothing is written.
    """
    # n8n first: it is where the tool layer is being built, and where the
    # integrations that come next (WhatsApp, Chatwoot, Monday) already have
    # nodes. Supabase and Apps Script stay reachable by clearing N8N_BASE_URL.
    url = os.environ.get("N8N_BASE_URL", "").rstrip("/")
    if url:
        secret = os.environ.get("N8N_WEBHOOK_SECRET", "")
        return url + "/webhook/homies-debt-tools", secret, "header", "n8n"

    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    secret = os.environ.get("TOOL_SECRET", "")
    if url and secret:
        return url + "/functions/v1/debt-tools", secret, "header", "supabase"

    url = os.environ.get("WEB_APP_URL", "").strip()
    secret = os.environ.get("APPS_SCRIPT_SECRET", "").strip()
    if url and secret:
        return url, secret, "query", "apps script (stopgap)"

    return None


def report_server():
    """Where the end-of-call report goes: (url, secret), or None.

    Supabase only, and NOT whatever tool_server() picked. The two are the same
    URL today and they are not the same decision: the tool endpoint is chosen by
    where the integrations live, and the report endpoint is chosen by where the
    `interactions` table is. n8n serves the tools and has no handler for a
    server message at all — pointing the report there would give Vapi a 200 and
    write nothing, which is the failure that leaves no trace anywhere.

    None rather than a guess. An assistant with a server URL that 404s makes Vapi
    retry the report six times and then drop it, and the only place that shows up
    is a Vapi log nobody reads.
    """
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    secret = os.environ.get("TOOL_SECRET", "")
    if url and secret:
        return url + "/functions/v1/debt-tools", secret
    return None


def native_voice(target, fallback):
    """Azure's purpose-built Hebrew voices, when VOICE_PROFILE=native.

    THE AMERICAN ACCENT IS NOT A SETTING, IT IS THE VOICE
    `vapi/Elliot` with `language: he` is an ENGLISH voice model being told to
    read Hebrew text. The language flag changes which letters it pronounces, not
    which language it learned to speak, so an English accent is not a
    misconfiguration to tune out — it is what that voice is. No amount of
    prompt work or speed adjustment reaches it.

    `azure/he-IL-AvriNeural` is a voice model trained on Hebrew. Note that it
    takes NO `language` property at all, which is the tell: the locale is in the
    name because the voice IS Hebrew rather than a multilingual voice pointed at
    it. Avri is male and Hila is female, matching the two prompts as written.

    THE TRADE, AND IT IS REAL
    Vapi's dashboard rates its own v2 voices at 93 for humanness against Azure's
    2019-generation neural output, and at ~440ms against Azure's slower. So this
    swaps an American accent for an older-sounding voice, and which of the two is
    worse is a question only ears answer. Hence the toggle rather than a
    decision: run one call each way and keep the better.

        VOICE_PROFILE=native  python scripts/vapi_sync.py debt --apply
        VOICE_PROFILE=vapi    python scripts/vapi_sync.py debt --apply

    An empty VOICE_PROFILE no longer means Elliot — since 7 Aug it means
    Cartesia, because Hebrew's default voice stopped being an environment
    setting. `vapi` is the way back to Elliot.

    Both were tested against the live API before this was written; Vapi accepts
    either voiceId with a 200.

    The third option beats both and is parked: a cloned voice speaking Hebrew has
    neither problem, because it is a real Hebrew speaker's voice rather than a
    model imitating one. This toggle is what to use until that exists.
    """
    vid = target.get("native_voice")
    if not vid or os.environ.get("VOICE_PROFILE", "").strip().lower() != "native":
        return None
    # No `language` key: Azure rejects one, and the voice name carries the locale.
    voice = voice_with_guard({"provider": "azure", "voiceId": vid})
    voice["fallbackPlan"] = {"voices": [dict(fallback, provider="vapi")]}
    return voice


def cloned_voice(fallback):
    """The Echo Stone voice — a clone of a real person — or None if there is none.

    Returns None whenever CARTESIA_VOICE_ID is unset, which is the state this
    project is in until a Cartesia account exists. That is deliberate: with the
    variable absent this function changes nothing at all, so the file can carry
    the wiring long before the voice exists and `--apply` stays safe to run.

    WHY CARTESIA AND NOT ELEVENLABS, WHICH IS WHAT EVERYONE REACHES FOR
    A cloned voice cannot run on `provider: vapi` at all. VapiVoice.voiceId is a
    closed enum of thirty names in Vapi's own OpenAPI spec — Elliot and Leah are
    two of them — with no slot for a custom id. CloneVoiceDTO exists in that spec
    and is referenced by no path and no other schema. So the clone lives in a
    provider account and Vapi points at it, whichever provider that is.

    Of the ones that accept a free-text voiceId, Cartesia is the only strong fit
    for Hebrew: `he` is declared in its 42-language enum. ElevenLabs declares
    `language` as free text, so nothing in the spec says whether Hebrew works —
    it would ride on eleven_v3 — and the spec carries the error
    `eleven-labs-blocked-using-instant-voice-clone-and-requested-upgrade`, so its
    cloning is plan-gated too. Paying to find out is the wrong order. PlayHT,
    LMNT and Rime also declare Hebrew and are the backups if Cartesia disappoints.

    Cartesia also keeps `chunkPlan`, which is where the output guard lives. A
    provider without it would silently drop the filter that stops the model
    reading its own tool calls aloud — see scripts/voice_guard.py.

    THE FALLBACK IS NOT OPTIONAL
    The Hebrew transcriber already falls back Hebrew-to-Hebrew so no path ends
    with an English engine listening to a Hebrew resident. The voice needs the
    same care for the same reason. A cloned voice is one account and one
    provider away from failing, and the failure would land mid-call; falling back
    to Elliot means a call continues in a male Hebrew voice reading masculine
    verbs, which is wrong-sounding but grammatical. FallbackVapiVoice carries
    chunkPlan, so the guard survives the fallback.
    """
    # ElevenLabs first, because if both are set the one someone just configured
    # is the one they mean, and 11labs is the account people already have.
    #
    # HEBREW EXISTS ON ONE ELEVENLABS MODEL AND ONLY ONE.
    # eleven_multilingual_v2 — the default, and what you get by saying nothing —
    # covers 29 languages and Hebrew is not among them. eleven_v3 covers 74 and
    # does include it. Getting this wrong is not a subtle degradation: it is an
    # engine that never learned the language reading Hebrew letters, which is the
    # same failure as Vapi's Elliot in a different accent.
    #
    # The cost of being right is latency. v3 is ElevenLabs' expressive model, not
    # their realtime one — Flash and Turbo are the low-latency pair, and neither
    # does Hebrew. So on this stack Hebrew and speed are in direct tension, and
    # the target here is under 800ms voice-to-voice. MEASURE IT with
    # scripts/vapi_latency.py before trusting it on a live call; if v3 is too
    # slow, Cartesia is the way back out rather than a different 11labs model.
    #
    # `language` is deliberately not set. Vapi's schema says that field is
    # "enforced for the model. Currently only Turbo v2.5" — so on v3 it does
    # nothing, and setting it would only look like it was doing something.
    vid = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
    if vid:
        voice = voice_with_guard({
            "provider": "11labs",
            "voiceId": vid,
            "model": os.environ.get("ELEVENLABS_MODEL", "eleven_v3").strip(),
        })
        voice["fallbackPlan"] = {"voices": [dict(fallback, provider="vapi")]}
        return voice

    vid = os.environ.get("CARTESIA_VOICE_ID", "").strip()
    if not vid:
        return None
    return cartesia_voice(vid, fallback)


# Cartesia's eleven masculine `language: he` voices, by name so a switch is one
# word instead of a uuid. Auditioned 7 Aug on one identical sentence; the seconds
# are that render, and they matter — same words, so a voice taking 11.55s is
# spending 2.6s more on hesitation and phrasing than Noam does at 8.91s. That is
# the difference between "expressive" and "robotic" as far as this project can
# measure it, and it is also billed by the minute.
#
# The full list is 29 voices, 18 of them feminine; see cartesia_tts.py --list.
HEBREW_MEN = {
    "noam":    ("3e32f3c5-9ac0-4192-9994-87fdb277120f", 8.91),   # Broadcaster — fastest, flattest
    "eyal":    ("a976c076-3e31-4bf2-a178-8c3ce3d52b2a", 9.48),   # Grounded Guide
    "avi":     ("858c98dc-db9e-4d1a-9435-557cdf77685c", 9.80),   # Calm Consultant
    "eitan":   ("daa4d6bb-da62-4e16-8065-76cd87942475", 9.87),   # Modern Communicator
    "gil":     ("84b969ad-19c7-428d-b742-48d387f7f138", 9.95),   # Friendly Host
    "asaf":    ("52271edb-c161-4c76-9e33-c5c1d39de6e3", 10.84),  # Steady Advisor
    "itai":    ("db3dc8a6-d8f8-4ca5-add9-559c849a6fa0", 10.92),  # Measured Advisor
    "oren":    ("431b7e77-b46d-4eda-8362-db430ac0913c", 11.00),  # Steady Advisor
    "ronen":   ("921f4026-af53-4761-ac56-1c32e44856e8", 11.00),  # Calm Consultant
    "ido":     ("33124162-0d74-48af-ab1c-c1c01bac0247", 11.15),  # Calm Communicator
    "yonatan": ("95d91579-a3f1-4bb3-b5e1-9a97ef401628", 11.55),  # Measured Professional — slowest
}


def cartesia_voice(vid, fallback):
    """A Cartesia voice object with the guard and an Elliot fallback attached.

    Split out of cloned_voice() on 7 Aug because the clone stopped being the only
    reason to reach for Cartesia. `POST /voices/clone` returns
    402 `plan_upgrade_required` — Instant Voice Cloning is Pro-tier, and the
    earlier note in this file that it was "fast and free" was wrong: that phrase
    is about training being free once you are on a plan that has the feature.

    What the free tier *does* carry is four voices with `language: he` — real
    Hebrew voices on a current model, which is the combination nothing else had.
    Azure's he-IL voices are native and flat; vapi/Elliot is expressive with an
    American accent. Measured on identical text, Cartesia gave `אה` +3.84s of
    hesitation against Azure's +1.46s, which is the difference being chased.

    THE PRICE IS WALL-CLOCK, AND IT IS BILLED.
    Cartesia ran 31-66% longer than Azure on the same sentences. Calls are billed
    per minute, so a 35% slower voice moves the ~5,000 min/month estimate toward
    6,750. If that shows up on the bill, `generationConfig.speed` accepts
    0.6-1.5 on sonic-3 — tune there before changing provider.
    """
    voice = voice_with_guard({
        "provider": "cartesia",
        "voiceId": vid,
        # WARMTH, ADDED 7 AUG. Cartesia is the only provider Vapi supports that
        # exposes emotion at all — Azure has no equivalent at any price.
        #
        # `positivity:low` and not `high`. This agent calls people about money
        # they owe, and an audibly cheerful collector is worse than a flat one:
        # it reads as insincere at exactly the moment sincerity is being judged.
        # Low is the difference between "polite" and "clipped", which is the
        # complaint this is answering, and it stops there.
        #
        # Overridable because the right level is a judgement by ear, and one
        # person's warm is another's saccharine:
        #     CARTESIA_EMOTION=positivity:high python scripts/vapi_sync.py debt
        # A LIST, THOUGH THE SPEC SAYS STRING. CartesiaExperimentalControls
        # declares `emotion` as `type: string` with an enum, and sending a string
        # gets 400 "Only one emotion intensity level per emotion type is
        # allowed" — the server reads it as a sequence of characters. The spec's
        # own `example` is `["happiness:high"]`, which is the tell. Trust the
        # example over the type here.
        "experimentalControls": {
            "emotion": [os.environ.get("CARTESIA_EMOTION", "positivity:low").strip()],
        },
        # sonic-3 by default. Overridable because the model list moves faster
        # than this file does, and because the right one is decided by ear.
        "model": os.environ.get("CARTESIA_MODEL", "sonic-3").strip(),
        # The same thing `language: he` does on the Vapi voices: without it a
        # multilingual voice reads Hebrew text as though it were English.
        "language": "he",
    })
    voice["fallbackPlan"] = {"voices": [dict(fallback, provider="vapi")]}
    return voice


def build(target, first_message, system_prompt):
    body = json.loads(json.dumps(BASE))
    body.update(target["extra"])
    body["name"] = target["name"]
    body["firstMessage"] = first_message
    body["model"]["messages"] = [{"role": "system", "content": system_prompt}]

    # Precedence, most specific first:
    #   1. a clone of a real person          CARTESIA_VOICE_ID / ELEVENLABS_VOICE_ID
    #   2. Azure's native Hebrew voice       VOICE_PROFILE=native
    #   3. the stock Vapi voice              VOICE_PROFILE=vapi
    #   4. Cartesia's native Hebrew voice    the default
    #
    # ELLIOT FOR ENGLISH, EYAL FOR HEBREW — AND THAT IS A PROPERTY OF THE AGENT,
    # NOT OF SOMEBODY'S SHELL. Cartesia used to sit behind VOICE_PROFILE=cartesia,
    # which meant the voice a Hebrew agent ended up with depended on which
    # environment variable happened to be set the last time anyone ran this. That
    # is not a hypothetical failure: the inbound agent was pushed once with the
    # profile set and the debt agent never was, so the two front doors of one
    # company spoke in two different voices for two days and no file said so.
    # Anything that can silently differ between two runs of the same command does
    # not belong in an environment variable.
    #
    # The English twins set their own voice in vapi_en.py and never reach this
    # code, so they keep Elliot without needing to know about any of it.
    #
    # WHY NOT ELLIOT FOR HEBREW TOO, WHICH IS SIMPLER: `vapi/Elliot` with
    # `language: he` is an English voice model being told to read Hebrew. The
    # American accent is not a setting that can be tuned out, it is what that
    # voice is. Eyal is a Hebrew voice on a Hebrew model. The price is wall-clock
    # — Cartesia ran 31-66% longer on identical sentences, and calls bill by the
    # minute — see cartesia_voice() for where to tune that before changing
    # provider.
    #
    # VOICE_PROFILE=vapi puts Elliot back on Hebrew for an A/B, without editing
    # anything. VOICE_PROFILE=native reaches Azure, which is the other native
    # Hebrew option: accurate and flat where Cartesia is expressive and slower.
    # Which of those is right is a judgement about the call rather than a fact
    # about the language, so both stay reachable.
    profile = os.environ.get("VOICE_PROFILE", "").strip().lower()

    if target.get("cloneable"):
        cloned = cloned_voice(body["voice"])
        if cloned:
            body["voice"] = cloned
    if body["voice"]["provider"] == "vapi" and profile != "vapi":
        vid = target.get("cartesia_voice")
        # HEBREW_VOICE=asaf picks by name, so auditioning is one word rather than
        # a uuid pasted from a browser. Masculine list only — putting a male
        # voice on the feminine intake agent is a grammatical error, not a
        # preference, so the override is refused rather than silently applied.
        pick = os.environ.get("HEBREW_VOICE", "").strip().lower()
        if pick:
            if pick not in HEBREW_MEN:
                sys.exit("HEBREW_VOICE=%s is not one of: %s"
                         % (pick, ", ".join(sorted(HEBREW_MEN))))
            if target.get("native_voice", "").endswith("AvriNeural"):
                vid = HEBREW_MEN[pick][0]
            else:
                sys.exit("HEBREW_VOICE only applies to agents with a masculine "
                         "prompt. Both are masculine as of 7 Aug; if this fires, "
                         "a target's native_voice was changed without its prompt.")
        if vid and profile != "native":
            body["voice"] = cartesia_voice(vid, body["voice"])
    if body["voice"]["provider"] == "vapi":
        native = native_voice(target, body["voice"])
        if native:
            body["voice"] = native

    server = tool_server()
    if target.get("tools") and server:
        url, secret, mode, _ = server
        body["model"]["tools"] = with_server(target["tools"], url, secret, mode)

    report = report_server()
    if report:
        url, secret = report
        # `server` on the assistant, not the deprecated top-level serverUrl —
        # that form takes no headers, and this endpoint authenticates on one.
        body["server"] = {"url": url, "headers": {"x-homies-secret": secret}}
        # Exactly one message, deliberately. Vapi offers eleven and the tempting
        # ones — conversation-update, speech-update — fire several times a
        # SECOND, each a round trip to Tokyo from a function that writes to the
        # same row. The end-of-call report carries the transcript, the recording,
        # the duration, the ended reason and the latency in one POST after the
        # call is over, where nothing it does can cost the caller a millisecond.
        body["serverMessages"] = ["end-of-call-report"]
    return body


def call(key, method, path, payload=None):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            # Vapi sits behind Cloudflare, which 403s (error 1010) on urllib's
            # default user-agent. Any ordinary UA string gets through.
            "User-Agent": "homies-vapi-sync/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s on %s %s\n%s" % (e.code, method, path, e.read().decode("utf-8")))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply_it = "--apply" in sys.argv
    if len(args) != 1 or args[0] not in TARGETS:
        sys.exit("Usage: vapi_sync.py {%s} [--apply]" % "|".join(TARGETS))

    target = TARGETS[args[0]]
    key = load_env()
    text = open(os.path.join(ROOT, target["doc"]), encoding="utf-8").read()
    first_message, system_prompt = (
        extract_fence(text) if target["extract"] == "fence" else extract_headings(text)
    )
    payload = build(target, first_message, system_prompt)

    existing = [a for a in call(key, "GET", "/assistant?limit=100") if a.get("name") == target["name"]]

    print("source        : %s" % target["doc"])
    print("assistant     : %s" % target["name"])
    print("first message : %s" % first_message)
    print("system prompt : %d chars" % len(system_prompt))
    sp, st = payload["startSpeakingPlan"], payload["stopSpeakingPlan"]
    print("transcriber   : %s %s" % (payload["transcriber"]["provider"],
                                     payload["transcriber"].get("model", "")
                                     or payload["transcriber"].get("language", "")))
    print("model         : %s" % payload["model"]["model"])
    v = payload["voice"]
    fb = (v.get("fallbackPlan") or {}).get("voices") or []
    print("voice         : %s %s%s%s" % (
        v["provider"], v["voiceId"],
        # Say which it is. A stock Cartesia voice and a clone of a real person
        # are the same shape in this payload, and printing "cloned" for both is
        # how someone later believes a clone exists when it does not.
        (" (cloned)" if os.environ.get("CARTESIA_VOICE_ID", "").strip()
         else " (stock he voice)") if v["provider"] == "cartesia" else "",
        "  fallback -> %s %s" % (fb[0]["provider"], fb[0]["voiceId"]) if fb else ""))
    print("endpointing   : wait %ss, noPunct %ss, number %ss, backoff %ss" % (
        sp["waitSeconds"],
        sp["transcriptionEndpointingPlan"]["onNoPunctuationSeconds"],
        sp["transcriptionEndpointingPlan"]["onNumberSeconds"],
        st["backoffSeconds"]))

    attached = payload.get("model", {}).get("tools", [])
    if attached:
        host = (tool_server() or (None, None, None, "?"))[3]
        # The secret is in the URL on the Apps Script path; do not print it.
        shown = attached[0]["server"]["url"].split("?")[0]
        print("tools         : %d -> %s [%s]" % (len(attached), shown, host))
        for t in attached:
            print("                %s" % t["function"]["name"])
    elif target.get("tools"):
        print("tools         : NONE ATTACHED — set SUPABASE_URL + TOOL_SECRET,")
        print("                or WEB_APP_URL + APPS_SCRIPT_SECRET, in .env")
        print("                the agent will say it opened a ticket and write nothing")

    if payload.get("server"):
        print("report        : %s %s" % (payload["server"]["url"],
                                         payload.get("serverMessages", [])))
    else:
        print("report        : NONE — every transcript, latency figure and ended")
        print("                reason is discarded when the call ends")

    vm = payload.get("voicemailDetection")
    print("voicemail     : %s" % (vm.get("provider") if vm else "off — the agent will "
                                  "hold the whole call with an answering machine"))

    print("target        : %s" % (("update " + existing[0]["id"]) if existing else "create new"))

    if not apply_it:
        print("\nDry run. Re-run with --apply to write.")
        return

    if existing:
        result = call(key, "PATCH", "/assistant/" + existing[0]["id"], payload)
    else:
        result = call(key, "POST", "/assistant", payload)
    print("\nOK — assistant %s" % result["id"])
    print("https://dashboard.vapi.ai/assistants/%s" % result["id"])


if __name__ == "__main__":
    main()
