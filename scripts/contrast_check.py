# -*- coding: utf-8 -*-
"""Measures every foreground/background pair the dashboard actually renders.

Colour on a dark ground is where design systems quietly fail accessibility:
a hue that clears 4.5:1 on white can sit at 3:1 on #101114, and nothing in the
browser says so. The Stovest tokens are documented as "eyeballed from
screenshots", so nothing here is taken on trust -- the pairs below are the ones
a reader looks at, composited exactly as CSS composites them (a soft pill
ground is rgba over the surface, not a flat swatch), and measured against WCAG.

Run:  python scripts/contrast_check.py            # both themes, exit 1 on a fail
"""
import io, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                  "..", "dashboard", "design-system", "tokens")

AA_BODY, AA_LARGE = 4.5, 3.0


def tokens(theme):
    """Every --var in the token files, resolved for one theme."""
    out = {}
    for f in ("colors.css", "app.css"):
        src = io.open(os.path.join(DS, f), encoding="utf-8").read()
        src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
        for block in re.finditer(r"(:root|\[data-theme=\"light\"\])\s*\{(.*?)\}", src, re.S):
            scope, body = block.group(1), block.group(2)
            if theme == "light" and scope == ":root":
                pass          # light inherits :root, then overrides
            elif theme == "dark" and scope != ":root":
                continue
            for name, value in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", body):
                out[name] = value.strip()
    return out


def rgb(value, tok, depth=0):
    """--var / #hex / rgba() -> (r, g, b, a). Follows var() chains."""
    value = value.strip()
    if value.startswith("var(") and depth < 6:
        inner = value[4:-1].split(",")[0].strip()
        return rgb(tok[inner], tok, depth + 1)
    if value.startswith("#"):
        h = value[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0
    m = re.match(r"rgba?\(([^)]+)\)", value)
    if m:
        p = [x.strip() for x in m.group(1).split(",")]
        return int(p[0]), int(p[1]), int(p[2]), float(p[3]) if len(p) > 3 else 1.0
    raise ValueError("cannot parse colour %r" % value)


def over(fg, bg):
    """Composite a translucent colour onto an opaque one, as the browser does."""
    a = fg[3]
    return tuple(round(fg[i] * a + bg[i] * (1 - a)) for i in range(3)) + (1.0,)


def lum(c):
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def ratio(fg, bg):
    a, b = lum(fg), lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


# (label, foreground token, [grounds composited outermost-last], threshold)
PAIRS = [
    ("body text on page",        "--text-1", ["--bg-0"],                  AA_BODY),
    ("body text on card",        "--text-1", ["--surface-1"],             AA_BODY),
    ("secondary text on card",   "--text-2", ["--surface-1"],             AA_BODY),
    ("secondary text on page",   "--text-2", ["--bg-0"],                  AA_BODY),
    ("secondary on sidebar",     "--text-2", ["--bg-sidebar"],            AA_BODY),
    ("micro-label on sidebar",   "--text-3", ["--bg-sidebar"],            AA_BODY),
    ("accent on card",           "--accent",     ["--surface-1"],         AA_LARGE),
    ("text on accent fill",      "--accent-fg", ["--accent-fill"],        AA_BODY),
    ("micro-label on card",      "--text-3",    ["--surface-1"],          AA_BODY),
    ("text on action fill",      "--action-fg",  ["--action"],            AA_BODY),
    ("open pill",       "--st-open",     ["--surface-1", "--st-open-bg"],     AA_BODY),
    ("progress pill",   "--st-progress", ["--surface-1", "--st-progress-bg"], AA_BODY),
    ("resolved pill",   "--st-done",     ["--surface-1", "--st-done-bg"],     AA_BODY),
    ("review pill",     "--st-review",   ["--surface-1", "--st-review-bg"],   AA_BODY),
    ("cancelled pill",  "--st-idle",     ["--surface-1", "--st-idle-bg"],     AA_BODY),
    ("urgent text on card", "--st-review", ["--surface-1"],                   AA_BODY),
    ("hero label",              "--text-2", ["--surface-2", "--accent-soft"], AA_BODY),
    ("hero number",             "--text-1", ["--surface-2", "--accent-soft"], AA_BODY),
    ("card border on page", "--border-1", ["--bg-0"],                         1.0),
]

def main():
    bad = 0
    for theme in ("dark", "light"):
        tok = tokens(theme)
        print("\n%s theme" % theme.upper())
        print("-" * 58)
        for lbl, fg, grounds, need in PAIRS:
            ground = rgb(tok[grounds[0]], tok)
            for extra in grounds[1:]:
                ground = over(rgb(tok[extra], tok), ground)
            r = ratio(over(rgb(tok[fg], tok), ground), ground)
            ok = r >= need
            bad += 0 if ok else 1
            print("  %-24s %5.2f:1  need %.1f  %s" % (lbl, r, need, "ok" if ok else "FAIL"))

    print("\n%d failing pair(s)" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
