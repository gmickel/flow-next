---
satisfies: [R1]
---
# fn-286-tracker-reconcile-flow-only-push.1 Implement Tracker reconcile flow-only push

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Refine's, capture's and plan's tracker steps now follow tracker-sync steps.md section 4 instead of naming one `--op "$OP"` call: prepare first for pull or reconcile; a reconcile classified `flow-only` with no genuine comments is a push with no body inputs; every other case reconciles with the authored files (#519). Codex mirrors regenerated. make-pr's body-preserving reconcile is untouched.

Defect route:
- prior fixes: open PRs none; recent commits on the four call sites none touching the reconcile wording; memory bug track no match; issues only #519 itself
- diagnosis: confirmed the call sites paraphrase the facade call as one `--op "$OP"` and drop section 4's flow-only branch; runtime repro against the real facade with a fake GitHub transport: reconcile with the prepared snapshot as --body-file returned success with no body sent to the issue, push without body inputs sent the refined body (wire-update)
- introduced by: skipped: no known-good revision (the wording predates the section 4 branch)
- base: the disposable repro at a12b8fc0 showed the literal reconcile leaves the issue body unchanged | head: all four sites name the section 4 branch; test_tracker_caller_execution 3/3, test_tracker_caller_oracle 1/1, test_prompt_text_pinned 3/3; full suite 3974/0 before the review fix, focused re-checks after
- live: no live surface (skill instructions; no tracker workspace exercised)

stage: impl-review - ran [round 1 NEEDS_WORK (1 P2: keep section 4's no-genuine-comments condition, fixed) .. round 2 SHIP] (model: gpt-6-astra)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 3e4f80671c1e606ff03b8cbccece4927a9fbe140, 64324c7b786ed6e4e357c180913281adb8b438c1
- Tests: python3 scripts/run_tests_parallel.py, python3 scripts/run_tests_parallel.py --pattern test_tracker_caller_execution.py, uvx ruff@0.16.0 check .
- PRs: