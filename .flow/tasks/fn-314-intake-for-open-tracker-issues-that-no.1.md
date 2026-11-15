---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-314-intake-for-open-tracker-issues-that-no.1 Implement Intake for open tracker issues that no spec covers

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
`wire list-open` gains `--any-lane` (every open issue, any lane, on all four providers with
readyState unset) and `--unlinked` (drops issues a local spec links, from local sync state with no
tracker call); either flag returns compact rows `{id, identifier, title, url, labels, excerpt}`.
Default output is unchanged in shape. Backlog mode reads `list-open --unlinked`. Flow gains one
route row (route-matrix-more.md) and `references/open-issue-intake.md`: one table, one confirming
question, then capture / fold / add-dep / leave through existing stages. R1 satisfied by fn-324.

Live recordings fixed two real defects on the way: Linear's duplicate state type is excluded from
`--any-lane`, and Jira Cloud list-open uses `/rest/api/<v>/search/jql` (Cloud answers 410 on
`GET /rest/api/2/search`, which every flowctl-resolved Cloud project hit); Data Center keeps the
classic search. Review added Linear label selection.

Live recordings (2026-11-15): GitHub gmickel/test #2-#7, GitLab localhost flownext/flownext #2-#7,
Linear FLOW-113..118 (canceled and duplicate excluded), Jira KAN-8..16 (Done excluded, browse URL
in compact rows). All test issues closed, canceled or Done.

stage: impl-review - ran codex three-lens NEEDS_WORK (3 findings: repeated capture question, Linear labels unselected, route tests pinned wording) then re-review SHIP (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 3e20de9e1470c95ee57356151a1788557c0212cf, 1c3aac35598c90f3049130442ea5d4b16c259b0c, aaef99f99bde36496f91b7050bb6adc3a89b1b97, 2ed20a08d0b88a362c978a7658cdeab8fc344e2e, 163d496eafb8403e7a9df1e455539c17036ecf0f, ed13780fea6490d61acbbaedf9cf1d91a6e3cc7b
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_tracker_list_open_intake.py' (+ test_tracker_wire, test_tracker_conformance, test_flow_routing, test_tracker_sync_backlog_mode); live list-open on GitHub/GitLab/Linear/Jira
- PRs: