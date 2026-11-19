---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-336-reviews-judge-the-branch-as-a-whole-org.1 Implement Reviews judge the branch as a whole; org criteria by reference

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Measured round (R3) run before shipping either rubric line; neither met its pre-registered bars, so both were removed and the spec records each result in place of R1 and R2.

- R1 (completion-review whole-branch lens): recall 2.0 vs 1.0 of 3 seeds per draw set, no false findings, one-task guard clean, wall 1.01x, but median tokens 1.30x against a 1.20 bar (3 draw sets, 18 reviews per arm). Template and byte-identical fallback back to main's text.
- R2 (outside-diff repeat line in the smell baseline): baseline already caught both seeded repeats in every run (2.0 vs 2.0), no false findings, wall 1.085x, tokens 1.03x. No recall gain; smell baseline unchanged.
- R4: teams guide gains "Rules shared across an organisation" (criteria.md as a link to a shared criteria file; a criterion naming a shared guidelines file; what each records; broken link fails closed, confirmed live; when standing criteria are judged; where per-criterion verdicts are recorded).
- R5: live completion review per backend with a criterion naming a rules file outside the repo: codex, cursor (grok-4.7-medium) and host (Claude Code read-only subagent) read it; claude cannot (Read denied, G1 not evaluated, NEEDS_HUMAN); copilot unchecked (monthly quota). Named in the guide.
- Conduct checklists unchanged: neither review contract changed in the end.

stage: impl-review - ran (codex gpt-6.2-sol medium: round 1 NEEDS_WORK on the guide's receipt claim, fixed; round 2 SHIP) (model: gpt-6.2-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 6a43b47829f016907d35f543d8f7867f083b5eb8, 40c742b1932b163ff2507a97b3d4be0acfbbfa7c, 6011c4999323dd90753327eb68edb3c1a291a923, 1c60c7c3e48787bb00d5233e0fa91d654a959659, dd890ab5f0be54616b17d6126b509c0cef49b3f1, 38dfb86e48835ed8c1cc9a327f237fea1a22d6f9, 12b88b7c86ca45b736ec9db3247cf3cec92f0014
- Tests: python3 scripts/run_tests_parallel.py (4510 ok); uvx ruff@0.16.0 check .; ./scripts/sync-codex.sh --check; test_review_prompt_template_parity
- PRs: