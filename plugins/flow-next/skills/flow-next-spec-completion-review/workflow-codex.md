# Spec Completion Review Workflow — Codex Backend

Use when `BACKEND="codex"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, and `SPEC_ID`.

## Critical rules (codex backend)

1. Use `$FLOWCTL codex completion-review` exclusively
2. Pass `--receipt` for session continuity on re-reviews
3. Parse verdict from command output

## Step 1: Execute Review

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-$(git rev-parse --show-toplevel)/.flow/tmp/completion-review-receipt-${SPEC_ID}.json}"  # repo- and spec-keyed default; explicit REVIEW_RECEIPT_PATH still wins

$FLOWCTL codex completion-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
```

**Output includes `VERDICT=SHIP|NEEDS_WORK|NEEDS_HUMAN`.**

## Step 2: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from output
2. Fix code and run tests
3. Commit fixes
4. Re-run step 1 (receipt enables session continuity)
5. Stop or loop as workflow-common.md's Fix Loop step 5 says

## Step 3: Receipt

Receipt is written automatically by `flowctl codex completion-review` when `--receipt` provided.

When `.flow/criteria.md` exists, the prompt includes the project's global acceptance criteria and the receipt may carry the additive `criteria: [{id, status, note?}]` field (absent when the reviewer output has no parseable `## Global criteria` section).

---

## Anti-patterns (Codex backend)

- **Using `--last` flag** - Conflicts with parallel usage; use `--receipt` instead
- **Direct codex calls** - Must use `flowctl codex` wrappers
