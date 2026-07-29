---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-146-honor-tracker-conflict-tiebreak-in.1 Honor conflict tiebreak in shared status policy

## Description
Wire the existing `tracker.conflictTiebreak` configuration into the shared deterministic status decision and execution path, validate the enum, preserve safe conflict behavior for the unrepresentable mirror, add direct/facade/provider regression coverage, propagate bundled copies, and record the fix under Unreleased.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl_tracker/status/policy.py`, `plugins/flow-next/scripts/flowctl_tracker/status/verb.py`, `plugins/flow-next/scripts/flowctl_tracker/facade/ops.py`, `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_tracker_status.py`, `plugins/flow-next/tests/test_tracker_facade.py`, `plugins/flow-next/tests/test_tracker_config.py`, `plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md`, bundled `.flow/bin` and Codex mirrors, `CHANGELOG.md`, public-doc tracker-sync and changelog mirrors

### Approach

- Preserve the deadlock-first predicate and pass a validated tiebreak into the provider-neutral decision layer.
- Add one shared validator: absent key defaults to `always-ask`; only exact string enum values pass. Call it before the direct-status claim and at `push`/`pull`/`reconcile` facade entry, before the outer claim or any sequence mutation.
- Reuse the existing `Decision("apply")`, `Decision("apply_local")`, persistence, receipt, and provider write paths; do not duplicate transport or local-write mechanics.
- Preserve `decision_as_error()` for `always-ask` and enrich the unrepresentable mirror conflict without inventing a persistent status override.
- Follow existing strict config-enum validation patterns in `flowctl.py`: invalid `config set` values keep the current exit-1 `{success:false,error:...}` contract; malformed persisted runtime config returns typed `INVALID_INPUT`.
- Correct the canonical status-sync reference and public-doc mirror for the unrepresentable `tracker-wins` mirror and existing `pulled` receipt path.
- Run the required distribution propagation chain after canonical implementation.

### Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl_tracker/status/policy.py:249-365` — decision ladder and deadlock ordering
- `plugins/flow-next/scripts/flowctl_tracker/status/verb.py:282-530` — config snapshot, apply/apply_local, persistence and receipts
- `plugins/flow-next/scripts/flowctl_tracker/facade/ops.py:190-840` — status-bearing facade entry points and pre-sequence claims
- `plugins/flow-next/tests/test_tracker_status.py:190-235` — current deadlock unit guard
- `plugins/flow-next/tests/test_tracker_status.py:760-830` — status integration/persistence patterns
- `plugins/flow-next/tests/test_tracker_facade.py` — lifecycle-facade status consumption and aggregate receipts
- `plugins/flow-next/scripts/flowctl.py:1120-1170` — tracker config schema/defaults

**Optional** (reference as needed):
- `plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md:258-295` — intended tiebreak contract
- `.flow/memory/bug/runtime-errors/who-wins-ladder-must-check-the-2026-06-03.md` — ordering regression history
- `plugins/flow-next/tests/test_tracker_distribution.py` — bundled parity gate

### Key context

- `flow-wins` on Flow terminal is safe only because `flow_norm=done` already requires clean merged-PR evidence.
- A merged Flow spec cannot durably adopt a tracker-active state using only raw `spec.status=open|done`; reopening normalizes to `in_review`, so the mirror `tracker-wins` choice must remain a typed conflict.
- The release correction itself is not part of this task; stage only the implementation fix under `## Unreleased`.

## Acceptance
- [ ] `always-ask`, `flow-wins`, and `tracker-wins` are consumed by the shared deadlock decision with both collision orientations covered.
- [ ] `flow-wins` reuses provider-neutral apply and existing merge-evidence/persistence/receipt gates.
- [ ] Tracker-terminal `tracker-wins` reuses the local terminal fold without a provider write.
- [ ] Tracker-active `tracker-wins` against merged Flow terminal fails closed as an explicit unrepresentable conflict with no mutation.
- [ ] Missing config defaults to `always-ask`; malformed stored values return typed `INVALID_INPUT` before direct/facade claims or sequence work; invalid config-set values retain the existing strict-enum exit-1 error envelope.
- [ ] Direct status, lifecycle facade, malformed-config zero-side-effect behavior (zero executor calls/local changes/receipt/`lastSyncedAt` advance), and four-provider fixtures have regression coverage.
- [ ] Canonical, `.flow/bin`, manifest, Codex mirror, canonical status-sync docs, and public-doc mirror are synchronized; focused tests, full suite, and Ruff pass.
- [ ] `CHANGELOG.md` records the fix under Unreleased and the eventual PR closes GitHub #268.


## Done summary
Implemented strict `tracker.conflictTiebreak` handling across direct status and facade operations: `always-ask`, `flow-wins`, and `tracker-wins` now use the shared policy with fail-fast persisted-config validation and zero-side-effect unrepresentable conflicts. Added provider-parity and facade regression coverage, propagated bundled/Codex copies, and updated canonical plus public documentation; Codex implementation review returned SHIP.
## Evidence
- Commits: 30341e0525e356f73dfc47c64d3b850d9e65bbac, c6db2eb84bcde20792a932ca37c496a617c7b4d8
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_status test_tracker_facade test_tracker_config -q, cd plugins/flow-next/tests && python3 -m unittest test_tracker_status test_tracker_facade test_tracker_config test_tracker_distribution -q, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check plugins/flow-next/scripts/flowctl.py plugins/flow-next/scripts/flowctl_tracker/status/policy.py plugins/flow-next/scripts/flowctl_tracker/status/verb.py plugins/flow-next/scripts/flowctl_tracker/facade/ops.py plugins/flow-next/tests/test_tracker_status.py plugins/flow-next/tests/test_tracker_facade.py plugins/flow-next/tests/test_tracker_config.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh (twice; idempotent and validation guards green), cd /Users/gordon/work/flow-next.dev && pnpm build
- PRs: