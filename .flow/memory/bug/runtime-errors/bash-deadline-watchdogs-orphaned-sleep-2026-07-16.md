---
title: "Bash deadline watchdogs: orphaned sleep holds pipes; group-kill via setsid, not "
date: "2026-07-16"
track: bug
category: runtime-errors
module: agent_docs/guidance-eval/runner.sh
tags: [bash, timeout, process-group, setsid, watchdog, eval-harness, fn-99]
problem_type: runtime-error
symptoms: runner pipeline hangs until TIMEOUT_SECS after all work completed; TERM-ignoring grandchildren survive timeout kills
root_cause: bare kill on a watchdog subshell orphans its sleep (holds inherited stdout); pgrep -P tree walk misses reparented descendants
resolution_type: fix
---

## Problem
The guidance-eval runner's per-run timeout used a backgrounded watchdog subshell `( sleep N; kill ... ) &` cancelled with a bare `kill $watchdog`. Killing the subshell orphans its `sleep N` child, which inherits the runner's stdout and holds the pipe open - any pipeline reading the runner (`./runner.sh | tail`) hangs until the full TIMEOUT_SECS even though all work finished minutes earlier. Separately, the impl-review pass showed a pid-tree walk (`pgrep -P` recursion) cannot terminate descendants that were reparented after their parent died - a real containment gap for unsandboxed `codex exec` children.

## What Didn't Work
- `kill "$watchdog"` on a subshell: kills the subshell only; the in-flight `sleep` survives, holds inherited fds.
- Killing the sleep FIRST: the subshell then *continues past* the sleep and runs its kill commands early (worse).
- Recursive `pgrep -P` tree kill: misses processes reparented to init after their parent exits.

## Solution
agent_docs/guidance-eval/runner.sh: launch BOTH the bridge command and the watchdog as their own session/process group via `perl -e 'use POSIX qw(setsid); setsid(); exec @ARGV'` (macOS has no setsid(1)), give the watchdog detached stdio (`>/dev/null 2>&1`), and cancel/terminate with GROUP signals (`kill -TERM -$pgid`). On timeout, let the watchdog complete its TERM->grace->KILL escalation before returning (a marker file records that the deadline fired, avoiding rc ambiguity).

## Prevention
Any bash "run with deadline" helper: (1) new setsid group per child, signal the group, never walk the pid tree; (2) watchdogs are also their own group with detached stdio, cancelled by group-kill; (3) test the helper by spawning a child-of-child that outlives its parent and asserting both die on timeout AND that the caller's pipeline returns promptly on normal completion.
