---
name: flow-next-work
description: Execute a flow-next spec or task end-to-end with worker subagents, gates, and commits. Use when asked to work on, implement, or execute fn-N.
user-invocable: false
---

# Flow work

Execute a plan systematically. Focus on finishing.

Follow this skill and linked workflows exactly. Deviations cause drift, bad gates, retries, and user frustration.

**`.flow/` is the only task tracker.** A run that recorded task state in a markdown TODO, a plan file, TodoWrite, or any other tracker has broken this — all task state is read and written via `flowctl`.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `phases.md`) use `$FLOWCTL`:

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

**Hard requirements (non-negotiable):**
- **Every completed task passes through `flowctl done` and a verified `done` status.** A task treated as finished while `flowctl show <task>` still reads `todo` or `in_progress` has broken this.
- **Staging is `git add -A`, never an explicit file list** — that is what pulls `.flow/` and `scripts/ralph/` (when present) into the commit. A commit whose diff omits the run's `.flow/` writes has broken this.
- **Completion is claimed only after `flowctl show <task>` reports `status: done`.** A completion claim printed ahead of that read has broken this.
- **`/flow-next:impl-review` is dispatched only on a green tree.** A review sent while tests or Quick commands are red has broken this.

**Role**: execution lead, plan fidelity first.
**Goal**: complete every task in order with tests.

## Ralph Mode Rules (always follow)

If `REVIEW_RECEIPT_PATH` is set or `FLOW_RALPH=1`, the Hard requirements above are
the receipt contract, plus:

- **The verified `done` status precedes the commit that carries the task.** A commit landing ahead of its verified `flowctl done` has broken this.
- **Tracking stays in `.flow/` via `flowctl` — TodoWrite is never the task record.** A Ralph iteration whose task list lives in TodoWrite has broken this.

Done when: the Hard requirements hold, and every completed task's `done` was verified before its commit.

## Autonomous Mode (questions off, no receipt obligations)

Before gates, treat this host-expanded block as literal prompt data, never shell:

<work-arguments>
$ARGUMENTS
</work-arguments>

Strip standalone whitespace token `mode:autonomous` into `WORK_ARGS`; preserve
all else verbatim (spaces/quotes/globs). Set/export `AUTONOMOUS=1` if found or
`FLOW_AUTONOMOUS=1`; otherwise set/export `AUTONOMOUS=0`.

Continue with `WORK_ARGS`; carry the exported marker into later shell fragments.
If `AUTONOMOUS=1`:

- **No setup question is asked** (branch + review questions below are suppressed). A run that puts either question to the user under `AUTONOMOUS=1` has broken this.
- **Branch defaults deterministically to `--branch=new`** when no explicit branch option is present — under autonomy "the user's answer" never exists, and defaulting to the current branch could commit straight to main. **Name the new branch exactly the spec's `branch_name` field** (`$FLOWCTL show <spec-id> --json | jq -r '.branch_name'`) — pilot's branch matrix, its all-done PR probe, and make-pr's branch-match spec detection all key on that name; an ad-hoc name breaks multi-tick continuity.
- **Review** = explicit `--review` passthrough if present, else the configured backend (`none` when `REVIEW_BACKEND` is `ASK`).
- **Autonomy ≠ Ralph.** Neither signal sets `FLOW_RALPH`, implies `REVIEW_RECEIPT_PATH` receipt obligations, or activates ralph-guard hooks. The Ralph rules above apply only under their own markers (the done/`git add -A`/no-TodoWrite discipline is universal anyway).
- **Never hang on a question.** A genuinely unanswerable ambiguity → stop cleanly with a one-line `NEEDS_HUMAN: <reason>` report instead of asking.

## Input

Full request after mode parsing: `$WORK_ARGS`

Accepts:
- Flow spec ID `fn-N-slug` (e.g., `fn-1-add-oauth`) or legacy `fn-N`/`fn-N-xxx` to work through all tasks
- Flow task ID `fn-N-slug.M` (e.g., `fn-1-add-oauth.2`) or legacy `fn-N.M`/`fn-N-xxx.M` to work on single task
- Markdown spec file path (creates spec from file, then executes)
- Idea text (creates minimal spec + single task, then executes)
- Chained instructions like "then review with /flow-next:impl-review"

Examples:
- `/flow-next:work fn-1-add-oauth`
- `/flow-next:work fn-1-add-oauth.3`
- `/flow-next:work fn-1` (legacy formats fn-1, fn-1-xxx still supported)
- `/flow-next:work docs/my-feature-spec.md`
- `/flow-next:work Add rate limiting`
- `/flow-next:work fn-1-add-oauth then review via /flow-next:impl-review`

If no input provided, ask for it.

## FIRST: Parse Options or Ask Questions

Check configured backend:
```bash
REVIEW_BACKEND=$($FLOWCTL review-backend)
```
Returns: `ASK` (not configured), or `rp`/`codex`/`copilot`/`cursor`/`host`/`none` (configured).

### Option Parsing (skip questions if found in arguments)

Parse `WORK_ARGS` for these patterns. If found, use them and skip corresponding questions:

**Branch mode**:
- `--branch=current` or `--current` or "current branch" or "stay on this branch" → current branch
- `--branch=new` or `--new-branch` or "new branch" or "create branch" → new branch
- `--branch=worktree` or `--worktree` or "isolated worktree" or "worktree" → isolated worktree

**Review mode**:
- `--review=codex` or "review with codex" or "codex review" or "use codex" → Codex CLI
- `--review=copilot` or "review with copilot" or "copilot review" → GitHub Copilot CLI
- `--review=cursor` or "review with cursor" or "cursor review" → Cursor CLI (`cursor-agent`)
- `--review=host` or "host review" or "host-native review" → host-native fresh-context reviewer subagent (cross-family pin from the AGENTS.md model-routing section)
- `--review=rp` or "review with rp" or "rp chat" or "repoprompt review" → RepoPrompt chat (via `flowctl rp chat-send`)
- `--review=none` or `--no-review` or "no review" or "skip review" → no review
- `--review=export` or "export review" or "external llm" → REFUSE at parse time, before any dispatch: export is not an impl-review backend — never fall through to the configured backend and never pass it as `REVIEW_MODE`; stop and point at `/flow-next:plan-review --review=export`, where export lives

(All non-`none` review modes route through `/flow-next:impl-review`, which resolves the
configured/overridden backend — codex, copilot, cursor, rp, or host — itself.)

**Autonomous mode**:
- `AUTONOMOUS=1` → suppress all setup questions; use the defaults above.

### If the options are absent from the arguments

**If `AUTONOMOUS=1` (autonomous mode):** ask nothing — apply the autonomous defaults and continue to the workflow.

**Otherwise (interactive)**: **the branch question is answered before anything else happens.** A run that reads a file or writes code before the answer arrives has broken this. Read
[references/setup-questions.md](references/setup-questions.md), ask the block it names for the
current `REVIEW_BACKEND` (branch-only when a backend is configured; branch AND review when
`REVIEW_BACKEND` is `ASK`), and wait for the response.

**Defaults when empty/ambiguous:**
- Branch = `new`
- Review = configured backend if set, else `none` (no auto-detect fallback)

Done when: the branch mode (and, under `REVIEW_BACKEND=ASK`, the review mode) is resolved from arguments, the user's answer, or the autonomous defaults — and no file has been read and no code written before that point.

## Workflow

After setup questions answered, read [phases.md](phases.md) and execute each phase in order.

**Worker agent model**: Each task is implemented by the `worker` agent role with fresh context. This prevents context bleed between tasks and keeps re-anchor info with the implementation. The main conversation owns the ready frontier: it prefers a concurrent wave when tasks are safely disjoint and the host can isolate and integrate them, otherwise it explains the sequential fallback. A parallel worker implements, tests, and commits in its isolated workspace, then returns task-unique handover files without completing shared Flow state. The conductor joins and integrates the whole wave before review, completion, tracker projection, plan-sync, or selecting the next frontier.

If user chose review, pass the review mode to the worker. The worker agent invokes `/flow-next:impl-review` after implementation and loops until SHIP.

**Completion review gate**: Default-on in SPEC_MODE when a review backend is configured. After all tasks are done, phases.md 3g invokes `/flow-next:spec-completion-review` — except it skips when the spec has exactly one task, that task's per-task impl-review reached SHIP (`REVIEW_MODE` was not `none`), and every spec R-ID is covered by that task's declared `satisfies`. On skip, persist `completion_review_status` `not_required` via the CAS setter (`--if-current unknown`) and record the Phase 5 stage line; a miss that reads `not_required` is an already-excused re-entry (same skip branch), while a verdict-status miss falls through to the normal status check without a skip line — policy outcome, never a SHIP. `flowctl next --require-completion-review` is a flowctl-level gate for driver loops; this skill does not read it. The spec-completion-review skill handles the fix loop internally until SHIP.

## Tracker sync (opt-in, off by default)

**The no-tracker path is the documented default and is behaviorally unchanged.** **A tracker touchpoint fires only when the bridge is active *and* its specific event is opted in** (the **shared gating predicate**); otherwise it is a silent no-op — no new steps, no new prerequisites. A run that adds a tracker step with the bridge inactive has broken this. The bridge is active iff `flowctl sync active --json` reports `active: true`. The touchpoint mechanics — the perEvent table, the shared gating predicate, and the three dispatch payloads (phases.md 3b.1 first-claim, 3d.1 done, 3g completion-review) — live in [references/tracker-touchpoints.md](references/tracker-touchpoints.md). **That reference is read only when a phases.md tracker gate prints its active read/execute/continue sentinel** (bridge active, or the gate's probe errored — fail open); a default bridge-inactive run that loaded it has broken this. Phase 5's end-of-run `sync check` + retro-fire + the mandatory four-state `Tracker sync:` summary slot stay inline in phases.md Phase 5 and run on every run (the slot reads `n/a (bridge inactive)` when no tracker is configured).

**Handle recognition (R16):** `/flow-next:work wor-17` / `work wor-17.1` resolve the existing linked spec/task — the Phase 1 input grammar routes any single-token arg through `flowctl show` (which resolves tracker handles via fn-52.10) before treating it as idea text, so a tracker key is never re-created as a new spec.

**Spec-id scheme on mint:** with a tracker configured, tracker-first is the recommended team default (`tracker.specIds=tracker`) — it stops parallel `fn-N` collisions. Gate: phases.md Phase 1.

**Unlink / re-link lifecycle:** documented with the touchpoints in [references/tracker-touchpoints.md](references/tracker-touchpoints.md) (`Unlink / re-link lifecycle`) — no work-run step.

## Guardrails

- **The branch question is answered before the run starts.** A run that began on an unresolved branch choice has broken this.
- **A plan or spec exists before implementation starts.** A run that began with no `.flow/` spec has broken this.
- **Tests run.** A task marked done with its spec's Quick commands unrun has broken this.
- **No task is left half-done.** A run that ends with a task still `in_progress` and no `NEEDS_HUMAN`/blocked report has broken this.
- **Task tracking lives in `.flow/` via `flowctl`.** A run tracking tasks in TodoWrite, or writing a plan file outside `.flow/`, has broken this.
