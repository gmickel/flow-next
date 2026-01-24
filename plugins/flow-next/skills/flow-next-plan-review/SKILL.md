---
name: flow-next-plan-review
description: Carmack-level plan review via RepoPrompt or Codex. Use when reviewing Flow epic specs or design docs. Triggers on /flow-next:plan-review.
---

# Plan Review Mode

**Read [workflow.md](workflow.md) for detailed phases and anti-patterns.**

Conduct a John Carmack-level review of epic plans.

**Role**: Code Review Coordinator (NOT the reviewer)
**Backends**: RepoPrompt (rp) or Codex CLI (codex)

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:
```bash
FLOWCTL="${CLAUDE_PLUGIN_ROOT}/scripts/flowctl"
```

## Backend Selection

**Priority** (first match wins):
1. `--review=rp|codex|export|none` argument
2. `FLOW_REVIEW_BACKEND` env var (`rp`, `codex`, `none`)
3. `.flow/config.json` → `review.backend`
4. **Error** - no auto-detection

### Parse from arguments first

Check $ARGUMENTS for:
- `--review=rp` or `--review rp` → use rp
- `--review=codex` or `--review codex` → use codex
- `--review=export` or `--review export` → use export
- `--review=none` or `--review none` → skip review

If found, use that backend and skip all other detection.

### Otherwise read from config

```bash
# Priority: --review flag > env > config
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
1. **DO NOT REVIEW THE PLAN YOURSELF** - you coordinate, RepoPrompt reviews
2. **MUST WAIT for actual RP response** - never simulate/skip the review
3. **MUST use `setup-review`** - handles window selection + builder atomically
4. **DO NOT add --json flag to chat-send** - it suppresses the review response
5. **Re-reviews MUST stay in SAME chat** - omit `--new-chat` after first review

**For codex backend:**
1. Use `$FLOWCTL codex plan-review` exclusively
2. Pass `--receipt` for session continuity on re-reviews
3. Parse verdict from command output

**For all backends:**
- If `REVIEW_RECEIPT_PATH` set: write receipt after review (any verdict)
- Any failure → output `<promise>RETRY</promise>` and stop

**FORBIDDEN**:
- Self-declaring SHIP without actual backend verdict
- Mixing backends mid-review (stick to one)
- Skipping review when backend is "none" without user consent

## Input

Arguments: $ARGUMENTS
Format: `<flow-epic-id> [focus areas]`

## Workflow

**See [workflow.md](workflow.md) for full details on each backend.**

```bash
FLOWCTL="${CLAUDE_PLUGIN_ROOT}/scripts/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

### Step 0: Detect Backend

Run backend detection from SKILL.md above. Then branch:

### Codex Backend

```bash
EPIC_ID="${1:-}"
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/plan-review-receipt.json}"

# Save checkpoint before review (recovery point if context compacts)
$FLOWCTL checkpoint save --epic "$EPIC_ID" --json

$FLOWCTL codex plan-review "$EPIC_ID" --receipt "$RECEIPT_PATH"
# Output includes VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK
```

On NEEDS_WORK: fix plan via `$FLOWCTL epic set-plan` AND sync affected task specs via `$FLOWCTL task set-spec`, then re-run (receipt enables session continuity).

**Note**: `codex plan-review` automatically includes task specs in the review prompt.

### RepoPrompt Backend

```bash
# Step 1: Get plan content
$FLOWCTL show <id> --json
$FLOWCTL cat <id>

# Save checkpoint before review (recovery point if context compacts)
$FLOWCTL checkpoint save --epic <id> --json

# Step 2: Atomic setup (pick-window + builder)
eval "$($FLOWCTL rp setup-review --repo-root "$REPO_ROOT" --summary "Review plan for <EPIC_ID>: <summary>")"
# Outputs W=<window> T=<tab>. If fails → <promise>RETRY</promise>

# Step 3: Augment selection - add epic AND task specs
$FLOWCTL rp select-add --window "$W" --tab "$T" .flow/specs/<epic-id>.md
# Add all task specs for this epic
for task_spec in .flow/tasks/${EPIC_ID}.*.md; do
  [[ -f "$task_spec" ]] && $FLOWCTL rp select-add --window "$W" --tab "$T" "$task_spec"
done

# Step 4: Get builder handoff and build review prompt
HANDOFF="$($FLOWCTL rp prompt-get --window "$W" --tab "$T")"
# Build /tmp/review-prompt.md with handoff + review criteria (see workflow.md)

# Step 5: Send review prompt
$FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file /tmp/review-prompt.md --new-chat --chat-name "Plan Review: <EPIC_ID>"
# WAIT for response. Extract verdict from response.
# Valid verdicts: SHIP, NEEDS_WORK, MAJOR_RETHINK
# If no valid verdict tag → <promise>RETRY</promise>

# Step 6: Write receipt if REVIEW_RECEIPT_PATH set
# Step 7: Update status
$FLOWCTL epic set-plan-review-status <EPIC_ID> --status ship --json
```

## Fix Loop (INTERNAL - do not exit to Ralph)

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is production-grade world-class software and architecture. Never use AskUserQuestion in this loop.**

If verdict is NEEDS_WORK, loop internally until SHIP:

1. **Parse issues** from reviewer feedback
2. **Fix epic spec** (stdin preferred, temp file if content has single quotes):
   ```bash
   # Preferred: stdin heredoc
   $FLOWCTL epic set-plan <EPIC_ID> --file - --json <<'EOF'
   <updated epic spec content>
   EOF

   # Or temp file
   $FLOWCTL epic set-plan <EPIC_ID> --file /tmp/updated-plan.md --json
   ```
3. **Sync affected task specs** - If epic changes affect task specs, update them:
   ```bash
   $FLOWCTL task set-spec <TASK_ID> --file - --json <<'EOF'
   <updated task spec content>
   EOF
   ```
   Task specs need updating when epic changes affect:
   - State/enum values referenced in tasks
   - Acceptance criteria that tasks implement
   - Approach/design decisions tasks depend on
   - Lock/retry/error handling semantics
   - API signatures or type definitions
4. **Re-review**:
   - **Codex**: Re-run `flowctl codex plan-review` (receipt enables context)
   - **RP**: `$FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file /tmp/re-review.md` (NO `--new-chat`)
5. **Repeat** until `<verdict>SHIP</verdict>`

**Recovery**: If context compaction occurred during review, restore from checkpoint:
```bash
$FLOWCTL checkpoint restore --epic <EPIC_ID> --json
```

**CRITICAL**: For RP, re-reviews must stay in the SAME chat so reviewer has context. Only use `--new-chat` on the FIRST review.
