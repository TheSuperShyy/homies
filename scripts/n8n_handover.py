# -*- coding: utf-8 -*-
"""Build the sub-workflow that pages a department when a WhatsApp chat is handed over.

    python scripts/n8n_handover.py                      # dry run: print what would be created or changed
    python scripts/n8n_handover.py --apply              # create it, or update it in place if it exists
    python scripts/n8n_handover.py --apply --publish    # ...and publish it

PUBLISH IS NOT OPTIONAL ON THIS n8n. Activating any workflow that carries an
Execute Workflow node pointing here fails with "references workflow ... which
is not published" until this one is published too (learned 3 Sep, on the test
harness). A sub-workflow with only an Execute Workflow Trigger publishes
cleanly; nothing starts running on its own.

WHY
`transfer_to_human` on WhatsApp wrote a `call_outcomes` row and stopped. No
person was told, nothing changed in Chatwoot, the bot kept answering, and the
prompt's line "the message reached a Homies representative and is marked
urgent" was untrue (WORKLOG 9891, "transfer_to_human notifies nobody"). Staff
share ONE number through Chatwoot, so a handover can never ring a rep's phone;
it has to mark the conversation, route it to a department, and NOTIFY someone
inside Chatwoot.

HOW THE ALERT WORKS
A private note that @mentions the department's TEAM. Chatwoot expands a team
mention (`[@x](mention://team/<id>/<name>)`) to every member and raises a
`conversation_mention` notification for each: bell, browser push, the mobile
app's push, and email once SMTP exists. Verified in Chatwoot's source (3 Sep):
MentionService runs on every message_created, private notes only, mentioned
users must be inbox members, and a note written by the agent bot still
notifies (only a User sender's self-mention is skipped). Assigning a TEAM
notifies nobody by itself, so the assignment here is routing, not the alert.

ONE WORKFLOW, FOUR MODES, all on the agent bot's token (bots may call show,
toggle_priority, custom_attributes, assignments, labels and messages -- the
allow-list in Chatwoot's access_token_auth_helper.rb):
  new        from the WhatsApp bot: guard, page (in office hours), stamp,
             priority, team, labels
  page       from the minute ticker: the 09:00 sweep of after-hours arrivals
  escalate1  nobody claimed it in 10 minutes: team again + Management, urgent
  escalate2  25 minutes: every team
The ticker lives in "Homies — Chatwoot handback" (n8n_handback_escalate.py).

THINGS THAT WOULD OTHERWISE COST AN AFTERNOON
- `POST .../labels` REPLACES the label set (Labelable#update_labels), so the
  Code node writes the union of what is there and what is added.
- `POST .../custom_attributes` merges. That is where the state lives
  (handover_at, handover_paged_at, handover_escalation), visible in the
  sidebar because the definitions were created on 3 Sep.
- The WhatsApp gate is untouched: the assignee stays the bot. A human's first
  public reply claims the thread (existing reply-claim node) and the bot goes
  quiet from then on. While the handover waits the bot keeps answering, the
  owner's decision of 3 Sep.
- Probe conversations do not exist in Chatwoot: the read 404s and the workflow
  exits through "Not a real conversation" without writing anything.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

WF_NAME = "Homies — Hand to a person"
CHATWOOT = "https://chat.srv1879140.hstgr.cloud/api/v1/accounts/2/conversations/"
# The agent bot's token, already an n8n credential (used by Send / Send menu).
BOT_CRED = {"httpHeaderAuth": {"id": "ctZhJP3JSajBO6ub",
                               "name": "Chatwoot bot (api_access_token)"}}
# THE READ USES THE ADMIN TOKEN, AND THAT IS A WORKAROUND FOR A CHATWOOT BUG.
# On 4.16.2, `GET /conversations/{id}` with an agent-bot token answers 500 the
# moment the conversation has a TEAM assigned (bisected 3 Sep on conversation
# 44: team on -> 500, team off -> 200; priority, labels and custom attributes
# are all fine). Every handover assigns a team, so every second run of this
# workflow -- the guard, the escalations, the 09:00 sweep -- would have died
# on its first node. An admin's read is unaffected, attributes nothing, and
# changes nothing. The writes stay on the bot token, so the activity log says
# "Assigned to service by Homies bot", which is the truth.
ADMIN_CRED = {"httpHeaderAuth": {"id": "1qfgfvxwZ4MsUBBh",
                                 "name": "Chatwoot admin (api_access_token)"}}
CONV = "{{ $('Decide the routing').first().json.conv_id }}"

INPUTS = [("conv_id", "number"), ("phone", "string"), ("reason", "string"),
          ("department", "string"), ("description", "string"),
          ("source", "string"), ("mode", "string"), ("now_override", "string"),
          # 14 Sep, voice joined: `whatsapp` (default) or `voice`. Optional, so
          # every existing caller keeps working unchanged; the value is stamped
          # on the conversation so page / escalate / served modes read it back.
          ("channel", "string")]

# --------------------------------------------------------------------------
# The one Code node. Multi-source (trigger inputs + the conversation read),
# a routing table, a label union and a Hebrew note for STAFF -- the note is
# internal, so the owner's "nothing templated" rule for resident-facing text
# does not apply to it.
# --------------------------------------------------------------------------
DECIDE = r"""
// Decide what this handover does: which team, which priority, whether to page
// now or wait for office hours, and what the private note says.
const inp = $('When handed a conversation').first().json;
const conv = $input.first().json;

const tz = 'Asia/Jerusalem';
const now = inp.now_override
  ? DateTime.fromISO(String(inp.now_override), { zone: tz })
  : DateTime.now().setZone(tz);
const mode = ['new', 'page', 'escalate1', 'escalate2', 'served'].includes(inp.mode) ? inp.mode : 'new';

// 14 Sep: a voice call's note lands on a conversation in the Voice inbox that
// exists only for this purpose. Nothing typed there reaches the caller, so
// the note's last line has to say what a rep does instead: phone them, then
// resolve. The channel is an input on `new` and a stamp afterwards. The
// voice-note workflow writes building / unit / phone / call_id into
// additional_attributes at creation; that is where a web caller with no
// number is found again.
const ca0 = conv.custom_attributes || {};
const channel = mode === 'new' ? String(inp.channel || 'whatsapp')
                               : String(ca0.handover_channel || 'whatsapp');
const voice = channel === 'voice';
const aa = conv.additional_attributes || {};
const where = [aa.building, aa.unit ? 'דירה ' + aa.unit : ''].filter(Boolean).join(', ');

const TEAMS = { collections: 1, operations: 2, management: 3, service: 4 };
const HEBREW = { collections: 'גבייה', operations: 'תפעול', management: 'הנהלה', service: 'שירות' };
const mention = (d) => '[@' + HEBREW[d] + '](mention://team/' + TEAMS[d] + '/' + d + ')';

const ca = conv.custom_attributes || {};
const labels = Array.isArray(conv.labels) ? conv.labels : [];
const meta = conv.meta || {};
// Only a PERSON counts as a takeover. Chatwoot assigns bot-inbox conversations
// to the agent bot itself; the same three-way test the handback ticker uses.
const a = meta.assignee;
const t = meta.assignee_type || conv.assignee_type;
const human = !!a && (a.type ? a.type === 'user' : (t ? t === 'User' : !a.outgoing_url));

// Office hours: Sunday to Thursday, 09:00-17:00 Israel time. Luxon: Sunday = 7.
const inHours = [7, 1, 2, 3, 4].includes(now.weekday) && now.hour >= 9 && now.hour < 17;

const VALID = Object.keys(TEAMS);
const reason = String(inp.reason || (ca.handover_reason || 'other'));
// 14 Sep: the reasons name the MATTER (what the resident wants), because the
// note is what the team reads, and the department follows it. The model may
// still override `department` by judgment.
const DEPT_BY_REASON = { payment: 'collections', billing: 'collections',
                         move: 'management', contract: 'management', quote: 'management',
                         emergency: 'operations' };
let dept;
if (mode === 'new') {
  dept = VALID.includes(inp.department) ? inp.department
       : (DEPT_BY_REASON[reason] || 'service');
} else {
  dept = VALID.includes(ca.handover_department) ? ca.handover_department : 'service';
}

// --- The guard, for `new` only ---------------------------------------------
// The tool and the promise-sentence can both fire in one turn. One note per
// MATTER per conversation per 24 hours: the same reason again is a duplicate
// and is skipped; a different reason is a different matter and gets its own
// note, because the bot has just told the resident the team knows about it
// (14 Sep -- before that the guard was per conversation, which would have
// made that sentence false the second time). An emergency over a
// non-emergency is an upgrade and says so.
// `handover_reasons` is every matter noted in the current 24-hour window,
// comma-joined, because the LAST reason alone is not enough: payment, then
// billing, then payment again would re-note the first (harness case 11,
// 14 Sep). It resets with the window.
let skip = false, why = '', upgrade = false;
const at = ca.handover_at ? DateTime.fromISO(String(ca.handover_at)) : null;
const fresh = !!(at && at.isValid && now.diff(at, 'hours').hours < 24);
const noted = fresh
  ? String(ca.handover_reasons || ca.handover_reason || '').split(',').map(x => x.trim()).filter(Boolean)
  : [];
if (mode === 'new') {
  const already = labels.includes('handover') && conv.status === 'open' && !human && fresh;
  if (already) {
    if (reason === 'emergency' && !noted.includes('emergency')) upgrade = true;
    else if (noted.includes(reason)) {
      skip = true; why = 'already noted (' + reason + ') within the last 24h';
    }
  }
}
const reasons = noted.includes(reason) ? noted : noted.concat([reason]);

// 14 Sep: a dues question is not `high`. Emergencies and escalations are
// urgent; everything else is a note for the team to work through.
const priority = (mode.startsWith('escalate') || reason === 'emergency') ? 'urgent' : 'medium';
// `served` writes state only: a person answered, so nothing is paged.
const page = mode === 'new' ? inHours : mode !== 'served';

// --- Labels: union, because POST /labels replaces the whole set --------------
// The department label follows the department: an emergency upgrade that moves
// a thread from Service to Operations must not leave both labels on it.
// `served` is the one mode that SUBTRACTS: a handover a person has answered is
// over, and the labels have to go or the ladder keeps finding it.
let want;
if (mode === 'served') {
  want = labels.filter(l => l !== 'handover' && !l.startsWith('handover-')
                         && l !== 'after-hours' && l !== 'escalated');
} else {
  want = labels.filter(l => (l !== 'after-hours' || (mode === 'new' && !inHours))
                         && !(l.startsWith('handover-') && l !== 'handover-' + dept));
  const add = ['handover', 'handover-' + dept];
  if (mode === 'new' && !inHours) add.push('after-hours');
  if (mode.startsWith('escalate')) add.push('escalated');
  for (const l of add) if (!want.includes(l)) want.push(l);
}

// --- The note -----------------------------------------------------------------
// 14 Sep evening: the owner read a note in translation and asked for words a
// non-technical rep understands. No "source", "escalation" or "handover" in
// the note; the mention first, one "what to do" line last.
const REASON = {
  payment: 'הדייר רוצה לשלם או להסדיר תשלום',
  billing: 'הדייר לא מסכים עם חיוב, או צריך מסמך (חשבונית, קבלה, אישור)',
  move: 'דייר נכנס לדירה או עוזב אותה',
  contract: 'משהו בחוזה',
  quote: 'הדייר מבקש הצעת מחיר',
  emergency: 'מצב חירום',
  caller_request: 'הדייר ביקש לדבר עם בן אדם',
  other: 'משהו שרק בן אדם מהצוות יכול לסדר',
  // Kept so an old stamp still reads; the bot no longer sends these.
  out_of_scope: 'משהו שהבוט לא מטפל בו',
  not_understood: 'הבוט לא הבין מה הדייר רוצה',
};
// Only the backstop is worth a sentence to a rep; a tap or a bot decision
// says nothing they act on differently (the reason already carries it).
const SOURCE = { backstop: 'הבוט אמר לדייר שהצוות יודע, ולכן זה נרשם כאן אוטומטית.' };
const recent = (Array.isArray(conv.messages) ? conv.messages : [])
  .filter(m => m && m.message_type === 0 && !m.private && m.content)
  .slice(-3).map(m => '• ' + String(m.content).slice(0, 300));
const phone = String(inp.phone || (meta.sender || {}).phone_number || '');
// Waiting time counts from the last page, not the original handover: an
// after-hours arrival paged at 09:00 has been waiting since 09:00, not since
// 22:00. The ticker re-stamps handover_paged_at on every escalation.
const since = ca.handover_paged_at || ca.handover_at;
const minutes = since ? Math.round(now.diff(DateTime.fromISO(String(since)), 'minutes').minutes) : 0;

const urgent = reason === 'emergency';
const lines = [];
if (mode === 'new' || mode === 'page') {
  lines.push(mention(dept) + ' ' + (upgrade ? 'דחוף. הפנייה של הדייר הזה הפכה למצב חירום.'
                                  : mode === 'page' ? 'דייר פנה מחוץ לשעות הפעילות ועדיין מחכה.'
                                  : urgent ? 'דחוף. דייר במצב חירום.'
                                           : 'דייר צריך מישהו מכם.'));
  lines.push('סיבה: ' + (REASON[reason] || reason) + '.');
  if (mode === 'new' && SOURCE[inp.source]) lines.push(SOURCE[inp.source]);
  if (phone) lines.push('הטלפון של הדייר: ' + phone);
  if (voice && where) lines.push('כתובת: ' + where);
  if (inp.description) lines.push((urgent ? 'מה קרה: ' : 'מה הדייר רוצה: ') + String(inp.description).slice(0, 500));
  // On voice the incoming messages ARE the caller's words as the tool sent
  // them, so the block repeats `description` unless the thread has history.
  const shown = voice ? recent.filter(r => r !== '• ' + String(inp.description || '').slice(0, 300)) : recent;
  if (shown.length) { lines.push(voice ? 'מה הדייר אמר קודם בשיחה:' : 'מה הדייר כתב לאחרונה:'); lines.push(...shown); }
  if (voice) {
    // How to reach them: the number, else the address, else say plainly that
    // the call left neither and what is above is all there is.
    const now_ = urgent ? ' עכשיו' : '';
    const reach = phone ? 'מתקשרים לדייר' + now_ + ' למספר שלמעלה.'
                : (where ? 'אין מספר, אז מתקשרים לדייר' + now_ + ' לפי הכתובת שלמעלה.'
                         : 'בשיחה לא נשאר לא מספר ולא כתובת. יש רק מה שכתוב למעלה.');
    lines.push('מה לעשות: זאת הייתה שיחת טלפון עם הבוט והיא כבר נגמרה, אז מה שכותבים כאן הדייר לא רואה. '
               + reach + ' כשסיימתם, סוגרים את השיחה הזאת כאן (Resolve).'
               + (urgent ? ' אם אף אחד לא סוגר או עונה כאן תוך 10 דקות, ההנהלה מקבלת את זה גם.' : ''));
  } else {
    lines.push('מה לעשות: לענות לדייר כאן, בשיחה הזאת' + (urgent ? ', עכשיו' : '')
               + '. ברגע שמישהו מכם עונה, הבוט מפסיק לענות לו.'
               + (urgent ? ' אם אף אחד לא עונה תוך 10 דקות, ההנהלה מקבלת את זה גם.'
                         : ' עד אז הבוט ממשיך לענות לו במקומכם.'));
  }
} else if (mode === 'escalate1') {
  lines.push(mention('management') + ' ' + mention(dept) + ' דייר מחכה כבר ' + minutes + ' דקות ואף אחד לא ענה לו.');
  lines.push('סיבה: ' + (REASON[reason] || reason) + '.' + (phone ? ' הטלפון של הדייר: ' + phone : ''));
  lines.push(voice ? 'זאת הייתה שיחת טלפון: מישהו צריך להתקשר לדייר עכשיו' + (phone ? ' (' + phone + ')' : (where ? ' (' + where + ')' : '')) + ' ואז לסגור את השיחה הזאת כאן (Resolve).'
                   : 'מישהו צריך לענות לו כאן עכשיו.');
} else {
  lines.push(VALID.map(mention).join(' ') + ' דייר מחכה כבר ' + minutes + ' דקות, גם אחרי שההנהלה קיבלה את זה.');
  lines.push('סיבה: ' + (REASON[reason] || reason) + '.' + (phone ? ' הטלפון של הדייר: ' + phone : ''));
  lines.push(voice ? 'זאת הייתה שיחת טלפון: מישהו חייב להתקשר לדייר עכשיו' + (phone ? ' (' + phone + ')' : (where ? ' (' + where + ')' : '')) + ' ואז לסגור את השיחה הזאת כאן (Resolve).'
                   : 'מישהו חייב לענות לו כאן עכשיו.');
}
const note = lines.join('\n');

// --- The stamp: state lives on the conversation, in the sidebar ------------------
// POST /custom_attributes REPLACES the whole set on Chatwoot 4.16.2 (measured
// 3 Sep: an escalation stamp of two fields wiped the other four, and the next
// escalation fell back to Service). So every stamp is the existing attributes
// with the changes laid over them, staff-set attributes included.
const iso = now.toISO();
let change;
if (mode === 'new') {
  change = { handover_at: iso, handover_reason: reason, handover_reasons: reasons.join(','),
             handover_department: dept, handover_channel: channel,
             handover_source: String(inp.source || 'tool'), handover_paged_at: page ? iso : '',
             handover_escalation: 0 };
} else if (mode === 'page') {
  change = { handover_paged_at: iso };
} else if (mode === 'served') {
  change = { handover_answered_at: iso };
} else {
  change = { handover_paged_at: iso, handover_escalation: mode === 'escalate1' ? 1 : 2 };
}
const stamp = Object.assign({}, ca, change);

return [{ json: {
  skip, why, upgrade, mode, conv_id: conv.id, dept, team_id: TEAMS[dept], priority,
  in_hours: inHours, page, labels: want, note, stamp,
} }];
"""


def http(name, pos, path, body, method="POST", on_error="continueRegularOutput",
         retry=True, cred=BOT_CRED):
    node = {
        "id": "handover-" + name.lower().replace(" ", "-").replace("?", "")[:28],
        "name": name,
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": list(pos),
        "parameters": {
            "method": method,
            "url": "=" + CHATWOOT + path,
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "options": {"timeout": 15000},
        },
        "credentials": cred,
        "onError": on_error,
    }
    if body is not None:
        node["parameters"]["sendBody"] = True
        node["parameters"]["specifyBody"] = "json"
        node["parameters"]["jsonBody"] = body
    if retry:
        # Transient Chatwoot blips are absorbed; the read is not retried because
        # its 404 is the probe path, and deterministic.
        node.update({"retryOnFail": True, "maxTries": 3, "waitBetweenTries": 3000})
    return node


def if_node(name, pos, expr, nid):
    return {
        "id": nid, "name": name, "type": "n8n-nodes-base.if", "typeVersion": 2,
        "position": list(pos),
        "parameters": {"conditions": {
            "options": {"caseSensitive": True, "leftValue": "",
                        "typeValidation": "loose", "version": 1},
            "conditions": [{"id": "c", "leftValue": expr, "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true",
                                         "singleValue": True}}],
            "combinator": "and"}, "options": {}},
    }


def noop(name, pos, nid):
    return {"id": nid, "name": name, "type": "n8n-nodes-base.noOp", "typeVersion": 1,
            "position": list(pos), "parameters": {}}


def workflow():
    D = "$('Decide the routing').first().json"
    nodes = [
        {"id": "handover-sticky", "name": "How a handover pages a department",
         "type": "n8n-nodes-base.stickyNote", "typeVersion": 1, "position": [0, -300],
         "parameters": {"width": 1180, "height": 220, "color": 4, "content":
             "### Hand to a person\n"
             "Inputs: conv_id (Chatwoot display id), phone, reason, department, description, "
             "source (tap | tool | backstop), mode (new | page | escalate1 | escalate2), "
             "now_override (ISO, tests only), channel (whatsapp | voice; 14 Sep: a voice "
             "note tells the rep to phone the resident and resolve, since nothing typed on "
             "a Voice-inbox thread reaches the caller).\n"
             "The alert is the private note that @mentions the department TEAM: every member "
             "gets a Chatwoot notification. Team assignment alone notifies nobody. "
             "14 Sep: reasons name the matter (payment / billing / move / contract / quote / "
             "emergency / caller_request / other), the department follows the reason, priority "
             "is medium except emergencies, the guard is per reason, and only an emergency "
             "climbs the escalation ladder. "
             "POST /labels replaces the set, so labels are written as a union. State is in "
             "the conversation's custom attributes (handover_*). "
             "Called by the WhatsApp bot and the voice-note workflow (mode new) and by the "
             "handback ticker (page / escalate)."}},
        {"id": "handover-trigger", "name": "When handed a conversation",
         "type": "n8n-nodes-base.executeWorkflowTrigger", "typeVersion": 1.1, "position": [0, 0],
         "parameters": {"inputSource": "workflowInputs",
                        "workflowInputs": {"values": [{"name": n, "type": t} for n, t in INPUTS]}}},
        http("Read the conversation", (240, 0),
             "{{ $('When handed a conversation').first().json.conv_id }}", None,
             method="GET", on_error="continueErrorOutput", retry=False,
             cred=ADMIN_CRED),
        noop("Not a real conversation", (480, 180), "handover-not-real"),
        {"id": "handover-decide", "name": "Decide the routing", "type": "n8n-nodes-base.code",
         "typeVersion": 2, "position": [480, 0], "parameters": {"jsCode": DECIDE.strip("\n")}},
        if_node("Anything to do?", (720, 0), "={{ $json.skip !== true }}", "handover-anything"),
        noop("Nothing to do", (960, 180), "handover-nothing"),
        if_node("Page now?", (960, 0), "={{ $json.page === true }}", "handover-pagenow"),
        http("Page the department", (1200, 0), CONV + "/messages",
             "={{ JSON.stringify({ content: %s.note, message_type: 'outgoing', private: true }) }}" % D),
        http("Stamp it", (1440, 0), CONV + "/custom_attributes",
             "={{ JSON.stringify({ custom_attributes: %s.stamp }) }}" % D),
        http("Mark it urgent", (1680, 0), CONV + "/toggle_priority",
             "={{ JSON.stringify({ priority: %s.priority }) }}" % D),
        http("Give it to the team", (1920, 0), CONV + "/assignments",
             "={{ JSON.stringify({ team_id: %s.team_id }) }}" % D),
        http("Label it", (2160, 0), CONV + "/labels",
             "={{ JSON.stringify({ labels: %s.labels }) }}" % D),
        {"id": "handover-report", "name": "Report back", "type": "n8n-nodes-base.set",
         "typeVersion": 3.4, "position": [2400, 0],
         "parameters": {"assignments": {"assignments": [
             {"id": "ok", "name": "ok", "type": "boolean", "value": "={{ true }}"},
             {"id": "conv", "name": "conv_id", "type": "number", "value": "={{ %s.conv_id }}" % D},
             {"id": "mode", "name": "mode", "type": "string", "value": "={{ %s.mode }}" % D},
             {"id": "dept", "name": "department", "type": "string", "value": "={{ %s.dept }}" % D},
             {"id": "paged", "name": "paged", "type": "boolean", "value": "={{ %s.page }}" % D},
             {"id": "hours", "name": "in_hours", "type": "boolean", "value": "={{ %s.in_hours }}" % D},
         ]}, "includeOtherFields": False, "options": {}}},
    ]

    def link(*names):
        return [{"node": n, "type": "main", "index": 0} for n in names]

    connections = {
        "When handed a conversation": {"main": [link("Read the conversation")]},
        "Read the conversation": {"main": [link("Decide the routing"), link("Not a real conversation")]},
        "Decide the routing": {"main": [link("Anything to do?")]},
        "Anything to do?": {"main": [link("Page now?"), link("Nothing to do")]},
        "Page now?": {"main": [link("Page the department"), link("Stamp it")]},
        "Page the department": {"main": [link("Stamp it")]},
        "Stamp it": {"main": [link("Mark it urgent")]},
        "Mark it urgent": {"main": [link("Give it to the team")]},
        "Give it to the team": {"main": [link("Label it")]},
        "Label it": {"main": [link("Report back")]},
    }
    return {"name": WF_NAME, "nodes": nodes, "connections": connections,
            "settings": {"executionOrder": "v1", "timezone": "Asia/Jerusalem"}}


def find():
    for w in W.api("GET", "/api/v1/workflows?limit=250").get("data", []):
        if w["name"] == WF_NAME:
            return w
    return None


def dumps(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False)


def publish(wid):
    back = W.api("GET", "/api/v1/workflows/%s" % wid)
    if back.get("active"):
        print("publish: already published")
        return
    W.api("POST", "/api/v1/workflows/%s/activate" % wid)
    print("publish: %s" % W.api("GET", "/api/v1/workflows/%s" % wid).get("active"))


def main():
    apply = "--apply" in sys.argv
    wf = workflow()
    W.check(wf["nodes"], WF_NAME)
    live = find()
    if live is None:
        print("%s: does not exist yet -> would CREATE (%d nodes)" % (WF_NAME, len(wf["nodes"])))
    else:
        same = (dumps(live["nodes"]) == dumps(wf["nodes"])
                and dumps(live["connections"]) == dumps(wf["connections"]))
        print("%s: exists as %s (%d nodes, published=%s) -> %s"
              % (WF_NAME, live["id"], len(live["nodes"]), live.get("active"),
                 "already matches" if same else "would UPDATE"))
        if same:
            if "--publish" in sys.argv and apply:
                publish(live["id"])
            return
    if not apply:
        print("Dry run. Re-run with --apply to write it.")
        return
    if live is None:
        out = W.api("POST", "/api/v1/workflows", wf)
    else:
        out = W.api("PUT", "/api/v1/workflows/%s" % live["id"], wf)
    print("written: %s (%s)" % (out.get("name"), out.get("id")))
    back = W.api("GET", "/api/v1/workflows/%s" % out["id"])
    print("verify : %d nodes, connections from %s"
          % (len(back["nodes"]), sorted(back["connections"])))
    if "--publish" in sys.argv:
        publish(out["id"])


if __name__ == "__main__":
    main()
