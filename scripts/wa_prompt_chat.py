# -*- coding: utf-8 -*-
"""Run a candidate WhatsApp prompt without installing it anywhere.

    python scripts/wa_prompt_chat.py "im stuck!!!" ">>in the elevator"
    python scripts/wa_prompt_chat.py --file candidate.md "יש ריח גז חזק"
    python scripts/wa_prompt_chat.py --vs candidate.md "im stuck!!!" ">>in the elevator"
    python scripts/wa_prompt_chat.py --ref HEAD~5 "נורה שרופה במסדרון"
    python scripts/wa_prompt_chat.py --runs 5 "im stuck!!!"

WHY THIS EXISTS
`probe_whatsapp.py` is the only way this repo could read the bot's Hebrew, and
it works by pushing the prompt to the live active workflow and talking to it
through the real webhook. That is fine for confirming a shipped change and wrong
for deciding whether to ship one: on 31 Aug a single afternoon of prompt
experiments took thirteen pushes to the workflow that serves real residents,
each one a real model call on the production key. The voice side got
`prompt_chat.py --file` for exactly this reason and WhatsApp never did.

This talks to OpenRouter directly with the same model, temperature and tool
definitions the live agent node uses, so **the wording of the prompt is the only
variable**. Nothing is pushed, nothing is written, and no resident is involved.

WHAT IT IS NOT
Not a replacement for `probe_whatsapp.py`. This exercises the model and the
tools; the live path also has the `Sort` node's short-circuits (greeting, menu
taps, media), the memory buffer's own template, and the three If nodes that
check the model's output afterwards. **A prompt that passes here still has to be
probed live before it is believed.** What this buys is the ten cheap iterations
before that one expensive confirmation.

TOOL CALLS ARE STUBBED, ON PURPOSE
`TOOL_RESULTS` returns plausible fixed values. A candidate prompt is being
judged on what it *says* and *which tool it reaches for with which arguments* —
and the arguments are printed, because a ticket opened against the wrong
apartment is the worst outcome in this system and `[tools] open_request` alone
cannot show it to you. Nothing reaches Supabase, OXS, Chatwoot or n8n.

WHY --runs EXISTS AND DEFAULTS ABOVE ONE
The lesson that cost the most on 31 Aug: one send measures the best case, and
the resident meets the floor. Three probes of a fixed arc passed and the owner
hit the cold reply ten minutes later. At temperature 0.6 a single run is an
anecdote, so this sends each arc more than once by default and prints every
result rather than the first.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(ROOT)

import n8n_whatsapp as W  # noqa: E402  (env(), TOOLS, MODEL, TEMPERATURE)

DOC = "docs/features/11-whatsapp-bot/prompt.md"
EXTRACT = r"^## System prompt\s*$(.*?)(?=^## |\Z)"

# The same fixed answers prompt_probe.py uses for the voice agents, with the
# reference in the format OXS actually returns. `found: True` on status matters:
# a stub that always says "not found" tests the not-found branch and nothing
# else, which is not usually the branch under test.
TOOL_RESULTS = {
    "open_request": {"ok": True, "reference": "255-1042-26"},
    "get_request_status": {"ok": True, "found": True, "reference": "255-1013-26",
                           "type": "elevator", "status": "in_progress",
                           "description": "מעלית תקועה", "other_open": 2},
    "get_balance": {"ok": True, "total": 450, "currency": "ILS",
                    "months": ["2026-07"]},
    "verify_address": {"ok": True, "found": True, "building": "הרצל 14"},
    "transfer_to_human": {"ok": True, "transferred": True},
}
TOOL_DEFAULT = {"ok": True}


def repo_prompt(ref=None):
    """The system prompt from the working tree, or from a git ref."""
    if ref:
        raw = subprocess.run(["git", "show", "%s:%s" % (ref, DOC)],
                             cwd=ROOT, capture_output=True, check=True
                             ).stdout.decode("utf-8")
    else:
        raw = io.open(DOC, encoding="utf-8").read()
    m = re.search(EXTRACT, raw, re.S | re.M)
    if not m:
        sys.exit("No '## System prompt' heading in %s%s"
                 % (DOC, " at " + ref if ref else ""))
    return m.group(1).strip()


WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
_WF = None


def live_workflow():
    """The live WhatsApp workflow, fetched once."""
    global _WF
    if _WF is None:
        _WF = W.api("GET", "/api/v1/workflows/" + WORKFLOW_ID)
    return _WF


def _literals(chunk):
    """Every quoted string in one $fromAI argument list, in order.

    Quote-aware rather than a regex, because the descriptions themselves
    contain quotes: fault_location's says "'apartment' for a leak in their
    kitchen". A naive split on quotes truncates it there.
    """
    out, i, n = [], 0, len(chunk)
    while i < n:
        if chunk[i] in "\"'":
            q, j = chunk[i], i + 1
            while j < n and chunk[j] != q:
                j += 2 if chunk[j] == "\\" else 1
            out.append(chunk[i + 1:j])
            i = j + 1
        else:
            i += 1
    return out


def from_ai(js):
    """(name, description) for every $fromAI(...) in a tool node's jsonBody.

    This IS the parameter schema live sends. n8n's httpRequestTool has no
    separate schema field: the model's arguments are whatever $fromAI asks
    for, inside the JS that builds the request body.
    """
    out, tag, k = [], "$fromAI(", js.find("$fromAI(")
    while k != -1:
        i, depth, q = k + len(tag), 1, None
        while i < len(js) and depth:
            c = js[i]
            if q:
                if c == "\\":
                    i += 1
                elif c == q:
                    q = None
            elif c in "\"'":
                q = c
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            i += 1
        lit = _literals(js[k + len(tag):i - 1])
        if len(lit) >= 2:
            out.append((lit[0], lit[1]))
        k = js.find(tag, i)
    return out


def live_tools():
    """The five tools exactly as the live agent node presents them.

    Not built from `n8n_whatsapp.TOOLS`, which has drifted: on 31 Aug two of
    its five descriptions were stale, including a `verify_address` that still
    said "Call this BEFORE open_request, every time" — an instruction live
    stopped sending. Every field live declares is a plain string with the
    permitted values written into its description, and none are marked
    required; the script's copy declares real enums and a required field, which
    is a different thing to hand a model.

    **This matters most when the prompt is short.** Strip the system prompt
    down and the tool descriptions become most of what the model has to go on,
    so a runner that sends the wrong ones measures the wrong prompt.
    """
    out = []
    for n in live_workflow()["nodes"]:
        if "tool" not in n.get("type", "").lower():
            continue
        p = n.get("parameters") or {}
        props = {name: {"type": "string", "description": doc}
                 for name, doc in from_ai(p.get("jsonBody") or "")}
        out.append({"type": "function",
                    "function": {"name": n["name"],
                                 "description": p.get("toolDescription") or "",
                                 "parameters": {"type": "object",
                                                "properties": props,
                                                "required": []}}})
    if not out:
        sys.exit("No tool nodes found in the live workflow.")
    return out


def report_drift(tools):
    """Say so when the script disagrees with live, rather than picking silently.

    The runner uses live either way. This exists so the drift gets fixed
    instead of quietly widening — it is how the stale descriptions surfaced.
    """
    script = {t["name"]: t["description"].strip() for t in getattr(W, "TOOLS", [])}
    stale = [t["function"]["name"] for t in tools
             if t["function"]["name"] in script
             and script[t["function"]["name"]] != t["function"]["description"].strip()]
    if stale:
        print("drift      : n8n_whatsapp.TOOLS is stale for %s "
              "(live is being used)" % ", ".join(stale))


def ask(messages, key, tools):
    body = {"model": W.MODEL, "messages": messages,
            "temperature": W.TEMPERATURE, "max_tokens": W.MAX_TOKENS,
            "tools": tools}
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions", method="POST",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json",
                 "User-Agent": "homies/1.0"})
    r = json.loads(urllib.request.urlopen(req, timeout=180).read())
    if "choices" not in r:
        sys.exit("OpenRouter returned no choices: %s" % json.dumps(r)[:300])
    return r["choices"][0]["message"], r.get("usage") or {}


def turn(messages, key, tools):
    """One resident turn, run until the agent stops calling tools and speaks."""
    called, tin, tout = [], 0, 0
    for _ in range(6):
        msg, usage = ask(messages, key, tools)
        tin += usage.get("prompt_tokens", 0)
        tout += usage.get("completion_tokens", 0)
        calls = msg.get("tool_calls") or []
        messages.append({k: v for k, v in msg.items()
                         if k in ("role", "content", "tool_calls")})
        if not calls:
            return msg.get("content") or "", called, tin, tout
        for c in calls:
            name = c["function"]["name"]
            raw = c["function"].get("arguments") or "{}"
            try:
                args = json.loads(raw)
            except ValueError:
                # Malformed arguments are a real failure mode and one the model
                # is never told about. Worth seeing rather than swallowing.
                args = {"(unparseable)": raw}
            result = TOOL_RESULTS.get(name, TOOL_DEFAULT)
            called.append((name, args))
            messages.append({"role": "tool", "tool_call_id": c["id"],
                             "content": json.dumps(result, ensure_ascii=False)})
    return "(the agent never stopped calling tools)", called, tin, tout


def live_tap_lines():
    """The tap replies as LIVE sends them, read from the Sort node.

    Not from `n8n_whatsapp.TAP_LINE`, which is dead: it still holds the single
    `בטח, אשמח לעזור...` opener the owner removed on 27 Aug, and live has since
    carried a rotation of three variants per tap keyed by the Hebrew button
    label. Seeding a line no resident receives would start the arc in a
    conversation that does not happen — and that stale constant also contains a
    phrase this prompt bans outright, which is its own bug (see HANDOVER).
    """
    code = [n for n in live_workflow()["nodes"]
            if n["name"] == "Sort"][0]["parameters"]["jsCode"]
    block = re.search(r"TAPPED\s*=\s*\{(.*?)\n\};", code, re.S)
    if not block:
        sys.exit("Could not read TAPPED out of the live Sort node.")
    out = {}
    for label, body in re.findall(r'"([^"]+)":\s*\[(.*?)\]', block.group(1), re.S):
        out[label] = re.findall(r'"([^"]+)"', body)
    return out


TAP_LABEL = {"open": "פתיחת קריאת שירות", "status": "מצב קריאה קיימת"}


def run_arc(prompt, phrases, key, tools, tap=None, taplines=None):
    """One conversation. Returns [(who, text, [(tool, args)]), ...]."""
    messages = [{"role": "system", "content": prompt}]
    rows = []
    # A menu tap is answered by the Sort node, never by the model, but it IS in
    # the conversation the model then sees. Seeding it reproduces the arc the
    # owner's screenshots start from.
    if tap:
        rows = (taplines or {}).get(TAP_LABEL[tap])
        if not rows:
            # Since 31 Aug only the נציג row is answered by the workflow; the
            # others reach the model. Seeding a line live no longer sends would
            # test a conversation that does not happen.
            sys.exit("The %r tap is no longer canned in the live Sort node — it "
                     "goes to the model now. Send %r as the first phrase "
                     "instead of using --tap." % (tap, TAP_LABEL[tap]))
        line = rows[0]
        messages.append({"role": "assistant", "content": line})
        rows.append(("bot", line, []))
    for p in phrases:
        # `>>` means "same conversation" in probe_whatsapp.py. Here every phrase
        # already continues the same one, so accept the prefix and drop it
        # rather than sending it to the model as text.
        p = p[2:].lstrip() if p.startswith(">>") else p
        messages.append({"role": "user", "content": p})
        reply, called, _, _ = turn(messages, key, tools)
        rows.append(("you", p, []))
        rows.append(("bot", reply, called))
    return rows


def show(rows, indent=""):
    for who, text, called in rows:
        for name, args in called:
            print("%s  [tool] %s %s" % (indent, name,
                                        json.dumps(args, ensure_ascii=False)))
        print("%s%-5s %s" % (indent, who + ":", text))


def main():
    ap = argparse.ArgumentParser(
        description="Run a candidate WhatsApp prompt without installing it.")
    ap.add_argument("phrases", nargs="+",
                    help="resident messages; the first starts a conversation "
                         "and each one after continues it")
    ap.add_argument("--file", default=None,
                    help="a candidate prompt from a plain text file, in place "
                         "of the repo's")
    ap.add_argument("--ref", default=None,
                    help="the prompt as the repo had it at this git ref")
    ap.add_argument("--vs", action="append", default=None, metavar="FILE",
                    help="head-to-head: run the same arc against this "
                         "candidate AND the repo prompt. Repeatable, so three "
                         "or more prompts can be compared in one pass")
    ap.add_argument("--tap", choices=["open", "status"], default=None,
                    help="start the arc from a menu tap, as the screenshots do")
    ap.add_argument("--runs", type=int, default=3,
                    help="how many times to run the arc (default 3 — one run "
                         "measures the best case, not the floor)")
    args = ap.parse_args()

    e = W.env()
    key = (e.get("OPENROUTER_API_KEY") or "").strip()
    if not key:
        sys.exit("OPENROUTER_API_KEY missing from .env")
    tools = live_tools()

    if args.file:
        current = io.open(args.file, encoding="utf-8").read().strip()
        label = args.file
    else:
        current = repo_prompt(args.ref)
        label = "repo" + (" at " + args.ref if args.ref else "")

    # Candidates first, incumbent last, so the run to compare against is the
    # one still on screen when the output stops scrolling.
    contenders = [(v, io.open(v, encoding="utf-8").read().strip())
                  for v in (args.vs or [])]
    contenders.append((label, current))

    print("model      : %s   temp %s   max_tokens %s"
          % (W.MODEL, W.TEMPERATURE, W.MAX_TOKENS))
    print("tools      : %s (live definitions, stubbed results — nothing is "
          "written anywhere)"
          % ", ".join(t["function"]["name"] for t in tools))
    report_drift(tools)
    print("runs       : %d per prompt" % args.runs)
    taplines = live_tap_lines() if args.tap else None
    if args.tap:
        if not (taplines or {}).get(TAP_LABEL[args.tap]):
            # Since 31 Aug only the נציג row is answered by the workflow; the
            # others reach the model. Seeding a line live no longer sends would
            # test a conversation that does not happen.
            sys.exit("The %r tap is no longer canned in the live Sort node — it "
                     "reaches the model now. Send %r as the first phrase "
                     "instead of using --tap."
                     % (args.tap, TAP_LABEL[args.tap]))
        print("opening    : menu tap '%s' -> %s"
              % (args.tap, taplines[TAP_LABEL[args.tap]][0]))
    print()

    for name, prompt in contenders:
        print("=" * 78)
        print("%s   (%d chars)" % (name, len(prompt)))
        print("=" * 78)
        for i in range(args.runs):
            if args.runs > 1:
                print("-- run %d --" % (i + 1))
            rows = run_arc(prompt, args.phrases, key, tools, args.tap,
                          taplines)
            show(rows, "  ")
            print()


if __name__ == "__main__":
    main()
