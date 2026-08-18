# Moving Homies to a new Supabase project

**Written 12 Aug. The DATABASE MOVE IS DONE as of 13 Aug — schema and every
row are in the target and verified. Production still points at the old
project.**

| | Live (still serving) | Target (loaded, idle) |
|---|---|---|
| Project ref | `nmxlhlmcnnggnnuxyelt` | `tfldjbwtghfgdwoyauio` |
| Owner | our account | **yariv@homies-management.co.il** |
| Region | ap-northeast-1 (Tokyo) | **ap-northeast-2 (Seoul)** |
| Schema | 001–019 | 001–019, ledger written |
| Data | source of truth | every table, counts matched |
| Edge Function | v17 ACTIVE | **not deployed** |
| Pointed at by | n8n, Vapi, dashboard | nothing |

**How the access blocker was solved.** Not with a connection string. A personal
access token (`sbp_…`) on the target account, plus the Management API's
`POST /v1/projects/{ref}/database/query`, which runs SQL directly — so
`SUPABASE_NEW_DB_URL` was never needed and is still a placeholder in `.env`.

**Region is the open decision.** Seoul is no closer to Israel than Tokyo, and a
project's region is fixed at creation. This move is worth doing for **ownership**
— the client holding their own data — but it does not improve latency, and the
voice agent makes tool calls mid-conversation. `eu-central-1` is ~2,700 km from
Tel Aviv against ~9,000. Decide before repointing production; afterwards it
means migrating live data a second time.

What was done on 13 Aug:

- **`generated/supabase-schema.sql` regenerated** — it covered 001–013 and was
  five migrations stale. Now 001–019, 87,774 characters.
- **`generated/supabase-ledger.sql` added.** Without it `supabase_migrate.py`
  replays all seventeen files against the new project.
- **The schema was actually run and verified** — see "Verifying the schema"
  below. It found a live security bug, now fixed as migration 019.
- **`scripts/supabase_move.py` written** — the data copy, re-runnable, with the
  table order derived from the real foreign keys rather than typed by hand.
  Dry-run works and correctly refuses because the target has no tables.

The two key styles differ in wording but not in role: `sb_publishable_` is
the new `anon`, `sb_secret_` is the new `service_role`.

## What is actually being moved

Counted on the live project **13 Aug** (the 12 Aug numbers are superseded):

| Table | Rows | Notes |
|---|---|---|
| `residents` | **7,391** | real names, real E.164 mobiles. The one irreplaceable table |
| `apartments` | 4,092 | new 13 Aug — the OXS flat list, incl. 138 named units |
| `messages` | 306 | WhatsApp chat log, both directions |
| `buildings` | 193 | new 13 Aug — 173 active, 20 disabled and carried |
| `charges` | 179 | one row per apartment per unpaid month |
| `interactions` | 119 | call and chat records, transcripts, `latency_ms` |
| `requests` | 53 | maintenance tickets |
| `call_outcomes` | 34 | how each call ended |
| `schema_migrations` | 19 | the ledger that says which migrations ran |
| `payment_links`, `payment_tickets`, `promises_to_pay`, `payment_disputes` | 0 | built, never used |

`buildings` and `apartments` are re-derivable — `python
scripts/oxs_buildings_sync.py --apply` rebuilds both from OXS in about four
minutes — so they are convenience, not risk.

Views (`v_conversations`, `v_debt_call_queue`, `v_debt_call_queue_person`,
`v_pending_payment_tickets`) and functions (`bump_charge_attempt`,
`hebrew_list`, `money_say`) are rebuilt by the schema, not copied.

**`residents` is the risk.** Everything else can be regenerated — tickets are
test data, charges come from an OXS re-import, the chat log is history. 7,391
residents with phone numbers came out of OXS over several runs and their
`handed_over` flags are the safety interlock.

## Step 1 — schema  ·  **DONE 13 Aug**

Run straight against the target through the Management API's
`database/query` endpoint, one migration at a time so a failure names itself;
all seventeen returned ok, then the ledger. The paste-it-yourself route below
is still accurate and is the fallback if the token is ever unavailable.

`docs/handover/generated/supabase-schema.sql` — migrations 001–019 in order,
87,774 characters. Paste it into the target project's SQL editor and run once.
Then paste `generated/supabase-ledger.sql` and run that too, or
`supabase_migrate.py` will try to replay all seventeen files.

**002 and 005 are deliberately excluded.** They seed demo residents and demo
charges, and both were purged from the live database on 10 August. A fresh
project should not be born holding the rows somebody deliberately deleted.

Regenerate with the snippet at the bottom of this file if a migration is added.

### Verifying the schema, which is worth doing and is not obvious

Running it against the live database proves nothing: every migration is
`create ... if not exists`, so on a database where the objects already exist
they all no-op, and the run is green without having tested anything — least of
all the thing that matters, which is whether the file works on a project with
nothing in it.

The trick is a throwaway schema first on the `search_path`, inside a
transaction that is always rolled back. Unqualified `create table` lands in it,
and unqualified references resolve to it, so it behaves as an empty database
while touching nothing:

```python
cur.execute("create schema _migtest")
cur.execute("set local search_path = _migtest, public")
cur.execute(open("docs/handover/generated/supabase-schema.sql").read())
# ... count what appeared in _migtest ...
conn.rollback()
```

Result on 13 Aug: **12 tables, 5 views, 5 functions, no table without RLS.**

**It failed the first time, and the failure was real.** 009 carries an
assertion that raises if any table in `public` lacks row-level security, and it
fired: `buildings` and `apartments` — created that morning by 016 — had none,
so the anon key that ships in the dashboard's browser bundle could read the
client's entire portfolio. Confirmed against the live project before fixing it,
not assumed. Migration **019** turns RLS on for both, with no anon policy,
because nothing in the dashboard reads them.

009's guard could not have caught this on its own: a migration runs once, so it
looked at the database as it stood on 9 August and never again. The same
assertion now runs in `scripts/supabase_migrate.py` after **every** run, where
it can see what was just applied.

## Step 2 — data  ·  **DONE 13 Aug**

Every table copied, counts matched both sides on a `--verify` pass.

**`scripts/supabase_move.py`.**

```
python scripts/supabase_move.py            # compare both sides, write nothing
python scripts/supabase_move.py --apply    # copy
python scripts/supabase_move.py --verify   # counts only
```

It reads the old project over `SUPABASE_DB_URL` — exact types, no JSON
round-trip surprises on timestamps and numerics — and writes the new one over
PostgREST with `SUPABASE_NEW_SECRET_KEY`, because that project has no database
URL yet. Writes are upserts on the primary key, so an interrupted run is
resumed by running it again.

**The order in the first draft of this document was wrong**, and it is worth
recording why. It said `residents → charges → requests → interactions`, which
cannot work: `requests.interaction_id` references `interactions`, so requests
must come last, not third. There are twenty foreign-key constraints across
twelve tables — more than anyone should hold in their head — so the script
sorts them topologically from the live catalogue instead of trusting a typed
list:

    buildings → apartments → residents → charges → interactions →
    call_outcomes → messages → payment_* → requests

**IDs are carried across verbatim.** Eight columns point at other tables' keys;
letting the new project mint fresh uuids would orphan every one of them, and
the copy would report success while the joins returned nothing.

**The one bug the real run found.** `messages` refused every row with
`column "inserted_at" does not exist`, on a table whose columns were identical
on both sides — the column belongs to neither. `pk_of()` joined
`table_constraints` to `key_column_usage` on `constraint_name` alone, and
constraint names are unique only within a schema: Supabase ships
`realtime.messages`, partitioned, whose primary key is also `messages_pkey` and
is `(id, inserted_at)`. The primary key of `public.messages` therefore came back
as `id, id, inserted_at`. Fixed by joining on `constraint_schema` as well.
`messages` is the only table here whose name collides with a Supabase-internal
one, which is why eleven tables copied cleanly first.

**Verify by count, never by the absence of errors.** A partial copy raises
nothing. `--verify` does exactly this comparison.

## Step 3 — the Edge Function

`supabase/functions/debt-tools` has to be deployed to the new project and its
secrets set: `TOOL_SECRET` at minimum, plus whatever `index.ts` reads. It is the
tool endpoint for both voice agents and the WhatsApp bot's writer, so nothing
works until it is live and answering.

Deploying needs the Supabase CLI or a personal access token **for the new
account** — see "What is still needed".

## Step 4 — repoint, in this order

Everything below currently names the old project by URL. None of it fails
loudly if missed: the old project keeps answering, so a half-migrated system
looks healthy while writing to two databases.

| What | Where | Holds |
|---|---|---|
| `.env` | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_DB_URL`, `SUPABASE_ACCESS_TOKEN` | every script in `scripts/` |
| n8n credential | `Homies Supabase service key` | the WhatsApp bot's two log nodes |
| n8n workflows | `Homies — WhatsApp bot`, `Homies — debt tools (Vapi)`, `Homies — call queue (read)` | the function URL is baked into node parameters — re-run each `n8n_*.py --apply` |
| Vapi, both Hebrew assistants | `server.url` + `server.headers` | the end-of-call report. Restored by `vapi_sync.py --apply`, never by hand |
| Dashboard | Vercel environment | its own read path |

**n8n has no PATCH for credentials.** Changing the Supabase key there means
creating a new credential and re-pushing the workflows, exactly as the
OpenRouter key change did on 12 Aug.

## Step 5 — verify, then stop using the old one

```
python scripts/check_tools.py        # 10 tools, writes must land
python scripts/check_whatsapp.py     # posts a real signed message, looks for the row
```

Then a web call from `homies-voice-demo.vercel.app` and confirm a row appears in
`interactions` with a transcript. That row arrives after the call ends, which is
why it is checked last.

**Do not delete the old project.** Leave it untouched until the new one has
carried real traffic for a week. It costs nothing to keep and it is the only
rollback.

## What is still needed

All three are for the **new account**, which is not the account
`SUPABASE_ACCESS_TOKEN` belongs to — verified 13 Aug by asking it for its
project list, which returns one entry, HOMIES.

1. **Somebody to run the schema in the target's SQL editor** — or, instead, the
   target's database connection string, which lets a script do it. This is the
   only thing blocking everything else, and the dashboard route needs no new
   credential at all.
2. **The target's database password or connection string** — nice to have for
   the copy, though `supabase_move.py` writes over PostgREST and does not
   require it.
3. **A personal access token on the target's account** (`sbp_…`) — for
   deploying the Edge Function and setting its secrets by API. Without it the
   function has to be deployed from a machine logged into that account.

The data copy itself is **not** blocked on 2 or 3: it needs only step 1.

Also worth answering before cutover: **which region the new project is in.** The
live one is Tokyo, which is already a strange choice for Israeli residents and
an Oregon-or-EU Vapi account. Migrating is the cheapest moment to fix it, and
the most expensive moment to get it wrong twice.

## Regenerating the schema file

```python
python - <<'PY'
import io, os
SRC, SKIP = "supabase", {"002_slice_seed.sql", "005_debt_seed.sql"}
files = [f for f in sorted(os.listdir(SRC)) if f.endswith(".sql")
         and f not in SKIP and f != "schema.sql"]
parts = []
for f in files:
    s = io.open(os.path.join(SRC, f), encoding="utf-8").read()
    parts.append("\n\n-- %s\n\n%s\n" % (f, s.strip()))
io.open(os.path.join(SRC, "schema.sql"), "w", encoding="utf-8",
        newline="\n").write("".join(parts))
print("wrote", len(files), "files")
PY
```
