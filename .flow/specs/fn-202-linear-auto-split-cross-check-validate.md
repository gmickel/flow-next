# Linear auto-split cross-check: validate tracker-side issue cutting against direct capture

## Goal & Context

Field finding from the Systabuild rollout (weekly sync, 7 Aug 2026, Swen Niebann): Swen creates a project in Linear and lets the model cut it into issues itself -- one spec per issue, dependencies included -- and then feeds those issues into flow-next. The open question is whether that tracker-side cut is trustworthy: does the model, cutting from the tracker's project view, arrive at the same decomposition it would produce cutting directly against the code?

The agreed validation is a controlled double-run: take the same source ticket, run it once through the Linear auto-split path and once through direct capture/plan against the repository, and compare the resulting splits (spec count, boundaries, dependency edges). Outcome is either confidence in the tracker-side workflow or a concrete counterexample showing where the tracker view lacks the code context to cut correctly.

This is adjacent to, but distinct from, the existing capture/interview split heuristic (8+ acceptance criteria proposes a split, user decides): that heuristic sizes a single spec; this spec validates whether an upstream tracker-side decomposition agrees with a code-aware one.

## Architecture & Data Models

No product code expected in the first iteration; this is an evaluation protocol. If the comparison surfaces a fixable gap (for example the auto-split lacking repository context that tracker-sync could supply), the fix lands as its own follow-up spec.

Artifacts involved: Linear project + auto-cut issues; tracker-sync bridge (fn-52, fn-64 lineage) for pulling issues into specs; direct capture/plan output on the same source ticket.

## API Contracts

None. Uses existing flowctl and tracker-sync surfaces as-is.

## Edge Cases & Constraints

- The comparison must use a real ticket of nontrivial size (a change that plausibly spans 2+ specs), not a toy. A single-spec ticket proves nothing in either direction.
- Model nondeterminism: one divergent run is weak evidence; agree convergence criteria before running (same spec count and materially same boundaries = pass; cosmetic wording differences ignored).
- The Linear path and the direct path must see the same source text; do not let the Linear issue descriptions accumulate extra context the direct run never saw, or the comparison measures input inequality, not cut quality.

## Acceptance Criteria

- **R1:** A documented double-run exists: the same source ticket decomposed once via Linear auto-split and once via direct capture/plan against the repo, with both outputs preserved.
- **R2:** A written comparison records spec count, boundary differences, and dependency-edge differences, and concludes either "tracker-side cut agrees" or names the concrete divergence.
- **R3:** If a divergence is found, a follow-up recommendation exists (fix in tracker-sync context supply, guidance to run splits code-side, or documentation of the limitation).

## Boundaries

- In scope: the evaluation protocol, one documented double-run, the comparison write-up.
- Out of scope: building new product features; changing the capture/interview split heuristic (already shipped, 8+ criteria); Systabuild-specific consulting artifacts (those live in the vault, not this repo).

## Decision Context

Origin: Systabuild weekly 7 Aug 2026 (Swen Niebann), carried as Todoist 6hF8cCCf3Vg3mgXR, stubbed into the repo 21 Aug 2026 so the backlog owns it instead of a task list. Swen's workflow motivation: letting Linear hold the project shape gives POs a familiar surface while flow-next executes; the double-run is the cheap way to find out whether that surface loses information that matters for cutting. No deadline; natural slot is alongside the next tracker-sync iteration.
