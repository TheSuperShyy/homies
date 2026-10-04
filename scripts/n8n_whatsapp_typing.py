# -*- coding: utf-8 -*-
"""WhatsApp shows "typing…" while Michael writes, 4 Oct.

    python scripts/n8n_whatsapp_typing.py            # dry run
    python scripts/n8n_whatsapp_typing.py --dump F   # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_typing.py --apply    # make its n8n credential, then write it
    python scripts/n8n_whatsapp_typing.py --restore  # put the 4 Oct snapshot back

WHY, 4 Oct. The owner: *"can we add a typing behaviour in whatsapp?"*, and later,
having looked for it on his phone, *"it does not have the typing indictor on it"*.
Chatwoot cannot do it: its toggle_typing_status only reaches Chatwoot's own screens
(Conversations::TypingStatusManager dispatches an internal event; the WhatsApp Cloud
service has no typing call). Meta can: POST /{phone-number-id}/messages with
status "read", the message's wamid and typing_indicator {type: "text"} marks the
message read (blue ticks) and shows "typing…" until the reply goes out or 25 s
pass. Checked against Meta on 4 Oct with a made-up wamid: v21.0, v23.0 and v25.0
all validate typing_indicator.type (enum [text]) and refuse only the id.

WHAT CHANGES. Two HTTP nodes and their wires, nothing else:
  - `Show typing`, when the bot commits to answering: off `Still the last word?`
    (after the 4 s `Let them finish`, so a resident still writing is not hurried,
    and only in the run that answers), off `Canned reply?` and off `Menu?`.
  - `Show typing again`, after the payment note (`Say it now`) and between the two
    parts of a two-part reply (`Two parts?` true): each of those sends a message,
    and a message ends "typing…".
Both read the wamid Chatwoot's webhook carries (`body.source_id`, on the webhook's
second output: GET is the first, POST the second), call Meta with their own n8n
credential (WHATSAPP_ACCESS_TOKEN: the system-user token Chatwoot's inbox sends
with, never expires), time out in 4 s, never retry (a "typing…" after the reply is
worse than none), and continue on error, so a failed call never holds a reply.

WHERE THEY SIT IS PART OF THE CHANGE. executionOrder v1 runs a node's children top
to bottom by canvas position (CONTEXT.md), so each sits above every sibling under
each of its parents: `Show typing` above `Worth a word?`, `Log inbound`, `Log reply`
and both `Type for a moment` waits; `Show typing again` above `Hold a beat` and
`Carry on`. problems() checks that, and check_whatsapp_rules.py runs the same
check on live.

WHAT IT DOES NOT TOUCH. Every existing node and wire, the prompt, the memory (no
epoch: nothing a model reads changes), Chatwoot, the voice agents.

AT CUTOVER the URL carries the Meta test number's phone-number id; Homies' own
number needs its id here and its token in the credential.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: the gate on live
before and after, check_patchers_idle.py, the owner's go, `--apply`, the owner's
handset, `--watch` (it notes a "typing…" that did not show).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-04oct-before-typing.json")
GRAPH = "v23.0"
CRED_NAME = "Homies WhatsApp typing (Meta)"
CRED_ENV = "N8N_WHATSAPP_TYPING_CRED_ID"
NOT_YET = "made-at-apply"
NL = chr(10)

FIRST, AGAIN = "Show typing", "Show typing again"
# (parent, output) pairs each node hangs off, and where it is drawn: above every
# sibling under every parent (the grid is 240 x 60; see n8n_layout.py).
PARENTS = {
    FIRST: [("Still the last word?", 0), ("Canned reply?", 0), ("Menu?", 0)],
    AGAIN: [("Say it now", 0), ("Two parts?", 0)],
}
POSITION = {FIRST: [720, -360], AGAIN: [1920, -360]}
NODE_ID = {FIRST: "showtyping", AGAIN: "showtypingagain"}

BODY = """={{ (() => {
  // The webhook answers on two outputs, GET first and POST second, and
  // Chatwoot's message arrives on the second. Read it there, then the first.
  let id = '';
  for (const b of [1, 0]) {
    try { id = String($('WhatsApp').first(b).json.body.source_id || ''); } catch (e) { id = ''; }
    if (id) break;
  }
  return JSON.stringify({ messaging_product: 'whatsapp', status: 'read', message_id: id,
                          typing_indicator: { type: 'text' } });
})() }}"""


def without_typing(spec):
    """A node's connections with every wire into the two typing nodes left out.

    For the patchers that pin a node's whole wiring (n8n_whatsapp_firstword.py:
    `Still the last word?`, `Say it now`; n8n_whatsapp_twobeat.py: `Two parts?`),
    so they neither read the typing wires as drift nor drop them on a rewrite."""
    if not spec:
        return spec
    out = json.loads(json.dumps(spec))
    for key, branches in out.items():
        out[key] = [[t for t in (b or []) if t.get("node") not in PARENTS] for b in branches or []]
    return out


def with_typing(spec, live_spec):
    """`spec`, plus the typing wires `live_spec` carries, on the same outputs."""
    out = json.loads(json.dumps(spec))
    for key, branches in (live_spec or {}).items():
        mine = out.setdefault(key, [])
        for i, b in enumerate(branches or []):
            keep = [t for t in (b or []) if t.get("node") in PARENTS]
            if not keep:
                continue
            while len(mine) <= i:
                mine.append([])
            mine[i] = (mine[i] or []) + [t for t in keep if t not in (mine[i] or [])]
    return out


def url():
    pid = W.env().get("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    if not pid:
        sys.exit("WHATSAPP_PHONE_NUMBER_ID is empty in .env.")
    return "https://graph.facebook.com/%s/%s/messages" % (GRAPH, pid)


def typing_node(name, cred_id):
    return {
        "parameters": {
            "method": "POST",
            "url": url(),
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": BODY,
            "options": {"timeout": 4000},
        },
        "id": NODE_ID[name],
        "name": name,
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": list(POSITION[name]),
        "credentials": {"httpHeaderAuth": {"id": cred_id, "name": CRED_NAME}},
        "onError": "continueRegularOutput",
    }


def problems(wf):
    """What is wrong with the two nodes on a workflow; empty when right.

    Shared with check_whatsapp_rules.py, which runs it on live."""
    by = {n["name"]: n for n in wf["nodes"]}
    conns = wf.get("connections") or {}
    out = []
    for name, parents in PARENTS.items():
        n = by.get(name)
        if n is None:
            out.append("%s is missing" % name)
            continue
        p = n.get("parameters") or {}
        u = str(p.get("url") or "")
        if p.get("method") != "POST" or not u.startswith("https://graph.facebook.com/") \
                or not u.endswith("/messages"):
            out.append("%s does not call Meta's messages endpoint (%s %s)" % (name, p.get("method"), u[:60]))
        if p.get("jsonBody") != BODY:
            out.append("%s: the body is not the typing call" % name)
        if n.get("onError") != "continueRegularOutput":
            out.append("%s can hold a reply: onError is %r" % (name, n.get("onError")))
        if n.get("retryOnFail"):
            out.append("%s retries: a 'typing…' after the reply is worse than none" % name)
        if int((p.get("options") or {}).get("timeout") or 0) > 5000:
            out.append("%s waits more than 5 s" % name)
        if not ((n.get("credentials") or {}).get("httpHeaderAuth") or {}).get("id"):
            out.append("%s has no credential" % name)
        if any(t for branch in (conns.get(name) or {}).get("main") or [] for t in branch or []):
            out.append("%s feeds other nodes; it has to be a side branch" % name)
        mine = n.get("position") or [0, 0]
        for parent, i in parents:
            branches = (conns.get(parent) or {}).get("main") or []
            kids = [t["node"] for t in (branches[i] if i < len(branches) else None) or []]
            if name not in kids:
                out.append("%s is not fed by %s (output %d)" % (name, parent, i))
                continue
            for k in kids:
                pos = (by.get(k) or {}).get("position")
                if k != name and pos and (pos[1], pos[0]) <= (mine[1], mine[0]):
                    out.append("%s is drawn below %s under %s, so it would run after it"
                               % (name, k, parent))
    return out


SMOKE_JS = """
const P = JSON.parse(require('fs').readFileSync(0, 'utf8'));
let f;
try { f = new Function('$', 'return (' + P.body + ');'); }
catch (e) { console.log(JSON.stringify({ bad: ['does not compile: ' + e.message] })); process.exit(0); }
const bad = [];
// What n8n hands the expression: the webhook's message on its second output.
const hook = (outs) => () => ({ first: (b) => {
  const items = outs[b] || [];
  if (!items.length) throw new Error('no data on output ' + b);
  return items[0];
} });
const msg = { json: { body: { source_id: P.wamid } } };
const cases = [
  ['the second output', [[], [msg]], P.wamid],
  ['the first output', [[msg], []], P.wamid],
  ['no message id', [[], [{ json: { body: {} } }]], ''],
];
for (const [label, outs, want] of cases) {
  let b;
  try { b = JSON.parse(f(hook(outs))); } catch (e) { bad.push(label + ': threw ' + e.message); continue; }
  if (b.message_id !== want) bad.push(label + ': message_id ' + b.message_id);
  if (b.status !== 'read' || b.messaging_product !== 'whatsapp' || !b.typing_indicator
      || b.typing_indicator.type !== 'text') bad.push(label + ': not the typing call ' + JSON.stringify(b));
}
console.log(JSON.stringify({ bad }));
"""


def smoke():
    import check_whatsapp_rules as C
    payload = {"body": C.inner(BODY), "wamid": "wamid.HBgMOTcyNTAwMDAwMDAwFQIAEhgUM0E="}
    r = subprocess.run(["node", "-e", SMOKE_JS], capture_output=True,
                       input=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    if r.returncode != 0:
        return ["node failed: " + r.stderr.decode("utf-8", "replace")[:300]]
    return json.loads(r.stdout.decode("utf-8"))["bad"]


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
        text = text.replace(secret, NP.PLACEHOLDER)
    with open(SNAPSHOT, "w", encoding="utf-8", newline=NL) as f:
        f.write(text)
    return True


def restore():
    snap = json.load(open(SNAPSHOT, encoding="utf-8"))
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    if not secret:
        sys.exit("N8N_WEBHOOK_SECRET is not in .env; the snapshot's Sort node would "
                 "go live with a placeholder secret. Refusing.")
    body = json.loads(json.dumps(snap, ensure_ascii=False).replace(NP.PLACEHOLDER, secret))
    W.api("PUT", "/api/v1/workflows/%s" % WORKFLOW_ID, {
        "name": body["name"], "nodes": body["nodes"],
        "connections": body["connections"], "settings": body.get("settings", {})})
    print("restored %s from %s (%d nodes)" % (WORKFLOW_ID, SNAPSHOT, len(body["nodes"])))
    print("The credential %r stays in n8n, unused; delete it in the n8n UI if wanted." % CRED_NAME)


def make_credential():
    """The token in n8n's credential store, never in the workflow. Made once;
    its id goes to .env so a re-run finds it instead of making another."""
    token = W.env().get("WHATSAPP_ACCESS_TOKEN", "").strip()
    if not token:
        sys.exit("WHATSAPP_ACCESS_TOKEN is empty in .env; nothing to make the credential from.")
    cid = W.api("POST", "/api/v1/credentials", {
        "name": CRED_NAME, "type": "httpHeaderAuth",
        "data": {"name": "Authorization", "value": "Bearer " + token},
    })["id"]
    W.set_env(CRED_ENV, cid)
    print("credential: %s -> %s (the token is in n8n, not in the workflow)" % (CRED_NAME, cid))
    return cid


def wire(conns, parent, i, child):
    """Add parent[i] -> child, leaving every other wire as it was."""
    main = conns.setdefault(parent, {}).setdefault("main", [])
    while len(main) <= i:
        main.append([])
    if main[i] is None:
        main[i] = []
    if not any(t.get("node") == child for t in main[i]):
        main[i].append({"node": child, "type": "main", "index": 0})
        return True
    return False


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    by = {n["name"]: n for n in nodes}
    for need in ("WhatsApp", "Sort") + tuple(p for ps in PARENTS.values() for p, _ in ps):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    bad = smoke()
    if bad:
        sys.exit("REFUSING: the body expression failed its smoke turns:" + NL + "  " + (NL + "  ").join(bad))

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    before_layout = layout_complaints(nodes)
    cred_id = W.env().get(CRED_ENV, "").strip()
    changes = []

    for name in (FIRST, AGAIN):
        want = typing_node(name, cred_id or NOT_YET)
        have = by.get(name)
        if have is None:
            nodes.append(want)
            by[name] = want
            changes.append("%s: added at %s" % (name, want["position"]))
        else:
            mine = dict(have, credentials=want["credentials"]) if cred_id else have
            keys = ("parameters", "type", "typeVersion", "position", "onError")
            if any(mine.get(k) != want.get(k) for k in keys) or (cred_id and have.get("credentials") != want["credentials"]):
                for k in keys + ("credentials",):
                    have[k] = want[k]
                changes.append("%s: put back to this script's version" % name)
        for parent, i in PARENTS[name]:
            if wire(conns, parent, i, name):
                changes.append("%s[%d] -> %s" % (parent, i, name))

    probs = problems({"nodes": nodes, "connections": conns})
    if probs:
        sys.exit("REFUSING: the would-be workflow is wrong:" + NL + "  " + (NL + "  ").join(probs))

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("checks   : body smoke 3 turns right; both nodes side branches, each above its siblings")
    print("calls    : POST %s" % url().replace(W.env().get("WHATSAPP_PHONE_NUMBER_ID", "").strip(), "<phone-number-id>"))
    print("credential: %s" % ("%s (%s)" % (CRED_NAME, cred_id) if cred_id else "made at --apply"))
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

    if not cred_id:
        cred_id = make_credential()
        for name in (FIRST, AGAIN):
            by[name]["credentials"] = {"httpHeaderAuth": {"id": cred_id, "name": CRED_NAME}}

    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": nodes, "connections": conns,
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    left = problems(back)
    print("")
    print("written: %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  typing nodes: %s" % ("right" if not left else "; ".join(left)))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
