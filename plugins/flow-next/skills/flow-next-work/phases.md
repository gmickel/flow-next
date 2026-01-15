# Flow Work Phases

(Branch question already asked in SKILL.md before reading this file)

**CRITICAL**: If you are about to create:
- a markdown TODO list,
- a task list outside `.flow/`,
- or any plan files outside `.flow/`,

**STOP** and instead:
- create/update tasks in `.flow/` using `flowctl`,
- record details in the epic/task spec markdown.

## Setup

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:

```bash
FLOWCTL="${CLAUDE_PLUGIN_ROOT}/scripts/flowctl"
```

## Phase 1: Resolve Input

Detect input type in this order (first match wins):

1. **Flow task ID** `fn-N.M` (e.g., fn-1.3)
2. **Flow epic ID** `fn-N` (e.g., fn-1)
3. **Spec file** `.md` path that exists on disk
4. **Idea text** everything else

---

**Flow task ID (fn-N.M)**:
- Read task: `$FLOWCTL show <id> --json`
- Read spec: `$FLOWCTL cat <id>`
- Get epic from task data for context: `$FLOWCTL show <epic-id> --json && $FLOWCTL cat <epic-id>`

**Flow epic ID (fn-N)**:
- Read epic: `$FLOWCTL show <id> --json`
- Read spec: `$FLOWCTL cat <id>`
- Get first ready task: `$FLOWCTL ready --epic <id> --json`

**Spec file start (.md path that exists)**:
1. Check file exists: `test -f "<path>"` — if not, treat as idea text
2. Initialize: `$FLOWCTL init --json`
3. Read file and extract title from first `# Heading` or use filename
4. Create epic: `$FLOWCTL epic create --title "<extracted-title>" --json`
5. Set spec from file: `$FLOWCTL epic set-plan <epic-id> --file <path> --json`
6. Create single task: `$FLOWCTL task create --epic <epic-id> --title "Implement <title>" --json`
7. Continue with epic-id

**Spec-less start (idea text)**:
1. Initialize: `$FLOWCTL init --json`
2. Create epic: `$FLOWCTL epic create --title "<idea>" --json`
3. Create single task: `$FLOWCTL task create --epic <epic-id> --title "Implement <idea>" --json`
4. Continue with epic-id

## Phase 2: Apply Branch Choice

Based on user's answer from setup questions:

- **Worktree**: use `skill: flow-next-worktree-kit`
- **New branch**:
  ```bash
  git checkout main && git pull origin main
  git checkout -b <branch>
  ```
- **Current branch**: proceed (user already confirmed)

## Phase 3: Task Loop

**For each task**, spawn a worker subagent with fresh context.

### 3a. Find Next Task

```bash
$FLOWCTL ready --epic <epic-id> --json
```

If no ready tasks, go to Phase 4 (Quality).

### 3b. Start Task

```bash
$FLOWCTL start <task-id> --json
```

### 3c. Spawn Worker

Use the Task tool to spawn a `worker` subagent. The worker gets fresh context and handles:
- Re-anchoring (reading spec, git status)
- Implementation
- Committing
- Review cycles (if enabled)
- Completing the task (flowctl done)

**Prompt template for worker:**

Pass config values only. Worker reads worker.md for phases. Do NOT paraphrase or add step-by-step instructions - worker.md has them.

```
Implement flow-next task.

TASK_ID: fn-X.Y
EPIC_ID: fn-X
FLOWCTL: /path/to/flowctl
REVIEW_MODE: none|rp|codex
RALPH_MODE: true|false

Follow your phases in worker.md exactly.
```

**Worker returns**: Summary of implementation, files changed, test results, review verdict.

### 3d. Verify Completion

After worker returns, verify the task completed:

```bash
$FLOWCTL show <task-id> --json
```

If status is not `done`, the worker failed. Check output and retry or investigate.

### 3e. Loop

Return to 3a for next task.

---

**Why spawn a worker?**

Context optimization. Each task gets fresh context:
- No bleed from previous task implementations
- Re-anchor info stays with implementation (not lost to compaction)
- Review cycles stay isolated
- Main conversation stays lean (just summaries)

**Ralph mode**: Worker inherits `bypassPermissions` from parent. FLOW_RALPH=1 and REVIEW_RECEIPT_PATH are passed through.

**Interactive mode**: Permission prompts pass through to user. Worker runs in foreground (blocking).

## Phase 4: Quality

After all tasks complete (or periodically for large epics):

- Run relevant tests
- Run lint/format per repo
- If change is large/risky, run the quality auditor subagent:
  - Task flow-next:quality-auditor("Review recent changes")
- Fix critical issues

## Phase 5: Ship

**Verify all tasks done**:
```bash
$FLOWCTL show <epic-id> --json
$FLOWCTL validate --epic <epic-id> --json
```

**Final commit** (if any uncommitted changes):
```bash
git add -A
git status
git diff --staged
git commit -m "<final summary>"
```

**Do NOT close the epic here** unless the user explicitly asked.
Ralph closes done epics at the end of the loop.

Then push + open PR if user wants.

## Definition of Done

Confirm before ship:
- All tasks have status "done"
- `$FLOWCTL validate --epic <id>` passes
- Tests pass
- Lint/format pass
- Docs updated if needed
- Working tree is clean

## Example loop

```
Phase 1 (resolve) → Phase 2 (branch) → Phase 3 loop:
  ├─ find task → start → spawn worker → verify → repeat
  └─ no more tasks → Phase 4 (quality) → Phase 5 (ship)
```
