# fn-109 flowctl hot-path perf: memoize repo root and state dir

> Planned 2026-07-19 from the fn-101 audit finding (profiled, verified linear). Autonomous pipeline run; review backend codex.

## Overview

`flowctl list --json` takes 30.8s wall and `flowctl status` 32s on this repo (100 specs / 403 tasks). Profiled root cause: `load_task_with_state` triggers 2 uncached `git rev-parse` subprocesses PER TASK via `get_repo_root()` (flowctl.py:188) and `get_state_dir()` (flowctl.py:838) - 809 subprocess spawns per list. Verified linear: pre-setting FLOW_STATE_DIR (kills half the calls) halves wall time to 16.0s. Affects status/show/specs/tasks/list/ready/next/spec-close; pilot and ralph run these every tick, so this is loop-tick latency, not a cosmetic fix.

## Quick commands

```bash
time .flow/bin/flowctl list --json >/dev/null      # target <1s (baseline 30.8s)
time .flow/bin/flowctl status >/dev/null            # target <1.5s (baseline 32s)
python3 -m unittest discover -s plugins/flow-next/tests -q
bash plugins/flow-next/scripts/smoke_test.sh
```

## Approach

1. **Memoize `get_repo_root()` and `get_state_dir()`** with module-level dict caches KEYED BY `Path.cwd()` (state-dir cache additionally keyed by the `FLOW_STATE_DIR` env value). Rationale (scout-verified): `tests/test_review_convergence_cap.py` and `tests/test_anchor_bundle.py` load flowctl ONCE at module scope then `os.chdir` to fresh temp dirs per test - a first-call-wins global or bare `functools.lru_cache` leaks the first repo root across tests. cwd-keying invalidates naturally on chdir. No `functools` precedent exists in flowctl.py; hand-rolled dict matches file style.
2. **Cache SUCCESS results only.** The existing fallback branches (CalledProcessError -> `Path.cwd()` / `.flow/state`) stay uncached so a transient git failure is never sticky. Same-input-same-output preserved; no behavior change.
3. **Two separate caches** - `get_repo_root` (`--show-toplevel`, worktree-local) and `get_state_dir` (`--git-common-dir`, shared across worktrees) have different semantics; never merge them.
4. **Sweep the smaller repeat offenders** (fn-101 findings): `get_cursor_version`/`get_copilot_version` per-process memo (flowctl.py:4737/4525 - in-process only, do NOT touch the disk model cache at :3249); prospect artifact triple-read folded to one read+parse passed down (`_prospect_iter_artifacts._emit` :11035, `_prospect_detect_corruption` :8194, `_prospect_artifact_status` :8267) and `_prospect_resolve_id` exact-hit shortcut (:11133); `cmd_tasks` double `get_flow_dir()` (:14029/14032) absorbed by cache; config triple-parse per `config get` reduced to one read passed down (:1435 resolver + :7203 inline dup).
5. **Batch `_export_removed_export_refs`** (flowctl.py:16034): up to 40 sequential `git grep -n <sym>` become one `git grep -n -e s1 --or -e s2 ...` invocation (chunk if argv budget demands).
6. **Dual-copy invariant**: every flowctl.py edit lands in `plugins/flow-next/scripts/flowctl.py` AND `.flow/bin/flowctl.py` in the SAME commit - 3 DualCopyInvariant unittest suites enforce byte-parity.

## Boundaries / non-goals

- No behavior changes, no new config leaves, no CLI surface changes.
- Worker-handover (`anchor`) paths untouched - parallel workstream owns them.
- The disk-backed model-resolution cache (flowctl.py:3249) is out of scope (own invalidation, fn-112/fn-115 territory).
- fn-103 (delegation diet, other agent): zero overlap confirmed (scout-verified: fn-103 has no flowctl.py changes). Land-order note: fn-109 lands FIRST among the fn-101 siblings; fn-111/112/113/115 rebase on it (same-file adjacent regions).

## Strategy Alignment

Active tracks served by this plan:
- **Ralph autonomous mode** (the loop suite): pilot/land/ralph run `list`/`status`/`ready` every tick; 30s -> <1s per read is direct loop-tick latency reduction across the whole autonomy track.

## Decision context

- cwd-keyed dict over `lru_cache`: lru_cache never invalidates on chdir and would break the two module-scope-loaded test files; a cwd key makes the cache self-invalidating with zero API change.
- Success-only caching: preserves the documented fallback/retry semantics exactly; "no behavior change" is the spec's hard constraint.
- Sweep rides in a second task: it is lower-urgency and sits in regions fn-111/112/113/115 also touch; keeping the core memoize atomic in task .1 makes it bisectable and lets the acceptance targets land even if the sweep needs rework.

## Acceptance Criteria

- **R1:** `flowctl list --json` on this repo (100 specs / 403 tasks) completes in under 1s wall (baseline 30.8s).
- **R2:** `flowctl status` completes in under 1.5s wall (baseline 32s).
- **R3:** A regression test (monkeypatched `subprocess.run`, precedent at tests/test_backend_spec.py:1024) asserts `cmd_list` at 400+ tasks spawns <= 5 subprocesses (baseline 809).
- **R4:** Caches are cwd-keyed: existing chdir-based suites (test_review_convergence_cap.py, test_anchor_bundle.py) pass unmodified, and a new unit test proves a chdir invalidates both caches.
- **R5:** `FLOW_STATE_DIR` override honored under caching (key includes the env value); new unit test covers set/unset within one process.
- **R6:** Transient git failure is not sticky: only success results are cached; a new unit test proves a failed first call does not poison a later successful call.
- **R7:** Sweep caches land with no behavior change: version-getter memo, prospect single-read, config single-parse, cmd_tasks dedup; existing prospect/config/backend test suites pass unmodified.
- **R8:** `_export_removed_export_refs` issues at most 2 `git grep` invocations for 40 removed symbols (was 40); export output byte-identical on a fixture spec.
- **R9:** Dual-copy byte-parity holds (DualCopyInvariant suites green); full `python3 -m unittest discover` + `bash plugins/flow-next/scripts/smoke_test.sh` green.
- **R10:** CHANGELOG gains an `## Unreleased` entry (bold-lead bullet naming fn-109, mechanism sub-bullets, "No version bump (batched releases)."), and docs/flowctl.md gains the one-line perf note under `### list`/`### status`.

## Early proof point

Task fn-109.1 validates the core approach (cwd-keyed success-only memoization hits R1-R3 without breaking the chdir suites). If it fails, re-evaluate toward passing a resolved context object through call sites instead of module caches before attempting fn-109.2.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | list <1s | fn-109.1 | - |
| R2  | status <1.5s | fn-109.1 | - |
| R3  | subprocess-count regression test | fn-109.1 | - |
| R4  | cwd-keyed invalidation | fn-109.1 | - |
| R5  | FLOW_STATE_DIR override test | fn-109.1 | - |
| R6  | failure never cached | fn-109.1 | - |
| R7  | sweep caches, no behavior change | fn-109.2 | - |
| R8  | batched export git grep | fn-109.2 | - |
| R9  | dual-copy parity + full gate green | fn-109.1, fn-109.2 | - |
| R10 | CHANGELOG + flowctl.md note | fn-109.2 | - |

## References

- fn-101 audit (spec plan sections 0 and 4): profile data, 809-subprocess evidence, FLOW_STATE_DIR halving experiment.
- flowctl.py:188 (get_repo_root), :838 (get_state_dir), :847 (FLOW_STATE_DIR read), :3249 (model cache, out of scope), :4525/:4737 (version getters), :8194/:8267/:11035/:11133 (prospect), :1435/:7203 (config resolver), :14029 (cmd_tasks), :16034 (export git grep).
- tests/test_review_convergence_cap.py:183/358/471 and tests/test_anchor_bundle.py:125/478 (chdir pattern), tests/test_backend_spec.py:1024 (subprocess.run mock precedent).
