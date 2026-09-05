# Spec Completion Review Workflow — Claude Backend

Use when `BACKEND="claude"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, and `SPEC_ID`.

Claude shells out to the Claude Code CLI (headless `claude -p`), billed against the user's Claude subscription or API key. This is the **review backend**, independent of Claude Code as the primary host.

**Same-family advisory:** on a Claude Code host the writer and this reviewer share a model family; the receipt records it (`mode: "claude"` plus `model`) and the run proceeds. Prefer `codex` or `host` there when family independence matters — `host` fails closed on same-family review; `claude` never refuses.

## Critical rules (claude backend)

1. Use `$FLOWCTL claude completion-review` exclusively
2. Pass `--receipt` for session continuity on re-reviews (session only resumes when prior receipt has `mode == "claude"`)
3. Model + effort resolved via (first match wins): `--spec claude:<model>:<effort>` flag, per-spec `default_review`, `FLOW_REVIEW_BACKEND` spec, `FLOW_CLAUDE_MODEL` / `FLOW_CLAUDE_EFFORT` env vars, registry defaults. Effort set: `low|medium|high|xhigh|max` (default `high`)
4. Parse verdict from command output

## Step 1: Identify Spec

```bash
# SPEC_ID from arguments (e.g., fn-1, fn-22-53k)
$FLOWCTL show "$SPEC_ID" --json
```

## Step 2: Execute Review

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/completion-review-receipt-${SPEC_ID}.json}"  # fn-90 R5: spec-scoped default (concurrent specs no longer collide); explicit REVIEW_RECEIPT_PATH still wins

# Runtime config:
#   --spec <spec>           full spec (claude:<model>:<effort>), highest priority
#   FLOW_REVIEW_BACKEND     spec-form ok: claude:<model>:<effort>
#   FLOW_CLAUDE_MODEL       fills missing model only (else registry default)
#   FLOW_CLAUDE_EFFORT      fills missing effort only (default high)

$FLOWCTL claude completion-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
```

**Output includes `VERDICT=SHIP|NEEDS_WORK|NEEDS_HUMAN`.**

The runner invokes `claude -p --output-format json --permission-mode dontAsk --tools Read Grep Glob --strict-mcp-config` with `cwd=repo_root`, the prompt on stdin, and `--model` / `--effort` from the resolved spec. `Read`, `Grep`, `Glob` are the only tools that exist for the child (no Bash, no write tool, no MCP tools); the reviewed diff is materialised to `.flow/tmp/claude-review/<receipt-id>-<base7>-<head7>.diff` and named in the prompt, so the reviewer reads it with `Read` instead of running git. At the ladder floor the runner omits both `--model` and `--effort`.

## Step 3: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from output
2. Fix code and run tests
3. Commit fixes
4. Re-run step 2 (receipt enables session continuity when `mode == "claude"`; the re-review resumes the session with a new diff file for the new range)
5. Repeat until SHIP

## Step 4: Receipt

Receipt is written automatically by `flowctl claude completion-review` when `--receipt` provided.
Format: `{"type":"completion_review","id":"<spec-id>","mode":"claude","verdict":"<verdict>","session_id":"<uuid>","model":"<model>","effort":"<effort>","spec":"claude:<model>:<effort>","timestamp":"..."}`

The `spec` field is the canonical round-trippable form; `model` + `effort` are the resolved values (`effort` absent when the ladder floored). `mode` plus `model` name the family — read them for the same-family advisory above.

When `.flow/criteria.md` exists, the prompt includes the project's global acceptance criteria and the receipt may carry the additive `criteria: [{id, status, note?}]` field (absent when the reviewer output has no parseable `## Global criteria` section).

Session resume guard: re-review only resumes the claude session when the existing receipt at `$RECEIPT_PATH` has `mode == "claude"`. The first call omits `--resume` and captures the CLI's generated `session_id`; continuations pass `--resume <session_id>`. Transcripts live in the CLI's own session store. Cross-backend switches start a fresh session.

---

## Anti-patterns (Claude backend)

- **Direct `claude -p` calls** - Must use `flowctl claude` wrappers
- **Inventing a `--model` CLI flag** - Use `--spec` for a full `claude:<model>:<effort>` value, or the `FLOW_CLAUDE_MODEL` / `FLOW_CLAUDE_EFFORT` env vars to fill the missing field
- **Widening the tool set** - `Read Grep Glob` is the whole reviewer tool set; Bash, Edit, Write, `--allowedTools`, or an MCP config breaks the read-only contract
- **Fabricating a first-call `--resume` id** - The first call omits `--resume`; persist the CLI's returned `session_id` and resume with that
- **Assuming cross-backend session continuity** - Resume only works when prior receipt has `mode == "claude"`
- **Treating a same-family run as an error** - It is a recorded choice, not a refusal; `host` is the fail-closed backend
