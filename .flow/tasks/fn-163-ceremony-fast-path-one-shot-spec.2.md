---
satisfies: [R1, R3, R4, R6]
---
# fn-163-ceremony-fast-path-one-shot-spec.2 Bulk task create --from-json + inline field variants + invocation-count test

## Description
Add bulk task creation (`task create --spec fn-N --from-json <path|->`) and inline `--description`/`--acceptance` string variants to flowctl, with atomic all-or-nothing semantics, plus the R1 invocation-count test proving the canonical flow fits in <=8 calls.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (cmd_task_create ~:28275, parser ~:47593-47615), `plugins/flow-next/tests/test_task_bulk_create.py` (new), `plugins/flow-next/tests/test_task_create_files.py` (inline-variant cases)

### Approach
- `--from-json` accepts a path or `-` (stdin). Mutually exclusive with `--title` and the single-task field flags. **Strict input schema:** non-empty JSON array of objects; per item: `title` required non-empty string; `description`/`acceptance` optional strings; `satisfies` optional ARRAY of R-ID token strings (grammar via `parse_satisfies_tokens`); `deps` optional array whose elements are task-id strings OR JSON integers (1-based index of an EARLIER entry); `priority` optional integer. Unknown keys, nulls, wrong types, empty array, empty/whitespace title → reject whole batch, typed error, zero writes.
- **Dep semantics preserved verbatim:** string deps validate exactly like granular `--deps` — canonicalization + same-spec membership via `_resolve_same_spec_deps`, NO new file-existence check (adding one would diverge bulk from granular and break equivalence). Index deps: out-of-range/forward → reject whole batch.
- **Output contract:** `--json` returns ordered created tasks (`{"success": true, "tasks": [{"id", "title"}, ...]}` in input order) — callers need the ids for `start`.
- Parse + validate the ENTIRE array before any write.
- Allocate all N ids under ONE acquisition of the per-spec task-create lock (`scan_max_task_id` + sha256-keyed lock, ~:28342-28403) — never N separate acquisitions. Write via `atomic_create`; on any failure remove every file created so far (extend the existing single-task rollback shape).
- Inline `--description`/`--acceptance` strings: mutually exclusive with their `-file` twins; write through the identical content path.
- Duplicate titles within a batch are ALLOWED (matches granular behavior); fixture asserts distinct ids.
- R1 test: script the canonical flow (spec create --plan-file, task create --from-json with 3 tasks, start x3, done x3) as REAL subprocess invocations of the production `flowctl.py` (the subprocess wire-form `test_anchor_bundle.py` uses for its baseline; flowctl's `main()` takes no argv param, so in-process dispatch is not an option) and assert <=8 subprocess calls (one subprocess run = one counted invocation).

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:28275-28410` — cmd_task_create: pre-write validation block, lock, alloc, atomic_create, rollback
- `plugins/flow-next/tests/test_task_create_files.py` — equivalence, error-ordering, rollback, 40-process concurrency patterns to extend

**Optional**:
- `plugins/flow-next/scripts/flowctl.py:47593-47615` — parser registration
- `plugins/flow-next/tests/test_create_first_recovery.py` — idempotency patterns

### Key context
- R3 equivalence: bulk output must be byte-identical (frozen time) to the same tasks created via N granular full-field `task create` calls.
- Concurrency: a concurrent single `task create` racing a bulk batch must never produce id collisions — cover with a process-race test mirroring `test_40_process_creators_publish_unique_matching_pairs`.
- Depends on task .1 landing first (invocation-count test uses `--plan-file`).

### Acceptance
- [ ] Bulk happy path: N tasks from JSON, one lock acquisition, state byte-identical (frozen time) to granular sequence
- [ ] Rejection fixtures for every boundary: malformed JSON, non-array, empty array, missing/empty title, wrong field types (boolean-as-integer, number-as-string), nulls, unknown keys, bad dep index → error before any write; `.flow/tasks/` unchanged (asserted)
- [ ] `--json` output lists created task ids in input order
- [ ] Intra-batch index deps resolve to allocated ids; forward/out-of-range index rejects whole batch
- [ ] Duplicate titles allowed with distinct ids
- [ ] Rollback removes all batch files on induced partial publication failure
- [ ] Inline `--description`/`--acceptance` equivalent to `-file` twins; mutual exclusion enforced
- [ ] Invocation-count test: canonical spec+3-tasks flow <=8 production CLI dispatches (R1)
- [ ] Focused suite green: `python3 -m unittest test_task_bulk_create test_task_create_files -q`
## Acceptance
- Bulk `--from-json` validates atomically, allocates under one lock, rejects partial input with no writes (R3)
- Bulk-vs-granular state equivalence proven byte-identical under frozen time (R3)
- Fixture matrix: happy path, malformed JSON, duplicate titles, dependency-carrying tasks incl. intra-batch indexes, rollback, concurrency race (R6)
- Invocation-count test demonstrates <=8 calls for the canonical flow (R1)
- Receipts/evidence/start/done schemas untouched (R4)
## Done summary
Implemented bulk task creation (`task create --spec fn-N --from-json <path|->`) with the strict input contract (non-empty array; typed fields; unknown keys/nulls/wrong types/empty titles → whole-batch reject, zero writes), single per-spec lock acquisition for the whole batch, atomic_create publication with all-created-files rollback, intra-batch 1-based index deps resolved after allocation, ordered `--json` output of created ids, and inline `--description`/`--acceptance` string variants (mutually exclusive with -file twins). Granular dep semantics preserved verbatim (canonicalization + same-spec membership, no new existence check). R1 invocation-count test drives the canonical spec+3-tasks flow as real subprocess invocations and asserts <=8 (exactly 8). 72 tests green across bulk/create/plan-file suites; ruff clean. Implemented by grok-4.5 bridge, host-verified.
## Evidence
- Commits: eaa75b241269ffca714b66a6bfe7ed2836cb93ce
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_task_bulk_create test_task_create_files test_spec_create_plan_file -q
- PRs: