# fn-16-ugn.1 Create flow-next-sync skill

## Overview

Create a new `/flow-next:sync` skill that manually triggers the plan-sync agent to update downstream task specs.

## Context

- Epic spec: `.flow/specs/fn-16-ugn.md` (read this first for full requirements)
- Existing agent: `plugins/flow-next/agents/plan-sync.md` (reuse this)
- Similar skill pattern: `plugins/flow-next/skills/flow-next-impl-review/`

## Files to Create

### 1. Command stub: `plugins/flow-next/commands/flow-next/sync.md`

```markdown
---
name: flow-next:sync
description: Manually trigger plan-sync to update downstream task specs after implementation drift
---

# IMPORTANT: This command MUST invoke the skill `flow-next-sync`

The ONLY purpose of this command is to call the `flow-next-sync` skill. You MUST use that skill now.

Pass through any arguments (task/epic ID, --dry-run flag).
```

### 2. Skill: `plugins/flow-next/skills/flow-next-sync/SKILL.md`

## SKILL.md Structure

Use this frontmatter:
```yaml
---
name: flow-next-sync
description: Manually trigger plan-sync to update downstream task specs after implementation drift. Use when code changes outpace specs.
---
```

## Workflow Steps

### 1. Parse Input

Accept: `/flow-next:sync <id> [--dry-run]`

- `<id>` can be task ID (fn-N.M) or epic ID (fn-N or fn-N-xxx)
- `--dry-run` flag optional

Detect ID type:
- Contains `.` → task ID
- No `.` → epic ID

### 2. Validate Environment

Check `.flow/` exists:
```bash
test -d .flow || echo "No .flow/ found. Run flowctl init first."
```

If missing, print error and stop.

### 3. Validate ID Exists

For task ID:
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/flowctl" show <id> --json
```

For epic ID:
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/flowctl" show <id> --json
```

If command fails, print: "Task/Epic <id> not found. Run `flowctl list` to see available."

### 4. Find Downstream Tasks

For task ID input:
```bash
# Get epic from task
EPIC=$(echo "<task-id>" | sed 's/\.[0-9]*$//')

# Get all todo and blocked tasks in epic
"${CLAUDE_PLUGIN_ROOT}/scripts/flowctl" tasks --epic "$EPIC" --json
```

Filter to `status: todo` or `status: blocked`, excluding the source task.

For epic ID input:
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/flowctl" tasks --epic "<epic-id>" --json
```

Filter to `status: todo` or `status: blocked`.

If no downstream tasks found:
```
No downstream tasks to sync (all done or none exist).
```
Stop here.

### 5. Spawn Plan-Sync Agent

Build context for agent:
- `SOURCE_TASK_ID` or `EPIC_ID` - what to sync from
- `FLOWCTL` - path to flowctl (`${CLAUDE_PLUGIN_ROOT}/scripts/flowctl`)
- `DOWNSTREAM_TASK_IDS` - comma-separated list from step 4
- `DRY_RUN` - "true" or "false"

Use Task tool with `subagent_type: flow-next:plan-sync`:
```
Sync task specs from <source> to downstream tasks.

Inputs:
- SOURCE: <id>
- FLOWCTL: ${CLAUDE_PLUGIN_ROOT}/scripts/flowctl
- DOWNSTREAM_TASK_IDS: <comma-list>
- DRY_RUN: <true|false>

<if dry-run>
DRY RUN MODE: Report what would change but do NOT use Edit tool.
</if>
```

### 6. Report Results

After agent returns, format output:

**Normal mode:**
```
Plan-sync: <source> → downstream tasks

Scanned: N tasks (<list>)
<agent summary>
```

**Dry-run mode:**
```
Plan-sync: <source> → downstream tasks (DRY RUN)

<agent summary>

No files modified.
```

## Error Messages

| Case | Message |
|------|---------|
| No `.flow/` | "No .flow/ found. Run `flowctl init` first." |
| ID not found | "<type> <id> not found. Run `flowctl list` to see available." |
| No downstream | "No downstream tasks to sync (all done or none exist)." |
| Invalid format | "Invalid ID format. Use fn-N (epic) or fn-N.M (task)." |

## Key Points

- Ignores `planSync.enabled` config (manual = always run)
- Any source task status allowed (todo, in_progress, done, blocked)
- Target set includes both `todo` and `blocked` tasks
- Reuses existing plan-sync agent (don't duplicate logic)

## Acceptance

- [ ] Command stub `commands/flow-next/sync.md` created and invokes skill
- [ ] Skill `skills/flow-next-sync/SKILL.md` created
- [ ] `/flow-next:sync fn-N.M` spawns plan-sync agent with correct context
- [ ] `/flow-next:sync fn-N` spawns plan-sync agent for whole epic
- [ ] `--dry-run` flag passed to agent
- [ ] Clear error messages for all failure cases
- [ ] Works without `.flow/config.json` planSync setting

## Done summary
Created /flow-next:sync command and skill for manual plan-sync trigger. Supports task ID (fn-N.M) or epic ID (fn-N), --dry-run flag, with ID validation and source task selection for epic mode.
## Evidence
- Commits: 9c54c1b, 0a2bdb7
- Tests: jq validate marketplace.json, jq validate plugin.json
- PRs:
## References

- Epic spec: `.flow/specs/fn-16-ugn.md`
- Agent: `plugins/flow-next/agents/plan-sync.md`
- Similar skill: `plugins/flow-next/skills/flow-next-impl-review/SKILL.md`
