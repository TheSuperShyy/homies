# -*- coding: utf-8 -*-
"""One person, in the singular: the WhatsApp bot stops writing "לכם" to one resident.

    python scripts/n8n_whatsapp_gender.py            # dry run
    python scripts/n8n_whatsapp_gender.py --dump F   # dry run, plus the would-be workflow in F
                                                     # (check_whatsapp_rules.py --candidate F,
                                                     #  wa_qa.py bundle --candidate F)
    python scripts/n8n_whatsapp_gender.py --apply    # write it
    python scripts/n8n_whatsapp_gender.py --restore  # put the 1 Oct snapshot back

WHY, 1 Oct. The owner: *"i notice it still uses how can i help you all which is
awkward"*. The bot wrote "במה אוכל לעזור לכם?" to one person. He added that *"the
bot should adapt if the person on the other line uses feminine words or
adjectives or something to identify it should know"*, and the Hebrew default he
pasted: masculine until corrected, then switch without making a thing of it. The
prompt said the opposite on purpose ("plural, always"), written after a
no-gender instruction made the bot invent ספר/י.

WHAT CHANGES, in one write. Every text below is owned by its own patcher; this
one only carries those edits to live together, so each of them is idle after it.
  - The prompt (docs/features/11-whatsapp-bot/prompt.md): singular; masculine
    until it is clear a woman is writing ("אני צריכה", "אני גרה"), then feminine
    to the end, without remarking on it; never a slash. The two quoted examples
    of what not to ask went singular too. MEMORY_EPOCH 69 -> 70: every buffer
    holds plural replies, and an example beats a rule.
  - The three small writers that see no conversation: the payment ack
    (firstword.SYSTEM), the rescue (sayagain.SAY_SYSTEM) and the outage note
    (outage.WRITER_SYSTEM). They write to one person in words that fit a man and
    a woman alike (לך, שלך), so they cannot contradict a switch they cannot see.
  - Try again's note (retry.RETRY_NOTE) no longer says a rejected reply was
    "singular instead of plural".
  - The code that reads "you" and only knew the plural:
      Team note this turn? (teamnote.SAID): "יחזרו אליך / אלייך" and "ייצרו
        איתך קשר" make the team note that "יחזרו אליכם" makes, and "רוצה שנעביר"
        is an offer like "רוצים שנעביר".
      Send's promise filter, v2 (nopromise.PHRASES): אותך, אליך, אלייך beside
        אתכם, אליכם.
      The opener shape (retry.OPENER_RE: the `opener` guard and Send's third
        menu rule): "במה אוכל לעזור לך היום" beside "... לכם היום".
    On plural text each of these matches exactly what it matched before; the
    gate's replay of every reply ever sent is the proof.

WHAT IT DOES NOT TOUCH. The inject, the tools, the menu (already neutral: "במה
אפשר לעזור?"), Sort, the other guards, the greeting filter, the buttons, the
voice agents.

A field is rewritten only when its live text is the new text with the changed
fragments put back. Anything else means it was changed since, and this refuses.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, then the Claude-played replay
(`wa_qa.py bundle --candidate F`), then the owner's go, `--apply`, the check
again on live, and every WhatsApp patcher's dry run idle.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_untemplate as U  # noqa: E402
import n8n_whatsapp_manners as M  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
import n8n_whatsapp_retry as R  # noqa: E402
import n8n_whatsapp_sayagain as S  # noqa: E402
import n8n_whatsapp_outage as O  # noqa: E402
import n8n_whatsapp_firstword as FW  # noqa: E402
import n8n_whatsapp_teamnote as TN  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-01oct-before-gender.json")
PLACEHOLDER = NP.PLACEHOLDER
OLD_EPOCH = 69
OLD_PROMPT = "8afa16824480"     # EPOCH_COVERS["prompt"] at epoch 69
NL = chr(10)

# The fragments that changed, new first. Put back into the new text, they must
# give the live text exactly.
SIDE = ('ואל הדייר אתה פונה ביחיד, במילים שמתאימות לגבר ולאישה כאחד, כמו "לך" ו"שלך".',
        "ואל הדייר אתה פונה בלשון רבים.")
OUTAGE_HIS = ("שההודעה שלו הגיעה", "שההודעה שלהם הגיעה")
OUTAGE_BACK = ("מי יחזור אליו ומתי", "מי יחזור אליהם ומתי")
NOTE_SLASH = ("שפנתה לדייר בלוכסן או בסוגריים,", "שפנתה לדייר בלוכסן או ביחיד במקום בלשון רבים,")
PROMISED = ("const promised = /((יחזרו|יחזור|נחזור) (אליכם|אליך|אלייך)|"
            "(יצרו|ייצרו|ניצור|יצור) (אתכם|איתכם|אתך|איתך) קשר)/.test(t);",
            "const promised = /(יחזרו אליכם|יחזור אליכם|נחזור אליכם|יצרו אתכם קשר|"
            "יצרו איתכם קשר|ייצרו אתכם קשר|ייצרו איתכם קשר|ניצור אתכם קשר|ניצור איתכם קשר|"
            "יצור אתכם קשר|יצור איתכם קשר)/.test(t);")
OFFER = ("רוצים שנעביר|רוצה שנעביר|", "רוצים שנעביר|")
OPENER_YOU = ("( לכם| לך| לכם היום| לך היום)?", "( לכם| לך| לכם היום)?")

# (node, condition id or None, path inside parameters, wanted, fragments)
FIELDS = [
    ("Worth a word?", None, ("options", "systemMessage"), FW.SYSTEM, [SIDE]),
    ("Say it again", None, ("options", "systemMessage"), S.SAY_SYSTEM, [SIDE]),
    ("Could not answer", None, ("options", "systemMessage"), O.WRITER_SYSTEM,
     [SIDE, OUTAGE_HIS, OUTAGE_BACK]),
    ("Try again", None, ("jsonOutput",), R.TRY_JSON, [NOTE_SLASH]),
    ("Team note this turn?", "teamnote", ("leftValue",), TN.NOTE_THIS_TURN, [PROMISED, OFFER]),
    ("Reply usable?", "opener", ("leftValue",), R.OPENER_GUARD["leftValue"], [OPENER_YOU]),
]
SEND_TAIL_OLD = R.SEND_TAIL_NEW.replace(OPENER_YOU[0], OPENER_YOU[1])
PROMISE_V1 = "const pv = 'promise v1';"
MEMORY_KEY = "={{ $json.to }}-%d"

# Turns the new Send body must get right before any PUT: the plural ones the
# promise filter shipped with, and the singular forms only v2 knows.
SMOKE = NP.SMOKE + [
    ("פתחתי לך קריאה מספר 255-1339-26. נעדכן אותך כשיהיה משהו חדש. אפשר לעזור בעוד משהו?",
     "the lights", "פתחתי לך קריאה מספר 255-1339-26. אפשר לעזור בעוד משהו?"),
    ("העברתי את זה לצוות. מישהו בדרך אלייך. יש עוד משהו?", "help",
     "העברתי את זה לצוות. יש עוד משהו?"),
    ("איזה מעצבן. תוכלי לכתוב לי באיזה בניין ובאיזו דירה?", "the lights",
     "איזה מעצבן. תוכלי לכתוב לי באיזה בניין ובאיזו דירה?"),
]


def node_of(by, name):
    if name not in by:
        sys.exit("No %r node on the live workflow -- refusing to guess." % name)
    return by[name]


def slot(by, name, cid, path):
    """The dict holding the field, and its key."""
    p = node_of(by, name)["parameters"]
    if cid is not None:
        conds = p["conditions"]["conditions"]
        hits = [c for c in conds if c.get("id") == cid]
        if len(hits) != 1:
            sys.exit("REFUSING: %r has %d conditions with id %r." % (name, len(hits), cid))
        p = hits[0]
    for k in path[:-1]:
        p = p.setdefault(k, {})
    return p, path[-1]


def put_back(wanted, frags):
    old = wanted
    for new, was in frags:
        if new not in old:
            sys.exit("REFUSING: the wanted text does not carry %r; a sibling's constant "
                     "is not what this script was written against." % new[:60])
        old = old.replace(new, was)
    return old


def smoke(json_body):
    import check_whatsapp_rules as C
    payload = {"expr": C.inner(json_body), "cases": [[a, b] for a, b, _ in SMOKE]}
    r = subprocess.run(["node", "-e", NP.SMOKE_JS], capture_output=True,
                       input=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    if r.returncode != 0:
        return ["node failed: " + r.stderr.decode("utf-8", "replace")[:300]]
    res = json.loads(r.stdout.decode("utf-8"))
    if "error" in res:
        return [res["error"]]
    return ["smoke %d: got %r, want %r" % (i, got, want)
            for i, (got, (_, _, want)) in enumerate(zip(res["out"], SMOKE)) if got != want]


COMPILE_JS = ("const fs = require('fs'); const xs = JSON.parse(fs.readFileSync(0, 'utf8')); "
              "const bad = []; for (const [k, e] of xs) { try { new Function('$json', '$', "
              "'$runIndex', 'return (' + e + ');'); } catch (err) { bad.push(k + ': ' + err.message); } } "
              "console.log(JSON.stringify(bad));")


def compiles(exprs):
    """Every changed expression parses as JavaScript, the way n8n will read it."""
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
    print("MEMORY_EPOCH in n8n_whatsapp.py still says %d; the restored key is -%d."
          % (W.MEMORY_EPOCH, OLD_EPOCH))


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    prompt = W.system_prompt()
    W.check_memory_epoch(prompt=prompt, inject=U.AGENT_NEW, tools=W.tools_text())
    if W.MEMORY_EPOCH < OLD_EPOCH + 1:
        sys.exit("REFUSING: MEMORY_EPOCH is %d; this change was written for %d -> %d."
                 % (W.MEMORY_EPOCH, OLD_EPOCH, OLD_EPOCH + 1))
    # A later epoch owns the prompt and the memory key from then on (the first was
    # n8n_whatsapp_rephello.py, epoch 71, 1 Oct evening). This script then checks
    # only its own fields, so it stays idle instead of refusing on a newer prompt.
    later = W.MEMORY_EPOCH > OLD_EPOCH + 1

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in ("Send", "Sort", "Answer the resident", "Conversation so far", "Two parts?"):
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
        changes.append("Answer the resident: prompt %s -> %s (singular; masculine until "
                       "a woman is clearly writing)" % (OLD_PROMPT, W.epoch_hash(prompt)))

    # The memory: every buffer holds plural replies.
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

    # The small writers, the retry note, the team note, the opener guard.
    exprs = []
    for name, cid, path, wanted, frags in FIELDS:
        holder, key = slot(by, name, cid, path)
        have = holder.get(key) or ""
        if wanted.startswith("={{"):
            exprs.append((name, wanted))
        if have == wanted:
            continue
        if have != put_back(wanted, frags):
            sys.exit("REFUSING: %r%s is neither the text this replaces nor the new one. "
                     "Read the live node first." % (name, " / " + cid if cid else ""))
        holder[key] = wanted
        olds.append(have)
        news.append(wanted)
        changes.append("%s%s: singular" % (name, " / " + cid if cid else ""))

    # Send: the opener shape in the third menu rule, and the promise filter v2.
    body = by["Send"]["parameters"].get("jsonBody") or ""
    new = body
    if R.SEND_TAIL_NEW not in new:
        if new.count(SEND_TAIL_OLD) != 1:
            sys.exit("REFUSING: Send does not carry the opener menu rule this script knows "
                     "(found %d)." % new.count(SEND_TAIL_OLD))
        new = new.replace(SEND_TAIL_OLD, R.SEND_TAIL_NEW, 1)
        changes.append("Send: the third menu rule knows the singular opener")
    if NP.SEND_NEW not in new:
        if new.count(PROMISE_V1) != 1 or new.count(NP.BLOCK_START) != 1:
            sys.exit("REFUSING: Send does not carry promise v1 exactly once. Read the live body first.")
        a = new.index(NP.BLOCK_START)
        z = new.index(NP.BLOCK_END, a)
        new = new[:a] + NP.FILTER + new[z:]
        changes.append("Send: promise filter v1 -> v2 (the singular you)")
    if new != body:
        if new.count("}}") != 1:
            sys.exit("REFUSING: the new Send body has %d '}}'." % new.count("}}"))
        if M.MARK not in new or NP.MARK not in new:
            sys.exit("REFUSING: the new Send body lost the greeting filter or the promise filter.")
        bad = smoke(new)
        if bad:
            sys.exit("REFUSING: the new Send body failed its smoke turns:" + NL + "  "
                     + (NL + "  ").join(bad))
        by["Send"]["parameters"]["jsonBody"] = new
        olds.append(body)
        news.append(new)

    bad = compiles(exprs)
    if bad:
        sys.exit("REFUSING: an expression does not compile:" + NL + "  " + (NL + "  ").join(bad))
    for _, wanted in exprs:
        if wanted.count("}}") != 1:
            sys.exit("REFUSING: an expression has %d '}}'." % wanted.count("}}"))

    sib = NP.siblings()
    sib = {k: v for k, v in sib.items() if not k.startswith("n8n_whatsapp_gender.")}
    old_all, new_all = NL.join(olds), NL.join(news)
    lost = [k for k, v in sib.items() if v in old_all and v not in new_all]
    if lost:
        sys.exit("REFUSING: the edit would break other patchers' anchors: %s" % lost)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("checks   : prompt hash %s, epoch %d, %d expressions compile, %d smoke turns right, "
          "%d sibling anchors intact" % (W.epoch_hash(prompt), W.MEMORY_EPOCH, len(exprs),
                                          len(SMOKE), sum(1 for v in sib.values() if v in old_all)))
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
    print("  prompt %s; memory key %s" % (
        W.epoch_hash(bb["Answer the resident"]["parameters"]["options"]["systemMessage"]),
        bb["Conversation so far"]["parameters"]["sessionKey"]))
    for name, cid, path, wanted, _ in FIELDS:
        holder, key = slot(bb, name, cid, path)
        print("  %s%s matches: %s" % (name, " / " + cid if cid else "", holder.get(key) == wanted))
    sb = bb["Send"]["parameters"]["jsonBody"]
    print("  Send carries %s: %s; %s: %s; the opener rule: %s; '}}' count: %d" % (
        NP.MARK, NP.MARK in sb, M.MARK, M.MARK in sb, R.SEND_TAIL_NEW in sb, sb.count("}}")))
    print("  Reply usable? conditions %s" % [
        c.get("id") for c in bb["Reply usable?"]["parameters"]["conditions"]["conditions"]])
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
