"""Turn a real OXS collection report into rows the debt agent can call.

    python scripts/oxs_import.py --report "<path.xlsx>" --building "הרצל 14"
    python scripts/oxs_import.py --report "<path.xlsx>" --building "הרצל 14" --out sheets/residents-real.csv

Reads the xlsx, maps it to the `residents` schema, and writes a CSV **locally**.
It does not upload, does not touch the Google Sheet, and does not call any API.
Review the file it writes before any of that happens.

WHY THIS DOES NOT USE THE OXS API
Both key guides describe how to create keys and neither contains a base URL, an
endpoint path, or the name of the header the key travels in. There is nothing to
call. Guessing a hostname and sending a live key at it is how a credential ends
up on a stranger's server, so the export is the source until OXS supplies the
API reference.

WHAT THE REPORT DOES NOT CONTAIN
The collection report has apartment, name, phone and the debt columns. It has no
building, no gender, no card digits and no handover status. Four of those matter:

  building     — {{building}} is spoken aloud in the voicemail line. Not in the
                 report because a report IS one building; hence --building.
  gender       — {{gender}} decides how the agent ADDRESSES the resident, and
                 Hebrew marks that on every verb. Guessing it from a first name
                 is wrong often enough to be worth refusing: this leaves the
                 column blank and counts it, rather than inventing it.
  handed_over  — isEligible() in sheets/Code.gs requires TRUE. Left FALSE, which
                 means NOBODY IMPORTED HERE IS CALLABLE until it is set. That is
                 deliberate: an apartment that was never handed over must not be
                 chased for a debt, and the report cannot tell us which is which.
  card_last4   — absent, and that is fine. The prompt already branches on it
                 being empty and offers alt_payment instead.

BEFORE THE OUTPUT OF THIS SCRIPT GOES ANYWHERE NEAR THE SHEET
Read sheets/Code.gs's own header. Real names, phones and debts behind an
Access=Anyone web app, guarded by a secret that is committed to this repo and
travels in the query string, is the thing that file says must not happen.
"""

import argparse
import csv
import os
import re
import sys
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The order sheets/residents.csv uses. Kept as one list so the header and every
# row are written from the same source and cannot drift apart.
COLUMNS = ["phone", "full_name", "building", "unit", "gender", "card_last4",
           "amount", "month", "status", "attempts", "handed_over", "do_not_call",
           "alt_payment"]

# Hebrew headers in the collection report.
H_UNIT, H_NAME, H_PHONE, H_DEBT = "דירה", "שם דייר", "טלפון", "חוב להיום"
MONTHS = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
          "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]


def read_xlsx(path):
    """Rows as dicts, using the stdlib only — no pandas, no openpyxl."""
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        xml = z.read("xl/sharedStrings.xml").decode("utf-8")
        shared = [re.sub(r"<[^>]+>", "", s) for s in re.findall(r"<si>(.*?)</si>", xml, re.S)]
    sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")

    def col_index(ref):
        """'C' -> 2. The letters in a cell reference like C5."""
        letters = re.match(r"([A-Z]+)", ref).group(1)
        n = 0
        for ch in letters:
            n = n * 26 + (ord(ch) - 64)
        return n - 1

    def cells(row):
        """Values placed BY CELL REFERENCE, not by position.

        xlsx omits empty cells entirely rather than writing a blank one, so a row
        with a gap in the middle has fewer <c> elements than the header does.
        Zipping positionally therefore shifts every value after the first gap
        into the wrong column — which read as 'this resident has no debt' for
        every row below the first blank, and silently excluded them all.
        """
        out = {}
        for m in re.finditer(r"<c([^>]*)>(.*?)</c>", row, re.S):
            attrs, inner = m.group(1), m.group(2)
            ref = re.search(r'r="([A-Z]+)\d+"', attrs)
            if not ref:
                continue
            v = re.search(r"<v>(.*?)</v>", inner)
            val = v.group(1) if v else ""
            if 't="s"' in attrs and val.isdigit():
                val = shared[int(val)]
            elif 't="inlineStr"' in attrs:
                t = re.search(r"<t[^>]*>(.*?)</t>", inner, re.S)
                val = t.group(1) if t else ""
            out[col_index(ref.group(1))] = val
        return out

    raw = [cells(r) for r in re.findall(r"<row[^>]*>(.*?)</row>", sheet, re.S)]
    if not raw:
        sys.exit("No rows in %s" % path)
    header = {i: v for i, v in raw[0].items()}
    out = []
    for r in raw[1:]:
        if not any(str(v).strip() for v in r.values()):
            continue
        out.append({header.get(i, "col%d" % i): v for i, v in r.items()})
    return out


def e164(raw):
    """Israeli mobile to E.164, or None if it is not one.

    None rather than a best effort. A wrong number on a debt call means telling a
    stranger about somebody else's debt, which is worse than not calling at all —
    so anything that does not look like an Israeli number is dropped and counted.
    """
    d = re.sub(r"\D", "", str(raw or ""))
    if d.startswith("972"):
        d = d[3:]
    d = d.lstrip("0")
    if len(d) != 9 or not d.startswith("5"):
        return None            # not an Israeli mobile
    return "+972" + d


def money(raw):
    try:
        v = float(str(raw).replace(",", "").strip() or 0)
    except ValueError:
        return 0
    return int(round(v))


def latest_unpaid_month(row):
    """The last month in the year carrying a balance, which is what the agent
    should name. Falls back to None so the caller decides rather than guessing."""
    found = None
    for m in MONTHS:
        if m in row and money(row[m]) > 0:
            found = m
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True, help="path to the OXS collection xlsx")
    ap.add_argument("--building", required=True,
                    help="the building this report covers — spoken aloud, so use the real name")
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--out", help="write here; omit for a summary only")
    ap.add_argument("--show", action="store_true",
                    help="print names and numbers. Off by default: this is real personal data.")
    a = ap.parse_args()

    rows = read_xlsx(a.report)

    # A totals row carries sums and no identity. It looks like a resident with a
    # very large debt, which is the worst thing to call.
    rows = [r for r in rows if str(r.get(H_UNIT, "")).strip().isdigit()
            and str(r.get(H_NAME, "")).strip()]

    # PLACEHOLDER DETECTION, and it is the check that matters most here.
    # A scrubbed or sample export repeats one dummy number down the column. Every
    # row then looks perfectly importable, and the agent would ring the same
    # wrong number once per resident, reading each of them somebody else's debt.
    # Silently dropping the rows would hide that; so would importing them.
    seen = {str(r.get(H_PHONE, "")).strip() for r in rows if str(r.get(H_PHONE, "")).strip()}
    if len(seen) == 1 and len(rows) > 2:
        print("STOP — every phone in this report is the same value: %s" % seen.pop())
        print("That is a placeholder, not %d residents. Importing it would mean" % len(rows))
        print("calling one number repeatedly and reading it each resident's debt.")
        print("\nAsk Homies for an export with the real phone column, or supply the")
        print("numbers separately and re-run.\n")

    out, dropped_phone, dropped_nodebt, no_month = [], 0, 0, 0

    for r in rows:
        if len(out) >= a.limit:
            break
        amount = money(r.get(H_DEBT))
        if amount <= 0:
            dropped_nodebt += 1
            continue
        phone = e164(r.get(H_PHONE))
        if not phone:
            dropped_phone += 1
            continue
        month = latest_unpaid_month(r)
        if not month:
            no_month += 1
        out.append({
            "phone": phone,
            "full_name": str(r.get(H_NAME, "")).strip(),
            "building": a.building,
            "unit": re.sub(r"\D", "", str(r.get(H_UNIT, ""))),
            "gender": "",            # never guessed — see the module docstring
            "card_last4": "",
            "amount": amount,
            "month": month or "",
            "status": "unpaid",
            "attempts": 0,
            "handed_over": "FALSE",  # nobody is callable until this is confirmed
            "do_not_call": "FALSE",
            "alt_payment": "",
        })

    print("report        : %s" % os.path.basename(a.report))
    print("rows read     : %d" % len(rows))
    print("importable    : %d  (limit %d)" % (len(out), a.limit))
    print("skipped       : %d no debt, %d unusable phone" % (dropped_nodebt, dropped_phone))
    print("building      : %s   (from --building; the report does not carry it)" % a.building)
    print()
    print("FIELDS THIS REPORT CANNOT FILL, and what each costs:")
    print("  gender      : %d blank — decides how the agent addresses them, and" % len(out))
    print("                Hebrew marks it on every verb. Not guessed from names.")
    print("  handed_over : %d FALSE — isEligible() requires TRUE, so NOTHING here" % len(out))
    print("                is callable until each one is confirmed by hand.")
    print("  card_last4  : %d blank — fine. The prompt branches to alt_payment." % len(out))
    if no_month:
        print("  month       : %d blank — no month in the year carried a balance." % no_month)

    if a.show:
        print()
        for r in out:
            print("  %-14s %-22s דירה %-5s %5d ש\"ח  %s" % (
                r["phone"], r["full_name"], r["unit"], r["amount"], r["month"]))
    else:
        print("\n(names and numbers hidden — pass --show to print them)")

    if not a.out:
        print("\nNothing written. Pass --out to produce a CSV.")
        return

    path = os.path.join(ROOT, a.out) if not os.path.isabs(a.out) else a.out
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(out)
    print("\nwrote %s — %d rows" % (a.out, len(out)))
    print("\nNOT UPLOADED, and do not upload it yet. sheets/Code.gs is deployed")
    print("Access=Anyone behind a secret that is committed to this repo and rides")
    print("in the query string. That was sized for ten fictional residents.")


if __name__ == "__main__":
    main()
