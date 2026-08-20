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


**fn-169 — host is the documented always-inject exception.** The `codex` backend
resumes the reviewer's own session on a re-review and therefore sends the
shrink-only contract WITHOUT re-rendering prior findings; `cursor` and `copilot`
keep injecting unconditionally until their resume semantics are measured the way
codex's were (copilot's `--resume` is create-or-resume via a marker, so "resumed"
and "created" are not separable there). `host` cannot resume at all: rule 3
above makes each re-review a fresh subagent with `session_id: null`, so the
reviewer holds nothing from the previous round. The prior findings must travel in
the prompt here, and the reply grammar below is what makes them machine-readable.
This is a deliberate exception, tested (`test_review_prompt_no_embed_ratchet`
asserts `host` has no flowctl dispatch, and the capability set is asserted
exactly), not an oversight to be "simplified" later.

Everything else on the identities side still applies: point the subagent at the
`base..head` range and the changed-path list and let it read the diff and the
spec from the checkout itself. Do not paste diff hunks or spec bodies into the
subagent prompt — it has the same repository you do.

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

The reviewer runs on the **reviewer tier** — a verdict from the writer's own
family is not an independent one. **Routing precedence, highest first: an
explicit argument in the invocation, then the project routing block in the
instruction file, then the agent definition's own default, then the session
model.** How *this* harness reaches that model - and what degrades when it
cannot - is its reach page: [`docs/reach/README.md`](../../docs/reach/README.md).
A harness that reaches only one model family natively fails closed when the
writer shares that family (interactive -> ask; autonomous -> stop with
`NEEDS_HUMAN: host review needs a cross-family reviewer in the AGENTS.md
routing block`); cross-family then comes through a bridge backend.

Dispatch one fresh read-only reviewer. Immediately beforehand capture
`REVIEW_HEAD_SHA="$(git rev-parse HEAD)"` and retain that literal through
receipt writing. Read-only is enforced by TOOLS, never by prompt: dispatch
through a read-only agent definition or the host's read-only subagent mode
(`disallowedTools: Edit, Write, Task` where the host consumes it) - never a
mutation-capable subagent, because the reviewer reads untrusted content. Where
the host cannot enforce it, say so in the receipt. The dispatch prompt additionally states working-tree conduct: the reviewer never runs a mutating command (`git checkout`/`restore`/`clean`/`stash`, shell file writes) - tool fences do not cover the shell, and uncommitted state it finds is evidence to report, never something to repair.

Receipt in every case: `mode: "host"`, the actual reviewer model,
`session_id: null`.

Give it the repo-relative PATHS to the current spec and every task spec — not
their contents (fn-169: the subagent has the same checkout you do, and a plan
review is judged against the spec on disk, so a pasted copy can only go stale).
On re-review give it the receipt's
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
finding is fixed — and only then — the single line `Prior findings: all fixed` may
replace the per-finding lines; the two must not be mixed, because any per-finding line
present wins and disables the aggregate. The `unaddressed` array in the JSON tail is about spec R-ID coverage and does
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
# A refunded (no-verdict) record journals nothing attachable — record already
# completed its own bookkeeping; attach only a delivered verdict.
if [[ -n "$VERDICT" ]]; then
  "$FLOWCTL" review-findings attach --reservation-id "$RESERVATION_ID" \
    --receipt "$RECEIPT_PATH" \
    --json
fi

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
