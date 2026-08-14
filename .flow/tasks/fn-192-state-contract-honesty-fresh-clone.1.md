---
satisfies: [R1, R2]
---
# fn-192-state-contract-honesty-fresh-clone.1 validate: status_source-gated downgrade of the fresh-clone false error (with legacy guard)

## Description
R1+R2: in validate's epic-status rule (flowctl.py ~:35305-35310, 'Epic marked done but task ... is ...'), downgrade the finding from errors to warnings when the task's status came from the committed snapshot with no runtime state anywhere (status_source is already stamped by merge_task_runtime ~:1077 via TaskInventory.load ~:19221-19226). Suffix the warning with a committed-snapshot-may-be-stale note. LEGACY GUARD: when the task definition file itself carries legacy runtime fields (merge_task_runtime's legacy branch ~:1071-1075), committed status IS authoritative - keep the ERROR there; distinguish 'no runtime anywhere' from 'runtime lives in the tracked file'. validate's exit code is already gated on errors only (~:45103, :45185-45193) - do not change that. Precedent for finding-shape in the same function: the fn-180 evidence-reachability warnings ~:35274-35283. R5(i-iii) tests in tests/test_validate_all_diagnostics.py's style: fresh-clone-shaped fixture -> warning + exit 0; runtime-sourced mismatch -> error; legacy-fields mismatch -> error. Pin contract tokens not sentences.

## Acceptance
R1, R2, R5(i-iii) met; test_validate_all_diagnostics green; a fresh-clone simulation (spec done, sidecar todo, empty state dir) exits 0 with the warning visible; ruff clean.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
