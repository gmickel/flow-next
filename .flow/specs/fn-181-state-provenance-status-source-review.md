# Overview

Two instances of one failure class from issues #304 and #307 (sn-furali 2026-08-08 batch): a flowctl read surface confidently answers from a source the caller has no reason to distrust - the committed task-status fallback when runtime state is absent, and per-worktree committed spec state that can be arbitrarily stale versus the shared task store. #304 has cost three review rounds across two review kinds, including a NEEDS_WORK at confidence 100 on a 3/3-done spec.

**Evidence standing: reporter-measured occurrences (three review rounds; a cleared dep edge invisible in a stale checkout); code paths confirmed unchanged on main. No new evals.**

## Goal & Context

Wrong answers become marked answers: status output carries its provenance, review skills stop judging task lifecycle from committed sidecars, and the pre-work commands note when the checkout is behind upstream. Advisory only - never fetch, never block.

## Architecture & Data Models

1. **Status provenance (#304 half 1):** `flowctl show` / `list` `--json` gain `status_source: "flow-state" | "committed"`; plain output prints one advisory line when the runtime directory is absent. The merge code already knows which store answered; this is a field, not a behavior change.
2. **Review-skill prose (#304 half 2, the load-bearing half):** plan-review and completion-review skill text states that committed `.flow/tasks/<id>.json` `status` is not authoritative, that task lifecycle state lives in git-common-dir flow-state (unreachable from a diff-scoped sandbox), and that task lifecycle is not the reviewer's to judge - completion review is spec compliance only. A provenance marker on an API the reviewer bypasses is invisible; the prose is what closes the recurrence.
3. **Staleness advisory (#307, RESCOPED from the issue's ask):** `ready` (and `anchor`) - NOT `list`/`status`/`next` - emit one advisory line / `stale_vs_upstream` JSON field when HEAD is behind its upstream: `note: checkout is N commits behind origin/main; spec-level state may be stale`. One check per invocation, never per task; skip instantly when no upstream is configured. Rationale: `list`/`status` are the high-frequency polls fn-109 made 60x faster; a git spawn there regresses that win, while `ready`/`anchor` are the ask-before-work commands where the issue's own value argument lives.

## Edge Cases & Constraints

- Detached HEAD, no upstream, offline: advisory silently absent; command behavior otherwise unchanged.
- The advisory never fetches and never blocks; a stale checkout still gets its computed answer, now qualified.
- Skill-prose additions are one to two sentences per skill (fn-82 token budget respected; the saved review rounds dwarf the cost).
- Prose changes ride sync-codex twice + mirror commit; flowctl changes ride dual-copy propagation.
- Not the tracker local-authority rule: `_resolve_dep_link()` deliberately never consults the remote tracker; this spec touches only the git-checkout axis.

## Acceptance Criteria

- **R1:** `show`/`list` `--json` carry `status_source`; plain output prints one advisory line when flow-state is absent. Errors: none; field always present under --json.
- **R2:** Plan-review and completion-review prose forbid establishing task lifecycle from committed sidecars and name the authoritative source. The #304 occurrence-3 shape (reviewer reads sidecar, flow-state says done) is addressed by prose a reviewer following the skill cannot miss.
- **R3:** `ready` and `anchor` emit the behind-upstream advisory (plain + `--json` field) when an upstream exists and HEAD is behind; silent otherwise. Errors: any git failure in the check degrades to no advisory, never to a command failure.
- **R4:** `list`, `status`, and `next` gain NO upstream check; their git-spawn count is unchanged (assert in tests or by inspection note). Errors: none.
- **R5:** At most one upstream check per invocation regardless of spec/task count.
- **R6:** Mirrors, dual copies, docs (flowctl.md for the new field/advisory), CHANGELOG Unreleased crediting @sn-furali. Errors: parity red blocks merge.

## Boundaries

- Never fetch, never block, no freshness enforcement, no new commands.
- No change to where state lives (committed vs git-local placement stays as designed).
- No keeping committed status current (explicitly not requested in #304; writing runtime state into the tree is the thing the placement avoids).
- Version bump deferred to the batched release.

## Decision Context

The #307 rescope (ready/anchor only) is a deliberate narrowing of the reporter's list and is being stated on the issue with reasoning: the issue asked for the advisory on five commands; putting it on the two pre-work commands preserves the entire value case (a wrong answer before starting work is maximally expensive) while keeping the fn-109 hot-path wins intact. R4 exists so the narrowing survives delegation. #304's two halves are ordered deliberately: the API marker alone was shown insufficient by occurrence 3, where the authoritative API was available and simply not asked.
