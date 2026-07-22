---
name: flow-next-spec-completion-review
description: Spec completion review - verifies all spec tasks implement the spec requirements. Triggers on /flow-next:spec-completion-review.
user-invocable: false
---

# Spec Completion Review Mode

**Workflow is backend-split. Read [workflow-common.md](workflow-common.md) for Phase 0 (backend detection + philosophy), then read ONLY the file matching your active backend:**

- `BACKEND=codex` → [workflow-codex.md](workflow-codex.md)
- `BACKEND=copilot` → [workflow-copilot.md](workflow-copilot.md)
- `BACKEND=cursor` → [workflow-cursor.md](workflow-cursor.md)
- `BACKEND=rp` → [workflow-rp.md](workflow-rp.md)

Do not load the others — only the active backend's file is needed.

Verify that the combined implementation of all tasks in a spec satisfies the spec requirements. This is NOT a code quality review (that's impl-review's job) — this confirms spec compliance only.

**Role**: Spec Completion Review Coordinator (NOT the reviewer)
**Backends** (branch on the Phase 0 `RP_ELIGIBLE` probe):
- When `RP_ELIGIBLE=1`: RepoPrompt (rp), Codex CLI (codex), GitHub Copilot CLI (copilot), or Cursor CLI (cursor)
- When `RP_ELIGIBLE=0`: Codex CLI (codex), GitHub Copilot CLI (copilot), or Cursor CLI (cursor) — rp is macOS-only; never list it in guidance you surface (`--review=rp` stays accepted)

## Preamble — execute Phase 0 exactly once

**The executable Phase 0 lives in [workflow-common.md](workflow-common.md) §"Phase 0: Backend Detection" — Read it and execute it ONCE, before any other bash in this skill.** It defines `$FLOWCTL` (bundled — NOT installed globally; `which flowctl` fails, expected), probes `RP_ELIGIBLE`, resolves `$BACKEND` via the single `flowctl review-backend` call, and handles the ASK / `none` cases. Never invoke `flowctl review-backend` a second time in the same run.

Exception: a `--review=<backend>` argument (see Backend Selection below) wins — when present, set `BACKEND` from the flag and skip Phase 0's `review-backend` call + ASK handling (still run its `$FLOWCTL` / `RP_ELIGIBLE` setup lines).

When `RP_ELIGIBLE=0` (not macOS, no supported RepoPrompt CLI), never *steer* the user toward rp: every backend summary, recommendation, or override hint you surface presents only the runnable configured backends `codex`, `copilot`, `cursor` (plus `none`). Suppression is not a ban: an explicit `--review=rp`, `FLOW_REVIEW_BACKEND=rp`, or `review.backend=rp` still resolves to rp and errors at runtime via `require_rp_cli()`.

## Backend Selection

**Priority** (first match wins):
1. `--review=rp|codex|copilot|cursor|none` argument
2. `FLOW_REVIEW_BACKEND` env var — bare backend (`rp`, `codex`, `copilot`, `cursor`, `none`) OR spec form (`codex:gpt-5.4:xhigh`, `copilot:claude-opus-4.5`, `cursor:gpt-5.5-high`)
3. `.flow/config.json` → `review.backend` (same bare / spec forms)
4. **Error** - no auto-detection

### Parse from arguments first

Check $ARGUMENTS for:
- `--review=rp` or `--review rp` → use rp
- `--review=codex` or `--review codex` → use codex
- `--review=copilot` or `--review copilot` → use copilot
- `--review=cursor` or `--review cursor` → use cursor
- `--review=none` or `--review none` → skip review

If found, use that backend and skip all other detection.

### Otherwise: Phase 0 resolves it

No `--review` flag → `$BACKEND` comes from [workflow-common.md](workflow-common.md) Phase 0 (executed once per the Preamble): the single `flowctl review-backend "$SPEC_ID"` call with ASK handling included. Do not re-resolve here.

### Backend at a glance

When `RP_ELIGIBLE=0`, omit the **rp** line below from any guidance you surface (explicit `--review=rp` still honored):

- **rp** — RepoPrompt (macOS GUI); builder auto-selects context. Primary backend.
- **codex** — Codex CLI (cross-platform); uses OpenAI models (default `gpt-5.5`). `FLOW_CODEX_MODEL` / `FLOW_CODEX_EFFORT` env vars, or `--spec codex:gpt-5.4:xhigh`.
- **copilot** — GitHub Copilot CLI (cross-platform); supports Claude Opus/Sonnet/Haiku 4.5 and GPT-5.2 families via a Copilot subscription. `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, or `--spec copilot:claude-opus-4.5:xhigh`.
- **cursor** — Cursor CLI (`cursor-agent`, cross-platform); reaches `gpt-5.5-high` (1M-ctx default), the `gpt-5.3-codex` family, `composer-2.5`, and `claude-opus-4-8-thinking-high` via a Cursor subscription. `FLOW_CURSOR_MODEL` env var, or `--spec cursor:gpt-5.5-high`. Cursor folds reasoning effort into the model name — **no effort field**.

**Spec grammar:** `backend[:model[:effort]]` — `FLOW_REVIEW_BACKEND` and `.flow/config.json review.backend` both accept this. Examples: `codex`, `codex:gpt-5.2`, `copilot:claude-opus-4.5:xhigh`, `cursor:gpt-5.5-high` (cursor takes model only — no `:effort`). Per-spec `default_review` (set via `flowctl spec set-backend`) overrides env.

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

**For copilot backend:**
1. Use `$FLOWCTL copilot completion-review` exclusively
2. Pass `--receipt` for session continuity on re-reviews (session only resumes when prior receipt has `mode == "copilot"`)
3. Model + effort resolved via (first match wins): `--spec backend:model:effort` flag, per-spec `default_review`, `FLOW_REVIEW_BACKEND` spec, `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, registry defaults
4. Parse verdict from command output

**For cursor backend:**
1. Use `$FLOWCTL cursor completion-review` exclusively
2. Pass `--receipt` for session continuity on re-reviews (session only resumes when prior receipt has `mode == "cursor"`)
3. Model resolved via (first match wins): `--spec cursor:<model>` flag, per-spec `default_review`, `FLOW_REVIEW_BACKEND` spec, `FLOW_CURSOR_MODEL` env var, registry default (`gpt-5.5-high`). **No effort** — Cursor bakes effort into the model name; `cursor:<model>:<effort>` is rejected
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
Format: `<spec-id> [--review=rp|codex|copilot|cursor|none]`

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

### Step 1: Load Backend Workflow

1. `$BACKEND` was already resolved by workflow-common.md Phase 0 (Preamble) — do NOT re-run it.
2. Read **only** the file for that backend:

| `$BACKEND` | File to read |
|------------|--------------|
| `codex`    | [workflow-codex.md](workflow-codex.md) |
| `copilot`  | [workflow-copilot.md](workflow-copilot.md) |
| `cursor`   | [workflow-cursor.md](workflow-cursor.md) |
| `rp`       | [workflow-rp.md](workflow-rp.md) |

**Do not read the other backend files.** Each is self-contained for its backend; loading the others wastes context.

### Step 2: Execute the backend workflow

Follow the phases in the per-backend file end-to-end. Each file owns its own Identify → Execute → Verdict → Receipt steps (and, for RP, the full Phase 1-4 setup-review / chat-send / receipt build).

## Fix Loop (INTERNAL - do not exit to Ralph)

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is complete spec compliance. Never use AskUserQuestion in this loop.**

**MAX ITERATIONS (backend-agnostic — applies to ALL backends: rp, codex, copilot, cursor):** keep an iteration counter in agent context, starting at 0. Each fix+re-review cycle increments it. When the counter reaches **${MAX_REVIEW_ITERATIONS:-4}** (default 4; env-overridable, configurable in Ralph's config.env) and the verdict is still NEEDS_WORK, BREAK the loop and escalate: surface the surviving gaps to the caller and stop (in Ralph mode output `<promise>RETRY</promise>` so the next iteration starts fresh). Never loop unbounded. The per-backend workflow files defer to this cap.

If verdict is NEEDS_WORK, loop internally until SHIP or the iteration cap:

1. **Parse issues** from reviewer feedback (missing requirements, incomplete implementations)
2. **Fix code** and run tests/lints
3. **Commit fixes** (mandatory before re-review; RP backend uses the snapshot-scoped staging in workflow-rp.md — never blanket-stage with `git add --all`)
4. **Re-review**:
   - **Codex**: Re-run `flowctl codex completion-review` (receipt enables context)
   - **Copilot**: Re-run `flowctl copilot completion-review` (receipt enables context; must be `mode == "copilot"` to resume)
   - **Cursor**: Re-run `flowctl cursor completion-review` (receipt enables context; must be `mode == "cursor"` to resume)
   - **RP**: `$FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file <literal re-review path from workflow-rp.md's fix loop>` (NO `--new-chat`; stdout redirected to the same literal response file, Read once)
5. **Repeat** until `<verdict>SHIP</verdict>` — or the MAX ITERATIONS cap above breaks the loop (escalate with surviving gaps)

**CRITICAL**: For RP, re-reviews must stay in the SAME chat so reviewer has context. Only use `--new-chat` on the FIRST review.

## Step 3: Record the verdict (MANDATORY for rp / repair; handler-owned otherwise)

`flowctl <backend> completion-review` self-writes `completion_review_status` / `completion_reviewed_at` from the parsed verdict on codex/copilot/cursor (fn-112). **Without a write somewhere, a standalone completion review leaves `completion_review_status: unknown`, which keeps `flowctl ready --require-completion-review` demanding a review (pilot's gate), feeds make-pr's Open-items / draft heuristic stale state, and blocks tracker-sync's terminal `verified` rung.** The standalone command remains for rp and for repairing a missed write:

```bash
# Final verdict resolved to SHIP → ship; NEEDS_WORK at the iteration cap → needs_work.
# Skip when the backend handler already wrote status (codex/copilot/cursor).
$FLOWCTL spec set-completion-review-status "$SPEC_ID" --status ship --json        # on SHIP
$FLOWCTL spec set-completion-review-status "$SPEC_ID" --status needs_work --json  # on NEEDS_WORK at cap
```

On rp (or if the JSON payload lacks `plan_review_status`/`completion_review_status`), write on BOTH terminal paths (SHIP and capped-NEEDS_WORK).
