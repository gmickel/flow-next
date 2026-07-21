---
satisfies: [R7, R8, R13, R16, R18]
---
# fn-122-flowctl-hardening-and-performance-completion-sweep.5 Unified task inventory, scanner parity, reverse dependencies, bulk state

## Description
Build one authoritative task-file iterator and command-scoped inventory for native/tracker-key IDs, canonical/legacy layouts, artifact exclusion, stable ordering, spec grouping, lookup, and runtime-state merging.

Migrate list, status, specs, tasks, worst-case next, validation, and reverse-dependency traversal with golden text/JSON parity. Build reverse adjacency once and traverse with deque. Give StateStore a meaningful bulk snapshot/deletion API or collapse the single-implementation seam while preserving monkeypatch and persistence contracts.

Complexity: 84/100.

Quick commands:
- cd plugins/flow-next/tests && python3 -m unittest test_hot_path_memoization test_hot_path_sweep test_task_runtime test_tracker_first test_validation -q
## Acceptance
- [ ] All backlog consumers share one eligible task universe and agree on native/tracker-key tasks.
- [ ] Golden human/JSON ordering and canonical/legacy precedence remain byte-equivalent.
- [ ] Reverse traversal loads each eligible task at most once plus constant overhead and covers chain, diamond, cycle, malformed, cross-spec, and tracker-key cases.
- [ ] specs, worst-case next, and validate --all use one task inventory scan per command.
- [ ] Runtime state is bulk-loaded or the unused abstraction is safely collapsed; no per-task factory churn remains.
- [ ] 400+ task status/list deterministic subprocess/read budgets prevent hot-path regression.
- [ ] Focused suites and operation-count tests pass without wall-clock CI assertions.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
