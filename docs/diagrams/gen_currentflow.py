# -*- coding: utf-8 -*-
"""Homies - every flow that actually runs, drawn end to end.

Same shape as Homies-System-Flow (front doors, a wide bar, six columns, bands
at the bottom) because that layout reads well. Everything IN it is different:
that one draws the PRD's intention, this one was built by reading the code on
10 Aug 2026.

What changed against the older diagram, and why each is not a style choice:

  * No Telnyx, no phone number. The Vapi account has no phoneNumberId; the
    only way a call happens today is a web call from web/index.html.
  * No Chatwoot in the path. deploy/chatwoot is groundwork, nothing routes
    through it.
  * n8n is a ROUTER, not "the brain". The twelve handlers live in the Supabase
    Edge Function debt-tools. Voice reaches it through n8n; the end-of-call
    report and the two chat read-tools go straight to it.
  * No identify_resident and no create_staff_task. Neither exists in code.
  * open_request writes Supabase `requests`, never OXS. OXS is read-only.
  * References are ours - HM-YYYY-NNNN from a Postgres sequence.

Colour says WHICH SYSTEM IS TOUCHED, not who is talking.
"""
import io, json

# --- palette -----------------------------------------------------------
RESIDENT = ("#2f9e44", "#b2f2bb")   # a person
AGENT    = ("#1971c2", "#d0ebff")   # agent runtime, voice or chat
TOOL     = ("#5f3dc4", "#e5dbff")   # a tool handler runs
DATA     = ("#0c8599", "#c5f6fa")   # a Supabase row is written
READ     = ("#1971c2", "#e7f5ff")   # a read, nothing written
PERSON   = ("#f08c00", "#ffec99")   # leaves the machine, or a human looks
OXS      = ("#9c36b5", "#f8f0fc")   # OXS, read-only forever
MISS     = ("#adb5bd", "#f1f3f5")   # not built
INK      = "#1e1e1e"
MUTED    = "#868e96"
HEAD     = "#1971c2"
WARN     = "#e03131"

# --- geometry ----------------------------------------------------------
BOX_W  = 300
PILL_W = 210
PITCH  = 540
EDGE   = 80
LH, EM = 1.25, 0.53
GAP    = 50

COLS = 6
CX   = [EDGE + BOX_W / 2.0 + i * PITCH for i in range(COLS)]
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


def node(cx, y, lines, colors, w=BOX_W, h=None, size=12, dashed=False):
    body = "\n".join(lines)
    if h is None:
        h = int(len(lines) * size * LH) + 26
    x = cx - w / 2.0
    tid = _id("t")
    shape = _base("rectangle", x, y, w, h, colors[0], colors[1], eid=_id("n"),
                  roundness={"type": 3},
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


def column(cx, y0, items):
    """A vertical flow.

    items = (lines, colors) for a step, or a third element:
      'exit' - an orange pill, the flow leaves to a human (this works today)
      'gap'  - a grey pill marked with a cross, this part is NOT BUILT
    """
    made, y = [], y0
    for it in items:
        lines, colors = it[0], it[1]
        kind = it[2] if len(it) > 2 else None
        if kind in ("exit", "gap"):
            anchor = made[-1]
            node(anchor["right"] + 20 + PILL_W / 2.0, anchor["mid"] - 24,
                 lines, PERSON if kind == "exit" else MISS,
                 w=PILL_W, size=11, dashed=True)
            continue
        nd = node(cx, y, lines, colors)
        if made:
            link(made[-1], nd)
        made.append(nd)
        y = nd["bottom"] + GAP
    return made


# =======================================================================
# title
# =======================================================================
label(EDGE, 4, "Homies  \u00b7  every flow that actually runs", 26)
label(EDGE, 44, "10 August 2026, built by reading the code. Colour says which "
                "system is touched. Dashed pills are the exits to a human.", 14, MUTED)
label(EDGE, 68, "Red notes mark where the PRD and the older diagram are now "
                "wrong.", 13, WARN)

# =======================================================================
# the scoreboard - done and not done, before anything else
# =======================================================================
SC = 100
_base("rectangle", EDGE, SC, WIDE, 92, "#adb5bd", "#fcfcfd",
      roundness={"type": 3}, boundElements=None)

label(EDGE + 22, SC + 14, "✓  DONE  —  five flows", 14, "#2f9e44")
label(EDGE + 22, SC + 40,
      "✓  outbound debt collection (voice)        "
      "✓  inbound calls answered, ticket opened (voice)        "
      "✓  balance check (voice + chat)", 12, INK)
label(EDGE + 22, SC + 62,
      "✓  WhatsApp bot — opens tickets, checks ticket status        "
      "✓  dashboard — calls, tickets, debts, conversations", 12, INK)

label(EDGE + 1720, SC + 14, "✗  NOT DONE  —  four gaps", 14, "#495057")
label(EDGE + 1720, SC + 40,
      "✗  calls on a real phone number        "
      "✗  payment link delivered on WhatsApp", 12, MUTED)
label(EDGE + 1720, SC + 62,
      "✗  human agent inbox (Chatwoot)        "
      "✗  automatic sync from OXS", 12, MUTED)

# =======================================================================
# the two front doors
# =======================================================================
SPINE_Y = 232
label(EDGE, SPINE_Y - 26, "THE TWO FRONT DOORS  \u00b7  and there is no third",
      12, HEAD)

sp_w, sp_h, sp_p = 210, 60, 244


def chain(y, items, colors):
    made = []
    for i, lines in enumerate(items):
        nd = node(EDGE + sp_w / 2.0 + i * sp_p, y, lines, colors,
                  w=sp_w, h=sp_h, size=11)
        if made:
            link(made[-1], nd, pts=[(made[-1]["right"] + 4, made[-1]["mid"]),
                                    (nd["left"] - 4, nd["mid"])])
        made.append(nd)
    return made


chain(SPINE_Y, [["[Resident]  \u00b7  browser", "opens web/index.html"],
                ["WEB CALL", "no phone number exists"],
                ["Vapi", "11labs STT \u00b7 Cartesia TTS"]], RESIDENT)
chain(SPINE_Y + 88, [["[Resident]  \u00b7  phone", "sends a WhatsApp message"],
                     ["Meta Cloud API v21.0", "one test number"],
                     ["n8n  \u00b7  WhatsApp bot", "/webhook/homies-whatsapp"]],
      RESIDENT)

# --- the OXS panel, beside the front doors -----------------------------
KX = EDGE + 3 * sp_p + 20
_base("rectangle", KX, SPINE_Y - 10, 1560, 168, "#9c36b5", "#fdf4ff",
      roundness={"type": 3}, boundElements=None)
label(KX + 22, SPINE_Y + 8, "OXS EXTERNAL API v1  \u00b7  VERIFIED WORKING, "
                            "READ-ONLY FOREVER", 13, "#9c36b5")
label(KX + 22, SPINE_Y + 32, "api.oxs.co.il/api/external/v1   \u00b7   header "
                             "x-api-key   \u00b7   envelope {status, data}   "
                             "\u00b7   60 req/min per key", 12, MUTED)
for i, (mod, key, what) in enumerate([
        ("general", "OXS_KEY_GENERAL", "buildings \u00b7 apartments \u00b7 tenants \u00b7 payments"),
        ("finance", "OXS_KEY_DEBTS", "debts \u2014 GET /debts carries real resident mobiles"),
        ("service_calls", "OXS_KEY_REQUESTS", "service calls \u2014 writes exist but are forbidden by policy")]):
    y = SPINE_Y + 58 + i * 22
    label(KX + 22, y, mod, 12, INK)
    label(KX + 150, y, key, 12, "#9c36b5")
    label(KX + 330, y, what, 12, MUTED)
label(KX + 22, SPINE_Y + 130, "Nothing in this system ever writes to OXS. A "
                              "change a resident asks for becomes staff work, "
                              "not an API call.", 12, WARN)

# =======================================================================
# the tool layer
# =======================================================================
BAR_Y = SPINE_Y + 196
bar = node(EDGE + WIDE / 2.0, BAR_Y,
           ["THE TOOL LAYER  \u00b7  one writer, reached three ways",
            "Vapi tool call \u2192 n8n /webhook/homies-debt-tools \u2192 Supabase Edge Function debt-tools   "
            "\u00b7   end-of-call report and the two chat read-tools go STRAIGHT to the Edge Function",
            "12 handlers  \u00b7  x-homies-secret  \u00b7  --no-verify-jwt  \u00b7  every write opens an interactions stub first"],
           TOOL, w=WIDE, h=86, size=13)

# =======================================================================
# the flows
# =======================================================================
FLOW_Y = BAR_Y + 150
label(EDGE, FLOW_Y - 74, "THE FLOWS THAT RUN TODAY", 12, HEAD)

HEADS = [
    ("\u2713  1.1  Inbound call \u2192 ticket", "voice  \u00b7  web call only"),
    ("\u2713  1.2  WhatsApp \u2192 ticket", "chat"),
    ("\u2713  1.3  Check a ticket", "chat  \u00b7  reads only"),
    ("\u2713  1.4  Check a balance", "voice + chat  \u00b7  reads only"),
    ("\u2713  2  Outbound debt follow-up", "voice  \u00b7  but see the crosses"),
    ("\u2713  3  OXS \u2192 Supabase", "works, but nobody schedules it"),
]
for i, (t, s) in enumerate(HEADS):
    centred(CX[i], FLOW_Y - 46, t, 15, HEAD)
    centred(CX[i], FLOW_Y - 24, s, 11, MUTED)

column(CX[0], FLOW_Y, [
    (["[Resident]", "starts a web call"], RESIDENT),
    (["Vapi  \u00b7  Inbound Intake (he/en)", "gpt-4.1-mini  \u00b7  180s cap"], AGENT),
    (["Captures type, description,", "building, unit, urgency"], AGENT),
    (["open_request", "via n8n \u2192 Edge Function", "30-minute duplicate guard"], TOOL),
    (["requests row", "reference HM-YYYY-NNNN", "ours, a Postgres sequence"], DATA),
    (["transfer_to_human", "\u2192 call_outcomes"], PERSON, "exit"),
    (["Reads the reference back", "once, slowly, never twice"], AGENT),
    (["end-of-call report", "interactions + transcript"], DATA),
    (["cut off or silence", "salvage \u2192 needs_review"], PERSON, "exit"),
])

column(CX[1], FLOW_Y, [
    (["[Resident]", "sends a WhatsApp message"], RESIDENT),
    (["Meta Cloud API v21.0", "POST /webhook/homies-whatsapp"], AGENT),
    (["Sign the raw body (HMAC)", "Sort: verify, dedupe on wamid,", "detect language"], AGENT),
    (["messages row  \u00b7  inbound", "straight to PostgREST"], DATA),
    (["AI Agent  \u00b7  gemini-2.5-flash", "memory: 30 turns, by phone"], AGENT),
    (["error \u2192 Hand over instead", "one fixed line, he/en"], PERSON, "exit"),
    (["open_request", "opened_via = 'whatsapp'"], TOOL),
    (["requests row  +  Send reply", "messages row  \u00b7  outbound"], DATA),
    (["\u2717  Chatwoot agent inbox", "not connected to the bot"], MISS, "gap"),
])

column(CX[2], FLOW_Y, [
    (["[Resident] asks for status", "or taps the menu"], RESIDENT),
    (["Menu taps answered", "deterministically, no LLM"], AGENT),
    (["get_request_status", "direct to the Edge Function,", "bypasses the n8n router"], TOOL),
    (["READS requests", "reference \u2192 resident \u2192 unit", "newest three"], READ),
    (["nothing found", "\u2192 the options list"], PERSON, "exit"),
    (["Answers the status in words", "never a table, never a dump"], AGENT),
])

column(CX[3], FLOW_Y, [
    (["[Resident]", "asks what they owe"], RESIDENT),
    (["Either agent, same tool", "voice and chat share one writer"], AGENT),
    (["get_balance", "direct to the Edge Function"], TOOL),
    (["READS residents + charges", "phone \u2192 resident \u2192 unit \u2192 name"], READ),
    (["the name is ambiguous", "\u2192 found: 0, ask again"], PERSON, "exit"),
    (["Answers the sum itself", "answered, not handed over"], AGENT),
])

column(CX[4], FLOW_Y, [
    (["v_debt_call_queue", "unpaid \u00b7 handed over \u00b7 not DNC", "attempts < 4  \u2014  the view IS the guard"], READ),
    (["Demo console places the call", "WEB CALL  \u2014  nothing dials"], AGENT),
    (["\u2717  a real phone number", "web calls only, no DID yet"], MISS, "gap"),
    (["Vapi  \u00b7  Debt Follow-up (he/en)", "Cartesia voice  \u00b7  240s cap"], AGENT),
    (["The four branches", "promise \u00b7 dispute \u00b7 paid \u00b7 refuse"], AGENT),
    (["transfer_to_human", "\u2192 call_outcomes"], PERSON, "exit"),
    (["log_promise_to_pay", "log_disputed_payment", "send_payment_link"], TOOL),
    (["promises_to_pay \u00b7 payment_disputes", "payment_links  \u2014  all 0 rows today"], DATA),
    (["\u2717  nothing delivers the link", "the row is written, then stops"], MISS, "gap"),
    (["log_call_outcome", "call_outcomes  +  charges.attempts"], DATA),
    (["flag_not_handed_over", "residents + charges, one way"], PERSON, "exit"),
])

column(CX[5], FLOW_Y, [
    (["OXS External API v1", "three scoped keys, all live"], OXS),
    (["GET /debts", "carries real resident mobiles"], OXS),
    (["oxs_import.py", "xlsx \u2192 CSV, guesses nothing"], OXS),
    (["import_oxs_csv.py --apply", "upsert on phone,", "and on (resident_id, period)"], OXS),
    (["residents + charges", "rows marked source = 'oxs'"], DATA),
    (["✗  no scheduler exists", "somebody runs this by hand"], MISS, "gap"),
])

# =======================================================================
# bands
# =======================================================================
BY = FLOW_Y + 700

node(EDGE + WIDE / 2.0, BY,
     ["SUPABASE (Postgres)  \u00b7  the only store  \u00b7  live counts, 10 Aug 2026",
      "interactions 53   \u00b7   messages 99   \u00b7   charges 19   \u00b7   residents 22 (12 real + 10 seed)   "
      "\u00b7   call_outcomes 15   \u00b7   requests 2",
      "payment_links 0   \u00b7   promises_to_pay 0   \u00b7   payment_disputes 0   \u00b7   payment_tickets 0  "
      "\u2014  every money table is still empty"],
     DATA, w=WIDE, h=86, size=13)

node(EDGE + WIDE / 2.0, BY + 116,
     ["WHAT A HUMAN LOOKS AT  \u00b7  Dashboard, Next.js 14 on Vercel, homies-dashboard.vercel.app",
      "/  \u00b7  /tickets  \u00b7  /debts  \u00b7  /conversations  \u00b7  /calls  \u00b7  /calls/[id]   "
      "\u2014   anon key, no login since 9 Aug, read-only except requests.status"],
     PERSON, w=WIDE, h=68, size=13)

NB = BY + 216
_base("rectangle", EDGE, NB, WIDE, 186, "#adb5bd", "#f8f9fa",
      roundness={"type": 3}, boundElements=None)
label(EDGE + 22, NB + 14, "NOT BUILT  \u2014  the four gaps, and what each one "
                          "actually blocks", 14, "#495057")
for i, (t, why) in enumerate([
        ("Calls on a real phone number",
         "The Vapi account has no phoneNumberId. Needs the four Omnitelecom SIP values, and an Israeli DID needs Homies' company documents. Web calls only until then."),
        ("Payment link sent on WhatsApp",
         "send_payment_link writes a payment_links row and stops. Nothing delivers it, which is why that table has 0 rows. OXS exposes no payment-link endpoint either."),
        ("Human agent inbox (Chatwoot)",
         "deploy/chatwoot exists as groundwork only. It is not in the message path; transfer_to_human writes a call_outcomes row and the conversation ends there."),
        ("Automatic sync from OXS",
         "The API is proven and read-only, but the import is two scripts run by hand. No scheduler, no nightly job, nothing watching for a changed debt.")]):
    y = NB + 44 + i * 30
    label(EDGE + 22, y, "\u2717  " + t, 13, "#495057")
    label(EDGE + 340, y, why, 12, MUTED)

label(EDGE + 22, NB + 166, "Also doc-only, despite the PRD and the older diagram "
      "drawing them: create_staff_task, the staff_tasks table, and "
      "identify_resident \u2014 no handler, no table, no tool. The real stand-in is "
      "transfer_to_human / request_standing_order writing call_outcomes.", 12, WARN)

LG = NB + 210
label(EDGE, LG, "COLOUR", 12, HEAD)
for i, (name, colors) in enumerate([
        ("a person", RESIDENT), ("agent runtime", AGENT), ("a tool runs", TOOL),
        ("Supabase write", DATA), ("a read only", READ), ("a human, or OXS", PERSON)]):
    x = EDGE + 90 + i * 250
    _base("rectangle", x, LG - 2, 22, 16, colors[0], colors[1],
          roundness={"type": 3}, boundElements=None)
    label(x + 30, LG, name, 12, MUTED)

label(EDGE, LG + 26, "\u2713  a column header means that whole flow runs today."
      "        \u2717  a grey dashed pill is the one part of that flow that is "
      "NOT built \u2014 everything above and below it works.", 12, MUTED)
label(EDGE, LG + 48, "An orange dashed pill is different: that is an exit to a "
      "human, and it works. Nothing on this page is aspirational \u2014 if it is "
      "drawn solid, it has a handler in code.", 12, MUTED)

# =======================================================================
doc = {"type": "excalidraw", "version": 2, "source": "https://excalidraw.com",
       "elements": els,
       "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
       "files": {}}

out = r"c:\Users\Acer nitro 5\Desktop\Homie\docs\diagrams\Homies-Current-System-Flow.excalidraw"
with io.open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=1)

print("wrote %s" % out)
print("elements: %d" % len(els))
