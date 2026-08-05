# -*- coding: utf-8 -*-
import json, io
from collections import Counter

p = r"c:\Users\Acer nitro 5\Desktop\Homie\docs\diagrams\Homies-Call-Flow.excalidraw"
d = json.load(io.open(p, encoding="utf-8"))
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
        return e["text"].replace("\n", " / ")[:34]
    t = e.get("boundElements") or []
    for b in t:
        if b.get("type") == "text" and b["id"] in by_id:
            return by_id[b["id"]]["text"].replace("\n", " / ")[:34]
    return "%s@%.0f,%.0f" % (e["type"], e["x"], e["y"])


print("elements:", len(els), dict(Counter(e["type"] for e in els)))

# --- shape on shape (the band is a deliberate container, skip it) -------
shapes = [e for e in els if e["type"] in SHAPES]
band = max(shapes, key=lambda e: e["width"])
shapes = [e for e in shapes if e is not band]
clash = [(name(a), name(b))
         for i, a in enumerate(shapes) for b in shapes[i + 1:] if hit(a, b)]
print("shape-on-shape overlaps:", len(clash))
for a, b in clash[:12]:
    print("   %r  X  %r" % (a, b))

# --- free text on free text / on shapes --------------------------------
free = [e for e in els if e["type"] == "text" and not e.get("containerId")]
tt = [(name(a), name(b))
      for i, a in enumerate(free) for b in free[i + 1:] if hit(a, b)]
print("label-on-label overlaps:", len(tt))
for a, b in tt[:12]:
    print("   %r  X  %r" % (a, b))

ts = [(name(a), name(b)) for a in free for b in shapes if hit(a, b)]
print("label-on-shape overlaps:", len(ts))
for a, b in ts[:12]:
    print("   %r  X  %r" % (a, b))

# --- bound text must fit its container ---------------------------------
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
for a, b in bad_fit[:12]:
    print("   %r  ->  %s" % (a, b))

# --- structural --------------------------------------------------------
req = {"id", "type", "x", "y", "width", "height", "strokeColor", "seed",
       "versionNonce", "isDeleted", "locked"}
print("missing keys:", [e["id"] for e in els if not req.issubset(e.keys())] or "none")
print("unique ids:", len({e["id"] for e in els}) == len(els))

dangling = []
for e in els:
    if e["type"] == "arrow":
        for k in ("startBinding", "endBinding"):
            b = e.get(k)
            if b and b["elementId"] not in by_id:
                dangling.append((e["id"], k))
print("dangling arrow bindings:", dangling or "none")

xs = [e["x"] for e in els]
ys = [e["y"] for e in els]
print("bounds x %.0f..%.0f  y %.0f..%.0f"
      % (min(xs), max(e["x"] + e["width"] for e in els),
         min(ys), max(e["y"] + e["height"] for e in els)))

ok = not clash and not tt and not ts and not bad_fit and not dangling
print("\nRESULT:", "CLEAN" if ok else "PROBLEMS REMAIN")
