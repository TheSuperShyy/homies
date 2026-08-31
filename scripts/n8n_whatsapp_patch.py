# -*- coding: utf-8 -*-
r"""Edit the LIVE WhatsApp workflow in place, without replacing it.

    python scripts/n8n_whatsapp_patch.py            # show the diff, change nothing
    python scripts/n8n_whatsapp_patch.py --apply    # write it

WHY THIS EXISTS, AND WHY IT IS NOT n8n_whatsapp.py

`n8n_whatsapp.py` builds the whole workflow and pushes it with a PUT, and a PUT
is a replace. Since the Chatwoot cutover on 21 Aug the live workflow has carried
nodes that script does not build -- the human handback, the promise backstop,
the tap transfer, the two typing-indicator Waits -- all applied through the REST
API and never brought back. On 31 Aug that was 35 live nodes against 21 built,
and the script's own guard refuses the push rather than delete fourteen of them.

That guard is right, and the correct long-term fix is to bring the script up to
date so it is the source of truth again. This is not that. This is the narrow
alternative: read the live workflow, change the few things that were asked for,
leave every other byte exactly as it was found, and write it back.

WHAT IT CHANGES, AND NOTHING ELSE

  1. Deletes the nodes `Dead end reply?` and `Options again`, and every
     connection into or out of them. That is the follow-up menu: an If that
     asked whether the outgoing reply contained a question mark, and sent the
     four-row options list after every reply that did not -- so a ticket number
     was always followed by a dropdown, and so was a resident who declined a
     ticket. Removed 31 Aug; the bot closes its own conversations now.

  2. Replaces the agent's systemMessage with the prompt as the repo has it,
     read through n8n_whatsapp.system_prompt() so there is one parser and not
     two.

  3. Sets options.temperature on the OpenRouter node. It carried only maxTokens,
     so the model ran at Google's default. See the TEMPERATURE comment in
     n8n_whatsapp.py for why that is suspected in the Hebrew spelling feedback.

IT IS IDEMPOTENT. Run it twice and the second run reports nothing to do. That
matters more than usual here, because the thing it is editing is live and the
obvious way to check whether it worked is to run it again.

WHAT IT DELIBERATELY LEAVES ALONE

The live `Sort` node still builds a `followup` object that now nothing reads.
It is dead weight, not a fault, and the live Sort is the Chatwoot-envelope
version that this repo does not have a copy of -- editing 16KB of JavaScript
nobody has in source to delete an unused field is a worse trade than leaving it.
It goes when the script catches up.

A backup of live before the first run is in
docs/handover/n8n-whatsapp-live-31aug-before-followup-removal.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n8n_whatsapp as W

# The two nodes that made up the follow-up menu. Named rather than matched by
# shape, because a rule that says "any If feeding a Set feeding Send menu" would
# one day match something else on a workflow this script cannot see in source.
DROP = ["Dead end reply?", "Options again"]


def strip_connections(conns, dropped):
    """Remove the dropped nodes as connection sources and as targets.

    n8n's shape is {source: {type: [[{node, type, index}, ...], ...]}}, so a
    node is deleted in two places and forgetting the second leaves a connection
    pointing at a node that is not there -- which the editor renders as a broken
    arrow and the runtime ignores silently.
    """
    out = {}
    for src, types in conns.items():
        if src in dropped:
            continue
        new_types = {}
        for kind, branches in types.items():
            new_types[kind] = [
                [t for t in branch if t.get("node") not in dropped]
                for branch in branches
            ]
        out[src] = new_types
    return out


def layout_complaints(nodes):
    """The lines n8n_layout.check() would raise, as a set, or empty."""
    try:
        W.check(nodes)
    except W.LayoutError as exc:
        return {l.strip() for l in str(exc).splitlines()[1:] if l.strip()}
    return set()


def new_layout_complaints(before, after):
    """Only what the patch itself introduced."""
    return sorted(layout_complaints(after) - layout_complaints(before))


def main():
    apply = "--apply" in sys.argv

    found = W.find()
    if not found:
        sys.exit("\nREFUSING TO PATCH. This would introduce placement "
                 "problems that are not already there:\n    %s"
                 % "\n    ".join(worse))

    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    # PUT takes only these four keys; sending id/active/tags back is a 400.
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"],
        "nodes": kept,
        "connections": conns,
        "settings": live.get("settings", {}),
    })
    print("\nwritten. Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
