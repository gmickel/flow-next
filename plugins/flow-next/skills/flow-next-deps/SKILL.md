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

Build a consolidated view of all specs with their dependencies — ONE heavy per-spec loop for the whole skill. Steps 2 and 3 reuse the cached file (bash vars do not survive across tool calls, so the cache is a file at a literal agent-composed path — compose `<suffix>` once, e.g. 4 random chars, and reuse the SAME literal path in every later block):

```bash
# ONE gather — Steps 2 and 3 read this file; never re-run the per-spec loop
SPECS_FILE="${TMPDIR:-/tmp}/flow-deps-specs-<suffix>.json"
$FLOWCTL specs --json | jq -r '.specs[].id' | while read id; do
  $FLOWCTL show "$id" --json | jq -c '{
    id: .id,
    title: .title,
    status: .status,
    plan_review: .plan_review_status,
    deps: (.depends_on_epics // [])
  }'
done | jq -s '.' > "$SPECS_FILE"
cat "$SPECS_FILE"
```

## Step 2: Identify Blocking Chains

Determine which specs are ready vs blocked (pure jq, works on any shell):

```bash
# Reuse the Step 1 gather — same literal path, NO re-fetch (one heavy loop total)
SPECS_FILE="${TMPDIR:-/tmp}/flow-deps-specs-<suffix>.json"

# Compute blocking status
jq -r '
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
' "$SPECS_FILE"
```

## Step 3: Compute Execution Phases

Group specs into parallel execution phases:

```bash
# Reuse the Step 1 gather — same literal path, NO re-fetch (one heavy loop total)
SPECS_FILE="${TMPDIR:-/tmp}/flow-deps-specs-<suffix>.json"

# Phase assignment algorithm (run in jq for reliability)
jq '
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
  # Emit the phases AND the residue: any open spec never assigned is UNRESOLVABLE — a
  # dependency cycle (A→B→A), a dep on a missing/closed spec, or a chain deeper than 10.
  # Dropping it silently is the one way /deps gives a WRONG answer (the graph it exists to
  # expose hides the deadlock). Surface it, with the offending deps for diagnosis.
  .assigned as $asg |
  { phases: .result,
    deadlocked: [ $open[] | select(.id as $i | ($asg | index($i)) | not)
                  | { id, status,
                      unresolved_deps: [ (.deps // [])[] | select(. as $d | ($asg | index($d)) or ($status[$d] == "done") | not) ] } ] }
' "$SPECS_FILE"
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

Render from the jq result's `.phases`:

| Phase | Specs | Can Start |
|-------|-------|-----------|
| **1** | fn-1-add-auth | **NOW** |
| 2 | fn-2-add-oauth | After Phase 1 |
| 3 | fn-3-user-profile | After Phase 2 |

### ⚠️ Deadlocked / Unresolvable

**Only render this section when `.deadlocked` is non-empty** — but when it is, it is the
most important part of the report. Each entry is an OPEN spec that could not be placed in
any phase: a dependency **cycle**, a dep on a **missing/closed** spec, or a chain deeper
than 10. These are invisible to `ready`/pilot (they just never become ready) — this is the
one place the graph surfaces them.

| Spec | Status | Unresolved deps | Likely cause |
|------|--------|-----------------|--------------|
| fn-7-x | blocked | fn-9-y | fn-9-y not found / closed, or a cycle fn-7↔fn-9 |

For each, state the likely cause: if two deadlocked specs list each other → **cycle** (fix
with `flowctl spec rm-dep`); if an unresolved dep isn't among the open specs → **missing or
closed dependency**. Never omit a deadlocked spec.

### Critical Path

fn-1-add-auth → fn-2-add-oauth → fn-3-user-profile (3 phases)
```

**Edit dependencies** with `flowctl spec add-dep <spec> <dep>` / `rm-dep <spec> <dep>`
(this skill is read-only inspection; those commands mutate the edges).

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
