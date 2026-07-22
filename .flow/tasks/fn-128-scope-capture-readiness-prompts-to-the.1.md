---
satisfies: [R1, R2, R3]
---
# fn-128-scope-capture-readiness-prompts-to-the.1 Fix capture readiness prompt and release 3.3.3

## Description
Make Capture's readiness follow-up target-aware for rewrites, clarify autonomous-queue semantics, add regression coverage, regenerate the Codex mirror, update public docs, and publish patch release 3.3.3.

## Acceptance
- [ ] New capture + adopted local readiness retains the optional mark-ready question.
- [ ] Ready rewrite target gets a restore-readiness question; draft rewrite target gets no question regardless of unrelated ready specs.
- [ ] Tracker-authoritative suppression, autofix no-write, rewrite reset, and existing option tokens remain unchanged.
- [ ] Canonical/mirror contracts, full repository gate, and exact docs-site build pass.
- [ ] Version 3.3.3 is committed, pushed, tagged, and verified publicly.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
