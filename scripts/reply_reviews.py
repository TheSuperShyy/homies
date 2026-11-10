# -*- coding: utf-8 -*-
"""What reviewers sent from the dashboard's /review page (migration 040).

    python scripts/reply_reviews.py                     # every send, newest first
    python scripts/reply_reviews.py --set grok-2026-11-10
    python scripts/reply_reviews.py --csv reviews.csv   # one row per marked step, for a spreadsheet

For each send: when, how many right and wrong, then every step marked wrong or given a note, with the
tenant's message, the start of Michael's reply and the reviewer's note. Reads through the Management
API's SQL endpoint (SUPABASE_ACCESS_TOKEN in .env), the way the migrations are applied. Never prints a
set's key.
"""
import csv
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402  (its env() reads .env)


def sql(query):
    e = W.env()
    ref = e["SUPABASE_URL"].split("//")[1].split(".")[0]
    req = urllib.request.Request(
        "https://api.supabase.com/v1/projects/%s/database/query" % ref,
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": "Bearer " + e["SUPABASE_ACCESS_TOKEN"], "Content-Type": "application/json",
                 "User-Agent": "homies-scripts/1.0"},
        method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main():
    args = sys.argv[1:]
    only = args[args.index("--set") + 1] if "--set" in args else None
    if only and not only.replace("-", "").isalnum():
        sys.exit("bad --set")
    where = "where r.set_id = '%s'" % only if only else ""
    sends = sql("select r.id, r.set_id, r.marks, r.passed, r.failed, r.total, r.created_at "
                "from reply_reviews r %s order by r.created_at desc" % where)
    sets = {s["id"]: s for s in sql("select id, title, data from review_sets")}
    steps = {sid: {st["id"]: st for c in s["data"]["chats"] for st in c["steps"]} for sid, s in sets.items()}
    rows = []
    print("%d send(s)%s" % (len(sends), " for " + only if only else ""))
    for r in sends:
        print("\n%s  %s  %d right, %d wrong, of %d" % (str(r["created_at"])[:16], r["set_id"], r["passed"], r["failed"], r["total"]))
        for sid, mk in sorted(r["marks"].items(), key=lambda kv: [int(x) for x in kv[0].split(".")]):
            st = steps.get(r["set_id"], {}).get(sid, {})
            rows.append([str(r["created_at"])[:16], r["set_id"], sid, mk.get("m") or "", st.get("sent", ""),
                         " / ".join(st.get("replies", [])), mk.get("n", "")])
            if mk.get("m") == "fail" or (mk.get("n") or "").strip():
                print("  %s %s  %s" % (sid, "✗" if mk.get("m") == "fail" else ("✓" if mk.get("m") == "pass" else "·"), st.get("sent", "")))
                print("     Michael: %s" % " / ".join(st.get("replies", []))[:160].replace("\n", " "))
                if (mk.get("n") or "").strip():
                    print("     note: %s" % mk["n"].strip())
    if "--csv" in args:
        out = args[args.index("--csv") + 1]
        with open(out, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["sent_at_utc", "set", "step", "mark", "tenant_message", "michael_reply", "note"])
            w.writerows(rows)
        print("\nwrote %s (%d rows)" % (out, len(rows)))


if __name__ == "__main__":
    main()
