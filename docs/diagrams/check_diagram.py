# -*- coding: utf-8 -*-
"""Overlap and structure check for any generated .excalidraw file.

    python docs/diagrams/check_diagram.py Homies-System-Flow.excalidraw

Layout bugs in a generated diagram are invisible until someone opens it, and by
then it has usually been sent to a client. This catches the three that actually
happen: shapes sitting on top of each other, labels colliding, and bound text
wider than the box holding it.

Shapes wider than CONTAINER are treated as deliberate panels - the brain bar,
the handover band, the key matrix - and excluded, since everything inside them
overlaps them by design.
"""
import io, json, os, sys
from collections import Counter

# Node labels contain arrows and bullets; the Windows console is cp1252.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONTAINER = 600
HERE = os.path.dirname(os.path.abspath(__file__))

arg = sys.argv[1] if len(sys.argv) > 1 else "Homies-System-Flow.excalidraw"
path = arg if os.path.isabs(arg) else os.path.join(HERE, arg)

d = json.load(io.open(path, encoding="utf-8"))
els = d["elements"]
by_id = {e["id"]: e for e in els}
SHAPES = ("rectangle", "diamond", "ellipse")


def box(e):
    return (e["x"], e["y"], e["x"] + e["width"], e["y"] + e["height"])


def hit(a, b, pad=0):
    ax0, ay0, ax1, ay1 = box(a)
    bx0, by0, bx1, by1 = box(b)
    return not (ax1 + pad <= bx0 or bx1 + pad <= ax0
                or ay1 + pad <= by0 or by1 + pad <= ay0)


def name(e):
    if e["type"] == "text":
        return e["text"].replace("\n", " / ")[:40]
    for b in (e.get("boundElements") or []):
        if b.get("type") == "text" and b["id"] in by_id:
            return by_id[b["id"]]["text"].replace("\n", " / ")[:40]
    return "%s@%.0f,%.0f" % (e["type"], e["x"], e["y"])


print(os.path.basename(path))
print("elements:", len(els), dict(Counter(e["type"] for e in els)))

shapes = [e for e in els if e["type"] in SHAPES and e["width"] <= CONTAINER]
panels = [e for e in els if e["type"] in SHAPES and e["width"] > CONTAINER]
print("panels excluded:", len(panels))

clash = [(name(a), name(b))
         for i, a in enumerate(shapes) for b in shapes[i + 1:] if hit(a, b)]
print("shape-on-shape overlaps:", len(clash))
for a, b in clash[:15]:
    print("   %r  X  %r" % (a, b))

free = [e for e in els if e["type"] == "text" and not e.get("containerId")]
tt = [(name(a), name(b))
      for i, a in enumerate(free) for b in free[i + 1:] if hit(a, b)]
print("label-on-label overlaps:", len(tt))
for a, b in tt[:15]:
    print("   %r  X  %r" % (a, b))

ts = [(name(a), name(b)) for a in free for b in shapes if hit(a, b)]
print("label-on-shape overlaps:", len(ts))
for a, b in ts[:15]:
    print("   %r  X  %r" % (a, b))

bad_fit = []
for e in els:
    if e["type"] == "text" and e.get("containerId"):
        c = by_id.get(e["containerId"])
        if not c:
            bad_fit.append((name(e), "MISSING CONTAINER"))
        elif e["width"] > c["width"] - 12 or e["height"] > c["height"] - 8:
            bad_fit.append((name(e), "%.0fx%.0f in %.0fx%.0f"
                            % (e["width"], e["height"], c["width"], c["height"])))
print("bound text overflowing:", len(bad_fit))
for a, b in bad_fit[:15]:
    print("   %r  ->  %s" % (a, b))

dangling = []
for e in els:
    if e["type"] == "arrow":
        for k in ("startBinding", "endBinding"):
            b = e.get(k)
            if b and b["elementId"] not in by_id:
                dangling.append((e["id"], k))
print("dangling arrow bindings:", dangling or "none")
print("unique ids:", len({e["id"] for e in els}) == len(els))
print("bounds x %.0f..%.0f  y %.0f..%.0f"
      % (min(e["x"] for e in els), max(e["x"] + e["width"] for e in els),
         min(e["y"] for e in els), max(e["y"] + e["height"] for e in els)))

ok = not (clash or tt or ts or bad_fit or dangling)
print("\nRESULT:", "CLEAN" if ok else "PROBLEMS REMAIN")
sys.exit(0 if ok else 1)
