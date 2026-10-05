---
title: "Bash deadline watchdogs: orphaned sleep holds pipes; group-kill via setsid, not "
date: "2026-07-16"
track: bug
category: runtime-errors
module: plugins/flow-next/skills/flow-next-prime/workflow.md
tags: [bash, timeout, process-group, setsid, watchdog, prime, fn-99]
problem_type: runtime-error
symptoms: runner pipeline hangs until TIMEOUT_SECS after all work completed; TERM-ignoring grandchildren survive timeout kills
root_cause: bare kill on a watchdog subshell orphans its sleep (holds inherited stdout); pgrep -P tree walk misses reparented descendants
resolution_type: fix
last_updated: "2026-10-05"
last_audited: "2026-10-05"
---

## Problem
An eval runner's per-run timeout (since removed from the repo) used a backgrounded watchdog subshell `( sleep N; kill ... ) &` cancelled with a bare `kill $watchdog`. Killing the subshell orphans its `sleep N` child, which inherited the runner's stdout and held the pipe open: any pipeline reading the runner (`./runner.sh | tail`) hung until the full timeout even though all work had finished. The impl review also showed that a pid-tree walk (`pgrep -P` recursion) cannot terminate descendants reparented after their parent died, a real containment gap for unsandboxed children.

## What Didn't Work
- `kill "$watchdog"` on a subshell with inherited stdio: kills the subshell only; the in-flight `sleep` survives and holds inherited fds.
- Killing the sleep first: the subshell then continues past the sleep and runs its kill commands early (worse).
- Recursive `pgrep -P` tree kill: misses processes reparented to init after their parent exits.

## Solution
The pattern now lives in `run_bounded` in `plugins/flow-next/skills/flow-next-prime/workflow.md` (the same helper is repeated in `references/boot-probe.md`). It starts the command as the leader of its own process group (`python3` calling `os.setsid()` before exec; macOS has no setsid(1)), gives the watchdog detached stdio (`>/dev/null 2>&1`) so an orphaned `sleep` cannot hold the caller's pipe, and on timeout signals the group (`kill -TERM -- -$pid`, then KILL after a grace period). On timeout it waits for the watchdog to finish that escalation; a marker file records that the deadline fired, so the 124 exit is unambiguous.

## Prevention
Any bash "run with deadline" helper: (1) start each child in a new process group and signal the group, never walk the pid tree; (2) give the watchdog detached stdio, because cancelling the watchdog subshell with a plain `kill` orphans its `sleep`, which is harmless only when that sleep holds no inherited pipe; (3) test the helper by spawning a child-of-child that outlives its parent and asserting both die on timeout, and that the caller's pipeline returns promptly on normal completion.
