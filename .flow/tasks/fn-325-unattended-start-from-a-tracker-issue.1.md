---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10]
---
# fn-325-unattended-start-from-a-tracker-issue.1 Implement Unattended start from a tracker issue: flow --from-issue

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Added `flow --auto --from-issue <key|url>`: a gated reference (`flow-next-flow/references/issue-start.md`) that checks consent through `tracker wire list-open` (the issue must be in tracker.readyState), resolves a linked spec in the checkout, on the fetched default branch or on branch-only refs, routes the issue on its content with the route matrix, applies the default bar (stricter AGENTS.md wins), captures with `flow-next-capture from:issue --no-plan`, marks the spec ready, commits it as `chore(flow): capture <spec> from <issue>` on its branch and pushes, design-reviews it against the issue before work, or refuses: question on the issue (`tracker wire question`), `tracker wire unready`, `ASKED`. Re-entry reads the comments after the earlier question. auto.md parses the flag and refuses an empty value or a second starting point. Capture gains `from:issue` (`references/from-issue.md`): the issue is the only source, quoted in Goal & Context, no inferred criteria, never splits. Docs, conduct clauses and Codex mirror updated.

Live: Linear FLOW-110 and Jira KAN-12 recorded list-open/read/comment-list/question/unready (Jira rows have no url; unready refuses backlog_slot there). End-to-end headless `flow --auto --from-issue --until=merge` on gmickel/flow-next-e2e-scratch: FLOW-111 clear (merged #1), FLOW-112 unclear (ASKED, Backlog) then answered and re-run (merged #2; exposed the skipped design review, fixed), FLOW-119 re-entry (plan-review ran, merged #3), FLOW-120 on the final code (plan-review, issue quoted, capture commit, merged #4).

stage: impl-review - ran codex three-lens NEEDS_WORK (7 findings fixed) then re-review SHIP (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: c700657ce02ecaad095bd17aa1edf123f01bc275, 4192524cd725a47345170065ccd1b50ba8b57f03, af25fa47dd9cb34042273908ccb4a585753fc9e0, 7ffd0fe6251c4382ed143981e3d3ad24061eb151
- Tests: python3 scripts/run_tests_parallel.py (4295, 0 failures); uvx ruff@0.16.0 check .
- PRs: