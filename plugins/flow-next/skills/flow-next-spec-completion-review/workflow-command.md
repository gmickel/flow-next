# Spec Completion Review Workflow — Command Backend

Use when `BACKEND="command"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, and `SPEC_ID`; its foreground rule and Fix Loop apply unchanged.

The command backend runs the argv configured at `review.commands.<label>` in `.flow/config.json`, selected as `command:<label>`. flowctl runs it without a shell, keeps the prompt, rounds, verdict parsing and receipt, and sends only inference to the command; the wrapper owns read-only access and the model.

## Critical rules (command backend)

1. Use `$FLOWCTL command completion-review` exclusively
2. Label resolved via (first match wins): `--spec command:<label>` (pass it when `--review=command:<label>` was given), per-spec `default_review`, `FLOW_REVIEW_BACKEND`, `review.backend`. There is no default label; an unknown label or a bad `review.commands` entry stops before any round is reserved
3. Pass `--receipt`; a re-review resumes only a receipt with `mode == "command"` and the same label

## Execute Review

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-$(git rev-parse --show-toplevel)/.flow/tmp/completion-review-receipt-${SPEC_ID}.json}"
args=("$SPEC_ID" --receipt "$RECEIPT_PATH")
# With --review=command:<label>, add: args+=(--spec "command:<label>")
$FLOWCTL command completion-review "${args[@]}"
```

Output includes `VERDICT=SHIP|NEEDS_WORK|NEEDS_HUMAN`; carry it into workflow-common.md's Fix Loop. The receipt records `mode: command`, the `label`, and the `model` the wrapper reported (`not reported` when it named none).
