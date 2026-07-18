---
satisfies: [R1, R2, R3, R4, R6, R10]
---

## Description

Convert the comment-shaped touchpoints and add the joins - the minimal-diff pass.

**Size:** M
**Files:** skills/flow-next-work/phases.md (+ references/tracker-touchpoints.md), skills/flow-next-resolve-pr/workflow.md, skills/flow-next-qa/workflow.md, skills/flow-next-make-pr/create-and-finalize.md, skills/flow-next-capture/workflow.md, codex mirror (regen)

1. Each comment-op gate (work.done 3d.1, completionReview comment-leaf case in 3g/tracker-touchpoints.md, resolvePr, qa) gains ONE conditional sentence: resolved op == comment AND spec linked AND host gate -> background tracker-runner per references/tracker-dispatch.md; else inline as today. Do NOT restate the rules at the gates (R11 makes the reference the sole statement).
2. resolvePr + qa: add the missing `event:` tags to their dispatch lines (R10); their dispatches are awaited before the skill summary (no later sync check audits them).
3. Pre-audit join sentences (one line each, pointing at the reference) before the sync checks: work Phase 5, make-pr section 5.7, capture Phase 6.
4. R2/R3/R6 by construction: no fork path for state-shaped/unlinked/ceremony flows - verify by diff review that every non-comment gate is byte-identical.
5. Mirror regen, idempotent, guards green.

## Acceptance
- [ ] R1: four comment gates conditional-dispatch via the reference
- [ ] R10: event tags present on resolve-pr + qa lines
- [ ] R4: three join sentences in place
- [ ] R2/R3/R6: non-comment paths byte-identical (diff evidence)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
