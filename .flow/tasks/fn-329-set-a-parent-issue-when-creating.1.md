---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12]
---
# fn-329-set-a-parent-issue-when-creating.1 Implement Set a parent issue when creating tracker issues

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
A spec's tracker block takes an optional `parent`, read only when flow-next creates the spec's issue: the spec-keyed create, the first push's create, create-first, and the Linear MCP create payload. Jira Cloud sends `fields.parent = {key}`, Linear `parentId`, GitLab `epic_id` (an `&N` / `group&N` reference resolved with one read; id 0 refused). GitHub and Jira Data Center (authScheme bearer-pat) refuse with a `capability` error before any request. Recorded through `spec create --tracker-parent`, `tracker create --parent`, `tracker create-first --parent`; results report `parent`. `sync create-first-key --parent` gives each parent its own retry key (unchanged without one); create-first refuses a recorded issue under another parent (`parent_mismatch`); `create-first-put` keeps the recorded parent. No later sync op reads or sends it. Docs: tracker-sync reference, flowctl reference, teams guide, capture and tracker-sync skill references, changelog. Tests: plugins/flow-next/tests/test_tracker_parent.py. Live: Jira Cloud, Linear, GitLab checked.

stage: impl-review - ran [round 1 NEEDS_WORK (3 lenses) .. round 3 SHIP] (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 5a31b5d3a0f07e1ba55987d31026295a53d2d8c4, 8a20874b5e11d36003f7b58c8051dc2884faa399, 34757df48f1437ff110c6620b4178a3acc75b47e, 892f5bb200a724bef7e753d82e00e158dcf5ca4c, 9e47ea12e1ba73d4b4d2cf39fe55967721ccd0c1
- Tests: python3 -m unittest test_tracker_parent test_tracker_lifecycle test_create_first_recovery test_create_first_sequence (+ all test_tracker_* earlier)
- PRs: