# Spec Completion Review Workflow — Copilot Backend

Use when `BACKEND="copilot"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, and `SPEC_ID`.

## Step 1: Identify Spec

```bash
# SPEC_ID from arguments (e.g., fn-1, fn-22-53k)
$FLOWCTL show "$SPEC_ID" --json
```

## Step 2: Execute Review

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/completion-review-receipt-${SPEC_ID}.json}" # fn-90 R5: spec-scoped default (concurrent specs no longer collide); explicit REVIEW_RECEIPT_PATH still wins

# Runtime config:
# --spec <spec> full spec (backend:model:effort), highest priority
# FLOW_REVIEW_BACKEND spec-form ok: copilot:claude-opus-4.5:xhigh
# FLOW_COPILOT_MODEL fills missing model only (default gpt-5.2)
# FLOW_COPILOT_EFFORT fills missing effort only (default high)

$FLOWCTL copilot completion-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
```

**Output includes `VERDICT=SHIP|NEEDS_WORK`.**

## Step 3: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from output
2. Fix code and run tests
3. Commit fixes
4. Re-run step 2 (receipt enables session continuity when `mode == "copilot"`)
5. Repeat until SHIP

## Step 4: Receipt

Receipt is written automatically by `flowctl copilot completion-review` when `--receipt` provided.
Format: `{"type":"completion_review","id":"<spec-id>","mode":"copilot","verdict":"<verdict>","session_id":"<uuid>","model":"<model>","effort":"<effort>","spec":"copilot:<model>:<effort>","timestamp":"..."}`

The `spec` field is the canonical round-trippable form (added in fn-28.3). `model` + `effort` remain for backward compatibility.

Session resume guard: re-review only resumes the copilot session when the existing receipt at `$RECEIPT_PATH` has `mode == "copilot"`. Cross-backend switches start a fresh session.

---

## Anti-patterns (Copilot backend)

- **Direct copilot calls** - Must use `flowctl copilot` wrappers
- **Inventing `--model`/`--effort` CLI flags** - Use `--spec` for a full backend:model:effort value, or `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars to fill individual fields
- **Using `--continue`** - Conflicts with parallel usage; session resume uses `--resume=<uuid>` under the hood via `--receipt`
- **Assuming cross-backend session continuity** - Resume only works when prior receipt has `mode == "copilot"`
