---
satisfies: [R6, R7, R8, R10, R11]
---
# fn-120-windows-test-corpus-compatibility-sweep.3 Fix backend hang and prove zero-exclusion Windows corpus

## Description
Find and fix the Windows backend-spec hang, harden runner process-tree cleanup, and remove the final exclusion.

**Size:** L
**Files:** plugins/flow-next/tests/test_backend_spec.py, plugins/flow-next/scripts/flowctl.py backend/subprocess helpers if proven, scripts/run_tests_parallel.py, runner regression tests, .github/workflows/test-flow-next.yml

### Approach

Use bounded per-test verbose Windows runs to bisect the hanging case. Capture child commands, stdin/pipe configuration, active processes, elapsed time, and timeout cleanup. Fix the narrow backend wait/handle cause and add regressions for both success and timeout cleanup; do not raise the 900-second ceiling.

Independently make runner cleanup unconditional: close stdin; use POSIX process groups and a Windows process-tree strategy; terminate descendants on timeout; bound post-kill collection. Add a synthetic runner regression whose grandchild holds stdout, asserting rc=124, timed-out filename, elapsed time, captured output, and descendant termination. Remove the last exclusion in the same commit as the backend/runner fix and focused Windows proof.

<!-- Updated by plan-sync: fn-120.1's fresh windows-2025 characterization (930cd764, run 30902967690) shows test_backend_spec.py PASSING in 4.4s -- the 900s hang described above did NOT reproduce on the current runner image. Re-verify reproduction under this task's own bounded/verbose run before assuming a live hang to bisect; if it stays green, this task still owes the R11 runner process-tree cleanup + synthetic regression and should record that no hang recurred (do not skip the exclusion removal or cleanup work on that basis alone). -->

<!-- Updated by plan-sync: fn-120.2 already investigated the scripts/run_tests_parallel.py:153 child-spawn encoding candidate (universal_newlines=True, no encoding kwarg) and deliberately left it unchanged after codex review -- parent/child already share the locale, so transport was symmetric with no live corruption, and forcing PYTHONIOENCODING=utf-8 on children would destroy the Windows leg's ability to catch the real cp1252 print-crash class fn-120.1 hit. Evidence: windows-latest run 30913423957 recorded as proof a Windows child's own unittest stream is cp1252. fn-120.2's done summary explicitly defers "runner encoding: pin or leave locale-faithful" to this task as a decision point -- treat it as one and weigh it against this recorded rationale rather than re-deriving from scratch; do not re-flag it as an open unchecked candidate. -->

### Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_backend_spec -v
python3 scripts/run_tests_parallel.py
```

## Acceptance
- [ ] The exact hanging test and child-process/handle cause are documented from a bounded Windows run.
- [ ] Backend and synthetic runner regressions prove normal completion and timeout cleanup with no orphan descendant or inherited interactive stdin on POSIX and Windows.
- [ ] `test_backend_spec.py` finishes below the existing file timeout on Windows; timeout is not increased.
- [ ] The final exclusion and Windows `EXCLUDES` block are removed in the same commit as the fix.
- [ ] Permanent timeout diagnostics report file, elapsed time, rc=124, and captured output with bounded post-kill collection.
- [ ] Focused Windows proof uses the exact commit SHA and records its workflow run URL/ID.

## Done summary
Retired the LAST Windows exclusion (fn-120 R6/R7/R8/R10/R11): the workflow now has no `EXCLUDES` array at all and all three OS legs run the same discovered corpus. `test_backend_spec.py` did NOT hang - the plan-sync note was right: on windows-2025 it PASSES in 4.26s against the unchanged 900s limit (focused bounded verbose run 30921644493, SHA bfbdd48a, ran=160). No timeout was raised anywhere; nothing was skipped or weakened.

The real hang risk was the RUNNER, and it was live on every platform. `subprocess.run(cmd, timeout=N)` kills only the DIRECT child and then drains the pipe with NO bound, so a grandchild that inherited the shard's stdout stalls the suite forever. Verified with teeth before fixing: with the old child-only kill the synthetic descendant stayed ALIVE and collection abandoned. Codex review then found the nastier shape I had missed - a shard that EXITS IMMEDIATELY after spawning such a descendant, where `proc.kill()` has nothing to kill and Windows `taskkill /F /T` cannot walk a tree from a dead pid.

`scripts/run_tests_parallel.py` now:
- owns a kill identity that OUTLIVES the shard (`_ShardTree`): POSIX captures the process-GROUP id at launch (own session => pgid == pid, reserved by the kernel while the group has members) and `killpg`s it regardless of parent liveness; Windows uses a ctypes **Job Object** (`TerminateJobObject` reaches every assigned process, shard alive or not), with `taskkill` kept only as the live-parent backstop and every ctypes call best-effort;
- owns the CAPTURE (a daemon reader thread draining into a buffer) instead of `communicate()`, so abandoning the reader never abandons the bytes already collected - the review's P2;
- detects a leak on EVERY path, not just on timeout: a reader still alive after the shard exited means a descendant holds the pipe, so the tree is killed and a `WARN` line is printed on the PASSING file's own status line (a leak on a pass is otherwise invisible - only failing files print output);
- closes stdin (`DEVNULL`) so no shard, and nothing it spawns, can block on the runner's inherited stdin;
- reports file, `rc=124`, elapsed, the kill action, the collection outcome and the output captured before the kill, with an UNCONDITIONAL 15s collection bound.

Runner encoding decision (fn-120.2 deferred it here): child decode stays locale-faithful (`universal_newlines`, no `encoding=`). Rationale recorded at the site - parent and child share the locale so transport is symmetric, and `PYTHONIOENCODING=utf-8` on children would destroy the Windows leg's ability to catch the real cp1252 print-crash class (evidence: run 30913423957).

Production backends: copilot's POSIX argv path and `cursor-agent` piped nothing, so they INHERITED our stdin and could block on an interactive prompt no automated caller answers. Both now pass `stdin=DEVNULL` (codex already pipes the prompt), with a regression asserting every backend exec either pipes a prompt or gets DEVNULL.

13 new regressions (29 in the runner file total): grandchild-holds-stdout timeout diagnostics, descendant proven dead via OS-neutral heartbeat sampling, shard-exits-then-leaks, output retention through abandonment with the kill deliberately suppressed, per-platform launch kwargs, stdin EOF, success-with-grandchild. Fixture timing note: the 3s per-file budget failed on a loaded macos-latest runner because the runner's clock starts at LAUNCH and must also cover interpreter startup + discovery - raised to 12s.

FINAL SHA deceb99a, run 30928443192: ALL matrix legs green. windows-latest 182 files / ran=4165 / 0 failures / ZERO exclusions, with `test_run_tests_parallel.py` PASS ran=29 (the Job Object path really executed there). Local full suite 182 files / ran=4165 green; ruff clean; codex impl-review SHIP after one NEEDS_WORK round.

HANDOVER for fn-120.4 (owns R9): run 30921678923 (SHA bfbdd48a) went RED on `test_tracker_capabilities.test_concurrent_relates_lose_no_ledger_entry` and the identical re-run 30923544649 was GREEN - a ~50% Windows FLAKE, pre-existing and unrelated to this task (that file was never excluded; it also passed at ec437e87). Signature: `TrackerError(INVALID_INPUT, subtype='path')` "<leaf> escapes <base>" from `flowctl_tracker/lifecycle/helpers.py:leaf_is_safe`, on a barrier-driven double `relate` writing into `.flow/create-first/`. Hypothesis to verify: `leaf_is_safe` resolves base and leaf INDEPENDENTLY, and Windows non-strict `Path.resolve()` stops expanding on transient errors (`ntpath._getfinalpathname_nonstrict`'s allowed-winerror list includes SHARING_VIOLATION / ACCESS_DENIED), so two concurrent writers can end up comparing a short `RUNNER~1` form against an expanded `runneradmin` one. Fix direction: derive the leaf from the ALREADY-resolved base instead of resolving twice. R9's parallel/serial/shuffled zero-exclusion proof cannot be trusted until that flake has an owner.
## Evidence
- Commits: bfbdd48a67e12de9ff0b8b9e7eea4dabe99fce38, 9b087ce7ba69fb37b6b6d6cd876a32c5529f2015, deceb99aaf020fb54632ed01fff7dae43123a411
- Tests: python3 scripts/run_tests_parallel.py (182 files / ran=4165 / 0 failures, local), uvx ruff@0.16.0 check . (clean), cd plugins/flow-next/tests && python3 -m unittest test_run_tests_parallel (29 tests), cd plugins/flow-next/tests && python3 -m unittest test_backend_spec (green), windows-latest focused bounded verbose run 30921644493 (SHA bfbdd48a): PASS test_backend_spec.py ran=160 4.26s vs 900s limit, windows-latest full parallel run 30923544649 (SHA bfbdd48a): 182 files / ran=4162 / 0 failures / zero exclusions, full matrix run 30928443192 (SHA deceb99a, FINAL): all legs green; windows 182 files / ran=4165 / 0 failures; test_run_tests_parallel PASS ran=29 (Job Object path exercised)
- PRs: