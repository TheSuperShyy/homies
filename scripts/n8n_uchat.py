# -*- coding: utf-8 -*-
"""The UChat version of the WhatsApp bot (feature 21): the live bot's own logic, with UChat in front.

    python scripts/n8n_uchat.py                  # dry run: build the three workflows, show what differs from live
    python scripts/n8n_uchat.py --apply          # credentials, the translator, the hand-over copy, the bot copy; all active
    python scripts/n8n_uchat.py --uchat          # once: the tags and contact fields the hand-over writes, in UChat
    python scripts/n8n_uchat.py --wire           # after the owner made the "Michael" sub flow: UChat's default reply
    python scripts/n8n_uchat.py --tester USER_NS # give one UChat contact the test phone, so the bot knows who it is

WHAT IT IS
  UChat posts each new message to "UCHAT — WhatsApp bot", a copy of the live
  bot regenerated from live by this script, the way n8n_sandbox.py makes the
  sandbox (never edited by hand; re-run it after a change on live). Inside, the
  copy IS the live bot: the same Sort, prompt, reply checks, memory rules and
  tools. Every call the live bot makes to Chatwoot goes instead to "UCHAT —
  Chatwoot-compatible API", a translator that answers in Chatwoot's shape and
  does the work through UChat's API. So the logic has no second version.

WHAT DIFFERS FROM LIVE, AND WHY
  - The way in. UChat's External Request posts {"user_ns": ...} and nothing
    else. Three nodes in front of Sort read the contact and their newest
    message back from UChat and hand Sort the Chatwoot `message_created` event
    it has always read. The id is UChat's own, so the burst check (`Still the
    last word?`) compares like with like, and a button tap reads the same as
    typed text.
  - Who gets through is UCHAT_TEST_PHONES: a list of numbers (the owner's by
    default), or `all` for everyone, which it is since 3 Nov (the owner: "on
    meta we have a real number so we dont need to add anyone as test user").
    The copy uses the LIVE tools, so a ticket it opens is real, the same as on
    the live WhatsApp bot; with a list, a stranger gets nothing at all.
  - Chatwoot calls: the host becomes the translator's, the Chatwoot tokens the
    translator's door token.
  - Memory: the session key gets "-uchat", so the two bots never share one.
  - Log inbound / Log reply write the live `messages` table, which the dashboard
    reads, as source 'uchat' with ids prefixed 'uchat:' (log_as_uchat(); until 3
    Nov evening they were NoOps). `Anything newer?` still reads the UChat
    conversation, as the sandbox reads its Chatwoot one.
  - Show typing (Meta's call) is live's, for the UChat number (UCHAT_WA_PHONE_ID)
    with UChat's copy of WhatsApp's message id (typing(); 3 Nov, the owner: "yes
    i need it back").
  - The hand-over copy pages through the translator. Labels become UChat tags
    (what the copies read back) and UChat labels (what staff see), the note goes
    to a contact field, `team_note` (UChat's API has no internal note), and a
    team becomes its agent group through UCHAT_GROUPS (Chatwoot team id -> UChat
    group id; the four departments made 3 Nov with Chatwoot's names).
  - Speed: `Worth a word?`, a Gemini call of about 6 s, runs only when the
    message has a payment word (`A payment word?`). Its note could go out only
    then anyway (`A word first?` tests the same words on the same text), so the
    replies are the same and a message without one is answered about 6 s sooner.
  - Speed (quicker()): `Let them finish` waits 2 s, and none after a button tap
    (live: 4 s); the two reads of the way in go out at once; UCHAT_MODEL, if
    set, replaces the model (unset: live's 3.1 Pro).

SAFETY
  The live workflows are only read (GET). write() refuses every live and every
  sandbox id; every write targets an id this script created. UChat writes go
  only to the owner's workspace behind Uchat_api_key. No secret is printed.
"""
import copy
import json
import os
import re
import secrets
import sys
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from supabase_functions import env, set_env  # noqa: E402
from n8n_sandbox import (n8n, load, replace_once, free_spot, webhook, base_copy,  # noqa: E402
                         chat_log_from_chatwoot, LIVE_IDS, LIVE_BOT, LIVE_HANDOVER)
from n8n_layout import check as layout_check  # noqa: E402
from n8n_whatsapp_firstword import PAY_JS  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UCHAT = "https://www.uchat.com.au/api"
UA = "curl/8.9.1"  # UChat's Cloudflare refuses Python's default user agent (error 1010)
CW_HOST = "https://chat.srv1879140.hstgr.cloud"
CW_CREDS = ("Chatwoot admin (api_access_token)", "Chatwoot bot (api_access_token)")
FACADE_HOOK = "uchat-cw"
BOT_PATH = "homies-whatsapp-uchat"
SETUP_FILE = os.path.join(ROOT, "local", "uchat-prep", "uchat-setup.txt")

# What the hand-over writes, made once in UChat by --uchat: Chatwoot account 2's
# labels and conversation attributes on 3 Nov, plus the note's own field.
TAGS = ["bot-off", "handover", "handover-collections", "handover-operations", "handover-management",
        "handover-service", "escalated", "after-hours", "urgent"]
FIELDS = [("team_note", "longtext"), ("handover_at", "text"), ("handover_reason", "text"),
          ("handover_department", "text"), ("handover_source", "text"), ("handover_paged_at", "text"),
          ("handover_escalation", "number"), ("handover_answered_at", "text"), ("handover_channel", "text"),
          ("handover_reasons", "text")]


# --- UChat -----------------------------------------------------------------

def uchat(method, path, body=None):
    req = urllib.request.Request(UCHAT + path, method=method,
                                 data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None,
                                 headers={"Authorization": "Bearer " + env()["Uchat_api_key"].strip().strip('"'),
                                          "User-Agent": UA, "Accept": "application/json",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as x:
        raw = x.read().decode("utf-8", "replace")
        try:
            return x.code, json.loads(raw)
        except ValueError:
            return x.code, {"raw": raw[:300]}


def rows(answer):
    d = answer.get("data") if isinstance(answer, dict) else None
    return d if isinstance(d, list) else []


# --- configuration -----------------------------------------------------------

def digits_list(text):
    return [re.sub(r"\D", "", p) for p in re.split(r"[,\s;]+", text or "") if re.sub(r"\D", "", p)]


def config(apply):
    e = env()
    cfg = {"n8n": e["N8N_BASE_URL"].strip().rstrip("/"),
           "flow_ns": e.get("UCHAT_FLOW_NS", ""),
           "menu_node": e.get("UCHAT_MENU_NODE", "") or "Michael",
           # The copy's model (quicker()); empty keeps live's. 3 Nov: 3.7 Flash was tried
           # for speed and not taken (about 15 s, and inventions; WORKLOG 3 Nov).
           "model": e.get("UCHAT_MODEL", "").strip(),
           # One step per menu button (see MAP_WRITE): "Michael", "Michael 2", "Michael 3".
           "menu_nodes": [s.strip() for s in (e.get("UCHAT_MENU_NODES", "") or "Michael,Michael 2,Michael 3").split(",")
                          if s.strip()],
           "groups": json.loads(e.get("UCHAT_GROUPS", "") or "{}"),
           "agents": json.loads(e.get("UCHAT_AGENTS", "") or "{}"),
           # UCHAT_TEST_PHONES=all lets everyone through (3 Nov, the owner, after Ido got no
           # answer: "on meta we have a real number so we dont need to add anyone as test user").
           "everyone": e.get("UCHAT_TEST_PHONES", "").strip().lower() == "all",
           "test_phones": digits_list(e.get("UCHAT_TEST_PHONES", "") or e.get("OXS_MIRROR_PHONES", "")),
           "wa_phone_id": e.get("UCHAT_WA_PHONE_ID", "").strip(),   # the UChat number at Meta (typing())
           "webhook_secret": e.get("UCHAT_WEBHOOK_SECRET", ""), "door": e.get("UCHAT_FACADE_SECRET", ""),
           "handover_id": e.get("UCHAT_N8N_HANDOVER_ID", "") or "PENDING"}
    assert cfg["test_phones"] or cfg["everyone"], \
        "no test phone: set UCHAT_TEST_PHONES (numbers, or all) or OXS_MIRROR_PHONES in .env"
    if not cfg["flow_ns"]:
        st, a = uchat("GET", "/team-flows")
        flows = rows(a)
        assert st == 200 and len(flows) == 1, "expected exactly one UChat bot in the workspace, got %s" % len(flows)
        cfg["flow_ns"] = flows[0]["flow_ns"]
        if apply:
            set_env("UCHAT_FLOW_NS", cfg["flow_ns"])
    for key, name in (("webhook_secret", "UCHAT_WEBHOOK_SECRET"), ("door", "UCHAT_FACADE_SECRET")):
        if not cfg[key]:
            cfg[key] = secrets.token_urlsafe(32) if apply else "DRY-RUN-SECRET"
            if apply:
                set_env(name, cfg[key])
    if apply and "UCHAT_TEST_PHONES" not in e:
        set_env("UCHAT_TEST_PHONES", ",".join(cfg["test_phones"]))
    cfg["facade"] = cfg["n8n"] + "/webhook/" + FACADE_HOOK
    if apply:
        cfg["cred_api"] = header_credential("UCHAT_N8N_CRED_API", "UCHAT — UChat API (Bearer)", "Authorization",
                                            "Bearer " + e["Uchat_api_key"].strip().strip('"'))
        cfg["cred_door"] = header_credential("UCHAT_N8N_CRED_DOOR", "UCHAT — translator door", "api_access_token",
                                             cfg["door"])
        cfg["cred_typing"] = header_credential("UCHAT_N8N_CRED_TYPING", "UCHAT — WhatsApp typing (Meta)", "Authorization",
                                               "Bearer " + e["WHATSAPP_ACCESS_TOKEN"].strip().strip('"'))
    else:
        cfg["cred_api"] = {"id": "DRY", "name": "UCHAT — UChat API (Bearer)"}
        cfg["cred_door"] = {"id": "DRY", "name": "UCHAT — translator door"}
        cfg["cred_typing"] = {"id": "DRY", "name": "UCHAT — WhatsApp typing (Meta)"}
    return cfg


def header_credential(env_key, name, header, value):
    e = env()
    if e.get(env_key, ""):
        return {"id": e[env_key], "name": name}
    made = n8n("POST", "/api/v1/credentials", {"name": name, "type": "httpHeaderAuth",
                                               "data": {"name": header, "value": value}})
    set_env(env_key, made["id"])
    return {"id": made["id"], "name": name}


# --- the translator ------------------------------------------------------------

DOOR_AND_IDS = r"""
const SECRET = %(door)s;
const FLOW = %(flow)s;
const j = $input.first().json;
const p = j.params || {};
const conv = String(p.conv || '').replace(/\D/g, '');
const user_ns = FLOW + 'u' + conv;
const out = (o) => [{ json: Object.assign({ action: p.action, conv: Number(conv), user_ns }, o) }];
if ((j.headers || {})['api_access_token'] !== SECRET) return out({ skip: true, code: 401, answer: { error: 'unauthorized' } });
if (!conv) return out({ skip: true, code: 404, answer: { error: 'no conversation' } });
"""

MAP_READ = DOOR_AND_IDS + r"""
// Two reads the copies make: a conversation's messages (`Read the photos`,
// `Anything newer?`, the way in) and the conversation itself (the way in, and
// `Read the conversation` in the hand-over, which the copy asks for as /info).
if (p.action === 'messages') {
  return out({ call: { path: '/subscriber/chat-messages?user_ns=' + encodeURIComponent(user_ns) + '&include_bot=1&limit=50' } });
}
if (p.action === 'info') {
  return out({ call: { path: '/subscriber/get-info?user_ns=' + encodeURIComponent(user_ns) } });
}
return out({ skip: true, code: 404, answer: { error: 'not mapped: GET ' + p.action } });
"""

MAP_WRITE = DOOR_AND_IDS + r"""
const AGENTS = %(agents)s;   // Chatwoot user id -> UChat agent id
const GROUPS = %(groups)s;   // Chatwoot team id -> UChat agent group id
// The sub flow steps menu buttons run, one per button: each holds the same
// External Request. UChat makes a button's WhatsApp id from its target, and
// WhatsApp refuses two buttons with one id (#131009 "Duplicate button id",
// 3 Nov), so no two buttons may share a step.
const MENU_NODES = %(menu)s;
const b = j.body || {};
// Every reply goes as the BOT through send-content. UChat logs send-text as an
// agent's message, and an agent's message pauses the bot for that contact for
// 30 minutes (seen 3 Nov), so the bot would silence itself after one reply.
const asBot = (messages) => ({ method: 'POST', path: '/subscriber/send-content',
  body: { user_ns, send_as_agent: 0, data: { version: 'v1', content: { messages } } } });
switch (p.action) {
  case 'messages': {
    // UChat's API has no internal note: a private note becomes the contact's
    // `team_note` field, which staff see beside the chat.
    if (b.private === true) {
      return out({ kind: 'note', content: b.content, call: { method: 'PUT', path: '/subscriber/set-user-fields-by-name',
        body: { user_ns, data: [{ name: 'team_note', value: String(b.content || '') }] } } });
    }
    const items = (b.content_attributes || {}).items;
    if (b.content_type === 'input_select' && Array.isArray(items) && items.length) {
      // WhatsApp shows at most three reply buttons of 20 characters.
      const buttons = items.slice(0, Math.min(3, MENU_NODES.length)).map((i, k) => (
        { type: 'node', caption: String(i.title || i.value || '').slice(0, 20), target: MENU_NODES[k] }));
      return out({ kind: 'menu', content: b.content, call: asBot([{ type: 'text', text: String(b.content || ''), buttons }]) });
    }
    return out({ kind: 'text', content: b.content, call: asBot([{ type: 'text', text: String(b.content || '') }]) });
  }
  case 'toggle_status': {
    const s = { open: 'open', resolved: 'done', pending: 'pending', snoozed: 'pending' }[String(b.status || 'open')] || 'open';
    return out({ kind: 'status', call: { method: 'POST', path: '/subscriber/move-chat-to', body: { user_ns, status: s } } });
  }
  case 'assignments': {
    if ('team_id' in b) {
      const g = GROUPS[String(b.team_id)];
      if (!g) return out({ skip: true, answer: { id: b.team_id, note: 'no UChat agent group for this team' } });
      return out({ kind: 'team', call: { method: 'POST', path: '/subscriber/assign-agent-group', body: { user_ns, agent_group_id: g } } });
    }
    if (b.assignee_id == null) return out({ kind: 'unassign', call: { method: 'POST', path: '/subscriber/unassign-agent', body: { user_ns } } });
    const a = AGENTS[String(b.assignee_id)];
    if (!a) return out({ skip: true, answer: { id: b.assignee_id, note: 'no UChat agent for this user' } });
    return out({ kind: 'assign', call: { method: 'POST', path: '/subscriber/assign-agent', body: { user_ns, agent_id: a } } });
  }
  case 'labels': {
    const names = (b.labels || []).map(String).filter(Boolean);
    if (!names.length) return out({ skip: true, answer: { payload: [] } });
    // Two calls, one item each. The tag is what the copies read back (`bot-off`:
    // UChat's contact record carries tags, not labels). The label is what staff
    // see on the chat in Live Chat, as in Chatwoot (3 Nov: the 8 labels made in
    // UChat with Chatwoot's names). "Answer a write" answers from the first.
    return [
      ...out({ kind: 'labels', labels: names, call: { method: 'POST', path: '/subscriber/add-tags-by-name',
        body: { user_ns, data: names.map(n => ({ tag_name: n })) } } }),
      ...out({ kind: 'labels', labels: names, call: { method: 'POST', path: '/subscriber/add-labels-by-name',
        body: { user_ns, data: names.map(n => ({ label_name: n })) } } }),
    ];
  }
  case 'custom_attributes': {
    const ca = b.custom_attributes || {};
    const data = Object.keys(ca).map(k => ({ name: k, value: String(ca[k] == null ? '' : ca[k]) }));
    if (!data.length) return out({ skip: true, answer: {} });
    return out({ kind: 'fields', call: { method: 'PUT', path: '/subscriber/set-user-fields-by-name', body: { user_ns, data } } });
  }
  case 'toggle_priority': {
    if (!['urgent', 'high'].includes(String(b.priority))) return out({ skip: true, answer: {} });
    return out({ kind: 'priority', call: { method: 'POST', path: '/subscriber/add-tags-by-name',
      body: { user_ns, data: [{ tag_name: 'urgent' }] } } });
  }
}
return out({ skip: true, code: 404, answer: { error: 'not mapped: POST ' + p.action } });
"""

ANSWER_READ = r"""
// UChat's answer, in the shape Chatwoot gives the same read.
const m = $('Map a read').first().json;
const r = $input.first().json || {};
const body = r.body || {};
if (m.action === 'messages') {
  const list = Array.isArray(body.data) ? body.data : [];
  const payload = list.map(x => {
    const pl = x.payload || {};
    const image = x.msg_type === 'image' && pl.url;
    return {
      id: Number(x.id), content: String(x.content || pl.text || ''), private: false,
      // UChat's copy of WhatsApp's own message id, as Chatwoot's source_id: the typing dots need it.
      source_id: String(x.mid || ''),
      message_type: x.type === 'in' ? 0 : 1, content_type: 'text', created_at: Number(x.ts) || 0,
      attachments: image ? [{ file_type: 'image', data_url: pl.url }] : [],
      sender: { type: x.type === 'in' ? 'contact' : (x.type === 'agent' ? 'user' : 'agent_bot') },
    };
  });
  return [{ json: { code: r.statusCode && r.statusCode >= 300 ? 502 : 200, answer: { payload } } }];
}
const u = (body.data && !Array.isArray(body.data)) ? body.data : body;
if (!u || !u.user_ns) return [{ json: { code: 404, answer: { error: 'no such contact' } } }];
let phone = String(u.phone || '').replace(/\D/g, '');
if (!phone && /^\d{9,15}$/.test(String(u.user_id || ''))) phone = String(u.user_id);
const ca = {};
for (const f of (u.user_fields || [])) if (f && f.name) ca[f.name] = f.value;
const name = u.name || [u.first_name, u.last_name].filter(Boolean).join(' ');
return [{ json: { code: 200, answer: {
  id: m.conv, status: 'open', labels: (u.tags || []).map(t => t && t.name).filter(Boolean),
  custom_attributes: ca, additional_attributes: {}, messages: [],
  meta: { sender: { phone_number: phone ? '+' + phone : '', name }, assignee: null, assignee_type: null },
} } }];
"""

ANSWER_WRITE = r"""
// What Chatwoot would have said, so the copies' next steps read the same.
const m = $('Map a write').first().json;
const r = $input.first().json || {};
const ok = (r.statusCode || 200) < 300 && !(r.body && r.body.status === 'error');
let answer;
if (m.action === 'messages') {
  answer = { id: Date.now(), content: m.content || '', message_type: 1, private: m.kind === 'note', status: ok ? 'sent' : 'failed' };
} else if (m.action === 'labels') {
  answer = { payload: m.labels || [] };
} else {
  answer = { payload: { success: ok } };
}
return [{ json: { code: ok ? 200 : 502, answer, uchat: r.body } }];
"""

FACADE_NOTE = ("### UCHAT translator (feature 21)\n"
               "Generated by `scripts/n8n_uchat.py`; change the script, not this canvas.\n\n"
               "Answers the Chatwoot calls of \"UCHAT — WhatsApp bot\" and \"UCHAT — Hand to a person\" "
               "in Chatwoot's shape, and does the work through UChat's API. Door: the `api_access_token` header.")


def js(text, **values):
    return text % {k: json.dumps(v, ensure_ascii=False) for k, v in values.items()}


def http_node(name, pos, method, cred):
    return {"id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": pos, "alwaysOutputData": True, "onError": "continueRegularOutput",
            "credentials": {"httpHeaderAuth": dict(cred)},
            "parameters": {"method": method, "url": "={{ 'https://www.uchat.com.au/api' + $json.call.path }}",
                           "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
                           "sendHeaders": True,
                           "headerParameters": {"parameters": [{"name": "User-Agent", "value": UA}]},
                           "options": {"timeout": 20000,
                                       "response": {"response": {"fullResponse": True, "neverError": True}}}}}


def if_node(name, pos, expr):
    return {"id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.if", "typeVersion": 2, "position": pos,
            "parameters": {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose",
                                                      "version": 1},
                                          "conditions": [{"id": "go", "leftValue": expr, "rightValue": "",
                                                          "operator": {"type": "boolean", "operation": "true",
                                                                       "singleValue": True}}],
                                          "combinator": "and"}, "options": {}}}


def code_node(name, pos, code):
    return {"id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": pos, "parameters": {"jsCode": code}}


def facade(cfg):
    v = dict(door=cfg["door"], flow=cfg["flow_ns"])
    write_http = http_node("UChat write", [720, 480], "={{ $json.call.method }}", cfg["cred_api"])
    write_http["parameters"].update({"sendBody": True, "specifyBody": "json",
                                     "jsonBody": "={{ JSON.stringify($json.call.body) }}"})
    nodes = [
        {"id": str(uuid.uuid4()), "name": "Chatwoot-shaped call", "type": "n8n-nodes-base.webhook", "typeVersion": 2,
         "position": [0, 300], "webhookId": FACADE_HOOK,
         "parameters": {"multipleMethods": True, "path": "api/v1/accounts/:acc/conversations/:conv/:action",
                        "responseMode": "responseNode", "options": {}}},
        code_node("Map a read", [240, 180], js(MAP_READ, **v)),
        code_node("Map a write", [240, 420], js(MAP_WRITE, menu=cfg["menu_nodes"], agents=cfg["agents"],
                                                 groups=cfg["groups"], **v)),
        if_node("Read allowed?", [480, 180], "={{ $json.skip !== true }}"),
        if_node("Write needed?", [480, 420], "={{ $json.skip !== true }}"),
        http_node("UChat read", [720, 120], "GET", cfg["cred_api"]),
        write_http,
        code_node("Answer a read", [960, 120], ANSWER_READ),
        code_node("Answer a write", [960, 480], ANSWER_WRITE),
        {"id": str(uuid.uuid4()), "name": "Answer in Chatwoot's shape", "type": "n8n-nodes-base.respondToWebhook",
         "typeVersion": 1.1, "position": [1200, 300],
         "parameters": {"respondWith": "json", "responseBody": "={{ JSON.stringify($json.answer) }}",
                        "options": {"responseCode": "={{ $json.code || 200 }}"}}},
        {"id": str(uuid.uuid4()), "name": "UCHAT translator", "type": "n8n-nodes-base.stickyNote", "typeVersion": 1,
         "position": [0, -60], "parameters": {"content": FACADE_NOTE, "width": 560, "height": 200, "color": 5}},
    ]
    to = lambda name: [{"node": name, "type": "main", "index": 0}]  # noqa: E731
    conns = {
        "Chatwoot-shaped call": {"main": [to("Map a read"), to("Map a write")]},  # GET first, POST second
        "Map a read": {"main": [to("Read allowed?")]},
        "Map a write": {"main": [to("Write needed?")]},
        "Read allowed?": {"main": [to("UChat read"), to("Answer in Chatwoot's shape")]},
        "Write needed?": {"main": [to("UChat write"), to("Answer in Chatwoot's shape")]},
        "UChat read": {"main": [to("Answer a read")]},
        "UChat write": {"main": [to("Answer a write")]},
        "Answer a read": {"main": [to("Answer in Chatwoot's shape")]},
        "Answer a write": {"main": [to("Answer in Chatwoot's shape")]},
    }
    wf = {"name": "UCHAT — Chatwoot-compatible API", "nodes": nodes, "connections": conns,
          "settings": {"executionOrder": "v1"}}
    layout_check(nodes, wf["name"])
    return wf


# --- the copies ------------------------------------------------------------------

COPY_NOTE = ("### UCHAT copy (feature 21)\n"
             "Generated from the live workflow \"%s\" by `scripts/n8n_uchat.py`. Do not edit it here: "
             "change the script and re-run it.\n\n"
             "Its Chatwoot calls go to \"UCHAT — Chatwoot-compatible API\", which does them in UChat. "
             "The tools are the live ones. Who gets through is UCHAT_TEST_PHONES in .env (all: everyone).")


def copy_note(wf, live_name):
    xs = [n["position"][0] for n in wf["nodes"]]
    ys = [n["position"][1] for n in wf["nodes"]]
    wf["nodes"].append({"id": str(uuid.uuid4()), "name": "UCHAT copy", "type": "n8n-nodes-base.stickyNote",
                        "typeVersion": 1, "position": [min(xs), min(ys) - 320],
                        "parameters": {"content": COPY_NOTE % live_name, "width": 560, "height": 220, "color": 5}})


def to_facade(n, cfg):
    """A Chatwoot call becomes the same call on the translator, with the door token."""
    p = n.get("parameters") or {}
    url = p.get("url")
    if isinstance(url, str) and CW_HOST in url:
        p["url"] = url.replace(CW_HOST, cfg["facade"])
    for ctype, c in list((n.get("credentials") or {}).items()):
        if c.get("name") in CW_CREDS:
            n["credentials"][ctype] = dict(cfg["cred_door"])


def uchatify_handover(live, cfg):
    out = base_copy(live, "UCHAT — Hand to a person")
    for n in out["nodes"]:
        to_facade(n, cfg)
        if n["name"] == "Read the conversation":
            # The conversation itself has no action segment on Chatwoot; the
            # translator's one webhook needs one, so the copy asks for /info.
            assert n["parameters"]["url"].endswith("}}"), "Read the conversation's URL changed shape on live"
            n["parameters"]["url"] += "/info"
    copy_note(out, live["name"])
    return out


FROM_UCHAT = r"""
// UChat's External Request posts {user_ns} and nothing else. Who is writing and
// what they wrote were read back from UChat by the node before this one (two
// items, read at once: the contact, then its messages), so a tap reads the same
// as typed text and the message id is UChat's own, the id `Anything newer?` will
// see. This hands Sort the Chatwoot event it has always read, so Sort and
// everything after it are the live bot's, unchanged.
//
// Who gets through: everyone, or only the test phones (UCHAT_TEST_PHONES). Either
// way the copy runs the LIVE tools, so what it opens is real.
const EVERYONE = %(everyone)s;
const TEST_PHONES = %(phones)s;
const hook = $('WhatsApp').first(1).json;
const both = $input.all();
const who = (both[0] && both[0].json) || {};
const msgs = ((both[1] && both[1].json) || {}).payload || [];
const sender = (who.meta || {}).sender || {};
const phone = String(sender.phone_number || '').replace(/\D/g, '');
const newest = msgs.filter(m => m.message_type === 0).sort((a, b) => b.id - a.id)[0];
const skip = (why) => [{ json: { query: hook.query || {}, body: { event: 'uchat_skipped', reason: why } } }];
if (!who.id) return skip('no such contact');
if (!newest) return skip('nothing from the contact yet');
if (!phone) return skip('no phone on the contact');
if (!EVERYONE && !TEST_PHONES.includes(phone)) return skip('not a test phone');
const contact = { type: 'contact', phone_number: '+' + phone, name: sender.name || '' };
return [{ json: { query: hook.query || {}, body: {
  event: 'message_created', message_type: 'incoming', private: false,
  id: newest.id, content: newest.content || '', attachments: newest.attachments || [],
  source_id: String(newest.source_id || ''),   // WhatsApp's message id, for Show typing
  sender: contact,
  conversation: { id: who.id, status: 'open', labels: who.labels || [],
                  meta: { sender: contact, assignee: null, assignee_type: null } },
} } }];
"""


def facade_get(name, pos, url, cfg):
    return {"id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": pos, "alwaysOutputData": True, "onError": "continueRegularOutput",
            "credentials": {"httpHeaderAuth": dict(cfg["cred_door"])},
            "parameters": {"method": "GET", "url": url, "authentication": "genericCredentialType",
                           "genericAuthType": "httpHeaderAuth", "options": {"timeout": 15000}}}


TWO_READS = r"""
// Both reads need only the contact id, so they go out together: the next node
// sends one request per item, all at once (3 Nov, for speed: one after the
// other they took about a second).
const conv = (String((($input.first().json || {}).body || {}).user_ns || '').match(/u(\d+)$/) || [null, '0'])[1];
const base = %(base)s + conv;
return [{ json: { url: base + '/info' } }, { json: { url: base + '/messages' } }];
"""


def way_in(wf, cfg):
    """WhatsApp (POST) -> Ask UChat -> Who and what? (UChat), both reads at once -> From UChat -> Sort."""
    hook = next(n for n in wf["nodes"] if n["name"] == "WhatsApp")
    x, y = hook["position"]
    ask = code_node("Ask UChat", free_spot(wf["nodes"], x, y + 240),
                    js(TWO_READS, base=cfg["facade"] + "/api/v1/accounts/2/conversations/"))
    wf["nodes"].append(ask)
    both = facade_get("Who and what? (UChat)", free_spot(wf["nodes"], x + 240, y + 240), "={{ $json.url }}", cfg)
    wf["nodes"].append(both)
    frm = code_node("From UChat", free_spot(wf["nodes"], x + 240, y + 120), js(FROM_UCHAT, phones=cfg["test_phones"],
                                                                                    everyone=cfg["everyone"]))
    wf["nodes"].append(frm)
    to = lambda name: [{"node": name, "type": "main", "index": 0}]  # noqa: E731
    c = wf["connections"]
    assert [[t["node"] for t in br] for br in c["WhatsApp"]["main"]] == [["Sort"], ["Sort"]], \
        "the live trigger's wiring changed; read it before re-running"
    c["WhatsApp"]["main"] = [[], to("Ask UChat")]  # GET goes nowhere; UChat only POSTs
    c["Ask UChat"] = {"main": [to("Who and what? (UChat)")]}
    c["Who and what? (UChat)"] = {"main": [to("From UChat")]}
    c["From UChat"] = {"main": [to("Sort")]}


def quicker(wf, cfg):
    """The UChat copy's speed settings (3 Nov, owner: "its too long i need like 10s max").

    - The model, only when UCHAT_MODEL is set: it feeds all three of the copy's
      agents, as 3.1 Pro does on live. Empty keeps live's (3 Nov: 3.7 Flash with
      thinking low answered in about 15 s on this path, with inventions).
    - `Let them finish` waits 2 s for a typed message (live: 4) and not at all
      after a button tap, which is one finished action (`tap_now`, from Sort).
    """
    nodes = {n["name"]: n for n in wf["nodes"]}
    model = nodes["OpenRouter"]
    assert model["type"] == "@n8n/n8n-nodes-langchain.lmChatOpenRouter", "the model node changed on live"
    if cfg["model"]:
        model["parameters"]["model"] = cfg["model"]
    wait = nodes["Let them finish"]["parameters"]
    assert wait.get("amount") == 4 and wait.get("unit") == "seconds", "Let them finish changed on live: %r" % wait
    wait["amount"] = "={{ $json.tap_now === true ? 0 : 2 }}"


PAY_GATE_NOTE = ("UCHAT copy only, for speed: Worth a word? runs only on a message with a payment word. "
                 "A word first? sends its note only then, so on any other message it was thrown away.")


def word_only_on_pay(wf):
    """Add who -> A payment word? -> Worth a word? (yes) or Carry on (no).

    `Worth a word?` is a Gemini call (6.3 s of a 33 s turn on 3 Nov) whose note
    `A word first?` lets out only when the resident's own message has a payment
    word (firstword.PAY_JS, tested on `Still the last word?`'s text). This asks
    the same question first, on the same text, so the replies do not change: a
    message without a payment word skips a call whose answer was never used.
    """
    nodes = {n["name"]: n for n in wf["nodes"]}
    c = wf["connections"]
    outs = lambda name: [[t["node"] for t in br] for br in c[name]["main"]]  # noqa: E731
    assert (outs("Add who"), outs("Worth a word?"), outs("A word first?")) == \
        ([["Worth a word?"]], [["A word first?"]], [["Say it now"], ["Carry on"]]), \
        "the pre-check's wiring changed on live; read it before re-running"
    word = nodes["A word first?"]["parameters"]["conditions"]["conditions"]
    assert len(word) == 1 and PAY_JS in word[0]["leftValue"] and "$('Still the last word?')" in word[0]["leftValue"], \
        "A word first? no longer tests firstword.PAY_JS on the resident's message"
    # Carry on reads Worth a word? only when Say it now ran, which needs it to have run.
    carry = nodes["Carry on"]["parameters"]
    carry["jsonOutput"] = replace_once(
        carry["jsonOutput"],
        "const t = String($('Worth a word?').first().json.output || '').trim(); return sent && ",
        "if (!sent) return ''; const t = String($('Worth a word?').first().json.output || '').trim(); return ")
    x, y = nodes["Worth a word?"]["position"]
    gate = if_node("A payment word?", free_spot(wf["nodes"], x, y - 240),
                   "={{ (() => { let said = ''; try { said = String($('Still the last word?').first().json.text || ''); } "
                   "catch (e) { said = ''; } return %s.test(said); })() }}" % PAY_JS)
    gate.update({"notes": PAY_GATE_NOTE, "notesInFlow": True})
    wf["nodes"].append(gate)
    to = lambda name: [{"node": name, "type": "main", "index": 0}]  # noqa: E731
    c["Add who"]["main"] = [to("A payment word?")]
    c["A payment word?"] = {"main": [to("Worth a word?"), to("Carry on")]}


TYPING_BODY = r"""={{ (() => {
  // WhatsApp's id of the resident's message: UChat keeps it (`mid`), the translator
  // hands it on as source_id, and From UChat puts it where Sort's event has it.
  let id = '';
  try { id = String($('From UChat').first().json.body.source_id || ''); } catch (e) { id = ''; }
  return JSON.stringify({ messaging_product: 'whatsapp', status: 'read', message_id: id,
                          typing_indicator: { type: 'text' } });
})() }}"""


def typing(wf, cfg):
    """Show typing / Show typing again: live's Meta call, for the UChat number.

    Live sends Meta's typing indicator (which also marks the message read) with
    the id Chatwoot passes on. The copy has UChat's copy of the same id, so the
    call is live's own with two things changed: the UChat number's id
    (UCHAT_WA_PHONE_ID) and a credential of its own holding the system-user
    token (WHATSAPP_ACCESS_TOKEN). Owner, 3 Nov: "yes i need it back".
    """
    phone_id = cfg["wa_phone_id"]
    assert re.fullmatch(r"\d{10,20}", phone_id), "set UCHAT_WA_PHONE_ID (the UChat number's id at Meta) in .env"
    for name in ("Show typing", "Show typing again"):
        n = next(x for x in wf["nodes"] if x["name"] == name)
        p = n["parameters"]
        url = re.fullmatch(r"https://graph\.facebook\.com/(v\d+\.\d+)/\d+/messages", p.get("url") or "")
        assert url and "typing_indicator" in p["jsonBody"] and "status: 'read'" in p["jsonBody"] \
            and "$('WhatsApp').first(b).json.body.source_id" in p["jsonBody"], "%s changed on live" % name
        p["url"] = "https://graph.facebook.com/%s/%s/messages" % (url.group(1), phone_id)
        p["jsonBody"] = TYPING_BODY
        n["credentials"] = {"httpHeaderAuth": dict(cfg["cred_typing"])}


def log_as_uchat(wf):
    """Log inbound / Log reply write the live `messages` table, marked as UChat's.

    The dashboard's Conversations page reads that table, so without these the UChat
    chats were missing from it (3 Nov evening, owner: "lets connect everything in the
    uchat?"). Live's own two writes, with two things changed:
    - `source` is 'uchat', so each row says which bot wrote it.
    - UChat numbers our workspace's messages from 1, the range Chatwoot's ids are in,
      and `external_id` is unique. So the copy's ids get a 'uchat:' prefix, here and on
      the photo it keeps (`Keep the photo` -> request_media.message_external_id), and a
      photo still lands in the bubble it came with.
    Both writes keep live's onError (continue), so a failed write never stops a reply.
    """
    nodes = {n["name"]: n for n in wf["nodes"]}
    inbound = nodes["Log inbound"]["parameters"]
    inbound["jsonBody"] = replace_once(inbound["jsonBody"], "external_id: $json.message_id,",
                                       "external_id: 'uchat:' + $json.message_id,")
    inbound["jsonBody"] = replace_once(inbound["jsonBody"], "source: 'n8n'", "source: 'uchat'")
    reply = nodes["Log reply"]["parameters"]
    reply["jsonBody"] = replace_once(reply["jsonBody"], "source: 'n8n'", "source: 'uchat'")
    photo = nodes["Keep the photo"]["parameters"]
    photo["jsonBody"] = replace_once(photo["jsonBody"], "message_id: $('Sort').first().json.message_id,",
                                     "message_id: 'uchat:' + $('Sort').first().json.message_id,")
    for name in ("Log inbound", "Log reply", "Keep the photo"):
        assert nodes[name].get("onError") == "continueRegularOutput", "%s no longer continues on error on live" % name


def uchatify_bot(live, cfg):
    out = base_copy(live, "UCHAT — WhatsApp bot")
    for n in out["nodes"]:
        to_facade(n, cfg)
        if n["type"] == "n8n-nodes-base.executeWorkflow":
            n["parameters"]["workflowId"] = {"__rl": True, "value": cfg["handover_id"], "mode": "id"}
        if n["name"] == "Sort":
            code = n["parameters"]["jsCode"]
            shared = re.search(r'const SHARED = "([^"]+)"', code).group(1)
            n["parameters"]["jsCode"] = replace_once(code, 'const SHARED = "%s"' % shared,
                                                     'const SHARED = "%s"' % cfg["webhook_secret"])
    memories = [n for n in out["nodes"] if n["type"] == "@n8n/n8n-nodes-langchain.memoryBufferWindow"]
    assert len(memories) == 1, "expected one memory node"
    memories[0]["parameters"]["sessionKey"] += "-uchat"
    webhook(out, BOT_PATH)
    log_as_uchat(out)
    typing(out, cfg)
    chat_log_from_chatwoot(out, {"chatwoot_url": cfg["facade"], "account_id": 2, "cred_admin": cfg["cred_door"]})
    way_in(out, cfg)
    word_only_on_pay(out)
    quicker(out, cfg)
    leftover = [n["name"] for n in out["nodes"] if CW_HOST in json.dumps(n.get("parameters") or {})]
    assert not leftover, "Chatwoot calls left in the copy: %s" % leftover
    copy_note(out, live["name"])
    return out


def changed(live, cp):
    """Node names that differ from live: added, removed, or with other parameters."""
    a = {n["name"]: n for n in live["nodes"]}
    b = {n["name"]: n for n in cp["nodes"]}
    added = sorted(set(b) - set(a))
    removed = sorted(set(a) - set(b))
    diff = sorted(k for k in set(a) & set(b)
                  if json.dumps([a[k].get("parameters"), a[k].get("type"), a[k].get("credentials")], sort_keys=True)
                  != json.dumps([b[k].get("parameters"), b[k].get("type"), b[k].get("credentials")], sort_keys=True))
    return added, removed, diff


# --- writing -------------------------------------------------------------------

def protected():
    e = env()
    return LIVE_IDS | {e.get(k) for k in ("SANDBOX_N8N_BOT_ID", "SANDBOX_N8N_HANDOVER_ID", "SANDBOX_N8N_ROUTER_ID")
                       if e.get(k)}


def write(wf, env_key):
    """POST a new UCHAT workflow, or PUT the one this script made before; then activate it."""
    wid = env().get(env_key, "")
    assert wid not in protected(), "refusing to write a live or sandbox workflow"
    if wid:
        n8n("PUT", "/api/v1/workflows/" + wid, wf)
    else:
        wid = n8n("POST", "/api/v1/workflows", wf)["id"]
        set_env(env_key, wid)
    assert wid not in protected()
    n8n("POST", "/api/v1/workflows/%s/activate" % wid)
    return wid


def setup_file(cfg):
    os.makedirs(os.path.dirname(SETUP_FILE), exist_ok=True)
    with open(SETUP_FILE, "w", encoding="utf-8") as f:
        f.write("UChat External Request for the \"Michael\" sub flow (feature 21). Not in git: the URL holds a secret.\n\n"
                "Method:  POST\n"
                "URL:     %s/webhook/%s?s=%s\n"
                "Body:    JSON, exactly this, with the User Ns field put in through UChat's field picker:\n"
                "         {\"user_ns\": \"<User Ns>\"}\n"
                "Name the step: %s\n"
                "Then duplicate it, one step per menu button: %s. WhatsApp refuses two\n"
                "buttons with one id, and UChat makes a button's id from its step.\n"
                % (cfg["n8n"], BOT_PATH, cfg["webhook_secret"], cfg["menu_nodes"][0], ", ".join(cfg["menu_nodes"])))


# --- UChat setup -------------------------------------------------------------------

def uchat_setup():
    st, a = uchat("GET", "/flow/tags?limit=100")
    have = {t.get("name") for t in rows(a)}
    for t in TAGS:
        if t not in have:
            st, r = uchat("POST", "/flow/create-tag", {"name": t})
            print("tag %-22s %s" % (t, st))
    st, a = uchat("GET", "/flow/user-fields?limit=100")
    have = {f.get("name") for f in rows(a)}
    for name, kind in FIELDS:
        if name not in have:
            st, r = uchat("POST", "/flow/create-user-field",
                          {"name": name, "var_type": kind, "value": "", "description": "feature 21, the hand-over"})
            print("field %-22s %s" % (name, st))
    st, a = uchat("GET", "/flow/tags?limit=100")
    st2, b = uchat("GET", "/flow/user-fields?limit=100")
    print("UChat now: %d tags, %d contact fields" % (len(rows(a)), len(rows(b))))


def wire(cfg):
    st, a = uchat("GET", "/flow/subflows?limit=100")
    subs = [s for s in rows(a) if str(s.get("name", "")).strip().lower() == cfg["menu_node"].lower()]
    assert len(subs) == 1, "expected one sub flow named %r, found %d" % (cfg["menu_node"], len(subs))
    ns = subs[0].get("sub_flow_ns") or subs[0].get("ns")
    print("default reply ->", uchat("POST", "/flow/set-default-reply", {"status": "active", "sub_flow_ns": ns})[0])
    print("web chat start ->", uchat("POST", "/flow/set-web-chat-widget-default-start-flow", {"sub_flow_ns": ns})[0])
    print("read back:", json.dumps(uchat("GET", "/flow/get-default-reply")[1].get("data"), ensure_ascii=False))


def tester(cfg, user_ns):
    assert cfg["test_phones"], "--tester needs a number: UCHAT_TEST_PHONES is 'all'"
    phone = "+" + cfg["test_phones"][0]
    st, r = uchat("PUT", "/subscriber/update", {"user_ns": user_ns, "phone": phone})
    st2, info = uchat("GET", "/subscriber/get-info?user_ns=" + user_ns)
    u = info.get("data", info) if isinstance(info, dict) else {}
    got = re.sub(r"\D", "", str(u.get("phone") or ""))
    print("update %s; the contact's phone is %s" % (st, "the test phone" if got == cfg["test_phones"][0] else "NOT set"))


# --- main ------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    # 10 Nov 2026: the bot runs on Chatwoot again (the owner: "move to the chatwoot now that it passed").
    # The Israeli number sits in Chatwoot's inbox 1 and the UChat copy is switched off. --apply would
    # switch the copy back on (write() activates every workflow it writes), and since UChat's app still
    # gets the number's messages, both bots would answer. Only a rollback to UChat may do it.
    if (apply or "--wire" in args) and "--back-to-uchat" not in args:
        sys.exit("REFUSING: since 10 Nov the bot runs on Chatwoot (CONTEXT, HANDOVER). --apply or --wire "
                 "would switch the UChat copy back on and both bots would answer. Only for a rollback to "
                 "UChat: add --back-to-uchat (and undo the Chatwoot side first: HANDOVER, the rollback).")
    cfg = config(apply or "--wire" in args or "--tester" in args)
    if "--uchat" in args:
        return uchat_setup()
    if "--wire" in args:
        return wire(cfg)
    if "--tester" in args:
        return tester(cfg, args[args.index("--tester") + 1])
    fac = facade(cfg)
    live_handover, live_bot = load(LIVE_HANDOVER), load(LIVE_BOT)
    if apply:
        cfg["facade_id"] = write(fac, "UCHAT_N8N_FACADE_ID")
        cfg["handover_id"] = write(uchatify_handover(live_handover, cfg), "UCHAT_N8N_HANDOVER_ID")
    handover = uchatify_handover(live_handover, cfg)
    bot = uchatify_bot(live_bot, cfg)
    for live, cp in ((live_handover, handover), (live_bot, bot)):
        added, removed, diff = changed(live, cp)
        print("%s: %d nodes (live %d)\n  added:   %s\n  removed: %s\n  changed: %s"
              % (cp["name"], len(cp["nodes"]), len(live["nodes"]), ", ".join(added) or "-",
                 ", ".join(removed) or "-", ", ".join(diff) or "-"))
    print("%s: %d nodes, layout ok" % (fac["name"], len(fac["nodes"])))
    if apply:
        bot_id = write(bot, "UCHAT_N8N_BOT_ID")
        setup_file(cfg)
        print("translator %s | hand-over %s | bot %s | all active" % (cfg["facade_id"], cfg["handover_id"], bot_id))
        print("UChat's External Request settings: %s" % os.path.relpath(SETUP_FILE, ROOT))
    else:
        print("Dry run. --apply creates them.")


if __name__ == "__main__":
    main()
