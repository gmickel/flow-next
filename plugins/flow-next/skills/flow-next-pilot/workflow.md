# /flow-next:pilot workflow

Execute these phases in order. One invocation advances at most one selected spec by one pipeline stage and ends with the terminal verdict line.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

Shared shell context for the workflow:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TODAY="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

`jq`, `git`, and `gh` must be on PATH when classification reaches the all-done PR branch. `PILOT_SPEC`, `PILOT_DRY_RUN`, `PILOT_REVIEW`, `PILOT_RESEARCH`, and `PILOT_DEPTH` come from SKILL.md Mode Detection.

## Phase 0 — Guards

Hard-stop when pilot is invoked under the Ralph harness. Emit the parseable terminal failure and dispatch nothing:

```bash
if [[ -n "${FLOW_RALPH:-}" || -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
  echo "Ralph and pilot are alternative drivers — never nest them" >&2
  echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="nested under Ralph harness (FLOW_RALPH/REVIEW_RECEIPT_PATH set) — refuse to run"'
  exit 1
fi
```

Refuse a dirty non-`.flow/` tree at tick start. Leave state untouched for diagnosis:

```bash
if git -C "$REPO_ROOT" status --porcelain | grep -v '^.. \.flow/' >/dev/null; then
  echo "Evidence: dirty non-.flow working tree at tick start"
  git -C "$REPO_ROOT" status --porcelain | grep -v '^.. \.flow/' || true
  echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="dirty working tree at tick start"'
  exit 0
fi
```

Resolve the strikes ledger after both hard guards — READ-ONLY here (a missing file reads as `{}`; nothing is created or written until a write site in Phase 1 or Phase 6, so `--dry-run` leaves the filesystem untouched). It lives under the git common dir so it is shared across worktrees and cannot be swept into commits by `git add -A`:

```bash
LEDGER_DIR="$(git -C "$REPO_ROOT" rev-parse --git-common-dir)/flow-next"
LEDGER="$LEDGER_DIR/pilot-strikes.json"
LEDGER_JSON="$(cat "$LEDGER" 2>/dev/null || echo '{}')"
```

Ledger schema: `{"<spec-id>": {"count": <n>, "stage": "<stage>", "reason": "<one line>", "ts": "<iso8601>"}}`. It is skill-owned scratch; no flowctl plumbing. Every write site runs `mkdir -p "$LEDGER_DIR"` plus `[ -s "$LEDGER" ] || echo '{}' > "$LEDGER"` first, then writes atomically with `jq` plus `mv`.

## Phase 1 — SELECT (two-pass)

Pass 1 enumerates minimal candidates:

```bash
SPECS_JSON="$($FLOWCTL specs --json)"
```

Candidate predicate for pass 1:

- `status == "open"`.
- ready flag is set.
- stable id order.
- if `--spec <id>` was provided, the candidate list is exactly that spec and it still must pass the predicate.

Echo the pass-1 counts: total specs, open specs, ready specs, and scope-lock target if present.

Pass 2 loads full spec JSON for each candidate:

```bash
SPEC_JSON="$($FLOWCTL show "$candidate" --json)"
TASKS_JSON="$($FLOWCTL tasks --spec "$candidate" --json)"
```

Apply the full predicate:

1. Dependencies: every `depends_on_epics[]` value is satisfied iff `$FLOWCTL show <dep> --json` reports `status == "done"`. Any unsatisfied dependency skips the candidate and records `deps unsatisfied: <ids>`.
2. Collision avoidance: no task may be `in_progress` and assigned to another actor. The minimal `tasks --spec` listing carries no `assignee` — for every task with `status == "in_progress"`, fetch `$FLOWCTL show <task-id> --json` and read its `assignee` field. Resolve this session's actor identity from `git config user.email`; if no robust actor identity exists, any non-empty assignee that is not ours counts as another actor.
3. Strikes: a ledger entry with `count >= 2` normally means the spec was unreadied after failure, but a candidate that is ready again has been human re-blessed. Clear that ledger entry (write site: `mkdir -p "$LEDGER_DIR"`, seed if missing, then atomic `jq` plus `mv`) and treat the spec as fresh. Under `--dry-run`, do not write — report the entry as would-clear in the classification report instead.
4. No gh here. PR state belongs exclusively to the all-done classification branch.

The first candidate passing everything becomes `SELECTED_SPEC`. If none pass, echo a compact skip table with counts by reason and stop:

```text
PILOT_VERDICT=NO_WORK spec=- stage=- reason="no ready spec with satisfied deps"
```

## Phase 2 — CLASSIFY the stage

Resolve the review backend before classification:

```bash
if [[ -n "${PILOT_REVIEW:-}" ]]; then
  REVIEW_BACKEND="$PILOT_REVIEW"
else
  REVIEW_BACKEND="$($FLOWCTL review-backend)"   # prints the backend, or ASK when unset
fi
case "$REVIEW_BACKEND" in
  none|ASK|"") REVIEW_CONFIGURED=0 ;;
  *) REVIEW_CONFIGURED=1 ;;
esac
```

Classify from `SPEC_JSON` plus `TASKS_JSON`; first match wins:

| Condition | Stage |
|---|---|
| 0 tasks exist | `plan` |
| tasks exist and `plan_review_status != "ship"` and review backend is configured | `plan-review` |
| any task has a non-`done` status — `todo`, `blocked`, or `in_progress` own/unassigned (canonical task statuses are `todo`, `in_progress`, `blocked`, `done`) | `work` |
| all tasks done and `completion_review_status != "ship"` and review backend is configured | `work` |
| all tasks done and completion is ship-or-ungated | PR probe, then `make-pr`, skip, or `NEEDS_HUMAN` |

A spec whose only remaining tasks are `blocked` still classifies as `work`; if work cannot advance it, the healthy-no-advance strike path handles it.

Review backend `none` or `ASK` skips both plan-review and completion-review gates; pilot never deadlocks on a gate that cannot run.

The all-done PR probe is the only gh touch in classification. Resolve the spec's `branch_name` first (Phase 3 reuses the same `BRANCH_NAME`):

```bash
BRANCH_NAME="$(printf '%s\n' "$SPEC_JSON" | jq -r '.branch_name // empty')"
PR_PROBE_FAILED=0
PR_JSON=$(gh pr list --head "$BRANCH_NAME" --state all --json url,state,number --limit 10 2>/dev/null) || PR_PROBE_FAILED=1
OPEN_PR=$(printf '%s\n' "${PR_JSON:-[]}" | jq -r '.[] | select(.state == "OPEN") | .url' | head -1)
CLOSED_PR=$(printf '%s\n' "${PR_JSON:-[]}" | jq -r '.[] | select(.state == "CLOSED") | .url' | head -1)
MERGED_PR=$(printf '%s\n' "${PR_JSON:-[]}" | jq -r '.[] | select(.state == "MERGED") | .url' | head -1)
```

Classification outcomes for the all-done branch:

- gh missing, unauthenticated, or API failure: `PILOT_VERDICT=NEEDS_HUMAN spec=<id> stage=make-pr reason="gh probe failed at all-done branch"`.
- OPEN PR exists: this spec is finished from pilot's perspective; skip to the next SELECT candidate.
- CLOSED PR exists and no OPEN PR exists: `NEEDS_HUMAN`, because the PR was closed without merge and pilot never silently reopens human-rejected work.
- MERGED PR exists while the spec is still open: `NEEDS_HUMAN`, because the state is inconsistent and pilot must not create a second PR.
- No PR exists: stage is `make-pr`.

Dry-run stops after classification. It prints selected spec, stage, review backend, task counts, consulted status fields, PR probe result if any, skipped candidates, and any would-clear ledger entries. It writes no ledger (the ledger file is never created or modified on a dry-run tick), checks out no branch, and dispatches nothing:

```text
PILOT_VERDICT=NO_WORK spec=<id> stage=<stage> reason="dry-run: classification only, nothing dispatched"
```

## Phase 3 — Branch resolution matrix

Pilot owns branch resolution. Reuse `BRANCH_NAME` from Phase 2 (resolve it here when classification never reached the all-done branch):

```bash
[[ -n "${BRANCH_NAME:-}" ]] || BRANCH_NAME="$(printf '%s\n' "$SPEC_JSON" | jq -r '.branch_name // empty')"
if [[ -n "$BRANCH_NAME" ]] && git -C "$REPO_ROOT" rev-parse --verify --quiet "$BRANCH_NAME" >/dev/null; then
  BRANCH_EXISTS=1
else
  BRANCH_EXISTS=0
fi
```

Matrix:

| State | Action |
|---|---|
| branch exists and stage is `work` | `git checkout <branch_name>`, dispatch work with `--branch=current` |
| branch absent and stage is first `work` tick | dispatch work with `--branch=new`; work creates it |
| stage is `make-pr` and branch exists | `git checkout <branch_name>`; make-pr auto-detects the spec from the branch |
| stage is `make-pr` and branch absent | `NEEDS_HUMAN`, reason `all tasks done but spec branch missing — inconsistent state` |
| stage is `plan` or `plan-review` | no branch action |

If branch checkout fails, stop with `NEEDS_HUMAN`; do not dispatch and do not strike.

## Phase 4 — DISPATCH exactly one sub-skill

Record the pre-dispatch evidence snapshot before invoking the stage skill:

- `plan`: task count from `$FLOWCTL tasks --spec <id> --json`.
- `plan-review`: `plan_review_status` from `$FLOWCTL show <id> --json`.
- `work`: per-task id/status list, spec status, and `completion_review_status`.
- `make-pr`: no OPEN PR for the branch, already proven by the all-done probe.

Dispatch exactly one existing stage skill (slash-command invocation), with `mode:autonomous` and `FLOW_AUTONOMOUS=1` semantics for any process-level work it starts:

- `plan`: `/flow-next:plan <spec-id> mode:autonomous --research=<grep|rp> --depth=<level> --review=<backend>`
- `plan-review`: `/flow-next:plan-review <spec-id> --review=<backend>`
- `work`: `/flow-next:work <spec-id> mode:autonomous --branch=<current|new> --review=<backend>`
- `make-pr`: `/flow-next:make-pr <spec-id> mode:autonomous`

Setter convention call-out: plan-review sets `plan_review_status` itself in its workflow Phase 4, and pilot only re-reads the field. Completion review is reached through work's Phase 3g; work invokes spec-completion-review, then the caller sets `completion_review_status=ship`. Pilot must not dispatch completion review directly.

If a sub-skill crashes, asks for judgment under autonomy, or reports ambiguity that needs a person, stop with `NEEDS_HUMAN`. Do not cleanup, reset claims, or record a strike.

## Phase 5 — VERIFY + evidence echo

Re-read state after dispatch. Judge advancement only on observed state, never sub-skill narration. Echo the before/after evidence block so a transcript-only driver can validate it.

For `plan`, advancement means tasks now exist:

```text
Evidence:
stage=plan
task_count.before=<n>
task_count.after=<m>
advanced=<m > 0>
```

For `plan-review`, advancement means the field is now `ship`:

```text
Evidence:
stage=plan-review
plan_review_status.before=<value>
plan_review_status.after=<value>
advanced=<after == ship>
```

For `work`, advancement means at least one task/spec status transition occurred, or `completion_review_status` newly became `ship` when that gate was the work to do:

```text
Evidence:
stage=work
tasks.before=<id:status,...>
tasks.after=<id:status,...>
spec_status.before=<value>
spec_status.after=<value>
completion_review_status.before=<value>
completion_review_status.after=<value>
advanced=<true|false>
```

For `make-pr`, advancement means a gh-confirmed OPEN PR URL for the branch. There is no flowctl transition for make-pr, and a successful PR tick must never record a strike:

```bash
OPEN_PR_URL=$(gh pr list --head "$BRANCH_NAME" --state all --json url,state,number --limit 10 2>/dev/null \
  | jq -r '.[] | select(.state == "OPEN") | .url' \
  | head -1)
```

Echo the URL when present:

```text
Evidence:
stage=make-pr
open_pr.before=-
open_pr.after=<url>
advanced=<url present>
```

If the post-dispatch tree is dirty outside `.flow/`, stop with `NEEDS_HUMAN` and leave state for diagnosis. This is a crash-class outcome, not a strike.

If the sub-skill emitted a `Tracker sync:` summary line, pass that line through in the evidence echo. Pilot never re-checks the tracker itself.

## Phase 6 — REPORT + strikes ledger

On `ADVANCED`, clear the selected spec's ledger entry if present and write the ledger atomically with `jq` plus `mv`:

```bash
mkdir -p "$LEDGER_DIR"
[ -s "$LEDGER" ] || echo '{}' > "$LEDGER"
tmp="$LEDGER.tmp.$$"
jq --arg spec "$SELECTED_SPEC" 'del(.[$spec])' "$LEDGER" > "$tmp" && mv "$tmp" "$LEDGER"
```

Then print the terminal line:

```text
PILOT_VERDICT=ADVANCED spec=<id> stage=<stage> reason="<what advanced>"
```

On healthy-but-no-advance, record a strike with count, stage, reason, and timestamp:

```bash
mkdir -p "$LEDGER_DIR"
[ -s "$LEDGER" ] || echo '{}' > "$LEDGER"
tmp="$LEDGER.tmp.$$"
jq --arg spec "$SELECTED_SPEC" --arg stage "$STAGE" --arg reason "$NO_ADVANCE_REASON" --arg ts "$TODAY" '
  .[$spec].count = ((.[$spec].count // 0) + 1)
  | .[$spec].stage = $stage
  | .[$spec].reason = $reason
  | .[$spec].ts = $ts
' "$LEDGER" > "$tmp" && mv "$tmp" "$LEDGER"
STRIKE_COUNT="$(jq -r --arg spec "$SELECTED_SPEC" '.[$spec].count' "$LEDGER")"
```

If `STRIKE_COUNT` is `1`, leave the spec ready and print:

```text
PILOT_VERDICT=BLOCKED spec=<id> stage=<stage> reason="no advancement (strike 1/2): <why>"
```

If `STRIKE_COUNT` is `2`, unready the spec, keep the ledger reason, and print:

```bash
$FLOWCTL spec unready "$SELECTED_SPEC"
```

```text
PILOT_VERDICT=BLOCKED spec=<id> stage=<stage> reason="no advancement (strike 2/2, spec unreadied): <why>"
```

Crash-class outcomes are `NEEDS_HUMAN`: sub-skill crash, dirty non-`.flow/` tree after dispatch, gh probe failure in the all-done branch, branch inconsistency, closed-without-merge PR, merged-PR-but-open-spec, or autonomy ambiguity. Leave state untouched and record no strike:

```text
PILOT_VERDICT=NEEDS_HUMAN spec=<id> stage=<stage> reason="<one line>"
```

No selectable candidate or all candidates finished with existing OPEN PRs yields:

```text
PILOT_VERDICT=NO_WORK spec=- stage=- reason="no ready spec with satisfied deps"
```

The `PILOT_VERDICT` line is always the last line of the tick output. Print nothing after it.
