---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-326-9110-pre-release-fixes-for-issue-start.1 Issue start: interrupted-capture recovery, cross-ref link resolution, question rounds, Jira site check, always review, no capture status conflict

## Description
Fix fn-325's issue start (merged in #608) for the audit findings in the parent spec: R1 interrupted capture recovery, R2 links on any fetched ref (including JSON-only changes to specs already on the default branch), R3 plain answer then follow-up question posts a new round, R4 Jira URL from another site stops before writes, R5 every work hop of an issue start runs implementation review (Gordon's decision), R6 no backlog-vs-ready status conflict at the capture push. Read the parent spec and the Codex audit reasoning summarised there. Prefer prose fixes in issue-start.md / from-issue.md / auto.md; add flowctl code only where a deterministic fact needs it (R2 cross-ref link lookup, R3 round handling may need wire question support). Update agent_docs/conduct/flow.md and capture.md checklist lines for changed contracts.

Touches: plugins/flow-next/skills/flow-next-flow/references/issue-start.md, plugins/flow-next/skills/flow-next-flow/auto.md, plugins/flow-next/skills/flow-next-capture/references/from-issue.md, plugins/flow-next/skills/flow-next-capture/SKILL.md, plugins/flow-next/skills/flow-next-capture/workflow.md, plugins/flow-next/scripts/flowctl.py, plugins/flow-next/scripts/flowctl-help.txt, plugins/flow-next/scripts/flowctl_tracker/wire/__init__.py, plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json, plugins/flow-next/codex/, agent_docs/conduct/flow.md, agent_docs/conduct/capture.md, plugins/flow-next/tests/test_flow_auto.py, plugins/flow-next/tests/test_capture_chart_handoff.py

## Acceptance
R1-R6 of the parent spec hold, each with the test or prose-contract pin the spec names. Fake-transport tests for any flowctl change; live recording on Linear FLOW for R3 and R6 (issues titled "[fn-326 live check] ...", canceled afterwards).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
