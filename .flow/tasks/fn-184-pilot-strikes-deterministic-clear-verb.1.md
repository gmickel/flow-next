---
satisfies: [R1, R2]
---
# fn-184-pilot-strikes-deterministic-clear-verb.1 flowctl pilot strikes list/clear verb family

## Description
Spec fn-184 item 1 (#325). New `flowctl pilot strikes list [--json]` / `clear <spec-id> [--json]` / `clear --all [--json]` over the EXISTING skill-owned ledger contract verbatim: $(git rev-parse --git-common-dir)/flow-next/pilot-strikes.json, schema {"<spec-id>": {count, stage, reason, ts}}. Atomic writes (tmp+rename), missing/empty file tolerated, unknown spec-id on clear is a distinct not-found (not silent success), non-repo contexts fail cleanly. Clearing never mutates spec readiness (orthogonal signals - pinned by test). Worktree resolution must match the skill's (common dir shared across worktrees).

**Files:** plugins/flow-next/scripts/flowctl.py (new pilot strikes subcommands) + .flow/bin/flowctl.py dual copy + manifest regen; new focused tests

## Acceptance
R1, R2 of the spec. list empty-safe + --json shape; clear one/all atomic; not-found distinct; readiness untouched; worktree common-dir resolution; no traceback off-repo.

## Done summary
flowctl pilot strikes verb family per fn-184 R1-R2 (#325). New top-level pilot parser with a single strikes subgroup: list (empty-safe, exit 0 even off-repo with a note), clear <spec-id> (atomic tmp+rename, other entries untouched, distinct exit-3 not-found naming known keys, exact-key-then-expand_bare_spec_id matching), clear --all. Ledger contract verbatim from the skill: git-common-dir/flow-next/pilot-strikes.json (worktree .git file resolves through - tested with a real worktree); flowctl owns READ+CLEAR only, skill keeps its jq write sites for recording. Unparseable ledger = clean error, never silent discard. R2 pinned: clearing never mutates spec readiness. Frozen subprocess inventory + surface-leaf list learned the additions.
## Evidence
- Commits: 886f0dfd
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_pilot_strikes test_flowctl_surface test_review_prompt_constraints -q (32 OK), python3 scripts/run_tests_parallel.py (4450 OK)
- PRs: