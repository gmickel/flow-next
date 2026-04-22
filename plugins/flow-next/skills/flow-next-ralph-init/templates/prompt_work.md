You are running one Ralph work iteration.

Inputs:
- TASK_ID={{TASK_ID}}
- BRANCH_MODE={{BRANCH_MODE_EFFECTIVE}}
- WORK_REVIEW={{WORK_REVIEW}}                  (may be spec form, e.g. `codex:gpt-5.4:xhigh`)
- WORK_REVIEW_BACKEND={{WORK_REVIEW_BACKEND}}  (bare backend name — use this for `--review`)

The full spec is also exported as `FLOW_REVIEW_BACKEND` for flowctl to resolve model + effort.

## Steps (execute ALL in order)

**Step 1: Execute task**
```
/flow-next:work {{TASK_ID}} --branch={{BRANCH_MODE_EFFECTIVE}} --review={{WORK_REVIEW_BACKEND}}
```
`--review` takes the bare backend name (`rp`, `codex`, `copilot`, `none`). If
WORK_REVIEW was spec form (e.g. `copilot:claude-opus-4.5:xhigh`), the exported
`FLOW_REVIEW_BACKEND` carries the full spec through to flowctl which resolves
model + effort automatically.

When `--review=rp`, the worker subagent invokes `/flow-next:impl-review` internally.
When `--review=codex`, the worker uses `flowctl codex impl-review` for review.
When `--review=copilot`, the worker uses `flowctl copilot impl-review` for review.
The impl-review skill handles review coordination and requires `<verdict>SHIP|NEEDS_WORK|MAJOR_RETHINK</verdict>` from reviewer.
Do NOT improvise review prompts - the skill has the correct format.
Never call `copilot` directly; never pass `--continue` — session continuity is via stored UUID passed to `--resume=<uuid>`.

**Step 2: Verify task done** (AFTER skill returns)
```bash
scripts/ralph/flowctl show {{TASK_ID}} --json
```
If status != `done`, output `<promise>RETRY</promise>` and stop.

**Step 3: Write impl receipt** (MANDATORY if WORK_REVIEW_BACKEND=rp, codex, or copilot)
For rp mode:
```bash
mkdir -p "$(dirname '{{REVIEW_RECEIPT_PATH}}')"
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cat > '{{REVIEW_RECEIPT_PATH}}' <<EOF
{"type":"impl_review","id":"{{TASK_ID}}","mode":"rp","verdict":"SHIP","timestamp":"$ts","iteration":{{RALPH_ITERATION}}}
EOF
echo "Receipt written: {{REVIEW_RECEIPT_PATH}}"
```
For codex mode, receipt is written automatically by `flowctl codex impl-review --receipt`.
For copilot mode, receipt is written automatically by `flowctl copilot impl-review --receipt`.
**CRITICAL: Copy the command EXACTLY. The `"id":"{{TASK_ID}}"` and `"verdict":"SHIP"` fields are REQUIRED.**
Ralph verifies receipts match this exact schema. Missing id/verdict = verification fails = forced retry.

**Step 4: Validate epic**
```bash
scripts/ralph/flowctl validate --epic $(echo {{TASK_ID}} | sed 's/\.[0-9]*$//') --json
```

**Step 5: On hard failure** → output `<promise>FAIL</promise>` and stop.

## Rules
- Must run `flowctl done` and verify task status is `done` before commit.
- Must `git add -A` (never list files).
- Do NOT use TodoWrite.

## ⛔ FORBIDDEN OUTPUT
**NEVER output `<promise>COMPLETE</promise>`** — this prompt handles ONE task only.
Ralph detects all-work-complete automatically via the selector. Outputting COMPLETE here is INVALID and will be ignored.
