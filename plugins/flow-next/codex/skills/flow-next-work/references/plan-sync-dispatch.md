# Plan-sync dispatch (gated reference)

> **Loaded only when phases.md 3e read `planSync.enabled == true`.** A run with
> plan-sync disabled (null/false/missing — the default) never reads this file; it
> records its `stage: plan-sync - skipped(config: planSync.enabled != true)` outcome
> line on each completed task inline and advances to 3f. The mandatory per-task
> stage-outcome lines themselves stay inline in phases.md 3e and are recorded
> whatever happens here.

Run this once per resolved wave. Pass the full completed-task set as
`COMPLETED_TASK_IDS` (comma-separated). A single-task wave is a one-element
list; the agent's obligations stay per-task within that one pass. Downstream
is every remaining `todo` task — do not narrow it to a dependency closure.

Get remaining `todo` task IDs (the JSON is an envelope - the list lives under `.tasks`):

```bash
DOWNSTREAM=$($FLOWCTL tasks --spec <spec-id> --status todo --json | jq -r '[.tasks[].id] | join(",")') || DOWNSTREAM=EXTRACT_FAILED
```

Skip if empty (no downstream tasks to update) — recording `stage: plan-sync - skipped(empty: no downstream todo tasks)` on each completed task per the stage-outcome block in phases.md 3e before advancing. `EXTRACT_FAILED` means the extraction itself broke (shape mismatch) - report it, record `stage: plan-sync - failed(EXTRACT_FAILED: <detail>)` on each completed task, and re-derive the IDs from the raw JSON; never treat it as "nothing to do".

Note: Only sync to `todo` tasks. `in_progress` tasks are already being worked on - updating them mid-flight could cause confusion.

Read the cross-spec flag (single config-leaf read — plan-sync.md documents `CROSS_SPEC` as a caller-provided input):

```bash
CROSS_SPEC=$($FLOWCTL config get planSync.crossSpec --json | jq -r '.value')
```

Use the Task tool to spawn the `plan-sync` subagent with this prompt. **Routing precedence, highest first: an explicit argument in the invocation, then the project routing block in the instruction file, then the agent definition's own default, then the session model.**

```
Sync downstream tasks after implementation.

COMPLETED_TASK_IDS: fn-X.Y,fn-X.Z
SPEC_ID: fn-X
FLOWCTL: /path/to/flowctl
DOWNSTREAM_TASK_IDS: fn-X.3,fn-X.4,fn-X.5
CROSS_SPEC: <the $CROSS_SPEC value read above — literal "true" or "false", NOT the string "true|false">

Follow your phases in plan-sync.md exactly.
```

Plan-sync returns a per-task summary (one section per id in `COMPLETED_TASK_IDS`). Log it but don't block - task updates are best-effort. The conductor emits one `stage: plan-sync - …` line per completed task from those sections.
