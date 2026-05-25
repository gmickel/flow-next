---
name: flow-next-sync
description: Manually trigger plan-sync to update downstream task specs after implementation drift. Use when code changes outpace specs.
user-invocable: false
---

# Manual Plan-Sync

Manually trigger plan-sync to update downstream task specs.

**CRITICAL: flowctl is BUNDLED - NOT installed globally.** Always use:
```bash
FLOWCTL="$HOME/.codex/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Input

Arguments: $ARGUMENTS
Format: `<id> [--dry-run]`

- `<id>` - task ID `fn-N-slug.M` (or legacy `fn-N.M`, `fn-N-xxx.M`) or spec ID `fn-N-slug` (or legacy `fn-N`, `fn-N-xxx`)
- `--dry-run` - show changes without writing

## Workflow

### Step 1: Parse Arguments

```bash
FLOWCTL="$HOME/.codex/scripts/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

Parse $ARGUMENTS for:
- First positional arg = `ID`
- `--dry-run` flag = `DRY_RUN` (true/false)

**Validate ID format first:**
- Must start with `fn-`
- If no ID provided: "Usage: /flow-next:sync <id> [--dry-run]"
- If doesn't match `fn-*` pattern: "Invalid ID format. Use fn-N-slug (spec) or fn-N-slug.M (task). Legacy fn-N, fn-N-xxx also work."

Detect ID type:
- Contains `.` (e.g., fn-1.2 or fn-1-add-oauth.2) -> task ID
- No `.` (e.g., fn-1 or fn-1-add-oauth) -> spec ID

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
- For spec ID: "Spec <id> not found. Run `flowctl specs` to see available."

Stop on failure.

### Step 4: Find Downstream Tasks

**For task ID input:**
```bash
# Extract spec from task ID (remove .N suffix)
SPEC=$(echo "<task-id>" | sed 's/\.[0-9]*$//')

# Get all tasks in spec
$FLOWCTL tasks --spec "$SPEC" --json
```

Filter to `status: todo` or `status: blocked`. Exclude the source task itself.

**For spec ID input:**
```bash
$FLOWCTL tasks --spec "<spec-id>" --json
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

### Step 5: Gather glossary + decisions + strategy context

Three extra context types help the agent catch drift the spec text alone can't reveal: project-glossary terms (renames where the old spec used a term whose `_Avoid_` alias now appears in code), active decision constraints (current code may touch files mentioned in a decision's `Consequences` section), and strategic-intent drift (completed task contradicts an active `STRATEGY.md` track or approach).

```bash
GLOSSARY_JSON="$("$FLOWCTL" glossary list --json 2>/dev/null \
 || echo '{"groups":[],"file_count":0,"total_terms":0}')"
DECISIONS_JSON="$("$FLOWCTL" memory list --track knowledge --category decisions --json 2>/dev/null \
 || echo '{"entries":[],"legacy":[],"count":0,"status":"active"}')"
STRATEGY_CONTENT="$("$FLOWCTL" strategy read --json 2>/dev/null || echo '{}')"
```

All three calls are best-effort — empty defaults keep the agent prompt valid when flowctl returns nothing or fails.

**Husk short-circuit** — when ALL three of the following hold, skip the extra context entirely (pass the empty defaults; the agent's husk short-circuit at the top of Phase 3b will skip the whole section):

- `GLOSSARY_JSON.total_terms == 0` (glossary missing or husk)
- `DECISIONS_JSON.count == 0` (no decision entries)
- `STRATEGY_CONTENT.sections_filled == 0` OR `STRATEGY_CONTENT == {}` (no STRATEGY.md or husk — verify with `flowctl strategy status --json | jq '.sections_filled // 0'`)

When ANY of the three has signal, pass through all three (untouched) and let the agent run the matching subsection (3b.1 / 3b.2 / 3b.3) and skip the empty ones.

When `GLOSSARY_JSON.total_terms == 0` but `file_count > 0`, every group is a husk. Husks carry no signal for drift detection — pass the JSON through untouched and let the agent skip them.

### Step 6: Spawn Plan-Sync Agent

Build context and spawn via Task tool:

```
Sync task specs from <source> to downstream tasks.

COMPLETED_TASK_ID: <source task id - the input task, or selected source for spec mode>
FLOWCTL: $HOME/.codex/scripts/flowctl
SPEC_ID: <spec id>
DOWNSTREAM_TASK_IDS: <comma-separated list from step 4>
DRY_RUN: <true|false>

GLOSSARY_JSON: <output of `flowctl glossary list --json` from step 5>
DECISIONS_JSON: <output of `flowctl memory list --track knowledge --category decisions --json` from step 5>
STRATEGY_CONTENT: <output of `flowctl strategy read --json` from step 5>

<if DRY_RUN is true>
DRY RUN MODE: Report what would change but do NOT use Edit tool. Only analyze and report drift.
</if>
```

Use Task tool with `subagent_type: flow-next:plan-sync`.

**Note:** `COMPLETED_TASK_ID` is always provided - for task-mode it's the input task, for spec-mode it's the source task selected in Step 4.

### Step 7: Report Results

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
| Invalid format | "Invalid ID format. Use fn-N-slug (spec) or fn-N-slug.M (task). Legacy fn-N, fn-N-xxx also work." |
| Task not found | "Task <id> not found. Run `flowctl list` to see available." |
| Spec not found | "Spec <id> not found. Run `flowctl list` to see available." |
| No source (spec mode) | "No completed or in-progress tasks to sync from. Complete a task first." |
| No downstream | "No downstream tasks to sync (all done or none exist)." |

## Rules

- **Ignores config** - `planSync.enabled` setting is for auto-trigger only; manual always runs
- **Any source status** - source task can be todo, in_progress, done, or blocked
- **Includes blocked** - downstream set includes both `todo` and `blocked` tasks
- **Reuses agent** - spawns existing plan-sync agent, no duplication
