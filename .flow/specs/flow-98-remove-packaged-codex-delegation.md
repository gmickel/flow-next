## Conversation Evidence

> user (turn 6): "we will need to clean this up at some point it is convoluted, i can easily prompt it to do what i want but this makes no sense"
> user (turn 7): "its because we built the delegate thing first, then replaced it with a more dynamic way of just orchestrating"
> user (turn 8): "usage.md covers using it without delegate already right, any downside to just deleting all of the delegate stuff"
> user (turn 9): "point 2 isn't true surely, setup allows writing the orchestration config into CLAUDE.md which is then called on every turn"
> user (turn 10): "we have two options a) we also have flow-swarm (see ~/work/flow-swarm), that has a similar thing but allows the configuration of which model for what more precisely, essentially extending the config model, but if we were to adopt this, then we would have the config twice, one in flow-next, one in flow-swarm"
> user (turn 10): "b) we keep it agentic, CLAUDE.md only and deprecate or remove cleanly in a major release, perhaps with clear docs and a migration route, not sure"
> user (turn 11): "the claude.md thing might still interfere with flow-swarm, butt flow-swarm is optional"
> user (turn 11): "i don't think people use the delegate thing much, we'll be fine, capture it"

## Goal & Context

<!-- Goal & Context: 60% [user], 40% [paraphrase] -->

The model-routing config surface has grown by strata: the packaged codex delegation subsystem (`work.delegate*`, fn-55) was built first, then superseded by the more dynamic agentic orchestration approach - the `/flow-next:setup` CLAUDE.md routing scaffold (standing prose loaded every turn, including autonomous runs) plus the usage.md bridge recipes and the `models.roles` role map. Both layers are live today, producing duplicated pins (`work.delegateModel` vs `models.roles.delegate`), half-inert role-map entries, and a config surface the maintainer describes as "convoluted ... this makes no sense."

Decision (option b): keep flow-next agentic - CLAUDE.md-scaffold prose is the canonical implementation-offload route - and remove the packaged delegation subsystem cleanly in a major release with clear docs and a migration route. Precise per-stage model staffing is flow-swarm's product, not flow-next's; adopting flow-swarm-style config into flow-next (option a) would duplicate routing truth across two products. Delegation usage in the field is believed low ("i don't think people use the delegate thing much"), so the removal risk is accepted.

## Acceptance Criteria

- **R1:** All `work.delegate*` config keys (`delegate`, `delegateConsent`, `delegateDecision`, `delegateEffort`, `delegateModel`, `delegateSandbox`) are removed from flowctl and the published config schema (gen_flow_config_schema.py TABLE + regenerated artifact); schema-drift test green. [paraphrase]
- **R2:** The delegation machinery is removed from the work skill: Phase 0 delegation gating/resolution chain, the `delegate:codex`/`delegate:local` arg tokens, the classify judge, and `references/codex-delegation.md`. [user]
- **R3:** The `models.roles.delegate` pin is removed and the role map is pruned to entries deterministic machinery actually reads. [user]
- **R4:** The CLAUDE.md setup scaffold + usage.md bridge recipes are the documented canonical implementation-offload route; every doc referencing packaged delegation (orchestration.md, ralph.md, teams.md, flowctl.md, skills.md, docs README, repo CLAUDE.md carve-out prose) is updated to point there. [paraphrase]
- **R5:** Migration route: a repo with `work.delegate` set gets a clear, actionable message pointing at the scaffold/bridge route (no silent behavior change); CHANGELOG frames the removal as a breaking change for the next major release. [user]
- **R6:** Delegation-specific tests are removed or repointed (test_codex_delegation_*, test_work_delegate_config, test_ralph_guard_codex_delegation, work-skill delegation route tests); full gate green. [paraphrase]
- **R7:** `spec set-backend` per-spec impl/review/sync fields are retained untouched as data carriage for flow-swarm and other control planes. [paraphrase]
- **R9:** Two things survive the deletion in prose rather than dying with the machinery: (a) the measured tier advice that motivated the packaged default in the first place - a value-tier implementer matched a strong-tier one on correctness at roughly two-thirds the wall on well-specified work - restated as guidance without benchmark tables; (b) the safety half the packaged path enforced, namely that a bridged child writes code while the host keeps git, judgment, and the verdict. Errors: prose that drops (b) turns every bridge recipe into an unbounded second agent, which is the regression this criterion exists to prevent.
- **R10:** The removal lands before the orchestration successor and both ship in one major release; nothing in this spec introduces a replacement vocabulary, because the successor owns it. Errors: shipping this alone would remove a capability with no replacement in the same release, which is the sequencing this criterion forbids.
- **R8:** An explicit decision is recorded in the spec/plan on what ralph-guard keeps: whether the deterministic "bridge child is forbidden from git" enforcement survives for prose-routed bridges, or is dropped with the rationale stated. [inferred]

## Boundaries

- Do NOT adopt flow-swarm-style precise per-stage model config into flow-next (option a rejected - config would exist twice across the two products). [user]
- `review.backend` machinery and the review-backend registry stay - the cross-model review gate is a sanctioned deterministic carve-out, not delegation strata. [paraphrase]
- The other sanctioned subprocess-LLM carve-outs (review-backend dispatch, triage-skip judge) are untouched; only the fn-55 delegation carve-out is retired. [paraphrase]
- Parked - explicitly NOT in the current weekend queue. [user]
- No version bump at implementation time; the major-release framing lands via the batched release process (CHANGELOG `## Unreleased`). [paraphrase]

## Decision Context

### Motivation

- Strata history: delegation (fn-55) predates the dynamic orchestration approach; the newer layer (setup scaffold + role map + bridge recipes, fn-88/97/103/115) superseded it without retiring it. [user]
- The CLAUDE.md scaffold is standing prose loaded every turn - including autonomous pilot/land/Ralph sessions - so agentic routing covers the promptless-runs case that previously justified packaged machinery. [user]
- Product boundary: flow-swarm owns precise per-stage staffing (its `impl_backend`/`review_backend`/staffing API); flow-next stays skill-driven/agentic. The CLAUDE.md scaffold may still interact with flow-swarm-driven repos, but flow-swarm is optional - acceptable. [user]
- Removal risk accepted on low field usage of delegation. [user]
- Prioritization: cleanliness of the routing surface beats preserving a packaged feature the prose route already covers. [paraphrase]

### R8 answered: the Ralph guard reverts, nothing widens (decided 2026-08-14)

The guard grew a delegation-specific amendment when the packaged path landed: a canonical-invocation recognizer, an allowed sandbox-flag list, and a scratch-path shape it would accept. All of it exists to bound one machine-generated command shape that this spec deletes, so it reverts with the feature and the guard returns to exactly what it enforced before the amendment.

Deliberately NOT widened to cover prose-routed bridges. Ralph is already deprecated - a shell script calling the pipeline primitives does what the harness did, and that is the documented route - so building new enforcement into a harness we are steering people away from would be paying maintenance for a path with no future. Ralph worked before the packaged path existed and returns to that behavior; anyone who wants an unattended loop writes a script around the primitives.

The consequence is stated rather than hidden: for prose-routed bridges the "child writes code, host keeps git and judgment" rule lives in prose only (R9b), not in a hook. That is weaker than a mechanical guard, and it is the accepted trade for deleting a subsystem whose enforcement only ever covered one generated command shape.

### Sequencing with the orchestration successor (added 2026-08-14)

This spec deletes; a successor spec defines what replaces it. That successor turns routing into intent expressed to the orchestrator - a small set of named tiers (reviewer, implementer, fast scout, thinking scout, otherwise the session model), consumer-written preferences in the project instruction file, per-harness reach pages, and no shipped model identifiers. `implementer` is the tier that carries this spec's capability forward, which is why the two must ship together: the deletion alone removes something users had, while the pair reads as "implementation routing became a preference you write instead of a subsystem you configure."

Field evidence that the prose route is sufficient, gathered before this was scheduled: an autonomous loop drove an entire spec to a pull request with the session model conducting and reviewing while sixteen implementation dispatches ran on another vendor's CLI, having first asked that CLI which models it offered. Nothing packaged was involved.

Measured deletion surface at planning time: roughly 1,074 lines of delegation reference prose, six config keys, two dedicated reference files, four dedicated test files, plus delegation mentions across 59 canonical files.

## Requirement coverage

| R-ID | Task |
|------|------|
| R1 | fn-N.M (TBD - populate via /flow-next:plan) |
| R2 | fn-N.M (TBD - populate via /flow-next:plan) |
| R3 | fn-N.M (TBD - populate via /flow-next:plan) |
| R4 | fn-N.M (TBD - populate via /flow-next:plan) |
| R5 | fn-N.M (TBD - populate via /flow-next:plan) |
| R6 | fn-N.M (TBD - populate via /flow-next:plan) |
| R7 | fn-N.M (TBD - populate via /flow-next:plan) |
| R8 | fn-N.M (TBD - populate via /flow-next:plan) |
