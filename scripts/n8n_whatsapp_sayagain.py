# -*- coding: utf-8 -*-
"""The last two fixed sentences: let the model write the rescue itself.

    python scripts/n8n_whatsapp_sayagain.py            # dry run
    python scripts/n8n_whatsapp_sayagain.py --apply    # write it

WHY
`Reply usable?` throws a reply away when it is empty, one word, or claims a
ticket with no reference behind it. What went out instead was `Hand over
instead`, a Set node holding two fixed Hebrew sentences — and if those ever came
out empty, `Send` had a third one hard-coded as a fallback inside its body.

The owner: *"i dont want a templated message, only the intro one which is the
menu."* These are not the menu.

WHAT REPLACES THEM
`Say it again` — a second model pass with no tools, given the resident's message
and, when `Open it anyway` has just minted one, the real reference. It writes the
message itself, so the resident gets sentences rather than a stock line. Its
system prompt is deliberately short and carries only what the voice needs; the
main prompt is not reused because it tells the model it has tools, and this node
has none.

`Second try usable?` gates it: if the second attempt is also unusable, **nothing
is sent**. There is no third fallback, because a third fallback is a template.
`Open it anyway` has already written a real ticket by then, so the report is not
lost — and this whole path fired 0 times in the 60 executions before the change,
so a double failure is close to hypothetical.

WHY AN AGENT NODE AND NOT A BASIC LLM CHAIN
`@n8n/n8n-nodes-langchain.agent` v3 is the node type this workflow already runs
and is known to work against the OpenRouter sub-node. A chain node would be a
better fit on paper and an unverified guess in practice.

HONEST LIMIT
The rescue path cannot be triggered on demand — it needs the model to produce an
unusable reply — so this ships wired and read back, not exercised. If the new
node fails at runtime the result is that nothing is sent, which is the same as
the designed fallback, so the downside is bounded.

Idempotent. Running it twice reports nothing to do.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"

# `}}` anywhere inside ends an n8n expression, so every brace that would touch
# another has a space in it.
SAY_TEXT = (
    "={{ (() => {"
    " let ref = '';"
    " try { const r = $json.results[0].result;"
    " ref = (typeof r === 'string' ? JSON.parse(r) : r).reference || '';"
    " } catch (e) { }"
    " const said = String($('Sort').first().json.text || '');"
    " const note = ref"
    " ? '[נפתחה עכשיו קריאה במערכת, מספר ' + ref + '. תמסור לדייר במילים שלך "
    "שהקריאה נפתחה, עם המספר.]'"
    " : '[התשובה הקודמת שלך לא יצאה לדייר. תכתוב לו תשובה קצרה וברורה על "
    "ההודעה שלו.]';"
    " return note + String.fromCharCode(10) + said;"
    " } )() }}"
)

SAY_SYSTEM = (
    "אתה מיכאל, נציג השירות של הומיז, חברת ניהול בתים משותפים, "
    "ואתה כותב לדייר בוואטסאפ בעברית. על עצמך אתה מדבר בלשון זכר, "
    "ואל הדייר אתה פונה בלשון רבים.\n"
    "ההודעה קצרה, בלי markdown, בלי כוכביות ובלי סוגריים. "
    "אין נוסח קבוע ואין משפט מוכן: תכתוב את זה במילים שלך.\n"
    "אתה מדווח מה כבר נעשה, לא מה עומד לקרות, "
    "ואתה לא אומר שמישהו יוצא לדרך או שעזרה נשלחת.\n"
    "אל תמציא מספר קריאה. אם לא נמסר לך מספר, אל תגיד שנפתחה קריאה."
)

SECOND_OK = (r"={{ String($json.output || '').trim()"
             r".split(/\s+/).filter(Boolean).length >= 2 }}")

# The fallback baked into Send's body: the third copy of the same sentence.
SEND_OLD = ".trim() || 'אני מעביר את זה לצוות, נחזור בהקדם.';"
SEND_NEW = ".trim();"


def main():
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes = live["nodes"]
    by = {n["name"]: n for n in nodes}
    conns = live["connections"]
    for need in ("Open it anyway", "Send", "Type for a moment", "Log reply",
                 "OpenRouter"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    changes = []

    # --- The two new nodes --------------------------------------------------
    # Placed on the empty row below the tools, not tucked in beside `Open it
    # anyway` where they first went: scripts/n8n_layout.py refused that, and it
    # is right to. A node drawn on top of another is a minute lost at eight in
    # the morning while the thing is failing.
    SAY_POS, SECOND_POS = [1200, 540], [1440, 540]

    if "Say it again" not in by:
        nodes.append({
            "id": "say_again", "name": "Say it again",
            "type": "@n8n/n8n-nodes-langchain.agent", "typeVersion": 3,
            "position": SAY_POS,
            "parameters": {"promptType": "define", "text": SAY_TEXT,
                           "options": {"systemMessage": SAY_SYSTEM}},
        })
        changes.append("Say it again: new node, writes the rescue message itself")
    else:
        p = by["Say it again"]["parameters"]
        if p.get("text") != SAY_TEXT or p.get("options", {}).get("systemMessage") != SAY_SYSTEM:
            p["text"] = SAY_TEXT
            p.setdefault("options", {})["systemMessage"] = SAY_SYSTEM
            changes.append("Say it again: prompt updated")
        if by["Say it again"].get("position") != SAY_POS:
            by["Say it again"]["position"] = SAY_POS
            changes.append("Say it again moved clear of Open it anyway")

    if "Second try usable?" in by and by["Second try usable?"].get("position") != SECOND_POS:
        by["Second try usable?"]["position"] = SECOND_POS
        changes.append("Second try usable? moved clear of Conversation so far")

    if "Second try usable?" not in by:
        nodes.append({
            "id": "second_ok", "name": "Second try usable?",
            "type": "n8n-nodes-base.if", "typeVersion": 2,
            "position": SECOND_POS,
            "parameters": {"conditions": {
                "options": {"caseSensitive": True, "leftValue": "",
                            "typeValidation": "loose"},
                "conditions": [{
                    "id": "ok", "leftValue": SECOND_OK, "rightValue": "",
                    "operator": {"type": "boolean", "operation": "true",
                                 "singleValue": True},
                }],
                "combinator": "and",
            }},
        })
        changes.append("Second try usable?: new node -- if the retry is also "
                       "unusable, nothing is sent rather than a stock line")

    # --- Rewiring -----------------------------------------------------------
    # Every edge that pointed at the Set node now points at the retry, found by
    # walking the graph rather than by naming the ones I remembered.
    #
    # `Open it anyway` was the obvious feeder. The one that was NOT obvious is
    # `Answer the resident`.main[1] — the agent's ERROR output, which catches a
    # model timeout and had the same fixed sentence waiting for it. n8n rejected
    # the first PUT because of it, which is the validation doing its job.
    #
    # On that path `$json` carries no rescue result, so Say it again's try/catch
    # leaves `ref` empty and it writes the plain apology instead of announcing a
    # ticket. If the model is what failed, the retry fails too and nothing is
    # sent — the designed fallback.
    rerouted = []
    for src, spec in conns.items():
        for branch in spec.get("main", []):
            for edge in branch:
                if edge.get("node") == "Hand over instead":
                    edge["node"] = "Say it again"
                    rerouted.append(src)
    if rerouted:
        changes.append("%s -> Say it again (was Hand over instead)"
                       % ", ".join(sorted(set(rerouted))))

    want_say = {"main": [[{"node": "Second try usable?", "type": "main", "index": 0}]]}
    if conns.get("Say it again") != want_say:
        conns["Say it again"] = want_say
        changes.append("Say it again -> Second try usable?")

    want_second = {"main": [[
        {"node": "Type for a moment", "type": "main", "index": 0},
        {"node": "Log reply", "type": "main", "index": 0}]]}
    if conns.get("Second try usable?") != want_second:
        conns["Second try usable?"] = want_second
        changes.append("Second try usable? -> the send path, true branch only")

    lm = conns.setdefault("OpenRouter", {}).setdefault("ai_languageModel", [[]])
    if not any(d["node"] == "Say it again" for d in lm[0]):
        lm[0].append({"node": "Say it again", "type": "ai_languageModel", "index": 0})
        changes.append("OpenRouter also drives Say it again")

    # --- The Set node and its two sentences, gone ---------------------------
    if "Hand over instead" in by:
        live["nodes"] = [n for n in nodes if n["name"] != "Hand over instead"]
        conns.pop("Hand over instead", None)
        changes.append("Hand over instead: deleted, with both fixed sentences")

    # --- The third copy, inside Send ----------------------------------------
    send = by["Send"]
    body = send["parameters"].get("jsonBody") or ""
    if SEND_OLD in body:
        send["parameters"]["jsonBody"] = body.replace(SEND_OLD, SEND_NEW, 1)
        changes.append("Send: drop the hard-coded fallback sentence in its body")

    print("workflow : %s  (%s, active=%s)"
          % (live["name"], live["id"], live.get("active")))
    if not changes:
        print("")
        print("Nothing to do. Live already matches.")
        return

    print("")
    print("changes:")
    for c in changes:
        print("  - %s" % c)

    if not apply:
        print("")
        print("Dry run. Re-run with --apply to write it.")
        return

    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": live["nodes"],
        "connections": live["connections"], "settings": live.get("settings", {}),
    })
    print("")
    print("written. Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
