---
satisfies: [R14, R18, R40]
---
# fn-135-chart-decision-map-discovery-for.1 Build shared allocator and crash-recoverable chart store

## Description
### Objective

Build the cross-kind allocation and crash-recoverable storage foundation only. Refactor spec creation onto the shared allocation lock, establish chart/decision canonical paths and v1 JSON envelopes, and prove paired/multi-file recovery before graph or claim behavior is layered on.

### Exact files

- `plugins/flow-next/scripts/flowctl.py` — shared spec+chart allocator/reservation lock, chart and D-ID canonicalizers, chart create/show/list skeleton, transaction journal/recovery primitive, exact chart JSON envelope helpers, and refactored spec create publication.
- `plugins/flow-next/tests/test_chart_store.py` — new allocation, canonicalization, envelope, no-clobber, handled-failure, and process-termination recovery suite.
- `plugins/flow-next/tests/test_spec_id_allocation.py` — extend concurrency/collision coverage so specs and charts share one allocation domain across worktrees/refs and spec create uses the common lock.

### Investigation targets

- Reuse `atomic_write`, `atomic_write_json`, `atomic_create`, and `cross_process_lock` around `flowctl.py:88` and `2225-2276`, but do not claim the current `cmd_spec_create` path already has paired rollback—it does not.
- Extend `scan_max_native_fn_spec_id` and the monotonic worktree/ref scan around `7845-7895` and `15267-15390`; do not allocate charts from a second counter.
- Put `spec create` and `chart create` under one allocator lock. Reserve with no-clobber publication so concurrent kinds cannot select the same `fn-N`.
- Add a write-ahead journal under `.flow/charts/.transactions/` containing pre-state fingerprints, the complete intended mutation set, staged file locations, and publication phase. Flush journal/staged data before replacement. Every chart command recovers an incomplete journal under the same resource lock by deterministic roll-forward or restore.
- Canonicalize `<chart-id>.D<n>` before I/O. D-IDs are chart-local; decision files remain `<n>.md/.json`.
- Use exact v1 envelopes: success `{success:true,schema_version:1,command,result}`; failure `{success:false,schema_version:1,command,error:{class,code,message,details}}`.

### Required behavior and examples

- Concurrent `spec create` and `chart create --title "Tenant isolation" --outcome "A capture-ready tenant model"` allocate different monotonic ids across linked worktrees and visible refs.
- Chart create publishes `.flow/charts/fn-N.md/.json` with an empty ledger; injected handled exceptions leave no half pair.
- A killed process between journal, staging, and publication is repaired on the next chart command; tests kill a subprocess at named failpoints and assert exact recovered state.
- `show`/`list` return compact chart metadata via exact result fixtures; no graph, frontier, or claims in this task.

### Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_chart_store test_spec_id_allocation -q
```

Do not run distribution propagation here; task 7 owns the final generated-copy chain after all flowctl edits.

### Non-goals

- No graph/frontier/claims/config; task 9 owns them.
- No resolve, briefing, tracker, skill, or docs.
## Acceptance
- Spec and chart creation use one allocation lock/domain and remain monotonic/collision-free under concurrent linked-worktree creation and visible-ref scanning.
- Chart/D-ID canonicalization rejects ambiguous or cross-chart identifiers before I/O.
- Chart/decision publication has a durable journal; handled-failure and killed-process failpoints recover to a complete pre-state or intended post-state, never a split pair/ledger.
- `spec create` is refactored onto the common allocation lock without changing its public output or file schema.
- Every implemented chart JSON path matches exact v1 success/failure fixtures using the existing `success` convention.
- Focused commands pass: `cd plugins/flow-next/tests && python3 -m unittest test_chart_store test_spec_id_allocation -q`.
## Done summary
Built the fn-135 storage foundation: one cross-kind native fn-N allocation domain for specs+charts (working tree + linked worktrees + refs) under a single allocation lock with no-clobber publication; chart/D-ID canonicalizers; chart create/show/list with exact v1 JSON envelopes (success/error classes per spec); write-ahead journal under .flow/charts/.transactions/ with pre-state fingerprints and deterministic roll-forward/restore recovery on every chart command; spec create refactored onto the shared lock without output/schema changes. Implemented by grok-4.5 worker, host-reviewed (Fable) + live-smoked (spec fn-1 / chart fn-2 / spec fn-3 in temp repo).
## Evidence
- Commits: 2e4a5b53
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_chart_store test_spec_id_allocation -q, cd plugins/flow-next/tests && python3 -m unittest test_task_create_files test_config_snapshot -q
- PRs: