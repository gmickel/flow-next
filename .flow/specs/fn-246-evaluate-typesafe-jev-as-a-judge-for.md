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

## Results (2026-09-17, two passes)

Study: private eval repo, `studies/jev-pipeline-judge-2026-09` (report.md, report_v2.md, records). Pass 1 covered the five pipeline-variation sites over 49 samples from three repos; pass 2 fixed the evidence (deterministic pre-routing, declared arrival view, live PR state, code-supplied startable target, tightened instructions, fork gate), added majority baselines and per-class precision/recall, and evaluated the six deferred sites. All Jev calls fit the budget (max 17k input tokens), median 600-970 ms per request, cost negligible.

| Site | Result vs majority baseline | Call |
|---|---|---|
| Land clean-review as 3-way Choice (clean / findings / wrapper) | 100/100 vs 0.77; catches 7 clean rewordings the regex misses; regex 5/12 with 15 false alarms | build |
| QA gate, UI-only question plus code-supplied startable fact | 0.88 vs 0.71 | build |
| Fork gate Noul, then observable-vs-preference Choice | 0.88 vs 0.76 gate; 10/12 on labeled forks; invented forks 12 to 1 | build with a confidence floor |
| Memory rerank, 15 Scores per call | precision@5 0.66 vs BM25 0.48; beats BM25 on 19/26 tasks | promising; needs a human-labeled subset |
| Route matrix, two-phase | 0.65 vs 0.28 on 40 non-prerouted samples; residue is refine vs plan-review vs chart | host keeps routing; Jev top-3 usable as a shortlist |
| Resolve-pr triage | actionable unscorable (79/90 fixed); category 0.51 vs 0.39 | needs a different enum and real negatives |
| Plan vs no-plan | at baseline; recorded routes encode the retired plan-by-default policy | drop |
| Spec-count tripwire | 33 trips predicted vs 15 labeled under both wordings | drop |
| Review preflight (predict first-round verdict from the diff) | 0.61 vs 0.55; no decomposed Noul separates; verdict tracks reviewer backend (codex 85% NEEDS_WORK, host 71% SHIP) | drop |
| CI failure class | ground truth degenerate on this repo (37 vs 2, no reruns) | untestable here |
| Implementer tier | Spearman 0.43 with lines changed; no real label | no call |

Pattern: Jev wins where code supplies the facts and the option set matches what the data contains, and loses where the decision is a judgment over soft categories. Caveats: single Jev run per sample; clean-review, triage category, and memory labels are session-model eyeballs; thresholds at 0.5 or swept on the same data; 53/96 preflight diffs truncated.

Follow-ups chosen: build clean-review detection in land (regex stays as the no-key fallback), the QA gate under pipeline.qa=auto, and the fork gate in prototype-before-ask, each opt-in behind the key. Iteration continues on the route step (labeler self-consistency ceiling; decomposed fact Nouls with the matrix in code) before any router decision.

### Pass 3 (2026-09-17): routing ceiling, decomposition, verdict prediction, pipeline composer

- Labeler ceiling: three labelers agree pairwise 0.82-0.88; 31/40 route samples stable. Jev two-phase reaches 0.74 on the stable subset and 0.33 on the unstable one, so about a third of the route miss is the label and two thirds the question shape.
- Decomposed facts: anchored content Nouls (defect, structural change, metric, how/why question, direction, staged PRs) agree 0.96-1.0; judgment Nouls over-fire (unresolved questions 31/40, design needs assessment 30/40, observable fork 11/40 against 1 labeled). A Noul-driven precedence tree lands at 0.62, no better than the row Choice.
- Verdict prediction (the cloned jev-predict-skill shape) on 20 tasks with recorded verdicts: 0.55 against a 0.50 baseline, SHIP on 19/20, and its breakdown gate passes everything. Dropped.
- Pipeline composer: an eleven-way kind Choice with lifecycle rows decided by code first agrees 0.78 with a fresh composer scout (0.72 excluding the code-decided existing-PR samples) and 0.70 with the three-labeler majority, confidence 0.89 on agreements vs 0.61 on misses. Non-build kinds each rest on one to three samples. Within the build kind the fact-driven stages hold (tiny direct 15/16, QA 15/16, research 14/16, capture vs direct 12/16); the judgment stages (plan-review, refine, split, chart, visual, features) are predicted on 9-11 of 16 against 0-3 labels; exact stage-set match 0/16. What-ran labels on 23 done specs show the same overcall and cannot say what was optimal.

Routing conclusion: the route step is a Jev job as (1) the kind Choice after code decides the lifecycle rows and (2) individual anchored-fact Nouls that code consumes; not as the row picker, the Noul precedence tree, the full stage composer, or the predict-the-verdict two-step. Hybrid shape: code facts plus one Jev call (kind and anchored Nouls) composing the fixed part of the pipeline, the host deciding refine, plan-review, split, chart, and lenses with Jev probabilities as hints, host fallback below about 0.6 kind confidence.

### Pass 4 (2026-09-17): route-assist design on a balanced set

- Set: 214 samples, 196 stable (two blind scouts at 0.91 pairwise, 0.99-1.0 against author intent on the authored set), 10-38 per kind, 168 intent texts. Held-out third chosen by id hash before any number was read.
- Kind Choice shape matters more than anything else tried: criteria = the matrix's starting-state cell plus its positive-signal cell, verbatim, scores 0.95 raw on the stable set; positive signal alone 0.82; adding safe-skip text 0.81; two-phase 0.89-0.91 (two calls); framed as the Next: command 0.51; coarse-then-fine 0.85.
- Confidence floor on the held-out third: at 0.7, 84% of content inputs route automatically at 98% accuracy on the covered set; the fallback sixth is 60% right under any router here. Floors 0.6 / 0.8 / 0.9 give 92% at 93%, 70% at 98%, 56% at 100%. The one confidently wrong boundary is tiny vs build.
- Code facts beat or tie Jev on separate owners, staged PRs, asks-for-plan (0.99-1.0) and on lifecycle rows; the research Noul (0.97, recall 0.86-0.89) beats the deterministic scan (0.95, recall 0.57). Fact-grade Nouls: defect, defect-with-repro, structural change, metric and surface, repeated target, read-only question, theme, unfamiliary library. Judgment Nouls stay out of the decision order: observable fork, tiny change, intent stateable, UI-observable criteria. The Choice beats a Noul precedence tree (0.95 vs 0.80).
- Host assist, the cookbook pattern, does not hold on intent text: haiku alone routes at 0.90-0.93 (two runs, 0.96 self-agreement); a one-line Jev hint drops it to 0.82 and the full fact dump to 0.86, because the host second-guesses answers it had right. Jev plus code lifecycle beats haiku on live specs (30/33 vs 24/33) and PR bodies (7/7 vs 0/7), where the host routes on input kind.
- Consistency: the same Jev call twice agrees on 195/196 with a mean confidence delta of 0.012; two haiku runs disagree on 7/196.
- --explain: full recommendation shape from code plus one call in about 0.6 s versus 6-8 s for a sonnet host; the host's why-not prose is better.

Design: lifecycle rows decided by code first; one Jev call carrying the kind Choice (starting-state plus positive-signal criteria) and the anchored Nouls; kind at or above 0.7 routes and quotes its firing Noul as the Signal line; below the floor or none_of_the_above the host decides with the top-3 as candidates and never receives the raw Nouls; modifiers (plan asked, staged PRs, separate owners, research names, repro) from code and fact-grade Nouls. Verdict: a value add for unattended runs and hosts that would spend a turn on routing (removes the route step for five inputs in six and never decides the sixth), and for cross-host consistency; not a value add for an attended session on a capable host. Before shipping: a third scout on the 18 unstable issue/PR samples, and the tiny-vs-build boundary tightened in the matrix text or handed to the host below 0.8.
