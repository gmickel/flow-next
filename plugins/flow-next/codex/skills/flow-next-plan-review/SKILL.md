---
name: flow-next-plan-review
description: Carmack-level plan review via RepoPrompt or Codex. Use when reviewing Flow epic specs or design docs. Triggers on /flow-next:plan-review.
user-invocable: false
---

# Plan Review Mode

**Read [workflow.md](workflow.md) for detailed phases and anti-patterns.**

Conduct a John Carmack-level review of epic plans.

**Role**: Code Review Coordinator (NOT the reviewer)
**Backends**: RepoPrompt (rp) or Codex CLI (codex)

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:
```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
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
3. **MUST use `setup-review (5-15 min, DO NOT RETRY)`** - handles window selection + builder atomically
4. **DO NOT add --json flag to chat-send (2-10 min, DO NOT RETRY)** - it suppresses the review response
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
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl"
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

# --files: comma-separated CODE files for reviewer context
# Epic/task specs are auto-included; pass files the plan will CREATE or MODIFY
# How to identify: read the epic spec, find files mentioned or directories affected
# Example: epic touches auth → pass existing auth files for context
#
# Dynamic approach (if epic mentions specific paths):
#   CODE_FILES=$(grep -oE 'src/[^ ]+\.(ts|py|js)' .flow/specs/${EPIC_ID}.md | sort -u | paste -sd,)
# Or list key files manually:
CODE_FILES="src/main.py,src/config.py"

$FLOWCTL codex plan-review "$EPIC_ID" --files "$CODE_FILES" --receipt "$RECEIPT_PATH"
# Output includes VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK
```

On NEEDS_WORK: fix plan via `$FLOWCTL epic set-plan` AND sync affected task specs via `$FLOWCTL task set-spec`, then re-run (receipt enables session continuity).

**Note**: `codex plan-review` automatically includes task specs in the review prompt.

### RepoPrompt Backend

**⚠️ STOP: You MUST read and execute [workflow.md](workflow.md) now.**

Go to the "RepoPrompt Backend Workflow" section in workflow.md and execute those steps. Do not proceed here until workflow.md phases are complete.

The workflow covers:
1. Get plan content and save checkpoint
2. Atomic setup (setup-review (5-15 min, DO NOT RETRY)) → sets `$W` and `$T`
3. Augment selection (epic + task specs)
4. Send review and parse verdict

**Return here only after workflow.md execution is complete.**

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
   - **RP**: `$FLOWCTL rp chat-send (2-10 min, DO NOT RETRY) --window "$W" --tab "$T" --message-file /tmp/re-review.md` (NO `--new-chat`)
5. **Repeat** until `<verdict>SHIP</verdict>`

**Recovery**: If context compaction occurred during review, restore from checkpoint:
```bash
$FLOWCTL checkpoint restore --epic <EPIC_ID> --json
```

**CRITICAL**: For RP, re-reviews must stay in the SAME chat so reviewer has context. Only use `--new-chat` on the FIRST review.
