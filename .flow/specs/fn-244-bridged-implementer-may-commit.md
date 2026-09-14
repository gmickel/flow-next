# Bridged implementer may commit checkpoints; timebox-free brief for long bridged tasks (#431)

## Conversation Evidence

Source: GitHub issue gmickel/flow-next#431 (reporter: DanielKillenberger), routed by the user through `/flow-next:flow`, plus one user answer in this session.

1. [issue] "The bridge recipe in `flowctl usage` ... says the bridged child never commits and the host keeps git. For a one-task spec implemented through a `codex exec` bridge, that rule leaves the host two bad options: one multi-hour run that ends in a single giant uncommitted diff, or host-inserted returns between the spec's steps so the host can commit checkpoints."
2. [issue] "Because the child may not commit, the host committed after each return. The first host session added a 'stop cleanly if you run out of room' line ... the implementer took that as licence to return partial after 30 to 45 minutes. Result: 19 dispatches for one task, each with a fresh context and a re-brief."
3. [issue] "with an in-host worker the worker commits per task and returns once; with a bridge the child cannot commit, so a long task either has no checkpoints or has host-inserted turns."
4. [issue] Option 1: "Let the bridged child commit checkpoints on its branch, with the host still owning review, `flowctl done`, push and any history rewrite. The safety rule could keep 'never push, never rebase, never decide scope, never issue a verdict' and drop 'never commit'. The host reviews the commit range on return, which is what the in-host worker path already does."
5. [issue] Option 2: "document the checkpoint pattern for long bridged tasks: one run per spec step or per commit-sized unit, host commits between, with a template brief that does not carry a timebox and says 'return only when this scope is done or blocked'."
6. [issue] Environment: "flow-next 5.2.1, Claude Code host, Codex CLI 0.153.4 as the bridge; implementer on the Codex bridge, reviewer host-native, `review.backend none`."
7. [user] "i feel like relax commit rule + brief template seems safe here right, any model is intelligent enough to do a commit."
8. [user] (selected option) Relax commit rule + brief template: let the bridged child commit checkpoints on its branch; keep never push / rebase / scope / verdict / nested bridge; host reviews the commit range on return; add the timebox-free brief template.

Strategic context (STRATEGY.md): approach "the artifact is the contract"; design principle "remember the bitter lesson: do not build scaffolding around a model's current weaknesses". Active tracks: Ralph autonomous mode (flow --auto + land), Cross-platform parity, Self-improving through normal work.

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 60% [paraphrase], 20% [user], 20% [inferred] -->

The headless bridge recipes (the `## Orchestration & model steering` section of the usage guide, mirrored into the orchestration guide and the site) carry a safety rule: the bridged child writes code, the host keeps git, judgment, and the verdict, and the child never commits. A user running a one-task `--no-plan` spec through a `codex exec` implementer hit the cost of that rule: with no checkpoints allowed, the host had to insert returns between the spec's steps and commit each one, and a timebox line added to make that possible taught the implementer to return partial. One task took 19 dispatches with a re-brief each time (evidence 1-3).

The in-host worker already commits per task and returns once, and the host reviews its commit range. A bridged child gains nothing from being forbidden to commit; the guard the rule actually needs is against push, history rewrite, scope drift, self-issued verdicts, and nested bridges. The maintainer's call (evidence 7-8): relax the commit clause, keep the rest, and document a brief shape for long bridged tasks that carries no timebox. This is a prose-only change to the bridge route, consistent with the recorded decision that bridge safety lives in prose rather than a hook.

## Architecture & Data Models
<!-- scope: technical -->

No code or config change. The deliverable is the revised bridge safety rule and a brief template, applied to every surface that currently states the rule: the usage guide template and its Codex mirror (kept identical by the sync script), the orchestration guide and its Codex mirror, the running-lean guide's pointer sentence, the repo's own instruction files' routing block, the changelog, and the site's work page, model-routing guide, cookbook entry, and landing-page card. Reach pages do not restate the rule and need no change unless a per-harness note about commit permission in a sandbox is warranted.

The rule's new shape: the bridged child writes code and may commit checkpoints on the branch the host names; the host keeps push, history rewrite, scope, review, verdict, task state, and `flowctl done`. On return the host reviews the child's commit range from the recorded base, exactly as it does for the in-host worker.

## API Contracts
<!-- scope: technical -->

Prose contract only. The brief template for a long bridged task states, at minimum: the branch to commit on and the commit convention; that the child commits a checkpoint per completed scope unit (a spec step or a commit-sized unit); that the child never pushes, never rebases or amends, never changes scope, never issues a verdict, never spawns a bridge; and the return condition "return only when this scope is done or blocked", with no timebox and no "stop cleanly if you run out of room" clause. The host's return handling names the base commit, the commit-range review, the gates, and the host-owned squash or rewrite decision.

## Edge Cases & Constraints
<!-- scope: technical -->

- A bridge invoked under a read-only or workspace-write sandbox that denies `git commit`: the brief's fallback is the one-run-per-scope-unit pattern with the host committing between runs; the child records that it could not commit in its digest rather than silently returning a dirty tree. [inferred]
- The child's commits are on the host-chosen branch only; any commit landing elsewhere is a host review finding on return. [inferred]
- The usage template and its Codex mirror must stay byte-identical; the sync script regenerates the mirror. [inferred]
- The recorded decision that bridge safety is prose-only stands: no hook, guard, or flowctl subcommand is added to enforce the new rule. [paraphrase]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The bridge safety rule in the usage guide (the `## Orchestration & model steering` section) and its Codex mirror reads: the bridged child writes code and may commit checkpoints on the branch the host names; the child never pushes, never rebases or rewrites history, never decides scope, never issues a review verdict, and never spawns a bridge of its own; the host keeps push, review, `flowctl done`, task state, and any history rewrite. Errors: no error surface beyond the template-mirror parity check. [user]
- **R2:** The same rule replaces every other copy that says the child never commits: the orchestration guide and its Codex mirror, the running-lean pointer sentence, and the repo's own instruction-file routing block. No surface in the plugin still states "never commits" for a bridged child. Errors: none beyond a grep for the old wording returning empty. [paraphrase]
- **R3:** The usage guide's bridge section states the host's on-return obligation: record the base commit before dispatch, review the child's commit range on return, run the gates on that diff, and decide squash or keep as the host. Errors: none. [paraphrase]
- **R4:** The usage guide carries a brief template for long bridged tasks: branch and commit convention, checkpoint unit (per spec step or commit-sized unit), the five never clauses from R1, and the return condition "return only when this scope is done or blocked", with an explicit note that a timebox or "stop cleanly if you run out of room" line invites partial returns and must not be included. Errors: none. [paraphrase]
- **R5:** The brief template names the fallback for a sandbox that denies commits: one run per scope unit with the host committing between runs, and the child reporting the denied commit in its digest. Errors: none. [inferred]
- **R6:** The changelog entry for this change credits the reporter of issue #431 and states the old rule, the new rule, and why. Errors: none. [inferred]
- **R7:** The flow-next.dev pages that restate the rule (work page, model-routing guide, cookbook entry, landing-page card) are updated to the new wording in the downstream release walk, and the issue receives a reply pointing at the shipped change. Errors: none. [inferred]

## Boundaries
<!-- scope: business -->

- No hook, guard, or flowctl subcommand enforces the new rule; bridge safety stays prose-only. [paraphrase]
- The child still never pushes, never rebases or amends, never decides scope, never issues a verdict, and never spawns a bridge. [user]
- No change to the in-host worker, `flowctl done`, review backends, or the thin-wrapper recipe beyond the sentence that names the rule. [inferred]
- No packaged delegation, no `work.delegate*` revival, no per-bridge config key. [inferred]

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation
<!-- scope: business -->

The commit prohibition protected against an unbounded second agent, but the bound that matters is push, rewrite, scope, and verdict; a local commit is reversible and reviewable. Forbidding it forced host-inserted turns and a timebox, which is scaffolding around a workflow gap rather than a capability gap, and the field report shows it multiplied dispatches nineteen-fold. Allowing checkpoint commits makes the bridge path match the in-host worker path the host already reviews. [paraphrase]

### Implementation Tradeoffs
<!-- scope: technical -->

Option 2 alone (document one-run-per-step, host commits between) was rejected as the primary shape because it keeps the re-brief cost that caused the report; it survives only as the sandbox fallback in R5. Adding a mechanical guard was rejected per the standing decision that prose-routed bridges have no hook-level git guard. [paraphrase]
