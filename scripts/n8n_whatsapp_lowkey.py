# -*- coding: utf-8 -*-
""""When will they call me?": a true reason, never a bare "I don't know" (19 Oct, late).

    python scripts/n8n_whatsapp_lowkey.py                       # dry run on live
    python scripts/n8n_whatsapp_lowkey.py --base F --dump G     # dry run on a dump F (norepeat's), would-be in G
    python scripts/n8n_whatsapp_lowkey.py --apply               # write it to live
    python scripts/n8n_whatsapp_lowkey.py --restore             # put the snapshot back

WHY. The stress test (docs/assistant/transcripts/2026-10-19-whatsapp-stress-test.md)
found Send's promise filter deleting the bot's honest answer to "will someone get back to
me?" in 8 turns of 7 conversations: "אם יחזרו אליך ומתי, את זה אני לא יודע" went, the
question went unanswered (one resident asked twice and never got it), and once the text
was left opening with "אבל". The owner: a "low key excuse" instead of a bare "I don't
know", then, approving twelve examples: "make sure its not templated and if the customer
ask it like twice in a row the response would depend".

WHAT CHANGES, in one write. Each text is owned elsewhere; this only carries them:
  Answer the resident   the prompt (prompt.md): one paragraph after "אתה מדווח מה הכלים
                        שלך כבר עשו" -- the true reason, from what the tools returned and
                        what is not in them (it names no reason of its own: a reason it
                        named came back in a third of the answers, 20 Oct), what is real
                        now (and for a ticket opened in this chat, that a message comes
                        here when it is closed), what he can do; no time invented; built
                        from the conversation, no sentence to copy; asked again, something
                        not yet done, and not the same reason again.
  get_request_status    its description and parameter docs, epoch 83's (n8n_whatsapp.py
                        TOOLS): the epoch covers the tools, so norepeat leaves them to the
                        later epoch, and they go with the prompt.
  Send                  promise v3 -> v4 (n8n_whatsapp_nopromise.py): "whether", under "I
                        don't know" (a subject and an adverb may stand between), a fronted
                        "I can't promise", a negated verb of saying ("אני לא יכול להגיד לך
                        שיגיעו היום"), and "that, I can't" are no longer cut; a cut never
                        leaves "להגיד לך." behind.
                        danger v3 -> v4 (n8n_whatsapp_danger.py): in an emergency, "who is
                        coming and when, I can't see from here" stays (it was the owner's
                        approved smoke example, and the danger step would have cut it), so
                        do "whether someone is already on the way, I can't know" and the
                        done message ("תגיע על זה הודעה לכאן").
  Conversation so far   MEMORY_EPOCH -> 84: the buffers hold the old bare answers.

THE ORDER WITH THE REPEAT FIX. Epoch 84 is later than norepeat's 83, so that carrier now
carries only what it alone owns (guards, Try again, Forget the draft, the status tool's
text) and this one carries the prompt and the key from either 82 or 83. Run them back to
back: `n8n_whatsapp_norepeat.py --apply`, then this. --base lets the gate see the stack
before either is live: dump norepeat's would-be workflow, then run this on top of it.

A field is rewritten only when its live text is one this replaces (by hash or by mark);
anything else means it changed since, and this refuses.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--base F --dump G`, then
`check_whatsapp_rules.py --candidate G --replay`, `check_patchers_idle.py G`, a
Claude-played replay of the inputs that reach the model (never OpenRouter), the new pins,
`--apply`, the check on live, every patcher idle, `--watch`.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_untemplate as U  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
import n8n_whatsapp_danger as D  # noqa: E402  (the emergency step, v4)
import n8n_whatsapp_norepeat as NR  # noqa: E402  (the status tool's texts, epoch 83's)
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover", "n8n-whatsapp-live-19oct-before-lowkey.json")
PLACEHOLDER = NP.PLACEHOLDER
EPOCH = 84
OLD_PROMPTS = {"9e4b0a8f158f": 82, "5cd340546742": 83}   # live today / norepeat's
OLD_KEYS = ("={{ $json.to }}-82", "={{ $json.to }}-83")
MEMORY_KEY = "={{ $json.to }}-%d"
OLD_MARK = "const pv = 'promise v3';"
OLD_DANGER = "const dv = 'danger v3';"
NL = chr(10)
KEPT = ("וכשהוא שואל מתי יחזרו אליו, מתי יגיעו, אם יקבל עדכון או אם כדאי לו להישאר בבית",
        "ומי ששואל את זה שוב לא מקבל את אותה תשובה בניסוח אחר")


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
    print("MEMORY_EPOCH in n8n_whatsapp.py still says %d and nopromise.py says v4; "
          "put the repo back too (git revert)." % W.MEMORY_EPOCH)


def load_base(path):
    """A patcher's --dump, laid out the way live comes back, secret put back in memory."""
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    d = json.loads(open(path, encoding="utf-8").read().replace(PLACEHOLDER, secret))
    return {"name": "Homies — WhatsApp bot (base %s)" % os.path.basename(path), "id": WORKFLOW_ID,
            "active": None, "nodes": d["nodes"], "connections": d["connections"], "settings": {}}


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv
    base = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else None
    if base and apply:
        sys.exit("REFUSING: --base is for the gate's dry run; --apply writes live only.")

    prompt = W.system_prompt()
    W.check_memory_epoch(prompt=prompt, inject=U.AGENT_NEW, tools=W.tools_text())
    if W.MEMORY_EPOCH < EPOCH:
        sys.exit("REFUSING: MEMORY_EPOCH is %d; this change was written for %d." % (W.MEMORY_EPOCH, EPOCH))
    later = W.MEMORY_EPOCH > EPOCH         # a later change owns the prompt and the key
    if not later:
        bad = [k for k in KEPT if k not in prompt]
        if bad:
            sys.exit("REFUSING: prompt.md does not read as this change: %s" % bad)
    if "promise v4" not in NP.MARK or "}}" in NP.FILTER:
        sys.exit("REFUSING: nopromise.py is not v4 (%r), or its filter holds a '}}'." % NP.MARK)

    live = load_base(base) if base else W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in ("Answer the resident", "Conversation so far", "Send", NR.STATUS):
        if need not in by:
            sys.exit("No %r node on the workflow -- refusing to guess." % need)

    if not base and snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    before_layout = layout_complaints(nodes)
    changes, olds, news = [], [], []

    # The prompt, by hash: live today (82) or norepeat's (83).
    agent = by["Answer the resident"]["parameters"].setdefault("options", {})
    have = agent.get("systemMessage") or ""
    if not later and have != prompt:
        old = W.epoch_hash(have)
        if old not in OLD_PROMPTS:
            sys.exit("REFUSING: the prompt is %s, none of the ones this replaces (%s) nor the "
                     "new one (%s)." % (old, ", ".join(OLD_PROMPTS), W.epoch_hash(prompt)))
        agent["systemMessage"] = prompt
        olds.append(have)
        news.append(prompt)
        changes.append("Answer the resident: prompt %s (epoch %d's) -> %s (a true reason, what is "
                       "real now, what he can do; asked again, something not yet done)"
                       % (old, OLD_PROMPTS[old], W.epoch_hash(prompt)))

    # The status tool's two texts (epoch 83's, n8n_whatsapp.py TOOLS). The epoch covers
    # the tools too, so norepeat leaves them to the later epoch: they go with the prompt.
    if not later:
        stp = by[NR.STATUS]["parameters"]
        got = NR.replace_field(stp.get("toolDescription") or "", W.tool(NR.STATUS)["description"],
                               NR.OLD_STATUS_DESC, "%s: description" % NR.STATUS, olds, news, changes,
                               "called first, with nothing; the number finds their tickets")
        if got is not None:
            stp["toolDescription"] = got
        got = NR.replace_field(stp.get("jsonBody") or "", NR.built(NR.STATUS)["parameters"]["jsonBody"],
                               NR.OLD_STATUS_BODY, "%s: parameter docs" % NR.STATUS, olds, news, changes,
                               "the building is for when they named one")
        if got is not None:
            stp["jsonBody"] = got

    # Send: the promise block, v3 -> v4, by mark.
    sp = by["Send"]["parameters"]
    body = sp.get("jsonBody") or ""
    if NP.SEND_NEW in body or NP.FILTER in body:
        pass
    elif NP.BLOCK_START in body and OLD_MARK in body:
        a = body.index(NP.BLOCK_START)
        z = body.index(NP.BLOCK_END, a)
        sp["jsonBody"] = body[:a] + NP.FILTER + body[z:]
        olds.append(body[a:z])
        news.append(NP.FILTER)
        changes.append("Send: promise v3 -> v4 (\"whether\", under \"I don't know\", is not cut)")
    else:
        sys.exit("REFUSING: Send carries neither promise v3 nor this v4. Read the live body first.")
    # Send: the emergency step, v3 -> v4, by mark ("who/whether…, I can't see" stays).
    body = sp["jsonBody"]
    if D.MARK in body:
        pass
    elif D.OLD_START in body and OLD_DANGER in body:
        a, z = body.index(D.OLD_START), body.index(D.ANCHOR)
        if not a < z:
            sys.exit("REFUSING: the danger step is not right before the emoji step.")
        sp["jsonBody"] = body[:a] + D.BLOCK + " " + body[z:]
        olds.append(body[a:z])
        news.append(D.BLOCK)
        changes.append("Send: danger v3 -> v4 (\"who/whether someone comes, I can't see from here\" "
                       "is not cut in an emergency)")
    else:
        sys.exit("REFUSING: Send carries neither danger v3 nor this v4. Read the live body first.")
    new_body = sp["jsonBody"]
    bad = D.smoke(new_body)
    if bad:
        sys.exit("REFUSING: the new Send body failed the danger smoke turns:\n  " + "\n  ".join(bad))
    if new_body.count("}}") != 1:
        sys.exit("REFUSING: the new Send body has %d '}}' -- n8n would end the expression "
                 "early." % new_body.count("}}"))
    bad = NP.smoke(new_body)
    if bad:
        sys.exit("REFUSING: the new Send body failed its smoke turns:\n  " + "\n  ".join(bad))

    # The memory: every buffer starts fresh.
    mem = by["Conversation so far"]["parameters"]
    want_key = MEMORY_KEY % W.MEMORY_EPOCH
    if not later and mem.get("sessionKey") != want_key:
        if mem.get("sessionKey") not in OLD_KEYS:
            sys.exit("REFUSING: the memory key is %r, not epoch 82 or 83." % mem.get("sessionKey"))
        changes.append("Conversation so far: memory key %s -> %s (every buffer starts fresh)"
                       % (mem.get("sessionKey"), want_key))
        mem["sessionKey"] = want_key
    if mem.get("contextWindowLength") != W.MEMORY_TURNS:
        sys.exit("REFUSING: the memory window is %r, not %d." % (mem.get("contextWindowLength"), W.MEMORY_TURNS))

    sib = NP.siblings()
    sib = {k: v for k, v in sib.items()
           if not k.startswith(("n8n_whatsapp_lowkey.", "n8n_whatsapp_nopromise."))}
    old_all, new_all = NL.join(olds), NL.join(news)
    lost = [k for k, v in sib.items() if v in old_all and v not in new_all]
    if lost:
        sys.exit("REFUSING: the edit would break other patchers' anchors: %s" % lost)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("checks   : prompt %s, Send %s, %d smoke turns right, epoch %d, %d sibling anchors intact"
          % (W.epoch_hash(prompt), NP.MARK, len(NP.SMOKE), W.MEMORY_EPOCH,
             sum(1 for v in sib.values() if v in old_all)))
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
    print("  prompt %s (want %s); memory key %s; Send carries %s: %s"
          % (W.epoch_hash(bb["Answer the resident"]["parameters"]["options"]["systemMessage"]),
             W.epoch_hash(prompt), bb["Conversation so far"]["parameters"]["sessionKey"],
             NP.MARK, NP.MARK in bb["Send"]["parameters"]["jsonBody"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
