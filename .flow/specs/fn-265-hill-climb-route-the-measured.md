# Hill-climb route: the measured improvement loop

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 10% [user], 50% [paraphrase], 40% [inferred] -->

`/flow-next:flow` already routes "one metric to improve against a target through repeated attempts" to a hill-climb route, and the docs draw it as a loop: a frozen harness, one change and one measurement per attempt, keep or revert, repeated inside work until the target is met. The judge classifies specs onto that route today. Nothing runs the loop. A hill-climb spec is executed like any other spec: one task, one baseline, one change, done. There is no attempt ledger, no revert discipline, and no rule for when a measured difference is real rather than noise.

This spec builds the loop the route promises, as a first-class part of `/flow-next:work`. The maintainer wants flow to be as capable as possible and asked for this route to be done properly, with full prose examples. The design follows the same discipline the maintainer's own evaluation work uses: fix the endpoint before any attempt, prove the instrument can tell better from worse, screen then replicate, publish every attempt including the ones that went the wrong way, and treat "inside the noise" as no result.

Target user: an engineer (or an unattended `flow --auto` run) who wants a number moved, such as a CLI's cold-start time, a test suite's wall time, a page's time to interactive, or a build's size, and has a command that measures it.

## Architecture & Data Models
<!-- scope: technical -->

- **Where it runs.** The loop lives inside work's direct route, within the one implicit task work mints for the spec. Work loads the loop's instructions when the spec's recorded route is hill-climb. The rolling scheduler does not apply: attempts are serial by nature. Review runs once over the kept commits at the end. make-pr renders the result through its existing proof cells. [paraphrase]
- **Pre-registration (in the spec).** Before any attempt, the spec states the metric and which direction is better, the target, a minimum attempt count, an attempt or time budget, the harness command, the number of runs per measurement, and the minimum detectable effect. The human owns the target, the attempt floor and the budget; the agent may propose them during capture or refine. [inferred]
- **Harness proof, then freeze.** The harness must rank a known-worse variant, the baseline and a known-better variant in the right order, with gaps larger than the measured spread, before it is trusted. The harness also checks the output is correct (exit status plus an output check), so a change that skips the work cannot score. Freezing records the harness command and its inputs with a content hash; changing either invalidates earlier measurements and forces a new baseline. [inferred]
- **Noise control.** Warm-up runs are discarded. Baseline and candidate runs are interleaved so drift hits both. Each side reports its median and spread over N runs. The minimum detectable effect is the larger of the user's floor and about twice the baseline spread. [inferred]
- **Keep rule.** A candidate is kept only when its median beats the current best by at least the minimum detectable effect, its range does not overlap the best's, one fresh replicate confirms it, and the spec's regression gate (its Quick commands) is green. Anything else is inconclusive or worse, and inconclusive counts as a revert. [inferred]
- **Attempt ledger.** One row per attempt, written whatever the outcome, in a gitignored run directory beside the other per-run records: attempt number, hypothesis family, the specific mechanism hypothesised, the change, before and after (median and spread), delta, gate result, verdict (kept, reverted, inconclusive), the reason, and the commit when kept. The agent reads the ledger before each attempt so a refuted idea is not retried. A summary of the ledger goes into the task's done evidence. [inferred]
- **Keep or revert.** One hypothesis per attempt. A kept attempt is exactly one commit that stages only the files it touched. A rejected attempt is fully reverted before the next begins. Changes are never stacked unmeasured. A win that breaks behaviour is reverted. A simplification that holds the number may be kept. [inferred]
- **Hypothesis families.** An attempt draws from a named family, and a family earns an attempt only when a profile or trace shows its signal: delete work nobody consumes; defer work off the measured path; reuse results for identical inputs (and name what invalidates them); coalesce many small calls that each pay a fixed overhead; shrink the input the cost scales with; parallelise independent units onto idle cores; switch to a cheaper representation or algorithm; move work nobody waits for off the waited path; lighten heavy dependencies that dominate startup; tune the environment (interpreter flags, caches, pools). [inferred]
- **Stop rules.** Stop when the target is met and the attempt floor is reached (one lucky early win does not end the run); when the budget is spent; when every family the profile supports has been tried; or at once when the harness breaks. A plateau (for example three reverts in a row) is not a stop: it changes hypothesis family, combines near misses, or re-profiles, and the pivot is recorded in the ledger. [inferred]
- **Knowledge that outlives the run.** A mechanism that proved out (or proved useless) is offered to the memory knowledge track, so the next climb on the same codebase starts from it. [inferred]

### Worked example

A spec asks to cut `mycli --version` cold start below 120 ms, with at least 6 attempts, a 20-attempt budget, and 15 runs per measurement.

The agent measures the baseline after 3 discarded warm-ups: median 410 ms, spread 395 to 430 ms. To prove the harness, it injects a 40 ms sleep (reads 450 ms) and a throwaway change that skips plugin discovery (reads 250 ms). The order is right and the gaps exceed the 35 ms spread, so the harness is frozen with its hash, the minimum detectable effect is set to 30 ms, and the unit suite is confirmed green as the regression gate.

Attempt 1, family defer: an import profile shows the HTTP client and the YAML parser load at startup but only two subcommands use them. Moving those imports inside the subcommands reads 290 ms (spread 280 to 300 ms). It clears the bar, a replicate reads 292 ms, the gate is green, and it is kept as one commit.

Attempt 2, family reuse: caching the plugin registry to disk reads 284 ms against the best of 290 ms. That is inside the noise, and the cache adds invalidation logic. Verdict inconclusive, reverted, reason logged. Attempts 3 and 4 try two more reuse ideas and are also reverted. Three reverts in a row is a plateau, so the agent re-profiles instead of stopping.

The new profile shows 150 ms spent scanning package entry points. Attempt 5, family lighter dependencies: switching to a metadata lookup filtered to one entry-point group reads 160 ms. Kept. Attempt 6, family delete: removing an unused startup telemetry probe reads 112 ms. Kept.

The target is met and six attempts have run, so the loop stops. The PR shows 410 ms to 112 ms (a 73% reduction), 6 attempts with 3 kept and 3 reverted, the three kept commits in order, the harness proof, the green gate on the final head, and the best idea not yet tried.

## Edge Cases & Constraints
<!-- scope: technical -->

- A spec on the hill-climb route that lacks any pre-registration field: attended work asks for it; `flow --auto` stops with `NEEDS_HUMAN` naming the missing fields. The target is never invented or relaxed by the agent.
- A harness that cannot rank the probe variants correctly: no attempts run. Attended, the harness or workload is revised with the user; unattended, `NEEDS_HUMAN`.
- A revert that fails to restore a clean tree: the run stops; later measurements would be meaningless.
- The budget runs out with the target unmet: the run ends honestly, the PR reports the gap, and the target's criterion stays unverified. Unattended, this is a draft PR, never a relaxed target.
- A measurement tool that needs a dependency the repo does not have: the harness is the user's command; flowctl adds no statistics engine and no dependency. Median and spread are simple arithmetic the agent (or the harness script) performs.
- Noise so large that the minimum detectable effect exceeds the target gap: stop before attempts and report that the instrument cannot resolve the goal.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** On a spec whose route is hill-climb, work refuses to start attempts until the spec names the metric, direction, target, attempt floor, budget, harness command, runs per measurement and minimum detectable effect. Errors: any missing field → attended, a question naming the field; unattended, `NEEDS_HUMAN` naming every missing field. [inferred]
- **R2:** Before the first attempt, the harness is shown to rank a known-worse and a known-better probe correctly with gaps larger than the baseline spread, and to reject an output that is wrong; only then is it frozen with a content hash. Errors: failed ranking or a harness that accepts a wrong output → no attempts; attended revision or unattended `NEEDS_HUMAN`. A later change to the frozen harness forces a new baseline and is recorded as a break in the ledger. [inferred]
- **R3:** An attempt is kept only when its median beats the current best by at least the minimum detectable effect, its range does not overlap the best's, one replicate confirms it, and the regression gate is green; otherwise it is reverted to a clean tree before the next attempt. Errors: a revert that does not restore a clean tree stops the run. [inferred]
- **R4:** Every attempt writes exactly one ledger row regardless of verdict, and every kept attempt is exactly one commit touching only its own files; the ledger summary lands in the task's done evidence. Errors: a missing row, an unmeasured change, or a kept change spread over several commits fails verification before done. [inferred]
- **R5:** The run stops only on (target met and attempt floor reached), budget spent, all profiled families exhausted, or a broken harness; three consecutive non-kept attempts switch hypothesis family rather than stopping. Errors: budget spent with the target unmet → the target criterion is reported unverified and never marked satisfied; under `flow --auto`, a draft PR carrying the gap. [inferred]
- **R6:** The PR briefing for a hill-climb spec shows the metric, target, baseline and final values with the percentage change, attempt counts (kept, reverted, inconclusive), the kept commits in order, the harness proof, the final gate result, and the best untried idea. Errors: any value that cannot be shown renders as unverified rather than being omitted. [inferred]
- **R7:** The routing row, the judge's route literals, the pipeline-variations guide and the flow-next.dev route pages describe the same loop in the same terms, and a worked example like the one in this spec appears in the docs. No error surface beyond the existing routing pin tests passing after the edit. [paraphrase]
- **R8:** The loop is proven on a real fixture: one end-to-end run on a small repository with a measurable metric shows a baseline, a harness proof, at least one kept and one reverted attempt, and the stop, with the ledger and PR evidence as described. The run's artifacts are kept with the change. [paraphrase]

## Boundaries
<!-- scope: business -->

- One-off slowness fixes stay on the existing measured-slowness route; this route is for repeated attempts against a target. [paraphrase]
- No statistics engine, profiler or benchmark framework is added to flowctl; the harness is the user's command. [inferred]
- The agent never changes the target, the attempt floor or the budget; those are spec edits by a human. [inferred]
- No parallel attempts in this spec; attempts are serial so each measurement compares against a known best. [inferred]
- Merge stays human-owned or land-gated as today. [inferred]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

The maintainer asked for this route to be built properly and to be as powerful as possible ("we want this to be as powerful as possible", "definitely do all of this"), with full prose examples ("we can add full prose examples to the specs"). [user] The route is already promised to users in routing and docs, so today a hill-climb request silently gets a single-pass implementation; closing that gap is the point. [paraphrase]

This spec is one of a set captured together to strengthen `/flow-next:flow`: keeping the feature map current, feature-map-aware bug intake, the feature map across live-app routes, a hardened defect route, answering questions by experiment, sharper handovers, a read-only PR status answer, diagnosing a captured profile, and resume and review hygiene. It stands alone; none of them is required for this one.

## Strategy Alignment

Serves the approach line that a ready spec runs through work with a capable agent and that evidence, not narration, decides: the loop makes every kept change carry its own measurement. Serves **Self-improving through normal work**: proven mechanisms feed memory so later climbs start ahead.

## Strategy Conflicts

None found.
