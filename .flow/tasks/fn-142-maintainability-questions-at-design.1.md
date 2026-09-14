---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13]
---
# fn-142-maintainability-questions-at-design.1 Implement Maintainability questions at design time, and an honest claim

## Description
In-repo build of the spec: the plan-review Maintainability criterion and `maintainability:` verdict block (template, flowctl fallback, both pins, parity fixtures, and both RepoPrompt paths), the Decision Context pointer in the plan-review skill, the two questions in the technical refine bank, the byte-identical claim sentence in the README and the docs home, the CHANGELOG entry, and the regenerated codex mirror.

**Scope deferrals (recorded, not silent):** R6 (flow-next.dev verification-spine page) and R8 (flow-next.dev FAQ entry and cross-link) live in another repository and are deferred to the parent agent after release, together with the rest of the R11 downstream chain (flow-next.dev build, AI x SDLC guide, vault Messaging Library and Release Timeline). R13 (the replay study under agent-evals) is deferred by the spec itself: shipping the prose does not wait for it, and no copy claims benefit. R10 is withdrawn by the spec.

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Plan review gains criterion 9 Maintainability (duplication and structure, each a concrete finding or "none identified", advisory unless it names concrete duplication, a back-edge, or the absorbing function) plus the `maintainability:` verdict block; the plan-review skill writes a named finding as one line into the spec's Decision Context; the technical refine bank asks the same two questions once for the direct route; the README and the docs home carry the byte-identical claim sentence; CHANGELOG Unreleased records it. The prompt edit is deliberate: template, flowctl fallback, both hash pins, both parity fixtures, and both RepoPrompt paths (CE summary + Classic rubric) updated together, codex mirror regenerated (idempotent).

Deferred to the parent agent after release (other repositories): R6 (flow-next.dev verification-spine sentence), R8 (FAQ entry + cross-link from the clean-code entry), and the rest of the R11 downstream chain (flow-next.dev build, AI x SDLC guide, vault Messaging Library and Release Timeline). R13 (replay study under agent-evals) deferred by the spec; no copy claims benefit. R10 withdrawn by the spec. Recorded in the task Description as well.

Review: codex three-draw fan-out returned NEEDS_WORK (R6/R8 unrecorded deferral; RepoPrompt path missed the criterion); both fixed in 47c218f6; re-review SHIP. Memory entry bug/integration/plan-review-criteria-edits-must-also-2026-09-14 captures the six-copy sweep rule. Verify gate: full suite green (4991 ran, rc=0), ruff clean; no green receipt minted because the re-review's spec-json bookkeeping left the tree dirty at the fix HEAD.

stage: impl-review - ran (fan-out NEEDS_WORK -> 1 fix round -> SHIP)
stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 701c7b9b795e25c2457280b0433d96bdffc6f123, 47c218f63e92c1417cd5a937ddfefa4afa0f4146
- Tests: baseline: green (python3 scripts/run_tests_parallel.py, 4991 ran, rc=0; no green receipt for HEAD), python3 -m unittest plugins.flow-next.tests.test_prompt_text_pinned plugins.flow-next.tests.test_review_prompt_template_parity, python3 -m unittest plugins.flow-next.tests.test_skill_prose_diet plugins.flow-next.tests.test_r22_invariant plugins.flow-next.tests.test_refine_rename plugins.flow-next.tests.test_chart_docs_inventory plugins.flow-next.tests.test_flowctl_surface plugins.flow-next.tests.test_interview_scope_flag, ./scripts/sync-codex.sh (run twice, idempotent), python3 scripts/run_tests_parallel.py (verify: files=220 ran=4991 failures=0 errors=0, rc=0), uvx ruff@0.16.0 check . (all checks passed), git diff --stat plugins/flow-next/templates .flow/templates (R5: empty), grep for claim verbs prevent/stop/fix + maintainability/decay in shipped copy (R9: no hits)
- PRs: