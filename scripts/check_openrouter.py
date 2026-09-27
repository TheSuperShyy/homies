# -*- coding: utf-8 -*-
"""Can the WhatsApp bot's model run right now? Read only, spends nothing.

    python scripts/check_openrouter.py

WHY, 27 Sep. Twice in three days an empty OpenRouter wallet looked like a bot
bug. 25 Sep it was "the bot not replying"; 27 Sep it was "why is it inventing"
-- the agent's model call was refused, the tool-less rescue answered instead,
and it claimed to have replaced light bulbs. Both mornings the key itself
looked healthy, and on 27 Sep the owner, reasonably: *"wait i thought we have
14usd left in the openrouter credits"*.

TWO NUMBERS, AND ONLY ONE OF THEM IS MONEY.

  the key's cap    `/api/v1/auth/key` -> limit / limit_remaining. A CEILING on
                   what this key may spend. "$14.98 left" means the key is
                   allowed $14.98 more, not that $14.98 exists.
  the wallet       `/api/v1/credits` -> total_credits - total_usage. The money
                   every key on the account draws from. OpenRouter: "If your
                   account has a negative credit balance, you may see 402
                   errors."

OpenRouter also pre-authorises a call's prompt before running it, so an almost
empty wallet fails BIG calls first: on 27 Sep a 325-token call passed while the
agent's 20,377-token one was refused ("Prompt tokens limit exceeded: 20377 >
18331"). A wallet under a couple of dollars is already the outage path.

The key is never printed, only its OpenRouter label.
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

VAR = "OPENROUTER_API_KEY"
# Below this the agent's ~20k-token turns start being refused while small
# calls still pass -- the shape that produced the invented repair.
LOW = 2.0


def get(key, path):
    req = urllib.request.Request("https://openrouter.ai/api/v1" + path,
                                 headers={"Authorization": "Bearer " + key,
                                          "user-agent": "homies/1.0"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=20).read() or b"{}").get("data") or {}
    except urllib.error.HTTPError as ex:
        sys.exit("OpenRouter answered HTTP %s on %s: %s" % (ex.code, path, ex.read().decode()[:160]))


def main():
    key = (W.env().get(VAR) or "").strip()
    if not key:
        sys.exit("%s is not in .env" % VAR)
    k = get(key, "/auth/key")
    c = get(key, "/credits")
    bought, spent = float(c.get("total_credits") or 0), float(c.get("total_usage") or 0)
    wallet = bought - spent
    cap = k.get("limit")
    print("key     %s  (%s)" % (k.get("label"), VAR))
    print("cap     %s" % ("none" if cap is None else
                          "$%s, $%.2f of it not yet spent  <- a ceiling, not money"
                          % (cap, float(k.get("limit_remaining") or 0))))
    print("wallet  bought $%.2f, spent $%.2f  ->  $%.2f  <- the money" % (bought, spent, wallet))
    print("")
    if wallet <= 0:
        print("EMPTY. Every real turn goes to the outage path: residents get a "
              "'technical problem' line and the team gets a note. Top up the account.")
        sys.exit(2)
    if wallet < LOW:
        print("LOW. Big turns (the agent) can be refused while small ones pass. Top up soon.")
        sys.exit(1)
    if cap is not None and float(k.get("limit_remaining") or 0) < LOW:
        print("The wallet has money but this KEY is near its cap. Raise the cap in the "
              "OpenRouter dashboard, or the key stops first.")
        sys.exit(1)
    print("OK. The wallet has money and the key has headroom: the real agent can run.")


if __name__ == "__main__":
    main()
