---
satisfies: [R6, R10, R11]
---
# fn-73-glab-git-ops-make-prresolve-prland-over.3 make-pr creates and updates GitLab merge requests

## Description
Adds MR creation and update behind make-pr's existing create seam and the skill's forge reference, so make-pr on GitLab pushes, opens or updates the MR with the rendered body, and closes the spec exactly as on GitHub.

**Size:** M
**Files:** `plugins/flow-next/scripts/make-pr-gitlab.sh`, `plugins/flow-next/scripts/make-pr-create.sh`, `plugins/flow-next/skills/flow-next-make-pr/forge-gitlab.md` (new), `plugins/flow-next/skills/flow-next-make-pr/workflow.md`, `plugins/flow-next/skills/flow-next-make-pr/SKILL.md`, `plugins/flow-next/tests/test_make_pr_gitlab.py`
**Touches:** [plugins/flow-next/scripts/make-pr-gitlab.sh, plugins/flow-next/scripts/make-pr-create.sh, plugins/flow-next/skills/flow-next-make-pr/**, plugins/flow-next/tests/test_make_pr_gitlab.py, plugins/flow-next/tests/fixtures/gitlab/**, plugins/flow-next/codex/**, scripts/sync-codex.sh]

### Approach
- Helper `create` takes the same arguments as `gh pr create` (`--title --body-file [--draft] --base --head`) and prints the MR URL, so `make-pr-create.sh` uses it through the existing `FLOW_PR_CREATE_CMD` seam (the smoke-pinned default line stays). Body as JSON on stdin with `Content-Type: application/json`, built by `jq`, never a heredoc. Draft = `Draft: ` title prefix. Retry only on GitLab's exact `source_branch ... does not exist` answer.
- Helper `update`: replace the description; `--ready` strips `Draft: `, `[Draft]`, `(Draft)`; otherwise keep the current draft state.
- `make-pr-create.sh`: widen the URL match to accept `/-/merge_requests/<n>`; route its update-mode reads/edit through the helper on GitLab; the stack-link and the tracker live-body edit stay GitHub-only (already origin-guarded or guard them); the 65536-char guard is GitHub's limit.
- On a forge whose name differs from the tracker provider, write the tracker reference as the issue URL, not `#N`, so GitLab does not link the wrong issue.
- `forge-gitlab.md`: the GitLab commands the agent runs (no issue or spec numbers in shipped skill text). `workflow.md` gets one dispatch line: on a forge other than GitHub, read `forge-<forge>.md`. `SKILL.md` description stops saying "via gh" only.
- Regenerate the Codex mirror (`./scripts/sync-codex.sh`); update its per-file rewrites if a matched phrase changed.
- Record live fixtures for create, update, draft and ready.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/make-pr-create.sh:25-100,105-150` — update path, create seam, URL match, retry, stack-link, tracker edit
- `plugins/flow-next/skills/flow-next-make-pr/create-and-finalize.md:15-40` — create contract
- `plugins/flow-next/scripts/make-pr_smoke_test.sh:790-800` — pinned create line

**Optional** (reference as needed):
- `scripts/sync-codex.sh:440-485` — make-pr phrase rewrites
- `plugins/flow-next/skills/flow-next-make-pr/no-spec-path.md` — gh prose for the no-spec path

### Key context
- make-pr closes the spec and commits before pushing; every GitLab check that can fail must already have run in preflight (task 2).

## Acceptance
- [ ] Create opens an MR with the rendered body (draft and ready), prints its URL, and make-pr records it as on GitHub
- [ ] `--update` replaces the description; `--ready` removes draft markers; draft state otherwise kept
- [ ] Not-yet-visible branch retried on GitLab's exact answer only
- [ ] Mismatched tracker and forge write the tracker reference as a URL
- [ ] Tests from live fixtures; make-pr GitHub tests and the make-pr smoke pass unmodified (R10)
- [ ] Codex mirror regenerated and `sync-codex.sh --check` passes

## Done summary
make-pr now opens and updates GitLab merge requests. `make-pr-gitlab.sh` gained `pr create`, which takes gh's argv, sends the body as JSON on stdin with an explicit Content-Type, and marks a draft with the `Draft: ` title prefix. It also gained `pr edit <n> --body-file F [--ready]`, which replaces the description and, with `--ready`, removes `Draft:`, `[Draft]` and `(Draft)` from the title. Both print the MR URL. When preflight's `PR_READ` is set, `make-pr-create.sh` runs the helper through the existing create seam and routes the update read and edit through it. It retries only on GitLab's exact `{"message":{"source_branch":["does not exist"]}}` answer and accepts `.../-/merge_requests/<n>` URLs (http or https). The stack-line refresh and the live-body tracker edit stay GitHub-only. When the tracker is on the other forge, the reference is written as the issue URL, or left out if no URL is stored. `forge-gitlab.md`, a dispatch line in workflow.md, the SKILL.md description and the Codex mirror are updated.

Tier: session (jev moderate 0.19) at default effort (model: claude-opus-5-5[1m])

Evidence (measured):
- Live, against the GitLab test project: the sourced `make-pr-create.sh` pushed a new branch and opened draft MR !11 (`Draft: fn73 e2e create`, `draft: true`). The body arrived intact, including quotes, backticks, `$HOME`, a backslash and a non-ASCII character. `--update` replaced the description and kept the draft. `--update --ready` cleared it (`draft: false`). The same update sourced from `zsh -f` also passed. MRs !9-!11 and their branches were deleted afterwards; the project is back to !1-!7.
- Fixtures recorded live by running the helper through a recording glab shim (argv, env, stdin, exit code, raw stdout/stderr): `mr-create-draft`, `mr-create-ready`, `mr-create-no-branch`, `mr-edit`, `mr-view-draft`, `mr-edit-ready`, `mr-branch-create`. No token-shaped strings.
- Tests: `test_make_pr_gitlab.py` has 7 new tests (21 in the file). They check request bodies for draft and ready creates; that edit keeps the draft unless `--ready`, across all three markers; that a refused create prints GitLab's answer; and that the create script pushes and then creates via glab with no gh call. They also check the retry fires only on the exact answer, update and ready through the script, and the tracker reference table (cross-forge URL, missing URL, same-forge unchanged). Mutation checks: removing each of the nine guarded behaviours fails at least one test.
- Focused suites passed: make_pr_gitlab, bundled_make_pr, make_pr_close, make_pr_preflight_auth, pr_cognitive_aid, forge, judge_route, pilot_snapshot, flow_auto, codex_config_merge, make_pr_reached_path, chain_consumer_fixtures (185 tests). Skill-prose, link and codex lint suites passed (47). `make-pr_smoke_test.sh` passed 63/0. `sync-codex.sh --check` and `ruff check .` (via uvx) passed. The existing GitHub make-pr tests and the smoke are unmodified (R10).
- Baseline: green (178 focused tests, smoke 63/0), with `PYTHONPATH=plugins/flow-next/tests` (pre-existing).

Decisions:
- `PR_READ` is the single GitLab signal in `make-pr-create.sh`, as in preflight. An explicit `FLOW_PR_CREATE_CMD` still wins. The smoke-pinned default line and the pinned GitHub URL grep are unchanged; the GitLab URL match is a second line.
- PHASE0_CONTEXT does not carry the forge, and preflight was outside this task's Touches. So `forge-gitlab.md` tells the agent to carry `FORGE`, `PR_READ`, `GITLAB_HOST` and `ORIGIN_PROJECT` into the create call, the same way it already carries `BASE_REF`. If the agent drops them, creation falls back to `gh pr create`, which fails after the close commit, the same as any create failure.
- The cross-forge rule applies both ways, so a GitLab tracker on a GitHub origin now writes the issue URL instead of a backticked `#N`, as the task asked.
- The Codex descriptions in `sync-codex.sh` (openai.yaml and the routing table) now also mention glab.
- On GitLab, finalize leaves out the resolve-pr line, because resolve-pr reads GitHub pull requests only for now.

Review: SHIP from all three lenses. One P2, raised by two lenses: a cross-forge tracker with no stored URL kept `#N`. Fixed in ee33c85fc with a test case that fails without the fix; no re-review, per the working rules. Declined P2: the `created_at` read in `forge-gitlab.md` does not strip glab's "Multiple config files found" stdout warning. That step is run by the agent and fails loudly rather than giving a wrong answer, and the warning comes from a misconfigured glab install.

Follow-ups:
- PHASE0_CONTEXT could carry the forge so the create call does not depend on the agent carrying four variables (this is in the preflight script).
- The no-spec path on a GitLab repo without `.flow/` never runs preflight, so it still uses `gh pr create`.

stage: impl-review - ran [2026-11-04..2026-11-04]

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: eba0bf60a94f2a3e1d2d9d55d6a4556bc83111b1, ee33c85fc75405b9a06ab0d2ce2255c371dbbf9b
- Tests: PYTHONPATH=plugins/flow-next/tests python3 -m unittest <12 focused make-pr/forge suites> (185 OK), bash plugins/flow-next/scripts/make-pr_smoke_test.sh (63/0), ./scripts/sync-codex.sh --check, uvx ruff check .
- PRs: