# Hill climb: the agent sets up the experiment

## Conversation Evidence

> user (turn 1): "the loop should happen whenever flow-next:flow decides to use that route, what am i misunderstanding"
> user (turn 2): "how does pstack do it, i am wary of overengineering and limiting what the agent can do, come up with the final solution"
> user (turn 3): "explain it what will change, does this rebuild everything?"
> user (turn 4): "i agree, do, our strategy is not too much machinery"

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 20% [user], 60% [paraphrase], 20% [inferred] -->

6.4.0 shipped the hill-climb loop (fn-265), but its first step requires the spec to carry a `## Hill-climb pre-registration` section with nine exact labelled fields, and any missing field stops the run before anything is measured. Capture, refine and the spec template know nothing about that section, so a hill-climb spec captured from a conversation such as "get cold start under 40 ms, keep trying" reaches the loop and stops; unattended, that is `NEEDS_HUMAN` asking for values the agent could decide itself. [paraphrase]

pstack's hillclimb playbook (21 lines) has no such form. The agent grounds the workload, fixes the metric, direction and a stop predicate (a target plus an attempt floor), builds and proves the harness, then loops; "Use the user's numbers when given, otherwise agree them." The maintainer's direction: the loop runs whenever flow chooses the route, the agent is not limited by a form, and "our strategy is not too much machinery". [paraphrase]

This spec replaces the form with the agent setting up the experiment and recording its choices at the top of the ledger. It changes one reference file and its small dependents; nothing else is rebuilt. [paraphrase]

Target user: anyone who asks flow to move one number toward a target, attended or through `flow --auto`. [inferred]

## Architecture & Data Models
<!-- scope: technical -->

- **The loop's instructions are rewritten shorter.** The work reference for the hill-climb loop keeps its discipline and drops the form: the worker reads the target from the spec, then decides the measured case, metric, direction, attempt floor, budget, runs per measurement and the smallest difference that counts, using the user's numbers where the spec or conversation gives them. It writes those choices as the ledger's header before the first attempt, so they are fixed in advance and visible in the pull request. [paraphrase]
- **The agent builds, proves and freezes the harness** (it is no longer "the user's command"), and records the baseline and a green regression gate before any change. [paraphrase]
- **One stop condition for missing information:** the spec states no target. Attended, work asks once; unattended, `NEEDS_HUMAN`. The target is never invented, relaxed or reinterpreted. [paraphrase]
- **Kept discipline:** one change per measurement; keep only past the noise with the regression gate green; revert everything else; one ledger row per attempt whatever the verdict; a missed target is reported and recorded `deferred`, never relaxed. [paraphrase]
- **Aligned with pstack:** a simplification that holds the number may be kept; independent hypotheses may be tried in parallel, each in its own worktree, each kept only on its own measurement against the current best. [paraphrase]
- **Removed:** the nine required labels, the missing-field stop, the required second replicate measurement, and the fixture check that the labels match. The worker's trigger is the spec's goal (one metric moved toward a target), with no mention of a labelled section. The fixture's recorded run stays as the worked example. [paraphrase]
- **Unchanged:** flow's routing, the work task and worker dispatch, review, completion, make-pr and the PR briefing's hill-climb proof cells, flowctl, capture, refine and the spec template. [paraphrase]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A spec whose goal is one metric moved toward a stated target runs the loop without any labelled pre-registration section; the worker records its chosen setup (case, metric, direction, attempt floor, budget, runs per measurement, smallest meaningful difference, harness and regression gate) as the ledger header before the first attempt, taking the user's values where the spec gives them. [paraphrase]
- **R2:** The only missing-information stop is a spec with no target: attended, one question; unattended, `NEEDS_HUMAN`. No other missing value stops the run. [paraphrase]
- **R3:** The keep rule, revert rule, one-row-per-attempt ledger and the honest unmet-target path (`deferred`, never relaxed) still hold; a simplification that holds the number may be kept; independent hypotheses may run in parallel worktrees, each measured against the current best. [paraphrase]
- **R4:** The loop reference is shorter than the 6.4.0 version, and the nine-label requirement, the missing-field stop, the required replicate and the label-parity fixture check are gone; the worker's trigger no longer names a labelled section. [inferred]
- **R5:** The pipeline-variations doc, the flow-next.dev pages that describe the loop, and the CHANGELOG describe the agent-set-up loop consistently. [inferred]
- **R6:** The full test suite passes and the codex mirror is regenerated. [inferred]

## Boundaries
<!-- scope: business -->

- No new machinery: no spec section, template entry, capture or refine step, config key or flowctl code. [paraphrase]
- Flow's routing and every stage outside the loop's reference are unchanged. [paraphrase]
- The target stays the human's; the agent never invents or relaxes it. [paraphrase]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

The maintainer is wary of overengineering and of limiting what the agent can do ("our strategy is not too much machinery"). [user] The first proposal (teach capture and refine to fill the form, add it to the template, default two fields in work) added machinery to feed a form that should not exist; pstack shows the smaller shape. [paraphrase]

## Strategy Alignment

Serves the approach line that the host agent is the intelligence and flowctl provides only thin helpers, and the bitter-lesson principle: do not build scaffolding around a model's weaknesses.

## Strategy Conflicts

None found.
