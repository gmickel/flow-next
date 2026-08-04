---
title: Test-runner timeout must kill a process TREE whose identity outlives the shard
date: "2026-08-04"
track: bug
category: test-failures
module: scripts/run_tests_parallel.py
tags: [windows, subprocess, process-group, job-object, timeout, ci, test-runner]
problem_type: test-failure
symptoms: "One hung/leaky test file stalls the whole suite forever, or leaves an orphan holding the shard's stdout; timeout diagnostics come back empty"
root_cause: "subprocess.run(timeout=) kills only the direct child then drains unbounded, and a kill keyed to a live parent (taskkill /T, proc.kill) cannot reach descendants of an already-exited shard"
resolution_type: fix
related_to: [bug/test-failures/windows-83-path-test-failures-were-2026-08-04]
---

## Problem
A file-level test runner that shards with `subprocess.run(cmd, timeout=N)` has TWO unbounded hang paths, and both hide behind a passing local suite:

1. On timeout, `subprocess.run` kills only the DIRECT child and then calls `communicate()` with **no** timeout. A grandchild that inherited the shard's stdout keeps the pipe's write handle open, so the drain never sees EOF and the whole suite stalls forever - the "one hung file" turning into "CI job killed at the 6h limit".
2. A shard that **exits immediately** after spawning such a descendant is worse: there is no live parent left, so `proc.kill()` has nothing to kill and Windows `taskkill /F /T` cannot walk a tree from a dead pid. The descendant is orphaned AND still holds the pipe.

## What Didn't Work
- `taskkill /F /T /PID <pid>` as the Windows "process tree" strategy: correct only while the shard is alive.
- Short-circuiting the kill when `proc.poll() is not None` ("shard already exited, nothing to do") - that is precisely case 2, where the descendants are the whole problem.
- Falling back to `proc.communicate(timeout=...)` a second time after the kill: bounded, but it returns NOTHING on the abandonment path, discarding the captured output that is the only evidence of what hung.

## Solution
Own both the kill identity and the capture (`scripts/run_tests_parallel.py`, fn-120.3):

- **Kill identity outlives the shard.** POSIX: launch with `start_new_session=True` and record the process-GROUP id at launch (own session ⇒ pgid == pid; the kernel reserves that number while the group has members), then `os.killpg(pgid, SIGKILL)` regardless of parent liveness. Windows: a **Job Object** via ctypes (`CreateJobObjectW` / `OpenProcess` / `AssignProcessToJobObject` / `TerminateJobObject`) - it kills every assigned process whether or not the shard lives; `taskkill` stays only as the live-parent backstop.
- **Own the capture**: a daemon reader thread drains stdout into a list. Abandoning the reader after a bounded join never abandons the bytes already collected.
- **Detect the leak on EVERY path**, not just on timeout: if the reader is still alive after `proc.wait()` returned, a descendant holds the pipe - kill the tree and print a `WARN` line on the passing file's status line (a leak on a PASS is otherwise invisible, because only failing files print output).
- `stdin=subprocess.DEVNULL` for every shard, so nothing it spawns can block on the runner's inherited stdin.

## Prevention
Synthetic regressions, not hope - a grandchild that inherits stdout and ticks a heartbeat file every 0.1s. Sample the heartbeat twice ~1.5s apart to prove a *running* descendant is gone (OS-neutral; no psutil, no tasklist parsing). Cover BOTH shapes (shard hangs, shard exits immediately), assert the bound holds with the kill deliberately suppressed, and assert the captured marker survives abandonment.

Two fixture-timing traps worth remembering: the runner's timeout clock starts at LAUNCH, so a per-file timeout in a test fixture must also cover interpreter startup + unittest discovery (3s passed locally and failed on a loaded macos-latest runner); and when patching a fake `Popen` into such a runner, launch the stand-in with the same session/group isolation, or a stray group kill can reach the test process's own group.
