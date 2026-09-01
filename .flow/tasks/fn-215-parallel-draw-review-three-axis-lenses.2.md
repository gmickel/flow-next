---
satisfies: [R1, R3, R5, R7, R9, R10, R11, R13]
---
# fn-215-parallel-draw-review-three-axis-lenses.2 impl-review skill prose: fan-out coordination, merge step, steering

## Description
skills/flow-next-impl-review coordination prose, now OWNING the host fan-out contract end to end (R9–R13 apply to the host path through this task). **Touches:** plugins/flow-next/skills/flow-next-impl-review/**, agent_docs/conduct/impl-review.md, plugins/flow-next/codex/**

workflow-codex.md: the fan-out is TWO blocking foreground flowctl calls — the phase-one dispatch (three concurrent draws, per-draw sidecars back), then the coordinator's merge, then the phase-two finalize (per task 1's interface); each call keeps the foreground rule — same-defect dedupe (judgment), evidence-bar drops with a stated count, ranked output with Act-On capped at 5 for non-blocking tiers plus the published remainder with axis provenance IN PROSE (never on finding items); every surviving introduced blocking finding is fixed regardless of count. workflow-host.md host fan-out: ONE `review-rounds increment` before dispatch, then three read-only reviewer subagents in ONE message (mirror the quality-auditor dispatch shape at flow-next-work/phases.md:568-588; Decision Context records why these merge while the auditor's stay verbatim), then ONE `record`/`attach` after the merge — never three cap slots per merged round (R13). Host round 2+: one FRESH read-only subagent, session_id null (host sessions are never resumed — fn-123 contract), merged prior-finding container injected in full; codex round 2+ resumes the primary session with the full merged container injected (lean resume disabled for the first post-fan-out round) per R11. Worst-wins verdict synthesis, wedge escalation (R9), partial-fail-open (R10), and the draws[] receipt shape (R12) stated for the host path with host contract tests. fix-loop.md re-entry updated for both backends. Steering prose with worked phrasings (R5): 'use 1 reviewer instead of 3' collapses to a single draw; 'use three different model families for the review fan-out' → the coordinator passes three explicit per-draw backend/model specs to the fan-out interface (prose parsed HERE, never in flowctl); ambiguous phrasing defaults to the standard three same-backend draws. rp/copilot/cursor workflow files gain one line each stating single dispatch stands. agent_docs/conduct/impl-review.md gains fan-out/merge/one-reservation checklist rows. Canonical files use Claude-native tool names; sync-codex twice; verify actionable-invocation transforms (sync-codex.sh:395,495-502) still rewrite the new prose; portable-host fallback clauses for the host dispatch.
## Acceptance
R1 (coordination prose), R3, R5, R7, and R9-R13 for the host path satisfied; judge against the parent spec's criteria directly. Skill-contract/prose suites green; mirror diff committed and idempotent.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
