# Plan-sync dispatch (gated reference)

> **Loaded only when phases.md 3e read `planSync.enabled == true`.** A run with
> plan-sync disabled (null/false/missing — the default) never reads this file; it
> records its `stage: plan-sync - skipped(config: planSync.enabled != true)` outcome
> line inline and advances to 3f. The mandatory stage-outcome line itself stays
> inline in phases.md 3e and is recorded whatever happens here.

Run this once for each task that reached `done` in the resolved wave.

Get remaining `todo` task IDs (the JSON is an envelope - the list lives under `.tasks`):

```bash
DOWNSTREAM=$($FLOWCTL tasks --spec <spec-id> --status todo --json | jq -r '[.tasks[].id] | join(",")') || DOWNSTREAM=EXTRACT_FAILED
```

Skip if empty (no downstream tasks to update) — recording `stage: plan-sync - skipped(empty: no downstream todo tasks)` per the stage-outcome block in phases.md 3e before advancing. `EXTRACT_FAILED` means the extraction itself broke (shape mismatch) - report it, record `stage: plan-sync - failed(EXTRACT_FAILED: <detail>)`, and re-derive the IDs from the raw JSON; never treat it as "nothing to do".

Note: Only sync to `todo` tasks. `in_progress` tasks are already being worked on - updating them mid-flight could cause confusion.

Read the cross-spec flag (single config-leaf read — plan-sync.md documents `CROSS_SPEC` as a caller-provided input):

```bash
CROSS_SPEC=$($FLOWCTL config get planSync.crossSpec --json | jq -r '.value')
```

Use the Task tool to spawn the `plan-sync` subagent with this prompt:

```
Sync downstream tasks after implementation.

COMPLETED_TASK_ID: fn-X.Y
SPEC_ID: fn-X
FLOWCTL: /path/to/flowctl
DOWNSTREAM_TASK_IDS: fn-X.3,fn-X.4,fn-X.5
CROSS_SPEC: <the $CROSS_SPEC value read above — literal "true" or "false", NOT the string "true|false">

Follow your phases in plan-sync.md exactly.
```

Plan-sync returns summary. Log it but don't block - task updates are best-effort.
