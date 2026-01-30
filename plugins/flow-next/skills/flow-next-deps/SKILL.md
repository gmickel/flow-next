---
name: flow-next-deps
description: "Show epic dependency graph and execution order. Use when asking 'what's blocking what', 'execution order', 'dependency graph', 'what order should epics run', 'critical path', 'which epics can run in parallel'."
---

# Flow-Next Dependency Graph

Visualize epic dependencies, blocking chains, and execution phases.

## Setup

```bash
FLOWCTL="${CLAUDE_PLUGIN_ROOT}/scripts/flowctl"
$FLOWCTL detect --json | jq -e '.exists' >/dev/null && echo "OK: .flow/ exists" || echo "ERROR: run $FLOWCTL init"
command -v jq >/dev/null 2>&1 && echo "OK: jq installed" || echo "ERROR: brew install jq"
```

## Step 1: Gather Epic Data

Build a consolidated view of all epics with their dependencies:

```bash
FLOWCTL="${CLAUDE_PLUGIN_ROOT}/scripts/flowctl"

# Get all epic IDs
epic_ids=$($FLOWCTL epics --json | jq -r '.epics[].id')

# For each epic, get full details including dependencies
for id in $epic_ids; do
  $FLOWCTL show "$id" --json | jq -c '{
    id: .id,
    title: .title,
    status: .status,
    plan_review: .plan_review_status,
    deps: (.depends_on_epics // [])
  }'
done
```

## Step 2: Identify Blocking Chains

Determine which epics are ready vs blocked:

```bash
FLOWCTL="${CLAUDE_PLUGIN_ROOT}/scripts/flowctl"

# Build status map first
declare -A status_map
for id in $($FLOWCTL epics --json | jq -r '.epics[].id'); do
  status_map[$id]=$($FLOWCTL show "$id" --json | jq -r '.status')
done

# Check each non-done epic
for id in $($FLOWCTL epics --json | jq -r '.epics[].id'); do
  epic_data=$($FLOWCTL show "$id" --json)
  status=$(echo "$epic_data" | jq -r '.status')
  [[ "$status" == "done" ]] && continue

  title=$(echo "$epic_data" | jq -r '.title')
  deps=$(echo "$epic_data" | jq -r '.depends_on_epics // [] | .[]')

  blocked_by=""
  for dep in $deps; do
    [[ "${status_map[$dep]}" != "done" ]] && blocked_by="$blocked_by $dep"
  done

  if [[ -z "$blocked_by" ]]; then
    echo "READY: $id - $title"
  else
    echo "BLOCKED: $id - $title (by:$blocked_by)"
  fi
done
```

## Step 3: Compute Execution Phases

Group epics into parallel execution phases:

```bash
FLOWCTL="${CLAUDE_PLUGIN_ROOT}/scripts/flowctl"

# Collect all epic data
epics_json=$($FLOWCTL epics --json | jq -r '.epics[].id' | while read id; do
  $FLOWCTL show "$id" --json | jq -c '{id: .id, title: .title, status: .status, deps: (.depends_on_epics // [])}'
done | jq -s '.')

# Phase assignment algorithm (run in jq for reliability)
echo "$epics_json" | jq '
  # Build status lookup
  (map({(.id): .status}) | add) as $status |

  # Filter to non-done epics
  [.[] | select(.status != "done")] |

  # Assign phases iteratively
  reduce range(10) as $phase (
    {assigned: {}, result: []};

    # Find epics whose deps are all done or assigned to earlier phases
    .assigned as $assigned |
    [.result[].epics[].id] as $prev_assigned |

    ([.[] | select(
      (.id | in($assigned) | not) and
      ((.deps // []) | all(. as $d | $status[$d] == "done" or ($prev_assigned | index($d))))
    )] | map(.id)) as $ready |

    if ($ready | length) > 0 then
      .result += [{phase: ($phase + 1), epics: [.[] | select(.id | IN($ready[]))]}] |
      .assigned += ($ready | map({(.): true}) | add)
    else . end
  ) |
  .result
'
```

## Output Format

Present results as:

```markdown
## Epic Dependency Graph

### Status Overview

| Epic | Title | Status | Dependencies | Blocked By |
|------|-------|--------|--------------|------------|
| **fn-1-abc** | Feature Alpha | **READY** | - | - |
| fn-2-def | Feature Beta | blocked | fn-1-abc | fn-1-abc |
| fn-3-ghi | Feature Gamma | blocked | fn-1-abc, fn-2-def | fn-2-def |

### Execution Phases

| Phase | Epics | Can Start |
|-------|-------|-----------|
| **1** | fn-1-abc | **NOW** |
| 2 | fn-2-def | After Phase 1 |
| 3 | fn-3-ghi | After Phase 2 |

### Critical Path

fn-1-abc → fn-2-def → fn-3-ghi (3 phases)
```

## Quick One-Liner

For a fast dependency check:

```bash
FLOWCTL="${CLAUDE_PLUGIN_ROOT}/scripts/flowctl"
$FLOWCTL epics --json | jq -r '.epics[] | select(.status != "done") | "\(.id): \(.title) [\(.status)]"'
```

## When to Use

- "What's the execution order for epics?"
- "What's blocking progress?"
- "Show me the dependency graph"
- "What's the critical path?"
- "Which epics can run in parallel?"
- "Why is Ralph working on X?"
- "What should I work on next?"
