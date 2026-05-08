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
- **T1 follow-up — hardcoded `.flow/epics/<id>.json` paths.** `smoke_test.sh` and `prospect_smoke_test.sh` contain ~7 direct filesystem reads of `.flow/epics/<id>.json` that bypass the flowctl CLI. T1 surfaced these as a known follow-up. Rewrite each to either (a) read via `flowctl show <id> --json` / `flowctl specs --json`, or (b) probe via `find_spec_json_path`-equivalent shell logic (`.flow/specs/<id>.json` first, fall back to `.flow/epics/<id>.json`) so the assertions work post-migration AND on alias-mode 0.x repos. <!-- Updated by plan-sync: T1 noted hardcoded epics/ filesystem paths in smoke tests as T14 follow-up -->
- New `alias_smoke.sh` covers high-value alias paths:
  1. `flowctl epic create` -> `cmd_spec_create` dispatch + stderr deprecation present.
  2. `flowctl epics --json` payload contains BOTH `"specs":` and `"epics":` keys (same array, R31 dual-emit).
  3. `flowctl tasks --epic <id> --json` -> matches `flowctl tasks --spec <id> --json` AND emits stderr deprecation; persisted task JSON contains `"spec":` only (no `"epic":`).
  4. `flowctl spec export-cognitive-aid <id> --section epic` -> matches `--section spec` AND emits stderr deprecation; payload top-level is `"spec":`.
  5. Top-level `flowctl show fn-X` (NOT renamed; no `flowctl spec show` introduced) resolves both spec and task ids identically pre- and post-rename.
  6. `EPICS_FILE=...` env var on `flowctl next` works AND emits stderr deprecation; `SPECS_FILE=...` is silent.
  7. `flowctl next --json` blocked-task output contains BOTH `reason: "blocked_by_spec_deps"` AND `legacy_reason: "blocked_by_epic_deps"`.
  Each assertion: stderr contains the deprecation marker; stdout JSON matches canonical exactly. <!-- Updated by plan-sync: T2 ships `_emit_rename_deprecation` as one-shot per process per legacy form (set-keyed `_RENAME_DEPRECATION_EMITTED`); each assertion runs in its own subshell to guarantee a fresh emission. -->
- New `migration_smoke.sh` covers:
  1. Pre-1.0 fixture (`.flow/epics/fn-X.json`, no sentinel) -> `flowctl migrate-rename --dry-run` prints plan, no mutation. <!-- Updated by plan-sync: T3 also writes `.flow/.banner-acknowledged` on --dry-run; assert the ack file lands and re-runs do not re-emit the banner -->
  2. Same fixture -> `flowctl migrate-rename --yes` migrates; sentinel + backup `.complete` marker + `.flow/.migration-manifest` (top-level) present.
  3. `.flow/.backup-pre-1.0/.migration-manifest` does NOT exist (manifest lives at top level, not inside backup).
  4. Idempotent re-run.
  5. `flowctl migrate-rollback --yes` restores pre-1.0 layout; `.flow/.backup-pre-1.0/` remains intact post-rollback.
  6. Post-migration spec creation -> `migrate-rollback --yes` FAILS with exit 1 + manifest-mismatch message.
  7. Post-migration spec creation -> `migrate-rollback --yes --force-overwrite-post-migration-changes` proceeds.
  8. Concurrency: two parallel `migrate-rename --yes` invocations, second waits. <!-- Updated by plan-sync: T3 ships PID-liveness reclaim; add stale-lock test (write fake PID inside `.flow/.migrating/`, reclaim succeeds when PID is dead via `os.kill` POSIX / `OpenProcess` Windows) -->
  9. Crash recovery — T3 ships a 4-case decision tree; smoke covers each case: <!-- Updated by plan-sync: T3 done summary enumerated 4 distinct cases; original spec said "kill mid-mutation" generically -->
     - 9a. No backup at all (crashed before backup started) -> migrate restarts cleanly from step 4.
     - 9b. Partial backup (no `.complete` marker) -> migrate detects + restarts the backup phase.
     - 9c. Complete backup, no manifest (crashed between backup and step 6) -> migrate detects + reinitializes manifest, retries.
     - 9d. Mid-migration crash (manifest populated, sentinel missing) -> migrate restores from backup by COPY (not move), retries.
  10. Read-only `.flow/`: `flowctl migrate-rename --yes` on a 0.x repo fails with exit code 1 + clear stderr message; `flowctl migrate-rename --yes` on an ALREADY-migrated 1.0 repo (sentinel present) on read-only fs is a no-op (idempotency check runs BEFORE read-only refusal). <!-- Updated by plan-sync: T3 ships idempotency-before-readonly ordering -->
  11. Atomic sentinel write — kill process during step 11 (sentinel write); restart finds either no sentinel (retries step 11) or fully written sentinel (idempotent skip), never a partial-byte sentinel. <!-- Updated by plan-sync: T3 ships atomic sentinel write via tmpfile + os.replace -->
  12. SHA256 task-drift detection — modify a task JSON file post-migration to a value not in the manifest's recorded SHA256, then run `flowctl migrate-rollback --yes`; rollback REFUSES with stderr naming the drifted file. <!-- Updated by plan-sync: T3 ships SHA256 task-drift detection in manifest; not previously specified -->
  13. Mid-migration contamination wipe — pre-existing `.flow/.migration-manifest` from a prior interrupted migrate is wiped clean before re-init on retry. <!-- Updated by plan-sync: T3 done summary called this out explicitly -->
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
- [ ] `smoke_test.sh` + `prospect_smoke_test.sh` no longer read `.flow/epics/<id>.json` paths directly; assertions go through `flowctl` or probe both legacy + canonical paths.
- [ ] `alias_smoke.sh` covers all 7 high-value alias paths above; passes in CI.
- [ ] `migration_smoke.sh` covers all 13 scenarios above (10 originally + 3 added per T3 implementation: 11 atomic sentinel write, 12 SHA256 task-drift detection, 13 mid-migration contamination wipe); passes on Linux + macOS (Windows lockfile coverage in T3 acceptance). <!-- Updated by plan-sync: scenario count expanded from 10 -> 13 to match T3's actual surface -->
- [ ] `ci_test.sh` has a new section guarding against `flowctl epic` references in canonical (excludes deprecation-context comments via grep -v pattern).
- [ ] `FLOW_NO_DEPRECATION=1` smoke: alias_smoke.sh asserts banner suppressed when env var set.
- [ ] Banner-suppression smoke (T4): `migration_smoke.sh` (or a new `banner_smoke.sh`) asserts each of `FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH=/tmp/x`, `FLOW_NO_AUTO_MIGRATE=1`, sentinel-present, and `.banner-acknowledged < 7d` independently suppress the 6-line banner on stderr; pre-1.0 fixture without any of those emits the full 6-line banner verbatim and `--json` stdout still parses cleanly with `jq`. <!-- Updated by plan-sync: T4 ships banner suppression matrix that smoke should cover end-to-end -->
- [ ] Future-version banner smoke (T4): seed `.flow/.flow_version` to `2.0.0`; assert `flowctl <verb>` emits the one-line "newer flow-next" warning to stderr and the subcommand's exit code is preserved (NOT forced to non-zero). v1.x sentinel (`1.5.2`) is silent. <!-- Updated by plan-sync: T4 forward-compat path on major >= 2 -->
- [ ] Top-level `flowctl show fn-X` smoke confirms NO new `flowctl spec show` subcommand was introduced.

## Done summary

## Evidence
- Commits:
- Tests:
- PRs:
