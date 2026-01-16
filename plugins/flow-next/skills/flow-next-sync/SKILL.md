---
name: flow-next-sync
description: Manually trigger plan-sync to update downstream task specs after implementation drift. Use when code changes outpace specs.
---

# Manual Plan-Sync

Manually trigger plan-sync to update downstream task specs.

**CRITICAL: flowctl is BUNDLED - NOT installed globally.** Always use:
```bash
FLOWCTL="${CLAUDE_PLUGIN_ROOT}/scripts/flowctl"
```

## Input

Arguments: $ARGUMENTS
Format: `<id> [--dry-run]`

- `<id>` - task ID (fn-N.M) or epic ID (fn-N or fn-N-xxx)
- `--dry-run` - show changes without writing

## Workflow

### Step 1: Parse Arguments

```bash
FLOWCTL="${CLAUDE_PLUGIN_ROOT}/scripts/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

Parse $ARGUMENTS for:
- First positional arg = `ID`
- `--dry-run` flag = `DRY_RUN` (true/false)

**Validate ID format first:**
- Must start with `fn-`
- If no ID provided: "Usage: /flow-next:sync <id> [--dry-run]"
- If doesn't match `fn-*` pattern: "Invalid ID format. Use fn-N (epic) or fn-N.M (task)."

Detect ID type:
- Contains `.` (e.g., fn-1.2) -> task ID
- No `.` (e.g., fn-1 or fn-1-abc) -> epic ID

### Step 2: Validate Environment

```bash
test -d .flow || { echo "No .flow/ found. Run flowctl init first."; exit 1; }
```

If `.flow/` missing, output error and stop.

### Step 3: Validate ID Exists

```bash
$FLOWCTL show <ID> --json
```

If command fails:
- For task ID: "Task <id> not found. Run `flowctl list` to see available."
- For epic ID: "Epic <id> not found. Run `flowctl epics` to see available."

Stop on failure.

### Step 4: Find Downstream Tasks

**For task ID input:**
```bash
# Extract epic from task ID (remove .N suffix)
EPIC=$(echo "<task-id>" | sed 's/\.[0-9]*$//')

# Get all tasks in epic
$FLOWCTL tasks --epic "$EPIC" --json
```

Filter to `status: todo` or `status: blocked`. Exclude the source task itself.

**For epic ID input:**
```bash
$FLOWCTL tasks --epic "<epic-id>" --json
```

1. First, find a **source task** to anchor drift detection (agent requires `COMPLETED_TASK_ID`):
   - Prefer most recently updated task with `status: done`
   - Else: most recently updated task with `status: in_progress`
   - Else: error "No completed or in-progress tasks to sync from. Complete a task first."

2. Then filter remaining tasks to `status: todo` or `status: blocked` (these are downstream).

**If no downstream tasks:**
```
No downstream tasks to sync (all done or none exist).
```
Stop here (success, nothing to do).

### Step 5: Spawn Plan-Sync Agent

Build context and spawn via Task tool:

```
Sync task specs from <source> to downstream tasks.

COMPLETED_TASK_ID: <source task id - the input task, or selected source for epic mode>
FLOWCTL: ${CLAUDE_PLUGIN_ROOT}/scripts/flowctl
EPIC_ID: <epic id>
DOWNSTREAM_TASK_IDS: <comma-separated list from step 4>
DRY_RUN: <true|false>

<if DRY_RUN is true>
DRY RUN MODE: Report what would change but do NOT use Edit tool. Only analyze and report drift.
</if>
```

Use Task tool with `subagent_type: flow-next:plan-sync`

**Note:** `COMPLETED_TASK_ID` is always provided - for task-mode it's the input task, for epic-mode it's the source task selected in Step 4.

### Step 6: Report Results

After agent returns, format output:

**Normal mode:**
```
Plan-sync: <source> -> downstream tasks

Scanned: N tasks (<list>)
<agent summary>
```

**Dry-run mode:**
```
Plan-sync: <source> -> downstream tasks (DRY RUN)

<agent summary>

No files modified.
```

## Error Messages

| Case | Message |
|------|---------|
| No ID provided | "Usage: /flow-next:sync <id> [--dry-run]" |
| No `.flow/` | "No .flow/ found. Run `flowctl init` first." |
| Invalid format | "Invalid ID format. Use fn-N (epic) or fn-N.M (task)." |
| Task not found | "Task <id> not found. Run `flowctl list` to see available." |
| Epic not found | "Epic <id> not found. Run `flowctl list` to see available." |
| No source (epic mode) | "No completed or in-progress tasks to sync from. Complete a task first." |
| No downstream | "No downstream tasks to sync (all done or none exist)." |

## Rules

- **Ignores config** - `planSync.enabled` setting is for auto-trigger only; manual always runs
- **Any source status** - source task can be todo, in_progress, done, or blocked
- **Includes blocked** - downstream set includes both `todo` and `blocked` tasks
- **Reuses agent** - spawns existing plan-sync agent, no duplication
