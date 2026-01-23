# Implementation Review Workflow

## Philosophy

The reviewer model only sees selected files. RepoPrompt's Builder discovers context you'd miss (rp backend). Codex uses context hints from flowctl (codex backend).

---

## Phase 0: Backend Detection

**Run this first. Do not skip.**

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:

```bash
set -e
FLOWCTL="${CLAUDE_PLUGIN_ROOT}/scripts/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Priority: --review flag > env > config (flag parsed in SKILL.md)
BACKEND=$($FLOWCTL review-backend)

if [[ "$BACKEND" == "ASK" ]]; then
  echo "Error: No review backend configured."
  echo "Run /flow-next:setup to configure, or pass --review=rp|codex|mcp|none"
  exit 1
fi

echo "Review backend: $BACKEND (override: --review=rp|codex|mcp|none)"
```

**If backend is "none"**: Skip review, inform user, and exit cleanly (no error).

**Then branch to backend-specific workflow below.**

---

## Codex Backend Workflow

Use when `BACKEND="codex"`.

### Step 1: Identify Task and Diff Base

```bash
BRANCH="$(git branch --show-current)"

# Use BASE_COMMIT from arguments if provided (task-scoped review)
# Otherwise fall back to main/master (full branch review)
if [[ -z "$BASE_COMMIT" ]]; then
  DIFF_BASE="main"
  git rev-parse main >/dev/null 2>&1 || DIFF_BASE="master"
else
  DIFF_BASE="$BASE_COMMIT"
fi

git log ${DIFF_BASE}..HEAD --oneline
```

### Step 2: Execute Review

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt.json}"

$FLOWCTL codex impl-review "$TASK_ID" --base "$DIFF_BASE" --receipt "$RECEIPT_PATH"
```

**Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK`.**

### Step 3: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from output
2. Fix code and run tests
3. Commit fixes
4. Re-run step 2 (receipt enables session continuity)
5. Repeat until SHIP

### Step 4: Receipt

Receipt is written automatically by `flowctl codex impl-review` when `--receipt` provided.
Format: `{"mode":"codex","task":"<id>","verdict":"<verdict>","session_id":"<thread_id>","timestamp":"..."}`

---

## RepoPrompt Backend Workflow

Use when `BACKEND="rp"`.

**Requires RepoPrompt 1.6.0+** for the builder review mode. Check version with `rp-cli --version`.

### Phase 1: Identify Changes (RP)

```bash
BRANCH="$(git branch --show-current)"

# Use BASE_COMMIT from arguments if provided (task-scoped review)
# Otherwise fall back to main/master (full branch review)
if [[ -z "$BASE_COMMIT" ]]; then
  DIFF_BASE="main"
  git rev-parse main >/dev/null 2>&1 || DIFF_BASE="master"
else
  DIFF_BASE="$BASE_COMMIT"
fi

# Get commit info for instructions
COMMITS="$(git log ${DIFF_BASE}..HEAD --oneline)"
CHANGED_FILES="$(git diff ${DIFF_BASE}..HEAD --name-only)"
```

### Phase 2: Build Review Instructions (RP)

Build XML-structured instructions for the builder review mode:

```bash
cat > /tmp/review-instructions.txt << EOF
<task>Review changes from ${DIFF_BASE}..HEAD for correctness, simplicity, and potential issues.

Focus on:
- Correctness - Logic errors, spec compliance
- Simplicity - Over-engineering, unnecessary complexity
- Edge cases - Failure modes, boundary conditions
- Security - Injection, auth gaps

Only flag issues in the changed code - not pre-existing patterns.
</task>

<context>
Branch: $BRANCH
Commits:
$COMMITS

Changed files:
$CHANGED_FILES
$([ -n "$TASK_ID" ] && echo "Task: $TASK_ID")
$([ -n "$FOCUS_AREAS" ] && echo "Focus areas: $FOCUS_AREAS")
</context>

<discovery_agent-guidelines>
Focus on directories containing the changed files. Include git diffs for the commits.
</discovery_agent-guidelines>
EOF
```

### Phase 3: Execute Review (RP)

Use `setup-review` with `--response-type review` (RP 1.6.0+). The builder's discovery agent automatically:
- Selects relevant files and git diffs
- Analyzes code with full codebase context
- Returns structured review findings

```bash
# Run builder review mode
REVIEW_OUTPUT=$($FLOWCTL rp setup-review \
  --repo-root "$REPO_ROOT" \
  --summary "$(cat /tmp/review-instructions.txt)" \
  --response-type review \
  --json)

# Parse output
W=$(echo "$REVIEW_OUTPUT" | jq -r '.window')
T=$(echo "$REVIEW_OUTPUT" | jq -r '.tab')
CHAT_ID=$(echo "$REVIEW_OUTPUT" | jq -r '.chat_id')
REVIEW_FINDINGS=$(echo "$REVIEW_OUTPUT" | jq -r '.review')

if [[ -z "$W" || -z "$T" ]]; then
  echo "<promise>RETRY</promise>"
  exit 0
fi

echo "Setup complete: W=$W T=$T CHAT_ID=$CHAT_ID"
echo "Review findings:"
echo "$REVIEW_FINDINGS"
```

The builder returns review findings but **not a verdict tag**. Request verdict via follow-up:

```bash
cat > /tmp/verdict-request.md << 'EOF'
Based on your review findings above, provide your final verdict.

**REQUIRED**: End with exactly one verdict tag:
`<verdict>SHIP</verdict>` or `<verdict>NEEDS_WORK</verdict>` or `<verdict>MAJOR_RETHINK</verdict>`
EOF

$FLOWCTL rp chat-send --window "$W" --tab "$T" \
  --message-file /tmp/verdict-request.md \
  --chat-id "$CHAT_ID" \
  --mode review
```

**WAIT** for response. Extract verdict from response.

### Phase 4: Receipt + Status (RP)

```bash
if [[ -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  mkdir -p "$(dirname "$REVIEW_RECEIPT_PATH")"
  cat > "$REVIEW_RECEIPT_PATH" <<EOF
{"type":"impl_review","id":"$TASK_ID","mode":"rp","timestamp":"$ts","chat_id":"$CHAT_ID"}
EOF
  echo "REVIEW_RECEIPT_WRITTEN: $REVIEW_RECEIPT_PATH"
fi
```

If no verdict tag in response, output `<promise>RETRY</promise>` and stop.

---

## MCP Backend Workflow

Use when `BACKEND="mcp"`.

**Prerequisite**: RepoPrompt MCP server must be connected to Claude Code.

### Key Difference from RP Backend
- **RP backend**: Claude calls `flowctl rp *` → flowctl calls `rp-cli` subprocess
- **MCP backend**: Claude calls MCP tools directly (no subprocess, no rp-cli needed)

### MCP Tool Mapping

| flowctl rp command | MCP Tool |
|-------------------|----------|
| `rp setup-review` | `mcp__RepoPrompt__manage_workspaces` (list_tabs, select_tab) |
| `rp select-add` | `mcp__RepoPrompt__manage_selection` (op: "add") |
| `rp select-get` | `mcp__RepoPrompt__manage_selection` (op: "get") |
| `rp chat-send` | `mcp__RepoPrompt__chat_send` |
| `rp prompt-get` | `mcp__RepoPrompt__prompt` (op: "get") |
| `rp builder` | `mcp__RepoPrompt__context_builder` |

### Phase 0: Verify MCP Connection

Before proceeding, verify RepoPrompt MCP is available:
```
mcp__RepoPrompt__manage_workspaces with action="list"
```

If this fails, output error and suggest using `--review=codex` or `--review=none`.

### Phase 1: Identify Changes

Same as RP backend - identify branch, commits, and changed files:
```bash
BRANCH="$(git branch --show-current)"

if [[ -z "$BASE_COMMIT" ]]; then
  DIFF_BASE="main"
  git rev-parse main >/dev/null 2>&1 || DIFF_BASE="master"
else
  DIFF_BASE="$BASE_COMMIT"
fi

COMMITS="$(git log ${DIFF_BASE}..HEAD --oneline)"
CHANGED_FILES="$(git diff ${DIFF_BASE}..HEAD --name-only)"
```

### Phase 2: Setup Review Context

```
# Step 1: List available tabs
mcp__RepoPrompt__manage_workspaces
  action: "list_tabs"

# Step 2: Select/bind to a tab
mcp__RepoPrompt__manage_workspaces
  action: "select_tab"
  tab: "<tab_id or name>"
```

### Phase 3: Add Changed Files to Selection

```
mcp__RepoPrompt__manage_selection
  op: "add"
  paths: [<changed files from Phase 1>]
```

### Phase 4: Send Review Request (Single Call with Verdict)

Build review instructions that include the verdict requirement upfront, so both review AND verdict come back in one response:

```
# First review (new chat) - includes verdict requirement
mcp__RepoPrompt__chat_send
  new_chat: true
  mode: "review"
  chat_name: "Impl Review: [BRANCH]"
  git_scope: "selected"  # Include git diffs
  message: |
    Review the changes for correctness, simplicity, and potential issues.

    Focus on:
    - Correctness - Logic errors, spec compliance
    - Simplicity - Over-engineering, unnecessary complexity
    - Edge cases - Failure modes, boundary conditions
    - Security - Injection, auth gaps

    Only flag issues in the changed code - not pre-existing patterns.

    After your review, you MUST conclude with exactly one verdict tag:
    - `<verdict>SHIP</verdict>` - Code is ready to merge
    - `<verdict>NEEDS_WORK</verdict>` - Issues found that must be fixed
    - `<verdict>MAJOR_RETHINK</verdict>` - Fundamental problems require redesign

    The verdict tag is REQUIRED. Do not end your response without it.
```

### Phase 5: Parse Response

Parse for verdict in the response:
- `<verdict>SHIP</verdict>`
- `<verdict>NEEDS_WORK</verdict>`
- `<verdict>MAJOR_RETHINK</verdict>`

If no verdict tag found, the review is incomplete - request clarification in the same chat.

### Phase 6: Receipt + Status

Write receipt (if REVIEW_RECEIPT_PATH set):
```bash
if [[ -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  mkdir -p "$(dirname "$REVIEW_RECEIPT_PATH")"
  cat > "$REVIEW_RECEIPT_PATH" <<EOF
{"type":"impl_review","id":"$TASK_ID","mode":"mcp","timestamp":"$ts","chat_id":"<CHAT_ID>"}
EOF
  echo "REVIEW_RECEIPT_WRITTEN: $REVIEW_RECEIPT_PATH"
fi
```

### Fix Loop (MCP)

Same as RP backend:
1. Parse issues from reviewer feedback (Critical → Major → Minor)
2. Fix the code
3. Run tests/lints
4. Commit fixes (MANDATORY before re-review)
5. Re-review using same chat_id (new_chat: false):
   ```
   mcp__RepoPrompt__chat_send
     new_chat: false
     chat_id: "<chat_id>"
     mode: "review"
     message: "Issues addressed. Please re-review.

   **REQUIRED**: End with `<verdict>SHIP</verdict>` or `<verdict>NEEDS_WORK</verdict>` or `<verdict>MAJOR_RETHINK</verdict>`"
   ```
6. Repeat until SHIP

**CRITICAL**: Re-reviews MUST use the same chat_id so reviewer has context.

---

## Fix Loop (RP)

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is production-grade world-class software and architecture. Never use AskUserQuestion in this loop.**

**CRITICAL: You MUST fix the code BEFORE re-reviewing. Never re-review without making changes.**

**MAX ITERATIONS**: Limit fix+re-review cycles to **${MAX_REVIEW_ITERATIONS:-3}** iterations (default 3, configurable in Ralph's config.env). If still NEEDS_WORK after max rounds, output `<promise>RETRY</promise>` and stop — let the next Ralph iteration start fresh.

If verdict is NEEDS_WORK:

1. **Parse issues** - Extract ALL issues by severity (Critical → Major → Minor)
2. **Fix the code** - Address each issue in order
3. **Run tests/lints** - Verify fixes don't break anything
4. **Commit fixes** (MANDATORY before re-review):
   ```bash
   git add -A
   git commit -m "fix: address review feedback"
   ```
   **If you skip this and re-review without committing changes, reviewer will return NEEDS_WORK again.**

5. **Request re-review** (only AFTER step 4):

   Use `--chat-id` to continue in the same conversation (reviewer has context):

   ```bash
   cat > /tmp/re-review.md << 'EOF'
   Issues addressed. Please re-review.

   **REQUIRED**: End with `<verdict>SHIP</verdict>` or `<verdict>NEEDS_WORK</verdict>` or `<verdict>MAJOR_RETHINK</verdict>`
   EOF

   $FLOWCTL rp chat-send --window "$W" --tab "$T" \
     --message-file /tmp/re-review.md \
     --chat-id "$CHAT_ID" \
     --mode review
   ```

6. **Repeat** until SHIP

**Note**: RP auto-refreshes file contents on every message. No need to re-add files to selection.

---

## Anti-patterns

**All backends:**
- **Reviewing yourself** - You coordinate; the backend reviews
- **No receipt** - If REVIEW_RECEIPT_PATH is set, you MUST write receipt
- **Ignoring verdict** - Must extract and act on verdict tag
- **Mixing backends** - Stick to one backend for the entire review session

**RP backend only:**
- **Calling builder directly** - Must use `setup-review` which wraps it
- **Skipping setup-review** - Window selection MUST happen via this command
- **Hard-coding window IDs** - Never write `--window 1`
- **Missing changed files** - Add ALL changed files to selection

**Codex backend only:**
- **Using `--last` flag** - Conflicts with parallel usage; use `--receipt` instead
- **Direct codex calls** - Must use `flowctl codex` wrappers

**MCP backend only:**
- **Calling flowctl rp commands** - MCP backend uses MCP tools directly, not flowctl
- **Using new_chat on re-reviews** - Must use same chat_id for reviewer context
- **Skipping MCP connection check** - Always verify MCP is connected first
