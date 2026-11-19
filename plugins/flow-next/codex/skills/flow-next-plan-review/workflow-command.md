# Plan Review Workflow — Command Backend

Use only when `BACKEND="command"` after [workflow.md](workflow.md).

## Critical rules

1. Use `$FLOWCTL command plan-review` exclusively.
2. The label's argv is in this machine's `FLOW_REVIEW_COMMAND_<LABEL>`. When
   `--review=command:<label>` was given, pass `--spec command:<label>`; otherwise (no
   `--review`, or a bare `--review=command`) flowctl takes the label from the per-spec pin,
   `FLOW_REVIEW_BACKEND` or `review.backend`. No label, an unset variable or a bad value
   stops before any round is reserved.
3. Pass `--receipt`; a re-review resumes only a receipt with mode `command` and the
   same label.

## Execute Review

```bash
SPEC_ID="<spec id resolved in workflow.md Phase 0>"   # substitute literally
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-$(git rev-parse --show-toplevel)/.flow/tmp/plan-review-receipt-${SPEC_ID}.json}"
args=("$SPEC_ID" --receipt "$RECEIPT_PATH")
# With --review=command:<label>, add: args+=(--spec "command:<label>")
$FLOWCTL command plan-review "${args[@]}"
```

Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK|NEEDS_HUMAN`; carry it into
SKILL.md's shared Fix Loop. flowctl runs that argv without a shell and owns
status, rounds and the receipt, which records `command`, the label and the model the
wrapper reported; the wrapper owns the model and read-only access.
