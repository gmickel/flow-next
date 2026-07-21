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
FLOWCTL="$HOME/.codex/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Pre-check: Local setup version

Compare `.flow/meta.json` `setup_version` to the plugin version; on mismatch, escalate once per plugin version. Fail-open throughout: a missing `jq`, `.flow/meta.json`, or plugin manifest silently continues.

```bash
SETUP_MODE=$(jq -r '.setup_mode // empty' .flow/meta.json 2>/dev/null)
SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/.codex-plugin/plugin.json"
PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
VERSION_ACK=$(jq -r '.version_ack // empty' .flow/meta.json 2>/dev/null)
if [[ "$SETUP_MODE" == "plugin" ]]; then
 # fn-121 plugin mode: no local copies exist to go stale - the version compare is
 # moot. Check only the CLAUDE.md snippet contract (sentinel vs the plugin's
 # expected v1; keep the literal in sync with SNIPPET_SCHEMA_VERSION in flowctl.py).
 SNIP_ACK=$(jq -r '.snippet_ack // empty' .flow/meta.json 2>/dev/null)
 SNIP_VER=$(grep -m1 -o 'flow-next:snippet:v[0-9]*' CLAUDE.md 2>/dev/null | grep -o '[0-9]*$')
 if [[ "${SNIP_VER:-missing}" != "1" ]]; then
 if [[ "${FLOW_RALPH:-}" == "1" || -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_AUTONOMOUS:-}" == "1" || "${ARGUMENTS:-}" == *mode:autonomous* \
 || "$SNIP_ACK" == "1" ]]; then
 echo "CLAUDE.md flow-next snippet contract v${SNIP_VER:-missing} != plugin v1. Refresh via /flow-next:setup or the interactive ask." >&2
 else
 echo "FLOW_SNIPPET_ASK ${SNIP_VER:-missing} 1"
 fi
 fi
elif [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" && "$SETUP_VER" != "$PLUGIN_VER" ]]; then
 if [[ "${FLOW_RALPH:-}" == "1" || -n "${REVIEW_RECEIPT_PATH:-}" \
 || "${FLOW_AUTONOMOUS:-}" == "1" || "${ARGUMENTS:-}" == *mode:autonomous* \
 || "$VERSION_ACK" == "$PLUGIN_VER" ]]; then
 echo "Local setup v${SETUP_VER} differs from plugin v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts." >&2
 else
 echo "FLOW_SETUP_ASK ${SETUP_VER} ${PLUGIN_VER}"
 fi
fi
```

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

If the block printed a `FLOW_SNIPPET_ASK` line (plugin mode only; suppressed to the stderr note under the autonomy markers above), before proceeding ask the user with plain-text numbered prompt (the CLAUDE.md flow-next snippet block is on an older contract than this plugin version; refresh the marker block?), offering exactly the options **Refresh now**, **Remind me next version**, **Skip this run**, then continue the skill whichever is chosen:
- **Refresh now**: run `"$HOME/.codex/scripts/flowctl" setup-block apply --file CLAUDE.md --template "$HOME/.codex/skills/flow-next-setup/templates/claude-md-snippet-plugin.md" --json`; if it returns `action: ask`, re-run as `setup-block resolve` with the same `--file`/`--template` plus `--choice overwrite --json` - this question WAS the consent. Marker-bounded: content outside the block is never touched.
- **Remind me next version**: record the acknowledgement so this contract version is not re-asked (fail-open: on any error, continue anyway):
 ```bash
 rm -f .flow/meta.json.tmp && jq '.snippet_ack = "1"' .flow/meta.json > .flow/meta.json.tmp && mv .flow/meta.json.tmp .flow/meta.json
 ```
- **Skip this run**: continue without writing anything; the next invocation asks again.

If the block printed a `FLOW_SETUP_ASK` line, before proceeding ask the user with plain-text numbered prompt (local setup differs from the plugin; refresh now?), offering exactly the options **Refresh now**, **Remind me next version**, **Skip this run**, then continue the skill whichever is chosen:
- **Refresh now**: pause and have the user run `/flow-next:setup` in this session (do not run setup yourself), then continue once it finishes.
- **Remind me next version**: record the acknowledgement so this version is not re-asked (only a later plugin version re-arms it), then continue. Run this self-contained write (fail-open: on any error, continue anyway):
 ```bash
 PJ="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/.codex-plugin/plugin.json"
 PV=$(jq -r '.version' "$PJ" 2>/dev/null)
 [[ -n "$PV" && "$PV" != "null" ]] && rm -f .flow/meta.json.tmp && jq --arg v "$PV" '.version_ack = $v' .flow/meta.json > .flow/meta.json.tmp && mv .flow/meta.json.tmp .flow/meta.json
 ```
- **Skip this run**: continue without writing anything; the next invocation asks again.

Any other output (the one-line differs notice, or nothing) is non-blocking: continue.

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
- Do NOT gate on a hard "must start with `fn-`" check. Route the arg through `$FLOWCTL show <ID> --json` (Step 3) — flowctl's widened resolver (fn-52.10) maps a tracker key (`wor-17` / `wor-17.M`) to its linked spec/task, so a resolvable handle is the existing spec/task, never a new id. So `/flow-next:sync wor-17` resolves the linked spec.
- If no ID provided: "Usage: /flow-next:sync <id> [--dry-run]"
- If the arg does NOT resolve via `flowctl show` (Step 3): "Unknown ID. Use fn-N-slug (spec) / fn-N-slug.M (task), a tracker handle (wor-17), or legacy fn-N, fn-N-xxx."

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

Read the cross-spec flag first — the same single config-leaf read `/flow-next:work` performs, so a repo that opted into cross-spec propagation (`planSync.crossSpec=true`) gets the SAME behavior from a manual `/flow-next:sync` as from the work-loop auto-trigger. Without this, `CROSS_SPEC` is unset and plan-sync skips the cross-spec phase entirely — the tool you reach for AFTER big drift silently checks only same-spec tasks:

```bash
CROSS_SPEC=$($FLOWCTL config get planSync.crossSpec --json | jq -r '.value')
```

Build context and spawn via Task tool:

```
Sync task specs from <source> to downstream tasks.

COMPLETED_TASK_ID: <source task id - the input task, or selected source for spec mode>
FLOWCTL: $HOME/.codex/scripts/flowctl
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
