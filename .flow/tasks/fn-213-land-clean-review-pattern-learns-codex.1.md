---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-213-land-clean-review-pattern-learns-codex.1 Implement land clean-review pattern for Codex summary-table format

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Extended the land.cleanReviewCommentPattern built-in default with a structured alternative for Codex's edited-in-place summary-table clean verdict (literal bold **Code Review** followed by **Completed**), updating every carrier in lockstep (flowctl seeded default, workflow.md null-fallback ERE + section 2.6 two-shapes commentary, SKILL.md gate bullet, docs/flowctl.md config row, seeded .flow/config.json, test pins + new behavioral anchors, codex mirror, CHANGELOG Unreleased). Baseline: green. Verified the old pattern misses the realistic summary-row body and the new one matches it while rejecting unstructured "code review completed" prose.

stage: impl-review - ran [codex, 1 round, SHIP first pass]
## Evidence
- Commits: 15edfa60337f59e5e3e75f80b3ea50c663d36201
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_land_config -q, uvx ruff@0.16.0 check plugins/flow-next/scripts/flowctl.py, ./scripts/sync-codex.sh (x2, idempotent), python3 scripts/gen_tracker_manifest.py
- PRs:
stage: plan-sync - skipped(config: planSync.enabled != true)
