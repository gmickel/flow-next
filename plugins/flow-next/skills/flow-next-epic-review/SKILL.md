---
name: flow-next-epic-review
description: Epic completion review - verifies all epic tasks implement spec requirements. Triggers on /flow-next:epic-review.
---

# Epic Completion Review Mode

**Read [workflow.md](workflow.md) for detailed phases and anti-patterns.**

Verify that the combined implementation of all epic tasks satisfies the spec requirements. This is NOT a code quality review (that's impl-review's job) — this confirms spec compliance only.

**Role**: Epic Review Coordinator (NOT the reviewer)
**Backends**: RepoPrompt (rp) or Codex CLI (codex)

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:
```bash
FLOWCTL="${CLAUDE_PLUGIN_ROOT}/scripts/flowctl"
```

## Backend Selection

**Priority** (first match wins):
1. `--review=rp|codex|none` argument
2. `FLOW_REVIEW_BACKEND` env var (`rp`, `codex`, `none`)
3. `.flow/config.json` → `review.backend`
4. **Error** - no auto-detection

### Parse from arguments first

Check $ARGUMENTS for:
- `--review=rp` or `--review rp` → use rp
- `--review=codex` or `--review codex` → use codex
- `--review=none` or `--review none` → skip review

If found, use that backend and skip all other detection.

### Otherwise read from config

```bash
BACKEND=$($FLOWCTL review-backend)

if [[ "$BACKEND" == "ASK" ]]; then
  echo "Error: No review backend configured."
  echo "Run /flow-next:setup to configure, or pass --review=rp|codex|none"
  exit 1
fi

echo "Review backend: $BACKEND (override: --review=rp|codex|none)"
```

## Critical Rules

**For rp backend:**
1. **DO NOT REVIEW CODE YOURSELF** - you coordinate, RepoPrompt reviews
2. **MUST WAIT for actual RP response** - never simulate/skip the review
3. **MUST use `setup-review`** - handles window selection + builder atomically
4. **DO NOT add --json flag to chat-send** - it suppresses the review response
5. **Re-reviews MUST stay in SAME chat** - omit `--new-chat` after first review

**For codex backend:**
1. Use `$FLOWCTL codex completion-review` exclusively
2. Pass `--receipt` for session continuity on re-reviews
3. Parse verdict from command output

**For all backends:**
- If `REVIEW_RECEIPT_PATH` set: write receipt after SHIP verdict (RP writes manually after fix loop; codex writes automatically via `--receipt`)
- Any failure → output `<promise>RETRY</promise>` and stop

**FORBIDDEN**:
- Self-declaring SHIP without actual backend verdict
- Mixing backends mid-review (stick to one)
- Skipping review silently (must inform user and exit cleanly when backend is "none")

## Input

Arguments: $ARGUMENTS
Format: `<epic-id> [--review=rp|codex|none]`

- Epic ID - Required, e.g. `fn-1` or `fn-22-53k`
- `--review` - Optional backend override

## Workflow

**See [workflow.md](workflow.md) for full details on each backend.**

```bash
FLOWCTL="${CLAUDE_PLUGIN_ROOT}/scripts/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

### Step 0: Parse Arguments

Parse $ARGUMENTS for:
- First positional arg matching `fn-*` → `EPIC_ID`
- `--review=<backend>` → backend override
- Remaining args → focus areas

### Step 1: Detect Backend

Run backend detection from SKILL.md above. Then branch:

### Codex Backend

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/completion-review-receipt.json}"

$FLOWCTL codex completion-review "$EPIC_ID" --receipt "$RECEIPT_PATH"
# Output includes VERDICT=SHIP|NEEDS_WORK
```

On NEEDS_WORK: fix code, commit, re-run (receipt enables session continuity).

### RepoPrompt Backend

```bash
# Step 1: Gather context
EPIC_SPEC="$($FLOWCTL cat "$EPIC_ID")"
TASKS="$($FLOWCTL tasks --epic "$EPIC_ID" --json)"
CHANGED_FILES="$(git diff main..HEAD --name-only)"

# Step 2: Atomic setup (pick-window + builder)
eval "$($FLOWCTL rp setup-review --repo-root "$REPO_ROOT" --summary "Epic completion review: $EPIC_ID")"
# Outputs W=<window> T=<tab>. If fails → <promise>RETRY</promise>

# Step 3: Augment selection
# Add epic spec, all task specs, and changed files
$FLOWCTL rp select-add --window "$W" --tab "$T" .flow/specs/$EPIC_ID.md
for task in $(echo "$TASKS" | jq -r '.[].id'); do
  $FLOWCTL rp select-add --window "$W" --tab "$T" .flow/tasks/$task.md
done
for f in $CHANGED_FILES; do
  $FLOWCTL rp select-add --window "$W" --tab "$T" "$f"
done

# Step 4: Get builder handoff and build review prompt
HANDOFF="$($FLOWCTL rp prompt-get --window "$W" --tab "$T")"
# Build /tmp/completion-review-prompt.md with handoff + review criteria (see workflow.md)

# Step 5: Send review prompt
$FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file /tmp/completion-review-prompt.md --new-chat --chat-name "Epic Review: $EPIC_ID"
# WAIT for response. Extract verdict from response.
# Valid verdicts: SHIP, NEEDS_WORK
# If no valid verdict tag → <promise>RETRY</promise>

# Step 6: Write receipt if REVIEW_RECEIPT_PATH set
```

## Fix Loop (INTERNAL - do not exit to Ralph)

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is complete spec compliance. Never use AskUserQuestion in this loop.**

If verdict is NEEDS_WORK, loop internally until SHIP:

1. **Parse issues** from reviewer feedback (missing requirements, incomplete implementations)
2. **Fix code** and run tests/lints
3. **Commit fixes** (mandatory before re-review)
4. **Re-review**:
   - **Codex**: Re-run `flowctl codex completion-review` (receipt enables context)
   - **RP**: `$FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file /tmp/re-review.md` (NO `--new-chat`)
5. **Repeat** until `<verdict>SHIP</verdict>`

**CRITICAL**: For RP, re-reviews must stay in the SAME chat so reviewer has context. Only use `--new-chat` on the FIRST review.
