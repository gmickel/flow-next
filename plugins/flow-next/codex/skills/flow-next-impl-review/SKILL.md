---
name: flow-next-impl-review
description: John Carmack-level implementation review via RepoPrompt or Codex. Use when reviewing code changes, PRs, or implementations. Triggers on /flow-next:impl-review.
user-invocable: false
---

# Implementation Review Mode

**Read [workflow.md](workflow.md) for detailed phases and anti-patterns.**

Conduct a John Carmack-level review of implementation changes on the current branch.

**Role**: Code Review Coordinator (NOT the reviewer)
**Backends**: RepoPrompt (rp), Codex CLI (codex), or GitHub Copilot CLI (copilot)

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:
```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
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

**Spec grammar:** `backend[:model[:effort]]` — `FLOW_REVIEW_BACKEND` and `.flow/config.json review.backend` both accept this. Examples: `codex`, `codex:gpt-5.2`, `copilot:claude-opus-4.5:xhigh`. Per-task `review` (set via `flowctl task set-backend`) overrides env.

## Critical Rules

**For rp backend:**
1. **DO NOT REVIEW CODE YOURSELF** - you coordinate, RepoPrompt reviews
2. **MUST WAIT for actual RP response** - never simulate/skip the review
3. **MUST use `setup-review (5-15 min, DO NOT RETRY)`** - handles window selection + builder atomically
4. **DO NOT add --json flag to chat-send (2-10 min, DO NOT RETRY)** - it suppresses the review response
5. **Re-reviews MUST stay in SAME chat** - omit `--new-chat` after first review

**For codex backend:**
1. Use `$FLOWCTL codex impl-review` exclusively
2. Pass `--receipt` for session continuity on re-reviews
3. Parse verdict from command output

**For copilot backend:**
1. Use `$FLOWCTL copilot impl-review` exclusively
2. Pass `--receipt` for session continuity on re-reviews (session only resumes when prior receipt has `mode == "copilot"`)
3. Model + effort resolved via (first match wins): `--spec backend:model:effort` flag, per-task `review`, `FLOW_REVIEW_BACKEND` spec, `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, registry defaults
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
Format: `[task ID] [--base <commit>] [focus areas]`

- `--base <commit>` - Compare against this commit instead of main/master (for task-scoped reviews)
- Task ID - Optional, for context and receipt tracking
- Focus areas - Optional, specific areas to examine

**Scope behavior:**
- With `--base`: Reviews only changes since that commit (task-scoped)
- Without `--base`: Reviews entire branch vs main/master (full branch review)

## Workflow

**See [workflow.md](workflow.md) for full details on each backend.**

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

### Step 0: Parse Arguments

Parse $ARGUMENTS for:
- `--base <commit>` → `BASE_COMMIT` (if provided, use for scoped diff)
- First positional arg matching `fn-*` → `TASK_ID`
- Remaining args → focus areas

If `--base` not provided, `BASE_COMMIT` stays empty (will fall back to main/master).

### Step 1: Detect Backend

Run backend detection from SKILL.md above. Then branch:

### Codex Backend

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt.json}"

# Use BASE_COMMIT if provided, else fall back to main
if [[ -n "$BASE_COMMIT" ]]; then
  $FLOWCTL codex impl-review "$TASK_ID" --base "$BASE_COMMIT" --receipt "$RECEIPT_PATH"
else
  $FLOWCTL codex impl-review "$TASK_ID" --base main --receipt "$RECEIPT_PATH"
fi
# Output includes VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK
```

On NEEDS_WORK: fix code, commit, re-run (receipt enables session continuity).

### Copilot Backend

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt.json}"

# Override model + effort (pick one):
#   --spec copilot:claude-opus-4.5:xhigh   (preferred, explicit)
#   FLOW_REVIEW_BACKEND=copilot:claude-opus-4.5:xhigh  (env, cascades through `review-backend`)
#   FLOW_COPILOT_MODEL=gpt-5.2 FLOW_COPILOT_EFFORT=high  (env per-field; fills only missing)

if [[ -n "$BASE_COMMIT" ]]; then
  $FLOWCTL copilot impl-review "$TASK_ID" --base "$BASE_COMMIT" --receipt "$RECEIPT_PATH"
else
  $FLOWCTL copilot impl-review "$TASK_ID" --base main --receipt "$RECEIPT_PATH"
fi
# Output includes VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK
```

On NEEDS_WORK: fix code, commit, re-run. Session resumes only when prior receipt at `$RECEIPT_PATH` has `mode == "copilot"` (cross-backend switch starts a fresh session).

### RepoPrompt Backend

**⚠️ STOP: You MUST read and execute [workflow.md](workflow.md) now.**

Go to the "RepoPrompt Backend Workflow" section in workflow.md and execute those steps. Do not proceed here until workflow.md phases are complete.

The workflow covers:
1. Identify changes (use `BASE_COMMIT` if provided)
2. Atomic setup (setup-review (5-15 min, DO NOT RETRY)) → sets `$W` and `$T`
3. Augment selection and build review prompt
4. Send review and parse verdict

**Return here only after workflow.md execution is complete.**

## Fix Loop (INTERNAL - do not exit to Ralph)

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is production-grade world-class software and architecture. Never use AskUserQuestion in this loop.**

If verdict is NEEDS_WORK, loop internally until SHIP:

1. **Parse issues** from reviewer feedback (Critical → Major → Minor)
2. **Fix code** and run tests/lints
3. **Commit fixes** (mandatory before re-review)
4. **Re-review**:
   - **Codex**: Re-run `flowctl codex impl-review` (receipt enables context)
   - **Copilot**: Re-run `flowctl copilot impl-review` (receipt enables context; must be `mode == "copilot"` to resume)
   - **RP**: `$FLOWCTL rp chat-send (2-10 min, DO NOT RETRY) --window "$W" --tab "$T" --message-file /tmp/re-review.md` (NO `--new-chat`)
5. **Repeat** until `<verdict>SHIP</verdict>`

**CRITICAL**: For RP, re-reviews must stay in the SAME chat so reviewer has context. Only use `--new-chat` on the FIRST review.
