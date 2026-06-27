# /flow-next:pilot workflow

Execute these phases in order. One invocation advances at most one selected spec by one pipeline stage and ends with the terminal verdict line.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks use `$FLOWCTL`:

```bash
FLOWCTL="$HOME/.codex/scripts/flowctl"
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
2. Collision avoidance: no task may be `in_progress` and assigned to another actor. The minimal `tasks --spec` listing carries no `assignee` — for every task with `status == "in_progress"`, fetch `$FLOWCTL show <task-id> --json` and read its `assignee` field. Resolve this session's actor identity exactly as `flowctl.get_actor()` does: `$FLOW_ACTOR` env var, else `git config user.email`, else `git config user.name`, else `$USER`, else `unknown`. If resolution bottoms out at `unknown`, any non-empty assignee counts as another actor.
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
 REVIEW_BACKEND="$($FLOWCTL review-backend)" # prints the backend, or ASK when unset
fi
case "$REVIEW_BACKEND" in
 none|ASK|"") REVIEW_CONFIGURED=0 ;;
 *) REVIEW_CONFIGURED=1 ;;
esac
```

Resolve the optional QA-stage gate (fn-72). **Strict** string-enum knob (default `off`): the stage activates **only** on the literal `on` — any other value (`off`, `null`, a coerced bool `true`, or a typo like `maybe`) leaves it off. Read once here and reused by the all-done classification:

```bash
QA_GATE="$($FLOWCTL config get pipeline.qa --json | jq -r '.value')"
if [ "$QA_GATE" = "on" ]; then # ONLY the literal `on` activates — never bool true / typos
 QA_STAGE_ENABLED=1
else
 QA_STAGE_ENABLED=0
fi
```

Classify from `SPEC_JSON` plus `TASKS_JSON`; first match wins:

| Condition | Stage |
|---|---|
| 0 tasks exist | `plan` |
| tasks exist and `plan_review_status != "ship"` and review backend is configured | `plan-review` |
| any task is `todo` or `blocked` (canonical task statuses are `todo`, `in_progress`, `blocked`, `done`) | `work` |
| the only non-`done` tasks are `in_progress` own/unassigned (other-actor claims were already skipped at SELECT) | `NEEDS_HUMAN`, reason `stale in-progress claim — work's ready-driven loop cannot resume it` |
| all tasks done and `completion_review_status != "ship"` and review backend is configured | `work` |
| all tasks done and completion is ship-or-ungated | run the all-done PR probe (below; `--state all`, fails closed): **open PR** → defer-to-land; **closed/merged/probe-failed/missing-branch** → `NEEDS_HUMAN`; **no PR** → `qa` (when `QA_STAGE_ENABLED=1` and no *fresh* `qa_verdict` — R1/R1b) else `make-pr` |

A spec whose only remaining tasks are `blocked` still classifies as `work`; if work cannot advance it, the healthy-no-advance strike path handles it. An in-progress-only spec is different: work's Phase 3a drives off `flowctl ready --spec`, which never returns an `in_progress` task, so dispatching would burn strikes or wrongly enter the completion-review path — the stale-claim `NEEDS_HUMAN` is crash-class (no dispatch, no strike).

Review backend `none` or `ASK` skips both plan-review and completion-review gates; pilot never deadlocks on a gate that cannot run.

### QA-stage freshness probe (R1b — only when `QA_STAGE_ENABLED=1`)

When the QA gate is on, the all-done juncture classifies `qa` **only when no *fresh* `qa_verdict` receipt exists** for the spec. Pilot is single-tick: without this idempotence gate it would re-classify `qa` forever and never reach make-pr. The receipt lives at the committed path `.flow/review-receipts/qa-<spec-id>.json` (the QA skill's default; task .1 added the `head_sha` field). A receipt is **fresh** iff all three hold:

1. `receipt.id == <spec-id>` (the receipt's existing spec-id field is `id`, not `spec`).
2. `receipt.head_sha` matches the spec **branch** head **with the `chore(flow): {qa verdict, pr artifact}` bookkeeping commits peeled off** — the receipt records the CODE head, but pilot commits the receipt (and make-pr the pr.html artifact) ABOVE it, so a raw `rev-parse "$BRANCH_NAME"` would never match and QA would re-run forever. Compute against the branch, not `HEAD` (a resumed/manual tick may sit on another branch); the post-dispatch verify (pre-receipt-commit) still uses `HEAD` directly.
3. `receipt.qa_outcome` is a valid terminal value (`SHIP`, `NEEDS_WORK`, `NA`, or `BLOCKED`).

Resolve `BRANCH_NAME` + `QA_FRESH` here; the `qa` decision itself is made in the all-done PR probe's **no-PR** branch below, so an existing PR always takes priority. Read the receipt with a single `jq` so a missing/malformed file degrades to never-fresh:

```bash
[[ -n "${BRANCH_NAME:-}" ]] || BRANCH_NAME="$(printf '%s\n' "$SPEC_JSON" | jq -r '.branch_name // empty')"
QA_RECEIPT="$REPO_ROOT/.flow/review-receipts/qa-$SELECTED_SPEC.json"
QA_FRESH=0
if [ -f "$QA_RECEIPT" ] && [ -n "$BRANCH_NAME" ]; then
 R_ID="$(jq -r '.id // ""' "$QA_RECEIPT" 2>/dev/null)"
 R_SHA="$(jq -r '.head_sha // ""' "$QA_RECEIPT" 2>/dev/null)"
 R_OUT="$(jq -r '.qa_outcome // ""' "$QA_RECEIPT" 2>/dev/null)"
 case "$R_OUT" in SHIP|NEEDS_WORK|NA|BLOCKED) : ;; *) R_SHA="" ;; esac # invalid outcome → never fresh
 # The receipt's head_sha is the CODE head; pilot's own `chore(flow): qa verdict` commit
 # (and a later `pr artifact` commit) sit ABOVE it on the branch, so the branch tip is not
 # the code head. Walk from the tip peeling those bookkeeping commits and accept a match
 # anywhere in the chain — else a successful QA pass reads as never-fresh and re-runs forever.
 if [ "$R_ID" = "$SELECTED_SPEC" ] && [ -n "$R_SHA" ]; then
 _s="$(git -C "$REPO_ROOT" rev-parse --verify --quiet "$BRANCH_NAME" 2>/dev/null || echo "")"
 while [ -n "$_s" ]; do
 [ "$_s" = "$R_SHA" ] && { QA_FRESH=1; break; }
 git -C "$REPO_ROOT" log -1 --format='%s' "$_s" 2>/dev/null \
 | grep -qE '^chore\(flow\): (qa verdict|pr artifact) ' || break
 _s="$(git -C "$REPO_ROOT" rev-parse "$_s^" 2>/dev/null || echo "")"
 done
 fi
fi
```

`QA_FRESH` feeds the **no-PR branch** of the all-done PR probe below — the `qa` decision is made *there*, not before it. Classify `qa` only when that probe finds **no PR** AND `QA_STAGE_ENABLED=1` AND `QA_FRESH=0`. Any existing PR takes priority over (re-)running QA (open → defer-to-land; closed/merged/probe-failed → `NEEDS_HUMAN`), and the probe **fails closed** on a `gh` error — so a transient API failure never misroutes to `qa`. A fresh receipt (`QA_FRESH=1`) or the gate off ⇒ `make-pr`. (Echo `qa_gate=<on|off> qa_fresh=<0|1>` in the classification report so a transcript-only driver sees why the juncture chose `qa` vs `make-pr`.)

The all-done PR probe is the only gh touch in classification. Resolve the spec's `branch_name` first (Phase 3 reuses the same `BRANCH_NAME`):

```bash
BRANCH_NAME="$(printf '%s\n' "$SPEC_JSON" | jq -r '.branch_name // empty')"
PR_PROBE_FAILED=0
PR_JSON=$(gh pr list --head "$BRANCH_NAME" --state all --json url,state,number --limit 10 2>/dev/null) || PR_PROBE_FAILED=1
OPEN_PR=$(printf '%s\n' "${PR_JSON:-[]}" | jq -r '.[] | select(.state == "OPEN") | .url' | head -1)
CLOSED_PR=$(printf '%s\n' "${PR_JSON:-[]}" | jq -r '.[] | select(.state == "CLOSED") | .url' | head -1)
MERGED_PR=$(printf '%s\n' "${PR_JSON:-[]}" | jq -r '.[] | select(.state == "MERGED") | .url' | head -1)
```

Classification outcomes for the all-done branch (the all-done invariant: an all-done / completion-`ship` spec lacking a **merged** PR is *unfinished from the board's perspective* — pilot keeps driving it (`make-pr`), defers it to land (open PR), or surfaces it (`NEEDS_HUMAN`); it never collapses to terminal `NO_WORK`):

- gh missing, unauthenticated, or API failure: `PILOT_VERDICT=NEEDS_HUMAN spec=<id> stage=make-pr reason="gh probe failed at all-done branch"`.
- OPEN PR exists (and no MERGED PR): this spec is **deferred to land** — land owns the open PR, not pilot — so record it as a *deferred candidate* and skip to the next SELECT candidate. This is an explicit defer, never a silent finish: if no later candidate is selectable, the tick terminates with the distinct, greppable `PILOT_VERDICT=DEFERRED_TO_LAND` line (Phase 6), never `NO_WORK`. Track the deferred spec id + open-PR url so the terminal line can name it.
- No PR exists: classify `qa` when `QA_STAGE_ENABLED=1` **and** `QA_FRESH=0` (the optional QA stage runs before make-pr); otherwise `make-pr`. This is the FLOW-15 case (all-done, no PR — make-pr never ran or its PR was lost); it MUST classify `qa`/`make-pr` and never fall through to `NO_WORK`.
- CLOSED PR exists and no OPEN PR exists: `NEEDS_HUMAN`, because the PR was closed without merge and pilot never silently reopens human-rejected work.
- MERGED PR exists while the spec is still open: `NEEDS_HUMAN`, because the state is inconsistent and pilot must not create a second PR.

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
| branch absent and stage is first `work` tick | dispatch work with `--branch=new`; under autonomy work names it exactly the spec's `branch_name` (fn-59.2 contract), so later ticks find it |
| stage is `qa` and branch exists | `git checkout <branch_name>`; QA drives the running app against this branch's build (never the default branch — the app under test is the spec's build). After checkout `HEAD` equals the branch head, so the Phase 5 post-dispatch freshness verify uses `HEAD`. |
| stage is `qa` and branch absent | `NEEDS_HUMAN`, reason `all tasks done but spec branch missing — inconsistent state` (all-done with no branch is the same inconsistency as the make-pr row; QA never silently skips) |
| stage is `make-pr` and branch exists | `git checkout <branch_name>`; make-pr auto-detects the spec from the branch |
| stage is `make-pr` and branch absent | `NEEDS_HUMAN`, reason `all tasks done but spec branch missing — inconsistent state` |
| stage is `plan` or `plan-review` | `git checkout` the default branch (local `main`, else `master`) |

The plan/plan-review checkout matters in multi-spec loops: a prior tick's make-pr leaves the worktree on that spec's PR branch, and planning state written there would mutate the already-open PR.

If branch checkout fails (any matrix row, including the default-branch checkout), stop with `NEEDS_HUMAN`; do not dispatch and do not strike.

## Phase 4 — DISPATCH exactly one sub-skill

Record the pre-dispatch evidence snapshot before invoking the stage skill:

- `plan`: task count from `$FLOWCTL tasks --spec <id> --json`.
- `plan-review`: `plan_review_status` from `$FLOWCTL show <id> --json`.
- `work`: per-task id/status list, spec status, and `completion_review_status`.
- `qa`: absence of a fresh `qa_verdict` receipt (`QA_FRESH=0`), already proven by the classify-time freshness probe; the post-dispatch verify re-reads the receipt against the **code head** (HEAD peeled past the qa-verdict bookkeeping commit).
- `make-pr`: no OPEN PR for the branch, already proven by the all-done probe.

Dispatch exactly one existing stage skill (slash-command invocation), with `mode:autonomous` and `FLOW_AUTONOMOUS=1` semantics for any process-level work it starts:

- `plan`: `/flow-next:plan <spec-id> mode:autonomous --research=<grep|rp> --depth=<level> --review=<backend>`
- `plan-review`: `/flow-next:plan-review <spec-id> --review=<backend>`
- `work`: `/flow-next:work <spec-id> mode:autonomous --branch=<current|new> --review=<backend>`
- `qa`: `/flow-next:qa <spec-id> mode:autonomous` — the QA skill derives scenarios from the spec, reads work's evidence, drives the **local running app**, and writes the `qa_verdict` receipt. `mode:autonomous` suppresses all prompts (the QA skill's Autonomous-mode gate) so the loop can't hang on an `plain-text numbered prompt`. Pilot dispatches the existing skill and never re-implements its logic; routing on the resulting `qa_outcome` is Phase 5.
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

For `qa`, advancement is judged from the **post-dispatch `qa_verdict` receipt** — observed state, never the QA skill's narration. The QA stage **advances on every terminal outcome**: the gate routes on `qa_outcome` (the four-outcome field), NOT the Ralph-guard `verdict` projection (the QA skill projects `BLOCKED→verdict=NEEDS_WORK`, so reading `verdict` would wrongly conflate "couldn't verify" with "found problems"). QA is advisory — it never hard-blocks the build loop; the human reviewer + the land gate act on its findings.

Read the receipt fresh after dispatch. The QA skill commits its own handoff in autonomous mode (qa §6.3b), so `HEAD` is now the `chore(flow): qa verdict` commit — peel it to the **code head** and match the receipt's `head_sha` against that (the pr-artifact commit can't exist yet — that's the next tick's make-pr):

```bash
QA_RECEIPT="$REPO_ROOT/.flow/review-receipts/qa-$SELECTED_SPEC.json"
QA_OUTCOME=""
QA_ADVANCED=false
# Code head = HEAD, peeled past qa's own `chore(flow): qa verdict` handoff commit (§6.3b).
CODE_HEAD="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "")"
git -C "$REPO_ROOT" log -1 --format='%s' 2>/dev/null | grep -q '^chore(flow): qa verdict ' \
 && CODE_HEAD="$(git -C "$REPO_ROOT" rev-parse HEAD^ 2>/dev/null || echo "")"
if [ -f "$QA_RECEIPT" ]; then
 QA_OUTCOME="$(jq -r '.qa_outcome // ""' "$QA_RECEIPT" 2>/dev/null || echo "")"
 # Advance ONLY on a FRESH receipt this dispatch produced: id matches, head_sha == the code
 # head, terminal outcome. A missing/stale receipt (qa errored before writing) ⇒
 # advanced=false — never advance on narration.
 QA_ADVANCED="$(jq -r --arg id "$SELECTED_SPEC" --arg sha "$CODE_HEAD" '
 if (.id == $id and .head_sha == $sha
 and (.qa_outcome | IN("SHIP","NEEDS_WORK","NA","BLOCKED")))
 then "true" else "false" end' "$QA_RECEIPT" 2>/dev/null || echo false)"
fi
```

Echo the evidence block:

```text
Evidence:
stage=qa
qa_outcome=<SHIP|NEEDS_WORK|NA|BLOCKED|->
head_sha=<receipt head_sha or ->
advanced=<true|false>
```

Routing on the **fresh** `qa_outcome` (`QA_ADVANCED=true`):

- `SHIP` / `NA` / `BLOCKED` → advance cleanly to the next tick's make-pr (BLOCKED = no local app reachable / NA = no driveable UI; both advance — QA is the optional augmenting pass, never a wedge).
- `NEEDS_WORK` → **still advance** (the build loop never stalls on QA). The findings ride the draft PR: make-pr surfaces them from the receipt (its §2.x QA-summary section), and the QA skill already filed them to the bug-memory track + (when the bridge is active) the tracker comment. A `NEEDS_WORK` qa stage is an `ADVANCED` verdict, not `BLOCKED`/`NEEDS_HUMAN`.

**The QA skill commits its own handoff** (the `qa_verdict` receipt + the exact bug-memory it filed) in autonomous mode (qa §6.3b) — so the receipt is already on the branch and rides the eventual make-pr push. **Pilot adds no commit of its own here**: the agent that wrote the files commits them precisely, so pilot never sweeps the tree or guesses paths.

A missing/stale receipt (`QA_ADVANCED=false`) is the healthy-no-advance path (Phase 6 strike), NOT a crash — the QA skill ran but produced no fresh verdict (e.g. it errored before writing). **Don't-thrash + non-fatal:** pilot is single-tick and the freshness gate prevents re-classifying `qa` once a fresh receipt exists, so the same spec is bounded to one qa pass per branch-head; the interactive work↔qa re-pass (out of scope here — autonomous surfaces + proceeds) is bounded by the existing strike/auto-block reflexes (2 strikes → unready). `BLOCKED` from a missing app is a fresh terminal outcome (it advances), never a failed loop.

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

For a `qa` stage the reason names the fresh `qa_outcome` so a transcript-only driver sees the result without re-reading the receipt, e.g. `reason="qa pass: qa_outcome=NEEDS_WORK — findings surfaced on draft PR"` or `reason="qa pass: qa_outcome=BLOCKED — no local app reachable, advancing"`. Every fresh terminal `qa_outcome` (SHIP/NEEDS_WORK/NA/BLOCKED) is an `ADVANCED` — QA is advisory and never `BLOCKED`/`NEEDS_HUMAN` on its own outcome; only a *missing/stale* receipt routes to the healthy-no-advance strike below.

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

Crash-class outcomes are `NEEDS_HUMAN`: sub-skill crash, dirty non-`.flow/` tree after dispatch, gh probe failure in the all-done branch, branch inconsistency, closed-without-merge PR, merged-PR-but-open-spec, stale in-progress-only claim, or autonomy ambiguity. Leave state untouched and record no strike:

```text
PILOT_VERDICT=NEEDS_HUMAN spec=<id> stage=<stage> reason="<one line>"
```

An all-done spec with an **open** PR is *not* crash-class — it is the benign `DEFERRED_TO_LAND` terminal below (land owns the merge). Only the closed-unmerged, missing-branch, and merged-but-open-spec all-done states are `NEEDS_HUMAN`. An all-done spec with **no** PR is never terminal at all — it classifies `make-pr` and dispatches.

Terminal verdict when no spec was dispatched, split by why — the two cases are distinct and must never be conflated:

- **No selectable candidate at all** (none open+ready, or all skipped for unsatisfied deps / other-actor claims) yields `NO_WORK`:

 ```text
 PILOT_VERDICT=NO_WORK spec=- stage=- reason="no ready spec with satisfied deps"
 ```

- **Every remaining candidate was deferred to land** (each all-done with an existing OPEN PR — the only reason they weren't dispatched) yields the distinct, greppable `DEFERRED_TO_LAND` verdict, naming the deferred spec so a transcript-only driver can hand it to `/flow-next:land`. This case MUST NOT collapse to `NO_WORK`: a `DONE`-but-open-PR spec is real outstanding work that land owns, not absence of work.

 ```text
 PILOT_VERDICT=DEFERRED_TO_LAND spec=<id> stage=land reason="all tasks done, open PR <url> — land owns the merge"
 ```

 When more than one candidate was deferred, name the first deferred spec (stable id order) in the line; the reason still reads `defer to land`.

The `PILOT_VERDICT` line is always the last line of the tick output. Print nothing after it.
