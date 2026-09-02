# Host Backend Workflow (impl-review)

Use when `BACKEND="host"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, and (optionally) `TASK_ID` / `BASE_COMMIT`.

**fn-123 R5:** `host` is a NON-EXECUTABLE selection sentinel. Review runs as a host-native fresh-context subagent (skill-owned judgment). No `flowctl host` subcommand, no subprocess path, no model/effort on the backend string — pins live in the AGENTS.md model-routing section.

## Critical rules

1. **The coordinator never reviews code itself** — you coordinate; a fresh-context host-native subagent reviews. A verdict formed without that subagent's response has broken this
2. Pin the subagent to a **cross-family** model slug (family that did **not** write the diff)
3. Every re-review is a **fresh subagent** — no context reuse, no fabricated resume ids
4. Receipt records actual reviewer model + `"mode": "host"`
5. Fail closed when no cross-family pin is available (never silent same-family self-review)
6. **`host` never shells out to another CLI** — a `codex exec` / `cursor-agent` / `claude -p` / `grok` subprocess inside a host review is a broken run; the CLI backends exist for exactly that, and the user chose `host` to avoid them. Dispatch through the harness's own subagent primitive with the model named in the dispatch; an unhonored model request degrades to the session model, and then rule 5 decides — never a CLI fallback

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
- **Interactive:** ask the user explicitly (plain-text numbered prompt) which reviewer model/family to use — do not silently self-review
- **Autonomous** (`mode:autonomous` / `FLOW_AUTONOMOUS=1` / Ralph / `REVIEW_RECEIPT_PATH` set): stop with `NEEDS_HUMAN: host review needs a cross-family model pin in AGENTS.md model-routing` — never same-family self-review

## Step 2: Dispatch read-only reviewer subagents

The reviewer subagent is the **reviewer** tier — a verdict from the writer's own family is not an independent one. **Routing precedence, highest first: an explicit argument in the invocation, then the project routing block in the instruction file, then the agent definition's own default, then the session model.**

**First round of a scope = three-draw fan-out (fn-215).** The first review round
dispatches **three** fresh read-only reviewer subagents — one per fixed axis
lens — and you merge their findings into one consolidated set for one fix pass.
Re-review rounds after fixes dispatch exactly **one** fresh subagent carrying
the full merged prior-finding container. Both shapes sit behind the SAME
reservation fence below: **ONE `review-rounds increment` before the dispatch,
one record/attach after the merge — never three cap slots per merged round.**
A merged fan-out round counts 1:1 against the deterministic round cap.

**Resume gate — run this BEFORE choosing between the two shapes.** A fresh
coordinator resuming this scope mid-fix-loop (context lost between a
`NEEDS_WORK` verdict and its fix pass) must not re-enter the three-draw shape:

```bash
# ROUTE (PR #392): ONE deterministic verb owns canonicalization, the
# repo/scope-keyed receipt path (the same default Step 3 uses; explicit
# REVIEW_RECEIPT_PATH always wins), receipt identity + verdict routing,
# stale-receipt rotation, and the task-mode ledger fences (in-flight round,
# unjournaled reservation, lost receipt on an open cycle, deep-overturned
# receipt, NEEDS_HUMAN). Branch on its action — never re-derive any of that
# in shell.
ROUTE="$("$FLOWCTL" review-route ${TASK_ID:+"$TASK_ID"} --rotate-stale --json)" || { printf '%s\n' "$ROUTE" >&2; exit 1; }
ACTION="$(jq -r '.action' <<<"$ROUTE")"
TASK_ID="$(jq -r '.task_id // empty' <<<"$ROUTE")"
RECEIPT_PATH="$(jq -r '.receipt_path' <<<"$ROUTE")"
RESUMED=0
case "$ACTION" in
  stop)
    # The message names the condition and the repair (NEEDS_HUMAN-prefixed).
    jq -r '.message' <<<"$ROUTE" >&2; exit 1 ;;
  fix-then-rereview)
    RESUMED=1
    # Context may have been lost BEFORE the fixes were applied — re-enter at
    # the fix pass and only then dispatch the re-review.
    echo "RESUMED SCOPE — active fix loop: first verify the receipt's findings are fixed and committed (apply them if not), then dispatch ONE fresh re-review subagent (Round 2+ shape) carrying this receipt's merged container; no fan-out" ;;
esac
```

With `RESUMED=1`, skip the "First round: three axis draws" section entirely —
but do NOT dispatch yet: first run the fix pass against the receipt's merged
container (Step 5 NEEDS_WORK handling: parse, fix, test, commit; verify
instead when the fixes are already committed), THEN dispatch under "Round 2+:
one fresh subagent". The reservation fence below runs the same either way
(one reservation per round). A re-review of unfixed code spends a round and
can replace unresolved findings with a stochastic verdict.

### Convergence reservation and recovery fence

After the exact reviewer input is composed and immediately before each ROUND's
dispatch — the whole three-draw fan-out on round 1, the single fresh subagent
on round 2+ — bind the reviewed range, build the artifact blob, and reserve one
task-scoped round (one reservation per round, never per draw). The full diff is materialized **for the artifact hash only** —
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
# --exclusive (PR #392 r22): the no-pending pre-check above is fast-fail UX
# only — this flag makes the refusal ATOMIC inside the reservation lock, so
# two concurrent coordinators cannot both reserve between the check and here.
ROUND_JSON="$("$FLOWCTL" review-rounds increment "${TASK_ID%.*}" --kind impl \
  --task "$TASK_ID" --review-type impl --artifact-file "$ARTIFACT_FILE" --exclusive --json)"
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

After the reviewer subagents return (all draws of the round, or the single
re-review subagent), construct the receipt input and target in Step 3.
Only then record the captured reservation and attach its journaled payload;
receipt findings must never be constructed after `record`.

### First round: three axis draws in ONE message

Dispatch three **fresh** read-only reviewer subagents with the resolved pin,
**all named in ONE message** — mirror the quality-auditor dispatch shape
(flow-next-work Phase 4): the same read-only agent dispatched three times, each
prompt differing from the base reviewer input by exactly one added axis line:

- correctness draw: "Axis focus for this draw: correctness-and-logic of the changed code — logic errors, spec mismatches, and edge cases in the changed paths."
- contracts draw: "Axis focus for this draw: contracts-and-consistency — do the docs, tests, comments, and stated promises agree with what the code actually does?"
- integration draw: "Axis focus for this draw: integration-with-unchanged-code — how the changed code meets the unchanged code: callers, callees, shared state, and cross-module assumptions."

A run that dispatched one draw and waited for its report before sending the
next has re-serialized what the fan-out parallelized. **Portable-host
fallback:** on a host whose subagent primitive cannot batch several dispatches
into one message (generic read-only dispatch with Edit/Write disallowed), run
the three draws back-to-back and report the degradation in the review record
(one line in the merged review document: sequential draws, host cannot batch
dispatches) — the contract is three independent fresh read-only contexts per
round, and the fan-out degrades honestly to sequential where the host offers
no one-message parallel dispatch.

**Unlike the quality auditor's two axis reports — which stay verbatim because
they feed a human-shaped judgment — these three draws MERGE**: they are k
samples of one finding distribution feeding one fix pass (the spec's Decision
Context records this deliberate difference in consumption contract). Same
dispatch pattern, different consumption.

**Steering (prose, no flags):** "use 1 reviewer instead of 3" collapses the
round to a single draw (the correctness lens). "use three different model
families for the review fan-out" names a different reviewer pin in each of the
three dispatches — each still cross-family from the writer. Ambiguous phrasing
defaults to the standard three same-pin draws.

### Round 2+: one fresh subagent, merged container injected

Every re-review dispatches exactly **one** fresh read-only subagent — host
sessions are never resumed (fn-123): no context reuse, no fabricated resume
ids. Inject the FULL merged prior-finding container from the previous round's
receipt into its prompt (every merged ordinal present, rendered as structured
`findings.items` per the list below) — the fresh subagent holds nothing from
the draws that authored those findings.

The `REVIEW_HEAD_SHA` / `REVIEW_BASE_SHA` anchors bound in the fence above are
the reviewed range; retain them (re-`source "$REVIEW_SNAPSHOT_FILE"` in any
later block) through receipt writing.

The reviewer runs on the **reviewer tier**. Resolution order: an explicit
instruction in the invocation, then the project routing block in the
instruction file, then the agent definition's own default, then the session
model. How *this* harness reaches that model - and what degrades when it
cannot - is its reach page: [`docs/reach/README.md`](../../docs/flow-next/reach/README.md).
A harness that reaches only one model family natively fails closed when the
writer shares that family (interactive -> ask; autonomous -> `NEEDS_HUMAN`);
cross-family then comes through a bridge backend.

Read-only is enforced by TOOLS, never by prompt: dispatch through a read-only
agent definition or the host's read-only subagent mode
(`disallowedTools: Edit, Write, Task` where the host consumes it) - never a
mutation-capable subagent, because the reviewer reads untrusted diff content. Where the host cannot
enforce it, say so in the receipt: pin and read-only enforcement are
host-dependent. The dispatch prompt additionally states working-tree conduct: the reviewer never runs a mutating command (`git checkout`/`restore`/`clean`/`stash`, shell file writes) - tool fences do not cover the shell, and uncommitted state it finds is evidence to report, never something to repair.

Receipt in every case: `mode: "host"`, the actual reviewer model,
`session_id: null`.

Give each reviewer subagent:
- The impl-review rubric ([references/impl-review-prompt.md](references/impl-review-prompt.md))
- The rubric's verification-budget rail travels with it (focused suites only; the full suite belongs to the run's final gate) — carried by pointer, never restated or widened in the dispatch prompt
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

Wait for the subagent result(s) (blocking — do not background).

## Step 2.5: Merge the draws (first round — judgment, yours)

Merge the surviving draws' findings into ONE consolidated review document:

- **Same-defect dedupe** is judgment: findings describing the same defect from
  different draws collapse to one entry, keeping the strongest evidence.
- **Evidence bar:** drop findings that fail it and state the dropped counts in
  the standard per-anchor tally grammar — e.g.
  `Suppressed findings: 3 at anchor 50, 2 at anchor 0.` — summing the draws'
  tallies per anchor.
- **Ranked output with an Act-On tier capped at 5 — non-blocking tiers only** —
  plus a published remainder: considered-and-deferred stays distinguishable
  from never-seen, and remainder items persist in the merged document (deferred
  lineage across rounds), never silently dropped. **Every surviving introduced
  blocking finding is fixed regardless of count.**
- **Axis provenance lives in your merge prose** ("the integration draw surfaced
  #3 and #7"), never as a field on finding items.
- Re-assign ordinals 1..N across the union and keep the draws' output format
  (severity, classification, file:line, the verdict-scope sections) — the
  merged document is what the receipt's `review` field carries and what the
  next round's ratchet renders.

**Verdict synthesis is mechanical worst-wins** over the draws' verdict tags
(`NEEDS_HUMAN > MAJOR_RETHINK > NEEDS_WORK > all-SHIP`) — no draw's verdict is
judged away. One defined exception (the wedge): a `NEEDS_WORK` where the
evidence gate dropped EVERY finding of every NEEDS_WORK draw escalates to
`NEEDS_HUMAN` rather than looping against an unchanged artifact.

**Partial fan-out fails open:** merge whichever draws returned a verdict — one
is enough — and record how many draws failed in the receipt. A failed draw
never blocks, retries, or consumes extra rounds. Only an all-draws-no-verdict
round is a transport failure with today's durable refund semantics (the
record fence below refunds the one reservation; nothing is attached).

When `--deep` / `--validate` / `--interactive` fired, run those optional
phases AFTER Step 3's record/attach, against the merged container it stamped —
still exactly ONCE per round, never per draw, and always before the fix pass
(Step 4's host-native rules apply). Same ordering as the codex fan-out: the
gated phases consume a finalized merged round, and their surviving findings
feed the fix pass, never a rewrite of the already-recorded merged document.

## Step 3: Receipt

Receipt path (the same route-derived default every backend uses; explicit `REVIEW_RECEIPT_PATH` always wins):

```bash
ROUTE="$("$FLOWCTL" review-route ${TASK_ID:+"$TASK_ID"} --json)"   # pure: canonical TASK_ID + receipt path (no rotation, no state change)
TASK_ID="$(jq -r '.task_id // empty' <<<"$ROUTE")"
RECEIPT_PATH="$(jq -r '.receipt_path' <<<"$ROUTE")"
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
  "draws": [{"axis": "<axis>", "model": "<slug>", "session_id": null, "verdict": "<tag or null>", "failed": false}],
  "timestamp": "<ISO-8601>"
}
```

`draws[]` appears on the first (fan-out) round only — one entry per dispatched
draw, honestly recording each draw's axis, model, `session_id` (always null on
host), verdict, and failed flag, including the draws that returned nothing
(`"failed": true`, `"verdict": null`). `review` carries the MERGED document.
This is the host path's equivalent of the codex fan-out receipt: the same
top-level shape plus the same honesty about what actually ran. Re-review
receipts (single fresh subagent) carry no `draws[]`.

`session_id` is literal `null` — deliberate: host re-reviews are always fresh subagents, and `null` distinguishes "no resumable session by design" from an accidentally incomplete receipt. `review` carries the reviewer's full output — the re-review ratchet reads it to inject prior findings into the next fresh subagent (convergence), so a host receipt that omits `review` has broken the convergence ratchet.

Write that base JSON to a temporary input file and persist the full reviewer
output (first round: the MERGED document, `$REVIEW_OUTPUT_FILE`) to a second
temporary file. Finalize the captured reservation first, then attach from that
journaled payload so host receipts follow the same lineage/currentness
contract as subprocess backends. **On a fan-out round this runs ONCE, after
the merge, against the one reservation from Step 2's fence — never once per
draw (three cap slots for one merged round would triple-charge the cap):**

```bash
# Scope ownership through the optional phases (PR #392, sol round 3): hold
# the lease BEFORE the record — while the exclusive reservation still stands,
# so no other dispatch can enter between consumption and lease. Acquisition
# failure is terminal; Step 4 releases it after the phases.
# Step 0 printed OPTIONAL_PHASES_COUNT; restate it here as a LITERAL (shell
# state does not survive across prompt turns). 0 when no optional flag is set.
OPTIONAL_PHASES_COUNT="<count printed by Step 0>"
if [ -n "$OPTIONAL_PHASES_COUNT" ] && [ "$OPTIONAL_PHASES_COUNT" != "0" ]; then
  "$FLOWCTL" review-route ${TASK_ID:+"$TASK_ID"} --receipt "$RECEIPT_PATH" --hold-phases "$OPTIONAL_PHASES_COUNT" --rid "$RESERVATION_ID" --json || exit 1
fi
RECORD_JSON="$("$FLOWCTL" review-rounds record "${TASK_ID%.*}" --kind impl \
  --task "$TASK_ID" --review-type impl --backend host \
  --output-file "$REVIEW_OUTPUT_FILE" --reservation-id "$RESERVATION_ID" \
  --receipt-target "$RECEIPT_PATH" --receipt-payload-file "$RECEIPT_INPUT" --json)"
RECORD_EXIT=$?
printf '%s\n' "$RECORD_JSON"
if [[ "$RECORD_EXIT" -ne 0 ]]; then
  # Release the lease we hold if the record did not land (nothing to fence).
  [ -n "$OPTIONAL_PHASES_COUNT" ] && [ "$OPTIONAL_PHASES_COUNT" != "0" ] && "$FLOWCTL" review-route ${TASK_ID:+"$TASK_ID"} --receipt "$RECEIPT_PATH" --release-phases --rid "$RESERVATION_ID" --json >/dev/null 2>&1
  exit "$RECORD_EXIT"
fi
# A refunded (no-verdict) record journals nothing attachable — record already
# completed its own bookkeeping; attach only a delivered verdict.
if [[ -n "$VERDICT" ]]; then
  "$FLOWCTL" review-findings attach --reservation-id "$RESERVATION_ID" \
    --receipt "$RECEIPT_PATH" \
    --json
fi

if [[ "$VERDICT" == "NEEDS_HUMAN" ]]; then
  # Terminal escalation: no optional phase runs, so release the lease held
  # above before exiting (codex r46) — nothing is left fenced behind the TTL.
  [ -n "$OPTIONAL_PHASES_COUNT" ] && [ "$OPTIONAL_PHASES_COUNT" != "0" ] && "$FLOWCTL" review-route ${TASK_ID:+"$TASK_ID"} --receipt "$RECEIPT_PATH" --release-phases --rid "$RESERVATION_ID" --json >/dev/null 2>&1
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

When the enabled phases have all run, release the scope lease held in Step 3
(before the fix pass):

```bash
"$FLOWCTL" review-route ${TASK_ID:+"$TASK_ID"} --receipt "$RECEIPT_PATH" --release-phases --rid "$RESERVATION_ID" --json
```

## Step 5: Continue through the shared fix loop

Carry the verdict directly into SKILL.md's shared Fix Loop in this same skill
run.

- `SHIP`: complete the review contract.
- `MAJOR_RETHINK`: continue into the shared `BLOCKED: DESIGN_CONFLICT`
  terminal; do not patch the design.
- `NEEDS_WORK`: parse every valid finding, fix the code, run the relevant
  tests/lints, and commit the fixes before re-review. Then repeat Steps 1–4
  with **one new** read-only subagent (never a second fan-out — the fan-out is
  first-round only), the same cross-family rules, and the full merged
  prior findings in its prompt. Continue until `SHIP` or the deterministic round cap.
- Dispatch, malformed-verdict, or receipt failure: output
  `<promise>RETRY</promise>` and stop. Never self-issue a verdict or switch
  backends.

## Anti-patterns (Host backend)

- **Self-reviewing** — coordinator never grades its own diff
- **Silent same-family self-review** when no cross-family pin is available
- **Reusing a prior subagent context** for re-review (always fresh)
- **Putting a model on the backend string** (`host:<model>`) — rejected by flowctl; the model is named on the `reviewer` tier of the AGENTS.md routing block
- **Calling a non-existent `flowctl host` command**
- **Fabricating resume/session ids** for host receipts
- **Three cap slots for one merged round** — one increment before the draws, one record/attach after the merge
- **Presenting the draws verbatim instead of merging** — that is the quality-auditor's contract, not this one; the draws feed one fix pass
- **Fanning out on round 2+** — re-reviews are one fresh subagent with the merged container injected
- **Judging away a draw's verdict** — synthesis is mechanical worst-wins; only the empty-merged-findings wedge escalates
