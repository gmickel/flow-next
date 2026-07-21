---
name: flow-next-plan-review
description: Carmack-level review of a flow-next spec or plan via the configured backend. Use when asked to review a plan or spec.
user-invocable: false
---

# Plan Review Mode

**Read [workflow.md](workflow.md) for detailed phases and anti-patterns.**

Conduct a John Carmack-level review of spec plans.

**Role**: Code Review Coordinator (NOT the reviewer)
**Backends** (branch on the Preamble `RP_ELIGIBLE` guard):
- When `RP_ELIGIBLE=1`: RepoPrompt (rp), Codex CLI (codex), GitHub Copilot CLI (copilot), or Cursor CLI (cursor)
- When `RP_ELIGIBLE=0`: Codex CLI (codex), GitHub Copilot CLI (copilot), or Cursor CLI (cursor) — rp is macOS-only; never list it in guidance you surface (`--review=rp` stays accepted)

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow.md`) use `$FLOWCTL`:

```bash
FLOWCTL="$HOME/.codex/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"

# RepoPrompt is macOS-only (rp-cli bridges the GUI). Only offer the rp path
# when it can actually run: on macOS, or when rp-cli is already on PATH.
if [ "$(uname 2>/dev/null)" = "Darwin" ] || command -v rp-cli >/dev/null 2>&1; then
 RP_ELIGIBLE=1
else
 RP_ELIGIBLE=0
fi
```

When `RP_ELIGIBLE=0` (not macOS, no rp-cli), never *steer* the user toward rp: every backend summary, recommendation, or override hint you surface presents only the runnable configured backends `codex`, `copilot`, `cursor` (plus `none`). `export` is an explicit one-off review MODE (`--review=export`), not a configured backend — never present it as one. Suppression is not a ban: an explicit `--review=rp`, `FLOW_REVIEW_BACKEND=rp`, or `review.backend=rp` still resolves to rp and errors at runtime via `require_rp_cli()` as today.

## Backend Selection

**Priority** (first match wins):
1. `--review=rp|codex|copilot|cursor|export|none` argument
2. `FLOW_REVIEW_BACKEND` env var — bare backend (`rp`, `codex`, `copilot`, `cursor`, `none`) OR spec form (`codex:gpt-5.4:xhigh`, `copilot:claude-opus-4.5`, `cursor:gpt-5.5-high`)
3. `.flow/config.json` → `review.backend` (same bare / spec forms)
4. **Error** - no auto-detection

### Parse from arguments first

Check $ARGUMENTS for:
- `--review=rp` or `--review rp` → use rp
- `--review=codex` or `--review codex` → use codex
- `--review=copilot` or `--review copilot` → use copilot
- `--review=cursor` or `--review cursor` → use cursor
- `--review=export` or `--review export` → use export
- `--review=none` or `--review none` → skip review

If found, use that backend and skip all other detection.

### Otherwise read from config

```bash
# Priority: --review flag > per-spec `default_review` override > env > config.
# Resolve the spec id from $ARGUMENTS FIRST so a per-spec `default_review` override routes to the
# right backend BEFORE branching (empty → env/config, no regression). `$1` is the positional spec
# arg — the backend blocks below reuse it as `SPEC_ID`.
SPEC_ID="${1:-}" # the spec-id positional arg (canonicalized by review-backend); empty falls back to env/config
BACKEND=$($FLOWCTL review-backend "$SPEC_ID")

if [[ "$BACKEND" == "ASK" ]]; then
 echo "Error: No review backend configured."
 if [ "$RP_ELIGIBLE" = 1 ]; then
 echo "Run /flow-next:setup to configure, or pass --review=rp|codex|copilot|cursor|none"
 else
 echo "Run /flow-next:setup to configure, or pass --review=codex|copilot|cursor|none"
 fi
 exit 1
fi

if [ "$RP_ELIGIBLE" = 1 ]; then
 echo "Review backend: $BACKEND (override: --review=rp|codex|copilot|cursor|none)"
else
 echo "Review backend: $BACKEND (override: --review=codex|copilot|cursor|none)"
fi
```

### Backend at a glance

When `RP_ELIGIBLE=0`, omit the **rp** line below from any guidance you surface (explicit `--review=rp` still honored):

- **rp** — RepoPrompt (macOS GUI); builder auto-selects context. Primary backend.
- **codex** — Codex CLI (cross-platform); uses OpenAI models (default `gpt-5.5`). `FLOW_CODEX_MODEL` / `FLOW_CODEX_EFFORT` env vars, or `--spec codex:gpt-5.4:xhigh`.
- **copilot** — GitHub Copilot CLI (cross-platform); supports Claude Opus/Sonnet/Haiku 4.5 and GPT-5.2 families via a Copilot subscription. `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, or `--spec copilot:claude-opus-4.5:xhigh`.
- **cursor** — Cursor CLI (`cursor-agent`, cross-platform); reaches `gpt-5.5-high` (1M-ctx default), the `gpt-5.3-codex` family, `composer-2.5`, and `claude-opus-4-8-thinking-high` via a Cursor subscription. `FLOW_CURSOR_MODEL` env var, or `--spec cursor:gpt-5.5-high`. Cursor folds reasoning effort into the model name — **no effort field**.

**Spec grammar:** `backend[:model[:effort]]` — `FLOW_REVIEW_BACKEND` and `.flow/config.json review.backend` both accept this. Examples: `codex`, `codex:gpt-5.2`, `copilot:claude-opus-4.5:xhigh`, `cursor:gpt-5.5-high` (cursor takes model only — no `:effort`). Per-spec `default_review` (set via `flowctl spec set-backend`) overrides env.

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

**For copilot backend:**
1. Use `$FLOWCTL copilot plan-review` exclusively
2. Pass `--receipt` for session continuity on re-reviews (session only resumes when prior receipt has `mode == "copilot"`)
3. Model + effort resolved via (first match wins): `--spec backend:model:effort` flag, per-spec `default_review`, `FLOW_REVIEW_BACKEND` spec, `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, registry defaults
4. Parse verdict from command output

**For cursor backend:**
1. Use `$FLOWCTL cursor plan-review` exclusively (requires `--files <code files>`, same as codex/copilot)
2. Pass `--receipt` for session continuity on re-reviews (session only resumes when prior receipt has `mode == "cursor"`)
3. Model resolved via (first match wins): `--spec cursor:<model>` flag, per-spec `default_review`, `FLOW_REVIEW_BACKEND` spec, `FLOW_CURSOR_MODEL` env var, registry default (`gpt-5.5-high`). **No effort** — Cursor bakes effort into the model name; `cursor:<model>:<effort>` is rejected
4. Parse verdict from command output

**For all backends:**
- If `REVIEW_RECEIPT_PATH` set: write receipt after review (any verdict)
- Any failure → output `<promise>RETRY</promise>` and stop
- **Foreground rule:** run every `flowctl <backend> plan-review` call as one **blocking foreground** Bash call with a generous timeout (10 minutes; verdicts typically land in 1–7) — never `run_in_background` + monitor/poll (a background completion does not reliably resume a subagent context)

**FORBIDDEN**:
- Self-declaring SHIP without actual backend verdict
- Mixing backends mid-review (stick to one)
- Skipping review when backend is "none" without user consent

## Input

Arguments: $ARGUMENTS
Format: `<flow-spec-id> [focus areas]`

## Workflow

**See [workflow.md](workflow.md) for full details on each backend.**

```bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

### Step 0: Detect Backend

Run backend detection from SKILL.md above. Then branch:

### Codex / Copilot / Cursor Backends

**⚠️ STOP: You MUST read and execute [workflow.md](workflow.md) now.** The per-backend execution blocks are single-sourced there (fn-110) — go to the matching "Codex Backend Workflow" / "Copilot Backend Workflow" / "Cursor Backend Workflow" section and execute it. Do not reconstruct the commands from memory here.

Each workflow is ONE atomic dispatch fence (checkpoint + spec id + receipt path + `CODE_FILES` reviewer anchors + `$FLOWCTL <backend> plan-review …`; Foreground rule applies) → update status → RETURN the verdict here. The workflow files never loop — the Fix Loop below is the single owner of NEEDS_WORK handling, MAJOR_RETHINK escalation, and the fn-90 deterministic cap.

**Return here only after workflow.md execution is complete.**

### RepoPrompt Backend

**⚠️ STOP: You MUST read and execute [workflow.md](workflow.md) now.**

Go to the "RepoPrompt Backend Workflow" section in workflow.md and execute those steps. Do not proceed here until workflow.md phases are complete.

The workflow covers:
1. Get plan content and save checkpoint
2. Atomic setup (setup-review (5-15 min, DO NOT RETRY)) → sets `$W` and `$T`
3. Augment selection (spec + task specs)
4. Send review and parse verdict

**Return here only after workflow.md execution is complete.**

## Fix Loop (INTERNAL - do not exit to Ralph)

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is production-grade world-class software and architecture. Never use the plain-text numbered prompt in this loop.**

**MAJOR_RETHINK is NOT a fix-loop input.** Every backend can emit `MAJOR_RETHINK` (a valid verdict tag), but it means the *plan/approach* is wrong — not something to patch finding-by-finding. Do NOT enter the fix loop on it. Escalate immediately: surface the reviewer's rationale to the caller and stop with a typed **`BLOCKED: DESIGN_CONFLICT`** (Ralph mode: output `<promise>RETRY</promise>`). A re-plan is a human decision, never an ad-hoc patch. Only `NEEDS_WORK` drives the loop below.

**MAX ITERATIONS (backend-agnostic — applies to ALL backends: rp, codex, copilot, cursor):** fix+re-review cycles are bounded at **${MAX_REVIEW_ITERATIONS:-4}** (default 4; env-overridable, configurable in Ralph's config.env) — the counter is flowctl-owned (below), never kept in agent context. When the cap is reached and the verdict is still NEEDS_WORK, BREAK the loop and escalate: surface the surviving findings to the caller and stop (in Ralph mode output `<promise>RETRY</promise>` so the next iteration starts fresh). Never loop unbounded. The per-backend workflow files defer to this cap. **The cap is now ALSO enforced deterministically by flowctl (fn-90 R5): each `flowctl <backend> plan-review` dispatch increments a cumulative spec-scoped counter (`plan_review_rounds`) and REFUSES at `${MAX_REVIEW_ITERATIONS:-4}` with an `ESCALATE:` marker + exit 4 — the flowctl counter survives across fresh `/flow-next:plan-review` invocations, so a caller-side "re-invoke until SHIP" outer loop can no longer reset the cap by re-entering. This loop is INTERNAL — the caller (e.g. `/flow-next:plan`, pilot) invokes plan-review ONCE and acts on the terminal verdict; the flowctl counter resets ONLY on a SHIP verdict or an explicit re-plan (`flowctl spec reset-review-rounds <spec-id>`), never on a fresh invocation or a spec edit.**

If verdict is NEEDS_WORK, loop internally until SHIP or the iteration cap:

1. **Parse issues** from reviewer feedback
2. **Fix spec** (stdin preferred, temp file if content has single quotes):
 ```bash
 # Preferred: stdin heredoc
 $FLOWCTL spec set-plan <SPEC_ID> --file - --json <<'EOF'
 <updated spec content>
 EOF

 # Or temp file — literal unique path per the path-persistence rule
 $FLOWCTL spec set-plan <SPEC_ID> --file "${TMPDIR:-/tmp}/flow-plan-review-updated-plan-<spec-id>-<suffix>.md" --json
 ```
3. **Sync affected task specs** - If spec changes affect task specs, update them:
 ```bash
 $FLOWCTL task set-spec <TASK_ID> --file - --json <<'EOF'
 <updated task spec content>
 EOF
 ```
 Task specs need updating when spec changes affect:
 - State/enum values referenced in tasks
 - Acceptance criteria that tasks implement
 - Approach/design decisions tasks depend on
 - Lock/retry/error handling semantics
 - API signatures or type definitions
4. **Re-review**:
 - **Codex**: Re-run `flowctl codex plan-review` (receipt enables context)
 - **Copilot**: Re-run `flowctl copilot plan-review` (receipt enables context; must be `mode == "copilot"` to resume)
 - **Cursor**: Re-run `flowctl cursor plan-review` (receipt enables context; must be `mode == "cursor"` to resume)
 - **RP**: `$FLOWCTL rp chat-send (2-10 min, DO NOT RETRY) --window "$W" --tab "$T" --message-file <literal re-review path from workflow.md's fix loop>` (NO `--new-chat`; stdout redirected to the same literal response file, Read once)
5. **Repeat** until `<verdict>SHIP</verdict>` — or the MAX ITERATIONS cap above breaks the loop (escalate with surviving findings)

**Recovery**: If context compaction occurred during review, restore from checkpoint:
```bash
$FLOWCTL checkpoint restore --spec <SPEC_ID> --json
```

**CRITICAL**: For RP, re-reviews must stay in the SAME chat so reviewer has context. Only use `--new-chat` on the FIRST review.
