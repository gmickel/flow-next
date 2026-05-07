---
satisfies: [R29]
---

## Description

Smoke test at `plugins/flow-next/scripts/make-pr_smoke_test.sh` covering the `flowctl epic export-cognitive-aid` aggregator (Task 1) and the skill's body-rendering / `--dry-run` (Tasks 3-6 once they land). Tests deterministic plumbing only — body rendering tests assert that `--dry-run` produces stdout output containing expected sections, not exact text matching.

**Size:** M (one new test file ~250 LOC, fixture builder + 11 assertions per epic spec R29)
**Files:** `plugins/flow-next/scripts/make-pr_smoke_test.sh`

Can run early (depends only on Task 1). Body-rendering assertions can be skipped or marked TODO until Tasks 3-6 land; minimum viable smoke is the export-cognitive-aid plumbing assertions.

## Approach

- **Template = `prospect_smoke_test.sh`** (multi-section JSON-shape assertions + fixture builder via Python heredoc). `audit_smoke_test.sh` for simpler cases. `strategy_smoke_test.sh` for cross-platform Windows handling.
- **Header banner** + `set -euo pipefail` + standard SCRIPT_DIR/PLUGIN_ROOT/FLOWCTL setup.
- **Helpers** to copy verbatim from `strategy_smoke_test.sh`: `to_winpath`, `pick_python`, `assert_rc`, `assert_grep`, `assert_grep_re`, `ok`, `fail`. Refuse-to-run-from-plugin-repo guard.
- **TEST_DIR** with `RUNNER_TEMP` / `TMPDIR` / `/tmp` fallback (from `prospect_smoke_test.sh`). Cleanup trap (with `KEEP_TEST_DIR=1` opt-out for debugging).
- **Fixture builder** via Python heredoc importing flowctl directly (pattern at `prospect_smoke_test.sh:156-197`). Sets up:
  - Empty git repo with main branch
  - `flowctl init`
  - One epic with 3 R-IDs
  - 2 done tasks with `done_summary` + `evidence.commits` (real commits via `git commit --allow-empty`)
  - 1 decision memory entry (`knowledge/decisions/`)
  - 1 bug memory entry (`bug/runtime-errors/`)
  - 1 architecture-patterns entry (`knowledge/architecture-patterns/`)
  - GLOSSARY.md with 2 terms (one added in HEAD vs base)
  - STRATEGY.md with 5 sections filled
  - 1 deferred review finding at `.flow/review-deferred/<branch-slug>.md`
  - Multi-file diff with cross-module imports (e.g. `plugins/flow-next/skills/foo.md` and `scripts/bar.sh` both new)
- **Test cases (T1-T11 per spec R29):**
  - T1: `flowctl epic export-cognitive-aid <epic> --base main --json` returns valid JSON with all top-level keys (`epic`, `tasks`, `tasks_summary`, `memory_during_epic`, `glossary_changes`, `strategy_alignment`, `diff_summary`, `review_receipts`, `deferred_findings`)
  - T2: `--section diff` returns only diff slice; full payload accessible without flag
  - T3: `diff_summary.files[]` populated; per-file `additions`+`deletions` counts match `git diff --numstat`
  - T4: `memory_during_epic.decisions[]` includes the seeded decision; `bugs[]` includes the bug; `architecture_patterns[]` includes the arch entry
  - T5: `glossary_changes.added[]` includes the new term; `removed` empty since none removed
  - T6: `strategy_alignment.tracks_served[]` populated when STRATEGY.md present (parse track names from raw markdown)
  - T7: Empty-epic handling — epic with 0 tasks → `tasks_summary.total: 0`, `done: 0`, `uncovered_r_ids: [<all R-IDs>]`. Subcommand exits 0 (graceful).
  - T8: All-empty optional inputs (no STRATEGY.md / no memory / no glossary / no deferred) → all empty arrays, no crash, subcommand exits 0
  - T9: Branch-no-commits-ahead → `cmd_epic_export_cognitive_aid` returns `diff_summary.files: []` (no error; caller handles)
  - T10: Skill `--dry-run` produces stdout output containing `## TL;DR`, `## R-ID coverage`, `## Critical changes` markers (loose match — exact text varies). NO `gh pr create` invoked. NO branch pushed. (This test SKIPS until Tasks 3-6 land — emit `SKIP` until skill exists.)
  - T11: Mermaid trigger logic — fixture with cross-module imports → body contains ` ```mermaid ` codefence; fixture without → body has no mermaid codefence. (SKIPS until Tasks 3-6 + Task 5 land.)
- **PASS/FAIL summary** at end: `echo "PASS=$PASS FAIL=$FAIL"; exit $FAIL`.
- **CI integration:** smoke is invoked by `ci_test.sh` matrix (already runs on ubuntu/macos/windows per fn-32 / 0.41.0 changelog). Cross-platform Windows handling: ensure `TEST_DIR` / FLOWCTL / `cygpath -m` / `assert_grep here-string` patterns from `strategy_smoke_test.sh`.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/strategy_smoke_test.sh:1-130` — most-recent / cleanest pattern
- `plugins/flow-next/scripts/prospect_smoke_test.sh:156-209` — fixture builder + repo init pattern
- `plugins/flow-next/scripts/audit_smoke_test.sh` — simpler plumbing test pattern (closer to make-pr's deterministic plumbing)

**Optional:**
- `plugins/flow-next/scripts/ci_test.sh` — CI matrix integration point (where to register the new smoke)

## Acceptance

- [ ] `plugins/flow-next/scripts/make-pr_smoke_test.sh` exists, executable, runs in <60s on local machine.
- [ ] All T1-T9 cases pass against fixture (deterministic plumbing tests). T10-T11 conditionally pass once Tasks 3-6 + Task 5 land — skip with `SKIP` marker until then; CI doesn't block.
- [ ] Cross-platform: passes on macOS + Linux (Windows handled via the `to_winpath` / `assert_grep here-string` patterns from strategy_smoke_test.sh).
- [ ] No real PRs created during the test (test never invokes `gh pr create`; fixture uses local-only git repo with no remote).
- [ ] PASS/FAIL summary emitted at end. Failing assertions print actionable error messages.
- [ ] Test registered in `ci_test.sh` matrix or equivalent so CI catches regressions.

## Done summary

_(populated by /flow-next:work after task completes)_

## Evidence

_(populated by /flow-next:work after task completes)_
