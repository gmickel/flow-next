# Plan Review Workflow — Host Backend

Use only when `BACKEND="host"` after [workflow.md](workflow.md).

`host` is a non-executable selection sentinel. It has no `flowctl host`
subcommand and accepts no model/effort suffix.

## Critical rules

1. The coordinator does not review the plan.
2. Dispatch a fresh, tool-enforced read-only reviewer pinned to a different
   model family than the plan author.
3. Every re-review is a new subagent; prior findings provide convergence
   context, never a fabricated resume id.
4. Receipt mode is `host`, actual reviewer model is recorded, and
   `session_id` is literal `null`.
5. Missing cross-family pin fails closed.

## Resolve and dispatch

Read the AGENTS.md model-routing section, identify the writer family, and select
a reviewer slug from another family.

If no cross-family pin is available:

- Interactive: ask explicitly which reviewer family/model to use.
- Autonomous / Ralph / `REVIEW_RECEIPT_PATH`: stop with
  `NEEDS_HUMAN: host review needs a cross-family model pin in AGENTS.md model-routing`.

Dispatch one fresh read-only reviewer using the host primitive:

| Host | Pin/read-only contract |
|---|---|
| Claude Code | native model parameter + `disallowedTools: Edit, Write, Task` |
| Codex | `spawn_agent`, pin in prompt, platform read-only sandbox |
| Cursor | in-prompt slug + tool-enforced `readonly: true` agent |
| Grok | host pin + tool-enforced read-only; same-family writer fails closed |
| Other | fresh context; record that pin enforcement is host-dependent |

Give it the current spec, all task specs, prior findings on re-review, focus
areas, and the plan-review rubric from
[references/plan-review-prompt.md](references/plan-review-prompt.md). Require
exactly one `SHIP`, `NEEDS_WORK`, or `MAJOR_RETHINK` verdict tag. Wait
blocking for the result.

## Receipt and status

Use:

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/plan-review-receipt-${SPEC_ID}.json}"
```

Write:

```json
{
  "type": "plan_review",
  "id": "<spec-id>",
  "mode": "host",
  "verdict": "<SHIP|NEEDS_WORK|MAJOR_RETHINK>",
  "model": "<actual-reviewer-slug>",
  "spec": "host",
  "session_id": null,
  "review": "<full reviewer output>",
  "timestamp": "<ISO-8601>"
}
```

After every verdict, including re-review, write latest status:

```bash
$FLOWCTL spec set-plan-review-status "$SPEC_ID" --status ship --json
# or
$FLOWCTL spec set-plan-review-status "$SPEC_ID" --status needs_work --json
```

Before each host re-review dispatch, call the deterministic cap:

```bash
$FLOWCTL review-rounds increment "$SPEC_ID" --kind plan --json
```

Exit 4 / `ESCALATE:` means do not dispatch. On `SHIP`, reset plan rounds.
Return the verdict to SKILL.md's shared fix loop.

## Anti-patterns

- Self-review or silent same-family review
- Mutation-capable reviewer
- `flowctl host`, `host:<model>`, or fabricated session ids
- Reusing a previous subagent context
