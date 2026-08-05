# -*- coding: utf-8 -*-
"""Homies voice agent - what happens when a resident calls. Client-facing."""
import io, json

# --- palette -----------------------------------------------------------
RESIDENT = ("#2f9e44", "#b2f2bb")   # the person speaking
AGENT    = ("#1971c2", "#d0ebff")   # the agent
PERSON   = ("#f08c00", "#ffec99")   # goes to a human
DECIDE   = ("#1971c2", "#a5d8ff")   # decision
TERM     = ("#1971c2", "#e7f5ff")   # start / end
INK      = "#1e1e1e"
MUTED    = "#868e96"
HEAD     = "#1971c2"

# --- geometry ----------------------------------------------------------
BOX_W   = 280
SIDE_W  = 220
DIA_W   = 260
DIA_H   = 120
PITCH   = 520
LEFT    = 380
LANE    = LEFT + BOX_W / 2.0 - 320    # side lane for column 1's branches
EDGE    = LANE - SIDE_W / 2.0         # left-most ink
C1      = LEFT + BOX_W / 2.0
C2      = C1 + PITCH
C3      = C2 + PITCH
G12     = (C1 + C2) / 2.0
G23     = (C2 + C3) / 2.0
FAR     = C3 + 400
HEAD_Y  = 92
TOP     = 138
LH      = 1.25
EM      = 0.53

_n = [0]
els = []


def _id(p):
    _n[0] += 1
    return "%s%d" % (p, _n[0])


def _base(kind, x, y, w, h, stroke, bg, eid=None, **kw):
    i = _n[0] + 1
    _n[0] = i
    e = {"id": eid or ("el%d" % i), "type": kind,
         "x": float(x), "y": float(y), "width": float(w), "height": float(h),
         "angle": 0, "strokeColor": stroke, "backgroundColor": bg,
         "fillStyle": "solid", "strokeWidth": 1.5, "strokeStyle": "solid",
         "roughness": 0, "opacity": 100, "groupIds": [], "frameId": None,
         "roundness": None, "seed": 100003 + i * 7919, "version": 1,
         "versionNonce": 200003 + i * 104729, "isDeleted": False,
         "boundElements": [], "updated": 1, "link": None, "locked": False}
    e.update(kw)
    els.append(e)
    return e


def label(x, y, s, size=12, color=INK, align="left"):
    w = max(8, int(len(s) * size * EM))
    _base("text", x, y, w, int(size * LH), color, "transparent",
          text=s, fontSize=size, fontFamily=2, textAlign=align,
          verticalAlign="top", containerId=None, originalText=s,
          lineHeight=LH, baseline=int(size * 0.9), boundElements=None)
    return w


def centred(cx, y, s, size=12, color=INK):
    w = max(8, int(len(s) * size * EM))
    label(cx - w / 2.0, y, s, size, color)


def node(kind, cx, y, lines, colors, w=BOX_W, h=None, size=12, dashed=False):
    """Box (or diamond/ellipse) with bound, centred, multi-line text."""
    body = "\n".join(lines)
    if h is None:
        h = int(len(lines) * size * LH) + 26
    x = cx - w / 2.0
    tid = _id("t")
    shape = _base(kind, x, y, w, h, colors[0], colors[1],
                  eid=_id("n"),
                  roundness={"type": 3} if kind == "rectangle" else None,
                  strokeStyle="dashed" if dashed else "solid",
                  boundElements=[{"type": "text", "id": tid}])
    tw = max(8, int(max(len(s) for s in lines) * size * EM))
    th = int(len(lines) * size * LH)
    _base("text", cx - tw / 2.0, y + (h - th) / 2.0, tw, th, INK, "transparent",
          eid=tid, text=body, fontSize=size, fontFamily=2,
          textAlign="center", verticalAlign="middle", containerId=shape["id"],
          originalText=body, lineHeight=LH, baseline=int(size * 0.9),
          boundElements=None)
    return {"id": shape["id"], "cx": cx, "top": y, "bottom": y + h,
            "left": x, "right": x + w, "mid": y + h / 2.0}


def connector(cx, y, letter):
    n = node("ellipse", cx, y, [letter], TERM, w=48, h=48, size=17)
    return n


def _bind(a, b, aid):
    for e in els:
        if e["id"] in (a, b):
            if e.get("boundElements") is None:
                e["boundElements"] = []
            e["boundElements"].append({"id": aid, "type": "arrow"})


def link(a, b, pts=None, text=None, tx=None, ty=None, dashed=False):
    """Arrow from node a to node b. pts = absolute waypoints, else vertical."""
    aid = _id("a")
    if pts is None:
        x0, y0 = a["cx"], a["bottom"] + 4
        x1, y1 = b["cx"], b["top"] - 4
        pts = [(x0, y0), (x1, y1)]
    ox, oy = pts[0]
    rel = [[float(px - ox), float(py - oy)] for px, py in pts]
    xs = [p[0] for p in rel]
    ys = [p[1] for p in rel]
    _base("arrow", ox, oy, max(xs) - min(xs), max(ys) - min(ys),
          "#495057", "transparent", eid=aid,
          strokeStyle="dashed" if dashed else "solid",
          points=rel, lastCommittedPoint=None,
          startBinding={"elementId": a["id"], "focus": 0, "gap": 4},
          endBinding={"elementId": b["id"], "focus": 0, "gap": 4},
          startArrowhead=None, endArrowhead="arrow", boundElements=None,
          roundness={"type": 2})
    _bind(a["id"], b["id"], aid)
    if text:
        centred(tx if tx is not None else (pts[0][0] + pts[-1][0]) / 2.0,
                ty if ty is not None else (pts[0][1] + pts[-1][1]) / 2.0 - 8,
                text, 11, MUTED)


GAP = 62   # vertical space between stacked nodes

# =======================================================================
# column headers
# =======================================================================
for cx, t in [(C1, "Calling in"),
              (C2, "Opening a request"),
              (C3, "Checking a request  (any time)")]:
    centred(cx, HEAD_Y, t, 15, HEAD)

# =======================================================================
# column 1 - calling in
# =======================================================================
y = TOP
start = node("rectangle", C1, y, ["Start"], TERM, w=150, h=46)
y = start["bottom"] + GAP

n1 = node("rectangle", C1, y, ["[Resident]", "Calls the office number"], RESIDENT)
link(start, n1)
y = n1["bottom"] + GAP

n2 = node("rectangle", C1, y, ["[Agent]", "Greets and says", "what it can help with"], AGENT)
link(n1, n2)
y = n2["bottom"] + GAP

n3 = node("rectangle", C1, y, ["[Agent]", "Asks the building,", "then the apartment,", "then the name"], AGENT)
link(n2, n3)
y = n3["bottom"] + GAP

d1 = node("diamond", C1, y, ["Do we know", "this resident?"], DECIDE, w=DIA_W, h=DIA_H)
link(n3, d1)
y = d1["bottom"] + GAP

n4 = node("rectangle", C1, y, ["[Agent]", "Reads the details", "back to confirm"], AGENT)
link(d1, n4, text="Yes", tx=C1 + 16, ty=d1["bottom"] + 16)

# the "no" branch gets its own lane to the left
s1 = node("rectangle", LANE, d1["mid"] - 40, ["[Agent]", "Takes the details", "anyway - a request", "is still opened"], AGENT, w=SIDE_W)
link(d1, s1, pts=[(d1["left"] - 4, d1["mid"]), (s1["right"] + 4, s1["mid"])],
     text="No", tx=(d1["left"] + s1["right"]) / 2.0, ty=d1["mid"] - 22)

# anytime jump across to the status flow
c_out = connector(LANE, n4["bottom"] + 2, "C")
link(n4, c_out, pts=[(n4["left"] - 4, n4["mid"]),
                     (c_out["cx"], n4["mid"]),
                     (c_out["cx"], c_out["top"] - 4)],
     text="any time", tx=(c_out["cx"] + n4["left"]) / 2.0, ty=n4["mid"] - 20,
     dashed=True)

y = n4["bottom"] + GAP + 40
a_out = connector(C1, y, "A")
link(n4, a_out)
# the no-branch rejoins, hugging the outside of the lane
link(s1, a_out, pts=[(s1["left"] + 20, s1["bottom"] + 4),
                     (s1["left"] + 20, a_out["mid"]),
                     (a_out["cx"] - 28, a_out["mid"])])

COL1_END = a_out["bottom"]

# =======================================================================
# column 2 - opening a request
# =======================================================================
y = TOP
a_in = connector(C2, y, "A")
y = a_in["bottom"] + GAP

m1 = node("rectangle", C2, y, ["[Resident]", "Says what is wrong"], RESIDENT)
link(a_in, m1)
y = m1["bottom"] + GAP

m2 = node("rectangle", C2, y, ["[Agent]", "Writes it down in the", "caller's own words"], AGENT)
link(m1, m2)
y = m2["bottom"] + GAP

d2 = node("diamond", C2, y, ["Clear enough", "to act on?"], DECIDE, w=DIA_W, h=DIA_H)
link(m2, d2)
y = d2["bottom"] + GAP

m3 = node("rectangle", C2, y, ["[Agent]", "Opens the request and reads", "back the reference number"], AGENT)
link(d2, m3, text="Yes", tx=C2 + 16, ty=d2["bottom"] + 16)
y = m3["bottom"] + GAP

d3 = node("diamond", C2, y, ["Anything", "wrong?"], DECIDE, w=DIA_W, h=DIA_H)
link(m3, d3)
y = d3["bottom"] + GAP

m4 = node("rectangle", C2, y, ["Request opened"], TERM, w=200, h=46)
link(d3, m4, text="No", tx=C2 + 16, ty=d3["bottom"] + 16)
COL2_END = m4["bottom"]

# --- retry chain, left gap ---------------------------------------------
s2 = node("rectangle", G12, d2["mid"] - 46, ["[Agent]", "Asks once more,", "worded differently", "(twice at most)"], AGENT, w=SIDE_W)
link(d2, s2, pts=[(d2["left"] - 4, d2["mid"]), (s2["right"] + 4, s2["mid"])],
     text="No", tx=(d2["left"] + s2["right"]) / 2.0, ty=d2["mid"] - 22)
link(s2, m1, pts=[(s2["cx"], s2["top"] - 4),
                  (s2["cx"], m1["mid"]),
                  (m1["left"] - 4, m1["mid"])])

s3 = node("rectangle", G12, s2["bottom"] + 84, ["[Agent]", "Saves what it has,", "with the recording,", "for a person"], PERSON, w=SIDE_W)
link(s2, s3, pts=[(s2["cx"], s2["bottom"] + 4), (s3["cx"], s3["top"] - 4)],
     text="still no", tx=G12 + 34, ty=s2["bottom"] + 30)

s3end = node("rectangle", G12, s3["bottom"] + GAP, ["Flagged for a person"], TERM, w=SIDE_W, h=46)
link(s3, s3end)

# --- correction loop, right gap ----------------------------------------
s4 = node("rectangle", G23, d3["mid"] - 46, ["[Resident]", "Corrects it - the", "same request is", "updated"], RESIDENT, w=SIDE_W)
link(d3, s4, pts=[(d3["right"] + 4, d3["mid"]), (s4["left"] - 4, s4["mid"])],
     text="Yes", tx=(d3["right"] + s4["left"]) / 2.0, ty=d3["mid"] - 22)
link(s4, m3, pts=[(s4["cx"], s4["top"] - 4),
                  (s4["cx"], m3["mid"]),
                  (m3["right"] + 4, m3["mid"])])

# =======================================================================
# column 3 - checking a request
# =======================================================================
y = TOP
c_in = connector(C3, y, "C")
y = c_in["bottom"] + GAP

k1 = node("rectangle", C3, y, ["[Resident]", "Asks about a request"], RESIDENT)
link(c_in, k1)
y = k1["bottom"] + GAP

k2 = node("rectangle", C3, y, ["[Agent]", "Looks it up by reference,", "or by building and apartment"], AGENT)
link(k1, k2)
y = k2["bottom"] + GAP

d4 = node("diamond", C3, y, ["Is it one the", "agent took?"], DECIDE, w=DIA_W, h=DIA_H)
link(k2, d4)
y = d4["bottom"] + GAP

k4 = node("rectangle", C3, y, ["[Agent]", "Says where it stands -", "never gives a", "completion date"], AGENT)
link(d4, k4, text="Yes", tx=C3 + 16, ty=d4["bottom"] + 16)
y = k4["bottom"] + GAP

k5 = node("rectangle", C3, y, ["Answer given"], TERM, w=200, h=46)
link(k4, k5)
COL3_END = k5["bottom"]

k3 = node("rectangle", FAR, d4["mid"] - 46, ["[Agent]", "Says it only sees", "requests it took", "itself, and offers", "a person"], AGENT, w=SIDE_W)
link(d4, k3, pts=[(d4["right"] + 4, d4["mid"]), (k3["left"] - 4, k3["mid"])],
     text="No", tx=(d4["right"] + k3["left"]) / 2.0, ty=d4["mid"] - 22)
link(k3, k5, pts=[(k3["cx"], k3["bottom"] + 4),
                  (k3["cx"], k5["mid"]),
                  (k5["right"] + 4, k5["mid"])])

# =======================================================================
# at-any-moment band
# =======================================================================
BAND_Y = max(COL1_END, COL2_END, COL3_END, s3end["bottom"]) + 90
BAND_R = FAR + SIDE_W / 2.0
_base("rectangle", EDGE, BAND_Y, BAND_R - EDGE, 108, "#f08c00", "#fff9db",
      roundness={"type": 3}, strokeStyle="dashed", boundElements=None)
label(EDGE + 22, BAND_Y + 16, "AT ANY MOMENT", 12, "#f08c00")
label(EDGE + 22, BAND_Y + 42,
      "An emergency  \u00b7  a question outside what it handles  \u00b7  the caller asks for a person  "
      "\u00b7  two attempts that did not work", 13)
label(LEFT + 22, BAND_Y + 68,
      "The agent explains what it is doing and passes the call to a person, "
      "carrying everything it has captured so far.", 13, MUTED)

# =======================================================================
# key
# =======================================================================
KY = BAND_Y + 146
label(EDGE, KY + 4, "WHO IS ACTING", 11, MUTED)
kx = EDGE + 120
for colors, txt in [(RESIDENT, "the resident"), (AGENT, "the agent"), (PERSON, "goes to a person")]:
    _base("rectangle", kx, KY, 26, 15, colors[0], colors[1],
          roundness={"type": 3}, boundElements=None)
    kx += 34 + label(kx + 34, KY + 1, txt, 12) + 34

TITLE = "Homies  \u00b7  what happens when a resident calls"
label(EDGE, 4, TITLE, 24)
label(EDGE, 4 + 34, "The agent takes the intake call. Anything needing judgment goes to a person.",
      13, MUTED)

# =======================================================================
doc = {"type": "excalidraw", "version": 2, "source": "https://excalidraw.com",
       "elements": els,
       "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
       "files": {}}

out = r"c:\Users\Acer nitro 5\Desktop\Homie\docs\diagrams\Homies-Call-Flow.excalidraw"
with io.open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=1)

print("wrote %s" % out)
print("elements: %d" % len(els))
