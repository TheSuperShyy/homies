# -*- coding: utf-8 -*-
"""The menu says it is Homies: "בוקר טוב 👋 כאן הומי'ז. במה אפשר לעזור?", 8 Oct.

    python scripts/n8n_whatsapp_menuline.py            # dry run
    python scripts/n8n_whatsapp_menuline.py --dump F   # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_menuline.py --apply    # write it
    python scripts/n8n_whatsapp_menuline.py --restore  # put the 8 Oct snapshot back

WHY. The owner, after the 7 Oct test page: *"can we change the chatbot opening
message on the menu like its just hi how can i help. it should be more like
homies"*. Four samples, then *"much more simpler"*, four shorter ones, and *"i
want the 1"*: the clock's greeting, the wave, "כאן הומי'ז", the question. It names
the company and not Michael, so the 23 Sep rule stands: Michael introduces
himself after a tap (n8n_whatsapp_rep.py).

THE SENTENCE LIVES IN FOUR PLACES, and they move in one write (the 7 Sep and
23 Sep lesson, n8n_whatsapp_rep.py):
  1. Sort: `MENU.content`, what the handset gets.
  2. Answer the resident: the prompt's ownership clause quotes the tail
     (docs/features/11-whatsapp-bot/prompt.md; check_greeting() holds it to
     GREETING_TAIL). A prompt change moves the memory epoch, 77 -> 78, so the
     memory key moves too (`Conversation so far`).
  3. Send, the echo clause: a reply that copies the menu sentence gets the
     buttons. The old tail's clause stays (greet.py and rep.py own it); the new
     tail's clause goes right after it.
  4. Send, `afterMenu` (manners.py's filter): the last outbound row that is the
     menu. The OLD tail stays as well, so a chat whose last menu went out before
     the change still reads as "right after the menu".
Each owner's constant moved in the repo first (greet.SORT_WAVE, rep.CONTENT_NEW,
manners.FILTER, n8n_whatsapp.GREETING_TAIL), so their dry runs read idle once
this has shipped.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, `check_patchers_idle.py F`,
`--apply`, the check again on live, every WhatsApp patcher's dry run idle.
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
import n8n_whatsapp_manners as M  # noqa: E402
import n8n_whatsapp_greet as G  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-08oct-before-menuline.json")
PLACEHOLDER = NP.PLACEHOLDER
NL = chr(10)
OLD_EPOCH = 77
MEMORY_KEY = "={{ $json.to }}-%d"

# 1. Sort
SORT_OLD = 'content: HELLO + " 👋 במה אפשר לעזור?"'
SORT_NEW = G.SORT_WAVE
# 3. Send, the echo clause (new tail after the old one)
NEW_TAIL_RE = "/👋 כאן הומי'ז[.] במה אפשר לעזור[?]/"
# The leading space keeps this anchor out of afterMenu's "lastOut.indexOf(...) !== -1 || "
# below, which ends in the same letters; manners.py refuses a filter holding any *_OLD.
ECHO_OLD = " " + G.SEND_ECHO
ECHO_NEW = " " + G.SEND_ECHO + NEW_TAIL_RE + ".test(t) || "
# 4. Send, afterMenu (manners.FILTER carries the new statement)
AFTER_OLD = "|| lastOut.indexOf('👋 במה אפשר לעזור?') !== -1;"
AFTER_NEW = "|| lastOut.indexOf('👋 במה אפשר לעזור?') !== -1 || " + NEW_TAIL_RE + ".test(lastOut);"

assert SORT_NEW.endswith('"') and W.GREETING_TAIL in SORT_NEW
assert ("const afterMenu = /במה אפשר לעזור/.test(String(S.last_bot || '')) " + AFTER_NEW) in M.FILTER, \
    "manners.FILTER and this carrier disagree on the afterMenu statement"


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
    print("The repo still says epoch %d and the new tail; put it back too (git revert)." % W.MEMORY_EPOCH)


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv
    prompt = W.system_prompt()                     # check_greeting(): the prompt quotes GREETING_TAIL
    W.check_memory_epoch(prompt=prompt, inject=U.AGENT_NEW, tools=W.tools_text())
    if W.MEMORY_EPOCH < OLD_EPOCH + 1:
        sys.exit("REFUSING: this carrier moves the epoch %d -> %d; the repo says %d."
                 % (OLD_EPOCH, OLD_EPOCH + 1, W.MEMORY_EPOCH))
    # A later epoch owns the prompt and the memory key (18 Oct: askfirst, 79). Sort
    # and Send stay this carrier's, and check_greeting() still holds the tail.
    later = W.MEMORY_EPOCH > OLD_EPOCH + 1
    old_prompt = prompt.replace(W.GREETING_TAIL, W.GREETING_TAIL_BEFORE)

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in ("Sort", "Send", "Answer the resident", "Conversation so far"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)
    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    before_layout = layout_complaints(nodes)
    changes = []

    # 1. Sort
    code = by["Sort"]["parameters"].get("jsCode") or ""
    if SORT_NEW not in code:
        if code.count(SORT_OLD) != 1:
            sys.exit("REFUSING: Sort carries `%s` %d times, not once." % (SORT_OLD, code.count(SORT_OLD)))
        by["Sort"]["parameters"]["jsCode"] = code.replace(SORT_OLD, SORT_NEW, 1)
        changes.append("Sort: the menu says \"כאן הומי'ז\" before the question")

    # 2. the prompt and the memory key
    opts = by["Answer the resident"]["parameters"].setdefault("options", {})
    have = opts.get("systemMessage") or ""
    if not later and have != prompt:
        if have != old_prompt:
            sys.exit("REFUSING: the live prompt is neither the repo's before (%s) nor after (%s); it is %s."
                     % (W.epoch_hash(old_prompt), W.epoch_hash(prompt), W.epoch_hash(have)))
        opts["systemMessage"] = prompt
        changes.append("Answer the resident: the ownership clause quotes the new tail (prompt %s -> %s)"
                       % (W.epoch_hash(old_prompt), W.epoch_hash(prompt)))
    mem = by["Conversation so far"]["parameters"]
    if not later and mem.get("sessionKey") != MEMORY_KEY % W.MEMORY_EPOCH:
        if mem.get("sessionKey") != MEMORY_KEY % OLD_EPOCH:
            sys.exit("REFUSING: the memory key is %r, not epoch %d." % (mem.get("sessionKey"), OLD_EPOCH))
        mem["sessionKey"] = MEMORY_KEY % W.MEMORY_EPOCH
        changes.append("Conversation so far: memory epoch %d -> %d (every buffer starts fresh)"
                       % (OLD_EPOCH, W.MEMORY_EPOCH))

    # 3 and 4. Send
    body = by["Send"]["parameters"].get("jsonBody") or ""
    if ECHO_NEW not in body:
        if body.count(ECHO_OLD) != 1:
            sys.exit("REFUSING: Send carries the echo clause %d times, not once." % body.count(ECHO_OLD))
        body = body.replace(ECHO_OLD, ECHO_NEW, 1)
        changes.append("Send: a reply that copies the new menu sentence gets the buttons, as the old one did")
    if AFTER_NEW not in body:
        if body.count(AFTER_OLD) != 1:
            sys.exit("REFUSING: Send carries the afterMenu statement %d times, not once." % body.count(AFTER_OLD))
        body = body.replace(AFTER_OLD, AFTER_NEW, 1)
        changes.append("Send: the last outbound row reads as the menu with either tail")
    if body.count("}}") != 1:
        sys.exit("REFUSING: the new Send body has %d '}}'." % body.count("}}"))
    if M.FILTER not in body:
        sys.exit("REFUSING: the new Send body does not carry manners.FILTER as the repo has it.")
    by["Send"]["parameters"]["jsonBody"] = body

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
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
        sys.exit("REFUSING TO PATCH. New placement problems:" + NL + "    " + (NL + "    ").join(worse))
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
    sb = bb["Send"]["parameters"]["jsonBody"]
    print("")
    print("written: %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  Sort says the new menu: %s" % (SORT_NEW in bb["Sort"]["parameters"]["jsCode"]))
    print("  prompt %s, memory key %s" % (
        W.epoch_hash(bb["Answer the resident"]["parameters"]["options"]["systemMessage"]),
        bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("  Send: echo %s, afterMenu %s, manners filter %s, '}}' %d"
          % (ECHO_NEW in sb, AFTER_NEW in sb, M.FILTER in sb, sb.count("}}")))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
