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

## Convergence reservation fence (before every host dispatch)

After composing the complete reviewer input, but immediately before spawning the
host reviewer, build the plan artifact and reserve exactly one round. This fence
is the host equivalent of the RP transport fence; never reserve earlier and
never reserve again after a replay result.

```bash
ARTIFACT_FILE="${TMPDIR:-/tmp}/flow-plan-review-artifact-${SPEC_ID}.blob"
"$FLOWCTL" review-artifact plan "$SPEC_ID" --output "$ARTIFACT_FILE" --json
ROUND_JSON="$("$FLOWCTL" review-rounds increment "$SPEC_ID" --kind plan \
 --review-type plan --artifact-file "$ARTIFACT_FILE" --json)"
ROUND_EXIT=$?
if [[ "$ROUND_EXIT" -ne 0 ]]; then
 printf '%s\n' "$ROUND_JSON"
 if grep -Fq 'NOT_RETRYABLE: artifact unchanged since last verdict' <<<"$ROUND_JSON"; then
 # Human-action terminal: edit the artifact, explicitly reset, or use
 # human --force. Never refund, reset, force, or redispatch autonomously.
 exit 1
 fi
 exit "$ROUND_EXIT"
fi
if [[ "$(jq -r '.replayed // false' <<<"$ROUND_JSON")" == "true" ]]; then
 # Record/attach recovery delivered the prior verdict. Apply terminal
 # precedence NEEDS_HUMAN > MAJOR_RETHINK > NEEDS_WORK > all-SHIP; no
 # new dispatch.
 printf '%s\n' "$ROUND_JSON"
 # A superseded replay never votes (a concurrent SHIP reset the counter).
 if [[ "$(jq -r '[.replays[]? | select(.superseded != true) | .verdict] | if index("NEEDS_HUMAN") then "NEEDS_HUMAN" else "" end' <<<"$ROUND_JSON")" == "NEEDS_HUMAN" ]]; then
 echo "ESCALATE: reviewer requested human review" >&2
 exit 4
 fi
 exit 0
fi
RESERVATION_ID="$(jq -er '.reservation_id' <<<"$ROUND_JSON")"
```

After the reviewer returns, continue to **Receipt and status**. Assemble its
receipt input, receipt target, status target, and reviewer output file there
BEFORE calling `record`; the reservation is not consumable until then.

Read the AGENTS.md model-routing section, identify the writer family, and select
a reviewer slug from another family.

If no cross-family pin is available:

- Interactive: ask explicitly which reviewer family/model to use.
- Autonomous / Ralph / `REVIEW_RECEIPT_PATH`: stop with
 `NEEDS_HUMAN: host review needs a cross-family model pin in AGENTS.md model-routing`.

Dispatch one fresh read-only reviewer using the host primitive:
Immediately beforehand capture `REVIEW_HEAD_SHA="$(git rev-parse HEAD)"` and
retain that literal through receipt writing.

| Host | Pin/read-only contract |
|---|---|
| Claude Code | native model parameter + `disallowedTools: Edit, Write, Task` |
| Codex | `spawn_agent`, pin in prompt, platform read-only sandbox |
| Cursor | in-prompt slug + tool-enforced `readonly: true` agent |
| Grok | host pin + tool-enforced read-only; same-family writer fails closed |
| Other | fresh context; record that pin enforcement is host-dependent |

Give it the current spec, all task specs, and on re-review the receipt's
structured `findings.items` (ordinal, severity, classification, status, title,
and file:line) rather than the legacy review prose. Include focus areas and the
plan-review rubric from
[references/plan-review-prompt.md](references/plan-review-prompt.md). Require
exactly one `SHIP`, `NEEDS_WORK`, `MAJOR_RETHINK`, or `NEEDS_HUMAN` verdict tag. Wait
blocking for the result.

On re-review, also state the **prior-finding reply grammar verbatim**. These lines are
machine-read, and prose resolutions are invisible to the parser — a reviewer that
resolves priors in prose only leaves them carried forward and the loop cannot converge.
Require one line per prior finding, at the start of a line, echoing the ordinal it was
rendered with:

```
Prior finding #1: fixed
Prior finding #2: not-fixed
Prior finding #3: withdrawn
```

Allowed statuses: `fixed`, `not-fixed`, `withdrawn` — nothing else parses. With exactly
one prior finding the number may be omitted (`Prior finding: fixed`). When every prior
finding is fixed, the single line `Prior findings: all fixed` may replace the per-finding
lines. The `unaddressed` array in the JSON tail is about spec R-ID coverage and does
**not** vouch for prior findings.

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
 "verdict": "<SHIP|NEEDS_WORK|MAJOR_RETHINK|NEEDS_HUMAN>",
 "model": "<actual-reviewer-slug>",
 "spec": "host",
 "session_id": null,
 "review": "<full reviewer output>",
 "timestamp": "<ISO-8601>"
}
```

Write the base JSON and full reviewer output to temporary files. Then finalize
the captured reservation with those complete inputs, and attach from the
journaled payload (never re-derive it after `record`):

```bash
RECORD_JSON="$("$FLOWCTL" review-rounds record "$SPEC_ID" --kind plan \
 --review-type plan --backend host --output-file "$REVIEW_OUTPUT_FILE" \
 --reservation-id "$RESERVATION_ID" --receipt-target "$RECEIPT_PATH" \
 --receipt-payload-file "$RECEIPT_INPUT" --status-target plan --json)"
RECORD_EXIT=$?
printf '%s\n' "$RECORD_JSON"
[[ "$RECORD_EXIT" -eq 0 ]] || exit "$RECORD_EXIT"
"$FLOWCTL" review-findings attach --reservation-id "$RESERVATION_ID" \
 --receipt "$RECEIPT_PATH" \
 --json

if [[ "$VERDICT" == "NEEDS_HUMAN" ]]; then
 echo "ESCALATE: reviewer requested human review" >&2
 exit 4
fi
```

It reads any prior receipt before atomic replacement, carries only valid
same-backend plan lineage, and adds no reviewer/model/network call.

`record` owns plan status and the SHIP counter reset; the status leg is
journaled and lands with receipt publication (the `attach` above, or the
pre-increment replay gate), never before it.
Carry the verdict directly into SKILL.md's shared Fix Loop; an `ESCALATE:` or
`NOT_RETRYABLE:` fence exit never becomes a transport refund.

## Anti-patterns

- Self-review or silent same-family review
- Mutation-capable reviewer
- `flowctl host`, `host:<model>`, or fabricated session ids
- Reusing a previous subagent context
