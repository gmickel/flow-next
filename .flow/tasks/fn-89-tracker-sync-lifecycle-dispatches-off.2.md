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
Converted the four comment-shaped tracker touchpoint gates (work.done, completionReview, resolvePr, qa) to conditional background tracker-runner dispatch via one sentence each pointing at references/tracker-dispatch.md (fire-and-forget where a later sync check audits; awaited before the skill summary for resolvePr/qa), added the missing event: resolvePr / event: qa tags (R10), and added the three join-before-audit sentences before the sync-check sites in work Phase 5, make-pr 5.7, and capture Phase 6 (R4). Non-comment/state-shaped/unlinked/ceremony paths are byte-identical (R2/R3/R6); Codex mirror regenerated idempotently with guards green. Implemented via codex delegation (gpt-5.6-terra, medium); codex impl-review verdict SHIP (first pass, all R-IDs met).
## Evidence
- Commits: e95bd4c30dc479066d758e96ff76443bb791f691
- Tests: baseline: green (python3 -m unittest discover -s plugins/flow-next/tests: Ran 1788 tests, OK, skipped=2, pre-edit), bash scripts/sync-codex.sh (x3 total: twice in delegation with guards green + identical mirror hashes, once post-commit: exit 0, zero mirror diff = idempotent), grep gates: event: resolvePr + event: qa present; tracker-dispatch.md linked at 4 comment gates; join-before-audit x1 in work phases.md, make-pr create-and-finalize.md, capture workflow.md, git diff evidence: non-comment gates (work.firstClaim, capture 5.7, make-pr 5.6) byte-identical (no hunks touch them)
- PRs: