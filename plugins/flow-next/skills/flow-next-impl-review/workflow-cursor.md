# Implementation Review Workflow — Cursor Backend

Use when `BACKEND="cursor"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, and (optionally) `TASK_ID` / `BASE_COMMIT`.

Cursor shells out to the `cursor-agent` CLI (headless `-p --output-format json`), billed against the user's Cursor subscription. It reaches reviewer models the other backends can't — ask `cursor-agent --list-models` for the current set. This is the **review backend**, independent of the Cursor-as-primary-host-driver path.

## Critical Rules (cursor backend)

1. Use `$FLOWCTL cursor impl-review` exclusively
2. Pass `--receipt` for session continuity on re-reviews (session only resumes when prior receipt has `mode == "cursor"`)
3. Model resolved via (first match wins): `--spec cursor:<model>` flag, per-task `review`, `FLOW_REVIEW_BACKEND` spec, `FLOW_CURSOR_MODEL` env var, registry default. **No effort** — Cursor bakes effort into the model name; `cursor:<model>:<effort>` is rejected
4. Parse verdict from command output
5. No fan-out on this backend: every round is a single dispatch (the three-draw fan-out is codex/host-only)

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
ROUTE="$($FLOWCTL review-route ${TASK_ID:+"$TASK_ID"} --json)"   # pure: canonical TASK_ID + receipt path (no rotation, no state change)
TASK_ID="$(jq -r '.task_id // empty' <<<"$ROUTE")"
RECEIPT_PATH="$(jq -r '.receipt_path' <<<"$ROUTE")"

# Runtime config:
#   --spec <spec>           full spec (cursor:<model>), highest priority
#   FLOW_REVIEW_BACKEND     env (spec-form ok: cursor:gpt-5.5-high)
#   FLOW_CURSOR_MODEL       env (fills missing model only; else registry default)
#   per-task stored review  via `flowctl task set-backend` (highest if set)
#
# Cursor folds reasoning effort INTO the model name (a `-high` / `-xhigh` suffix),
# so there is NO effort field — `cursor:<model>:<effort>` is rejected, and there
# is no FLOW_CURSOR_EFFORT env var.

# Standalone branch reviews leave TASK_ID empty — OMIT the positional entirely
# (a quoted "" is rejected as an invalid task id; standalone mode needs no task arg).
# Subcommand tokens stay LITERAL on the command line (the Ralph guard blocks
# a variable in either of the two tokens after the launcher).
args=()
[ -n "$TASK_ID" ] && args+=("$TASK_ID")
args+=(--base "$DIFF_BASE" --receipt "$RECEIPT_PATH")
$FLOWCTL cursor impl-review "${args[@]}"
```

**Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK|NEEDS_HUMAN`.**

The runner invokes `cursor-agent -p --output-format json --trust --mode ask` with `cwd=repo_root` (`--mode ask` is read-only — the reviewer never mutates the tree).

## Step 3: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from output
2. Fix code and run tests
3. Commit fixes
4. Re-run step 2 (receipt enables session continuity when `mode == "cursor"`)
5. Repeat until SHIP — bounded by the backend-agnostic fix-loop cap in [SKILL.md](SKILL.md) (`MAX_REVIEW_ITERATIONS`, default 8): count each fix+re-review cycle; at the cap, surface surviving findings and stop instead of looping

## Step 4: Receipt

Receipt is written automatically by `flowctl cursor impl-review` when `--receipt` provided.
Format: `{"type":"impl_review","id":"<id>","mode":"cursor","verdict":"<verdict>","session_id":"<uuid>","model":"<model>","spec":"cursor:<model>","timestamp":"..."}`

There is **no `effort` key** — effort is not a Cursor field (it lives inside the model name). The `spec` field is the canonical round-trippable form; `model` is the resolved Cursor model string.

Session resume guard: re-review only resumes the cursor session when the existing receipt at `$RECEIPT_PATH` has `mode == "cursor"`. The first call omits `--resume` and captures Cursor's generated `session_id`; continuations pass `--resume <session_id>` using that persisted id. A cross-backend switch (e.g., copilot receipt at the same path) starts a fresh session.

## Optional phases (gated by flags)

When the corresponding flag is set, run these phases from [optional-phases.md](optional-phases.md) — the dispatch matches the `cursor` case in each phase:

- `--deep` → "Deep-Pass Phase" (Step D.1 → D.5)
- `--validate` → "Validator Pass" (Step V.1 → V.4)
- `--interactive` → "Interactive Walkthrough Phase" (Step W.1 → W.5)

See [optional-phases.md](optional-phases.md) "Phase ordering & flag-combination matrix" for the order when multiple flags are set.

---

## Anti-patterns (Cursor backend)

- **Direct cursor-agent calls** - Must use `flowctl cursor` wrappers
- **Inventing a `--model` CLI flag** - Use `--spec` for a full `cursor:<model>` value, or the `FLOW_CURSOR_MODEL` env var to fill the model
- **Passing an effort** - Cursor has no effort field; `cursor:<model>:<effort>` is rejected. Pick a model whose name already encodes the effort
- **Fabricating a first-call `--resume` id** - The first call omits `--resume`; persist Cursor's returned `session_id` and resume with that. Session resume uses `--resume=<uuid>` under the hood via `--receipt`
- **Assuming cross-backend session continuity** - Resume only works when prior receipt has `mode == "cursor"`
