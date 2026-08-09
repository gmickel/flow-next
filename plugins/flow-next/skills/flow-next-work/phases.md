# Flow Work Phases

(Branch question already asked in SKILL.md before reading this file)

**CRITICAL**: If you are about to create:
- a markdown TODO list,
- a task list outside `.flow/`,
- or any plan files outside `.flow/`,

**STOP** and instead:
- create/update tasks in `.flow/` using `flowctl`,
- record details in the spec/task markdown.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Phase 0: Delegation request check (cheap, single step)

**Codex delegation adds exactly this one step to the default work path.** With
delegation off (the default) it resolves to a no-op and Work's observable
lifecycle is unchanged (R1/R3). A default run that gained a second delegation
step, or that read a delegation reference, has broken this.

Done when: `delegation_requested` is resolved to true or false, and — when false —
nothing else in this phase ran.

```bash
# Cheap host short-circuit FIRST — delegation is Claude-Code-only. On a non-Claude
# orchestrator (Codex / Droid / OpenCode) this resolves delegation OFF *before* the
# ~45k references/codex-delegation.md is ever read, so that reference never loads
# into a non-Claude host's context just to be disabled by Gate 1. (Gate 1 in the
# reference stays the authoritative full platform check — incl. the OPENCODE_* env
# scan; this is its cheap pre-check subset, run pre-load.)
host_is_claude_code() {
  [ -n "${CLAUDECODE:-}" ] || return 1        # not Claude Code → off
  [ -z "${DROID_PLUGIN_ROOT:-}" ] || return 1 # Droid → off (compat alias not keyed)
  [ -z "${OPENCODE:-}" ] || return 1          # OpenCode → off
  return 0
}
# Single value-check — same shape as the tracker-sync touchpoints (SKILL.md).
# Guard a missing .flow/: a fresh repo / idea-or-markdown input has not been
# `flowctl init`ed yet (that happens in Phase 1), and `config get` errors on an
# absent .flow/. Treat missing .flow/ as delegation OFF — a bare-idea input is
# never delegation-eligible anyway (delegation requires a plan/spec/task input).
if [ -d .flow ]; then
  # ONE root snapshot (fn-110) serving work.delegate here AND the Phase 1 mint's
  # tracker.specIds: one config read per run, not two. Re-type the literal path.
  WORK_CFG="${TMPDIR:-/tmp}/flow-work-config-<suffix>.json"
  $FLOWCTL config get --json > "$WORK_CFG" 2>/dev/null || printf '{"key":null,"value":{}}' > "$WORK_CFG"
  DELEGATE_CFG=$(jq -r '.value.work.delegate // false' "$WORK_CFG" 2>/dev/null)
else
  DELEGATE_CFG=false
fi
# delegation_requested = host_is_claude_code && (arg delegate:codex | DELEGATE_CFG == "codex") && not arg delegate:local
#   On a non-Claude-Code host delegation_requested is FALSE here. The generic
#   "use codex" is NOT the token — it still selects the review backend.
```

If `delegation_requested` is **false** (the default), do nothing more here and run
Phase 1 onward exactly as written — no `INPUT_WAS_BARE_PROMPT` capture, no gates,
and no delegation-reference read. **If and only if `delegation_requested` is
true**, also capture `INPUT_WAS_BARE_PROMPT` inside Phase 1 and run Phase 1.5.

## Phase 1: Resolve Input

Detect input type in this order (first match wins):

1. **Flow task ID** `fn-N-slug.M` (e.g., fn-1-add-oauth.3) or legacy `fn-N.M`/`fn-N-xxx.M` → **SINGLE_TASK_MODE**
2. **Flow spec ID** `fn-N-slug` (e.g., fn-1-add-oauth) or legacy `fn-N`/`fn-N-xxx` → **SPEC_MODE**
3. **Resolvable handle** — any single-token arg that `$FLOWCTL show <arg> --json` resolves (including a tracker key like `wor-17` / `wor-17.1`, which flowctl's widened resolver maps to the linked spec/task — fn-52.10/.16). A `.`-containing handle is a task (SINGLE_TASK_MODE); otherwise a spec (SPEC_MODE).
4. **Spec file** `.md` path that exists on disk → **SPEC_MODE**
5. **Idea text** everything else → **SPEC_MODE**

**Handle-recognition rule (R16):** **every single-token arg goes through `$FLOWCTL show <arg> --json` before it can be treated as idea text.** If it resolves (rc 0) it is an existing spec/task — use the canonical id from the JSON. Only a non-resolving token that isn't an `.md` path falls through to idea text. A run that gated on a "starts with `fn-`" check, or that re-created `wor-17` / `wor-17.1` as a new spec, has broken this.

**Track the mode** — it controls looping in Phase 3.

**Original-input-kind capture — runs only when `delegation_requested` (Phase 0).** A bare
idea-text input (match #5 above) gets promoted into a spec+task by the steps below, so
its original kind must be recorded **before** that promotion. Read
[references/codex-delegation-selection.md](references/codex-delegation-selection.md) now and
execute its `Gate 0 — original input kind` block: set `INPUT_WAS_BARE_PROMPT` here, on the
ORIGINAL input, immediately after detection and **before** running any "Spec file start" /
"Spec-less start" promotion step. On the default (delegation-off) path this step does not
exist — Phase 0 already returned.

---

**Flow task ID (fn-N-slug.M or legacy fn-N.M/fn-N-xxx.M)** → SINGLE_TASK_MODE:
- Read task: `$FLOWCTL show <id> --json`
- Read spec: `$FLOWCTL cat <id>`
- Get parent spec from task data for context: `$FLOWCTL show <spec-id> --json && $FLOWCTL cat <spec-id>`
- **This is the only task to execute** — no loop to next task

**Flow spec ID (fn-N-slug or legacy fn-N/fn-N-xxx)** → SPEC_MODE:
- Read spec metadata: `$FLOWCTL show <id> --json`
- Read spec markdown: `$FLOWCTL cat <id>`
- Get first ready task: `$FLOWCTL ready --spec <id> --json`

**Spec file start (.md path that exists)**:
1. Check file exists: `test -f "<path>"` — if not, treat as idea text
2. Initialize: `$FLOWCTL init --json`
3. Read file and extract title from first `# Heading` or use filename
4. Create spec — mint gate (tracker-first vs flow-first): [references/spec-id-mint.md](references/spec-id-mint.md), read only when minting.

5. Set spec from file: `$FLOWCTL spec set-plan <spec-id> --file <path> --json`
6. Create single task: `$FLOWCTL task create --spec <spec-id> --title "Implement <title>" --json`
7. Continue with spec-id

**Spec-less start (idea text)**:
1. Initialize: `$FLOWCTL init --json`
2. Create spec — run the **same tracker-first gate as Spec file start above**, verbatim, with `<idea>` as the title. Do not restate it here; that block is the single source.
3. Create single task: `$FLOWCTL task create --spec <spec-id> --title "Implement <idea>" --json`
4. Continue with spec-id

Done when: the input is classified into exactly one of the five kinds, the mode (`SPEC_MODE` / `SINGLE_TASK_MODE`) is recorded, and a spec id exists to carry into Phase 2.

## Phase 1.5: Select the Codex-delegation path (runs only when requested)

**Skip unless `delegation_requested=true`.** When requested, **read
[references/codex-delegation-selection.md](references/codex-delegation-selection.md)
top to bottom, execute its exact ordered gates, consent ceremony, clean-tree
check, and terminal routing, then continue with Phase 2**. A failed or declined
selection continues standard mode without loading active-only machinery.
Only a passing selection loads `references/codex-delegation.md`.

## Phase 2: Apply Branch Choice

Based on user's answer from setup questions:

- **Worktree**: use `skill: flow-next-worktree-kit`
- **New branch**:
  ```bash
  git checkout main && git pull origin main
  git checkout -b <branch>
  ```
- **Current branch**: proceed (user already confirmed)

After the branch choice is applied in any mode, persist the SPEC-RUN BASE once:
```bash
mkdir -p .flow/tmp
git merge-base HEAD <base-branch> > .flow/tmp/spec_base   # <base-branch> = the branch the run is based on, e.g. origin/main
```
Like the worker `BASE_COMMIT`, bash variables do not survive across tool calls, so later phases re-read this persisted base via `$(cat .flow/tmp/spec_base)`. Capture it once at branch setup; Phase 4 uses it for classify calls.

Done when: the run is on the branch the choice named (under autonomy, exactly the spec's `branch_name`) and `.flow/tmp/spec_base` holds the merge-base.

## Phase 3: Task Wave Loop

In SPEC_MODE, inspect the whole ready frontier and prefer a concurrent safe
subset. In SINGLE_TASK_MODE, the selected wave is always the requested task
alone. Every task still gets a fresh-context worker.

When `delegation_active=true`, initialize the **host-owned** circuit breaker
once before the loop exactly as specified in the already-loaded delegation
reference. Default/declined paths initialize nothing.

### 3a. Inspect Ready Frontier and Select a Wave

```bash
$FLOWCTL ready --spec <spec-id> --json
```

If no ready tasks, check for completion review gate (see 3g below).

In SPEC_MODE, consider every returned task and apply the **wave dispatch rule
(fail-closed — fn-176)**. **Concurrent dispatch requires all five conditions
together; any one unmet sends the wave serial.** A wave dispatched with a missing
or overlapping `**Touches:**` declaration has broken this.

1. same spec;
2. wave size ≤ 3;
3. no dependency path between any pair, in either direction, **transitively**
   (walk the `depends_on` closure from `$FLOWCTL show <task-id> --json` /
   `$FLOWCTL tasks --spec <spec-id> --json` — `flowctl dep` only writes edges,
   it has no read verb; a direct-only check is wrong);
4. every dispatched task carries a `**Touches:**` declaration, and the declared
   sets are pairwise **disjoint** (`touches(A) ∩ touches(B) = ∅`, glob-aware);
5. no task touches the always-serial set: `.flow/`, lockfiles, migration
   dirs, codegen/generated outputs (in this repo: `plugins/flow-next/codex/**`,
   `.flow/bin` dual copies), or spec/task files.

The error paths are the rule: a task with no `**Touches:**` declaration →
serial; any intersection → serial; any doubt about a glob, a hidden coupling
(shared fixtures, services), or host capacity → serial. The failure mode is
today's behavior — sequential dispatch — never a risky wave. This replaces
judgment with declared intent: the same trust model as `deps` (fn-83's
decision record untouched; no semantic prediction anywhere). Safety is
structural, not the check — workers run in isolated worktrees, so a wrong
dispatch surfaces at the join as a merge conflict (3d), costing one serial
retry, never correctness. Never run concurrent writers in one checkout. An
explicit request to parallelize strengthens the preference but never
overrides the rule.

Report the decision before claiming:

```text
Ready frontier: [fn-X.1, fn-X.2]
Selected wave: [fn-X.1, fn-X.2]
Isolation: <native worktrees | linked worktrees | other safe mechanism>
Dispatch count: 2
Sequential fallback: <reason> # only when multiple tasks were ready but one selected
```

Done when: the four report lines are printed (plus `Sequential fallback:` when one applies) and the selected wave satisfies all five conditions above.

### 3b. Claim the Selected Wave

Claim every selected task before dispatch:

```bash
$FLOWCTL start <task-id> --json
```

If any claim fails, do not dispatch that task. Retain every successfully
claimed task in the selected wave and recompute only the failed/unclaimed
membership from ground truth; never abandon a task that this conductor already
moved to `in_progress`. A successful atomic claim prevents duplicate ownership;
it does not make shared-checkout Git or filesystem mutations safe.

Done when: every task in the selected wave reads `in_progress` under this actor, and any task whose claim failed has been dropped from the wave rather than dispatched.

#### 3b.1 Tracker sync (opt-in) — first claim → In-Progress

**Optional. Runs only when the tracker bridge is active AND `work.firstClaim` is opted in. With no tracker configured this is a no-op — the work flow is unchanged.**

```bash
ACTIVE=0
# NO pipelines in the probe — a failed producer masked by a healthy consumer
# fails CLOSED. Capture raw first, rc-checked; parse separately.
RAW="$($FLOWCTL sync active --json 2>/dev/null)" || ACTIVE=1     # probe ERROR ⇒ ACTIVE (fail open)
if [ "$ACTIVE" = "0" ]; then
  VAL="$(printf '%s' "$RAW" | jq -r '.active' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
  [ "$VAL" = "true" ] && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
  echo "GATE ACTIVE — read and execute references/tracker-touchpoints.md#first-claim, then continue with Phase 3c."
fi   # default branch: bare no-op — NO link, NO read path
```

When the sentinel prints, read [references/tracker-touchpoints.md](references/tracker-touchpoints.md), execute its `First claim` section (`work.firstClaim` leaf check + best-effort dispatch), then continue with Phase 3c. When the gate is silent (bridge inactive), continue — nothing fires here.

### 3c. Spawn Worker

Use the Task tool to spawn a `worker` subagent. For a multi-task wave, create
one isolated mutable workspace and task-unique summary/evidence paths per
worker, then dispatch the selected workers concurrently. For a one-task wave,
use the existing single-worker path.

The worker gets fresh context and handles:
- Re-anchoring (reading spec, git status, task-relevant glossary terms when populated)
- Implementation
- Committing
- Review cycles (if enabled)
- Completing the task (flowctl done)

The last two responsibilities apply only to the existing single-worker path. A
parallel-wave worker defers review and all shared lifecycle work to the
conductor after integration.

**Prompt template for worker:**

**The prompt carries config values only** — the worker reads worker.md for its phases. A prompt that paraphrases or restates the worker's steps has broken this.

**`REVIEW_MODE` is per-task, not a fixed run-wide value.** Resolve it for THIS task: if the user
passed an explicit `--review=<backend>` to `/flow-next:work`, use that (a deliberate run-wide override
wins for every task); OTHERWISE resolve task-aware — `REVIEW_MODE=$($FLOWCTL review-backend "$TASK_ID")`
— so a task's own `review:` override (e.g. `review: cursor:...` under a `codex` project default) selects
its backend rather than the project default. `none` still skips review. (This is why the worker passes
`--review=$REVIEW_MODE` below — the value already carries the correct explicit-or-per-task precedence.)

**Host review routes OUTSIDE the worker (fn-123 R5) — and gates BEFORE `done`.** The worker agent carries `disallowedTools: Task` and cannot dispatch the fresh reviewer subagent the `host` backend requires. When the resolved review mode is `host`, pass `REVIEW_MODE: host-deferred` to the worker — the worker then defers `flowctl done` and the conductor runs `/flow-next:impl-review <task-id> --review=host` itself as the mandatory gate before `done`; `rg host-deferred` in this file must always find it. Read [references/host-deferred-review.md](references/host-deferred-review.md) for the full contract (worker deferral, SHIP/NEEDS_WORK handling, evidence update, Codex-mirror parity) and execute it — including its 3d.0 gate — before completing this task.

All other backends keep the worker-owned review dispatch + worker-owned `flowctl done` unchanged.

```
Implement flow-next task.

TASK_ID: fn-X.Y
SPEC_ID: fn-X
FLOWCTL: /path/to/flowctl
REVIEW_MODE: none|rp|codex|copilot|cursor|host-deferred
RALPH_MODE: true|false
PARALLEL_WAVE: true|false
WORKSPACE: <isolated mutable workspace>
HANDOVER_SUMMARY: <task-unique summary path>
HANDOVER_EVIDENCE: <task-unique evidence path>

Follow your phases in worker.md exactly.
```

Set `PARALLEL_WAVE: true` for a concurrently dispatched multi-task wave AND
for a reviewer-overlap dispatch (fn-176's one-task wave — the overlapped
worker must return the parallel handover, never self-complete).
Those workers implement, test, commit, and return their workspace, commits, and
the exact handover paths. They do **not** call `flowctl done`, project tracker
state, invoke plan-sync, run impl-review, or integrate their own commit. This
host-deferred shape is independent of `REVIEW_MODE`; the conductor preserves
the resolved backend and applies it after integration. The prompt fields are an
internal handoff, not a public CLI or stored schema.

**Codex-delegation flags — appended only when `delegation_active`, Phase 1.5's
gates all passed, and (for `work.delegateDecision=ask` interactive) the host
confirmed this task.** Append the resolved flags to the worker prompt; the worker
delegates its Phase 2 implementation to `codex exec` per
[references/codex-delegation.md](references/codex-delegation.md) — whose
`Gate outcome — the resolved flags passed to each worker` block is the exact
set to append (model resolved via `flowctl models resolve delegate`). Omit them
entirely (or pass `DELEGATE: local`) when delegation is off or a gate failed —
the worker then runs standard in-session implementation, unchanged. **The flags are provisional — the worker owns the final per-task call**: its thin-task valve (worker.md Phase 2) may still run the task standard in-session, emitting no `DELEGATION_*` lines (counter untouched). A conductor that counted an unemitted signal as a strike has broken this.

**Worker returns**: Summary of implementation, files changed, test results,
review verdict on the single-worker path; or task ID, workspace, commits, and
task-unique handover paths on the parallel path.

### 3d. Join, Integrate, and Verify

**Parallel wave or reviewer-overlap dispatch** (3a `Dispatch count` > 1, or an
fn-176 overlapped one-task wave): read
[references/wave-join.md](references/wave-join.md) and execute it — it owns the
join report, integration, collision handling (never auto-resolve), the
reviewer-overlap schedule point and its plan-sync barrier, the per-task review
passes, the mandatory integrated-target verification before `done`, completion,
and workspace-first partial-failure diagnosis. Do not select more work or run
plan-sync until every dispatched worker has returned and the wave is resolved.

On the single-worker path, verify completion as before:

```bash
$FLOWCTL show <task-id> --json
```

#### 3d.0 host-deferred gate (runs FIRST on the single-worker path when this task's REVIEW_MODE was `host-deferred`)

A host-deferred worker returns with the task still `in_progress` BY DESIGN — that is the contract, not a failure. Before any failure classification, read [references/host-deferred-review.md](references/host-deferred-review.md) and execute its `3d.0 gate` section (re-read the persisted base, confirm the handover, run the mandatory `/flow-next:impl-review --review=host`, update evidence, then `done` only on SHIP). Only after this gate does the standard rule below apply to host-deferred tasks.

If status is not `done` (and the 3d.0 gate did not apply or already ran), the worker failed. Diagnose from ground truth (below) then retry — **but the retry is bounded**: keep a per-task standard-failure strike counter (the mirror of the delegation circuit breaker in 3d.2, which only covers `delegation_active`). **After 2 consecutive non-`done` returns for the *same task*** (a worker that keeps aborting early or a persistently red Quick command), retrying stops and the failure escalates. A third respawn of the same task has broken this. Under `SPEC_MODE` / `mode:autonomous`, emit the worker's typed `BLOCKED: <reason>` as a `NEEDS_HUMAN` line and move on to the next ready task (autonomy's "never hang" promise has no loop-guard otherwise — a bad Quick command or broken baseline would respawn workers forever); interactively, surface the failure and stop.

**Lost / errored worker result (`[Tool result missing due to internal error]`).** On long runs the host (Agent-tool) can drop the worker's completion report — you get an error placeholder instead of the report, even though the worker's *work* may be complete. Don't block waiting for a result that will never arrive. Treat a missing/errored result the same as "status not `done`" and **diagnose from ground truth** before retrying:

```bash
$FLOWCTL show <task-id> --json          # status + evidence the worker recorded
git log --oneline -5                     # did the worker leave commits?
git status --short                       # uncommitted-but-complete changes?
```

Classify and act:
- **Already `done`** (status `done`, clean worktree at HEAD) — the report was lost but the task finished. Proceed to plan-sync (3e) as normal.
- **Code present but not finalized** (commits and/or uncommitted changes exist, but status is still `in_progress` and build/review/`flowctl done` never ran) — spawn a **re-anchoring continuation worker** that re-reads the spec + current task status + `git status`/`git diff` and resumes from the late phase (verify build → review → `flowctl done`), rather than restarting the task from scratch.
- **Nothing landed** (no commits, clean worktree, still `in_progress`) — the worker aborted early; retry the task normally.

Done when: every dispatched task in the wave reads `done`, or has been escalated with a typed reason after its second consecutive failure — and no task is left silently `in_progress`.

#### 3d.1 Tracker sync (opt-in) — task done → status comment + evidence

**Optional. Runs only when the tracker bridge is active AND `work.done` is opted in, and only when the task reached `done` (from 3d). With no tracker configured this is a no-op.**

```bash
ACTIVE=0
# NO pipelines in the probe — a failed producer masked by a healthy consumer
# fails CLOSED. Capture raw first, rc-checked; parse separately.
RAW="$($FLOWCTL sync active --json 2>/dev/null)" || ACTIVE=1     # probe ERROR ⇒ ACTIVE (fail open)
if [ "$ACTIVE" = "0" ]; then
  VAL="$(printf '%s' "$RAW" | jq -r '.active' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
  [ "$VAL" = "true" ] && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
  echo "GATE ACTIVE — read and execute references/tracker-touchpoints.md#task-done, then continue with Phase 3d.2."
fi   # default branch: bare no-op — NO link, NO read path
```

When the sentinel prints, read [references/tracker-touchpoints.md](references/tracker-touchpoints.md), execute its `Task done` section (`work.done` leaf check + best-effort dispatch), then continue with Phase 3d.2. When the gate is silent (bridge inactive), continue — nothing fires here.

#### 3d.2 Delegated worker signal (runs only when `delegation_active`)

Apply the already-loaded delegation reference's host circuit-breaker contract
after each returned delegated worker. A missing `DELEGATION_*` signal leaves
the counter untouched; a tool failure disables delegation immediately; three
consecutive task misses disable it; success resets the streak. Once disabled,
omit `DELEGATE:*` flags from later workers and continue standard mode. Preserve
the inlined delegation evidence as the durable Ralph/log receipt surface.

### 3e. Plan Sync After the Resolved Wave (if enabled) — both modes

**Runs in SINGLE_TASK_MODE and SPEC_MODE.** Only the loop-back in 3f differs by mode.

Do not run plan-sync while any peer worker is active or the wave is unresolved.
After the join, integration, review, and completion steps finish, run this
section once for each task that reached `done` in the resolved wave. If a task
is not `done`, skip plan-sync for it and investigate/retry.

Check if plan-sync should run:

```bash
$FLOWCTL config get planSync.enabled --json
```

Skip unless planSync.enabled is explicitly `true` (null/false/missing = skip) — but a skip still records its outcome line (`stage: plan-sync - skipped(config: planSync.enabled != true)`, see the stage-outcome block below) before advancing to 3f.

Downstream target extraction, the `planSync.crossSpec` read, and the `plan-sync`
subagent dispatch live in [references/plan-sync-dispatch.md](references/plan-sync-dispatch.md)
— read it and execute it now, then record the stage-outcome line below. Its skip
and failure branches (`skipped(empty: ...)`, `failed(EXTRACT_FAILED: ...)`) feed
that same line.

**Stage-outcome line (mandatory — fn-178).** Whatever happened above, record ONE
outcome line for the plan-sync stage in the completed task's done evidence (the
task .md `## Done summary` the run already writes, via a small append or the
next `flowctl done` summary when the wave is still resolving):

```
stage: plan-sync - ran [<start>..<end>] | skipped(config: planSync.enabled != true) | skipped(empty: no downstream todo tasks) | failed(EXTRACT_FAILED: <detail>) | failed(error: <detail>)
```

**A skipped stage is an event with a reason, never an absence.** `DOWNSTREAM=EXTRACT_FAILED`
yields a `failed(EXTRACT_FAILED...)` line (the #293 class becomes visible on
first occurrence) and "no downstream tasks" yields `skipped(empty...)`, which is
distinguishable from a broken extraction; a run that recorded a broken extraction as
"nothing to do", or omitted the line entirely, has broken this. Include start..end
timestamps when this orchestrator knows them.

Done when: each `done` task in the resolved wave carries exactly one `stage: plan-sync - …` line in its evidence.

### 3f. Loop or Finish

**Steps 3d and 3e run after the whole selected wave returns, in both modes.** A run
that skipped either because it was in `SINGLE_TASK_MODE` has broken this. Only the
loop-back behavior differs:

**SINGLE_TASK_MODE**: After 3d→3e, go to Phase 4 (Quality). No loop.

**SPEC_MODE**: After 3d→3e, recompute the next ready frontier at 3a. Never
select it before the current wave is joined and resolved.

### 3g. Completion Review Gate (SPEC_MODE only)

When 3a finds no ready tasks, check if completion review is required.

**Check spec's completion review status directly:**

```bash
$FLOWCTL show <spec-id> --json | jq -r '.completion_review_status'
```

- If `ship` → review already passed, go to Phase 4
- If `unknown` or `needs_work` → needs review

**If review needed:**

1. Invoke `/flow-next:spec-completion-review <spec-id>` skill
   - Pass `--review=<backend>` matching the work review backend
   - Skill handles rp/codex/copilot/cursor/host backend dispatch
   - Skill runs its fix loop internally until SHIP and writes terminal
     `completion_review_status` through its backend-aware shared owner

2. After skill returns with SHIP:
   - **Tracker sync (opt-in) — SHIP posts a verdict comment, never a terminal `Done` (fn-66):** runs only when the tracker bridge is active and `completionReview` is opted in. With no tracker configured this is a no-op:

     ```bash
     ACTIVE=0
     # NO pipelines in the probe — a failed producer masked by a healthy consumer
     # fails CLOSED. Capture raw first, rc-checked; parse separately.
     RAW="$($FLOWCTL sync active --json 2>/dev/null)" || ACTIVE=1     # probe ERROR ⇒ ACTIVE (fail open)
     if [ "$ACTIVE" = "0" ]; then
       VAL="$(printf '%s' "$RAW" | jq -r '.active' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
       [ "$VAL" = "true" ] && ACTIVE=1
     fi
     if [ "$ACTIVE" = "1" ]; then
       echo "GATE ACTIVE — read and execute references/tracker-touchpoints.md#completion-review, then continue with Phase 4."
     fi   # default branch: bare no-op — NO link, NO read path
     ```

     When the sentinel prints, read [references/tracker-touchpoints.md](references/tracker-touchpoints.md), execute its `Completion review` section (`completionReview` leaf check + comment-shaped verdict/R-ID-coverage dispatch), then continue with Phase 4. **`land.merged` is the only driver that writes terminal `Done`/`verified`** — a dispatch from here that flipped the issue terminal has broken this. When the gate is silent (bridge inactive), continue — nothing fires here.
   - Go to Phase 4 (Quality)

**Note:** The spec-completion-review skill owns the terminal
`completion_review_status` write. Work never writes that status again. After
the skill returns SHIP, Work only posts the opt-in verdict / R-ID-coverage
comment to the linked tracker issue here. **That comment never flips the
issue to `Done`/`verified`** (fn-66: that is gated on a `MERGED` PR and driven
solely by `land.merged`).

**Fix loop behavior**: Same as impl-review. If reviewer returns NEEDS_WORK:
1. Skill parses issues
2. Skill fixes code inline
3. Skill commits
4. Skill re-reviews (same chat for rp, same session for codex)
5. Repeat until SHIP

Only after SHIP does control return here. If skill outputs `<promise>RETRY</promise>`, there was a backend error - retry the skill invocation.

Done when: `completion_review_status` reads `ship` (or the gate did not apply), and the opt-in tracker comment either fired or was a documented no-op.

---

**Why spawn a worker?**

Context optimization. Each task gets fresh context:
- No bleed from previous task implementations
- Re-anchor info stays with implementation (not lost to compaction)
- Review cycles stay isolated
- Main conversation stays lean (just summaries)

**Ralph mode**: Worker inherits `bypassPermissions` from parent. FLOW_RALPH=1 and REVIEW_RECEIPT_PATH are passed through.

**Autonomous mode** (`mode:autonomous` token or `FLOW_AUTONOMOUS=1`): forward `FLOW_AUTONOMOUS=1` to the worker when set. It suppresses questions only — no receipt obligations, no ralph-guard activation; never set `FLOW_RALPH` from it.

**Interactive mode**: Permission prompts pass through to user. Worker runs in foreground (blocking).

## Phase 4: Quality

After all tasks complete (or periodically for large specs):

- Run `$FLOWCTL gate classify --base "$(cat .flow/tmp/spec_base)"`; exit 0 means docs-only tier-B: run lint/format only and note `Gates: docs-only tier-B` for the Phase 5 final summary. On nonzero, run the full gates.
- For each full gate (test) command that would run, first probe `$FLOWCTL gate check --gate <gate_id> --command "<cmd>"`; exit 0 means skip that re-run and note `Gates: baseline reused (green receipt <sha8>)` for the Phase 5 final summary. On nonzero, run it. After any passing full gate run here, write its receipt with `$FLOWCTL gate receipt --gate <gate_id> --command "<cmd>"`.
- Run lint/format per repo
- If change is large/risky, run the quality auditor subagent:
  - Task flow-next:quality-auditor("Review recent changes")
- Fix critical issues

Host skips cannot land in task evidence because tasks are already done by Phase 4. **Every skip/honor outcome is accumulated as it happens** (gate_id, plus the receipt `<sha8>` where one was honored) **and surfaces as its own `Gates:` line in the Phase 5 final summary.** A silent skip, or several mixed outcomes collapsed into one line, has broken this (a periodic Phase 4 pass can produce several: some gates receipt-reused, some run full, a later pass docs-only).

Done when: lint/format ran, every full gate either ran green or was receipt-honored, and one `Gates:` line is queued per outcome.

## Phase 5: Ship

**Verify all tasks done**:
```bash
$FLOWCTL show <spec-id> --json
$FLOWCTL validate --spec <spec-id> --json
```

**Final commit** (if any uncommitted changes):
```bash
git add -A
git status
git diff --staged
git commit -m "<final summary>"
```

**The spec is left open unless the user explicitly asked for it to be closed** —
Ralph closes done specs at the end of the loop. A run that closed the spec on its
own initiative has broken this.

Then push + open PR if user wants.

**Tracker-sync end-of-run check - LAST action before the final summary.** Read-only audit: did every lifecycle touchpoint that triggered this run actually fire (receipt-backed)? It runs independently of the touchpoints, so a wholesale-skipped facade call is still caught. With no tracker configured, `sync check` exits silently in constant time; the summary slot then reads `n/a (bridge inactive)` and nothing else changes.

```bash
# Tasks worked this run = the task ids Phase 3 claimed/completed (you know these
# from the loop; substitute them).
WORKED="<task-id-1> <task-id-2> ..."

# --since: earliest claimed_at among tasks worked this run. On-disk anchor —
# bash vars do NOT survive across tool calls; flowctl show re-derives it anytime.
SINCE=""
for T in $WORKED; do
  TS="$($FLOWCTL show "$T" --json | jq -r '.claimed_at // empty')"
  [ -n "$TS" ] && { [ -z "$SINCE" ] || [ "$TS" \< "$SINCE" ]; } && SINCE="$TS"
done

# --events: ONLY what actually triggered this run (triggered-set contract):
#   ≥1 task claimed this run            → include work.firstClaim
#   ≥1 task reached done this run       → include work.done
#   completion review ran this run (3g) → include completionReview
# Configured-but-not-triggered events are never checked, never MISSING.
EVENTS="work.firstClaim,work.done"   # ← substitute the actual triggered set

"$FLOWCTL" sync check "$SPEC_ID" --events "$EVENTS" --since "$SINCE" --json
# Empty output → bridge inactive → slot = `n/a (bridge inactive)`. Otherwise
# `.missing` empty → slot = `OK`; non-empty → retro-fire (below).
# Under Ralph (FLOW_RALPH=1 / REVIEW_RECEIPT_PATH set): route any echo of check
# output to stderr (>&2) — work's stdout stays clean for harness parsing.
```

(Nothing triggered at all — no claims, no dones, no 3g, e.g. a resumed no-op run — skip the check; the slot is vacuously `OK`.)

**Retro-fire on MISSING — exactly ONE cycle, never blocking.** When `.missing` is
non-empty, read [references/tracker-retro-fire.md](references/tracker-retro-fire.md)
and execute its cycle (anchor → per-event inline tracker-sync wrapper call → re-check
the missed events only → record the final state in the summary slot). Still MISSING
after the one cycle is a recorded, visible outcome — never a second retro-fire, never
a block.

**Final summary (mandatory template).** End the run with this block. **`Tracker sync:` is a required field carrying exactly one of its four states** — an explicit `n/a` proves the check ran, and an absent field reads as a skipped check. A summary printed without the slot has broken this. Under Ralph, the summary goes to the summary block / stderr, never stdout. The `Gates:` slot is where host-layer gate skips surface — one `Gates:` line per accumulated Phase 4 outcome (repeat the line for each skip/honor so none is overwritten); worker-layer skips live in each task's evidence `tests[]`.

```
Spec: <spec-id> — <title>
Tasks: <n done>/<total>
Tests: <commands + result>
Review: <verdict | n/a>
Gates: <full | baseline reused (green receipt <sha8>) | docs-only tier-B>   # one line per outcome; repeat for each
Tracker sync: <OK | MISSING:<event> → retro-fired → OK | MISSING:<event> (retro-fire failed: <reason>) | n/a (bridge inactive)>
```

**Stage-outcome lines (fn-178, binding on every stage this run orchestrated).**
Each optional or delegated stage the run reached (plan-sync, impl-review,
completion review, QA, a delegation attempt, a wave dispatch) records exactly
one line in the receipt surface it already writes — the task's `## Done
summary` for task-scoped stages, this final summary for run-scoped ones:

```
stage: <name> - ran [<start>..<end>] | skipped(<policy|config|empty|error>: <detail>) | failed(<reason>: <detail>)
```

**A skipped stage is an event with a reason, never an absence** — review treats a
stage with no line as failed (that inversion is the point: "no record" can never
again masquerade as "nothing to do", the #293 class). A stage this run reached
that left no line has broken this. Timestamps ride the line only where this
orchestrator knows them; there is no separate timing store. Token/cost telemetry
is out of scope — it is host-side data flowctl cannot observe (a future host
integration could report it; nothing here does). Reading them back:
`flowctl usage --stages <spec-id>` summarizes ran/skipped/failed counts + reasons
from the committed receipts.

Done when: all tasks read `done`, `flowctl validate` passes, the tracker-sync check has run, and the final summary block is printed with its `Tracker sync:` slot and one `Gates:` line per Phase 4 outcome.

## Definition of Done

Confirm before ship:
- All tasks have status "done"
- `$FLOWCTL validate --spec <id>` passes
- Tests pass
- Lint/format pass
- Docs updated if needed
- Working tree is clean
- Final summary printed with the mandatory `Tracker sync:` slot (one of the four states — explicit `n/a (bridge inactive)` when no tracker is configured)

## Example flow

```
Phase 1 (resolve) → Phase 2 (branch) → Phase 3:
  ├─ 3a-c: inspect frontier → select/claim wave → dispatch isolated worker(s)
  ├─ 3d: join → integrate → review/complete each task
  ├─ 3e: plan-sync after the wave resolves (if enabled + downstream tasks exist)
  ├─ 3f: SPEC_MODE? → loop to 3a | SINGLE_TASK_MODE? → Phase 4
  ├─ no more tasks → 3g: check completion_review_status
  │   ├─ status != ship → invoke /flow-next:spec-completion-review → skill fixes, writes SHIP once, returns
  │   └─ status = ship → Phase 4
  └─ Phase 4 (quality) → Phase 5 (ship: verify → commit → sync check → retro-fire MISSING once → summary w/ Tracker sync slot)
```
