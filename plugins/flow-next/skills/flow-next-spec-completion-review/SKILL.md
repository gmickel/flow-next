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
- `BACKEND=claude` → [workflow-claude.md](workflow-claude.md)
- `BACKEND=host` → [workflow-host.md](workflow-host.md)

Do not load the others — only the active backend's file is needed.

Verify that the combined implementation of all tasks in a spec satisfies the spec requirements. This is NOT a code quality review (that's impl-review's job) — this confirms spec compliance only.

**Role**: Spec Completion Review Coordinator (NOT the reviewer)
**Backends**: Codex CLI (codex), GitHub Copilot CLI (copilot), Cursor CLI (cursor), Claude Code CLI (claude), or host-native (`host`)

Read [working-rules.md](../../references/working-rules.md) first unless you already have this run; it holds for every step of this skill.

## Preamble — execute Phase 0 exactly once

**The executable Phase 0 lives in [workflow-common.md](workflow-common.md) §"Phase 0: Backend Detection" — Read it and execute it ONCE, before any other bash in this skill.** It defines `$FLOWCTL` (bundled — NOT installed globally; `which flowctl` fails, expected), resolves `$BACKEND` via the single `flowctl review-backend` call, and handles the ASK / `none` cases. Never invoke `flowctl review-backend` a second time in the same run.

Exception: a `--review=<backend>` argument (see Backend Selection below) wins — when present, set `BACKEND` from the flag and skip Phase 0's `review-backend` call + ASK handling (still run its `$FLOWCTL` setup lines). An explicit `--review=rp` or `--review=export` was removed: tell the user in one line "RepoPrompt review (rp, export) was removed in flow-next 8.0.0; review backends: claude, codex, copilot, cursor, host." and stop as for ASK.

## Backend Selection

**Priority** (first match wins):
1. `--review=<backend>` or `--review <backend>` argument (`codex|copilot|cursor|claude|host|none`)
2. `FLOW_REVIEW_BACKEND` env var — bare backend (`codex`, `copilot`, `cursor`, `claude`, `host`, `none`) OR spec form (`codex:<model>:xhigh`, `copilot:<model>`, `cursor:<model>`, `claude:<model>:<effort>`); `host` is bare-only (`host:<model>` is rejected)
3. `.flow/config.json` → `review.backend` (same bare / spec forms)
4. **Error** - no auto-detection

### Backend at a glance

The per-backend summary (models, env vars, `--spec` forms and `FLOW_REVIEW_BACKEND` spec-form examples) and the `backend[:model[:effort]]` spec grammar live in [references/backend-at-a-glance.md](references/backend-at-a-glance.md). Read it **only** when you surface backend guidance to the user (ASK branch, recommendation, override hint) — routing does not need it.

## Critical Rules

Per-backend critical rules live in the backend file you route to (`workflow-codex.md`, `workflow-copilot.md`, `workflow-cursor.md`, `workflow-claude.md`) — each opens with its own **Critical rules** section. The host safety invariant and the all-backends rules stay here because they gate routing itself.

**For host backend:**
`host` is bare-only. After selection, read [workflow-host.md](workflow-host.md).
The review must use a fresh, tool-enforced read-only reviewer from a different
model family and fail closed when no cross-family pin is available.

**For all backends:**
- If `REVIEW_RECEIPT_PATH` set: write receipt after SHIP verdict (codex writes automatically via `--receipt`)
- Any failure → output `RETRY: no verdict (backend or transport failure)` and stop; when its
  `CLI message:` reports a usage, credit or spend limit, report that message instead of `RETRY:`,
  since a retry fails the same way. No-verdict
  transport failures are recorded and their reserved round refunded; never
  manually reset the review counter. Exit 5 / `TRANSPORT_UNHEALTHY` stops
  automatic retries until the backend is repaired.

The three **hard invariants** (never self-declare SHIP, never mix backends, never skip review silently) live with the shared anti-patterns in [workflow-common.md](workflow-common.md) §"Anti-patterns (all backends)".

## Input

Arguments: $ARGUMENTS
Format: `<spec-id> [--review=codex|copilot|cursor|claude|host|none]`

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
any backend. Run the same checkpoint again immediately after host records a
verdict. It recovers a terminal status write that failed after the verdict round
was durably consumed, without reserving or dispatching another review.
Host terminal status has one owner, `review-rounds record --status-target completion` (with a journaled receipt, that status leg lands when the receipt publishes); this checkpoint only repairs a write that did not land. A stored `not_required` (work's 3g policy skip) is neither `ship` nor `unknown` here: the checkpoint has no terminal attempt to resume for it, and an explicit manual invocation may still run a real review and overwrite it with `ship`/`needs_work` — the upgrade direction is legal, while the skip's own write stays gated on `unknown`.

```bash
TERMINAL_REVIEW_JSON="$($FLOWCTL review-rounds resume-terminal "$SPEC_ID" --review-type completion --json)" || exit $?
TERMINAL_ACTION="$(printf '%s' "$TERMINAL_REVIEW_JSON" | jq -r '.action')"
TERMINAL_STATUS="$(printf '%s' "$TERMINAL_REVIEW_JSON" | jq -r '.status')"
TERMINAL_EXIT="$(printf '%s' "$TERMINAL_REVIEW_JSON" | jq -r '.exit')"
case "$TERMINAL_ACTION" in
  continue) ;;
  retry) echo "RETRY: no verdict (backend or transport failure)"; exit "$TERMINAL_EXIT" ;;
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

Follow the phases in the per-backend file end-to-end. Each file owns its own Identify → Execute → Verdict → Receipt steps.

### Step 3: Fix loop and terminal status

Both are backend-agnostic and live in [workflow-common.md](workflow-common.md) — already in context from Phase 0:

- §"Fix Loop (INTERNAL)" — the round cap, the anti-patterns, and the parse → fix → commit → re-review cycle.
- §"Record the terminal verdict exactly once" — who writes `completion_review_status`, and when host re-runs the Step 0.5 checkpoint above.
