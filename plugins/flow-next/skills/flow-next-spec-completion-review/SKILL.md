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
- `BACKEND=host` → [workflow-host.md](workflow-host.md)
- `BACKEND=rp` → [workflow-rp.md](workflow-rp.md)

Do not load the others — only the active backend's file is needed.

Verify that the combined implementation of all tasks in a spec satisfies the spec requirements. This is NOT a code quality review (that's impl-review's job) — this confirms spec compliance only.

**Role**: Spec Completion Review Coordinator (NOT the reviewer)
**Backends** (branch on the Phase 0 `RP_ELIGIBLE` probe):
- When `RP_ELIGIBLE=1`: RepoPrompt (rp), Codex CLI (codex), GitHub Copilot CLI (copilot), Cursor CLI (cursor), or host-native (`host`)
- When `RP_ELIGIBLE=0`: Codex CLI (codex), GitHub Copilot CLI (copilot), Cursor CLI (cursor), or host-native (`host`) — rp is macOS-only; never list it in guidance you surface (`--review=rp` stays accepted)

## Preamble — execute Phase 0 exactly once

**The executable Phase 0 lives in [workflow-common.md](workflow-common.md) §"Phase 0: Backend Detection" — Read it and execute it ONCE, before any other bash in this skill.** It defines `$FLOWCTL` (bundled — NOT installed globally; `which flowctl` fails, expected), probes `RP_ELIGIBLE`, resolves `$BACKEND` via the single `flowctl review-backend` call, and handles the ASK / `none` cases. Never invoke `flowctl review-backend` a second time in the same run.

Exception: a `--review=<backend>` argument (see Backend Selection below) wins — when present, set `BACKEND` from the flag and skip Phase 0's `review-backend` call + ASK handling (still run its `$FLOWCTL` / `RP_ELIGIBLE` setup lines).

When `RP_ELIGIBLE=0` (not macOS, no supported RepoPrompt CLI), never *steer* the user toward rp: every backend summary, recommendation, or override hint you surface presents only the runnable configured backends `codex`, `copilot`, `cursor`, `host` (plus `none`). Suppression is not a ban: an explicit `--review=rp`, `FLOW_REVIEW_BACKEND=rp`, or `review.backend=rp` still resolves to rp and errors at runtime via `require_rp_cli()`.

## Backend Selection

**Priority** (first match wins):
1. `--review=rp|codex|copilot|cursor|host|none` argument
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
- **host** — Bare-only non-executable selection sentinel; selected mechanics
  live in [workflow-host.md](workflow-host.md).

**Spec grammar:** `backend[:model[:effort]]` — `FLOW_REVIEW_BACKEND` and `.flow/config.json review.backend` both accept this. Examples: `codex`, `codex:gpt-5.2`, `copilot:claude-opus-4.5:xhigh`, `cursor:gpt-5.5-high` (cursor takes model only — no `:effort`), `host` (bare only). Per-spec `default_review` (set via `flowctl spec set-backend`) overrides env.

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

**For host backend (fn-123 R5 / fn-126):**
`host` is bare-only. After selection, read [workflow-host.md](workflow-host.md).
The review must use a fresh, tool-enforced read-only reviewer from a different
model family and fail closed when no cross-family pin is available.

**For all backends:**
- If `REVIEW_RECEIPT_PATH` set: write receipt after SHIP verdict (RP writes manually after fix loop; codex writes automatically via `--receipt`)
- Any failure → output `<promise>RETRY</promise>` and stop. No-verdict
  transport failures are recorded and their reserved round refunded; never
  manually reset the review counter. Exit 5 / `TRANSPORT_UNHEALTHY` stops
  automatic retries until the backend is repaired.

**FORBIDDEN**:
- Self-declaring SHIP without actual backend verdict
- Mixing backends mid-review (stick to one)
- Skipping review silently (must inform user and exit cleanly when backend is "none")

## Input

Arguments: $ARGUMENTS
Format: `<spec-id> [--review=rp|codex|copilot|cursor|host|none]`

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

### Step 0.5: Resume terminal status persistence before dispatch

Run this checkpoint after parsing `SPEC_ID` and **before** loading or dispatching
any backend. Run the same checkpoint again immediately after host/rp records a
verdict. It recovers a terminal status write that failed after the verdict round
was durably consumed, without reserving or dispatching another review.
This shared step is the sole writer for host and rp terminal status.

```bash
if ! TERMINAL_REVIEW_JSON="$($FLOWCTL review-rounds attempts "$SPEC_ID" \
  --kind plan --review-type completion --json)" \
  || ! SPEC_STATE_JSON="$($FLOWCTL show "$SPEC_ID" --json)"; then
  echo "<promise>RETRY</promise>"
  exit 0
fi

LATEST_OUTCOME="$(printf '%s' "$TERMINAL_REVIEW_JSON" \
  | jq -r '.attempts[-1].outcome // ""')"
VERDICT="$(printf '%s' "$TERMINAL_REVIEW_JSON" \
  | jq -r '.attempts[-1].verdict // ""')"
ATTEMPT_BACKEND="$(printf '%s' "$TERMINAL_REVIEW_JSON" \
  | jq -r '.attempts[-1].backend // ""')"
ATTEMPT_AT="$(printf '%s' "$TERMINAL_REVIEW_JSON" \
  | jq -r '.attempts[-1].timestamp // ""')"
REVIEW_ROUND="$(printf '%s' "$TERMINAL_REVIEW_JSON" \
  | jq -r '.review_rounds // 0')"
REVIEW_CAP="$(printf '%s' "$TERMINAL_REVIEW_JSON" \
  | jq -r '.review_rounds_cap // 0')"
CURRENT_STATUS="$(printf '%s' "$SPEC_STATE_JSON" \
  | jq -r '.completion_review_status // "unknown"')"
CURRENT_REVIEWED_AT="$(printf '%s' "$SPEC_STATE_JSON" \
  | jq -r '.completion_reviewed_at // ""')"

TERMINAL_STATUS=""
TERMINAL_EXIT=0
if [[ "$LATEST_OUTCOME" == "verdict" && "$VERDICT" == "SHIP" ]]; then
  TERMINAL_STATUS="ship"
elif [[ "$LATEST_OUTCOME" == "verdict" \
  && "$VERDICT" == "NEEDS_WORK" \
  && "$REVIEW_CAP" -gt 0 \
  && "$REVIEW_ROUND" -ge "$REVIEW_CAP" ]]; then
  TERMINAL_STATUS="needs_work"
  TERMINAL_EXIT=4
fi

# A matching status means the terminal already persisted. A newer terminal
# attempt means persistence is pending. A newer completion_reviewed_at is an
# explicit later status decision (for example `unknown` to request re-review);
# honor it instead of resurrecting the old verdict.
if [[ -n "$TERMINAL_STATUS" \
  && ( "$CURRENT_STATUS" == "$TERMINAL_STATUS" \
    || ( -n "$ATTEMPT_AT" \
      && ( -z "$CURRENT_REVIEWED_AT" \
        || "$ATTEMPT_AT" > "$CURRENT_REVIEWED_AT" ) ) ) ]]; then
  RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/completion-review-receipt-${SPEC_ID}.json}"
  RECEIPT_RECOVERY="$REPO_ROOT/.flow/tmp/completion-review-receipt-recovery-${SPEC_ID}.json"
  RECEIPT_REQUIRED=false
  # Bind evidence requirements to the durable attempt being resumed, never
  # the backend selected for this invocation (which may have changed).
  case "$ATTEMPT_BACKEND" in
    codex|copilot|cursor|host) RECEIPT_REQUIRED=true ;;
    rp)
      [[ "$VERDICT" == "SHIP" \
        && ( -n "${REVIEW_RECEIPT_PATH:-}" || -f "$RECEIPT_RECOVERY" ) ]] \
        && RECEIPT_REQUIRED=true
      ;;
  esac

  # Every receipt-owning backend preserves the complete payload here before
  # writing the caller-selected path. Restore it before status so a transient
  # receipt-path failure never consumes another review or loses Ralph evidence.
  if [[ -f "$RECEIPT_RECOVERY" ]]; then
    mkdir -p "$(dirname "$RECEIPT_PATH")"
    cp "$RECEIPT_RECOVERY" "$RECEIPT_PATH"
    if ! jq -e --arg id "$SPEC_ID" --arg verdict "$VERDICT" \
      '.type == "completion_review"
       and .id == $id
       and .verdict == $verdict' "$RECEIPT_PATH" >/dev/null; then
      echo "<promise>RETRY</promise>"
      exit 0
    fi
    rm "$RECEIPT_RECOVERY"
  fi

  if [[ "$RECEIPT_REQUIRED" == true ]] \
    && ! jq -e --arg id "$SPEC_ID" --arg verdict "$VERDICT" \
      '.type == "completion_review"
       and .id == $id
       and .verdict == $verdict' "$RECEIPT_PATH" >/dev/null 2>&1; then
    echo "<promise>RETRY</promise>"
    exit 0
  fi

  if [[ "$CURRENT_STATUS" != "$TERMINAL_STATUS" ]]; then
    TERMINAL_WRITE_JSON="$($FLOWCTL spec set-completion-review-status "$SPEC_ID" \
      --status "$TERMINAL_STATUS" --json)"
    TERMINAL_WRITE_EXIT=$?
    printf '%s\n' "$TERMINAL_WRITE_JSON"
    if [[ "$TERMINAL_WRITE_EXIT" -ne 0 ]]; then
      echo "<promise>RETRY</promise>"
      exit 0
    fi
  fi

  if [[ "$TERMINAL_EXIT" -eq 4 ]]; then
    echo "ESCALATE: completion-review did not converge in ${REVIEW_CAP} verdict rounds"
    exit 4
  fi
  echo "VERDICT=SHIP"
  exit 0
fi
```

### Step 1: Load Backend Workflow

1. `$BACKEND` was already resolved by workflow-common.md Phase 0 (Preamble) — do NOT re-run it.
2. Read **only** the file for that backend:

| `$BACKEND` | File to read |
|------------|--------------|
| `codex`    | [workflow-codex.md](workflow-codex.md) |
| `copilot`  | [workflow-copilot.md](workflow-copilot.md) |
| `cursor`   | [workflow-cursor.md](workflow-cursor.md) |
| `host`     | [workflow-host.md](workflow-host.md) |
| `rp`       | [workflow-rp.md](workflow-rp.md) |

**Do not read the other backend files.** Each is self-contained for its backend; loading the others wastes context.

### Step 2: Execute the backend workflow

Follow the phases in the per-backend file end-to-end. Each file owns its own Identify → Execute → Verdict → Receipt steps (and, for RP, the full Phase 1-4 setup-review / chat-send / receipt build).

## Fix Loop (INTERNAL - do not exit to Ralph)

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is complete spec compliance. Never use AskUserQuestion in this loop.**

**MAX ITERATIONS (backend-agnostic — rp, codex, copilot, cursor, host):**
The codex/copilot/cursor handlers reserve a round before dispatch; the selected
rp/host workflows call the same `review-rounds` reserve/record surface.
Verdict-bearing attempts consume the reservation; no-verdict transport failures
are recorded and refunded.

When a delivered `NEEDS_WORK` consumes round
`${MAX_REVIEW_ITERATIONS:-4}`, it is the terminal capped verdict:

- codex/copilot/cursor already self-wrote `needs_work` while handling that
  verdict; do not duplicate it.
- host/rp continue to Step 3 immediately, write `needs_work` exactly once, then
  emit `ESCALATE:` and exit 4. Do not attempt another reserve/dispatch first.

An exit-4 cap refusal before this run has delivered a completion verdict is
non-terminal for completion status: surface `ESCALATE:` / `NEEDS_HUMAN` and do
not invent a `needs_work` write. More than
`${MAX_REVIEW_TRANSPORT_FAILURES:-2}` consecutive transport failures stop
separately with `TRANSPORT_UNHEALTHY` + exit 5; never write completion status or
reset the verdict counter for transport health.

**ANTI-PATTERN (never do either):** (1) a delivered verdict is never a
transport failure. Once flowctl parses `VERDICT=...` the round is consumed and
recorded; do not re-dispatch or re-frame a `NEEDS_WORK` as a backend/sandbox
problem to claim a refund. (2) Never widen the reviewer sandbox. Reviewers are
read-only by contract; a sandbox-blocked reviewer means something asked it to
mutate the workspace. Fix that, do not pass `--sandbox workspace-write` /
`danger-full-access` or set `CODEX_SANDBOX` (Windows resolves via `auto`).

If verdict is NEEDS_WORK, loop internally until SHIP or the iteration cap:

1. **Parse issues** from reviewer feedback (missing requirements, incomplete implementations)
2. **Fix code** and run tests/lints
3. **Commit fixes** (mandatory before re-review; RP backend uses the snapshot-scoped staging in workflow-rp.md — never blanket-stage with `git add --all`)
4. **Re-review**:
   - **Codex**: Re-run `flowctl codex completion-review` (receipt enables context)
   - **Copilot**: Re-run `flowctl copilot completion-review` (receipt enables context; must be `mode == "copilot"` to resume)
   - **Cursor**: Re-run `flowctl cursor completion-review` (receipt enables context; must be `mode == "cursor"` to resume)
   - **Host**: Continue through [workflow-host.md](workflow-host.md)'s selected
     re-review path.
   - **RP**: `$FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file <literal re-review path from workflow-rp.md's fix loop>` (NO `--new-chat`; stdout redirected to the same literal response file, Read once)
5. **Repeat** until `<verdict>SHIP</verdict>` — or a delivered `NEEDS_WORK`
   consumes the final round. On that final host/rp verdict, run Step 3 before
   the cap terminal; never rely on a later step after exit 4.

**CRITICAL**: For RP, re-reviews must stay in the SAME chat so reviewer has context. Only use `--new-chat` on the FIRST review.

## Step 3: Record the terminal verdict exactly once

`flowctl <backend> completion-review` self-writes `completion_review_status` / `completion_reviewed_at` from the parsed verdict on codex/copilot/cursor (fn-112). **Without a write somewhere, a standalone completion review leaves `completion_review_status: unknown`, which keeps `flowctl ready --require-completion-review` demanding a review (pilot's gate), feeds make-pr's Open-items / draft heuristic stale state, and blocks tracker-sync's terminal `verified` rung.** The standalone command remains for rp and for repairing a missed write:

For host/rp, execute the Step 0.5 checkpoint again now. The just-recorded
terminal attempt is newer than the stored status, so that shared checkpoint is
the sole writer and emits the terminal only after persistence succeeds.
Codex/copilot/cursor handlers already self-write status; their next invocation
also runs Step 0.5 first, so a handler-side write failure recovers without
another reviewer dispatch.

For host and rp, write once on BOTH terminal paths (SHIP and capped-NEEDS_WORK).
The capped write happens immediately after the final verdict is recorded and
before `ESCALATE:` / exit 4; no later control flow is assumed.
`NEEDS_HUMAN`, transport failure, malformed verdict, and retry outcomes are
non-terminal and never write completion status.
