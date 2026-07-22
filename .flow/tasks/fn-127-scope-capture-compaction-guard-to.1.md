---
satisfies: [R1, R2, R3]
---
# fn-127-scope-capture-compaction-guard-to.1 Fix capture compaction relevance guard and release 3.3.2

## Description
Replace capture's any-signal hard refusal with a relevance-based evidence check, pin the behavior in a focused test, regenerate the Codex mirror, and publish patch release 3.3.2 including the public docs-site release entry.

## Acceptance
- [ ] Historical compaction alone does not block a fully visible capture source.
- [ ] Relevant missing/truncated/summary-only evidence still refuses without `--from-compacted-ok`; autofix remains fail-closed.
- [ ] Canonical and Codex mirror prose stay aligned and focused regression coverage passes.
- [ ] Full repository gate and docs-site build pass.
- [ ] Version 3.3.2 is committed, pushed, tagged, and verified on GitHub.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
