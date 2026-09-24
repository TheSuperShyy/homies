# -*- coding: utf-8 -*-
"""A reply that did real work arrives as two messages: the word, then the thing.

    python scripts/n8n_whatsapp_twobeat.py            # dry run
    python scripts/n8n_whatsapp_twobeat.py --apply    # write it

WHY, the owner on 24 Sep, against a transcript where "give me the payment link"
was answered with the link and nothing else: *"it was straight to the point ...
i dont want it to apologize but reword instead like this is just an example `I
understand please give me a moment, i will check it out on our system.` then
after it will send like `Hi, regarding the blah blah this is the payment link
for the blah blah please do not blah blah`"*

Two messages, and he picked that shape over a single message when asked. So the
model writes both halves in ONE completion, separated by a delimiter, and the
workflow posts them as two Chatwoot messages about a second and a half apart.
One model call, no extra spend, and both halves are the model's own words --
which is what keeps this inside the standing rule that the menu is the only
fixed text in the system.

THE DELIMITER IS `§§§`, and the choice is not free. Send's cleanup strips
`[...]` wholesale (`replace(/\\[[^\\]]*\\]/g, ' ')`), so any bracketed marker
would be eaten before the split could see it. Em dashes are rewritten to
commas. `§` survives both and does not occur in Hebrew WhatsApp prose.

DEGRADES TO TODAY'S BEHAVIOUR. No delimiter, or nothing after it, and `Two
parts?` sends the flow straight on: one message, exactly as before. That
matters because the model will sometimes forget, and a forgotten delimiter must
cost a nicety, never a reply.

THE BUTTONS RIDE ON A SINGLE MESSAGE ONLY. When the reply splits, the menu rows
are suppressed: a resident who asked a concrete question and is being answered
in two beats does not also need the three-row menu, and attaching it to the
first beat would put buttons above an answer that has not arrived yet.

Surgical, like every live edit here. `n8n_whatsapp.py --apply` remains the wrong
way to ship to this workflow. Idempotent: running it twice reports nothing to do.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n8n_whatsapp as W  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SEP = "§§§"

# The source both new nodes read. `Type for a moment` is the only node feeding
# `Send`, and a Wait passes its item through untouched, so this is the same
# text `Send` itself splits -- agent output or a canned line, whichever ran.
SRC = ("String($('Type for a moment').first().json.output || "
       "$('Type for a moment').first().json.text || '')")

# --------------------------------------------------------------------------
# 1. Send: post the FIRST half, and drop the buttons when there is a second.
# --------------------------------------------------------------------------
# `acked`, 24 Sep: when `Worth a word?` has ALREADY sent the resident a "one
# moment" before the work started, the model must not send another. The inject
# tells it so and it did it anyway -- three messages, two of them saying the
# same thing. Instructions lost, so this is enforced here instead: with an
# acknowledgement already out, any §§§ split is collapsed and the half that
# survives is the SECOND one, the answer. The duplicate is dropped, never the
# substance.
#
# Read through `Carry on` because the agent node replaces $json with its own
# output, so the field cannot ride through on the item. try/catch because the
# retry path (`Try again` -> agent) never runs `Carry on` and referencing an
# unexecuted node throws.
ACKED = ("(() => { try { return String($('Carry on').first().json.acked || '')"
         ".trim(); } catch (e) { return ''; } })()")

SEND_T_OLD = ("const raw = String($json.output || $json.text || ''); "
              "const parts = raw.split('%s'); "
              "const two = parts.length > 1 && parts.slice(1).join('%s').trim().length > 0; "
              "const t = String(parts[0] || '')" % (SEP, SEP))
SEND_T_NEW = ("const raw = String($json.output || $json.text || ''); "
              "const parts = raw.split('%s'); const acked = %s; "
              "const two = !acked && parts.length > 1 && "
              "parts.slice(1).join('%s').trim().length > 0; "
              "const t = String((acked && parts.length > 1 ? "
              "parts.slice(1).join('%s') : parts[0]) || '')" % (SEP, ACKED, SEP, SEP))

# The whole button condition gets wrapped in `!two && ( ... )`. Two anchors,
# the open and the close; the close is the last `)))` before the body block.
SEND_IF_OLD = "if ($('Sort').first().json.greeting ||"
SEND_IF_NEW = "if (!two && ($('Sort').first().json.greeting ||"
SEND_CLOSE_OLD = ".trim()))) { body.content_type"
SEND_CLOSE_NEW = ".trim())))) { body.content_type"

# --------------------------------------------------------------------------
# 2. The three new nodes.
# --------------------------------------------------------------------------
TWO_EXPR = ("={{ (() => { const r = " + SRC + "; const p = r.split('" + SEP + "'); "
            "const a = " + ACKED + "; return !a && p.length > 1 && "
            "p.slice(1).join('" + SEP + "').trim().length > 0; })() }}")

# The second half, cleaned the same way Send cleans the first. Kept in step
# with Send by hand: if Send's cleanup chain changes, change it here too.
REST_BODY = ("={{ (() => { const r = " + SRC + "; const p = r.split('" + SEP + "'); "
             "const t = p.slice(1).join('" + SEP + "')"
             ".replace(/\\[[^\\]]*\\]/g, ' ').replace(/\\s*[—–]\\s*/g, ', ')"
             ".replace(/,\\s*,/g, ',').replace(/\\s+,/g, ',').replace(/,\\s*\\./g, '.')"
             ".replace(/\\s{2,}/g, ' ').trim(); "
             "return JSON.stringify({ content: t, message_type: 'outgoing' }); })() }}")

# The owner, 24 Sep, watching the first live one: "after a few seconds like 2".
# So ~2s, jittered, rather than the 1.1-1.9 it shipped with. Long enough that
# the first message reads as somebody actually going to look, short enough that
# nobody wonders whether it broke.
HOLD_AMOUNT = "={{ 1.7 + Math.random() * 0.9 }}"

# Positions are enforced, not just set on create: n8n_layout.py fails the
# workflow when two nodes sit closer than the 240 x 60 grid, and the first
# placement here put three pairs on top of each other. Keeping them in one
# table means a re-run repairs a canvas somebody has dragged about.
POS = {"Two parts?": [1680, 64], "Hold a beat": [1920, -80],
       "Send the rest": [2160, -80]}


def guard(gid, expr):
    return {"id": gid, "leftValue": expr, "rightValue": "",
            "operator": {"type": "boolean", "operation": "true", "singleValue": True}}


def main():
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes = live["nodes"]
    by = {n["name"]: n for n in nodes}
    conns = live["connections"]
    for need in ("Send", "Type for a moment", "Show it in Open"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    changes = []

    def edit(node, field, old, new, label):
        val = by[node]["parameters"].get(field) or ""
        if new in val and old not in val:
            return
        if old not in val:
            sys.exit("Anchor missing on live %r.%s -- refusing to guess:\n  %s"
                     % (node, field, label))
        by[node]["parameters"][field] = val.replace(old, new, 1)
        changes.append(label)

    edit("Send", "jsonBody", SEND_T_OLD, SEND_T_NEW,
         "Send: splits the reply on %s and posts the first half" % SEP)
    edit("Send", "jsonBody", SEND_IF_OLD, SEND_IF_NEW,
         "Send: the menu rows are suppressed when the reply splits (open)")
    edit("Send", "jsonBody", SEND_CLOSE_OLD, SEND_CLOSE_NEW,
         "Send: the menu rows are suppressed when the reply splits (close)")

    # --- Two parts? -------------------------------------------------------
    if "Two parts?" not in by:
        nodes.append({
            "id": "two_parts", "name": "Two parts?",
            "type": "n8n-nodes-base.if", "typeVersion": 2,
            "position": POS["Two parts?"],
            "parameters": {"conditions": {
                "options": {"caseSensitive": True, "leftValue": "",
                            "typeValidation": "loose"},
                "conditions": [guard("two", TWO_EXPR)],
                "combinator": "and"}},
        })
        changes.append("Two parts?: new node, is there a second half to send")
    else:
        c = by["Two parts?"]["parameters"]["conditions"]["conditions"][0]
        if c.get("leftValue") != TWO_EXPR:
            c["leftValue"] = TWO_EXPR
            changes.append("Two parts?: condition updated")

    # --- Hold a beat ------------------------------------------------------
    wait_ver = by["Type for a moment"].get("typeVersion", 1.1)
    if "Hold a beat" not in by:
        nodes.append({
            "id": "hold_a_beat", "name": "Hold a beat",
            "type": "n8n-nodes-base.wait", "typeVersion": wait_ver,
            "position": POS["Hold a beat"],
            "parameters": {"amount": HOLD_AMOUNT, "unit": "seconds"},
        })
        changes.append("Hold a beat: new node, a second and a bit between the two")
    elif by["Hold a beat"]["parameters"].get("amount") != HOLD_AMOUNT:
        by["Hold a beat"]["parameters"]["amount"] = HOLD_AMOUNT
        changes.append("Hold a beat: pause updated")

    # --- Send the rest ----------------------------------------------------
    src = by["Send"]
    if "Send the rest" not in by:
        nodes.append({
            "id": "send_the_rest", "name": "Send the rest",
            "type": src["type"], "typeVersion": src["typeVersion"],
            "position": POS["Send the rest"],
            "parameters": {
                "method": "POST",
                "url": src["parameters"]["url"],
                "authentication": src["parameters"].get("authentication"),
                "genericAuthType": src["parameters"].get("genericAuthType"),
                "sendBody": True, "specifyBody": "json",
                "jsonBody": REST_BODY,
                "options": src["parameters"].get("options", {"timeout": 20000}),
            },
            "credentials": src.get("credentials", {}),
        })
        changes.append("Send the rest: new node, posts the second half")
    else:
        p = by["Send the rest"]["parameters"]
        if p.get("jsonBody") != REST_BODY:
            p["jsonBody"] = REST_BODY
            changes.append("Send the rest: body updated")

    # --- positions --------------------------------------------------------
    for name, want_pos in POS.items():
        n = by.get(name) or next((x for x in nodes if x["name"] == name), None)
        if n and n.get("position") != want_pos:
            n["position"] = want_pos
            changes.append("layout: %s moved to %s" % (name, want_pos))

    # --- the wiring -------------------------------------------------------
    want = {
        "Send": {"main": [[{"node": "Two parts?", "type": "main", "index": 0}]]},
        "Two parts?": {"main": [
            [{"node": "Hold a beat", "type": "main", "index": 0}],
            [{"node": "Show it in Open", "type": "main", "index": 0}],
        ]},
        "Hold a beat": {"main": [[{"node": "Send the rest", "type": "main", "index": 0}]]},
        "Send the rest": {"main": [[{"node": "Show it in Open", "type": "main", "index": 0}]]},
    }
    for name, spec in want.items():
        if conns.get(name) != spec:
            conns[name] = spec
            changes.append("wiring: %s" % name)

    print("workflow : %s  (%s, active=%s)"
          % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
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
        "name": live["name"], "nodes": nodes,
        "connections": conns, "settings": live.get("settings", {}),
    })
    print("")
    print("written. Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
