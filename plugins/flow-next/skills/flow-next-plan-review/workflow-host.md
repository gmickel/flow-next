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
6. **`host` never shells out to another CLI.** A `codex exec` / `cursor-agent` /
   `claude -p` / `grok` subprocess inside a host review is a broken run — the
   CLI backends exist for exactly that; the user chose `host` to avoid them.
   The subagent is dispatched through the harness's own primitive with the
   model named in the dispatch; a harness that does not honor the model
   request degrades to the session model, and then rule 2's fail-closed
   cross-family check decides — never a CLI fallback.


Everything else on the identities side still applies: point the subagent at the
`base..head` range and the changed-path list and let it read the diff and the
spec from the checkout itself. Do not paste diff hunks or spec bodies into the
subagent prompt — it has the same repository you do.

## Resolve and dispatch

## Convergence reservation fence (before every host dispatch)

After composing the complete reviewer input, but immediately before spawning the
host reviewer, build the plan artifact and reserve exactly one round. This fence
is the host review's transport fence; never reserve earlier and
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

The reviewer runs on the **reviewer tier** — a verdict from the writer's own
family is not an independent one. **Routing precedence, highest first: an
explicit argument in the invocation, then the project routing block in the
instruction file, then the agent definition's own default, then the session
model.** How *this* harness reaches that model - and what degrades when it
cannot - is its reach page: [`docs/reach/README.md`](../../docs/reach/README.md).
A harness that reaches only one model family natively fails closed when the
writer shares that family (interactive -> ask; autonomous -> stop with
`NEEDS_HUMAN: host review needs a cross-family reviewer in the model-routing
block`); cross-family then comes through a bridge backend.

Dispatch one fresh read-only reviewer. Immediately beforehand capture
`REVIEW_HEAD_SHA="$(git rev-parse HEAD)"` and retain that literal through
receipt writing. Read-only is enforced by TOOLS, never by prompt: dispatch
through a read-only agent definition or the host's read-only subagent mode
(`disallowedTools: Edit, Write, Task` where the host consumes it) - never a
mutation-capable subagent, because the reviewer reads untrusted content. Where
the host cannot enforce it, say so in the receipt. The dispatch prompt additionally states working-tree conduct: the reviewer never runs a mutating command (`git checkout`/`restore`/`clean`/`stash`, shell file writes) - tool fences do not cover the shell, and uncommitted state it finds is evidence to report, never something to repair.

Receipt in every case: `mode: "host"`, the actual reviewer model,
`session_id: null`.

Render the dispatch file with the shared backend builder:

```bash
"$FLOWCTL" review-prompt plan "$SPEC_ID" --receipt "$RECEIPT_PATH" \
  --out "${TMPDIR:-/tmp}/flow-plan-review-${SPEC_ID}.md" --json || exit $?
```

Dispatch the generated prompt verbatim; it already supplies paths, rubric and
prior-finding grammar. Do not reconstruct its contents by hand.

It also carries the verdict tags and, on re-review, the prior findings. Add only the focus
areas, and wait blocking for the result.

## Receipt and status

Use:

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-$(git rev-parse --show-toplevel)/.flow/tmp/plan-review-receipt-${SPEC_ID}.json}"
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
  "head": "<REVIEW_HEAD_SHA>",
  "timestamp": "<ISO-8601>"
}
```

Write the base JSON and full reviewer output to temporary files. Then finalize
the captured reservation with those complete inputs, and attach from the
journaled payload (never re-derive it after `record`):

```bash
RECORD_JSON="$("$FLOWCTL" review-rounds record "$SPEC_ID" --kind plan \
  --review-type plan --backend host --output-file "$REVIEW_OUTPUT_FILE" \
  --model "<actual reviewer slug>" \
  --reservation-id "$RESERVATION_ID" --receipt-target "$RECEIPT_PATH" \
  --receipt-payload-file "$RECEIPT_INPUT" --status-target plan --attach --json)"
RECORD_EXIT=$?
if [[ "$RECORD_EXIT" -ne 0 ]]; then
  printf '%s\n' "$RECORD_JSON"
  exit "$RECORD_EXIT"
fi
# Only the fields the next step reads; the full ledger stays in flowctl.
printf '%s' "$RECORD_JSON" | jq -c '{superseded: (.superseded // false), verdict: .verdict, timestamp: .attempts[-1].timestamp, review_rounds}'

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
