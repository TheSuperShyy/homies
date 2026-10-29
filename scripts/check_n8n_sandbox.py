"""Offline checks of the feature 19 transforms on fresh GET copies of the live workflows.

    python scripts/check_n8n_sandbox.py

Reads the live bot, "Hand to a person" and the debt-tools router (GET only), runs the
sandbox transforms in memory and checks that nothing in the copies can reach production:
every URL goes to the sandbox account, the sandbox function or the sandbox router; Supabase
is only ever read; no live workflow id, credential or webhook path is left.
"""
import copy, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from n8n_layout import overlaps
from n8n_sandbox import LIVE_IDS, load, sandboxify_bot, sandboxify_handover, sandboxify_router

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CFG = {"account_id": 99, "chatwoot_url": "https://chat.srv1879140.hstgr.cloud",
       "supabase_url": "https://nmxlhlmcnnggnnuxyelt.supabase.co", "sandbox_secret": "SANDBOX-SECRET",
       "cred_admin": {"id": "A", "name": "SANDBOX Chatwoot admin"}, "cred_bot": {"id": "B", "name": "SANDBOX Chatwoot bot"},
       "handover_id": "HANDOVER-SBX", "teams": {"collections": 11, "operations": 12, "management": 13, "service": 14}}

live_bot, live_h, live_r = load("u2JjrbcNPYyyh3yl"), load("oB66atFlWwtkSGgN"), load("lXofknAbE5wu5nwQ")
keep_bot, keep_h, keep_r = copy.deepcopy(live_bot), copy.deepcopy(live_h), copy.deepcopy(live_r)
bot, h, r = sandboxify_bot(live_bot, CFG), sandboxify_handover(live_h, CFG), sandboxify_router(live_r, CFG)
assert (live_bot, live_h, live_r) == (keep_bot, keep_h, keep_r), "the transforms must not mutate the live copies"
live_secret = re.search(r'const SHARED = "([^"]+)"',
                        next(n for n in keep_bot["nodes"] if n["name"] == "Sort")["parameters"]["jsCode"]).group(1)


def reach(wf):
    """Every HTTP call a copy can make must stay inside the sandbox. Returns the problems."""
    bad = []
    for n in wf["nodes"]:
        if n["type"] not in ("n8n-nodes-base.httpRequest", "n8n-nodes-base.httpRequestTool"):
            continue
        p = n["parameters"]
        url, method = str(p.get("url", "")), p.get("method", "GET")
        if "supabase.co/rest/v1/" in url:
            ok = method == "GET"
        elif "/functions/v1/" in url:
            ok = re.search(r"/functions/v1/debt-tools-sandbox(?![-\w])", url) is not None
        elif "chat.srv1879140.hstgr.cloud" in url:
            ok = "/api/v1/accounts/%d/" % CFG["account_id"] in url
        elif "n8n-zqvb.srv1879140.hstgr.cloud" in url:
            ok = url.endswith("/webhook/homies-debt-tools-sandbox")
        else:
            ok = False
        if not ok:
            bad.append("%s: %s %s" % (n["name"], method, url[:90]))
    return bad


def new_overlaps(copy_wf, live_wf):
    seen = {frozenset(o[:2]) for o in overlaps(live_wf["nodes"])}
    return [o for o in overlaps(copy_wf["nodes"]) if frozenset(o[:2]) not in seen]


for label, wf, live in (("bot", bot, keep_bot), ("handover", h, keep_h), ("router", r, keep_r)):
    text = json.dumps(wf, ensure_ascii=False)
    for bad in ("/api/v1/accounts/2/", "graph.facebook.com", "/rest/v1/messages",
                "Chatwoot admin (api_access_token)", "Chatwoot bot (api_access_token)", "Homies WhatsApp typing (Meta)"):
        assert bad not in text, "%s: live reference left in the sandbox: %s" % (label, bad)
    for live_path in (r"/functions/v1/debt-tools(?![-\w])", r"/webhook/homies-debt-tools(?![-\w])",
                      r"homies-whatsapp(?![-\w])"):
        assert not re.search(live_path, text), "%s: still points at the live %s" % (label, live_path)
    for wid in LIVE_IDS:
        assert wid not in text, "%s: a live workflow id is still referenced: %s" % (label, wid)
    assert live_secret not in text, "%s: the live webhook secret is still in the copy" % label
    assert reach(wf) == [], "%s: calls that leave the sandbox: %s" % (label, reach(wf))
    assert new_overlaps(wf, live) == [], "%s: new overlapping nodes: %s" % (label, new_overlaps(wf, live))
    assert wf["name"].startswith("SANDBOX — "), label
    assert any(n["type"] == "n8n-nodes-base.stickyNote" and "SANDBOX" in n["parameters"]["content"]
               for n in wf["nodes"]), "%s: no sandbox note on the canvas" % label

by = {n["name"]: n for n in bot["nodes"]}
assert by["WhatsApp"]["parameters"]["path"] == "homies-whatsapp-sandbox"
assert by["WhatsApp"]["webhookId"] == "homies-whatsapp-sandbox-v1"
assert 'const SHARED = "SANDBOX-SECRET"' in by["Sort"]["parameters"]["jsCode"]
assert by["Conversation so far"]["parameters"]["sessionKey"].endswith("-sbx"), "memory must not share the live session key"
assert by["Anything newer?"]["type"] == "n8n-nodes-base.code"
assert bot["connections"]["Anything newer? (fetch)"]["main"][0][0]["node"] == "Anything newer?"
assert bot["connections"]["Anything newer?"]["main"][0][0]["node"] == "Still the last word?"
for name in ("Show typing", "Show typing again", "Log inbound", "Log reply"):
    assert by[name]["type"] == "n8n-nodes-base.noOp", name
assert all(n["parameters"]["workflowId"]["value"] == "HANDOVER-SBX"
           for n in bot["nodes"] if n["type"] == "n8n-nodes-base.executeWorkflow")
for tool in ("open_request", "notify_team"):
    assert by[tool]["parameters"]["url"].endswith("/webhook/homies-debt-tools-sandbox"), tool
code = next(n for n in h["nodes"] if n["name"] == "Decide the routing")["parameters"]["jsCode"]
assert "const TEAMS = { collections: 11, operations: 12, management: 13, service: 14 };" in code
rb = {n["name"]: n for n in r["nodes"]}
assert rb["Vapi tool call"]["parameters"]["path"] == "homies-debt-tools-sandbox"
assert rb["Vapi tool call"]["webhookId"] == "homies-debt-tools-sandbox-v1"
print("check_n8n_sandbox: copy ok")

# --- Yariv's section 6, in the sandbox copy only ---------------------------------
from n8n_sandbox_section6 import WHO_RULE, section6
supa = next(n for n in keep_bot["nodes"] if n["name"] == "Anything newer?")["credentials"]["httpHeaderAuth"]
bot_before_s6 = copy.deepcopy(bot)
s6 = section6(bot, supa)
assert bot == bot_before_s6, "section6 must not mutate the copy it is given"
by6 = {n["name"]: n for n in s6["nodes"]}
assert "לדבר עם נציג" not in by6["Sort"]["parameters"]["jsCode"], "the menu still offers a representative"
assert "לדבר עם נציג" not in by6["Send"]["parameters"]["jsonBody"], "Send still re-attaches the representative button"
prompt = by6["Answer the resident"]["parameters"]["options"]["systemMessage"]
assert "לדבר עם נציג" not in prompt, "the prompt still describes the representative button"
assert WHO_RULE in prompt
assert "identified in the system" in by6["open_request"]["parameters"]["jsonBody"], "the ticket tool still asks every time"
assert by6["Who is writing?"]["parameters"]["method"] == "GET"
assert by6["Who is writing?"]["parameters"]["url"].startswith("=https://nmxlhlmcnnggnnuxyelt.supabase.co/rest/v1/residents?phone=eq.%2B")
assert by6["Who is writing?"].get("alwaysOutputData") is True
assert s6["connections"]["Still the last word?"]["main"][0] == [{"node": "Who is writing?", "type": "main", "index": 0}]
assert s6["connections"]["Who is writing?"]["main"][0] == [{"node": "Add who", "type": "main", "index": 0}]
assert {c["node"] for c in s6["connections"]["Add who"]["main"][0]} == {"Worth a word?", "Show typing"}
assert "$('Add who')" in by6["Answer the resident"]["parameters"]["text"]
assert reach(s6) == [], "section 6: calls that leave the sandbox: %s" % reach(s6)
assert new_overlaps(s6, keep_bot) == [], "section 6: new overlapping nodes: %s" % new_overlaps(s6, keep_bot)
# 29 Oct: the balance recognises the sender; nothing of the typed-only rule is left to argue with it.
from n8n_sandbox_section6 import BALANCE_TOOL
bal6 = by6["get_balance"]["parameters"]
assert bal6["toolDescription"].count(BALANCE_TOOL) == 1, "the balance tool text is not the new one"
for gone in ("IDENTITY FIRST", "not even when they say it is the same one", "do not use the number they are messaging from"):
    assert gone not in bal6["toolDescription"], "the balance still forbids the sender's number: " + gone
assert "NOT the number the message arrived from" not in bal6["jsonBody"] and "Required." not in bal6["jsonBody"]
assert "full-name-and-phone" not in by6["open_request"]["parameters"]["toolDescription"]
print("check_n8n_sandbox: section 6 ok")

# --- C: the bot handles it; a manager request leaves the team a note (owner, 27 Oct) ---
from n8n_sandbox_section6 import SOLVE_EDITS
for old, new in SOLVE_EDITS:
    if new:
        assert new in prompt, "section 6 C missing: " + new[:40]
assert "ענייני ועד הבית" not in prompt, "the committee fee is still on the staff-only list"
assert "המשפט שלך נגמר בזה שהצוות יודע" not in prompt, "the prompt still ends a manager request on 'the team knows'"
assert "רק מה שבאמת מעבר לך נשאר אצל הצוות" not in prompt, "a tenant's 'you can't help' is still a way out to the team"
assert "לפני שמשהו עובר למנהל" not in prompt and "אין מה להעביר" not in prompt, "the bot still asks so it can forward"
from n8n_sandbox_section6 import NOTE_EDITS
note6 = by6["notify_team"]["parameters"]["toolDescription"]
for old, new in NOTE_EDITS:
    assert new in note6 and old not in note6, "notify_team not brought in line: " + old[:40]
assert "Call it only for what is really past you" not in note6, "notify_team still sends a manager request to the team"
# The owner's protocol, 27 Oct evening: management told at once, never gatekept or conceded.
from n8n_sandbox_section6 import MANAGER_RULE, MANAGER_TOOL
assert prompt.count(MANAGER_RULE) == 1 and note6.count(MANAGER_TOOL) == 1, "the manager rule is not in whole"
assert "בקשה ריקה לא נרשמת" not in prompt, "the prompt still withholds the manager note until the matter"
assert "A request with nothing in it is never a note" not in note6, "notify_team still withholds the manager note"
print("check_n8n_sandbox: section 6 C ok")

# --- D: one reply per burst, checked again right before Send (owner's chat, 27 Oct) ---
by6 = {n["name"]: n for n in s6["nodes"]}
assert s6["connections"]["Type for a moment"]["main"][0][0]["node"] == "Anything newer before sending? (fetch)"
assert s6["connections"]["Anything newer before sending? (fetch)"]["main"][0][0]["node"] == "Still the last word before sending?"
assert s6["connections"]["Still the last word before sending?"]["main"][0][0]["node"] == "Send"
assert by6["Anything newer before sending? (fetch)"]["alwaysOutputData"] is True
assert "const GREETING = new RegExp(" in by6["Still the last word before sending?"]["parameters"]["jsCode"]
assert reach(s6) == [] and new_overlaps(s6, keep_bot) == []
print("check_n8n_sandbox: section 6 D ok")
