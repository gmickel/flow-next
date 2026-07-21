---
satisfies: [R17, R18, R19, R20]
---
# fn-122-flowctl-hardening-and-performance-completion-sweep.11 Integration benchmark, cross-platform gate, and completion evidence

## Description
Run the final integrated verification once all tasks land. Collect the reproducible pre/post benchmark report for ordinary and specialized paths, explicitly including plugin-bin/copy help, flowctl usage, setup-mode, config, list, status, specs, prime, export, memory, cascade, and pilot. Compare deterministic operation counts and investigate every >10% regression.

Exercise Python minimum/latest, Windows locking/launcher coverage, plugin/copy modes, plugin-bin, mirrors, dogfood and Ralph copies, full Python suite, shell smokes, plugin validation, and docs build. Prepare completion-review evidence with commits, exact commands/results, benchmark tables, retained/deferred findings, and clean-worktree state. Do not bump or release.

Complexity: 72/100.

Quick commands:
- python3 scripts/run_tests_parallel.py
- cd plugins/flow-next/scripts && bash smoke_test.sh
- ./scripts/sync-codex.sh && ./scripts/sync-codex.sh
- claude plugin validate plugins/flow-next
- cd ~/work/flow-next.dev && pnpm build
## Acceptance
- [ ] Final report contains reproducible pre/post medians and operation counts for help/usage/setup-mode/config/list/status/specs/prime/export/memory/cascade/pilot.
- [ ] No optimized path regresses >10% without an explicit correctness justification accepted in the evidence.
- [ ] Full parallel suite, focused platform/launcher/locking tests, shell smokes, mirror idempotency, plugin validation, and docs build pass.
- [ ] Python 3.11 and latest-stable gates pass; Windows tests prove real lock behavior.
- [ ] Canonical flowctl, plugin-bin, dogfood copy, Ralph copy, templates, and Codex mirror are synchronized with fn-121 invariants intact.
- [ ] Worktree scope is clean apart from intended fn-122 artifacts and associated code/docs changes.
- [ ] Completion evidence lists commits/tests, retained/deferred findings, and confirms no version bump or release.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
