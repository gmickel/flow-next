# Plan Review Workflow — Cursor Backend

Use only when `BACKEND="cursor"` after [workflow.md](workflow.md).

## Critical rules

1. Use `$FLOWCTL cursor plan-review` exclusively.
2. Pass `--receipt`; resume only when the prior receipt mode is `cursor`.
3. Cursor takes a model only. Effort is encoded in the model name; never pass an
 effort field.
4. Run the read-only dispatch as one blocking foreground call.

## Execute Review — one atomic fence

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
SPEC_ID="${1:-}"
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/plan-review-receipt-${SPEC_ID}.json}"

$FLOWCTL checkpoint save --spec "$SPEC_ID" --json
CODE_FILES="$(awk '/^## Key files/{f=1;next} /^## /{f=0} f' ".flow/specs/${SPEC_ID}.md" | grep -oE '`[^`]+\.[A-Za-z0-9]+`' | tr -d '`' | grep -vE '^https?:' | sort -u | head -20 | paste -sd, -)"
[ -z "$CODE_FILES" ] && CODE_FILES="$(grep -oE '[A-Za-z0-9_./-]+\.(py|ts|tsx|js|jsx|go|rs|rb|java|php|c|cpp|h|md|sh)' ".flow/specs/${SPEC_ID}.md" | grep -vE '^https?:' | sort -u | head -20 | paste -sd, -)"

$FLOWCTL cursor plan-review "$SPEC_ID" --files "$CODE_FILES" --receipt "$RECEIPT_PATH"
```

Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK`. The handler owns
status, cumulative rounds, and receipt writes. Cursor invokes
`cursor-agent -p --output-format json --trust --mode ask` in the repo root; the
reviewer is read-only. The receipt has no effort key.

Return the verdict to SKILL.md's shared fix loop. The first call omits a resume
id; only a persisted same-mode `session_id` enables continuation.

## Anti-patterns

- Direct `cursor-agent` calls
- Passing an effort or fabricating a first-call resume id
- Cross-backend session reuse
