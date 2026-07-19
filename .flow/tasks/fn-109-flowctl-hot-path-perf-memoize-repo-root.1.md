---
satisfies: [R1, R2, R3, R4, R5, R6, R9]
---

## Description

Memoize `get_repo_root()` and `get_state_dir()` in flowctl.py with module-level dict caches. This alone collapses `flowctl list`/`status` from ~30s to sub-second at 400-task scale (809 git subprocesses -> <=5).

**Size:** M
**Files:** plugins/flow-next/scripts/flowctl.py, .flow/bin/flowctl.py (byte-identical mirror, SAME commit), plugins/flow-next/tests/test_hot_path_memoization.py (new)

## Approach

- `get_repo_root()` (flowctl.py:188): module dict `_REPO_ROOT_CACHE` keyed by `Path.cwd()`; cache only the SUCCESS branch (the `CalledProcessError` -> `Path.cwd()` fallback stays uncached so transient failures never stick).
- `get_state_dir()` (flowctl.py:838): dict keyed by `(Path.cwd(), os.environ.get("FLOW_STATE_DIR"))`; env override branch (:847) semantics unchanged; success-only caching for the `--git-common-dir` branch, fallback uncached.
- Keep the two caches SEPARATE (worktree-local vs common-dir semantics differ).
- No functools.lru_cache (never invalidates on chdir; would break the module-scope-loaded chdir suites).

## Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:185-210` - get_repo_root + get_flow_dir
- `plugins/flow-next/scripts/flowctl.py:838-865` - get_state_dir resolution order
- `plugins/flow-next/tests/test_review_convergence_cap.py:36-60,183` - module-scope load + chdir pattern the cache must survive
- `plugins/flow-next/tests/test_backend_spec.py:1011-1051` - subprocess.run mock/restore precedent for the regression test

**Optional:**
- `plugins/flow-next/tests/test_anchor_bundle.py:125-155` - second chdir suite
- `plugins/flow-next/scripts/flowctl.py:960-985` - load_task_with_state (the hot loop)

## Key context

- Tests load flowctl via importlib at MODULE scope then os.chdir per test - a first-call-wins cache leaks across tests. cwd-keying is the fix, not an option.
- Dual-copy invariant: 3 DualCopyInvariant unittest suites enforce scripts/flowctl.py == .flow/bin/flowctl.py byte-parity; edit both in the same commit.
- Baseline measurements (this repo, 2026-07-19): list 30.8s / status 32s / 809 subprocess spawns; FLOW_STATE_DIR preset halves list to 16.0s (linearity proof).

## Acceptance

- [ ] `time .flow/bin/flowctl list --json` < 1s on this repo (R1); `time .flow/bin/flowctl status` < 1.5s (R2)
- [ ] New test: cmd_list at 400+ generated tasks spawns <= 5 subprocesses via monkeypatched subprocess.run (R3)
- [ ] New tests: chdir invalidates both caches (R4); FLOW_STATE_DIR set/unset honored within one process (R5); failed git call not cached, later success caches (R6)
- [ ] test_review_convergence_cap.py + test_anchor_bundle.py pass UNMODIFIED
- [ ] Full unittest discover + smoke_test.sh green; DualCopyInvariant suites green (R9)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
