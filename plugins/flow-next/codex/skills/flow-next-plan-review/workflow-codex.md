# Plan Review Workflow — Codex Backend

Use only when `BACKEND="codex"` after [workflow.md](workflow.md).

## Critical rules

1. Use `$FLOWCTL codex plan-review` exclusively.
2. Pass `--receipt`; re-reviews resume only through that receipt.
3. Parse the actual backend verdict; never self-declare.
4. Run the dispatch as one blocking foreground call.

## Execute Review — one atomic fence

Checkpoint, canonical spec id, receipt, code anchors, and dispatch stay in one
fence because shell variables do not survive prompt turns:

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
SPEC_ID="${1:-}"
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/plan-review-receipt-${SPEC_ID}.json}"

$FLOWCTL checkpoint save --spec "$SPEC_ID" --json
CODE_FILES="$(awk '/^## Key files/{f=1;next} /^## /{f=0} f' ".flow/specs/${SPEC_ID}.md" | grep -oE '`[^`]+\.[A-Za-z0-9]+`' | tr -d '`' | grep -vE '^https?:' | sort -u | head -20 | paste -sd, -)"
[ -z "$CODE_FILES" ] && CODE_FILES="$(grep -oE '[A-Za-z0-9_./-]+\.(py|ts|tsx|js|jsx|go|rs|rb|java|php|c|cpp|h|md|sh)' ".flow/specs/${SPEC_ID}.md" | grep -vE '^https?:' | sort -u | head -20 | paste -sd, -)"

$FLOWCTL codex plan-review "$SPEC_ID" --files "$CODE_FILES" --receipt "$RECEIPT_PATH"
```

Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK`. The handler owns
`plan_review_status`, `plan_reviewed_at`, cumulative rounds, and receipt writes.
Receipt session continuity must remain mode `codex`.

Return the verdict to SKILL.md's shared fix loop. A re-review repeats this same
fence after the spec/task updates.

## Anti-patterns

- Direct `codex exec`
- `--last` instead of receipt continuity
- Reconstructing the reviewer prompt in skill prose
