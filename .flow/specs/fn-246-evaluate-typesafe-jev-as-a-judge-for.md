# Evaluate TypeSafe Jev as a judge for flow's pipeline-variation decisions

<!-- Conversation Evidence block omitted at the user's request. Tags below still follow the four-tag grammar; `[user]` lines quote the user inline. -->

## Goal & Context
<!-- scope: business -->

<!-- Source-tag breakdown: 40% [user] / 40% [paraphrase] / 20% [inferred] -->

TypeSafe's Jev is a System One model: it takes a state plus typed questions (Choice, Score, Noul) and returns a typed answer with a probability distribution and a calibrated confidence, in about 100 ms, at roughly $46 per billion tokens. It generates no text. Flow-next today makes a family of closed decisions with the host model that decide which pipeline variation a piece of work takes: which route-matrix row a starting state matches, plan versus no-plan, the spec-count tripwire, whether a fork is observable or a preference call, and whether the QA gate runs. These decisions are host-dependent and unreproducible, and each one costs a host turn.

The user's direction: "we should test our assumptions and judge the value" and "i want to quickly see directionally what is worth pursuing", with the evaluation done "in the easiest and fastest way possible not in the most rigorous way". The two candidate uses the user called out are the route-step auto-router and the pipeline-variation judgments ("everywhere where we need to judge pipeline variations"). Jev access is invite-gated, so anything that later ships must be "fully optional".

This spec is a directional evaluation, not a product change. Its deliverable is a short report that says, per decision site, whether Jev agrees with the host, whether its confidence separates the cases it gets wrong, what the state costs in tokens and latency, and a keep / drop / needs-more-signal call. A follow-up spec decides what, if anything, ships.

## Architecture & Data Models
<!-- scope: technical -->

<!-- Source-tag breakdown: 20% [paraphrase] / 80% [inferred] -->

A throwaway harness, kept outside the plugin and flowctl, with three parts. [inferred]

- **State assembly, deterministic.** For each sample the harness builds the Jev state from machine-readable sources only, with no host-model reading in the loop: the spec show JSON and body, task count, `no_plan` and `ready` fields, PR existence, the branch, a short git summary, and for intent samples the raw intent text. Samples come from three sibling repos' spec directories read in place, run as a checkout-local pass per repo. The user's stated assumption under test is that state assembly must be deterministic for the speed to be real. [paraphrase]
- **Question presets, one per decision site.** Each preset's option set is copied verbatim from the routing reference that owns the decision, with a `none_of_the_above` option appended, and never invented by the harness. [paraphrase] Sites and question shapes: [inferred]
  - Route matrix: one Choice over the matrix rows, plus the two-phase variant from TypeSafe's skill-suggestion cookbook (rank all rows, then re-ask over the top three with the full row text).
  - Plan versus no-plan: three Nouls, one per positive signal named in the rule (user asked for a plan, separate human owners, staged delivery across several PRs).
  - Spec-count tripwire: one Noul, does the intent need more than one spec.
  - Fork classification: one Noul, is the answer observable by running something versus a product or preference call.
  - QA gate: one Noul, does the spec describe a drivable user surface.
- **Labels and comparison.** The current session model, acting as today's router, labels each sample once with the same option sets. Jev's pick is compared with that label, and disagreements are listed for a human eyeball pass. [inferred]

Answers, latency, token usage, state size, and the label land in one JSONL record per sample per site, from which the report is rendered. [inferred]

## API Contracts
<!-- scope: technical -->

<!-- Source-tag breakdown: 100% [inferred] -->

The harness calls the TypeSafe evaluation endpoint with `model: "jev-latest"` and reads the API key from the environment at call time. The key is never written to a file, a record, the report, or a commit. [inferred]

Per-sample record shape (the fields shown are the contract):

```json
{
  "site": "route|plan_vs_no_plan|spec_count|fork_class|qa_gate",
  "sample_id": "fn-123 | intent-07",
  "state_chars": 18400,
  "input_tokens": 4100,
  "latency_ms": 140,
  "jev": {"answer": "capture", "confidence": 0.71, "probabilities": {"capture": 0.71, "work_no_plan": 0.2, "none_of_the_above": 0.09}},
  "label": "capture",
  "agree": true
}
```

Report shape, one block per site: agreement rate, mean confidence on agreements versus disagreements, median latency, median input tokens, count of samples over the 32k-token state budget, and one line of recommendation. [inferred]

## Edge Cases & Constraints
<!-- scope: technical -->

<!-- Source-tag breakdown: 30% [user] / 30% [paraphrase] / 40% [inferred] -->

- **Fails closed.** No key, a non-2xx response after two retries on 429/529, or an answer missing the option set aborts that sample with a recorded reason; the harness never guesses an answer. [paraphrase]
- **Token budget.** A state that exceeds the 32k-token request budget is recorded as over budget and skipped for that site, and the count is reported. The report says whether spec bodies plus show JSON fit. [inferred]
- **Calibration is a group property.** A confident answer is not a verdict; the report reads confidence only as a separator between agreements and disagreements across the set. [paraphrase]
- **Prediction never skips a gate.** The colleague's demo predicts a review verdict; this evaluation does not test verdict prediction, and no site here is a review, QA, or land gate outcome. [paraphrase]
- **Speed is secondary.** The route step is not the wall-clock bottleneck; the value being tested is host-independent, reproducible, evaluable routing. Latency is reported but is not the decision criterion. [paraphrase]
- **Cost is not a constraint.** At $46 per billion tokens a full run over every sample and site costs well under one dollar, so the sample set is bounded by labeling effort, not spend. [user]
- **Not rigorous by design.** No pre-registered bars, no replication, no held-out set. The report states this bound in its first paragraph. [user]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A harness assembles Jev state for a sample from machine-readable flow-next and git sources only, with no host-model reading in the assembly path. Errors: a sample whose spec or intent cannot be read is recorded as unassembled and skipped, never filled in by hand. [paraphrase]
- **R2:** Each of the five sites (route matrix, plan versus no-plan, spec-count tripwire, fork classification, QA gate) has one preset whose option set is taken verbatim from the routing reference that owns the decision plus `none_of_the_above`. Errors: an option set with fewer than two options from the reference fails the preset at load time. [paraphrase]
- **R3:** The sample set spans three repos in the user's workspace, this one, dettivo-linux, and flow-swarm, with at most one third of the route-matrix samples from this repo, because its specs are "too skill heavy" to stand for typical work. It holds at least 30 route-matrix samples across lifecycle states plus at least 10 written intents, and at least 15 samples per remaining site. Errors: a repo whose specs cannot be read is named in the report and the balance rule is reported as unmet, never silently filled from another repo. [user]
- **R4:** Every sample is labeled once by the current session model using the same option set, and Jev's pick is compared against that label; every disagreement is listed with both picks and Jev's confidence. Errors: an unlabeled sample is excluded from agreement figures and counted in the report. [inferred]
- **R5:** The route-matrix site is evaluated in both one-call and two-phase (rank all, re-ask top three) forms, reported side by side. Errors: no error surface beyond R1 and the fail-closed rule. [inferred]
- **R6:** The report gives, per site, agreement rate, confidence on agreements versus disagreements, median latency, median input tokens, over-budget count, and a one-line keep / drop / needs-more-signal call, and opens with the statement that the evaluation is directional and not rigorous. Errors: a site with fewer than the R3 minimum reports its shortfall instead of a call. [user]
- **R7:** The API key is read from the environment at call time only and appears in no file, record, report, or commit; the harness aborts with a named reason when the key is absent, a call fails after retries, or an answer lacks the option set. [paraphrase]
- **R8:** Nothing under the plugin, flowctl, the routing references, or the docs changes in this spec; the harness and report live outside the shipped product. Errors: none beyond the boundary itself. [user]

## Boundaries
<!-- scope: business -->

- No product integration: no flowctl subcommand, no skill change, no config key, no shadow logging in flow. The user ruled out shadow mode because the evaluation can be run directly. [user]
- No verdict prediction to skip a review, QA, or land gate. [paraphrase]
- No rigorous methodology: the private eval repo's full method and replication rules do not apply to this pass. [user]
- The other candidate sites (resolve-pr triage, land's clean-review regex and CI-failure class, review preflight, memory rerank, implementer tier routing) are deferred to a follow-up spec chosen on this report's result. [paraphrase]
- No claim about Jev's calibration beyond what the agreement split shows. [inferred]

## Decision Context
<!-- scope: both -->

- **Eval before build.** The strategy's bitter-lesson rule and the wall-clock research record both say to evaluate a mechanism against its absence before shipping it; a cheap directional pass answers "is any of this worth a real spec" for under a dollar. [paraphrase]
- **Pipeline-variation sites first.** The user picked the route-step router and the variation judgments over the higher-frequency triage and land sites because they are the one dial on the opinionated default path and the place where host-dependence hurts most. [paraphrase]
- **Deterministic state or nothing.** The colleague's skill has the host gather the state, which puts the slow model back in the loop; if the assembled state is not enough for Jev to route, the router idea fails on that fact, which is the answer the eval exists to find. [paraphrase]
- **Mixed-repo samples.** This repo's specs describe skills and plumbing and would flatter a router trained on prose about routing; a desktop app repo and a companion product repo add ordinary feature, bug, and cleanup shapes. [paraphrase]
- **Fast over thorough.** The user asked twice for fast answers; the sample floors are the smallest that give a direction, and a site that misses its floor reports the shortfall rather than waiting for more samples. [user]
- **Session model as labeler.** It is the router today, so agreement with it is the directional question; a human eyeball over disagreements is the cheapest correction for its own errors. [inferred]
- **Optional by construction.** Jev is an external service behind an invite; the strategy's zero-dependency contract means any later integration follows the opt-in pattern with no key meaning today's behaviour byte for byte. This spec ships nothing, so it stays inside the contract. [paraphrase]
- **Rejected:** shadow logging in flow (unnecessary given direct eval), a Python SDK dependency (the endpoint is one HTTP call), and evaluating verdict prediction (a calibrated guess is not a gate). [paraphrase]
