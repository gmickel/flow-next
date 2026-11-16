---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11]
---
# fn-330-start-from-an-upstream-idea-jira.1 Implement Start from an upstream idea (Jira Product Discovery first)

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Idea intake from Jira Product Discovery. `tracker.perTracker.ideaProjectKeys` turns it on; the Jira wire read of an idea names the new reference `plugins/flow-next/references/idea-intake.md` (no extra request), and `flowctl tracker idea read|parent|link` (new lazy module `flowctl_tracker/idea.py`) read the idea with comments and delivery links, reuse or create one parent at the level above the configured issue type and write the discovery delivery link (type found by listing link types; parent inward). Ideas are read-only: linking a spec to an idea is refused and any Jira write whose parent read lands on an idea is refused. Unconfigured, requests and reads are byte-identical; ready/next import nothing new. Docs, schema, changelog and Codex mirror updated. Live-checked on a Jira Cloud site (read, reuse, create+link, repeat, children under the parent, dependency edge, refusals).

stage: impl-review - ran [round 1 NEEDS_WORK (3 draws, 6 kept findings, all fixed) .. round 2 SHIP] (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 800a8945af5b69ffe6f47ff65b2a148750f79c84, 673e72490e311c91da84a3363c7e7dc14a89dbca, 30df472a6486f1a645f8790e75ee663f73730886
- Tests: python3 scripts/run_tests_parallel.py --pattern 'test_tracker_*.py'
- PRs: