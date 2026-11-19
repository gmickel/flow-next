# Spec Completion Review Workflow — Command Backend

Use when `BACKEND="command"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, and `SPEC_ID`.

The command backend runs the argv configured at `review.commands.<label>` in `.flow/config.json`, selected as `command:<label>`. flowctl keeps the prompt, rounds, verdict parsing and receipt; only inference crosses to the command.

## Critical rules (command backend)

1. Use `$FLOWCTL command completion-review` exclusively
2. Label resolved via (first match wins): `--spec command:<label>` (pass it when `--review=command:<label>` was given), per-spec `default_review`, `FLOW_REVIEW_BACKEND`, `review.backend`. There is no default label; an unknown label or a bad `review.commands` entry stops before any round is reserved
3. Pass `--receipt` for session continuity on re-reviews (session only resumes when prior receipt has `mode == "command"`)
4. Parse verdict from command output

## Step 1: Execute Review

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-$(git rev-parse --show-toplevel)/.flow/tmp/completion-review-receipt-${SPEC_ID}.json}"  # repo- and spec-keyed default; explicit REVIEW_RECEIPT_PATH still wins
args=("$SPEC_ID" --receipt "$RECEIPT_PATH")
# With --review=command:<label>, add: args+=(--spec "command:<label>")

$FLOWCTL command completion-review "${args[@]}"
```

**Output includes `VERDICT=SHIP|NEEDS_WORK|NEEDS_HUMAN`.**

flowctl runs the argv without a shell, writes the review execution request to its standard input and reads the response from its standard output. The wrapper owns read-only access and the model.

## Step 2: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from output
2. Fix code and run tests
3. Commit fixes
4. Re-run step 1 (receipt enables session continuity when `mode == "command"`)
5. Stop or loop as workflow-common.md's Fix Loop step 5 says

## Step 3: Receipt

Receipt is written automatically by `flowctl command completion-review` when `--receipt` provided. It records `mode: command`, the `label`, and the `model` the wrapper reported (`not reported` when it named none).

When `.flow/criteria.md` exists, the prompt includes the project's global acceptance criteria and the receipt may carry the additive `criteria: [{id, status, note?}]` field (absent when the reviewer output has no parseable `## Global criteria` section).

Session resume guard: a re-review resumes the session the command returned; when the command reports that resume failed, flowctl re-runs it fresh with the prior findings. Cross-backend switches start a fresh session.

---

## Anti-patterns (command backend)

- **Running the wrapper directly** - Must use `flowctl command` wrappers
- **Passing a model or effort** - The wrapper owns the model; `command:<label>` takes nothing else
- **Assuming cross-backend session continuity** - Resume only works when prior receipt has `mode == "command"`
