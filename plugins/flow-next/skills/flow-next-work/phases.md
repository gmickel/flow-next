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

## Phase 3: Prime / Re-anchor Context (EVERY task)

**MANDATORY: This phase runs before EVERY task. No exceptions. No optimizations.**

Per Anthropic's long-running agent guidance: agents must re-anchor from sources of truth to prevent drift. Even if you "remember" the context, re-read it. The reads are cheap; drift is expensive.

**Also run this phase after context compaction** (if you notice the conversation was summarized).

### Re-anchor Checklist (run ALL before each task)

**You MUST run every command below. Do not skip or combine.**

```bash
# 1. Find next task
$FLOWCTL ready --epic <epic-id> --json

# 2. Re-read epic (EVERY time)
$FLOWCTL show <epic-id> --json
$FLOWCTL cat <epic-id>

# 3. Re-read task spec (EVERY time)
$FLOWCTL show <task-id> --json
$FLOWCTL cat <task-id>

# 4. Check git state (EVERY time)
git status
git log -5 --oneline

# 5. Validate structure (EVERY time)
$FLOWCTL validate --epic <epic-id> --json

# 6. Check memory (if enabled)
$FLOWCTL config get memory.enabled --json
```

**If memory.enabled is true**, also run:
- Task flow-next:memory-scout(<task-id>: <task-title>)

This retrieves relevant project learnings before implementation.

If no ready tasks after step 1, all done → go to Phase 6.

After step 5, run the smoke command from epic spec's "Quick commands" section.

**Why every time?** Context windows compress. You forget details. The spec is the truth. 30 seconds of re-reading prevents hours of rework.

**Anti-pattern**: Running steps 2-5 only on the first task. The whole point is EVERY task gets fresh context.

## Phase 4: Execute Task Loop

**For each task** (one at a time):

1. **Start task**:
   ```bash
   $FLOWCTL start <task-id> --json
   ```

2. **Implement + test thoroughly**:
   - Read task spec for requirements
   - Write code
   - Run tests (including epic spec "Quick commands")
   - Verify acceptance criteria
   - If any command fails, fix before proceeding

3. **If you discover new work**:
   - Draft new task title + acceptance checklist
   - Create immediately:
     ```bash
     # Write acceptance to temp file first
     $FLOWCTL task create --epic <epic-id> --title "Found: <issue>" --deps <current-task-id> --acceptance-file <temp-md> --json
     ```
   - Re-run `$FLOWCTL ready --epic <epic-id> --json` to see updated order

4. **Commit implementation** (code changes only):
   ```bash
   git add -A   # never list files; include .flow/ and scripts/ralph/ if present
   git status --short
   git commit -m "<type>: <short summary of what was done>"
   COMMIT_HASH="$(git rev-parse HEAD)"
   echo "Commit: $COMMIT_HASH"
   ```

5. **Complete task** (records done status + evidence):
   Write done summary to temp file (required format):
   ```
   - What changed (1-3 bullets)
   - Why (1-2 bullets)
   - Verification (tests/commands run)
   - Follow-ups (optional, max 2 bullets)
   ```

   Write evidence to temp JSON file **with the commit hash from step 4**:
   ```json
   {"commits":["<COMMIT_HASH>"],"tests":["npm test"],"prs":[]}
   ```

   Then:
   ```bash
   $FLOWCTL done <task-id> --summary-file <summary.md> --evidence-json <evidence.json> --json
   ```

   Verify the task is actually marked done:
   ```bash
   $FLOWCTL show <task-id> --json
   ```
   If status is not `done`, stop and re-run `flowctl done` before proceeding.

6. **Amend commit** to include .flow/ updates:
   ```bash
   git add -A
   git commit --amend --no-edit
   ```

7. **Verify task completion**:
   ```bash
   $FLOWCTL validate --epic <epic-id> --json
   git status
   ```
   Ensure working tree is clean.

8. **Loop**: Return to Phase 3 for next task.

## Phase 5: Quality

After all tasks complete (or periodically for large epics):

- Run relevant tests
- Run lint/format per repo
- If change is large/risky, run the quality auditor subagent:
  - Task flow-next:quality-auditor("Review recent changes")
- Fix critical issues

## Phase 6: Ship

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

## Phase 7: Review (if chosen at start)

If user chose "Yes" to review in setup questions or `--review=codex` / `--review=rp` was passed:

**CRITICAL: You MUST invoke the `/flow-next:impl-review` skill. Do NOT improvise your own review format.**

The impl-review skill:
- Auto-detects backend (Codex CLI or RepoPrompt) based on config/availability
- Uses the correct prompt template requiring `<verdict>SHIP|NEEDS_WORK|MAJOR_RETHINK</verdict>`
- Handles the fix loop internally

Steps:
1. Invoke `/flow-next:impl-review` (this loads the skill with its workflow.md)
2. If review returns NEEDS_WORK or MAJOR_RETHINK:
   - **Immediately fix the issues** (do NOT ask for confirmation — user already consented)
   - Commit fixes
   - Re-run tests/Quick commands
   - Re-run `/flow-next:impl-review`
3. Repeat until review returns SHIP

**Anti-pattern**: Sending your own review prompts directly without invoking the skill.
The skill has the correct format; improvised prompts ask for "LGTM" which breaks automation.

**No human gates here** — the review-fix-review loop is fully automated.

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
Prime → Task A → test → done → commit → Prime → Task B → ...
```
