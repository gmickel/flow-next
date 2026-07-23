---
satisfies: [R2, R7, R12]
---
# fn-130-reached-path-skill-prompt-optimization.6 Split Plan Review by selected backend

## Description
Restructure Plan Review into common orchestration plus one selected backend reference, following the existing Impl Review and Completion Review pattern. Preserve export mode, real-engine review quality, receipts, cumulative caps, re-anchors, and fix-loop semantics.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-plan-review/{SKILL.md,workflow.md,references/*.md}`, `plugins/flow-next/tests/test_backend_spec.py`, `test_skill_prose_diet.py`, review route fixtures, `optimization/review-prompt/**` extensions, corresponding Codex mirror.

### Approach
- Verify the task input hashes match `V1/B1`; compare every structural candidate against `B1`.
- Extract codex, copilot, cursor, RP, and host execution/rubric material into directly selected references; none performs no backend load.
- Preserve `--review=export` as a distinct non-review route: emit the same export artifact/output and side effects, load no configured review backend guidance, and never enter the review fix loop.
- Keep backend resolution, common validation, receipt/status, cumulative deterministic cap, re-anchor, fix cycle, and terminal verdict in common orchestration.
- Validate prompt/rubric behavior through the real backend path using planted risky and clean corpora; do not substitute only a subagent-reader comprehension test.
- Preserve user-edited spec grounding and the exact foreground/cap contracts protected by `test_skill_prose_diet.py`.
- Confirm unavailable backend interactive/autonomous behavior and Codex rewrite semantics.

### Frozen fixtures
- backend none, `--review=export`, host, codex, copilot, cursor, RP, configured-but-unavailable.
- planted risky plan, clean overflag guard, hand-edited spec, Needs Work fix cycle, Major Rethink/escalation, SHIP, cumulative-cap exhaustion.

### Investigation targets
**Required**
- `plugins/flow-next/skills/flow-next-plan-review/SKILL.md:153-222` — root export/host/backend and loop contracts.
- `plugins/flow-next/skills/flow-next-plan-review/workflow.md:59-467` — co-resident backend paths to split.
- `plugins/flow-next/tests/test_skill_prose_diet.py:248-260` — current single-source assertions.
- `optimization/review-prompt/README.md` — real-engine answer-key/clean-corpus harness.
- `plugins/flow-next/skills/flow-next-impl-review/` — common plus selected backend reference pattern.

**Optional**
- fn-112 backend-registry decisions; plan-review prompt quality history from fn-74.

## Acceptance
- [ ] Task input hashes match `V1/B1`; all eight export/backend/unavailable routes have `B1` and candidate read traces; exactly one selected backend reference loads and `--review=export` loads none.
- [ ] Export output, artifact writes, terminal behavior, and exclusion from configured-backend guidance remain equivalent to `B1`.
- [ ] Real-engine risky/clean and user-edited-spec corpora meet or exceed `B1` detection, overflag, and grounding cells.
- [ ] Verdict grammar, receipt/status writes, foreground rule, cumulative cap, re-anchor, fix loop, autonomous escalation, and terminal behavior are unchanged.
- [ ] Common orchestration contains no duplicated backend invocation blocks; mirror transforms preserve backend semantics.
- [ ] Focused backend/prose/mirror tests pass; discarded backend splits remain logged independently if one engine regresses.
- [ ] Measured non-selected-path reduction is recorded for every backend.

## Done summary
Split Plan Review into a compact common/router path plus one lazily loaded selected-backend workflow for host, Codex, Copilot, Cursor, or RP; `none`/`--export` remain backend-cold and configured-but-unavailable backends never fall through. Added production-path corpus evidence and structural ratchets: every route reduces reached prompt text by 63.80–79.21% from the 48,486-character B1 while preserving the byte-identical reviewer prompt and risky/clean/user-edited grounding contracts.

Verification: focused Plan Review suites and candidate ratchet green; smoke 136/136 green. Full suite ran once (2,225 tests) with one inherited failure in `test_setup_precheck_suppresses_prompt_on_forked_dispatch`, reproduced unchanged at base commit `01635d40`; mirror regeneration and lifecycle completion remain deferred to the conductor.
## Evidence
- Commits: 0a4400f7, ed9b6206, 63e9942e, 3e4e92ee, f3d1ff79, f7c85984, e901aa00, 1ab5bb3b, 0f08c608, c00dc797, c0142c0d, 97e9793a
- Tests: ./scripts/sync-codex.sh twice: 28 skills, 22 agents, idempotent, python3 scripts/run_tests_parallel.py: 2,286 run, 3 skipped, 0 failures/errors, bash plugins/flow-next/scripts/smoke_test.sh from /tmp: 136 passed, 0 failed, flow-next.dev build: Astro check 0 errors/warnings/hints; 74 pages built, git diff --check and changed-reference existence audit: passed, Prime authenticated Claude baseline and candidate: 7/7 each; 6/6 synthetic plus negative control
- PRs:
