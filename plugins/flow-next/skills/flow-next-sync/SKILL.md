---
name: flow-next-sync
description: Manually trigger plan-sync to update downstream task specs after implementation drift. Use when code changes outpace specs.
user-invocable: false
---

# Manual Plan-Sync

Manually trigger plan-sync to update downstream task specs.

## Preamble

**CRITICAL: flowctl is BUNDLED - NOT installed globally.** Define once; subsequent blocks use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Input

Arguments: $ARGUMENTS
Format: `<id> [--dry-run]`

- `<id>` - task ID `fn-N-slug.M` (or legacy `fn-N.M`, `fn-N-xxx.M`) or spec ID `fn-N-slug` (or legacy `fn-N`, `fn-N-xxx`), **or a resolvable tracker handle** (`wor-17` / `wor-17.M`) that `flowctl show` maps to the linked spec/task (fn-52.10, R16)
- `--dry-run` - show changes without writing

## Workflow

### Step 1: Parse Arguments

```bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

Parse $ARGUMENTS for:
- First positional arg = `ID`
- `--dry-run` flag = `DRY_RUN` (true/false)

**Validate ID first (handle-recognition rule, R16):**
- **The id is resolved by `flowctl show`, not by a prefix check.** A session that rejects a resolvable tracker handle as an unknown id — because it gated on "must start with `fn-`" — has broken this. Route the arg through `$FLOWCTL show <ID> --json` (Step 3); flowctl's widened resolver (fn-52.10) maps a tracker key (`wor-17` / `wor-17.M`) to its linked spec/task, so a resolvable handle is the existing spec/task, never a new id. `/flow-next:sync wor-17` therefore resolves the linked spec.
- If no ID provided: "Usage: /flow-next:sync <id> [--dry-run]"
- If the arg does not resolve via `flowctl show` (Step 3): "Unknown ID. Use fn-N-slug (spec) / fn-N-slug.M (task), a tracker handle (wor-17), or legacy fn-N, fn-N-xxx."

Detect ID type (use the canonical id from `flowctl show`):
- Contains `.` (e.g., fn-1.2, fn-1-add-oauth.2, wor-17.2) -> task ID
- No `.` (e.g., fn-1, fn-1-add-oauth, wor-17) -> spec ID

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

#### Done when

- A source task is anchored — the input task in task mode, or the most recently updated `done` (else `in_progress`) task in spec mode — or the run stopped with the documented refusal because neither exists.
- `DOWNSTREAM_TASK_IDS` holds the spec's `todo` and `blocked` tasks with the source task excluded. **An empty downstream set stops the run here.** A session that spawns the agent with nothing downstream has broken this.

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

**Husk short-circuit** — when all three of the following hold, skip the extra context entirely (pass the empty defaults; the agent's husk short-circuit at the top of Phase 3b will skip the whole section):

- `GLOSSARY_JSON.total_terms == 0` (glossary missing or husk)
- `DECISIONS_JSON.count == 0` (no decision entries)
- `STRATEGY_CONTENT.sections_filled == 0` OR `STRATEGY_CONTENT == {}` (no STRATEGY.md or husk — verify with `flowctl strategy status --json | jq '.sections_filled // 0'`)

When any of the three has signal, pass through all three (untouched) and let the agent run the matching subsection (3b.1 / 3b.2 / 3b.3) and skip the empty ones.

When `GLOSSARY_JSON.total_terms == 0` but `file_count > 0`, every group is a husk. Husks carry no signal for drift detection — pass the JSON through untouched and let the agent skip them.

#### Done when

- All three variables are populated — **with the documented empty default preserved on failure**, never dropped. A prompt built with a missing `GLOSSARY_JSON` / `DECISIONS_JSON` / `STRATEGY_CONTENT` key has broken this.
- The husk short-circuit passes the empty defaults through when all three carry no signal, and passes all three untouched when any one has signal.

### Step 6: Spawn Plan-Sync Agent

Read the cross-spec flag first — the same single config-leaf read `/flow-next:work` performs, so a repo that opted into cross-spec propagation (`planSync.crossSpec=true`) gets the same behavior from a manual `/flow-next:sync` as from the work-loop auto-trigger. Without this, `CROSS_SPEC` is unset and plan-sync skips the cross-spec phase entirely — the tool you reach for after big drift silently checks only same-spec tasks:

```bash
CROSS_SPEC=$($FLOWCTL config get planSync.crossSpec --json | jq -r '.value')
```

Build context and spawn via Task tool:

```
Sync task specs from <source> to downstream tasks.

COMPLETED_TASK_ID: <source task id - the input task, or selected source for spec mode>
FLOWCTL: ${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl
SPEC_ID: <spec id>
DOWNSTREAM_TASK_IDS: <comma-separated list from step 4>
DRY_RUN: <true|false>
CROSS_SPEC: <the $CROSS_SPEC value read below — literal "true" or "false", NOT "true|false">

GLOSSARY_JSON: <output of `flowctl glossary list --json` from step 5>
DECISIONS_JSON: <output of `flowctl memory list --track knowledge --category decisions --json` from step 5>
STRATEGY_CONTENT: <output of `flowctl strategy read --json` from step 5>

<if DRY_RUN is true>
DRY RUN MODE: Report what would change but do NOT use Edit tool. Only analyze and report drift.
</if>
```

Use Task tool with `subagent_type: flow-next:plan-sync` (sync-codex.sh rewrites `Task` to `spawn_agent` for the Codex mirror).

**Note:** `COMPLETED_TASK_ID` is always provided - for task-mode it's the input task, for spec-mode it's the source task selected in Step 4.

#### Done when

- `CROSS_SPEC` was read from `planSync.crossSpec` and passed to the agent as the literal string `true` or `false`.
- **The downstream task-spec edits are made by the spawned `flow-next:plan-sync` agent.** A session that edits downstream task specs directly has broken this.
- Under `--dry-run` the agent is told to report drift without using Edit, and Step 7 closes with "No files modified."

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
| Unknown ID (does not resolve) | "Unknown ID. Use fn-N-slug (spec) / fn-N-slug.M (task), a tracker handle (wor-17), or legacy fn-N, fn-N-xxx." |
| Task not found | "Task <id> not found. Run `flowctl list` to see available." |
| Spec not found | "Spec <id> not found. Run `flowctl list` to see available." |
| No source (spec mode) | "No completed or in-progress tasks to sync from. Complete a task first." |
| No downstream | "No downstream tasks to sync (all done or none exist)." |

## Rules

- **Ignores config** - `planSync.enabled` setting is for auto-trigger only; manual always runs
- **Any source status** - source task can be todo, in_progress, done, or blocked
- **Includes blocked** - downstream set includes both `todo` and `blocked` tasks
- **Reuses agent** - spawns existing plan-sync agent, no duplication
