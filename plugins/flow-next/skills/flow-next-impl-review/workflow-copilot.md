# Implementation Review Workflow — Copilot Backend

Use when `BACKEND="copilot"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, and (optionally) `TASK_ID` / `BASE_COMMIT`.

## Step 1: Identify Task and Diff Base

```bash
BRANCH="$(git branch --show-current)"

# Use BASE_COMMIT from arguments if provided (task-scoped review)
# Otherwise fall back to main/master (full branch review)
if [[ -z "$BASE_COMMIT" ]]; then
  DIFF_BASE="main"
  git rev-parse main >/dev/null 2>&1 || DIFF_BASE="master"
else
  DIFF_BASE="$BASE_COMMIT"
fi

git log ${DIFF_BASE}..HEAD --oneline
```

## Step 2: Execute Review

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt${TASK_ID:+-${TASK_ID}}.json}"  # fn-90 R5: task-scoped default (concurrent tasks no longer collide); explicit REVIEW_RECEIPT_PATH still wins

# Runtime config:
#   --spec <spec>           full spec (backend:model:effort), highest priority
#   FLOW_REVIEW_BACKEND     env (spec-form ok: copilot:claude-opus-4.5:xhigh)
#   FLOW_COPILOT_MODEL      env (fills missing model only; default gpt-5.5)
#   FLOW_COPILOT_EFFORT     env (fills missing effort only; default high)
#   per-task stored review  via `flowctl task set-backend` (highest if set)

# Standalone branch reviews leave TASK_ID empty — OMIT the positional entirely
# (a quoted "" is rejected as an invalid task id; standalone mode needs no task arg).
args=(copilot impl-review)
[ -n "$TASK_ID" ] && args+=("$TASK_ID")
args+=(--base "$DIFF_BASE" --receipt "$RECEIPT_PATH")
$FLOWCTL "${args[@]}"
```

**Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK`.**

## Step 3: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from output
2. Fix code and run tests
3. Commit fixes
4. Re-run step 2 (receipt enables session continuity when `mode == "copilot"`)
5. Repeat until SHIP — bounded by the backend-agnostic fix-loop cap in [SKILL.md](SKILL.md) (`MAX_REVIEW_ITERATIONS`, default 4): count each fix+re-review cycle; at the cap, surface surviving findings and stop instead of looping

## Step 4: Receipt

Receipt is written automatically by `flowctl copilot impl-review` when `--receipt` provided.
Format: `{"type":"impl_review","id":"<id>","mode":"copilot","verdict":"<verdict>","session_id":"<uuid>","model":"<model>","effort":"<effort>","spec":"copilot:<model>:<effort>","timestamp":"..."}`

The `spec` field is the canonical round-trippable form (added in fn-28.3). `model` + `effort` remain for backward compatibility.

Session resume guard: re-review only resumes the copilot session when the existing receipt at `$RECEIPT_PATH` has `mode == "copilot"`. A cross-backend switch (e.g., codex receipt at the same path) starts a fresh session.

## Optional phases (gated by flags)

When the corresponding flag is set, run these phases from [workflow-common.md](workflow-common.md) — the dispatch matches the `copilot` case in each phase:

- `--deep` → "Deep-Pass Phase" (Step D.1 → D.5)
- `--validate` → "Validator Pass" (Step V.1 → V.4)
- `--interactive` → "Interactive Walkthrough Phase" (Step W.1 → W.5)

See [workflow-common.md](workflow-common.md) "Phase ordering & flag-combination matrix" for the order when multiple flags are set.

---

## Anti-patterns (Copilot backend)

- **Direct copilot calls** - Must use `flowctl copilot` wrappers
- **Inventing `--model`/`--effort` CLI flags** - Use `--spec` for a full backend:model:effort value, or `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars to fill individual fields
- **Using `--continue`** - Conflicts with parallel usage; session resume uses `--resume=<uuid>` under the hood via `--receipt`
- **Assuming cross-backend session continuity** - Resume only works when prior receipt has `mode == "copilot"`
