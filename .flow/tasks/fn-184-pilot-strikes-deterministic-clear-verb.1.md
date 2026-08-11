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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
