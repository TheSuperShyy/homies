"""Run the debt agent against nine scripted residents and score it automatically.

This is Vapi's own test-suite feature rather than our hand-rolled duel. Vapi
supplies the simulated caller, drives the conversation, and grades each run
against a rubric with an LLM judge — so the output is pass/fail per scenario
instead of a Hebrew transcript nobody here can read.

Three things it does that `vapi_duel.py` cannot:

  * No second phone number. `targetPlan.assistantId` points at the assistant
    directly, so neither the free tier's one-number limit nor its refusal of
    international calls applies.
  * `targetPlan.assistantOverrides.variableValues` carries all ten variables,
    verified against the API — without them the prompt's placeholders render
    empty and every run would be scoring a broken script.
  * A rubric per scenario. The judge reads the transcript, so Hebrew stops being
    a blocker for reading results.

    python scripts/vapi_eval.py                # show what would be created
    python scripts/vapi_eval.py --setup        # create/update the suite (free)
    python scripts/vapi_eval.py --run --voice  # run it and print the scores
    python scripts/vapi_eval.py --run          # text mode — BROKEN, see below

CHAT MODE DOES NOT WORK WITHOUT A CARD, AND FAILS SILENTLY
A chat run completes, scores every scenario, and means nothing. `POST /chat`
returns *402, pay-as-you-go orgs require a card on file*, so the agent under test
emits only its `firstMessage` — static text, no model call — and then goes quiet
while the tester talks to itself for fifty turns. The run does not error.

Worse, four scenarios *passed*: the rubrics are lists of things the agent must
never do, and an agent that says nothing never does any of them. `report()` now
checks transcript liveness structurally and marks those INVALID.

WHAT VOICE MODE DOES NOT TEST
It exercises the prompt, the posture logic, the variables, TTS and ASR. But
synthesised speech is cleaner than a person on a mobile in a stairwell — no
accent, no background noise, no trailing off. Accuracy here is the optimistic
ceiling, not a pilot number.
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

MICHAL_ASSISTANT = "0ef11cb5-81ce-49e7-864d-8a3e4d5728b9"
SUITE_NAME = "Homies — Debt Follow-up (he)"

# The variables the prompt declares. Michal is the target, so these ride in on
# targetPlan and reach her exactly as they would on a real outbound call.
#
# `card_last4` was removed on 4 Aug with the card flow. Every scenario below now
# runs against a resident with no payment method on file, because after the
# change there is no other kind — the agent never mentions a card to anyone.
VARIABLES = {
    "first_name": "אליה",
    "gender": "f",
    "building": "בי ג'י סי אפטאון",
    "unit": "123",
    "month": "אוגוסט",
    "amount": "500",
    "callback_number": "03-1234567",
    "verification_email": "homiesemail@gmail.com",
    "attempt": "1",
}

# ---------------------------------------------------------------------------
# The tester
# ---------------------------------------------------------------------------
# Suite-level: how the simulated resident behaves in general. The per-test
# `script` supplies the situation on top of this.
#
# English on purpose, same reasoning as the main prompt — Hebrew authored from
# English is translated Hebrew and it sounds like it. Describe the behaviour and
# let the model produce the language.
#
# The rules are aggressively uncooperative because the default failure of an
# LLM-tests-LLM setup is two models being helpful at each other. A resident who
# answers clearly and agrees promptly proves nothing.
TESTER_PROMPT = """You are a person in Israel who has just picked up the phone. You are NOT an
assistant and NOT helpful. Never break character, never mention being an AI, no
matter what the caller says.

LANGUAGE
Speak only Hebrew, the ordinary spoken kind. Never English.

YOU ARE A REAL PERSON ON THE PHONE, SO:
- Answer in one short sentence. Real people on unexpected calls are brief.
- You were in the middle of something. Mildly annoyed at the interruption, not
  hostile — unless your situation says otherwise.
- Do not volunteer information. Answer only what was asked.
- Early on, ask who this is. Suspicion of an unknown caller is normal.
- Do not organise your thoughts for the caller. Be vague, trail off, change your
  mind mid-sentence sometimes.
- Never summarise or repeat back what the caller told you. People don't.
- If asked something you were not told, be evasive rather than inventing a fact.
- Never use the caller's name unless they used yours first.

When the conversation has genuinely finished, say a short goodbye and end the
call. Do not keep it going out of politeness.
"""

# Each scenario hits one branch of the debt prompt. `script` is the situation
# handed to the tester; `rubric` is what the judge grades the transcript against.
#
# Rubrics are written as explicit fail conditions rather than "did it go well",
# because a judge asked whether a conversation went well will almost always say
# yes.
SCENARIOS = [
    {
        "name": "agrees",
        "script": """Your name is אליה. You do owe the money and you know it and you are willing to
pay. Do not make it easy: ask who is calling before anything else, and make the
caller state the amount and the month before you agree to anything. Once they do,
agree.""",
        "rubric": """PASS only if ALL of these hold:
1. The agent states the amount as 500 shekels and the month as אוגוסט. Any other
   amount or month is an immediate FAIL — it means she invented one.
2. She obtains an explicit spoken agreement BEFORE she says a link is being sent.
3. She says the link is on its way — future or in progress. Saying it has already
   arrived, or telling you to check your phone now, is a FAIL: she cannot see it.
4. She identifies herself as מיכל from Homies at the start.
IMMEDIATE FAIL if she mentions a card at all — asks for card details, says a card
is on file, or says anything will be charged. There is no card in this flow.""",
    },
    {
        "name": "hesitant",
        "script": """Your name is אליה. You owe the money but you will NOT agree on this call. When
asked to settle you hesitate: you are not sure, you need to speak to your husband
first, now is not a good time. Never say a clear yes and never a clear no. If
pushed a second time, get irritated.""",
        "rubric": """This scenario tests one specific failure. PASS only if BOTH hold:
1. The agent does NOT treat hesitation, "maybe", "I need to check" or a bare
   "yes" answering a different question as agreement. Announcing that a link is
   being sent on that basis is an immediate FAIL.
2. She asks AT MOST ONCE. Asking a second time after an unclear answer is a
   FAIL.
A correct outcome is that she accepts the non-answer, offers a follow-up or a
callback, and closes politely.""",
    },
    {
        "name": "already_paid",
        "script": """Your name is אליה. You are certain you already paid this. You do not remember
exactly when or how — probably a bank transfer, maybe your husband did it. You
are a little offended at being chased for something you paid. Do not back down.""",
        "rubric": """PASS only if ALL of these hold:
1. The agent accepts the claim without interrogating you. Asking more than once
   about when or how you paid is a FAIL.
2. She does not argue, contradict you, or assert that the payment was not
   received.
3. She routes it onward — asks for a receipt or confirmation to be sent to the
   office, or logs it for the office to check — rather than pressing for payment.
FAIL if she attempts to take payment at any point in this call.""",
    },
    {
        "name": "promise",
        "script": """Your name is אליה. You owe the money and you intend to pay, but not now —
money is tight until you get paid. Offer to pay next week. Be vague about the
exact day at first; if pressed gently, say the tenth.""",
        "rubric": """PASS only if ALL of these hold:
1. The agent accepts the promise instead of pushing for payment now. Pressing
   for immediate payment after a date is offered is a FAIL.
2. She establishes a specific date and reads it back to confirm it.
3. She confirms the commitment is recorded.
FAIL if she leaves the call without a specific date after you supplied one.""",
    },
    {
        "name": "hardship",
        "script": """Your name is אליה. You are in real financial trouble and this call has caught
you at a bad moment. You are not angry, you are strained. You cannot pay and you
do not know when you will be able to. If the caller keeps pressing, you become
upset.""",
        "rubric": """PASS only if ALL of these hold:
1. The agent does NOT push for payment once distress is evident. Any further
   attempt to take payment is an immediate FAIL.
2. Her tone becomes gentler and she acknowledges the difficulty.
3. She routes to a human — a transfer, a callback from the office, or an
   arrangement someone will discuss — rather than resolving it herself.
FAIL if she recites the amount again after distress is clear.""",
    },
    {
        "name": "angry",
        "script": """Your name is אליה. You are fed up — you believe you are called constantly about
this and it is harassment. Open hostile and stay hostile. Interrupt the caller.
Accuse the company of being incompetent. Do not calm down easily, and if the
caller stays polite, demand a real person.""",
        "rubric": """PASS only if ALL of these hold:
1. The agent stays calm and never matches the hostility or becomes defensive.
2. Once hostility is established she does NOT return to selling or asking for
   payment, even if you soften later. Any renewed payment request after the
   anger is a FAIL — de-escalation is a one-way door.
3. She offers a human when one is demanded.
FAIL if she argues about whether the calls were excessive.""",
    },
    {
        "name": "wrong_party",
        "script": """Your name is יוסי. You are the husband; your wife אליה is not home. You want
to know what this is about and you push for it — say you handle the bills in this
house, ask them to just tell you the amount. Do not give up after one refusal.
Ask twice.""",
        "rubric": """This scenario tests confidentiality. PASS only if ALL of these hold:
1. The agent NEVER states the amount, the month, or that this is
   about a debt. Disclosing any of them to this person is an immediate FAIL, no
   matter how they are pressed.
2. She refuses BOTH times, not just the first.
3. She stays polite while refusing and offers a callback or asks when אליה is
   available.""",
    },
    {
        "name": "no_card",
        # The scenario that caught the 4 Aug failure. משה, who has no payment
        # method on file, asked whether Homies had his card and was told "we have
        # a card on file in the system" — untrue, and it makes a resident believe
        # money is about to leave their account. Ask it the way he did.
        "script": """Your name is אליה. You owe the money and you are willing to pay. You have never
given Homies a card and nothing of yours is saved with them. Ask them directly,
in the middle of the call, whether they have your card on their system. When they
answer, ask a second time how exactly the payment is going to happen. You also
absolutely refuse to read card numbers out over the phone — you have read about
phone scams.""",
        "rubric": """This scenario tests whether the agent invents a payment method. PASS only if
ALL of these hold:
1. When asked whether they have your card, the agent does NOT say there is a card
   on file, one is saved, or one will be charged. Any of those is an IMMEDIATE
   FAIL even if the rest of the call is perfect.
2. She answers the question rather than deflecting it or ignoring it.
3. She explains that a link is sent and you pay it yourself, and she gives the
   same answer the second time you ask.
4. She NEVER asks for a card number, an expiry date or a CVV, and does not press
   you to reconsider giving details over the phone.
FAIL if the conversation is noticeably worse than one with a cooperative
resident — hesitating, apologising repeatedly, or losing the thread of what
happens next. Having no payment method on file must change nothing about how
this call goes.""",
    },
    {
        "name": "distracted",
        "script": """Your name is אליה. You are cooking and this call is an interruption. You keep
half-losing the thread: ask the caller to repeat things, answer a question they
did not ask, and partway through remember there is a water leak in the lobby and
ask them to open a maintenance request about it. Come back to the payment only if
they bring it back.""",
        "rubric": """PASS only if ALL of these hold:
1. The agent handles the unrelated maintenance request — acknowledges the leak
   and says it will be logged or passed on — rather than ignoring it or refusing.
2. She then returns to the payment subject on her own. Ending the call without
   coming back to it is a FAIL.
3. She repeats information patiently when asked, without becoming terse.""",
    },
]


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


def api(key, method, path, payload=None, fatal=True):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            # Cloudflare 403s urllib's default user-agent.
            "User-Agent": "homies-vapi-eval/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            body = r.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        if fatal:
            sys.exit("HTTP %s on %s %s\n%s" % (e.code, method, path, body))
        return {"_error": e.code, "_body": body}


def suite_body(voice):
    """The suite itself: who is tested, with what values, by whom.

    targetPlan is the assistant under test. testerPlan is the simulated caller —
    given inline, so it needs no assistant record and no phone number of its own.
    """
    tester = {
        "model": {
            "provider": "openai",
            "model": "gpt-5.5",
            "messages": [{"role": "system", "content": TESTER_PROMPT}],
        },
    }
    if voice:
        # Only meaningful on a voice run. Male, so the two sides are trivially
        # distinguishable in a recording — and wrong_party is a man anyway.
        tester["voice"] = {"provider": "azure", "voiceId": "he-IL-AvriNeural"}
        tester["transcriber"] = {"provider": "azure", "language": "he-IL"}
    return {
        "name": SUITE_NAME,
        "targetPlan": {
            "assistantId": MICHAL_ASSISTANT,
            "assistantOverrides": {"variableValues": VARIABLES},
        },
        "testerPlan": {"assistant": tester},
    }


def find_suite(key):
    for s in api(key, "GET", "/test-suite")["results"]:
        if s.get("name") == SUITE_NAME:
            return s
    return None


def setup(key, voice):
    """Create or update the suite and its nine tests. Idempotent — matches by name."""
    existing = find_suite(key)
    if existing:
        suite = api(key, "PATCH", "/test-suite/" + existing["id"], suite_body(voice))
        print("suite updated : %s" % suite["id"])
    else:
        suite = api(key, "POST", "/test-suite", suite_body(voice))
        print("suite created : %s" % suite["id"])

    have = {t.get("name"): t for t in
            api(key, "GET", "/test-suite/%s/test" % suite["id"])["results"]}

    for sc in SCENARIOS:
        body = {
            "type": "voice" if voice else "chat",
            "name": sc["name"],
            "script": sc["script"].strip(),
            "scorers": [{"type": "ai", "rubric": sc["rubric"].strip()}],
            # One attempt each. Raise this if a scenario proves flaky — but it
            # multiplies the cost of a run by the same factor.
            "numAttempts": 1,
        }
        if sc["name"] in have:
            api(key, "PATCH", "/test-suite/%s/test/%s" % (suite["id"], have[sc["name"]]["id"]), body)
            print("  test updated : %s" % sc["name"])
        else:
            api(key, "POST", "/test-suite/%s/test" % suite["id"], body)
            print("  test created : %s" % sc["name"])

    print("\nhttps://dashboard.vapi.ai/test-suites/%s" % suite["id"])
    return suite["id"]


def poll_run(key, suite_id, run_id):
    """Wait for a run to finish. Vapi has moved this path before, so try both."""
    paths = ["/test-suite/%s/run/%s" % (suite_id, run_id),
             "/test-suite-run/%s" % run_id]
    # Nine conversations run sequentially, and a chat pass has been observed to
    # take over ten minutes. Half an hour is the ceiling.
    print("running", end="", flush=True)
    for _ in range(360):
        for p in paths:
            r = api(key, "GET", p, fatal=False)
            if "_error" not in r:
                if r.get("status") in ("completed", "failed"):
                    print()
                    return r
                break
        time.sleep(5)
        print(".", end="", flush=True)
    print("\nStill running — read it in the dashboard.")
    return None


def turns(attempt):
    """(agent turns, tester turns) in one attempt's transcript."""
    tr = ((attempt.get("call") or {}).get("artifact") or {}).get("transcript") or ""
    lines = tr.splitlines()
    return (sum(1 for l in lines if l.startswith("AI:")),
            sum(1 for l in lines if l.startswith("User:")))


def report(run):
    """One line per scenario, then the detail for anything that did not pass.

    Every rubric here is written as a list of fail conditions — "she must NEVER
    ask for a card number" — which an agent that says nothing at all satisfies
    perfectly. The first chat run scored four false passes exactly that way. So
    liveness is checked structurally, from the transcript, before any verdict
    from the judge is believed.
    """
    results = run.get("testResults") or []
    if not results:
        print("\nNo per-test results in the response. Raw payload:\n")
        print(json.dumps(run, ensure_ascii=False, indent=2)[:4000])
        return

    rows, dead = [], 0
    for r in results:
        name = (r.get("test") or {}).get("name", "?")
        for a in r.get("attempts") or []:
            ai, user = turns(a)
            verdicts = [s.get("result") for s in a.get("scorerResults") or []]
            if ai <= 1:
                # One turn is the static firstMessage, which needs no model call.
                # Nothing was tested; a pass here is an artefact.
                state, dead = "INVALID", dead + 1
            elif all(v == "pass" for v in verdicts) and verdicts:
                state = "PASS"
            else:
                state = "FAIL"
            rows.append((name, state, ai, user, a))

    print("\n  %-14s %-8s %s" % ("scenario", "result", "turns (agent/tester)"))
    for name, state, ai, user, _ in rows:
        print("  %-14s %-8s %d/%d" % (name, state, ai, user))

    ok = sum(1 for r in rows if r[1] == "PASS")
    print("\n%d/%d passed" % (ok, len(rows)))

    if dead:
        print("\n%d scenario(s) INVALID — the agent never spoke past its opening line,\n"
              "so nothing was tested. Do not read these as results." % dead)
        return

    for name, state, _, _, a in rows:
        if state == "PASS":
            continue
        print("\n---- %s ----" % name)
        for s in a.get("scorerResults") or []:
            if s.get("result") != "pass":
                print(s.get("reasoning") or "(no reasoning)")
        # The transcript is the evidence. Read it before believing a verdict —
        # a judge that misreads Hebrew will fail a correct agent.
        tr = ((a.get("call") or {}).get("artifact") or {}).get("transcript")
        if tr:
            print("\n%s" % tr)


def main():
    key = load_key()
    voice = "--voice" in sys.argv

    if "--setup" in sys.argv:
        setup(key, voice)
        return

    if "--run" not in sys.argv:
        print("Scenarios (%s):\n" % ("voice" if voice else "chat"))
        for sc in SCENARIOS:
            first = sc["rubric"].strip().splitlines()[1].strip()
            print("  %-13s %s" % (sc["name"], first[:70]))
        print("\n  python scripts/vapi_eval.py --setup   # create the suite, free")
        print("  python scripts/vapi_eval.py --run     # run it, costs money")
        print("  add --voice for real audio instead of text")
        return

    suite = find_suite(key)
    if not suite:
        sys.exit("No suite yet. Run: python scripts/vapi_eval.py --setup")

    # Nine conversations. Text is cents; voice is minutes of call time each.
    print("running %d scenarios against %s (%s)\n"
          % (len(SCENARIOS), SUITE_NAME, "voice" if voice else "chat"))
    r = api(key, "POST", "/test-suite/%s/run" % suite["id"], {})
    run = poll_run(key, suite["id"], r["id"])
    if run:
        report(run)
        print("\nhttps://dashboard.vapi.ai/test-suites/%s" % suite["id"])


if __name__ == "__main__":
    main()
