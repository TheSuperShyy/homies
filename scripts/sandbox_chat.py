"""Talk to the sandbox bot as a tenant (feature 19).

    python scripts/sandbox_chat.py   # then open http://127.0.0.1:8765

One page, plus a proxy to Chatwoot's public client API for the sandbox API inbox.
"Writing as" comes from SANDBOX_PERSONAS in .env (label:+phone, never committed).
Each persona is a Chatwoot contact carrying that phone, which is what the bot
reads, as on WhatsApp. Nothing here touches the live account, the live bot or WhatsApp.
"""
import json, os, sys, urllib.error, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from supabase_functions import env

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "local", "sandbox", "contacts.json")
E = env()
CW = E["CHATWOOT_URL"].rstrip("/") + "/public/api/v1/inboxes/" + E["SANDBOX_CW_INBOX_IDENTIFIER"]
PERSONAS = {"p%d" % i: (lbl.strip(), ph.strip())
            for i, (lbl, ph) in enumerate(p.split(":", 1) for p in E["SANDBOX_PERSONAS"].split(","))}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PAGE = """<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Homies sandbox chat</title>
<style>
body{font-family:system-ui,Arial,sans-serif;margin:0;background:#efeae2;color:#111}
header{background:#075e54;color:#fff;padding:10px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
header select,header button{font-size:15px;padding:4px 8px}
#log{padding:12px;display:flex;flex-direction:column;gap:6px;height:calc(100vh - 130px);overflow-y:auto}
.m{max-width:75%;padding:7px 10px;border-radius:8px;white-space:pre-wrap;line-height:1.4}
.in{align-self:flex-start;background:#dcf8c6}.out{align-self:flex-end;background:#fff}
.btns{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}.btns button{font-size:14px;padding:4px 8px}
form{display:flex;gap:8px;padding:8px;background:#f0f0f0}form input{flex:1;font-size:16px;padding:8px}
</style></head><body>
<header><strong>סביבת ניסוי — מיכאל</strong>
<label>כותב בתור <select id="who"></select></label><button id="new">שיחה חדשה</button></header>
<div id="log"></div>
<form id="f"><input id="t" autocomplete="off" placeholder="הודעה…"><button>שליחה</button></form>
<script>
let conv = null, key = null, seen = 0;
const $ = (id) => document.getElementById(id);
async function j(url, body) {
  const r = await fetch(url, body ? {method: "POST", headers: {"content-type": "application/json"}, body: JSON.stringify(body)} : {});
  return r.json();
}
async function start() {
  key = $("who").value; $("log").innerHTML = ""; seen = 0;
  conv = (await j("/api/start", {key})).conv;
}
async function send(text) {
  if (!conv || !text.trim()) return;
  await j("/api/send", {key, conv, content: text});
}
async function poll() {
  if (conv) {
    const msgs = await j("/api/messages?key=" + key + "&conv=" + conv);
    for (const m of msgs.slice(seen)) {
      const d = document.createElement("div");
      d.className = "m " + (m.out ? "out" : "in"); d.textContent = m.content;
      if (m.buttons.length) {
        const b = document.createElement("div"); b.className = "btns";
        for (const t of m.buttons) { const x = document.createElement("button"); x.textContent = t; x.onclick = () => send(t); b.appendChild(x); }
        d.appendChild(b);
      }
      $("log").appendChild(d); $("log").scrollTop = 1e9;
    }
    seen = msgs.length;
  }
  setTimeout(poll, 1500);
}
(async () => {
  for (const p of await j("/api/personas")) { const o = document.createElement("option"); o.value = p.key; o.textContent = p.label; $("who").appendChild(o); }
  $("new").onclick = start; $("who").onchange = start;
  $("f").onsubmit = (e) => { e.preventDefault(); send($("t").value); $("t").value = ""; };
  await start(); poll();
})();
</script></body></html>"""


def cw(method, path, body=None):
    req = urllib.request.Request(CW + path, method=method,
                                 data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None,
                                 headers={"Content-Type": "application/json", "User-Agent": "homies/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")


def contact(key):
    """The persona's source_id on the sandbox inbox, created once and cached."""
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    if key not in cache:
        label, phone = PERSONAS[key]
        cache[key] = cw("POST", "/contacts", {"identifier": "sbx-" + key, "name": label, "phone_number": phone})["source_id"]
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        json.dump(cache, open(CACHE, "w", encoding="utf-8"))
    return cache[key]


def messages(key, conv):
    """The conversation as the page shows it: oldest first, tenant and bot only, with any buttons."""
    msgs = cw("GET", "/contacts/%s/conversations/%s/messages" % (contact(key), conv)) or []
    return [{"id": m["id"], "out": m.get("message_type") == 1, "content": m.get("content") or "",
             "buttons": [i.get("title") for i in ((m.get("content_attributes") or {}).get("items") or [])]}
            for m in sorted(msgs, key=lambda m: m["id"]) if m.get("message_type") in (0, 1)]


class H(BaseHTTPRequestHandler):
    def reply(self, obj, ctype="application/json", code=200):
        data = obj.encode("utf-8") if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code); self.send_header("content-type", ctype + "; charset=utf-8"); self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = dict(urllib.parse.parse_qsl(u.query))
        try:
            if u.path == "/":
                return self.reply(PAGE, "text/html")
            if u.path == "/api/personas":
                return self.reply([{"key": k, "label": v[0]} for k, v in PERSONAS.items()])
            if u.path == "/api/messages":
                return self.reply(messages(q["key"], q["conv"]))
        except urllib.error.HTTPError as x:
            return self.reply({"error": "chatwoot %s" % x.code}, code=502)
        self.send_error(404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
        try:
            if self.path == "/api/start":
                return self.reply({"conv": cw("POST", "/contacts/%s/conversations" % contact(body["key"]), {})["id"]})
            if self.path == "/api/send":
                cw("POST", "/contacts/%s/conversations/%s/messages" % (contact(body["key"]), body["conv"]),
                   {"content": body["content"]})
                return self.reply({"ok": True})
        except urllib.error.HTTPError as x:
            return self.reply({"error": "chatwoot %s" % x.code}, code=502)
        self.send_error(404)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("sandbox chat on http://127.0.0.1:8765 (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", 8765), H).serve_forever()
