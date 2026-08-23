# -*- coding: utf-8 -*-
"""Auto-housekeeping: commit and push the briefing files and docs.

This repository is PUBLIC, so nothing is committed blind: only the briefing
files and docs/ are staged, and the staged diff's ADDED lines are scanned for
real phone numbers and key-shaped strings before any commit. A hit unstages
everything and reports instead of committing — a human then looks.

Allowed on purpose: the office line 077-6687949 (public), the synthetic test
phones 9725099020xx (fake by construction), and OXS ticket references like
255-1013-26 (not personal data).

Runs as a Stop hook after every Claude Code turn; exits 0 always so it never
blocks the session. Prints hook JSON ({"systemMessage": ...}) only when it
did something or found something.
"""
import json
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TARGETS = ["CONTEXT.md", "HANDOVER.md", "docs"]

SECRET_PATTERNS = [
    (r"\bsk[-_][A-Za-z0-9_-]{8,}", "sk_-style API key"),
    (r"\beyJ[A-Za-z0-9_-]{20,}", "JWT-shaped token"),
    (r"\bwhsec_[A-Za-z0-9]{10,}", "webhook secret"),
    (r"(?i)\b(api[_-]?key|secret|token|password)\b['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9+/_-]{16,}",
     "key=value credential"),
]
PHONE_PATTERNS = [
    (r"\+?972[-\s]?5\d[-\s]?\d{3}[-\s]?\d{4}", "Israeli mobile"),
    (r"\b05\d[-\s]?\d{3}[-\s]?\d{4}\b", "Israeli mobile"),
    (r"\+63\s?\d{9,10}", "PH mobile"),
]
SYNTHETIC = re.compile(r"9725099020\d\d")


def run(*args):
    return subprocess.run(["git", *args], capture_output=True, cwd=None)


def out(msg):
    print(json.dumps({"systemMessage": msg}, ensure_ascii=False))


def main():
    run("add", "--", *TARGETS)
    diff = run("diff", "--cached", "--unified=0")
    text = diff.stdout.decode("utf-8", errors="replace")
    added = [l[1:] for l in text.splitlines()
             if l.startswith("+") and not l.startswith("+++")]
    if not added:
        return  # nothing staged, stay silent

    findings = []
    for line in added:
        for pat, label in SECRET_PATTERNS:
            for m in re.finditer(pat, line):
                findings.append((label, m.group(0)[:24] + "…"))
        for pat, label in PHONE_PATTERNS:
            for m in re.finditer(pat, line):
                digits = re.sub(r"\D", "", m.group(0))
                if SYNTHETIC.fullmatch(digits) or SYNTHETIC.search(digits):
                    continue
                findings.append((label, m.group(0)))

    if findings:
        run("reset", "-q", "--", *TARGETS)
        uniq = sorted({f"{lbl}: {frag}" for lbl, frag in findings})[:6]
        out("Housekeeping BLOCKED — staged docs contain data that must not "
            "reach the public repo: " + "; ".join(uniq) +
            ". Nothing was committed; clean the files first.")
        return

    stat = run("diff", "--cached", "--stat")
    n_files = len([l for l in stat.stdout.decode("utf-8", "replace").splitlines()
                   if "|" in l])
    c = run("commit", "-m",
            "Housekeeping: briefing files and docs kept current (auto)\n\n"
            "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>")
    if c.returncode != 0:
        out("Housekeeping: commit failed — " +
            c.stderr.decode("utf-8", "replace")[:200])
        return
    p = run("push")
    if p.returncode != 0:
        out(f"Housekeeping: committed {n_files} doc file(s); push failed "
            "(will ride along next time) — " +
            p.stderr.decode("utf-8", "replace")[:150])
    else:
        out(f"Housekeeping: committed and pushed {n_files} doc file(s).")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never block the session
        out("Housekeeping: error — " + str(e)[:200])
    sys.exit(0)
