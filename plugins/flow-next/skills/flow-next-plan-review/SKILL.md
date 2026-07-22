---
name: flow-next-plan-review
description: Carmack-level plan review via RepoPrompt or Codex. Use when reviewing Flow specs or design docs. Triggers on /flow-next:plan-review.
user-invocable: false
---

# Plan Review Mode

**Read [workflow.md](workflow.md) for detailed phases and anti-patterns.**

Conduct a John Carmack-level review of spec plans.

**Role**: Code Review Coordinator (NOT the reviewer)
**Backends** (branch on the Preamble `RP_ELIGIBLE` guard):
- When `RP_ELIGIBLE=1`: RepoPrompt (rp), Codex CLI (codex), GitHub Copilot CLI (copilot), Cursor CLI (cursor), or host-native (`host`)
- When `RP_ELIGIBLE=0`: Codex CLI (codex), GitHub Copilot CLI (copilot), Cursor CLI (cursor), or host-native (`host`) — rp is macOS-only; never list it in guidance you surface (`--review=rp` stays accepted)

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow.md`) use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"

# Prefer RepoPrompt CE; retain Classic only as the final compatibility rung.
if command -v rpce-cli >/dev/null 2>&1 \
  || [ -x "$HOME/RepoPrompt/repoprompt_ce_cli" ] \
  || [ -x "$HOME/Library/Application Support/RepoPrompt CE/repoprompt_ce_cli" ] \
  || command -v rp-cli >/dev/null 2>&1; then
  RP_ELIGIBLE=1
else
  RP_ELIGIBLE=0
fi
```

When `RP_ELIGIBLE=0` (not macOS, no supported RepoPrompt CLI), never *steer* the user toward rp: every backend summary, recommendation, or override hint you surface presents only the runnable configured backends `codex`, `copilot`, `cursor`, `host` (plus `none`). `export` is an explicit one-off review MODE (`--review=export`), not a configured backend — never present it as one. Suppression is not a ban: an explicit `--review=rp`, `FLOW_REVIEW_BACKEND=rp`, or `review.backend=rp` still resolves to rp and errors at runtime via `require_rp_cli()`.

## Backend Selection

**Priority** (first match wins):
1. `--review=rp|codex|copilot|cursor|host|export|none` argument
2. `FLOW_REVIEW_BACKEND` env var — bare backend (`rp`, `codex`, `copilot`, `cursor`, `host`, `none`) OR spec form (`codex:gpt-5.4:xhigh`, `copilot:claude-opus-4.5`, `cursor:gpt-5.5-high`); `host` is bare-only (`host:<model>` is rejected)
3. `.flow/config.json` → `review.backend` (same bare / spec forms)
4. **Error** - no auto-detection

### Parse from arguments first

Check $ARGUMENTS for:
- `--review=rp` or `--review rp` → use rp
- `--review=codex` or `--review codex` → use codex
- `--review=copilot` or `--review copilot` → use copilot
- `--review=cursor` or `--review cursor` → use cursor
- `--review=host` or `--review host` → use host
- `--review=export` or `--review export` → use export
- `--review=none` or `--review none` → skip review

If found, use that backend and skip all other detection.

### Otherwise read from config

```bash
# Priority: --review flag > per-spec `default_review` override > env > config.
# Resolve the spec id from $ARGUMENTS FIRST so a per-spec `default_review` override routes to the
# right backend BEFORE branching (empty → env/config, no regression). `$1` is the positional spec
# arg — the backend blocks below reuse it as `SPEC_ID`.
SPEC_ID="${1:-}"   # the spec-id positional arg (canonicalized by review-backend); empty falls back to env/config
BACKEND=$($FLOWCTL review-backend "$SPEC_ID")

if [[ "$BACKEND" == "ASK" ]]; then
  echo "Error: No review backend configured."
  if [ "$RP_ELIGIBLE" = 1 ]; then
    echo "Run /flow-next:setup to configure, or pass --review=rp|codex|copilot|cursor|host|none"
  else
    echo "Run /flow-next:setup to configure, or pass --review=codex|copilot|cursor|host|none"
  fi
  exit 1
fi

if [ "$RP_ELIGIBLE" = 1 ]; then
  echo "Review backend: $BACKEND (override: --review=rp|codex|copilot|cursor|host|none)"
else
  echo "Review backend: $BACKEND (override: --review=codex|copilot|cursor|host|none)"
fi
```

### Backend at a glance

When `RP_ELIGIBLE=0`, omit the **rp** line below from any guidance you surface (explicit `--review=rp` still honored):

- **rp** — RepoPrompt (macOS GUI); builder auto-selects context. Primary backend.
- **codex** — Codex CLI (cross-platform); uses OpenAI models (default `gpt-5.5`). `FLOW_CODEX_MODEL` / `FLOW_CODEX_EFFORT` env vars, or `--spec codex:gpt-5.4:xhigh`.
- **copilot** — GitHub Copilot CLI (cross-platform); supports Claude Opus/Sonnet/Haiku 4.5 and GPT-5.2 families via a Copilot subscription. `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, or `--spec copilot:claude-opus-4.5:xhigh`.
- **cursor** — Cursor CLI (`cursor-agent`, cross-platform); reaches `gpt-5.5-high` (1M-ctx default), the `gpt-5.3-codex` family, `composer-2.5`, and `claude-opus-4-8-thinking-high` via a Cursor subscription. `FLOW_CURSOR_MODEL` env var, or `--spec cursor:gpt-5.5-high`. Cursor folds reasoning effort into the model name — **no effort field**.
- **host** — Host-native fresh-context reviewer subagent (fn-123 R5). Non-executable selection sentinel: no subprocess, no `flowctl host` command. Model pins live in the AGENTS.md model-routing section (caller routing instructions), never on the backend string — bare `host` only; `host:<model>` is rejected.

**Spec grammar:** `backend[:model[:effort]]` — `FLOW_REVIEW_BACKEND` and `.flow/config.json review.backend` both accept this. Examples: `codex`, `codex:gpt-5.2`, `copilot:claude-opus-4.5:xhigh`, `cursor:gpt-5.5-high` (cursor takes model only — no `:effort`), `host` (bare only). Per-spec `default_review` (set via `flowctl spec set-backend`) overrides env.

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
3. Model + effort resolved via (first match wins): `--spec backend:model:effort` flag, per-spec `default_review`, `FLOW_REVIEW_BACKEND` spec, `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, registry defaults
4. Parse verdict from command output

**For cursor backend:**
1. Use `$FLOWCTL cursor plan-review` exclusively (requires `--files <code files>`, same as codex/copilot)
2. Pass `--receipt` for session continuity on re-reviews (session only resumes when prior receipt has `mode == "cursor"`)
3. Model resolved via (first match wins): `--spec cursor:<model>` flag, per-spec `default_review`, `FLOW_REVIEW_BACKEND` spec, `FLOW_CURSOR_MODEL` env var, registry default (`gpt-5.5-high`). **No effort** — Cursor bakes effort into the model name; `cursor:<model>:<effort>` is rejected
4. Parse verdict from command output

**For host backend (fn-123 R5):**
1. **DO NOT REVIEW THE PLAN YOURSELF** — you coordinate; a fresh-context host-native subagent reviews
2. Dispatch a **read-only** reviewer subagent pinned to a **cross-family** model slug (family that did not write the plan) from the AGENTS.md model-routing section:
   - **Claude Code**: native subagent `model` param (existing reviewer-subagent arrangement)
   - **Cursor**: in-prompt slug pin on the subagent (host honors Cursor slugs)
   - **Other hosts**: generic fresh-context reviewer with an explicit note that the pin is best-effort / host-dependent
3. Reuse the existing plan-review rubrics + prior-finding convergence context (same verdict grammar as other backends)
4. Write receipt with actual reviewer model + `"mode": "host"` (shape compatible with existing convergence/cap/pilot/land consumers)
5. **Every re-review is a fresh subagent** — no context reuse, no fabricated resume ids
6. **Fail closed on missing cross-family pin:** interactive → ask the user explicitly which model/family to use; autonomous (`mode:autonomous` / `FLOW_AUTONOMOUS=1` / Ralph) → return `NEEDS_HUMAN` (never silent same-family self-review)

**For all backends:**
- If `REVIEW_RECEIPT_PATH` set: write receipt after review (any verdict)
- Any failure → output `<promise>RETRY</promise>` and stop
- **Foreground rule:** run every `flowctl <backend> plan-review` call as one **blocking foreground** Bash call with a generous timeout (10 minutes; verdicts typically land in 1–7) — never `run_in_background` + monitor/poll (a background completion does not reliably resume a subagent context). Host-backend subagent dispatches are also blocking (wait for the subagent result).

**FORBIDDEN**:
- Self-declaring SHIP without actual backend verdict
- Mixing backends mid-review (stick to one)
- Skipping review when backend is "none" without user consent
- Silent same-family self-review under `host` when no cross-family pin is available

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

### Host Backend (fn-123 R5)

When `BACKEND="host"`, do **not** call any `flowctl <backend> plan-review` — there is no subprocess path. Execute the host branch here:

1. **Resolve cross-family pin** from the AGENTS.md model-routing section (review role / cross-family pairing). Identify the family that wrote the plan and pick a reviewer slug from a *different* family.
2. **Fail closed** if no cross-family pin is available:
   - Interactive: ask the user explicitly (blocking question) which reviewer model/family to use — do not silently self-review
   - Autonomous / Ralph: stop with `NEEDS_HUMAN: host review needs a cross-family model pin in AGENTS.md model-routing` (never same-family self-review)
3. **Dispatch** a fresh read-only reviewer subagent with the pin:
   - Claude Code: `Task` / subagent with `model: <cross-family-slug>`, `disallowedTools: Edit, Write, Task` (or host equivalent read-only)
   - Cursor: subagent with the slug stated in the prompt (Cursor honors in-prompt model pins)
   - Elsewhere: fresh-context reviewer; note in the receipt that pin enforcement is host-dependent
4. Give the subagent the plan-review rubric ([references/plan-review-prompt.md](references/plan-review-prompt.md)), the spec content, and any prior findings for convergence. Require the same verdict tags (`SHIP` / `NEEDS_WORK` / `MAJOR_RETHINK`).
5. **Receipt** — path `RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/plan-review-receipt${SPEC_ID:+-${SPEC_ID}}.json}"` (explicit env always wins). Write exactly:

   ```json
   {
     "type": "plan_review",
     "id": "<spec-id>",
     "mode": "host",
     "verdict": "<SHIP|NEEDS_WORK|MAJOR_RETHINK>",
     "model": "<actual-reviewer-slug>",
     "spec": "host",
     "session_id": null,
     "timestamp": "<ISO-8601>"
   }
   ```

   `session_id` is literal `null` — every re-review is a new subagent; `null` marks by-design non-resumability (vs an incomplete receipt).
6. **Status write:** `$FLOWCTL spec set-plan-review-status "$SPEC_ID" --status ship|needs_work --json` as appropriate (host has no handler-owned write).
7. Return the verdict to the Fix Loop below. On re-review, spawn a **new** subagent every time (no context reuse).

### RepoPrompt Backend

**⚠️ STOP: You MUST read and execute [workflow.md](workflow.md) now.**

Go to the "RepoPrompt Backend Workflow" section in workflow.md and execute those steps. Do not proceed here until workflow.md phases are complete.

The workflow covers:
1. Get plan content and save checkpoint
2. Atomic setup (setup-review) → sets `$W` and `$T`
3. Augment selection (spec + task specs)
4. Send review and parse verdict

**Return here only after workflow.md execution is complete.**

## Fix Loop (INTERNAL - do not exit to Ralph)

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is production-grade world-class software and architecture. Never use AskUserQuestion in this loop.**

**MAJOR_RETHINK is NOT a fix-loop input.** Every backend can emit `MAJOR_RETHINK` (a valid verdict tag), but it means the *plan/approach* is wrong — not something to patch finding-by-finding. Do NOT enter the fix loop on it. Escalate immediately: surface the reviewer's rationale to the caller and stop with a typed **`BLOCKED: DESIGN_CONFLICT`** (Ralph mode: output `<promise>RETRY</promise>`). A re-plan is a human decision, never an ad-hoc patch. Only `NEEDS_WORK` drives the loop below.

**MAX ITERATIONS (backend-agnostic — applies to ALL backends: rp, codex, copilot, cursor, host):** fix+re-review cycles are bounded at **${MAX_REVIEW_ITERATIONS:-4}** (default 4; env-overridable, configurable in Ralph's config.env) — the counter is flowctl-owned (below), never kept in agent context. When the cap is reached and the verdict is still NEEDS_WORK, BREAK the loop and escalate: surface the surviving findings to the caller and stop (in Ralph mode output `<promise>RETRY</promise>` so the next iteration starts fresh). Never loop unbounded. The per-backend workflow files defer to this cap. **The cap is now ALSO enforced deterministically by flowctl (fn-90 R5): each `flowctl <backend> plan-review` dispatch increments a cumulative spec-scoped counter (`plan_review_rounds`) and REFUSES at `${MAX_REVIEW_ITERATIONS:-4}` with an `ESCALATE:` marker + exit 4 — the flowctl counter survives across fresh `/flow-next:plan-review` invocations, so a caller-side "re-invoke until SHIP" outer loop can no longer reset the cap by re-entering. This loop is INTERNAL — the caller (e.g. `/flow-next:plan`, pilot) invokes plan-review ONCE and acts on the terminal verdict; the flowctl counter resets ONLY on a SHIP verdict or an explicit re-plan (`flowctl spec reset-review-rounds <spec-id>`), never on a fresh invocation or a spec edit.** On **host**, there is no flowctl dispatch counter — keep the in-agent iteration counter and call `$FLOWCTL review-rounds increment <spec-id> --kind plan` before each host re-review dispatch when available (same cap semantics).

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
   - **Host**: Spawn a **fresh** read-only reviewer subagent (same cross-family pin rules; never reuse prior subagent context; update receipt `mode: "host"` + actual model)
   - **RP**: `$FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file <literal re-review path from workflow.md's fix loop>` (NO `--new-chat`; stdout redirected to the same literal response file, Read once)
5. **Repeat** until `<verdict>SHIP</verdict>` — or the MAX ITERATIONS cap above breaks the loop (escalate with surviving findings)

**Recovery**: If context compaction occurred during review, restore from checkpoint:
```bash
$FLOWCTL checkpoint restore --spec <SPEC_ID> --json
```

**CRITICAL**: For RP, re-reviews must stay in the SAME chat so reviewer has context. Only use `--new-chat` on the FIRST review.
