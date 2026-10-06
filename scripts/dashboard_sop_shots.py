#!/usr/bin/env python
"""Screenshots of the live dashboard for the staff SOP, with resident data blurred.

    python scripts/dashboard_sop_shots.py          # open Chrome, wait for a sign-in, shoot, build
    python scripts/dashboard_sop_shots.py --build  # rebuild the illustrated SOP from saved shots

A PERSON SIGNS IN, NOT THIS SCRIPT. No dashboard password is stored in this
project, and none should be. The script opens Chrome at /login and waits; the
person running it signs in by hand in that window. The session stays in a
throwaway Chrome profile in the system temp folder, never in the repo.

IT ONLY LOOKS. Every step is a page load and a screenshot. Nothing is clicked:
not a status Save, not Call, not Run import. Theme and language are cookies,
set on the throwaway profile only, so nobody else's dashboard changes.

EVERYTHING PERSONAL IS BLURRED BEFORE THE SHOT. The SOP is handed around, so
names, phone numbers, flats, addresses, emails, message text, ticket
descriptions, call summaries and photos are blurred in the page itself.
Tables are hit by their cells' `data-label`, which every dashboard table
carries. The shots go to local/sop-shots/ (gitignored) and the illustrated
SOP to the Downloads folder; neither is committed. Look at every shot before
the file goes anywhere.

THE SOP ITSELF is docs/features/13-dashboard/sop-he.html. It carries
`<!-- shot:NAME -->` markers where a picture belongs; the build swaps each for
the matching image, embedded, so the result is one file to send, and prints a
PDF beside it.
"""

import argparse
import base64
import re
import sys
import tempfile
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SOP = ROOT / "docs" / "features" / "13-dashboard" / "sop-he.html"
SHOTS = ROOT / "local" / "sop-shots"
OUT_DIR = Path.home() / "Downloads"
OUT_NAME = "Homies dashboard SOP (Hebrew)"
PROFILE = Path(tempfile.gettempdir()) / "homies-sop-chrome"
BASE = "https://homies-dashboard.vercel.app"

VIEWPORT = {"width": 1280, "height": 860}
PHONE = {"width": 390, "height": 844}
SIGN_IN_MINUTES = 15

# Column labels as the dashboard writes them in Hebrew (dashboard/lib/i18n.ts).
PRIVATE_CELLS = [
    "דייר", "טלפון", "טלפון הפונה", "איפה", "מה", "בניין", "דירה", "דירות",
    "מי", "הודעה אחרונה", "מספר", "תקציר", "מה נכתב",
]
BLUR_CSS = ",\n".join('td[data-label="%s"]' % k for k in PRIVATE_CELLS) + """,
.thumbs img, .thread .msg > div[dir="auto"], .msg[dir="auto"], .transcript,
.side .panel > div[dir="auto"], .pagehead h1[dir="auto"], .pagehead p.mono,
.voice-name, .voice-sub, .voice-amount, .voice-told,
.railgreet b, .who-block b, .who-block small, .avatar,
.setrow .val.mono, #name, .setpage img
{ filter: blur(6px) !important; }
"""
# The call page lists its facts as label/value rows with no attribute to hang
# a selector on, so the caller's number is found by its label.
BLUR_JS = """() => {
  for (const row of document.querySelectorAll('.rows .row')) {
    const k = row.querySelector('.muted');
    if (k && k.textContent.trim() === 'מספר') {
      const v = row.querySelector('.mono');
      if (v) v.style.setProperty('filter', 'blur(6px)', 'important');
    }
  }
}"""

CAPTIONS = {
    "login": "מסך הכניסה.",
    "overview": "המסך הראשי: תפריט הצד, הפס העליון, ובמרכז מסך הסקירה.",
    "mobile": "אותו מסך בטלפון: התפריט בתחתית המסך.",
    "overview-activity": "פעילות השבוע: בחירת התקופה, הטבעת והגרפים.",
    "tickets": "עמוד הקריאות: לשוניות הסטטוס למעלה, והטבלה מתחתיהן.",
    "ticket-row": "שורה של קריאה. בעמודה סטטוס: הרשימה וכפתור השמירה.",
    "debts": "עמוד החובות: לשוניות החודשים, לפי דירה או לפי בעלים, והטבלה.",
    "conversations": "רשימת שיחות הווטסאפ.",
    "thread": "שיחה אחת: בועות הדייר, מיכאל והנציג, ומתחתן הקריאות האחרונות של אותו מספר.",
    "calls": "עמוד שיחות הטלפון: הלשוניות, החיפוש במה שנאמר, והטבלה.",
    "call": "דף של שיחה: השיחה עצמה, ולצידה התקציר, הפרטים והכלים שהופעלו.",
    "search": "תוצאות חיפוש, מחולקות לקבוצות.",
    "voice": "עמוד שיחת סוכן קולי, לבדיקות בלבד.",
    "sync": "עמוד הייבוא מ-OXS.",
    "settings": "עמוד ההגדרות.",
}
NOTE = ('<p class="legend">בצילומים התצוגה בהירה, ופרטים אישיים טושטשו. התצוגה הכהה '
        'זהה בצבעים אחרים, ומחליפים ביניהן במתג שבפס העליון.</p>')


def shoot(page, name, path=None, element=None, full=False):
    """Load `path` (or stay), blur, and save `name`.jpg. Never clicks anything."""
    if path:
        page.goto(BASE + path, wait_until="networkidle")
        if "/login" in page.url:
            sys.exit("Signed out while shooting %s; run again and sign in." % name)
    page.add_style_tag(content=BLUR_CSS)
    page.evaluate(BLUR_JS)
    page.wait_for_timeout(400)
    out = SHOTS / (name + ".jpg")
    target = page.locator(element).first if element else page
    kwargs = {"path": str(out), "type": "jpeg", "quality": 85}
    if not element:
        kwargs["full_page"] = full
    target.screenshot(**kwargs)
    print("  shot", name)


def first_href(page, selector):
    link = page.locator(selector).first
    return link.get_attribute("href") if link.count() else None


def capture():
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), channel="chrome", headless=False,
            viewport=VIEWPORT, device_scale_factor=1.25, locale="he-IL",
            args=["--no-first-run", "--no-default-browser-check"],
        )
        # Light for paper, Hebrew as staff read it. This profile only.
        ctx.add_cookies([
            {"name": "homies_theme", "value": "light", "url": BASE},
            {"name": "homies_lang", "value": "he", "url": BASE},
        ])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(BASE + "/", wait_until="networkidle")
        if "/login" in page.url:
            shoot(page, "login")  # the empty form, before anybody types
            print("Sign in to the dashboard in the Chrome window. Waiting up to %d minutes."
                  % SIGN_IN_MINUTES, flush=True)
            waited = 0
            while "/login" in page.url:
                if waited > SIGN_IN_MINUTES * 60:
                    ctx.close()
                    sys.exit("No sign-in after %d minutes; nothing else was shot." % SIGN_IN_MINUTES)
                page.wait_for_timeout(1000)
                waited += 1
            page.wait_for_load_state("networkidle")
            print("Signed in. Shooting; please do not click in that window.", flush=True)

        plan = [
            ("overview", "/", None),
            ("overview-activity", None, ".panel:has(.chartcard)"),
            ("tickets", "/tickets", None),
            ("ticket-row", None, "table tbody tr"),
            ("debts", "/debts", None),
            ("conversations", "/conversations", None),
            ("calls", "/calls", None),
            ("search", "/search?q=" + urllib.parse.quote("נזילה"), None),
            ("voice", "/voice", None),
            ("sync", "/sync", None),
            ("settings", "/settings", None),
        ]
        for name, path, element in plan:
            try:
                shoot(page, name, path, element)
            except Exception as e:  # one bad page must not cost the rest
                print("  FAILED", name, str(e).splitlines()[0][:160])

        # One conversation and one call, the newest of each. The thread's URL
        # carries a phone number, so it is followed and never printed.
        for name, listing, selector in (
            ("thread", "/conversations", "td[data-label='מי'] a"),
            ("call", "/calls", "a.btn-sm[href^='/calls/']"),
        ):
            try:
                page.goto(BASE + listing, wait_until="networkidle")
                href = first_href(page, selector)
                if href:
                    shoot(page, name, href)
                else:
                    print("  none to show for", name)
            except Exception as e:
                print("  FAILED", name, str(e).splitlines()[0][:160])

        try:
            page.set_viewport_size(PHONE)
            shoot(page, "mobile", "/")
        except Exception as e:
            print("  FAILED mobile", str(e).splitlines()[0][:160])
        ctx.close()


def build():
    html = SOP.read_text(encoding="utf-8")
    missing = []

    def figure(m):
        name = m.group(1)
        f = SHOTS / (name + ".jpg")
        if not f.exists():
            missing.append(name)
            return ""
        cap = CAPTIONS.get(name, "")
        cls = "shot narrow" if name == "mobile" else "shot"
        data = base64.b64encode(f.read_bytes()).decode("ascii")
        return ('<figure class="%s"><img alt="%s" src="data:image/jpeg;base64,%s">'
                '<figcaption>%s</figcaption></figure>' % (cls, cap, data, cap))

    html = re.sub(r"<!-- shot:([a-z-]+) -->", figure, html)
    html = html.replace("<!-- shot-note -->", NOTE)
    OUT_DIR.mkdir(exist_ok=True)
    out_html = OUT_DIR / (OUT_NAME + ".html")
    out_pdf = OUT_DIR / (OUT_NAME + ".pdf")
    out_html.write_text(html, encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page()
        page.goto(out_html.as_uri(), wait_until="networkidle")
        page.pdf(path=str(out_pdf), format="A4", print_background=True,
                 prefer_css_page_size=True)
        browser.close()
    print("built", out_html.name, "and", out_pdf.name, "in", OUT_DIR)
    if missing:
        print("no shot for:", ", ".join(missing))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", action="store_true", help="rebuild from saved shots only")
    a = ap.parse_args()
    if not a.build:
        capture()
    build()


if __name__ == "__main__":
    main()
