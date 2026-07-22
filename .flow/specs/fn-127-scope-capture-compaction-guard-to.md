# fn-127-scope-capture-compaction-guard-to Scope capture compaction guard to relevant evidence

## Overview
`/flow-next:capture` currently refuses whenever any historical compaction marker or system-summary block is visible, even when the material being captured is fully present after that compaction. Scope the safety guard to relevant missing evidence and ship the correction as flow-next 3.3.2.

## Scope
- Capture compaction-detection prose and its Codex mirror.
- Focused prose-contract regression coverage.
- Repository and public docs-site release metadata/changelogs for 3.3.2.

## Approach
Treat compaction markers as warning signals, not automatic proof of an incomplete capture source. Proceed when the relevant user intent is fully visible; refuse only when relevant requirements are summary-only, truncated, or depend on unresolved gaps. Preserve `--from-compacted-ok` as the explicit override for genuinely incomplete evidence. Regenerate mirrors, run focused and full gates, then publish the patch release without a review pass.

## Quick commands
<!-- Required: at least one smoke command for the repo -->
- `python3 -m unittest plugins.flow-next.tests.test_capture_compaction_contract -v`
- `./scripts/sync-codex.sh && ./scripts/sync-codex.sh`

## Acceptance
- [ ] **R1:** A historical system-summary block or compaction marker alone no longer blocks capture when the requested material remains fully visible.
- [ ] **R2:** Capture still refuses without `--from-compacted-ok` when relevant requirements are missing, truncated, summary-only, or depend on unresolved gaps; autofix remains fail-closed for those cases.
- [ ] **R3:** Canonical skill prose, generated Codex mirror, focused regression test, changelogs, and release metadata ship together as flow-next 3.3.2.

## References
- `plugins/flow-next/skills/flow-next-capture/workflow.md` Phase 0.4
- Originating requirement: fn-36 R6
