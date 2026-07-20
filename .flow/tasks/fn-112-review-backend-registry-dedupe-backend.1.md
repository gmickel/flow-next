# fn-112-review-backend-registry-dedupe-backend.1 Registry hooks + generic driver (impl-review migration)

## Description
Registry hook extension + the generic review driver, migrated first for the three impl-review commands.

**Size:** L
**Files:** both flowctl.py copies (plugins/flow-next/scripts/flowctl.py + .flow/bin/flowctl.py), plugins/flow-next/tests/test_backend_spec.py (additions only)

### Approach

- Read fn-101 plan section on the review family first (.flow/specs/fn-101-flowctl-determinism-audit-what-still.md) plus the current BACKEND_REGISTRY (flowctl.py ~4020) and _dispatch_review_with_fallback.
- Extend BACKEND_REGISTRY entries with per-backend Python callables/fields for the genuine variance points: run_exec (spawn shape: codex sandbox flags, copilot session marker, cursor argv budget handling), resolve_spec (model/effort spec-string parsing), availability probe (the internal detection the old `check` commands wrapped - note the user-facing check triplet was REMOVED in fn-111; only internal probes remain), prompt-fit hints.
- One `cmd_backend_review(backend, kind)` driver implementing the shared pipeline (git-diff gathering block exists byte-identical at 4 sites - hoist ONCE), then migrate cmd_codex_review / cmd_copilot_review / cmd_cursor_review (the impl kind) onto it. Plan/completion kinds come in task 2 - design the driver for all three kinds now, migrate impl only.
- Argparse: parameterized registration for the migrated commands; CLI surface (names, flags, help) byte-compatible.
- HARD CONSTRAINTS: review receipts byte-compatible (schema + field order - pilot/land/ralph read them); <verdict>...</verdict> tag contract unchanged; fn-90 deterministic-cap behavior unchanged; RALPH_ITERATION stamping untouched in this task (task 2 dedupes it).
- Dual-copy mirrored byte-identical; sync-codex x2. NO git commands, no flowctl start/done.
- After each parser edit, smoke the surviving command with canonical flags (lesson from fn-111: a collapse dropped a neighboring required flag).

### Acceptance

- [ ] cmd_backend_review exists; the three impl-review commands route through it; their CLI surface and receipts byte-compatible (prove: run one codex impl-review against a fixture in mock/offline mode if available, else assert argparse + prompt-build parity via tests)
- [ ] Focused suites green: python3 scripts/run_tests_parallel.py --pattern "test_backend_spec.py" and --pattern "test_cursor_review_commands.py" and --pattern "test_review*.py"
- [ ] Both flowctl.py copies byte-identical; sync-codex idempotent

## Acceptance
- [ ] TBD

## Done summary
BACKEND_REGISTRY extended with per-backend hooks (run_exec/resolve_spec/check_probe/gather_diff/prompt_fit/resume policy/receipt-shape flags/extract_review/labels) wired lazily by _wire_backend_review_hooks; cmd_backend_review(args, backend, kind) generic driver implements the shared impl-review pipeline and the three impl-review commands route through it as thin wrappers. Genuine variance preserved as hooks: codex sandbox + prior-receipt-model tracking (PR #203 r2), copilot minted-UUID session marker, cursor argv-budget fit + persona override + resume-only sid. Receipts byte-compatible - key order verified exactly against HEAD~1 per backend (effort conditional matches old cursor omission). -194 LOC this task (large cut comes with plan/completion in .2). 4 new registry/driver tests. Host review: all four delegate-flagged uncertainty points resolved (receipt order proven, unused keys deferred to .2, diff-hoist pending .2 by design, codex asymmetry intentional); test-count reconciliation 132 baseline + 4 new = 136 (fn-111.3 prunes account for the 138->132 memory). OPERATIONAL NOTE: the delegate dispatch inherited a drifted cwd and edited the MAIN repo working tree; work was transferred to the worktree via patch (commit 83392e53), main cleaned via labeled stash (fn112-t1-duplicate..., safe to drop). All dispatch/gate blocks now carry explicit cd. Full parallel suite 83 files / 1829 tests / 0 failures / 81.4s.
## Evidence
- Commits: 83392e53
- Tests: python3 scripts/run_tests_parallel.py (83 files, 1829 tests, 0 failures, 81.4s), focused: test_backend_spec.py 136 / test_cursor_review_commands.py 32 / test_review* 45 / test_r22_invariant.py 38 all green, receipt key-order parity vs HEAD~1 verified per backend
- PRs: