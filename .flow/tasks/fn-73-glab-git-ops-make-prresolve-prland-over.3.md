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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
