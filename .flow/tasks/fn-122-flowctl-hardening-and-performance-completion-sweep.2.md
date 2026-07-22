---
satisfies: [R2, R3, R6, R16]
---
# fn-122-flowctl-hardening-and-performance-completion-sweep.2 Transactional task creation, portable locks, spawn-fallback hardening

## Description
Fix the confirmed concurrent task-create data-loss path and replace the POSIX-only/no-op-on-Windows locking behavior with one portable cross-process contract.

Lock per-spec task allocation across scan, exclusive reservation, JSON/Markdown publication, and failure cleanup. A success response must correspond to one durable unique ID and matching artifacts. Define bounded lock acquisition and stale-owner behavior. Apply the same real exclusion semantics to task runtime and setup-block read-modify-write critical sections. Catch OSError variants in repo/state/version discovery where graceful fallback is promised, keeping failures non-sticky.

Use real subprocess races rather than thread-only mocks. Preserve canonical/legacy layout behavior and current JSON/text responses outside corrected failure cases.

Complexity: 82/100.

Quick commands:
- cd plugins/flow-next/tests && python3 -m unittest test_task_create_files test_task_runtime test_setup_block test_hot_path_memoization -q
## Acceptance
- [ ] 20-40 concurrent task creators cannot overwrite an ID or mix JSON/Markdown content.
- [ ] Every acknowledged success persists exactly once; collision and injected second-write failures are explicit and leave no half-created task.
- [ ] POSIX and Windows receive real inter-process exclusion; no ImportError path becomes a no-op lock.
- [ ] Parallel runtime/start/setup-block tests prove exactly-one-winner or lossless-merge behavior as appropriate.
- [ ] Lock timeout and stale-owner/recovery semantics are deterministic and tested.
- [ ] FileNotFoundError, PermissionError, and equivalent OSError probes fall back without poisoning later successful discovery.
- [ ] Focused suites pass with existing output/layout semantics preserved.
## Done summary
Implemented transactional task creation and portable locking. Task IDs now allocate under a per-spec kernel lock; paired JSON/Markdown publication is no-clobber and rolls back partial writes. Runtime and setup state use bounded POSIX/Windows kernel locks with crash recovery and stable CLI errors. Repo/state/CLI discovery now treats spawn OSErrors as retryable fallbacks.
## Evidence
- Commits: e98d021d, 56dcfb23
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_portable_locks test_task_create_files test_setup_block_helper test_hot_path_memoization -q (53 passed), cd plugins/flow-next/tests && python3 -m unittest test_task_create_files test_portable_locks test_setup_block_helper test_hot_path_memoization test_anchor_bundle test_pilot_backlog_substrate -q (106 passed before final review fixes), python3 -m py_compile plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py, Codex implementation review round 3: SHIP
- PRs: