# Implementation Review Workflow — Claude Backend

Use when `BACKEND="claude"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, and (optionally) `TASK_ID` / `BASE_COMMIT`.

Claude shells out to the Claude Code CLI (headless `claude -p`), billed against the user's Claude subscription or API key. It is the packaged Claude-family verdict for hosts that cannot dispatch a Claude subagent themselves (Codex, Cursor, Grok Build, Droid, OpenCode). This is the **review backend**, independent of Claude Code as the primary host.

**Same-family advisory:** on a Claude Code host the writer and this reviewer share a model family; the receipt records it (`mode: "claude"` plus `model`), and the run proceeds. Prefer `codex` or `host` there when family independence matters — `host` is the backend that fails closed on same-family review; `claude` never refuses.

## Critical Rules (claude backend)

1. Use `$FLOWCTL claude impl-review` exclusively
2. Pass `--receipt` for session continuity on re-reviews (session only resumes when prior receipt has `mode == "claude"`)
3. Model + effort resolved via (first match wins): `--spec claude:<model>:<effort>` flag, per-task `review`, `FLOW_REVIEW_BACKEND` spec, `FLOW_CLAUDE_MODEL` / `FLOW_CLAUDE_EFFORT` env vars, registry defaults. Effort set is the CLI's own: `low|medium|high|xhigh|max` (default `high`)
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
#   --spec <spec>           full spec (claude:<model>:<effort>), highest priority
#   FLOW_REVIEW_BACKEND     env (spec-form ok: claude:<model>:<effort>)
#   FLOW_CLAUDE_MODEL       env (fills missing model only; else registry default)
#   FLOW_CLAUDE_EFFORT      env (fills missing effort only; default high)
#   per-task stored review  via `flowctl task set-backend` (highest if set)

# Standalone branch reviews leave TASK_ID empty — OMIT the positional entirely
# (a quoted "" is rejected as an invalid task id; standalone mode needs no task arg).
# Subcommand tokens stay LITERAL on the command line (the Ralph guard blocks
# a variable in either of the two tokens after the launcher).
args=()
[ -n "$TASK_ID" ] && args+=("$TASK_ID")
args+=(--base "$DIFF_BASE" --receipt "$RECEIPT_PATH")
$FLOWCTL claude impl-review "${args[@]}"
```

**Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK|NEEDS_HUMAN`.**

The runner invokes `claude -p --output-format json --permission-mode dontAsk --tools Read Grep Glob --strict-mcp-config` with `cwd=repo_root`, the prompt on **stdin** (no argv transport cap), and `--model` / `--effort` from the resolved spec. Read-only by construction: `Read`, `Grep`, `Glob` are the only tools that exist for the child (no Bash, no Edit, no Write, no MCP tools), so the reviewer cannot run `git diff` itself — every primary dispatch materialises the reviewed range to `.flow/tmp/claude-review/<receipt-id>-<base7>-<head7>.diff` (gitignored) and the prompt names that path and the range; the reviewer reads it with `Read`. At the resolution ladder's floor the runner omits both `--model` and `--effort` and the receipt records `"effort": null`.

## Step 3: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from output
2. Fix code and run tests
3. Commit fixes
4. Re-run step 2 (receipt enables session continuity when `mode == "claude"`; the re-review resumes the same session with a new diff file for the new range)
5. Repeat until SHIP — bounded by the backend-agnostic fix-loop cap in [SKILL.md](SKILL.md) (`MAX_REVIEW_ITERATIONS`, default 8): count each fix+re-review cycle; at the cap, surface surviving findings and stop instead of looping

## Step 4: Receipt

Receipt is written automatically by `flowctl claude impl-review` when `--receipt` provided.
Format: `{"type":"impl_review","id":"<id>","mode":"claude","verdict":"<verdict>","session_id":"<uuid>","model":"<model>","effort":"<effort>","spec":"claude:<model>:<effort>","timestamp":"..."}`

The `spec` field is the canonical round-trippable form; `model` + `effort` are the resolved values (`effort` is `null` when the ladder floored). `mode` plus `model` name the family — read them for the same-family advisory above.

Session resume guard: re-review only resumes the claude session when the existing receipt at `$RECEIPT_PATH` has `mode == "claude"`. The first call omits `--resume` and captures the CLI's generated `session_id`; continuations pass `--resume <session_id>` using that persisted id. Session transcripts live in the CLI's own session store on disk. A cross-backend switch (e.g., codex receipt at the same path) starts a fresh session.

## Optional phases (gated by flags)

When the corresponding flag is set, run these phases from [optional-phases.md](optional-phases.md) — the dispatch matches the `claude` case in each phase; `deep-pass` and `validate` resume the primary session via the receipt and write no diff file (the session already holds the primary's):

- `--deep` → "Deep-Pass Phase" (Step D.1 → D.5)
- `--validate` → "Validator Pass" (Step V.1 → V.4)
- `--interactive` → "Interactive Walkthrough Phase" (Step W.1 → W.5)

See [optional-phases.md](optional-phases.md) "Phase ordering & flag-combination matrix" for the order when multiple flags are set.

---

## Anti-patterns (Claude backend)

- **Direct `claude -p` calls** - Must use `flowctl claude` wrappers
- **Inventing a `--model` CLI flag** - Use `--spec` for a full `claude:<model>:<effort>` value, or the `FLOW_CLAUDE_MODEL` / `FLOW_CLAUDE_EFFORT` env vars to fill the missing field
- **Widening the tool set** - `Read Grep Glob` is the whole reviewer tool set; a review that hands the child Bash, Edit, Write, `--allowedTools`, or an MCP config has broken the read-only contract
- **Fabricating a first-call `--resume` id** - The first call omits `--resume`; persist the CLI's returned `session_id` and resume with that. Session resume uses `--resume <uuid>` under the hood via `--receipt`
- **Assuming cross-backend session continuity** - Resume only works when prior receipt has `mode == "claude"`
- **Treating a same-family run as an error** - It is a recorded choice, not a refusal; `host` is the fail-closed backend
