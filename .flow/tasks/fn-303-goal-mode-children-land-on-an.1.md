---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-303-goal-mode-children-land-on-an.1 Implement Goal mode: children land on an integration branch

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Goal runs land children on an integration branch, goal/<goal branch_name>, by default: created once from the default branch, children branch from it (work --base) and target it (make-pr --base), the default branch is merged in before each measurement, and the goal reaches the default branch through one final pull request opened only after a whole-diff implementation review (draft when the review leaves an open item). A sentence in the goal spec or the starting message opts out; the first run logs the choice. A child PR into the integration branch with no checks, while PRs into the default branch have some, stops NEEDS_HUMAN. Work gains --base=<branch> (origin/<branch>); an unfetchable branch or a chained spec stops BLOCKED before a branch exists. Docs: CHANGELOG, GLOSSARY, skills.md; flow-next.dev goal-mode page in cfb39ef (held).

Decision: the integration branch is goal/<branch_name> rather than branch_name itself, because land selects the spec whose branch_name matches the PR head and would stop on the still-open goal spec; the goal/ prefix also gives one CI pattern (goal/**).

stage: impl-review - ran [codex, 3 draws NEEDS_WORK -> fix pass -> re-review SHIP] (model: gpt-6-astra)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 97b2402f8c5ea1bd4b1810ca27403d24959c1422, 797286fdb99e8c91a95025efa6c2ea345ba87829
- Tests: python3 scripts/run_tests_parallel.py (4050 ran, 0 failures); uvx ruff@0.16.0 check . (clean); test_chain_consumer_fixtures.py (35 OK)
- PRs: