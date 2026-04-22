---
name: flow-next-plan-review
description: Carmack-level plan review via RepoPrompt or Codex. Use when reviewing Flow epic specs or design docs. Triggers on /flow-next:plan-review.
user-invocable: false
---

# Plan Review Mode

**Read [workflow.md](workflow.md) for detailed phases and anti-patterns.**

Conduct a John Carmack-level review of epic plans.

**Role**: Code Review Coordinator (NOT the reviewer)
**Backends**: RepoPrompt (rp), Codex CLI (codex), or GitHub Copilot CLI (copilot)

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:
```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
```

## Backend Selection

**Priority** (first match wins):
1. `--review=rp|codex|copilot|export|none` argument
2. `FLOW_REVIEW_BACKEND` env var — bare backend (`rp`, `codex`, `copilot`, `none`) OR spec form (`codex:gpt-5.4:xhigh`, `copilot:claude-opus-4.5`)
3. `.flow/config.json` → `review.backend` (same bare / spec forms)
4. **Error** - no auto-detection

### Parse from arguments first

Check $ARGUMENTS for:
- `--review=rp` or `--review rp` → use rp
- `--review=codex` or `--review codex` → use codex
- `--review=copilot` or `--review copilot` → use copilot
- `--review=export` or `--review export` → use export
- `--review=none` or `--review none` → skip review

If found, use that backend and skip all other detection.

### Otherwise read from config

```bash
# Priority: --review flag > env > config
BACKEND=$($FLOWCTL review-backend)

if [[ "$BACKEND" == "ASK" ]]; then
  echo "Error: No review backend configured."
  echo "Run /flow-next:setup to configure, or pass --review=rp|codex|copilot|none"
  exit 1
fi

echo "Review backend: $BACKEND (override: --review=rp|codex|copilot|none)"
```

### Backend at a glance

- **rp** — RepoPrompt (macOS GUI); builder auto-selects context. Primary backend.
- **codex** — Codex CLI (cross-platform); uses OpenAI models (default `gpt-5.4`). `FLOW_CODEX_MODEL` / `FLOW_CODEX_EFFORT` env vars, or `--spec codex:gpt-5.4:xhigh`.
- **copilot** — GitHub Copilot CLI (cross-platform); supports Claude Opus/Sonnet/Haiku 4.5 and GPT-5.2 families via a Copilot subscription. `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, or `--spec copilot:claude-opus-4.5:xhigh`.

**Spec grammar:** `backend[:model[:effort]]` — `FLOW_REVIEW_BACKEND` and `.flow/config.json review.backend` both accept this. Examples: `codex`, `codex:gpt-5.2`, `copilot:claude-opus-4.5:xhigh`. Per-epic `default_review` (set via `flowctl epic set-backend`) overrides env.

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

**For copilot backend:**
1. Use `$FLOWCTL copilot plan-review` exclusively
2. Pass `--receipt` for session continuity on re-reviews (session only resumes when prior receipt has `mode == "copilot"`)
3. Model + effort resolved via (first match wins): `--spec backend:model:effort` flag, per-epic `default_review`, `FLOW_REVIEW_BACKEND` spec, `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, registry defaults
4. Parse verdict from command output

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
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
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

### Copilot Backend

```bash
EPIC_ID="${1:-}"
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/plan-review-receipt.json}"

# Save checkpoint before review (recovery point if context compacts)
$FLOWCTL checkpoint save --epic "$EPIC_ID" --json

# --files: comma-separated CODE files for reviewer context (same shape as codex)
# Epic/task specs are auto-included; pass files the plan will CREATE or MODIFY
CODE_FILES="src/main.py,src/config.py"

# Override model + effort (pick one):
#   --spec copilot:claude-opus-4.5:xhigh   (preferred)
#   FLOW_REVIEW_BACKEND=copilot:claude-opus-4.5:xhigh
#   FLOW_COPILOT_MODEL=gpt-5.2 FLOW_COPILOT_EFFORT=high

$FLOWCTL copilot plan-review "$EPIC_ID" --files "$CODE_FILES" --receipt "$RECEIPT_PATH"
# Output includes VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK
```

On NEEDS_WORK: fix plan via `$FLOWCTL epic set-plan` AND sync affected task specs via `$FLOWCTL task set-spec`, then re-run. Session resume only when prior receipt has `mode == "copilot"`.

**Note**: `copilot plan-review` automatically includes task specs in the review prompt (same as codex).

### RepoPrompt Backend

**⚠️ STOP: You MUST read and execute [workflow.md](workflow.md) now.**

Go to the "RepoPrompt Backend Workflow" section in workflow.md and execute those steps. Do not proceed here until workflow.md phases are complete.

The workflow covers:
1. Get plan content and save checkpoint
2. Atomic setup (setup-review) → sets `$W` and `$T`
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
   - **Copilot**: Re-run `flowctl copilot plan-review` (receipt enables context; must be `mode == "copilot"` to resume)
   - **RP**: `$FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file /tmp/re-review.md` (NO `--new-chat`)
5. **Repeat** until `<verdict>SHIP</verdict>`

**Recovery**: If context compaction occurred during review, restore from checkpoint:
```bash
$FLOWCTL checkpoint restore --epic <EPIC_ID> --json
```

**CRITICAL**: For RP, re-reviews must stay in the SAME chat so reviewer has context. Only use `--new-chat` on the FIRST review.
