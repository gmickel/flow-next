---
satisfies: [R1, R2, R3, R4]
---
# fn-316-resolve-pr-over-gitlab-merge-request.1 Implement resolve-pr over GitLab merge request discussions

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
resolve-pr works on a GitLab origin. The Preamble reads the forge from `flowctl pilot snapshot`'s `forge` field (fn-73's one rule; unreadable stays GitHub) and loads `forge-gitlab.md`, which swaps the gh commands for glab ones while the phases, triage, dispatch and verdicts stay shared. New scripts: `get-mr-discussions` (every page via `glab api --paginate`, same JSON keys as `get-pr-comments`, system notes dropped, `isOutdated` from the position's head), `reply-to-mr-discussion`, `resolve-mr-discussion`. A top-level note is answered with a new note, because replying inside it turns it into an unresolved thread (measured). A merge request URL must name the checkout's project. Resolvers read `git diff origin/<target>...HEAD` in place of `gh pr diff`.

Fixtures are live recordings from MR !13 of the self-managed test project, reviewed by a throwaway second user; runner tokens redacted. R2 amended to GitHub's resolve rule (spec Decision Context).

stage: impl-review - ran [codex 3-lens panel NEEDS_WORK -> fix pass b3d71d4ee -> re-review SHIP] (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 74c5c928d85e87dd3be2f686de8397c556026dce, b3d71d4ee05834bb037b18443b8491ca8ee91c8b
- Tests: python3 scripts/run_tests_parallel.py (4175 passed); python3 -m unittest test_resolve_pr_gitlab test_make_pr_gitlab (OK after fixes)
- PRs: