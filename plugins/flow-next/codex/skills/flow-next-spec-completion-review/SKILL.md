---
name: flow-next-spec-completion-review
description: Spec completion review - verifies all spec tasks implement the spec requirements. Triggers on /flow-next:spec-completion-review.
user-invocable: false
---

# Spec Completion Review Mode

**Workflow is backend-split. Read [workflow-common.md](workflow-common.md) for Phase 0 (backend detection + philosophy), then read ONLY the file matching your active backend:**

- `BACKEND=codex` → [workflow-codex.md](workflow-codex.md)
- `BACKEND=copilot` → [workflow-copilot.md](workflow-copilot.md)
- `BACKEND=rp` → [workflow-rp.md](workflow-rp.md)

Do not load the other two — only the active backend's file is needed.

Verify that the combined implementation of all tasks in a spec satisfies the spec requirements. This is NOT a code quality review (that's impl-review's job) — this confirms spec compliance only.

**Role**: Spec Completion Review Coordinator (NOT the reviewer)
**Backends**: RepoPrompt (rp), Codex CLI (codex), or GitHub Copilot CLI (copilot)

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow-*.md`) use `$FLOWCTL`:

```bash
FLOWCTL="$HOME/.codex/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Backend Selection

**Priority** (first match wins):
1. `--review=rp|codex|copilot|none` argument
2. `FLOW_REVIEW_BACKEND` env var — bare backend (`rp`, `codex`, `copilot`, `none`) OR spec form (`codex:gpt-5.4:xhigh`, `copilot:claude-opus-4.5`)
3. `.flow/config.json` → `review.backend` (same bare / spec forms)
4. **Error** - no auto-detection

### Parse from arguments first

Check $ARGUMENTS for:
- `--review=rp` or `--review rp` → use rp
- `--review=codex` or `--review codex` → use codex
- `--review=copilot` or `--review copilot` → use copilot
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
- **codex** — Codex CLI (cross-platform); uses OpenAI models (default `gpt-5.5`). `FLOW_CODEX_MODEL` / `FLOW_CODEX_EFFORT` env vars, or `--spec codex:gpt-5.4:xhigh`.
- **copilot** — GitHub Copilot CLI (cross-platform); supports Claude Opus/Sonnet/Haiku 4.5 and GPT-5.2 families via a Copilot subscription. `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, or `--spec copilot:claude-opus-4.5:xhigh`.

**Spec grammar:** `backend[:model[:effort]]` — `FLOW_REVIEW_BACKEND` and `.flow/config.json review.backend` both accept this. Examples: `codex`, `codex:gpt-5.2`, `copilot:claude-opus-4.5:xhigh`. Per-spec `default_review` (set via `flowctl spec set-backend`) overrides env.

## Critical Rules

**For rp backend:**
1. **DO NOT REVIEW CODE YOURSELF** - you coordinate, RepoPrompt reviews
2. **MUST WAIT for actual RP response** - never simulate/skip the review
3. **MUST use `setup-review (5-15 min, DO NOT RETRY)`** - handles window selection + builder atomically
4. **DO NOT add --json flag to chat-send (2-10 min, DO NOT RETRY)** - it suppresses the review response
5. **Re-reviews MUST stay in SAME chat** - omit `--new-chat` after first review

**For codex backend:**
1. Use `$FLOWCTL codex completion-review` exclusively
2. Pass `--receipt` for session continuity on re-reviews
3. Parse verdict from command output

**For copilot backend:**
1. Use `$FLOWCTL copilot completion-review` exclusively
2. Pass `--receipt` for session continuity on re-reviews (session only resumes when prior receipt has `mode == "copilot"`)
3. Model + effort resolved via (first match wins): `--spec backend:model:effort` flag, per-spec `default_review`, `FLOW_REVIEW_BACKEND` spec, `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, registry defaults
4. Parse verdict from command output

**For all backends:**
- If `REVIEW_RECEIPT_PATH` set: write receipt after SHIP verdict (RP writes manually after fix loop; codex writes automatically via `--receipt`)
- Any failure → output `<promise>RETRY</promise>` and stop

**FORBIDDEN**:
- Self-declaring SHIP without actual backend verdict
- Mixing backends mid-review (stick to one)
- Skipping review silently (must inform user and exit cleanly when backend is "none")

## Input

Arguments: $ARGUMENTS
Format: `<spec-id> [--review=rp|codex|copilot|none]`

- Spec ID - Required, e.g. `fn-1` or `fn-22-53k`
- `--review` - Optional backend override

## Workflow

```bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

### Step 0: Parse Arguments

Parse $ARGUMENTS for:
- First positional arg matching `fn-*` → `SPEC_ID`
- `--review=<backend>` → backend override
- Remaining args → focus areas

### Step 1: Detect Backend + Load Workflow

1. Read [workflow-common.md](workflow-common.md) and execute its Phase 0 to resolve `$BACKEND`.
2. Then read **only** the file for that backend:

| `$BACKEND` | File to read |
|------------|--------------|
| `codex` | [workflow-codex.md](workflow-codex.md) |
| `copilot` | [workflow-copilot.md](workflow-copilot.md) |
| `rp` | [workflow-rp.md](workflow-rp.md) |

**Do not read the other backend files.** Each is self-contained for its backend; loading the others wastes context.

### Step 2: Execute the backend workflow

Follow the phases in the per-backend file end-to-end. Each file owns its own Identify → Execute → Verdict → Receipt steps (and, for RP, the full Phase 1-4 setup-review (5-15 min, DO NOT RETRY) / chat-send (2-10 min, DO NOT RETRY) / receipt build).

## Fix Loop (INTERNAL - do not exit to Ralph)

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is complete spec compliance. Never use the plain-text numbered prompt in this loop.**

If verdict is NEEDS_WORK, loop internally until SHIP:

1. **Parse issues** from reviewer feedback (missing requirements, incomplete implementations)
2. **Fix code** and run tests/lints
3. **Commit fixes** (mandatory before re-review)
4. **Re-review**:
 - **Codex**: Re-run `flowctl codex completion-review` (receipt enables context)
 - **Copilot**: Re-run `flowctl copilot completion-review` (receipt enables context; must be `mode == "copilot"` to resume)
 - **RP**: `$FLOWCTL rp chat-send (2-10 min, DO NOT RETRY) --window "$W" --tab "$T" --message-file /tmp/re-review.md` (NO `--new-chat`)
5. **Repeat** until `<verdict>SHIP</verdict>`

**CRITICAL**: For RP, re-reviews must stay in the SAME chat so reviewer has context. Only use `--new-chat` on the FIRST review.
