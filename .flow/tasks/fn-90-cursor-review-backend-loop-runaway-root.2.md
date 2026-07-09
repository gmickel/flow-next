# fn-90-cursor-review-backend-loop-runaway-root.2 Productionize: guards, receipts, evals, docs, changelog, mirror, release staging

## Description
TBD

## Acceptance
Covers R5 (full), R6, R8, R9. Productionization on top of task 1's validated fixes.

- [ ] Spec-scoped receipt defaults (all review commands); explicit REVIEW_RECEIPT_PATH still wins; receipt back-compat (no findings field => round 1) tested.
- [ ] Counter semantics hardened: impl-review per-task counter parity; Ralph/autonomous surfaces the cap refusal as escalate/NEEDS_HUMAN, never retryable; exit code distinct from transport failures.
- [ ] 031a0058 guard parity in plan-review SKILL.md + workflow.md (MAJOR_RETHINK carve-out + caller-reset warning) — R6.
- [ ] Eval regression in the fn-54 harness: poisoned-stream parse fixture + convergence guard — R8.
- [ ] Full gate green: unittest + bash smoke_test.sh (run the bash smoke, not just unittest).
- [ ] Docs: orchestration.md (cursor AGENTS.md/persona injection note + persona override), flowctl.md (cap + receipt semantics — note round-counting counts every dispatch ATTEMPT including failed execs, a deliberate anti-runaway bias, not just SHIP/NEEDS_WORK-resolved rounds), ralph.md (MAX_REVIEW_ITERATIONS now deterministic), troubleshooting.md (runaway-loop entry). <!-- Updated by plan-sync: fn-90.1 used attempt-counting (incl. failed execs) not resolved-round-counting -->
- [ ] CHANGELOG `## Unreleased` entries (repo + flow-next.dev docs-site changelog page); NO version bump (batched-release convention).
- [ ] Codex mirror regenerated (`scripts/sync-codex.sh`) + structural guard green.
- [ ] R-ID coverage check across the spec (R1-R9 all satisfied or explicitly re-scoped).


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
