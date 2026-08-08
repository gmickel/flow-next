# Overview

85% of 684 measured subagent dispatches ran with zero overlapping sibling; `flow-next:worker` dispatches average 17 minutes. The wave machinery (worktree isolation, parallel-wave worker contract, conductor join) shipped long ago but its trigger is a vague judgment call ("prefer a concurrent wave when tasks are safely disjoint") that almost never fires. Reviewers additionally block ~19% of pipeline wall fully serially. This spec replaces the judgment call with an explicit fail-closed dispatch rule and folds in reviewer overlap - the two remaining large speed levers (est. 15-20% + 4-7%).

**Evidence standing: designed from measured serialization in the flow-efficiency replay campaign (results 06 §2, 01 §6). The sequential-equivalence gate below is part of the change itself - no separate eval campaign.** This spec is the primary dogfood target for fn-175's task shape: its own tasks should come out how-shaped, Touches:-declared, restatement-free.

## Goal & Context

Make same-spec concurrent worker waves the DEFAULT whenever an explicit, checkable rule passes, and let review of a completed task overlap implementation of a dep-independent one - without weakening plan-sync's consistency role or adding any flowctl code.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_work_reached_path_routes test_skill_prose_diet -q
./scripts/sync-codex.sh && ./scripts/sync-codex.sh && git status --short   # idempotent
```

## Architecture & Data Models

Prose-only orchestration change. Edit sites:

1. `plugins/flow-next/skills/flow-next-work/phases.md` 3a: replace the vague preference paragraph with the explicit fail-closed dispatch rule (R1): dispatch concurrently iff ALL of - same spec; wave ≤ 3; no transitive dep path either way (`flowctl dep`); disjoint `**Touches:**` declarations; neither touches the always-serial set (`.flow/`, lockfiles, migration dirs, codegen outputs, spec/task files); every dispatched task HAS a Touches: declaration. Any missing declaration, any intersection, any doubt → serial (today's behavior is the failure mode).
2. Same file, 3d: join conflict handling (R2) - a merge conflict at join is never auto-resolved; the conductor serially re-runs the losing task from the joined state and records the collision in the receipt (a stage line: `stage: wave-join - failed(collision: <tasks> <paths>)` per fn-178), making bad Touches: declarations visible to plan review.
3. Same file, 3d/3f: reviewer-overlap rule (R3) - review(N) may run concurrently with implement(N+1) only when N+1 is dep-independent of N AND outside N's plan-sync target set; plan-sync remains the barrier before any dependent work anchors; done(N) → plan-sync(N) ordering unchanged.
4. Plan-review rubric (R4): extend `plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md` criterion 3 (Parallelizability) and `references/plan-review-prompt.md` criterion 8 (Consistency) with Touches: plausibility + overlapping-pair flagging. plan-review-prompt.md is byte-pinned: carries the full parity chain (PLAN_REVIEW_PROMPT_FALLBACK sync, dual flowctl.py copy, both hash pins, rendered-fixture rebaseline) - same shape as fn-174.
5. **R5 equivalence gate (executed in this spec's verification):** a two-task sandbox spec with disjoint Touches: runs once serially and once under the wave rule (isolated worktrees, conductor join); both runs must end with the same tests green. Recorded in the task evidence; any divergence blocks landing.

## Edge Cases & Constraints

- Parallel-wave worker terminal contract is already shipped and NOT modified; worker.md untouched.
- Conflict at join must never auto-resolve; serial re-run of the conflicted task from the joined state, always.
- Same-spec only in v1; wave ≤ 3; transitive dep check, not direct-only.
- Reviewer overlap never reorders receipts: done(N) precedes plan-sync(N) precedes any anchor reading N's downstream updates.

## Acceptance Criteria

- **R1:** phases.md carries the explicit dispatch rule verbatim in place of the judgment prose; fail-closed on every listed condition. Errors: missing Touches: → serial; ambiguity → serial; these ARE the error paths and must be stated in the prose.
- **R2:** Join handling specifies merge-conflict → serial re-run + collision recorded in the receipt. Errors: a conflict must never be auto-resolved or silently dropped.
- **R3:** Reviewer-overlap rule present with both conditions and the plan-sync barrier stated. Errors: overlap with a dependent task is the failure this R prevents.
- **R4:** Plan-review rubric checks Touches: plausibility and flags overlapping pairs. Errors: none beyond prose.
- **R5 (the gate):** a replayed multi-task spec run under wave dispatch reproduces the sequential run's test outcomes (same tests green at completion). Errors: any divergence blocks landing.
- **R6:** Mirrors, CHANGELOG per conventions; docs-site rides the batched release. Errors: parity red blocks merge.

## Boundaries

- No flowctl code, no deterministic checker binary (prose + structure only).
- No cross-spec waves, no wave >3, no predictive/semantic gating of any kind.
- No change to worker.md's wave contract or to plan-sync's own behavior.
- No reviewer-content changes (overlap is scheduling only).

## Strategy Alignment

Active tracks served by this plan:
- **Self-improving through normal work** - measured serialization converted into an explicit dispatch rule.
- **Cross-platform parity** - mirrors regenerated with the canonical change.

## Decision Context

A Python disjointness checker was considered and rejected: the merge-conflict backstop makes prose-grade checking safe (wrong answer costs one serial retry, never correctness), and Gordon explicitly preferred no new deterministic machinery. Wave ≤3 and same-spec-only keep v1's blast radius small; both are stated limits, not architecture, liftable by evidence later. Reviewer overlap folded in here because it shares the identical safety predicate and edit site. The R5 gate runs as a sandbox two-task replay (serial vs wave) rather than a fleet campaign - the equivalence claim is about the dispatch rule's mechanics, which a minimal disjoint pair exercises fully.

## Early proof point

Task fn-176.1 validates the core approach (the fail-closed rule reads as checkable and the R5 sandbox replay reproduces sequential outcomes). If the wave run diverges, stop - do not land.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | Fail-closed dispatch rule in 3a | fn-176.1 | - |
| R2  | Join conflict handling | fn-176.1 | - |
| R3  | Reviewer-overlap rule + barrier | fn-176.1 | - |
| R4  | Rubric Touches: check (both copies) | fn-176.1 | - |
| R5  | Sequential-equivalence sandbox gate | fn-176.1 | - |
| R6  | Mirrors + CHANGELOG | fn-176.1 (mirrors), fn-176.2 (CHANGELOG) | - |
