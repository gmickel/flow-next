# Plan Review Workflow — Copilot Backend

Use only when `BACKEND="copilot"` after [workflow.md](workflow.md).

## Critical rules

1. Use `$FLOWCTL copilot plan-review` exclusively.
2. Pass `--receipt`; resume only when the prior receipt mode is `copilot`.
3. Model/effort precedence remains explicit spec → per-spec default → review
   env → Copilot env → registry defaults.
4. Run the dispatch as one blocking foreground call.

## Execute Review — one atomic fence

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
SPEC_ID="${1:-}"
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/plan-review-receipt-${SPEC_ID}.json}"

$FLOWCTL checkpoint save --spec "$SPEC_ID" --json
CODE_FILES="$(awk '/^## Key files/{f=1;next} /^## /{f=0} f' ".flow/specs/${SPEC_ID}.md" | grep -oE '`[^`]+\.[A-Za-z0-9]+`' | tr -d '`' | grep -vE '^https?:' | sort -u | head -20 | paste -sd, -)"
[ -z "$CODE_FILES" ] && CODE_FILES="$(grep -oE '[A-Za-z0-9_./-]+\.(py|ts|tsx|js|jsx|go|rs|rb|java|php|c|cpp|h|md|sh)' ".flow/specs/${SPEC_ID}.md" | grep -vE '^https?:' | sort -u | head -20 | paste -sd, -)"

$FLOWCTL copilot plan-review "$SPEC_ID" --files "$CODE_FILES" --receipt "$RECEIPT_PATH"
```

Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK`. The handler owns
status, cumulative rounds, and receipt writes. The receipt retains the resolved
`model`, `effort`, round-trippable `spec`, and Copilot `session_id`.

Return the verdict to SKILL.md's shared fix loop. A cross-backend receipt never
resumes a Copilot session.

## Anti-patterns

- Direct `copilot` calls
- Invented `--model` / `--effort` flags instead of backend spec resolution
- `--continue` or cross-backend session reuse
