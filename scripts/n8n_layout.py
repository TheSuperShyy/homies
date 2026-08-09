"""Refuse to deploy an n8n workflow whose nodes are badly placed.

A workflow is not only a thing that runs. It is a diagram somebody opens at
eight in the morning while it is failing, and a node hidden behind another node
is a minute of that failure spent finding it.

Imported by n8n_deploy.py, n8n_whatsapp.py and n8n_queue.py, which each call
check(nodes) before pushing. A rule that has to be remembered is a rule that
lasts until the next hurried commit; this one fails the deploy.

PLACEMENT ONLY
No sticky notes, no node descriptions, nothing written on the canvas. The
canvas shows the shape of the flow and nothing else; the reasoning lives in the
script that builds the workflow, where it sits beside the code it explains and
can be diffed. Two places for the same explanation is two places to drift.

WHY THIS EXISTS AS CODE AND NOT AS A NOTE
`Anything to write?` and `Needs the real answer?` sat at exactly [460, 120] in
the debt-tools workflow from the day it was written until 8 Aug. Identical
coordinates, so one node was drawn perfectly on top of the other and the canvas
showed seven nodes where there were eight. Nothing failed. The workflow ran
correctly the whole time. It was simply not possible to see what it did.

    python scripts/n8n_layout.py       # check every workflow on the instance
"""
import json
import os
import re
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# n8n draws a node roughly 200 wide and 100 tall, plus its label underneath.
# Two nodes closer than this on BOTH axes visually collide even when their
# coordinates differ, so the check is a box and not an equality test.
NODE_W = 200
NODE_H = 100

# The grid every workflow here is laid out on. One column per stage of the flow,
# one row per branch. Sticking to it means a reader who has seen one of these
# workflows can read the next one without re-learning where things are.
COL = 240
ROW = 180


class LayoutError(Exception):
    pass


def overlaps(nodes):
    """Pairs of nodes drawn on top of each other. Sticky notes are excluded.

    A sticky note is a background rectangle that is *supposed* to sit under the
    nodes it annotates — including it would make every documented workflow fail
    the check, which is the wrong incentive exactly.
    """
    real = [n for n in nodes if "stickyNote" not in n.get("type", "")]
    bad = []
    for i, a in enumerate(real):
        for b in real[i + 1:]:
            dx = abs(a["position"][0] - b["position"][0])
            dy = abs(a["position"][1] - b["position"][1])
            if dx < NODE_W and dy < NODE_H:
                bad.append((a["name"], b["name"], dx, dy))
    return bad


def off_grid(nodes):
    """Nodes not sitting on the column/row grid.

    Not about tidiness for its own sake. A grid is what makes a second workflow
    readable by someone who has read a first one: the trigger is always at the
    left, each column is one step further along, and two nodes in the same column
    are two branches of the same decision. Freehand coordinates lose that, and
    the canvas has to be re-read from scratch every time.
    """
    return [(n["name"], n["position"]) for n in nodes
            if n["position"][0] % COL or n["position"][1] % (ROW // 3)]


def check(nodes, name=""):
    """Raise unless the nodes are well placed. Called before every push.

    Placement only — no sticky notes, no descriptions. The canvas shows the
    shape of the flow; the reasoning lives in the script that builds it, where
    it is version-controlled and can be diffed.
    """
    problems = []

    for a, b, dx, dy in overlaps(nodes):
        problems.append("%r and %r overlap (dx=%d, dy=%d)%s"
                        % (a, b, dx, dy, " — identical position" if dx == dy == 0 else ""))

    for n, pos in off_grid(nodes):
        problems.append("%r is at %s, off the %d x %d grid" % (n, pos, COL, ROW // 3))

    if problems:
        raise LayoutError(
            "%s is not well placed:\n    %s" % (name or "This workflow",
                                                "\n    ".join(problems)))


def _env():
    return dict(re.findall(r"^([A-Z0-9_]+)=(.*)$",
                           open(os.path.join(ROOT, ".env"), encoding="utf-8").read(), re.M))


def main():
    """Check every workflow on the instance, not only the ones this repo builds."""
    e = _env()
    base = e["N8N_BASE_URL"].strip().rstrip("/")
    h = {"X-N8N-API-KEY": e["N8N_API_KEY"].strip(), "accept": "application/json",
         "User-Agent": "curl/8.5.0"}
    data = json.load(urllib.request.urlopen(
        urllib.request.Request(base + "/api/v1/workflows?limit=100", headers=h), timeout=60))

    failed = 0
    for w in data.get("data", []):
        try:
            check(w["nodes"], w["name"])
            print("  ok    %s" % w["name"])
        except LayoutError as ex:
            failed += 1
            print("  FAIL  %s" % str(ex).split(" is not readable:\n    ", 1)[0])
            for line in str(ex).split("\n")[1:]:
                print("       %s" % line.strip())

    print("\n%d of %d workflows are readable."
          % (len(data.get("data", [])) - failed, len(data.get("data", []))))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
