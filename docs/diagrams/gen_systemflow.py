# -*- coding: utf-8 -*-
"""Homies - the whole PRD as one flow.

Every flow in Homies-PRD-v2.md, drawn end to end: the two front doors, the
brain, the six flows, and the four places anything can be written.

Colour encodes *which system is touched*, not who is talking, because that is
the question the diagram has to answer. A violet box is an Ox API call. A cyan
box is a Supabase write. Orange leaves the machine and lands on a person.

Reflects the OXS API discovery of 4 Aug, which the PRD does not yet: service
requests are writable, debts and general info are readable, and there is no
payment-method module at all. Sections marked with a delta are where the
written PRD is now out of date.
"""
import io, json

# --- palette -----------------------------------------------------------
RESIDENT = ("#2f9e44", "#b2f2bb")   # the person speaking
AGENT    = ("#1971c2", "#d0ebff")   # the agent, working on its own
OX       = ("#6741d9", "#e5dbff")   # touches the OXS API
DATA     = ("#0c8599", "#c5f6fa")   # written to Supabase
PERSON   = ("#f08c00", "#ffec99")   # leaves the machine - staff or Monday
GATE     = ("#e03131", "#ffe3e3")   # hard gate, refuses rather than degrades
DECIDE   = ("#1971c2", "#a5d8ff")
TERM     = ("#1971c2", "#e7f5ff")
INK      = "#1e1e1e"
MUTED    = "#868e96"
HEAD     = "#1971c2"
DELTA    = "#c2255c"                # changed by the Ox API discovery

# --- geometry ----------------------------------------------------------
BOX_W  = 300
PILL_W = 210
PITCH  = 540          # BOX_W + PILL_W + two 20px gutters, so pills never collide
EDGE   = 80
LH     = 1.25
EM     = 0.53
GAP    = 52

COLS = 6
CX   = [EDGE + BOX_W / 2.0 + i * PITCH for i in range(COLS)]
# The last column's exit pills sit in open space to its right, so the full-width
# bands have to reach past them or the page ends up visibly ragged.
RIGHT = CX[-1] + BOX_W / 2.0 + 20 + PILL_W + 20
WIDE  = RIGHT - EDGE

_n = [0]
els = []


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


def _id(p):
    _n[0] += 1
    return "%s%d" % (p, _n[0])


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


def node(kind, cx, y, lines, colors, w=BOX_W, h=None, size=12, dashed=False):
    body = "\n".join(lines)
    if h is None:
        h = int(len(lines) * size * LH) + 26
    x = cx - w / 2.0
    tid = _id("t")
    shape = _base(kind, x, y, w, h, colors[0], colors[1], eid=_id("n"),
                  roundness={"type": 3} if kind == "rectangle" else None,
                  strokeStyle="dashed" if dashed else "solid",
                  boundElements=[{"type": "text", "id": tid}])
    tw = max(8, int(max(len(s) for s in lines) * size * EM))
    th = int(len(lines) * size * LH)
    _base("text", cx - tw / 2.0, y + (h - th) / 2.0, tw, th, INK, "transparent",
          eid=tid, text=body, fontSize=size, fontFamily=2, textAlign="center",
          verticalAlign="middle", containerId=shape["id"], originalText=body,
          lineHeight=LH, baseline=int(size * 0.9), boundElements=None)
    return {"id": shape["id"], "cx": cx, "top": y, "bottom": y + h,
            "left": x, "right": x + w, "mid": y + h / 2.0}


def _bind(a, b, aid):
    for e in els:
        if e["id"] in (a, b):
            if e.get("boundElements") is None:
                e["boundElements"] = []
            e["boundElements"].append({"id": aid, "type": "arrow"})


def link(a, b, pts=None, text=None, tx=None, ty=None, dashed=False):
    aid = _id("a")
    if pts is None:
        pts = [(a["cx"], a["bottom"] + 4), (b["cx"], b["top"] - 4)]
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


def exits(anchor, lines):
    """A dashed pill in the gutter: this step can leave for a person.

    Drawn unattached on purpose. Six columns of escalation arrows converging on
    one band at the bottom is unreadable; a consistent pill shape reads as one
    rule applied everywhere, which is what section 7 actually is.
    """
    node("rectangle", anchor["right"] + 20 + PILL_W / 2.0, anchor["mid"] - 26,
         lines, PERSON, w=PILL_W, size=11, dashed=True)


# =======================================================================
# title
# =======================================================================
label(EDGE, 4, "Homies  \u00b7  the whole system, end to end", 26)
label(EDGE, 44, "Every flow in PRD v2, with the OXS API discovery of 4 Aug folded in. "
                "Colour says which system is touched.", 14, MUTED)
label(EDGE, 68, "Pink notes mark where the written PRD is now out of date.", 13, DELTA)

# =======================================================================
# the spine
# =======================================================================
SPINE_Y = 128
label(EDGE, SPINE_Y - 26, "THE TWO FRONT DOORS", 12, HEAD)

sp_w, sp_h, sp_p = 210, 60, 244


def chain(y, items, colors):
    made = []
    for i, lines in enumerate(items):
        n = node("rectangle", EDGE + sp_w / 2.0 + i * sp_p, y, lines, colors,
                 w=sp_w, h=sp_h, size=12)
        if made:
            link(made[-1], n, pts=[(made[-1]["right"] + 4, made[-1]["mid"]),
                                   (n["left"] - 4, n["mid"])])
        made.append(n)
    return made

voice = chain(SPINE_Y, [["[Resident]", "picks up the phone"],
                        ["Telnyx", "+972 number, SIP"],
                        ["Vapi", "Azure he-IL STT + TTS"]], RESIDENT)
chat = chain(SPINE_Y + 92, [["[Resident]", "sends a message"],
                            ["Meta Cloud API", "WhatsApp"],
                            ["Chatwoot", "agent inbox"]], RESIDENT)

BRAIN_Y = SPINE_Y + 190
brain = node("rectangle", EDGE + WIDE / 2.0, BRAIN_Y,
             ["n8n  \u00b7  the brain",
              "twelve channel-agnostic tools  \u00b7  the same webhooks serve voice and chat"],
             AGENT, w=WIDE, h=76, size=14)
link(voice[-1], brain, pts=[(voice[-1]["cx"], voice[-1]["bottom"] + 4),
                            (voice[-1]["cx"], brain["top"] - 4)])
link(chat[-1], brain, pts=[(chat[-1]["cx"], chat[-1]["bottom"] + 4),
                           (chat[-1]["cx"], brain["top"] - 4)])

# --- the Ox key matrix, in the space beside the front doors ------------
KX = EDGE + 3 * sp_p + 20
_base("rectangle", KX, SPINE_Y - 8, 1400, 160, "#6741d9", "#f8f0ff",
      roundness={"type": 3}, boundElements=None)
label(KX + 22, SPINE_Y + 8, "OXS API  \u00b7  THREE SCOPED KEYS", 13, "#6741d9")
label(KX + 22, SPINE_Y + 34,
      "One key per module, one access level per key. A key that pulls debts cannot "
      "open or delete a service request.", 12, MUTED)
for i, (mod, lvl, what) in enumerate([
        ("service requests", "FULL CONTROL", "view \u00b7 open \u00b7 update \u00b7 delete"),
        ("resident debts", "read only", "debts and balances"),
        ("general info", "read only", "buildings \u00b7 apartments \u00b7 residents \u00b7 payment history")]):
    ry = SPINE_Y + 62 + i * 26
    label(KX + 22, ry, mod, 12, INK)
    label(KX + 190, ry, lvl, 12, "#6741d9" if i == 0 else MUTED)
    label(KX + 320, ry, what, 12, MUTED)
label(KX + 22, SPINE_Y + 142,
      "No payment-method module exists. That is why 2.3 ends at a human, and why nothing "
      "here can ever charge anyone.", 12, DELTA)

# =======================================================================
# the six flows
# =======================================================================
TOP = BRAIN_Y + 150
label(EDGE, TOP - 58, "THE SIX FLOWS", 12, HEAD)

HEADS = [
    ("2.1  Open a request", "voice + WhatsApp"),
    ("2.2  Check a request", "live now, was nightly"),
    ("2.3  Change payment details", "staff-confirmed"),
    ("2.4  Payment link", "OXS generates it"),
    ("2.5  Complaint ticket", "voice + WhatsApp"),
    ("3  Outbound debt follow-up", "R2  \u00b7  built, untooled"),
]
for i, (t, sub) in enumerate(HEADS):
    centred(CX[i], TOP - 30, t, 15, DELTA if i in (1, 2) else HEAD)
    centred(CX[i], TOP - 10, sub, 11, MUTED)

ends = []


def column(i, steps):
    """steps: list of (kind, colors, lines) or ('exit', reason-lines)."""
    y = TOP + 18
    prev = None
    for step in steps:
        if step[0] == "exit":
            exits(prev, step[1])
            continue
        kind, colors, lines = step
        h = 46 if kind == "term" else None
        n = node("rectangle" if kind != "diamond" else "diamond",
                 CX[i], y, lines, colors, h=h,
                 w=BOX_W if kind != "diamond" else 260)
        if prev:
            link(prev, n)
        prev = n
        y = n["bottom"] + GAP
    ends.append(prev)
    return prev


# --- 2.1 open a request -------------------------------------------------
column(0, [
    ("box", RESIDENT, ["[Resident]", "asks to open a request"]),
    ("box", OX, ["identify_resident", "READ general info", "phone \u2192 building + unit"]),
    ("box", AGENT, ["Captures type, description,", "building, unit, urgency"]),
    ("box", OX, ["open_request", "WRITE service requests", "the one write we have"]),
    ("box", AGENT, ["Reads back the OXS reference", "\u2014 a real one, not ours"]),
    ("exit", ["cannot capture it", "after two tries"]),
    ("box", DATA, ["log_call_outcome", "interactions + transcript"]),
    ("term", TERM, ["Request open in OXS"]),
])

# --- 2.2 check a request ------------------------------------------------
column(1, [
    ("box", RESIDENT, ["[Resident]", "asks about a request"]),
    ("box", OX, ["identify_resident", "READ general info"]),
    ("box", OX, ["get_request_status", "READ service requests", "live, not last night"]),
    ("diamond", DECIDE, ["Found?"]),
    ("box", AGENT, ["States the current status.", "No freshness caveat needed."]),
    ("exit", ["not found \u2192", "offer to open one", "falls through to 2.1"]),
    ("box", DATA, ["log_call_outcome"]),
    ("term", TERM, ["Answered"]),
])

# --- 2.3 change payment details -----------------------------------------
p3 = [
    ("box", RESIDENT, ["[Resident]", "asks to change", "payment details"]),
    ("box", DATA, ["log_payment_change_request", "documented FIRST, so a", "broken flow still leaves a record"]),
    ("box", GATE, ["verify_identity", "HARD GATE \u00b7 server-side", "never the agent's own claim"]),
    ("exit", ["fails \u2192 no task,", "escalate to a person"]),
    ("box", PERSON, ["create_staff_task \u2192 Monday", "verification result attached"]),
    ("box", AGENT, ["Tells the resident a team", "member will action it"]),
    ("box", PERSON, ["[Staff] confirms and deletes", "the payment info in OXS", "by hand \u2014 no API for this"]),
    ("box", DATA, ["Audit record", "who asked, what was verified,", "who confirmed, when"]),
    ("box", AGENT, ["send_app_instructions", "WhatsApp: re-enter in the app"]),
    ("box", PERSON, ["48h / 72h follow-up flag", "if details never re-entered"]),
    ("term", TERM, ["Payment details replaced"]),
]
column(2, p3)

# --- 2.4 payment link ---------------------------------------------------
column(3, [
    ("box", RESIDENT, ["[Resident]", "asks to pay, or asks", "what they owe"]),
    ("box", OX, ["identify_resident", "READ general info"]),
    ("box", OX, ["READ debts", "live balance"]),
    ("box", AGENT, ["send_payment_link", "the link is OXS-generated,", "never made by us"]),
    ("box", DATA, ["payment_events", "who, when, which balance"]),
    ("term", TERM, ["Link sent on WhatsApp"]),
])

# --- 2.5 complaint ticket -----------------------------------------------
column(4, [
    ("box", RESIDENT, ["[Resident]", "makes a complaint"]),
    ("box", OX, ["identify_resident", "READ general info"]),
    ("box", DATA, ["open_complaint_ticket", "category, description,", "building/unit, channel, time"]),
    ("exit", ["angry \u00b7 safety \u00b7 legal", "\u00b7 asks for a person", "\u2192 immediately"]),
    ("box", PERSON, ["Summary to the", "responsible team"]),
    ("box", DATA, ["log_call_outcome"]),
    ("term", TERM, ["Ticket open"]),
])

# --- 3 outbound debt ----------------------------------------------------
column(5, [
    ("box", OX, ["Campaign queue", "READ debts \u00b7 live balances"]),
    ("box", GATE, ["Guards before any dial", "duplicate prevention \u00b7 call", "windows \u00b7 DNC list"]),
    ("box", AGENT, ["Telnyx dials", "Israeli caller ID"]),
    ("diamond", DECIDE, ["Right person?"]),
    ("box", AGENT, ["States the month and", "the amount. Nothing else", "about money."]),
    ("exit", ["wrong party \u00b7 voicemail", "\u2192 fixed line, no amount,", "log and end"]),
    ("diamond", DECIDE, ["Card on file?"]),
    ("box", AGENT, ["Asks authorisation to charge", "the card ending 0000.", "Never takes card details."]),
    ("box", DATA, ["open_payment_ticket", "authorization_captured", "a person makes the charge"]),
    ("exit", ["hardship \u00b7 dispute \u00b7 distress", "\u00b7 language \u00b7 asked for a person", "\u2192 hand over, stay on the line"]),
    ("box", DATA, ["log_call_outcome", "every call, always \u2014 including", "voicemail and wrong party"]),
    ("term", TERM, ["Outcome logged"]),
])

BOT = max(e["bottom"] for e in ends)

# no-card branch, written beside the diamond rather than drawn as a second column
label(CX[5] - BOX_W / 2.0 - 225, TOP + 690,
      "no card on file \u2192", 12, MUTED)
label(CX[5] - BOX_W / 2.0 - 225, TOP + 710,
      "\"someone will contact you", 12, MUTED)
label(CX[5] - BOX_W / 2.0 - 225, TOP + 728,
      "to arrange it\"  \u2014 and", 12, MUTED)
label(CX[5] - BOX_W / 2.0 - 225, TOP + 746,
      "nothing about the card", 12, MUTED)

# =======================================================================
# section 7 - the rule every dashed pill obeys
# =======================================================================
BAND_Y = BOT + 90
_base("rectangle", EDGE, BAND_Y, WIDE, 118, "#f08c00", "#fff9db",
      roundness={"type": 3}, strokeStyle="dashed", boundElements=None)
label(EDGE + 24, BAND_Y + 16, "7.  HUMAN HANDOVER  \u00b7  MANDATORY IN EVERY FLOW", 13, "#f08c00")
label(EDGE + 24, BAND_Y + 42,
      "Triggers:  asks for a person  \u00b7  anger or distress  \u00b7  a payment dispute  \u00b7  "
      "safety or legal  \u00b7  the agent cannot resolve it", 13)
label(EDGE + 24, BAND_Y + 68,
      "Voice: warm transfer, the agent whispers a summary first. No rep free \u2192 schedule_callback "
      "and say so.    WhatsApp: staff take the thread, the bot switches off for it.", 13, MUTED)
label(EDGE + 24, BAND_Y + 92,
      "Every dashed pill above lands here. On outbound the agent says the handover line, calls "
      "transfer_to_human, and stays on the line \u2014 it never hangs up on a handover.", 12, MUTED)

# =======================================================================
# where anything can be written
# =======================================================================
SINK_Y = BAND_Y + 168
label(EDGE, SINK_Y - 28, "THE ONLY FOUR PLACES ANYTHING LANDS", 12, HEAD)

sink_w = (WIDE - 3 * 24) / 4.0
for i, (colors, title, body) in enumerate([
        (OX, "OXS  \u00b7  the spine",
         "Service requests written live.\nDebts and residents read live.\n"
         "Payment methods: no API \u2014\na person, every time."),
        (DATA, "Supabase  \u00b7  the record",
         "Everything that happened.\nInteractions, transcripts, audio,\nverification attempts, audit log,\n"
         "and all outbound call outcomes\n\u2014 which OXS cannot accept."),
        (PERSON, "Monday  \u00b7  the work",
         "Everything a person must do next.\nAll of it through create_staff_task,\n"
         "so where it lands stays one\nnode's configuration."),
        (TERM, "CRM  \u00b7  the window",
         "Read-only over Supabase. Hebrew RTL.\nNot a work queue \u2014 staff already\n"
         "live in OXS and Monday.\nDepartment-scoped by design.")]):
    x = EDGE + i * (sink_w + 24)
    _base("rectangle", x, SINK_Y, sink_w, 156, colors[0], colors[1],
          roundness={"type": 3}, boundElements=None)
    label(x + 18, SINK_Y + 16, title, 14, INK)
    for j, ln in enumerate(body.split("\n")):
        label(x + 18, SINK_Y + 44 + j * 20, ln, 12, INK)

# =======================================================================
# key + what is not built
# =======================================================================
KY = SINK_Y + 194
label(EDGE, KY + 4, "WHICH SYSTEM IS TOUCHED", 11, MUTED)
kx = EDGE + 210
for colors, txt in [(RESIDENT, "the resident"), (AGENT, "the agent alone"),
                    (OX, "OXS API"), (DATA, "Supabase"),
                    (PERSON, "a person"), (GATE, "refuses rather than degrades")]:
    _base("rectangle", kx, KY, 26, 15, colors[0], colors[1],
          roundness={"type": 3}, boundElements=None)
    kx += 34 + label(kx + 34, KY + 1, txt, 12) + 30

label(EDGE, KY + 40, "NOT BUILT YET", 11, MUTED)
label(EDGE + 210, KY + 40,
      "Not one of the twelve tools exists as a webhook. Both assistants show tools: none \u2014 so today "
      "the agent says it opened a ticket and nothing is written.", 13, "#e03131")
label(EDGE + 210, KY + 62,
      "Also open: the verification method for 2.3, the 48h-vs-72h window, call-recording consent "
      "under Israeli law, and OXS endpoint docs \u2014 the table above says what the modules expose, not "
      "what the requests look like.", 13, MUTED)

# =======================================================================
doc = {"type": "excalidraw", "version": 2, "source": "https://excalidraw.com",
       "elements": els,
       "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
       "files": {}}

out = r"c:\Users\Acer nitro 5\Desktop\Homie\docs\diagrams\Homies-System-Flow.excalidraw"
with io.open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=1)

print("wrote %s" % out)
print("elements: %d" % len(els))
