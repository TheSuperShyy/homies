# -*- coding: utf-8 -*-
"""Make the promise backstop actually fire, and record what it rescued.

    python scripts/n8n_whatsapp_promise.py            # dry run
    python scripts/n8n_whatsapp_promise.py --apply    # write it

WHY
`Promised a transfer, made none?` exists so that a reply telling a resident
their message is going to a person is true when it is sent. On 1 Sep a resident
was trapped in a lift with a dead emergency button, was told
`אני מעביר את הפנייה שלכם לצוות שלנו באופן מיידי`, and across four turns
`transfer_to_human` was never called once. Nothing was recorded. The guard did
not fire, and it has never fired.

THREE THINGS ARE WRONG WITH IT, AND THEY COMPOUND

1. It asks the tool node whether it ran:

       try { if ($('transfer_to_human').isExecuted) return false; } catch (e) {}

   `isExecuted` is spuriously true — it describes the node being reachable, not
   having run — so this returns false on every execution and the node is dead
   code. Exactly the defect removed from the phantom-ticket guard on 1 Sep, and
   there is no working way to ask: `.all()` throws from inside an If, which
   makes a guard fire on everything. **Do not put either back.** The promise is
   in the reply, and the reply is what this now decides on.

   The cost of deciding on the promise alone is one spare `call_outcomes` row
   when a transfer really was made. Nothing else: the emergency backstop checks
   for a prior request on the interaction before writing a ticket, and the
   resident still receives the model's own words, because `Transfer it anyway`
   passes the reply on to `Carry the reply`.

2. Its regex is an exact-phrase list in a language that inflects. It covers
   `אני מעביר` and misses `העברתי` and `העברנו`, which the bot writes at least
   as often. Widened to the verb plus a destination — and deliberately kept to
   the FIRST PERSON, because the passive `הועברה לטיפול` is what a status reply
   says about a ticket that was passed on weeks ago, and matching it would fire
   the guard on correct status answers. Same false-positive class as the 27 Aug
   phantom-guard regression.

3. `Transfer it anyway` hands over with `reason: 'caller_request'`, and the
   emergency backstop in debt-tools writes its `needs_review` ticket only for
   `emergency` — so an emergency rescued by this guard leaves no ticket. Taking
   the reason from the reply was tried and measured, and it wrote TWO tickets
   for one lift call. See the comment on RESCUE_BODY: it stays
   `caller_request`, and the gap is recorded rather than papered over. The
   resident's message is now sent with it either way.

Idempotent. Running it twice reports nothing to do.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"

# --------------------------------------------------------------------------
# 1. The condition.
#
# Every brace that would touch another has a space in it: n8n closes an
# expression on the first `}}` it meets, so `}})()` truncates the whole thing
# and the node reports "invalid syntax". Backslashes are single, in a raw
# string, so they reach n8n as the regex escapes they are meant to be.
# --------------------------------------------------------------------------
CONDITION = (
    r"={{ (() => {"
    r" const t = String($json.output || '');"
    # First person only. `הועברה`/`הועבר` are what a STATUS answer says about
    # somebody's existing ticket, and firing on those would hand over a
    # resident who only asked how their request was getting on.
    r" const said = /(אני |אנחנו )?(מעביר|מעבירה|מעבירים|העברתי|העברנו)/.test(t);"
    r" if (!said) return false;"
    # A verb on its own is not a promise — `מעביר` turns up in plenty of
    # sentences that are not about handing this conversation to anybody.
    r" if (!/(לצוות|לנציג|לטיפול|לעמית)/.test(t)) return false;"
    # An OFFER is not a claim. `רוצים שאעביר את זה?` asks permission and
    # nothing has happened yet, which is the one case where the reply is
    # honest and the guard would make it a lie.
    r" if (/(שאעביר|האם להעביר|רוצים שנעביר|אם תרצו)/.test(t)) return false;"
    r" return true;"
    r" } )() }}"
)

# The two `isExecuted` clauses, removed rather than replaced.
EXEC_OLDS = [
    " try { if ($('transfer_to_human').isExecuted) return false; } catch (e) {}",
    " try { if ($('open_request').isExecuted) return false; } catch (e) {}",
]

# --------------------------------------------------------------------------
# 2. The rescue call itself.
#
# `description` is the resident's own message, so the row a person reads says
# what happened rather than nothing.
#
# `reason` STAYS `caller_request`, AND THAT IS A DELIBERATE GAP. It was briefly
# derived from the urgency in the model's own reply, so that an emergency
# rescued here would reach the ticket-writing backstop in debt-tools. Measured
# live, that produced TWO tickets for one lift call: the guard fires on the
# promise alone, so on the ordinary path the model's own `transfer_to_human`
# and this rescue both run in the same execution, both forward asynchronously
# through the n8n router, and both reach the backstop's
# `select ... where interaction_id` before either insert lands. Neither sees a
# prior request and both write.
#
# That breaks "one incident, one row", which was fixed hours earlier the same
# day, so it came straight back out. Closing it properly needs the backstop's
# check-and-insert to be atomic — a partial unique index on `interaction_id`
# where `oxs_ref = 'partial:emergency_transfer'`, and the conflict swallowed —
# and that is a schema change, not a wording fix. Until then: a handover
# rescued here is recorded and reaches a person, and an emergency that the
# model never transferred at all still leaves no ticket.
# --------------------------------------------------------------------------
RESCUE_BODY = (
    "={{ JSON.stringify({ message: { call: {"
    " id: 'wa:' + $('Sort').first().json.to,"
    " assistantOverrides: { variableValues:"
    " { phone: $('Sort').first().json.to } } },"
    " toolCalls: [{ id: 'wa-backstop', function: { name: 'transfer_to_human',"
    " arguments: { reason: 'caller_request',"
    " description: String($('Sort').first().json.in_text || '')"
    " } } }] } }) }}"
)


def main():
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    for need in ("Promised a transfer, made none?", "Transfer it anyway"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    changes = []

    guard = by["Promised a transfer, made none?"]
    conds = guard["parameters"]["conditions"]["conditions"]
    for c in conds:
        if c.get("id") != "promise":
            continue
        lv = str(c.get("leftValue", ""))
        if lv != CONDITION:
            if any(o in lv for o in EXEC_OLDS):
                changes.append("Promised a transfer, made none?: stop asking the "
                               "tool node whether it ran (isExecuted is always "
                               "true, so this guard has never fired)")
            changes.append("Promised a transfer, made none?: match the verb and a "
                           "destination instead of four exact phrases, and let an "
                           "offer through")
            c["leftValue"] = CONDITION

    rescue = by["Transfer it anyway"]
    if rescue["parameters"].get("jsonBody") != RESCUE_BODY:
        changes.append("Transfer it anyway: send the resident's message with "
                       "the rescued handover, so the row says what happened")
        rescue["parameters"]["jsonBody"] = RESCUE_BODY

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

    # PUT takes only these four keys; sending id/active/tags back is a 400.
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": live["nodes"],
        "connections": live["connections"], "settings": live.get("settings", {}),
    })
    print("")
    print("written. Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
