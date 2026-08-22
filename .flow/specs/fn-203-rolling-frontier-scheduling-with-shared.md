## Goal & Context

The 2026-08 wall-clock research pass (maintainer notes, Pass 2) located the remaining schedulable idle in the work pipeline in two places: the per-task review tail sits serial on the critical path, and the wave path is serial post-join - after a wave of workers returns, reviews run one at a time and the next wave dispatches only after every review, done, and plan-sync completes. A wave-granular overlap prototype (review(N) concurrent with implement(N+1), prose-only) measured an 11.2% work-phase wall saving at n=1 on a 3-task fixture - below the pre-registered 15% ship gate, but with confounds running against it and the minimum possible overlap surface: the saving accrues per task boundary, and a 3-task spec exposes only two.

This spec answers three questions with evidence before shipping anything:

1. **Rolling frontier:** does per-task admission (the conductor admits a new ready task the moment any in-flight task returns, instead of at wave boundaries) recover the wall-clock the barrier costs, at quality parity?
2. **Isolation model:** does workspace isolation still earn its keep under rolling admission, or does a single shared checkout - with commit discipline replacing worktree isolation - win by deleting the entire integration step?
3. **Shared notes surface:** exploration output reaches every workspace by pointer to an outside-tree notes directory instead of by embedded payload.

Phase A is a pre-registered three-arm eval. Phase B ships the winning architecture as a bounded beta work variant to gather field receipts on real specs. Phase C graduates the beta into the canonical work skill (or sunsets it) on a recorded decision. No permanent dual topology and no scheduling knob: evidence picks the architecture, the beta is the proving vehicle, and it terminates either way.

## Quick commands

```bash
# Focused suites for the surfaces this spec touches (work-skill prose + flowctl):
cd plugins/flow-next/tests && python3 -m unittest test_parallel_work_prose test_worker_anchor_prose test_cp1252_robustness -q
# Phase B flowctl mutex (only if arm 2 wins) adds its own focused test module to this list.
```

## Architecture & Data Models

**Admission rule (arm-neutral).** The existing wave dispatch rule, re-scoped from wave peers to the in-flight set: same spec; concurrency cap (<=3 in flight; see the capacity probe below); transitive dep-independence in both directions vs every in-flight task; declared `Touches:` pairwise disjoint vs every in-flight task (glob-aware); always-serial set untouched. Admission happens at every worker-return event. Any unmet condition holds the task; an empty admissible set with a non-empty frontier degrades to today's serial behavior and reports why. The fail-closed error paths are preserved verbatim: missing declaration, any intersection, any doubt - all hold.

**Arm 1 - rolling + isolated workspaces.** Each admitted worker runs in its own workspace. On worker return the conductor integrates that task's workspace into the conductor branch (reusing the existing wave-join evidence and SHA normalization), dispatches that task's review conductor-side, recomputes the frontier, and admits. A join conflict is a wrong dispatch surfacing structurally: one serial retry of that task, never a correctness loss.

**Arm 2 - rolling + shared checkout.** All admitted workers edit one checkout; there is no integration step. Isolation is replaced by two mechanical disciplines:

- **Staging-by-declaration:** a worker stages and commits only its own declared paths (`git add -- <its Touches>`), never a blanket add. The declaration becomes the literal commit boundary: an edit outside a worker's declaration never enters its commit and surfaces as a foreign dirty path - a detectable violation rather than a silent interleave.
- **Commit mutex:** commits are serialized through a lock so the shared index is never raced. Thin deterministic plumbing. **Phasing:** the Phase A prototype uses a branch-local lock script following flowctl's existing cross-process-lock pattern (never a shipped verb); the real flowctl verb is authored fresh in Phase B only if this arm wins, so canonical surfaces stay untouched during the eval.
- **Edit-state ledger:** each worker appends `writing: <paths>` to the shared notes surface when it starts mutating files and `settled: <paths>` when those files are self-consistent again (naturally at its commit points, since a worker verifies before committing). Prose protocol, agent-followed, no machinery.

Verify policy under arm 2: focused suites and typecheck may observe a sibling's in-progress edits through build-graph coupling that `Touches:` disjointness does not exclude (imports cross file boundaries). Two rules bound this. Before a focused verify, the worker consults the ledger and prefers a moment when implicated sibling paths are settled. And a red verify that implicates paths outside the worker's own declaration is not yet a failure: re-run after the implicated sibling settles, and only a red that survives the re-run counts. The second rule is load-bearing - it holds even when ledger discipline slips, degrading a missed ledger line to one re-run rather than a wrong escalation. The full suite runs only at quiesce (frontier and in-flight set both empty), unchanged from today's doctrine.

**Review topology (both rolling arms).** Conductor-owned review for every backend via the host-deferred handover shape: the worker implements, tests, commits, and returns a handover; the conductor dispatches review(N) while other workers run. Concurrent backend reviews use the thin-wrapper-subagent pattern. Reviewer identity, rubric, diff scope, SHIP-before-done gate, and fix-loop cap are all unchanged. done(N) fires only on SHIP(N); a NEEDS_WORK fix loop never blocks admission of others.

**plan-sync.** The fail-closed gate is preserved exactly: `planSync.enabled=true` disables concurrent admission entirely (serial, today's behavior). Rolling admission is active only when plan-sync is off (the default). No dependency-closure narrowing.

**Shared notes surface (all arms).** A per-run notes directory outside the mutable tree (sibling convention to the runtime state dir), keyed by spec id plus a run identifier so concurrent runs - other specs, or a beta and a canonical session on sibling worktrees sharing the same state root - never collide on one path. Created by the conductor at Phase 3 start, passed to every worker and scout by path in the dispatch prompt, and deleted by the conductor on clean run completion; a dir abandoned by an interrupted run is inert prose and may be removed by hand. Scouts and workers write markdown notes there (exploration findings, integration warnings for later tasks, and under arm 2 a live "working on <paths>" line per active worker); consumers read by pointer. Prose-routed convention only; no flowctl verb beyond the commit mutex above.

**Beta vehicle (Phase B).** The winning architecture ships as a separate user-invoked beta skill, explicitly marked experimental. It is a thin delta: its own SKILL.md plus one rolling-scheduler reference file; every other phase, reference, and agent contract is consumed from the canonical work skill's files by pointer, so a fix to canonical work applies to the beta without a second edit. The canonical work skill is not modified in Phase B. The beta carries a termination clause: it graduates (Phase C) or sunsets; it never becomes a standing second topology.

No new persisted schema. Field receipts for Phase C come from the existing receipt surfaces.

## API Contracts

flowctl gains exactly one mechanical surface, used only by the shared-checkout arm: a commit mutex (acquire, run, release around the worker's stage-and-commit). No other flowctl changes. When rolling admission is active, the Phase 3a report block gains three lines per admission event (exhaustive shape):

```text
In-flight: [fn-X.1 (review), fn-X.3 (impl)]
Admitted: [fn-X.4]
Held: [fn-X.5: Touches intersects fn-X.3]
```

The existing report lines (`Ready frontier`, `Isolation`, `Dispatch count`, `Sequential fallback`) are unchanged.

## Edge Cases & Constraints

- Worker return order is nondeterministic; admission is recomputed per event, never precomputed for the run.
- A stall-guard terminal (blocked-with-green-code) or a second consecutive worker failure frees the in-flight slot: the task leaves the set with its existing typed escalation and the loop continues. The run never wedges on one task.
- Claim-at-admission: a task is claimed when admitted; a failed claim drops it from the admissible set (existing semantics).
- Arm 1: fix commits from an open NEEDS_WORK loop land on the conductor branch while other workers hold older bases; workers reconcile at integration (existing wave mechanics).
- Arm 2 known hazards, instrumented not assumed away: blanket-add sweeps of sibling work, stale index locks, phantom-red focused verifies through build-graph coupling, and mid-edit states visible to sibling builds. Each is a counted incident class in the Phase A eval; the commit mutex and staging-by-declaration drive the first two to zero by construction, and the edit-state ledger plus the re-run-before-counting rule bound the last two to retries rather than wrong escalations. The counted phantom-red endpoint measures the residual after these disciplines, not the raw hazard.
- Arm 2: review diff scope per task = that task's commit range (attribution by construction from staging-by-declaration).
- The notes directory survives worker test-hygiene cleanup by construction (outside the mutable tree).
- The completion-review gate fires when frontier and in-flight set are both empty; only its timing shifts, never its semantics.
- Capacity probe: the <=3 cap is not a property of the isolation model; any cap change is measured, never assumed (see R1), and stays out of Phase B unless the measurement clears it.
- Cross-run claim contention: task claims live in the shared runtime state store and are spec-scoped, not skill-scoped, so a beta run and a canonical run on the same spec contend on the same claims and fail closed against each other by existing semantics - Phase B verifies this holds rather than assuming it.

## Acceptance Criteria

Phase A - proof (blocks everything below):

- **R1:** A pre-registered three-arm eval (endpoints and decision rule frozen before any draw; INCONCLUSIVE a first-class outcome) compares (a) the shipped wave scheduler, (b) rolling + isolated workspaces, and (c) rolling + shared checkout with commit mutex, staging-by-declaration, and the edit-state ledger (all three disciplines frozen in the pre-registration), on a wave-friendly fixture spec of >=5 tasks exposing >=4 admissible task boundaries - authored and frozen as part of the pre-registration if no suitable fixture exists - in paired same-machine draws, each draw in its own isolated checkout with its own runtime state dir (no shared claim or receipt state across draws), with reviewer, completion-review, and quality-audit surfaces byte-identical across arms, and with conductor and workers on the production default model configuration (opus-5 at medium effort) - identical across arms and draws, frozen in the pre-registration, never the planning session's escalation-tier model. Primary endpoint: quality parity (blind checklist scoring plus full deterministic suites, one scoring standard across arms; the scorer receives only the final integrated diff and suite results, with commit history and notes artifacts stripped so arm identity cannot leak through structurally distinctive artifacts). Secondary endpoints: work-phase wall-clock, and per-arm incident counts (lost or swept writes, commit-attribution violations, phantom-red focused verifies, join-conflict retries, index-lock stalls). Named secondary probe: at least one draw of the leading rolling arm at a cap above 3, reported but not gating. Ship gate per rolling arm: >=15% work-phase wall saving over the baseline arm at quality parity AND zero uncontained correctness incidents (a contained incident is one the arm's own mechanics detected and recovered; an uncontained one reached a commit, a verdict, or a receipt unnoticed). The study runs supervised under pre-registered token/wall budgets per draw and per arm and pre-registered abort rules: a draw is killed immediately on harness failure, wrong model or effort, runaway review churn, or budget exhaustion (a killed draw is invalidated, not scored); outcome-based early stopping happens only through a pre-registered futility rule, never ad-hoc judgment mid-study. Errors: harness contamination across paired draws invalidates the affected draw, not the study; any treatment-arm quality regression fails that arm regardless of wall saving; if both rolling arms pass, the arm with fewer incidents wins, wall-clock as tiebreaker.
- **R2:** The eval outcome (per-arm pass/fail/inconclusive and the winning architecture, if any) is recorded in the study changelog and appended to this spec's Decision Context before any Phase B task starts. If no arm passes, Phase B and C tasks are closed unimplemented with the result recorded and the spec closes as a completed negative result. No error surface beyond mis-sequencing, which this criterion exists to forbid.

Phase B - beta (gated on R1 pass and R2 record):

- **R3:** The winning architecture ships as a separate user-invoked beta work skill, marked experimental in its description, implemented as a thin delta: its own SKILL.md plus one scheduler reference file, with all other phases and references consumed from the canonical work skill by pointer. The canonical work skill's files are byte-unchanged in Phase B (scheduler content included). Errors: a canonical-work edit that the beta cannot consume by pointer is a blocking defect of the beta's structure, fixed there - never by forking the canonical file.
- **R4:** The beta admits tasks per worker-return event under the arm-neutral admission rule (five conditions vs the in-flight set, cap <=3) and emits the admission report lines; an empty admissible set degrades to serial dispatch with the reason reported. Errors: missing `Touches:` on any candidate holds it; any intersection or doubt holds it; `planSync.enabled=true` disables concurrent admission entirely (fail-closed).
- **R5:** Review runs conductor-side for every configured backend via the host-deferred handover shape; SHIP(N) gates done(N) per task; fix-loop cap and reviewer prompts byte-unchanged. Errors: a reviewer dispatch failure or stall-guard terminal frees the in-flight slot via the existing typed escalation and never blocks admission of other tasks.
- **R6:** Integration per the winning arm. Arm 1: per-task integration reuses the wave-join evidence and SHA normalization; a join conflict retries that task serially. Arm 2: workers stage and commit only their declared paths under the commit mutex, maintain the edit-state ledger, and apply the re-run-before-counting rule to red verifies implicating undeclared paths; a foreign dirty path or an edit outside the declaration at commit time is reported as a violation and the offending task goes serial. No error surface beyond those paths.
- **R7:** The conductor creates the outside-tree notes directory and passes its path in every worker and scout dispatch; skill prose directs consumers to read it by pointer and forbids embedding its content into dispatch prompts. Errors: directory creation failure degrades to a run without the notes surface (advisory, never blocking).
- **R8:** No change to review rubric, finding caps, completion-review charter, or quality-audit axes in any phase; this spec changes scheduling, isolation, and staging mechanics only. Verified on two pin surfaces: the prompt-pin suite stays green with no hash updates attributable to this spec, and in Phase B the prose-pin suites covering the canonical work skill stay green untouched (canonical files are byte-unchanged); Phase C's canonical scheduler replacement updates those prose pins deliberately in the same change. No error surface beyond those checks.
- **R9:** Docs updated (beta status, invocation, and the graduation plan stated), mirror regeneration run twice idempotently, prose growth justified per G1, test shape per G2; the commit mutex (if the shared-checkout arm won) lands with focused deterministic tests. Errors: a sync-guard failure is fixed in content or transform, never by relaxing the guard.

Phase C - graduation or sunset:

- **R10:** After a pre-declared field window (recorded in the spec before the beta ships: a minimum count of beta-run specs with receipts), a recorded decision either graduates the beta - its scheduler replaces canonical work Phase 3 in one change and the beta skill is deleted in the same change - or sunsets it, deleting the beta skill and recording why. Errors: the beta persisting past a decided graduation or sunset is a defect; there is no third outcome in which both topologies remain.

## Early proof point

Task fn-203-rolling-frontier-scheduling-with-shared.3 validates the core approach (a rolling arm clears the >=15% wall gate at quality parity with zero uncontained incidents). If it fails, the spec closes as a completed negative result per R2 - Phase B and C tasks are never implemented.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Pre-registered three-arm eval | .1, .2, .3 | - |
| R2 | Outcome recorded before Phase B | .3 | - |
| R3 | Beta skill as thin delta | .4 | - |
| R4 | Rolling admission rule + report lines | .4 | - |
| R5 | Conductor-owned review, SHIP gates done | .4 | - |
| R6 | Integration per winning arm (join reuse / mutex + staging-by-declaration) | .4 | Arm 1 won (fn-203.3, 2026-08-22); .5 (commit-mutex verb) closes unimplemented, arm-2-only. R6 coverage is .4 alone (join-reuse integration). |
| R7 | Outside-tree notes surface | .4 | - |
| R8 | Review surfaces untouched, pin suites green | .6 | - |
| R9 | Docs, mirror, G1/G2, mutex tests | .6 | - |
| R10 | Graduation or sunset | .7 | - |

## Boundaries

Out of scope:

- Live inter-worker negotiation: workers reading each other's intents from the notes surface and resolving overlap conflicts among themselves at edit time. The notes surface carries advisory "working on" lines under arm 2, but admission remains the conductor's fail-closed decision; worker-negotiated admission would supersede the declared-intent doctrine and needs its own decision record.
- Autonomous conflict resolution at join (an agent resolving arm-1 integration conflicts in place of the serial retry). The retry stays.
- Any scheduling or isolation configuration knob in the canonical work skill (no rolling switch, no isolation option). The beta is the only second surface, and R10 terminates it.
- Raising the concurrency cap in Phase B. The R1 capacity probe informs a future decision; it does not license one here.
- Review rubric, finding caps, churn handling, or completion-review redesign - separately adjudicated, untouched here.
- flowctl scheduling machinery: scheduling stays skill prose; flowctl gains only the commit mutex, and only if the shared-checkout arm wins.
- Pilot and land changes beyond consuming the existing report lines. In particular, pilot and land never dispatch the beta: the pipeline stays on canonical flow-next-work, and the beta is user-invoked only for its entire life.
- Ralph support for the beta: the deprecated Ralph harness is not taught the beta's dispatch shape; Ralph installs keep using canonical work.

## Strategy Alignment

Active tracks served by this plan:
- **Ralph autonomous mode** (the loop-suite track) - shrinks work-phase wall-clock on the pilot+land assembly line by removing the wave barrier's schedulable idle, with the quality-discipline invariants (multi-model review at every handover, evidence over narration) explicitly pinned untouched.
- **Self-improving through normal work** - Phase C's graduation decision is driven by field receipts generated as a side-effect of normal beta runs, not by a manual ceremony.

## Decision Context

**R2 record - Phase A eval outcome (2026-08-22, study `rolling-frontier-2026-08`, verdict entry `9635d29`).**
Per-arm: **A0 baseline** wall 129.1 min, checklist 37/42. **A1 rolling+isolated: PASS** - wall
61.9 min (52.1% saving, decisive band, no replication owed), checklist 37/42 (parity), zero
uncontained correctness incidents (maintainer-ratified reading of the class-2 clause: task-own
undeclared co-located files with zero sibling contact are declaration-incompleteness, not
incidents). **A2 rolling+shared: FAIL** - quality regression (33/42 vs baseline 37/42; hard
rule, its 69.2% wall saving moot). **Winning architecture: A1 - rolling frontier + isolated
workspaces.** Phase B builds the beta on rolling admission + per-task worktree integration;
the flowctl commit-mutex (task .5) is closed unimplemented (arm-2-only). A2 post-mortem
(recorded in the study changelog): its speed was partly bought with ~30% thinner test
artifacts; leading hypothesis - A1's per-task integration step doubles as a conductor quality
pass, and deleting it deleted real quality attention. Two draws were invalidated for
infrastructure (529 storm; print-mode wave incapability) and two for shared-state
contamination before the valid sequential runs; full ledger in the study changelog.

**R10 field window (recorded 2026-08-22, task .6).** The Phase C
graduation-or-sunset decision fires after a minimum of **5 beta-run specs with
receipts**: real (non-fixture) specs driven end-to-end by
`/flow-next:work-rolling` whose review/done receipts exist on the standard
surfaces. A run that degraded to fully serial admission for its whole life
(never more than one task in flight - e.g. `planSync.enabled=true` or a
perpetually held frontier) does not count toward the window, since it exercises
none of the scheduler. Recording note: R10 asks for this window before the beta
ships; the beta shipped in task .4 with the window unrecorded (pre-existing gap
flagged by .4's reviewer) - it is recorded here, in the first task to land
after the flag, and applies from this record forward.


Eval-first because the last review-architecture redesign looked dominant on paper and was falsified only by its pre-registered eval; the standing decision is no conditional machinery - evidence picks the architecture. Per-task granularity over wave-granular overlap because the measured saving accrues per task boundary (the n=1 measurement ran on the minimum surface) and the wave path is verified serial post-join, so the barrier itself is schedulable idle that wave-granular overlap cannot recover.

The shared-checkout arm is included because it deletes the entire integration step (no join, no SHA normalization, no conflict-retry path, fresh bases by construction) and because its two classic failure modes have mechanical answers: staging-by-declaration turns the Touches declaration into the literal commit boundary - putting the invariant where it is true by construction instead of enumerating misbehaviors - and the commit mutex serializes the shared index. It is an arm rather than the default because the third thing isolation buys, verify soundness, is only mitigated, not eliminated: declaration disjointness does not imply build-graph disjointness, so focused verifies can observe a sibling's in-progress edits, and previously observed shared-checkout failure modes (blanket-add sweeps, stale index locks) are documented field pain. The mitigation is deliberately prose-shaped - the edit-state ledger orders verifies around sibling write windows, and the re-run-before-counting rule converts the residual from wrong escalations into single retries, so a slipped ledger line costs latency, never correctness; the final artifact was never at risk because the full suite at quiesce is the actual gate. Whether the residual retry rate is acceptable is an empirical question, which is why phantom-reds are a counted incident class and the zero-uncontained-incidents clause in R1's ship gate keeps a fast-but-leaky arm from winning.

The beta-skill vehicle exists because paired lab draws alone are a thin evidence base and this project's record repeatedly trusts field receipts over small-n lab numbers; the beta generates them on real specs without touching the canonical skill. It is compatible with the no-dual-topology decision only because R3 bounds its structure (thin delta, canonical files byte-unchanged) and R10 bounds its lifetime (graduate or sunset, never both surfaces indefinitely).

The plan-sync fail-closed gate survives untouched because dependency-closure narrowing was falsified against real receipts: actual plan-sync edits target dep-independent siblings, so no dependency-based narrowing of the overlap gate is sound. The notes surface lives outside the mutable tree because both failure modes of the alternatives are measured: shared runtime state through the repository common dir contaminates sibling agents, and in-workspace state is destroyed by worker test hygiene. Rejected: an in-repo committed notes directory (commit churn; isolated workers cannot see uncommitted siblings), a flowctl notes verb (a pointer convention needs no plumbing), and shipping either rolling arm straight into canonical work (unproven scheduler in the highest-traffic skill; the beta exists to price that risk with receipts first).
