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
FLOWCTL="$HOME/.codex/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Phase 0: Delegation value-check (cheap, single step)

**This is the ONLY step the Codex-delegation feature adds to the default work
path.** With delegation off (the default), it resolves to a no-op and the rest
of `phases.md` is byte-identical to before (R1/R3).

```bash
# Cheap host short-circuit FIRST — delegation is Claude-Code-only. On a non-Claude
# orchestrator (Codex / Droid / OpenCode) this resolves delegation OFF *before* the
# ~45k references/codex-delegation.md is ever read, so that reference never loads
# into a non-Claude host's context just to be disabled by Gate 1. (Gate 1 in the
# reference stays the authoritative full platform check — incl. the OPENCODE_* env
# scan; this is its cheap pre-check subset, run pre-load.)
host_is_claude_code() {
 [ -n "${CLAUDECODE:-}" ] || return 1 # not Claude Code → off
 [ -z "${DROID_PLUGIN_ROOT:-}" ] || return 1 # Droid → off (compat alias not keyed)
 [ -z "${OPENCODE:-}" ] || return 1 # OpenCode → off
 return 0
}
# Single value-check — same shape as the tracker-sync touchpoints (SKILL.md).
# Guard a missing .flow/: a fresh repo / idea-or-markdown input has not been
# `flowctl init`ed yet (that happens in Phase 1), and `config get` errors on an
# absent .flow/. Treat missing .flow/ as delegation OFF — a bare-idea input is
# never delegation-eligible anyway (delegation requires a plan/spec/task input).
if [ -d .flow ]; then
 DELEGATE_CFG="$($FLOWCTL config get work.delegate --json | jq -r '.value')"
else
 DELEGATE_CFG=false
fi
# delegation_active = host_is_claude_code && (arg delegate:codex | DELEGATE_CFG == "codex") && not arg delegate:local
# On a non-Claude-Code host delegation_active is FALSE here — codex-delegation.md
# is never read. The generic "use codex" is NOT the token — review backend.
```

If `delegation_active` is **false** (the default), do nothing more here and run
Phase 1 onward exactly as written — no `INPUT_WAS_BARE_PROMPT` capture, no gates,
no pointer. **If and only if `delegation_active` is true**, ALSO run the
`INPUT_WAS_BARE_PROMPT` capture inside Phase 1 (below) and Phase 1.5
(host pre-flight gates). See [references/codex-delegation.md](references/codex-delegation.md).

## Phase 1: Resolve Input

Detect input type in this order (first match wins):

1. **Flow task ID** `fn-N-slug.M` (e.g., fn-1-add-oauth.3) or legacy `fn-N.M`/`fn-N-xxx.M` → **SINGLE_TASK_MODE**
2. **Flow spec ID** `fn-N-slug` (e.g., fn-1-add-oauth) or legacy `fn-N`/`fn-N-xxx` → **SPEC_MODE**
3. **Resolvable handle** — any single-token arg that `$FLOWCTL show <arg> --json` resolves (including a tracker key like `wor-17` / `wor-17.1`, which flowctl's widened resolver maps to the linked spec/task — fn-52.10/.16). A `.`-containing handle is a task (SINGLE_TASK_MODE); otherwise a spec (SPEC_MODE).
4. **Spec file** `.md` path that exists on disk → **SPEC_MODE**
5. **Idea text** everything else → **SPEC_MODE**

**Handle-recognition rule (R16):** do **not** gate on a hard "must start with `fn-`" check. Before treating a single-token arg as idea text, route it through `$FLOWCTL show <arg> --json` — if it resolves (rc 0), it is an existing spec/task (use the canonical id from the JSON), never a new idea. Only a non-resolving token that isn't an `.md` path falls through to idea text. So `work wor-17` / `work wor-17.1` resolve the existing spec/task; they are never re-created.

**Track the mode** — it controls looping in Phase 3.

**Original-input-kind capture (ONLY when `delegation_active` — Phase 0).** A bare
idea-text input (match #5 above — not a Flow id, not a resolvable handle, not an
existing `.md` spec path) gets promoted into a spec+task by the steps below, so
its original kind must be recorded **before** that promotion. Set the flag here,
on the ORIGINAL input, immediately after detection and **before** running any
"Spec file start" / "Spec-less start" promotion step:

```bash
# Runs ONLY when delegation_active (resolved in Phase 0). On the default
# (delegation-off) path this step does not exist — Phase 0 already returned.
if <original input matched #5 idea text>; then
 INPUT_WAS_BARE_PROMPT=1 # promoted bare prompt → NOT eligible for delegation (Gate 5)
else
 INPUT_WAS_BARE_PROMPT=0 # Flow id / resolvable handle / existing .md spec → eligible
fi
```

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
4. Create spec: `$FLOWCTL spec create --title "<extracted-title>" --json`
5. Set spec from file: `$FLOWCTL spec set-plan <spec-id> --file <path> --json`
6. Create single task: `$FLOWCTL task create --spec <spec-id> --title "Implement <title>" --json`
7. Continue with spec-id

**Spec-less start (idea text)**:
1. Initialize: `$FLOWCTL init --json`
2. Create spec: `$FLOWCTL spec create --title "<idea>" --json`
3. Create single task: `$FLOWCTL task create --spec <spec-id> --title "Implement <idea>" --json`
4. Continue with spec-id

## Phase 1.5: Codex-delegation host pre-flight gates (ONLY when `delegation_active`)

**Skip this entire phase unless `delegation_active` is true (Phase 0).** On the
default (delegation-off) path this phase does not exist — proceed straight to
Phase 2.

When `delegation_active`, read [references/codex-delegation.md](references/codex-delegation.md)
and run its host pre-flight gates + one-time consent **ONCE here**, before the
Phase 3 per-task loop. Run them in the **host** (this skill) — NOT the worker
subagent, which cannot call `plain-text numbered prompt` (#12890/#34592). The reference
pins the exact probes; the gate sequence is:

1. **Platform gate** — Claude Code only: `CLAUDECODE` present AND
 `DROID_PLUGIN_ROOT` unset AND no OpenCode marker. NOT keyed on `CODEX_*`
 (so `CODEX_SANDBOX=auto`, Ralph's review-backend knob, stays eligible).
2. **Recursion guard** — trips on a Codex-runtime `CODEX_SANDBOX` value (outside
 the flow-next config set `{read-only,workspace-write,danger-full-access,auto}`)
 or `CODEX_SANDBOX_NETWORK_DISABLED` — NOT on `CODEX_SANDBOX=auto`.
3. **Availability** — `command -v codex` resolves.
4. **One-time consent** — interactive `plain-text numbered prompt` for the sandbox mode
 (yolo recommended | full-auto), persisted to `work.delegateConsent` /
 `work.delegateSandbox`; a second run with consent already `true` does not
 re-prompt. **Headless (Ralph):** no prompt — proceed only if consent already
 `true`, else delegation stays silently off.
5. **Input kind** — `INPUT_WAS_BARE_PROMPT != 1` (a promoted bare prompt is not
 eligible; decided on the ORIGINAL input, Phase 1).
6. **Clean baseline (code tree)** — `git status --porcelain` shows **no non-`.flow/`
 worktree changes**. Load-bearing: on a rollback the worker reverts tracked files
 authoritatively from `BASE_COMMIT` (`git reset --mixed` + `git checkout -- .
 ':(exclude).flow'`), which would ALSO discard PRE-EXISTING non-`.flow` edits a
 dirty tree carried in. So a dirty code tree ⇒ delegation OFF (commit/stash first,
 or run standard mode). Host-owned `.flow/` dirtiness (plan-sync edits, scratch)
 is excluded and never trips this — only non-`.flow/` changes do.

**Any gate failure → standard in-session mode for the rest of the run** (never
blocks the worker). When all gates pass, the host resolves the per-task decision
(`work.delegateDecision`: `auto` delegates every eligible task; `ask` prompts
before each in interactive mode — headless treats `ask` as `auto` only when
consent is pre-granted) and carries the resolved flags into Phase 3c.

## Phase 2: Apply Branch Choice

Based on user's answer from setup questions:

- **Worktree**: use `skill: flow-next-worktree-kit`
- **New branch**:
 ```bash
 git checkout main && git pull origin main
 git checkout -b <branch>
 ```
- **Current branch**: proceed (user already confirmed)

## Phase 3: Task Loop

**For each task**, use the worker agent with fresh context.

**Circuit-breaker counter init (ONLY when `delegation_active` — Phase 0/1.5).**
The breaker counter is **host-owned**: each task is a fresh-context worker, so an
in-worker counter would reset every task and never trip. Initialize ONCE here,
before the per-task loop (skip entirely on the default delegation-off path):

```text
consecutive_failures = 0
# delegation_active was resolved by the Phase 1.5 gates (true iff all passed).
```

After each delegated worker returns, the host bridges the worker's terminal
`DELEGATION_RESULT=`/`DELEGATION_ACTION=` signal into this counter — see 3d.2.

### 3a. Find Next Task

```bash
$FLOWCTL ready --spec <spec-id> --json
```

If no ready tasks, check for completion review gate (see 3g below).

### 3b. Start Task

```bash
$FLOWCTL start <task-id> --json
```

#### 3b.1 Tracker sync (opt-in) — first claim → In-Progress

**Optional. Runs only when the tracker bridge is active AND `work.firstClaim` is opted in. With no tracker configured this is a no-op — the work flow is unchanged.**

```bash
ACTIVE=0
# NO pipelines in the probe — a failed producer masked by a healthy consumer
# fails CLOSED. Capture raw first, rc-checked; parse separately.
RAW="$($FLOWCTL sync active --json 2>/dev/null)" || ACTIVE=1 # probe ERROR ⇒ ACTIVE (fail open)
if [ "$ACTIVE" = "0" ]; then
 VAL="$(printf '%s' "$RAW" | jq -r '.active' 2>/dev/null)" || ACTIVE=1 # parse ERROR ⇒ ACTIVE
 [ "$VAL" = "true" ] && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
 echo "GATE ACTIVE — STOP. Read references/tracker-touchpoints.md#first-claim before continuing."
fi # default branch: bare no-op — NO link, NO read path
```

When the sentinel prints, STOP and Read [references/tracker-touchpoints.md](references/tracker-touchpoints.md) before any further step — its `First claim` section holds this touchpoint's `work.firstClaim` leaf check + dispatch (best-effort; never blocks the worker). When the gate is silent (bridge inactive), continue — nothing fires here.

### 3c. Run Worker Agent

Use the **worker** agent role to implement the task. The worker gets fresh context and handles:
- Re-anchoring (reading spec, git status, task-relevant glossary terms when populated)
- Implementation
- Committing
- Review cycles (if enabled)
- Completing the task (flowctl done)

**`REVIEW_MODE` is per-task, not a fixed run-wide value.** Resolve it for THIS task: if the user
passed an explicit `--review=<backend>` to `/flow-next:work`, use that (a deliberate run-wide override
wins for every task); OTHERWISE resolve task-aware — `REVIEW_MODE=$($FLOWCTL review-backend "$TASK_ID")`
— so a task's own `review:` override (e.g. `review: cursor:...` under a `codex` project default) selects
its backend rather than the project default. `none` still skips review.

**Invoke the worker:**

"Use the worker agent to implement this task:

TASK_ID: fn-X.Y
SPEC_ID: fn-X
FLOWCTL: $FLOWCTL
REVIEW_MODE: none|rp|codex|copilot|cursor
RALPH_MODE: true|false

Follow your phases exactly."

**Worker returns**: Summary of implementation, files changed, test results, review verdict.

### 3d. Verify Completion

After the worker agent returns, verify the task completed:

```bash
$FLOWCTL show <task-id> --json
```

If status is not `done`, the worker agent failed. Diagnose from ground truth (below) then retry — but **BOUNDED**: keep a per-task standard-failure strike counter (the mirror of the delegation circuit breaker in 3d.2, which only covers `delegation_active`). After **2** consecutive non-`done` returns for the *same task* (a worker that keeps aborting early or a persistently red Quick command), STOP retrying and escalate — do NOT respawn unboundedly. Under `SPEC_MODE` / `mode:autonomous`, emit the worker's typed `BLOCKED: <reason>` as a `NEEDS_HUMAN` line and move on to the next ready task (autonomy's "never hang" promise has no loop-guard otherwise — a bad Quick command or broken baseline would rerun worker agents forever); interactively, surface the failure and stop.

**Lost / errored worker result (`[Tool result missing due to internal error]`).** On long runs the host (Agent-tool) can drop the worker's completion report — you get an error placeholder instead of the report, even though the worker's *work* may be complete. Don't block waiting for a result that will never arrive. Treat a missing/errored result the same as "status not `done`" and **diagnose from ground truth** before retrying:

```bash
$FLOWCTL show <task-id> --json # status + evidence the worker recorded
git log --oneline -5 # did the worker leave commits?
git status --short # uncommitted-but-complete changes?
```

Classify and act:
- **Already `done`** (status `done`, clean worktree at HEAD) — the report was lost but the task finished. Proceed to plan-sync (3e) as normal.
- **Code present but not finalized** (commits and/or uncommitted changes exist, but status is still `in_progress` and build/review/`flowctl done` never ran) — spawn a **re-anchoring continuation worker** that re-reads the spec + current task status + `git status`/`git diff` and resumes from the late phase (verify build → review → `flowctl done`), rather than restarting the task from scratch.
- **Nothing landed** (no commits, clean worktree, still `in_progress`) — the worker aborted early; retry the task normally.

#### 3d.1 Tracker sync (opt-in) — task done → status comment + evidence

**Optional. Runs only when the tracker bridge is active AND `work.done` is opted in, and only when the task reached `done` (from 3d). With no tracker configured this is a no-op.**

```bash
ACTIVE=0
# NO pipelines in the probe — a failed producer masked by a healthy consumer
# fails CLOSED. Capture raw first, rc-checked; parse separately.
RAW="$($FLOWCTL sync active --json 2>/dev/null)" || ACTIVE=1 # probe ERROR ⇒ ACTIVE (fail open)
if [ "$ACTIVE" = "0" ]; then
 VAL="$(printf '%s' "$RAW" | jq -r '.active' 2>/dev/null)" || ACTIVE=1 # parse ERROR ⇒ ACTIVE
 [ "$VAL" = "true" ] && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
 echo "GATE ACTIVE — STOP. Read references/tracker-touchpoints.md#task-done before continuing."
fi # default branch: bare no-op — NO link, NO read path
```

When the sentinel prints, STOP and Read [references/tracker-touchpoints.md](references/tracker-touchpoints.md) before any further step — its `Task done` section holds this touchpoint's `work.done` leaf check + dispatch (best-effort; never blocks the work loop). When the gate is silent (bridge inactive), continue — nothing fires here.

#### 3d.2 Circuit breaker (ONLY when `delegation_active`) — bridge the worker signal

**Skip unless `delegation_active`.** When a delegated worker returns, parse its
terminal `DELEGATION_RESULT=<class>` + `DELEGATION_ACTION=<action>` lines (both
from `flowctl codex classify-result`, fn-55.4) and update the host-owned counter
(init'd at the top of Phase 3). The worker emits these lines ONLY when delegation
was active for the task — **a missing signal means the task ran standard and the
counter is untouched** (e.g. a gate failed mid-run, all units were trivial, or the
worker fell back to in-session).

```text
case DELEGATION_ACTION:
 rollback_and_disable → # a cli_failure — tool itself unhealthy
 delegation_active = false # disable IMMEDIATELY for ALL remaining tasks
 rollback | finish_locally → # task_failure / partial — a per-task miss
 consecutive_failures += 1
 if consecutive_failures >= 3:
 delegation_active = false # 3 strikes → standard mode for the rest
 commit → # success
 consecutive_failures = 0 # reset the consecutive streak
# (no DELEGATION_* lines → standard task → counter untouched)
```

Once `delegation_active` flips **false**, the host stops appending the
`DELEGATE:*` flags to subsequent worker prompts (3c) — every remaining task runs
standard in-session, and the loop **never blocks** (Ralph-safe: failures degrade,
they don't halt). The inlined `evidence.delegation` the worker wrote into
`flowctl done` is the durable proof-of-work surface (Ralph log / receipt).

### 3e. Plan Sync (if enabled) — BOTH MODES

**Runs in SINGLE_TASK_MODE and SPEC_MODE.** Only the loop-back in 3f differs by mode.

Only run plan-sync if the task status is `done` (from step 3d). If not `done`, skip plan-sync and investigate/retry.

Check if plan-sync should run:

```bash
$FLOWCTL config get planSync.enabled --json
```

Skip unless planSync.enabled is explicitly `true` (null/false/missing = skip).

Get remaining tasks (todo status = not started yet):

```bash
$FLOWCTL tasks --spec <spec-id> --status todo --json
```

Skip if empty (no downstream tasks to update).

Extract downstream task IDs:

```bash
DOWNSTREAM=$($FLOWCTL tasks --spec <spec-id> --status todo --json | jq -r '[.[].id] | join(",")')
```

Note: Only sync to `todo` tasks. `in_progress` tasks are already being worked on - updating them mid-flight could cause confusion.

Read the cross-spec flag (single config-leaf read — plan-sync.md documents `CROSS_SPEC` as a caller-provided input):

```bash
CROSS_SPEC=$($FLOWCTL config get planSync.crossSpec --json | jq -r '.value')
```

Use the plan_sync agent with this prompt:

```
Sync downstream tasks after implementation.

COMPLETED_TASK_ID: fn-X.Y
SPEC_ID: fn-X
FLOWCTL: /path/to/flowctl
DOWNSTREAM_TASK_IDS: fn-X.3,fn-X.4,fn-X.5
CROSS_SPEC: <the $CROSS_SPEC value read above — literal "true" or "false", NOT the string "true|false">

Follow your phases in plan-sync.md exactly.
```

Plan-sync returns summary. Log it but don't block - task updates are best-effort.

### 3f. Loop or Finish

**IMPORTANT**: Steps 3d and 3e ALWAYS run after worker returns, regardless of mode. Only the loop-back behavior differs:

**SINGLE_TASK_MODE**: After 3d→3e, go to Phase 4 (Quality). No loop.

**SPEC_MODE**: After 3d→3e, return to 3a for next task.

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
 - Skill handles rp/codex/copilot/cursor backend dispatch
 - Skill runs fix loop internally until SHIP verdict

2. After skill returns with SHIP:
 - Set status: `$FLOWCTL spec set-completion-review-status <spec-id> --status ship --json`
 - **Tracker sync (opt-in) — SHIP → verdict comment, NEVER terminal Done (fn-66):** runs only when the tracker bridge is active AND `completionReview` is opted in. With no tracker configured this is a no-op:

 ```bash
 ACTIVE=0
 # NO pipelines in the probe — a failed producer masked by a healthy consumer
 # fails CLOSED. Capture raw first, rc-checked; parse separately.
 RAW="$($FLOWCTL sync active --json 2>/dev/null)" || ACTIVE=1 # probe ERROR ⇒ ACTIVE (fail open)
 if [ "$ACTIVE" = "0" ]; then
 VAL="$(printf '%s' "$RAW" | jq -r '.active' 2>/dev/null)" || ACTIVE=1 # parse ERROR ⇒ ACTIVE
 [ "$VAL" = "true" ] && ACTIVE=1
 fi
 if [ "$ACTIVE" = "1" ]; then
 echo "GATE ACTIVE — STOP. Read references/tracker-touchpoints.md#completion-review before continuing."
 fi # default branch: bare no-op — NO link, NO read path
 ```

 When the sentinel prints, STOP and Read [references/tracker-touchpoints.md](references/tracker-touchpoints.md) before any further step — its `Completion review` section holds this touchpoint's `completionReview` leaf check + the comment-shaped dispatch (verdict + R-ID coverage; never a terminal `Done`/`verified` push — land.merged is the SOLE Done driver). When the gate is silent (bridge inactive), continue — nothing fires here.
 - Go to Phase 4 (Quality)

**Note:** The spec-completion-review skill gets SHIP from the reviewer but does NOT set the status itself. The caller (work skill or Ralph) sets `completion_review_status=ship` after successful review — and (when opted in) posts the verdict / R-ID-coverage comment to the linked tracker issue here. It does **NOT** flip the issue to `Done`/`verified` (fn-66: that is gated on a `MERGED` PR and driven solely by `land.merged`). The review skill (`flow-next-spec-completion-review`) is NOT edited; the touchpoint lives at this caller.

**Fix loop behavior**: Same as impl-review. If reviewer returns NEEDS_WORK:
1. Skill parses issues
2. Skill fixes code inline
3. Skill commits
4. Skill re-reviews (same chat for rp, same session for codex)
5. Repeat until SHIP

Only after SHIP does control return here. If skill outputs `<promise>RETRY</promise>`, there was a backend error - retry the skill invocation.

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

- Run relevant tests
- Run lint/format per repo
- If change is large/risky, run the quality_auditor agent:
 - Use the quality_auditor agent("Review recent changes")
- Fix critical issues

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

**Do NOT close the spec here** unless the user explicitly asked.
Ralph closes done specs at the end of the loop.

Then push + open PR if user wants.

**Tracker-sync end-of-run check — LAST action before the final summary.** Read-only audit: did every lifecycle touchpoint that triggered this run actually fire (receipt-backed)? It runs independently of the touchpoints, so a wholesale-skipped dispatch block is still caught. With no tracker configured, `sync check` exits silently in constant time — the summary slot then reads `n/a (bridge inactive)` and nothing else changes. Join first: before running this `sync check`, await any outstanding `tracker-runner` dispatches for this spec (join-before-audit, [`plugins/flow-next/references/tracker-dispatch.md`](../../references/tracker-dispatch.md)).

```bash
# Tasks worked this run = the task ids Phase 3 claimed/completed (you know these
# from the loop; substitute them).
WORKED="<task-id-1> <task-id-2> ..."

# --since: earliest claimed_at among tasks worked this run. On-disk anchor —
# bash vars do NOT survive across prompt turns; flowctl show re-derives it anytime.
SINCE=""
for T in $WORKED; do
 TS="$($FLOWCTL show "$T" --json | jq -r '.claimed_at // empty')"
 [ -n "$TS" ] && { [ -z "$SINCE" ] || [ "$TS" \< "$SINCE" ]; } && SINCE="$TS"
done

# --events: ONLY what actually triggered this run (triggered-set contract):
# ≥1 task claimed this run → include work.firstClaim
# ≥1 task reached done this run → include work.done
# completion review ran this run (3g) → include completionReview
# Configured-but-not-triggered events are never checked, never MISSING.
EVENTS="work.firstClaim,work.done" # ← substitute the actual triggered set

"$FLOWCTL" sync check "$SPEC_ID" --events "$EVENTS" --since "$SINCE" --json
# Empty output → bridge inactive → slot = `n/a (bridge inactive)`. Otherwise
# `.missing` empty → slot = `OK`; non-empty → retro-fire (below).
# Under Ralph (FLOW_RALPH=1 / REVIEW_RECEIPT_PATH set): route any echo of check
# output to stderr (>&2) — work's stdout stays clean for harness parsing.
```

(Nothing triggered at all — no claims, no dones, no 3g, e.g. a resumed no-op run — skip the check; the slot is vacuously `OK`.)

**Retro-fire on MISSING — exactly ONE cycle, never blocking:**

1. Record the retro-fire start anchor and echo it (the re-check needs it as `--since`): `date -u +%Y-%m-%dT%H:%M:%SZ`
2. For each MISSING event, invoke the **flow-next-tracker-sync skill directly** — the same dispatch as the touchpoint that missed, with its `event:` tag — NEVER this check block as a wrapper (no recursion):
 - `work.firstClaim` → `skill: flow-next-tracker-sync (operation: push <spec-id>, status-only, event: work.firstClaim)`
 - `work.done` → `skill: flow-next-tracker-sync (operation: comment <spec-id>, event: work.done)`
 - completion review → `skill: flow-next-tracker-sync (operation: comment <spec-id>, event: completionReview)` — comment-shaped (verdict + R-ID coverage as evidence), NEVER terminal (fn-66). Event key is the TOP-LEVEL `completionReview` (matches the `tracker.perEvent.completionReview` leaf — a `work.`-prefixed tag resolves no leaf and the audit can never clear or miss it)
3. Re-check the missed events only, `--since` = the step-1 anchor:
 `"$FLOWCTL" sync check "$SPEC_ID" --events "<missed-csv>" --since "<retro-fire-start>" --json`
4. Record the final state in the summary slot. Still MISSING after the one cycle is a recorded, visible outcome — never a second retro-fire, never a block (the work is already done; a tracker hiccup must not become a hard stop). Recovery guidance lives in the receipt note + `docs/tracker-sync.md`.

**Final summary (mandatory template).** End the run with this block. `Tracker sync:` is a REQUIRED field with exactly four states — an explicit `n/a` proves the check ran; an absent field is a skipped check. Under Ralph, the summary goes to the summary block / stderr, never stdout.

```
Spec: <spec-id> — <title>
Tasks: <n done>/<total>
Tests: <commands + result>
Review: <verdict | n/a>
Tracker sync: <OK | MISSING:<event> → retro-fired → OK | MISSING:<event> (retro-fire failed: <reason>) | n/a (bridge inactive)>
```

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
 ├─ 3a-c: find task → start → run worker agent
 ├─ 3d: verify done
 ├─ 3e: plan-sync (if enabled + downstream tasks exist)
 ├─ 3f: SPEC_MODE? → loop to 3a | SINGLE_TASK_MODE? → Phase 4
 ├─ no more tasks → 3g: check completion_review_status
 │ ├─ status != ship → invoke /flow-next:spec-completion-review → fix loop until SHIP → set status=ship
 │ └─ status = ship → Phase 4
 └─ Phase 4 (quality) → Phase 5 (ship: verify → commit → sync check → retro-fire MISSING once → summary w/ Tracker sync slot)
```
