# -*- coding: utf-8 -*-
"""Only the six emoji reach a resident: a last step in Send, 5 Oct.

    python scripts/n8n_whatsapp_emoji.py            # dry run
    python scripts/n8n_whatsapp_emoji.py --dump F   # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_emoji.py --apply    # write it
    python scripts/n8n_whatsapp_emoji.py --restore  # put the 5 Oct snapshot back

WHY. The prompt allows "a face or a hand, and only these: 🙂 😊 🙏 👍 💪 🤝", and
the model still sends others: 😔 and 😥 on the live run as Assaf Clix (5 Oct),
👋 on a goodbye. Open since 2 Oct; fix 5's small companion in the owner's plan
("Send keeps only the six emoji the prompt lists").

WHAT IT DOES, as the last step before Send returns its body: in a model reply
(not the system's menu, whose 👋 is the owner's), every emoji that is not one of
the six goes, with its skin tone or ZWJ tail; the spaces it leaves are closed up.
© ® ™ are not emoji here. A reply that would be left empty goes as it was. It
only removes. The buttons rule above it read the text before this, as before.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, `check_patchers_idle.py F`,
`--apply`, the check again on live, every WhatsApp patcher's dry run idle.
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
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-05oct-before-emoji.json")
PLACEHOLDER = NP.PLACEHOLDER
NL = chr(10)

# A backslash is built, never typed (manners.py, 27 Sep): `¤` stands for one.
BS = chr(92)
PH = "¤"
MARK = "const ev = 'emoji v1';"
SIX = ("🙂", "😊", "🙏", "👍", "💪", "🤝")
LINES = [
    "body.content = (() => { " + MARK,
    "let G = { }; try { G = $('Sort').first().json || { }; } catch (e) { G = { }; }",
    "if (G.greeting === true) return body.content;",
    "const s = String(body.content || '');",
    "const KEEP = [" + ", ".join("'%s'" % e for e in SIX) + "];",
    "const E = /(?![¤u00A9¤u00AE¤u2122])¤p{Extended_Pictographic}(?:¤uFE0F|[¤u{1F3FB}-¤u{1F3FF}]|¤u200D¤p{Extended_Pictographic})*/gu;",
    "const out = s.replace(E, (m) => KEEP.indexOf(m.replace(/[¤uFE0F¤u{1F3FB}-¤u{1F3FF}]/gu, '')) !== -1 ? m : '');",
    "if (out === s) return s;",
    "const r = out.replace(/[ ¤t]{2,}/g, ' ').replace(/[ ¤t]+([.,!?:;])/g, '$1')"
    ".replace(/[ ¤t]+$/gm, '').replace(/^[ ¤t]+/gm, '').trim();",
    "return r || s; })();",
]
BLOCK = " ".join(LINES).replace(PH, BS)
assert PH not in BLOCK and "}}" not in BLOCK and "{{" not in BLOCK
TAIL_OLD = "} return JSON.stringify(body); })() }}"
TAIL_NEW = "} " + BLOCK + " return JSON.stringify(body); })() }}"

# Turns run through the new Send body before any PUT (NP.SMOKE_JS's world).
SMOKE = [
    ("אני מבין לגמרי את הלחץ שלך. 😥 הצוות שלנו כבר יודע על הנזילה. יש עוד פרט שחשוב שאדע?", "leak",
     "אני מבין לגמרי את הלחץ שלך. הצוות שלנו כבר יודע על הנזילה. יש עוד פרט שחשוב שאדע?"),
    ("אוקיי, אסף. תודה שפנית אלינו, ושיהיה לך יום טוב! 👋", "thanks",
     "אוקיי, אסף. תודה שפנית אלינו, ושיהיה לך יום טוב!"),
    ("פתחתי לך קריאה מספר 255-1347-26 👍 יש עוד פרט שחשוב שהצוות ידע?", "lift",
     "פתחתי לך קריאה מספר 255-1347-26 👍 יש עוד פרט שחשוב שהצוות ידע?"),
    ("אוי, לא נעים 😔", "lights", "אוי, לא נעים"),
]


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


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv
    W.check_memory_epoch(prompt=W.system_prompt(), inject=U.AGENT_NEW, tools=W.tools_text())

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    if "Send" not in by or "Sort" not in by:
        sys.exit("No Send / Sort node on the live workflow -- refusing to guess.")
    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    before_layout = layout_complaints(nodes)

    changes = []
    body = by["Send"]["parameters"].get("jsonBody") or ""
    if MARK not in body:
        if body.count(TAIL_OLD) != 1 or not body.endswith(TAIL_OLD):
            sys.exit("REFUSING: Send does not end with the tail this script knows. Read the live body first.")
        if NP.MARK not in body:
            sys.exit("REFUSING: Send does not carry the promise filter (%s)." % NP.MARK)
        by["Send"]["parameters"]["jsonBody"] = body[:-len(TAIL_OLD)] + TAIL_NEW
        changes.append("Send: only the six emoji (%s), the last step before it returns" % MARK)
    new_body = by["Send"]["parameters"]["jsonBody"]
    if new_body.count("}}") != 1:
        sys.exit("REFUSING: the new Send body has %d '}}'." % new_body.count("}}"))
    sib = NP.siblings()
    sib = {k: v for k, v in sib.items() if not k.startswith("n8n_whatsapp_emoji.")}
    lost = [k for k, v in sib.items() if v in body and v not in new_body]
    if lost:
        sys.exit("REFUSING: the edit would break other patchers' anchors: %s" % lost)
    bad = smoke(new_body)
    if bad:
        sys.exit("REFUSING: the new Send body failed its smoke turns:" + NL + "  " + (NL + "  ").join(bad))

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("Send     : compiles in Node, %d smoke turns right, %d sibling anchors intact"
          % (len(SMOKE), sum(1 for v in sib.values() if v in body)))
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
    sb = {n["name"]: n for n in back["nodes"]}["Send"]["parameters"]["jsonBody"]
    print("")
    print("written: %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  Send carries %s: %s; %s: %s; '}}' count: %d"
          % (MARK, MARK in sb, NP.MARK, NP.MARK in sb, sb.count("}}")))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
