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
SPEC_ID="<spec id resolved in workflow.md Phase 0>"   # substitute literally
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-$(git rev-parse --show-toplevel)/.flow/tmp/plan-review-receipt-${SPEC_ID}.json}"

$FLOWCTL checkpoint save --spec "$SPEC_ID" --json
$FLOWCTL copilot plan-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
```

Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK|NEEDS_HUMAN`. The handler owns
status, cumulative rounds, and receipt writes. The receipt retains the resolved
`model`, `effort`, round-trippable `spec`, and Copilot `session_id`.

Carry the verdict directly into SKILL.md's shared Fix Loop. A cross-backend
receipt never resumes a Copilot session.

## Anti-patterns

- Direct `copilot` calls
- Invented `--model` / `--effort` flags instead of backend spec resolution
- `--continue` or cross-backend session reuse
