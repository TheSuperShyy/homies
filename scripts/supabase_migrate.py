#!/usr/bin/env python
"""Run the supabase/*.sql migrations in order against the Supabase project.

Reads SUPABASE_DB_URL from .env. Each file runs inside its own transaction, so a
file either applies completely or not at all; the run stops at the first failure
rather than leaving half a schema behind.

Applied files are recorded in a schema_migrations table, so re-running is safe
and only picks up what has not been applied. That table is created here rather
than in a migration because it has to exist before the first migration runs.

    python scripts/supabase_migrate.py            # show what would run
    python scripts/supabase_migrate.py --apply    # run it
"""
import os
import sys

import psycopg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL_DIR = os.path.join(ROOT, "supabase")

LEDGER = """
create table if not exists schema_migrations (
    filename    text primary key,
    applied_at  timestamptz not null default now()
)
"""


def env():
    d = {}
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        sys.exit("No .env at %s" % path)
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def migrations():
    files = sorted(f for f in os.listdir(SQL_DIR) if f.endswith(".sql"))
    if not files:
        sys.exit("No .sql files in %s" % SQL_DIR)
    return files


def main():
    apply = "--apply" in sys.argv
    dsn = env().get("SUPABASE_DB_URL", "").strip()
    if not dsn:
        sys.exit("SUPABASE_DB_URL is empty in .env — nothing to connect to.")

    with psycopg.connect(dsn, connect_timeout=15) as conn:
        conn.execute(LEDGER)
        conn.commit()
        done = {r[0] for r in conn.execute(
            "select filename from schema_migrations").fetchall()}

        pending = [f for f in migrations() if f not in done]

        print("%d applied already, %d pending\n" % (len(done), len(pending)))
        for f in migrations():
            print("  %-28s %s" % (f, "applied" if f in done else "PENDING"))

        if not pending:
            print("\nNothing to do.")
            return
        if not apply:
            print("\nDry run. Re-run with --apply to execute the pending files.")
            return

        print()
        for f in pending:
            sql = open(os.path.join(SQL_DIR, f), encoding="utf-8").read()
            try:
                with conn.transaction():
                    conn.execute(sql)
                    conn.execute(
                        "insert into schema_migrations (filename) values (%s)",
                        (f,))
            except Exception as ex:
                print("  %-28s FAILED" % f)
                print("\n%s\n" % str(ex).strip())
                print("Stopped. %s was rolled back; earlier files stay applied."
                      % f)
                sys.exit(1)
            print("  %-28s ok" % f)

        print("\nAll %d applied." % len(pending))
        audit(conn)


# The same assertion 009 carries, run after every migration instead of once.
#
# 009 wrote it to stop a table shipping without row-level security, because 008
# had just done exactly that. It could not do its job: a migration runs once, so
# the check in 009 looked at the database as it stood on 9 August and never
# again. 016 added `buildings` and `apartments` on 13 August with no RLS, the
# anon key could read the client's whole portfolio, and nothing said a word —
# the guard had had its only turn four days earlier.
#
# A check that runs once is documentation. This is the same SQL somewhere it can
# actually see what was just applied.
#
# Warns rather than exits. By the time this runs the migrations are committed,
# so failing here would report a problem it cannot undo while implying it did;
# the fix is always another migration.
AUDIT = """
select coalesce(string_agg(c.relname, ', ' order by c.relname), '')
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind = 'r'
  and not c.relrowsecurity
  and c.relname <> 'schema_migrations'
"""


def audit(conn):
    unguarded = conn.execute(AUDIT).fetchone()[0]
    if not unguarded:
        print("RLS: every table guarded.")
        return
    print("\n!! NO ROW-LEVEL SECURITY: %s" % unguarded)
    print("!! The anon key ships in the dashboard bundle and is public by")
    print("!! design, so these tables are readable by anyone holding it.")
    print("!! Fix with a migration: alter table <name> enable row level security;")


if __name__ == "__main__":
    main()
