---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-273-hill-climb-the-agent-sets-up-the.1 Implement Hill climb: the agent sets up the experiment

## Description
Rewrite the hill-climb loop reference (`plugins/flow-next/skills/flow-next-work/references/hill-climb.md`) so the agent sets up the experiment itself, in the spirit and near the size of pstack's 21-line hillclimb playbook: no labelled `## Hill-climb pre-registration` form, the setup recorded as the ledger header before the first attempt, the only missing-information stop being a spec with no target. Keep flow-next's specifics: ledger rows, one commit per kept attempt, `deferred` for an unmet target, the bridged-child hand-off, and the done-summary `Hill climb:` record that make-pr maps to proof cells. Sweep the dependents (worker trigger lines, fixture test label-parity check, fixture SPEC/ledger wording, pipeline-variations, route matrix, CHANGELOG Unreleased, codex mirror, flow-next.dev current-behaviour pages).

Review focus: overengineering, slop and YAGNI. This spec is mostly deletion ("not too much machinery"): flag any new spec section, template entry, config key, flowctl code, capture/refine step, or prose that re-adds form-like required fields, extra statistics ceremony, or rules the agent could decide itself. Also flag lost discipline the spec keeps (keep/revert rule, one row per attempt, deferred unmet target, never relaxing the target) and any contract drift between the `Hill climb:` record and pr-cognitive-aid.md.
## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
