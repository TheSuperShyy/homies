# -*- coding: utf-8 -*-
"""The third row says "talk to a representative", and the opener follows the clock.

    python scripts/n8n_whatsapp_rep.py            # dry run
    python scripts/n8n_whatsapp_rep.py --apply    # write it

WHY, the owner on 23 Sep: *"it should be talk with a representative and the bot
will be the representative, also the starting conversation should always be a
greeting like good morning, good afternoon, good evening."*

So two changes and one thing that deliberately does NOT change: nothing pages a
person. The 13 Sep decision stands -- that is the day `לדבר עם נציג` BECAME
`משהו אחר`, because the owner wanted the bot to handle everything rather than
hand residents on. The label is coming back without the handover behind it,
which is honest here and nowhere else: the prompt has cast the bot as נציג
השירות since the beginning, and a resident asking for a representative gets
one.

THE TITLE IS THE ROUTING KEY. Chatwoot throws the button's id away and forwards
only its TITLE, so `MENU.items` and `TAP_KIND` are one table in two halves and
must move in the same write. Live `Sort` says it in its own comment: *"reword
one there and the flow it starts silently stops starting, falling through to
the model instead of failing loudly."* `value: "other"` never moves; nothing
downstream reads it (`tappedOpen` tests `open`, `tappedHuman` tests `human`).

THE GREETING, AND THE INVARIANT TAIL. Only the first word varies. Everything
from the wave onwards -- `👋 כאן מיכאל מהומי'ז. במה אפשר לעזור?` -- is fixed,
and every guard that used to match the whole sentence is re-anchored on that
tail here and in the repo: Send's echo test below, `check_greeting()`, and the
prompt's ownership clause. `n8n_whatsapp_rename.py` recorded the trap this
avoids: *"Rename the greeting without them and the guard silently stops firing
-- the protection reads as present and is not."*

Hour in plain JS, not Luxon: `Sort` is a Code node, and the workflow carries no
timezone setting, which is why the agent's inject spells out `setZone` too. The
cut-offs are the ones both voice agents use (`prompt_probe.py`): before 05:00
שלום, to 12:00 בוקר טוב, to 17:00 צהריים טובים, then ערב טוב.

Surgical, like every live edit here: read the workflow, change only the named
strings, write the rest back byte for byte. `n8n_whatsapp.py --apply` remains
the wrong way to ship to this workflow.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n8n_whatsapp as W  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"

# --------------------------------------------------------------------------
# 1. Sort: the third row, and the routing table that reads its title.
# --------------------------------------------------------------------------
# The column each row's `value:` sits at is kept, because the next person to
# read this file reads it as a table.
ROW_OLD = '{ title: "משהו אחר",         value: "other" },'
ROW_NEW = '{ title: "לדבר עם נציג",      value: "other" },'

TAP_OLD = '"משהו אחר":          "other",'
TAP_NEW = '"לדבר עם נציג":       "other",'

# --------------------------------------------------------------------------
# 2. Sort: the opener follows the clock.
# --------------------------------------------------------------------------
CONTENT_OLD = (
    'const MENU = {\n'
    '  content: "היי 👋 כאן מיכאל מהומי\'ז. במה אפשר לעזור?",'
)
CONTENT_NEW = (
    '// 23 Sep: the opening word follows the clock in Israel, as both voice\n'
    '// agents have since 22 Sep. ONLY the first word moves -- everything from\n'
    '// the wave on is the invariant tail that Send\'s echo guard and\n'
    '// check_greeting() anchor on. hourCycle h23 because h12/hour12:false\n'
    '// returns 24 for midnight on some engines.\n'
    'const HH = Number(new Intl.DateTimeFormat(\'en-GB\', '
    '{ hour: \'2-digit\', hourCycle: \'h23\', timeZone: \'Asia/Jerusalem\' })'
    '.format(new Date()));\n'
    'const HELLO = HH < 5 ? \'שלום\' : HH < 12 ? \'בוקר טוב\' '
    ': HH < 17 ? \'צהריים טובים\' : \'ערב טוב\';\n'
    'const MENU = {\n'
    '  content: HELLO + " 👋 כאן מיכאל מהומי\'ז. במה אפשר לעזור?",'
)

# --------------------------------------------------------------------------
# 3. Send: the echo guard drops the first word and keeps the tail.
# --------------------------------------------------------------------------
# Narrow on purpose. The live literal is single-quoted JS with an escaped
# apostrophe further along; touching only the head of it leaves that escape
# exactly as found -- the 17 Sep outage was that character, unescaped.
ECHO_OLD = "t.indexOf('היי 👋 כאן"
ECHO_NEW = "t.indexOf('👋 כאן"

# --------------------------------------------------------------------------
# 4. Send: the opener SHAPE learns the three clock greetings.
# --------------------------------------------------------------------------
# `OPENER_RE` in n8n_whatsapp_retry.py is one source with two live uses -- the
# `opener` guard in `Reply usable?` and Send's third menu rule -- and it only
# ever listed היי / הי / שלום / שלום רב / אהלן. A reply that opens בוקר טוב
# would stop counting as "the turn the resident has already had", so the guard
# would read as present and protect nothing. The alternation is the narrowest
# honest anchor; retry.py's constant moved with it, and it goes idle again once
# this is applied.
OPENER_OLD = "(היי|הי|שלום|שלום רב|אהלן)[,!.]?"
OPENER_NEW = "(היי|הי|שלום|שלום רב|אהלן|בוקר טוב|צהריים טובים|ערב טוב)[,!.]?"

# --------------------------------------------------------------------------
# 5. Send: the rows the handset actually draws.
# --------------------------------------------------------------------------
# THE THIRD COPY, and the one that would have broken this silently. `Sort`
# holds the table twice (MENU + TAP_KIND) and `Send` holds the buttons it
# draws. Changing the first two alone leaves a handset showing משהו אחר while
# the routing table waits for לדבר עם נציג, and a tap then matches nothing --
# no error, just a resident whose button stopped working. Caught by
# n8n_whatsapp_menu.py refusing after the first apply, which is what that
# refusal is for.
SEND_ROW_OLD = "{ title: 'משהו אחר', value: 'other' }"
SEND_ROW_NEW = "{ title: 'לדבר עם נציג', value: 'other' }"


def main():
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    for need in ("Sort", "Send"):
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

    edit("Sort", "jsCode", ROW_OLD, ROW_NEW,
         "Sort: the third row reads לדבר עם נציג")
    edit("Sort", "jsCode", TAP_OLD, TAP_NEW,
         "Sort: the tap routing table follows the new title")
    edit("Sort", "jsCode", CONTENT_OLD, CONTENT_NEW,
         "Sort: the opener greets by the hour in Israel")
    edit("Send", "jsonBody", ECHO_OLD, ECHO_NEW,
         "Send: the echo guard anchors on the invariant tail")
    edit("Send", "jsonBody", OPENER_OLD, OPENER_NEW,
         "Send: the opener shape counts בוקר טוב / צהריים טובים / ערב טוב")
    edit("Send", "jsonBody", SEND_ROW_OLD, SEND_ROW_NEW,
         "Send: the drawn button reads לדבר עם נציג")

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
