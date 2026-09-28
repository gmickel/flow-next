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
The hill-climb reference is rewritten after pstack's playbook (139 lines / 2127 words down to 33 lines / 1191 words). The labelled pre-registration form, the missing-field stop, the required replicate and the label-parity fixture test are gone. The agent now sets up the experiment and records it as the ledger header before the first attempt, and only a missing target stops the run. The keep/revert rule, one row per attempt, one commit per kept attempt, the `deferred` path for an unmet target, the bridged-child hand-off and the `Hill climb:` done-summary record are unchanged, so pr-cognitive-aid.md needed no edit. Simplifications that hold the number may be kept, and independent hypotheses may run in parallel worktrees. Dependents updated: the worker trigger lines, the route-matrix row, pipeline-variations, the fixture SPEC and ledger header, CHANGELOG Unreleased and the codex mirror. The route matrix's "needs" column was left as it was because flowctl's judge pins it verbatim.

flow-next.dev: worktree /home/gordon/work/flow-next.dev-fn-273, branch fn-273-hill-climb-the-agent-sets-up-the, local commit c3efac1 (not pushed). It updates choosing-your-route.mdx, whose worked example now follows the recorded fixture run, and skills/work.mdx. make-pr.mdx was already accurate, and the 6.4.0 changelog entry is left as published. Site build and link check pass.

Tier: session - explicit override: implementer opus 5.5 (actual: claude-opus-5-5)

stage: impl-review - ran [codex gpt-6-astra high fan-out, 3 draws SHIP, 0 findings]

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: c8c45ad38953f4c4e6842ff6a9d8a8789b8bfc6c
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check, flow-next.dev: pnpm build && node scripts/check-links.mjs
- PRs: