---
satisfies: [R1]
---
# fn-203-rolling-frontier-scheduling-with-shared.1 Pre-register the three-arm eval: fixture, endpoints, harness design

## Description
Produce the frozen pre-registration for the R1 eval before any prototype draw runs. This is study design only - no product files change.

**Size:** M
**Files:** pre-registration + fixture live in the maintainer's eval workspace (outside this repo); no repo files modified
**Touches:** []

### Approach
- Select or author the fixture spec: >=5 tasks, >=4 admissible task boundaries (dep-independent, disjoint Touches). Minimum valid size - 5 tasks, not more; the fixture exists to fix the prior measurement's minimum-surface confound, not to maximize runtime. If authored, freeze its plan and task files at a pinned SHA so all arms draw from identical input.
- Freeze endpoints and decision rules per R1: primary quality parity (blind checklist + full deterministic suites), secondary work-phase wall-clock and the five incident classes, the >=15% ship gate, zero-uncontained-incidents clause, tiebreaker, INCONCLUSIVE as first-class.
- Freeze the model configuration: conductor and workers on the production default (opus-5 at medium effort), identical across all arms and draws - never the planning session's escalation-tier model. Record the exact model ids and effort in the registration so draws are reproducible.
- Freeze the supervision budget and abort rules, wall-clock-first (tokens are the backstop, not the constraint). Register these defaults unless the fixture argues otherwise: kill any treatment draw exceeding 1.5x its paired baseline draw's actual duration (a rolling arm slower than the barrier has already failed); kill a draw whose current task exceeds ~3x the fixture's median task time beyond the existing review-cap/stall-guard bounds; a nominal high token ceiling per draw purely as a runaway backstop. Killed draws are invalidated, not scored.
- Freeze the batch and futility plan for speed: one batch, all three arms launched same-second on one machine (contention hits all arms equally, so the paired wall comparison stays valid); a batch-1 verdict stands when the margin is decisive (gate cleared with margin plus zero uncontained incidents, or clearly failed) and a single replication batch is owed only on a borderline result. No other outcome-based early stopping exists.
- Freeze the blind-scoring redaction contract: scorer sees only the final integrated diff + suite results; commit history and notes artifacts stripped (arm-2 output is structurally distinctive - the redaction is what keeps scoring blind).
- Freeze harness isolation: each draw in its own isolated checkout with its own runtime state dir (set the state-dir env per draw); paired same-second same-machine launches.
- Freeze all three arm-2 disciplines (staging-by-declaration, branch-local lock, edit-state ledger) as part of the registration.

### Key context
- Draws must not share claim/receipt state: the runtime state store resolves through the git common dir and is shared across sibling worktrees unless the state-dir env is set per draw.
## Acceptance
- [ ] Fixture spec exists, satisfies the >=5-task / >=4-boundary shape at minimum valid size, and is pinned
- [ ] Pre-registration frozen before any draw: endpoints, decision rule, model config (opus-5 at medium), wall-first budgets + kill rules, batch/futility plan, redaction contract, isolation design, arm-2 disciplines
- [ ] No files in this repo modified
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
