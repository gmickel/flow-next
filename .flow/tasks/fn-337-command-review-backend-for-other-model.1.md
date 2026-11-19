---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-337-command-review-backend-for-other-model.1 Implement Command review backend for other model families

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Added the `command` review backend: `command:<label>` selects an argv in `review.commands`, run without a shell over the review execution contract (request on stdin, response on stdout). Accepted in config, `FLOW_REVIEW_BACKEND`, `--review`, per-spec and per-task pins and fan-out draws; impl, plan and completion reviews plus validate/deep-pass run through it. Receipts record `mode: command`, `label` and the reported model (`not reported` otherwise). Bad selection fails before a round is reserved; transport failures refund. Prior findings are always injected; a reported failed resume re-runs fresh once; sessions stay with their label. Wrapper output is bounded while read. Schema, setup, the three review skills, docs (with a working opencode wrapper) and the Codex mirror describe it. R7 verified live: opencode on xai/grok-4.7 reached SHIP with a correct receipt.

stage: impl-review - ran [round 1 three-draw fan-out NEEDS_WORK (7 findings) .. round 4 SHIP] (model: gpt-6.2-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 015a0760e4ac7fe4d9ece64f99a9ff73b0a8fdd2, ef62d273cc6683d071995363d93792a7cda664a7, 9344de4c9bff8d6af1f9ddc3fdd1502fcdeb928c, 8fcbd6299c379d55f75a7d52f35fedc8ac57270d, 63ff6264bda004e608d0caecb3f69c6cc45dc6bb
- Tests: python3 scripts/run_tests_parallel.py (4522 ran, 0 failures); uvx ruff@0.16.0 check .
- PRs: