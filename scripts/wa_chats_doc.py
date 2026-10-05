# -*- coding: utf-8 -*-
"""The WhatsApp bot's real chats, as a document for Google Docs.

    python scripts/wa_chats_doc.py --run RUN_DIR --en EN.json --out PREFIX [--conversation 1] [--date 2026-10-05]

WHY, 6 Oct. The owner, after the two voice documents: *"ok now do one for the
chatbot only get the chats you have all the api key u need"*. No new test: the
chats that already happened, taken from the system.

WHERE EACH SIDE COMES FROM, AND WHY TWO PLACES
- The bot's side, and its notes to the team, come from the inbox: Chatwoot,
  read through the API (GET only). That is what reached the phone and what the
  team sees.
- The tenant's side comes from the live run's own record (`wa_qa.py live`,
  RUN_DIR/transcripts/*_A.json). Those messages were handed to the bot's webhook
  in Chatwoot's own envelope, so the bot answered them, but Chatwoot never
  stored them: an injected message is not a message Chatwoot received.
Every bot reply in the record is matched to the inbox word for word, and the
script says how many were not. Notes are attached to the reply they came with
(n8n writes the note a second before the reply).

The English and the commentary come from EN.json, written by whoever read the
chats; the Hebrew is always copied, never retyped.
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TEAMS = {"שירות": "service", "תפעול": "operations", "גבייה": "collections", "ניהול": "management"}
REASONS = {
    "משהו שרק בן אדם מהצוות יכול לסדר.": "something only a person on the team can sort out",
    "הדייר ביקש לדבר עם בן אדם.": "the resident asked to talk to a person",
    "הדייר רוצה לשלם או להסדיר תשלום.": "the resident wants to pay or arrange a payment",
}
AUTO = "הבוט אמר לדייר שהצוות יודע, ולכן זה נרשם כאן אוטומטית."


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def inbox(conversation):
    """Every message of one Chatwoot conversation, oldest first (GET only)."""
    import prompt_probe as P
    base = P.E["CHATWOOT_URL"].rstrip("/")
    head = {"api_access_token": P.E["CHATWOOT_API_TOKEN"], "User-Agent": "homies/1.0"}
    msgs, before = {}, None
    while True:
        url = "%s/api/v1/accounts/%s/conversations/%d/messages%s" % (
            base, P.E["CHATWOOT_ACCOUNT_ID"], conversation, "?before=%d" % before if before else "")
        page = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=head), timeout=60).read()).get("payload", [])
        fresh = [m for m in page if m["id"] not in msgs]
        if not fresh:
            break
        for m in page:
            msgs[m["id"]] = m
        before = min(m["id"] for m in page)
    return sorted(msgs.values(), key=lambda m: (m["created_at"], m["id"]))


def norm(s):
    return " ".join(str(s or "").split())


def utc(ts, fmt="%H:%M"):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime(fmt)


def menu_buttons(m):
    items = (m.get("content_attributes") or {}).get("items") or []
    return " ".join("[%s]" % i.get("title") for i in items)


def note_parts(text):
    out = {"team": "", "reason": "", "auto": False, "what": ""}
    for line in str(text or "").splitlines():
        line = line.strip()
        t = re.match(r"\[@([^\]]+)\]", line)
        if t:
            out["team"] = TEAMS.get(t.group(1), t.group(1))
        elif line.startswith("סיבה:"):
            out["reason"] = line[len("סיבה:"):].strip()
        elif line == AUTO:
            out["auto"] = True
        elif line.startswith("מה הדייר רוצה:"):
            out["what"] = line[len("מה הדייר רוצה:"):].strip()
    return out


def note_he(text):
    """The note as the team reads it, with Chatwoot's mention markup flattened."""
    return re.sub(r"\[(@[^\]]+)\]\(mention://[^)]*\)", r"\1", str(text or "")).strip()


def assemble(run, msgs, day, en):
    """The chats: run turns with the inbox's replies and notes attached."""
    today = [m for m in msgs if utc(m["created_at"], "%Y-%m-%d") == day]
    outs = [m for m in today if m.get("message_type") == 1 and not m.get("private")]
    notes = [m for m in today if m.get("private")]
    used, chats, misses = set(), [], 0
    for sid in en["order"]:
        t = load(os.path.join(run, "transcripts", sid + "_A.json"))
        turns = []
        for i, x in enumerate(t["turns"]):
            got = []
            for h in x.get("handset") or []:
                cand = [o for o in outs if o["id"] not in used and norm(o["content"]) == norm(h)]
                if i == 0 and cand:
                    # The menu is the same text every time: take the last one
                    # before this chat's next reply, not the first of the day.
                    nxt = t["turns"][1]["handset"][0] if len(t["turns"]) > 1 and t["turns"][1].get("handset") else None
                    after = min((o["created_at"] for o in outs if o["id"] not in used and nxt and norm(o["content"]) == norm(nxt)),
                                default=None)
                    cand = [o for o in cand if after is None or o["created_at"] <= after][-1:] or cand[:1]
                elif cand and turns and turns[-1]["bot"]:
                    last = turns[-1]["bot"][-1]["created_at"]
                    cand = [o for o in cand if o["created_at"] >= last] or cand
                m = cand[0] if cand else None
                if m:
                    used.add(m["id"])
                else:
                    misses += 1
                got.append({"text": h, "id": m["id"] if m else None, "created_at": m["created_at"] if m else None,
                            "buttons": menu_buttons(m) if m else ""})
            turns.append({"i": i, "kind": x.get("kind"), "tenant": x["resident"], "tenant_en": x.get("resident_en", ""),
                          "bot": got, "tools": x.get("tool_calls") or [], "execution": x.get("execution"), "notes": []})
        chats.append({"id": sid, "ended": t.get("ended"), "turns": turns})
    # Each note goes with the first reply written at or after it (n8n writes the
    # note, then the reply, a second apart).
    placed = [(b["created_at"], c, tr) for c in chats for tr in c["turns"] for b in tr["bot"] if b["created_at"]]
    placed.sort(key=lambda p: p[0])
    for n in notes:
        hit = next(((c, tr) for ts, c, tr in placed if ts >= n["created_at"] and ts - n["created_at"] <= 10), None)
        if hit:
            hit[1]["notes"].append(n)
    # What else the inbox holds that day: messages that are not part of the run.
    rest = [m for m in today if not m.get("private") and m.get("message_type") in (0, 1) and m["id"] not in used]
    own, cur = [], []
    for m in rest:
        if cur and m["created_at"] - cur[-1]["created_at"] > 600:
            own.append(cur)
            cur = []
        cur.append(m)
    if cur:
        own.append(cur)
    return chats, own, misses, len(notes)


def note_en(n, turn, en):
    p = note_parts(n.get("content"))
    what = turn["tenant_en"] if norm(p["what"]) == norm(turn["tenant"]) else en.get("note_what_en", {}).get(str(n["id"]), "")
    bits = ["To the %s team: a resident needs one of you." % (p["team"] or "?"),
            "Reason: %s." % REASONS.get(p["reason"], p["reason"])]
    if p["auto"]:
        bits.append("Logged automatically, because the bot had told the resident the team knows.")
    bits.append("What the resident wants: “%s”." % what.rstrip("."))
    return " ".join(bits)


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(chats, own, en, meta):
    md, ht = [], []

    def para(title, items, ordered=False):
        md.extend(["## " + title, ""] + [("%d. " % (k + 1) if ordered else "- ") + x for k, x in enumerate(items)] + [""])
        tag = "ol" if ordered else "ul"
        ht.extend(["<h2>%s</h2>" % esc(title), "<%s>" % tag] + ["<li>%s</li>" % esc(x) for x in items] + ["</%s>" % tag])

    md += ["# " + en["title"], "", en["subtitle"], ""]
    ht += ["<h1>%s</h1>" % esc(en["title"]), "<p>%s</p>" % esc(en["subtitle"])]
    para("How these chats happened", en["how"])
    para("What we found", en["findings"], ordered=True)
    head = ["Chat", "Button", "The situation", "Did he get what he came for?"]
    md += ["## The nine chats at a glance", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    ht += ["<h2>The nine chats at a glance</h2>", '<table border="1" cellpadding="6" style="border-collapse:collapse">',
           "<tr>" + "".join("<th>%s</th>" % h for h in head) + "</tr>"]
    for k, c in enumerate(chats):
        e = en["chats"][c["id"]]
        cells = [str(k + 1), e["button"], e["situation_short"], e["outcome"]]
        md.append("| " + " | ".join(x.replace("|", "/") for x in cells) + " |")
        ht.append("<tr>" + "".join("<td>%s</td>" % esc(x) for x in cells) + "</tr>")
    md.append("")
    ht.append("</table>")

    def row(who, eng, he, shade=False):
        he = re.sub(r"\s*\n+\s*", " ", he)
        md.extend(["**%s:** %s  " % (who, he), "*%s*" % eng, ""])
        ht.append('<tr%s><td><b>%s</b></td><td>%s</td><td dir="rtl" style="text-align:right">%s</td></tr>'
                  % (' style="background:#f7f7f7"' if shade else "", esc(who), esc(eng), esc(he)))

    def aside(text):
        md.extend(["> *%s*" % text, ""])
        ht.append('<tr><td colspan="3" style="background:#f2f2f2"><i>%s</i></td></tr>' % esc(text))

    fixed = en.get("text_en", {})
    for k, c in enumerate(chats):
        e = en["chats"][c["id"]]
        md += ["## Chat %d. %s" % (k + 1, e["heading"]), "", "*%s*" % e["setting"], ""]
        ht += ["<h2>Chat %d. %s</h2>" % (k + 1, esc(e["heading"])), "<p><i>%s</i></p>" % esc(e["setting"]),
               '<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">',
               "<tr><th>Who</th><th>English</th><th>Hebrew, as written</th></tr>"]
        for tr in c["turns"]:
            k_ = str(tr["i"])
            who = "Assaf (taps a button)" if tr["kind"] == "tap" else "Assaf"
            row(who, fixed.get(tr["tenant"]) if tr["kind"] == "tap" and tr["tenant"] in fixed else tr["tenant_en"], tr["tenant"])
            for line in e.get("tools_en", {}).get(k_, []):
                aside("Behind the scenes: " + line)
            for n in tr["notes"]:
                row("Note to the team (inbox only)", note_en(n, tr, en), note_he(n.get("content")), shade=True)
            for b in tr["bot"]:
                he = b["text"] + ((" " + b["buttons"]) if b["buttons"] else "")
                eng = e.get("bot_en", {}).get(k_) or fixed.get(b["text"], "")
                if b["buttons"]:
                    eng = (eng + " " + fixed.get("_buttons_en", "")).strip()
                row("Bot (fixed menu)" if tr["i"] == 0 else "Michael", eng, he)
        aside(e["ended_en"])
        md += ["**What this chat shows:**", ""] + ["- " + x for x in e["shows"]] + [""]
        ht += ["</table>", "<p><b>What this chat shows:</b></p>", "<ul>"] + ["<li>%s</li>" % esc(x) for x in e["shows"]] + ["</ul>"]

    if own and en.get("own"):
        md += ["## " + en["own"]["heading"], "", en["own"]["intro"], ""]
        ht += ["<h2>%s</h2>" % esc(en["own"]["heading"]), "<p>%s</p>" % esc(en["own"]["intro"]),
               '<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">',
               "<tr><th>Who</th><th>English</th><th>Hebrew, as written</th></tr>"]
        for chunk in own:
            aside("%s UTC (%s in Israel)" % (utc(chunk[0]["created_at"]), utc(chunk[0]["created_at"] + 3 * 3600)))
            for m in chunk:
                text = m.get("content") or ""
                he = text + ((" " + menu_buttons(m)) if menu_buttons(m) else "")
                eng = fixed.get(text, "")
                if menu_buttons(m):
                    eng = (eng + " " + fixed.get("_buttons_en", "")).strip()
                row("You" if m.get("message_type") == 0 else ("Bot (fixed menu)" if menu_buttons(m) else "Michael"), eng, he)
        ht.append("</table>")
        md.append("")
    para("How this document was made (technical)", en["technical"] + [meta])
    return "\n".join(md), "\n".join(
        ['<!doctype html>', '<html lang="en"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1">',
         "<title>%s</title>" % esc(en.get("short_title", en["title"])),
         "<style>body{font-family:Arial,sans-serif;max-width:1000px;margin:24px auto;padding:0 16px;"
         "line-height:1.45;background:#fff;color:#111}td,th{vertical-align:top;text-align:left}"
         "th{background:#e8e8e8}</style></head><body>"] + ht + ["</body></html>"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--en", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--conversation", type=int, default=1)
    ap.add_argument("--date", default="2026-10-05")
    a = ap.parse_args()
    en = load(a.en)
    msgs = inbox(a.conversation)
    chats, own, misses, n_notes = assemble(a.run, msgs, a.date, en)
    replies = sum(len(tr["bot"]) for c in chats for tr in c["turns"])
    attached = sum(len(tr["notes"]) for c in chats for tr in c["turns"])
    meta = ("Read from the inbox on %s UTC: conversation %d, %d messages on %s; the bot's %d replies in the chats "
            "matched the run's record word for word with %d missing; %d of the day's %d team notes attached to a reply."
            % (datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"), a.conversation,
               sum(1 for m in msgs if utc(m["created_at"], "%Y-%m-%d") == a.date), a.date, replies, misses,
               attached, n_notes))
    md, html = render(chats, own, en, meta)
    write(a.out + ".md", md)
    write(a.out + ".html", html)
    write(a.out + ".json", json.dumps({"source": meta, "en": en, "chats": chats, "own": own},
                                      ensure_ascii=False, indent=1))
    print(meta)
    print("wrote %s.md, .html and .json" % a.out)


if __name__ == "__main__":
    main()
