# -*- coding: utf-8 -*-
"""Every WhatsApp patcher's dry run, against a would-be workflow, before any write.

    python scripts/check_patchers_idle.py F    # F: a patcher's --dump

WHY, 1 Oct evening. "Every WhatsApp patcher's dry run is idle" was only ever
checked AFTER an --apply, on live. A change that moves texts owned by several
patchers (n8n_whatsapp_gender.py: the prompt, three small writers, the retry
note, the team note, the promise filter, the opener) can leave one of them
wanting to rewrite its node back -- and the first anyone would hear of it is a
patcher pushing old text over the new. This runs them all before the write:
live, with the dump's nodes laid over it (as check_whatsapp_rules.py
--candidate does), served to every patcher in place of the real GET.

Nothing is written. Every non-GET call raises, no patcher gets --apply, and
each one's snapshot() is replaced by a no-op so a dry run cannot leave a file
in docs/handover. The webhook secret is put back into the dump in memory only.

Expected: IDLE for every patcher except the documented baseline (CONTEXT.md,
"How a WhatsApp change ships": batch.py's old drift; open, handover, promise,
transfer and untemplate refusing on nodes removed in mid-September).
"""
import contextlib
import copy
import importlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(os.path.dirname(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

WF_ID = "u2JjrbcNPYyyh3yl"
PLACEHOLDER = "REPLACE_WITH_N8N_WEBHOOK_SECRET"


def would_be(dump_path):
    live = W.api("GET", "/api/v1/workflows/%s" % WF_ID)
    secret = W.env().get("N8N_WEBHOOK_SECRET", "").strip()
    dumped = json.loads(open(dump_path, encoding="utf-8").read().replace(PLACEHOLDER, secret))
    idx = {n["name"]: i for i, n in enumerate(live["nodes"])}
    wf = copy.deepcopy(live)
    # 5 Oct (n8n_whatsapp_safetynet.py): a dump that adds or removes nodes is the
    # would-be workflow whole, nodes and wires; laid over live by name it would
    # keep the removed nodes and drop the new ones.
    if {n["name"] for n in dumped["nodes"]} != set(idx) and "connections" in dumped:
        wf["nodes"], wf["connections"] = dumped["nodes"], dumped["connections"]
        return wf
    for n in dumped["nodes"]:
        if n["name"] in idx:
            wf["nodes"][idx[n["name"]]] = n
    return wf


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    real_api = W.api
    wf = would_be(sys.argv[1])

    def fake_api(method, path, body=None):
        if method != "GET":
            raise RuntimeError("BLOCKED %s %s" % (method, path))
        if path.startswith("/api/v1/workflows/%s" % WF_ID):
            return copy.deepcopy(wf)
        return real_api(method, path, body)       # other workflows and listings, read only

    W.api = fake_api
    names = sorted(f[:-3] for f in os.listdir(HERE)
                   if f.startswith("n8n_whatsapp_") and f.endswith(".py"))
    not_idle = 0
    for name in names:
        buf = io.StringIO()
        status = "ran"
        try:
            mod = importlib.import_module(name)
            if hasattr(mod, "W"):
                mod.W.api = fake_api
            if hasattr(mod, "snapshot"):
                mod.snapshot = lambda *a, **k: False
            sys.argv = [name + ".py"]
            with contextlib.redirect_stdout(buf):
                mod.main()
        except SystemExit as e:
            status = "exit: %s" % (str(e.code)[:300] if e.code not in (None, 0) else "0")
        except Exception as e:  # noqa: BLE001 -- report it, keep going
            status = "error: %s" % str(e)[:300]
        out = buf.getvalue()
        idle = "Nothing to do" in out
        not_idle += 0 if idle else 1
        print("%-28s %s" % (name, "IDLE" if idle else "NOT IDLE  [%s]" % status))
        if not idle:
            for line in [l for l in out.splitlines() if l.strip()][-6:]:
                print("     " + line[:220])
    print("")
    print("%d of %d patchers not idle (the baseline is 6: batch, handover, open, promise, "
          "transfer, untemplate)" % (not_idle, len(names)))


if __name__ == "__main__":
    main()
