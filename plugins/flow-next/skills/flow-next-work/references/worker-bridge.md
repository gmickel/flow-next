# Worker Phase 1b: bridged implementer (gated reference)

> **Read by the worker only when its prompt's `IMPLEMENTER` line or the project routing block names an
> implementer model** (worker.md Phase 1b). A worker running on the session model, with no implementer
> named, never reads this file.

**Resolve the implementer tier before Phase 1.5** — routing precedence, highest first: the `IMPLEMENTER` line in your dispatch prompt (the conductor passes an explicit invocation or the judged mechanical tier; you have no other view of the invocation), then the project routing block in the instruction file, then the agent definition's own default, then the session model. How this harness reaches the named model lives in its reach page (`plugins/flow-next/docs/reach/`, or the generic page when the host is undetectable):

- **Session model, or an in-host subagent model** → this phase is inert and ends here. Continue with Phase 1.5; the standard phases run unchanged and the summary carries no `implement` stage line.
- **A model this harness reaches only by shelling out to another CLI** → this phase runs. You stay the task's worker (anchor, base commit, review dispatch, gates, evidence, `done`), and the bridged child becomes the task's owner: it reads the artifacts, implements, commits, and decides its own delegation.
- **A named model this harness cannot reach** → fall back to the session model, say so once, record `stage: implement - skipped(reach: <model> unreachable, session model used)` for Phase 5, and continue with Phase 1.5; this phase ends here.

Everything below in this phase, its Done-when included, binds only the bridged branch.

**Skip Phase 1.5 and every worker-side scout.** The child investigates and delegates for itself; a worker that read Investigation targets, ran the similar-code search, or dispatched scouts before the bridge has done the child's work twice.

**Compose the pointer prompt** — identities and rails only, never restated spec content (STRATEGY.md: the artifact is the contract):

1. `TASK_ID`, the spec path and the task path from the anchor bundle, the spec's `## Resolved via Research` section when the spec has one (named as a section to read, not pasted), the path of [defect-route.md](defect-route.md) when the task fixes a reported defect (named as a file to read before writing the fix), the path of [hill-climb.md](hill-climb.md) when the spec's goal is one metric moved toward a target through repeated attempts (named as a file to read before the first change), the path of [measured-numbers.md](../../../references/measured-numbers.md) when the acceptance is a measured slowness moved once (named as a file to read before measuring), and the project instruction file (`CLAUDE.md` / `AGENTS.md`).
2. The usage guide's long-task brief **verbatim** (`<FLOWCTL> usage`, `## Orchestration & model steering`, the `Branch: <branch>, already checked out...` block) with the branch filled in. The brief carries the judicious-subagent license, so the child holds the same delegation license as an in-host worker; when your own dispatch prompt carried a `Judicious subagent use` paragraph, append it verbatim after the brief as well — the license passes through to the owner, it is never held on the owner's behalf. Its commit clause names the owner as the only committer and defers the commit convention to the owner's path, so it agrees with the brief's checkpoint convention rather than contradicting it.
3. Nothing else. Your own `TIMEBOX` is never copied into the brief (a timebox teaches the child to return partial); no worker-side parallel bridge calls, no per-child worktrees, no branch integration in this phase — parallelization is the child's.

**Run the bridge as one foreground call** from the asserted repo root (`[ "$(git rev-parse --show-toplevel)" = "<repo-root>" ]` first, per the usage guide's recipe for that CLI), at the sandbox that permits `git commit` (on codex, `--sandbox danger-full-access` inside the asserted root), model and effort on the command line, digest captured to a file rather than scraped from stdout. Blocking, never `run_in_background` + a monitor. When the host's tool timeout is shorter than the task, the one foreground call is the usage guide's thin-wrapper recipe: a fast-tier wrapper subagent that runs the bridge in its foreground and returns only the digest, never changing the task, model, or verdict.

**On return:**

1. Commit any dirty remainder with the standard staging (`git add -- <changed files> .flow/ && git commit -m "<type>(<scope>): <what>"`) — this is the sandbox-denied-commit case the brief tells the child to report; a dirty tree never reaches range review.
2. Record `stage: implement - ran (model: <what ran>; delegated: <n>)` for Phase 5. `model:` is the model and effort you passed on the bridge command line (the effort from the `IMPLEMENTER` line's `at <effort>`, else the routing block's, else the level your `TIER_LINE` applied; a bridge that rejects the level runs once more at its default and the line says `effort <level> rejected, ran at default effort`; a bridge CLI with no effort setting runs without one and the line says `effort not applied (bridge takes no effort)`) — the command line is the record (nothing can strip it), and a child's self-report of its model is not evidence (reach page). `delegated:` is the number of subagents the child's digest reports; a digest without a count records `delegated: unknown`.
3. Review `$(cat .flow/tmp/base_commit)..HEAD` against every acceptance criterion the task names and against Phase 2's rules (no weakened tests or gates, no rename drift, no scope past the ACs, every enumerated error case tested), on a defect task against defect-route.md's steps and record, and on a hill-climb task against hill-climb.md's verify step. A gap against an AC is yours to close under Phase 2's rules before Phase 3; this is the worker's range check, not a review verdict — Phase 4 still owns that.
4. Run the focused Quick commands for the code under change, then continue at Phase 3 (the child's checkpoints stay; your Phase 3 commit covers what you added).

Under `PARALLEL_WAVE` or `host-deferred` review this phase changes only who wrote the code; the handover and deferral contracts in Phase 5 stand unchanged.

Done when (bridged branch only): the bridge run is recorded as an `implement` stage line, the child's range is committed, reviewed against the ACs, and gated, and no worker-side scouting, parallel bridge, or worktree ran.

## Rule

- **The owner holds the license** - on the Phase 1b bridged path the child owns delegation; a worker that fanned out bridge calls or worktrees on the child's behalf, or briefed the child with a never-list wider than the usage guide's, has broken this
