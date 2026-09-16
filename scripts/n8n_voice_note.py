# -*- coding: utf-8 -*-
"""Build "Homies — Voice team note": a voice call's way into the Chatwoot team mention.

    python scripts/n8n_voice_note.py                      # dry run
    python scripts/n8n_voice_note.py --apply              # create, or update in place
    python scripts/n8n_voice_note.py --apply --publish    # ...and activate (registers the webhook)
    python scripts/n8n_voice_note.py --apply --rotate-secret   # new N8N_VOICE_NOTE_SECRET + credential

WHY (14 Sep)
The inbound voice agent got the chatbot's durability: past its threshold it
calls `notify_team` and tells the caller the team knows. On WhatsApp that
sentence is true because the workflow fires "Homies — Hand to a person" on the
resident's Chatwoot conversation. A voice call has no conversation, so the
Edge Function behind `notify_team` posts here instead, and this workflow gives
the call one -- a contact and a conversation in the "Homies — Voice" inbox
(scripts/chatwoot_voice_inbox.py) -- then hands it to the same sub-workflow
with `channel: voice`. The note the team reads is the same note, with a last
line that says: phone the resident, then resolve here.

THE SHAPE
  Webhook (header auth, answers 200 on receipt -- the Edge Function is inside
  a Vapi tool call and must never wait on Chatwoot)
  -> shape the caller
  -> find the contact (by phone, else by identifier), create it if new
  -> the contact's open Voice conversation from the last 24 h, else create one
  -> post the caller's words as an INCOMING message
  -> Execute Workflow "Hand to a person" (mode new, channel voice), no wait

WHY AN INCOMING MESSAGE
Chatwoot sets `waiting_since` on an incoming message and clears it only on a
human's public reply. The handback ticker reads `waiting_since` 0 as "a
person answered" and strips the handover labels (`served`). A conversation
created with nothing in it would be served on the next tick in office hours;
the caller's own words, posted as the contact, keep it waiting until a rep
acts. It also shows the rep what was said before the note.

WHO IS THE CONTACT
The CALL: identifier `voice:call:<call id>`, minted by the Edge Function. It
was the apartment first, and the first live probe showed why not: the ask
comes before the address, so the identity changed mid-call and the same call
opened a second thread with the same notes. The apartment (canonical, from
the Edge Function as `label`) is the contact's NAME, and the number is its
phone, and those are how a LATER call finds the same contact: three searches
(call, phone, label), one pick in that order. A hit on the call with a label
or number that arrived since fills the contact in, so the next call matches.
Chatwoot's `phone_number` is unique per account (a WhatsApp resident already
has a contact), so a phone hit may be a WhatsApp contact -- fine, one person.

CREDENTIALS
Chatwoot calls here use the ADMIN token: contacts endpoints are not on the
agent bot's allow-list. The note itself is written by the sub-workflow on the
bot token (a User's self-mention would notify nobody). The webhook's shared
secret is a FRESH one (N8N_VOICE_NOTE_SECRET) in n8n's credential store, not
N8N_WEBHOOK_SECRET, which is in the public repo's August snapshots. It reaches
the Edge Function as a function secret via supabase_functions.py.
"""
import json
import os
import secrets
import sys
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_handover as H  # noqa: E402

WF_NAME = "Homies — Voice team note"
WEBHOOK_PATH = "homies-voice-note"
ACCOUNT = "https://chat.srv1879140.hstgr.cloud/api/v1/accounts/2"
SHAPED = "$('Shape the caller').first().json"
CONV = "$('The conversation').first().json.conv_id"


def ensure_voice_cred(e, rotate=False):
    """The webhook's header secret, in n8n's credential store.

    Reused across runs (the id is in .env) so --apply stays idempotent; the
    public API cannot read a credential back, so `--rotate-secret` is the only
    way to replace it, and it prints the reminder to push the new value to the
    Edge Function.
    """
    secret = e.get("N8N_VOICE_NOTE_SECRET", "").strip()
    cid = e.get("N8N_VOICENOTE_CRED_ID", "").strip()
    if secret and cid and not rotate:
        return cid, None
    if not secret or rotate:
        secret = secrets.token_urlsafe(32)
        W.set_env("N8N_VOICE_NOTE_SECRET", secret)
    # The new one first; the old one is deleted by main() only after the
    # workflow has been written to point at the new one, so a layout refusal
    # or a failed PUT leaves the live webhook on a credential that exists.
    new = W.api("POST", "/api/v1/credentials", {
        "name": "Homies voice note secret", "type": "httpHeaderAuth",
        "data": {"name": "x-homies-secret", "value": secret},
    })["id"]
    W.set_env("N8N_VOICENOTE_CRED_ID", new)
    print("credential: Homies voice note secret -> %s  (now run: python scripts/supabase_functions.py --apply)" % new)
    return new, (cid or None)


# --------------------------------------------------------------------------
# Code nodes. Each is one item in, one item out (or none, which ends the run).
# --------------------------------------------------------------------------
SHAPE = r"""
// What the Edge Function sent, checked and named. No call id, nothing to do.
const b = ($('Voice tool call').first().json.body) || {};
const s = (x) => String(x == null ? '' : x).trim();
const call_id = s(b.call_id);
if (!call_id) return [];
const phone = s(b.phone);
const building = s(b.building);
const unit = s(b.unit);
const reason = s(b.reason) || 'other';
const identifier = s(b.identifier) || ('voice:call:' + call_id);
const label = s(b.label);
const name = label || phone || ('שיחה קולית ' + call_id.slice(0, 8));
return [{ json: {
  call_id, phone, building, unit, reason, label,
  department: s(b.department), description: s(b.description).slice(0, 500),
  source: ['tool', 'backstop'].includes(s(b.source)) ? s(b.source) : 'tool',
  identifier, name,
  cutoff: Date.now() - 24 * 3600 * 1000,
} }];
"""

CANDIDATES = r"""
// What to search for, in the order a hit counts: this call, the number, the
// apartment. One item per search; the HTTP node runs once per item.
const w = $('Shape the caller').first().json;
const out = [{ json: { q: w.identifier, kind: 'call' } }];
if (w.phone) out.push({ json: { q: w.phone, kind: 'phone' } });
if (w.label) out.push({ json: { q: w.label, kind: 'label' } });
return out;
"""

PICK = r"""
// The search is ILIKE over name / email / phone / identifier. Exact matches
// only, in this order: the call's own identifier (the same call again), the
// number (may be the resident's WhatsApp contact -- one person), the
// apartment as the contact's name (a previous call from the same flat).
// Anything looser would attach a call to a stranger.
const want = $('Shape the caller').first().json;
const rows = [].concat(...$input.all().map(i => (i.json && i.json.payload) || []));
const by = (f) => rows.find(f) || null;
let hit = by(r => String(r.identifier || '') === want.identifier), kind = 'call';
if (!hit && want.phone) { hit = by(r => String(r.phone_number || '') === want.phone); kind = 'phone'; }
if (!hit && want.label) { hit = by(r => String(r.name || '') === want.label); kind = 'label'; }
// Filling in: a hit on the call whose contact is still nameless or
// numberless, and the caller has since said where or how to reach them.
const fill = !!hit && kind === 'call' && (
  (want.label && String(hit.name || '') !== want.label) ||
  (want.phone && String(hit.phone_number || '') !== want.phone));
return [{ json: { contact_id: hit ? hit.id : null, kind: hit ? kind : '', fill } }];
"""

CREATED = r"""
// Chatwoot answers a contact create with { payload: { contact: {...} } }.
const p = $input.first().json.payload || {};
return [{ json: { contact_id: (p.contact || {}).id || null } }];
"""

REUSE = r"""
// An open conversation of this contact, in the Voice inbox, active in the
// last 24 hours -- the same window as the sub-workflow's guard. Newest wins.
const want = $('Shape the caller').first().json;
const inbox = Number($('Voice inbox').first().json.inbox_id);
const rows = ($input.first().json.payload) || [];
const open = rows
  .filter(c => Number(c.inbox_id) === inbox && c.status === 'open'
            && Number(c.last_activity_at || 0) * 1000 >= want.cutoff)
  .sort((a, b) => Number(b.last_activity_at || 0) - Number(a.last_activity_at || 0));
const contact_id = $('The contact').first().json.contact_id;
return [{ json: { conv_id: open.length ? open[0].id : null, contact_id } }];
"""


# n8n retries a node that THROWS. A node set to continue on error returns an
# {error} item instead of throwing, so retryOnFail on it is inert (review,
# 14 Sep). So: a read may continue (a failed search falls through to a
# create), and the writes that the note cannot live without -- the
# conversation, the caller's words -- STOP the workflow on failure after
# their retries, so a lost note is a red execution and not a green one.
def http(name, pos, path, body, method="POST", on_error="continueRegularOutput", retry=False):
    node = {
        "id": "voicenote-" + name.lower().replace(" ", "-").replace("?", "").replace("'", "")[:30],
        "name": name,
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": list(pos),
        "parameters": {
            "method": method,
            "url": "=" + ACCOUNT + path,
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "options": {"timeout": 15000},
        },
        "credentials": H.ADMIN_CRED,
        "onError": on_error,
    }
    if body is not None:
        node["parameters"]["sendBody"] = True
        node["parameters"]["specifyBody"] = "json"
        node["parameters"]["jsonBody"] = body
    if retry:
        node.update({"retryOnFail": True, "maxTries": 3, "waitBetweenTries": 3000})
    return node


def code(name, pos, js, nid):
    return {"id": nid, "name": name, "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": list(pos), "parameters": {"jsCode": js.strip("\n")}}


def set_node(name, pos, nid, fields):
    return {"id": nid, "name": name, "type": "n8n-nodes-base.set", "typeVersion": 3.4,
            "position": list(pos),
            "parameters": {"assignments": {"assignments": [
                {"id": k, "name": k, "type": t, "value": v} for k, t, v in fields]},
                "includeOtherFields": False, "options": {}}}


def workflow(cred_id, inbox_id, sub_id):
    schema = [{"id": n, "displayName": n, "required": False, "defaultMatch": False,
               "display": True, "canBeUsedToMatch": True, "type": t} for n, t in H.INPUTS]
    values = {
        "conv_id": "={{ %s }}" % CONV,
        "phone": "={{ %s.phone }}" % SHAPED,
        "reason": "={{ %s.reason }}" % SHAPED,
        "department": "={{ %s.department }}" % SHAPED,
        "description": "={{ %s.description }}" % SHAPED,
        "source": "={{ %s.source }}" % SHAPED,
        "mode": "new", "now_override": "", "channel": "voice",
    }
    nodes = [
        {"id": "voicenote-sticky", "name": "Why a phone call gets a Chatwoot thread",
         "type": "n8n-nodes-base.stickyNote", "typeVersion": 1, "position": [0, -600],
         "parameters": {"width": 1420, "height": 240, "color": 4, "content":
             "### Voice team note\n"
             "The inbound voice agent's `notify_team` lands here (from the debt-tools Edge "
             "Function, header-authenticated, answered on receipt). A call has no Chatwoot "
             "conversation, so this makes one in the Voice inbox: the contact (this call's "
             "`voice:call:<id>`, found again by the number or the apartment as its name), an open conversation from "
             "the last 24 h or a new one, the caller's words as an INCOMING message (that is "
             "what sets `waiting_since`, so the handback ticker does not mark it served), then "
             "\"Hand to a person\" with channel voice -- the same mention the WhatsApp bot "
             "makes, whose note tells the rep to phone the resident and resolve. "
             "Admin token for the contact calls (not on the bot's allow-list); the note "
             "itself is the sub-workflow's, on the bot. Built by scripts/n8n_voice_note.py."}},
        {"id": "voicenote-webhook", "name": "Voice tool call", "type": "n8n-nodes-base.webhook",
         "typeVersion": 2, "position": [0, 0], "webhookId": "homies-voice-note-v1",
         "parameters": {"httpMethod": "POST", "path": WEBHOOK_PATH,
                        "authentication": "headerAuth", "responseMode": "onReceived",
                        "options": {}},
         "credentials": {"httpHeaderAuth": {"id": cred_id, "name": "Homies voice note secret"}}},
        set_node("Voice inbox", (240, 0), "voicenote-inbox",
                 [("inbox_id", "number", "={{ %d }}" % inbox_id)]),
        code("Shape the caller", (480, 0), SHAPE, "voicenote-shape"),
        code("What to search for", (720, 0), CANDIDATES, "voicenote-candidates"),
        http("Find the contact", (960, 0),
             "/contacts/search?q={{ encodeURIComponent($json.q) }}", None, method="GET"),
        code("Pick the contact", (1200, 0), PICK, "voicenote-pick"),
        H.if_node("Contact exists?", (1440, 0), "={{ !!$json.contact_id }}", "voicenote-exists"),
        H.if_node("Fill the contact in?", (1680, -180), "={{ $json.fill === true }}", "voicenote-fill"),
        # The same call, now with an address or a number it did not have at
        # its first note. A 422 (the number belongs to another contact) is
        # ignored: the thread is still this call's.
        http("Fill the contact in", (1920, -360), "/contacts/{{ $json.contact_id }}",
             "={{ JSON.stringify(Object.assign({}, %s.label ? { name: %s.label } : {}, "
             "%s.phone ? { phone_number: %s.phone } : {})) }}" % (SHAPED, SHAPED, SHAPED, SHAPED),
             method="PUT", retry=False),
        http("Create the contact", (1680, 180), "/contacts",
             "={{ JSON.stringify(Object.assign({ inbox_id: $('Voice inbox').first().json.inbox_id, "
             "name: %s.name, identifier: %s.identifier }, "
             "%s.phone ? { phone_number: %s.phone } : {})) }}" % (SHAPED, SHAPED, SHAPED, SHAPED),
             on_error="continueErrorOutput", retry=False),
        code("Created id", (1920, 180), CREATED, "voicenote-created"),
        # Two notes from one call in the same second: the second create is a
        # 422 (identifier taken) and the contact it wanted exists now; a number
        # that belongs to another contact is a 422 too, and the search by
        # call finds nothing -- so the retry creates without the number.
        http("Search again", (1920, 360),
             "/contacts/search?q={{ encodeURIComponent(%s.identifier) }}" % SHAPED, None, method="GET"),
        code("Pick again", (2160, 360), PICK, "voicenote-pick-again"),
        H.if_node("Found it after all?", (2400, 360), "={{ !!$json.contact_id }}", "voicenote-found"),
        http("Create without the number", (2640, 540), "/contacts",
             "={{ JSON.stringify({ inbox_id: $('Voice inbox').first().json.inbox_id, "
             "name: %s.name, identifier: %s.identifier }) }}" % (SHAPED, SHAPED),
             on_error="stopWorkflow", retry=True),
        code("Created id (no number)", (2880, 540), CREATED, "voicenote-created-2"),
        # Fed by four paths: the pick, a create, a fill-in (Chatwoot answers a
        # PUT with the contact under payload) and a failed fill-in (the pick
        # still holds the id).
        set_node("The contact", (3120, 0), "voicenote-contact",
                 [("contact_id", "number",
                   "={{ $json.contact_id || (($json.payload || {}).contact || {}).id "
                   "|| $('Pick the contact').first().json.contact_id }}")]),
        http("The contact's conversations", (3360, 0),
             "/contacts/{{ $json.contact_id }}/conversations", None, method="GET"),
        code("Reuse or create?", (3600, 0), REUSE, "voicenote-reuse"),
        H.if_node("Have a conversation?", (3840, 0), "={{ !!$json.conv_id }}", "voicenote-have"),
        http("Create the conversation", (4080, 180), "/conversations",
             "={{ JSON.stringify({ inbox_id: $('Voice inbox').first().json.inbox_id, "
             "contact_id: $json.contact_id, status: 'open', "
             "additional_attributes: { channel: 'voice', call_id: %s.call_id, "
             "building: %s.building, unit: %s.unit, phone: %s.phone } }) }}"
             % (SHAPED, SHAPED, SHAPED, SHAPED),
             on_error="stopWorkflow", retry=True),
        set_node("The conversation", (4320, 0), "voicenote-conversation",
                 [("conv_id", "number", "={{ $json.conv_id || $json.id }}")]),
        http("Post the caller's words", (4560, 0),
             "/conversations/{{ %s }}/messages" % CONV,
             "={{ JSON.stringify({ content: %s.description || ('שיחה קולית: ' + %s.reason), "
             "message_type: 'incoming', private: false }) }}" % (SHAPED, SHAPED),
             on_error="stopWorkflow", retry=True),
        {"id": "voicenote-hand", "name": "Let the team know", "type": "n8n-nodes-base.executeWorkflow",
         "typeVersion": 1.2, "position": [4800, 0],
         "parameters": {"workflowId": {"__rl": True, "value": sub_id, "mode": "id"},
                        "workflowInputs": {"mappingMode": "defineBelow", "value": values,
                                           "matchingColumns": [], "schema": schema},
                        "mode": "once", "options": {"waitForSubWorkflow": False}},
         "onError": "continueRegularOutput"},
    ]

    def link(*names):
        return [{"node": n, "type": "main", "index": 0} for n in names]

    connections = {
        "Voice tool call": {"main": [link("Voice inbox")]},
        "Voice inbox": {"main": [link("Shape the caller")]},
        "Shape the caller": {"main": [link("What to search for")]},
        "What to search for": {"main": [link("Find the contact")]},
        "Find the contact": {"main": [link("Pick the contact")]},
        "Pick the contact": {"main": [link("Contact exists?")]},
        "Contact exists?": {"main": [link("Fill the contact in?"), link("Create the contact")]},
        "Fill the contact in?": {"main": [link("Fill the contact in"), link("The contact")]},
        "Fill the contact in": {"main": [link("The contact")]},
        "Create the contact": {"main": [link("Created id"), link("Search again")]},
        "Created id": {"main": [link("The contact")]},
        "Search again": {"main": [link("Pick again")]},
        "Pick again": {"main": [link("Found it after all?")]},
        "Found it after all?": {"main": [link("The contact"), link("Create without the number")]},
        "Create without the number": {"main": [link("Created id (no number)")]},
        "Created id (no number)": {"main": [link("The contact")]},
        "The contact": {"main": [link("The contact's conversations")]},
        "The contact's conversations": {"main": [link("Reuse or create?")]},
        "Reuse or create?": {"main": [link("Have a conversation?")]},
        "Have a conversation?": {"main": [link("The conversation"), link("Create the conversation")]},
        "Create the conversation": {"main": [link("The conversation")]},
        "The conversation": {"main": [link("Post the caller's words")]},
        "Post the caller's words": {"main": [link("Let the team know")]},
    }
    return {"name": WF_NAME, "nodes": nodes, "connections": connections,
            "settings": {"executionOrder": "v1", "timezone": "Asia/Jerusalem"}}


def find():
    for w in W.api("GET", "/api/v1/workflows?limit=250").get("data", []):
        if w["name"] == WF_NAME:
            return w
    return None


def main():
    apply = "--apply" in sys.argv
    e = W.env()
    inbox_id = e.get("CHATWOOT_VOICE_INBOX_ID", "").strip()
    if not inbox_id.isdigit():
        sys.exit("CHATWOOT_VOICE_INBOX_ID is not in .env: run scripts/chatwoot_voice_inbox.py --apply first.")
    sub = H.find()
    if sub is None or not sub.get("active"):
        sys.exit("%r must exist and be published first: python scripts/n8n_handover.py --apply --publish" % H.WF_NAME)
    live_sub = W.api("GET", "/api/v1/workflows/%s" % sub["id"])
    decide = next((n for n in live_sub["nodes"] if n["name"] == "Decide the routing"), None)
    if decide is None or "handover_channel" not in (decide["parameters"].get("jsCode") or ""):
        sys.exit("The live sub-workflow does not know `channel` yet: python scripts/n8n_handover.py --apply --publish first.")

    cred_id = e.get("N8N_VOICENOTE_CRED_ID", "").strip() or "PENDING"
    old_cred = None
    if apply:
        cred_id, old_cred = ensure_voice_cred(e, rotate="--rotate-secret" in sys.argv)
    elif cred_id == "PENDING":
        print("credential: would create 'Homies voice note secret' (N8N_VOICE_NOTE_SECRET generated)")

    wf = workflow(cred_id, int(inbox_id), sub["id"])
    W.check(wf["nodes"], WF_NAME)
    live = find()
    if live is None:
        print("%s: does not exist yet -> would CREATE (%d nodes)" % (WF_NAME, len(wf["nodes"])))
    else:
        same = (H.dumps(live["nodes"]) == H.dumps(wf["nodes"])
                and H.dumps(live["connections"]) == H.dumps(wf["connections"]))
        print("%s: exists as %s (%d nodes, published=%s) -> %s"
              % (WF_NAME, live["id"], len(live["nodes"]), live.get("active"),
                 "already matches" if same else "would UPDATE"))
        if same:
            if "--publish" in sys.argv and apply:
                H.publish(live["id"])
            return
    print("webhook  : %s/webhook/%s" % (e["N8N_BASE_URL"].strip().rstrip("/"), WEBHOOK_PATH))
    if not apply:
        print("Dry run. Re-run with --apply to write it.")
        return
    if live is None:
        out = W.api("POST", "/api/v1/workflows", wf)
    else:
        out = W.api("PUT", "/api/v1/workflows/%s" % live["id"], wf)
    print("written: %s (%s)" % (out.get("name"), out.get("id")))
    back = W.api("GET", "/api/v1/workflows/%s" % out["id"])
    print("verify : %d nodes, connections from %s" % (len(back["nodes"]), sorted(back["connections"])))
    if "--publish" in sys.argv:
        H.publish(out["id"])
    if old_cred:
        try:
            W.api("DELETE", "/api/v1/credentials/%s" % old_cred)
            print("credential: old %s deleted" % old_cred)
        except SystemExit:
            print("credential: old %s already gone" % old_cred)
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
