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
Productionized the fn-90 review-loop-runaway fixes on top of task .1's validated core. Added completion-review cap enforcement across all three backends (reusing the spec-scoped plan counter, reset on SHIP), made all 16 canonical review-receipt defaults spec/task-scoped (explicit REVIEW_RECEIPT_PATH still wins), ported the 031a0058 guards (MAJOR_RETHINK carve-out + caller-reset/deterministic-cap warning) to plan-review SKILL.md + workflow.md and added the deterministic-cap parity note to impl-review, added an offline fn-54 eval regression guard (poisoned-stream parse + convergence ratchet, run in the gate), documented the round-counting semantics (every dispatch attempt counts, incl. failed execs) and cap/receipt/reset semantics across orchestration.md/flowctl.md/ralph.md/troubleshooting.md, added the CHANGELOG ## Unreleased entry (no version bump — batched release), and regenerated the Codex mirror. Full gate green: 1518 unittests + 143 smoke tests. R1-R9 all satisfied across tasks .1 and .2.
## Evidence
- Commits: 6a23b3566d664847f4687d26ee00d7a3926f7757
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (1518 OK, baseline: green 1512), bash plugins/flow-next/scripts/smoke_test.sh from /tmp (143 passed, 0 failed), python3 optimization/review-prompt/reveval_parse_guard.py (ALL PASS), bash scripts/sync-codex.sh (structural guard green, 29 skills/21 agents)
- PRs: