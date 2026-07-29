# Honor tracker conflict tiebreak in deterministic status policy

## Goal & Context
<!-- scope: business -->

GitHub [#268](https://github.com/gmickel/flow-next/issues/268) exposed a contract gap after the tracker-determinism batch shipped: `tracker.conflictTiebreak` is configured and documented as `always-ask | flow-wins | tracker-wins`, but the deterministic status policy ignores it and unconditionally returns `status-deadlock`. The collision detector is correct; the selected recovery is missing.

This spec wires the existing setting into the provider-neutral decision layer without weakening the merge-evidence gate or restoring judgment prose to lifecycle skills. It is also the corrective feature included before publishing the tracker batch under the properly classified 3.6.0 minor release.

## Architecture & Data Models
<!-- scope: technical -->

Keep the fix inside the existing shared status path:

1. One shared validator reads `tracker.conflictTiebreak` from the persisted config: an absent key resolves to `always-ask`; only exact string enum values are accepted; malformed values return `INVALID_INPUT`.
2. Direct `status` invokes that validator before taking its create-first claim. Status-bearing facade operations (`push`, `pull`, and `reconcile`) invoke it at entry before their outer claim, provider I/O, local writes, or any sequence step.
3. `status.policy.decide` receives the validated value and resolves a detected deadlock before any ordinary terminal/in-progress rule.
4. `always-ask` preserves the current candidate-bearing `status-deadlock` conflict.
5. `flow-wins` returns the existing provider-neutral `apply` decision targeting `flow_norm`; terminal writes still require the already-derived clean `merged` evidence.
6. `tracker-wins` reuses `apply_local` when the tracker is terminal. The mirror case—Flow terminal after a merged PR while the tracker is active—cannot be represented durably by Flow's raw `open|done` spec state because the merged branch continues to normalize as `in_review`; it remains a typed conflict with no mutation instead of writing a state that immediately diverges again.

No new persistent status override, merge-base field, provider-specific policy, or agent-side request construction is introduced.

## Edge Cases & Constraints
<!-- scope: technical -->

- Preserve the load-bearing deadlock-first ordering recorded in memory `who-wins-ladder-must-check-the-2026-06-03`.
- Both mirror pairs are covered: `flow=in_progress × tracker=done` and `flow=done × tracker=in_progress`.
- `flow-wins` may close a tracker only when `flow_norm=done`, which remains impossible without clean merged-PR evidence.
- `tracker-wins` on tracker-terminal folds only the existing supported local terminal state; active task runtime records remain untouched, matching the existing tracker-terminal authority contract.
- Invalid or non-string persisted tiebreak values fail closed before direct-status or facade claims, executor calls, provider/local mutation, receipts, or `lastSyncedAt` changes. The public config setter must reject values outside the documented enum rather than preserve a latent typo.
- All four providers consume the same normalized decision; provider transition inability remains the existing structured capability/defer/error result.
- The propagation chain is mandatory for `flowctl_tracker` changes: `.flow/bin`, tracker manifest, Codex mirror twice.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_tracker_status test_tracker_facade test_tracker_config -q
uvx ruff@0.16.0 check plugins/flow-next/scripts/flowctl.py plugins/flow-next/scripts/flowctl_tracker/status plugins/flow-next/scripts/flowctl_tracker/facade/ops.py plugins/flow-next/tests/test_tracker_status.py plugins/flow-next/tests/test_tracker_facade.py plugins/flow-next/tests/test_tracker_config.py
```

Full release gate after implementation: `python3 scripts/run_tests_parallel.py` plus `uvx ruff@0.16.0 check .`.

## Boundaries / non-goals

- No redesign of Flow's `open|done` spec-status model.
- No persistent status override or attempt to represent post-merge active work on the already-merged spec; that requires a new spec/branch, not a sync tiebreak.
- No provider-specific recovery logic.
- No redesign of the broader tracker-sync docs. Update the canonical status-sync contract and public-doc mirror to describe the unrepresentable `tracker-wins` mirror, its no-mutation conflict, and the existing `pulled` receipt semantics.
- Version correction and downstream 3.6.0 publication occur after this spec lands, outside the implementation task.

## Strategy Alignment

Active tracks served by this plan:
- **Spec-driven team patterns** — makes the documented tracker projection contract executable and auditable.
- **Ralph autonomous mode** — preserves always-ask defer semantics while allowing explicitly configured deterministic recovery.
- **Cross-platform parity** — fixes the shared provider-neutral path and propagates every bundled copy.
- **Self-improving through normal work** — converts a live release-recovery finding into a regression-backed deterministic contract.

## Decision Context

- The bug is not the deadlock detector; removing or reordering it would revive the earlier silent-auto-close defect.
- Routing the configured choice inside the shared policy keeps direct `tracker status` and lifecycle-facade calls identical across Linear, GitHub, GitLab, and Jira.
- Refusing the unrepresentable `tracker-wins` mirror is safer than reopening a merged spec into a raw state that normalizes differently on the next invocation.
- One cohesive task is sufficient: the implementation, config validation, distribution propagation, tests, and changelog share the same small policy surface.

## Acceptance Criteria

- **R1:** `tracker.conflictTiebreak=always-ask` preserves the current `class: conflict`, `status-deadlock`, candidate-bearing envelope for both terminal×active orientations, with no mutation or `lastSyncedAt` advance.
- **R2:** `flow-wins` deterministically applies `flow_norm` through the existing provider-neutral write path for both orientations; terminal projection remains gated by clean merged-PR evidence and successful runs retain existing persistence/receipt semantics.
- **R3:** `tracker-wins` on a terminal tracker uses the existing local terminal fold, writes no provider mutation, advances durable sync state only after local persistence, and emits the existing pulled/aggregate receipt path.
- **R4:** `tracker-wins` when the tracker is active and Flow is terminal returns a typed, candidate-bearing unrepresentable conflict with no local/provider mutation rather than creating a non-convergent reopened spec.
- **R5:** Missing config defaults to `always-ask`; malformed persisted values return the tracker runtime's typed `INVALID_INPUT`. Invalid `config set tracker.conflictTiebreak` inputs retain the existing strict-enum CLI contract (`exit 1` with `{success:false,error:...}`). Direct status validates before its claim; status-bearing facades validate at entry before their outer claim or any sequence step, producing zero executor calls, zero local changes, no receipt, and no `lastSyncedAt` advance.
- **R6:** Unit and facade-level regression tests cover both collision orientations, all three configured values, direct status plus lifecycle-facade consumption, malformed-config zero-side-effect behavior, receipt/`lastSyncedAt` invariants, and one shared normalized decision across all four provider fixtures.
- **R7:** Canonical code, `.flow/bin`, distribution manifest, and Codex mirror remain in parity; canonical status-sync docs and the public-doc mirror match runtime behavior; focused tests, the full suite, and Ruff pass; `CHANGELOG.md` records the fix under Unreleased and closes #268 through the implementation PR.

## Early proof point

Task fn-146-honor-tracker-conflict-tiebreak-in.1 proves the existing decision types can express both supported tiebreak outcomes while retaining the unrepresentable mirror as a safe conflict. If that cannot converge without a new persistent override, stop rather than expanding the spec-status model inside this bug fix.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | always-ask unchanged | fn-146-honor-tracker-conflict-tiebreak-in.1 | — |
| R2 | flow-wins provider-neutral apply | fn-146-honor-tracker-conflict-tiebreak-in.1 | — |
| R3 | tracker-wins terminal local fold | fn-146-honor-tracker-conflict-tiebreak-in.1 | — |
| R4 | unrepresentable mirror fails closed | fn-146-honor-tracker-conflict-tiebreak-in.1 | — |
| R5 | config default and validation | fn-146-honor-tracker-conflict-tiebreak-in.1 | — |
| R6 | direct/facade/provider regression matrix | fn-146-honor-tracker-conflict-tiebreak-in.1 | — |
| R7 | distribution, gates, changelog, issue closure | fn-146-honor-tracker-conflict-tiebreak-in.1 | — |
