---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-176-same-spec-concurrent-waves-with.1 Fail-closed wave dispatch rule, join collision handling, reviewer overlap, rubric check + R5 gate

## Description
Land the explicit wave-dispatch rule and reviewer overlap in the work skill (R1-R3), the rubric Touches: check (R4), and execute the R5 sandbox equivalence gate.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-work/phases.md`, `plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md`, `plugins/flow-next/skills/flow-next-plan-review/references/plan-review-prompt.md`, `plugins/flow-next/scripts/flowctl.py` (PLAN_REVIEW_PROMPT_FALLBACK string only), `.flow/bin/flowctl.py` (copy), `plugins/flow-next/tests/test_prompt_text_pinned.py` (hash pins), `plugins/flow-next/tests/fixtures/review_prompts/*.txt` (regenerated), `plugins/flow-next/codex/**` (regenerated)
**Touches:** [plugins/flow-next/skills/flow-next-work/phases.md, plugins/flow-next/skills/flow-next-plan-review/**, plugins/flow-next/scripts/flowctl.py, plugins/flow-next/tests/**]

### Approach
- phases.md 3a: replace the two vague-preference paragraphs with the fail-closed rule per spec §Architecture item 1, keeping the decision-report block and the Never-run-concurrent-writers sentence; state the error paths (missing Touches: -> serial; any intersection or doubt -> serial; always-serial set).
- phases.md 3d: add join-collision handling per item 2 (never auto-resolve; serial re-run from joined state; stage: wave-join failed(collision) line per fn-178).
- phases.md 3d/3f: reviewer-overlap rule per item 3 with the plan-sync barrier sentence.
- Rubric (R4): workflow-rp.md criterion 3 + plan-review-prompt.md criterion 8 get the Touches: plausibility/overlap sentence. plan-review-prompt.md parity chain exactly as fn-174: single-line-safe wording (avoid new continuation-line dedent issues), fallback string sync, cp dual copy, both sha pins via the CRLF-normalized commands, fixture regen via the parity-test inputs.
- R5 gate: in a temp sandbox repo, create a 2-task spec with disjoint Touches: (two independent files+tests). Run A: serial (task1 then task2 in one checkout). Run B: wave (both tasks applied in separate git worktrees, conductor merges both into the target). Assert both runs end with the identical test set green. Record commands + outcomes in evidence.
- ./scripts/sync-codex.sh x2; focused suites green.

### Acceptance
- [ ] 3a carries the rule with all six conditions + fail-closed error paths stated (R1)
- [ ] 3d collision handling: no auto-resolve, serial re-run, receipt line (R2)
- [ ] Reviewer overlap with both conditions + plan-sync barrier (R3)
- [ ] Both rubric copies check Touches: plausibility/overlap (R4); parity chain green
- [ ] R5 sandbox replay: wave outcomes == serial outcomes, recorded in evidence
- [ ] sync-codex x2 idempotent; focused suites green

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
