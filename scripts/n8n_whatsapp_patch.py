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
    pointing at a node that is not there -- which the editor draws as a broken
    arrow and the runtime ignores silently.
    """
    out = {}
    for src, types in conns.items():
        if src in dropped:
            continue
        out[src] = {
            kind: [[t for t in branch if t.get("node") not in dropped]
                   for branch in branches]
            for kind, branches in types.items()
        }
    return out


def layout_complaints(nodes):
    """The lines n8n_layout.check() would raise, as a set. Empty if it passes."""
    try:
        W.check(nodes)
    except W.LayoutError as exc:
        return {line.strip() for line in str(exc).splitlines()[1:] if line.strip()}
    return set()


def main():
    apply = "--apply" in sys.argv

    found = W.find()
    if not found:
        sys.exit("No workflow named %r on the instance." % W.WF_NAME)
    live = W.api("GET", "/api/v1/workflows/%s" % found["id"])

    nodes = live["nodes"]
    conns = live["connections"]
    changes = []

    # 1. the follow-up menu
    present = [n["name"] for n in nodes if n["name"] in DROP]
    if present:
        changes.append("remove nodes: %s" % ", ".join(present))
    kept = [n for n in nodes if n["name"] not in DROP]

    before = json.dumps(conns, sort_keys=True, ensure_ascii=False)
    conns = strip_connections(conns, set(DROP))
    if json.dumps(conns, sort_keys=True, ensure_ascii=False) != before:
        changes.append("rewire: drop every connection touching those nodes")

    # 2. the prompt
    prompt = W.system_prompt()
    W.check_greeting(prompt)
    # And the buffers this prompt would be landing on top of. See
    # check_memory_epoch: an old buffer is a worked example of the behaviour
    # being replaced, argued at close range, and it wins.
    W.check_memory_epoch(prompt=prompt)
    agent = next((n for n in kept if n["type"].endswith("langchain.agent")), None)
    if agent is None:
        sys.exit("No agent node on the live workflow -- refusing to guess.")
    old_prompt = agent["parameters"].get("options", {}).get("systemMessage", "")
    if old_prompt != prompt:
        changes.append("prompt: %d chars -> %d" % (len(old_prompt), len(prompt)))
        agent["parameters"].setdefault("options", {})["systemMessage"] = prompt

    # 3. the temperature
    model = next((n for n in kept if n["type"].endswith("lmChatOpenRouter")), None)
    if model is None:
        sys.exit("No OpenRouter node on the live workflow -- refusing to guess.")
    opts = model["parameters"].setdefault("options", {})
    if opts.get("temperature") != W.TEMPERATURE:
        changes.append("temperature: %s -> %s"
                       % (opts.get("temperature", "unset"), W.TEMPERATURE))
        opts["temperature"] = W.TEMPERATURE

    # 4. the memory epoch and window
    #
    # This node had no owner until 1 Sep, which is exactly why the epoch went
    # three deploys without being bumped: the prompt and the temperature were
    # synced from the repo on every run and the session key was only ever
    # changed by hand, in the editor, by somebody who remembered. It is synced
    # here now, beside the two other fields that decide how the bot behaves.
    mem = next((n for n in kept if n["type"].endswith("memoryBufferWindow")), None)
    if mem is None:
        sys.exit("No memory node on the live workflow -- refusing to guess.")
    mp = mem["parameters"]
    want_key = "={{ $json.to }}-%d" % W.MEMORY_EPOCH
    if mp.get("sessionKey") != want_key:
        changes.append("memory epoch: %s -> %s (every existing buffer is "
                       "abandoned)" % (mp.get("sessionKey"), want_key))
        mp["sessionKey"] = want_key
    if mp.get("contextWindowLength") != W.MEMORY_TURNS:
        changes.append("memory window: %s -> %s exchanges"
                       % (mp.get("contextWindowLength"), W.MEMORY_TURNS))
        mp["contextWindowLength"] = W.MEMORY_TURNS

    print("workflow : %s  (%s, active=%s)"
          % (W.WF_NAME, live["id"], live.get("active")))
    print("nodes    : %d live -> %d after" % (len(nodes), len(kept)))
    if not changes:
        print("")
        print("Nothing to do. Live already matches.")
        return
    print("")
    print("changes:")
    for c in changes:
        print("  - %s" % c)

    # PLACEMENT IS CHECKED RELATIVELY, NOT ABSOLUTELY, and that is deliberate.
    #
    # n8n_layout.check() raises on the live workflow as it stands: seven pairs of
    # overlapping nodes, and every node off the grid, all of it from the hand
    # edits that put those fourteen nodes there in the first place. That is a
    # real complaint and somebody should answer it, but it is not this patch's to
    # answer -- failing here would mean no surgical edit can ever be made to this
    # workflow until an unrelated tidy-up happens first.
    #
    # So the bar is: do not make it worse. Any complaint the patched workflow
    # raises that the live one did not is one this patch caused, and that fails.
    worse = sorted(layout_complaints(kept) - layout_complaints(nodes))
    if worse:
        sys.exit("REFUSING TO PATCH. This would introduce placement problems "
                 "that are not already there:\n    " + "\n    ".join(worse))

    if not apply:
        print("")
        print("Dry run. Re-run with --apply to write it.")
        return

    # PUT takes only these four keys; sending id/active/tags back is a 400.
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"],
        "nodes": kept,
        "connections": conns,
        "settings": live.get("settings", {}),
    })
    print("")
    print("written. Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
