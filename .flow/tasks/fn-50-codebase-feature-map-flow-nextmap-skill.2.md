---
satisfies: [R3, R9]
---

## Description

Add `flowctl repo-map list / show / since-ref` reader subcommands that parse `.clawpatch/features/*.json` and return text + `--json`. Enforce `schemaVersion: 1`; per-file parse errors emit one-line stderr diagnostic and skip without aborting the list.

This is the **first flowctl reader for data outside `.flow/`**. The new handlers BYPASS the standard `ensure_flow_exists()` guard, gating on `.clawpatch/` presence instead.

**Size:** M
**Files:**
- `plugins/flow-next/scripts/flowctl.py` — new `cmd_repo_map_list/show/since_ref` handlers + argparse subparser registration
- `plugins/flow-next/tests/test_repo_map.py` (new, **unittest** — match repo convention; `python -m unittest discover -p "test_repo_map.py"` is the CI runner)
- `plugins/flow-next/tests/fixtures/clawpatch-map/.clawpatch/features/{valid,invalid-schema,malformed}.json` (new) — checked-in fixtures (no clawpatch invocation in CI)

## Approach

Mirror `cmd_prospect_list` at `plugins/flow-next/scripts/flowctl.py:8864-8973` for the structural template (list-under-dir, filter flag, JSON-or-text). Mirror `cmd_prospect_read` at `flowctl.py:8976-9100` for `show --feature <id>`.

For `since-ref <git-ref>`: list features whose `ownedFiles[].path` or `entrypoints[].path` overlap files touched in `git diff --name-only <ref>..HEAD`. Use the existing flowctl `_git_diff_names_only` helper if present; otherwise stick to a single `subprocess.run(["git","diff","--name-only",f"{ref}..HEAD"])`.

**Failure handling for `since-ref` (per spec edge cases):**
- **Non-git repo** (no `.git/` reachable): emit one-line stderr `[flowctl repo-map since-ref] not a git repository — since-ref unavailable; use 'list' instead` and return `{"success": false, "count": 0, "features": [], "error": "not-a-git-repo"}` with **exit 0** (so callers in skill bash can branch on the JSON `success` field rather than hitting a non-zero exit). The `list` and `show` subcommands work fine in non-git repos.
- **Invalid / unknown ref** (`git rev-parse <ref>` fails): emit one-line stderr `[flowctl repo-map since-ref] unknown ref: <ref>` and return `{"success": false, "count": 0, "features": [], "error": "unknown-ref"}` with **exit 0**. Probe via `git rev-parse --verify <ref>^{commit}` BEFORE running `git diff` to avoid the noisy `unknown revision or path not in the working tree` git error reaching the user.

Argparse pattern at `flowctl.py:21311-21388` (prospect subcommands) — copy verbatim for `repo-map` subcommands with `--count` (list only), `--feature <id>` (show only), `--ref <git-ref>` (since-ref only), and global `--json`.

**BYPASS `ensure_flow_exists()`** at the top of each new handler — gate on `os.path.isdir(".clawpatch")` instead. Absent `.clawpatch/` returns `{success: true, count: 0, features: []}` with exit 0 (so `prime`'s `--count` check works without special-casing).

Schema-version guard (R9): on each `*.json` parse, check `schemaVersion == 1`; on mismatch emit `[flowctl repo-map] {path}: skip — schemaVersion={found}, expected=1` to stderr and continue. Malformed JSON: emit `[flowctl repo-map] {path}: skip — invalid JSON` and continue. `list` reports `parse_skipped: N` in JSON output when non-zero.

Parser is **duck-type**: read each `*.json`, check `schemaVersion === 1`, pluck the fields scouts need (`featureId`, `title`, `kind`, `ownedFiles[].path`, `tags`, `confidence`, `entrypoints[].path`, `updatedAt`). Don't recreate Zod validation; clawpatch already validated on write.

Tests use checked-in fixtures only — `subprocess.run(["clawpatch", ...])` MUST NOT appear in tests. Test fixtures: one valid file (schemaVersion=1, well-formed), one invalid-schema (schemaVersion=2), one malformed (truncated JSON). Assertions: list counts only valid; stderr contains both skip diagnostics; show by ID works for the valid one and returns clean not-found for invalid IDs.

## Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:8864-8973` — `cmd_prospect_list` (structural template for list)
- `plugins/flow-next/scripts/flowctl.py:8976-9100` — `cmd_prospect_read` (structural template for show)
- `plugins/flow-next/scripts/flowctl.py:21311-21388` — prospect argparse registration
- `plugins/flow-next/scripts/flowctl.py:13849-13978` — `cmd_ready` (aggregated list view, JSON-mirrors-text convention)
- `plugins/flow-next/scripts/flowctl.py:13851` — `ensure_flow_exists()` guard call site (DO NOT use for repo-map)
- https://github.com/openclaw/clawpatch/blob/main/src/types.ts — Zod source for `featureRecordSchema` (defines `schemaVersion: 1` literal + field set)

**Optional**:
- `plugins/flow-next/scripts/flowctl.py:9923-9991` — `cmd_strategy_read` (single-section reader pattern)
- Existing test patterns under `plugins/flow-next/tests/test_*.py`

## Key context

- clawpatch's `featureRecordSchema` writes `schemaVersion: 1` as a literal; future schema bumps will be observable.
- File layout: `.clawpatch/{config.json, project.json, features/, findings/, runs/, ...}` per `src/state.ts:statePaths()`.
- `featureId` is the stable key for `show`. `ownedFiles[].path` + `entrypoints[].path` are repo-relative.
- `updatedAt` ISO 8601 — used for `features_anchored.last_mapped` staleness signal downstream.

## Acceptance

- [ ] R3: `flowctl repo-map list`, `repo-map show --feature <id>`, `repo-map since-ref <ref>` all implemented with `--json` flag
- [ ] R3: All three handlers BYPASS `ensure_flow_exists()`; gate on `.clawpatch/` presence; return `count: 0` exit 0 when absent
- [ ] R3: `flowctl repo-map list --count` returns scalar count (for prime DE7 detection)
- [ ] R9: Per-file `schemaVersion != 1` emits one-line stderr diagnostic naming expected vs found and skips the file (never aborts list)
- [ ] R9: Malformed JSON triggers the same skip-with-diagnostic path
- [ ] R9: `list --json` includes `parse_skipped` count when non-zero
- [ ] Tests in `plugins/flow-next/tests/test_repo_map.py` cover: valid fixture parse, schemaVersion mismatch skip, malformed JSON skip, missing `.clawpatch/` returns count=0, `since-ref` overlaps `ownedFiles[]` paths against `git diff` output, **`since-ref` in non-git repo returns `success:false` + `error:"not-a-git-repo"` exit 0**, **`since-ref <bogus-ref>` returns `success:false` + `error:"unknown-ref"` exit 0**
- [ ] No `subprocess.run(["clawpatch", ...])` in test code (checked-in fixtures only)
- [ ] `plugins/flow-next/docs/flowctl.md` gains a `repo-map` group entry with flags + output schema

## Done summary
Shipped `flowctl repo-map list/show/since-ref` reader subcommands that parse clawpatch's `.clawpatch/features/*.json` index, the first flowctl reader for data outside `.flow/`. Handlers bypass `ensure_flow_exists()` and gate on `.clawpatch/` presence; absent state returns `count:0` exit 0 so prime's DE7 detection works without special-casing. R9 enforced: `schemaVersion != 1` and malformed JSON each emit one-line stderr diagnostics + skip without aborting `list`, with `parse_skipped` surfacing in `list --json`. `since-ref` returns the zero-exit `{success:false, error:<kind>}` envelope for non-git-repo and unknown-ref cases. New `unittest` suite (`test_repo_map.py`, 21 tests, production-path via subprocess) + checked-in fixtures land cleanly for fn-50.6's CI wiring. Codex impl-review caught one real schema drift (numeric `confidence` vs upstream Zod enum `"high"|"medium"|"low"`); fixed + locked in a test assertion + captured a memory entry on the fixture-must-mirror-upstream-Zod lesson. R3 and R9 met.
## Evidence
- Commits: e5b5d0c, 229b61b, 1bfe1a8
- Tests: python3 -m py_compile plugins/flow-next/scripts/flowctl.py, python3 -m unittest discover -s plugins/flow-next/tests -p "test_repo_map.py" -v  # 21/21 pass, python3 -m unittest discover -s plugins/flow-next/tests -p "test_prospect_cli.py"  # 34/34 pass (adjacent suite — no regression), flowctl codex impl-review fn-50-codebase-feature-map-flow-nextmap-skill.2 --base 4760f732d4adec4c5cd8900bef966bc3d7739586  # NEEDS_WORK (1 finding: confidence enum drift) -> SHIP after fix
- PRs: