---
name: flow-next-deps
description: "Show epic dependency graph and execution order. Use when asking 'what's blocking what', 'execution order', 'dependency graph', 'what order should epics run', 'critical path'."
---

# Flow-Next Dependency Graph

Shows epic dependencies, blocking chains, and execution order phases.


## Step 1: Get all epic dependencies and status

```bash
for epic in $(ls .flow/epics/fn-*.json | xargs -I{} basename {} .json); do
  deps=$(jq -c '.depends_on_epics // []' ".flow/epics/${epic}.json" 2>/dev/null)
  status=$(jq -r '.status' ".flow/epics/${epic}.json" 2>/dev/null)
  title=$(jq -r '.title' ".flow/epics/${epic}.json" 2>/dev/null)
  plan_review=$(jq -r '.plan_review_status' ".flow/epics/${epic}.json" 2>/dev/null)
  echo "$epic|$status|$plan_review|$deps|$title"
done
```

## Step 2: Identify blocking chains

For each open epic, check if its dependencies are done:

```bash
for epic in $(ls .flow/epics/fn-*.json | xargs -I{} basename {} .json); do
  status=$(jq -r '.status' ".flow/epics/${epic}.json" 2>/dev/null)
  [[ "$status" == "done" ]] && continue

  title=$(jq -r '.title' ".flow/epics/${epic}.json" 2>/dev/null)
  deps=$(jq -r '.depends_on_epics // [] | .[]' ".flow/epics/${epic}.json" 2>/dev/null)

  blocked_by=""
  for dep in $deps; do
    dep_status=$(jq -r '.status' ".flow/epics/${dep}.json" 2>/dev/null)
    [[ "$dep_status" != "done" ]] && blocked_by="$blocked_by $dep"
  done

  if [[ -z "$blocked_by" ]]; then
    echo "READY: $epic - $title"
  else
    echo "BLOCKED: $epic - $title (by:$blocked_by)"
  fi
done
```

## Step 3: Build execution order table

Present results as a table with descriptions:

| Epic | Description | Blocked By | Status |
|------|-------------|------------|--------|
| **fn-41-9xt** | Silent by Default CLI Output | - | **READY** |
| fn-31-gib | Import Reliability & Testing | fn-41-9xt | blocked |
| fn-33-lp4 | User Templates & Customization | fn-31-gib, fn-41-9xt | blocked |

## Step 4: Compute execution phases

Group epics into phases where each phase can run in parallel:

1. **Phase 1**: Epics with all deps done (READY now)
2. **Phase 2**: Epics unblocked after Phase 1 completes
3. **Phase 3**: Epics unblocked after Phase 2 completes
4. etc.

## Output Format

Present as:

```
## Epic Dependency Graph with Descriptions

### Blocking Chain Table

| Epic | Description | Blocked By | Status |
|------|-------------|------------|--------|
| **fn-41-9xt** | Silent by Default CLI Output | fn-36-rb7 ✓ | **READY** |
| fn-31-gib | Import Reliability & Comprehensive Testing | fn-36 ✓, **fn-41** | blocked |

### Execution Order

| Phase | Epics | Description |
|-------|-------|-------------|
| **1** | **fn-41-9xt** | Silent by Default CLI Output ← **NOW** |
| **2** | fn-13-1c7, fn-31-gib | Devcontainer Research + Import Reliability |
| **3** | fn-33-lp4 | User Templates & Customization |
```

## When to Use

- "What's the execution order for epics?"
- "What's blocking progress?"
- "Show me the dependency graph"
- "What's the critical path?"
- "Which epics can run in parallel?"
- "Why is Ralph working on X?"
