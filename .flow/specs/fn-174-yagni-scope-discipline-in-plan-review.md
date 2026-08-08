# Overview

Planning agents systematically overbuild: in the flow-efficiency replay campaign, two independent opus runs of the same real request (gno fn-107) each produced 6 tasks / 21–23KB specs / a 500–900-line trust-consent subsystem, where the human-steered shipped version needed 4 tasks / 6.7KB and eliminated the trust problem structurally. A third run with scope-minimality prose produced 4 tasks, explicitly declined the trust machinery in Boundaries, and delivered −43% output tokens / −57% cost with reviewed quality ABOVE the unmodified arm. This spec lands that prose.

**Evidence standing: validated in the flow-efficiency replay campaign (`~/work/agent-scripts/flow-efficiency/results/06-IMPLEMENTATION-LIST.md` §1, `05-REPLAY-CAMPAIGN.md`). No further evaluation is required before landing.** Tested prose exists verbatim in worktree commit `5a54d5f0` (`replay/wt/flow-next-yagni`); this spec lands it plus one amendment its quality review demanded.

## Goal & Context

Make scope minimality a first-class, checkable planning discipline: every task traces to an R-ID, every R-ID traces to the request, unrequested capabilities go to Boundaries as one-line exclusions, and risk-elimination is preferred over risk-management machinery. Overengineering becomes a plan-review FINDING, not a taste note.

## Architecture & Data Models

Prose-only; no flowctl changes. Four edit sites (tested wording in `5a54d5f0`):

1. `skills/flow-next-plan/steps.md` Step 2: binding scope-minimality block — trace-to-request rule, smallest architecture satisfying the ACs, structural-elimination-over-risk-machinery principle, one-line rejections in Decision Context, extras → Boundaries.
2. `skills/flow-next-plan-review/references/plan-review-prompt.md` criterion 6: overengineering is a finding, with three concrete patterns (untraceable surface; risk-machinery where structural elimination is available; N-way generality for a one-case request).
3. `templates/spec.md`: SCOPE DISCIPLINE comment block.
4. `agents/worker.md`: build to the AC, not past it; follow-ups noted in the done summary, never built.

## Edge Cases & Constraints

The rigor exemption is the load-bearing safety clause and MUST appear at all four sites, extended beyond the tested wording per the quality review's one real finding: minimality never trims (a) error/negative-case enumeration per AC, (b) **filesystem-identity, permission, and concurrency guards** — realpath/symlink containment, lock-guarded writes, forced excludes of runtime state. The yagni arm's only defect was eliminating a containment guard along with the features ("an eliminated guard, not an eliminated feature").

## Acceptance Criteria

- **R1:** All four edit sites carry the scope-minimality prose functionally equivalent to `5a54d5f0`. Errors: no error surface beyond prose consistency.
- **R2:** Every site's exemption clause names BOTH error-case enumeration AND filesystem-identity/permission/concurrency guards as rigor, not scope. Errors: a site missing either exemption fails review.
- **R3:** Plan-review rubric lists the three overengineering patterns as findings. Errors: none beyond R1.
- **R4:** Codex/cursor mirrors regenerated; docs-site updated per downstream conventions; CHANGELOG entry cites the replay-campaign evidence. Errors: mirror-parity check red blocks merge.

## Boundaries

- No new evals or benchmark runs (evidence standing above).
- No enforcement code, no lint, no flowctl verbs — prose only.
- No length/byte budgets (measured ignored 3x; rejected lever).
- No change to error-enumeration discipline itself (fn-165 stands as-is).

## Decision Context

Chosen over per-project config because the failure is universal in unattended planning and the discipline is self-exempting where a request genuinely needs the bigger design (the rules bind derivation, not outcomes — a traced task satisfying a real R-ID is always legal). Structural-elimination principle sourced from the campaign's sharpest reviewer finding: the shipped fn-107 made the profile format inert instead of building consent machinery; both unguided replay arms built the machinery. Rejected: shipping the tested prose without the guard-exemption amendment — the yagni arm's symlink-containment miss shows minimality pressure needs the guard clause before fleet exposure.
