# -*- coding: utf-8 -*-
"""The bot sees the photos a tenant sends (2 Nov 2026, epoch 92).

    python scripts/n8n_whatsapp_photo.py              # dry run
    python scripts/n8n_whatsapp_photo.py --dump F     # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_photo.py --apply      # write it
    python scripts/n8n_whatsapp_photo.py --restore    # put the snapshot back

WHY. Asked whether an image analyser was in, the answer was no. A photo has been kept and hung on
the ticket since 17 Sep (n8n_whatsapp_media.py, store_media), but the model was told "you do not see
its content". The owner, 2 Nov: "ok lets implement that".

HOW, the platform's own way. The Agent node (v3) hands every binary image on its input item to the
model ("Automatically Passthrough Binary Images", on by default; read on the instance, n8n 2.33.3).
Gemini reads images. So the photos only have to be on the item when it reaches the agent:
- "A photo to look at?" -> "Read the photos" hangs off "Still the last word?", drawn below "Show
  typing" (the indicator goes first, as the gate's typing check wants) and above "Who is writing?".
  Under executionOrder v1 a parent's branches run top to bottom, so it finishes before the branch
  that leads to the answer.
  It lists the conversation's messages from Chatwoot with the admin credential the workflow already
  holds. A photo is often its own message, with the words two seconds later. That photo's own run
  was silenced by the burst join, so only Chatwoot still has its file.
- "Any photos?" -> "Show the photos" sits between {Carry on, Try again} and the agent.
  - It takes the burst's photos: the inbound image rows of "Anything newer?" up to the last reply,
    read as "Still the last word?" reads them, matched by Chatwoot message id.
  - It downloads up to three, the newest, from their Chatwoot links, which need no key.
  - It puts them on the item as binary, with `photos_shown`.
  - A turn with no photo skips both IFs' work, so text turns are unchanged and no slower.
- The note the model reads on a photo turn changed in one place. Where a photo is on the item:
  "it is attached and you see it, and what is seen in it is part of what he tells you". Where none
  could be fetched, the old sentence stays: "you do not see its content".
  - The prompt already forbids instructions and safety advice, so a photo adds no rule
    (CONTEXT: delete competing text before adding a rule).
- Memory epoch 91 -> 92: the inject changed, and the buffers hold turns where the bot could not see
  a photo.

Not changed: the prompt, the tools, the guards, Send, Sort, Still the last word?.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F --replay`, the new pin, `--apply`, the check on live, the
owner's handset, `--watch`.
"""
import copy
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402
from n8n_whatsapp_patch import layout_complaints  # noqa: E402

EPOCH = 92
OLD_KEY = "={{ $json.to }}-91"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-02nov-before-photo.json")
ADDED = ("A photo to look at?", "Read the photos", "Any photos?", "Show the photos", "Photos are seen")

NOTE_OLD = "אתה לא רואה את התוכן שלה, ולכן מה שקרה ואיפה מגיע רק מהמילים.]'"
NOTE_NEW = ("' + ($json.photos_shown > 1 ? 'התמונות מצורפות כאן ואתה רואה אותן, ומה שרואים בהן הוא חלק ממה שהוא "
            "מספר לך.' : $json.photos_shown ? 'היא מצורפת כאן ואתה רואה אותה, ומה שרואים בה הוא חלק ממה שהוא מספר "
            "לך.' : 'אתה לא רואה את התוכן שלה, ולכן מה שקרה ואיפה מגיע רק מהמילים.') + ']'")

SHOW_JS = r"""// 2 Nov 2026 (scripts/n8n_whatsapp_photo.py): this turn's photos go to the model, which sees them.
// The agent passes every binary image on its input item to the model. A photo is often its own
// message, with the words two seconds later, and that photo's run was silenced by the burst join.
// So the burst is read the way Still the last word? reads it: Anything newer?'s rows, newest first,
// up to the last reply. Read the photos (Chatwoot) has the files; their links need no key.
// At most three, the newest. A photo that cannot be fetched is left out, and the note then says the
// model cannot see it.
const MAX = 3;
// Nothing here may cost the reply: on any surprise the item goes on as it came, with no photo shown.
const asCame = () => $input.all().map(item => ({ json: Object.assign({}, item.json, { photos_shown: 0 }) }));
try {
let rows = [];
try { rows = $('Anything newer?').all().map(i => i.json); } catch (e) { rows = []; }
const burst = new Set();
for (const r of rows) {
  if (r.direction === 'outbound') break;
  if (r.message_type === 'image' && r.external_id) burst.add(String(r.external_id));
}
let msgs = [];
try { msgs = $('Read the photos').first().json.payload || []; } catch (e) { msgs = []; }
const urls = [];
for (const m of msgs.slice().sort((a, b) => a.id - b.id)) {
  if (m.message_type !== 0 || !burst.has(String(m.id))) continue;
  for (const a of (m.attachments || [])) {
    if (a && a.file_type === 'image' && a.data_url) urls.push(String(a.data_url));
  }
}
// This run's own photo, from Sort, in case Chatwoot's list did not have it.
let own = [];
try { own = $('Sort').first().json.attachments || []; } catch (e) { own = []; }
for (const a of own) {
  if (a && a.file_type === 'image' && a.data_url && !urls.includes(String(a.data_url))) urls.push(String(a.data_url));
}
const binary = {};
const pick = urls.slice(-MAX);
for (let k = 0; k < pick.length; k++) {
  try {
    const r = await this.helpers.httpRequest({ url: pick[k], encoding: 'arraybuffer', returnFullResponse: true, timeout: 15000 });
    const mime = String((r.headers || {})['content-type'] || '').split(';')[0].trim().toLowerCase();
    if (!/^image\/(jpeg|png|webp|gif)$/.test(mime)) continue;
    const ext = mime === 'image/jpeg' ? 'jpg' : mime.split('/')[1];
    binary['photo_' + k] = await this.helpers.prepareBinaryData(Buffer.from(r.body), 'photo_' + k + '.' + ext, mime);
  } catch (e) {
    // left out: the note says what is true
  }
}
const shown = Object.keys(binary).length;
if (!shown) return asCame();
return $input.all().map(item => ({ json: Object.assign({}, item.json, { photos_shown: shown }), binary }));
} catch (e) {
  return asCame();
}
"""


def _if(name, node_id, pos, left):
    return {
        "id": node_id, "name": name, "type": "n8n-nodes-base.if", "typeVersion": 2, "position": pos,
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 1},
                "conditions": [{"id": "p", "leftValue": left, "rightValue": "",
                                "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
                "combinator": "and",
            },
            "options": {},
        },
    }


def photo(wf):
    """The workflow with the photo path and the true note. Not memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    # The Chatwoot account path and the admin credential, as the workflow already uses them.
    assign = by["Assign to the replier"]
    base = re.match(r"=?(https://[^/]+/api/v1/accounts/\d+/)", assign["parameters"]["url"]).group(1)
    admin = assign["credentials"]["httpHeaderAuth"]

    out["nodes"] += [
        # Below Show typing (the typing indicator goes first) and above Who is writing? (the way to the
        # answer): under executionOrder v1 a parent's branches run top to bottom.
        _if("A photo to look at?", "photo-look", [960, -300], "={{ $json.photo === true }}"),
        {
            "id": "photo-read", "name": "Read the photos", "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2, "position": [1200, -240],
            "parameters": {
                "method": "GET",
                "url": "=" + base + "conversations/{{ $('Still the last word?').first().json.conv_id }}/messages",
                "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
                "options": {"timeout": 10000},
            },
            "credentials": {"httpHeaderAuth": admin},
            # A failed read must never cost the reply: the note then says the photo cannot be seen.
            "retryOnFail": True, "maxTries": 2, "waitBetweenTries": 1000, "onError": "continueRegularOutput",
        },
        _if("Any photos?", "photo-any", [720, 540], "={{ $json.photo === true }}"),
        {
            "id": "photo-show", "name": "Show the photos", "type": "n8n-nodes-base.code", "typeVersion": 2,
            # No onError: the code catches everything itself and passes the item on as it came. n8n's
            # "continue" would replace the item with {error}, and the agent would read nothing.
            "position": [720, 420], "parameters": {"jsCode": SHOW_JS},
        },
        {
            "id": "photo-note", "name": "Photos are seen", "type": "n8n-nodes-base.stickyNote", "typeVersion": 1,
            "position": [960, -840],
            "parameters": {"width": 480, "height": 200, "color": 4, "content":
                "## Photos are seen (2 Nov)\n"
                "On a turn with a photo, Read the photos lists the chat from Chatwoot, before the branch to the "
                "answer runs. Show the photos then puts the burst's photos (up to 3) on the item, and the agent "
                "hands them to the model. A photo that cannot be fetched leaves the old note: \"you do not see "
                "it\". Owned by scripts/n8n_whatsapp_photo.py."},
        },
    ]

    c = out["connections"]
    # Topmost under "Still the last word?", so it runs before "Who is writing?" leads on to the answer.
    c["Still the last word?"]["main"][0].append({"node": "A photo to look at?", "type": "main", "index": 0})
    c["A photo to look at?"] = {"main": [[{"node": "Read the photos", "type": "main", "index": 0}], []]}
    for src in ("Carry on", "Try again"):
        outs = c[src]["main"][0]
        hits = [i for i, t in enumerate(outs) if t["node"] == "Answer the resident"]
        assert len(hits) == 1, (src, outs)
        outs[hits[0]] = {"node": "Any photos?", "type": "main", "index": 0}
    c["Any photos?"] = {"main": [[{"node": "Show the photos", "type": "main", "index": 0}],
                                 [{"node": "Answer the resident", "type": "main", "index": 0}]]}
    c["Show the photos"] = {"main": [[{"node": "Answer the resident", "type": "main", "index": 0}]]}

    p = {n["name"]: n for n in out["nodes"]}["Answer the resident"]["parameters"]
    p["text"] = once(p["text"], NOTE_OLD, NOTE_NEW)
    return out


def inject_of(wf):
    return {n["name"]: n for n in wf["nodes"]}["Answer the resident"]["parameters"]["text"]


def main():
    if "--restore" in sys.argv:
        return restore(SNAPSHOT)
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    if key == NEW_KEY and all(n in by for n in ADDED):
        print("Nothing to do. Live already shows the model its photos, epoch %d." % EPOCH)
        return
    if key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 91's. Read live first." % key)
    if any(n in by for n in ADDED):
        sys.exit("REFUSING: live already has some of the new nodes: %s" % [n for n in ADDED if n in by])

    new = photo(live)
    nb = {n["name"]: n for n in new["nodes"]}
    nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
    grew = layout_complaints(new["nodes"]) - layout_complaints(live["nodes"])
    if grew:
        sys.exit("REFUSING: new layout problems:\n  " + "\n  ".join(sorted(grew)))

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d -> %d (added: %s)" % (len(live["nodes"]), len(new["nodes"]), ", ".join(ADDED)))
    print("prompt   : %s (unchanged: %s)" % (W.epoch_hash(prompt_of(new)), prompt_of(new) == prompt_of(live)))
    print("tools    : %s (unchanged: %s)" % (W.epoch_hash(tools_of(new)), tools_of(new) == tools_of(live)))
    print("inject   : %s -> %s" % (W.epoch_hash(inject_of(live)), W.epoch_hash(inject_of(new))))
    print("memory   : %s -> %s (every buffer starts fresh)" % (OLD_KEY, NEW_KEY))
    print("changed  : %s" % ", ".join(n["name"] for n in new["nodes"] if n["name"] in by and n != by[n["name"]]))

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
    print("\nwritten  : %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  inject %s (want %s); new nodes present: %s; memory key %s" % (
        W.epoch_hash(inject_of(back)), W.epoch_hash(inject_of(new)), all(n in bb for n in ADDED),
        bb["Conversation so far"]["parameters"]["sessionKey"]))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
