# -*- coding: utf-8 -*-
"""Homies outbound debt follow-up - grounded in the four sample call transcripts."""
import io, json

RESIDENT = ("#2f9e44", "#b2f2bb")
AGENT    = ("#1971c2", "#d0ebff")
PERSON   = ("#f08c00", "#ffec99")
DECIDE   = ("#1971c2", "#a5d8ff")
TERM     = ("#1971c2", "#e7f5ff")
INK      = "#1e1e1e"
MUTED    = "#868e96"
HEAD     = "#1971c2"

BOX_W  = 280
SIDE_W = 230
DIA_W  = 270
DIA_H  = 124
PITCH  = 540
LEFT   = 400
LANE   = LEFT + BOX_W / 2.0 - 330
EDGE   = LANE - SIDE_W / 2.0
C1     = LEFT + BOX_W / 2.0
C2     = C1 + PITCH
C3     = C2 + PITCH
G12    = (C1 + C2) / 2.0
BUS    = C3 - 300
HEAD_Y = 92
TOP    = 138
GAP    = 62
LH     = 1.25
EM     = 0.53

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


def label(x, y, s, size=12, color=INK):
    w = max(8, int(len(s) * size * EM))
    _base("text", x, y, w, int(size * LH), color, "transparent",
          text=s, fontSize=size, fontFamily=2, textAlign="left",
          verticalAlign="top", containerId=None, originalText=s,
          lineHeight=LH, baseline=int(size * 0.9), boundElements=None)
    return w


def centred(cx, y, s, size=12, color=INK):
    w = max(8, int(len(s) * size * EM))
    label(cx - w / 2.0, y, s, size, color)


def node(kind, cx, y, lines, colors, w=BOX_W, h=None, size=12):
    body = "\n".join(lines)
    if h is None:
        h = int(len(lines) * size * LH) + 26
    x = cx - w / 2.0
    tid = _id("t")
    shape = _base(kind, x, y, w, h, colors[0], colors[1], eid=_id("n"),
                  roundness={"type": 3} if kind == "rectangle" else None,
                  boundElements=[{"type": "text", "id": tid}])
    tw = max(8, int(max(len(s) for s in lines) * size * EM))
    th = int(len(lines) * size * LH)
    _base("text", cx - tw / 2.0, y + (h - th) / 2.0, tw, th, INK, "transparent",
          eid=tid, text=body, fontSize=size, fontFamily=2, textAlign="center",
          verticalAlign="middle", containerId=shape["id"], originalText=body,
          lineHeight=LH, baseline=int(size * 0.9), boundElements=None)
    return {"id": shape["id"], "cx": cx, "top": y, "bottom": y + h,
            "left": x, "right": x + w, "mid": y + h / 2.0}


def connector(cx, y, letter):
    return node("ellipse", cx, y, [letter], TERM, w=48, h=48, size=17)


def _bind(eid, aid):
    for e in els:
        if e["id"] == eid:
            if e.get("boundElements") is None:
                e["boundElements"] = []
            e["boundElements"].append({"id": aid, "type": "arrow"})


def link(a, b, pts=None, text=None, tx=None, ty=None, head=True):
    aid = _id("a")
    if pts is None:
        pts = [(a["cx"], a["bottom"] + 4), (b["cx"], b["top"] - 4)]
    ox, oy = pts[0]
    rel = [[float(px - ox), float(py - oy)] for px, py in pts]
    xs = [p[0] for p in rel]
    ys = [p[1] for p in rel]
    _base("arrow", ox, oy, max(xs) - min(xs), max(ys) - min(ys),
          "#495057", "transparent", eid=aid, points=rel,
          lastCommittedPoint=None,
          startBinding={"elementId": a["id"], "focus": 0, "gap": 4} if a else None,
          endBinding={"elementId": b["id"], "focus": 0, "gap": 4} if b else None,
          startArrowhead=None, endArrowhead="arrow" if head else None,
          boundElements=None, roundness={"type": 2})
    if a:
        _bind(a["id"], aid)
    if b:
        _bind(b["id"], aid)
    if text:
        centred(tx if tx is not None else (pts[0][0] + pts[-1][0]) / 2.0,
                ty if ty is not None else (pts[0][1] + pts[-1][1]) / 2.0 - 8,
                text, 11, MUTED)


def spine(x, y0, y1):
    _base("line", x, y0, 0, y1 - y0, "#495057", "transparent",
          points=[[0.0, 0.0], [0.0, float(y1 - y0)]], lastCommittedPoint=None,
          startBinding=None, endBinding=None, startArrowhead=None,
          endArrowhead=None, boundElements=None)


def feed(box, trigger):
    """Horizontal arrow from the bus into a stacked outcome box."""
    link(None, box, pts=[(BUS, box["mid"]), (box["left"] - 4, box["mid"])])
    label(BUS + 12, box["mid"] - 20, trigger, 11, MUTED)


# =======================================================================
label(EDGE, 4, "Homies  \u00b7  chasing an unpaid month", 24)
label(EDGE, 38,
      "The agent makes the follow-up call. It never takes a payment on the line, "
      "and never discusses a debt with anyone but the account holder.", 13, MUTED)

for cx, t in [(C1, "Before it dials"),
              (C2, "The call"),
              (C3, "How it ends")]:
    centred(cx, HEAD_Y, t, 15, HEAD)

# ---------------------------------------------------------------- col 1
y = TOP
start = node("rectangle", C1, y, ["Every morning"], TERM, w=190, h=46)
y = start["bottom"] + GAP

n1 = node("rectangle", C1, y, ["[System]", "Lists every apartment with", "a month still unpaid"], AGENT)
link(start, n1)
y = n1["bottom"] + GAP

d1 = node("diamond", C1, y, ["Has the handover", "protocol been", "signed?"], DECIDE, w=DIA_W, h=DIA_H)
link(n1, d1)
y = d1["bottom"] + GAP

n2 = node("rectangle", C1, y, ["[System]", "Skips standing orders,", "anyone called in the last", "few days, and anything", "outside legal calling hours"], AGENT)
link(d1, n2, text="Yes", tx=C1 + 16, ty=d1["bottom"] + 16)

s1 = node("rectangle", LANE, d1["mid"] - 33, ["Nothing is owed yet.", "No call is made."], TERM, w=SIDE_W)
link(d1, s1, pts=[(d1["left"] - 4, d1["mid"]), (s1["right"] + 4, s1["mid"])],
     text="No", tx=(d1["left"] + s1["right"]) / 2.0, ty=d1["mid"] - 22)

y = n2["bottom"] + GAP
a_out = connector(C1, y, "A")
link(n2, a_out)

# ---------------------------------------------------------------- col 2
y = TOP
a_in = connector(C2, y, "A")
y = a_in["bottom"] + GAP

m1 = node("rectangle", C2, y, ["[Agent]", "Says who it is and which", "building it manages"], AGENT)
link(a_in, m1)
y = m1["bottom"] + GAP

d2 = node("diamond", C2, y, ["Did the account", "holder answer?"], DECIDE, w=DIA_W, h=DIA_H)
link(m1, d2)
y = d2["bottom"] + GAP

m2 = node("rectangle", C2, y, ["[Agent]", "Names the month that is", "unpaid and the amount"], AGENT)
link(d2, m2, text="Yes", tx=C2 + 16, ty=d2["bottom"] + 16)
y = m2["bottom"] + GAP

b_out = connector(C2, y, "B")
link(m2, b_out)

# no-answer / wrong-person chain, left channel
s2 = node("rectangle", G12, d2["mid"] - 46, ["[Agent]", "Leaves a short message,", "or asks for a call back.", "No amount, no details."], AGENT, w=SIDE_W)
link(d2, s2, pts=[(d2["left"] - 4, d2["mid"]), (s2["right"] + 4, s2["mid"])],
     text="No", tx=(d2["left"] + s2["right"]) / 2.0, ty=d2["mid"] - 22)

s3 = node("rectangle", G12, s2["bottom"] + GAP, ["[Agent]", "Logs the attempt. After", "four, a person takes it on."], PERSON, w=SIDE_W)
link(s2, s3)

s4 = node("rectangle", G12, s3["bottom"] + GAP, ["Passed to a person"], TERM, w=SIDE_W, h=46)
link(s3, s4)

# ---------------------------------------------------------------- col 3
y = TOP
b_in = connector(C3, y, "B")
y = b_in["bottom"] + GAP

k0 = node("rectangle", C3, y, ["[Resident]", "Says what they intend to do"], RESIDENT)
link(b_in, k0)
y = k0["bottom"] + 74

o1 = node("rectangle", C3, y, ["[Agent]", "Sends a payment link by text.", "Logs a promise, with the", "date they gave."], AGENT)
y = o1["bottom"] + GAP
o2 = node("rectangle", C3, y, ["[Agent]", "Sends the standing-order", "form. Flags it for a person", "to finish."], AGENT)
y = o2["bottom"] + GAP
o3 = node("rectangle", C3, y, ["[Agent]", "Does not argue. Opens a", "task and passes it", "to a person."], PERSON)

link(k0, None, pts=[(k0["cx"], k0["bottom"] + 4),
                    (k0["cx"], k0["bottom"] + 34),
                    (BUS, k0["bottom"] + 34)], head=False)
spine(BUS, k0["bottom"] + 34, o3["mid"])
feed(o1, "agrees to pay")
feed(o2, "wants a standing order")
feed(o3, "disputes it, or refuses")

# ---------------------------------------------------------------- band
BAND_Y = max(a_out["bottom"], s4["bottom"], o3["bottom"]) + 92
BAND_R = C3 + BOX_W / 2.0
_base("rectangle", EDGE, BAND_Y, BAND_R - EDGE, 112, "#e03131", "#fff5f5",
      roundness={"type": 3}, strokeStyle="dashed", boundElements=None)
label(EDGE + 22, BAND_Y + 16, "WHAT THE AGENT NEVER DOES", 12, "#e03131")
label(EDGE + 22, BAND_Y + 42,
      "Take card details or charge a card on the call  \u00b7  discuss a debt with anyone "
      "but the account holder  \u00b7  argue, press, or negotiate", 13)
label(EDGE + 22, BAND_Y + 68,
      "Decide that a formal warning is due - three months unpaid is a person's call. "
      "Every attempt is recorded, including the ones nobody answered.", 13, MUTED)

KY = BAND_Y + 150
label(EDGE, KY + 4, "WHO IS ACTING", 11, MUTED)
kx = EDGE + 120
for colors, txt in [(RESIDENT, "the resident"), (AGENT, "the agent or the system"),
                    (PERSON, "goes to a person")]:
    _base("rectangle", kx, KY, 26, 15, colors[0], colors[1],
          roundness={"type": 3}, boundElements=None)
    kx += 34 + label(kx + 34, KY + 1, txt, 12) + 34

doc = {"type": "excalidraw", "version": 2, "source": "https://excalidraw.com",
       "elements": els,
       "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
       "files": {}}

out = r"c:\Users\Acer nitro 5\Desktop\Homie\docs\diagrams\Homies-Debt-Followup-Flow.excalidraw"
with io.open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=1)

print("wrote %s" % out)
print("elements: %d" % len(els))
