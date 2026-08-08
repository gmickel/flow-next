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
Landed the fail-closed wave dispatch rule in work 3a (six conditions, error paths stated, structural-backstop rationale), join collision handling in 3d (never auto-resolve, serial re-run from joined state, fn-178 collision stage line), the reviewer-overlap rule with the plan-sync barrier, and the Touches: plausibility/overlap check in both rubric copies (full parity chain for the pinned prompt). Executed the R5 sequential-equivalence gate: two-task sandbox spec with disjoint Touches: run serially and as a worktree wave - identical outcomes (2/2 OK both), byte-identical touched files, clean join.

stage: plan-sync - skipped(config: planSync.enabled != true)
stage: impl-review - skipped(policy: maintainer waived in-host review for this series; bot review on the PR is the gate)
stage: wave-dispatch - skipped(policy: fn-176.2 depends on fn-176.1 - dep path forces serial per the rule this task lands)

RECEIPT NOTE (goal): plan authored on the new prose - scope-minimal (2 tasks, no new machinery; the python checker was declined in Decision Context per the yagni discipline), tasks how-shaped without spec restatement (R-ID references, Touches: body lines, HOW in Approach). The dispatch rule itself correctly forced THIS spec serial: its two tasks share a dep edge.
## Evidence
- Commits: b3afe093
- Tests: python3 -m unittest test_prompt_text_pinned test_review_prompt_template_parity test_review_prompt_constraints test_work_reached_path_routes test_skill_prose_diet -q, R5 gate: sandbox serial vs wave replay - EQUIVALENT (2/2 OK both, identical trees), ./scripts/sync-codex.sh x2 idempotent
- PRs: