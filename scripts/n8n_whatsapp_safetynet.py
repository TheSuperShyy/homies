# -*- coding: utf-8 -*-
"""The safety net stops making things worse: the bot's truth checks and its last resort, 5 Oct.

    python scripts/n8n_whatsapp_safetynet.py            # dry run
    python scripts/n8n_whatsapp_safetynet.py --dump F   # dry run, plus the would-be workflow in F
                                                        # (check_whatsapp_rules.py --candidate F,
                                                        #  check_patchers_idle.py F)
    python scripts/n8n_whatsapp_safetynet.py --apply    # write it
    python scripts/n8n_whatsapp_safetynet.py --restore  # put the 5 Oct snapshot back

WHY, 5 Oct. The owner, after the live run as Assaf Clix in בר כוכבא 23
(docs/assistant/transcripts/2026-10-05-whatsapp-live-assaf.md: 1 of 9
conversations got everything): *"what are the fix that is needed for it to be
able to be consistent and not break"*. Read back, the worst of it came from the
code around the model, not from its drafts:
  - The checks blocked 21 drafts; 18 for style alone. All 4 last-resort rewrites
    were set off by checks misfiring on honest replies: "לא פתחתי" (I did NOT
    open one) read as a claim; the second pass's "בדקתי" blocked because it could
    not see the first pass's lookup; a ticket from two turns back, quoted with
    its number, blocked because no tool ran that turn.
  - 3 of the 4 rewrites sent something untrue. `Open it anyway` handed back the
    phone's newest ticket (the gate's) as "just opened"; `Say it again`, with no
    memory and no tools, told Assaf three times that a mould ticket 255-1345-26
    was open. None was. And `Second try usable?` had no false branch: a failure
    there sent nothing at all.
The owner approved the plan on 5 Oct, and chose the two fixed lines below in chat.

WHAT CHANGES, in one write:
  Reply usable?   `phantom` and `deeds` read a claim only when it is said (not
                  negated, not asked), count the first pass's tools on the second,
                  and take a ticket number as proof only when it is real (a tool
                  returned it, or it is in the last twelve messages). `links` sees
                  the first pass's link on the second. (wa_truth.py says how;
                  `deeds` is outage.py's, `links` paylink.py's.)
  Try again       carries the first pass's tools, its draft and the guards'
                  verdict on it; names a truth failure; tells the model what the
                  tools returned (retry.py's TRY_JSON).
  Claimed a ticket?   NEW. After two rejections: does what would go out claim a
                  ticket with no real number, and was none opened? Only then the
                  rescue ticket (`Open it anyway`).
  Mend the reply  NEW. No model: the first draft when its only fault was style;
                  otherwise the second, minus every sentence that claims what did
                  not happen, the ticket's real number where a false ticket claim
                  stood; when too little is left, "סליחה, משהו השתבש לי בתשובה.
                  אפשר לכתוב לי את זה שוב?". Never nothing.
  Say it again, Second try usable?   GONE (sayagain.py is retired).
  Wiring          Already retried? (yes) -> Claimed a ticket? -> (yes) Open it
                  anyway -> Mend the reply; (no) -> Mend the reply; Mend the reply
                  -> Type for a moment + Log reply, the send path as before.

WHAT IT DOES NOT TOUCH. The prompt, the inject, the tools' texts, the memory
(no epoch: none of what the memory covers moves), Send, Sort, the menu, the
small writers, the voice agents. The rescue ticket's duplicate check is in the
Edge Function (rescue_request, supabase/functions/debt-tools/index.ts) and ships
with its own deploy: until it does, a rescue can still hand back an older real
ticket of the same phone, and `Mend the reply` will say that ticket's number.

A field is rewritten only when its live text is the one this replaces (by
fingerprint); anything else means it changed since, and this refuses.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, `check_patchers_idle.py F` (it
lays the dump's nodes AND wires over live), the Claude-played replay for Try
again's note, the owner's go, `--apply`, the check again on live, every WhatsApp
patcher's dry run idle, then `--watch` from the deploy.
"""
import copy
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_untemplate as U  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
import n8n_whatsapp_outage as O  # noqa: E402
import n8n_whatsapp_paylink as PL  # noqa: E402
import n8n_whatsapp_retry as R  # noqa: E402
import wa_truth as T  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-05oct-before-safetynet.json")
PLACEHOLDER = NP.PLACEHOLDER
NL = chr(10)

GATE = "Reply usable?"
RETRIED = "Already retried?"
CLAIMED = R.CLAIMED                      # "Claimed a ticket?"
MEND = "Mend the reply"
RESCUE_CALL = "Open it anyway"
GONE = ("Say it again", "Second try usable?")
# The two removed nodes' cells: drawn clear of everything (sayagain.py moved them
# there for n8n_layout.py), so the two new ones take them.
CLAIMED_POS, MEND_POS = [1200, 540], [1440, 540]

NEED = (GATE, RETRIED, "Try again", RESCUE_CALL, "Type for a moment", "Log reply",
        "Answer the resident", "OpenRouter", "Anything newer?", "Sort")
# The patchers that refuse on live before touching anything (the documented
# baseline in check_patchers_idle.py).
BASELINE = tuple("n8n_whatsapp_%s." % n for n in ("batch", "handover", "open", "promise", "transfer", "untemplate"))

# The fingerprints (sha256[:12], W.epoch_hash) of what this replaces, read off
# live on 5 Oct before any write. `Try again` is the pin in check_whatsapp_rules.py.
OLD = {
    ("cond", "phantom"): "c5fe5ba8bd9c",
    ("cond", "deeds"): "5d9387a07e7a",
    ("cond", "links"): "1c3635c2e47d",
    ("try", None): "49907a4bd8c4",
}

PHANTOM_GUARD = T.phantom_expr()
assert PL.PHANTOM_NEW == T.PHANTOM, "paylink.py's anchor and wa_truth.py's phantom must be one regex"
assert PL.PHANTOM_NEW in PHANTOM_GUARD, "the new phantom guard must keep paylink.py's anchor"

WANT_COND = {
    "phantom": PHANTOM_GUARD,
    "deeds": O.REPLY_DEEDS["leftValue"],
    "links": PL.URL_GUARD["leftValue"],
}


def link(node):
    return {"node": node, "type": "main", "index": 0}


def claimed_node():
    return {
        "id": "claimed_ticket", "name": CLAIMED,
        "type": "n8n-nodes-base.if", "typeVersion": 2,
        "position": list(CLAIMED_POS),
        "parameters": {"conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
            "conditions": [{"id": "claimed", "leftValue": T.claimed_expr(), "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
            "combinator": "and"}, "options": {}},
    }


def mend_node():
    return {
        "id": "mend_reply", "name": MEND,
        "type": "n8n-nodes-base.set", "typeVersion": 3.4,
        "position": list(MEND_POS),
        "parameters": {"mode": "raw", "jsonOutput": T.mend_expr(), "options": {}},
    }


WANT_CONNS = {
    RETRIED: {"main": [[link(CLAIMED)], [link("Try again")]]},
    CLAIMED: {"main": [[link(RESCUE_CALL)], [link(MEND)]]},
    RESCUE_CALL: {"main": [[link(MEND)]]},
    MEND: {"main": [[link("Type for a moment"), link("Log reply")]]},
}

COMPILE_JS = ("const fs = require('fs'); const xs = JSON.parse(fs.readFileSync(0, 'utf8')); "
              "const bad = []; for (const [k, e] of xs) { try { new Function('$json', '$', "
              "'$runIndex', 'return (' + e + ');'); } catch (err) { bad.push(k + ': ' + err.message); } } "
              "console.log(JSON.stringify(bad));")


def compiles(exprs):
    """Every new expression parses as JavaScript, the way n8n will read it."""
    import check_whatsapp_rules as C
    xs = [[k, C.inner(v)] for k, v in exprs]
    r = subprocess.run(["node", "-e", COMPILE_JS], capture_output=True,
                       input=json.dumps(xs, ensure_ascii=False).encode("utf-8"))
    if r.returncode != 0:
        return ["node failed: " + r.stderr.decode("utf-8", "replace")[:300]]
    return json.loads(r.stdout.decode("utf-8"))


def snapshot(live):
    if os.path.exists(SNAPSHOT):
        return False
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    live = dict(live, staticData="<stripped: runtime state keyed by phone numbers>")
    text = json.dumps(live, ensure_ascii=False, indent=1)
    if secret:
        if secret not in text:
            sys.exit("The live workflow does not contain N8N_WEBHOOK_SECRET from .env, "
                     "so the snapshot's redaction would miss. Refusing to write it.")
        text = text.replace(secret, PLACEHOLDER)
    with open(SNAPSHOT, "w", encoding="utf-8", newline=NL) as f:
        f.write(text)
    return True


def restore():
    snap = json.load(open(SNAPSHOT, encoding="utf-8"))
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    if not secret:
        sys.exit("N8N_WEBHOOK_SECRET is not in .env; the snapshot's Sort node would "
                 "go live with a placeholder secret. Refusing.")
    body = json.loads(json.dumps(snap, ensure_ascii=False).replace(PLACEHOLDER, secret))
    W.api("PUT", "/api/v1/workflows/%s" % WORKFLOW_ID, {
        "name": body["name"], "nodes": body["nodes"],
        "connections": body["connections"], "settings": body.get("settings", {})})
    print("restored %s from %s (%d nodes)" % (WORKFLOW_ID, SNAPSHOT, len(body["nodes"])))
    print("Put the repo back too (git revert the safetynet commit): the owners' constants "
          "(outage.REPLY_DEEDS, paylink.URL_GUARD, retry.TRY_JSON) describe the new checks.")


def problems(nodes, conns):
    """What the two checks over the dump cannot see: this change adds nodes and
    wires (CONTEXT.md, "How a WhatsApp change ships", 4 Oct)."""
    by = {n["name"]: n for n in nodes}
    out = []
    for name in GONE:
        if name in by:
            out.append("%s is still on the workflow" % name)
        if name in conns:
            out.append("%s still has wires out" % name)
    for src, spec in conns.items():
        for kind, branches in spec.items():
            for branch in branches:
                for edge in branch or []:
                    if edge.get("node") in GONE:
                        out.append("%s (%s) still points at %s" % (src, kind, edge["node"]))
                    elif edge.get("node") not in by:
                        out.append("%s (%s) points at a node that does not exist: %s" % (src, kind, edge.get("node")))
    for name, want in WANT_CONNS.items():
        if conns.get(name) != want:
            out.append("%s is not wired as wanted" % name)
    ru = (conns.get(GATE) or {}).get("main") or []
    if len(ru) < 2 or [e["node"] for e in ru[1]] != [RETRIED]:
        out.append("Reply usable? (false) does not go to Already retried?")
    feeders = sorted({src for src, spec in conns.items() for b in spec.get("main", []) for e in b or []
                      if e.get("node") == MEND})
    if feeders != sorted([CLAIMED, RESCUE_CALL]):
        out.append("Mend the reply is fed by %s, not by Claimed a ticket? and Open it anyway alone" % feeders)
    return out


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    # The guard every sibling runs first: nothing here is hashed into the epoch,
    # and a live edit made while the repo's prompt has moved without its epoch is
    # how the 1 Sep buffers happened.
    W.check_memory_epoch(prompt=W.system_prompt(), inject=U.AGENT_NEW, tools=W.tools_text())

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in NEED:
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    before_layout = layout_complaints(nodes)
    changes, olds, news, exprs = [], [], [], []

    # 1. Reply usable?: phantom, deeds, links, by id, each only from the text it replaces.
    cond = by[GATE]["parameters"]["conditions"]["conditions"]
    for cid, want in WANT_COND.items():
        hits = [c for c in cond if c.get("id") == cid]
        if len(hits) != 1:
            sys.exit("REFUSING: %s has %d conditions with id %r." % (GATE, len(hits), cid))
        have = hits[0]["leftValue"]
        exprs.append(("%s / %s" % (GATE, cid), want))
        if have == want:
            continue
        if W.epoch_hash(have) != OLD[("cond", cid)]:
            sys.exit("REFUSING: %s / %s is %s, neither the one this replaces (%s) nor the new one (%s)."
                     % (GATE, cid, W.epoch_hash(have), OLD[("cond", cid)], W.epoch_hash(want)))
        hits[0]["leftValue"] = want
        olds.append(have)
        news.append(want)
        changes.append("%s / %s: %s -> %s" % (GATE, cid, W.epoch_hash(have), W.epoch_hash(want)))

    # 2. Try again: the first pass's tools, its draft and its verdict ride along.
    tp = by["Try again"]["parameters"]
    exprs.append(("Try again", R.TRY_JSON))
    if tp.get("jsonOutput") != R.TRY_JSON:
        if W.epoch_hash(tp.get("jsonOutput") or "") != OLD[("try", None)]:
            sys.exit("REFUSING: Try again is %s, neither the one this replaces (%s) nor the new one (%s)."
                     % (W.epoch_hash(tp.get("jsonOutput") or ""), OLD[("try", None)], W.epoch_hash(R.TRY_JSON)))
        olds.append(tp["jsonOutput"])
        news.append(R.TRY_JSON)
        tp["jsonOutput"] = R.TRY_JSON
        changes.append("Try again: carries first_steps, first_output and first_truth_ok; names a truth failure")

    # 3. The two new nodes, in the two old ones' cells.
    for want in (claimed_node(), mend_node()):
        have = by.get(want["name"])
        if want["name"] == CLAIMED:
            exprs.append((CLAIMED, want["parameters"]["conditions"]["conditions"][0]["leftValue"]))
        else:
            exprs.append((MEND, want["parameters"]["jsonOutput"]))
        if have is None:
            nodes.append(want)
            by[want["name"]] = want
            changes.append("add %r" % want["name"])
            continue
        for field in ("parameters", "type", "typeVersion", "position"):
            if have.get(field) != want[field]:
                have[field] = copy.deepcopy(want[field])
                changes.append("update %r %s" % (want["name"], field))

    # 4. The two old ones, gone, with every wire to or from them.
    for name in GONE:
        if name in by:
            nodes[:] = [n for n in nodes if n["name"] != name]
            del by[name]
            changes.append("remove %r" % name)
        if conns.pop(name, None) is not None:
            changes.append("remove %r's wires" % name)
    for src, spec in list(conns.items()):
        for kind, branches in spec.items():
            for i, branch in enumerate(branches):
                kept = [e for e in (branch or []) if e.get("node") not in GONE]
                if len(kept) != len(branch or []):
                    branches[i] = kept
                    changes.append("%s (%s): drop the wire to %s" % (
                        src, kind, ", ".join(sorted({e["node"] for e in branch if e.get("node") in GONE}))))

    # 5. The new wiring.
    for name, want in WANT_CONNS.items():
        if conns.get(name) != want:
            conns[name] = copy.deepcopy(want)
            changes.append("%s -> %s" % (name, " / ".join(
                "+".join(e["node"] for e in b) for b in want["main"])))

    # Checks before anything is shown as ready.
    bad = compiles(exprs)
    if bad:
        sys.exit("REFUSING: an expression does not compile:" + NL + "  " + (NL + "  ").join(bad))
    for k, e in exprs:
        if e.count("}}") != 1:
            sys.exit("REFUSING: %s has %d '}}'." % (k, e.count("}}")))
    probs = problems(nodes, conns)
    if probs:
        sys.exit("REFUSING: the would-be workflow is wrong:" + NL + "  " + (NL + "  ").join(probs))
    # Other patchers' anchors: what the edited texts held must still be there.
    # sayagain.py is retired with its node, and this script's own strings are not
    # siblings; the removed nodes' texts are deliberately not in `olds`. The
    # baseline six refuse before they reach any anchor (CONTEXT.md, "How a
    # WhatsApp change ships": nodes removed in mid-September), so theirs are moot:
    # open.py's EXEC_NEW, the old phantom's "return /\b\d{3}-.../.test(t);", is
    # one of them and goes with the old phantom.
    sib = NP.siblings()
    sib = {k: v for k, v in sib.items()
           if not k.startswith(("n8n_whatsapp_safetynet.", "n8n_whatsapp_sayagain.") + BASELINE)}
    old_all, new_all = NL.join(olds), NL.join(news)
    lost = [k for k, v in sib.items() if v in old_all and v not in new_all]
    if lost:
        sys.exit("REFUSING: the edit would break other patchers' anchors: %s" % lost)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("checks   : %d expressions compile, wiring right, %d sibling anchors intact"
          % (len(exprs), sum(1 for v in sib.values() if v in old_all)))
    if not changes:
        print("")
        print("Nothing to do. Live already matches.")
        return
    print("")
    print("changes:")
    for ch in changes:
        print("  - %s" % ch)

    worse = sorted(layout_complaints(nodes) - before_layout)
    if worse:
        sys.exit("REFUSING TO PATCH. This would introduce placement problems "
                 "that are not already there:" + NL + "    " + (NL + "    ").join(worse))

    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        NP.dump(nodes, conns, path)
        print("")
        print("dumped   : %s (the would-be workflow, secret replaced)" % path)

    if not apply:
        print("")
        print("Dry run. Re-run with --apply to write it.")
        return

    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": nodes, "connections": conns,
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    bb = {n["name"]: n for n in back["nodes"]}
    print("")
    print("written: %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    got = {c["id"]: W.epoch_hash(c["leftValue"]) for c in bb[GATE]["parameters"]["conditions"]["conditions"]}
    print("  %s: phantom %s, deeds %s, links %s" % (GATE, got.get("phantom"), got.get("deeds"), got.get("links")))
    print("  Try again %s (want %s)" % (W.epoch_hash(bb["Try again"]["parameters"]["jsonOutput"]), W.epoch_hash(R.TRY_JSON)))
    print("  %s / %s present; %s gone" % (CLAIMED, MEND, " / ".join(n for n in GONE if n not in bb)))
    left = problems(back["nodes"], back["connections"])
    print("  wiring: %s" % ("right" if not left else "; ".join(left)))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
