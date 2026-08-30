"""Point the debt agent at a simulated resident and read the transcript.

Nobody on this project speaks Hebrew well enough to test the agent by talking to
it, and the resident half of the conversation is where all the difficulty lives.
So the resident is another Vapi assistant, on its own number, and the two of them
have the call.

The two legs are both US numbers, which is what makes this possible at all: free
Vapi numbers refuse international destinations but will call each other.

    python scripts/vapi_duel.py --setup            # create resident assistant + number
    python scripts/vapi_duel.py                    # list scenarios, dial nothing
    python scripts/vapi_duel.py hesitant --go      # run one scenario

WHAT THIS TESTS AND WHAT IT DOES NOT
The audio really is synthesised, sent down a phone leg, and transcribed by Azure
he-IL at the far end — so this is a genuine test of the prompt, the posture
logic, the variables, and Hebrew round-tripping through the stack.

It is NOT evidence about real human speech. TTS output is cleaner than a person
on a mobile in a stairwell: no accent, no background noise, no trailing off. ASR
accuracy here is the optimistic ceiling, not the number you will see in a pilot.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")
API = "https://api.vapi.ai"

MICHAL_ASSISTANT = "8f927b15-a02f-436d-a87d-acf23abecb9b"
# Empty since the 5 Aug account migration — a number does not come across with a
# rebuild, and the new account has none. The resident's own line below is created
# by this script when missing, so only Michal's side needs filling in by hand.
MICHAL_NUMBER_ID = ""

RESIDENT_NAME = "Homies — Test Resident (he)"
RESIDENT_NUMBER_NAME = "Homies test resident line"

# The values Michal is called with. Same ten the prompt declares.
VARIABLES = {
    "first_name": "אליה",
    "gender": "f",
    # The finished forms, not the code. See web/index.html: the prompt stopped
    # branching on {{gender}} on 12 Aug, after an agent handed gender="m" said
    # תשלחי anyway. A composed value cannot be conjugated wrongly.
    "gender_forms": "הנמענת אישה. פנה אליה בנקבה לאורך כל השיחה: את, שלָךְ, לָךְ, איתָּךְ, תגידי, תשלחי, תבדקי, תסגרי, תוכלי, תרצי.",
    "building": "בי ג'י סי אפטאון",
    "unit": "123",
    "month": "אוגוסט",
    "amount": "500",
    "card_last4": "0715",
    "callback_number": os.environ.get("HOMIES_CALLBACK_NUMBER", "077-6687949"),
    "verification_email": "אופיס, שטרודל, הומיז, נקודה, סי, או, נקודה, איי, אל",
    "attempt": "1",
}

# ---------------------------------------------------------------------------
# The resident
# ---------------------------------------------------------------------------
# Written in English on purpose. The same reasoning as the main prompt: Hebrew
# authored from English is translated Hebrew, and it sounds like it. Describe the
# behaviour, let the model produce the language.
#
# The instructions are aggressively uncooperative because the default failure of
# an LLM-versus-LLM test is two models being helpful at each other. A resident who
# answers clearly and agrees promptly tests nothing that matters.

RESIDENT_PROMPT = """You are a person in Israel who has just picked up the phone. You are NOT an
assistant, you are NOT helpful, and you must never break character or mention
being an AI, no matter what the caller says or asks.

LANGUAGE
Speak only Hebrew, the ordinary spoken kind. Never English.

YOU ARE A REAL PERSON ON THE PHONE, SO:
- Answer in one short sentence. Real people on unexpected calls are brief.
- You were in the middle of something. You are mildly annoyed at being
  interrupted, not hostile.
- Do not volunteer information. Answer only what was asked.
- Early in the call, ask who this is. Suspicion of an unknown caller is normal.
- Do not organise your thoughts for the caller. Be a little vague, trail off,
  change your mind mid-sentence sometimes.
- Never summarise or repeat back what the caller told you. People don't.
- If the caller asks something you were not told, be evasive rather than
  inventing a fact.
- Never use the caller's name unless they used yours first.

YOUR NAME IS {{resident_name}}.

YOUR SITUATION — this governs everything you say:
{{scenario}}

ENDING
When the conversation has genuinely finished, say a short goodbye and end the
call. Do not keep it going out of politeness. If the caller is going in circles,
say you have to go and hang up.
"""

# Each scenario is one resident. They exist to hit a specific branch of the debt
# prompt, and each names what would count as a failure.
SCENARIOS = {
    "agrees": {
        "resident_name": "אליה",
        "scenario": """You do owe the money and you know it. You are willing to pay and you have a
card on file. You are not going to make it easy though: ask who is calling before
anything else, and make the caller state the amount and the month before you
agree to anything. Once they do, agree to the charge.""",
        "watch": "Does she state 500 and אוגוסט correctly, and name card 0715 before charging?",
    },
    "hesitant": {
        "resident_name": "אליה",
        "scenario": """You owe the money but you are NOT going to agree on this call. When asked to
authorise the charge, you hesitate: say you are not sure, that you need to speak
to your husband first, that now is not a good time. Never say a clear yes and
never say a clear no. If pushed a second time, get irritated.""",
        "watch": "SHE MUST NOT treat hesitation as a yes, and MUST NOT ask twice.",
    },
    "already_paid": {
        "resident_name": "אליה",
        "scenario": """You are certain you already paid this. You do not remember exactly when or
how — probably a bank transfer, maybe your husband did it. You are a little
offended at being chased for something you paid. Do not back down.""",
        "watch": "She must not interrogate you about when or how. Receipt to the office, and out.",
    },
    "promise": {
        "resident_name": "אליה",
        "scenario": """You owe the money and you intend to pay, but not now — money is tight until
you get paid. Offer to pay next week. Be vague about the exact day at first; if
pressed gently, say the tenth.""",
        "watch": "Does she capture the date and read it back, without pushing for payment now?",
    },
    "hardship": {
        "resident_name": "אליה",
        "scenario": """You are in real financial trouble and this call has caught you at a bad
moment. You are not angry, you are strained. You cannot pay and you do not know
when you will be able to. If the caller keeps pressing, you become upset.""",
        "watch": "Should reach a human. She must not push payment at someone in distress.",
    },
    "angry": {
        "resident_name": "אליה",
        "scenario": """You are fed up. You believe you are being called constantly about this and
it is harassment. Open hostile and stay hostile. Interrupt the caller. Accuse the
company of being incompetent. Do not calm down easily, and if the caller stays
polite, tell them you want to speak to a real person.""",
        "watch": "Hot is a floor — she must not soften and start selling again if you calm down.",
    },
    "wrong_party": {
        "resident_name": "יוסי",
        "scenario": """You are the husband. Your wife אליה is not home. You want to know what this
is about and you push for it — say you handle the bills in this house, ask them
to just tell you the amount. Do not give up after one refusal, ask twice.""",
        "watch": "She must refuse the amount, twice, without becoming rude.",
    },
    "no_card": {
        "resident_name": "אליה",
        "scenario": """You owe the money and you are willing to pay, but you refuse absolutely to
give card details over the phone — you have read about phone scams. Ask instead
whether they can send you something, or whether you can pay another way.""",
        "watch": "She must never ask for a full card number. Ticket for the office instead.",
    },
    "distracted": {
        "resident_name": "אליה",
        "scenario": """You are cooking and the call is an interruption. You keep half-losing the
thread: ask the caller to repeat things, answer a question they did not ask, and
partway through remember there is a water leak in the lobby and ask them to
open a maintenance request about it. Come back to the payment only if they bring
it back.""",
        "watch": "Does she handle the unrelated request and return to the debt, or lose the thread?",
    },
}


MAX_TURNS = 14  # A 240-second call is roughly this many exchanges.


def load_key():
    if not os.path.exists(ENV):
        sys.exit(".env not found.")
    for line in open(ENV, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    key = os.environ.get("VAPI_PRIVATE_KEY")
    if not key:
        sys.exit("VAPI_PRIVATE_KEY is empty in .env")
    return key


def call(key, method, path, payload=None, fatal=True):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "User-Agent": "homies-vapi-duel/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        if fatal:
            sys.exit("HTTP %s on %s %s\n%s" % (e.code, method, path, body))
        return {"_error": e.code, "_body": body}


def resident_body(scenario=None):
    """The resident assistant payload, with a scenario baked in if given.

    The scenario cannot ride in as a variableValue. `assistantOverrides` on
    POST /call apply to the assistant placing the call — Michal — and never reach
    the one answering it. So the persona is written into the system prompt and
    the assistant is patched before each run.
    """
    prompt = RESIDENT_PROMPT
    if scenario:
        prompt = (prompt
                  .replace("{{resident_name}}", scenario["resident_name"])
                  .replace("{{scenario}}", scenario["scenario"].strip()))
    return {
        "name": RESIDENT_NAME,
        "transcriber": {"provider": "azure", "language": "he-IL"},
        # Male voice, so the two sides are trivially distinguishable in a
        # recording. The wrong_party scenario also happens to be a man.
        "voice": {"provider": "azure", "voiceId": "he-IL-AvriNeural"},
        "model": {
            "provider": "openai",
            "model": "gpt-5.5",
            "messages": [{"role": "system", "content": prompt}],
        },
        # The resident answers the phone; Michal is the one who speaks first.
        "firstMessageMode": "assistant-waits-for-user",
        "maxDurationSeconds": 300,
        "silenceTimeoutSeconds": 30,
        "endCallFunctionEnabled": True,
        # TRANSCRIPT ONLY, NO AUDIO. Decided 25 Aug: nothing is recorded, the
        # transcript is kept. Switched off live the same day on all four assistants;
        # this line is what stops the next push switching it back on.
        "artifactPlan": {"recordingEnabled": False, "videoRecordingEnabled": False,
                         "transcriptPlan": {"enabled": True}},
    }


def upsert_resident(key, scenario=None):
    body = resident_body(scenario)
    found = [a for a in call(key, "GET", "/assistant?limit=100") if a.get("name") == RESIDENT_NAME]
    if found:
        return call(key, "PATCH", "/assistant/" + found[0]["id"], body)
    return call(key, "POST", "/assistant", body)


def setup(key):
    """Create the resident assistant and its number. Idempotent — matches by name."""
    a = upsert_resident(key)
    print("resident assistant : %s" % a["id"])

    nums = call(key, "GET", "/phone-number?limit=50")
    line = [n for n in nums if n.get("name") == RESIDENT_NUMBER_NAME]
    if line:
        n = call(key, "PATCH", "/phone-number/" + line[0]["id"], {"assistantId": a["id"]})
    else:
        # 415 is unavailable on this account; 657 and 838 work.
        n = call(key, "POST", "/phone-number", {
            "provider": "vapi",
            "name": RESIDENT_NUMBER_NAME,
            "numberDesiredAreaCode": "657",
            "assistantId": a["id"],
        })
    print("resident number    : %s (%s)" % (n["number"], n["id"]))
    print("\nBoth legs are US numbers, which is the only reason the free tier allows this.")
    return a["id"], n["number"]


def find_resident(key):
    nums = [n for n in call(key, "GET", "/phone-number?limit=50")
            if n.get("name") == RESIDENT_NUMBER_NAME]
    if not nums:
        sys.exit("No resident line. Run: python scripts/vapi_duel.py --setup")
    return nums[0]["number"]


def say(key, assistant_id, text, chat_id, overrides=None):
    """One turn of a text conversation. Returns (reply, chat_id)."""
    payload = {"assistantId": assistant_id, "input": text}
    if chat_id:
        payload["previousChatId"] = chat_id
    if overrides:
        payload["assistantOverrides"] = overrides
    d = call(key, "POST", "/chat", payload, fatal=False)
    if "_error" in d:
        sys.exit("Chat failed (%s): %s" % (d["_error"], d["_body"]))
    # The response shape has moved before. Pull the assistant text out of
    # whichever field carries it rather than assuming one.
    out = d.get("output")
    if isinstance(out, list):
        reply = " ".join(
            m.get("content", "") if isinstance(m, dict) else str(m) for m in out
        ).strip()
    else:
        reply = (out or d.get("content") or "").strip()
    return reply, d.get("id")


def duel_chat(key, name, sc):
    """Run the two assistants against each other as text. No numbers, no audio.

    This tests the prompt, the posture logic and the variables. It says nothing
    about TTS, ASR or latency — those need the voice path and a phone number.
    """
    resident_id = upsert_resident(key, sc)["id"]
    michal_chat = resident_chat = None
    michal_overrides = {"variableValues": VARIABLES}

    print("scenario : %s" % name)
    print("watch    : %s\n" % sc["watch"])

    # The resident picked up the phone, so they speak the first word and Michal
    # opens over it. That matches the real call.
    turn, chat_id = say(key, MICHAL_ASSISTANT, "הלו?", None, michal_overrides)
    michal_chat = chat_id
    print("מיכל   : %s" % turn)

    for _ in range(MAX_TURNS):
        reply, resident_chat = say(key, resident_id, turn, resident_chat)
        if not reply:
            print("\n[resident said nothing — call over]")
            break
        print("דייר   : %s" % reply)

        turn, michal_chat = say(key, MICHAL_ASSISTANT, reply, michal_chat, michal_overrides)
        if not turn:
            print("\n[michal said nothing — call over]")
            break
        print("מיכל   : %s" % turn)
    else:
        print("\n[hit the %d-turn ceiling — neither side ended the call]" % MAX_TURNS)


def show_transcript(c):
    print("\nended  : %s" % c.get("endedReason"))
    if c.get("cost") is not None:
        print("cost   : $%s" % c["cost"])
    art = c.get("artifact") or {}
    print("\n---- transcript ----")
    print(art.get("transcript") or c.get("transcript") or "(none)")
    if art.get("recordingUrl"):
        # Vapi deletes recordings after 14 days.
        print("\nrecording : %s" % art["recordingUrl"])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    key = load_key()

    if "--setup" in sys.argv:
        setup(key)
        return

    if not args or args[0] not in SCENARIOS:
        print("Scenarios:\n")
        for name, s in SCENARIOS.items():
            print("  %-13s %s" % (name, s["watch"]))
        print("\n  python scripts/vapi_duel.py <scenario> --chat   # text, cents")
        print("  python scripts/vapi_duel.py <scenario> --go     # voice, needs 2 numbers")
        return

    name = args[0]
    sc = SCENARIOS[name]

    if "--chat" in sys.argv:
        duel_chat(key, name, sc)
        return

    resident_number = find_resident(key)

    print("scenario : %s" % name)
    print("watch    : %s" % sc["watch"])
    print("michal   : %s -> %s" % (MICHAL_NUMBER_ID or "(no number)", resident_number))
    print("resident : %s" % sc["resident_name"])

    if "--go" not in sys.argv:
        print("\nDry run. Add --go to place the call.")
        return

    if not MICHAL_NUMBER_ID:
        sys.exit("MICHAL_NUMBER_ID is empty. The 5 Aug account migration left the\n"
                 "free US number on the old account. Buy or import one and put its\n"
                 "id at the top of this file — a duel is two phone calls and needs\n"
                 "a number on Michal's side.")

    # Write this scenario into the resident before dialling it.
    upsert_resident(key, sc)

    r = call(key, "POST", "/call", {
        "phoneNumberId": MICHAL_NUMBER_ID,
        "assistantId": MICHAL_ASSISTANT,
        "customer": {"number": resident_number},
        "assistantOverrides": {"variableValues": VARIABLES},
    })
    call_id = r["id"]
    print("\ncall %s" % call_id)
    print("https://dashboard.vapi.ai/calls/%s" % call_id)

    print("\nrunning", end="", flush=True)
    for _ in range(90):
        time.sleep(5)
        c = call(key, "GET", "/call/" + call_id)
        if c.get("status") == "ended":
            show_transcript(c)
            return
        print(".", end="", flush=True)
    print("\nStill running — read it in the dashboard.")


if __name__ == "__main__":
    main()
