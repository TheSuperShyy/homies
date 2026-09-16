# -*- coding: utf-8 -*-
"""Pull every page of homies-management.co.il down to readable text.

The site is WordPress + Elementor, so the content IS in the HTML -- no JS
needed. Elementor wraps everything in nested divs with long class lists, so
the trick is not parsing structure but throwing away script/style/chrome and
keeping the block-level text in order, with headings marked.

MUTING A CONTAINER NEEDS ITS DEPTH, NOT ITS NAME. The first version muted when
a div's class looked like a menu and unmuted on `</nav>`/`</header>`/`</footer>`
-- tags that never came, because the thing it muted was a div. Every page after
the first menu div came back as its title and nothing else (30-90 chars). So
every element now carries a depth, and a mute is released by the close of the
exact element that set it.
"""
import html
import io
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
os.makedirs(OUT, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
DROP = {"script", "style", "noscript", "svg", "iframe", "select", "option", "template"}
CHROME = re.compile(
    r"\b(elementor-location-header|elementor-location-footer|site-header|site-footer"
    r"|main-navigation|nav-menu|menu-item|breadcrumb|cookie|accessibility|pojo-a11y"
    r"|skip-link|screen-reader|sr-only)", re.I)
BLOCK = {"p", "div", "li", "br", "tr", "section", "article", "h1", "h2", "h3",
         "h4", "h5", "h6", "td", "th", "figcaption", "blockquote"}
HEADS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.depth = 0
        self.mutes = []          # depths at which a mute began

    def _mute(self):
        return bool(self.mutes)

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            if tag == "br" and not self._mute():
                self.out.append("\n")
            return
        self.depth += 1
        a = dict(attrs)
        cls = (a.get("class") or "") + " " + (a.get("id") or "") + " " + (a.get("role") or "")
        if tag in DROP or tag in ("nav", "header", "footer") or CHROME.search(cls):
            self.mutes.append(self.depth)
            return
        if self._mute():
            return
        if tag in HEADS:
            self.out.append("\n\n#HEAD%s#" % tag[1])
        elif tag in BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if self.mutes and self.mutes[-1] == self.depth:
            self.mutes.pop()
        elif not self._mute() and tag in HEADS:
            self.out.append("\n")
        self.depth = max(0, self.depth - 1)

    def handle_data(self, d):
        if self._mute():
            return
        d = d.strip()
        if d:
            self.out.append(d + " ")


def clean(raw):
    p = Text()
    p.feed(raw)
    t = html.unescape("".join(p.out))
    t = re.sub(r"[ \t ]+", " ", t)
    lines, blanks = [], 0
    for ln in t.split("\n"):
        ln = ln.strip()
        if not ln:
            blanks += 1
            if blanks < 2:
                lines.append("")
            continue
        blanks = 0
        m = re.match(r"^#HEAD(\d)#\s*(.*)$", ln)
        if m:
            if m.group(2):
                lines.append("\n" + "#" * int(m.group(1)) + " " + m.group(2))
            continue
        lines.append(ln)
    out, prev = [], None
    for ln in lines:                     # Elementor repeats a heading as its own anchor text
        if ln and ln == prev:
            continue
        out.append(ln)
        prev = ln
    return "\n".join(out).strip()


def slug(url):
    p = urllib.parse.unquote(urllib.parse.urlparse(url).path.strip("/")) or "home"
    return re.sub(r"[^\w֐-׿-]+", "-", p)[:70] or "home"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Language": "he-IL,he;q=0.9"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def main():
    urls = [u.strip() for u in io.open(sys.argv[1], encoding="utf-8") if u.strip()]
    index = []
    for i, u in enumerate(urls, 1):
        try:
            raw = fetch(u)
        except Exception as ex:
            print("  %2d FAIL %-50s %s" % (i, u[-50:], ex))
            continue
        m = re.search(r"<title>(.*?)</title>", raw, re.S)
        title = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else ""
        txt = clean(raw)
        name = slug(u) + ".txt"
        io.open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n").write(
            "URL: %s\nTITLE: %s\n\n%s\n" % (u, title, txt))
        index.append((name, title, len(txt), u))
        print("  %2d %-46s %6d chars  %s" % (i, name[:46], len(txt), title[:36]))
        time.sleep(0.4)
    io.open(os.path.join(OUT, "_index.txt"), "w", encoding="utf-8", newline="\n").write(
        "\n".join("%s\t%d\t%s\t%s" % (n, c, t, u) for n, t, c, u in index))
    print("\n%d pages, %d chars total" % (len(index), sum(c for _, _, c, _ in index)))


if __name__ == "__main__":
    main()
