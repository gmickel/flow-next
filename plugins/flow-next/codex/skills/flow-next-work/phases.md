# Flow Work Phases

(Branch chosen in SKILL.md before reading this file)

## Phase 1: Resolve Input

Detect input type in this order (first match wins):

1. **Flow task ID** `fn-N-slug.M` (e.g., fn-1-add-oauth.3) or legacy `fn-N.M`/`fn-N-xxx.M` → **SINGLE_TASK_MODE**
2. **Flow spec ID** `fn-N-slug` (e.g., fn-1-add-oauth) or legacy `fn-N`/`fn-N-xxx` → **SPEC_MODE**
3. **Resolvable handle** — any single-token arg that `$FLOWCTL show <arg> --json` resolves (including a tracker key like `wor-17` / `wor-17.1`, which flowctl's widened resolver maps to the linked spec/task). A `.`-containing handle is a task (SINGLE_TASK_MODE); otherwise a spec (SPEC_MODE).
4. **Spec file** `.md` path that exists on disk → **SPEC_MODE**
5. **Idea text** everything else → **SPEC_MODE**

**Handle-recognition rule:** **every single-token arg goes through `$FLOWCTL show <arg> --json` before it can be treated as idea text.** If it resolves (rc 0) it is an existing spec/task — use the canonical id from the JSON. Only a non-resolving token that isn't an `.md` path falls through to idea text. A run that gated on a "starts with `fn-`" check, or that re-created `wor-17` / `wor-17.1` as a new spec, has broken this.

**Track the mode** — it controls looping in Phase 3.

**Direct-route review gate (both modes):** after reading the parent spec metadata,
apply this gate before proceeding in either `SINGLE_TASK_MODE` or `SPEC_MODE`. It applies only to zero-task specs or
`no_plan: true` with exactly one task in total marked `implicit_owner: true`.
Stop if `plan_review_status` is `needs_work` or `needs_human`, or the current user
message or carried invocation host context explicitly requests spec/design review
before work. A `stale` plan review (the spec body changed after its SHIP) stops work
the same way for a spec with any number of tasks. Report `NEEDS_HUMAN` and instruct the user to run
`$flow-next-plan-review` for this spec separately, resolve its findings, then
re-invoke work. Stop before route writes, task minting, claims or dispatch,
including when no review backend is available. Work's `--review` selects
implementation review; it does not satisfy this gate.

**Direct-owner resume admission (both modes):** for the sole implicit-owner shape above,
fetch `$FLOWCTL show <owner-id> --json` after reading the parent spec. Only when that owner
reads `in_progress`: read [references/direct-owner-resume.md](references/direct-owner-resume.md)
and apply it before any claim; `--reclaim` is passed only for an owner it admits.

---

**Flow task ID (fn-N-slug.M or legacy fn-N.M/fn-N-xxx.M)** → SINGLE_TASK_MODE:
- Read task: `$FLOWCTL show <id> --json`
- Read spec: `$FLOWCTL cat <id>`
- Get parent spec from task data for context: `$FLOWCTL show <spec-id> --json && $FLOWCTL cat <spec-id>`
- **This is the only task to execute** — no loop to next task

**Flow spec ID (fn-N-slug or legacy fn-N/fn-N-xxx)** → SPEC_MODE:
- Read spec metadata: `$FLOWCTL show <id> --json`
- Read spec markdown: `$FLOWCTL cat <id>`
- **Zero-task fork:** if the metadata's `tasks` array is EMPTY, the spec was
  never planned — distinct from all-tasks-done, where tasks exist and read
  `done` (that state proceeds normally and reaches 3g). Read
  [references/no-plan-route.md](references/no-plan-route.md), execute its fork
  (autonomous refusal / pre-answer / ask), then continue with Phase 2 only
  after its Direct route minted the implicit task — its plan-first and refusal
  branches end the run. A zero-task spec never proceeds past this fork, so the
  legacy fall-through (a zero-task run reaching Phase 3 and a completion
  review over an empty diff) is unreachable. A spec with tasks — whatever
  their status — never reads that file.
- **Direct continuation:** `no_plan: true` plus exactly one task marked
  `implicit_owner: true` retains the accepted direct route. Never mint again or
  demand plan-review merely because the owner now exists. The direct-route review
  gate above still applies. Re-read the full current spec, including added requirements;
  keep the owner's `satisfies:` declaration current via `task set-spec` before dispatch.
- **Intentional tasks:** any other non-empty task set is the planned route,
  including extra tasks added after direct execution. A stale `no_plan: true` or
  invocation flag does not replace it; report that the existing tasks govern.
- Read the ready frontier: `$FLOWCTL ready --spec <id> --json`. An admitted
  direct owner is selected by 3a even when this list is empty.

**Spec file (kind 4) or idea text (kind 5):** read
[references/spec-less-start.md](references/spec-less-start.md) and create the spec and its single
task as it says.

Done when: the input is classified into exactly one of the five kinds, the mode (`SPEC_MODE` / `SINGLE_TASK_MODE`) is recorded, and a spec id exists to carry into Phase 2.

Only when this run dispatches a scout: read [references/judge-tier.md](references/judge-tier.md) before that dispatch.

## Phase 2: Apply Branch Choice

**Chain check first.** The fence below asks `flowctl spec chain` before any branch is created.
Only when the spec's `depends_on_epics` (in `$FLOWCTL show <spec-id> --json`) is non-empty, or
the fence prints `BLOCKED:`: read [references/chained-spec.md](references/chained-spec.md).

```bash
# fence:work-branch — inputs: FLOWCTL, SPEC_ID, BRANCH_NAME, BRANCH_MODE (new|current), DEFAULT_BASE (optional; defaults to origin/HEAD); origin reachable
branch_git() {
  local output
  output=$(git "$@" 2>&1) || { printf "BLOCKED: git %s: %s\n" "$*" "$output" >&2; exit 2; }
  printf "%s\n" "$output"
}
CHAIN_JSON=$("$FLOWCTL" spec chain "$SPEC_ID" --json) || { echo "BLOCKED: spec chain failed for $SPEC_ID"; exit 2; }
CHAIN_PARENT=$(printf '%s' "$CHAIN_JSON" | jq -r '.parent // empty')
CHAIN_PARENT_BRANCH=$(printf '%s' "$CHAIN_JSON" | jq -r '.parent_branch // empty')
if [[ "$(printf '%s' "$CHAIN_JSON" | jq -r '.eligible')" != "true" ]]; then
  echo "BLOCKED: $(printf '%s' "$CHAIN_JSON" | jq -r '.reason')"; exit 2
fi
if [[ -n "$CHAIN_PARENT" ]]; then
  git fetch -q origin "refs/heads/$CHAIN_PARENT_BRANCH:refs/remotes/origin/$CHAIN_PARENT_BRANCH" \
    || { echo "BLOCKED: cannot fetch parent branch $CHAIN_PARENT_BRANCH from origin"; exit 2; }
  BASE_BRANCH="origin/$CHAIN_PARENT_BRANCH"
else
  # Unset DEFAULT_BASE resolves from origin's HEAD, never a guessed branch name.
  BASE_BRANCH="${DEFAULT_BASE:-$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || echo origin/main)}"
fi
case "$BRANCH_MODE" in
  new)
    if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
      branch_git checkout -q "$BRANCH_NAME"
    else
      PRE_HEAD=$(branch_git rev-parse HEAD) || exit 2
      # Refresh the resolved remote base without checking out the default branch.
      if [[ -z "$CHAIN_PARENT" && "$BASE_BRANCH" == origin/* ]]; then
        branch_git fetch -q origin "refs/heads/${BASE_BRANCH#origin/}:refs/remotes/$BASE_BRANCH"
      fi
      START_REF="$BASE_BRANCH"
      if [[ -z "$CHAIN_PARENT" && "$BASE_BRANCH" == origin/* ]] \
        && git show-ref --verify --quiet "refs/heads/${BASE_BRANCH#origin/}" \
        && git merge-base --is-ancestor "$BASE_BRANCH" "${BASE_BRANCH#origin/}"; then
        # Preserve local planning commits, as pulling the resolved default would.
        START_REF="${BASE_BRANCH#origin/}"
      fi
      branch_git checkout -q -b "$BRANCH_NAME" "$START_REF"
      # The resolved base may predate this spec's tracked planning files.
      SPEC_FILES=$(git ls-tree -r --name-only "$PRE_HEAD" -- .flow/specs .flow/tasks 2>/dev/null \
        | grep -E "^\.flow/(specs/$SPEC_ID\.(md|json)|tasks/$SPEC_ID\.[0-9]+\.(md|json))$" || true)
      if [[ -n "$SPEC_FILES" ]]; then
        CARRIED_FILES=()
        while IFS= read -r SPEC_FILE; do
          # Uncommitted planning edits rode the checkout (it refuses when the
          # committed versions differ); carry only committed content that differs.
          git diff --quiet HEAD -- "$SPEC_FILE" || continue
          if [[ "$(git rev-parse -q --verify "HEAD:$SPEC_FILE")" != "$(git rev-parse "$PRE_HEAD:$SPEC_FILE")" ]]; then
            branch_git checkout -q "$PRE_HEAD" -- "$SPEC_FILE"
            CARRIED_FILES+=("$SPEC_FILE")
          fi
        done <<< "$SPEC_FILES"
        if (( ${#CARRIED_FILES[@]} > 0 )); then
          branch_git commit -q --only -m "chore(flow): carry $SPEC_ID spec files onto the task branch" -- "${CARRIED_FILES[@]}"
        fi
      fi
    fi ;;
  current)
    if [[ -n "$CHAIN_PARENT" ]] && ! git merge-base --is-ancestor "$BASE_BRANCH" HEAD; then
      echo "BLOCKED: current branch $(git branch --show-current) does not contain the parent tip $BASE_BRANCH ($CHAIN_PARENT)"; exit 2
    fi ;;
esac
mkdir -p .flow/tmp || { echo "BLOCKED: cannot create .flow/tmp"; exit 2; }
branch_git merge-base HEAD "$BASE_BRANCH" > .flow/tmp/spec_base || exit 2
rm -f .flow/tmp/spec_base_repos   # sibling bases are per run; recorded below
```

Based on the resolved branch mode (`BRANCH_MODE`):

- **Worktree**: use `skill: flow-next-worktree-kit`, with the same `BASE_BRANCH` the fence resolved (the parent's remote-tracking ref on a chained spec, the default branch otherwise).
- **New branch**: the fence's `new` arm - from `origin/<parent_branch>` on a chained spec (carrying the spec's own tracked `.flow/specs/<id>.*` and `.flow/tasks/<id>.*` files from the pre-checkout commit when the start point lacks them or holds an older version, as one bookkeeping commit), else the resolved default base (refreshed from origin when remote). Existing task branches are checked out unchanged.
- **Current branch**: proceed; on a chained spec the fence's `current` arm requires the parent tip in the branch's ancestry and blocks naming the missing ancestry otherwise.

The fence persists the SPEC-RUN BASE once (`git merge-base HEAD "$BASE_BRANCH" > .flow/tmp/spec_base`); the base is the run's `BASE_BRANCH`, never a hard-coded `origin/main`. Like the worker `BASE_COMMIT`, bash variables do not survive across prompt turns, so later phases re-read this persisted base via `$(cat .flow/tmp/spec_base)`. Capture it once at branch setup; Phase 4 uses it for classify calls and the auditor dispatch. When the spec changes code in git repos beside this one (the project instructions or the spec name them): read [references/multi-repo-base.md § Phase 2](references/multi-repo-base.md#phase-2). Publication is unchanged: the spec branch is pushed as today, and no PR exists until make-pr, which detects the chain from history (`flow-next-make-pr/workflow.md` Phase 0).

Done when: `spec chain` reported `eligible: true`, the run is on the branch the choice named (under autonomy, exactly the spec's `branch_name`; on a chained spec created from `origin/<parent_branch>`), and `.flow/tmp/spec_base` holds the merge-base with the run's base.

## Phase 3: Implement

**Several tasks, or a worker wanted:** read [references/multi-task.md](references/multi-task.md)
and follow it as this phase. That covers a spec with more than one open task, and a single task
when the user or config names an implementer model or tier, when the task's review mode resolves
to `host` (the writer never dispatches its own host review), or when your context is too full to
implement well (say which in one line). Only on that route does
[references/judge-tier.md](references/judge-tier.md) apply.

**One task (a one-task plan, a task-id run, or the direct route's implicit owner): implement it
here, inline.** Print `Scheduling: inline (single task)`.

1. **Claim and re-anchor.** `$FLOWCTL start <task-id> --json` (add `--reclaim` only for a direct
   owner Phase 1 admitted for resume), then `$FLOWCTL anchor <task-id> --md`: the task, its spec,
   git state, matching glossary terms and the memory index. Search memory
   (`$FLOWCTL memory search "<keyword>" --json`) when an entry looks relevant. Record the base:
   `mkdir -p .flow/tmp && git rev-parse HEAD > .flow/tmp/base_commit`.
2. **Tracker.** Run `$FLOWCTL sync active --json > <run-sync-active.json>` once (a run-unique file
   under `.flow/tmp/`). Only when it reports `active: true` (or fails) read
   [references/tracker-touchpoints.md](references/tracker-touchpoints.md), passing it that file, and fire its
   `First claim` section now, its `Task done` section after step 6, and its `Completion review`
   section when step 7 ran a completion review that returned SHIP; otherwise nothing fires.
3. **Implement** to the acceptance criteria, following working-rules.md: a failing test first
   where cheap (on the defect route, [references/defect-route.md](references/defect-route.md); on
   the hill-climb route, [references/hill-climb.md](references/hill-climb.md) replaces this step),
   one focused test per criterion and per enumerated error case, the focused tests for the code
   you changed. Never weaken a test, gate or assertion to make the change pass; a gate you believe
   is wrong is `BLOCKED: TOOLING_FAILURE`. Do not edit `.flow/features/`.
4. **Commit** with `git add -- <files you changed> .flow/` and a conventional message ending
   `Task: <task-id>`. On a defect, a commit with the failing test before the fix is preferred.
5. **Review, by the risk rule in working-rules.md.** Selected, and the review mode is not `none`:
   attended, hand the result back first, then run
   `$flow-next-impl-review <task-id> --base <base_commit> --review=<mode>` in the
   background and report its verdict when it lands (`<mode>` is a backend the user named for this run, else
   `$FLOWCTL review-backend <task-id>` run from the repository root, so a task's own backend wins over the project default; `ASK` there means nothing is configured: skip review and say once in the handoff "no review backend set; run setup or set review.backend"); unattended, run it and wait. `done` waits for
   SHIP, or for an `OVERRIDDEN:` line from an unattended loop (its declined findings go in the
   summary and the Decisions list) or from the person accepting an attended `NEEDS_WORK`, or for an
   `OPEN_ITEM:` line from an unattended review (the call goes in the summary as one left for the person). Not selected: record `stage: impl-review - skipped(policy: risk - <reason>)`. When a
   review went NEEDS_WORK then SHIP on a non-trivial fix and memory is enabled, capture the lesson
   per [references/worker-memory-capture.md](references/worker-memory-capture.md).
6. **Done.** Write a short summary to `.flow/tmp/<task-id>-summary.md` (what changed, and one
   `stage: impl-review - ...` line), then run `$FLOWCTL done <task-id> --range
   "<base_commit>..HEAD" --test "<command you ran>" --summary-file .flow/tmp/<task-id>-summary.md
   --json` with the base read from `.flow/tmp/base_commit`.
7. **Completion review**, only once every task in the spec is done. A task-id run whose spec
   still has unfinished tasks runs none: it commits the task receipt (the command below) and
   finishes. Skip it when the spec has this one task, its review reached SHIP (or a recorded
   override or unattended `OPEN_ITEM:`) or the risk rule skipped that review, and every spec R-ID is
   in the task's `satisfies`: run `$FLOWCTL spec
   set-completion-review-status <spec-id> --status not_required --if-current unknown --json` and,
   when it reports `written: true` or the status already reads `not_required`, note `stage:
   completion-review - skipped(policy: single-task, per-task SHIP covers spec surface)`; any other
   result means the skip did not land: a verdict already recorded stands, and `refused` (another task
   appeared) waits, like any spec with unfinished tasks, until every task is done. Otherwise invoke `$flow-next-spec-completion-review <spec-id>` with the same
   `--review`. Commit the task receipt and this status together:
   `git add -- .flow/ && git commit -m "chore(flow): task receipt <task-id>"`.

## Phase 4: Quality

After all tasks complete:

- When `.flow/features/` exists, once all tasks are done, run [references/feature-map-update.md](references/feature-map-update.md) first: it updates the feature files whose user route this change altered.
- Run `$FLOWCTL gate classify --base "$(cat .flow/tmp/spec_base)"`; exit 0 means docs-only tier-B: run lint/format only and note `Gates: docs-only tier-B` for the Phase 5 final summary. On nonzero, run the full gates only when the repository's instructions or the user ask for a full suite: once, here, and not again after later fixes (re-check those with focused tests). When nobody asked, note `Gates: focused (full suite not requested)`; that is the normal outcome, not a gap to fill. A full gate that already ran this run (rolling quiesce, the wave join) is not run again here. When `.flow/tmp/spec_base_repos` exists: read
  [references/multi-repo-base.md § Phase 4](references/multi-repo-base.md#phase-4) as well.
- Only when a full gate (test) command is about to run here: read
  [references/full-gate-receipts.md](references/full-gate-receipts.md) first.
- Run lint/format per repo
- If change is large/risky: read [references/quality-auditor.md](references/quality-auditor.md)
  and run the two-axis audit and its fix rule as it says.

- **Caught gate manipulation strengthens the gate, never just reverts the
  edit.** When this phase (or any review) catches a test, gate, or baseline
  edited to make it pass, reverting the edit only restores the state the
  manipulation already got past once — harden the gate in its own change (pin
  the value, add the missing assertion, guard the baseline) so the same edit
  cannot pass silently again.

Host skips cannot land in task evidence because tasks are already done by Phase 4. **Every skip/honor outcome is accumulated as it happens** (gate_id, plus the receipt `<sha8>` where one was honored) **and surfaces as its own `Gates:` line in the Phase 5 final summary.** A silent skip, or several mixed outcomes collapsed into one line, has broken this (one pass can produce several: some gates receipt-reused, some run full).

Done when: lint/format ran, every required full gate either ran green or was receipt-honored, and one `Gates:` line is queued per outcome.

## Phase 5: Ship

**Verify all tasks done**:
```bash
$FLOWCTL show <spec-id> --json
$FLOWCTL validate --spec <spec-id> --json
```

**Final commit** (if any uncommitted changes):
```bash
git add -- <files you changed> .flow/
git status
git diff --staged
git commit -m "<final summary>"
```

**The spec is left open unless the user explicitly asked for it to be closed.**
A run that closed the spec on its own initiative has broken this.

Then push + open PR if user wants.

**Tracker-sync end-of-run check - LAST action before the final summary.** Run a fresh
`$FLOWCTL sync active --json` now (the run may have changed the config since its first probe).
Only when it parses and reads `active: false`: the slot reads `n/a (bridge inactive)` and the check
is skipped. Otherwise, including when the probe fails or is unreadable: read
[references/tracker-touchpoints.md § End-of-run check](references/tracker-touchpoints.md#end-of-run-check)
and run it.

**Final summary (mandatory template).** End the run with this block. **`Tracker sync:` is a required field carrying exactly one of its four states** — an explicit `n/a` proves the check ran, and an absent field reads as a skipped check. A summary printed without the slot has broken this. The `Gates:` slot is where host-layer gate skips surface — one `Gates:` line per accumulated Phase 4 outcome (repeat the line for each skip/honor so none is overwritten); worker-layer skips live in each task's evidence `tests[]`.

```
Spec: <spec-id> — <title>
Tasks: <n done>/<total>
Tests: <commands + result>
Review: <verdict | n/a>
Gates: <full | baseline reused (green receipt <sha8>) | docs-only tier-B>   # one line per outcome; repeat for each
Tracker sync: <OK | MISSING:<event> → retro-fired → OK | MISSING:<event> (retro-fire failed: <reason>) | n/a (bridge inactive)>
Shipped: <n PRs merged | 0 (no PR yet — spec complete, unshipped)>
Next: $flow-next-make-pr <spec-id>   # or $flow-next-qa <spec-id> first when pipeline.qa=on
```

The `Next:` line is the executable handoff — the reader runs it, rather than
re-deriving which command comes next from the summary above it.

**Shipped-count honesty:** an all-done spec with no PR counts as ZERO shipped —
`done` tasks on an unmerged branch are inventory, not delivery. The `Shipped:`
line carries that count explicitly: `0 (no PR yet — spec complete, unshipped)`
in the normal pre-make-pr state, never omitted. The `Next:`
line is the remaining work (make-pr, qa, land), never a victory lap; a summary
that read all-done-no-PR as finished has broken this.

**Host command form:** print every copy-pasteable flow-next command here in the spelling this host invokes — the flat `/flow-next-<name>` form when the resolved plugin root carries `.flow-next-opencode-manifest` (an OpenCode install — the same signal setup's host detection uses); on any other or indeterminate host, exactly as spelled here.

**Stage-outcome lines (binding on every stage this run orchestrated).**
Each optional stage the run reached (plan-sync, impl-review, completion
review, QA, a wave dispatch) records exactly one line in the receipt surface it
already writes — the task's `## Done summary` for task-scoped stages, this
final summary for run-scoped ones:

```
stage: <name> - ran [<start>..<end>] | skipped(<policy|config|empty|error>: <detail>) | failed(<reason>: <detail>) (model: <what actually ran>)
```

**Append `(model: <what actually ran>)` when this orchestrator knows what ran that
stage** — a subagent it dispatched on a named model, a bridged CLI it invoked with
an explicit model, or a review whose backend reported one. **Record only, never
prescribe:** write the model that *executed*, not the one your routing block asked
for; omit the annotation entirely when the harness did not expose it (absent reads
as `unknown`), and never write a selector placeholder (`auto`, `default`,
`unknown`) — an unrouted stage and a ladder floor are both honestly unknown.

**A skipped stage is an event with a reason, never an absence** — review treats a
stage with no line as failed (that inversion is the point: "no record" can never
again masquerade as "nothing to do"). A stage this run reached
that left no line has broken this. Timestamps ride the line only where this orchestrator knows
them; there is no separate timing store.

Done when: all tasks read `done`, `flowctl validate` passes, the tests and lint/format pass, the working tree is clean, the tracker-sync check has run (or the fresh probe read `active: false`), and the final summary block is printed with its `Tracker sync:` slot and one `Gates:` line per Phase 4 outcome.
