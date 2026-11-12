# -*- coding: utf-8 -*-
"""A reply that gives our line goes out on the first pass; an emoji that ended a sentence leaves a full stop;
"כדי שיעזרו" goes with the other "so that they" clauses (12 Nov 2026, after the owner's Grok run of epoch 109).

    python scripts/n8n_whatsapp_linepass.py                         # dry run
    python scripts/n8n_whatsapp_linepass.py --dump F                # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_linepass.py --dump F --labels-only  # the labels only (TDD: cases fail)
    python scripts/n8n_whatsapp_linepass.py --apply                 # write it
    python scripts/n8n_whatsapp_linepass.py --restore               # put the snapshot back

WHY. The owner's Grok run of the standard (13:31-13:53 Israel, 11:32-11:54 UTC) passed every serious rule. One fail
and one note had a cause in our code, read in the executions:
  - E3.2 (175784), FAIL H8: "בבקשה תתקשר עכשיו בדחיפות למוקד החירום הטלפוני שלנו כדי שיעזרו לכם מיד". The first
    draft was right ("אני מבין שזה מצב מאוד מלחיץ ודחוף. אני רק העוזר הדיגיטלי, אז ... בבקשה תתקשר עכשיו בדחיפות
    למוקד החירום הטלפוני שלנו במספר 077-6687949."), but Reply usable?'s `echo` sends back any first draft with
    "אני מבין ש" when no tool ran, and an emergency runs none. The second pass, which every guard lets out, brought
    the plural "לכם" and the near-promise "שיעזרו ... מיד".
  - E1.1 (175738), NOTE: "אוי, מבאס להיכנס ללובי חשוך 😕 לפתוח על זה קריאת שירות?" went out as "... חשוך לפתוח על
    זה ...": Send's emoji step took the 😕 that ended the sentence and left nothing in its place.

WHAT CHANGES, in one write (code only: the prompt, the tools and the memory epoch stay):
  Reply usable?  echo v2 and clerk v2: a draft that gives our line counts as a turn that did its work, like a tool,
                 so it is never sent back as an echo or a clerk.
  Send           voice v4: "כדי שיעזרו" joins "כדי שיטפלו / שיבדקו / שיוכלו ...", whose clause goes (a clause with
                 our number still stays, voice v3). emoji v2: an emoji that is dropped between a word and the next
                 word becomes a full stop.
Not changed: the standard, the prompt, the other guards (and every guard still lets the second pass out).
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_hotline import expr_compiles  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-12nov-before-linepass.json")
KEY = "={{ $json.to }}-109"

WORKED_OLD = "const worked = t.indexOf('§§§') !== -1 || steps.some(s => {"
GUARD_EDITS = {   # condition id -> (label, old, new)
    "echo": ("echo v2", WORKED_OLD,
             "const ecv = 'echo v2'; const worked = t.indexOf('§§§') !== -1 || /0?77[-\\s]?668[-\\s]?7949/.test(t) "
             "|| steps.some(s => {"),
    "clerk": ("clerk v2", WORKED_OLD,
              "const ckv = 'clerk v2'; const worked = t.indexOf('§§§') !== -1 || /0?77[-\\s]?668[-\\s]?7949/.test(t) "
              "|| steps.some(s => {"),
}
GUARD_LABELS = {
    "echo": (WORKED_OLD, "const ecv = 'echo v2'; " + WORKED_OLD),
    "clerk": (WORKED_OLD, "const ckv = 'clerk v2'; " + WORKED_OLD),
}

EMOJI_OLD = r"const out = s.replace(E, (m) => KEEP.indexOf(m.replace(/[\uFE0F\u{1F3FB}-\u{1F3FF}]/gu, '')) !== -1 ? m : '');"
EMOJI_NEW = (r"const out = s.replace(E, (m, off, all) => { if (KEEP.indexOf(m.replace(/[\uFE0F\u{1F3FB}-\u{1F3FF}]/gu, '')) "
             r"!== -1) return m; const pre = all.slice(0, off).replace(/[\s\p{Extended_Pictographic}\uFE0F\u200D"
             r"\u{1F3FB}-\u{1F3FF}]+$/u, ''); const post = all.slice(off + m.length); return (/[\p{L}\p{N}]$/u.test(pre) "
             r"&& /^[ \t]+[\p{L}\p{N}]/u.test(post)) ? (/(?:^|[\s,])(?:שלום רב|שלום|היי|הי|אהלן|בוקר טוב|צהריים טובים|"
             r"ערב טוב|לילה טוב|שבוע טוב|שבת שלום|חג שמח|יום טוב)$/u.test(pre) ? ',' : '.') : ''; });")
LABELS = (
    ("const vv = 'voice v3';", "const vv = 'voice v4';"),
    ("const ev = 'emoji v1';", "const ev = 'emoji v2';"),
)
SEND_EDITS = LABELS + (
    ("יבדקו|יהיה להם|הצוות|המנהל|ההנהלה)", "יבדקו|יעזרו|יהיה להם|הצוות|המנהל|ההנהלה)"),
    (EMOJI_OLD, EMOJI_NEW),
)


def linepass(wf, labels_only=False):
    """The workflow with the edits above; each anchor exactly once. Does not touch memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    body = by["Send"]["parameters"]["jsonBody"]
    for old, new in (LABELS if labels_only else SEND_EDITS):
        assert "}}" not in new and "{{" not in new, "an edit would end the expression early"
        body = once(body, old, new)
    by["Send"]["parameters"]["jsonBody"] = body
    for c in by["Reply usable?"]["parameters"]["conditions"]["conditions"]:
        if c["id"] in GUARD_EDITS:
            old, new = (GUARD_LABELS if labels_only else {k: v[1:] for k, v in GUARD_EDITS.items()})[c["id"]]
            c["leftValue"] = once(c["leftValue"], old, new)
    return out


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    labels_only = "--labels-only" in sys.argv
    if apply and labels_only:
        sys.exit("REFUSING: --labels-only is for a dump, never for live.")
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    if "const ev = 'emoji v2';" in by["Send"]["parameters"]["jsonBody"]:
        print("Nothing to do. Live already lets a reply with our line out on the first pass (echo v2, emoji v2).")
        return
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key != KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 109's. Read live first." % key)

    new = linepass(live, labels_only)
    nb = {n["name"]: n for n in new["nodes"]}
    if prompt_of(new) != prompt_of(live) or tools_of(new) != tools_of(live):
        sys.exit("REFUSING: the prompt or the tools would change; this patcher is code only.")
    W.check_memory_epoch(prompt=prompt_of(new), tools=tools_of(new))
    expr_compiles(nb["Send"]["parameters"]["jsonBody"], "Send")
    for c in nb["Reply usable?"]["parameters"]["conditions"]["conditions"]:
        if c["id"] in GUARD_EDITS:
            expr_compiles(c["leftValue"], "Reply usable? / " + c["id"])
    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("prompt   : %s (unchanged)   memory: %s (unchanged)" % (W.epoch_hash(prompt_of(new)), key))
    print("code     : Reply usable? echo v2 + clerk v2; Send voice v4 + emoji v2%s"
          % (" (LABELS ONLY)" if labels_only else ""))
    print("changed  : %s" % ", ".join(n["name"] for n in new["nodes"] if n != by[n["name"]]))

    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        NP.dump(new["nodes"], new["connections"], path)
        print("dumped   : %s (the would-be workflow, secret replaced)" % path)
    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    if snapshot(live, SNAPSHOT):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": new["nodes"], "connections": new["connections"],
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    bb = {n["name"]: n for n in back["nodes"]}
    same = all(bb[n] == nb[n] for n in ("Send", "Reply usable?"))
    print("\nwritten  : %d nodes, active=%s; Send and Reply usable? %s; memory key %s"
          % (len(back["nodes"]), back.get("active"), "as written" if same else "DIFFER",
             bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
