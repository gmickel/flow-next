# Plan Review Workflow — Command Backend

Use only when `BACKEND="command"` after [workflow.md](workflow.md).

## Critical rules

1. Use `$FLOWCTL command plan-review` exclusively.
2. The label names an entry in `review.commands`. When `--review=command:<label>` was
   given, pass `--spec command:<label>`; otherwise flowctl takes the label from the
   per-spec pin, `FLOW_REVIEW_BACKEND` or `review.backend`.
3. Pass `--receipt`; resume only when the prior receipt mode is `command`.
4. Run the dispatch as one blocking foreground call.

## Execute Review — one atomic fence

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
SPEC_ID="<spec id resolved in workflow.md Phase 0>"   # substitute literally
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-$(git rev-parse --show-toplevel)/.flow/tmp/plan-review-receipt-${SPEC_ID}.json}"
args=("$SPEC_ID" --receipt "$RECEIPT_PATH")
# With --review=command:<label>, add: args+=(--spec "command:<label>")

$FLOWCTL command plan-review "${args[@]}"
```

Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK|NEEDS_HUMAN`. The handler owns
status, cumulative rounds, and receipt writes. flowctl runs the configured argv without a
shell, sends the review execution request on stdin and reads the response from stdout;
the wrapper owns the model and read-only access. The receipt records `command`, the label
and the model the wrapper reported. An unknown label or a bad `review.commands` entry
stops before any round is reserved.

Carry the verdict directly into SKILL.md's shared Fix Loop. A re-review resumes the
session the command returned; when the command reports that resume failed, flowctl
re-runs it fresh with the prior findings.

## Anti-patterns

- Running the wrapper directly
- Passing a model or effort: the wrapper owns the model
- Cross-backend session reuse
