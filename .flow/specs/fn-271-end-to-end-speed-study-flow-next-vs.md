# End-to-end speed study: flow-next vs vanilla Claude Code

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 20% [user], 70% [paraphrase], 10% [inferred] -->

The maintainer wants to know whether flow-next as a whole makes an agent faster end to end than vanilla Claude Code. The answer decides whether a public wall-clock claim ("flow-next gets you from report to merged fix faster") can be made or must be refused, and it gives later optimisation work a baseline that shows whether each change keeps paying off.

Why now: three agent-evals studies (feature-map-2026-09, defect-intake-map-2026-09, live-routes-map-2026-09) found that a maintained feature map roughly halves turns and wall time when the task does not say where in the app the problem is. The not-located slowness baseline went from 26.3 to 14.0 turns and 97 s to 46 s; not-located tasks pooled across routes went from 25.0 to 14.7 turns and 71 s to 40 s, with success 8/9 to 9/9. When the task names the place, the map gave no gain. In all three studies both arms were plain `claude -p` sessions and no flow-next skill ran. The gain therefore belongs to the map file plus a one-paragraph gate, not to flow-next. None of the studies measured flow-next's own overhead (skill loading, routing and judge calls, receipts, reviews, worker dispatch) or the one-time cost of seeding the map. The maintainer asked how many of the measured turns were flow-next turns that a vanilla setup would not have spent; the honest answer today is that none were measured.

## Architecture & Data Models
<!-- scope: technical -->

- **Where it runs.** The study lives in the private agent-evals repository and follows its `METHODOLOGY.md` and `lib/evalkit.py`: preregistered, model held constant, every draw retained. It reuses the existing fixture harness (isolated T3 Code v0.0.42 instances scored by live state plus database) rather than building a new one. [paraphrase]
- **Arms.** At minimum: (a) vanilla Claude Code given the task only; (b) vanilla Claude Code plus a maintained feature map and the short gate, which isolates the map's effect; (c) full flow-next driving the same task, for example `/flow-next:flow` on a bug report through to a verified fix, or a preregistered sub-goal if a full merge is not practical on the fixture. [paraphrase]
- **Task mix.** Both located reports (the task names where the problem is) and not-located reports, because that split decided every earlier result. [paraphrase]
- **Measurement source.** The harness's stream logs are the only instrument. Overhead is attributed from those logs by a rule fixed in the preregistration; flowctl is not instrumented. [paraphrase]

## Edge Cases & Constraints
<!-- scope: technical -->

- Gating draws run one at a time on an otherwise idle machine; concurrent draws may inform but never carry the verdict, and preregistration terms are exact, not soft (prior study failure recorded in project memory). [inferred]
- Cross-family review is optional in flow-next, so it is a configuration of arm (c), not a fixed part of it. The preregistration fixes arm (c)'s configuration (the shipped default, and optionally a with/without-review pair) and records any reviewer's backend, model and effort; whatever runs counts toward arm (c)'s tokens and wall time. The implementing model stays the same across all arms. [user]
- A fixture on which arm (c) cannot reach the preregistered endpoint (for example, no merge target) uses the preregistered sub-goal for every arm on that task, so arms are compared on the same endpoint. [inferred]
- The expected advantage of flow-next is outcome quality, not raw speed: its prior-fix check, diagnosis, base/head proof and verification should yield better fixes even at equal or higher wall time. The primary comparison is therefore time and cost to a correct fix, and the quality rubric must catch a fix that passes once but is wrong or incomplete (rework a vanilla fix would need counts against that arm). A faster arm that produces a worse fix does not win. [user]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Before any draw, a preregistration is committed in agent-evals naming the hypotheses, the arms, the task set with its located and not-located split, the metrics and decision bars (what counts as faster, equal or slower), the draw count, the held-constant model, the fix-quality rubric, the overhead attribution rule, and the proposed spend. No draw runs until the maintainer has approved the spend. Errors: a draw run before approval, or any bar or rubric changed after the first gating draw, is recorded as a deviation and cannot carry the verdict. [paraphrase]
- **R2:** The study runs at least arms (a) vanilla with the task only, (b) vanilla plus a maintained feature map and the short gate, and (c) full flow-next driving the same task to a verified fix or the preregistered sub-goal, all on the existing fixture harness with the same model. Errors: an arm (c) draw that stalls, errors or stops for a human is scored as a failed draw with its elapsed cost, never dropped or rerun silently. [paraphrase]
- **R3:** Every draw records success by live state, wall-clock, turns, token cost, and a fix-quality score from the preregistered rubric, and results are reported for located tasks, not-located tasks and pooled. Errors: a draw the scorer cannot read is reported as unscored and counted in the totals; a split whose draws cannot reach the preregistered bar is reported as inconclusive for that split. [paraphrase]
- **R4:** For arm (c), turns, wall time and tokens are broken out into flow-next machinery (skill loading, routing and judge calls, receipts, reviews, worker dispatch) versus work on the task, from the harness stream logs only, and this breakdown is recorded as the baseline for later optimisation studies such as fn-260's trimming items. Errors: a span the attribution rule cannot place is reported as unattributed, never assigned to either side. [paraphrase]
- **R5:** The one-time cost of seeding the feature map (turns, wall time, tokens) is measured separately from the per-task draws and reported beside them, with the number of tasks after which the map arm's per-task saving covers that cost. No error surface beyond R3's unscored-draw handling. [paraphrase]
- **R6:** The study writes a verdict that states, per split and pooled, where full flow-next is faster than, equal to or slower than each vanilla arm and by how much, whether fix quality differs, and the time and cost to a correct fix; every draw, including failures and negative results, stays in the study record. No error surface beyond R1's deviation rule. [paraphrase]
- **R7:** Public documentation states only conclusions, and a public wall-clock claim is made only when the R6 verdict supports it; when it does not, the verdict records the claim as refused and no public text claims speed. Errors: a conclusion that would need raw study data, private paths or per-draw logs to support it is not published. [paraphrase]

## Boundaries
<!-- scope: business -->

- Evaluation only: no flow-next product change is made in this spec. [paraphrase]
- flowctl gains no telemetry; measurement uses the harness's stream logs. [user]
- Study data, logs and the preregistration stay in the private agent-evals repository; public docs carry conclusions only. [paraphrase]
- Rerunning or replacing fn-263's R5 map-use study (live-routes-map-2026-09) is out of scope; its results are prior evidence here. [inferred]

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation
<!-- scope: business -->

A public claim that flow-next is faster needs evidence that flow-next, not the map artifact alone, produced the gain, net of its own overhead and the map's seeding cost. [paraphrase] Arm (b) exists to separate those two effects; without it, a gain in arm (c) could not be credited to flow-next. [paraphrase] Fix quality is scored alongside speed because flow-next adds reviews that vanilla does not, so a speed-only comparison would penalise work that buys quality. [paraphrase] Spend is proposed in the preregistration and approved by the maintainer before draws. [user]

## Strategy Alignment

STRATEGY.md lists idea-to-merge wall-clock as a key metric "worth measuring as the system matures"; this study is the first end-to-end measurement of it against a vanilla baseline. The "remember the bitter lesson" principle asks that machinery be evaluated against its absence with preregistered bars; arm (a) is that absence for flow-next as a whole. The overhead breakdown gives the "flowctl grows only under burden of proof" and trimming work a measured cost to argue from.
