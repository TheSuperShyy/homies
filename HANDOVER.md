# Handover — OXS API and the missing phone numbers

Written 2026-08-10 to carry this thread into a new session. The question being
worked: **can we pull residents' real mobile numbers from OXS?**

## Where things stand

**Short answer: entitled on paper, nothing to call yet.**

- The 12 real residents in Supabase (`source='oxs'`) carry **synthetic phones**
  (`+972500000001`–`+972500000012`). The real OXS collection report had one
  placeholder number repeated down the whole טלפון column, so the import ran
  with `--test-phones`. Real names, real debts, fake phones.
- All three OXS API keys are now filled in `.env` (70-char opaque `oxs_k_…`
  tokens, nothing decodable in them):
  | Key | Module | Access | Exposes |
  |---|---|---|---|
  | `OXS_KEY_GENERAL` | General Information | Read-only | Buildings, apartments, **residing tenants (phones live here)**, payment histories |
  | `OXS_KEY_DEBTS` | Tenant Debts | Read-only | Balances, payment details, outstanding amounts |
  | `OXS_KEY_REQUESTS` | Service Requests | Read-only **or** Full Control | View tickets; create/update/delete only if issued Full Control |
- **UPDATE 2026-08-10: the API host is found and verified.** `api.oxs.co.il`
  resolves and presents a valid Amazon-issued cert for `*.oxs.co.il`
  (CN=oxs.co.il) — proven OXS, not guessed. `/swagger.json` there returns a
  real `401 Not Authorized` unauthenticated (every unknown path returns the
  4285-byte SPA instead), so a genuine key-gated API spec sits behind it. The
  only thing left is one authenticated GET, which the Claude Code classifier
  won't let this session send (it blocks transmitting the key). Run
  `python scripts/oxs_probe.py` locally to make that call. It answers the only
  question that matters — whether a *populated* mobile comes back, not merely
  whether a phone field exists — with one of four verdicts: POPULATED,
  PLACEHOLDER (filled but all identical: the same dead end as the last export),
  EMPTY, or ABSENT. Sample numbers print masked.
  The guide PDF still documents none of this — it's four pages of key
  management only.

## Decisions in force

- **OXS is read-only, forever.** Import to clone into Supabase; never write.
  `create_staff_task` exists because of this. If a design needs an OXS write,
  the design is wrong.
- **The user wants `OXS_KEY_REQUESTS` re-issued as Read-Only.** That happens on
  the OXS access-levels page (only place a key's level is set); when the new
  key is pasted into `.env`, verify it (length check, don't print values).
- Phone is a **join key only** — nothing dials it. Web calls only; no phone
  numbers owned.

## Next actions (either of the first two unblocks phones)

1. **Email OXS Support** (support@oxs.co.il / +972 3-679-7269) for the API
   reference. **Draft ready to send** —
   `docs/reference/Homies-OXS-Support-Email.md`, English and Hebrew. Asks for
   base URL, auth header, routes, tenant/debt field names, whether the tenants
   endpoint returns the mobile number, and API-activation confirmation.
2. **Or get a re-export** with the real phone column populated, then re-run
   `scripts/oxs_import.py` without `--test-phones` →
   `scripts/import_oxs_csv.py --apply`.
3. **Before re-importing with real phones:** run
   `scripts/oxs_purge_synthetic.py --apply` (script written 2026-08-10,
   dry-run verified: 12 residents, 9 charges, cascade handles the charges).
   Residents upsert on `phone`, so skipping this duplicates all 12 people.

## Operational facts from the guide (matter later)

- Rate limits: 60 req/min, 1,000 req/hr, **shared across all keys** — shapes
  paging ~10,000 apartments.
- Every key expires: 1 year default, 2 max; reminders at 30/7/1 days. An
  expired key looks exactly like an outage.
- Rotation has a 24-hour overlap window; deactivating API service kills all
  keys instantly.

## Files that matter

- `scripts/oxs_import.py` — xlsx collection report → CSV; placeholder-phone
  STOP check; `--test-phones` / `--assume-handed-over` are test-only flags.
- `scripts/import_oxs_csv.py` — CSV → Supabase; upsert residents on phone,
  charges on (resident_id, period); rows marked `source='oxs'`.
- `supabase/OXS_API_Keys_Guide_EN (1).pdf` — the only OXS API document we have.
- `docs/WORKLOG.md` — 2026-08-10 entry (keys complete) and the 2026-08-05
  entries (import, read-only decision, no-endpoints finding).
