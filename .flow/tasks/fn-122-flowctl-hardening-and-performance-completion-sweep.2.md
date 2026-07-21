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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
