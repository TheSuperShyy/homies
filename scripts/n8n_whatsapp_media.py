# -*- coding: utf-8 -*-
"""A resident's photo lands on the ticket -- the workflow half.

    python scripts/n8n_whatsapp_media.py            # dry run
    python scripts/n8n_whatsapp_media.py --apply    # write it
    python scripts/n8n_whatsapp_media.py --restore  # put the 17 Sep snapshot back

WHY, 17 SEP

The client's old bot (ManyChat -> Make -> Monday, scanned this morning)
attaches the resident's photo to the task it files. Ours dropped it: the
photo reaches Chatwoot, which keeps the file and shows it in the conversation,
but the ticket never hears of it and the bot tells the resident it only reads
text. Owner: adopt the photo; the bot accepts and acknowledges, never invites.

WHAT THIS SHIPS

- `Sort` reads Chatwoot's `attachments[]` and emits the images (`attachments`,
  `photo`, `_media`), and logs a photo as `message_type 'image'` rather than
  the generic 'attachment'.
- Two nodes hung off `Log inbound`: `Photo to keep?` (was there an image?) and
  `Keep the photo`, which posts the URLs to the Edge Function as `store_media`
  with the same envelope and the same secret the other tools use. The function
  copies the bytes into our own bucket and links the row to the resident's
  live ticket, or leaves it for the next `open_request` to adopt.
- `Anything newer?` / `Still the last word?` carry the photo through a burst:
  a picture followed two seconds later by the words is one thought, and the
  reply that survives the join must still know a picture arrived.
- `Reply usable?` no longer treats a one-word answer to a photo as a rescue
  case: "קיבלתי" after a picture is an answer, not a failure.

Off `Log inbound`, not off `Sort`, for two reasons. The messages row must
exist before the copy starts (the burst join reads it), and the copy must
finish before the 4-second wait ends (the reply's note says the photo is
saved). `Log inbound` is a leaf with `alwaysOutputData`, so exactly one item
flows on from every branch -- work, canned and menu alike.

The template sentence the model reads and the memory epoch are NOT written
here: `n8n_whatsapp_teamnote.py --apply` owns those and runs after this, so
the note goes live only once the flag it reads exists.

The epoch guard runs first for the same reason it runs everywhere: this
delivery is one half of a change the guard already knows about, and it must
refuse until `n8n_whatsapp.py` has been told.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_untemplate as U  # noqa: E402
from n8n_whatsapp_handover import ensure_link  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-17sep-before-media.json")
PLACEHOLDER = "REPLACE_WITH_N8N_WEBHOOK_SECRET"

IF_NODE = "Photo to keep?"
KEEP_NODE = "Keep the photo"

# --- Sort: read the attachments -------------------------------------------
SORT_A1_OLD = "const attachment = !text.trim();"
SORT_A1_NEW = (
    "const attachment = !text.trim();\n"
    "// Chatwoot's attachments[] on message_created: { id, message_id, file_type,\n"
    "// extension, data_url, thumb_url, file_size, width, height }. Images are\n"
    "// copied into our own bucket by the Edge Function (Keep the photo, 17 Sep);\n"
    "// anything else keeps the old \"arrived, cannot be read\" note and is not stored.\n"
    "const images = (Array.isArray(body.attachments) ? body.attachments : [])\n"
    "  .filter(a => a && a.file_type === 'image' && a.data_url)\n"
    "  .map(a => ({ data_url: String(a.data_url), file_type: 'image',\n"
    "               extension: a.extension || '', file_size: a.file_size || 0 }));\n"
    "const photo = images.length > 0;"
)
SORT_A2_OLD = "tap: tapNow, tap_now: !!tapNow, attachment,"
SORT_A2_NEW = "tap: tapNow, tap_now: !!tapNow, attachment, photo, _media: photo, attachments: images,"
SORT_A3_OLD = "in_text: inText, msg_type: attachment ? 'attachment' : 'text',"
SORT_A3_NEW = "in_text: inText, msg_type: photo ? 'image' : (attachment ? 'attachment' : 'text'),"
SORT_A4_OLD = "in_text: inText, msg_type: 'greeting', message_id: id,"
SORT_A4_NEW = "in_text: inText, msg_type: 'greeting', message_id: id, _media: photo, attachments: images,"

# --- The burst join carries the photo ---------------------------------------
NEWER_OLD = "&select=external_id,body,direction"
NEWER_NEW = "&select=external_id,body,direction,message_type"
LAST_A_OLD = ("const backlog = [];\n"
              "for (const r of rows) {\n"
              "  if (r.direction === 'outbound') break;")
LAST_A_NEW = ("const backlog = [];\n"
              "let photo = j.photo === true;\n"
              "for (const r of rows) {\n"
              "  if (r.direction === 'outbound') break;\n"
              "  // A photo in the unanswered backlog is still a photo when the text\n"
              "  // after it answers for both.\n"
              "  if (r.message_type === 'image') photo = true;")
LAST_B_OLD = "burst_size: backlog.length || 1 })"
LAST_B_NEW = "burst_size: backlog.length || 1, photo: photo })"

# --- One word after a photo is an answer ------------------------------------
USABLE_OLD = "return w === 1 && $('Sort').first().json.greeting === true;"
USABLE_NEW = ("return w === 1 && ($('Sort').first().json.greeting === true "
              "|| $('Sort').first().json.photo === true);")


def if_node():
    return {
        "id": "photo_to_keep", "name": IF_NODE,
        "type": "n8n-nodes-base.if", "typeVersion": 2,
        "position": [1200, -360],
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "",
                            "typeValidation": "loose", "version": 1},
                "conditions": [{
                    "id": "p",
                    # $('Sort') and not $json: the input here is Log inbound's
                    # output (the messages row), not the sorted message.
                    "leftValue": "={{ $('Sort').first().json._media }}",
                    "rightValue": "",
                    "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                }],
                "combinator": "and",
            },
            "options": {},
        },
    }


def keep_node():
    e = W.env()
    return {
        "id": "keep_the_photo", "name": KEEP_NODE,
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [1440, -360],
        # The reply must never wait on a failed copy: continue on error, and
        # always emit an item so the branch closes cleanly.
        "onError": "continueRegularOutput",
        "alwaysOutputData": True,
        "credentials": {"httpHeaderAuth": {
            "id": e["N8N_TOOLSECRET_CRED_ID"].strip(), "name": "Homies tool secret"}},
        "parameters": {
            "method": "POST",
            "url": e["SUPABASE_URL"].rstrip("/") + "/functions/v1/debt-tools",
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": (
                "={{ JSON.stringify({ message: { call: { id: 'wa:' + $('Sort').first().json.to, "
                "assistantOverrides: { variableValues: { phone: $('Sort').first().json.to } } }, "
                "toolCalls: [{ id: 'wa-media', function: { name: 'store_media', arguments: { "
                "phone: $('Sort').first().json.to, conv_id: $('Sort').first().json.conv_id, "
                "message_id: $('Sort').first().json.message_id, "
                "attachments: $('Sort').first().json.attachments } } }] } }) }}"
            ),
            "options": {"timeout": 20000},
        },
    }


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
    with open(SNAPSHOT, "w", encoding="utf-8", newline="\n") as f:
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
    for need in ("Sort", "Log inbound", "Anything newer?", "Still the last word?",
                 "Reply usable?", "Answer the resident"):
        if need not in by:
            sys.exit("No %r node on the live workflow -- refusing to guess." % need)

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    before_layout = layout_complaints(nodes)
    changes = []

    def edit(node, field, old, new, label):
        val = by[node]["parameters"].get(field) or ""
        # `new in val` alone: four of these anchors keep the old text as a
        # prefix of the new, so "old absent" can never be the done signal.
        if new in val:
            return
        if old not in val:
            sys.exit("Anchor missing on live %r.%s -- refusing to guess:\n  %s"
                     % (node, field, label))
        by[node]["parameters"][field] = val.replace(old, new, 1)
        changes.append(label)

    edit("Sort", "jsCode", SORT_A1_OLD, SORT_A1_NEW, "Sort: read Chatwoot's attachments[]")
    edit("Sort", "jsCode", SORT_A2_OLD, SORT_A2_NEW, "Sort: emit photo / _media / attachments")
    edit("Sort", "jsCode", SORT_A3_OLD, SORT_A3_NEW, "Sort: a photo logs as message_type 'image'")
    edit("Sort", "jsCode", SORT_A4_OLD, SORT_A4_NEW, "Sort: a greeting with a photo keeps the photo")
    edit("Anything newer?", "url", NEWER_OLD, NEWER_NEW, "Anything newer?: select message_type")
    edit("Still the last word?", "jsCode", LAST_A_OLD, LAST_A_NEW, "Still the last word?: a photo in the backlog counts")
    edit("Still the last word?", "jsCode", LAST_B_OLD, LAST_B_NEW, "Still the last word?: emit photo")

    # The one-word guard lives in a condition expression, not jsCode.
    cond = by["Reply usable?"]["parameters"]["conditions"]["conditions"]
    words = next((c for c in cond if c.get("id") == "words"), None)
    if words is None:
        sys.exit("Reply usable? has no 'words' condition -- refusing to guess.")
    if USABLE_NEW not in words["leftValue"]:
        if USABLE_OLD not in words["leftValue"]:
            sys.exit("Anchor missing on live 'Reply usable?' words condition.")
        words["leftValue"] = words["leftValue"].replace(USABLE_OLD, USABLE_NEW, 1)
        changes.append("Reply usable?: one word after a photo is an answer")

    for want in (if_node(), keep_node()):
        have = by.get(want["name"])
        if have is None:
            nodes.append(want)
            by[want["name"]] = want
            changes.append("add node %r (%s)" % (want["name"], want["type"]))
        else:
            for field in ("parameters", "type", "typeVersion", "credentials",
                          "onError", "alwaysOutputData"):
                if field in want and have.get(field) != want[field]:
                    have[field] = want[field]
                    changes.append("update %r %s" % (want["name"], field))

    if ensure_link(conns, "Log inbound", IF_NODE, 0):
        changes.append("wire Log inbound -> %s" % IF_NODE)
    if ensure_link(conns, IF_NODE, KEEP_NODE, 0):
        changes.append("wire %s (true) -> %s" % (IF_NODE, KEEP_NODE))

    worse = sorted(layout_complaints(nodes) - before_layout)
    if worse:
        sys.exit("This would make the canvas less readable:\n  " + "\n  ".join(worse))

    if not changes:
        print("\nNothing to do. Live already matches.")
        return

    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
    print("\nchanges:")
    for c in changes:
        print("  - %s" % c)

    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": nodes,
        "connections": conns, "settings": live.get("settings", {}),
    })
    print("\nwritten. Re-run without --apply to confirm it reports nothing to do, then\n"
          "run n8n_whatsapp_teamnote.py --apply for the note and the epoch -- until\n"
          "that lands, the photo is kept and the bot still says it cannot see it.")


if __name__ == "__main__":
    main()
