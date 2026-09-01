---
satisfies: [R1, R3, R5, R7]
---
# fn-215-parallel-draw-review-three-axis-lenses.2 impl-review skill prose: fan-out coordination, merge step, steering

## Description
skills/flow-next-impl-review: workflow-codex.md documents the fan-out dispatch (still ONE blocking foreground flowctl call — flowctl owns the concurrency) and the coordinator's merge step after it: same-defect dedupe (judgment), evidence-bar drops with a stated count, ranked output with Act-On tier capped at 5 plus a published remainder with axis provenance labels (considered-and-deferred distinguishable from never-seen). workflow-host.md gains the host-native fan-out: three read-only reviewer subagents dispatched in ONE message (mirror the quality-auditor dispatch shape at flow-next-work/phases.md:568-588, but with the merge consumption contract — the Decision Context records why these merge while the auditor's reports stay verbatim). fix-loop.md re-entry: round 2+ resumes the single primary session per R11. Steering prose with worked phrasings (R5): 'use 1 reviewer instead of 3' collapses to a single draw; 'use three different model families for the review fan-out' routes draws cross-family via the existing routing precedence; ambiguous phrasing defaults to the standard three. rp/copilot/cursor workflow files gain one line each stating single dispatch stands there. agent_docs/conduct/impl-review.md gains the fan-out/merge checklist rows. Canonical files use Claude-native tool names; sync-codex twice and verify the actionable-invocation transforms (sync-codex.sh:395,495-502) still rewrite the new prose; portable-host fallback clauses for the host dispatch.

## Acceptance
R1 (coordination prose), R3, R5, R7 satisfied; judge against the parent spec's criteria directly. Skill-contract/prose suites green; mirror diff committed and idempotent.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
