---
satisfies: [R20, R26, R27]
---

## Description

Rewire all smoke tests to assert the new `flowctl spec *` surface. Add a separate `alias_smoke.sh` that exercises high-value alias paths and verifies the deprecation banner appears on stderr. Add migration smoke tests covering `flowctl migrate-rename --dry-run`, `--yes`, `migrate-rollback`, the lockfile concurrency case, crash recovery, the read-only-fs failure mode, and post-migration-write rollback safety. Add CI guard against `flowctl epic` references in canonical prose.

**Size:** M
**Files:**
- `plugins/flow-next/scripts/smoke_test.sh` (95 refs)
- `plugins/flow-next/scripts/make-pr_smoke_test.sh` (53 refs)
- `plugins/flow-next/scripts/ralph_smoke_test.sh` (34 refs)
- `plugins/flow-next/scripts/ci_test.sh` (22 refs)
- `plugins/flow-next/scripts/prospect_smoke_test.sh` (26 refs)
- `plugins/flow-next/scripts/ralph_e2e_test.sh` (8 refs)
- `plugins/flow-next/scripts/ralph_e2e_short_rp_test.sh` (10 refs)
- `plugins/flow-next/scripts/ralph_e2e_rp_test.sh` (9 refs)
- `plugins/flow-next/scripts/ralph_smoke_rp.sh` (4 refs)
- `plugins/flow-next/scripts/plan_review_prompt_smoke.sh` (5 refs)
- NEW: `plugins/flow-next/scripts/alias_smoke.sh`
- NEW: `plugins/flow-next/scripts/migration_smoke.sh`

## Approach

- Rewire pattern: factor existing smoke tests into a shared assertion function `assert_spec_workflow()` parameterized by verb. Run the full suite with `verb=spec` (canonical). The alias layer is verified separately, not by doubling the suite.
- New `alias_smoke.sh` covers high-value alias paths:
  1. `flowctl epic create` -> `cmd_spec_create` dispatch + stderr deprecation present.
  2. `flowctl epics --json` payload contains BOTH `"specs":` and `"epics":` keys (same array, R31 dual-emit).
  3. `flowctl tasks --epic <id> --json` -> matches `flowctl tasks --spec <id> --json` AND emits stderr deprecation; persisted task JSON contains `"spec":` only (no `"epic":`).
  4. `flowctl spec export-cognitive-aid <id> --section epic` -> matches `--section spec` AND emits stderr deprecation; payload top-level is `"spec":`.
  5. Top-level `flowctl show fn-X` (NOT renamed; no `flowctl spec show` introduced) resolves both spec and task ids identically pre- and post-rename.
  6. `EPICS_FILE=...` env var on `flowctl next` works AND emits stderr deprecation; `SPECS_FILE=...` is silent.
  7. `flowctl next --json` blocked-task output contains BOTH `reason: "blocked_by_spec_deps"` AND `legacy_reason: "blocked_by_epic_deps"`.
  Each assertion: stderr contains the deprecation marker; stdout JSON matches canonical exactly.
- New `migration_smoke.sh` covers:
  1. Pre-1.0 fixture (`.flow/epics/fn-X.json`, no sentinel) -> `flowctl migrate-rename --dry-run` prints plan, no mutation.
  2. Same fixture -> `flowctl migrate-rename --yes` migrates; sentinel + backup `.complete` marker + `.flow/.migration-manifest` (top-level) present.
  3. `.flow/.backup-pre-1.0/.migration-manifest` does NOT exist (manifest lives at top level, not inside backup).
  4. Idempotent re-run.
  5. `flowctl migrate-rollback --yes` restores pre-1.0 layout; `.flow/.backup-pre-1.0/` remains intact post-rollback.
  6. Post-migration spec creation -> `migrate-rollback --yes` FAILS with exit 1 + manifest-mismatch message.
  7. Post-migration spec creation -> `migrate-rollback --yes --force-overwrite-post-migration-changes` proceeds.
  8. Concurrency: two parallel `migrate-rename --yes` invocations, second waits.
  9. Crash recovery: kill process mid-mutation, restart -> detects partial state, recovers.
  10. Read-only `.flow/`: `flowctl migrate-rename --yes` fails with exit code 1 + clear stderr message.
- `ci_test.sh` gets a NEW R19/R30 validation block: grep for `flowctl epic` references in canonical skill / agent / command files (FAIL if found, except in deprecation-context comments tagged `# alias-context:` or similar). Mirrors the existing R17/R19 (DDD/strategy fluff) two-tier guard pattern.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/smoke_test.sh` -- structure of existing assertions; identify the function-extraction points.
- `plugins/flow-next/scripts/ci_test.sh` -- existing R17/R19 grep-guard pattern to model the new alias-vocabulary guard.

## Key context

- The alias layer shares the same `cmd_spec_*` handlers as the canonical surface (per T1+T2). Smoke testing the canonical path is sufficient for behavior; alias_smoke.sh validates the warning + dispatch correctness, not duplicate behavior.
- Cross-platform: migration_smoke.sh's lockfile concurrency test runs in CI on Linux/macOS/Windows per commit `26bba86`.

## Acceptance

- [ ] All listed smoke scripts updated; existing test coverage maintained.
- [ ] `alias_smoke.sh` covers all 7 high-value alias paths above; passes in CI.
- [ ] `migration_smoke.sh` covers all 10 scenarios above; passes on Linux + macOS (Windows lockfile coverage in T3 acceptance).
- [ ] `ci_test.sh` has a new section guarding against `flowctl epic` references in canonical (excludes deprecation-context comments via grep -v pattern).
- [ ] `FLOW_NO_DEPRECATION=1` smoke: alias_smoke.sh asserts banner suppressed when env var set.
- [ ] Top-level `flowctl show fn-X` smoke confirms NO new `flowctl spec show` subcommand was introduced.

## Done summary

## Evidence
- Commits:
- Tests:
- PRs:
