# fn-128-scope-capture-readiness-prompts-to-the Scope capture readiness prompts to the rewrite target

## Overview
`/flow-next:capture --rewrite` currently offers to mark any rewritten draft ready whenever some unrelated spec makes readiness "adopted" in the repository. Make rewrite readiness consent depend on the target's own pre-write state, and explain readiness as Pilot/autonomous eligibility rather than a vague second approval.

## Scope
- Capture skill readiness-consent prose and generated Codex mirror.
- Focused prose-contract regression coverage.
- Capture public docs plus repository/docs-site release notes for 3.3.3.

## Approach
At the existing post-approval readiness probe, read the rewrite target's current `ready` value before any write. New captures retain the repo-adoption gate. Rewrites offer the consent only when that target itself is currently ready; an unrelated ready spec cannot trigger it. Preserve the existing `mark-ready` / `keep-draft` tokens, tracker-authoritative suppression, rewrite reset, autofix behavior, and all deterministic readiness plumbing.

## Quick commands
<!-- Required: at least one smoke command for the repo -->
- `python3 -m unittest plugins.flow-next.tests.test_capture_readiness_contract -v`
- `./scripts/sync-codex.sh && ./scripts/sync-codex.sh`

## Acceptance
- [ ] **R1:** A draft rewrite does not show a readiness question merely because another spec is ready.
- [ ] **R2:** A ready rewrite target still gets explicit consent to restore readiness after the rewrite; new captures retain the adopted-repo offer; tracker-authoritative and autofix paths remain unchanged.
- [ ] **R3:** User-facing copy names Pilot/autonomous eligibility, canonical and Codex prose stay aligned, focused/full gates pass, and flow-next 3.3.3 ships with public docs.

## References
- `plugins/flow-next/skills/flow-next-capture/workflow.md` §§4.2, 5.3, 5.9
- Originating readiness contract: fn-58
