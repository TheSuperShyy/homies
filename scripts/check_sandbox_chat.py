"""Offline checks for the sandbox chat page (feature 19): it keeps showing the conversation.

    python scripts/check_sandbox_chat.py

Runs sandbox_chat.PAGE in headless Chrome against a stand-in for its own /api, with no
Chatwoot and no bot. On 27 Oct the owner's page went blank while the bot kept answering:
a switch of "writing as" let a check for new messages ask for the old conversation under
the new persona, the proxy answered "chatwoot 404", the loop threw, and nothing more was
shown until the page was reloaded. A late answer for the previous conversation, or a
check that got no answer at all, did the same. On that night's line (a fifth of the packets
to the server lost) opening a conversation took up to 16 s and a send could fail outright,
so the page also waits for the conversation instead of dropping what was typed, tries
again when opening one fails, and gives a failed send back to be sent again.
"""
import json, os, sys, threading, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox_chat import PAGE
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class Fake:
    """Chatwoot as the page sees it through the proxy: each conversation belongs to one persona."""
    def __init__(self):
        self.convs, self.start_delay, self.slow = {}, 0, {}
        self.drop, self.dropped = {}, {}  # path -> how many of the next requests get no answer
        self.slow_started = threading.Event()

    def dropping(self, path):
        if self.drop.get(path):
            self.drop[path] -= 1; self.dropped[path] = self.dropped.get(path, 0) + 1
            return True
        return False


F = Fake()


class H(BaseHTTPRequestHandler):
    def reply(self, obj, code=200, ctype="application/json"):
        data = (obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)).encode("utf-8")
        self.send_response(code); self.send_header("content-type", ctype + "; charset=utf-8"); self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = dict(urllib.parse.parse_qsl(u.query))
        if u.path == "/":
            return self.reply(PAGE, ctype="text/html")
        if u.path == "/api/personas":
            return self.reply([{"key": "p0", "label": "A"}, {"key": "p1", "label": "B"}])
        if u.path == "/api/messages":
            if F.dropping(u.path):  # no answer at all, as when Chatwoot is too slow or unreachable
                return
            conv = int(q["conv"]); owner, msgs = F.convs.get(conv, (None, []))
            if owner != q["key"]:
                return self.reply({"error": "chatwoot 404"}, 502)
            if F.slow.get(conv):
                F.slow_started.set(); time.sleep(F.slow[conv])
            return self.reply(list(msgs))
        self.send_error(404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
        if F.dropping(self.path):  # never reached Chatwoot
            return
        if self.path == "/api/start":
            time.sleep(F.start_delay)
            conv = len(F.convs) + 1; F.convs[conv] = (body["key"], [])
            return self.reply({"conv": conv})
        if self.path == "/api/send":
            msgs = F.convs[body["conv"]][1]; text = body["content"]
            msgs.append({"id": len(msgs) + 1, "out": False, "content": text, "buttons": []})
            threading.Timer(0.3, lambda: msgs.append(
                {"id": len(msgs) + 1, "out": True, "content": "re: " + text, "buttons": ["x"]})).start()
            return self.reply({"ok": True})
        self.send_error(404)

    def log_message(self, *a):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=server.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:%d/" % server.server_address[1]


def shown(pg, n, timeout=6.0):
    """The bubbles' texts once there are n of them, or whatever is there when the time is up."""
    end = time.time() + timeout
    while True:
        texts = pg.evaluate("[...document.querySelectorAll('#log .m')].map(d => d.firstChild.textContent)")
        if len(texts) >= n or time.time() > end:
            return texts
        pg.wait_for_timeout(100)


def say(pg, text):
    pg.fill("#t", text); pg.press("#t", "Enter")


ok = 0
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    errors = []

    def fresh():
        pg = browser.new_page(); pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(500)
        return pg

    # 1. The 27 Oct failure: a check for new messages runs while "writing as" changes.
    F.start_delay = 1.7  # longer than the 1.5 s between checks, so one always falls inside the switch
    pg = fresh(); pg.wait_for_timeout(1500)
    pg.select_option("#who", "p1"); pg.wait_for_timeout(2500)
    F.start_delay = 0
    say(pg, "hey")
    got = shown(pg, 2)
    assert got == ["hey", "re: hey"] and not errors, "after a persona switch: shown %s, errors %s" % (got, errors)
    ok += 1; pg.close()

    # 2. A late answer for the previous conversation arrives after "new conversation".
    pg = fresh(); say(pg, "hey"); shown(pg, 2)
    old = max(F.convs); F.slow[old] = 1.2; F.slow_started.clear()
    while not F.slow_started.is_set():
        pg.wait_for_timeout(20)
    pg.click("#new"); pg.wait_for_timeout(2000)
    say(pg, "hi")
    got = shown(pg, 2)
    assert got == ["hi", "re: hi"] and not errors, "after a new conversation: shown %s, errors %s" % (got, errors)
    ok += 1; pg.close()

    # 3. One check gets no answer at all; the page carries on.
    pg = fresh(); F.drop["/api/messages"] = 1; pg.wait_for_timeout(2000)
    say(pg, "again")
    got = shown(pg, 2)
    assert F.dropped.get("/api/messages") == 1, "the stand-in should have dropped one check"
    assert got == ["again", "re: again"] and not errors, "after a check with no answer: shown %s, errors %s" % (got, errors)
    ok += 1; pg.close()

    # 4. Typed while the conversation is still being opened: it waits, it is not dropped.
    F.start_delay = 2.0
    pg = fresh(); say(pg, "hey")
    got = shown(pg, 2, timeout=8)
    F.start_delay = 0
    assert got == ["hey", "re: hey"] and not errors, "typed before the chat was open: shown %s, errors %s" % (got, errors)
    ok += 1; pg.close()

    # 5. Opening a conversation fails once: the page says so and tries again.
    F.drop["/api/start"] = 1
    pg = fresh(); pg.wait_for_timeout(1000)
    line = pg.text_content("#st")
    say(pg, "hey")
    got = shown(pg, 2, timeout=10)
    assert F.dropped.get("/api/start") == 1 and "retrying" in line, "a failed opening should say it retries: %r" % line
    assert got == ["hey", "re: hey"] and not errors, "after a failed opening: shown %s, errors %s" % (got, errors)
    ok += 1; pg.close()

    # 6. A send fails: the text comes back to the box with a line saying so, and Enter sends it.
    pg = fresh(); pg.wait_for_timeout(800)
    F.drop["/api/send"] = 1
    say(pg, "again"); pg.wait_for_timeout(1000)
    back, line = pg.input_value("#t"), pg.text_content("#st")
    assert back == "again" and "send it again" in line, "a failed send: box %r, line %r" % (back, line)
    pg.press("#t", "Enter")
    got = shown(pg, 2)
    assert got == ["again", "re: again"] and not errors, "after a failed send: shown %s, errors %s" % (got, errors)
    ok += 1; pg.close()
    browser.close()
print("check_sandbox_chat: %d/6 ok" % ok)
