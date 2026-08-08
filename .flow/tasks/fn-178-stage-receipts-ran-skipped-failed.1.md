---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-178-stage-receipts-ran-skipped-failed.1 Stage-outcome convention in work/pilot prose + flowctl usage --stages + test

## Description
Land the stage-outcome line convention at the three orchestrator sites (R1-R4) and the flag-gated usage summarizer (R5).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-work/phases.md`, `plugins/flow-next/agents/worker.md`, `plugins/flow-next/skills/flow-next-pilot/workflow.md`, `plugins/flow-next/scripts/flowctl.py` (cmd_usage + argparse only), `.flow/bin/flowctl.py` (copy), `plugins/flow-next/tests/test_usage_stages.py` (new), `plugins/flow-next/codex/**` (regenerated)
**Touches:** [plugins/flow-next/skills/flow-next-work/phases.md, plugins/flow-next/agents/worker.md, plugins/flow-next/skills/flow-next-pilot/workflow.md, plugins/flow-next/scripts/flowctl.py, plugins/flow-next/tests/test_usage_stages.py]

### Approach
- phases.md: add the convention block near Phase 5 (line grammar `stage: <name> - ran | skipped(<reason>) | failed(<reason>) [<start>..<end>]`, skipped-is-an-event rule, no-line-is-failed inversion, token-telemetry out-of-scope note per spec R4); amend 3e so the plan-sync dispatch records ran/skipped(reason)/failed(EXTRACT_FAILED) in the completed task's done evidence (the #293 signature must yield a failed line).
- worker.md: done-summary carries stage lines for the stages the worker owns (impl-review dispatch, delegation attempt), timestamps where known.
- pilot workflow.md: the tick evidence echo includes the dispatched stage's outcome line.
- flowctl.py: extend cmd_usage with `--stages <spec-id>` + `--json` (argparse on the existing verb; bare `usage` unchanged). Parse `^stage: ` lines from the spec's task .md files; count review receipts (`.flow/review-receipts/*<spec>*.json` with a verdict) as ran; output per-stage counts {ran, skipped, failed, unknown} + reasons list. Malformed lines increment unknown; missing spec errors cleanly.
- New focused test test_usage_stages.py: green path, skipped/failed reasons, malformed-line -> unknown, --json shape. Table-driven, one test per enumerated case (R5 errors).
- Propagation: cp flowctl.py dual copy; python3 scripts/gen_tracker_manifest.py; ./scripts/sync-codex.sh x2.

### Acceptance
- [ ] Convention block present at all three sites with skipped-is-an-event + no-line-is-failed + R4 note (R1, R4)
- [ ] plan-sync 3e records outcome lines incl. failed(EXTRACT_FAILED) (R2); timestamps convention stated (R3)
- [ ] `flowctl usage --stages <spec>` plain + --json; malformed -> unknown, exit 0; bare usage unchanged (R5)
- [ ] test_usage_stages green; ruff clean; dual copy + manifest + mirrors idempotent

## Acceptance
- [ ] TBD

## Done summary
Landed the stage-outcome convention at the three orchestrator sites (work phases.md: convention block + plan-sync 3e outcome lines incl. failed(EXTRACT_FAILED); worker.md: summary stage lines for worker-owned stages; pilot workflow.md: evidence-echo stage line) with skipped-is-an-event, no-line-is-failed inversion, timestamps-where-known, and the R4 token-telemetry out-of-scope note. Implemented flowctl usage --stages (flag-gated on the existing verb; parses committed done-summary stage lines + review receipts; malformed -> unknown, exit 0; bare usage byte-identical). 6-case table-driven test green; full suite 4279 green; ruff clean; dual copy + manifest + mirrors idempotent.

stage: plan-sync - skipped(config: planSync.enabled != true)
stage: impl-review - skipped(policy: maintainer waived in-host review for this series; bot review on the PR is the gate)
stage: delegation - failed(error: cursor-agent bridge returned empty output 3x earlier in this campaign; conductor self-implemented per goal fallback)

RECEIPT NOTE (goal): this plan was authored on the new prose and came out scope-minimal - 2 tasks, every task traced to R-IDs, no unrequested surface (the usage extension stayed flag-gated on the existing verb; a telemetry subsystem was declined in Decision Context). Tasks were how-shaped without spec restatement: Description ≤10 lines referencing R-IDs, HOW in Approach, Touches: body lines per fn-175.
## Evidence
- Commits: f7a929c7
- Tests: python3 -m unittest test_usage_stages -q (6 cases), python3 scripts/run_tests_parallel.py (4279 OK), uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh x2 idempotent
- PRs: