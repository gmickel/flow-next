---
satisfies: [R5, R6, R8]
---

## Description
Author the orchestration-split + safety mechanics in `references/codex-delegation.md` AND add the deterministic `flowctl codex classify-result` helper that makes classification/rollback testable. The host/worker keep all git; `codex exec` only writes code. The classification, schema-validation, and scoped-rollback-path computation live in flowctl (mechanical, CLAUDE.md split-rule), so CI tests target executable code — not markdown.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (new `codex classify-result` helper), `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md`, `plugins/flow-next/agents/worker.md` (commit/rollback interplay), `plugins/flow-next/tests/` (classification/rollback tests + mock-codex fixture)

## Approach
- **Deterministic helpers (flowctl):**
  - `flowctl codex classify-result --result <file> --exit <code> --json` → `{class, status, action, valid_schema}` per the 5-row table. Pure function over (exit code, result JSON) → no LLM.
  - `flowctl codex rollback-plan --repo-root <root> --preexisting-untracked-file <pre> --post-untracked-file <post> --json` → `{rollback_paths, rejected}`. Untracked-cleanup set = `post − pre` (newly-created untracked FILES), derived from pre/post snapshots taken with **`git ls-files --others --exclude-standard -z`** (NUL-delimited — avoids porcelain-v1 quoting of spaces/backslashes/newlines, and enumerates files inside new dirs individually rather than collapsing to `?? dir/`) — NOT from the result's `files_modified` (absent on CLI-failure/missing/malformed, yet Codex may have created files). Rejects absolute paths, `..` traversal, empty, `.`, and bare directories (never fed to `git clean`; `git clean -fd <files>` removes emptied dirs). Tracked changes revert via a tracked-only checkout (only touches tracked).
  These are the testable surfaces (no markdown-only logic).
- Prompt template (lifted, XML-tagged): `<task> <files> <patterns> <approach> <constraints> <testing> <verify> <output_contract>`. `<constraints>` MUST forbid Codex `git commit`/`push`/PRs, restrict to repo root, keep scope tight. `<verify>` forbids `status:"completed"` unless tests pass (Codex self-verifies + fixes).
- Batching scoped to ONE flow task: ≤5 units = the task's logical change-sets, split at phase/file boundaries, never split shared-file units, skip delegation if all units trivial. No cross-task batching in v1.
- 5-row classification (computed by the helper): exit≠0 → CLI failure / rollback / fall back for all remaining; missing-or-malformed JSON → task failure; `failed` → task failure; `partial` → keep diff, finish locally + verify + commit; `completed` → cross-check then commit.
- **Trust cross-check** (cheap): before committing `completed`, intersect `git status --porcelain` with `files_modified`; a mismatch downgrades to partial/failed (don't commit blind). No test re-run when an impl-review gate or worker verification already covers it (fn-55.5 handles the `REVIEW_MODE=none` verification).
- **Clean-baseline preflight via `git status --porcelain`** (catches untracked files `git diff --quiet HEAD` misses), no auto-stash, **scoped to the code tree — EXCLUDES host-owned `.flow/`**. `/flow-next:work` runs plan-sync after each task (`phases.md` 3e), leaving uncommitted `.flow/tasks/` edits; a whole-tree clean-baseline would false-disable delegation after task 1. Only non-`.flow/` dirtiness counts as "dirty".
- **Git-ownership enforcement (not prompt-only):** a yolo sandbox can still run git. The worker captures `BASE_COMMIT` (already does, `worker.md:108`) and asserts `git rev-parse HEAD == BASE_COMMIT` AFTER `codex exec`. HEAD moved (Codex committed) → `git reset --soft BASE_COMMIT` (un-commit, keep diff) → scoped rollback → classify failure → disable delegation. A committed change is invisible to the `git status` cross-check, so this assertion is the real "Claude owns all git" guard.
- **`.flow/` integrity enforcement (not prompt-only):** `<constraints>` forbid Codex writing under `.flow/` except its `.flow/tmp/codex-<task-id>/` scratch dir. Because rollback never touches `.flow/**`, an unauthorized `.flow/` write would otherwise survive. Snapshot non-scratch `.flow/` content (everything under `.flow/` except `.flow/tmp/codex-*`) BEFORE delegating; after `codex exec`, re-check. Any new/changed non-scratch `.flow/` path → restore those paths from the snapshot (the one case rollback touches `.flow/`, to undo Codex's edit) → disable delegation → surface/escalate.
- **Scoped rollback:** snapshot the untracked set (`git ls-files --others --exclude-standard -z`) BEFORE delegating and again AFTER the run; rollback (tracked-only checkout + `git clean -fd -- <paths>`) feeds `git clean` ONLY the sanitized `post − pre` paths from `flowctl codex rollback-plan` (works even when the result JSON is missing/malformed) — never bare `git clean` (cite github/copilot-cli#1675), never a pre-existing untracked file, **never a `.flow/**` path** (host-owned).
- Reuse the worker's existing `BASE_COMMIT` (`worker.md:108`) for rollback/review scope — do not reset the base (preserves the spec-wide-base rule for the final integration task).
- Each batch surfaces a result block (summary/files/verification/issues).
- **Mock-codex fixture:** a stub emitting canned `result-batch-*.json` for each of the 5 rows → deterministic tests of `classify-result` + the rollback path computation (no real model).

## Investigation targets
**Required**:
- `plugins/flow-next/scripts/flowctl.py:2841-2853` — codex helper area (where `classify-result` slots in alongside existing codex subcommands)
- `plugins/flow-next/agents/worker.md:106-161` — Phase 2 impl + `BASE_COMMIT`, Phase 3 commit, Phase 4 impl-review (rollback/commit interplay)
- `.flow/specs/fn-55-optional-codex-implementation.md` — Result classification table + Safety + Prompt template + classify-helper contract (lift verbatim)
- `plugins/flow-next/tests/` — existing fixture/test patterns for a stub external command
**Optional**:
- memory `final-integration-tasks-need-wider-impl-2026-05-26` — impl-review must use the spec-wide merge base for the final task; delegation must inherit, not reset

## Acceptance
- [ ] `flowctl codex classify-result --result <f> --exit <n> --json` returns the correct `{class, status, action, valid_schema}` for all 5 rows + malformed/missing JSON; covered by deterministic unit tests using the mock-codex fixture.
- [ ] `flowctl codex rollback-plan` derives the cleanup set from the `post − pre` untracked-snapshot diff (`git ls-files --others --exclude-standard -z`, NOT `files_modified`), so it still cleans new untracked files — including files in newly-created nested directories and paths with whitespace/odd chars — on CLI-failure / missing / malformed results; emits only sanitized repo-relative file paths and rejects absolute / `..` / empty / `.` / bare-directory — covered by path-sanitization + CLI-failure/malformed + nested-dir + whitespace-path cleanup tests.
- [ ] Prompt template documented with all 8 XML sections; `<constraints>` forbids Codex git/PRs, restricts to repo root, and forbids non-scratch `.flow/` writes (only `.flow/tmp/codex-<task-id>/` allowed); `<verify>` forbids `completed` unless tests pass.
- [ ] Batching rules documented as per-task (≤5 units, phase/file boundaries, never split shared-file, skip-if-trivial); cross-task batching explicitly out of scope.
- [ ] Trust cross-check documented: `git status --porcelain` ∩ `files_modified` mismatch → treat as partial/failed.
- [ ] Clean-baseline preflight is scoped to the code tree and EXCLUDES `.flow/` — a multi-task run with `planSync.enabled=true` (plan-sync leaving uncommitted `.flow/tasks/` edits) does NOT disable delegation after task 1, and rollback never touches `.flow/**` — covered by a multi-task plan-sync test.
- [ ] Post-`codex exec` HEAD-unchanged assertion: a mock Codex that creates a commit triggers `git reset --soft BASE_COMMIT` + scoped rollback + delegation-disable — covered by a test.
- [ ] Non-scratch `.flow/` integrity: a mock Codex that mutates `.flow/tasks/*.md` (outside the scratch dir) triggers restore-from-snapshot + delegation-disable; a write to `.flow/tmp/codex-*` is allowed — covered by a test. `<constraints>` forbid non-scratch `.flow/` writes.
- [ ] Rollback is scoped to codex-created files only (untracked snapshot pre/post), never bare `git clean`, never a pre-existing untracked file, never a `.flow/**` path — covered by a rollback-scope test.
- [ ] Rollback reuses the worker `BASE_COMMIT`; no base reset (final-integration spec-wide base preserved).
- [ ] Test suite green.

## Done summary
_(pending implementation)_

## Evidence
_(pending implementation)_
