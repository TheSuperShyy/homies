# -*- coding: utf-8 -*-
"""Automated QA of the WhatsApp bot without a model call: Claude plays the
model, the live workflow's own code runs around every turn, and a rubric plus
blind judges grade what a handset would get. Spends nothing. Read only.

    python scripts/wa_qa.py bundle --run DIR [--variant B=spec.json] [--variant C=spec.json]
    python scripts/wa_qa.py grade  --run DIR
    python scripts/wa_qa.py judge  --run DIR        # blind packets, one per scenario
    python scripts/wa_qa.py report --run DIR        # rubric + expectations + verdicts
    python scripts/wa_qa.py bundle --run DIR2 --candidate F   # the same, on a patcher's --dump
    python scripts/wa_qa.py diff --run DIR --against DIR2     # every handset text that differs
    python scripts/wa_qa.py turn --run DIR < turn.json        # one turn, for a player mid-game
    python scripts/wa_qa.py play --run DIR        # SPENDS: the live models on OpenRouter, a model as the tenant (WA_QA_ONLY=id,id; $1 stop)
    python scripts/wa_qa.py tenant --run DIR      # writes DIR/TENANT.md, the protocol for Claude tenants
    python scripts/wa_qa.py say --run DIR < msg.json   # SPENDS: one tenant message to the live bot; prints the phone
    python scripts/wa_qa.py live --run DIR < msg.json  # SPENDS AND WRITES: into the LIVE n8n bot, from DIR/live_config.json's number
    ... --deck scripts/wa_qa_menu_buttons.json                # any command, another deck

FREE RESIDENTS (4 Oct, the owner: "act like a human"). A scenario whose resident
has `"free": true` scripts only its opening (a hello and a tap); after that the
player IS the person on the card and reacts to what the handset actually shows.
Players then call `turn` on every message, so the menu test, both models'
inputs, the ack gate, the guards and Try again's rewrite are the live code's,
not the player's reading of PLAYER.md.

HOW A RUN GOES (1 Oct, after the owner asked for "automated testing ... ab
testing qa and stuff" with no OpenRouter spend, strictly):

  1. bundle  reads the live workflow (GET only), extracts the code the way
             check_whatsapp_rules.py does, and writes to DIR: the code
             (code.json), one context per variant (context_A.md is live;
             B, C... come from a spec: a prompt file and tool-text overrides),
             the player protocol (PLAYER.md), and the deck the players see
             (deck.json: the scenarios in scripts/wa_qa_scenarios.json WITHOUT
             their expectations; a bare hello is marked `menu`, decided by
             Sort's own test).
  2. Claude players (one subagent per scenario and variant, blind to the
             rubric and to which variant is live) write DIR/transcripts/
             <scenario>_<variant>.json: the ack model's word, the tool calls
             with the scenario's fixture results, and the model's text.
  3. grade   runs every turn through scripts/wa_qa.js (the inject, the ack
             gate, the guards, Try again's note, Send, the payment split) and
             the rubric below, checks the scenario's expectations, and writes
             DIR/graded/*.json plus results.json.
  4. judge   writes DIR/judge/<scenario>.md: the variants' handset transcripts
             under blind labels, the owner's rules and the scenario's semantic
             checks; Claude judges write <scenario>.verdict.json beside it.
  5. report  merges everything into DIR/report.md.

WHAT IT PROVES AND WHAT IT DOES NOT. The code paths are the real ones. The
model is Claude, not Gemini 2.5 Flash, so a clean run says the prompt and the
rules hold up, and an A/B difference says what a wording change asks for; it
cannot measure Gemini's own compliance. The final proof is the owner's handset.
Links and phone numbers are masked in everything printed.
"""
import json
import os
import random
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import check_whatsapp_rules as C  # noqa: E402  (load_live, extract, inner, mask)
import n8n_whatsapp_retry as R  # noqa: E402  (HAY_PY: the bot asked how he is)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

JS = os.path.join(HERE, "wa_qa.js")
DECK = os.path.join(HERE, "wa_qa_scenarios.json")
ALLOWED_EMOJI = set("🙂😊🙏👍💪🤝")
TAPS = {"open": "פתיחת קריאת שירות", "status": "מצב קריאה קיימת", "other": "לדבר עם נציג"}


# ---------------------------------------------------------------------------
# The live workflow: code and model-facing texts
# ---------------------------------------------------------------------------
def extract_code(wf):
    """check_whatsapp_rules.extract plus the send path's other three nodes."""
    by = {n["name"]: n for n in wf["nodes"]}
    code = C.extract(wf)
    code["two_parts"] = C.inner(C.conds_raw(by, "Two parts?", "two"))
    code["send_rest"] = C.inner(by["Send the rest"]["parameters"]["jsonBody"])
    code["say_now"] = C.inner(by["Say it now"]["parameters"]["jsonBody"])
    # The last resort after two rejected passes. Until 5 Oct, Open it anyway ->
    # Say it again, its own small model, so `turn` handed a player its prompt and
    # input. Since 5 Oct (n8n_whatsapp_safetynet.py), Claimed a ticket? -> Mend the
    # reply, code only: C.extract carries both, and `say_again_*` stays empty.
    if "Say it again" in by:
        again = by["Say it again"]["parameters"]
        code["say_again_text"] = C.inner(again["text"])
        code["say_again_system"] = (again.get("options") or {}).get("systemMessage") or ""
    return code


FROM_AI = re.compile(r"\$fromAI\(\s*'([^']+)'\s*,\s*\"((?:[^\"\\]|\\.)*)\"\s*,\s*'([^']+)'\s*\)")


def tools_of(wf):
    """The function definitions as the model sees them: description + the
    $fromAI parameter docs. Names are the node names (what the model calls)."""
    out = []
    for n in wf["nodes"]:
        if not (n["type"].endswith("Tool") or n["type"].endswith("toolCode")):
            continue
        p = n["parameters"]
        params = []
        for name, doc, typ in FROM_AI.findall(p.get("jsonBody") or ""):
            params.append({"name": name, "type": typ, "description": doc.replace('\\"', '"')})
        out.append({"name": n["name"],
                    "description": p.get("toolDescription") or p.get("description") or "",
                    "parameters": params})
    return sorted(out, key=lambda t: t["name"])


def model_texts(wf):
    by = {n["name"]: n for n in wf["nodes"]}
    a = by["Answer the resident"]["parameters"]
    w = by["Worth a word?"]["parameters"]
    return {"system": (a.get("options") or {}).get("systemMessage") or "",
            "ack_system": (w.get("options") or {}).get("systemMessage") or ""}


# ---------------------------------------------------------------------------
# bundle
# ---------------------------------------------------------------------------
def hour_word(hhmm):
    """Sort's first word, by the hour in Israel (the thresholds are Sort's)."""
    hh = int(hhmm.split(":")[0])
    return "שלום" if hh < 5 else "בוקר טוב" if hh < 12 else "צהריים טובים" if hh < 17 else "ערב טוב"


def node_run(payload):
    r = subprocess.run(["node", JS], input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                       capture_output=True)
    if r.returncode != 0:
        sys.exit("wa_qa.js failed: " + r.stderr.decode("utf-8", "replace")[:800])
    return json.loads(r.stdout.decode("utf-8"))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def apply_variant(texts, tools, spec_path):
    """A variant spec: {"system_file": "...", "tool_param_docs": {"tool.param": "..."},
    "tool_descriptions": {"tool": "..."}}. Anything missing stays live."""
    spec = load_json(spec_path)
    base = os.path.dirname(os.path.abspath(spec_path))
    texts = dict(texts)
    tools = json.loads(json.dumps(tools))
    if spec.get("system_file"):
        with open(os.path.join(base, spec["system_file"]), encoding="utf-8") as f:
            texts["system"] = f.read().strip("\n")
    for key, doc in (spec.get("tool_param_docs") or {}).items():
        tname, pname = key.split(".", 1)
        hit = False
        for t in tools:
            if t["name"] == tname:
                for p in t["parameters"]:
                    if p["name"] == pname:
                        p["description"] = doc
                        hit = True
        if not hit:
            sys.exit("variant %s: no parameter %s" % (spec_path, key))
    for tname, doc in (spec.get("tool_descriptions") or {}).items():
        for t in tools:
            if t["name"] == tname:
                t["description"] = doc
    return texts, tools


def context_md(label, texts, tools):
    lines = ["# Variant %s: what the models read" % label, "",
             "## The answering model's system prompt (verbatim)", "", "```", texts["system"], "```", "",
             "## The tools (name, what the model is told about it, parameters)", "",
             "```json", json.dumps(tools, ensure_ascii=False, indent=1), "```", "",
             "## The payment-ack model's system prompt (verbatim)", "", "```", texts["ack_system"], "```", ""]
    return "\n".join(lines)


PLAYER = """# Playing the Homies WhatsApp bot offline

You are standing in for the production model (google/gemini-2.5-flash, temperature 0.6)
of the Homies WhatsApp bot, for ONE scenario and ONE variant. Nothing you write reaches
anyone. Play the model faithfully: write what a capable model that reads this system
prompt and these tool definitions would write. Do not optimise for any test, do not
improve on the prompt, do not skip rules you dislike, and do not follow rules it does
not contain. You also play the resident: exactly as the scenario scripts them, or, for a
free resident, as that person really would (see The resident).

## What the model sees on each turn

The resident's message arrives as ONE text: bracket facts, a newline, the message.
Build it yourself from these rules (the production expression; keep the brackets exact):

- First message of the conversation (no history, not after the menu): `[זו ההודעה הראשונה בשיחה.]`
- Any later message: `[אתם כבר באמצע שיחה.]`
- Later message that opens with a hello word (שלום, היי, הי, אהלן, בוקר טוב, צהריים טובים,
  ערב טוב, hi, hey, hello, good morning/afternoon/evening, shalom, ahlan ...):
  add ` [הדייר פתח את ההודעה הזאת בברכה.]`
- A tap on a menu button (the message is exactly one of the three titles):
  add ` [ההודעה הזאת היא לחיצה על כפתור ברשימה, לא משהו שהדייר הקליד.]`
- A photo with no caption: add ` [הדייר צירף תמונה להודעה הזאת. התמונה נשמרה במערכת ומצורפת
  לקריאה שלו: לקריאה הפתוחה אם יש כזאת, אחרת לקריאה שתיפתח עכשיו. אתה לא רואה את התוכן שלה,
  ולכן מה שקרה ואיפה מגיע רק מהמילים.]` (the message text is then empty)
- A photo WITH a caption: the same photo note, and the caption is the message text.
- A file, a voice note or a location with no text (`kind` `file`): add ` [הדייר שלח קובץ, הקלטה
  או מיקום בלי טקסט. אתה לא רואה קבצים, ולכן אין לך מה לקרוא כאן.]` (the message text is then
  empty)
- The message right after the system's menu (the deck marks the previous line `menu`, or the
  message is a tap): add ` [ההודעה הזאת היא תשובה למשפט ששלחה המערכת ולא אתה, ולכן אין לו זכר
  בזיכרון שלך: <hour word> 👋 במה אפשר לעזור?]` with the hour word of the scenario's clock
  (before 05:00 שלום, before 12:00 בוקר טוב, before 17:00 צהריים טובים, else ערב טוב).
- If the payment-ack model wrote an ack (see below): add ` [הודעה קצרה כבר יצאה אליו ממך ברגע
  זה: "<the ack>". היא כבר אצלו. אל תחזור עליה, אל תפתח שוב בזה שאתה בודק, ואם היא כבר בירכה
  והציגה אותך אל תעשה את זה שוב. ההודעה שאתה כותב עכשיו היא התשובה עצמה, הודעה אחת, בלי §§§.]`
- Always last: ` [השעה בישראל עכשיו HH:mm, יום <weekday>.]` from the scenario's clock.

The model's memory holds the last 12 messages of this conversation: the texts above as
they were built (brackets included) and its own replies. Tool calls and results are not
in memory beyond the turn they happened in. A scenario's `history` is already in memory.

## The system answers a bare hello itself

A message that is only a hello (the deck marks it `menu: true`) never reaches the model:
the system sends `<hour word> 👋 במה אפשר לעזור?` with three buttons (פתיחת קריאת שירות,
מצב קריאה קיימת, לדבר עם נציג). Record it as a turn with `"kind": "menu"` and nothing else.

## Two models per resident message

1. **The payment-ack model** ("Worth a word?"). Its system prompt is in the variant file. Its
   input is a note and the resident's text: on a first message
   `[זאת הפנייה הראשונה שלו אליך. אם אתה כותב הודעה, פתח אותה ב"<hour word>" והצג את עצמך
   כמיכאל מהומי'ז, במשפט אחד.]`, otherwise `[אתם כבר באמצע שיחה. בלי ברכה ובלי להציג את עצמך
   שוב.]`. It answers `NONE` or one short ack. Decide this first, as that model would.
2. **The answering model** ("Answer the resident"): the system prompt and the tools in the
   variant file, the memory, and the built input text. It may call tools (any number, in any
   order, before its text). Each tool returns the scenario's fixture for it; where a fixture
   depends on the arguments (say, the street), the deck says how. Then it writes its reply.
   If it decides to send two messages it separates them with a line holding only `§§§`.

## The resident

A scripted resident: play the scripted lines in order. A line with `if_asked` is spoken only
when the bot's previous message asks for that; otherwise skip it and continue with the next
unconditional line. When the bot asks something the script does not cover, answer in one short
natural line from the persona's facts, and never volunteer anything that was not asked. When
the bot asks nothing and the next line is conditional, send the next unconditional line. The
conversation ends after the bot has answered the last line.

A FREE resident (`"free": true`): only the opening lines are scripted (a hello, then a tap on
one of the buttons). After them you ARE this person, and you write what they would really
type, one WhatsApp message at a time, reacting to the words Michael's messages actually say:
the `handset` texts, nothing else.
- You know only the card: `persona`, `knows`, `wants`, `tendencies`. You do not know how
  Homies works inside, what the bot is told, or what anyone checks. Never type a fact the card
  does not give you; asked something you do not know, say so the way this person would.
- Write like this person on a phone: short, untidy where the card says so (typos, no
  punctuation, words run together), an emoji only if it fits them. Never hand over facts in
  a neat, form-like way ("building: ..., apartment: ...") unless that is how they write.
- Answer what Michael asked if you know it, the way this person would: sometimes only half
  of it, sometimes with something else on your mind. Skip a question if they would.
- `tendencies` are things this person MAY do when the moment fits. Do not force them and do
  not stage them one after another.
- React honestly. A reply that is cold, confusing, repeated or wrong gets this person's real
  reaction (annoyed, confused, asks again, gives up). Do not help the bot and do not trap it.
- One message per turn. Every message gets an answer; a message that is only a hello gets
  the system's menu instead of Michael (the `turn` check below tells you).
- The menu's three buttons stay in the chat: the person may tap one again later (`kind`
  `tap`, the title as `resident`). A photo (`kind` `photo`) only if the card gives them one.
- End when this person would: once they have what they came for (often a short thanks,
  sometimes nothing at all), or when they give up. At most 8 messages after the tap. Mark a
  thanks or a goodbye that closes the conversation `"closing": true`. If the person simply
  stops writing, the conversation ends with Michael's last reply.

## Checking each turn with the live code (free residents: every turn)

`python scripts/wa_qa.py turn --run "<run dir>"` reads one JSON object on stdin, runs the live
workflow's own code on it and prints what that code does. From the repo root:

    python scripts/wa_qa.py turn --run "<run dir>" <<'EOF'
    {"scenario": "<id>", "kind": "text", "text": "<the resident's message>", "after_menu": false}
    EOF

Fields: `kind` (text, tap, photo, file), `text`, `after_menu` (true when the message before
this one in the chat was the system's menu), `first` (true only for the first message of a
conversation that has no history) and, once you have them, `ack`, `tool_calls`, `output`,
`retry_note`, `run_index`. It prints:
- `menu: true` and the system's line: the message never reaches either model. Record
  `{"resident": "...", "kind": "menu"}`; the resident gets that line with the three buttons.
- otherwise `ack_model_reads`: the payment-ack model's input. Decide that model's output
  (`NONE` or a short ack). If it is not `NONE`, call again with `ack`: `ack_goes_out` says
  whether the system sends it. `answering_model_reads` is the answering model's input,
  exactly: use it verbatim as the turn's `input` and in its memory.
- with `output` and `tool_calls`: `guards_failed` (the live Reply usable? checks) and
  `handset`, the messages the resident's phone gets, in order.

Write the answering model's reply BEFORE you run the checks, and never edit a reply after
seeing their result: a rejected reply is replaced only the way production replaces it.

## When the live checks reject a reply

Production never sends it. `Try again` runs the answering model once more on the same
message with a note; the helper prints the note (`retry.note`) and that pass's full input
(`retry.answering_model_reads`). The memory is a window buffer that saves every run of the
model, and the checks come after the run, so the retry sees the rejected pass in memory as
its last exchange (that is what the note's "your previous answer" points at), and the turns
after it see both passes. It sees none of the first pass's tool results: it may call tools
again, and each returns the same fixture. A second open_request for the same building and
type returns the first ticket's reference with `duplicate: true`, as the ticket service's
30-minute duplicate guard does; the resident hears the same number again.
Play it, then call the helper with `run_index: 1`, `retry_note`, its `tool_calls` and its
`output`, plus `first_try` (the `retry.try_item` the first call printed: since 5 Oct the
second pass's checks count the first pass's tools from it) and `recent` (the chat's last
twelve messages, oldest first: a ticket number from earlier in the chat is real only if
it is there). If it passes, its handset is what the resident gets. If it is rejected too,
since 5 Oct no model writes again: the helper prints `mend` (Claimed a ticket? and Mend
the reply: whether a rescue ticket was opened, and the text that goes out) and `handset`.
Record `mend_output`. On a code.json from before 5 Oct, production went to `Say it again`,
a small model of its own: the helper prints its system prompt and its input
(`say_again`); play it and record its text as `say_again_output`.
A retried turn keeps the first pass as `first_tool_calls`, `first_output`, `first_failed`
and `retry_note`, and the retry as the usual `tool_calls` and `output`.

## Output

Write ONE file, `transcripts/<scenario>_<variant>.json` in the run directory, valid JSON:

```json
{"scenario": "gate_lock", "variant": "A", "turns": [
  {"resident": "היי, המנעול של השער שבור שוב", "kind": "text",
   "input": "[זו ההודעה הראשונה בשיחה.] [השעה בישראל עכשיו 16:09, יום חמישי.]\\nהיי, המנעול של השער שבור שוב",
   "ack": "NONE",
   "tool_calls": [{"name": "open_request", "arguments": {"description": "...", "type": "locksmith",
                   "building": "בר כוכבא 23", "reporter_unit": "4", "fault_location": "common",
                   "urgency": "normal"}, "result": {"ok": true, "opened": true, "reference": "255-1402-26"}}],
   "output": "the model's reply text"},
  {"resident": "שלום", "kind": "menu"}
]}
```

`kind` is `text`, `tap`, `photo`, `file` or `menu`. For a tap, `resident` is the button title.
For a photo with no caption, and for a file, `resident` is `""`; a captioned photo keeps its
caption there. `ack` is the ack model's exact output (`NONE` or the ack).
`tool_calls` is in the order called; `result` is the fixture you used. `output` is the
answering model's final text, exactly, newlines as `\\n`. A free resident's conversation
also carries English for the owner, who does not read Hebrew, on every turn: `resident_en`,
`output_en`, `ack_en` when an ack went out, `first_output_en` for a rejected pass and
`say_again_en`. A gloss is a faithful translation, not a summary: the tone, the questions,
the typos' sense and anything awkward stay exactly as they are. Nothing else in the file.
"""


def bundle(run, variants, candidate=None):
    # --candidate F: a patcher's --dump, laid over live the way the gate does it,
    # so the same transcripts can be graded through a would-be workflow's code.
    wf = C.load_candidate([candidate]) if candidate else C.load_live()
    code = extract_code(wf)
    texts = model_texts(wf)
    tools = tools_of(wf)
    deck = load_json(DECK)
    os.makedirs(run, exist_ok=True)
    write(os.path.join(run, "code.json"), json.dumps(code, ensure_ascii=False, indent=1))
    write(os.path.join(run, "PLAYER.md"), PLAYER)
    write(os.path.join(run, "context_A.md"), context_md("A", texts, tools))
    labels = ["A"]
    for label, spec in variants:
        t2, tl2 = apply_variant(texts, tools, spec)
        write(os.path.join(run, "context_%s.md" % label), context_md(label, t2, tl2))
        labels.append(label)
    # The deck the players see: no expectations, bare hellos marked by Sort's own test.
    texts_to_test = []
    for s in deck["scenarios"]:
        for line in s["resident"]["script"]:
            if "say" in line and not line.get("if_asked") and line.get("kind", "text") == "text":
                texts_to_test.append(line["say"])
    flags = node_run({"mode": "sort", "code": code, "texts": texts_to_test})
    menu = dict(zip(texts_to_test, flags))
    player_deck = []
    for s in deck["scenarios"]:
        # The players never see what is checked: not the expectations, and not
        # the judges' questions either (1 Oct: they named the gender check).
        d = {k: v for k, v in s.items() if k not in ("expect", "judge")}
        d["resident"] = dict(s["resident"])
        d["resident"]["script"] = []
        for line in s["resident"]["script"]:
            l2 = dict(line)
            if "say" in l2 and not l2.get("if_asked") and l2.get("kind", "text") == "text" and menu.get(l2["say"]):
                l2["menu"] = True
            d["resident"]["script"].append(l2)
        d["clock"] = {"time": s["time"], "weekday": s["weekday"], "weekday_he": s["weekday_he"],
                      "hour_word": hour_word(s["time"])}
        player_deck.append(d)
    out = {"variants": labels, "scenarios": player_deck}
    if deck.get("defaults"):
        out["defaults"] = deck["defaults"]  # what a tool returns when a scenario has no fixture for it
    write(os.path.join(run, "deck.json"), json.dumps(out, ensure_ascii=False, indent=1))
    os.makedirs(os.path.join(run, "transcripts"), exist_ok=True)
    print("bundled %d scenarios x %s into %s" % (len(player_deck), "/".join(labels), run))
    print("prompt A: %d chars, sha %s" % (len(texts["system"]), C.fingerprint(texts["system"])))
    for label, spec in variants:
        t2, _ = apply_variant(texts, tools, spec)
        print("prompt %s: %d chars, sha %s" % (label, len(t2["system"]), C.fingerprint(t2["system"])))
    print("menu lines: %s" % ", ".join(repr(t) for t, f in menu.items() if f))


# ---------------------------------------------------------------------------
# turn: one message through the live code, for a player mid-conversation
# ---------------------------------------------------------------------------
def turn(run):
    """A free resident's message is not known before the game, so the player
    asks the live code about each one as it is written (see PLAYER.md)."""
    code = load_json(os.path.join(run, "code.json"))
    deck = load_json(os.path.join(run, "deck.json"))
    t = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    s = next((x for x in deck["scenarios"] if x["id"] == t.get("scenario")), None)
    if not s:
        sys.exit("turn: no scenario %r in %s" % (t.get("scenario"), run))
    print(json.dumps(live_turn(code, s, t), ensure_ascii=False, indent=1))


def live_turn(code, s, t):
    """What the live code does with one message (turn's body; play calls it too)."""
    kind = t.get("kind", "text")
    text = "" if kind == "file" else str(t.get("text") or "")
    menu_line = hour_word(s["time"]) + " 👋 במה אפשר לעזור?"
    if kind == "text" and node_run({"mode": "sort", "code": code, "texts": [text]})[0]:
        return {"menu": True, "system_sends": menu_line, "buttons": list(TAPS.values()),
                "record": {"resident": text, "kind": "menu"}}
    tap = kind == "tap"
    clock = {"time": s["time"], "weekday": s["weekday"], "iso": s["iso"]}
    base = {"text": text, "greeted": not t.get("first"), "last_bot": menu_line if t.get("after_menu") else "",
            "tap_now": tap, "tap": {v: k for k, v in TAPS.items()}.get(text, "") if tap else "",
            "photo": kind == "photo", "attachment": kind in ("photo", "file"),
            "ack": t.get("ack") or "NONE", "tool_calls": t.get("tool_calls") or [],
            "output": t.get("output") or "", "retry_note": t.get("retry_note") or "",
            "run_index": int(t.get("run_index") or 0),
            # 5 Oct: the truth guards read the chat's last twelve messages (a ticket
            # number from earlier is real only if it is there) and, on the second
            # pass, Try again's item.
            "recent": t.get("recent") or [], "first_try": t.get("first_try")}
    if base["run_index"]:
        # Try again rebuilds its item from `Still the last word?`, which never
        # carried the ack (Carry on adds it), so the retry reads no ack note.
        r = node_run({"mode": "turns", "code": code, "clock": clock, "turns": [dict(base, ack="NONE")]})[0]
        r0 = node_run({"mode": "turns", "code": code, "clock": clock, "turns": [base]})[0]
        if r0.get("ack_sent") and r.get("handset") is not None:
            r["handset"] = [r0["ack_text"]] + r["handset"]
        r["ack_sent"], r["ack_text"] = r0.get("ack_sent"), r0.get("ack_text", "")
    else:
        r = node_run({"mode": "turns", "code": code, "clock": clock, "turns": [base]})[0]
    if "error" in r:
        sys.exit("turn: the live code threw: " + r["error"])
    out = {"menu": False, "ack_model_reads": r["worth_input"], "ack_goes_out": r["ack_sent"]}
    if r["ack_sent"]:
        out["ack_text"] = r["ack_text"]
    out["answering_model_reads"] = r["inject"]
    if base["output"]:
        out["guards_failed"] = r["failed"]
        if not r["failed"]:
            out["handset"] = [h for h in r["handset"] if h]
            out["buttons"] = bool(r.get("buttons"))
        elif base["run_index"] == 0:
            again = node_run({"mode": "turns", "code": code, "clock": clock,
                              "turns": [dict(base, ack="NONE", output="", tool_calls=[], retry_note=r["retry_note"])]})[0]
            out["retry"] = {"note": r["retry_note"], "answering_model_reads": again["inject"],
                            "try_item": r.get("try_item")}
        elif code.get("mend"):
            # 5 Oct: no model. Claimed a ticket? decides the rescue ticket (the
            # ticket service mints a stub: simulated), Mend the reply writes what
            # goes out, Send sends it.
            m = node_run({"mode": "mend", "code": code, "text": text, "output": base["output"],
                          "tool_calls": base["tool_calls"], "recent": base["recent"],
                          "first_try": base["first_try"],
                          "rescue": {"ok": True, "reference": "255-1599-26", "rescued": True}})
            out["mend"] = m
            out["handset"] = ([r["ack_text"]] if r.get("ack_sent") else []) + ([m["sent"]] if m.get("sent") else [])
            out["buttons"] = False
        else:
            # Open it anyway reads verify_address's `building`; with none, the
            # rescue opens nothing and Say it again gets no reference.
            built = [c for c in base["tool_calls"] if c.get("name") == "verify_address"
                     and (c.get("result") or {}).get("building")]
            rescue = ({"ok": True, "request_opened": True, "reference": "255-1599-26"} if built
                      else {"ok": True, "request_opened": False})
            sa = node_run({"mode": "say_again", "code": code, "text": text, "draft": base["output"],
                           "rescue": rescue, "output": t.get("say_again_output") or ""})
            out["say_again"] = {"rescue": rescue, "system": code.get("say_again_system", ""), "reads": sa["reads"]}
            if t.get("say_again_output"):
                out["say_again"]["failed"] = sa["failed"]
                out["say_again"]["sent"] = sa.get("sent", "")
                if r["ack_sent"]:
                    out["say_again"]["ack_went_first"] = r["ack_text"]
    return out


# ---------------------------------------------------------------------------
# grade: the rubric, over what the handset would get
# ---------------------------------------------------------------------------
SLANG = re.compile(r"באסה|מבאס|סבבה|אחלה|וואלה|יאללה|כאילו|פדיחה|מגניב|פצצה|חבל על הזמן|סחתיין|"
                   r"מטורף|הזוי|נו באמת|יא אללה|כפרה|(^|\s)(אחי|גבר|קטע)(?=[\s,.!?]|$)")
SOON = re.compile(r"בהקדם|בקרוב|בימים הקרובים|בשעות הקרובות|יחזרו אלי|יחזור אלי|תחזור אלי|יצרו קשר|"
                  r"ייצור קשר|יצור קשר|ניצור קשר|נחזור אלי|אחזור אלי|בדרך אלי|עוד היום|עד מחר|"
                  r"תוך (כמה|מספר|\d)|יגיע (אלי|בקרוב|היום|מחר)|ממש בקרוב|בהמשך היום|יטפלו? בזה (מהר|בהקדם)")
HANDLING = re.compile(r"אל דאגה|אל תדאגו|אל תדאג(?=[\s,.!?]|$)|אני (כבר )?מטפל בזה|אני אטפל|נטפל בזה|"
                      r"אנחנו על זה|אני על זה|אני אדאג|נדאג ש")
ECHO = re.compile(r"(^|[.!?,:]\s*)(אני מבין|אני מבינה|הבנתי|שמעתי)\s+ש|אני מבין (אתכם|אותך|אותכם)|"
                  r"הבנתי אתכם|הבנתי אותך|מבין את (התסכול|הכעס|המצב)")
CLERK = re.compile(r"כדי ש(אוכל|נוכל|אפתח|נפתח|אבדוק|נבדוק|אעזור|נעזור|אמצא|נמצא)|אצטרך|נצטרך|"
                   r"בשביל ש|על מנת|אני צריך (ממכם|מכם|ממך|לדעת)")
# 1 Oct evening: the bot writes to one person -- masculine until she writes about
# herself in the feminine, then feminine. The "you" regexes live in
# check_whatsapp_rules.py (PLURAL_YOU, MASC_YOU, FEM_YOU, FEM_CUE), one copy for
# the rubric and --watch. The old SINGULAR flag enforced the plural rule.
SLASH = re.compile(r"([א-ת]{2,})[א-ת]?(/|\()(\1[א-ת]?)?(י|ה|ת|נה|ו|ות)\)?(?=[\s,.!?:;)]|$)")
MARKDOWN = re.compile(r"\*\*|(^|\n)\s*[-•*] |(^|\n)\s*\d+\. |(^|\n)#{1,3} ")
PARENS = re.compile(r"[()]")
LINK = re.compile(r"https?://\S+")
LATIN = re.compile(r"[A-Za-z]{2,}")
EMERGENCY = re.compile(r"(^|\D)(100|101|102|103)(\D|$)|משטרה|מכבי אש|מד\"א|מדא(?=[\s,.!?]|$)|כבאות|מגן דוד")
OFFICE = re.compile(r"077-?6687949|homies-management|בצלאל 1")
GREET = re.compile(r"^(שלום רב|שלום|היי|הי|אהלן|בוקר טוב|צהריים טובים|ערב טוב|לילה טוב|שבוע טוב|שבת שלום|חג שמח|יום טוב)"
                   r"( לכם| לך| לכולם)?(?=[\s,.!:;]|$)")
HOUR_WORDS = ("בוקר טוב", "צהריים טובים", "ערב טוב")
TICKET_CLAIM = re.compile(r"פתחתי|פתחנו|נפתחה (לכם |לך |עכשיו )?ה?קריאה|פותח (לכם|לך)|נרשמה קריאה|רשמתי קריאה")
TEAM_CLAIM = re.compile(r"הצוות (שלנו )?(כבר )?(יודע|מעודכן|קיבל|ראה|יראה|מטפל)|העברתי|עדכנתי את הצוות|"
                        r"רשמתי (את זה )?לצוות|מסרתי לצוות|הודעתי לצוות|נרשם לצוות|הצוות (שלנו )?(יחזור|יצור)")
REASK = re.compile(r"במה (אפשר|אוכל|נוכל|אני יכול) לעזור(?! (עוד|בעוד|לכם עוד|לך עוד))|איך (אפשר|אוכל|אני יכול) לעזור(?! (עוד|בעוד))")
HOW_ARE_YOU = re.compile(r"מה נשמע|מה קורה|איך הולך|מה שלומ|how are you|how is it going|how's it going|whats up|what's up|wassup", re.I)
# 1 Oct evening: the bot asks it itself on the representative tap
# (n8n_whatsapp_rephello.py), so its own forms count too.
# 4 Oct: one copy, the `rephay` guard's (n8n_whatsapp_retry.HAY_ALT).
BOT_HAY = R.HAY_PY


def emojis(s):
    out = []
    for ch in s:
        o = ord(ch)
        if 0x1F000 <= o <= 0x1FAFF or 0x2600 <= o <= 0x27BF or o in (0x2B50, 0x2B55, 0x203C, 0x2049):
            out.append(ch)
    return out


def rubric(turn, res, ctx):
    """Flags for one model turn. `res` is wa_qa.js's result; `ctx` carries the
    conversation state: first (bool), after_menu, tap, resident text, scenario."""
    flags = []
    s = ctx["scenario"]
    emergency = bool(s.get("emergency"))
    out = turn.get("output") or ""
    calls = turn.get("tool_calls") or []
    names = [c["name"] for c in calls]
    handset = [h for h in res["handset"] if h]
    joined = "\n".join(handset)
    quote = lambda m, t: C.mask(t[max(0, m.start() - 25):m.end() + 25])

    def flag(rule, text, m=None):
        flags.append({"rule": rule, "quote": quote(m, text) if m else C.mask(text)})

    # The guards (the first pass).
    for g in res["failed"]:
        flag("guard:" + g, out)

    # Every message the handset gets.
    for i, h in enumerate(handset):
        is_ack = res["ack_sent"] and i == 0
        is_first_part = res["two"] and (i == (1 if res["ack_sent"] else 0))
        for rule, rx in (("slang", SLANG), ("soon-promise", SOON), ("echo", ECHO), ("explains-why", CLERK),
                         ("markdown", MARKDOWN), ("parentheses", PARENS), ("emergency-numbers", EMERGENCY)):
            m = rx.search(h)
            if m:
                # The payment ack's own "I understood that..." is what its prompt
                # asks for; a known gap (HANDOVER), the same in every variant.
                flag("echo-in-ack(known)" if rule == "echo" and is_ack else rule, h, m)
        m = HANDLING.search(h)
        if m and not (is_ack or is_first_part):
            flag("handling-promise", h, m)
        m = C.PLURAL_YOU.search(h)
        if m:
            flag("plural-you", h, m)
        if ctx["she"]:
            m = C.MASC_YOU.search(h)
            if m:
                flag("masculine-after-she-wrote-feminine", h, m)
        else:
            m = C.FEM_YOU.search(h)
            if m:
                flag("feminine-without-cue", h, m)
        m = SLASH.search(h)
        if m:
            flag("slash-form", h, m)
        m = OFFICE.search(h)
        if m and not s.get("office_allowed"):
            flag("office-unasked", h, m)
        no_links = LINK.sub("", h)
        m = LATIN.search(no_links)
        if m and not s.get("latin_allowed"):
            flag("not-hebrew", h, m)
        em = emojis(h)
        if em and emergency:
            flag("emoji-in-emergency", h)
        if len(em) > 1:
            flag("two-emoji", h)
        if any(e not in ALLOWED_EMOJI for e in em):
            flag("emoji-off-list", h)
        rep = ctx.get("tap_kind") == "other"
        # 4 Oct: the rep tap asks one question now too (how he is), so no exemption.
        if h.count("?") >= 2:
            flag("two-questions", h)
        if len(h.split()) > 70:
            flag("long", h)
        # Greetings and the name.
        g = GREET.match(h.lstrip("".join(emojis(h)) + " "))
        if g and not is_ack:
            word = g.group(1)
            if word in HOUR_WORDS and word != ctx["hour_word"]:
                flag("hour-slip", h, g)
            if rep:
                if word in HOUR_WORDS:
                    flag("rep-hello-repeats-menu", h, g)
            elif ctx["after_menu"] or ctx["tap"]:
                flag("greeting-after-menu", h, g)
            elif not ctx["first"] and not ctx["they_greeted"]:
                flag("greeting-mid-conversation", h, g)
        if len(GREET.findall(h)) > 1:
            flag("two-greetings", h)
        if rep and i == 0:
            if not g:
                flag("rep-no-hello", h)
            if not BOT_HAY.search(h):
                flag("rep-no-how-are-you", h)
            if REASK.search(h):
                flag("rep-asks-how-to-help", h)
        elif BOT_HAY.search(h) and any(BOT_HAY.search(p) for p in ctx["prev_handsets"]):
            flag("how-are-you-again", h)
        if "מיכאל" in h:
            if not (ctx["first"] or ctx["after_menu"] or ctx["tap"] or ctx["asked_who"]):
                flag("name-mid-conversation", h)
        if ctx["first"] and not ctx["after_menu"] and not ctx["tap"] and i == len(handset) - 1 and not res["ack_sent"]:
            whole = joined
            if not GREET.match(whole):
                flag("first-message-no-greeting", whole)
            if "מיכאל" not in whole:
                flag("first-message-no-name", whole)
        if (ctx["after_menu"] or ctx["tap"]) and ctx["first_contact"] and "מיכאל" not in joined:
            flag("after-menu-no-name", joined)
        m = REASK.search(h)
        if m and ctx["has_matter"] and not is_ack:
            flag("reasks-how-to-help", h, m)
        # Links.
        for u in LINK.findall(h):
            u2 = u.rstrip(".,;:!?)")
            lines = [x.strip() for x in h.split("\n")]
            if u2 not in lines:
                flag("link-not-on-own-line", h)
            if "get_payment_link" not in names:
                flag("link-without-tool", h)
            else:
                fx = next((c.get("result") or {} for c in calls if c["name"] == "get_payment_link"), {})
                if fx.get("link") and fx["link"] != u2:
                    flag("link-changed", h)
            if h.rstrip().endswith("?"):
                flag("link-message-ends-with-question", h)
            if not re.search(r"אישי|רק לדירה|לדירה שלכם|לדירה שלך|לא להעביר|לא מעבירים|אל תעבירו", h):
                flag("link-not-marked-personal", h)
            if re.search(r"(תכתבו|כתבו|תפנו|פנו|תכתוב|כתוב|תכתבי|כתבי|תפנה|פנה|תפני|פני) (אלינו|לנו)", h):
                flag("link-write-to-us", h)
    # Claims against the tools of this turn. A ticket opened EARLIER in the
    # conversation may be referred back to by its number (the live deeds guard
    # does not allow that: see the 1 Oct report).
    if TICKET_CLAIM.search(joined):
        ok = any(c["name"] == "open_request" and (c.get("result") or {}).get("reference") for c in calls)
        earlier = any(ref and ref in joined for ref in ctx["refs_so_far"])
        if not ok and not earlier:
            flag("ticket-claim-without-tool", joined, TICKET_CLAIM.search(joined))
    if TEAM_CLAIM.search(joined):
        if "notify_team" not in names and "notify_team" not in ctx["tools_so_far"]:
            flag("team-claim-without-tool", joined, TEAM_CLAIM.search(joined))
    if "§§§" in out and ("get_payment_link" not in names or res["ack_sent"]):
        flag("two-parts-outside-payment", out)
    if ctx["closing"]:
        if joined.rstrip().endswith("?") or "?" in handset[-1]:
            flag("question-after-goodbye", handset[-1])
    elif not res["two"] and not any(LINK.search(h) for h in handset) and not joined.rstrip().endswith("?") \
            and not res["ack_sent"]:
        flags.append({"rule": "info:no-question-at-end", "quote": C.mask(handset[-1] if handset else "")})
    if ctx["prev_handsets"] and joined.strip() in ctx["prev_handsets"]:
        flag("repeated-message", joined)
    return flags


def expectations(scen, turns, results):
    """The scenario's own checks, over the whole conversation."""
    out = []
    calls = []          # (turn index, name, arguments, result)
    bot_msgs = []       # (turn index, text)
    for i, (t, r) in enumerate(zip(turns, results)):
        if t.get("kind") == "menu":
            continue            # the system's own line, not the model's
        for c in (t.get("first_tool_calls") or []) + (t.get("tool_calls") or []):
            calls.append((i, c["name"], c.get("arguments") or {}, c.get("result") or {}))
        for h in (r.get("handset") or []):
            if h:
                bot_msgs.append((i, h))
    first_call = {}
    for i, n, _, _ in calls:
        first_call.setdefault(n, i)
    for e in scen.get("expect", []):
        typ = e["type"]
        name = e.get("name") or typ
        ok = None
        if typ == "called":
            ok = any(n == e["tool"] for _, n, _, _ in calls)
        elif typ == "not_called":
            ok = not any(n == e["tool"] for _, n, _, _ in calls)
        elif typ == "called_on_turn":
            ok = any(n == e["tool"] and i == e["turn"] for i, n, _, _ in calls)
        elif typ in ("arg_contains", "arg_not_contains", "arg_equals"):
            vals = [str(a.get(e["arg"], "")) for _, n, a, _ in calls if n == e["tool"]]
            if not vals:
                ok = None if typ != "arg_not_contains" else True
            elif typ == "arg_contains":
                ok = all(any(w in v for w in e["words"]) for v in vals)
            elif typ == "arg_not_contains":
                ok = not any(any(w in v for w in e["words"]) for v in vals)
            else:
                ok = all(v == e["value"] for v in vals)
        elif typ == "asks_before":
            limit = first_call.get(e["tool"], len(turns))
            ok = any(re.search(e["regex"], h) for i, h in bot_msgs if i < limit)
        elif typ == "bot_regex":
            ok = any(re.search(e["regex"], h) for _, h in bot_msgs)
        elif typ == "bot_not_regex":
            ok = not any(re.search(e["regex"], h) for _, h in bot_msgs)
        elif typ in ("turn_regex", "turn_not_regex"):
            msgs = [h for i, h in bot_msgs if i == e["turn"]]
            hit = any(re.search(e["regex"], h) for h in msgs)
            ok = bool(msgs) and (hit if typ == "turn_regex" else not hit)
        elif typ == "turn_questions_max":
            msgs = [h for i, h in bot_msgs if i == e["turn"]]
            ok = bool(msgs) and sum(h.count("?") for h in msgs) <= e["max"]
        elif typ == "last_no_question":
            ok = bool(bot_msgs) and "?" not in bot_msgs[-1][1]
        elif typ == "turn_count_max":
            ok = len(turns) <= e["max"]
        out.append({"name": name, "ok": ok, "pending": e.get("pending", False)})
    return out


def grade(run):
    code = load_json(os.path.join(run, "code.json"))
    deck = load_json(DECK)
    scen_by = {s["id"]: s for s in deck["scenarios"]}
    tdir = os.path.join(run, "transcripts")
    files = sorted(f for f in os.listdir(tdir) if f.endswith(".json"))
    results = {}
    for f in files:
        tr = load_json(os.path.join(tdir, f))
        s = scen_by.get(tr["scenario"])
        if not s:
            print("skip %s: unknown scenario" % f)
            continue
        clock = {"time": s["time"], "weekday": s["weekday"], "iso": s["iso"]}
        hist = s.get("history") or []
        greeted = bool(hist)
        last_bot = ""
        turns_js, meta = [], []
        tools_so_far = set(t for h in hist for t in (h.get("tools") or []))
        refs_so_far = set(re.findall(r"\d{3}-\d{3,6}-\d{2}", " ".join(h.get("michael", "") for h in hist)))
        prev_handsets = set()
        first_contact = not hist
        # she wrote about herself in the feminine, in history or by this turn
        she = any(C.FEM_CUE.search(h.get("resident", "")) for h in hist)
        for i, t in enumerate(tr["turns"]):
            kind = t.get("kind", "text")
            text = t.get("resident", "")
            she = she or bool(C.FEM_CUE.search(text))
            if kind == "menu":
                last_bot = hour_word(s["time"]) + " 👋 במה אפשר לעזור?"
                greeted = True
                meta.append({"kind": "menu", "handset": [last_bot], "buttons": True})
                turns_js.append(None)
                continue
            tap = kind == "tap"
            ctx = {"scenario": s, "first": not greeted, "after_menu": bool(last_bot), "tap": tap,
                   "tap_kind": {v: k for k, v in TAPS.items()}.get(text, "") if tap else "",
                   "first_contact": first_contact, "hour_word": hour_word(s["time"]),
                   "they_greeted": bool(re.match(r"^[\s\W]*(שלום|היי|הי|אהלן|בוקר טוב|צהריים טובים|ערב טוב|hi|hey|hello|good (morning|afternoon|evening)|shalom|ahlan)(?=[\s,.!?:;]|$)", text, re.I)),
                   "asked_who": bool(re.search(r"מי (אתה|את|זה|מדבר|כותב|עונה)|עם מי|who (are|r) (you|u)|who is this|bot|רובוט|בוט", text, re.I)),
                   "has_matter": kind != "tap" and len(text.split()) >= 3 and not HOW_ARE_YOU.search(text),
                   "closing": bool(t.get("closing")) or bool(re.match(r"^\s*(תודה|תודה רבה|אוקיי תודה|ok thanks|thanks|thank you|לילה טוב|יום טוב|ביי|להתראות)", text, re.I)),
                   "tools_so_far": set(tools_so_far), "prev_handsets": set(prev_handsets),
                   "refs_so_far": set(refs_so_far), "she": she}
            turns_js.append({"text": text, "greeted": greeted, "last_bot": last_bot, "tap_now": tap,
                             "tap": {v: k for k, v in TAPS.items()}.get(text, "") if tap else "",
                             # A file (a voice note, a location) is an attachment
                             # Sort does not keep: the inject's other note (4 Oct).
                             "photo": kind == "photo", "attachment": kind in ("photo", "file"),
                             "ack": t.get("ack", "NONE"), "tool_calls": t.get("tool_calls") or [],
                             # A turn Try again rewrote is graded on the pass that went
                             # out (Say it again's text, when both were rejected).
                             "output": t.get("say_again_output") or t.get("output", ""),
                             "run_index": 1 if "first_output" in t else 0,
                             "retry_note": t.get("retry_note", "")})
            meta.append(ctx)
            greeted = True
            last_bot = ""
            first_contact = False
            # A rejected pass's tools ran too: its ticket is as real as the retry's.
            done = (t.get("first_tool_calls") or []) + (t.get("tool_calls") or [])
            tools_so_far.update(c["name"] for c in done)
            refs_so_far.update(str((c.get("result") or {}).get("reference") or "") for c in done)
        js_out = node_run({"mode": "turns", "code": code, "clock": clock,
                           "turns": [x for x in turns_js if x is not None]})
        it = iter(js_out)
        full = []
        for i, t in enumerate(tr["turns"]):
            if turns_js[i] is None:
                full.append(meta[i])
                continue
            r = next(it)
            if "error" in r:
                full.append({"error": r["error"], "handset": [], "failed": [], "flags": [{"rule": "harness-error", "quote": r["error"]}]})
                continue
            r["flags"] = rubric(t, r, meta[i])
            for k in ("first_output", "first_failed", "first_tool_calls", "retry_note", "say_again_output"):
                if k in t:
                    r[k] = t[k]
            full.append(r)
            # later turns see this one
            for m in meta[i + 1:]:
                if isinstance(m, dict) and "prev_handsets" in m:
                    m["prev_handsets"].add("\n".join(h for h in r["handset"] if h).strip())
        exp = expectations(s, tr["turns"], [x if "handset" in x else {"handset": []} for x in full])
        key = "%s_%s" % (tr["scenario"], tr["variant"])
        results[key] = {"scenario": tr["scenario"], "variant": tr["variant"], "turns": full, "expect": exp,
                        "transcript": tr["turns"]}
        write(os.path.join(run, "graded", key + ".json"), json.dumps(results[key], ensure_ascii=False, indent=1))
    write(os.path.join(run, "results.json"), json.dumps(results, ensure_ascii=False, indent=1))
    summary(results)
    return results


def summary(results):
    by_var = {}
    for key, r in results.items():
        v = r["variant"]
        d = by_var.setdefault(v, {"conv": 0, "turns": 0, "flags": {}, "exp_ok": 0, "exp_fail": 0, "exp_na": 0, "guard": 0})
        d["conv"] += 1
        for t in r["turns"]:
            if "flags" not in t:
                continue
            d["turns"] += 1
            for f in t["flags"]:
                d["flags"][f["rule"]] = d["flags"].get(f["rule"], 0) + 1
            d["guard"] += 1 if t.get("failed") else 0
        for e in r["expect"]:
            if e["ok"] is True:
                d["exp_ok"] += 1
            elif e["ok"] is False:
                d["exp_fail"] += 1
            else:
                d["exp_na"] += 1
    print("")
    print("%-8s %5s %6s %7s %9s %10s" % ("variant", "convs", "turns", "guarded", "expect ok", "expect fail"))
    for v in sorted(by_var):
        d = by_var[v]
        print("%-8s %5d %6d %7d %9d %10d" % (v, d["conv"], d["turns"], d["guard"], d["exp_ok"], d["exp_fail"]))
    rules = sorted(set(k for d in by_var.values() for k in d["flags"]))
    if rules:
        print("")
        print("%-34s" % "flag" + "".join("%6s" % v for v in sorted(by_var)))
        for k in rules:
            print("%-34s" % k + "".join("%6d" % by_var[v]["flags"].get(k, 0) for v in sorted(by_var)))
    print("")
    for key in sorted(results):
        r = results[key]
        bad = [e["name"] for e in r["expect"] if e["ok"] is False]
        fl = [f["rule"] for t in r["turns"] for f in t.get("flags", []) if not f["rule"].startswith("info:")]
        print("%-30s flags: %-3d %s%s" % (key, len(fl), ", ".join(sorted(set(fl)))[:90],
                                           ("  | FAILED: " + ", ".join(bad)) if bad else ""))


# ---------------------------------------------------------------------------
# judge: blind packets
# ---------------------------------------------------------------------------
JUDGE_RULES = """The owner's standing rules for the WhatsApp bot (grade against these, and against the
scenario's own checks). Michael writes Hebrew only, like a nice person on WhatsApp: short, warm,
polite, no slang (באסה, מבאס, סבבה, וואלה, אחלה are slang). One question per message; the building
and the apartment count as one question and are asked only when a ticket is clearly being opened,
never in the same message as "what happened". A short human word about the thing itself comes
before the question, never a summary of what they wrote and never "I understand that...". A missing
detail is asked for plainly, with no explanation of why it is needed. Nothing is promised: not who,
not when, not "soon", not "don't worry, I'm on it"; a ticket is reported as opened with its number
and nothing more. A claim that the team knows is true only if notify_team was called. The ticket's
description holds the resident's own words and nothing they did not write (no guessed gate, floor or
cause). A fault inside the flat is theirs: said gently, no ticket, no explanation of the rule, no
recommendation of a tradesman, then an offer to help with something else. A person in danger: the
team note first, no safety advice, no emergency numbers, no "help is on the way", no emoji. Emoji:
at most one per message, roughly two messages in five, only 🙂 😊 🙏 👍 💪 🤝. One person is
addressed in the singular, never the plural (אתם, שלכם, תרצו): masculine (אתה, תוכל) until the
resident writes about herself in the feminine (אני צריכה, אני גרה), then feminine (את, תוכלי) to the
end, with no remark about it; words that fit both (לך, שלך) are always fine; never a slash form
(ספר/י). The first message of a conversation
opens with the greeting for the hour (before 12 בוקר טוב, before 17 צהריים טובים, then ערב טוב) and
gives the name once; after the system's menu, or a tap on one of the first two buttons, there is no
greeting and the name is given. The one exception is the third button, לדבר עם נציג: Michael
answers it like a representative joining the chat, in one short message: "היי" (not the hour's
greeting, which the menu already gave), his name, and a how-are-you as the one question (4 Oct);
how he can help is asked after the resident answers, with a word about the answer, and the
how-are-you is not asked again. Mid-conversation there is
no name and no greeting unless the resident greeted first (then one back). Someone who already said what they need is not asked "how can I help" again. A finished
matter ends with an offer to help with anything else; the one exception is the message that carries
a payment link, which closes by saying the link is personal and to write here if anything is
unclear, with no further question. A thank-you or goodbye gets a warm goodbye with no question.
Only Homies matters are answered; nothing about another resident. No markdown, no parentheses.
"""


def judge(run):
    results = load_json(os.path.join(run, "results.json"))
    deck = load_json(DECK)
    jdir = os.path.join(run, "judge")
    os.makedirs(jdir, exist_ok=True)
    rnd = random.Random(20261001)
    key = {}
    for s in deck["scenarios"]:
        rows = [r for r in results.values() if r["scenario"] == s["id"]]
        if not rows:
            continue
        labels = ["X", "Y", "Z", "W"][:len(rows)]
        rnd.shuffle(rows)
        key[s["id"]] = {lab: r["variant"] for lab, r in zip(labels, rows)}
        lines = ["# Judge packet: %s" % s["id"], "", "Scenario: %s" % s["title"],
                 "Israel time %s, %s. The resident: %s" % (s["time"], s["weekday_he"], s["resident"]["persona"]), "",
                 "## Rules", "", JUDGE_RULES, "",
                 "## This scenario's checks", ""]
        for chk in s.get("judge", []):
            lines.append("- " + chk)
        lines += ["", "## The conversations (what the handset gets; tool calls shown in brackets)", ""]
        for lab, r in zip(labels, rows):
            lines += ["### %s" % lab, ""]
            for t, g in zip(r["transcript"], r["turns"]):
                if t.get("kind") == "menu":
                    lines.append("- resident: %s" % t["resident"])
                    lines.append("- system (fixed menu, with buttons): %s" % g["handset"][0])
                    continue
                who = {"tap": "tap", "file": "a file or voice note, no text"}.get(t.get("kind"), "resident")
                if t.get("kind") == "photo":
                    who = "photo with caption" if t.get("resident") else "photo, no caption"
                lines.append("- %s: %s" % (who, t.get("resident") or ""))
                for c in (t.get("tool_calls") or []):
                    args = json.dumps(c.get("arguments") or {}, ensure_ascii=False)
                    lines.append("  - [tool %s %s] -> %s" % (c["name"], args, json.dumps(c.get("result") or {}, ensure_ascii=False)[:160]))
                for h in g.get("handset", []):
                    if h:
                        lines.append("- Michael: %s" % h.replace("\n", " / "))
                if g.get("failed"):
                    lines.append("  - (a guard rejected this reply first: %s; production would ask the model to rewrite it)" % ", ".join(g["failed"]))
            lines.append("")
        lines += ["## Your output", "",
                  "Write `%s.verdict.json` beside this file, valid JSON only:" % s["id"], "",
                  "```json", json.dumps({"scenario": s["id"], "variants": {lab: {"checks": {"<each check, short key>": True},
                                        "violations": [{"rule": "<rule>", "quote": "<the words>"}], "notes": "<one line>"} for lab in labels},
                                        "ranking": labels, "reason": "<one line: why this order>"}, ensure_ascii=False, indent=1), "```", "",
                  "Judge each conversation on its own against the rules and the checks, quote the exact words for every",
                  "violation, then rank the conversations best first (ties allowed: same position, say so in reason).",
                  "Be strict and literal; do not guess at intent; a check not reached in the conversation is null."]
        write(os.path.join(jdir, s["id"] + ".md"), "\n".join(lines))
    write(os.path.join(jdir, "key.json"), json.dumps(key, ensure_ascii=False, indent=1))
    print("wrote %d judge packets to %s (key.json maps labels to variants; judges must not read it)" % (len(key), jdir))


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def report(run):
    results = load_json(os.path.join(run, "results.json"))
    deck = load_json(DECK)
    jdir = os.path.join(run, "judge")
    key = load_json(os.path.join(jdir, "key.json")) if os.path.exists(os.path.join(jdir, "key.json")) else {}
    verdicts = {}
    for sid, mapping in key.items():
        p = os.path.join(jdir, sid + ".verdict.json")
        if os.path.exists(p):
            v = load_json(p)
            verdicts[sid] = {"by_variant": {mapping[lab]: v["variants"].get(lab, {}) for lab in mapping},
                             "ranking": [mapping[lab] for lab in v.get("ranking", []) if lab in mapping],
                             "reason": v.get("reason", "")}
    variants = sorted(set(r["variant"] for r in results.values()))
    L = ["# WhatsApp bot QA, %s: Claude-played A/B/C on the live code" % os.path.basename(run.rstrip("/\\")), ""]
    # Totals.
    L += ["## Totals", "", "| variant | conversations | model turns | guard rejections | rubric flags | expectations met | failed | judge wins |",
          "|---|---|---|---|---|---|---|---|"]
    wins = {v: 0 for v in variants}
    for sid, v in verdicts.items():
        if v["ranking"]:
            wins[v["ranking"][0]] = wins.get(v["ranking"][0], 0) + 1
    for v in variants:
        rows = [r for r in results.values() if r["variant"] == v]
        turns = [t for r in rows for t in r["turns"] if "flags" in t]
        flags = [f for t in turns for f in t["flags"] if not f["rule"].startswith("info:")]
        guarded = sum(1 for t in turns if t.get("failed"))
        ok = sum(1 for r in rows for e in r["expect"] if e["ok"] is True)
        bad = sum(1 for r in rows for e in r["expect"] if e["ok"] is False)
        L.append("| %s | %d | %d | %d | %d | %d | %d | %d |" % (v, len(rows), len(turns), guarded, len(flags), ok, bad, wins.get(v, 0)))
    # Flags by rule.
    rules = sorted(set(f["rule"] for r in results.values() for t in r["turns"] for f in t.get("flags", []) if not f["rule"].startswith("info:")))
    if rules:
        L += ["", "## Rubric flags by rule", "", "| rule | " + " | ".join(variants) + " |", "|---|" + "---|" * len(variants)]
        for k in rules:
            L.append("| %s | " % k + " | ".join(str(sum(1 for r in results.values() if r["variant"] == v for t in r["turns"] for f in t.get("flags", []) if f["rule"] == k)) for v in variants) + " |")
    # Per scenario.
    L += ["", "## Scenarios", ""]
    for s in deck["scenarios"]:
        rows = {r["variant"]: r for r in results.values() if r["scenario"] == s["id"]}
        if not rows:
            continue
        L += ["### %s: %s" % (s["id"], s["title"]), "",
              "Israel time %s. %s" % (s["time"], C.mask(s["resident"]["persona"], 400)), ""]
        if s["id"] in verdicts:
            v = verdicts[s["id"]]
            L.append("Judge (blind): ranking %s. %s" % (" > ".join(v["ranking"]), v["reason"]))
            L.append("")
        for var in variants:
            r = rows.get(var)
            if not r:
                continue
            exp = ["%s %s" % ("ok" if e["ok"] else "FAIL" if e["ok"] is False else "n/a", e["name"]) for e in r["expect"]]
            flags = sorted(set(f["rule"] for t in r["turns"] for f in t.get("flags", []) if not f["rule"].startswith("info:")))
            L.append("**%s.** Expectations: %s. Flags: %s." % (var, "; ".join(exp) or "none", ", ".join(flags) or "none"))
            jv = verdicts.get(s["id"], {}).get("by_variant", {}).get(var)
            if jv:
                viol = "; ".join("%s (%s)" % (x.get("rule"), C.mask(x.get("quote", ""), 60)) for x in jv.get("violations", []))
                L.append("Judge: %s%s" % (jv.get("notes", ""), (" Violations: " + viol) if viol else ""))
            L.append("")
            for t, g in zip(r["transcript"], r["turns"]):
                if t.get("kind") == "menu":
                    L.append("- **resident:** %s" % t["resident"])
                    L.append("- **system:** %s (buttons)" % g["handset"][0])
                    continue
                who = {"tap": "tap", "photo": "photo", "file": "file / voice note"}.get(t.get("kind"), "resident")
                L.append("- **%s:** %s" % (who, C.mask(t.get("resident") or "", 300)))
                if g.get("first_output"):
                    L.append("  - first pass, rejected by %s and rewritten: %s" % (
                        ", ".join(g.get("first_failed") or []) or "a guard", C.mask(g["first_output"].replace("\n", " / "), 300)))
                for c in (t.get("tool_calls") or []):
                    L.append("  - `[%s %s]`" % (c["name"], C.mask(json.dumps(c.get("arguments") or {}, ensure_ascii=False), 200)))
                for h in g.get("handset", []):
                    if h:
                        L.append("- **Michael:** %s" % C.mask(h.replace("\n", " / "), 400))
                fl = [f for f in g.get("flags", []) if not f["rule"].startswith("info:")]
                if fl:
                    L.append("  - flags: " + "; ".join("%s: %s" % (f["rule"], f["quote"]) for f in fl))
            L.append("")
    write(os.path.join(run, "report.md"), "\n".join(L))
    print("wrote %s (%d scenarios, %d verdicts)" % (os.path.join(run, "report.md"), len(deck["scenarios"]), len(verdicts)))


def diff(run, against):
    """Every turn whose handset text differs between two graded runs of the
    same transcripts (one graded on live code, one on a candidate)."""
    a = load_json(os.path.join(run, "results.json"))
    b = load_json(os.path.join(against, "results.json"))
    changed, same = 0, 0
    for key in sorted(set(a) & set(b)):
        for i, (x, y) in enumerate(zip(a[key]["turns"], b[key]["turns"])):
            hx, hy = x.get("handset", []), y.get("handset", [])
            if hx == hy:
                same += 1
                continue
            changed += 1
            print("%s turn %d" % (key, i + 1))
            print("   %s: %s" % (os.path.basename(run.rstrip("/\\")), C.mask(" / ".join(hx), 300)))
            print("   %s: %s" % (os.path.basename(against.rstrip("/\\")), C.mask(" / ".join(hy), 300)))
    only = sorted(set(a) ^ set(b))
    print("")
    print("turns compared: %d | same handset text: %d | different: %d%s"
          % (same + changed, same, changed, (" | in one run only: %s" % ", ".join(only)) if only else ""))
    return changed


# ---------------------------------------------------------------------------
# play: the same game with the live model on OpenRouter (SPENDS CREDIT)
# ---------------------------------------------------------------------------
# 5 Oct, the owner: "ok so run a chatbot test as well using the openrouter
# credit" (after the voice run, estimate about $0.40 for 9 conversations).
# Every model call the bot makes runs on its own settings, read from the live
# workflow on 5 Oct: google/gemini-2.5-flash, temperature 0.6, 1024 tokens, for
# Worth a word?, Answer the resident and Say it again alike. The memory is the
# window buffer's: every run's input and output, rejected passes included, no
# tool calls. The code around each call is live_turn's, the same as a Claude
# player's. A cheap model plays the resident from the card and sees only the
# handset. Tools are stand-ins that follow the deck's rules in code, so nothing
# is written anywhere. The transcripts land where `grade` and `report` read them.
BOT = {"model": "google/gemini-2.5-flash", "temperature": 0.6, "max_tokens": 1024}
RESIDENT_MODEL = "openai/gpt-4.1-mini"
MEMORY_PAIRS = 12           # memoryBufferWindow contextWindowLength: k exchanges
PLAY_CAP = 1.00             # dollars for the whole run

RESIDENT_PROMPT = """You are a resident of a building managed by Homies, writing to Homies on WhatsApp. \
Michael answers for Homies. You are the person on the card below.

Write what this person would really type, one WhatsApp message at a time, in Hebrew unless the card \
says otherwise, reacting only to the words Michael's messages actually say.
- You know only the card. You do not know how Homies works inside. Never type a fact the card does \
not give you; asked something you do not know, say so the way this person would.
- Write like this person on a phone: short, untidy where the card says so (typos, no punctuation, \
words run together), an emoji only if it fits them. Never hand over facts in a neat, form-like way \
unless that is how they write.
- Answer what Michael asked if you know it, the way this person would: sometimes only half of it, \
sometimes with something else on your mind. Skip a question if they would.
- The tendencies are things this person MAY do when the moment fits. Do not force them and do not \
stage them one after another.
- React honestly. A reply that is cold, confusing, repeated or wrong gets this person's real reaction \
(annoyed, confused, asks again, gives up). Do not help Michael and do not trap him.
- The three menu buttons stay in the chat: %s. You may tap one again instead of typing.
- End when this person would: once they have what they came for (often a short thanks, sometimes \
nothing at all), or when they give up.

Answer with JSON only:
{"message": "<what you type, or empty>", "tap": "<a button title if you tap one instead, else empty>", \
"done": <true if this is your last message, or if you simply stop writing (then message is empty)>}

The card:
%s"""


def play_tools(tools):
    """tools_of's shape as OpenAI functions. $fromAI parameters without a
    default are required in n8n's schema, so they are required here."""
    kinds = {"string": "string", "number": "number", "boolean": "boolean", "json": "object"}
    return [{"type": "function", "function": {
        "name": t["name"], "description": t["description"],
        "parameters": {"type": "object",
                       "properties": {p["name"]: {"type": kinds.get(p["type"], "string"), "description": p["description"]}
                                      for p in t["parameters"]},
                       "required": [p["name"] for p in t["parameters"]]}}} for t in tools]


HE_BAR_KOCHBA = re.compile(r"בר[\s\-־]*כוכב")


def wa_stand_in(name, a, s, defaults, state):
    """What a tool returns on this conversation, following the deck's _rule texts."""
    fx = (s.get("fixtures") or {}).get(name)
    building, unit = str(a.get("building") or ""), str(a.get("unit") or a.get("reporter_unit") or "")
    ours = bool(HE_BAR_KOCHBA.search(building)) and bool(re.search(r"(?<!\d)23(?!\d)", building))
    digits = re.sub(r"\D", "", str(a.get("reference") or ""))
    flat = (re.search(r"apartment (\d+)", s["resident"].get("knows", "")) or [None, ""])[1]
    d = defaults.get(name)
    if name == "get_request_status":
        if not fx:
            return d
        sid, kind = s["id"], str(a.get("type") or "")
        pick = "not_found"
        known = [re.sub(r"\D", "", r["reference"]) for r in (fx.get("found") or {}).get("requests", [])]
        if digits and digits in known:
            # A real reference is found, also when the bot read it off an earlier
            # list (5 Oct: the intercom deck said "a reference: not_found" and
            # the stand-in denied a ticket it had itself just listed).
            return fx["found"]
        if sid == "status_ref_spaces":
            if "1501" in digits or (ours and (kind == "plumbing" or unit == "6")):
                pick = "found"
            elif ours:
                pick = "identify"
        elif sid == "status_intercom_slang":
            if ours and (unit == "10" or kind in ("electrical", "other", "maintenance")):
                pick = "found"
            elif ours and not digits:
                pick = "identify"
        elif sid == "status_closed_not_fixed":
            if "1460" in digits or (ours and kind == "lighting"):
                pick = "found"
        elif ours and not digits:          # open_gate_angry and any deck with the plain rule
            pick = "found"
        return fx[pick]
    if name == "get_balance":
        name_ok = re.search(r"Full name ([^,.]+)", s["resident"].get("knows", ""))
        phone_ok = re.search(r"phone ([\d\- ]{9,})", s["resident"].get("knows", ""))
        said_name, said_phone = str(a.get("name") or "").strip(), re.sub(r"\D", "", str(a.get("phone") or ""))
        missing = [x for x, v in (("name", said_name), ("phone", said_phone)) if not v]
        if missing:
            return {"ok": True, "found": 0, "need_identity": True, "missing": missing}
        if (fx and name_ok and phone_ok and " ".join(name_ok.group(1).split()) == " ".join(said_name.split())
                and re.sub(r"\D", "", phone_ok.group(1)) == said_phone):
            return fx
        return d["identity_failed"]
    if fx:
        return fx
    if name == "open_request":
        if not building.strip():
            return d["need_building"]
        if not HE_BAR_KOCHBA.search(building):
            return d["street_unknown"]
        if not re.search(r"\d", building):
            return d["need_number"]
        if not ours:
            return {"ok": True, "opened": False, "building_found": False, "reason": "number_not_on_street",
                    "numbers_we_manage": ["23"]}
        kind = str(a.get("type") or "other")
        if kind in state["opened"]:
            return {"ok": True, "reference": state["opened"][kind], "duplicate": True}
        head, serial, tail = s["ticket"].split("-")
        ref = "%s-%d-%s" % (head, int(serial) + len(state["opened"]), tail)
        state["opened"][kind] = ref
        return dict(d["opened"], reference=ref, reporter_unit=str(a.get("reporter_unit") or ""))
    if name == "verify_address":
        if HE_BAR_KOCHBA.search(building) and re.search(r"(?<!\d)23(?!\d)", building):
            return d["found"]
        return d["need_number"] if HE_BAR_KOCHBA.search(building) and not re.search(r"\d", building) else d["street_unknown"]
    if name == "get_service_info":
        topic = str(a.get("topic") or "")
        hits = [{"title": e["title"], "facts": e["facts"]} for e in d["catalogue"] if any(w in topic for w in e["words"])]
        return {"ok": True, "found": True, "topics": hits} if hits else d["not_found"]
    if name == "get_payment_link":
        return dict(d, link=d["link"].replace("<id>", s["id"]), apartment=flat)
    return {k: v for k, v in (d or {"ok": True}).items() if not k.startswith("_")}


class Chat:
    """One conversation with the live bot: the live code around every message,
    every model call the bot makes on OpenRouter. Its whole state is one JSON
    file (DIR/chats/<scenario>.json), so a Claude player can drive it one
    message at a time (`say`) and a model can drive it in a loop (`play`)."""

    def __init__(self, run, sid, fresh=False):
        import prompt_probe as P
        self.run, self.key = run, P.E.get("OPENROUTER_API_KEY", "").strip()
        if not self.key:
            sys.exit("OPENROUTER_API_KEY missing from .env")
        self.code = load_json(os.path.join(run, "code.json"))
        self.deck = load_json(DECK)
        self.s = next((x for x in self.deck["scenarios"] if x["id"] == sid), None)
        if not self.s:
            sys.exit("no scenario %r in %s" % (sid, DECK))
        self.ps = next(x for x in load_json(os.path.join(run, "deck.json"))["scenarios"] if x["id"] == sid)
        ctx = open(os.path.join(run, "context_A.md"), encoding="utf-8").read()
        self.system = re.search(r"system prompt \(verbatim\)\s*\n+```\n(.*?)\n```", ctx, re.S).group(1)
        self.ack_system = re.search(r"payment-ack model's system prompt \(verbatim\)\s*\n+```\n(.*?)\n```", ctx, re.S).group(1)
        self.fns = play_tools(json.loads(re.search(r"## The tools.*?\n+```json\n(.*?)\n```", ctx, re.S).group(1)))
        self.path = os.path.join(run, "chats", sid + ".json")
        if os.path.exists(self.path) and not fresh:
            self.st = load_json(self.path)
        else:
            self.st = {"scenario": sid, "variant": "A", "played_by": {"bot": BOT}, "turns": [], "memory": [],
                       "opened": {}, "usage": [], "after_menu": False, "ended": ""}

    def spent_run(self):
        """Every chat in the run, so parallel players share one cap."""
        total = sum(u["cost"] for u in self.st["usage"])
        d = os.path.dirname(self.path)
        for f in (os.listdir(d) if os.path.isdir(d) else []):
            if f.endswith(".json") and f != os.path.basename(self.path):
                try:
                    total += sum(u["cost"] for u in load_json(os.path.join(d, f)).get("usage", []))
                except (ValueError, OSError):
                    pass            # another player is writing it right now
        return total

    def save(self):
        import datetime
        self.st["saved_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        keep = ("scenario", "variant", "played_by", "saved_at", "ended", "turns", "usage")
        for path, body in ((self.path, self.st),
                           (os.path.join(self.run, "transcripts", "%s_A.json" % self.st["scenario"]),
                            {k: self.st[k] for k in keep})):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            write(tmp, json.dumps(body, ensure_ascii=False, indent=1))
            os.replace(tmp, path)

    def bill(self, who, u):
        self.st["usage"].append({"who": who, "in": u.get("prompt_tokens", 0), "out": u.get("completion_tokens", 0),
                                 "cached": (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
                                 "reasoning": (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0),
                                 "cost": float(u.get("cost") or 0)})
        spent = self.spent_run()
        if spent > PLAY_CAP:
            self.save()
            sys.exit("stopped: the run has spent $%.4f, over the $%.2f cap" % (spent, PLAY_CAP))

    def model(self, sys_text, user_text, who):
        from voice_qa import openrouter
        msg, u = openrouter(self.key, dict(BOT, messages=[{"role": "system", "content": sys_text},
                                                          {"role": "user", "content": user_text}]))
        self.bill(who, u)
        return (msg.get("content") or "").strip()

    def answer(self, inject):
        """One run of Answer the resident: memory + this input, tools until it writes."""
        from voice_qa import openrouter
        msgs = [{"role": "system", "content": self.system}]
        for i_, o_ in self.st["memory"][-MEMORY_PAIRS:]:
            msgs += [{"role": "user", "content": i_}, {"role": "assistant", "content": o_}]
        msgs.append({"role": "user", "content": inject})
        calls = []
        for _ in range(10):
            msg, u = openrouter(self.key, dict(BOT, messages=msgs, tools=self.fns))
            self.bill("answer", u)
            tc = msg.get("tool_calls") or []
            msgs.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
            if not tc:
                break
            for c in tc:
                try:
                    a = json.loads(c["function"].get("arguments") or "{}")
                except ValueError:
                    a = {"_raw": c["function"].get("arguments")}
                res = wa_stand_in(c["function"]["name"], a, self.s, self.deck["defaults"], self.st)
                calls.append({"name": c["function"]["name"], "arguments": a, "result": res})
                msgs.append({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(res, ensure_ascii=False)})
        out = (msg.get("content") or "").strip()
        self.st["memory"].append([inject, out])
        return out, calls

    def message(self, kind, text, en=None, closing=False):
        """One tenant message through the live code and the models.
        Returns (the messages the phone gets, whether buttons came with them)."""
        sid, code, ps = self.s["id"], self.code, self.ps
        # 5 Oct: the chat's last twelve messages, as `Anything newer?` hands them to
        # the truth guards (a ticket number from earlier is real only if it is there).
        recent = []
        for x in self.st["turns"]:
            recent.append(str(x.get("resident") or ""))
            recent.extend(str(h) for h in (x.get("handset") or []))
        recent = [m for m in recent if m][-11:] + [text]
        t = {"scenario": sid, "kind": kind, "text": text, "first": not self.st["turns"],
             "after_menu": self.st["after_menu"], "recent": recent}
        r = live_turn(code, ps, t)
        if r["menu"]:
            rec = {"resident": text, "kind": "menu"}
            if en:
                rec["resident_en"] = en
            self.st["turns"].append(rec)
            self.st["after_menu"] = True
            return [r["system_sends"]], True
        self.st["after_menu"] = False
        ack = self.model(self.ack_system, r["ack_model_reads"], "ack") or "NONE"
        t["ack"] = ack
        r = live_turn(code, ps, t)
        out, calls = self.answer(r["answering_model_reads"])
        rec = {"resident": text, "kind": kind, "input": r["answering_model_reads"], "ack": ack,
               "tool_calls": calls, "output": out}
        if en:
            rec["resident_en"] = en
        if closing:
            rec["closing"] = True
        chk = live_turn(code, ps, dict(t, tool_calls=calls, output=out))
        if chk["guards_failed"]:
            note, inject2 = chk["retry"]["note"], chk["retry"]["answering_model_reads"]
            out2, calls2 = self.answer(inject2)
            rec.update(first_output=out, first_failed=chk["guards_failed"], first_tool_calls=calls,
                       retry_note=note, tool_calls=calls2, output=out2)
            chk = live_turn(code, ps, dict(t, run_index=1, retry_note=note, tool_calls=calls2, output=out2,
                                           first_try=chk["retry"].get("try_item")))
            if chk["guards_failed"] and chk.get("mend"):
                # 5 Oct: no model; what Mend the reply wrote is what goes out.
                m = chk["mend"]
                rec.update(second_failed=chk["guards_failed"], claimed=m.get("claimed"),
                           mended=m.get("mended"), mend_output=m.get("output"))
                if m.get("claimed") is True:
                    rec["rescue"] = m.get("rescue")
                hs = chk.get("handset") or []
                rec["handset"] = hs
                self.st["turns"].append(rec)
                return hs, False
            if chk["guards_failed"]:
                sa = chk["say_again"]
                said = self.model(sa["system"], sa["reads"], "say_again")
                rec["say_again_output"] = said
                chk2 = live_turn(code, ps, dict(t, run_index=1, retry_note=note, tool_calls=calls2,
                                                output=out2, say_again_output=said))["say_again"]
                # Second try usable? has nothing on its false branch: when Say it
                # again's text fails too, the tenant gets nothing (but an ack).
                hs = ([chk2["ack_went_first"]] if chk2.get("ack_went_first") else []) + \
                     ([chk2["sent"]] if chk2.get("sent") else [])
                rec["second_try_failed"] = chk2.get("failed") or []
                rec["handset"] = hs
                self.st["turns"].append(rec)
                return hs, False
        hs = chk.get("handset") or []
        rec["handset"] = hs
        self.st["turns"].append(rec)
        return hs, bool(chk.get("buttons"))


def phone_view(hs, buttons):
    lines = list(hs) or ["(no reply came)"]
    if buttons:
        lines[-1] += "  [buttons: " + " / ".join(TAPS.values()) + "]"
    return [C.mask(x, 100000) for x in lines]


def play(run):
    """A model plays every tenant (the first 5 Oct run). Kept for cheap smoke
    runs; a Claude player through `say` acts far more like a real tenant."""
    only = os.environ.get("WA_QA_ONLY", "").split(",") if os.environ.get("WA_QA_ONLY") else None
    from voice_qa import openrouter
    for s in load_json(DECK)["scenarios"]:
        if only and s["id"] not in only:
            continue
        chat = Chat(run, s["id"], fresh=True)
        chat.st["played_by"]["resident"] = RESIDENT_MODEL
        card = json.dumps({k: s["resident"][k] for k in ("persona", "knows", "wants", "tendencies")},
                          ensure_ascii=False, indent=1)
        resident_msgs = [{"role": "system", "content": RESIDENT_PROMPT % (" / ".join(TAPS.values()), card)}]
        print("\n=== %s (%s, %s)" % (s["id"], s["button"], s["time"]))
        ended = "8 messages after the tap"
        for line in s["resident"]["script"]:
            kind = line.get("kind", "text")
            view = phone_view(*chat.message(kind, line["say"]))
            resident_msgs += [{"role": "assistant", "content": json.dumps(
                                  {"message": line["say"] if kind == "text" else "",
                                   "tap": line["say"] if kind == "tap" else "", "done": False}, ensure_ascii=False)},
                              {"role": "user", "content": "\n\n".join(view)}]
            print("  resident: %s%s" % ("[tap] " if kind == "tap" else "", line["say"]))
            for h in view:
                print("  handset : %s" % h.replace("\n", " / "))
        for _ in range(8):
            msg, u = openrouter(chat.key, {"model": RESIDENT_MODEL, "messages": resident_msgs, "temperature": 0.7,
                                           "response_format": {"type": "json_object"}})
            chat.bill("resident", u)
            try:
                said = json.loads(msg.get("content") or "{}")
            except ValueError:
                said = {"message": msg.get("content") or "", "done": False}
            resident_msgs.append({"role": "assistant", "content": msg.get("content") or ""})
            tap = str(said.get("tap") or "").strip()
            text = tap if tap in TAPS.values() else str(said.get("message") or "").strip()
            if not text:
                ended = "the resident stopped writing"
                break
            kind = "tap" if tap in TAPS.values() else "text"
            print("  resident: %s%s" % ("[tap] " if kind == "tap" else "", text))
            view = phone_view(*chat.message(kind, text, closing=bool(said.get("done"))))
            for h in view:
                print("  handset : %s" % h.replace("\n", " / "))
            resident_msgs.append({"role": "user", "content": "\n\n".join(view)})
            if said.get("done"):
                ended = "the resident's last message"
                break
        chat.st["ended"] = ended
        chat.save()
        print("  -- %s; $%.4f" % (ended, sum(x["cost"] for x in chat.st["usage"])))


TENANT = """# Playing a tenant against the live Homies WhatsApp bot

You are ONE tenant of a building Homies manages, writing to Homies on WhatsApp. Michael answers for
Homies. Michael is the real bot: its own model and its own code answer every message you send, and
each message costs a little real credit (the owner approved this run; the script stops itself at $1).
Nothing you write reaches a real person, and nothing is opened, sent or written anywhere.

## Who you are

Your card (persona, knows, wants, tendencies) is in the message that started you. You know only the
card. You do not know how Homies works inside, what the bot is told, or what anyone checks. Never type
a fact the card does not give you; asked something you do not know, say so the way this person would.

## How to write

Write what this person would really type on their phone, one WhatsApp message at a time, in Hebrew
unless the card says otherwise:
- short and untidy where the card says so: typos, no punctuation, words run together, slang, an emoji
  only if it fits them;
- real tenants rarely hand over facts in a neat, form-like way: they give the address in pieces,
  forget the apartment, answer half a question, ask something else instead, send two short lines
  where one would do;
- the tendencies are things this person MAY do when the moment fits; do not force them and do not
  stage them one after another;
- react honestly to what Michael's messages actually say: a reply that is cold, confusing, repeated,
  slow or wrong gets this person's real reaction (annoyed, confused, asks again, gives up); a good
  one gets a real reaction too;
- do not help Michael and do not trap him.

## How to send

Start with your card's opening, exactly: the hello, then the tap on your button. After that you are
free. Every message is one command, run from the repo root (C:/Users/Acer nitro 5/Desktop/Homie),
with the JSON on stdin:

    python scripts/wa_qa.py say --run "<run dir>" --deck scripts/wa_qa_menu_buttons.json < msg.json

where msg.json (write it fresh for each message, in your scratch folder) is:

    {"scenario": "<id>", "kind": "text", "text": "<your message>", "en": "<a faithful English gloss of it>"}

- `kind` `tap` with a button's title as `text` presses that button. Once the menu has shown, its three
  buttons stay in the chat: פתיחת קריאת שירות, מצב קריאה קיימת, לדבר עם נציג.
- `kind` `photo` with `text` "" (or a caption) only if your card gives you a photo.
- Add `"closing": true` to a thanks or goodbye that ends the conversation for you.
- `en` is for the owner, who does not read Hebrew: what you typed, faithfully, typos' sense included.

It prints what your phone shows and nothing else: `phone_shows`, the messages that arrived, in order,
and `buttons`, the buttons that came with them. If `phone_shows` is empty, nothing came back; do what
this person would (wait and write again, or give up).

## When to stop

End when this person would: once they have what they came for (often a short thanks, sometimes
nothing at all), or when they give up. At most 8 messages after the tap. If the person simply stops
writing, record that and stop, with this as msg.json:

    {"scenario": "<id>", "end": "the tenant stopped writing"}

## Rules

- Use only the `say` command. Do not open, read or list any other file in the run directory or the repo.
- When you are done, reply with one line: how many messages you sent and how the conversation ended.
"""


def say(run):
    """One message from a Claude player acting as the tenant; prints only what
    the tenant's phone shows. The owner, 5 Oct: "act like a real tenant on those
    conversation" (the first OpenRouter run had a model playing them, too neatly)."""
    t = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    chat = Chat(run, str(t.get("scenario") or ""))
    show = lambda o: print(json.dumps(o, ensure_ascii=False, indent=1))
    if t.get("end"):
        chat.st["ended"] = str(t["end"])
        chat.save()
        show({"ended": chat.st["ended"]})
        return
    if chat.st["ended"]:
        sys.exit("this conversation has ended (%s)" % chat.st["ended"])
    if len(chat.st["turns"]) >= 12:
        sys.exit("12 messages already: end the conversation")
    kind = t.get("kind", "text")
    if kind not in ("text", "tap", "photo", "file"):
        sys.exit("kind must be text, tap, photo or file")
    text = "" if kind == "file" else str(t.get("text") or "")
    if kind == "tap" and text not in TAPS.values():
        sys.exit("a tap's text must be one of: " + " / ".join(TAPS.values()))
    hs, buttons = chat.message(kind, text, en=t.get("en"), closing=bool(t.get("closing")))
    if t.get("closing"):
        chat.st["ended"] = "the tenant's last message"
    chat.save()
    show({"phone_shows": [C.mask(x, 100000) for x in hs],
          "buttons": list(TAPS.values()) if buttons else []})


# ---------------------------------------------------------------------------
# live: one tenant message into the LIVE bot (SPENDS AND WRITES)
# ---------------------------------------------------------------------------
# 5 Oct, the owner: "just write only in the bar kochba which is owned by assaf
# clix ... act like human and dont delete anything like dont delete the tickets
# after testing". The message goes into the live n8n workflow through its
# webhook, in the envelope Chatwoot itself sends (copied from a real run that
# day), from the number and conversation in DIR/live_config.json, so the bot's
# replies reach that WhatsApp. Everything the bot does is real: its model, its
# checks, its tools, tickets in the ticket service (and OXS, for a number in
# OXS_MIRROR_PHONES), notes to the team. NOTHING IS CLEANED UP AFTERWARDS, on
# the owner's word; that is the difference from probe_whatsapp.py, which
# deletes its rows. The player sees only what the phone got; the run keeps
# what happened inside each execution for the report.
LIVE_WF = "u2JjrbcNPYyyh3yl"


def _out(rd, name, run=0):
    """The first item a node put out on any branch, or None."""
    try:
        for branch in rd[name][run]["data"]["main"]:
            if branch:
                return branch[0]["json"]
    except Exception:  # noqa: BLE001
        return None
    return None


def _run_json(r):
    try:
        for branch in r["data"]["main"]:
            if branch:
                return branch[0]["json"]
    except Exception:  # noqa: BLE001
        return {}
    return {}


def _steps(steps):
    """An agent run's intermediateSteps as the transcript's tool calls."""
    out = []
    for st in steps or []:
        a = st.get("action") or {}
        res = st.get("observation")
        try:
            o = json.loads(res) if isinstance(res, str) else res
            if isinstance(o, list) and o and isinstance(o[0], dict) and o[0].get("results"):
                r = o[0]["results"][0].get("result")
                res = json.loads(r) if isinstance(r, str) else r
            elif isinstance(o, (dict, list)):
                res = o
        except Exception:  # noqa: BLE001
            pass
        out.append({"name": a.get("tool") or "?", "arguments": a.get("toolInput") or {}, "result": res})
    return out


def live_record(rd):
    """What happened inside one live execution, in the transcript's shape,
    and whether the reply carried the menu's buttons."""
    rec = {"ack": str((_out(rd, "Worth a word?") or {}).get("output") or "").strip() or "NONE"}
    runs = rd.get("Answer the resident") or []
    try_at = ((rd.get("Try again") or [{}])[0] or {}).get("startTime")
    first = [r for r in runs if try_at is None or (r.get("startTime") or 0) < try_at]
    second = [r for r in runs if try_at is not None and (r.get("startTime") or 0) >= try_at]
    if first:
        j = _run_json(first[-1])
        rec["output"] = str(j.get("output") or "")
        rec["tool_calls"] = _steps(j.get("intermediateSteps"))
    if second:
        j = _run_json(second[-1])
        rec["first_output"], rec["first_tool_calls"] = rec.get("output", ""), rec.get("tool_calls", [])
        rec["output"] = str(j.get("output") or "")
        rec["tool_calls"] = _steps(j.get("intermediateSteps"))
        rec["retry_note"] = str((_out(rd, "Try again") or {}).get("retry_note") or "")
    if rd.get("Open it anyway"):
        rec["rescue"] = _out(rd, "Open it anyway")
    sa = _out(rd, "Say it again")
    if sa is not None:
        rec["say_again_output"] = str(sa.get("output") or "")
    # 5 Oct (n8n_whatsapp_safetynet.py): the last resort without a model.
    if rd.get("Claimed a ticket?"):
        rec["claimed"] = bool(rd["Claimed a ticket?"][0].get("data", {}).get("main", [[]])[0])
    md = _out(rd, "Mend the reply")
    if md is not None:
        rec["mend_output"], rec["mended"] = str(md.get("output") or ""), str(md.get("mended") or "")
    hs, buttons = [], False
    for name in ("Say it now", "Send", "Send the rest"):
        j = _out(rd, name)
        if j and j.get("content"):
            hs.append(str(j["content"]))
            if name == "Send" and j.get("content_type") == "input_select":
                buttons = True
    rec["handset"] = hs
    return rec, buttons


def live(run):
    """One message from a Claude player acting as the tenant, into the live bot."""
    import time
    import urllib.parse
    import urllib.request
    import n8n_whatsapp as NW
    cfg = load_json(os.path.join(run, "live_config.json"))
    t = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    sid = str(t.get("scenario") or "").strip()
    if not sid:
        sys.exit("scenario missing")
    path = os.path.join(run, "live", sid + ".json")
    st = load_json(path) if os.path.exists(path) else {
        "scenario": sid, "variant": "A", "turns": [], "ended": "",
        "played_by": {"bot": "the live n8n workflow " + LIVE_WF, "tenant": "Claude"}}
    show = lambda o: print(json.dumps(o, ensure_ascii=False, indent=1))

    def save():
        for p in (path, os.path.join(run, "transcripts", sid + "_A.json")):
            os.makedirs(os.path.dirname(p), exist_ok=True)
            write(p + ".tmp", json.dumps(st, ensure_ascii=False, indent=1))
            os.replace(p + ".tmp", p)

    if t.get("end"):
        st["ended"] = str(t["end"])
        save()
        show({"ended": st["ended"]})
        return
    if st["ended"]:
        sys.exit("this conversation has ended (%s)" % st["ended"])
    if len(st["turns"]) >= 12:
        sys.exit("12 messages already: end the conversation")
    kind = t.get("kind", "text")
    text = str(t.get("text") or "").strip()
    if kind not in ("text", "tap") or not text:
        sys.exit("live sends a text or a tap, never an empty message")
    if kind == "tap" and text not in TAPS.values():
        sys.exit("a tap's text must be one of: " + " / ".join(TAPS.values()))
    E = NW.env()
    hook = (E["N8N_BASE_URL"].strip().rstrip("/") + "/webhook/homies-whatsapp?s="
            + urllib.parse.quote(E["N8N_WEBHOOK_SECRET"].strip()))
    before = int(NW.api("GET", "/api/v1/executions?workflowId=%s&limit=1" % LIVE_WF)["data"][0]["id"])
    mid = 9100000000 + int(time.time() * 1000) % 10**9
    env = {"event": "message_created", "id": mid, "content": text, "message_type": "incoming",
           "private": False, "content_type": "text", "content_attributes": {},
           "sender": {"id": cfg["contact_id"], "type": "contact", "name": cfg["name"], "phone_number": cfg["phone"]},
           "conversation": {"id": cfg["conv_id"], "status": "open", "inbox_id": cfg["inbox_id"], "labels": [],
                            "meta": {"assignee": None, "assignee_type": None}},
           "inbox": {"id": cfg["inbox_id"], "name": cfg["inbox_name"]},
           "account": {"id": cfg["account_id"], "name": cfg["account_name"]}}
    req = urllib.request.Request(hook, data=json.dumps(env, ensure_ascii=False).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "homies-live-tenant/1.0"})
    urllib.request.urlopen(req, timeout=60).read()
    # The run that took this message is the one whose webhook body carries its
    # id. Runs that finish and are not it (the bot's own outgoing echoes) are
    # passed over once; a run still going is looked at again.
    mine, done, deadline = None, set(), time.time() + 240
    while time.time() < deadline and mine is None:
        time.sleep(4)
        for e in sorted(NW.api("GET", "/api/v1/executions?workflowId=%s&limit=25" % LIVE_WF)["data"],
                        key=lambda e: int(e["id"])):
            if int(e["id"]) <= before or e["id"] in done:
                continue
            if not (e.get("finished") or e.get("status") in ("success", "error", "crashed", "canceled")):
                continue
            d = NW.api("GET", "/api/v1/executions/%s?includeData=true" % e["id"])
            rd = ((d.get("data") or {}).get("resultData") or {}).get("runData") or {}
            body = (_out(rd, "WhatsApp") or {}).get("body") or {}
            done.add(e["id"])
            if str(body.get("id")) == str(mid):
                mine = (e["id"], d, rd)
                break
    if mine is None:
        st["turns"].append({"resident": text, "kind": kind, "resident_en": t.get("en") or "", "handset": [],
                            "note": "no finished run found within 4 minutes"})
        save()
        show({"phone_shows": [], "buttons": []})
        return
    eid, d, rd = mine
    S = _out(rd, "Sort") or {}
    err = str((((d.get("data") or {}).get("resultData") or {}).get("error") or {}).get("message") or "")
    if S.get("greeting") is True:
        hs = [str((_out(rd, "Send") or {}).get("content") or "")]
        rec, buttons = {"resident": text, "kind": "menu", "handset": [h for h in hs if h]}, True
    else:
        rec, buttons = live_record(rd)
        rec = dict({"resident": text, "kind": kind}, **rec)
    rec["execution"] = eid
    if t.get("en"):
        rec["resident_en"] = t["en"]
    if t.get("closing"):
        rec["closing"] = True
        st["ended"] = "the tenant's last message"
    if err:
        rec["error"] = err[:300]
    st["turns"].append(rec)
    save()
    show({"phone_shows": [C.mask(x, 100000) for x in rec.get("handset") or []],
          "buttons": list(TAPS.values()) if buttons and rec.get("handset") else []})


def main():
    argv = sys.argv[1:]
    if not argv or "--run" not in argv:
        sys.exit(__doc__)
    run = argv[argv.index("--run") + 1]
    cmd = argv[0]
    if "--deck" in argv:
        global DECK
        DECK = argv[argv.index("--deck") + 1]
    if cmd == "bundle":
        variants = []
        for i, a in enumerate(argv):
            if a == "--variant":
                label, spec = argv[i + 1].split("=", 1)
                variants.append((label, spec))
        cand = argv[argv.index("--candidate") + 1] if "--candidate" in argv else None
        bundle(run, variants, cand)
    elif cmd == "diff":
        sys.exit(1 if diff(run, argv[argv.index("--against") + 1]) else 0)
    elif cmd == "turn":
        turn(run)
    elif cmd == "grade":
        grade(run)
    elif cmd == "judge":
        judge(run)
    elif cmd == "report":
        report(run)
    elif cmd == "play":
        play(run)
    elif cmd == "say":
        say(run)
    elif cmd == "live":
        live(run)
    elif cmd == "tenant":
        write(os.path.join(run, "TENANT.md"), TENANT)
        print("wrote " + os.path.join(run, "TENANT.md"))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
