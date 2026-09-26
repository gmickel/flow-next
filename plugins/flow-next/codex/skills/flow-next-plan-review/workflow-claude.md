# Plan Review Workflow — Claude Backend

Use only when `BACKEND="claude"` after [workflow.md](workflow.md).

**Same-family advisory:** on a Claude Code host the writer and this reviewer
share a model family; the receipt records it (`mode: "claude"` plus `model`)
and the run proceeds. Prefer `codex` or `host` there when family independence
matters.

## Critical rules

1. Use `$FLOWCTL claude plan-review` exclusively.
2. Pass `--receipt`; resume only when the prior receipt mode is `claude`.
3. Claude takes a model and an effort (`low|medium|high|xhigh|max`, default
   `high`): `--spec claude:<model>:<effort>`, or `FLOW_CLAUDE_MODEL` /
   `FLOW_CLAUDE_EFFORT` to fill a missing field.
4. Run the read-only dispatch as one blocking foreground call.

## Execute Review — one atomic fence

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
SPEC_ID="<spec id resolved in workflow.md Phase 0>"   # substitute literally
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-$(git rev-parse --show-toplevel)/.flow/tmp/plan-review-receipt-${SPEC_ID}.json}"

$FLOWCTL checkpoint save --spec "$SPEC_ID" --json
$FLOWCTL claude plan-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
```

Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK|NEEDS_HUMAN`. The handler owns
status, cumulative rounds, and receipt writes. Claude invokes
`claude -p --output-format json --permission-mode dontAsk --tools Read Grep Glob --strict-mcp-config`
in the repo root with the prompt on stdin; the reviewer holds only the three
read tools (no Bash, no write tool, no MCP). The receipt carries `model` and
`effort` (`effort` is `null` when the ladder floored).

Carry the verdict directly into SKILL.md's shared Fix Loop. The first call
omits a resume id; only a persisted same-mode `session_id` enables continuation
(`--resume <session_id>`; transcripts live in the CLI's own session store).

## Anti-patterns

- Direct `claude -p` calls
- Widening the tool set past `Read Grep Glob`, or fabricating a first-call resume id
- Cross-backend session reuse
- Treating a same-family run as an error (it is recorded, never refused; `host` fails closed)
