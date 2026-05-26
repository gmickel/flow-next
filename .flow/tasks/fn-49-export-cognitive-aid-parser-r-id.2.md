---
satisfies: [R3, R4, R5, R6]
---

## Description

Make `_export_memory_during_spec` in `plugins/flow-next/scripts/flowctl.py` null-safe when `spec.created` is null. Currently the time-window filter uses `spec.created` as the lower bound; when null, the filter fails closed and returns `[]`, hiding legitimate memory entries (decisions, bugs, architecture-patterns) that were written during the spec's lifetime. fn-48's `factory-droid-platform-status-2026-05-2026-05-25` decision is the reproducer — written during fn-48.2, present in the diff, but invisible in `memory_during_spec.decisions[]`.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (`_export_memory_during_spec` helper), a new or extended test file under `plugins/flow-next/tests/` exercising the null-spec.created path, CHANGELOG.md (release-time entry under `[unreleased]`).

## Approach

- Locate `_export_memory_during_spec` in `flowctl.py`. Per spec, it currently filters memory entries by `created >= spec.created`. When `spec.created` is null, the comparison fails (or treats null as min-int, masking everything).
- **Pick ONE fallback** (implementer's choice, but must be deterministic):
  - **Option A — earliest task-created timestamp**: scan `tasks[].created` for the spec; use `min()` as the lower bound. Simplest if tasks exist. Falls back to Option B if no tasks have created either.
  - **Option B — branch first commit**: `git log <spec.branch_name> --reverse --format=%cI --max-count=1` returns the first commit's ISO timestamp on the branch. Deterministic given a fixed branch + git history.
  - **Option C — diff-touched detection**: skip the time-window filter entirely; use `git diff --name-only <base>..HEAD -- .flow/memory/` to find memory entries created/modified on the branch, regardless of timestamp. Most resilient but requires plumbing `<base>` into the helper (already in the export's signature).
- **Recommendation**: try Option A first (simplest, uses data flowctl already has). Fall back to Option B in code if Option A returns no usable timestamp. Option C is overkill for this scope.
- Document the chosen mechanism in a code comment near the fallback branch so future readers know why.
- Add a unit test fixture: a synthetic spec JSON with `created: null` + tasks with `created` populated + memory entries (one before, one after the earliest task) + assert the export returns only entries that should be in the window.
- Add a synthetic spec JSON with `created: null` AND tasks with `created: null` → Option B (branch first-commit) should fire; test will need a git repo fixture.
- Run fn-48 export and confirm `memory_during_spec.decisions | length == 1` post-fix (was 0):
  ```bash
  .flow/bin/flowctl spec export-cognitive-aid fn-48-backend-split-review-workflows-flowctl --base origin/main --json | jq '.memory_during_spec.decisions | length'
  ```
- The factory-droid-platform-status decision entry (the reproducer) should appear with its correct title and `first_sentence` extracted.
- Draft a `[unreleased]` CHANGELOG bullet under `### Fixed`. Cite fn-48 as surfacing context and the chosen fallback mechanism.

## Investigation targets

**Required**:
- `plugins/flow-next/scripts/flowctl.py` — find `_export_memory_during_spec` (use grep). Examine the time-window comparison and how `spec.created` is read.
- The fn-48 spec JSON: `.flow/specs/fn-48-backend-split-review-workflows-flowctl.json` — confirm `created` is null (or missing).
- The decision entry `.flow/memory/knowledge/decisions/factory-droid-platform-status-2026-05-2026-05-25.md` — confirm its `created` frontmatter or file mtime falls within the spec's actual lifetime.
- Memory entry `bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08` — direct precedent: shows how absent spec fields silently crash later commands. Same class of bug.
- Memory entry `bug/build-errors/fn-44-review-cycle-lessons-2026-05-21` — broader flowctl.py parser-contract lessons; required reading.
- Memory entry `bug/data/migrationrollback-cli-10-review-cycle-2026-05-08` — atomic write + null/missing field handling pitfalls.

**Optional**:
- `plugins/flow-next/scripts/flowctl.py` — the broader `cmd_spec_export_cognitive_aid` function for context on how the helper is called.

## Acceptance

- [ ] `_export_memory_during_spec` handles `spec.created` being null without returning `[]`; uses a deterministic fallback (Option A → B chain, or whichever single option the implementer picks).
- [ ] Fallback choice documented in a code comment explaining why the chosen path is deterministic.
- [ ] Unit test fixture exists for `spec.created: null + tasks have created` → returns expected entries via earliest-task-created fallback.
- [ ] Unit test fixture exists for `spec.created: null + tasks all null` → returns expected entries via the secondary fallback (branch first-commit or diff-touched).
- [ ] Re-running `.flow/bin/flowctl spec export-cognitive-aid fn-48-backend-split-review-workflows-flowctl --base origin/main --json | jq '.memory_during_spec.decisions | length'` returns `1` (was `0` pre-fix), and the entry is `factory-droid-platform-status-2026-05-2026-05-25` with its title intact.
- [ ] `bash plugins/flow-next/scripts/smoke_test.sh` runs green (existing 127/2 baseline preserved + new null-spec.created cases pass).
- [ ] CHANGELOG `[unreleased]` entry drafted under `### Fixed` citing fn-48 as surfacing context and naming the chosen fallback mechanism.

## Done summary
Made `_export_memory_during_epic` null-safe with a deterministic Option A → B → no-signal fallback chain (earliest `tasks[].created_at` → branch first-commit via `git log` → return-all graceful-degradation). New `_export_resolve_memory_threshold` helper isolates the chain; 12 new tests in `tests/test_memory_during_spec_null_safe.py` cover each step including a synthetic git repo with pinned `GIT_COMMITTER_DATE`. fn-48 re-export confirms the `factory-droid-platform-status-2026-05-2026-05-25` decision surfaces with its title and first_sentence intact.
## Evidence
- Commits: 2f476f9c1917fbde883964691278af5dbea59852
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' (644 pass, 2 skip), bash plugins/flow-next/scripts/smoke_test.sh (127 pass, 2 pre-existing fail), .flow/bin/flowctl spec export-cognitive-aid fn-48-backend-split-review-workflows-flowctl --base origin/main --json | jq '.memory_during_epic.decisions | length' => 1 (factory-droid-platform-status, title intact)
- PRs: