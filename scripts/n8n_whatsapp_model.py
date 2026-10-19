# -*- coding: utf-8 -*-
"""The WhatsApp bot's model: gemini-2.5-flash -> Gemini 3.1 Pro (19 Oct, the owner's word).

    python scripts/n8n_whatsapp_model.py            # dry run
    python scripts/n8n_whatsapp_model.py --dump F   # dry run, plus the would-be workflow in F
    python scripts/n8n_whatsapp_model.py --apply    # write it
    python scripts/n8n_whatsapp_model.py --restore  # put the snapshot back (2.5 Flash, 1024, 0.6)

WHY. 19 Oct, 11:30-11:57 UTC (14:30-14:57 Israel): Yariv's own chat (conversation 54,
execution 114483) asked what was happening with his ticket and got "הכל בסדר תודה, מה
שלומך היום?" -- the bot's previous greeting again; Ido's (conversation 44, 114583) got
"איזו קריאה את רוצה שאבדוק" -- feminine to a man, and a request for a reference number
instead of a lookup; the owner's own chat got one sentence twice. Owner: "the
conversation went crazy it hallucinated so right now we need to change LLM like a
better one gemini 3 pro". The second-try repeat is the workflow's (CONTEXT, "The bot
repeats itself"); the rest is the model's.

WHAT CHANGES, the OpenRouter node only. It feeds Answer the resident, Worth a word? and
Could not answer, so all three move together.
  model        google/gemini-2.5-flash -> google/gemini-3.1-pro-preview
               "Gemini 3 Pro" on OpenRouter is 3.1 Pro Preview: google/gemini-3-pro-preview
               is no longer on their model list (checked 19 Oct). $2 in / $12 out per 1M
               tokens against $0.30 / $2.50.
  maxTokens    1024 -> 8192
               Gemini 3 thinks before every answer and OpenRouter counts the thinking
               against max_tokens: a cap the thinking fills returns finish_reason
               "length" with EMPTY content -- a silent bot (their parameters doc). 1024
               was set on 25 Sep for the pre-authorisation shortfall when the wallet was
               near zero; OpenRouter still pre-authorises the full cap, so a call now
               needs about $0.13 of balance (8192 x $12/M plus the ~13k-token prompt at
               $2/M). Under that, every reply is "Payment required" again.
  temperature  0.6 -> 1.0
               Google, Gemini 3 developer guide: "we strongly recommend keeping the
               temperature parameter at its default value of 1.0 ... setting it below 1.0
               may lead to unexpected behavior, such as looping or degraded performance".
               The 31 Aug reasons for 0.6 were about 2.5 Flash.

NOT TOUCHED: the prompt, the tools, the guards, Send, the memory key. No epoch bump: a
buffer holds plain turns, nothing model-specific.

NO REASONING CONTROL. The lmChatOpenRouter v1 node has no reasoning parameter, so the
model thinks at Google's default for 3.1 Pro, "high". Measured 19 Oct on a two-step
tool round-trip in n8n's own message shape (the assistant's tool call echoed back
without reasoning_details): it works -- the tool call, then the answer -- with 131 and
447 reasoning tokens, 4 and 7 seconds, $0.0083 for both calls. The lever if cost or
latency bites: an OpenRouter preset (@preset/..., made in their dashboard) with
reasoning effort "low", or the OpenAI chat-model node pointed at OpenRouter, which has
a reasoningEffort option. Either is a different change.

COST. A resident message is two model calls (Worth a word? ~0.6k tokens in, Answer the
resident ~13k in), three with a retry: about $0.03-0.07 against $0.004 on 2.5 Flash.
The wallet held $7.25 on 19 Oct 12:20 UTC: one to two hundred messages. Gemini's
implicit prompt caching may cut the input part; not counted on.

EVERY CHANGE HERE SHIPS THROUGH scripts/check_whatsapp_rules.py: `--dump F`, then
`check_whatsapp_rules.py --candidate F` (no model-facing text moves, so the pins hold
and there is nothing to replay), `check_patchers_idle.py F`, `--apply`, the check on
live, every patcher idle, the owner's own message, `--watch`.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402
import n8n_whatsapp_nopromise as NP  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
SNAPSHOT = os.path.join(W.ROOT, "docs", "handover",
                        "n8n-whatsapp-live-19oct-before-model.json")
PLACEHOLDER = NP.PLACEHOLDER
NL = chr(10)

OLD = {"model": "google/gemini-2.5-flash", "maxTokens": 1024, "temperature": 0.6}
NEW = {"model": "google/gemini-3.1-pro-preview", "maxTokens": 8192, "temperature": 1.0}


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
    with open(SNAPSHOT, "w", encoding="utf-8", newline=NL) as f:
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
    print("n8n_whatsapp.py still says %s / %s / %s; put the repo back too (git revert), or "
          "n8n_whatsapp_patch.py will push the temperature forward again."
          % (W.MODEL, W.MAX_TOKENS, W.TEMPERATURE))


def model_node(nodes):
    models = [n for n in nodes if n["type"].endswith("lmChatOpenRouter")]
    if len(models) != 1:
        sys.exit("REFUSING: %d OpenRouter model nodes on the live workflow, expected one."
                 % len(models))
    return models[0]


def settings(node):
    p = node["parameters"]
    o = p.get("options") or {}
    return {"model": p.get("model"), "maxTokens": o.get("maxTokens"), "temperature": o.get("temperature")}


def main():
    if "--restore" in sys.argv:
        return restore()
    apply = "--apply" in sys.argv

    repo = {"model": W.MODEL, "maxTokens": W.MAX_TOKENS, "temperature": W.TEMPERATURE}
    for k, v in NEW.items():
        if repo[k] != v:
            sys.exit("REFUSING: n8n_whatsapp.py says %s = %r; this change was written for %r."
                     % (k, repo[k], v))

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    nodes, conns = live["nodes"], live["connections"]
    node = model_node(nodes)
    fed = [c["node"] for c in (conns.get(node["name"], {}).get("ai_languageModel") or [[]])[0]]
    if snapshot(live):
        print("snapshot : %s" % os.path.relpath(SNAPSHOT, W.ROOT))

    have = settings(node)
    params = node["parameters"]
    opts = params.setdefault("options", {})
    changes = []
    for k in ("model", "maxTokens", "temperature"):
        if have[k] == NEW[k]:
            continue
        if have[k] != OLD[k]:
            sys.exit("REFUSING: live %s is %r, neither the one this replaces (%r) nor the "
                     "new one (%r)." % (k, have[k], OLD[k], NEW[k]))
        if k == "model":
            params["model"] = NEW[k]
        else:
            opts[k] = NEW[k]
        changes.append("%s: %r -> %r" % (k, OLD[k], NEW[k]))

    print("workflow : %s  (%s, active=%s)" % (live["name"], live["id"], live.get("active")))
    print("nodes    : %d" % len(nodes))
    print("model    : node %r feeds %s" % (node["name"], ", ".join(fed) or "nothing"))
    print("live     : model %s, maxTokens %s, temperature %s"
          % (have["model"], have["maxTokens"], have["temperature"]))
    if not changes:
        print("")
        print("Nothing to do. Live already matches.")
        return
    print("")
    print("changes:")
    for ch in changes:
        print("  - %s" % ch)

    if "--dump" in sys.argv:
        path = sys.argv[sys.argv.index("--dump") + 1]
        NP.dump(nodes, conns, path)
        print("")
        print("dumped   : %s (the would-be workflow, secret replaced)" % path)

    if not apply:
        print("")
        print("Dry run. Re-run with --apply to write it.")
        return

    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": nodes, "connections": conns,
        "settings": live.get("settings", {})})
    back = W.api("GET", "/api/v1/workflows/%s" % live["id"])
    got = settings(model_node(back["nodes"]))
    print("")
    print("written: %d nodes, active=%s" % (len(back["nodes"]), back.get("active")))
    print("  model %s, maxTokens %s, temperature %s (want %s, %s, %s)"
          % (got["model"], got["maxTokens"], got["temperature"],
             NEW["model"], NEW["maxTokens"], NEW["temperature"]))
    print("  read-back %s" % ("matches" if got == NEW else "DOES NOT MATCH -- look before anything else"))
    print("Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
