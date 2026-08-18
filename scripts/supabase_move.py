#!/usr/bin/env python
"""Copy the data from the live Supabase project into the new one.

    python scripts/supabase_move.py              # dry run: compare both sides
    python scripts/supabase_move.py --apply      # copy
    python scripts/supabase_move.py --verify     # counts only, both sides

Reads the old project over its **database connection** (`SUPABASE_DB_URL`),
which is exact — real types, no JSON round-trip surprises on timestamps and
numerics. Writes the new project over **PostgREST** with `SUPABASE_NEW_SECRET_KEY`,
because no database URL exists for it yet.

SCHEMA FIRST. This copies rows and creates nothing. Run
`docs/handover/generated/supabase-schema.sql` in the new project before this,
then `supabase-ledger.sql`.

WHY THE ORDER IS DERIVED AND NOT WRITTEN DOWN
The order in the migration plan was `residents -> charges -> requests ->
interactions`, which cannot work: `requests.interaction_id` references
`interactions`, so requests must come after. Rather than correct one hand-typed
list into another hand-typed list, TABLES below is a topological sort of the
real foreign keys, checked against the live database. Twenty FK constraints
across twelve tables is more than anyone should be holding in their head.

IDs ARE CARRIED ACROSS VERBATIM. Every primary key is copied as-is, because
`requests.interaction_id`, `messages.interaction_id` and six other columns point
at them. Letting the new project mint fresh uuids would silently orphan every
one of those references — the copy would report success and the joins would
return nothing.

RE-RUNNABLE. Writes go through PostgREST upsert on the primary key, so an
interrupted run is resumed by running it again rather than by cleaning up.

The old project is never written to. This opens one read-only connection to it.
"""
import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import psycopg

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Topological order over the live foreign keys. Parents before children.
# `schema_migrations` is deliberately absent: the ledger is written by
# supabase-ledger.sql alongside the schema, and copying it from here would race
# with that.
TABLES = [
    "buildings",
    "apartments",
    "residents",
    "charges",
    "interactions",
    "call_outcomes",
    "messages",
    "payment_disputes",
    "payment_links",
    "payment_tickets",
    "promises_to_pay",
    "requests",
]

CHUNK = 500          # rows per PostgREST call; 4,000 in one body times out


def env():
    d = {}
    for line in io.open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


E = env()


def jsonable(v):
    """psycopg hands back real Python types; PostgREST wants JSON."""
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, (dict, list)) or v is None or isinstance(v, (str, int, float, bool)):
        return v
    return str(v)


def new_rest(method, path, payload=None, prefer=None):
    url = E["SUPABASE_NEW_URL"] + "/rest/v1/" + path
    key = E["SUPABASE_NEW_SECRET_KEY"]
    headers = {
        "apikey": key, "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "User-Agent": "homies-supabase-move/1.0",
    }
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(
        url, method=method,
        data=json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        if payload is not None else None,
        headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read().decode("utf-8")
        return r.headers, (json.loads(body) if body.strip() else [])


def new_count(table):
    """Rows in the target, or None when the table is not there yet."""
    try:
        h, _ = new_rest("GET", "%s?select=*&limit=0" % table,
                        prefer="count=exact")
        return int((h.get("content-range") or "*/0").split("/")[-1])
    except urllib.error.HTTPError as e:
        if e.code in (404, 400):
            return None
        raise


def pk_of(conn, table):
    """The primary-key columns of public.<table>.

    JOINED ON constraint_schema AS WELL AS constraint_name, and that is the
    whole point of this docstring. Constraint names are only unique within a
    schema, and Supabase ships `realtime.messages` whose primary key is also
    called `messages_pkey` — partitioned, so its key is (id, inserted_at).

    Without the schema in the join, asking for the key of `public.messages`
    returns `id, id, inserted_at`: our column, theirs, and a partition key that
    exists on neither. The upsert URL then names `inserted_at`, PostgREST
    answers `column "inserted_at" does not exist`, and the failure points at the
    target table rather than at the query that produced it. Cost an hour on
    13 Aug. `messages` is the only table here whose name collides with a
    Supabase-internal one, which is why nothing else ever showed it.
    """
    row = conn.execute("""
        select kcu.column_name
        from information_schema.table_constraints tc
        join information_schema.key_column_usage kcu
          on  kcu.constraint_name   = tc.constraint_name
          and kcu.constraint_schema = tc.constraint_schema
        where tc.table_schema='public' and tc.table_name=%s
          and tc.constraint_type='PRIMARY KEY'
        order by kcu.ordinal_position
    """, (table,)).fetchall()
    return [r[0] for r in row]


def read_all(conn, table):
    cur = conn.execute('select * from "%s"' % table)
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, (jsonable(v) for v in r))) for r in cur.fetchall()]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--only", metavar="TABLE", help="one table, for a retry")
    args = p.parse_args()

    for k in ("SUPABASE_DB_URL", "SUPABASE_NEW_URL", "SUPABASE_NEW_SECRET_KEY"):
        if not E.get(k):
            sys.exit("%s is empty in .env" % k)

    print("from : %s" % E["SUPABASE_URL"].split("//")[-1])
    print("to   : %s\n" % E["SUPABASE_NEW_URL"].split("//")[-1])

    tables = [args.only] if args.only else TABLES
    conn = psycopg.connect(E["SUPABASE_DB_URL"], connect_timeout=20)
    try:
        print("  %-22s %8s %8s" % ("table", "source", "target"))
        plan = []
        missing = []
        for t in tables:
            src = conn.execute('select count(*) from "%s"' % t).fetchone()[0]
            dst = new_count(t)
            print("  %-22s %8d %8s" % (t, src, "—" if dst is None else dst))
            if dst is None:
                missing.append(t)
            plan.append((t, src, dst))

        if missing:
            print("\nThese tables do not exist in the target: %s" % ", ".join(missing))
            print("Run docs/handover/generated/supabase-schema.sql there first.")
            if args.apply:
                sys.exit(1)

        if args.verify:
            bad = [(t, s, d) for t, s, d in plan if d is not None and d != s]
            print("\n%s" % ("counts match on every table"
                            if not bad else
                            "MISMATCH: " + ", ".join("%s %d/%d" % (t, d, s) for t, s, d in bad)))
            return
        if not args.apply:
            print("\nDry run. Re-run with --apply to copy.")
            return

        print()
        for t, src, dst in plan:
            if src == 0:
                print("  %-22s empty, skipped" % t)
                continue
            pk = pk_of(conn, t)
            if not pk:
                print("  %-22s NO PRIMARY KEY — skipped, cannot upsert safely" % t)
                continue
            rows = read_all(conn, t)
            sent = 0
            for i in range(0, len(rows), CHUNK):
                chunk = rows[i:i + CHUNK]
                try:
                    new_rest("POST", "%s?on_conflict=%s" % (t, ",".join(pk)), chunk,
                             prefer="resolution=merge-duplicates,return=minimal")
                except urllib.error.HTTPError as e:
                    print("  %-22s FAILED at row %d" % (t, i))
                    print("    HTTP %s %s" % (e.code, e.read().decode("utf-8")[:400]))
                    print("\nStopped. Fix, then re-run — writes upsert, so"
                          " finished tables are not duplicated.")
                    sys.exit(1)
                sent += len(chunk)
                if len(rows) > CHUNK:
                    print("  %-22s %d/%d" % (t, sent, len(rows)))
            after = new_count(t)
            ok = "ok" if after == src else "!! %d in target, expected %d" % (after, src)
            print("  %-22s %d copied  %s" % (t, sent, ok))
    finally:
        conn.close()

    print("\nDone. Re-run with --verify to confirm counts, and remember the"
          " Edge Function and .env still point at the old project.")


if __name__ == "__main__":
    main()
