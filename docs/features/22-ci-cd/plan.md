# CI/CD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans (inline) to run this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** one fast check in front of `main`, and the Edge Function deploying itself from `main`, code only.

**Architecture:**
- One workflow, `.github/workflows/ci.yml`, with two jobs: `checks` runs the existing offline checks, and `deploy-function` runs `supabase_functions.py --apply --code-only` after a push to `main` that touched the function.
- `main` is protected: a pull request with `checks` green is the only way in.
- The hand-run deploy script refuses function code that `main` does not hold.

**Tech stack:** GitHub Actions, Node 24 (`node --test`, `stripTypeScriptTypes`), Python 3.12, the Supabase Management API, `gh`.

## Global Constraints

- Only checks that already exist. No new test suites, no live calls, no spend (owner, 5 Nov: "dont overtest").
- The pipeline never pushes or deletes a function secret.
- `ClixTeam579` gets write access. `TheSuperShyy` is used only for the one-time admin settings, then `gh` switches back.
- Tokens are never printed. `SUPABASE_ACCESS_TOKEN` goes from `.env` into `gh secret set` on stdin.
- The required check name is `checks` (GitHub Actions app id 15368).

---

### Task 1: `supabase_functions.py`: `--code-only`, and the main-only guard

**Files:** Modify `scripts/supabase_functions.py`.

**Produces:**
- `--apply --code-only` deploys `index.ts`, `identity.ts`, `route.ts` and `names.ts` with no secret touched, and exits non-zero unless the version reads ACTIVE.
- `--apply`, outside GitHub Actions, exits before any network write when a function file differs from `origin/main`.

- [ ] `env()` reads `.env` when it exists, and takes `SUPABASE_ACCESS_TOKEN` and `SUPABASE_URL` from the process environment when it does not.
- [ ] Add `differs_from_main()`. It runs `git fetch origin main`, then compares each function file with `git show origin/main:<path>`, line endings normalised, and returns the paths that differ.
- [ ] In `main()`, if `--apply` and not `GITHUB_ACTIONS` and `differs_from_main()` is non-empty, exit with "REFUSED".
- [ ] Factor the deploy POST into `deploy_code(token, ref, url, files)`. It exits non-zero unless the status is ACTIVE.
- [ ] Add the `--code-only` branch, before any `TOOL_SECRET` or secret work.
- [ ] Check:
  - `python scripts/supabase_functions.py --code-only` prints "code only" and "Dry run".
  - `python scripts/supabase_functions.py --apply --code-only` on `feature/chatbot` (its function differs from `main` today) prints REFUSED and deploys nothing.

### Task 2: `.github/workflows/ci.yml`

**Files:** Create `.github/workflows/ci.yml`.

- [ ] `checks`, on pull requests to `main` and pushes to `main`:
  - checkout;
  - Node 24, with an npm cache on `dashboard/package-lock.json`;
  - Python 3.12;
  - `node scripts/check_function_syntax.mjs`;
  - `node --test scripts/*.test.ts`;
  - `python -m compileall -q scripts`;
  - `python scripts/check_name_flow_test.py`;
  - in `dashboard/`, `npm ci` then `npx tsc --noEmit`.
- [ ] `deploy-function`:
  - runs after `checks`, and only on a push to `main`;
  - checks out with `fetch-depth: 0`;
  - works out from `git diff --quiet $BEFORE $GITHUB_SHA -- supabase/functions/debt-tools` whether the function changed. An empty, zero or unknown `$BEFORE` counts as changed;
  - when it changed, runs `python scripts/supabase_functions.py --apply --code-only`, with the two secrets in env;
  - `concurrency: deploy-function`.
- [ ] Check: the file parses with PyYAML.

### Task 3: the first pull request: pipeline, the live function and its tests

**Files**, on a branch `ci-pipeline` cut from `origin/main`. Each comes over from `feature/chatbot`'s HEAD:
- `.github/workflows/ci.yml`;
- `scripts/supabase_functions.py`;
- `supabase/functions/debt-tools/{index,identity,route,names}.ts`, which is live v142;
- `supabase/functions/debt-tools-sandbox/guard.ts`, which `check_sandbox_guard.test.ts` imports;
- `scripts/check_function_syntax.mjs` and `scripts/check_{dialer,identity,names,route,sandbox_guard}.test.ts`;
- `scripts/check_name_flow.py` and `scripts/check_name_flow_test.py`;
- `docs/features/22-ci-cd/*`.

Steps:
- [ ] Build it in a temporary worktree, and run the five check commands there once, on `main`'s dashboard. `check_route.test.ts` reads `dashboard/lib/call.ts` and `check_dialer.test.ts` reads `dashboard/lib/dialer-rules.ts`, and `main`'s versions of both differ from `feature/chatbot`'s. Commit.

### Task 4: GitHub, once, as TheSuperShyy

- [ ] `gh auth switch -u TheSuperShyy`.
- [ ] `PUT repos/TheSuperShyy/homies/collaborators/ClixTeam579` with `permission=push`. Accept the invitation as `ClixTeam579`.
- [ ] `gh secret set SUPABASE_ACCESS_TOKEN`, value from `.env`, on stdin. Confirm `SUPABASE_URL` is listed.
- [ ] Push `ci-pipeline` and open the pull request. Wait for `checks`.
- [ ] Once `checks` is green, `PUT .../branches/main/protection`:
  - `required_status_checks {strict: false, checks: [{context: "checks", app_id: 15368}]}`;
  - `enforce_admins: true`;
  - `required_pull_request_reviews {required_approving_review_count: 0}`;
  - `restrictions: null`;
  - no force pushes, no deletion.
  
  Read it back.
- [ ] `gh auth switch -u ClixTeam579`.

### Task 5: merge, and watch the first deploy

- [ ] `gh pr merge --merge` as `ClixTeam579`. On `main`, `checks` then `deploy-function` run.
- [ ] Read back:
  - the function's new version is ACTIVE;
  - the function's secret names still include `OXS_KEY_REQUESTS` and `OXS_MIRROR_PHONES`, and not `OXS_MIRROR_TYPES`.

### Task 6: the second pull request: the OXS sync fix

- [ ] Rebase `sync-mirror-close-for-main` onto the new `main`, push it, open the pull request, wait for `checks`, merge. No function change, so no deploy. The scheduled OXS job uses it from its next run.

### Task 7: briefing

- [ ] Update:
  - CONTEXT: the rule that live code goes through a pull request and the function deploys from `main`;
  - HANDOVER: the status;
  - WORKLOG: the entry;
  - feature 22's status and the README row;
  - a memory note.
  
  Commit on `feature/chatbot`.
