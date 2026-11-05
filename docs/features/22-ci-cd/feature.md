# CI/CD: checks before `main`, and the function deploys from `main`

**Estimate:** 0.5d
**Depends on:** nothing
**Status:** LIVE 5 Nov 2026 (option 2 of 3, owner: "ok"). PR #1 `33651ba`: the pipeline, the live function and its tests; first deploy v143. PR #2 `46bae91`: the first change through it.

## Purpose

Until now nothing checked code on its way to live:
- The dashboard deployed itself from `main` (Vercel), and the OXS jobs ran from `main`.
- The Edge Function, the n8n workflows and the phone agents were pushed from the PC by script, with no gate between a change and the residents.
- GitHub ran no checks, and `main` was unprotected.

This feature puts one fast check in front of `main` and makes the function deploy from `main` only.

## Behaviour

1. **CI.** `.github/workflows/ci.yml` has a job `checks` that runs on every pull request to `main` and every push to `main`. It runs only the checks that already exist:
   - `node scripts/check_function_syntax.mjs`
   - `node --test scripts/*.test.ts`
   - `python -m compileall -q scripts`
   - `python scripts/check_name_flow_test.py`
   - in `dashboard/`, `npm ci` then `npx tsc --noEmit`

   It needs no secrets, calls no live system and spends nothing.
2. **CD.** The same file has a job `deploy-function`. It runs after `checks`, on a push to `main` only, and only when that push changed `supabase/functions/debt-tools/`.
   - It runs `python scripts/supabase_functions.py --apply --code-only`.
   - It deploys the code only: no secret is pushed or deleted.
   - It fails unless the new version reads back ACTIVE.
3. **`main` is protected.**
   - Changes arrive by pull request only, with `checks` required.
   - The rule applies to admins too.
   - No force pushes, no deletion.
4. **Hand deploys only from `main`.** `supabase_functions.py --apply` refuses when the local function files differ from `origin/main`, after a fetch. It still sets secrets, such as `--oxs-mirror`, by hand, as before. Outside GitHub Actions only (`GITHUB_ACTIONS`).
5. **The way in.** Each change goes on a small branch cut from `main`, with a pull request. Not `feature/chatbot` itself: it is 557 commits ahead, and some of its dashboard files are older than `main`'s.

## Interface

`python scripts/supabase_functions.py --apply --code-only`
- reads only `SUPABASE_ACCESS_TOKEN` and `SUPABASE_URL`, from `.env` or the environment;
- uploads `index.ts`, `identity.ts`, `route.ts` and `names.ts`;
- prints the new version and its status, and exits non-zero unless it is ACTIVE.

## Data

- One new GitHub repository secret: `SUPABASE_ACCESS_TOKEN`.
- `SUPABASE_URL` is already one, for the OXS jobs.
- Nothing in the database changes.

## Acceptance

1. A pull request to `main` shows `checks`, and a red `checks` blocks the merge.
2. A direct push to `main` is refused.
3. A merge that touches the function deploys it: a new version, ACTIVE. A merge that does not touch it deploys nothing.
4. After a pipeline deploy, the function's secrets are as they were: the OXS mirror is on for the one number, and `OXS_MIRROR_TYPES` is unset.
5. The first pull request gives `main` the function exactly as it runs live (v142), its tests and the pipeline. Its deploy is a redeploy of the same code.
6. `supabase_functions.py --apply` run by hand on `feature/chatbot`, while its function differs from `main`, refuses and deploys nothing.
