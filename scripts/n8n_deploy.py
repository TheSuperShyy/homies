r"""Build and push the Vapi tool layer to n8n.

Named for the debt agent because that is what it was built for, and serving both
agents since 5 Aug — the inbound intake assistant posts `open_request`,
`save_partial_request` and `transfer_to_human` to the same webhook. One workflow
rather than two because the router already switches on the tool name, and a
second workflow would mean two copies of the writer, the secret and the shape.
The path stays `homies-debt-tools`: renaming it would break the live debt
assistant's eight tools until they were re-synced, which is a real outage to buy
a better name.

    python scripts/n8n_deploy.py            # show what would be pushed
    python scripts/n8n_deploy.py --apply    # create or update the workflow
    python scripts/n8n_deploy.py --activate # switch it on

The workflow is defined here rather than clicked together in the editor, for the
same reason the prompts are: an editor change is invisible to everyone who did
not make it, and there is no diff. Re-running this is safe — it updates the
workflow with the matching name instead of making a second one.

THE SHAPE, AND WHY IT IS THIS SHAPE

    Webhook -> Decide (Code) -> Respond to Webhook
                            \-> Only if writing (If) -> Google Sheets

Everything Vapi needs is computed in the Code node and returned immediately.
The sheet write happens *after* the response has already gone back. That is the
whole point: a Google Sheets append takes roughly a second, and on the Apps
Script version the agent sat through it saying "this will just take a sec" —
twice — before hanging up on the resident. Here the caller never waits for
storage, however slow storage is.

It also means validation cannot be delegated to the database. The Code node is
the only thing standing between a model's tool call and a row, so the refusals
live there: no amount on the call, an outcome that is not in the enum, a request
with no description.

WHAT THE MODEL IS NOT ALLOWED TO SUPPLY
The amount, the month and who is being called come from the call's
variableValues, never from tool arguments — the model can read them and cannot
change them. Same rule as the Supabase and Apps Script versions, and the reason
a mishearing cannot become a wrong number in a payment ticket.
"""

import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from n8n_layout import check, LayoutError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WF_NAME = "Homies — debt tools (Vapi)"
WEBHOOK_PATH = "homies-debt-tools"

# The spreadsheet already holding the ten seed residents.
SHEET_ID = "1WHktpyNWOpxUtgWftZppd77c6UD2AwWnF9H_KahS8Pg"

# Reusing an existing credential rather than asking for fresh OAuth. It belongs
# to another project on this instance, so the only question is whether that
# Google account can see the Homies spreadsheet — which the smoke test answers
# far faster than reasoning about it.
# Where rows actually land.
#
# Not the n8n Google Sheets node: every googleSheetsOAuth2Api credential on this
# instance fails with "unknown client", which is the OAuth client itself being
# rejected rather than one expired token — so no Google node on this instance can
# write anything until that is repaired.
#
# The Apps Script endpoint already writes correctly and is already deployed. Its
# problem was never correctness, it was 13 seconds of latency in front of a
# speaking agent. Behind n8n that stops mattering: n8n answers Vapi in ~700ms and
# calls this afterwards, with nobody on the line waiting for it.
#
# One trap when poking this endpoint by hand: Apps Script 404s the `homies/1.0`
# user-agent — GET and POST alike, deployment alive or not. An ordinary browser
# string gets through. This is the exact inverse of Vapi, where Cloudflare 404s
# urllib's *default* agent and `homies/1.0` is the fix, so the same header that
# rescues one host breaks the other. A 404 here means almost nothing until the
# user-agent has been ruled out.
def _writer():
    """Where a tool call is actually written. Supabase since 8 Aug.

    It was the Apps Script bridge until then, and the swap is the whole reason
    this is a function rather than a constant. Both stores answer in the SAME
    Vapi shape — {results: [{toolCallId, result}]} — and both writer nodes post
    the untouched original envelope, so the change is a URL and a header and
    nothing else in the graph moves.

    Why it had to change: the CRM reads Supabase, the six migrations describe
    Supabase, and `requests.reference` is a Postgres default. On 8 Aug the
    spreadsheet held 28 rows in `call_requests` and Supabase held one, because
    every ticket either agent had ever opened went to the sheet. Nothing was
    lost and nothing was visible to the thing built to show it.

    The Apps Script endpoint stays deployed and stays the export target. It is
    no longer the store of record.
    """
    e = dict(
        l.strip().split("=", 1)
        for l in open(os.path.join(ROOT, ".env"), encoding="utf-8")
        if l.strip() and not l.startswith("#") and "=" in l
    )
    url = e.get("SUPABASE_URL", "").strip().rstrip("/")
    secret = e.get("TOOL_SECRET", "").strip()
    if not url or not secret:
        raise SystemExit(
            "SUPABASE_URL and TOOL_SECRET must both be set — the writer is "
            "Supabase now. Set them in .env and re-run."
        )
    return url + "/functions/v1/debt-tools", secret


def env():
    return dict(
        l.strip().split("=", 1)
        for l in open(os.path.join(ROOT, ".env"), encoding="utf-8")
        if l.strip() and not l.startswith("#") and "=" in l
    )


def api(method, path, body=None):
    e = env()
    req = urllib.request.Request(
        e["N8N_BASE_URL"].strip() + path,
        method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={
            "X-N8N-API-KEY": e["N8N_API_KEY"].strip(),
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "homies/1.0",
        },
    )
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read() or b"{}")
    except urllib.error.HTTPError as exc:
        sys.exit("HTTP %s on %s %s\n%s" % (exc.code, method, path, exc.read().decode()[:600]))


# ---------------------------------------------------------------------------
# The Code node
# ---------------------------------------------------------------------------
# Plain JS, no imports. Returns one item carrying three things: `_vapi` (what
# goes back to the agent), `_tab` (which sheet to append to) and `_write`
# (whether to append at all), alongside the row's own fields at top level so the
# Sheets node can map them by header name.

DECIDE = r"""
// Vapi posts { message: { call, toolCalls: [...] } } and expects
// { results: [ { toolCallId, result } ] } where result is a string.
const body = $input.first().json.body || $input.first().json;
const msg  = body.message || {};
const call = msg.call || {};

// The facts about this call. Attached by whoever placed it; the model can read
// these and cannot change them, which is why no tool takes an amount.
const v = (call.assistantOverrides && call.assistantOverrides.variableValues)
       || (msg.assistant && msg.assistant.variableValues)
       || {};

const ctx = {
  call_id:    call.id || '',
  phone:      v.phone || '',
  first_name: v.first_name || '',
  amount:     v.amount || '',
  // A person call (feature 14) carries months_phrase, not month. Either counts
  // as "this call knows what it is collecting" for the guards below.
  month:      v.month || v.months_phrase || '',
  card_last4: v.card_last4 || '',
  building:   v.building || '',
  unit:       v.unit || '',
};

// The charges whitelist a person call rides in on. variableValues are template
// substitutions, so it can arrive as JSON text or as itself; both are read.
// Absent or malformed means a single-charge call, and every check below then
// passes everything through — exactly the old behaviour.
let chargesOnCall = [];
try {
  let c = v.charges;
  if (typeof c === 'string') c = JSON.parse(c);
  if (Array.isArray(c)) chargesOnCall = c;
} catch (e) { /* single-charge call */ }
const unitsOnCall = [];
for (const c of chargesOnCall) {
  const u = String((c && c.unit) || '').trim();
  if (u && unitsOnCall.indexOf(u) < 0) unitsOnCall.push(u);
}

// Mirrors targets() in the Supabase writer, and has to: this node answers Vapi
// BEFORE the writer runs, so a refusal that exists only downstream would arrive
// after the agent had already been told yes. A unit that is not on the call is
// refused, never widened back to the whole call — a mishearing on "I paid for
// four" must not dispute a flat the resident never mentioned.
function badUnit(args) {
  const asked = String((args && args.unit) || '').trim();
  if (!asked || !unitsOnCall.length) return null;
  if (unitsOnCall.indexOf(asked) >= 0) return null;
  return { ok: false, error: 'apartment ' + asked + ' is not on this call — ' +
           'apartments on this call: ' + unitsOnCall.join(', ') };
}

const tc = (msg.toolCalls || [])[0] || {};
const fn = tc.function || {};
let args = fn.arguments || {};
if (typeof args === 'string') { try { args = JSON.parse(args); } catch (e) { args = {}; } }

// Israel time, formatted for a spreadsheet rather than for a machine.
const at = new Date().toLocaleString('sv-SE', { timeZone: 'Asia/Jerusalem' });

const OUTCOMES = ['link_sent','authorized','promised','disputed','refused',
                  'transferred','voicemail','wrong_party','not_handed_over',
                  'no_answer','office_to_contact'];
// Both agents' reasons in one list, because both agents post here. The first six
// are the outbound ones; the rest are inbound. An unrecognised reason does not
// error, it becomes 'caller_request' — so a reason missing from this list is not
// a bug anyone sees, it is a column that quietly says the wrong thing forever.
// Kept in step with INTAKE_TRANSFER_REASONS in scripts/vapi_tools.py.
const REASONS  = ['hardship','dispute','distress','language','not_understood',
                  'caller_request','ownership',
                  'out_of_scope','emergency','repeated_failure'];

let result = { ok: false, error: 'unknown tool ' + fn.name };
let tab = null;
let row = {};

switch (fn.name) {
  case 'send_payment_link': {
    // Refused rather than written: a link request with no amount is a row a
    // person cannot action, and the agent must not be told one is on its way.
    if (!ctx.amount || !ctx.month) { result = { ok:false, error:'no amount or month on this call' }; break; }
    const bad = badUnit(args); if (bad) { result = bad; break; }
    tab = 'payment_links';
    row = { at, call_id: ctx.call_id, phone: ctx.phone, first_name: ctx.first_name,
            amount: ctx.amount, month: ctx.month, status: 'requested',
            unit: String(args.unit || '').trim(), note: args.note || '' };
    result = { ok: true };
    break;
  }
  case 'open_payment_ticket': {
    // Retired 4 Aug and no longer offered to the agent; still answered so a
    // stale assistant does not get 'unknown tool' mid-call.
    if (!ctx.amount || !ctx.month) { result = { ok:false, error:'no amount or month on this call' }; break; }
    const captured = args.authorization_captured === true;
    // This node answers Vapi *before* the writer runs, so a guard that exists
    // only in Apps Script would refuse the row after the agent had already been
    // told yes — the resident hears a confirmation for a row nobody wrote. Every
    // refusal has to live here too, not only downstream.
    if (captured && !ctx.card_last4) {
      result = { ok:false, error:'no card on file for this resident — authorisation cannot be captured' };
      break;
    }
    tab = 'payment_tickets';
    row = { at, call_id: ctx.call_id, phone: ctx.phone, first_name: ctx.first_name,
            amount: ctx.amount, month: ctx.month, card_last4: ctx.card_last4,
            authorization_captured: captured, status: 'pending', note: args.note || '' };
    result = { ok: true, authorization_captured: captured };
    break;
  }
  case 'log_promise_to_pay': {
    if (!args.said) { result = { ok:false, error:'said is required' }; break; }
    const bad = badUnit(args); if (bad) { result = bad; break; }
    tab = 'promises';
    row = { at, call_id: ctx.call_id, phone: ctx.phone, first_name: ctx.first_name,
            promised_date: args.promised_date || '', said: String(args.said),
            unit: String(args.unit || '').trim() };
    result = { ok: true };
    break;
  }
  case 'request_standing_order': {
    tab = 'call_outcomes';
    row = { at, call_id: ctx.call_id, phone: ctx.phone, first_name: ctx.first_name,
            outcome: 'office_to_contact', standing_order_requested: true };
    result = { ok: true };
    break;
  }
  case 'log_disputed_payment': {
    const bad = badUnit(args); if (bad) { result = bad; break; }
    tab = 'disputes';
    row = { at, call_id: ctx.call_id, phone: ctx.phone, first_name: ctx.first_name,
            receipt_requested: true, unit: String(args.unit || '').trim() };
    result = { ok: true };
    break;
  }
  case 'open_request': {
    if (!args.description) { result = { ok:false, error:'description is required' }; break; }
    // A real reference, because the agent reads it aloud and is forbidden from
    // inventing one. Generated here so it can be returned before the row lands.
    const ref = 'HM-' + new Date().getFullYear() + '-' +
                String(Math.floor(Math.random() * 9000) + 1000);
    tab = 'call_requests';
    row = { at, call_id: ctx.call_id, phone: ctx.phone, reference: ref,
            type: args.type || 'other', description: String(args.description),
            // variableValues first, tool arguments only as the gap-filler. On an
            // outbound call the location is a fact the call was placed with and
            // the model cannot overwrite it; on an inbound call ctx is empty and
            // what the caller said is the only source there is. One expression,
            // both agents, and the precedence is what keeps the outbound
            // guarantee intact.
            building: ctx.building || args.building || '',
            unit: ctx.unit || args.unit || '',
            urgency: args.urgency || 'normal' };
    result = { ok: true, reference: ref };
    break;
  }
  case 'save_partial_request': {
    // Never refuses. This is what the agent calls when the call is already
    // failing — a line too noisy to continue, or seconds left on the clock —
    // and a validation error here would turn a salvaged call into a lost one.
    // An empty description is a real answer: it says the audio was unusable,
    // which is exactly what the row is for.
    tab = 'partial_requests';
    row = { at, call_id: ctx.call_id, phone: ctx.phone,
            reason: args.reason || 'audio',
            description: args.description ? String(args.description) : '',
            building: ctx.building || args.building || '',
            unit: ctx.unit || args.unit || '' };
    result = { ok: true };
    break;
  }
  case 'flag_not_handed_over': {
    // Retired 11 Aug and no longer offered to the agent; answered so a stale
    // assistant does not get 'unknown tool' mid-call. The Supabase writer no
    // longer flags anything on this path — it pauses the apartment and routes
    // it to a person, same as transfer_to_human with reason ownership.
    const bad = badUnit(args); if (bad) { result = bad; break; }
    tab = 'call_outcomes';
    row = { at, call_id: ctx.call_id, phone: ctx.phone, first_name: ctx.first_name,
            outcome: 'transferred', transfer_reason: 'ownership',
            unit: String(args.unit || '').trim() };
    result = { ok: true, paused: true };
    break;
  }
  case 'transfer_to_human': {
    const reason = REASONS.indexOf(args.reason) >= 0 ? args.reason : 'caller_request';
    // ownership is the one reason that also pauses an apartment, so the unit it
    // names has to be on the call — mirroring the writer's refusal, which would
    // otherwise arrive after the agent had been told yes.
    if (reason === 'ownership') { const bad = badUnit(args); if (bad) { result = bad; break; } }
    tab = 'call_outcomes';
    row = { at, call_id: ctx.call_id, phone: ctx.phone, first_name: ctx.first_name,
            outcome: 'transferred', transfer_reason: reason,
            posture_reached: args.posture_reached || '',
            unit: String(args.unit || '').trim() };
    result = { ok: true, reason };
    break;
  }
  case 'log_call_outcome': {
    if (OUTCOMES.indexOf(args.outcome) < 0) {
      result = { ok:false, error:'outcome must be one of: ' + OUTCOMES.join(', ') }; break;
    }
    tab = 'call_outcomes';
    row = { at, call_id: ctx.call_id, phone: ctx.phone, first_name: ctx.first_name,
            outcome: args.outcome, posture_reached: args.posture_reached || '',
            transfer_reason: args.transfer_reason || '' };
    result = { ok: true };
    break;
  }
  case 'identify_resident': {
    // Kept so one webhook serves every tool. The lookup itself is not here yet.
    result = { ok: true, note: 'lookup not implemented on n8n yet' };
    break;
  }
}

// open_request is the one tool whose answer cannot be invented here: the agent
// reads the reference aloud, and if n8n minted one while the sheet minted
// another they would disagree forever. So that call alone waits for the writer
// and returns whatever it says. It fires rarely — a maintenance issue raised
// during a debt call — so paying for it there is cheap.
const needsRealAnswer = fn.name === 'open_request' && Boolean(args.description);

// What actually goes to the writer. Almost verbatim — with the location resolved
// into variableValues first.
//
// The writer reads the building and the apartment off the call, never off the
// tool arguments, and that rule is deliberate: outbound, the location is a fact
// the call was placed with and a mishearing must not be able to overwrite it.
// Inbound there is no such fact. Nothing is attached to the call, so reading
// only variableValues would write every inbound ticket with an empty address —
// a row with a description and no door to knock on.
//
// Resolving it here rather than in the writer keeps the rule intact and puts the
// merge in one place instead of two. The precedence is unchanged, so the
// outbound guarantee is untouched: variableValues still win wherever they exist,
// and the tool arguments only fill a gap that outbound never has.
//
// It also means this works against the writer that is deployed today, with no
// change on that side at all.
const forward = JSON.parse(JSON.stringify(body));
forward.message = forward.message || {};
forward.message.call = forward.message.call || {};
forward.message.call.assistantOverrides = forward.message.call.assistantOverrides || {};
// The writer treats variableValues.unit as a fact of the call, so the agent's
// argument only fills the gap when it names an apartment the call actually
// covers (or when there is no whitelist — inbound, where what the caller said
// is the only source there is). An off-call unit stays out: the writer files
// the ticket with no apartment for a person to read, rather than trusting a
// guess promoted to a fact by this merge.
const argUnit = String(args.unit || '').trim();
const safeUnit = (!unitsOnCall.length || unitsOnCall.indexOf(argUnit) >= 0) ? argUnit : '';
forward.message.call.assistantOverrides.variableValues = Object.assign({}, v, {
  building: ctx.building || args.building || '',
  unit:     ctx.unit     || safeUnit      || '',
});

return [{
  json: Object.assign({}, row, {
    _vapi:  { results: [{ toolCallId: tc.id, result: JSON.stringify(result) }] },
    _tab:   tab || 'call_outcomes',
    _write: Boolean(tab),
    _sync:  needsRealAnswer,
    _original: forward,
  }),
}];
"""


WRITER_URL, WRITER_SECRET = _writer()


def workflow():
    node = lambda **kw: dict({"parameters": {}, "typeVersion": 1}, **kw)
    return {
        "name": WF_NAME,
        "settings": {"executionOrder": "v1"},
        "nodes": [
            # The canvas explains itself, because the person who opens it will be
            # doing so while it is failing and will not have this file to hand.
            node(
                id="webhook", name="Vapi tool call", type="n8n-nodes-base.webhook",
                typeVersion=2, position=[0, 0],
                # n8n registers a production webhook against this id, not against
                # the path. Created without one, the workflow reports active:true
                # and every POST still 404s "not registered" — which is what
                # happened on the first deploy. Copied the convention from the
                # working webhooks already on this instance.
                webhookId="homies-debt-tools-v1",
                parameters={
                    "httpMethod": "POST",
                    "path": WEBHOOK_PATH,
                    # The response comes from the Respond node, so the shape is
                    # ours rather than n8n's default execution summary.
                    "responseMode": "responseNode",
                    "options": {},
                },
            ),
            node(
                id="decide", name="Decide", type="n8n-nodes-base.code",
                typeVersion=2, position=[240, 0],
                parameters={"jsCode": DECIDE},
            ),
            node(
                id="respond", name="Answer Vapi", type="n8n-nodes-base.respondToWebhook",
                # 1.1 is what the working workflows on this instance use.
                typeVersion=1.1, position=[720, 60],
                parameters={
                    "respondWith": "json",
                    "responseBody": "={{ JSON.stringify($json._vapi) }}",
                    "options": {},
                },
            ),
            node(
                id="shouldwrite", name="Anything to write?", type="n8n-nodes-base.if",
                typeVersion=2, position=[720, 240],
                parameters={"conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                    "conditions": [{
                        "id": "w",
                        "leftValue": "={{ $json._write }}",
                        "rightValue": "",
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                    }],
                    "combinator": "and",
                }},
            ),
            node(
                id="issync", name="Needs the real answer?", type="n8n-nodes-base.if",
                typeVersion=2, position=[480, 0],
                parameters={"conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                    "conditions": [{
                        "id": "s",
                        "leftValue": "={{ $json._sync }}",
                        "rightValue": "",
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                    }],
                    "combinator": "and",
                }},
            ),
            node(
                id="writesync", name="Write, then answer", type="n8n-nodes-base.httpRequest",
                typeVersion=4.2, position=[720, -120],
                parameters={
                    "method": "POST", "url": WRITER_URL,
                    "sendHeaders": True,
                    "headerParameters": {"parameters": [
                        {"name": "x-homies-secret", "value": WRITER_SECRET},
                    ]},
                    "sendBody": True, "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify($json._original) }}",
                    "options": {"timeout": 25000},
                },
            ),
            node(
                id="answersync", name="Answer from writer",
                type="n8n-nodes-base.respondToWebhook", typeVersion=1.1,
                position=[960, -120],
                parameters={"respondWith": "json",
                            "responseBody": "={{ JSON.stringify($json) }}",
                            "options": {}},
            ),
            node(
                id="writeasync", name="Write after answering",
                type="n8n-nodes-base.httpRequest", typeVersion=4.2,
                position=[960, 240],
                parameters={
                    "method": "POST", "url": WRITER_URL,
                    "sendHeaders": True,
                    "headerParameters": {"parameters": [
                        {"name": "x-homies-secret", "value": WRITER_SECRET},
                    ]},
                    "sendBody": True, "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify($json._original) }}",
                    # Long because nobody is waiting. Apps Script needed it —
                    # 13s from cold — and an Edge Function does not, but the
                    # branch exists for the general case and the ceiling costs
                    # nothing when it is not reached.
                    "options": {"timeout": 30000},
                },
            ),
        ],
        "connections": {
            "Vapi tool call": {"main": [[{"node": "Decide", "type": "main", "index": 0}]]},
            "Decide": {"main": [[{"node": "Needs the real answer?", "type": "main", "index": 0}]]},
            # Answering is never gated on there being a row to write. A refusal —
            # bad outcome enum, missing description — writes nothing and still has
            # to reply, and wiring Respond behind the write test left those calls
            # hanging with no response at all.
            "Needs the real answer?": {"main": [
                [{"node": "Write, then answer", "type": "main", "index": 0}],
                [{"node": "Answer Vapi", "type": "main", "index": 0},
                 {"node": "Anything to write?", "type": "main", "index": 0}],
            ]},
            "Write, then answer": {"main": [[{"node": "Answer from writer", "type": "main", "index": 0}]]},
            "Anything to write?": {"main": [[{"node": "Write after answering", "type": "main", "index": 0}]]},
        },
    }


def find():
    for w in api("GET", "/api/v1/workflows?limit=100").get("data", []):
        if w["name"] == WF_NAME:
            return w
    return None


def main():
    wf = workflow()
    # Before anything is pushed, and before the dry run prints, because a layout
    # nobody can read is not a smaller problem than a wrong URL.
    try:
        check(wf["nodes"], WF_NAME)
    except LayoutError as ex:
        sys.exit("\n%s\n" % ex)

    existing = find()
    base = env()["N8N_BASE_URL"].strip()

    print("workflow : %s" % WF_NAME)
    print("nodes    : %s" % ", ".join(n["name"] for n in wf["nodes"]))
    print("webhook  : %s/webhook/%s" % (base, WEBHOOK_PATH))
    print("writer   : %s" % WRITER_URL.split("?")[0])
    print("target   : %s" % (("update " + existing["id"]) if existing else "create new"))

    if "--activate" in sys.argv:
        if not existing:
            sys.exit("Nothing to activate — run with --apply first.")
        api("POST", "/api/v1/workflows/%s/activate" % existing["id"])
        print("\nactivated. Webhook is live at:")
        print("  %s/webhook/%s" % (base, WEBHOOK_PATH))
        return

    if "--apply" not in sys.argv:
        print("\nDry run. Re-run with --apply to push.")
        return

    if existing:
        api("PUT", "/api/v1/workflows/%s" % existing["id"], wf)
        wid = existing["id"]
        print("\nupdated %s" % wid)
    else:
        wid = api("POST", "/api/v1/workflows", wf)["id"]
        print("\ncreated %s" % wid)
    print("%s/workflow/%s" % (base, wid))
    print("\nNot active yet. Run with --activate, then: python scripts/check_tools.py")


if __name__ == "__main__":
    main()
