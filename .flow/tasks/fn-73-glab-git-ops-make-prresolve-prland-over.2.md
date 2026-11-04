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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
