# -*- coding: utf-8 -*-
"""A bank transfer goes to a person from collections, and Michael says so (18 Nov 2026; epoch 111).

    python scripts/n8n_whatsapp_banktransfer.py              # dry run
    python scripts/n8n_whatsapp_banktransfer.py --dump F     # dry run, plus the would-be bot workflow in F
    python scripts/n8n_whatsapp_banktransfer.py --apply      # write both workflows, and the Chatwoot label
    python scripts/n8n_whatsapp_banktransfer.py --restore    # put both snapshots back (the label stays, unused)

WHY. Yariv, 18 Nov: "אם דייר מבקש לבצע תשלום באמצעות העברה בנקאית, צריך לסמן את הצ'ט ככה שזה מועבר לנציג.
בעצם שהבוט יגיד לו אני מעביר אותך לנציג לצורך קבלת הפרטים ולהעביר את הצ'ט". The bot had no account details
anywhere (prompt, tools, service facts) and the one-voice rule kept it from saying it passed anything on. The
owner, on the plan: "ok go ahead, keep answering" -- Michael keeps answering until a person replies, as every
handover has since 3 Sep.

WHAT CHANGES, in one write per workflow:
  The prompt         the one-voice sentence names a third matter (the lift, the standing order, a bank transfer);
                     the list of what his tools do gains it; a sentence after the standing order's says the
                     account details are not his, and that whoever wants to pay by transfer, or asks for the
                     details, is passed to a representative from collections with the note tool, and told so,
                     never when.
  notify_team        a paragraph: a bank transfer is the one note the resident hears about (reason bank_transfer,
                     department collections, at once; then say so; asked again, it is already with them).
                     "Nobody else is in it" gets its exception. The `reason` list gains bank_transfer.
  get_payment_link   one sentence: a bank transfer is not this link; it is notify_team's, instead.
  Memory             epoch 110 -> 111.
  Hand to a person   "Decide the routing": reason bank_transfer always goes to Collections, reads "הדייר רוצה
                     לשלם בהעברה בנקאית ומחכה לפרטי החשבון", adds the `bank-transfer` label, and the note's last
                     line says to send the account details here. n8n_handover.py's DECIDE is the source; live
                     follows it.
  Chatwoot           the label `bank-transfer` in account 2, created if missing.
Not changed: Send, Reply usable?, Try again, Team note this turn?, Let the team know. They already treat
notify_team as done, and check_whatsapp_rules.js's 18 Nov block proves the line goes out whole and a time is still
cut. The incoming phone agent's twin is owed (the owner: WhatsApp first); the debt agent is not included.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py. The bot in use is this workflow (Chatwoot,
since 10 Nov); the UChat copy is off.
"""
import copy
import io
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402
from n8n_whatsapp_ionly import WORKFLOW_ID, once, prompt_of, tools_of, snapshot, restore  # noqa: E402

EPOCH = 111
OLD_KEY = "={{ $json.to }}-110"
NEW_KEY = "={{ $json.to }}-%d" % EPOCH
SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-whatsapp-live-18nov-before-banktransfer.json")
HANDOVER_ID = "oB66atFlWwtkSGgN"
HANDOVER_SNAPSHOT = os.path.join(W.ROOT, "local", "n8n-handover-live-18nov-before-banktransfer.json")
LABEL = {"title": "bank-transfer", "color": "#2E86C1", "show_on_sidebar": True,
         "description": "A resident wants to pay by bank transfer; Collections sends the account details in the chat"}

PROMPT_EDITS = (
    ("רק במעלית ובהוראת קבע זה אחרת, כמו שכתוב בהמשך.",
     "רק במעלית, בהוראת קבע ובהעברה בנקאית זה אחרת, כמו שכתוב בהמשך."),
    ("רושם בקשה להוראת קבע, מברר מה הומי'ז עושה ורושם הערות במערכת.",
     "רושם בקשה להוראת קבע, מעביר לנציג מצוות הגבייה מי שרוצה לשלם בהעברה בנקאית, מברר מה הומי'ז עושה ורושם "
     "הערות במערכת."),
    ("ואומר לו שרשמת אותה ושמישהו מצוות הגבייה ייצור איתו קשר בטלפון, בלי מתי.",
     "ואומר לו שרשמת אותה ושמישהו מצוות הגבייה ייצור איתו קשר בטלפון, בלי מתי. העברה בנקאית היא עניין של צוות "
     "הגבייה: את פרטי החשבון אין לך, ואתה לא ממציא אותם. מי שרוצה לשלם בהעברה בנקאית, או מבקש את פרטי החשבון, אתה "
     "מעביר לנציג מצוות הגבייה עם הכלי שרושם הערות במערכת, ואומר לו שהעברת אותו לנציג מצוות הגבייה שישלח לו כאן את "
     "פרטי החשבון, בלי מתי."),
)

NOTIFY_EDITS = (
    ("\nNever for an emergency or for gas:",
     "\nA bank transfer is the one note the resident hears about. You do not have the account details and never "
     "make them up. A resident who wants to pay by bank transfer, or asks for the account details to transfer to, is "
     "handed to the collections team with this call, at once: reason bank_transfer, department collections, with what "
     "they asked. Then tell them, in your own words, that you have passed them to a representative from the "
     "collections team, who will send them the account details here in this chat: never when, nothing more promised, "
     "then whether there is anything else you can help with meanwhile. Asked about it again, it is already with "
     "collections: say so, without calling again.\nNever for an emergency or for gas:"),
    ("Nobody else is in it: no team, no manager,",
     "Apart from a bank transfer, nobody else is in it: no team, no manager,"),
)

NOTIFY_BODY_EDITS = (
    ("caller_request = they asked for a person; other = anything else past you.",
     "caller_request = they asked for a person; bank_transfer = they want to pay by bank transfer or ask for the "
     "account details (department collections); other = anything else past you."),
    ("One of payment/billing/move/contract/quote/caller_request/other.",
     "One of payment/billing/move/contract/quote/caller_request/bank_transfer/other."),
)

LINK_EDITS = (
    ("Call the moment a resident wants to pay, asks how or where to pay, asks for their payment link, or says after a "
     "balance that they will settle it.",
     "Call the moment a resident wants to pay, asks how or where to pay, asks for their payment link, or says after a "
     "balance that they will settle it. A bank transfer is not this: a resident who wants to pay by bank transfer, or "
     "asks for the account details, is handed to collections with notify_team (reason bank_transfer) instead."),
)

# "Homies — Hand to a person", node "Decide the routing". The same edits are in n8n_handover.py's DECIDE.
DECIDE_EDITS = (
    ("const DEPT_BY_REASON = { payment: 'collections', billing: 'collections',\n",
     "const DEPT_BY_REASON = { payment: 'collections', billing: 'collections', bank_transfer: 'collections',\n"),
    ("  dept = VALID.includes(inp.department) ? inp.department\n       : (DEPT_BY_REASON[reason] || 'service');\n",
     "  // 18 Nov: a bank transfer always goes to Collections, whatever `department` says: they send the details.\n"
     "  dept = reason === 'bank_transfer' ? 'collections'\n"
     "       : VALID.includes(inp.department) ? inp.department\n"
     "       : (DEPT_BY_REASON[reason] || 'service');\n"),
    ("  if (mode.startsWith('escalate')) add.push('escalated');\n",
     "  if (mode.startsWith('escalate')) add.push('escalated');\n"
     "  // 18 Nov (Yariv: mark the chat): a bank transfer is marked as such, and the mark outlives `served`.\n"
     "  if (reason === 'bank_transfer') add.push('bank-transfer');\n"),
    ("  billing: 'הדייר לא מסכים עם חיוב, או צריך מסמך (חשבונית, קבלה, אישור)',\n",
     "  billing: 'הדייר לא מסכים עם חיוב, או צריך מסמך (חשבונית, קבלה, אישור)',\n"
     "  // 18 Nov (n8n_whatsapp_banktransfer.py): the one note the bot tells the resident about.\n"
     "  bank_transfer: 'הדייר רוצה לשלם בהעברה בנקאית ומחכה לפרטי החשבון',\n"),
    ("    lines.push('מה לעשות: לענות לדייר כאן, בשיחה הזאת' + (urgent ? ', עכשיו' : '')\n",
     "    lines.push('מה לעשות: ' + (reason === 'bank_transfer' ? 'לשלוח לדייר כאן, בשיחה הזאת, את פרטי החשבון של הבניין שלו'\n"
     "                                                     : 'לענות לדייר כאן, בשיחה הזאת') + (urgent ? ', עכשיו' : '')\n"),
)


def banktransfer(wf):
    """The bot workflow with the prompt, notify_team and get_payment_link changed. Not memory."""
    out = copy.deepcopy(wf)
    by = {n["name"]: n for n in out["nodes"]}
    opts = by["Answer the resident"]["parameters"]["options"]
    sm = opts["systemMessage"]
    for old, new in PROMPT_EDITS:
        sm = once(sm, old, new)
    opts["systemMessage"] = sm
    for node, edits in (("notify_team", NOTIFY_EDITS), ("get_payment_link", LINK_EDITS)):
        p = by[node]["parameters"]
        d = p["toolDescription"]
        for old, new in edits:
            d = once(d, old, new)
        p["toolDescription"] = d
    p = by["notify_team"]["parameters"]
    body = p["jsonBody"]
    for old, new in NOTIFY_BODY_EDITS:
        body = once(body, old, new)
    p["jsonBody"] = body
    return out


def decide_code(code):
    for old, new in DECIDE_EDITS:
        code = once(code, old, new)
    return code


def chatwoot(method, path, body=None):
    e = W.env()
    req = urllib.request.Request(e["CHATWOOT_URL"].rstrip("/") + "/api/v1/accounts/2" + path, method=method,
                                 data=json.dumps(body).encode("utf-8") if body is not None else None,
                                 headers={"api_access_token": e["CHATWOOT_API_TOKEN"].strip(),
                                          "Content-Type": "application/json", "User-Agent": "homies/1.0"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read() or b"{}")


def handover_restore():
    snap = json.load(open(HANDOVER_SNAPSHOT, encoding="utf-8"))
    W.api("PUT", "/api/v1/workflows/%s" % HANDOVER_ID, {
        "name": snap["name"], "nodes": snap["nodes"], "connections": snap["connections"],
        "settings": snap.get("settings", {})})
    print("restored %s from %s" % (HANDOVER_ID, os.path.relpath(HANDOVER_SNAPSHOT, W.ROOT)))


def main():
    import n8n_handover as H  # the source of the routing code
    if "--restore" in sys.argv:
        restore(SNAPSHOT)
        handover_restore()
        print("Then put n8n_handover.py's DECIDE back (git revert), and n8n_whatsapp.py's MEMORY_EPOCH.")
        return
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    by = {n["name"]: n for n in live["nodes"]}
    hlive = W.api("GET", "/api/v1/workflows/%s" % HANDOVER_ID)
    hby = {n["name"]: n for n in hlive["nodes"]}
    hcode = hby["Decide the routing"]["parameters"]["jsCode"]
    key = by["Conversation so far"]["parameters"].get("sessionKey")
    bot_done = key == NEW_KEY and LINK_EDITS[0][1] in by["get_payment_link"]["parameters"]["toolDescription"]
    hand_done = "bank_transfer: 'הדייר רוצה לשלם בהעברה בנקאית" in hcode
    if bot_done and hand_done:
        print("Nothing to do. Live already hands a bank transfer to collections, epoch %d." % EPOCH)
        return
    if not bot_done and key != OLD_KEY:
        sys.exit("REFUSING: the memory key is %r, not epoch 110's. Read live first." % key)

    # The bot workflow.
    new = banktransfer(live) if not bot_done else copy.deepcopy(live)
    nb = {n["name"]: n for n in new["nodes"]}
    if not bot_done:
        changed = [n["name"] for n in new["nodes"] if n != by[n["name"]]]
        if sorted(changed) != sorted(["Answer the resident", "notify_team", "get_payment_link"]):
            sys.exit("REFUSING: unexpected nodes would change: %s" % changed)
        if W.MEMORY_EPOCH != EPOCH:
            sys.exit("REFUSING: n8n_whatsapp.MEMORY_EPOCH is %d, not %d. Move the repo first." % (W.MEMORY_EPOCH, EPOCH))
        if prompt_of(new) != W.system_prompt():
            sys.exit("REFUSING: the would-be prompt is not docs/features/11-whatsapp-bot/prompt.md's. "
                     "Edit the document first; live follows it.")
        W.check_memory_epoch(prompt=prompt_of(new), tools=tools_of(new))
        nb["Conversation so far"]["parameters"]["sessionKey"] = NEW_KEY
        print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
        print("prompt   : %s (%d chars) -> %s (%d chars)" % (W.epoch_hash(prompt_of(live)), len(prompt_of(live)),
                                                             W.epoch_hash(prompt_of(new)), len(prompt_of(new))))
        print("tools    : %s -> %s" % (W.epoch_hash(tools_of(live)), W.epoch_hash(tools_of(new))))
        print("memory   : %s -> %s (every buffer starts fresh)" % (OLD_KEY, NEW_KEY))
        print("changed  : %s" % ", ".join(changed + ["Conversation so far"]))

    # Hand to a person.
    if not hand_done:
        hnew = decide_code(hcode)
        if hnew.strip() != H.DECIDE.strip():   # n8n keeps the code without the script's leading and trailing newline
            sys.exit("REFUSING: the would-be routing code is not n8n_handover.py's DECIDE. Edit the script first; "
                     "live follows it.")
        print("handover : %s (%s) 'Decide the routing' %d -> %d chars" % (hlive["name"], HANDOVER_ID, len(hcode), len(hnew)))

    labels = [l.get("title") for l in chatwoot("GET", "/labels").get("payload", [])]
    print("label    : %s" % ("bank-transfer exists" if "bank-transfer" in labels else "bank-transfer will be created"))

    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        NP.dump(new["nodes"], new["connections"], path)
        print("dumped   : %s (the would-be bot workflow, secret replaced)" % path)
    if not apply:
        print("\nDry run. Re-run with --apply to write it.")
        return

    if "bank-transfer" not in labels:
        r = chatwoot("POST", "/labels", LABEL)
        print("label    : created, id %s" % r.get("id"))
    if not hand_done:
        if not os.path.exists(HANDOVER_SNAPSHOT):
            text = json.dumps(hlive, ensure_ascii=False, indent=1)
            secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
            if secret and secret in text:
                sys.exit("REFUSING: the handover workflow holds the webhook secret; snapshot it by hand.")
            io.open(HANDOVER_SNAPSHOT, "w", encoding="utf-8").write(text)
            print("snapshot : %s" % os.path.relpath(HANDOVER_SNAPSHOT, W.ROOT))
        nodes = copy.deepcopy(hlive["nodes"])
        for n in nodes:
            if n["name"] == "Decide the routing":
                n["parameters"]["jsCode"] = decide_code(hcode)
        W.api("PUT", "/api/v1/workflows/%s" % HANDOVER_ID, {
            "name": hlive["name"], "nodes": nodes, "connections": hlive["connections"],
            "settings": hlive.get("settings", {})})
        hb = W.api("GET", "/api/v1/workflows/%s" % HANDOVER_ID)
        hc = {n["name"]: n for n in hb["nodes"]}["Decide the routing"]["parameters"]["jsCode"]
        print("handover : written, active=%s, routing %s" % (hb.get("active"),
                                                            "as written" if hc == decide_code(hcode) else "DIFFERS"))
    if not bot_done:
        if snapshot(live, SNAPSHOT):
            print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))
        W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
            "name": live["name"], "nodes": new["nodes"], "connections": new["connections"],
            "settings": live.get("settings", {})})
        back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
        bb = {n["name"]: n for n in back["nodes"]}
        print("\nwritten  : %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
        print("  prompt %s (want %s); tools %s (want %s); memory key %s" % (
            W.epoch_hash(prompt_of(back)), W.epoch_hash(prompt_of(new)),
            W.epoch_hash(tools_of(back)), W.epoch_hash(tools_of(new)),
            bb["Conversation so far"]["parameters"]["sessionKey"]))
        for node in ("notify_team", "get_payment_link"):
            print("  %s: %s" % (node, "as written" if bb[node]["parameters"] == nb[node]["parameters"] else "DIFFERS"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
