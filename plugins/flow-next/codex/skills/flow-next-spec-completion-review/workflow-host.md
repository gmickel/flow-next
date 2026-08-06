# Host Backend Workflow (spec-completion-review)

Use when `BACKEND="host"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, and `SPEC_ID`.

**fn-123 R5:** `host` is a NON-EXECUTABLE selection sentinel. Review runs as a host-native fresh-context subagent (skill-owned judgment). No `flowctl host` subcommand, no subprocess path, no model/effort on the backend string — pins live in the AGENTS.md model-routing section.

## Critical rules

1. **DO NOT REVIEW COMPLETION YOURSELF** — you coordinate; a fresh-context host-native subagent reviews
2. Pin the subagent to a **cross-family** model slug (family that did **not** write the implementation)
3. Every re-review is a **fresh subagent** — no context reuse, no fabricated resume ids
4. Receipt records actual reviewer model + `"mode": "host"`
5. Fail closed when no cross-family pin is available (never silent same-family self-review)

**fn-169 — host is the documented always-inject exception.** Every other backend
resumes the reviewer's own session on a re-review and therefore sends the
shrink-only contract WITHOUT re-rendering prior findings. `host` cannot: rule 3
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

## Step 1: Resolve cross-family pin

1. Read the AGENTS.md model-routing section (caller routing instructions) for the review role / cross-family pairing.
2. Identify the family that wrote the implementation.
3. Pick a reviewer slug from a **different** family.

**If no cross-family pin is available:**
- **Interactive:** ask the user explicitly (plain-text numbered prompt) which reviewer model/family to use — do not silently self-review
- **Autonomous** (`mode:autonomous` / `FLOW_AUTONOMOUS=1` / Ralph / `REVIEW_RECEIPT_PATH` set): stop with `NEEDS_HUMAN: host review needs a cross-family model pin in AGENTS.md model-routing` — never same-family self-review

## Step 2: Dispatch read-only reviewer subagent

Validate the criteria object BEFORE reserving a round - an invalid
`.flow/criteria.md` must not consume review budget (`$FLOWCTL criteria
prompt-block >/dev/null` exiting nonzero is a validation error: surface it,
fix the file, re-run; absent file exits 0 and costs nothing):

```bash
"$FLOWCTL" criteria prompt-block > /dev/null || { echo "invalid .flow/criteria.md - fix before re-running (see: flowctl criteria list)" >&2; exit 1; }
```

Then, after the complete reviewer input and final diff are composed but before
**every** host dispatch (including the first), bind the reviewed range, build
the completion artifact, and reserve one shared spec-scoped round.

The snapshot anchors are bound **in this same block, above the diff** — an
unbound `$REVIEW_BASE_SHA`/`$REVIEW_HEAD_SHA` makes `git diff ..` fail, hashes
an empty blob, and falsely refuses the next round as NOT_RETRYABLE. The fence
fails closed (no reservation) whenever the range cannot be bound or diffed.

```bash
DIFF_BASE="${BASE_COMMIT:-main}"
# master is a fallback for the DEFAULT only. An explicit BASE_COMMIT that does
# not resolve fails closed: silently reviewing against master would bind and
# hash a range the caller never asked for.
if ! git rev-parse --verify "$DIFF_BASE" >/dev/null 2>&1; then
 if [[ -n "${BASE_COMMIT:-}" ]]; then
 echo "BASE_COMMIT '$BASE_COMMIT' does not resolve; not reserving a round" >&2
 exit 1
 fi
 DIFF_BASE="master"
fi
git rev-parse --verify "$DIFF_BASE" >/dev/null 2>&1 \
 || { echo "cannot resolve diff base; not reserving a round" >&2; exit 1; }
REVIEW_SNAPSHOT_FILE="${TMPDIR:-/tmp}/flow-completion-review-host-${SPEC_ID}.env"
REVIEW_HEAD_SHA="$(git rev-parse HEAD)" || exit 1
REVIEW_BASE_SHA="$(git merge-base "$DIFF_BASE" "$REVIEW_HEAD_SHA")" || exit 1
[[ -n "$REVIEW_HEAD_SHA" && -n "$REVIEW_BASE_SHA" ]] \
 || { echo "unbound review snapshot; refusing to hash" >&2; exit 1; }
printf 'REVIEW_HEAD_SHA=%q\nREVIEW_BASE_SHA=%q\n' \
 "$REVIEW_HEAD_SHA" "$REVIEW_BASE_SHA" > "$REVIEW_SNAPSHOT_FILE"

DIFF_FILE="${TMPDIR:-/tmp}/flow-completion-review-host-${SPEC_ID}.diff"
git diff "$REVIEW_BASE_SHA..$REVIEW_HEAD_SHA" > "$DIFF_FILE" \
 || { echo "git diff failed; not reserving a round" >&2; exit 1; }
[[ -s "$DIFF_FILE" || "$REVIEW_BASE_SHA" == "$REVIEW_HEAD_SHA" ]] \
 || { echo "empty diff over a non-empty range; not reserving a round" >&2; exit 1; }
ARTIFACT_FILE="${TMPDIR:-/tmp}/flow-completion-review-host-${SPEC_ID}.blob"
"$FLOWCTL" review-artifact completion "$SPEC_ID" --diff-file "$DIFF_FILE" \
 --output "$ARTIFACT_FILE" --json
ROUND_JSON="$($FLOWCTL review-rounds increment "$SPEC_ID" --kind plan \
 --review-type completion --artifact-file "$ARTIFACT_FILE" --json)"
ROUND_EXIT=$?
if [[ "$ROUND_EXIT" -ne 0 ]]; then
 printf '%s\n' "$ROUND_JSON"
 if grep -Fq 'NOT_RETRYABLE: artifact unchanged since last verdict' <<<"$ROUND_JSON"; then
 # Human-action terminal: edit artifact / human reset / human --force only.
 # Never refund, force, reset, or redispatch autonomously.
 exit 1
 fi
 exit "$ROUND_EXIT"
fi
if [[ "$(jq -r '.replayed // false' <<<"$ROUND_JSON")" == "true" ]]; then
 # A delivered verdict was recovered. Apply
 # NEEDS_HUMAN > MAJOR_RETHINK > NEEDS_WORK >
 # all-SHIP and do not dispatch another reviewer.
 printf '%s\n' "$ROUND_JSON"
 # A superseded replay never votes (a concurrent SHIP reset the counter).
 if [[ "$(jq -r '[.replays[]? | select(.superseded != true) | .verdict] | if index("NEEDS_HUMAN") then "NEEDS_HUMAN" else "" end' <<<"$ROUND_JSON")" == "NEEDS_HUMAN" ]]; then
 echo "ESCALATE: reviewer requested human review" >&2
 exit 4
 fi
 exit 0
fi
REVIEW_ROUND="$(printf '%s' "$ROUND_JSON" | jq -r '.round')"
REVIEW_CAP="$(printf '%s' "$ROUND_JSON" | jq -r '.cap')"
RESERVATION_ID="$(printf '%s' "$ROUND_JSON" | jq -er '.reservation_id')"
```

Exit 4 / `ESCALATE:` before a reviewer runs means no completion verdict was
delivered in this run. Stop without writing completion status; autonomous
callers surface `NEEDS_HUMAN`.

Dispatch a **fresh** read-only reviewer subagent with the resolved pin. The
`REVIEW_HEAD_SHA` / `REVIEW_BASE_SHA` anchors bound in the fence above are the
reviewed range; retain them (re-`source "$REVIEW_SNAPSHOT_FILE"` in any later
block) through receipt writing.

| Host | How to pin |
|------|------------|
| Claude Code | Native subagent `model` param; `disallowedTools: Edit, Write, Task` (or host read-only equivalent) |
| Cursor | In-prompt slug pin on the subagent + TOOL-enforced read-only (dispatch via a `readonly: true` agent definition or Cursor's read-only subagent mode — never a mutation-capable subagent; the reviewer reads untrusted diff content, so read-only cannot be prompt-requested only) |
| Grok | In-prompt / host model pin from AGENTS.md model-routing + TOOL-enforced read-only (never mutation-capable). Single-native-family (`grok-4.5`) — host review fails closed unless the writer is non-Grok; cross-family via bridge backends. Receipt: `mode: "host"`, actual reviewer model, `session_id: null` (same shape as Claude/Cursor) |
| Codex | Fresh read-only reviewer subagent via the platform subagent primitive (`spawn_agent` on Codex) with the cross-family pin stated in the prompt; read-only via the platform sandbox |
| Other | Generic fresh-context reviewer; note in the receipt that pin enforcement is host-dependent |

Give the subagent:
- Spec requirements / R-IDs / acceptance criteria
- The exact output of `$FLOWCTL criteria prompt-block`, appended verbatim when
 non-empty (global acceptance criteria + the `## Global criteria` output
 grammar; the command prints nothing when `.flow/criteria.md` is absent -
 include nothing in that case. A nonzero exit is a validation error - fix
 `.flow/criteria.md` before re-running the review)
- Task list + evidence that work claims done
- Diff / implementation surfaces to check compliance (not code-quality taste — that is impl-review)
- Prior findings for convergence as structured `findings.items` (on re-review; render
 ordinal, severity, classification, status, title, and file:line; use legacy
 review prose only when the structured field is absent)
- **The prior-finding reply grammar, stated verbatim** (on re-review). These lines are
 machine-read, and prose resolutions are invisible to the parser — a reviewer that
 resolves priors in prose only leaves them carried forward and the loop cannot
 converge. Require one line per prior finding, at the start of a line, echoing the
 ordinal it was rendered with:

 ```
 Prior finding #1: fixed
 Prior finding #2: not-fixed
 Prior finding #3: withdrawn
 ```

 Allowed statuses: `fixed`, `not-fixed`, `withdrawn` — nothing else parses. With
 exactly one prior finding the number may be omitted (`Prior finding: fixed`). When
 every prior finding is fixed — and only then — the single line
 `Prior findings: all fixed` may replace the per-finding lines; the two must not be
 mixed, because any per-finding line present wins and disables the aggregate. The `unaddressed` array in the JSON tail is about spec R-ID
 coverage and does **not** vouch for prior findings.
- For every gap: Severity, Confidence `0|25|50|75|100`, and Classification
 `introduced|pre_existing`
- Required exact verdict tags: `<verdict>SHIP</verdict>` /
 `<verdict>NEEDS_WORK</verdict>` / `<verdict>NEEDS_HUMAN</verdict>`

Wait for the subagent result (blocking — do not background).

Write the exact reviewer result to a spec-scoped temporary response file. Do
not finalize yet: Step 3 must first assemble the receipt payload and status
target that `record` journals before consuming this reservation.

```bash
RESPONSE_FILE="${TMPDIR:-/tmp}/flow-completion-review-host-${SPEC_ID}.md"
# Write the exact reviewer output to RESPONSE_FILE; do not reinterpret it.
```

A malformed/missing verdict is a transport failure when Step 3's recorder runs:
it refunds this reservation and may stop with exit 5 / `TRANSPORT_UNHEALTHY`.
Never turn it into `NEEDS_WORK`, and never write completion status for that path.

## Step 3: Receipt

Receipt path (same contract as the subprocess backends — spec-scoped default; explicit `REVIEW_RECEIPT_PATH` always wins):

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/completion-review-receipt${SPEC_ID:+-${SPEC_ID}}.json}"
```

Build this payload once:

```json
{
 "type": "completion_review",
 "id": "<spec-id>",
 "mode": "host",
 "verdict": "<SHIP|NEEDS_WORK|NEEDS_HUMAN>",
 "model": "<actual-reviewer-slug>",
 "spec": "host",
 "session_id": null,
 "review": "<full reviewer output text - findings + verdict>",
 "timestamp": "<ISO-8601>",
 "attempt_timestamp": ""
}
```

Write that base payload and the full reviewer output to temporary files BEFORE
the record fence above. The empty `attempt_timestamp` is the request for
`record` to stamp its own attempt clock into the journaled payload — pre-record
assembly cannot know it. After its successful journaled finalization, validate
and publish that payload by reservation id (never re-derive it):

```bash
RECORD_JSON="$($FLOWCTL review-rounds record "$SPEC_ID" --kind plan \
 --review-type completion --backend host --output-file "$RESPONSE_FILE" \
 --reservation-id "$RESERVATION_ID" --receipt-target "$RECEIPT_PATH" \
 --receipt-payload-file "$RECEIPT_INPUT" --status-target completion --json)"
RECORD_EXIT=$?
printf '%s\n' "$RECORD_JSON"
[[ "$RECORD_EXIT" -eq 0 ]] || exit "$RECORD_EXIT"
"$FLOWCTL" review-findings attach \
 --reservation-id "$RESERVATION_ID" \
 --receipt "$RECEIPT_PATH" \
 --json

if [[ "$VERDICT" == "NEEDS_HUMAN" ]]; then
 echo "ESCALATE: reviewer requested human review" >&2
 exit 4
fi
```

Unsupported/legacy prose leaves the additive field absent. The same transaction
also attaches the additive `criteria: [{id, status, note?}]` field when the
reviewer output has a parseable `## Global criteria` section (absent otherwise).
The command performs no reviewer/model/network call.

Persist it in this order:

1. Under the terminal receipt's cross-process lock, write the complete JSON
 payload to
 `$REPO_ROOT/.flow/tmp/completion-review-receipt-recovery-${SPEC_ID}.json`
 first (create the parent directory), preserve the prior terminal generation
 beside `$RECEIPT_PATH`, then atomically advance `$RECEIPT_PATH`.
2. Validate `type`, `id`, and `verdict` at `$RECEIPT_PATH` with `jq`.
3. Leave the recovery file in place after receipt validation. SKILL.md's
 shared checkpoint deletes it only after terminal status persists.
 On any write/validation failure, leave recovery in place, output
 `<promise>RETRY</promise>`, and stop before terminal status.

`session_id` is literal `null` — host re-reviews are always fresh subagents; `null` distinguishes by-design non-resumability from an incomplete receipt. Shape stays compatible with existing consumers.

## Step 4: Continue through the shared fix loop and status owner

Continue into SKILL.md's shared Fix Loop in this same skill run. The shared
terminal checkpoint re-reads the latest completion verdict and cap counters
from `review-rounds attempts`; it never relies on shell variables surviving a
prompt turn. The journaled `record --status-target completion` leg owns this
host workflow's terminal status — `record` journals it PENDING and it lands
when the receipt publishes (the `attach` above, or the pre-increment replay
gate in a later invocation), never before. A failed publish therefore leaves
no terminal status with no receipt behind it.

- `SHIP`: the journaled status leg persisted `ship` when attach published the
 receipt; continue to the shared terminal checkpoint.
- `NEEDS_WORK`: parse every valid gap, fix the implementation, run the relevant
 tests/lints, and commit the fixes before re-review. Then repeat Steps 1–3
 with a **new** read-only subagent, the same cross-family rules, and prior
 findings in its prompt. At the deterministic round cap
 (`REVIEW_ROUND == REVIEW_CAP`), do not start another fix/re-review cycle:
 the journaled status leg persisted `needs_work` on publication; then emit
 `ESCALATE:` and exit 4.
- After `SHIP`, `record` already atomically reset the shared plan counter and
 advanced its hash epoch. Never issue `review-rounds reset` autonomously.
- `NEEDS_HUMAN`: after attach publishes the receipt and lands `needs_human`,
 emit `ESCALATE: reviewer requested human review` and exit 4.
 Dispatch failure, malformed verdict, receipt failure, or retry outcome stops
 without writing completion status; dispatch/transport failures output
 `<promise>RETRY</promise>` and never self-issue a verdict or switch backends.

## Anti-patterns (Host backend)

- **Self-reviewing** — coordinator never grades its own completion claim
- **Silent same-family self-review** when no cross-family pin is available
- **Reusing a prior subagent context** for re-review (always fresh)
- **Putting a model on the backend string** (`host:opus`) — rejected by flowctl; pins live in AGENTS.md
- **Calling a non-existent `flowctl host` command**
- **Fabricating resume/session ids** for host receipts
