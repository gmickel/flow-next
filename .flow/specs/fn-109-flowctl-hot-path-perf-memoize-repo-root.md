# fn-109 flowctl hot-path perf: memoize repo root and state dir

> STUB from the fn-101 audit (2026-07-19). Small, urgent, measurable. Interview/plan optional; scope is tight enough to work directly.

## Goal & Context

`flowctl list --json` takes 30.8s wall and `flowctl status` 32s on the flow-next repo itself (100 specs / 403 tasks). Profiled root cause: `load_task_with_state` triggers 2 uncached `git rev-parse` subprocesses PER TASK via `get_repo_root()` (flowctl.py:188) and `get_state_dir()` (flowctl.py:838) - 809 subprocess spawns per list. Verified linear: pre-setting FLOW_STATE_DIR halves wall time. Affects status/show/specs/tasks/list/ready/next/spec-close; pilot and ralph run these every tick.

## Approach

1. Memoize `get_repo_root()` and `get_state_dir()` per process (functools.lru_cache or module cache). Both are zero-arg; `get_state_dir` must keep the FLOW_STATE_DIR env override live-checked or cache post-resolution (env does not change mid-process).
2. Sweep for other per-item uncached subprocess/file-read patterns identified in fn-101: `get_cursor_version`/`get_copilot_version` (flowctl.py:4737/4525) called multiple times per invocation; prospect artifacts read+frontmatter-parsed 3x per item (`_prospect_iter_artifacts._emit` flowctl.py:11035, `_prospect_detect_corruption` 8194, `_prospect_artifact_status` 8267); `_prospect_resolve_id` full-dir scan on an exact filename hit (11133); `cmd_tasks` double `get_flow_dir()` (14029/14032); triple config.json parse per `config get` (resolver at 1435 + inline dup at 7203).
3. Batch `_export_removed_export_refs` git grep fan-out (flowctl.py:16034): up to 40 sequential `git grep` per cognitive-aid export into one `git grep -e s1 --or -e s2 ...`.
4. Remember the dual-copy invariant: scripts/flowctl.py and .flow/bin/flowctl.py.

## Acceptance

- `flowctl list --json` on this repo < 1s (from 30.8s).
- `flowctl status` < 1.5s (from 32s).
- Subprocess count for `list` at 403 tasks: <= 5 (from 809). Add a regression test asserting repo-root subprocess count via monkeypatched subprocess.run.
- Full test suite + smoke_test.sh green.

## Boundaries

- No behavior changes, only caching/batching. No new config.
- Do not touch worker-handover (`anchor`) paths - parallel workstream.
