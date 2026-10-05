# -*- coding: utf-8 -*-
"""Straight answers: who Michael is, danger, "when?", "anything else?", earlier
tickets and the balance check -- fixes 4 and 5 of the owner's five, 5 Oct.

    python scripts/n8n_whatsapp_straight.py            # dry run
    python scripts/n8n_whatsapp_straight.py --dump F   # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_straight.py --apply    # write it
    python scripts/n8n_whatsapp_straight.py --restore  # put the 5 Oct snapshot back

WHY, 5 Oct. The live run as Assaf Clix (1 of 9 conversations got everything,
docs/assistant/transcripts/2026-10-05-whatsapp-live-assaf.md). What the prompt
itself produced:
  - "אני מיכאל, נציג שירות אמיתי" and "a large language model, trained by Google":
    the prompt called him "נציג השירות" and said whoever asks for a rep "is
    waiting for a person to answer him", and said nothing about being asked.
  - "Anything else?" after nearly every reply, even to a tenant still asking
    "when?": four places asked for it every time.
  - "Up to 4 hours / 3 business days", given as a promise: a line in the facts.
  - "I have no way of knowing what happened with your earlier report" while
    255-1341-26 was open: the paragraph on what was SENT before was read as
    covering earlier tickets.
  - The balance asked for again and again ("I already told you twice").
The owner's decisions, in chat, are in prompt.md's "5 Oct" section.

WHAT CHANGES, in one write:
  Answer the resident   the prompt, by hash (prompt.md, the System prompt section).
  get_balance           its description (n8n_whatsapp.py TOOLS): ask once, explain
                        once, a refusal is a team note; any country's number.
  Conversation so far   MEMORY_EPOCH 73 -> 74: every buffer holds "anything else?"
                        endings and the 4-hour answer.
The Edge Function's half (typedPhoneOf, the lookups) shipped as v116 the same day.

A field is rewritten only when its live text is the one this replaces (by
hash); anything else means it changed since, and this refuses. A later epoch
owns the prompt and the key: then this is idle.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, `check_patchers_idle.py F`, a
Claude-played replay of the inputs that reach the model (never OpenRouter), the
new pins, `--apply`, the check on live, every patcher idle, `--watch`.
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
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-05oct-before-straight.json")
PLACEHOLDER = NP.PLACEHOLDER
OLD_EPOCH = 73
OLD_PROMPT = "65c56f9d9c40"     # EPOCH_COVERS["prompt"] at epoch 73
OLD_BALANCE = "71748fa397ba"    # get_balance's live toolDescription before this
MEMORY_KEY = "={{ $json.to }}-%d"
NL = chr(10)

# The prompt must hold the new fragments and none of the old ones, or this refuses.
GONE = ("אתה מיכאל, נציג השירות של הומי'ז",
        "ומי שביקש נציג מחכה שבן אדם יענה לו",
        "ומשם אתה שואל במה עוד לעזור",
        "ומציע לעזור בעוד משהו",
        "והצעה לעזור בעוד משהו",
        "אתה מציע לעזור בעוד משהו, במילים שלך",
        "ושהצוות יודע, וזה כל מה שיש לך",
        "**זמני טיפול:**")
KEPT = ("אתה מיכאל מצוות השירות של הומי'ז",
        "אתה העוזר הדיגיטלי בצוות השירות של הומי'ז",
        "תאריך מדויק אין לך",
        # With its number (5 Oct, the Claude-played check): without one, fix 1's
        # phantom guard sends "פתחתי לך קריאה דחופה, וזה הדבר היחיד…" back.
        "שפתחת לו קריאה דחופה, עם המספר שלה, ושזה הדבר היחיד שאתה יכול לעשות מכאן",
        "\"יש עוד משהו?\" שואלים רק כשהעניין שלו באמת נגמר",
        "קריאה שהוא דיווח עליה בעבר היא דבר אחר, ואותה בודקים")
BALANCE_KEPT = ("ask once", "explain once", "notify_team", "any country")


def node_of(by, name):
    if name not in by:
        sys.exit("No %r node on the live workflow -- refusing to guess." % name)
    return by[name]


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
    print("MEMORY_EPOCH in n8n_whatsapp.py still says %d; the restored key is -%d and the "
          "prompt is %s. Put the repo back too (git revert)." % (W.MEMORY_EPOCH, OLD_EPOCH, OLD_PROMPT))


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    prompt = W.system_prompt()
    balance = W.tool("get_balance")["description"]
    W.check_memory_epoch(prompt=prompt, inject=U.AGENT_NEW, tools=W.tools_text())
    if W.MEMORY_EPOCH < OLD_EPOCH + 1:
        sys.exit("REFUSING: MEMORY_EPOCH is %d; this change was written for %d -> %d."
                 % (W.MEMORY_EPOCH, OLD_EPOCH, OLD_EPOCH + 1))
    later = W.MEMORY_EPOCH > OLD_EPOCH + 1     # a later change owns the prompt and the key
    if not later:
        bad = [g for g in GONE if g in prompt] + [k for k in KEPT if k not in prompt]
        bad += [k for k in BALANCE_KEPT if k not in balance.lower()]
        if bad:
            sys.exit("REFUSING: prompt.md / get_balance do not read as this change: %s" % bad)

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in ("Answer the resident", "Conversation so far", "get_balance"):
        node_of(by, need)

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    before_layout = layout_complaints(nodes)
    changes, olds, news = [], [], []

    # The prompt: by hash, the way MEMORY_EPOCH covers it.
    agent = by["Answer the resident"]["parameters"].setdefault("options", {})
    have = agent.get("systemMessage") or ""
    if not later and have != prompt:
        if W.epoch_hash(have) != OLD_PROMPT:
            sys.exit("REFUSING: the live prompt is %s, neither the one this replaces (%s) "
                     "nor the new one (%s)." % (W.epoch_hash(have), OLD_PROMPT, W.epoch_hash(prompt)))
        agent["systemMessage"] = prompt
        olds.append(have)
        news.append(prompt)
        changes.append("Answer the resident: prompt %s -> %s (from the service team, honest when "
                       "asked; danger: the urgent ticket and nothing more; \"when?\": no date, it "
                       "will be handled; \"anything else?\" once the matter is done; an earlier "
                       "ticket is looked up; the 4h / 3-day line gone)" % (OLD_PROMPT, W.epoch_hash(prompt)))

    # get_balance: ask once, explain once, a refusal is a team note.
    bp = by["get_balance"]["parameters"]
    have = bp.get("toolDescription") or ""
    if not later and have != balance:
        if W.epoch_hash(have) != OLD_BALANCE:
            sys.exit("REFUSING: get_balance's description is %s, neither the one this replaces (%s) "
                     "nor the new one (%s)." % (W.epoch_hash(have), OLD_BALANCE, W.epoch_hash(balance)))
        bp["toolDescription"] = balance
        olds.append(have)
        news.append(balance)
        changes.append("get_balance: description %s -> %s (ask once, explain once, a refusal is a "
                       "team note; any country's number)" % (OLD_BALANCE, W.epoch_hash(balance)))

    # The memory: every buffer holds "anything else?" endings and the 4-hour answer.
    mem = by["Conversation so far"]["parameters"]
    want_key = MEMORY_KEY % W.MEMORY_EPOCH
    if not later and mem.get("sessionKey") != want_key:
        if mem.get("sessionKey") != MEMORY_KEY % OLD_EPOCH:
            sys.exit("REFUSING: the memory key is %r, not epoch %d." % (mem.get("sessionKey"), OLD_EPOCH))
        mem["sessionKey"] = want_key
        changes.append("Conversation so far: memory epoch %d -> %d (every buffer starts fresh)"
                       % (OLD_EPOCH, W.MEMORY_EPOCH))
    if mem.get("contextWindowLength") != W.MEMORY_TURNS:
        sys.exit("REFUSING: the memory window is %r, not %d." % (mem.get("contextWindowLength"), W.MEMORY_TURNS))

    sib = NP.siblings()
    sib = {k: v for k, v in sib.items() if not k.startswith("n8n_whatsapp_straight.")}
    old_all, new_all = NL.join(olds), NL.join(news)
    lost = [k for k, v in sib.items() if v in old_all and v not in new_all]
    if lost:
        sys.exit("REFUSING: the edit would break other patchers' anchors: %s" % lost)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("checks   : prompt hash %s, get_balance %s, epoch %d, %d sibling anchors intact"
          % (W.epoch_hash(prompt), W.epoch_hash(balance), W.MEMORY_EPOCH,
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
    print("  prompt %s (want %s); get_balance %s (want %s); memory key %s" % (
        W.epoch_hash(bb["Answer the resident"]["parameters"]["options"]["systemMessage"]),
        W.epoch_hash(prompt), W.epoch_hash(bb["get_balance"]["parameters"].get("toolDescription") or ""),
        W.epoch_hash(balance), bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
