# CI/CD — context

## Why this exists

On 5 Nov 2026 the owner was asked to push the OXS sync fix (Yariv's change 1) to `main`, and answered: *"we need a ci/cd before pushing live"*. Then, on the plan: *"dont overtest tho since your test is overkill"*.

The same day, the Edge Function had gone live by hand from `feature/chatbot` (v142), with no gate.

## Decisions

**Option 2 of three.** The options were:
1. checks only;
2. checks, plus the function deploys itself from `main`;
3. everything through a sandbox stage first.

The owner took the recommendation. Option 1 left the hand deploy, the riskiest step, as it was. Option 3 is several days of work for the n8n and phone-agent parts, which already have their own gates.

**Only checks that already existed.** "dont overtest". New test suites, live probes (`check_whatsapp_rules.py` reads the live n8n) and the sandbox stage were all left out. Every check here passed on 5 Nov, so the pipeline started green.

**The deploy carries code, never secrets.**
- The pipeline needs one secret, the deploy token.
- The function's own settings, the OXS mirror's switches among them, stay with the hand-run script and its explicit flags. So the pipeline can never turn the mirror on.
- Rejected: copying all twelve function secrets into GitHub. That means more exposure, and the mirror's on/off state would then live in two places.

**Hand deploys refuse code that is not on `main`.** Without the guard, a hand deploy from `feature/chatbot` goes around the pipeline, which is exactly what happened with v142. Secrets still go by hand, but only from a checkout whose function matches `main`.

**Small branches from `main`, not `feature/chatbot` into `main`.**
- `feature/chatbot` is 557 commits ahead.
- `main` holds newer dashboard files from hotfixes cherry-picked straight onto it.
- A whole-branch merge would ship weeks of unreviewed change to the dashboard at once.

The practice of cherry-picking onto `main` (`c97eca3`, `cf9f141`) continues, now through a pull request.

**The first pull request is the live function, its tests and the pipeline.**
- `main`'s copy of the function was about 1,400 lines behind live.
- The first function change merged after the pipeline existed would otherwise have deployed that old copy and rolled live back by weeks.
- None of the test files existed on `main`.

**Admins are inside the protection.** "Nobody pushes to `main` directly" holds only if it holds for the admin account too. In an emergency, the admin can lift the protection, which is a visible act.

**n8n and the phone agents stay manual for now.** Their deploys carry their own gates:
- `check_whatsapp_rules.py`;
- the `MEMORY_EPOCH` check;
- `vapi_sync.py`'s compare against the live agent.

## Constraints

- `ClixTeam579`, the account sessions use, can only read the repository. `TheSuperShyy` is its admin and is logged in on this PC as the second `gh` account.
- The repository is public. GitHub gives no secrets to pull requests from forks, and the deploy job runs only on a push to `main`.
- `node --test` on `.ts` files and `stripTypeScriptTypes` need a recent Node: 24, as on this PC.
- A required check is matched by the job's name, `checks`, from the GitHub Actions app (id 15368).
- GitHub's scheduled runs are best-effort. The OXS jobs fire later and less often than their cron, which this feature does not change.

## Known failure modes

- **The deploy job fails after a merge** (token expired, Supabase down). `main` and live then differ. Fix the secret and re-run the job, or run `--apply --code-only` by hand from a checkout of `main`.
- **A hand deploy from an older checkout of `main`.** The guard fetches first, so a stale local `main` refuses rather than deploying old code.
- **A check flakes.** Re-run it. If it flakes twice, fix or drop it rather than adding retries.

## Open questions

- Whether the n8n workflows and the phone agents join the pipeline later. That is settled by the owner, once this has carried a few changes.
