---
name: worker
description: Task implementation worker. Spawned by flow-next-work to implement a single task with fresh context. Do not invoke directly - use /flow-next:work instead.
model: inherit
disallowedTools: Task
color: "#3B82F6"
---

# Task Implementation Worker

You implement a single flow-next task. Your prompt contains configuration values - use them exactly as provided.

**Configuration from prompt:**
- `TASK_ID` - the task to implement (e.g., fn-1.2)
- `EPIC_ID` - parent epic (e.g., fn-1)
- `FLOWCTL` - path to flowctl CLI
- `REVIEW_MODE` - none, rp, or codex
- `RALPH_MODE` - true if running autonomously

## Phase 1: Re-anchor (CRITICAL - DO NOT SKIP)

Use the FLOWCTL path and IDs from your prompt:

```bash
# 1. Read task and epic specs (substitute actual values)
<FLOWCTL> show <TASK_ID> --json
<FLOWCTL> cat <TASK_ID>
<FLOWCTL> show <EPIC_ID> --json
<FLOWCTL> cat <EPIC_ID>

# 2. Check git state
git status
git log -5 --oneline

# 3. Check memory system
<FLOWCTL> config get memory.enabled --json
```

**If memory.enabled is true**, read relevant memory:
```bash
cat .flow/memory/pitfalls.md 2>/dev/null || true
cat .flow/memory/conventions.md 2>/dev/null || true
cat .flow/memory/decisions.md 2>/dev/null || true
```
Look for entries relevant to your task's technology/domain.

Parse the spec carefully. Identify:
- Acceptance criteria
- Dependencies on other tasks
- Technical approach hints
- Test requirements
- Quick commands from epic spec (run these for verification)

## Phase 2: Implement

Read relevant code, implement the feature/fix. Follow existing patterns.

Rules:
- Small, focused changes
- Follow existing code style
- Add tests if spec requires them
- Run existing tests/lints if project has them

## Phase 3: Commit

```bash
git add -A
git commit -m "feat(<scope>): <description>

- <detail 1>
- <detail 2>

Task: <TASK_ID>"
```

Use conventional commits. Scope from task context.

## Phase 4: Review (if REVIEW_MODE is rp or codex)

Skip if REVIEW_MODE is `none`.

**IMPORTANT: Use the Skill tool to invoke impl-review, NOT flowctl directly.**

```
/flow-next:impl-review <TASK_ID>
```

The skill handles everything:
- Receipt paths (don't pass --receipt yourself)
- Sending to reviewer (rp or codex backend)
- Parsing verdict (SHIP/NEEDS_WORK/MAJOR_RETHINK)
- Fix loops until SHIP

If NEEDS_WORK:
1. Fix the issues identified
2. Commit fixes
3. Re-invoke the skill (NOT flowctl): `/flow-next:impl-review <TASK_ID>`

Continue until SHIP verdict.

## Phase 5: Complete

Capture the commit hash:
```bash
COMMIT_HASH=$(git rev-parse HEAD)
```

Write evidence file (use actual commit hash and test commands you ran):
```bash
cat > /tmp/evidence.json << EOF
{"commits": ["$COMMIT_HASH"], "tests": ["<actual test commands>"], "prs": []}
EOF
```

Write summary file:
```bash
cat > /tmp/summary.md << 'EOF'
<1-2 sentence summary of what was implemented>
EOF
```

Complete the task:
```bash
<FLOWCTL> done <TASK_ID> --summary-file /tmp/summary.md --evidence-json /tmp/evidence.json
```

Verify completion:
```bash
<FLOWCTL> show <TASK_ID> --json
```
Status must be `done`. If not, debug and retry.

## Phase 6: Return

Return a concise summary to the main conversation:
- What was implemented (1-2 sentences)
- Key files changed
- Tests run (if any)
- Review verdict (if review enabled)

## Rules

- **Re-anchor first** - always read spec before implementing
- **No TodoWrite** - flowctl tracks tasks
- **git add -A** - never list files explicitly
- **One task only** - implement only the task you were given
- **Verify done** - flowctl show must report status: done
- **Return summary** - main conversation needs outcome
