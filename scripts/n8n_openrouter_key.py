# -*- coding: utf-8 -*-
"""Point the WhatsApp bot's model node at a different OpenRouter key.

    python scripts/n8n_openrouter_key.py OPENROUTER_API_KEY
    python scripts/n8n_openrouter_key.py OPENROUTER_API_KEY --apply

WHY, 25 Sep. The bot stopped answering mid-conversation: every model call came
back `Payment required - perhaps check your payment details?` and the retry node
threw, so the resident got silence. The account's main key was spent. The owner
named a second key that still draws, and this is how it gets swapped without
anyone typing a secret into a chat window or a node field.

IT CREATES A NEW CREDENTIAL AND REPOINTS THE NODE; it never edits the old one.
n8n refuses to hand a stored secret back (`GET /credentials/:id` is 403, which
is correct of it), so an in-place edit would be a blind write over a value
nobody can read first. A new credential beside the old one means the rollback is
one run of this script with the previous key's variable name, and the spent
credential is still sitting there if it is ever topped up.

IDEMPOTENT BY CREDENTIAL NAME. The workflow stores the credential's name beside
its id, so a second run sees the node already pointing at the target and reports
nothing to do. That is also why the name carries the env variable in it: two
keys from the same account are otherwise indistinguishable in the n8n UI.

27 SEP: RUN WITH OPENROUTER_API_KEY. The owner consolidated .env onto that one
variable (the CAPPED15 one is gone) and asked for the node to use it. The node
was already on that key -- the 402 that day named it by hash, and sha256 of
the .env value matched -- but through `key 2`, a credential pasted by hand in
the UI on 25 Sep that nothing in the repo could trace. The run replaced a
label, not a key: credential `Homies OpenRouter (OPENROUTER_API_KEY)`.
`key 2` and the unused CAPPED15 credential are left on n8n; delete them in
the UI only if the owner asks.

A KEY'S CAP IS NOT MONEY. `scripts/check_openrouter.py` prints the cap and the
wallet side by side; the wallet is the one that runs out.

THE KEY IS NEVER PRINTED. Only its OpenRouter label (`sk-or-v1-abc...xyz`),
which is what their dashboard shows, and which is the thing you actually need in
order to tell two keys apart.
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n8n_whatsapp as W  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"
CRED_TYPE = "openRouterApi"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    if len(args) != 1:
        sys.exit("give the .env variable holding the key, e.g. OPENROUTER_API_KEY")
    var = args[0].strip()

    e = W.env()
    key = (e.get(var) or "").strip()
    if not key:
        sys.exit("%s is not in .env" % var)

    # --- is the key actually good? ask OpenRouter, not the balance page -----
    # `/credits` reports the ACCOUNT, and a capped key on a spent-looking
    # account can still draw; 25 Sep proved exactly that. So the only honest
    # test is the label plus what the key says about its own limit.
    req = urllib.request.Request("https://openrouter.ai/api/v1/auth/key",
                                 headers={"Authorization": "Bearer " + key,
                                          "user-agent": "homies/1.0"})
    try:
        info = (json.loads(urllib.request.urlopen(req, timeout=20).read() or b"{}")
                .get("data") or {})
    except urllib.error.HTTPError as ex:
        sys.exit("OpenRouter rejected %s: HTTP %s %s" % (var, ex.code, ex.read().decode()[:160]))
    label = info.get("label")
    limit, left = info.get("limit"), info.get("limit_remaining")
    print("key         : %s  (%s)" % (label, var))
    print("cap         : %s" % ("none" if limit is None else
                                "%s, %.2f left" % (limit, float(left or 0))))

    name = "Homies OpenRouter (%s)" % var

    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    users = [n for n in live["nodes"] if (n.get("credentials") or {}).get(CRED_TYPE)]
    if not users:
        sys.exit("No node on the workflow uses a %s credential." % CRED_TYPE)
    for n in users:
        c = n["credentials"][CRED_TYPE]
        print("node        : %-18s -> %s (%s)" % (n["name"], c.get("name"), c.get("id")))

    if all((n["credentials"][CRED_TYPE].get("name") == name) for n in users):
        print("\nNothing to do. Every node already uses %r." % name)
        return

    if not apply:
        print("\nWould create credential %r and repoint %d node(s)." % (name, len(users)))
        print("Dry run. Re-run with --apply to write it.")
        return

    made = W.api("POST", "/api/v1/credentials",
                 {"name": name, "type": CRED_TYPE, "data": {"apiKey": key}})
    cid = made.get("id")
    if not cid:
        sys.exit("credential not created: %s" % json.dumps(made)[:200])
    print("\ncreated     : credential %s  %r" % (cid, name))

    for n in users:
        n["credentials"][CRED_TYPE] = {"id": cid, "name": name}
    W.api("PUT", "/api/v1/workflows/%s" % WORKFLOW_ID, {
        "name": live["name"], "nodes": live["nodes"],
        "connections": live["connections"], "settings": live.get("settings", {}),
    })
    print("repointed   : %s" % ", ".join(n["name"] for n in users))
    print("\nThe old credential is untouched. To go back, run this with the "
          "previous key's variable name.")


if __name__ == "__main__":
    main()
