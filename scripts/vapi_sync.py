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
# it — and 11labs, speechmatics and soniox accept `he` too. Azure stays the
# default because it is the one that has actually been heard transcribing
# Hebrew; the alternatives are an untested opportunity, not a recommendation.
# Swap by replacing this line, and measure with scripts/vapi_latency.py:
#     {"provider": "deepgram", "model": "nova-3", "language": "he"}
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
    "transcriber": {
        "provider": "11labs",
        "model": "scribe_v2",
        "language": "he",
        "fallbackPlan": {
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
    "voice": voice_with_guard(
        {"provider": "vapi", "voiceId": "Leah", "version": "2", "language": "he"},
        chunk=SPEECH),
    "model": {"provider": "openai", "model": "gpt-4.1-mini", "temperature": 0.3},
    "firstMessageMode": "assistant-speaks-first",
    "artifactPlan": {"recordingEnabled": True},
    # See the assistant docs for why each of these departs from the default.
    "startSpeakingPlan": {
        # 0.6 -> 0.4, matching the English twin.
        "waitSeconds": 0.4,
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
            # 1.0 and not the English twin's 0.8, deliberately. Azure he-IL
            # punctuates Hebrew far less reliably than Deepgram Flux punctuates
            # English, so on Hebrew almost every turn takes this path and the
            # timer is the only signal there is. Cutting a caller off mid-sentence
            # is a worse failure than 200ms of extra wait, and this is a call
            # about money.
            "onNoPunctuationSeconds": 1.0,
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
        },
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
                {"provider": "vapi", "voiceId": "Elliot", "version": "2", "language": "he"},
                chunk=SPEECH),
            # Target is a two-minute call. Anything past four is a call that
            # should have been handed over.
            "maxDurationSeconds": 240,
            # Outbound: a silent line is an answering machine or a hang-up, not
            # someone thinking.
            "silenceTimeoutSeconds": 20,
            "endCallFunctionEnabled": True,
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
            "endCallPhrases": ["and goodbye", "ולהתראות"],
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
            "model": {"provider": "openai", "model": "gpt-5.4"},
        },
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


def build(target, first_message, system_prompt):
    body = json.loads(json.dumps(BASE))
    body.update(target["extra"])
    body["name"] = target["name"]
    body["firstMessage"] = first_message
    body["model"]["messages"] = [{"role": "system", "content": system_prompt}]

    server = tool_server()
    if target.get("tools") and server:
        url, secret, mode, _ = server
        body["model"]["tools"] = with_server(target["tools"], url, secret, mode)
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
