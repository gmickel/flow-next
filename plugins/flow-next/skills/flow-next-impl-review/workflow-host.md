# Host Backend Workflow (impl-review)

Use when `BACKEND="host"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, and (optionally) `TASK_ID` / `BASE_COMMIT`.

**fn-123 R5:** `host` is a NON-EXECUTABLE selection sentinel. Review runs as a host-native fresh-context subagent (skill-owned judgment). No `flowctl host` subcommand, no subprocess path, no model/effort on the backend string — pins live in the AGENTS.md model-routing section.

## Critical rules

1. **The coordinator never reviews code itself** — you coordinate; a fresh-context host-native subagent reviews. A verdict formed without that subagent's response has broken this
2. Pin the subagent to a **cross-family** model slug (family that did **not** write the diff)
3. Every re-review is a **fresh subagent** — no context reuse, no fabricated resume ids
4. Receipt records actual reviewer model + `"mode": "host"`
5. Fail closed when no cross-family pin is available (never silent same-family self-review)


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

## Step 1: Resolve cross-family pin

1. Read the AGENTS.md model-routing section (caller routing instructions) for the review role / cross-family pairing.
2. Identify the family that wrote the diff (session model / implementer family).
3. Pick a reviewer slug from a **different** family (uncorrelated blind spots).

**If no cross-family pin is available:**
- **Interactive:** ask the user explicitly (blocking question) which reviewer model/family to use — do not silently self-review
- **Autonomous** (`mode:autonomous` / `FLOW_AUTONOMOUS=1` / Ralph / `REVIEW_RECEIPT_PATH` set): stop with `NEEDS_HUMAN: host review needs a cross-family model pin in AGENTS.md model-routing` — never same-family self-review

## Step 2: Dispatch read-only reviewer subagent

### Convergence reservation and recovery fence

After the exact reviewer input is composed and immediately before every host
dispatch, bind the reviewed range, build the artifact blob, and reserve one
task-scoped round. The full diff is materialized **for the artifact hash only** —
it is the identity that must move when the code moves. It does not go into the
subagent prompt: give the subagent `$REVIEW_BASE_SHA..$REVIEW_HEAD_SHA`, the
`git diff --numstat --no-renames` path list for that range, and the task-spec
PATH, and let it read the spec and the hunks itself. Capture its id; it is the only
id that may finalize or refund this dispatch.

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
REVIEW_SNAPSHOT_FILE="${TMPDIR:-/tmp}/flow-impl-review-host-${TASK_ID:-branch}.env"
REVIEW_HEAD_SHA="$(git rev-parse HEAD)" || exit 1
REVIEW_BASE_SHA="$(git merge-base "$DIFF_BASE" "$REVIEW_HEAD_SHA")" || exit 1
[[ -n "$REVIEW_HEAD_SHA" && -n "$REVIEW_BASE_SHA" ]] \
  || { echo "unbound review snapshot; refusing to hash" >&2; exit 1; }
printf 'REVIEW_HEAD_SHA=%q\nREVIEW_BASE_SHA=%q\n' \
  "$REVIEW_HEAD_SHA" "$REVIEW_BASE_SHA" > "$REVIEW_SNAPSHOT_FILE"

DIFF_FILE="${TMPDIR:-/tmp}/flow-impl-review-host-${TASK_ID:-branch}.diff"
git diff "$REVIEW_BASE_SHA..$REVIEW_HEAD_SHA" > "$DIFF_FILE" \
  || { echo "git diff failed; not reserving a round" >&2; exit 1; }
[[ -s "$DIFF_FILE" || "$REVIEW_BASE_SHA" == "$REVIEW_HEAD_SHA" ]] \
  || { echo "empty diff over a non-empty range; not reserving a round" >&2; exit 1; }
ARTIFACT_FILE="${TMPDIR:-/tmp}/flow-impl-review-host-${TASK_ID:-branch}.blob"
"$FLOWCTL" review-artifact impl "${TASK_ID%.*}" --diff-file "$DIFF_FILE" \
  --output "$ARTIFACT_FILE" --json
ROUND_JSON="$("$FLOWCTL" review-rounds increment "${TASK_ID%.*}" --kind impl \
  --task "$TASK_ID" --review-type impl --artifact-file "$ARTIFACT_FILE" --json)"
ROUND_EXIT=$?
if [[ "$ROUND_EXIT" -ne 0 ]]; then
  printf '%s\n' "$ROUND_JSON"
  if grep -Fq 'NOT_RETRYABLE: artifact unchanged since last verdict' <<<"$ROUND_JSON"; then
    # Human-action terminal: edit artifact / human reset / human --force only.
    # Never refund, force, reset, or redispatch from an autonomous loop.
    exit 1
  fi
  exit "$ROUND_EXIT"
fi
if [[ "$(jq -r '.replayed // false' <<<"$ROUND_JSON")" == "true" ]]; then
  # Recovered verdict terminal precedence:
  # NEEDS_HUMAN > MAJOR_RETHINK > NEEDS_WORK > all-SHIP.
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

After the reviewer returns, construct the receipt input and target in Step 3.
Only then record the captured reservation and attach its journaled payload;
receipt findings must never be constructed after `record`.

Dispatch a **fresh** read-only reviewer subagent with the resolved pin. The
`REVIEW_HEAD_SHA` / `REVIEW_BASE_SHA` anchors bound in the fence above are the
reviewed range; retain them (re-`source "$REVIEW_SNAPSHOT_FILE"` in any later
block) through receipt writing.

| Host | How to pin |
|------|------------|
| Claude Code | Native subagent `model` param (existing reviewer-subagent arrangement); `disallowedTools: Edit, Write, Task` (or host read-only equivalent) |
| Cursor | In-prompt slug pin on the subagent + TOOL-enforced read-only (dispatch via a `readonly: true` agent definition or Cursor's read-only subagent mode — never a mutation-capable subagent; the reviewer reads untrusted diff content, so read-only cannot be prompt-requested only) |
| Grok | In-prompt / host model pin from AGENTS.md model-routing + TOOL-enforced read-only (never mutation-capable). Single-native-family (grok, e.g. `grok-4.6`) — host review fails closed unless the writer is non-Grok; cross-family via bridge backends. Receipt: `mode: "host"`, actual reviewer model, `session_id: null` (same shape as Claude/Cursor) |
| Codex | Fresh read-only reviewer subagent via the platform subagent primitive (`spawn_agent` on Codex) with the cross-family pin stated in the prompt; read-only via the platform sandbox |
| Other | Generic fresh-context reviewer; note in the receipt that pin enforcement is host-dependent |

Give the subagent:
- The impl-review rubric ([references/impl-review-prompt.md](references/impl-review-prompt.md))
- Diff scope (`--base` / branch vs main as resolved in Phase 0)
- Task id / focus areas if any
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
- Required verdict tags: `SHIP` / `NEEDS_WORK` / `MAJOR_RETHINK` / `NEEDS_HUMAN`

Wait for the subagent result (blocking — do not background).

## Step 3: Receipt

Receipt path (same contract as the subprocess backends — fn-90 task-scoped default; explicit `REVIEW_RECEIPT_PATH` always wins):

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt${TASK_ID:+-${TASK_ID}}.json}"
```

Write a receipt compatible with existing consumers:

```json
{
  "type": "impl_review",
  "id": "<task-id or branch scope>",
  "mode": "host",
  "verdict": "<SHIP|NEEDS_WORK|MAJOR_RETHINK|NEEDS_HUMAN>",
  "model": "<actual-reviewer-slug>",
  "spec": "host",
  "session_id": null,
  "review": "<full reviewer output text - findings + verdict>",
  "timestamp": "<ISO-8601>"
}
```

`session_id` is literal `null` — deliberate: host re-reviews are always fresh subagents, and `null` distinguishes "no resumable session by design" from an accidentally incomplete receipt. `review` carries the reviewer's full output — the re-review ratchet reads it to inject prior findings into the next fresh subagent (convergence), so a host receipt that omits `review` has broken the convergence ratchet.

Write that base JSON to a temporary input file and persist the full reviewer
output to a second temporary file. Finalize the captured reservation first,
then attach from that journaled payload so host receipts follow the same
lineage/currentness contract as subprocess backends:

```bash
RECORD_JSON="$("$FLOWCTL" review-rounds record "${TASK_ID%.*}" --kind impl \
  --task "$TASK_ID" --review-type impl --backend host \
  --output-file "$REVIEW_OUTPUT_FILE" --reservation-id "$RESERVATION_ID" \
  --receipt-target "$RECEIPT_PATH" --receipt-payload-file "$RECEIPT_INPUT" --json)"
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

The command reads the prior receipt before atomically replacing it. Unsupported
or legacy prose preserves the base receipt without a `findings` field; no extra
reviewer, model, or network call occurs.

Do **not** invent a `session_id` for resume — host re-reviews always spawn a new subagent. Shape stays compatible with convergence/cap/pilot/land consumers (`mode`, `verdict`, `model`, `timestamp`).

## Step 4: Optional phases

When `--deep` / `--validate` / `--interactive` flags are set, run the gated phases from [optional-phases.md](optional-phases.md) where they apply. Host has no `flowctl host deep-pass` / `validate` — if those paths require a subprocess backend, either:
- run the pass as another host-native read-only subagent with the same cross-family pin, or
- skip with an explicit note in the receipt when the pass cannot run without a CLI backend

Never silently drop a required gate without a note.

## Step 5: Continue through the shared fix loop

Carry the verdict directly into SKILL.md's shared Fix Loop in this same skill
run.

- `SHIP`: complete the review contract.
- `MAJOR_RETHINK`: continue into the shared `BLOCKED: DESIGN_CONFLICT`
  terminal; do not patch the design.
- `NEEDS_WORK`: parse every valid finding, fix the code, run the relevant
  tests/lints, and commit the fixes before re-review. Then repeat Steps 1–4
  with a **new** read-only subagent, the same cross-family rules, and the prior
  findings in its prompt. Continue until `SHIP` or the deterministic round cap.
- Dispatch, malformed-verdict, or receipt failure: output
  `<promise>RETRY</promise>` and stop. Never self-issue a verdict or switch
  backends.

## Anti-patterns (Host backend)

- **Self-reviewing** — coordinator never grades its own diff
- **Silent same-family self-review** when no cross-family pin is available
- **Reusing a prior subagent context** for re-review (always fresh)
- **Putting a model on the backend string** (`host:opus`) — rejected by flowctl; pins live in AGENTS.md
- **Calling a non-existent `flowctl host` command**
- **Fabricating resume/session ids** for host receipts
