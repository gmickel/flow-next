# Plan Review Workflow — Codex Backend

Use only when `BACKEND="codex"` after [workflow.md](workflow.md).

## Critical rules

1. Use `$FLOWCTL codex plan-review` exclusively.
2. Pass `--receipt`; re-reviews resume only through that receipt.
3. Parse the actual backend verdict; never self-declare.
4. Run the dispatch as one blocking foreground call.

## Execute Review — one atomic fence

Checkpoint, canonical spec id, receipt, and dispatch stay in one fence because
shell variables do not survive tool calls:

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
SPEC_ID="<spec id resolved in workflow.md Phase 0>"   # substitute literally
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-$(git rev-parse --show-toplevel)/.flow/tmp/plan-review-receipt-${SPEC_ID}.json}"

$FLOWCTL checkpoint save --spec "$SPEC_ID" --json
$FLOWCTL codex plan-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
```

Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK|NEEDS_HUMAN`. The handler owns
`plan_review_status`, `plan_reviewed_at`, cumulative rounds, and receipt writes.
Receipt session continuity must remain mode `codex`.

Carry the verdict directly into SKILL.md's shared Fix Loop. A re-review repeats
this same fence after the spec/task updates.

## Anti-patterns

- Direct `codex exec`
- `--last` instead of receipt continuity
- Reconstructing the reviewer prompt in skill prose
