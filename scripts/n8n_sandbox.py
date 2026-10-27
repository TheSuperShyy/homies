"""The sandbox copies of the WhatsApp bot, "Hand to a person" and the debt-tools router (feature 19).

    python scripts/n8n_sandbox.py                       # transform and print what would be created
    python scripts/n8n_sandbox.py --apply               # credentials, then the three workflows, then activate
    python scripts/n8n_sandbox.py --apply --section6    # the same, with Yariv's section 6 in the bot copy
    ... --apply --section6 --fresh-memory               # and a new memory round: every persona starts clean

The live workflows are only ever read (GET). Every write targets an id this
script created; write() refuses any id in LIVE_IDS. Re-running PUTs the same
sandbox ids, so the copies are regenerated from live, never edited by hand.

What changes in a copy, and why:
- Chatwoot: account 2 -> the sandbox account, with the sandbox tokens.
- The function: debt-tools -> debt-tools-sandbox (the live code behind a guard
  that fakes every database write and refuses every outside call).
- The router: the bot's open_request and notify_team go through
  /webhook/homies-debt-tools, which answers some tools before it writes. A copy
  of it keeps that behaviour, pointed at the sandbox function.
- Webhooks: own paths and webhookIds; Sort's shared secret is the sandbox's.
- Memory: the session key gets "-sbx", so no sandbox turn can enter a live
  conversation's memory even if n8n keyed its buffers by session alone. Then
  SANDBOX_MEMORY_ROUND, bumped by --fresh-memory: a persona's memory is its
  phone's, so one bad reply is carried into every later test as that persona
  (27 Oct, Ido) until the round changes. Live does the same with its -84 epoch.
- Meta and the chat log: Show typing, Show typing again, Log inbound and Log
  reply become NoOps (a NoOp passes its input on, so the flow is unchanged).
  `Anything newer?` read the live `messages` table; the sandbox reads its own
  Chatwoot conversation instead and hands the seven readers the same row shape.
"""
import copy, json, os, re, sys, uuid, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from supabase_functions import env, set_env

LIVE_IDS = {"u2JjrbcNPYyyh3yl", "oB66atFlWwtkSGgN", "lXofknAbE5wu5nwQ", "IVNR5iNn7bQS8JgP",
            "i3VMdCnXZGooI1Dj", "pduAdXjX1EU7cA6E", "pvMuradcJOASapF0"}
LIVE_BOT, LIVE_HANDOVER, LIVE_ROUTER = "u2JjrbcNPYyyh3yl", "oB66atFlWwtkSGgN", "lXofknAbE5wu5nwQ"
LIVE_TEAMS = "const TEAMS = { collections: 1, operations: 2, management: 3, service: 4 };"
NODE_W, NODE_H = 200, 100

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def n8n(method, path, body=None):
    e = env()
    req = urllib.request.Request(e["N8N_BASE_URL"].rstrip("/") + path, method=method,
                                 data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None,
                                 headers={"X-N8N-API-KEY": e["N8N_API_KEY"], "accept": "application/json",
                                          "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as x:
        sys.exit("n8n %s %s -> HTTP %s %s" % (method, path, x.code, x.read()[:500].decode("utf-8", "replace")))


def load(wid):
    return n8n("GET", "/api/v1/workflows/" + wid)


def replace_once(text, old, new):
    assert text.count(old) == 1, "expected exactly one %r, found %d" % (old[:60], text.count(old))
    return text.replace(old, new)


def free_spot(nodes, x, y):
    """The nearest grid position to (x, y) that no node is drawn on (scripts/n8n_layout.py's box)."""
    taken = [n["position"] for n in nodes if "stickyNote" not in n["type"]]
    for r in range(0, 20):
        for dx, dy in ((0, 0), (0, r * 120), (0, -r * 120), (r * 240, 0), (r * 240, r * 120),
                       (r * 240, -r * 120), (-r * 240, r * 120), (-r * 240, -r * 120)):
            px, py = x + dx, y + dy
            if all(abs(px - a) >= NODE_W or abs(py - b) >= NODE_H for a, b in taken):
                return [px, py]
    raise RuntimeError("no free spot near %s" % [x, y])


def note(wf, text):
    """One sticky note above the canvas saying what this copy is."""
    xs = [n["position"][0] for n in wf["nodes"]]
    ys = [n["position"][1] for n in wf["nodes"]]
    wf["nodes"].append({"id": str(uuid.uuid4()), "name": "Sandbox copy", "type": "n8n-nodes-base.stickyNote",
                        "typeVersion": 1, "position": [min(xs), min(ys) - 320],
                        "parameters": {"content": text, "width": 560, "height": 220, "color": 3}})


def rewrite_node(n, cfg):
    """URLs and credentials: the sandbox account, function, router and tokens."""
    p = n.setdefault("parameters", {})
    url = p.get("url")
    if isinstance(url, str):
        url = url.replace("/api/v1/accounts/2/", "/api/v1/accounts/%d/" % cfg["account_id"])
        url = re.sub(r"/functions/v1/debt-tools(?![-\w])", "/functions/v1/debt-tools-sandbox", url)
        url = re.sub(r"/webhook/homies-debt-tools(?![-\w])", "/webhook/homies-debt-tools-sandbox", url)
        p["url"] = url
    for ctype, c in list((n.get("credentials") or {}).items()):
        if c.get("name") == "Chatwoot admin (api_access_token)":
            n["credentials"][ctype] = dict(cfg["cred_admin"])
        elif c.get("name") == "Chatwoot bot (api_access_token)":
            n["credentials"][ctype] = dict(cfg["cred_bot"])


def webhook(wf, path):
    hooks = [n for n in wf["nodes"] if n["type"] == "n8n-nodes-base.webhook"]
    assert len(hooks) == 1, "expected one webhook trigger in %s" % wf["name"]
    hooks[0]["parameters"]["path"] = path
    hooks[0]["webhookId"] = path + "-v1"


def noop(wf, name):
    n = next(x for x in wf["nodes"] if x["name"] == name)
    n.update({"type": "n8n-nodes-base.noOp", "typeVersion": 1, "parameters": {}})
    n.pop("credentials", None)


CHAT_LOG = (
    "// Feature 19: the sandbox keeps no chat log of its own; its Chatwoot conversation\n"
    "// is the log. These are the rows the live `messages` query returned: newest first,\n"
    "// at most 12, both directions, private notes and activity lines left out.\n"
    "const payload = $input.first().json.payload || [];\n"
    "const rows = payload\n"
    "  .filter(m => (m.message_type === 0 || m.message_type === 1) && !m.private)\n"
    "  .sort((a, b) => b.id - a.id)\n"
    "  .slice(0, 12)\n"
    "  .map(m => ({ json: {\n"
    "    external_id: String(m.id),\n"
    "    body: m.content || '',\n"
    "    direction: m.message_type === 0 ? 'inbound' : 'outbound',\n"
    "    message_type: m.content_type === 'input_select' ? 'menu'\n"
    "      : (m.attachments || []).some(a => a.file_type === 'image') ? 'image' : 'text',\n"
    "  } }));\n"
    "// Like the live HTTP node's \"always output data\": an empty log still lets\n"
    "// `Still the last word?` run, with this run's own message as the text.\n"
    "return rows.length ? rows : [{ json: {} }];")


def chat_log_from_chatwoot(wf, cfg):
    """`Anything newer?` read Supabase `messages`. The sandbox's log is its Chatwoot
    conversation: the fetch keeps the old node's slot, and a Code node named
    `Anything newer?` hands its seven readers the same rows as before."""
    old = next(x for x in wf["nodes"] if x["name"] == "Anything newer?")
    old["name"] = "Anything newer? (fetch)"
    old["parameters"] = {"method": "GET", "options": {"timeout": 10000},
                         "url": "=%s/api/v1/accounts/%d/conversations/{{ $('Sort').first().json.conv_id }}/messages"
                                % (cfg["chatwoot_url"], cfg["account_id"]),
                         "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth"}
    old["credentials"] = {"httpHeaderAuth": dict(cfg["cred_admin"])}
    spot = free_spot(wf["nodes"], old["position"][0], old["position"][1] - 120)
    wf["nodes"].append({"id": str(uuid.uuid4()), "name": "Anything newer?", "type": "n8n-nodes-base.code",
                        "typeVersion": 2, "position": spot, "alwaysOutputData": True,
                        "parameters": {"jsCode": CHAT_LOG}})
    conns = wf["connections"]
    for src in conns.values():
        for lst in src.get("main", []):
            for c in lst:
                if c["node"] == "Anything newer?":
                    c["node"] = "Anything newer? (fetch)"
    out = conns.pop("Anything newer?")
    conns["Anything newer? (fetch)"] = {"main": [[{"node": "Anything newer?", "type": "main", "index": 0}]]}
    conns["Anything newer?"] = out


def base_copy(wf, name):
    w = copy.deepcopy(wf)
    return {"name": name, "nodes": w["nodes"], "connections": w["connections"],
            "settings": dict(w.get("settings") or {})}


NOTE = ("### SANDBOX copy (feature 19)\n"
        "Generated from the live workflow \"%s\" by `scripts/n8n_sandbox.py`. Do not edit it here: "
        "change the script and re-run it.\n\n"
        "Talks only to Chatwoot account %d, `debt-tools-sandbox` and the other SANDBOX workflows. "
        "No WhatsApp, no writes to the live database.")


def sandboxify_router(wf, cfg):
    out = base_copy(wf, "SANDBOX — debt tools router")
    for n in out["nodes"]:
        rewrite_node(n, cfg)
    webhook(out, "homies-debt-tools-sandbox")
    note(out, NOTE % (wf["name"], cfg["account_id"]))
    return out


def sandboxify_handover(wf, cfg):
    out = base_copy(wf, "SANDBOX — Hand to a person")
    for n in out["nodes"]:
        rewrite_node(n, cfg)
        if n["name"] == "Decide the routing":
            t = cfg["teams"]
            n["parameters"]["jsCode"] = replace_once(
                n["parameters"]["jsCode"], LIVE_TEAMS,
                "const TEAMS = { collections: %d, operations: %d, management: %d, service: %d };"
                % (t["collections"], t["operations"], t["management"], t["service"]))
    note(out, NOTE % (wf["name"], cfg["account_id"]))
    return out


def sandboxify_bot(wf, cfg):
    out = base_copy(wf, "SANDBOX — WhatsApp bot")
    for n in out["nodes"]:
        rewrite_node(n, cfg)
        if n["type"] == "n8n-nodes-base.executeWorkflow":
            n["parameters"]["workflowId"] = {"__rl": True, "value": cfg["handover_id"], "mode": "id"}
        if n["name"] == "Sort":
            js = n["parameters"]["jsCode"]
            live = re.search(r'const SHARED = "([^"]+)"', js).group(1)
            n["parameters"]["jsCode"] = replace_once(js, 'const SHARED = "%s"' % live,
                                                     'const SHARED = "%s"' % cfg["sandbox_secret"])
    memories = [n for n in out["nodes"] if n["type"] == "@n8n/n8n-nodes-langchain.memoryBufferWindow"]
    assert len(memories) == 1, "expected one memory node"
    memories[0]["parameters"]["sessionKey"] += "-sbx" + str(cfg.get("memory_round") or "")
    webhook(out, "homies-whatsapp-sandbox")
    for name in ("Show typing", "Show typing again", "Log inbound", "Log reply"):
        noop(out, name)
    chat_log_from_chatwoot(out, cfg)
    note(out, NOTE % (wf["name"], cfg["account_id"]))
    return out


def write(wf, env_key):
    """POST a new sandbox workflow, or PUT the one this script made before; then activate it."""
    wid = env().get(env_key, "")
    assert wid not in LIVE_IDS, "refusing to write a live workflow"
    if wid:
        n8n("PUT", "/api/v1/workflows/" + wid, wf)
    else:
        wid = n8n("POST", "/api/v1/workflows", wf)["id"]
        set_env(env_key, wid)
    assert wid not in LIVE_IDS
    n8n("POST", "/api/v1/workflows/%s/activate" % wid)
    return wid


def credential(env_key, name, token):
    e = env()
    if e.get(env_key, ""):
        return {"id": e[env_key], "name": name}
    made = n8n("POST", "/api/v1/credentials", {"name": name, "type": "httpHeaderAuth",
                                               "data": {"name": "api_access_token", "value": token}})
    set_env(env_key, made["id"])
    return {"id": made["id"], "name": name}


def config(apply):
    e = env()
    cfg = {"account_id": int(e["SANDBOX_CW_ACCOUNT_ID"]), "chatwoot_url": e["CHATWOOT_URL"].rstrip("/"),
           "supabase_url": e["SUPABASE_URL"].rstrip("/"), "sandbox_secret": e["SANDBOX_WEBHOOK_SECRET"],
           "teams": json.loads(e["SANDBOX_CW_TEAMS"]), "handover_id": e.get("SANDBOX_N8N_HANDOVER_ID", "") or "PENDING",
           "memory_round": e.get("SANDBOX_MEMORY_ROUND", "")}
    assert cfg["account_id"] != 2, "the sandbox account must not be account 2"
    if apply and "--fresh-memory" in sys.argv:
        cfg["memory_round"] = str(int(cfg["memory_round"] or 1) + 1)
        set_env("SANDBOX_MEMORY_ROUND", cfg["memory_round"])
    if apply:
        cfg["cred_admin"] = credential("SANDBOX_N8N_CRED_ADMIN", "SANDBOX Chatwoot admin", e["SANDBOX_CW_ADMIN_TOKEN"])
        cfg["cred_bot"] = credential("SANDBOX_N8N_CRED_BOT", "SANDBOX Chatwoot bot", e["SANDBOX_CW_BOT_TOKEN"])
    else:
        cfg["cred_admin"] = {"id": "DRY", "name": "SANDBOX Chatwoot admin"}
        cfg["cred_bot"] = {"id": "DRY", "name": "SANDBOX Chatwoot bot"}
    return cfg


def main():
    apply = "--apply" in sys.argv
    cfg = config(apply)
    router = sandboxify_router(load(LIVE_ROUTER), cfg)
    handover = sandboxify_handover(load(LIVE_HANDOVER), cfg)
    print("router copy: %d nodes | handover copy: %d nodes" % (len(router["nodes"]), len(handover["nodes"])))
    if apply:
        cfg["router_id"] = write(router, "SANDBOX_N8N_ROUTER_ID")
        cfg["handover_id"] = write(handover, "SANDBOX_N8N_HANDOVER_ID")
    live_bot = load(LIVE_BOT)
    bot = sandboxify_bot(live_bot, cfg)
    if "--section6" in sys.argv:
        from n8n_sandbox_section6 import section6
        supa = next(n for n in live_bot["nodes"] if n["name"] == "Anything newer?")["credentials"]["httpHeaderAuth"]
        bot = section6(bot, supa)
    print("bot copy: %d nodes%s" % (len(bot["nodes"]), " (with section 6)" if "--section6" in sys.argv else ""))
    if apply:
        print("router %s | handover %s | bot %s | all active"
              % (cfg["router_id"], cfg["handover_id"], write(bot, "SANDBOX_N8N_BOT_ID")))
    else:
        print("Dry run. --apply creates them.")


if __name__ == "__main__":
    main()
