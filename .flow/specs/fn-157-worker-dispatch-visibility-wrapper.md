# Worker dispatch visibility: wrapper subagents + streaming discipline

**Status: STUB.** Captured from a live pilot run on 2026-08-01/02 (flow-swarm, fn-150). Needs interview + task breakdown before work.

## Problem

When a pilot/work stage dispatches an external CLI worker (cursor-agent, codex, another claude), the host currently does it as a single blocking shell call with stdout redirected to a file:

```
cursor-agent -p --model <m> "$(cat /tmp/fn150-worker-1.md)" > /tmp/fn150-worker-1.out 2>&1
```

Observed consequences during the fn-150 run:

- The worker ran **21 minutes** with **zero** host-visible output. `/tmp/fn150-worker-1.out` stayed 0 bytes for the entire run — `cursor-agent -p` block-buffers on a non-TTY and flushes only at exit.
- The host UI (T3 Code, but any harness behaves the same) showed one anonymous in-flight Bash call. "Working normally" and "wedged" are visually identical.
- The user could not distinguish progress from a hang without out-of-band forensics: `ps` elapsed/CPU, `lsof` on the process, and the vendor's own session log at `$TMPDIR/cursor-agent-logs-<uid>/session-*.log` — which *was* updating every minute the whole time, but is discoverable by nobody.
- A false "it stopped" conclusion followed, and the user prodded the loop by hand.

This is a **dispatch-pattern** problem, not a host-UI problem. No harness can render a stream that was deliberately redirected to a file.

## Proposed direction (to be validated, not yet decided)

Two changes, independent but complementary:

**1. Wrapper subagent per dispatched worker.** Instead of the conductor blocking on the shell call itself, spawn a thin subagent whose only job is to run the worker, tee its output, poll it, and report. Gains: the harness renders each worker as a named live entity with its own tool-call feed; several workers can run concurrently; the wrapper can summarize mid-flight and apply a stall policy. Cost: one extra agent per worker, and the wrapper must not re-plan or "help" — its contract is dispatch + observe + report, nothing else.

**2. Streaming discipline (required regardless of 1).** A wrapper alone does not fix buffering — it relocates the silence. The dispatch line must keep the stream alive:

- `2>&1 | tee <logfile>` rather than `> <logfile> 2>&1`, so output is both observable and captured; and/or
- drive the worker with its own structured stream (`--output-format stream-json` where the backend supports it) and project progress events; and/or
- adopt a heartbeat: emit an elapsed-time line every N seconds so silence is distinguishable from death.

## Open questions

- Which backends support a streaming/structured output mode today (cursor-agent, codex, claude), and what is the fallback for those that do not?
- Does the wrapper belong in the pilot skill, in `work`, or in a shared dispatch helper used by both?
- Stall policy: what elapsed-without-output threshold warrants surfacing a warning, and should it ever escalate to killing the worker?
- Should the vendor session log (`$TMPDIR/cursor-agent-logs-*/session-*.log` and equivalents) be surfaced as a fallback progress source when the worker's own stdout is opaque?
- Interaction with `PILOT_VERDICT` — does a stalled worker produce `BLOCKED`, `NEEDS_HUMAN`, or neither?

## Non-goals

- Changing how the work stage selects or orders tasks.
- Any host-specific (T3 Code) UI work. The fix is in what the dispatcher emits, not in what one client renders.

## Evidence

- Run: flow-swarm `fn-150-provider-instances-multiple-claudecodex`, task .1, 2026-08-01 23:42 → 00:03 CEST.
- Worker: `cursor-agent -p --model cursor-grok-4.5-high`, pid 7519, 21 min wall clock, 9s CPU, one ESTABLISHED TLS connection throughout.
- Outcome was fine (`0ed3c81a`, 19 tests pass, lint green) — the defect is purely that nobody could tell while it ran.
