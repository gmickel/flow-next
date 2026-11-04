---
satisfies: [R4, R6, R11, R13]
---
# fn-73-glab-git-ops-make-prresolve-prland-over.2 make-pr forge rule in shell and GitLab reads in preflight

## Description
Teaches make-pr's shared preflight which forge it is on and gives its three `gh` reads a GitLab equivalent, so the neutral fences (spec detect, close, chain base selection) run unchanged on GitLab. Creation and update come in the next task; this one ends with preflight passing on a GitLab origin and stopping correctly on unknown hosts.

**Size:** M
**Files:** `plugins/flow-next/scripts/make-pr-preflight.sh`, `plugins/flow-next/scripts/make-pr-gitlab.sh` (new), `plugins/flow-next/tests/test_make_pr_preflight_auth.py`, `plugins/flow-next/tests/test_make_pr_gitlab.py` (new), `plugins/flow-next/tests/test_forge.py`
**Touches:** [plugins/flow-next/scripts/make-pr-preflight.sh, plugins/flow-next/scripts/make-pr-gitlab.sh, plugins/flow-next/tests/test_make_pr_preflight_auth.py, plugins/flow-next/tests/test_make_pr_gitlab.py, plugins/flow-next/tests/test_forge.py, plugins/flow-next/tests/fixtures/gitlab/**, scripts/install-codex.sh, plugins/flow-next/tests/test_codex_config_merge.py, plugins/flow-next/tests/test_bundled_make_pr.py, plugins/flow-next/tests/chain_fixture_support.py, plugins/flow-next/scripts/make-pr_smoke_test.sh]

### Approach
- Origin block (`make-pr-preflight.sh:6-24`, before `# end:block`): keep the github.com / ssh.github.com fast path byte-for-byte. For any other host apply the same order as the Python rule (task 1): gitlab.com or `CI_SERVER_HOST` -> gitlab; with `GH_ENTERPRISE_TOKEN` or `GITHUB_ENTERPRISE_TOKEN` set, ask `glab auth status --hostname <host:port>` before `gh auth token --hostname` (an enterprise token makes gh claim every host); otherwise gh first, then glab. Set `FORGE`; a host neither claims stops with one message naming `gh auth login` and `glab auth login`. Keep fn-310's existing message text for the cases its tests pin, or extend it so they still match.
- Parity test: feed the same origin cases to the Python rule (task 1) and this shell block, including a self-managed GitLab host with an enterprise token set; they must agree.
- GitLab auth and scope: `glab` present and logged in to the host, and the token has `api` scope (token self-read), all before any close or push.
- New `make-pr-gitlab.sh` helper with read subcommands answering in `gh`'s JSON keys: `list --head <branch>` (number, state, baseRefName, url) and `view` (existing open or locked MR for the current branch). Use `GITLAB_HOST`, project from the origin path (URL-encoded), MRs from the origin project only.
- One forge guard in the shared script selects the read helper for the three reads (parent-PR lookup :62, existing-PR check :166, prior-PR count :183); the jq after each read stays shared. Merged-parent history fetch uses `refs/merge-requests/<iid>/head` on GitLab.
- On GitLab, capture each helper read's exit status and validate its JSON before any filtering: only a successful, complete, well-formed empty listing means "no MR". A failed or malformed read stops `NEEDS_HUMAN` before close or push. (GitHub's existing `|| true` at :166 is pre-existing and not changed here.)
- Ship the new helper everywhere `make-pr-create.sh` ships: `scripts/install-codex.sh` copies an explicit script list (:297), and the bundled-script tests and fixtures stage named scripts (`tests/test_bundled_make_pr.py`, `tests/chain_fixture_support.py`, `scripts/make-pr_smoke_test.sh`). Extend `tests/test_codex_config_merge.py`'s real-installer assertions to check the helper is installed.
- Record fixtures live for every glab call this task adds.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/make-pr-preflight.sh:1-90,160-190` — origin block, parent lookup, existing-PR and prior-PR reads
- `plugins/flow-next/tests/test_make_pr_preflight_auth.py:1-70` — the `# end:block` seam and pinned text
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md:15-35` — exit codes 1-4 and close semantics

**Optional** (reference as needed):
- `plugins/flow-next/tests/test_make_pr_close.py:60-80,380-400` — PATH shims and `FLOW_PR_CREATE_CMD`
- `plugins/flow-next/tests/test_make_pr_reached_path.py` — markers that must stay (`# fence:chain-detect`, `# --- §0.5`)

### Key context
- The `# end:block` test seam runs the origin block without `FLOWCTL`; the shell rule must not call flowctl.
- A spec with any branch-bearing dependency runs the parent lookup, so GitLab needs it for ordinary dependency chains, not only stacks (R13).

## Acceptance
- [ ] On a GitLab origin preflight sets the forge, checks glab login and `api` scope before close or push, and passes
- [ ] An origin neither CLI claims stops `NEEDS_HUMAN` naming both login commands; fn-310's tests pass unmodified
- [ ] Shell and Python forge rules agree on the shared origin cases (parity test)
- [ ] Parent MR open -> base is the parent branch; parent MR merged -> default branch, with merged history fetched via the MR ref; unreadable parent -> `NEEDS_HUMAN` (R13)
- [ ] Existing open or locked MR without `--update` stops as on GitHub
- [ ] A failed or malformed GitLab existing-MR or parent read stops `NEEDS_HUMAN` before close or push (regression test)
- [ ] Helper output tested against live-recorded fixtures; GitHub preflight tests pass unmodified
- [ ] The Codex installer ships the helper, asserted by the real-installer test

## Done summary
make-pr's preflight now works out the forge from the origin remote in shell, using the same rule as flowctl's `repo_forge`. On GitLab it checks that glab is installed, logged in, and holds a token with api scope before any close or push. A single guard sends the three PR reads (parent lookup, existing-PR check, prior-PR count) to the new `scripts/make-pr-gitlab.sh`, which accepts the same argv as gh and answers in gh's JSON keys. A merged parent's history is fetched from `refs/merge-requests/<iid>/head`. The Codex installer ships the helper.

Tier: session (jev long_running 0.49) at default effort (model: claude-opus-5-5[1m])

Evidence (measured):
- Live, against the GitLab test project (scratch clone, nothing pushed): the full preflight sourced in bash on a child of `fn73-fx-reused` set `FORGE=gitlab`, read parent MR !2 as OPEN, set the base to `origin/fn73-fx-reused`, found no existing MR, and closed the spec locally. On `fn73-fx-reused` itself it stopped with "branch already has an OPEN PR: .../merge_requests/2"; with `--update` it found PR #2. A spec depending on `fn73-fx-merged` (branch deleted, MR !3 merged) fetched the parent from `refs/merge-requests/3/head` and set the base to `origin/main`, with no rewrite because the project merges with a merge commit. The origin block also passed live under zsh against the real glab, including the login and the api-scope self-read.
- Tests: the new `tests/test_make_pr_gitlab.py` has 14 tests. They cover helper rows, view, failed, malformed, empty and HTML reads, and api scope; GitLab login, scope and unknown-host stops; a shell-vs-Python parity test over 12 origin cases, including an enterprise token with logged-in, offline and logged-out glab; R13 open, merged and unreadable parents through the shared chain-detect fence; and existing-MR stops before close. All glab answers replay live recordings. Mutation checks: making gh answer first under an enterprise token, or dropping the fork filter, each fails 7 tests. The empty-output regressions fail before the review fix.
- The focused suites passed: test_forge, judge_route, pilot_snapshot, make_pr_preflight_auth, make_pr_close, flow_auto, make_pr_gitlab, bundled_make_pr, chain_consumer_fixtures, codex_config_merge and make_pr_reached_path (150 tests). `make-pr_smoke_test.sh` passed 63/0. `ruff check .` and `sync-codex.sh --check` passed. fn-310's tests and the GitHub preflight tests are unmodified (R10).
- New fixtures, recorded live: `token-self-api`, `token-self-read-api` (a scratch read_api token, revoked after recording) and `token-self-revoked`. The MR list fixtures from task .1 have the exact argv the helper uses.
- Baseline: green, with `PYTHONPATH=plugins/flow-next/tests`. The Quick command fails to import without that path; this predates the task.

Decisions:
- The helper accepts gh's argv (`pr list --head B --state all --json K [--jq E]`, `pr view --json K`) so each read site changes only `gh` to `"${PR_READ:-gh}"`. The tests run the chain-detect, chain-rewrite and §0.5 slices without the origin block; with this form, an unset guard still means gh. The helper always returns number, url, state and baseRefName.
- The existing-PR read keeps gh's swallowed failure, since gh's nonzero exit is its "no PR". On GitLab, a failed read stops `NEEDS_HUMAN` instead. The `refs/pull/$DEP_PR_NUMBER/head` literal stays because `test_make_pr_reached_path` pins it; the guard's `PR_HEAD_REFS` overrides it on GitLab.
- The unknown-host message still contains fn-310's pinned text and now names both `gh auth login --hostname` and `glab auth login --hostname`. A missing or logged-out glab exits 1 with "Error:", matching the gh checks. A missing api scope, or a token self-read that fails, stops `NEEDS_HUMAN` (exit 2).
- `GITLAB_HOST` (host:port) and `ORIGIN_PROJECT` are exported for the helper, so task .3's glab calls inherit the host.
- Dry runs skip the origin block, as before, so a GitLab dry run reads through gh and treats a parent as open (the existing note).
- The existing `test_bundled_make_pr` zsh check caught `$DEP_PR_HEAD:refs` (a zsh modifier); it is now braced.

Follow-ups:
- The shell `glab auth status` probe has no deadline (declined review finding). A slow host waits and then answers definitively, and never reads as GitHub. Stock macOS has no `timeout(1)`.
- A glab login via OAuth rather than a PAT may fail the `personal_access_tokens/self` scope read and stop `NEEDS_HUMAN`. This was not tested; the test instance has no OAuth app.
- An SSH origin on a self-managed GitLab with a non-default web port reads as unknown, as in task .1.

Review: one NEEDS_WORK finding, fixed. All three lenses found that a successful glab call with empty or non-JSON stdout read as "no MR". Each page must now be exactly one JSON array. The re-review returned SHIP.

Left on the live instance: nothing new. The scratch read_api token was revoked; the scratch clone is under the session scratchpad.

stage: impl-review - ran [2026-11-04..2026-11-04]

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 96ac26dc9ecdb9037622eb8a98ff667bef19026d, 23c5852e80b50e1c25177709db2a6354da8e4cc9
- Tests: PYTHONPATH=plugins/flow-next/tests python3 -m unittest test_forge test_judge_route test_pilot_snapshot test_make_pr_preflight_auth test_make_pr_close test_flow_auto test_make_pr_gitlab test_bundled_make_pr test_chain_consumer_fixtures test_codex_config_merge test_make_pr_reached_path (150 OK), bash plugins/flow-next/scripts/make-pr_smoke_test.sh (63 pass), uvx ruff check .
- PRs: