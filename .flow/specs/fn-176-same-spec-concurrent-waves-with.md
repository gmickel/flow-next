# Overview

85% of 684 measured subagent dispatches ran with zero overlapping sibling; `flow-next:worker` dispatches average 17 minutes. The wave machinery (worktree isolation, parallel-wave worker contract, conductor join) shipped long ago but its trigger is a vague judgment call ("prefer a concurrent wave when tasks are safely disjoint") that almost never fires. Reviewers additionally block ~19% of pipeline wall fully serially. This spec replaces the judgment call with an explicit fail-closed dispatch rule and folds in reviewer overlap — the two remaining large speed levers (est. 15–20% + 4–7%).

**Evidence standing: designed from measured serialization in the flow-efficiency replay campaign (results 06 §2, 01 §6). The sequential-equivalence gate below is part of the change itself — no separate eval campaign.** This spec is the primary dogfood target for the fn-spec on task shape: its own tasks should come out how-shaped, `touches:`-declared, restatement-free.

## Goal & Context

Make same-spec concurrent worker waves the DEFAULT whenever an explicit, checkable rule passes, and let review of a completed task overlap implementation of a dep-independent one — without weakening plan-sync's consistency role or adding any flowctl code.

## Architecture & Data Models

Prose-only orchestration change in `skills/flow-next-work/phases.md` (+ small plan-review rubric line). Depends on the task-shape spec landing `touches:`.

**Wave dispatch rule (replaces the vague preference; fail-closed):** dispatch tasks A and B concurrently iff ALL of: same spec; wave size ≤ 3; neither depends on the other, transitively (`flowctl dep`); `touches(A) ∩ touches(B) = ∅`; neither touches the always-serial set (`.flow/`, lockfiles, migration dirs, codegen outputs, spec/task files); every dispatched task HAS a `touches:` declaration. Any missing declaration, any intersection, any doubt → serial (today's behavior — the rule's failure mode is the status quo).

**Safety is structural, not the check:** workers run in isolated worktrees, so a wrong dispatch surfaces at the join as a merge conflict → conductor serially re-runs the losing task and records the collision in the receipt (making bad `touches:` declarations visible to plan review). A prose-grade check with a structural backstop; no semantic prediction anywhere (fn-83's decision record untouched — this is declared-intent enforcement, same trust model as `deps`).

**Reviewer overlap:** review(N) may run concurrently with implement(N+1) only when N+1 is dep-independent of N AND outside N's plan-sync target set (spec-level reading of the same dep graph). **Plan-sync remains the barrier before any dependent work anchors.** Join → review → plan-sync → next frontier is otherwise unchanged.

## Edge Cases & Constraints

- Parallel-wave worker terminal contract is already shipped and is NOT modified.
- Conflict at join must never auto-resolve: serial re-run of the conflicted task from the joined state, always.
- A wave is same-spec only in v1; cross-spec waves are out of scope.
- If `flowctl dep` shows any path between candidates, serial — transitive, not direct-only.
- Reviewer overlap never reorders receipts: done(N) still precedes plan-sync(N) precedes any anchor that could read N's downstream updates.

## Acceptance Criteria

- **R1:** phases.md carries the explicit dispatch rule verbatim in place of the judgment prose; fail-closed on every listed condition. Errors: missing `touches:` → serial; ambiguity → serial; these ARE the error paths and must be stated in the prose.
- **R2:** Join handling specifies merge-conflict → serial re-run + collision recorded in the receipt. Errors: a conflict must never be auto-resolved or silently dropped.
- **R3:** Reviewer-overlap rule present with both conditions and the plan-sync barrier stated. Errors: overlap with a dependent task is the failure this R prevents.
- **R4:** Plan-review rubric checks `touches:` plausibility and flags overlapping pairs. Errors: none beyond prose.
- **R5 (the gate):** a replayed multi-task spec run under wave dispatch reproduces the sequential run's test outcomes (same tests green at completion). Errors: any divergence blocks landing — this is the sequential-equivalence gate, executed as part of this spec's verification, not a separate campaign.
- **R6:** Mirrors, docs-site, CHANGELOG per conventions. Errors: parity red blocks merge.

## Boundaries

- No flowctl code, no deterministic checker binary (prose + structure only).
- No cross-spec waves, no wave >3, no predictive/semantic gating of any kind.
- No change to worker.md's wave contract or to plan-sync's own behavior.
- No reviewer-content changes (overlap is scheduling only).

## Decision Context

A Python disjointness checker was considered and rejected: the merge-conflict backstop makes prose-grade checking safe (wrong answer costs one serial retry, never correctness), and Gordon explicitly preferred no new deterministic machinery. Wave ≤3 and same-spec-only keep v1's blast radius small; both are stated limits, not architecture, and can be lifted by evidence later. Reviewer overlap folded in here rather than its own spec because it shares the identical safety predicate and edit site — one orchestration change, one gate.
