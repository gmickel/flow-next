---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-288-a-business-path-bas-and-pos-can-walk.1 Implement A business path BAs and POs can walk without engineering

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Flow carries a stated role or refine lens into refine, and an interview request or an explicit lens overrides the code route. Under a non-technical lens refine leaves technical forks to engineering, speaks plainly throughout, and parks "not my call" as a hand-off, not a skip. Teams guide gains a four-step BA/PO path (including starting from a BRD); skills.md and CHANGELOG updated; Codex mirror synced.

One isolated TUI draw (simulated PO, ready spec): flow routed to refine --biz over the code's work route; round 1 asked four plain product questions and no technical ones. The draw ended early on a harness multi-select driver loop, so "not my call" and the read-back were not observed.

stage: impl-review - ran (model: gpt-6-astra) NEEDS_WORK (lens shortcut did not count as interview request) -> fixed -> SHIP

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 3d2cd589c8dccd2d04da431a0d7f061d2e2b7bf4, ca852ab1997723eb4a78e253c5a0f372df407a90
- Tests: python3 scripts/run_tests_parallel.py (3975 ok); python3 -m unittest test_flow_routing test_codex_flow_dispatch test_refine_rename test_sync_codex_check (13 ok)
- PRs: