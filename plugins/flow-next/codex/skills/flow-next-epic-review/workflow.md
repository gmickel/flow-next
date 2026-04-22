# Epic Completion Review Workflow

---

## CRITICAL: RepoPrompt Commands Are SLOW - DO NOT RETRY

**READ THIS BEFORE RUNNING ANY COMMANDS:**

1. **`setup-review` takes 5-15 MINUTES** - It runs the RepoPrompt context builder which indexes files. This is NORMAL. Do NOT assume it is stuck.

2. **`chat-send` takes 2-10 MINUTES** - It waits for the LLM to generate a full review. This is NORMAL. Do NOT assume it is stuck.

3. **Run commands directly and WAIT** - Do NOT use background jobs. Just run the command and wait:
   ```bash
   # Run setup-review - takes 5-15 minutes, just wait
   $FLOWCTL rp setup-review --repo-root "$REPO_ROOT" --summary "..."
   # You will see file paths printed as it indexes - this is progress, not errors
   ```

4. **Output is progress, not errors** - The context builder prints file paths as it indexes. Seeing many lines of output is NORMAL. Do not interpret this as an error loop.

5. **NEVER retry these commands** - If you run them again, you will create duplicate reviews and waste time. Run ONCE and WAIT.

6. **Exit code 0 = success** - When the command finishes, check the exit code. If it is 0, it worked.

**If a command has been running for less than 15 minutes, WAIT. Do not retry. Do not output <promise>RETRY</promise>.**

---


## Philosophy

Epic completion review verifies spec compliance, NOT code quality. impl-review handles code quality per-task. This review catches:
- Requirements that never became tasks (decomposition gaps)
- Requirements partially implemented across tasks (cross-task gaps)
- Scope drift (task marked done without fully addressing spec intent)
- Missing doc updates

---

## Phase 0: Backend Detection

**Run this first. Do not skip.**

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:

```bash
set -e
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Priority: --review flag > env > config (flag parsed in SKILL.md)
BACKEND=$($FLOWCTL review-backend)

if [[ "$BACKEND" == "ASK" ]]; then
  echo "Error: No review backend configured."
  echo "Run /flow-next:setup to configure, or pass --review=rp|codex|copilot|none"
  exit 1
fi

echo "Review backend: $BACKEND"
```

**If backend is "none"**: Skip review, inform user, and exit cleanly (no error).

**Then branch to backend-specific workflow below.**

---

## Codex Backend Workflow

Use when `BACKEND="codex"`.

### Step 1: Identify Epic

```bash
# EPIC_ID from arguments (e.g., fn-1, fn-22-53k)
$FLOWCTL show "$EPIC_ID" --json
```

### Step 2: Execute Review

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/completion-review-receipt.json}"

$FLOWCTL codex completion-review "$EPIC_ID" --receipt "$RECEIPT_PATH"
```

**Output includes `VERDICT=SHIP|NEEDS_WORK`.**

### Step 3: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from output
2. Fix code and run tests
3. Commit fixes
4. Re-run step 2 (receipt enables session continuity)
5. Repeat until SHIP

### Step 4: Receipt

Receipt is written automatically by `flowctl codex completion-review` when `--receipt` provided.
Format: `{"type":"completion_review","id":"<epic-id>","mode":"codex","verdict":"<verdict>","session_id":"<thread_id>","timestamp":"..."}`

---

## Copilot Backend Workflow

Use when `BACKEND="copilot"`.

### Step 1: Identify Epic

```bash
# EPIC_ID from arguments (e.g., fn-1, fn-22-53k)
$FLOWCTL show "$EPIC_ID" --json
```

### Step 2: Execute Review

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/completion-review-receipt.json}"

# Runtime config via env vars (no CLI flags for model/effort):
#   FLOW_COPILOT_MODEL   (default gpt-5.2)
#   FLOW_COPILOT_EFFORT  (default high)

$FLOWCTL copilot completion-review "$EPIC_ID" --receipt "$RECEIPT_PATH"
```

**Output includes `VERDICT=SHIP|NEEDS_WORK`.**

### Step 3: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from output
2. Fix code and run tests
3. Commit fixes
4. Re-run step 2 (receipt enables session continuity when `mode == "copilot"`)
5. Repeat until SHIP

### Step 4: Receipt

Receipt is written automatically by `flowctl copilot completion-review` when `--receipt` provided.
Format: `{"type":"completion_review","id":"<epic-id>","mode":"copilot","verdict":"<verdict>","session_id":"<uuid>","model":"<model>","effort":"<effort>","timestamp":"..."}`

Session resume guard: re-review only resumes the copilot session when the existing receipt at `$RECEIPT_PATH` has `mode == "copilot"`. Cross-backend switches start a fresh session.

---

## RepoPrompt Backend Workflow

Use when `BACKEND="rp"`.

## Phase 1: Gather Context (RP)

**Run this BEFORE setup-review so the builder gets a real summary.**

```bash
BRANCH="$(git branch --show-current)"

# Get epic spec and task list
EPIC_SPEC="$($FLOWCTL cat "$EPIC_ID")"
TASKS_JSON="$($FLOWCTL tasks --epic "$EPIC_ID" --json)"

# Get changed files on branch
DIFF_BASE="main"
git rev-parse main >/dev/null 2>&1 || DIFF_BASE="master"
git log ${DIFF_BASE}..HEAD --oneline
CHANGED_FILES="$(git diff ${DIFF_BASE}..HEAD --name-only)"
git diff ${DIFF_BASE}..HEAD --stat
```

Save:
- Epic ID and spec
- Task list (IDs and titles)
- Branch name
- Changed files list

Compose a 1-2 sentence `REVIEW_SUMMARY` for the setup-review command below.

---

### Atomic Setup Block

**Only run ONCE. Uses the summary composed in Phase 1.**

```bash
# Atomic: pick-window + builder (uses REVIEW_SUMMARY from Phase 1)
eval "$($FLOWCTL rp setup-review --repo-root "$REPO_ROOT" --summary "$REVIEW_SUMMARY" --create)"

# Verify we have W and T
if [[ -z "${W:-}" || -z "${T:-}" ]]; then
  echo "<promise>RETRY</promise>"
  exit 0
fi

echo "Setup complete: W=$W T=$T"
```

If this block fails, output `<promise>RETRY</promise>` and stop. Do not improvise.
**Do NOT re-run setup-review** — the builder runs inside it. Re-running = double context build.

---

## Phase 2: Augment Selection (RP)

Builder selects context automatically. Review and add must-haves:

```bash
# See what builder selected
$FLOWCTL rp select-get --window "$W" --tab "$T"

# Add epic spec
$FLOWCTL rp select-add --window "$W" --tab "$T" ".flow/specs/$EPIC_ID.md"

# Add all task specs
for task_id in $(echo "$TASKS_JSON" | jq -r '.[].id'); do
  $FLOWCTL rp select-add --window "$W" --tab "$T" ".flow/tasks/$task_id.md"
done

# Add ALL changed files
for f in $CHANGED_FILES; do
  $FLOWCTL rp select-add --window "$W" --tab "$T" "$f"
done
```

**Why this matters:** Chat only sees selected files.

---

## Phase 3: Execute Review (RP)

### Build combined prompt

Get builder's handoff:
```bash
HANDOFF="$($FLOWCTL rp prompt-get --window "$W" --tab "$T")"
```

Write combined prompt:
```bash
cat > /tmp/completion-review-prompt.md << 'EOF'
[PASTE HANDOFF HERE]

---

## IMPORTANT: File Contents
RepoPrompt includes the actual source code of selected files in a `<file_contents>` XML section at the end of this message. You MUST:
1. Locate the `<file_contents>` section
2. Read and analyze the actual source code within it
3. Base your review on the code, not summaries or descriptions

If you cannot find `<file_contents>`, ask for the files to be re-attached before proceeding.

## Epic Under Review
Epic: [EPIC_ID]
Branch: [BRANCH_NAME]
Tasks: [LIST TASK IDs]

## Epic Spec
[PASTE EPIC SPEC]

## Review Focus: Spec Compliance

This is NOT a code quality review — impl-review handles that per-task.

Your job: Verify the combined implementation delivers everything the spec requires.

### Three-Phase Approach

**Phase 1: Extract Requirements**
Read the epic spec and list ALL explicit requirements as bullets:
- Features/functionality to implement
- Docs to update (README, API docs, etc.)
- Tests to add
- Config/schema changes
- Any other deliverables

**Phase 2: Verify Implementation**
For each requirement from Phase 1:
- [ ] Is it implemented in the changed files?
- [ ] Is the implementation complete (not partial)?
- [ ] Does it match the spec intent?

**Phase 3: Reverse Coverage (Code → Spec)**
For each new/modified file in the changed files list:
- Identify which epic requirement it serves
- Flag any file that doesn't trace to a spec requirement

If the epic spec has a `## Requirement coverage` traceability table, use it as the primary reference for mapping files to requirements.

Classification for untraced changes:
- `UNDOCUMENTED_ADDITION` — new functionality not in spec (scope creep)
- `LEGITIMATE_SUPPORT` — refactoring/infrastructure needed to implement a requirement (OK)
- `UNRELATED_CHANGE` — changes outside epic scope (may be accidental)

Report untraced changes but don't auto-reject. UNDOCUMENTED_ADDITION is a flag for acknowledgment, not automatic NEEDS_WORK.

### What to Check
- Requirements that never became tasks (decomposition gaps)
- Requirements partially implemented across tasks (cross-task gaps)
- Scope drift (task marked done without fully addressing spec intent)
- Missing doc updates specified in acceptance criteria
- Scope creep (code changes that don't trace to spec requirements)

### What NOT to Check
- Code style, patterns, architecture (impl-review covers this)
- Test quality (impl-review covers this)
- Performance (impl-review covers this)
- Legitimate refactoring needed to implement requirements (flag as LEGITIMATE_SUPPORT but don't block)

## Output Format

**Forward coverage (Spec → Code):**
For each gap found:
- **Requirement**: What the spec says
- **Status**: Missing / Partial / Wrong
- **Evidence**: What you found (or didn't find) in the code

**Reverse coverage (Code → Spec):**
For each untraced change:
- **File**: Changed file path
- **Classification**: UNDOCUMENTED_ADDITION / LEGITIMATE_SUPPORT / UNRELATED_CHANGE
- **Note**: Brief explanation

**REQUIRED**: You MUST end your response with exactly one verdict tag. This is mandatory:
`<verdict>SHIP</verdict>` or `<verdict>NEEDS_WORK</verdict>`

- SHIP: All spec requirements are implemented
- NEEDS_WORK: One or more requirements are missing, partial, or wrong

Do NOT skip this tag. The automation depends on it.
EOF
```

**Note:** Replace bracket placeholders (`[EPIC_ID]`, `[BRANCH_NAME]`, etc.) with actual values before sending.

### Send to RepoPrompt and Parse Verdict

```bash
# Send review and capture response
REVIEW_RESPONSE="$($FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file /tmp/completion-review-prompt.md --new-chat --chat-name "Epic Review: $EPIC_ID")"
echo "$REVIEW_RESPONSE"

# Extract verdict tag from response
VERDICT="$(echo "$REVIEW_RESPONSE" \
  | tr -d '\r' \
  | grep -oE '<verdict>(SHIP|NEEDS_WORK)</verdict>' \
  | tail -n 1 \
  | sed -E 's#</?verdict>##g')"

if [[ -z "$VERDICT" ]]; then
  echo "No verdict tag found in response"
  echo "<promise>RETRY</promise>"
  exit 0
fi

echo "VERDICT=$VERDICT"
```

**WAIT** for response. Takes 1-5+ minutes.

---

## Phase 4: Receipt + Status (RP)

### Write receipt (if REVIEW_RECEIPT_PATH set)

Receipt written after SHIP verdict (not on NEEDS_WORK):

```bash
if [[ -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  mkdir -p "$(dirname "$REVIEW_RECEIPT_PATH")"
  cat > "$REVIEW_RECEIPT_PATH" <<EOF
{"type":"completion_review","id":"$EPIC_ID","mode":"rp","verdict":"SHIP","timestamp":"$ts"}
EOF
  echo "REVIEW_RECEIPT_WRITTEN: $REVIEW_RECEIPT_PATH"
fi
```

---

## Fix Loop (RP)

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is complete spec compliance. Never use AskUserQuestion in this loop.**

**CRITICAL: You MUST fix the code BEFORE re-reviewing. Never re-review without making changes.**

**MAX ITERATIONS**: Limit fix+re-review cycles to **${MAX_REVIEW_ITERATIONS:-3}** iterations (default 3, configurable in Ralph's config.env). If still NEEDS_WORK after max rounds, output `<promise>RETRY</promise>` and stop — let the next Ralph iteration start fresh.

If verdict is NEEDS_WORK:

1. **Parse issues** - Extract ALL gaps (missing requirements, partial implementations)
2. **Fix the code** - Implement missing functionality
3. **Run tests/lints** - Verify fixes don't break anything
4. **Commit fixes** (MANDATORY before re-review):
   ```bash
   git add -A
   git commit -m "fix: address completion review gaps"
   ```
   **If you skip this and re-review without committing changes, reviewer will return NEEDS_WORK again.**

5. **Request re-review** (only AFTER step 4):

   **IMPORTANT**: Do NOT re-add files already in the selection. RepoPrompt auto-refreshes
   file contents on every message. Only use `select-add` for NEW files created during fixes:
   ```bash
   # Only if fixes created new files not in original selection
   if [[ -n "$NEW_FILES" ]]; then
     $FLOWCTL rp select-add --window "$W" --tab "$T" $NEW_FILES
   fi
   ```

   Then send re-review request (NO --new-chat, stay in same chat).

   **CRITICAL: Do NOT summarize fixes.** RP auto-refreshes file contents - reviewer sees your changes automatically. Just request re-review. Any summary wastes tokens and duplicates what reviewer already sees.

   ```bash
   cat > /tmp/re-review.md << 'EOF'
   Gaps addressed. Please re-review for spec compliance.

   **REQUIRED**: End with `<verdict>SHIP</verdict>` or `<verdict>NEEDS_WORK</verdict>`
   EOF

   $FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file /tmp/re-review.md
   ```
6. **Repeat** until SHIP

**Anti-pattern**: Re-adding already-selected files before re-review. RP auto-refreshes; re-adding can cause issues.

---

## Anti-patterns

**All backends:**
- **Reviewing yourself** - You coordinate; the backend reviews
- **No receipt** - If REVIEW_RECEIPT_PATH is set, you MUST write receipt
- **Ignoring verdict** - Must extract and act on verdict tag
- **Mixing backends** - Stick to one backend for the entire review session
- **Checking code quality** - That's impl-review's job; focus on spec compliance

**RP backend only:**
- **Calling builder directly** - Must use `setup-review` which wraps it
- **Skipping setup-review** - Window selection MUST happen via this command
- **Hard-coding window IDs** - Never write `--window 1`
- **Missing task specs** - Add ALL task specs to selection

**Codex backend only:**
- **Using `--last` flag** - Conflicts with parallel usage; use `--receipt` instead
- **Direct codex calls** - Must use `flowctl codex` wrappers

**Copilot backend only:**
- **Direct copilot calls** - Must use `flowctl copilot` wrappers
- **Inventing `--model`/`--effort` CLI flags** - Those are env-only (`FLOW_COPILOT_MODEL`, `FLOW_COPILOT_EFFORT`)
- **Using `--continue`** - Conflicts with parallel usage; session resume uses `--resume=<uuid>` under the hood via `--receipt`
- **Assuming cross-backend session continuity** - Resume only works when prior receipt has `mode == "copilot"`
