---
name: flow-next-spec-completion-review
description: Verify that a spec's completed tasks fully implement the spec requirements. Use at spec completion before close.
user-invocable: false
---

# Spec Completion Review Mode

**Workflow is backend-split. Read [workflow-common.md](workflow-common.md) for Phase 0 (backend detection + philosophy), then read ONLY the file matching your active backend:**

- `BACKEND=codex` → [workflow-codex.md](workflow-codex.md)
- `BACKEND=copilot` → [workflow-copilot.md](workflow-copilot.md)
- `BACKEND=cursor` → [workflow-cursor.md](workflow-cursor.md)
- `BACKEND=claude` → [workflow-claude.md](workflow-claude.md)
- `BACKEND=host` → [workflow-host.md](workflow-host.md)
- `BACKEND=rp` → [workflow-rp.md](workflow-rp.md)

Do not load the others — only the active backend's file is needed.

Verify that the combined implementation of all tasks in a spec satisfies the spec requirements. This is NOT a code quality review (that's impl-review's job) — this confirms spec compliance only.

**Role**: Spec Completion Review Coordinator (NOT the reviewer)
**Backends** (branch on the Phase 0 `RP_ELIGIBLE` probe):
- When `RP_ELIGIBLE=1`: RepoPrompt (rp), Codex CLI (codex), GitHub Copilot CLI (copilot), Cursor CLI (cursor), Claude Code CLI (claude), or host-native (`host`)
- When `RP_ELIGIBLE=0`: Codex CLI (codex), GitHub Copilot CLI (copilot), Cursor CLI (cursor), Claude Code CLI (claude), or host-native (`host`) — rp is macOS-only; never list it in guidance you surface (`--review=rp` stays accepted)

## Preamble — execute Phase 0 exactly once

**The executable Phase 0 lives in [workflow-common.md](workflow-common.md) §"Phase 0: Backend Detection" — Read it and execute it ONCE, before any other bash in this skill.** It defines `$FLOWCTL` (bundled — NOT installed globally; `which flowctl` fails, expected), probes `RP_ELIGIBLE`, resolves `$BACKEND` via the single `flowctl review-backend` call, and handles the ASK / `none` cases. Never invoke `flowctl review-backend` a second time in the same run.

Exception: a `--review=<backend>` argument (see Backend Selection below) wins — when present, set `BACKEND` from the flag and skip Phase 0's `review-backend` call + ASK handling (still run its `$FLOWCTL` / `RP_ELIGIBLE` setup lines).

When `RP_ELIGIBLE=0` (not macOS, no supported RepoPrompt CLI), never *steer* the user toward rp: every backend summary, recommendation, or override hint you surface presents only the runnable configured backends `codex`, `copilot`, `cursor`, `claude`, `host` (plus `none`). Suppression is not a ban: an explicit `--review=rp`, `FLOW_REVIEW_BACKEND=rp`, or `review.backend=rp` still resolves to rp and errors at runtime via `require_rp_cli()`.

## Backend Selection

**Priority** (first match wins):
1. `--review=rp|codex|copilot|cursor|claude|host|none` argument
2. `FLOW_REVIEW_BACKEND` env var — bare backend (`rp`, `codex`, `copilot`, `cursor`, `claude`, `host`, `none`) OR spec form (`codex:<model>:xhigh`, `copilot:<model>`, `cursor:<model>`, `claude:<model>:<effort>`); `host` is bare-only (`host:<model>` is rejected)
3. `.flow/config.json` → `review.backend` (same bare / spec forms)
4. **Error** - no auto-detection

### Parse from arguments first

Check $ARGUMENTS for:
- `--review=rp` or `--review rp` → use rp
- `--review=codex` or `--review codex` → use codex
- `--review=copilot` or `--review copilot` → use copilot
- `--review=cursor` or `--review cursor` → use cursor
- `--review=claude` or `--review claude` → use claude
- `--review=host` or `--review host` → use host
- `--review=none` or `--review none` → skip review

If found, use that backend and skip all other detection.

### Otherwise: Phase 0 resolves it

No `--review` flag → `$BACKEND` comes from [workflow-common.md](workflow-common.md) Phase 0 (executed once per the Preamble): the single `flowctl review-backend "$SPEC_ID"` call with ASK handling included. Do not re-resolve here.

### Backend at a glance

The per-backend summary (models, env vars, `--spec` forms) and the `backend[:model[:effort]]` spec grammar live in [references/backend-at-a-glance.md](references/backend-at-a-glance.md). Read it **only** when you surface backend guidance to the user (ASK branch, recommendation, override hint) — routing does not need it.

## Critical Rules

Per-backend critical rules live in the backend file you route to (`workflow-codex.md`, `workflow-copilot.md`, `workflow-cursor.md`, `workflow-claude.md`, `workflow-rp.md`) — each opens with its own **Critical rules** section. The host safety invariant and the all-backends rules stay here because they gate routing itself.

**For host backend:**
`host` is bare-only. After selection, read [workflow-host.md](workflow-host.md).
The review must use a fresh, tool-enforced read-only reviewer from a different
model family and fail closed when no cross-family pin is available.

**For all backends:**
- If `REVIEW_RECEIPT_PATH` set: write receipt after SHIP verdict (RP writes manually after fix loop; codex writes automatically via `--receipt`)
- Any failure → output `<promise>RETRY</promise>` and stop. No-verdict
  transport failures are recorded and their reserved round refunded; never
  manually reset the review counter. Exit 5 / `TRANSPORT_UNHEALTHY` stops
  automatic retries until the backend is repaired.

The three **hard invariants** (never self-declare SHIP, never mix backends, never skip review silently) live with the shared anti-patterns in [workflow-common.md](workflow-common.md) §"Anti-patterns (all backends)".

## Input

Arguments: $ARGUMENTS
Format: `<spec-id> [--review=rp|codex|copilot|cursor|claude|host|none]`

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
Host and rp terminal status has one owner, `review-rounds record --status-target completion` (with a journaled receipt, that status leg lands when the receipt publishes); this checkpoint only repairs a write that did not land. A stored `not_required` (work's 3g policy skip) is neither `ship` nor `unknown` here: the checkpoint has no terminal attempt to resume for it, and an explicit manual invocation may still run a real review and overwrite it with `ship`/`needs_work` — the upgrade direction is legal, while the skip's own write stays gated on `unknown`.

```bash
TERMINAL_REVIEW_JSON="$($FLOWCTL review-rounds resume-terminal "$SPEC_ID" --review-type completion --json)" || exit $?
TERMINAL_ACTION="$(printf '%s' "$TERMINAL_REVIEW_JSON" | jq -r '.action')"
TERMINAL_STATUS="$(printf '%s' "$TERMINAL_REVIEW_JSON" | jq -r '.status')"
TERMINAL_EXIT="$(printf '%s' "$TERMINAL_REVIEW_JSON" | jq -r '.exit')"
case "$TERMINAL_ACTION" in
  continue) ;;
  retry) echo "<promise>RETRY</promise>"; exit "$TERMINAL_EXIT" ;;
  ship) echo "VERDICT=SHIP"; exit "$TERMINAL_EXIT" ;;
  superseded) echo "COMPLETION_REVIEW_STATUS=$TERMINAL_STATUS"; exit "$TERMINAL_EXIT" ;;
  escalate)
    if [ "$TERMINAL_STATUS" = needs_human ]; then
      echo "ESCALATE: reviewer requested human review"
    else
      echo "ESCALATE: completion-review did not converge within the verdict-round cap"
    fi
    exit "$TERMINAL_EXIT" ;;
  *) echo "Unknown terminal review action: $TERMINAL_ACTION" >&2; exit 1 ;;
esac
```

An exit-4 cap refusal before this run has delivered a completion verdict is
non-terminal for completion status: surface `ESCALATE:` / `NEEDS_HUMAN` and do
not invent a `needs_work` write. More than
`${MAX_REVIEW_TRANSPORT_FAILURES:-2}` consecutive transport failures stop
separately with `TRANSPORT_UNHEALTHY` + exit 5; never write completion status or
reset the verdict counter for transport health.

**Unchanged-artifact terminal:** `NOT_RETRYABLE: artifact unchanged since last verdict` exits `1` before dispatch. Stop for human action; never refund, reset,
use `--force`, or redispatch autonomously. A human may edit the exact artifact,
explicitly reset, or deliberately apply `--force`.

### Step 1: Load Backend Workflow

1. `$BACKEND` was already resolved by workflow-common.md Phase 0 (Preamble) — do NOT re-run it.
2. Read **only** the file for that backend, per the routing table at the top of this file.

**Do not read the other backend files.** Each is self-contained for its backend; loading the others wastes context.

### Step 2: Execute the backend workflow

Follow the phases in the per-backend file end-to-end. Each file owns its own Identify → Execute → Verdict → Receipt steps (and, for RP, the full Phase 1-4 setup-review (5-15 min, DO NOT RETRY) / chat-send (2-10 min, DO NOT RETRY) / receipt build).

### Step 3: Fix loop and terminal status

Both are backend-agnostic and live in [workflow-common.md](workflow-common.md) — already in context from Phase 0:

- §"Fix Loop (INTERNAL - do not exit to Ralph)" — the round cap, the anti-patterns, and the parse → fix → commit → re-review cycle.
- §"Record the terminal verdict exactly once" — who writes `completion_review_status`, and when host/rp re-run the Step 0.5 checkpoint above.
