# -*- coding: utf-8 -*-
"""Delete the last two places live still orders a verify_address pre-step.

    python scripts/n8n_whatsapp_toolfix.py            # dry run
    python scripts/n8n_whatsapp_toolfix.py --apply     # write it

WHY
`open_request`'s own description has said "You do NOT need verify_address
before this — there is no step before this" for a while, and the backend agrees:
`debt-tools/index.ts:1562` runs `matchBuilding` inside `open_request` and
refuses with `opened: false` on a building we do not manage. The system prompt
agrees too (prompt.md:1212). But two of `open_request`'s `$fromAI` parameter
docs still tell the model to verify first, and the model reads those on every
single request. One tool, arguing with itself.

`n8n_whatsapp_patch.py` cannot do this: it patches the follow-up menu, the
system prompt and the temperature, and deliberately touches nothing else.
Idempotent — running it twice reports nothing to do.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

WORKFLOW_ID = "u2JjrbcNPYyyh3yl"

FIXES = [
    ("Street and number, as verify_address returned it.",
     "Street and number, as the resident wrote it. The whole sentence is fine; "
     "this tool checks it."),
    (" Verify it with verify_address first.", ""),
]


def main():
    apply = "--apply" in sys.argv
    live = W.api("GET", "/api/v1/workflows/%s" % WORKFLOW_ID)
    node = next((n for n in live["nodes"] if n["name"] == "open_request"), None)
    if node is None:
        sys.exit("No open_request node on the live workflow -- refusing to guess.")

    body = node["parameters"]["jsonBody"]
    before = len(body)
    changed = []
    for old, new in FIXES:
        if old not in body:
            continue
        if body.count(old) != 1:
            sys.exit("REFUSING: %r appears %d times." % (old[:40], body.count(old)))
        body = body.replace(old, new, 1)
        changed.append(old.strip())

    print("workflow : %s  (%s, active=%s)"
          % (live["name"], live["id"], live.get("active")))
    if not changed:
        print("")
        print("Nothing to do. Live already matches.")
        return

    node["parameters"]["jsonBody"] = body
    print("node     : open_request  jsonBody %d -> %d chars" % (before, len(body)))
    print("")
    print("changes:")
    for c in changed:
        print("  - drop: %s" % c)

    if not apply:
        print("")
        print("Dry run. Re-run with --apply to write it.")
        return

    # PUT takes only these four keys; sending id/active/tags back is a 400.
    W.api("PUT", "/api/v1/workflows/%s" % live["id"], {
        "name": live["name"], "nodes": live["nodes"],
        "connections": live["connections"], "settings": live.get("settings", {}),
    })
    print("")
    print("written. Re-run without --apply to confirm it reports nothing to do.")


if __name__ == "__main__":
    main()
