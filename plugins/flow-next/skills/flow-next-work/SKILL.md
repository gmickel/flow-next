---
name: flow-next-work
description: Execute a Flow spec or task systematically with git setup, task tracking, quality checks, and commit workflow. Use when implementing a plan or working through a spec. Triggers on /flow-next:work with Flow IDs (fn-1-add-oauth, fn-1-add-oauth.2, or legacy fn-1, fn-1.2, fn-1-xxx, fn-1-xxx.2).
user-invocable: false
---

# Flow work

Execute a plan systematically. Focus on finishing.

Follow this skill and linked workflows exactly. Deviations cause drift, bad gates, retries, and user frustration.

**IMPORTANT**: This plugin uses `.flow/` for ALL task tracking. Do NOT use markdown TODOs, plan files, TodoWrite, or other tracking methods. All task state must be read and written via `flowctl`.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `phases.md`) use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

**Hard requirements (non-negotiable):**
- You MUST run `flowctl done` for each completed task and verify the task status is `done`.
- You MUST stage with `git add -A` (never list files). This ensures `.flow/` and `scripts/ralph/` (if present) are included.
- Do NOT claim completion until `flowctl show <task>` reports `status: done`.
- Do NOT invoke `/flow-next:impl-review` until tests/Quick commands are green.

**Role**: execution lead, plan fidelity first.
**Goal**: complete every task in order with tests.

## Ralph Mode Rules (always follow)

If `REVIEW_RECEIPT_PATH` is set or `FLOW_RALPH=1`:
- **Must** use `flowctl done` and verify task status is `done` before committing.
- **Must** stage with `git add -A` (never list files).
- **Do NOT** use TodoWrite for tracking.

## Input

Full request: $ARGUMENTS

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
Returns: `ASK` (not configured), or `rp`/`codex`/`none` (configured).

### Option Parsing (skip questions if found in arguments)

Parse the arguments for these patterns. If found, use them and skip corresponding questions:

**Branch mode**:
- `--branch=current` or `--current` or "current branch" or "stay on this branch" → current branch
- `--branch=new` or `--new-branch` or "new branch" or "create branch" → new branch
- `--branch=worktree` or `--worktree` or "isolated worktree" or "worktree" → isolated worktree

**Review mode**:
- `--review=codex` or "review with codex" or "codex review" or "use codex" → Codex CLI (GPT 5.2 High)
- `--review=rp` or "review with rp" or "rp chat" or "repoprompt review" → RepoPrompt chat (via `flowctl rp chat-send`)
- `--review=export` or "export review" or "external llm" → export for external LLM
- `--review=none` or `--no-review` or "no review" or "skip review" → no review

### If options NOT found in arguments

**If REVIEW_BACKEND is rp, codex, or none** (already configured): Only ask branch question. Show override hint:

```
Quick setup: Where to work?
a) Current branch  b) New branch  c) Isolated worktree

(Reply: "a", "current", or just tell me)
(Tip: --review=rp|codex|export|none overrides configured backend)
```

**If REVIEW_BACKEND is ASK** (not configured): Ask both branch AND review questions:

```
Quick setup before starting:

1. **Branch** — Where to work?
   a) Current branch
   b) New branch
   c) Isolated worktree

2. **Review** — Run Carmack-level review after?
   a) Codex CLI
   b) RepoPrompt
   c) Export for external LLM
   d) None (configure later with --review flag)

(Reply: "1a 2a", "current branch, codex", or just tell me naturally)
```

Wait for response. Parse naturally — user may reply terse or ramble via voice.

**Defaults when empty/ambiguous:**
- Branch = `new`
- Review = configured backend if set, else `none` (no auto-detect fallback)

**Do NOT read files or write code until user responds.**

## Workflow

After setup questions answered, read [phases.md](phases.md) and execute each phase in order.

**Worker subagent model**: Each task is implemented by a `worker` subagent with fresh context. This prevents context bleed between tasks and keeps re-anchor info with the implementation. The main conversation handles task selection and looping; worker handles implementation, commits, and reviews.

If user chose review, pass the review mode to the worker. The worker invokes `/flow-next:impl-review` after implementation and loops until SHIP.

**Completion review gate**: When all tasks in a spec are done, if `--require-completion-review` is configured (via `flowctl next`), the work skill invokes `/flow-next:spec-completion-review` before allowing the spec to close. This verifies the combined implementation satisfies the spec. The spec-completion-review skill handles the fix loop internally until SHIP.

## Tracker sync (opt-in, off by default)

**The no-tracker path is the documented default and is behaviorally unchanged.** Every tracker touchpoint below runs ONLY when the bridge is **active** AND the specific event is opted in; otherwise it is a silent no-op (no new steps, no new prerequisites). The bridge is active iff `flowctl sync active --json` reports `active: true` (the single value-checked predicate from fn-52.1: raw `tracker.enabled == true` OR raw `tracker.type ∈ {linear,github}` — NOT merely that a `tracker` block exists, and NOT a stray `type:null`). Each event then reads its own nested `perEvent` leaf (all default `off`):

| Lifecycle event | perEvent key | Effect when opted in |
|---|---|---|
| first task claimed (phases.md 3b.1) | `tracker.perEvent.work.firstClaim` | move the linked issue In-Progress |
| task done (phases.md 3d.1) | `tracker.perEvent.work.done` | post a status comment + evidence (tests / commits / PR) |
| spec-completion-review SHIP (phases.md 3g) | `tracker.perEvent.completionReview` | flip the issue Done/verified + post verdict / R-ID coverage |

(capture / interview / plan / make-pr / resolve-pr carry their own touchpoints in those skills, gated identically on `tracker.perEvent.{capture,interview,plan,makePr,resolvePr}`.)

**Shared gating predicate** — every touchpoint uses this exact shape (active AND leaf ≠ off/null):

```bash
LEAF="$($FLOWCTL config get tracker.perEvent.<key> --json | jq -r '.value')"
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
   && [ "$LEAF" != "off" ] && [ "$LEAF" != "null" ]; then
  # invoke the flow-next-tracker-sync skill (operation per the leaf / event)
  :
fi
```

The actual tracker work (transport, body merge, status who-wins, comment dedup, receipts) lives entirely in the **`flow-next-tracker-sync` skill** — the lifecycle skills only gate + delegate. Every touchpoint is **best-effort**: a tracker failure (no transport reachable, 404 issue, etc.) never blocks the lifecycle; the tracker-sync skill emits its own `sync receipt` and, under Ralph, queues genuine conflicts (`sync defer`) instead of asking. A spec with **no linked tracker id** is **flow-first-pushed (issue created + linked) on the first touchpoint that fires**, then reconciled by later ones (tracker-sync §Phase 3 "create-if-unlinked") — an active bridge keeps in-flow-authored specs in sync rather than leaving them untracked. A touchpoint only no-ops when no transport is reachable.

**Handle recognition (R16):** `/flow-next:work wor-17` / `work wor-17.1` resolve the existing linked spec/task — the Phase 1 input grammar routes any single-token arg through `flowctl show` (which resolves tracker handles via fn-52.10) before treating it as idea text, so a tracker key is never re-created as a new spec.

**Unlink / re-link lifecycle:** detaching a spec from its tracker issue is done via `/flow-next:tracker-sync unlink <id>` — that ceremony (in the tracker-sync skill) clears the tracker id + `lastSyncedAt` + merge-base atomically (`flowctl sync clear`) and posts a one-line "detached" comment to the issue. After unlink, all lifecycle touchpoints above no-op for that spec (no linked id). A later re-link re-seeds the merge base from the current issue body (so re-link does not resurrect stale state). The spec/task ids, branch, and files are NEVER touched by unlink (no rename).

## Codex implementation-delegation (opt-in, off by default)

**The in-session path is the documented default and is behaviorally unchanged.**
With delegation off — the default — the work flow adds exactly ONE cheap
value-check and nothing else; `/flow-next:work` stays byte-identical to today.
All delegation mechanics live in [references/codex-delegation.md](references/codex-delegation.md),
read **only when delegation is active** (progressive disclosure, R3).

**Activation is disambiguated from the review backend.** `/flow-next:work`
already maps the generic fuzzy "use codex" to the **review backend** (Review-mode
parsing above). Delegation activates ONLY via the explicit arg token
`delegate:codex` (off-switch `delegate:local`), the flow config
`work.delegate=codex`, or an unambiguous "use codex **for implementation**" /
"delegate implementation to codex" — **never** bare "use codex".

**Resolution chain (precedence):** arg token (`delegate:codex` / `delegate:local`)
> flow config `work.delegate` > hard default OFF. The single value-check
computes `delegation_active` ONCE, before the per-task loop:

```bash
# Default-path bloat = this one value-check. Nothing else runs when off.
# Cheap host short-circuit FIRST — delegation is Claude-Code-only. On a non-Claude
# orchestrator (Codex / Droid / OpenCode) delegation_active is FALSE here, so the
# ~45k references/codex-delegation.md is NEVER read into context just to be
# disabled by Gate 1 (which stays the authoritative full platform check).
host_is_claude_code() {
  [ -n "${CLAUDECODE:-}" ] || return 1        # not Claude Code → off
  [ -z "${DROID_PLUGIN_ROOT:-}" ] || return 1 # Droid → off (compat alias not keyed)
  [ -z "${OPENCODE:-}" ] || return 1          # OpenCode → off
  return 0
}
# Guard a missing .flow/ (fresh repo / idea or markdown input, not yet `flowctl
# init`ed) — `config get` errors on an absent .flow/; treat it as delegation OFF.
if [ -d .flow ]; then
  DELEGATE_CFG="$($FLOWCTL config get work.delegate --json | jq -r '.value')"
else
  DELEGATE_CFG=false
fi
# delegation_active = host_is_claude_code && (arg delegate:codex | DELEGATE_CFG == "codex") && not arg delegate:local
# if delegation_active → read references/codex-delegation.md and run the host
#   pre-flight gates + one-time consent ONCE, before the loop (phases.md Phase 1.5).
# else → standard in-session execution, unchanged, zero new steps (non-Claude host
#   short-circuits here — the reference is never read).
```

When `delegation_active`, the host (NOT the worker subagent) reads
[references/codex-delegation.md](references/codex-delegation.md) and runs its
pre-flight gates + one-time consent once, then passes the resolved flags into
each spawned worker. Any gate failure (non-Claude-Code platform, inside a Codex
sandbox, `codex` missing, no consent, bare-prompt input, dirty tree) → standard
mode for the rest of the run; delegation never blocks the worker.

## Guardrails

- Don't start without asking branch question
- Don't start without plan/spec
- Don't skip tests
- Don't leave tasks half-done
- Never use TodoWrite for task tracking
- Never create plan files outside `.flow/`
