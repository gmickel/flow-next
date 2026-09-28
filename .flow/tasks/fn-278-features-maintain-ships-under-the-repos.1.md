---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-278-features-maintain-ships-under-the-repos.1 Implement maintain ship under repo naming rules and host

## Description
TBD

## Acceptance
Every R-ID in the parent spec's Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Maintain reads the repo's branch/commit naming rules at entry (asks for a ticket key before Phase 1, BLOCKED at entry when nobody can answer), names branch and commit by them (run id only in the default name), opens the PR via ${FLOW_PR_CREATE_CMD:-gh pr create} and stops CHANGED after the push when no create command reaches the host, honours commit-only / leave-uncommitted requests, and keeps proven edits on a commit/push/create failure (restore still applies before/during proofs and on a moved base). SKILL verdict table, architecture doc, codex mirror, CHANGELOG (credits @CWayman, #495), 3 contract tests (entry-gate placement, executed create fence with a stub, BLOCKED keep token). Codex review: round 1 NEEDS_WORK (run id forced into repo-dictated names), fixed, round 2 SHIP.

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 73eb0be19146eb70f36a30285ec1f1f0900a6e97, ad73df30659ee10a2c63b0cc4d304f134d63846e
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check .
- PRs: