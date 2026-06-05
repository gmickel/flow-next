---
name: flow-next-deps
description: "Show spec dependency graph and execution order. Use when asking 'what's blocking what', 'execution order', 'dependency graph', 'what order should specs run', 'critical path', 'which specs can run in parallel'."
---

# Flow-Next Dependency Graph

Visualize spec dependencies, blocking chains, and execution phases.

## Preamble

flowctl is bundled with the plugin (not on PATH). Define once; subsequent blocks use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Setup

```bash
$FLOWCTL detect --json | jq -e '.exists' >/dev/null && echo "OK: .flow/ exists" || echo "ERROR: run $FLOWCTL init"
command -v jq >/dev/null 2>&1 && echo "OK: jq installed" || echo "ERROR: brew install jq"
```

## Step 1: Gather Spec Data

Build a consolidated view of all specs with their dependencies:

```bash
# Get all spec IDs
spec_ids=$($FLOWCTL specs --json | jq -r '.specs[].id')

# For each spec, get full details including dependencies
for id in $spec_ids; do
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

Determine which specs are ready vs blocked (pure jq, works on any shell):

```bash
# Collect all spec data with deps
specs_json=$($FLOWCTL specs --json | jq -r '.specs[].id' | while read id; do
  $FLOWCTL show "$id" --json | jq -c '{id: .id, title: .title, status: .status, deps: (.depends_on_epics // [])}'
done | jq -s '.')

# Compute blocking status
echo "$specs_json" | jq -r '
  # Build status lookup
  (map({(.id): .status}) | add // {}) as $status |

  # Check each non-done spec
  .[] | select(.status != "done") |
  .id as $id | .title as $title |

  # Find deps that are not done
  ([.deps[] | select($status[.] != "done")] | join(", ")) as $blocked_by |

  if ($blocked_by | length) == 0 then
    "READY: \($id) - \($title)"
  else
    "BLOCKED: \($id) - \($title) (by: \($blocked_by))"
  end
'
```

## Step 3: Compute Execution Phases

Group specs into parallel execution phases:

```bash
# Collect all spec data
specs_json=$($FLOWCTL specs --json | jq -r '.specs[].id' | while read id; do
  $FLOWCTL show "$id" --json | jq -c '{id: .id, title: .title, status: .status, deps: (.depends_on_epics // [])}'
done | jq -s '.')

# Phase assignment algorithm (run in jq for reliability)
echo "$specs_json" | jq '
  # Build status lookup
  (map({(.id): .status}) | add // {}) as $status |

  # Filter to non-done specs
  [.[] | select(.status != "done")] as $open |

  # Assign phases iteratively
  reduce range(10) as $phase (
    {assigned: [], result: [], open: $open};

    .assigned as $assigned |
    .open as $remaining |

    # Find specs not yet assigned whose deps are all done or in earlier phases
    ([.open[] | select(
      ([.id] | inside($assigned) | not) and
      ((.deps // []) | all(. as $d | $status[$d] == "done" or ($assigned | index($d))))
    )] | map(.id)) as $ready |

    if ($ready | length) > 0 then
      .result += [{phase: ($phase + 1), specs: [.open[] | select(.id | IN($ready[]))]}] |
      .assigned += $ready
    else . end
  ) |
  .result
'
```

## Output Format

Present results as:

```markdown
## Spec Dependency Graph

### Status Overview

| Spec | Title | Status | Dependencies | Blocked By |
|------|-------|--------|--------------|------------|
| **fn-1-add-auth** | Add Authentication | **READY** | - | - |
| fn-2-add-oauth | Add OAuth Login | blocked | fn-1-add-auth | fn-1-add-auth |
| fn-3-user-profile | User Profile Page | blocked | fn-1-add-auth, fn-2-add-oauth | fn-2-add-oauth |

### Execution Phases

| Phase | Specs | Can Start |
|-------|-------|-----------|
| **1** | fn-1-add-auth | **NOW** |
| 2 | fn-2-add-oauth | After Phase 1 |
| 3 | fn-3-user-profile | After Phase 2 |

### Critical Path

fn-1-add-auth → fn-2-add-oauth → fn-3-user-profile (3 phases)
```

## Quick One-Liner

For a fast dependency check:

```bash
$FLOWCTL specs --json | jq -r '.specs[] | select(.status != "done") | "\(.id): \(.title) [\(.status)]"'
```

## When to Use

- "What's the execution order for specs?"
- "What's blocking progress?"
- "Show me the dependency graph"
- "What's the critical path?"
- "Which specs can run in parallel?"
- "Why is Ralph working on X?"
- "What should I work on next?"
