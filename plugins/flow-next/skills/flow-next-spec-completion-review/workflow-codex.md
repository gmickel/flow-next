# Spec Completion Review Workflow — Codex Backend

Use when `BACKEND="codex"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, and `SPEC_ID`.

## Step 1: Identify Spec

```bash
# SPEC_ID from arguments (e.g., fn-1, fn-22-53k)
$FLOWCTL show "$SPEC_ID" --json
```

## Step 2: Execute Review

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/completion-review-receipt-${SPEC_ID}.json}"  # fn-90 R5: spec-scoped default (concurrent specs no longer collide); explicit REVIEW_RECEIPT_PATH still wins

$FLOWCTL codex completion-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
```

**Output includes `VERDICT=SHIP|NEEDS_WORK`.**

## Step 3: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from output
2. Fix code and run tests
3. Commit fixes
4. Re-run step 2 (receipt enables session continuity)
5. Repeat until SHIP

## Step 4: Receipt

Receipt is written automatically by `flowctl codex completion-review` when `--receipt` provided.
Format: `{"type":"completion_review","id":"<spec-id>","mode":"codex","verdict":"<verdict>","session_id":"<thread_id>","timestamp":"..."}`

---

## Anti-patterns (Codex backend)

- **Using `--last` flag** - Conflicts with parallel usage; use `--receipt` instead
- **Direct codex calls** - Must use `flowctl codex` wrappers
